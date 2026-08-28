"""Legacy repository CLI compatibility facade.

The canonical implementation is package-owned under :mod:`skatmind.cli`.
"""

import sys
from functools import wraps

from skatmind.cli import execution as _cli
from skatmind.cli.execution import *  # noqa: F403

_LEGACY_PATCH_POINT_FUNCTIONS = _cli._LEGACY_PATCH_POINT_FUNCTIONS
_format_list_player_identity = _cli._format_list_player_identity
_print_comparison_source_summary = _cli._print_comparison_source_summary
_print_historical_continuation_event = _cli._print_historical_continuation_event


def _legacy_delegate(function):
    @wraps(function)
    def delegated(*args, **kwargs):
        with _cli.legacy_patch_namespace(sys.modules[__name__]):
            return function(*args, **kwargs)

    return delegated


for _name in (
    "build_legacy_application_dependencies",
    "execute_legacy_application",
    "load_external_opponent_statistics_document",
    "build_analysis_result",
    "run_json_position_analysis",
    "run_json_historical_game_analysis",
    "run_json_training_dataset_conversion",
    "run_json_training_dataset_preparation",
    "run_json_bounded_search_evaluation",
    "run_json_dataset_partition_audit",
    "run_json_rolling_opponent_policy_evaluation",
    "run_json_historical_opponent_statistics_aggregation",
    "run_json_fixed_three_player_historical_list_analysis",
    "run_json_fixed_three_player_historical_list_comparison",
    "run_json_opponent_statistics_conversion",
):
    globals()[_name] = _legacy_delegate(getattr(_cli, _name))


def parse_arguments() -> argparse.Namespace:  # noqa: F405
    """Parses arguments using the legacy repository invocation identity."""
    return _cli.parse_arguments(invocation_style="legacy")


def main() -> int:
    """Runs the canonical CLI through the established Root patch namespace."""
    return _cli.run_cli(
        invocation_style="legacy",
        legacy_namespace=sys.modules[__name__],
    )


if __name__ == "__main__":
    raise SystemExit(main())
