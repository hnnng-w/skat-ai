import copy
import json
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest
from test_historical_declarer_card_exposure import build_exposure_prefix
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_defender_open_play import build_open_play_prefix
from test_historical_game import build_stub_expected_value_recommendation
from test_historical_open_card_throw import build_throw_prefix
from test_historical_search_review import _fake_immediate, _fake_search
from test_input_schema import INPUT_VALIDATOR
from test_output_schema import OUTPUT_VALIDATOR
from test_training_dataset import build_training_input

from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_historical_game_summary_from_input,
)
from skatmind.historical_game_event import build_historical_game_event_chain_context
from skatmind.historical_game_review import build_historical_game_review_summary
from skatmind.historical_opponent_statistics import aggregate_historical_opponent_statistics
from skatmind.historical_play_prefix import replay_historical_state_at_play_boundary
from skatmind.historical_search_review import build_historical_search_review_summary
from skatmind.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skatmind.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)

ROOT = Path(__file__).resolve().parents[1]
TERMINAL_BUILDERS = {
    "declarer_concession": lambda: build_concession_prefix(
        completed_trick_count=5,
        current_trick_card_count=2,
    ),
    "defender_concession": lambda: build_defender_concession_prefix(
        completed_trick_count=5,
        current_trick_card_count=2,
    ),
    "declarer_card_exposure": lambda: build_exposure_prefix(
        completed_trick_count=5,
        current_trick_card_count=2,
    ),
    "defender_open_play": lambda: build_open_play_prefix(
        completed_trick_count=5,
        current_trick_card_count=2,
    ),
    "open_card_throw": lambda: build_throw_prefix(
        completed_trick_count=5,
        current_trick_card_count=2,
    ),
}
CONTINUATION_KINDS = (
    "defender_open_play_continuation",
    "declarer_card_exposure_continuation",
)


def add_continuation(data: dict, kind: str, after_play_count: int = 12) -> dict:
    data = copy.deepcopy(data)
    record = build_historical_game_record(data)
    replay = replay_historical_state_at_play_boundary(record, after_play_count)
    defender_ids = [
        player.player_id
        for player in record.players
        if player.player_id != record.declarer_player_id
    ]
    if kind == "defender_open_play_continuation":
        exposing_id = defender_ids[0]
        event = {
            "schema_version": 1,
            "kind": kind,
            "after_play_count": after_play_count,
            "exposing_defender_player_id": exposing_id,
            "exposed_cards": list(replay.remaining_hand_for(exposing_id)),
            "declarer_response": "request_continued_play",
        }
    else:
        event = {
            "schema_version": 1,
            "kind": kind,
            "after_play_count": after_play_count,
            "exposure": {
                "form": "shown_to_defender",
                "shown_to_defender_player_id": defender_ids[0],
            },
            "claimed_play_level": "simple",
            "defender_responses": [
                {
                    "defender_player_id": defender_ids[0],
                    "response": "accept",
                    "form": "explicit",
                },
                {
                    "defender_player_id": defender_ids[1],
                    "response": "continue",
                    "form": "unambiguous_conduct",
                },
            ],
            "public_declarer_cards": list(
                replay.remaining_hand_for(record.declarer_player_id)
            ),
        }
    data["game_events"] = [event]
    return data


def snapshot_without_source(snapshot) -> dict:
    result = asdict(snapshot)
    result.pop("source_game_id")
    result.pop("source_played_at")
    return result


@pytest.mark.parametrize("continuation_kind", CONTINUATION_KINDS)
@pytest.mark.parametrize("terminal_kind", TERMINAL_BUILDERS)
def test_all_continuation_and_terminal_combinations_delegate_unchanged(
    continuation_kind: str,
    terminal_kind: str,
) -> None:
    terminal_data = TERMINAL_BUILDERS[terminal_kind]()
    terminal_summary = build_historical_game_summary_from_input(terminal_data)
    chain_data = add_continuation(terminal_data, continuation_kind)
    chain_summary = build_historical_game_summary_from_input(chain_data)
    event = chain_summary["historical_game_events_summary"]["events"][0]

    delegated_fields = set(terminal_summary) - {"record"}
    assert all(chain_summary[field] == terminal_summary[field] for field in delegated_fields)
    assert chain_summary["historical_game_end_summary"]["kind"] == terminal_kind
    assert event["actual_plays_after_event"] == 5
    assert event["final_game_end_reason"] == terminal_kind
    assert event["final_outcome_source"] == "subsequent_terminal_shortening"
    assert event["exact_proof_applied"] is False
    assert event["game_end_applied"] is False
    assert event["settlement_applied"] is False
    assert build_historical_game_summary_from_input(chain_summary["record"]) == chain_summary
    assert list(INPUT_VALIDATOR.iter_errors({"historical_game_input": chain_data})) == []
    output = {
        "input_file": "event-chain.json",
        "historical_game_summary": chain_summary,
    }
    assert list(OUTPUT_VALIDATOR.iter_errors(output)) == []


@pytest.mark.parametrize("continuation_kind", CONTINUATION_KINDS)
def test_terminal_shortening_may_be_immediate_at_the_continuation_boundary(
    continuation_kind: str,
) -> None:
    data = TERMINAL_BUILDERS["defender_concession"]()
    data = add_continuation(data, continuation_kind, after_play_count=17)
    summary = build_historical_game_summary_from_input(data)
    event = summary["historical_game_events_summary"]["events"][0]
    snapshots = build_historical_decision_snapshots(summary)

    assert event["actual_plays_after_event"] == 0
    assert event["first_affected_decision_index"] == 18
    assert snapshots.snapshot_count == 17
    assert all(
        not snapshot.visible_state.public_exposed_cards
        for snapshot in snapshots.snapshots
    )


def test_terminal_end_before_the_continuation_is_rejected() -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "defender_open_play_continuation",
    )
    data["game_events"][0]["after_play_count"] = 18

    with pytest.raises(ValueError, match="exceeds the final recorded play count"):
        build_historical_game_record(data)


def test_terminal_shortening_after_all_thirty_plays_is_rejected() -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "defender_open_play_continuation",
    )
    normal = json.loads(
        (ROOT / "examples" / "historical_grand_normal_completion.json").read_text(
            encoding="utf-8"
        )
    )["historical_game_input"]
    data["tricks"] = copy.deepcopy(normal["tricks"])

    with pytest.raises(ValueError, match="before all 30 plays"):
        build_historical_game_record(data)


def test_chain_rejects_an_incomplete_trick_before_later_recorded_cards() -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](),
        "defender_open_play_continuation",
    )
    data["tricks"][3]["plays"] = data["tricks"][3]["plays"][:2]

    with pytest.raises(ValueError, match="only the final historical trick"):
        build_historical_game_record(data)


def test_chain_requires_the_terminal_object_to_match_its_reason() -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "declarer_card_exposure_continuation",
    )
    data["game_end"]["kind"] = "defender_concession"

    with pytest.raises(ValueError, match="kind must match game_end_reason"):
        build_historical_game_record(data)


def test_chain_context_is_immutable_and_records_exact_chronology() -> None:
    record = build_historical_game_record(
        add_continuation(
            TERMINAL_BUILDERS["declarer_concession"](),
            "defender_open_play_continuation",
        )
    )
    context = build_historical_game_event_chain_context(record)

    assert context.continuation_event is record.game_events[0]
    assert context.continuation_play_boundary == 12
    assert context.final_recorded_play_count == 17
    assert len(context.plays_after_continuation) == 5
    assert context.final_game_end_reason == "declarer_concession"
    assert context.terminal_shortening is True
    with pytest.raises(FrozenInstanceError):
        context.final_recorded_play_count = 18


@pytest.mark.parametrize("continuation_kind", CONTINUATION_KINDS)
def test_final_public_hand_must_reconcile_exactly(continuation_kind: str) -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        continuation_kind,
    )
    card_field = (
        "exposed_cards"
        if continuation_kind == "defender_open_play_continuation"
        else "public_declarer_cards"
    )
    data["game_events"][0][card_field].pop()

    with pytest.raises(ValueError, match="exactly equal"):
        build_historical_game_record(data)


def test_post_event_wrong_owner_and_card_reuse_are_rejected() -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "declarer_card_exposure_continuation",
    )
    public_card = data["game_events"][0]["public_declarer_cards"][0]
    data["tricks"][4]["plays"][0]["card"] = public_card

    with pytest.raises(ValueError, match="does not own remaining card"):
        build_historical_game_record(data)


@pytest.mark.parametrize("continuation_kind", CONTINUATION_KINDS)
def test_later_terminal_evidence_does_not_change_shared_prefix_snapshots(
    monkeypatch,
    continuation_kind: str,
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_game_review.recommend_card_by_expected_value",
        build_stub_expected_value_recommendation,
    )
    first_terminal = TERMINAL_BUILDERS["declarer_concession"]()
    second_terminal = TERMINAL_BUILDERS["defender_concession"]()
    second_terminal["game_id"] = first_terminal["game_id"]
    first = add_continuation(first_terminal, continuation_kind)
    second = add_continuation(second_terminal, continuation_kind)
    first_record = build_historical_game_record(first)
    second_record = build_historical_game_record(second)
    first_rows = build_historical_decision_snapshots(
        build_historical_game_summary(first_record)
    )
    second_rows = build_historical_decision_snapshots(
        build_historical_game_summary(second_record)
    )

    assert [snapshot_without_source(row) for row in first_rows.snapshots] == [
        snapshot_without_source(row) for row in second_rows.snapshots
    ]
    assert all(
        not row.visible_state.public_exposed_cards for row in first_rows.snapshots[:12]
    )
    assert all(
        row.visible_state.public_exposed_cards for row in first_rows.snapshots[12:]
    )
    first_review = build_historical_game_review_summary(
        first_rows,
        first_record,
        sample_count=1,
        base_random_seed=7,
    )
    second_review = build_historical_game_review_summary(
        second_rows,
        second_record,
        sample_count=1,
        base_random_seed=7,
    )
    assert first_review == second_review


def test_review_search_training_and_statistics_use_only_actual_plays(monkeypatch) -> None:
    monkeypatch.setattr(
        "skatmind.historical_game_review.recommend_card_by_expected_value",
        build_stub_expected_value_recommendation,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _fake_search,
    )
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "defender_open_play_continuation",
    )
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)
    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=3,
    )
    search_review = build_historical_search_review_summary(
        snapshots,
        record,
        base_search_seed=5,
        immediate_sample_count=1,
    )
    dataset = build_training_dataset_input(build_training_input([data], ["train"]))
    training = build_training_dataset_summary(dataset)
    statistics = aggregate_historical_opponent_statistics(dataset)

    assert snapshots.snapshot_count == 17
    assert review["decision_count"] == 17
    assert search_review["decision_counts"]["decision_count"] == 17
    assert training["sample_count"] == 17
    assert statistics.source_game_count == 1
    serialized_samples = json.dumps(training["records"][0]["samples"])
    for forbidden in (
        "game_end",
        "defender_consent",
        "final_settlement_summary",
        "request_continued_play",
    ):
        assert forbidden not in serialized_samples


def test_rolling_evaluation_uses_chain_card_plays_without_terminal_targets() -> None:
    source = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "defender_open_play_continuation",
    )
    source["played_at"] = "2026-07-10T12:00:00Z"
    target = copy.deepcopy(source)
    target["game_id"] = "historical-chain-rolling-target"
    target["played_at"] = "2026-07-11T12:00:00Z"
    dataset = build_training_dataset_input(
        build_training_input([source, target], ["train", "validation"])
    )
    result = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(dataset)
    )

    assert result["selection"]["source_record_count"] == 1
    assert result["selection"]["target_decision_count"] == 17
    assert result["target_games"][0]["decision_count"] == 17
    serialized_decisions = json.dumps(result["target_games"][0]["decisions"])
    for forbidden in ("game_end", "defender_consent", "request_continued_play"):
        assert forbidden not in serialized_decisions


def test_normal_completion_with_each_continuation_remains_supported() -> None:
    for example_name in (
        "historical_grand_defender_open_play_continuation.json",
        "historical_grand_declarer_card_exposure_continuation.json",
    ):
        data = json.loads((ROOT / "examples" / example_name).read_text(encoding="utf-8"))
        summary = build_historical_game_summary_from_input(data["historical_game_input"])
        event = summary["historical_game_events_summary"]["events"][0]

        assert event["actual_plays_after_event"] == 18
        assert event["final_game_end_reason"] == "normal_completion"
        assert event["final_outcome_source"] == "actual_continued_play"
