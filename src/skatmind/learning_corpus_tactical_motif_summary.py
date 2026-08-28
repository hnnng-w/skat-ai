from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Final

from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_player_catalog import (
    LearningCorpusPlayerCatalogEntryV1,
    LearningCorpusPlayerCatalogV1,
    _validate_learning_corpus_player_catalog_v1,
)
from skatmind.learning_corpus_tactical_motif_evidence import (
    LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS,
    LEARNING_CORPUS_TACTICAL_MOTIF_PHASES,
    LEARNING_CORPUS_TACTICAL_MOTIF_ROLES,
    LEARNING_CORPUS_TACTICAL_MOTIF_SEATS,
    LearningCorpusSkippedTacticalMotifDecisionV1,
    LearningCorpusTacticalMotifEvidenceCollectionV1,
    LearningCorpusTacticalMotifEvidenceV1,
    _require_count,
    _require_hash,
    _require_hash_tuple,
    _require_identifier,
    _require_version,
    _validate_learning_corpus_tactical_motif_collection_v1,
)
from skatmind.tactical_motif_contracts import (
    TACTICAL_MOTIF_FAMILIES,
    TACTICAL_MOTIF_FAMILY_BY_TYPE,
    TACTICAL_MOTIF_TYPES,
)

LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_VERSION = 1
LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_VERSION = 1
LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_VERSION = 1
LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_VERSION = 1

LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_SCOPES: Final[tuple[str, ...]] = (
    "single_game_only",
    "multiple_games_one_match",
    "multiple_matches",
)
LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_SCOPES: Final[tuple[str, ...]] = (
    "role",
    "seat",
    "phase",
    "contract",
)
LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_LIMITATIONS: Final[tuple[str, ...]] = (
    "current_match_snapshots_only",
    "structural_observation_not_quality_assessment",
    "actual_card_not_ground_truth",
    "skipped_decisions_are_not_inferred",
    "distinct_game_and_match_counts_are_not_player_traits",
    "counts_are_not_rates_or_statistical_significance",
    "no_intent_signaling_or_communication_claim",
    "no_commentary_or_response_interpretation",
    "no_strategy_teacher_join_or_method_preference",
    "no_cross_game_coaching_or_recommendation",
    "no_learning_dataset_v2_mutation",
)

LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_motif_scope_summary_v1\0"
)
LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_motif_player_summary_v1\0"
)
LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_motif_recurrence_v1\0"
)
LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_motif_cross_game_summary_v1\0"
)

_SCOPE_VALUES = {
    "role": LEARNING_CORPUS_TACTICAL_MOTIF_ROLES,
    "seat": LEARNING_CORPUS_TACTICAL_MOTIF_SEATS,
    "phase": LEARNING_CORPUS_TACTICAL_MOTIF_PHASES,
    "contract": LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS,
}


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def _identity_material(value: object, identity_field: str) -> dict[str, Any]:
    material = value.to_dict()
    del material[identity_field]
    return material


def _require_string_tuple(
    value: object,
    field_name: str,
    *,
    hashes: bool = False,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for item in value:
        if hashes:
            _require_hash(item, field_name)
        else:
            _require_identifier(item, field_name)
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must contain unique values.")
    return value


def _require_canonical_counts(
    value: object,
    field_name: str,
    canonical_values: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    if any(type(item) is not tuple or len(item) != 2 for item in value):
        raise ValueError(f"{field_name} must contain immutable Count pairs.")
    if tuple(item[0] for item in value) != canonical_values:
        raise ValueError(f"{field_name} must follow canonical taxonomy order.")
    for _, count in value:
        _require_count(count, field_name)
    return value


def _game_phase(trick_number: int) -> str:
    if 1 <= trick_number <= 3:
        return "opening"
    if 4 <= trick_number <= 7:
        return "middle"
    if 8 <= trick_number <= 10:
        return "endgame"
    raise ValueError("Tactical Decisions require Tricks 1 through 10.")


@dataclass(frozen=True, slots=True)
class _DecisionItem:
    match_snapshot_id: str
    match_id: str
    match_position: int
    game_reference_id: str
    game_id: str
    decision_reference_id: str
    decision_index: int
    acting_player_id: str
    acting_side: str
    acting_seat: str
    phase: str
    game_type: str
    observation_status: str | None
    evidence_id: str | None
    motif_types: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifScopeSummaryV1:
    learning_corpus_tactical_motif_scope_summary_version: int
    scope_summary_id: str
    scope: str
    scope_value: str
    decision_count: int
    evidence_count: int
    skipped_decision_count: int
    complete_observation_count: int
    partial_observation_count: int
    motif_occurrence_count: int
    distinct_game_count: int
    distinct_match_count: int
    motif_counts: tuple[tuple[str, int], ...]
    motif_game_counts: tuple[tuple[str, int], ...]
    motif_match_counts: tuple[tuple[str, int], ...]
    family_counts: tuple[tuple[str, int], ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusTacticalMotifScopeSummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalMotifScopeSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_scope_summary_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_VERSION,
            "learning_corpus_tactical_motif_scope_summary_version",
        )
        _require_hash(self.scope_summary_id, "scope_summary_id")
        if self.scope not in LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_SCOPES:
            raise ValueError("scope must be canonical.")
        if self.scope_value not in _SCOPE_VALUES[self.scope]:
            raise ValueError("scope_value must be canonical for its scope.")
        for field_name in (
            "decision_count",
            "evidence_count",
            "skipped_decision_count",
            "complete_observation_count",
            "partial_observation_count",
            "motif_occurrence_count",
            "distinct_game_count",
            "distinct_match_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.decision_count != self.evidence_count + self.skipped_decision_count:
            raise ValueError("Scope Decision Counts must reconcile exactly.")
        if self.evidence_count != (
            self.complete_observation_count + self.partial_observation_count
        ):
            raise ValueError("Scope Observation Counts must reconcile exactly.")
        if self.distinct_match_count > self.distinct_game_count:
            raise ValueError("Scope Match Count cannot exceed Game Count.")
        for field_name in (
            "motif_counts",
            "motif_game_counts",
            "motif_match_counts",
        ):
            _require_canonical_counts(
                getattr(self, field_name),
                field_name,
                TACTICAL_MOTIF_TYPES,
            )
        _require_canonical_counts(
            self.family_counts,
            "family_counts",
            TACTICAL_MOTIF_FAMILIES,
        )
        if sum(count for _, count in self.motif_counts) != self.motif_occurrence_count:
            raise ValueError("Scope motif Counts must reconcile exactly.")
        if sum(count for _, count in self.family_counts) != self.motif_occurrence_count:
            raise ValueError("Scope family Counts must reconcile exactly.")
        if any(
            game_count > occurrence_count or match_count > game_count
            for (_, occurrence_count), (_, game_count), (_, match_count) in zip(
                self.motif_counts,
                self.motif_game_counts,
                self.motif_match_counts,
                strict=True,
            )
        ):
            raise ValueError("Scope motif occurrence, Game, and Match Counts are invalid.")
        if verify_identity and self.scope_summary_id != _build_identifier(
            LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_ID_DOMAIN,
            _identity_material(self, "scope_summary_id"),
        ):
            raise ValueError("scope_summary_id must cover the exact Scope Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_scope_summary_version": (
                self.learning_corpus_tactical_motif_scope_summary_version
            ),
            "scope_summary_id": self.scope_summary_id,
            "scope": self.scope,
            "scope_value": self.scope_value,
            "decision_count": self.decision_count,
            "evidence_count": self.evidence_count,
            "skipped_decision_count": self.skipped_decision_count,
            "complete_observation_count": self.complete_observation_count,
            "partial_observation_count": self.partial_observation_count,
            "motif_occurrence_count": self.motif_occurrence_count,
            "distinct_game_count": self.distinct_game_count,
            "distinct_match_count": self.distinct_match_count,
            "motif_counts": _serialize_counts(self.motif_counts, "motif_type"),
            "motif_game_counts": _serialize_counts(
                self.motif_game_counts,
                "motif_type",
            ),
            "motif_match_counts": _serialize_counts(
                self.motif_match_counts,
                "motif_type",
            ),
            "family_counts": _serialize_counts(
                self.family_counts,
                "motif_family",
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifPlayerSummaryV1:
    learning_corpus_tactical_motif_player_summary_version: int
    player_summary_id: str
    player_id: str
    observed_labels: tuple[str, ...]
    match_ids: tuple[str, ...]
    current_match_snapshot_ids: tuple[str, ...]
    match_count: int
    game_count: int
    decision_count: int
    evidence_count: int
    skipped_decision_count: int
    complete_observation_count: int
    partial_observation_count: int
    motif_occurrence_count: int
    motif_counts: tuple[tuple[str, int], ...]
    motif_game_counts: tuple[tuple[str, int], ...]
    motif_match_counts: tuple[tuple[str, int], ...]
    family_counts: tuple[tuple[str, int], ...]
    role_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]
    seat_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]
    phase_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]
    contract_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusTacticalMotifPlayerSummaryV1 requires its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalMotifPlayerSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_player_summary_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_VERSION,
            "learning_corpus_tactical_motif_player_summary_version",
        )
        _require_hash(self.player_summary_id, "player_summary_id")
        _require_identifier(self.player_id, "player_id")
        _require_string_tuple(self.observed_labels, "observed_labels")
        _require_string_tuple(self.match_ids, "match_ids")
        _require_hash_tuple(
            self.current_match_snapshot_ids,
            "current_match_snapshot_ids",
        )
        if self.observed_labels != tuple(sorted(self.observed_labels)):
            raise ValueError("observed_labels must use sorted exact label history.")
        for field_name in (
            "match_count",
            "game_count",
            "decision_count",
            "evidence_count",
            "skipped_decision_count",
            "complete_observation_count",
            "partial_observation_count",
            "motif_occurrence_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.match_count != len(self.match_ids) or self.match_count != len(
            self.current_match_snapshot_ids
        ):
            raise ValueError("Player Match identities and Count must reconcile exactly.")
        if self.decision_count != self.evidence_count + self.skipped_decision_count:
            raise ValueError("Player Decision Counts must reconcile exactly.")
        if self.evidence_count != (
            self.complete_observation_count + self.partial_observation_count
        ):
            raise ValueError("Player Observation Counts must reconcile exactly.")
        for field_name in (
            "motif_counts",
            "motif_game_counts",
            "motif_match_counts",
        ):
            _require_canonical_counts(
                getattr(self, field_name),
                field_name,
                TACTICAL_MOTIF_TYPES,
            )
        _require_canonical_counts(
            self.family_counts,
            "family_counts",
            TACTICAL_MOTIF_FAMILIES,
        )
        if sum(count for _, count in self.motif_counts) != self.motif_occurrence_count:
            raise ValueError("Player motif Counts must reconcile exactly.")
        if sum(count for _, count in self.family_counts) != self.motif_occurrence_count:
            raise ValueError("Player family Counts must reconcile exactly.")
        groups = (
            ("role", self.role_summaries),
            ("seat", self.seat_summaries),
            ("phase", self.phase_summaries),
            ("contract", self.contract_summaries),
        )
        for scope, summaries in groups:
            _validate_scope_group(
                scope=scope,
                summaries=summaries,
                decision_count=self.decision_count,
                evidence_count=self.evidence_count,
                skipped_decision_count=self.skipped_decision_count,
                motif_occurrence_count=self.motif_occurrence_count,
            )
        if verify_identity and self.player_summary_id != _build_identifier(
            LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_ID_DOMAIN,
            _identity_material(self, "player_summary_id"),
        ):
            raise ValueError("player_summary_id must cover the exact Player Summary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_player_summary_version": (
                self.learning_corpus_tactical_motif_player_summary_version
            ),
            "player_summary_id": self.player_summary_id,
            "player_id": self.player_id,
            "observed_labels": list(self.observed_labels),
            "match_ids": list(self.match_ids),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "match_count": self.match_count,
            "game_count": self.game_count,
            "decision_count": self.decision_count,
            "evidence_count": self.evidence_count,
            "skipped_decision_count": self.skipped_decision_count,
            "complete_observation_count": self.complete_observation_count,
            "partial_observation_count": self.partial_observation_count,
            "motif_occurrence_count": self.motif_occurrence_count,
            "motif_counts": _serialize_counts(self.motif_counts, "motif_type"),
            "motif_game_counts": _serialize_counts(
                self.motif_game_counts,
                "motif_type",
            ),
            "motif_match_counts": _serialize_counts(
                self.motif_match_counts,
                "motif_type",
            ),
            "family_counts": _serialize_counts(
                self.family_counts,
                "motif_family",
            ),
            "role_summaries": [item.to_dict() for item in self.role_summaries],
            "seat_summaries": [item.to_dict() for item in self.seat_summaries],
            "phase_summaries": [item.to_dict() for item in self.phase_summaries],
            "contract_summaries": [item.to_dict() for item in self.contract_summaries],
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifRecurrenceV1:
    learning_corpus_tactical_motif_recurrence_version: int
    recurrence_id: str
    player_id: str
    motif_type: str
    motif_family: str
    recurrence_scope: str
    occurrence_count: int
    decision_count: int
    game_count: int
    match_count: int
    tactical_motif_evidence_ids: tuple[str, ...]
    game_reference_ids: tuple[str, ...]
    game_ids: tuple[str, ...]
    match_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusTacticalMotifRecurrenceV1 requires its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalMotifRecurrenceV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_recurrence_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_VERSION,
            "learning_corpus_tactical_motif_recurrence_version",
        )
        _require_hash(self.recurrence_id, "recurrence_id")
        _require_identifier(self.player_id, "player_id")
        if self.motif_type not in TACTICAL_MOTIF_TYPES:
            raise ValueError("motif_type must be canonical.")
        if self.motif_family != TACTICAL_MOTIF_FAMILY_BY_TYPE[self.motif_type]:
            raise ValueError("motif_family must match motif_type.")
        if self.recurrence_scope not in LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_SCOPES:
            raise ValueError("recurrence_scope must be canonical.")
        for field_name in (
            "occurrence_count",
            "decision_count",
            "game_count",
            "match_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.occurrence_count <= 0 or self.decision_count != self.occurrence_count:
            raise ValueError("Recurrence requires positive one-per-Decision occurrences.")
        _require_hash_tuple(
            self.tactical_motif_evidence_ids,
            "tactical_motif_evidence_ids",
        )
        _require_hash_tuple(self.game_reference_ids, "game_reference_ids")
        _require_string_tuple(self.game_ids, "game_ids")
        _require_string_tuple(self.match_ids, "match_ids")
        if self.occurrence_count != len(self.tactical_motif_evidence_ids):
            raise ValueError("Recurrence Evidence IDs must cover every occurrence.")
        if self.game_count != len(self.game_reference_ids):
            raise ValueError("game_count must use distinct Game Reference identities.")
        if not 1 <= len(self.game_ids) <= self.game_count:
            raise ValueError("game_ids must retain unique source Game IDs.")
        if self.match_count != len(self.match_ids):
            raise ValueError("match_count must reconcile with match_ids.")
        expected_scope = (
            "multiple_matches"
            if self.match_count >= 2
            else "multiple_games_one_match"
            if self.game_count >= 2
            else "single_game_only"
        )
        if self.recurrence_scope != expected_scope:
            raise ValueError("recurrence_scope must match distinct source Counts.")
        if verify_identity and self.recurrence_id != _build_identifier(
            LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_ID_DOMAIN,
            _identity_material(self, "recurrence_id"),
        ):
            raise ValueError("recurrence_id must cover the exact Recurrence.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_recurrence_version": (
                self.learning_corpus_tactical_motif_recurrence_version
            ),
            "recurrence_id": self.recurrence_id,
            "player_id": self.player_id,
            "motif_type": self.motif_type,
            "motif_family": self.motif_family,
            "recurrence_scope": self.recurrence_scope,
            "occurrence_count": self.occurrence_count,
            "decision_count": self.decision_count,
            "game_count": self.game_count,
            "match_count": self.match_count,
            "tactical_motif_evidence_ids": list(self.tactical_motif_evidence_ids),
            "game_reference_ids": list(self.game_reference_ids),
            "game_ids": list(self.game_ids),
            "match_ids": list(self.match_ids),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifCrossGameSummaryV1:
    learning_corpus_tactical_motif_cross_game_summary_version: int
    tactical_motif_cross_game_summary_fingerprint: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    player_catalog_fingerprint: str
    tactical_motif_collection_fingerprint: str
    collection_status: str
    observed_game_count: int
    observed_decision_count: int
    evidence_count: int
    skipped_decision_count: int
    complete_observation_count: int
    partial_observation_count: int
    motif_occurrence_count: int
    motif_counts: tuple[tuple[str, int], ...]
    motif_game_counts: tuple[tuple[str, int], ...]
    motif_match_counts: tuple[tuple[str, int], ...]
    family_counts: tuple[tuple[str, int], ...]
    player_summaries: tuple[LearningCorpusTacticalMotifPlayerSummaryV1, ...]
    role_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]
    seat_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]
    phase_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]
    contract_summaries: tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...]
    recurrences: tuple[LearningCorpusTacticalMotifRecurrenceV1, ...]
    limitations: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalMotifCrossGameSummaryV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalMotifCrossGameSummaryV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_cross_game_summary_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_VERSION,
            "learning_corpus_tactical_motif_cross_game_summary_version",
        )
        for field_name in (
            "tactical_motif_cross_game_summary_fingerprint",
            "source_catalog_fingerprint",
            "source_catalog_content_fingerprint",
            "player_catalog_fingerprint",
            "tactical_motif_collection_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        _require_identifier(self.corpus_id, "corpus_id")
        _require_count(self.source_catalog_revision, "source_catalog_revision")
        _require_hash_tuple(
            self.current_match_snapshot_ids,
            "current_match_snapshot_ids",
        )
        for field_name in (
            "observed_game_count",
            "observed_decision_count",
            "evidence_count",
            "skipped_decision_count",
            "complete_observation_count",
            "partial_observation_count",
            "motif_occurrence_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.collection_status not in ("empty", "partial", "complete"):
            raise ValueError("collection_status must be canonical.")
        if self.observed_decision_count != (
            self.evidence_count + self.skipped_decision_count
        ) or self.evidence_count != (
            self.complete_observation_count + self.partial_observation_count
        ):
            raise ValueError("Global Tactical Decision Counts must reconcile exactly.")
        for field_name in (
            "motif_counts",
            "motif_game_counts",
            "motif_match_counts",
        ):
            _require_canonical_counts(
                getattr(self, field_name),
                field_name,
                TACTICAL_MOTIF_TYPES,
            )
        _require_canonical_counts(
            self.family_counts,
            "family_counts",
            TACTICAL_MOTIF_FAMILIES,
        )
        if sum(count for _, count in self.motif_counts) != self.motif_occurrence_count:
            raise ValueError("Global motif Counts must reconcile exactly.")
        if sum(count for _, count in self.family_counts) != self.motif_occurrence_count:
            raise ValueError("Global family Counts must reconcile exactly.")
        if type(self.player_summaries) is not tuple or any(
            type(item) is not LearningCorpusTacticalMotifPlayerSummaryV1
            for item in self.player_summaries
        ):
            raise ValueError("player_summaries must contain exact immutable values.")
        for item in self.player_summaries:
            item._validate(verify_identity=True)
        if len({item.player_id for item in self.player_summaries}) != len(self.player_summaries):
            raise ValueError("Player Summaries must have unique stable Player IDs.")
        for scope, summaries in (
            ("role", self.role_summaries),
            ("seat", self.seat_summaries),
            ("phase", self.phase_summaries),
            ("contract", self.contract_summaries),
        ):
            _validate_scope_group(
                scope=scope,
                summaries=summaries,
                decision_count=self.observed_decision_count,
                evidence_count=self.evidence_count,
                skipped_decision_count=self.skipped_decision_count,
                motif_occurrence_count=self.motif_occurrence_count,
            )
        if type(self.recurrences) is not tuple or any(
            type(item) is not LearningCorpusTacticalMotifRecurrenceV1 for item in self.recurrences
        ):
            raise ValueError("recurrences must contain exact immutable values.")
        for item in self.recurrences:
            item._validate(verify_identity=True)
        if self.limitations != LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_LIMITATIONS:
            raise ValueError("limitations must retain exact canonical order.")
        if verify_fingerprint and self.tactical_motif_cross_game_summary_fingerprint != (
            _build_identifier(
                LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
                _identity_material(
                    self,
                    "tactical_motif_cross_game_summary_fingerprint",
                ),
            )
        ):
            raise ValueError(
                "tactical_motif_cross_game_summary_fingerprint must cover the exact Summary."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_cross_game_summary_version": (
                self.learning_corpus_tactical_motif_cross_game_summary_version
            ),
            "tactical_motif_cross_game_summary_fingerprint": (
                self.tactical_motif_cross_game_summary_fingerprint
            ),
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": (self.source_catalog_content_fingerprint),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "player_catalog_fingerprint": self.player_catalog_fingerprint,
            "tactical_motif_collection_fingerprint": (self.tactical_motif_collection_fingerprint),
            "collection_status": self.collection_status,
            "observed_game_count": self.observed_game_count,
            "observed_decision_count": self.observed_decision_count,
            "evidence_count": self.evidence_count,
            "skipped_decision_count": self.skipped_decision_count,
            "complete_observation_count": self.complete_observation_count,
            "partial_observation_count": self.partial_observation_count,
            "motif_occurrence_count": self.motif_occurrence_count,
            "motif_counts": _serialize_counts(self.motif_counts, "motif_type"),
            "motif_game_counts": _serialize_counts(
                self.motif_game_counts,
                "motif_type",
            ),
            "motif_match_counts": _serialize_counts(
                self.motif_match_counts,
                "motif_type",
            ),
            "family_counts": _serialize_counts(
                self.family_counts,
                "motif_family",
            ),
            "player_summaries": [item.to_dict() for item in self.player_summaries],
            "role_summaries": [item.to_dict() for item in self.role_summaries],
            "seat_summaries": [item.to_dict() for item in self.seat_summaries],
            "phase_summaries": [item.to_dict() for item in self.phase_summaries],
            "contract_summaries": [item.to_dict() for item in self.contract_summaries],
            "recurrences": [item.to_dict() for item in self.recurrences],
            "limitations": list(self.limitations),
        }


def _serialize_counts(
    values: tuple[tuple[str, int], ...],
    category_name: str,
) -> list[dict[str, int | str]]:
    return [{category_name: category, "count": count} for category, count in values]


def _validate_scope_group(
    *,
    scope: str,
    summaries: object,
    decision_count: int,
    evidence_count: int,
    skipped_decision_count: int,
    motif_occurrence_count: int,
) -> None:
    if type(summaries) is not tuple or any(
        type(item) is not LearningCorpusTacticalMotifScopeSummaryV1 for item in summaries
    ):
        raise ValueError(f"{scope}_summaries must contain exact immutable values.")
    if tuple(item.scope_value for item in summaries) != _SCOPE_VALUES[scope] or any(
        item.scope != scope for item in summaries
    ):
        raise ValueError(f"{scope}_summaries must use complete canonical scope order.")
    for item in summaries:
        item._validate(verify_identity=True)
    if (
        sum(item.decision_count for item in summaries) != decision_count
        or sum(item.evidence_count for item in summaries) != evidence_count
        or sum(item.skipped_decision_count for item in summaries) != skipped_decision_count
        or sum(item.motif_occurrence_count for item in summaries) != motif_occurrence_count
    ):
        raise ValueError(f"{scope}_summaries must reconcile exact aggregate Counts.")


def _summary_counts(
    records: tuple[_DecisionItem, ...],
) -> dict[str, object]:
    evidence = tuple(item for item in records if item.evidence_id is not None)
    motif_counts = tuple(
        (
            motif_type,
            sum(motif_type in item.motif_types for item in evidence),
        )
        for motif_type in TACTICAL_MOTIF_TYPES
    )
    motif_game_counts = tuple(
        (
            motif_type,
            len({item.game_reference_id for item in evidence if motif_type in item.motif_types}),
        )
        for motif_type in TACTICAL_MOTIF_TYPES
    )
    motif_match_counts = tuple(
        (
            motif_type,
            len({item.match_id for item in evidence if motif_type in item.motif_types}),
        )
        for motif_type in TACTICAL_MOTIF_TYPES
    )
    family_counts = tuple(
        (
            family,
            sum(
                TACTICAL_MOTIF_FAMILY_BY_TYPE[motif_type] == family
                for item in evidence
                for motif_type in item.motif_types
            ),
        )
        for family in TACTICAL_MOTIF_FAMILIES
    )
    return {
        "decision_count": len(records),
        "evidence_count": len(evidence),
        "skipped_decision_count": len(records) - len(evidence),
        "complete_observation_count": sum(
            item.observation_status == "complete" for item in evidence
        ),
        "partial_observation_count": sum(item.observation_status == "partial" for item in evidence),
        "motif_occurrence_count": sum(len(item.motif_types) for item in evidence),
        "distinct_game_count": len({item.game_reference_id for item in records}),
        "distinct_match_count": len({item.match_id for item in records}),
        "motif_counts": motif_counts,
        "motif_game_counts": motif_game_counts,
        "motif_match_counts": motif_match_counts,
        "family_counts": family_counts,
    }


def _build_scope_summary(
    *,
    scope: str,
    scope_value: str,
    records: tuple[_DecisionItem, ...],
) -> LearningCorpusTacticalMotifScopeSummaryV1:
    selected = tuple(
        item
        for item in records
        if getattr(
            item,
            {
                "role": "acting_side",
                "seat": "acting_seat",
                "phase": "phase",
                "contract": "game_type",
            }[scope],
        )
        == scope_value
    )
    values = {
        "learning_corpus_tactical_motif_scope_summary_version": (
            LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_VERSION
        ),
        "scope_summary_id": "0" * 64,
        "scope": scope,
        "scope_value": scope_value,
        **_summary_counts(selected),
    }
    provisional = LearningCorpusTacticalMotifScopeSummaryV1._from_validated(**values)
    values["scope_summary_id"] = _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_ID_DOMAIN,
        _identity_material(provisional, "scope_summary_id"),
    )
    return LearningCorpusTacticalMotifScopeSummaryV1._from_validated(**values)


def _build_scope_groups(
    records: tuple[_DecisionItem, ...],
) -> tuple[
    tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...],
    tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...],
    tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...],
    tuple[LearningCorpusTacticalMotifScopeSummaryV1, ...],
]:
    return tuple(
        tuple(
            _build_scope_summary(
                scope=scope,
                scope_value=scope_value,
                records=records,
            )
            for scope_value in _SCOPE_VALUES[scope]
        )
        for scope in LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_SCOPES
    )


def _build_player_summary(
    *,
    catalog_entry: LearningCorpusPlayerCatalogEntryV1,
    records: tuple[_DecisionItem, ...],
) -> LearningCorpusTacticalMotifPlayerSummaryV1:
    counts = _summary_counts(records)
    role, seat, phase, contract = _build_scope_groups(records)
    values = {
        "learning_corpus_tactical_motif_player_summary_version": (
            LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_VERSION
        ),
        "player_summary_id": "0" * 64,
        "player_id": catalog_entry.player_id,
        "observed_labels": catalog_entry.observed_labels,
        "match_ids": catalog_entry.match_ids,
        "current_match_snapshot_ids": catalog_entry.current_match_snapshot_ids,
        "match_count": catalog_entry.match_count,
        "game_count": counts["distinct_game_count"],
        "decision_count": counts["decision_count"],
        "evidence_count": counts["evidence_count"],
        "skipped_decision_count": counts["skipped_decision_count"],
        "complete_observation_count": counts["complete_observation_count"],
        "partial_observation_count": counts["partial_observation_count"],
        "motif_occurrence_count": counts["motif_occurrence_count"],
        "motif_counts": counts["motif_counts"],
        "motif_game_counts": counts["motif_game_counts"],
        "motif_match_counts": counts["motif_match_counts"],
        "family_counts": counts["family_counts"],
        "role_summaries": role,
        "seat_summaries": seat,
        "phase_summaries": phase,
        "contract_summaries": contract,
    }
    provisional = LearningCorpusTacticalMotifPlayerSummaryV1._from_validated(**values)
    values["player_summary_id"] = _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_ID_DOMAIN,
        _identity_material(provisional, "player_summary_id"),
    )
    return LearningCorpusTacticalMotifPlayerSummaryV1._from_validated(**values)


def _build_recurrence(
    *,
    player_id: str,
    motif_type: str,
    records: tuple[_DecisionItem, ...],
) -> LearningCorpusTacticalMotifRecurrenceV1:
    game_reference_ids = tuple(dict.fromkeys(item.game_reference_id for item in records))
    game_ids = tuple(dict.fromkeys(item.game_id for item in records))
    match_ids = tuple(dict.fromkeys(item.match_id for item in records))
    recurrence_scope = (
        "multiple_matches"
        if len(match_ids) >= 2
        else "multiple_games_one_match"
        if len(game_reference_ids) >= 2
        else "single_game_only"
    )
    values = {
        "learning_corpus_tactical_motif_recurrence_version": (
            LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_VERSION
        ),
        "recurrence_id": "0" * 64,
        "player_id": player_id,
        "motif_type": motif_type,
        "motif_family": TACTICAL_MOTIF_FAMILY_BY_TYPE[motif_type],
        "recurrence_scope": recurrence_scope,
        "occurrence_count": len(records),
        "decision_count": len(records),
        "game_count": len(game_reference_ids),
        "match_count": len(match_ids),
        "tactical_motif_evidence_ids": tuple(
            item.evidence_id for item in records if item.evidence_id is not None
        ),
        "game_reference_ids": game_reference_ids,
        "game_ids": game_ids,
        "match_ids": match_ids,
    }
    provisional = LearningCorpusTacticalMotifRecurrenceV1._from_validated(**values)
    values["recurrence_id"] = _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_ID_DOMAIN,
        _identity_material(provisional, "recurrence_id"),
    )
    return LearningCorpusTacticalMotifRecurrenceV1._from_validated(**values)


def _evidence_item(evidence: LearningCorpusTacticalMotifEvidenceV1) -> _DecisionItem:
    facts = evidence.observation.decision_time_facts
    return _DecisionItem(
        match_snapshot_id=evidence.match_snapshot_id,
        match_id=evidence.match_id,
        match_position=evidence.match_position,
        game_reference_id=evidence.game_reference_id,
        game_id=evidence.game_id,
        decision_reference_id=evidence.decision_reference_id,
        decision_index=evidence.decision_index,
        acting_player_id=evidence.acting_player_id,
        acting_side=facts.acting_side,
        acting_seat=facts.acting_seat,
        phase=_game_phase(facts.trick_number),
        game_type=facts.game_type,
        observation_status=evidence.observation.observation_status,
        evidence_id=evidence.tactical_motif_evidence_id,
        motif_types=tuple(item.motif_type for item in evidence.observation.motifs),
    )


def _skipped_item(
    skipped: LearningCorpusSkippedTacticalMotifDecisionV1,
) -> _DecisionItem:
    return _DecisionItem(
        match_snapshot_id=skipped.match_snapshot_id,
        match_id=skipped.match_id,
        match_position=skipped.match_position,
        game_reference_id=skipped.game_reference_id,
        game_id=skipped.game_id,
        decision_reference_id=skipped.decision_reference_id,
        decision_index=skipped.decision_index,
        acting_player_id=skipped.acting_player_id,
        acting_side=skipped.acting_side,
        acting_seat=skipped.acting_seat,
        phase=_game_phase(skipped.trick_number),
        game_type=skipped.game_type,
        observation_status=None,
        evidence_id=None,
        motif_types=(),
    )


def build_learning_corpus_tactical_motif_cross_game_summary_v1(
    collection: LearningCorpusTacticalMotifEvidenceCollectionV1,
    player_catalog: LearningCorpusPlayerCatalogV1,
) -> LearningCorpusTacticalMotifCrossGameSummaryV1:
    """Aggregates exact descriptive Tactical Counts without source regeneration."""
    _validate_learning_corpus_tactical_motif_collection_v1(collection)
    _validate_learning_corpus_player_catalog_v1(player_catalog)
    collection_source = (
        collection.corpus_id,
        collection.source_catalog_revision,
        collection.source_catalog_fingerprint,
        collection.source_catalog_content_fingerprint,
        collection.current_match_snapshot_ids,
        collection.retained_match_snapshot_count,
        collection.current_match_count,
        collection.orphan_match_snapshot_count,
    )
    catalog_source = (
        player_catalog.corpus_id,
        player_catalog.source_catalog_revision,
        player_catalog.source_catalog_fingerprint,
        player_catalog.source_catalog_content_fingerprint,
        player_catalog.current_match_snapshot_ids,
        player_catalog.retained_match_snapshot_count,
        player_catalog.current_match_count,
        player_catalog.orphan_match_snapshot_count,
    )
    if collection_source != catalog_source:
        raise ValueError("Tactical Collection and Player Catalog sources must match exactly.")

    records = []
    records_by_player: dict[str, list[_DecisionItem]] = {
        item.player_id: [] for item in player_catalog.players
    }
    recurrence_records: dict[tuple[str, str], list[_DecisionItem]] = {}
    for evidence in collection.evidences:
        item = _evidence_item(evidence)
        records.append(item)
        if item.acting_player_id not in records_by_player:
            raise ValueError("Every Tactical acting Player must resolve through the Catalog.")
        records_by_player[item.acting_player_id].append(item)
        for motif_type in item.motif_types:
            recurrence_records.setdefault(
                (item.acting_player_id, motif_type),
                [],
            ).append(item)
    for skipped in collection.skipped_decisions:
        item = _skipped_item(skipped)
        records.append(item)
        if item.acting_player_id not in records_by_player:
            raise ValueError("Every skipped acting Player must resolve through the Catalog.")
        records_by_player[item.acting_player_id].append(item)

    snapshot_rank = {
        snapshot_id: index
        for index, snapshot_id in enumerate(collection.current_match_snapshot_ids)
    }
    ordered_records = tuple(
        sorted(
            records,
            key=lambda item: (
                snapshot_rank[item.match_snapshot_id],
                item.match_position,
                item.decision_index,
            ),
        )
    )
    player_summaries = tuple(
        _build_player_summary(
            catalog_entry=entry,
            records=tuple(
                sorted(
                    records_by_player[entry.player_id],
                    key=lambda item: (
                        snapshot_rank[item.match_snapshot_id],
                        item.match_position,
                        item.decision_index,
                    ),
                )
            ),
        )
        for entry in player_catalog.players
    )
    role, seat, phase, contract = _build_scope_groups(ordered_records)
    recurrences = tuple(
        _build_recurrence(
            player_id=entry.player_id,
            motif_type=motif_type,
            records=tuple(recurrence_records[(entry.player_id, motif_type)]),
        )
        for entry in player_catalog.players
        for motif_type in TACTICAL_MOTIF_TYPES
        if (entry.player_id, motif_type) in recurrence_records
    )
    global_counts = _summary_counts(ordered_records)
    values = {
        "learning_corpus_tactical_motif_cross_game_summary_version": (
            LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_VERSION
        ),
        "tactical_motif_cross_game_summary_fingerprint": "0" * 64,
        "corpus_id": collection.corpus_id,
        "source_catalog_revision": collection.source_catalog_revision,
        "source_catalog_fingerprint": collection.source_catalog_fingerprint,
        "source_catalog_content_fingerprint": (collection.source_catalog_content_fingerprint),
        "current_match_snapshot_ids": collection.current_match_snapshot_ids,
        "player_catalog_fingerprint": player_catalog.player_catalog_fingerprint,
        "tactical_motif_collection_fingerprint": (collection.tactical_motif_collection_fingerprint),
        "collection_status": collection.status,
        "observed_game_count": collection.observed_game_count,
        "observed_decision_count": global_counts["decision_count"],
        "evidence_count": global_counts["evidence_count"],
        "skipped_decision_count": global_counts["skipped_decision_count"],
        "complete_observation_count": global_counts["complete_observation_count"],
        "partial_observation_count": global_counts["partial_observation_count"],
        "motif_occurrence_count": global_counts["motif_occurrence_count"],
        "motif_counts": global_counts["motif_counts"],
        "motif_game_counts": global_counts["motif_game_counts"],
        "motif_match_counts": global_counts["motif_match_counts"],
        "family_counts": global_counts["family_counts"],
        "player_summaries": player_summaries,
        "role_summaries": role,
        "seat_summaries": seat,
        "phase_summaries": phase,
        "contract_summaries": contract,
        "recurrences": recurrences,
        "limitations": LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_LIMITATIONS,
    }
    provisional = LearningCorpusTacticalMotifCrossGameSummaryV1._from_validated(**values)
    values["tactical_motif_cross_game_summary_fingerprint"] = _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
        _identity_material(
            provisional,
            "tactical_motif_cross_game_summary_fingerprint",
        ),
    )
    return LearningCorpusTacticalMotifCrossGameSummaryV1._from_validated(**values)


def _validate_learning_corpus_tactical_motif_cross_game_summary_v1(
    summary: LearningCorpusTacticalMotifCrossGameSummaryV1,
) -> None:
    if type(summary) is not LearningCorpusTacticalMotifCrossGameSummaryV1:
        raise ValueError("summary must be an exact LearningCorpusTacticalMotifCrossGameSummaryV1.")
    summary._validate(verify_fingerprint=True)
