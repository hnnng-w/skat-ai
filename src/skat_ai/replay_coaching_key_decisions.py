import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skat_ai.replay_coaching_evidence import REPLAY_COACHING_CONTRACT_VERSION
from skat_ai.replay_coaching_method_neutral import (
    get_replay_coaching_assessment_version,
    get_replay_coaching_evidence_basis_order,
    get_replay_coaching_primary_gap_value,
    validate_supported_replay_coaching_assessment,
)

REPLAY_COACHING_PRIORITIZATION_VERSION = 1
MAX_REPLAY_COACHING_KEY_DECISIONS = 5

REPLAY_COACHING_KEY_DECISION_SELECTION_REASONS = (
    "contract_success_gap",
    "settlement_score_gap",
    "card_point_margin_gap",
    "immediate_only_gap",
)
REPLAY_COACHING_TURNING_POINT_TYPES = (
    "decision_opportunity",
    "recorded_outcome",
)


def get_replay_coaching_primary_gap(
    assessment: Any,
) -> float:
    """Returns the existing objective-aligned positive gap for one eligible decision."""
    return get_replay_coaching_primary_gap_value(assessment)


def _selection_reason(assessment: Any) -> str:
    return {
        "contract_success": "contract_success_gap",
        "settlement_score": "settlement_score_gap",
        "card_point_margin": "card_point_margin_gap",
        "immediate_only": "immediate_only_gap",
    }[assessment.impact_tier]


def get_replay_coaching_key_decision_ranking_key(
    assessment: Any,
) -> tuple[int, int, float, int, int]:
    reason = _selection_reason(assessment)
    evidence = assessment.evidence_basis
    return (
        REPLAY_COACHING_KEY_DECISION_SELECTION_REASONS.index(reason),
        get_replay_coaching_evidence_basis_order(assessment).index(evidence),
        -get_replay_coaching_primary_gap(assessment),
        -int(assessment.strictly_better_card_count),
        assessment.decision_time_evidence.decision_index,
    )


@dataclass(frozen=True)
class ReplayCoachingKeyDecision:
    """One deterministically ranked missed-impact card decision."""

    prioritization_version: int
    rank: int
    assessment: Any
    selection_reason: str
    primary_gap: float
    is_high_impact: bool
    turning_point_types: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.prioritization_version, bool)
            or not isinstance(self.prioritization_version, int)
            or self.prioritization_version != REPLAY_COACHING_PRIORITIZATION_VERSION
        ):
            raise ValueError("Unsupported replay-coaching prioritization version.")
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank <= 0:
            raise ValueError("Key Decision rank must be a positive integer.")
        validate_supported_replay_coaching_assessment(self.assessment)
        if (
            get_replay_coaching_assessment_version(self.assessment)
            != REPLAY_COACHING_CONTRACT_VERSION
        ):
            raise ValueError("Key Decision assessment contract version is unsupported.")
        if self.assessment.assessment_status != "strictly_below_best":
            raise ValueError("Key Decisions require strictly_below_best assessments.")
        expected_reason = _selection_reason(self.assessment)
        if self.selection_reason != expected_reason:
            raise ValueError("selection_reason does not match the assessment impact.")
        if (
            isinstance(self.primary_gap, bool)
            or not isinstance(self.primary_gap, (int, float))
            or not math.isfinite(self.primary_gap)
            or self.primary_gap <= 0
        ):
            raise ValueError("primary_gap must be a finite positive number.")
        expected_gap = get_replay_coaching_primary_gap(self.assessment)
        if self.primary_gap != expected_gap:
            raise ValueError("primary_gap does not match the existing assessment evidence.")
        if not isinstance(self.is_high_impact, bool):
            raise ValueError("is_high_impact must be a boolean.")
        if not isinstance(self.turning_point_types, tuple):
            raise TypeError("turning_point_types must be a tuple.")
        if len(self.turning_point_types) != len(set(self.turning_point_types)):
            raise ValueError("turning_point_types must be unique.")
        expected_types = tuple(
            value
            for value in REPLAY_COACHING_TURNING_POINT_TYPES
            if value in self.turning_point_types
        )
        if self.turning_point_types != expected_types:
            raise ValueError("turning_point_types must use canonical order.")
        expected_high_impact = (
            self.assessment.impact_tier == "contract_success"
            or "recorded_outcome" in self.turning_point_types
        )
        if self.is_high_impact != expected_high_impact:
            raise ValueError("is_high_impact does not match Key Decision semantics.")


def build_replay_coaching_key_decisions(
    assessments: tuple[Any, ...],
    turning_point_types_by_decision: dict[int, tuple[str, ...]],
) -> tuple[ReplayCoachingKeyDecision, ...]:
    """Selects and ranks at most five eligible assessments."""
    if not isinstance(assessments, tuple):
        raise TypeError("assessments must be a tuple.")
    eligible = sorted(
        (
            assessment
            for assessment in assessments
            if assessment.assessment_status == "strictly_below_best"
            and assessment.impact_tier
            in {"contract_success", "settlement_score", "card_point_margin", "immediate_only"}
        ),
        key=get_replay_coaching_key_decision_ranking_key,
    )[:MAX_REPLAY_COACHING_KEY_DECISIONS]
    return tuple(
        ReplayCoachingKeyDecision(
            prioritization_version=REPLAY_COACHING_PRIORITIZATION_VERSION,
            rank=rank,
            assessment=assessment,
            selection_reason=_selection_reason(assessment),
            primary_gap=get_replay_coaching_primary_gap(assessment),
            is_high_impact=(
                assessment.impact_tier == "contract_success"
                or "recorded_outcome"
                in turning_point_types_by_decision.get(
                    assessment.decision_time_evidence.decision_index, ()
                )
            ),
            turning_point_types=tuple(
                turning_point_types_by_decision.get(
                    assessment.decision_time_evidence.decision_index, ()
                )
            ),
        )
        for rank, assessment in enumerate(eligible, start=1)
    )


def build_serializable_replay_coaching_key_decision(
    key_decision: ReplayCoachingKeyDecision,
    *,
    assessment_serializer: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from skat_ai.replay_coaching_assessment import (
        build_serializable_replay_coaching_decision_assessment,
    )

    serializer = assessment_serializer or (
        build_serializable_replay_coaching_decision_assessment
    )
    return {
        "prioritization_version": key_decision.prioritization_version,
        "rank": key_decision.rank,
        "assessment": serializer(key_decision.assessment),
        "selection_reason": key_decision.selection_reason,
        "primary_gap": key_decision.primary_gap,
        "is_high_impact": key_decision.is_high_impact,
        "turning_point_types": list(key_decision.turning_point_types),
    }
