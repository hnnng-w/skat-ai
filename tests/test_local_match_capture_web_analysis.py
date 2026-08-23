import json
import threading
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlencode

import pytest
from test_local_match_capture_web import (
    _create_context,
    _operation_values,
    _request,
)
from test_match_decision_analysis import _complete_workspace
from test_match_decision_review_preparation import _workspace_with_partial_game
from test_match_historical_analysis import _strict_workspace
from test_match_workspace_contracts import _definition
from test_match_workspace_materialization import _all_passed_workspace

import skat_ai.capture_web.analysis as analysis_module
import skat_ai.capture_web.server as server_module
from skat_ai.api.v1.contracts import ResultDocumentV1
from skat_ai.capture_web.analysis import execute_match_capture_web_analysis_v1
from skat_ai.capture_web.context import MatchCaptureWebContextV1
from skat_ai.capture_web.operations import (
    apply_match_capture_web_operation_v1,
    reload_match_capture_workspace_v1,
)
from skat_ai.capture_web.rendering import render_match_capture_web_page_v1
from skat_ai.capture_web.report_store import MatchAnalysisReportStoreV1
from skat_ai.capture_web.server import start_match_capture_web_server_v1
from skat_ai.capture_web.state import build_match_capture_web_state_v1
from skat_ai.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    MatchHistoricalAnalysisOptionsV1,
    build_match_analysis_report_v1,
    prepare_match_materialization_report_v1,
)
from skat_ai.match_analysis_exports import build_match_materialization_summary_export_v1
from skat_ai.match_analysis_report_source_codec import (
    resume_match_analysis_report_source_export_v1,
)
from skat_ai.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)
from skat_ai.match_decision_analysis import execute_match_decision_analysis_v1
from skat_ai.match_historical_analysis import execute_match_historical_analysis_v1
from skat_ai.match_workspace_contracts import MatchWorkspaceV1, create_match_workspace_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _analysis_values(
    context: MatchCaptureWebContextV1,
    operation: str,
    *,
    position: int = 3,
    **overrides: object,
) -> dict[str, object]:
    assert context.workspace is not None
    values: dict[str, object] = {
        "operation": operation,
        "match_position": str(position),
        "expected_revision": str(context.workspace.revision),
    }
    values.update(overrides)
    return values


def _partial_context(tmp_path: Path) -> MatchCaptureWebContextV1:
    workspace, _data = _workspace_with_partial_game()
    context = MatchCaptureWebContextV1.open(tmp_path / "analysis-match.json")
    document = build_match_workspace_persistence_document_v1(workspace)
    assert context.save_candidate(workspace) == "saved"
    assert context.content_fingerprint == document.content_fingerprint
    return context


def _workspace_context(tmp_path: Path, workspace, filename: str) -> MatchCaptureWebContextV1:
    context = MatchCaptureWebContextV1.open(tmp_path / filename)
    assert context.save_candidate(workspace) == "saved"
    return context


def _start_server(context: MatchCaptureWebContextV1):
    server = start_match_capture_web_server_v1(context, port=0, token="analysis-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _bootstrap_analysis(server):
    status, headers, body = _request(
        server,
        "GET",
        "/?token=analysis-token",
        headers={"Host": f"127.0.0.1:{server.port}"},
    )
    assert status == 303 and body == b""
    cookie = headers["set-cookie"].split(";", 1)[0]
    get_headers = {
        "Host": f"127.0.0.1:{server.port}",
        "Cookie": cookie,
    }
    return get_headers, {
        **get_headers,
        "Origin": f"http://127.0.0.1:{server.port}",
    }


def test_report_store_replaces_without_refresh_and_evicts_oldest() -> None:
    workspace, _data = _workspace_with_partial_game()
    reports = []
    for decision_index in range(1, 10):
        value = execute_match_decision_analysis_v1(
            workspace,
            match_position=3,
            decision_index=decision_index,
            options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
        )
        reports.append(build_match_analysis_report_v1(value))
    store = MatchAnalysisReportStoreV1()
    for report in reports[:8]:
        assert store.put(report) is report
    store.put(reports[0])
    store.put(reports[8])
    assert len(store) == 8
    assert store.get(reports[0].report_id) is None
    assert tuple(item.report_id for item in store.list()) == tuple(
        item.report_id for item in reports[1:]
    )
    store.clear()
    assert store.list() == ()
    assert store.generation == 1
    store.clear()
    assert store.generation == 2


def test_analysis_state_is_curated_and_execution_does_not_save(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _partial_context(tmp_path)
    before_workspace = context.workspace
    before_bytes = context.workspace_path.read_bytes()
    monkeypatch.setattr(
        MatchCaptureWebContextV1,
        "save_candidate",
        lambda _self, _workspace: pytest.fail("analysis attempted Workspace Save"),
    )
    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_decision",
            decision_index="1",
            recommendation_method="immediate_expected_value",
            immediate_sample_count="1",
            immediate_random_seed="0",
            search_random_seed="",
            search_budget_profile="historical_review_v1",
            use_profile_presets=True,
        ),
    )
    assert result.status == "applied"
    assert result.state["selected_report_id"] is not None
    assert result.state["selected_report"]["details"]["recommendation"]
    serialized = json.dumps(result.to_dict())
    assert '"result"' not in serialized
    assert '"request"' not in serialized
    assert "compatible_worlds" not in serialized
    assert "content_fingerprint" not in serialized
    assert context.workspace is before_workspace
    assert context.workspace_path.read_bytes() == before_bytes
    assert len(context.report_store) == 1
    html = render_match_capture_web_page_v1(result.to_dict()["state"])
    report_id = result.state["selected_report_id"]
    assert "Download for Learning Corpus" in html
    assert f"/api/v1/reports/{report_id}/strategy-source.json" in html


def test_information_set_analysis_form_and_report_use_safe_diagnostics(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _workspace_context(
        tmp_path,
        _complete_workspace(),
        "information-set-analysis.json",
    )
    calls = 0
    original = analysis_module.execute_match_decision_analysis_v1

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        analysis_module,
        "execute_match_decision_analysis_v1",
        counted,
    )
    initial_state = build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
        selected_position=3,
        report_store=context.report_store,
    )
    initial_html = render_match_capture_web_page_v1(initial_state)
    assert '<option value="information_set_search">' in initial_html
    assert "Search random seed" in initial_html
    assert "Immediate sample count" in initial_html
    assert "Use eligible Player Profile Presets" in initial_html
    assert "strict without fallback" in initial_html

    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_decision",
            decision_index="30",
            recommendation_method="information_set_search",
            immediate_sample_count="1",
            immediate_random_seed="3",
            search_random_seed="7",
            search_budget_profile="interactive_v1",
            use_profile_presets=True,
        ),
        browser_form=True,
    )
    assert calls == 1
    details = result.state["selected_report"]["details"]
    information_set = details["information_set_search"]
    assert information_set["status"] == "complete"
    assert information_set["policy_consistency"] == ("controlled_player_information_set_consistent")
    assert information_set["information_set_recommended_card"] is not None
    state_document = result.to_dict()["state"]

    def keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    for forbidden in (
        "controlled_policy",
        "observations",
        "world_states",
        "exact_states",
        "own_remaining_hand",
        "candidate_results",
        "fixed_policy_settings",
        "wall_clock_elapsed_ms",
    ):
        assert forbidden not in keys(state_document)
    html = render_match_capture_web_page_v1(result.state)
    assert calls == 1
    assert "Information-set Search" in html
    assert "Same-selection PIMC Card" in html
    assert "not calibrated probability" in html


def test_selected_report_state_recursively_allows_only_rendered_fields() -> None:
    workspace, _data = _workspace_with_partial_game()
    decision = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    decision_document = decision.result.to_dict()["document"]
    decision_document["recommendation_method_summary"]["private_seed"] = 7
    decision_document["recommendation"]["private_hand"] = ["CA"]
    decision_document["analysis_report"][0]["private_world"] = {"left": ["S7"]}
    decision = replace(
        decision,
        result=ResultDocumentV1(
            workflow=decision.result.workflow,
            document=decision_document,
            warnings=decision.result.warnings,
        ),
    )
    decision_report = build_match_analysis_report_v1(decision)
    decision_store = MatchAnalysisReportStoreV1()
    decision_store.add(decision_report)
    decision_state = build_match_capture_web_state_v1(
        workspace,
        workspace_filename="private.json",
        selected_position=3,
        report_store=decision_store,
        selected_report_id=decision_report.report_id,
    )
    serialized_decision = json.dumps(decision_state)
    assert "private_seed" not in serialized_decision
    assert "private_hand" not in serialized_decision
    assert "private_world" not in serialized_decision

    historical_workspace = _strict_workspace()
    historical = execute_match_historical_analysis_v1(
        historical_workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1),
    )
    historical_document = historical.result.to_dict()["document"]
    summary = historical_document["historical_game_summary"]
    summary["historical_game_review_summary"]["quality_counts"]["private_decisions"] = ["CA"]
    summary["historical_search_review_summary"] = {
        "decision_counts": {"private_count": 1},
        "status_counts": {"private_status": 1},
        "coverage": {"private_worlds": ["CA"]},
        "search_vs_immediate_agreement": {"private_agreement": True},
        "quality_gate": {"private_gate": True},
        "actual_card_agreement": {"private_cards": ["CA"]},
        "performance": {"private_nodes": 1},
    }
    summary["historical_replay_coaching_summary"] = {
        "report_method": "historical_replay_coaching_v1",
        "coverage_summary": {"private_evidence": ["CA"]},
        "prioritization": {"key_decisions": [], "turning_points": []},
        "guidance": {
            "decision_recommendations": [],
            "pattern_recommendations": [],
            "private_patterns": ["CA"],
        },
        "outcome_context": {"private_outcome": ["CA"]},
        "limitations": [],
        "private_coaching": ["CA"],
    }
    summary["historical_information_set_search_review_summary"] = {
        "review_method": "information_set_search_with_same_selection_pimc_and_immediate_v1",
        "source_game_id": historical.game_id,
        "decision_count": 1,
        "status_counts": {"complete": 1, "private_status": 1},
        "coverage_counts": {"single_exact_world": 1, "private_world": 1},
        "selected_world_count_total": 1,
        "sampled_world_count_total": 0,
        "comparison_available_count": 1,
        "comparison_unavailable_count": 0,
        "information_set_recommendation_count": 1,
        "information_set_pimc_agreement": {"same_card_count": 1},
        "information_set_immediate_agreement": {"same_card_count": 1},
        "information_set_actual_agreement": {"same_card_count": 1},
        "decisions": [{"private_observation": ["CA"]}],
    }
    summary["historical_information_set_replay_coaching_summary"] = {
        "report_method": "historical_information_set_replay_coaching_v1",
        "source_game_id": historical.game_id,
        "coverage": {
            "decision_count": 1,
            "assessable_decision_count": 1,
            "forced_move_count": 0,
            "best_or_equivalent_count": 1,
            "strictly_below_best_count": 0,
            "not_assessable_count": 0,
            "high_impact_decision_count": 0,
            "key_decision_count": 0,
            "turning_point_count": 0,
            "pattern_count": 0,
            "actionable_pattern_count": 0,
            "decision_recommendation_count": 0,
            "pattern_recommendation_count": 0,
            "information_set_recommendation_count": 1,
            "pimc_recommendation_count": 1,
            "immediate_recommendation_count": 1,
            "assessment_status_counts": [],
            "evidence_basis_counts": [],
            "information_set_status_counts": [],
            "world_coverage_counts": [],
            "information_set_pimc_agreement_counts": [],
            "information_set_immediate_agreement_counts": [],
            "private_coverage": ["CA"],
        },
        "assessments": [{"private_policy": ["CA"]}],
        "prioritization": {"key_decisions": [], "turning_points": []},
        "guidance": {
            "decision_recommendations": [],
            "pattern_recommendations": [],
            "private_guidance": ["CA"],
        },
        "outcome_context": {"private_information_set_outcome": ["CA"]},
        "limitations": [],
    }
    historical = replace(
        historical,
        result=ResultDocumentV1(
            workflow=historical.result.workflow,
            document=historical_document,
            warnings=historical.result.warnings,
        ),
    )
    historical_report = build_match_analysis_report_v1(historical)
    historical_store = MatchAnalysisReportStoreV1()
    historical_store.add(historical_report)
    historical_state = build_match_capture_web_state_v1(
        historical_workspace,
        workspace_filename="private.json",
        selected_position=3,
        report_store=historical_store,
        selected_report_id=historical_report.report_id,
    )
    serialized_historical = json.dumps(historical_state)
    for private_field in (
        "private_decisions",
        "private_count",
        "private_status",
        "private_worlds",
        "private_agreement",
        "private_gate",
        "private_cards",
        "private_nodes",
        "private_evidence",
        "private_patterns",
        "private_outcome",
        "private_coaching",
        "private_observation",
        "private_policy",
        "private_coverage",
        "private_guidance",
        "private_information_set_outcome",
    ):
        assert private_field not in serialized_historical
    information_set_details = historical_state["selected_report"]["details"]
    assert information_set_details["information_set_search_review"][
        "decision_count"
    ] == 1
    assert information_set_details["information_set_replay_coaching"][
        "coverage"
    ]["assessable_decision_count"] == 1
    historical_html = render_match_capture_web_page_v1(historical_state)
    assert "Historical Information-set Search Review" in historical_html
    assert "Information-set Replay Coaching" in historical_html
    assert "Assessment status counts" in historical_html
    assert "Same-selection PIMC agreement counts" in historical_html
    assert "Immediate agreement counts" in historical_html
    assert "Same-selection PIMC and Immediate are diagnostics, never fallback" in (
        historical_html
    )
    assert "It is not equilibrium, calibrated probability, or perfect play." in (
        historical_html
    )
    for private_field in (
        "private_observation",
        "private_policy",
        "private_coverage",
        "private_guidance",
        "private_information_set_outcome",
    ):
        assert private_field not in historical_html


def test_state_build_prepares_evidence_but_executes_no_application(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _partial_context(tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("ordinary browser state executed Application analysis")

    monkeypatch.setattr(
        "skat_ai.application.execution.execute_application_invocation",
        forbidden,
    )
    state = build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
        selected_position=3,
        report_store=context.report_store,
    )
    assert state["decision_preparation"]["source_play_count"] == 6
    assert state["historical_materialization"]["available"] is False
    assert context.report_store.list() == ()


def test_materialization_and_unavailable_historical_are_normal_reports(tmp_path: Path) -> None:
    context = _partial_context(tmp_path)
    materialization = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(context, "prepare_materialization"),
    )
    assert materialization.http_status == 200
    assert materialization.state["download_availability"]["materialization"] is True
    historical = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_historical_game",
            decision_snapshots=False,
            immediate_review=True,
            search_review=False,
            replay_coaching=False,
            immediate_sample_count="1",
            immediate_random_seed="0",
            search_random_seed=None,
            search_budget_profile="historical_review_v1",
            use_profile_presets=True,
        ),
    )
    assert historical.http_status == 200
    assert historical.state["selected_report"]["status"] == "unavailable"
    assert historical.state["selected_report"]["details"]["unavailable_reason"] == (
        "incomplete_play_trace"
    )


def test_json_analysis_options_are_strict_and_accept_no_custom_budget(
    tmp_path: Path,
) -> None:
    context = _partial_context(tmp_path)
    with pytest.raises(ValueError, match="Search and Auto require"):
        execute_match_capture_web_analysis_v1(
            context,
            _analysis_values(
                context,
                "analyze_decision",
                decision_index="1",
                recommendation_method="bounded_search",
                immediate_sample_count="1",
                search_random_seed=None,
            ),
        )
    with pytest.raises(ValueError, match="Immediate analysis requires"):
        execute_match_capture_web_analysis_v1(
            context,
            _analysis_values(
                context,
                "analyze_decision",
                decision_index="1",
                recommendation_method="immediate_expected_value",
                immediate_sample_count="1",
                search_random_seed="0",
            ),
        )
    with pytest.raises(ValueError, match="Unsupported analysis form fields"):
        execute_match_capture_web_analysis_v1(
            context,
            _analysis_values(
                context,
                "analyze_decision",
                decision_index="1",
                max_selected_worlds="1",
            ),
        )
    with pytest.raises(ValueError, match="information_set_replay_coaching must be a boolean"):
        execute_match_capture_web_analysis_v1(
            context,
            _analysis_values(
                context,
                "analyze_historical_game",
                immediate_review=False,
                information_set_replay_coaching=1,
                search_random_seed=0,
            ),
        )
    with pytest.raises(ValueError, match="Workspace mutation"):
        apply_match_capture_web_operation_v1(
            context,
            _analysis_values(
                context,
                "analyze_decision",
                decision_index="1",
            ),
        )


def test_historical_information_set_browser_controls_and_options_are_explicit(
    tmp_path: Path,
) -> None:
    context = _partial_context(tmp_path)
    state = build_match_capture_web_state_v1(
        _strict_workspace(),
        workspace_filename="historical-information-set.json",
        selected_position=3,
    )
    html = render_match_capture_web_page_v1(state)
    assert 'name="information_set_search_review"' in html
    assert 'name="information_set_replay_coaching"' in html
    assert "PIMC and Immediate are diagnostic baselines with no fallback" in html
    assert "not equilibrium or perfect play" in html

    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_historical_game",
            decision_snapshots=False,
            immediate_review=False,
            search_review=False,
            information_set_search_review=True,
            replay_coaching=False,
            information_set_replay_coaching=True,
            immediate_sample_count="1",
            immediate_random_seed="23",
            search_random_seed="29",
            search_budget_profile="interactive_v1",
            use_profile_presets=True,
        ),
    )
    report = context.report_store.get(result.state["selected_report_id"])
    options = report.value.options
    assert options.information_set_search_review is True
    assert options.information_set_replay_coaching is True
    assert options.search_random_seed == 29
    assert options.immediate_random_seed == 23
    assert options.use_profile_presets is True


@pytest.mark.parametrize("changed_field", ("revision", "fingerprint"))
def test_analysis_reconciliation_discards_changed_context_without_retry(
    tmp_path: Path,
    monkeypatch,
    changed_field: str,
) -> None:
    context = _partial_context(tmp_path)
    calls = 0
    original = analysis_module.execute_match_decision_analysis_v1

    def changed(*args, **kwargs):
        nonlocal calls
        calls += 1
        value = original(*args, **kwargs)
        with context.lock:
            if changed_field == "revision":
                workspace = context.workspace
                context.workspace = MatchWorkspaceV1._from_validated(
                    revision=workspace.revision + 1,
                    match_definition=workspace.match_definition,
                    slots=workspace.slots,
                )
            else:
                context.content_fingerprint = "0" * 64
        return value

    monkeypatch.setattr(analysis_module, "execute_match_decision_analysis_v1", changed)
    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_decision",
            decision_index="1",
            immediate_sample_count="1",
        ),
    )
    assert result.http_status == 409
    assert calls == 1
    assert len(context.report_store) == 0


def test_analysis_releases_context_lock_during_core_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _partial_context(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    original = analysis_module.execute_match_decision_analysis_v1

    def paused(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(analysis_module, "execute_match_decision_analysis_v1", paused)
    result = []

    def run_analysis():
        result.append(
            execute_match_capture_web_analysis_v1(
                context,
                _analysis_values(
                    context,
                    "analyze_decision",
                    decision_index="1",
                    immediate_sample_count="1",
                ),
            )
        )

    thread = threading.Thread(target=run_analysis)
    thread.start()
    assert entered.wait(timeout=5)
    acquired = context.lock.acquire(timeout=1)
    try:
        assert acquired is True
    finally:
        if acquired:
            context.lock.release()
    release.set()
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert result[0].status == "applied"


def test_report_invalidation_matrix(tmp_path: Path, monkeypatch) -> None:
    context = _create_context(tmp_path)

    def prepare_report():
        result = execute_match_capture_web_analysis_v1(
            context,
            _analysis_values(
                context,
                "prepare_materialization",
                position=1,
            ),
        )
        return result.state["selected_report_id"]

    first_id = prepare_report()
    unchanged = apply_match_capture_web_operation_v1(
        context,
        _operation_values(
            context,
            "clear_position",
            confirm_clear="true",
        ),
    )
    assert unchanged.status == "unchanged"
    assert context.report_store.get(first_id) is not None
    conflict = apply_match_capture_web_operation_v1(
        context,
        {
            "operation": "clear_position",
            "match_position": "1",
            "expected_revision": "99",
        },
    )
    assert conflict.status == "revision_conflict"
    assert context.report_store.get(first_id) is not None

    with monkeypatch.context() as patch:
        patch.setattr(
            MatchCaptureWebContextV1,
            "save_candidate",
            lambda _self, _workspace: "conflict",
        )
        persistence = apply_match_capture_web_operation_v1(
            context,
            _operation_values(context, "start_game"),
        )
    assert persistence.status == "persistence_conflict"
    assert context.report_store.get(first_id) is not None

    applied = apply_match_capture_web_operation_v1(
        context,
        _operation_values(context, "start_game"),
    )
    assert applied.status == "applied"
    assert context.report_store.list() == ()
    second_id = prepare_report()
    assert reload_match_capture_workspace_v1(context).status == "reloaded"
    assert context.report_store.get(second_id) is None


def test_browser_analysis_forms_and_materialization_downloads_are_no_js(
    tmp_path: Path,
) -> None:
    context = _partial_context(tmp_path)
    server, thread = _start_server(context)
    try:
        get_headers, post_headers = _bootstrap_analysis(server)
        status, _headers, body = _request(
            server,
            "GET",
            "/position/3",
            headers=get_headers,
        )
        assert status == 200
        assert b"Prepare Match summary" in body
        assert b"Match materialization" in body
        assert b"Observed Game Decisions" in body
        assert b"actual Card is retrospective evidence" in body
        assert b"Historical Game Analysis unavailable" in body
        assert b'name="decision_index"' in body
        assert body.count(b"data-native-submit") == 2
        assert b'<option value="1">#1' in body
        assert b"acting hand unavailable" in body

        status, _headers, script = _request(
            server,
            "GET",
            "/assets/capture.js",
            headers=get_headers,
        )
        assert status == 200
        native_guard = script.index(b"[data-native-submit]")
        assert native_guard < script.index(b"event.preventDefault();", native_guard)
        assert native_guard < script.index(b"fetch(event.target.action")

        form_headers = {
            **post_headers,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        values = _analysis_values(
            context,
            "prepare_materialization",
        )
        status, headers, body = _request(
            server,
            "POST",
            "/api/v1/analysis",
            headers=form_headers,
            body=urlencode(values).encode(),
        )
        assert status == 303 and body == b""
        report_url = headers["location"]
        assert report_url.startswith("/reports/")
        status, _headers, body = _request(
            server,
            "GET",
            report_url,
            headers=get_headers,
        )
        assert status == 200
        assert b"Prepared Match summary" in body
        assert b"Private local download" in body
        assert (
            context.workspace_path.parent.joinpath(f"{report_url.rsplit('/', 1)[-1]}.json").exists()
            is False
        )
        assert tuple(context.workspace_path.parent.glob("*report*.json")) == ()

        state_status, _state_headers, state_body = _request(
            server,
            "GET",
            "/api/v1/state",
            headers=get_headers,
        )
        assert state_status == 200
        ordinary_state = json.loads(state_body)
        assert ordinary_state["materialization_available"] is True
        assert ordinary_state["selected_report"] is None
        assert '"result"' not in state_body.decode()
        assert '"request"' not in state_body.decode()

        status, headers, body = _request(
            server,
            "GET",
            "/api/v1/exports/materialization.json",
            headers=get_headers,
        )
        assert status == 200
        assert headers["content-disposition"] == (
            f'attachment; filename="{context.workspace.match_definition.match_id}-'
            'materialization.json"'
        )
        report = context.report_store.list()[-1]
        assert (
            body
            == (
                json.dumps(
                    report.value.materialization.to_dict(),
                    ensure_ascii=True,
                    allow_nan=False,
                    indent=2,
                )
                + "\n"
            ).encode()
        )

        status, headers, body = _request(
            server,
            "GET",
            "/api/v1/exports/historical-games.json",
            headers=get_headers,
        )
        assert status == 200
        assert headers["content-disposition"] == (
            f'attachment; filename="{context.workspace.match_definition.match_id}-'
            'historical-games.json"'
        )
        assert json.loads(body)["available_game_count"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert context.report_store.list() == ()


def test_report_json_auth_bytes_filename_stale_and_invalidation(tmp_path: Path) -> None:
    context = _partial_context(tmp_path)
    server, thread = _start_server(context)
    try:
        get_headers, post_headers = _bootstrap_analysis(server)
        json_headers = {**post_headers, "Content-Type": "application/json"}
        values = {
            "operation": "analyze_decision",
            "match_position": 3,
            "expected_revision": context.workspace.revision,
            "decision_index": 1,
            "recommendation_method": "immediate_expected_value",
            "immediate_sample_count": 1,
            "immediate_random_seed": 0,
            "search_random_seed": None,
            "search_budget_profile": "historical_review_v1",
            "use_profile_presets": True,
        }
        status, _headers, body = _request(
            server,
            "POST",
            "/api/v1/analysis",
            headers=json_headers,
            body=json.dumps(values).encode(),
        )
        assert status == 200
        report_id = json.loads(body)["state"]["selected_report_id"]
        path = f"/api/v1/reports/{report_id}.json"
        strategy_path = f"/api/v1/reports/{report_id}/strategy-source.json"
        status, _headers, _body = _request(
            server,
            "GET",
            path,
            headers={"Host": f"127.0.0.1:{server.port}"},
        )
        assert status == 403
        status, _headers, _body = _request(
            server,
            "GET",
            strategy_path,
            headers={"Host": f"127.0.0.1:{server.port}"},
        )
        assert status == 403
        status, headers, body = _request(server, "GET", path, headers=get_headers)
        assert status == 200
        assert headers["content-disposition"] == (
            f'attachment; filename="{context.workspace.match_definition.match_id}-'
            "position-03-decision-01-"
            'immediate_expected_value.json"'
        )
        report = context.report_store.get(report_id)
        assert json.loads(body) == report.value.result.to_dict()["document"]
        assert body.endswith(b"\n") and not body.endswith(b"\n\n")
        root_result_body = body
        files_before = {
            item.name: item.read_bytes()
            for item in context.workspace_path.parent.iterdir()
            if item.is_file()
        }
        status, headers, body = _request(
            server,
            "GET",
            strategy_path,
            headers=get_headers,
        )
        assert status == 200
        assert headers["content-disposition"] == (
            f'attachment; filename="{context.workspace.match_definition.match_id}-'
            'position-03-decision-01-immediate_expected_value-strategy-source.json"'
        )
        assert headers["content-disposition"].isascii()
        source_export = build_match_analysis_report_source_export_v1(report)
        assert body == serialize_match_analysis_report_source_export_v1(source_export)
        assert resume_match_analysis_report_source_export_v1(json.loads(body)).report == report
        assert {
            item.name: item.read_bytes()
            for item in context.workspace_path.parent.iterdir()
            if item.is_file()
        } == files_before
        status, _headers, body = _request(server, "GET", path, headers=get_headers)
        assert status == 200
        assert body == root_result_body
        status, _headers, _body = _request(
            server,
            "GET",
            f"/api/v1/reports/{'f' * 64}/strategy-source.json",
            headers=get_headers,
        )
        assert status == 404

        with context.lock:
            context.workspace = MatchWorkspaceV1._from_validated(
                revision=context.workspace.revision + 1,
                match_definition=context.workspace.match_definition,
                slots=context.workspace.slots,
            )
        status, _headers, _body = _request(server, "GET", path, headers=get_headers)
        assert status == 409
        status, _headers, _body = _request(server, "GET", strategy_path, headers=get_headers)
        assert status == 409
        with context.lock:
            context.workspace = MatchWorkspaceV1._from_validated(
                revision=context.workspace.revision - 1,
                match_definition=context.workspace.match_definition,
                slots=context.workspace.slots,
            )
        mutation = _operation_values(
            context,
            "set_game_timecode",
            match_position="3",
            game_timecode_start="",
            game_timecode_end="",
        )
        mutation["match_position"] = 3
        mutation["expected_revision"] = context.workspace.revision
        status, _headers, _body = _request(
            server,
            "POST",
            "/api/v1/operation",
            headers=json_headers,
            body=json.dumps(mutation).encode(),
        )
        assert status == 200
        status, _headers, _body = _request(server, "GET", path, headers=get_headers)
        assert status == 404
        status, _headers, _body = _request(server, "GET", strategy_path, headers=get_headers)
        assert status == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_equal_content_reload_discards_in_flight_analysis(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _partial_context(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    original = analysis_module.execute_match_decision_analysis_v1

    def paused(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(analysis_module, "execute_match_decision_analysis_v1", paused)
    source_revision = context.workspace.revision
    source_fingerprint = context.content_fingerprint
    results = []

    thread = threading.Thread(
        target=lambda: results.append(
            execute_match_capture_web_analysis_v1(
                context,
                _analysis_values(
                    context,
                    "analyze_decision",
                    decision_index="1",
                    immediate_sample_count="1",
                ),
            )
        )
    )
    thread.start()
    assert entered.wait(timeout=5)
    assert reload_match_capture_workspace_v1(context).status == "reloaded"
    assert context.workspace.revision == source_revision
    assert context.content_fingerprint == source_fingerprint
    release.set()
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert results[0].http_status == 409
    assert context.report_store.list() == ()


@pytest.mark.parametrize(
    "path,builder_name",
    (
        ("report", "build_match_report_result_export_v1"),
        ("materialization", "build_match_materialization_summary_export_v1"),
    ),
)
def test_export_serialization_value_error_is_artifact_unavailable(
    tmp_path: Path,
    monkeypatch,
    path: str,
    builder_name: str,
) -> None:
    import skat_ai.capture_web.server as server_module

    context = _partial_context(tmp_path)
    operation = "analyze_decision" if path == "report" else "prepare_materialization"
    values = _analysis_values(context, operation)
    if operation == "analyze_decision":
        values.update(decision_index="1", immediate_sample_count="1")
    result = execute_match_capture_web_analysis_v1(context, values)
    report_id = result.state["selected_report_id"]
    original_builder = getattr(server_module, builder_name)

    class BrokenArtifact:
        filename = "unreachable.json"

        def to_bytes(self):
            raise ValueError("serialization failed")

    monkeypatch.setattr(
        server_module,
        builder_name,
        lambda *args, **kwargs: original_builder(*args, **kwargs) and BrokenArtifact(),
    )
    if path == "materialization":
        monkeypatch.setitem(
            server_module._EXPORT_BUILDERS,
            "/api/v1/exports/materialization.json",
            getattr(server_module, builder_name),
        )
    server, server_thread = _start_server(context)
    try:
        get_headers, _post_headers = _bootstrap_analysis(server)
        request_path = (
            f"/api/v1/reports/{report_id}.json"
            if path == "report"
            else "/api/v1/exports/materialization.json"
        )
        status, _headers, body = _request(
            server,
            "GET",
            request_path,
            headers=get_headers,
        )
        assert status == 404
        assert body == b"Artifact unavailable"
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def test_download_serialization_linearizes_before_report_invalidation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from skat_ai.match_analysis_exports import MatchArtifactExportV1

    context = _create_context(tmp_path)
    prepared = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(context, "prepare_materialization", position=1),
    )
    report_id = prepared.state["selected_report_id"]
    entered = threading.Event()
    release = threading.Event()
    mutation_started = threading.Event()
    mutation_finished = threading.Event()
    original = MatchArtifactExportV1.to_bytes

    def paused(artifact):
        entered.set()
        assert release.wait(timeout=5)
        return original(artifact)

    monkeypatch.setattr(MatchArtifactExportV1, "to_bytes", paused)
    server, server_thread = _start_server(context)
    download_result = []
    mutation_result = []
    try:
        get_headers, _post_headers = _bootstrap_analysis(server)
        download = threading.Thread(
            target=lambda: download_result.append(
                _request(
                    server,
                    "GET",
                    "/api/v1/exports/materialization.json",
                    headers=get_headers,
                )
            )
        )
        mutation_values = _operation_values(context, "start_game")

        def mutate():
            mutation_started.set()
            mutation_result.append(apply_match_capture_web_operation_v1(context, mutation_values))
            mutation_finished.set()

        download.start()
        assert entered.wait(timeout=5)
        mutation = threading.Thread(target=mutate)
        mutation.start()
        assert mutation_started.wait(timeout=5)
        assert mutation_finished.wait(timeout=0.2) is False
        release.set()
        download.join(timeout=10)
        mutation.join(timeout=10)
        assert not download.is_alive()
        assert not mutation.is_alive()
        assert download_result[0][0] == 200
        assert mutation_result[0].status == "applied"
        assert context.report_store.get(report_id) is None
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


@pytest.mark.parametrize(
    "match_id",
    ("opaque/match", 'opaque"match\r\nheader', "opaque-match-ä"),
)
def test_opaque_match_id_download_header_is_ascii_safe(
    tmp_path: Path,
    match_id: str,
) -> None:
    context = _workspace_context(
        tmp_path,
        create_match_workspace_v1(_definition(match_id=match_id)),
        "opaque-id.json",
    )
    execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(context, "prepare_materialization", position=1),
    )
    report = context.report_store.list()[-1]
    expected = build_match_materialization_summary_export_v1(report.value).filename
    server, thread = _start_server(context)
    try:
        get_headers, _post_headers = _bootstrap_analysis(server)
        status, headers, _body = _request(
            server,
            "GET",
            "/api/v1/exports/materialization.json",
            headers=get_headers,
        )
        assert status == 200
        disposition = headers["content-disposition"]
        assert disposition == f'attachment; filename="{expected}"'
        assert disposition.isascii()
        filename = disposition.removeprefix('attachment; filename="').removesuffix('"')
        assert all(character not in filename for character in '\r\n/\\%"')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "field,value",
    (
        ("expected_revision", "1"),
        ("match_position", "3"),
        ("decision_index", "1"),
        ("immediate_sample_count", "1"),
        ("immediate_random_seed", "0"),
        ("use_profile_presets", "true"),
        ("expected_revision", True),
        ("immediate_sample_count", 10**400),
    ),
)
def test_json_analysis_rejects_stringified_or_boolean_scalars(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    context = _partial_context(tmp_path)
    server, thread = _start_server(context)
    try:
        _get_headers, post_headers = _bootstrap_analysis(server)
        values = {
            "operation": "analyze_decision",
            "match_position": 3,
            "expected_revision": context.workspace.revision,
            "decision_index": 1,
            "recommendation_method": "immediate_expected_value",
            "immediate_sample_count": 1,
            "immediate_random_seed": 0,
            "search_random_seed": None,
            "search_budget_profile": "historical_review_v1",
            "use_profile_presets": True,
        }
        values[field] = value
        status, _headers, _body = _request(
            server,
            "POST",
            "/api/v1/analysis",
            headers={**post_headers, "Content-Type": "application/json"},
            body=json.dumps(values).encode(),
        )
        assert status == 400
        assert context.report_store.list() == ()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_disabled_profile_presets_are_private_report_only(tmp_path: Path) -> None:
    from test_match_decision_analysis import _complete_workspace
    from test_match_player_statistics_context import (
        _actionable_snapshot,
        _capture_with_snapshots,
    )

    definition = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
            _actionable_snapshot("player-c", "snapshot-c"),
        )
    )
    context = _workspace_context(
        tmp_path,
        _complete_workspace(definition=definition),
        "disabled-profiles.json",
    )
    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_decision",
            decision_index="1",
            immediate_sample_count="1",
            use_profile_presets=False,
        ),
    )
    report = context.report_store.get(result.state["selected_report_id"])
    assert report is not None
    assert "opponent_profile_application_summary" not in (report.value.result.to_dict()["document"])
    profiles = result.to_dict()["state"]["selected_report"]["details"]["profiles"]
    assert profiles["left"]["not_applied_reason"] == "profile_presets_disabled"
    assert profiles["right"]["not_applied_reason"] == "profile_presets_disabled"
    assert profiles["left"]["effective_lead_policy"] == "lowest_point"
    assert profiles["right"]["effective_response_policy"] == "lowest_point"


def test_unavailable_form_analysis_still_redirects_to_report(tmp_path: Path) -> None:
    context = _partial_context(tmp_path)
    server, thread = _start_server(context)
    try:
        get_headers, post_headers = _bootstrap_analysis(server)
        headers = {
            **post_headers,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        values = _analysis_values(
            context,
            "analyze_historical_game",
            immediate_review="true",
            immediate_sample_count="1",
            immediate_random_seed="0",
            search_random_seed="0",
            search_budget_profile="historical_review_v1",
            use_profile_presets="true",
        )
        status, response_headers, body = _request(
            server,
            "POST",
            "/api/v1/analysis",
            headers=headers,
            body=urlencode(values).encode(),
        )
        assert status == 303 and body == b""
        status, _headers, body = _request(
            server,
            "GET",
            response_headers["location"],
            headers=get_headers,
        )
        assert status == 200
        assert b"normally unavailable" in body
        assert b"incomplete play trace" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_form_analysis_conflict_renders_current_position_without_report(
    tmp_path: Path,
) -> None:
    context = _partial_context(tmp_path)
    server, thread = _start_server(context)
    try:
        _get_headers, post_headers = _bootstrap_analysis(server)
        headers = {
            **post_headers,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        values = _analysis_values(context, "prepare_materialization")
        values["expected_revision"] = "999"
        status, response_headers, body = _request(
            server,
            "POST",
            "/api/v1/analysis",
            headers=headers,
            body=urlencode(values).encode(),
        )
        assert status == 409
        assert "location" not in response_headers
        assert b"Workspace revision conflict" in body
        assert b"Position 3" in body
        assert context.report_store.list() == ()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_analysis_validation_security_method_and_unknown_report(tmp_path: Path) -> None:
    context = _partial_context(tmp_path)
    server, thread = _start_server(context)
    try:
        get_headers, post_headers = _bootstrap_analysis(server)
        form_headers = {
            **post_headers,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        values = _analysis_values(
            context,
            "analyze_decision",
            decision_index="1",
            recommendation_method="bounded_search",
            max_nodes="1",
        )
        status, _headers, body = _request(
            server,
            "POST",
            "/api/v1/analysis",
            headers=form_headers,
            body=urlencode(values).encode(),
        )
        assert status == 400
        assert b"Unsupported analysis form fields" in body
        assert context.report_store.list() == ()
        bad_origin = dict(form_headers)
        bad_origin["Origin"] = "http://evil.example"
        status, _headers, _body = _request(
            server,
            "POST",
            "/api/v1/analysis",
            headers=bad_origin,
            body=urlencode(_analysis_values(context, "prepare_materialization")).encode(),
        )
        assert status == 403
        unknown = "f" * 64
        status, _headers, _body = _request(
            server,
            "GET",
            f"/reports/{unknown}",
            headers=get_headers,
        )
        assert status == 404
        status, _headers, _body = _request(
            server,
            "GET",
            f"/api/v1/reports/{unknown}/strategy-source.json",
            headers=get_headers,
        )
        assert status == 404
        status, headers, _body = _request(
            server,
            "POST",
            f"/reports/{unknown}",
            headers=post_headers,
            body=b"",
        )
        assert status == 405 and headers["allow"] == "GET, POST"
        status, _headers, _body = _request(
            server,
            "GET",
            "/api/v1/exports/materialization.json?path=private.json",
            headers=get_headers,
        )
        assert status == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_strategy_source_route_rejects_unsupported_current_report_kinds_and_status(
    tmp_path: Path,
) -> None:
    context = _workspace_context(
        tmp_path,
        _strict_workspace(),
        "unsupported-strategy-sources.json",
    )
    workspace = context.workspace
    materialization = build_match_analysis_report_v1(
        prepare_match_materialization_report_v1(workspace)
    )
    unavailable_decision = build_match_analysis_report_v1(
        execute_match_decision_analysis_v1(
            workspace,
            match_position=3,
            decision_index=99,
            options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
        )
    )
    historical = build_match_analysis_report_v1(
        execute_match_historical_analysis_v1(
            workspace,
            match_position=3,
            options=MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1),
        )
    )
    for report in (materialization, unavailable_decision, historical):
        context.report_store.add(report)

    server, thread = _start_server(context)
    try:
        get_headers, _post_headers = _bootstrap_analysis(server)
        for report in (materialization, unavailable_decision, historical):
            status, _headers, body = _request(
                server,
                "GET",
                f"/api/v1/reports/{report.report_id}/strategy-source.json",
                headers=get_headers,
            )
            assert status == 404
            assert body == b"Artifact unavailable"
            state = build_match_capture_web_state_v1(
                workspace,
                workspace_filename=context.workspace_filename,
                selected_position=report.match_position or 1,
                report_store=context.report_store,
                selected_report_id=report.report_id,
            )
            assert "Download for Learning Corpus" not in (render_match_capture_web_page_v1(state))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_strategy_source_serialization_failure_is_generic_internal_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _partial_context(tmp_path)
    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_decision",
            decision_index="1",
            immediate_sample_count="1",
            immediate_random_seed="0",
            recommendation_method="immediate_expected_value",
            search_random_seed="",
            search_budget_profile="historical_review_v1",
            use_profile_presets="false",
        ),
        browser_form=True,
    )
    assert result.status == "applied"
    report = context.report_store.list()[0]
    monkeypatch.setattr(
        server_module,
        "serialize_match_analysis_report_source_export_v1",
        lambda _export: (_ for _ in ()).throw(ValueError("private serialization")),
    )
    server, thread = _start_server(context)
    try:
        get_headers, _post_headers = _bootstrap_analysis(server)
        status, _headers, body = _request(
            server,
            "GET",
            f"/api/v1/reports/{report.report_id}/strategy-source.json",
            headers=get_headers,
        )
        assert status == 500
        assert body == b"Internal server error"
        assert b"private serialization" not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_cached_historical_download_uses_canonical_bytes_and_filename(
    tmp_path: Path,
) -> None:
    workspace = _strict_workspace()
    value = execute_match_historical_analysis_v1(
        workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1),
    )
    report = build_match_analysis_report_v1(value)
    context = _workspace_context(tmp_path, workspace, "historical-download.json")
    context.report_store.add(report)
    server, thread = _start_server(context)
    try:
        get_headers, _post_headers = _bootstrap_analysis(server)
        status, headers, body = _request(
            server,
            "GET",
            f"/api/v1/reports/{report.report_id}.json",
            headers=get_headers,
        )
        assert status == 200
        assert headers["content-disposition"] == (
            f'attachment; filename="{report.match_id}-game-03-historical-analysis.json"'
        )
        assert json.loads(body) == value.result.to_dict()["document"]
        assert body.endswith(b"\n") and not body.endswith(b"\n\n")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_strict_historical_form_executes_once_and_rendering_does_not_rerun(
    tmp_path: Path,
    monkeypatch,
) -> None:
    context = _workspace_context(tmp_path, _strict_workspace(), "historical.json")
    calls = 0
    original = analysis_module.execute_match_historical_analysis_v1

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(analysis_module, "execute_match_historical_analysis_v1", counted)
    state = build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
        selected_position=3,
        report_store=context.report_store,
    )
    before = render_match_capture_web_page_v1(state)
    assert "Strict Historical materialization is available" in before
    before_workspace = context.workspace
    before_bytes = context.workspace_path.read_bytes()
    monkeypatch.setattr(
        MatchCaptureWebContextV1,
        "save_candidate",
        lambda _self, _workspace: pytest.fail("Historical analysis attempted Save"),
    )
    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "analyze_historical_game",
            decision_snapshots=True,
            immediate_review=True,
            search_review=False,
            replay_coaching=False,
            immediate_sample_count="1",
            immediate_random_seed="0",
            search_random_seed=None,
            search_budget_profile="historical_review_v1",
            use_profile_presets=True,
        ),
    )
    assert calls == 1
    assert context.workspace is before_workspace
    assert context.workspace_path.read_bytes() == before_bytes
    html = render_match_capture_web_page_v1(result.to_dict()["state"])
    assert calls == 1
    assert "Historical Analysis report" in html
    assert "Decision Snapshot coverage" in html
    assert "Immediate Review coverage and agreement" in html
    assert "Download exact cached Historical Root Result JSON" in html


def test_complete_materialization_renders_standings_lot_and_twelve_rounds(
    tmp_path: Path,
) -> None:
    context = _workspace_context(tmp_path, _all_passed_workspace(), "list.json")
    result = execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(
            context,
            "prepare_materialization",
            position=1,
        ),
    )
    selected = result.to_dict()["state"]["selected_report"]
    assert len(selected["details"]["historical_list"]["round_end_progression"]) == 12
    html = render_match_capture_web_page_v1(result.to_dict()["state"])
    assert "Final standings" in html
    assert "lot required" in html.lower()
    assert html.count("<tr><td>") >= 12
    assert "Download Historical list input JSON" in html
    assert "Download Historical list aggregation JSON" in html


def test_complete_materialization_serves_all_cached_export_kinds(tmp_path: Path) -> None:
    context = _workspace_context(tmp_path, _all_passed_workspace(), "exports.json")
    execute_match_capture_web_analysis_v1(
        context,
        _analysis_values(context, "prepare_materialization", position=1),
    )
    server, thread = _start_server(context)
    try:
        get_headers, _post_headers = _bootstrap_analysis(server)
        match_id = context.workspace.match_definition.match_id
        expected = {
            "training-sources.json": f"{match_id}-training-sources.json",
            "historical-list-input.json": f"{match_id}-historical-list-input.json",
            "historical-list-aggregation.json": (f"{match_id}-historical-list-aggregation.json"),
        }
        for route, filename in expected.items():
            status, headers, body = _request(
                server,
                "GET",
                f"/api/v1/exports/{route}",
                headers=get_headers,
            )
            assert status == 200
            assert headers["content-disposition"] == (f'attachment; filename="{filename}"')
            assert json.loads(body)
            assert body.endswith(b"\n") and not body.endswith(b"\n\n")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
