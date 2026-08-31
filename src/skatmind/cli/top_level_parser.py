"""Lightweight top-level dispatch classification and Product help parsing."""

from __future__ import annotations

import argparse
import sys

from skatmind import __version__
from skatmind.cli.onboarding_contracts import ADVANCED_COMMAND_FAMILIES
from skatmind.cli.top_level_help import (
    build_top_level_description,
    build_top_level_epilog,
)
from skatmind.errors import CLI_EXIT_CODE_SUCCESS, CLI_EXIT_CODE_USAGE

_INVOCATION_COMMANDS = {
    "installed": "skatmind",
    "module": "python -m skatmind",
    "legacy": "python main.py",
}

TOP_LEVEL_DISPATCH_APP = "app"
TOP_LEVEL_DISPATCH_RUN = "run"
TOP_LEVEL_DISPATCH_SESSION = "session"
TOP_LEVEL_DISPATCH_CAPTURE = "capture"
TOP_LEVEL_DISPATCH_CORPUS = "corpus"
TOP_LEVEL_DISPATCH_HELP = "help"
TOP_LEVEL_DISPATCH_VERSION = "version"
TOP_LEVEL_DISPATCH_ROOT_COMPATIBILITY = "root_compatibility"
TOP_LEVEL_DISPATCH_UNKNOWN_COMMAND = "unknown_command"


def _invocation_command(invocation_style: str) -> str:
    try:
        return _INVOCATION_COMMANDS[invocation_style]
    except KeyError as error:
        raise ValueError(
            f"invocation_style must be one of {tuple(_INVOCATION_COMMANDS)}."
        ) from error


def classify_top_level_argv(argv: tuple[str, ...]) -> str:
    """Classifies argv without importing or executing a Product command family."""

    if not argv or argv[0] == ADVANCED_COMMAND_FAMILIES[0]:
        return TOP_LEVEL_DISPATCH_APP
    first = argv[0]
    if first == ADVANCED_COMMAND_FAMILIES[1]:
        return TOP_LEVEL_DISPATCH_RUN
    if first == ADVANCED_COMMAND_FAMILIES[2]:
        return TOP_LEVEL_DISPATCH_SESSION
    if first == ADVANCED_COMMAND_FAMILIES[3]:
        return TOP_LEVEL_DISPATCH_CAPTURE
    if first == ADVANCED_COMMAND_FAMILIES[4]:
        return TOP_LEVEL_DISPATCH_CORPUS
    if first in {"-h", "--help"}:
        return TOP_LEVEL_DISPATCH_HELP
    if first == "--version":
        return TOP_LEVEL_DISPATCH_VERSION
    if first.startswith("-"):
        return TOP_LEVEL_DISPATCH_ROOT_COMPATIBILITY
    return TOP_LEVEL_DISPATCH_UNKNOWN_COMMAND


def build_top_level_argument_parser(
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    """Builds concise Product help with no Root option inventory."""

    command = _invocation_command(invocation_style)
    parser = argparse.ArgumentParser(
        prog=command,
        usage=f"{command} [-h] [--version] [COMMAND]",
        description=build_top_level_description(command),
        epilog=build_top_level_epilog(command),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    common = parser.add_argument_group("Common options")
    common.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this Product-oriented help and exit.",
    )
    common.add_argument(
        "--version",
        action="version",
        version=f"SkatMind {__version__}",
        help="Show the installed SkatMind Package version and exit.",
    )
    return parser


def run_top_level_help_or_version(
    argv: tuple[str, ...],
    *,
    invocation_style: str,
) -> int:
    """Runs only argparse help or version actions."""

    build_top_level_argument_parser(invocation_style).parse_args(argv)
    return CLI_EXIT_CODE_SUCCESS


def report_unknown_top_level_command(
    command_name: str,
    *,
    invocation_style: str,
) -> int:
    """Reports one concise top-level command error without Root initialization."""

    command = _invocation_command(invocation_style)
    print(f"usage: {command} [-h] [--version] [COMMAND]", file=sys.stderr)
    print(
        f"{command}: error: unknown command {command_name!r}. "
        f"Run '{command} --help' for available commands.",
        file=sys.stderr,
    )
    return CLI_EXIT_CODE_USAGE
