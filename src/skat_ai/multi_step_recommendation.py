from dataclasses import dataclass

from skat_ai.bounded_search_result import BoundedSearchResult
from skat_ai.card_selection import SEARCH_AWARE_MULTI_STEP_POLICIES
from skat_ai.recommendation_workflow import (
    AUTO_METHOD,
    BOUNDED_SEARCH_METHOD,
    COMPATIBLE_WORLD_MINIMAX_METHOD,
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    NONE_EFFECTIVE_METHOD,
    RecommendationWorkflowResult,
)

LOCAL_POLICY_NO_RECOMMENDATION = "local_policy_no_recommendation"
MULTI_STEP_BOUNDED_SEARCH_DECISION_STREAM = (
    "multi_step_bounded_search_decision_v1"
)


@dataclass(frozen=True)
class MultiStepRecommendationDecision:
    """Privacy-safe routing result for one Search-aware local decision."""

    step_index: int
    requested_method: str
    effective_method: str
    search_attempted: bool
    recommendation_card: str | None
    recommendation_reason: str
    fallback_used: bool
    fallback_method: str | None
    bounded_search_result: BoundedSearchResult

    def __post_init__(self) -> None:
        if self.step_index < 0:
            raise ValueError("Recommendation decision step_index must not be negative.")
        if self.requested_method not in SEARCH_AWARE_MULTI_STEP_POLICIES:
            raise ValueError("Recommendation decision requires a Search-aware method.")
        if self.effective_method not in {
            COMPATIBLE_WORLD_MINIMAX_METHOD,
            IMMEDIATE_EXPECTED_VALUE_METHOD,
            NONE_EFFECTIVE_METHOD,
        }:
            raise ValueError("Recommendation decision has an invalid effective method.")
        if not self.search_attempted:
            raise ValueError("A Search-aware recommendation decision must attempt Search.")
        if self.effective_method == NONE_EFFECTIVE_METHOD:
            if self.recommendation_card is not None:
                raise ValueError("A stopped recommendation decision cannot contain a card.")
        elif self.recommendation_card is None:
            raise ValueError("An executed recommendation decision requires a card.")
        if self.requested_method == BOUNDED_SEARCH_METHOD and self.fallback_used:
            raise ValueError("Strict bounded Search cannot use fallback.")
        if self.fallback_used:
            if (
                self.requested_method != AUTO_METHOD
                or self.effective_method != IMMEDIATE_EXPECTED_VALUE_METHOD
                or self.fallback_method != IMMEDIATE_EXPECTED_VALUE_METHOD
            ):
                raise ValueError("Only auto may use Immediate fallback.")
        elif self.fallback_method is not None:
            raise ValueError("Unused fallback must have no fallback method.")
        if self.bounded_search_result.fallback_used != self.fallback_used:
            raise ValueError("Decision and Search fallback flags must match.")
        if self.bounded_search_result.fallback_method != self.fallback_method:
            raise ValueError("Decision and Search fallback methods must match.")
        if self.effective_method == COMPATIBLE_WORLD_MINIMAX_METHOD and (
            self.bounded_search_result.recommended_card != self.recommendation_card
        ):
            raise ValueError("Search decision card must match the Search result card.")
        if self.effective_method != COMPATIBLE_WORLD_MINIMAX_METHOD and (
            self.bounded_search_result.recommended_card is not None
        ):
            raise ValueError("A non-Search effective method requires no Search card.")


def build_multi_step_recommendation_decision(
    step_index: int,
    workflow: RecommendationWorkflowResult,
) -> MultiStepRecommendationDecision:
    """Narrows one workflow result to the stable Multi-Step decision contract."""
    if workflow.bounded_search_result is None:
        raise ValueError("Search-aware Multi-Step requires a bounded-search result.")
    return MultiStepRecommendationDecision(
        step_index=step_index,
        requested_method=workflow.requested_method,
        effective_method=workflow.effective_method,
        search_attempted=True,
        recommendation_card=workflow.recommendation_card,
        recommendation_reason=workflow.recommendation_reason,
        fallback_used=workflow.fallback_used,
        fallback_method=workflow.fallback_method,
        bounded_search_result=workflow.bounded_search_result,
    )


def build_compact_search_decision_diagnostic(
    decision: MultiStepRecommendationDecision,
) -> dict[str, str | int | bool | None]:
    """Builds ordered aggregate-only diagnostics for Policy Comparison."""
    search = decision.bounded_search_result
    consumed = search.consumed_budget
    return {
        "step_index": decision.step_index,
        "effective_method": decision.effective_method,
        "search_status": search.status,
        "search_stop_reason": search.stop_reason,
        "selected_world_count": consumed.selected_world_count,
        "completed_world_count": consumed.completed_world_count,
        "recommendation_card": decision.recommendation_card,
        "fallback_used": decision.fallback_used,
    }
