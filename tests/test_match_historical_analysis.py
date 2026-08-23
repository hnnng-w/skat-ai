import pytest
from test_match_player_statistics_context import (
    _actionable_snapshot,
    _capture_with_snapshots,
)
from test_match_workspace_contracts import (
    _complete_observed_game,
    _definition,
    _observed_game,
    _set_game,
)

from skat_ai.application.execution import (
    ApplicationWorkflowDependencies,
)
from skat_ai.application.execution import (
    execute_application_invocation as real_execute_application_invocation,
)
from skat_ai.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
)
from skat_ai.match_analysis_contracts import MatchHistoricalAnalysisOptionsV1
from skat_ai.match_historical_analysis import execute_match_historical_analysis_v1
from skat_ai.match_historical_information_set_analysis import (
    MATCH_HISTORICAL_INFORMATION_SET_COACHING_INTEGRATION_VERSION,
    MATCH_HISTORICAL_INFORMATION_SET_COACHING_POLICY,
    MATCH_HISTORICAL_INFORMATION_SET_MODE_POLICY,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_operations import mark_match_workspace_passed_deal_v1


def _strict_workspace(*, definition=None):
    definition = definition or _definition()
    return _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition, match_position=3),
    )


def test_match_historical_information_set_version_and_policies_are_exact() -> None:
    assert MATCH_HISTORICAL_INFORMATION_SET_COACHING_INTEGRATION_VERSION == 1
    assert MATCH_HISTORICAL_INFORMATION_SET_COACHING_POLICY == (
        "one_historical_application_with_shared_information_set_review"
    )
    assert MATCH_HISTORICAL_INFORMATION_SET_MODE_POLICY == (
        "separate_from_existing_pimc_replay_coaching"
    )


def test_empty_passed_and_incomplete_historical_analysis_are_normal_unavailable() -> None:
    options = MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1)
    empty = create_match_workspace_v1(_definition())
    assert execute_match_historical_analysis_v1(
        empty,
        match_position=1,
        options=options,
    ).unavailable_reason == "slot_empty"
    passed = mark_match_workspace_passed_deal_v1(
        empty,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    assert execute_match_historical_analysis_v1(
        passed,
        match_position=1,
        options=options,
    ).unavailable_reason == "passed_deal"
    definition = _definition()
    complete = _complete_observed_game(definition, match_position=3)
    partial = _observed_game(
        definition,
        game_id=complete.game_id,
        match_position=complete.match_position,
        game_timecode=complete.game_timecode,
        seat_order_player_ids=tuple(player.player_id for player in complete.players),
        perspective_initial_hand=complete.perspective_initial_hand,
        declarer_player_id=complete.declarer_player_id,
        declaration=complete.declaration,
        original_skat=complete.original_skat,
        discarded_cards=complete.discarded_cards,
        plays=complete.plays[:3],
        commentaries=(),
        response_links=(),
    )
    incomplete = _set_game(create_match_workspace_v1(definition), partial)
    result = execute_match_historical_analysis_v1(
        incomplete,
        match_position=3,
        options=options,
    )
    assert result.status == "unavailable"
    assert result.unavailable_reason == "incomplete_play_trace"
    assert result.request is None
    assert result.result is None


def test_historical_immediate_review_executes_application_once(monkeypatch) -> None:
    import skat_ai.match_historical_analysis as analysis_module

    workspace = _strict_workspace()
    calls = 0
    validations = 0

    def counted(invocation, **kwargs):
        nonlocal calls
        calls += 1
        return real_execute_application_invocation(invocation, **kwargs)

    def counted_validation(document):
        nonlocal validations
        validations += 1
        from skat_ai.api.v1.schema_validation import validate_output_document

        validate_output_document(document)

    monkeypatch.setattr(analysis_module, "execute_application_invocation", counted)
    monkeypatch.setattr(analysis_module, "validate_output_document", counted_validation)
    result = execute_match_historical_analysis_v1(
        workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1),
    )
    assert calls == 1
    assert validations == 1
    assert result.status == "executed"
    assert result.request is not None
    assert set(result.request.document) == {"historical_game_input"}
    document = result.result.to_dict()["document"]
    assert document["input_file"] == (
        f"match:{result.match_id}:workspace:{workspace.revision}:position:3:historical"
    )
    summary = document["historical_game_summary"]
    assert summary["game_id"] == result.game_id
    assert summary["historical_game_review_summary"]["decision_count"] == 30


def test_decision_snapshots_only_does_not_inject_statistics() -> None:
    definition = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
        )
    )
    result = execute_match_historical_analysis_v1(
        _strict_workspace(definition=definition),
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            decision_snapshots=True,
            immediate_review=False,
        ),
    )
    document = result.result.to_dict()["document"]
    assert document["historical_game_summary"]["decision_snapshot_summary"][
        "snapshot_count"
    ] == 30
    assert "historical_opponent_profile_application_summary" not in document


def test_historical_profiles_are_injected_only_for_enabled_immediate_review() -> None:
    definition = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
        )
    )
    workspace = _strict_workspace(definition=definition)
    enabled = execute_match_historical_analysis_v1(
        workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1),
    )
    document = enabled.result.to_dict()["document"]
    application = document["historical_opponent_profile_application_summary"]
    assert application["matched_player_count"] == 2
    matches = {item["player_id"]: item for item in application["participant_matches"]}
    assert set(matches) == {"player-a", "player-b", "player-c"}
    assert matches["player-a"]["match_status"] == "matched"
    assert matches["player-b"]["match_status"] == "matched"
    assert matches["player-c"]["match_status"] == "unmatched"
    decisions = document["historical_game_summary"]["historical_game_review_summary"][
        "decisions"
    ]
    assert all(
        decision["opponent_profile_application"]["acting_player_id"]
        not in {
            decision["opponent_profile_application"]["left_opponent_player_id"],
            decision["opponent_profile_application"]["right_opponent_player_id"],
        }
        for decision in decisions
    )

    disabled = execute_match_historical_analysis_v1(
        workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            immediate_sample_count=1,
            use_profile_presets=False,
        ),
    )
    assert "historical_opponent_profile_application_summary" not in (
        disabled.result.to_dict()["document"]
    )


def test_historical_search_and_coaching_modes_route_through_existing_application(
    monkeypatch,
) -> None:
    calls = []

    def stub_search(**kwargs):
        calls.append(("search", kwargs["base_search_seed"]))
        return {"status": "stub-search"}

    def stub_coaching(**kwargs):
        calls.append(("coaching", kwargs["base_search_seed"]))
        return {
            "historical_search_review_summary": {"status": "stub-search"},
            "historical_replay_coaching_summary": {"status": "stub-coaching"},
        }

    dependencies = ApplicationWorkflowDependencies(
        historical_game=HistoricalGameWorkflowDependencies(
            build_search_review=stub_search,
            build_replay_coaching=stub_coaching,
        )
    )
    import skat_ai.match_historical_analysis as analysis_module

    monkeypatch.setattr(
        analysis_module,
        "validate_output_document",
        lambda _document: None,
    )
    search = execute_match_historical_analysis_v1(
        _strict_workspace(),
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            immediate_review=False,
            search_review=True,
            search_random_seed=7,
        ),
        dependencies=dependencies,
    )
    coaching = execute_match_historical_analysis_v1(
        _strict_workspace(),
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            immediate_review=False,
            replay_coaching=True,
            search_random_seed=9,
        ),
        dependencies=dependencies,
    )
    assert search.result.to_dict()["document"]["historical_game_summary"][
        "historical_search_review_summary"
    ] == {"status": "stub-search"}
    assert coaching.result.to_dict()["document"]["historical_game_summary"][
        "historical_replay_coaching_summary"
    ] == {"status": "stub-coaching"}
    assert calls == [("search", 7), ("coaching", 9)]


def test_historical_information_set_review_and_coaching_share_one_application(
    monkeypatch,
) -> None:
    import skat_ai.match_historical_analysis as analysis_module

    application_calls = 0
    review_calls = 0
    coaching_calls = 0

    def counted_application(invocation, **kwargs):
        nonlocal application_calls
        application_calls += 1
        return real_execute_application_invocation(invocation, **kwargs)

    def build_review(**kwargs):
        nonlocal review_calls
        review_calls += 1
        return {"source_game_id": kwargs["historical_record"].game_id}

    class StubCoachingReport:
        def __init__(self, game_id: str) -> None:
            self.game_id = game_id

        def to_dict(self):
            return {
                "source_game_id": self.game_id,
                "report_method": "historical_information_set_replay_coaching_v1",
            }

    def build_coaching(**kwargs):
        nonlocal coaching_calls
        coaching_calls += 1
        assert kwargs["source_review"] == {
            "source_game_id": kwargs["historical_record"].game_id
        }
        return StubCoachingReport(kwargs["historical_record"].game_id)

    dependencies = ApplicationWorkflowDependencies(
        historical_game=HistoricalGameWorkflowDependencies(
            build_information_set_search_review=build_review,
            build_information_set_replay_coaching=build_coaching,
            serialize_information_set_replay_coaching=lambda report: report.to_dict(),
        )
    )
    monkeypatch.setattr(
        analysis_module,
        "execute_application_invocation",
        counted_application,
    )
    monkeypatch.setattr(analysis_module, "validate_output_document", lambda _document: None)

    result = execute_match_historical_analysis_v1(
        _strict_workspace(),
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            immediate_review=False,
            information_set_search_review=True,
            information_set_replay_coaching=True,
            search_random_seed=13,
            immediate_sample_count=1,
        ),
        dependencies=dependencies,
    )

    assert application_calls == 1
    assert review_calls == 1
    assert coaching_calls == 1
    assert result.request is not None
    summary = result.result.to_dict()["document"]["historical_game_summary"]
    assert summary["historical_information_set_search_review_summary"] == {
        "source_game_id": result.game_id
    }
    assert summary["historical_information_set_replay_coaching_summary"][
        "source_game_id"
    ] == result.game_id


def test_historical_information_set_profiles_do_not_change_classic_family(
    monkeypatch,
) -> None:
    import skat_ai.match_historical_analysis as analysis_module

    definition = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
        )
    )
    workspace = _strict_workspace(definition=definition)
    information_set_bindings = []

    def build_information_set_review(**kwargs):
        information_set_bindings.append(kwargs["effective_policy_settings_by_decision"])
        return {"source_game_id": kwargs["historical_record"].game_id}

    information_set_dependencies = ApplicationWorkflowDependencies(
        historical_game=HistoricalGameWorkflowDependencies(
            build_information_set_search_review=build_information_set_review,
        )
    )
    monkeypatch.setattr(analysis_module, "validate_output_document", lambda _document: None)
    information_set = execute_match_historical_analysis_v1(
        workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            immediate_review=False,
            information_set_search_review=True,
            search_random_seed=17,
            immediate_sample_count=1,
        ),
        dependencies=information_set_dependencies,
    )
    information_set_document = information_set.result.to_dict()["document"]
    assert information_set_document[
        "historical_opponent_profile_application_summary"
    ]["matched_player_count"] == 2
    assert len(information_set_bindings) == 1

    def build_classic_coaching(**_kwargs):
        return {
            "historical_search_review_summary": {"status": "unused"},
            "historical_replay_coaching_summary": {"status": "classic"},
        }

    classic_dependencies = ApplicationWorkflowDependencies(
        historical_game=HistoricalGameWorkflowDependencies(
            build_replay_coaching=build_classic_coaching,
        )
    )
    classic = execute_match_historical_analysis_v1(
        workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            immediate_review=False,
            replay_coaching=True,
            search_random_seed=19,
            immediate_sample_count=1,
        ),
        dependencies=classic_dependencies,
    )
    assert "historical_opponent_profile_application_summary" not in (
        classic.result.to_dict()["document"]
    )


def test_historical_unavailable_performs_no_application_call(monkeypatch) -> None:
    import skat_ai.match_historical_analysis as analysis_module

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Application must not execute for unavailable evidence.")

    monkeypatch.setattr(analysis_module, "execute_application_invocation", forbidden)
    result = execute_match_historical_analysis_v1(
        create_match_workspace_v1(_definition()),
        match_position=1,
        options=MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1),
    )
    assert result.unavailable_reason == "slot_empty"


def test_historical_options_type_is_strict() -> None:
    with pytest.raises(ValueError, match="options"):
        execute_match_historical_analysis_v1(
            _strict_workspace(),
            match_position=3,
            options=None,
        )
