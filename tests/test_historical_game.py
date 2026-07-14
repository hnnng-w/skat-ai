import copy
import random
from dataclasses import replace

import pytest

from skat_ai.deck import get_full_deck
from skat_ai.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot_summary,
)
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_historical_game_summary_from_input,
)
from skat_ai.historical_game_review import (
    HistoricalGameReviewSettings,
    build_historical_game_review_summary,
)
from skat_ai.historical_snapshot_adapter import (
    build_position_from_historical_snapshot,
)
from skat_ai.rules import get_legal_cards, get_trick_winner

PLAYER_IDS_BY_SEAT = ["player-a", "player-b", "player-c"]


def build_historical_input(
    game_type: str = "grand",
    hand_game: bool = False,
    declarer_player_id: str = "player-b",
    bid_value: int = 18,
    deck: list[str] | None = None,
) -> dict:
    deck = deck or get_full_deck()
    initial_hands = {
        "player-a": deck[0:10],
        "player-b": deck[10:20],
        "player-c": deck[20:30],
    }
    skat = deck[30:32]
    discarded_cards = [] if hand_game else initial_hands[declarer_player_id][:2]
    playable_hands = copy.deepcopy(initial_hands)
    if not hand_game:
        playable_hands[declarer_player_id].extend(skat)
        for card in discarded_cards:
            playable_hands[declarer_player_id].remove(card)

    tricks = []
    leader_player_id = "player-a"
    for trick_number in range(1, 11):
        leader_index = PLAYER_IDS_BY_SEAT.index(leader_player_id)
        player_order = [
            PLAYER_IDS_BY_SEAT[(leader_index + offset) % 3] for offset in range(3)
        ]
        trick_cards = []
        plays = []
        for player_id in player_order:
            legal_cards = get_legal_cards(
                playable_hands[player_id], trick_cards, game_type
            )
            card = legal_cards[0]
            playable_hands[player_id].remove(card)
            trick_cards.append(card)
            plays.append({"player_id": player_id, "card": card})
        winner_index = get_trick_winner(trick_cards, game_type)
        leader_player_id = plays[winner_index]["player_id"]
        tricks.append(
            {
                "trick_number": trick_number,
                "leader_player_id": player_order[0],
                "plays": plays,
            }
        )

    return {
        "schema_version": 1,
        "game_id": f"test-{game_type}-game",
        "players": [
            {
                "player_id": "player-a",
                "player_label": "Alice",
                "seat": "forehand",
                "initial_hand": initial_hands["player-a"],
            },
            {
                "player_id": "player-b",
                "seat": "middlehand",
                "initial_hand": initial_hands["player-b"],
            },
            {
                "player_id": "player-c",
                "player_label": "Carol",
                "seat": "rearhand",
                "initial_hand": initial_hands["player-c"],
            },
        ],
        "skat": skat,
        "declarer_player_id": declarer_player_id,
        "declaration": {
            "game_type": game_type,
            "hand_game": hand_game,
            "bid_value": bid_value,
        },
        "discarded_cards": discarded_cards,
        "game_end_reason": "normal_completion",
        "tricks": tricks,
    }


def build_decision_snapshot_summary(data: dict) -> dict:
    historical_summary = build_historical_game_summary_from_input(data)
    return build_serializable_historical_decision_snapshot_summary(
        build_historical_decision_snapshots(historical_summary)
    )


def build_typed_historical_review_inputs(data: dict):
    record = build_historical_game_record(data)
    historical_summary = build_historical_game_summary(record)
    snapshot_summary = build_historical_decision_snapshots(historical_summary)
    return record, snapshot_summary


def build_stub_expected_value_recommendation(
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
    legal_cards = get_legal_cards(
        state.hand,
        state.current_trick,
        state.game_type,
    )
    values = {
        card: {
            "win_rate": 0.5,
            "average_trick_points": 5.0,
            "average_points_won": 5.0,
            "average_points_lost": 5.0,
        }
        for card in legal_cards
    }
    return legal_cards[0], "Stub immediate recommendation.", values


def rebuild_historical_suffix(data: dict, completed_prefix_tricks: int) -> dict:
    """Builds a coherent alternative suffix after complete unchanged tricks."""
    alternative = copy.deepcopy(data)
    record = build_historical_game_record(alternative)
    hands = {player.player_id: list(player.initial_hand) for player in record.players}
    if not record.declaration.hand_game:
        hands[record.declarer_player_id].extend(record.skat)
        for card in record.discarded_cards:
            hands[record.declarer_player_id].remove(card)

    for trick in record.tricks[:completed_prefix_tricks]:
        for play in trick.plays:
            hands[play.player_id].remove(play.card)

    previous_trick = alternative["tricks"][completed_prefix_tricks - 1]
    previous_cards = [play["card"] for play in previous_trick["plays"]]
    winner_index = get_trick_winner(previous_cards, record.declaration.game_type)
    leader_player_id = previous_trick["plays"][winner_index]["player_id"]
    suffix = []
    changed_play_selected = False
    for trick_number in range(completed_prefix_tricks + 1, 11):
        leader_index = PLAYER_IDS_BY_SEAT.index(leader_player_id)
        player_order = [
            PLAYER_IDS_BY_SEAT[(leader_index + offset) % 3] for offset in range(3)
        ]
        trick_cards = []
        plays = []
        for player_id in player_order:
            legal_cards = get_legal_cards(
                hands[player_id], trick_cards, record.declaration.game_type
            )
            if not changed_play_selected and len(legal_cards) > 1:
                card = legal_cards[-1]
                changed_play_selected = True
            else:
                card = legal_cards[0]
            hands[player_id].remove(card)
            trick_cards.append(card)
            plays.append({"player_id": player_id, "card": card})
        winner_index = get_trick_winner(trick_cards, record.declaration.game_type)
        leader_player_id = plays[winner_index]["player_id"]
        suffix.append(
            {
                "trick_number": trick_number,
                "leader_player_id": plays[0]["player_id"],
                "plays": plays,
            }
        )

    assert changed_play_selected
    alternative["tricks"][completed_prefix_tricks:] = suffix
    return alternative


@pytest.mark.parametrize(
    ("game_type", "hand_game"),
    [("clubs", True), ("grand", False), ("null", False)],
)
def test_complete_suit_grand_and_null_games_are_derived(
    game_type: str,
    hand_game: bool,
) -> None:
    data = build_historical_input(game_type=game_type, hand_game=hand_game)

    summary = build_historical_game_summary_from_input(data)

    assert summary["status"] == "complete"
    assert len(summary["derived_tricks"]) == 10
    assert summary["declarer_trick_points"] + summary["defender_trick_points"] == (
        120 - summary["skat_points"]
    )
    assert summary["declarer_points"] + summary["defender_points"] == 120
    assert summary["winner"] in {"declarer", "defenders"}
    assert summary["game_result_summary"]["is_complete"] is True
    assert summary["final_settlement_summary"]["is_complete"] is True


@pytest.mark.parametrize(
    ("game_type", "hand_game"),
    [("clubs", True), ("grand", False), ("null", False)],
)
def test_decision_snapshots_have_legal_pre_play_hands_for_all_contract_families(
    game_type: str,
    hand_game: bool,
) -> None:
    snapshots = build_decision_snapshot_summary(
        build_historical_input(game_type=game_type, hand_game=hand_game)
    )["snapshots"]
    played_by_player = {player_id: set() for player_id in PLAYER_IDS_BY_SEAT}

    for snapshot in snapshots:
        visible_state = snapshot["visible_state"]
        actual_card = snapshot["actual_card_played"]
        acting_player = snapshot["acting_player_id"]
        assert actual_card in visible_state["own_hand"]
        assert actual_card in visible_state["legal_cards"]
        assert set(visible_state["legal_cards"]) <= set(visible_state["own_hand"])
        assert not played_by_player[acting_player].intersection(
            visible_state["own_hand"]
        )
        played_by_player[acting_player].add(actual_card)


def test_decision_snapshot_sequence_mapping_and_temporal_state_are_deterministic() -> None:
    data = build_historical_input()
    first_result = build_decision_snapshot_summary(data)
    second_result = build_decision_snapshot_summary(data)
    snapshots = first_result["snapshots"]

    assert first_result == second_result
    assert first_result["schema_version"] == 1
    assert first_result["information_policy"] == "decision_time"
    assert first_result["snapshot_count"] == 30
    assert [snapshot["decision_index"] for snapshot in snapshots] == list(
        range(1, 31)
    )
    assert [snapshot["trick_number"] for snapshot in snapshots] == [
        trick_number for trick_number in range(1, 11) for _ in range(3)
    ]
    assert [snapshot["play_index"] for snapshot in snapshots] == [1, 2, 3] * 10
    assert {snapshot["source_game_id"] for snapshot in snapshots} == {
        "test-grand-game"
    }
    assert [len(snapshot["visible_state"]["current_trick"]) for snapshot in snapshots] == (
        [0, 1, 2] * 10
    )

    expected_maps = {
        "player-a": {"me": "player-a", "left": "player-b", "right": "player-c"},
        "player-b": {"me": "player-b", "left": "player-c", "right": "player-a"},
        "player-c": {"me": "player-c", "left": "player-a", "right": "player-b"},
    }
    for snapshot in snapshots:
        expected_map = expected_maps[snapshot["acting_player_id"]]
        visible_state = snapshot["visible_state"]
        assert snapshot["relative_player_map"] == expected_map
        assert [
            opponent["player_id"]
            for opponent in visible_state["opponent_hand_sizes"]
        ] == [expected_map["left"], expected_map["right"]]
        assert len(set(expected_map.values())) == 3
        prior_plays = snapshots[: snapshot["decision_index"] - 1]
        for opponent in visible_state["opponent_hand_sizes"]:
            expected_size = 10 - sum(
                prior_snapshot["acting_player_id"] == opponent["player_id"]
                for prior_snapshot in prior_plays
            )
            assert opponent["remaining_card_count"] == expected_size
        assert visible_state["declarer_trick_points"] == sum(
            trick["trick_points"]
            for trick in visible_state["completed_tricks"]
            if trick["winner_side"] == "declarer"
        )
        assert visible_state["defender_trick_points"] == sum(
            trick["trick_points"]
            for trick in visible_state["completed_tricks"]
            if trick["winner_side"] == "defenders"
        )

    assert snapshots[2]["visible_state"]["completed_tricks"] == []
    first_completed = snapshots[3]["visible_state"]["completed_tricks"]
    assert len(first_completed) == 1
    assert first_completed[0]["trick_number"] == 1
    assert snapshots[3]["visible_state"]["declarer_trick_points"] == 15
    assert snapshots[3]["visible_state"]["defender_trick_points"] == 0


def test_decision_snapshots_apply_skat_matador_and_ouvert_visibility() -> None:
    non_hand_data = build_historical_input()
    non_hand_snapshots = build_decision_snapshot_summary(non_hand_data)["snapshots"]
    final_matadors = build_historical_game_summary_from_input(non_hand_data)["record"][
        "declaration"
    ]["matadors"]
    assert all(
        snapshot["visible_state"]["public_exposed_cards"] == []
        for snapshot in non_hand_snapshots
    )

    for snapshot in non_hand_snapshots:
        visible_state = snapshot["visible_state"]
        if snapshot["acting_side"] == "declarer":
            assert visible_state["skat_visibility"] == "known_to_declarer"
            assert visible_state["known_skat_cards"] == non_hand_data["discarded_cards"]
            assert visible_state["declaration"]["matadors"] == final_matadors
        else:
            assert visible_state["skat_visibility"] == "unknown"
            assert visible_state["known_skat_cards"] == []
    assert non_hand_snapshots[0]["visible_state"]["declaration"]["matadors"] is None
    assert any(
        snapshot["visible_state"]["declaration"]["matadors"] is not None
        for snapshot in non_hand_snapshots
        if snapshot["acting_side"] == "defenders"
    )

    hand_data = build_historical_input(game_type="clubs", hand_game=True)
    hand_snapshots = build_decision_snapshot_summary(hand_data)["snapshots"]
    assert all(
        snapshot["visible_state"]["skat_visibility"] == "unknown"
        and snapshot["visible_state"]["known_skat_cards"] == []
        for snapshot in hand_snapshots
    )
    assert all(
        not set(hand_data["skat"]).intersection(snapshot["visible_state"]["own_hand"])
        for snapshot in hand_snapshots
    )

    ouvert_data = build_historical_input(game_type="null", hand_game=True)
    ouvert_data["declaration"]["ouvert"] = True
    ouvert_snapshots = build_decision_snapshot_summary(ouvert_data)["snapshots"]
    declarer_id = ouvert_data["declarer_player_id"]
    declarer_cards_played = set()
    for snapshot in ouvert_snapshots:
        exposure = snapshot["visible_state"]["public_exposed_cards"]
        assert len(exposure) == 1
        assert exposure[0]["player_id"] == declarer_id
        assert not declarer_cards_played.intersection(exposure[0]["cards"])
        if snapshot["acting_player_id"] == declarer_id:
            assert exposure[0]["cards"] == snapshot["visible_state"]["own_hand"]
            declarer_cards_played.add(snapshot["actual_card_played"])


def test_decision_snapshots_exclude_future_and_final_information() -> None:
    data = build_historical_input()
    snapshots = build_decision_snapshot_summary(data)["snapshots"]
    first_visible_state = snapshots[0]["visible_state"]
    first_player_cards = set(data["players"][0]["initial_hand"])
    hidden_opponent_cards = {
        card for player in data["players"][1:] for card in player["initial_hand"]
    }

    def collect_visible_cards(value: object) -> set[str]:
        if isinstance(value, str):
            return {value} if value in get_full_deck() else set()
        if isinstance(value, list):
            return set().union(*(collect_visible_cards(item) for item in value))
        if isinstance(value, dict):
            return set().union(
                *(collect_visible_cards(item) for item in value.values())
            )
        return set()

    assert not hidden_opponent_cards.intersection(first_visible_state["own_hand"])
    assert not hidden_opponent_cards.intersection(
        collect_visible_cards(first_visible_state)
    )
    assert first_visible_state["completed_tricks"] == []
    assert first_visible_state["current_trick"] == []
    assert set(first_visible_state["own_hand"]) == first_player_cards
    forbidden_fields = {
        "winner",
        "game_result_summary",
        "game_value_summary",
        "overbid_summary",
        "final_settlement_summary",
        "declarer_points",
        "defender_points",
        "skat_points",
        "schneider_status",
        "schwarz_status",
        "recommendation",
        "decision_quality",
    }
    for snapshot in snapshots:
        assert forbidden_fields.isdisjoint(snapshot)
        assert forbidden_fields.isdisjoint(snapshot["visible_state"])
        assert snapshot["actual_card_played"] not in {
            play["card"] for play in snapshot["visible_state"]["current_trick"]
        }


def test_unchanged_prefix_snapshots_are_stable_when_future_suffix_changes() -> None:
    data = build_historical_input()
    alternative_data = rebuild_historical_suffix(data, completed_prefix_tricks=5)

    original_snapshots = build_decision_snapshot_summary(data)["snapshots"]
    alternative_snapshots = build_decision_snapshot_summary(alternative_data)["snapshots"]

    assert alternative_data["tricks"][:5] == data["tricks"][:5]
    assert alternative_data["tricks"][5:] != data["tricks"][5:]
    assert alternative_snapshots[:15] == original_snapshots[:15]


@pytest.mark.parametrize("acting_player_id", PLAYER_IDS_BY_SEAT)
def test_historical_snapshot_adapter_maps_each_acting_seat_to_local_position(
    acting_player_id: str,
) -> None:
    record, snapshot_summary = build_typed_historical_review_inputs(
        build_historical_input()
    )
    snapshot = next(
        snapshot
        for snapshot in snapshot_summary.snapshots
        if snapshot.acting_player_id == acting_player_id
        and snapshot.decision_index > 3
        and snapshot.play_index > 1
    )

    position = build_position_from_historical_snapshot(snapshot, record)
    state = position.state
    stable_to_local = {
        player_id: relative_player
        for relative_player, player_id in snapshot.relative_player_map.items()
    }

    assert snapshot.relative_player_map["me"] == acting_player_id
    assert state.next_player == "me"
    assert state.player_position == snapshot.acting_seat
    assert state.player_role == (
        "declarer" if snapshot.acting_side == "declarer" else "defender"
    )
    assert state.declarer_player == stable_to_local[record.declarer_player_id]
    assert state.hand == list(snapshot.visible_state.own_hand)
    assert state.current_trick == [
        play.card for play in snapshot.visible_state.current_trick
    ]
    assert state.trick_leader == stable_to_local[
        snapshot.visible_state.current_trick[0].player_id
    ]
    assert state.completed_tricks == [
        {
            "cards": [play.card for play in trick.plays],
            "players": [stable_to_local[play.player_id] for play in trick.plays],
            "winner_player": stable_to_local[trick.winner_player_id],
            "winner_role": trick.winner_side,
        }
        for trick in snapshot.visible_state.completed_tricks
    ]
    assert state.declarer_points == snapshot.visible_state.declarer_trick_points
    assert state.defender_points == snapshot.visible_state.defender_trick_points
    assert position.left_hand_size == (
        snapshot.visible_state.opponent_hand_sizes[0].remaining_card_count
    )
    assert position.right_hand_size == (
        snapshot.visible_state.opponent_hand_sizes[1].remaining_card_count
    )
    assert state.skat == list(snapshot.visible_state.known_skat_cards)
    assert position.game_declaration.matadors == snapshot.visible_state.declaration.matadors
    assert position.game_end_reason == "not_ended"
    assert position.legal_cards == snapshot.visible_state.legal_cards


@pytest.mark.parametrize("game_type", ["clubs", "grand", "null"])
@pytest.mark.parametrize("acting_side", ["declarer", "defenders"])
@pytest.mark.parametrize("play_index", [1, 2, 3])
def test_historical_snapshot_adapter_covers_contract_perspective_and_trick_position(
    game_type: str,
    acting_side: str,
    play_index: int,
) -> None:
    template = build_historical_input(game_type=game_type, hand_game=True)
    acting_player_id = template["tricks"][0]["plays"][play_index - 1]["player_id"]
    declarer_player_id = (
        acting_player_id
        if acting_side == "declarer"
        else next(
            player_id
            for player_id in PLAYER_IDS_BY_SEAT
            if player_id != acting_player_id
        )
    )
    record, snapshot_summary = build_typed_historical_review_inputs(
        build_historical_input(
            game_type=game_type,
            hand_game=True,
            declarer_player_id=declarer_player_id,
        )
    )
    snapshot = next(
        snapshot
        for snapshot in snapshot_summary.snapshots
        if snapshot.acting_side == acting_side and snapshot.play_index == play_index
    )

    position = build_position_from_historical_snapshot(snapshot, record)

    assert position.state.game_type == game_type
    assert position.state.player_role == (
        "declarer" if acting_side == "declarer" else "defender"
    )
    assert len(position.state.current_trick) == play_index - 1
    assert position.state.skat == []


def test_complete_historical_review_reconciles_rows_players_and_quality_counts(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        build_stub_expected_value_recommendation,
    )
    record, snapshot_summary = build_typed_historical_review_inputs(
        build_historical_input()
    )

    review = build_historical_game_review_summary(
        snapshot_summary,
        record,
        sample_count=1,
        base_random_seed=42,
    )

    assert review["decision_count"] == 30
    assert review["reviewed_decision_count"] == 30
    assert review["unavailable_decision_count"] == 0
    assert [player["player_id"] for player in review["player_summaries"]] == [
        player.player_id for player in record.players
    ]
    assert [player["player_label"] for player in review["player_summaries"]] == [
        player.player_label for player in record.players
    ]
    assert all(
        player["decision_count"] == 10
        and player["reviewed_decision_count"] == 10
        for player in review["player_summaries"]
    )
    assert sum(review["quality_counts"].values()) == 30
    for decision in review["decisions"]:
        assert decision["actual_card_played"] in decision["legal_cards"]
        assert decision["recommendation"]["card"] is not None
        assert sum(
            row["is_recommended"] for row in decision["analysis_report"]
        ) == 1
        assert sum(
            row["card"] == decision["actual_card_played"]
            for row in decision["analysis_report"]
        ) == 1
    assert all(
        len(decision["legal_cards"]) == 1
        for decision in review["decisions"][-3:]
    )
    for quality, count in review["quality_counts"].items():
        assert count == sum(
            player["quality_counts"][quality]
            for player in review["player_summaries"]
        )


def test_historical_review_derives_decision_seeds_and_preserves_unseeded_nulls(
    monkeypatch,
) -> None:
    observed_seeds = []

    def capture_seed(*args, random_seed=None, **kwargs):
        observed_seeds.append(random_seed)
        return build_stub_expected_value_recommendation(
            *args,
            random_seed=random_seed,
            **kwargs,
        )

    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        capture_seed,
    )
    record, snapshot_summary = build_typed_historical_review_inputs(
        build_historical_input()
    )

    seeded_review = build_historical_game_review_summary(
        snapshot_summary,
        record,
        sample_count=1,
        base_random_seed=42,
    )
    assert observed_seeds == list(range(42, 72))
    assert seeded_review["decisions"][0]["effective_random_seed"] == 42
    assert seeded_review["decisions"][-1]["effective_random_seed"] == 71

    observed_seeds.clear()
    unseeded_review = build_historical_game_review_summary(
        snapshot_summary,
        record,
        sample_count=1,
    )
    assert observed_seeds == [None] * 30
    assert all(
        decision["effective_random_seed"] is None
        for decision in unseeded_review["decisions"]
    )
    assert HistoricalGameReviewSettings().sample_count == 100


def test_historical_review_does_not_convert_unexpected_simulation_errors(
    monkeypatch,
) -> None:
    def fail_simulation(*args, **kwargs):
        raise RuntimeError("unexpected simulation failure")

    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        fail_simulation,
    )
    record, snapshot_summary = build_typed_historical_review_inputs(
        build_historical_input()
    )

    with pytest.raises(RuntimeError, match="unexpected simulation failure"):
        build_historical_game_review_summary(
            snapshot_summary,
            record,
            sample_count=1,
            base_random_seed=42,
        )


def test_historical_review_uses_only_snapshot_state_for_unchanged_prefix(
    monkeypatch,
) -> None:
    captured_first_states = []

    def capture_state(*args, state, **kwargs):
        if not captured_first_states:
            captured_first_states.append(copy.deepcopy(state))
        return build_stub_expected_value_recommendation(
            *args,
            state=state,
            **kwargs,
        )

    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        capture_state,
    )
    data = build_historical_input()
    alternative_data = rebuild_historical_suffix(data, completed_prefix_tricks=5)
    record, snapshots = build_typed_historical_review_inputs(data)
    alternative_record, alternative_snapshots = build_typed_historical_review_inputs(
        alternative_data
    )

    original_review = build_historical_game_review_summary(
        snapshots, record, sample_count=1, base_random_seed=42
    )
    alternative_review = build_historical_game_review_summary(
        alternative_snapshots,
        alternative_record,
        sample_count=1,
        base_random_seed=42,
    )

    assert original_review["decisions"][:15] == alternative_review["decisions"][:15]
    first_state = captured_first_states[0]
    assert first_state.hand == list(snapshots.snapshots[0].visible_state.own_hand)
    assert first_state.current_trick == []
    assert first_state.completed_tricks == []
    hidden_initial_cards = {
        card
        for player in record.players[1:]
        for card in player.initial_hand
    }
    assert hidden_initial_cards.isdisjoint(first_state.hand)


def test_historical_review_actual_card_is_only_a_decision_label(monkeypatch) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        build_stub_expected_value_recommendation,
    )
    record, snapshot_summary = build_typed_historical_review_inputs(
        build_historical_input()
    )
    snapshot = next(
        snapshot
        for snapshot in snapshot_summary.snapshots
        if len(snapshot.visible_state.legal_cards) > 1
    )
    changed_snapshot = replace(
        snapshot,
        actual_card_played=snapshot.visible_state.legal_cards[-1],
    )
    changed_summary = replace(
        snapshot_summary,
        snapshots=tuple(
            changed_snapshot if item is snapshot else item
            for item in snapshot_summary.snapshots
        ),
    )

    original = build_historical_game_review_summary(
        snapshot_summary, record, sample_count=1, base_random_seed=42
    )["decisions"][snapshot.decision_index - 1]
    changed = build_historical_game_review_summary(
        changed_summary, record, sample_count=1, base_random_seed=42
    )["decisions"][snapshot.decision_index - 1]

    assert changed["actual_card_played"] != original["actual_card_played"]
    assert changed["legal_cards"] == original["legal_cards"]
    assert changed["recommendation"] == original["recommendation"]
    assert changed["analysis_report"] == original["analysis_report"]


def test_ouvert_historical_review_is_unavailable_without_simulation(monkeypatch) -> None:
    def fail_simulation(*args, **kwargs):
        raise AssertionError("Ouvert historical review must not run simulation.")

    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        fail_simulation,
    )
    data = build_historical_input(game_type="null", hand_game=True)
    data["declaration"]["ouvert"] = True
    record, snapshot_summary = build_typed_historical_review_inputs(data)

    review = build_historical_game_review_summary(
        snapshot_summary,
        record,
        sample_count=1,
        base_random_seed=42,
    )

    assert review["reviewed_decision_count"] == 0
    assert review["unavailable_decision_count"] == 30
    assert review["quality_counts"] == {
        "optimal": 0,
        "acceptable": 0,
        "suboptimal": 0,
        "mistake": 0,
        "not_available": 30,
    }
    assert all(
        decision["status"] == "unavailable"
        and decision["unavailable_reason"]
        == "public_exposed_cards_not_supported"
        and decision["legal_cards"] == []
        and decision["analysis_report"] == []
        and decision["recommendation"]["card"] is None
        and decision["post_game_review_summary"]["decision_quality"]
        == "not_available"
        for decision in review["decisions"]
    )
    assert all(
        player["unavailable_decision_count"] == 10
        and player["quality_counts"]["not_available"] == 10
        for player in review["player_summaries"]
    )


def test_seeded_complete_historical_review_is_end_to_end_deterministic() -> None:
    record, snapshot_summary = build_typed_historical_review_inputs(
        build_historical_input()
    )

    first = build_historical_game_review_summary(
        snapshot_summary,
        record,
        sample_count=1,
        base_random_seed=42,
    )
    second = build_historical_game_review_summary(
        snapshot_summary,
        record,
        sample_count=1,
        base_random_seed=42,
    )

    assert first == second
    assert first["reviewed_decision_count"] == 30
    assert all(
        decision["recommendation"]["card"] in decision["legal_cards"]
        for decision in first["decisions"]
    )


def test_derived_trick_winner_and_points_are_rule_based() -> None:
    summary = build_historical_game_summary_from_input(build_historical_input())

    first_trick = summary["derived_tricks"][0]
    assert first_trick["winner_player_id"] == "player-b"
    assert first_trick["winner_side"] == "declarer"
    assert first_trick["trick_points"] == 15


@pytest.mark.parametrize(
    ("declarer_player_id", "expected_winner"),
    [("player-b", "declarer"), ("player-a", "defenders")],
)
def test_null_win_and_loss_follow_trick_ownership(
    declarer_player_id: str,
    expected_winner: str,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_historical_input(
            game_type="null", declarer_player_id=declarer_player_id
        )
    )

    assert summary["winner"] == expected_winner
    assert summary["schneider_status"] == "not_applicable"
    assert summary["schwarz_status"] == "not_applicable"


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_game_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_null_variants_are_supported(
    hand_game: bool,
    ouvert: bool,
    expected_game_value: int,
) -> None:
    data = build_historical_input(game_type="null", hand_game=hand_game)
    data["declaration"]["ouvert"] = ouvert

    summary = build_historical_game_summary_from_input(data)

    assert summary["game_value_summary"]["game_value"] == expected_game_value
    assert summary["final_settlement_summary"]["is_complete"] is True


def test_schneider_is_derived_from_final_card_points() -> None:
    summary = build_historical_game_summary_from_input(
        build_historical_input(game_type="clubs", hand_game=True)
    )

    assert (
        summary["schneider_status"]
        == "defenders_made_schneider"
    )
    assert summary["final_settlement_summary"]["effective_game_value"] == 48


def test_schwarz_is_derived_from_complete_trick_ownership() -> None:
    schwarz_summary = None
    for seed in range(1000):
        deck = get_full_deck()
        random.Random(seed).shuffle(deck)
        summary = build_historical_game_summary_from_input(
            build_historical_input(game_type="grand", hand_game=True, deck=deck)
        )
        if summary["game_result_summary"]["effective_schwarz_status"] != "none":
            schwarz_summary = summary
            break

    assert schwarz_summary is not None
    assert schwarz_summary["schwarz_status"] != "none"
    assert schwarz_summary["final_settlement_summary"]["is_complete"] is True


def test_canonical_null_record_round_trip_omits_excluded_metadata() -> None:
    original_summary = build_historical_game_summary_from_input(
        build_historical_input(game_type="null")
    )

    declaration = original_summary["record"]["declaration"]
    assert "matadors" not in declaration
    assert "schneider_announced" not in declaration
    assert "schwarz_announced" not in declaration
    assert build_historical_game_summary_from_input(original_summary["record"]) == (
        original_summary
    )


def test_non_hand_pickup_and_discards_define_final_playable_hand_and_skat_points() -> None:
    data = build_historical_input(hand_game=False)

    summary = build_historical_game_summary_from_input(data)

    assert summary["record"]["discarded_cards"] == data["discarded_cards"]
    assert summary["skat_points"] == 7


def test_hand_game_leaves_original_skat_unplayed_and_counts_its_points() -> None:
    data = build_historical_input(game_type="clubs", hand_game=True)

    summary = build_historical_game_summary_from_input(data)

    assert summary["record"]["discarded_cards"] == []
    assert summary["skat_points"] == 0


def test_matadors_are_inferred_and_matching_supplied_value_is_accepted() -> None:
    data = build_historical_input()
    inferred_summary = build_historical_game_summary_from_input(data)
    inferred_matadors = inferred_summary["record"]["declaration"]["matadors"]
    data["declaration"]["matadors"] = inferred_matadors

    verified_summary = build_historical_game_summary_from_input(data)

    assert verified_summary["record"]["declaration"]["matadors"] == inferred_matadors


def test_conflicting_supplied_matadors_are_rejected() -> None:
    data = build_historical_input()
    inferred_matadors = build_historical_game_summary_from_input(data)["record"][
        "declaration"
    ]["matadors"]
    data["declaration"]["matadors"] = 1 if inferred_matadors != 1 else 2

    with pytest.raises(ValueError, match="conflicts with inferred matadors"):
        build_historical_game_record(data)


def test_canonical_record_round_trip_is_deterministic() -> None:
    original_summary = build_historical_game_summary_from_input(
        build_historical_input(game_type="clubs", hand_game=True)
    )

    round_trip_summary = build_historical_game_summary_from_input(
        original_summary["record"]
    )

    assert round_trip_summary == original_summary


def test_canonical_declaration_dependencies_are_normalized() -> None:
    data = build_historical_input(game_type="clubs", hand_game=True)
    del data["declaration"]["hand_game"]
    data["declaration"]["ouvert"] = True

    declaration = build_historical_game_summary_from_input(data)["record"]["declaration"]

    assert declaration["hand_game"] is True
    assert declaration["schneider_announced"] is True
    assert declaration["schwarz_announced"] is True


def test_suit_overbid_forces_final_settlement_loss() -> None:
    data = build_historical_input(game_type="clubs", hand_game=True, bid_value=264)

    summary = build_historical_game_summary_from_input(data)

    assert summary["overbid_summary"]["is_overbid"] is True
    assert summary["final_settlement_summary"]["is_loss"] is True
    assert summary["final_settlement_summary"]["settlement_score"] < 0


@pytest.mark.parametrize("schema_version", [0, 2, "1", None, True])
def test_unsupported_schema_versions_are_rejected(schema_version: object) -> None:
    data = build_historical_input()
    data["schema_version"] = schema_version

    with pytest.raises(ValueError, match="schema_version"):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    ("field_path", "invalid_value"),
    [
        (("game_id",), ""),
        (("game_id",), " padded"),
        (("players", 0, "player_id"), "player-a "),
        (("players", 0, "player_label"), ""),
    ],
)
def test_blank_or_padded_identifiers_and_labels_are_rejected(
    field_path: tuple,
    invalid_value: object,
) -> None:
    data = build_historical_input()
    target = data
    for path_part in field_path[:-1]:
        target = target[path_part]
    target[field_path[-1]] = invalid_value

    with pytest.raises(ValueError, match="non-empty, non-padded"):
        build_historical_game_record(data)


@pytest.mark.parametrize("player_count", [2, 4])
def test_player_count_must_be_exactly_three(player_count: int) -> None:
    data = build_historical_input()
    if player_count == 2:
        data["players"].pop()
    else:
        data["players"].append(copy.deepcopy(data["players"][0]))

    with pytest.raises(ValueError, match="exactly three players"):
        build_historical_game_record(data)


def test_duplicate_player_ids_are_rejected() -> None:
    data = build_historical_input()
    data["players"][1]["player_id"] = data["players"][0]["player_id"]

    with pytest.raises(ValueError, match="player_id values must be unique"):
        build_historical_game_record(data)


@pytest.mark.parametrize("seat", ["forehand", "unknown"])
def test_duplicate_or_invalid_seats_are_rejected(seat: str) -> None:
    data = build_historical_input()
    data["players"][1]["seat"] = seat

    with pytest.raises(ValueError, match="seat"):
        build_historical_game_record(data)


def test_unknown_declarer_id_is_rejected() -> None:
    data = build_historical_input()
    data["declarer_player_id"] = "unknown-player"

    with pytest.raises(ValueError, match="does not reference a declared player"):
        build_historical_game_record(data)


def test_incorrect_initial_hand_count_is_rejected() -> None:
    data = build_historical_input()
    data["players"][0]["initial_hand"].pop()

    with pytest.raises(ValueError, match="exactly 10 cards"):
        build_historical_game_record(data)


def test_incorrect_skat_size_is_rejected() -> None:
    data = build_historical_input()
    data["skat"].pop()

    with pytest.raises(ValueError, match="exactly 2 cards"):
        build_historical_game_record(data)


def test_duplicate_or_incomplete_deal_is_rejected() -> None:
    data = build_historical_input()
    data["players"][0]["initial_hand"][0] = data["players"][0]["initial_hand"][1]

    with pytest.raises(ValueError, match="duplicate"):
        build_historical_game_record(data)


def test_non_standard_card_is_rejected() -> None:
    data = build_historical_input()
    data["players"][0]["initial_hand"][0] = "X1"

    with pytest.raises(ValueError, match="invalid cards"):
        build_historical_game_record(data)


@pytest.mark.parametrize("discard_count", [0, 1])
def test_non_hand_game_requires_two_discards(discard_count: int) -> None:
    data = build_historical_input()
    data["discarded_cards"] = data["discarded_cards"][:discard_count]

    with pytest.raises(ValueError, match="exactly two discarded_cards"):
        build_historical_game_record(data)


def test_hand_game_rejects_discards() -> None:
    data = build_historical_input(hand_game=True)
    data["discarded_cards"] = [data["players"][1]["initial_hand"][0]]

    with pytest.raises(ValueError, match="Hand games require discarded_cards"):
        build_historical_game_record(data)


def test_discard_not_owned_after_pickup_is_rejected() -> None:
    data = build_historical_input()
    data["discarded_cards"][0] = data["players"][0]["initial_hand"][0]

    with pytest.raises(ValueError, match="not owned by the declarer"):
        build_historical_game_record(data)


def test_duplicate_discards_are_rejected() -> None:
    data = build_historical_input()
    data["discarded_cards"][1] = data["discarded_cards"][0]

    with pytest.raises(ValueError, match="duplicate cards"):
        build_historical_game_record(data)


def test_discarded_card_appearing_in_play_is_rejected() -> None:
    data = build_historical_input()
    first_declarer_play = next(
        play
        for trick in data["tricks"]
        for play in trick["plays"]
        if play["player_id"] == data["declarer_player_id"]
    )
    data["discarded_cards"][0] = first_declarer_play["card"]

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="unplayable skat or discarded card"):
        build_historical_game_summary(record)


def test_original_hand_skat_card_appearing_in_play_is_rejected() -> None:
    data = build_historical_input(game_type="clubs", hand_game=True)
    data["tricks"][0]["plays"][0]["card"] = data["skat"][0]

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="unplayable skat or discarded card"):
        build_historical_game_summary(record)


@pytest.mark.parametrize("trick_count", [9, 11])
def test_exactly_ten_tricks_are_required(trick_count: int) -> None:
    data = build_historical_input()
    if trick_count == 9:
        data["tricks"].pop()
    else:
        data["tricks"].append(copy.deepcopy(data["tricks"][-1]))

    with pytest.raises(ValueError, match="exactly ten tricks"):
        build_historical_game_record(data)


def test_non_consecutive_trick_number_is_rejected() -> None:
    data = build_historical_input()
    data["tricks"][4]["trick_number"] = 6

    with pytest.raises(ValueError, match="trick_number must be 5"):
        build_historical_game_record(data)


def test_input_cannot_supply_derived_winner_or_points() -> None:
    data = build_historical_input()
    data["tricks"][0]["winner_player_id"] = "player-b"

    with pytest.raises(ValueError, match="unsupported fields"):
        build_historical_game_record(data)


def test_wrong_first_leader_is_rejected() -> None:
    data = build_historical_input()
    data["tricks"][0]["leader_player_id"] = "player-b"

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="must be led by 'player-a'"):
        build_historical_game_summary(record)


def test_invalid_player_order_and_duplicate_player_are_rejected() -> None:
    data = build_historical_input()
    data["tricks"][0]["plays"][1]["player_id"] = "player-a"

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="play order"):
        build_historical_game_summary(record)


def test_unknown_play_player_is_rejected() -> None:
    data = build_historical_input()
    data["tricks"][0]["plays"][1]["player_id"] = "unknown-player"

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="play order"):
        build_historical_game_summary(record)


def test_card_played_by_wrong_owner_is_rejected() -> None:
    data = build_historical_input()
    data["tricks"][0]["plays"][0]["card"] = data["players"][1]["initial_hand"][2]

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="does not own remaining card"):
        build_historical_game_summary(record)


def test_reused_card_and_unplayed_card_are_rejected() -> None:
    data = build_historical_input()
    first_card = data["tricks"][0]["plays"][0]["card"]
    later_play = next(
        play
        for trick in data["tricks"][1:]
        for play in trick["plays"]
        if play["player_id"] == "player-a"
    )
    later_play["card"] = first_card

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="does not own remaining card"):
        build_historical_game_summary(record)


def test_follow_obligation_violation_is_rejected() -> None:
    data = build_historical_input(game_type="grand")
    record = build_historical_game_record(data)
    hands = {player.player_id: list(player.initial_hand) for player in record.players}
    hands[record.declarer_player_id].extend(record.skat)
    for card in record.discarded_cards:
        hands[record.declarer_player_id].remove(card)

    violation_created = False
    for trick_index, trick in enumerate(data["tricks"]):
        trick_cards = []
        for play_index, play in enumerate(trick["plays"]):
            hand = hands[play["player_id"]]
            legal_cards = get_legal_cards(hand, trick_cards, "grand")
            illegal_cards = [card for card in hand if card not in legal_cards]
            if play_index > 0 and illegal_cards:
                illegal_card = illegal_cards[0]
                for later_trick in data["tricks"][trick_index:]:
                    for later_play in later_trick["plays"]:
                        if (
                            later_play["player_id"] == play["player_id"]
                            and later_play["card"] == illegal_card
                        ):
                            later_play["card"], play["card"] = play["card"], illegal_card
                            violation_created = True
                            break
                    if violation_created:
                        break
            if violation_created:
                break
            hand.remove(play["card"])
            trick_cards.append(play["card"])
        if violation_created:
            break

    assert violation_created
    with pytest.raises(ValueError, match="illegally plays"):
        build_historical_game_summary(build_historical_game_record(data))


def test_later_trick_must_be_led_by_previous_winner() -> None:
    data = build_historical_input()
    current_leader = data["tricks"][1]["leader_player_id"]
    data["tricks"][1]["leader_player_id"] = next(
        player_id for player_id in PLAYER_IDS_BY_SEAT if player_id != current_leader
    )

    record = build_historical_game_record(data)
    with pytest.raises(ValueError, match="must be led by"):
        build_historical_game_summary(record)


def test_null_rejects_matador_and_schneider_metadata() -> None:
    data = build_historical_input(game_type="null")
    data["declaration"]["matadors"] = 1

    with pytest.raises(ValueError, match="does not allow Null metadata"):
        build_historical_game_record(data)

    data = build_historical_input(game_type="null")
    data["declaration"]["schneider_announced"] = True
    with pytest.raises(ValueError, match="does not allow Null metadata"):
        build_historical_game_record(data)


def test_overbid_null_record_is_rejected_as_unsupported_impossible_null() -> None:
    data = build_historical_input(game_type="null", bid_value=24)

    with pytest.raises(ValueError, match="overbid Null records"):
        build_historical_game_summary_from_input(data)
