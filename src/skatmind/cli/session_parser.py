from __future__ import annotations

import argparse

import skatmind.api.v1.session as session_api
from skatmind.input_validation import MAX_SAMPLE_COUNT
from skatmind.recommendation_workflow import (
    SEARCH_RECOMMENDATION_METHODS,
    VALID_RECOMMENDATION_METHODS,
    RecommendationMethodConfiguration,
    build_serializable_bounded_search_settings,
)
from skatmind.search_budget_profiles import (
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    INTERACTIVE_SEARCH_BUDGET_PROFILE,
    SEARCH_BUDGET_PROFILE_IDENTIFIERS,
    get_search_budget_profile,
)
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

CLI_INVOCATION_STYLES = ("installed", "module", "legacy")
SESSION_CLI_CONTRACT_VERSION = 1
SESSION_CLI_COMMAND = "session"
SESSION_CLI_SUBCOMMANDS = (
    "new",
    "show",
    "apply",
    "undo",
    "correct",
    "checkpoint",
    "export-position",
    "export-historical",
    "analyze",
    "review",
    "finalize",
    "assistant",
)
SESSION_CLI_PERSISTENCE_POLICY = "load_operate_compare_and_swap_save"
SESSION_CLI_ANALYSIS_POLICY = "export_then_existing_application_once"
SESSION_CLI_AUTOMATIC_CHECKPOINT_POLICY = "collect_without_automatic_analysis"


def _invocation_command(invocation_style: str) -> str:
    commands = {
        "installed": "skatmind",
        "module": "python -m skatmind",
        "legacy": "python main.py",
    }
    try:
        return commands[invocation_style]
    except KeyError as error:
        raise ValueError(
            f"invocation_style must be one of {list(CLI_INVOCATION_STYLES)}."
        ) from error


def _positive_sample_count(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if not 1 <= parsed <= MAX_SAMPLE_COUNT:
        raise argparse.ArgumentTypeError(
            f"must be from 1 through {MAX_SAMPLE_COUNT}"
        )
    return parsed


def _non_negative_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _add_common_options(
    parser: argparse.ArgumentParser,
    *,
    output_required: bool = False,
    include_provenance: bool = True,
) -> None:
    parser.add_argument(
        "--session",
        required=True,
        help="Read or write this explicit private Session JSON file.",
    )
    parser.add_argument(
        "--output",
        required=output_required,
        default=None,
        help="Write only the requested operation or Engine Result JSON here.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress successful human-readable output.",
    )
    if include_provenance:
        parser.add_argument(
            "--include-provenance",
            action="store_true",
            help="Include public-safe provenance in the requested JSON result.",
        )


def _add_position_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--samples",
        type=_positive_sample_count,
        default=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        help="Use this deterministic Position sample count.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Use this deterministic Position random seed.",
    )
    parser.add_argument(
        "--opponent-strategy",
        choices=("basic", "random"),
        default="basic",
        help="Use the basic or random legacy opponent strategy.",
    )
    parser.add_argument(
        "--recommendation-method",
        choices=VALID_RECOMMENDATION_METHODS,
        default=None,
        help="Select an explicit Position recommendation method.",
    )
    parser.add_argument(
        "--search-budget-profile",
        choices=SEARCH_BUDGET_PROFILE_IDENTIFIERS,
        default=INTERACTIVE_SEARCH_BUDGET_PROFILE,
        help="Use this versioned bounded-Search budget when Search is requested.",
    )


def _add_historical_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--historical-decision-snapshots",
        action="store_true",
        help="Add information-safe Historical decision snapshots.",
    )
    parser.add_argument(
        "--historical-game-review",
        action="store_true",
        help="Run Immediate Historical decision review.",
    )
    parser.add_argument(
        "--historical-search-review",
        action="store_true",
        help="Run bounded-Search Historical decision review.",
    )
    parser.add_argument(
        "--historical-replay-coaching",
        action="store_true",
        help="Build the Historical Replay Coaching Report.",
    )
    parser.add_argument(
        "--search-seed",
        type=int,
        default=None,
        help="Use this explicit Historical Search base seed.",
    )
    parser.add_argument(
        "--search-budget-profile",
        choices=SEARCH_BUDGET_PROFILE_IDENTIFIERS,
        default=HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
        help="Use this versioned Historical Search budget.",
    )
    parser.add_argument(
        "--samples",
        type=_positive_sample_count,
        default=None,
        help="Use this Immediate Historical review sample count.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Use this Immediate Historical review base random seed.",
    )


def build_session_argument_parser(
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    command = _invocation_command(invocation_style)
    parser = argparse.ArgumentParser(
        prog=f"{command} {SESSION_CLI_COMMAND}",
        description=(
            "Create, edit, inspect, export, analyze, and review one explicit "
            "private Skat Session file."
        ),
    )
    subparsers = parser.add_subparsers(
        dest="session_subcommand",
        required=True,
    )

    new = subparsers.add_parser("new", help="Create one new Session file.")
    _add_common_options(new)
    new.add_argument("--input", required=True, help="Read strict Session creation JSON.")

    show = subparsers.add_parser("show", help="Show privacy-safe Session status.")
    _add_common_options(show, include_provenance=False)

    apply = subparsers.add_parser("apply", help="Apply one strict Session Command.")
    _add_common_options(apply)
    apply.add_argument("--input", required=True, help="Read one Session Command JSON object.")
    _add_position_options(apply)

    undo = subparsers.add_parser("undo", help="Rewind to one strict-prefix revision.")
    _add_common_options(undo)
    undo.add_argument(
        "--target-revision",
        required=True,
        type=_non_negative_integer,
        help="Retain exactly this accepted revision prefix.",
    )
    _add_position_options(undo)

    correct = subparsers.add_parser("correct", help="Correct one accepted Command.")
    _add_common_options(correct)
    correct.add_argument(
        "--input",
        required=True,
        help="Read one strict Session Command Correction JSON object.",
    )
    _add_position_options(correct)

    checkpoint = subparsers.add_parser(
        "checkpoint",
        help="Collect or reuse the current exact Decision Checkpoint.",
    )
    _add_common_options(checkpoint)
    _add_position_options(checkpoint)

    export_position = subparsers.add_parser(
        "export-position",
        help="Export one information-safe Position Request without analysis.",
    )
    _add_common_options(export_position, output_required=True)
    _add_position_options(export_position)

    export_historical = subparsers.add_parser(
        "export-historical",
        help="Export one complete Historical Request without execution.",
    )
    _add_common_options(export_historical, output_required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze one Position-ready Session through the existing Application.",
    )
    _add_common_options(analyze, output_required=True)
    _add_position_options(analyze)

    review = subparsers.add_parser(
        "review",
        help="Review one observed frozen Decision Checkpoint.",
    )
    _add_common_options(review, output_required=True)
    review.add_argument(
        "--checkpoint-index",
        required=True,
        type=_non_negative_integer,
        help="Select one zero-based canonical Checkpoint index.",
    )

    finalize = subparsers.add_parser(
        "finalize",
        help="Execute one Historical-ready Session through the existing Application.",
    )
    _add_common_options(finalize, output_required=True)
    _add_historical_options(finalize)

    assistant = subparsers.add_parser(
        "assistant",
        help="Run the deterministic phase-aware interactive Session Assistant.",
    )
    assistant.add_argument(
        "--session",
        required=True,
        help="Read or write this explicit private Session JSON file.",
    )

    return parser


def parse_session_arguments(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> argparse.Namespace:
    return build_session_argument_parser(invocation_style).parse_args(argv)


def position_export_options(
    args: argparse.Namespace,
) -> session_api.SessionPositionExportOptionsV1:
    bounded_search_settings = None
    if args.recommendation_method in SEARCH_RECOMMENDATION_METHODS:
        bounded_search_settings = build_serializable_bounded_search_settings(
            RecommendationMethodConfiguration(
                explicitly_supplied=True,
                requested_method=args.recommendation_method,
                search_random_seed=args.seed,
                requested_search_budget=get_search_budget_profile(
                    args.search_budget_profile
                ),
            )
        )
    return session_api.SessionPositionExportOptionsV1(
        sample_count=args.samples,
        random_seed=args.seed,
        use_basic_opponent_strategy=args.opponent_strategy == "basic",
        recommendation_method=args.recommendation_method,
        bounded_search_settings=bounded_search_settings,
    )


_position_export_options = position_export_options
