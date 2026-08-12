from dataclasses import replace
from pathlib import Path

import pytest
from test_local_match_capture_web import (
    _create_context,
    _creation_values,
    _operation_values,
)
from test_match_capture_contracts import _statistics_record

import skat_ai.capture_web.operations as operations_module
from skat_ai.capture_web.context import MatchCaptureWebContextV1
from skat_ai.capture_web.operations import (
    apply_match_capture_web_operation_v1,
    create_match_capture_workspace_v1,
)
from skat_ai.capture_web.rendering import render_match_capture_web_page_v1
from skat_ai.capture_web.state import build_match_capture_web_state_v1
from skat_ai.match_player_statistics_updates import (
    set_match_player_statistics_snapshot_v1,
)
from skat_ai.match_workspace_persistence import save_match_workspace_file_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _statistics_values(
    context: MatchCaptureWebContextV1,
    *,
    player_id: str = "player-a",
    source_type: str = "manual_entry",
    snapshot_id: str = "",
    observed_at: str = "2026-07-20T10:00:00Z",
    exact_counts: bool = False,
    **overrides: object,
) -> dict[str, object]:
    values = _operation_values(
        context,
        "set_player_statistics_snapshot",
        player_id=player_id,
        snapshot_id=snapshot_id,
        observed_at=observed_at,
        source_type=source_type,
        source_name=("Local observation" if source_type == "manual_entry" else "Platform"),
        source_player_id="source-player-a",
        notes="Match-bound profile evidence",
        games_played="127",
        solo_games_played_percent="31",
        solo_games_won_percent="58",
        solo_hand_percent="12",
        suit_games_percent="61",
        grand_games_percent="29",
        null_games_percent="10",
        defender_games_played_percent="69",
        defender_games_won_percent="64",
    )
    if exact_counts:
        values.update(
            solo_games_played="40",
            solo_games_won="23",
            solo_hand_games="5",
            suit_games="24",
            grand_games="12",
            null_games="4",
            defender_games_played="87",
            defender_games_won="56",
        )
    values.update(overrides)
    return values


def _metadata_values(
    context: MatchCaptureWebContextV1,
    *,
    played_at: str,
) -> dict[str, object]:
    return _operation_values(
        context,
        "update_match_metadata",
        title="36er Finals Table",
        game_platform="EuroSkat",
        external_match_id="external-165",
        played_at=played_at,
        source_kind="youtube_video",
        source_url="https://www.youtube.com/watch?v=example",
        source_title="Finals recording",
        source_channel_name="Tournament channel",
        match_timecode_start="01:02:03.500",
        match_timecode_end="02:12:00",
        player_1_label="Alice",
        player_1_platform_id="platform-a",
        player_2_label="Bob",
        player_2_platform_id="platform-b",
        player_3_label="Carol",
        player_3_platform_id="platform-c",
    )


@pytest.mark.parametrize("source_type", ("manual_entry", "online_platform"))
def test_browser_sets_each_supported_source_with_all_percentages(
    tmp_path: Path,
    source_type: str,
) -> None:
    context = _create_context(tmp_path)
    result = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context, source_type=source_type),
    )
    assert result.status == "applied"
    assert context.workspace is not None
    snapshot = context.workspace.match_definition.participants[0].statistics_snapshot
    assert snapshot.snapshot_id == "capture-web-match-player-a-statistics-r1"
    record = snapshot.statistics_record
    assert record.player_id == "player-a"
    assert record.player_label == "Alice"
    assert record.source.source_type == source_type
    assert record.source.source_player_id == "source-player-a"
    assert record.source.notes == "Match-bound profile evidence"
    assert record.games_played == 127
    assert record.statistics.__dict__ == {
        "solo_games_played_percent": 31,
        "solo_games_won_percent": 58,
        "solo_hand_percent": 12,
        "suit_games_percent": 61,
        "grand_games_percent": 29,
        "null_games_percent": 10,
        "defender_games_played_percent": 69,
        "defender_games_won_percent": 64,
    }
    assert record.exact_counts is None
    participant = result.state["participants"][0]
    assert participant["statistics_source"]["source_type"] == source_type
    assert participant["statistics_games_played"] == 127
    assert participant["statistics_temporal_status"] == "eligible"
    assert participant["statistics_eligible_for_match_analysis"] is True
    assert participant["normalized_profile"]["solo_rate"] == 0.31
    assert participant["profile_confidence"]["overall"]["level"] == "medium"
    assert participant["profile_classification"] == "aggressive"
    assert participant["profile_derivation_status"] == "insufficient_confidence"
    assert participant["recommended_policy_preset"] == "aggressive_points"
    assert participant["actionable_policy_preset"] is None
    assert participant["profile_explanations"]


def test_browser_complete_exact_counts_are_reused_and_partial_set_is_rejected(
    tmp_path: Path,
) -> None:
    context = _create_context(tmp_path)
    complete = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context, exact_counts=True),
    )
    assert complete.status == "applied"
    participant = complete.state["participants"][0]
    assert participant["statistics_exact_counts"] == {
        "solo_games_played": 40,
        "solo_games_won": 23,
        "solo_hand_games": 5,
        "suit_games": 24,
        "grand_games": 12,
        "null_games": 4,
        "defender_games_played": 87,
        "defender_games_won": 56,
    }
    assert participant["normalized_profile"]["solo_rate"] == 40 / 127
    assert participant["profile_confidence"]["declarer"]["evidence_kind"] == "exact"

    partial_context = MatchCaptureWebContextV1.open(tmp_path / "partial.json")
    create_match_capture_workspace_v1(partial_context, _creation_values())
    before = partial_context.workspace
    values = _statistics_values(partial_context, solo_games_played="40")
    with pytest.raises(ValueError, match="solo_games_won must be an integer"):
        apply_match_capture_web_operation_v1(partial_context, values)
    assert partial_context.workspace is before


def test_browser_rejects_historical_source_construction_and_invalid_percentage(
    tmp_path: Path,
) -> None:
    context = _create_context(tmp_path)
    with pytest.raises(ValueError, match="manual_entry or online_platform"):
        apply_match_capture_web_operation_v1(
            context,
            _statistics_values(context, source_type="historical_games"),
        )
    with pytest.raises(ValueError, match="contract-distribution percentages"):
        apply_match_capture_web_operation_v1(
            context,
            _statistics_values(context, grand_games_percent="80"),
        )
    assert context.workspace.revision == 0


def test_replace_equal_clear_and_no_save_outcomes(tmp_path: Path, monkeypatch) -> None:
    context = _create_context(tmp_path)
    applied = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context),
    )
    assert applied.status == "applied"
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
    unchanged = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(
            context,
            observed_at="2026-07-20T12:00:00+02:00",
        ),
    )
    assert unchanged.status == "unchanged"
    assert calls == 0
    original_id = unchanged.state["participants"][0]["statistics_snapshot"][
        "snapshot_id"
    ]
    assert original_id == "capture-web-match-player-a-statistics-r1"

    replaced = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(
            context,
            source_type="online_platform",
            snapshot_id="replacement-snapshot",
        ),
    )
    assert replaced.status == "applied"
    assert calls == 1
    assert replaced.state["participants"][0]["statistics_snapshot"][
        "snapshot_id"
    ] == "replacement-snapshot"
    cleared = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "clear_player_statistics_snapshot",
            player_id="player-a",
            confirm_clear_snapshot="true",
        ),
    )
    assert cleared.status == "applied"
    assert calls == 2
    unchanged_clear = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "clear_player_statistics_snapshot",
            player_id="player-a",
            confirm_clear_snapshot="true",
        ),
    )
    assert unchanged_clear.status == "unchanged"
    assert calls == 2


def test_revision_conflict_precedes_form_semantics_and_does_not_save(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _create_context(tmp_path)
    monkeypatch.setattr(
        MatchCaptureWebContextV1,
        "save_candidate",
        lambda _self, _workspace: pytest.fail("stale Snapshot update attempted Save"),
    )
    result = apply_match_capture_web_operation_v1(
        context,
        {
            "operation": "set_player_statistics_snapshot",
            "match_position": "1",
            "expected_revision": "99",
            "player_id": "player-a",
            "observed_at": "invalid",
            "source_type": "historical_games",
        },
    )
    assert result.status == "revision_conflict"


def test_historical_snapshot_is_complete_read_only_clearable_and_replaceable(
    tmp_path: Path,
) -> None:
    context = _create_context(tmp_path)
    assert context.workspace is not None
    update = set_match_player_statistics_snapshot_v1(
        context.workspace,
        player_id="player-a",
        observed_at="2026-07-20T19:00:00+02:00",
        statistics_record=_statistics_record("player-a", "historical_games"),
        expected_revision=0,
    )
    assert context.save_candidate(update.workspace_change.workspace) == "saved"
    state = build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
    )
    player = state["participants"][0]
    assert player["statistics_source"]["source_type"] == "historical_games"
    assert player["statistics_source"]["historical_aggregation"] is not None
    html = render_match_capture_web_page_v1(state)
    assert "Historical aggregation:" in html
    assert "retained read-only" in html
    assert "Source record IDs" in html
    assert "Source Game IDs" in html
    assert "record-1" in html
    assert "game-1" in html
    assert '<option value="historical_games"' not in html
    assert "Replace Snapshot" in html
    assert "Clear Snapshot" in html

    replaced = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context, source_type="manual_entry"),
    )
    assert replaced.status == "applied"
    assert replaced.state["participants"][0]["statistics_source"][
        "source_type"
    ] == "manual_entry"


def test_state_and_html_present_all_temporal_profile_and_form_boundaries(
    tmp_path: Path,
) -> None:
    context = _create_context(tmp_path)
    state = build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
    )
    html = render_match_capture_web_page_v1(state)
    assert html.count('class="panel statistics-card"') == 3
    assert html.count('name="source_type"') == 3
    assert html.count('name="solo_games_played_percent"') == 3
    assert html.count('name="defender_games_won_percent"') == 3
    assert html.count('name="solo_games_played"') == 3
    assert html.count('name="defender_games_won"') == 3
    assert "one immutable Match-bound Snapshot" in html
    assert "A later Match may retain another Snapshot" in html
    assert "Missing Match time" in html
    assert "equal or later captures remain descriptive" in html
    assert "Prepared Profiles are not yet applied to Match analysis" in html
    assert "Add Snapshot" in html
    assert state["player_statistics_preparation"]["status"] == "unavailable"


def test_match_time_metadata_changes_recompute_status_without_mutating_snapshot(
    tmp_path: Path,
) -> None:
    context = _create_context(tmp_path)
    applied = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context),
    )
    snapshot_before = context.workspace.match_definition.participants[
        0
    ].statistics_snapshot
    assert applied.state["participants"][0]["statistics_temporal_status"] == "eligible"

    missing = apply_match_capture_web_operation_v1(
        context,
        _metadata_values(context, played_at=""),
    )
    assert missing.status == "applied"
    assert missing.state["participants"][0]["statistics_temporal_status"] == (
        "match_time_unavailable"
    )
    assert context.workspace.match_definition.participants[0].statistics_snapshot == (
        snapshot_before
    )
    assert context.workspace.revision == 2

    equal = apply_match_capture_web_operation_v1(
        context,
        _metadata_values(context, played_at="2026-07-20T12:00:00+02:00"),
    )
    assert equal.status == "applied"
    assert equal.state["participants"][0]["statistics_temporal_status"] == (
        "captured_not_before_match"
    )
    assert context.workspace.match_definition.participants[0].statistics_snapshot == (
        snapshot_before
    )
    assert context.workspace.revision == 3


def test_metadata_label_change_preserves_snapshot_under_new_deterministic_id(
    tmp_path: Path,
) -> None:
    context = _create_context(tmp_path)
    apply_match_capture_web_operation_v1(context, _statistics_values(context))
    snapshot_before = context.workspace.match_definition.participants[
        0
    ].statistics_snapshot
    slots_before = context.workspace.slots
    values = _metadata_values(context, played_at="2026-08-01T19:30:00Z")
    values["player_1_label"] = "Alice Corrected"
    result = apply_match_capture_web_operation_v1(context, values)
    assert result.status == "applied"
    assert context.workspace.revision == 2
    participant = context.workspace.match_definition.participants[0]
    snapshot_after = participant.statistics_snapshot
    assert participant.player_label == "Alice Corrected"
    assert snapshot_after.snapshot_id == "capture-web-match-player-a-statistics-r2"
    assert snapshot_after.statistics_record.player_label == "Alice Corrected"
    assert snapshot_after.observed_at == snapshot_before.observed_at
    assert snapshot_after.statistics_record.source == snapshot_before.statistics_record.source
    assert snapshot_after.statistics_record.statistics == (
        snapshot_before.statistics_record.statistics
    )
    assert snapshot_after.statistics_record.exact_counts == (
        snapshot_before.statistics_record.exact_counts
    )
    assert context.workspace.slots == slots_before


def test_web_snapshot_result_reuses_preparation_without_second_derivation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import skat_ai.match_player_statistics_context as context_module

    context = _create_context(tmp_path)
    calls = 0
    original = context_module.derive_opponent_profile

    def counted(profile):
        nonlocal calls
        calls += 1
        return original(profile)

    monkeypatch.setattr(context_module, "derive_opponent_profile", counted)
    result = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context),
    )
    assert result.status == "applied"
    assert calls == 1


def test_snapshot_persistence_conflict_retains_context_until_explicit_reload(
    tmp_path: Path,
) -> None:
    context = _create_context(tmp_path)
    old_workspace = context.workspace
    external = set_match_player_statistics_snapshot_v1(
        old_workspace,
        player_id="player-b",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=replace(
            _statistics_record("player-b"),
            player_label="Bob",
        ),
        expected_revision=0,
    ).workspace_change.workspace
    external_document = build_match_workspace_persistence_document_v1(external)
    assert save_match_workspace_file_v1(
        context.workspace_path,
        external_document,
        expected_content_fingerprint=context.content_fingerprint,
    ).status == "saved"
    result = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context),
    )
    assert result.status == "persistence_conflict"
    assert result.http_status == 409
    assert context.workspace == old_workspace
    assert context.content_fingerprint != external_document.content_fingerprint


def test_snapshot_operation_executes_no_analysis_materialization_network_or_history(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _create_context(tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Forbidden analysis, history, or network path executed.")

    monkeypatch.setattr(
        "skat_ai.application.execution.execute_application_invocation",
        forbidden,
    )
    monkeypatch.setattr("socket.create_connection", forbidden)
    result = apply_match_capture_web_operation_v1(
        context,
        _statistics_values(context),
    )
    assert result.status == "applied"
