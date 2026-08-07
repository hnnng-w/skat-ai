from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from skat_ai.bounded_search_result import RequestedSearchBudget
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.multi_step_recommendation import MultiStepRecommendationDecision
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.strategic_metadata import StrategicMetadata


class DecisionProvenanceHook(Protocol):
    """Receives only public/local state immediately before local selection."""

    def __call__(
        self,
        *,
        state: GameState,
        left_hand_size: int,
        right_hand_size: int,
        public_hand_constraints: tuple[PublicHandConstraint, ...],
        strategic_metadata: StrategicMetadata,
        game_declaration: GameDeclaration,
        decision_index: int,
        selection_method: str,
        selection_settings: Mapping[str, object],
    ) -> None: ...


class RecommendationDecisionObserver(Protocol):
    """Receives one aggregate-only Search-aware decision after existing execution."""

    def __call__(
        self,
        policy: str,
        decision: MultiStepRecommendationDecision,
    ) -> None: ...


def build_safe_selection_settings(
    *,
    sample_count: int,
    use_basic_opponent_strategy: bool,
    opponent_response_policy_by_player: Mapping[str, str] | None,
    requested_search_budget: RequestedSearchBudget | None,
) -> dict[str, object]:
    """Builds effective selection settings without any random-stream identity."""
    search_budget = None
    if requested_search_budget is not None:
        search_budget = {
            "max_remaining_tricks": requested_search_budget.max_remaining_tricks,
            "max_depth_plies": requested_search_budget.max_depth_plies,
            "max_nodes": requested_search_budget.max_nodes,
            "max_selected_worlds": requested_search_budget.max_selected_worlds,
            "max_sampled_worlds": requested_search_budget.max_sampled_worlds,
            "minimum_comparable_worlds": (
                requested_search_budget.minimum_comparable_worlds
            ),
            "wall_clock_timeout_ms": requested_search_budget.wall_clock_timeout_ms,
        }
    response_policies = opponent_response_policy_by_player or {}
    return {
        "sample_count": sample_count,
        "use_basic_opponent_strategy": use_basic_opponent_strategy,
        "opponent_response_policy_by_player": {
            player: response_policies[player] for player in sorted(response_policies)
        },
        "bounded_search_budget": search_budget,
    }
