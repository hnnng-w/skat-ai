from __future__ import annotations

from dataclasses import dataclass

from skatmind.deck import get_full_deck
from skatmind.rules import get_card_name


@dataclass(frozen=True, slots=True)
class CardFormControlV1:
    """One canonical text-only Card control for the guided frontend."""

    code: str
    name: str
    label: str

    def __post_init__(self) -> None:
        if type(self.code) is not str or self.code not in get_full_deck():
            raise ValueError("Card control code must belong to the canonical Skat deck.")
        if self.name != get_card_name(self.code):
            raise ValueError("Card control name must use the existing Card-name helper.")
        if self.label != f"{self.name} ({self.code})":
            raise ValueError("Card control label must include the readable name and code.")


@dataclass(frozen=True, slots=True)
class CardZoneSelectionV1:
    """One immutable mutually exclusive known-Card zone."""

    field: str
    cards: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.field) is not str or not self.field:
            raise ValueError("Card zone field must be non-empty text.")
        cards = tuple(self.cards)
        object.__setattr__(self, "cards", cards)
        if any(type(card) is not str for card in cards):
            raise ValueError("Card zone values must be strings.")


@dataclass(frozen=True, slots=True)
class CardZoneConflictV1:
    """One Card selected more than once across exclusive known zones."""

    card: str
    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.card) is not str or not self.card:
            raise ValueError("Card conflict Card must be non-empty text.")
        fields = tuple(self.fields)
        object.__setattr__(self, "fields", fields)
        if len(fields) < 1 or any(type(field) is not str or not field for field in fields):
            raise ValueError("Card conflict fields must identify one or more zones.")


def _build_canonical_card_controls_v1() -> tuple[CardFormControlV1, ...]:
    return tuple(
        CardFormControlV1(
            code=card,
            name=get_card_name(card),
            label=f"{get_card_name(card)} ({card})",
        )
        for card in get_full_deck()
    )


CANONICAL_CARD_CONTROLS_V1 = _build_canonical_card_controls_v1()


def get_canonical_card_controls_v1() -> tuple[CardFormControlV1, ...]:
    """Returns the immutable canonical 32-Card controls in Deck order."""

    return CANONICAL_CARD_CONTROLS_V1


def is_canonical_card_code_v1(card: object) -> bool:
    return type(card) is str and card in get_full_deck()


def find_card_zone_conflicts_v1(
    zones: tuple[CardZoneSelectionV1, ...],
) -> tuple[CardZoneConflictV1, ...]:
    """Finds duplicate selections within and across mutually exclusive zones."""

    if type(zones) is not tuple or any(type(zone) is not CardZoneSelectionV1 for zone in zones):
        raise ValueError("Card zones must be an exact tuple of CardZoneSelectionV1 values.")
    occurrences: dict[str, list[str]] = {}
    for zone in zones:
        for card in zone.cards:
            occurrences.setdefault(card, []).append(zone.field)
    deck_order = {card: index for index, card in enumerate(get_full_deck())}
    duplicate_cards = sorted(
        (card for card, fields in occurrences.items() if len(fields) > 1),
        key=lambda card: (deck_order.get(card, len(deck_order)), card),
    )
    return tuple(
        CardZoneConflictV1(card=card, fields=tuple(dict.fromkeys(occurrences[card])))
        for card in duplicate_cards
    )
