import copy
import random

import pytest

from skat_ai.deck import get_full_deck
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_historical_game_summary_from_input,
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
