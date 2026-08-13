from dataclasses import replace

import pytest
from test_historical_game import build_historical_input
from test_match_decision_review_preparation import _workspace_with_partial_game
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
from test_observed_game_contracts import (
    declaration_from_historical,
    observed_plays_from_historical,
)

from skat_ai.application.execution import (
    ApplicationWorkflowDependencies,
)
from skat_ai.application.execution import (
    execute_application_invocation as real_execute_application_invocation,
)
from skat_ai.application.position_workflow import (
    PositionWorkflowDependencies,
)
from skat_ai.match_analysis_contracts import MatchDecisionAnalysisOptionsV1
from skat_ai.match_decision_analysis import (
    build_match_decision_position_request_v1,
    execute_match_decision_analysis_v1,
    select_match_prepared_decision_v1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_operations import mark_match_workspace_passed_deal_v1
from skat_ai.rules import get_card_points, get_legal_cards


def _complete_workspace(*, definition=None, game_type="grand"):
    definition = definition or _definition()
    data = build_historical_input(game_type=game_type)
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data),
    )
    return _set_game(create_match_workspace_v1(definition), game)


def test_selector_supports_partial_decision_without_historical_materialization() -> None:
    workspace, _data = _workspace_with_partial_game()
    preparation, snapshot, binding = select_match_prepared_decision_v1(
        workspace,
        match_position=3,
        decision_index=1,
    )
    assert preparation.status == "partial"
    assert snapshot.decision_index == 1
    assert binding.decision_index == 1
    assert preparation.game_id == snapshot.source_game_id


def test_decision_unavailability_is_normal_and_executes_nothing(monkeypatch) -> None:
    import skat_ai.match_decision_analysis as analysis_module

    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("Application must not run.")

    monkeypatch.setattr(analysis_module, "execute_application_invocation", forbidden)
    options = MatchDecisionAnalysisOptionsV1(immediate_sample_count=1)
    empty = create_match_workspace_v1(_definition())
    result = execute_match_decision_analysis_v1(
        empty,
        match_position=1,
        decision_index=1,
        options=options,
    )
    assert result.status == "unavailable"
    assert result.unavailable_reason == "slot_not_observed_game"
    partial, _data = _workspace_with_partial_game()
    skipped = execute_match_decision_analysis_v1(
        partial,
        match_position=3,
        decision_index=2,
        options=options,
    )
    assert skipped.unavailable_reason == "decision_not_preparable"
    assert skipped.skipped_reason == "acting_hand_unavailable"
    absent = execute_match_decision_analysis_v1(
        partial,
        match_position=3,
        decision_index=30,
        options=options,
    )
    assert absent.unavailable_reason == "decision_not_retained"
    assert calls == 0


@pytest.mark.parametrize("game_type", ("clubs", "grand", "null"))
def test_position_request_preserves_decision_time_information(game_type: str) -> None:
    workspace = _complete_workspace(game_type=game_type)
    prepared = build_match_decision_position_request_v1(
        workspace,
        match_position=3,
        decision_index=5,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    root = prepared.request.to_dict()["document"]
    preparation, snapshot, binding = select_match_prepared_decision_v1(
        workspace,
        match_position=3,
        decision_index=5,
    )
    state = snapshot.visible_state
    assert root["hand"] == list(state.own_hand)
    assert get_legal_cards(root["hand"], root["current_trick"], game_type) == list(
        state.legal_cards
    )
    assert root["completed_tricks"]
    assert root["current_trick"]
    assert root["declarer_points"] == 0
    assert root["defender_points"] == 0
    assert sum(
        sum(get_card_points(card) for card in trick["cards"])
        for trick in root["completed_tricks"]
        if trick["winner_role"] == "declarer"
    ) == state.declarer_trick_points
    assert sum(
        sum(get_card_points(card) for card in trick["cards"])
        for trick in root["completed_tricks"]
        if trick["winner_role"] == "defenders"
    ) == state.defender_trick_points
    assert root["player_position"] == snapshot.acting_seat
    assert root["player_role"] == (
        "declarer" if snapshot.acting_side == "declarer" else "defender"
    )
    assert root["left_hand_size"] == state.opponent_hand_sizes[0].remaining_card_count
    assert root["right_hand_size"] == state.opponent_hand_sizes[1].remaining_card_count
    assert root["analysis_mode"] == "post_game_review"
    assert root["actual_card_played"] == snapshot.actual_card_played
    assert root["game_end_reason"] == "not_ended"
    assert root["recommendation_method"] == "immediate_expected_value"
    assert "bounded_search_settings" not in root
    assert "commentaries" not in root
    assert "response_links" not in root
    assert "final_settlement_summary" not in root
    assert preparation.game_id == snapshot.source_game_id
    assert prepared.profile_binding == binding


def test_position_request_preserves_unknown_bid_and_search_budget() -> None:
    definition = _definition()
    data = build_historical_input(game_type="grand")
    declaration = replace(declaration_from_historical(data), bid_value=None)
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration,
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data, count=1),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    prepared = build_match_decision_position_request_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(
            recommendation_method="bounded_search",
            immediate_sample_count=1,
            search_random_seed=7,
            search_budget_profile="interactive_v1",
        ),
    )
    root = prepared.request.to_dict()["document"]
    assert root["game_declaration"]["bid_value"] is None
    assert root["bounded_search_settings"] == {
        "random_seed": 7,
        "max_remaining_tricks": 3,
        "max_depth_plies": 9,
        "max_nodes": 500_000,
        "max_selected_worlds": 64,
        "max_sampled_worlds": 32,
        "minimum_comparable_worlds": 8,
        "wall_clock_timeout_ms": 1_000,
    }


def test_execution_preserves_unknown_decision_time_matadors() -> None:
    definition = _capture_with_snapshots()
    source = _complete_observed_game(definition, match_position=3)
    game = _observed_game(
        definition,
        match_position=3,
        game_id=source.game_id,
        perspective_initial_hand=source.perspective_initial_hand,
        declarer_player_id=source.declarer_player_id,
        declaration=source.declaration,
        original_skat=source.original_skat,
        discarded_cards=None,
        plays=source.plays,
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    _preparation, snapshot, _binding = select_match_prepared_decision_v1(
        workspace,
        match_position=3,
        decision_index=2,
    )
    assert snapshot.visible_state.declaration.matadors is None

    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=2,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    assert result.status == "executed"
    assert result.request.to_dict()["document"]["game_declaration"]["matadors"] is None
    assert result.result.to_dict()["document"]["game_declaration"]["matadors"] is None


def test_immediate_execution_once_validates_result_and_actual_card(monkeypatch) -> None:
    import skat_ai.match_decision_analysis as analysis_module

    workspace = _complete_workspace()
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
    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    assert calls == 1
    assert validations == 1
    assert result.status == "executed"
    assert result.result is not None
    document = result.result.to_dict()["document"]
    assert document["input_file"] == (
        f"match:{result.match_id}:workspace:{workspace.revision}:position:3:decision:1"
    )
    assert document["post_game_review_summary"]["actual_card_played"] == (
        result.request.to_dict()["document"]["actual_card_played"]
    )


def test_profile_binding_excludes_actor_applies_sides_and_can_be_disabled() -> None:
    definition = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
            _actionable_snapshot("player-c", "snapshot-c"),
        )
    )
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition, match_position=3),
    )
    enabled = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    assert enabled.profile_binding is not None
    summary = enabled.result.to_dict()["document"][
        "opponent_profile_application_summary"
    ]
    actor = enabled.profile_binding.acting_player_id
    assert {summary["left"]["bound_player_id"], summary["right"]["bound_player_id"]} == {
        enabled.profile_binding.left_opponent_player_id,
        enabled.profile_binding.right_opponent_player_id,
    }
    assert actor not in {
        summary["left"]["bound_player_id"],
        summary["right"]["bound_player_id"],
    }
    assert summary["left"]["application_status"] == "applied"
    assert summary["right"]["application_status"] == "applied"

    disabled = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(
            immediate_sample_count=1,
            use_profile_presets=False,
        ),
    )
    disabled_document = disabled.result.to_dict()["document"]
    assert "opponent_profile_application_summary" not in disabled_document
    assert disabled.profile_binding is not None
    assert disabled.profile_binding.left_profile_available is True
    assert disabled.profile_binding.right_profile_available is True
    assert disabled_document["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_search_unavailable_remains_an_executed_root_result() -> None:
    workspace = _complete_workspace()
    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(
            recommendation_method="bounded_search",
            immediate_sample_count=1,
            search_random_seed=0,
            search_budget_profile="interactive_v1",
        ),
    )
    assert result.status == "executed"
    search = result.result.to_dict()["document"]["bounded_search_result"]
    assert search["status"] == "unavailable"


def test_late_bounded_search_executes_with_profile_budget() -> None:
    workspace = _complete_workspace()
    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=22,
        options=MatchDecisionAnalysisOptionsV1(
            recommendation_method="bounded_search",
            immediate_sample_count=1,
            search_random_seed=0,
            search_budget_profile="interactive_v1",
        ),
    )
    assert result.status == "executed"
    document = result.result.to_dict()["document"]
    assert document["bounded_search_result"]["status"] == "complete"
    assert document["recommendation_method_summary"]["requested_method"] == (
        "bounded_search"
    )


def test_application_post_game_profile_compatibility_is_narrow() -> None:
    workspace = _complete_workspace(
        definition=_capture_with_snapshots(
            snapshots=(_actionable_snapshot("player-a", "snapshot-a"),)
        )
    )
    prepared = build_match_decision_position_request_v1(
        workspace,
        match_position=3,
        decision_index=2,
        options=MatchDecisionAnalysisOptionsV1(
            immediate_sample_count=1,
            use_profile_presets=False,
        ),
    )
    root = prepared.request.to_dict()["document"]
    root["game_end_reason"] = "normal_completion"
    from skat_ai.application.execution import build_application_invocation
    from skat_ai.errors import SkatAIWorkflowError

    invocation = build_application_invocation(
        root,
        input_reference=prepared.input_reference,
        options=prepared.application_options,
        external_documents=prepared.external_documents,
    )
    with pytest.raises(SkatAIWorkflowError, match="flat nonterminal"):
        real_execute_application_invocation(invocation)


def test_passed_slot_is_normal_unavailable() -> None:
    workspace = mark_match_workspace_passed_deal_v1(
        create_match_workspace_v1(_definition()),
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=1,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
        dependencies=ApplicationWorkflowDependencies(
            position=PositionWorkflowDependencies()
        ),
    )
    assert result.unavailable_reason == "slot_not_observed_game"
