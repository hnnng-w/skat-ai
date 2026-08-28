import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skatmind.declarer_card_exposure import (
    get_declared_mandatory_play_level,
    get_play_level_rank,
)
from skatmind.final_settlement import (
    apply_achieved_schneider_settlement_level,
    apply_achieved_schwarz_settlement_level,
    calculate_basic_settlement_score,
    get_effective_settlement_game_value,
    is_completed_trick_ownership_required_for_schwarz_announcement,
    is_schneider_announcement_failed,
    is_schwarz_announcement_failed,
)
from skatmind.game_decision import get_mandatory_level_source
from skatmind.game_declaration import get_base_game_value
from skatmind.game_result import (
    get_card_point_winner,
    get_completed_trick_schwarz_status,
    get_null_contract_winner_from_completed_tricks,
    get_schneider_status,
    get_schwarz_status,
)
from skatmind.game_value import calculate_game_value, calculate_suit_or_grand_game_level
from skatmind.overbid import calculate_required_overbid_game_value, get_overbid_required_level
from skatmind.party_wide_claim_contracts import (
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND,
)
from skatmind.party_wide_claim_proof_contracts import (
    PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
    PartyWideClaimProofResultV1,
)

PARTY_WIDE_CLAIM_ADJUDICATION_FACTS_VERSION = 1
PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_VERSION = 1

PARTY_WIDE_CLAIM_ADJUDICATION_STATUSES = (
    "adjudicated",
    "no_outcome",
)
PARTY_WIDE_CLAIM_ADJUDICATION_REASONS = (
    "valid_proof",
    "invalid_proof",
    "unavailable_proof",
)
PARTY_WIDE_CLAIM_ADJUDICATION_OUTCOME_SOURCES = (
    "preexisting_game_decision",
    "exact_party_wide_claim_adjudication",
)
PARTY_WIDE_CLAIM_ADJUDICATION_WINNER_BASES = (
    "preexisting_game_decision",
    "completed_claim_assignment",
)

PARTY_WIDE_CLAIM_ADJUDICATION_PROOF_POLICY = "valid_proof_only_terminal_adjudication"
PARTY_WIDE_CLAIM_ADJUDICATION_PREEXISTING_POLICY = "preserve_preexisting_game_decision"
PARTY_WIDE_CLAIM_ADJUDICATION_ASSIGNMENT_POLICY = (
    "assign_all_unresolved_tricks_cards_and_points_to_claiming_party"
)
PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_POLICY = "complete_points_and_trick_ownership_before_result"
PARTY_WIDE_CLAIM_ADJUDICATION_LEVEL_POLICY = "normal_achieved_levels_with_null_not_applicable"
PARTY_WIDE_CLAIM_ADJUDICATION_OVERBID_POLICY = "preserve_declared_and_overbid_required_value"
PARTY_WIDE_CLAIM_ADJUDICATION_SETTLEMENT_POLICY = "reuse_existing_result_and_final_settlement"
PARTY_WIDE_CLAIM_ADJUDICATION_SETTLEMENT_PROJECTION_POLICY = (
    "exact_claim_assignment_reuses_normal_completion_settlement_projection"
)
PARTY_WIDE_CLAIM_ADJUDICATION_NO_OUTCOME_POLICY = "invalid_or_unavailable_proof_produces_no_outcome"
PARTY_WIDE_CLAIM_ADJUDICATION_RUNTIME_POLICY = (
    "private_internal_without_runtime_or_historical_union"
)
PARTY_WIDE_CLAIM_ADJUDICATION_EXECUTION_POLICY = "no_proof_rerun_search_or_fallback"

_PARTIES = ("declarer", "defenders")
_DECISION_STATES = (
    "undecided",
    "declarer_already_won",
    "defenders_already_won",
)
_SCHNEIDER_STATUSES = (
    "declarer_made_schneider",
    "defenders_made_schneider",
    "none",
)
_SCHWARZ_STATUSES = (
    "declarer_made_schwarz",
    "defenders_made_schwarz",
    "none",
)


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must be exactly {expected}.")


def _require_count(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a strict non-negative integer.")
    return value


def _freeze_json(value: object, field_name: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} contains a non-finite number.")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} must contain only string mapping keys.")
            frozen[key] = _freeze_json(item, f"{field_name}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, f"{field_name}[{index}]") for index, item in enumerate(value)
        )
    raise ValueError(f"{field_name} must contain only JSON-compatible values.")


def _freeze_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping.")
    frozen = _freeze_json(value, field_name)
    if not isinstance(frozen, Mapping):
        raise ValueError(f"{field_name} must be a mapping.")
    return frozen


def _thaw_json(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _json_value_equals_exact(actual: object, expected: object) -> bool:
    if isinstance(expected, Mapping):
        return (
            isinstance(actual, Mapping)
            and set(actual) == set(expected)
            and all(_json_value_equals_exact(actual[key], value) for key, value in expected.items())
        )
    if isinstance(expected, tuple):
        return (
            type(actual) is tuple
            and len(actual) == len(expected)
            and all(
                _json_value_equals_exact(actual_item, expected_item)
                for actual_item, expected_item in zip(actual, expected, strict=True)
            )
        )
    return type(actual) is type(expected) and actual == expected


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimAdjudicationFactsV1:
    """Complete private accounting derived from one valid Claim proof."""

    party_wide_claim_adjudication_facts_version: int
    claim_kind: str
    claimant_player_id: str
    claiming_party: str
    decision_state_before_claim: str
    outcome_source: str
    winner_basis: str
    adjudicated_winner: str
    observed_declarer_points: int
    observed_defender_points: int
    out_of_play_points: int
    assigned_declarer_points: int
    assigned_defender_points: int
    final_declarer_points: int
    final_defender_points: int
    observed_declarer_tricks: int
    observed_defender_tricks: int
    assigned_declarer_tricks: int
    assigned_defender_tricks: int
    final_declarer_tricks: int
    final_defender_tricks: int
    final_completed_trick_winner_parties: tuple[str, ...]
    remaining_points_recipient: str
    remaining_points_assigned: int
    achieved_schneider_status: str
    achieved_schwarz_status: str
    achieved_schneider_applied: bool
    achieved_schwarz_applied: bool
    overbid_required_level: str | None
    overbid_required_value_applied: bool

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "PartyWideClaimAdjudicationFactsV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimAdjudicationFactsV1":
        facts = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(facts, field_name, field_value)
        return facts

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_adjudication_facts_version": (
                self.party_wide_claim_adjudication_facts_version
            ),
            "claim_kind": self.claim_kind,
            "claimant_player_id": self.claimant_player_id,
            "claiming_party": self.claiming_party,
            "decision_state_before_claim": self.decision_state_before_claim,
            "outcome_source": self.outcome_source,
            "winner_basis": self.winner_basis,
            "adjudicated_winner": self.adjudicated_winner,
            "observed_declarer_points": self.observed_declarer_points,
            "observed_defender_points": self.observed_defender_points,
            "out_of_play_points": self.out_of_play_points,
            "assigned_declarer_points": self.assigned_declarer_points,
            "assigned_defender_points": self.assigned_defender_points,
            "final_declarer_points": self.final_declarer_points,
            "final_defender_points": self.final_defender_points,
            "observed_declarer_tricks": self.observed_declarer_tricks,
            "observed_defender_tricks": self.observed_defender_tricks,
            "assigned_declarer_tricks": self.assigned_declarer_tricks,
            "assigned_defender_tricks": self.assigned_defender_tricks,
            "final_declarer_tricks": self.final_declarer_tricks,
            "final_defender_tricks": self.final_defender_tricks,
            "final_completed_trick_winner_parties": list(self.final_completed_trick_winner_parties),
            "remaining_points_recipient": self.remaining_points_recipient,
            "remaining_points_assigned": self.remaining_points_assigned,
            "achieved_schneider_status": self.achieved_schneider_status,
            "achieved_schwarz_status": self.achieved_schwarz_status,
            "achieved_schneider_applied": self.achieved_schneider_applied,
            "achieved_schwarz_applied": self.achieved_schwarz_applied,
            "overbid_required_level": self.overbid_required_level,
            "overbid_required_value_applied": self.overbid_required_value_applied,
        }


def build_party_wide_claim_adjudication_facts_v1(
    *,
    proof_result: PartyWideClaimProofResultV1,
    decision_state_before_claim: str,
    outcome_source: str,
    winner_basis: str,
    adjudicated_winner: str,
    observed_declarer_points: int,
    observed_defender_points: int,
    out_of_play_points: int,
    assigned_declarer_points: int,
    assigned_defender_points: int,
    final_declarer_points: int,
    final_defender_points: int,
    observed_declarer_tricks: int,
    observed_defender_tricks: int,
    assigned_declarer_tricks: int,
    assigned_defender_tricks: int,
    final_declarer_tricks: int,
    final_defender_tricks: int,
    final_completed_trick_winner_parties: tuple[str, ...],
    remaining_points_recipient: str,
    remaining_points_assigned: int,
    achieved_schneider_status: str,
    achieved_schwarz_status: str,
    achieved_schneider_applied: bool,
    achieved_schwarz_applied: bool,
    overbid_required_level: str | None,
    overbid_required_value_applied: bool,
) -> PartyWideClaimAdjudicationFactsV1:
    if not isinstance(proof_result, PartyWideClaimProofResultV1):
        raise ValueError("proof_result must be a PartyWideClaimProofResultV1.")
    _require_version(
        proof_result.party_wide_claim_proof_result_version,
        PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
        "party_wide_claim_proof_result_version",
    )
    if proof_result.status != "valid" or proof_result.assignment is None:
        raise ValueError("Adjudication Facts require one valid proof Result.")
    preparation = proof_result.preparation
    evidence = preparation.evidence
    if evidence is None:
        raise ValueError("A valid proof Result must retain exact Evidence.")
    claim = preparation.claim
    assignment = proof_result.assignment

    if decision_state_before_claim not in _DECISION_STATES:
        raise ValueError("decision_state_before_claim is not canonical.")
    if outcome_source not in PARTY_WIDE_CLAIM_ADJUDICATION_OUTCOME_SOURCES:
        raise ValueError("outcome_source is not canonical.")
    if winner_basis not in PARTY_WIDE_CLAIM_ADJUDICATION_WINNER_BASES:
        raise ValueError("winner_basis is not canonical.")
    if adjudicated_winner not in _PARTIES:
        raise ValueError("adjudicated_winner must be 'declarer' or 'defenders'.")
    is_preexisting = decision_state_before_claim != "undecided"
    expected_source = (
        "preexisting_game_decision" if is_preexisting else "exact_party_wide_claim_adjudication"
    )
    expected_basis = "preexisting_game_decision" if is_preexisting else "completed_claim_assignment"
    if outcome_source != expected_source or winner_basis != expected_basis:
        raise ValueError("Outcome source and winner basis contradict the pre-Claim decision.")
    expected_preexisting_winner = {
        "declarer_already_won": "declarer",
        "defenders_already_won": "defenders",
    }.get(decision_state_before_claim)
    if (
        expected_preexisting_winner is not None
        and adjudicated_winner != expected_preexisting_winner
    ):
        raise ValueError("A preexisting winner must be preserved.")

    counts = {
        name: _require_count(value, name)
        for name, value in (
            ("observed_declarer_points", observed_declarer_points),
            ("observed_defender_points", observed_defender_points),
            ("out_of_play_points", out_of_play_points),
            ("assigned_declarer_points", assigned_declarer_points),
            ("assigned_defender_points", assigned_defender_points),
            ("final_declarer_points", final_declarer_points),
            ("final_defender_points", final_defender_points),
            ("observed_declarer_tricks", observed_declarer_tricks),
            ("observed_defender_tricks", observed_defender_tricks),
            ("assigned_declarer_tricks", assigned_declarer_tricks),
            ("assigned_defender_tricks", assigned_defender_tricks),
            ("final_declarer_tricks", final_declarer_tricks),
            ("final_defender_tricks", final_defender_tricks),
            ("remaining_points_assigned", remaining_points_assigned),
        )
    }
    expected_out_of_play_points = (
        120
        - evidence.declarer_trick_points
        - evidence.defender_trick_points
        - evidence.unresolved_card_points
    )
    expected_observed = (
        evidence.declarer_trick_points + expected_out_of_play_points,
        evidence.defender_trick_points,
    )
    if (
        counts["out_of_play_points"] != expected_out_of_play_points
        or (
            counts["observed_declarer_points"],
            counts["observed_defender_points"],
        )
        != expected_observed
    ):
        raise ValueError("Observed point accounting contradicts Claim Evidence.")

    expected_assigned_points = (
        (assignment.assigned_card_points, 0)
        if claim.claiming_party == "declarer"
        else (0, assignment.assigned_card_points)
    )
    expected_assigned_tricks = (
        (assignment.assigned_trick_count, 0)
        if claim.claiming_party == "declarer"
        else (0, assignment.assigned_trick_count)
    )
    if (
        counts["assigned_declarer_points"],
        counts["assigned_defender_points"],
    ) != expected_assigned_points or (
        counts["assigned_declarer_tricks"],
        counts["assigned_defender_tricks"],
    ) != expected_assigned_tricks:
        raise ValueError("Adjudication assignment contradicts the valid proof assignment.")
    if assignment.assigned_card_count != evidence.unresolved_card_count:
        raise ValueError("Proof assigned Card count contradicts Claim Evidence.")
    if (
        assignment.assigned_card_points != evidence.unresolved_card_points
        or assignment.assigned_trick_count != evidence.remaining_trick_count
    ):
        raise ValueError("Proof assignment totals contradict Claim Evidence.")

    if (
        counts["final_declarer_points"]
        != counts["observed_declarer_points"] + counts["assigned_declarer_points"]
        or counts["final_defender_points"]
        != counts["observed_defender_points"] + counts["assigned_defender_points"]
        or counts["final_declarer_points"] + counts["final_defender_points"] != 120
    ):
        raise ValueError("Final Claim points must reconcile and total 120.")
    if (
        counts["observed_declarer_tricks"] != evidence.declarer_completed_tricks
        or counts["observed_defender_tricks"] != evidence.defender_completed_tricks
        or counts["final_declarer_tricks"]
        != counts["observed_declarer_tricks"] + counts["assigned_declarer_tricks"]
        or counts["final_defender_tricks"]
        != counts["observed_defender_tricks"] + counts["assigned_defender_tricks"]
        or counts["final_declarer_tricks"] + counts["final_defender_tricks"] != 10
    ):
        raise ValueError("Final Claim Trick counts must reconcile and total ten.")

    if type(final_completed_trick_winner_parties) is not tuple:
        raise ValueError("final_completed_trick_winner_parties must be an immutable tuple.")
    expected_winner_parties = (
        tuple(trick.winner_side for trick in evidence.completed_tricks)
        + (claim.claiming_party,) * evidence.remaining_trick_count
    )
    if final_completed_trick_winner_parties != expected_winner_parties:
        raise ValueError("Final Trick ownership contradicts Evidence and proof assignment.")
    if len(final_completed_trick_winner_parties) != 10 or any(
        party not in _PARTIES for party in final_completed_trick_winner_parties
    ):
        raise ValueError("Final Trick ownership must contain ten canonical parties.")
    if (
        final_completed_trick_winner_parties.count("declarer") != counts["final_declarer_tricks"]
        or final_completed_trick_winner_parties.count("defenders")
        != counts["final_defender_tricks"]
    ):
        raise ValueError("Final Trick ownership does not match final Trick counts.")
    if (
        remaining_points_recipient != claim.claiming_party
        or counts["remaining_points_assigned"] != assignment.assigned_card_points
    ):
        raise ValueError("Remaining-point facts contradict the valid proof assignment.")

    is_null = evidence.declaration.game_type == "null"
    if is_null:
        if (
            achieved_schneider_status != "not_applicable"
            or achieved_schwarz_status != "not_applicable"
            or achieved_schneider_applied is not False
            or achieved_schwarz_applied is not False
        ):
            raise ValueError("Null Claim adjudication cannot apply Schneider or Schwarz.")
    else:
        expected_schneider_status = (
            "declarer_made_schneider"
            if counts["final_defender_points"] <= 30
            else ("defenders_made_schneider" if counts["final_declarer_points"] <= 30 else "none")
        )
        expected_schwarz_status = (
            "declarer_made_schwarz"
            if counts["final_defender_tricks"] == 0
            else ("defenders_made_schwarz" if counts["final_declarer_tricks"] == 0 else "none")
        )
        if (
            achieved_schneider_status not in _SCHNEIDER_STATUSES
            or achieved_schwarz_status not in _SCHWARZ_STATUSES
            or achieved_schneider_status != expected_schneider_status
            or achieved_schwarz_status != expected_schwarz_status
        ):
            raise ValueError("Suit and Grand achieved levels contradict completed ownership.")
    if not isinstance(achieved_schneider_applied, bool) or not isinstance(
        achieved_schwarz_applied, bool
    ):
        raise ValueError("Achieved-level application fields must be booleans.")
    if overbid_required_level not in (None, "schneider", "schwarz"):
        raise ValueError("overbid_required_level is not canonical.")
    if not isinstance(overbid_required_value_applied, bool):
        raise ValueError("overbid_required_value_applied must be a boolean.")
    declaration = evidence.declaration
    game_value = calculate_game_value(declaration)
    expected_overbid_applied = (
        declaration.bid_value is not None and declaration.bid_value > game_value
    )
    expected_overbid_level = None
    if expected_overbid_applied:
        if is_null:
            raise ValueError("Null Overbid Claim adjudication is unsupported.")
        base_value = get_base_game_value(declaration.game_type)
        required_game_value = calculate_required_overbid_game_value(
            declaration.bid_value,
            base_value,
        )
        additional_levels = required_game_value // base_value - calculate_suit_or_grand_game_level(
            declaration
        )
        expected_overbid_level = {1: "schneider", 2: "schwarz"}.get(additional_levels)
        if expected_overbid_level is None:
            raise ValueError("Claim adjudication requires a supported Overbid level.")
    if (
        overbid_required_level != expected_overbid_level
        or overbid_required_value_applied is not expected_overbid_applied
    ):
        raise ValueError("Overbid-required facts contradict the retained Declaration and bid.")
    expected_schneider_applied = (
        not is_null
        and achieved_schneider_status in {"declarer_made_schneider", "defenders_made_schneider"}
        and not expected_overbid_applied
        and not (
            achieved_schneider_status == "defenders_made_schneider"
            and evidence.declaration.schneider_announced
        )
    )
    expected_schwarz_applied = (
        not is_null
        and achieved_schwarz_status in {"declarer_made_schwarz", "defenders_made_schwarz"}
        and not expected_overbid_applied
    )
    if (
        achieved_schneider_applied is not expected_schneider_applied
        or achieved_schwarz_applied is not expected_schwarz_applied
    ):
        raise ValueError("Achieved-level application contradicts completed Claim facts.")
    declared_level = get_declared_mandatory_play_level(
        {
            "is_null_game": is_null,
            "details": {
                "schneider_announced": declaration.schneider_announced,
                "schwarz_announced": declaration.schwarz_announced,
            },
        }
    )
    mandatory_level = max(
        (level for level in (declared_level, expected_overbid_level) if level is not None),
        key=get_play_level_rank,
        default=None,
    )
    if is_null:
        candidate_winner = get_null_contract_winner_from_completed_tricks(
            [{"winner_role": party} for party in final_completed_trick_winner_parties]
        )
    else:
        candidate_winner = get_card_point_winner(
            counts["final_declarer_points"],
            counts["final_defender_points"],
        )
    achieved_level_rank = 0
    if achieved_schneider_status == "declarer_made_schneider":
        achieved_level_rank = 1
    if achieved_schwarz_status == "declarer_made_schwarz":
        achieved_level_rank = 2
    mandatory_level_covered = (
        mandatory_level is None
        or candidate_winner == "declarer"
        and achieved_level_rank >= get_play_level_rank(mandatory_level)
    )
    expected_winner = expected_preexisting_winner
    if expected_winner is None:
        expected_winner = (
            "defenders"
            if candidate_winner == "declarer" and not mandatory_level_covered
            else candidate_winner
        )
    if adjudicated_winner != expected_winner:
        raise ValueError("Adjudicated winner contradicts the completed Claim assignment.")

    return PartyWideClaimAdjudicationFactsV1._from_validated(
        party_wide_claim_adjudication_facts_version=(PARTY_WIDE_CLAIM_ADJUDICATION_FACTS_VERSION),
        claim_kind=PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND,
        claimant_player_id=claim.claimant_player_id,
        claiming_party=claim.claiming_party,
        decision_state_before_claim=decision_state_before_claim,
        outcome_source=outcome_source,
        winner_basis=winner_basis,
        adjudicated_winner=adjudicated_winner,
        observed_declarer_points=observed_declarer_points,
        observed_defender_points=observed_defender_points,
        out_of_play_points=out_of_play_points,
        assigned_declarer_points=assigned_declarer_points,
        assigned_defender_points=assigned_defender_points,
        final_declarer_points=final_declarer_points,
        final_defender_points=final_defender_points,
        observed_declarer_tricks=observed_declarer_tricks,
        observed_defender_tricks=observed_defender_tricks,
        assigned_declarer_tricks=assigned_declarer_tricks,
        assigned_defender_tricks=assigned_defender_tricks,
        final_declarer_tricks=final_declarer_tricks,
        final_defender_tricks=final_defender_tricks,
        final_completed_trick_winner_parties=final_completed_trick_winner_parties,
        remaining_points_recipient=remaining_points_recipient,
        remaining_points_assigned=remaining_points_assigned,
        achieved_schneider_status=achieved_schneider_status,
        achieved_schwarz_status=achieved_schwarz_status,
        achieved_schneider_applied=achieved_schneider_applied,
        achieved_schwarz_applied=achieved_schwarz_applied,
        overbid_required_level=overbid_required_level,
        overbid_required_value_applied=overbid_required_value_applied,
    )


def _reconcile_adjudication_facts_v1(
    proof_result: PartyWideClaimProofResultV1,
    facts: PartyWideClaimAdjudicationFactsV1,
) -> None:
    evidence = proof_result.preparation.evidence
    assignment = proof_result.assignment
    if evidence is None or assignment is None:
        raise ValueError("Adjudication Facts require retained Evidence and assignment.")
    claim = proof_result.preparation.claim
    out_of_play_points = (
        120
        - evidence.declarer_trick_points
        - evidence.defender_trick_points
        - evidence.unresolved_card_points
    )
    observed_declarer_points = evidence.declarer_trick_points + out_of_play_points
    observed_defender_points = evidence.defender_trick_points
    assigned_declarer_points = (
        assignment.assigned_card_points if claim.claiming_party == "declarer" else 0
    )
    assigned_defender_points = (
        assignment.assigned_card_points if claim.claiming_party == "defenders" else 0
    )
    assigned_declarer_tricks = (
        assignment.assigned_trick_count if claim.claiming_party == "declarer" else 0
    )
    assigned_defender_tricks = (
        assignment.assigned_trick_count if claim.claiming_party == "defenders" else 0
    )
    expected_values = {
        "claim_kind": claim.kind,
        "claimant_player_id": claim.claimant_player_id,
        "claiming_party": claim.claiming_party,
        "observed_declarer_points": observed_declarer_points,
        "observed_defender_points": observed_defender_points,
        "out_of_play_points": out_of_play_points,
        "assigned_declarer_points": assigned_declarer_points,
        "assigned_defender_points": assigned_defender_points,
        "final_declarer_points": observed_declarer_points + assigned_declarer_points,
        "final_defender_points": observed_defender_points + assigned_defender_points,
        "observed_declarer_tricks": evidence.declarer_completed_tricks,
        "observed_defender_tricks": evidence.defender_completed_tricks,
        "assigned_declarer_tricks": assigned_declarer_tricks,
        "assigned_defender_tricks": assigned_defender_tricks,
        "final_declarer_tricks": (evidence.declarer_completed_tricks + assigned_declarer_tricks),
        "final_defender_tricks": (evidence.defender_completed_tricks + assigned_defender_tricks),
        "final_completed_trick_winner_parties": (
            tuple(trick.winner_side for trick in evidence.completed_tricks)
            + (claim.claiming_party,) * assignment.assigned_trick_count
        ),
        "remaining_points_recipient": claim.claiming_party,
        "remaining_points_assigned": assignment.assigned_card_points,
    }
    if any(
        not _json_value_equals_exact(getattr(facts, field_name), expected)
        for field_name, expected in expected_values.items()
    ):
        raise ValueError("Adjudication Facts contradict retained Proof accounting.")
    is_preexisting = facts.decision_state_before_claim != "undecided"
    expected_source = (
        "preexisting_game_decision" if is_preexisting else "exact_party_wide_claim_adjudication"
    )
    expected_basis = "preexisting_game_decision" if is_preexisting else "completed_claim_assignment"
    if facts.outcome_source != expected_source or facts.winner_basis != expected_basis:
        raise ValueError("Adjudication Facts contradict their pre-Claim decision state.")


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimAdjudicationResultV1:
    """One private adjudicated or normal no-outcome Claim result."""

    party_wide_claim_adjudication_result_version: int
    status: str
    reason: str
    proof_result: PartyWideClaimProofResultV1
    facts: PartyWideClaimAdjudicationFactsV1 | None
    game_value_summary: Mapping[str, object] | None
    overbid_summary: Mapping[str, object] | None
    game_result_summary: Mapping[str, object] | None
    final_settlement_summary: Mapping[str, object] | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "PartyWideClaimAdjudicationResultV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimAdjudicationResultV1":
        result = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(result, field_name, field_value)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_adjudication_result_version": (
                self.party_wide_claim_adjudication_result_version
            ),
            "status": self.status,
            "reason": self.reason,
            "proof_result": self.proof_result.to_dict(),
            "facts": self.facts.to_dict() if self.facts is not None else None,
            "game_value_summary": _thaw_json(self.game_value_summary),
            "overbid_summary": _thaw_json(self.overbid_summary),
            "game_result_summary": _thaw_json(self.game_result_summary),
            "final_settlement_summary": _thaw_json(self.final_settlement_summary),
        }


def build_party_wide_claim_adjudication_result_v1(
    *,
    status: str,
    reason: str,
    proof_result: PartyWideClaimProofResultV1,
    facts: PartyWideClaimAdjudicationFactsV1 | None,
    game_value_summary: Mapping[str, object] | None,
    overbid_summary: Mapping[str, object] | None,
    game_result_summary: Mapping[str, object] | None,
    final_settlement_summary: Mapping[str, object] | None,
) -> PartyWideClaimAdjudicationResultV1:
    if not isinstance(proof_result, PartyWideClaimProofResultV1):
        raise ValueError("proof_result must be a PartyWideClaimProofResultV1.")
    _require_version(
        proof_result.party_wide_claim_proof_result_version,
        PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
        "party_wide_claim_proof_result_version",
    )
    if status not in PARTY_WIDE_CLAIM_ADJUDICATION_STATUSES:
        raise ValueError("status is not a canonical Claim adjudication status.")
    if reason not in PARTY_WIDE_CLAIM_ADJUDICATION_REASONS:
        raise ValueError("reason is not a canonical Claim adjudication reason.")

    summaries = (
        game_value_summary,
        overbid_summary,
        game_result_summary,
        final_settlement_summary,
    )
    if status == "no_outcome":
        expected_reason = {
            "invalid": "invalid_proof",
            "unavailable": "unavailable_proof",
        }.get(proof_result.status)
        if reason != expected_reason:
            raise ValueError("No-outcome reason must reconcile with Proof Result status.")
        if facts is not None or any(summary is not None for summary in summaries):
            raise ValueError("A no-outcome Result cannot retain downstream adjudication values.")
        frozen_summaries = (None, None, None, None)
    else:
        if reason != "valid_proof" or proof_result.status != "valid":
            raise ValueError("An adjudicated Result requires one valid proof Result.")
        if not isinstance(facts, PartyWideClaimAdjudicationFactsV1):
            raise ValueError("An adjudicated Result requires adjudication Facts.")
        _require_version(
            facts.party_wide_claim_adjudication_facts_version,
            PARTY_WIDE_CLAIM_ADJUDICATION_FACTS_VERSION,
            "party_wide_claim_adjudication_facts_version",
        )
        claim = proof_result.preparation.claim
        if (
            facts.claim_kind != claim.kind
            or facts.claimant_player_id != claim.claimant_player_id
            or facts.claiming_party != claim.claiming_party
        ):
            raise ValueError("Adjudication Facts contradict the retained Claim.")
        _reconcile_adjudication_facts_v1(proof_result, facts)
        frozen_summaries = tuple(
            _freeze_mapping(summary, field_name)
            for field_name, summary in zip(
                (
                    "game_value_summary",
                    "overbid_summary",
                    "game_result_summary",
                    "final_settlement_summary",
                ),
                summaries,
                strict=True,
            )
        )
        frozen_game_value = frozen_summaries[0]
        frozen_overbid = frozen_summaries[1]
        frozen_game_result = frozen_summaries[2]
        frozen_settlement = frozen_summaries[3]
        helper_game_value = _thaw_json(frozen_game_value)
        helper_overbid = _thaw_json(frozen_overbid)
        declaration = proof_result.preparation.evidence.declaration
        is_null = declaration.game_type == "null"
        game_value = frozen_game_value.get("game_value")
        expected_game_value = calculate_game_value(declaration)
        details = frozen_game_value.get("details")
        if (
            type(game_value) is not int
            or game_value <= 0
            or game_value != expected_game_value
            or frozen_game_value.get("game_type") != declaration.game_type
            or frozen_game_value.get("is_null_game") is not is_null
            or not isinstance(details, Mapping)
            or details.get("hand_game") is not declaration.hand_game
            or details.get("ouvert") is not declaration.ouvert
        ):
            raise ValueError("Game-value summary contradicts the retained Declaration.")
        if is_null:
            if (
                frozen_game_value.get("base_value") is not None
                or frozen_game_value.get("game_level") is not None
            ):
                raise ValueError("Null Game-value summary cannot retain Suit or Grand levels.")
        elif (
            type(frozen_game_value.get("base_value")) is not int
            or frozen_game_value.get("base_value") != get_base_game_value(declaration.game_type)
            or type(frozen_game_value.get("game_level")) is not int
            or frozen_game_value.get("game_level")
            != calculate_suit_or_grand_game_level(declaration)
            or details.get("matadors") != declaration.matadors
            or details.get("hand_game") is not declaration.hand_game
            or details.get("schneider_announced") is not declaration.schneider_announced
            or details.get("schwarz_announced") is not declaration.schwarz_announced
            or details.get("ouvert") is not declaration.ouvert
            or details.get("is_complete") is not True
        ):
            raise ValueError("Suit or Grand Game-value details contradict the Declaration.")
        final_completed_tricks = [
            {"winner_role": party} for party in facts.final_completed_trick_winner_parties
        ]
        if is_null:
            expected_schneider_status = "not_applicable"
            expected_schwarz_status = "not_applicable"
        else:
            expected_schneider_status = get_schneider_status(
                facts.final_declarer_points,
                facts.final_defender_points,
            )
            expected_schwarz_status = {
                "declarer": "declarer_made_schwarz",
                "defenders": "defenders_made_schwarz",
                "none": "none",
            }[get_completed_trick_schwarz_status(final_completed_tricks)]
        if (
            facts.achieved_schneider_status != expected_schneider_status
            or facts.achieved_schwarz_status != expected_schwarz_status
        ):
            raise ValueError("Adjudication Facts contradict completed level semantics.")

        bid_value = declaration.bid_value
        if not _json_value_equals_exact(
            frozen_overbid.get("game_value"), game_value
        ) or not _json_value_equals_exact(frozen_overbid.get("bid_value"), bid_value):
            raise ValueError("Overbid summary contradicts the retained bid and game value.")
        if bid_value is None:
            expected_overbid_values = {
                "is_overbid": None,
                "margin": None,
                "required_game_value": None,
                "status": "unknown_bid_value",
            }
        elif bid_value > game_value:
            required_game_value = frozen_overbid.get("required_game_value")
            base_value = frozen_game_value.get("base_value")
            if type(base_value) is not int:
                raise ValueError("Supported Overbid requires one Suit or Grand base value.")
            canonical_required_game_value = calculate_required_overbid_game_value(
                bid_value,
                base_value,
            )
            if (
                type(required_game_value) is not int
                or required_game_value != canonical_required_game_value
            ):
                raise ValueError("Supported Overbid requires one strict covering game value.")
            expected_overbid_values = {
                "is_overbid": True,
                "margin": game_value - bid_value,
                "required_game_value": required_game_value,
                "status": "overbid",
            }
        else:
            expected_overbid_values = {
                "is_overbid": False,
                "margin": game_value - bid_value,
                "required_game_value": game_value,
                "status": "not_overbid",
            }
        if any(
            not _json_value_equals_exact(frozen_overbid.get(key), value)
            for key, value in expected_overbid_values.items()
        ):
            raise ValueError("Overbid summary contradicts the retained Declaration and game value.")
        is_overbid = frozen_overbid.get("is_overbid") is True
        overbid_required_level = get_overbid_required_level(
            helper_game_value,
            helper_overbid,
        )
        if (
            facts.overbid_required_level != overbid_required_level
            or facts.overbid_required_value_applied is not is_overbid
        ):
            raise ValueError("Adjudication Facts contradict retained Overbid semantics.")
        expected_schneider_applied = (
            not is_null
            and expected_schneider_status in {"declarer_made_schneider", "defenders_made_schneider"}
            and not is_overbid
            and not (
                expected_schneider_status == "defenders_made_schneider"
                and declaration.schneider_announced
            )
        )
        expected_schwarz_applied = (
            not is_null
            and expected_schwarz_status in {"declarer_made_schwarz", "defenders_made_schwarz"}
            and not is_overbid
        )
        if (
            facts.achieved_schneider_applied is not expected_schneider_applied
            or facts.achieved_schwarz_applied is not expected_schwarz_applied
        ):
            raise ValueError("Adjudication Facts contradict achieved-level application.")

        declared_level = get_declared_mandatory_play_level(helper_game_value)
        mandatory_level = max(
            (level for level in (declared_level, overbid_required_level) if level is not None),
            key=get_play_level_rank,
            default=None,
        )
        if is_null:
            candidate_winner = get_null_contract_winner_from_completed_tricks(
                [{"winner_role": party} for party in facts.final_completed_trick_winner_parties]
            )
        else:
            candidate_winner = get_card_point_winner(
                facts.final_declarer_points,
                facts.final_defender_points,
            )
        achieved_level_rank = 0
        if facts.achieved_schneider_status == "declarer_made_schneider":
            achieved_level_rank = 1
        if facts.achieved_schwarz_status == "declarer_made_schwarz":
            achieved_level_rank = 2
        mandatory_level_covered = (
            mandatory_level is None
            or candidate_winner == "declarer"
            and achieved_level_rank >= get_play_level_rank(mandatory_level)
        )
        overbid_requirement_covered = (
            overbid_required_level is None
            or candidate_winner == "declarer"
            and achieved_level_rank >= get_play_level_rank(overbid_required_level)
        )
        if facts.decision_state_before_claim == "declarer_already_won":
            expected_winner = "declarer"
        elif facts.decision_state_before_claim == "defenders_already_won":
            expected_winner = "defenders"
        elif candidate_winner == "declarer" and not mandatory_level_covered:
            expected_winner = "defenders"
        else:
            expected_winner = candidate_winner
        if facts.adjudicated_winner != expected_winner:
            raise ValueError("Adjudicated winner contradicts the completed Claim assignment.")

        is_preexisting = facts.decision_state_before_claim != "undecided"
        expected_game_result_values = {
            "declarer_points": facts.final_declarer_points,
            "defender_points": facts.final_defender_points,
            "points_remaining": 0,
            "is_complete": True,
            "winner": expected_winner,
            "status": "final_decided" if is_preexisting else "final_adjudicated",
            "raw_schneider_status": get_schneider_status(
                facts.final_declarer_points,
                facts.final_defender_points,
            ),
            "raw_schwarz_status": get_schwarz_status(
                facts.final_declarer_points,
                facts.final_defender_points,
            ),
            "effective_schneider_status": facts.achieved_schneider_status,
            "effective_schwarz_status": facts.achieved_schwarz_status,
            "game_end_reason": PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND,
            "game_end_kind": PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND,
            "outcome_source": facts.outcome_source,
            "winner_basis": facts.winner_basis,
            "decision_state_before_game_end": facts.decision_state_before_claim,
            "party_wide_claim_proof_status": proof_result.status,
            "claimant_player_id": claim.claimant_player_id,
            "claiming_party": claim.claiming_party,
            "mandatory_level_awarded": False,
            "mandatory_level_source": get_mandatory_level_source(
                helper_game_value,
                overbid_required_level,
            ),
            "declared_mandatory_play_level": declared_level,
            "mandatory_play_level": mandatory_level,
            "mandatory_level_covered": mandatory_level_covered,
            "achieved_schneider_applied": facts.achieved_schneider_applied,
            "achieved_schwarz_applied": facts.achieved_schwarz_applied,
            "overbid_required_level": overbid_required_level,
            "overbid_requirement_covered": overbid_requirement_covered,
            "overbid_required_value_applied": is_overbid,
            "rest_tricks_recipient": claim.claiming_party,
            "remaining_points_recipient": claim.claiming_party,
            "remaining_points_assigned": facts.remaining_points_assigned,
            "rest_trick_assignment": {
                "source": "party_wide_claim_proof_assignment",
                "recipient": claim.claiming_party,
                "remaining_trick_count": proof_result.assignment.assigned_trick_count,
                "assigned_card_count": proof_result.assignment.assigned_card_count,
                "assigned_card_points": proof_result.assignment.assigned_card_points,
            },
        }
        if any(
            not _json_value_equals_exact(frozen_game_result.get(key), value)
            for key, value in expected_game_result_values.items()
        ):
            raise ValueError("Private Game Result does not reconcile with adjudication Facts.")

        settlement_projection = _thaw_json(frozen_game_result)
        settlement_projection["game_end_reason"] = "normal_completion"
        settlement_projection["game_end_kind"] = "normal_completion"
        expected_effective_game_value = get_effective_settlement_game_value(
            game_value,
            helper_overbid,
        )
        expected_effective_game_value = apply_achieved_schneider_settlement_level(
            expected_effective_game_value,
            helper_game_value,
            settlement_projection,
            helper_overbid,
        )
        expected_effective_game_value = apply_achieved_schwarz_settlement_level(
            expected_effective_game_value,
            helper_game_value,
            settlement_projection,
            helper_overbid,
            final_completed_tricks,
        )
        effective_declarer_won = expected_winner == "declarer"
        if is_overbid:
            effective_declarer_won = False
        elif is_schneider_announcement_failed(
            helper_game_value,
            settlement_projection,
        ):
            effective_declarer_won = False
        elif is_completed_trick_ownership_required_for_schwarz_announcement(
            helper_game_value,
            settlement_projection,
            helper_overbid,
            final_completed_tricks,
        ):
            raise ValueError("Completed Claim Settlement cannot require Trick ownership.")
        elif is_schwarz_announcement_failed(
            helper_game_value,
            settlement_projection,
            final_completed_tricks,
        ):
            effective_declarer_won = False
        expected_settlement_score = calculate_basic_settlement_score(
            expected_effective_game_value,
            effective_declarer_won,
        )
        expected_settlement_values = {
            "is_complete": True,
            "missing_inputs": (),
            "declarer_won_by_card_points": expected_winner == "declarer",
            "winner": expected_winner,
            "game_value": game_value,
            "effective_game_value": expected_effective_game_value,
            "bid_value": bid_value,
            "settlement_score": expected_settlement_score,
            "is_loss": not effective_declarer_won,
            "is_overbid": frozen_overbid.get("is_overbid"),
            "overbid_margin": frozen_overbid.get("margin"),
            "overbid_status": frozen_overbid.get("status"),
            "overbid_required_game_value": frozen_overbid.get("required_game_value"),
        }
        if any(
            not _json_value_equals_exact(frozen_settlement.get(key), value)
            for key, value in expected_settlement_values.items()
        ):
            raise ValueError("Adjudicated Final Settlement must be complete and reconciled.")

    return PartyWideClaimAdjudicationResultV1._from_validated(
        party_wide_claim_adjudication_result_version=(PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_VERSION),
        status=status,
        reason=reason,
        proof_result=proof_result,
        facts=facts,
        game_value_summary=frozen_summaries[0],
        overbid_summary=frozen_summaries[1],
        game_result_summary=frozen_summaries[2],
        final_settlement_summary=frozen_summaries[3],
    )
