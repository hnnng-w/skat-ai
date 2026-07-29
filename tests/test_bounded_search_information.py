from dataclasses import FrozenInstanceError, replace

import pytest

from skat_ai.bounded_search_information import (
    HISTORICAL_DECISION_SNAPSHOT_SOURCE,
    LIVE_LOCAL_VIEW_SOURCE,
    SearchRemainingHandSize,
    assess_search_eligibility,
    build_historical_search_information_view,
    build_live_search_information_view,
    get_remaining_search_card_count,
    get_remaining_search_trick_count,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.historical_snapshot_adapter import HistoricalSnapshotPosition
from skat_ai.public_hand_constraint import (
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PublicHandConstraint,
)


def _declaration(
    *,
    game_type: str = "grand",
    matadors: int | None = 1,
    bid_value: int | None = 18,
) -> GameDeclaration:
    return GameDeclaration(
        game_type=game_type,
        matadors=None if game_type == "null" else matadors,
        bid_value=bid_value,
    )


def _state_for_seat(seat: str) -> tuple[GameState, int, int]:
    current_by_seat = {
        "lead": ([], "me", "me", 2, 2),
        "second": (["C8"], "right", "me", 2, 1),
        "third": (["C8", "C9"], "left", "me", 1, 1),
    }
    current_trick, leader, next_player, left_size, right_size = current_by_seat[seat]
    return (
        GameState(
            game_type="grand",
            player_role="declarer",
            declarer_player="me",
            hand=["DA", "C7"],
            current_trick=current_trick,
            trick_leader=leader,
            next_player=next_player,
        ),
        left_size,
        right_size,
    )


def _view_for_seat(seat: str = "lead"):
    state, left_size, right_size = _state_for_seat(seat)
    return build_live_search_information_view(
        state=state,
        declaration=_declaration(),
        left_hand_size=left_size,
        right_hand_size=right_size,
    )


def test_search_information_values_are_frozen_and_defensively_copied() -> None:
    hand = ["DA", "C7"]
    public_cards = ["H10", "H7"]
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=hand,
        current_trick=[],
        trick_leader="me",
        next_player="me",
        skat=["S8", "S7"],
    )
    constraint = PublicHandConstraint(
        player="left",
        cards=public_cards,  # type: ignore[arg-type]
        source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    )

    view = build_live_search_information_view(
        state=state,
        declaration=_declaration(),
        left_hand_size=2,
        right_hand_size=2,
        skat_visibility="known_to_declarer",
        public_hand_constraints=(constraint,),
    )
    hand.append("D7")
    public_cards.append("H8")
    state.skat.append("S9")

    assert view.local_remaining_hand == ("C7", "DA")
    assert view.known_skat_cards == ("S8", "S7")
    assert view.public_hand_constraints[0].cards == ("H10", "H7")
    with pytest.raises(FrozenInstanceError):
        view.next_player = "left"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        view.remaining_hand_sizes[0].card_count = 3  # type: ignore[misc]


def test_live_view_redacts_non_local_skat_and_rejects_post_game_visibility() -> None:
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["DA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
        skat=["CA", "SA"],
    )

    view = build_live_search_information_view(
        state=state,
        declaration=_declaration(),
        left_hand_size=1,
        right_hand_size=1,
        skat_visibility="known_to_declarer",
    )

    assert view.known_skat_cards == ()
    with pytest.raises(ValueError, match="post-game Skat"):
        build_live_search_information_view(
            state=state,
            declaration=_declaration(),
            left_hand_size=1,
            right_hand_size=1,
            skat_visibility="known_post_game",
        )


def test_live_hand_game_rejects_declarer_private_skat_claim() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["DA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
        skat=["CA", "SA"],
    )
    declaration = GameDeclaration(
        game_type="grand",
        hand_game=True,
        matadors=1,
        bid_value=18,
    )

    with pytest.raises(ValueError, match="Hand game cannot expose Skat"):
        build_live_search_information_view(
            state=state,
            declaration=declaration,
            left_hand_size=1,
            right_hand_size=1,
            skat_visibility="known_to_declarer",
        )


def test_live_and_historical_adapters_share_the_same_normalized_view() -> None:
    state, left_size, right_size = _state_for_seat("third")
    state.skat = ["S8", "S7"]
    public_constraint = PublicHandConstraint(
        player="left",
        cards=("H10",),
        source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    )
    live = build_live_search_information_view(
        state=state,
        declaration=_declaration(),
        left_hand_size=left_size,
        right_hand_size=right_size,
        skat_visibility="known_to_declarer",
        public_hand_constraints=(public_constraint,),
    )
    position = HistoricalSnapshotPosition(
        state=GameState(**vars(state)),
        legal_cards=("C7",),
        left_hand_size=left_size,
        right_hand_size=right_size,
        game_declaration=_declaration(),
        public_hand_constraints=(public_constraint,),
    )

    historical = build_historical_search_information_view(position)

    assert live.source == LIVE_LOCAL_VIEW_SOURCE
    assert historical.source == HISTORICAL_DECISION_SNAPSHOT_SOURCE
    assert replace(historical, source=LIVE_LOCAL_VIEW_SOURCE) == live


def test_private_worlds_and_future_fields_cannot_change_the_shared_prefix() -> None:
    first_state, left_size, right_size = _state_for_seat("lead")
    second_state, _, _ = _state_for_seat("lead")
    first_state.actual_left_hand = ["CA", "SA"]
    first_state.future_winner = "declarer"
    second_state.actual_left_hand = ["HA", "H10"]
    second_state.future_winner = "defenders"

    first = build_live_search_information_view(
        state=first_state,
        declaration=_declaration(),
        left_hand_size=left_size,
        right_hand_size=right_size,
    )
    second = build_live_search_information_view(
        state=second_state,
        declaration=_declaration(),
        left_hand_size=left_size,
        right_hand_size=right_size,
    )

    assert first == second
    view = first
    assert set(vars(view)).isdisjoint(
        {
            "left_hand",
            "right_hand",
            "hypothetical_skat",
            "future_winner",
            "actual_card_played",
            "final_settlement",
        }
    )
    assert view.information_cutoff == "current_decision"


@pytest.mark.parametrize(
    ("seat", "expected_players"),
    [
        ("lead", ()),
        ("second", ("right",)),
        ("third", ("left", "right")),
    ],
)
def test_lead_second_and_third_seat_views_are_eligible(
    seat: str,
    expected_players: tuple[str, ...],
) -> None:
    view = _view_for_seat(seat)

    eligibility = assess_search_eligibility(view, 2)

    assert eligibility.eligible is True
    assert eligibility.unavailable_reason is None
    assert tuple(play.player for play in view.current_trick) == expected_players
    assert eligibility.remaining_plies == 6
    assert eligibility.remaining_tricks == 2


def test_remaining_counts_include_cards_already_in_partial_trick() -> None:
    second = _view_for_seat("second")
    third = _view_for_seat("third")

    assert get_remaining_search_card_count(second) == 6
    assert get_remaining_search_card_count(third) == 6
    assert get_remaining_search_trick_count(second) == 2
    assert get_remaining_search_trick_count(third) == 2


def test_completed_public_history_normalizes_points_tricks_and_nested_values() -> None:
    completed = {
        "cards": ["C7", "CA", "C8"],
        "players": ["me", "left", "right"],
        "winner_player": "left",
        "winner_role": "defenders",
    }
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["S9"],
        current_trick=["S7", "S8"],
        trick_leader="left",
        next_player="me",
        completed_tricks=[completed],
        declarer_points=5,
        defender_points=6,
    )

    view = build_live_search_information_view(
        state=state,
        declaration=_declaration(),
        left_hand_size=0,
        right_hand_size=0,
    )
    completed["cards"][0] = "DA"
    completed["players"][0] = "right"

    assert tuple(play.card for play in view.completed_tricks[0].plays) == (
        "C7",
        "CA",
        "C8",
    )
    assert view.completed_tricks[0].winner_player == "left"
    assert view.completed_tricks[0].trick_points == 11
    assert view.declarer_points == 5
    assert view.defender_points == 17
    assert view.declarer_trick_count == 0
    assert view.defender_trick_count == 1


def _reason_view(reason: str):
    base = _view_for_seat("lead")
    if reason == "unsupported_perspective":
        return replace(base, perspective_player="left", local_side="defenders")
    if reason == "missing_concrete_declarer":
        state = GameState(
            game_type="grand",
            player_role="unknown",
            declarer_player="unknown",
            hand=["DA"],
            current_trick=[],
            trick_leader="me",
            next_player="me",
        )
        return build_live_search_information_view(
            state=state,
            declaration=_declaration(),
            left_hand_size=1,
            right_hand_size=1,
        )
    if reason == "game_already_complete":
        state = GameState(
            game_type="grand",
            player_role="declarer",
            declarer_player="me",
            hand=[],
            current_trick=[],
            trick_leader="me",
            next_player="me",
        )
        return build_live_search_information_view(
            state=state,
            declaration=_declaration(),
            left_hand_size=0,
            right_hand_size=0,
        )
    if reason == "unsupported_turn_phase":
        return replace(base, next_player="unknown")
    if reason == "local_player_not_to_act":
        return replace(base, next_player="left")
    if reason == "no_legal_cards":
        sizes = (
            SearchRemainingHandSize("me", 0),
            SearchRemainingHandSize("left", 2),
            SearchRemainingHandSize("right", 2),
        )
        return replace(base, local_remaining_hand=(), remaining_hand_sizes=sizes)
    if reason == "missing_terminal_utility_inputs":
        return replace(base, declaration=_declaration(matadors=None))
    if reason == "remaining_trick_limit_exceeded":
        return base
    raise AssertionError(f"Unhandled reason fixture: {reason}")


@pytest.mark.parametrize(
    "reason",
    [
        "unsupported_perspective",
        "missing_concrete_declarer",
        "game_already_complete",
        "unsupported_turn_phase",
        "local_player_not_to_act",
        "no_legal_cards",
        "missing_terminal_utility_inputs",
        "remaining_trick_limit_exceeded",
    ],
)
def test_current_eligibility_assessment_reports_each_supported_unavailable_reason(
    reason: str,
) -> None:
    limit = 1 if reason == "remaining_trick_limit_exceeded" else 2

    eligibility = assess_search_eligibility(_reason_view(reason), limit)

    assert eligibility.eligible is False
    assert eligibility.unavailable_reason == reason


def test_contradictory_known_card_ownership_is_a_validation_error() -> None:
    state, left_size, right_size = _state_for_seat("second")
    state.hand.append("C8")

    with pytest.raises(ValueError, match="Duplicate known cards"):
        build_live_search_information_view(
            state=state,
            declaration=_declaration(),
            left_hand_size=left_size,
            right_hand_size=right_size,
        )


def test_legacy_unattributed_played_cards_are_rejected_instead_of_discarded() -> None:
    state, left_size, right_size = _state_for_seat("lead")
    state.played_cards = ["S7"]

    with pytest.raises(ValueError, match="attributed completed trick history"):
        build_live_search_information_view(
            state=state,
            declaration=_declaration(),
            left_hand_size=left_size,
            right_hand_size=right_size,
        )


def test_public_hand_size_and_source_must_match_visible_position() -> None:
    state, left_size, right_size = _state_for_seat("lead")
    wrong_size = PublicHandConstraint(
        player="left",
        cards=("H10",),
        source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    )
    wrong_source = PublicHandConstraint(
        player="me",
        cards=tuple(state.hand),
        source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    )

    with pytest.raises(ValueError, match="hand size does not match"):
        build_live_search_information_view(
            state=state,
            declaration=_declaration(),
            left_hand_size=left_size,
            right_hand_size=right_size,
            public_hand_constraints=(wrong_size,),
        )
    with pytest.raises(ValueError, match="must expose a defender"):
        build_live_search_information_view(
            state=state,
            declaration=_declaration(),
            left_hand_size=left_size,
            right_hand_size=right_size,
            public_hand_constraints=(wrong_source,),
        )


def test_eligibility_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        assess_search_eligibility(_view_for_seat(), 0)
