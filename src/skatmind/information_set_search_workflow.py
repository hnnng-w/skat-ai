from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skatmind.bounded_search_information import SearchInformationView
from skatmind.bounded_search_result import RequestedSearchBudget
from skatmind.effective_opponent_policy import EffectiveOpponentPolicySettings
from skatmind.information_set_search_contracts import (
    BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
    INFORMATION_SET_SEARCH_BUDGET_VERSION,
    INFORMATION_SET_SEARCH_CONTROL_SCOPES,
    INFORMATION_SET_SEARCH_FIXED_POLICY_TIE_POLICY,
    INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
    InformationSetFixedPlayerPolicyV1,
    InformationSetSearchBudgetV1,
    InformationSetSearchPolicySettingsV1,
    InformationSetSearchRequestV1,
    InformationSetSearchResultV1,
    build_information_set_search_request_v1,
)
from skatmind.information_set_search_executor import execute_information_set_search_v1
from skatmind.information_set_search_preparation import (
    InformationSetSearchPreparationV1,
    prepare_information_set_search_v1,
)
from skatmind.information_set_search_public import (
    build_nondeterministic_fixed_policy_public_result_v1,
    build_public_information_set_search_result_v1,
)

INFORMATION_SET_SEARCH_ROUTING_VERSION = 1
INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD = "information_set_search"
INFORMATION_SET_SEARCH_EFFECTIVE_METHOD = BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD

INFORMATION_SET_SEARCH_ROUTING_POLICY = (
    "strict_information_set_search_without_fallback"
)
INFORMATION_SET_SEARCH_FIXED_POLICY_SOURCE_POLICY = (
    "existing_effective_left_right_policy_settings"
)
INFORMATION_SET_SEARCH_BASELINE_POLICY = (
    "same_selected_world_pimc_plus_independent_immediate"
)
INFORMATION_SET_SEARCH_ACTUAL_CARD_POLICY = (
    "attach_actual_card_only_after_decision_time_analysis"
)
INFORMATION_SET_SEARCH_COMPATIBILITY_POLICY = (
    "existing_immediate_bounded_search_and_auto_unchanged"
)

INFORMATION_SET_SEARCH_SETTING_KEYS = (
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


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchSettings:
    random_seed: int
    max_remaining_tricks: int
    max_depth_plies: int
    max_state_nodes: int
    max_information_sets: int
    max_selected_worlds: int
    max_sampled_worlds: int
    minimum_comparable_worlds: int
    wall_clock_timeout_ms: int | None

    def __post_init__(self) -> None:
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise ValueError("random_seed must be an integer and must not be a boolean.")
        self.to_budget()

    def to_budget(self) -> InformationSetSearchBudgetV1:
        return InformationSetSearchBudgetV1(
            information_set_search_budget_version=INFORMATION_SET_SEARCH_BUDGET_VERSION,
            max_remaining_tricks=self.max_remaining_tricks,
            max_depth_plies=self.max_depth_plies,
            max_state_nodes=self.max_state_nodes,
            max_information_sets=self.max_information_sets,
            max_selected_worlds=self.max_selected_worlds,
            max_sampled_worlds=self.max_sampled_worlds,
            minimum_comparable_worlds=self.minimum_comparable_worlds,
            wall_clock_timeout_ms=self.wall_clock_timeout_ms,
        )


def convert_information_set_search_budget_to_requested_search_budget_v1(
    budget: InformationSetSearchBudgetV1,
) -> RequestedSearchBudget:
    """Converts structural limits for same-selection compatible-world PIMC."""
    if type(budget) is not InformationSetSearchBudgetV1:
        raise ValueError("budget must be an InformationSetSearchBudgetV1.")
    return RequestedSearchBudget(
        max_remaining_tricks=budget.max_remaining_tricks,
        max_depth_plies=budget.max_depth_plies,
        max_nodes=budget.max_state_nodes,
        max_selected_worlds=budget.max_selected_worlds,
        max_sampled_worlds=budget.max_sampled_worlds,
        minimum_comparable_worlds=budget.minimum_comparable_worlds,
        wall_clock_timeout_ms=budget.wall_clock_timeout_ms,
    )


def build_information_set_search_policy_settings_v1(
    effective_settings: EffectiveOpponentPolicySettings,
) -> InformationSetSearchPolicySettingsV1 | None:
    """Maps only effective policy names; random_legal remains unavailable."""
    if type(effective_settings) is not EffectiveOpponentPolicySettings:
        raise ValueError("effective_settings must be EffectiveOpponentPolicySettings.")
    policy_names = (
        effective_settings.left_lead_policy,
        effective_settings.left_response_policy,
        effective_settings.right_lead_policy,
        effective_settings.right_response_policy,
    )
    if "random_legal" in policy_names:
        return None
    return InformationSetSearchPolicySettingsV1(
        information_set_search_policy_settings_version=(
            INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION
        ),
        controlled_player="me",
        control_scope=INFORMATION_SET_SEARCH_CONTROL_SCOPES[0],
        fixed_player_policies=(
            InformationSetFixedPlayerPolicyV1(
                player="left",
                lead_policy=effective_settings.left_lead_policy,
                response_policy=effective_settings.left_response_policy,
                tie_policy=INFORMATION_SET_SEARCH_FIXED_POLICY_TIE_POLICY,
            ),
            InformationSetFixedPlayerPolicyV1(
                player="right",
                lead_policy=effective_settings.right_lead_policy,
                response_policy=effective_settings.right_response_policy,
                tie_policy=INFORMATION_SET_SEARCH_FIXED_POLICY_TIE_POLICY,
            ),
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchWorkflowResultV1:
    routing_version: int
    request: InformationSetSearchRequestV1 | None
    preparation: InformationSetSearchPreparationV1 | None
    result: InformationSetSearchResultV1 | None
    public_result: dict[str, Any]

    def __post_init__(self) -> None:
        if (
            isinstance(self.routing_version, bool)
            or not isinstance(self.routing_version, int)
            or self.routing_version != INFORMATION_SET_SEARCH_ROUTING_VERSION
        ):
            raise ValueError("Unsupported information-set Search routing version.")
        if not isinstance(self.public_result, dict):
            raise ValueError("public_result must be a mutable dictionary.")


def execute_live_information_set_search_workflow_v1(
    *,
    information_view: SearchInformationView,
    settings: InformationSetSearchSettings,
    effective_policy_settings: EffectiveOpponentPolicySettings,
    request_builder: Callable[..., InformationSetSearchRequestV1] = (
        build_information_set_search_request_v1
    ),
    preparation_builder: Callable[
        [InformationSetSearchRequestV1], InformationSetSearchPreparationV1
    ] = prepare_information_set_search_v1,
    executor: Callable[
        [InformationSetSearchPreparationV1], InformationSetSearchResultV1
    ] = execute_information_set_search_v1,
) -> InformationSetSearchWorkflowResultV1:
    """Runs one strict flat Information-set Search without baselines or fallback."""
    if type(information_view) is not SearchInformationView:
        raise ValueError("information_view must be a SearchInformationView.")
    if type(settings) is not InformationSetSearchSettings:
        raise ValueError("settings must be InformationSetSearchSettings.")
    policy_settings = build_information_set_search_policy_settings_v1(
        effective_policy_settings
    )
    requested_budget = settings.to_budget()
    if policy_settings is None:
        return InformationSetSearchWorkflowResultV1(
            routing_version=INFORMATION_SET_SEARCH_ROUTING_VERSION,
            request=None,
            preparation=None,
            result=None,
            public_result=build_nondeterministic_fixed_policy_public_result_v1(
                game_type=information_view.game_type,
                requested_budget=requested_budget,
                effective_policy_settings=effective_policy_settings,
            ),
        )

    request = request_builder(
        information_view=information_view,
        requested_budget=requested_budget,
        world_selection_seed=settings.random_seed,
        policy_settings=policy_settings,
    )
    preparation = preparation_builder(request)
    result = executor(preparation)
    return InformationSetSearchWorkflowResultV1(
        routing_version=INFORMATION_SET_SEARCH_ROUTING_VERSION,
        request=request,
        preparation=preparation,
        result=result,
        public_result=build_public_information_set_search_result_v1(result),
    )
