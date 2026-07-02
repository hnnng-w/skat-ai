import argparse
import sys
from typing import Any

from skat_ai.analysis_metadata import build_serializable_analysis_metadata
from skat_ai.analysis_report import (
    build_card_analysis_report,
    build_strategic_summary,
    format_card_analysis_report,
)
from skat_ai.card_selection import VALID_CARD_SELECTION_POLICIES
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
from skat_ai.information_policy import build_information_policy_summary
from skat_ai.input_loader import (
    build_game_state_from_input,
    get_actual_card_played_from_input,
    get_analysis_metadata_from_input,
    get_game_declaration_from_input,
    get_list_analysis_results_from_input,
    get_list_game_contributions_from_input,
    get_list_performance_input_from_input,
    get_performance_rating_system_from_input,
    get_profile_preset_settings_from_input,
    get_simulation_settings_from_input,
    load_position_from_json,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.opponent_policy import VALID_OPPONENT_CARD_POLICIES
from skat_ai.output_writer import write_analysis_result_to_json
from skat_ai.overbid import build_overbid_summary
from skat_ai.performance_rating import (
    build_list_performance_summary,
    build_list_performance_summary_from_analysis_results,
    build_list_performance_summary_from_game_contributions,
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
from skat_ai.rules import get_legal_cards

IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON = (
    "Immediate analysis is unavailable because the local player is not next."
)
IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON = (
    "Immediate analysis is unavailable because the game is complete."
)


class CliUsageError(ValueError):
    """Raised when parsed CLI arguments form an invalid invocation."""


def get_immediate_unavailable_reason(
    state_next_player: str,
    game_end_reason: str,
) -> str | None:
    """Returns why Immediate Analysis is unavailable, if it is unavailable."""
    if game_end_reason != "not_ended":
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
) -> EffectiveOpponentPolicySettings:
    """
    Builds shared effective opponent policy settings for one analysis invocation.
    """
    return build_effective_opponent_policy_settings(
        data=data,
        left_player_profile=analysis_metadata.left_player_profile,
        right_player_profile=analysis_metadata.right_player_profile,
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
) -> dict[str, Any]:
    """
    Builds the full analysis result as a structured dictionary.
    """
    data = load_position_from_json(file_path)
    state = build_game_state_from_input(data)
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
    game_declaration = get_game_declaration_from_input(data)
    performance_rating_system = get_performance_rating_system_from_input(data)
    list_performance_input = get_list_performance_input_from_input(data)
    list_game_contributions = get_list_game_contributions_from_input(data)
    list_analysis_results = get_list_analysis_results_from_input(data)
    game_value_summary = build_game_value_summary(game_declaration)
    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=game_declaration.bid_value,
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
    adjusted_game_result_summary = apply_remaining_points_assignment(
        game_result_summary=game_result_summary,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
    )
    final_settlement_summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=adjusted_game_result_summary,
        overbid_summary=overbid_summary,
        completed_tricks=state.completed_tricks,
    )
    performance_rating_summary = build_performance_rating_summary(
        final_settlement_summary=final_settlement_summary,
        rating_system=performance_rating_system,
    )
    list_performance_summary = None
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
        print(f"Not available: {reason}")
        print(f"Decision factors: {decision_factors}")
        print(f"Decision explanation: {decision_explanation}")
        print(
            "Actual card rank: "
            f"{format_optional_cli_value(summary.get('actual_card_rank'))}"
        )
        print(
            "Recommended card rank: "
            f"{format_optional_cli_value(summary.get('recommended_card_rank'))}"
        )
        print(
            f"Candidate count: {format_optional_cli_value(summary.get('candidate_count'))}"
        )
        print(
            "Better card count: "
            f"{format_optional_cli_value(summary.get('better_card_count'))}"
        )
        return

    actual_expected_point_swing = float(summary["actual_expected_point_swing"])
    recommended_expected_point_swing = float(
        summary["recommended_expected_point_swing"]
    )
    expected_point_swing_difference = float(
        summary["expected_point_swing_difference"]
    )

    print(f"Actual card played: {summary['actual_card_played']}")
    print(f"Recommended card: {summary['recommended_card']}")
    print(f"Actual expected point swing: {actual_expected_point_swing:.2f}")
    print(
        "Recommended expected point swing: "
        f"{recommended_expected_point_swing:.2f}"
    )
    print(
        "Expected point swing difference: "
        f"{expected_point_swing_difference:.2f}"
    )
    print(f"Decision quality: {summary['decision_quality']}")
    print(f"Decision factors: {decision_factors}")
    print(f"Decision explanation: {decision_explanation}")
    print(f"Actual card rank: {summary['actual_card_rank']}")
    print(f"Recommended card rank: {summary['recommended_card_rank']}")
    print(f"Candidate count: {summary['candidate_count']}")
    print(f"Better card count: {summary['better_card_count']}")


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

    print_post_game_review_summary(result)


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
    expected_value_sample_count: int = 100,
    strict_context: bool = False,
    compare_policies: bool = False,
    comparison_only: bool = False,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
) -> None:
    if comparison_only and not compare_policies:
        raise ValueError("comparison_only requires compare_policies to be enabled.")

    if multi_step_count is not None and multi_step_count <= 0:
        raise ValueError("multi_step_count must be a positive integer.")

    position_data = load_position_from_json(file_path)
    analysis_metadata = get_analysis_metadata_from_input(position_data)
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
    )

    multi_step_result_to_print = None
    policy_comparison_result_to_print = None

    if multi_step_count is not None:
        state = build_game_state_from_input(position_data)
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

    print_analysis_result(result)

    if multi_step_result_to_print is not None:
        print_multi_step_result(multi_step_result_to_print)

    if policy_comparison_result_to_print is not None:
        print_policy_comparison_result(policy_comparison_result_to_print)

    if output_path is not None:
        print()
        print("Output file written:", output_path)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a Skat position from a JSON input file.",
    )

    parser.add_argument(
        "--input",
        default="input_position.json",
        help="Path to the JSON input file. Default: input_position.json",
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Override sample_count from the JSON input file.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random_seed from the JSON input file.",
    )

    parser.add_argument(
        "--opponent-strategy",
        choices=["basic", "random"],
        default=None,
        help="Override opponent strategy from the JSON input file. Choices: basic, random.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write the analysis result as JSON.",
    )

    parser.add_argument(
        "--multi-step",
        type=int,
        default=None,
        help="Optionally run a multi-step simulation with the given number of steps.",
    )

    parser.add_argument(
        "--card-policy",
        choices=VALID_CARD_SELECTION_POLICIES,
        default="first_legal",
        help="Card-selection policy for multi-step simulation.",
    )

    parser.add_argument(
        "--expected-value-samples",
        type=int,
        default=100,
        help="Sample count used by the highest_expected_value card policy.",
    )

    parser.add_argument(
        "--strict-context",
        action="store_true",
        help="Fail if duplicate simulated opponent cards are detected.",
    )

    parser.add_argument(
        "--compare-policies",
        action="store_true",
        help="Compare all card-selection policies for the given multi-step setup.",
    )

    parser.add_argument(
        "--comparison-only",
        action="store_true",
        help="Only print the policy comparison, not the individual multi-step details.",
    )

    parser.add_argument(
        "--opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help="Opponent lead card policy for multi-step simulations.",
    )

    parser.add_argument(
        "--opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Opponent response card policy for immediate response analysis "
            "and multi-step simulations."
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
            "Opponent policy preset for immediate response analysis "
            "and multi-step simulations."
        ),
    )

    parser.add_argument(
        "--use-profile-presets",
        action="store_true",
        help=(
            "Use player profiles to derive opponent policy presets for immediate "
            "response analysis and multi-step simulations."
        ),
    )

    parser.add_argument(
        "--left-opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
    )
    parser.add_argument(
        "--left-opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Left opponent response card policy for immediate response analysis "
            "and multi-step simulations."
        ),
    )
    parser.add_argument(
        "--right-opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
    )
    parser.add_argument(
        "--right-opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Right opponent response card policy for immediate response analysis "
            "and multi-step simulations."
        ),
    )

    return parser.parse_args()


def validate_cli_arguments(args: argparse.Namespace) -> None:
    """Validates semantic CLI-only argument combinations."""
    if args.samples is not None and args.samples <= 0:
        raise CliUsageError("--samples must be a positive integer.")

    if args.expected_value_samples <= 0:
        raise CliUsageError("--expected-value-samples must be a positive integer.")

    if args.multi_step is not None and args.multi_step <= 0:
        raise CliUsageError("--multi-step must be a positive integer.")

    if args.comparison_only and not args.compare_policies:
        raise CliUsageError("--comparison-only requires --compare-policies.")

    if args.compare_policies and args.multi_step is None:
        raise CliUsageError("--compare-policies requires --multi-step.")


def main() -> int:
    args = parse_arguments()

    try:
        validate_cli_arguments(args)
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
            card_selection_policy=args.card_policy,
            expected_value_sample_count=args.expected_value_samples,
            strict_context=args.strict_context,
            compare_policies=args.compare_policies,
            comparison_only=args.comparison_only,
            opponent_policy_preset_override=args.opponent_policy_preset,
            opponent_lead_policy_override=args.opponent_lead_policy,
            opponent_response_policy_override=args.opponent_response_policy,
            use_profile_presets_override=args.use_profile_presets,
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
