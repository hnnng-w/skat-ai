import copy
import json
import re
from pathlib import Path

import pytest

from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_serializable_historical_record,
)
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_profile_application import (
    resolve_historical_opponent_profiles_for_decision,
)
from skat_ai.historical_opponent_profile_binding import (
    resolve_historical_opponent_profile_bindings,
)
from skat_ai.opponent_statistics import build_opponent_statistics_input
from skat_ai.rules import get_legal_cards

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
STATISTICS_PATH = PROJECT_ROOT / "examples" / "historical_opponent_statistics.json"


def load_historical_data() -> dict:
    with HISTORICAL_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)["historical_game_input"]


def load_statistics_data() -> dict:
    with STATISTICS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)["opponent_statistics_input"]


def build_profile_inputs(
    historical_data: dict | None = None,
    statistics_data: dict | None = None,
):
    record = build_historical_game_record(historical_data or load_historical_data())
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)
    statistics_input = build_opponent_statistics_input(statistics_data or load_statistics_data())
    bindings = resolve_historical_opponent_profile_bindings(
        record,
        statistics_input,
        statistics_input_file=str(STATISTICS_PATH),
    )
    return record, summary, snapshots, bindings


@pytest.mark.parametrize(
    "played_at",
    [
        "2026-07-24T18:30:00+02:00",
        "2026-07-24T09:30:00-07:00",
        "2026-07-24T16:30:00Z",
    ],
)
def test_historical_played_at_is_optional_and_preserved(played_at: str) -> None:
    data = load_historical_data()
    data["played_at"] = played_at

    record = build_historical_game_record(data)
    serialized = build_serializable_historical_record(record)
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)

    assert record.played_at == played_at
    assert serialized["played_at"] == played_at
    assert summary["played_at"] == played_at
    assert {snapshot.source_played_at for snapshot in snapshots.snapshots} == {played_at}


def test_historical_game_without_played_at_remains_valid_without_profiles() -> None:
    data = load_historical_data()
    data.pop("played_at")

    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)

    assert record.played_at is None
    assert "played_at" not in build_serializable_historical_record(record)
    assert "played_at" not in summary


@pytest.mark.parametrize(
    "played_at",
    ["not-a-time", "2026-07-24T18:30:00", "2026-02-30T18:30:00+02:00"],
)
def test_historical_played_at_rejects_invalid_or_offsetless_values(
    played_at: str,
) -> None:
    data = load_historical_data()
    data["played_at"] = played_at

    with pytest.raises(ValueError, match="played_at.*RFC 3339.*offset"):
        build_historical_game_record(data)


def test_historical_profiles_require_played_at() -> None:
    data = load_historical_data()
    data.pop("played_at")
    record = build_historical_game_record(data)
    statistics_input = build_opponent_statistics_input(load_statistics_data())

    with pytest.raises(ValueError, match="played_at.*required"):
        resolve_historical_opponent_profile_bindings(
            record,
            statistics_input,
            statistics_input_file=str(STATISTICS_PATH),
        )


@pytest.mark.parametrize(
    ("captured_at", "played_at"),
    [
        ("2026-07-24T18:30:00+02:00", "2026-07-24T18:30:00+02:00"),
        ("2026-07-24T18:30:01+02:00", "2026-07-24T18:30:00+02:00"),
        ("2026-07-24T16:30:00Z", "2026-07-24T18:30:00+02:00"),
    ],
)
def test_matched_capture_must_be_strictly_before_game_start(
    captured_at: str,
    played_at: str,
) -> None:
    historical_data = load_historical_data()
    historical_data["played_at"] = played_at
    statistics_data = load_statistics_data()
    statistics_data["records"][0]["source"]["captured_at"] = captured_at

    with pytest.raises(
        ValueError,
        match=rf"player-a.*{re.escape(captured_at)}.*{re.escape(played_at)}",
    ):
        build_profile_inputs(historical_data, statistics_data)


def test_all_matched_captures_are_checked_but_unmatched_records_are_ignored() -> None:
    statistics_data = load_statistics_data()
    statistics_data["records"][1]["source"]["captured_at"] = "2026-07-25T08:15:00Z"

    with pytest.raises(ValueError, match="player-c.*2026-07-25"):
        build_profile_inputs(statistics_data=statistics_data)

    statistics_data["records"][1]["player_id"] = "not-a-participant"
    _, _, _, bindings = build_profile_inputs(statistics_data=statistics_data)
    assert set(bindings.profiles_by_player_id) == {"player-a"}


@pytest.mark.parametrize("matched_player_count", [1, 2, 3])
def test_exact_participant_matching_supports_partial_and_complete_coverage(
    matched_player_count: int,
) -> None:
    statistics_data = load_statistics_data()
    if matched_player_count == 1:
        statistics_data["records"] = statistics_data["records"][:1]
    elif matched_player_count == 3:
        third = copy.deepcopy(statistics_data["records"][0])
        third["player_id"] = "player-b"
        third["player_label"] = "Bob"
        statistics_data["records"].append(third)
    statistics_data["records"].append(
        {
            **copy.deepcopy(statistics_data["records"][0]),
            "player_id": "extra-player",
        }
    )

    record, _, _, bindings = build_profile_inputs(statistics_data=statistics_data)
    application_summary = bindings.application_summary

    assert application_summary["matched_player_count"] == matched_player_count
    assert len(bindings.profiles_by_player_id) == matched_player_count
    assert len(application_summary["participant_matches"]) == 3
    assert "extra-player" not in bindings.profiles_by_player_id
    assert set(application_summary["unmatched_player_ids"]) == {
        player.player_id
        for player in record.players
        if player.player_id not in bindings.profiles_by_player_id
    }


def test_matching_is_case_sensitive_and_zero_matches_are_rejected() -> None:
    statistics_data = load_statistics_data()
    statistics_data["records"][0]["player_id"] = "PLAYER-A"
    statistics_data["records"][1]["player_id"] = "PLAYER-C"

    with pytest.raises(ValueError, match="No opponent-statistics records.*participants"):
        build_profile_inputs(statistics_data=statistics_data)


def test_profiles_follow_stable_ids_across_all_relative_decision_mappings() -> None:
    record, _, snapshots, bindings = build_profile_inputs()
    observed_sides = {player_id: set() for player_id in bindings.profiles_by_player_id}

    for snapshot in snapshots.snapshots:
        resolved = resolve_historical_opponent_profiles_for_decision(
            record,
            snapshot,
            bindings.profiles_by_player_id,
        )
        assert resolved.left_player_id == snapshot.relative_player_map["left"]
        assert resolved.right_player_id == snapshot.relative_player_map["right"]
        assert resolved.left_player_id != resolved.right_player_id
        assert snapshot.acting_player_id not in {
            resolved.left_player_id,
            resolved.right_player_id,
        }
        for side in ("left", "right"):
            player_id = getattr(resolved, f"{side}_player_id")
            profile = getattr(resolved, side)
            assert (profile is not None) == (player_id in bindings.profiles_by_player_id)
            if profile is not None:
                assert profile.player_id == player_id
                observed_sides[player_id].add(side)

    assert observed_sides == {"player-a": {"left", "right"}, "player-c": {"left", "right"}}


def stub_expected_value_recommendation(
    state,
    left_hand_size,
    right_hand_size,
    sample_count,
    random_seed=None,
    use_basic_opponent_strategy=True,
    opponent_response_policy_by_player=None,
):
    del (
        left_hand_size,
        right_hand_size,
        sample_count,
        random_seed,
        use_basic_opponent_strategy,
        opponent_response_policy_by_player,
    )
    legal_cards = get_legal_cards(state.hand, state.current_trick, state.game_type)
    values = {
        card: {
            "win_rate": 0.5,
            "average_trick_points": 5.0,
            "average_points_won": 5.0,
            "average_points_lost": 5.0,
        }
        for card in legal_cards
    }
    return legal_cards[0], "Stub recommendation.", values


def test_review_applies_actionable_profiles_and_reconciles_decision_output(
    monkeypatch,
) -> None:
    observed_policies = []

    def capture_policies(*args, opponent_response_policy_by_player=None, **kwargs):
        observed_policies.append(opponent_response_policy_by_player)
        return stub_expected_value_recommendation(
            *args,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            **kwargs,
        )

    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        capture_policies,
    )
    record, _, snapshots, bindings = build_profile_inputs()

    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
        opponent_profile_bindings=bindings,
    )

    assert review["settings"]["opponent_policy_mode"] == "external_profiles"
    assert len(observed_policies) == 30
    assert review["opponent_profile_application_counts"] == {
        "total_decisions": 30,
        "decisions_with_matched_opponent_profile": 30,
        "decisions_with_applied_left_profile": 20,
        "decisions_with_applied_right_profile": 20,
        "decisions_with_no_actionable_external_profile": 0,
        "application_counts_by_player_id": {"player-a": 20, "player-c": 20},
        "application_counts_by_preset": {
            "aggressive_points": 20,
            "cautious_defender": 20,
        },
    }
    for decision, policies in zip(review["decisions"], observed_policies, strict=True):
        application = decision["opponent_profile_application"]
        assert application["acting_player_id"] == decision["acting_player_id"]
        assert application["left_opponent_player_id"] != decision["acting_player_id"]
        assert application["right_opponent_player_id"] != decision["acting_player_id"]
        expected_policies = {
            side: application[side]["effective_response_policy"]
            for side in ("left", "right")
            if application[side]["effective_response_policy"] != "lowest_point"
        }
        assert policies == (expected_policies or None)
        assert "source" not in application["left"]
        assert "statistics" not in application["left"]


def test_explicit_policy_precedence_and_non_actionable_profiles_preserve_defaults(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        stub_expected_value_recommendation,
    )
    statistics_data = load_statistics_data()
    statistics_data["records"][0]["games_played"] = 20
    statistics_data["records"][1]["statistics"].update(
        solo_games_played_percent=30,
        solo_hand_percent=0,
        suit_games_percent=100,
        grand_games_percent=0,
        null_games_percent=0,
        defender_games_played_percent=70,
        defender_games_won_percent=50,
    )
    record, _, snapshots, bindings = build_profile_inputs(statistics_data=statistics_data)

    non_actionable = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        opponent_profile_bindings=bindings,
    )
    assert all(
        decision["opponent_profile_application"][side]["application_status"]
        in {"not_actionable", "unmatched"}
        for decision in non_actionable["decisions"]
        for side in ("left", "right")
    )
    assert all(
        decision["opponent_profile_application"][side]["applied_policy_preset"] is None
        for decision in non_actionable["decisions"]
        for side in ("left", "right")
    )

    _, _, actionable_snapshots, actionable_bindings = build_profile_inputs()
    explicit = build_historical_game_review_summary(
        actionable_snapshots,
        record,
        sample_count=1,
        opponent_profile_bindings=actionable_bindings,
        opponent_response_policy_override="lowest_point",
        left_opponent_response_policy_override="highest_point",
    )
    for decision in explicit["decisions"]:
        application = decision["opponent_profile_application"]
        assert application["left"]["effective_response_policy"] == "highest_point"
        assert application["right"]["effective_response_policy"] == "lowest_point"
        for side in ("left", "right"):
            if application[side]["profile_match_status"] == "matched":
                assert application[side]["application_status"] == "explicit_policy_precedence"


def test_profile_review_is_deterministic_and_preserves_replay_and_snapshot_data() -> None:
    record, historical_summary, snapshots, bindings = build_profile_inputs()

    first = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
        opponent_profile_bindings=bindings,
    )
    second = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
        opponent_profile_bindings=bindings,
    )
    baseline = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
    )

    assert first == second
    assert [decision["effective_random_seed"] for decision in first["decisions"]] == list(
        range(42, 72)
    )
    assert [decision["legal_cards"] for decision in first["decisions"]] == [
        decision["legal_cards"] for decision in baseline["decisions"]
    ]
    assert [decision["actual_card_played"] for decision in first["decisions"]] == [
        decision["actual_card_played"] for decision in baseline["decisions"]
    ]
    assert historical_summary == build_historical_game_summary(record)
    assert snapshots == build_historical_decision_snapshots(historical_summary)
