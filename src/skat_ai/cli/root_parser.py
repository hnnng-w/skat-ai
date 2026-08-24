"""Argument parsing for the package-owned Root CLI."""

import argparse

from skat_ai import __version__
from skat_ai.card_selection import VALID_MULTI_STEP_POLICIES
from skat_ai.opponent_policy import VALID_OPPONENT_CARD_POLICIES
from skat_ai.search_budget_profiles import SEARCH_BUDGET_PROFILE_IDENTIFIERS

INSTALLED_CLI_CONTRACT_VERSION = 1
INSTALLED_CLI_COMMAND = "skat-ai"
MODULE_CLI_COMMAND = "python -m skat_ai"
LEGACY_CLI_COMMAND = "python main.py"
CLI_INVOCATION_STYLES = ("installed", "module", "legacy")


def _invocation_command(invocation_style: str) -> str:
    commands = {
        "installed": INSTALLED_CLI_COMMAND,
        "module": MODULE_CLI_COMMAND,
        "legacy": LEGACY_CLI_COMMAND,
    }
    try:
        return commands[invocation_style]
    except KeyError as error:
        raise ValueError(f"invocation_style must be one of {CLI_INVOCATION_STYLES}.") from error


def _invocation_examples(invocation_style: str) -> str:
    command = _invocation_command(invocation_style)
    if invocation_style == "legacy":
        paths = {
            "position": "examples/grand_second_position.json",
            "historical": "examples/historical_grand_normal_completion.json",
            "list": "examples/fixed_three_player_historical_list_mixed.json",
            "comparison": "examples/fixed_three_player_historical_list_comparison.json",
            "dataset": "examples/training_dataset_normal_play.json",
            "preparation": "examples/training_dataset_preparation_known_opponent.json",
            "statistics": "examples/opponent_statistics.json",
        }
    else:
        paths = {
            "position": "position.json",
            "historical": "historical-game.json",
            "list": "historical-list.json",
            "comparison": "historical-list-comparison.json",
            "dataset": "training-dataset.json",
            "preparation": "training-dataset-preparation.json",
            "statistics": "opponent-statistics.json",
        }
    return (
        "Examples:\n"
        f"  {command}\n"
        f"  {command} --input {paths['position']}\n"
        f"  {command} --input {paths['position']} --multi-step 2\n"
        f"  {command} --input {paths['position']} --multi-step 1 --compare-policies\n"
        f"  {command} --input {paths['position']} --multi-step 1 "
        "--compare-policies --comparison-only\n"
        f"  {command} --input {paths['historical']}\n"
        f"  {command} --input {paths['list']}\n"
        f"  {command} --input {paths['comparison']}\n"
        f"  {command} --input {paths['dataset']}\n"
        f"  {command} --input {paths['preparation']}\n"
        f"  {command} --input {paths['statistics']}"
    )


def build_argument_parser(
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    command = _invocation_command(invocation_style)
    parser = argparse.ArgumentParser(
        prog=command,
        description=(
            "Analyze a Skat position, replay a historical game, expose a complete "
            "historical 36-position list or independent-list comparison, prepare or "
            "convert a training dataset, or normalize opponent statistics from JSON."
        ),
        epilog=_invocation_examples(invocation_style),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"skat-ai {__version__}",
        help="Show the installed skat-ai Package version and exit.",
    )

    parser.add_argument(
        "--input",
        default="input_position.json",
        help=(
            "Read position-analysis, historical-game, historical-list, "
            "historical-list-comparison, training-dataset-preparation, training-dataset, "
            "or opponent-statistics input from this JSON file. "
            "Default: input_position.json."
        ),
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Override the JSON sample_count for Monte Carlo card analysis.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override the JSON random_seed for reproducible analysis.",
    )

    parser.add_argument(
        "--opponent-strategy",
        choices=["basic", "random"],
        default=None,
        help="Override legacy opponent strategy from the JSON input file.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Write the structured analysis result JSON to this path.",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress successful human-readable stdout output.",
    )

    parser.add_argument(
        "--include-provenance",
        action="store_true",
        help="Include a public-safe field-provenance sidecar in Root JSON output.",
    )

    parser.add_argument(
        "--audit-dataset-partitions",
        action="store_true",
        help="Audit exact stable-player membership and overlap across dataset partitions.",
    )
    parser.add_argument(
        "--dataset-partition-mode",
        choices=("report_only", "known_opponent", "unseen_player"),
        default=None,
        help="Evaluate the partition audit under this explicit policy mode.",
    )
    parser.add_argument(
        "--aggregate-opponent-statistics",
        action="store_true",
        help="Aggregate exact reusable opponent statistics from a training dataset.",
    )
    parser.add_argument(
        "--opponent-statistics-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Include this training-dataset partition; may be repeated.",
    )
    parser.add_argument(
        "--opponent-statistics-before",
        default=None,
        help="Include only games with played_at strictly before this RFC 3339 instant.",
    )
    parser.add_argument(
        "--export-opponent-statistics",
        default=None,
        help="Write a standalone reusable opponent_statistics_input JSON file.",
    )
    parser.add_argument(
        "--evaluate-opponent-policy-profiles",
        "--evaluate-rolling-opponent-policies",
        action="store_true",
        help="Evaluate rolling as-of profile policies against simple_lowest.",
    )
    parser.add_argument(
        "--profile-source-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Select a profile-history source partition; may be repeated.",
    )
    parser.add_argument(
        "--profile-evaluation-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Select a policy-evaluation target partition; may be repeated.",
    )

    parser.add_argument(
        "--historical-decision-snapshots",
        action="store_true",
        help=("Add one information-safe pre-play snapshot per supplied historical play."),
    )

    parser.add_argument(
        "--historical-game-review",
        action="store_true",
        help=("Evaluate every supplied historical card decision with decision-time information."),
    )
    parser.add_argument(
        "--historical-search-review",
        action="store_true",
        help="Evaluate every historical decision with bounded Search and Immediate.",
    )
    parser.add_argument(
        "--historical-information-set-search-review",
        action="store_true",
        help=(
            "Evaluate every historical decision with bounded Information-set Search, "
            "same-selection Search, and Immediate."
        ),
    )
    parser.add_argument(
        "--historical-information-set-replay-coaching",
        action="store_true",
        help=(
            "Build Information-set Replay Coaching from complete Information-set "
            "Search evidence without PIMC or Immediate fallback."
        ),
    )
    parser.add_argument(
        "--historical-replay-coaching",
        action="store_true",
        help="Build the complete Replay Coaching Report for a historical game.",
    )
    parser.add_argument(
        "--historical-tactical-motif-review",
        action="store_true",
        help=(
            "Add deterministic structural observations for every recorded "
            "historical Card play."
        ),
    )
    parser.add_argument(
        "--search-seed",
        type=int,
        default=None,
        help=(
            "Use this explicit base seed for Historical Search Review, Information-set "
            "Search Review, either Replay Coaching family, or evaluation."
        ),
    )
    parser.add_argument(
        "--search-budget-profile",
        choices=SEARCH_BUDGET_PROFILE_IDENTIFIERS,
        default=None,
        help=(
            "Select a versioned Historical Search Review, Information-set Search Review, "
            "either Replay Coaching family, or evaluation budget profile."
        ),
    )
    parser.add_argument(
        "--evaluate-bounded-search",
        action="store_true",
        help="Evaluate bounded Search against Immediate on a training dataset.",
    )
    parser.add_argument(
        "--information-set-search-evaluation",
        action="store_true",
        help=(
            "Evaluate Information-set Search against same-selection Search and Immediate "
            "on a training dataset."
        ),
    )
    parser.add_argument(
        "--search-evaluation-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Select a Search evaluation partition; may be repeated.",
    )
    parser.add_argument(
        "--search-evaluation-max-decisions",
        type=int,
        default=None,
        help="Evaluate only this deterministic prefix of selected Search decisions.",
    )

    parser.add_argument(
        "--multi-step",
        type=int,
        default=None,
        help="Run a phase-aware simulation for this many local decision steps.",
    )

    parser.add_argument(
        "--card-policy",
        choices=VALID_MULTI_STEP_POLICIES,
        default=None,
        help=(
            "Choose local cards during multi-step simulation. Search policies require "
            "matching JSON recommendation settings; otherwise the default is first_legal."
        ),
    )

    parser.add_argument(
        "--expected-value-samples",
        type=int,
        default=None,
        help=("Samples per candidate for the highest_expected_value card policy. Default: 100."),
    )

    parser.add_argument(
        "--strict-context",
        action="store_true",
        help=(
            "Fail multi-step simulation on duplicate cards, ownership drift, "
            "or hidden-world accounting violations."
        ),
    )

    parser.add_argument(
        "--compare-policies",
        action="store_true",
        help=(
            "Compare the four legacy local policies and append the configured Search "
            "method when present."
        ),
    )

    parser.add_argument(
        "--comparison-only",
        action="store_true",
        help="Print only policy comparison details; requires --compare-policies.",
    )

    parser.add_argument(
        "--opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help="Set both opponents' lead policy for multi-step simulation.",
    )

    parser.add_argument(
        "--opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Set both opponents' response policy for immediate analysis and multi-step simulation."
        ),
    )

    parser.add_argument(
        "--opponent-policy-preset",
        choices=[
            "simple_lowest",
            "cautious_defender",
            "aggressive_points",
            "random",
        ],
        default=None,
        help=("Apply an opponent policy preset to immediate analysis and multi-step simulation."),
    )

    parser.add_argument(
        "--use-profile-presets",
        action="store_true",
        help=(
            "Use player profiles to derive opponent policy presets for immediate "
            "analysis and multi-step simulation."
        ),
    )

    parser.add_argument(
        "--opponent-statistics-file",
        default=None,
        help=(
            "Attach validated external opponent statistics to a live position or "
            "time-safe historical game review."
        ),
    )
    parser.add_argument(
        "--left-opponent-player-id",
        default=None,
        help="Bind this exact external player ID to the left opponent.",
    )
    parser.add_argument(
        "--right-opponent-player-id",
        default=None,
        help="Bind this exact external player ID to the right opponent.",
    )

    parser.add_argument(
        "--left-opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help="Override only left opponent's lead policy for multi-step simulation.",
    )
    parser.add_argument(
        "--left-opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Override only left opponent's response policy for immediate analysis "
            "and multi-step simulation."
        ),
    )
    parser.add_argument(
        "--right-opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help="Override only right opponent's lead policy for multi-step simulation.",
    )
    parser.add_argument(
        "--right-opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Override only right opponent's response policy for immediate analysis "
            "and multi-step simulation."
        ),
    )

    return parser


def parse_arguments(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> argparse.Namespace:
    return build_argument_parser(invocation_style).parse_args(argv)
