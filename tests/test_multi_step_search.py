import json
from copy import deepcopy
from pathlib import Path

import pytest

from main import resolve_multi_step_card_selection_policy
from skat_ai.bounded_search_result import (
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    mark_bounded_search_fallback_used,
)
from skat_ai.card_selection import (
    DEFAULT_POLICY_COMPARISON_POLICIES,
    LEGACY_CARD_SELECTION_POLICIES,
    SEARCH_AWARE_MULTI_STEP_POLICIES,
    VALID_MULTI_STEP_POLICIES,
    choose_card_by_policy,
)
from skat_ai.coherent_hidden_world import (
    CoherentHiddenWorld,
    derive_simulation_child_seed,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.input_loader import (
    build_local_game_state_from_input,
    get_analysis_metadata_from_input,
    get_game_declaration_from_input,
    get_recommendation_method_configuration_from_input,
    get_simulation_settings_from_input,
    load_position_from_json,
)
from skat_ai.multi_step_recommendation import (
    MULTI_STEP_BOUNDED_SEARCH_DECISION_STREAM,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.multi_step_summary import build_multi_step_summary
from skat_ai.policy_comparison import (
    build_policy_recommendation,
    compare_multi_step_policies,
    sort_policy_results_by_local_point_swing,
)
from skat_ai.recommendation_workflow import (
    AUTO_METHOD,
    BOUNDED_SEARCH_METHOD,
    COMPATIBLE_WORLD_MINIMAX_METHOD,
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    NONE_EFFECTIVE_METHOD,
    RecommendationMethodConfiguration,
    RecommendationWorkflowResult,
)
from skat_ai.result_serialization import build_serializable_multi_step_result
from skat_ai.strategic_metadata import StrategicMetadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _budget(*, timeout: int | None = None) -> RequestedSearchBudget:
    return RequestedSearchBudget(
        max_remaining_tricks=5,
        max_depth_plies=15,
        max_nodes=1000,
        max_selected_worlds=2,
        max_sampled_worlds=2,
        minimum_comparable_worlds=1,
        wall_clock_timeout_ms=timeout,
    )


def _configuration(
    method: str = BOUNDED_SEARCH_METHOD,
    *,
    budget: RequestedSearchBudget | None = None,
) -> RecommendationMethodConfiguration:
    return RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method=method,
        search_random_seed=113,
        requested_search_budget=budget or _budget(),
    )


def _world(
    state: GameState,
    left_hand: tuple[str, ...],
    right_hand: tuple[str, ...],
) -> CoherentHiddenWorld:
    known = set(
        state.hand
        + state.current_trick
        + state.played_cards
        + state.skat
        + [
            card
            for trick in state.completed_tricks
            for card in trick.get("cards", [])
        ]
    )
    assigned = {*left_hand, *right_hand}
    deck = [
        f"{suit}{rank}"
        for suit in "CSHD"
        for rank in ("A", "10", "K", "Q", "J", "9", "8", "7")
    ]
    skat = tuple(card for card in deck if card not in known | assigned)
    return CoherentHiddenWorld(left_hand, right_hand, skat)


def _search_result(
    state: GameState,
    budget: RequestedSearchBudget,
    card: str | None,
    *,
    status: str = "complete",
    stop_reason: str = "completed",
) -> BoundedSearchResult:
    completed = 1 if card is not None else 0
    selected = 2 if card is not None and status != "complete" else 1
    candidate = AggregateSearchCandidateResult(
        card=state.hand[0],
        rank=1,
        is_recommended=card is not None,
        completed_world_count=completed,
        local_contract_success_count=completed,
        local_contract_success_rate=1.0 if completed else None,
        mean_local_side_game_score=24.0 if completed else None,
        mean_local_side_card_point_margin=10.0 if completed else None,
    )
    claim = {
        "completed": "exact_per_selected_world",
        "node_budget_exhausted": "node_limited_partial",
        "depth_budget_exhausted": "depth_limited_per_selected_world",
        "wall_clock_timeout": "none",
    }[stop_reason]
    return BoundedSearchResult(
        schema_version=1,
        analysis_method="bounded_search",
        search_method=COMPATIBLE_WORLD_MINIMAX_METHOD,
        game_type=state.game_type,
        status=status,
        stop_reason=stop_reason,
        world_coverage="all_compatible_worlds",
        solution_claim=claim,
        terminal_utility_version=1,
        requested_budget=budget,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=1,
            nodes_expanded=2,
            selected_world_count=selected,
            completed_world_count=completed,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            wall_clock_elapsed_ms=0,
        ),
        compatible_world_count=selected,
        candidate_results=(candidate,),
        recommended_card=card,
        fallback_used=False,
        fallback_method=None,
    )


def _workflow(
    configuration: RecommendationMethodConfiguration,
    state: GameState,
    card: str | None,
    *,
    status: str = "complete",
    stop_reason: str = "completed",
    fallback: bool = False,
) -> RecommendationWorkflowResult:
    budget = configuration.requested_search_budget
    assert budget is not None
    search = _search_result(
        state,
        budget,
        None if fallback else card,
        status=status,
        stop_reason=stop_reason,
    )
    if fallback:
        search = mark_bounded_search_fallback_used(search)
    effective = (
        IMMEDIATE_EXPECTED_VALUE_METHOD
        if fallback
        else COMPATIBLE_WORLD_MINIMAX_METHOD
        if card is not None
        else NONE_EFFECTIVE_METHOD
    )
    return RecommendationWorkflowResult(
        requested_method=configuration.requested_method,
        effective_method=effective,
        recommendation_card=card,
        recommendation_reason="Local test recommendation.",
        legal_cards=tuple(state.hand),
        analysis_report=(),
        analysis_report_method=(
            IMMEDIATE_EXPECTED_VALUE_METHOD
            if fallback or (configuration.requested_method == AUTO_METHOD and card is None)
            else "none"
        ),
        strategic_summary="Strategic summary: local test.",
        bounded_search_result=search,
        fallback_used=fallback,
        fallback_method=IMMEDIATE_EXPECTED_VALUE_METHOD if fallback else None,
    )


def _live_metadata() -> StrategicMetadata:
    return StrategicMetadata(
        analysis_mode="live_decision",
        skat_visibility="unknown",
        game_end_reason="not_ended",
    )


def test_policy_registries_keep_legacy_execution_separate() -> None:
    assert LEGACY_CARD_SELECTION_POLICIES == [
        "first_legal",
        "lowest_point",
        "highest_point",
        "highest_expected_value",
    ]
    assert SEARCH_AWARE_MULTI_STEP_POLICIES == ["bounded_search", "auto"]
    assert VALID_MULTI_STEP_POLICIES == [
        *LEGACY_CARD_SELECTION_POLICIES,
        *SEARCH_AWARE_MULTI_STEP_POLICIES,
    ]
    assert DEFAULT_POLICY_COMPARISON_POLICIES == LEGACY_CARD_SELECTION_POLICIES
    with pytest.raises(ValueError, match="Invalid card selection policy"):
        choose_card_by_policy(GameState("grand", "declarer", ["D7"], []), "bounded_search")


@pytest.mark.parametrize("method", SEARCH_AWARE_MULTI_STEP_POLICIES)
def test_multi_step_policy_resolution_requires_matching_search_configuration(
    method: str,
) -> None:
    configuration = _configuration(method)
    assert resolve_multi_step_card_selection_policy(None, configuration) == method
    assert resolve_multi_step_card_selection_policy(method, configuration) == method
    with pytest.raises(ValueError, match="conflicts"):
        resolve_multi_step_card_selection_policy("first_legal", configuration)

    immediate = RecommendationMethodConfiguration(False, IMMEDIATE_EXPECTED_VALUE_METHOD)
    with pytest.raises(ValueError, match="requires matching"):
        resolve_multi_step_card_selection_policy(method, immediate)
    assert resolve_multi_step_card_selection_policy(None, immediate) == "first_legal"


def test_search_policy_requires_all_direct_call_contract_inputs() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["D7"],
        current_trick=["D8", "D9"],
        trick_leader="left",
        next_player="me",
    )
    with pytest.raises(ValueError, match="normalized game declaration"):
        simulate_multiple_steps(state, 0, 0, 1, card_selection_policy="bounded_search")
    with pytest.raises(ValueError, match="method configuration"):
        simulate_multiple_steps(
            state,
            0,
            0,
            1,
            card_selection_policy="bounded_search",
            game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        )
    with pytest.raises(ValueError, match="must match"):
        simulate_multiple_steps(
            state,
            0,
            0,
            1,
            card_selection_policy="bounded_search",
            game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
            recommendation_configuration=_configuration(AUTO_METHOD),
            strategic_metadata=_live_metadata(),
        )


def test_search_repeats_with_public_counts_fresh_budget_and_separate_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA", "SA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )
    world = _world(state, ("C7", "S7"), ("C8", "S8"))
    configuration = _configuration()
    calls = []
    provenance_calls = []

    def fake_workflow(**kwargs):
        calls.append(kwargs)
        return _workflow(kwargs["configuration"], kwargs["state"], kwargs["state"].hand[0])

    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.execute_recommendation_workflow",
        fake_workflow,
    )
    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=2,
        random_seed=41,
        card_selection_policy="bounded_search",
        strategic_metadata=_live_metadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        initial_hidden_world=world,
        strict_context=True,
        decision_provenance_hook=lambda **kwargs: provenance_calls.append(kwargs),
    )

    assert len(calls) == 2
    assert len(provenance_calls) == 2
    assert [call["decision_index"] for call in provenance_calls] == [0, 1]
    assert all(call["selection_method"] == "bounded_search" for call in provenance_calls)
    assert all("random_seed" not in repr(call) for call in provenance_calls)
    assert [(call["left_hand_size"], call["right_hand_size"]) for call in calls] == [
        (2, 2),
        (1, 1),
    ]
    assert calls[1]["state"].completed_tricks == result["steps"][0]["next_state"].completed_tricks
    assert all(
        call["configuration"].requested_search_budget == configuration.requested_search_budget
        for call in calls
    )
    assert [call["configuration"].search_random_seed for call in calls] == [
        derive_simulation_child_seed(
            113,
            MULTI_STEP_BOUNDED_SEARCH_DECISION_STREAM,
            child_index=index,
        )
        for index in range(2)
    ]
    assert [call["immediate_random_seed"] for call in calls] == [
        derive_simulation_child_seed(41, "expected_value_samples", child_index=index)
        for index in range(2)
    ]
    assert all("coherent_hidden_world" not in call for call in calls)
    assert all("initial_hidden_world" not in call for call in calls)
    assert {
        key: result["summary"][key]
        for key in (
            "requested_method",
            "decisions_attempted",
            "decisions_executed",
            "search_recommendations_used",
            "immediate_fallbacks_used",
            "no_recommendation_count",
        )
    } == {
        "requested_method": "bounded_search",
        "decisions_attempted": 2,
        "decisions_executed": 2,
        "search_recommendations_used": 2,
        "immediate_fallbacks_used": 0,
        "no_recommendation_count": 0,
    }


@pytest.mark.parametrize(
    ("status", "stop_reason", "timeout"),
    [
        ("partial", "node_budget_exhausted", None),
        ("timeout", "wall_clock_timeout", 1),
    ],
)
def test_strict_search_executes_qualified_partial_and_timeout_recommendations(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    stop_reason: str,
    timeout: int | None,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C7", "C8"],
        trick_leader="left",
        next_player="me",
    )
    configuration = _configuration(budget=_budget(timeout=timeout))

    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.execute_recommendation_workflow",
        lambda **kwargs: _workflow(
            kwargs["configuration"],
            kwargs["state"],
            "CA",
            status=status,
            stop_reason=stop_reason,
        ),
    )
    result = simulate_multiple_steps(
        state,
        0,
        0,
        1,
        card_selection_policy="bounded_search",
        strategic_metadata=_live_metadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        initial_hidden_world=_world(state, (), ()),
    )

    assert result["steps_simulated"] == 1
    decision = result["steps"][0]["recommendation_decision"]
    assert decision.bounded_search_result.status == status
    assert decision.recommendation_card == "CA"
    assert decision.fallback_used is False


def test_auto_executes_immediate_fallback_and_counts_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C7", "C8"],
        trick_leader="left",
        next_player="me",
    )
    configuration = _configuration(AUTO_METHOD)
    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.execute_recommendation_workflow",
        lambda **kwargs: _workflow(
            kwargs["configuration"],
            kwargs["state"],
            "CA",
            status="partial",
            stop_reason="node_budget_exhausted",
            fallback=True,
        ),
    )
    result = simulate_multiple_steps(
        state,
        0,
        0,
        1,
        card_selection_policy="auto",
        strategic_metadata=_live_metadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        initial_hidden_world=_world(state, (), ()),
    )

    assert result["steps"][0]["candidate_card"] == "CA"
    assert result["summary"]["immediate_fallbacks_used"] == 1
    assert result["summary"]["search_recommendations_used"] == 0


def test_auto_without_search_or_immediate_card_stops_without_marking_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C7", "C8"],
        trick_leader="left",
        next_player="me",
    )
    configuration = _configuration(AUTO_METHOD)
    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.execute_recommendation_workflow",
        lambda **kwargs: _workflow(
            kwargs["configuration"],
            kwargs["state"],
            None,
            status="partial",
            stop_reason="node_budget_exhausted",
        ),
    )
    result = simulate_multiple_steps(
        state,
        0,
        0,
        1,
        card_selection_policy="auto",
        strategic_metadata=_live_metadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        initial_hidden_world=_world(state, (), ()),
    )

    stopped = result["stopped_recommendation_decision"]
    assert result["stop_reason"] == "local_policy_no_recommendation"
    assert stopped.fallback_used is False
    assert stopped.fallback_method is None
    assert result["summary"]["immediate_fallbacks_used"] == 0


def test_no_recommendation_retains_opponent_preparation_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=[],
        trick_leader="right",
        next_player="right",
    )
    world = _world(state, ("C8",), ("C7",))
    configuration = _configuration()
    calls = []

    def no_recommendation(**kwargs):
        calls.append(kwargs)
        return _workflow(
            kwargs["configuration"],
            kwargs["state"],
            None,
            status="partial",
            stop_reason="node_budget_exhausted",
        )

    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.execute_recommendation_workflow",
        no_recommendation,
    )
    result = simulate_multiple_steps(
        state,
        1,
        1,
        1,
        random_seed=7,
        card_selection_policy="bounded_search",
        strategic_metadata=_live_metadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        initial_hidden_world=world,
        strict_context=True,
    )

    assert result["stop_reason"] == "local_policy_no_recommendation"
    assert result["steps_simulated"] == 0
    assert result["steps"] == []
    assert len(result["final_state"].current_trick) == 1
    assert result["context_summary"]["simulated_opponent_card_count"] == 1
    assert result["context_summary"]["event_count"] == 1
    assert result["context_summary"]["hidden_world"]["ownership_transition_count"] == 1
    assert result["stopped_recommendation_decision"].recommendation_card is None
    assert result["summary"]["no_recommendation_count"] == 1
    assert calls[0]["left_hand_size"] == 1
    assert calls[0]["right_hand_size"] == 0

    serialized = build_serializable_multi_step_result(result)
    assert serialized["stopped_recommendation_decision"]["recommendation_card"] is None
    serialized_text = json.dumps(serialized)
    assert '"left_hand":' not in serialized_text
    assert '"right_hand":' not in serialized_text
    assert "child_seed" not in serialized_text


def test_unexpected_search_errors_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C7", "C8"],
        trick_leader="left",
        next_player="me",
    )
    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.execute_recommendation_workflow",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("search failed")),
    )
    with pytest.raises(RuntimeError, match="search failed"):
        simulate_multiple_steps(
            state,
            0,
            0,
            1,
            card_selection_policy="auto",
            strategic_metadata=_live_metadata(),
            game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
            recommendation_configuration=_configuration(AUTO_METHOD),
            initial_hidden_world=_world(state, (), ()),
        )


def test_shared_public_prefix_search_decision_is_invariant_across_private_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )
    configuration = _configuration()
    seen = []

    def fake_workflow(**kwargs):
        seen.append(kwargs)
        return _workflow(kwargs["configuration"], kwargs["state"], "CA")

    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.execute_recommendation_workflow",
        fake_workflow,
    )
    first = simulate_multiple_steps(
        state,
        1,
        1,
        1,
        random_seed=3,
        card_selection_policy="bounded_search",
        strategic_metadata=_live_metadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        initial_hidden_world=_world(state, ("C7",), ("C8",)),
    )
    second = simulate_multiple_steps(
        state,
        1,
        1,
        1,
        random_seed=3,
        card_selection_policy="bounded_search",
        strategic_metadata=_live_metadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        initial_hidden_world=_world(state, ("C8",), ("C7",)),
    )

    first_decision = first["steps"][0]["recommendation_decision"]
    second_decision = second["steps"][0]["recommendation_decision"]
    assert first_decision == second_decision
    assert first_decision.bounded_search_result == second_decision.bounded_search_result
    assert seen[0]["state"] == seen[1]["state"]
    assert seen[0]["left_hand_size"] == seen[1]["left_hand_size"] == 1
    assert seen[0]["right_hand_size"] == seen[1]["right_hand_size"] == 1


def test_real_search_multi_step_and_comparison_append_contract() -> None:
    path = PROJECT_ROOT / "examples" / "grand_bounded_search_exhaustive.json"
    data = load_position_from_json(str(path))
    settings = get_simulation_settings_from_input(data)
    configuration = get_recommendation_method_configuration_from_input(data)
    declaration = get_game_declaration_from_input(data)
    metadata = get_analysis_metadata_from_input(data).strategic_metadata
    state = build_local_game_state_from_input(data)
    observed_comparison_decisions = []

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        random_seed=settings["random_seed"],
        card_selection_policy="bounded_search",
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
    )
    comparison = compare_multi_step_policies(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        random_seed=settings["random_seed"],
        strategic_metadata=metadata,
        game_declaration=declaration,
        recommendation_configuration=configuration,
        recommendation_decision_observer=(
            lambda policy, decision: observed_comparison_decisions.append(
                (policy, decision)
            )
        ),
    )

    assert result["steps"][0]["recommendation_decision"].recommendation_card == "D7"
    assert comparison["policies"] == [
        *DEFAULT_POLICY_COMPARISON_POLICIES,
        "bounded_search",
    ]
    search_row = next(
        item for item in comparison["policy_results"] if item["policy"] == "bounded_search"
    )
    assert search_row["eligible_for_recommendation"] is True
    assert search_row["search_decision_diagnostics"][0]["recommendation_card"] == "D7"
    assert search_row["recommendation_summary"]["search_recommendations_used"] == 1
    assert len(observed_comparison_decisions) == 1
    assert observed_comparison_decisions[0][0] == "bounded_search"
    assert observed_comparison_decisions[0][1].bounded_search_result.search_method == (
        "compatible_world_minimax_v1"
    )

    tampered = deepcopy(result)
    tampered["steps"][0]["candidate_card"] = "C7"
    with pytest.raises(ValueError, match="must match the executed card"):
        build_serializable_multi_step_result(tampered)
    tampered_summary = deepcopy(result)
    tampered_summary["stopped_recommendation_decision"] = tampered_summary[
        "steps"
    ][0]["recommendation_decision"]
    with pytest.raises(ValueError, match="Stopped recommendation decision"):
        build_multi_step_summary(tampered_summary)


def test_real_strict_no_recommendation_comparison_keeps_search_row_ineligible() -> None:
    path = PROJECT_ROOT / "examples" / "grand_auto_search_fallback.json"
    data = load_position_from_json(str(path))
    settings = get_simulation_settings_from_input(data)
    auto_configuration = get_recommendation_method_configuration_from_input(data)
    configuration = RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method=BOUNDED_SEARCH_METHOD,
        search_random_seed=auto_configuration.search_random_seed,
        requested_search_budget=auto_configuration.requested_search_budget,
    )
    comparison = compare_multi_step_policies(
        state=build_local_game_state_from_input(data),
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        random_seed=settings["random_seed"],
        strategic_metadata=get_analysis_metadata_from_input(data).strategic_metadata,
        game_declaration=get_game_declaration_from_input(data),
        recommendation_configuration=configuration,
    )
    search_row = next(
        item for item in comparison["policy_results"] if item["policy"] == "bounded_search"
    )

    assert search_row["stop_reason"] == "local_policy_no_recommendation"
    assert search_row["eligible_for_recommendation"] is False
    assert search_row["ineligible_reason"] == "local_policy_no_recommendation"
    assert search_row["recommendation_summary"]["no_recommendation_count"] == 1
    assert comparison["policy_results"][-1] == search_row
    assert comparison["recommended_policy"]["policy"] != "bounded_search"


def test_ineligible_search_policy_sorts_last_and_cannot_be_recommended() -> None:
    eligible = {
        "policy": "first_legal",
        "eligible_for_recommendation": True,
        "final_point_swing": -10,
        "local_point_swing": -10,
        "declarer_points_gained": 0,
        "defender_points_gained": 10,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
    }
    ineligible = {
        "policy": "bounded_search",
        "eligible_for_recommendation": False,
        "ineligible_reason": "local_policy_no_recommendation",
        "final_point_swing": 100,
        "local_point_swing": 100,
        "declarer_points_gained": 100,
        "defender_points_gained": 0,
        "steps_simulated": 0,
        "stop_reason": "local_policy_no_recommendation",
    }
    comparison = {"policy_results": [ineligible, eligible]}

    assert sort_policy_results_by_local_point_swing([ineligible, eligible]) == [
        eligible,
        ineligible,
    ]
    assert build_policy_recommendation(comparison)["policy"] == "first_legal"
    assert build_policy_recommendation({"policy_results": [ineligible]}) is None


def test_policy_comparison_rejects_explicit_empty_or_duplicate_policy_lists() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C7", "C8"],
        trick_leader="left",
        next_player="me",
    )
    with pytest.raises(ValueError, match="at least one policy"):
        compare_multi_step_policies(state, 0, 0, 1, policies=[])
    with pytest.raises(ValueError, match="must be unique"):
        compare_multi_step_policies(
            state,
            0,
            0,
            1,
            policies=["first_legal", "first_legal"],
        )
