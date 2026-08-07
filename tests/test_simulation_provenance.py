from skat_ai.bounded_search_result import RequestedSearchBudget
from skat_ai.coherent_hidden_world import CoherentHiddenWorld
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.live_analysis_provenance import (
    build_live_decision_provenance_attachment,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.recommendation_workflow import RecommendationMethodConfiguration
from skat_ai.strategic_metadata import StrategicMetadata


def _world(
    state: GameState,
    left_hand: tuple[str, ...],
    right_hand: tuple[str, ...],
) -> CoherentHiddenWorld:
    known = set(state.hand + state.current_trick)
    assigned = {*left_hand, *right_hand}
    deck = [
        f"{suit}{rank}"
        for suit in "CSHD"
        for rank in ("A", "10", "K", "Q", "J", "9", "8", "7")
    ]
    skat = tuple(card for card in deck if card not in known | assigned)
    return CoherentHiddenWorld(left_hand, right_hand, skat)


def _state() -> GameState:
    return GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )


def _run(world: CoherentHiddenWorld, captured: list):
    def hook(**kwargs):
        captured.append(
            build_live_decision_provenance_attachment(
                name=f"multi_step_decision/{kwargs['decision_index']}",
                simulation_scope=True,
                **kwargs,
            )
        )

    return simulate_multiple_steps(
        state=_state(),
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        random_seed=3,
        card_selection_policy="first_legal",
        expected_value_sample_count=1,
        strategic_metadata=StrategicMetadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        initial_hidden_world=world,
        decision_provenance_hook=hook,
    )


def test_hook_receives_no_private_world_or_random_stream_and_runs_once() -> None:
    state = _state()
    captured_kwargs = []

    def hook(**kwargs):
        captured_kwargs.append(kwargs)

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        random_seed=3,
        card_selection_policy="first_legal",
        expected_value_sample_count=1,
        strategic_metadata=StrategicMetadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        initial_hidden_world=_world(state, ("C7",), ("C8",)),
        decision_provenance_hook=hook,
    )

    assert result["steps_simulated"] == 1
    assert len(captured_kwargs) == 1
    assert set(captured_kwargs[0]) == {
        "state",
        "left_hand_size",
        "right_hand_size",
        "public_hand_constraints",
        "strategic_metadata",
        "game_declaration",
        "decision_index",
        "selection_method",
        "selection_settings",
    }
    assert "random_seed" not in repr(captured_kwargs[0]["selection_settings"])


def test_equal_visible_states_with_changed_private_ownership_have_equal_provenance() -> None:
    state = _state()
    first_captured = []
    second_captured = []
    first = _run(_world(state, ("C7",), ("C8",)), first_captured)
    second = _run(_world(state, ("C8",), ("C7",)), second_captured)

    assert first["steps_simulated"] == second["steps_simulated"] == 1
    assert len(first_captured) == len(second_captured) == 1
    assert first_captured[0].document == second_captured[0].document
    assert first_captured[0].ledger == second_captured[0].ledger
    assert first_captured[0].coverage_summary == second_captured[0].coverage_summary
    assert first_captured[0].document["game_state"]["hand"] == ("CA",)


def test_unsupported_turn_phase_does_not_invoke_decision_hook() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["D7"],
        current_trick=["CA"],
        trick_leader="me",
        next_player="left",
    )
    calls = []

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        random_seed=3,
        strategic_metadata=StrategicMetadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        initial_hidden_world=_world(state, ("C7",), ("C8",)),
        decision_provenance_hook=lambda **kwargs: calls.append(kwargs),
    )

    assert result["steps_simulated"] == 0
    assert result["stop_reason"] == "unsupported_turn_phase"
    assert calls == []


def test_search_inclusive_policy_comparison_threads_same_hook_once_per_policy(
    monkeypatch,
) -> None:
    calls = []

    def fake_simulate_multiple_steps(**kwargs):
        calls.append(kwargs)
        summary = {
            "requested_step_count": kwargs["step_count"],
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "strict_context": kwargs["strict_context"],
            "score_summary": {
                "declarer_points_gained": 0,
                "defender_points_gained": 0,
                "final_point_swing": 0,
            },
            "context_summary": {},
        }
        if kwargs["card_selection_policy"] == "bounded_search":
            summary.update(
                requested_method="bounded_search",
                decisions_attempted=0,
                decisions_executed=0,
                search_recommendations_used=0,
                immediate_fallbacks_used=0,
                no_recommendation_count=0,
            )
        return {
            "summary": summary,
            "steps": [],
            "stop_reason": "Requested step count reached.",
        }

    monkeypatch.setattr(
        "skat_ai.policy_comparison.simulate_multiple_steps",
        fake_simulate_multiple_steps,
    )
    def hook(**_kwargs):
        return None
    configuration = RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method="bounded_search",
        search_random_seed=113,
        requested_search_budget=RequestedSearchBudget(
            max_remaining_tricks=5,
            max_depth_plies=15,
            max_nodes=1000,
            max_selected_worlds=2,
            max_sampled_worlds=2,
            minimum_comparable_worlds=1,
        ),
    )
    result = compare_multi_step_policies(
        state=_state(),
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        policies=["first_legal"],
        random_seed=3,
        strategic_metadata=StrategicMetadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        recommendation_configuration=configuration,
        decision_provenance_hook=hook,
    )

    assert result["policies"] == ["first_legal", "bounded_search"]
    assert len(calls) == 2
    assert all(call["decision_provenance_hook"] is hook for call in calls)
    assert all(call["game_declaration"] is not None for call in calls)
