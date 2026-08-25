from __future__ import annotations

from skat_ai.learning_corpus_human_evidence_builder import (
    build_learning_corpus_human_evidence_collection_v1,
)
from skat_ai.learning_corpus_player_catalog import (
    build_learning_corpus_player_catalog_v1,
)
from skat_ai.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)
from skat_ai.learning_corpus_tactical_cross_game_coaching import (
    build_learning_corpus_tactical_cross_game_coaching_report_v1,
)
from skat_ai.learning_corpus_tactical_motif_builder import (
    build_learning_corpus_tactical_motif_evidence_collection_v1,
)
from skat_ai.learning_corpus_tactical_motif_summary import (
    build_learning_corpus_tactical_motif_cross_game_summary_v1,
)
from skat_ai.learning_dataset_v2_builder import build_learning_dataset_v2
from skat_ai.learning_dataset_v2_partition_contracts import (
    LearningDatasetPartitionWeightsV1,
)
from skat_ai.learning_dataset_v2_partition_preparation import (
    build_learning_dataset_partition_preparation_request_v1,
    prepare_learning_dataset_v2_partitions_v1,
)
from skat_ai.learning_dataset_v2_summary_builder import (
    build_learning_dataset_v2_cross_game_summary_v1,
)

from .context import LearningCorpusWebContextV1
from .contracts import (
    LearningCorpusPreparedArtifactsV1,
    LearningCorpusTacticalCoachingPreparedArtifactsV1,
    LearningCorpusTacticalPreparedArtifactsV1,
    LearningCorpusWebResultV1,
)
from .operations import _result


def _require_dataset_id(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("dataset_id must be a non-empty, non-padded string.")
    return value


def _require_seed(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field_name} must be an integer and not a boolean.")
    return value


def _require_weight(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def prepare_learning_corpus_artifacts_web_v1(
    context: LearningCorpusWebContextV1,
    *,
    dataset_id: str,
    known_player_seed: int,
    unseen_player_seed: int,
    train_weight: int,
    validation_weight: int,
    test_weight: int,
) -> LearningCorpusWebResultV1:
    """Builds each required learning artifact once outside the context lock."""
    if type(context) is not LearningCorpusWebContextV1:
        raise ValueError("context must be an exact LearningCorpusWebContextV1.")
    requested_dataset_id = _require_dataset_id(dataset_id)
    known_seed = _require_seed(known_player_seed, "known_player_seed")
    unseen_seed = _require_seed(unseen_player_seed, "unseen_player_seed")
    weights = LearningDatasetPartitionWeightsV1(
        train=_require_weight(train_weight, "train_weight"),
        validation=_require_weight(validation_weight, "validation_weight"),
        test=_require_weight(test_weight, "test_weight"),
    )

    with context.lock:
        store = context.store
        if store is None:
            raise ValueError("Initialize the Learning Corpus before preparation.")
        classified = context.strategy_source_store.classified_sources(store)
        if any(status == "non_current" for _source, status in classified):
            raise ValueError("Remove non-current Strategy Teacher sources before preparation.")
        sources = tuple(source for source, _status in classified)
        source_revision = context.strategy_source_store.revision
        generation = context.generation
        catalog_revision = store.document.catalog.revision
        catalog_content_fingerprint = store.document.content_fingerprint

    player_catalog = build_learning_corpus_player_catalog_v1(store)
    human_evidence = build_learning_corpus_human_evidence_collection_v1(store)
    strategy_teacher_evidence = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        sources,
    )
    learning_dataset = build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        strategy_teacher_evidence,
        dataset_id=requested_dataset_id,
    )
    known_request = build_learning_dataset_partition_preparation_request_v1(
        learning_dataset,
        player_catalog,
        mode="known_player",
        base_random_seed=known_seed,
        partition_weights=weights,
    )
    known_result = prepare_learning_dataset_v2_partitions_v1(known_request)
    unseen_request = build_learning_dataset_partition_preparation_request_v1(
        learning_dataset,
        player_catalog,
        mode="unseen_player",
        base_random_seed=unseen_seed,
        partition_weights=weights,
    )
    unseen_result = prepare_learning_dataset_v2_partitions_v1(unseen_request)
    cross_game_summary = build_learning_dataset_v2_cross_game_summary_v1(
        learning_dataset,
        player_catalog,
        known_player_partition_result=known_result,
        unseen_player_partition_result=unseen_result,
    )
    prepared = LearningCorpusPreparedArtifactsV1(
        source_catalog_revision=catalog_revision,
        source_catalog_content_fingerprint=catalog_content_fingerprint,
        strategy_source_binding_ids=tuple(source.source_binding_id for source in sources),
        dataset_id=requested_dataset_id,
        known_player_base_random_seed=known_seed,
        unseen_player_base_random_seed=unseen_seed,
        partition_weights=weights,
        player_catalog=player_catalog,
        human_evidence=human_evidence,
        strategy_teacher_evidence=strategy_teacher_evidence,
        learning_dataset=learning_dataset,
        known_player_partition_result=known_result,
        unseen_player_partition_result=unseen_result,
        cross_game_summary=cross_game_summary,
    )
    tactical_motif_collection = (
        build_learning_corpus_tactical_motif_evidence_collection_v1(store)
    )
    tactical_motif_cross_game_summary = (
        build_learning_corpus_tactical_motif_cross_game_summary_v1(
            tactical_motif_collection,
            player_catalog,
        )
    )
    tactical_prepared = LearningCorpusTacticalPreparedArtifactsV1(
        source_catalog_revision=catalog_revision,
        source_catalog_content_fingerprint=catalog_content_fingerprint,
        player_catalog_fingerprint=player_catalog.player_catalog_fingerprint,
        tactical_motif_collection=tactical_motif_collection,
        tactical_motif_cross_game_summary=tactical_motif_cross_game_summary,
    )
    tactical_cross_game_coaching_report = (
        build_learning_corpus_tactical_cross_game_coaching_report_v1(
            player_catalog=player_catalog,
            strategy_teacher_collection=strategy_teacher_evidence,
            tactical_motif_collection=tactical_motif_collection,
            tactical_motif_cross_game_summary=tactical_motif_cross_game_summary,
        )
    )
    tactical_coaching_prepared = LearningCorpusTacticalCoachingPreparedArtifactsV1(
        source_catalog_revision=catalog_revision,
        source_catalog_content_fingerprint=catalog_content_fingerprint,
        player_catalog_fingerprint=player_catalog.player_catalog_fingerprint,
        strategy_teacher_collection_fingerprint=(
            strategy_teacher_evidence.strategy_teacher_collection_fingerprint
        ),
        tactical_motif_collection_fingerprint=(
            tactical_motif_collection.tactical_motif_collection_fingerprint
        ),
        tactical_motif_cross_game_summary_fingerprint=(
            tactical_motif_cross_game_summary.tactical_motif_cross_game_summary_fingerprint
        ),
        tactical_cross_game_coaching_report=tactical_cross_game_coaching_report,
    )

    with context.lock:
        current_store = context.store
        changed = (
            current_store is not store
            or current_store is None
            or current_store.document.catalog.revision != catalog_revision
            or current_store.document.content_fingerprint != catalog_content_fingerprint
            or context.strategy_source_store.revision != source_revision
            or context.generation != generation
        )
        if changed:
            context._invalidate_prepared_lineage_locked(
                store=store,
                source_revision=source_revision,
                generation=generation,
            )
            return _result(
                context,
                operation="prepare_learning_artifacts",
                status="source_changed",
                message=(
                    "Learning Corpus sources changed during preparation; "
                    "no artifacts were published."
                ),
            )
        context.publish_prepared(
            prepared,
            tactical_prepared,
            tactical_coaching_prepared,
            store=store,
            source_revision=source_revision,
            generation=generation,
        )
        return _result(
            context,
            operation="prepare_learning_artifacts",
            status="prepared",
            message="Learning artifacts prepared.",
            extra_state={
                "dataset_id": prepared.dataset_id,
                "dataset_status": prepared.learning_dataset.status,
                "record_count": prepared.learning_dataset.record_count,
                "skipped_decision_count": (prepared.learning_dataset.skipped_decision_count),
                "known_player_partition_status": (prepared.known_player_partition_result.status),
                "unseen_player_partition_status": (prepared.unseen_player_partition_result.status),
                "tactical_collection_status": tactical_motif_collection.status,
                "tactical_evidence_count": tactical_motif_collection.evidence_count,
                "tactical_skipped_decision_count": (
                    tactical_motif_collection.skipped_decision_count
                ),
                "tactical_motif_occurrence_count": (
                    tactical_motif_collection.motif_occurrence_count
                ),
                "tactical_coaching_status": tactical_cross_game_coaching_report.status,
                "tactical_coaching_decision_count": (
                    tactical_cross_game_coaching_report.decision_summary_count
                ),
                "tactical_coaching_teacher_assessment_count": (
                    tactical_cross_game_coaching_report.teacher_assessment_count
                ),
                "tactical_coaching_focus_area_count": (
                    tactical_cross_game_coaching_report.focus_area_count
                ),
                "tactical_coaching_player_with_focus_count": (
                    tactical_cross_game_coaching_report.player_with_focus_count
                ),
            },
        )
