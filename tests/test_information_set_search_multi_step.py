from dataclasses import replace
from pathlib import Path

import pytest

import skat_ai.multi_step_simulation as multi_step_module
from skat_ai.card_selection import (
    DEFAULT_POLICY_COMPARISON_POLICIES,
    SEARCH_AWARE_MULTI_STEP_POLICIES,
    VALID_CARD_SELECTION_POLICIES,
    VALID_MULTI_STEP_POLICIES,
)
from skat_ai.cli.presentation.simulation import (
    print_multi_step_result,
    print_policy_comparison_result,
)
from skat_ai.coherent_hidden_world import (
    CoherentHiddenWorld,
    derive_simulation_child_seed,
)
from skat_ai.deck import get_full_deck
from skat_ai.effective_opponent_policy import (
    build_effective_opponent_policy_settings,
)
from skat_ai.exact_search_state import (
    apply_exact_search_card,
    build_exact_search_state,
    get_exact_search_legal_cards,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.information_set_search_multi_step import (
    INFORMATION_SET_SEARCH_AUTO_COMPATIBILITY_POLICY,
    INFORMATION_SET_SEARCH_MULTI_STEP_DECISION_VERSION,
    INFORMATION_SET_SEARCH_MULTI_STEP_EXECUTION_POLICY,
    INFORMATION_SET_SEARCH_MULTI_STEP_INTEGRATION_VERSION,
    INFORMATION_SET_SEARCH_MULTI_STEP_POLICY_RETENTION_POLICY,
    INFORMATION_SET_SEARCH_MULTI_STEP_SEED_POLICY,
    INFORMATION_SET_SEARCH_MULTI_STEP_SOURCE_POLICY,
    INFORMATION_SET_SEARCH_MULTI_STEP_STOP_POLICY,
    INFORMATION_SET_SEARCH_POLICY_COMPARISON_ELIGIBILITY_POLICY,
    INFORMATION_SET_SEARCH_POLICY_COMPARISON_INTEGRATION_VERSION,
    INFORMATION_SET_SEARCH_POLICY_COMPARISON_METHOD_POLICY,
    INFORMATION_SET_SEARCH_POLICY_COMPARISON_ROOT_POLICY,
    INFORMATION_SET_SEARCH_SIMULATION_PUBLIC_POLICY,
    MULTI_STEP_INFORMATION_SET_SEARCH_DECISION_STREAM,
    InformationSetSearchMultiStepDecisionV1,
    build_compact_information_set_search_decision_diagnostic_v1,
    build_serializable_information_set_search_multi_step_decision_v1,
    derive_information_set_search_multi_step_configuration_v1,
)
from skat_ai.input_loader import (
    build_local_game_state_from_input,
    get_analysis_metadata_from_input,
    get_game_declaration_from_input,
    get_recommendation_method_configuration_from_input,
    get_simulation_settings_from_input,
    load_position_from_json,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.recommendation_workflow import SEARCH_RECOMMENDATION_METHODS
from skat_ai.result_serialization import build_serializable_multi_step_result

ROOT = Path(__file__).resolve().parents[1]


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value))
    return set()


def _inputs() -> tuple:
    data = load_position_from_json(str(ROOT / "examples" / "information_set_search.json"))
    return (
        data,
        build_local_game_state_from_input(data),
        get_simulation_settings_from_input(data),
        get_game_declaration_from_input(data),
        get_analysis_metadata_from_input(data).strategic_metadata,
        get_recommendation_method_configuration_from_input(data),
        build_effective_opponent_policy_settings(data),
    )


def test_information_set_multi_step_versions_policies_and_vocabulary_are_exact() -> None:
    assert INFORMATION_SET_SEARCH_MULTI_STEP_INTEGRATION_VERSION == 1
    assert INFORMATION_SET_SEARCH_MULTI_STEP_DECISION_VERSION == 1
    assert INFORMATION_SET_SEARCH_POLICY_COMPARISON_INTEGRATION_VERSION == 1
    assert INFORMATION_SET_SEARCH_MULTI_STEP_SOURCE_POLICY == (
        "current_public_decision_boundary_without_coherent_world_disclosure"
    )
    assert INFORMATION_SET_SEARCH_MULTI_STEP_EXECUTION_POLICY == (
        "fresh_strict_information_set_search_per_local_decision"
    )
    assert INFORMATION_SET_SEARCH_MULTI_STEP_SEED_POLICY == (
        "domain_separated_per_decision_world_selection_seed"
    )
    assert INFORMATION_SET_SEARCH_MULTI_STEP_STOP_POLICY == (
        "no_recommendation_stops_before_local_play"
    )
    assert INFORMATION_SET_SEARCH_MULTI_STEP_POLICY_RETENTION_POLICY == (
        "private_per_decision_policy_not_reused_across_steps"
    )
    assert INFORMATION_SET_SEARCH_POLICY_COMPARISON_ROOT_POLICY == (
        "shared_coherent_root_with_independent_immutable_paths"
    )
    assert INFORMATION_SET_SEARCH_POLICY_COMPARISON_METHOD_POLICY == (
        "exactly_one_configured_search_policy_appended_last"
    )
    assert INFORMATION_SET_SEARCH_POLICY_COMPARISON_ELIGIBILITY_POLICY == (
        "stopped_search_path_visible_but_ineligible"
    )
    assert INFORMATION_SET_SEARCH_AUTO_COMPATIBILITY_POLICY == (
        "existing_auto_remains_pimc_then_immediate"
    )
    assert INFORMATION_SET_SEARCH_SIMULATION_PUBLIC_POLICY == (
        "safe_aggregate_diagnostics_without_private_worlds_or_policy_table"
    )
    assert MULTI_STEP_INFORMATION_SET_SEARCH_DECISION_STREAM == (
        "multi_step_information_set_search_decision_v1"
    )
    assert SEARCH_AWARE_MULTI_STEP_POLICIES == [
        "bounded_search",
        "auto",
        "information_set_search",
    ]
    assert VALID_MULTI_STEP_POLICIES[-3:] == SEARCH_AWARE_MULTI_STEP_POLICIES
    assert VALID_CARD_SELECTION_POLICIES == DEFAULT_POLICY_COMPARISON_POLICIES
    assert SEARCH_RECOMMENDATION_METHODS == ("bounded_search", "auto")


def test_information_set_multi_step_child_configuration_changes_only_seed() -> None:
    *_prefix, configuration, _effective = _inputs()
    settings = configuration.information_set_search_settings
    assert settings is not None

    first = derive_information_set_search_multi_step_configuration_v1(
        configuration,
        step_index=0,
    )
    repeated = derive_information_set_search_multi_step_configuration_v1(
        configuration,
        step_index=0,
    )
    second = derive_information_set_search_multi_step_configuration_v1(
        configuration,
        step_index=1,
    )

    assert first == repeated
    assert first != second
    assert first.information_set_search_settings == replace(
        settings,
        random_seed=derive_simulation_child_seed(
            settings.random_seed,
            MULTI_STEP_INFORMATION_SET_SEARCH_DECISION_STREAM,
            child_index=0,
        ),
    )
    assert replace(first.information_set_search_settings, random_seed=settings.random_seed) == (
        settings
    )
    assert first.search_random_seed is None
    assert first.requested_search_budget is None


def test_real_information_set_multi_step_retains_private_result_and_safe_output() -> None:
    data, state, settings, declaration, metadata, configuration, effective = _inputs()

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        random_seed=settings["random_seed"],
        card_selection_policy="information_set_search",
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=effective,
    )

    decision = result["steps"][0]["recommendation_decision"]
    assert type(decision) is InformationSetSearchMultiStepDecisionV1
    assert decision.information_set_search_result is not None
    assert decision.information_set_search_result.status == "complete"
    assert decision.information_set_search_public_result["recommended_card"] == "D7"
    assert result["steps"][0]["candidate_card"] == "D7"
    assert result["summary"] == {
        **result["summary"],
        "requested_method": "information_set_search",
        "decisions_attempted": 1,
        "decisions_executed": 1,
        "search_recommendations_used": 1,
        "immediate_fallbacks_used": 0,
        "no_recommendation_count": 0,
    }

    public_decision = build_serializable_information_set_search_multi_step_decision_v1(
        decision,
        executed_card="D7",
    )
    assert tuple(public_decision) == (
        "schema_version",
        "step_index",
        "requested_method",
        "effective_method",
        "search_attempted",
        "recommendation_card",
        "recommendation_reason",
        "fallback_used",
        "fallback_method",
        "information_set_search_result",
    )
    assert "information_set_search_multi_step_decision_version" not in public_decision
    assert "controlled_policy" not in _all_keys(public_decision)
    assert "world_selection_seed" not in _all_keys(public_decision)

    private = decision.to_dict()
    private["information_set_search_public_result"]["status"] = "tampered"
    assert decision.information_set_search_public_result["status"] == "complete"
    source_public_result = private["information_set_search_public_result"]
    source_public_result["status"] = "complete"
    copied = replace(
        decision,
        information_set_search_public_result=source_public_result,
    )
    source_public_result["status"] = "tampered"
    assert copied.information_set_search_public_result["status"] == "complete"
    with pytest.raises(TypeError):
        copied.information_set_search_public_result["status"] = "tampered"

    serialized = build_serializable_multi_step_result(result)
    assert serialized["steps"][0]["recommendation_decision"] == public_decision
    assert "child_seed" not in repr(serialized)


def test_information_set_multi_step_runs_fresh_two_decision_searches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deck = tuple(get_full_deck())
    declaration = GameDeclaration("grand", hand_game=False, matadors=1, bid_value=24)
    exact_state = build_exact_search_state(
        declaration=declaration,
        declarer_player="left",
        remaining_hands={
            player: deck[index * 10 : (index + 1) * 10]
            for index, player in enumerate(("me", "left", "right"))
        },
        current_trick=(),
        next_player="me",
        declarer_trick_points=0,
        defender_trick_points=0,
        declarer_completed_tricks=0,
        defender_completed_tricks=0,
        out_of_play_cards=deck[-2:],
    )
    completed_tricks = []
    for _ in range(24):
        transition = apply_exact_search_card(
            exact_state,
            get_exact_search_legal_cards(exact_state)[0],
        )
        exact_state = transition.next_state
        if transition.completed_trick is not None:
            trick = transition.completed_trick
            completed_tricks.append(
                {
                    "cards": [play.card for play in trick.plays],
                    "players": [play.player for play in trick.plays],
                    "winner_player": trick.winner_player,
                    "winner_role": trick.winner_side,
                }
            )
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=list(exact_state.hand_for("me")),
        current_trick=[],
        completed_tricks=completed_tricks,
        skat=[],
        declarer_points=0,
        defender_points=0,
        trick_leader=exact_state.next_player,
        next_player=exact_state.next_player,
    )
    configuration = replace(
        _inputs()[-2],
        information_set_search_settings=replace(
            _inputs()[-2].information_set_search_settings,
            max_remaining_tricks=2,
            max_depth_plies=6,
            max_state_nodes=20_000,
            max_information_sets=5_000,
        ),
    )
    effective = _inputs()[-1]
    workflow_calls = []
    workflow_results = []
    original_workflow = multi_step_module.execute_recommendation_workflow

    def observed_workflow(**kwargs):
        workflow_calls.append(kwargs)
        workflow = original_workflow(**kwargs)
        workflow_results.append(workflow)
        return workflow

    monkeypatch.setattr(
        multi_step_module,
        "execute_recommendation_workflow",
        observed_workflow,
    )
    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=2,
        random_seed=41,
        card_selection_policy="information_set_search",
        strategic_metadata=_inputs()[-3],
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=effective,
        initial_hidden_world=CoherentHiddenWorld(
            left_hand=exact_state.hand_for("left"),
            right_hand=exact_state.hand_for("right"),
            hypothetical_skat=exact_state.out_of_play_cards,
        ),
        strict_context=True,
    )

    assert len(workflow_calls) == 2
    assert len(result["steps"]) == 2
    assert [
        call["configuration"].information_set_search_settings.random_seed
        for call in workflow_calls
    ] == [
        derive_simulation_child_seed(
            configuration.information_set_search_settings.random_seed,
            MULTI_STEP_INFORMATION_SET_SEARCH_DECISION_STREAM,
            child_index=index,
        )
        for index in range(2)
    ]
    assert all("coherent_hidden_world" not in call for call in workflow_calls)
    assert all("initial_hidden_world" not in call for call in workflow_calls)
    assert workflow_results[0].information_set_search_result is not (
        workflow_results[1].information_set_search_result
    )
    assert result["steps"][0]["recommendation_decision"] is not (
        result["steps"][1]["recommendation_decision"]
    )


def test_compact_information_set_diagnostic_has_exact_safe_fields() -> None:
    _data, state, settings, declaration, metadata, configuration, effective = _inputs()
    result = simulate_multiple_steps(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        card_selection_policy="information_set_search",
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=effective,
    )
    diagnostic = build_compact_information_set_search_decision_diagnostic_v1(
        result["steps"][0]["recommendation_decision"]
    )

    assert tuple(diagnostic) == (
        "step_index",
        "requested_method",
        "effective_method",
        "search_method",
        "search_status",
        "search_stop_reason",
        "world_coverage",
        "policy_claim",
        "policy_consistency",
        "selected_world_count",
        "completed_world_count",
        "information_sets_evaluated",
        "controlled_policy_decision_count",
        "fixed_policy_decision_count",
        "recommendation_card",
        "fallback_used",
    )
    assert diagnostic["recommendation_card"] == "D7"
    assert diagnostic["fallback_used"] is False


def test_information_set_search_runs_after_public_canonical_completion_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _data, _input_state, _settings, declaration, metadata, configuration, effective = (
        _inputs()
    )
    configuration = replace(
        configuration,
        information_set_search_settings=replace(
            configuration.information_set_search_settings,
            max_depth_plies=3,
            max_state_nodes=1000,
            max_information_sets=1000,
        ),
    )
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["D7"],
        current_trick=["CA"],
        trick_leader="me",
        next_player="left",
    )
    world = CoherentHiddenWorld(
        left_hand=("C7", "H7"),
        right_hand=("C8", "S7"),
        hypothetical_skat=tuple(
            card
            for card in get_full_deck()
            if card not in {"D7", "CA", "C7", "H7", "C8", "S7"}
        ),
    )
    workflow_calls = []
    original_workflow = multi_step_module.execute_recommendation_workflow

    def observed_workflow(**kwargs):
        workflow_calls.append(kwargs)
        return original_workflow(**kwargs)

    monkeypatch.setattr(
        multi_step_module,
        "execute_recommendation_workflow",
        observed_workflow,
    )
    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=29,
        card_selection_policy="information_set_search",
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=effective,
        initial_hidden_world=world,
    )

    assert len(workflow_calls) == 1
    assert workflow_calls[0]["state"].hand == ["D7"]
    assert workflow_calls[0]["state"].current_trick == []
    assert workflow_calls[0]["state"].completed_tricks[-1]["cards"] == [
        "CA",
        "C7",
        "C8",
    ]
    assert workflow_calls[0]["left_hand_size"] == 1
    assert workflow_calls[0]["right_hand_size"] == 1
    assert "coherent_hidden_world" not in workflow_calls[0]
    assert "initial_hidden_world" not in workflow_calls[0]
    assert result["steps"] == []
    assert result["stop_reason"] == "local_policy_no_recommendation"
    stopped = result["stopped_recommendation_decision"]
    assert stopped.step_index == 0
    assert stopped.recommendation_card is None
    assert stopped.fallback_used is False


def test_information_set_no_recommendation_stops_without_fallback() -> None:
    _data, state, settings, declaration, metadata, configuration, effective = _inputs()
    nondeterministic = replace(effective, left_response_policy="random_legal")

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        card_selection_policy="information_set_search",
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=nondeterministic,
    )

    assert result["steps"] == []
    assert result["stop_reason"] == "local_policy_no_recommendation"
    stopped = result["stopped_recommendation_decision"]
    assert type(stopped) is InformationSetSearchMultiStepDecisionV1
    assert stopped.information_set_search_result is None
    assert stopped.information_set_search_public_result["status"] == "unavailable"
    assert stopped.recommendation_card is None
    assert stopped.fallback_used is False
    assert stopped.fallback_method is None
    assert result["summary"]["decisions_attempted"] == 1
    assert result["summary"]["decisions_executed"] == 0
    assert result["summary"]["no_recommendation_count"] == 1
    malformed = stopped.to_dict()["information_set_search_public_result"]
    malformed["fixed_policy_settings"][0]["controlled_policy"] = []
    with pytest.raises(ValueError, match="canonical public unavailability"):
        replace(stopped, information_set_search_public_result=malformed)


def test_information_set_multi_step_requires_resolved_effective_policies() -> None:
    _data, state, settings, declaration, metadata, configuration, _effective = _inputs()

    with pytest.raises(ValueError, match="effective opponent"):
        simulate_multiple_steps(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            step_count=1,
            card_selection_policy="information_set_search",
            strategic_metadata=metadata,
            game_declaration=declaration,
            recommendation_configuration=configuration,
        )


def test_information_set_multi_step_reuses_effective_policies_for_execution() -> None:
    _data, state, settings, declaration, metadata, configuration, effective = _inputs()
    resolved = replace(
        effective,
        global_lead_policy="highest_point",
        global_response_policy="highest_point",
        left_lead_policy="highest_point",
        left_response_policy="highest_point",
        right_lead_policy="highest_point",
        right_response_policy="highest_point",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        card_selection_policy="information_set_search",
        strategic_metadata=metadata,
        opponent_lead_policy="lowest_point",
        opponent_response_policy="lowest_point",
        left_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        right_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=resolved,
    )

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    fixed = result["steps"][0]["recommendation_decision"].information_set_search_public_result[
        "fixed_policy_settings"
    ]
    assert [item["lead_policy"] for item in fixed] == [
        "highest_point",
        "highest_point",
    ]
    assert [item["response_policy"] for item in fixed] == [
        "highest_point",
        "highest_point",
    ]


def test_information_set_policy_comparison_appends_one_eligible_safe_row_last() -> None:
    _data, state, settings, declaration, metadata, configuration, effective = _inputs()

    comparison = compare_multi_step_policies(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        policies=["information_set_search", *DEFAULT_POLICY_COMPARISON_POLICIES],
        random_seed=settings["random_seed"],
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=effective,
    )

    assert comparison["policies"] == [
        *DEFAULT_POLICY_COMPARISON_POLICIES,
        "information_set_search",
    ]
    row = next(
        item
        for item in comparison["policy_results"]
        if item["policy"] == "information_set_search"
    )
    assert row["eligible_for_recommendation"] is True
    assert row["ineligible_reason"] is None
    assert row["recommendation_summary"]["search_recommendations_used"] == 1
    assert tuple(row["search_decision_diagnostics"][0]) == (
        "step_index",
        "requested_method",
        "effective_method",
        "search_method",
        "search_status",
        "search_stop_reason",
        "world_coverage",
        "policy_claim",
        "policy_consistency",
        "selected_world_count",
        "completed_world_count",
        "information_sets_evaluated",
        "controlled_policy_decision_count",
        "fixed_policy_decision_count",
        "recommendation_card",
        "fallback_used",
    )
    assert "controlled_policy" not in _all_keys(row)


def test_information_set_comparison_uses_one_effective_policy_neutral_prelude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _data, _input_state, _settings, declaration, metadata, configuration, effective = (
        _inputs()
    )
    highest = replace(
        effective,
        global_lead_policy="highest_point",
        global_response_policy="highest_point",
        left_lead_policy="highest_point",
        left_response_policy="highest_point",
        right_lead_policy="highest_point",
        right_response_policy="highest_point",
    )
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["D7"],
        current_trick=["S7"],
        trick_leader="me",
        next_player="left",
    )
    captured_calls = []

    def fake_simulate_multiple_steps(**kwargs):
        captured_calls.append(kwargs)
        summary = {
            "requested_step_count": kwargs["step_count"],
            "steps_simulated": 0,
            "stop_reason": "Player has no cards left.",
            "strict_context": kwargs["strict_context"],
            "score_summary": {
                "declarer_points_gained": 0,
                "defender_points_gained": 0,
                "final_point_swing": 0,
                "local_point_swing": 0,
            },
            "context_summary": {},
            "requested_method": "information_set_search",
            "decisions_attempted": 0,
            "decisions_executed": 0,
            "search_recommendations_used": 0,
            "immediate_fallbacks_used": 0,
            "no_recommendation_count": 0,
        }
        return {
            "final_state": kwargs["state"],
            "summary": summary,
            "stop_reason": "Player has no cards left.",
            "steps": [],
        }

    monkeypatch.setattr(
        "skat_ai.policy_comparison.simulate_multiple_steps",
        fake_simulate_multiple_steps,
    )

    comparison = compare_multi_step_policies(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        policies=["first_legal", "information_set_search"],
        random_seed=31,
        strategic_metadata=metadata,
        opponent_lead_policy="lowest_point",
        opponent_response_policy="lowest_point",
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=highest,
    )

    assert comparison["opponent_lead_policy"] == "highest_point"
    assert comparison["opponent_response_policy"] == "highest_point"
    assert {item["card_selection_policy"] for item in captured_calls} == {
        "first_legal",
        "information_set_search",
    }
    assert all(
        item["opponent_lead_policy"] == "highest_point"
        and item["opponent_response_policy"] == "highest_point"
        for item in captured_calls
    )
    assert all(
        item["opponent_response_policy_by_player"]
        == {"left": "highest_point", "right": "highest_point"}
        for item in captured_calls
    )
    assert all(
        item["left_opponent_policy_settings"]
        == {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "highest_point",
        }
        and item["right_opponent_policy_settings"]
        == {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "highest_point",
        }
        for item in captured_calls
    )
    assert captured_calls[0]["initial_hidden_world"] == captured_calls[1][
        "initial_hidden_world"
    ]
    assert captured_calls[0]["initial_hidden_world"] is not captured_calls[1][
        "initial_hidden_world"
    ]


def test_information_set_policy_comparison_retains_stopped_ineligible_row_last() -> None:
    _data, state, settings, declaration, metadata, configuration, effective = _inputs()
    nondeterministic = replace(effective, left_response_policy="random_legal")

    comparison = compare_multi_step_policies(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        random_seed=settings["random_seed"],
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=nondeterministic,
    )

    rows = [
        row
        for row in comparison["policy_results"]
        if row["policy"] == "information_set_search"
    ]
    assert len(rows) == 1
    row = rows[0]
    assert comparison["policies"][-1] == "information_set_search"
    assert comparison["policy_results"][-1] is row
    assert row["stop_reason"] == "local_policy_no_recommendation"
    assert row["eligible_for_recommendation"] is False
    assert row["ineligible_reason"] == "local_policy_no_recommendation"
    assert row["search_decision_diagnostics"][0]["search_status"] == "unavailable"
    assert comparison["recommended_policy"]["policy"] != "information_set_search"


def test_information_set_simulation_presentations_are_concise_and_safe(capsys) -> None:
    _data, state, settings, declaration, metadata, configuration, effective = _inputs()
    multi_step = simulate_multiple_steps(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        card_selection_policy="information_set_search",
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=effective,
    )
    comparison = compare_multi_step_policies(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        effective_opponent_policy_settings=effective,
    )

    print_multi_step_result(multi_step)
    print_policy_comparison_result(comparison)
    output = capsys.readouterr().out
    assert "Card selection policy: information_set_search" in output
    assert "Recommendation decisions attempted: 1" in output
    assert "Recommendation decisions executed: 1" in output
    assert "Search recommendations used: 1" in output
    assert "information_set_search" in output
    assert "Eligible for recommendation: True" in output
    assert "controlled_policy" not in output
    assert "world_selection_seed" not in output
