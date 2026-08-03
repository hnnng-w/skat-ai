import json
from dataclasses import replace
from pathlib import Path

import pytest

import skat_ai.recommendation_workflow as workflow_module
from skat_ai.bounded_search_result import (
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    mark_bounded_search_fallback_used,
    rank_search_candidate_results,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.input_validation import validate_position_input
from skat_ai.recommendation_workflow import (
    AUTO_METHOD,
    BOUNDED_SEARCH_METHOD,
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    RecommendationMethodConfiguration,
    build_recommendation_method_configuration,
    build_recommendation_method_summary,
    execute_recommendation_workflow,
    validate_recommendation_method_workflow,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _budget(**overrides: int | None) -> RequestedSearchBudget:
    values = {
        "max_remaining_tricks": 1,
        "max_depth_plies": 3,
        "max_nodes": 100,
        "max_selected_worlds": 2,
        "max_sampled_worlds": 2,
        "minimum_comparable_worlds": 1,
        "wall_clock_timeout_ms": None,
    }
    values.update(overrides)
    return RequestedSearchBudget(**values)  # type: ignore[arg-type]


def _settings(**overrides: int | None) -> dict[str, int | None]:
    values = {
        "random_seed": 113,
        "max_remaining_tricks": 1,
        "max_depth_plies": 3,
        "max_nodes": 100,
        "max_selected_worlds": 2,
        "max_sampled_worlds": 2,
        "minimum_comparable_worlds": 1,
        "wall_clock_timeout_ms": None,
    }
    values.update(overrides)
    return values


def _state(*, next_player: str = "me") -> GameState:
    return GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        player_position="forehand",
        trick_leader=next_player,
        hand=["D7"],
        current_trick=[],
        played_cards=[],
        completed_tricks=[],
        next_player=next_player,
    )


def _candidate(
    card: str = "D7",
    *,
    completed: int,
    recommended: bool,
) -> tuple[AggregateSearchCandidateResult, ...]:
    return rank_search_candidate_results(
        (
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=completed,
                local_contract_success_count=completed,
                local_contract_success_rate=1.0 if completed else None,
                mean_local_side_game_score=24.0 if completed else None,
                mean_local_side_card_point_margin=10.0 if completed else None,
            ),
        ),
        "grand",
        recommend=recommended,
    )


def _search_result(
    *,
    status: str = "complete",
    stop_reason: str = "completed",
    completed: int = 2,
    recommended: bool = True,
    timeout: bool = False,
    sampled: bool = False,
) -> BoundedSearchResult:
    budget = _budget(wall_clock_timeout_ms=1 if timeout else None)
    claim = {
        "completed": "exact_per_selected_world",
        "node_budget_exhausted": "node_limited_partial",
        "depth_budget_exhausted": "depth_limited_per_selected_world",
        "wall_clock_timeout": "none",
    }[stop_reason]
    return BoundedSearchResult(
        schema_version=1,
        analysis_method="bounded_search",
        search_method="compatible_world_minimax_v1",
        game_type="grand",
        status=status,
        stop_reason=stop_reason,
        world_coverage=("sampled_compatible_worlds" if sampled else "all_compatible_worlds"),
        solution_claim=claim,
        terminal_utility_version=1,
        requested_budget=budget,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=1,
            nodes_expanded=2,
            selected_world_count=2,
            completed_world_count=completed,
            sampled_world_count=2 if sampled else 0,
            unique_sampled_world_count=2 if sampled else 0,
            wall_clock_elapsed_ms=0,
        ),
        compatible_world_count=2,
        candidate_results=_candidate(completed=completed, recommended=recommended),
        recommended_card="D7" if recommended else None,
        fallback_used=False,
        fallback_method=None,
    )


def _unavailable_search_result() -> BoundedSearchResult:
    return BoundedSearchResult(
        schema_version=1,
        analysis_method="bounded_search",
        search_method="compatible_world_minimax_v1",
        game_type="grand",
        status="unavailable",
        stop_reason="local_player_not_to_act",
        world_coverage="none",
        solution_claim="none",
        terminal_utility_version=1,
        requested_budget=_budget(),
        consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
        compatible_world_count=None,
        candidate_results=(),
        recommended_card=None,
        fallback_used=False,
        fallback_method=None,
    )


def _configuration(
    method: str,
    budget: RequestedSearchBudget | None = None,
) -> RecommendationMethodConfiguration:
    return RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method=method,
        search_random_seed=113 if method != IMMEDIATE_EXPECTED_VALUE_METHOD else None,
        requested_search_budget=(
            budget or _budget() if method != IMMEDIATE_EXPECTED_VALUE_METHOD else None
        ),
    )


def _execute(configuration: RecommendationMethodConfiguration, **overrides):
    values = {
        "configuration": configuration,
        "state": _state(),
        "declaration": GameDeclaration("grand", matadors=1, bid_value=24),
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 10,
        "immediate_random_seed": 42,
        "use_basic_opponent_strategy": True,
        "opponent_response_policy_by_player": {},
        "public_hand_constraints": (),
        "skat_visibility": "unknown",
        "immediate_unavailable_reason": None,
    }
    values.update(overrides)
    return execute_recommendation_workflow(**values)


def _stub_immediate(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    monkeypatch.setattr(
        workflow_module,
        "build_hidden_card_inference_model",
        lambda *_args, **_kwargs: None,
    )

    def recommend(**_kwargs):
        calls.append("immediate")
        return (
            "D7",
            "Immediate reason.",
            {
                "D7": {
                    "win_rate": 1.0,
                    "average_trick_points": 0.0,
                    "average_points_won": 0.0,
                    "average_points_lost": 0.0,
                }
            },
        )

    monkeypatch.setattr(workflow_module, "recommend_card_by_expected_value", recommend)


@pytest.mark.parametrize(
    "method",
    [IMMEDIATE_EXPECTED_VALUE_METHOD, BOUNDED_SEARCH_METHOD, AUTO_METHOD],
)
def test_configuration_accepts_all_explicit_methods(method: str) -> None:
    data = {"recommendation_method": method}
    if method != IMMEDIATE_EXPECTED_VALUE_METHOD:
        data["bounded_search_settings"] = _settings()

    configuration = build_recommendation_method_configuration(data)

    assert configuration.requested_method == method
    assert configuration.explicitly_supplied is True


def test_configuration_omission_is_backward_compatible_immediate() -> None:
    configuration = build_recommendation_method_configuration({})

    assert configuration.requested_method == IMMEDIATE_EXPECTED_VALUE_METHOD
    assert configuration.explicitly_supplied is False
    assert configuration.requested_search_budget is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"recommendation_method": "unknown"}, "Invalid recommendation_method"),
        ({"recommendation_method": BOUNDED_SEARCH_METHOD}, "requires bounded_search_settings"),
        ({"bounded_search_settings": _settings()}, "allowed only"),
        (
            {
                "recommendation_method": IMMEDIATE_EXPECTED_VALUE_METHOD,
                "bounded_search_settings": _settings(),
            },
            "allowed only",
        ),
        (
            {
                "recommendation_method": AUTO_METHOD,
                "bounded_search_settings": {**_settings(), "unknown": 1},
            },
            "unsupported keys",
        ),
        (
            {
                "recommendation_method": AUTO_METHOD,
                "bounded_search_settings": {
                    key: value for key, value in _settings().items() if key != "max_nodes"
                },
            },
            "missing required keys",
        ),
        (
            {
                "recommendation_method": AUTO_METHOD,
                "bounded_search_settings": {**_settings(), "random_seed": True},
            },
            "must not be a boolean",
        ),
        (
            {
                "recommendation_method": AUTO_METHOD,
                "bounded_search_settings": {**_settings(), "max_nodes": 0},
            },
            "max_nodes",
        ),
    ],
)
def test_configuration_rejects_invalid_contracts(data: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_recommendation_method_configuration(data)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"analysis_mode": "post_game_review"}, "actual_card_played"),
        ({"game_end_reason": "normal_completion"}, "game_end_reason"),
        ({"skat_visibility": "known_post_game"}, "post-game Skat"),
        ({"actual_card_played": "D7"}, "actual_card_played"),
        ({"played_cards": ["C7"]}, "legacy played_cards"),
        ({"game_shortening": {}}, "terminal game shortening"),
        ({"impossible_null_settlement": {}}, "impossible-Null"),
        ({"list_performance_input": {}}, "flat position"),
        (
            {"completed_tricks": [{"cards": ["C7", "C8", "C9"]}]},
            "attributed completed_tricks",
        ),
    ],
)
def test_search_workflow_restrictions(override: dict, message: str) -> None:
    data = {
        "analysis_mode": "live_decision",
        "game_end_reason": "not_ended",
        "skat_visibility": "unknown",
        "played_cards": [],
        "completed_tricks": [],
    }
    data.update(override)

    with pytest.raises(ValueError, match=message):
        validate_recommendation_method_workflow(data, _configuration(BOUNDED_SEARCH_METHOD))


def test_omitted_and_explicit_immediate_invoke_only_immediate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _stub_immediate(monkeypatch, calls)
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("Search must not run")),
    )

    omitted = _execute(build_recommendation_method_configuration({}))
    explicit = _execute(_configuration(IMMEDIATE_EXPECTED_VALUE_METHOD))

    assert calls == ["immediate", "immediate"]
    assert omitted.recommendation_card == explicit.recommendation_card == "D7"
    assert omitted.analysis_report == explicit.analysis_report


@pytest.mark.parametrize(
    "search_result",
    [
        _search_result(),
        _search_result(
            status="partial",
            stop_reason="node_budget_exhausted",
            completed=1,
        ),
        _search_result(
            status="timeout",
            stop_reason="wall_clock_timeout",
            completed=1,
            timeout=True,
        ),
    ],
)
def test_search_recommendation_skips_immediate_for_strict_and_auto(
    monkeypatch: pytest.MonkeyPatch,
    search_result: BoundedSearchResult,
) -> None:
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: search_result,
    )
    monkeypatch.setattr(
        workflow_module,
        "recommend_card_by_expected_value",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("Immediate must not run")),
    )

    for method in (BOUNDED_SEARCH_METHOD, AUTO_METHOD):
        result = _execute(_configuration(method, search_result.requested_budget))
        assert result.effective_method == "compatible_world_minimax_v1"
        assert result.recommendation_card == "D7"
        assert result.analysis_report == ()
        assert result.analysis_report_method == "none"


def test_strict_search_without_recommendation_never_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search_result = _search_result(
        status="partial",
        stop_reason="node_budget_exhausted",
        completed=0,
        recommended=False,
    )
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: search_result,
    )
    monkeypatch.setattr(
        workflow_module,
        "recommend_card_by_expected_value",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("Fallback must not run")),
    )

    result = _execute(_configuration(BOUNDED_SEARCH_METHOD))

    assert result.effective_method == "none"
    assert result.recommendation_card is None
    assert result.fallback_used is False
    assert result.analysis_report == ()


@pytest.mark.parametrize(
    "search_result",
    [
        _search_result(
            status="partial",
            stop_reason="node_budget_exhausted",
            completed=0,
            recommended=False,
        ),
        _search_result(
            status="timeout",
            stop_reason="wall_clock_timeout",
            completed=0,
            recommended=False,
            timeout=True,
        ),
    ],
)
def test_auto_below_threshold_search_falls_back_to_immediate(
    monkeypatch: pytest.MonkeyPatch,
    search_result: BoundedSearchResult,
) -> None:
    calls: list[str] = []
    _stub_immediate(monkeypatch, calls)
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: search_result,
    )

    result = _execute(_configuration(AUTO_METHOD, search_result.requested_budget))

    assert calls == ["immediate"]
    assert result.effective_method == IMMEDIATE_EXPECTED_VALUE_METHOD
    assert result.recommendation_card == "D7"
    assert result.fallback_used is True
    assert result.bounded_search_result is not None
    assert result.bounded_search_result.fallback_used is True
    assert result.analysis_report[0]["is_recommended"] is True
    assert "Auto fallback" in result.recommendation_reason


def test_search_exception_is_not_hidden_by_auto_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("search invariant")),
    )

    with pytest.raises(RuntimeError, match="search invariant"):
        _execute(_configuration(AUTO_METHOD))


def test_invalid_search_result_is_not_hidden_by_auto_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: object(),
    )

    with pytest.raises(ValueError, match="invalid bounded-search result"):
        _execute(_configuration(AUTO_METHOD))


@pytest.mark.parametrize(
    ("search_result", "message"),
    [
        (replace(_search_result(), game_type="hearts"), "different game type"),
        (
            replace(_search_result(), requested_budget=_budget(max_nodes=101)),
            "different requested budget",
        ),
        (
            replace(
                _unavailable_search_result(),
                search_method="perfect_information_minimax_v1",
            ),
            "unexpected method",
        ),
        (
            mark_bounded_search_fallback_used(
                _search_result(
                    status="partial",
                    stop_reason="node_budget_exhausted",
                    completed=0,
                    recommended=False,
                )
            ),
            "caller-owned fallback metadata",
        ),
    ],
)
def test_contextually_invalid_search_result_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
    search_result: BoundedSearchResult,
    message: str,
) -> None:
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: search_result,
    )

    with pytest.raises(ValueError, match=message):
        _execute(_configuration(AUTO_METHOD))


def test_search_and_immediate_use_their_separate_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int | None] = {}
    search_result = _search_result(
        status="partial",
        stop_reason="node_budget_exhausted",
        completed=0,
        recommended=False,
    )

    def solve(**kwargs):
        captured["search"] = kwargs["random_seed"]
        return search_result

    def recommend(**kwargs):
        captured["immediate"] = kwargs["random_seed"]
        return (
            "D7",
            "Immediate reason.",
            {
                "D7": {
                    "win_rate": 1.0,
                    "average_trick_points": 0.0,
                    "average_points_won": 0.0,
                    "average_points_lost": 0.0,
                }
            },
        )

    monkeypatch.setattr(workflow_module, "solve_compatible_world_minimax", solve)
    monkeypatch.setattr(workflow_module, "recommend_card_by_expected_value", recommend)
    monkeypatch.setattr(
        workflow_module,
        "build_hidden_card_inference_model",
        lambda *_args, **_kwargs: None,
    )

    _execute(_configuration(AUTO_METHOD), immediate_random_seed=42)

    assert captured == {"search": 113, "immediate": 42}


def test_failed_immediate_fallback_is_not_marked_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search_result = _unavailable_search_result()
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: search_result,
    )

    result = _execute(
        _configuration(AUTO_METHOD),
        state=_state(next_player="left"),
        immediate_unavailable_reason="Immediate unavailable.",
    )

    assert result.effective_method == "none"
    assert result.recommendation_card is None
    assert result.fallback_used is False
    assert result.bounded_search_result == search_result
    assert "fallback" not in result.recommendation_reason.lower()
    assert "used Immediate" not in result.strategic_summary
    assert "also returned no recommendation" in result.recommendation_reason


def test_fallback_helper_preserves_search_evidence_and_rejects_invalid_use() -> None:
    search_result = _search_result(
        status="partial",
        stop_reason="node_budget_exhausted",
        completed=0,
        recommended=False,
    )

    marked = mark_bounded_search_fallback_used(search_result)

    assert marked == replace(
        search_result,
        fallback_used=True,
        fallback_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
    )
    assert marked.candidate_results is search_result.candidate_results
    with pytest.raises(ValueError, match="cannot use fallback"):
        mark_bounded_search_fallback_used(_search_result())
    with pytest.raises(ValueError, match="already"):
        mark_bounded_search_fallback_used(marked)


def test_method_summary_matches_effective_search_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_module,
        "solve_compatible_world_minimax",
        lambda **_kwargs: _search_result(),
    )

    result = _execute(_configuration(BOUNDED_SEARCH_METHOD))

    assert build_recommendation_method_summary(result) == {
        "requested_method": "bounded_search",
        "effective_method": "compatible_world_minimax_v1",
        "search_attempted": True,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": "none",
    }
    assert "status complete" in result.recommendation_reason
    assert "1.000" in result.recommendation_reason
    assert "mean settlement score 24.00" in result.recommendation_reason
    assert "optimal imperfect-information policy" in result.recommendation_reason


def test_search_reason_covers_complete_sampled_and_incomplete_prefixes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = (
        _search_result(sampled=True),
        _search_result(
            status="partial",
            stop_reason="depth_budget_exhausted",
            completed=1,
        ),
        _search_result(
            status="timeout",
            stop_reason="wall_clock_timeout",
            completed=1,
            timeout=True,
        ),
    )

    for search_result in results:
        monkeypatch.setattr(
            workflow_module,
            "solve_compatible_world_minimax",
            lambda search_result=search_result, **_kwargs: search_result,
        )
        result = _execute(
            _configuration(BOUNDED_SEARCH_METHOD, search_result.requested_budget)
        )
        assert f"status {search_result.status}" in result.recommendation_reason
        assert f"stop reason {search_result.stop_reason}" in result.recommendation_reason
        assert search_result.world_coverage.replace("_", " ") in (
            result.recommendation_reason
        )


def test_search_accepts_declared_ouvert_public_hand() -> None:
    with (PROJECT_ROOT / "examples" / "grand_second_position.json").open(
        "r", encoding="utf-8"
    ) as file:
        data = json.load(file)
    data.update(
        analysis_mode="live_decision",
        game_end_reason="not_ended",
        skat_visibility="unknown",
        hand_game=True,
        ouvert=True,
        schneider_announced=True,
        schwarz_announced=True,
        matadors=1,
        bid_value=120,
        recommendation_method="bounded_search",
        bounded_search_settings=_settings(),
    )

    validate_position_input(data)


@pytest.mark.parametrize(
    "example_name",
    [
        "declarer_card_exposure_continuation.json",
        "defender_open_play_continuation.json",
    ],
)
def test_search_accepts_authorized_continuation_public_hands(example_name: str) -> None:
    with (PROJECT_ROOT / "examples" / example_name).open("r", encoding="utf-8") as file:
        data = json.load(file)
    data.update(
        recommendation_method="bounded_search",
        bounded_search_settings=_settings(),
    )

    validate_position_input(data)
