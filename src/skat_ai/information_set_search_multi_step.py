from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

from skat_ai.coherent_hidden_world import derive_simulation_child_seed
from skat_ai.effective_opponent_policy import EffectiveOpponentPolicySettings
from skat_ai.game_declaration import GameDeclaration
from skat_ai.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_BUDGET_VERSION,
    InformationSetSearchBudgetV1,
    InformationSetSearchResultV1,
)
from skat_ai.information_set_search_public import (
    build_nondeterministic_fixed_policy_public_result_v1,
    build_public_information_set_search_result_v1,
)
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
    InformationSetSearchSettings,
)
from skat_ai.multi_step_recommendation import MultiStepRecommendationDecision
from skat_ai.opponent_policy import validate_opponent_card_policy
from skat_ai.recommendation_workflow import (
    NONE_EFFECTIVE_METHOD,
    RecommendationMethodConfiguration,
    RecommendationWorkflowResult,
)
from skat_ai.strategic_metadata import StrategicMetadata

INFORMATION_SET_SEARCH_MULTI_STEP_INTEGRATION_VERSION = 1
INFORMATION_SET_SEARCH_MULTI_STEP_DECISION_VERSION = 1
INFORMATION_SET_SEARCH_POLICY_COMPARISON_INTEGRATION_VERSION = 1

INFORMATION_SET_SEARCH_MULTI_STEP_SOURCE_POLICY = (
    "current_public_decision_boundary_without_coherent_world_disclosure"
)
INFORMATION_SET_SEARCH_MULTI_STEP_EXECUTION_POLICY = (
    "fresh_strict_information_set_search_per_local_decision"
)
INFORMATION_SET_SEARCH_MULTI_STEP_SEED_POLICY = (
    "domain_separated_per_decision_world_selection_seed"
)
INFORMATION_SET_SEARCH_MULTI_STEP_STOP_POLICY = (
    "no_recommendation_stops_before_local_play"
)
INFORMATION_SET_SEARCH_MULTI_STEP_POLICY_RETENTION_POLICY = (
    "private_per_decision_policy_not_reused_across_steps"
)
INFORMATION_SET_SEARCH_POLICY_COMPARISON_ROOT_POLICY = (
    "shared_coherent_root_with_independent_immutable_paths"
)
INFORMATION_SET_SEARCH_POLICY_COMPARISON_METHOD_POLICY = (
    "exactly_one_configured_search_policy_appended_last"
)
INFORMATION_SET_SEARCH_POLICY_COMPARISON_ELIGIBILITY_POLICY = (
    "stopped_search_path_visible_but_ineligible"
)
INFORMATION_SET_SEARCH_AUTO_COMPATIBILITY_POLICY = (
    "existing_auto_remains_pimc_then_immediate"
)
INFORMATION_SET_SEARCH_SIMULATION_PUBLIC_POLICY = (
    "safe_aggregate_diagnostics_without_private_worlds_or_policy_table"
)

MULTI_STEP_INFORMATION_SET_SEARCH_DECISION_STREAM = (
    "multi_step_information_set_search_decision_v1"
)

_INFORMATION_SET_SEARCH_PUBLIC_RESULT_FIELDS = (
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
)


def _require_version(value: object, expected: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError("Unsupported Information-set Multi-Step Decision version.")


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    return deepcopy(value)


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json_value(item) for item in value]
    return deepcopy(value)


def _build_canonical_unavailable_public_result(
    public_result: dict[str, Any],
) -> dict[str, Any]:
    try:
        requested_budget = InformationSetSearchBudgetV1(
            information_set_search_budget_version=(
                INFORMATION_SET_SEARCH_BUDGET_VERSION
            ),
            **public_result["requested_budget"],
        )
        fixed_settings = public_result["fixed_policy_settings"]
        if (
            type(fixed_settings) is not list
            or len(fixed_settings) != 2
            or any(type(item) is not dict for item in fixed_settings)
            or [item.get("player") for item in fixed_settings] != ["left", "right"]
        ):
            raise ValueError
        policy_names = tuple(
            item[field]
            for item in fixed_settings
            for field in ("lead_policy", "response_policy")
        )
        for policy_name in policy_names:
            validate_opponent_card_policy(policy_name)
        if "random_legal" not in policy_names:
            raise ValueError
        effective_settings = EffectiveOpponentPolicySettings(
            global_lead_policy=fixed_settings[0]["lead_policy"],
            global_response_policy=fixed_settings[0]["response_policy"],
            left_lead_policy=fixed_settings[0]["lead_policy"],
            left_response_policy=fixed_settings[0]["response_policy"],
            right_lead_policy=fixed_settings[1]["lead_policy"],
            right_response_policy=fixed_settings[1]["response_policy"],
            immediate_response_policy_by_player=None,
            left_lead_source="retained_unavailable_result",
            left_response_source="retained_unavailable_result",
            right_lead_source="retained_unavailable_result",
            right_response_source="retained_unavailable_result",
        )
        return build_nondeterministic_fixed_policy_public_result_v1(
            game_type=public_result["game_type"],
            requested_budget=requested_budget,
            effective_policy_settings=effective_settings,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "Information-set decision unavailable public Result is invalid."
        ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchMultiStepDecisionV1:
    information_set_search_multi_step_decision_version: int
    step_index: int
    requested_method: str
    effective_method: str
    search_attempted: bool
    recommendation_card: str | None
    recommendation_reason: str
    fallback_used: bool
    fallback_method: str | None
    information_set_search_result: InformationSetSearchResultV1 | None
    information_set_search_public_result: Mapping[str, Any]

    def __post_init__(self) -> None:
        _require_version(
            self.information_set_search_multi_step_decision_version,
            INFORMATION_SET_SEARCH_MULTI_STEP_DECISION_VERSION,
        )
        if (
            isinstance(self.step_index, bool)
            or not isinstance(self.step_index, int)
            or self.step_index < 0
        ):
            raise ValueError("Information-set decision step_index must not be negative.")
        if self.requested_method != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
            raise ValueError("Information-set decision requires information_set_search.")
        if self.search_attempted is not True:
            raise ValueError("Information-set decision must attempt Search.")
        if not isinstance(self.recommendation_reason, str) or not self.recommendation_reason:
            raise ValueError("Information-set decision requires a recommendation reason.")
        if self.fallback_used is not False or self.fallback_method is not None:
            raise ValueError("Information-set decision cannot use fallback.")
        if not isinstance(self.information_set_search_public_result, Mapping):
            raise ValueError("Information-set decision requires one exact safe public Result.")
        public_result = _thaw_json_value(self.information_set_search_public_result)
        if tuple(public_result) != _INFORMATION_SET_SEARCH_PUBLIC_RESULT_FIELDS:
            raise ValueError("Information-set decision public Result fields are invalid.")
        if self.information_set_search_result is not None:
            if type(self.information_set_search_result) is not InformationSetSearchResultV1:
                raise ValueError("Information-set decision contains an invalid private Result.")
            if build_public_information_set_search_result_v1(
                self.information_set_search_result
            ) != public_result:
                raise ValueError("Private and public Information-set Results must match.")
        elif public_result != _build_canonical_unavailable_public_result(public_result):
            raise ValueError(
                "A missing private Result requires canonical public unavailability."
            )
        public_card = public_result.get("recommended_card")
        if public_card != self.recommendation_card:
            raise ValueError("Information-set decision recommendation Cards must match.")
        expected_effective = (
            INFORMATION_SET_SEARCH_EFFECTIVE_METHOD
            if self.recommendation_card is not None
            else NONE_EFFECTIVE_METHOD
        )
        if self.effective_method != expected_effective:
            raise ValueError("Information-set decision effective method is inconsistent.")
        object.__setattr__(
            self,
            "information_set_search_public_result",
            _freeze_json_value(public_result),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializes the complete private Decision defensively."""
        return {
            "information_set_search_multi_step_decision_version": (
                self.information_set_search_multi_step_decision_version
            ),
            "step_index": self.step_index,
            "requested_method": self.requested_method,
            "effective_method": self.effective_method,
            "search_attempted": self.search_attempted,
            "recommendation_card": self.recommendation_card,
            "recommendation_reason": self.recommendation_reason,
            "fallback_used": self.fallback_used,
            "fallback_method": self.fallback_method,
            "information_set_search_result": (
                self.information_set_search_result.to_dict()
                if self.information_set_search_result is not None
                else None
            ),
            "information_set_search_public_result": _thaw_json_value(
                self.information_set_search_public_result
            ),
        }


type SearchAwareMultiStepDecision = (
    MultiStepRecommendationDecision | InformationSetSearchMultiStepDecisionV1
)


def validate_information_set_search_multi_step_inputs_v1(
    *,
    game_declaration: GameDeclaration | None,
    recommendation_configuration: RecommendationMethodConfiguration | None,
    strategic_metadata: StrategicMetadata | None,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None,
) -> None:
    if type(game_declaration) is not GameDeclaration:
        raise ValueError(
            "Information-set Search Multi-Step requires a normalized game declaration."
        )
    if type(recommendation_configuration) is not RecommendationMethodConfiguration:
        raise ValueError(
            "Information-set Search Multi-Step requires exact recommendation configuration."
        )
    if (
        recommendation_configuration.requested_method
        != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
    ):
        raise ValueError(
            "Multi-Step Information-set Search policy and recommendation method must match."
        )
    if (
        type(recommendation_configuration.information_set_search_settings)
        is not InformationSetSearchSettings
    ):
        raise ValueError("Information-set Search Multi-Step requires exact settings.")
    if (
        recommendation_configuration.search_random_seed is not None
        or recommendation_configuration.requested_search_budget is not None
    ):
        raise ValueError("Information-set Search Multi-Step rejects bounded Search settings.")
    if type(effective_opponent_policy_settings) is not EffectiveOpponentPolicySettings:
        raise ValueError(
            "Information-set Search Multi-Step requires exact effective opponent settings."
        )
    if type(strategic_metadata) is not StrategicMetadata:
        raise ValueError("Information-set Search Multi-Step requires live strategic metadata.")
    if strategic_metadata.analysis_mode != "live_decision":
        raise ValueError(
            "Information-set Search Multi-Step requires analysis_mode='live_decision'."
        )
    if strategic_metadata.game_end_reason != "not_ended":
        raise ValueError(
            "Information-set Search Multi-Step requires game_end_reason='not_ended'."
        )


def derive_information_set_search_multi_step_configuration_v1(
    configuration: RecommendationMethodConfiguration,
    *,
    step_index: int,
) -> RecommendationMethodConfiguration:
    if type(configuration) is not RecommendationMethodConfiguration:
        raise ValueError("configuration must be RecommendationMethodConfiguration.")
    if configuration.requested_method != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        raise ValueError("Information-set child settings require information_set_search.")
    settings = configuration.information_set_search_settings
    if type(settings) is not InformationSetSearchSettings:
        raise ValueError("Information-set child settings require exact settings.")
    if isinstance(step_index, bool) or not isinstance(step_index, int) or step_index < 0:
        raise ValueError("step_index must be a strict non-negative integer.")
    child_settings = replace(
        settings,
        random_seed=derive_simulation_child_seed(
            settings.random_seed,
            MULTI_STEP_INFORMATION_SET_SEARCH_DECISION_STREAM,
            child_index=step_index,
        ),
    )
    return replace(
        configuration,
        information_set_search_settings=child_settings,
    )


def build_information_set_search_multi_step_decision_v1(
    *,
    step_index: int,
    workflow: RecommendationWorkflowResult,
) -> InformationSetSearchMultiStepDecisionV1:
    if type(workflow) is not RecommendationWorkflowResult:
        raise ValueError("workflow must be RecommendationWorkflowResult.")
    if workflow.requested_method != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        raise ValueError("Information-set Multi-Step requires its strict workflow.")
    public_result = workflow.information_set_search_public_result
    if public_result is None:
        raise ValueError("Information-set Multi-Step requires a retained public Result.")
    return InformationSetSearchMultiStepDecisionV1(
        information_set_search_multi_step_decision_version=(
            INFORMATION_SET_SEARCH_MULTI_STEP_DECISION_VERSION
        ),
        step_index=step_index,
        requested_method=workflow.requested_method,
        effective_method=workflow.effective_method,
        search_attempted=True,
        recommendation_card=workflow.recommendation_card,
        recommendation_reason=workflow.recommendation_reason,
        fallback_used=False,
        fallback_method=None,
        information_set_search_result=workflow.information_set_search_result,
        information_set_search_public_result=public_result,
    )


def build_serializable_information_set_search_multi_step_decision_v1(
    decision: InformationSetSearchMultiStepDecisionV1,
    *,
    executed_card: str | None,
) -> dict[str, Any]:
    if type(decision) is not InformationSetSearchMultiStepDecisionV1:
        raise ValueError("Invalid Information-set Multi-Step Decision.")
    if decision.recommendation_card != executed_card:
        raise ValueError("Recommendation decision card must match the executed card.")
    return {
        "schema_version": INFORMATION_SET_SEARCH_MULTI_STEP_DECISION_VERSION,
        "step_index": decision.step_index,
        "requested_method": decision.requested_method,
        "effective_method": decision.effective_method,
        "search_attempted": decision.search_attempted,
        "recommendation_card": decision.recommendation_card,
        "recommendation_reason": decision.recommendation_reason,
        "fallback_used": decision.fallback_used,
        "fallback_method": decision.fallback_method,
        "information_set_search_result": _thaw_json_value(
            decision.information_set_search_public_result
        ),
    }


def build_compact_information_set_search_decision_diagnostic_v1(
    decision: InformationSetSearchMultiStepDecisionV1,
) -> dict[str, str | int | bool | None]:
    if type(decision) is not InformationSetSearchMultiStepDecisionV1:
        raise ValueError("Invalid Information-set Multi-Step Decision.")
    public_result = decision.information_set_search_public_result
    consumed = public_result["consumed_budget"]
    return {
        "step_index": decision.step_index,
        "requested_method": decision.requested_method,
        "effective_method": decision.effective_method,
        "search_method": public_result["search_method"],
        "search_status": public_result["status"],
        "search_stop_reason": public_result["stop_reason"],
        "world_coverage": public_result["world_coverage"],
        "policy_claim": public_result["policy_claim"],
        "policy_consistency": public_result["policy_consistency"],
        "selected_world_count": consumed["selected_world_count"],
        "completed_world_count": consumed["completed_world_count"],
        "information_sets_evaluated": consumed["information_sets_evaluated"],
        "controlled_policy_decision_count": public_result[
            "controlled_policy_decision_count"
        ],
        "fixed_policy_decision_count": consumed["fixed_policy_decisions"],
        "recommendation_card": decision.recommendation_card,
        "fallback_used": decision.fallback_used,
    }
