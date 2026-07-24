from dataclasses import dataclass
from typing import Any

from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_value import build_game_value_summary
from skat_ai.overbid import build_overbid_summary
from skat_ai.rules import get_card_points
from skat_ai.turn_phase import CONCRETE_PLAYERS, normalize_turn_phase_for_position

GAME_SHORTENING_SCHEMA_VERSION = 1
DECLARER_CONCESSION_KIND = "declarer_concession"
VALID_CONSENT_STATUSES = {"not_required", "granted"}
GAME_SHORTENING_KEYS = {
    "schema_version",
    "kind",
    "declarer_hand_cards_remaining",
    "defender_consent",
}
DEFENDER_CONSENT_KEYS = {"status", "consenting_defender_count"}
LIST_WORKFLOW_FIELDS = {
    "list_performance_input",
    "list_game_contributions",
    "list_analysis_results",
    "list_standings_input",
}


@dataclass(frozen=True)
class DefenderConsent:
    status: str
    consenting_defender_count: int


@dataclass(frozen=True)
class DeclarerConcession:
    schema_version: int
    kind: str
    declarer_hand_cards_remaining: int
    defender_consent: DefenderConsent


@dataclass(frozen=True)
class DeclarerCardCountEvidence:
    hand_cards_remaining: int
    source: str


@dataclass(frozen=True)
class DeclarerConcessionAdjudication:
    game_result_summary: dict[str, Any]
    game_shortening_summary: dict[str, Any]


def is_strict_integer(value: Any) -> bool:
    """Returns whether a value is an integer but not a boolean."""
    return isinstance(value, int) and not isinstance(value, bool)


def require_exact_keys(
    data: dict[str, Any],
    required_keys: set[str],
    field_name: str,
) -> None:
    """Requires an object to contain exactly the public contract keys."""
    missing_keys = sorted(required_keys - set(data))
    if missing_keys:
        raise ValueError(f"{field_name} is missing required keys: {missing_keys}")

    unsupported_keys = sorted(set(data) - required_keys)
    if unsupported_keys:
        raise ValueError(f"{field_name} has unsupported keys: {unsupported_keys}")


def build_declarer_concession(value: Any) -> DeclarerConcession:
    """Builds and validates one version-1 declarer concession."""
    if not isinstance(value, dict):
        raise ValueError("game_shortening must be an object.")

    require_exact_keys(value, GAME_SHORTENING_KEYS, "game_shortening")

    schema_version = value["schema_version"]
    if not is_strict_integer(schema_version) or schema_version != 1:
        raise ValueError("game_shortening.schema_version must be exactly 1.")

    kind = value["kind"]
    if kind != DECLARER_CONCESSION_KIND:
        raise ValueError(
            "game_shortening.kind must be 'declarer_concession' for schema_version 1."
        )

    hand_cards_remaining = value["declarer_hand_cards_remaining"]
    if not is_strict_integer(hand_cards_remaining):
        raise ValueError(
            "game_shortening.declarer_hand_cards_remaining must be an integer."
        )
    if not 1 <= hand_cards_remaining <= 10:
        raise ValueError(
            "game_shortening.declarer_hand_cards_remaining must be between 1 and 10."
        )

    consent_value = value["defender_consent"]
    if not isinstance(consent_value, dict):
        raise ValueError("game_shortening.defender_consent must be an object.")
    require_exact_keys(
        consent_value,
        DEFENDER_CONSENT_KEYS,
        "game_shortening.defender_consent",
    )

    consent_status = consent_value["status"]
    if consent_status not in VALID_CONSENT_STATUSES:
        raise ValueError(
            "game_shortening.defender_consent.status must be 'not_required' or "
            "'granted'."
        )

    consenting_defender_count = consent_value["consenting_defender_count"]
    if not is_strict_integer(consenting_defender_count):
        raise ValueError(
            "game_shortening.defender_consent.consenting_defender_count must be "
            "an integer."
        )
    if not 0 <= consenting_defender_count <= 2:
        raise ValueError(
            "game_shortening.defender_consent.consenting_defender_count must be "
            "between 0 and 2."
        )

    if hand_cards_remaining >= 9:
        if consent_status != "not_required" or consenting_defender_count != 0:
            raise ValueError(
                "A declarer concession with 9 or 10 hand cards requires "
                "defender_consent.status='not_required' and "
                "consenting_defender_count=0."
            )
    elif consent_status != "granted" or consenting_defender_count not in {1, 2}:
        raise ValueError(
            "A declarer concession with 1 to 8 hand cards requires "
            "defender_consent.status='granted' and one or two consenting defenders."
        )

    return DeclarerConcession(
        schema_version=schema_version,
        kind=kind,
        declarer_hand_cards_remaining=hand_cards_remaining,
        defender_consent=DefenderConsent(
            status=consent_status,
            consenting_defender_count=consenting_defender_count,
        ),
    )


def get_declarer_concession_from_input(
    data: dict[str, Any],
) -> DeclarerConcession | None:
    """Returns the optional structured declarer concession."""
    if "game_shortening" not in data:
        return None

    value = data["game_shortening"]
    if isinstance(value, dict) and value.get("kind") != DECLARER_CONCESSION_KIND:
        return None

    return build_declarer_concession(value)


def build_declarer_card_count_evidence(
    data: dict[str, Any],
) -> DeclarerCardCountEvidence | None:
    """Builds reliable current-hand evidence for a concrete declarer."""
    declarer_player = data.get("declarer_player", "unknown")
    direct_evidence = None

    if declarer_player == "me":
        hand = data.get("hand")
        if isinstance(hand, list):
            direct_evidence = DeclarerCardCountEvidence(
                hand_cards_remaining=len(hand),
                source="declarer_hand",
            )

    if declarer_player == "left":
        left_hand_size = data.get("left_hand_size")
        if is_strict_integer(left_hand_size):
            direct_evidence = DeclarerCardCountEvidence(
                hand_cards_remaining=left_hand_size,
                source="left_hand_size",
            )

    if declarer_player == "right":
        right_hand_size = data.get("right_hand_size")
        if is_strict_integer(right_hand_size):
            direct_evidence = DeclarerCardCountEvidence(
                hand_cards_remaining=right_hand_size,
                source="right_hand_size",
            )

    history_evidence = build_play_history_card_count_evidence(data)
    if direct_evidence is None:
        return history_evidence
    if history_evidence is None:
        return direct_evidence
    if direct_evidence.hand_cards_remaining != history_evidence.hand_cards_remaining:
        raise ValueError(
            "Reliable declarer current-hand evidence contradicts play history: "
            f"{direct_evidence.hand_cards_remaining} versus "
            f"{history_evidence.hand_cards_remaining}."
        )

    return DeclarerCardCountEvidence(
        hand_cards_remaining=direct_evidence.hand_cards_remaining,
        source=f"{direct_evidence.source}_and_play_history",
    )


def build_play_history_card_count_evidence(
    data: dict[str, Any],
) -> DeclarerCardCountEvidence | None:
    """Derives the declarer's physical hand count from reliable play timing."""
    completed_trick_count = len(data.get("completed_tricks", []))
    current_trick = data.get("current_trick", [])
    if not isinstance(current_trick, list):
        return None

    base_count = 10 - completed_trick_count
    if not current_trick:
        return DeclarerCardCountEvidence(base_count, "play_history")

    declarer_player = data.get("declarer_player", "unknown")
    if declarer_player not in CONCRETE_PLAYERS:
        return None

    phase = normalize_turn_phase_for_position(
        trick_leader=data.get("trick_leader", "unknown"),
        next_player=data.get("next_player", "unknown"),
        current_trick=current_trick,
        completed_tricks=data.get("completed_tricks", []),
    )
    if phase.trick_leader not in CONCRETE_PLAYERS:
        return None

    leader_index = CONCRETE_PLAYERS.index(phase.trick_leader)
    players_who_played = {
        CONCRETE_PLAYERS[(leader_index + offset) % len(CONCRETE_PLAYERS)]
        for offset in range(len(current_trick))
    }
    declarer_already_played = declarer_player in players_who_played

    return DeclarerCardCountEvidence(
        hand_cards_remaining=base_count - int(declarer_already_played),
        source="play_history",
    )


def reconcile_declarer_hand_card_count(
    concession: DeclarerConcession,
    evidence: DeclarerCardCountEvidence | None,
) -> str:
    """Confirms the supplied count or reports that it cannot be verified."""
    if evidence is None:
        return "not_verifiable"

    if evidence.hand_cards_remaining != concession.declarer_hand_cards_remaining:
        raise ValueError(
            "game_shortening.declarer_hand_cards_remaining contradicts reliable "
            f"{evidence.source} evidence: expected {evidence.hand_cards_remaining}, "
            f"got {concession.declarer_hand_cards_remaining}."
        )

    return "confirmed"


def get_known_assigned_card_points(data: dict[str, Any]) -> int:
    """Returns points already assigned by explicit totals and completed tricks."""
    completed_trick_points = sum(
        get_card_points(card)
        for trick in data.get("completed_tricks", [])
        for card in trick.get("cards", [])
    )
    return (
        data.get("declarer_points", 0)
        + data.get("defender_points", 0)
        + completed_trick_points
    )


def validate_declarer_concession_context(
    data: dict[str, Any],
    concession: DeclarerConcession,
) -> None:
    """Validates position-workflow and settlement prerequisites."""
    if data.get("analysis_mode", "live_decision") != "post_game_review":
        raise ValueError(
            "game_shortening declarer concession requires "
            "analysis_mode='post_game_review'."
        )

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
        raise ValueError("A declarer concession cannot occur after all tricks are played.")

    if get_known_assigned_card_points(data) >= 120:
        raise ValueError(
            "A declarer concession requires unplayed card points and cannot be "
            "combined with normal completion."
        )

    declaration = build_game_declaration_from_input(data)
    game_value_summary = build_game_value_summary(declaration)
    if game_value_summary["game_value"] is None:
        raise ValueError(
            "game_shortening declarer concession requires enough declaration "
            "information to calculate the game value."
        )

    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=declaration.bid_value,
    )
    if (
        overbid_summary["is_overbid"] is True
        and overbid_summary["required_game_value"] is None
    ):
        raise ValueError(
            "game_shortening declarer concession requires a supported "
            "overbid-required game value."
        )

    reconcile_declarer_hand_card_count(
        concession,
        build_declarer_card_count_evidence(data),
    )


def adjudicate_declarer_concession(
    game_shortening: DeclarerConcession,
    game_result_summary: dict[str, Any],
    game_value_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
    evidence: DeclarerCardCountEvidence | None = None,
) -> DeclarerConcessionAdjudication:
    """Adjudicates a valid concession without assigning unplayed points."""
    if game_result_summary.get("points_remaining", 0) <= 0:
        raise ValueError("A declarer concession requires unplayed card points.")

    if game_value_summary.get("game_value") is None:
        raise ValueError("A declarer concession requires a calculable game value.")

    if (
        overbid_summary.get("is_overbid") is True
        and overbid_summary.get("required_game_value") is None
    ):
        raise ValueError(
            "A declarer concession requires a supported overbid-required game value."
        )

    reconciliation = reconcile_declarer_hand_card_count(game_shortening, evidence)
    adjudicated_result = game_result_summary.copy()
    adjudicated_result.update(
        {
            "is_complete": True,
            "winner": "defenders",
            "status": "final_adjudicated",
            "effective_schneider_status": "not_applicable",
            "effective_schwarz_status": "not_applicable",
            "game_end_reason": DECLARER_CONCESSION_KIND,
            "game_end_kind": DECLARER_CONCESSION_KIND,
            "outcome_source": "adjudicated",
            "remaining_points_recipient": None,
            "remaining_points_assigned": 0,
        }
    )

    consent_required = game_shortening.declarer_hand_cards_remaining < 9
    rule_section = "4.4.2" if consent_required else "4.4.1"
    summary = {
        "schema_version": game_shortening.schema_version,
        "kind": game_shortening.kind,
        "rule_sections": [rule_section],
        "declarer_hand_cards_remaining": (
            game_shortening.declarer_hand_cards_remaining
        ),
        "hand_card_count_reconciliation": reconciliation,
        "consent_required": consent_required,
        "defender_consent": {
            "status": game_shortening.defender_consent.status,
            "consenting_defender_count": (
                game_shortening.defender_consent.consenting_defender_count
            ),
        },
        "adjudicated_winner": "defenders",
        "remaining_points_assigned": False,
        "settlement_level_policy": (
            "declared_or_overbid_value_without_achieved_levels"
        ),
    }

    return DeclarerConcessionAdjudication(
        game_result_summary=adjudicated_result,
        game_shortening_summary=summary,
    )
