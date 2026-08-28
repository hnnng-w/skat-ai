import hashlib
import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_match_workspace_contracts import _definition

from skatmind.match_analysis_contracts import (
    MATCH_ANALYSIS_AUTOMATION_POLICY,
    MATCH_ANALYSIS_EXECUTION_POLICY,
    MATCH_ANALYSIS_EXECUTION_STATUSES,
    MATCH_ANALYSIS_EXECUTION_VERSION,
    MATCH_ANALYSIS_EXPORT_POLICY,
    MATCH_ANALYSIS_OPERATIONS,
    MATCH_ANALYSIS_PROFILE_POLICY,
    MATCH_ANALYSIS_REPORT_ID_POLICY,
    MATCH_ANALYSIS_REPORT_KINDS,
    MATCH_ANALYSIS_REPORT_POLICY,
    MATCH_ANALYSIS_REPORT_STORE_LIMIT,
    MATCH_ANALYSIS_REPORT_STORE_VERSION,
    MATCH_ANALYSIS_REPORT_VERSION,
    MATCH_ARTIFACT_EXPORT_KINDS,
    MATCH_ARTIFACT_EXPORT_VERSION,
    MATCH_DECISION_ANALYSIS_INFORMATION_POLICY,
    MATCH_DECISION_ANALYSIS_OPTIONS_VERSION,
    MATCH_DECISION_ANALYSIS_UNAVAILABLE_REASONS,
    MATCH_HISTORICAL_ANALYSIS_OPTIONS_VERSION,
    MatchAnalysisReportV1,
    MatchDecisionAnalysisOptionsV1,
    MatchDecisionAnalysisResultV1,
    MatchHistoricalAnalysisOptionsV1,
    MatchHistoricalAnalysisResultV1,
    MatchMaterializationReportV1,
    build_match_analysis_report_v1,
    prepare_match_materialization_report_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT


def test_versions_tuples_and_policies_are_exact() -> None:
    assert (
        MATCH_ANALYSIS_EXECUTION_VERSION,
        MATCH_DECISION_ANALYSIS_OPTIONS_VERSION,
        MATCH_HISTORICAL_ANALYSIS_OPTIONS_VERSION,
        MATCH_ANALYSIS_REPORT_VERSION,
        MATCH_ANALYSIS_REPORT_STORE_VERSION,
        MATCH_ARTIFACT_EXPORT_VERSION,
    ) == (1, 1, 1, 1, 1, 1)
    assert MATCH_ANALYSIS_OPERATIONS == (
        "prepare_materialization",
        "analyze_decision",
        "analyze_historical_game",
    )
    assert MATCH_ANALYSIS_EXECUTION_STATUSES == ("executed", "unavailable")
    assert MATCH_DECISION_ANALYSIS_UNAVAILABLE_REASONS == (
        "slot_not_observed_game",
        "decision_not_retained",
        "decision_not_preparable",
    )
    assert MATCH_ANALYSIS_REPORT_KINDS == (
        "materialization",
        "decision_analysis",
        "historical_analysis",
    )
    assert MATCH_ARTIFACT_EXPORT_KINDS == (
        "report_result",
        "materialization_summary",
        "historical_game_collection",
        "training_source_collection",
        "historical_list_input",
        "historical_list_aggregation",
    )
    assert MATCH_ANALYSIS_REPORT_STORE_LIMIT == 8
    assert MATCH_ANALYSIS_EXECUTION_POLICY == (
        "explicit_existing_application_execution_once"
    )
    assert MATCH_DECISION_ANALYSIS_INFORMATION_POLICY == (
        "prepared_snapshot_plus_retrospective_actual_card"
    )
    assert MATCH_ANALYSIS_PROFILE_POLICY == (
        "eligible_relative_profiles_via_existing_application"
    )
    assert MATCH_ANALYSIS_REPORT_POLICY == (
        "ephemeral_revision_scoped_not_workspace_persisted"
    )
    assert MATCH_ANALYSIS_REPORT_ID_POLICY == (
        "sha256_canonical_analysis_report_v1"
    )
    assert MATCH_ANALYSIS_EXPORT_POLICY == (
        "authenticated_browser_download_without_server_path"
    )
    assert MATCH_ANALYSIS_AUTOMATION_POLICY == "never_execute_on_capture_mutation"
    assert tuple(field.name for field in fields(MatchDecisionAnalysisResultV1)) == (
        "match_analysis_execution_version",
        "status",
        "match_id",
        "workspace_revision",
        "match_position",
        "game_id",
        "decision_index",
        "unavailable_reason",
        "skipped_reason",
        "options",
        "profile_binding",
        "request",
        "result",
    )
    assert tuple(field.name for field in fields(MatchHistoricalAnalysisResultV1)) == (
        "match_analysis_execution_version",
        "status",
        "match_id",
        "workspace_revision",
        "match_position",
        "game_id",
        "unavailable_reason",
        "options",
        "request",
        "result",
    )
    assert tuple(field.name for field in fields(MatchMaterializationReportV1)) == (
        "match_id",
        "workspace_revision",
        "materialization",
    )
    assert tuple(field.name for field in fields(MatchAnalysisReportV1)) == (
        "match_analysis_report_version",
        "report_id",
        "report_kind",
        "match_id",
        "workspace_revision",
        "match_position",
        "decision_index",
        "value",
    )


def test_decision_options_defaults_fields_and_serialization_are_exact() -> None:
    options = MatchDecisionAnalysisOptionsV1()
    assert tuple(field.name for field in fields(options)) == (
        "match_decision_analysis_options_version",
        "recommendation_method",
        "immediate_sample_count",
        "immediate_random_seed",
        "search_random_seed",
        "search_budget_profile",
        "use_profile_presets",
    )
    assert options.to_dict() == {
        "match_decision_analysis_options_version": 1,
        "recommendation_method": "immediate_expected_value",
        "immediate_sample_count": DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        "immediate_random_seed": 0,
        "search_random_seed": None,
        "search_budget_profile": "historical_review_v1",
        "use_profile_presets": True,
    }
    first = options.to_dict()
    first["recommendation_method"] = "changed"
    assert options.to_dict()["recommendation_method"] == "immediate_expected_value"
    with pytest.raises(FrozenInstanceError):
        options.immediate_random_seed = 1


@pytest.mark.parametrize("method", ("bounded_search", "auto"))
@pytest.mark.parametrize("profile", ("interactive_v1", "historical_review_v1"))
def test_decision_search_options_are_bounded(method: str, profile: str) -> None:
    options = MatchDecisionAnalysisOptionsV1(
        recommendation_method=method,
        search_random_seed=0,
        search_budget_profile=profile,
        use_profile_presets=False,
    )
    assert options.search_random_seed == 0
    assert options.use_profile_presets is False


@pytest.mark.parametrize(
    "kwargs",
    (
        {"immediate_sample_count": 0},
        {"immediate_sample_count": 100_001},
        {"immediate_sample_count": True},
        {"immediate_random_seed": True},
        {"recommendation_method": "bounded_search"},
        {"search_random_seed": 0},
        {"search_budget_profile": "interactive_v1"},
        {"search_budget_profile": "evaluation_v1"},
        {"use_profile_presets": 1},
    ),
)
def test_decision_options_reject_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        MatchDecisionAnalysisOptionsV1(**kwargs)


def test_historical_options_defaults_modes_and_search_seed_rules() -> None:
    defaults = MatchHistoricalAnalysisOptionsV1()
    assert defaults.immediate_review is True
    assert defaults.information_set_search_review is False
    assert defaults.information_set_replay_coaching is False
    assert defaults.tactical_motif_review is False
    assert defaults.search_random_seed is None
    assert defaults.to_dict()["search_budget_profile"] == "historical_review_v1"
    snapshots = MatchHistoricalAnalysisOptionsV1(
        decision_snapshots=True,
        immediate_review=False,
    )
    assert snapshots.search_random_seed is None
    tactical = MatchHistoricalAnalysisOptionsV1(
        tactical_motif_review=True,
        immediate_review=False,
    )
    assert tactical.search_random_seed is None
    assert tactical.to_dict()["tactical_motif_review"] is True
    search = MatchHistoricalAnalysisOptionsV1(
        immediate_review=False,
        search_review=True,
        search_random_seed=0,
        search_budget_profile="interactive_v1",
        use_profile_presets=False,
    )
    assert search.search_review is True
    assert search.use_profile_presets is False
    coaching = replace(search, search_review=False, replay_coaching=True)
    assert coaching.replay_coaching is True
    information_set = replace(
        search,
        search_review=False,
        information_set_search_review=True,
    )
    assert information_set.information_set_search_review is True
    combined_information_set = replace(
        information_set,
        information_set_replay_coaching=True,
    )
    assert combined_information_set.information_set_replay_coaching is True
    assert combined_information_set.to_dict()[
        "information_set_replay_coaching"
    ] is True


@pytest.mark.parametrize(
    "kwargs",
    (
        {"immediate_review": False},
        {"search_review": True},
        {"information_set_replay_coaching": True},
        {"search_random_seed": 0},
        {
            "search_review": True,
            "information_set_search_review": True,
            "search_random_seed": 0,
        },
        {"decision_snapshots": 1},
        {"tactical_motif_review": 1},
        {"immediate_random_seed": True},
        {"search_budget_profile": "interactive_v1"},
        {"search_budget_profile": "evaluation_v1"},
    ),
)
def test_historical_options_reject_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        MatchHistoricalAnalysisOptionsV1(**kwargs)


def test_materialization_report_is_once_defensive_and_sha256_identified(
    monkeypatch,
) -> None:
    import skatmind.match_analysis_contracts as contracts_module

    workspace = create_match_workspace_v1(_definition())
    original = contracts_module.build_match_workspace_materialization_v1
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        contracts_module,
        "build_match_workspace_materialization_v1",
        counted,
    )
    value = prepare_match_materialization_report_v1(workspace)
    report = build_match_analysis_report_v1(value)
    assert calls == 1
    assert len(report.report_id) == 64
    assert report.report_id == report.report_id.lower()
    identity = report.to_dict()
    del identity["report_id"]
    canonical = json.dumps(
        identity,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert report.report_id == hashlib.sha256(
        b"skatmind\0match_analysis_report_v1\0" + canonical
    ).hexdigest()
    assert build_match_analysis_report_v1(value).report_id == report.report_id
    serialized = report.to_dict()
    serialized["value"]["materialization"]["slot_materializations"].clear()
    assert len(report.to_dict()["value"]["materialization"]["slot_materializations"]) == 36
