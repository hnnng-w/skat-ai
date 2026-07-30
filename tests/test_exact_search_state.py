from dataclasses import FrozenInstanceError

import pytest

from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import (
    ExactSearchPlay,
    ExactSearchState,
    apply_exact_search_card,
    build_exact_search_state,
    get_exact_search_legal_cards,
    get_exact_search_terminal_facts,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.rules import get_trick_points
from skat_ai.turn_phase import CONCRETE_PLAYERS


def _initial_hands() -> dict[str, list[str]]:
    playable_cards = get_full_deck()[:-2]
    return {
        player: playable_cards[index * 10 : (index + 1) * 10]
        for index, player in enumerate(CONCRETE_PLAYERS)
    }


def _state_arguments(
    *,
    hands: dict[str, list[str] | tuple[str, ...]],
    current_trick: list[tuple[str, str]] | tuple[tuple[str, str], ...] = (),
    next_player: str = "me",
    declaration: GameDeclaration | None = None,
    declarer_player: str = "me",
    out_of_play_cards: list[str] | tuple[str, ...] = ("D8", "D7"),
) -> dict[str, object]:
    explicit_cards = {
        *(card for hand in hands.values() for card in hand),
        *(card for _, card in current_trick),
        *out_of_play_cards,
    }
    completed_cards = [card for card in get_full_deck() if card not in explicit_cards]
    return {
        "declaration": declaration or GameDeclaration("grand"),
        "declarer_player": declarer_player,
        "remaining_hands": hands,
        "current_trick": current_trick,
        "next_player": next_player,
        "declarer_trick_points": 0,
        "defender_trick_points": get_trick_points(completed_cards),
        "declarer_completed_tricks": 0,
        "defender_completed_tricks": len(completed_cards) // 3,
        "out_of_play_cards": out_of_play_cards,
    }


def _build_state(**overrides: object) -> ExactSearchState:
    arguments = _state_arguments(
        hands={"me": ["C10"], "left": [], "right": ["C7"]},
        current_trick=[("left", "CA")],
        next_player="right",
    )
    arguments.update(overrides)
    return build_exact_search_state(**arguments)  # type: ignore[arg-type]


def test_state_is_frozen_hashable_and_requires_strict_builder() -> None:
    state = _build_state()

    assert hash(state) == hash(state)
    with pytest.raises(FrozenInstanceError):
        state.next_player = "me"  # type: ignore[misc]
    with pytest.raises(TypeError, match="build_exact_search_state"):
        ExactSearchState()


def test_builder_defensively_copies_and_canonicalizes_mutable_inputs() -> None:
    hands = _initial_hands()
    out_of_play_cards = ["D7", "D8"]
    state = build_exact_search_state(
        **_state_arguments(
            hands=hands,
            next_player="left",
            out_of_play_cards=out_of_play_cards,
        )
    )

    hands["me"].clear()
    out_of_play_cards.clear()

    assert len(state.hand_for("me")) == 10
    assert state.out_of_play_cards == ("D8", "D7")


def test_equivalent_source_orders_have_equal_states_and_hashes() -> None:
    hands = _initial_hands()
    first = build_exact_search_state(
        **_state_arguments(hands=hands, next_player="right")
    )
    second_arguments = _state_arguments(hands=hands, next_player="right")
    second_arguments["remaining_hands"] = [
        (player, list(reversed(hands[player]))) for player in reversed(CONCRETE_PLAYERS)
    ]
    second_arguments["out_of_play_cards"] = ["D7", "D8"]
    second = build_exact_search_state(**second_arguments)  # type: ignore[arg-type]

    assert first == second
    assert hash(first) == hash(second)


@pytest.mark.parametrize("game_type", ["clubs", "grand", "null"])
@pytest.mark.parametrize("next_player", CONCRETE_PLAYERS)
def test_initial_state_supports_all_contracts_and_turn_positions(
    game_type: str,
    next_player: str,
) -> None:
    state = build_exact_search_state(
        **_state_arguments(
            hands=_initial_hands(),
            next_player=next_player,
            declaration=GameDeclaration(game_type),
        )
    )

    assert state.remaining_plies == 30
    assert state.remaining_tricks == 10
    assert state.is_terminal is False
    assert len(state.hand_for(next_player)) == 10


def test_partial_and_late_game_state_counts_current_trick_once() -> None:
    state = _build_state()

    assert state.current_trick == (ExactSearchPlay("left", "CA"),)
    assert state.remaining_plies == 2
    assert state.remaining_tricks == 1
    assert state.is_terminal is False


def test_terminal_state_has_no_remaining_play() -> None:
    state = build_exact_search_state(
        **_state_arguments(
            hands={player: [] for player in CONCRETE_PLAYERS},
            next_player="left",
            out_of_play_cards=("CA", "C10"),
        )
    )

    assert state.remaining_plies == 0
    assert state.remaining_tricks == 0
    assert state.is_terminal is True
    assert get_exact_search_legal_cards(state) == ()


@pytest.mark.parametrize(
    ("game_type", "left_hand", "expected"),
    [
        ("clubs", ["SA", "C9"], ("C9",)),
        ("grand", ["SA", "HJ"], ("HJ",)),
        ("null", ["SA", "C9"], ("C9",)),
    ],
)
def test_legal_cards_use_canonical_rules_and_order(
    game_type: str,
    left_hand: list[str],
    expected: tuple[str, ...],
) -> None:
    state = build_exact_search_state(
        **_state_arguments(
            hands={"me": ["S7"], "left": left_hand, "right": ["H7", "D7"]},
            current_trick=[("me", "CJ")],
            next_player="left",
            declaration=GameDeclaration(game_type),
            out_of_play_cards=("D9", "D8"),
        )
    )

    assert get_exact_search_legal_cards(state) == expected


def test_lead_legal_cards_are_deterministically_canonical() -> None:
    hands = _initial_hands()
    hands["left"].reverse()
    state = build_exact_search_state(
        **_state_arguments(hands=hands, next_player="left")
    )

    assert get_exact_search_legal_cards(state) == tuple(_initial_hands()["left"])


def test_non_completing_transition_is_immutable_and_advances_one_seat() -> None:
    parent = build_exact_search_state(
        **_state_arguments(hands=_initial_hands(), next_player="left")
    )
    original_hand = parent.hand_for("left")
    transition = apply_exact_search_card(parent, original_hand[0])

    assert transition.actor == "left"
    assert transition.card == original_hand[0]
    assert transition.completed_trick is None
    assert transition.next_state.next_player == "right"
    assert transition.next_state.current_trick == (
        ExactSearchPlay("left", original_hand[0]),
    )
    assert transition.next_state.declarer_trick_points == parent.declarer_trick_points
    assert transition.next_state.defender_trick_points == parent.defender_trick_points
    assert parent.hand_for("left") == original_hand
    assert parent.current_trick == ()


@pytest.mark.parametrize(
    ("declarer_player", "winner_side", "point_field", "trick_field"),
    [
        ("left", "declarer", "declarer_trick_points", "declarer_completed_tricks"),
        ("me", "defenders", "defender_trick_points", "defender_completed_tricks"),
    ],
)
@pytest.mark.parametrize("game_type", ["clubs", "grand", "null"])
def test_trick_completing_transition_updates_winner_side_points_count_and_leader(
    game_type: str,
    declarer_player: str,
    winner_side: str,
    point_field: str,
    trick_field: str,
) -> None:
    arguments = _state_arguments(
        hands={"me": ["C10"], "left": [], "right": []},
        current_trick=[("left", "CA"), ("right", "C7")],
        next_player="me",
        declaration=GameDeclaration(game_type),
        declarer_player=declarer_player,
    )
    parent = build_exact_search_state(**arguments)  # type: ignore[arg-type]
    transition = apply_exact_search_card(parent, "C10")
    resolution = transition.completed_trick

    assert resolution is not None
    assert resolution.plays == (
        ExactSearchPlay("left", "CA"),
        ExactSearchPlay("right", "C7"),
        ExactSearchPlay("me", "C10"),
    )
    assert resolution.winner_player == "left"
    assert resolution.winner_side == winner_side
    assert resolution.trick_points == 21
    assert transition.next_state.next_player == "left"
    assert transition.next_state.current_trick == ()
    assert getattr(transition.next_state, point_field) == getattr(parent, point_field) + 21
    assert getattr(transition.next_state, trick_field) == getattr(parent, trick_field) + 1
    other_point_field = (
        "defender_trick_points" if winner_side == "declarer" else "declarer_trick_points"
    )
    other_trick_field = (
        "defender_completed_tricks"
        if winner_side == "declarer"
        else "declarer_completed_tricks"
    )
    assert getattr(transition.next_state, other_point_field) == getattr(parent, other_point_field)
    assert getattr(transition.next_state, other_trick_field) == getattr(parent, other_trick_field)
    assert parent.hand_for("me") == ("C10",)
    assert len(parent.current_trick) == 2


def test_transition_rejects_unowned_and_illegal_cards() -> None:
    state = build_exact_search_state(
        **_state_arguments(
            hands={"me": ["H7"], "left": ["C7", "S7"], "right": ["H8", "H9"]},
            current_trick=[("me", "SA")],
            next_player="left",
        )
    )

    with pytest.raises(ValueError, match="does not own"):
        apply_exact_search_card(state, "H8")
    with pytest.raises(ValueError, match="not legal"):
        apply_exact_search_card(state, "C7")


def test_transition_rejects_terminal_state() -> None:
    terminal = build_exact_search_state(
        **_state_arguments(
            hands={player: [] for player in CONCRETE_PLAYERS},
            next_player="me",
            out_of_play_cards=("CA", "C10"),
        )
    )

    with pytest.raises(ValueError, match="terminal"):
        apply_exact_search_card(terminal, "C7")


def test_equal_state_and_move_produce_equal_transitions() -> None:
    hands = _initial_hands()
    first = build_exact_search_state(
        **_state_arguments(hands=hands, next_player="me")
    )
    reordered = {player: list(reversed(cards)) for player, cards in hands.items()}
    second = build_exact_search_state(
        **_state_arguments(hands=reordered, next_player="me")
    )

    assert apply_exact_search_card(first, "CA") == apply_exact_search_card(second, "CA")


@pytest.mark.parametrize("game_type", ["clubs", "grand", "null"])
def test_terminal_facts_add_out_of_play_points_only_to_declarer(game_type: str) -> None:
    state = build_exact_search_state(
        **_state_arguments(
            hands={player: [] for player in CONCRETE_PLAYERS},
            next_player="right",
            declaration=GameDeclaration(game_type),
            out_of_play_cards=("CA", "C10"),
        )
    )
    facts = get_exact_search_terminal_facts(state)

    assert facts.out_of_play_points == 21
    assert facts.declarer_final_points == 21
    assert facts.defender_final_points == 99
    assert facts.declarer_final_points + facts.defender_final_points == 120
    assert facts.declarer_trick_count + facts.defender_trick_count == 10


def test_terminal_facts_reject_non_terminal_state() -> None:
    with pytest.raises(ValueError, match="terminal"):
        get_exact_search_terminal_facts(_build_state())


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("declarer_player", "unknown", "concrete declarer"),
        ("next_player", "unknown", "concrete next_player"),
        ("out_of_play_cards", ["D7"], "exactly two"),
        ("declarer_trick_points", -1, "non-negative"),
        ("defender_completed_tricks", -1, "non-negative"),
    ],
)
def test_builder_rejects_invalid_scalar_values(
    field_name: str,
    value: object,
    message: str,
) -> None:
    arguments = _state_arguments(hands=_initial_hands(), next_player="me")
    arguments[field_name] = value

    with pytest.raises(ValueError, match=message):
        build_exact_search_state(**arguments)  # type: ignore[arg-type]


def test_builder_rejects_invalid_declaration_and_cards() -> None:
    arguments = _state_arguments(hands=_initial_hands(), next_player="me")
    arguments["declaration"] = "grand"
    with pytest.raises(ValueError, match="GameDeclaration"):
        build_exact_search_state(**arguments)  # type: ignore[arg-type]

    hands = _initial_hands()
    hands["me"][0] = "XX"
    with pytest.raises(ValueError, match="Invalid cards"):
        build_exact_search_state(
            **_state_arguments(hands=hands, next_player="me")
        )


@pytest.mark.parametrize(
    ("remaining_hands", "message"),
    [
        ({"me": [], "left": []}, "Missing"),
        ({"me": [], "left": [], "right": [], "other": []}, "Unknown"),
        (
            [("me", []), ("left", []), ("right", []), ("me", [])],
            "Duplicate exact search hand player",
        ),
    ],
)
def test_builder_rejects_missing_unknown_and_duplicate_hand_players(
    remaining_hands: object,
    message: str,
) -> None:
    arguments = _state_arguments(
        hands={player: [] for player in CONCRETE_PLAYERS},
        next_player="me",
        out_of_play_cards=("CA", "C10"),
    )
    arguments["remaining_hands"] = remaining_hands

    with pytest.raises(ValueError, match=message):
        build_exact_search_state(**arguments)  # type: ignore[arg-type]


def test_builder_rejects_duplicate_explicit_cards() -> None:
    hands = _initial_hands()
    hands["left"][0] = hands["me"][0]

    with pytest.raises(ValueError, match="Duplicate explicit"):
        build_exact_search_state(
            **_state_arguments(hands=hands, next_player="me")
        )


def test_builder_rejects_current_trick_length_players_order_and_next_player() -> None:
    valid_arguments = _state_arguments(
        hands={"me": ["C10"], "left": [], "right": ["C7"]},
        current_trick=[("left", "CA")],
        next_player="right",
    )

    too_long = dict(valid_arguments)
    too_long["current_trick"] = [("me", "CA"), ("left", "C7"), ("right", "C10")]
    with pytest.raises(ValueError, match="more than two"):
        build_exact_search_state(**too_long)  # type: ignore[arg-type]

    duplicate_players = dict(valid_arguments)
    duplicate_players["current_trick"] = [("left", "CA"), ("left", "C7")]
    with pytest.raises(ValueError, match="duplicate players"):
        build_exact_search_state(**duplicate_players)  # type: ignore[arg-type]

    wrong_order = dict(valid_arguments)
    wrong_order["current_trick"] = [("left", "CA"), ("me", "C7")]
    with pytest.raises(ValueError, match="player order"):
        build_exact_search_state(**wrong_order)  # type: ignore[arg-type]

    wrong_next = dict(valid_arguments)
    wrong_next["next_player"] = "me"
    with pytest.raises(ValueError, match="next_player is inconsistent"):
        build_exact_search_state(**wrong_next)  # type: ignore[arg-type]


def test_builder_rejects_illegal_already_present_current_trick_play() -> None:
    arguments = _state_arguments(
        hands={"me": ["H7"], "left": ["C7"], "right": ["H8", "H9"]},
        current_trick=[("me", "CA"), ("left", "S7")],
        next_player="right",
    )

    with pytest.raises(ValueError, match="not a legal play"):
        build_exact_search_state(**arguments)  # type: ignore[arg-type]


def test_builder_rejects_hand_progression_and_incomplete_unresolved_trick() -> None:
    progression = _state_arguments(
        hands={"me": ["C10"], "left": ["S7"], "right": []},
        current_trick=[("left", "CA")],
        next_player="right",
    )
    with pytest.raises(ValueError, match="hand-size progression"):
        build_exact_search_state(**progression)  # type: ignore[arg-type]

    incomplete = _state_arguments(
        hands={"me": ["CA"], "left": [], "right": []},
        next_player="me",
        out_of_play_cards=("D8", "D7"),
    )
    with pytest.raises(ValueError, match="complete tricks"):
        build_exact_search_state(**incomplete)  # type: ignore[arg-type]


def test_builder_rejects_completed_card_trick_and_point_inconsistency() -> None:
    arguments = _state_arguments(
        hands={"me": ["C10"], "left": [], "right": ["C7"]},
        current_trick=[("left", "CA")],
        next_player="right",
    )

    wrong_tricks = dict(arguments)
    wrong_tricks["defender_completed_tricks"] = 8
    with pytest.raises(ValueError, match="Completed card count"):
        build_exact_search_state(**wrong_tricks)  # type: ignore[arg-type]

    wrong_points = dict(arguments)
    wrong_points["defender_trick_points"] = int(arguments["defender_trick_points"]) - 1
    with pytest.raises(ValueError, match="Completed card points"):
        build_exact_search_state(**wrong_points)  # type: ignore[arg-type]

    points_without_trick = dict(arguments)
    points_without_trick["declarer_trick_points"] = 1
    points_without_trick["defender_trick_points"] = (
        int(arguments["defender_trick_points"]) - 1
    )
    with pytest.raises(ValueError, match="without a completed trick"):
        build_exact_search_state(**points_without_trick)  # type: ignore[arg-type]
