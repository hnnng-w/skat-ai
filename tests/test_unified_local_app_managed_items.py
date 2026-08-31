from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_local_match_capture_web import _creation_values
from test_match_decision_review_preparation import _workspace_with_partial_game
from test_match_workspace_contracts import _definition

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
import skatmind.app_web.learning_frontend as learning_frontend_module
import skatmind.app_web.managed_item_discovery as discovery_module
import skatmind.app_web.managed_item_import as import_module
from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.cross_area_transfer import (
    transfer_active_match_report_to_corpus_v1,
    transfer_active_match_workspace_to_corpus_v1,
)
from skatmind.app_web.learning_frontend import (
    build_unified_learning_download_v1,
    build_unified_learning_state_v1,
    create_unified_learning_corpus_v1,
    import_workspace_bytes_into_unified_learning_v1,
    open_unified_learning_corpus_v1,
    prepare_unified_learning_artifacts_v1,
    reload_unified_learning_corpus_v1,
)
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.managed_item_contracts import (
    FRONTEND_CROSS_AREA_TRANSFER_VERSION,
    GUIDED_SESSION_FRONTEND_VERSION,
    MANAGED_ITEM_DISCOVERY_STATUSES,
    MANAGED_ITEM_DISCOVERY_VERSION,
    MANAGED_ITEM_FAMILIES,
    MANAGED_STATEFUL_FRONTEND_POLICIES,
    MANAGED_STATEFUL_FRONTEND_VERSION,
    UNIFIED_LEARNING_FRONTEND_VERSION,
    UNIFIED_MATCH_CAPTURE_FRONTEND_VERSION,
    validate_managed_stateful_frontend_contract_v1,
)
from skatmind.app_web.managed_item_discovery import discover_managed_items_v1
from skatmind.app_web.managed_item_import import (
    decode_managed_item_json_object_v1,
    parse_managed_item_json_upload_v1,
)
from skatmind.app_web.managed_item_storage import (
    build_managed_item_handle_v1,
    build_managed_item_storage_name_v1,
    validate_managed_direct_child_path_v1,
)
from skatmind.app_web.match_frontend import (
    apply_unified_match_operation_v1,
    build_unified_match_state_v1,
    build_unified_match_workspace_download_v1,
    create_unified_match_v1,
    execute_unified_match_analysis_v1,
    import_unified_match_v1,
    open_unified_match_v1,
    reload_unified_match_v1,
    select_unified_match_position_v1,
)
from skatmind.app_web.session_form_translation import (
    build_session_command_from_form_v1,
    build_session_edit_from_form_v1,
    build_session_historical_execution_options_from_form_v1,
    build_session_position_options_from_form_v1,
)
from skatmind.app_web.session_frontend import (
    apply_guided_session_command_v1,
    build_guided_session_persistence_download_v1,
    correct_guided_session_command_v1,
    create_guided_session_v1,
    default_session_position_export_options_v1,
    execute_guided_session_position_v1,
    import_guided_session_v1,
    open_guided_session_v1,
    reload_guided_session_v1,
    rewind_guided_session_v1,
)
from skatmind.app_web.stateful_rendering import (
    render_guided_session_v1,
    render_managed_category_landing_v1,
)
from skatmind.capture_web.rendering import render_match_capture_web_body_v1
from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
from skatmind.corpus_web.rendering import render_learning_corpus_web_body_v1
from skatmind.learning_corpus_persistence import (
    initialize_learning_corpus_directory_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)
from skatmind.session_commands import SESSION_COMMAND_KINDS


def _players() -> tuple[session_api.SessionPlayerV1, ...]:
    return (
        session_api.SessionPlayerV1(
            player_id="alice",
            player_label="Alice",
            seat="forehand",
        ),
        session_api.SessionPlayerV1(
            player_id="bob",
            player_label="Bob",
            seat="middlehand",
        ),
        session_api.SessionPlayerV1(
            player_id="carol",
            player_label="Carol",
            seat="rearhand",
        ),
    )


def _save_session(path: Path, *, session_id: str = "session-212") -> None:
    state = session_api.create_session(
        session_id=session_id,
        players=_players(),
        capture_mode="retrospective",
    ).value
    document = session_api.build_session_persistence_document(state).value
    assert session_files.save_session_file(
        path,
        document,
        expected_content_fingerprint=None,
    ).value.status == "saved"


def _save_match(path: Path) -> None:
    document = build_match_workspace_persistence_document_v1(
        create_match_workspace_v1(_definition(match_id="match-212"))
    )
    assert save_match_workspace_file_v1(
        path,
        document,
        expected_content_fingerprint=None,
    ).status == "saved"


def _multipart(*, boundary: str, field_name: str, content: bytes) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="ignored.json"\r\n'
        "Content-Type: application/json\r\n"
        "\r\n"
    ).encode("ascii") + content + f"\r\n--{boundary}--\r\n".encode("ascii")


def test_issue_212_private_versions_and_policies_are_exact() -> None:
    assert MANAGED_STATEFUL_FRONTEND_VERSION == 1
    assert MANAGED_ITEM_DISCOVERY_VERSION == 1
    assert GUIDED_SESSION_FRONTEND_VERSION == 1
    assert UNIFIED_MATCH_CAPTURE_FRONTEND_VERSION == 1
    assert UNIFIED_LEARNING_FRONTEND_VERSION == 1
    assert FRONTEND_CROSS_AREA_TRANSFER_VERSION == 1
    assert MANAGED_ITEM_FAMILIES == ("sessions", "matches", "corpora")
    assert MANAGED_ITEM_DISCOVERY_STATUSES == (
        "available",
        "invalid",
        "resolution_required",
    )
    assert MANAGED_STATEFUL_FRONTEND_POLICIES == (
        "managed_category_discovery_is_explicit_and_non_recursive",
        "opaque_browser_handles_never_expose_filesystem_paths",
        "canonical_item_paths_are_derived_from_existing_product_identities",
        "strict_create_import_open_resume_reload_without_silent_overwrite",
        "existing_session_match_and_corpus_persistence_remains_authoritative",
        "one_active_process_local_context_per_stateful_family",
        "switching_items_discards_only_process_local_artifacts",
        "all_mutations_reuse_existing_operations_and_conflict_semantics",
        "cross_area_match_to_corpus_transfer_is_explicit_and_source_verified",
        "unified_app_cookie_and_security_context_only",
        "no_child_server_proxy_iframe_or_background_worker",
        "no_implicit_analysis_selection_preparation_or_conversion",
    )
    validate_managed_stateful_frontend_contract_v1()


def test_issue_212_contract_validation_rejects_version_and_policy_drift() -> None:
    with pytest.raises(ValueError, match="must equal 1"):
        validate_managed_stateful_frontend_contract_v1(
            managed_item_discovery_version=2
        )
    with pytest.raises(ValueError, match="exact Issue-#212"):
        validate_managed_stateful_frontend_contract_v1(
            policies=tuple(reversed(MANAGED_STATEFUL_FRONTEND_POLICIES))
        )


def test_managed_handles_and_storage_names_are_opaque_and_domain_separated() -> None:
    handle = build_managed_item_handle_v1(
        family="sessions",
        basename="private-name.json",
    )
    assert len(handle) == 64 and handle.isascii() and handle.islower()
    assert "private" not in handle and "/" not in handle and "\\" not in handle
    assert handle != build_managed_item_handle_v1(
        family="matches",
        basename="private-name.json",
    )
    assert build_managed_item_storage_name_v1(
        family="sessions",
        product_id="stable-id",
    ).startswith("session-")
    assert build_managed_item_storage_name_v1(
        family="matches",
        product_id="stable-id",
    ).endswith(".json")
    corpus_name = build_managed_item_storage_name_v1(
        family="corpora",
        product_id="stable-id",
    )
    assert corpus_name.startswith("corpus-") and not corpus_name.endswith(".json")
    assert len(corpus_name) == len("corpus-") + 64


def test_managed_discovery_classifies_all_three_families_without_paths(
    tmp_path: Path,
) -> None:
    sessions = tmp_path / "sessions"
    matches = tmp_path / "matches"
    corpora = tmp_path / "corpora"
    sessions.mkdir()
    matches.mkdir()
    corpora.mkdir()
    _save_session(sessions / "opaque.json")
    _save_match(matches / "opaque.json")
    initialize_learning_corpus_directory_v1(
        corpora / "opaque",
        corpus_id="corpus-212",
    )

    session_discovery = discover_managed_items_v1(
        sessions,
        family="sessions",
        generation=1,
    )
    match_discovery = discover_managed_items_v1(
        matches,
        family="matches",
        generation=2,
    )
    corpus_discovery = discover_managed_items_v1(
        corpora,
        family="corpora",
        generation=3,
    )
    assert session_discovery.view.items[0].semantic_product_id == "session-212"
    assert session_discovery.view.items[0].phase == "setup"
    assert match_discovery.view.items[0].semantic_product_id == "match-212"
    assert match_discovery.view.items[0].phase == "empty"
    assert corpus_discovery.view.items[0].semantic_product_id == "corpus-212"
    assert corpus_discovery.view.items[0].revision == 0
    serialized = json.dumps(
        {
            "sessions": session_discovery.view.to_dict(),
            "matches": match_discovery.view.to_dict(),
            "corpora": corpus_discovery.view.to_dict(),
        },
        sort_keys=True,
    ).lower()
    assert str(tmp_path).lower() not in serialized
    assert "opaque.json" not in serialized and "\\" not in serialized


def test_discovery_is_direct_bounded_generic_for_invalid_and_duplicate_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    _save_session(sessions / "one.json")
    _save_session(sessions / "two.json")
    (sessions / "broken-private-name.json").write_text("not json", encoding="utf-8")
    nested = sessions / "nested"
    nested.mkdir()
    _save_session(nested / "not-discovered.json", session_id="nested-session")

    discovered = discover_managed_items_v1(
        sessions,
        family="sessions",
        generation=4,
    )
    assert tuple(item.status for item in discovered.view.items) == (
        "invalid",
        "resolution_required",
        "resolution_required",
    )
    assert all(
        item.semantic_product_id == "session-212"
        for item in discovered.view.items
        if item.status == "resolution_required"
    )
    invalid = next(item for item in discovered.view.items if item.status == "invalid")
    assert invalid.semantic_product_id is invalid.display_label is None
    assert "broken-private-name" not in repr(discovered.view.to_dict())
    assert "nested-session" not in repr(discovered.view.to_dict())

    monkeypatch.setattr(discovery_module, "MANAGED_ITEM_MAX_CANDIDATES", 2)
    limited = discover_managed_items_v1(
        sessions,
        family="sessions",
        generation=5,
    )
    assert len(limited.view.items) == 2
    assert limited.view.candidate_limit_reached is True


def test_managed_json_decoder_and_multipart_are_strict_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert decode_managed_item_json_object_v1(b'{"value":1}') == {"value": 1}
    for invalid in (
        b'{"value":1,"value":2}',
        b"\xef\xbb\xbf{}",
        b"[]",
        b'{"value":NaN}',
    ):
        with pytest.raises(ValueError):
            decode_managed_item_json_object_v1(invalid)

    boundary = "SkatMind212"
    upload = parse_managed_item_json_upload_v1(
        _multipart(
            boundary=boundary,
            field_name="session_file",
            content=b'{"session":"safe"}',
        ),
        content_type=f"multipart/form-data; boundary={boundary}",
        expected_file_field="session_file",
    )
    assert dict(upload.document) == {"session": "safe"}
    assert upload.file_content == b'{"session":"safe"}'

    monkeypatch.setattr(import_module, "MANAGED_ITEM_MAX_IMPORT_BYTES", 2)
    with pytest.raises(OverflowError, match="too large"):
        decode_managed_item_json_object_v1(b"{} ")


def test_guided_session_create_apply_reload_and_download_use_public_persistence(
    tmp_path: Path,
) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    context = create_guided_session_v1(
        sessions,
        handle="a" * 64,
        session_id="guided-session",
        players=_players(),
        capture_mode="retrospective",
        local_player_id=None,
    )
    assert context.state.revision == 0
    assert context.path.name == build_managed_item_storage_name_v1(
        family="sessions",
        product_id="guided-session",
    )
    command = session_api.SetSessionGameMetadataCommandV1(
        expected_revision=0,
        game_id="game-1",
    )
    assert apply_guided_session_command_v1(context, command).status == "applied"
    assert context.state.revision == 1
    persisted = session_files.load_session_file(context.path).value.document
    assert persisted == context.document
    assert json.loads(build_guided_session_persistence_download_v1(context)) == (
        context.document.to_dict()
    )

    stale = session_api.SetSessionGameMetadataCommandV1(
        expected_revision=0,
        game_id="stale",
    )
    assert apply_guided_session_command_v1(context, stale).status == "rejected"
    assert context.state.revision == 1
    assert execute_guided_session_position_v1(
        context,
        export_options=default_session_position_export_options_v1(),
        execution_options=ExecutionOptionsV1(),
    ).status == "unavailable"

    assert reload_guided_session_v1(context).status == "reloaded"
    assert context.execution is None


def test_guided_session_cas_conflict_requires_explicit_reload(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    context = create_guided_session_v1(
        sessions,
        handle="b" * 64,
        session_id="conflict-session",
        players=_players(),
        capture_mode="retrospective",
        local_player_id=None,
    )
    external_result = session_api.apply_session_command(
        context.state,
        session_api.SetSessionGameMetadataCommandV1(
            expected_revision=0,
            game_id="external-game",
        ),
    )
    external_document = session_api.build_session_persistence_document(
        external_result.value.state
    ).value
    assert session_files.save_session_file(
        context.path,
        external_document,
        expected_content_fingerprint=context.document.content_fingerprint,
    ).value.status == "saved"

    operation = apply_guided_session_command_v1(
        context,
        session_api.SetSessionGameMetadataCommandV1(
            expected_revision=0,
            game_id="browser-game",
        ),
    )
    assert operation.status == "conflict"
    assert context.state.revision == 0
    assert reload_guided_session_v1(context).status == "reloaded"
    assert context.state.revision == 1
    assert context.state.command_log[-1].command.game_id == "external-game"


def test_guided_session_import_open_undo_and_correction_preserve_history(
    tmp_path: Path,
) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    source_state = session_api.create_session(
        session_id="imported-session",
        players=_players(),
        capture_mode="retrospective",
    ).value
    source_document = session_api.build_session_persistence_document(source_state).value
    context = import_guided_session_v1(
        sessions,
        handle="c" * 64,
        document=source_document.to_dict(),
    )
    with pytest.raises(FileExistsError, match="already uses"):
        import_guided_session_v1(
            sessions,
            handle="d" * 64,
            document=source_document.to_dict(),
        )
    first = session_api.SetSessionGameMetadataCommandV1(
        expected_revision=0,
        game_id="first",
    )
    second = session_api.SetSessionGameMetadataCommandV1(
        expected_revision=1,
        played_at="2026-08-31T10:00:00Z",
    )
    assert apply_guided_session_command_v1(context, first).status == "applied"
    assert apply_guided_session_command_v1(context, second).status == "applied"
    correction = session_api.SessionCommandCorrectionV1(
        expected_revision=2,
        target_revision=2,
        replacement_command=session_api.SetSessionGameMetadataCommandV1(
            expected_revision=1,
            played_at="2026-08-31T11:00:00Z",
        ),
    )
    assert correct_guided_session_command_v1(context, correction).status == "applied"
    assert (
        context.state.command_log[-1].command.played_at
        == "2026-08-31T11:00:00Z"
    )
    assert rewind_guided_session_v1(context, target_revision=1).status == "applied"
    assert context.state.revision == 1
    assert context.state.command_log[-1].command.game_id == "first"

    discovered = discover_managed_items_v1(
        sessions,
        family="sessions",
        generation=1,
    )
    opened = open_guided_session_v1(sessions, discovered.entries[0])
    assert opened.state == context.state


def test_managed_direct_child_validation_rejects_escape_and_links(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    direct = root / "direct.json"
    direct.write_text("{}", encoding="utf-8")
    validate_managed_direct_child_path_v1(root, direct, expected_kind="file")
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="direct category child"):
        validate_managed_direct_child_path_v1(root, outside, expected_kind="file")
    link = root / "link.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("This Windows account cannot create symbolic links.")
    with pytest.raises(ValueError, match="links and junctions"):
        validate_managed_direct_child_path_v1(root, link, expected_kind="file")


def test_unified_match_create_delegates_operations_and_redacts_storage_name(
    tmp_path: Path,
) -> None:
    matches = tmp_path / "matches"
    matches.mkdir()
    context = create_unified_match_v1(
        matches,
        handle="e" * 64,
        values=_creation_values(match_id="managed-match"),
    )
    assert context.workspace is not None and context.workspace.revision == 0
    assert context.path.name == build_managed_item_storage_name_v1(
        family="matches",
        product_id="managed-match",
    )
    state = build_unified_match_state_v1(context)
    assert state["workspace_filename"] == "managed-match.json"
    assert len(state["slots"]) == 36
    assert context.path.name not in json.dumps(state)

    result = apply_unified_match_operation_v1(
        context,
        {
            "operation": "start_game",
            "match_position": "1",
            "expected_revision": "0",
            "game_id": "game-1",
            "game_timecode_start": "",
            "game_timecode_end": "",
        },
    )
    assert result.status == "applied"
    assert context.workspace.revision == 1
    assert json.loads(build_unified_match_workspace_download_v1(context))[
        "workspace"
    ]["revision"] == 1
    select_unified_match_position_v1(context, 36)
    assert build_unified_match_state_v1(context)["selected_position"] == 36


def test_unified_match_import_open_reload_and_report_invalidation(tmp_path: Path) -> None:
    matches = tmp_path / "matches"
    matches.mkdir()
    source = build_match_workspace_persistence_document_v1(
        create_match_workspace_v1(_definition(match_id="import-match"))
    )
    context = import_unified_match_v1(
        matches,
        handle="f" * 64,
        document=source.to_dict(),
    )
    with pytest.raises(FileExistsError, match="already uses"):
        import_unified_match_v1(
            matches,
            handle="0" * 64,
            document=source.to_dict(),
        )
    analysis = execute_unified_match_analysis_v1(
        context,
        {
            "operation": "prepare_materialization",
            "expected_revision": "0",
            "match_position": "1",
        },
    )
    assert analysis.status == "applied"
    assert len(context.capture.report_store) == 1
    assert reload_unified_match_v1(context).status == "reloaded"
    assert len(context.capture.report_store) == 0

    discovered = discover_managed_items_v1(
        matches,
        family="matches",
        generation=1,
    )
    opened = open_unified_match_v1(matches, discovered.entries[0])
    assert opened.workspace == context.workspace


def test_capture_renderer_adapts_existing_ui_to_namespaced_shell_routes(
    tmp_path: Path,
) -> None:
    matches = tmp_path / "matches"
    matches.mkdir()
    context = create_unified_match_v1(
        matches,
        handle="1" * 64,
        values=_creation_values(match_id="render-match"),
    )
    body = render_match_capture_web_body_v1(
        build_unified_match_state_v1(context),
        route_prefix="/matches",
        notice="Retained notice",
        managed_handle=context.handle,
        additional_content='<section id="transfer-panel">Transfer</section>',
    )
    assert '<div id="capture-app">' in body
    assert 'action="/matches/api/v1/operation"' in body
    assert 'href="/matches/position/1"' in body
    assert 'href="https://www.youtube.com/watch?v=example"' in body
    assert "<main" not in body
    assert "<h1" not in body
    assert body.count(f'name="managed_handle" value="{context.handle}"') == body.count(
        "<form"
    )
    assert body.index('id="transfer-panel"') < body.rindex("</div>")
    assert context.path.name not in body


def test_unified_learning_create_open_import_prepare_and_download(tmp_path: Path) -> None:
    corpora = tmp_path / "corpora"
    matches = tmp_path / "matches"
    corpora.mkdir()
    matches.mkdir()
    learning = create_unified_learning_corpus_v1(
        corpora,
        handle="2" * 64,
        corpus_id="managed-corpus",
    )
    assert learning.path.name == build_managed_item_storage_name_v1(
        family="corpora",
        product_id="managed-corpus",
    )
    source = create_unified_match_v1(
        matches,
        handle="3" * 64,
        values=_creation_values(match_id="learning-source-match"),
    )
    imported = import_workspace_bytes_into_unified_learning_v1(
        learning,
        build_unified_match_workspace_download_v1(source),
        selection_mode="select_imported",
        same_revision_resolution="reject",
        expected_catalog_revision=0,
    )
    assert imported.status == "applied"
    state = build_unified_learning_state_v1(learning)
    assert state["corpus"]["logical_match_count"] == 1
    assert state["corpus"]["current_match_snapshot_count"] == 1

    prepared = prepare_unified_learning_artifacts_v1(
        learning,
        dataset_id="managed-dataset",
        known_player_seed=0,
        unseen_player_seed=0,
        train_weight=70,
        validation_weight=15,
        test_weight=15,
    )
    assert prepared.status == "prepared"
    for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
        download = build_unified_learning_download_v1(learning, kind=kind)
        assert download.kind == kind
        assert download.filename.endswith(".json")
        assert isinstance(json.loads(download.content), dict)

    assert reload_unified_learning_corpus_v1(learning).status == "reloaded"
    assert build_unified_learning_state_v1(learning)["prepared"] is None
    discovered = discover_managed_items_v1(
        corpora,
        family="corpora",
        generation=1,
    )
    opened = open_unified_learning_corpus_v1(corpora, discovered.entries[0])
    assert opened.corpus.store.document == learning.corpus.store.document


def test_unified_learning_mutation_revalidates_managed_containment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpora = tmp_path / "corpora"
    corpora.mkdir()
    context = create_unified_learning_corpus_v1(
        corpora,
        handle="4" * 64,
        corpus_id="containment-corpus",
    )

    def reject_replaced_path(*_args: object, **_kwargs: object) -> None:
        raise ValueError("Managed item links and junctions are not followed.")

    monkeypatch.setattr(
        learning_frontend_module,
        "validate_managed_direct_child_path_v1",
        reject_replaced_path,
    )
    with pytest.raises(ValueError, match="links and junctions"):
        learning_frontend_module.clear_unified_learning_report_sources_v1(context)


def test_learning_renderer_adapts_existing_ui_to_namespaced_shell_routes(
    tmp_path: Path,
) -> None:
    corpora = tmp_path / "corpora"
    corpora.mkdir()
    context = create_unified_learning_corpus_v1(
        corpora,
        handle="4" * 64,
        corpus_id="render-corpus",
    )
    body = render_learning_corpus_web_body_v1(
        build_unified_learning_state_v1(context),
        route_prefix="/learning",
        notice="Retained notice",
        managed_handle=context.handle,
    )
    assert '<div id="corpus-app">' in body
    assert 'action="/learning/api/v1/operations"' in body
    assert body.count(f'name="managed_handle" value="{context.handle}"') == body.count(
        "<form"
    )
    assert context.path.name not in body


def test_managed_stateful_context_tracks_generations_handles_and_active_items(
    tmp_path: Path,
) -> None:
    app = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "home"))
    with app.lock:
        first = app.managed_stateful.refresh("sessions")
        assert first.view.generation == 1 and first.view.items == ()
        storage_name = build_managed_item_storage_name_v1(
            family="sessions",
            product_id="active-session",
        )
        context = create_guided_session_v1(
            app.managed_stateful.root("sessions"),
            handle=build_managed_item_handle_v1(
                family="sessions",
                basename=storage_name,
            ),
            session_id="active-session",
            players=_players(),
            capture_mode="retrospective",
            local_player_id=None,
        )
        app.managed_stateful.activate_session(context)
        refreshed = app.managed_stateful.refresh("sessions")
        assert refreshed.view.generation == 2
        assert refreshed.view.items[0].active is True
        with pytest.raises(ValueError, match="discovery changed"):
            app.managed_stateful.resolve(
                "sessions",
                handle=refreshed.view.items[0].handle,
                generation=1,
            )
        entry = app.managed_stateful.resolve(
            "sessions",
            handle=refreshed.view.items[0].handle,
            generation=2,
        )
        assert entry.summary.semantic_product_id == "active-session"


def test_explicit_cross_area_workspace_and_report_transfers_are_path_free(
    tmp_path: Path,
) -> None:
    matches = tmp_path / "matches"
    corpora = tmp_path / "corpora"
    matches.mkdir()
    corpora.mkdir()
    workspace, _data = _workspace_with_partial_game()
    source_document = build_match_workspace_persistence_document_v1(workspace)
    source = import_unified_match_v1(
        matches,
        handle="6" * 64,
        document=source_document.to_dict(),
    )
    target = create_unified_learning_corpus_v1(
        corpora,
        handle="7" * 64,
        corpus_id="transfer-corpus",
    )
    workspace_transfer = transfer_active_match_workspace_to_corpus_v1(
        source,
        target,
        selection_mode="select_imported",
        same_revision_resolution="reject",
        expected_catalog_revision=0,
    )
    assert workspace_transfer.status == "applied"
    assert workspace_transfer.source_match_id == workspace.match_definition.match_id
    assert "path" not in json.dumps(workspace_transfer.to_dict()).lower()

    analyzed = execute_unified_match_analysis_v1(
        source,
        {
            "operation": "analyze_decision",
            "match_position": "3",
            "expected_revision": str(workspace.revision),
            "decision_index": "1",
        },
    )
    assert analyzed.status == "applied"
    report_id = analyzed.state["selected_report_id"]
    current_snapshot_id = build_unified_learning_state_v1(target)[
        "current_match_snapshots"
    ][0]["match_snapshot_id"]
    report_transfer = transfer_active_match_report_to_corpus_v1(
        source,
        target,
        report_id=report_id,
        match_snapshot_id=current_snapshot_id,
    )
    assert report_transfer.status == "applied"
    assert report_transfer.source_report_id == report_id
    assert len(target.corpus.strategy_source_store.sources) == 1


@pytest.mark.parametrize(
    ("kind", "fields"),
    (
        ("set_game_metadata", {"game_id": "game-1", "played_at": ""}),
        (
            "record_dealt_card",
            {"destination": "player_hand", "player_id": "alice", "card": "CA"},
        ),
        ("set_declarer", {"player_id": "alice"}),
        (
            "set_declaration",
            {
                "game_type": "grand",
                "hand_game": "true",
                "ouvert": "false",
                "schneider_announced": "false",
                "schwarz_announced": "false",
                "matadors": "2",
                "bid_value": "24",
            },
        ),
        ("record_discard", {"card": "D7"}),
        ("record_play", {"player_id": "alice", "card": "S7"}),
        (
            "set_game_event",
            {
                "event_kind": "defender_open_play_continuation",
                "after_play_count": "3",
                "player_id": "bob",
                "cards": "CA, C10",
            },
        ),
        (
            "set_game_end",
            {"game_end_reason": "normal_completion"},
        ),
        ("promote_to_retrospective", {}),
        (
            "set_public_hand",
            {"player_id": "alice", "cards": "CA C10"},
        ),
    ),
)
def test_guided_session_forms_build_all_ten_typed_commands(
    kind: str,
    fields: dict[str, str],
) -> None:
    command = build_session_command_from_form_v1(
        {"kind": kind, **fields},
        expected_revision=4,
    )
    assert command.kind == kind
    assert command.expected_revision == 4


def test_guided_session_forms_build_strict_exposure_end_and_correction() -> None:
    values = {
        "kind": "set_game_end",
        "game_end_reason": "declarer_card_exposure",
        "exposure_form": "shown_to_defender",
        "shown_to_defender_player_id": "bob",
        "cards": "CA C10",
        "claimed_play_level": "simple",
        "defender_1_player_id": "bob",
        "defender_1_response": "accept",
        "defender_1_form": "explicit",
        "defender_2_player_id": "carol",
        "defender_2_response": "accept",
        "defender_2_form": "unambiguous_conduct",
        "target_revision": "3",
    }
    edit = build_session_edit_from_form_v1(values, current_revision=7)
    assert isinstance(edit, session_api.SessionCommandCorrectionV1)
    assert edit.expected_revision == 7
    assert edit.target_revision == 3
    assert edit.replacement_command.expected_revision == 2
    game_end = edit.replacement_command.to_dict()["game_end"]
    assert game_end["exposure"]["shown_to_defender_player_id"] == "bob"
    assert game_end["defender_responses"][1]["form"] == "unambiguous_conduct"


def test_guided_session_analysis_forms_reuse_existing_option_contracts() -> None:
    position = build_session_position_options_from_form_v1(
        {
            "sample_count": "25",
            "random_seed": "7",
            "opponent_strategy": "basic",
            "recommendation_method": "bounded_search",
            "search_budget_profile": "interactive_v1",
        }
    )
    assert position.sample_count == 25
    assert position.recommendation_method == "bounded_search"
    assert position.bounded_search_settings["random_seed"] == 7

    historical = build_session_historical_execution_options_from_form_v1(
        {
            "decision_snapshots": "true",
            "immediate_review": "true",
            "search_review": "false",
            "information_set_search_review": "false",
            "replay_coaching": "false",
            "information_set_replay_coaching": "false",
            "historical_tactical_motif_review": "true",
            "sample_count": "50",
            "random_seed": "8",
            "search_seed": "9",
            "search_budget_profile": "historical_review_v1",
        }
    )
    assert historical.workflow_options["immediate_sample_count"] == 50
    assert historical.workflow_options["historical_tactical_motif_review"] is True


def test_managed_landing_and_guided_session_render_without_storage_paths(
    tmp_path: Path,
) -> None:
    app = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "home"))
    sessions = app.managed_stateful.root("sessions")
    storage_name = build_managed_item_storage_name_v1(
        family="sessions",
        product_id="render-session",
    )
    context = create_guided_session_v1(
        sessions,
        handle=build_managed_item_handle_v1(
            family="sessions",
            basename=storage_name,
        ),
        session_id="render-session",
        players=_players(),
        capture_mode="retrospective",
        local_player_id=None,
    )
    with app.lock:
        app.managed_stateful.activate_session(context)
        landing = render_managed_category_landing_v1(
            app.managed_stateful.refresh("sessions").view
        )
    rendered = render_guided_session_v1(context)
    assert 'action="/sessions/open"' in landing
    assert 'action="/sessions/create"' in landing
    assert str(tmp_path) not in landing
    assert all(f'value="{kind}"' in rendered for kind in SESSION_COMMAND_KINDS)
    assert rendered.count('action="/sessions/command"') == 10
    assert rendered.count(f'name="managed_handle" value="{context.handle}"') == rendered.count(
        "<form"
    )
    assert 'action="/sessions/analyze"' in rendered
    assert context.path.name not in rendered
