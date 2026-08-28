import json
from pathlib import Path

import main as main_module
from skatmind.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.rules import get_legal_cards
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_flat_search_review_runs_independent_immediate_and_treats_ties_as_equivalent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data = json.loads(
        (ROOT / "examples" / "grand_second_position.json").read_text(
            encoding="utf-8"
        )
    )
    data.update(
        analysis_mode="post_game_review",
        skat_visibility="unknown",
        game_end_reason="not_ended",
        right_hand_size=4,
        actual_card_played="S9",
        matadors=1,
        bid_value=24,
        recommendation_method="bounded_search",
        bounded_search_settings={
            "random_seed": 113,
            "max_remaining_tricks": 10,
            "max_depth_plies": 1,
            "max_nodes": 10,
            "max_selected_worlds": 1,
            "max_sampled_worlds": 1,
            "minimum_comparable_worlds": 1,
            "wall_clock_timeout_ms": None,
        },
    )
    input_path = tmp_path / "flat-search-review.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")
    calls = []

    def search(*, information_view, requested_budget, random_seed):
        calls.append(("search", random_seed))
        legal_cards = get_legal_cards(
            list(information_view.local_remaining_hand),
            [play.card for play in information_view.current_trick],
            information_view.game_type,
        )
        candidates = tuple(
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=1,
                local_contract_success_count=1,
                local_contract_success_rate=1.0,
                mean_local_side_game_score=24.0,
                mean_local_side_card_point_margin=10.0,
            )
            for card in legal_cards
        )
        ranked = rank_search_candidate_results(
            candidates, information_view.game_type, recommend=True
        )
        return BoundedSearchResult(
            schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
            analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
            search_method="compatible_world_minimax_v1",
            game_type=information_view.game_type,
            status="complete",
            stop_reason="completed",
            world_coverage="all_compatible_worlds",
            solution_claim="exact_per_selected_world",
            terminal_utility_version=TERMINAL_UTILITY_VERSION,
            requested_budget=requested_budget,
            consumed_budget=ConsumedSearchBudget(1, 1, 1, 1, 0, 0, 0),
            compatible_world_count=1,
            candidate_results=ranked,
            recommended_card=ranked[0].card,
            fallback_used=False,
            fallback_method=None,
        )

    def immediate(*, state, random_seed, **_kwargs):
        calls.append(("immediate", random_seed))
        legal_cards = get_legal_cards(state.hand, state.current_trick, state.game_type)
        values = {
            card: {
                "win_rate": 1.0 if card == "S10" else 0.0,
                "average_trick_points": 5.0 if card == "S10" else 0.0,
                "average_points_won": 5.0 if card == "S10" else 0.0,
                "average_points_lost": 0.0,
            }
            for card in legal_cards
        }
        return "S10", "Independent Immediate baseline.", values

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(main_module, "recommend_card_by_expected_value", immediate)

    result = main_module.build_analysis_result(str(input_path))

    assert calls == [("search", 113), ("immediate", 42)]
    assert result["recommendation"]["card"] == "SA"
    assert result["post_game_review_summary"]["recommended_card"] == "S10"
    comparison = result["bounded_search_post_game_review_summary"][
        "search_vs_immediate_comparison"
    ]
    assert comparison["is_available"] is True
    assert comparison["search_card"] == "SA"
    assert comparison["immediate_card"] == "S10"
    assert comparison["same_recommended_card"] is False
    assert comparison["search_aggregate_relation"] == "aggregate_equivalent"
    assert comparison["search_contract_success_rate_advantage"] == 0.0
    assert comparison["search_mean_game_score_advantage"] == 0.0
    assert comparison["search_mean_card_point_margin_advantage"] == 0.0
