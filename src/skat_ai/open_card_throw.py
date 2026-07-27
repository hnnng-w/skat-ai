from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.declarer_card_exposure import (
    get_declared_mandatory_play_level,
    get_play_level_rank,
)
from skat_ai.declarer_concession import (
    LIST_WORKFLOW_FIELDS,
    build_player_card_count_evidence,
    is_strict_integer,
    require_exact_keys,
)
from skat_ai.game_decision import (
    determine_decision_state_before_game_end,
    get_mandatory_level_source,
)
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_result import (
    get_card_point_winner,
    get_effective_schneider_status,
    get_effective_schwarz_status,
)
from skat_ai.game_value import build_game_value_summary
from skat_ai.overbid import build_overbid_summary, get_overbid_required_level
from skat_ai.rules import get_legal_cards
from skat_ai.side_ownership import get_player_side
from skat_ai.theoretical_level_exclusion import (
    JackOwnershipEvidence,
    assess_theoretical_schwarz_exclusion,
    build_reliable_jack_ownership_evidence,
    build_serializable_theoretical_schwarz_assessment,
)
from skat_ai.turn_phase import (
    CONCRETE_PLAYERS,
    derive_next_player,
    normalize_turn_phase_for_position,
)

OPEN_CARD_THROW_KIND = "open_card_throw"
OPEN_CARD_THROW_KEYS = {
    "schema_version",
    "kind",
    "throwing_player",
    "thrown_cards",
    "statement_classification",
}
VALID_STATEMENT_CLASSIFICATIONS = {
    "none",
    "generic_concession",
    "attempted_level_limitation",
}
SPECIFIC_TRICK_ASSERTION_KEYS = {
    "specific_future_trick_assertion",
    "future_trick_assertion",
    "claimed_future_tricks",
}
PRIOR_RESULT_FIELDS = {
    "adjusted_game_result_summary",
    "final_settlement_summary",
    "game_result_summary",
    "normal_completion",
}


@dataclass(frozen=True)
class OpenCardThrow:
    schema_version: int
    kind: str
    throwing_player: str
    thrown_cards: tuple[str, ...]
    statement_classification: str


@dataclass(frozen=True)
class OpenCardThrowContext:
    declarer_player: str
    throwing_party: str
    opposing_party: str
    joint_liability: bool
    card_reconciliation: str
    remaining_trick_count: int
    assigned_card_count: int
    observed_trick_counts: tuple[tuple[str, int], ...]
    rule_assigned_trick_counts: tuple[tuple[str, int], ...]
    final_trick_counts: tuple[tuple[str, int], ...]
    jack_ownership_evidence: tuple[JackOwnershipEvidence, ...]


@dataclass(frozen=True)
class OpenCardThrowAdjudication:
    game_result_summary: dict[str, Any]
    game_shortening_summary: dict[str, Any]


def build_open_card_throw(value: Any) -> OpenCardThrow:
    """Builds one strict version-1 open-card-throw event."""
    if not isinstance(value, dict):
        raise ValueError("game_shortening must be an object.")
    if SPECIFIC_TRICK_ASSERTION_KEYS.intersection(value):
        raise ValueError(
            "A specific future-trick assertion requires a separate classified "
            "trick-claim workflow and is not an open-card-throw level limitation."
        )
    require_exact_keys(value, OPEN_CARD_THROW_KEYS, "game_shortening")

    schema_version = value["schema_version"]
    if not is_strict_integer(schema_version) or schema_version != 1:
        raise ValueError("game_shortening.schema_version must be exactly 1.")
    if value["kind"] != OPEN_CARD_THROW_KIND:
        raise ValueError(
            "game_shortening.kind must be 'open_card_throw' for schema_version 1."
        )
    throwing_player = value["throwing_player"]
    if throwing_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "game_shortening.throwing_player must be 'me', 'left', or 'right'."
        )

    thrown_cards = value["thrown_cards"]
    if not isinstance(thrown_cards, list):
        raise ValueError("game_shortening.thrown_cards must be an array.")
    if not 1 <= len(thrown_cards) <= 10:
        raise ValueError(
            "game_shortening.thrown_cards must contain between 1 and 10 cards."
        )
    full_deck = set(get_full_deck())
    invalid_cards = [
        card for card in thrown_cards if not isinstance(card, str) or card not in full_deck
    ]
    if invalid_cards:
        raise ValueError(f"Invalid cards in game_shortening.thrown_cards: {invalid_cards}")
    duplicates = sorted({card for card in thrown_cards if thrown_cards.count(card) > 1})
    if duplicates:
        raise ValueError(f"Duplicate cards in game_shortening.thrown_cards: {duplicates}")

    statement_classification = value["statement_classification"]
    if statement_classification not in VALID_STATEMENT_CLASSIFICATIONS:
        raise ValueError(
            "game_shortening.statement_classification must be 'none', "
            "'generic_concession', or 'attempted_level_limitation'."
        )
    return OpenCardThrow(
        schema_version=schema_version,
        kind=value["kind"],
        throwing_player=throwing_player,
        thrown_cards=tuple(thrown_cards),
        statement_classification=statement_classification,
    )


def _get_current_trick_players(data: dict[str, Any]) -> tuple[str, ...]:
    current_trick = data.get("current_trick", [])
    if not current_trick:
        return ()
    phase = normalize_turn_phase_for_position(
        data.get("trick_leader", "unknown"),
        data.get("next_player", "unknown"),
        current_trick,
        data.get("completed_tricks", []),
    )
    if phase.trick_leader not in CONCRETE_PLAYERS:
        raise ValueError("Open card throw requires a concrete current-trick turn phase.")
    return tuple(
        derive_next_player(phase.trick_leader, index)
        for index in range(len(current_trick))
    )


def _validate_thrown_cards(
    data: dict[str, Any],
    game_shortening: OpenCardThrow,
) -> str:
    thrown = set(game_shortening.thrown_cards)
    unavailable: dict[str, str] = {}
    for field_name in ("current_trick", "played_cards", "skat"):
        for card in data.get(field_name, []):
            unavailable[card] = field_name
    for trick in data.get("completed_tricks", []):
        for card in trick.get("cards", []):
            unavailable[card] = "completed_tricks"
    if game_shortening.throwing_player != "me":
        for card in data.get("hand", []):
            unavailable[card] = "another player's local hand"
    contradictions = sorted(thrown.intersection(unavailable))
    if contradictions:
        card = contradictions[0]
        raise ValueError(
            f"Thrown card {card} contradicts reliable {unavailable[card]} evidence."
        )

    count_evidence = build_player_card_count_evidence(
        data,
        game_shortening.throwing_player,
    )
    if count_evidence is not None and len(thrown) != count_evidence.hand_cards_remaining:
        raise ValueError(
            "game_shortening.thrown_cards contradict reliable "
            f"{count_evidence.source} evidence: expected "
            f"{count_evidence.hand_cards_remaining} cards, got {len(thrown)}."
        )

    if game_shortening.throwing_player != "me":
        return "not_verifiable"
    if thrown != set(data.get("hand", [])):
        raise ValueError(
            "game_shortening.thrown_cards must exactly match the local throwing "
            "player's complete current hand."
        )
    return "confirmed"


def _validate_hand_size_progression(data: dict[str, Any]) -> tuple[int, int]:
    completed_count = len(data.get("completed_tricks", []))
    remaining_trick_count = 10 - completed_count
    if remaining_trick_count < 1:
        raise ValueError("At least one trick must remain unresolved for open card throw.")

    current_players = set(_get_current_trick_players(data))
    actual_sizes = {
        "me": len(data.get("hand", [])),
        "left": data.get("left_hand_size"),
        "right": data.get("right_hand_size"),
    }
    for player in CONCRETE_PLAYERS:
        expected = remaining_trick_count - int(player in current_players)
        if actual_sizes[player] != expected:
            raise ValueError(
                "Open-card-throw hand-size progression is inconsistent: "
                f"expected {expected} cards for {player}, got {actual_sizes[player]}."
            )

    assigned_card_count = remaining_trick_count * 3
    if sum(actual_sizes.values()) + len(data.get("current_trick", [])) != assigned_card_count:
        raise ValueError("Open-card-throw unresolved card accounting is inconsistent.")
    return remaining_trick_count, assigned_card_count


def _validate_supported_current_trick_plays(
    data: dict[str, Any],
    game_shortening: OpenCardThrow,
) -> None:
    current_trick = data.get("current_trick", [])
    players = _get_current_trick_players(data)
    prior_cards: list[str] = []
    for card, player in zip(current_trick, players, strict=True):
        current_hand: tuple[str, ...] | list[str] | None = None
        if player == game_shortening.throwing_player:
            current_hand = game_shortening.thrown_cards
        elif player == "me":
            current_hand = data.get("hand", [])
        if current_hand is not None:
            hand_before_play = [*current_hand, card]
            if card not in get_legal_cards(hand_before_play, prior_cards, data["game_type"]):
                raise ValueError(
                    f"current_trick card {card} was not a legal follow-suit play for {player}."
                )
        prior_cards.append(card)


def resolve_open_card_throw_context(
    data: dict[str, Any],
    game_shortening: OpenCardThrow,
) -> OpenCardThrowContext:
    """Validates the flat adjudication context and derives party-level facts."""
    if data.get("analysis_mode", "live_decision") != "post_game_review":
        raise ValueError(
            "game_shortening open card throw requires analysis_mode='post_game_review'."
        )
    declarer_player = data.get("declarer_player", "unknown")
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError("Open card throw requires a concrete declarer_player.")
    if data.get("game_end_reason", "not_ended") != "not_ended":
        raise ValueError(
            "game_shortening cannot be combined with an active legacy game_end_reason."
        )
    if "game_continuation" in data:
        raise ValueError("Open card throw cannot be combined with game_continuation.")
    if "impossible_null_settlement" in data:
        raise ValueError("game_shortening cannot be combined with impossible_null_settlement.")
    conflicts = sorted(LIST_WORKFLOW_FIELDS.intersection(data))
    if conflicts:
        raise ValueError(
            "game_shortening is not supported for list-performance workflows: "
            f"{conflicts}."
        )
    prior_result_fields = sorted(PRIOR_RESULT_FIELDS.intersection(data))
    if prior_result_fields:
        raise ValueError(
            "Open card throw cannot follow an existing adjudicated or completed result: "
            f"{prior_result_fields}."
        )

    declaration = build_game_declaration_from_input(data)
    game_value_summary = build_game_value_summary(declaration)
    if game_value_summary["game_value"] is None:
        raise ValueError(
            "game_shortening open card throw requires enough declaration "
            "information to calculate the game value."
        )
    overbid_summary = build_overbid_summary(game_value_summary, declaration.bid_value)
    if overbid_summary["is_overbid"] is True and overbid_summary["required_game_value"] is None:
        raise ValueError(
            "game_shortening open card throw requires a supported "
            "overbid-required game value."
        )
    get_overbid_required_level(game_value_summary, overbid_summary)

    throwing_party = get_player_side(game_shortening.throwing_player, declarer_player)
    if throwing_party is None:
        raise ValueError("Open card throw requires deterministic party derivation.")
    opposing_party = "defenders" if throwing_party == "declarer" else "declarer"
    reconciliation = _validate_thrown_cards(data, game_shortening)
    remaining_trick_count, assigned_card_count = _validate_hand_size_progression(data)
    _validate_supported_current_trick_plays(data, game_shortening)

    observed = {"declarer": 0, "defenders": 0}
    for trick in data.get("completed_tricks", []):
        observed[trick["winner_role"]] += 1
    assigned = {"declarer": 0, "defenders": 0}
    assigned[opposing_party] = remaining_trick_count
    final = {party: observed[party] + assigned[party] for party in observed}
    if sum(final.values()) != 10:
        raise ValueError("Completed and rule-assigned trick counts must total ten.")

    return OpenCardThrowContext(
        declarer_player=declarer_player,
        throwing_party=throwing_party,
        opposing_party=opposing_party,
        joint_liability=throwing_party == "defenders",
        card_reconciliation=reconciliation,
        remaining_trick_count=remaining_trick_count,
        assigned_card_count=assigned_card_count,
        observed_trick_counts=tuple(observed.items()),
        rule_assigned_trick_counts=tuple(assigned.items()),
        final_trick_counts=tuple(final.items()),
        jack_ownership_evidence=build_reliable_jack_ownership_evidence(
            data,
            game_shortening.throwing_player,
            game_shortening.thrown_cards,
        ),
    )


def validate_open_card_throw(
    data: dict[str, Any],
    game_shortening: OpenCardThrow,
) -> OpenCardThrowContext:
    """Validates and returns the resolved open-card-throw context."""
    return resolve_open_card_throw_context(data, game_shortening)


def _highest_required_level(
    game_value_summary: dict[str, Any],
    overbid_required_level: str | None,
) -> str | None:
    levels = [
        level
        for level in [
            get_declared_mandatory_play_level(game_value_summary),
            overbid_required_level,
        ]
        if level is not None
    ]
    return max(levels, key=get_play_level_rank, default=None)


def adjudicate_open_card_throw(
    game_shortening: OpenCardThrow,
    context: OpenCardThrowContext,
    game_result_summary: dict[str, Any],
    game_value_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
    completed_tricks: list[dict[str, Any]],
) -> OpenCardThrowAdjudication:
    """Assigns every unresolved trick and point without simulating future play."""
    assigned_points = game_result_summary["points_remaining"]
    declarer_points = game_result_summary["declarer_points"]
    defender_points = game_result_summary["defender_points"]
    if context.opposing_party == "declarer":
        declarer_points += assigned_points
    else:
        defender_points += assigned_points
    if declarer_points + defender_points != 120:
        raise ValueError("Open-card-throw final Suit/Grand points must total 120.")

    observed_tricks = dict(context.observed_trick_counts)
    assigned_tricks = dict(context.rule_assigned_trick_counts)
    final_tricks = dict(context.final_trick_counts)
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
    is_preexisting = decision_state != "undecided"
    is_null = game_value_summary.get("is_null_game") is True

    if decision_state == "declarer_already_won":
        candidate_winner = "declarer"
    elif decision_state == "defenders_already_won":
        candidate_winner = "defenders"
    elif is_null:
        candidate_winner = (
            "declarer" if final_tricks["declarer"] == 0 else "defenders"
        )
    else:
        candidate_winner = get_card_point_winner(declarer_points, defender_points)
        if candidate_winner == "undecided":
            raise ValueError("Open-card-throw final point assignment must decide the game.")

    candidate_losing_party = (
        "defenders" if candidate_winner == "declarer" else "declarer"
    )
    theoretical_assessment = assess_theoretical_schwarz_exclusion(
        candidate_losing_party,
        context.jack_ownership_evidence,
    )
    candidate_losing_points = (
        defender_points if candidate_losing_party == "defenders" else declarer_points
    )
    candidate_schneider = not is_null and candidate_losing_points <= 30
    candidate_schwarz = (
        not is_null
        and final_tricks[candidate_losing_party] == 0
        and theoretical_assessment.status == "not_excluded"
    )
    candidate_level_rank = 2 if candidate_schwarz else int(candidate_schneider)

    declared_level = get_declared_mandatory_play_level(game_value_summary)
    mandatory_level = _highest_required_level(
        game_value_summary,
        overbid_required_level,
    )
    mandatory_source = get_mandatory_level_source(
        game_value_summary,
        overbid_required_level,
    )
    mandatory_level_covered = (
        mandatory_level is None
        or candidate_winner == "declarer"
        and candidate_level_rank >= get_play_level_rank(mandatory_level)
    )

    winner = candidate_winner
    if not is_preexisting and candidate_winner == "declarer" and not mandatory_level_covered:
        winner = "defenders"
        if (
            mandatory_level == "schwarz"
            and final_tricks["defenders"] == 0
            and theoretical_assessment.status == "excluded"
        ):
            winner_basis = "theoretically_excluded_required_schwarz"
        elif overbid_required_level is not None:
            winner_basis = "uncovered_overbid_requirement"
        else:
            winner_basis = "failed_mandatory_level"
    elif is_preexisting:
        winner_basis = "preexisting_game_decision"
    else:
        winner_basis = "open_card_throw_rule_state"

    losing_party = "defenders" if winner == "declarer" else "declarer"
    losing_points = defender_points if losing_party == "defenders" else declarer_points
    open_throw_schneider_applied = not is_null and losing_points <= 30
    open_throw_schwarz_applied = (
        not is_null
        and winner == candidate_winner
        and final_tricks[losing_party] == 0
        and theoretical_assessment.status == "not_excluded"
    )
    effective_schneider_status = "not_applicable"
    effective_schwarz_status = "not_applicable"
    if not is_null:
        if open_throw_schneider_applied:
            effective_schneider_status = (
                "declarer_made_schneider"
                if winner == "declarer"
                else "defenders_made_schneider"
            )
        else:
            effective_schneider_status = "none"
        if open_throw_schwarz_applied:
            effective_schwarz_status = (
                "declarer_made_schwarz"
                if winner == "declarer"
                else "defenders_made_schwarz"
            )
        else:
            effective_schwarz_status = "none"

    observed_points = {
        "declarer": game_result_summary["declarer_points"],
        "defenders": game_result_summary["defender_points"],
    }
    assigned_points_by_party = {"declarer": 0, "defenders": 0}
    assigned_points_by_party[context.opposing_party] = assigned_points
    final_points = {"declarer": declarer_points, "defenders": defender_points}
    rest_assignment = {
        "source": OPEN_CARD_THROW_KIND,
        "recipient": context.opposing_party,
        "remaining_trick_count": context.remaining_trick_count,
        "assigned_card_count": context.assigned_card_count,
        "assigned_card_points": assigned_points,
    }
    theoretical_output = build_serializable_theoretical_schwarz_assessment(
        theoretical_assessment
    )
    adjusted_result = game_result_summary.copy()
    adjusted_result.update(
        {
            "declarer_points": declarer_points,
            "defender_points": defender_points,
            "points_remaining": 0,
            "is_complete": True,
            "winner": winner,
            "status": "final_decided" if is_preexisting else "final_adjudicated",
            "raw_schneider_status": get_effective_schneider_status(
                declarer_points, defender_points
            ),
            "raw_schwarz_status": get_effective_schwarz_status(
                declarer_points, defender_points
            ),
            "effective_schneider_status": effective_schneider_status,
            "effective_schwarz_status": effective_schwarz_status,
            "game_end_reason": OPEN_CARD_THROW_KIND,
            "game_end_kind": OPEN_CARD_THROW_KIND,
            "outcome_source": (
                "preexisting_game_decision" if is_preexisting else "rule_adjudication"
            ),
            "winner_basis": winner_basis,
            "decision_state_before_game_end": decision_state,
            "rest_tricks_recipient": context.opposing_party,
            "remaining_points_recipient": context.opposing_party,
            "remaining_points_assigned": assigned_points,
            "rest_trick_assignment": rest_assignment,
            "observed_trick_counts": observed_tricks,
            "rule_assigned_trick_counts": assigned_tricks,
            "final_trick_counts": final_tricks,
            "observed_points": observed_points,
            "rule_assigned_points": assigned_points_by_party,
            "final_points": final_points,
            "schneider_level_source": (
                "open_card_throw_final_point_state"
                if not is_null
                else "not_applicable"
            ),
            "schwarz_level_source": (
                "open_card_throw_rule_state" if not is_null else "not_applicable"
            ),
            "theoretical_schwarz_assessment": theoretical_output,
            "theoretical_schwarz_status": theoretical_assessment.status,
            "declared_mandatory_play_level": declared_level,
            "mandatory_play_level": mandatory_level,
            "mandatory_level_source": mandatory_source,
            "mandatory_level_covered": mandatory_level_covered,
            "declared_mandatory_schneider_applied": (
                winner == "declarer"
                and get_play_level_rank(declared_level) >= 1
                and candidate_level_rank >= 1
            ),
            "declared_mandatory_schwarz_applied": (
                winner == "declarer"
                and get_play_level_rank(declared_level) >= 2
                and candidate_level_rank >= 2
            ),
            "achieved_schneider_applied": False,
            "achieved_schwarz_applied": False,
            "open_throw_schneider_applied": open_throw_schneider_applied,
            "open_throw_schwarz_applied": open_throw_schwarz_applied,
            "overbid_required_level": overbid_required_level,
            "overbid_requirement_covered": (
                overbid_required_level is None
                or winner == "declarer"
                and candidate_level_rank >= get_play_level_rank(overbid_required_level)
            ),
            "overbid_required_value_applied": overbid_summary.get("is_overbid") is True,
            "normally_played_declarer_trick_count": observed_tricks["declarer"],
            "rule_assigned_declarer_trick_count": assigned_tricks["declarer"],
        }
    )

    canonical_order = {card: index for index, card in enumerate(get_full_deck())}
    thrown_cards = sorted(game_shortening.thrown_cards, key=canonical_order.__getitem__)
    summary = {
        "schema_version": game_shortening.schema_version,
        "kind": game_shortening.kind,
        "rule_sections": ["4.4.6"],
        "throwing_player": game_shortening.throwing_player,
        "throwing_party": context.throwing_party,
        "opposing_party": context.opposing_party,
        "joint_liability": context.joint_liability,
        "thrown_cards": thrown_cards,
        "thrown_card_count": len(thrown_cards),
        "card_reconciliation": context.card_reconciliation,
        "statement_classification": game_shortening.statement_classification,
        "decision_state_before_shortening": decision_state,
        "rest_trick_assignment": rest_assignment,
        "rest_tricks_recipient": context.opposing_party,
        "remaining_trick_count": context.remaining_trick_count,
        "observed_trick_counts": observed_tricks,
        "rule_assigned_trick_counts": assigned_tricks,
        "final_trick_counts": final_tricks,
        "observed_points": observed_points,
        "rule_assigned_points": assigned_points_by_party,
        "final_points": final_points,
        "adjudicated_winner": winner,
        "winner_basis": winner_basis,
        "schneider_rule_level_applied": open_throw_schneider_applied,
        "schwarz_rule_level_applied": open_throw_schwarz_applied,
        "theoretical_schwarz_status": theoretical_assessment.status,
        "theoretical_schwarz_assessment": theoretical_output,
        "continued_play_supported": False,
    }
    return OpenCardThrowAdjudication(adjusted_result, summary)


def build_open_card_throw_summary(
    adjudication: OpenCardThrowAdjudication,
) -> dict[str, Any]:
    """Returns a detached summary dictionary for typed API callers."""
    return adjudication.game_shortening_summary.copy()
