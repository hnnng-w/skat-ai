from types import MappingProxyType
from typing import Final

from skat_ai.bounded_search_result import RequestedSearchBudget
from skat_ai.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_BUDGET_VERSION,
    InformationSetSearchBudgetV1,
)

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


def convert_requested_search_budget_to_information_set_search_budget_v1(
    budget: RequestedSearchBudget,
) -> InformationSetSearchBudgetV1:
    """Applies the version-1 structural retrospective budget mapping."""
    if type(budget) is not RequestedSearchBudget:
        raise ValueError("budget must be a RequestedSearchBudget.")
    return InformationSetSearchBudgetV1(
        information_set_search_budget_version=INFORMATION_SET_SEARCH_BUDGET_VERSION,
        max_remaining_tricks=min(3, budget.max_remaining_tricks),
        max_depth_plies=min(9, budget.max_depth_plies),
        max_state_nodes=budget.max_nodes,
        max_information_sets=budget.max_nodes,
        max_selected_worlds=budget.max_selected_worlds,
        max_sampled_worlds=budget.max_sampled_worlds,
        minimum_comparable_worlds=budget.minimum_comparable_worlds,
        wall_clock_timeout_ms=budget.wall_clock_timeout_ms,
    )


def get_information_set_search_budget_profile(
    profile_identifier: str,
) -> InformationSetSearchBudgetV1:
    """Converts one existing named profile without adding or changing profiles."""
    return convert_requested_search_budget_to_information_set_search_budget_v1(
        get_search_budget_profile(profile_identifier)
    )
