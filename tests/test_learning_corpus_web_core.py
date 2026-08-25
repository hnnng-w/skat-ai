from __future__ import annotations

import json
import threading
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest
from test_learning_corpus_human_evidence import _store
from test_learning_corpus_strategy_teacher import _source_bundle

import skat_ai.corpus_web.operations as operations_module
import skat_ai.corpus_web.preparation as preparation_module
from skat_ai.corpus_web.context import LearningCorpusWebContextV1
from skat_ai.corpus_web.contracts import (
    LEARNING_CORPUS_PREPARED_ARTIFACTS_VERSION,
    LEARNING_CORPUS_STRATEGY_SOURCE_BINDING_STATUSES,
    LEARNING_CORPUS_STRATEGY_SOURCE_STORE_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_ARTIFACTS_VERSION,
    LEARNING_CORPUS_TACTICAL_PREPARED_ARTIFACTS_VERSION,
    LEARNING_CORPUS_WEB_ASSET_POLICY,
    LEARNING_CORPUS_WEB_DOWNLOAD_POLICY,
    LEARNING_CORPUS_WEB_INVALIDATION_POLICY,
    LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES,
    LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES,
    LEARNING_CORPUS_WEB_MUTATION_POLICY,
    LEARNING_CORPUS_WEB_NETWORK_POLICY,
    LEARNING_CORPUS_WEB_OPERATIONS,
    LEARNING_CORPUS_WEB_PREPARATION_POLICY,
    LEARNING_CORPUS_WEB_PRESENTATION_POLICY,
    LEARNING_CORPUS_WEB_PROTOCOL_VERSION,
    LEARNING_CORPUS_WEB_REPORT_SOURCE_POLICY,
    LEARNING_CORPUS_WEB_RESULT_STATUSES,
    LEARNING_CORPUS_WEB_ROOT_POLICY,
    LEARNING_CORPUS_WEB_SECURITY_POLICY,
    LEARNING_CORPUS_WEB_STALE_SOURCE_POLICY,
    LEARNING_CORPUS_WEB_UPLOAD_POLICY,
    LEARNING_CORPUS_WEB_VERSION,
    LearningCorpusWebResultV1,
)
from skat_ai.corpus_web.downloads import (
    LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS,
    LEARNING_CORPUS_PREPARED_DOWNLOAD_KINDS,
    LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_DOWNLOAD_KINDS,
    LEARNING_CORPUS_TACTICAL_PREPARED_DOWNLOAD_KINDS,
    LearningCorpusPreparedDownloadUnavailableError,
    build_learning_corpus_artifact_filename_v1,
    build_learning_corpus_prepared_download_v1,
)
from skat_ai.corpus_web.operations import (
    clear_strategy_teacher_reports_from_learning_corpus_web_v1,
    import_match_workspace_into_learning_corpus_web_v1,
    import_strategy_teacher_report_into_learning_corpus_web_v1,
    initialize_learning_corpus_web_v1,
    reload_learning_corpus_web_v1,
    remove_strategy_teacher_report_from_learning_corpus_web_v1,
    select_current_learning_corpus_snapshot_web_v1,
)
from skat_ai.corpus_web.preparation import (
    prepare_learning_corpus_artifacts_web_v1,
)
from skat_ai.corpus_web.source_store import (
    LearningCorpusStrategyTeacherSourceStoreV1,
)
from skat_ai.learning_corpus_catalog import create_empty_learning_corpus_catalog_v1
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_persistence import save_learning_corpus_catalog_v1
from skat_ai.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
)
from skat_ai.learning_corpus_strategy_teacher_builder import (
    validate_learning_corpus_strategy_teacher_report_source_v1,
)
from skat_ai.match_workspace_operations import (
    replace_match_workspace_definition_v1,
)
from skat_ai.match_workspace_persistence import save_match_workspace_file_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


@pytest.fixture(scope="module")
def immediate_bundle():
    return _source_bundle()


@pytest.fixture(scope="module")
def auto_bundle():
    return _source_bundle(
        recommendation_method="auto",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )


def _initialize(tmp_path: Path, corpus_id: str = "corpus-web"):
    context = LearningCorpusWebContextV1.open(tmp_path / corpus_id)
    result = initialize_learning_corpus_web_v1(context, corpus_id=corpus_id)
    assert result.status == "applied"
    assert context.store is not None
    return context


def _prepare_empty(context: LearningCorpusWebContextV1, dataset_id="dataset-web"):
    result = prepare_learning_corpus_artifacts_web_v1(
        context,
        dataset_id=dataset_id,
        known_player_seed=3,
        unseen_player_seed=5,
        train_weight=70,
        validation_weight=15,
        test_weight=15,
    )
    assert result.status == "prepared"
    assert context.prepared_artifacts is not None
    assert context.tactical_prepared_artifacts is not None
    assert context.tactical_coaching_prepared_artifacts is not None
    return context.prepared_artifacts


def _save_workspace(path: Path, workspace) -> None:
    result = save_match_workspace_file_v1(
        path,
        build_match_workspace_persistence_document_v1(workspace),
        expected_content_fingerprint=None,
    )
    assert result.status == "saved"


def test_versions_vocabularies_policies_and_limits_are_exact() -> None:
    assert (
        LEARNING_CORPUS_WEB_VERSION,
        LEARNING_CORPUS_WEB_PROTOCOL_VERSION,
        LEARNING_CORPUS_STRATEGY_SOURCE_STORE_VERSION,
        LEARNING_CORPUS_PREPARED_ARTIFACTS_VERSION,
        LEARNING_CORPUS_TACTICAL_PREPARED_ARTIFACTS_VERSION,
        LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_ARTIFACTS_VERSION,
    ) == (1, 1, 1, 1, 1, 1)
    assert LEARNING_CORPUS_WEB_OPERATIONS == (
        "initialize_corpus",
        "reload_corpus",
        "import_match_workspace",
        "select_current_snapshot",
        "import_strategy_teacher_report",
        "remove_strategy_teacher_report",
        "clear_strategy_teacher_reports",
        "prepare_learning_artifacts",
    )
    assert LEARNING_CORPUS_WEB_RESULT_STATUSES == (
        "applied",
        "unchanged",
        "revision_conflict",
        "persistence_conflict",
        "resolution_required",
        "reloaded",
        "prepared",
        "source_changed",
    )
    assert LEARNING_CORPUS_STRATEGY_SOURCE_BINDING_STATUSES == (
        "current",
        "non_current",
    )
    assert (
        LEARNING_CORPUS_WEB_ROOT_POLICY,
        LEARNING_CORPUS_WEB_UPLOAD_POLICY,
        LEARNING_CORPUS_WEB_MUTATION_POLICY,
        LEARNING_CORPUS_WEB_REPORT_SOURCE_POLICY,
        LEARNING_CORPUS_WEB_PREPARATION_POLICY,
        LEARNING_CORPUS_WEB_INVALIDATION_POLICY,
        LEARNING_CORPUS_WEB_STALE_SOURCE_POLICY,
        LEARNING_CORPUS_WEB_SECURITY_POLICY,
        LEARNING_CORPUS_WEB_PRESENTATION_POLICY,
        LEARNING_CORPUS_WEB_ASSET_POLICY,
        LEARNING_CORPUS_WEB_DOWNLOAD_POLICY,
        LEARNING_CORPUS_WEB_NETWORK_POLICY,
    ) == (
        "one_explicit_corpus_root_per_server",
        "strict_uploaded_json_without_caller_server_path",
        "optimistic_catalog_compare_and_swap",
        "session_local_exact_decision_report_sources",
        "explicit_rebuild_without_analysis_execution",
        "invalidate_prepared_artifacts_on_source_change",
        "non_current_report_sources_block_preparation_until_removed",
        "loopback_token_cookie_same_origin",
        "server_rendered_with_progressive_enhancement",
        "packaged_local_assets_without_external_dependencies",
        "authenticated_private_downloads_without_server_paths",
        "no_external_requests",
    )
    assert LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES == 16_777_216
    assert LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES == 2_048


def test_result_envelope_is_strict_frozen_and_path_free() -> None:
    result = LearningCorpusWebResultV1(
        operation="reload_corpus",
        status="reloaded",
        http_status=200,
        message="Reloaded.",
        state={"values": [1, 2]},
    )
    assert result.to_dict() == {
        "learning_corpus_web_protocol_version": 1,
        "operation": "reload_corpus",
        "status": "reloaded",
        "http_status": 200,
        "message": "Reloaded.",
        "state": {"values": [1, 2]},
    }
    with pytest.raises(TypeError):
        result.state["path"] = "not-allowed"
    with pytest.raises(FrozenInstanceError):
        result.status = "applied"
    with pytest.raises(ValueError, match="must equal 1"):
        replace(result, learning_corpus_web_protocol_version=True)


def test_context_startup_initialization_reload_and_shutdown(tmp_path: Path) -> None:
    absent_root = tmp_path / "absent"
    context = LearningCorpusWebContextV1.open(absent_root)
    assert context.store is None
    assert context.corpus_root == absent_root

    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    assert LearningCorpusWebContextV1.open(empty_root).store is None

    initialize = initialize_learning_corpus_web_v1(context, corpus_id="corpus-start")
    assert initialize.state["initialized"] is True
    assert "root" not in initialize.to_dict()["state"]
    reopened = LearningCorpusWebContextV1.open(absent_root)
    assert reopened.store == context.store
    generation = reopened.generation
    reload_result = reload_learning_corpus_web_v1(reopened)
    assert reload_result.status == "reloaded"
    assert reopened.generation == generation + 1

    invalid_root = tmp_path / "invalid"
    invalid_root.mkdir()
    (invalid_root / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises((FileNotFoundError, ValueError)):
        LearningCorpusWebContextV1.open(invalid_root)

    root_file = tmp_path / "file"
    root_file.write_text("not a directory", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        LearningCorpusWebContextV1.open(root_file)
    with pytest.raises(FileNotFoundError):
        LearningCorpusWebContextV1.open(tmp_path / "missing-parent" / "corpus")

    _prepare_empty(reopened)
    reopened.shutdown()
    assert reopened.strategy_source_store.sources == ()
    assert reopened.prepared_artifacts is None
    assert reopened.tactical_prepared_artifacts is None
    assert reopened.tactical_coaching_prepared_artifacts is None


def test_source_store_duplicate_limit_order_and_classification(
    immediate_bundle,
    auto_bundle,
) -> None:
    workspace, snapshot, _result, _report, immediate, store = immediate_bundle
    _auto_workspace, auto_snapshot, _auto_result, _auto_report, auto, _ = auto_bundle
    assert auto_snapshot.match_snapshot_id == snapshot.match_snapshot_id

    source_store = LearningCorpusStrategyTeacherSourceStoreV1(max_sources=2)
    assert source_store.add(auto) == "applied"
    assert source_store.add(immediate) == "applied"
    assert tuple(
        source.report.value.options.recommendation_method for source in source_store.sources
    ) == ("immediate_expected_value", "auto")
    revision = source_store.revision
    assert source_store.add(immediate) == "unchanged"
    assert source_store.revision == revision
    assert source_store.binding_status(immediate, store) == "current"
    changed = replace_match_workspace_definition_v1(
        workspace,
        replace(workspace.match_definition, title="Non-current source"),
        expected_revision=workspace.revision,
    )
    changed_snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(changed.workspace)
    )
    non_current_store = _store(
        snapshot,
        changed_snapshot,
        current=(changed_snapshot,),
    )
    assert source_store.binding_status(immediate, non_current_store) == "non_current"

    limited = LearningCorpusStrategyTeacherSourceStoreV1(max_sources=1)
    assert limited.add(immediate) == "applied"
    with pytest.raises(ValueError, match="limit"):
        limited.add(auto)
    assert limited.remove("0" * 64) == "unchanged"
    assert limited.remove(immediate.source_binding_id) == "applied"
    revision = limited.revision
    assert limited.clear() == "unchanged"
    assert limited.revision == revision
    with pytest.raises(ValueError, match="positive integer"):
        LearningCorpusStrategyTeacherSourceStoreV1(max_sources=True)


def test_one_source_validation_and_source_operations_do_not_build_collection(
    tmp_path: Path,
    immediate_bundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _workspace, _snapshot, _analysis, _report, source, store = immediate_bundle
    context = LearningCorpusWebContextV1(
        corpus_root=tmp_path / "unused",
        store=store,
    )
    validate_learning_corpus_strategy_teacher_report_source_v1(store, source)
    monkeypatch.setattr(
        preparation_module,
        "build_learning_corpus_strategy_teacher_evidence_collection_v1",
        lambda *_args, **_kwargs: pytest.fail("collection must not be built on add"),
    )

    first = import_strategy_teacher_report_into_learning_corpus_web_v1(
        context,
        source,
    )
    assert first.status == "applied"
    generation = context.generation
    duplicate = import_strategy_teacher_report_into_learning_corpus_web_v1(
        context,
        source,
    )
    assert duplicate.status == "unchanged"
    assert context.generation == generation
    removed = remove_strategy_teacher_report_from_learning_corpus_web_v1(
        context,
        source_binding_id=source.source_binding_id,
    )
    assert removed.status == "applied"
    assert context.generation == generation + 1
    assert clear_strategy_teacher_reports_from_learning_corpus_web_v1(context).status == (
        "unchanged"
    )


def test_non_current_source_blocks_preparation_before_any_builder(
    tmp_path: Path,
    immediate_bundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, snapshot, _analysis, _report, source, current_store = immediate_bundle
    context = LearningCorpusWebContextV1(
        corpus_root=tmp_path / "unused-stale",
        store=current_store,
    )
    assert context.strategy_source_store.add(source) == "applied"
    changed = replace_match_workspace_definition_v1(
        workspace,
        replace(workspace.match_definition, title="Selected after source upload"),
        expected_revision=workspace.revision,
    )
    changed_snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(changed.workspace)
    )
    context.store = _store(
        snapshot,
        changed_snapshot,
        current=(changed_snapshot,),
    )
    monkeypatch.setattr(
        preparation_module,
        "build_learning_corpus_player_catalog_v1",
        lambda *_args, **_kwargs: pytest.fail("stale source reached a builder"),
    )
    with pytest.raises(ValueError, match="non-current"):
        prepare_learning_corpus_artifacts_web_v1(
            context,
            dataset_id="dataset-stale-source",
            known_player_seed=0,
            unseen_player_seed=0,
            train_weight=1,
            validation_weight=1,
            test_weight=1,
        )


def test_workspace_import_selection_conflicts_and_invalidation(
    tmp_path: Path,
    immediate_bundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _snapshot, _analysis, _report, _source, _store_value = immediate_bundle
    context = _initialize(tmp_path, "corpus-operations")
    prepared = _prepare_empty(context, "dataset-before-import")
    tactical_prepared = context.tactical_prepared_artifacts
    assert tactical_prepared is not None
    coaching_prepared = context.tactical_coaching_prepared_artifacts
    assert coaching_prepared is not None
    generation = context.generation
    workspace_path = tmp_path / "uploaded-workspace.json"
    _save_workspace(workspace_path, workspace)

    calls = 0
    original_import = operations_module.import_match_workspace_file_into_learning_corpus_v1

    def counted_import(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_import(*args, **kwargs)

    monkeypatch.setattr(
        operations_module,
        "import_match_workspace_file_into_learning_corpus_v1",
        counted_import,
    )
    imported = import_match_workspace_into_learning_corpus_web_v1(
        context,
        workspace_path,
        selection_mode="select_imported",
        same_revision_resolution="reject",
        expected_catalog_revision=0,
    )
    assert calls == 1
    assert imported.status == "applied"
    assert context.prepared_artifacts is None
    assert context.tactical_prepared_artifacts is None
    assert context.tactical_coaching_prepared_artifacts is None
    assert context.generation == generation + 1
    assert context.store is not None
    first_snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )

    context.prepared_artifacts = prepared
    context.tactical_prepared_artifacts = tactical_prepared
    context.tactical_coaching_prepared_artifacts = coaching_prepared
    generation = context.generation
    duplicate = import_match_workspace_into_learning_corpus_web_v1(
        context,
        workspace_path,
        selection_mode="select_imported",
        same_revision_resolution="reject",
        expected_catalog_revision=1,
    )
    assert duplicate.status == "unchanged"
    assert context.prepared_artifacts is prepared
    assert context.tactical_prepared_artifacts is tactical_prepared
    assert context.tactical_coaching_prepared_artifacts is coaching_prepared
    assert context.generation == generation
    conflict = import_match_workspace_into_learning_corpus_web_v1(
        context,
        workspace_path,
        selection_mode="select_imported",
        same_revision_resolution="reject",
        expected_catalog_revision=0,
    )
    assert conflict.status == "revision_conflict"
    assert conflict.http_status == 409
    assert context.prepared_artifacts is prepared
    assert context.tactical_prepared_artifacts is tactical_prepared
    assert context.tactical_coaching_prepared_artifacts is coaching_prepared

    changed = replace_match_workspace_definition_v1(
        workspace,
        replace(workspace.match_definition, title="Changed retained revision"),
        expected_revision=workspace.revision,
    )
    assert changed.status == "applied"
    changed_path = tmp_path / "uploaded-workspace-changed.json"
    _save_workspace(changed_path, changed.workspace)
    retained = import_match_workspace_into_learning_corpus_web_v1(
        context,
        changed_path,
        selection_mode="keep_current",
        same_revision_resolution="reject",
        expected_catalog_revision=1,
    )
    assert retained.status == "applied"
    changed_snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(changed.workspace)
    )
    assert context.store is not None
    assert context.store.document.catalog.current_matches[0].match_snapshot_id == (
        first_snapshot.match_snapshot_id
    )

    context.prepared_artifacts = prepared
    context.tactical_prepared_artifacts = tactical_prepared
    context.tactical_coaching_prepared_artifacts = coaching_prepared
    selected = select_current_learning_corpus_snapshot_web_v1(
        context,
        match_id=changed_snapshot.match_id,
        match_snapshot_id=changed_snapshot.match_snapshot_id,
        expected_catalog_revision=2,
    )
    assert selected.status == "applied"
    assert context.prepared_artifacts is None
    assert context.tactical_prepared_artifacts is None
    assert context.tactical_coaching_prepared_artifacts is None
    generation = context.generation
    unchanged = select_current_learning_corpus_snapshot_web_v1(
        context,
        match_id=changed_snapshot.match_id,
        match_snapshot_id=changed_snapshot.match_snapshot_id,
        expected_catalog_revision=3,
    )
    assert unchanged.status == "unchanged"
    assert context.generation == generation


def test_persistence_conflict_does_not_replace_or_invalidate_context(
    tmp_path: Path,
    immediate_bundle,
) -> None:
    workspace, _snapshot, _analysis, _report, _source, _store_value = immediate_bundle
    context = _initialize(tmp_path, "corpus-persistence-conflict")
    prepared = _prepare_empty(context, "dataset-conflict")
    tactical_prepared = context.tactical_prepared_artifacts
    assert tactical_prepared is not None
    coaching_prepared = context.tactical_coaching_prepared_artifacts
    assert coaching_prepared is not None
    assert context.store is not None
    original_store = context.store
    replacement = build_learning_corpus_catalog_persistence_document_v1(
        create_empty_learning_corpus_catalog_v1("externally-replaced-corpus")
    )
    write = save_learning_corpus_catalog_v1(
        context.corpus_root,
        replacement,
        expected_content_fingerprint=original_store.document.content_fingerprint,
    )
    assert write.status == "saved"
    workspace_path = tmp_path / "conflict-workspace.json"
    _save_workspace(workspace_path, workspace)
    generation = context.generation
    result = import_match_workspace_into_learning_corpus_web_v1(
        context,
        workspace_path,
        selection_mode="select_imported",
        same_revision_resolution="reject",
        expected_catalog_revision=0,
    )
    assert result.status == "persistence_conflict"
    assert result.http_status == 409
    assert context.store is original_store
    assert context.prepared_artifacts is prepared
    assert context.tactical_prepared_artifacts is tactical_prepared
    assert context.tactical_coaching_prepared_artifacts is coaching_prepared
    assert context.generation == generation


def test_preparation_contract_exact_counts_unlocked_and_source_changed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _initialize(tmp_path, "corpus-preparation")
    function_names = (
        "build_learning_corpus_player_catalog_v1",
        "build_learning_corpus_human_evidence_collection_v1",
        "build_learning_corpus_strategy_teacher_evidence_collection_v1",
        "build_learning_dataset_v2",
        "build_learning_dataset_partition_preparation_request_v1",
        "prepare_learning_dataset_v2_partitions_v1",
        "build_learning_dataset_v2_cross_game_summary_v1",
        "build_learning_corpus_tactical_motif_evidence_collection_v1",
        "build_learning_corpus_tactical_motif_cross_game_summary_v1",
        "build_learning_corpus_tactical_cross_game_coaching_report_v1",
    )
    originals = {name: getattr(preparation_module, name) for name in function_names}
    counts = {name: 0 for name in function_names}
    lock_was_available = False

    for name, original in originals.items():

        def wrapper(*args, _name=name, _original=original, **kwargs):
            nonlocal lock_was_available
            counts[_name] += 1
            if _name == "build_learning_corpus_player_catalog_v1":
                acquired = threading.Event()

                def take_lock() -> None:
                    with context.lock:
                        acquired.set()

                thread = threading.Thread(target=take_lock)
                thread.start()
                thread.join(timeout=1)
                lock_was_available = acquired.is_set()
                thread.join(timeout=1)
            return _original(*args, **kwargs)

        monkeypatch.setattr(preparation_module, name, wrapper)

    result = prepare_learning_corpus_artifacts_web_v1(
        context,
        dataset_id="dataset-exact-counts",
        known_player_seed=-7,
        unseen_player_seed=11,
        train_weight=2,
        validation_weight=1,
        test_weight=1,
    )
    assert result.status == "prepared"
    assert lock_was_available
    assert counts == {
        "build_learning_corpus_player_catalog_v1": 1,
        "build_learning_corpus_human_evidence_collection_v1": 1,
        "build_learning_corpus_strategy_teacher_evidence_collection_v1": 1,
        "build_learning_dataset_v2": 1,
        "build_learning_dataset_partition_preparation_request_v1": 2,
        "prepare_learning_dataset_v2_partitions_v1": 2,
        "build_learning_dataset_v2_cross_game_summary_v1": 1,
        "build_learning_corpus_tactical_motif_evidence_collection_v1": 1,
        "build_learning_corpus_tactical_motif_cross_game_summary_v1": 1,
        "build_learning_corpus_tactical_cross_game_coaching_report_v1": 1,
    }
    prepared = context.prepared_artifacts
    assert prepared is not None
    tactical_prepared = context.tactical_prepared_artifacts
    assert tactical_prepared is not None
    coaching_prepared = context.tactical_coaching_prepared_artifacts
    assert coaching_prepared is not None
    assert tuple(field.name for field in fields(prepared)) == (
        "learning_corpus_prepared_artifacts_version",
        "source_catalog_revision",
        "source_catalog_content_fingerprint",
        "strategy_source_binding_ids",
        "dataset_id",
        "known_player_base_random_seed",
        "unseen_player_base_random_seed",
        "partition_weights",
        "player_catalog",
        "human_evidence",
        "strategy_teacher_evidence",
        "learning_dataset",
        "known_player_partition_result",
        "unseen_player_partition_result",
        "cross_game_summary",
    )
    assert prepared.learning_dataset.status == "empty"
    assert prepared.known_player_partition_result.status == "unavailable"
    assert prepared.unseen_player_partition_result.status == "unavailable"
    assert prepared.to_dict()["dataset_id"] == "dataset-exact-counts"
    assert tuple(field.name for field in fields(tactical_prepared)) == (
        "learning_corpus_tactical_prepared_artifacts_version",
        "source_catalog_revision",
        "source_catalog_content_fingerprint",
        "player_catalog_fingerprint",
        "tactical_motif_collection",
        "tactical_motif_cross_game_summary",
    )
    assert tactical_prepared.tactical_motif_collection.status == "empty"
    assert tactical_prepared.tactical_motif_cross_game_summary.collection_status == (
        "empty"
    )
    assert tuple(field.name for field in fields(coaching_prepared)) == (
        "learning_corpus_tactical_coaching_prepared_artifacts_version",
        "source_catalog_revision",
        "source_catalog_content_fingerprint",
        "player_catalog_fingerprint",
        "strategy_teacher_collection_fingerprint",
        "tactical_motif_collection_fingerprint",
        "tactical_motif_cross_game_summary_fingerprint",
        "tactical_cross_game_coaching_report",
    )
    assert coaching_prepared.tactical_cross_game_coaching_report.status == "empty"
    with pytest.raises(FrozenInstanceError):
        prepared.dataset_id = "changed"
    with pytest.raises(ValueError, match="integer and not a boolean"):
        prepare_learning_corpus_artifacts_web_v1(
            context,
            dataset_id="dataset-invalid",
            known_player_seed=True,
            unseen_player_seed=0,
            train_weight=1,
            validation_weight=1,
            test_weight=1,
        )

    original_player_builder = originals["build_learning_corpus_player_catalog_v1"]
    newer_wrappers = {}

    def reload_and_publish_newer_during_build(store):
        context.reload()
        monkeypatch.setattr(
            preparation_module,
            "build_learning_corpus_player_catalog_v1",
            original_player_builder,
        )
        newer = prepare_learning_corpus_artifacts_web_v1(
            context,
            dataset_id="dataset-newer",
            known_player_seed=1,
            unseen_player_seed=1,
            train_weight=1,
            validation_weight=1,
            test_weight=1,
        )
        assert newer.status == "prepared"
        newer_wrappers.update(
            prepared=context.prepared_artifacts,
            tactical=context.tactical_prepared_artifacts,
            coaching=context.tactical_coaching_prepared_artifacts,
        )
        return original_player_builder(store)

    monkeypatch.setattr(
        preparation_module,
        "build_learning_corpus_player_catalog_v1",
        reload_and_publish_newer_during_build,
    )
    changed = prepare_learning_corpus_artifacts_web_v1(
        context,
        dataset_id="dataset-stale",
        known_player_seed=0,
        unseen_player_seed=0,
        train_weight=1,
        validation_weight=1,
        test_weight=1,
    )
    assert changed.status == "source_changed"
    assert changed.http_status == 409
    assert context.prepared_artifacts is not None
    assert context.prepared_artifacts.dataset_id == "dataset-newer"
    assert context.prepared_artifacts is newer_wrappers["prepared"]
    assert context.tactical_prepared_artifacts is newer_wrappers["tactical"]
    assert context.tactical_coaching_prepared_artifacts is newer_wrappers["coaching"]


def test_all_downloads_are_deterministic_and_do_not_rebuild_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _initialize(tmp_path, "cörpus downloads")
    _prepare_empty(context, "dätaset/downloads")
    before = tuple(sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")))
    for name in (
        "build_learning_corpus_player_catalog_v1",
        "build_learning_corpus_human_evidence_collection_v1",
        "build_learning_corpus_strategy_teacher_evidence_collection_v1",
        "build_learning_dataset_v2",
        "build_learning_dataset_partition_preparation_request_v1",
        "prepare_learning_dataset_v2_partitions_v1",
        "build_learning_dataset_v2_cross_game_summary_v1",
        "build_learning_corpus_tactical_motif_evidence_collection_v1",
        "build_learning_corpus_tactical_motif_cross_game_summary_v1",
        "build_learning_corpus_tactical_cross_game_coaching_report_v1",
    ):
        monkeypatch.setattr(
            preparation_module,
            name,
            lambda *_args, _name=name, **_kwargs: pytest.fail(
                f"download rebuilt source through {_name}"
            ),
        )

    first = tuple(
        build_learning_corpus_prepared_download_v1(context, kind=kind)
        for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
    )
    second = tuple(
        build_learning_corpus_prepared_download_v1(context, kind=kind)
        for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
    )
    assert first == second
    assert LEARNING_CORPUS_PREPARED_DOWNLOAD_KINDS == (
        "player_catalog",
        "human_evidence",
        "strategy_teacher_evidence",
        "learning_dataset_v2",
        "known_player_partitions",
        "unseen_player_partitions",
        "cross_game_summary",
    )
    assert LEARNING_CORPUS_TACTICAL_PREPARED_DOWNLOAD_KINDS == (
        "tactical_motif_evidence",
        "tactical_motif_cross_game_summary",
    )
    assert LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_DOWNLOAD_KINDS == (
        "tactical_cross_game_coaching",
    )
    assert tuple(item.kind for item in first) == (
        LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
    )
    assert len({item.filename for item in first}) == 10
    for item in first:
        assert item.filename.isascii()
        assert "/" not in item.filename and "\\" not in item.filename
        assert item.content.endswith(b"\n")
        assert not item.content.startswith(b"\xef\xbb\xbf")
        assert isinstance(json.loads(item.content), dict)
    after = tuple(sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")))
    assert after == before

    assert (
        build_learning_corpus_artifact_filename_v1(
            source_id=" ../../Ü 😺 ",
            artifact_identity="a" * 64,
            kind="player_catalog",
        )
        == "artifact-player-catalog-aaaaaaaaaaaa.json"
    )
    long_name = build_learning_corpus_artifact_filename_v1(
        source_id="x" * 100,
        artifact_identity="b" * 64,
        kind="learning_dataset_v2",
    )
    assert long_name.startswith(f"{'x' * 64}-learning-dataset-v2-")

    context.generation += 1
    with pytest.raises(LearningCorpusPreparedDownloadUnavailableError) as mismatch:
        build_learning_corpus_prepared_download_v1(context, kind="player_catalog")
    assert mismatch.value.reason == "source_mismatch"
    context.invalidate_prepared()
    with pytest.raises(LearningCorpusPreparedDownloadUnavailableError) as missing:
        build_learning_corpus_prepared_download_v1(context, kind="player_catalog")
    assert missing.value.reason == "missing"
