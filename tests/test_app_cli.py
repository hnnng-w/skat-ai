from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

import main as legacy_main
import skatmind.cli.app as app_cli
import skatmind.cli.execution as root_cli
from skatmind.cli.app_parser import (
    APP_CLI_COMMAND,
    LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION,
    build_app_argument_parser,
    parse_app_arguments,
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


def test_app_parser_contract_and_exact_options() -> None:
    assert LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION == 1
    assert APP_CLI_COMMAND == "app"
    assert _actions(build_app_argument_parser()) == (
        (("-h", "--help"), "help", False, "==SUPPRESS==", 0),
        (("--data-root",), "data_root", False, None, None),
        (("--port",), "port", False, 0, None),
        (("--no-open",), "no_open", False, False, 0),
    )


def test_app_parser_defaults_port_zero_override_and_invocation_identity() -> None:
    assert vars(parse_app_arguments([])) == {
        "data_root": None,
        "port": 0,
        "no_open": False,
    }
    assert vars(
        parse_app_arguments(
            ["--data-root", "private", "--port", "0", "--no-open"],
            invocation_style="module",
        )
    ) == {"data_root": "private", "port": 0, "no_open": True}
    assert parse_app_arguments(["--port", "65535"]).port == 65_535
    assert build_app_argument_parser(invocation_style="installed").prog == "skatmind app"
    assert build_app_argument_parser(invocation_style="module").prog == (
        "python -m skatmind app"
    )
    assert build_app_argument_parser(invocation_style="legacy").prog == (
        "python main.py app"
    )


@pytest.mark.parametrize("port", ("-1", "65536", "true", "1.5"))
def test_app_parser_rejects_invalid_ports(port: str) -> None:
    with pytest.raises(SystemExit) as raised:
        parse_app_arguments(["--port", port])
    assert raised.value.code == 2


@pytest.mark.parametrize(
    "argv",
    (
        ["--data-root"],
        ["--host", "0.0.0.0"],
        ["--daemon"],
        ["--output", "result.json"],
        ["--force"],
    ),
)
def test_app_parser_rejects_missing_or_unsupported_options(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        parse_app_arguments(argv)
    assert raised.value.code == 2


@pytest.mark.parametrize(
    ("command", "usage"),
    (
        ([sys.executable, "-m", "skatmind", "app", "--help"], "python -m skatmind app"),
        ([sys.executable, "main.py", "app", "--help"], "python main.py app"),
    ),
)
def test_module_and_legacy_app_help(command: list[str], usage: str) -> None:
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
    assert "--data-root PATH" in completed.stdout
    assert "--port INTEGER" in completed.stdout
    assert "--no-open" in completed.stdout
    assert "--host" not in completed.stdout


@pytest.mark.parametrize("style", ("installed", "module", "legacy"))
def test_shell_first_entrypoints_do_not_import_product_families(style: str) -> None:
    probe = """
import runpy
import sys
from types import ModuleType

style = sys.argv[1]
app_module = ModuleType("skatmind.cli.app")
app_module.run_app_cli = lambda argv, *, invocation_style: 0
sys.modules["skatmind.cli.app"] = app_module
sys.argv = ["skatmind"]
if style == "installed":
    from skatmind.cli import main
    assert main() == 0
elif style == "module":
    try:
        runpy.run_module("skatmind", run_name="__main__")
    except SystemExit as error:
        assert error.code == 0
else:
    sys.argv[0] = "main.py"
    try:
        runpy.run_path("main.py", run_name="__main__")
    except SystemExit as error:
        assert error.code == 0

blocked = (
    "skatmind.application",
    "skatmind.capture_web",
    "skatmind.corpus_web",
    "skatmind.learning_corpus",
    "skatmind.match_",
    "skatmind.session",
)
loaded = sorted(
    name for name in sys.modules
    if any(name == prefix or name.startswith(prefix) for prefix in blocked)
)
assert loaded == [], loaded
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe, style],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_app_help_imports_no_product_families() -> None:
    probe = """
import sys
from skatmind.cli.entrypoint import run_cli

try:
    run_cli(["app", "--help"])
except SystemExit as error:
    assert error.code == 0
blocked = (
    "skatmind.application",
    "skatmind.capture_web",
    "skatmind.corpus_web",
    "skatmind.learning_corpus",
    "skatmind.match_",
    "skatmind.session",
)
loaded = sorted(
    name for name in sys.modules
    if any(name == prefix or name.startswith(prefix) for prefix in blocked)
)
assert loaded == [], loaded
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("style", ("installed", "module", "legacy"))
def test_bare_dispatch_runs_app_for_all_invocation_styles(
    style: str,
    monkeypatch,
) -> None:
    calls = []
    monkeypatch.setattr(
        app_cli,
        "run_app_cli",
        lambda argv, *, invocation_style: calls.append((argv, invocation_style)) or 17,
    )
    namespace = legacy_main if style == "legacy" else None
    assert root_cli.run_cli([], invocation_style=style, legacy_namespace=namespace) == 17
    assert calls == [((), style)]


def test_explicit_app_dispatch_passes_only_remaining_arguments(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        app_cli,
        "run_app_cli",
        lambda argv, *, invocation_style: calls.append((argv, invocation_style)) or 19,
    )
    assert root_cli.run_cli(
        ["app", "--data-root", "private", "--no-open"],
        invocation_style="module",
    ) == 19
    assert calls == [(('--data-root', 'private', '--no-open'), "module")]


def test_existing_leading_dispatch_and_root_routes_are_preserved(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        root_cli,
        "_run_cli",
        lambda argv, style: calls.append(("root", argv, style)) or 1,
    )
    assert root_cli.run_cli(["--input", "position.json"], invocation_style="module") == 1
    assert calls == [("root", ["--input", "position.json"], "module")]


class _InterruptingServer:
    def __init__(self, context, *, port: int) -> None:
        self.context = context
        self.port = port
        self.bootstrap_url = f"http://127.0.0.1:{port or 54321}/?token=secret-token"
        self.serve_count = 0
        self.close_count = 0

    def serve_forever(self) -> None:
        self.serve_count += 1
        raise KeyboardInterrupt

    def server_close(self) -> None:
        self.close_count += 1


def test_app_cli_browser_success_uses_managed_root_and_secret_free_output(
    tmp_path: Path,
    capsys,
) -> None:
    root = tmp_path / "managed"
    opened = []
    server = None

    def factory(context, *, port):
        nonlocal server
        server = _InterruptingServer(context, port=port)
        return server

    assert app_cli.run_app_cli(
        [],
        server_factory=factory,
        browser_open=lambda url: opened.append(url) or True,
        managed_root_resolver=lambda: root,
    ) == 0
    assert opened == ["http://127.0.0.1:54321/?token=secret-token"]
    assert server is not None
    assert server.serve_count == 1
    assert server.close_count == 1
    assert server.context.managed_home.root == root
    assert sorted(path.name for path in root.iterdir()) == ["corpora", "matches", "sessions"]
    captured = capsys.readouterr()
    assert captured.out == (
        "SkatMind is running locally. Press Ctrl+C to stop.\n"
        "SkatMind stopped.\n"
    )
    assert not captured.err
    for secret in ("127.0.0.1", "54321", str(root), "secret-token"):
        assert secret not in captured.out


@pytest.mark.parametrize("failure", (False, None, RuntimeError("browser failed")))
def test_app_cli_browser_failure_prints_one_bootstrap_url_and_continues(
    tmp_path: Path,
    capsys,
    failure: object,
) -> None:
    def opener(_url: str) -> object:
        if isinstance(failure, Exception):
            raise failure
        return failure

    assert app_cli.run_app_cli(
        [],
        server_factory=_InterruptingServer,
        browser_open=opener,
        managed_root_resolver=lambda: tmp_path / "managed",
    ) == 0
    captured = capsys.readouterr()
    assert captured.out.count("http://127.0.0.1:54321/?token=secret-token") == 1
    assert captured.out.endswith("SkatMind stopped.\n")
    assert not captured.err


def test_app_cli_no_open_uses_explicit_root_without_resolver_or_browser(
    tmp_path: Path,
    capsys,
) -> None:
    calls = []

    def unexpected_resolver() -> Path:
        raise AssertionError("Explicit data root attempted platform resolution.")

    root = tmp_path / "explicit"
    assert app_cli.run_app_cli(
        ["--data-root", str(root), "--port", "12345", "--no-open"],
        server_factory=_InterruptingServer,
        browser_open=lambda url: calls.append(url),
        managed_root_resolver=unexpected_resolver,
    ) == 0
    assert calls == []
    output = capsys.readouterr().out
    assert output.count("http://127.0.0.1:12345/?token=secret-token") == 1
    assert root.is_dir()


def test_app_cli_startup_and_serve_failures_close_server_exactly_once(
    tmp_path: Path,
    capsys,
) -> None:
    collision = tmp_path / "collision"
    collision.write_text("file", encoding="utf-8")
    assert app_cli.run_app_cli(
        ["--data-root", str(collision), "--no-open"],
        server_factory=_InterruptingServer,
    ) == 1
    assert "Error:" in capsys.readouterr().err

    class FailingServer(_InterruptingServer):
        def serve_forever(self) -> None:
            self.serve_count += 1
            raise OSError("serve failed")

    server = None

    def factory(context, *, port):
        nonlocal server
        server = FailingServer(context, port=port)
        return server

    assert app_cli.run_app_cli(
        ["--data-root", str(tmp_path / "managed"), "--no-open"],
        server_factory=factory,
    ) == 1
    assert server is not None and server.close_count == 1
    captured = capsys.readouterr()
    assert "Error: serve failed" in captured.err
    assert captured.out.endswith("SkatMind stopped.\n")


def test_startup_creates_no_product_files_or_identifiers(tmp_path: Path) -> None:
    root = tmp_path / "managed"
    assert app_cli.run_app_cli(
        ["--data-root", str(root), "--no-open"],
        server_factory=_InterruptingServer,
    ) == 0
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob("*")) == [
        "corpora",
        "matches",
        "sessions",
    ]
