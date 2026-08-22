from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from skat_ai.api.v1.contracts import (
    _freeze_json_object,
    _freeze_json_value,
    _thaw_json_value,
)

LEARNING_CORPUS_INFORMATION_SET_STRATEGY_TEACHER_EXTENSION_VERSION = 1

LEARNING_CORPUS_INFORMATION_SET_TEACHER_POLICY = (
    "method_bound_information_set_evidence_not_ground_truth"
)
LEARNING_CORPUS_INFORMATION_SET_TEACHER_RESULT_POLICY = (
    "retain_safe_aggregate_result_without_controlled_policy_table"
)
LEARNING_CORPUS_INFORMATION_SET_TEACHER_COMPARISON_POLICY = (
    "same_selection_pimc_and_immediate_are_diagnostic_baselines"
)
LEARNING_CORPUS_INFORMATION_SET_TEACHER_IDENTITY_POLICY = (
    "exact_source_identity_and_wall_clock_normalized_semantic_identity"
)
LEARNING_CORPUS_INFORMATION_SET_TEACHER_PRIVACY_POLICY = (
    "minimized_private_evidence_without_worlds_observations_or_policy_table"
)
LEARNING_CORPUS_INFORMATION_SET_TEACHER_AUTOMATION_POLICY = (
    "explicit_report_transfer_without_automatic_capture"
)

_RESULT_FIELDS = {
    "schema_version",
    "analysis_method",
    "search_method",
    "status",
    "stop_reason",
    "game_type",
    "world_coverage",
    "policy_claim",
    "policy_consistency",
    "terminal_utility_version",
    "requested_budget",
    "consumed_budget",
    "compatible_world_count",
    "candidate_results",
    "recommended_card",
    "controlled_policy_decision_count",
    "fixed_policy_settings",
}
_REQUESTED_BUDGET_FIELDS = {
    "max_remaining_tricks",
    "max_depth_plies",
    "max_state_nodes",
    "max_information_sets",
    "max_selected_worlds",
    "max_sampled_worlds",
    "minimum_comparable_worlds",
    "wall_clock_timeout_ms",
}
_CONSUMED_BUDGET_FIELDS = {
    "depth_reached",
    "state_nodes_evaluated",
    "information_sets_evaluated",
    "controlled_policy_decisions",
    "fixed_policy_decisions",
    "selected_world_count",
    "completed_world_count",
    "sampled_world_count",
    "unique_sampled_world_count",
    "wall_clock_elapsed_ms",
}
_CANDIDATE_FIELDS = {
    "card",
    "rank",
    "is_recommended",
    "completed_world_count",
    "local_contract_success_count",
    "local_contract_success_rate",
    "mean_local_side_game_score",
    "mean_local_side_card_point_margin",
}
_FIXED_POLICY_FIELDS = {"player", "lead_policy", "response_policy"}
_COMPARISON_FIELDS = {
    "schema_version",
    "comparison_method",
    "comparison_status",
    "unavailable_reason",
    "same_selected_world_sequence",
    "selected_world_count",
    "sampled_world_count",
    "information_set_status",
    "pimc_status",
    "information_set_recommended_card",
    "pimc_recommended_card",
    "immediate_recommended_card",
    "actual_card",
    "information_set_pimc_same_card",
    "information_set_immediate_same_card",
    "pimc_immediate_same_card",
    "information_set_actual_same_card",
    "pimc_actual_same_card",
    "immediate_actual_same_card",
    "information_set_rank_of_pimc_card",
    "pimc_rank_of_information_set_card",
    "information_set_rank_of_actual_card",
    "pimc_rank_of_actual_card",
    "information_set_minus_pimc_at_information_set_card",
    "information_set_minus_pimc_at_pimc_card",
    "strategy_fusion_mitigation_scope",
}


def _require_exact_fields(
    value: Mapping[str, object],
    fields: set[str],
    field_name: str,
) -> None:
    if set(value) != fields:
        raise ValueError(f"{field_name} fields must be exact.")


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON object.")
    return value


def _require_sequence(value: object, field_name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a JSON array.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusInformationSetStrategyTeacherEvidenceV1:
    """Minimized safe aggregate evidence from one exact Match Result."""

    learning_corpus_information_set_strategy_teacher_extension_version: int
    information_set_search_result: Mapping[str, object]
    information_set_search_comparison: Mapping[str, object]
    search_status: str
    search_stop_reason: str
    world_coverage: str
    policy_claim: str
    policy_consistency: str
    requested_budget: Mapping[str, object]
    consumed_budget: Mapping[str, object]
    candidate_results: tuple[object, ...]
    controlled_policy_decision_count: int
    information_sets_evaluated: int
    fixed_policy_settings: tuple[object, ...]
    information_set_recommended_card: str | None
    pimc_recommended_card: str | None
    immediate_recommended_card: str | None
    actual_card_played: str
    wall_clock_elapsed_ms: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusInformationSetStrategyTeacherEvidenceV1 must be "
            "constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: object,
    ) -> LearningCorpusInformationSetStrategyTeacherEvidenceV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_information_set_strategy_teacher_extension_version",
            LEARNING_CORPUS_INFORMATION_SET_STRATEGY_TEACHER_EXTENSION_VERSION,
        )
        for field_name, field_value in values.items():
            if field_name in {
                "information_set_search_result",
                "information_set_search_comparison",
                "requested_budget",
                "consumed_budget",
            }:
                field_value = _freeze_json_object(
                    cast(Mapping[str, object], field_value),
                    path=field_name,
                )
            elif field_name in {"candidate_results", "fixed_policy_settings"}:
                field_value = _freeze_json_value(field_value, path=field_name)
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        if (
            type(self.learning_corpus_information_set_strategy_teacher_extension_version) is not int
            or self.learning_corpus_information_set_strategy_teacher_extension_version
            != LEARNING_CORPUS_INFORMATION_SET_STRATEGY_TEACHER_EXTENSION_VERSION
        ):
            raise ValueError("Unsupported Learning Corpus Information-set Teacher version.")
        result = self.information_set_search_result
        comparison = self.information_set_search_comparison
        _require_exact_fields(result, _RESULT_FIELDS, "information_set_search_result")
        _require_exact_fields(
            comparison,
            _COMPARISON_FIELDS,
            "information_set_search_comparison",
        )
        requested = _require_mapping(result.get("requested_budget"), "requested_budget")
        consumed = _require_mapping(result.get("consumed_budget"), "consumed_budget")
        candidates = _require_sequence(result.get("candidate_results"), "candidate_results")
        fixed = _require_sequence(result.get("fixed_policy_settings"), "fixed_policy_settings")
        _require_exact_fields(requested, _REQUESTED_BUDGET_FIELDS, "requested_budget")
        _require_exact_fields(consumed, _CONSUMED_BUDGET_FIELDS, "consumed_budget")
        for item in candidates:
            _require_exact_fields(
                _require_mapping(item, "candidate_result"),
                _CANDIDATE_FIELDS,
                "candidate_result",
            )
        if len(fixed) != 2:
            raise ValueError("fixed_policy_settings must contain left and right.")
        for item in fixed:
            _require_exact_fields(
                _require_mapping(item, "fixed_policy_setting"),
                _FIXED_POLICY_FIELDS,
                "fixed_policy_setting",
            )
        if (
            self.search_status != result.get("status")
            or self.search_stop_reason != result.get("stop_reason")
            or self.world_coverage != result.get("world_coverage")
            or self.policy_claim != result.get("policy_claim")
            or self.policy_consistency != result.get("policy_consistency")
            or self.requested_budget != requested
            or self.consumed_budget != consumed
            or self.candidate_results != tuple(candidates)
            or self.controlled_policy_decision_count
            != result.get("controlled_policy_decision_count")
            or self.information_sets_evaluated != consumed.get("information_sets_evaluated")
            or self.fixed_policy_settings != tuple(fixed)
            or self.wall_clock_elapsed_ms != consumed.get("wall_clock_elapsed_ms")
        ):
            raise ValueError(
                "Information-set Teacher convenience fields must equal the safe Result."
            )
        if (
            comparison.get("information_set_status") != self.search_status
            or comparison.get("information_set_recommended_card")
            != self.information_set_recommended_card
            or result.get("recommended_card") != self.information_set_recommended_card
            or comparison.get("pimc_recommended_card") != self.pimc_recommended_card
            or comparison.get("immediate_recommended_card") != self.immediate_recommended_card
            or comparison.get("actual_card") != self.actual_card_played
            or comparison.get("selected_world_count") != consumed.get("selected_world_count")
            or comparison.get("sampled_world_count") != consumed.get("sampled_world_count")
        ):
            raise ValueError("Information-set Teacher comparison must equal retained stage values.")
        if self.controlled_policy_decision_count != consumed.get("controlled_policy_decisions"):
            raise ValueError("Information-set Teacher controlled-Policy counts differ.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_information_set_strategy_teacher_extension_version": (
                self.learning_corpus_information_set_strategy_teacher_extension_version
            ),
            "information_set_search_result": _thaw_json_value(self.information_set_search_result),
            "information_set_search_comparison": _thaw_json_value(
                self.information_set_search_comparison
            ),
            "search_status": self.search_status,
            "search_stop_reason": self.search_stop_reason,
            "world_coverage": self.world_coverage,
            "policy_claim": self.policy_claim,
            "policy_consistency": self.policy_consistency,
            "requested_budget": _thaw_json_value(self.requested_budget),
            "consumed_budget": _thaw_json_value(self.consumed_budget),
            "candidate_results": _thaw_json_value(self.candidate_results),
            "controlled_policy_decision_count": (self.controlled_policy_decision_count),
            "information_sets_evaluated": self.information_sets_evaluated,
            "fixed_policy_settings": _thaw_json_value(self.fixed_policy_settings),
            "information_set_recommended_card": (self.information_set_recommended_card),
            "pimc_recommended_card": self.pimc_recommended_card,
            "immediate_recommended_card": self.immediate_recommended_card,
            "actual_card_played": self.actual_card_played,
            "wall_clock_elapsed_ms": self.wall_clock_elapsed_ms,
        }


def build_learning_corpus_information_set_strategy_teacher_evidence_v1(
    *,
    information_set_search_result: Mapping[str, object],
    information_set_search_comparison: Mapping[str, object],
    actual_card_played: str,
) -> LearningCorpusInformationSetStrategyTeacherEvidenceV1:
    """Builds minimized evidence from already executed, schema-valid values."""
    result = _require_mapping(
        information_set_search_result,
        "information_set_search_result",
    )
    comparison = _require_mapping(
        information_set_search_comparison,
        "information_set_search_comparison",
    )
    requested = _require_mapping(result.get("requested_budget"), "requested_budget")
    consumed = _require_mapping(result.get("consumed_budget"), "consumed_budget")
    candidates = _require_sequence(result.get("candidate_results"), "candidate_results")
    fixed = _require_sequence(result.get("fixed_policy_settings"), "fixed_policy_settings")
    return LearningCorpusInformationSetStrategyTeacherEvidenceV1._from_validated(
        information_set_search_result=result,
        information_set_search_comparison=comparison,
        search_status=result.get("status"),
        search_stop_reason=result.get("stop_reason"),
        world_coverage=result.get("world_coverage"),
        policy_claim=result.get("policy_claim"),
        policy_consistency=result.get("policy_consistency"),
        requested_budget=requested,
        consumed_budget=consumed,
        candidate_results=candidates,
        controlled_policy_decision_count=result.get("controlled_policy_decision_count"),
        information_sets_evaluated=consumed.get("information_sets_evaluated"),
        fixed_policy_settings=fixed,
        information_set_recommended_card=result.get("recommended_card"),
        pimc_recommended_card=comparison.get("pimc_recommended_card"),
        immediate_recommended_card=comparison.get("immediate_recommended_card"),
        actual_card_played=actual_card_played,
        wall_clock_elapsed_ms=consumed.get("wall_clock_elapsed_ms"),
    )
