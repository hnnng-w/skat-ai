from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skat_ai.analysis_report import build_card_analysis_report, build_strategic_summary
from skat_ai.bounded_search_information import build_live_search_information_view
from skat_ai.bounded_search_result import (
    BoundedSearchResult,
    RequestedSearchBudget,
    mark_bounded_search_fallback_used,
)
from skat_ai.compatible_world_minimax import solve_compatible_world_minimax
from skat_ai.effective_opponent_policy import EffectiveOpponentPolicySettings
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    HiddenCardInferenceModel,
    build_hidden_card_inference_model,
)
from skat_ai.information_set_search_contracts import InformationSetSearchResultV1
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
    INFORMATION_SET_SEARCH_SETTING_KEYS,
    InformationSetSearchSettings,
    InformationSetSearchWorkflowResultV1,
    execute_live_information_set_search_workflow_v1,
)
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.rules import get_legal_cards

IMMEDIATE_EXPECTED_VALUE_METHOD = "immediate_expected_value"
BOUNDED_SEARCH_METHOD = "bounded_search"
AUTO_METHOD = "auto"
COMPATIBLE_WORLD_MINIMAX_METHOD = "compatible_world_minimax_v1"
NONE_EFFECTIVE_METHOD = "none"
NONE_ANALYSIS_REPORT_METHOD = "none"
VALID_RECOMMENDATION_METHODS = (
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    BOUNDED_SEARCH_METHOD,
    AUTO_METHOD,
)
SEARCH_RECOMMENDATION_METHODS = (BOUNDED_SEARCH_METHOD, AUTO_METHOD)
FLAT_RECOMMENDATION_METHODS = (
    *VALID_RECOMMENDATION_METHODS,
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
)
FLAT_SEARCH_RECOMMENDATION_METHODS = (
    *SEARCH_RECOMMENDATION_METHODS,
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
)

IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON = (
    "Immediate analysis is unavailable because the local player is not next."
)
IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON = (
    "Immediate analysis is unavailable because the game is complete."
)

BOUNDED_SEARCH_SETTING_KEYS = (
    "random_seed",
    "max_remaining_tricks",
    "max_depth_plies",
    "max_nodes",
    "max_selected_worlds",
    "max_sampled_worlds",
    "minimum_comparable_worlds",
    "wall_clock_timeout_ms",
)


@dataclass(frozen=True)
class RecommendationMethodConfiguration:
    """One validated explicit or backward-compatible recommendation request."""

    explicitly_supplied: bool
    requested_method: str
    search_random_seed: int | None = None
    requested_search_budget: RequestedSearchBudget | None = None
    information_set_search_settings: InformationSetSearchSettings | None = None

    def __post_init__(self) -> None:
        if self.requested_method not in FLAT_RECOMMENDATION_METHODS:
            raise ValueError(f"Invalid recommendation_method: {self.requested_method}")
        if self.requested_method in SEARCH_RECOMMENDATION_METHODS:
            if self.search_random_seed is None or self.requested_search_budget is None:
                raise ValueError(
                    "Search recommendation methods require bounded_search_settings."
                )
            if self.information_set_search_settings is not None:
                raise ValueError(
                    "Bounded Search recommendation methods cannot contain "
                    "information-set Search settings."
                )
        elif self.requested_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
            if self.information_set_search_settings is None:
                raise ValueError(
                    "Information-set Search requires information_set_search_settings."
                )
            if type(self.information_set_search_settings) is not InformationSetSearchSettings:
                raise ValueError(
                    "information_set_search_settings must be InformationSetSearchSettings."
                )
            if self.search_random_seed is not None or self.requested_search_budget is not None:
                raise ValueError(
                    "Information-set Search cannot contain bounded Search settings."
                )
        elif (
            self.search_random_seed is not None
            or self.requested_search_budget is not None
            or self.information_set_search_settings is not None
        ):
            raise ValueError(
                "Immediate recommendation cannot contain Search settings."
            )


@dataclass(frozen=True)
class RecommendationWorkflowResult:
    """Immutable routing result for one flat position recommendation."""

    requested_method: str
    effective_method: str
    recommendation_card: str | None
    recommendation_reason: str
    legal_cards: tuple[str, ...]
    analysis_report: tuple[dict[str, float | str | bool], ...]
    analysis_report_method: str
    strategic_summary: str
    bounded_search_result: BoundedSearchResult | None
    fallback_used: bool
    fallback_method: str | None
    hidden_card_inference_model: HiddenCardInferenceModel | None = None
    information_set_search_result: InformationSetSearchResultV1 | None = None
    information_set_search_public_result: dict[str, Any] | None = None
    information_set_search_workflow: InformationSetSearchWorkflowResultV1 | None = None

    def __post_init__(self) -> None:
        if self.requested_method not in FLAT_RECOMMENDATION_METHODS:
            raise ValueError("Recommendation workflow has an invalid requested method.")
        if self.effective_method not in {
            IMMEDIATE_EXPECTED_VALUE_METHOD,
            COMPATIBLE_WORLD_MINIMAX_METHOD,
            INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
            NONE_EFFECTIVE_METHOD,
        }:
            raise ValueError("Recommendation workflow has an invalid effective method.")
        if self.analysis_report_method not in {
            IMMEDIATE_EXPECTED_VALUE_METHOD,
            NONE_ANALYSIS_REPORT_METHOD,
        }:
            raise ValueError("Recommendation workflow has an invalid report method.")
        if self.analysis_report_method == NONE_ANALYSIS_REPORT_METHOD and self.analysis_report:
            raise ValueError("Report method none requires an empty analysis report.")
        if self.effective_method == NONE_EFFECTIVE_METHOD and self.recommendation_card is not None:
            raise ValueError("Effective method none cannot recommend a card.")
        if self.effective_method != NONE_EFFECTIVE_METHOD and self.recommendation_card is None:
            raise ValueError("An effective recommendation method requires a card.")
        if (
            self.recommendation_card is not None
            and self.recommendation_card not in self.legal_cards
        ):
            raise ValueError("The effective recommendation card must be legal.")
        if self.effective_method == COMPATIBLE_WORLD_MINIMAX_METHOD:
            if self.bounded_search_result is None or self.recommendation_card is None:
                raise ValueError("Effective bounded Search requires a Search recommendation.")
            if self.analysis_report or self.analysis_report_method != NONE_ANALYSIS_REPORT_METHOD:
                raise ValueError("Effective bounded Search cannot emit an Immediate report.")
            if self.bounded_search_result.recommended_card != self.recommendation_card:
                raise ValueError("Top-level and Search recommendation cards must match.")
        if self.requested_method == IMMEDIATE_EXPECTED_VALUE_METHOD:
            if (
                self.bounded_search_result is not None
                or self.fallback_used
                or self.effective_method == COMPATIBLE_WORLD_MINIMAX_METHOD
                or self.analysis_report_method != IMMEDIATE_EXPECTED_VALUE_METHOD
            ):
                raise ValueError("Immediate recommendation method metadata is inconsistent.")
        elif self.requested_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
            if (
                self.bounded_search_result is not None
                or self.fallback_used
                or self.fallback_method is not None
                or self.analysis_report
                or self.analysis_report_method != NONE_ANALYSIS_REPORT_METHOD
                or self.information_set_search_public_result is None
                or self.information_set_search_workflow is None
            ):
                raise ValueError(
                    "Information-set Search recommendation metadata is inconsistent."
                )
            if self.information_set_search_result is not (
                self.information_set_search_workflow.result
            ):
                raise ValueError("Retained Information-set Search Results must match.")
            if self.information_set_search_public_result is not (
                self.information_set_search_workflow.public_result
            ):
                raise ValueError("Retained public Information-set Results must match.")
            if self.information_set_search_public_result.get(
                "recommended_card"
            ) != self.recommendation_card:
                raise ValueError(
                    "Top-level and Information-set Search recommendation Cards must match."
                )
            expected_effective = (
                INFORMATION_SET_SEARCH_EFFECTIVE_METHOD
                if self.recommendation_card is not None
                else NONE_EFFECTIVE_METHOD
            )
            if self.effective_method != expected_effective:
                raise ValueError("Information-set Search effective method is inconsistent.")
        elif self.bounded_search_result is None:
            raise ValueError("Search recommendation methods require a Search result.")
        if self.bounded_search_result is not None and (
            self.bounded_search_result.fallback_used != self.fallback_used
            or self.bounded_search_result.fallback_method != self.fallback_method
        ):
            raise ValueError("Workflow and Search fallback metadata must match.")
        if self.requested_method == BOUNDED_SEARCH_METHOD:
            if (
                self.fallback_used
                or self.effective_method == IMMEDIATE_EXPECTED_VALUE_METHOD
                or self.analysis_report_method != NONE_ANALYSIS_REPORT_METHOD
            ):
                raise ValueError("Strict bounded Search cannot use Immediate fallback.")
        if self.fallback_used:
            if (
                self.requested_method != AUTO_METHOD
                or self.effective_method != IMMEDIATE_EXPECTED_VALUE_METHOD
                or self.fallback_method != IMMEDIATE_EXPECTED_VALUE_METHOD
                or self.recommendation_card is None
                or self.bounded_search_result is None
                or not self.bounded_search_result.fallback_used
            ):
                raise ValueError("Recommendation fallback metadata is inconsistent.")
        elif self.fallback_method is not None:
            raise ValueError("fallback_method must be null when fallback is unused.")
        if self.requested_method == AUTO_METHOD:
            if self.effective_method == IMMEDIATE_EXPECTED_VALUE_METHOD and not self.fallback_used:
                raise ValueError("Effective auto Immediate requires marked fallback.")
            if (
                self.effective_method == NONE_EFFECTIVE_METHOD
                and self.analysis_report_method != IMMEDIATE_EXPECTED_VALUE_METHOD
            ):
                raise ValueError("Failed auto fallback requires the Immediate report method.")
        if self.requested_method != INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD and (
            self.information_set_search_result is not None
            or self.information_set_search_public_result is not None
            or self.information_set_search_workflow is not None
            or self.effective_method == INFORMATION_SET_SEARCH_EFFECTIVE_METHOD
        ):
            raise ValueError(
                "Only Information-set Search may retain Information-set Search values."
            )


def build_recommendation_method_configuration(
    data: dict[str, Any],
) -> RecommendationMethodConfiguration:
    """Builds and validates the optional public method and Search settings."""
    explicitly_supplied = "recommendation_method" in data
    requested_method = data.get(
        "recommendation_method",
        IMMEDIATE_EXPECTED_VALUE_METHOD,
    )
    if requested_method not in FLAT_RECOMMENDATION_METHODS:
        raise ValueError(f"Invalid recommendation_method: {requested_method}")

    bounded_settings_supplied = "bounded_search_settings" in data
    information_set_settings_supplied = "information_set_search_settings" in data
    if requested_method == IMMEDIATE_EXPECTED_VALUE_METHOD:
        if bounded_settings_supplied or information_set_settings_supplied:
            raise ValueError(
                "Search settings are allowed only for their matching Search method."
            )
        return RecommendationMethodConfiguration(
            explicitly_supplied=explicitly_supplied,
            requested_method=requested_method,
        )

    if requested_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        if bounded_settings_supplied:
            raise ValueError(
                "information_set_search rejects bounded_search_settings."
            )
        if not information_set_settings_supplied:
            raise ValueError(
                "recommendation_method='information_set_search' requires "
                "information_set_search_settings."
            )
        raw_settings = data["information_set_search_settings"]
        if not isinstance(raw_settings, dict):
            raise ValueError("information_set_search_settings must be an object.")
        missing = sorted(set(INFORMATION_SET_SEARCH_SETTING_KEYS) - set(raw_settings))
        unknown = sorted(set(raw_settings) - set(INFORMATION_SET_SEARCH_SETTING_KEYS))
        if missing:
            raise ValueError(
                f"information_set_search_settings is missing required keys: {missing}"
            )
        if unknown:
            raise ValueError(
                f"information_set_search_settings has unsupported keys: {unknown}"
            )
        return RecommendationMethodConfiguration(
            explicitly_supplied=True,
            requested_method=requested_method,
            information_set_search_settings=InformationSetSearchSettings(
                **raw_settings
            ),
        )

    if information_set_settings_supplied:
        raise ValueError(
            "bounded_search and auto reject information_set_search_settings."
        )
    if not bounded_settings_supplied:
        raise ValueError(
            f"recommendation_method='{requested_method}' requires bounded_search_settings."
        )
    raw_settings = data["bounded_search_settings"]
    if not isinstance(raw_settings, dict):
        raise ValueError("bounded_search_settings must be an object.")
    missing = sorted(set(BOUNDED_SEARCH_SETTING_KEYS) - set(raw_settings))
    unknown = sorted(set(raw_settings) - set(BOUNDED_SEARCH_SETTING_KEYS))
    if missing:
        raise ValueError(f"bounded_search_settings is missing required keys: {missing}")
    if unknown:
        raise ValueError(f"bounded_search_settings has unsupported keys: {unknown}")
    random_seed = raw_settings["random_seed"]
    if isinstance(random_seed, bool) or not isinstance(random_seed, int):
        raise ValueError(
            "bounded_search_settings.random_seed must be an integer and must not be a boolean."
        )
    requested_budget = RequestedSearchBudget(
        max_remaining_tricks=raw_settings["max_remaining_tricks"],
        max_depth_plies=raw_settings["max_depth_plies"],
        max_nodes=raw_settings["max_nodes"],
        max_selected_worlds=raw_settings["max_selected_worlds"],
        max_sampled_worlds=raw_settings["max_sampled_worlds"],
        minimum_comparable_worlds=raw_settings["minimum_comparable_worlds"],
        wall_clock_timeout_ms=raw_settings["wall_clock_timeout_ms"],
    )
    return RecommendationMethodConfiguration(
        explicitly_supplied=True,
        requested_method=requested_method,
        search_random_seed=random_seed,
        requested_search_budget=requested_budget,
    )


def validate_recommendation_method_workflow(
    data: dict[str, Any],
    configuration: RecommendationMethodConfiguration,
) -> None:
    """Enforces the flat ongoing decision boundary for Search methods."""
    if configuration.requested_method not in FLAT_SEARCH_RECOMMENDATION_METHODS:
        return
    analysis_mode = data.get("analysis_mode", "live_decision")
    if analysis_mode not in {"live_decision", "post_game_review"}:
        raise ValueError(
            "Search recommendation methods require live_decision or post_game_review."
        )
    if data.get("game_end_reason", "not_ended") != "not_ended":
        raise ValueError("Search recommendation methods require game_end_reason='not_ended'.")
    if data.get("skat_visibility", "unknown") == "known_post_game":
        raise ValueError("Search recommendation methods cannot use post-game Skat visibility.")
    if analysis_mode == "live_decision" and "actual_card_played" in data:
        raise ValueError("Search recommendation methods do not accept actual_card_played.")
    if analysis_mode == "post_game_review" and "actual_card_played" not in data:
        raise ValueError(
            "Post-game Search recommendation methods require actual_card_played."
        )
    if data.get("played_cards", []):
        raise ValueError(
            "Search recommendation methods require attributed completed_tricks instead "
            "of legacy played_cards."
        )
    if "game_shortening" in data:
        raise ValueError("Search recommendation methods do not support terminal game shortening.")
    if "impossible_null_settlement" in data:
        raise ValueError("Search recommendation methods do not support impossible-Null settlement.")
    list_fields = {
        "list_performance_input",
        "list_game_contributions",
        "list_analysis_results",
        "list_standings_input",
    }.intersection(data)
    if list_fields:
        raise ValueError("Search recommendation methods require flat position analysis.")
    for index, trick in enumerate(data.get("completed_tricks", [])):
        if not isinstance(trick, dict) or "players" not in trick:
            raise ValueError(
                "Search recommendation methods require attributed completed_tricks; "
                f"completed_tricks[{index}] has no players."
            )


def build_serializable_bounded_search_settings(
    configuration: RecommendationMethodConfiguration,
) -> dict[str, int | None] | None:
    """Serializes only normalized public Search settings, never a child seed."""
    budget = configuration.requested_search_budget
    if budget is None:
        return None
    return {
        "random_seed": configuration.search_random_seed,
        "max_remaining_tricks": budget.max_remaining_tricks,
        "max_depth_plies": budget.max_depth_plies,
        "max_nodes": budget.max_nodes,
        "max_selected_worlds": budget.max_selected_worlds,
        "max_sampled_worlds": budget.max_sampled_worlds,
        "minimum_comparable_worlds": budget.minimum_comparable_worlds,
        "wall_clock_timeout_ms": budget.wall_clock_timeout_ms,
    }


def build_serializable_information_set_search_settings(
    configuration: RecommendationMethodConfiguration,
) -> dict[str, int | None] | None:
    settings = configuration.information_set_search_settings
    if settings is None:
        return None
    return {
        key: getattr(settings, key) for key in INFORMATION_SET_SEARCH_SETTING_KEYS
    }


def get_immediate_unavailable_reason(
    state_next_player: str,
    game_end_reason: str,
    has_game_shortening: bool = False,
) -> str | None:
    """Returns why Immediate Analysis is unavailable, if unavailable."""
    if game_end_reason != "not_ended" or has_game_shortening:
        return IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON
    if state_next_player != "me":
        return IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON
    return None


def build_unavailable_strategic_summary(reason: str) -> str:
    """Builds the existing readable unavailable summary."""
    return f"Strategic summary: {reason}"


def _run_immediate(
    *,
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None,
    use_basic_opponent_strategy: bool,
    opponent_response_policy_by_player: dict[str, str],
    public_hand_constraints: tuple[PublicHandConstraint, ...],
    unavailable_reason: str | None,
    legal_cards_builder: Callable[..., list[str]],
    hidden_model_builder: Callable[..., HiddenCardInferenceModel | None],
    immediate_recommender: Callable[..., tuple[str | None, str, dict[str, float]]],
    report_builder: Callable[..., list[dict[str, float | str | bool]]],
    summary_builder: Callable[..., str],
    unavailable_summary_builder: Callable[[str], str],
) -> tuple[
    str | None,
    str,
    tuple[str, ...],
    tuple[dict[str, float | str | bool], ...],
    str,
    HiddenCardInferenceModel | None,
]:
    if unavailable_reason is not None:
        return (
            None,
            unavailable_reason,
            (),
            (),
            unavailable_summary_builder(unavailable_reason),
            None,
        )
    legal_cards = tuple(
        legal_cards_builder(state.hand, state.current_trick, state.game_type)
    )
    hidden_model = hidden_model_builder(
        state,
        left_hand_size,
        right_hand_size,
        public_hand_constraints,
    )
    inference_kwargs = (
        {"hidden_card_inference_model": hidden_model}
        if hidden_model is not None
        else {}
    )
    recommended_card, reason, values = immediate_recommender(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        sample_count=sample_count,
        random_seed=random_seed,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
        public_hand_constraints=public_hand_constraints,
        **inference_kwargs,
    )
    report = report_builder(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        sample_count=sample_count,
        random_seed=random_seed,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
        public_hand_constraints=public_hand_constraints,
        precomputed_values=values or None,
        **inference_kwargs,
    )
    return (
        recommended_card,
        reason,
        legal_cards,
        tuple(report),
        summary_builder(
            report,
            game_type=state.game_type,
            player_role=state.player_role,
        ),
        hidden_model,
    )


def _coverage_text(world_coverage: str) -> str:
    return world_coverage.replace("_", " ")


def _search_details(result: BoundedSearchResult) -> str:
    consumed = result.consumed_budget
    details = (
        f"status {result.status}, stop reason {result.stop_reason}, "
        f"{consumed.completed_world_count} of {consumed.selected_world_count} selected "
        f"worlds completed, coverage {_coverage_text(result.world_coverage)}"
    )
    if result.recommended_card is None:
        return details
    candidate = next(
        item for item in result.candidate_results if item.card == result.recommended_card
    )
    metric_text = (
        f", candidate success rate {candidate.local_contract_success_rate:.3f}, "
        f"mean settlement score {candidate.mean_local_side_game_score:.2f}"
    )
    if candidate.mean_local_side_card_point_margin is not None:
        metric_text += (
            f", mean local card-point margin "
            f"{candidate.mean_local_side_card_point_margin:.2f}"
        )
    return details + metric_text


def build_search_recommendation_reason(result: BoundedSearchResult) -> str:
    """Builds deterministic Search wording without private world data."""
    details = _search_details(result)
    if result.recommended_card is None:
        return (
            f"Bounded Search returned {details}. No Search recommendation is available. "
            "The result does not claim an optimal imperfect-information policy."
        )
    return (
        f"Bounded Search recommends {result.recommended_card}: {details}. "
        "This determinization aggregate does not claim an optimal "
        "imperfect-information policy."
    )


def build_search_strategic_summary(result: BoundedSearchResult) -> str:
    """Builds the Search-specific strategic summary."""
    if result.recommended_card is None:
        return (
            "Strategic summary: Bounded Search produced no recommendation; "
            f"{_search_details(result)}."
        )
    return (
        f"Strategic summary: {result.recommended_card} is recommended by bounded "
        f"compatible-world Search; {_search_details(result)}."
    )


def build_information_set_search_recommendation_reason(
    result: dict[str, Any],
) -> str:
    """Builds deterministic privacy-safe wording for strict Information-set Search."""
    consumed = result["consumed_budget"]
    details = (
        f"status {result['status']}, stop reason {result['stop_reason']}, "
        f"{consumed['completed_world_count']} of "
        f"{consumed['selected_world_count']} selected worlds completed, "
        f"coverage {_coverage_text(result['world_coverage'])}"
    )
    scope = (
        "The controlled player uses one action per equal Information Set against "
        "supplied fixed opponent Policies. Any completion applies only to the "
        "selected World sequence. Sampling is not calibrated probability, and the "
        "Result is not an equilibrium or globally optimal Skat-play claim."
    )
    card = result["recommended_card"]
    if card is None:
        return (
            f"Information-set Search returned {details}. No recommendation is available. "
            f"{scope}"
        )
    return f"Information-set Search recommends {card}: {details}. {scope}"


def build_information_set_search_strategic_summary(
    result: dict[str, Any],
) -> str:
    card = result["recommended_card"]
    if card is None:
        return (
            "Strategic summary: Information-set Search produced no recommendation; "
            f"status {result['status']}, stop reason {result['stop_reason']}."
        )
    return (
        f"Strategic summary: {card} is recommended by Information-set Search over "
        "the selected World sequence with one controlled action per equal "
        "Information Set and supplied fixed opponent Policies."
    )


def build_auto_fallback_reason(
    search_result: BoundedSearchResult,
    immediate_reason: str,
) -> str:
    return (
        f"Auto fallback after bounded Search {_search_details(search_result)}. "
        f"Immediate expected value: {immediate_reason}"
    )


def build_auto_fallback_strategic_summary(
    search_result: BoundedSearchResult,
    immediate_summary: str,
) -> str:
    return (
        "Strategic summary: Auto used Immediate expected value after bounded Search "
        f"{_search_details(search_result)}. "
        f"{immediate_summary.removeprefix('Strategic summary: ')}"
    )


def build_auto_unavailable_reason(
    search_result: BoundedSearchResult,
    immediate_reason: str,
) -> str:
    return (
        f"Auto bounded Search returned {_search_details(search_result)}. "
        f"Immediate expected value also returned no recommendation: {immediate_reason}"
    )


def build_auto_unavailable_strategic_summary(
    search_result: BoundedSearchResult,
    immediate_summary: str,
) -> str:
    return (
        "Strategic summary: Auto produced no recommendation after bounded Search "
        f"{_search_details(search_result)}. "
        f"{immediate_summary.removeprefix('Strategic summary: ')}"
    )


def _validate_search_result_context(
    result: BoundedSearchResult,
    configuration: RecommendationMethodConfiguration,
    state: GameState,
) -> None:
    if result.search_method != COMPATIBLE_WORLD_MINIMAX_METHOD:
        raise ValueError("Search returned a result for an unexpected method.")
    if result.game_type != state.game_type:
        raise ValueError("Search returned a result for a different game type.")
    if result.requested_budget != configuration.requested_search_budget:
        raise ValueError("Search returned a result for a different requested budget.")
    if result.fallback_used or result.fallback_method is not None:
        raise ValueError("Search solver returned caller-owned fallback metadata.")


def execute_recommendation_workflow(
    *,
    configuration: RecommendationMethodConfiguration,
    state: GameState,
    declaration: GameDeclaration,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    immediate_random_seed: int | None,
    use_basic_opponent_strategy: bool,
    opponent_response_policy_by_player: dict[str, str],
    public_hand_constraints: tuple[PublicHandConstraint, ...],
    skat_visibility: str,
    immediate_unavailable_reason: str | None,
    legal_cards_builder: Callable[..., list[str]] | None = None,
    hidden_model_builder: Callable[..., HiddenCardInferenceModel | None] | None = None,
    immediate_recommender: (
        Callable[..., tuple[str | None, str, dict[str, float]]] | None
    ) = None,
    report_builder: Callable[..., list[dict[str, float | str | bool]]] | None = None,
    summary_builder: Callable[..., str] | None = None,
    unavailable_summary_builder: Callable[[str], str] | None = None,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    information_set_workflow_executor: Callable[
        ..., InformationSetSearchWorkflowResultV1
    ] | None = None,
) -> RecommendationWorkflowResult:
    """Executes Immediate, strict Search, or Search-first auto routing."""
    legal_cards_builder = legal_cards_builder or get_legal_cards
    hidden_model_builder = hidden_model_builder or build_hidden_card_inference_model
    immediate_recommender = immediate_recommender or recommend_card_by_expected_value
    report_builder = report_builder or build_card_analysis_report
    summary_builder = summary_builder or build_strategic_summary
    unavailable_summary_builder = (
        unavailable_summary_builder or build_unavailable_strategic_summary
    )
    if configuration.requested_method == IMMEDIATE_EXPECTED_VALUE_METHOD:
        card, reason, legal, report, summary, hidden_model = _run_immediate(
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            sample_count=sample_count,
            random_seed=immediate_random_seed,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=public_hand_constraints,
            unavailable_reason=immediate_unavailable_reason,
            legal_cards_builder=legal_cards_builder,
            hidden_model_builder=hidden_model_builder,
            immediate_recommender=immediate_recommender,
            report_builder=report_builder,
            summary_builder=summary_builder,
            unavailable_summary_builder=unavailable_summary_builder,
        )
        return RecommendationWorkflowResult(
            requested_method=configuration.requested_method,
            effective_method=(
                IMMEDIATE_EXPECTED_VALUE_METHOD if card is not None else NONE_EFFECTIVE_METHOD
            ),
            recommendation_card=card,
            recommendation_reason=reason,
            legal_cards=legal,
            analysis_report=report,
            analysis_report_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
            strategic_summary=summary,
            bounded_search_result=None,
            fallback_used=False,
            fallback_method=None,
            hidden_card_inference_model=hidden_model,
        )

    if configuration.requested_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        settings = configuration.information_set_search_settings
        if settings is None:
            raise ValueError("Information-set Search requires settings.")
        if effective_opponent_policy_settings is None:
            raise ValueError(
                "Information-set Search requires resolved effective opponent Policies."
            )
        information_view = build_live_search_information_view(
            state=state,
            declaration=declaration,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            skat_visibility=skat_visibility,
            public_hand_constraints=public_hand_constraints,
        )
        workflow_executor = (
            information_set_workflow_executor
            or execute_live_information_set_search_workflow_v1
        )
        information_set_workflow = workflow_executor(
            information_view=information_view,
            settings=settings,
            effective_policy_settings=effective_opponent_policy_settings,
        )
        public_result = information_set_workflow.public_result
        card = public_result["recommended_card"]
        legal_cards = (
            tuple(legal_cards_builder(state.hand, state.current_trick, state.game_type))
            if state.next_player == "me"
            else ()
        )
        return RecommendationWorkflowResult(
            requested_method=configuration.requested_method,
            effective_method=(
                INFORMATION_SET_SEARCH_EFFECTIVE_METHOD
                if card is not None
                else NONE_EFFECTIVE_METHOD
            ),
            recommendation_card=card,
            recommendation_reason=build_information_set_search_recommendation_reason(
                public_result
            ),
            legal_cards=legal_cards,
            analysis_report=(),
            analysis_report_method=NONE_ANALYSIS_REPORT_METHOD,
            strategic_summary=build_information_set_search_strategic_summary(
                public_result
            ),
            bounded_search_result=None,
            fallback_used=False,
            fallback_method=None,
            information_set_search_result=information_set_workflow.result,
            information_set_search_public_result=public_result,
            information_set_search_workflow=information_set_workflow,
        )

    if configuration.requested_search_budget is None:
        raise ValueError("Search recommendation requires a requested budget.")
    if configuration.search_random_seed is None:
        raise ValueError("Search recommendation requires an explicit Search seed.")
    information_view = build_live_search_information_view(
        state=state,
        declaration=declaration,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        skat_visibility=skat_visibility,
        public_hand_constraints=public_hand_constraints,
    )
    search_result = solve_compatible_world_minimax(
        information_view=information_view,
        requested_budget=configuration.requested_search_budget,
        random_seed=configuration.search_random_seed,
    )
    if not isinstance(search_result, BoundedSearchResult):
        raise ValueError("Search returned an invalid bounded-search result.")
    _validate_search_result_context(search_result, configuration, state)
    legal_cards = (
        tuple(legal_cards_builder(state.hand, state.current_trick, state.game_type))
        if state.next_player == "me"
        else ()
    )
    if search_result.recommended_card is not None:
        return RecommendationWorkflowResult(
            requested_method=configuration.requested_method,
            effective_method=COMPATIBLE_WORLD_MINIMAX_METHOD,
            recommendation_card=search_result.recommended_card,
            recommendation_reason=build_search_recommendation_reason(search_result),
            legal_cards=legal_cards,
            analysis_report=(),
            analysis_report_method=NONE_ANALYSIS_REPORT_METHOD,
            strategic_summary=build_search_strategic_summary(search_result),
            bounded_search_result=search_result,
            fallback_used=False,
            fallback_method=None,
        )
    if configuration.requested_method == BOUNDED_SEARCH_METHOD:
        return RecommendationWorkflowResult(
            requested_method=configuration.requested_method,
            effective_method=NONE_EFFECTIVE_METHOD,
            recommendation_card=None,
            recommendation_reason=build_search_recommendation_reason(search_result),
            legal_cards=legal_cards,
            analysis_report=(),
            analysis_report_method=NONE_ANALYSIS_REPORT_METHOD,
            strategic_summary=build_search_strategic_summary(search_result),
            bounded_search_result=search_result,
            fallback_used=False,
            fallback_method=None,
        )

    card, immediate_reason, immediate_legal, report, immediate_summary, hidden_model = (
        _run_immediate(
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            sample_count=sample_count,
            random_seed=immediate_random_seed,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=public_hand_constraints,
            unavailable_reason=immediate_unavailable_reason,
            legal_cards_builder=legal_cards_builder,
            hidden_model_builder=hidden_model_builder,
            immediate_recommender=immediate_recommender,
            report_builder=report_builder,
            summary_builder=summary_builder,
            unavailable_summary_builder=unavailable_summary_builder,
        )
    )
    if card is None:
        return RecommendationWorkflowResult(
            requested_method=configuration.requested_method,
            effective_method=NONE_EFFECTIVE_METHOD,
            recommendation_card=None,
            recommendation_reason=build_auto_unavailable_reason(
                search_result,
                immediate_reason,
            ),
            legal_cards=immediate_legal,
            analysis_report=report,
            analysis_report_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
            strategic_summary=build_auto_unavailable_strategic_summary(
                search_result,
                immediate_summary,
            ),
            bounded_search_result=search_result,
            fallback_used=False,
            fallback_method=None,
            hidden_card_inference_model=hidden_model,
        )
    marked_search_result = mark_bounded_search_fallback_used(search_result)
    return RecommendationWorkflowResult(
        requested_method=configuration.requested_method,
        effective_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
        recommendation_card=card,
        recommendation_reason=build_auto_fallback_reason(
            marked_search_result,
            immediate_reason,
        ),
        legal_cards=immediate_legal,
        analysis_report=report,
        analysis_report_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
        strategic_summary=build_auto_fallback_strategic_summary(
            marked_search_result,
            immediate_summary,
        ),
        bounded_search_result=marked_search_result,
        fallback_used=True,
        fallback_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
        hidden_card_inference_model=hidden_model,
    )


def build_recommendation_method_summary(
    result: RecommendationWorkflowResult,
) -> dict[str, str | bool | None]:
    """Builds the strict explicit-method summary."""
    return {
        "requested_method": result.requested_method,
        "effective_method": result.effective_method,
        "search_attempted": (
            result.bounded_search_result is not None
            or result.information_set_search_public_result is not None
        ),
        "fallback_used": result.fallback_used,
        "fallback_method": result.fallback_method,
        "analysis_report_method": result.analysis_report_method,
    }
