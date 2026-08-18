"""Compatibility facade for the package-owned Root CLI.

The focused Root modules own parsing, validation, Application adaptation,
dispatch, transport, and presentation. This module intentionally keeps the
historically broad import namespace used by repository-root ``main.py`` and
established monkeypatch seams.
"""

import sys
from types import ModuleType

from skat_ai.cli.presentation.common import *  # noqa: F403
from skat_ai.cli.presentation.dataset import *  # noqa: F403
from skat_ai.cli.presentation.historical import *  # noqa: F403
from skat_ai.cli.presentation.historical import (  # noqa: F401
    _print_historical_continuation_event,
)
from skat_ai.cli.presentation.historical_lists import *  # noqa: F403
from skat_ai.cli.presentation.historical_lists import (
    _format_list_player_identity,  # noqa: F401
    _print_comparison_source_summary,  # noqa: F401
)
from skat_ai.cli.presentation.opponent_statistics import *  # noqa: F403
from skat_ai.cli.presentation.position import *  # noqa: F403
from skat_ai.cli.presentation.provenance import *  # noqa: F403
from skat_ai.cli.presentation.simulation import *  # noqa: F403
from skat_ai.cli.root_application import *  # noqa: F403
from skat_ai.cli.root_compatibility import *  # noqa: F403
from skat_ai.cli.root_compatibility import (
    _DEFAULT_LEGACY_PATCH_VALUES,  # noqa: F401
    _LEGACY_PATCH_POINT_FUNCTIONS,  # noqa: F401
    _active_legacy_patch_namespace,  # noqa: F401
    _facade_value,  # noqa: F401
    _has_active_legacy_patch_namespace,  # noqa: F401
    _legacy_patch_value,  # noqa: F401
)
from skat_ai.cli.root_dispatch import *  # noqa: F403
from skat_ai.cli.root_dispatch import _run_cli
from skat_ai.cli.root_parser import *  # noqa: F403
from skat_ai.cli.root_parser import (  # noqa: F401
    _invocation_command,
    _invocation_examples,
)
from skat_ai.cli.root_transport import *  # noqa: F403
from skat_ai.cli.root_validation import *  # noqa: F403


def run_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
    legacy_namespace: ModuleType | None = None,
) -> int:
    """Runs one argv-capable CLI invocation using the selected command identity."""
    _invocation_command(invocation_style)
    dispatch_argv = tuple(sys.argv[1:] if argv is None else argv)
    if dispatch_argv[:1] == ("corpus",):
        from skat_ai.cli.corpus import run_corpus_cli

        return run_corpus_cli(
            dispatch_argv[1:],
            invocation_style=invocation_style,
        )
    if dispatch_argv[:1] == ("capture",):
        from skat_ai.cli.capture import run_capture_cli

        return run_capture_cli(
            dispatch_argv[1:],
            invocation_style=invocation_style,
        )
    if dispatch_argv[:1] == ("session",):
        from skat_ai.cli.session import run_session_cli

        session_argv = dispatch_argv[1:]
        if legacy_namespace is None:
            return run_session_cli(session_argv, invocation_style=invocation_style)
        with legacy_patch_namespace(legacy_namespace):  # noqa: F405
            return run_session_cli(session_argv, invocation_style=invocation_style)
    if legacy_namespace is None:
        return _run_cli(argv, invocation_style)
    with legacy_patch_namespace(legacy_namespace):  # noqa: F405
        return _run_cli(argv, invocation_style)


def main() -> int:
    """Runs the installed ``skat-ai`` Console Script."""
    return run_cli(invocation_style="installed")
