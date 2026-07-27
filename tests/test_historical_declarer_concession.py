import copy
import json
from pathlib import Path

import pytest

from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.declarer_concession import (
    DeclarerCardCountEvidence,
    adjudicate_declarer_concession,
    build_declarer_concession,
)
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_result import build_game_result_summary_from_points
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary_from_input,
)
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
)
from skat_ai.rolling_opponent_policy_evaluation import (
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.training_dataset import (
    TrainingDatasetInput,
    TrainingDatasetRecord,
    TrainingProvenance,
    build_training_dataset_input,
    build_training_dataset_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMAL_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
CONCESSION_EXAMPLE_PATH = (
    PROJECT_ROOT / "examples" / "historical_grand_declarer_concession.json"
)


def load_historical_data(path: Path = NORMAL_EXAMPLE_PATH) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)["historical_game_input"]


def build_concession_prefix(
    *, completed_trick_count: int = 0, current_trick_card_count: int = 0
) -> dict:
    data = load_historical_data()
    tricks = copy.deepcopy(data["tricks"][:completed_trick_count])
    if current_trick_card_count:
        current = copy.deepcopy(data["tricks"][completed_trick_count])
        current["plays"] = current["plays"][:current_trick_card_count]
        tricks.append(current)
    declarer_id = data["declarer_player_id"]
    declarer_play_count = sum(
        play["player_id"] == declarer_id for trick in tricks for play in trick["plays"]
    )
    hand_count = 10 - declarer_play_count
    consent_required = hand_count < 9
    data.update(
        {
            "game_id": "test-historical-concession",
            "game_end_reason": "declarer_concession",
            "game_end": {
                "schema_version": 1,
                "kind": "declarer_concession",
                "declarer_hand_cards_remaining": hand_count,
                "defender_consent": {
                    "status": "granted" if consent_required else "not_required",
                    "consenting_defender_player_ids": ["player-a"] if consent_required else [],
                },
            },
            "tricks": tricks,
        }
    )
    return data


@pytest.mark.parametrize(
    ("completed_trick_count", "current_trick_card_count", "expected_plays"),
    [(0, 0, 0), (1, 0, 3), (4, 0, 12), (9, 0, 27), (4, 1, 13), (4, 2, 14)],
)
def test_exact_empty_complete_and_incomplete_prefixes_are_supported(
    completed_trick_count: int,
    current_trick_card_count: int,
    expected_plays: int,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_concession_prefix(
            completed_trick_count=completed_trick_count,
            current_trick_card_count=current_trick_card_count,
        )
    )

    prefix = summary["play_prefix_summary"]
    assert prefix["played_card_count"] == expected_plays
    assert prefix["completed_trick_count"] == completed_trick_count
    assert prefix["current_trick_card_count"] == current_trick_card_count
    assert sum(prefix["remaining_hand_sizes"].values()) + expected_plays == 30
    assert len(summary["derived_tricks"]) == completed_trick_count
    assert ("incomplete_current_trick" in summary) is bool(current_trick_card_count)
    if current_trick_card_count:
        assert "winner_player_id" not in summary["incomplete_current_trick"]
        assert "trick_points" not in summary["incomplete_current_trick"]


def test_concession_after_all_cards_are_played_is_rejected() -> None:
    data = build_concession_prefix(completed_trick_count=9)
    data["tricks"] = copy.deepcopy(load_historical_data()["tricks"])
    data["game_end"]["declarer_hand_cards_remaining"] = 1

    with pytest.raises(ValueError, match="after all 30 playable cards"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.pop("game_end"), "game_end is required"),
        (
            lambda data: data["game_end"].update({"kind": "defender_concession"}),
            "kind must match",
        ),
        (
            lambda data: data["game_end"].update({"schema_version": 2}),
            "schema_version must be exactly 1",
        ),
        (
            lambda data: data["game_end"].update({"extra": True}),
            "unsupported fields",
        ),
    ],
)
def test_historical_game_end_contract_is_strict(mutation, message: str) -> None:
    data = build_concession_prefix()
    mutation(data)

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


def test_normal_completion_rejects_a_game_end_object() -> None:
    data = load_historical_data()
    data["game_end"] = build_concession_prefix()["game_end"]

    with pytest.raises(ValueError, match="game_end must be absent"):
        build_historical_game_record(data)


def test_unknown_historical_game_end_reason_is_rejected() -> None:
    data = build_concession_prefix()
    data["game_end_reason"] = "defender_concession"

    with pytest.raises(ValueError, match="unsupported game_end_reason"):
        build_historical_game_record(data)


def test_only_final_trick_may_be_incomplete() -> None:
    data = build_concession_prefix(completed_trick_count=2)
    data["tricks"][0]["plays"].pop()

    with pytest.raises(ValueError, match="only the final historical trick"):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda data: data["tricks"][-1]["plays"][1].update(
                {"player_id": "player-c"}
            ),
            "play order",
        ),
        (
            lambda data: data["tricks"][-1]["plays"][0].update({"card": "SK"}),
            "unplayable skat or discarded card",
        ),
        (
            lambda data: data["tricks"][-1]["plays"][0].update({"card": "HA"}),
            "does not own remaining card",
        ),
    ],
)
def test_incomplete_prefix_validates_order_and_ownership(mutation, message: str) -> None:
    data = build_concession_prefix(completed_trick_count=4, current_trick_card_count=2)
    mutation(data)

    with pytest.raises(ValueError, match=message):
        build_historical_game_summary_from_input(data)


def test_incomplete_prefix_validates_follow_suit() -> None:
    data = build_concession_prefix(current_trick_card_count=2)
    data["tricks"][-1]["plays"][0]["card"] = "CJ"
    data["tricks"][-1]["plays"][1]["card"] = "S9"

    with pytest.raises(ValueError, match="illegally plays"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize("invalid_count", [0, 11, -1, True, 1.5])
def test_declarer_hand_count_requires_a_strict_supported_integer(invalid_count) -> None:
    data = build_concession_prefix()
    data["game_end"]["declarer_hand_cards_remaining"] = invalid_count

    with pytest.raises(ValueError, match="declarer_hand_cards_remaining"):
        build_historical_game_record(data)


def test_declarer_hand_count_must_match_exact_reconstruction() -> None:
    data = build_concession_prefix(completed_trick_count=4, current_trick_card_count=2)
    data["game_end"]["declarer_hand_cards_remaining"] = 6

    with pytest.raises(ValueError, match="exact play-prefix reconstruction"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize(
    ("completed_tricks", "hand_count", "status", "consent_ids"),
    [
        (0, 10, "not_required", []),
        (1, 9, "not_required", []),
        (2, 8, "granted", ["player-a"]),
        (9, 1, "granted", ["player-c", "player-a"]),
    ],
)
def test_stable_defender_consent_matrix_and_canonical_order(
    completed_tricks: int,
    hand_count: int,
    status: str,
    consent_ids: list[str],
) -> None:
    data = build_concession_prefix(completed_trick_count=completed_tricks)
    data["game_end"]["defender_consent"] = {
        "status": status,
        "consenting_defender_player_ids": consent_ids,
    }

    summary = build_historical_game_summary_from_input(data)

    assert summary["historical_game_end_summary"][
        "declarer_hand_cards_remaining"
    ] == hand_count
    assert summary["record"]["game_end"]["defender_consent"][
        "consenting_defender_player_ids"
    ] == [
        player_id
        for player_id in ("player-a", "player-b", "player-c")
        if player_id in consent_ids
    ]


@pytest.mark.parametrize(
    "consent_ids",
    [[], ["player-b"], ["unknown-player"], ["player-a", "player-a"]],
)
def test_required_consent_rejects_missing_non_defender_unknown_and_duplicate_ids(
    consent_ids: list[str],
) -> None:
    data = build_concession_prefix(completed_trick_count=2)
    data["game_end"]["defender_consent"]["consenting_defender_player_ids"] = consent_ids

    with pytest.raises(ValueError, match="consent|defender|duplicates"):
        build_historical_game_record(data)


def test_consent_is_rejected_when_nine_or_ten_cards_need_none() -> None:
    data = build_concession_prefix()
    data["game_end"]["defender_consent"] = {
        "status": "granted",
        "consenting_defender_player_ids": ["player-a"],
    }

    with pytest.raises(ValueError, match="9 or 10 hand cards"):
        build_historical_game_record(data)


def test_observed_and_unresolved_points_reconcile_without_assignment() -> None:
    summary = build_historical_game_summary_from_input(
        build_concession_prefix(completed_trick_count=4, current_trick_card_count=2)
    )
    points = summary["point_accounting"]

    assert points["unresolved_current_trick_points"] > 0
    assert points["unresolved_remaining_hand_points"] > 0
    assert (
        points["observed_declarer_points"]
        + points["observed_defender_points"]
        + points["total_unresolved_points"]
        == 120
    )
    assert summary["game_result_summary"]["winner"] == "defenders"
    assert summary["game_result_summary"]["outcome_source"] == "adjudicated"
    assert summary["game_result_summary"]["remaining_points_recipient"] is None
    assert summary["game_result_summary"]["remaining_points_assigned"] == 0
    assert summary["schneider_status"] == "not_applicable"
    assert summary["schwarz_status"] == "not_applicable"
    assert summary["historical_game_end_summary"]["rule_sections"] == ["4.4.2"]


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert", "expected_value"),
    [
        ("clubs", False, False, None),
        ("spades", False, False, None),
        ("hearts", False, False, None),
        ("diamonds", False, False, None),
        ("grand", False, False, None),
        ("null", False, False, 23),
        ("null", True, False, 35),
        ("null", False, True, 46),
        ("null", True, True, 59),
    ],
)
def test_suit_grand_and_all_null_variant_concessions_settle_as_losses(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
    expected_value: int | None,
) -> None:
    data = build_concession_prefix()
    data["declaration"] = {
        "game_type": game_type,
        "hand_game": hand_game,
        "ouvert": ouvert,
        "bid_value": 18,
    }
    data["discarded_cards"] = [] if hand_game else ["SK", "SQ"]

    summary = build_historical_game_summary_from_input(data)

    if expected_value is not None:
        assert summary["game_value_summary"]["game_value"] == expected_value
    assert summary["final_settlement_summary"]["is_loss"] is True
    assert summary["final_settlement_summary"]["settlement_score"] == (
        -2 * summary["final_settlement_summary"]["effective_game_value"]
    )


@pytest.mark.parametrize(
    "declaration_updates",
    [
        {"hand_game": True},
        {"hand_game": True, "schneider_announced": True},
        {
            "hand_game": True,
            "schneider_announced": True,
            "schwarz_announced": True,
        },
        {"ouvert": True},
    ],
)
def test_historical_concession_preserves_grand_declared_levels(
    declaration_updates: dict,
) -> None:
    data = build_concession_prefix()
    data["declaration"].update(declaration_updates)
    if declaration_updates.get("ouvert") is True:
        data["declaration"].pop("hand_game")
    if any(declaration_updates.values()):
        data["discarded_cards"] = []

    summary = build_historical_game_summary_from_input(data)

    declaration = summary["record"]["declaration"]
    for field_name, expected in declaration_updates.items():
        assert declaration[field_name] is expected
    assert summary["final_settlement_summary"]["is_loss"] is True
    assert summary["final_settlement_summary"]["settlement_basis"][
        "achieved_schneider_applied"
    ] is False
    assert summary["final_settlement_summary"]["settlement_basis"][
        "achieved_schwarz_applied"
    ] is False


def test_historical_concession_applies_supported_overbid_required_value() -> None:
    data = build_concession_prefix()
    data["declaration"]["bid_value"] = 121

    summary = build_historical_game_summary_from_input(data)

    overbid = summary["overbid_summary"]
    settlement = summary["final_settlement_summary"]
    assert overbid["is_overbid"] is True
    assert settlement["effective_game_value"] == overbid["required_game_value"]
    assert settlement["settlement_score"] == -2 * overbid["required_game_value"]
    assert settlement["settlement_basis"]["overbid_required_value_applied"] is True


def test_historical_and_flat_concession_settlement_are_equal() -> None:
    summary = build_historical_game_summary_from_input(
        build_concession_prefix(completed_trick_count=4, current_trick_card_count=2)
    )
    event = summary["record"]["game_end"]
    flat = build_declarer_concession(
        {
            "schema_version": 1,
            "kind": "declarer_concession",
            "declarer_hand_cards_remaining": event["declarer_hand_cards_remaining"],
            "defender_consent": {
                "status": event["defender_consent"]["status"],
                "consenting_defender_count": len(
                    event["defender_consent"]["consenting_defender_player_ids"]
                ),
            },
        }
    )
    flat_adjudication = adjudicate_declarer_concession(
        game_shortening=flat,
        game_result_summary=build_game_result_summary_from_points(
            summary["declarer_points"], summary["defender_points"]
        ),
        game_value_summary=summary["game_value_summary"],
        overbid_summary=summary["overbid_summary"],
        evidence=DeclarerCardCountEvidence(
            event["declarer_hand_cards_remaining"], "exact_historical_play_prefix"
        ),
    )
    flat_settlement = build_final_settlement_summary(
        summary["game_value_summary"],
        flat_adjudication.game_result_summary,
        summary["overbid_summary"],
    )

    assert flat_adjudication.game_result_summary["winner"] == summary["winner"]
    assert flat_settlement == summary["final_settlement_summary"]


def test_canonical_concession_round_trip_is_deterministic_and_private() -> None:
    original = build_historical_game_summary_from_input(
        load_historical_data(CONCESSION_EXAMPLE_PATH)
    )

    assert build_historical_game_summary_from_input(original["record"]) == original
    serialized = json.dumps(original)
    assert "remaining_hands" not in serialized
    assert "consenting_defender_count" not in serialized
    assert original["record"]["tricks"] == load_historical_data(CONCESSION_EXAMPLE_PATH)[
        "tricks"
    ]


def test_training_input_accepts_and_preserves_concession_records() -> None:
    training_data = {
        "schema_version": 1,
        "dataset_id": "shortened",
        "dataset_version": "1",
        "feature_generation_version": 1,
        "target": "actual_card_played",
        "records": [
            {
                "record_id": "record-1",
                "partition": "train",
                "provenance": {"source_type": "manual_entry", "source_name": "test"},
                "historical_game": build_concession_prefix(),
            }
        ],
    }
    dataset = build_training_dataset_input(training_data)

    assert dataset.records[0].historical_game.game_end_reason == "declarer_concession"
    assert build_training_dataset_summary(dataset)["sample_count"] == 0


def test_shortened_dataset_boundaries_are_workflow_specific() -> None:
    record = build_historical_game_record(build_concession_prefix())
    dataset = TrainingDatasetInput(
        schema_version=1,
        dataset_id="shortened",
        dataset_version="1",
        feature_generation_version=1,
        target="actual_card_played",
        partition_policy=None,
        records=(
            TrainingDatasetRecord(
                record_id="record-1",
                partition="train",
                provenance=TrainingProvenance(
                    source_type="manual_entry",
                    source_name="test",
                    source_record_id=None,
                    collected_at=None,
                    notes=None,
                ),
                historical_game=record,
            ),
        ),
    )

    assert build_training_dataset_summary(dataset)["sample_count"] == 0
    assert audit_training_dataset_partitions(dataset, "report_only").source_dataset[
        "total_record_count"
    ] == 1
    aggregation = aggregate_historical_opponent_statistics(dataset)
    assert aggregation.source_game_count == 1
    assert all(record.statistics_record.games_played == 1 for record in aggregation.records)
    with pytest.raises(ValueError, match="contain no target records"):
        evaluate_rolling_opponent_policy_predictions(dataset)
