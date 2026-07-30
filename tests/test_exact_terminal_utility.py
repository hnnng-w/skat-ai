import pytest

from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import build_exact_search_state
from skat_ai.exact_terminal_utility import (
    build_exact_suit_or_grand_terminal_utility,
    build_exact_terminal_utility,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.rules import get_trick_points


def _terminal_state(
    *,
    declaration: GameDeclaration,
    declarer_points: int,
    declarer_tricks: int,
    out_of_play_cards: tuple[str, str] = ("D8", "D7"),
):
    completed_cards = [card for card in get_full_deck() if card not in out_of_play_cards]
    completed_points = get_trick_points(completed_cards)
    return build_exact_search_state(
        declaration=declaration,
        declarer_player="me",
        remaining_hands={"me": [], "left": [], "right": []},
        current_trick=(),
        next_player="me",
        declarer_trick_points=declarer_points,
        defender_trick_points=completed_points - declarer_points,
        declarer_completed_tricks=declarer_tricks,
        defender_completed_tricks=10 - declarer_tricks,
        out_of_play_cards=out_of_play_cards,
    )


@pytest.mark.parametrize("game_type", ["clubs", "spades", "hearts", "diamonds", "grand"])
def test_exact_terminal_utility_supports_every_suit_and_grand(game_type: str) -> None:
    state = _terminal_state(
        declaration=GameDeclaration(game_type, matadors=1, bid_value=18),
        declarer_points=61,
        declarer_tricks=6,
    )

    utility = build_exact_suit_or_grand_terminal_utility(
        state=state,
        local_side="declarer",
    )

    assert utility.game_type == game_type
    assert utility.local_contract_success is True
    assert utility.local_side_card_point_margin == 2


@pytest.mark.parametrize(
    ("declaration", "points", "tricks", "success", "score", "margin"),
    [
        (GameDeclaration("clubs", matadors=1, bid_value=18), 61, 6, True, 24, 2),
        (GameDeclaration("clubs", matadors=1, bid_value=18), 60, 5, False, -48, 0),
        (GameDeclaration("clubs", matadors=1, bid_value=25), 100, 9, False, -72, 80),
        (GameDeclaration("clubs", matadors=1, bid_value=18), 90, 9, True, 36, 60),
        (GameDeclaration("clubs", matadors=1, bid_value=18), 120, 10, True, 48, 120),
        (
            GameDeclaration(
                "clubs",
                hand_game=True,
                schneider_announced=True,
                matadors=1,
                bid_value=18,
            ),
            90,
            9,
            True,
            60,
            60,
        ),
        (
            GameDeclaration(
                "clubs",
                hand_game=True,
                schneider_announced=True,
                matadors=1,
                bid_value=18,
            ),
            89,
            9,
            False,
            -96,
            58,
        ),
        (
            GameDeclaration(
                "clubs",
                hand_game=True,
                schneider_announced=True,
                schwarz_announced=True,
                matadors=1,
                bid_value=18,
            ),
            120,
            10,
            True,
            84,
            120,
        ),
        (
            GameDeclaration(
                "clubs",
                hand_game=True,
                schneider_announced=True,
                schwarz_announced=True,
                matadors=1,
                bid_value=18,
            ),
            120,
            9,
            False,
            -144,
            120,
        ),
    ],
    ids=[
        "normal-win",
        "normal-loss-at-60",
        "overbid-despite-point-win",
        "achieved-schneider",
        "achieved-schwarz",
        "announced-schneider-achieved",
        "announced-schneider-failed",
        "announced-schwarz-achieved",
        "announced-schwarz-failed",
    ],
)
def test_exact_terminal_utility_uses_complete_settlement_behavior(
    declaration: GameDeclaration,
    points: int,
    tricks: int,
    success: bool,
    score: int,
    margin: int,
) -> None:
    state = _terminal_state(
        declaration=declaration,
        declarer_points=points,
        declarer_tricks=tricks,
    )

    utility = build_exact_suit_or_grand_terminal_utility(
        state=state,
        local_side="declarer",
    )

    assert utility.local_contract_success is success
    assert utility.local_side_game_score == score
    assert utility.local_side_card_point_margin == margin


@pytest.mark.parametrize(
    ("declaration", "declarer_tricks", "success", "score"),
    [
        (GameDeclaration("null", bid_value=23), 0, True, 23),
        (GameDeclaration("null", bid_value=23), 1, False, -46),
        (GameDeclaration("null", hand_game=True, bid_value=35), 0, True, 35),
        (GameDeclaration("null", hand_game=True, bid_value=35), 3, False, -70),
        (GameDeclaration("null", ouvert=True, bid_value=46), 0, True, 46),
        (GameDeclaration("null", ouvert=True, bid_value=46), 1, False, -92),
        (
            GameDeclaration("null", hand_game=True, ouvert=True, bid_value=59),
            0,
            True,
            59,
        ),
        (
            GameDeclaration("null", hand_game=True, ouvert=True, bid_value=59),
            1,
            False,
            -118,
        ),
    ],
    ids=[
        "null-win",
        "null-loss",
        "null-hand-win",
        "null-hand-loss",
        "null-ouvert-win",
        "null-ouvert-loss",
        "null-hand-ouvert-win",
        "null-hand-ouvert-loss",
    ],
)
def test_exact_null_terminal_utility_reuses_fixed_value_settlement(
    declaration: GameDeclaration,
    declarer_tricks: int,
    success: bool,
    score: int,
) -> None:
    state = _terminal_state(
        declaration=declaration,
        declarer_points=0,
        declarer_tricks=declarer_tricks,
    )

    utility = build_exact_terminal_utility(state=state, local_side="declarer")

    assert utility.game_type == "null"
    assert utility.local_contract_success is success
    assert utility.local_side_game_score == score
    assert utility.local_side_card_point_margin is None


def test_exact_null_terminal_utility_uses_tricks_not_card_points() -> None:
    state = _terminal_state(
        declaration=GameDeclaration("null", bid_value=23),
        declarer_points=0,
        declarer_tricks=0,
        out_of_play_cards=("DA", "D7"),
    )

    declarer = build_exact_terminal_utility(state=state, local_side="declarer")
    defenders = build_exact_terminal_utility(state=state, local_side="defenders")

    assert declarer.local_contract_success is True
    assert declarer.local_side_game_score == 23
    assert defenders.local_contract_success is False
    assert defenders.local_side_game_score == -23
    assert declarer.local_side_card_point_margin is None
    assert defenders.local_side_card_point_margin is None


def test_exact_null_terminal_utility_orients_defender_success() -> None:
    state = _terminal_state(
        declaration=GameDeclaration("null", bid_value=23),
        declarer_points=0,
        declarer_tricks=1,
    )

    utility = build_exact_terminal_utility(state=state, local_side="defenders")

    assert utility.local_contract_success is True
    assert utility.local_side_game_score == 46
    assert utility.local_side_card_point_margin is None


def test_exact_null_terminal_utility_rejects_missing_bid_and_overbid() -> None:
    missing_bid = _terminal_state(
        declaration=GameDeclaration("null"),
        declarer_points=0,
        declarer_tricks=0,
    )
    overbid = _terminal_state(
        declaration=GameDeclaration("null", bid_value=24),
        declarer_points=0,
        declarer_tricks=0,
    )

    with pytest.raises(ValueError, match="bid value"):
        build_exact_terminal_utility(state=missing_bid, local_side="declarer")
    with pytest.raises(ValueError, match="complete settlement"):
        build_exact_terminal_utility(state=overbid, local_side="declarer")


def test_exact_terminal_utility_orients_the_same_result_to_defenders() -> None:
    state = _terminal_state(
        declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        declarer_points=60,
        declarer_tricks=5,
    )

    utility = build_exact_suit_or_grand_terminal_utility(
        state=state,
        local_side="defenders",
    )

    assert utility.local_contract_success is True
    assert utility.local_side_game_score == 96
    assert utility.local_side_card_point_margin == 0


def test_exact_terminal_utility_rejects_null_and_missing_settlement_inputs() -> None:
    null_state = _terminal_state(
        declaration=GameDeclaration("null", bid_value=23),
        declarer_points=61,
        declarer_tricks=6,
    )
    missing_bid = _terminal_state(
        declaration=GameDeclaration("clubs", matadors=1),
        declarer_points=61,
        declarer_tricks=6,
    )

    with pytest.raises(ValueError, match="only Suit and Grand"):
        build_exact_suit_or_grand_terminal_utility(
            state=null_state,
            local_side="declarer",
        )
    with pytest.raises(ValueError, match="matadors and a bid value"):
        build_exact_suit_or_grand_terminal_utility(
            state=missing_bid,
            local_side="declarer",
        )


def test_exact_terminal_utility_requires_terminal_state() -> None:
    state = build_exact_search_state(
        declaration=GameDeclaration("clubs", matadors=1, bid_value=18),
        declarer_player="me",
        remaining_hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        current_trick=(),
        next_player="me",
        declarer_trick_points=50,
        defender_trick_points=70,
        declarer_completed_tricks=4,
        defender_completed_tricks=5,
        out_of_play_cards=("D8", "D7"),
    )

    with pytest.raises(ValueError, match="terminal"):
        build_exact_suit_or_grand_terminal_utility(
            state=state,
            local_side="declarer",
        )
