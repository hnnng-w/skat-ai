import json
from pathlib import Path

import pytest

import skatmind.application.position_workflow as position_module
from skatmind.application.contracts import PositionAnalysisApplicationOptions
from skatmind.application.position_workflow import (
    PositionWorkflowDependencies,
    build_position_analysis_result,
    execute_position_analysis_workflow,
)
from skatmind.effective_opponent_policy import (
    build_effective_opponent_policy_settings,
)
from skatmind.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
    convert_information_set_search_budget_to_requested_search_budget_v1,
)
from skatmind.recommendation_workflow import (
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    SEARCH_RECOMMENDATION_METHODS,
)

ROOT = Path(__file__).resolve().parents[1]
INFORMATION_SET_SEARCH_SETTINGS = {
    "random_seed": 113,
    "max_remaining_tricks": 1,
    "max_depth_plies": 3,
    "max_state_nodes": 10_000,
    "max_information_sets": 10_000,
    "max_selected_worlds": 1,
    "max_sampled_worlds": 1,
    "minimum_comparable_worlds": 1,
    "wall_clock_timeout_ms": None,
}


def _position(*, post_game: bool) -> dict:
    name = (
        "grand_bounded_search_post_game_review.json"
        if post_game
        else "grand_bounded_search_exhaustive.json"
    )
    data = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    data["recommendation_method"] = INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
    data["information_set_search_settings"] = dict(INFORMATION_SET_SEARCH_SETTINGS)
    data.pop("bounded_search_settings")
    return data


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value))
    return set()


def test_live_position_forwards_effective_settings_and_runs_no_baselines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    effective_settings = build_effective_opponent_policy_settings({})
    original_execute = position_module.execute_recommendation_workflow
    calls: list[dict] = []

    def execute(**kwargs):
        calls.append(kwargs)
        return original_execute(**kwargs)

    monkeypatch.setattr(position_module, "execute_recommendation_workflow", execute)
    monkeypatch.setattr(
        position_module,
        "solve_compatible_world_minimax_on_selection_v1",
        lambda **_kwargs: pytest.fail("live Position ran a PIMC baseline"),
    )

    result = build_position_analysis_result(
        _position(post_game=False),
        input_reference="memory:live-information-set-search",
        options=PositionAnalysisApplicationOptions(),
        effective_opponent_policy_settings=effective_settings,
        dependencies=PositionWorkflowDependencies(
            immediate_recommender=lambda **_kwargs: pytest.fail(
                "live Position ran an Immediate baseline"
            )
        ),
    )

    assert len(calls) == 1
    assert calls[0]["configuration"].requested_method == (
        INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
    )
    assert calls[0]["effective_opponent_policy_settings"] is effective_settings
    assert result["settings"]["information_set_search_settings"] == (
        INFORMATION_SET_SEARCH_SETTINGS
    )
    assert result["settings"]["bounded_search_settings"] is None
    assert result["bounded_search_result"] is None
    assert result["information_set_search_result"]["status"] == "complete"
    assert (
        result["recommendation"]["card"]
        == result["information_set_search_result"]["recommended_card"]
    )
    assert "information_set_search_comparison" not in result
    assert {
        "controlled_policy",
        "information_set",
        "observation",
        "exact_states",
        "world_states",
        "own_remaining_hand",
    }.isdisjoint(_all_keys(result["information_set_search_result"]))


def test_post_game_position_runs_pre_actual_stages_in_order_on_retained_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _position(post_game=True)
    effective_settings = build_effective_opponent_policy_settings({})
    original_execute = position_module.execute_recommendation_workflow
    original_pimc = position_module.solve_compatible_world_minimax_on_selection_v1
    original_pre_actual = (
        position_module.build_information_set_search_comparison_pre_actual_analysis_v1
    )
    original_actual_reader = position_module.get_actual_card_played_from_input
    original_attach = position_module.attach_actual_card_to_information_set_search_comparison_v1
    original_serialize = position_module.build_serializable_information_set_search_comparison_v1
    events: list[str] = []
    retained: dict[str, object] = {}

    def execute(**kwargs):
        configuration = kwargs["configuration"]
        assert kwargs["effective_opponent_policy_settings"] is effective_settings
        if configuration.requested_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
            events.append("primary")
            result = original_execute(**kwargs)
            workflow = result.information_set_search_workflow
            assert workflow is not None
            assert workflow.preparation is not None
            assert workflow.preparation.world_selection is not None
            retained["workflow"] = workflow
            retained["selection"] = workflow.preparation.world_selection
            events.append("primary_complete")
            return result
        assert configuration.requested_method == IMMEDIATE_EXPECTED_VALUE_METHOD
        assert "selection" not in kwargs
        assert kwargs["immediate_random_seed"] == data["random_seed"]
        assert kwargs["sample_count"] == data["sample_count"]
        events.append("immediate")
        result = original_execute(**kwargs)
        events.append("immediate_complete")
        return result

    def solve_pimc(**kwargs):
        assert events[-1] == "primary_complete"
        workflow = retained["workflow"]
        assert kwargs["selection"] is retained["selection"]
        assert kwargs["information_view"] is workflow.request.information_view
        assert kwargs["requested_budget"] == (
            convert_information_set_search_budget_to_requested_search_budget_v1(
                workflow.request.requested_budget
            )
        )
        events.append("pimc")
        result = original_pimc(**kwargs)
        events.append("pimc_complete")
        return result

    def build_pre_actual(**kwargs):
        assert events[-1] == "immediate_complete"
        assert kwargs["same_selected_world_sequence"] is True
        events.append("comparison_pre_actual")
        return original_pre_actual(**kwargs)

    def read_actual_card(value):
        assert events[-1] == "comparison_pre_actual"
        events.append("actual_card")
        return original_actual_reader(value)

    def attach_actual(analysis, actual_card):
        assert events[-1] == "actual_card"
        assert actual_card == data["actual_card_played"]
        events.append("attach_actual")
        return original_attach(analysis, actual_card)

    def serialize(comparison):
        assert events[-1] == "attach_actual"
        events.append("serialize_comparison")
        return original_serialize(comparison)

    monkeypatch.setattr(position_module, "execute_recommendation_workflow", execute)
    monkeypatch.setattr(
        position_module,
        "solve_compatible_world_minimax_on_selection_v1",
        solve_pimc,
    )
    monkeypatch.setattr(
        position_module,
        "build_information_set_search_comparison_pre_actual_analysis_v1",
        build_pre_actual,
    )
    monkeypatch.setattr(
        position_module,
        "get_actual_card_played_from_input",
        read_actual_card,
    )
    monkeypatch.setattr(
        position_module,
        "attach_actual_card_to_information_set_search_comparison_v1",
        attach_actual,
    )
    monkeypatch.setattr(
        position_module,
        "build_serializable_information_set_search_comparison_v1",
        serialize,
    )

    result = build_position_analysis_result(
        data,
        input_reference="memory:post-game-information-set-search",
        options=PositionAnalysisApplicationOptions(),
        effective_opponent_policy_settings=effective_settings,
    )

    assert events == [
        "primary",
        "primary_complete",
        "pimc",
        "pimc_complete",
        "immediate",
        "immediate_complete",
        "comparison_pre_actual",
        "actual_card",
        "attach_actual",
        "serialize_comparison",
    ]
    comparison = result["information_set_search_comparison"]
    assert comparison["comparison_status"] == "available"
    assert comparison["same_selected_world_sequence"] is True
    assert comparison["actual_card"] == data["actual_card_played"]
    assert comparison["information_set_recommended_card"] == result["recommendation"]["card"]
    assert result["recommendation_method_summary"]["fallback_used"] is False
    assert result["recommendation_method_summary"]["fallback_method"] is None


def test_information_set_method_is_forwarded_to_multi_step_and_policy_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, dict] = {}

    def simulate(**kwargs):
        observed["multi_step"] = kwargs
        return {"kind": "multi_step"}

    def compare(**kwargs):
        observed["policy_comparison"] = kwargs
        return {"kind": "policy_comparison"}

    monkeypatch.setattr(
        position_module,
        "build_serializable_multi_step_result",
        lambda value: value,
    )
    monkeypatch.setattr(
        position_module,
        "build_serializable_policy_comparison_result",
        lambda value: value,
    )

    result = execute_position_analysis_workflow(
        _position(post_game=False),
        input_reference="memory:flat-only-information-set-search",
        options=PositionAnalysisApplicationOptions(
            multi_step_count=1,
            compare_policies=True,
        ),
        dependencies=PositionWorkflowDependencies(
            multi_step_simulator=simulate,
            policy_comparator=compare,
        ),
    )

    assert INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD not in (SEARCH_RECOMMENDATION_METHODS)
    assert observed["multi_step"]["card_selection_policy"] == (
        INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
    )
    assert observed["multi_step"]["recommendation_configuration"].requested_method == (
        INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
    )
    assert observed["multi_step"]["effective_opponent_policy_settings"] is (
        observed["policy_comparison"]["effective_opponent_policy_settings"]
    )
    assert observed[
        "policy_comparison"
    ]["recommendation_configuration"].requested_method == (
        INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
    )
    assert result["multi_step_result"] == {"kind": "multi_step"}
    assert result["policy_comparison_result"] == {"kind": "policy_comparison"}
