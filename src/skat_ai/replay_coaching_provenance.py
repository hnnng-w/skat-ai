from __future__ import annotations

from collections.abc import Mapping

from skat_ai.application.provenance import ApplicationProvenanceAttachment
from skat_ai.errors import SkatAIInformationPolicyError
from skat_ai.field_provenance import FieldProvenanceEntry
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.replay_coaching_assessment import (
    ReplayCoachingDecisionAssessment,
    build_serializable_replay_coaching_decision_assessment,
)
from skat_ai.replay_coaching_evidence import (
    DecisionTimeReplayCoachingEvidence,
    build_serializable_decision_time_replay_coaching_evidence,
)
from skat_ai.replay_coaching_guidance import (
    ReplayCoachingGuidanceResult,
    build_serializable_replay_coaching_guidance_result,
)
from skat_ai.replay_coaching_prioritization import (
    ReplayCoachingPrioritizationResult,
    build_serializable_replay_coaching_prioritization_result,
)
from skat_ai.replay_coaching_report import (
    ReplayCoachingReport,
    build_serializable_replay_coaching_report,
)
from skat_ai.retrospective_review_provenance import (
    _entry,
    _reference,
    build_complete_provenance_attachment,
    search_entries_for_nested_result,
    validate_retrospective_provenance_dependency,
)

REPLAY_COACHING_PROVENANCE_VERSION = 1


def _historical_context(
    *,
    stage: str,
    decision_index: int | None,
    player_id: str | None,
    side: str | None,
) -> InformationUseContext:
    return InformationUseContext(
        workflow="historical_game",
        stage=stage,
        perspective_player_id=player_id,
        perspective_side=side,
        decision_index=decision_index,
        event_index=None,
    )


def _decision_time_entry_builder(
    *,
    evidence: DecisionTimeReplayCoachingEvidence,
):
    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if tokens and tokens[0] == "legal_cards":
            origin = "rule_derived"
            derivation = "deterministic_rule"
            reference_id = "legal_card_rules"
            reference_type = "rule_contract"
        elif tokens and tokens[0] == "immediate_evidence":
            origin = "heuristic_analysis"
            derivation = "heuristic"
            reference_id = "immediate_expected_value"
            reference_type = "algorithm"
        elif tokens and tokens[0] == "search_vs_immediate_comparison":
            origin = "search_derived"
            derivation = "deterministic_rule"
            reference_id = "search_vs_immediate_comparison"
            reference_type = "algorithm"
        else:
            origin = "historical_replay"
            derivation = "reconstruction"
            reference_id = "historical_search_review"
            reference_type = "algorithm"
        return _entry(
            path,
            origin=origin,
            visibility="public",
            available_from="current_decision",
            derivation=derivation,
            decision_index=evidence.decision_index,
            perspective_player_id=evidence.acting_player_id,
            source_references=(_reference(reference_type, reference_id),),
        )

    return build


def build_replay_coaching_decision_time_attachment(
    *,
    name: str,
    evidence: DecisionTimeReplayCoachingEvidence,
    document_prefix: str | None = None,
) -> ApplicationProvenanceAttachment:
    """Builds complete pre-actual provenance from retained Coaching evidence."""
    document = build_serializable_decision_time_replay_coaching_evidence(evidence)
    if document_prefix is not None:
        document = {document_prefix: document}
        search_path = f"/{document_prefix}/bounded_search_result"
    else:
        search_path = "/bounded_search_result"
    overrides = search_entries_for_nested_result(
        evidence.bounded_search_result,
        field_path=search_path,
        decision_index=evidence.decision_index,
        perspective_player_id=evidence.acting_player_id,
    )
    return build_complete_provenance_attachment(
        name=name,
        document_role="result",
        document=document,
        information_use_context=_historical_context(
            stage="decision_time",
            decision_index=evidence.decision_index,
            player_id=evidence.acting_player_id,
            side=evidence.local_side,
        ),
        entry_builder=_decision_time_entry_builder(evidence=evidence),
        override_entries=overrides,
    )


def _assessment_entry_builder(
    *,
    assessment: ReplayCoachingDecisionAssessment,
):
    evidence = assessment.decision_time_evidence

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        evidence_index = tokens.index("decision_time_evidence") if (
            "decision_time_evidence" in tokens
        ) else None
        if evidence_index is not None:
            return _decision_time_entry_builder(evidence=evidence)(path, tokens)
        is_actual = tokens[-1] in {"actual_card", "actual_card_played"}
        return _entry(
            path,
            origin="retrospective_attachment" if is_actual else "heuristic_analysis",
            visibility="public",
            available_from="after_actual_play",
            derivation="retrospective" if is_actual else "heuristic",
            decision_index=evidence.decision_index,
            perspective_player_id=evidence.acting_player_id,
            source_references=(
                _reference(
                    "retrospective_observation" if is_actual else "algorithm",
                    "historical_actual_card" if is_actual else "replay_coaching_assessment",
                ),
            ),
        )

    return build


def build_replay_coaching_assessment_attachment(
    *,
    name: str,
    assessment: ReplayCoachingDecisionAssessment,
    document_prefix: str | None = None,
) -> ApplicationProvenanceAttachment:
    """Builds complete after-actual provenance from one retained assessment."""
    validate_retrospective_provenance_dependency(
        consumer_stage="retrospective_assessment",
        dependency_stage="actual_card_attachment",
        path=f"/{name}",
    )
    evidence = assessment.decision_time_evidence
    document = build_serializable_replay_coaching_decision_assessment(assessment)
    if document_prefix is not None:
        document = {document_prefix: document}
        search_path = (
            f"/{document_prefix}/decision_time_evidence/bounded_search_result"
        )
    else:
        search_path = "/decision_time_evidence/bounded_search_result"
    overrides = search_entries_for_nested_result(
        evidence.bounded_search_result,
        field_path=search_path,
        decision_index=evidence.decision_index,
        perspective_player_id=evidence.acting_player_id,
    )
    return build_complete_provenance_attachment(
        name=name,
        document_role="result",
        document=document,
        information_use_context=_historical_context(
            stage="after_actual_play",
            decision_index=evidence.decision_index,
            player_id=evidence.acting_player_id,
            side=evidence.local_side,
        ),
        entry_builder=_assessment_entry_builder(assessment=assessment),
        override_entries=overrides,
    )


def _offline_entry(
    path: str,
    _tokens: tuple[str, ...],
    *,
    algorithm: str,
) -> FieldProvenanceEntry:
    return _entry(
        path,
        origin="heuristic_analysis",
        visibility="public",
        available_from="offline_review",
        derivation="heuristic",
        decision_index=None,
        perspective_player_id=None,
        source_references=(_reference("algorithm", algorithm),),
    )


def build_replay_coaching_prioritization_attachment(
    result: ReplayCoachingPrioritizationResult,
) -> ApplicationProvenanceAttachment:
    """Builds complete offline provenance for Key Decisions and Turning Points."""
    document = build_serializable_replay_coaching_prioritization_result(result)
    if "outcome_context" in document:
        raise SkatAIInformationPolicyError(
            "Outcome Context cannot feed Replay Coaching prioritization.",
            path="/outcome_context",
        )
    return build_complete_provenance_attachment(
        name="replay_coaching/prioritization",
        document_role="result",
        document=document,
        information_use_context=_historical_context(
            stage="offline_review",
            decision_index=result.decision_count,
            player_id=None,
            side=None,
        ),
        entry_builder=lambda path, tokens: _offline_entry(
            path,
            tokens,
            algorithm="replay_coaching_prioritization_v1",
        ),
    )


def build_replay_coaching_guidance_attachment(
    result: ReplayCoachingGuidanceResult,
) -> ApplicationProvenanceAttachment:
    """Builds complete offline provenance for patterns and recommendations."""
    validate_retrospective_provenance_dependency(
        consumer_stage="guidance",
        dependency_stage="prioritization",
        path="/replay_coaching/guidance",
    )
    document = build_serializable_replay_coaching_guidance_result(result)
    if "outcome_context" in document:
        raise SkatAIInformationPolicyError(
            "Outcome Context cannot feed Replay Coaching guidance.",
            path="/outcome_context",
        )
    return build_complete_provenance_attachment(
        name="replay_coaching/guidance",
        document_role="result",
        document=document,
        information_use_context=_historical_context(
            stage="offline_review",
            decision_index=result.decision_count,
            player_id=None,
            side=None,
        ),
        entry_builder=lambda path, tokens: _offline_entry(
            path,
            tokens,
            algorithm="replay_coaching_guidance_v1",
        ),
    )


def _report_entry_builder(
    *,
    document: Mapping[str, object],
):
    assessment_rows = document.get("decision_assessments")

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if tokens and tokens[0] == "outcome_context":
            return _entry(
                path,
                origin="rule_derived",
                visibility="post_game_only",
                available_from="game_end",
                derivation="deterministic_rule",
                decision_index=None,
                perspective_player_id=None,
                source_references=(_reference("aggregate", "final_outcome_context"),),
            )
        if (
            len(tokens) >= 2
            and tokens[0] == "decision_assessments"
            and tokens[1].isdecimal()
            and isinstance(assessment_rows, (list, tuple))
        ):
            row = assessment_rows[int(tokens[1])]
            decision_index = row["decision_time_evidence"]["decision_index"]
            acting_player_id = row["decision_time_evidence"]["acting_player_id"]
            if "decision_time_evidence" in tokens:
                return _entry(
                    path,
                    origin="search_derived",
                    visibility="public",
                    available_from="current_decision",
                    derivation="direct",
                    decision_index=decision_index,
                    perspective_player_id=acting_player_id,
                    source_references=(
                        _reference("algorithm", "historical_search_review"),
                    ),
                )
            is_actual = tokens[-1] == "actual_card"
            return _entry(
                path,
                origin=(
                    "retrospective_attachment" if is_actual else "heuristic_analysis"
                ),
                visibility="public",
                available_from="after_actual_play",
                derivation="retrospective" if is_actual else "heuristic",
                decision_index=decision_index,
                perspective_player_id=acting_player_id,
                source_references=(
                    _reference(
                        "retrospective_observation" if is_actual else "algorithm",
                        "historical_actual_card" if is_actual else "replay_coaching_assessment",
                    ),
                ),
            )
        if tokens and tokens[0] == "game_context":
            return _entry(
                path,
                origin="historical_replay",
                visibility="public",
                available_from="game_end",
                derivation="reconstruction",
                decision_index=None,
                perspective_player_id=None,
                source_references=(
                    _reference("algorithm", "historical_replay_coaching_v1"),
                ),
            )
        return _offline_entry(
            path,
            tokens,
            algorithm="historical_replay_coaching_v1",
        )

    return build


def build_replay_coaching_report_attachment(
    report: ReplayCoachingReport,
) -> ApplicationProvenanceAttachment:
    """Builds a complete ledger over the exact existing serialized report."""
    validate_retrospective_provenance_dependency(
        consumer_stage="final_report",
        dependency_stage="guidance",
        path="/replay_coaching/report",
    )
    document = build_serializable_replay_coaching_report(report)
    return build_complete_provenance_attachment(
        name="replay_coaching/report",
        document_role="result",
        document=document,
        information_use_context=_historical_context(
            stage="offline_review",
            decision_index=len(report.decision_assessments),
            player_id=None,
            side=None,
        ),
        entry_builder=_report_entry_builder(document=document),
    )
