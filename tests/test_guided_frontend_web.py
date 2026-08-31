from __future__ import annotations

import http.client
import json
import socket
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlencode

import pytest

import skatmind.app_web.server as server_module
import skatmind.app_web.workflow_operations as operations_module
from skatmind.api.v1 import (
    ExecutionOptionsV1,
    ExecutionResultV1,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
)
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.execution import GuidedFrontendExecutionV1
from skatmind.app_web.guided_contracts import (
    ANALYZE_ACTION_ROUTE_PATHS,
    ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESET_ACTION_ROUTE_PATH,
    ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
    ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
    GUIDED_ACTION_ROUTE_PATHS,
    GUIDED_DOWNLOAD_ROUTE_PATHS,
    POSITION_REQUEST_DOWNLOAD_FILENAME,
    POSITION_RESULT_DOWNLOAD_FILENAME,
    REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
    REVIEW_BACK_ACTION_ROUTE_PATH,
    REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_FILENAME,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESET_ACTION_ROUTE_PATH,
    REVIEW_RESULT_DOWNLOAD_FILENAME,
    REVIEW_RESULT_DOWNLOAD_ROUTE_PATH,
    REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
    REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_START_ACTION_ROUTE_PATH,
    REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
)
from skatmind.app_web.historical_form import (
    HistoricalFormDraftV1,
    build_historical_play_view_v1,
    create_historical_form_draft_v1,
)
from skatmind.app_web.json_transfer import (
    FRONTEND_JSON_MAX_FILE_BYTES,
    build_frontend_request_json_bytes_v1,
    build_frontend_result_json_bytes_v1,
)
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.position_form import parse_position_form_v1
from skatmind.app_web.rendering import render_app_page_v1
from skatmind.app_web.security import APP_WEB_COOKIE_NAME
from skatmind.app_web.server import (
    SkatMindAppWebServerV1,
    serve_app_web_in_thread_v1,
    start_app_web_server_v1,
)
from skatmind.errors import SkatMindValidationError

ROOT = Path(__file__).resolve().parents[1]
_TOKEN = "guided-web-test-token"


def _request(
    server: SkatMindAppWebServerV1,
    method: str,
    target: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    connection.request(method, target, body=body, headers=headers or {})
    response = connection.getresponse()
    content = response.read()
    response_headers = {name.lower(): value for name, value in response.getheaders()}
    connection.close()
    return response.status, response_headers, content


def _raw_request(server: SkatMindAppWebServerV1, request: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", server.port), timeout=10) as connection:
        connection.sendall(request)
        connection.shutdown(socket.SHUT_WR)
        response = bytearray()
        while chunk := connection.recv(4096):
            response.extend(chunk)
    return bytes(response)


@pytest.fixture
def guided_server(tmp_path: Path) -> Iterator[SkatMindAppWebServerV1]:
    context = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))
    server = start_app_web_server_v1(context, port=0, token=_TOKEN)
    thread = serve_app_web_in_thread_v1(server)
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def _bootstrap(server: SkatMindAppWebServerV1) -> tuple[str, dict[str, str]]:
    status, headers, body = _request(server, "GET", f"/?token={_TOKEN}")
    assert status == 303 and body == b""
    cookie = headers["set-cookie"].split(";", 1)[0]
    assert cookie == f"{APP_WEB_COOKIE_NAME}={_TOKEN}"
    return cookie, {"Cookie": cookie, "Origin": server.origin}


def _post_form(
    server: SkatMindAppWebServerV1,
    route: str,
    headers: dict[str, str],
    values: dict[str, object],
) -> tuple[int, dict[str, str], bytes]:
    body = urlencode(values, doseq=True).encode("ascii")
    return _request(
        server,
        "POST",
        route,
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )


def _position_values(revision: int) -> dict[str, object]:
    return {
        "revision": str(revision),
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "declarer_player": "me",
        "trick_leader": "me",
        "hand": ["CJ", "CA", "C10", "CK", "CQ", "C9", "C8", "C7", "SA", "S10"],
    }


def _example(name: str) -> dict[str, object]:
    value = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _multipart(content: bytes, *, revision: int) -> tuple[bytes, str]:
    boundary = "skatmind-guided-web-boundary"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="revision"\r\n\r\n'
        f"{revision}\r\n"
        f'--{boundary}\r\nContent-Disposition: form-data; name="request_file"; '
        'filename="ignored.json"\r\nContent-Type: application/json\r\n\r\n'
    ).encode("ascii") + content + f"\r\n--{boundary}--\r\n".encode("ascii")
    return body, f"multipart/form-data; boundary={boundary}"


def _fake_execution(
    request: RequestDocumentV1,
    *,
    options: ExecutionOptionsV1,
) -> GuidedFrontendExecutionV1:
    if request.workflow is WorkflowV1.POSITION_ANALYSIS:
        document = {
            "position": {},
            "game_declaration": {},
            "information_policy_summary": {},
            "settings": {},
            "recommendation": {"reason": "Retained test recommendation."},
        }
    else:
        document = {"historical_game_summary": {"status": "complete"}}
    result = ExecutionResultV1(
        result=ResultDocumentV1(
            workflow=request.workflow,
            document=document,
            warnings=("Retained test warning.",),
        )
    )
    return GuidedFrontendExecutionV1(
        request=request,
        options=options,
        result=result,
        request_json_bytes=build_frontend_request_json_bytes_v1(request),
        result_json_bytes=build_frontend_result_json_bytes_v1(result),
    )


def _assert_redirect(response: tuple[int, dict[str, str], bytes], location: str) -> None:
    status, headers, body = response
    assert status == 303
    assert headers["location"] == location
    assert body == b""


def test_analyze_guided_import_run_reset_and_exact_download_routes(
    guided_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = guided_server
    cookie, mutation_headers = _bootstrap(server)
    calls: list[tuple[RequestDocumentV1, ExecutionOptionsV1]] = []

    def execute(
        request: RequestDocumentV1,
        *,
        options: ExecutionOptionsV1,
    ) -> GuidedFrontendExecutionV1:
        calls.append((request, options))
        return _fake_execution(request, options=options)

    monkeypatch.setattr(operations_module, "execute_guided_frontend_analysis_v1", execute)
    before = tuple(server.app_context.managed_home.root.rglob("*"))

    _assert_redirect(
        _post_form(
            server,
            ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
            mutation_headers,
            _position_values(0),
        ),
        "/analyze",
    )
    assert len(calls) == 1
    status, _headers, _body = _post_form(
        server,
        ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        mutation_headers,
        _position_values(0),
    )
    assert status == 409
    assert len(calls) == 1

    with server.app_context.lock:
        request_bytes = server.app_context.analyze_state.request_json_bytes
        result_bytes = server.app_context.analyze_state.result_json_bytes
        revision = server.app_context.analyze_state.revision
    assert request_bytes is not None and result_bytes is not None
    for route, filename, expected in (
        (ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH, POSITION_REQUEST_DOWNLOAD_FILENAME, request_bytes),
        (ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH, POSITION_RESULT_DOWNLOAD_FILENAME, result_bytes),
    ):
        status, headers, body = _request(server, "GET", route, headers={"Cookie": cookie})
        assert status == 200
        assert headers["content-type"] == "application/json; charset=utf-8"
        assert headers["content-disposition"] == f'attachment; filename="{filename}"'
        assert body == expected
    assert len(calls) == 1

    imported_json = json.dumps(_example("grand_second_position.json")).encode("utf-8")
    multipart, content_type = _multipart(imported_json, revision=revision)
    _assert_redirect(
        _request(
            server,
            "POST",
            ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
            headers={**mutation_headers, "Content-Type": content_type},
            body=multipart,
        ),
        "/analyze",
    )
    assert len(calls) == 1
    with server.app_context.lock:
        imported_revision = server.app_context.analyze_state.revision
        assert server.app_context.analyze_state.imported_request is not None
        assert server.app_context.analyze_state.latest_successful_result is None
        imported_request_bytes = server.app_context.analyze_state.request_json_bytes
    status, _headers, imported_page = _request(
        server,
        "GET",
        "/analyze",
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH.encode() in imported_page
    status, _headers, downloaded_request = _request(
        server,
        "GET",
        ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
        headers={"Cookie": cookie},
    )
    assert status == 200 and downloaded_request == imported_request_bytes
    assert len(calls) == 1

    _assert_redirect(
        _post_form(
            server,
            ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": imported_revision},
        ),
        "/analyze",
    )
    assert len(calls) == 2
    status, _headers, completed_page = _request(
        server,
        "GET",
        "/analyze",
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert b"This imported Request produced the Result shown above." in completed_page
    assert b"Run imported Request again" in completed_page
    status, _headers, _body = _post_form(
        server,
        ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
        mutation_headers,
        {"revision": imported_revision},
    )
    assert status == 409
    assert len(calls) == 2
    with server.app_context.lock:
        completed_revision = server.app_context.analyze_state.revision
    _assert_redirect(
        _post_form(
            server,
            ANALYZE_RESET_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": completed_revision, "confirm_reset": "on"},
        ),
        "/analyze",
    )
    with server.app_context.lock:
        assert server.app_context.analyze_state.latest_successful_result is None
        assert server.app_context.analyze_state.imported_request is None
    assert tuple(server.app_context.managed_home.root.rglob("*")) == before


def test_review_all_guided_actions_run_download_and_reset(
    guided_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = guided_server
    cookie, mutation_headers = _bootstrap(server)
    calls: list[tuple[RequestDocumentV1, ExecutionOptionsV1]] = []

    def execute(
        request: RequestDocumentV1,
        *,
        options: ExecutionOptionsV1,
    ) -> GuidedFrontendExecutionV1:
        calls.append((request, options))
        return _fake_execution(request, options=options)

    monkeypatch.setattr(operations_module, "execute_guided_frontend_review_v1", execute)
    _assert_redirect(
        _post_form(
            server,
            REVIEW_START_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 0},
        ),
        "/review",
    )
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
            mutation_headers,
            {
                "revision": 1,
                "forehand_label": "{{<Forehand>}}",
                "middlehand_label": "{{CONTENT}}",
                "rearhand_label": "Rearhand",
            },
        ),
        "/review",
    )
    _assert_redirect(
        _post_form(
            server,
            REVIEW_BACK_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 2},
        ),
        "/review",
    )
    status, _headers, body = _request(server, "GET", "/review", headers={"Cookie": cookie})
    assert status == 200
    assert b"{{&lt;Forehand&gt;}}" in body and b"<Forehand>" not in body
    assert b"{{CONTENT}}" in body
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
            mutation_headers,
            {
                "revision": 3,
                "forehand_label": "{{<Forehand>}}",
                "middlehand_label": "{{CONTENT}}",
                "rearhand_label": "Rearhand",
            },
        ),
        "/review",
    )

    from skatmind.deck import get_full_deck

    deck = tuple(get_full_deck())
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
            mutation_headers,
            {
                "revision": 4,
                "forehand_hand": deck[:10],
                "middlehand_hand": deck[10:20],
                "rearhand_hand": deck[20:30],
                "skat": deck[30:],
            },
        ),
        "/review",
    )
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
            mutation_headers,
            {
                "revision": 5,
                "declarer_player_id": "frontend-forehand",
                "game_type": "grand",
                "bid_value": "18",
            },
        ),
        "/review",
    )
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 6, "discarded_cards": deck[30:]},
        ),
        "/review",
    )

    with server.app_context.lock:
        draft = server.app_context.review_state.draft
    assert type(draft) is HistoricalFormDraftV1
    first_card = build_historical_play_view_v1(draft).legal_cards[0]
    _assert_redirect(
        _post_form(
            server,
            REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 7, "card": first_card},
        ),
        "/review",
    )
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 8},
        ),
        "/review",
    )

    for _index in range(30):
        with server.app_context.lock:
            revision = server.app_context.review_state.revision
            draft = server.app_context.review_state.draft
        assert type(draft) is HistoricalFormDraftV1
        card = build_historical_play_view_v1(draft).legal_cards[0]
        _assert_redirect(
            _post_form(
                server,
                REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
                mutation_headers,
                {"revision": revision, "card": card},
            ),
            "/review",
        )

    with server.app_context.lock:
        options_revision = server.app_context.review_state.revision
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
            mutation_headers,
            {
                "revision": options_revision,
                "decision_snapshots": "on",
                "include_provenance": "on",
            },
        ),
        "/review",
    )
    run_revision = options_revision + 1
    _assert_redirect(
        _post_form(
            server,
            REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": run_revision},
        ),
        "/review",
    )
    assert len(calls) == 1
    assert calls[0][1].include_provenance is True

    with server.app_context.lock:
        request_bytes = server.app_context.review_state.request_json_bytes
        result_bytes = server.app_context.review_state.result_json_bytes
        completed_revision = server.app_context.review_state.revision
    for route, filename, expected in (
        (REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH, REVIEW_REQUEST_DOWNLOAD_FILENAME, request_bytes),
        (REVIEW_RESULT_DOWNLOAD_ROUTE_PATH, REVIEW_RESULT_DOWNLOAD_FILENAME, result_bytes),
    ):
        status, headers, body = _request(server, "GET", route, headers={"Cookie": cookie})
        assert status == 200 and body == expected
        assert headers["content-disposition"] == f'attachment; filename="{filename}"'
    assert len(calls) == 1

    status, _headers, _body = _post_form(
        server,
        REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
        mutation_headers,
        {"revision": run_revision},
    )
    assert status == 409
    assert len(calls) == 1

    def fail_request_build(_draft: HistoricalFormDraftV1) -> RequestDocumentV1:
        raise RuntimeError("private request construction failure")

    monkeypatch.setattr(operations_module, "build_historical_request_v1", fail_request_build)
    status, _headers, body = _post_form(
        server,
        REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
        mutation_headers,
        {"revision": completed_revision},
    )
    assert status == 500
    assert body == b"Internal server error"
    assert b"private request construction failure" not in body
    with server.app_context.lock:
        failed_state = server.app_context.review_state
    assert failed_state.execution_source_revision is None
    assert failed_state.latest_successful_result is None

    _assert_redirect(
        _post_form(
            server,
            REVIEW_RESET_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": completed_revision, "confirm_reset": "on"},
        ),
        "/review",
    )


def test_invalid_review_deal_retains_safe_submitted_cards(
    guided_server: SkatMindAppWebServerV1,
) -> None:
    server = guided_server
    _cookie, mutation_headers = _bootstrap(server)
    _assert_redirect(
        _post_form(
            server,
            REVIEW_START_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 0},
        ),
        "/review",
    )
    _assert_redirect(
        _post_form(
            server,
            REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 1},
        ),
        "/review",
    )

    from skatmind.deck import get_full_deck

    deck = tuple(get_full_deck())
    status, _headers, body = _post_form(
        server,
        REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
        mutation_headers,
        {
            "revision": 2,
            "forehand_hand": deck[:9],
            "middlehand_hand": deck[10:20],
            "rearhand_hand": deck[20:30],
            "skat": deck[30:],
        },
    )
    assert status == 400
    assert b"must contain exactly 10 cards" in body
    with server.app_context.lock:
        state = server.app_context.review_state
    assert state.revision == 3
    assert type(state.draft) is HistoricalFormDraftV1
    assert state.draft.players[0].initial_hand == deck[:9]
    assert state.latest_successful_result is None


def test_review_import_and_separate_run_are_non_executing_then_exactly_once(
    guided_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = guided_server
    _cookie, mutation_headers = _bootstrap(server)
    calls = 0

    def execute(
        request: RequestDocumentV1,
        *,
        options: ExecutionOptionsV1,
    ) -> GuidedFrontendExecutionV1:
        nonlocal calls
        calls += 1
        return _fake_execution(request, options=options)

    monkeypatch.setattr(operations_module, "execute_guided_frontend_review_v1", execute)
    content = json.dumps(_example("historical_grand_normal_completion.json")).encode()
    body, content_type = _multipart(content, revision=0)
    _assert_redirect(
        _request(
            server,
            "POST",
            REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
            headers={**mutation_headers, "Content-Type": content_type},
            body=body,
        ),
        "/review",
    )
    assert calls == 0
    _assert_redirect(
        _post_form(
            server,
            REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
            mutation_headers,
            {"revision": 1},
        ),
        "/review",
    )
    assert calls == 1


def test_route_methods_authentication_missing_downloads_and_status_mapping(
    guided_server: SkatMindAppWebServerV1,
) -> None:
    server = guided_server
    cookie, mutation_headers = _bootstrap(server)
    for route in GUIDED_ACTION_ROUTE_PATHS:
        status, headers, _body = _request(server, "GET", route, headers={"Cookie": cookie})
        assert status == 405 and headers["allow"] == "POST"
        status, _headers, _body = _post_form(
            server,
            route,
            {"Cookie": cookie},
            {"revision": 0},
        )
        assert status == 403

    for route in GUIDED_DOWNLOAD_ROUTE_PATHS:
        status, _headers, _body = _request(server, "GET", route, headers={"Cookie": cookie})
        assert status == 404
        status, headers, _body = _post_form(server, route, mutation_headers, {})
        assert status == 405 and headers["allow"] == "GET"

    status, _headers, _body = _post_form(
        server,
        ANALYZE_RESET_ACTION_ROUTE_PATH,
        mutation_headers,
        {"revision": 9, "confirm_reset": "on"},
    )
    assert status == 409
    status, _headers, _body = _request(
        server,
        "POST",
        ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        headers={**mutation_headers, "Content-Type": "application/json"},
        body=b"{}",
    )
    assert status == 415


def test_malformed_targets_and_protocol_errors_keep_hardened_headers(
    guided_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = guided_server
    cookie, _mutation_headers = _bootstrap(server)
    host = f"127.0.0.1:{server.port}"

    malformed_target = _raw_request(
        server,
        f"GET http://[ HTTP/1.1\r\nHost: {host}\r\nCookie: {cookie}\r\n\r\n".encode(
            "ascii"
        ),
    )
    assert malformed_target.startswith(b"HTTP/1.0 400")
    assert b"Cache-Control: no-store\r\n" in malformed_target
    assert b"Content-Security-Policy:" in malformed_target

    invalid_protocol = _raw_request(
        server,
        f"GET / HTTP/9.9\r\nHost: {host}\r\n\r\n".encode("ascii"),
    )
    assert invalid_protocol.startswith(b"HTTP/1.0 505")
    assert b"Cache-Control: no-store\r\n" in invalid_protocol
    assert b"Content-Security-Policy:" in invalid_protocol

    http_09 = _raw_request(server, b"GET /\r\n")
    assert http_09.startswith(b"HTTP/1.0 505")
    assert b"Cache-Control: no-store\r\n" in http_09
    assert b"Content-Security-Policy:" in http_09

    def fail_render(*_args: object, **_kwargs: object) -> str:
        raise ValueError("private rendering invariant")

    monkeypatch.setattr(server_module, "render_app_page_v1", fail_render)
    status, _headers, body = _request(
        server,
        "GET",
        "/",
        headers={"Cookie": cookie},
    )
    assert status == 500
    assert body == b"Internal server error"


def test_validation_is_field_local_accessible_and_advanced_groups_are_exact(
    guided_server: SkatMindAppWebServerV1,
) -> None:
    server = guided_server
    cookie, mutation_headers = _bootstrap(server)
    invalid = _position_values(0)
    invalid["game_type"] = "invalid"
    status, _headers, body = _post_form(
        server,
        ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        mutation_headers,
        invalid,
    )
    assert status == 400
    html = body.decode()
    assert '<a href="#field-game_type">' in html
    assert 'id="field-game_type" aria-invalid="true"' in html
    assert 'aria-describedby="error-game_type-1"' in html
    assert 'id="error-game_type-1"' in html
    assert html.index('id="field-game_type"') < html.index('id="error-game_type-1"')

    status, _headers, analyze_body = _request(
        server,
        "GET",
        "/analyze",
        headers={"Cookie": cookie},
    )
    assert status == 200
    analyze_html = analyze_body.decode()
    assert 'name="completed_trick_1_leader"' in analyze_html
    assert 'name="completed_trick_1_card_1"' in analyze_html
    assert 'name="completed_tricks"' not in analyze_html
    review_state = server.app_context.review_state.mutate(
        expected_revision=0,
        draft=replace(create_historical_form_draft_v1(), step=6),
    )
    review_html = render_app_page_v1(
        server.app_context.browser_state,
        "/review",
        review_state=review_state,
    )
    groups = (
        "Analysis method",
        "Runtime and reproducibility",
        "Opponent behavior",
        "Simulation and comparison",
        "Technical evidence",
        "Dataset and evaluation",
    )
    for page_html in (analyze_html, review_html):
        for group in groups:
            assert page_html.count(f"<summary>{group}</summary>") == 1
        assert "<details open" not in page_html
        assert "<script" not in page_html


def test_exact_one_mebibyte_upload_reaches_file_validation_and_oversize_is_413(
    guided_server: SkatMindAppWebServerV1,
) -> None:
    server = guided_server
    _cookie, mutation_headers = _bootstrap(server)
    encoded = json.dumps(_example("grand_second_position.json")).encode()
    exact = encoded + b" " * (FRONTEND_JSON_MAX_FILE_BYTES - len(encoded))
    body, content_type = _multipart(exact, revision=0)
    _assert_redirect(
        _request(
            server,
            "POST",
            ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
            headers={**mutation_headers, "Content-Type": content_type},
            body=body,
        ),
        "/analyze",
    )
    oversized, oversized_type = _multipart(exact + b" ", revision=1)
    status, _headers, _body = _request(
        server,
        "POST",
        ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
        headers={**mutation_headers, "Content-Type": oversized_type},
        body=oversized,
    )
    assert status == 413


def test_import_rejects_an_incompatible_workflow_with_a_safe_distinct_error(
    guided_server: SkatMindAppWebServerV1,
) -> None:
    server = guided_server
    _cookie, mutation_headers = _bootstrap(server)
    historical = json.dumps(_example("historical_grand_normal_completion.json")).encode()
    body, content_type = _multipart(historical, revision=0)

    status, _headers, response_body = _request(
        server,
        "POST",
        ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
        headers={**mutation_headers, "Content-Type": content_type},
        body=body,
    )

    assert status == 400
    html = response_body.decode()
    assert "Unsupported workflow" in html
    assert "historical_grand_normal_completion" not in html
    assert str(server.app_context.managed_home.root) not in html

    valid = json.dumps(_example("grand_second_position.json")).encode()
    leading_zero_body, leading_zero_type = _multipart(valid, revision=1)
    leading_zero_body = leading_zero_body.replace(
        b'name="revision"\r\n\r\n1\r\n',
        b'name="revision"\r\n\r\n01\r\n',
        1,
    )
    status, _headers, _body = _request(
        server,
        "POST",
        ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
        headers={**mutation_headers, "Content-Type": leading_zero_type},
        body=leading_zero_body,
    )
    assert status == 400


def test_duplicate_run_is_409_and_unexpected_execution_failure_is_generic_500(
    guided_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = guided_server
    _cookie, mutation_headers = _bootstrap(server)
    values = _position_values(0)
    parse_values = {
        key: value if isinstance(value, list) else [str(value)]
        for key, value in values.items()
        if key != "revision"
    }
    draft = parse_position_form_v1(parse_values)
    with server.app_context.lock:
        server.app_context.analyze_state = (
            server.app_context.analyze_state.mutate(expected_revision=0, draft=draft).begin(
                expected_revision=1
            )
        )
    duplicate = _position_values(1)
    status, _headers, _body = _post_form(
        server,
        ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        mutation_headers,
        duplicate,
    )
    assert status == 409

    with server.app_context.lock:
        server.app_context.analyze_state = server.app_context.analyze_state.reset(
            expected_revision=1
        )

    def fail(
        _request_value: RequestDocumentV1,
        *,
        options: ExecutionOptionsV1,
    ) -> GuidedFrontendExecutionV1:
        assert options.validate_output is True
        raise RuntimeError(f"private path {server.app_context.managed_home.root}")

    monkeypatch.setattr(operations_module, "execute_guided_frontend_analysis_v1", fail)
    status, headers, body = _post_form(
        server,
        ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        mutation_headers,
        _position_values(2),
    )
    assert status == 500
    assert body == b"Internal server error"
    assert str(server.app_context.managed_home.root).encode() not in body
    assert headers["cache-control"] == "no-store"
    with server.app_context.lock:
        assert server.app_context.analyze_state.execution_source_revision is None
        assert server.app_context.analyze_state.latest_successful_result is None


def test_public_execution_validation_is_400_and_retains_safe_field_message(
    guided_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = guided_server
    _cookie, mutation_headers = _bootstrap(server)

    def reject(
        _request_value: RequestDocumentV1,
        *,
        options: ExecutionOptionsV1,
    ) -> GuidedFrontendExecutionV1:
        assert options.validate_output is True
        raise SkatMindValidationError("The submitted hand is invalid.", path="/hand")

    monkeypatch.setattr(operations_module, "execute_guided_frontend_analysis_v1", reject)
    status, _headers, body = _post_form(
        server,
        ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        mutation_headers,
        _position_values(0),
    )
    assert status == 400
    html = body.decode()
    assert "The submitted hand is invalid." in html
    assert 'id="field-hand" aria-invalid="true"' in html
    assert 'aria-describedby="error-hand-1"' in html


def test_action_and_download_route_sets_are_fully_exercised() -> None:
    assert set(ANALYZE_ACTION_ROUTE_PATHS) == {
        ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
        ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
        ANALYZE_RESET_ACTION_ROUTE_PATH,
    }
    assert set(GUIDED_ACTION_ROUTE_PATHS) == {
        *ANALYZE_ACTION_ROUTE_PATHS,
        REVIEW_START_ACTION_ROUTE_PATH,
        REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
        REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
        REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
        REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
        REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
        REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH,
        REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
        REVIEW_BACK_ACTION_ROUTE_PATH,
        REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
        REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
        REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
        REVIEW_RESET_ACTION_ROUTE_PATH,
    }
    assert set(GUIDED_DOWNLOAD_ROUTE_PATHS) == {
        ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
        ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
        REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
        REVIEW_RESULT_DOWNLOAD_ROUTE_PATH,
    }
