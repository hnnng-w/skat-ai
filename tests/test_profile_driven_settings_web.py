from __future__ import annotations

import http.client
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlencode

import pytest

import skatmind.app_web.learning_frontend as learning_frontend
import skatmind.app_web.match_frontend as match_frontend
import skatmind.app_web.profile_player_operations as profile_player_operations
import skatmind.app_web.server as server_module
import skatmind.app_web.session_frontend as session_frontend
import skatmind.capture_web.context as capture_context
import skatmind.capture_web.operations as capture_operations
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.frontend_profile_operations import (
    FRONTEND_LANGUAGE_ACTION_ROUTE,
    FRONTEND_PROFILE_MANAGED_LABEL_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE,
    FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE,
    FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE,
    FrontendProfilePersistenceConflictError,
    save_prepared_frontend_profile_v1,
)
from skatmind.app_web.frontend_profile_persistence import FrontendProfilePersistenceSizeError
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.profile_player_contracts import ManagedItemDisplayLabelV1
from skatmind.app_web.server import (
    SkatMindAppWebServerV1,
    serve_app_web_in_thread_v1,
    start_app_web_server_v1,
)

_TOKEN = "profile-settings-test-token"


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
def settings_server(tmp_path: Path) -> Iterator[SkatMindAppWebServerV1]:
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
    return get_headers, {
        **get_headers,
        "Origin": server.origin,
        "Content-Type": "application/x-www-form-urlencoded",
    }


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


def _generation(server: SkatMindAppWebServerV1) -> str:
    with server.app_context.lock:
        return str(server.app_context.frontend_profile.generation)


def _add_player(
    server: SkatMindAppWebServerV1,
    headers: dict[str, str],
    *,
    name: str = "Anna",
) -> None:
    status, response_headers, body = _post(
        server,
        headers,
        FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE,
        {
            "display_name": name,
            "aliases": "Anni\nA. Example",
            "platform_player_ids": "EuroSkat = anna-42",
            "profile_generation": _generation(server),
        },
    )
    assert status == 303 and response_headers["location"] == "/about" and body == b""


def _session_values(server: SkatMindAppWebServerV1) -> dict[str, str]:
    return {
        "game_name": "One-call game",
        "capture_mode": "retrospective",
        "player_1_handle": "",
        "player_1_name": "Alice",
        "player_2_handle": "",
        "player_2_name": "Bob",
        "player_3_handle": "",
        "player_3_name": "Carol",
        "perspective_seat": "",
        "save_players": "false",
        "save_preferences": "false",
        "profile_generation": _generation(server),
    }


def _match_values(server: SkatMindAppWebServerV1) -> dict[str, str]:
    return {
        "match_title": "One-call match",
        "played_date": "",
        "platform_choice": "euroskat",
        "custom_platform": "",
        "player_1_handle": "",
        "player_1_name": "Alice",
        "player_2_handle": "",
        "player_2_name": "Bob",
        "player_3_handle": "",
        "player_3_name": "Carol",
        "perspective_seat": "forehand",
        "source_url": "",
        "external_match_id": "",
        "player_1_platform_id": "",
        "player_2_platform_id": "",
        "player_3_platform_id": "",
        "source_kind": "",
        "source_title": "",
        "source_channel_name": "",
        "played_at": "",
        "match_timecode_start": "",
        "match_timecode_end": "",
        "save_players": "false",
        "save_preferences": "false",
        "profile_generation": _generation(server),
    }


def test_about_renders_bilingual_local_settings_without_internal_player_ids(
    settings_server: SkatMindAppWebServerV1,
) -> None:
    server = settings_server
    get_headers, post_headers = _bootstrap(server)
    status, _headers, body = _request(server, "GET", "/about", headers=get_headers)
    html = body.decode()
    assert status == 200
    assert "Local settings and players" in html
    assert "Saved Players" in html
    assert "Creation defaults" in html
    assert FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE in html

    _add_player(server, post_headers)
    with server.app_context.lock:
        profile = server.app_context.frontend_profile.document
    assert profile is not None
    player = profile.known_players[0]
    status, _headers, body = _request(server, "GET", "/about", headers=get_headers)
    html = body.decode()
    assert status == 200
    assert "Anna" in html and "Anni" in html and "anna-42" in html
    assert player.player_id not in html
    assert build_known_player_handle_v1(player.player_id) in html

    status, _headers, body = _request(
        server,
        "GET",
        "/about",
        headers={**get_headers, "Accept-Language": "de"},
    )
    assert status == 200
    german = body.decode()
    assert "Lokale Einstellungen und Spieler" in german
    assert "Gespeicherte Spieler" in german
    assert "Erfassungsvorgaben" in german


def test_player_edit_preferences_and_referenced_removal_use_profile_cas(
    settings_server: SkatMindAppWebServerV1,
) -> None:
    server = settings_server
    get_headers, post_headers = _bootstrap(server)
    _add_player(server, post_headers)
    with server.app_context.lock:
        profile = server.app_context.frontend_profile.document
    assert profile is not None
    handle = build_known_player_handle_v1(profile.known_players[0].player_id)

    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE,
        {
            "display_name": "Anna Berlin",
            "aliases": "Anna",
            "platform_player_ids": "EuroSkat = anna-43",
            "player_handle": handle,
            "profile_generation": _generation(server),
        },
    )
    assert status == 303 and headers["location"] == "/about"
    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE,
        {
            "own_player_handle": handle,
            "preferred_perspective_player_handle": handle,
            "platform_choice": "custom",
            "custom_platform": "Local club",
            "advanced_settings_expanded": "true",
            "profile_generation": _generation(server),
        },
    )
    assert status == 303 and headers["location"] == "/about"
    with server.app_context.lock:
        profile = server.app_context.frontend_profile.document
    assert profile is not None
    assert profile.known_players[0].display_name == "Anna Berlin"
    assert profile.own_player_id == profile.known_players[0].player_id
    assert profile.preferred_perspective_player_id == profile.own_player_id
    assert profile.preferred_game_platform == "Local club"
    assert profile.interface_preferences.advanced_settings_expanded is True

    status, _headers, body = _request(server, "GET", "/matches/new", headers=get_headers)
    html = body.decode()
    assert status == 200
    assert '<option value="custom" selected>' in html
    assert 'name="custom_platform" maxlength="120" value="Local club"' in html
    assert '<details class="advanced-settings" open>' in html
    assert f'<option value="{handle}" selected>' in html
    assert '<option value="forehand" selected>' in html

    status, _headers, body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE,
        {
            "player_handle": handle,
            "profile_generation": _generation(server),
        },
    )
    assert status == 400 and b"Check the submitted form" in body
    with server.app_context.lock:
        assert len(server.app_context.frontend_profile.document.known_players) == 1
    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE,
        {
            "player_handle": handle,
            "confirm_referenced": "on",
            "profile_generation": _generation(server),
        },
    )
    assert status == 303 and headers["location"] == "/about"
    with server.app_context.lock:
        profile = server.app_context.frontend_profile.document
    assert profile is not None
    assert profile.known_players == ()
    assert profile.own_player_id is None
    assert profile.preferred_perspective_player_id is None


def test_managed_label_and_recommended_reset_preserve_local_identity_data(
    settings_server: SkatMindAppWebServerV1,
) -> None:
    server = settings_server
    get_headers, post_headers = _bootstrap(server)
    status, _headers, _body = _post(
        server,
        post_headers,
        "/learning/create",
        {
            "collection_name": "Original collection",
            "profile_generation": _generation(server),
        },
    )
    assert status == 303
    status, _headers, body = _request(server, "GET", "/learning", headers=get_headers)
    assert status == 200 and FRONTEND_PROFILE_MANAGED_LABEL_ACTION_ROUTE.encode() in body
    with server.app_context.lock:
        discovery = server.app_context.managed_stateful.discoveries["corpora"]
    item = discovery.view.items[0]
    product_id = item.semantic_product_id
    assert product_id is not None
    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_MANAGED_LABEL_ACTION_ROUTE,
        {
            "managed_family": "corpora",
            "managed_handle": item.handle,
            "managed_generation": str(item.discovery_generation),
            "display_name": "Renamed collection",
            "played_date": "",
            "profile_generation": _generation(server),
            "return_to": "/learning",
        },
    )
    assert status == 303 and headers["location"] == "/learning"
    status, _headers, body = _request(server, "GET", "/learning", headers=get_headers)
    assert status == 200 and b"Renamed collection" in body
    assert product_id.encode() not in body

    status, _headers, _body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {
            "language": "de",
            "profile_generation": _generation(server),
            "return_to": "/about",
        },
    )
    assert status == 303
    _add_player(server, post_headers)
    with server.app_context.lock:
        profile = server.app_context.frontend_profile.document
    assert profile is not None
    handle = build_known_player_handle_v1(profile.known_players[0].player_id)
    status, _headers, _body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE,
        {
            "own_player_handle": handle,
            "preferred_perspective_player_handle": handle,
            "platform_choice": "euroskat",
            "custom_platform": "",
            "advanced_settings_expanded": "true",
            "profile_generation": _generation(server),
        },
    )
    assert status == 303
    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE,
        {
            "confirm_recommended_reset": "on",
            "profile_generation": _generation(server),
        },
    )
    assert status == 303 and headers["location"] == "/about"
    with server.app_context.lock:
        profile = server.app_context.frontend_profile.document
    assert profile is not None
    assert profile.language == "de"
    assert len(profile.known_players) == 1
    assert profile.own_player_id == profile.known_players[0].player_id
    assert profile.preferred_perspective_player_id is None
    assert profile.preferred_game_platform is None
    assert profile.interface_preferences.advanced_settings_expanded is False
    assert profile.managed_item_display_labels[0].display_name == "Renamed collection"


def test_normal_creation_invokes_each_product_initializer_once(
    settings_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = settings_server
    _get_headers, post_headers = _bootstrap(server)
    counts = {
        "session_initialize": 0,
        "session_save": 0,
        "match_initialize": 0,
        "match_save": 0,
        "learning_initialize": 0,
        "profile_save": 0,
    }

    session_create = session_frontend.session_api.create_session
    session_save = session_frontend.session_files.save_session_file
    match_create = capture_operations.create_match_capture_workspace_v1
    match_save = capture_context.save_match_workspace_file_v1
    learning_create = learning_frontend.initialize_learning_corpus_web_v1
    profile_save = server_module.save_prepared_frontend_profile_v1

    def counted_session(*args, **kwargs):
        counts["session_initialize"] += 1
        return session_create(*args, **kwargs)

    def counted_session_save(*args, **kwargs):
        counts["session_save"] += 1
        return session_save(*args, **kwargs)

    def counted_match(*args, **kwargs):
        counts["match_initialize"] += 1
        return match_create(*args, **kwargs)

    def counted_match_save(*args, **kwargs):
        counts["match_save"] += 1
        return match_save(*args, **kwargs)

    def counted_learning(*args, **kwargs):
        counts["learning_initialize"] += 1
        return learning_create(*args, **kwargs)

    def counted_profile_save(*args, **kwargs):
        counts["profile_save"] += 1
        return profile_save(*args, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Creation must not run analysis or preparation.")

    monkeypatch.setattr(session_frontend.session_api, "create_session", counted_session)
    monkeypatch.setattr(session_frontend.session_files, "save_session_file", counted_session_save)
    monkeypatch.setattr(match_frontend, "create_match_capture_workspace_v1", counted_match)
    monkeypatch.setattr(capture_context, "save_match_workspace_file_v1", counted_match_save)
    monkeypatch.setattr(
        learning_frontend,
        "initialize_learning_corpus_web_v1",
        counted_learning,
    )
    monkeypatch.setattr(server_module, "save_prepared_frontend_profile_v1", counted_profile_save)
    monkeypatch.setattr(server_module, "execute_guided_session_position_v1", forbidden)
    monkeypatch.setattr(server_module, "execute_guided_session_historical_v1", forbidden)
    monkeypatch.setattr(server_module, "execute_unified_match_analysis_v1", forbidden)
    monkeypatch.setattr(server_module, "prepare_unified_learning_artifacts_v1", forbidden)

    assert _post(server, post_headers, "/sessions/create", _session_values(server))[0] == 303
    assert _post(server, post_headers, "/matches/api/v1/create", _match_values(server))[0] == 303
    assert (
        _post(
            server,
            post_headers,
            "/learning/create",
            {
                "collection_name": "One-call collection",
                "profile_generation": _generation(server),
            },
        )[0]
        == 303
    )
    assert counts == {
        "session_initialize": 1,
        "session_save": 1,
        "match_initialize": 1,
        "match_save": 1,
        "learning_initialize": 1,
        "profile_save": 3,
    }
    active_session = server.app_context.managed_stateful.active_session
    active_match = server.app_context.managed_stateful.active_match
    active_learning = server.app_context.managed_stateful.active_learning
    assert active_session is not None
    assert active_session.document.state.revision == 0
    assert active_session.document.decision_checkpoints == ()
    assert active_match is not None and active_match.workspace.revision == 0
    assert len(active_match.capture.report_store) == 0
    assert active_learning is not None
    assert active_learning.corpus.prepared_artifacts is None


@pytest.mark.parametrize("family", ("sessions", "matches", "corpora"))
@pytest.mark.parametrize(
    ("failure", "warning"),
    (
        (
            FrontendProfilePersistenceConflictError(),
            b"Restart SkatMind before retrying profile-only changes",
        ),
        (
            FrontendProfilePersistenceSizeError(),
            b"bounded local profile is full",
        ),
        (
            OSError(),
            b"local profile file could not be written",
        ),
    ),
)
def test_profile_failure_after_product_creation_keeps_product_and_warns(
    settings_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    failure: Exception,
    warning: bytes,
) -> None:
    server = settings_server
    get_headers, post_headers = _bootstrap(server)

    save_attempts = 0

    def fail(*_args, **_kwargs):
        nonlocal save_attempts
        save_attempts += 1
        raise failure

    monkeypatch.setattr(
        "skatmind.app_web.server.save_prepared_frontend_profile_v1",
        fail,
    )
    if family == "sessions":
        route = "/sessions/create"
        values = _session_values(server)
        location = "/sessions/current"
        active_attribute = "active_session"
    elif family == "matches":
        route = "/matches/api/v1/create"
        values = _match_values(server)
        location = "/matches/position/1"
        active_attribute = "active_match"
    else:
        route = "/learning/create"
        values = {
            "collection_name": "Retained Product",
            "profile_generation": "0",
        }
        location = "/learning/current"
        active_attribute = "active_learning"
    status, headers, _body = _post(
        server,
        post_headers,
        route,
        values,
    )
    assert status == 303 and headers["location"] == location
    active = getattr(server.app_context.managed_stateful, active_attribute)
    assert active is not None and active.path.exists()
    assert save_attempts == 1
    assert not (server.app_context.managed_home.root / "frontend-profile.json").exists()
    status, _headers, body = _request(server, "GET", location, headers=get_headers)
    assert status == 200
    assert b"The Product was created and remains available" in body
    assert warning in body


def test_profile_file_conflict_requires_restart_instead_of_page_reload(
    settings_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = settings_server
    _get_headers, post_headers = _bootstrap(server)

    def conflict(*_args, **_kwargs):
        raise FrontendProfilePersistenceConflictError

    monkeypatch.setattr(
        profile_player_operations,
        "save_prepared_frontend_profile_v1",
        conflict,
    )
    status, _headers, body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE,
        {
            "display_name": "Anna",
            "aliases": "",
            "platform_player_ids": "",
            "profile_generation": "0",
        },
    )
    assert status == 409
    assert b"Restart SkatMind before trying again" in body
    assert b"Reload the current page" not in body


def test_full_profile_keeps_created_product_and_uses_capacity_warning(
    settings_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = settings_server
    get_headers, post_headers = _bootstrap(server)
    labels = tuple(
        ManagedItemDisplayLabelV1("sessions", f"existing-{index}", f"Game {index}")
        for index in range(2048)
    )
    full = build_local_frontend_profile_v1(managed_item_display_labels=labels)
    assert (
        save_prepared_frontend_profile_v1(
            server.app_context,
            requested=full,
            expected_generation=0,
        )
        == "saved"
    )

    def unexpected_profile_save(*_args, **_kwargs):
        raise AssertionError("A capacity-rejected profile must not be saved.")

    monkeypatch.setattr(
        server_module,
        "save_prepared_frontend_profile_v1",
        unexpected_profile_save,
    )
    status, headers, _body = _post(
        server,
        post_headers,
        "/learning/create",
        {
            "collection_name": "Created despite full profile",
            "profile_generation": "1",
        },
    )
    assert status == 303 and headers["location"] == "/learning/current"
    active = server.app_context.managed_stateful.active_learning
    assert active is not None and active.path.exists()
    with server.app_context.lock:
        assert server.app_context.frontend_profile.document == full
        assert server.app_context.frontend_profile.generation == 1
    status, _headers, body = _request(server, "GET", "/learning/current", headers=get_headers)
    assert status == 200
    assert b"bounded local profile is full" in body


def test_language_switch_preserves_local_settings_validation_without_new_entropy(
    settings_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = settings_server
    get_headers, post_headers = _bootstrap(server)
    _add_player(server, post_headers)

    def unexpected_entropy(_size: int) -> bytes:
        raise AssertionError("Invalid duplicate Player input consumed entropy.")

    monkeypatch.setattr("skatmind.app_web.server.secrets.token_bytes", unexpected_entropy)
    status, _headers, body = _post(
        server,
        post_headers,
        FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE,
        {
            "display_name": "Anna",
            "aliases": "Retained alias",
            "platform_player_ids": "",
            "profile_generation": _generation(server),
        },
    )
    assert status == 400 and b"Retained alias" in body
    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {
            "language": "de",
            "profile_generation": _generation(server),
            "return_to": "/about",
        },
    )
    assert status == 303 and headers["location"] == "/about"
    status, _headers, body = _request(server, "GET", "/about", headers=get_headers)
    html = body.decode()
    assert status == 200
    assert '<html lang="de">' in html
    assert "Retained alias" in html
    assert "Prüfen Sie das ausgefüllte Formular" in html


def test_language_switch_preserves_match_creation_and_field_local_feedback(
    settings_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = settings_server
    get_headers, post_headers = _bootstrap(server)

    def unexpected_entropy(_size: int) -> bytes:
        raise AssertionError("Rejected creation or language switching consumed entropy.")

    monkeypatch.setattr("skatmind.app_web.server.secrets.token_bytes", unexpected_entropy)
    values = _match_values(server)
    values.update(
        {
            "match_title": "Retained Match",
            "played_date": "2026-09-03",
            "platform_choice": "custom",
            "custom_platform": "Local table",
            "player_1_name": "Anna",
            "player_2_name": "Peter",
            "player_3_name": "Mira",
            "perspective_seat": "middlehand",
            "source_url": "https://youtube.com/watch?v=retained",
            "external_match_id": "external-retained",
            "source_kind": "manual_observation",
            "source_title": "Retained source",
            "source_channel_name": "Retained channel",
            "played_at": "2026-09-03T19:30:00+02:00",
            "match_timecode_start": "00:01:00",
            "match_timecode_end": "00:02:00",
        }
    )
    status, _headers, body = _post(
        server,
        post_headers,
        "/matches/api/v1/create",
        values,
    )
    english = body.decode()
    assert status == 400
    assert 'name="source_kind" aria-invalid="true"' in english
    assert '<details class="advanced-settings" open>' in english
    assert "Retained source" in english
    assert server.app_context.managed_stateful.active_match is None

    status, headers, _body = _post(
        server,
        post_headers,
        FRONTEND_LANGUAGE_ACTION_ROUTE,
        {
            "language": "de",
            "profile_generation": _generation(server),
            "return_to": "/matches/new",
        },
    )
    assert status == 303 and headers["location"] == "/matches/new"
    status, _headers, body = _request(server, "GET", "/matches/new", headers=get_headers)
    german = body.decode()
    assert status == 200
    assert '<html lang="de">' in german
    assert 'value="Retained Match"' in german
    assert 'value="2026-09-03"' in german
    assert '<option value="custom" selected>' in german
    assert 'value="Local table"' in german
    assert all(f'value="{name}"' in german for name in ("Anna", "Peter", "Mira"))
    assert '<option value="middlehand" selected>' in german
    assert 'value="https://youtube.com/watch?v=retained"' in german
    assert 'value="external-retained"' in german
    assert '<option value="manual_observation" selected>' in german
    assert 'value="Retained source"' in german
    assert 'value="Retained channel"' in german
    assert 'value="2026-09-03T19:30:00+02:00"' in german
    assert 'value="00:01:00"' in german and 'value="00:02:00"' in german
    assert 'name="source_kind" aria-invalid="true"' in german
    assert "Quellentyp" in german
    assert '<details class="advanced-settings" open>' in german
    assert server.app_context.managed_stateful.active_match is None


def test_product_failure_writes_no_profile_change(
    settings_server: SkatMindAppWebServerV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = settings_server
    _get_headers, post_headers = _bootstrap(server)

    def rejected(*_args, **_kwargs):
        raise ValueError("Product rejected.")

    monkeypatch.setattr(server_module, "create_unified_learning_corpus_v1", rejected)
    status, _headers, _body = _post(
        server,
        post_headers,
        "/learning/create",
        {
            "collection_name": "Rejected collection",
            "profile_generation": "0",
        },
    )
    assert status == 400
    assert server.app_context.managed_stateful.active_learning is None
    assert not (server.app_context.managed_home.root / "frontend-profile.json").exists()
