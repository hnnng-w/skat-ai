import copy
import json
from functools import lru_cache
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from skat_ai.dataset_partition_audit import (
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
)
from skat_ai.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot_summary,
)
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_profile_binding import (
    resolve_historical_opponent_profile_bindings,
)
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_historical_opponent_statistics_aggregation_summary,
)
from skat_ai.input_loader import (
    load_historical_game_from_json,
    load_opponent_statistics_from_json,
    load_training_dataset_from_json,
)
from skat_ai.opponent_statistics import build_opponent_statistics_summary
from skat_ai.post_game_review import build_unavailable_post_game_review_summary
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.training_dataset import build_training_dataset_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "output.schema.json"
HISTORICAL_DECISION_SNAPSHOT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_decision_snapshot.schema.json"
)
HISTORICAL_GAME_REVIEW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_game_review.schema.json"
)
HISTORICAL_GAME_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game.schema.json"
TRAINING_DATASET_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "training_dataset_output.schema.json"
)
OPPONENT_STATISTICS_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "opponent_statistics_output.schema.json"
)
OPPONENT_PROFILE_DERIVATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "opponent_profile_derivation.schema.json"
)
OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "opponent_profile_application.schema.json"
)
HISTORICAL_OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_opponent_profile_application.schema.json"
)
HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "historical_opponent_statistics_aggregation.schema.json"
)
ROLLING_OPPONENT_POLICY_EVALUATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "rolling_opponent_policy_evaluation.schema.json"
)
DATASET_PARTITION_POLICY_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "dataset_partition_policy.schema.json"
)
DATASET_PARTITION_AUDIT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "dataset_partition_audit.schema.json"
)
DECLARER_CONCESSION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "declarer_concession_output.schema.json"
)
DEFENDER_CONCESSION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "defender_concession_output.schema.json"
)


def load_output_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


with HISTORICAL_DECISION_SNAPSHOT_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    HISTORICAL_DECISION_SNAPSHOT_SCHEMA = json.load(file)
with HISTORICAL_GAME_REVIEW_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    HISTORICAL_GAME_REVIEW_SCHEMA = json.load(file)
with HISTORICAL_GAME_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    HISTORICAL_GAME_SCHEMA = json.load(file)
with TRAINING_DATASET_OUTPUT_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    TRAINING_DATASET_OUTPUT_SCHEMA = json.load(file)
with OPPONENT_STATISTICS_OUTPUT_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    OPPONENT_STATISTICS_OUTPUT_SCHEMA = json.load(file)
with OPPONENT_PROFILE_DERIVATION_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    OPPONENT_PROFILE_DERIVATION_SCHEMA = json.load(file)
with OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    OPPONENT_PROFILE_APPLICATION_SCHEMA = json.load(file)
with HISTORICAL_OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    HISTORICAL_OPPONENT_PROFILE_APPLICATION_SCHEMA = json.load(file)
with HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_SCHEMA_PATH.open(
    "r", encoding="utf-8"
) as file:
    HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_SCHEMA = json.load(file)
with ROLLING_OPPONENT_POLICY_EVALUATION_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    ROLLING_OPPONENT_POLICY_EVALUATION_SCHEMA = json.load(file)
with DATASET_PARTITION_POLICY_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    DATASET_PARTITION_POLICY_SCHEMA = json.load(file)
with DATASET_PARTITION_AUDIT_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    DATASET_PARTITION_AUDIT_SCHEMA = json.load(file)
with DECLARER_CONCESSION_OUTPUT_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    DECLARER_CONCESSION_OUTPUT_SCHEMA = json.load(file)
with DEFENDER_CONCESSION_OUTPUT_SCHEMA_PATH.open("r", encoding="utf-8") as file:
    DEFENDER_CONCESSION_OUTPUT_SCHEMA = json.load(file)

OUTPUT_SCHEMA_REGISTRY = Registry().with_resources(
    [
        (
            HISTORICAL_DECISION_SNAPSHOT_SCHEMA["$id"],
            Resource.from_contents(HISTORICAL_DECISION_SNAPSHOT_SCHEMA),
        ),
        (
            HISTORICAL_GAME_REVIEW_SCHEMA["$id"],
            Resource.from_contents(HISTORICAL_GAME_REVIEW_SCHEMA),
        ),
        (HISTORICAL_GAME_SCHEMA["$id"], Resource.from_contents(HISTORICAL_GAME_SCHEMA)),
        (
            TRAINING_DATASET_OUTPUT_SCHEMA["$id"],
            Resource.from_contents(TRAINING_DATASET_OUTPUT_SCHEMA),
        ),
        (
            OPPONENT_STATISTICS_OUTPUT_SCHEMA["$id"],
            Resource.from_contents(OPPONENT_STATISTICS_OUTPUT_SCHEMA),
        ),
        (
            HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_SCHEMA["$id"],
            Resource.from_contents(HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_SCHEMA),
        ),
        (
            OPPONENT_PROFILE_DERIVATION_SCHEMA["$id"],
            Resource.from_contents(OPPONENT_PROFILE_DERIVATION_SCHEMA),
        ),
        (
            OPPONENT_PROFILE_APPLICATION_SCHEMA["$id"],
            Resource.from_contents(OPPONENT_PROFILE_APPLICATION_SCHEMA),
        ),
        (
            HISTORICAL_OPPONENT_PROFILE_APPLICATION_SCHEMA["$id"],
            Resource.from_contents(HISTORICAL_OPPONENT_PROFILE_APPLICATION_SCHEMA),
        ),
        (
            ROLLING_OPPONENT_POLICY_EVALUATION_SCHEMA["$id"],
            Resource.from_contents(ROLLING_OPPONENT_POLICY_EVALUATION_SCHEMA),
        ),
        (
            DATASET_PARTITION_POLICY_SCHEMA["$id"],
            Resource.from_contents(DATASET_PARTITION_POLICY_SCHEMA),
        ),
        (
            DATASET_PARTITION_AUDIT_SCHEMA["$id"],
            Resource.from_contents(DATASET_PARTITION_AUDIT_SCHEMA),
        ),
        (
            DECLARER_CONCESSION_OUTPUT_SCHEMA["$id"],
            Resource.from_contents(DECLARER_CONCESSION_OUTPUT_SCHEMA),
        ),
        (
            DEFENDER_CONCESSION_OUTPUT_SCHEMA["$id"],
            Resource.from_contents(DEFENDER_CONCESSION_OUTPUT_SCHEMA),
        ),
    ]
)
OUTPUT_VALIDATOR = Draft202012Validator(
    load_output_schema(), registry=OUTPUT_SCHEMA_REGISTRY
)


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


def build_list_standings_summary() -> dict[str, object]:
    return {
        "rating_system": "isko_list",
        "basis": "fixed_three_player_game_results",
        "table_size": 3,
        "player_count": 3,
        "game_count": 1,
        "ranking_status": "lot_required",
        "lot_required_player_ids": ["bob", "carol"],
        "applied_lot_order": None,
        "standings": [
            {
                "rank": 1,
                "input_order": 1,
                "player_id": "alice",
                "player_label": "Alice",
                "games_played": 1,
                "declarer_games": 1,
                "defender_games": 0,
                "own_games_won": 1,
                "own_games_lost": 0,
                "defender_games_won": 0,
                "defender_games_lost": 0,
                "other_players_lost_games": 0,
                "player_game_points": 96,
                "own_game_bonus_points": 50,
                "opponent_loss_bonus_points": 0,
                "total_performance_points": 146,
            },
            {
                "rank": 2,
                "input_order": 2,
                "player_id": "bob",
                "player_label": "Bob",
                "games_played": 1,
                "declarer_games": 0,
                "defender_games": 1,
                "own_games_won": 0,
                "own_games_lost": 0,
                "defender_games_won": 0,
                "defender_games_lost": 1,
                "other_players_lost_games": 0,
                "player_game_points": 0,
                "own_game_bonus_points": 0,
                "opponent_loss_bonus_points": 0,
                "total_performance_points": 0,
            },
            {
                "rank": 2,
                "input_order": 3,
                "player_id": "carol",
                "player_label": None,
                "games_played": 1,
                "declarer_games": 0,
                "defender_games": 1,
                "own_games_won": 0,
                "own_games_lost": 0,
                "defender_games_won": 0,
                "defender_games_lost": 1,
                "other_players_lost_games": 0,
                "player_game_points": 0,
                "own_game_bonus_points": 0,
                "opponent_loss_bonus_points": 0,
                "total_performance_points": 0,
            },
        ],
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


def build_valid_historical_output() -> dict[str, object]:
    input_path = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
    record = load_historical_game_from_json(str(input_path))
    return {
        "input_file": "examples/historical_grand_normal_completion.json",
        "historical_game_summary": build_historical_game_summary(record),
    }


def build_valid_historical_output_with_decision_snapshots() -> dict[str, object]:
    data = build_valid_historical_output()
    historical_summary = data["historical_game_summary"]
    assert isinstance(historical_summary, dict)
    historical_summary["decision_snapshot_summary"] = (
        build_serializable_historical_decision_snapshot_summary(
            build_historical_decision_snapshots(historical_summary)
        )
    )
    return data


@lru_cache(maxsize=1)
def build_cached_valid_historical_output_with_game_review() -> dict[str, object]:
    data = build_valid_historical_output()
    historical_summary = data["historical_game_summary"]
    assert isinstance(historical_summary, dict)
    input_path = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
    record = load_historical_game_from_json(str(input_path))
    snapshots = build_historical_decision_snapshots(historical_summary)
    historical_summary["historical_game_review_summary"] = (
        build_historical_game_review_summary(
            snapshots,
            record,
            sample_count=1,
            base_random_seed=42,
        )
    )
    return data


def build_valid_historical_output_with_game_review() -> dict[str, object]:
    return copy.deepcopy(build_cached_valid_historical_output_with_game_review())


@lru_cache(maxsize=1)
def build_cached_valid_historical_output_with_profiles() -> dict[str, object]:
    data = build_valid_historical_output()
    historical_summary = data["historical_game_summary"]
    assert isinstance(historical_summary, dict)
    record = load_historical_game_from_json(
        str(PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json")
    )
    statistics_path = PROJECT_ROOT / "examples" / "historical_opponent_statistics.json"
    bindings = resolve_historical_opponent_profile_bindings(
        record,
        load_opponent_statistics_from_json(str(statistics_path)),
        statistics_input_file="examples/historical_opponent_statistics.json",
    )
    historical_summary["historical_game_review_summary"] = build_historical_game_review_summary(
        build_historical_decision_snapshots(historical_summary),
        record,
        sample_count=1,
        base_random_seed=42,
        opponent_profile_bindings=bindings,
    )
    data["historical_opponent_profile_application_summary"] = bindings.application_summary
    return data


def build_valid_historical_output_with_profiles() -> dict[str, object]:
    return copy.deepcopy(build_cached_valid_historical_output_with_profiles())


def build_valid_training_dataset_output() -> dict[str, object]:
    input_path = PROJECT_ROOT / "examples" / "training_dataset_normal_play.json"
    dataset = load_training_dataset_from_json(str(input_path))
    return {
        "input_file": "examples/training_dataset_normal_play.json",
        "training_dataset_summary": build_training_dataset_summary(dataset),
    }


def build_valid_opponent_statistics_output() -> dict[str, object]:
    input_path = PROJECT_ROOT / "examples" / "opponent_statistics.json"
    statistics_input = load_opponent_statistics_from_json(str(input_path))
    return {
        "input_file": "examples/opponent_statistics.json",
        "opponent_statistics_summary": build_opponent_statistics_summary(
            statistics_input
        ),
    }


def build_valid_historical_opponent_statistics_output() -> dict[str, object]:
    input_path = PROJECT_ROOT / "examples" / "training_dataset_normal_play.json"
    dataset = load_training_dataset_from_json(str(input_path))
    aggregation = aggregate_historical_opponent_statistics(
        dataset,
        included_partitions=("validation", "train"),
        before="2026-07-21T00:00:00Z",
    )
    return {
        "input_file": "examples/training_dataset_normal_play.json",
        "historical_opponent_statistics_aggregation_summary": (
            build_historical_opponent_statistics_aggregation_summary(aggregation)
        ),
    }


def build_valid_rolling_opponent_policy_evaluation_output() -> dict[str, object]:
    input_path = (
        PROJECT_ROOT / "examples" / "historical_opponent_policy_evaluation_dataset.json"
    )
    dataset = load_training_dataset_from_json(str(input_path))
    evaluation = evaluate_rolling_opponent_policy_predictions(dataset)
    return {
        "input_file": str(input_path),
        "rolling_opponent_policy_evaluation_summary": (
            build_serializable_rolling_opponent_policy_evaluation(evaluation)
        ),
    }


def build_valid_dataset_partition_audit_output() -> dict[str, object]:
    input_path = PROJECT_ROOT / "examples" / "training_dataset_partition_audit.json"
    dataset = load_training_dataset_from_json(str(input_path))
    audit = audit_training_dataset_partitions(dataset, "known_opponent")
    return {
        "input_file": str(input_path),
        "dataset_partition_audit_summary": build_serializable_dataset_partition_audit(
            audit
        ),
    }


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


def test_schema_accepts_historical_game_output_branch() -> None:
    assert_schema_valid(build_valid_historical_output())


def test_schema_accepts_historical_decision_snapshot_output_branch() -> None:
    assert_schema_valid(build_valid_historical_output_with_decision_snapshots())


def test_schema_accepts_historical_game_review_output_branch() -> None:
    assert_schema_valid(build_valid_historical_output_with_game_review())


def test_schema_accepts_historical_profile_application_output_branch() -> None:
    assert_schema_valid(build_valid_historical_output_with_profiles())


def test_schema_rejects_simple_lowest_as_applied_historical_preset() -> None:
    data = build_valid_historical_output_with_profiles()
    review = data["historical_game_summary"]["historical_game_review_summary"]
    side = review["decisions"][0]["opponent_profile_application"]["right"]
    side["applied_policy_preset"] = "simple_lowest"

    assert_schema_invalid(data)


def test_schema_accepts_training_dataset_output_branch() -> None:
    assert_schema_valid(build_valid_training_dataset_output())


def test_schema_accepts_opponent_statistics_output_branch() -> None:
    assert_schema_valid(build_valid_opponent_statistics_output())


def test_schema_accepts_historical_opponent_statistics_output_branch() -> None:
    assert_schema_valid(build_valid_historical_opponent_statistics_output())


def test_schema_accepts_rolling_opponent_policy_evaluation_output_branch() -> None:
    assert_schema_valid(build_valid_rolling_opponent_policy_evaluation_output())


def test_schema_accepts_dataset_partition_audit_output_branch() -> None:
    assert_schema_valid(build_valid_dataset_partition_audit_output())


@pytest.mark.parametrize(
    "mutation",
    [
        lambda summary: summary.update(effective_audit_mode="automatic"),
        lambda summary: summary.update(compliance_status="unknown"),
        lambda summary: summary["partition_summary"]["train"].pop("game_count"),
        lambda summary: summary["players"][0].update(
            classification="behavioral_style"
        ),
        lambda summary: summary["overlap_summary"]["train_validation"].update(
            player_count=-1
        ),
        lambda summary: summary["known_opponent_coverage"][
            "train_to_validation"
        ].update(eligibility_basis="temporally_eligible"),
        lambda summary: summary["unseen_player_compliance"].update(
            player_disjoint="yes"
        ),
    ],
)
def test_schema_rejects_invalid_dataset_partition_audit_fields(mutation) -> None:
    data = build_valid_dataset_partition_audit_output()
    mutation(data["dataset_partition_audit_summary"])

    assert_schema_invalid(data)


def test_schema_accepts_actionable_rolling_prediction_shape() -> None:
    data = build_valid_rolling_opponent_policy_evaluation_output()
    decision = data["rolling_opponent_policy_evaluation_summary"]["target_games"][0][
        "decisions"
    ][0]
    profile_prediction = copy.deepcopy(decision["baseline_prediction"])
    profile_prediction.update(
        {
            "policy_preset": "aggressive_points",
            "concrete_policy": "highest_point",
        }
    )
    decision.update(
        {
            "profile_prediction_status": "actionable",
            "profile_derivation_status": "actionable",
            "actionable_profile_preset": "aggressive_points",
            "profile_prediction": profile_prediction,
            "profile_prediction_unavailable_reason": None,
            "preferred_comparison_outcome": "both_match",
            "exact_comparison_outcome": "both_match",
        }
    )

    assert_schema_valid(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda summary: summary["selection"].__setitem__("temporal_rule", "inclusive"),
        lambda summary: summary["coverage"].__setitem__(
            "decisions_with_actionable_profile", -1
        ),
        lambda summary: summary["actionable_profile_paired_results"].__setitem__(
            "profile_preferred_card_match_rate", "unavailable"
        ),
        lambda summary: summary["target_games"][0]["decisions"][0][
            "baseline_prediction"
        ].__setitem__("preferred_cards", []),
        lambda summary: summary["target_games"][0]["baseline_results"].__setitem__(
            "unexpected", True
        ),
    ],
)
def test_schema_rejects_invalid_rolling_evaluation_fields(mutation) -> None:
    data = build_valid_rolling_opponent_policy_evaluation_output()
    mutation(data["rolling_opponent_policy_evaluation_summary"])

    assert_schema_invalid(data)


def test_schema_accepts_live_opponent_profile_application_summary() -> None:
    data = build_valid_output()
    data["opponent_profile_application_summary"] = {
        "enabled": True,
        "statistics_input_file": "examples/opponent_statistics.json",
        "use_profile_presets": True,
        "left": {
            "relative_player": "left",
            "bound_player_id": "opponent-123",
            "binding_status": "matched",
            "effective_profile_source": "external_statistics",
            "external_profile": {
                "source_type": "online_platform",
                "source_name": "Example platform",
                "source_player_id": "platform-user-456",
                "captured_at": "2026-07-23T12:00:00+02:00",
                "profile_derivation_version": 1,
                "classification": "cautious_defender",
                "derivation_status": "actionable",
                "confidence_level": "medium",
                "recommended_policy_preset": "cautious_defender",
                "actionable_policy_preset": "cautious_defender",
            },
            "application_status": "applied",
            "not_applied_reason": None,
            "applied_policy_preset": "cautious_defender",
            "effective_lead_policy": "basic_defender_lead",
            "effective_response_policy": "basic_defender_response",
        },
        "right": {
            "relative_player": "right",
            "bound_player_id": None,
            "binding_status": "not_requested",
            "effective_profile_source": "none",
            "external_profile": None,
            "application_status": "not_requested",
            "not_applied_reason": "not_requested",
            "applied_policy_preset": None,
            "effective_lead_policy": "lowest_point",
            "effective_response_policy": "lowest_point",
        },
    }

    assert_schema_valid(data)


def test_schema_rejects_simple_lowest_as_applied_external_preset() -> None:
    data = build_valid_output()
    data["opponent_profile_application_summary"] = {
        "enabled": True,
        "statistics_input_file": "examples/opponent_statistics.json",
        "use_profile_presets": True,
        "left": {
            "relative_player": "left",
            "bound_player_id": "opponent-123",
            "binding_status": "matched",
            "effective_profile_source": "external_statistics",
            "external_profile": None,
            "application_status": "applied",
            "not_applied_reason": None,
            "applied_policy_preset": "simple_lowest",
            "effective_lead_policy": "lowest_point",
            "effective_response_policy": "lowest_point",
        },
        "right": {
            "relative_player": "right",
            "bound_player_id": None,
            "binding_status": "not_requested",
            "effective_profile_source": "none",
            "external_profile": None,
            "application_status": "not_requested",
            "not_applied_reason": "not_requested",
            "applied_policy_preset": None,
            "effective_lead_policy": "lowest_point",
            "effective_response_policy": "lowest_point",
        },
    }

    assert_schema_invalid(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda summary: summary.update(schema_version=2),
        lambda summary: summary["records"][0]["normalized_profile_statistics"].update(
            solo_games_played=39
        ),
        lambda summary: summary["records"][0]["validation_metadata"].update(
            percentage_sum_tolerance_points=3.0
        ),
        lambda summary: summary["records"][0]["profile_derivation"].update(
            profile_derivation_version=2
        ),
        lambda summary: summary["records"][0]["profile_derivation"]["signals"][0].update(
            reason_code="certain_prediction"
        ),
    ],
)
def test_schema_rejects_malformed_opponent_statistics_output(mutation) -> None:
    data = build_valid_opponent_statistics_output()
    mutation(data["opponent_statistics_summary"])

    assert_schema_invalid(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda summary: summary.update(target="decision_quality"),
        lambda summary: summary["partition_counts"].pop("test"),
        lambda summary: summary["records"][0].update(sample_count=29),
        lambda summary: summary["records"][0]["samples"].pop(),
        lambda summary: summary["records"][0]["samples"][0]["features"].update(
            source_game_id="leaked-id"
        ),
        lambda summary: summary["records"][0]["samples"][0]["label"].update(
            target="recommendation"
        ),
    ],
)
def test_schema_rejects_malformed_training_dataset_output(mutation) -> None:
    data = build_valid_training_dataset_output()
    mutation(data["training_dataset_summary"])

    assert_schema_invalid(data)


def test_schema_accepts_nullable_seeds_and_ouvert_unavailable_review_branch() -> None:
    data = build_valid_historical_output_with_game_review()
    review = data["historical_game_summary"]["historical_game_review_summary"]
    review["settings"]["base_random_seed"] = None
    decision = review["decisions"][0]
    decision["status"] = "unavailable"
    decision["unavailable_reason"] = "public_exposed_cards_not_supported"
    decision["effective_random_seed"] = None
    decision["legal_cards"] = []
    decision["recommendation"] = {
        "card": None,
        "reason": "Public exposed cards are not supported.",
    }
    decision["analysis_report"] = []
    decision["post_game_review_summary"] = (
        build_unavailable_post_game_review_summary(
            reason="public_exposed_cards_not_supported",
            actual_card_played=decision["actual_card_played"],
        )
    )

    assert_schema_valid(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda review: review.update(decision_count=29),
        lambda review: review["player_summaries"].pop(),
        lambda review: review["decisions"][0]["recommendation"].update(card=None),
        lambda review: review["decisions"][0].update(analysis_report=[]),
        lambda review: review["quality_counts"].update(extra=0),
    ],
)
def test_schema_rejects_malformed_historical_game_review(mutation) -> None:
    data = build_valid_historical_output_with_game_review()
    review = data["historical_game_summary"]["historical_game_review_summary"]
    mutation(review)

    assert_schema_invalid(data)


def test_schema_rejects_malformed_historical_decision_snapshot_summary() -> None:
    data = build_valid_historical_output_with_decision_snapshots()
    historical_summary = data["historical_game_summary"]
    assert isinstance(historical_summary, dict)
    snapshot_summary = historical_summary["decision_snapshot_summary"]
    assert isinstance(snapshot_summary, dict)
    snapshot_summary["snapshot_count"] = 29

    assert_schema_invalid(data)


def test_schema_rejects_combined_position_and_historical_output_branches() -> None:
    data = build_valid_output()
    data["historical_game_summary"] = build_valid_historical_output()[
        "historical_game_summary"
    ]

    assert_schema_invalid(data)


def test_schema_rejects_combined_position_and_training_output_branches() -> None:
    data = build_valid_output()
    data["training_dataset_summary"] = build_valid_training_dataset_output()[
        "training_dataset_summary"
    ]

    assert_schema_invalid(data)


def test_schema_rejects_combined_position_and_opponent_statistics_output_branches() -> None:
    data = build_valid_output()
    data["opponent_statistics_summary"] = build_valid_opponent_statistics_output()[
        "opponent_statistics_summary"
    ]

    assert_schema_invalid(data)


@pytest.mark.parametrize(
    "missing_field",
    [
        "schema_version",
        "record",
        "derived_tricks",
        "winner",
        "game_value_summary",
        "overbid_summary",
        "final_settlement_summary",
    ],
)
def test_schema_rejects_incomplete_historical_game_summary(
    missing_field: str,
) -> None:
    data = build_valid_historical_output()
    del data["historical_game_summary"][missing_field]

    assert_schema_invalid(data)


def test_schema_accepts_structured_multi_step_and_policy_results() -> None:
    assert_schema_valid(build_valid_output_with_optional_results())


def test_schema_accepts_list_standings_summary() -> None:
    data = build_valid_output()
    data["list_standings_summary"] = build_list_standings_summary()

    assert_schema_valid(data)


def test_schema_accepts_final_list_standings_with_applied_lot_order() -> None:
    data = build_valid_output()
    summary = build_list_standings_summary()
    summary["ranking_status"] = "final"
    summary["lot_required_player_ids"] = []
    summary["applied_lot_order"] = ["carol", "bob"]
    data["list_standings_summary"] = summary

    assert_schema_valid(data)


def test_schema_rejects_inconsistent_list_standings_ranking_status() -> None:
    data = build_valid_output()
    summary = build_list_standings_summary()
    summary["ranking_status"] = "final"
    data["list_standings_summary"] = summary

    assert_schema_invalid(data)


def test_schema_rejects_malformed_list_standings_row() -> None:
    data = build_valid_output()
    data["list_standings_summary"] = build_list_standings_summary()
    summary = data["list_standings_summary"]
    assert isinstance(summary, dict)
    standings = summary["standings"]
    assert isinstance(standings, list)
    del standings[0]["total_performance_points"]

    assert_schema_invalid(data)


def test_schema_rejects_wrong_list_standings_table_size() -> None:
    data = build_valid_output()
    data["list_standings_summary"] = build_list_standings_summary()
    summary = data["list_standings_summary"]
    assert isinstance(summary, dict)
    summary["table_size"] = 4

    assert_schema_invalid(data)


def test_schema_rejects_non_three_player_list_standings_output() -> None:
    data = build_valid_output()
    data["list_standings_summary"] = build_list_standings_summary()
    summary = data["list_standings_summary"]
    assert isinstance(summary, dict)
    standings = summary["standings"]
    assert isinstance(standings, list)
    standings.pop()

    assert_schema_invalid(data)


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
        "impossible_null_declaration",
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


def test_schema_accepts_impossible_null_settlement_summary() -> None:
    data = build_valid_output()
    replacement_summary = {
        "replacement_game_type": "clubs",
        "matadors": 1,
        "hand_game": True,
        "base_value": 12,
        "minimum_game_value": 36,
        "required_game_value": 60,
    }
    overbid_summary = data["overbid_summary"]
    final_settlement_summary = data["final_settlement_summary"]
    assert isinstance(overbid_summary, dict)
    assert isinstance(final_settlement_summary, dict)
    overbid_summary["impossible_null_settlement"] = replacement_summary
    final_settlement_summary["impossible_null_settlement"] = replacement_summary

    assert_schema_valid(data)


def test_schema_accepts_structured_declarer_concession_output() -> None:
    data = build_valid_output()
    adjusted = data["adjusted_game_result_summary"]
    settlement = data["final_settlement_summary"]
    assert isinstance(adjusted, dict)
    assert isinstance(settlement, dict)
    adjusted.update(
        {
            "is_complete": True,
            "winner": "defenders",
            "game_end_reason": "declarer_concession",
            "game_end_kind": "declarer_concession",
            "outcome_source": "adjudicated",
        }
    )
    data["game_shortening_summary"] = {
        "schema_version": 1,
        "kind": "declarer_concession",
        "rule_sections": ["4.4.1"],
        "declarer_hand_cards_remaining": 9,
        "hand_card_count_reconciliation": "confirmed",
        "consent_required": False,
        "defender_consent": {
            "status": "not_required",
            "consenting_defender_count": 0,
        },
        "adjudicated_winner": "defenders",
        "remaining_points_assigned": False,
        "settlement_level_policy": (
            "declared_or_overbid_value_without_achieved_levels"
        ),
    }
    settlement["settlement_basis"] = {
        "game_end_kind": "declarer_concession",
        "outcome_source": "adjudicated",
        "forced_winner": "defenders",
        "achieved_schneider_applied": False,
        "achieved_schwarz_applied": False,
        "overbid_required_value_applied": False,
    }

    assert_schema_valid(data)


def test_schema_rejects_malformed_structured_concession_output() -> None:
    data = build_valid_output()
    data["game_shortening_summary"] = {
        "schema_version": 2,
        "kind": "declarer_concession",
    }

    assert_schema_invalid(data)


def test_schema_accepts_structured_defender_concession_output() -> None:
    data = build_valid_output()
    adjusted = data["adjusted_game_result_summary"]
    settlement = data["final_settlement_summary"]
    assert isinstance(adjusted, dict)
    assert isinstance(settlement, dict)
    adjusted.update(
        {
            "is_complete": True,
            "winner": "declarer",
            "game_end_reason": "defender_concession",
            "game_end_kind": "defender_concession",
            "outcome_source": "adjudicated",
            "winner_basis": "defender_concession",
            "decision_state_before_game_end": "undecided",
            "mandatory_level_awarded": False,
            "mandatory_level_source": None,
            "achieved_schneider_applied": False,
            "achieved_schwarz_applied": False,
            "overbid_required_value_applied": False,
        }
    )
    data["game_shortening_summary"] = {
        "schema_version": 1,
        "kind": "defender_concession",
        "rule_sections": ["4.4.3", "4.1.4"],
        "conceding_player": "left",
        "concession_form": "explicit_verbal",
        "liable_party": "defenders",
        "joint_liability": True,
        "decision_state_before_concession": "undecided",
        "adjudicated_winner": "declarer",
        "winner_basis": "defender_concession",
        "remaining_points_assigned": False,
        "continued_play_requested": False,
        "settlement_level_policy": (
            "declared_or_mandatory_value_without_optional_achieved_levels"
        ),
    }
    settlement["settlement_basis"] = {
        "game_end_kind": "defender_concession",
        "outcome_source": "adjudicated",
        "winner_basis": "defender_concession",
        "decision_state_before_game_end": "undecided",
        "mandatory_level_awarded": False,
        "mandatory_level_source": None,
        "achieved_schneider_applied": False,
        "achieved_schwarz_applied": False,
        "overbid_required_value_applied": False,
    }

    assert_schema_valid(data)


def test_schema_accepts_null_impossible_null_settlement_summary() -> None:
    data = build_valid_output()
    overbid_summary = data["overbid_summary"]
    final_settlement_summary = data["final_settlement_summary"]
    assert isinstance(overbid_summary, dict)
    assert isinstance(final_settlement_summary, dict)
    overbid_summary["impossible_null_settlement"] = None
    final_settlement_summary["impossible_null_settlement"] = None

    assert_schema_valid(data)


def test_mutating_valid_output_does_not_modify_original() -> None:
    original = build_valid_output_with_optional_results()
    mutated = copy.deepcopy(original)
    mutated.pop("profile_preset_settings")

    assert_schema_valid(original)
    assert_schema_invalid(mutated)
