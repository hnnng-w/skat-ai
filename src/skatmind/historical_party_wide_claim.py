from typing import Any

from skatmind.errors import SkatMindInvariantError
from skatmind.historical_game_end import (
    HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_VERSION,
    HistoricalPartyWideAllRemainingTricksClaim,
)
from skatmind.historical_play_prefix import (
    HistoricalReplayState,
    build_serializable_incomplete_trick,
)
from skatmind.party_wide_claim_adjudication import (
    adjudicate_party_wide_claim_proof_v1,
)
from skatmind.party_wide_claim_contracts import (
    PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS,
    PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS,
    build_party_wide_all_remaining_tricks_claim_v1,
)
from skatmind.party_wide_claim_evidence import (
    build_party_wide_claim_evidence_from_historical_replay_v1,
)
from skatmind.party_wide_claim_proof_contracts import (
    prepare_party_wide_claim_proof_request_v1,
)
from skatmind.party_wide_claim_proof_executor import (
    PARTY_WIDE_CLAIM_PROOF_EXECUTION_METHOD,
    PARTY_WIDE_CLAIM_PROOF_EXECUTOR_VERSION,
    execute_party_wide_claim_proof_v1,
)
from skatmind.rules import get_card_points
from skatmind.settlement_normative_matrix import (
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1,
)

HISTORICAL_PARTY_WIDE_CLAIM_SUMMARY_VERSION = 1
HISTORICAL_PARTY_WIDE_CLAIM_SOURCE_POLICY = "complete_historical_record_and_terminal_claim_event"
HISTORICAL_PARTY_WIDE_CLAIM_EXECUTION_POLICY = "replay_prepare_execute_adjudicate_once"
HISTORICAL_PARTY_WIDE_CLAIM_VALIDITY_POLICY = "valid_proof_required_for_terminal_historical_record"
HISTORICAL_PARTY_WIDE_CLAIM_INVALID_POLICY = "invalid_or_unavailable_proof_rejects_terminal_record"
HISTORICAL_PARTY_WIDE_CLAIM_CONTINUATION_POLICY = "one_supported_continuation_before_terminal_claim"
HISTORICAL_PARTY_WIDE_CLAIM_OUTPUT_POLICY = (
    "diagnostic_proof_and_adjudication_summary_without_private_state_duplication"
)
HISTORICAL_PARTY_WIDE_CLAIM_DOWNSTREAM_POLICY = (
    "played_prefix_only_decisions_without_terminal_target"
)
HISTORICAL_PARTY_WIDE_CLAIM_PUBLIC_POLICY = "historical_root_workflow_only_without_flat_shortening"
HISTORICAL_PARTY_WIDE_CLAIM_MATRIX_CASE_ID = (
    "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
)
HISTORICAL_PARTY_WIDE_CLAIM_REPRESENTATIVE_LINE_SCOPE = "diagnostic_decisive_branch_only"


def _build_exact_proof_summary(proof: Any) -> dict[str, Any]:
    if proof.assignment is None:
        raise SkatMindInvariantError("Valid party-wide Claim proof lacks its assignment.")
    return {
        "executor_version": PARTY_WIDE_CLAIM_PROOF_EXECUTOR_VERSION,
        "execution_method": PARTY_WIDE_CLAIM_PROOF_EXECUTION_METHOD,
        "status": proof.status,
        "proof_complete": proof.proof_complete,
        "claim_satisfied": proof.claim_satisfied,
        "evaluated_state_count": proof.evaluated_state_count,
        "memoized_state_count": proof.memoized_state_count,
        "terminal_state_count": proof.terminal_state_count,
        "counterexample_found": proof.counterexample_found,
        "assignment": proof.assignment.to_dict(),
        "representative_line": [move.to_dict() for move in proof.representative_line],
        "representative_line_scope": (HISTORICAL_PARTY_WIDE_CLAIM_REPRESENTATIVE_LINE_SCOPE),
    }


def _build_adjudication_summary(adjudication: Any) -> dict[str, Any]:
    facts = adjudication.facts
    if facts is None:
        raise SkatMindInvariantError("Valid party-wide Claim lacks adjudication Facts.")
    return {
        "adjudication_result_version": (adjudication.party_wide_claim_adjudication_result_version),
        "adjudication_facts_version": (facts.party_wide_claim_adjudication_facts_version),
        "status": adjudication.status,
        "reason": adjudication.reason,
        "decision_state_before_claim": facts.decision_state_before_claim,
        "outcome_source": facts.outcome_source,
        "winner_basis": facts.winner_basis,
        "adjudicated_winner": facts.adjudicated_winner,
        "final_declarer_points": facts.final_declarer_points,
        "final_defender_points": facts.final_defender_points,
        "final_declarer_tricks": facts.final_declarer_tricks,
        "final_defender_tricks": facts.final_defender_tricks,
        "remaining_points_recipient": facts.remaining_points_recipient,
        "remaining_points_assigned": facts.remaining_points_assigned,
        "achieved_schneider_status": facts.achieved_schneider_status,
        "achieved_schwarz_status": facts.achieved_schwarz_status,
        "achieved_schneider_applied": facts.achieved_schneider_applied,
        "achieved_schwarz_applied": facts.achieved_schwarz_applied,
        "overbid_required_level": facts.overbid_required_level,
        "overbid_required_value_applied": facts.overbid_required_value_applied,
    }


def adjudicate_historical_party_wide_claim(
    record: Any,
    replay: HistoricalReplayState,
) -> dict[str, Any]:
    """Proves and adjudicates one terminal Historical party-wide Claim."""
    event = record.game_end
    if not isinstance(event, HistoricalPartyWideAllRemainingTricksClaim):
        raise ValueError("Historical party-wide Claim adjudication requires its event.")
    if event.schema_version != HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_VERSION:
        raise SkatMindInvariantError("Historical party-wide Claim schema version drifted.")

    claim = build_party_wide_all_remaining_tricks_claim_v1(
        claimant_player_id=event.claimant_player_id,
        claiming_party=event.claiming_party,
    )
    evidence = build_party_wide_claim_evidence_from_historical_replay_v1(
        record,
        replay,
    )
    preparation = prepare_party_wide_claim_proof_request_v1(claim, evidence)
    if preparation.status == "unavailable":
        raise ValueError(
            f"Historical game '{record.game_id}': party-wide Claim proof is "
            f"unavailable: {preparation.unavailable_reason}."
        )

    proof = execute_party_wide_claim_proof_v1(preparation)
    if proof.status == "invalid":
        raise ValueError(f"Historical game '{record.game_id}': party-wide Claim proof is invalid.")
    if proof.status != "valid":
        raise SkatMindInvariantError(
            "Available party-wide Claim proof execution did not return a complete Result."
        )

    adjudication = adjudicate_party_wide_claim_proof_v1(proof)
    if (
        adjudication.status != "adjudicated"
        or adjudication.reason != "valid_proof"
        or adjudication.facts is None
    ):
        raise SkatMindInvariantError(
            "Valid party-wide Claim proof did not produce one adjudicated outcome."
        )
    values = adjudication.to_dict()
    facts = adjudication.facts
    game_result_summary = values["game_result_summary"]
    game_value_summary = values["game_value_summary"]
    overbid_summary = values["overbid_summary"]
    final_settlement_summary = values["final_settlement_summary"]
    if not all(
        isinstance(summary, dict)
        for summary in (
            game_result_summary,
            game_value_summary,
            overbid_summary,
            final_settlement_summary,
        )
    ):
        raise SkatMindInvariantError("Adjudicated party-wide Claim summaries are incomplete.")

    out_of_play_points = facts.out_of_play_points
    unresolved_current_trick_points = (
        sum(get_card_points(card) for _, card in replay.current_trick.plays)
        if replay.current_trick is not None
        else 0
    )
    unresolved_remaining_hand_points = sum(
        get_card_points(card)
        for _, remaining_hand in replay.remaining_hands
        for card in remaining_hand
    )
    point_accounting = {
        "completed_trick_declarer_points": evidence.declarer_trick_points,
        "completed_trick_defender_points": evidence.defender_trick_points,
        "skat_points": out_of_play_points,
        "observed_declarer_points": facts.observed_declarer_points,
        "observed_defender_points": facts.observed_defender_points,
        "unresolved_current_trick_points": unresolved_current_trick_points,
        "unresolved_remaining_hand_points": unresolved_remaining_hand_points,
        "total_unresolved_points": evidence.unresolved_card_points,
        "assigned_declarer_points": facts.assigned_declarer_points,
        "assigned_defender_points": facts.assigned_defender_points,
        "final_declarer_points": facts.final_declarer_points,
        "final_defender_points": facts.final_defender_points,
        "total_card_points": 120,
    }
    defender_player_ids = [
        player.player_id
        for player in evidence.players
        if player.player_id != evidence.declarer_player_id
    ]
    exact_proof_summary = _build_exact_proof_summary(proof)
    adjudication_summary = _build_adjudication_summary(adjudication)
    historical_end_summary = {
        "schema_version": HISTORICAL_PARTY_WIDE_CLAIM_SUMMARY_VERSION,
        "kind": event.kind,
        "normative_matrix_case_id": HISTORICAL_PARTY_WIDE_CLAIM_MATRIX_CASE_ID,
        "claimant_player_id": event.claimant_player_id,
        "claiming_party": event.claiming_party,
        "declarer_player_id": record.declarer_player_id,
        "defender_player_ids": defender_player_ids,
        "event_after_play_count": replay.played_card_count,
        "event_after_completed_trick_count": len(replay.completed_tricks),
        "event_during_incomplete_trick": replay.current_trick is not None,
        "remaining_trick_count": evidence.remaining_trick_count,
        "proof_policy": PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1,
        "proof_quantifiers": [
            {"actor": actor, "quantifier": quantifier}
            for actor, quantifier in PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS
        ],
        "proof_maximum_unresolved_tricks": (PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS),
        "exact_proof": exact_proof_summary,
        "adjudication": adjudication_summary,
        "settlement_applied": True,
    }
    play_prefix_summary = {
        "played_card_count": replay.played_card_count,
        "completed_trick_count": len(replay.completed_tricks),
        "current_trick_card_count": (
            len(replay.current_trick.plays) if replay.current_trick is not None else 0
        ),
        "remaining_hand_sizes": {
            player_id: len(cards) for player_id, cards in replay.remaining_hands
        },
        "next_player_id": replay.next_player_id,
    }
    effective_schwarz = facts.achieved_schwarz_status
    result = {
        "declarer_trick_points": evidence.declarer_trick_points,
        "defender_trick_points": evidence.defender_trick_points,
        "skat_points": out_of_play_points,
        "declarer_points": facts.final_declarer_points,
        "defender_points": facts.final_defender_points,
        "winner": facts.adjudicated_winner,
        "schneider_status": facts.achieved_schneider_status,
        "schwarz_status": (
            "not_applicable"
            if effective_schwarz == "not_applicable"
            else "declarer"
            if effective_schwarz == "declarer_made_schwarz"
            else "defenders"
            if effective_schwarz == "defenders_made_schwarz"
            else "none"
        ),
        "play_prefix_summary": play_prefix_summary,
        "point_accounting": point_accounting,
        "historical_game_end_summary": historical_end_summary,
        "game_result_summary": game_result_summary,
        "game_value_summary": game_value_summary,
        "overbid_summary": overbid_summary,
        "final_settlement_summary": final_settlement_summary,
    }
    if replay.current_trick is not None:
        result["incomplete_current_trick"] = build_serializable_incomplete_trick(
            replay.current_trick
        )
    return result
