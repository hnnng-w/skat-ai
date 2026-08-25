from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from skat_ai.learning_corpus_human_evidence import (
    LearningCorpusHumanEvidenceCollectionV1,
    _validate_learning_corpus_human_evidence_collection_v1,
)
from skat_ai.learning_corpus_player_catalog import (
    LearningCorpusPlayerCatalogV1,
    _validate_learning_corpus_player_catalog_v1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    _validate_learning_corpus_strategy_teacher_collection_v1,
)
from skat_ai.learning_corpus_tactical_motif_evidence import (
    LearningCorpusTacticalMotifEvidenceCollectionV1,
    _validate_learning_corpus_tactical_motif_collection_v1,
)
from skat_ai.learning_corpus_tactical_motif_summary import (
    LearningCorpusTacticalMotifCrossGameSummaryV1,
    _validate_learning_corpus_tactical_motif_cross_game_summary_v1,
)
from skat_ai.learning_dataset_v2_contracts import (
    LearningDatasetV2,
    _validate_learning_dataset_v2,
)
from skat_ai.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_PARTITION_ALGORITHM_BY_MODE,
    LearningDatasetPartitionPreparationResultV1,
    LearningDatasetPartitionWeightsV1,
)
from skat_ai.learning_dataset_v2_partition_identity import (
    build_learning_dataset_partition_request_fingerprint_v1,
)
from skat_ai.learning_dataset_v2_summary_contracts import (
    LearningDatasetCrossGameSummaryV1,
    _validate_learning_dataset_cross_game_summary_v1,
)

LEARNING_CORPUS_WEB_VERSION = 1
LEARNING_CORPUS_WEB_PROTOCOL_VERSION = 1
LEARNING_CORPUS_STRATEGY_SOURCE_STORE_VERSION = 1
LEARNING_CORPUS_PREPARED_ARTIFACTS_VERSION = 1
LEARNING_CORPUS_TACTICAL_PREPARED_ARTIFACTS_VERSION = 1

LEARNING_CORPUS_WEB_OPERATIONS: Final[tuple[str, ...]] = (
    "initialize_corpus",
    "reload_corpus",
    "import_match_workspace",
    "select_current_snapshot",
    "import_strategy_teacher_report",
    "remove_strategy_teacher_report",
    "clear_strategy_teacher_reports",
    "prepare_learning_artifacts",
)
LEARNING_CORPUS_WEB_RESULT_STATUSES: Final[tuple[str, ...]] = (
    "applied",
    "unchanged",
    "revision_conflict",
    "persistence_conflict",
    "resolution_required",
    "reloaded",
    "prepared",
    "source_changed",
)
LEARNING_CORPUS_STRATEGY_SOURCE_BINDING_STATUSES: Final[tuple[str, ...]] = (
    "current",
    "non_current",
)

LEARNING_CORPUS_WEB_ROOT_POLICY = "one_explicit_corpus_root_per_server"
LEARNING_CORPUS_WEB_UPLOAD_POLICY = "strict_uploaded_json_without_caller_server_path"
LEARNING_CORPUS_WEB_MUTATION_POLICY = "optimistic_catalog_compare_and_swap"
LEARNING_CORPUS_WEB_REPORT_SOURCE_POLICY = "session_local_exact_decision_report_sources"
LEARNING_CORPUS_WEB_PREPARATION_POLICY = "explicit_rebuild_without_analysis_execution"
LEARNING_CORPUS_WEB_INVALIDATION_POLICY = "invalidate_prepared_artifacts_on_source_change"
LEARNING_CORPUS_WEB_STALE_SOURCE_POLICY = (
    "non_current_report_sources_block_preparation_until_removed"
)
LEARNING_CORPUS_WEB_SECURITY_POLICY = "loopback_token_cookie_same_origin"
LEARNING_CORPUS_WEB_PRESENTATION_POLICY = "server_rendered_with_progressive_enhancement"
LEARNING_CORPUS_WEB_ASSET_POLICY = "packaged_local_assets_without_external_dependencies"
LEARNING_CORPUS_WEB_DOWNLOAD_POLICY = "authenticated_private_downloads_without_server_paths"
LEARNING_CORPUS_WEB_NETWORK_POLICY = "no_external_requests"

LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES = 16_777_216
LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES = 2_048


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


def _require_integer(value: object, field_name: str, *, positive: bool = False) -> int:
    if type(value) is not int or (positive and value <= 0):
        qualifier = "positive " if positive else ""
        raise ValueError(f"{field_name} must be a {qualifier}integer and not a boolean.")
    return value


def _freeze_json(value: object) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("state must not contain non-finite numbers.")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("state keys must be strings.")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    raise ValueError("state must contain only JSON-compatible values.")


def _thaw_json(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusWebResultV1:
    """One path-free result envelope for the private HTTP transport boundary."""

    learning_corpus_web_protocol_version: int = LEARNING_CORPUS_WEB_PROTOCOL_VERSION
    operation: str
    status: str
    http_status: int
    message: str
    state: Mapping[str, Any]

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_web_protocol_version,
            LEARNING_CORPUS_WEB_PROTOCOL_VERSION,
            "learning_corpus_web_protocol_version",
        )
        if self.operation not in LEARNING_CORPUS_WEB_OPERATIONS:
            raise ValueError(f"operation must be one of {list(LEARNING_CORPUS_WEB_OPERATIONS)}.")
        if self.status not in LEARNING_CORPUS_WEB_RESULT_STATUSES:
            raise ValueError(f"status must be one of {list(LEARNING_CORPUS_WEB_RESULT_STATUSES)}.")
        if type(self.http_status) is not int or not 100 <= self.http_status <= 599:
            raise ValueError("http_status must be one valid HTTP status code.")
        _require_identifier(self.message, "message")
        if not isinstance(self.state, Mapping):
            raise ValueError("state must be a browser-safe mapping.")
        object.__setattr__(self, "state", _freeze_json(self.state))

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_web_protocol_version": (self.learning_corpus_web_protocol_version),
            "operation": self.operation,
            "status": self.status,
            "http_status": self.http_status,
            "message": self.message,
            "state": _thaw_json(self.state),
        }


def _source_identity(value: Any) -> tuple[object, ...]:
    return (
        value.corpus_id,
        value.source_catalog_revision,
        value.source_catalog_fingerprint,
        value.source_catalog_content_fingerprint,
        value.current_match_snapshot_ids,
        value.retained_match_snapshot_count,
        value.current_match_count,
        value.orphan_match_snapshot_count,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusPreparedArtifactsV1:
    """One process-local exact set of explicitly rebuilt learning artifacts."""

    learning_corpus_prepared_artifacts_version: int = LEARNING_CORPUS_PREPARED_ARTIFACTS_VERSION
    source_catalog_revision: int
    source_catalog_content_fingerprint: str
    strategy_source_binding_ids: tuple[str, ...]
    dataset_id: str
    known_player_base_random_seed: int
    unseen_player_base_random_seed: int
    partition_weights: LearningDatasetPartitionWeightsV1
    player_catalog: LearningCorpusPlayerCatalogV1
    human_evidence: LearningCorpusHumanEvidenceCollectionV1
    strategy_teacher_evidence: LearningCorpusStrategyTeacherEvidenceCollectionV1
    learning_dataset: LearningDatasetV2
    known_player_partition_result: LearningDatasetPartitionPreparationResultV1
    unseen_player_partition_result: LearningDatasetPartitionPreparationResultV1
    cross_game_summary: LearningDatasetCrossGameSummaryV1

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_prepared_artifacts_version,
            LEARNING_CORPUS_PREPARED_ARTIFACTS_VERSION,
            "learning_corpus_prepared_artifacts_version",
        )
        if type(self.source_catalog_revision) is not int or (self.source_catalog_revision < 0):
            raise ValueError("source_catalog_revision must be a non-negative integer.")
        _require_hash(
            self.source_catalog_content_fingerprint,
            "source_catalog_content_fingerprint",
        )
        if type(self.strategy_source_binding_ids) is not tuple:
            raise ValueError("strategy_source_binding_ids must be an immutable tuple.")
        for binding_id in self.strategy_source_binding_ids:
            _require_hash(binding_id, "strategy_source_binding_ids")
        if len(self.strategy_source_binding_ids) != len(set(self.strategy_source_binding_ids)):
            raise ValueError("strategy_source_binding_ids must contain unique IDs.")
        _require_identifier(self.dataset_id, "dataset_id")
        _require_integer(
            self.known_player_base_random_seed,
            "known_player_base_random_seed",
        )
        _require_integer(
            self.unseen_player_base_random_seed,
            "unseen_player_base_random_seed",
        )
        if type(self.partition_weights) is not LearningDatasetPartitionWeightsV1:
            raise ValueError(
                "partition_weights must be an exact LearningDatasetPartitionWeightsV1."
            )
        if type(self.player_catalog) is not LearningCorpusPlayerCatalogV1:
            raise ValueError("player_catalog must use the exact contract.")
        if type(self.human_evidence) is not LearningCorpusHumanEvidenceCollectionV1:
            raise ValueError("human_evidence must use the exact contract.")
        if (
            type(self.strategy_teacher_evidence)
            is not LearningCorpusStrategyTeacherEvidenceCollectionV1
        ):
            raise ValueError("strategy_teacher_evidence must use the exact contract.")
        if type(self.learning_dataset) is not LearningDatasetV2:
            raise ValueError("learning_dataset must use the exact contract.")
        for field_name in (
            "known_player_partition_result",
            "unseen_player_partition_result",
        ):
            if type(getattr(self, field_name)) is not LearningDatasetPartitionPreparationResultV1:
                raise ValueError(f"{field_name} must use the exact contract.")
        if type(self.cross_game_summary) is not LearningDatasetCrossGameSummaryV1:
            raise ValueError("cross_game_summary must use the exact contract.")

        _validate_learning_corpus_player_catalog_v1(self.player_catalog)
        _validate_learning_corpus_human_evidence_collection_v1(self.human_evidence)
        _validate_learning_corpus_strategy_teacher_collection_v1(self.strategy_teacher_evidence)
        _validate_learning_dataset_v2(self.learning_dataset)
        self.known_player_partition_result._validate()
        self.unseen_player_partition_result._validate()
        _validate_learning_dataset_cross_game_summary_v1(self.cross_game_summary)
        self._validate_reconciliation()

    def _validate_reconciliation(self) -> None:
        sources = (
            self.player_catalog,
            self.human_evidence,
            self.strategy_teacher_evidence,
            self.learning_dataset,
            self.cross_game_summary,
        )
        identity = _source_identity(self.player_catalog)
        if any(_source_identity(source) != identity for source in sources[1:]):
            raise ValueError("Prepared artifacts must use one exact Corpus source identity.")
        if (
            self.source_catalog_revision != self.player_catalog.source_catalog_revision
            or self.source_catalog_content_fingerprint
            != self.player_catalog.source_catalog_content_fingerprint
        ):
            raise ValueError("Prepared source identity must match every nested artifact.")
        if self.dataset_id != self.learning_dataset.dataset_id:
            raise ValueError("dataset_id must match the exact Learning Dataset.")
        evidence_binding_ids = tuple(
            evidence.source_binding_id for evidence in self.strategy_teacher_evidence.evidences
        )
        if self.strategy_source_binding_ids != evidence_binding_ids:
            raise ValueError("strategy_source_binding_ids must match exact Teacher Evidence order.")
        if (
            self.learning_dataset.player_catalog_fingerprint
            != self.player_catalog.player_catalog_fingerprint
            or self.learning_dataset.human_evidence_collection_fingerprint
            != self.human_evidence.human_evidence_collection_fingerprint
            or self.learning_dataset.strategy_teacher_collection_fingerprint
            != self.strategy_teacher_evidence.strategy_teacher_collection_fingerprint
        ):
            raise ValueError("Learning Dataset source fingerprints must reconcile.")
        if (
            self.cross_game_summary.dataset_fingerprint != self.learning_dataset.dataset_fingerprint
            or self.cross_game_summary.player_catalog_fingerprint
            != self.player_catalog.player_catalog_fingerprint
            or self.cross_game_summary.dataset_id != self.learning_dataset.dataset_id
            or self.cross_game_summary.dataset_status != self.learning_dataset.status
            or self.cross_game_summary.observed_game_count
            != self.learning_dataset.observed_game_count
            or self.cross_game_summary.observed_decision_count
            != self.learning_dataset.observed_decision_count
            or self.cross_game_summary.record_count != self.learning_dataset.record_count
            or self.cross_game_summary.skipped_decision_count
            != self.learning_dataset.skipped_decision_count
            or self.cross_game_summary.player_count != self.player_catalog.player_count
        ):
            raise ValueError("Cross-game Summary sources must reconcile.")
        self._validate_partition_result(
            self.known_player_partition_result,
            mode="known_player",
            seed=self.known_player_base_random_seed,
        )
        self._validate_partition_result(
            self.unseen_player_partition_result,
            mode="unseen_player",
            seed=self.unseen_player_base_random_seed,
        )
        readiness_by_mode = {
            item.mode: item
            for item in self.cross_game_summary.readiness_summary.partition_readiness
        }
        for result in (
            self.known_player_partition_result,
            self.unseen_player_partition_result,
        ):
            readiness = readiness_by_mode.get(result.plan.mode)
            if (
                readiness is None
                or readiness.status != result.status
                or readiness.unavailable_reason != result.unavailable_reason
                or readiness.request_fingerprint != result.request_fingerprint
                or readiness.plan_fingerprint != result.plan.plan_fingerprint
                or readiness.base_random_seed != result.plan.base_random_seed
                or readiness.requested_partition_weights != result.plan.requested_partition_weights
            ):
                raise ValueError("Cross-game Summary must use the exact partition Results.")

    def _validate_partition_result(
        self,
        result: LearningDatasetPartitionPreparationResultV1,
        *,
        mode: str,
        seed: int,
    ) -> None:
        plan = result.plan
        if (
            plan.mode != mode
            or plan.base_random_seed != seed
            or plan.requested_partition_weights != self.partition_weights
        ):
            raise ValueError("Partition Result inputs must match Prepared Artifacts.")
        expected_request_fingerprint = build_learning_dataset_partition_request_fingerprint_v1(
            mode=mode,
            algorithm=LEARNING_DATASET_PARTITION_ALGORITHM_BY_MODE[mode],
            base_random_seed=seed,
            partition_weights=self.partition_weights,
            learning_dataset=self.learning_dataset,
            player_catalog=self.player_catalog,
        )
        if result.request_fingerprint != expected_request_fingerprint:
            raise ValueError("Partition Result must use the exact prepared sources.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_prepared_artifacts_version": (
                self.learning_corpus_prepared_artifacts_version
            ),
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_content_fingerprint": (self.source_catalog_content_fingerprint),
            "strategy_source_binding_ids": list(self.strategy_source_binding_ids),
            "dataset_id": self.dataset_id,
            "known_player_base_random_seed": self.known_player_base_random_seed,
            "unseen_player_base_random_seed": self.unseen_player_base_random_seed,
            "partition_weights": self.partition_weights.to_dict(),
            "player_catalog": self.player_catalog.to_dict(),
            "human_evidence": self.human_evidence.to_dict(),
            "strategy_teacher_evidence": self.strategy_teacher_evidence.to_dict(),
            "learning_dataset": self.learning_dataset.to_dict(),
            "known_player_partition_result": (self.known_player_partition_result.to_dict()),
            "unseen_player_partition_result": (self.unseen_player_partition_result.to_dict()),
            "cross_game_summary": self.cross_game_summary.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusTacticalPreparedArtifactsV1:
    """One separate process-local Tactical artifact family."""

    learning_corpus_tactical_prepared_artifacts_version: int = (
        LEARNING_CORPUS_TACTICAL_PREPARED_ARTIFACTS_VERSION
    )
    source_catalog_revision: int
    source_catalog_content_fingerprint: str
    player_catalog_fingerprint: str
    tactical_motif_collection: LearningCorpusTacticalMotifEvidenceCollectionV1
    tactical_motif_cross_game_summary: LearningCorpusTacticalMotifCrossGameSummaryV1

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_tactical_prepared_artifacts_version,
            LEARNING_CORPUS_TACTICAL_PREPARED_ARTIFACTS_VERSION,
            "learning_corpus_tactical_prepared_artifacts_version",
        )
        if type(self.source_catalog_revision) is not int or self.source_catalog_revision < 0:
            raise ValueError("source_catalog_revision must be a non-negative integer.")
        _require_hash(
            self.source_catalog_content_fingerprint,
            "source_catalog_content_fingerprint",
        )
        _require_hash(self.player_catalog_fingerprint, "player_catalog_fingerprint")
        _validate_learning_corpus_tactical_motif_collection_v1(
            self.tactical_motif_collection
        )
        _validate_learning_corpus_tactical_motif_cross_game_summary_v1(
            self.tactical_motif_cross_game_summary
        )
        collection = self.tactical_motif_collection
        summary = self.tactical_motif_cross_game_summary
        if (
            self.source_catalog_revision != collection.source_catalog_revision
            or self.source_catalog_revision != summary.source_catalog_revision
            or self.source_catalog_content_fingerprint
            != collection.source_catalog_content_fingerprint
            or self.source_catalog_content_fingerprint
            != summary.source_catalog_content_fingerprint
            or self.player_catalog_fingerprint != summary.player_catalog_fingerprint
            or collection.tactical_motif_collection_fingerprint
            != summary.tactical_motif_collection_fingerprint
        ):
            raise ValueError("Tactical Prepared Artifacts must use exact shared sources.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_prepared_artifacts_version": (
                self.learning_corpus_tactical_prepared_artifacts_version
            ),
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_content_fingerprint": (
                self.source_catalog_content_fingerprint
            ),
            "player_catalog_fingerprint": self.player_catalog_fingerprint,
            "tactical_motif_collection": self.tactical_motif_collection.to_dict(),
            "tactical_motif_cross_game_summary": (
                self.tactical_motif_cross_game_summary.to_dict()
            ),
        }


for _limit_name, _limit_value in (
    ("LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES", LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES),
    (
        "LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES",
        LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES,
    ),
):
    _require_integer(_limit_value, _limit_name, positive=True)
del _limit_name, _limit_value
