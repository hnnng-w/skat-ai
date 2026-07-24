from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.declarer_concession import (
    LIST_WORKFLOW_FIELDS,
    DeclarerCardCountEvidence,
    build_declarer_card_count_evidence,
    is_strict_integer,
    require_exact_keys,
)
from skat_ai.final_settlement import is_schneider_announced, is_schwarz_announced
from skat_ai.game_decision import (
    determine_decision_state_before_game_end,
    get_secured_achieved_schneider_status,
)
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_value import build_game_value_summary
from skat_ai.overbid import build_overbid_summary, get_overbid_required_level
from skat_ai.turn_phase import CONCRETE_PLAYERS

DECLARER_CARD_EXPOSURE_KIND = "declarer_card_exposure"
VALID_EXPOSURE_FORMS = {"laid_open", "shown_to_defender"}
VALID_CLAIMED_PLAY_LEVELS = {"simple", "schneider", "schwarz"}
VALID_ACCEPTANCE_FORMS = {"explicit", "unambiguous_conduct"}
GAME_SHORTENING_KEYS = {
    "schema_version",
    "kind",
    "exposure",
    "claimed_play_level",
    "defender_responses",
}
DEFENDER_RESPONSE_KEYS = {"player", "response", "form"}


@dataclass(frozen=True)
class DeclarerCardExposureDetails:
    form: str
    exposed_cards: tuple[str, ...]
    shown_to_player: str | None = None


@dataclass(frozen=True)
class DefenderExposureResponse:
    player: str
    response: str
    form: str


@dataclass(frozen=True)
class DeclarerCardExposure:
    schema_version: int
    kind: str
    exposure: DeclarerCardExposureDetails
    claimed_play_level: str
    defender_responses: tuple[DefenderExposureResponse, ...]


@dataclass(frozen=True)
class DeclarerExposedCardEvidence:
    declarer_player: str
    exact_declarer_cards: tuple[str, ...] | None
    declarer_card_count: DeclarerCardCountEvidence | None
    unavailable_cards: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DeclarerCardExposureAdjudication:
    game_result_summary: dict[str, Any]
    game_shortening_summary: dict[str, Any]


def build_exposure_details(value: Any) -> DeclarerCardExposureDetails:
    """Builds the strict exposure-form member of a card-exposure event."""
    if not isinstance(value, dict):
        raise ValueError("game_shortening.exposure must be an object.")

    form = value.get("form")
    if form not in VALID_EXPOSURE_FORMS:
        raise ValueError(
            "game_shortening.exposure.form must be 'laid_open' or "
            "'shown_to_defender'."
        )
    required_keys = {"form", "exposed_cards"}
    if form == "shown_to_defender":
        required_keys.add("shown_to_player")
    require_exact_keys(value, required_keys, "game_shortening.exposure")

    shown_to_player = value.get("shown_to_player")
    if form == "shown_to_defender" and shown_to_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "game_shortening.exposure.shown_to_player must be 'me', 'left', or "
            "'right'."
        )

    exposed_cards = value["exposed_cards"]
    if not isinstance(exposed_cards, list):
        raise ValueError("game_shortening.exposure.exposed_cards must be an array.")
    if not 1 <= len(exposed_cards) <= 10:
        raise ValueError(
            "game_shortening.exposure.exposed_cards must contain between 1 and 10 cards."
        )
    full_deck = set(get_full_deck())
    invalid_cards = [
        card
        for card in exposed_cards
        if not isinstance(card, str) or card not in full_deck
    ]
    if invalid_cards:
        raise ValueError(
            "Invalid cards in game_shortening.exposure.exposed_cards: "
            f"{invalid_cards}"
        )
    duplicate_cards = sorted({
        card for card in exposed_cards if exposed_cards.count(card) > 1
    })
    if duplicate_cards:
        raise ValueError(
            "Duplicate cards in game_shortening.exposure.exposed_cards: "
            f"{duplicate_cards}"
        )

    return DeclarerCardExposureDetails(
        form=form,
        exposed_cards=tuple(exposed_cards),
        shown_to_player=shown_to_player,
    )


def build_defender_response(value: Any, index: int) -> DefenderExposureResponse:
    """Builds one externally classified defender acceptance."""
    field_name = f"game_shortening.defender_responses[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    require_exact_keys(value, DEFENDER_RESPONSE_KEYS, field_name)

    player = value["player"]
    if player not in CONCRETE_PLAYERS:
        raise ValueError(f"{field_name}.player must be 'me', 'left', or 'right'.")
    response = value["response"]
    if response != "accept":
        raise ValueError(
            "Both defenders must accept declarer card exposure; exposed-card "
            "continuation after an objection is not supported by Issue #88."
        )
    acceptance_form = value["form"]
    if acceptance_form not in VALID_ACCEPTANCE_FORMS:
        raise ValueError(
            f"{field_name}.form must be 'explicit' or 'unambiguous_conduct'."
        )
    return DefenderExposureResponse(player, response, acceptance_form)


def build_declarer_card_exposure(value: Any) -> DeclarerCardExposure:
    """Builds and structurally validates one version-1 exposure event."""
    if not isinstance(value, dict):
        raise ValueError("game_shortening must be an object.")
    require_exact_keys(value, GAME_SHORTENING_KEYS, "game_shortening")

    schema_version = value["schema_version"]
    if not is_strict_integer(schema_version) or schema_version != 1:
        raise ValueError("game_shortening.schema_version must be exactly 1.")
    kind = value["kind"]
    if kind != DECLARER_CARD_EXPOSURE_KIND:
        raise ValueError(
            "game_shortening.kind must be 'declarer_card_exposure' for "
            "schema_version 1."
        )
    claimed_play_level = value["claimed_play_level"]
    if claimed_play_level not in VALID_CLAIMED_PLAY_LEVELS:
        raise ValueError(
            "game_shortening.claimed_play_level must be 'simple', 'schneider', "
            "or 'schwarz'."
        )

    response_values = value["defender_responses"]
    if not isinstance(response_values, list):
        raise ValueError("game_shortening.defender_responses must be an array.")
    if len(response_values) != 2:
        raise ValueError(
            "game_shortening.defender_responses must contain exactly two "
            "defender acceptances."
        )
    responses = tuple(
        build_defender_response(response, index)
        for index, response in enumerate(response_values)
    )
    response_players = [response.player for response in responses]
    if len(set(response_players)) != 2:
        raise ValueError(
            "game_shortening.defender_responses must identify each defender "
            "exactly once."
        )

    return DeclarerCardExposure(
        schema_version=schema_version,
        kind=kind,
        exposure=build_exposure_details(value["exposure"]),
        claimed_play_level=claimed_play_level,
        defender_responses=responses,
    )


def get_declarer_card_exposure_from_input(
    data: dict[str, Any],
) -> DeclarerCardExposure | None:
    """Returns the optional declarer-card-exposure union member."""
    value = data.get("game_shortening")
    if value is None:
        return None
    if isinstance(value, dict) and value.get("kind") != DECLARER_CARD_EXPOSURE_KIND:
        return None
    return build_declarer_card_exposure(value)


def build_declarer_exposed_card_evidence(
    data: dict[str, Any],
) -> DeclarerExposedCardEvidence:
    """Builds ownership-aware evidence without exposing hidden cards in output."""
    declarer_player = data.get("declarer_player", "unknown")
    hand = data.get("hand", [])
    exact_declarer_cards = (
        tuple(hand)
        if declarer_player == "me" and isinstance(hand, list)
        else None
    )
    unavailable_cards: list[tuple[str, str]] = []

    for field_name in ("current_trick", "played_cards", "skat"):
        cards = data.get(field_name, [])
        if isinstance(cards, list):
            unavailable_cards.extend((card, field_name) for card in cards)
    for trick in data.get("completed_tricks", []):
        if isinstance(trick, dict) and isinstance(trick.get("cards"), list):
            unavailable_cards.extend(
                (card, "completed_tricks") for card in trick["cards"]
            )
    if declarer_player != "me" and isinstance(hand, list):
        unavailable_cards.extend((card, "defender_hand") for card in hand)

    return DeclarerExposedCardEvidence(
        declarer_player=declarer_player,
        exact_declarer_cards=exact_declarer_cards,
        declarer_card_count=build_declarer_card_count_evidence(data),
        unavailable_cards=tuple(unavailable_cards),
    )


def validate_exposure_parties(
    exposure: DeclarerCardExposure,
    declarer_player: str,
) -> None:
    """Requires the shown player and responses to identify concrete defenders."""
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "game_shortening declarer card exposure requires a concrete "
            "declarer_player."
        )
    defenders = [player for player in CONCRETE_PLAYERS if player != declarer_player]
    responders = [response.player for response in exposure.defender_responses]
    if declarer_player in responders:
        raise ValueError(
            "game_shortening.defender_responses cannot include the declarer."
        )
    if set(responders) != set(defenders):
        raise ValueError(
            "game_shortening.defender_responses must identify exactly the two "
            "concrete defenders."
        )
    shown_to_player = exposure.exposure.shown_to_player
    if shown_to_player is not None and shown_to_player not in defenders:
        raise ValueError(
            "game_shortening.exposure.shown_to_player must be a concrete defender, "
            "not the declarer."
        )


def reconcile_exposed_cards(
    exposure: DeclarerCardExposure,
    evidence: DeclarerExposedCardEvidence | None,
) -> str:
    """Confirms the complete remaining hand or reports bounded unverifiability."""
    if evidence is None:
        return "not_verifiable"

    exposed_cards = set(exposure.exposure.exposed_cards)
    unavailable_by_card = dict(evidence.unavailable_cards)
    contradictions = sorted(exposed_cards.intersection(unavailable_by_card))
    if contradictions:
        card = contradictions[0]
        raise ValueError(
            f"Exposed declarer card {card} contradicts reliable "
            f"{unavailable_by_card[card]} evidence."
        )

    count_evidence = evidence.declarer_card_count
    if (
        count_evidence is not None
        and len(exposure.exposure.exposed_cards)
        != count_evidence.hand_cards_remaining
    ):
        raise ValueError(
            "game_shortening.exposure.exposed_cards contradict reliable "
            f"{count_evidence.source} evidence: expected "
            f"{count_evidence.hand_cards_remaining} cards, got "
            f"{len(exposure.exposure.exposed_cards)}."
        )

    if evidence.exact_declarer_cards is None:
        return "not_verifiable"
    if exposed_cards != set(evidence.exact_declarer_cards):
        raise ValueError(
            "game_shortening.exposure.exposed_cards must exactly match the "
            "reliable remaining declarer hand."
        )
    return "confirmed"


def validate_declarer_card_exposure_context(
    data: dict[str, Any],
    exposure: DeclarerCardExposure,
) -> None:
    """Validates workflow, parties, reconciliation, and settlement prerequisites."""
    if data.get("analysis_mode", "live_decision") != "post_game_review":
        raise ValueError(
            "game_shortening declarer card exposure requires "
            "analysis_mode='post_game_review'."
        )
    validate_exposure_parties(exposure, data.get("declarer_player", "unknown"))

    game_end_reason = data.get("game_end_reason", "not_ended")
    if game_end_reason != "not_ended":
        raise ValueError(
            "game_shortening cannot be combined with an active legacy "
            f"game_end_reason: {game_end_reason}."
        )
    if "impossible_null_settlement" in data:
        raise ValueError(
            "game_shortening cannot be combined with impossible_null_settlement."
        )
    conflicting_list_fields = sorted(LIST_WORKFLOW_FIELDS.intersection(data))
    if conflicting_list_fields:
        raise ValueError(
            "game_shortening is not supported for list-performance workflows: "
            f"{conflicting_list_fields}."
        )
    if len(data.get("completed_tricks", [])) >= 10:
        raise ValueError(
            "Declarer card exposure cannot occur after all ten tricks are complete."
        )

    declaration = build_game_declaration_from_input(data)
    game_value_summary = build_game_value_summary(declaration)
    if game_value_summary["game_value"] is None:
        raise ValueError(
            "game_shortening declarer card exposure requires enough declaration "
            "information to calculate the game value."
        )
    if game_value_summary["is_null_game"] and exposure.claimed_play_level != "simple":
        raise ValueError("Null declarer card exposure requires claimed_play_level='simple'.")

    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=declaration.bid_value,
    )
    if (
        overbid_summary["is_overbid"] is True
        and overbid_summary["required_game_value"] is None
    ):
        raise ValueError(
            "game_shortening declarer card exposure requires a supported "
            "overbid-required game value."
        )
    get_overbid_required_level(game_value_summary, overbid_summary)
    evidence = build_declarer_exposed_card_evidence(data)
    reconcile_exposed_cards(exposure, evidence)


def get_play_level_rank(level: str | None) -> int:
    """Returns the bounded simple, Schneider, or Schwarz hierarchy rank."""
    return {None: 0, "simple": 0, "schneider": 1, "schwarz": 2}[level]


def get_declared_mandatory_play_level(
    game_value_summary: dict[str, Any],
) -> str | None:
    """Returns the highest play level made mandatory by the declaration."""
    if game_value_summary.get("is_null_game") is not False:
        return None
    if is_schwarz_announced(game_value_summary):
        return "schwarz"
    if is_schneider_announced(game_value_summary):
        return "schneider"
    return None


def adjudicate_accepted_declarer_card_exposure(
    game_shortening: DeclarerCardExposure,
    game_result_summary: dict[str, Any],
    game_value_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
    completed_tricks: list[dict[str, Any]],
    card_evidence: DeclarerExposedCardEvidence | None = None,
) -> DeclarerCardExposureAdjudication:
    """Adjudicates unanimously accepted exposure without future-play simulation."""
    if game_value_summary.get("game_value") is None:
        raise ValueError("Declarer card exposure requires a calculable game value.")
    if (
        overbid_summary.get("is_overbid") is True
        and overbid_summary.get("required_game_value") is None
    ):
        raise ValueError(
            "Declarer card exposure requires a supported overbid-required game value."
        )
    if game_value_summary.get("is_null_game") is True:
        if game_shortening.claimed_play_level != "simple":
            raise ValueError(
                "Null declarer card exposure requires claimed_play_level='simple'."
            )
    if card_evidence is not None:
        validate_exposure_parties(game_shortening, card_evidence.declarer_player)
    reconciliation = reconcile_exposed_cards(game_shortening, card_evidence)

    overbid_required_level = get_overbid_required_level(
        game_value_summary,
        overbid_summary,
    )
    decision_state = determine_decision_state_before_game_end(
        game_result_summary,
        game_value_summary,
        overbid_summary,
        completed_tricks,
    )
    is_preexisting_decision = decision_state != "undecided"
    declared_level = get_declared_mandatory_play_level(game_value_summary)
    declared_rank = get_play_level_rank(declared_level)
    claimed_rank = get_play_level_rank(game_shortening.claimed_play_level)
    required_rank = get_play_level_rank(overbid_required_level)
    accepted_level_rank = max(declared_rank, claimed_rank)
    overbid_requirement_covered = (
        overbid_required_level is None or accepted_level_rank >= required_rank
    )

    if decision_state == "defenders_already_won":
        winner = "defenders"
        winner_basis = "preexisting_game_decision"
    elif decision_state == "declarer_already_won":
        winner = "declarer"
        winner_basis = "preexisting_game_decision"
    elif not overbid_requirement_covered:
        winner = "defenders"
        winner_basis = "uncovered_overbid_requirement"
    else:
        winner = "declarer"
        winner_basis = "accepted_declarer_card_exposure"

    outcome_source = (
        "preexisting_game_decision" if is_preexisting_decision else "adjudicated"
    )
    apply_adjudicated_levels = not is_preexisting_decision and winner == "declarer"
    declared_mandatory_schneider_applied = (
        apply_adjudicated_levels and declared_rank >= 1
    )
    declared_mandatory_schwarz_applied = (
        apply_adjudicated_levels and declared_rank >= 2
    )
    accepted_claimed_schneider_applied = (
        apply_adjudicated_levels and claimed_rank >= 1
    )
    accepted_claimed_schwarz_applied = (
        apply_adjudicated_levels and claimed_rank >= 2
    )

    achieved_schneider_status = None
    if is_preexisting_decision and game_value_summary.get("is_null_game") is False:
        achieved_schneider_status = get_secured_achieved_schneider_status(
            decision_state,
            game_result_summary,
        )
    achieved_schneider_applied = achieved_schneider_status is not None
    if (
        achieved_schneider_status == "defenders_made_schneider"
        and is_schneider_announced(game_value_summary)
    ):
        achieved_schneider_applied = False

    adjusted_result = game_result_summary.copy()
    adjusted_result.update(
        {
            "is_complete": True,
            "winner": winner,
            "status": (
                "final_decided" if is_preexisting_decision else "final_adjudicated"
            ),
            "effective_schneider_status": (
                achieved_schneider_status or "not_applicable"
            ),
            "effective_schwarz_status": "not_applicable",
            "game_end_reason": DECLARER_CARD_EXPOSURE_KIND,
            "game_end_kind": DECLARER_CARD_EXPOSURE_KIND,
            "outcome_source": outcome_source,
            "winner_basis": winner_basis,
            "decision_state_before_game_end": decision_state,
            "claimed_play_level": game_shortening.claimed_play_level,
            "declared_mandatory_schneider_applied": (
                declared_mandatory_schneider_applied
            ),
            "declared_mandatory_schwarz_applied": declared_mandatory_schwarz_applied,
            "accepted_claimed_schneider_applied": (
                accepted_claimed_schneider_applied
            ),
            "accepted_claimed_schwarz_applied": accepted_claimed_schwarz_applied,
            "achieved_schneider_applied": achieved_schneider_applied,
            "achieved_schwarz_applied": False,
            "overbid_required_value_applied": (
                overbid_summary.get("is_overbid") is True
            ),
            "overbid_requirement_covered": overbid_requirement_covered,
            "settlement_play_level_count": (
                accepted_level_rank if apply_adjudicated_levels else 0
            ),
            "remaining_points_recipient": None,
            "remaining_points_assigned": 0,
        }
    )

    canonical_order = {card: index for index, card in enumerate(get_full_deck())}
    exposed_cards = sorted(
        game_shortening.exposure.exposed_cards,
        key=canonical_order.__getitem__,
    )
    responses_by_player = {
        response.player: response for response in game_shortening.defender_responses
    }
    accepting_defenders = [
        player for player in CONCRETE_PLAYERS if player in responses_by_player
    ]
    summary = {
        "schema_version": game_shortening.schema_version,
        "kind": game_shortening.kind,
        "rule_sections": ["4.4.4"],
        "exposure_form": game_shortening.exposure.form,
        "shown_to_player": game_shortening.exposure.shown_to_player,
        "exposed_cards": exposed_cards,
        "exposed_card_count": len(exposed_cards),
        "card_reconciliation": reconciliation,
        "unanimous_defender_acceptance": True,
        "accepting_defenders": accepting_defenders,
        "acceptance_forms": {
            player: responses_by_player[player].form for player in accepting_defenders
        },
        "claimed_play_level": game_shortening.claimed_play_level,
        "decision_state_before_shortening": decision_state,
        "adjudicated_winner": winner,
        "winner_basis": winner_basis,
        "continued_play_required": False,
        "remaining_points_assigned": False,
        "settlement_level_policy": (
            "secured_observed_levels_only"
            if is_preexisting_decision
            else "declared_and_unanimously_accepted_claimed_levels"
        ),
    }
    return DeclarerCardExposureAdjudication(adjusted_result, summary)
