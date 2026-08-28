from dataclasses import InitVar, dataclass
from typing import Any

from skatmind.historical_game import HISTORICAL_SEATS, HistoricalGameRecord
from skatmind.replay_coaching_assessment import ReplayCoachingDecisionAssessment
from skatmind.replay_coaching_method_neutral import (
    get_replay_coaching_evidence_basis_order,
    get_replay_coaching_impact_tier_order,
    has_replay_coaching_search_immediate_divergence,
    is_replay_coaching_divergence_actionable,
    validate_supported_replay_coaching_assessment,
)
from skatmind.replay_coaching_prioritization import (
    ReplayCoachingPrioritizationResult,
    build_replay_coaching_prioritization_result,
    validate_replay_coaching_assessment_sequence,
)
from skatmind.rules import GAME_TYPES

REPLAY_COACHING_GUIDANCE_VERSION = 1
MIN_REPLAY_COACHING_PATTERN_OCCURRENCES = 2

REPLAY_COACHING_PATTERN_SCOPES = ("player", "role", "phase", "contract")
REPLAY_COACHING_PATTERN_TYPES = (
    "repeated_lower_contract_success",
    "repeated_lower_settlement_score",
    "repeated_lower_card_point_margin",
    "repeated_immediate_only_gap",
    "repeated_search_immediate_divergence",
    "repeated_aggregate_equivalent_choice",
    "repeated_forced_move",
    "repeated_search_unavailable",
)
REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES = REPLAY_COACHING_PATTERN_TYPES[:5]
REPLAY_COACHING_DESCRIPTIVE_PATTERN_TYPES = REPLAY_COACHING_PATTERN_TYPES[5:]

REPLAY_COACHING_PATTERN_FACTORS = (
    "repeated_contract_success_gap",
    "repeated_settlement_score_gap",
    "repeated_card_point_margin_gap",
    "repeated_immediate_only_gap",
    "repeated_search_immediate_divergence",
    "repeated_aggregate_equivalent_choice",
    "repeated_forced_move",
    "repeated_search_unavailable",
    "player_scope",
    "role_scope",
    "phase_scope",
    "contract_scope",
)
REPLAY_COACHING_PATTERN_LIMITATIONS = (
    "single_recorded_game_only",
    "minimum_occurrence_product_rule",
    "bounded_late_game_search",
    "determinization_strategy_fusion",
    "sampled_compatible_worlds",
    "completed_common_prefix",
    "immediate_expected_value_only",
    "search_unavailable",
    "observed_card_not_ground_truth",
    "no_tactical_motif_inference",
    "no_causal_outcome_claim",
)

def _decision_index(assessment: ReplayCoachingDecisionAssessment) -> int:
    return assessment.decision_time_evidence.decision_index


def is_replay_coaching_pattern_occurrence(
    pattern_type: str,
    assessment: ReplayCoachingDecisionAssessment,
) -> bool:
    """Applies one exact version-1 occurrence predicate."""
    if pattern_type not in REPLAY_COACHING_PATTERN_TYPES:
        raise ValueError(f"Unsupported Replay Coaching pattern type: {pattern_type}")
    validate_supported_replay_coaching_assessment(assessment)
    if pattern_type == "repeated_lower_contract_success":
        return (
            assessment.assessment_status == "strictly_below_best"
            and assessment.impact_tier == "contract_success"
        )
    if pattern_type == "repeated_lower_settlement_score":
        return (
            assessment.assessment_status == "strictly_below_best"
            and assessment.impact_tier == "settlement_score"
        )
    if pattern_type == "repeated_lower_card_point_margin":
        return (
            assessment.decision_time_evidence.game_type != "null"
            and assessment.assessment_status == "strictly_below_best"
            and assessment.impact_tier == "card_point_margin"
        )
    if pattern_type == "repeated_immediate_only_gap":
        return (
            assessment.assessment_status == "strictly_below_best"
            and assessment.impact_tier == "immediate_only"
        )
    if pattern_type == "repeated_search_immediate_divergence":
        return has_replay_coaching_search_immediate_divergence(assessment)
    if pattern_type == "repeated_aggregate_equivalent_choice":
        return (
            assessment.assessment_status == "best_or_equivalent"
            and assessment.aggregate_equivalent is True
            and assessment.actual_card != assessment.best_card
        )
    if pattern_type == "repeated_forced_move":
        return assessment.assessment_status == "forced_move"
    return "search_unavailable" in assessment.factors


def _scope_value(
    scope: str,
    assessment: ReplayCoachingDecisionAssessment,
) -> str:
    evidence = assessment.decision_time_evidence
    return {
        "player": evidence.acting_player_id,
        "role": evidence.local_side,
        "phase": evidence.game_phase,
        "contract": evidence.game_type,
    }[scope]


def _canonical_scope_values(
    record: HistoricalGameRecord,
    scope: str,
) -> tuple[str, ...]:
    if scope == "player":
        return tuple(
            next(player.player_id for player in record.players if player.seat == seat)
            for seat in HISTORICAL_SEATS
        )
    if scope == "role":
        return ("declarer", "defenders")
    if scope == "phase":
        return ("opening", "middle", "endgame")
    if scope == "contract":
        return tuple(GAME_TYPES)
    raise ValueError(f"Unsupported Replay Coaching pattern scope: {scope}")


def _count_tuple(
    occurrences: tuple[ReplayCoachingDecisionAssessment, ...],
    field_name: str,
    canonical_values: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(
        (
            value,
            sum(getattr(assessment, field_name) == value for assessment in occurrences),
        )
        for value in canonical_values
    )


def _high_impact_indices(
    prioritization: ReplayCoachingPrioritizationResult,
) -> set[int]:
    indices = {
        _decision_index(key.assessment)
        for key in prioritization.key_decisions
        if key.is_high_impact
    }
    indices.update(_decision_index(point.assessment) for point in prioritization.turning_points)
    return indices


def _pattern_factors(pattern_type: str, scope: str) -> tuple[str, ...]:
    selected = {
        REPLAY_COACHING_PATTERN_FACTORS[
            REPLAY_COACHING_PATTERN_TYPES.index(pattern_type)
        ],
        f"{scope}_scope",
    }
    return tuple(factor for factor in REPLAY_COACHING_PATTERN_FACTORS if factor in selected)


def _pattern_limitations(
    occurrences: tuple[ReplayCoachingDecisionAssessment, ...],
) -> tuple[str, ...]:
    selected = {
        "single_recorded_game_only",
        "minimum_occurrence_product_rule",
        "observed_card_not_ground_truth",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
    }
    selected.update(
        limitation
        for assessment in occurrences
        for limitation in assessment.limitations
        if limitation in REPLAY_COACHING_PATTERN_LIMITATIONS
    )
    return tuple(
        limitation
        for limitation in REPLAY_COACHING_PATTERN_LIMITATIONS
        if limitation in selected
    )


def _is_pattern_actionable(
    pattern_type: str,
    occurrences: tuple[ReplayCoachingDecisionAssessment, ...],
) -> bool:
    if pattern_type not in REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES:
        return False
    if pattern_type == "repeated_search_immediate_divergence":
        return all(
            is_replay_coaching_divergence_actionable(assessment)
            for assessment in occurrences
        )
    return True


@dataclass(frozen=True)
class ReplayCoachingPattern:
    """One repeated assessment pattern within one recorded game."""

    guidance_version: int
    source_game_id: str
    pattern_type: str
    scope: str
    scope_value: str
    game_type: str
    scope_decision_count: int
    scope_assessable_decision_count: int
    occurrence_count: int
    decision_indices: tuple[int, ...]
    key_decision_indices: tuple[int, ...]
    high_impact_decision_count: int
    evidence_basis_counts: tuple[tuple[str, int], ...]
    impact_tier_counts: tuple[tuple[str, int], ...]
    is_actionable: bool
    factors: tuple[str, ...]
    limitations: tuple[str, ...]
    record: InitVar[HistoricalGameRecord]
    assessments: InitVar[tuple[ReplayCoachingDecisionAssessment, ...]]
    prioritization: InitVar[ReplayCoachingPrioritizationResult]

    def __post_init__(
        self,
        record: HistoricalGameRecord,
        assessments: tuple[ReplayCoachingDecisionAssessment, ...],
        prioritization: ReplayCoachingPrioritizationResult,
    ) -> None:
        if (
            isinstance(self.guidance_version, bool)
            or not isinstance(self.guidance_version, int)
            or self.guidance_version != REPLAY_COACHING_GUIDANCE_VERSION
        ):
            raise ValueError("Unsupported Replay Coaching guidance version.")
        if self.pattern_type not in REPLAY_COACHING_PATTERN_TYPES:
            raise ValueError("Unsupported Replay Coaching pattern type.")
        if self.scope not in REPLAY_COACHING_PATTERN_SCOPES:
            raise ValueError("Unsupported Replay Coaching pattern scope.")
        validate_replay_coaching_assessment_sequence(record, assessments)
        if self.source_game_id != record.game_id:
            raise ValueError("Pattern source_game_id must match the source game.")
        if not isinstance(prioritization, ReplayCoachingPrioritizationResult):
            raise ValueError("prioritization must be ReplayCoachingPrioritizationResult.")
        if prioritization != build_replay_coaching_prioritization_result(
            record, assessments
        ):
            raise ValueError(
                "Pattern prioritization must match the same assessment sequence."
            )
        if self.game_type != record.declaration.game_type:
            raise ValueError("Pattern game_type must match the source game.")
        canonical_values = _canonical_scope_values(record, self.scope)
        if self.scope_value not in canonical_values:
            raise ValueError("Pattern scope_value is unsupported for the source game.")
        scoped = tuple(
            assessment
            for assessment in assessments
            if _scope_value(self.scope, assessment) == self.scope_value
        )
        occurrences = tuple(
            assessment
            for assessment in scoped
            if is_replay_coaching_pattern_occurrence(self.pattern_type, assessment)
        )
        occurrence_indices = tuple(_decision_index(item) for item in occurrences)
        if len(occurrence_indices) != len(set(occurrence_indices)):
            raise ValueError("Pattern occurrence decisions must be unique.")
        if len(occurrences) < MIN_REPLAY_COACHING_PATTERN_OCCURRENCES:
            raise ValueError("A Replay Coaching pattern requires at least two occurrences.")
        for field_name in (
            "scope_decision_count",
            "scope_assessable_decision_count",
            "occurrence_count",
            "high_impact_decision_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"Pattern {field_name} must be a non-negative integer.")
        for field_name in ("decision_indices", "key_decision_indices"):
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
                for value in values
            ):
                raise ValueError(f"Pattern {field_name} must contain positive integers.")
        for field_name in ("evidence_basis_counts", "impact_tier_counts"):
            counts = getattr(self, field_name)
            if not isinstance(counts, tuple) or any(
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or isinstance(item[1], bool)
                or not isinstance(item[1], int)
                or item[1] < 0
                for item in counts
            ):
                raise ValueError(f"Pattern {field_name} must contain canonical counts.")
        if not isinstance(self.is_actionable, bool):
            raise ValueError("Pattern is_actionable must be a boolean.")
        if not isinstance(self.factors, tuple) or not isinstance(self.limitations, tuple):
            raise TypeError("Pattern factors and limitations must be tuples.")
        key_index_set = {
            _decision_index(key.assessment) for key in prioritization.key_decisions
        }
        expected_key_indices = tuple(
            index for index in occurrence_indices if index in key_index_set
        )
        high_indices = _high_impact_indices(prioritization)
        expected_values = {
            "scope_decision_count": len(scoped),
            "scope_assessable_decision_count": sum(
                item.assessment_status != "not_assessable" for item in scoped
            ),
            "occurrence_count": len(occurrences),
            "decision_indices": occurrence_indices,
            "key_decision_indices": expected_key_indices,
            "high_impact_decision_count": sum(
                index in high_indices for index in occurrence_indices
            ),
            "evidence_basis_counts": _count_tuple(
                occurrences,
                "evidence_basis",
                get_replay_coaching_evidence_basis_order(occurrences[0]),
            ),
            "impact_tier_counts": _count_tuple(
                occurrences,
                "impact_tier",
                get_replay_coaching_impact_tier_order(occurrences[0]),
            ),
            "is_actionable": _is_pattern_actionable(
                self.pattern_type,
                occurrences,
            ),
            "factors": _pattern_factors(self.pattern_type, self.scope),
            "limitations": _pattern_limitations(occurrences),
        }
        for field_name, expected in expected_values.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"Pattern {field_name} does not reconcile with its evidence.")
        if self.pattern_type == "repeated_lower_card_point_margin" and any(
            item.decision_time_evidence.game_type == "null" for item in occurrences
        ):
            raise ValueError("Null assessments cannot create a card-point-margin pattern.")


def _build_pattern(
    record: HistoricalGameRecord,
    assessments: tuple[ReplayCoachingDecisionAssessment, ...],
    prioritization: ReplayCoachingPrioritizationResult,
    pattern_type: str,
    scope: str,
    scope_value: str,
) -> ReplayCoachingPattern | None:
    scoped = tuple(
        assessment
        for assessment in assessments
        if _scope_value(scope, assessment) == scope_value
    )
    occurrences = tuple(
        assessment
        for assessment in scoped
        if is_replay_coaching_pattern_occurrence(pattern_type, assessment)
    )
    if len(occurrences) < MIN_REPLAY_COACHING_PATTERN_OCCURRENCES:
        return None
    occurrence_indices = tuple(_decision_index(item) for item in occurrences)
    key_index_set = {
        _decision_index(key.assessment) for key in prioritization.key_decisions
    }
    high_indices = _high_impact_indices(prioritization)
    return ReplayCoachingPattern(
        guidance_version=REPLAY_COACHING_GUIDANCE_VERSION,
        source_game_id=record.game_id,
        pattern_type=pattern_type,
        scope=scope,
        scope_value=scope_value,
        game_type=record.declaration.game_type,
        scope_decision_count=len(scoped),
        scope_assessable_decision_count=sum(
            item.assessment_status != "not_assessable" for item in scoped
        ),
        occurrence_count=len(occurrences),
        decision_indices=occurrence_indices,
        key_decision_indices=tuple(
            index for index in occurrence_indices if index in key_index_set
        ),
        high_impact_decision_count=sum(
            index in high_indices for index in occurrence_indices
        ),
        evidence_basis_counts=_count_tuple(
            occurrences,
            "evidence_basis",
            get_replay_coaching_evidence_basis_order(occurrences[0]),
        ),
        impact_tier_counts=_count_tuple(
            occurrences,
            "impact_tier",
            get_replay_coaching_impact_tier_order(occurrences[0]),
        ),
        is_actionable=_is_pattern_actionable(pattern_type, occurrences),
        factors=_pattern_factors(pattern_type, scope),
        limitations=_pattern_limitations(occurrences),
        record=record,
        assessments=assessments,
        prioritization=prioritization,
    )


def get_replay_coaching_pattern_ordering_key(
    record: HistoricalGameRecord,
    pattern: ReplayCoachingPattern,
) -> tuple[int, int, int, int, int]:
    return (
        REPLAY_COACHING_PATTERN_TYPES.index(pattern.pattern_type),
        REPLAY_COACHING_PATTERN_SCOPES.index(pattern.scope),
        _canonical_scope_values(record, pattern.scope).index(pattern.scope_value),
        -pattern.occurrence_count,
        pattern.decision_indices[0],
    )


def get_replay_coaching_scope_value_order(
    record: HistoricalGameRecord,
    scope: str,
    scope_value: str,
) -> int:
    """Returns the source-record-aware canonical order for one scope value."""
    return _canonical_scope_values(record, scope).index(scope_value)


def build_replay_coaching_patterns(
    record: HistoricalGameRecord,
    assessments: tuple[ReplayCoachingDecisionAssessment, ...],
    prioritization: ReplayCoachingPrioritizationResult,
) -> tuple[ReplayCoachingPattern, ...]:
    """Builds every undeduplicated repeated pattern from one assessment sequence."""
    if not isinstance(assessments, tuple):
        raise TypeError("assessments must be a tuple.")
    validate_replay_coaching_assessment_sequence(record, assessments)
    if not isinstance(prioritization, ReplayCoachingPrioritizationResult):
        raise ValueError("prioritization must be ReplayCoachingPrioritizationResult.")
    if prioritization != build_replay_coaching_prioritization_result(
        record, assessments
    ):
        raise ValueError(
            "prioritization must be built from the same assessment sequence."
        )
    patterns = []
    for pattern_type in REPLAY_COACHING_PATTERN_TYPES:
        for scope in REPLAY_COACHING_PATTERN_SCOPES:
            for scope_value in _canonical_scope_values(record, scope):
                pattern = _build_pattern(
                    record,
                    assessments,
                    prioritization,
                    pattern_type,
                    scope,
                    scope_value,
                )
                if pattern is not None:
                    patterns.append(pattern)
    patterns.sort(key=lambda pattern: get_replay_coaching_pattern_ordering_key(record, pattern))
    return tuple(patterns)


def _serialize_counts(
    counts: tuple[tuple[str, int], ...],
    value_name: str,
) -> list[dict[str, str | int]]:
    return [{value_name: value, "count": count} for value, count in counts]


def build_serializable_replay_coaching_pattern(
    pattern: ReplayCoachingPattern,
) -> dict[str, Any]:
    return {
        "guidance_version": pattern.guidance_version,
        "source_game_id": pattern.source_game_id,
        "pattern_type": pattern.pattern_type,
        "scope": pattern.scope,
        "scope_value": pattern.scope_value,
        "game_type": pattern.game_type,
        "scope_decision_count": pattern.scope_decision_count,
        "scope_assessable_decision_count": pattern.scope_assessable_decision_count,
        "occurrence_count": pattern.occurrence_count,
        "decision_indices": list(pattern.decision_indices),
        "key_decision_indices": list(pattern.key_decision_indices),
        "high_impact_decision_count": pattern.high_impact_decision_count,
        "evidence_basis_counts": _serialize_counts(
            pattern.evidence_basis_counts, "evidence_basis"
        ),
        "impact_tier_counts": _serialize_counts(
            pattern.impact_tier_counts, "impact_tier"
        ),
        "is_actionable": pattern.is_actionable,
        "factors": list(pattern.factors),
        "limitations": list(pattern.limitations),
    }
