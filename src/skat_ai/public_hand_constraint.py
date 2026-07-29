from dataclasses import dataclass, replace
from typing import Any

from skat_ai.deck import get_full_deck

PUBLIC_HAND_VISIBILITY_SCOPE = "all_players"
DECLARED_OUVERT_SOURCE = "declared_ouvert"
DECLARER_EXPOSURE_CONTINUATION_SOURCE = "declarer_card_exposure_continuation"
DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE = "defender_open_play_continuation"


@dataclass(frozen=True)
class PublicHandConstraint:
    """Fixes one player's complete current hand as public information."""

    player: str
    cards: tuple[str, ...]
    visibility_scope: str = PUBLIC_HAND_VISIBILITY_SCOPE
    source: str = DECLARER_EXPOSURE_CONTINUATION_SOURCE


def canonicalize_cards(cards: tuple[str, ...]) -> tuple[str, ...]:
    """Returns cards in stable deck order."""
    order = {card: index for index, card in enumerate(get_full_deck())}
    return tuple(sorted(cards, key=order.__getitem__))


def build_serializable_public_hand_constraint(
    constraint: PublicHandConstraint,
) -> dict[str, Any]:
    """Builds the stable public constraint output shape."""
    cards = list(canonicalize_cards(constraint.cards))
    return {
        "player": constraint.player,
        "source": constraint.source,
        "visibility_scope": constraint.visibility_scope,
        "card_count": len(cards),
        "cards": cards,
    }


def build_serializable_public_hand_constraints(
    constraints: tuple[PublicHandConstraint, ...],
) -> list[dict[str, Any]]:
    """Builds deterministic output for all rule-authorized public hands."""
    player_order = {"me": 0, "left": 1, "right": 2}
    return [
        build_serializable_public_hand_constraint(constraint)
        for constraint in sorted(
            constraints,
            key=lambda constraint: player_order[constraint.player],
        )
    ]


def remove_public_hand_cards(
    constraints: tuple[PublicHandConstraint, ...],
    played_cards: list[str] | tuple[str, ...],
) -> tuple[PublicHandConstraint, ...]:
    """Removes newly played cards while preserving every other public card."""
    played = set(played_cards)
    return tuple(
        replace(
            constraint,
            cards=tuple(card for card in constraint.cards if card not in played),
        )
        for constraint in constraints
    )


def get_constrained_hand_sizes(
    constraints: tuple[PublicHandConstraint, ...],
    left_hand_size: int,
    right_hand_size: int,
) -> tuple[int, int]:
    """Uses exact public hand sizes after exposed cards have been played."""
    for constraint in constraints:
        if constraint.player == "left":
            left_hand_size = len(constraint.cards)
        elif constraint.player == "right":
            right_hand_size = len(constraint.cards)
    return left_hand_size, right_hand_size
