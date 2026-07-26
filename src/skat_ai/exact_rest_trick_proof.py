from dataclasses import dataclass

from skat_ai.deck import get_full_deck
from skat_ai.rules import get_legal_cards, get_trick_winner
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
    state: ExactRemainingPlayState,
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

    cache: dict[ExactRemainingPlayState, tuple[bool, tuple[ExactPlayMove, ...]]] = {}
    evaluated_state_count = 0

    def search(
        current_state: ExactRemainingPlayState,
    ) -> tuple[bool, tuple[ExactPlayMove, ...]]:
        nonlocal evaluated_state_count
        cached = cache.get(current_state)
        if cached is not None:
            return cached
        evaluated_state_count += 1

        if not any(current_state.hands):
            result = (True, ())
            cache[current_state] = result
            return result

        player = current_state.next_player
        player_index = CONCRETE_PLAYERS.index(player)
        hand = current_state.hands[player_index]
        trick_cards = [card for _, card in current_state.current_trick]
        legal_cards = _canonical_cards(
            get_legal_cards(list(hand), trick_cards, current_state.game_type)
        )
        child_results: list[tuple[bool, tuple[ExactPlayMove, ...]]] = []

        for card in legal_cards:
            next_hand = tuple(held_card for held_card in hand if held_card != card)
            next_hands = list(current_state.hands)
            next_hands[player_index] = next_hand
            next_trick = (*current_state.current_trick, (player, card))
            trick_winner = None

            if len(next_trick) == 3:
                winner_index = get_trick_winner(
                    [played_card for _, played_card in next_trick],
                    current_state.game_type,
                )
                trick_winner = next_trick[winner_index][0]
                if trick_winner == declarer_player:
                    child_result = (
                        False,
                        (ExactPlayMove(player, card, trick_winner),),
                    )
                    child_results.append(child_result)
                    continue
                child_state = ExactRemainingPlayState(
                    game_type=current_state.game_type,
                    hands=tuple(next_hands),
                    current_trick=(),
                    next_player=trick_winner,
                )
            else:
                child_state = ExactRemainingPlayState(
                    game_type=current_state.game_type,
                    hands=tuple(next_hands),
                    current_trick=next_trick,
                    next_player=derive_next_player(player, 1),
                )

            child_valid, child_line = search(child_state)
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

    valid, line = search(state)
    return DefenderRestTrickProof(
        status="valid" if valid else "invalid",
        proof_complete=True,
        remaining_trick_count=remaining_trick_count,
        evaluated_state_count=evaluated_state_count,
        memoized_state_count=len(cache),
        counterexample_found=not valid,
        line=line,
    )
