from collections.abc import Callable
from dataclasses import InitVar, dataclass
from typing import Any

from skatmind.historical_game import HistoricalGameRecord
from skatmind.replay_coaching_assessment import ReplayCoachingDecisionAssessment
from skatmind.replay_coaching_patterns import (
    REPLAY_COACHING_GUIDANCE_VERSION,
    ReplayCoachingPattern,
    build_replay_coaching_patterns,
    build_serializable_replay_coaching_pattern,
)
from skatmind.replay_coaching_prioritization import (
    ReplayCoachingPrioritizationResult,
    build_replay_coaching_prioritization_result,
    build_serializable_replay_coaching_prioritization_result,
    validate_replay_coaching_assessment_sequence,
)
from skatmind.replay_coaching_recommendations import (
    MAX_REPLAY_COACHING_DECISION_RECOMMENDATIONS,
    MAX_REPLAY_COACHING_PATTERN_RECOMMENDATIONS,
    ReplayCoachingDecisionRecommendation,
    ReplayCoachingPatternRecommendation,
    build_replay_coaching_decision_recommendations,
    build_replay_coaching_pattern_recommendations,
    build_serializable_replay_coaching_decision_recommendation,
    build_serializable_replay_coaching_pattern_recommendation,
)


@dataclass(frozen=True)
class ReplayCoachingGuidanceResult:
    """One immutable internal guidance composition for one recorded game."""

    guidance_version: int
    source_game_id: str
    decision_count: int
    pattern_count: int
    actionable_pattern_count: int
    decision_recommendation_count: int
    pattern_recommendation_count: int
    prioritization: ReplayCoachingPrioritizationResult
    patterns: tuple[ReplayCoachingPattern, ...]
    decision_recommendations: tuple[ReplayCoachingDecisionRecommendation, ...]
    pattern_recommendations: tuple[ReplayCoachingPatternRecommendation, ...]
    record: InitVar[HistoricalGameRecord]
    assessments: InitVar[tuple[ReplayCoachingDecisionAssessment, ...]]

    def __post_init__(
        self,
        record: HistoricalGameRecord,
        assessments: tuple[ReplayCoachingDecisionAssessment, ...],
    ) -> None:
        if (
            isinstance(self.guidance_version, bool)
            or not isinstance(self.guidance_version, int)
            or self.guidance_version != REPLAY_COACHING_GUIDANCE_VERSION
        ):
            raise ValueError("Unsupported Replay Coaching guidance version.")
        validate_replay_coaching_assessment_sequence(record, assessments)
        if self.source_game_id != record.game_id:
            raise ValueError("Guidance source_game_id must match the historical record.")
        expected_prioritization = build_replay_coaching_prioritization_result(
            record, assessments
        )
        if self.prioritization != expected_prioritization:
            raise ValueError(
                "Guidance prioritization must match the same assessment sequence."
            )
        expected_patterns = build_replay_coaching_patterns(
            record, assessments, self.prioritization
        )
        expected_decision_recommendations = (
            build_replay_coaching_decision_recommendations(
                self.prioritization.key_decisions
            )
        )
        expected_pattern_recommendations = (
            build_replay_coaching_pattern_recommendations(record, expected_patterns)
        )
        expected_counts = {
            "decision_count": len(assessments),
            "pattern_count": len(expected_patterns),
            "actionable_pattern_count": sum(
                pattern.is_actionable for pattern in expected_patterns
            ),
            "decision_recommendation_count": len(
                expected_decision_recommendations
            ),
            "pattern_recommendation_count": len(expected_pattern_recommendations),
        }
        for field_name, expected in expected_counts.items():
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value != expected:
                raise ValueError(f"Guidance {field_name} does not reconcile.")
        if not isinstance(self.patterns, tuple) or self.patterns != expected_patterns:
            raise ValueError("Guidance patterns are not complete and canonically ordered.")
        if (
            not isinstance(self.decision_recommendations, tuple)
            or self.decision_recommendations != expected_decision_recommendations
        ):
            raise ValueError(
                "Guidance decision recommendations must align with all Key Decisions."
            )
        if (
            not isinstance(self.pattern_recommendations, tuple)
            or self.pattern_recommendations != expected_pattern_recommendations
        ):
            raise ValueError(
                "Guidance pattern recommendations must be ranked and deduplicated."
            )
        if len(self.decision_recommendations) > (
            MAX_REPLAY_COACHING_DECISION_RECOMMENDATIONS
        ):
            raise ValueError("Too many guidance decision recommendations.")
        if len(self.pattern_recommendations) > (
            MAX_REPLAY_COACHING_PATTERN_RECOMMENDATIONS
        ):
            raise ValueError("Too many guidance pattern recommendations.")


def build_replay_coaching_guidance(
    record: HistoricalGameRecord,
    assessments: tuple[ReplayCoachingDecisionAssessment, ...],
    prioritization: ReplayCoachingPrioritizationResult,
) -> ReplayCoachingGuidanceResult:
    """Builds internal patterns and recommendations without running analysis."""
    if not isinstance(assessments, tuple):
        raise TypeError("assessments must be a tuple.")
    validate_replay_coaching_assessment_sequence(record, assessments)
    expected_prioritization = build_replay_coaching_prioritization_result(
        record, assessments
    )
    if prioritization != expected_prioritization:
        raise ValueError(
            "prioritization must be built from the same record and assessment sequence."
        )
    patterns = build_replay_coaching_patterns(record, assessments, prioritization)
    decision_recommendations = build_replay_coaching_decision_recommendations(
        prioritization.key_decisions
    )
    pattern_recommendations = build_replay_coaching_pattern_recommendations(
        record, patterns
    )
    return ReplayCoachingGuidanceResult(
        guidance_version=REPLAY_COACHING_GUIDANCE_VERSION,
        source_game_id=record.game_id,
        decision_count=len(assessments),
        pattern_count=len(patterns),
        actionable_pattern_count=sum(pattern.is_actionable for pattern in patterns),
        decision_recommendation_count=len(decision_recommendations),
        pattern_recommendation_count=len(pattern_recommendations),
        prioritization=prioritization,
        patterns=patterns,
        decision_recommendations=decision_recommendations,
        pattern_recommendations=pattern_recommendations,
        record=record,
        assessments=assessments,
    )


def build_serializable_replay_coaching_guidance_result(
    result: ReplayCoachingGuidanceResult,
    *,
    assessment_serializer: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "guidance_version": result.guidance_version,
        "source_game_id": result.source_game_id,
        "decision_count": result.decision_count,
        "pattern_count": result.pattern_count,
        "actionable_pattern_count": result.actionable_pattern_count,
        "decision_recommendation_count": result.decision_recommendation_count,
        "pattern_recommendation_count": result.pattern_recommendation_count,
        "prioritization": build_serializable_replay_coaching_prioritization_result(
            result.prioritization,
            assessment_serializer=assessment_serializer,
        ),
        "patterns": [
            build_serializable_replay_coaching_pattern(pattern)
            for pattern in result.patterns
        ],
        "decision_recommendations": [
            build_serializable_replay_coaching_decision_recommendation(
                recommendation,
                assessment_serializer=assessment_serializer,
            )
            for recommendation in result.decision_recommendations
        ],
        "pattern_recommendations": [
            build_serializable_replay_coaching_pattern_recommendation(recommendation)
            for recommendation in result.pattern_recommendations
        ],
    }
