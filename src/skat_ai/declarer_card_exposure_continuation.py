from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.declarer_card_exposure import (
    DECLARER_CARD_EXPOSURE_KIND,
    VALID_ACCEPTANCE_FORMS,
    VALID_CLAIMED_PLAY_LEVELS,
    VALID_EXPOSURE_FORMS,
    DefenderExposureResponse,
)
from skat_ai.declarer_concession import (
    LIST_WORKFLOW_FIELDS,
    build_declarer_card_count_evidence,
    is_strict_integer,
    require_exact_keys,
)
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_value import build_game_value_summary
from skat_ai.public_hand_constraint import (
    PUBLIC_HAND_VISIBILITY_SCOPE,
    PublicHandConstraint,
    canonicalize_cards,
)
from skat_ai.turn_phase import CONCRETE_PLAYERS

GAME_CONTINUATION_KEYS = {
    "schema_version",
    "kind",
    "exposure",
    "claimed_play_level",
    "defender_responses",
    "public_declarer_cards",
}
EXPOSURE_KEYS = {"form"}
DEFENDER_RESPONSE_KEYS = {"player", "response", "form"}
VALID_RESPONSES = {"accept", "continue"}
CLAIMED_PLAY_LEVEL_STATUS = "continuation_required_no_immediate_settlement_effect"


@dataclass(frozen=True)
class ContinuationExposureDetails:
    form: str
    shown_to_player: str | None = None


@dataclass(frozen=True)
class DeclarerCardExposureContinuation:
    schema_version: int
    kind: str
    exposure: ContinuationExposureDetails
    claimed_play_level: str
    defender_responses: tuple[DefenderExposureResponse, ...]
    public_declarer_cards: tuple[str, ...]


@dataclass(frozen=True)
class DeclarerCardExposureContinuationContext:
    continuation: DeclarerCardExposureContinuation
    declarer_player: str
    card_reconciliation: str
    public_hand_constraint: PublicHandConstraint


def build_continuation_exposure_details(value: Any) -> ContinuationExposureDetails:
    """Builds the strict exposure-form provenance object."""
    if not isinstance(value, dict):
        raise ValueError("game_continuation.exposure must be an object.")
    form = value.get("form")
    if form not in VALID_EXPOSURE_FORMS:
        raise ValueError(
            "game_continuation.exposure.form must be 'laid_open' or 'shown_to_defender'."
        )
    required_keys = EXPOSURE_KEYS.copy()
    if form == "shown_to_defender":
        required_keys.add("shown_to_player")
    require_exact_keys(value, required_keys, "game_continuation.exposure")
    shown_to_player = value.get("shown_to_player")
    if form == "shown_to_defender" and shown_to_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "game_continuation.exposure.shown_to_player must be 'me', 'left', or 'right'."
        )
    return ContinuationExposureDetails(form, shown_to_player)


def build_continuation_defender_response(
    value: Any,
    index: int,
) -> DefenderExposureResponse:
    """Builds one externally classified defender response."""
    field_name = f"game_continuation.defender_responses[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    require_exact_keys(value, DEFENDER_RESPONSE_KEYS, field_name)
    player = value["player"]
    if player not in CONCRETE_PLAYERS:
        raise ValueError(f"{field_name}.player must be 'me', 'left', or 'right'.")
    response = value["response"]
    if response not in VALID_RESPONSES:
        raise ValueError(f"{field_name}.response must be 'accept' or 'continue'.")
    response_form = value["form"]
    if response_form not in VALID_ACCEPTANCE_FORMS:
        raise ValueError(f"{field_name}.form must be 'explicit' or 'unambiguous_conduct'.")
    return DefenderExposureResponse(player, response, response_form)


def build_declarer_card_exposure_continuation(
    value: Any,
) -> DeclarerCardExposureContinuation:
    """Builds one strict version-1 ongoing continuation event."""
    if not isinstance(value, dict):
        raise ValueError("game_continuation must be an object.")
    require_exact_keys(value, GAME_CONTINUATION_KEYS, "game_continuation")
    schema_version = value["schema_version"]
    if not is_strict_integer(schema_version) or schema_version != 1:
        raise ValueError("game_continuation.schema_version must be exactly 1.")
    if value["kind"] != DECLARER_CARD_EXPOSURE_KIND:
        raise ValueError(
            "game_continuation.kind must be 'declarer_card_exposure' for schema_version 1."
        )
    claimed_play_level = value["claimed_play_level"]
    if claimed_play_level not in VALID_CLAIMED_PLAY_LEVELS:
        raise ValueError(
            "game_continuation.claimed_play_level must be 'simple', 'schneider', or 'schwarz'."
        )
    response_values = value["defender_responses"]
    if not isinstance(response_values, list) or len(response_values) != 2:
        raise ValueError(
            "game_continuation.defender_responses must contain exactly two defender responses."
        )
    responses = tuple(
        build_continuation_defender_response(response, index)
        for index, response in enumerate(response_values)
    )
    if len({response.player for response in responses}) != 2:
        raise ValueError(
            "game_continuation.defender_responses must identify each defender exactly once."
        )
    if all(response.response == "accept" for response in responses):
        raise ValueError(
            "Unanimous defender acceptance must use game_shortening.kind='declarer_card_exposure'."
        )
    cards = value["public_declarer_cards"]
    if not isinstance(cards, list):
        raise ValueError("game_continuation.public_declarer_cards must be an array.")
    if not 1 <= len(cards) <= 10:
        raise ValueError(
            "game_continuation.public_declarer_cards must contain between 1 and 10 cards."
        )
    full_deck = set(get_full_deck())
    invalid_cards = [card for card in cards if not isinstance(card, str) or card not in full_deck]
    if invalid_cards:
        raise ValueError(
            f"Invalid cards in game_continuation.public_declarer_cards: {invalid_cards}"
        )
    duplicate_cards = sorted({card for card in cards if cards.count(card) > 1})
    if duplicate_cards:
        raise ValueError(
            f"Duplicate cards in game_continuation.public_declarer_cards: {duplicate_cards}"
        )
    return DeclarerCardExposureContinuation(
        schema_version=schema_version,
        kind=value["kind"],
        exposure=build_continuation_exposure_details(value["exposure"]),
        claimed_play_level=claimed_play_level,
        defender_responses=responses,
        public_declarer_cards=tuple(cards),
    )


def get_game_continuation_from_input(
    data: dict[str, Any],
) -> Any:
    """Compatibility wrapper for the versioned continuation union parser."""
    from skat_ai.game_continuation import get_game_continuation_from_input as get_union

    return get_union(data)


def validate_continuation_parties(
    continuation: DeclarerCardExposureContinuation,
    declarer_player: str,
) -> None:
    """Requires both concrete defenders and a defender-only shown player."""
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "game_continuation declarer card exposure requires a concrete declarer_player."
        )
    defenders = [player for player in CONCRETE_PLAYERS if player != declarer_player]
    responders = [response.player for response in continuation.defender_responses]
    if declarer_player in responders:
        raise ValueError("game_continuation.defender_responses cannot include the declarer.")
    if set(responders) != set(defenders):
        raise ValueError(
            "game_continuation.defender_responses must identify exactly the two concrete defenders."
        )
    shown_to_player = continuation.exposure.shown_to_player
    if shown_to_player is not None and shown_to_player not in defenders:
        raise ValueError(
            "game_continuation.exposure.shown_to_player must be a concrete defender, "
            "not the declarer."
        )


def reconcile_public_declarer_cards(
    data: dict[str, Any],
    continuation: DeclarerCardExposureContinuation,
) -> str:
    """Rejects reliable contradictions and reports exact independent confirmation."""
    public_cards = set(continuation.public_declarer_cards)
    unavailable_by_card: dict[str, str] = {}
    for field_name in ("current_trick", "played_cards", "skat"):
        cards = data.get(field_name, [])
        if isinstance(cards, list):
            unavailable_by_card.update((card, field_name) for card in cards)
    for trick in data.get("completed_tricks", []):
        if isinstance(trick, dict) and isinstance(trick.get("cards"), list):
            unavailable_by_card.update((card, "completed_tricks") for card in trick["cards"])
    if data.get("declarer_player") != "me" and isinstance(data.get("hand"), list):
        unavailable_by_card.update((card, "defender_hand") for card in data["hand"])
    contradictions = sorted(public_cards.intersection(unavailable_by_card))
    if contradictions:
        card = contradictions[0]
        raise ValueError(
            f"Public declarer card {card} contradicts reliable "
            f"{unavailable_by_card[card]} evidence."
        )
    count_evidence = build_declarer_card_count_evidence(data)
    if (
        count_evidence is not None
        and len(continuation.public_declarer_cards) != count_evidence.hand_cards_remaining
    ):
        raise ValueError(
            "game_continuation.public_declarer_cards contradict reliable "
            f"{count_evidence.source} evidence: expected "
            f"{count_evidence.hand_cards_remaining} cards, got "
            f"{len(continuation.public_declarer_cards)}."
        )
    if data.get("declarer_player") != "me":
        return "not_verifiable"
    if public_cards != set(data.get("hand", [])):
        raise ValueError(
            "game_continuation.public_declarer_cards must exactly match the "
            "reliable remaining declarer hand."
        )
    return "confirmed"


def resolve_declarer_card_exposure_continuation(
    position: dict[str, Any],
    continuation: DeclarerCardExposureContinuation,
) -> DeclarerCardExposureContinuationContext:
    """Validates and resolves one ongoing exposed-declarer-hand state."""
    if position.get("analysis_mode", "live_decision") not in {
        "live_decision",
        "post_game_review",
    }:
        raise ValueError(
            "game_continuation supports only flat live_decision or "
            "post_game_review position analysis."
        )
    declarer_player = position.get("declarer_player", "unknown")
    validate_continuation_parties(continuation, declarer_player)
    if "game_shortening" in position:
        raise ValueError("game_continuation cannot be combined with game_shortening.")
    game_end_reason = position.get("game_end_reason", "not_ended")
    if game_end_reason != "not_ended":
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
    if len(position.get("completed_tricks", [])) >= 10:
        raise ValueError("game_continuation cannot be used after all ten tricks are complete.")
    declaration = build_game_declaration_from_input(position)
    game_value_summary = build_game_value_summary(declaration)
    if game_value_summary["game_value"] is None:
        raise ValueError(
            "game_continuation requires enough final declaration information to "
            "calculate the game value."
        )
    if game_value_summary["is_null_game"] and continuation.claimed_play_level != "simple":
        raise ValueError(
            "Null declarer card exposure continuation requires claimed_play_level='simple'."
        )
    reconciliation = reconcile_public_declarer_cards(position, continuation)
    return DeclarerCardExposureContinuationContext(
        continuation=continuation,
        declarer_player=declarer_player,
        card_reconciliation=reconciliation,
        public_hand_constraint=PublicHandConstraint(
            player=declarer_player,
            cards=canonicalize_cards(continuation.public_declarer_cards),
        ),
    )


def build_game_continuation_summary(
    context: DeclarerCardExposureContinuationContext,
) -> dict[str, Any]:
    """Builds the stable non-settling continuation summary."""
    continuation = context.continuation
    responses_by_player = {
        response.player: response for response in continuation.defender_responses
    }
    ordered_players = [player for player in CONCRETE_PLAYERS if player in responses_by_player]
    responses = [
        {
            "player": player,
            "response": responses_by_player[player].response,
            "form": responses_by_player[player].form,
        }
        for player in ordered_players
    ]
    continuing = [
        response["player"] for response in responses if response["response"] == "continue"
    ]
    accepting = [response["player"] for response in responses if response["response"] == "accept"]
    cards = list(canonicalize_cards(continuation.public_declarer_cards))
    return {
        "schema_version": continuation.schema_version,
        "kind": continuation.kind,
        "rule_sections": ["4.4.4"],
        "declarer_player": context.declarer_player,
        "exposure_form": continuation.exposure.form,
        "shown_to_player": continuation.exposure.shown_to_player,
        "defender_responses": responses,
        "continuing_defenders": continuing,
        "accepting_defenders": accepting,
        "unanimous_acceptance": False,
        "continuation_required": True,
        "public_declarer_cards": cards,
        "public_declarer_card_count": len(cards),
        "card_reconciliation": context.card_reconciliation,
        "visibility_scope": PUBLIC_HAND_VISIBILITY_SCOPE,
        "claimed_play_level": continuation.claimed_play_level,
        "claimed_play_level_status": CLAIMED_PLAY_LEVEL_STATUS,
        "game_end_applied": False,
        "settlement_applied": False,
    }
