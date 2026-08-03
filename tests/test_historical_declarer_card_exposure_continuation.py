import copy
import json
import random
from dataclasses import asdict
from pathlib import Path

import pytest
from test_historical_game import (
    build_historical_input,
    build_stub_expected_value_recommendation,
)
from test_input_schema import INPUT_VALIDATOR
from test_output_schema import OUTPUT_VALIDATOR
from test_training_dataset import build_training_input

from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot_summary,
)
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_historical_game_summary_from_input,
    build_serializable_historical_record,
)
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
)
from skat_ai.historical_play_prefix import replay_historical_state_at_play_boundary
from skat_ai.historical_snapshot_adapter import build_position_from_historical_snapshot
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.simulation import generate_sampled_hidden_state
from skat_ai.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMAL_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
CONTINUATION_EXAMPLE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "historical_grand_declarer_card_exposure_continuation.json"
)


def load_historical_data(path: Path = CONTINUATION_EXAMPLE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["historical_game_input"]


def build_event_record(
    after_play_count: int = 12,
    *,
    base_data: dict | None = None,
) -> dict:
    data = copy.deepcopy(base_data) if base_data is not None else load_historical_data(
        NORMAL_EXAMPLE_PATH
    )
    record = build_historical_game_record(data)
    replay = replay_historical_state_at_play_boundary(record, after_play_count)
    defender_ids = [
        player.player_id
        for player in record.players
        if player.player_id != record.declarer_player_id
    ]
    data["game_id"] = "historical-grand-declarer-exposure-continuation-test"
    data["game_events"] = [
        {
            "schema_version": 1,
            "kind": "declarer_card_exposure_continuation",
            "after_play_count": after_play_count,
            "exposure": {
                "form": "shown_to_defender",
                "shown_to_defender_player_id": defender_ids[0],
            },
            "claimed_play_level": "simple",
            "defender_responses": [
                {
                    "defender_player_id": defender_ids[1],
                    "response": "continue",
                    "form": "unambiguous_conduct",
                },
                {
                    "defender_player_id": defender_ids[0],
                    "response": "accept",
                    "form": "explicit",
                },
            ],
            "public_declarer_cards": list(
                replay.remaining_hand_for(record.declarer_player_id)
            ),
        }
    ]
    return data


def decision_state(snapshot) -> dict:
    value = asdict(snapshot)
    value.pop("source_game_id")
    value.pop("source_played_at")
    return value


def test_event_round_trips_canonically_and_preserves_normal_completion() -> None:
    data = load_historical_data()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    serialized_event = build_serializable_historical_record(record)["game_events"][0]
    event = summary["historical_game_events_summary"]["events"][0]

    assert record.game_end is None
    assert record.game_end_reason == "normal_completion"
    assert len(record.tricks) == 10
    assert sum(len(trick.plays) for trick in record.tricks) == 30
    assert serialized_event["public_declarer_cards"] == [
        "HA",
        "H10",
        "HK",
        "HQ",
        "D8",
        "D7",
    ]
    assert [
        response["defender_player_id"]
        for response in serialized_event["defender_responses"]
    ] == ["player-a", "player-c"]
    assert event["card_reconciliation"] == "confirmed"
    assert event["continuation_required"] is True
    assert event["unanimous_acceptance"] is False
    assert event["cards_remain_in_declarer_hand"] is True
    assert event["hand_physically_open"] is True
    assert event["visibility_scope"] == "all_players"
    assert event["claimed_play_level_status"] == (
        "continuation_required_no_immediate_settlement_effect"
    )
    assert event["final_game_end_reason"] == "normal_completion"
    assert build_historical_game_summary_from_input(summary["record"]) == summary

    wrapped_input = {"historical_game_input": data}
    assert list(INPUT_VALIDATOR.iter_errors(wrapped_input)) == []
    wrapped_output = {
        "input_file": str(CONTINUATION_EXAMPLE_PATH),
        "historical_game_summary": summary,
    }
    summary["decision_snapshot_summary"] = (
        build_serializable_historical_decision_snapshot_summary(
            build_historical_decision_snapshots(summary)
        )
    )
    assert list(OUTPUT_VALIDATOR.iter_errors(wrapped_output)) == []


def test_existing_records_and_defender_continuation_remain_unchanged() -> None:
    normal = build_historical_game_summary_from_input(load_historical_data(NORMAL_EXAMPLE_PATH))
    defender_data = load_historical_data(
        PROJECT_ROOT / "examples" / "historical_grand_defender_open_play_continuation.json"
    )
    defender = build_historical_game_summary_from_input(defender_data)

    assert "game_events" not in normal["record"]
    assert "historical_game_events_summary" not in normal
    assert defender["historical_game_events_summary"]["events"][0]["kind"] == (
        "defender_open_play_continuation"
    )


@pytest.mark.parametrize("after_play_count", [0, 1, 2, 12, 13, 14])
def test_supported_boundaries_replay_the_exact_state(after_play_count: int) -> None:
    data = build_event_record(after_play_count)
    record = build_historical_game_record(data)
    replay = replay_historical_state_at_play_boundary(record, after_play_count)
    event = build_historical_game_summary(record)["historical_game_events_summary"][
        "events"
    ][0]

    assert replay.played_card_count == after_play_count
    assert event["after_completed_trick_count"] == after_play_count // 3
    assert event["event_during_incomplete_trick"] is (after_play_count % 3 != 0)
    assert event["next_player_id"] == replay.next_player_id
    assert event["actual_plays_after_event"] == 30 - after_play_count


def test_boundary_after_twenty_nine_plays_requires_the_declarers_final_card() -> None:
    base_data = build_historical_input(declarer_player_id="player-c")
    data = build_event_record(29, base_data=base_data)
    summary = build_historical_game_summary_from_input(data)
    snapshots = build_historical_decision_snapshots(summary).snapshots

    assert data["game_events"][0]["public_declarer_cards"] == [
        data["tricks"][-1]["plays"][-1]["card"]
    ]
    assert all(not row.visible_state.public_exposed_cards for row in snapshots[:29])
    assert snapshots[29].visible_state.public_exposed_cards[0].cards == tuple(
        data["game_events"][0]["public_declarer_cards"]
    )


@pytest.mark.parametrize("after_play_count", [-1, True, 30, 31])
def test_invalid_boundaries_are_rejected(after_play_count) -> None:
    data = build_event_record()
    data["game_events"][0]["after_play_count"] = after_play_count

    with pytest.raises(ValueError, match="after_play_count"):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda events: events.clear(), "exactly one"),
        (lambda events: events.append(copy.deepcopy(events[0])), "exactly one"),
        (lambda events: events[0].update({"schema_version": 2}), "schema_version"),
        (lambda events: events[0].update({"kind": "future_event"}), "unsupported"),
        (lambda events: events[0].pop("exposure"), "missing required fields"),
        (lambda events: events[0].update({"extra": True}), "unsupported fields"),
    ],
)
def test_version_one_event_union_remains_strict(mutation, message: str) -> None:
    data = build_event_record()
    mutation(data["game_events"])

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    ("form", "shown_to", "accepted"),
    [
        ("laid_open", None, True),
        ("shown_to_defender", "player-a", True),
        ("shown_to_defender", "player-c", True),
        ("shown_to_defender", None, False),
        ("shown_to_defender", "player-b", False),
        ("shown_to_defender", "missing-player", False),
        ("shown_to_defender", " player-a", False),
        ("shown_to_defender", "left", False),
        ("unsupported", None, False),
    ],
)
def test_exposure_forms_require_one_exact_stable_defender(
    form: str, shown_to: str | None, accepted: bool
) -> None:
    data = build_event_record()
    exposure = {"form": form}
    if shown_to is not None:
        exposure["shown_to_defender_player_id"] = shown_to
    data["game_events"][0]["exposure"] = exposure

    if accepted:
        summary = build_historical_game_summary_from_input(data)
        assert summary["historical_game_events_summary"]["events"][0][
            "exposure_form"
        ] == form
    else:
        with pytest.raises(ValueError):
            build_historical_game_record(data)


def test_laid_open_rejects_a_shown_to_player() -> None:
    data = build_event_record()
    data["game_events"][0]["exposure"] = {
        "form": "laid_open",
        "shown_to_defender_player_id": "player-a",
    }

    with pytest.raises(ValueError, match="unsupported fields"):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    "cards",
    [
        [],
        ["HA", "HA"],
        ["X1"],
        ["HA"],
        ["HA", "H10", "HK", "HQ", "D8", "D7", "CQ"],
        ["SJ", "H10", "HK", "HQ", "D8", "D7"],
        ["SK", "H10", "HK", "HQ", "D8", "D7"],
        ["CA", "H10", "HK", "HQ", "D8", "D7"],
    ],
)
def test_public_declarer_cards_must_be_valid_unique_and_exact(cards: list[str]) -> None:
    data = build_event_record()
    data["game_events"][0]["public_declarer_cards"] = cards

    with pytest.raises(ValueError, match="public_declarer_cards"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda responses: responses.pop(), "exactly two"),
        (lambda responses: responses.append(copy.deepcopy(responses[0])), "exactly two"),
        (
            lambda responses: responses[1].update(
                {"defender_player_id": responses[0]["defender_player_id"]}
            ),
            "exactly once",
        ),
        (
            lambda responses: responses[0].update({"defender_player_id": "player-b"}),
            "defender ID",
        ),
        (
            lambda responses: responses[0].update({"defender_player_id": "left"}),
            "relative",
        ),
        (
            lambda responses: responses[0].update({"response": "maybe"}),
            "accept.*continue",
        ),
        (
            lambda responses: responses[0].update({"form": "silence"}),
            "explicit.*unambiguous_conduct",
        ),
    ],
)
def test_defender_responses_require_both_stable_defenders(mutation, message: str) -> None:
    data = build_event_record()
    mutation(data["game_events"][0]["defender_responses"])

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


def test_unanimous_acceptance_uses_the_terminal_historical_contract() -> None:
    data = build_event_record()
    for response in data["game_events"][0]["defender_responses"]:
        response["response"] = "accept"

    with pytest.raises(
        ValueError, match="game_end_reason='declarer_card_exposure'"
    ):
        build_historical_game_record(data)


@pytest.mark.parametrize("claimed_level", ["simple", "schneider", "schwarz"])
def test_grand_supports_all_claimed_levels_without_changing_declaration(
    claimed_level: str,
) -> None:
    data = build_event_record()
    data["game_events"][0]["claimed_play_level"] = claimed_level
    summary = build_historical_game_summary_from_input(data)

    assert summary["record"]["declaration"]["hand_game"] is False
    assert summary["record"]["declaration"]["ouvert"] is False
    assert summary["historical_game_events_summary"]["events"][0][
        "claimed_play_level"
    ] == claimed_level


def test_null_requires_a_simple_claim() -> None:
    base_data = build_historical_input(game_type="null", hand_game=True)
    data = build_event_record(12, base_data=base_data)
    build_historical_game_summary_from_input(data)
    data["game_events"][0]["claimed_play_level"] = "schneider"

    with pytest.raises(ValueError, match="Null.*simple"):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    "path_name",
    [
        "historical_grand_declarer_concession.json",
        "historical_grand_defender_concession.json",
        "historical_grand_declarer_card_exposure.json",
        "historical_grand_defender_open_play.json",
        "historical_grand_open_card_throw.json",
    ],
)
def test_event_cannot_be_combined_with_a_terminal_end(path_name: str) -> None:
    data = load_historical_data(PROJECT_ROOT / "examples" / path_name)
    data["game_events"] = copy.deepcopy(build_event_record()["game_events"])

    with pytest.raises(ValueError, match="requires game_end_reason='normal_completion'"):
        build_historical_game_record(data)


def test_snapshot_boundary_is_exact_and_public_hand_only_shrinks() -> None:
    event_summary = build_historical_game_summary_from_input(build_event_record())
    no_event_summary = build_historical_game_summary_from_input(
        load_historical_data(NORMAL_EXAMPLE_PATH)
    )
    event_rows = build_historical_decision_snapshots(event_summary).snapshots
    no_event_rows = build_historical_decision_snapshots(no_event_summary).snapshots

    assert len(event_rows) == 30
    assert [decision_state(row) for row in event_rows[:12]] == [
        decision_state(row) for row in no_event_rows[:12]
    ]
    assert all(not row.visible_state.public_exposed_cards for row in event_rows[:12])
    assert event_rows[12].visible_state.public_exposed_cards[0].cards == (
        "HA",
        "H10",
        "HK",
        "HQ",
        "D8",
        "D7",
    )
    assert event_rows[14].visible_state.public_exposed_cards[0].cards == (
        "H10",
        "HK",
        "HQ",
        "D8",
        "D7",
    )
    public_sets = [
        set(row.visible_state.public_exposed_cards[0].cards)
        for row in event_rows[12:]
    ]
    assert all(
        later <= earlier
        for earlier, later in zip(public_sets, public_sets[1:], strict=False)
    )
    assert event_rows[-1].visible_state.public_exposed_cards[0].cards == ()


def test_declared_ouvert_visibility_is_independent_and_deduplicated() -> None:
    data = build_historical_input(game_type="null", hand_game=True)
    data["declaration"]["ouvert"] = True
    data = build_event_record(12, base_data=data)
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(data)
    ).snapshots

    assert len(snapshots[11].visible_state.public_exposed_cards) == 1
    assert len(snapshots[12].visible_state.public_exposed_cards) == 1
    assert snapshots[11].visible_state.public_exposed_cards[0].player_id == "player-b"
    record = build_historical_game_record(data)
    position = build_position_from_historical_snapshot(snapshots[12], record)
    assert len(position.public_hand_constraints) == 1
    assert position.public_hand_constraints[0].source == "declared_ouvert"
    assert position.public_hand_constraints[0].cards == (
        snapshots[12].visible_state.public_exposed_cards[0].cards
    )


@pytest.mark.parametrize("decision_index", [13, 14, 15])
def test_review_maps_public_declarer_to_me_left_and_right(decision_index: int) -> None:
    data = build_event_record()
    record = build_historical_game_record(data)
    snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
    snapshot = snapshots.snapshots[decision_index - 1]
    position = build_position_from_historical_snapshot(snapshot, record)
    constraint = position.public_hand_constraints[0]
    expected_relative = {
        stable_id: relative
        for relative, stable_id in snapshot.relative_player_map.items()
    }[record.declarer_player_id]

    assert constraint.player == expected_relative
    assert constraint.source == "declarer_card_exposure_continuation"
    if constraint.player in {"left", "right"}:
        sampled = generate_sampled_hidden_state(
            position.state,
            position.left_hand_size,
            position.right_hand_size,
            random.Random(42),
            position.public_hand_constraints,
        )
        sampled_hand = sampled.left_hand if constraint.player == "left" else sampled.right_hand
        assert sampled_hand == list(constraint.cards)


def test_review_reuses_the_same_constraint_without_event_decisions(monkeypatch) -> None:
    captured_constraints = []

    def capture_constraint(*args, public_hand_constraints=(), **kwargs):
        captured_constraints.append(public_hand_constraints)
        return build_stub_expected_value_recommendation(
            *args,
            public_hand_constraints=public_hand_constraints,
            **kwargs,
        )

    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        capture_constraint,
    )
    data = build_event_record()
    record = build_historical_game_record(data)
    snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
    )

    assert review["decision_count"] == 30
    assert review["reviewed_decision_count"] == 30
    assert captured_constraints[:12] == [()] * 12
    assert all(len(constraints) == 1 for constraints in captured_constraints[12:])
    assert all(
        constraints[0].source == "declarer_card_exposure_continuation"
        for constraints in captured_constraints[12:]
    )


def test_training_retains_thirty_actual_card_targets_and_safe_boundary() -> None:
    event_data = build_event_record()
    dataset = build_training_dataset_input(
        build_training_input([event_data], ["train"])
    )
    training = build_training_dataset_summary(dataset)
    samples = training["records"][0]["samples"]

    assert training["feature_generation_version"] == 1
    assert training["target"] == "actual_card_played"
    assert len(samples) == 30
    assert [sample["sample_id"] for sample in samples] == [
        f"record-001:{index}" for index in range(1, 31)
    ]
    assert all(not sample["features"]["public_exposed_cards"] for sample in samples[:12])
    assert samples[12]["features"]["public_exposed_cards"][0]["cards"] == [
        "HA",
        "H10",
        "HK",
        "HQ",
        "D8",
        "D7",
    ]
    serialized_features = json.dumps([sample["features"] for sample in samples])
    for forbidden in (
        "exposure_form",
        "claimed_play_level",
        "defender_responses",
        "continuation_required",
        "final_settlement_summary",
    ):
        assert forbidden not in serialized_features


def test_final_result_statistics_and_partitions_match_no_event_game() -> None:
    normal_data = load_historical_data(NORMAL_EXAMPLE_PATH)
    event_data = build_event_record()
    event_data["game_events"][0]["claimed_play_level"] = "schneider"
    normal = build_historical_game_summary_from_input(normal_data)
    event = build_historical_game_summary_from_input(event_data)
    parity_fields = (
        "derived_tricks",
        "declarer_trick_points",
        "defender_trick_points",
        "declarer_points",
        "defender_points",
        "winner",
        "schneider_status",
        "schwarz_status",
        "game_result_summary",
        "game_value_summary",
        "overbid_summary",
        "final_settlement_summary",
    )
    assert all(normal[field] == event[field] for field in parity_fields)

    event_dataset = build_training_dataset_input(
        build_training_input([event_data], ["train"])
    )
    normal_dataset = build_training_dataset_input(
        build_training_input([normal_data], ["train"])
    )
    event_statistics = build_exportable_opponent_statistics_input(
        aggregate_historical_opponent_statistics(event_dataset)
    )
    normal_statistics = build_exportable_opponent_statistics_input(
        aggregate_historical_opponent_statistics(normal_dataset)
    )
    assert event_statistics.records == normal_statistics.records
    assert "game_events" in build_training_dataset_summary(event_dataset)["records"][0][
        "historical_game"
    ]
    audit = audit_training_dataset_partitions(event_dataset, "known_opponent")
    assert audit.partition_summary["train"]["record_count"] == 1
    assert audit.partition_summary["train"]["distinct_player_count"] == 3


def test_rolling_source_and_target_remain_one_game_and_thirty_decisions() -> None:
    source = build_event_record()
    source["played_at"] = "2026-07-10T12:00:00Z"
    target = build_event_record()
    target["game_id"] = "historical-declarer-continuation-target"
    target["played_at"] = "2026-07-11T12:00:00Z"
    dataset = build_training_dataset_input(
        build_training_input([source, target], ["train", "validation"])
    )
    result = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(dataset)
    )

    assert result["selection"]["source_record_count"] == 1
    assert result["selection"]["target_decision_count"] == 30
    assert result["target_games"][0]["decision_count"] == 30
    serialized = json.dumps(result)
    for forbidden in (
        "claimed_play_level",
        "defender_responses",
        "shown_to_defender_player_id",
        "continuation_required",
    ):
        assert forbidden not in serialized


def test_event_never_invokes_exact_rest_trick_proof(monkeypatch) -> None:
    def fail_proof(*args, **kwargs):
        raise AssertionError("The continuation event must not invoke exact proof.")

    monkeypatch.setattr("skat_ai.defender_open_play.prove_defender_rest_tricks", fail_proof)
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        build_stub_expected_value_recommendation,
    )
    data = build_event_record()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)
    review = build_historical_game_review_summary(snapshots, record, sample_count=1)
    training = build_training_dataset_summary(
        build_training_dataset_input(build_training_input([data], ["train"]))
    )

    event = summary["historical_game_events_summary"]["events"][0]
    assert review["decision_count"] == 30
    assert training["sample_count"] == 30
    assert event["exact_proof_applied"] is False
    assert event["game_end_applied"] is False
    assert event["settlement_applied"] is False
    for forbidden in ("winner", "result", "settlement", "point_assignment"):
        assert forbidden not in event


def test_package_version_is_0_10_0() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.10.0"' in pyproject
