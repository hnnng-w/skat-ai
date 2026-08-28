from dataclasses import dataclass
from typing import Any

from skatmind.deck import get_full_deck
from skatmind.declarer_card_exposure import get_declared_mandatory_play_level
from skatmind.declarer_concession import (
    LIST_WORKFLOW_FIELDS,
    is_strict_integer,
    require_exact_keys,
)
from skatmind.exact_rest_trick_proof import (
    DefenderRestTrickProof,
    ExactRemainingPlayState,
    prove_defender_rest_tricks,
)
from skatmind.exact_search_state import ExactSearchState, build_exact_search_state
from skatmind.final_settlement import is_schneider_announced
from skatmind.game_decision import (
    determine_decision_state_before_game_end,
    get_mandatory_level_source,
    get_secured_achieved_schneider_status,
)
from skatmind.game_declaration import build_game_declaration_from_input
from skatmind.game_result import (
    get_card_point_winner,
    get_completed_trick_winner_roles,
    get_effective_schneider_status,
    get_effective_schwarz_status,
)
from skatmind.game_value import build_game_value_summary
from skatmind.overbid import build_overbid_summary, get_overbid_required_level
from skatmind.rules import get_trick_points
from skatmind.turn_phase import (
    CONCRETE_PLAYERS,
    derive_next_player,
    normalize_turn_phase_for_position,
)

DEFENDER_OPEN_PLAY_KIND = "defender_open_play"
DEFENDER_OPEN_PLAY_KEYS = {
    "schema_version",
    "kind",
    "exposing_defender",
    "remaining_hands",
    "declarer_response",
}
REMAINING_HAND_KEYS = set(CONCRETE_PLAYERS)


@dataclass(frozen=True)
class DefenderOpenPlay:
    schema_version: int
    kind: str
    exposing_defender: str
    remaining_hands: tuple[tuple[str, tuple[str, ...]], ...]
    declarer_response: str

    def get_remaining_hands(self) -> dict[str, tuple[str, ...]]:
        return dict(self.remaining_hands)


@dataclass(frozen=True)
class DefenderOpenPlayContext:
    declarer_player: str
    exposing_defender: str
    non_exposing_defender: str
    exact_state: ExactRemainingPlayState | ExactSearchState
    remaining_trick_count: int
    assigned_card_count: int
    inferred_out_of_play_cards: tuple[str, ...]


@dataclass(frozen=True)
class DefenderOpenPlayAdjudication:
    game_result_summary: dict[str, Any]
    game_shortening_summary: dict[str, Any]


def _build_remaining_hand(value: Any, player: str) -> tuple[str, ...]:
    field_name = f"game_shortening.remaining_hands.{player}"
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be an array.")
    full_deck = set(get_full_deck())
    invalid_cards = [card for card in value if not isinstance(card, str) or card not in full_deck]
    if invalid_cards:
        raise ValueError(f"Invalid cards in {field_name}: {invalid_cards}")
    duplicates = sorted({card for card in value if value.count(card) > 1})
    if duplicates:
        raise ValueError(f"Duplicate cards in {field_name}: {duplicates}")
    return tuple(value)


def build_defender_open_play(value: Any) -> DefenderOpenPlay:
    """Builds one strict version-1 defender open-play event."""
    if not isinstance(value, dict):
        raise ValueError("game_shortening must be an object.")
    require_exact_keys(value, DEFENDER_OPEN_PLAY_KEYS, "game_shortening")

    schema_version = value["schema_version"]
    if not is_strict_integer(schema_version) or schema_version != 1:
        raise ValueError("game_shortening.schema_version must be exactly 1.")
    if value["kind"] != DEFENDER_OPEN_PLAY_KIND:
        raise ValueError("game_shortening.kind must be 'defender_open_play' for schema_version 1.")
    exposing_defender = value["exposing_defender"]
    if exposing_defender not in CONCRETE_PLAYERS:
        raise ValueError("game_shortening.exposing_defender must be 'me', 'left', or 'right'.")
    if value["declarer_response"] == "request_continued_play":
        raise ValueError("Continued play must use game_continuation.kind='defender_open_play'.")
    if value["declarer_response"] != "accept_adjudication":
        raise ValueError("game_shortening.declarer_response must be 'accept_adjudication'.")

    remaining_hands = value["remaining_hands"]
    if not isinstance(remaining_hands, dict):
        raise ValueError("game_shortening.remaining_hands must be an object.")
    require_exact_keys(
        remaining_hands,
        REMAINING_HAND_KEYS,
        "game_shortening.remaining_hands",
    )
    hands = tuple(
        (player, _build_remaining_hand(remaining_hands[player], player))
        for player in CONCRETE_PLAYERS
    )
    all_cards = [card for _, hand in hands for card in hand]
    cross_duplicates = sorted({card for card in all_cards if all_cards.count(card) > 1})
    if cross_duplicates:
        raise ValueError(
            f"Duplicate cards across game_shortening.remaining_hands: {cross_duplicates}"
        )
    if not dict(hands)[exposing_defender]:
        raise ValueError("The exposing defender must have at least one remaining card.")

    return DefenderOpenPlay(
        schema_version=schema_version,
        kind=value["kind"],
        exposing_defender=exposing_defender,
        remaining_hands=hands,
        declarer_response=value["declarer_response"],
    )


def _completed_cards(data: dict[str, Any]) -> list[str]:
    return [card for trick in data.get("completed_tricks", []) for card in trick.get("cards", [])]


def validate_exact_remaining_play_state(
    data: dict[str, Any],
    open_play: DefenderOpenPlay,
) -> DefenderOpenPlayContext:
    """Validates and builds complete private late-game proof evidence."""
    declarer_player = data.get("declarer_player", "unknown")
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError("Defender open play requires a concrete declarer_player.")
    if open_play.exposing_defender == declarer_player:
        raise ValueError(
            "game_shortening.exposing_defender must be a member of the defending party."
        )
    non_exposing_defender = next(
        player
        for player in CONCRETE_PLAYERS
        if player not in {declarer_player, open_play.exposing_defender}
    )
    hands = open_play.get_remaining_hands()
    current_trick = data.get("current_trick", [])
    completed_tricks = data.get("completed_tricks", [])
    completed_cards = _completed_cards(data)

    phase = normalize_turn_phase_for_position(
        data.get("trick_leader", "unknown"),
        data.get("next_player", "unknown"),
        current_trick,
        completed_tricks,
    )
    if phase.trick_leader not in CONCRETE_PLAYERS or phase.next_player not in CONCRETE_PLAYERS:
        raise ValueError("Defender open play requires a concrete turn phase.")

    completed_count = len(completed_tricks)
    remaining_trick_count = 10 - completed_count
    if remaining_trick_count < 1:
        raise ValueError("At least one trick must remain unresolved for defender open play.")
    if remaining_trick_count > 5:
        raise ValueError("Defender open play supports at most five remaining tricks.")

    current_players = {
        derive_next_player(phase.trick_leader, index) for index in range(len(current_trick))
    }
    for player in CONCRETE_PLAYERS:
        expected_size = remaining_trick_count - (1 if player in current_players else 0)
        if len(hands[player]) != expected_size:
            raise ValueError(
                "game_shortening.remaining_hands hand-size progression is inconsistent: "
                f"expected {expected_size} cards for {player}, got {len(hands[player])}."
            )

    exact_cards = [
        *completed_cards,
        *current_trick,
        *(card for player in CONCRETE_PLAYERS for card in hands[player]),
    ]
    duplicates = sorted({card for card in exact_cards if exact_cards.count(card) > 1})
    if duplicates:
        raise ValueError(
            f"Exact remaining cards contradict played or current-trick evidence: {duplicates}"
        )
    if len(exact_cards) != 30:
        raise ValueError(
            "Defender open play requires exactly 30 accounted in-play cards; "
            f"got {len(exact_cards)}."
        )

    full_deck = get_full_deck()
    inferred_out_of_play = tuple(card for card in full_deck if card not in exact_cards)
    supplied_skat = data.get("skat", [])
    if supplied_skat and set(supplied_skat) != set(inferred_out_of_play):
        raise ValueError(
            "skat must match the two exact inferred out-of-play cards for defender open play."
        )
    local_hand = data.get("hand", [])
    if set(local_hand) != set(hands["me"]):
        raise ValueError("hand must exactly match game_shortening.remaining_hands.me.")
    if data.get("left_hand_size") != len(hands["left"]):
        raise ValueError("left_hand_size contradicts the exact remaining left hand.")
    if data.get("right_hand_size") != len(hands["right"]):
        raise ValueError("right_hand_size contradicts the exact remaining right hand.")
    played_cards = data.get("played_cards", [])
    if played_cards:
        raise ValueError(
            "Defender open play exact accounting requires played_cards to be empty; "
            "use completed_tricks for played-card evidence."
        )

    declarer_completed_tricks = sum(
        trick.get("winner_role") == "declarer" for trick in completed_tricks
    )
    defender_completed_tricks = completed_count - declarer_completed_tricks
    declarer_trick_points = sum(
        get_trick_points(trick["cards"])
        for trick in completed_tricks
        if trick.get("winner_role") == "declarer"
    )
    defender_trick_points = sum(
        get_trick_points(trick["cards"])
        for trick in completed_tricks
        if trick.get("winner_role") == "defenders"
    )
    exact_state = build_exact_search_state(
        declaration=build_game_declaration_from_input(data),
        declarer_player=declarer_player,
        remaining_hands=hands,
        current_trick=tuple(
            (derive_next_player(phase.trick_leader, index), card)
            for index, card in enumerate(current_trick)
        ),
        next_player=phase.next_player,
        declarer_trick_points=declarer_trick_points,
        defender_trick_points=defender_trick_points,
        declarer_completed_tricks=declarer_completed_tricks,
        defender_completed_tricks=defender_completed_tricks,
        out_of_play_cards=inferred_out_of_play,
    )
    return DefenderOpenPlayContext(
        declarer_player=declarer_player,
        exposing_defender=open_play.exposing_defender,
        non_exposing_defender=non_exposing_defender,
        exact_state=exact_state,
        remaining_trick_count=remaining_trick_count,
        assigned_card_count=sum(len(hand) for hand in hands.values()) + len(current_trick),
        inferred_out_of_play_cards=inferred_out_of_play,
    )


def validate_defender_open_play_context(
    data: dict[str, Any],
    open_play: DefenderOpenPlay,
) -> DefenderOpenPlayContext:
    """Validates workflow, exclusivity, exact evidence, and settlement support."""
    if data.get("analysis_mode", "live_decision") != "post_game_review":
        raise ValueError(
            "game_shortening defender open play requires analysis_mode='post_game_review'."
        )
    if data.get("game_end_reason", "not_ended") != "not_ended":
        raise ValueError(
            "game_shortening cannot be combined with an active legacy game_end_reason."
        )
    if "game_continuation" in data:
        raise ValueError("Defender open play cannot be combined with game_continuation.")
    if "impossible_null_settlement" in data:
        raise ValueError("game_shortening cannot be combined with impossible_null_settlement.")
    conflicting_list_fields = sorted(LIST_WORKFLOW_FIELDS.intersection(data))
    if conflicting_list_fields:
        raise ValueError(
            "game_shortening is not supported for list-performance workflows: "
            f"{conflicting_list_fields}."
        )

    declaration = build_game_declaration_from_input(data)
    game_value_summary = build_game_value_summary(declaration)
    if game_value_summary["game_value"] is None:
        raise ValueError(
            "game_shortening defender open play requires enough declaration "
            "information to calculate the game value."
        )
    overbid_summary = build_overbid_summary(game_value_summary, declaration.bid_value)
    if overbid_summary["is_overbid"] is True and overbid_summary["required_game_value"] is None:
        raise ValueError(
            "game_shortening defender open play requires a supported overbid-required game value."
        )
    get_overbid_required_level(game_value_summary, overbid_summary)
    return validate_exact_remaining_play_state(data, open_play)


def _serialize_proof_line(
    proof: DefenderRestTrickProof,
    exposing_defender: str,
) -> list[dict[str, Any]]:
    return [
        {
            "player": move.player,
            "card": move.card if move.player == exposing_defender else None,
            "card_visibility": (
                "exposed" if move.player == exposing_defender else "private_evidence_redacted"
            ),
            "trick_winner": move.trick_winner,
        }
        for move in proof.line
    ]


def adjudicate_defender_open_play(
    game_shortening: DefenderOpenPlay,
    context: DefenderOpenPlayContext,
    game_result_summary: dict[str, Any],
    game_value_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
    completed_tricks: list[dict[str, Any]],
) -> DefenderOpenPlayAdjudication:
    """Runs exact proof and adjudicates its valid or invalid rule consequence."""
    proof = prove_defender_rest_tricks(
        context.exact_state,
        context.exposing_defender,
        context.declarer_player,
    )
    decision_state = determine_decision_state_before_game_end(
        game_result_summary,
        game_value_summary,
        overbid_summary,
        completed_tricks,
    )
    is_preexisting = decision_state != "undecided"
    valid = proof.status == "valid"
    recipient = "defenders" if valid else "declarer"
    assigned_points = game_result_summary["points_remaining"]
    declarer_points = game_result_summary["declarer_points"]
    defender_points = game_result_summary["defender_points"]
    if recipient == "declarer":
        declarer_points += assigned_points
    else:
        defender_points += assigned_points

    if decision_state == "declarer_already_won":
        winner = "declarer"
        winner_basis = "preexisting_game_decision"
    elif decision_state == "defenders_already_won":
        winner = "defenders"
        winner_basis = "preexisting_game_decision"
    elif game_value_summary.get("is_null_game") is True:
        winner = "declarer"
        winner_basis = "valid_defender_open_play" if valid else "invalid_defender_open_play"
    elif valid:
        winner = get_card_point_winner(declarer_points, defender_points)
        winner_basis = "valid_defender_open_play"
    else:
        winner = "declarer"
        winner_basis = "invalid_defender_open_play"

    overbid_required_level = get_overbid_required_level(
        game_value_summary,
        overbid_summary,
    )
    mandatory_level_source = get_mandatory_level_source(
        game_value_summary,
        overbid_required_level,
    )
    mandatory_level_awarded = (
        not valid
        and decision_state == "undecided"
        and mandatory_level_source is not None
        and winner == "declarer"
    )
    achieved_schneider_status = None
    achieved_schwarz_status = None
    achieved_schneider_applied = False
    achieved_schwarz_applied = False
    if game_value_summary.get("is_null_game") is False:
        if valid:
            achieved_schneider_status = get_effective_schneider_status(
                declarer_points,
                defender_points,
            )
            completed_roles = get_completed_trick_winner_roles(completed_tricks)
            if "declarer" not in completed_roles:
                achieved_schwarz_status = "defenders_made_schwarz"
            else:
                achieved_schwarz_status = "none"
            achieved_schneider_applied = (
                achieved_schneider_status in {"declarer_made_schneider", "defenders_made_schneider"}
                and overbid_summary.get("is_overbid") is not True
                and not (
                    achieved_schneider_status == "defenders_made_schneider"
                    and is_schneider_announced(game_value_summary)
                )
            )
            achieved_schwarz_applied = (
                achieved_schwarz_status == "defenders_made_schwarz"
                and overbid_summary.get("is_overbid") is not True
            )
        elif is_preexisting:
            achieved_schneider_status = get_secured_achieved_schneider_status(
                decision_state,
                game_result_summary,
            )
            achieved_schneider_applied = (
                achieved_schneider_status is not None
                and overbid_summary.get("is_overbid") is not True
                and not (
                    achieved_schneider_status == "defenders_made_schneider"
                    and is_schneider_announced(game_value_summary)
                )
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
            "raw_schwarz_status": get_effective_schwarz_status(declarer_points, defender_points),
            "effective_schneider_status": achieved_schneider_status or "not_applicable",
            "effective_schwarz_status": achieved_schwarz_status or "not_applicable",
            "game_end_reason": DEFENDER_OPEN_PLAY_KIND,
            "game_end_kind": DEFENDER_OPEN_PLAY_KIND,
            "outcome_source": (
                "preexisting_game_decision" if is_preexisting else "exact_adjudication"
            ),
            "winner_basis": winner_basis,
            "decision_state_before_game_end": decision_state,
            "rest_trick_proof_status": proof.status,
            "rest_tricks_recipient": recipient,
            "mandatory_level_awarded": mandatory_level_awarded,
            "mandatory_level_source": (mandatory_level_source if mandatory_level_awarded else None),
            "mandatory_play_level": (
                max(
                    [
                        level
                        for level in [
                            get_declared_mandatory_play_level(game_value_summary),
                            overbid_required_level,
                        ]
                        if level is not None
                    ],
                    key={"schneider": 1, "schwarz": 2}.__getitem__,
                    default=None,
                )
                if mandatory_level_awarded
                else None
            ),
            "achieved_schneider_applied": achieved_schneider_applied,
            "achieved_schwarz_applied": achieved_schwarz_applied,
            "overbid_required_value_applied": overbid_summary.get("is_overbid") is True,
            "remaining_points_recipient": recipient,
            "remaining_points_assigned": assigned_points,
            "rest_trick_assignment": {
                "source": (
                    "defender_open_play_adjudication" if valid else "invalid_defender_open_play"
                ),
                "recipient": recipient,
                "remaining_trick_count": context.remaining_trick_count,
                "assigned_card_count": context.assigned_card_count,
                "assigned_card_points": assigned_points,
            },
        }
    )

    rule_sections = ["4.4.5"]
    if is_preexisting:
        rule_sections.append("4.1.3")
    elif not valid:
        rule_sections.append("4.1.4")
        if mandatory_level_awarded:
            rule_sections.append("4.1.5")

    exposed_cards = list(game_shortening.get_remaining_hands()[context.exposing_defender])
    canonical_order = {card: index for index, card in enumerate(get_full_deck())}
    exposed_cards.sort(key=canonical_order.__getitem__)
    line_key = "successful_line" if valid else "counterexample_line"
    summary = {
        "schema_version": game_shortening.schema_version,
        "kind": game_shortening.kind,
        "rule_sections": rule_sections,
        "exposing_defender": context.exposing_defender,
        "non_exposing_defender": context.non_exposing_defender,
        "defending_party": [
            player for player in CONCRETE_PLAYERS if player != context.declarer_player
        ],
        "exposed_cards": exposed_cards,
        "exposed_card_count": len(exposed_cards),
        "declarer_response": game_shortening.declarer_response,
        "decision_state_before_shortening": decision_state,
        "remaining_trick_count": context.remaining_trick_count,
        "exact_proof": {
            "status": proof.status,
            "proof_complete": proof.proof_complete,
            "quantifier_policy": {
                "exposing_defender": "exists_legal_strategy",
                "declarer": "all_legal_plays",
                "non_exposing_defender": "all_legal_plays",
            },
            "evaluated_state_count": proof.evaluated_state_count,
            "memoized_state_count": proof.memoized_state_count,
            "counterexample_found": proof.counterexample_found,
            line_key: _serialize_proof_line(proof, context.exposing_defender),
        },
        "rest_trick_assignment": adjusted_result["rest_trick_assignment"],
        "rest_tricks_recipient": recipient,
        "adjudicated_winner": winner,
        "winner_basis": winner_basis,
        "continued_play_requested": False,
    }
    return DefenderOpenPlayAdjudication(adjusted_result, summary)
