"""Canonical advanced Root JSON automation command."""

from __future__ import annotations

from types import ModuleType

from skatmind.cli.root_compatibility import legacy_patch_namespace
from skatmind.cli.root_dispatch import _run_cli


def run_root_automation_cli(
    argv: list[str] | tuple[str, ...],
    *,
    invocation_style: str,
    legacy_namespace: ModuleType | None = None,
) -> int:
    """Runs the shared Root implementation in explicit-input automation mode."""

    if legacy_namespace is None:
        return _run_cli(argv, invocation_style, parser_mode="run")
    with legacy_patch_namespace(legacy_namespace):
        return _run_cli(argv, invocation_style, parser_mode="run")
