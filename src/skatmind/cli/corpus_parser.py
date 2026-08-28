from __future__ import annotations

import argparse

LEARNING_CORPUS_CLI_VERSION = 1
LEARNING_CORPUS_CLI_COMMAND = "corpus"
LEARNING_CORPUS_DEFAULT_PORT = 8766

_CLI_INVOCATION_COMMANDS = {
    "installed": "skatmind corpus",
    "module": "python -m skatmind corpus",
    "legacy": "python main.py corpus",
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


def build_corpus_argument_parser(
    *,
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_invocation_command(invocation_style),
        description="Open one private local Learning Corpus in a browser.",
    )
    parser.add_argument(
        "--corpus",
        required=True,
        metavar="PATH",
        help="Explicit private Learning Corpus directory.",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=LEARNING_CORPUS_DEFAULT_PORT,
        metavar="INTEGER",
        help=(f"Loopback port from 1 through 65535; default {LEARNING_CORPUS_DEFAULT_PORT}."),
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the local URL in the default browser.",
    )
    return parser


def parse_corpus_arguments(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> argparse.Namespace:
    return build_corpus_argument_parser(invocation_style=invocation_style).parse_args(argv)
