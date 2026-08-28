from __future__ import annotations

from pathlib import Path
from typing import Any

from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.learning_corpus_import import (
    import_match_workspace_file_into_learning_corpus_v1,
    set_learning_corpus_current_match_snapshot_file_v1,
)
from skatmind.learning_corpus_persistence import (
    initialize_learning_corpus_directory_v1,
)
from skatmind.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherReportSourceV1,
)
from skatmind.learning_corpus_strategy_teacher_builder import (
    validate_learning_corpus_strategy_teacher_report_source_v1,
)

from .context import LearningCorpusWebContextV1
from .contracts import LearningCorpusWebResultV1


def _require_context(context: object) -> LearningCorpusWebContextV1:
    if type(context) is not LearningCorpusWebContextV1:
        raise ValueError("context must be an exact LearningCorpusWebContextV1.")
    return context


def _require_revision(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _state(context: LearningCorpusWebContextV1) -> dict[str, Any]:
    store = context.store
    catalog = None if store is None else store.document.catalog
    return {
        "initialized": store is not None,
        "corpus_id": None if catalog is None else catalog.corpus_id,
        "catalog_revision": None if catalog is None else catalog.revision,
        "retained_match_snapshot_count": (0 if store is None else len(store.match_snapshots)),
        "current_match_count": (0 if catalog is None else len(catalog.current_matches)),
        "orphan_match_snapshot_count": (
            0 if store is None else len(store.orphan_match_snapshot_ids)
        ),
        "strategy_source_revision": context.strategy_source_store.revision,
        "strategy_source_count": len(context.strategy_source_store.sources),
        "prepared": (
            context.prepared_artifacts is not None
            and context.tactical_prepared_artifacts is not None
            and context.tactical_coaching_prepared_artifacts is not None
        ),
        "context_generation": context.generation,
    }


def _result(
    context: LearningCorpusWebContextV1,
    *,
    operation: str,
    status: str,
    message: str,
    extra_state: dict[str, Any] | None = None,
) -> LearningCorpusWebResultV1:
    state = _state(context)
    if extra_state:
        state.update(extra_state)
    return LearningCorpusWebResultV1(
        operation=operation,
        status=status,
        http_status=(
            409
            if status in {"revision_conflict", "persistence_conflict", "source_changed"}
            else 200
        ),
        message=message,
        state=state,
    )


def initialize_learning_corpus_web_v1(
    context: LearningCorpusWebContextV1,
    *,
    corpus_id: str,
) -> LearningCorpusWebResultV1:
    requested = _require_context(context)
    with requested.lock:
        if requested.store is not None:
            raise ValueError("The Learning Corpus is already initialized.")
        store = initialize_learning_corpus_directory_v1(
            requested.corpus_root,
            corpus_id=corpus_id,
        )
        requested.store = store
        requested.strategy_source_store.clear()
        requested._invalidate_prepared_locked()
        requested.generation += 1
        return _result(
            requested,
            operation="initialize_corpus",
            status="applied",
            message="Learning Corpus initialized.",
        )


def reload_learning_corpus_web_v1(
    context: LearningCorpusWebContextV1,
) -> LearningCorpusWebResultV1:
    requested = _require_context(context)
    with requested.lock:
        requested.reload()
        return _result(
            requested,
            operation="reload_corpus",
            status="reloaded",
            message="Learning Corpus reloaded from disk.",
        )


def import_match_workspace_into_learning_corpus_web_v1(
    context: LearningCorpusWebContextV1,
    server_owned_workspace_path: Path,
    *,
    selection_mode: str,
    same_revision_resolution: str,
    expected_catalog_revision: int,
) -> LearningCorpusWebResultV1:
    requested = _require_context(context)
    if not isinstance(server_owned_workspace_path, Path):
        raise ValueError("server_owned_workspace_path must be an exact Path.")
    expected_revision = _require_revision(
        expected_catalog_revision,
        "expected_catalog_revision",
    )
    with requested.lock:
        store = requested.store
        if store is None:
            raise ValueError("Initialize the Learning Corpus before importing.")
        result = import_match_workspace_file_into_learning_corpus_v1(
            requested.corpus_root,
            server_owned_workspace_path,
            expected_catalog_revision=expected_revision,
            expected_catalog_content_fingerprint=(store.document.content_fingerprint),
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
        )
        if result.status == "applied":
            requested.store = result.store
            requested._invalidate_prepared_locked()
            requested.generation += 1
        return _result(
            requested,
            operation="import_match_workspace",
            status=result.status,
            message=(
                "Match Workspace imported."
                if result.status == "applied"
                else "Match Workspace import made no Corpus change."
            ),
            extra_state={
                "relation": (
                    None if result.classification is None else result.classification.relation
                )
            },
        )


def select_current_learning_corpus_snapshot_web_v1(
    context: LearningCorpusWebContextV1,
    *,
    match_id: str,
    match_snapshot_id: str,
    expected_catalog_revision: int,
) -> LearningCorpusWebResultV1:
    requested = _require_context(context)
    expected_revision = _require_revision(
        expected_catalog_revision,
        "expected_catalog_revision",
    )
    with requested.lock:
        store = requested.store
        if store is None:
            raise ValueError("Initialize the Learning Corpus before selecting.")
        result = set_learning_corpus_current_match_snapshot_file_v1(
            requested.corpus_root,
            match_id=match_id,
            match_snapshot_id=match_snapshot_id,
            expected_catalog_revision=expected_revision,
            expected_catalog_content_fingerprint=(store.document.content_fingerprint),
        )
        if result.status == "applied":
            requested.store = result.store
            requested._invalidate_prepared_locked()
            requested.generation += 1
        return _result(
            requested,
            operation="select_current_snapshot",
            status=result.status,
            message=(
                "Current Match Snapshot selected."
                if result.status == "applied"
                else "Current Match Snapshot selection made no Corpus change."
            ),
        )


def import_strategy_teacher_report_into_learning_corpus_web_v1(
    context: LearningCorpusWebContextV1,
    source: LearningCorpusStrategyTeacherReportSourceV1,
) -> LearningCorpusWebResultV1:
    requested = _require_context(context)
    with requested.lock:
        store = requested.store
        if store is None:
            raise ValueError("Initialize the Learning Corpus before adding sources.")
        try:
            validate_learning_corpus_strategy_teacher_report_source_v1(store, source)
        except SkatMindInvariantError as error:
            raise SkatMindValidationError(
                "Uploaded Report source does not reconcile with the Current Snapshot.",
                path="",
            ) from error
        status = requested.strategy_source_store.add(source)
        if status == "applied":
            requested._invalidate_prepared_locked()
            requested.generation += 1
        return _result(
            requested,
            operation="import_strategy_teacher_report",
            status=status,
            message=(
                "Strategy Teacher Report source added."
                if status == "applied"
                else "Strategy Teacher Report source was already present."
            ),
            extra_state={
                "source_binding_id": source.source_binding_id,
                "source_binding_status": requested.strategy_source_store.binding_status(
                    source,
                    store,
                ),
            },
        )


def remove_strategy_teacher_report_from_learning_corpus_web_v1(
    context: LearningCorpusWebContextV1,
    *,
    source_binding_id: str,
) -> LearningCorpusWebResultV1:
    requested = _require_context(context)
    with requested.lock:
        status = requested.strategy_source_store.remove(source_binding_id)
        if status == "applied":
            requested._invalidate_prepared_locked()
            requested.generation += 1
        return _result(
            requested,
            operation="remove_strategy_teacher_report",
            status=status,
            message=(
                "Strategy Teacher Report source removed."
                if status == "applied"
                else "Strategy Teacher Report source was not present."
            ),
        )


def clear_strategy_teacher_reports_from_learning_corpus_web_v1(
    context: LearningCorpusWebContextV1,
) -> LearningCorpusWebResultV1:
    requested = _require_context(context)
    with requested.lock:
        status = requested.strategy_source_store.clear()
        if status == "applied":
            requested._invalidate_prepared_locked()
            requested.generation += 1
        return _result(
            requested,
            operation="clear_strategy_teacher_reports",
            status=status,
            message=(
                "Strategy Teacher Report sources cleared."
                if status == "applied"
                else "No Strategy Teacher Report sources were present."
            ),
        )
