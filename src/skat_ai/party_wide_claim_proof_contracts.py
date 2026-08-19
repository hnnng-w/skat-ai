from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_value import build_game_value_summary
from skat_ai.overbid import build_overbid_summary, get_overbid_required_level
from skat_ai.party_wide_claim_contracts import (
    PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS,
    PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS,
    PartyWideAllRemainingTricksClaimV1,
    _require_stable_player_id,
    validate_party_wide_claim_against_evidence_v1,
)
from skat_ai.party_wide_claim_evidence import (
    PartyWideClaimEvidenceV1,
    PartyWideClaimExactStateContextV1,
    build_party_wide_claim_exact_state_context_v1,
    validate_party_wide_claim_exact_state_context_v1,
)
from skat_ai.rules import get_legal_cards, get_trick_winner
from skat_ai.settlement_normative_matrix import (
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1,
)

PARTY_WIDE_CLAIM_PROOF_REQUEST_VERSION = 1
PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION = 1
PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION = 1

PARTY_WIDE_CLAIM_PROOF_PREPARATION_STATUSES = ("available", "unavailable")
PARTY_WIDE_CLAIM_PROOF_STATUSES = ("valid", "invalid", "unavailable")
PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS = (
    "party_wide_claim_evidence_incomplete",
    "party_wide_claim_evidence_contradictory",
    "party_wide_claim_unsupported_contract",
    "party_wide_claim_unsupported_turn_phase",
    "party_wide_claim_no_unresolved_tricks",
    "party_wide_claim_unresolved_trick_limit_exceeded",
    "party_wide_claim_proof_not_executed",
)

_SOURCE_EVIDENCE_REASONS = frozenset(PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS[:2])
_FULL_DECK = frozenset(get_full_deck())


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a strict non-negative integer.")
    return value


def _require_available_preparation(
    preparation: object,
) -> "PartyWideClaimProofPreparationV1":
    if not isinstance(preparation, PartyWideClaimProofPreparationV1):
        raise ValueError("preparation must be a PartyWideClaimProofPreparationV1.")
    if preparation.status != "available" or preparation.request is None:
        raise ValueError("A complete proof Result requires an available preparation.")
    return preparation


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimProofRequestV1:
    party_wide_claim_proof_request_version: int
    proof_policy: str
    proof_quantifiers: tuple[tuple[str, str], ...]
    maximum_unresolved_tricks: int
    claim: PartyWideAllRemainingTricksClaimV1
    evidence: PartyWideClaimEvidenceV1
    exact_state_context: PartyWideClaimExactStateContextV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("PartyWideClaimProofRequestV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimProofRequestV1":
        request = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(request, field_name, field_value)
        return request

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_proof_request_version": (self.party_wide_claim_proof_request_version),
            "proof_policy": self.proof_policy,
            "proof_quantifiers": [
                {"actor": actor, "quantifier": quantifier}
                for actor, quantifier in self.proof_quantifiers
            ],
            "maximum_unresolved_tricks": self.maximum_unresolved_tricks,
            "claim": self.claim.to_dict(),
            "evidence": self.evidence.to_dict(),
            "exact_state_context": self.exact_state_context.to_dict(),
        }


def build_party_wide_claim_proof_request_v1(
    *,
    claim: PartyWideAllRemainingTricksClaimV1,
    evidence: PartyWideClaimEvidenceV1,
    exact_state_context: PartyWideClaimExactStateContextV1,
) -> PartyWideClaimProofRequestV1:
    validate_party_wide_claim_against_evidence_v1(claim, evidence)
    validate_party_wide_claim_exact_state_context_v1(claim, evidence, exact_state_context)
    if not 1 <= evidence.remaining_trick_count <= PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS:
        raise ValueError("Proof Requests require one through five unresolved Tricks.")
    if not _is_supported_claim_contract(evidence):
        raise ValueError("Proof Requests require one supported Claim contract.")
    return PartyWideClaimProofRequestV1._from_validated(
        party_wide_claim_proof_request_version=PARTY_WIDE_CLAIM_PROOF_REQUEST_VERSION,
        proof_policy=PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1,
        proof_quantifiers=PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS,
        maximum_unresolved_tricks=PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS,
        claim=claim,
        evidence=evidence,
        exact_state_context=exact_state_context,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimProofPreparationV1:
    party_wide_claim_proof_preparation_version: int
    status: str
    unavailable_reason: str | None
    claim: PartyWideAllRemainingTricksClaimV1
    evidence: PartyWideClaimEvidenceV1 | None
    request: PartyWideClaimProofRequestV1 | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "PartyWideClaimProofPreparationV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimProofPreparationV1":
        preparation = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(preparation, field_name, field_value)
        return preparation

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_proof_preparation_version": (
                self.party_wide_claim_proof_preparation_version
            ),
            "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "claim": self.claim.to_dict(),
            "evidence": self.evidence.to_dict() if self.evidence is not None else None,
            "request": self.request.to_dict() if self.request is not None else None,
        }


def build_unavailable_party_wide_claim_proof_preparation_v1(
    *,
    claim: PartyWideAllRemainingTricksClaimV1,
    unavailable_reason: str,
    evidence: PartyWideClaimEvidenceV1 | None = None,
) -> PartyWideClaimProofPreparationV1:
    if not isinstance(claim, PartyWideAllRemainingTricksClaimV1):
        raise ValueError("claim must be a PartyWideAllRemainingTricksClaimV1.")
    if unavailable_reason not in PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS:
        raise ValueError("unavailable_reason is not a canonical Claim-proof reason.")
    if unavailable_reason in _SOURCE_EVIDENCE_REASONS:
        if evidence is not None:
            raise ValueError(
                "Incomplete or contradictory source preparation must not retain exact Evidence."
            )
    else:
        if not isinstance(evidence, PartyWideClaimEvidenceV1):
            raise ValueError("A structurally ineligible preparation must retain exact Evidence.")
        validate_party_wide_claim_against_evidence_v1(claim, evidence)
    return PartyWideClaimProofPreparationV1._from_validated(
        party_wide_claim_proof_preparation_version=(PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION),
        status="unavailable",
        unavailable_reason=unavailable_reason,
        claim=claim,
        evidence=evidence,
        request=None,
    )


def _is_supported_claim_contract(evidence: PartyWideClaimEvidenceV1) -> bool:
    game_value_summary = build_game_value_summary(evidence.declaration)
    if game_value_summary["game_value"] is None:
        return False
    overbid_summary = build_overbid_summary(game_value_summary, evidence.declaration.bid_value)
    if overbid_summary["is_overbid"] is True and overbid_summary["required_game_value"] is None:
        return False
    try:
        get_overbid_required_level(game_value_summary, overbid_summary)
    except ValueError:
        return False
    return True


def prepare_party_wide_claim_proof_request_v1(
    claim: PartyWideAllRemainingTricksClaimV1,
    evidence: PartyWideClaimEvidenceV1,
) -> PartyWideClaimProofPreparationV1:
    if not isinstance(evidence, PartyWideClaimEvidenceV1):
        raise ValueError("evidence must be a PartyWideClaimEvidenceV1.")
    validate_party_wide_claim_against_evidence_v1(claim, evidence)
    if evidence.remaining_trick_count == 0:
        return build_unavailable_party_wide_claim_proof_preparation_v1(
            claim=claim,
            evidence=evidence,
            unavailable_reason="party_wide_claim_no_unresolved_tricks",
        )
    if evidence.remaining_trick_count > PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS:
        return build_unavailable_party_wide_claim_proof_preparation_v1(
            claim=claim,
            evidence=evidence,
            unavailable_reason="party_wide_claim_unresolved_trick_limit_exceeded",
        )
    if not _is_supported_claim_contract(evidence):
        return build_unavailable_party_wide_claim_proof_preparation_v1(
            claim=claim,
            evidence=evidence,
            unavailable_reason="party_wide_claim_unsupported_contract",
        )
    participant_ids = {player.player_id for player in evidence.players}
    if evidence.next_player_id not in participant_ids:
        return build_unavailable_party_wide_claim_proof_preparation_v1(
            claim=claim,
            evidence=evidence,
            unavailable_reason="party_wide_claim_unsupported_turn_phase",
        )
    exact_state_context = build_party_wide_claim_exact_state_context_v1(claim, evidence)
    request = build_party_wide_claim_proof_request_v1(
        claim=claim,
        evidence=evidence,
        exact_state_context=exact_state_context,
    )
    return PartyWideClaimProofPreparationV1._from_validated(
        party_wide_claim_proof_preparation_version=(PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION),
        status="available",
        unavailable_reason=None,
        claim=claim,
        evidence=evidence,
        request=request,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimProofMoveV1:
    player_id: str
    card: str
    completed_trick_winner_player_id: str | None
    completed_trick_winner_party: str | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("PartyWideClaimProofMoveV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimProofMoveV1":
        move = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(move, field_name, field_value)
        return move

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "card": self.card,
            "completed_trick_winner_player_id": (self.completed_trick_winner_player_id),
            "completed_trick_winner_party": self.completed_trick_winner_party,
        }


def build_party_wide_claim_proof_move_v1(
    *,
    player_id: str,
    card: str,
    completed_trick_winner_player_id: str | None = None,
    completed_trick_winner_party: str | None = None,
) -> PartyWideClaimProofMoveV1:
    player_id = _require_stable_player_id(player_id, "player_id")
    if not isinstance(card, str) or card not in _FULL_DECK:
        raise ValueError("card must be one canonical Skat Card.")
    if (completed_trick_winner_player_id is None) != (completed_trick_winner_party is None):
        raise ValueError("Completed-Trick winner fields must both be null or present.")
    if completed_trick_winner_player_id is not None:
        completed_trick_winner_player_id = _require_stable_player_id(
            completed_trick_winner_player_id,
            "completed_trick_winner_player_id",
        )
        if completed_trick_winner_party not in ("declarer", "defenders"):
            raise ValueError("completed_trick_winner_party must be 'declarer' or 'defenders'.")
    return PartyWideClaimProofMoveV1._from_validated(
        player_id=player_id,
        card=card,
        completed_trick_winner_player_id=completed_trick_winner_player_id,
        completed_trick_winner_party=completed_trick_winner_party,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimProofAssignmentV1:
    recipient_party: str
    assigned_trick_count: int
    assigned_card_count: int
    assigned_card_points: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "PartyWideClaimProofAssignmentV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimProofAssignmentV1":
        assignment = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(assignment, field_name, field_value)
        return assignment

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipient_party": self.recipient_party,
            "assigned_trick_count": self.assigned_trick_count,
            "assigned_card_count": self.assigned_card_count,
            "assigned_card_points": self.assigned_card_points,
        }


def build_party_wide_claim_proof_assignment_v1(
    *,
    preparation: PartyWideClaimProofPreparationV1,
    recipient_party: str,
    assigned_trick_count: int,
    assigned_card_count: int,
    assigned_card_points: int,
) -> PartyWideClaimProofAssignmentV1:
    preparation = _require_available_preparation(preparation)
    evidence = preparation.evidence
    if evidence is None:
        raise ValueError("Available preparation must retain exact Evidence.")
    for field_name, value in (
        ("assigned_trick_count", assigned_trick_count),
        ("assigned_card_count", assigned_card_count),
        ("assigned_card_points", assigned_card_points),
    ):
        _require_non_negative_integer(value, field_name)
    if recipient_party != preparation.claim.claiming_party:
        raise ValueError("Proof assignment recipient must equal the claiming party.")
    expected = (
        evidence.remaining_trick_count,
        evidence.unresolved_card_count,
        evidence.unresolved_card_points,
    )
    if (
        assigned_trick_count,
        assigned_card_count,
        assigned_card_points,
    ) != expected:
        raise ValueError("Proof assignment must cover every unresolved Trick, Card, and point.")
    return PartyWideClaimProofAssignmentV1._from_validated(
        recipient_party=recipient_party,
        assigned_trick_count=assigned_trick_count,
        assigned_card_count=assigned_card_count,
        assigned_card_points=assigned_card_points,
    )


def _validate_representative_line(
    preparation: "PartyWideClaimProofPreparationV1",
    representative_line: tuple[PartyWideClaimProofMoveV1, ...],
    *,
    valid: bool,
) -> tuple[PartyWideClaimProofMoveV1, ...]:
    if not isinstance(representative_line, tuple) or not representative_line:
        raise ValueError("A complete proof Result requires one representative line.")
    if any(not isinstance(move, PartyWideClaimProofMoveV1) for move in representative_line):
        raise ValueError("representative_line must contain Claim-proof Move values.")
    evidence = preparation.evidence
    if evidence is None:
        raise ValueError("Available preparation must retain exact Evidence.")
    participant_ids = {player.player_id for player in evidence.players}
    if any(
        move.player_id not in participant_ids
        or (
            move.completed_trick_winner_player_id is not None
            and move.completed_trick_winner_player_id not in participant_ids
        )
        for move in representative_line
    ):
        raise ValueError("Representative-line Players must be Evidence participants.")
    if valid and len(representative_line) != sum(
        len(cards) for _, cards in evidence.remaining_hands
    ):
        raise ValueError("A valid representative line must reach normal completion.")

    seat_order = tuple(
        next(player.player_id for player in evidence.players if player.seat == seat)
        for seat in ("forehand", "middlehand", "rearhand")
    )
    hands = {player_id: list(cards) for player_id, cards in evidence.remaining_hands}
    trick = list(evidence.current_trick.plays if evidence.current_trick is not None else ())
    expected_player = evidence.next_player_id
    opposing_winner_found = False
    for move in representative_line:
        if move.player_id != expected_player:
            raise ValueError("Representative-line Player order is not chronological.")
        if move.card not in hands[move.player_id]:
            raise ValueError("Representative-line Card is not held by the acting Player.")
        legal_cards = get_legal_cards(
            hands[move.player_id],
            [card for _, card in trick],
            evidence.declaration.game_type,
        )
        if move.card not in legal_cards:
            raise ValueError("Representative-line Card violates Bedienpflicht.")
        hands[move.player_id].remove(move.card)
        trick.append((move.player_id, move.card))
        if len(trick) == 3:
            winner_index = get_trick_winner(
                [card for _, card in trick], evidence.declaration.game_type
            )
            winner_player_id = trick[winner_index][0]
            winner_party = (
                "declarer" if winner_player_id == evidence.declarer_player_id else "defenders"
            )
            if (
                move.completed_trick_winner_player_id != winner_player_id
                or move.completed_trick_winner_party != winner_party
            ):
                raise ValueError("Representative-line completed-Trick winner is incorrect.")
            if winner_party != preparation.claim.claiming_party:
                opposing_winner_found = True
            expected_player = winner_player_id
            trick = []
        else:
            if move.completed_trick_winner_player_id is not None:
                raise ValueError("Non-completing Move cannot retain a Trick winner.")
            player_index = seat_order.index(move.player_id)
            expected_player = seat_order[(player_index + 1) % 3]
    if valid and opposing_winner_found:
        raise ValueError("A valid representative line assigns a Trick to the opposing party.")
    if not valid and not opposing_winner_found:
        raise ValueError("An invalid representative line must show an opposing-party Trick.")
    return tuple(representative_line)


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimProofResultV1:
    party_wide_claim_proof_result_version: int
    status: str
    preparation: PartyWideClaimProofPreparationV1
    proof_complete: bool
    claim_satisfied: bool | None
    unavailable_reason: str | None
    evaluated_state_count: int
    memoized_state_count: int
    terminal_state_count: int
    counterexample_found: bool
    assignment: PartyWideClaimProofAssignmentV1 | None
    representative_line: tuple[PartyWideClaimProofMoveV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("PartyWideClaimProofResultV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimProofResultV1":
        result = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(result, field_name, field_value)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_proof_result_version": (self.party_wide_claim_proof_result_version),
            "status": self.status,
            "preparation": self.preparation.to_dict(),
            "proof_complete": self.proof_complete,
            "claim_satisfied": self.claim_satisfied,
            "unavailable_reason": self.unavailable_reason,
            "evaluated_state_count": self.evaluated_state_count,
            "memoized_state_count": self.memoized_state_count,
            "terminal_state_count": self.terminal_state_count,
            "counterexample_found": self.counterexample_found,
            "assignment": self.assignment.to_dict() if self.assignment is not None else None,
            "representative_line": [move.to_dict() for move in self.representative_line],
        }


def _validate_complete_result_counters(
    *,
    evaluated_state_count: int,
    memoized_state_count: int,
    terminal_state_count: int,
) -> None:
    for field_name, value in (
        ("evaluated_state_count", evaluated_state_count),
        ("memoized_state_count", memoized_state_count),
        ("terminal_state_count", terminal_state_count),
    ):
        _require_non_negative_integer(value, field_name)
    if terminal_state_count < 1:
        raise ValueError("A complete proof Result must evaluate a terminal state.")
    if memoized_state_count > evaluated_state_count:
        raise ValueError("memoized_state_count cannot exceed evaluated_state_count.")
    if terminal_state_count > evaluated_state_count:
        raise ValueError("terminal_state_count cannot exceed evaluated_state_count.")


def build_valid_party_wide_claim_proof_result_v1(
    *,
    preparation: PartyWideClaimProofPreparationV1,
    evaluated_state_count: int,
    memoized_state_count: int,
    terminal_state_count: int,
    assignment: PartyWideClaimProofAssignmentV1,
    representative_line: tuple[PartyWideClaimProofMoveV1, ...],
) -> PartyWideClaimProofResultV1:
    preparation = _require_available_preparation(preparation)
    _validate_complete_result_counters(
        evaluated_state_count=evaluated_state_count,
        memoized_state_count=memoized_state_count,
        terminal_state_count=terminal_state_count,
    )
    if not isinstance(assignment, PartyWideClaimProofAssignmentV1):
        raise ValueError("A valid proof Result requires one proof-level assignment.")
    evidence = preparation.evidence
    if evidence is None or (
        assignment.recipient_party != preparation.claim.claiming_party
        or assignment.assigned_trick_count != evidence.remaining_trick_count
        or assignment.assigned_card_count != evidence.unresolved_card_count
        or assignment.assigned_card_points != evidence.unresolved_card_points
    ):
        raise ValueError("Valid proof assignment contradicts the preparation.")
    line = _validate_representative_line(preparation, representative_line, valid=True)
    return PartyWideClaimProofResultV1._from_validated(
        party_wide_claim_proof_result_version=PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
        status="valid",
        preparation=preparation,
        proof_complete=True,
        claim_satisfied=True,
        unavailable_reason=None,
        evaluated_state_count=evaluated_state_count,
        memoized_state_count=memoized_state_count,
        terminal_state_count=terminal_state_count,
        counterexample_found=False,
        assignment=assignment,
        representative_line=line,
    )


def build_invalid_party_wide_claim_proof_result_v1(
    *,
    preparation: PartyWideClaimProofPreparationV1,
    evaluated_state_count: int,
    memoized_state_count: int,
    terminal_state_count: int,
    representative_line: tuple[PartyWideClaimProofMoveV1, ...],
) -> PartyWideClaimProofResultV1:
    preparation = _require_available_preparation(preparation)
    _validate_complete_result_counters(
        evaluated_state_count=evaluated_state_count,
        memoized_state_count=memoized_state_count,
        terminal_state_count=terminal_state_count,
    )
    line = _validate_representative_line(preparation, representative_line, valid=False)
    return PartyWideClaimProofResultV1._from_validated(
        party_wide_claim_proof_result_version=PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
        status="invalid",
        preparation=preparation,
        proof_complete=True,
        claim_satisfied=False,
        unavailable_reason=None,
        evaluated_state_count=evaluated_state_count,
        memoized_state_count=memoized_state_count,
        terminal_state_count=terminal_state_count,
        counterexample_found=True,
        assignment=None,
        representative_line=line,
    )


def build_unavailable_party_wide_claim_proof_result_v1(
    *,
    preparation: PartyWideClaimProofPreparationV1,
    unavailable_reason: str,
) -> PartyWideClaimProofResultV1:
    if not isinstance(preparation, PartyWideClaimProofPreparationV1):
        raise ValueError("preparation must be a PartyWideClaimProofPreparationV1.")
    if unavailable_reason not in PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS:
        raise ValueError("unavailable_reason is not a canonical Claim-proof reason.")
    if preparation.status == "available":
        if unavailable_reason != "party_wide_claim_proof_not_executed":
            raise ValueError(
                "An available preparation may only be unavailable because proof was not executed."
            )
    elif unavailable_reason != preparation.unavailable_reason:
        raise ValueError("Unavailable Result reason must equal the preparation reason.")
    return PartyWideClaimProofResultV1._from_validated(
        party_wide_claim_proof_result_version=PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
        status="unavailable",
        preparation=preparation,
        proof_complete=False,
        claim_satisfied=None,
        unavailable_reason=unavailable_reason,
        evaluated_state_count=0,
        memoized_state_count=0,
        terminal_state_count=0,
        counterexample_found=False,
        assignment=None,
        representative_line=(),
    )
