from __future__ import annotations

import argparse

MATCH_CAPTURE_CLI_VERSION = 1
MATCH_CAPTURE_CLI_COMMAND = "capture"

_CLI_INVOCATION_COMMANDS = {
    "installed": "skatmind capture",
    "module": "python -m skatmind capture",
    "legacy": "python main.py capture",
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
    if not 1 <= port <= 65_535:
        raise argparse.ArgumentTypeError("port must be from 1 through 65535.")
    return port


def build_capture_argument_parser(
    *,
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_invocation_command(invocation_style),
        description=(
            "Capture one EuroSkat 36er Standard Match in a private local browser."
        ),
    )
    parser.add_argument(
        "--workspace",
        required=True,
        metavar="PATH",
        help="Explicit private Match Workspace file.",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=0,
        metavar="INTEGER",
        help="Loopback port from 1 through 65535; default 0 selects a free port.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the local URL in the default browser.",
    )
    return parser


def parse_capture_arguments(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> argparse.Namespace:
    return build_capture_argument_parser(
        invocation_style=invocation_style
    ).parse_args(argv)
