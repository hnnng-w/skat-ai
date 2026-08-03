from types import MappingProxyType
from typing import Final

from skat_ai.bounded_search_result import RequestedSearchBudget

INTERACTIVE_SEARCH_BUDGET_PROFILE = "interactive_v1"
HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE = "historical_review_v1"
EVALUATION_SEARCH_BUDGET_PROFILE = "evaluation_v1"

SEARCH_BUDGET_PROFILE_IDENTIFIERS: Final[tuple[str, ...]] = (
    INTERACTIVE_SEARCH_BUDGET_PROFILE,
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    EVALUATION_SEARCH_BUDGET_PROFILE,
)

SEARCH_BUDGET_PROFILES = MappingProxyType(
    {
        INTERACTIVE_SEARCH_BUDGET_PROFILE: RequestedSearchBudget(
            max_remaining_tricks=3,
            max_depth_plies=9,
            max_nodes=500_000,
            max_selected_worlds=64,
            max_sampled_worlds=32,
            minimum_comparable_worlds=8,
            wall_clock_timeout_ms=1_000,
        ),
        HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE: RequestedSearchBudget(
            max_remaining_tricks=4,
            max_depth_plies=12,
            max_nodes=2_000_000,
            max_selected_worlds=128,
            max_sampled_worlds=64,
            minimum_comparable_worlds=16,
            wall_clock_timeout_ms=5_000,
        ),
        EVALUATION_SEARCH_BUDGET_PROFILE: RequestedSearchBudget(
            max_remaining_tricks=5,
            max_depth_plies=15,
            max_nodes=10_000_000,
            max_selected_worlds=512,
            max_sampled_worlds=256,
            minimum_comparable_worlds=32,
            wall_clock_timeout_ms=None,
        ),
    }
)


def get_search_budget_profile(profile_identifier: str) -> RequestedSearchBudget:
    """Returns the immutable budget for one versioned internal profile."""
    try:
        return SEARCH_BUDGET_PROFILES[profile_identifier]
    except KeyError as exc:
        raise ValueError(
            f"Unknown Search budget profile: {profile_identifier}"
        ) from exc
