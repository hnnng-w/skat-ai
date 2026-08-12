import http.client
import json
import threading
from dataclasses import fields
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlencode, urlsplit

import pytest
from test_match_workspace_contracts import _definition

import skat_ai.capture_web.operations as operations_module
from skat_ai.capture_web.context import MatchCaptureWebContextV1
from skat_ai.capture_web.contracts import (
    MATCH_CAPTURE_WEB_API_PREFIX,
    MATCH_CAPTURE_WEB_ASSET_POLICY,
    MATCH_CAPTURE_WEB_BIND_HOST,
    MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES,
    MATCH_CAPTURE_WEB_NETWORK_POLICY,
    MATCH_CAPTURE_WEB_OPERATIONS,
    MATCH_CAPTURE_WEB_PERSISTENCE_POLICY,
    MATCH_CAPTURE_WEB_PROTOCOL_VERSION,
    MATCH_CAPTURE_WEB_RENDERING_POLICY,
    MATCH_CAPTURE_WEB_SECURITY_POLICY,
    MATCH_CAPTURE_WEB_VERSION,
    MATCH_CAPTURE_WEB_WORKSPACE_POLICY,
    MatchCaptureWebResultV1,
)
from skat_ai.capture_web.operations import (
    apply_match_capture_web_operation_v1,
    create_match_capture_workspace_v1,
    reload_match_capture_workspace_v1,
)
from skat_ai.capture_web.rendering import render_match_capture_web_page_v1
from skat_ai.capture_web.security import (
    MATCH_CAPTURE_WEB_CONTENT_SECURITY_POLICY,
    MATCH_CAPTURE_WEB_COOKIE_NAME,
    MATCH_CAPTURE_WEB_PERMISSIONS_POLICY,
)
from skat_ai.capture_web.server import start_match_capture_web_server_v1
from skat_ai.capture_web.state import build_match_capture_web_state_v1
from skat_ai.capture_web.timecodes import (
    build_presentation_timecode_v1,
    format_presentation_timecode_v1,
    parse_presentation_timecode_v1,
)
from skat_ai.errors import SkatAIValidationError
from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_capture_application import (
    append_match_capture_plays_v1,
    set_match_capture_declaration_v1,
    start_match_capture_game_v1,
)
from skat_ai.match_capture_application_contracts import MatchCaptureCardEntryV1
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence import save_match_workspace_file_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _creation_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "match_id": "capture-web-match",
        "title": "36er Finals Table",
        "game_platform": "EuroSkat",
        "external_match_id": "external-165",
        "played_at": "2026-08-01T19:30:00Z",
        "source_kind": "youtube_video",
        "source_url": "https://www.youtube.com/watch?v=example",
        "source_title": "Finals recording",
        "source_channel_name": "Tournament channel",
        "match_timecode_start": "01:02:03.500",
        "match_timecode_end": "02:12:00",
        "player_1_id": "player-a",
        "player_1_label": "Alice",
        "player_1_platform_id": "platform-a",
        "player_2_id": "player-b",
        "player_2_label": "Bob",
        "player_2_platform_id": "platform-b",
        "player_3_id": "player-c",
        "player_3_label": "Carol",
        "player_3_platform_id": "platform-c",
        "perspective_player_id": "player-a",
    }
    values.update(overrides)
    return values


def _operation_values(
    context: MatchCaptureWebContextV1,
    operation: str,
    **overrides: object,
) -> dict[str, object]:
    assert context.workspace is not None
    values: dict[str, object] = {
        "operation": operation,
        "match_position": "1",
        "expected_revision": str(context.workspace.revision),
    }
    values.update(overrides)
    return values


def _create_context(tmp_path: Path) -> MatchCaptureWebContextV1:
    context = MatchCaptureWebContextV1.open(tmp_path / "match.json")
    result = create_match_capture_workspace_v1(context, _creation_values())
    assert result.status == "applied"
    return context


def _ready_context(tmp_path: Path) -> MatchCaptureWebContextV1:
    context = _create_context(tmp_path)
    started = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "start_game"),
    )
    assert started.status == "applied"
    declared = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "set_declaration",
            declarer_player_id="player-b",
            game_type="grand",
            hand_game="",
            ouvert="",
            schneider_announced="",
            schwarz_announced="",
            matadors="",
            bid_value="24",
        ),
    )
    assert declared.status == "applied"
    return context


def test_web_versions_operations_policies_and_result_contract_are_exact() -> None:
    assert MATCH_CAPTURE_WEB_VERSION == 1
    assert MATCH_CAPTURE_WEB_PROTOCOL_VERSION == 1
    assert MATCH_CAPTURE_WEB_BIND_HOST == "127.0.0.1"
    assert MATCH_CAPTURE_WEB_API_PREFIX == "/api/v1"
    assert MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES == 1_048_576
    assert MATCH_CAPTURE_WEB_OPERATIONS == (
        "create_workspace",
        "reload_workspace",
        "update_match_metadata",
        "start_game",
        "set_game_timecode",
        "set_perspective_hand",
        "set_declaration",
        "set_original_skat",
        "set_discarded_cards",
        "append_plays",
        "truncate_plays",
        "set_commentary",
        "remove_commentary",
        "set_response_link",
        "remove_response_link",
        "mark_passed_deal",
        "clear_position",
    )
    assert MATCH_CAPTURE_WEB_WORKSPACE_POLICY == (
        "one_explicit_workspace_file_per_server"
    )
    assert MATCH_CAPTURE_WEB_PERSISTENCE_POLICY == (
        "load_operate_compare_and_swap_save"
    )
    assert MATCH_CAPTURE_WEB_SECURITY_POLICY == "loopback_same_origin_token"
    assert MATCH_CAPTURE_WEB_ASSET_POLICY == (
        "packaged_local_assets_without_external_dependencies"
    )
    assert MATCH_CAPTURE_WEB_RENDERING_POLICY == (
        "server_rendered_with_progressive_enhancement"
    )
    assert MATCH_CAPTURE_WEB_NETWORK_POLICY == "no_external_requests"
    assert tuple(field.name for field in fields(MatchCaptureWebResultV1)) == (
        "match_capture_web_protocol_version",
        "operation",
        "status",
        "http_status",
        "message",
        "state",
        "removed_commentary_ids",
        "removed_response_link_ids",
    )
    result = MatchCaptureWebResultV1(
        operation="reload_workspace",
        status="reloaded",
        http_status=200,
        message="Reloaded.",
        state={"nested": {"cards": ["CA"]}},
    )
    assert type(result.state) is MappingProxyType
    assert type(result.state["nested"]) is MappingProxyType
    assert result.state["nested"]["cards"] == ("CA",)
    with pytest.raises(TypeError):
        result.state["changed"] = True
    assert result.to_dict()["state"] == {"nested": {"cards": ["CA"]}}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", None),
        ("42", 42_000),
        ("12:34", 754_000),
        ("01:12:34", 4_354_000),
        ("01:12:34.500", 4_354_500),
        ("00:00:00.001", 1),
    ],
)
def test_presentation_timecode_parsing_and_formatting(
    value: str,
    expected: int | None,
) -> None:
    assert parse_presentation_timecode_v1(value) == expected
    if expected is not None:
        formatted = format_presentation_timecode_v1(expected)
        assert parse_presentation_timecode_v1(formatted) == expected


@pytest.mark.parametrize(
    "value",
    (
        " 42",
        "42 ",
        "-1",
        "60",
        "1:60",
        "1:60:00",
        "1:2",
        "1:02.5",
        "abc",
    ),
)
def test_presentation_timecode_rejects_invalid_text(value: str) -> None:
    with pytest.raises(ValueError):
        parse_presentation_timecode_v1(value)


def test_timecode_builder_persists_only_milliseconds() -> None:
    value = build_presentation_timecode_v1("12:34.500", "12:40")
    assert value.to_dict() == {
        "media_timecode_version": 1,
        "start_offset_ms": 754_500,
        "end_offset_ms": 760_000,
    }
    assert "12:34.500" not in json.dumps(value.to_dict())


def test_context_absent_resume_invalid_parent_and_safe_filename(tmp_path: Path) -> None:
    path = tmp_path / "private-match.json"
    context = MatchCaptureWebContextV1.open(path)
    assert context.workspace is None
    assert context.content_fingerprint is None
    assert context.workspace_filename == "private-match.json"
    with pytest.raises(FileNotFoundError):
        MatchCaptureWebContextV1.open(tmp_path / "missing" / "match.json")

    workspace = create_match_workspace_v1(_definition())
    document = build_match_workspace_persistence_document_v1(workspace)
    assert save_match_workspace_file_v1(
        path,
        document,
        expected_content_fingerprint=None,
    ).status == "saved"
    resumed = MatchCaptureWebContextV1.open(path)
    assert resumed.workspace == workspace
    assert resumed.content_fingerprint == document.content_fingerprint

    path.write_text("{}", encoding="utf-8")
    with pytest.raises(SkatAIValidationError):
        MatchCaptureWebContextV1.open(path)


def test_workspace_creation_uses_canonical_format_players_perspective_and_save(
    tmp_path: Path,
) -> None:
    context = MatchCaptureWebContextV1.open(tmp_path / "match.json")
    result = create_match_capture_workspace_v1(context, _creation_values())
    assert result.status == "applied"
    assert result.state["workspace_exists"] is True
    assert result.state["workspace_filename"] == "match.json"
    assert context.workspace is not None
    definition = context.workspace.match_definition
    assert definition.tournament_format.format_id == "euroskat_36_standard_v1"
    assert tuple(player.table_place for player in definition.participants) == (
        "place_1",
        "place_2",
        "place_3",
    )
    assert definition.perspective_player_id == "player-a"
    assert all(player.statistics_snapshot is None for player in definition.participants)
    assert context.workspace.revision == 0
    assert len(context.workspace.slots) == 36
    assert context.workspace_path.is_file()


@pytest.mark.parametrize(
    "source_values",
    (
        {
            "source_kind": "other_video",
            "source_url": "https://video.example.test/match",
            "source_channel_name": "Archive",
        },
        {
            "source_kind": "manual_observation",
            "source_url": "",
            "source_channel_name": "",
        },
    ),
)
def test_workspace_creation_supports_each_non_youtube_source(
    tmp_path: Path,
    source_values: dict[str, object],
) -> None:
    context = MatchCaptureWebContextV1.open(tmp_path / "match.json")
    assert create_match_capture_workspace_v1(
        context,
        _creation_values(**source_values),
    ).status == "applied"


def test_workspace_creation_conflict_when_target_appears_externally(tmp_path: Path) -> None:
    context = MatchCaptureWebContextV1.open(tmp_path / "match.json")
    external_workspace = create_match_workspace_v1(_definition())
    external_document = build_match_workspace_persistence_document_v1(
        external_workspace
    )
    save_match_workspace_file_v1(
        context.workspace_path,
        external_document,
        expected_content_fingerprint=None,
    )
    result = create_match_capture_workspace_v1(context, _creation_values())
    assert result.status == "persistence_conflict"
    assert result.http_status == 409
    assert context.workspace is None
    assert context.content_fingerprint is None


def test_metadata_correction_preserves_identity_and_uses_no_write_when_equal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _create_context(tmp_path)
    assert context.workspace is not None
    source = context.workspace.match_definition
    calls = 0
    original_save = operations_module.MatchCaptureWebContextV1.save_candidate

    def counted_save(self, workspace):
        nonlocal calls
        calls += 1
        return original_save(self, workspace)

    monkeypatch.setattr(
        operations_module.MatchCaptureWebContextV1,
        "save_candidate",
        counted_save,
    )
    values = _operation_values(
        context,
        "update_match_metadata",
        title="Corrected title",
        game_platform="EuroSkat corrected",
        external_match_id="external-165-corrected",
        played_at="2026-08-02T19:30:00Z",
        source_kind="other_video",
        source_url="https://video.example.test/corrected",
        source_title="Corrected recording",
        source_channel_name="Corrected channel",
        match_timecode_start="01:02:03.500",
        match_timecode_end="02:12:00",
        player_1_label="Alice corrected",
        player_1_platform_id="platform-a-corrected",
        player_2_label="Bob",
        player_2_platform_id="platform-b",
        player_3_label="Carol",
        player_3_platform_id="platform-c",
    )
    changed = apply_match_capture_web_operation_v1(context, values)
    assert changed.status == "applied"
    assert calls == 1
    assert context.workspace is not None
    target = context.workspace.match_definition
    assert target.match_id == source.match_id
    assert target.tournament_format is source.tournament_format
    assert tuple(item.player_id for item in target.participants) == tuple(
        item.player_id for item in source.participants
    )
    assert target.perspective_player_id == source.perspective_player_id
    assert target.title == "Corrected title"

    equal_values = dict(values)
    equal_values["expected_revision"] = str(context.workspace.revision)
    unchanged = apply_match_capture_web_operation_v1(context, equal_values)
    assert unchanged.status == "unchanged"
    assert calls == 1


def test_revision_conflict_precedes_payload_validation_and_save(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _create_context(tmp_path)
    monkeypatch.setattr(
        MatchCaptureWebContextV1,
        "save_candidate",
        lambda _self, _workspace: pytest.fail("stale operation attempted Save"),
    )
    result = apply_match_capture_web_operation_v1(
        context,
        {
            "operation": "append_plays",
            "match_position": "1",
            "expected_revision": "99",
            "cards": "XX",
            "decision_timecode": "invalid",
        },
    )
    assert result.status == "revision_conflict"
    assert result.http_status == 409


def test_game_setup_card_batch_derivation_undo_commentary_links_passed_and_clear(
    tmp_path: Path,
) -> None:
    context = _ready_context(tmp_path)
    assert context.workspace is not None
    first_batch = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "append_plays", cards="CA S7 C7", decision_timecode=""),
    )
    assert first_batch.status == "applied"
    game = context.workspace.slots[0].observed_game
    assert game is not None
    assert tuple(play.decision_index for play in game.plays) == (1, 2, 3)
    assert tuple(play.player_id for play in game.plays) == (
        "player-b",
        "player-c",
        "player-a",
    )
    assert first_batch.state["position_view"]["completed_trick_count"] == 1

    second = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "append_plays",
            cards="D7",
            decision_timecode="01:10:00",
        ),
    )
    assert second.status == "applied"
    assert second.state["position_view"]["current_trick_cards"] == ("D7",)

    commentary = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "set_commentary",
            decision_index="2",
            commentator_player_id="",
            commentator_name="Video analyst",
            text="First line\nSecond line",
            commentary_timecode="01:10:01",
            commentary_id="",
        ),
    )
    assert commentary.status == "applied"
    retained = context.workspace.slots[0].observed_game
    assert retained is not None
    item = retained.commentaries[0]
    assert item.subject_player_id == "player-c"
    assert item.text == "First line\nSecond line"

    link = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "set_response_link",
            commentary_id=item.commentary_id,
            response_decision_index="4",
            link_id="",
        ),
    )
    assert link.status == "applied"
    retained = context.workspace.slots[0].observed_game
    assert retained is not None and len(retained.response_links) == 1
    html = render_match_capture_web_page_v1(link.state)
    assert f'value="{item.commentary_id}"' in html
    assert '<option value="2" selected>#2 player-c - S7</option>' in html
    assert '<option value="4" selected>#4 player-b - D7</option>' in html

    truncated = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "truncate_plays", target_play_count="1"),
    )
    assert truncated.status == "applied"
    assert truncated.removed_commentary_ids == (item.commentary_id,)
    assert len(truncated.removed_response_link_ids) == 1
    assert context.workspace.slots[0].observed_game.plays[0].card == "CA"

    undo = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "truncate_plays", target_play_count="0"),
    )
    assert undo.status == "applied"
    passed = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "mark_passed_deal",
            game_timecode_start="",
            game_timecode_end="",
            confirm_replace="true",
        ),
    )
    assert passed.status == "applied"
    assert passed.state["position_view"]["game_state"] == "passed_deal"
    cleared = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "clear_position", confirm_clear="true"),
    )
    assert cleared.status == "applied"
    assert cleared.state["position_view"]["game_state"] == "empty"


def test_atomic_invalid_card_batch_preserves_context_and_file(tmp_path: Path) -> None:
    context = _ready_context(tmp_path)
    before_workspace = context.workspace
    before_bytes = context.workspace_path.read_bytes()
    with pytest.raises(ValueError):
        apply_match_capture_web_operation_v1(
            context,
            _operation_values(
                context,
                "append_plays",
                cards="CA XX C7",
                decision_timecode="",
            ),
        )
    assert context.workspace == before_workspace
    assert context.workspace_path.read_bytes() == before_bytes


def test_external_persistence_conflict_retains_old_context_until_explicit_reload(
    tmp_path: Path,
) -> None:
    context = _ready_context(tmp_path)
    old_workspace = context.workspace
    assert old_workspace is not None
    external_result = start_match_capture_game_v1(
        old_workspace,
        match_position=2,
        expected_revision=old_workspace.revision,
    )
    external_workspace = external_result.workspace_change.workspace
    external_document = build_match_workspace_persistence_document_v1(
        external_workspace
    )
    assert save_match_workspace_file_v1(
        context.workspace_path,
        external_document,
        expected_content_fingerprint=context.content_fingerprint,
    ).status == "saved"

    conflicted = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "append_plays", cards="CA", decision_timecode=""),
    )
    assert conflicted.status == "persistence_conflict"
    assert context.workspace == old_workspace
    reloaded = reload_match_capture_workspace_v1(context, selected_position=2)
    assert reloaded.status == "reloaded"
    assert context.workspace == external_workspace
    assert reloaded.state["selected_position"] == 2


def test_state_and_html_render_all_positions_rounds_palettes_and_private_boundaries(
    tmp_path: Path,
) -> None:
    context = _ready_context(tmp_path)
    state = build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
        selected_position=1,
    )
    assert state["match_capture_web_protocol_version"] == 1
    assert len(state["slots"]) == 36
    assert len(state["card_palette"]) == 32
    assert state["position_view"]["card_selection_scope"] == (
        "bounded_observation_candidates"
    )
    html = render_match_capture_web_page_v1(state)
    assert html.count('class="round"') == 12
    assert "Observed-card candidates; ownership may be unknown" in html
    assert "Exact legal cards" not in html
    assert "Commentary and Response Links" in html
    assert "data-undo-form" in html
    assert html.count('class="setup-card ') == 96
    assert "Record blockers" in html
    assert "Evidence Summary" in html
    assert "Workspace Progress" in html
    assert str(context.workspace_path.resolve()) not in html
    assert context.content_fingerprint not in html
    assert "workspace_fingerprint" not in html
    assert "content_fingerprint" not in html
    assert "Traceback" not in html
    assert "youtube.com/embed" not in html
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html


def test_exact_card_palette_is_labeled_without_claiming_bounded_candidates(
    tmp_path: Path,
) -> None:
    context = _ready_context(tmp_path)
    assert context.workspace is not None
    hand = "CA C10 CK CQ CJ C9 C8 C7 SA S10"
    saved = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "set_perspective_hand",
            card_evidence_mode="exact",
            cards=hand,
        ),
    )
    assert saved.status == "applied"
    first = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "append_plays", cards="H7", decision_timecode=""),
    )
    assert first.status == "applied"
    second = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "append_plays", cards="D7", decision_timecode=""),
    )
    assert second.status == "applied"
    assert second.state["position_view"]["next_player_id"] == "player-a"
    assert second.state["position_view"]["card_selection_scope"] == "exact_legal_cards"
    html = render_match_capture_web_page_v1(second.state)
    assert "Exact legal cards" in html
    assert "Observed-card candidates; ownership may be unknown" not in html


def _request(
    server,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection(MATCH_CAPTURE_WEB_BIND_HOST, server.port)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    response_body = response.read()
    response_headers = {name.lower(): value for name, value in response.getheaders()}
    connection.close()
    return response.status, response_headers, response_body


@pytest.fixture
def running_server(tmp_path: Path):
    context = MatchCaptureWebContextV1.open(tmp_path / "web-match.json")
    server = start_match_capture_web_server_v1(context, port=0, token="fixed-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, context
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _bootstrap(server) -> tuple[dict[str, str], dict[str, str]]:
    status, headers, body = _request(
        server,
        "GET",
        "/?token=fixed-token",
        headers={"Host": f"127.0.0.1:{server.port}"},
    )
    assert status == 303 and body == b""
    assert headers["location"] == "/"
    cookie = headers["set-cookie"]
    assert cookie.startswith(f"{MATCH_CAPTURE_WEB_COOKIE_NAME}=fixed-token;")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    return (
        {
            "Host": f"127.0.0.1:{server.port}",
            "Cookie": cookie.split(";", 1)[0],
        },
        {
            "Host": f"127.0.0.1:{server.port}",
            "Cookie": cookie.split(";", 1)[0],
            "Origin": f"http://127.0.0.1:{server.port}",
        },
    )


def test_server_binds_loopback_and_token_bootstrap_protects_routes(running_server) -> None:
    server, _context = running_server
    assert server.server_address[0] == "127.0.0.1"
    parsed = urlsplit(server.bootstrap_url)
    assert parsed.hostname == "127.0.0.1"
    assert parsed.query == "token=fixed-token"

    status, _headers, _body = _request(
        server,
        "GET",
        "/",
        headers={"Host": f"127.0.0.1:{server.port}"},
    )
    assert status == 403
    status, _headers, _body = _request(
        server,
        "GET",
        "/?token=wrong",
        headers={"Host": f"127.0.0.1:{server.port}"},
    )
    assert status == 403
    get_headers, _post_headers = _bootstrap(server)
    status, headers, body = _request(server, "GET", "/", headers=get_headers)
    assert status == 200
    assert b"Create web-match.json" in body
    assert b"fixed-token" not in body
    assert "access-control-allow-origin" not in headers


def test_host_cookie_origin_request_limit_and_security_headers(running_server) -> None:
    server, _context = running_server
    status, _headers, _body = _request(
        server,
        "GET",
        "/?token=fixed-token",
        headers={"Host": "example.test"},
    )
    assert status == 403
    get_headers, post_headers = _bootstrap(server)
    status, headers, _body = _request(server, "GET", "/", headers=get_headers)
    assert status == 200
    assert headers["cache-control"] == "no-store"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["x-frame-options"] == "DENY"
    assert headers["content-security-policy"] == (
        MATCH_CAPTURE_WEB_CONTENT_SECURITY_POLICY
    )
    assert headers["permissions-policy"] == MATCH_CAPTURE_WEB_PERMISSIONS_POLICY

    form = urlencode(_creation_values()).encode()
    missing_origin = dict(get_headers)
    missing_origin["Content-Type"] = "application/x-www-form-urlencoded"
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/create",
        headers=missing_origin,
        body=form,
    )
    assert status == 403
    cross_origin = dict(post_headers)
    cross_origin["Origin"] = "http://evil.example"
    cross_origin["Content-Type"] = "application/x-www-form-urlencoded"
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/create",
        headers=cross_origin,
        body=form,
    )
    assert status == 403
    host_mismatch = dict(post_headers)
    host_mismatch["Origin"] = f"http://localhost:{server.port}"
    host_mismatch["Content-Type"] = "application/x-www-form-urlencoded"
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/create",
        headers=host_mismatch,
        body=form,
    )
    assert status == 403

    too_large = dict(post_headers)
    too_large["Content-Type"] = "application/x-www-form-urlencoded"
    too_large["Content-Length"] = str(MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES + 1)
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/create",
        headers=too_large,
        body=b"",
    )
    assert status == 413


def test_asset_allowlist_traversal_unknown_routes_and_methods(running_server) -> None:
    server, _context = running_server
    get_headers, post_headers = _bootstrap(server)
    for path, marker in (
        ("/assets/capture.css", b"--green"),
        ("/assets/capture.js", b"focusKey"),
    ):
        status, _headers, body = _request(server, "GET", path, headers=get_headers)
        assert status == 200 and marker in body
        assert b"https://" not in body
        assert b"http://" not in body
    for path in (
        "/assets/missing.css",
        "/assets/../templates/page.html",
        "/unknown",
    ):
        status, _headers, _body = _request(server, "GET", path, headers=get_headers)
        assert status == 404
    status, headers, _body = _request(server, "PUT", "/", headers=get_headers)
    assert status == 405
    assert headers["allow"] == "GET, POST"
    status, headers, _body = _request(
        server,
        "GET",
        "/api/v1/create",
        headers=get_headers,
    )
    assert status == 405
    assert headers["allow"] == "GET, POST"
    status, headers, _body = _request(server, "POST", "/", headers=post_headers)
    assert status == 405
    assert headers["allow"] == "GET, POST"
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/create?unexpected=true",
        headers=post_headers,
    )
    assert status == 403


def test_no_javascript_html_form_creation_game_declaration_card_and_undo(
    running_server,
) -> None:
    server, context = running_server
    get_headers, post_headers = _bootstrap(server)
    form_headers = {
        **post_headers,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    status, _headers, body = _request(
        server,
        "POST",
        "/api/v1/create",
        headers=form_headers,
        body=urlencode(_creation_values()).encode(),
    )
    assert status == 303 and body == b""
    status, _headers, body = _request(
        server,
        "GET",
        "/position/1",
        headers=get_headers,
    )
    assert status == 200 and b"Change saved." in body
    assert context.workspace is not None and context.workspace_path.is_file()

    def post_operation(values: dict[str, object]) -> bytes:
        status, response_headers, response_body = _request(
            server,
            "POST",
            "/api/v1/operation",
            headers=form_headers,
            body=urlencode(values).encode(),
        )
        assert status == 303 and response_body == b""
        status, _headers, response_body = _request(
            server,
            "GET",
            response_headers["location"],
            headers=get_headers,
        )
        assert status == 200
        return response_body

    body = post_operation(_operation_values(context, "start_game"))
    assert b"Declaration" in body
    body = post_operation(
        _operation_values(
            context,
            "set_declaration",
            declarer_player_id="player-b",
            game_type="grand",
            hand_game="",
            ouvert="",
            schneider_announced="",
            schwarz_announced="",
            matadors="",
            bid_value="24",
        )
    )
    assert b"Observed-card candidates; ownership may be unknown" in body
    body = post_operation(
        _operation_values(context, "append_plays", cards="CA", decision_timecode="")
    )
    assert b"Undo last Play" in body
    body = post_operation(
        _operation_values(context, "truncate_plays", target_play_count="0")
    )
    assert b"No Plays retained." in body

    status, _headers, state_body = _request(
        server,
        "GET",
        "/api/v1/state",
        headers=get_headers,
    )
    state = json.loads(state_body)
    assert status == 200
    assert state["workspace_exists"] is True
    assert "content_fingerprint" not in state_body.decode()
    assert "fixed-token" not in state_body.decode()
    assert str(context.workspace_path.resolve()) not in state_body.decode()


def test_json_transport_and_duplicate_json_keys(running_server) -> None:
    server, context = running_server
    _get_headers, post_headers = _bootstrap(server)
    json_headers = {**post_headers, "Content-Type": "application/json"}
    status, _headers, body = _request(
        server,
        "POST",
        "/api/v1/create",
        headers=json_headers,
        body=json.dumps(_creation_values()).encode(),
    )
    assert status == 200
    result = json.loads(body)
    assert result["status"] == "applied"
    assert context.workspace is not None

    status, _headers, body = _request(
        server,
        "POST",
        "/api/v1/operation",
        headers=json_headers,
        body=b'{"operation":"start_game","operation":"clear_position"}',
    )
    assert status == 400
    assert b"Duplicate JSON object key" in body


def test_repeated_card_form_fields_support_setup_palette(running_server) -> None:
    server, context = running_server
    _get_headers, post_headers = _bootstrap(server)
    form_headers = {
        **post_headers,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/create",
        headers=form_headers,
        body=urlencode(_creation_values()).encode(),
    )
    assert status == 303
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/operation",
        headers=form_headers,
        body=urlencode(_operation_values(context, "start_game")).encode(),
    )
    assert status == 303
    cards = ("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10")
    values = _operation_values(
        context,
        "set_perspective_hand",
        card_evidence_mode="exact",
    )
    body = urlencode([*values.items(), *(("cards", card) for card in cards)]).encode()
    status, _headers, _body = _request(
        server,
        "POST",
        "/api/v1/operation",
        headers=form_headers,
        body=body,
    )
    assert status == 303
    assert context.workspace.slots[0].observed_game.perspective_initial_hand == cards


def test_generic_internal_failure_exposes_no_stack_trace_or_exception(
    running_server,
    monkeypatch,
) -> None:
    server, _context = running_server
    get_headers, _post_headers = _bootstrap(server)

    def failure(*_args, **_kwargs):
        raise RuntimeError("private internal details")

    monkeypatch.setattr(
        "skat_ai.capture_web.server.build_match_capture_web_state_v1",
        failure,
    )
    status, _headers, body = _request(server, "GET", "/", headers=get_headers)
    assert status == 500
    assert body == b"Internal server error"
    assert b"private internal details" not in body
    assert b"Traceback" not in body


def test_server_access_logging_is_disabled_and_token_is_not_persisted(
    running_server,
    capsys,
) -> None:
    server, context = running_server
    get_headers, _post_headers = _bootstrap(server)
    _request(server, "GET", "/", headers=get_headers)
    captured = capsys.readouterr()
    assert "fixed-token" not in captured.out
    assert "fixed-token" not in captured.err
    assert context.workspace is None


def test_operations_execute_no_root_session_analysis_materialization_or_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _ready_context(tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Forbidden workflow or external network path executed.")

    monkeypatch.setattr(
        "skat_ai.application.execution.execute_application_invocation",
        forbidden,
    )
    monkeypatch.setattr("socket.create_connection", forbidden)
    result = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "append_plays", cards="CA", decision_timecode=""),
    )
    assert result.status == "applied"


def test_existing_capture_services_remain_authoritative_for_player_and_decision() -> None:
    workspace = create_match_workspace_v1(_definition())
    workspace = start_match_capture_game_v1(
        workspace,
        match_position=1,
        expected_revision=0,
    ).workspace_change.workspace
    workspace = set_match_capture_declaration_v1(
        workspace,
        match_position=1,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    result = append_match_capture_plays_v1(
        workspace,
        match_position=1,
        entries=(
            MatchCaptureCardEntryV1(card="CA", decision_timecode=None),
            MatchCaptureCardEntryV1(card="S7", decision_timecode=None),
        ),
        expected_revision=workspace.revision,
    )
    assert tuple(
        (play.decision_index, play.player_id)
        for play in result.workspace_change.workspace.slots[0].observed_game.plays
    ) == ((1, "player-b"), (2, "player-c"))
