from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from skat_ai.bounded_search_result import (
    AggregateSearchCandidateResult,
    rank_search_candidate_results,
)
from skat_ai.errors import SkatAIInvariantError
from skat_ai.information_set_search_contracts import (
    InformationSetSearchConsumedBudgetV1,
)
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
    InformationSetSearchSettings,
)
from skat_ai.recommendation_workflow import (
    NONE_ANALYSIS_REPORT_METHOD,
    NONE_EFFECTIVE_METHOD,
    RecommendationMethodConfiguration,
    build_serializable_information_set_search_settings,
)
from skat_ai.rules import get_legal_cards
from skat_ai.search_budget_profiles import (
    get_information_set_search_budget_profile,
)

if TYPE_CHECKING:
    from skat_ai.match_analysis_contracts import MatchDecisionAnalysisOptionsV1


MATCH_INFORMATION_SET_SEARCH_INTEGRATION_VERSION = 1

MATCH_INFORMATION_SET_SEARCH_SOURCE_POLICY = (
    "prepared_match_decision_through_existing_position_application"
)
MATCH_INFORMATION_SET_SEARCH_SETTINGS_POLICY = "existing_match_profile_to_information_set_budget"
MATCH_INFORMATION_SET_SEARCH_EXECUTION_POLICY = (
    "strict_information_set_search_once_without_fallback"
)
MATCH_INFORMATION_SET_SEARCH_COMPARISON_POLICY = (
    "same_selection_pimc_plus_independent_immediate_before_actual_card"
)
MATCH_INFORMATION_SET_SEARCH_PROFILE_POLICY = (
    "existing_effective_profile_policies_without_search_weighting"
)
MATCH_INFORMATION_SET_SEARCH_REPORT_POLICY = (
    "exact_revision_scoped_decision_report_with_safe_aggregate_result"
)
MATCH_INFORMATION_SET_SEARCH_BROWSER_POLICY = "explicit_user_execution_and_safe_diagnostics_only"


def build_match_information_set_search_settings_v1(
    options: MatchDecisionAnalysisOptionsV1,
) -> InformationSetSearchSettings:
    """Maps one existing Match profile to strict Information-set settings."""
    if options.recommendation_method != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        raise ValueError("Match options must request information_set_search.")
    if type(options.search_random_seed) is not int:
        raise ValueError("Information-set Search requires search_random_seed.")
    budget = get_information_set_search_budget_profile(options.search_budget_profile)
    return InformationSetSearchSettings(
        random_seed=options.search_random_seed,
        max_remaining_tricks=budget.max_remaining_tricks,
        max_depth_plies=budget.max_depth_plies,
        max_state_nodes=budget.max_state_nodes,
        max_information_sets=budget.max_information_sets,
        max_selected_worlds=budget.max_selected_worlds,
        max_sampled_worlds=budget.max_sampled_worlds,
        minimum_comparable_worlds=budget.minimum_comparable_worlds,
        wall_clock_timeout_ms=budget.wall_clock_timeout_ms,
    )


def build_match_information_set_search_request_fields_v1(
    options: MatchDecisionAnalysisOptionsV1,
) -> dict[str, object]:
    settings = build_match_information_set_search_settings_v1(options)
    configuration = RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method=INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
        information_set_search_settings=settings,
    )
    serialized = build_serializable_information_set_search_settings(configuration)
    if serialized is None:
        raise SkatAIInvariantError("Match Information-set Search settings were not serialized.")
    return {"information_set_search_settings": serialized}


def _require_mapping(
    document: Mapping[str, object],
    field_name: str,
) -> Mapping[str, object]:
    value = document.get(field_name)
    if not isinstance(value, Mapping):
        raise SkatAIInvariantError(f"Match Information-set Search Result requires {field_name}.")
    return value


def _require_sequence(
    value: object,
    field_name: str,
) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SkatAIInvariantError(f"Match Information-set Search {field_name} must be an array.")
    return value


def _require_mapping_value(
    value: object,
    field_name: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SkatAIInvariantError(f"Match Information-set Search {field_name} must be an object.")
    return value


def _serialized_requested_budget(
    settings: InformationSetSearchSettings,
) -> dict[str, int | None]:
    budget = settings.to_budget()
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


def _validate_safe_search_result(
    *,
    settings: InformationSetSearchSettings,
    request_document: Mapping[str, object],
    result_document: Mapping[str, object],
    search: Mapping[str, object],
    consumed: Mapping[str, object],
    candidates: Sequence[object],
) -> tuple[InformationSetSearchConsumedBudgetV1, tuple[AggregateSearchCandidateResult, ...]]:
    try:
        consumed_budget = InformationSetSearchConsumedBudgetV1(**dict(consumed))
        candidate_results = tuple(
            AggregateSearchCandidateResult(**dict(_require_mapping_value(candidate, "candidate")))
            for candidate in candidates
        )
    except (TypeError, ValueError) as error:
        raise SkatAIInvariantError(
            "Match Information-set Search aggregate Result is invalid."
        ) from error

    requested_budget = settings.to_budget()
    if (
        consumed_budget.depth_reached > requested_budget.max_depth_plies
        or consumed_budget.state_nodes_evaluated > requested_budget.max_state_nodes
        or consumed_budget.information_sets_evaluated > requested_budget.max_information_sets
        or consumed_budget.selected_world_count > requested_budget.max_selected_worlds
        or consumed_budget.sampled_world_count > requested_budget.max_sampled_worlds
    ):
        raise SkatAIInvariantError(
            "Match Information-set Search consumed more than its requested budget."
        )

    game_type = search.get("game_type")
    if game_type != request_document.get("game_type") or not isinstance(game_type, str):
        raise SkatAIInvariantError("Match Information-set Search changed the requested game type.")
    try:
        hand = list(_require_sequence(request_document.get("hand"), "request hand"))
        current_trick = list(
            _require_sequence(
                request_document.get("current_trick"),
                "request current_trick",
            )
        )
        expected_legal_cards = get_legal_cards(hand, current_trick, game_type)
    except (TypeError, ValueError) as error:
        raise SkatAIInvariantError(
            "Match Information-set Search could not rebuild legal Cards."
        ) from error
    legal_cards = list(_require_sequence(result_document.get("legal_cards"), "legal_cards"))
    if legal_cards != expected_legal_cards:
        raise SkatAIInvariantError("Match Information-set Search Result changed legal Cards.")

    status = search.get("status")
    coverage = search.get("world_coverage")
    compatible_world_count = search.get("compatible_world_count")
    if coverage == "none":
        if any(
            (
                consumed_budget.selected_world_count,
                consumed_budget.completed_world_count,
                consumed_budget.sampled_world_count,
                consumed_budget.unique_sampled_world_count,
            )
        ):
            raise SkatAIInvariantError(
                "Match Information-set Search no-coverage counts are inconsistent."
            )
    elif coverage == "all_compatible_worlds":
        if (
            type(compatible_world_count) is not int
            or compatible_world_count <= 0
            or consumed_budget.selected_world_count != compatible_world_count
            or consumed_budget.sampled_world_count != 0
            or consumed_budget.unique_sampled_world_count != 0
        ):
            raise SkatAIInvariantError(
                "Match Information-set Search all-world coverage is inconsistent."
            )
    elif coverage == "sampled_compatible_worlds":
        if (
            type(compatible_world_count) is not int
            or compatible_world_count <= 0
            or consumed_budget.selected_world_count == 0
            or consumed_budget.sampled_world_count != consumed_budget.selected_world_count
            or consumed_budget.unique_sampled_world_count > compatible_world_count
        ):
            raise SkatAIInvariantError(
                "Match Information-set Search sampled coverage is inconsistent."
            )
    else:
        raise SkatAIInvariantError("Match Information-set Search coverage is unsupported.")

    try:
        expected_candidates = rank_search_candidate_results(
            candidate_results,
            game_type,
            recommend=status == "complete",
        )
    except ValueError as error:
        raise SkatAIInvariantError(
            "Match Information-set Search Candidate ranking is invalid."
        ) from error
    if candidate_results != expected_candidates:
        raise SkatAIInvariantError(
            "Match Information-set Search Candidates changed deterministic ranking."
        )
    if any(
        candidate.completed_world_count != consumed_budget.completed_world_count
        for candidate in candidate_results
    ):
        raise SkatAIInvariantError(
            "Match Information-set Search Candidate denominators are inconsistent."
        )
    candidate_cards = {candidate.card for candidate in candidate_results}
    if not candidate_cards.issubset(set(expected_legal_cards)):
        raise SkatAIInvariantError(
            "Match Information-set Search contains an illegal Candidate Card."
        )
    recommended_card = search.get("recommended_card")
    controlled_policy_count = search.get("controlled_policy_decision_count")
    if controlled_policy_count != consumed_budget.controlled_policy_decisions:
        raise SkatAIInvariantError("Match Information-set Search controlled-Policy counts differ.")

    if status == "complete":
        if (
            consumed_budget.selected_world_count == 0
            or consumed_budget.completed_world_count != consumed_budget.selected_world_count
            or candidate_cards != set(expected_legal_cards)
            or recommended_card is None
            or controlled_policy_count == 0
        ):
            raise SkatAIInvariantError(
                "Match complete Information-set Search aggregates are inconsistent."
            )
    elif status == "partial":
        exhausted = {
            "depth_budget_exhausted": (
                consumed_budget.depth_reached,
                requested_budget.max_depth_plies,
            ),
            "state_node_budget_exhausted": (
                consumed_budget.state_nodes_evaluated,
                requested_budget.max_state_nodes,
            ),
            "information_set_budget_exhausted": (
                consumed_budget.information_sets_evaluated,
                requested_budget.max_information_sets,
            ),
        }
        stop_reason = search.get("stop_reason")
        if (
            stop_reason not in exhausted
            or exhausted[stop_reason][0] != exhausted[stop_reason][1]
            or consumed_budget.selected_world_count == 0
            or consumed_budget.completed_world_count != 0
            or candidate_results
            or recommended_card is not None
        ):
            raise SkatAIInvariantError(
                "Match partial Information-set Search aggregates are inconsistent."
            )
    elif status == "timeout":
        if (
            requested_budget.wall_clock_timeout_ms is None
            or consumed_budget.wall_clock_elapsed_ms < requested_budget.wall_clock_timeout_ms
            or consumed_budget.selected_world_count == 0
            or consumed_budget.completed_world_count != 0
            or candidate_results
            or recommended_card is not None
            or controlled_policy_count != 0
        ):
            raise SkatAIInvariantError(
                "Match timed-out Information-set Search aggregates are inconsistent."
            )
    elif status == "unavailable":
        if (
            any(consumed_budget.to_dict().values())
            or candidate_results
            or recommended_card is not None
            or controlled_policy_count != 0
            or (
                search.get("stop_reason") == "incompatible_world_space"
                and compatible_world_count != 0
            )
        ):
            raise SkatAIInvariantError(
                "Match unavailable Information-set Search aggregates are inconsistent."
            )
    else:
        raise SkatAIInvariantError("Match Information-set Search status is unsupported.")
    return consumed_budget, candidate_results


def _expected_same_card(
    left_card: object,
    right_card: object,
    *,
    available: bool,
) -> bool | None:
    if not available or left_card is None or right_card is None:
        return None
    return left_card == right_card


def _validate_comparison_semantics(
    *,
    request_document: Mapping[str, object],
    search: Mapping[str, object],
    comparison: Mapping[str, object],
    review: Mapping[str, object],
    consumed: InformationSetSearchConsumedBudgetV1,
    candidates: tuple[AggregateSearchCandidateResult, ...],
) -> None:
    information_status = search.get("status")
    pimc_status = comparison.get("pimc_status")
    same_selection = comparison.get("same_selected_world_sequence") is True
    information_complete = information_status == "complete"
    pimc_complete = pimc_status == "complete"
    same_selection_complete = information_complete and pimc_complete and same_selection
    information_card = search.get("recommended_card")
    pimc_card = comparison.get("pimc_recommended_card")
    immediate_card = review.get("recommended_card")
    actual_card = request_document.get("actual_card_played")
    if same_selection != (consumed.selected_world_count > 0) or (
        (pimc_status == "not_available") == same_selection
    ):
        raise SkatAIInvariantError(
            "Match Information-set Search comparison changed selection availability."
        )
    if pimc_complete and pimc_card is None:
        raise SkatAIInvariantError(
            "Match Information-set Search complete PIMC omitted its recommendation."
        )

    if information_status != "complete":
        unavailable_reason = "information_set_result_not_complete"
    elif pimc_status == "not_available":
        unavailable_reason = "pimc_result_not_available"
    elif pimc_status != "complete":
        unavailable_reason = "pimc_result_not_complete"
    elif not same_selection:
        unavailable_reason = "selected_world_sequence_not_shared"
    elif immediate_card is None:
        unavailable_reason = "immediate_recommendation_not_available"
    elif actual_card is None:
        unavailable_reason = "actual_card_not_provided"
    else:
        unavailable_reason = None
    if (
        comparison.get("comparison_status")
        != ("available" if unavailable_reason is None else "unavailable")
        or comparison.get("unavailable_reason") != unavailable_reason
        or comparison.get("selected_world_count") != consumed.selected_world_count
        or comparison.get("sampled_world_count") != consumed.sampled_world_count
        or comparison.get("information_set_status") != information_status
        or comparison.get("information_set_recommended_card") != information_card
        or comparison.get("immediate_recommended_card") != immediate_card
        or comparison.get("actual_card") != actual_card
    ):
        raise SkatAIInvariantError(
            "Match Information-set Search comparison changed retained stage values."
        )

    expected_agreements = {
        "information_set_pimc_same_card": _expected_same_card(
            information_card,
            pimc_card,
            available=same_selection_complete,
        ),
        "information_set_immediate_same_card": _expected_same_card(
            information_card,
            immediate_card,
            available=information_complete,
        ),
        "pimc_immediate_same_card": _expected_same_card(
            pimc_card,
            immediate_card,
            available=pimc_complete,
        ),
        "information_set_actual_same_card": _expected_same_card(
            information_card,
            actual_card,
            available=information_complete,
        ),
        "pimc_actual_same_card": _expected_same_card(
            pimc_card,
            actual_card,
            available=pimc_complete,
        ),
        "immediate_actual_same_card": _expected_same_card(
            immediate_card,
            actual_card,
            available=True,
        ),
    }
    if any(
        comparison.get(field_name) != expected
        for field_name, expected in expected_agreements.items()
    ):
        raise SkatAIInvariantError(
            "Match Information-set Search comparison agreement facts differ."
        )

    ranks = {candidate.card: candidate.rank for candidate in candidates}
    expected_information_ranks = {
        "information_set_rank_of_pimc_card": (
            ranks.get(pimc_card) if same_selection_complete else None
        ),
        "information_set_rank_of_actual_card": (
            ranks.get(actual_card) if information_complete else None
        ),
    }
    if any(
        comparison.get(field_name) != expected
        for field_name, expected in expected_information_ranks.items()
    ):
        raise SkatAIInvariantError("Match Information-set Search comparison ranks differ.")
    if (comparison.get("pimc_rank_of_information_set_card") is None) != (
        not same_selection_complete
    ) or (comparison.get("pimc_rank_of_actual_card") is None) != (not pimc_complete):
        raise SkatAIInvariantError(
            "Match Information-set Search PIMC comparison ranks are incomplete."
        )

    metric_fields = (
        ("information_set_minus_pimc_at_information_set_card", information_card),
        ("information_set_minus_pimc_at_pimc_card", pimc_card),
    )
    for field_name, expected_card in metric_fields:
        metric = comparison.get(field_name)
        if not same_selection_complete:
            if metric is not None:
                raise SkatAIInvariantError(
                    "Match Information-set Search comparison retained unavailable deltas."
                )
            continue
        metric_mapping = _require_mapping(comparison, field_name)
        denominator = metric_mapping.get("completed_world_count")
        success_count_delta = metric_mapping.get("local_contract_success_count_delta")
        success_rate_delta = metric_mapping.get("local_contract_success_rate_delta")
        expected_margin_absent = search.get("game_type") == "null"
        if (
            metric_mapping.get("card") != expected_card
            or denominator != consumed.completed_world_count
            or type(success_count_delta) is not int
            or not isinstance(success_rate_delta, (int, float))
            or not math.isclose(
                success_rate_delta,
                success_count_delta / denominator,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            or (metric_mapping.get("mean_local_side_card_point_margin_delta") is None)
            != expected_margin_absent
        ):
            raise SkatAIInvariantError(
                "Match Information-set Search comparison metric deltas are inconsistent."
            )


def reconcile_match_information_set_search_result_v1(
    *,
    options: MatchDecisionAnalysisOptionsV1,
    request_document: Mapping[str, object],
    result_document: Mapping[str, object],
) -> None:
    """Reconciles one schema-valid Match Result without re-executing analysis."""
    settings = build_match_information_set_search_settings_v1(options)
    request_fields = build_match_information_set_search_request_fields_v1(options)
    expected_settings = request_fields["information_set_search_settings"]
    if (
        request_document.get("recommendation_method")
        != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
        or request_document.get("information_set_search_settings") != expected_settings
        or "bounded_search_settings" in request_document
    ):
        raise SkatAIInvariantError(
            "Match Information-set Search Request changed its method or settings."
        )

    result_settings = _require_mapping(result_document, "settings")
    if (
        result_settings.get("recommendation_method") != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
        or result_settings.get("bounded_search_settings") is not None
        or result_settings.get("information_set_search_settings") != expected_settings
    ):
        raise SkatAIInvariantError(
            "Match Information-set Search Result changed its requested settings."
        )

    search = _require_mapping(result_document, "information_set_search_result")
    comparison = _require_mapping(
        result_document,
        "information_set_search_comparison",
    )
    summary = _require_mapping(result_document, "recommendation_method_summary")
    recommendation = _require_mapping(result_document, "recommendation")
    review = _require_mapping(result_document, "post_game_review_summary")
    consumed = _require_mapping(search, "consumed_budget")
    requested = _require_mapping(search, "requested_budget")
    candidates = _require_sequence(search.get("candidate_results"), "candidates")
    fixed_policies = _require_sequence(
        search.get("fixed_policy_settings"),
        "fixed_policy_settings",
    )
    if requested != _serialized_requested_budget(settings):
        raise SkatAIInvariantError(
            "Match Information-set Search Result changed its requested budget."
        )
    consumed_budget, candidate_results = _validate_safe_search_result(
        settings=settings,
        request_document=request_document,
        result_document=result_document,
        search=search,
        consumed=consumed,
        candidates=candidates,
    )

    expected_policies = []
    for side in ("left", "right"):
        policy = _require_mapping(
            result_document,
            f"{side}_opponent_policy_settings",
        )
        expected_policies.append(
            {
                "player": side,
                "lead_policy": policy.get("opponent_lead_policy"),
                "response_policy": policy.get("opponent_response_policy"),
            }
        )
    if list(fixed_policies) != expected_policies:
        raise SkatAIInvariantError("Match Information-set Search changed effective fixed Policies.")

    recommended_card = search.get("recommended_card")
    expected_effective_method = (
        INFORMATION_SET_SEARCH_EFFECTIVE_METHOD
        if recommended_card is not None
        else NONE_EFFECTIVE_METHOD
    )
    expected_summary = {
        "requested_method": INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
        "effective_method": expected_effective_method,
        "search_attempted": True,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": NONE_ANALYSIS_REPORT_METHOD,
    }
    if summary != expected_summary:
        raise SkatAIInvariantError("Match Information-set Search method summary is inconsistent.")
    if recommendation.get("card") != recommended_card:
        raise SkatAIInvariantError("Match Information-set Search recommendation Cards differ.")
    if sum(
        isinstance(candidate, Mapping)
        and candidate.get("is_recommended") is True
        and candidate.get("card") == recommended_card
        for candidate in candidates
    ) != (1 if recommended_card is not None else 0):
        raise SkatAIInvariantError(
            "Match Information-set Search Candidates changed the recommendation."
        )

    _validate_comparison_semantics(
        request_document=request_document,
        search=search,
        comparison=comparison,
        review=review,
        consumed=consumed_budget,
        candidates=candidate_results,
    )


def build_match_information_set_search_report_view_v1(
    result_document: Mapping[str, object],
) -> dict[str, Any] | None:
    """Projects only safe aggregate diagnostics for the local Match browser."""
    search = result_document.get("information_set_search_result")
    comparison = result_document.get("information_set_search_comparison")
    if search is None and comparison is None:
        return None
    if not isinstance(search, Mapping) or not isinstance(comparison, Mapping):
        raise SkatAIInvariantError("Match Information-set Search diagnostics are incomplete.")
    consumed = _require_mapping(search, "consumed_budget")
    return {
        "status": search.get("status"),
        "stop_reason": search.get("stop_reason"),
        "world_coverage": search.get("world_coverage"),
        "policy_claim": search.get("policy_claim"),
        "policy_consistency": search.get("policy_consistency"),
        "compatible_world_count": search.get("compatible_world_count"),
        "selected_world_count": consumed.get("selected_world_count"),
        "completed_world_count": consumed.get("completed_world_count"),
        "information_sets_evaluated": consumed.get("information_sets_evaluated"),
        "controlled_policy_decision_count": search.get("controlled_policy_decision_count"),
        "fixed_policy_decision_count": consumed.get("fixed_policy_decisions"),
        "information_set_recommended_card": comparison.get("information_set_recommended_card"),
        "pimc_recommended_card": comparison.get("pimc_recommended_card"),
        "immediate_recommended_card": comparison.get("immediate_recommended_card"),
        "actual_card": comparison.get("actual_card"),
        "information_set_pimc_same_card": comparison.get("information_set_pimc_same_card"),
        "information_set_immediate_same_card": comparison.get(
            "information_set_immediate_same_card"
        ),
        "information_set_actual_same_card": comparison.get("information_set_actual_same_card"),
    }
