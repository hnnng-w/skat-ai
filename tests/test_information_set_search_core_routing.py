from dataclasses import fields, replace

import pytest
from test_compatible_world_minimax import _budget as _pimc_budget
from test_compatible_world_minimax import _sampled_view
from test_information_set_search_state_and_preparation import _find_view

import skatmind.compatible_world_minimax as pimc_module
import skatmind.information_set_search_executor as executor_module
import skatmind.recommendation_workflow as recommendation_module
from skatmind.compatible_search_world import (
    build_compatible_search_world_space,
    select_compatible_search_worlds,
)
from skatmind.compatible_world_minimax import (
    solve_compatible_world_minimax,
    solve_compatible_world_minimax_on_selection_v1,
)
from skatmind.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skatmind.game_state import GameState
from skatmind.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_BUDGET_VERSION,
    InformationSetSearchBudgetV1,
)
from skatmind.information_set_search_executor import (
    INFORMATION_SET_SEARCH_EXECUTION_ALGORITHM,
)
from skatmind.information_set_search_public import (
    INFORMATION_SET_SEARCH_PUBLIC_RESULT_POLICY,
    INFORMATION_SET_SEARCH_PUBLIC_RESULT_VERSION,
    build_public_information_set_search_result_v1,
)
from skatmind.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_ACTUAL_CARD_POLICY,
    INFORMATION_SET_SEARCH_BASELINE_POLICY,
    INFORMATION_SET_SEARCH_COMPATIBILITY_POLICY,
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
    INFORMATION_SET_SEARCH_FIXED_POLICY_SOURCE_POLICY,
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
    INFORMATION_SET_SEARCH_ROUTING_POLICY,
    INFORMATION_SET_SEARCH_ROUTING_VERSION,
    InformationSetSearchSettings,
    build_information_set_search_policy_settings_v1,
    convert_information_set_search_budget_to_requested_search_budget_v1,
    execute_live_information_set_search_workflow_v1,
)
from skatmind.recommendation_workflow import (
    AUTO_METHOD,
    BOUNDED_SEARCH_METHOD,
    FLAT_RECOMMENDATION_METHODS,
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    SEARCH_RECOMMENDATION_METHODS,
    VALID_RECOMMENDATION_METHODS,
    RecommendationMethodConfiguration,
    build_recommendation_method_configuration,
    build_recommendation_method_summary,
    execute_recommendation_workflow,
)
from skatmind.search_budget_profiles import (
    SEARCH_BUDGET_PROFILE_IDENTIFIERS,
    get_information_set_search_budget_profile,
    get_search_budget_profile,
)


def _settings(**changes: int | None) -> InformationSetSearchSettings:
    values = {
        "random_seed": 17,
        "max_remaining_tricks": 1,
        "max_depth_plies": 3,
        "max_state_nodes": 20_000,
        "max_information_sets": 20_000,
        "max_selected_worlds": 4,
        "max_sampled_worlds": 4,
        "minimum_comparable_worlds": 1,
        "wall_clock_timeout_ms": None,
    }
    values.update(changes)
    return InformationSetSearchSettings(**values)  # type: ignore[arg-type]


def _settings_dict(**changes: int | None) -> dict[str, int | None]:
    settings = _settings(**changes)
    return {item.name: getattr(settings, item.name) for item in fields(settings)}


def _state_from_view(view) -> GameState:
    completed_tricks = [
        {
            "cards": [play.card for play in trick.plays],
            "players": [play.player for play in trick.plays],
            "winner_player": trick.winner_player,
            "winner_role": trick.winner_side,
        }
        for trick in view.completed_tricks
    ]
    return GameState(
        game_type=view.game_type,
        player_role="declarer" if view.declarer_player == "me" else "defender",
        declarer_player=view.declarer_player,
        hand=list(view.local_remaining_hand),
        current_trick=[play.card for play in view.current_trick],
        completed_tricks=completed_tricks,
        skat=list(view.known_skat_cards),
        trick_leader=(
            view.current_trick[0].player if view.current_trick else view.next_player
        ),
        declarer_points=0,
        defender_points=0,
        next_player=view.next_player,
    )


def _effective(**changes: str) -> EffectiveOpponentPolicySettings:
    values = {
        "global_lead_policy": "lowest_point",
        "global_response_policy": "lowest_point",
        "left_lead_policy": "lowest_point",
        "left_response_policy": "lowest_point",
        "right_lead_policy": "lowest_point",
        "right_response_policy": "lowest_point",
        "immediate_response_policy_by_player": None,
        "left_lead_source": "profile",
        "left_response_source": "profile",
        "right_lead_source": "input_explicit",
        "right_response_source": "input_explicit",
    }
    values.update(changes)
    return EffectiveOpponentPolicySettings(**values)  # type: ignore[arg-type]


def test_versions_methods_and_routing_policies_are_exact() -> None:
    assert INFORMATION_SET_SEARCH_ROUTING_VERSION == 1
    assert INFORMATION_SET_SEARCH_PUBLIC_RESULT_VERSION == 1
    assert INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD == "information_set_search"
    assert INFORMATION_SET_SEARCH_EXECUTION_ALGORITHM == (
        "selected_world_information_set_best_response_v1"
    )
    assert INFORMATION_SET_SEARCH_EFFECTIVE_METHOD == (
        "bounded_information_set_policy_search_v1"
    )
    assert (
        INFORMATION_SET_SEARCH_ROUTING_POLICY,
        INFORMATION_SET_SEARCH_FIXED_POLICY_SOURCE_POLICY,
        INFORMATION_SET_SEARCH_BASELINE_POLICY,
        INFORMATION_SET_SEARCH_ACTUAL_CARD_POLICY,
        INFORMATION_SET_SEARCH_PUBLIC_RESULT_POLICY,
        INFORMATION_SET_SEARCH_COMPATIBILITY_POLICY,
    ) == (
        "strict_information_set_search_without_fallback",
        "existing_effective_left_right_policy_settings",
        "same_selected_world_pimc_plus_independent_immediate",
        "attach_actual_card_only_after_decision_time_analysis",
        "safe_aggregate_result_without_private_policy_table",
        "existing_immediate_bounded_search_and_auto_unchanged",
    )
    assert VALID_RECOMMENDATION_METHODS == (
        "immediate_expected_value",
        "bounded_search",
        "auto",
    )
    assert SEARCH_RECOMMENDATION_METHODS == ("bounded_search", "auto")
    assert FLAT_RECOMMENDATION_METHODS == (
        *VALID_RECOMMENDATION_METHODS,
        "information_set_search",
    )
    assert not isinstance(INFORMATION_SET_SEARCH_ROUTING_VERSION, bool)
    assert not isinstance(INFORMATION_SET_SEARCH_PUBLIC_RESULT_VERSION, bool)


def test_information_set_settings_are_exact_and_strict() -> None:
    settings = _settings()
    assert tuple(item.name for item in fields(settings)) == (
        "random_seed",
        "max_remaining_tricks",
        "max_depth_plies",
        "max_state_nodes",
        "max_information_sets",
        "max_selected_worlds",
        "max_sampled_worlds",
        "minimum_comparable_worlds",
        "wall_clock_timeout_ms",
    )
    assert settings.to_budget().max_state_nodes == 20_000
    assert _settings(wall_clock_timeout_ms=1).wall_clock_timeout_ms == 1

    for changes in (
        {"random_seed": True},
        {"max_remaining_tricks": 4},
        {"max_depth_plies": 0},
        {"max_state_nodes": True},
        {"max_information_sets": -1},
        {"wall_clock_timeout_ms": 0},
        {"wall_clock_timeout_ms": True},
    ):
        with pytest.raises(ValueError):
            _settings(**changes)


@pytest.mark.parametrize(
    "data",
    [
        {"recommendation_method": "information_set_search"},
        {
            "recommendation_method": "information_set_search",
            "information_set_search_settings": {
                **_settings_dict(),
                "unknown": 1,
            },
        },
        {
            "recommendation_method": "information_set_search",
            "information_set_search_settings": {
                key: value
                for key, value in _settings_dict().items()
                if key != "max_information_sets"
            },
        },
        {
            "recommendation_method": "information_set_search",
            "information_set_search_settings": _settings_dict(),
            "bounded_search_settings": {},
        },
        {
            "recommendation_method": BOUNDED_SEARCH_METHOD,
            "information_set_search_settings": _settings_dict(),
        },
        {
            "recommendation_method": IMMEDIATE_EXPECTED_VALUE_METHOD,
            "information_set_search_settings": _settings_dict(),
        },
    ],
)
def test_flat_configuration_rejects_mismatched_or_non_strict_settings(data) -> None:
    with pytest.raises(ValueError):
        build_recommendation_method_configuration(data)


def test_flat_configuration_accepts_information_set_settings_without_changing_defaults() -> None:
    configuration = build_recommendation_method_configuration(
        {
            "recommendation_method": "information_set_search",
            "information_set_search_settings": _settings_dict(),
        }
    )
    omitted = build_recommendation_method_configuration({})

    assert configuration.information_set_search_settings == _settings()
    assert configuration.requested_search_budget is None
    assert configuration.search_random_seed is None
    assert omitted == RecommendationMethodConfiguration(
        explicitly_supplied=False,
        requested_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
    )


def test_effective_fixed_policy_mapping_has_names_but_no_sources() -> None:
    effective = _effective(
        left_lead_policy="highest_point",
        left_response_policy="basic_trick_play",
        right_lead_policy="basic_defender_lead",
        right_response_policy="basic_defender_response",
    )
    settings = build_information_set_search_policy_settings_v1(effective)

    assert settings is not None
    assert [item.to_dict() for item in settings.fixed_player_policies] == [
        {
            "player": "left",
            "lead_policy": "highest_point",
            "response_policy": "basic_trick_play",
            "tie_policy": "first_canonical_preferred_card",
        },
        {
            "player": "right",
            "lead_policy": "basic_defender_lead",
            "response_policy": "basic_defender_response",
            "tie_policy": "first_canonical_preferred_card",
        },
    ]
    text = repr(settings.to_dict())
    assert "source" not in text
    assert "profile" not in text
    assert "statistics" not in text
    assert "confidence" not in text


def test_random_fixed_policy_is_canonically_unavailable_without_replacement() -> None:
    view, _ = _find_view(
        actor="me",
        remaining_tricks=1,
        hand_game=True,
        public_players=("left", "right"),
    )
    effective = _effective(left_response_policy="random_legal")
    assert build_information_set_search_policy_settings_v1(effective) is None

    workflow = execute_live_information_set_search_workflow_v1(
        information_view=view,
        settings=_settings(),
        effective_policy_settings=effective,
        request_builder=lambda **_kwargs: pytest.fail("random policy built a Request"),
        preparation_builder=lambda _request: pytest.fail("random policy prepared Search"),
        executor=lambda _preparation: pytest.fail("random policy executed Search"),
    )

    assert workflow.request is workflow.preparation is workflow.result is None
    assert workflow.public_result["status"] == "unavailable"
    assert workflow.public_result["stop_reason"] == "nondeterministic_fixed_policy"
    assert workflow.public_result["fixed_policy_settings"][0][
        "response_policy"
    ] == "random_legal"
    assert not any(workflow.public_result["consumed_budget"].values())


def test_role_invalid_deterministic_policy_flows_through_private_unavailability() -> None:
    view, _ = _find_view(
        actor="me",
        remaining_tricks=1,
        declarer_player="left",
        hand_game=True,
        public_players=("left", "right"),
    )
    workflow = execute_live_information_set_search_workflow_v1(
        information_view=view,
        settings=_settings(),
        effective_policy_settings=_effective(
            left_lead_policy="basic_defender_lead",
        ),
    )

    assert workflow.request is not None
    assert workflow.preparation is not None
    assert workflow.preparation.status == "unavailable"
    assert workflow.result is not None
    assert workflow.result.status == "unavailable"
    assert workflow.public_result["stop_reason"] == "unsupported_fixed_policy"


def test_live_flat_routing_executes_once_without_pimc_immediate_or_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view, _ = _find_view(
        actor="me",
        remaining_tricks=1,
        hand_game=True,
        public_players=("left", "right"),
    )
    state = _state_from_view(view)
    configuration = RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method=INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
        information_set_search_settings=_settings(),
    )
    effective = build_effective_opponent_policy_settings({})
    calls = {"workflow": 0}

    def counted_workflow(**kwargs):
        calls["workflow"] += 1
        return execute_live_information_set_search_workflow_v1(**kwargs)

    monkeypatch.setattr(
        recommendation_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: pytest.fail("live Information-set Search ran PIMC"),
    )
    monkeypatch.setattr(
        recommendation_module,
        "recommend_card_by_expected_value",
        lambda **_kwargs: pytest.fail("live Information-set Search ran Immediate"),
    )
    result = execute_recommendation_workflow(
        configuration=configuration,
        state=state,
        declaration=view.declaration,
        left_hand_size=view.remaining_hand_size("left"),
        right_hand_size=view.remaining_hand_size("right"),
        sample_count=5,
        immediate_random_seed=99,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={},
        public_hand_constraints=view.public_hand_constraints,
        skat_visibility="unknown",
        immediate_unavailable_reason=None,
        effective_opponent_policy_settings=effective,
        information_set_workflow_executor=counted_workflow,
    )

    assert calls == {"workflow": 1}
    assert result.recommendation_card is not None
    assert result.effective_method == INFORMATION_SET_SEARCH_EFFECTIVE_METHOD
    assert result.fallback_used is False
    assert result.fallback_method is None
    assert result.bounded_search_result is None
    assert result.analysis_report == ()
    assert result.information_set_search_result is not None
    assert result.information_set_search_result.status == "complete"
    assert result.information_set_search_public_result is not None
    assert build_recommendation_method_summary(result)["search_attempted"] is True
    wording = result.recommendation_reason
    assert "Information-set Search" in wording
    assert "one action per equal Information Set" in wording
    assert "supplied fixed opponent Policies" in wording
    assert "selected World sequence" in wording
    assert "not calibrated probability" in wording
    assert "not an equilibrium or globally optimal" in wording


def test_partial_timeout_and_unavailable_results_never_recommend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view, _ = _find_view(
        actor="me",
        remaining_tricks=1,
        hand_game=True,
        public_players=("left", "right"),
    )
    effective = build_effective_opponent_policy_settings({})
    partial = execute_live_information_set_search_workflow_v1(
        information_view=view,
        settings=_settings(max_state_nodes=1),
        effective_policy_settings=effective,
    )

    clock_calls = 0

    def timeout_clock() -> float:
        nonlocal clock_calls
        clock_calls += 1
        return 0.0 if clock_calls == 1 else 0.002

    monkeypatch.setattr(executor_module, "_monotonic", timeout_clock)
    timeout = execute_live_information_set_search_workflow_v1(
        information_view=view,
        settings=_settings(wall_clock_timeout_ms=1),
        effective_policy_settings=effective,
    )
    unavailable = execute_live_information_set_search_workflow_v1(
        information_view=view,
        settings=_settings(),
        effective_policy_settings=_effective(left_lead_policy="random_legal"),
    )

    assert [
        item.public_result["status"] for item in (partial, timeout, unavailable)
    ] == ["partial", "timeout", "unavailable"]
    assert all(
        item.public_result["recommended_card"] is None
        for item in (partial, timeout, unavailable)
    )


def test_public_projection_is_fresh_mutable_and_omits_private_values() -> None:
    view, _ = _find_view(
        actor="me",
        remaining_tricks=1,
        hand_game=True,
        public_players=("left", "right"),
    )
    workflow = execute_live_information_set_search_workflow_v1(
        information_view=view,
        settings=_settings(),
        effective_policy_settings=build_effective_opponent_policy_settings({}),
    )
    assert workflow.result is not None
    first = build_public_information_set_search_result_v1(workflow.result)
    second = build_public_information_set_search_result_v1(workflow.result)

    assert tuple(first) == (
        "schema_version",
        "analysis_method",
        "search_method",
        "status",
        "stop_reason",
        "game_type",
        "world_coverage",
        "policy_claim",
        "policy_consistency",
        "terminal_utility_version",
        "requested_budget",
        "consumed_budget",
        "compatible_world_count",
        "candidate_results",
        "recommended_card",
        "controlled_policy_decision_count",
        "fixed_policy_settings",
    )
    assert tuple(first["consumed_budget"]) == (
        "depth_reached",
        "state_nodes_evaluated",
        "information_sets_evaluated",
        "controlled_policy_decisions",
        "fixed_policy_decisions",
        "selected_world_count",
        "completed_world_count",
        "sampled_world_count",
        "unique_sampled_world_count",
        "wall_clock_elapsed_ms",
    )
    assert tuple(first["fixed_policy_settings"][0]) == (
        "player",
        "lead_policy",
        "response_policy",
    )
    first["candidate_results"].clear()
    first["fixed_policy_settings"][0]["lead_policy"] = "changed"
    assert second["candidate_results"]
    assert second["fixed_policy_settings"][0]["lead_policy"] == "lowest_point"
    private_names = {
        "controlled_policy",
        "information_set",
        "own_remaining_hand",
        "exact_states",
        "world_states",
        "memoization",
        "bundle_memo",
    }

    def keys(value):
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert private_names.isdisjoint(keys(second))


def test_same_selection_pimc_preserves_order_duplicates_and_root_cards_without_reselection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = _sampled_view(game_type="null")
    budget = _pimc_budget(max_selected_worlds=10, max_sampled_worlds=10)
    world_space = build_compatible_search_world_space(view)
    selection = next(
        selection
        for seed in range(100)
        if (
            selection := select_compatible_search_worlds(
                world_space=world_space,
                requested_budget=budget,
                random_seed=seed,
            )
        ).unique_sampled_world_count
        < selection.sampled_world_count
    )
    evaluated_states = []
    original_evaluate = pimc_module._evaluate_exact_world_root_utilities

    def capture_state(**kwargs):
        evaluated_states.append(kwargs["state"])
        return original_evaluate(**kwargs)

    monkeypatch.setattr(
        pimc_module,
        "build_compatible_search_world_space",
        lambda _view: pytest.fail("same-selection PIMC rebuilt worlds"),
    )
    monkeypatch.setattr(
        pimc_module,
        "select_compatible_search_worlds",
        lambda **_kwargs: pytest.fail("same-selection PIMC reselected worlds"),
    )
    monkeypatch.setattr(
        pimc_module,
        "_evaluate_exact_world_root_utilities",
        capture_state,
    )
    result = solve_compatible_world_minimax_on_selection_v1(
        information_view=view,
        requested_budget=budget,
        selection=selection,
    )

    assert tuple(evaluated_states) == selection.exact_states
    assert len(set(evaluated_states)) < len(evaluated_states)
    assert result.compatible_world_count == selection.compatible_world_count
    assert result.consumed_budget.selected_world_count == selection.selected_world_count
    assert result.consumed_budget.sampled_world_count == selection.sampled_world_count
    assert result.consumed_budget.unique_sampled_world_count == (
        selection.unique_sampled_world_count
    )
    assert {item.card for item in result.candidate_results} == set(
        selection.legal_root_cards
    )
    with pytest.raises(ValueError, match="does not belong"):
        solve_compatible_world_minimax_on_selection_v1(
            information_view=replace(
                view,
                declarer_points=view.declarer_points + 1,
            ),
            requested_budget=budget,
            selection=selection,
        )
    with pytest.raises(ValueError, match="exceeds"):
        solve_compatible_world_minimax_on_selection_v1(
            information_view=view,
            requested_budget=_pimc_budget(
                max_selected_worlds=5,
                max_sampled_worlds=5,
            ),
            selection=selection,
        )


def test_existing_pimc_entry_matches_the_new_seam_on_its_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = _sampled_view(game_type="grand")
    budget = _pimc_budget(max_selected_worlds=5, max_sampled_worlds=5)
    seed = 31
    selection = select_compatible_search_worlds(
        world_space=build_compatible_search_world_space(view),
        requested_budget=budget,
        random_seed=seed,
    )
    monkeypatch.setattr(pimc_module, "_monotonic", lambda: 10.0)

    existing = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=budget,
        random_seed=seed,
    )
    retained = solve_compatible_world_minimax_on_selection_v1(
        information_view=view,
        requested_budget=budget,
        selection=selection,
    )

    assert existing == retained


def test_information_set_budget_conversions_are_exact_and_profiles_unchanged() -> None:
    information_set_budget = InformationSetSearchBudgetV1(
        information_set_search_budget_version=INFORMATION_SET_SEARCH_BUDGET_VERSION,
        max_remaining_tricks=3,
        max_depth_plies=8,
        max_state_nodes=123,
        max_information_sets=99,
        max_selected_worlds=7,
        max_sampled_worlds=6,
        minimum_comparable_worlds=5,
        wall_clock_timeout_ms=4,
    )
    converted = convert_information_set_search_budget_to_requested_search_budget_v1(
        information_set_budget
    )
    assert tuple(getattr(converted, item.name) for item in fields(converted)) == (
        3,
        8,
        123,
        7,
        6,
        5,
        4,
    )
    assert not hasattr(converted, "max_information_sets")

    original_profiles = {
        identifier: get_search_budget_profile(identifier)
        for identifier in SEARCH_BUDGET_PROFILE_IDENTIFIERS
    }
    expected = {
        "interactive_v1": (3, 9, 500_000, 500_000, 64, 32, 8, 1_000),
        "historical_review_v1": (3, 9, 2_000_000, 2_000_000, 128, 64, 16, 5_000),
        "evaluation_v1": (3, 9, 10_000_000, 10_000_000, 512, 256, 32, None),
    }
    for identifier, values in expected.items():
        budget = get_information_set_search_budget_profile(identifier)
        assert (
            budget.max_remaining_tricks,
            budget.max_depth_plies,
            budget.max_state_nodes,
            budget.max_information_sets,
            budget.max_selected_worlds,
            budget.max_sampled_worlds,
            budget.minimum_comparable_worlds,
            budget.wall_clock_timeout_ms,
        ) == values
        assert get_search_budget_profile(identifier) is original_profiles[identifier]


def test_existing_methods_still_accept_their_original_configuration_shapes() -> None:
    bounded = build_recommendation_method_configuration(
        {
            "recommendation_method": BOUNDED_SEARCH_METHOD,
            "bounded_search_settings": {
                "random_seed": 1,
                "max_remaining_tricks": 1,
                "max_depth_plies": 3,
                "max_nodes": 10,
                "max_selected_worlds": 1,
                "max_sampled_worlds": 1,
                "minimum_comparable_worlds": 1,
                "wall_clock_timeout_ms": None,
            },
        }
    )
    auto = RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method=AUTO_METHOD,
        search_random_seed=bounded.search_random_seed,
        requested_search_budget=bounded.requested_search_budget,
    )

    assert bounded.information_set_search_settings is None
    assert auto.information_set_search_settings is None
