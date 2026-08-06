from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skat_ai.analysis_metadata import build_serializable_analysis_metadata
from skat_ai.analysis_report import build_card_analysis_report, build_strategic_summary
from skat_ai.application.contracts import PositionAnalysisApplicationOptions
from skat_ai.bounded_search_post_game_review import (
    build_bounded_search_post_game_review_summary,
)
from skat_ai.bounded_search_result import build_serializable_bounded_search_result
from skat_ai.card_selection import SEARCH_AWARE_MULTI_STEP_POLICIES
from skat_ai.declarer_card_exposure import (
    DeclarerCardExposure,
    adjudicate_accepted_declarer_card_exposure,
    build_declarer_exposed_card_evidence,
)
from skat_ai.declarer_concession import (
    adjudicate_declarer_concession,
    build_declarer_card_count_evidence,
)
from skat_ai.defender_concession import (
    DefenderConcession,
    adjudicate_defender_concession,
)
from skat_ai.defender_open_play import (
    DefenderOpenPlay,
    adjudicate_defender_open_play,
    validate_defender_open_play_context,
)
from skat_ai.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skat_ai.errors import SkatAIWorkflowError
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_continuation import (
    build_game_continuation_summary,
    resolve_game_continuation,
)
from skat_ai.game_declaration import build_serializable_game_declaration
from skat_ai.game_end import apply_remaining_points_assignment
from skat_ai.game_history import build_score_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_value import build_game_value_summary
from skat_ai.hidden_card_inference import (
    build_hidden_card_inference_model,
    build_hidden_card_inference_summary,
)
from skat_ai.impossible_null_settlement import (
    build_impossible_null_settlement_summary,
    build_serializable_impossible_null_settlement_summary,
)
from skat_ai.information_policy import build_information_policy_summary
from skat_ai.information_view import build_local_analysis_input
from skat_ai.input_loader import (
    build_game_state_from_input,
    build_local_game_state_from_input,
    build_opponent_statistics_from_document,
    build_position_from_document,
    get_actual_card_played_from_input,
    get_analysis_metadata_from_input,
    get_game_continuation_from_input,
    get_game_declaration_from_input,
    get_game_shortening_from_input,
    get_impossible_null_settlement_from_input,
    get_list_analysis_results_from_input,
    get_list_game_contributions_from_input,
    get_list_performance_input_from_input,
    get_list_standings_input_from_input,
    get_performance_rating_system_from_input,
    get_profile_preset_settings_from_input,
    get_recommendation_method_configuration_from_input,
    get_simulation_settings_from_input,
)
from skat_ai.live_opponent_profile_binding import (
    LiveOpponentProfileBindings,
    resolve_live_opponent_profile_bindings,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.open_card_throw import (
    OpenCardThrow,
    adjudicate_open_card_throw,
    resolve_open_card_throw_context,
)
from skat_ai.opponent_profile_application import (
    EffectiveLiveOpponentProfiles,
    build_opponent_profile_application_summary,
    select_effective_live_opponent_profiles,
)
from skat_ai.opponent_statistics import build_opponent_statistics_summary
from skat_ai.ouvert_simulation import (
    build_declared_ouvert_public_hand_constraint,
    resolve_effective_public_hand_constraints,
)
from skat_ai.overbid import build_overbid_summary
from skat_ai.performance_rating import (
    build_list_performance_summary,
    build_list_performance_summary_from_analysis_results,
    build_list_performance_summary_from_game_contributions,
    build_list_standings_summary,
    build_performance_rating_summary,
)
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.post_game_review import build_post_game_review_summary
from skat_ai.recommendation_workflow import (
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    SEARCH_RECOMMENDATION_METHODS,
    RecommendationMethodConfiguration,
    build_recommendation_method_summary,
    build_serializable_bounded_search_settings,
    execute_recommendation_workflow,
)
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.result_serialization import (
    build_serializable_multi_step_result,
    build_serializable_policy_comparison_result,
)
from skat_ai.rules import get_legal_cards

IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON = (
    "Immediate analysis is unavailable because the local player is not next."
)
IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON = (
    "Immediate analysis is unavailable because the game is complete."
)


def get_immediate_unavailable_reason(
    state_next_player: str,
    game_end_reason: str,
    has_game_shortening: bool = False,
) -> str | None:
    """Returns why Immediate Analysis is unavailable, if it is unavailable."""
    if game_end_reason != "not_ended" or has_game_shortening:
        return IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON
    if state_next_player != "me":
        return IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON
    return None


def build_unavailable_strategic_summary(reason: str) -> str:
    """Builds a readable strategic summary for unavailable Immediate Analysis."""
    return f"Strategic summary: {reason}"


@dataclass(frozen=True, slots=True)
class PositionWorkflowDependencies:
    """Legacy patch seams for Position Analysis orchestration."""

    immediate_recommender: Callable[..., Any] = recommend_card_by_expected_value
    report_builder: Callable[..., Any] = build_card_analysis_report
    strategic_summary_builder: Callable[..., Any] = build_strategic_summary
    unavailable_summary_builder: Callable[..., Any] = (
        build_unavailable_strategic_summary
    )
    multi_step_simulator: Callable[..., Any] = simulate_multiple_steps
    policy_comparator: Callable[..., Any] = compare_multi_step_policies


_DEFAULT_DEPENDENCIES = PositionWorkflowDependencies()


def _apply_overrides(
    settings: dict[str, Any],
    options: PositionAnalysisApplicationOptions,
) -> dict[str, Any]:
    updated_settings = settings.copy()
    if options.sample_count_override is not None:
        updated_settings["sample_count"] = options.sample_count_override
    if options.random_seed_override is not None:
        updated_settings["random_seed"] = options.random_seed_override
    if options.opponent_strategy_override == "basic":
        updated_settings["use_basic_opponent_strategy"] = True
    if options.opponent_strategy_override == "random":
        updated_settings["use_basic_opponent_strategy"] = False
    return updated_settings


def _apply_profile_preset_override(
    settings: dict[str, bool],
    options: PositionAnalysisApplicationOptions,
) -> dict[str, bool]:
    updated_settings = settings.copy()
    if options.use_profile_presets_override:
        updated_settings["use_profile_presets"] = True
    return updated_settings


def _build_effective_opponent_policy_settings(
    data: dict[str, Any],
    analysis_metadata: Any,
    options: PositionAnalysisApplicationOptions,
    effective_live_profiles: EffectiveLiveOpponentProfiles | None = None,
) -> EffectiveOpponentPolicySettings:
    return build_effective_opponent_policy_settings(
        data=data,
        left_player_profile=(
            effective_live_profiles.left
            if effective_live_profiles is not None
            else analysis_metadata.left_player_profile
        ),
        right_player_profile=(
            effective_live_profiles.right
            if effective_live_profiles is not None
            else analysis_metadata.right_player_profile
        ),
        opponent_policy_preset_override=options.opponent_policy_preset_override,
        opponent_lead_policy_override=options.opponent_lead_policy_override,
        opponent_response_policy_override=options.opponent_response_policy_override,
        use_profile_presets_override=options.use_profile_presets_override,
        left_opponent_lead_policy_override=(
            options.left_opponent_lead_policy_override
        ),
        left_opponent_response_policy_override=(
            options.left_opponent_response_policy_override
        ),
        right_opponent_lead_policy_override=(
            options.right_opponent_lead_policy_override
        ),
        right_opponent_response_policy_override=(
            options.right_opponent_response_policy_override
        ),
    )


def _global_policy_settings(
    settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    return {
        "opponent_lead_policy": settings.global_lead_policy,
        "opponent_response_policy": settings.global_response_policy,
    }


def _left_policy_settings(
    settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    return {
        "opponent_lead_policy": settings.left_lead_policy,
        "opponent_response_policy": settings.left_response_policy,
    }


def _right_policy_settings(
    settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    return {
        "opponent_lead_policy": settings.right_lead_policy,
        "opponent_response_policy": settings.right_response_policy,
    }


def _resolve_multi_step_card_selection_policy(
    explicit_policy: str | None,
    recommendation_configuration: RecommendationMethodConfiguration,
) -> str:
    configured_search_method = (
        recommendation_configuration.requested_method
        if recommendation_configuration.requested_method
        in SEARCH_RECOMMENDATION_METHODS
        else None
    )
    if configured_search_method is not None:
        if explicit_policy is not None and explicit_policy != configured_search_method:
            raise ValueError(
                "Explicit --card-policy conflicts with the configured Search "
                f"recommendation method {configured_search_method}."
            )
        return configured_search_method
    if explicit_policy in SEARCH_AWARE_MULTI_STEP_POLICIES:
        raise ValueError(
            "A Search-aware --card-policy requires matching recommendation_method "
            "and bounded_search_settings."
        )
    return explicit_policy or "first_legal"


def _build_position_analysis_result(
    data: dict[str, Any],
    *,
    input_reference: str,
    options: PositionAnalysisApplicationOptions,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    opponent_profile_application_summary: dict[str, Any] | None = None,
    dependencies: PositionWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    local_data = build_local_analysis_input(data)
    state = build_game_state_from_input(local_data)
    settings = get_simulation_settings_from_input(data)
    recommendation_configuration = get_recommendation_method_configuration_from_input(
        data
    )
    analysis_metadata = get_analysis_metadata_from_input(data)
    if effective_opponent_policy_settings is None:
        effective_opponent_policy_settings = _build_effective_opponent_policy_settings(
            data,
            analysis_metadata,
            options,
        )
    opponent_response_policy_by_player = (
        effective_opponent_policy_settings.immediate_response_policy_by_player
    )
    actual_card_played = get_actual_card_played_from_input(data)
    game_shortening = get_game_shortening_from_input(data)
    game_continuation = get_game_continuation_from_input(data)
    continuation_context = (
        resolve_game_continuation(data, game_continuation)
        if game_continuation is not None
        else None
    )
    declared_ouvert_constraint = build_declared_ouvert_public_hand_constraint(data)
    public_hand_constraints = resolve_effective_public_hand_constraints(
        tuple(
            constraint
            for constraint in (
                declared_ouvert_constraint,
                (
                    continuation_context.public_hand_constraint
                    if continuation_context is not None
                    else None
                ),
            )
            if constraint is not None
        )
    )
    game_declaration = get_game_declaration_from_input(
        data if game_shortening is not None else local_data
    )
    impossible_null_selection = get_impossible_null_settlement_from_input(data)
    performance_rating_system = get_performance_rating_system_from_input(data)
    list_performance_input = get_list_performance_input_from_input(data)
    list_game_contributions = get_list_game_contributions_from_input(data)
    list_analysis_results = get_list_analysis_results_from_input(data)
    list_standings_input = get_list_standings_input_from_input(data)
    game_value_summary = build_game_value_summary(game_declaration)
    impossible_null_summary = (
        build_impossible_null_settlement_summary(
            selection=impossible_null_selection,
            original_declaration=game_declaration,
        )
        if impossible_null_selection is not None
        else None
    )
    serializable_impossible_null_summary = (
        build_serializable_impossible_null_settlement_summary(
            impossible_null_summary
        )
    )
    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=game_declaration.bid_value,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
        impossible_null_settlement=serializable_impossible_null_summary,
    )
    opponent_policy_settings = _global_policy_settings(
        effective_opponent_policy_settings
    )
    left_opponent_policy_settings = _left_policy_settings(
        effective_opponent_policy_settings
    )
    right_opponent_policy_settings = _right_policy_settings(
        effective_opponent_policy_settings
    )
    profile_preset_settings = get_profile_preset_settings_from_input(data)
    settings = _apply_overrides(settings, options)
    profile_preset_settings = _apply_profile_preset_override(
        profile_preset_settings,
        options,
    )
    immediate_unavailable_reason = get_immediate_unavailable_reason(
        state_next_player=state.next_player,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
        has_game_shortening=game_shortening is not None,
    )

    recommendation_workflow = execute_recommendation_workflow(
        configuration=recommendation_configuration,
        state=state,
        declaration=game_declaration,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        sample_count=settings["sample_count"],
        immediate_random_seed=settings["random_seed"],
        use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
        opponent_response_policy_by_player=opponent_response_policy_by_player,
        public_hand_constraints=public_hand_constraints,
        skat_visibility=analysis_metadata.strategic_metadata.skat_visibility,
        immediate_unavailable_reason=immediate_unavailable_reason,
        legal_cards_builder=get_legal_cards,
        hidden_model_builder=build_hidden_card_inference_model,
        immediate_recommender=dependencies.immediate_recommender,
        report_builder=dependencies.report_builder,
        summary_builder=dependencies.strategic_summary_builder,
        unavailable_summary_builder=dependencies.unavailable_summary_builder,
    )
    legal_cards = list(recommendation_workflow.legal_cards)
    recommended_card = recommendation_workflow.recommendation_card
    reason = recommendation_workflow.recommendation_reason
    report = list(recommendation_workflow.analysis_report)
    strategic_summary = recommendation_workflow.strategic_summary
    hidden_card_inference_model = recommendation_workflow.hidden_card_inference_model

    bounded_search_post_game_review_summary = None
    immediate_review_report = report
    if (
        recommendation_configuration.requested_method
        in SEARCH_RECOMMENDATION_METHODS
        and analysis_metadata.strategic_metadata.analysis_mode == "post_game_review"
        and actual_card_played is not None
    ):
        immediate_baseline = execute_recommendation_workflow(
            configuration=RecommendationMethodConfiguration(
                explicitly_supplied=True,
                requested_method=IMMEDIATE_EXPECTED_VALUE_METHOD,
            ),
            state=state,
            declaration=game_declaration,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            sample_count=settings["sample_count"],
            immediate_random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=public_hand_constraints,
            skat_visibility=analysis_metadata.strategic_metadata.skat_visibility,
            immediate_unavailable_reason=immediate_unavailable_reason,
            legal_cards_builder=get_legal_cards,
            hidden_model_builder=build_hidden_card_inference_model,
            immediate_recommender=dependencies.immediate_recommender,
            report_builder=dependencies.report_builder,
            summary_builder=dependencies.strategic_summary_builder,
            unavailable_summary_builder=dependencies.unavailable_summary_builder,
        )
        immediate_review_report = list(immediate_baseline.analysis_report)
        if recommendation_workflow.bounded_search_result is None:
            raise ValueError(
                "Post-game Search review requires a bounded Search result."
            )
        bounded_search_post_game_review_summary = (
            build_bounded_search_post_game_review_summary(
                search_result=recommendation_workflow.bounded_search_result,
                actual_card=actual_card_played,
                immediate_card=immediate_baseline.recommendation_card,
                immediate_analysis_report=immediate_review_report,
                game_type=state.game_type,
                player_role=state.player_role,
            )
        )

    post_game_review_summary = build_post_game_review_summary(
        actual_card_played=actual_card_played,
        analysis_report=immediate_review_report,
        game_type=state.game_type,
        player_role=state.player_role,
        game_value=game_value_summary["game_value"],
    )
    score_summary = build_score_summary(state)
    game_result_summary = build_game_result_summary_from_score_summary(
        score_summary=score_summary,
        game_type=state.game_type,
        completed_tricks=state.completed_tricks,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
    )
    game_shortening_summary = None
    if isinstance(game_shortening, DefenderConcession):
        adjudication = adjudicate_defender_concession(
            game_shortening=game_shortening,
            game_result_summary=game_result_summary,
            game_value_summary=game_value_summary,
            overbid_summary=overbid_summary,
            completed_tricks=state.completed_tricks,
        )
        adjusted_game_result_summary = adjudication.game_result_summary
        game_shortening_summary = adjudication.game_shortening_summary
    elif isinstance(game_shortening, DefenderOpenPlay):
        adjudication = adjudicate_defender_open_play(
            game_shortening=game_shortening,
            context=validate_defender_open_play_context(data, game_shortening),
            game_result_summary=game_result_summary,
            game_value_summary=game_value_summary,
            overbid_summary=overbid_summary,
            completed_tricks=state.completed_tricks,
        )
        adjusted_game_result_summary = adjudication.game_result_summary
        game_shortening_summary = adjudication.game_shortening_summary
    elif isinstance(game_shortening, DeclarerCardExposure):
        adjudication = adjudicate_accepted_declarer_card_exposure(
            game_shortening=game_shortening,
            game_result_summary=game_result_summary,
            game_value_summary=game_value_summary,
            overbid_summary=overbid_summary,
            completed_tricks=state.completed_tricks,
            card_evidence=build_declarer_exposed_card_evidence(data),
        )
        adjusted_game_result_summary = adjudication.game_result_summary
        game_shortening_summary = adjudication.game_shortening_summary
    elif isinstance(game_shortening, OpenCardThrow):
        adjudication = adjudicate_open_card_throw(
            game_shortening=game_shortening,
            context=resolve_open_card_throw_context(data, game_shortening),
            game_result_summary=game_result_summary,
            game_value_summary=game_value_summary,
            overbid_summary=overbid_summary,
            completed_tricks=state.completed_tricks,
        )
        adjusted_game_result_summary = adjudication.game_result_summary
        game_shortening_summary = adjudication.game_shortening_summary
    elif game_shortening is not None:
        adjudication = adjudicate_declarer_concession(
            game_shortening=game_shortening,
            game_result_summary=game_result_summary,
            game_value_summary=game_value_summary,
            overbid_summary=overbid_summary,
            evidence=build_declarer_card_count_evidence(data),
        )
        adjusted_game_result_summary = adjudication.game_result_summary
        game_shortening_summary = adjudication.game_shortening_summary
    else:
        adjusted_game_result_summary = apply_remaining_points_assignment(
            game_result_summary=game_result_summary,
            game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
        )
    final_settlement_summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=adjusted_game_result_summary,
        overbid_summary=overbid_summary,
        completed_tricks=state.completed_tricks,
        impossible_null_settlement=serializable_impossible_null_summary,
    )
    performance_rating_summary = build_performance_rating_summary(
        final_settlement_summary=final_settlement_summary,
        rating_system=performance_rating_system,
    )
    list_performance_summary = None
    list_standings_summary = None
    if list_performance_input is not None:
        list_performance_summary = build_list_performance_summary(
            list_performance_input=list_performance_input,
            rating_system=performance_rating_system,
        )
    elif list_game_contributions is not None:
        list_performance_summary = (
            build_list_performance_summary_from_game_contributions(
                game_contributions=list_game_contributions,
                rating_system=performance_rating_system,
            )
        )
    elif list_analysis_results is not None:
        list_performance_summary = (
            build_list_performance_summary_from_analysis_results(
                analysis_results=list_analysis_results,
                rating_system=performance_rating_system,
            )
        )
    elif list_standings_input is not None:
        list_standings_summary = build_list_standings_summary(
            list_standings_input=list_standings_input,
            rating_system=performance_rating_system,
        )
    information_policy_summary = build_information_policy_summary(
        analysis_mode=analysis_metadata.strategic_metadata.analysis_mode,
        skat_visibility=analysis_metadata.strategic_metadata.skat_visibility,
        game_end_reason=analysis_metadata.strategic_metadata.game_end_reason,
        public_hand_constraints=public_hand_constraints,
    )

    result = {
        "input_file": input_reference,
        "position": {
            "game_type": state.game_type,
            "player_role": state.player_role,
            "player_position": state.player_position,
            "declarer_player": state.declarer_player,
            "trick_leader": state.trick_leader,
            "hand": (
                state.hand
                if (
                    not isinstance(game_shortening, DefenderOpenPlay)
                    or game_shortening.exposing_defender == "me"
                )
                and (
                    not isinstance(game_shortening, OpenCardThrow)
                    or game_shortening.throwing_player == "me"
                )
                else []
            ),
            "current_trick": state.current_trick,
            "played_cards": state.played_cards,
            "completed_tricks": state.completed_tricks,
            "declarer_points": state.declarer_points,
            "defender_points": state.defender_points,
            "next_player": state.next_player,
            "skat": state.skat,
        },
        "settings": settings,
        "opponent_policy_settings": opponent_policy_settings,
        "left_opponent_policy_settings": left_opponent_policy_settings,
        "right_opponent_policy_settings": right_opponent_policy_settings,
        "profile_preset_settings": profile_preset_settings,
        "analysis_metadata": build_serializable_analysis_metadata(analysis_metadata),
        "information_policy_summary": information_policy_summary,
        "post_game_review_summary": post_game_review_summary,
        "game_declaration": build_serializable_game_declaration(game_declaration),
        "game_value_summary": game_value_summary,
        "overbid_summary": overbid_summary,
        "legal_cards": legal_cards,
        "analysis_report": report,
        "strategic_summary": strategic_summary,
        "score_summary": score_summary,
        "game_result_summary": game_result_summary,
        "adjusted_game_result_summary": adjusted_game_result_summary,
        "final_settlement_summary": final_settlement_summary,
        "performance_rating_summary": performance_rating_summary,
        "recommendation": {"card": recommended_card, "reason": reason},
    }
    if recommendation_configuration.explicitly_supplied:
        settings["recommendation_method"] = (
            recommendation_configuration.requested_method
        )
        settings["bounded_search_settings"] = (
            build_serializable_bounded_search_settings(
                recommendation_configuration
            )
        )
        result["recommendation_method_summary"] = (
            build_recommendation_method_summary(recommendation_workflow)
        )
        result["bounded_search_result"] = (
            build_serializable_bounded_search_result(
                recommendation_workflow.bounded_search_result
            )
            if recommendation_workflow.bounded_search_result is not None
            else None
        )
    if bounded_search_post_game_review_summary is not None:
        result["bounded_search_post_game_review_summary"] = (
            bounded_search_post_game_review_summary
        )
    if list_performance_summary is not None:
        result["list_performance_summary"] = list_performance_summary
    if list_standings_summary is not None:
        result["list_standings_summary"] = list_standings_summary
    if game_shortening_summary is not None:
        result["game_shortening_summary"] = game_shortening_summary
    if continuation_context is not None:
        result["game_continuation_summary"] = build_game_continuation_summary(
            continuation_context
        )
    if opponent_profile_application_summary is not None:
        result["opponent_profile_application_summary"] = (
            opponent_profile_application_summary
        )
    hidden_card_inference_summary = build_hidden_card_inference_summary(
        hidden_card_inference_model
    )
    if hidden_card_inference_summary is not None:
        result["hidden_card_inference_summary"] = hidden_card_inference_summary
    return result


def build_position_analysis_result(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    options: PositionAnalysisApplicationOptions,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    opponent_profile_application_summary: dict[str, Any] | None = None,
    dependencies: PositionWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Builds one Position result directly from an in-memory Root document."""
    data = build_position_from_document(root_document)
    return _build_position_analysis_result(
        data,
        input_reference=input_reference,
        options=options,
        effective_opponent_policy_settings=effective_opponent_policy_settings,
        opponent_profile_application_summary=opponent_profile_application_summary,
        dependencies=dependencies,
    )


def _validate_live_profile_options(
    data: dict[str, Any],
    options: PositionAnalysisApplicationOptions,
    has_statistics: bool,
) -> None:
    left_id = options.left_opponent_player_id
    right_id = options.right_opponent_player_id
    if not has_statistics:
        if left_id is not None or right_id is not None:
            raise SkatAIWorkflowError(
                "Opponent player IDs require injected opponent statistics."
            )
        return
    if left_id is None and right_id is None:
        raise SkatAIWorkflowError(
            "Injected opponent statistics require at least one opponent player ID."
        )
    if data.get("analysis_mode", "live_decision") != "live_decision":
        raise SkatAIWorkflowError(
            "Injected opponent statistics are supported only for "
            "analysis_mode='live_decision'."
        )
    unsupported_fields = {
        "list_performance_input",
        "list_game_contributions",
        "list_analysis_results",
        "list_standings_input",
        "impossible_null_settlement",
    }.intersection(data)
    if unsupported_fields:
        raise SkatAIWorkflowError(
            "Injected opponent statistics are not supported for this non-live "
            f"analysis workflow: {', '.join(sorted(unsupported_fields))}."
        )
    if not (
        data.get("use_profile_presets") is True
        or options.use_profile_presets_override
    ):
        raise SkatAIWorkflowError(
            "Injected opponent statistics require effective Profile Presets opt-in."
        )


def execute_position_analysis_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    options: PositionAnalysisApplicationOptions,
    opponent_statistics_document: dict[str, Any] | None = None,
    opponent_statistics_reference: str | None = None,
    dependencies: PositionWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Executes all selected Position Analysis sub-workflows without transport I/O."""
    data = build_position_from_document(root_document)
    if "game_shortening" in data and (
        options.multi_step_count is not None or options.compare_policies
    ):
        raise SkatAIWorkflowError(
            "Structured game_shortening cannot be combined with multi-step "
            "simulation or policy comparison."
        )
    shortening_value = data.get("game_shortening")
    is_open_card_throw = (
        isinstance(shortening_value, dict)
        and shortening_value.get("kind") == "open_card_throw"
    )
    if is_open_card_throw and (
        opponent_statistics_document is not None
        or options.left_opponent_player_id is not None
        or options.right_opponent_player_id is not None
    ):
        raise SkatAIWorkflowError(
            "Open card throw cannot be combined with opponent-statistics or "
            "live profile-binding options."
        )
    _validate_live_profile_options(
        data,
        options,
        opponent_statistics_document is not None,
    )

    analysis_metadata = get_analysis_metadata_from_input(data)
    recommendation_configuration = get_recommendation_method_configuration_from_input(
        data
    )
    game_continuation = get_game_continuation_from_input(data)
    continuation_context = (
        resolve_game_continuation(data, game_continuation)
        if game_continuation is not None
        else None
    )
    declared_ouvert_constraint = build_declared_ouvert_public_hand_constraint(data)
    public_hand_constraints = resolve_effective_public_hand_constraints(
        tuple(
            constraint
            for constraint in (
                declared_ouvert_constraint,
                (
                    continuation_context.public_hand_constraint
                    if continuation_context is not None
                    else None
                ),
            )
            if constraint is not None
        )
    )

    bindings: LiveOpponentProfileBindings | None = None
    effective_live_profiles: EffectiveLiveOpponentProfiles | None = None
    if opponent_statistics_document is not None:
        statistics_input = build_opponent_statistics_from_document(
            opponent_statistics_document
        )
        statistics_summary = build_opponent_statistics_summary(statistics_input)
        bindings = resolve_live_opponent_profile_bindings(
            statistics_summary,
            left_player_id=options.left_opponent_player_id,
            right_player_id=options.right_opponent_player_id,
        )
        effective_live_profiles = select_effective_live_opponent_profiles(
            data=data,
            manual_left_profile=analysis_metadata.left_player_profile,
            manual_right_profile=analysis_metadata.right_player_profile,
            bindings=bindings,
        )
    effective_settings = _build_effective_opponent_policy_settings(
        data,
        analysis_metadata,
        options,
        effective_live_profiles,
    )
    profile_summary = None
    if bindings is not None and effective_live_profiles is not None:
        profile_summary = build_opponent_profile_application_summary(
            statistics_input_file=opponent_statistics_reference,
            use_profile_presets=True,
            bindings=bindings,
            effective_profiles=effective_live_profiles,
            effective_settings=effective_settings,
        )

    result = _build_position_analysis_result(
        data,
        input_reference=input_reference,
        options=options,
        effective_opponent_policy_settings=effective_settings,
        opponent_profile_application_summary=profile_summary,
        dependencies=dependencies,
    )
    if options.multi_step_count is None:
        return result

    state = build_local_game_state_from_input(data)
    game_declaration = get_game_declaration_from_input(
        build_local_analysis_input(data)
    )
    effective_card_policy = _resolve_multi_step_card_selection_policy(
        options.card_selection_policy,
        recommendation_configuration,
    )
    settings = _apply_overrides(get_simulation_settings_from_input(data), options)
    opponent_policy_settings = _global_policy_settings(effective_settings)
    left_policy_settings = _left_policy_settings(effective_settings)
    right_policy_settings = _right_policy_settings(effective_settings)
    profile_preset_settings = _apply_profile_preset_override(
        get_profile_preset_settings_from_input(data),
        options,
    )
    result["opponent_policy_settings"] = opponent_policy_settings
    result["left_opponent_policy_settings"] = left_policy_settings
    result["right_opponent_policy_settings"] = right_policy_settings
    multi_step_result = dependencies.multi_step_simulator(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=options.multi_step_count,
        random_seed=settings["random_seed"],
        use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
        card_selection_policy=effective_card_policy,
        expected_value_sample_count=options.expected_value_sample_count,
        strict_context=options.strict_context,
        strategic_metadata=analysis_metadata.strategic_metadata,
        opponent_lead_policy=opponent_policy_settings["opponent_lead_policy"],
        opponent_response_policy=opponent_policy_settings[
            "opponent_response_policy"
        ],
        left_opponent_policy_settings=left_policy_settings,
        right_opponent_policy_settings=right_policy_settings,
        opponent_response_policy_by_player=(
            effective_settings.immediate_response_policy_by_player
        ),
        public_hand_constraints=public_hand_constraints,
        game_declaration=game_declaration,
        recommendation_configuration=(
            recommendation_configuration
            if effective_card_policy in SEARCH_AWARE_MULTI_STEP_POLICIES
            else None
        ),
    )
    result["multi_step_result"] = build_serializable_multi_step_result(
        multi_step_result
    )
    result["profile_preset_settings"] = profile_preset_settings
    if options.compare_policies:
        policy_comparison_result = dependencies.policy_comparator(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            step_count=options.multi_step_count,
            random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
            expected_value_sample_count=options.expected_value_sample_count,
            strict_context=options.strict_context,
            strategic_metadata=analysis_metadata.strategic_metadata,
            opponent_lead_policy=opponent_policy_settings[
                "opponent_lead_policy"
            ],
            opponent_response_policy=opponent_policy_settings[
                "opponent_response_policy"
            ],
            left_opponent_policy_settings=left_policy_settings,
            right_opponent_policy_settings=right_policy_settings,
            opponent_response_policy_by_player=(
                effective_settings.immediate_response_policy_by_player
            ),
            public_hand_constraints=public_hand_constraints,
            game_declaration=game_declaration,
            recommendation_configuration=(
                recommendation_configuration
                if recommendation_configuration.requested_method
                in SEARCH_RECOMMENDATION_METHODS
                else None
            ),
        )
        result["policy_comparison_result"] = (
            build_serializable_policy_comparison_result(policy_comparison_result)
        )
    return result
