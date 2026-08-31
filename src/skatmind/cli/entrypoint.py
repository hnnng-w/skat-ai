"""Lightweight command-family selection for installed and module startup."""

import sys
from types import ModuleType

from skatmind.cli.top_level_parser import (
    TOP_LEVEL_DISPATCH_APP,
    TOP_LEVEL_DISPATCH_HELP,
    TOP_LEVEL_DISPATCH_UNKNOWN_COMMAND,
    TOP_LEVEL_DISPATCH_VERSION,
    classify_top_level_argv,
    report_unknown_top_level_command,
    run_top_level_help_or_version,
)


def run_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
    legacy_namespace: ModuleType | None = None,
) -> int:
    """Routes the shell without importing the broad Root compatibility facade."""

    dispatch_argv = tuple(sys.argv[1:] if argv is None else argv)
    dispatch = classify_top_level_argv(dispatch_argv)
    if dispatch == TOP_LEVEL_DISPATCH_APP:
        from skatmind.cli.app import run_app_cli

        return run_app_cli(
            dispatch_argv if not dispatch_argv else dispatch_argv[1:],
            invocation_style=invocation_style,
        )
    if dispatch in {TOP_LEVEL_DISPATCH_HELP, TOP_LEVEL_DISPATCH_VERSION}:
        return run_top_level_help_or_version(
            dispatch_argv,
            invocation_style=invocation_style,
        )
    if dispatch == TOP_LEVEL_DISPATCH_UNKNOWN_COMMAND:
        return report_unknown_top_level_command(
            dispatch_argv[0],
            invocation_style=invocation_style,
        )

    from skatmind.cli.execution import run_cli as run_technical_cli

    return run_technical_cli(
        argv,
        invocation_style=invocation_style,
        legacy_namespace=legacy_namespace,
    )


def main() -> int:
    """Runs the installed ``skatmind`` Console Script."""

    return run_cli(invocation_style="installed")
