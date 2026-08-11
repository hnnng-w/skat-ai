import copy
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_historical_game import build_historical_input
from test_observed_game_contracts import (
    build_complete_observed_record,
    build_observed_match,
    build_observed_record,
    declaration_from_historical,
    observed_plays_from_historical,
)

from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.observed_game_trace import (
    ObservedGameTraceSummaryV1,
    ObservedPlayV1,
    validate_observed_game_trace_v1,
)
from skat_ai.rules import get_legal_cards, get_trick_winner


def _plays_for_discards(data: dict, discarded_cards: tuple[str, str]):
    hands = {
        player["player_id"]: list(player["initial_hand"])
        for player in data["players"]
    }
    declarer_player_id = data["declarer_player_id"]
    hands[declarer_player_id].extend(data["skat"])
    for card in discarded_cards:
        hands[declarer_player_id].remove(card)
    initial_hands = copy.deepcopy(hands)
    leader_player_id = "player-a"
    plays = []
    for _trick_number in range(1, 11):
        leader_index = ("player-a", "player-b", "player-c").index(
            leader_player_id
        )
        player_order = tuple(
            ("player-a", "player-b", "player-c")[(leader_index + offset) % 3]
            for offset in range(3)
        )
        trick_cards = []
        trick_plays = []
        for player_id in player_order:
            card = get_legal_cards(hands[player_id], trick_cards, "grand")[0]
            hands[player_id].remove(card)
            trick_cards.append(card)
            trick_plays.append((player_id, card))
        winner_index = get_trick_winner(trick_cards, "grand")
        leader_player_id = trick_plays[winner_index][0]
        plays.extend(trick_plays)
    return initial_hands, tuple(
        ObservedPlayV1(
            decision_index=index,
            player_id=player_id,
            card=card,
            decision_timecode=None,
        )
        for index, (player_id, card) in enumerate(plays, start=1)
    )


@pytest.mark.parametrize("play_count", (0, 1, 2, 3, 7, 29))
def test_zero_through_partial_trace_shapes_are_accepted(play_count: int) -> None:
    data = build_historical_input()
    record = build_observed_record(
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data, count=play_count),
    )
    assert len(record.plays) == play_count
    assert [play.decision_index for play in record.plays] == list(
        range(1, play_count + 1)
    )


def test_partial_trace_requires_contiguous_indices_unique_cards_and_known_players() -> None:
    data = build_historical_input()
    plays = list(observed_plays_from_historical(data, count=3))
    bad_values = (
        (replace(plays[0], decision_index=2), "contiguous"),
        (replace(plays[1], card=plays[0].card), "more than once"),
        (replace(plays[1], player_id="foreign"), "unknown Game Player"),
    )
    for replacement, message in bad_values:
        invalid = plays.copy()
        invalid[replacement.decision_index - 1 if replacement.decision_index <= 3 else 0] = (
            replacement
        )
        if message == "contiguous":
            invalid[0] = replacement
        elif message == "more than once":
            invalid[1] = replacement
        else:
            invalid[1] = replacement
        with pytest.raises(ValueError, match=message):
            build_observed_record(
                declarer_player_id=data["declarer_player_id"],
                declaration=declaration_from_historical(data),
                plays=tuple(invalid),
            )


def test_trace_rejects_more_than_30_plays_or_more_than_ten_for_one_player() -> None:
    declaration = GameDeclaration(game_type="grand")
    with pytest.raises(ValueError, match="at most 30"):
        build_observed_record(
            declarer_player_id="player-b",
            declaration=declaration,
            plays=tuple(
                ObservedPlayV1(
                    decision_index=index,
                    player_id=("player-a", "player-b", "player-c")[(index - 1) % 3],
                    card=card,
                    decision_timecode=None,
                )
                for index, card in enumerate(
                    [*build_historical_input()["players"][0]["initial_hand"],
                     *build_historical_input()["players"][1]["initial_hand"],
                     *build_historical_input()["players"][2]["initial_hand"],
                     "D8"],
                    start=1,
                )
            ),
        )

    cards = [play.card for play in observed_plays_from_historical(build_historical_input())]
    with pytest.raises(ValueError, match="at most ten"):
        build_observed_record(
            declarer_player_id="player-b",
            declaration=declaration,
            plays=tuple(
                ObservedPlayV1(
                    decision_index=index,
                    player_id="player-a",
                    card=card,
                    decision_timecode=None,
                )
                for index, card in enumerate(cards, start=1)
            ),
        )


def test_forehand_seat_order_and_previous_winner_lead_are_enforced() -> None:
    data = build_historical_input()
    plays = list(observed_plays_from_historical(data, count=4))
    for index, player_id in ((0, "player-b"), (1, "player-c"), (3, "player-c")):
        invalid = plays.copy()
        invalid[index] = replace(invalid[index], player_id=player_id)
        with pytest.raises(ValueError, match="must be played by"):
            build_observed_record(
                declarer_player_id=data["declarer_player_id"],
                declaration=declaration_from_historical(data),
                plays=tuple(invalid),
            )


@pytest.mark.parametrize("game_type", ("clubs", "grand", "null"))
def test_suit_grand_and_null_winners_drive_partial_trick_progression(
    game_type: str,
) -> None:
    data = build_historical_input(game_type=game_type)
    record = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=observed_plays_from_historical(data, count=4),
    )
    assert record.plays[3].player_id == data["tricks"][1]["leader_player_id"]


def test_decision_timecodes_are_optional_contained_and_non_decreasing() -> None:
    data = build_historical_input()
    source = observed_plays_from_historical(data, count=3)
    plays = tuple(
        replace(
            play,
            decision_timecode=(
                None
                if index == 1
                else MediaTimecodeV1(
                    start_offset_ms=20_000 + index * 1_000,
                    end_offset_ms=None,
                )
            ),
        )
        for index, play in enumerate(source)
    )
    assert build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=plays,
    ).plays[1].decision_timecode is None

    decreasing = (
        replace(
            source[0],
            decision_timecode=MediaTimecodeV1(
                start_offset_ms=30_000,
                end_offset_ms=None,
            ),
        ),
        replace(source[1], decision_timecode=None),
        replace(
            source[2],
            decision_timecode=MediaTimecodeV1(
                start_offset_ms=29_999,
                end_offset_ms=None,
            ),
        ),
    )
    with pytest.raises(ValueError, match="non-decreasing"):
        build_observed_record(
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            plays=decreasing,
        )
    with pytest.raises(ValueError, match="within game_timecode"):
        build_observed_record(
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            plays=(
                replace(
                    source[0],
                    decision_timecode=MediaTimecodeV1(
                        start_offset_ms=19_999,
                        end_offset_ms=None,
                    ),
                ),
            ),
        )


def test_known_perspective_ownership_and_bedienpflicht_are_enforced() -> None:
    perspective_hand = (
        "CA",
        "C10",
        "CK",
        "CQ",
        "CJ",
        "C9",
        "C8",
        "C7",
        "SA",
        "H7",
    )
    with pytest.raises(ValueError, match="illegally plays"):
        build_observed_record(
            match_definition=build_observed_match(perspective_player_id="player-b"),
            perspective_initial_hand=perspective_hand,
            declarer_player_id="player-c",
            declaration=GameDeclaration(game_type="grand"),
            plays=(
                ObservedPlayV1(
                    decision_index=1,
                    player_id="player-a",
                    card="S7",
                    decision_timecode=None,
                ),
                ObservedPlayV1(
                    decision_index=2,
                    player_id="player-b",
                    card="H7",
                    decision_timecode=None,
                ),
            ),
        )
    with pytest.raises(ValueError, match="does not own"):
        build_observed_record(
            perspective_initial_hand=perspective_hand,
            declarer_player_id="player-b",
            declaration=GameDeclaration(game_type="grand", hand_game=True),
            discarded_cards=(),
            plays=(
                ObservedPlayV1(
                    decision_index=1,
                    player_id="player-a",
                    card="D7",
                    decision_timecode=None,
                ),
            ),
        )


def test_unknown_opponent_failure_to_follow_is_not_invented_or_rejected() -> None:
    record = build_observed_record(
        declarer_player_id="player-c",
        declaration=GameDeclaration(game_type="grand"),
        plays=(
            ObservedPlayV1(
                decision_index=1,
                player_id="player-a",
                card="S7",
                decision_timecode=None,
            ),
            ObservedPlayV1(
                decision_index=2,
                player_id="player-b",
                card="H7",
                decision_timecode=None,
            ),
        ),
    )
    assert [play.card for play in record.plays] == ["S7", "H7"]


@pytest.mark.parametrize(
    ("game_type", "hand_game"),
    (("clubs", True), ("grand", False), ("null", False)),
)
def test_complete_suit_grand_and_null_traces_replay_all_30_plays(
    game_type: str,
    hand_game: bool,
) -> None:
    record = build_complete_observed_record(
        game_type=game_type,
        hand_game=hand_game,
    )
    assert len(record.plays) == 30
    assert {
        player.player_id: sum(play.player_id == player.player_id for play in record.plays)
        for player in record.players
    } == {"player-a": 10, "player-b": 10, "player-c": 10}


def test_complete_trace_rejects_a_bedienpflicht_violation() -> None:
    data = build_historical_input(game_type="grand")
    original = list(observed_plays_from_historical(data))
    illegal_trace = None
    for first_index, first in enumerate(original):
        for second_index in range(first_index + 1, len(original)):
            second = original[second_index]
            if first.player_id != second.player_id:
                continue
            candidate = original.copy()
            candidate[first_index] = replace(first, card=second.card)
            candidate[second_index] = replace(second, card=first.card)
            try:
                build_observed_record(
                    declarer_player_id=data["declarer_player_id"],
                    declaration=declaration_from_historical(data),
                    discarded_cards=data["discarded_cards"],
                    plays=tuple(candidate),
                )
            except ValueError as error:
                if "illegally plays" in str(error):
                    illegal_trace = tuple(candidate)
                    break
        if illegal_trace is not None:
            break
    assert illegal_trace is not None
    with pytest.raises(ValueError, match="illegally plays"):
        build_observed_record(
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            discarded_cards=data["discarded_cards"],
            plays=illegal_trace,
        )


def test_discarded_and_hand_skat_cards_cannot_appear_in_plays() -> None:
    play = ObservedPlayV1(
        decision_index=1,
        player_id="player-a",
        card="CA",
        decision_timecode=None,
    )
    with pytest.raises(ValueError, match="Discarded Card"):
        build_observed_record(
            declarer_player_id="player-a",
            declaration=GameDeclaration(game_type="grand"),
            discarded_cards=("CA", "D7"),
            plays=(play,),
        )
    with pytest.raises(ValueError, match="Hand-game original Skat"):
        build_observed_record(
            declarer_player_id="player-a",
            declaration=GameDeclaration(game_type="grand", hand_game=True),
            original_skat=("CA", "D7"),
            discarded_cards=(),
            plays=(play,),
        )


def test_complete_hand_and_non_hand_card_reconciliation_is_exact() -> None:
    hand_data = build_historical_input(game_type="clubs", hand_game=True)
    with pytest.raises(ValueError, match="original Skat"):
        build_observed_record(
            perspective_initial_hand=hand_data["players"][0]["initial_hand"],
            declarer_player_id=hand_data["declarer_player_id"],
            declaration=declaration_from_historical(hand_data),
            original_skat=("D9", "D8"),
            discarded_cards=(),
            plays=observed_plays_from_historical(hand_data),
        )

    non_hand_data = build_historical_input()
    with pytest.raises(ValueError, match="Discarded Card|Discards must equal"):
        build_observed_record(
            perspective_initial_hand=non_hand_data["players"][0]["initial_hand"],
            declarer_player_id=non_hand_data["declarer_player_id"],
            declaration=declaration_from_historical(non_hand_data),
            original_skat=non_hand_data["skat"],
            discarded_cards=("D9", "D8"),
            plays=observed_plays_from_historical(non_hand_data),
        )


def test_complete_perspective_hand_reconciliation_covers_all_roles() -> None:
    build_complete_observed_record(perspective_player_id="player-a")
    build_complete_observed_record(
        game_type="clubs",
        hand_game=True,
        perspective_player_id="player-b",
    )
    build_complete_observed_record(perspective_player_id="player-b")

    data = build_historical_input()
    wrong_hand = list(data["players"][0]["initial_hand"])
    wrong_hand[-1] = data["players"][1]["initial_hand"][-1]
    with pytest.raises(ValueError, match="perspective initial hand|Defender perspective hand"):
        build_observed_record(
            perspective_initial_hand=tuple(wrong_hand),
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            original_skat=data["skat"],
            discarded_cards=data["discarded_cards"],
            plays=observed_plays_from_historical(data),
        )


def test_missing_skat_and_discards_remain_null_after_complete_trace() -> None:
    record = build_complete_observed_record(
        include_original_skat=False,
        include_discards=False,
    )
    assert record.original_skat is None
    assert record.discarded_cards is None
    serialized = record.to_dict()
    assert serialized["original_skat"] is None
    assert serialized["discarded_cards"] is None


@pytest.mark.parametrize("discard_original_skat_count", (1, 2))
def test_non_hand_original_skat_may_overlap_discards_and_reconstruct_declarer_hand(
    discard_original_skat_count: int,
) -> None:
    data = build_historical_input()
    declarer_initial_hand = next(
        player["initial_hand"]
        for player in data["players"]
        if player["player_id"] == data["declarer_player_id"]
    )
    discarded_cards = tuple(
        [
            *data["skat"][:discard_original_skat_count],
            *declarer_initial_hand[: 2 - discard_original_skat_count],
        ]
    )
    _initial_playable_hands, plays = _plays_for_discards(data, discarded_cards)
    record = build_observed_record(
        match_definition=build_observed_match(
            perspective_player_id=data["declarer_player_id"]
        ),
        perspective_initial_hand=declarer_initial_hand,
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=discarded_cards,
        plays=plays,
    )
    assert set(record.original_skat).intersection(record.discarded_cards) == set(
        data["skat"][:discard_original_skat_count]
    )


def test_non_hand_declarer_partial_trace_enforces_transformed_hand_bedienpflicht() -> None:
    data = build_historical_input()
    declarer_initial_hand = next(
        player["initial_hand"]
        for player in data["players"]
        if player["player_id"] == data["declarer_player_id"]
    )
    discarded_cards = (data["skat"][0], declarer_initial_hand[0])
    _initial_playable_hands, full_plays = _plays_for_discards(data, discarded_cards)
    partial_plays = list(full_plays[:29])
    illegal_partial = None
    for first_index, first_play in enumerate(partial_plays):
        if first_play.player_id != data["declarer_player_id"]:
            continue
        for second_index in range(first_index + 1, len(partial_plays)):
            second_play = partial_plays[second_index]
            if second_play.player_id != data["declarer_player_id"]:
                continue
            candidate = partial_plays.copy()
            candidate[first_index] = replace(first_play, card=second_play.card)
            candidate[second_index] = replace(second_play, card=first_play.card)
            try:
                build_observed_record(
                    match_definition=build_observed_match(
                        perspective_player_id=data["declarer_player_id"]
                    ),
                    perspective_initial_hand=declarer_initial_hand,
                    declarer_player_id=data["declarer_player_id"],
                    declaration=declaration_from_historical(data),
                    original_skat=data["skat"],
                    discarded_cards=discarded_cards,
                    plays=tuple(candidate),
                )
            except ValueError as error:
                if "illegally plays" in str(error):
                    illegal_partial = tuple(candidate)
                    break
        if illegal_partial is not None:
            break
    assert illegal_partial is not None
    with pytest.raises(ValueError, match="illegally plays"):
        build_observed_record(
            match_definition=build_observed_match(
                perspective_player_id=data["declarer_player_id"]
            ),
            perspective_initial_hand=declarer_initial_hand,
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            original_skat=data["skat"],
            discarded_cards=discarded_cards,
            plays=illegal_partial,
        )


def test_complete_non_hand_declarer_rejects_inconsistent_initial_hand() -> None:
    data = build_historical_input()
    declarer_initial_hand = list(
        next(
            player["initial_hand"]
            for player in data["players"]
            if player["player_id"] == data["declarer_player_id"]
        )
    )
    declarer_initial_hand[-1] = data["players"][0]["initial_hand"][-1]
    with pytest.raises(ValueError, match="perspective initial hand|non-Hand Declarer"):
        build_observed_record(
            match_definition=build_observed_match(
                perspective_player_id=data["declarer_player_id"]
            ),
            perspective_initial_hand=tuple(declarer_initial_hand),
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            original_skat=data["skat"],
            discarded_cards=data["discarded_cards"],
            plays=observed_plays_from_historical(data),
        )


def test_derived_trace_summary_is_immutable_ordered_and_defensively_serialized() -> None:
    data = build_historical_input()
    record = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=observed_plays_from_historical(data, count=4),
    )
    summary = validate_observed_game_trace_v1(
        plays=record.plays,
        seat_order_player_ids=tuple(player.player_id for player in record.players),
        perspective_player_id=record.perspective_player_id,
        perspective_initial_hand=None,
        perspective_playable_hand=None,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        original_skat=None,
        discarded_cards=None,
        game_timecode=record.game_timecode,
    )
    first = summary.to_dict()
    second = summary.to_dict()
    first["plays"][0]["card"] = "D7"
    assert second["plays"][0]["card"] == record.plays[0].card
    assert [field.name for field in fields(summary)] == [
        "plays",
        "completed_trick_count",
        "current_trick_play_count",
        "winner_player_ids",
        "trick_points",
        "next_player_id",
        "player_play_counts",
        "complete_play_trace",
        "playable_hands",
    ]
    assert summary.completed_trick_count == 1
    assert summary.current_trick_play_count == 1
    assert not hasattr(summary, "__dict__")
    with pytest.raises(FrozenInstanceError):
        summary.completed_trick_count = 2
    with pytest.raises(TypeError, match="trace validator"):
        ObservedGameTraceSummaryV1()
