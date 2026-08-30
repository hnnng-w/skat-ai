"""Lightweight command-family selection for installed and module startup."""

import sys
from types import ModuleType


def run_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
    legacy_namespace: ModuleType | None = None,
) -> int:
    """Routes the shell without importing the broad Root compatibility facade."""

    dispatch_argv = tuple(sys.argv[1:] if argv is None else argv)
    if not dispatch_argv or dispatch_argv[:1] == ("app",):
        from skatmind.cli.app import run_app_cli

        return run_app_cli(
            dispatch_argv if not dispatch_argv else dispatch_argv[1:],
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
