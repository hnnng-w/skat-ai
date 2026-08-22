from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Final

from skat_ai.deck import get_full_deck
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
)
from skat_ai.learning_corpus_human_evidence import (
    LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS,
)
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_player_statistics import (
    LEARNING_CORPUS_PLAYER_STATISTICS_UNAVAILABLE_REASONS,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES,
)
from skat_ai.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_PARTITION_MODES,
    LearningDatasetPartitionSummaryV1,
    LearningDatasetPartitionWeightsV1,
)
from skat_ai.match_decision_review_preparation import (
    MATCH_DECISION_REVIEW_SKIP_REASONS,
)
from skat_ai.recommendation_workflow import (
    COMPATIBLE_WORLD_MINIMAX_METHOD,
    FLAT_RECOMMENDATION_METHODS,
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    NONE_EFFECTIVE_METHOD,
)
from skat_ai.rules import GAME_TYPES

LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION = 1
LEARNING_DATASET_MATCH_SUMMARY_VERSION = 1
LEARNING_DATASET_PLAYER_SUMMARY_VERSION = 1
LEARNING_DATASET_COMMUNICATION_SUMMARY_VERSION = 1
LEARNING_DATASET_STRATEGY_SUMMARY_VERSION = 1
LEARNING_DATASET_PARTITION_READINESS_VERSION = 1
LEARNING_DATASET_READINESS_SUMMARY_VERSION = 1
LEARNING_DATASET_CROSS_GAME_SUMMARY_VERSION = 1
LEARNING_DATASET_SUMMARY_EXPORT_VERSION = 1

LEARNING_DATASET_SUMMARY_COVERAGE_STATUSES: Final[tuple[str, ...]] = (
    "absent",
    "partial",
    "complete",
)
LEARNING_DATASET_SUMMARY_COVERAGE_FAMILIES: Final[tuple[str, ...]] = (
    "decision_state",
    "observed_behavior",
    "player_context",
    "strategy_teacher",
    "human_commentary",
    "linked_response",
)

LEARNING_DATASET_SUMMARY_SOURCE_POLICY = "exact_dataset_player_catalog_and_partition_results"
LEARNING_DATASET_SUMMARY_CURRENT_SOURCE_POLICY = "explicit_current_match_snapshots_only"
LEARNING_DATASET_SUMMARY_BEHAVIOR_POLICY = (
    "descriptive_observed_behavior_without_skill_or_quality_claim"
)
LEARNING_DATASET_SUMMARY_COMMUNICATION_POLICY = (
    "count_exact_human_and_response_evidence_without_interpretation"
)
LEARNING_DATASET_SUMMARY_STRATEGY_POLICY = (
    "aggregate_method_bound_teacher_status_without_preference_or_truth_claim"
)
LEARNING_DATASET_SUMMARY_READINESS_POLICY = (
    "coverage_and_partition_availability_not_model_readiness"
)
LEARNING_DATASET_SUMMARY_PLAYER_POLICY = (
    "stable_player_descriptive_history_without_rating_or_ranking"
)
LEARNING_DATASET_SUMMARY_PARTITION_POLICY = "report_supplied_partition_results_without_regeneration"
LEARNING_DATASET_SUMMARY_RATIO_POLICY = "exact_counts_without_floating_point_percentages"
LEARNING_DATASET_SUMMARY_TEXT_POLICY = "human_text_never_used_for_grouping_or_output"
LEARNING_DATASET_SUMMARY_PRIVACY_POLICY = "private_local_minimized_aggregate_metadata"
LEARNING_DATASET_SUMMARY_EXPORT_POLICY = "deterministic_path_free_json_document"

LEARNING_DATASET_SUMMARY_GAME_TYPES: Final[tuple[str, ...]] = tuple(GAME_TYPES)
LEARNING_DATASET_SUMMARY_ACTING_SIDES: Final[tuple[str, ...]] = (
    "declarer",
    "defenders",
)
LEARNING_DATASET_SUMMARY_SEATS: Final[tuple[str, ...]] = (
    "forehand",
    "middlehand",
    "rearhand",
)
LEARNING_DATASET_SUMMARY_HUMAN_ROLES: Final[tuple[str, ...]] = (
    "declarer",
    "defender",
)
LEARNING_DATASET_SUMMARY_CARDS: Final[tuple[str, ...]] = tuple(get_full_deck())
LEARNING_DATASET_SUMMARY_EFFECTIVE_METHODS: Final[tuple[str, ...]] = (
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    COMPATIBLE_WORLD_MINIMAX_METHOD,
    NONE_EFFECTIVE_METHOD,
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
)
LEARNING_DATASET_SUMMARY_PLAYER_CONTEXT_UNAVAILABLE_REASONS: Final[tuple[str, ...]] = tuple(
    reason
    for reason in LEARNING_CORPUS_PLAYER_STATISTICS_UNAVAILABLE_REASONS
    if reason
    not in {
        "explicit_observation_not_found",
        "explicit_observation_not_before_target",
    }
)

_SUMMARY_COUNT_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_summary_count_v1\0"
_COVERAGE_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_summary_coverage_v1\0"
_MATCH_SUMMARY_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_match_summary_v1\0"
_PLAYER_SUMMARY_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_player_summary_v1\0"
_COMMUNICATION_SUMMARY_FINGERPRINT_DOMAIN = (
    b"skat-ai\0learning_dataset_v2_communication_summary_v1\0"
)
_STRATEGY_SUMMARY_FINGERPRINT_DOMAIN = b"skat-ai\0learning_dataset_v2_strategy_summary_v1\0"
_PARTITION_READINESS_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_partition_readiness_v1\0"
_READINESS_SUMMARY_FINGERPRINT_DOMAIN = b"skat-ai\0learning_dataset_v2_readiness_summary_v1\0"
_CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN = b"skat-ai\0learning_dataset_v2_cross_game_summary_v1\0"


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_count(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_identifier(
    value: object,
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        nullable = " or null" if allow_none else ""
        raise ValueError(f"{field_name} must be a non-empty, non-padded string{nullable}.")
    return value


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_boolean_or_none(value: object, field_name: str) -> bool | None:
    if value is not None and type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean or null.")
    return value


def _require_count_tuple(
    value: object,
    field_name: str,
) -> tuple[LearningDatasetSummaryCategoricalCountV1, ...]:
    if type(value) is not tuple or any(
        type(item) is not LearningDatasetSummaryCategoricalCountV1 for item in value
    ):
        raise ValueError(f"{field_name} must contain immutable categorical Counts.")
    categories = tuple(item.category for item in value)
    if len(categories) != len(set(categories)):
        raise ValueError(f"{field_name} must contain unique categories.")
    return value


def _require_integer_count_tuple(
    value: object,
    field_name: str,
) -> tuple[LearningDatasetSummaryIntegerCountV1, ...]:
    if type(value) is not tuple or any(
        type(item) is not LearningDatasetSummaryIntegerCountV1 for item in value
    ):
        raise ValueError(f"{field_name} must contain immutable integer Counts.")
    values = tuple(item.value for item in value)
    if len(values) != len(set(values)) or values != tuple(sorted(values)):
        raise ValueError(f"{field_name} must use unique ascending integer values.")
    return value


def _require_canonical_categories(
    value: tuple[LearningDatasetSummaryCategoricalCountV1, ...],
    field_name: str,
    canonical: tuple[str, ...],
    *,
    complete: bool = False,
) -> None:
    categories = tuple(item.category for item in value)
    expected = canonical if complete else tuple(item for item in canonical if item in categories)
    if categories != expected:
        raise ValueError(f"{field_name} must use canonical category order.")


def _count_sum(value: tuple[LearningDatasetSummaryCategoricalCountV1, ...]) -> int:
    return sum(item.count for item in value)


def _integer_count_sum(value: tuple[LearningDatasetSummaryIntegerCountV1, ...]) -> int:
    return sum(item.count for item in value)


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetSummaryCategoricalCountV1:
    learning_dataset_summary_primitive_version: int = LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION
    category: str
    count: int

    def __post_init__(self) -> None:
        _require_version(
            self.learning_dataset_summary_primitive_version,
            LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION,
            "learning_dataset_summary_primitive_version",
        )
        _require_identifier(self.category, "category")
        _require_count(self.count, "count")

    def to_dict(self) -> dict[str, int | str]:
        return {
            "learning_dataset_summary_primitive_version": (
                self.learning_dataset_summary_primitive_version
            ),
            "category": self.category,
            "count": self.count,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetSummaryIntegerCountV1:
    learning_dataset_summary_primitive_version: int = LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION
    value: int
    count: int

    def __post_init__(self) -> None:
        _require_version(
            self.learning_dataset_summary_primitive_version,
            LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION,
            "learning_dataset_summary_primitive_version",
        )
        if type(self.value) is not int:
            raise ValueError("value must be an integer and not a boolean.")
        _require_count(self.count, "count")

    def to_dict(self) -> dict[str, int]:
        return {
            "learning_dataset_summary_primitive_version": (
                self.learning_dataset_summary_primitive_version
            ),
            "value": self.value,
            "count": self.count,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetSummaryCoverageV1:
    learning_dataset_summary_primitive_version: int
    coverage_id: str
    family: str
    status: str
    covered_count: int
    total_count: int
    uncovered_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetSummaryCoverageV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetSummaryCoverageV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_summary_primitive_version,
            LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION,
            "learning_dataset_summary_primitive_version",
        )
        _require_hash(self.coverage_id, "coverage_id")
        if self.family not in LEARNING_DATASET_SUMMARY_COVERAGE_FAMILIES:
            raise ValueError("family must be one canonical Summary Coverage family.")
        if self.status not in LEARNING_DATASET_SUMMARY_COVERAGE_STATUSES:
            raise ValueError("status must be absent, partial, or complete.")
        for field_name in ("covered_count", "total_count", "uncovered_count"):
            _require_count(getattr(self, field_name), field_name)
        if self.covered_count > self.total_count or self.uncovered_count != (
            self.total_count - self.covered_count
        ):
            raise ValueError("Coverage Counts must reconcile exactly.")
        expected_status = (
            "absent"
            if self.covered_count == 0
            else "complete"
            if self.covered_count == self.total_count and self.total_count > 0
            else "partial"
        )
        if self.status != expected_status:
            raise ValueError("Coverage status must match exact Count semantics.")
        if verify_identity and self.coverage_id != _build_identifier(
            _COVERAGE_ID_DOMAIN,
            _identity_material(self, "coverage_id"),
        ):
            raise ValueError("coverage_id must cover the exact Coverage value.")

    def to_dict(self) -> dict[str, int | str]:
        return {
            "learning_dataset_summary_primitive_version": (
                self.learning_dataset_summary_primitive_version
            ),
            "coverage_id": self.coverage_id,
            "family": self.family,
            "status": self.status,
            "covered_count": self.covered_count,
            "total_count": self.total_count,
            "uncovered_count": self.uncovered_count,
        }


def build_learning_dataset_summary_coverage_v1(
    *,
    family: str,
    covered_count: int,
    total_count: int,
) -> LearningDatasetSummaryCoverageV1:
    """Builds one exact Count-only Coverage value."""
    _require_count(covered_count, "covered_count")
    _require_count(total_count, "total_count")
    if covered_count > total_count:
        raise ValueError("covered_count cannot exceed total_count.")
    status = (
        "absent"
        if covered_count == 0
        else "complete"
        if covered_count == total_count and total_count > 0
        else "partial"
    )
    values = {
        "learning_dataset_summary_primitive_version": (LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION),
        "coverage_id": "0" * 64,
        "family": family,
        "status": status,
        "covered_count": covered_count,
        "total_count": total_count,
        "uncovered_count": total_count - covered_count,
    }
    provisional = LearningDatasetSummaryCoverageV1._from_validated(**values)
    values["coverage_id"] = _build_identifier(
        _COVERAGE_ID_DOMAIN,
        _identity_material(provisional, "coverage_id"),
    )
    return LearningDatasetSummaryCoverageV1._from_validated(**values)


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetMatchSummaryV1:
    learning_dataset_match_summary_version: int
    match_summary_id: str
    match_snapshot_id: str
    match_id: str
    played_at: str | None
    player_ids: tuple[str, ...]
    perspective_player_id: str
    observed_game_count: int
    record_count: int
    skipped_decision_count: int
    observed_decision_count: int
    record_coverage: LearningDatasetSummaryCoverageV1
    records_by_game_type: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    records_by_acting_side: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    records_by_acting_seat: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    records_by_trick_number: tuple[LearningDatasetSummaryIntegerCountV1, ...]
    records_by_play_index: tuple[LearningDatasetSummaryIntegerCountV1, ...]
    forced_choice_record_count: int
    choice_record_count: int
    player_context_available_count: int
    player_context_unavailable_count: int
    strategy_teacher_evidence_count: int
    commentary_evidence_count: int
    response_evidence_count: int
    records_with_strategy_teacher_count: int
    records_with_commentary_count: int
    records_with_linked_response_count: int
    unjoined_commentary_evidence_count: int
    unjoined_response_evidence_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetMatchSummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetMatchSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_match_summary_version,
            LEARNING_DATASET_MATCH_SUMMARY_VERSION,
            "learning_dataset_match_summary_version",
        )
        for field_name in ("match_summary_id", "match_snapshot_id"):
            _require_hash(getattr(self, field_name), field_name)
        _require_identifier(self.match_id, "match_id")
        _require_identifier(self.played_at, "played_at", allow_none=True)
        if type(self.player_ids) is not tuple or len(self.player_ids) != 3:
            raise ValueError("player_ids must contain exactly three stable Players.")
        for player_id in self.player_ids:
            _require_identifier(player_id, "player_ids")
        if len(set(self.player_ids)) != 3:
            raise ValueError("player_ids must contain three unique Players.")
        _require_identifier(self.perspective_player_id, "perspective_player_id")
        if self.perspective_player_id not in self.player_ids:
            raise ValueError("Perspective Player must belong to the Match.")
        count_fields = (
            "observed_game_count",
            "record_count",
            "skipped_decision_count",
            "observed_decision_count",
            "forced_choice_record_count",
            "choice_record_count",
            "player_context_available_count",
            "player_context_unavailable_count",
            "strategy_teacher_evidence_count",
            "commentary_evidence_count",
            "response_evidence_count",
            "records_with_strategy_teacher_count",
            "records_with_commentary_count",
            "records_with_linked_response_count",
            "unjoined_commentary_evidence_count",
            "unjoined_response_evidence_count",
        )
        for field_name in count_fields:
            _require_count(getattr(self, field_name), field_name)
        if self.observed_decision_count != self.record_count + self.skipped_decision_count:
            raise ValueError("Match Decision Counts must reconcile exactly.")
        if type(self.record_coverage) is not LearningDatasetSummaryCoverageV1:
            raise ValueError("record_coverage must be one exact Coverage value.")
        self.record_coverage._validate(verify_identity=True)
        if (
            self.record_coverage.family != "decision_state"
            or self.record_coverage.covered_count != self.record_count
            or self.record_coverage.total_count != self.observed_decision_count
        ):
            raise ValueError("record_coverage must cover exact Match Decisions.")
        category_fields = (
            ("records_by_game_type", LEARNING_DATASET_SUMMARY_GAME_TYPES),
            ("records_by_acting_side", LEARNING_DATASET_SUMMARY_ACTING_SIDES),
            ("records_by_acting_seat", LEARNING_DATASET_SUMMARY_SEATS),
        )
        for field_name, categories in category_fields:
            values = _require_count_tuple(getattr(self, field_name), field_name)
            _require_canonical_categories(values, field_name, categories, complete=True)
            if _count_sum(values) != self.record_count:
                raise ValueError(f"{field_name} must cover every safe Record.")
        for field_name in ("records_by_trick_number", "records_by_play_index"):
            values = _require_integer_count_tuple(getattr(self, field_name), field_name)
            if _integer_count_sum(values) != self.record_count:
                raise ValueError(f"{field_name} must cover every safe Record.")
        if self.forced_choice_record_count + self.choice_record_count != self.record_count:
            raise ValueError("Forced and multi-choice Counts must cover every safe Record.")
        if self.player_context_available_count + self.player_context_unavailable_count != (
            self.record_count * 3
        ):
            raise ValueError("Player Context Counts must cover three contexts per Record.")
        for field_name in (
            "records_with_strategy_teacher_count",
            "records_with_commentary_count",
            "records_with_linked_response_count",
        ):
            if getattr(self, field_name) > self.record_count:
                raise ValueError(f"{field_name} cannot exceed record_count.")
        if verify_identity and self.match_summary_id != _build_identifier(
            _MATCH_SUMMARY_ID_DOMAIN,
            _identity_material(self, "match_summary_id"),
        ):
            raise ValueError("match_summary_id must cover the exact Match Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_match_summary_version": self.learning_dataset_match_summary_version,
            "match_summary_id": self.match_summary_id,
            "match_snapshot_id": self.match_snapshot_id,
            "match_id": self.match_id,
            "played_at": self.played_at,
            "player_ids": list(self.player_ids),
            "perspective_player_id": self.perspective_player_id,
            "observed_game_count": self.observed_game_count,
            "record_count": self.record_count,
            "skipped_decision_count": self.skipped_decision_count,
            "observed_decision_count": self.observed_decision_count,
            "record_coverage": self.record_coverage.to_dict(),
            "records_by_game_type": [item.to_dict() for item in self.records_by_game_type],
            "records_by_acting_side": [item.to_dict() for item in self.records_by_acting_side],
            "records_by_acting_seat": [item.to_dict() for item in self.records_by_acting_seat],
            "records_by_trick_number": [item.to_dict() for item in self.records_by_trick_number],
            "records_by_play_index": [item.to_dict() for item in self.records_by_play_index],
            "forced_choice_record_count": self.forced_choice_record_count,
            "choice_record_count": self.choice_record_count,
            "player_context_available_count": self.player_context_available_count,
            "player_context_unavailable_count": self.player_context_unavailable_count,
            "strategy_teacher_evidence_count": self.strategy_teacher_evidence_count,
            "commentary_evidence_count": self.commentary_evidence_count,
            "response_evidence_count": self.response_evidence_count,
            "records_with_strategy_teacher_count": self.records_with_strategy_teacher_count,
            "records_with_commentary_count": self.records_with_commentary_count,
            "records_with_linked_response_count": self.records_with_linked_response_count,
            "unjoined_commentary_evidence_count": self.unjoined_commentary_evidence_count,
            "unjoined_response_evidence_count": self.unjoined_response_evidence_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPlayerSummaryV1:
    learning_dataset_player_summary_version: int
    player_summary_id: str
    player_id: str
    observed_labels: tuple[str, ...]
    match_ids: tuple[str, ...]
    current_match_snapshot_ids: tuple[str, ...]
    match_count: int
    perspective_match_count: int
    record_count: int
    skipped_decision_count: int
    observed_decision_count: int
    records_by_game_type: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    records_by_acting_side: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    records_by_acting_seat: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    records_by_trick_number: tuple[LearningDatasetSummaryIntegerCountV1, ...]
    records_by_play_index: tuple[LearningDatasetSummaryIntegerCountV1, ...]
    forced_choice_record_count: int
    choice_record_count: int
    actual_card_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    player_context_reference_count: int
    player_context_available_count: int
    player_context_unavailable_count: int
    player_context_unavailable_reason_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    statistics_observation_count: int
    strategy_teacher_evidence_count: int
    teacher_distinct_decision_count: int
    recommendation_available_count: int
    recommendation_unavailable_count: int
    teacher_actual_card_match_count: int
    teacher_actual_card_difference_count: int
    commentary_subject_count: int
    commented_decision_count: int
    commentary_authored_count: int
    outgoing_response_count: int
    incoming_response_count: int
    same_trick_response_count: int
    later_trick_response_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPlayerSummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetPlayerSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_player_summary_version,
            LEARNING_DATASET_PLAYER_SUMMARY_VERSION,
            "learning_dataset_player_summary_version",
        )
        _require_hash(self.player_summary_id, "player_summary_id")
        _require_identifier(self.player_id, "player_id")
        for field_name in ("observed_labels", "match_ids"):
            values = getattr(self, field_name)
            if type(values) is not tuple:
                raise ValueError(f"{field_name} must be an immutable tuple.")
            for item in values:
                _require_identifier(item, field_name)
        if self.observed_labels != tuple(sorted(set(self.observed_labels))):
            raise ValueError("observed_labels must be unique and sorted without canonicalization.")
        if type(self.current_match_snapshot_ids) is not tuple:
            raise ValueError("current_match_snapshot_ids must be immutable.")
        for item in self.current_match_snapshot_ids:
            _require_hash(item, "current_match_snapshot_ids")
        count_fields = (
            "match_count",
            "perspective_match_count",
            "record_count",
            "skipped_decision_count",
            "observed_decision_count",
            "forced_choice_record_count",
            "choice_record_count",
            "player_context_reference_count",
            "player_context_available_count",
            "player_context_unavailable_count",
            "statistics_observation_count",
            "strategy_teacher_evidence_count",
            "teacher_distinct_decision_count",
            "recommendation_available_count",
            "recommendation_unavailable_count",
            "teacher_actual_card_match_count",
            "teacher_actual_card_difference_count",
            "commentary_subject_count",
            "commented_decision_count",
            "commentary_authored_count",
            "outgoing_response_count",
            "incoming_response_count",
            "same_trick_response_count",
            "later_trick_response_count",
        )
        for field_name in count_fields:
            _require_count(getattr(self, field_name), field_name)
        if (
            self.match_count != len(self.match_ids)
            or self.match_count != len(self.current_match_snapshot_ids)
            or self.perspective_match_count > self.match_count
        ):
            raise ValueError("Player Match Counts and identities must reconcile exactly.")
        if self.observed_decision_count != self.record_count + self.skipped_decision_count:
            raise ValueError("Player Decision Counts must reconcile exactly.")
        category_fields = (
            ("records_by_game_type", LEARNING_DATASET_SUMMARY_GAME_TYPES),
            ("records_by_acting_side", LEARNING_DATASET_SUMMARY_ACTING_SIDES),
            ("records_by_acting_seat", LEARNING_DATASET_SUMMARY_SEATS),
        )
        for field_name, categories in category_fields:
            values = _require_count_tuple(getattr(self, field_name), field_name)
            _require_canonical_categories(values, field_name, categories, complete=True)
            if _count_sum(values) != self.record_count:
                raise ValueError(f"{field_name} must cover every acting safe Record.")
        for field_name in ("records_by_trick_number", "records_by_play_index"):
            values = _require_integer_count_tuple(getattr(self, field_name), field_name)
            if _integer_count_sum(values) != self.record_count:
                raise ValueError(f"{field_name} must cover every acting safe Record.")
        if self.forced_choice_record_count + self.choice_record_count != self.record_count:
            raise ValueError("Player forced and multi-choice Counts must reconcile.")
        actual_cards = _require_count_tuple(self.actual_card_counts, "actual_card_counts")
        _require_canonical_categories(
            actual_cards,
            "actual_card_counts",
            LEARNING_DATASET_SUMMARY_CARDS,
        )
        if _count_sum(actual_cards) != self.record_count:
            raise ValueError("actual_card_counts must cover every acting safe Record.")
        reason_counts = _require_count_tuple(
            self.player_context_unavailable_reason_counts,
            "player_context_unavailable_reason_counts",
        )
        _require_canonical_categories(
            reason_counts,
            "player_context_unavailable_reason_counts",
            LEARNING_DATASET_SUMMARY_PLAYER_CONTEXT_UNAVAILABLE_REASONS,
        )
        if (
            self.player_context_available_count + self.player_context_unavailable_count
            != (self.player_context_reference_count)
            or _count_sum(reason_counts) != self.player_context_unavailable_count
        ):
            raise ValueError("Player Context availability Counts must reconcile exactly.")
        if self.recommendation_available_count + self.recommendation_unavailable_count != (
            self.strategy_teacher_evidence_count
        ):
            raise ValueError("Player Strategy Teacher status Counts must reconcile exactly.")
        if self.teacher_actual_card_match_count + self.teacher_actual_card_difference_count > (
            self.strategy_teacher_evidence_count
        ):
            raise ValueError("Player exact Card equality Counts cannot exceed Teacher Evidence.")
        if self.teacher_distinct_decision_count > self.strategy_teacher_evidence_count:
            raise ValueError("Distinct Teacher Decisions cannot exceed Teacher Evidence.")
        if self.commented_decision_count > self.commentary_subject_count:
            raise ValueError("Distinct commented Decisions cannot exceed Commentary subjects.")
        if self.same_trick_response_count + self.later_trick_response_count != (
            self.outgoing_response_count
        ):
            raise ValueError("Same- and later-Trick Counts must cover outgoing Responses.")
        if verify_identity and self.player_summary_id != _build_identifier(
            _PLAYER_SUMMARY_ID_DOMAIN,
            _identity_material(self, "player_summary_id"),
        ):
            raise ValueError("player_summary_id must cover the exact Player Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_player_summary_version": self.learning_dataset_player_summary_version,
            "player_summary_id": self.player_summary_id,
            "player_id": self.player_id,
            "observed_labels": list(self.observed_labels),
            "match_ids": list(self.match_ids),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "match_count": self.match_count,
            "perspective_match_count": self.perspective_match_count,
            "record_count": self.record_count,
            "skipped_decision_count": self.skipped_decision_count,
            "observed_decision_count": self.observed_decision_count,
            "records_by_game_type": [item.to_dict() for item in self.records_by_game_type],
            "records_by_acting_side": [item.to_dict() for item in self.records_by_acting_side],
            "records_by_acting_seat": [item.to_dict() for item in self.records_by_acting_seat],
            "records_by_trick_number": [item.to_dict() for item in self.records_by_trick_number],
            "records_by_play_index": [item.to_dict() for item in self.records_by_play_index],
            "forced_choice_record_count": self.forced_choice_record_count,
            "choice_record_count": self.choice_record_count,
            "actual_card_counts": [item.to_dict() for item in self.actual_card_counts],
            "player_context_reference_count": self.player_context_reference_count,
            "player_context_available_count": self.player_context_available_count,
            "player_context_unavailable_count": self.player_context_unavailable_count,
            "player_context_unavailable_reason_counts": [
                item.to_dict() for item in self.player_context_unavailable_reason_counts
            ],
            "statistics_observation_count": self.statistics_observation_count,
            "strategy_teacher_evidence_count": self.strategy_teacher_evidence_count,
            "teacher_distinct_decision_count": self.teacher_distinct_decision_count,
            "recommendation_available_count": self.recommendation_available_count,
            "recommendation_unavailable_count": self.recommendation_unavailable_count,
            "teacher_actual_card_match_count": self.teacher_actual_card_match_count,
            "teacher_actual_card_difference_count": self.teacher_actual_card_difference_count,
            "commentary_subject_count": self.commentary_subject_count,
            "commented_decision_count": self.commented_decision_count,
            "commentary_authored_count": self.commentary_authored_count,
            "outgoing_response_count": self.outgoing_response_count,
            "incoming_response_count": self.incoming_response_count,
            "same_trick_response_count": self.same_trick_response_count,
            "later_trick_response_count": self.later_trick_response_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetCommunicationSummaryV1:
    learning_dataset_communication_summary_version: int
    communication_summary_fingerprint: str
    commentary_count: int
    commented_decision_count: int
    commentator_identity_kind_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    commentary_on_perspective_player_count: int
    commentary_on_non_perspective_player_count: int
    commentaries_with_response_count: int
    commentaries_without_response_count: int
    response_count: int
    same_trick_response_count: int
    later_trick_response_count: int
    decision_offset_counts: tuple[LearningDatasetSummaryIntegerCountV1, ...]
    subject_role_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    response_role_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    subject_seat_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    response_seat_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    subject_response_role_pair_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    subject_response_seat_pair_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    unjoined_commentary_evidence_count: int
    unjoined_response_evidence_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetCommunicationSummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetCommunicationSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_communication_summary_version,
            LEARNING_DATASET_COMMUNICATION_SUMMARY_VERSION,
            "learning_dataset_communication_summary_version",
        )
        _require_hash(self.communication_summary_fingerprint, "communication_summary_fingerprint")
        for field_name in (
            "commentary_count",
            "commented_decision_count",
            "commentary_on_perspective_player_count",
            "commentary_on_non_perspective_player_count",
            "commentaries_with_response_count",
            "commentaries_without_response_count",
            "response_count",
            "same_trick_response_count",
            "later_trick_response_count",
            "unjoined_commentary_evidence_count",
            "unjoined_response_evidence_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.commented_decision_count > self.commentary_count:
            raise ValueError("Distinct commented Decisions cannot exceed Commentary Count.")
        if (
            self.commentary_on_perspective_player_count
            + (self.commentary_on_non_perspective_player_count)
            != self.commentary_count
        ):
            raise ValueError("Perspective Commentary Counts must reconcile exactly.")
        if self.commentaries_with_response_count + self.commentaries_without_response_count != (
            self.commentary_count
        ):
            raise ValueError("Commentary Response-availability Counts must reconcile.")
        if self.same_trick_response_count + self.later_trick_response_count != self.response_count:
            raise ValueError("Same- and later-Trick Responses must reconcile exactly.")
        identity_counts = _require_count_tuple(
            self.commentator_identity_kind_counts,
            "commentator_identity_kind_counts",
        )
        _require_canonical_categories(
            identity_counts,
            "commentator_identity_kind_counts",
            LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS,
            complete=True,
        )
        if _count_sum(identity_counts) != self.commentary_count:
            raise ValueError("Commentator identity Counts must cover every Commentary.")
        offsets = _require_integer_count_tuple(
            self.decision_offset_counts,
            "decision_offset_counts",
        )
        if _integer_count_sum(offsets) != self.response_count:
            raise ValueError("Decision-offset Counts must cover every Response.")
        role_pairs = tuple(
            f"{subject}->{response}"
            for subject in LEARNING_DATASET_SUMMARY_HUMAN_ROLES
            for response in LEARNING_DATASET_SUMMARY_HUMAN_ROLES
        )
        seat_pairs = tuple(
            f"{subject}->{response}"
            for subject in LEARNING_DATASET_SUMMARY_SEATS
            for response in LEARNING_DATASET_SUMMARY_SEATS
        )
        category_fields = (
            ("subject_role_counts", LEARNING_DATASET_SUMMARY_HUMAN_ROLES, self.commentary_count),
            ("response_role_counts", LEARNING_DATASET_SUMMARY_HUMAN_ROLES, self.response_count),
            ("subject_seat_counts", LEARNING_DATASET_SUMMARY_SEATS, self.commentary_count),
            ("response_seat_counts", LEARNING_DATASET_SUMMARY_SEATS, self.response_count),
            ("subject_response_role_pair_counts", role_pairs, self.response_count),
            ("subject_response_seat_pair_counts", seat_pairs, self.response_count),
        )
        for field_name, categories, expected_count in category_fields:
            values = _require_count_tuple(getattr(self, field_name), field_name)
            _require_canonical_categories(values, field_name, categories, complete=True)
            if _count_sum(values) != expected_count:
                raise ValueError(f"{field_name} must reconcile exactly.")
        if verify_identity and self.communication_summary_fingerprint != _build_identifier(
            _COMMUNICATION_SUMMARY_FINGERPRINT_DOMAIN,
            _identity_material(self, "communication_summary_fingerprint"),
        ):
            raise ValueError("communication_summary_fingerprint must cover the exact Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_communication_summary_version": (
                self.learning_dataset_communication_summary_version
            ),
            "communication_summary_fingerprint": self.communication_summary_fingerprint,
            "commentary_count": self.commentary_count,
            "commented_decision_count": self.commented_decision_count,
            "commentator_identity_kind_counts": [
                item.to_dict() for item in self.commentator_identity_kind_counts
            ],
            "commentary_on_perspective_player_count": (self.commentary_on_perspective_player_count),
            "commentary_on_non_perspective_player_count": (
                self.commentary_on_non_perspective_player_count
            ),
            "commentaries_with_response_count": self.commentaries_with_response_count,
            "commentaries_without_response_count": self.commentaries_without_response_count,
            "response_count": self.response_count,
            "same_trick_response_count": self.same_trick_response_count,
            "later_trick_response_count": self.later_trick_response_count,
            "decision_offset_counts": [item.to_dict() for item in self.decision_offset_counts],
            "subject_role_counts": [item.to_dict() for item in self.subject_role_counts],
            "response_role_counts": [item.to_dict() for item in self.response_role_counts],
            "subject_seat_counts": [item.to_dict() for item in self.subject_seat_counts],
            "response_seat_counts": [item.to_dict() for item in self.response_seat_counts],
            "subject_response_role_pair_counts": [
                item.to_dict() for item in self.subject_response_role_pair_counts
            ],
            "subject_response_seat_pair_counts": [
                item.to_dict() for item in self.subject_response_seat_pair_counts
            ],
            "unjoined_commentary_evidence_count": self.unjoined_commentary_evidence_count,
            "unjoined_response_evidence_count": self.unjoined_response_evidence_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetStrategySummaryV1:
    learning_dataset_strategy_summary_version: int
    strategy_summary_fingerprint: str
    evidence_count: int
    distinct_decision_count: int
    multi_teacher_decision_count: int
    maximum_teacher_count_per_decision: int
    semantic_fingerprint_count: int
    semantic_duplicate_group_count: int
    recommendation_available_count: int
    recommendation_unavailable_count: int
    requested_method_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    effective_method_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    search_status_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    fallback_count: int
    profile_presets_enabled_count: int
    profile_application_summary_count: int
    actual_card_match_evidence_count: int
    actual_card_difference_evidence_count: int
    actual_card_comparison_unavailable_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetStrategySummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetStrategySummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_strategy_summary_version,
            LEARNING_DATASET_STRATEGY_SUMMARY_VERSION,
            "learning_dataset_strategy_summary_version",
        )
        _require_hash(self.strategy_summary_fingerprint, "strategy_summary_fingerprint")
        count_fields = (
            "evidence_count",
            "distinct_decision_count",
            "multi_teacher_decision_count",
            "maximum_teacher_count_per_decision",
            "semantic_fingerprint_count",
            "semantic_duplicate_group_count",
            "recommendation_available_count",
            "recommendation_unavailable_count",
            "fallback_count",
            "profile_presets_enabled_count",
            "profile_application_summary_count",
            "actual_card_match_evidence_count",
            "actual_card_difference_evidence_count",
            "actual_card_comparison_unavailable_count",
        )
        for field_name in count_fields:
            _require_count(getattr(self, field_name), field_name)
        if self.recommendation_available_count + self.recommendation_unavailable_count != (
            self.evidence_count
        ):
            raise ValueError("Recommendation availability Counts must cover Teacher Evidence.")
        category_fields = (
            ("requested_method_counts", tuple(FLAT_RECOMMENDATION_METHODS)),
            ("effective_method_counts", LEARNING_DATASET_SUMMARY_EFFECTIVE_METHODS),
            ("search_status_counts", LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES),
        )
        for field_name, categories in category_fields:
            values = _require_count_tuple(getattr(self, field_name), field_name)
            _require_canonical_categories(values, field_name, categories, complete=True)
            if _count_sum(values) != self.evidence_count:
                raise ValueError(f"{field_name} must cover every Teacher Evidence value.")
        if (
            self.actual_card_match_evidence_count
            + (self.actual_card_difference_evidence_count)
            + self.actual_card_comparison_unavailable_count
            != self.evidence_count
        ):
            raise ValueError("Exact Card comparison Counts must cover Teacher Evidence.")
        if self.distinct_decision_count > self.evidence_count:
            raise ValueError("Distinct Decisions cannot exceed Teacher Evidence Count.")
        if self.multi_teacher_decision_count > self.distinct_decision_count:
            raise ValueError("Multi-Teacher Decisions cannot exceed distinct Decisions.")
        expected_maximum_zero = self.evidence_count == 0
        if (self.maximum_teacher_count_per_decision == 0) != expected_maximum_zero:
            raise ValueError("Maximum Teacher Count must be zero exactly for empty evidence.")
        if self.semantic_fingerprint_count > self.evidence_count or (
            self.semantic_duplicate_group_count > self.semantic_fingerprint_count
        ):
            raise ValueError("Semantic fingerprint Counts must reconcile.")
        for field_name in (
            "fallback_count",
            "profile_presets_enabled_count",
            "profile_application_summary_count",
        ):
            if getattr(self, field_name) > self.evidence_count:
                raise ValueError(f"{field_name} cannot exceed evidence_count.")
        if verify_identity and self.strategy_summary_fingerprint != _build_identifier(
            _STRATEGY_SUMMARY_FINGERPRINT_DOMAIN,
            _identity_material(self, "strategy_summary_fingerprint"),
        ):
            raise ValueError("strategy_summary_fingerprint must cover the exact Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_strategy_summary_version": (
                self.learning_dataset_strategy_summary_version
            ),
            "strategy_summary_fingerprint": self.strategy_summary_fingerprint,
            "evidence_count": self.evidence_count,
            "distinct_decision_count": self.distinct_decision_count,
            "multi_teacher_decision_count": self.multi_teacher_decision_count,
            "maximum_teacher_count_per_decision": self.maximum_teacher_count_per_decision,
            "semantic_fingerprint_count": self.semantic_fingerprint_count,
            "semantic_duplicate_group_count": self.semantic_duplicate_group_count,
            "recommendation_available_count": self.recommendation_available_count,
            "recommendation_unavailable_count": self.recommendation_unavailable_count,
            "requested_method_counts": [item.to_dict() for item in self.requested_method_counts],
            "effective_method_counts": [item.to_dict() for item in self.effective_method_counts],
            "search_status_counts": [item.to_dict() for item in self.search_status_counts],
            "fallback_count": self.fallback_count,
            "profile_presets_enabled_count": self.profile_presets_enabled_count,
            "profile_application_summary_count": self.profile_application_summary_count,
            "actual_card_match_evidence_count": self.actual_card_match_evidence_count,
            "actual_card_difference_evidence_count": self.actual_card_difference_evidence_count,
            "actual_card_comparison_unavailable_count": (
                self.actual_card_comparison_unavailable_count
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPartitionReadinessV1:
    learning_dataset_partition_readiness_version: int
    partition_readiness_id: str
    mode: str
    algorithm: str
    status: str
    unavailable_reason: str | None
    request_fingerprint: str
    plan_fingerprint: str
    base_random_seed: int
    requested_partition_weights: LearningDatasetPartitionWeightsV1
    source_active_match_group_count: int
    source_inactive_match_count: int
    source_record_count: int
    source_skipped_decision_count: int
    leakage_audit_status: str | None
    all_partitions_have_records: bool | None
    mode_constraints_satisfied: bool
    partition_summaries: tuple[LearningDatasetPartitionSummaryV1, ...]
    known_player_time_group_count: int | None
    known_player_validation_train_coverage_complete: bool | None
    known_player_test_train_coverage_complete: bool | None
    unseen_player_component_count: int | None
    unseen_player_player_disjoint: bool | None
    unseen_player_local_move_optimal: bool | None
    unseen_player_local_swap_optimal: bool | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPartitionReadinessV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetPartitionReadinessV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_partition_readiness_version,
            LEARNING_DATASET_PARTITION_READINESS_VERSION,
            "learning_dataset_partition_readiness_version",
        )
        _require_hash(self.partition_readiness_id, "partition_readiness_id")
        if self.mode not in LEARNING_DATASET_PARTITION_MODES:
            raise ValueError("mode must be one canonical partition mode.")
        _require_identifier(self.algorithm, "algorithm")
        if self.status not in {"complete", "unavailable"}:
            raise ValueError("status must be complete or unavailable.")
        _require_identifier(self.unavailable_reason, "unavailable_reason", allow_none=True)
        for field_name in ("request_fingerprint", "plan_fingerprint"):
            _require_hash(getattr(self, field_name), field_name)
        if type(self.base_random_seed) is not int:
            raise ValueError("base_random_seed must be an integer and not a boolean.")
        if type(self.requested_partition_weights) is not LearningDatasetPartitionWeightsV1:
            raise ValueError("requested_partition_weights must use the exact partition contract.")
        for field_name in (
            "source_active_match_group_count",
            "source_inactive_match_count",
            "source_record_count",
            "source_skipped_decision_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        _require_identifier(self.leakage_audit_status, "leakage_audit_status", allow_none=True)
        _require_boolean_or_none(self.all_partitions_have_records, "all_partitions_have_records")
        if type(self.mode_constraints_satisfied) is not bool:
            raise ValueError("mode_constraints_satisfied must be a boolean.")
        if type(self.partition_summaries) is not tuple or any(
            type(item) is not LearningDatasetPartitionSummaryV1 for item in self.partition_summaries
        ):
            raise ValueError("partition_summaries must contain exact partition Summaries.")
        optional_counts = ("known_player_time_group_count", "unseen_player_component_count")
        for field_name in optional_counts:
            field_value = getattr(self, field_name)
            if field_value is not None:
                _require_count(field_value, field_name)
        optional_booleans = (
            "known_player_validation_train_coverage_complete",
            "known_player_test_train_coverage_complete",
            "unseen_player_player_disjoint",
            "unseen_player_local_move_optimal",
            "unseen_player_local_swap_optimal",
        )
        for field_name in optional_booleans:
            _require_boolean_or_none(getattr(self, field_name), field_name)
        known_values = (
            self.known_player_time_group_count,
            self.known_player_validation_train_coverage_complete,
            self.known_player_test_train_coverage_complete,
        )
        unseen_values = (
            self.unseen_player_component_count,
            self.unseen_player_player_disjoint,
            self.unseen_player_local_move_optimal,
            self.unseen_player_local_swap_optimal,
        )
        if self.status == "unavailable":
            if (
                self.unavailable_reason is None
                or self.leakage_audit_status is not None
                or self.all_partitions_have_records is not None
                or self.mode_constraints_satisfied
                or self.partition_summaries
                or any(value is not None for value in (*known_values, *unseen_values))
            ):
                raise ValueError("Unavailable readiness must retain only source and reason facts.")
        else:
            if (
                self.unavailable_reason is not None
                or self.leakage_audit_status != "compliant"
                or self.all_partitions_have_records is not True
                or not self.mode_constraints_satisfied
                or len(self.partition_summaries) != 3
            ):
                raise ValueError("Complete readiness requires compliant supplied split facts.")
            if self.mode == "known_player":
                if any(value is None for value in known_values) or any(
                    value is not None for value in unseen_values
                ):
                    raise ValueError("Known-player readiness must retain only temporal facts.")
            elif any(value is None for value in unseen_values) or any(
                value is not None for value in known_values
            ):
                raise ValueError("Unseen-player readiness must retain only component facts.")
        if verify_identity and self.partition_readiness_id != _build_identifier(
            _PARTITION_READINESS_ID_DOMAIN,
            _identity_material(self, "partition_readiness_id"),
        ):
            raise ValueError("partition_readiness_id must cover the exact readiness value.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_partition_readiness_version": (
                self.learning_dataset_partition_readiness_version
            ),
            "partition_readiness_id": self.partition_readiness_id,
            "mode": self.mode,
            "algorithm": self.algorithm,
            "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "request_fingerprint": self.request_fingerprint,
            "plan_fingerprint": self.plan_fingerprint,
            "base_random_seed": self.base_random_seed,
            "requested_partition_weights": self.requested_partition_weights.to_dict(),
            "source_active_match_group_count": self.source_active_match_group_count,
            "source_inactive_match_count": self.source_inactive_match_count,
            "source_record_count": self.source_record_count,
            "source_skipped_decision_count": self.source_skipped_decision_count,
            "leakage_audit_status": self.leakage_audit_status,
            "all_partitions_have_records": self.all_partitions_have_records,
            "mode_constraints_satisfied": self.mode_constraints_satisfied,
            "partition_summaries": [item.to_dict() for item in self.partition_summaries],
            "known_player_time_group_count": self.known_player_time_group_count,
            "known_player_validation_train_coverage_complete": (
                self.known_player_validation_train_coverage_complete
            ),
            "known_player_test_train_coverage_complete": (
                self.known_player_test_train_coverage_complete
            ),
            "unseen_player_component_count": self.unseen_player_component_count,
            "unseen_player_player_disjoint": self.unseen_player_player_disjoint,
            "unseen_player_local_move_optimal": self.unseen_player_local_move_optimal,
            "unseen_player_local_swap_optimal": self.unseen_player_local_swap_optimal,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetReadinessSummaryV1:
    learning_dataset_readiness_summary_version: int
    readiness_summary_fingerprint: str
    dataset_status: str
    decision_state_coverage: LearningDatasetSummaryCoverageV1
    evidence_family_coverages: tuple[LearningDatasetSummaryCoverageV1, ...]
    skipped_reason_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    player_context_total_count: int
    player_context_available_count: int
    player_context_unavailable_count: int
    player_context_unavailable_reason_counts: tuple[LearningDatasetSummaryCategoricalCountV1, ...]
    selected_statistics_context_count: int
    statistics_observation_pool_count: int
    unjoined_commentary_evidence_count: int
    unjoined_response_evidence_count: int
    partition_readiness: tuple[LearningDatasetPartitionReadinessV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetReadinessSummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetReadinessSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_readiness_summary_version,
            LEARNING_DATASET_READINESS_SUMMARY_VERSION,
            "learning_dataset_readiness_summary_version",
        )
        _require_hash(self.readiness_summary_fingerprint, "readiness_summary_fingerprint")
        if self.dataset_status not in {"empty", "unavailable", "partial", "complete"}:
            raise ValueError("dataset_status must be one canonical Learning Dataset status.")
        if type(self.decision_state_coverage) is not LearningDatasetSummaryCoverageV1:
            raise ValueError("decision_state_coverage must be one exact Coverage value.")
        self.decision_state_coverage._validate(verify_identity=True)
        if self.decision_state_coverage.family != "decision_state":
            raise ValueError("decision_state_coverage must use the decision_state family.")
        if type(self.evidence_family_coverages) is not tuple or any(
            type(item) is not LearningDatasetSummaryCoverageV1
            for item in self.evidence_family_coverages
        ):
            raise ValueError("evidence_family_coverages must contain exact Coverage values.")
        for item in self.evidence_family_coverages:
            item._validate(verify_identity=True)
        if (
            tuple(item.family for item in self.evidence_family_coverages)
            != (LEARNING_DATASET_SUMMARY_COVERAGE_FAMILIES[1:])
        ):
            raise ValueError("Evidence Coverage must use canonical non-state family order.")
        record_count = self.decision_state_coverage.covered_count
        if any(item.total_count != record_count for item in self.evidence_family_coverages):
            raise ValueError("Evidence-family Coverage must use safe Record Count.")
        skipped = _require_count_tuple(self.skipped_reason_counts, "skipped_reason_counts")
        _require_canonical_categories(
            skipped,
            "skipped_reason_counts",
            MATCH_DECISION_REVIEW_SKIP_REASONS,
            complete=True,
        )
        if _count_sum(skipped) != self.decision_state_coverage.uncovered_count:
            raise ValueError("Skipped reason Counts must cover skipped Decisions.")
        reasons = _require_count_tuple(
            self.player_context_unavailable_reason_counts,
            "player_context_unavailable_reason_counts",
        )
        _require_canonical_categories(
            reasons,
            "player_context_unavailable_reason_counts",
            LEARNING_DATASET_SUMMARY_PLAYER_CONTEXT_UNAVAILABLE_REASONS,
        )
        for field_name in (
            "player_context_total_count",
            "player_context_available_count",
            "player_context_unavailable_count",
            "selected_statistics_context_count",
            "statistics_observation_pool_count",
            "unjoined_commentary_evidence_count",
            "unjoined_response_evidence_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.player_context_total_count != record_count * 3 or (
            self.player_context_available_count + self.player_context_unavailable_count
            != self.player_context_total_count
        ):
            raise ValueError("Player Context totals must cover three contexts per Record.")
        if _count_sum(reasons) != self.player_context_unavailable_count:
            raise ValueError("Player Context reason Counts must cover unavailability.")
        if self.selected_statistics_context_count != self.player_context_available_count:
            raise ValueError("Selected Statistics Context Count must equal available Contexts.")
        if type(self.partition_readiness) is not tuple or any(
            type(item) is not LearningDatasetPartitionReadinessV1
            for item in self.partition_readiness
        ):
            raise ValueError("partition_readiness must contain exact readiness values.")
        if tuple(item.mode for item in self.partition_readiness) != (
            LEARNING_DATASET_PARTITION_MODES
        ):
            raise ValueError("partition_readiness must use canonical mode order.")
        for item in self.partition_readiness:
            item._validate(verify_identity=True)
        if verify_identity and self.readiness_summary_fingerprint != _build_identifier(
            _READINESS_SUMMARY_FINGERPRINT_DOMAIN,
            _identity_material(self, "readiness_summary_fingerprint"),
        ):
            raise ValueError("readiness_summary_fingerprint must cover the exact Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_readiness_summary_version": (
                self.learning_dataset_readiness_summary_version
            ),
            "readiness_summary_fingerprint": self.readiness_summary_fingerprint,
            "dataset_status": self.dataset_status,
            "decision_state_coverage": self.decision_state_coverage.to_dict(),
            "evidence_family_coverages": [
                item.to_dict() for item in self.evidence_family_coverages
            ],
            "skipped_reason_counts": [item.to_dict() for item in self.skipped_reason_counts],
            "player_context_total_count": self.player_context_total_count,
            "player_context_available_count": self.player_context_available_count,
            "player_context_unavailable_count": self.player_context_unavailable_count,
            "player_context_unavailable_reason_counts": [
                item.to_dict() for item in self.player_context_unavailable_reason_counts
            ],
            "selected_statistics_context_count": self.selected_statistics_context_count,
            "statistics_observation_pool_count": self.statistics_observation_pool_count,
            "unjoined_commentary_evidence_count": self.unjoined_commentary_evidence_count,
            "unjoined_response_evidence_count": self.unjoined_response_evidence_count,
            "partition_readiness": [item.to_dict() for item in self.partition_readiness],
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetCrossGameSummaryV1:
    learning_dataset_cross_game_summary_version: int
    cross_game_summary_fingerprint: str
    dataset_id: str
    dataset_fingerprint: str
    player_catalog_fingerprint: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    dataset_status: str
    retained_match_snapshot_count: int
    current_match_count: int
    orphan_match_snapshot_count: int
    observed_game_count: int
    observed_decision_count: int
    record_count: int
    skipped_decision_count: int
    player_count: int
    match_summaries: tuple[LearningDatasetMatchSummaryV1, ...]
    player_summaries: tuple[LearningDatasetPlayerSummaryV1, ...]
    communication_summary: LearningDatasetCommunicationSummaryV1
    strategy_summary: LearningDatasetStrategySummaryV1
    readiness_summary: LearningDatasetReadinessSummaryV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetCrossGameSummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetCrossGameSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_cross_game_summary_version,
            LEARNING_DATASET_CROSS_GAME_SUMMARY_VERSION,
            "learning_dataset_cross_game_summary_version",
        )
        _require_hash(self.cross_game_summary_fingerprint, "cross_game_summary_fingerprint")
        _require_identifier(self.dataset_id, "dataset_id")
        for field_name in (
            "dataset_fingerprint",
            "player_catalog_fingerprint",
            "source_catalog_fingerprint",
            "source_catalog_content_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        _require_identifier(self.corpus_id, "corpus_id")
        _require_count(self.source_catalog_revision, "source_catalog_revision")
        if type(self.current_match_snapshot_ids) is not tuple:
            raise ValueError("current_match_snapshot_ids must be immutable.")
        for item in self.current_match_snapshot_ids:
            _require_hash(item, "current_match_snapshot_ids")
        if len(self.current_match_snapshot_ids) != len(set(self.current_match_snapshot_ids)):
            raise ValueError("Current Match Snapshot IDs must be unique.")
        if self.dataset_status not in {"empty", "unavailable", "partial", "complete"}:
            raise ValueError("dataset_status must be one canonical Learning Dataset status.")
        for field_name in (
            "retained_match_snapshot_count",
            "current_match_count",
            "orphan_match_snapshot_count",
            "observed_game_count",
            "observed_decision_count",
            "record_count",
            "skipped_decision_count",
            "player_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.current_match_count != len(self.current_match_snapshot_ids):
            raise ValueError("current_match_count must reconcile exactly.")
        if self.observed_decision_count != self.record_count + self.skipped_decision_count:
            raise ValueError("Global Decision Counts must reconcile exactly.")
        if type(self.match_summaries) is not tuple or any(
            type(item) is not LearningDatasetMatchSummaryV1 for item in self.match_summaries
        ):
            raise ValueError("match_summaries must contain exact Match Summaries.")
        if self.match_summaries != tuple(
            sorted(self.match_summaries, key=lambda item: (item.match_id, item.match_snapshot_id))
        ):
            raise ValueError("Match Summaries must use canonical Match order.")
        for item in self.match_summaries:
            item._validate(verify_identity=True)
        if len(self.match_summaries) != self.current_match_count or {
            item.match_snapshot_id for item in self.match_summaries
        } != set(self.current_match_snapshot_ids):
            raise ValueError("Match Summaries must cover every Current Match exactly once.")
        if (
            sum(item.record_count for item in self.match_summaries) != self.record_count
            or sum(item.skipped_decision_count for item in self.match_summaries)
            != self.skipped_decision_count
        ):
            raise ValueError("Match Summary Decision Counts must reconcile globally.")
        if type(self.player_summaries) is not tuple or any(
            type(item) is not LearningDatasetPlayerSummaryV1 for item in self.player_summaries
        ):
            raise ValueError("player_summaries must contain exact Player Summaries.")
        if self.player_summaries != tuple(
            sorted(self.player_summaries, key=lambda item: item.player_id)
        ):
            raise ValueError("Player Summaries must use stable Player-ID order.")
        for item in self.player_summaries:
            item._validate(verify_identity=True)
        if self.player_count != len(self.player_summaries):
            raise ValueError("player_count must reconcile exactly.")
        if (
            sum(item.record_count for item in self.player_summaries) != self.record_count
            or sum(item.skipped_decision_count for item in self.player_summaries)
            != self.skipped_decision_count
        ):
            raise ValueError("Player Summary acting Decision Counts must reconcile globally.")
        if type(self.communication_summary) is not LearningDatasetCommunicationSummaryV1:
            raise ValueError("communication_summary must use the exact contract.")
        if type(self.strategy_summary) is not LearningDatasetStrategySummaryV1:
            raise ValueError("strategy_summary must use the exact contract.")
        if type(self.readiness_summary) is not LearningDatasetReadinessSummaryV1:
            raise ValueError("readiness_summary must use the exact contract.")
        self.communication_summary._validate(verify_identity=True)
        self.strategy_summary._validate(verify_identity=True)
        self.readiness_summary._validate(verify_identity=True)
        if (
            self.readiness_summary.dataset_status != self.dataset_status
            or self.readiness_summary.decision_state_coverage.covered_count != self.record_count
            or self.readiness_summary.decision_state_coverage.total_count
            != self.observed_decision_count
        ):
            raise ValueError("Readiness Summary must reconcile with global Dataset Counts.")
        if verify_identity and self.cross_game_summary_fingerprint != _build_identifier(
            _CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
            _identity_material(self, "cross_game_summary_fingerprint"),
        ):
            raise ValueError("cross_game_summary_fingerprint must cover the exact Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_cross_game_summary_version": (
                self.learning_dataset_cross_game_summary_version
            ),
            "cross_game_summary_fingerprint": self.cross_game_summary_fingerprint,
            "dataset_id": self.dataset_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "player_catalog_fingerprint": self.player_catalog_fingerprint,
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": self.source_catalog_content_fingerprint,
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "dataset_status": self.dataset_status,
            "retained_match_snapshot_count": self.retained_match_snapshot_count,
            "current_match_count": self.current_match_count,
            "orphan_match_snapshot_count": self.orphan_match_snapshot_count,
            "observed_game_count": self.observed_game_count,
            "observed_decision_count": self.observed_decision_count,
            "record_count": self.record_count,
            "skipped_decision_count": self.skipped_decision_count,
            "player_count": self.player_count,
            "match_summaries": [item.to_dict() for item in self.match_summaries],
            "player_summaries": [item.to_dict() for item in self.player_summaries],
            "communication_summary": self.communication_summary.to_dict(),
            "strategy_summary": self.strategy_summary.to_dict(),
            "readiness_summary": self.readiness_summary.to_dict(),
        }


def _identity_material(value: object, identity_field: str) -> dict[str, Any]:
    material = value.to_dict()
    del material[identity_field]
    return material


def _build_hashed_value(
    cls: Any,
    *,
    identity_field: str,
    domain: bytes,
    values: dict[str, Any],
) -> Any:
    provisional = cls._from_validated(**{identity_field: "0" * 64, **values})
    identity = _build_identifier(domain, _identity_material(provisional, identity_field))
    return cls._from_validated(**{identity_field: identity, **values})


def _build_match_summary_v1(**values: Any) -> LearningDatasetMatchSummaryV1:
    return _build_hashed_value(
        LearningDatasetMatchSummaryV1,
        identity_field="match_summary_id",
        domain=_MATCH_SUMMARY_ID_DOMAIN,
        values=values,
    )


def _build_player_summary_v1(**values: Any) -> LearningDatasetPlayerSummaryV1:
    return _build_hashed_value(
        LearningDatasetPlayerSummaryV1,
        identity_field="player_summary_id",
        domain=_PLAYER_SUMMARY_ID_DOMAIN,
        values=values,
    )


def _build_communication_summary_v1(
    **values: Any,
) -> LearningDatasetCommunicationSummaryV1:
    return _build_hashed_value(
        LearningDatasetCommunicationSummaryV1,
        identity_field="communication_summary_fingerprint",
        domain=_COMMUNICATION_SUMMARY_FINGERPRINT_DOMAIN,
        values=values,
    )


def _build_strategy_summary_v1(**values: Any) -> LearningDatasetStrategySummaryV1:
    return _build_hashed_value(
        LearningDatasetStrategySummaryV1,
        identity_field="strategy_summary_fingerprint",
        domain=_STRATEGY_SUMMARY_FINGERPRINT_DOMAIN,
        values=values,
    )


def _build_partition_readiness_v1(
    **values: Any,
) -> LearningDatasetPartitionReadinessV1:
    return _build_hashed_value(
        LearningDatasetPartitionReadinessV1,
        identity_field="partition_readiness_id",
        domain=_PARTITION_READINESS_ID_DOMAIN,
        values=values,
    )


def _build_readiness_summary_v1(
    **values: Any,
) -> LearningDatasetReadinessSummaryV1:
    return _build_hashed_value(
        LearningDatasetReadinessSummaryV1,
        identity_field="readiness_summary_fingerprint",
        domain=_READINESS_SUMMARY_FINGERPRINT_DOMAIN,
        values=values,
    )


def _build_cross_game_summary_v1(
    **values: Any,
) -> LearningDatasetCrossGameSummaryV1:
    return _build_hashed_value(
        LearningDatasetCrossGameSummaryV1,
        identity_field="cross_game_summary_fingerprint",
        domain=_CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
        values=values,
    )


def _validate_learning_dataset_cross_game_summary_v1(
    summary: LearningDatasetCrossGameSummaryV1,
) -> None:
    if type(summary) is not LearningDatasetCrossGameSummaryV1:
        raise ValueError("summary must be an exact LearningDatasetCrossGameSummaryV1.")
    summary._validate(verify_identity=True)
