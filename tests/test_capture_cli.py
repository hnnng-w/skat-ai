import argparse
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import main as legacy_main
import skat_ai.cli.capture as capture_cli
import skat_ai.cli.execution as root_cli
from skat_ai.capture_web.contracts import MATCH_CAPTURE_WEB_BIND_HOST
from skat_ai.cli.capture_parser import (
    MATCH_CAPTURE_CLI_COMMAND,
    MATCH_CAPTURE_CLI_VERSION,
    build_capture_argument_parser,
    parse_capture_arguments,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _actions(parser: argparse.ArgumentParser) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            tuple(action.option_strings),
            action.dest,
            action.required,
            action.default,
            action.nargs,
        )
        for action in parser._actions
    )


def test_capture_cli_version_command_and_exact_options() -> None:
    assert MATCH_CAPTURE_CLI_VERSION == 1
    assert MATCH_CAPTURE_CLI_COMMAND == "capture"
    parser = build_capture_argument_parser()
    assert _actions(parser) == (
        (("-h", "--help"), "help", False, "==SUPPRESS==", 0),
        (("--workspace",), "workspace", True, None, None),
        (("--port",), "port", False, 0, None),
        (("--no-open",), "no_open", False, False, 0),
    )
    option_strings = {
        option for action in parser._actions for option in action.option_strings
    }
    assert option_strings == {
        "-h",
        "--help",
        "--workspace",
        "--port",
        "--no-open",
    }


def test_capture_parser_defaults_valid_port_no_open_and_invocation_identity() -> None:
    args = parse_capture_arguments(["--workspace", "match.json"])
    assert vars(args) == {
        "workspace": "match.json",
        "port": 0,
        "no_open": False,
    }
    args = parse_capture_arguments(
        ["--workspace", "match.json", "--port", "12345", "--no-open"],
        invocation_style="module",
    )
    assert vars(args) == {
        "workspace": "match.json",
        "port": 12345,
        "no_open": True,
    }
    assert build_capture_argument_parser(invocation_style="installed").prog == (
        "skat-ai capture"
    )
    assert build_capture_argument_parser(invocation_style="module").prog == (
        "python -m skat_ai capture"
    )
    assert build_capture_argument_parser(invocation_style="legacy").prog == (
        "python main.py capture"
    )


@pytest.mark.parametrize("port", ("0", "-1", "65536", "true", "1.5"))
def test_capture_parser_rejects_invalid_explicit_port(port: str) -> None:
    with pytest.raises(SystemExit) as raised:
        parse_capture_arguments(
            ["--workspace", "match.json", "--port", port]
        )
    assert raised.value.code == 2


@pytest.mark.parametrize(
    "argv",
    (
        [],
        ["--workspace"],
        ["--workspace", "match.json", "--host", "0.0.0.0"],
        ["--workspace", "match.json", "--force"],
        ["--workspace", "match.json", "--daemon"],
        ["--workspace", "match.json", "--output", "x.json"],
    ),
)
def test_capture_parser_rejects_missing_or_unsupported_options(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        parse_capture_arguments(argv)
    assert raised.value.code == 2


@pytest.mark.parametrize(
    ("command", "usage"),
    (
        ([sys.executable, "-m", "skat_ai", "capture", "--help"], "python -m skat_ai capture"),
        ([sys.executable, "main.py", "capture", "--help"], "python main.py capture"),
    ),
)
def test_module_and_legacy_capture_help(command: list[str], usage: str) -> None:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert not completed.stderr
    assert f"usage: {usage}" in completed.stdout
    assert "--workspace PATH" in completed.stdout
    assert "--port INTEGER" in completed.stdout
    assert "--no-open" in completed.stdout
    assert "--host" not in completed.stdout


def test_capture_dispatch_precedes_session_and_root(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        capture_cli,
        "run_capture_cli",
        lambda argv, *, invocation_style: calls.append((argv, invocation_style)) or 17,
    )
    assert root_cli.run_cli(
        ["capture", "--workspace", "match.json"],
        invocation_style="module",
    ) == 17
    assert calls == [(('--workspace', 'match.json'), "module")]


def test_legacy_capture_dispatch_uses_package_implementation(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        capture_cli,
        "run_capture_cli",
        lambda argv, *, invocation_style: calls.append((argv, invocation_style)) or 0,
    )
    assert root_cli.run_cli(
        ["capture", "--workspace", "match.json"],
        invocation_style="legacy",
        legacy_namespace=legacy_main,
    ) == 0
    assert calls == [(('--workspace', 'match.json'), "legacy")]


class _InterruptingServer:
    def __init__(self, _context, *, port: int) -> None:
        assert port in {0, 12345}
        self.bootstrap_url = f"http://127.0.0.1:{port or 54321}/?token=test"
        self.closed = False

    def serve_forever(self) -> None:
        raise KeyboardInterrupt

    def server_close(self) -> None:
        self.closed = True


def test_capture_cli_startup_browser_open_interrupt_and_shutdown(
    tmp_path: Path,
    capsys,
) -> None:
    opened = []
    server = None

    def factory(context, *, port):
        nonlocal server
        server = _InterruptingServer(context, port=port)
        return server

    result = capture_cli.run_capture_cli(
        ["--workspace", str(tmp_path / "match.json")],
        server_factory=factory,
        browser_open=lambda url: opened.append(url) or True,
    )
    assert result == 0
    assert opened == ["http://127.0.0.1:54321/?token=test"]
    assert server is not None and server.closed is True
    captured = capsys.readouterr()
    assert captured.out == (
        "Local Match capture: http://127.0.0.1:54321/?token=test\n"
    )
    assert not captured.err


def test_capture_cli_no_open_and_browser_failure_warning(tmp_path: Path, capsys) -> None:
    opened = []

    result = capture_cli.run_capture_cli(
        ["--workspace", str(tmp_path / "match.json"), "--no-open"],
        server_factory=_InterruptingServer,
        browser_open=lambda url: opened.append(url),
    )
    assert result == 0 and opened == []
    capsys.readouterr()

    result = capture_cli.run_capture_cli(
        ["--workspace", str(tmp_path / "match-2.json")],
        server_factory=_InterruptingServer,
        browser_open=lambda _url: False,
    )
    assert result == 0
    assert "Warning: Could not open the browser." in capsys.readouterr().err


def test_capture_cli_startup_failures_return_one(tmp_path: Path, capsys) -> None:
    missing_parent = tmp_path / "missing" / "match.json"
    assert capture_cli.run_capture_cli(
        ["--workspace", str(missing_parent), "--no-open"],
        server_factory=_InterruptingServer,
    ) == 1
    assert "Error:" in capsys.readouterr().err

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    assert capture_cli.run_capture_cli(
        ["--workspace", str(invalid), "--no-open"],
        server_factory=_InterruptingServer,
    ) == 1
    assert "Error:" in capsys.readouterr().err


def test_capture_server_factory_always_receives_loopback_context(tmp_path: Path) -> None:
    captured = SimpleNamespace()

    def factory(context, *, port):
        captured.context = context
        captured.port = port
        captured.host = MATCH_CAPTURE_WEB_BIND_HOST
        return _InterruptingServer(context, port=port)

    assert capture_cli.run_capture_cli(
        [
            "--workspace",
            str(tmp_path / "match.json"),
            "--port",
            "12345",
            "--no-open",
        ],
        server_factory=factory,
    ) == 0
    assert captured.host == "127.0.0.1"
    assert captured.port == 12345
    assert captured.context.workspace_path.name == "match.json"
