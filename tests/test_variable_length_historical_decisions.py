import copy
from dataclasses import asdict

import pytest
from test_dataset_partition_audit import rename_players
from test_historical_declarer_concession import build_concession_prefix
from test_historical_game import build_historical_input
from test_historical_opponent_profiles import (
    build_profile_inputs,
    stub_expected_value_recommendation,
)
from test_training_dataset import build_training_input

from skatmind.dataset_partition_audit import audit_training_dataset_partitions
from skatmind.deck import get_full_deck
from skatmind.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot_summary,
)
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_historical_game_summary_from_input,
)
from skatmind.historical_game_review import build_historical_game_review_summary
from skatmind.rules import get_legal_cards, get_trick_winner
from skatmind.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)


def build_twenty_nine_play_concession() -> dict:
    cards = get_full_deck()
    player_ids = ["player-a", "player-b", "player-c"]
    hands = {
        player_id: list(cards[index * 10 : (index + 1) * 10])
        for index, player_id in enumerate(player_ids)
    }
    replay_hands = copy.deepcopy(hands)
    leader_index = 0
    tricks = []
    for trick_number in range(1, 11):
        order = [player_ids[(leader_index + offset) % 3] for offset in range(3)]
        trick_cards = []
        plays = []
        for player_id in order:
            legal_cards = get_legal_cards(replay_hands[player_id], trick_cards, "grand")
            card = legal_cards[0]
            replay_hands[player_id].remove(card)
            trick_cards.append(card)
            plays.append({"player_id": player_id, "card": card})
        winner_index = get_trick_winner(trick_cards, "grand")
        leader_index = player_ids.index(order[winner_index])
        tricks.append(
            {
                "trick_number": trick_number,
                "leader_player_id": order[0],
                "plays": plays,
            }
        )

    declarer_player_id = tricks[-1]["plays"][-1]["player_id"]
    tricks[-1]["plays"].pop()
    return {
        "schema_version": 1,
        "game_id": "twenty-nine-play-concession",
        "played_at": "2026-07-27T18:00:00Z",
        "players": [
            {
                "player_id": player_id,
                "seat": seat,
                "initial_hand": hands[player_id],
            }
            for player_id, seat in zip(
                player_ids, ("forehand", "middlehand", "rearhand"), strict=True
            )
        ],
        "skat": cards[30:],
        "declarer_player_id": declarer_player_id,
        "declaration": {
            "game_type": "grand",
            "hand_game": True,
            "bid_value": 18,
        },
        "discarded_cards": [],
        "game_end_reason": "declarer_concession",
        "game_end": {
            "schema_version": 1,
            "kind": "declarer_concession",
            "declarer_hand_cards_remaining": 1,
            "defender_consent": {
                "status": "granted",
                "consenting_defender_player_ids": [
                    player_id
                    for player_id in player_ids
                    if player_id != declarer_player_id
                ][:1],
            },
        },
        "tricks": tricks,
    }


@pytest.mark.parametrize(
    ("game", "expected_count"),
    [
        (build_concession_prefix(), 0),
        (build_concession_prefix(current_trick_card_count=1), 1),
        (build_concession_prefix(current_trick_card_count=2), 2),
        (build_concession_prefix(completed_trick_count=1), 3),
        (build_concession_prefix(completed_trick_count=4), 12),
        (build_concession_prefix(completed_trick_count=4, current_trick_card_count=1), 13),
        (build_concession_prefix(completed_trick_count=4, current_trick_card_count=2), 14),
        (build_twenty_nine_play_concession(), 29),
    ],
)
def test_snapshot_count_matches_every_supplied_play(game: dict, expected_count: int) -> None:
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(game)
    )

    assert snapshots.snapshot_count == expected_count
    assert [snapshot.decision_index for snapshot in snapshots.snapshots] == list(
        range(1, expected_count + 1)
    )


def test_incomplete_trick_snapshots_preserve_pre_play_state_and_completed_points() -> None:
    summary = build_historical_game_summary_from_input(
        build_concession_prefix(completed_trick_count=4, current_trick_card_count=2)
    )
    snapshots = build_historical_decision_snapshots(summary)
    first_partial, second_partial = snapshots.snapshots[-2:]

    assert first_partial.visible_state.current_trick == ()
    assert len(second_partial.visible_state.current_trick) == 1
    assert len(first_partial.visible_state.completed_tricks) == 4
    assert len(second_partial.visible_state.completed_tricks) == 4
    assert first_partial.visible_state.declarer_trick_points == (
        second_partial.visible_state.declarer_trick_points
    )
    assert first_partial.visible_state.defender_trick_points == (
        second_partial.visible_state.defender_trick_points
    )
    assert first_partial.actual_card_played in first_partial.visible_state.own_hand
    assert first_partial.actual_card_played in first_partial.visible_state.legal_cards
    assert [size.remaining_card_count for size in first_partial.visible_state.opponent_hand_sizes]
    assert snapshots.snapshots[-1].acting_player_id != summary["incomplete_current_trick"][
        "next_player_id"
    ]


def _decision_state(snapshot) -> dict:
    serialized = asdict(snapshot)
    for key in ("source_game_id", "source_played_at"):
        serialized.pop(key, None)
    return serialized


def test_shared_prefix_and_consent_choices_do_not_change_decision_time_information() -> None:
    normal = build_historical_input()
    concession = build_concession_prefix(
        completed_trick_count=4, current_trick_card_count=2
    )
    concession["played_at"] = normal.get("played_at")
    normal_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(normal)
    )
    concession_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(concession)
    )

    assert [_decision_state(snapshot) for snapshot in concession_snapshots.snapshots] == [
        _decision_state(snapshot)
        for snapshot in normal_snapshots.snapshots[: concession_snapshots.snapshot_count]
    ]

    both_consents = copy.deepcopy(concession)
    both_consents["game_end"]["defender_consent"][
        "consenting_defender_player_ids"
    ] = ["player-a", "player-c"]
    consent_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(both_consents)
    )
    assert [_decision_state(snapshot) for snapshot in consent_snapshots.snapshots] == [
        _decision_state(snapshot) for snapshot in concession_snapshots.snapshots
    ]
    visible_states = [
        row["visible_state"]
        for row in build_serializable_historical_decision_snapshot_summary(
            concession_snapshots
        )["snapshots"]
    ]
    serialized_visible_states = str(visible_states)
    assert "concession" not in serialized_visible_states
    assert "consent" not in serialized_visible_states
    assert "settlement" not in serialized_visible_states


def test_empty_and_variable_reviews_reconcile_actual_player_counts(monkeypatch) -> None:
    monkeypatch.setattr(
        "skatmind.historical_game_review.recommend_card_by_expected_value",
        stub_expected_value_recommendation,
    )
    for game, expected_count in (
        (build_concession_prefix(), 0),
        (build_concession_prefix(completed_trick_count=4, current_trick_card_count=2), 14),
    ):
        record = build_historical_game_record(game)
        snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
        review = build_historical_game_review_summary(
            snapshots, record, sample_count=1, base_random_seed=42
        )

        assert review["decision_count"] == expected_count
        assert review["reviewed_decision_count"] + review[
            "unavailable_decision_count"
        ] == expected_count
        assert sum(review["quality_counts"].values()) == expected_count
        assert sum(row["decision_count"] for row in review["player_summaries"]) == (
            expected_count
        )
        assert len(review["player_summaries"]) == 3
        assert [decision["effective_random_seed"] for decision in review["decisions"]] == list(
            range(42, 42 + expected_count)
        )
    assert review["decision_count"] == 14


def test_training_samples_follow_shared_cardinality_and_prefix_features() -> None:
    normal = build_historical_input()
    shortened = build_concession_prefix(
        completed_trick_count=4, current_trick_card_count=2
    )
    zero = build_concession_prefix()
    data = build_training_input(
        [normal, shortened, zero], ["train", "validation", "test"]
    )
    summary = build_training_dataset_summary(build_training_dataset_input(data))

    assert summary["sample_count"] == 44
    assert [record["sample_count"] for record in summary["records"]] == [30, 14, 0]
    assert summary["partition_counts"] == {
        "train": {"record_count": 1, "sample_count": 30},
        "validation": {"record_count": 1, "sample_count": 14},
        "test": {"record_count": 1, "sample_count": 0},
    }
    shortened_samples = summary["records"][1]["samples"]
    assert [sample["sample_id"] for sample in shortened_samples] == [
        f"record-002:{index}" for index in range(1, 15)
    ]
    assert [sample["features"] for sample in shortened_samples] == [
        sample["features"] for sample in summary["records"][0]["samples"][:14]
    ]
    assert [sample["label"] for sample in shortened_samples] == [
        sample["label"] for sample in summary["records"][0]["samples"][:14]
    ]
    assert summary["feature_generation_version"] == 1
    assert summary["target"] == "actual_card_played"
    assert "game_end" not in str([sample["features"] for sample in shortened_samples])

    both_consents = copy.deepcopy(shortened)
    both_consents["game_end"]["defender_consent"][
        "consenting_defender_player_ids"
    ] = ["player-a", "player-c"]
    consent_summary = build_training_dataset_summary(
        build_training_dataset_input(build_training_input([both_consents]))
    )
    assert [sample["features"] for sample in consent_summary["records"][0]["samples"]] == [
        sample["features"] for sample in shortened_samples
    ]


def test_all_zero_sample_dataset_and_partition_audit_keep_record_membership() -> None:
    data = build_training_input([build_concession_prefix()], ["train"])
    dataset = build_training_dataset_input(data)
    summary = build_training_dataset_summary(dataset)
    audit = audit_training_dataset_partitions(dataset, "known_opponent")

    assert summary["record_count"] == 1
    assert summary["sample_count"] == 0
    assert summary["records"][0]["samples"] == []
    assert audit.partition_summary["train"]["record_count"] == 1
    assert audit.partition_summary["train"]["distinct_player_count"] == 3
    assert len(audit.players) == 3


def test_shortened_unseen_player_policy_remains_strict() -> None:
    first = build_concession_prefix()
    second = copy.deepcopy(first)
    second["game_id"] = "second-zero-decision-concession"
    overlapping = build_training_input([first, second], ["train", "validation"])
    overlapping["partition_policy"] = {
        "policy_version": 1,
        "mode": "unseen_player",
    }
    with pytest.raises(ValueError, match="unseen_player.*Conflicting players"):
        build_training_dataset_input(overlapping)

    disjoint_second = rename_players(
        second,
        {
            "player-a": "player-d",
            "player-b": "player-e",
            "player-c": "player-f",
        },
    )
    disjoint = build_training_input([first, disjoint_second], ["train", "validation"])
    disjoint["partition_policy"] = {
        "policy_version": 1,
        "mode": "unseen_player",
    }
    dataset = build_training_dataset_input(disjoint)
    audit = audit_training_dataset_partitions(dataset, "unseen_player")
    assert audit.compliance_status == "compliant"
    assert audit.unseen_player_compliance["player_disjoint"] is True


def test_shortened_external_profile_review_applies_only_to_actual_decisions(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_game_review.recommend_card_by_expected_value",
        stub_expected_value_recommendation,
    )
    historical_data = build_concession_prefix(
        completed_trick_count=4, current_trick_card_count=2
    )
    historical_data["played_at"] = "2026-07-27T18:00:00+02:00"
    record, _, snapshots, bindings = build_profile_inputs(historical_data=historical_data)
    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        opponent_profile_bindings=bindings,
    )

    assert review["decision_count"] == 14
    assert review["opponent_profile_application_counts"]["total_decisions"] == 14
    assert all("opponent_profile_application" in row for row in review["decisions"])

    zero_data = build_concession_prefix()
    zero_data["played_at"] = "2026-07-27T18:00:00+02:00"
    zero_record, _, zero_snapshots, zero_bindings = build_profile_inputs(
        historical_data=zero_data
    )
    zero_review = build_historical_game_review_summary(
        zero_snapshots,
        zero_record,
        sample_count=1,
        opponent_profile_bindings=zero_bindings,
    )
    assert zero_review["opponent_profile_application_counts"] == {
        "total_decisions": 0,
        "decisions_with_matched_opponent_profile": 0,
        "decisions_with_applied_left_profile": 0,
        "decisions_with_applied_right_profile": 0,
        "decisions_with_no_actionable_external_profile": 0,
        "application_counts_by_player_id": {},
        "application_counts_by_preset": {},
    }
