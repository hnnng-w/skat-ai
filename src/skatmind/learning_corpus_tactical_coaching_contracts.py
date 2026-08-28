from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Final

from skatmind.deck import get_full_deck
from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_tactical_motif_evidence import (
    LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS,
    LEARNING_CORPUS_TACTICAL_MOTIF_PHASES,
    LEARNING_CORPUS_TACTICAL_MOTIF_ROLES,
    LEARNING_CORPUS_TACTICAL_MOTIF_SEATS,
)
from skatmind.learning_corpus_tactical_motif_summary import (
    LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_SCOPES,
)
from skatmind.recommendation_workflow import FLAT_RECOMMENDATION_METHODS
from skatmind.replay_coaching_assessment import REPLAY_COACHING_IMPACT_TIERS
from skatmind.tactical_motif_contracts import (
    TACTICAL_MOTIF_FAMILY_BY_TYPE,
    TACTICAL_MOTIF_TYPES,
)

LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_VERSION = 1
LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_VERSION = 1
LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_VERSION = 1
LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_VERSION = 1
LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_VERSION = 1
LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_VERSION = 1
LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_ARTIFACTS_VERSION = 1

LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_METHOD = (
    "learning_corpus_tactical_cross_game_coaching_v1"
)

LEARNING_CORPUS_TACTICAL_COACHING_ASSESSMENT_SCOPES: Final[tuple[str, ...]] = (
    "complete_search",
    "completed_common_prefix",
    "immediate_only",
    "none",
)
LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_BASES: Final[tuple[str, ...]] = (
    "bounded_search_single_exact_world",
    "bounded_search_all_compatible_worlds",
    "bounded_search_sampled_compatible_worlds",
    "bounded_search_completed_common_prefix",
    "information_set_single_exact_world",
    "information_set_all_compatible_worlds",
    "information_set_sampled_compatible_worlds",
    "immediate_expected_value",
    "none",
)
LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_STATUSES: Final[
    tuple[str, ...]
] = (
    "forced_move",
    "best_or_equivalent",
    "strictly_below_best",
    "not_assessable",
)
LEARNING_CORPUS_TACTICAL_COACHING_DECISION_STATUSES: Final[tuple[str, ...]] = (
    "forced_move",
    "no_teacher",
    "not_assessable",
    "best_or_equivalent",
    "strictly_below_best",
    "mixed",
)
LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_STATUSES: Final[
    tuple[str, ...]
] = (
    "empty",
    "insufficient_evidence",
    "available",
)
LEARNING_CORPUS_TACTICAL_COACHING_IMPACT_TIERS: Final[tuple[str, ...]] = tuple(
    REPLAY_COACHING_IMPACT_TIERS
)
LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES: Final[tuple[str, ...]] = (
    "contract_success",
    "settlement_score",
    "card_point_margin",
    "mixed",
)
LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_CODES: Final[tuple[str, ...]] = (
    "review_repeated_contract_success_gap",
    "review_repeated_settlement_score_gap",
    "review_repeated_card_point_margin_gap",
    "review_repeated_mixed_search_gap",
)
LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_TEXT_BY_CODE: Final[dict[str, str]] = {
    "review_repeated_contract_success_gap": (
        "Review these repeated Decisions because every distinct semantic complete-Search "
        "Teacher ranked the observed Card below at least one alternative on retained "
        "contract-success impact."
    ),
    "review_repeated_settlement_score_gap": (
        "Review these repeated Decisions because every distinct semantic complete-Search "
        "Teacher ranked the observed Card below at least one alternative on retained "
        "settlement-score impact."
    ),
    "review_repeated_card_point_margin_gap": (
        "Review these repeated Decisions because every distinct semantic complete-Search "
        "Teacher ranked the observed Card below at least one alternative on retained "
        "card-point-margin impact."
    ),
    "review_repeated_mixed_search_gap": (
        "Review these repeated Decisions because every distinct semantic complete-Search "
        "Teacher ranked the observed Card below at least one alternative across retained "
        "Search-impact components."
    ),
}

LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_DECISIONS = 2
LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_GAMES = 2
LEARNING_CORPUS_TACTICAL_COACHING_MAXIMUM_FOCUS_AREAS_PER_PLAYER = 5

LEARNING_CORPUS_TACTICAL_COACHING_SOURCE_POLICY = (
    "explicit_current_snapshot_tactical_and_strategy_sources"
)
LEARNING_CORPUS_TACTICAL_COACHING_JOIN_POLICY = (
    "exact_snapshot_scoped_decision_reference_join"
)
LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_POLICY = (
    "one_assessment_per_exact_teacher_report_without_preference"
)
LEARNING_CORPUS_TACTICAL_COACHING_SEMANTIC_POLICY = (
    "semantic_duplicate_reports_do_not_multiply_decision_consensus"
)
LEARNING_CORPUS_TACTICAL_COACHING_ACTIONABLE_POLICY = (
    "complete_search_teacher_evidence_only_for_actionable_focus"
)
LEARNING_CORPUS_TACTICAL_COACHING_CONSENSUS_POLICY = (
    "all_distinct_semantic_complete_search_teachers_must_agree"
)
LEARNING_CORPUS_TACTICAL_COACHING_RECURRENCE_POLICY = (
    "repeated_below_best_decisions_across_at_least_two_games"
)
LEARNING_CORPUS_TACTICAL_COACHING_PRIORITY_POLICY = (
    "existing_objective_priority_without_teacher_preference"
)
LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_POLICY = (
    "fixed_template_review_guidance_without_trait_or_causal_claim"
)
LEARNING_CORPUS_TACTICAL_COACHING_ACTUAL_CARD_POLICY = (
    "observed_behavior_not_ground_truth"
)
LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_SEPARATION_POLICY = (
    "human_strategy_and_tactical_evidence_remain_separate"
)
LEARNING_CORPUS_TACTICAL_COACHING_DATASET_POLICY = (
    "no_learning_dataset_v2_or_existing_summary_mutation"
)
LEARNING_CORPUS_TACTICAL_COACHING_PREPARATION_POLICY = (
    "process_local_explicit_generation_safe_preparation"
)
LEARNING_CORPUS_TACTICAL_COACHING_EXPORT_POLICY = (
    "deterministic_path_free_private_json"
)
LEARNING_CORPUS_TACTICAL_COACHING_PUBLIC_POLICY = (
    "private_dashboard_counts_and_authenticated_download"
)

LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_LIMITATIONS: Final[
    tuple[str, ...]
] = (
    "current_match_snapshots_only",
    "tactical_motifs_are_structural_observations",
    "strategy_teacher_evidence_is_method_bound_not_ground_truth",
    "actual_card_not_ground_truth",
    "multiple_teacher_reports_without_preference",
    "semantic_duplicates_do_not_increase_decision_weight",
    "complete_search_only_for_actionable_focus",
    "selected_world_and_sampling_scope_remain_bounded",
    "sampled_worlds_are_not_calibrated_probability",
    "fixed_opponent_policy_model",
    "no_equilibrium_or_global_optimality_claim",
    "focus_threshold_is_not_statistical_significance",
    "no_player_trait_rating_strength_or_weakness",
    "no_intent_signaling_or_communication_claim",
    "no_commentary_or_response_interpretation",
    "no_causal_outcome_claim",
    "no_model_training_or_dataset_mutation",
)

LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_coaching_teacher_assessment_v1\0"
)
LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_coaching_decision_summary_v1\0"
)
LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_coaching_focus_area_v1\0"
)
LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_coaching_player_report_v1\0"
)
LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_FINGERPRINT_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_cross_game_coaching_report_v1\0"
)
LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_cross_game_coaching_export_v1\0"
)

_VALID_CARDS = frozenset(get_full_deck())
_DECISION_CONSENSUS_IMPACT_VALUES = (
    *LEARNING_CORPUS_TACTICAL_COACHING_IMPACT_TIERS,
    "mixed",
)


def _build_coaching_identifier_v1(domain: bytes, value: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(value)
    ).hexdigest()


def _identity_material_v1(value: object, identity_field: str) -> dict[str, Any]:
    material = value.to_dict()
    del material[identity_field]
    return material


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_count(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_positive_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _require_boolean(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _require_optional_number(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number or null.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{field_name} must be finite.")
    return converted


def _require_string_tuple(
    value: object,
    field_name: str,
    *,
    hashes: bool = False,
    unique: bool = True,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for item in value:
        (_require_hash if hashes else _require_identifier)(item, field_name)
    if unique and len(value) != len(set(value)):
        raise ValueError(f"{field_name} must contain unique values.")
    return value


def _require_canonical_counts(
    value: object,
    field_name: str,
    canonical_values: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    if type(value) is not tuple or any(
        type(item) is not tuple or len(item) != 2 for item in value
    ):
        raise ValueError(f"{field_name} must contain immutable Count pairs.")
    if tuple(item[0] for item in value) != canonical_values:
        raise ValueError(f"{field_name} must follow canonical order.")
    for _, count in value:
        _require_count(count, field_name)
    return value


def _serialize_counts(
    values: tuple[tuple[str, int], ...],
    category_name: str,
) -> list[dict[str, int | str]]:
    return [{category_name: category, "count": count} for category, count in values]


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalCoachingTeacherAssessmentV1:
    learning_corpus_tactical_coaching_teacher_assessment_version: int
    teacher_assessment_id: str
    tactical_motif_evidence_id: str
    strategy_teacher_evidence_id: str
    teacher_semantic_fingerprint: str
    match_snapshot_id: str
    game_reference_id: str
    decision_reference_id: str
    match_id: str
    game_id: str
    decision_index: int
    acting_player_id: str
    actual_card_played: str
    requested_method: str
    effective_method: str
    assessment_scope: str
    evidence_basis: str
    assessment_status: str
    impact_tier: str
    best_card: str | None
    actual_card_rank: int | None
    best_card_rank: int | None
    strictly_better_card_count: int | None
    aggregate_equivalent: bool | None
    contract_success_rate_gap: float | None
    mean_local_side_game_score_gap: float | None
    mean_local_side_card_point_margin_gap: float | None
    immediate_expected_point_swing_gap: float | None
    eligible_for_focus: bool

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalCoachingTeacherAssessmentV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalCoachingTeacherAssessmentV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_coaching_teacher_assessment_version,
            LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_VERSION,
            "learning_corpus_tactical_coaching_teacher_assessment_version",
        )
        for field_name in (
            "teacher_assessment_id",
            "tactical_motif_evidence_id",
            "strategy_teacher_evidence_id",
            "teacher_semantic_fingerprint",
            "match_snapshot_id",
            "game_reference_id",
            "decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in ("match_id", "game_id", "acting_player_id"):
            _require_identifier(getattr(self, field_name), field_name)
        _require_positive_integer(self.decision_index, "decision_index")
        if self.actual_card_played not in _VALID_CARDS:
            raise ValueError("actual_card_played must be one valid Skat Card.")
        if self.requested_method not in FLAT_RECOMMENDATION_METHODS:
            raise ValueError("requested_method must be canonical.")
        _require_identifier(self.effective_method, "effective_method")
        if self.assessment_scope not in LEARNING_CORPUS_TACTICAL_COACHING_ASSESSMENT_SCOPES:
            raise ValueError("assessment_scope must be canonical.")
        if self.evidence_basis not in LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_BASES:
            raise ValueError("evidence_basis must be canonical.")
        if (
            self.assessment_status
            not in LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_STATUSES
        ):
            raise ValueError("assessment_status must be canonical.")
        if self.impact_tier not in LEARNING_CORPUS_TACTICAL_COACHING_IMPACT_TIERS:
            raise ValueError("impact_tier must be canonical.")
        if self.best_card is not None and self.best_card not in _VALID_CARDS:
            raise ValueError("best_card must be one valid Skat Card or null.")
        for field_name in ("actual_card_rank", "best_card_rank"):
            value = getattr(self, field_name)
            if value is not None:
                _require_positive_integer(value, field_name)
        if self.strictly_better_card_count is not None:
            _require_count(self.strictly_better_card_count, "strictly_better_card_count")
        if self.aggregate_equivalent is not None:
            _require_boolean(self.aggregate_equivalent, "aggregate_equivalent")
        for field_name in (
            "contract_success_rate_gap",
            "mean_local_side_game_score_gap",
            "mean_local_side_card_point_margin_gap",
            "immediate_expected_point_swing_gap",
        ):
            _require_optional_number(getattr(self, field_name), field_name)
        _require_boolean(self.eligible_for_focus, "eligible_for_focus")
        expected_eligible = (
            self.assessment_scope == "complete_search"
            and self.assessment_status == "strictly_below_best"
        )
        if self.eligible_for_focus != expected_eligible:
            raise ValueError("eligible_for_focus must require complete below-best Search.")
        if self.assessment_status == "best_or_equivalent" and (
            self.impact_tier != "no_missed_impact"
            or self.strictly_better_card_count != 0
        ):
            raise ValueError("best_or_equivalent fields must reconcile.")
        if self.assessment_status == "strictly_below_best" and (
            self.impact_tier
            not in {"contract_success", "settlement_score", "card_point_margin", "immediate_only"}
            or self.strictly_better_card_count is None
            or self.strictly_better_card_count <= 0
        ):
            raise ValueError("strictly_below_best fields must reconcile.")
        if self.assessment_status == "not_assessable" and (
            self.assessment_scope != "none"
            or self.evidence_basis != "none"
            or self.impact_tier != "not_assessable"
            or any(
                item is not None
                for item in (
                    self.best_card,
                    self.actual_card_rank,
                    self.best_card_rank,
                    self.strictly_better_card_count,
                    self.aggregate_equivalent,
                    self.contract_success_rate_gap,
                    self.mean_local_side_game_score_gap,
                    self.mean_local_side_card_point_margin_gap,
                )
            )
        ):
            raise ValueError("not_assessable fields must be unavailable.")
        if self.assessment_status == "forced_move" and (
            self.impact_tier != "no_missed_impact"
            or self.best_card != self.actual_card_played
            or self.actual_card_rank != 1
            or self.best_card_rank != 1
            or self.strictly_better_card_count != 0
        ):
            raise ValueError("forced_move fields must reconcile.")
        scope_basis = {
            "complete_search": LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_BASES[:3]
            + LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_BASES[4:7],
            "completed_common_prefix": ("bounded_search_completed_common_prefix",),
            "immediate_only": ("immediate_expected_value",),
            "none": ("none",),
        }
        if self.evidence_basis not in scope_basis[self.assessment_scope]:
            raise ValueError("assessment_scope and evidence_basis must reconcile.")
        if verify_identity and self.teacher_assessment_id != _build_coaching_identifier_v1(
            LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_ID_DOMAIN,
            _identity_material_v1(self, "teacher_assessment_id"),
        ):
            raise ValueError("teacher_assessment_id must cover the exact Assessment.")

    def to_dict(self) -> dict[str, Any]:
        return {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalCoachingDecisionSummaryV1:
    learning_corpus_tactical_coaching_decision_summary_version: int
    decision_summary_id: str
    tactical_motif_evidence_id: str
    match_snapshot_id: str
    game_reference_id: str
    decision_reference_id: str
    match_id: str
    game_id: str
    decision_index: int
    acting_player_id: str
    actual_card_played: str
    motif_types: tuple[str, ...]
    teacher_assessment_ids: tuple[str, ...]
    teacher_semantic_fingerprints: tuple[str, ...]
    exact_teacher_count: int
    semantic_teacher_count: int
    complete_search_semantic_teacher_count: int
    completed_common_prefix_semantic_teacher_count: int
    immediate_only_semantic_teacher_count: int
    not_assessable_semantic_teacher_count: int
    assessment_status_counts: tuple[tuple[str, int], ...]
    impact_tier_counts: tuple[tuple[str, int], ...]
    decision_status: str
    consensus_impact_tier: str
    eligible_for_focus: bool

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalCoachingDecisionSummaryV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalCoachingDecisionSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_coaching_decision_summary_version,
            LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_VERSION,
            "learning_corpus_tactical_coaching_decision_summary_version",
        )
        for field_name in (
            "decision_summary_id",
            "tactical_motif_evidence_id",
            "match_snapshot_id",
            "game_reference_id",
            "decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in ("match_id", "game_id", "acting_player_id"):
            _require_identifier(getattr(self, field_name), field_name)
        _require_positive_integer(self.decision_index, "decision_index")
        if self.actual_card_played not in _VALID_CARDS:
            raise ValueError("actual_card_played must be one valid Skat Card.")
        _require_string_tuple(self.motif_types, "motif_types")
        if self.motif_types != tuple(
            motif_type for motif_type in TACTICAL_MOTIF_TYPES if motif_type in self.motif_types
        ):
            raise ValueError("motif_types must use canonical Tactical order.")
        _require_string_tuple(
            self.teacher_assessment_ids,
            "teacher_assessment_ids",
            hashes=True,
        )
        _require_string_tuple(
            self.teacher_semantic_fingerprints,
            "teacher_semantic_fingerprints",
            hashes=True,
        )
        for field_name in (
            "exact_teacher_count",
            "semantic_teacher_count",
            "complete_search_semantic_teacher_count",
            "completed_common_prefix_semantic_teacher_count",
            "immediate_only_semantic_teacher_count",
            "not_assessable_semantic_teacher_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.exact_teacher_count != len(self.teacher_assessment_ids):
            raise ValueError("exact_teacher_count must reconcile exactly.")
        if self.semantic_teacher_count != len(self.teacher_semantic_fingerprints):
            raise ValueError("semantic_teacher_count must reconcile exactly.")
        if self.semantic_teacher_count != sum(
            (
                self.complete_search_semantic_teacher_count,
                self.completed_common_prefix_semantic_teacher_count,
                self.immediate_only_semantic_teacher_count,
                self.not_assessable_semantic_teacher_count,
            )
        ):
            raise ValueError("Semantic Teacher scope Counts must reconcile exactly.")
        _require_canonical_counts(
            self.assessment_status_counts,
            "assessment_status_counts",
            LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_STATUSES,
        )
        _require_canonical_counts(
            self.impact_tier_counts,
            "impact_tier_counts",
            LEARNING_CORPUS_TACTICAL_COACHING_IMPACT_TIERS,
        )
        if sum(count for _, count in self.assessment_status_counts) != (
            self.semantic_teacher_count
        ) or sum(count for _, count in self.impact_tier_counts) != self.semantic_teacher_count:
            raise ValueError("Semantic Teacher classification Counts must reconcile exactly.")
        if self.decision_status not in LEARNING_CORPUS_TACTICAL_COACHING_DECISION_STATUSES:
            raise ValueError("decision_status must be canonical.")
        if self.consensus_impact_tier not in _DECISION_CONSENSUS_IMPACT_VALUES:
            raise ValueError("consensus_impact_tier must be canonical.")
        _require_boolean(self.eligible_for_focus, "eligible_for_focus")
        if self.eligible_for_focus != (self.decision_status == "strictly_below_best"):
            raise ValueError("Only strictly_below_best Decisions may be focus-eligible.")
        if self.decision_status == "no_teacher" and self.exact_teacher_count != 0:
            raise ValueError("no_teacher requires no exact Teacher Assessment.")
        if self.decision_status in {"best_or_equivalent", "strictly_below_best", "mixed"} and (
            self.complete_search_semantic_teacher_count == 0
        ):
            raise ValueError("Assessable Decision status requires complete Search evidence.")
        if verify_identity and self.decision_summary_id != _build_coaching_identifier_v1(
            LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_ID_DOMAIN,
            _identity_material_v1(self, "decision_summary_id"),
        ):
            raise ValueError("decision_summary_id must cover the exact Decision Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_coaching_decision_summary_version": (
                self.learning_corpus_tactical_coaching_decision_summary_version
            ),
            "decision_summary_id": self.decision_summary_id,
            "tactical_motif_evidence_id": self.tactical_motif_evidence_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "decision_reference_id": self.decision_reference_id,
            "match_id": self.match_id,
            "game_id": self.game_id,
            "decision_index": self.decision_index,
            "acting_player_id": self.acting_player_id,
            "actual_card_played": self.actual_card_played,
            "motif_types": list(self.motif_types),
            "teacher_assessment_ids": list(self.teacher_assessment_ids),
            "teacher_semantic_fingerprints": list(self.teacher_semantic_fingerprints),
            "exact_teacher_count": self.exact_teacher_count,
            "semantic_teacher_count": self.semantic_teacher_count,
            "complete_search_semantic_teacher_count": (
                self.complete_search_semantic_teacher_count
            ),
            "completed_common_prefix_semantic_teacher_count": (
                self.completed_common_prefix_semantic_teacher_count
            ),
            "immediate_only_semantic_teacher_count": (
                self.immediate_only_semantic_teacher_count
            ),
            "not_assessable_semantic_teacher_count": (
                self.not_assessable_semantic_teacher_count
            ),
            "assessment_status_counts": _serialize_counts(
                self.assessment_status_counts,
                "assessment_status",
            ),
            "impact_tier_counts": _serialize_counts(
                self.impact_tier_counts,
                "impact_tier",
            ),
            "decision_status": self.decision_status,
            "consensus_impact_tier": self.consensus_impact_tier,
            "eligible_for_focus": self.eligible_for_focus,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalCoachingFocusAreaV1:
    learning_corpus_tactical_coaching_focus_area_version: int
    focus_area_id: str
    player_id: str
    motif_type: str
    motif_family: str
    recurrence_scope: str
    primary_impact_tier: str
    guidance_code: str
    guidance_text: str
    qualifying_decision_count: int
    distinct_game_count: int
    distinct_match_count: int
    contract_success_decision_count: int
    settlement_score_decision_count: int
    card_point_margin_decision_count: int
    mixed_impact_decision_count: int
    decision_summary_ids: tuple[str, ...]
    tactical_motif_evidence_ids: tuple[str, ...]
    game_reference_ids: tuple[str, ...]
    match_ids: tuple[str, ...]
    requested_method_counts: tuple[tuple[str, int], ...]
    role_counts: tuple[tuple[str, int], ...]
    seat_counts: tuple[tuple[str, int], ...]
    phase_counts: tuple[tuple[str, int], ...]
    contract_counts: tuple[tuple[str, int], ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusTacticalCoachingFocusAreaV1 requires its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalCoachingFocusAreaV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_coaching_focus_area_version,
            LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_VERSION,
            "learning_corpus_tactical_coaching_focus_area_version",
        )
        _require_hash(self.focus_area_id, "focus_area_id")
        _require_identifier(self.player_id, "player_id")
        if self.motif_type not in TACTICAL_MOTIF_TYPES:
            raise ValueError("motif_type must be canonical.")
        if self.motif_family != TACTICAL_MOTIF_FAMILY_BY_TYPE[self.motif_type]:
            raise ValueError("motif_family must match motif_type.")
        if self.recurrence_scope not in LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_SCOPES:
            raise ValueError("recurrence_scope must be canonical.")
        if self.primary_impact_tier not in LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES:
            raise ValueError("primary_impact_tier must be canonical.")
        expected_guidance_index = LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES.index(
            self.primary_impact_tier
        )
        if self.guidance_code != LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_CODES[
            expected_guidance_index
        ]:
            raise ValueError("guidance_code must match the primary impact tier.")
        if self.guidance_text != LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_TEXT_BY_CODE.get(
            self.guidance_code
        ):
            raise ValueError("guidance_text must use the exact fixed template.")
        for field_name in (
            "qualifying_decision_count",
            "distinct_game_count",
            "distinct_match_count",
            "contract_success_decision_count",
            "settlement_score_decision_count",
            "card_point_margin_decision_count",
            "mixed_impact_decision_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if (
            self.qualifying_decision_count
            < LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_DECISIONS
            or self.distinct_game_count < LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_GAMES
            or self.distinct_match_count <= 0
            or self.distinct_match_count > self.distinct_game_count
        ):
            raise ValueError("Focus threshold Counts must reconcile exactly.")
        if self.qualifying_decision_count != sum(
            (
                self.contract_success_decision_count,
                self.settlement_score_decision_count,
                self.card_point_margin_decision_count,
                self.mixed_impact_decision_count,
            )
        ):
            raise ValueError("Focus impact Counts must cover every qualifying Decision.")
        for field_name in (
            "decision_summary_ids",
            "tactical_motif_evidence_ids",
            "game_reference_ids",
        ):
            _require_string_tuple(getattr(self, field_name), field_name, hashes=True)
        _require_string_tuple(self.match_ids, "match_ids")
        if self.qualifying_decision_count != len(self.decision_summary_ids) or (
            self.qualifying_decision_count != len(self.tactical_motif_evidence_ids)
        ):
            raise ValueError("Focus Decision identities must reconcile exactly.")
        if self.distinct_game_count != len(self.game_reference_ids) or (
            self.distinct_match_count != len(self.match_ids)
        ):
            raise ValueError("Focus Game and Match identities must reconcile exactly.")
        for field_name, canonical in (
            ("requested_method_counts", tuple(FLAT_RECOMMENDATION_METHODS)),
            ("role_counts", LEARNING_CORPUS_TACTICAL_MOTIF_ROLES),
            ("seat_counts", LEARNING_CORPUS_TACTICAL_MOTIF_SEATS),
            ("phase_counts", LEARNING_CORPUS_TACTICAL_MOTIF_PHASES),
            ("contract_counts", LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS),
        ):
            _require_canonical_counts(getattr(self, field_name), field_name, canonical)
        for field_name in ("role_counts", "seat_counts", "phase_counts", "contract_counts"):
            if sum(count for _, count in getattr(self, field_name)) != (
                self.qualifying_decision_count
            ):
                raise ValueError(f"{field_name} must cover every qualifying Decision.")
        if verify_identity and self.focus_area_id != _build_coaching_identifier_v1(
            LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_ID_DOMAIN,
            _identity_material_v1(self, "focus_area_id"),
        ):
            raise ValueError("focus_area_id must cover the exact Focus Area.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_coaching_focus_area_version": (
                self.learning_corpus_tactical_coaching_focus_area_version
            ),
            "focus_area_id": self.focus_area_id,
            "player_id": self.player_id,
            "motif_type": self.motif_type,
            "motif_family": self.motif_family,
            "recurrence_scope": self.recurrence_scope,
            "primary_impact_tier": self.primary_impact_tier,
            "guidance_code": self.guidance_code,
            "guidance_text": self.guidance_text,
            "qualifying_decision_count": self.qualifying_decision_count,
            "distinct_game_count": self.distinct_game_count,
            "distinct_match_count": self.distinct_match_count,
            "contract_success_decision_count": self.contract_success_decision_count,
            "settlement_score_decision_count": self.settlement_score_decision_count,
            "card_point_margin_decision_count": self.card_point_margin_decision_count,
            "mixed_impact_decision_count": self.mixed_impact_decision_count,
            "decision_summary_ids": list(self.decision_summary_ids),
            "tactical_motif_evidence_ids": list(self.tactical_motif_evidence_ids),
            "game_reference_ids": list(self.game_reference_ids),
            "match_ids": list(self.match_ids),
            "requested_method_counts": _serialize_counts(
                self.requested_method_counts,
                "requested_method",
            ),
            "role_counts": _serialize_counts(self.role_counts, "role"),
            "seat_counts": _serialize_counts(self.seat_counts, "seat"),
            "phase_counts": _serialize_counts(self.phase_counts, "phase"),
            "contract_counts": _serialize_counts(self.contract_counts, "contract"),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalCoachingPlayerReportV1:
    learning_corpus_tactical_coaching_player_report_version: int
    player_report_id: str
    player_id: str
    observed_labels: tuple[str, ...]
    match_ids: tuple[str, ...]
    current_match_snapshot_ids: tuple[str, ...]
    tactical_decision_count: int
    teacher_covered_decision_count: int
    exact_teacher_assessment_count: int
    semantic_teacher_group_count: int
    forced_move_count: int
    no_teacher_count: int
    not_assessable_count: int
    best_or_equivalent_count: int
    strictly_below_best_count: int
    mixed_count: int
    eligible_focus_candidate_count: int
    retained_focus_area_count: int
    focus_areas: tuple[LearningCorpusTacticalCoachingFocusAreaV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalCoachingPlayerReportV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalCoachingPlayerReportV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_coaching_player_report_version,
            LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_VERSION,
            "learning_corpus_tactical_coaching_player_report_version",
        )
        _require_hash(self.player_report_id, "player_report_id")
        _require_identifier(self.player_id, "player_id")
        _require_string_tuple(self.observed_labels, "observed_labels")
        if self.observed_labels != tuple(sorted(self.observed_labels)):
            raise ValueError("observed_labels must retain sorted exact label history.")
        _require_string_tuple(self.match_ids, "match_ids")
        _require_string_tuple(
            self.current_match_snapshot_ids,
            "current_match_snapshot_ids",
            hashes=True,
        )
        for field_name in (
            "tactical_decision_count",
            "teacher_covered_decision_count",
            "exact_teacher_assessment_count",
            "semantic_teacher_group_count",
            "forced_move_count",
            "no_teacher_count",
            "not_assessable_count",
            "best_or_equivalent_count",
            "strictly_below_best_count",
            "mixed_count",
            "eligible_focus_candidate_count",
            "retained_focus_area_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.tactical_decision_count != sum(
            (
                self.forced_move_count,
                self.no_teacher_count,
                self.not_assessable_count,
                self.best_or_equivalent_count,
                self.strictly_below_best_count,
                self.mixed_count,
            )
        ):
            raise ValueError("Player Decision status Counts must reconcile exactly.")
        if type(self.focus_areas) is not tuple or any(
            type(item) is not LearningCorpusTacticalCoachingFocusAreaV1
            for item in self.focus_areas
        ):
            raise ValueError("focus_areas must contain exact immutable Focus Areas.")
        for item in self.focus_areas:
            item._validate(verify_identity=True)
            if item.player_id != self.player_id:
                raise ValueError("Player Focus Areas must use the report Player ID.")
        if self.retained_focus_area_count != len(self.focus_areas) or (
            self.retained_focus_area_count
            > LEARNING_CORPUS_TACTICAL_COACHING_MAXIMUM_FOCUS_AREAS_PER_PLAYER
        ):
            raise ValueError("Retained Player Focus Count must reconcile exactly.")
        if self.eligible_focus_candidate_count < self.retained_focus_area_count:
            raise ValueError("Eligible Focus Count cannot be below retained Focus Count.")
        if verify_identity and self.player_report_id != _build_coaching_identifier_v1(
            LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_ID_DOMAIN,
            _identity_material_v1(self, "player_report_id"),
        ):
            raise ValueError("player_report_id must cover the exact Player Report.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_coaching_player_report_version": (
                self.learning_corpus_tactical_coaching_player_report_version
            ),
            "player_report_id": self.player_report_id,
            "player_id": self.player_id,
            "observed_labels": list(self.observed_labels),
            "match_ids": list(self.match_ids),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "tactical_decision_count": self.tactical_decision_count,
            "teacher_covered_decision_count": self.teacher_covered_decision_count,
            "exact_teacher_assessment_count": self.exact_teacher_assessment_count,
            "semantic_teacher_group_count": self.semantic_teacher_group_count,
            "forced_move_count": self.forced_move_count,
            "no_teacher_count": self.no_teacher_count,
            "not_assessable_count": self.not_assessable_count,
            "best_or_equivalent_count": self.best_or_equivalent_count,
            "strictly_below_best_count": self.strictly_below_best_count,
            "mixed_count": self.mixed_count,
            "eligible_focus_candidate_count": self.eligible_focus_candidate_count,
            "retained_focus_area_count": self.retained_focus_area_count,
            "focus_areas": [item.to_dict() for item in self.focus_areas],
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalCrossGameCoachingReportV1:
    learning_corpus_tactical_cross_game_coaching_report_version: int
    tactical_cross_game_coaching_report_fingerprint: str
    report_method: str
    status: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    player_catalog_fingerprint: str
    strategy_teacher_collection_fingerprint: str
    tactical_motif_collection_fingerprint: str
    tactical_motif_cross_game_summary_fingerprint: str
    tactical_decision_count: int
    tactical_skipped_decision_count: int
    exact_teacher_evidence_count: int
    joined_teacher_evidence_count: int
    unjoined_teacher_evidence_count: int
    semantic_teacher_group_count: int
    teacher_assessment_count: int
    decision_summary_count: int
    teacher_covered_decision_count: int
    complete_search_assessable_decision_count: int
    strictly_below_best_decision_count: int
    mixed_decision_count: int
    focus_area_count: int
    player_with_focus_count: int
    teacher_assessments: tuple[LearningCorpusTacticalCoachingTeacherAssessmentV1, ...]
    decision_summaries: tuple[LearningCorpusTacticalCoachingDecisionSummaryV1, ...]
    unjoined_strategy_teacher_evidence_ids: tuple[str, ...]
    player_reports: tuple[LearningCorpusTacticalCoachingPlayerReportV1, ...]
    focus_areas: tuple[LearningCorpusTacticalCoachingFocusAreaV1, ...]
    limitations: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalCrossGameCoachingReportV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalCrossGameCoachingReportV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_cross_game_coaching_report_version,
            LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_VERSION,
            "learning_corpus_tactical_cross_game_coaching_report_version",
        )
        for field_name in (
            "tactical_cross_game_coaching_report_fingerprint",
            "source_catalog_fingerprint",
            "source_catalog_content_fingerprint",
            "player_catalog_fingerprint",
            "strategy_teacher_collection_fingerprint",
            "tactical_motif_collection_fingerprint",
            "tactical_motif_cross_game_summary_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        if self.report_method != LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_METHOD:
            raise ValueError("report_method must be the exact Coaching method.")
        if self.status not in LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_STATUSES:
            raise ValueError("status must be canonical.")
        _require_identifier(self.corpus_id, "corpus_id")
        _require_count(self.source_catalog_revision, "source_catalog_revision")
        _require_string_tuple(
            self.current_match_snapshot_ids,
            "current_match_snapshot_ids",
            hashes=True,
        )
        for field_name in (
            "tactical_decision_count",
            "tactical_skipped_decision_count",
            "exact_teacher_evidence_count",
            "joined_teacher_evidence_count",
            "unjoined_teacher_evidence_count",
            "semantic_teacher_group_count",
            "teacher_assessment_count",
            "decision_summary_count",
            "teacher_covered_decision_count",
            "complete_search_assessable_decision_count",
            "strictly_below_best_decision_count",
            "mixed_decision_count",
            "focus_area_count",
            "player_with_focus_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        typed_groups = (
            (
                self.teacher_assessments,
                LearningCorpusTacticalCoachingTeacherAssessmentV1,
                "teacher_assessments",
            ),
            (
                self.decision_summaries,
                LearningCorpusTacticalCoachingDecisionSummaryV1,
                "decision_summaries",
            ),
            (
                self.player_reports,
                LearningCorpusTacticalCoachingPlayerReportV1,
                "player_reports",
            ),
            (self.focus_areas, LearningCorpusTacticalCoachingFocusAreaV1, "focus_areas"),
        )
        for items, expected_type, field_name in typed_groups:
            if type(items) is not tuple or any(type(item) is not expected_type for item in items):
                raise ValueError(f"{field_name} must contain exact immutable values.")
            for item in items:
                identity_name = next(
                    name
                    for name in (
                        "teacher_assessment_id",
                        "decision_summary_id",
                        "player_report_id",
                        "focus_area_id",
                    )
                    if hasattr(item, name)
                )
                item._validate(verify_identity=True)
                _require_hash(getattr(item, identity_name), identity_name)
        _require_string_tuple(
            self.unjoined_strategy_teacher_evidence_ids,
            "unjoined_strategy_teacher_evidence_ids",
            hashes=True,
        )
        if self.teacher_assessment_count != len(self.teacher_assessments) or (
            self.joined_teacher_evidence_count != self.teacher_assessment_count
        ):
            raise ValueError("Teacher Assessment Counts must reconcile exactly.")
        if self.exact_teacher_evidence_count != (
            self.joined_teacher_evidence_count + self.unjoined_teacher_evidence_count
        ) or self.unjoined_teacher_evidence_count != len(
            self.unjoined_strategy_teacher_evidence_ids
        ):
            raise ValueError("Joined and unjoined Teacher Counts must reconcile exactly.")
        if self.decision_summary_count != len(self.decision_summaries) or (
            self.tactical_decision_count != self.decision_summary_count
        ):
            raise ValueError("Tactical Decision Summary Counts must reconcile exactly.")
        if self.semantic_teacher_group_count != sum(
            item.semantic_teacher_count for item in self.decision_summaries
        ):
            raise ValueError("Semantic Teacher group Count must reconcile exactly.")
        if self.teacher_covered_decision_count != sum(
            item.exact_teacher_count > 0 for item in self.decision_summaries
        ):
            raise ValueError("Teacher-covered Decision Count must reconcile exactly.")
        if self.complete_search_assessable_decision_count != sum(
            item.decision_status
            in {"best_or_equivalent", "strictly_below_best", "mixed"}
            for item in self.decision_summaries
        ):
            raise ValueError("Complete-Search assessable Decision Count must reconcile exactly.")
        if self.strictly_below_best_decision_count != sum(
            item.decision_status == "strictly_below_best" for item in self.decision_summaries
        ) or self.mixed_decision_count != sum(
            item.decision_status == "mixed" for item in self.decision_summaries
        ):
            raise ValueError("Decision classification Counts must reconcile exactly.")
        if self.focus_area_count != len(self.focus_areas) or self.focus_area_count != sum(
            item.retained_focus_area_count for item in self.player_reports
        ):
            raise ValueError("Focus Area Count must reconcile exactly.")
        if self.focus_areas != tuple(
            focus for player in self.player_reports for focus in player.focus_areas
        ):
            raise ValueError("Global Focus order must follow Player Report order.")
        if self.player_with_focus_count != sum(
            item.retained_focus_area_count > 0 for item in self.player_reports
        ):
            raise ValueError("Player-with-focus Count must reconcile exactly.")
        expected_status = (
            "empty"
            if self.tactical_decision_count == 0
            else "available"
            if self.focus_area_count > 0
            else "insufficient_evidence"
        )
        if self.status != expected_status:
            raise ValueError("Report status must follow exact Coaching semantics.")
        if self.limitations != LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_LIMITATIONS:
            raise ValueError("limitations must retain exact canonical order.")
        if verify_fingerprint and self.tactical_cross_game_coaching_report_fingerprint != (
            _build_coaching_identifier_v1(
                LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_FINGERPRINT_DOMAIN,
                _identity_material_v1(
                    self,
                    "tactical_cross_game_coaching_report_fingerprint",
                ),
            )
        ):
            raise ValueError(
                "tactical_cross_game_coaching_report_fingerprint must cover the exact Report."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_cross_game_coaching_report_version": (
                self.learning_corpus_tactical_cross_game_coaching_report_version
            ),
            "tactical_cross_game_coaching_report_fingerprint": (
                self.tactical_cross_game_coaching_report_fingerprint
            ),
            "report_method": self.report_method,
            "status": self.status,
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": self.source_catalog_content_fingerprint,
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "player_catalog_fingerprint": self.player_catalog_fingerprint,
            "strategy_teacher_collection_fingerprint": (
                self.strategy_teacher_collection_fingerprint
            ),
            "tactical_motif_collection_fingerprint": (
                self.tactical_motif_collection_fingerprint
            ),
            "tactical_motif_cross_game_summary_fingerprint": (
                self.tactical_motif_cross_game_summary_fingerprint
            ),
            "tactical_decision_count": self.tactical_decision_count,
            "tactical_skipped_decision_count": self.tactical_skipped_decision_count,
            "exact_teacher_evidence_count": self.exact_teacher_evidence_count,
            "joined_teacher_evidence_count": self.joined_teacher_evidence_count,
            "unjoined_teacher_evidence_count": self.unjoined_teacher_evidence_count,
            "semantic_teacher_group_count": self.semantic_teacher_group_count,
            "teacher_assessment_count": self.teacher_assessment_count,
            "decision_summary_count": self.decision_summary_count,
            "teacher_covered_decision_count": self.teacher_covered_decision_count,
            "complete_search_assessable_decision_count": (
                self.complete_search_assessable_decision_count
            ),
            "strictly_below_best_decision_count": self.strictly_below_best_decision_count,
            "mixed_decision_count": self.mixed_decision_count,
            "focus_area_count": self.focus_area_count,
            "player_with_focus_count": self.player_with_focus_count,
            "teacher_assessments": [item.to_dict() for item in self.teacher_assessments],
            "decision_summaries": [item.to_dict() for item in self.decision_summaries],
            "unjoined_strategy_teacher_evidence_ids": list(
                self.unjoined_strategy_teacher_evidence_ids
            ),
            "player_reports": [item.to_dict() for item in self.player_reports],
            "focus_areas": [item.to_dict() for item in self.focus_areas],
            "limitations": list(self.limitations),
        }


def _validate_learning_corpus_tactical_cross_game_coaching_report_v1(
    report: LearningCorpusTacticalCrossGameCoachingReportV1,
) -> None:
    if type(report) is not LearningCorpusTacticalCrossGameCoachingReportV1:
        raise ValueError(
            "report must be an exact LearningCorpusTacticalCrossGameCoachingReportV1."
        )
    report._validate(verify_fingerprint=True)
