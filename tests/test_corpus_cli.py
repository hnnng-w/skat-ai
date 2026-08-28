import argparse
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import main as legacy_main
import skatmind
import skatmind.cli.corpus as corpus_cli
import skatmind.cli.execution as root_cli
from skatmind.cli.corpus_parser import (
    LEARNING_CORPUS_CLI_COMMAND,
    LEARNING_CORPUS_CLI_VERSION,
    LEARNING_CORPUS_DEFAULT_PORT,
    build_corpus_argument_parser,
    parse_corpus_arguments,
)
from skatmind.errors import SkatMindError

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


def _install_corpus_web_modules(
    monkeypatch,
    *,
    context_open=None,
    default_server_factory=None,
) -> SimpleNamespace:
    state = SimpleNamespace(opened_paths=[], default_factory_calls=[])

    if context_open is None:

        def context_open(path):
            state.opened_paths.append(path)
            return SimpleNamespace(corpus_path=Path(path))

    class LearningCorpusWebContextV1:
        open = staticmethod(context_open)

    def start_learning_corpus_web_server_v1(context, *, port):
        state.default_factory_calls.append((context, port))
        if default_server_factory is None:
            raise AssertionError("Unexpected default Corpus server factory call.")
        return default_server_factory(context, port=port)

    package = ModuleType("skatmind.corpus_web")
    package.__path__ = []
    context_module = ModuleType("skatmind.corpus_web.context")
    context_module.LearningCorpusWebContextV1 = LearningCorpusWebContextV1
    server_module = ModuleType("skatmind.corpus_web.server")
    server_module.start_learning_corpus_web_server_v1 = start_learning_corpus_web_server_v1
    monkeypatch.setitem(sys.modules, "skatmind.corpus_web", package)
    monkeypatch.setitem(sys.modules, "skatmind.corpus_web.context", context_module)
    monkeypatch.setitem(sys.modules, "skatmind.corpus_web.server", server_module)
    monkeypatch.setattr(skatmind, "corpus_web", package, raising=False)
    return state


def test_corpus_cli_version_command_default_port_and_exact_options() -> None:
    assert LEARNING_CORPUS_CLI_VERSION == 1
    assert LEARNING_CORPUS_CLI_COMMAND == "corpus"
    assert LEARNING_CORPUS_DEFAULT_PORT == 8766
    parser = build_corpus_argument_parser()
    assert _actions(parser) == (
        (("-h", "--help"), "help", False, "==SUPPRESS==", 0),
        (("--corpus",), "corpus", True, None, None),
        (("--port",), "port", False, 8766, None),
        (("--no-open",), "no_open", False, False, 0),
    )
    option_strings = {option for action in parser._actions for option in action.option_strings}
    assert option_strings == {
        "-h",
        "--help",
        "--corpus",
        "--port",
        "--no-open",
    }


def test_corpus_parser_defaults_boundary_ports_no_open_and_invocation_identity() -> None:
    args = parse_corpus_arguments(["--corpus", "corpus"])
    assert vars(args) == {
        "corpus": "corpus",
        "port": 8766,
        "no_open": False,
    }
    for port in (1, 65_535):
        args = parse_corpus_arguments(
            ["--corpus", "corpus", "--port", str(port), "--no-open"],
            invocation_style="module",
        )
        assert vars(args) == {
            "corpus": "corpus",
            "port": port,
            "no_open": True,
        }
    assert build_corpus_argument_parser(invocation_style="installed").prog == ("skatmind corpus")
    assert build_corpus_argument_parser(invocation_style="module").prog == (
        "python -m skatmind corpus"
    )
    assert build_corpus_argument_parser(invocation_style="legacy").prog == ("python main.py corpus")


@pytest.mark.parametrize("port", ("0", "-1", "65536", "true", "1.5"))
def test_corpus_parser_rejects_invalid_explicit_port(port: str) -> None:
    with pytest.raises(SystemExit) as raised:
        parse_corpus_arguments(["--corpus", "corpus", "--port", port])
    assert raised.value.code == 2


@pytest.mark.parametrize(
    "argv",
    (
        [],
        ["--corpus"],
        ["--corpus", "corpus", "--host", "0.0.0.0"],
        ["--corpus", "corpus", "--root", "other"],
        ["--corpus", "corpus", "--generate"],
        ["--corpus", "corpus", "--force"],
        ["--corpus", "corpus", "--daemon"],
    ),
)
def test_corpus_parser_rejects_missing_or_unsupported_options(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        parse_corpus_arguments(argv)
    assert raised.value.code == 2


@pytest.mark.parametrize(
    ("command", "usage"),
    (
        ([sys.executable, "-m", "skatmind", "corpus", "--help"], "python -m skatmind corpus"),
        ([sys.executable, "main.py", "corpus", "--help"], "python main.py corpus"),
    ),
)
def test_module_and_legacy_corpus_help(command: list[str], usage: str) -> None:
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
    assert "--corpus PATH" in completed.stdout
    assert "--port INTEGER" in completed.stdout
    assert "--no-open" in completed.stdout
    for unsupported in ("--host", "--root", "--generate", "--force", "--daemon"):
        assert unsupported not in completed.stdout


def test_corpus_dispatch_precedes_capture_session_and_root(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        corpus_cli,
        "run_corpus_cli",
        lambda argv, *, invocation_style: calls.append((argv, invocation_style)) or 17,
    )
    assert (
        root_cli.run_cli(
            ["corpus", "--corpus", "corpus"],
            invocation_style="module",
        )
        == 17
    )
    assert calls == [(("--corpus", "corpus"), "module")]


def test_legacy_corpus_dispatch_uses_package_implementation_without_patching(
    monkeypatch,
) -> None:
    calls = []
    monkeypatch.setattr(
        corpus_cli,
        "run_corpus_cli",
        lambda argv, *, invocation_style: calls.append((argv, invocation_style)) or 0,
    )
    monkeypatch.setattr(
        root_cli,
        "legacy_patch_namespace",
        lambda _namespace: pytest.fail("Corpus dispatch must not patch the Legacy facade."),
    )
    assert (
        root_cli.run_cli(
            ["corpus", "--corpus", "corpus"],
            invocation_style="legacy",
            legacy_namespace=legacy_main,
        )
        == 0
    )
    assert calls == [(("--corpus", "corpus"), "legacy")]


class _InterruptingServer:
    def __init__(self, _context, *, port: int) -> None:
        assert port in {8766, 12345}
        self.bootstrap_url = f"http://127.0.0.1:{port}/?token=test"
        self.closed = False

    def serve_forever(self) -> None:
        raise KeyboardInterrupt

    def server_close(self) -> None:
        self.closed = True


def test_corpus_cli_startup_open_browser_interrupt_and_shutdown(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    servers = []

    def factory(context, *, port):
        server = _InterruptingServer(context, port=port)
        servers.append(server)
        return server

    state = _install_corpus_web_modules(
        monkeypatch,
        default_server_factory=factory,
    )
    opened = []
    corpus_path = tmp_path / "corpus"
    result = corpus_cli.run_corpus_cli(
        ["--corpus", str(corpus_path)],
        browser_open=lambda url: opened.append(url) or True,
    )
    assert result == 0
    assert state.opened_paths == [str(corpus_path)]
    assert state.default_factory_calls[0][1] == 8766
    assert opened == ["http://127.0.0.1:8766/?token=test"]
    assert len(servers) == 1 and servers[0].closed is True
    captured = capsys.readouterr()
    assert captured.out == ("Local Learning Corpus: http://127.0.0.1:8766/?token=test\n")
    assert not captured.err


def test_corpus_cli_no_open_and_browser_failure_warnings(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _install_corpus_web_modules(monkeypatch)
    opened = []
    corpus_path = tmp_path / "corpus"

    result = corpus_cli.run_corpus_cli(
        ["--corpus", str(corpus_path), "--no-open"],
        server_factory=_InterruptingServer,
        browser_open=lambda url: opened.append(url),
    )
    assert result == 0 and opened == []
    capsys.readouterr()

    result = corpus_cli.run_corpus_cli(
        ["--corpus", str(corpus_path)],
        server_factory=_InterruptingServer,
        browser_open=lambda _url: False,
    )
    assert result == 0
    assert "Warning: Could not open the browser." in capsys.readouterr().err

    def fail_to_open(_url):
        raise RuntimeError("browser unavailable")

    result = corpus_cli.run_corpus_cli(
        ["--corpus", str(corpus_path)],
        server_factory=_InterruptingServer,
        browser_open=fail_to_open,
    )
    assert result == 0
    assert "Warning: Could not open the browser." in capsys.readouterr().err


@pytest.mark.parametrize(
    "error",
    (
        SkatMindError("corpus unavailable"),
        TypeError("invalid corpus"),
        ValueError("invalid corpus"),
        OSError("corpus unavailable"),
    ),
)
def test_corpus_cli_context_open_failures_return_one(
    error: Exception,
    monkeypatch,
    capsys,
) -> None:
    def fail_to_open(_path):
        raise error

    _install_corpus_web_modules(monkeypatch, context_open=fail_to_open)
    assert corpus_cli.run_corpus_cli(["--corpus", "corpus", "--no-open"]) == 1
    assert capsys.readouterr().err == f"Error: {error}\n"


def test_corpus_cli_server_failure_returns_one_and_server_errors_still_close(
    monkeypatch,
    capsys,
) -> None:
    _install_corpus_web_modules(monkeypatch)

    def fail_to_start(_context, *, port):
        assert port == 8766
        raise OSError("bind failed")

    assert (
        corpus_cli.run_corpus_cli(
            ["--corpus", "corpus", "--no-open"],
            server_factory=fail_to_start,
        )
        == 1
    )
    assert capsys.readouterr().err == "Error: bind failed\n"

    class FailingServer(_InterruptingServer):
        def serve_forever(self) -> None:
            raise ValueError("serve failed")

    server = None

    def factory(context, *, port):
        nonlocal server
        server = FailingServer(context, port=port)
        return server

    assert (
        corpus_cli.run_corpus_cli(
            ["--corpus", "corpus", "--no-open"],
            server_factory=factory,
        )
        == 1
    )
    assert server is not None and server.closed is True
    assert capsys.readouterr().err == "Error: serve failed\n"


def test_corpus_server_factory_receives_opened_context_and_explicit_port(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _install_corpus_web_modules(monkeypatch)
    captured = SimpleNamespace()

    def factory(context, *, port):
        captured.context = context
        captured.port = port
        return _InterruptingServer(context, port=port)

    corpus_path = tmp_path / "corpus"
    assert (
        corpus_cli.run_corpus_cli(
            [
                "--corpus",
                str(corpus_path),
                "--port",
                "12345",
                "--no-open",
            ],
            server_factory=factory,
        )
        == 0
    )
    assert captured.port == 12345
    assert captured.context.corpus_path == corpus_path
