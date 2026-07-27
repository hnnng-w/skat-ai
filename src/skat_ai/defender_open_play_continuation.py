from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.declarer_concession import (
    LIST_WORKFLOW_FIELDS,
    build_player_card_count_evidence,
    is_strict_integer,
    require_exact_keys,
)
from skat_ai.defender_open_play import DEFENDER_OPEN_PLAY_KIND
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_value import build_game_value_summary
from skat_ai.public_hand_constraint import (
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PUBLIC_HAND_VISIBILITY_SCOPE,
    PublicHandConstraint,
    canonicalize_cards,
)
from skat_ai.turn_phase import CONCRETE_PLAYERS, normalize_turn_phase_for_position

DEFENDER_OPEN_PLAY_CONTINUATION_KEYS = {
    "schema_version",
    "kind",
    "exposing_defender",
    "declarer_response",
    "public_exposing_defender_cards",
}
DECLARER_RESPONSE = "request_continued_play"


@dataclass(frozen=True)
class DefenderOpenPlayContinuation:
    schema_version: int
    kind: str
    exposing_defender: str
    declarer_response: str
    public_exposing_defender_cards: tuple[str, ...]


@dataclass(frozen=True)
class DefenderOpenPlayContinuationContext:
    continuation: DefenderOpenPlayContinuation
    declarer_player: str
    exposing_defender: str
    non_exposing_defender: str
    card_reconciliation: str
    public_hand_constraint: PublicHandConstraint


def build_defender_open_play_continuation(
    value: Any,
) -> DefenderOpenPlayContinuation:
    """Builds one strict version-1 defender-open-play continuation."""
    if not isinstance(value, dict):
        raise ValueError("game_continuation must be an object.")
    require_exact_keys(
        value,
        DEFENDER_OPEN_PLAY_CONTINUATION_KEYS,
        "game_continuation",
    )
    schema_version = value["schema_version"]
    if not is_strict_integer(schema_version) or schema_version != 1:
        raise ValueError("game_continuation.schema_version must be exactly 1.")
    if value["kind"] != DEFENDER_OPEN_PLAY_KIND:
        raise ValueError(
            "game_continuation.kind must be 'defender_open_play' for schema_version 1."
        )
    exposing_defender = value["exposing_defender"]
    if exposing_defender not in CONCRETE_PLAYERS:
        raise ValueError("game_continuation.exposing_defender must be 'me', 'left', or 'right'.")
    declarer_response = value["declarer_response"]
    if declarer_response == "accept_adjudication":
        raise ValueError(
            "Accepted defender-open-play adjudication must use "
            "game_shortening.kind='defender_open_play'."
        )
    if declarer_response != DECLARER_RESPONSE:
        raise ValueError("game_continuation.declarer_response must be 'request_continued_play'.")

    cards = value["public_exposing_defender_cards"]
    if not isinstance(cards, list):
        raise ValueError("game_continuation.public_exposing_defender_cards must be an array.")
    if not 1 <= len(cards) <= 10:
        raise ValueError(
            "game_continuation.public_exposing_defender_cards must contain between 1 and 10 cards."
        )
    full_deck = set(get_full_deck())
    invalid_cards = [card for card in cards if not isinstance(card, str) or card not in full_deck]
    if invalid_cards:
        raise ValueError(
            f"Invalid cards in game_continuation.public_exposing_defender_cards: {invalid_cards}"
        )
    duplicate_cards = sorted({card for card in cards if cards.count(card) > 1})
    if duplicate_cards:
        raise ValueError(
            "Duplicate cards in game_continuation.public_exposing_defender_cards: "
            f"{duplicate_cards}"
        )
    return DefenderOpenPlayContinuation(
        schema_version=schema_version,
        kind=value["kind"],
        exposing_defender=exposing_defender,
        declarer_response=declarer_response,
        public_exposing_defender_cards=tuple(cards),
    )


def validate_defender_open_play_continuation(
    position: dict[str, Any],
    continuation: DefenderOpenPlayContinuation,
) -> None:
    """Validates workflow, parties, turn phase, and ongoing-game exclusivity."""
    if position.get("analysis_mode", "live_decision") not in {
        "live_decision",
        "post_game_review",
    }:
        raise ValueError(
            "game_continuation supports only flat live_decision or "
            "post_game_review position analysis."
        )
    declarer_player = position.get("declarer_player", "unknown")
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError("Defender-open-play continuation requires a concrete declarer_player.")
    if continuation.exposing_defender == declarer_player:
        raise ValueError(
            "game_continuation.exposing_defender must be a member of the defending party."
        )
    if "game_shortening" in position:
        raise ValueError("game_continuation cannot be combined with game_shortening.")
    if position.get("game_end_reason", "not_ended") != "not_ended":
        raise ValueError(
            "game_continuation requires an ongoing game with game_end_reason='not_ended'."
        )
    if "impossible_null_settlement" in position:
        raise ValueError("game_continuation cannot be combined with impossible_null_settlement.")
    conflicting_list_fields = sorted(LIST_WORKFLOW_FIELDS.intersection(position))
    if conflicting_list_fields:
        raise ValueError(
            "game_continuation is not supported for list-performance workflows: "
            f"{conflicting_list_fields}."
        )
    completed_tricks = position.get("completed_tricks", [])
    if len(completed_tricks) >= 10:
        raise ValueError("game_continuation cannot be used after all ten tricks are complete.")
    current_trick = position.get("current_trick", [])
    phase = normalize_turn_phase_for_position(
        position.get("trick_leader", "unknown"),
        position.get("next_player", "unknown"),
        current_trick,
        completed_tricks,
    )
    if phase.trick_leader not in CONCRETE_PLAYERS or phase.next_player not in CONCRETE_PLAYERS:
        raise ValueError("Defender-open-play continuation requires a concrete current turn phase.")
    declaration = build_game_declaration_from_input(position)
    if build_game_value_summary(declaration)["game_value"] is None:
        raise ValueError(
            "game_continuation requires enough final declaration information to "
            "calculate the game value."
        )


def _reconcile_public_exposing_defender_cards(
    position: dict[str, Any],
    continuation: DefenderOpenPlayContinuation,
) -> str:
    public_cards = set(continuation.public_exposing_defender_cards)
    unavailable_by_card: dict[str, str] = {}
    for field_name in ("current_trick", "played_cards", "skat"):
        cards = position.get(field_name, [])
        if isinstance(cards, list):
            unavailable_by_card.update((card, field_name) for card in cards)
    for trick in position.get("completed_tricks", []):
        if isinstance(trick, dict) and isinstance(trick.get("cards"), list):
            unavailable_by_card.update((card, "completed_tricks") for card in trick["cards"])
    if continuation.exposing_defender != "me" and isinstance(position.get("hand"), list):
        unavailable_by_card.update((card, "local_hand") for card in position["hand"])
    contradictions = sorted(public_cards.intersection(unavailable_by_card))
    if contradictions:
        card = contradictions[0]
        raise ValueError(
            f"Public exposing-defender card {card} contradicts reliable "
            f"{unavailable_by_card[card]} evidence."
        )

    count_evidence = build_player_card_count_evidence(
        position,
        continuation.exposing_defender,
    )
    if (
        count_evidence is not None
        and len(continuation.public_exposing_defender_cards) != count_evidence.hand_cards_remaining
    ):
        raise ValueError(
            "game_continuation.public_exposing_defender_cards contradict reliable "
            f"{count_evidence.source} evidence: expected "
            f"{count_evidence.hand_cards_remaining} cards, got "
            f"{len(continuation.public_exposing_defender_cards)}."
        )
    if continuation.exposing_defender != "me":
        return "not_verifiable"
    if public_cards != set(position.get("hand", [])):
        raise ValueError(
            "game_continuation.public_exposing_defender_cards must exactly match "
            "the reliable local hand."
        )
    return "confirmed"


def resolve_defender_open_play_continuation(
    position: dict[str, Any],
    continuation: DefenderOpenPlayContinuation,
) -> DefenderOpenPlayContinuationContext:
    """Resolves the returned but permanently public exposing-defender hand."""
    validate_defender_open_play_continuation(position, continuation)
    declarer_player = position["declarer_player"]
    non_exposing_defender = next(
        player
        for player in CONCRETE_PLAYERS
        if player not in {declarer_player, continuation.exposing_defender}
    )
    cards = canonicalize_cards(continuation.public_exposing_defender_cards)
    return DefenderOpenPlayContinuationContext(
        continuation=continuation,
        declarer_player=declarer_player,
        exposing_defender=continuation.exposing_defender,
        non_exposing_defender=non_exposing_defender,
        card_reconciliation=_reconcile_public_exposing_defender_cards(
            position,
            continuation,
        ),
        public_hand_constraint=PublicHandConstraint(
            player=continuation.exposing_defender,
            cards=cards,
            source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
        ),
    )


def build_defender_open_play_continuation_summary(
    context: DefenderOpenPlayContinuationContext,
) -> dict[str, Any]:
    """Builds the stable non-adjudicating continued-play summary."""
    cards = list(context.public_hand_constraint.cards)
    return {
        "schema_version": context.continuation.schema_version,
        "kind": context.continuation.kind,
        "rule_sections": ["4.4.5", "4.1.6"],
        "declarer_player": context.declarer_player,
        "exposing_defender": context.exposing_defender,
        "non_exposing_defender": context.non_exposing_defender,
        "declarer_response": context.continuation.declarer_response,
        "cards_returned_to_hand": True,
        "hand_physically_open": False,
        "visibility_scope": PUBLIC_HAND_VISIBILITY_SCOPE,
        "public_exposing_defender_cards": cards,
        "public_exposing_defender_card_count": len(cards),
        "card_reconciliation": context.card_reconciliation,
        "rest_trick_claim": "all_remaining_tricks",
        "rest_trick_claim_status": "not_adjudicated_due_to_continued_play",
        "continued_play_effect": "open_play_consequence_disregarded",
        "continuation_required": True,
        "exact_proof_applied": False,
        "game_end_applied": False,
        "settlement_applied": False,
    }
