from __future__ import annotations

import http.client
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlencode

import pytest
from test_local_match_capture_web import _creation_values

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_profile_operations import (
    FRONTEND_LANGUAGE_ACTION_ROUTE,
    FRONTEND_PROFILE_RESET_ACTION_ROUTE,
    is_safe_frontend_return_path_v1,
)
from skatmind.app_web.frontend_profile_persistence import load_frontend_profile_file_v1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.security import APP_WEB_COOKIE_NAME
from skatmind.app_web.server import (
    SkatMindAppWebServerV1,
    serve_app_web_in_thread_v1,
    start_app_web_server_v1,
)

_TOKEN = "localization-test-token"


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


@pytest.fixture
def localized_server(tmp_path: Path) -> Iterator[SkatMindAppWebServerV1]:
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


def _bootstrap(server: SkatMindAppWebServerV1) -> tuple[dict[str, str], dict[str, str]]:
    status, headers, body = _request(server, "GET", f"/?token={_TOKEN}")
    assert status == 303 and body == b""
    cookie = headers["set-cookie"].split(";", 1)[0]
    get_headers = {"Cookie": cookie}
    post_headers = {
        **get_headers,
        "Origin": server.origin,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    return get_headers, post_headers


def _post(
    server: SkatMindAppWebServerV1,
    headers: dict[str, str],
    route: str,
    values: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    return _request(
        server,
        "POST",
        route,
        headers=headers,
        body=urlencode(values).encode("ascii"),
    )


def test_return_path_allowlist_accepts_only_rendered_html_routes() -> None:
    report = "a" * 64
    for allowed in (
        "/",
        "/analyze",
        "/review",
        "/sessions",
        "/sessions/current",
        "/matches",
        "/matches/new",
        "/matches/current",
        "/matches/position/1",
        "/matches/position/36",
        f"/matches/reports/{report}",
        "/learning",
        "/learning/current",
        "/about",
    ):
        assert is_safe_frontend_return_path_v1(allowed)
    for rejected in (
        "https://example.com/",
        "//example.com/",
        "/?token=secret",
        "/about?x=1",
        "/about#profile",
        "/assets/app.css",
        "/downloads/analyze/result.json",
        "/matches/api/v1/state",
        "/learning/api/v1/state",
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        "/missing",
        "/matches/position/0",
        f"/matches/reports/{'A' * 64}",
    ):
        assert not is_safe_frontend_return_path_v1(rejected)


def test_browser_german_does_not_write_and_localizes_shell_home_about_and_errors(
    localized_server: SkatMindAppWebServerV1,
) -> None:
    server = localized_server
    get_headers, _post_headers = _bootstrap(server)
    german = {**get_headers, "Accept-Language": "de-DE,de;q=0.9"}
    for route in ("/", "/about", "/analyze", "/review", "/sessions", "/matches", "/learning"):
        status, _headers, body = _request(server, "GET", route, headers=german)
        assert status == 200
        html = body.decode()
        assert '<html lang="de">' in html
        assert "Deutsch" in html and "English" in html
        assert 'action="/actions/profile/language"' in html
        assert "Zum Hauptinhalt springen" in html
        assert "Hauptnavigation" in html
        assert "Lokale Skat-Analyse. Kein Cloud-Dienst." in html
    assert not (server.app_context.managed_home.root / "frontend-profile.json").exists()

    status, _headers, home = _request(server, "GET", "/", headers=german)
    assert status == 200
    home_html = home.decode()
    home_main = home_html[home_html.index("<main") : home_html.index("</main>")]
    home_groups = home_main[home_main.index('<section class="home-group"') :]
    assert "SkatMind läuft lokal auf diesem Computer" in home_html
    assert home_html.count('<article class="task-card">') == 6
    assert home_html.count('<section class="home-group"') == 4
    assert "Welchen Bereich brauche ich?" in home_html
    assert "Benötigte Angaben" in home_html
    assert "Eine Entscheidung analysieren" in home_html
    assert home_groups.index("Ein vollständiges 36er-Match erfassen") < home_groups.index(
        "Ein einzelnes Spiel erfassen oder fortsetzen"
    )
    assert "Aktuell oder nachträglich" in home_html

    status, _headers, about = _request(server, "GET", "/about", headers=german)
    assert status == 200
    about_html = about.decode()
    assert "Lokale Einstellungen und Spieler" in about_html
    assert "Browsersprache" in about_html
    assert "Nicht gespeichert" in about_html
    assert "Gespeicherte Spieler und Arbeitsablauf-Vorgaben" in about_html
    assert 'action="/actions/profile/reset"' in about_html
    assert ", and <code>" not in about_html

    status, _headers, missing = _request(server, "GET", "/missing", headers=german)
    assert status == 404
    assert "Seite nicht gefunden" in missing.decode()


def test_german_workflow_bodies_are_explicitly_marked_as_transitional_english(
    localized_server: SkatMindAppWebServerV1,
) -> None:
    server = localized_server
    get_headers, _post_headers = _bootstrap(server)
    german = {**get_headers, "Accept-Language": "de"}
    for route in ("/analyze", "/review", "/sessions", "/matches", "/learning"):
        status, _headers, body = _request(server, "GET", route, headers=german)
        html = body.decode()
        assert status == 200
        assert "vorübergehend auf Englisch verfügbar" in html
        assert '<div class="english-workflow-body" lang="en">' in html
        assert html.index('class="concept-guide"') < html.index(
            '<div class="english-workflow-body" lang="en">'
        )
    status, _headers, sessions = _request(server, "GET", "/sessions", headers=german)
    assert status == 200
    sessions_html = sessions.decode()
    assert "Noch keine erfassten einzelnen Spiele" in sessions_html
    assert sessions_html.index("Noch keine erfassten einzelnen Spiele") < sessions_html.index(
        '<div class="english-workflow-body" lang="en">'
    )
    status, _headers, matches = _request(server, "GET", "/matches", headers=german)
    assert status == 200 and "Noch keine erfassten Matches" in matches.decode()
    status, _headers, learning = _request(server, "GET", "/learning", headers=german)
    assert status == 200 and "Noch keine Lernsammlungen" in learning.decode()
    status, _headers, home = _request(server, "GET", "/", headers=german)
    assert status == 200
    assert "english-workflow-body" not in home.decode()


def test_explicit_language_persists_over_browser_changes_and_survives_restart(
    localized_server: SkatMindAppWebServerV1,
) -> None:
    server = localized_server
    get_headers, post_headers = _bootstrap(server)
    status, headers, body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {"language": "en", "profile_generation": "0", "return_to": "/about"},
    )
    assert status == 303 and headers["location"] == "/about" and body == b""
    profile = load_frontend_profile_file_v1(server.app_context.managed_home.root)
    assert profile.status == "available"
    assert profile.document is not None
    assert profile.document.revision == 0 and profile.document.language == "en"
    profile_path = server.app_context.managed_home.root / "frontend-profile.json"
    retained_bytes = profile_path.read_bytes()
    retained_mtime = profile_path.stat().st_mtime_ns

    german_browser = {**get_headers, "Accept-Language": "de-DE"}
    status, _headers, content = _request(server, "GET", "/", headers=german_browser)
    assert status == 200 and b'<html lang="en">' in content

    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {"language": "en", "profile_generation": "1", "return_to": "/"},
    )
    assert status == 303 and headers["location"] == "/"
    assert profile_path.read_bytes() == retained_bytes
    assert profile_path.stat().st_mtime_ns == retained_mtime
    assert server.app_context.frontend_profile.generation == 1

    restarted = AppWebContextV1.create(server.app_context.managed_home)
    assert restarted.frontend_profile.document is not None
    assert restarted.frontend_profile.document.language == "en"


def test_language_redirect_to_category_reuses_retained_discovery(
    localized_server: SkatMindAppWebServerV1,
) -> None:
    server = localized_server
    get_headers, post_headers = _bootstrap(server)
    status, _headers, _body = _request(server, "GET", "/sessions", headers=get_headers)
    assert status == 200
    before = server.app_context.managed_stateful.discoveries["sessions"]
    before_generation = server.app_context.managed_stateful.generations["sessions"]

    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {"language": "de", "profile_generation": "0", "return_to": "/sessions"},
    )
    assert status == 303 and headers["location"] == "/sessions"
    status, _headers, _body = _request(server, "GET", "/about", headers=get_headers)
    assert status == 200
    status, _headers, body = _request(server, "GET", "/sessions", headers=get_headers)
    assert status == 200 and b'<html lang="de">' in body
    assert server.app_context.managed_stateful.discoveries["sessions"] is before
    assert server.app_context.managed_stateful.generations["sessions"] == before_generation


@pytest.mark.parametrize(
    "return_to",
    (
        "https://example.com/",
        "//example.com/",
        "/about?unsafe=1",
        "/about#unsafe",
        "/assets/app.css",
        "/downloads/analyze/result.json",
        "/matches/api/v1/state",
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        "/unknown",
    ),
)
def test_language_action_rejects_unsafe_redirects(
    localized_server: SkatMindAppWebServerV1,
    return_to: str,
) -> None:
    _get_headers, post_headers = _bootstrap(localized_server)
    status, headers, _body = _post(
        localized_server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {"language": "de", "profile_generation": "0", "return_to": return_to},
    )
    assert status == 400
    assert "location" not in headers
    assert not (localized_server.app_context.managed_home.root / "frontend-profile.json").exists()


def test_language_action_enforces_cookie_host_origin_locale_and_generation(
    localized_server: SkatMindAppWebServerV1,
) -> None:
    server = localized_server
    get_headers, post_headers = _bootstrap(server)
    values = {"language": "de", "profile_generation": "0", "return_to": "/"}
    for headers in (
        {"Origin": server.origin, "Content-Type": "application/x-www-form-urlencoded"},
        {
            "Cookie": f"{APP_WEB_COOKIE_NAME}={_TOKEN}",
            "Origin": "null",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        {
            "Cookie": f"{APP_WEB_COOKIE_NAME}={_TOKEN}",
            "Origin": "http://example.com",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    ):
        status, _response_headers, _body = _post(
            server,
            headers,
            FRONTEND_LANGUAGE_ACTION_ROUTE,
            values,
        )
        assert status == 403
    malformed = (
        {**values, "language": "fr"},
        {**values, "profile_generation": "00"},
        {**values, "extra": "unsupported"},
    )
    for submitted in malformed:
        status, _headers, _body = _post(
            server,
            post_headers,
            FRONTEND_LANGUAGE_ACTION_ROUTE,
            submitted,
        )
        assert status == 400
    status, _headers, _body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {**values, "profile_generation": "1"},
    )
    assert status == 409
    status, headers, _body = _request(
        server,
        "GET",
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        headers=get_headers,
    )
    assert status == 405 and headers["allow"] == "POST"


def test_language_action_error_retains_its_safe_return_route(
    localized_server: SkatMindAppWebServerV1,
) -> None:
    _get_headers, post_headers = _bootstrap(localized_server)
    status, _headers, body = _post(
        localized_server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {"language": "fr", "profile_generation": "0", "return_to": "/about"},
    )
    assert status == 400
    assert 'name="return_to" value="/about"' in body.decode()


def test_language_switch_preserves_all_retained_context_objects_and_executes_no_product_work(
    localized_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = localized_server
    _get_headers, post_headers = _bootstrap(server)
    status, _headers, _body = _post(
        server,
        post_headers,
        "/learning/create",
        {"corpus_id": "locale-corpus"},
    )
    assert status == 303
    status, _headers, _body = _post(
        server,
        post_headers,
        "/sessions/create",
        {
            "session_id": "locale-session",
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
    assert status == 303
    status, _headers, _body = _post(
        server,
        post_headers,
        "/matches/api/v1/create",
        _creation_values(match_id="locale-match"),
    )
    assert status == 303
    context = server.app_context
    assert context.managed_stateful.active_session is not None
    assert context.managed_stateful.active_match is not None
    assert context.managed_stateful.active_learning is not None
    active_match = context.managed_stateful.active_match
    active_learning = context.managed_stateful.active_learning
    retained = (
        context.analyze_state,
        context.review_state,
        context.managed_stateful,
        context.managed_stateful.active_session,
        context.managed_stateful.active_match,
        context.managed_stateful.active_learning,
        active_match.capture.report_store,
        active_match.last_result,
        active_learning.corpus.strategy_source_store,
        active_learning.corpus.prepared_artifacts,
        active_learning.last_result,
        dict(context.managed_stateful.discoveries),
        dict(context.managed_stateful.generations),
    )

    def unexpected_product_execution(*_args, **_kwargs):
        raise AssertionError("Language switching executed Product work.")

    for name in (
        "run_guided_analyze_v1",
        "run_guided_review_v1",
        "execute_guided_session_position_v1",
        "execute_unified_match_analysis_v1",
        "prepare_unified_learning_artifacts_v1",
    ):
        monkeypatch.setattr(f"skatmind.app_web.server.{name}", unexpected_product_execution)
    status, _headers, _body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {"language": "de", "profile_generation": "0", "return_to": "/review"},
    )
    assert status == 303
    assert retained == (
        context.analyze_state,
        context.review_state,
        context.managed_stateful,
        context.managed_stateful.active_session,
        context.managed_stateful.active_match,
        context.managed_stateful.active_learning,
        active_match.capture.report_store,
        active_match.last_result,
        active_learning.corpus.strategy_source_store,
        active_learning.corpus.prepared_artifacts,
        active_learning.last_result,
        dict(context.managed_stateful.discoveries),
        dict(context.managed_stateful.generations),
    )


def test_invalid_profile_warns_in_english_and_requires_authenticated_reset(
    tmp_path: Path,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    profile_path = home.root / "frontend-profile.json"
    invalid = b"private parser detail <unsafe>\n"
    profile_path.write_bytes(invalid)
    context = AppWebContextV1.create(home)
    server = start_app_web_server_v1(context, port=0, token=_TOKEN)
    thread = serve_app_web_in_thread_v1(server)
    try:
        get_headers, post_headers = _bootstrap(server)
        german = {**get_headers, "Accept-Language": "de"}
        status, _headers, body = _request(server, "GET", "/", headers=german)
        html = body.decode()
        assert status == 200 and '<html lang="en">' in html
        assert "The local settings profile is invalid" in html
        assert "private parser detail" not in html
        assert str(profile_path) not in html

        status, _headers, _body = _post(
            server,
            post_headers,
            FRONTEND_LANGUAGE_ACTION_ROUTE,
            {"language": "de", "profile_generation": "0", "return_to": "/"},
        )
        assert status == 409 and profile_path.read_bytes() == invalid
        status, headers, _body = _post(
            server,
            post_headers,
            FRONTEND_PROFILE_RESET_ACTION_ROUTE,
            {
                "confirm_reset": "on",
                "profile_generation": "0",
                "return_to": "/about",
            },
        )
        assert status == 303 and headers["location"] == "/about"
        loaded = load_frontend_profile_file_v1(home.root)
        assert loaded.status == "available"
        assert loaded.document is not None and loaded.document.language is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_authorization_page_uses_browser_language_without_reflecting_request_values(
    localized_server: SkatMindAppWebServerV1,
) -> None:
    server = localized_server
    status, headers, body = _request(
        server,
        "GET",
        "/private-marker?submitted-marker=value-marker",
        headers={"Accept-Language": "de-DE"},
    )
    html = body.decode()
    assert status == 403
    assert headers["content-type"] == "text/html; charset=utf-8"
    assert '<html lang="de">' in html
    assert "Anfrage nicht autorisiert" in html
    assert "private-marker" not in html
    assert "submitted-marker" not in html
    assert "value-marker" not in html
    assert "href=" not in html and "src=" not in html
