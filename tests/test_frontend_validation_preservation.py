from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from skatmind.app_web.form_parsing import FormValuesV1, FormValueV1
from skatmind.app_web.form_registry import (
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
    capture_safe_submitted_values_v1,
    resolve_frontend_form_v1,
    validate_frontend_form_registry_v1,
)
from skatmind.app_web.form_state import ProcessLocalFrontendFeedbackStateV1
from skatmind.app_web.validation_contracts import (
    FRONTEND_VALIDATION_PRESERVATION_VERSION,
    FrontendSubmittedFormStateV1,
    FrontendValidationIssueV1,
)
from skatmind.app_web.validation_mapping import map_frontend_exception_v1
from skatmind.app_web.validation_rendering import (
    apply_validation_feedback_to_html_v1,
    instrument_registered_forms_v1,
)
from skatmind.corpus_web.rendering import render_learning_corpus_web_body_v1


def _issue(field: str | None = "game_type") -> FrontendValidationIssueV1:
    return FrontendValidationIssueV1(
        field_key=field,
        message_key="validation.message.choice",
    )


def _state(
    *,
    form_key: str = "analyze.run_guided",
    family: str = "analyze",
    values: FormValuesV1 | None = None,
    instance: int | None = None,
    status: str = "invalid",
) -> FrontendSubmittedFormStateV1:
    return FrontendSubmittedFormStateV1(
        contract_version=FRONTEND_VALIDATION_PRESERVATION_VERSION,
        form_key=form_key,
        originating_route="/actions/analyze/run-guided",
        active_family_binding=family,
        review_wizard_step=None,
        form_instance=instance,
        safe_visible_values=values or FormValuesV1(),
        validation_issues=(_issue(),),
        status=status,
        feedback_generation=1,
    )


def test_validation_contract_and_registry_coverage_are_exact() -> None:
    assert FRONTEND_VALIDATION_PRESERVATION_VERSION == 1
    assert len(UNIFIED_FRONTEND_POST_ROUTES) == 44
    assert len(FRONTEND_FORM_REGISTRY) == 77
    assert {form.action_route for form in FRONTEND_FORM_REGISTRY} == set(
        UNIFIED_FRONTEND_POST_ROUTES
    )
    validate_frontend_form_registry_v1()

    assert {
        form.discriminator_value
        for form in FRONTEND_FORM_REGISTRY
        if form.action_route == "/sessions/command"
    } == {
        "set_game_metadata",
        "record_dealt_card",
        "set_declarer",
        "set_declaration",
        "record_discard",
        "record_play",
        "set_public_hand",
        "set_game_event",
        "set_game_end",
        "promote_to_retrospective",
    }
    with pytest.raises(ValueError, match="discriminator"):
        resolve_frontend_form_v1("/sessions/command", {"kind": "unsupported"})
    with pytest.raises(ValueError, match="discriminator"):
        resolve_frontend_form_v1("/learning/api/v1/operations")
    with pytest.raises(ValueError, match="media type"):
        resolve_frontend_form_v1(
            "/learning/api/v1/operations",
            {"operation": "import_match_workspace"},
            media_type="application/x-www-form-urlencoded",
        )
    assert (
        resolve_frontend_form_v1(
            "/learning/api/v1/operations",
            {"operation": "import_match_workspace"},
            media_type="multipart/form-data",
        ).form_key
        == "learning.operation.import_match_workspace"
    )

    metadata = resolve_frontend_form_v1(
        "/matches/api/v1/operation",
        {"operation": "update_match_metadata"},
    )
    assert tuple(field.field_key for field in metadata.safe_fields) == (
        "title",
        "game_platform",
        "external_match_id",
        "played_at",
        "source_kind",
        "source_url",
        "source_title",
        "source_channel_name",
        "match_timecode_start",
        "match_timecode_end",
        "player_1_label",
        "player_1_platform_id",
        "player_2_label",
        "player_2_platform_id",
        "player_3_label",
        "player_3_platform_id",
    )


def test_validation_contracts_are_immutable_and_strict() -> None:
    issue = _issue()
    state = _state()
    with pytest.raises(FrozenInstanceError):
        issue.message_key = "validation.message.required"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.status = "conflict"  # type: ignore[misc]
    with pytest.raises(ValueError, match="translation key"):
        FrontendValidationIssueV1(field_key=None, message_key="raw error")


def test_safe_capture_is_allowlisted_bounded_and_clears_omitted_groups() -> None:
    definition = resolve_frontend_form_v1("/actions/analyze/run-guided")
    captured = capture_safe_submitted_values_v1(
        definition,
        {
            "analysis_mode": ["live_decision"],
            "game_type": ["grand"],
            "bid_value": ["18"],
            "hand_game": ["on"],
            "request_file": ["private.json"],
            "managed_handle": ["not-safe"],
            "revision": ["99"],
        },
    )
    assert captured.singular("analysis_mode") == "live_decision"
    assert captured.singular("game_type") == "grand"
    assert captured.singular("bid_value") == "18"
    assert captured.singular("hand_game") == "on"
    assert captured.all("hand") == ("",)
    assert not captured.contains("request_file")
    assert not captured.contains("managed_handle")
    assert not captured.contains("revision")

    rejected = capture_safe_submitted_values_v1(
        definition,
        {
            "analysis_mode": ["unsupported"],
            "game_type": ["<script>"],
            "bid_value": ["x" * 2049],
        },
    )
    assert rejected.singular("analysis_mode") is None
    assert rejected.singular("game_type") is None
    assert rejected.singular("bid_value") is None


def test_maximum_valid_platform_identifier_text_is_retained() -> None:
    definition = resolve_frontend_form_v1("/actions/profile/players/add")
    platform_ids = "\n".join(
        f"{'p' * 120} = {index:02d}-{'x' * 252}" for index in range(16)
    )
    assert 4096 < len(platform_ids) <= 8192
    captured = capture_safe_submitted_values_v1(
        definition,
        {
            "display_name": ["Anna"],
            "aliases": [""],
            "platform_player_ids": [platform_ids],
            "profile_generation": ["0"],
        },
    )
    assert captured.singular("platform_player_ids") == platform_ids


def test_file_and_destructive_values_are_never_retained() -> None:
    upload = resolve_frontend_form_v1("/sessions/import")
    assert upload.file_reselection_behavior == "required"
    assert (
        capture_safe_submitted_values_v1(
            upload,
            {"session_file": ["C:/private/session.json"]},
        )
        == FormValuesV1()
    )

    reset = resolve_frontend_form_v1("/actions/analyze/reset")
    assert tuple(field.field_key for field in reset.safe_fields) == ("confirm_reset",)
    assert (
        capture_safe_submitted_values_v1(
            reset,
            {"confirm_reset": ["on"]},
        )
        == FormValuesV1()
    )


def test_registry_uses_form_specific_session_and_match_controls() -> None:
    declaration = resolve_frontend_form_v1(
        "/sessions/command",
        {"kind": "set_declaration"},
    )
    declaration_fields = {field.field_key: field for field in declaration.safe_fields}
    assert declaration_fields["hand_game"].control_type == "select"
    assert declaration_fields["hand_game"].allowed_values == ("false", "true")

    public_hand = resolve_frontend_form_v1(
        "/sessions/command",
        {"kind": "set_public_hand"},
    )
    cards = {field.field_key: field for field in public_hand.safe_fields}["cards"]
    assert cards.control_type == "text"
    assert cards.cardinality == "single"

    evidence = resolve_frontend_form_v1(
        "/matches/api/v1/operation",
        {"operation": "set_perspective_hand"},
    )
    evidence_fields = {field.field_key: field for field in evidence.safe_fields}
    assert evidence_fields["card_evidence_mode"].control_type == "radio"
    assert evidence_fields["card_evidence_mode"].allowed_values == (
        "unknown",
        "exact",
    )
    assert evidence_fields["cards"].control_type == "card"
    assert evidence_fields["cards"].cardinality == "repeated"

    appended_plays = resolve_frontend_form_v1(
        "/matches/api/v1/operation",
        {"operation": "append_plays"},
    )
    assert {field.field_key: field for field in appended_plays.safe_fields}[
        "cards"
    ].control_type == "text"
    assert {field.field_key: field for field in appended_plays.safe_fields}[
        "cards"
    ].cardinality == "single"

    game_end = resolve_frontend_form_v1(
        "/sessions/command",
        {"kind": "set_game_end"},
    )
    game_end_fields = {field.field_key: field for field in game_end.safe_fields}
    assert game_end_fields["game_end_reason"].control_type == "select"
    assert game_end_fields["player_id"].control_type == "select"


def test_registry_preserves_exact_visible_select_and_card_controls() -> None:
    analyze = resolve_frontend_form_v1("/actions/analyze/run-guided")
    analyze_fields = {field.field_key: field for field in analyze.safe_fields}
    assert analyze_fields["completed_trick_1_leader"].control_type == "select"
    assert analyze_fields["completed_trick_1_leader"].allowed_values == (
        "",
        "me",
        "left",
        "right",
    )
    assert analyze_fields["completed_trick_1_card_1"].control_type == "card"
    assert analyze_fields["actual_card_played"].control_type == "card"

    match_declaration = resolve_frontend_form_v1(
        "/matches/api/v1/operation",
        {"operation": "set_declaration"},
    )
    assert {field.field_key: field for field in match_declaration.safe_fields}[
        "declarer_player_id"
    ].control_type == "select"

    match_analysis = resolve_frontend_form_v1(
        "/matches/api/v1/analysis",
        {"operation": "analyze_decision"},
    )
    assert {field.field_key: field for field in match_analysis.safe_fields}[
        "decision_index"
    ].control_type == "select"

    report_transfer = resolve_frontend_form_v1("/matches/transfer-report")
    assert {field.field_key: field for field in report_transfer.safe_fields}[
        "match_snapshot_id"
    ].control_type == "select"

    report_import = resolve_frontend_form_v1(
        "/learning/api/v1/operations",
        {"operation": "import_strategy_teacher_report"},
    )
    assert {field.field_key: field for field in report_import.safe_fields}[
        "match_snapshot_id"
    ].control_type == "select"


def test_hidden_learning_snapshot_identity_is_not_safe_visible_state() -> None:
    definition = resolve_frontend_form_v1(
        "/learning/api/v1/operations",
        {"operation": "select_current_snapshot"},
    )
    assert definition.value_free is True
    assert definition.safe_fields == ()
    assert (
        capture_safe_submitted_values_v1(
            definition,
            {
                "match_id": ["private-match"],
                "match_snapshot_id": ["private-snapshot"],
            },
        )
        == FormValuesV1()
    )


def test_unified_corpus_adapter_rejects_standalone_initialization_state() -> None:
    with pytest.raises(ValueError, match="requires an initialized Corpus"):
        render_learning_corpus_web_body_v1(
            {"initialized": False},
            route_prefix="/learning",
        )


def test_feedback_store_is_bounded_and_active_identity_safe() -> None:
    store = ProcessLocalFrontendFeedbackStateV1()
    first_identity = object()
    second_identity = object()
    state = _state(form_key="session.create", family="sessions")
    store.retain("sessions", state, active_identity=first_identity)
    assert store.retained_family_count == 1
    assert store.current("sessions", active_identity=first_identity) is state
    assert store.current("sessions", active_identity=second_identity) is None
    assert store.retained_family_count == 0

    store.retain("analyze", _state(), active_identity=None)
    store.retain("review", _state(family="review"), active_identity=None)
    assert store.retained_family_count == 2
    store.clear("analyze")
    assert store.retained_family_count == 1


def test_safe_mapping_never_retains_raw_exception_text() -> None:
    definition = resolve_frontend_form_v1("/sessions/create")
    secret = "private path C:/Users/example/token-123"
    issues = map_frontend_exception_v1(ValueError(secret), definition, status=400)
    assert issues == (
        FrontendValidationIssueV1(
            field_key=None,
            message_key="validation.message.product_rejected",
        ),
    )
    assert secret not in repr(issues)


def test_rendering_preserves_values_localizes_and_targets_exact_form_instance() -> None:
    definition = resolve_frontend_form_v1("/actions/analyze/run-guided")
    html = (
        '<form action="/actions/analyze/run-guided">'
        '<select id="first-game-type" name="game_type"><option value="grand">Grand</option>'
        '<option value="null" selected>Null</option></select></form>'
        '<form action="/actions/analyze/run-guided">'
        '<select id="second-game-type" name="game_type"><option value="grand">Grand</option>'
        '<option value="null" selected>Null</option></select></form>'
    )
    instrumented = instrument_registered_forms_v1(html, FRONTEND_FORM_REGISTRY)
    assert instrumented.count('name="_frontend_form_instance"') == 2
    state = _state(
        values=FormValuesV1((FormValueV1("game_type", ("grand",)),)),
        instance=1,
    )
    rendered = apply_validation_feedback_to_html_v1(
        instrumented,
        definition,
        state,
        locale="de",
    )
    assert rendered.count('class="error-summary"') == 1
    assert "Prüfen Sie das ausgefüllte Formular" in rendered
    assert 'aria-invalid="true"' in rendered
    assert 'aria-describedby="validation-message-1-1"' in rendered
    assert 'href="#second-game-type"' in rendered
    assert 'id="validation-form-heading-1"' in rendered
    assert rendered.index('value="null" selected') < rendered.index("error-summary")
    assert rendered.rindex('value="grand" selected') > rendered.index("error-summary")


def test_player_feedback_uses_opaque_handle_instead_of_stale_form_ordinal() -> None:
    definition = resolve_frontend_form_v1("/actions/profile/players/update")
    handle = "b" * 64
    html = (
        '<main id="main-content"><form action="/actions/profile/players/update">'
        f'<input type="hidden" name="player_handle" value="{handle}">'
        '<label>Name <input name="display_name" value="Current"></label>'
        "</form></main>"
    )
    state = FrontendSubmittedFormStateV1(
        contract_version=FRONTEND_VALIDATION_PRESERVATION_VERSION,
        form_key="profile.player_update",
        originating_route="/actions/profile/players/update",
        active_family_binding="local_settings",
        review_wizard_step=None,
        form_instance=1,
        safe_visible_values=FormValuesV1(
            (
                FormValueV1("display_name", ("Retained",)),
                FormValueV1("player_handle", (handle,)),
            )
        ),
        validation_issues=(
            FrontendValidationIssueV1(
                field_key="display_name",
                message_key="validation.message.stale",
            ),
        ),
        status="conflict",
        feedback_generation=2,
    )
    rendered = apply_validation_feedback_to_html_v1(
        html,
        definition,
        state,
        locale="en",
    )
    assert 'name="display_name" value="Retained" aria-invalid="true"' in rendered
    assert rendered.count('class="error-summary"') == 1

    missing = apply_validation_feedback_to_html_v1(
        '<main id="main-content"><p>No matching Player remains.</p></main>',
        definition,
        state,
        locale="en",
    )
    assert missing.count('class="error-summary"') == 1
    assert "No matching Player remains." in missing


def test_repeated_select_values_keep_their_submitted_order() -> None:
    definition = resolve_frontend_form_v1("/actions/analyze/run-guided")
    html = (
        '<form action="/actions/analyze/run-guided">'
        '<select name="current_trick"><option value="">-</option>'
        '<option value="CA">CA</option><option value="C10">C10</option></select>'
        '<select name="current_trick"><option value="">-</option>'
        '<option value="CA">CA</option><option value="C10">C10</option></select>'
        "</form>"
    )
    state = _state(
        values=FormValuesV1((FormValueV1("current_trick", ("CA", "C10")),)),
    )
    rendered = apply_validation_feedback_to_html_v1(
        html,
        definition,
        state,
        locale="en",
    )
    assert rendered.index('value="CA" selected') < rendered.index('value="C10" selected')
