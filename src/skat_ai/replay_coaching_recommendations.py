from dataclasses import dataclass
from typing import Any

from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.replay_coaching_key_decisions import ReplayCoachingKeyDecision
from skat_ai.replay_coaching_patterns import (
    REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES,
    REPLAY_COACHING_GUIDANCE_VERSION,
    REPLAY_COACHING_PATTERN_LIMITATIONS,
    REPLAY_COACHING_PATTERN_SCOPES,
    ReplayCoachingPattern,
    build_serializable_replay_coaching_pattern,
    get_replay_coaching_scope_value_order,
)

MAX_REPLAY_COACHING_DECISION_RECOMMENDATIONS = 5
MAX_REPLAY_COACHING_PATTERN_RECOMMENDATIONS = 5

REPLAY_COACHING_DECISION_RECOMMENDATION_TYPES = (
    "prioritize_contract_success",
    "prefer_higher_settlement_score",
    "prefer_higher_card_point_margin",
    "review_immediate_alternative",
)
REPLAY_COACHING_PATTERN_RECOMMENDATION_TYPES = (
    "review_repeated_contract_success_gaps",
    "review_repeated_settlement_score_gaps",
    "review_repeated_card_point_margin_gaps",
    "review_repeated_immediate_only_gaps",
    "review_search_immediate_divergence",
)
REPLAY_COACHING_RECOMMENDATION_FACTORS = (
    "decision_specific",
    "repeated_pattern",
    "contract_success_priority",
    "settlement_score_priority",
    "card_point_margin_priority",
    "immediate_only_evidence",
    "search_immediate_divergence",
    "player_scope",
    "role_scope",
    "phase_scope",
    "contract_scope",
)
REPLAY_COACHING_RECOMMENDATION_LIMITATIONS = REPLAY_COACHING_PATTERN_LIMITATIONS

_NULL_OBJECTIVE_TEXT = (
    "For Null, the relevant contract objective is whether the declarer remains "
    "without a trick; card points are not a Search objective."
)


def _ordered_subset(values: tuple[str, ...], canonical: tuple[str, ...], name: str) -> None:
    if len(values) != len(set(values)) or any(value not in canonical for value in values):
        raise ValueError(f"{name} must contain unique supported values.")
    if values != tuple(value for value in canonical if value in values):
        raise ValueError(f"{name} must use deterministic canonical order.")


def _format_gap(value: float) -> str:
    return format(value, ".12g")


def _decision_recommendation_type(key_decision: ReplayCoachingKeyDecision) -> str:
    return {
        "contract_success_gap": "prioritize_contract_success",
        "settlement_score_gap": "prefer_higher_settlement_score",
        "card_point_margin_gap": "prefer_higher_card_point_margin",
        "immediate_only_gap": "review_immediate_alternative",
    }[key_decision.selection_reason]


def _recommendation_factor(recommendation_type: str) -> str:
    return {
        "prioritize_contract_success": "contract_success_priority",
        "prefer_higher_settlement_score": "settlement_score_priority",
        "prefer_higher_card_point_margin": "card_point_margin_priority",
        "review_immediate_alternative": "immediate_only_evidence",
        "review_repeated_contract_success_gaps": "contract_success_priority",
        "review_repeated_settlement_score_gaps": "settlement_score_priority",
        "review_repeated_card_point_margin_gaps": "card_point_margin_priority",
        "review_repeated_immediate_only_gaps": "immediate_only_evidence",
        "review_search_immediate_divergence": "search_immediate_divergence",
    }[recommendation_type]


def _decision_text(
    key_decision: ReplayCoachingKeyDecision,
    recommendation_type: str,
) -> tuple[str, str, str]:
    assessment = key_decision.assessment
    decision_index = assessment.decision_time_evidence.decision_index
    actual_card = assessment.actual_card
    best_card = assessment.best_card
    gap = _format_gap(key_decision.primary_gap)
    if recommendation_type == "prioritize_contract_success":
        title = f"Prioritize Contract success at decision {decision_index}"
        explanation = (
            f"The observed card {actual_card} had a lower aggregate local-side "
            f"Contract-success result than the best evaluated alternative {best_card} "
            f"(gap {gap})."
        )
        if assessment.decision_time_evidence.game_type == "null":
            explanation = f"{explanation} {_NULL_OBJECTIVE_TEXT}"
        action = (
            "Consider Contract success before settlement score when comparing the "
            "evaluated cards."
            if assessment.decision_time_evidence.game_type == "null"
            else "Consider Contract success before settlement score or card-point margin "
            "when comparing the evaluated cards."
        )
    elif recommendation_type == "prefer_higher_settlement_score":
        title = f"Compare settlement score at decision {decision_index}"
        explanation = (
            f"The Contract-success result was equivalent, while the observed card "
            f"{actual_card} had a lower mean local-side settlement score than the best "
            f"evaluated alternative {best_card} (gap {gap})."
        )
        action = (
            "Compare settlement score after Contract success."
            if assessment.decision_time_evidence.game_type == "null"
            else "Compare settlement score after Contract success and before card-point margin."
        )
    elif recommendation_type == "prefer_higher_card_point_margin":
        if assessment.decision_time_evidence.game_type == "null":
            raise ValueError("Null cannot receive card-point-margin advice.")
        title = f"Compare card-point margin at decision {decision_index}"
        explanation = (
            f"Contract success and settlement score were equivalent, while the observed "
            f"card {actual_card} had a lower mean local-side Suit or Grand card-point "
            f"margin than the best evaluated alternative {best_card} (gap {gap})."
        )
        action = "Use card-point margin as a tertiary objective."
    else:
        title = f"Review the Immediate alternative at decision {decision_index}"
        explanation = (
            f"Bounded Search did not provide an assessable actual-card comparison; the "
            f"existing one-trick Immediate analysis preferred {best_card} to the observed "
            f"card {actual_card} (objective-utility gap {gap})."
        )
        action = (
            "Review this as one-trick Immediate evidence, not as multi-trick "
            "Contract-success evidence."
        )
    return title, explanation, action


def _decision_factors(recommendation_type: str) -> tuple[str, ...]:
    selected = {"decision_specific", _recommendation_factor(recommendation_type)}
    return tuple(
        factor for factor in REPLAY_COACHING_RECOMMENDATION_FACTORS if factor in selected
    )


def _decision_limitations(key_decision: ReplayCoachingKeyDecision) -> tuple[str, ...]:
    selected = {
        *key_decision.assessment.limitations,
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
    }
    return tuple(
        limitation
        for limitation in REPLAY_COACHING_RECOMMENDATION_LIMITATIONS
        if limitation in selected
    )


@dataclass(frozen=True)
class ReplayCoachingDecisionRecommendation:
    """One fixed-template recommendation for one existing Key Decision."""

    guidance_version: int
    rank: int
    recommendation_type: str
    key_decision: ReplayCoachingKeyDecision
    title: str
    explanation: str
    action: str
    factors: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.guidance_version, bool)
            or not isinstance(self.guidance_version, int)
            or self.guidance_version != REPLAY_COACHING_GUIDANCE_VERSION
        ):
            raise ValueError("Unsupported Replay Coaching guidance version.")
        if self.recommendation_type not in REPLAY_COACHING_DECISION_RECOMMENDATION_TYPES:
            raise ValueError("Unsupported decision recommendation type.")
        if not isinstance(self.key_decision, ReplayCoachingKeyDecision):
            raise ValueError("key_decision must be ReplayCoachingKeyDecision.")
        if (
            isinstance(self.rank, bool)
            or not isinstance(self.rank, int)
            or self.rank != self.key_decision.rank
        ):
            raise ValueError("Decision recommendation rank must match its Key Decision.")
        expected_type = _decision_recommendation_type(self.key_decision)
        if self.recommendation_type != expected_type:
            raise ValueError("Decision recommendation type must match its Key Decision.")
        expected_text = _decision_text(self.key_decision, self.recommendation_type)
        if (self.title, self.explanation, self.action) != expected_text:
            raise ValueError("Decision recommendation text must use the fixed template.")
        if self.factors != _decision_factors(self.recommendation_type):
            raise ValueError("Decision recommendation factors do not reconcile.")
        if self.limitations != _decision_limitations(self.key_decision):
            raise ValueError("Decision recommendation limitations do not reconcile.")
        _ordered_subset(self.factors, REPLAY_COACHING_RECOMMENDATION_FACTORS, "factors")
        _ordered_subset(
            self.limitations,
            REPLAY_COACHING_RECOMMENDATION_LIMITATIONS,
            "limitations",
        )


def build_replay_coaching_decision_recommendations(
    key_decisions: tuple[ReplayCoachingKeyDecision, ...],
) -> tuple[ReplayCoachingDecisionRecommendation, ...]:
    """Builds exactly one recommendation for every existing Key Decision."""
    if not isinstance(key_decisions, tuple):
        raise TypeError("key_decisions must be a tuple.")
    if len(key_decisions) > MAX_REPLAY_COACHING_DECISION_RECOMMENDATIONS:
        raise ValueError("Too many decision recommendations.")
    if tuple(key.rank for key in key_decisions) != tuple(
        range(1, len(key_decisions) + 1)
    ):
        raise ValueError("Key Decision ranks must be contiguous and one-based.")
    recommendations = []
    for key_decision in key_decisions:
        recommendation_type = _decision_recommendation_type(key_decision)
        title, explanation, action = _decision_text(key_decision, recommendation_type)
        recommendations.append(
            ReplayCoachingDecisionRecommendation(
                guidance_version=REPLAY_COACHING_GUIDANCE_VERSION,
                rank=key_decision.rank,
                recommendation_type=recommendation_type,
                key_decision=key_decision,
                title=title,
                explanation=explanation,
                action=action,
                factors=_decision_factors(recommendation_type),
                limitations=_decision_limitations(key_decision),
            )
        )
    return tuple(recommendations)


def _pattern_recommendation_type(pattern: ReplayCoachingPattern) -> str:
    return REPLAY_COACHING_PATTERN_RECOMMENDATION_TYPES[
        REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES.index(pattern.pattern_type)
    ]


def _scope_text(pattern: ReplayCoachingPattern) -> str:
    if pattern.scope == "player":
        return f"for acting player '{pattern.scope_value}'"
    if pattern.scope == "role":
        return f"for the {pattern.scope_value} role"
    if pattern.scope == "phase":
        return f"in the {pattern.scope_value} phase"
    return f"for the {pattern.scope_value} contract"


def _pattern_text(
    pattern: ReplayCoachingPattern,
    recommendation_type: str,
) -> tuple[str, str, str]:
    labels = {
        "review_repeated_contract_success_gaps": (
            "Repeated Contract-success gaps",
            "showed a lower aggregate local-side Contract-success result",
            "Review these decisions together and prioritize contract preservation before "
            "lower-order objectives.",
        ),
        "review_repeated_settlement_score_gaps": (
            "Repeated settlement-score gaps",
            "showed equivalent Contract-success results and a lower mean local-side "
            "settlement score",
            "When Contract-success results are equivalent, compare mean local-side "
            "settlement score before card-point margin.",
        ),
        "review_repeated_card_point_margin_gaps": (
            "Repeated card-point-margin gaps",
            "showed equivalent Contract-success and settlement-score results and a lower "
            "Suit or Grand card-point margin",
            "Use card-point margin only after Contract success and settlement score are "
            "equivalent.",
        ),
        "review_repeated_immediate_only_gaps": (
            "Repeated Immediate-only gaps",
            "had another card preferred by the existing one-trick Immediate analysis "
            "without an assessable bounded-Search actual-card comparison",
            "Review the listed one-trick alternatives while keeping the Immediate-only "
            "evidence limitation explicit.",
        ),
        "review_search_immediate_divergence": (
            "Repeated Search-versus-Immediate divergence",
            "had different bounded-Search and Immediate recommendations; this is a review "
            "focus, not a player error",
            "Review these positions as bounded multi-trick evidence versus one-trick "
            "Immediate evidence; the divergence itself is not a player error.",
        ),
    }
    title_label, evidence_text, action = labels[recommendation_type]
    if (
        recommendation_type == "review_repeated_card_point_margin_gaps"
        and pattern.scope == "contract"
        and pattern.scope_value == "null"
    ):
        raise ValueError("Null cannot receive card-point-margin advice.")
    if (
        recommendation_type == "review_repeated_settlement_score_gaps"
        and pattern.game_type == "null"
    ):
        action = (
            "When Contract-success results are equivalent, compare mean local-side "
            "settlement score."
        )
    indices = ", ".join(str(index) for index in pattern.decision_indices)
    title = f"{title_label} {_scope_text(pattern)}"
    explanation = (
        f"Within this one recorded game, {pattern.occurrence_count} decisions "
        f"{_scope_text(pattern)} {evidence_text}: {indices}."
    )
    if (
        recommendation_type == "review_repeated_contract_success_gaps"
        and pattern.game_type == "null"
    ):
        explanation = f"{explanation} {_NULL_OBJECTIVE_TEXT}"
    return title, explanation, action


def _pattern_factors(
    pattern: ReplayCoachingPattern,
    recommendation_type: str,
) -> tuple[str, ...]:
    selected = {
        "repeated_pattern",
        _recommendation_factor(recommendation_type),
        f"{pattern.scope}_scope",
    }
    return tuple(
        factor for factor in REPLAY_COACHING_RECOMMENDATION_FACTORS if factor in selected
    )


@dataclass(frozen=True)
class ReplayCoachingPatternRecommendation:
    """One deduplicated fixed-template recommendation for an actionable pattern."""

    guidance_version: int
    rank: int
    recommendation_type: str
    pattern: ReplayCoachingPattern
    title: str
    explanation: str
    action: str
    decision_indices: tuple[int, ...]
    factors: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.guidance_version, bool)
            or not isinstance(self.guidance_version, int)
            or self.guidance_version != REPLAY_COACHING_GUIDANCE_VERSION
        ):
            raise ValueError("Unsupported Replay Coaching guidance version.")
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank <= 0:
            raise ValueError("Pattern recommendation rank must be positive.")
        if not isinstance(self.pattern, ReplayCoachingPattern) or not self.pattern.is_actionable:
            raise ValueError("Pattern recommendations require an actionable pattern.")
        expected_type = _pattern_recommendation_type(self.pattern)
        if self.recommendation_type != expected_type:
            raise ValueError("Pattern recommendation type must match its pattern.")
        if self.decision_indices != self.pattern.decision_indices:
            raise ValueError("Pattern recommendation decisions must match its pattern.")
        if not isinstance(self.decision_indices, tuple) or any(
            isinstance(index, bool) or not isinstance(index, int) or index <= 0
            for index in self.decision_indices
        ):
            raise ValueError(
                "Pattern recommendation decision_indices must contain positive integers."
            )
        if (self.title, self.explanation, self.action) != _pattern_text(
            self.pattern, self.recommendation_type
        ):
            raise ValueError("Pattern recommendation text must use the fixed template.")
        if self.factors != _pattern_factors(self.pattern, self.recommendation_type):
            raise ValueError("Pattern recommendation factors do not reconcile.")
        if self.limitations != self.pattern.limitations:
            raise ValueError("Pattern recommendations must inherit pattern limitations.")
        _ordered_subset(self.factors, REPLAY_COACHING_RECOMMENDATION_FACTORS, "factors")
        _ordered_subset(
            self.limitations,
            REPLAY_COACHING_RECOMMENDATION_LIMITATIONS,
            "limitations",
        )


def get_replay_coaching_pattern_recommendation_ordering_key(
    record: HistoricalGameRecord,
    pattern: ReplayCoachingPattern,
) -> tuple[int, int, int, int, int, int]:
    return (
        REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES.index(pattern.pattern_type),
        -pattern.high_impact_decision_count,
        -pattern.occurrence_count,
        REPLAY_COACHING_PATTERN_SCOPES.index(pattern.scope),
        pattern.decision_indices[0],
        get_replay_coaching_scope_value_order(record, pattern.scope, pattern.scope_value),
    )


def build_replay_coaching_pattern_recommendations(
    record: HistoricalGameRecord,
    patterns: tuple[ReplayCoachingPattern, ...],
) -> tuple[ReplayCoachingPatternRecommendation, ...]:
    """Ranks, evidence-deduplicates, and truncates actionable pattern advice."""
    if not isinstance(patterns, tuple):
        raise TypeError("patterns must be a tuple.")
    if any(not isinstance(pattern, ReplayCoachingPattern) for pattern in patterns):
        raise ValueError("patterns must contain ReplayCoachingPattern values.")
    if any(
        pattern.source_game_id != record.game_id
        or pattern.game_type != record.declaration.game_type
        for pattern in patterns
    ):
        raise ValueError("Pattern recommendations must belong to the source game.")
    candidates = sorted(
        (pattern for pattern in patterns if pattern.is_actionable),
        key=lambda pattern: get_replay_coaching_pattern_recommendation_ordering_key(
            record, pattern
        ),
    )
    selected = []
    evidence_keys: set[tuple[str, tuple[int, ...]]] = set()
    for pattern in candidates:
        recommendation_type = _pattern_recommendation_type(pattern)
        evidence_key = (recommendation_type, pattern.decision_indices)
        if evidence_key in evidence_keys:
            continue
        evidence_keys.add(evidence_key)
        selected.append((pattern, recommendation_type))
        if len(selected) == MAX_REPLAY_COACHING_PATTERN_RECOMMENDATIONS:
            break
    return tuple(
        ReplayCoachingPatternRecommendation(
            guidance_version=REPLAY_COACHING_GUIDANCE_VERSION,
            rank=rank,
            recommendation_type=recommendation_type,
            pattern=pattern,
            title=_pattern_text(pattern, recommendation_type)[0],
            explanation=_pattern_text(pattern, recommendation_type)[1],
            action=_pattern_text(pattern, recommendation_type)[2],
            decision_indices=tuple(pattern.decision_indices),
            factors=_pattern_factors(pattern, recommendation_type),
            limitations=tuple(pattern.limitations),
        )
        for rank, (pattern, recommendation_type) in enumerate(selected, start=1)
    )


def build_serializable_replay_coaching_decision_recommendation(
    recommendation: ReplayCoachingDecisionRecommendation,
) -> dict[str, Any]:
    from skat_ai.replay_coaching_key_decisions import (
        build_serializable_replay_coaching_key_decision,
    )

    return {
        "guidance_version": recommendation.guidance_version,
        "rank": recommendation.rank,
        "recommendation_type": recommendation.recommendation_type,
        "key_decision": build_serializable_replay_coaching_key_decision(
            recommendation.key_decision
        ),
        "title": recommendation.title,
        "explanation": recommendation.explanation,
        "action": recommendation.action,
        "factors": list(recommendation.factors),
        "limitations": list(recommendation.limitations),
    }


def build_serializable_replay_coaching_pattern_recommendation(
    recommendation: ReplayCoachingPatternRecommendation,
) -> dict[str, Any]:
    return {
        "guidance_version": recommendation.guidance_version,
        "rank": recommendation.rank,
        "recommendation_type": recommendation.recommendation_type,
        "pattern": build_serializable_replay_coaching_pattern(recommendation.pattern),
        "title": recommendation.title,
        "explanation": recommendation.explanation,
        "action": recommendation.action,
        "decision_indices": list(recommendation.decision_indices),
        "factors": list(recommendation.factors),
        "limitations": list(recommendation.limitations),
    }
