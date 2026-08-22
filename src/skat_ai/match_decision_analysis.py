from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skat_ai.api.v1.schema_validation import validate_output_document
from skat_ai.application import execution as application_execution
from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    PositionAnalysisApplicationOptions,
)
from skat_ai.application.execution import (
    ApplicationWorkflowDependencies,
    build_application_invocation,
)
from skat_ai.application.position_workflow import (
    _build_effective_opponent_policy_settings,
)
from skat_ai.errors import SkatAIInvariantError
from skat_ai.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
)
from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshot
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
)
from skat_ai.input_loader import (
    build_opponent_statistics_from_document,
    build_position_from_document,
    get_analysis_metadata_from_input,
)
from skat_ai.live_opponent_profile_binding import (
    resolve_live_opponent_profile_bindings,
)
from skat_ai.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    MatchDecisionAnalysisResultV1,
)
from skat_ai.match_decision_review_preparation import (
    MatchDecisionOpponentProfileBindingV1,
    MatchDecisionReviewPreparationV1,
    _build_match_decision_review_preparation_from_reconstruction_v1,
)
from skat_ai.match_information_set_search import (
    build_match_information_set_search_request_fields_v1,
    reconcile_match_information_set_search_result_v1,
)
from skat_ai.match_observed_reconstruction import (
    build_match_observed_game_reconstruction_v1,
)
from skat_ai.match_player_statistics_preparation import (
    MatchPlayerStatisticsPreparationV1,
    build_match_player_statistics_preparation_v1,
)
from skat_ai.match_workspace_contracts import (
    MatchWorkspaceV1,
    _require_match_position,
    _validate_match_workspace_with_traces_v1,
)
from skat_ai.opponent_profile_application import (
    build_opponent_profile_application_summary,
    select_effective_live_opponent_profiles,
)
from skat_ai.opponent_statistics import (
    build_opponent_statistics_summary,
    build_serializable_opponent_statistics_input,
)
from skat_ai.recommendation_workflow import (
    SEARCH_RECOMMENDATION_METHODS,
    RecommendationMethodConfiguration,
    build_serializable_bounded_search_settings,
)
from skat_ai.search_budget_profiles import get_search_budget_profile

execute_application_invocation = (
    application_execution._execute_match_decision_application_invocation
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchDecisionAnalysisRequestV1:
    """One immutable prepared invocation for a selected Match Decision."""

    request: RequestDocumentV1
    application_options: ApplicationExecutionOptions
    external_documents: ApplicationExternalDocuments
    profile_binding: MatchDecisionOpponentProfileBindingV1
    input_reference: str

    def __post_init__(self) -> None:
        if (
            type(self.request) is not RequestDocumentV1
            or self.request.workflow is not WorkflowV1.POSITION_ANALYSIS
        ):
            raise ValueError("request must be one Position RequestDocumentV1.")
        if type(self.application_options) is not ApplicationExecutionOptions:
            raise ValueError("application_options must be ApplicationExecutionOptions.")
        if self.application_options.position_analysis is None:
            raise ValueError("application_options must contain Position options.")
        if type(self.external_documents) is not ApplicationExternalDocuments:
            raise ValueError("external_documents must be ApplicationExternalDocuments.")
        if type(self.profile_binding) is not MatchDecisionOpponentProfileBindingV1:
            raise ValueError("profile_binding must be MatchDecisionOpponentProfileBindingV1.")
        if (
            not isinstance(self.input_reference, str)
            or not self.input_reference
            or self.input_reference != self.input_reference.strip()
        ):
            raise ValueError("input_reference must be a non-empty string.")


@dataclass(frozen=True, slots=True)
class _SelectedDecision:
    preparation: MatchDecisionReviewPreparationV1
    snapshot: HistoricalDecisionSnapshot
    profile_binding: MatchDecisionOpponentProfileBindingV1
    statistics_preparation: MatchPlayerStatisticsPreparationV1


@dataclass(frozen=True, slots=True)
class _DecisionUnavailable(Exception):
    reason: str
    game_id: str | None
    skipped_reason: str | None = None


def _select_match_prepared_decision_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    decision_index: int,
) -> _SelectedDecision:
    validated_traces = dict(_validate_match_workspace_with_traces_v1(workspace))
    _require_match_position(match_position)
    if type(decision_index) is not int or decision_index <= 0:
        raise ValueError("decision_index must be a positive integer.")
    slot = workspace.slots[match_position - 1]
    if slot.observed_game is None:
        raise _DecisionUnavailable("slot_not_observed_game", None)

    statistics = build_match_player_statistics_preparation_v1(workspace.match_definition)
    reconstruction = build_match_observed_game_reconstruction_v1(
        slot.observed_game,
        validated_trace=validated_traces[match_position],
    )
    preparation = _build_match_decision_review_preparation_from_reconstruction_v1(
        reconstruction,
        source_played_at=workspace.match_definition.played_at,
        statistics_preparation=statistics,
    )
    snapshot = next(
        (item for item in preparation.snapshots if item.decision_index == decision_index),
        None,
    )
    binding = next(
        (item for item in preparation.profile_bindings if item.decision_index == decision_index),
        None,
    )
    skipped = next(
        (item for item in preparation.skipped_decisions if item.decision_index == decision_index),
        None,
    )
    if snapshot is None:
        if skipped is not None:
            raise _DecisionUnavailable(
                "decision_not_preparable",
                preparation.game_id,
                skipped.reason,
            )
        raise _DecisionUnavailable("decision_not_retained", preparation.game_id)
    if binding is None:
        raise SkatAIInvariantError(
            "A prepared Match Decision has no corresponding Profile binding."
        )
    return _SelectedDecision(
        preparation=preparation,
        snapshot=snapshot,
        profile_binding=binding,
        statistics_preparation=statistics,
    )


def select_match_prepared_decision_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    decision_index: int,
) -> tuple[
    MatchDecisionReviewPreparationV1,
    HistoricalDecisionSnapshot,
    MatchDecisionOpponentProfileBindingV1,
]:
    """Selects one exact prepared Decision without executing analysis."""
    try:
        selected = _select_match_prepared_decision_v1(
            workspace,
            match_position=match_position,
            decision_index=decision_index,
        )
    except _DecisionUnavailable as error:
        raise ValueError(error.reason) from error
    return (
        selected.preparation,
        selected.snapshot,
        selected.profile_binding,
    )


def _stable_to_relative(snapshot: HistoricalDecisionSnapshot) -> dict[str, str]:
    relative_map = snapshot.relative_player_map
    if set(relative_map) != {"me", "left", "right"}:
        raise SkatAIInvariantError("Prepared Decision relative mapping is incomplete.")
    if relative_map["me"] != snapshot.acting_player_id:
        raise SkatAIInvariantError("Prepared Decision actor does not map to me.")
    if len(set(relative_map.values())) != 3:
        raise SkatAIInvariantError("Prepared Decision mapping must contain three Players.")
    return {
        stable_player_id: relative_player
        for relative_player, stable_player_id in relative_map.items()
    }


def _build_position_root(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    selected: _SelectedDecision,
    options: MatchDecisionAnalysisOptionsV1,
) -> dict[str, Any]:
    snapshot = selected.snapshot
    visible = snapshot.visible_state
    stable_to_relative = _stable_to_relative(snapshot)
    observed_game = workspace.slots[match_position - 1].observed_game
    if observed_game is None or observed_game.declarer_player_id is None:
        raise SkatAIInvariantError(
            "A prepared Match Decision requires a concrete observed Declarer."
        )
    try:
        declarer_player = stable_to_relative[observed_game.declarer_player_id]
    except KeyError as error:
        raise SkatAIInvariantError(
            "The observed Declarer is absent from the prepared relative mapping."
        ) from error

    opponent_sizes = {
        item.relative_player: item.remaining_card_count for item in visible.opponent_hand_sizes
    }
    if set(opponent_sizes) != {"left", "right"}:
        raise SkatAIInvariantError(
            "Prepared Decision must retain left and right opponent hand sizes."
        )
    for item in visible.opponent_hand_sizes:
        if item.player_id != snapshot.relative_player_map[item.relative_player]:
            raise SkatAIInvariantError(
                "Prepared Decision opponent hand-size identity is inconsistent."
            )

    completed_tricks = [
        {
            "cards": [play.card for play in trick.plays],
            "players": [stable_to_relative[play.player_id] for play in trick.plays],
            "winner_player": stable_to_relative[trick.winner_player_id],
            "winner_role": trick.winner_side,
        }
        for trick in visible.completed_tricks
    ]
    current_trick = [play.card for play in visible.current_trick]
    trick_leader = (
        stable_to_relative[visible.current_trick[0].player_id] if visible.current_trick else "me"
    )
    declaration = visible.declaration
    game_declaration = GameDeclaration(
        game_type=visible.game_type,
        hand_game=declaration.hand_game,
        ouvert=declaration.ouvert,
        schneider_announced=declaration.schneider_announced,
        schwarz_announced=declaration.schwarz_announced,
        matadors=declaration.matadors,
        bid_value=declaration.bid_value,
    )
    root: dict[str, Any] = {
        "game_type": visible.game_type,
        "player_role": ("declarer" if snapshot.acting_side == "declarer" else "defender"),
        "declarer_player": declarer_player,
        "player_position": snapshot.acting_seat,
        "trick_leader": trick_leader,
        "hand": list(visible.own_hand),
        "current_trick": current_trick,
        "played_cards": [],
        "completed_tricks": completed_tricks,
        # The Position contract adds completed-trick points to these explicit
        # prior-point fields, so retained completed tricks carry this snapshot's totals.
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": list(visible.known_skat_cards),
        "skat_visibility": visible.skat_visibility,
        "left_hand_size": opponent_sizes["left"],
        "right_hand_size": opponent_sizes["right"],
        "sample_count": options.immediate_sample_count,
        "random_seed": options.immediate_random_seed,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "actual_card_played": snapshot.actual_card_played,
        "game_end_reason": "not_ended",
        "game_declaration": build_serializable_game_declaration(game_declaration),
        "recommendation_method": options.recommendation_method,
    }
    if declaration.ouvert:
        public_declarer = next(
            (
                exposure
                for exposure in visible.public_exposed_cards
                if exposure.player_id == observed_game.declarer_player_id
            ),
            None,
        )
        if public_declarer is None:
            raise SkatAIInvariantError(
                "Prepared declared-Ouvert Decision has no public Declarer hand."
            )
        root["public_declarer_cards"] = list(public_declarer.cards)
    if options.recommendation_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        root.update(build_match_information_set_search_request_fields_v1(options))
    elif options.recommendation_method in SEARCH_RECOMMENDATION_METHODS:
        configuration = RecommendationMethodConfiguration(
            explicitly_supplied=True,
            requested_method=options.recommendation_method,
            search_random_seed=options.search_random_seed,
            requested_search_budget=get_search_budget_profile(options.search_budget_profile),
        )
        root["bounded_search_settings"] = build_serializable_bounded_search_settings(configuration)
    return root


def _external_documents(
    workspace: MatchWorkspaceV1,
    selected: _SelectedDecision,
) -> ApplicationExternalDocuments:
    binding = selected.profile_binding
    bound_opponent_exists = binding.left_profile_available or binding.right_profile_available
    statistics_input = selected.statistics_preparation.opponent_statistics_input
    if statistics_input is None or not bound_opponent_exists:
        return ApplicationExternalDocuments()
    return ApplicationExternalDocuments(
        opponent_statistics_document=(
            build_serializable_opponent_statistics_input(statistics_input)
        ),
        opponent_statistics_reference=(
            f"match:{workspace.match_definition.match_id}:workspace:"
            f"{workspace.revision}:eligible-player-statistics"
        ),
    )


def _build_match_decision_position_request_from_selected_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    options: MatchDecisionAnalysisOptionsV1,
    selected: _SelectedDecision,
) -> MatchDecisionAnalysisRequestV1:
    root = _build_position_root(
        workspace,
        match_position=match_position,
        selected=selected,
        options=options,
    )
    try:
        validated_root = build_position_from_document(root)
    except SkatAIInvariantError:
        raise
    except Exception as error:
        raise SkatAIInvariantError(
            "A prepared Match Decision could not build a validated Position Request."
        ) from error
    binding = selected.profile_binding
    external_documents = _external_documents(workspace, selected)
    has_external = external_documents.opponent_statistics_document is not None
    position_options = PositionAnalysisApplicationOptions(
        sample_count_override=options.immediate_sample_count,
        random_seed_override=options.immediate_random_seed,
        use_profile_presets_override=options.use_profile_presets,
        left_opponent_player_id=(
            binding.left_opponent_player_id
            if has_external and binding.left_profile_available
            else None
        ),
        right_opponent_player_id=(
            binding.right_opponent_player_id
            if has_external and binding.right_profile_available
            else None
        ),
    )
    input_reference = (
        f"match:{workspace.match_definition.match_id}:workspace:{workspace.revision}:"
        f"position:{match_position}:decision:{selected.snapshot.decision_index}"
    )
    return MatchDecisionAnalysisRequestV1(
        request=RequestDocumentV1(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document=validated_root,
        ),
        application_options=ApplicationExecutionOptions(position_analysis=position_options),
        external_documents=external_documents,
        profile_binding=binding,
        input_reference=input_reference,
    )


def build_match_decision_position_request_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    decision_index: int,
    options: MatchDecisionAnalysisOptionsV1,
) -> MatchDecisionAnalysisRequestV1:
    """Builds one validated Position Request from one prepared Match Decision."""
    if type(options) is not MatchDecisionAnalysisOptionsV1:
        raise ValueError("options must be MatchDecisionAnalysisOptionsV1.")
    try:
        selected = _select_match_prepared_decision_v1(
            workspace,
            match_position=match_position,
            decision_index=decision_index,
        )
    except _DecisionUnavailable as error:
        raise ValueError(error.reason) from error
    return _build_match_decision_position_request_from_selected_v1(
        workspace,
        match_position=match_position,
        options=options,
        selected=selected,
    )


def _reconcile_profile_summary(
    result_document: dict[str, Any],
    prepared: MatchDecisionAnalysisRequestV1,
) -> None:
    request_document = prepared.request.to_dict()["document"]
    position_options = prepared.application_options.position_analysis
    if position_options is None:
        raise SkatAIInvariantError("Prepared Match Decision omitted Position options.")
    analysis_metadata = get_analysis_metadata_from_input(request_document)
    external_document = prepared.external_documents.opponent_statistics_to_dict()
    bindings = None
    effective_profiles = None
    if external_document is not None:
        statistics_input = build_opponent_statistics_from_document(external_document)
        bindings = resolve_live_opponent_profile_bindings(
            build_opponent_statistics_summary(statistics_input),
            left_player_id=position_options.left_opponent_player_id,
            right_player_id=position_options.right_opponent_player_id,
        )
        effective_profiles = select_effective_live_opponent_profiles(
            data=request_document,
            manual_left_profile=analysis_metadata.left_player_profile,
            manual_right_profile=analysis_metadata.right_player_profile,
            bindings=bindings,
        )
    effective_settings = _build_effective_opponent_policy_settings(
        request_document,
        analysis_metadata,
        position_options,
        effective_profiles,
    )
    expected_policies = {
        "opponent_policy_settings": {
            "opponent_lead_policy": effective_settings.global_lead_policy,
            "opponent_response_policy": effective_settings.global_response_policy,
        },
        "left_opponent_policy_settings": {
            "opponent_lead_policy": effective_settings.left_lead_policy,
            "opponent_response_policy": effective_settings.left_response_policy,
        },
        "right_opponent_policy_settings": {
            "opponent_lead_policy": effective_settings.right_lead_policy,
            "opponent_response_policy": effective_settings.right_response_policy,
        },
    }
    if any(
        result_document.get(field_name) != expected
        for field_name, expected in expected_policies.items()
    ):
        raise SkatAIInvariantError("Position Result changed effective opponent Policy settings.")

    summary = result_document.get("opponent_profile_application_summary")
    has_external = external_document is not None
    expects_summary = has_external and position_options.use_profile_presets_override
    if not expects_summary:
        if summary is not None:
            raise SkatAIInvariantError("Position Result unexpectedly contains Profile application.")
        return
    if not isinstance(summary, dict) or bindings is None or effective_profiles is None:
        raise SkatAIInvariantError(
            "Position Result omitted the requested Profile application summary."
        )
    expected_summary = build_opponent_profile_application_summary(
        statistics_input_file=(prepared.external_documents.opponent_statistics_reference),
        use_profile_presets=True,
        bindings=bindings,
        effective_profiles=effective_profiles,
        effective_settings=effective_settings,
    )
    if summary.get("statistics_input_file") != (
        prepared.external_documents.opponent_statistics_reference
    ):
        raise SkatAIInvariantError("Position Profile summary changed the statistics reference.")
    binding = prepared.profile_binding
    for side in ("left", "right"):
        side_summary = summary.get(side)
        if not isinstance(side_summary, dict):
            raise SkatAIInvariantError("Position Profile summary omitted one side.")
        expected_player_id = (
            getattr(binding, f"{side}_opponent_player_id")
            if getattr(binding, f"{side}_profile_available")
            else None
        )
        if side_summary.get("bound_player_id") != expected_player_id:
            raise SkatAIInvariantError(
                "Position Profile summary changed a stable opponent identity."
            )
        if side_summary.get("bound_player_id") == binding.acting_player_id:
            raise SkatAIInvariantError(
                "Position Profile summary bound the acting Player as an opponent."
            )
    if summary != expected_summary:
        raise SkatAIInvariantError("Position Result changed the Profile application summary.")


def execute_match_decision_analysis_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    decision_index: int,
    options: MatchDecisionAnalysisOptionsV1,
    dependencies: ApplicationWorkflowDependencies | None = None,
) -> MatchDecisionAnalysisResultV1:
    """Executes the existing Position Application once for one explicit Decision."""
    if type(workspace) is not MatchWorkspaceV1:
        raise ValueError("workspace must be a MatchWorkspaceV1.")
    if type(options) is not MatchDecisionAnalysisOptionsV1:
        raise ValueError("options must be MatchDecisionAnalysisOptionsV1.")
    match_id = workspace.match_definition.match_id
    try:
        selected = _select_match_prepared_decision_v1(
            workspace,
            match_position=match_position,
            decision_index=decision_index,
        )
    except _DecisionUnavailable as error:
        return MatchDecisionAnalysisResultV1(
            status="unavailable",
            match_id=match_id,
            workspace_revision=workspace.revision,
            match_position=match_position,
            game_id=error.game_id,
            decision_index=decision_index,
            unavailable_reason=error.reason,
            skipped_reason=error.skipped_reason,
            options=options,
            profile_binding=None,
            request=None,
            result=None,
        )
    prepared = _build_match_decision_position_request_from_selected_v1(
        workspace,
        match_position=match_position,
        options=options,
        selected=selected,
    )
    invocation = build_application_invocation(
        prepared.request.to_dict()["document"],
        input_reference=prepared.input_reference,
        options=prepared.application_options,
        external_documents=prepared.external_documents,
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=dependencies,
    )
    result = execution.result
    if result.workflow is not WorkflowV1.POSITION_ANALYSIS:
        raise SkatAIInvariantError("Match Decision execution changed workflow identity.")
    result_document = result.to_dict()["document"]
    validate_output_document(result_document)
    if result_document.get("input_file") != prepared.input_reference:
        raise SkatAIInvariantError("Match Decision Result changed input identity.")
    _reconcile_profile_summary(result_document, prepared)
    if options.recommendation_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        reconcile_match_information_set_search_result_v1(
            options=options,
            request_document=prepared.request.document,
            result_document=result_document,
        )
    return MatchDecisionAnalysisResultV1(
        status="executed",
        match_id=match_id,
        workspace_revision=workspace.revision,
        match_position=match_position,
        game_id=selected.preparation.game_id,
        decision_index=decision_index,
        unavailable_reason=None,
        skipped_reason=None,
        options=options,
        profile_binding=selected.profile_binding,
        request=prepared.request,
        result=result,
    )
