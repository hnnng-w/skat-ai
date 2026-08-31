from __future__ import annotations

import hmac
import http.client
import json
import socket
from collections.abc import Iterator
from html import escape
from pathlib import Path
from urllib.parse import urlencode

import pytest
from test_local_match_capture_web import _creation_values

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.contracts import APP_NAVIGATION_LABELS, APP_ROUTE_PATHS
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.security import (
    APP_WEB_CONTENT_SECURITY_POLICY,
    APP_WEB_COOKIE_NAME,
    APP_WEB_PERMISSIONS_POLICY,
    has_valid_app_web_cookie_v1,
)
from skatmind.app_web.server import (
    APP_WEB_MAX_REQUEST_BYTES,
    SkatMindAppWebServerV1,
    serve_app_web_in_thread_v1,
    start_app_web_server_v1,
)
from skatmind.capture_web.security import has_valid_match_capture_web_cookie_v1
from skatmind.corpus_web.security import has_valid_learning_corpus_web_cookie_v1

_TOKEN = "app-test-token"


def _request(
    server: SkatMindAppWebServerV1,
    method: str,
    target: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    connection.request(method, target, body=body, headers=headers or {})
    response = connection.getresponse()
    content = response.read()
    response_headers = {name.lower(): value for name, value in response.getheaders()}
    connection.close()
    return response.status, response_headers, content


def _raw_request(
    server: SkatMindAppWebServerV1,
    method: str,
    target: str,
    headers: tuple[tuple[str, str], ...],
    *,
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    connection.putrequest(method, target, skip_host=True)
    for name, value in headers:
        connection.putheader(name, value)
    connection.endheaders(body)
    response = connection.getresponse()
    content = response.read()
    response_headers = {name.lower(): value for name, value in response.getheaders()}
    connection.close()
    return response.status, response_headers, content


@pytest.fixture
def running_app_server(tmp_path: Path) -> Iterator[SkatMindAppWebServerV1]:
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
    assert status == 303
    assert headers["location"] == "/"
    assert body == b""
    set_cookie = headers["set-cookie"]
    assert set_cookie == (
        f"{APP_WEB_COOKIE_NAME}={_TOKEN}; HttpOnly; SameSite=Strict; Path=/"
    )
    cookie = set_cookie.split(";", 1)[0]
    return cookie, {
        "Cookie": cookie,
        "Origin": server.origin,
    }


def test_server_identity_factory_loopback_and_random_bootstrap(tmp_path: Path) -> None:
    context = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))
    first = start_app_web_server_v1(context, port=0)
    second = start_app_web_server_v1(context, port=0)
    try:
        assert type(first) is SkatMindAppWebServerV1
        assert first.server_address[0] == "127.0.0.1"
        assert first.port > 0 and second.port > 0
        assert first.app_token != second.app_token
        assert first.bootstrap_url.startswith(f"http://127.0.0.1:{first.port}/?token=")
        assert first.origin == f"http://127.0.0.1:{first.port}"
    finally:
        first.server_close()
        second.server_close()


def test_bootstrap_requires_exact_sole_token_and_redirects_cleanly(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    for target in (
        "/",
        "/?token=wrong",
        f"/?token={_TOKEN}&extra=1",
        f"/?token={_TOKEN}&token={_TOKEN}",
        f"/about?token={_TOKEN}",
    ):
        status, headers, _body = _request(server, "GET", target)
        assert status == 403
        assert "set-cookie" not in headers

    cookie, _mutation_headers = _bootstrap(server)
    status, headers, body = _request(server, "GET", "/", headers={"Cookie": cookie})
    assert status == 200
    assert "set-cookie" not in headers
    assert _TOKEN.encode() not in body


def test_bootstrap_token_uses_constant_time_comparison(
    monkeypatch: pytest.MonkeyPatch,
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    comparisons: list[tuple[str, str]] = []
    original_compare_digest = hmac.compare_digest

    def compare_digest(left: str, right: str) -> bool:
        comparisons.append((left, right))
        return original_compare_digest(left, right)

    monkeypatch.setattr("skatmind.app_web.server.hmac.compare_digest", compare_digest)
    status, _headers, _body = _request(
        running_app_server,
        "GET",
        "/?token=wrong",
    )
    assert status == 403
    assert comparisons == [("wrong", _TOKEN)]


def test_cookie_token_uses_constant_time_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comparisons: list[tuple[str, str]] = []
    original_compare_digest = hmac.compare_digest

    def compare_digest(left: str, right: str) -> bool:
        comparisons.append((left, right))
        return original_compare_digest(left, right)

    monkeypatch.setattr("skatmind.app_web.security.hmac.compare_digest", compare_digest)
    assert has_valid_app_web_cookie_v1(
        f"{APP_WEB_COOKIE_NAME}={_TOKEN}",
        _TOKEN,
    )
    assert comparisons == [(_TOKEN, _TOKEN)]


def test_app_cookie_is_isolated_from_capture_and_corpus(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    for unrelated_cookie in (
        f"skatmind_capture_token={_TOKEN}",
        f"skatmind_corpus_token={_TOKEN}",
    ):
        status, _headers, _body = _request(
            server,
            "GET",
            "/",
            headers={"Cookie": unrelated_cookie},
        )
        assert status == 403

    app_cookie = f"{APP_WEB_COOKIE_NAME}={_TOKEN}"
    assert has_valid_app_web_cookie_v1(app_cookie, _TOKEN)
    assert not has_valid_match_capture_web_cookie_v1(app_cookie, _TOKEN)
    assert not has_valid_learning_corpus_web_cookie_v1(app_cookie, _TOKEN)
    assert not has_valid_app_web_cookie_v1(
        f"{app_cookie}; {APP_WEB_COOKIE_NAME}={_TOKEN}",
        _TOKEN,
    )


def test_all_authenticated_routes_render_shared_navigation_and_one_h1(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    for route, current_label in zip(APP_ROUTE_PATHS, APP_NAVIGATION_LABELS, strict=True):
        status, headers, body = _request(server, "GET", route, headers={"Cookie": cookie})
        assert status == 200
        assert headers["content-type"] == "text/html; charset=utf-8"
        html = body.decode("utf-8")
        assert html.count("<h1>") == 1
        assert '<a class="skip-link" href="#main-content">Skip to main content</a>' in html
        assert "<header" in html and "<nav" in html and "<main" in html and "<footer" in html
        assert f'>{escape(current_label)}</a>' in html
        assert html.count('aria-current="page"') == 1
        positions = [
            html.index(f">{escape(label)}</a>") for label in APP_NAVIGATION_LABELS
        ]
        assert positions == sorted(positions)
        assert "<script" not in html
        assert "http://" not in html and "https://" not in html


def test_home_has_exact_tasks_local_no_cloud_copy_and_honest_status(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    status, _headers, body = _request(server, "GET", "/", headers={"Cookie": cookie})
    assert status == 200
    html = body.decode("utf-8")
    assert "SkatMind runs locally on this computer" in html
    assert "stores no data in the cloud" in html
    assert html.count('<article class="task-card">') == 6
    assert html.count("Available now.") == 6
    assert "not yet available" not in html
    assert "Issue #" not in html
    for heading in ("What you need", "Mode", "Stored", "Result"):
        assert html.count(f"<dt>{heading}</dt>") == 6
    for forbidden in (
        "type=\"file\"",
        "seed",
        "samples",
        "Search settings",
        "Dataset settings",
        "Provenance settings",
    ):
        assert forbidden not in html


def test_guided_and_managed_stateful_pages_are_available(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    for route in ("/analyze", "/review"):
        status, _headers, body = _request(server, "GET", route, headers={"Cookie": cookie})
        assert status == 200
        html = body.decode("utf-8")
        assert "Process-local only" in html
        assert "<form" in html
        assert "Not yet available" not in html
        assert "Issue #" not in html

    expected_stateful_text = {
        "/sessions": "Create a Session",
        "/matches": "Create a Match",
        "/learning": "Create a Learning Corpus",
    }
    for route, expected in expected_stateful_text.items():
        status, _headers, body = _request(server, "GET", route, headers={"Cookie": cookie})
        assert status == 200
        html = body.decode("utf-8")
        assert expected in html
        assert "Not yet available" not in html
        assert "Issue #" not in html


def _post_form(
    server: SkatMindAppWebServerV1,
    target: str,
    mutation_headers: dict[str, str],
    values: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    body = urlencode(values).encode("ascii")
    return _request(
        server,
        "POST",
        target,
        headers={
            **mutation_headers,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body=body,
    )


def test_managed_session_http_lifecycle_command_and_download(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, mutation_headers = _bootstrap(server)
    status, headers, _body = _post_form(
        server,
        "/sessions/create",
        mutation_headers,
        {
            "session_id": "web-session",
            "capture_mode": "retrospective",
            "local_player_id": "",
            "player_1_id": "alice",
            "player_1_label": "Alice",
            "player_2_id": "bob",
            "player_2_label": "Bob",
            "player_3_id": "carol",
            "player_3_label": "Carol",
        },
    )
    assert status == 303 and headers["location"] == "/sessions/current"
    active_session = server.app_context.managed_stateful.active_session
    assert active_session is not None

    status, headers, _body = _post_form(
        server,
        "/sessions/command",
        mutation_headers,
        {
            "managed_handle": active_session.handle,
            "expected_revision": "0",
            "target_revision": "",
            "kind": "set_game_metadata",
            "game_id": "web-game",
            "played_at": "",
        },
    )
    assert status == 303 and headers["location"] == "/sessions/current"
    status, _headers, body = _request(
        server,
        "GET",
        "/sessions/current",
        headers={"Cookie": cookie},
    )
    html = body.decode("utf-8")
    assert status == 200
    assert "web-session" in html and "web-game" in html
    assert html.count('action="/sessions/command"') == 10

    status, headers, body = _request(
        server,
        "GET",
        "/sessions/downloads/session.json",
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert headers["content-disposition"].endswith('"skatmind-managed-session.json"')
    assert json.loads(body)["state"]["revision"] == 1


def test_managed_session_form_is_rejected_after_active_item_switch(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    _cookie, mutation_headers = _bootstrap(server)
    create_values = {
        "capture_mode": "retrospective",
        "local_player_id": "",
        "player_1_id": "alice",
        "player_1_label": "Alice",
        "player_2_id": "bob",
        "player_2_label": "Bob",
        "player_3_id": "carol",
        "player_3_label": "Carol",
    }
    status, _headers, _body = _post_form(
        server,
        "/sessions/create",
        mutation_headers,
        {**create_values, "session_id": "first-session"},
    )
    assert status == 303
    first = server.app_context.managed_stateful.active_session
    assert first is not None
    status, _headers, _body = _post_form(
        server,
        "/sessions/create",
        mutation_headers,
        {**create_values, "session_id": "second-session"},
    )
    assert status == 303
    second = server.app_context.managed_stateful.active_session
    assert second is not None and second.handle != first.handle

    status, _headers, body = _post_form(
        server,
        "/sessions/command",
        mutation_headers,
        {
            "managed_handle": first.handle,
            "expected_revision": "0",
            "target_revision": "",
            "kind": "set_game_metadata",
            "game_id": "must-not-apply",
            "played_at": "",
        },
    )
    assert status == 409
    assert b"This form is stale" in body
    assert second.state.revision == 0


def test_managed_match_learning_and_explicit_transfer_http_lifecycle(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, mutation_headers = _bootstrap(server)
    status, headers, _body = _post_form(
        server,
        "/learning/create",
        mutation_headers,
        {"corpus_id": "web-corpus"},
    )
    assert status == 303 and headers["location"] == "/learning/current"
    learning = server.app_context.managed_stateful.active_learning
    assert learning is not None

    status, headers, _body = _post_form(
        server,
        "/matches/api/v1/create",
        mutation_headers,
        _creation_values(match_id="web-match"),
    )
    assert status == 303 and headers["location"] == "/matches/position/1"
    match = server.app_context.managed_stateful.active_match
    assert match is not None
    status, _headers, body = _request(
        server,
        "GET",
        "/matches/position/1",
        headers={"Cookie": cookie},
    )
    html = body.decode("utf-8")
    assert status == 200
    assert html.count("<h1>") == 1
    assert '<div id="capture-app">' in html
    assert 'action="/matches/api/v1/operation"' in html
    assert 'action="/matches/transfer-workspace"' in html
    assert f'name="managed_handle" value="{match.handle}"' in html
    assert f'name="target_managed_handle" value="{learning.handle}"' in html
    assert "/matches/assets/capture.js" in html

    status, headers, _body = _post_form(
        server,
        "/matches/transfer-workspace",
        mutation_headers,
        {
            "managed_handle": match.handle,
            "target_managed_handle": learning.handle,
            "expected_catalog_revision": "0",
            "selection_mode": "select_imported",
            "same_revision_resolution": "reject",
        },
    )
    assert status == 303 and headers["location"] == "/matches/position/1"
    status, _headers, transfer_body = _request(
        server,
        "GET",
        headers["location"],
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert b"import" in transfer_body.lower()
    assert b'name="expected_catalog_revision" value="1"' in transfer_body
    status, _headers, body = _request(
        server,
        "GET",
        "/learning/api/v1/state",
        headers={"Cookie": cookie},
    )
    state = json.loads(body)
    assert status == 200
    assert state["corpus"]["logical_match_count"] == 1
    assert state["current_match_snapshots"][0]["match_id"] == "web-match"

    status, _headers, body = _post_form(
        server,
        "/matches/transfer-workspace",
        mutation_headers,
        {
            "managed_handle": match.handle,
            "target_managed_handle": learning.handle,
            "expected_catalog_revision": "0",
            "selection_mode": "select_imported",
            "same_revision_resolution": "reject",
        },
    )
    assert status == 409
    assert b"revision" in body.lower()
    assert b'name="expected_catalog_revision" value="1"' in body

    status, headers, body = _request(
        server,
        "GET",
        "/matches/downloads/workspace.json",
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert headers["content-disposition"].endswith('"skatmind-managed-match.json"')
    assert json.loads(body)["workspace"]["match_definition"]["match_id"] == "web-match"


def test_about_identity_runtime_local_boundaries_and_closed_storage_disclosure(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    status, _headers, body = _request(server, "GET", "/about", headers={"Cookie": cookie})
    assert status == 200
    html = body.decode("utf-8")
    for value in (
        "SkatMind",
        "Package 0.17.0",
        "AGPL-3.0-only",
        "Copyright (C) 2026 Henning Wiese",
        "Current Python runtime",
        "Python &gt;=3.13",
        "CPython 3.13",
        "no cloud or remote service",
        "advanced command-line interfaces",
        "Public Python API contract version 1",
        "README.md",
        "docs/installed_cli.md",
        "docs/public_python_api_v1.md",
        "docs/unified_local_frontend_contract.md",
    ):
        assert value in html
    storage_root = str(server.app_context.managed_home.root)
    assert html.count(storage_root) == 1
    assert '<details class="storage-disclosure">' in html
    assert '<details class="storage-disclosure" open' not in html
    for route in APP_ROUTE_PATHS[:-1]:
        _status, _headers, other_body = _request(
            server,
            "GET",
            route,
            headers={"Cookie": cookie},
        )
        assert storage_root not in other_body.decode("utf-8")


def test_asset_allowlist_unknown_routes_and_no_product_endpoint(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    status, headers, body = _request(
        server,
        "GET",
        "/assets/app.css",
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert headers["content-type"] == "text/css; charset=utf-8"
    assert b"focus-visible" in body and b"@media" in body
    for route in (
        "/missing",
        "/assets/app.js",
        "/assets/../templates/app.html",
        "/api/v1/state",
        "/api/v1/operations",
    ):
        status, _headers, body = _request(
            server,
            "GET",
            route,
            headers={"Cookie": cookie},
        )
        assert status == 404
        assert b"Page not found" in body


def test_response_security_headers_apply_to_success_redirect_and_errors(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    responses = (
        _request(server, "GET", f"/?token={_TOKEN}"),
        _request(server, "GET", "/", headers={"Cookie": cookie}),
        _request(server, "GET", "/missing", headers={"Cookie": cookie}),
        _request(server, "GET", "/"),
    )
    for _status, headers, _body in responses:
        assert headers["cache-control"] == "no-store"
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["x-frame-options"] == "DENY"
        assert headers["content-security-policy"] == APP_WEB_CONTENT_SECURITY_POLICY
        assert headers["permissions-policy"] == APP_WEB_PERMISSIONS_POLICY
        assert "access-control-allow-origin" not in headers


def test_access_logging_is_disabled(
    running_app_server: SkatMindAppWebServerV1,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status, _headers, _body = _request(
        running_app_server,
        "GET",
        f"/?token={_TOKEN}",
    )
    assert status == 303
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


def test_host_cookie_and_query_validation_rejects_missing_invalid_and_duplicates(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    host = f"127.0.0.1:{server.port}"
    invalid_requests = (
        (("Cookie", cookie),),
        (("Host", "example.com"), ("Cookie", cookie)),
        (("Host", host),),
        (("Host", host), ("Cookie", "malformed-cookie")),
        (("Host", host), ("Cookie", cookie), ("Cookie", cookie)),
        (("Host", host), ("Host", host), ("Cookie", cookie)),
    )
    for headers in invalid_requests:
        status, _response_headers, _body = _raw_request(server, "GET", "/", headers)
        assert status == 403
    status, _headers, _body = _request(
        server,
        "GET",
        "/?unexpected=1",
        headers={"Cookie": cookie},
    )
    assert status == 403


def test_mutation_origin_and_duplicate_origin_are_rejected(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, mutation_headers = _bootstrap(server)
    host = f"127.0.0.1:{server.port}"
    base = (
        ("Host", host),
        ("Cookie", cookie),
        ("Content-Length", "0"),
        ("Content-Type", "application/x-www-form-urlencoded"),
    )
    for origins in (
        (),
        (("Origin", "http://example.com"),),
        (("Origin", server.origin), ("Origin", server.origin)),
        (("Origin", f"http://localhost:{server.port}"),),
    ):
        status, _headers, _body = _raw_request(server, "POST", "/", (*base, *origins))
        assert status == 403

    status, headers, body = _request(
        server,
        "POST",
        "/",
        headers={
            **mutation_headers,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body=b"",
    )
    assert status == 405
    assert headers["allow"] == "GET"
    assert body == b"Method not allowed"


def test_body_header_cardinality_transfer_encoding_type_and_size_limits(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    host = f"127.0.0.1:{server.port}"
    authorized = (
        ("Host", host),
        ("Cookie", cookie),
        ("Origin", server.origin),
    )
    cases = (
        ((*authorized, ("Content-Type", "application/x-www-form-urlencoded")), 400),
        (
            (
                *authorized,
                ("Content-Length", "0"),
                ("Content-Length", "0"),
                ("Content-Type", "application/x-www-form-urlencoded"),
            ),
            400,
        ),
        (
            (
                *authorized,
                ("Content-Length", "0"),
                ("Content-Type", "application/x-www-form-urlencoded"),
                ("Content-Type", "application/x-www-form-urlencoded"),
            ),
            400,
        ),
        (
            (
                *authorized,
                ("Content-Length", "0"),
                ("Content-Type", "application/json"),
            ),
            415,
        ),
        (
            (
                *authorized,
                ("Content-Length", "0"),
                ("Content-Type", "application/x-www-form-urlencoded"),
                ("Transfer-Encoding", "chunked"),
            ),
            400,
        ),
        (
            (
                *authorized,
                ("Content-Length", str(APP_WEB_MAX_REQUEST_BYTES + 1)),
                ("Content-Type", "application/x-www-form-urlencoded"),
            ),
            413,
        ),
    )
    for headers, expected_status in cases:
        status, _response_headers, _body = _raw_request(server, "POST", "/", headers)
        assert status == expected_status

    assert APP_WEB_MAX_REQUEST_BYTES > 1_048_576


def test_short_request_body_is_rejected(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    connection.putrequest("POST", "/")
    connection.putheader("Cookie", cookie)
    connection.putheader("Origin", server.origin)
    connection.putheader("Content-Length", "2")
    connection.putheader("Content-Type", "application/x-www-form-urlencoded")
    connection.endheaders(b"x")
    assert connection.sock is not None
    connection.sock.shutdown(socket.SHUT_WR)
    response = connection.getresponse()
    assert response.status == 400
    response.read()
    connection.close()


@pytest.mark.parametrize(
    "method",
    ("BREW", "CONNECT", "DELETE", "HEAD", "OPTIONS", "TRACE"),
)
def test_unsupported_methods_are_405_on_known_routes(
    running_app_server: SkatMindAppWebServerV1,
    method: str,
) -> None:
    server = running_app_server
    cookie, mutation_headers = _bootstrap(server)
    headers = {"Cookie": cookie}
    if method == "DELETE":
        headers["Origin"] = mutation_headers["Origin"]
    status, response_headers, _body = _request(server, method, "/about", headers=headers)
    assert status == 405
    assert response_headers["allow"] == "GET"


def test_unknown_route_with_unsupported_method_is_404(
    running_app_server: SkatMindAppWebServerV1,
) -> None:
    server = running_app_server
    cookie, _mutation_headers = _bootstrap(server)
    status, _headers, _body = _request(
        server,
        "OPTIONS",
        "/unknown",
        headers={"Cookie": cookie},
    )
    assert status == 404
