from __future__ import annotations

import http.client
import json
import socket
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlencode

import pytest
from test_learning_corpus_strategy_teacher import _changed_report, _source_bundle

import skatmind.corpus_web.server as server_module
import skatmind.corpus_web.uploads as uploads_module
from skatmind.corpus_web.context import LearningCorpusWebContextV1
from skatmind.corpus_web.contracts import LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES
from skatmind.corpus_web.downloads import (
    LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS,
    build_learning_corpus_prepared_download_v1,
)
from skatmind.corpus_web.security import LEARNING_CORPUS_WEB_COOKIE_NAME
from skatmind.corpus_web.server import (
    serve_learning_corpus_web_in_thread_v1,
    start_learning_corpus_web_server_v1,
)
from skatmind.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)
from skatmind.match_workspace_operations import replace_match_workspace_definition_v1
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _request(
    server,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
    request_headers = {"Host": f"127.0.0.1:{server.port}", **(headers or {})}
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    content = response.read()
    result = response.status, dict(response.getheaders()), content
    connection.close()
    return result


def _raw_request(
    server,
    method: str,
    path: str,
    headers: tuple[tuple[str, str], ...],
    *,
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
    connection.putrequest(method, path, skip_host=True)
    for name, value in headers:
        connection.putheader(name, value)
    connection.endheaders(body)
    response = connection.getresponse()
    content = response.read()
    result = response.status, dict(response.getheaders()), content
    connection.close()
    return result


def _bootstrap(server) -> str:
    status, headers, _content = _request(
        server,
        "GET",
        f"/?token={server.corpus_token}",
    )
    assert status == 303
    assert headers["Location"] == "/"
    cookie = headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    return cookie.split(";", 1)[0]


def _post_form(server, cookie: str, values: dict[str, object]):
    body = urlencode(values).encode()
    return _request(
        server,
        "POST",
        "/api/v1/operations",
        headers={
            "Cookie": cookie,
            "Origin": server.origin,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body=body,
    )


def _multipart(
    fields: dict[str, object],
    *,
    file_field: str,
    file_content: bytes,
    filename: str = "caller-private-name.json",
) -> tuple[bytes, str]:
    boundary = "skatmind-http-boundary"
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields.items()
    ]
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\nContent-Type: application/json\r\n\r\n'.encode()
        + file_content
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _post_upload(
    server,
    cookie: str,
    fields: dict[str, object],
    *,
    file_field: str,
    file_content: bytes,
    filename: str = "caller-private-name.json",
):
    body, content_type = _multipart(
        fields,
        file_field=file_field,
        file_content=file_content,
        filename=filename,
    )
    return _request(
        server,
        "POST",
        "/api/v1/operations",
        headers={
            "Cookie": cookie,
            "Origin": server.origin,
            "Content-Type": content_type,
        },
        body=body,
    )


def _workspace_bytes(workspace) -> bytes:
    document = build_match_workspace_persistence_document_v1(workspace)
    return (
        json.dumps(document.to_dict(), ensure_ascii=True, allow_nan=False, indent=2) + "\n"
    ).encode()


@pytest.fixture
def running_server(tmp_path: Path):
    context = LearningCorpusWebContextV1.open(tmp_path / "corpus-root")
    server = start_learning_corpus_web_server_v1(
        context,
        port=0,
        token="corpus-test-token",
    )
    thread = serve_learning_corpus_web_in_thread_v1(server)
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_loopback_bootstrap_host_cookie_origin_headers_assets_and_methods(
    running_server,
) -> None:
    server = running_server
    assert server.server_address[0] == "127.0.0.1"
    assert server.bootstrap_url.endswith("/?token=corpus-test-token")

    assert _request(server, "GET", "/")[0] == 403
    assert _request(server, "GET", "/", headers={"Host": "evil.example"})[0] == 403
    assert _request(server, "GET", "/?token=wrong")[0] == 403
    cookie = _bootstrap(server)

    status, headers, page = _request(server, "GET", "/", headers={"Cookie": cookie})
    assert status == 200
    assert b"Initialize the Learning Corpus" in page
    assert b"corpus-test-token" not in page
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "Access-Control-Allow-Origin" not in headers

    for path, marker in (
        ("/assets/corpus.css", b"--moss"),
        ("/assets/corpus.js", b"One local JSON file selected"),
    ):
        asset_status, asset_headers, asset = _request(
            server,
            "GET",
            path,
            headers={"Cookie": cookie},
        )
        assert asset_status == 200
        assert marker in asset
        assert "https://" not in asset.decode()
        assert asset_headers["Cache-Control"] == "no-store"

    assert (
        _request(server, "GET", "/assets/../templates/page.html", headers={"Cookie": cookie})[0]
        == 404
    )
    assert _request(server, "GET", "/unknown", headers={"Cookie": cookie})[0] == 404
    assert _request(server, "GET", "/api/v1/operations", headers={"Cookie": cookie})[0] == 405
    assert _request(server, "DELETE", "/", headers={"Cookie": cookie})[0] == 405
    assert _request(server, "DELETE", "/unknown", headers={"Cookie": cookie})[0] == 404
    assert _request(server, "DELETE", "/")[0] == 403

    body = urlencode({"operation": "initialize_corpus", "corpus_id": "blocked"}).encode()
    assert (
        _request(
            server,
            "POST",
            "/api/v1/operations",
            headers={
                "Cookie": cookie,
                "Origin": "http://evil.example",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=body,
        )[0]
        == 403
    )
    assert (
        _request(
            server,
            "POST",
            "/api/v1/operations",
            headers={
                "Cookie": cookie,
                "Origin": f"{server.origin}////",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=body,
        )[0]
        == 403
    )

    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
    connection.putrequest("GET", "/", skip_host=True)
    connection.putheader("Host", f"127.0.0.1:{server.port}")
    connection.putheader("Host", "localhost")
    connection.putheader("Cookie", cookie)
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 403
    response.read()
    connection.close()
    assert (
        _request(
            server,
            "POST",
            "/api/v1/operations",
            headers={
                "Cookie": cookie,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=body,
        )[0]
        == 403
    )


def test_browser_referrer_policy_matches_mutation_origin_contract(running_server) -> None:
    server = running_server
    cookie = _bootstrap(server)
    status, headers, _body = _request(server, "GET", "/", headers={"Cookie": cookie})
    assert status == 200
    assert headers["Referrer-Policy"] == "origin"
    assert "Access-Control-Allow-Origin" not in headers

    values = {"operation": "initialize_corpus", "corpus_id": "policy-corpus"}
    status, _headers, _body = _post_form(server, cookie, values)
    assert status == 200

    body = urlencode(values).encode()
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/operations",
        headers={
            "Cookie": cookie,
            "Origin": "null",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body=body,
    )
    assert status == 403


def test_duplicate_corpus_authorization_headers_and_cookie_are_rejected(
    running_server,
) -> None:
    server = running_server
    cookie = _bootstrap(server)
    host = f"127.0.0.1:{server.port}"
    base = (
        ("Host", host),
        ("Cookie", cookie),
        ("Origin", server.origin),
        ("Content-Length", "0"),
        ("Content-Type", "application/x-www-form-urlencoded"),
    )
    for duplicated_name in ("Host", "Cookie", "Origin"):
        duplicated_value = {
            "Host": host,
            "Cookie": cookie,
            "Origin": server.origin,
        }[duplicated_name]
        status, _headers, _body = _raw_request(
            server,
            "POST",
            "/api/v1/operations",
            (*base, (duplicated_name, duplicated_value)),
        )
        assert status == 403

    for duplicated_cookie in (
        f"{cookie}; {cookie}",
        f"{LEARNING_CORPUS_WEB_COOKIE_NAME}=wrong, {cookie}",
    ):
        status, _headers, _body = _request(
            server,
            "POST",
            "/api/v1/operations",
            headers={
                "Cookie": duplicated_cookie,
                "Origin": server.origin,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=b"",
        )
        assert status == 403


def test_corpus_access_logging_is_disabled(
    running_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    server = running_server
    status, _headers, _body = _request(
        server,
        "GET",
        f"/?token={server.corpus_token}",
    )
    assert status == 303
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


def test_request_limit_required_length_and_validation_errors(running_server) -> None:
    server = running_server
    cookie = _bootstrap(server)

    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
    connection.putrequest("POST", "/api/v1/operations", skip_host=True)
    connection.putheader("Host", f"127.0.0.1:{server.port}")
    connection.putheader("Cookie", cookie)
    connection.putheader("Origin", server.origin)
    connection.putheader("Content-Type", "application/x-www-form-urlencoded")
    connection.putheader("Content-Length", str(LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES + 1))
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 413
    response.read()
    connection.close()

    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
    connection.putrequest("POST", "/api/v1/operations", skip_host=True)
    connection.putheader("Host", f"127.0.0.1:{server.port}")
    connection.putheader("Cookie", cookie)
    connection.putheader("Origin", server.origin)
    connection.putheader("Content-Type", "application/x-www-form-urlencoded")
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 400
    response.read()
    connection.close()

    status, _headers, content = _post_form(
        server,
        cookie,
        {"operation": "unknown"},
    )
    assert status == 400
    assert b"supported operation" in content

    short_body = urlencode(
        {"operation": "initialize_corpus", "corpus_id": "must-not-apply"}
    ).encode()
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
    connection.putrequest("POST", "/api/v1/operations", skip_host=True)
    connection.putheader("Host", f"127.0.0.1:{server.port}")
    connection.putheader("Cookie", cookie)
    connection.putheader("Origin", server.origin)
    connection.putheader("Content-Type", "application/x-www-form-urlencoded")
    connection.putheader("Content-Length", str(len(short_body) + 5))
    connection.endheaders(short_body)
    assert connection.sock is not None
    connection.sock.shutdown(socket.SHUT_WR)
    response = connection.getresponse()
    assert response.status == 400
    response.read()
    connection.close()
    assert server.corpus_context.store is None


def test_no_javascript_end_to_end_upload_prepare_download_and_invalidation(
    running_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = running_server
    context = server.corpus_context
    cookie = _bootstrap(server)
    workspace, snapshot, _analysis, report, _source, _store = _source_bundle()

    status, _headers, page = _post_form(
        server,
        cookie,
        {"operation": "initialize_corpus", "corpus_id": "corpus-browser"},
    )
    assert status == 200
    assert b"Learning Corpus initialized" in page
    assert context.store is not None

    status, _headers, page = _post_upload(
        server,
        cookie,
        {
            "operation": "import_match_workspace",
            "selection_mode": "select_imported",
            "same_revision_resolution": "reject",
            "expected_catalog_revision": 0,
        },
        file_field="workspace_file",
        file_content=_workspace_bytes(workspace),
        filename="../../do-not-persist.json",
    )
    assert status == 200
    assert b"Match Workspace imported" in page
    assert context.store is not None
    assert context.store.document.catalog.current_matches[0].match_snapshot_id == (
        snapshot.match_snapshot_id
    )
    assert not any("do-not-persist" in path.name for path in context.corpus_root.rglob("*"))

    wrong_revision = _post_upload(
        server,
        cookie,
        {
            "operation": "import_match_workspace",
            "selection_mode": "select_imported",
            "same_revision_resolution": "reject",
            "expected_catalog_revision": 0,
        },
        file_field="workspace_file",
        file_content=_workspace_bytes(workspace),
    )
    assert wrong_revision[0] == 409
    assert b"no Corpus change" in wrong_revision[2]

    report_export = build_match_analysis_report_source_export_v1(report)
    report_bytes = serialize_match_analysis_report_source_export_v1(report_export)
    tampered_request = report.value.request.to_dict()["document"]
    tampered_request["random_seed"] = 99
    tampered_report = _changed_report(
        report.value,
        request_document=tampered_request,
    )
    tampered_bytes = serialize_match_analysis_report_source_export_v1(
        build_match_analysis_report_source_export_v1(tampered_report)
    )
    invalid_source = _post_upload(
        server,
        cookie,
        {
            "operation": "import_strategy_teacher_report",
            "match_snapshot_id": snapshot.match_snapshot_id,
        },
        file_field="report_source_file",
        file_content=tampered_bytes,
    )
    assert invalid_source[0] == 400
    assert b"does not reconcile" in invalid_source[2]
    assert context.strategy_source_store.sources == ()

    monkeypatch.setattr(
        uploads_module.tempfile,
        "mkstemp",
        lambda **_kwargs: pytest.fail("Report-source upload wrote a temporary file"),
    )
    status, _headers, page = _post_upload(
        server,
        cookie,
        {
            "operation": "import_strategy_teacher_report",
            "match_snapshot_id": snapshot.match_snapshot_id,
        },
        file_field="report_source_file",
        file_content=report_bytes,
    )
    assert status == 200
    assert b"Report source added" in page
    assert b"immediate_expected_value" in page
    assert len(context.strategy_source_store.sources) == 1

    generation = context.generation
    duplicate = _post_upload(
        server,
        cookie,
        {
            "operation": "import_strategy_teacher_report",
            "match_snapshot_id": snapshot.match_snapshot_id,
        },
        file_field="report_source_file",
        file_content=report_bytes,
    )
    assert duplicate[0] == 200
    assert b"already present" in duplicate[2]
    assert context.generation == generation

    status, _headers, page = _post_form(
        server,
        cookie,
        {
            "operation": "prepare_learning_artifacts",
            "dataset_id": "corpus-browser-learning-dataset-v2",
            "known_player_seed": 0,
            "unseen_player_seed": 0,
            "train_weight": 70,
            "validation_weight": 15,
            "test_weight": 15,
        },
    )
    assert status == 200
    assert b"Learning artifacts prepared" in page
    assert b"Dataset status" in page
    assert b"Known-player readiness" in page
    assert b"Tactical status" in page
    assert b"Tactical Motif Evidence" in page
    assert b"Tactical Coaching status" in page
    assert b"Tactical Cross-game Coaching" in page
    assert context.prepared_artifacts is not None
    assert context.tactical_prepared_artifacts is not None
    assert context.tactical_coaching_prepared_artifacts is not None

    route_by_kind = {
        "player_catalog": "/downloads/player-catalog.json",
        "human_evidence": "/downloads/human-evidence.json",
        "strategy_teacher_evidence": "/downloads/strategy-teacher-evidence.json",
        "learning_dataset_v2": "/downloads/learning-dataset-v2.json",
        "known_player_partitions": "/downloads/known-player-partitions.json",
        "unseen_player_partitions": "/downloads/unseen-player-partitions.json",
        "cross_game_summary": "/downloads/cross-game-summary.json",
        "tactical_motif_evidence": "/downloads/tactical-motif-evidence.json",
        "tactical_motif_cross_game_summary": (
            "/downloads/tactical-motif-cross-game-summary.json"
        ),
        "tactical_cross_game_coaching": (
            "/downloads/tactical-cross-game-coaching.json"
        ),
    }
    assert tuple(route_by_kind) == LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
    assert _request(
        server,
        "GET",
        "/downloads/tactical-cross-game-coaching.json",
    )[0] == 403
    files_before = tuple(
        sorted(path.relative_to(context.corpus_root) for path in context.corpus_root.rglob("*"))
    )
    for kind, route in route_by_kind.items():
        expected = build_learning_corpus_prepared_download_v1(context, kind=kind)
        download_status, download_headers, content = _request(
            server,
            "GET",
            route,
            headers={"Cookie": cookie},
        )
        assert download_status == 200
        assert content == expected.content
        assert content.endswith(b"\n") and b"\r" not in content
        assert download_headers["Content-Type"] == "application/json; charset=utf-8"
        assert download_headers["Content-Disposition"] == (
            f'attachment; filename="{expected.filename}"'
        )
    files_after = tuple(
        sorted(path.relative_to(context.corpus_root) for path in context.corpus_root.rglob("*"))
    )
    assert files_after == files_before

    status, _headers, raw_state = _request(
        server,
        "GET",
        "/api/v1/state",
        headers={"Cookie": cookie},
    )
    assert status == 200
    state_text = raw_state.decode()
    assert str(context.corpus_root) not in state_text
    assert server.corpus_token not in state_text
    for forbidden in (
        "fingerprint",
        '"request"',
        '"result"',
        '"hand"',
        '"skat"',
        '"discards"',
        '"commentary_text"',
        '"records"',
        '"actual_card',
        '"decision_reference',
        '"motif_counts"',
        '"guidance',
        '"focus_areas"',
        '"teacher_assessments"',
        '"best_card"',
    ):
        assert forbidden not in state_text.lower()
    state = json.loads(raw_state)
    assert state["prepared"]["strategy_teacher_evidence_count"] == 1
    assert state["prepared"]["tactical_collection_status"] == "complete"
    assert state["prepared"]["tactical_evidence_count"] == 30
    assert state["prepared"]["tactical_skipped_decision_count"] == 0
    assert state["prepared"]["tactical_motif_occurrence_count"] > 0
    assert state["prepared"]["tactical_cross_game_player_count"] == 3
    assert state["prepared"]["tactical_cross_game_recurrence_count"] > 0
    assert state["prepared"]["tactical_coaching_status"] == "insufficient_evidence"
    assert state["prepared"]["tactical_coaching_decision_count"] == 30
    assert state["prepared"]["tactical_coaching_teacher_assessment_count"] == 1
    assert state["prepared"]["tactical_coaching_focus_area_count"] == 0
    assert state["prepared"]["tactical_coaching_player_with_focus_count"] == 0
    assert set(state["strategy_sources"][0]) == {
        "source_binding_id",
        "source_report_id",
        "match_snapshot_id",
        "match_id",
        "match_position",
        "decision_index",
        "recommendation_method",
        "binding_status",
    }

    source_binding_id = context.strategy_source_store.source_binding_ids[0]
    remove = _post_form(
        server,
        cookie,
        {
            "operation": "remove_strategy_teacher_report",
            "source_binding_id": source_binding_id,
        },
    )
    assert remove[0] == 200
    assert context.prepared_artifacts is None
    assert context.tactical_prepared_artifacts is None
    assert context.tactical_coaching_prepared_artifacts is None
    for route in route_by_kind.values():
        assert _request(server, "GET", route, headers={"Cookie": cookie})[0] == 404


def test_selection_non_current_block_reload_and_download_source_mismatch(
    running_server,
) -> None:
    server = running_server
    context = server.corpus_context
    cookie = _bootstrap(server)
    workspace, snapshot, _analysis, report, _source, _store = _source_bundle()
    assert (
        _post_form(
            server,
            cookie,
            {"operation": "initialize_corpus", "corpus_id": "corpus-selection"},
        )[0]
        == 200
    )
    assert (
        _post_upload(
            server,
            cookie,
            {
                "operation": "import_match_workspace",
                "selection_mode": "select_imported",
                "same_revision_resolution": "reject",
                "expected_catalog_revision": 0,
            },
            file_field="workspace_file",
            file_content=_workspace_bytes(workspace),
        )[0]
        == 200
    )
    assert (
        _post_upload(
            server,
            cookie,
            {
                "operation": "import_strategy_teacher_report",
                "match_snapshot_id": snapshot.match_snapshot_id,
            },
            file_field="report_source_file",
            file_content=serialize_match_analysis_report_source_export_v1(
                build_match_analysis_report_source_export_v1(report)
            ),
        )[0]
        == 200
    )

    changed = replace_match_workspace_definition_v1(
        workspace,
        replace(workspace.match_definition, title="Retained later revision"),
        expected_revision=workspace.revision,
    )
    assert changed.status == "applied"
    assert context.store is not None
    revision = context.store.document.catalog.revision
    assert (
        _post_upload(
            server,
            cookie,
            {
                "operation": "import_match_workspace",
                "selection_mode": "keep_current",
                "same_revision_resolution": "reject",
                "expected_catalog_revision": revision,
            },
            file_field="workspace_file",
            file_content=_workspace_bytes(changed.workspace),
        )[0]
        == 200
    )
    assert context.store is not None
    changed_entry = next(
        entry
        for entry in context.store.document.catalog.match_snapshots
        if entry.workspace_revision == changed.workspace.revision
    )
    revision = context.store.document.catalog.revision
    selected = _post_form(
        server,
        cookie,
        {
            "operation": "select_current_snapshot",
            "match_id": changed_entry.match_id,
            "match_snapshot_id": changed_entry.match_snapshot_id,
            "expected_catalog_revision": revision,
        },
    )
    assert selected[0] == 200
    assert b"non_current" in selected[2]
    blocked = _post_form(
        server,
        cookie,
        {
            "operation": "prepare_learning_artifacts",
            "dataset_id": "blocked-dataset",
            "known_player_seed": 0,
            "unseen_player_seed": 0,
            "train_weight": 1,
            "validation_weight": 1,
            "test_weight": 1,
        },
    )
    assert blocked[0] == 400
    assert b"non-current" in blocked[2]

    source_binding_id = context.strategy_source_store.source_binding_ids[0]
    assert (
        _post_form(
            server,
            cookie,
            {
                "operation": "remove_strategy_teacher_report",
                "source_binding_id": source_binding_id,
            },
        )[0]
        == 200
    )
    assert (
        _post_form(
            server,
            cookie,
            {
                "operation": "prepare_learning_artifacts",
                "dataset_id": "current-dataset",
                "known_player_seed": 0,
                "unseen_player_seed": 0,
                "train_weight": 1,
                "validation_weight": 1,
                "test_weight": 1,
            },
        )[0]
        == 200
    )
    assert context.prepared_artifacts is not None
    assert context.tactical_prepared_artifacts is not None
    assert context.tactical_coaching_prepared_artifacts is not None
    context.generation += 1
    assert (
        _request(
            server,
            "GET",
            "/downloads/player-catalog.json",
            headers={"Cookie": cookie},
        )[0]
        == 409
    )
    context.generation -= 1

    reload_result = _post_form(server, cookie, {"operation": "reload_corpus"})
    assert reload_result[0] == 200
    assert b"reloaded" in reload_result[2]
    assert context.prepared_artifacts is None
    assert context.tactical_prepared_artifacts is None
    assert context.tactical_coaching_prepared_artifacts is None


def test_information_set_report_upload_prepares_existing_learning_downloads(
    running_server,
) -> None:
    server = running_server
    context = server.corpus_context
    cookie = _bootstrap(server)
    workspace, snapshot, _analysis, report, _source, _store = _source_bundle(
        recommendation_method="information_set_search",
        decision_index=30,
        match_id="match-corpus-information-set",
        search_random_seed=7,
        search_budget_profile="interactive_v1",
    )
    assert (
        _post_form(
            server,
            cookie,
            {"operation": "initialize_corpus", "corpus_id": "corpus-information-set"},
        )[0]
        == 200
    )
    imported = _post_upload(
        server,
        cookie,
        {
            "operation": "import_match_workspace",
            "selection_mode": "select_imported",
            "same_revision_resolution": "reject",
            "expected_catalog_revision": 0,
        },
        file_field="workspace_file",
        file_content=_workspace_bytes(workspace),
    )
    assert imported[0] == 200
    assert context.strategy_source_store.sources == ()

    report_bytes = serialize_match_analysis_report_source_export_v1(
        build_match_analysis_report_source_export_v1(report)
    )
    uploaded = _post_upload(
        server,
        cookie,
        {
            "operation": "import_strategy_teacher_report",
            "match_snapshot_id": snapshot.match_snapshot_id,
        },
        file_field="report_source_file",
        file_content=report_bytes,
    )
    assert uploaded[0] == 200
    assert b"information_set_search" in uploaded[2]
    assert len(context.strategy_source_store.sources) == 1
    assert context.prepared_artifacts is None
    assert context.tactical_prepared_artifacts is None
    assert context.tactical_coaching_prepared_artifacts is None

    prepared = _post_form(
        server,
        cookie,
        {
            "operation": "prepare_learning_artifacts",
            "dataset_id": "corpus-information-set-dataset",
            "known_player_seed": 0,
            "unseen_player_seed": 0,
            "train_weight": 70,
            "validation_weight": 15,
            "test_weight": 15,
        },
    )
    assert prepared[0] == 200
    assert context.prepared_artifacts is not None
    assert context.tactical_prepared_artifacts is not None
    assert context.tactical_coaching_prepared_artifacts is not None

    for route, markers in (
        (
            "/downloads/strategy-teacher-evidence.json",
            (
                b'"information_set_search_requested_count": 1',
                b'"information_set_search_evidence"',
            ),
        ),
        (
            "/downloads/learning-dataset-v2.json",
            (b'"information_set_search_evidence"',),
        ),
        (
            "/downloads/cross-game-summary.json",
            (
                b'"category": "information_set_search"',
                b'"category": "bounded_information_set_policy_search_v1"',
            ),
        ),
        (
            "/downloads/tactical-cross-game-coaching.json",
            (
                b'"report_method": "learning_corpus_tactical_cross_game_coaching_v1"',
                b'"requested_method": "information_set_search"',
            ),
        ),
    ):
        status, _headers, content = _request(
            server,
            "GET",
            route,
            headers={"Cookie": cookie},
        )
        assert status == 200
        for marker in markers:
            assert marker in content


def test_generic_unexpected_error_exposes_no_exception_or_path(
    running_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = running_server
    cookie = _bootstrap(server)
    private_path = str(server.corpus_context.corpus_root)

    def fail(_context):
        raise RuntimeError(f"secret failure at {private_path}")

    monkeypatch.setattr(server_module, "build_learning_corpus_web_state_v1", fail)
    status, _headers, content = _request(
        server,
        "GET",
        "/api/v1/state",
        headers={"Cookie": cookie},
    )
    assert status == 500
    assert content == b"Internal server error"
    assert private_path.encode() not in content

    status, _headers, content = _post_form(
        server,
        cookie,
        {"operation": "unknown"},
    )
    assert status == 500
    assert content == b"Internal server error"
    assert private_path.encode() not in content
