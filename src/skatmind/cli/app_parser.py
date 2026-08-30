from __future__ import annotations

import argparse

from skatmind.app_web.contracts import LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION  # noqa: F401

APP_CLI_COMMAND = "app"

_CLI_INVOCATION_COMMANDS = {
    "installed": "skatmind app",
    "module": "python -m skatmind app",
    "legacy": "python main.py app",
}


def _invocation_command(invocation_style: str) -> str:
    try:
        return _CLI_INVOCATION_COMMANDS[invocation_style]
    except KeyError as error:
        raise ValueError(
            f"invocation_style must be one of {list(_CLI_INVOCATION_COMMANDS)}."
        ) from error


def _port(value: str) -> int:
    if not isinstance(value, str):
        raise argparse.ArgumentTypeError("port must be an integer.")
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be an integer.") from error
    if not 0 <= port <= 65_535:
        raise argparse.ArgumentTypeError("port must be 0 or from 1 through 65535.")
    return port


def build_app_argument_parser(
    *,
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_invocation_command(invocation_style),
        description="Open the unified local SkatMind application shell.",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        metavar="PATH",
        help="Advanced override for the managed local data root.",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=0,
        metavar="INTEGER",
        help="Loopback port 0 or from 1 through 65535; default 0 selects a free port.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the local application in the default browser.",
    )
    return parser


def parse_app_arguments(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> argparse.Namespace:
    return build_app_argument_parser(
        invocation_style=invocation_style
    ).parse_args(argv)
