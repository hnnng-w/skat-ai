from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Final

from skat_ai.deck import get_full_deck
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.match_decision_review_preparation import (
    MATCH_DECISION_REVIEW_SKIP_REASONS,
)
from skat_ai.rules import GAME_TYPES
from skat_ai.tactical_motif_contracts import (
    TACTICAL_MOTIF_FAMILIES,
    TACTICAL_MOTIF_TYPES,
    TacticalDecisionObservationV1,
    build_serializable_tactical_decision_observation_v1,
)

LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_VERSION = 1
LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_VERSION = 1
LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_VERSION = 1

LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_STATUSES: Final[tuple[str, ...]] = (
    "empty",
    "partial",
    "complete",
)

LEARNING_CORPUS_TACTICAL_MOTIF_SOURCE_POLICY = "explicit_current_match_snapshots_only"
LEARNING_CORPUS_TACTICAL_MOTIF_DECISION_POLICY = "safe_reconstructed_decision_or_explicit_skip"
LEARNING_CORPUS_TACTICAL_MOTIF_OBSERVATION_POLICY = (
    "reuse_exact_tactical_detector_without_search_or_coaching"
)
LEARNING_CORPUS_TACTICAL_MOTIF_IDENTITY_POLICY = (
    "exact_snapshot_game_and_decision_reference_identity"
)
LEARNING_CORPUS_TACTICAL_MOTIF_COVERAGE_POLICY = "every_observed_decision_is_evidence_or_skipped"
LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_POLICY = (
    "distinct_game_and_match_counts_without_trait_inference"
)
LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_POLICY = "exact_counts_without_rates_quality_or_significance"
LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_SEPARATION_POLICY = (
    "tactical_human_and_strategy_evidence_remain_separate"
)
LEARNING_CORPUS_TACTICAL_MOTIF_DATASET_POLICY = "no_learning_dataset_v2_contract_or_record_mutation"
LEARNING_CORPUS_TACTICAL_MOTIF_PREPARATION_POLICY = (
    "process_local_explicit_generation_safe_preparation"
)
LEARNING_CORPUS_TACTICAL_MOTIF_EXPORT_POLICY = "deterministic_path_free_private_json"
LEARNING_CORPUS_TACTICAL_MOTIF_PUBLIC_POLICY = (
    "private_corpus_downloads_without_public_schema_or_api"
)

LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_ID_DOMAIN = (
    b"skat-ai\0learning_corpus_tactical_motif_evidence_v1\0"
)
LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_ID_DOMAIN = (
    b"skat-ai\0learning_corpus_tactical_motif_skipped_decision_v1\0"
)
LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_FINGERPRINT_DOMAIN = (
    b"skat-ai\0learning_corpus_tactical_motif_collection_v1\0"
)

LEARNING_CORPUS_TACTICAL_MOTIF_ROLES: Final[tuple[str, ...]] = (
    "declarer",
    "defenders",
)
LEARNING_CORPUS_TACTICAL_MOTIF_SEATS: Final[tuple[str, ...]] = (
    "forehand",
    "middlehand",
    "rearhand",
)
LEARNING_CORPUS_TACTICAL_MOTIF_PHASES: Final[tuple[str, ...]] = (
    "opening",
    "middle",
    "endgame",
)
LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS: Final[tuple[str, ...]] = tuple(GAME_TYPES)

_VALID_CARDS = frozenset(get_full_deck())


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


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


def _require_hash_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for item in value:
        _require_hash(item, field_name)
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must contain unique IDs.")
    return value


def _require_canonical_counts(
    value: object,
    field_name: str,
    canonical_values: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    if type(value) is not tuple or tuple(item[0] for item in value) != canonical_values:
        raise ValueError(f"{field_name} must follow canonical taxonomy order.")
    for item in value:
        if type(item) is not tuple or len(item) != 2:
            raise ValueError(f"{field_name} must contain immutable Count pairs.")
        _require_count(item[1], field_name)
    return value


def _scope_fields(
    value: LearningCorpusSkippedTacticalMotifDecisionV1,
) -> tuple[str, str, str]:
    acting_seat = value.acting_seat
    acting_side = value.acting_side
    game_type = value.game_type
    if acting_seat not in LEARNING_CORPUS_TACTICAL_MOTIF_SEATS:
        raise ValueError("acting_seat must be canonical.")
    if acting_side not in LEARNING_CORPUS_TACTICAL_MOTIF_ROLES:
        raise ValueError("acting_side must be declarer or defenders.")
    if game_type not in LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS:
        raise ValueError("game_type must be canonical.")
    return acting_seat, acting_side, game_type


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifEvidenceV1:
    """One exact retained actual play with its safe Tactical Observation."""

    learning_corpus_tactical_motif_evidence_version: int
    tactical_motif_evidence_id: str
    match_snapshot_id: str
    workspace_revision: int
    game_reference_id: str
    decision_reference_id: str
    match_id: str
    match_position: int
    game_id: str
    decision_index: int
    acting_player_id: str
    actual_card_played: str
    observation: TacticalDecisionObservationV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusTacticalMotifEvidenceV1 requires its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalMotifEvidenceV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_evidence_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_VERSION,
            "learning_corpus_tactical_motif_evidence_version",
        )
        for field_name in (
            "tactical_motif_evidence_id",
            "match_snapshot_id",
            "game_reference_id",
            "decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in ("match_id", "game_id", "acting_player_id"):
            _require_identifier(getattr(self, field_name), field_name)
        _require_count(self.workspace_revision, "workspace_revision")
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        _require_positive_integer(self.decision_index, "decision_index")
        if self.actual_card_played not in _VALID_CARDS:
            raise ValueError("actual_card_played must be one valid Skat Card.")
        if type(self.observation) is not TacticalDecisionObservationV1:
            raise ValueError("observation must be an exact TacticalDecisionObservationV1.")
        facts = self.observation.decision_time_facts
        if (
            facts.source_game_id != self.game_id
            or facts.decision_index != self.decision_index
            or facts.acting_player_id != self.acting_player_id
            or self.observation.actual_card != self.actual_card_played
        ):
            raise ValueError("Tactical Observation must reconcile with source identity.")
        build_learning_corpus_canonical_json_bytes_v1(
            build_serializable_tactical_decision_observation_v1(self.observation)
        )
        if verify_identity and self.tactical_motif_evidence_id != _build_identifier(
            LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_ID_DOMAIN,
            _identity_material(self, "tactical_motif_evidence_id"),
        ):
            raise ValueError("tactical_motif_evidence_id must cover the exact Evidence.")

    @property
    def trick_number(self) -> int:
        return self.observation.decision_time_facts.trick_number

    @property
    def play_index(self) -> int:
        return self.observation.decision_time_facts.play_index

    @property
    def acting_seat(self) -> str:
        return self.observation.decision_time_facts.acting_seat

    @property
    def acting_side(self) -> str:
        return self.observation.decision_time_facts.acting_side

    @property
    def game_type(self) -> str:
        return self.observation.decision_time_facts.game_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_evidence_version": (
                self.learning_corpus_tactical_motif_evidence_version
            ),
            "tactical_motif_evidence_id": self.tactical_motif_evidence_id,
            "match_snapshot_id": self.match_snapshot_id,
            "workspace_revision": self.workspace_revision,
            "game_reference_id": self.game_reference_id,
            "decision_reference_id": self.decision_reference_id,
            "match_id": self.match_id,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "decision_index": self.decision_index,
            "acting_player_id": self.acting_player_id,
            "actual_card_played": self.actual_card_played,
            "observation": build_serializable_tactical_decision_observation_v1(self.observation),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusSkippedTacticalMotifDecisionV1:
    """One observed Decision whose required safe state was unavailable."""

    learning_corpus_tactical_motif_skipped_decision_version: int
    skipped_tactical_motif_decision_id: str
    match_snapshot_id: str
    workspace_revision: int
    game_reference_id: str
    decision_reference_id: str
    match_id: str
    match_position: int
    game_id: str
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: str
    acting_side: str
    game_type: str
    reason: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusSkippedTacticalMotifDecisionV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusSkippedTacticalMotifDecisionV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_skipped_decision_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_VERSION,
            "learning_corpus_tactical_motif_skipped_decision_version",
        )
        for field_name in (
            "skipped_tactical_motif_decision_id",
            "match_snapshot_id",
            "game_reference_id",
            "decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in ("match_id", "game_id", "acting_player_id"):
            _require_identifier(getattr(self, field_name), field_name)
        _require_count(self.workspace_revision, "workspace_revision")
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        for field_name in ("decision_index", "trick_number", "play_index"):
            _require_positive_integer(getattr(self, field_name), field_name)
        if self.play_index not in (1, 2, 3):
            raise ValueError("play_index must be 1, 2, or 3.")
        if self.decision_index != (self.trick_number - 1) * 3 + self.play_index:
            raise ValueError("Decision, Trick, and Play indexes must reconcile.")
        _scope_fields(self)
        if self.reason not in MATCH_DECISION_REVIEW_SKIP_REASONS:
            raise ValueError("reason must reuse one Match Decision skip reason.")
        if verify_identity and self.skipped_tactical_motif_decision_id != (
            _build_identifier(
                LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_ID_DOMAIN,
                _identity_material(self, "skipped_tactical_motif_decision_id"),
            )
        ):
            raise ValueError(
                "skipped_tactical_motif_decision_id must cover the exact skipped Decision."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_skipped_decision_version": (
                self.learning_corpus_tactical_motif_skipped_decision_version
            ),
            "skipped_tactical_motif_decision_id": (self.skipped_tactical_motif_decision_id),
            "match_snapshot_id": self.match_snapshot_id,
            "workspace_revision": self.workspace_revision,
            "game_reference_id": self.game_reference_id,
            "decision_reference_id": self.decision_reference_id,
            "match_id": self.match_id,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "decision_index": self.decision_index,
            "trick_number": self.trick_number,
            "play_index": self.play_index,
            "acting_player_id": self.acting_player_id,
            "acting_seat": self.acting_seat,
            "acting_side": self.acting_side,
            "game_type": self.game_type,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifEvidenceCollectionV1:
    """Complete Tactical coverage over explicit Current Match Snapshots."""

    learning_corpus_tactical_motif_collection_version: int
    tactical_motif_collection_fingerprint: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    retained_match_snapshot_count: int
    current_match_count: int
    orphan_match_snapshot_count: int
    status: str
    observed_game_count: int
    observed_decision_count: int
    evidence_count: int
    skipped_decision_count: int
    complete_observation_count: int
    partial_observation_count: int
    motif_occurrence_count: int
    evidences: tuple[LearningCorpusTacticalMotifEvidenceV1, ...]
    skipped_decisions: tuple[LearningCorpusSkippedTacticalMotifDecisionV1, ...]
    motif_counts: tuple[tuple[str, int], ...]
    family_counts: tuple[tuple[str, int], ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalMotifEvidenceCollectionV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusTacticalMotifEvidenceCollectionV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_collection_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_VERSION,
            "learning_corpus_tactical_motif_collection_version",
        )
        _require_hash(
            self.tactical_motif_collection_fingerprint,
            "tactical_motif_collection_fingerprint",
        )
        _require_identifier(self.corpus_id, "corpus_id")
        _require_count(self.source_catalog_revision, "source_catalog_revision")
        _require_hash(self.source_catalog_fingerprint, "source_catalog_fingerprint")
        _require_hash(
            self.source_catalog_content_fingerprint,
            "source_catalog_content_fingerprint",
        )
        _require_hash_tuple(
            self.current_match_snapshot_ids,
            "current_match_snapshot_ids",
        )
        for field_name in (
            "retained_match_snapshot_count",
            "current_match_count",
            "orphan_match_snapshot_count",
            "observed_game_count",
            "observed_decision_count",
            "evidence_count",
            "skipped_decision_count",
            "complete_observation_count",
            "partial_observation_count",
            "motif_occurrence_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.current_match_count != len(self.current_match_snapshot_ids):
            raise ValueError("current_match_count must reconcile exactly.")
        if self.retained_match_snapshot_count < self.current_match_count:
            raise ValueError("Retained Snapshot count cannot be below Current count.")
        if self.status not in LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_STATUSES:
            raise ValueError("status must be one canonical Collection status.")
        expected_status = (
            "empty"
            if self.observed_decision_count == 0
            else "partial"
            if self.skipped_decision_count
            else "complete"
        )
        if self.status != expected_status:
            raise ValueError("status must follow exact Tactical coverage semantics.")
        if type(self.evidences) is not tuple or any(
            type(item) is not LearningCorpusTacticalMotifEvidenceV1 for item in self.evidences
        ):
            raise ValueError("evidences must contain exact immutable Evidence values.")
        if type(self.skipped_decisions) is not tuple or any(
            type(item) is not LearningCorpusSkippedTacticalMotifDecisionV1
            for item in self.skipped_decisions
        ):
            raise ValueError("skipped_decisions must contain exact immutable skipped values.")
        for item in self.evidences:
            item._validate(verify_identity=True)
        for item in self.skipped_decisions:
            item._validate(verify_identity=True)
        snapshot_rank = {
            snapshot_id: index for index, snapshot_id in enumerate(self.current_match_snapshot_ids)
        }
        if any(
            item.match_snapshot_id not in snapshot_rank
            for item in (*self.evidences, *self.skipped_decisions)
        ):
            raise ValueError("Every Tactical Decision must belong to a Current Snapshot.")

        def source_key(
            item: (
                LearningCorpusTacticalMotifEvidenceV1 | LearningCorpusSkippedTacticalMotifDecisionV1
            ),
        ) -> tuple[int, int, int]:
            return (
                snapshot_rank[item.match_snapshot_id],
                item.match_position,
                item.decision_index,
            )

        if self.evidences != tuple(sorted(self.evidences, key=source_key)):
            raise ValueError("evidences must preserve canonical Current source order.")
        if self.skipped_decisions != tuple(sorted(self.skipped_decisions, key=source_key)):
            raise ValueError("skipped_decisions must preserve canonical Current source order.")
        evidence_references = tuple(item.decision_reference_id for item in self.evidences)
        skipped_references = tuple(item.decision_reference_id for item in self.skipped_decisions)
        if (
            len(evidence_references) != len(set(evidence_references))
            or len(skipped_references) != len(set(skipped_references))
            or set(evidence_references) & set(skipped_references)
        ):
            raise ValueError("Every observed Decision must be reconciled exactly once.")
        if self.evidence_count != len(self.evidences):
            raise ValueError("evidence_count must reconcile exactly.")
        if self.skipped_decision_count != len(self.skipped_decisions):
            raise ValueError("skipped_decision_count must reconcile exactly.")
        if self.observed_decision_count != (self.evidence_count + self.skipped_decision_count):
            raise ValueError("Observed Decision coverage must reconcile exactly.")
        if self.complete_observation_count != sum(
            item.observation.observation_status == "complete" for item in self.evidences
        ) or self.partial_observation_count != sum(
            item.observation.observation_status == "partial" for item in self.evidences
        ):
            raise ValueError("Observation status Counts must reconcile exactly.")
        if self.evidence_count != (
            self.complete_observation_count + self.partial_observation_count
        ):
            raise ValueError("Observation status Counts must cover every Evidence value.")
        _require_canonical_counts(
            self.motif_counts,
            "motif_counts",
            TACTICAL_MOTIF_TYPES,
        )
        _require_canonical_counts(
            self.family_counts,
            "family_counts",
            TACTICAL_MOTIF_FAMILIES,
        )
        if self.motif_occurrence_count != sum(
            len(item.observation.motifs) for item in self.evidences
        ):
            raise ValueError("motif_occurrence_count must reconcile exactly.")
        if sum(count for _, count in self.motif_counts) != self.motif_occurrence_count:
            raise ValueError("motif_counts must reconcile exactly.")
        if sum(count for _, count in self.family_counts) != self.motif_occurrence_count:
            raise ValueError("family_counts must reconcile exactly.")
        if verify_fingerprint and self.tactical_motif_collection_fingerprint != (
            _build_identifier(
                LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_FINGERPRINT_DOMAIN,
                _identity_material(self, "tactical_motif_collection_fingerprint"),
            )
        ):
            raise ValueError(
                "tactical_motif_collection_fingerprint must cover the exact Collection."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_collection_version": (
                self.learning_corpus_tactical_motif_collection_version
            ),
            "tactical_motif_collection_fingerprint": (self.tactical_motif_collection_fingerprint),
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": (self.source_catalog_content_fingerprint),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "retained_match_snapshot_count": self.retained_match_snapshot_count,
            "current_match_count": self.current_match_count,
            "orphan_match_snapshot_count": self.orphan_match_snapshot_count,
            "status": self.status,
            "observed_game_count": self.observed_game_count,
            "observed_decision_count": self.observed_decision_count,
            "evidence_count": self.evidence_count,
            "skipped_decision_count": self.skipped_decision_count,
            "complete_observation_count": self.complete_observation_count,
            "partial_observation_count": self.partial_observation_count,
            "motif_occurrence_count": self.motif_occurrence_count,
            "evidences": [item.to_dict() for item in self.evidences],
            "skipped_decisions": [item.to_dict() for item in self.skipped_decisions],
            "motif_counts": [
                {"motif_type": motif_type, "count": count}
                for motif_type, count in self.motif_counts
            ],
            "family_counts": [
                {"motif_family": family, "count": count} for family, count in self.family_counts
            ],
        }


def _identity_material(value: object, identity_field: str) -> dict[str, Any]:
    material = value.to_dict()
    del material[identity_field]
    return material


def _build_learning_corpus_tactical_motif_evidence_v1(
    **values: Any,
) -> LearningCorpusTacticalMotifEvidenceV1:
    values = {
        "learning_corpus_tactical_motif_evidence_version": (
            LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_VERSION
        ),
        "tactical_motif_evidence_id": "0" * 64,
        **values,
    }
    provisional = LearningCorpusTacticalMotifEvidenceV1._from_validated(**values)
    values["tactical_motif_evidence_id"] = _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_ID_DOMAIN,
        _identity_material(provisional, "tactical_motif_evidence_id"),
    )
    return LearningCorpusTacticalMotifEvidenceV1._from_validated(**values)


def _build_learning_corpus_skipped_tactical_motif_decision_v1(
    **values: Any,
) -> LearningCorpusSkippedTacticalMotifDecisionV1:
    values = {
        "learning_corpus_tactical_motif_skipped_decision_version": (
            LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_VERSION
        ),
        "skipped_tactical_motif_decision_id": "0" * 64,
        **values,
    }
    provisional = LearningCorpusSkippedTacticalMotifDecisionV1._from_validated(**values)
    values["skipped_tactical_motif_decision_id"] = _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_ID_DOMAIN,
        _identity_material(provisional, "skipped_tactical_motif_decision_id"),
    )
    return LearningCorpusSkippedTacticalMotifDecisionV1._from_validated(**values)


def _build_learning_corpus_tactical_motif_collection_v1(
    **values: Any,
) -> LearningCorpusTacticalMotifEvidenceCollectionV1:
    values = {
        "learning_corpus_tactical_motif_collection_version": (
            LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_VERSION
        ),
        "tactical_motif_collection_fingerprint": "0" * 64,
        **values,
    }
    provisional = LearningCorpusTacticalMotifEvidenceCollectionV1._from_validated(**values)
    values["tactical_motif_collection_fingerprint"] = _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_FINGERPRINT_DOMAIN,
        _identity_material(provisional, "tactical_motif_collection_fingerprint"),
    )
    return LearningCorpusTacticalMotifEvidenceCollectionV1._from_validated(**values)


def _validate_learning_corpus_tactical_motif_collection_v1(
    collection: LearningCorpusTacticalMotifEvidenceCollectionV1,
) -> None:
    if type(collection) is not LearningCorpusTacticalMotifEvidenceCollectionV1:
        raise ValueError(
            "collection must be an exact LearningCorpusTacticalMotifEvidenceCollectionV1."
        )
    collection._validate(verify_fingerprint=True)
