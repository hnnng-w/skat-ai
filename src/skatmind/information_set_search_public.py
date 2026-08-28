from typing import Any

from skatmind.bounded_search_result import AggregateSearchCandidateResult
from skatmind.effective_opponent_policy import EffectiveOpponentPolicySettings
from skatmind.information_set_search_contracts import (
    BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
    INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
    InformationSetSearchBudgetV1,
    InformationSetSearchConsumedBudgetV1,
    InformationSetSearchPolicySettingsV1,
    InformationSetSearchResultV1,
)
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION

INFORMATION_SET_SEARCH_PUBLIC_RESULT_VERSION = 1
INFORMATION_SET_SEARCH_PUBLIC_RESULT_POLICY = (
    "safe_aggregate_result_without_private_policy_table"
)


def _serialize_requested_budget(
    budget: InformationSetSearchBudgetV1,
) -> dict[str, int | None]:
    return {
        "max_remaining_tricks": budget.max_remaining_tricks,
        "max_depth_plies": budget.max_depth_plies,
        "max_state_nodes": budget.max_state_nodes,
        "max_information_sets": budget.max_information_sets,
        "max_selected_worlds": budget.max_selected_worlds,
        "max_sampled_worlds": budget.max_sampled_worlds,
        "minimum_comparable_worlds": budget.minimum_comparable_worlds,
        "wall_clock_timeout_ms": budget.wall_clock_timeout_ms,
    }


def _serialize_consumed_budget(
    budget: InformationSetSearchConsumedBudgetV1,
) -> dict[str, int]:
    return {
        "depth_reached": budget.depth_reached,
        "state_nodes_evaluated": budget.state_nodes_evaluated,
        "information_sets_evaluated": budget.information_sets_evaluated,
        "controlled_policy_decisions": budget.controlled_policy_decisions,
        "fixed_policy_decisions": budget.fixed_policy_decisions,
        "selected_world_count": budget.selected_world_count,
        "completed_world_count": budget.completed_world_count,
        "sampled_world_count": budget.sampled_world_count,
        "unique_sampled_world_count": budget.unique_sampled_world_count,
        "wall_clock_elapsed_ms": budget.wall_clock_elapsed_ms,
    }


def _serialize_candidate(candidate: AggregateSearchCandidateResult) -> dict[str, Any]:
    return {
        "card": candidate.card,
        "rank": candidate.rank,
        "is_recommended": candidate.is_recommended,
        "completed_world_count": candidate.completed_world_count,
        "local_contract_success_count": candidate.local_contract_success_count,
        "local_contract_success_rate": candidate.local_contract_success_rate,
        "mean_local_side_game_score": candidate.mean_local_side_game_score,
        "mean_local_side_card_point_margin": candidate.mean_local_side_card_point_margin,
    }


def _serialize_fixed_policy_settings(
    settings: InformationSetSearchPolicySettingsV1,
) -> list[dict[str, str]]:
    return [
        {
            "player": item.player,
            "lead_policy": item.lead_policy,
            "response_policy": item.response_policy,
        }
        for item in settings.fixed_player_policies
    ]


def _serialize_effective_fixed_policy_settings(
    settings: EffectiveOpponentPolicySettings,
) -> list[dict[str, str]]:
    return [
        {
            "player": "left",
            "lead_policy": settings.left_lead_policy,
            "response_policy": settings.left_response_policy,
        },
        {
            "player": "right",
            "lead_policy": settings.right_lead_policy,
            "response_policy": settings.right_response_policy,
        },
    ]


def build_public_information_set_search_result_v1(
    result: InformationSetSearchResultV1,
) -> dict[str, Any]:
    """Projects one private Result without Worlds, Observations, or its Policy table."""
    if type(result) is not InformationSetSearchResultV1:
        raise ValueError("result must be an InformationSetSearchResultV1.")
    return {
        "schema_version": INFORMATION_SET_SEARCH_PUBLIC_RESULT_VERSION,
        "analysis_method": result.analysis_method,
        "search_method": result.search_method,
        "status": result.status,
        "stop_reason": result.stop_reason,
        "game_type": result.game_type,
        "world_coverage": result.world_coverage,
        "policy_claim": result.policy_claim,
        "policy_consistency": result.policy_consistency,
        "terminal_utility_version": result.terminal_utility_version,
        "requested_budget": _serialize_requested_budget(result.requested_budget),
        "consumed_budget": _serialize_consumed_budget(result.consumed_budget),
        "compatible_world_count": result.compatible_world_count,
        "candidate_results": [
            _serialize_candidate(candidate) for candidate in result.candidate_results
        ],
        "recommended_card": result.recommended_card,
        "controlled_policy_decision_count": len(result.controlled_policy),
        "fixed_policy_settings": _serialize_fixed_policy_settings(
            result.fixed_policy_settings
        ),
    }


def build_nondeterministic_fixed_policy_public_result_v1(
    *,
    game_type: str,
    requested_budget: InformationSetSearchBudgetV1,
    effective_policy_settings: EffectiveOpponentPolicySettings,
) -> dict[str, Any]:
    """Builds the canonical public unavailability without replacing random_legal."""
    if not isinstance(game_type, str) or not game_type:
        raise ValueError("game_type must be a non-empty string.")
    if type(requested_budget) is not InformationSetSearchBudgetV1:
        raise ValueError("requested_budget must be an InformationSetSearchBudgetV1.")
    if type(effective_policy_settings) is not EffectiveOpponentPolicySettings:
        raise ValueError(
            "effective_policy_settings must be EffectiveOpponentPolicySettings."
        )
    return {
        "schema_version": INFORMATION_SET_SEARCH_PUBLIC_RESULT_VERSION,
        "analysis_method": INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
        "search_method": BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        "status": "unavailable",
        "stop_reason": "nondeterministic_fixed_policy",
        "game_type": game_type,
        "world_coverage": "none",
        "policy_claim": "none",
        "policy_consistency": "not_assessed",
        "terminal_utility_version": TERMINAL_UTILITY_VERSION,
        "requested_budget": _serialize_requested_budget(requested_budget),
        "consumed_budget": {
            "depth_reached": 0,
            "state_nodes_evaluated": 0,
            "information_sets_evaluated": 0,
            "controlled_policy_decisions": 0,
            "fixed_policy_decisions": 0,
            "selected_world_count": 0,
            "completed_world_count": 0,
            "sampled_world_count": 0,
            "unique_sampled_world_count": 0,
            "wall_clock_elapsed_ms": 0,
        },
        "compatible_world_count": None,
        "candidate_results": [],
        "recommended_card": None,
        "controlled_policy_decision_count": 0,
        "fixed_policy_settings": _serialize_effective_fixed_policy_settings(
            effective_policy_settings
        ),
    }
