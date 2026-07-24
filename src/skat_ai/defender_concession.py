from dataclasses import dataclass
from typing import Any

from skat_ai.declarer_concession import (
    LIST_WORKFLOW_FIELDS,
    is_strict_integer,
    require_exact_keys,
)
from skat_ai.final_settlement import is_schneider_announced
from skat_ai.game_decision import (
    determine_decision_state_before_game_end,
    get_mandatory_level_source,
    get_secured_achieved_schneider_status,
)
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_value import build_game_value_summary
from skat_ai.overbid import build_overbid_summary, get_overbid_required_level
from skat_ai.turn_phase import CONCRETE_PLAYERS

DEFENDER_CONCESSION_KIND = "defender_concession"
VALID_CONCESSION_FORMS = {
    "explicit_verbal",
    "adjudicated_unambiguous_conduct",
}
DEFENDER_CONCESSION_KEYS = {
    "schema_version",
    "kind",
    "conceding_player",
    "concession_form",
}


@dataclass(frozen=True)
class DefenderConcession:
    schema_version: int
    kind: str
    conceding_player: str
    concession_form: str


@dataclass(frozen=True)
class DefenderConcessionAdjudication:
    game_result_summary: dict[str, Any]
    game_shortening_summary: dict[str, Any]


def build_defender_concession(value: Any) -> DefenderConcession:
    """Builds and validates one version-1 defender concession."""
    if not isinstance(value, dict):
        raise ValueError("game_shortening must be an object.")

    require_exact_keys(value, DEFENDER_CONCESSION_KEYS, "game_shortening")

    schema_version = value["schema_version"]
    if not is_strict_integer(schema_version) or schema_version != 1:
        raise ValueError("game_shortening.schema_version must be exactly 1.")

    kind = value["kind"]
    if kind != DEFENDER_CONCESSION_KIND:
        raise ValueError(
            "game_shortening.kind must be 'defender_concession' for schema_version 1."
        )

    conceding_player = value["conceding_player"]
    if conceding_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "game_shortening.conceding_player must be 'me', 'left', or 'right'."
        )

    concession_form = value["concession_form"]
    if concession_form not in VALID_CONCESSION_FORMS:
        raise ValueError(
            "game_shortening.concession_form must be 'explicit_verbal' or "
            "'adjudicated_unambiguous_conduct'."
        )

    return DefenderConcession(
        schema_version=schema_version,
        kind=kind,
        conceding_player=conceding_player,
        concession_form=concession_form,
    )


def validate_defender_concession_context(
    data: dict[str, Any],
    concession: DefenderConcession,
) -> None:
    """Validates party, workflow, timing, and settlement prerequisites."""
    if data.get("analysis_mode", "live_decision") != "post_game_review":
        raise ValueError(
            "game_shortening defender concession requires "
            "analysis_mode='post_game_review'."
        )

    declarer_player = data.get("declarer_player", "unknown")
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError(
            "game_shortening defender concession requires a concrete declarer_player."
        )
    if concession.conceding_player == declarer_player:
        raise ValueError(
            "game_shortening.conceding_player must be a member of the defending party."
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
        raise ValueError(
            "A defender concession cannot occur after all ten tricks are complete."
        )

    declaration = build_game_declaration_from_input(data)
    game_value_summary = build_game_value_summary(declaration)
    if game_value_summary["game_value"] is None:
        raise ValueError(
            "game_shortening defender concession requires enough declaration "
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
            "game_shortening defender concession requires a supported "
            "overbid-required game value."
        )
    get_overbid_required_level(game_value_summary, overbid_summary)


def adjudicate_defender_concession(
    game_shortening: DefenderConcession,
    game_result_summary: dict[str, Any],
    game_value_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
    completed_tricks: list[dict[str, Any]],
) -> DefenderConcessionAdjudication:
    """Adjudicates one defender concession without assigning or simulating cards."""
    if game_value_summary.get("game_value") is None:
        raise ValueError("A defender concession requires a calculable game value.")
    if (
        overbid_summary.get("is_overbid") is True
        and overbid_summary.get("required_game_value") is None
    ):
        raise ValueError(
            "A defender concession requires a supported overbid-required game value."
        )

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
    if decision_state == "defenders_already_won":
        winner = "defenders"
    else:
        winner = "declarer"

    is_preexisting_decision = decision_state != "undecided"
    outcome_source = (
        "preexisting_game_decision" if is_preexisting_decision else "adjudicated"
    )
    winner_basis = (
        "preexisting_game_decision" if is_preexisting_decision else DEFENDER_CONCESSION_KIND
    )
    mandatory_level_source = get_mandatory_level_source(
        game_value_summary,
        overbid_required_level,
    )
    mandatory_level_awarded = (
        decision_state == "undecided" and mandatory_level_source is not None
    )
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
    achieved_schwarz_applied = False
    overbid_required_value_applied = overbid_summary.get("is_overbid") is True

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
            "game_end_reason": DEFENDER_CONCESSION_KIND,
            "game_end_kind": DEFENDER_CONCESSION_KIND,
            "outcome_source": outcome_source,
            "winner_basis": winner_basis,
            "decision_state_before_game_end": decision_state,
            "mandatory_level_awarded": mandatory_level_awarded,
            "mandatory_level_source": mandatory_level_source,
            "achieved_schneider_applied": achieved_schneider_applied,
            "achieved_schwarz_applied": achieved_schwarz_applied,
            "overbid_required_value_applied": overbid_required_value_applied,
            "remaining_points_recipient": None,
            "remaining_points_assigned": 0,
        }
    )

    rule_sections = ["4.4.3", "4.1.3" if is_preexisting_decision else "4.1.4"]
    if mandatory_level_awarded:
        rule_sections.append("4.1.5")

    summary = {
        "schema_version": game_shortening.schema_version,
        "kind": game_shortening.kind,
        "rule_sections": rule_sections,
        "conceding_player": game_shortening.conceding_player,
        "concession_form": game_shortening.concession_form,
        "liable_party": "defenders",
        "joint_liability": True,
        "decision_state_before_concession": decision_state,
        "adjudicated_winner": winner,
        "winner_basis": winner_basis,
        "remaining_points_assigned": False,
        "continued_play_requested": False,
        "settlement_level_policy": (
            "secured_observed_levels_only"
            if is_preexisting_decision
            else "declared_or_mandatory_value_without_optional_achieved_levels"
        ),
    }

    return DefenderConcessionAdjudication(
        game_result_summary=adjusted_result,
        game_shortening_summary=summary,
    )
