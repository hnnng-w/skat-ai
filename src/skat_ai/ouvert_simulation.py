from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import GameDeclaration, build_game_declaration_from_input
from skat_ai.public_hand_constraint import (
    DECLARED_OUVERT_SOURCE,
    DECLARER_EXPOSURE_CONTINUATION_SOURCE,
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PUBLIC_HAND_VISIBILITY_SCOPE,
    PublicHandConstraint,
    canonicalize_cards,
)

CONCRETE_PLAYERS = ("me", "left", "right")
PUBLIC_HAND_SOURCE_PRECEDENCE = {
    DECLARED_OUVERT_SOURCE: 0,
    DECLARER_EXPOSURE_CONTINUATION_SOURCE: 1,
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE: 2,
}


def _get_completed_trick_cards(data: dict[str, Any]) -> list[str]:
    return [
        card
        for trick in data.get("completed_tricks", [])
        if isinstance(trick, dict)
        for card in trick.get("cards", [])
        if isinstance(card, str)
    ]


def validate_declared_ouvert_public_cards(
    data: dict[str, Any],
    declaration: GameDeclaration | None = None,
) -> tuple[str, ...] | None:
    """Validates and returns the exact current declared-Ouvert hand."""
    declaration = declaration or build_game_declaration_from_input(data)
    supplied = "public_declarer_cards" in data
    raw_cards = data.get("public_declarer_cards")

    if supplied and not declaration.ouvert:
        raise ValueError("public_declarer_cards is allowed only when ouvert=true.")
    if not declaration.ouvert:
        return None

    declarer_player = data.get("declarer_player")
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "Declared Ouvert analysis requires declarer_player to be me, left, or right."
        )

    supplied_cards: list[str] | None = None
    if supplied:
        if not isinstance(raw_cards, list):
            raise ValueError("public_declarer_cards must be an array.")
        if len(raw_cards) > 10:
            raise ValueError("public_declarer_cards must contain at most 10 cards.")
        if not all(isinstance(card, str) for card in raw_cards):
            raise ValueError("public_declarer_cards must contain only card strings.")
        valid_cards = set(get_full_deck())
        invalid_cards = [card for card in raw_cards if card not in valid_cards]
        if invalid_cards:
            raise ValueError(f"Invalid cards in public_declarer_cards: {invalid_cards}")
        duplicates = sorted(
            {card for card in raw_cards if raw_cards.count(card) > 1}
        )
        if duplicates:
            raise ValueError(
                f"Duplicate cards in public_declarer_cards: {duplicates}"
            )
        supplied_cards = raw_cards

    hand = data.get("hand", [])
    if declarer_player == "me":
        if supplied_cards is not None and set(supplied_cards) != set(hand):
            raise ValueError(
                "public_declarer_cards must exactly match hand when declarer_player='me'."
            )
        cards = list(hand)
    else:
        if supplied_cards is None:
            raise ValueError(
                "Declared Ouvert analysis with an opponent declarer requires "
                "public_declarer_cards."
            )
        cards = supplied_cards
        hand_size_field = f"{declarer_player}_hand_size"
        expected_count = data[hand_size_field]
        if len(cards) != expected_count:
            raise ValueError(
                f"public_declarer_cards has {len(cards)} cards, but "
                f"{hand_size_field} is {expected_count}."
            )

    card_set = set(cards)
    contradiction_fields = {
        "played_cards": data.get("played_cards", []),
        "current_trick": data.get("current_trick", []),
        "completed_tricks": _get_completed_trick_cards(data),
        "skat": data.get("skat", []),
    }
    if declarer_player != "me":
        contradiction_fields["hand"] = hand

    for field_name, known_cards in contradiction_fields.items():
        contradictions = sorted(card_set.intersection(known_cards))
        if contradictions:
            raise ValueError(
                "public_declarer_cards contradicts cards in "
                f"{field_name}: {contradictions}"
            )

    return canonicalize_cards(tuple(cards))


def build_declared_ouvert_public_hand_constraint(
    data: dict[str, Any],
    declaration: GameDeclaration | None = None,
) -> PublicHandConstraint | None:
    """Builds the exact all-player public hand for a declared Ouvert game."""
    cards = validate_declared_ouvert_public_cards(data, declaration)
    if cards is None:
        return None
    return PublicHandConstraint(
        player=data["declarer_player"],
        cards=cards,
        source=DECLARED_OUVERT_SOURCE,
    )


def resolve_effective_public_hand_constraints(
    constraints: tuple[PublicHandConstraint, ...],
) -> tuple[PublicHandConstraint, ...]:
    """Deduplicates compatible public hands and rejects ownership conflicts."""
    constraints_by_player: dict[str, PublicHandConstraint] = {}
    full_deck = set(get_full_deck())

    for constraint in constraints:
        if constraint.player not in CONCRETE_PLAYERS:
            raise ValueError("Public hand constraints require player me, left, or right.")
        if constraint.visibility_scope != PUBLIC_HAND_VISIBILITY_SCOPE:
            raise ValueError("Public hand constraints must be visible to all players.")
        if constraint.source not in PUBLIC_HAND_SOURCE_PRECEDENCE:
            raise ValueError(f"Unsupported public hand source: {constraint.source}")
        if len(set(constraint.cards)) != len(constraint.cards):
            raise ValueError("Public hand constraints must contain unique cards.")
        invalid_cards = sorted(set(constraint.cards) - full_deck)
        if invalid_cards:
            raise ValueError(f"Invalid cards in public hand constraint: {invalid_cards}")

        canonical_constraint = PublicHandConstraint(
            player=constraint.player,
            cards=canonicalize_cards(constraint.cards),
            visibility_scope=constraint.visibility_scope,
            source=constraint.source,
        )
        existing = constraints_by_player.get(constraint.player)
        if existing is None:
            constraints_by_player[constraint.player] = canonical_constraint
            continue
        if set(existing.cards) != set(canonical_constraint.cards):
            raise ValueError(
                f"Contradictory public hand constraints for {constraint.player}."
            )
        if PUBLIC_HAND_SOURCE_PRECEDENCE[canonical_constraint.source] < (
            PUBLIC_HAND_SOURCE_PRECEDENCE[existing.source]
        ):
            constraints_by_player[constraint.player] = canonical_constraint

    assigned_cards: dict[str, str] = {}
    for player, constraint in constraints_by_player.items():
        for card in constraint.cards:
            existing_player = assigned_cards.get(card)
            if existing_player is not None and existing_player != player:
                raise ValueError(
                    "Public hand constraints assign "
                    f"{card} to both {existing_player} and {player}."
                )
            assigned_cards[card] = player

    return tuple(
        constraints_by_player[player]
        for player in CONCRETE_PLAYERS
        if player in constraints_by_player
    )
