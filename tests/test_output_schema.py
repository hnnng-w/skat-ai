import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "output.schema.json"


def load_output_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


OUTPUT_VALIDATOR = Draft202012Validator(load_output_schema())


def build_policy_settings() -> dict[str, str]:
    return {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def build_context_summary() -> dict[str, object]:
    return {
        "simulated_opponent_card_count": 2,
        "unique_simulated_opponent_card_count": 2,
        "duplicate_simulated_opponent_cards": [],
        "event_count": 1,
        "strategic_metadata": {
            "analysis_mode": "live_decision",
            "skat_visibility": "unknown",
            "game_end_reason": "not_ended",
        },
    }


def build_completed_trick() -> dict[str, object]:
    return {
        "cards": ["S7", "SA", "S8"],
        "players": ["right", "me", "left"],
        "winner_role": "declarer",
        "winner_player": "me",
    }


def build_game_state(
    hand: list[str] | None = None,
    current_trick: list[str] | None = None,
    completed_tricks: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": hand if hand is not None else ["SA"],
        "current_trick": current_trick if current_trick is not None else ["S7"],
        "played_cards": [],
        "skat": [],
        "player_position": "middlehand",
        "declarer_player": "me",
        "trick_leader": "right",
        "completed_tricks": completed_tricks if completed_tricks is not None else [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
    }


def build_multi_step_result() -> dict[str, object]:
    context_summary = build_context_summary()
    completed_trick = build_completed_trick()
    prepared_state = build_game_state()
    final_state = build_game_state(
        hand=[],
        current_trick=[],
        completed_tricks=[completed_trick],
    )
    final_state["declarer_points"] = 11

    return {
        "card_selection_policy": "highest_point",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "strict_context": False,
        "opponent_policy_settings": build_policy_settings(),
        "left_opponent_policy_settings": build_policy_settings(),
        "right_opponent_policy_settings": build_policy_settings(),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "highest_point",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
                "local_point_swing": 11,
            },
            "context_summary": context_summary,
        },
        "context_summary": context_summary,
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": None,
                "prepared_state": prepared_state,
                "candidate_card": "SA",
                "card_selection_policy": "highest_point",
                "detailed_result": {
                    "trick": ["S7", "SA", "S8"],
                    "did_win": True,
                    "candidate_card_won": True,
                    "local_side_won": True,
                    "trick_points": 11,
                    "completed_trick": completed_trick,
                },
            }
        ],
        "final_state": final_state,
    }


def build_policy_comparison_result() -> dict[str, object]:
    policy_result = {
        "policy": "highest_point",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "strict_context": False,
        "declarer_points_gained": 11,
        "defender_points_gained": 0,
        "final_point_swing": 11,
        "local_point_swing": 11,
        "context_summary": build_context_summary(),
    }

    return {
        "requested_step_count": 1,
        "random_seed": 42,
        "expected_value_sample_count": 20,
        "use_basic_opponent_strategy": True,
        "strict_context": False,
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
        "policies": ["first_legal", "highest_point"],
        "policy_results": [policy_result],
        "recommended_policy": {
            "policy": "highest_point",
            "reason": "Best final point swing after tie-breakers.",
            "final_point_swing": 11,
            "local_point_swing": 11,
            "declarer_points_gained": 11,
            "defender_points_gained": 0,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
        },
    }


def build_valid_output() -> dict[str, object]:
    return {
        "input_file": "tests/fixtures/generated_output_schema/position.json",
        "position": {
            "declarer_player": "me",
        },
        "settings": {},
        "analysis_metadata": {},
        "game_declaration": {
            "game_type": "grand",
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "matadors": 1,
            "bid_value": None,
        },
        "game_value_summary": {
            "game_type": "grand",
            "is_null_game": False,
            "base_value": 24,
            "game_level": 2,
            "game_value": 48,
            "details": {},
        },
        "overbid_summary": {
            "bid_value": None,
            "game_value": 48,
            "is_overbid": None,
            "margin": None,
            "required_game_value": None,
            "status": "unknown_bid_value",
        },
        "legal_cards": [],
        "analysis_report": [],
        "score_summary": {
            "explicit_declarer_points": 0,
            "explicit_defender_points": 0,
            "completed_trick_declarer_points": 0,
            "completed_trick_defender_points": 0,
            "total_declarer_points": 0,
            "total_defender_points": 0,
        },
        "game_result_summary": {
            "declarer_points": 0,
            "defender_points": 0,
            "points_remaining": 120,
            "is_complete": False,
            "winner": "undecided",
        },
        "adjusted_game_result_summary": {
            "declarer_points": 0,
            "defender_points": 0,
            "points_remaining": 120,
            "is_complete": False,
            "winner": "undecided",
            "game_end_reason": "not_ended",
            "remaining_points_recipient": None,
            "remaining_points_assigned": 0,
        },
        "final_settlement_summary": {
            "is_complete": False,
            "missing_inputs": ["complete_card_points"],
            "declarer_won_by_card_points": None,
            "winner": None,
            "game_value": 48,
            "effective_game_value": None,
            "bid_value": None,
            "settlement_score": None,
            "is_loss": None,
            "is_overbid": None,
            "overbid_margin": None,
            "overbid_status": "unknown_bid_value",
            "overbid_required_game_value": None,
        },
        "performance_rating_summary": {
            "is_implemented": False,
            "is_partially_implemented": False,
            "implemented_scope": None,
            "unsupported_scope": "performance_rating_not_implemented",
            "rating_system": None,
            "table_player_count": 3,
            "basis": "individual_game_settlement",
            "game_outcome": "incomplete",
            "settlement_score": None,
            "rating_score": None,
            "declarer_rating_score": None,
            "declarer_rating_points": None,
            "counterparty_rating_points": None,
            "defender_rating_points": None,
            "unsupported_reason": "performance_rating_not_implemented",
        },
        "recommendation": {
            "card": None,
            "reason": "Immediate analysis is unavailable.",
        },
        "information_policy_summary": {
            "analysis_mode": "live_decision",
            "skat_visibility": "unknown",
            "game_end_reason": "not_ended",
            "live_information_enforced": True,
            "known_post_game_skat_allowed": False,
            "known_skat_cards_allowed": False,
            "ended_game_allowed": False,
            "unverifiable_completed_trick_winner_metadata_allowed": False,
        },
        "post_game_review_summary": {
            "is_available": False,
            "reason": "immediate_analysis_unavailable",
            "actual_card_played": None,
            "recommended_card": None,
            "actual_expected_point_swing": None,
            "recommended_expected_point_swing": None,
            "expected_point_swing_difference": None,
            "decision_quality": "not_available",
            "decision_factors": ["immediate_analysis_unavailable"],
            "decision_explanation": "Immediate analysis is unavailable.",
            "actual_card_rank": None,
            "recommended_card_rank": None,
            "candidate_count": 0,
            "better_card_count": None,
        },
        "opponent_policy_settings": build_policy_settings(),
        "left_opponent_policy_settings": build_policy_settings(),
        "right_opponent_policy_settings": build_policy_settings(),
        "profile_preset_settings": {
            "use_profile_presets": False,
        },
    }


def build_valid_output_with_optional_results() -> dict[str, object]:
    data = build_valid_output()
    data["multi_step_result"] = build_multi_step_result()
    data["policy_comparison_result"] = build_policy_comparison_result()

    return data


def assert_schema_valid(data: dict[str, object]) -> None:
    errors = sorted(
        OUTPUT_VALIDATOR.iter_errors(data),
        key=lambda validation_error: list(validation_error.absolute_path),
    )

    assert not errors, [
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def assert_schema_invalid(data: dict[str, object]) -> None:
    errors = list(OUTPUT_VALIDATOR.iter_errors(data))

    assert errors


def test_schema_accepts_base_output_without_optional_results() -> None:
    assert_schema_valid(build_valid_output())


def test_schema_accepts_structured_multi_step_and_policy_results() -> None:
    assert_schema_valid(build_valid_output_with_optional_results())


def test_schema_rejects_malformed_multi_step_steps_type() -> None:
    data = build_valid_output_with_optional_results()
    multi_step_result = data["multi_step_result"]

    assert isinstance(multi_step_result, dict)
    multi_step_result["steps"] = "not-a-list"

    assert_schema_invalid(data)


def test_schema_rejects_malformed_prepared_state() -> None:
    data = build_valid_output_with_optional_results()
    multi_step_result = data["multi_step_result"]

    assert isinstance(multi_step_result, dict)
    steps = multi_step_result["steps"]
    assert isinstance(steps, list)
    step = steps[0]
    assert isinstance(step, dict)
    step["prepared_state"] = {
        "game_type": "grand",
    }

    assert_schema_invalid(data)


def test_schema_rejects_invalid_multi_step_stop_reason() -> None:
    data = build_valid_output_with_optional_results()
    multi_step_result = data["multi_step_result"]

    assert isinstance(multi_step_result, dict)
    multi_step_result["stop_reason"] = "unsupported phase"

    assert_schema_invalid(data)


def test_schema_rejects_malformed_policy_comparison_result() -> None:
    data = build_valid_output_with_optional_results()
    policy_comparison_result = data["policy_comparison_result"]

    assert isinstance(policy_comparison_result, dict)
    policy_comparison_result["policy_results"] = "not-a-list"

    assert_schema_invalid(data)


def test_schema_rejects_invalid_post_game_unavailable_reason() -> None:
    data = build_valid_output()
    post_game_review_summary = data["post_game_review_summary"]

    assert isinstance(post_game_review_summary, dict)
    post_game_review_summary["reason"] = "local_player_not_next"

    assert_schema_invalid(data)


@pytest.mark.parametrize(
    "decision_factor",
    [
        "no_missed_null_objective",
        "lower_null_objective_than_recommendation",
        "small_null_objective_gap",
        "medium_null_objective_gap",
        "large_null_objective_gap",
    ],
)
def test_schema_accepts_null_post_game_decision_factors(
    decision_factor: str,
) -> None:
    data = build_valid_output()
    post_game_review_summary = data["post_game_review_summary"]

    assert isinstance(post_game_review_summary, dict)
    post_game_review_summary["decision_factors"] = [decision_factor]

    assert_schema_valid(data)


def test_schema_rejects_missing_required_profile_preset_settings() -> None:
    data = build_valid_output()
    data.pop("profile_preset_settings")

    assert_schema_invalid(data)


@pytest.mark.parametrize(
    "game_end_reason",
    [
        "not_ended",
        "normal_completion",
        "declarer_claimed_remaining_tricks",
        "declarer_conceded_remaining_tricks",
        "defenders_conceded_remaining_tricks",
    ],
)
def test_schema_accepts_supported_game_end_reasons(game_end_reason: str) -> None:
    data = build_valid_output()
    adjusted_summary = data["adjusted_game_result_summary"]
    information_summary = data["information_policy_summary"]

    assert isinstance(adjusted_summary, dict)
    assert isinstance(information_summary, dict)
    adjusted_summary["game_end_reason"] = game_end_reason
    information_summary["game_end_reason"] = game_end_reason

    assert_schema_valid(data)


@pytest.mark.parametrize(
    "overbid_status",
    [
        "unknown",
        "unknown_bid_value",
        "unknown_game_value",
        "not_overbid",
        "overbid",
    ],
)
def test_schema_accepts_supported_overbid_statuses(overbid_status: str) -> None:
    data = build_valid_output()
    overbid_summary = data["overbid_summary"]
    final_settlement_summary = data["final_settlement_summary"]

    assert isinstance(overbid_summary, dict)
    assert isinstance(final_settlement_summary, dict)
    overbid_summary["status"] = overbid_status
    final_settlement_summary["overbid_status"] = overbid_status

    assert_schema_valid(data)


def test_mutating_valid_output_does_not_modify_original() -> None:
    original = build_valid_output_with_optional_results()
    mutated = copy.deepcopy(original)
    mutated.pop("profile_preset_settings")

    assert_schema_valid(original)
    assert_schema_invalid(mutated)
