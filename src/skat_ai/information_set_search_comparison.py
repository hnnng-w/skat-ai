from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from skat_ai.bounded_search_result import (
    AggregateSearchCandidateResult,
    BoundedSearchResult,
)
from skat_ai.deck import get_full_deck
from skat_ai.information_set_search_contracts import InformationSetSearchResultV1
from skat_ai.information_set_search_public import (
    build_public_information_set_search_result_v1,
)

INFORMATION_SET_SEARCH_COMPARISON_VERSION = 1
INFORMATION_SET_SEARCH_COMPARISON_METHOD = (
    "information_set_vs_same_selection_pimc_and_immediate_v1"
)

INFORMATION_SET_SEARCH_BASELINE_POLICY = (
    "same_selected_world_pimc_plus_independent_immediate"
)
INFORMATION_SET_SEARCH_ACTUAL_CARD_POLICY = (
    "attach_actual_card_only_after_decision_time_analysis"
)
INFORMATION_SET_SEARCH_COMPARISON_POLICY = (
    "descriptive_method_comparison_without_accuracy_or_truth_claim"
)
INFORMATION_SET_SEARCH_PROVENANCE_POLICY = (
    "retained_stage_values_without_execution_rerun"
)
INFORMATION_SET_SEARCH_STRATEGY_FUSION_MITIGATION_SCOPE = (
    "controlled_player_over_selected_world_sequence"
)

COMPARISON_STATUSES = ("available", "unavailable")
METHOD_NOT_AVAILABLE = "not_available"


@dataclass(frozen=True, slots=True, kw_only=True)
class SameDenominatorSearchMetricDeltasV1:
    """Information-set minus PIMC metrics for one Card and denominator."""

    card: str
    completed_world_count: int
    local_contract_success_count_delta: int
    local_contract_success_rate_delta: float
    mean_local_side_game_score_delta: float
    mean_local_side_card_point_margin_delta: float | None

    def __post_init__(self) -> None:
        if self.card not in get_full_deck():
            raise ValueError("Metric deltas require a valid Card.")
        if (
            isinstance(self.completed_world_count, bool)
            or not isinstance(self.completed_world_count, int)
            or self.completed_world_count <= 0
        ):
            raise ValueError("Metric deltas require a positive denominator.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchComparisonPreActualAnalysisV1:
    """Retained decision-time analyses that structurally exclude the actual Card."""

    information_set_result: InformationSetSearchResultV1 | None
    pimc_result: BoundedSearchResult | None
    immediate_recommended_card: str | None
    same_selected_world_sequence: bool
    information_set_public_result: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.information_set_result is not None and not isinstance(
            self.information_set_result,
            InformationSetSearchResultV1,
        ):
            raise ValueError(
                "information_set_result must be an InformationSetSearchResultV1 or null."
            )
        if self.pimc_result is not None and not isinstance(
            self.pimc_result,
            BoundedSearchResult,
        ):
            raise ValueError("pimc_result must be a BoundedSearchResult or null.")
        expected_public_result = (
            build_public_information_set_search_result_v1(
                self.information_set_result
            )
            if self.information_set_result is not None
            else None
        )
        if self.information_set_public_result is None:
            if expected_public_result is not None:
                object.__setattr__(
                    self,
                    "information_set_public_result",
                    expected_public_result,
                )
        elif not isinstance(self.information_set_public_result, Mapping):
            raise ValueError("information_set_public_result must be a mapping or null.")
        elif expected_public_result is not None and dict(
            self.information_set_public_result
        ) != expected_public_result:
            raise ValueError("Private and public Information-set Results must match.")
        if not isinstance(self.same_selected_world_sequence, bool):
            raise ValueError("same_selected_world_sequence must be a boolean.")
        if self.immediate_recommended_card is not None and (
            self.immediate_recommended_card not in get_full_deck()
        ):
            raise ValueError("immediate_recommended_card must be a valid Card or null.")
        if (
            self.information_set_result is not None
            and self.pimc_result is not None
        ):
            if self.information_set_result.game_type != self.pimc_result.game_type:
                raise ValueError("Information-set and PIMC game types must match.")
            information_consumed = self.information_set_result.consumed_budget
            pimc_consumed = self.pimc_result.consumed_budget
            if self.same_selected_world_sequence and (
                information_consumed.selected_world_count
                != pimc_consumed.selected_world_count
                or information_consumed.sampled_world_count
                != pimc_consumed.sampled_world_count
                or information_consumed.unique_sampled_world_count
                != pimc_consumed.unique_sampled_world_count
                or self.information_set_result.compatible_world_count
                != self.pimc_result.compatible_world_count
            ):
                raise ValueError(
                    "The same selected World sequence requires equal selection counts."
                )
            if (
                self.same_selected_world_sequence
                and self.information_set_result.status == "complete"
                and self.pimc_result.status == "complete"
                and {
                    candidate.card
                    for candidate in self.information_set_result.candidate_results
                }
                != {candidate.card for candidate in self.pimc_result.candidate_results}
            ):
                raise ValueError(
                    "The same selected World sequence requires equal root Cards."
                )

    @property
    def selected_world_count(self) -> int:
        if self.information_set_result is not None:
            return self.information_set_result.consumed_budget.selected_world_count
        if self.pimc_result is not None:
            return self.pimc_result.consumed_budget.selected_world_count
        if self.information_set_public_result is not None:
            consumed = self.information_set_public_result.get("consumed_budget")
            if isinstance(consumed, Mapping):
                value = consumed.get("selected_world_count")
                if type(value) is int:
                    return value
        return 0

    @property
    def sampled_world_count(self) -> int:
        if self.information_set_result is not None:
            return self.information_set_result.consumed_budget.sampled_world_count
        if self.pimc_result is not None:
            return self.pimc_result.consumed_budget.sampled_world_count
        if self.information_set_public_result is not None:
            consumed = self.information_set_public_result.get("consumed_budget")
            if isinstance(consumed, Mapping):
                value = consumed.get("sampled_world_count")
                if type(value) is int:
                    return value
        return 0


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchComparisonV1:
    schema_version: int
    comparison_method: str
    comparison_status: str
    unavailable_reason: str | None
    same_selected_world_sequence: bool
    selected_world_count: int
    sampled_world_count: int
    information_set_status: str
    pimc_status: str
    information_set_recommended_card: str | None
    pimc_recommended_card: str | None
    immediate_recommended_card: str | None
    actual_card: str | None
    information_set_pimc_same_card: bool | None
    information_set_immediate_same_card: bool | None
    pimc_immediate_same_card: bool | None
    information_set_actual_same_card: bool | None
    pimc_actual_same_card: bool | None
    immediate_actual_same_card: bool | None
    information_set_rank_of_pimc_card: int | None
    pimc_rank_of_information_set_card: int | None
    information_set_rank_of_actual_card: int | None
    pimc_rank_of_actual_card: int | None
    information_set_minus_pimc_at_information_set_card: (
        SameDenominatorSearchMetricDeltasV1 | None
    )
    information_set_minus_pimc_at_pimc_card: (
        SameDenominatorSearchMetricDeltasV1 | None
    )
    strategy_fusion_mitigation_scope: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != INFORMATION_SET_SEARCH_COMPARISON_VERSION
        ):
            raise ValueError("Unsupported information-set Search comparison version.")
        if self.comparison_method != INFORMATION_SET_SEARCH_COMPARISON_METHOD:
            raise ValueError("Unsupported information-set Search comparison method.")
        if self.comparison_status not in COMPARISON_STATUSES:
            raise ValueError("Unsupported information-set Search comparison status.")
        if not isinstance(self.same_selected_world_sequence, bool):
            raise ValueError("same_selected_world_sequence must be a boolean.")
        for field_name in ("selected_world_count", "sampled_world_count"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.sampled_world_count > self.selected_world_count:
            raise ValueError("sampled_world_count cannot exceed selected_world_count.")
        if (self.comparison_status == "available") != (
            self.unavailable_reason is None
        ):
            raise ValueError("Comparison status and unavailable reason must agree.")
        for field_name in (
            "information_set_recommended_card",
            "pimc_recommended_card",
            "immediate_recommended_card",
            "actual_card",
        ):
            card = getattr(self, field_name)
            if card is not None and card not in get_full_deck():
                raise ValueError(f"{field_name} must be a valid Card or null.")
        for field_name in (
            "information_set_pimc_same_card",
            "information_set_immediate_same_card",
            "pimc_immediate_same_card",
            "information_set_actual_same_card",
            "pimc_actual_same_card",
            "immediate_actual_same_card",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{field_name} must be a boolean or null.")
        for field_name in (
            "information_set_rank_of_pimc_card",
            "pimc_rank_of_information_set_card",
            "information_set_rank_of_actual_card",
            "pimc_rank_of_actual_card",
        ):
            rank = getattr(self, field_name)
            if rank is not None and (
                isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0
            ):
                raise ValueError(f"{field_name} must be a positive integer or null.")
        if self.strategy_fusion_mitigation_scope != (
            INFORMATION_SET_SEARCH_STRATEGY_FUSION_MITIGATION_SCOPE
        ):
            raise ValueError("Unsupported strategy-fusion mitigation scope.")


def build_information_set_search_comparison_pre_actual_analysis_v1(
    *,
    information_set_result: InformationSetSearchResultV1 | None,
    pimc_result: BoundedSearchResult | None,
    immediate_recommended_card: str | None,
    same_selected_world_sequence: bool,
    information_set_public_result: Mapping[str, Any] | None = None,
) -> InformationSetSearchComparisonPreActualAnalysisV1:
    """Captures all method outputs before an observed Card can be attached."""
    return InformationSetSearchComparisonPreActualAnalysisV1(
        information_set_result=information_set_result,
        pimc_result=pimc_result,
        immediate_recommended_card=immediate_recommended_card,
        same_selected_world_sequence=same_selected_world_sequence,
        information_set_public_result=information_set_public_result,
    )


def _candidate_by_card(
    candidates: tuple[AggregateSearchCandidateResult, ...],
) -> dict[str, AggregateSearchCandidateResult]:
    return {candidate.card: candidate for candidate in candidates}


def _rank_of(
    candidates: tuple[AggregateSearchCandidateResult, ...],
    card: str | None,
) -> int | None:
    if card is None:
        return None
    candidate = _candidate_by_card(candidates).get(card)
    return candidate.rank if candidate is not None else None


def _same_denominator_deltas(
    *,
    card: str | None,
    information_set_result: InformationSetSearchResultV1,
    pimc_result: BoundedSearchResult,
) -> SameDenominatorSearchMetricDeltasV1 | None:
    if card is None:
        return None
    information_candidate = _candidate_by_card(
        information_set_result.candidate_results
    ).get(card)
    pimc_candidate = _candidate_by_card(pimc_result.candidate_results).get(card)
    if information_candidate is None or pimc_candidate is None:
        return None
    denominator = information_candidate.completed_world_count
    if denominator <= 0 or denominator != pimc_candidate.completed_world_count:
        return None
    if (
        information_candidate.local_contract_success_rate is None
        or pimc_candidate.local_contract_success_rate is None
        or information_candidate.mean_local_side_game_score is None
        or pimc_candidate.mean_local_side_game_score is None
    ):
        return None
    information_margin = information_candidate.mean_local_side_card_point_margin
    pimc_margin = pimc_candidate.mean_local_side_card_point_margin
    margin_delta = None
    if information_set_result.game_type != "null":
        if information_margin is None or pimc_margin is None:
            return None
        margin_delta = information_margin - pimc_margin
    return SameDenominatorSearchMetricDeltasV1(
        card=card,
        completed_world_count=denominator,
        local_contract_success_count_delta=(
            information_candidate.local_contract_success_count
            - pimc_candidate.local_contract_success_count
        ),
        local_contract_success_rate_delta=(
            information_candidate.local_contract_success_rate
            - pimc_candidate.local_contract_success_rate
        ),
        mean_local_side_game_score_delta=(
            information_candidate.mean_local_side_game_score
            - pimc_candidate.mean_local_side_game_score
        ),
        mean_local_side_card_point_margin_delta=margin_delta,
    )


def _comparison_unavailable_reason(
    analysis: InformationSetSearchComparisonPreActualAnalysisV1,
    actual_card: str | None,
) -> str | None:
    information_result = analysis.information_set_result
    public_result = analysis.information_set_public_result
    pimc_result = analysis.pimc_result
    if information_result is None and public_result is None:
        return "information_set_result_not_available"
    information_status = (
        information_result.status
        if information_result is not None
        else public_result.get("status")
    )
    if information_status != "complete":
        return "information_set_result_not_complete"
    if pimc_result is None:
        return "pimc_result_not_available"
    if pimc_result.status != "complete":
        return "pimc_result_not_complete"
    if not analysis.same_selected_world_sequence:
        return "selected_world_sequence_not_shared"
    if analysis.immediate_recommended_card is None:
        return "immediate_recommendation_not_available"
    if actual_card is None:
        return "actual_card_not_provided"
    return None


def attach_actual_card_to_information_set_search_comparison_v1(
    analysis: InformationSetSearchComparisonPreActualAnalysisV1,
    actual_card: str | None,
) -> InformationSetSearchComparisonV1:
    """Attaches the observed Card after every decision-time method has completed."""
    if not isinstance(
        analysis,
        InformationSetSearchComparisonPreActualAnalysisV1,
    ):
        raise ValueError("analysis must be a pre-actual comparison analysis.")
    if actual_card is not None and actual_card not in get_full_deck():
        raise ValueError("actual_card must be a valid Card or null.")

    information_result = analysis.information_set_result
    public_result = analysis.information_set_public_result
    pimc_result = analysis.pimc_result
    information_status = (
        information_result.status
        if information_result is not None
        else (
            public_result.get("status")
            if public_result is not None
            else METHOD_NOT_AVAILABLE
        )
    )
    information_complete = information_status == "complete"
    pimc_complete = pimc_result is not None and pimc_result.status == "complete"
    information_card = (
        information_result.recommended_card
        if information_result is not None
        else (
            public_result.get("recommended_card")
            if public_result is not None
            else None
        )
    )
    pimc_card = pimc_result.recommended_card if pimc_result is not None else None
    immediate_card = analysis.immediate_recommended_card
    reason = _comparison_unavailable_reason(analysis, actual_card)

    information_candidates = (
        information_result.candidate_results
        if information_result is not None and information_complete
        else ()
    )
    pimc_candidates = (
        pimc_result.candidate_results
        if pimc_result is not None and pimc_complete
        else ()
    )
    same_selection_complete = (
        information_complete
        and pimc_complete
        and analysis.same_selected_world_sequence
    )
    return InformationSetSearchComparisonV1(
        schema_version=INFORMATION_SET_SEARCH_COMPARISON_VERSION,
        comparison_method=INFORMATION_SET_SEARCH_COMPARISON_METHOD,
        comparison_status="available" if reason is None else "unavailable",
        unavailable_reason=reason,
        same_selected_world_sequence=analysis.same_selected_world_sequence,
        selected_world_count=analysis.selected_world_count,
        sampled_world_count=analysis.sampled_world_count,
        information_set_status=information_status,
        pimc_status=pimc_result.status if pimc_result is not None else METHOD_NOT_AVAILABLE,
        information_set_recommended_card=information_card,
        pimc_recommended_card=pimc_card,
        immediate_recommended_card=immediate_card,
        actual_card=actual_card,
        information_set_pimc_same_card=(
            information_card == pimc_card
            if same_selection_complete
            and information_card is not None
            and pimc_card is not None
            else None
        ),
        information_set_immediate_same_card=(
            information_card == immediate_card
            if information_complete
            and information_card is not None
            and immediate_card is not None
            else None
        ),
        pimc_immediate_same_card=(
            pimc_card == immediate_card
            if pimc_complete and pimc_card is not None and immediate_card is not None
            else None
        ),
        information_set_actual_same_card=(
            information_card == actual_card
            if information_complete
            and information_card is not None
            and actual_card is not None
            else None
        ),
        pimc_actual_same_card=(
            pimc_card == actual_card
            if pimc_complete and pimc_card is not None and actual_card is not None
            else None
        ),
        immediate_actual_same_card=(
            immediate_card == actual_card
            if immediate_card is not None and actual_card is not None
            else None
        ),
        information_set_rank_of_pimc_card=(
            _rank_of(information_candidates, pimc_card)
            if same_selection_complete
            else None
        ),
        pimc_rank_of_information_set_card=(
            _rank_of(pimc_candidates, information_card)
            if same_selection_complete
            else None
        ),
        information_set_rank_of_actual_card=(
            _rank_of(information_candidates, actual_card)
            if information_complete
            else None
        ),
        pimc_rank_of_actual_card=(
            _rank_of(pimc_candidates, actual_card) if pimc_complete else None
        ),
        information_set_minus_pimc_at_information_set_card=(
            _same_denominator_deltas(
                card=information_card,
                information_set_result=information_result,
                pimc_result=pimc_result,
            )
            if same_selection_complete
            and information_result is not None
            and pimc_result is not None
            else None
        ),
        information_set_minus_pimc_at_pimc_card=(
            _same_denominator_deltas(
                card=pimc_card,
                information_set_result=information_result,
                pimc_result=pimc_result,
            )
            if same_selection_complete
            and information_result is not None
            and pimc_result is not None
            else None
        ),
        strategy_fusion_mitigation_scope=(
            INFORMATION_SET_SEARCH_STRATEGY_FUSION_MITIGATION_SCOPE
        ),
    )


def _serialize_metric_deltas(
    value: SameDenominatorSearchMetricDeltasV1 | None,
) -> dict[str, int | float | str | None] | None:
    if value is None:
        return None
    return {
        "card": value.card,
        "completed_world_count": value.completed_world_count,
        "local_contract_success_count_delta": (
            value.local_contract_success_count_delta
        ),
        "local_contract_success_rate_delta": (
            value.local_contract_success_rate_delta
        ),
        "mean_local_side_game_score_delta": (
            value.mean_local_side_game_score_delta
        ),
        "mean_local_side_card_point_margin_delta": (
            value.mean_local_side_card_point_margin_delta
        ),
    }


def build_serializable_information_set_search_comparison_v1(
    comparison: InformationSetSearchComparisonV1,
) -> dict[str, Any]:
    """Builds deterministic descriptive output without truth or accuracy fields."""
    if not isinstance(comparison, InformationSetSearchComparisonV1):
        raise ValueError("comparison must be InformationSetSearchComparisonV1.")
    return {
        "schema_version": comparison.schema_version,
        "comparison_method": comparison.comparison_method,
        "comparison_status": comparison.comparison_status,
        "unavailable_reason": comparison.unavailable_reason,
        "same_selected_world_sequence": comparison.same_selected_world_sequence,
        "selected_world_count": comparison.selected_world_count,
        "sampled_world_count": comparison.sampled_world_count,
        "information_set_status": comparison.information_set_status,
        "pimc_status": comparison.pimc_status,
        "information_set_recommended_card": (
            comparison.information_set_recommended_card
        ),
        "pimc_recommended_card": comparison.pimc_recommended_card,
        "immediate_recommended_card": comparison.immediate_recommended_card,
        "actual_card": comparison.actual_card,
        "information_set_pimc_same_card": (
            comparison.information_set_pimc_same_card
        ),
        "information_set_immediate_same_card": (
            comparison.information_set_immediate_same_card
        ),
        "pimc_immediate_same_card": comparison.pimc_immediate_same_card,
        "information_set_actual_same_card": (
            comparison.information_set_actual_same_card
        ),
        "pimc_actual_same_card": comparison.pimc_actual_same_card,
        "immediate_actual_same_card": comparison.immediate_actual_same_card,
        "information_set_rank_of_pimc_card": (
            comparison.information_set_rank_of_pimc_card
        ),
        "pimc_rank_of_information_set_card": (
            comparison.pimc_rank_of_information_set_card
        ),
        "information_set_rank_of_actual_card": (
            comparison.information_set_rank_of_actual_card
        ),
        "pimc_rank_of_actual_card": comparison.pimc_rank_of_actual_card,
        "information_set_minus_pimc_at_information_set_card": (
            _serialize_metric_deltas(
                comparison.information_set_minus_pimc_at_information_set_card
            )
        ),
        "information_set_minus_pimc_at_pimc_card": _serialize_metric_deltas(
            comparison.information_set_minus_pimc_at_pimc_card
        ),
        "strategy_fusion_mitigation_scope": (
            comparison.strategy_fusion_mitigation_scope
        ),
    }

