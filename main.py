import argparse
import sys
from pathlib import Path
from typing import Any

from skat_ai.analysis_metadata import build_serializable_analysis_metadata
from skat_ai.analysis_report import (
    build_card_analysis_report,
    build_strategic_summary,
    format_card_analysis_report,
)
from skat_ai.card_selection import VALID_CARD_SELECTION_POLICIES
from skat_ai.dataset_partition_audit import (
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
    resolve_dataset_partition_audit_mode,
)
from skat_ai.declarer_concession import (
    adjudicate_declarer_concession,
    build_declarer_card_count_evidence,
)
from skat_ai.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import build_serializable_game_declaration
from skat_ai.game_end import apply_remaining_points_assignment
from skat_ai.game_history import build_score_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_value import build_game_value_summary
from skat_ai.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot_summary,
)
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_profile_binding import (
    HistoricalOpponentProfileBindings,
    resolve_historical_opponent_profile_bindings,
)
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
    build_historical_opponent_statistics_aggregation_summary,
)
from skat_ai.impossible_null_settlement import (
    build_impossible_null_settlement_summary,
    build_serializable_impossible_null_settlement_summary,
)
from skat_ai.information_policy import build_information_policy_summary
from skat_ai.information_view import build_local_analysis_input
from skat_ai.input_loader import (
    build_game_state_from_input,
    build_local_game_state_from_input,
    get_actual_card_played_from_input,
    get_analysis_metadata_from_input,
    get_declarer_concession_from_input,
    get_game_declaration_from_input,
    get_impossible_null_settlement_from_input,
    get_input_workflow,
    get_list_analysis_results_from_input,
    get_list_game_contributions_from_input,
    get_list_performance_input_from_input,
    get_list_standings_input_from_input,
    get_performance_rating_system_from_input,
    get_profile_preset_settings_from_input,
    get_simulation_settings_from_input,
    load_historical_game_from_json,
    load_json_object,
    load_opponent_statistics_from_json,
    load_position_from_json,
    load_training_dataset_from_json,
)
from skat_ai.input_validation import MAX_SAMPLE_COUNT
from skat_ai.live_opponent_profile_binding import (
    LiveOpponentProfileBindings,
    resolve_live_opponent_profile_bindings,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.objective_utility import calculate_expected_objective_utility
from skat_ai.opponent_policy import VALID_OPPONENT_CARD_POLICIES
from skat_ai.opponent_profile_application import (
    EffectiveLiveOpponentProfiles,
    build_opponent_profile_application_summary,
    select_effective_live_opponent_profiles,
)
from skat_ai.opponent_statistics import (
    build_opponent_statistics_summary,
    build_serializable_opponent_statistics_input,
)
from skat_ai.output_writer import write_analysis_result_to_json
from skat_ai.overbid import build_overbid_summary
from skat_ai.performance_rating import (
    build_list_performance_summary,
    build_list_performance_summary_from_analysis_results,
    build_list_performance_summary_from_game_contributions,
    build_list_standings_summary,
    build_performance_rating_summary,
)
from skat_ai.policy_comparison import (
    compare_multi_step_policies,
    find_best_policy_by_local_point_swing,
)
from skat_ai.post_game_review import build_post_game_review_summary
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.result_serialization import (
    build_serializable_multi_step_result,
    build_serializable_policy_comparison_result,
)
from skat_ai.rolling_opponent_policy_evaluation import (
    DEFAULT_EVALUATION_PARTITIONS,
    DEFAULT_SOURCE_PARTITIONS,
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.rules import get_legal_cards
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
from skat_ai.training_dataset import build_training_dataset_summary

IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON = (
    "Immediate analysis is unavailable because the local player is not next."
)
IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON = (
    "Immediate analysis is unavailable because the game is complete."
)
POST_GAME_REVIEW_UNAVAILABLE_REASON_TEXT = {
    "actual_card_played_not_provided": "the actual card was not provided.",
    "immediate_analysis_unavailable": "immediate analysis is unavailable for this position.",
    "expected_point_swing_difference_not_available": (
        "the expected point swing difference is not available."
    ),
}


class CliUsageError(ValueError):
    """Raised when parsed CLI arguments form an invalid invocation."""


def get_immediate_unavailable_reason(
    state_next_player: str,
    game_end_reason: str,
    has_game_shortening: bool = False,
) -> str | None:
    """Returns why Immediate Analysis is unavailable, if it is unavailable."""
    if game_end_reason != "not_ended" or has_game_shortening:
        return IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON

    if state_next_player != "me":
        return IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON

    return None


def build_unavailable_strategic_summary(reason: str) -> str:
    """Builds a readable strategic summary for unavailable Immediate Analysis."""
    return f"Strategic summary: {reason}"


def apply_cli_overrides(
    settings: dict[str, Any],
    sample_count: int | None,
    random_seed: int | None,
    opponent_strategy: str | None,
) -> dict[str, Any]:
    """
    Applies optional command-line overrides to simulation settings.
    """
    updated_settings = settings.copy()

    if sample_count is not None:
        updated_settings["sample_count"] = sample_count

    if random_seed is not None:
        updated_settings["random_seed"] = random_seed

    if opponent_strategy == "basic":
        updated_settings["use_basic_opponent_strategy"] = True

    if opponent_strategy == "random":
        updated_settings["use_basic_opponent_strategy"] = False

    return updated_settings

def apply_profile_preset_cli_overrides(
    profile_preset_settings: dict[str, bool],
    use_profile_presets: bool = False,
) -> dict[str, bool]:
    """
    Applies CLI overrides to profile-preset settings.
    """
    updated_settings = profile_preset_settings.copy()

    if use_profile_presets:
        updated_settings["use_profile_presets"] = True

    return updated_settings


def build_effective_opponent_policy_settings_for_analysis(
    data: dict[str, Any],
    analysis_metadata: Any,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    effective_live_profiles: EffectiveLiveOpponentProfiles | None = None,
) -> EffectiveOpponentPolicySettings:
    """
    Builds shared effective opponent policy settings for one analysis invocation.
    """
    return build_effective_opponent_policy_settings(
        data=data,
        left_player_profile=(
            effective_live_profiles.left
            if effective_live_profiles is not None
            else analysis_metadata.left_player_profile
        ),
        right_player_profile=(
            effective_live_profiles.right
            if effective_live_profiles is not None
            else analysis_metadata.right_player_profile
        ),
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )


def build_global_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing global opponent-policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.global_lead_policy,
        "opponent_response_policy": effective_settings.global_response_policy,
    }


def build_left_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing left-opponent policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.left_lead_policy,
        "opponent_response_policy": effective_settings.left_response_policy,
    }


def build_right_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing right-opponent policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.right_lead_policy,
        "opponent_response_policy": effective_settings.right_response_policy,
    }


def build_analysis_result(
    file_path: str,
    sample_count_override: int | None = None,
    random_seed_override: int | None = None,
    opponent_strategy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    opponent_profile_application_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Builds the full analysis result as a structured dictionary.
    """
    data = load_position_from_json(file_path)
    local_data = build_local_analysis_input(data)
    state = build_game_state_from_input(local_data)
    settings = get_simulation_settings_from_input(data)
    analysis_metadata = get_analysis_metadata_from_input(data)
    if effective_opponent_policy_settings is None:
        effective_opponent_policy_settings = build_effective_opponent_policy_settings_for_analysis(
            data=data,
            analysis_metadata=analysis_metadata,
            opponent_policy_preset_override=opponent_policy_preset_override,
            opponent_lead_policy_override=opponent_lead_policy_override,
            opponent_response_policy_override=opponent_response_policy_override,
            use_profile_presets_override=use_profile_presets_override,
            left_opponent_lead_policy_override=left_opponent_lead_policy_override,
            left_opponent_response_policy_override=left_opponent_response_policy_override,
            right_opponent_lead_policy_override=right_opponent_lead_policy_override,
            right_opponent_response_policy_override=right_opponent_response_policy_override,
        )
    opponent_response_policy_by_player = (
        effective_opponent_policy_settings.immediate_response_policy_by_player
    )
    actual_card_played = get_actual_card_played_from_input(data)
    declarer_concession = get_declarer_concession_from_input(data)
    game_declaration = get_game_declaration_from_input(
        data if declarer_concession is not None else local_data
    )
    impossible_null_selection = get_impossible_null_settlement_from_input(data)
    performance_rating_system = get_performance_rating_system_from_input(data)
    list_performance_input = get_list_performance_input_from_input(data)
    list_game_contributions = get_list_game_contributions_from_input(data)
    list_analysis_results = get_list_analysis_results_from_input(data)
    list_standings_input = get_list_standings_input_from_input(data)
    game_value_summary = build_game_value_summary(game_declaration)
    impossible_null_summary = (
        build_impossible_null_settlement_summary(
            selection=impossible_null_selection,
            original_declaration=game_declaration,
        )
        if impossible_null_selection is not None
        else None
    )
    serializable_impossible_null_summary = (
        build_serializable_impossible_null_settlement_summary(
            impossible_null_summary
        )
    )
    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=game_declaration.bid_value,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
        impossible_null_settlement=serializable_impossible_null_summary,
    )
    opponent_policy_settings = build_global_opponent_policy_settings(
        effective_opponent_policy_settings
    )
    left_opponent_policy_settings = build_left_opponent_policy_settings(
        effective_opponent_policy_settings
    )
    right_opponent_policy_settings = build_right_opponent_policy_settings(
        effective_opponent_policy_settings
    )
    profile_preset_settings = get_profile_preset_settings_from_input(data)

    settings = apply_cli_overrides(
        settings=settings,
        sample_count=sample_count_override,
        random_seed=random_seed_override,
        opponent_strategy=opponent_strategy_override,
    )

    profile_preset_settings = apply_profile_preset_cli_overrides(
        profile_preset_settings=profile_preset_settings,
        use_profile_presets=use_profile_presets_override,
    )

    immediate_unavailable_reason = get_immediate_unavailable_reason(
        state_next_player=state.next_player,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
        has_game_shortening=declarer_concession is not None,
    )

    if immediate_unavailable_reason is None:
        legal_cards = get_legal_cards(
            hand=state.hand,
            current_trick=state.current_trick,
            game_type=state.game_type,
        )

        recommended_card, reason, _ = recommend_card_by_expected_value(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            sample_count=settings["sample_count"],
            random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
            opponent_response_policy_by_player=opponent_response_policy_by_player,
        )

        report = build_card_analysis_report(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            sample_count=settings["sample_count"],
            random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
            opponent_response_policy_by_player=opponent_response_policy_by_player,
        )
        strategic_summary = build_strategic_summary(
            report,
            game_type=state.game_type,
            player_role=state.player_role,
        )
    else:
        legal_cards = []
        recommended_card = None
        reason = immediate_unavailable_reason
        report = []
        strategic_summary = build_unavailable_strategic_summary(
            immediate_unavailable_reason
        )

    post_game_review_summary = build_post_game_review_summary(
        actual_card_played=actual_card_played,
        analysis_report=report,
        game_type=state.game_type,
        player_role=state.player_role,
        game_value=game_value_summary["game_value"],
    )

    score_summary = build_score_summary(state)
    game_result_summary = build_game_result_summary_from_score_summary(
        score_summary=score_summary,
        game_type=state.game_type,
        completed_tricks=state.completed_tricks,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
    )
    game_shortening_summary = None
    if declarer_concession is not None:
        adjudication = adjudicate_declarer_concession(
            game_shortening=declarer_concession,
            game_result_summary=game_result_summary,
            game_value_summary=game_value_summary,
            overbid_summary=overbid_summary,
            evidence=build_declarer_card_count_evidence(data),
        )
        adjusted_game_result_summary = adjudication.game_result_summary
        game_shortening_summary = adjudication.game_shortening_summary
    else:
        adjusted_game_result_summary = apply_remaining_points_assignment(
            game_result_summary=game_result_summary,
            game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
        )
    final_settlement_summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=adjusted_game_result_summary,
        overbid_summary=overbid_summary,
        completed_tricks=state.completed_tricks,
        impossible_null_settlement=serializable_impossible_null_summary,
    )
    performance_rating_summary = build_performance_rating_summary(
        final_settlement_summary=final_settlement_summary,
        rating_system=performance_rating_system,
    )
    list_performance_summary = None
    list_standings_summary = None
    if list_performance_input is not None:
        list_performance_summary = build_list_performance_summary(
            list_performance_input=list_performance_input,
            rating_system=performance_rating_system,
        )
    elif list_game_contributions is not None:
        list_performance_summary = build_list_performance_summary_from_game_contributions(
            game_contributions=list_game_contributions,
            rating_system=performance_rating_system,
        )
    elif list_analysis_results is not None:
        list_performance_summary = build_list_performance_summary_from_analysis_results(
            analysis_results=list_analysis_results,
            rating_system=performance_rating_system,
        )
    elif list_standings_input is not None:
        list_standings_summary = build_list_standings_summary(
            list_standings_input=list_standings_input,
            rating_system=performance_rating_system,
        )
    information_policy_summary = build_information_policy_summary(
        analysis_mode=analysis_metadata.strategic_metadata.analysis_mode,
        skat_visibility=analysis_metadata.strategic_metadata.skat_visibility,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
    )

    result = {
        "input_file": str(file_path),
        "position": {
            "game_type": state.game_type,
            "player_role": state.player_role,
            "player_position": state.player_position,
            "declarer_player": state.declarer_player,
            "trick_leader": state.trick_leader,
            "hand": state.hand,
            "current_trick": state.current_trick,
            "played_cards": state.played_cards,
            "completed_tricks": state.completed_tricks,
            "declarer_points": state.declarer_points,
            "defender_points": state.defender_points,
            "next_player": state.next_player,
            "skat": state.skat,
        },
        "settings": settings,
        "opponent_policy_settings": opponent_policy_settings,
        "left_opponent_policy_settings": left_opponent_policy_settings,
        "right_opponent_policy_settings": right_opponent_policy_settings,
        "profile_preset_settings": profile_preset_settings,
        "analysis_metadata": build_serializable_analysis_metadata(analysis_metadata),
        "information_policy_summary": information_policy_summary,
        "post_game_review_summary": post_game_review_summary,
        "game_declaration": build_serializable_game_declaration(game_declaration),
        "game_value_summary": game_value_summary,
        "overbid_summary": overbid_summary,
        "legal_cards": legal_cards,
        "analysis_report": report,
        "strategic_summary": strategic_summary,
        "score_summary": score_summary,
        "game_result_summary": game_result_summary,
        "adjusted_game_result_summary": adjusted_game_result_summary,
        "final_settlement_summary": final_settlement_summary,
        "performance_rating_summary": performance_rating_summary,
        "recommendation": {
            "card": recommended_card,
            "reason": reason,
        },
    }

    if list_performance_summary is not None:
        result["list_performance_summary"] = list_performance_summary

    if list_standings_summary is not None:
        result["list_standings_summary"] = list_standings_summary

    if game_shortening_summary is not None:
        result["game_shortening_summary"] = game_shortening_summary

    if opponent_profile_application_summary is not None:
        result["opponent_profile_application_summary"] = (
            opponent_profile_application_summary
        )

    return result


def format_decision_factors(summary: dict[str, object]) -> str:
    """Formats post-game review decision factors for CLI output."""
    decision_factors = summary.get("decision_factors", [])

    if not isinstance(decision_factors, list):
        return str(decision_factors)

    return ", ".join(str(factor) for factor in decision_factors)


def format_optional_cli_value(value: object) -> str:
    """Formats optional values for human-readable CLI output."""
    if value is None:
        return "not available"

    return str(value)


def format_post_game_review_unavailable_reason(reason: object) -> str:
    """Formats stable post-game review reason codes for human-readable CLI output."""
    reason_text = str(reason)

    return POST_GAME_REVIEW_UNAVAILABLE_REASON_TEXT.get(
        reason_text,
        reason_text.replace("_", " "),
    )


def is_null_review_result(result: dict[str, object]) -> bool:
    """Returns whether the CLI review output should use Null objective wording."""
    position = result.get("position")

    return isinstance(position, dict) and position.get("game_type") == "null"


def get_analysis_report_row_for_cli(
    result: dict[str, object],
    card: object,
) -> dict[str, object] | None:
    """Returns an analysis-report row for CLI-only presentation calculations."""
    analysis_report = result.get("analysis_report")

    if not isinstance(card, str) or not isinstance(analysis_report, list):
        return None

    for row in analysis_report:
        if isinstance(row, dict) and row.get("card") == card:
            return row

    return None


def calculate_missed_null_objective_gap_for_cli(
    result: dict[str, object],
    summary: dict[str, object],
) -> float | None:
    """Calculates the displayed Null objective gap without changing JSON output."""
    position = result.get("position")
    game_value_summary = result.get("game_value_summary")

    if not isinstance(position, dict) or not isinstance(game_value_summary, dict):
        return None

    actual_row = get_analysis_report_row_for_cli(
        result=result,
        card=summary.get("actual_card_played"),
    )
    recommended_row = get_analysis_report_row_for_cli(
        result=result,
        card=summary.get("recommended_card"),
    )

    if actual_row is None or recommended_row is None:
        return None

    try:
        actual_objective_utility = calculate_expected_objective_utility(
            game_type="null",
            player_role=str(position["player_role"]),
            value=actual_row,
        )
        recommended_objective_utility = calculate_expected_objective_utility(
            game_type="null",
            player_role=str(position["player_role"]),
            value=recommended_row,
        )
        game_value = float(game_value_summary["game_value"])
    except (KeyError, TypeError, ValueError):
        return None

    return max(
        0.0,
        (recommended_objective_utility - actual_objective_utility) * game_value,
    )


def print_post_game_review_rank_summary(summary: dict[str, object]) -> None:
    """Prints concise rank and better-alternative wording for review output."""
    candidate_count = format_optional_cli_value(summary.get("candidate_count"))
    actual_rank = format_optional_cli_value(summary.get("actual_card_rank"))
    recommended_rank = format_optional_cli_value(summary.get("recommended_card_rank"))
    actual_rank_text = actual_rank
    recommended_rank_text = recommended_rank

    if summary.get("actual_card_rank") is not None:
        actual_rank_text = f"{actual_rank} of {candidate_count}"

    if summary.get("recommended_card_rank") is not None:
        recommended_rank_text = f"{recommended_rank} of {candidate_count}"

    print(
        "Review ranks: "
        f"actual {actual_rank_text}; "
        f"recommended {recommended_rank_text}; "
        f"better alternatives {format_optional_cli_value(summary.get('better_card_count'))}."
    )

    better_card_count = summary.get("better_card_count")

    if better_card_count is None:
        print("Better alternatives: not available.")
        return

    if better_card_count == 0:
        print("Actual card is best-ranked by the review objective.")
        return

    suffix = "" if better_card_count == 1 else "s"
    print(
        f"Actual card has {better_card_count} better alternative{suffix} "
        "by the review objective."
    )


def print_post_game_review_value_summary(
    result: dict[str, object],
    summary: dict[str, object],
) -> None:
    """Prints point or objective-gap wording for post-game review output."""
    actual_expected_point_swing = float(summary["actual_expected_point_swing"])
    recommended_expected_point_swing = float(
        summary["recommended_expected_point_swing"]
    )
    expected_point_swing_difference = float(
        summary["expected_point_swing_difference"]
    )

    if is_null_review_result(result):
        missed_objective_gap = calculate_missed_null_objective_gap_for_cli(
            result=result,
            summary=summary,
        )
        missed_objective_gap_text = (
            format(missed_objective_gap, ".2f")
            if missed_objective_gap is not None
            else None
        )
        print("Objective basis: Null contract objective, not raw card points.")
        print(
            "Actual card-point swing (informational): "
            f"{actual_expected_point_swing:.2f}"
        )
        print(
            "Recommended card-point swing (informational): "
            f"{recommended_expected_point_swing:.2f}"
        )
        print(
            "Card-point swing difference (informational): "
            f"{expected_point_swing_difference:.2f}"
        )
        print(
            "Missed Null objective gap: "
            f"{format_optional_cli_value(missed_objective_gap_text)}"
        )
        return

    print(f"Actual expected point swing: {actual_expected_point_swing:.2f}")
    print(
        "Recommended expected point swing: "
        f"{recommended_expected_point_swing:.2f}"
    )
    print(
        "Missed expected point swing: "
        f"{max(0.0, expected_point_swing_difference):.2f}"
    )


def print_post_game_review_summary(result: dict[str, object]) -> None:
    """Prints the post-game review summary for human-readable CLI output."""
    summary = result.get("post_game_review_summary")

    if not isinstance(summary, dict):
        return

    print()
    print("Post-game review summary")

    decision_factors = format_decision_factors(summary)
    decision_explanation = summary.get("decision_explanation", "")

    if summary.get("is_available") is not True:
        reason = summary.get("reason", "not_available")
        print("Review status: not available")
        print(
            "Actual card played: "
            f"{format_optional_cli_value(summary.get('actual_card_played'))}"
        )
        print(
            "Recommended card: "
            f"{format_optional_cli_value(summary.get('recommended_card'))}"
        )
        print(
            "Unavailable reason: "
            f"{format_post_game_review_unavailable_reason(reason)}"
        )
        print(f"Reason code: {reason}")
        print(f"Decision factors: {decision_factors}")
        print(f"Decision explanation: {decision_explanation}")
        print_post_game_review_rank_summary(summary)
        return

    print(f"Actual card played: {summary['actual_card_played']}")
    print(f"Recommended card: {summary['recommended_card']}")
    print_post_game_review_value_summary(result=result, summary=summary)
    print(f"Decision quality: {summary['decision_quality']}")
    print(f"Decision factors: {decision_factors}")
    print(f"Decision explanation: {decision_explanation}")
    print_post_game_review_rank_summary(summary)


def print_analysis_result(result: dict[str, Any]) -> None:
    """
    Prints the analysis result in a readable text format.
    """
    position = result["position"]
    settings = result["settings"]
    score_summary = result["score_summary"]

    print("JSON position analysis")
    print("Input file:", result["input_file"])
    print("Game type:", position["game_type"])
    print("Player role:", position["player_role"])
    print("Player position:", position["player_position"])
    print("Declarer player:", position["declarer_player"])
    print("Trick leader:", position["trick_leader"])
    print("Hand:", position["hand"])
    print("Current trick:", position["current_trick"])
    print("Played cards:", position["played_cards"])
    print("Skat:", position["skat"])
    print("Completed tricks:", position["completed_tricks"])
    print("Declarer points:", position["declarer_points"])
    print("Defender points:", position["defender_points"])
    print("Next player:", position["next_player"])
    print("Legal cards:", result["legal_cards"])
    print("Left hand size:", settings["left_hand_size"])
    print("Right hand size:", settings["right_hand_size"])
    print("Sample count:", settings["sample_count"])
    print("Random seed:", settings["random_seed"])
    print("Use basic opponent strategy:", settings["use_basic_opponent_strategy"])

    print_opponent_profile_application_summary(result)

    print()
    print("Score summary")
    print("Explicit declarer points:", score_summary["explicit_declarer_points"])
    print("Explicit defender points:", score_summary["explicit_defender_points"])
    print(
        "Completed-trick declarer points:",
        score_summary["completed_trick_declarer_points"],
    )
    print(
        "Completed-trick defender points:",
        score_summary["completed_trick_defender_points"],
    )
    print("Total declarer points:", score_summary["total_declarer_points"])
    print("Total defender points:", score_summary["total_defender_points"])

    print()
    print(format_card_analysis_report(result["analysis_report"]))

    print()
    print(result["strategic_summary"])

    print()
    print(
        "Recommended card:",
        format_optional_cli_value(result["recommendation"]["card"]),
    )
    print("Reason:", result["recommendation"]["reason"])

    print_declarer_concession_summary(result)

    print_post_game_review_summary(result)


def print_declarer_concession_summary(result: dict[str, Any]) -> None:
    """Prints the bounded structured declarer-concession outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict):
        return

    hand_count = summary["declarer_hand_cards_remaining"]
    consent = summary["defender_consent"]
    if summary["consent_required"]:
        consent_text = (
            f"accepted by {consent['consenting_defender_count']} defender"
            + ("s" if consent["consenting_defender_count"] != 1 else "")
        )
    else:
        consent_text = "defender consent not required"

    settlement = result["final_settlement_summary"]
    print()
    print(f"Declarer concession: {hand_count} hand cards, {consent_text}.")
    print("Result: declarer lost; no remaining card points were assigned.")
    print(
        f"Settlement: {settlement['settlement_score']} using effective game value "
        f"{settlement['effective_game_value']}; no achieved Schneider or Schwarz "
        "level was added."
    )


def print_opponent_profile_application_summary(result: dict[str, Any]) -> None:
    """Prints one concise line per requested external opponent binding."""
    summary = result.get("opponent_profile_application_summary")
    if not isinstance(summary, dict):
        return

    for relative_player in ("left", "right"):
        side = summary[relative_player]
        if side["binding_status"] != "matched":
            continue
        external_profile = side["external_profile"]
        classification = external_profile["classification"]
        confidence = external_profile["confidence_level"]
        status = side["application_status"]
        if status == "applied":
            decision = f"applied {side['applied_policy_preset']}"
        elif status == "manual_profile_precedence":
            decision = "not applied; manual profile takes precedence"
        elif status == "explicit_policy_precedence":
            decision = "not applied; explicit policy takes precedence"
        else:
            decision = "not applied"
        print(
            f"{relative_player.title()} opponent {side['bound_player_id']}: "
            f"{classification}, {confidence} confidence, {decision}."
        )


def print_historical_game_result(result: dict[str, Any]) -> None:
    """Prints a concise complete historical-game summary."""
    summary = result["historical_game_summary"]
    declaration = summary["record"]["declaration"]
    settlement = summary["final_settlement_summary"]

    print("Historical game summary")
    print("Input file:", result["input_file"])
    print("Game ID:", summary["game_id"])
    print("Game type:", declaration["game_type"])
    print("Declarer:", summary["record"]["declarer_player_id"])
    print("Result winner:", summary["winner"])
    print("Declarer points:", summary["declarer_points"])
    print("Defender points:", summary["defender_points"])
    print("Game value:", summary["game_value_summary"]["game_value"])
    print("Overbid status:", summary["overbid_summary"]["status"])
    print("Settlement score:", settlement["settlement_score"])
    decision_snapshot_summary = summary.get("decision_snapshot_summary")
    if decision_snapshot_summary is not None:
        print("Decision snapshots generated:", decision_snapshot_summary["snapshot_count"])
    review_summary = summary.get("historical_game_review_summary")
    if review_summary is not None:
        profile_summary = result.get("historical_opponent_profile_application_summary")
        if profile_summary is not None:
            participant_count = len(profile_summary["participant_matches"])
            matched_count = profile_summary["matched_player_count"]
            print(
                f"Historical profile application: {matched_count} of "
                f"{participant_count} participants matched."
            )
            print("Temporal eligibility: all matched captures predate the game.")
            application_counts = review_summary["opponent_profile_application_counts"]
            applied_decisions = sum(
                any(
                    application[side]["application_status"] == "applied"
                    for side in ("left", "right")
                )
                for application in (
                    decision["opponent_profile_application"]
                    for decision in review_summary["decisions"]
                )
            )
            print(
                "Reviewed decisions with an applied external profile: "
                f"{applied_decisions} of {application_counts['total_decisions']}."
            )
        print()
        print("Historical game review")
        print("Total decisions:", review_summary["decision_count"])
        print("Reviewed decisions:", review_summary["reviewed_decision_count"])
        print("Unavailable decisions:", review_summary["unavailable_decision_count"])
        for quality, count in review_summary["quality_counts"].items():
            print(f"{quality.replace('_', ' ').title()} decisions:", count)
        for decision in review_summary["decisions"]:
            decision_quality = decision["post_game_review_summary"][
                "decision_quality"
            ]
            if decision_quality not in {"suboptimal", "mistake"}:
                continue
            print(
                f"Decision {decision['decision_index']} ({decision['acting_player_id']}): "
                f"{decision_quality}; actual {decision['actual_card_played']}, "
                f"recommended {decision['recommendation']['card']}."
            )


def print_training_dataset_result(result: dict[str, Any]) -> None:
    """Prints a concise training-dataset conversion summary."""
    summary = result["training_dataset_summary"]
    print("Training dataset summary")
    print("Input file:", result["input_file"])
    print("Dataset ID:", summary["dataset_id"])
    print("Dataset version:", summary["dataset_version"])
    print("Records:", summary["record_count"])
    print("Samples:", summary["sample_count"])
    for partition in ("train", "validation", "test"):
        counts = summary["partition_counts"][partition]
        print(
            f"{partition.title()} partition:",
            f"{counts['record_count']} records, {counts['sample_count']} samples",
        )


def print_dataset_partition_audit_result(result: dict[str, Any]) -> None:
    """Prints a concise stable-player partition-audit summary."""
    summary = result["dataset_partition_audit_summary"]
    source = summary["source_dataset"]
    players = summary["player_summary"]
    unseen = summary["unseen_player_compliance"]
    coverage = summary["known_opponent_coverage"]["train_to_validation"]
    print(
        "Dataset partition audit: "
        f"{source['total_historical_game_count']} games, "
        f"{players['total_distinct_player_count']} distinct players."
    )
    print("Partition mode:", f"{summary['effective_audit_mode']}.")
    print("Cross-partition players:", f"{unseen['violating_player_count']}.")
    print(
        "Train -> validation shared players: "
        f"{coverage['shared_player_count']} of "
        f"{coverage['target_distinct_player_count']} validation players."
    )
    if unseen["player_disjoint"]:
        print("Unseen-player compliance: passed.")
    else:
        print(
            "Unseen-player compliance: failed with "
            f"{unseen['violating_player_count']} overlapping players."
        )


def print_rolling_opponent_policy_evaluation_result(result: dict[str, Any]) -> None:
    """Prints a concise behavioral policy-evaluation summary."""
    summary = result["rolling_opponent_policy_evaluation_summary"]
    coverage = summary["coverage"]
    paired = summary["actionable_profile_paired_results"]
    print(
        "Rolling opponent-policy evaluation: "
        f"{coverage['target_game_count']} target games, "
        f"{coverage['target_decisions']} decisions."
    )
    print(
        "Prior player history: "
        f"{coverage['decisions_with_prior_player_history']} of "
        f"{coverage['target_decisions']} decisions."
    )
    print(
        "Actionable profile coverage: "
        f"{coverage['decisions_with_actionable_profile']} of "
        f"{coverage['target_decisions']} decisions."
    )
    if paired["paired_decision_count"] == 0:
        print(
            "No actionable profile predictions were available; baseline and coverage "
            "results were still recorded."
        )
        return
    print(
        "Paired preferred-card match: profile "
        f"{paired['profile_preferred_card_match_rate']:.2f}%, baseline "
        f"{paired['baseline_preferred_card_match_rate']:.2f}%, delta "
        f"{paired['preferred_card_rate_delta_percentage_points']:+.2f} pp."
    )


def print_opponent_statistics_result(result: dict[str, Any]) -> None:
    """Prints one concise summary per external opponent-statistics record."""
    summary = result["opponent_statistics_summary"]
    print("Opponent statistics summary")
    print("Input file:", result["input_file"])
    print("Records:", summary["record_count"])
    for record in summary["records"]:
        statistics = record["statistics"]
        derivation = record["profile_derivation"]
        label = record.get("player_label")
        identity = (
            record["player_id"]
            if label is None
            else f"{record['player_id']} ({label})"
        )
        print(
            f"{identity}: {record['games_played']} games; "
            f"declarer {statistics['solo_games_played_percent']:g}%; "
            f"declarer wins {statistics['solo_games_won_percent']:g}%; "
            f"defender {statistics['defender_games_played_percent']:g}%; "
            f"defender wins {statistics['defender_games_won_percent']:g}%."
        )
        confidence = derivation["confidence"]
        actionable = derivation["actionable_policy_preset"] is not None
        print(
            "  Profile derivation: "
            f"overall {confidence['overall']['level']}, "
            f"declarer {confidence['declarer']['level']}, "
            f"defender {confidence['defender']['level']}; "
            f"classification {derivation['classification']}; "
            f"recommended preset {derivation['recommended_policy_preset']}; "
            f"actionable {'yes' if actionable else 'no'}."
        )
        print(f"  Explanation: {derivation['explanations'][-1]}")


def print_historical_opponent_statistics_result(result: dict[str, Any]) -> None:
    """Prints a concise historical aggregation summary."""
    summary = result["historical_opponent_statistics_aggregation_summary"]
    print(
        "Historical opponent statistics: "
        f"{summary['source_game_count']} games, {summary['player_count']} players."
    )
    print(
        "Included partitions:",
        ", ".join(summary["selection"]["included_partitions"]),
    )
    for record in summary["records"]:
        statistics = record["statistics"]
        confidence = record["profile_derivation"]["confidence"]["overall"]["level"]
        print(
            f"{record['player_id']}: {record['games_played']} games, "
            f"{statistics['solo_games_played_percent']:.2f}% declarer, "
            f"{statistics['defender_games_played_percent']:.2f}% defender, "
            f"{confidence} confidence."
        )


def print_multi_step_result(result: dict[str, Any]) -> None:
    """
    Prints a multi-step simulation result in a readable text format.
    """
    final_state = result["final_state"]
    steps = result["steps"]

    if "summary" in result:
        print_multi_step_score_summary(result["summary"])

    print()
    print("Multi-step simulation")
    print("Card selection policy:", result["card_selection_policy"])
    print("Requested steps:", result.get("requested_step_count", len(steps)))
    print("Steps simulated:", result.get("steps_simulated", len(steps)))
    print("Stop reason:", result.get("stop_reason", "unknown"))
    if "opponent_policy_settings" in result:
        print(
            "Opponent lead policy:",
            result["opponent_policy_settings"]["opponent_lead_policy"],
        )
        print(
            "Opponent response policy:",
            result["opponent_policy_settings"]["opponent_response_policy"],
        )
    if "context_summary" in result:
        context_summary = result["context_summary"]
        duplicate_cards = context_summary["duplicate_simulated_opponent_cards"]

        print("Context summary:", context_summary)

        if duplicate_cards:
            print(
                "Context warning: duplicate simulated opponent cards detected:",
                duplicate_cards,
            )
        else:
            print("Context warning: none")

    for step in steps:
        detailed_result = step["detailed_result"]
        completed_trick = detailed_result["completed_trick"]
        opponent_lead_result = step.get("opponent_lead_result")

        print()
        print("Step:", step["step_index"])

        if opponent_lead_result is not None:
            print("Opponent lead player:", opponent_lead_result["leader"])
            print("Opponent lead card:", opponent_lead_result["lead_card"])

            if "responder" in opponent_lead_result:
                print("Opponent response player:", opponent_lead_result["responder"])
                print("Opponent response card:", opponent_lead_result["response_card"])

        print("Candidate card:", step["candidate_card"])
        print("Trick:", detailed_result["trick"])
        print("Did win:", detailed_result["did_win"])
        if "candidate_card_won" in detailed_result:
            print("Candidate card won:", detailed_result["candidate_card_won"])
        if "local_side_won" in detailed_result:
            print("Local side won:", detailed_result["local_side_won"])
        print("Trick points:", detailed_result["trick_points"])
        print("Winner role:", completed_trick["winner_role"])

    print()
    print("Final state")
    print("Remaining hand:", final_state.hand)
    print("Completed tricks:", final_state.completed_tricks)
    print("Declarer points:", final_state.declarer_points)
    print("Defender points:", final_state.defender_points)
    print("Next player:", final_state.next_player)


def print_policy_comparison_result(result: dict[str, Any]) -> None:
    """
    Prints a compact policy comparison result.
    """
    best_policy = find_best_policy_by_local_point_swing(result)

    print()
    print("Policy comparison")
    print("Requested steps:", result["requested_step_count"])
    print("Random seed:", result["random_seed"])
    print("Expected-value samples:", result["expected_value_sample_count"])
    print("Use basic opponent strategy:", result["use_basic_opponent_strategy"])
    print("Strict context:", result["strict_context"])
    print("Opponent lead policy:", result.get("opponent_lead_policy", "lowest_point"))
    print(
        "Opponent response policy:",
        result.get("opponent_response_policy", "lowest_point"),
    )

    print()
    print(
        f"{'Policy':<24}"
        f"{'Steps':>7}"
        f"{'Decl. +':>10}"
        f"{'Def. +':>10}"
        f"{'Swing':>10}"
        f"{'Local':>10}"
    )
    print("-" * 71)

    for policy_result in result["policy_results"]:
        local_point_swing = policy_result.get(
            "local_point_swing",
            policy_result["final_point_swing"],
        )
        print(
            f"{policy_result['policy']:<24}"
            f"{policy_result['steps_simulated']:>7}"
            f"{policy_result['declarer_points_gained']:>10}"
            f"{policy_result['defender_points_gained']:>10}"
            f"{policy_result['final_point_swing']:>10}"
            f"{local_point_swing:>10}"
        )

    recommended_policy = result.get("recommended_policy")

    print()

    if recommended_policy is not None:
        print("Recommended policy:", recommended_policy["policy"])
        print("Recommendation reason:", recommended_policy["reason"])
        print("Recommended final point swing:", recommended_policy["final_point_swing"])
        print(
            "Recommended local point swing:",
            recommended_policy.get(
                "local_point_swing",
                recommended_policy["final_point_swing"],
            ),
        )
    else:
        print("Best policy:", best_policy["policy"])
        print("Best final point swing:", best_policy["final_point_swing"])
        print(
            "Best local point swing:",
            best_policy.get("local_point_swing", best_policy["final_point_swing"]),
        )


def print_multi_step_score_summary(summary: dict[str, Any]) -> None:
    """
    Prints a compact multi-step score summary.
    """
    score_summary = summary["score_summary"]

    print()
    print("Multi-step score summary")
    print("Requested steps:", summary["requested_step_count"])
    print("Steps simulated:", summary["steps_simulated"])
    print("Stop reason:", summary["stop_reason"])
    print("Card selection policy:", summary["card_selection_policy"])
    print("Strict context:", summary["strict_context"])
    print("Initial declarer points:", score_summary["initial_declarer_points"])
    print("Initial defender points:", score_summary["initial_defender_points"])
    print("Final declarer points:", score_summary["final_declarer_points"])
    print("Final defender points:", score_summary["final_defender_points"])
    print("Declarer points gained:", score_summary["declarer_points_gained"])
    print("Defender points gained:", score_summary["defender_points_gained"])
    print("Final point swing:", score_summary["final_point_swing"])
    if "local_point_swing" in score_summary:
        print("Local point swing:", score_summary["local_point_swing"])


def run_json_position_analysis(
    file_path: str,
    sample_count_override: int | None = None,
    random_seed_override: int | None = None,
    opponent_strategy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    output_path: str | None = None,
    multi_step_count: int | None = None,
    card_selection_policy: str = "first_legal",
    expected_value_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    strict_context: bool = False,
    compare_policies: bool = False,
    comparison_only: bool = False,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    opponent_statistics_file: str | None = None,
    left_opponent_player_id: str | None = None,
    right_opponent_player_id: str | None = None,
    quiet: bool = False,
) -> None:
    if comparison_only and not compare_policies:
        raise ValueError("comparison_only requires compare_policies to be enabled.")

    if multi_step_count is not None and multi_step_count <= 0:
        raise ValueError("multi_step_count must be a positive integer.")

    position_data = load_position_from_json(file_path)
    if "game_shortening" in position_data and multi_step_count is not None:
        raise ValueError(
            "Structured game_shortening cannot be combined with multi-step simulation."
        )
    analysis_metadata = get_analysis_metadata_from_input(position_data)
    validate_live_opponent_profile_options(
        position_data=position_data,
        opponent_statistics_file=opponent_statistics_file,
        left_opponent_player_id=left_opponent_player_id,
        right_opponent_player_id=right_opponent_player_id,
        use_profile_presets_override=use_profile_presets_override,
    )
    bindings: LiveOpponentProfileBindings | None = None
    effective_live_profiles: EffectiveLiveOpponentProfiles | None = None
    if opponent_statistics_file is not None:
        statistics_input = load_opponent_statistics_from_json(opponent_statistics_file)
        statistics_summary = build_opponent_statistics_summary(statistics_input)
        bindings = resolve_live_opponent_profile_bindings(
            statistics_summary,
            left_player_id=left_opponent_player_id,
            right_player_id=right_opponent_player_id,
        )
        effective_live_profiles = select_effective_live_opponent_profiles(
            data=position_data,
            manual_left_profile=analysis_metadata.left_player_profile,
            manual_right_profile=analysis_metadata.right_player_profile,
            bindings=bindings,
        )
    effective_opponent_policy_settings = build_effective_opponent_policy_settings_for_analysis(
        data=position_data,
        analysis_metadata=analysis_metadata,
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
        effective_live_profiles=effective_live_profiles,
    )
    opponent_profile_application_summary = None
    if (
        opponent_statistics_file is not None
        and bindings is not None
        and effective_live_profiles is not None
    ):
        opponent_profile_application_summary = (
            build_opponent_profile_application_summary(
                statistics_input_file=opponent_statistics_file,
                use_profile_presets=True,
                bindings=bindings,
                effective_profiles=effective_live_profiles,
                effective_settings=effective_opponent_policy_settings,
            )
        )

    result = build_analysis_result(
        file_path=file_path,
        sample_count_override=sample_count_override,
        random_seed_override=random_seed_override,
        opponent_strategy_override=opponent_strategy_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        effective_opponent_policy_settings=effective_opponent_policy_settings,
        opponent_profile_application_summary=(
            opponent_profile_application_summary
        ),
    )

    multi_step_result_to_print = None
    policy_comparison_result_to_print = None

    if multi_step_count is not None:
        state = build_local_game_state_from_input(position_data)
        settings = get_simulation_settings_from_input(position_data)
        opponent_policy_settings = build_global_opponent_policy_settings(
            effective_opponent_policy_settings
        )
        left_opponent_policy_settings = build_left_opponent_policy_settings(
            effective_opponent_policy_settings
        )
        right_opponent_policy_settings = build_right_opponent_policy_settings(
            effective_opponent_policy_settings
        )

        profile_preset_settings = get_profile_preset_settings_from_input(position_data)
        profile_preset_settings = apply_profile_preset_cli_overrides(
            profile_preset_settings=profile_preset_settings,
            use_profile_presets=use_profile_presets_override,
        )

        settings = apply_cli_overrides(
            settings=settings,
            sample_count=sample_count_override,
            random_seed=random_seed_override,
            opponent_strategy=opponent_strategy_override,
        )

        result["opponent_policy_settings"] = opponent_policy_settings
        result["left_opponent_policy_settings"] = left_opponent_policy_settings
        result["right_opponent_policy_settings"] = right_opponent_policy_settings

        multi_step_result = simulate_multiple_steps(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            step_count=multi_step_count,
            random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
            card_selection_policy=card_selection_policy,
            expected_value_sample_count=expected_value_sample_count,
            strict_context=strict_context,
            strategic_metadata=analysis_metadata.strategic_metadata,
            opponent_lead_policy=opponent_policy_settings["opponent_lead_policy"],
            opponent_response_policy=opponent_policy_settings["opponent_response_policy"],
            left_opponent_policy_settings=left_opponent_policy_settings,
            right_opponent_policy_settings=right_opponent_policy_settings,
            opponent_response_policy_by_player=(
                effective_opponent_policy_settings.immediate_response_policy_by_player
            ),
        )

        result["multi_step_result"] = build_serializable_multi_step_result(
            multi_step_result
        )
        result["profile_preset_settings"] = profile_preset_settings

        if not comparison_only:
            multi_step_result_to_print = multi_step_result

        if compare_policies:
            policy_comparison_result = compare_multi_step_policies(
                state=state,
                left_hand_size=settings["left_hand_size"],
                right_hand_size=settings["right_hand_size"],
                step_count=multi_step_count,
                random_seed=settings["random_seed"],
                use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
                expected_value_sample_count=expected_value_sample_count,
                strict_context=strict_context,
                strategic_metadata=analysis_metadata.strategic_metadata,
                opponent_lead_policy=opponent_policy_settings["opponent_lead_policy"],
                opponent_response_policy=opponent_policy_settings["opponent_response_policy"],
                left_opponent_policy_settings=left_opponent_policy_settings,
                right_opponent_policy_settings=right_opponent_policy_settings,
                opponent_response_policy_by_player=(
                    effective_opponent_policy_settings.immediate_response_policy_by_player
                ),
            )

            result["policy_comparison_result"] = build_serializable_policy_comparison_result(
                policy_comparison_result
            )

            policy_comparison_result_to_print = policy_comparison_result

    if output_path is not None:
        write_analysis_result_to_json(
            output_path=output_path,
            result=result,
        )

    if quiet:
        return

    if not comparison_only:
        print_analysis_result(result)

    if multi_step_result_to_print is not None:
        print_multi_step_result(multi_step_result_to_print)

    if policy_comparison_result_to_print is not None:
        print_policy_comparison_result(policy_comparison_result_to_print)

    if output_path is not None:
        print()
        print("Output file written:", output_path)


def run_json_historical_game_analysis(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    historical_decision_snapshots: bool = False,
    historical_game_review: bool = False,
    sample_count: int | None = None,
    base_random_seed: int | None = None,
    opponent_statistics_file: str | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> None:
    """Runs the complete historical-game workflow."""
    record = load_historical_game_from_json(file_path)
    historical_game_summary = build_historical_game_summary(record)
    opponent_profile_bindings: HistoricalOpponentProfileBindings | None = None
    if opponent_statistics_file is not None:
        statistics_input = load_opponent_statistics_from_json(opponent_statistics_file)
        opponent_profile_bindings = resolve_historical_opponent_profile_bindings(
            record,
            statistics_input,
            statistics_input_file=opponent_statistics_file,
        )
    snapshot_summary = None
    if historical_decision_snapshots or historical_game_review:
        snapshot_summary = build_historical_decision_snapshots(
            historical_game_summary
        )
    if historical_decision_snapshots:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        historical_game_summary["decision_snapshot_summary"] = (
            build_serializable_historical_decision_snapshot_summary(
                snapshot_summary
            )
        )
    if historical_game_review:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        historical_game_summary["historical_game_review_summary"] = (
            build_historical_game_review_summary(
                snapshot_summary=snapshot_summary,
                historical_record=record,
                sample_count=(
                    sample_count
                    if sample_count is not None
                    else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                ),
                base_random_seed=base_random_seed,
                opponent_profile_bindings=opponent_profile_bindings,
                opponent_policy_preset_override=opponent_policy_preset_override,
                opponent_lead_policy_override=opponent_lead_policy_override,
                opponent_response_policy_override=opponent_response_policy_override,
                left_opponent_lead_policy_override=(left_opponent_lead_policy_override),
                left_opponent_response_policy_override=(left_opponent_response_policy_override),
                right_opponent_lead_policy_override=(right_opponent_lead_policy_override),
                right_opponent_response_policy_override=(right_opponent_response_policy_override),
            )
        )
    result = {
        "input_file": str(file_path),
        "historical_game_summary": historical_game_summary,
    }
    if opponent_profile_bindings is not None:
        result["historical_opponent_profile_application_summary"] = (
            opponent_profile_bindings.application_summary
        )

    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)

    if quiet:
        return

    print_historical_game_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)


def run_json_training_dataset_conversion(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
) -> None:
    """Runs deterministic training-dataset validation and sample generation."""
    dataset = load_training_dataset_from_json(file_path)
    result = {
        "input_file": str(file_path),
        "training_dataset_summary": build_training_dataset_summary(dataset),
    }
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_training_dataset_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)


def run_json_dataset_partition_audit(
    file_path: str,
    requested_mode: str | None = None,
    output_path: str | None = None,
    quiet: bool = False,
) -> None:
    """Audits training-dataset player overlap without generating samples."""
    dataset = load_training_dataset_from_json(file_path)
    try:
        effective_mode = resolve_dataset_partition_audit_mode(dataset, requested_mode)
    except ValueError as error:
        raise CliUsageError(str(error)) from error
    audit = audit_training_dataset_partitions(dataset, effective_mode)
    result = {
        "input_file": str(file_path),
        "dataset_partition_audit_summary": (
            build_serializable_dataset_partition_audit(audit)
        ),
    }
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_dataset_partition_audit_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)


def run_json_rolling_opponent_policy_evaluation(
    file_path: str,
    source_partitions: tuple[str, ...] = DEFAULT_SOURCE_PARTITIONS,
    evaluation_partitions: tuple[str, ...] = DEFAULT_EVALUATION_PARTITIONS,
    output_path: str | None = None,
    quiet: bool = False,
) -> None:
    """Runs rolling profile-derived behavioral policy evaluation."""
    dataset = load_training_dataset_from_json(file_path)
    evaluation = evaluate_rolling_opponent_policy_predictions(
        dataset,
        source_partitions=source_partitions,
        evaluation_partitions=evaluation_partitions,
    )
    result = {
        "input_file": str(file_path),
        "rolling_opponent_policy_evaluation_summary": (
            build_serializable_rolling_opponent_policy_evaluation(evaluation)
        ),
    }
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_rolling_opponent_policy_evaluation_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)


def run_json_historical_opponent_statistics_aggregation(
    file_path: str,
    included_partitions: tuple[str, ...] | None = None,
    before: str | None = None,
    output_path: str | None = None,
    export_path: str | None = None,
    quiet: bool = False,
) -> None:
    """Aggregates historical statistics without generating training samples."""
    dataset = load_training_dataset_from_json(file_path)
    aggregation = aggregate_historical_opponent_statistics(
        dataset,
        included_partitions=included_partitions,
        before=before,
    )
    result = {
        "input_file": str(file_path),
        "historical_opponent_statistics_aggregation_summary": (
            build_historical_opponent_statistics_aggregation_summary(aggregation)
        ),
    }
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if export_path is not None:
        export_input = build_exportable_opponent_statistics_input(aggregation)
        write_analysis_result_to_json(
            output_path=export_path,
            result=build_serializable_opponent_statistics_input(export_input),
        )
    if quiet:
        return
    print_historical_opponent_statistics_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    if export_path is not None:
        print("Exported opponent statistics to", f"{export_path}.")


def run_json_opponent_statistics_conversion(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
) -> None:
    """Runs deterministic external opponent-statistics validation and normalization."""
    statistics_input = load_opponent_statistics_from_json(file_path)
    result = {
        "input_file": str(file_path),
        "opponent_statistics_summary": build_opponent_statistics_summary(
            statistics_input
        ),
    }
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_opponent_statistics_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze a Skat position, replay a historical game, convert a training "
            "dataset, or normalize opponent statistics from JSON."
        ),
        epilog=(
            "Examples:\n"
            "  python main.py\n"
            "  python main.py --input examples/grand_second_position.json\n"
            "  python main.py --input examples/grand_second_position.json "
            "--multi-step 2\n"
            "  python main.py --input examples/grand_second_position.json "
            "--multi-step 1 --compare-policies\n"
            "  python main.py --input examples/grand_second_position.json "
            "--multi-step 1 --compare-policies --comparison-only\n"
            "  python main.py --input examples/historical_grand_normal_completion.json\n"
            "  python main.py --input examples/training_dataset_normal_play.json\n"
            "  python main.py --input examples/opponent_statistics.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input",
        default="input_position.json",
        help=(
            "Read position-analysis, historical-game, training-dataset, or "
            "opponent-statistics input from this JSON file. "
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
        help=(
            "Add 30 information-safe pre-play snapshots to historical-game output."
        ),
    )

    parser.add_argument(
        "--historical-game-review",
        action="store_true",
        help=(
            "Evaluate all 30 historical decisions with decision-time information."
        ),
    )

    parser.add_argument(
        "--multi-step",
        type=int,
        default=None,
        help="Run a phase-aware simulation for this many local decision steps.",
    )

    parser.add_argument(
        "--card-policy",
        choices=VALID_CARD_SELECTION_POLICIES,
        default=None,
        help="Choose local cards during multi-step simulation. Default: first_legal.",
    )

    parser.add_argument(
        "--expected-value-samples",
        type=int,
        default=None,
        help=(
            "Samples per candidate for the highest_expected_value card policy. "
            "Default: 100."
        ),
    )

    parser.add_argument(
        "--strict-context",
        action="store_true",
        help="Fail multi-step simulation if duplicate simulated opponent cards are detected.",
    )

    parser.add_argument(
        "--compare-policies",
        action="store_true",
        help="Compare all local card policies for the requested multi-step setup.",
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
            "Set both opponents' response policy for immediate analysis "
            "and multi-step simulation."
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
        help=(
            "Apply an opponent policy preset to immediate analysis "
            "and multi-step simulation."
        ),
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

    return parser.parse_args()


def validate_cli_arguments(
    args: argparse.Namespace,
    workflow: str | None = None,
) -> None:
    """Validates semantic CLI-only argument combinations."""
    if args.samples is not None and args.samples <= 0:
        raise CliUsageError("--samples must be a positive integer.")

    if args.samples is not None and args.samples > MAX_SAMPLE_COUNT:
        raise CliUsageError(f"--samples must be at most {MAX_SAMPLE_COUNT}.")

    if args.expected_value_samples is not None and args.expected_value_samples <= 0:
        raise CliUsageError("--expected-value-samples must be a positive integer.")

    if (
        args.expected_value_samples is not None
        and args.expected_value_samples > MAX_SAMPLE_COUNT
    ):
        raise CliUsageError(
            f"--expected-value-samples must be at most {MAX_SAMPLE_COUNT}."
        )

    if args.multi_step is not None and args.multi_step <= 0:
        raise CliUsageError("--multi-step must be a positive integer.")

    aggregate_statistics = getattr(args, "aggregate_opponent_statistics", False)
    evaluate_profiles = getattr(args, "evaluate_opponent_policy_profiles", False)
    audit_partitions = getattr(args, "audit_dataset_partitions", False)
    dataset_partition_mode = getattr(args, "dataset_partition_mode", None)
    if dataset_partition_mode is not None and not audit_partitions:
        raise CliUsageError(
            "--dataset-partition-mode requires --audit-dataset-partitions."
        )
    if audit_partitions and workflow != "training_dataset":
        raise CliUsageError(
            "--audit-dataset-partitions is supported only for training_dataset_input."
        )
    evaluation_only_options = {
        "--profile-source-partition": getattr(args, "profile_source_partition", None)
        is not None,
        "--profile-evaluation-partition": getattr(
            args, "profile_evaluation_partition", None
        )
        is not None,
    }
    supplied_evaluation_options = [
        option for option, supplied in evaluation_only_options.items() if supplied
    ]
    if supplied_evaluation_options and not evaluate_profiles:
        raise CliUsageError(
            "Opponent-policy profile evaluation partition options require "
            "--evaluate-opponent-policy-profiles: "
            f"{', '.join(supplied_evaluation_options)}."
        )
    if evaluate_profiles and workflow != "training_dataset":
        raise CliUsageError(
            "--evaluate-opponent-policy-profiles is supported only for "
            "training_dataset_input."
        )
    source_partitions = tuple(
        getattr(args, "profile_source_partition", None) or DEFAULT_SOURCE_PARTITIONS
    )
    evaluation_partitions = tuple(
        getattr(args, "profile_evaluation_partition", None)
        or DEFAULT_EVALUATION_PARTITIONS
    )
    overlap = sorted(set(source_partitions).intersection(evaluation_partitions))
    if evaluate_profiles and overlap:
        raise CliUsageError(
            "Profile source and evaluation partitions must be disjoint; overlap: "
            f"{overlap}."
        )
    aggregation_only_options = {
        "--opponent-statistics-partition": getattr(
            args, "opponent_statistics_partition", None
        )
        is not None,
        "--opponent-statistics-before": getattr(
            args, "opponent_statistics_before", None
        )
        is not None,
        "--export-opponent-statistics": getattr(
            args, "export_opponent_statistics", None
        )
        is not None,
    }
    supplied_aggregation_options = [
        option for option, supplied in aggregation_only_options.items() if supplied
    ]
    if supplied_aggregation_options and not aggregate_statistics:
        raise CliUsageError(
            "Historical opponent-statistics options require "
            "--aggregate-opponent-statistics: "
            f"{', '.join(supplied_aggregation_options)}."
        )
    if aggregate_statistics and workflow != "training_dataset":
        raise CliUsageError(
            "--aggregate-opponent-statistics is supported only for "
            "training_dataset_input."
        )
    if aggregate_statistics:
        paths = [
            ("--input", args.input),
            ("--output", args.output),
            (
                "--export-opponent-statistics",
                getattr(args, "export_opponent_statistics", None),
            ),
        ]
        resolved_paths = [
            (option, Path(path).resolve())
            for option, path in paths
            if path is not None
        ]
        for index, (first_option, first_path) in enumerate(resolved_paths):
            for second_option, second_path in resolved_paths[index + 1 :]:
                if first_path == second_path:
                    raise CliUsageError(
                        f"{first_option} and {second_option} must use different paths."
                    )

    if args.comparison_only and not args.compare_policies:
        raise CliUsageError("--comparison-only requires --compare-policies.")

    if args.compare_policies and args.multi_step is None:
        raise CliUsageError("--compare-policies requires --multi-step.")

    opponent_statistics_file = getattr(args, "opponent_statistics_file", None)
    left_player_id = getattr(args, "left_opponent_player_id", None)
    right_player_id = getattr(args, "right_opponent_player_id", None)
    if opponent_statistics_file is None and (
        left_player_id is not None or right_player_id is not None
    ):
        raise CliUsageError(
            "--left-opponent-player-id and --right-opponent-player-id require "
            "--opponent-statistics-file."
        )
    if (
        opponent_statistics_file is not None
        and not getattr(args, "historical_game_review", False)
        and workflow != "historical_game"
        and (left_player_id is None and right_player_id is None)
    ):
        raise CliUsageError(
            "--opponent-statistics-file requires --left-opponent-player-id, "
            "--right-opponent-player-id, or both."
        )
    for option_name, player_id in (
        ("--left-opponent-player-id", left_player_id),
        ("--right-opponent-player-id", right_player_id),
    ):
        if player_id is not None and (not player_id or player_id != player_id.strip()):
            raise CliUsageError(
                f"{option_name} must be a non-empty, non-padded string."
            )
    if left_player_id is not None and left_player_id == right_player_id:
        raise CliUsageError(
            "--left-opponent-player-id and --right-opponent-player-id must be different."
        )


def validate_live_opponent_profile_options(
    position_data: dict[str, Any],
    opponent_statistics_file: str | None,
    left_opponent_player_id: str | None,
    right_opponent_player_id: str | None,
    use_profile_presets_override: bool,
) -> None:
    """Validates external-profile options for one live position invocation."""
    if opponent_statistics_file is None:
        if left_opponent_player_id is not None or right_opponent_player_id is not None:
            raise CliUsageError(
                "Opponent player IDs require --opponent-statistics-file."
            )
        return
    if left_opponent_player_id is None and right_opponent_player_id is None:
        raise CliUsageError(
            "--opponent-statistics-file requires at least one opponent player ID."
        )
    if position_data.get("analysis_mode", "live_decision") != "live_decision":
        raise CliUsageError(
            "--opponent-statistics-file is supported only for "
            "analysis_mode='live_decision'."
        )
    unsupported_fields = {
        "list_performance_input",
        "list_game_contributions",
        "list_analysis_results",
        "list_standings_input",
        "impossible_null_settlement",
    }.intersection(position_data)
    if unsupported_fields:
        raise CliUsageError(
            "--opponent-statistics-file is not supported for this non-live analysis "
            f"workflow: {', '.join(sorted(unsupported_fields))}."
        )
    if not (
        position_data.get("use_profile_presets") is True
        or use_profile_presets_override
    ):
        raise CliUsageError(
            "--opponent-statistics-file requires effective --use-profile-presets opt-in."
        )


def validate_historical_game_cli_arguments(args: argparse.Namespace) -> None:
    """Rejects position-analysis and simulation overrides for historical games."""
    historical_profile_review = (
        args.historical_game_review and args.opponent_statistics_file is not None
    )
    if args.opponent_statistics_file is not None and not args.historical_game_review:
        raise CliUsageError(
            "--opponent-statistics-file requires --historical-game-review for "
            "historical-game input."
        )
    if historical_profile_review and (
        args.left_opponent_player_id is not None or args.right_opponent_player_id is not None
    ):
        raise CliUsageError(
            "--left-opponent-player-id and --right-opponent-player-id are live-only "
            "and are not accepted for historical review."
        )
    if historical_profile_review and not args.use_profile_presets:
        raise CliUsageError(
            "--opponent-statistics-file requires effective --use-profile-presets opt-in."
        )
    incompatible_options = {
        "--samples": args.samples is not None and not args.historical_game_review,
        "--seed": args.seed is not None and not args.historical_game_review,
        "--opponent-strategy": args.opponent_strategy is not None,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": (
            args.opponent_policy_preset is not None and not historical_profile_review
        ),
        "--opponent-lead-policy": (
            args.opponent_lead_policy is not None and not historical_profile_review
        ),
        "--opponent-response-policy": (
            args.opponent_response_policy is not None and not historical_profile_review
        ),
        "--use-profile-presets": args.use_profile_presets and not historical_profile_review,
        "--left-opponent-lead-policy": (
            args.left_opponent_lead_policy is not None and not historical_profile_review
        ),
        "--left-opponent-response-policy": (
            args.left_opponent_response_policy is not None and not historical_profile_review
        ),
        "--right-opponent-lead-policy": (
            args.right_opponent_lead_policy is not None and not historical_profile_review
        ),
        "--right-opponent-response-policy": (
            args.right_opponent_response_policy is not None and not historical_profile_review
        ),
        "--opponent-statistics-file": False,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
        "--aggregate-opponent-statistics": getattr(
            args, "aggregate_opponent_statistics", False
        ),
    }
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Historical-game inputs do not accept position-analysis, recommendation, "
            "policy, comparison, or simulation options: "
            f"{', '.join(supplied_options)}."
        )


def validate_training_dataset_cli_arguments(args: argparse.Namespace) -> None:
    """Rejects all analysis, review, simulation, policy, and profile options."""
    incompatible_options = {
        "--samples": args.samples is not None,
        "--seed": args.seed is not None,
        "--opponent-strategy": args.opponent_strategy is not None,
        "--historical-decision-snapshots": args.historical_decision_snapshots,
        "--historical-game-review": args.historical_game_review,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": args.opponent_policy_preset is not None,
        "--opponent-lead-policy": args.opponent_lead_policy is not None,
        "--opponent-response-policy": args.opponent_response_policy is not None,
        "--use-profile-presets": args.use_profile_presets,
        "--left-opponent-lead-policy": args.left_opponent_lead_policy is not None,
        "--left-opponent-response-policy": args.left_opponent_response_policy is not None,
        "--right-opponent-lead-policy": args.right_opponent_lead_policy is not None,
        "--right-opponent-response-policy": args.right_opponent_response_policy is not None,
        "--opponent-statistics-file": args.opponent_statistics_file is not None,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
    }
    evaluation_mode = getattr(args, "evaluate_opponent_policy_profiles", False)
    audit_mode = getattr(args, "audit_dataset_partitions", False)
    if audit_mode:
        incompatible_options.update(
            {
                "--aggregate-opponent-statistics": getattr(
                    args, "aggregate_opponent_statistics", False
                ),
                "--opponent-statistics-partition": getattr(
                    args, "opponent_statistics_partition", None
                )
                is not None,
                "--opponent-statistics-before": getattr(
                    args, "opponent_statistics_before", None
                )
                is not None,
                "--export-opponent-statistics": getattr(
                    args, "export_opponent_statistics", None
                )
                is not None,
                "--evaluate-opponent-policy-profiles": evaluation_mode,
            }
        )
    if evaluation_mode:
        incompatible_options.update(
            {
                "--aggregate-opponent-statistics": getattr(
                    args, "aggregate_opponent_statistics", False
                ),
                "--opponent-statistics-partition": getattr(
                    args, "opponent_statistics_partition", None
                )
                is not None,
                "--opponent-statistics-before": getattr(
                    args, "opponent_statistics_before", None
                )
                is not None,
                "--export-opponent-statistics": getattr(
                    args, "export_opponent_statistics", None
                )
                is not None,
            }
        )
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Training-dataset inputs do not accept position-analysis, historical-review, "
            "recommendation, policy, profile, comparison, or simulation options: "
            f"{', '.join(supplied_options)}."
        )


def validate_opponent_statistics_cli_arguments(args: argparse.Namespace) -> None:
    """Rejects every option except input, output, and quiet output."""
    incompatible_options = {
        "--samples": args.samples is not None,
        "--seed": args.seed is not None,
        "--opponent-strategy": args.opponent_strategy is not None,
        "--historical-decision-snapshots": args.historical_decision_snapshots,
        "--historical-game-review": args.historical_game_review,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": args.opponent_policy_preset is not None,
        "--opponent-lead-policy": args.opponent_lead_policy is not None,
        "--opponent-response-policy": args.opponent_response_policy is not None,
        "--use-profile-presets": args.use_profile_presets,
        "--left-opponent-lead-policy": args.left_opponent_lead_policy is not None,
        "--left-opponent-response-policy": args.left_opponent_response_policy is not None,
        "--right-opponent-lead-policy": args.right_opponent_lead_policy is not None,
        "--right-opponent-response-policy": args.right_opponent_response_policy is not None,
        "--opponent-statistics-file": args.opponent_statistics_file is not None,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
        "--aggregate-opponent-statistics": getattr(
            args, "aggregate_opponent_statistics", False
        ),
    }
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Opponent-statistics inputs do not accept analysis, historical, training-"
            "dataset, list, recommendation, policy, profile, review, sample, seed, or "
            f"simulation options: {', '.join(supplied_options)}."
        )


def main() -> int:
    args = parse_arguments()

    try:
        input_data = load_json_object(args.input)
        workflow = get_input_workflow(input_data)
        validate_cli_arguments(args, workflow=workflow)
        if workflow == "opponent_statistics":
            validate_opponent_statistics_cli_arguments(args)
            run_json_opponent_statistics_conversion(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
            )
        elif workflow == "training_dataset":
            validate_training_dataset_cli_arguments(args)
            if args.audit_dataset_partitions:
                run_json_dataset_partition_audit(
                    file_path=args.input,
                    requested_mode=args.dataset_partition_mode,
                    output_path=args.output,
                    quiet=args.quiet,
                )
            elif args.evaluate_opponent_policy_profiles:
                run_json_rolling_opponent_policy_evaluation(
                    file_path=args.input,
                    source_partitions=tuple(
                        args.profile_source_partition or DEFAULT_SOURCE_PARTITIONS
                    ),
                    evaluation_partitions=tuple(
                        args.profile_evaluation_partition
                        or DEFAULT_EVALUATION_PARTITIONS
                    ),
                    output_path=args.output,
                    quiet=args.quiet,
                )
            elif args.aggregate_opponent_statistics:
                run_json_historical_opponent_statistics_aggregation(
                    file_path=args.input,
                    included_partitions=(
                        tuple(args.opponent_statistics_partition)
                        if args.opponent_statistics_partition is not None
                        else None
                    ),
                    before=args.opponent_statistics_before,
                    output_path=args.output,
                    export_path=args.export_opponent_statistics,
                    quiet=args.quiet,
                )
            else:
                run_json_training_dataset_conversion(
                    file_path=args.input,
                    output_path=args.output,
                    quiet=args.quiet,
                )
        elif workflow == "historical_game":
            validate_historical_game_cli_arguments(args)
            run_json_historical_game_analysis(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
                historical_decision_snapshots=args.historical_decision_snapshots,
                historical_game_review=args.historical_game_review,
                sample_count=args.samples,
                base_random_seed=args.seed,
                opponent_statistics_file=args.opponent_statistics_file,
                opponent_policy_preset_override=args.opponent_policy_preset,
                opponent_lead_policy_override=args.opponent_lead_policy,
                opponent_response_policy_override=args.opponent_response_policy,
                left_opponent_lead_policy_override=args.left_opponent_lead_policy,
                left_opponent_response_policy_override=(args.left_opponent_response_policy),
                right_opponent_lead_policy_override=args.right_opponent_lead_policy,
                right_opponent_response_policy_override=(args.right_opponent_response_policy),
            )
        else:
            if args.historical_decision_snapshots:
                raise CliUsageError(
                    "--historical-decision-snapshots requires historical-game input."
                )
            if args.historical_game_review:
                raise CliUsageError(
                    "--historical-game-review requires historical-game input."
                )
            run_json_position_analysis(
                file_path=args.input,
                sample_count_override=args.samples,
                random_seed_override=args.seed,
                opponent_strategy_override=args.opponent_strategy,
                left_opponent_lead_policy_override=args.left_opponent_lead_policy,
                left_opponent_response_policy_override=args.left_opponent_response_policy,
                right_opponent_lead_policy_override=args.right_opponent_lead_policy,
                right_opponent_response_policy_override=args.right_opponent_response_policy,
                output_path=args.output,
                multi_step_count=args.multi_step,
                card_selection_policy=args.card_policy or "first_legal",
                expected_value_sample_count=(
                    args.expected_value_samples
                    or DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                ),
                strict_context=args.strict_context,
                compare_policies=args.compare_policies,
                comparison_only=args.comparison_only,
                opponent_policy_preset_override=args.opponent_policy_preset,
                opponent_lead_policy_override=args.opponent_lead_policy,
                opponent_response_policy_override=args.opponent_response_policy,
                use_profile_presets_override=args.use_profile_presets,
                opponent_statistics_file=args.opponent_statistics_file,
                left_opponent_player_id=args.left_opponent_player_id,
                right_opponent_player_id=args.right_opponent_player_id,
                quiet=args.quiet,
            )
    except CliUsageError as error:
        print(f"CLI error: {error}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
