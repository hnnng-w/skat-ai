from dataclasses import FrozenInstanceError, fields

import pytest

from skat_ai.bounded_search_result import RequestedSearchBudget
from skat_ai.search_budget_profiles import (
    SEARCH_BUDGET_PROFILE_IDENTIFIERS,
    SEARCH_BUDGET_PROFILES,
    get_search_budget_profile,
)


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("interactive_v1", (3, 9, 500_000, 64, 32, 8, 1_000)),
        ("historical_review_v1", (4, 12, 2_000_000, 128, 64, 16, 5_000)),
        ("evaluation_v1", (5, 15, 10_000_000, 512, 256, 32, None)),
    ],
)
def test_search_budget_profiles_have_exact_versioned_values(
    identifier: str,
    expected: tuple[int, int, int, int, int, int, int | None],
) -> None:
    budget = get_search_budget_profile(identifier)

    assert isinstance(budget, RequestedSearchBudget)
    assert tuple(getattr(budget, field.name) for field in fields(budget)) == expected
    assert get_search_budget_profile(identifier) is budget
    assert not hasattr(budget, "random_seed")


def test_search_budget_profiles_and_budgets_are_immutable() -> None:
    assert tuple(SEARCH_BUDGET_PROFILES) == SEARCH_BUDGET_PROFILE_IDENTIFIERS

    with pytest.raises(TypeError):
        SEARCH_BUDGET_PROFILES["interactive_v1"] = get_search_budget_profile(
            "evaluation_v1"
        )
    with pytest.raises(FrozenInstanceError):
        get_search_budget_profile("interactive_v1").max_nodes = 1  # type: ignore[misc]


def test_unknown_search_budget_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown Search budget profile: future_v2"):
        get_search_budget_profile("future_v2")
