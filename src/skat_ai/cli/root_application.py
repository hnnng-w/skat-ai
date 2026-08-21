"""Root CLI application option and position-analysis helpers."""

from typing import Any

from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    PositionAnalysisApplicationOptions,
)
from skat_ai.application.execution import (
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.application.position_workflow import build_position_analysis_result
from skat_ai.card_selection import SEARCH_AWARE_MULTI_STEP_POLICIES
from skat_ai.cli.root_compatibility import (
    _facade_value,
    _legacy_patch_value,
    build_legacy_application_dependencies,
)
from skat_ai.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skat_ai.input_loader import load_position_from_json
from skat_ai.opponent_profile_application import EffectiveLiveOpponentProfiles
from skat_ai.recommendation_workflow import RecommendationMethodConfiguration

IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON = (
    "Immediate analysis is unavailable because the local player is not next."
)
IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON = (
    "Immediate analysis is unavailable because the game is complete."
)


def execute_legacy_application(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    options: ApplicationExecutionOptions | None = None,
    external_documents: ApplicationExternalDocuments | None = None,
    include_provenance: bool = False,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Executes one Root document and thaws its result and artifacts for transport."""
    invocation = build_application_invocation(
        root_document,
        input_reference=input_reference,
        options=options,
        external_documents=external_documents,
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=build_legacy_application_dependencies(),
    )
    if include_provenance:
        from skat_ai.api.v1.schema_validation import validate_output_document
        from skat_ai.public_field_provenance import attach_public_field_provenance

        result, _public_provenance = attach_public_field_provenance(execution)
        validate_output_document(result)
    else:
        result = execution.result.to_dict()["document"]
    if not isinstance(result, dict):
        raise ValueError("Application result document must be an object.")
    artifacts = {artifact.name: artifact.to_dict() for artifact in execution.artifacts}
    return result, artifacts


def load_external_opponent_statistics_document(
    file_path: str,
) -> dict[str, Any]:
    """Loads one external statistics file through the established CLI seam."""
    statistics_input = _legacy_patch_value("load_opponent_statistics_from_json")(
        file_path
    )
    return _legacy_patch_value("build_serializable_opponent_statistics_input")(
        statistics_input
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


def apply_cli_overrides(
    settings: dict[str, Any],
    sample_count: int | None,
    random_seed: int | None,
    opponent_strategy: str | None,
) -> dict[str, Any]:
    """Applies optional command-line overrides to simulation settings."""
    updated_settings = settings.copy()

    if sample_count is not None:
        updated_settings["sample_count"] = sample_count

    if random_seed is not None:
        updated_settings["random_seed"] = random_seed

    if opponent_strategy == "basic":
        updated_settings["use_basic_opponent_strategy"] = True

    if opponent_strategy == "random":
        updated_settings["use_basic_opponent_strategy"] = False

    return updated_settings


def apply_profile_preset_cli_overrides(
    profile_preset_settings: dict[str, bool],
    use_profile_presets: bool = False,
) -> dict[str, bool]:
    """Applies CLI overrides to profile-preset settings."""
    updated_settings = profile_preset_settings.copy()

    if use_profile_presets:
        updated_settings["use_profile_presets"] = True

    return updated_settings


def build_effective_opponent_policy_settings_for_analysis(
    data: dict[str, Any],
    analysis_metadata: Any,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    effective_live_profiles: EffectiveLiveOpponentProfiles | None = None,
) -> EffectiveOpponentPolicySettings:
    """Builds shared effective opponent policy settings for one analysis invocation."""
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
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )


def build_global_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing global opponent-policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.global_lead_policy,
        "opponent_response_policy": effective_settings.global_response_policy,
    }


def build_left_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing left-opponent policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.left_lead_policy,
        "opponent_response_policy": effective_settings.left_response_policy,
    }


def build_right_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing right-opponent policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.right_lead_policy,
        "opponent_response_policy": effective_settings.right_response_policy,
    }


def resolve_multi_step_card_selection_policy(
    explicit_policy: str | None,
    recommendation_configuration: RecommendationMethodConfiguration,
) -> str:
    """Resolves CLI policy omission and explicit Search-method precedence."""
    configured_search_method = (
        recommendation_configuration.requested_method
        if recommendation_configuration.requested_method
        in SEARCH_AWARE_MULTI_STEP_POLICIES
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
            "and its matching Search settings."
        )
    return explicit_policy or "first_legal"


def build_analysis_result(
    file_path: str,
    sample_count_override: int | None = None,
    random_seed_override: int | None = None,
    opponent_strategy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    opponent_profile_application_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Builds the full analysis result as a structured dictionary."""
    loader = _facade_value("load_position_from_json", load_position_from_json)
    dependency_builder = _facade_value(
        "build_legacy_application_dependencies",
        build_legacy_application_dependencies,
    )
    data = loader(file_path)
    return build_position_analysis_result(
        data,
        input_reference=file_path,
        options=PositionAnalysisApplicationOptions(
            sample_count_override=sample_count_override,
            random_seed_override=random_seed_override,
            opponent_strategy_override=opponent_strategy_override,
            left_opponent_lead_policy_override=(
                left_opponent_lead_policy_override
            ),
            left_opponent_response_policy_override=(
                left_opponent_response_policy_override
            ),
            right_opponent_lead_policy_override=(
                right_opponent_lead_policy_override
            ),
            right_opponent_response_policy_override=(
                right_opponent_response_policy_override
            ),
            opponent_policy_preset_override=opponent_policy_preset_override,
            opponent_lead_policy_override=opponent_lead_policy_override,
            opponent_response_policy_override=opponent_response_policy_override,
            use_profile_presets_override=use_profile_presets_override,
        ),
        effective_opponent_policy_settings=effective_opponent_policy_settings,
        opponent_profile_application_summary=opponent_profile_application_summary,
        dependencies=dependency_builder().position,
    )
