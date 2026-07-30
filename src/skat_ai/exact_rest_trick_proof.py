from dataclasses import dataclass

from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import (
    ExactSearchState,
    apply_exact_search_card,
    build_exact_search_state,
    get_exact_search_legal_cards,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.rules import get_trick_points
from skat_ai.turn_phase import CONCRETE_PLAYERS, derive_next_player


@dataclass(frozen=True)
class ExactPlayMove:
    player: str
    card: str
    trick_winner: str | None = None


@dataclass(frozen=True)
class ExactRemainingPlayState:
    game_type: str
    hands: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]
    current_trick: tuple[tuple[str, str], ...]
    next_player: str


@dataclass(frozen=True)
class DefenderRestTrickProof:
    status: str
    proof_complete: bool
    remaining_trick_count: int
    evaluated_state_count: int
    memoized_state_count: int
    counterexample_found: bool
    line: tuple[ExactPlayMove, ...]


def _canonical_cards(cards: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    order = {card: index for index, card in enumerate(get_full_deck())}
    return tuple(sorted(cards, key=order.__getitem__))


def build_exact_remaining_play_state(
    *,
    game_type: str,
    remaining_hands: dict[str, tuple[str, ...]],
    current_trick_cards: list[str],
    trick_leader: str,
    next_player: str,
) -> ExactRemainingPlayState:
    """Builds one canonical immutable state for exact late-game proof."""
    current_players = [
        derive_next_player(trick_leader, index) for index in range(len(current_trick_cards))
    ]
    return ExactRemainingPlayState(
        game_type=game_type,
        hands=tuple(_canonical_cards(remaining_hands[player]) for player in CONCRETE_PLAYERS),
        current_trick=tuple(zip(current_players, current_trick_cards, strict=True)),
        next_player=next_player,
    )


def prove_defender_rest_tricks(
    state: ExactRemainingPlayState | ExactSearchState,
    exposing_defender: str,
    declarer_player: str,
) -> DefenderRestTrickProof:
    """Exhaustively proves whether the declarer can be denied every remaining trick."""
    if exposing_defender == declarer_player:
        raise ValueError("The exposing defender cannot be the declarer.")
    if exposing_defender not in CONCRETE_PLAYERS or declarer_player not in CONCRETE_PLAYERS:
        raise ValueError("Exact rest-trick proof requires concrete players.")

    unresolved_card_count = sum(len(hand) for hand in state.hands) + len(state.current_trick)
    if unresolved_card_count == 0 or unresolved_card_count % 3 != 0:
        raise ValueError("Exact rest-trick proof requires complete unresolved tricks.")
    remaining_trick_count = unresolved_card_count // 3
    if remaining_trick_count > 5:
        raise ValueError("Exact rest-trick proof supports at most five remaining tricks.")

    if isinstance(state, ExactSearchState):
        if state.declarer_player != declarer_player:
            raise ValueError("Exact proof declarer_player contradicts the exact search state.")
        search_root = state
    else:
        explicit_cards = {
            *(card for hand in state.hands for card in hand),
            *(card for _, card in state.current_trick),
        }
        completed_or_out_of_play = [
            card for card in get_full_deck() if card not in explicit_cards
        ]
        out_of_play_cards = completed_or_out_of_play[:2]
        completed_cards = completed_or_out_of_play[2:]
        search_root = build_exact_search_state(
            declaration=GameDeclaration(state.game_type),
            declarer_player=declarer_player,
            remaining_hands=zip(CONCRETE_PLAYERS, state.hands, strict=True),
            current_trick=state.current_trick,
            next_player=state.next_player,
            declarer_trick_points=0,
            defender_trick_points=get_trick_points(completed_cards),
            declarer_completed_tricks=0,
            defender_completed_tricks=len(completed_cards) // 3,
            out_of_play_cards=out_of_play_cards,
        )

    cache: dict[ExactSearchState, tuple[bool, tuple[ExactPlayMove, ...]]] = {}
    evaluated_state_count = 0

    def search(
        current_state: ExactSearchState,
    ) -> tuple[bool, tuple[ExactPlayMove, ...]]:
        nonlocal evaluated_state_count
        cached = cache.get(current_state)
        if cached is not None:
            return cached
        evaluated_state_count += 1

        if current_state.is_terminal:
            result = (True, ())
            cache[current_state] = result
            return result

        player = current_state.next_player
        legal_cards = get_exact_search_legal_cards(current_state)
        child_results: list[tuple[bool, tuple[ExactPlayMove, ...]]] = []

        for card in legal_cards:
            transition = apply_exact_search_card(current_state, card)
            resolution = transition.completed_trick
            trick_winner = resolution.winner_player if resolution is not None else None

            if resolution is not None:
                if trick_winner == declarer_player:
                    child_result = (
                        False,
                        (ExactPlayMove(player, card, trick_winner),),
                    )
                    child_results.append(child_result)
                    continue

            child_valid, child_line = search(transition.next_state)
            child_results.append(
                (
                    child_valid,
                    (ExactPlayMove(player, card, trick_winner), *child_line),
                )
            )

        if player == exposing_defender:
            selected = next(
                (child for child in child_results if child[0]),
                child_results[0],
            )
        else:
            selected = next(
                (child for child in child_results if not child[0]),
                child_results[0],
            )

        cache[current_state] = selected
        return selected

    valid, line = search(search_root)
    return DefenderRestTrickProof(
        status="valid" if valid else "invalid",
        proof_complete=True,
        remaining_trick_count=remaining_trick_count,
        evaluated_state_count=evaluated_state_count,
        memoized_state_count=len(cache),
        counterexample_found=not valid,
        line=line,
    )
