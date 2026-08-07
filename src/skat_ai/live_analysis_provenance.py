from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.card_selection import VALID_MULTI_STEP_POLICIES
from skat_ai.errors import SkatAIInformationPolicyError
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceExemption,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
    build_json_pointer,
    parse_json_pointer,
    resolve_json_pointer,
)
from skat_ai.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
    enumerate_json_leaf_paths,
)
from skat_ai.field_provenance_policy import (
    InformationUseContext,
    validate_field_provenance_entry_use,
)
from skat_ai.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
)
from skat_ai.game_state import GameState
from skat_ai.information_view import is_skat_visible_to_local_player
from skat_ai.multi_step_recommendation import MultiStepRecommendationDecision
from skat_ai.ouvert_simulation import resolve_effective_public_hand_constraints
from skat_ai.public_hand_constraint import (
    DECLARED_OUVERT_SOURCE,
    DECLARER_EXPOSURE_CONTINUATION_SOURCE,
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PublicHandConstraint,
    build_serializable_public_hand_constraints,
)
from skat_ai.recommendation_workflow import (
    AUTO_METHOD,
    BOUNDED_SEARCH_METHOD,
    COMPATIBLE_WORLD_MINIMAX_METHOD,
    IMMEDIATE_EXPECTED_VALUE_METHOD,
    NONE_EFFECTIVE_METHOD,
    SEARCH_RECOMMENDATION_METHODS,
    RecommendationWorkflowResult,
)
from skat_ai.result_serialization import build_serializable_game_state
from skat_ai.search_provenance import build_bounded_search_provenance_entries
from skat_ai.strategic_metadata import StrategicMetadata, validate_strategic_metadata

LIVE_ANALYSIS_PROVENANCE_VERSION = 1

_LEGACY_RESULT_PATHS = (
    "/post_game_review_summary",
    "/bounded_search_post_game_review_summary",
    "/game_value_summary",
    "/overbid_summary",
    "/score_summary",
    "/game_result_summary",
    "/adjusted_game_result_summary",
    "/final_settlement_summary",
    "/performance_rating_summary",
    "/list_performance_summary",
    "/list_standings_summary",
    "/game_shortening_summary",
)

_TRACKED_RESULT_KEYS = {
    "input_file",
    "position",
    "settings",
    "opponent_policy_settings",
    "left_opponent_policy_settings",
    "right_opponent_policy_settings",
    "profile_preset_settings",
    "analysis_metadata",
    "information_policy_summary",
    "post_game_review_summary",
    "game_declaration",
    "game_value_summary",
    "overbid_summary",
    "legal_cards",
    "analysis_report",
    "strategic_summary",
    "score_summary",
    "game_result_summary",
    "adjusted_game_result_summary",
    "final_settlement_summary",
    "performance_rating_summary",
    "recommendation",
    "recommendation_method_summary",
    "bounded_search_result",
    "bounded_search_post_game_review_summary",
    "list_performance_summary",
    "list_standings_summary",
    "game_shortening_summary",
    "game_continuation_summary",
    "opponent_profile_application_summary",
    "hidden_card_inference_summary",
    "multi_step_result",
    "policy_comparison_result",
}


def _reference(
    reference_type: str,
    reference_id: str,
    *,
    visibility: str = "public",
    field_path: str | None = None,
) -> FieldProvenanceSourceReference:
    return FieldProvenanceSourceReference(
        reference_type=reference_type,
        reference_id=reference_id,
        field_path=field_path,
        visibility=visibility,
    )


def _entry(
    field_path: str,
    *,
    origin: str,
    visibility: str,
    derivation: str,
    decision_index: int,
    source_references: tuple[FieldProvenanceSourceReference, ...],
    dependency_paths: tuple[str, ...] = (),
    coverage_kind: str = "subtree",
) -> FieldProvenanceEntry:
    return FieldProvenanceEntry(
        field_path=field_path,
        coverage_kind=coverage_kind,
        origin=origin,
        visibility=visibility,
        available_from="current_decision",
        available_from_decision_index=decision_index,
        available_from_event_index=None,
        derivation=derivation,
        source_references=source_references,
        dependency_paths=dependency_paths,
        subject_player_id=None,
        perspective_player_id="me",
    )


def _decision_context(
    *,
    state: GameState,
    decision_index: int,
) -> InformationUseContext:
    return InformationUseContext(
        workflow="position_analysis",
        stage="decision_time",
        perspective_player_id="me",
        perspective_side=(
            "declarer" if state.player_role == "declarer" else "defenders"
        ),
        decision_index=decision_index,
        event_index=None,
    )


def _information_policy_error(path: str) -> SkatAIInformationPolicyError:
    return SkatAIInformationPolicyError(
        "Decision information is not authorized in the live information-use context.",
        path=path,
    )


def _validated_live_public_hand_constraints(
    *,
    constraints: tuple[PublicHandConstraint, ...],
    state: GameState,
    declaration: GameDeclaration,
    left_hand_size: int,
    right_hand_size: int,
) -> tuple[PublicHandConstraint, ...]:
    try:
        normalized = resolve_effective_public_hand_constraints(tuple(constraints))
    except (TypeError, ValueError) as error:
        raise _information_policy_error("/public_hand_constraints") from error
    expected_sizes = {
        "me": len(state.hand),
        "left": left_hand_size,
        "right": right_hand_size,
    }
    for constraint in normalized:
        if len(constraint.cards) != expected_sizes[constraint.player]:
            raise _information_policy_error("/public_hand_constraints")
        if constraint.source == DECLARED_OUVERT_SOURCE and (
            not declaration.ouvert or constraint.player != state.declarer_player
        ):
            raise _information_policy_error("/public_hand_constraints")
        if constraint.source == DECLARER_EXPOSURE_CONTINUATION_SOURCE and (
            constraint.player != state.declarer_player
        ):
            raise _information_policy_error("/public_hand_constraints")
        if constraint.source == DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE and (
            constraint.player == state.declarer_player
        ):
            raise _information_policy_error("/public_hand_constraints")
    return normalized


def _validate_seed_free_selection_settings(
    selection_settings: Mapping[str, object],
) -> None:
    expected_keys = {
        "sample_count",
        "use_basic_opponent_strategy",
        "opponent_response_policy_by_player",
        "bounded_search_budget",
    }
    if set(selection_settings) != expected_keys:
        raise _information_policy_error("/selection/settings")
    budget = selection_settings["bounded_search_budget"]
    expected_budget_keys = {
        "max_remaining_tricks",
        "max_depth_plies",
        "max_nodes",
        "max_selected_worlds",
        "max_sampled_worlds",
        "minimum_comparable_worlds",
        "wall_clock_timeout_ms",
    }
    if budget is not None and (
        not isinstance(budget, Mapping) or set(budget) != expected_budget_keys
    ):
        raise _information_policy_error("/selection/settings/bounded_search_budget")
    if not isinstance(selection_settings["opponent_response_policy_by_player"], Mapping):
        raise _information_policy_error(
            "/selection/settings/opponent_response_policy_by_player"
        )


def build_live_decision_provenance_attachment(
    *,
    name: str,
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    public_hand_constraints: tuple[PublicHandConstraint, ...],
    strategic_metadata: StrategicMetadata,
    game_declaration: GameDeclaration,
    decision_index: int,
    selection_method: str,
    selection_settings: Mapping[str, object],
    simulation_scope: bool,
) -> ApplicationProvenanceAttachment:
    """Builds one complete allowlisted decision-information attachment."""
    if not isinstance(state, GameState):
        raise ValueError("state must be a GameState.")
    if not isinstance(strategic_metadata, StrategicMetadata):
        raise ValueError("strategic_metadata must be StrategicMetadata.")
    try:
        validate_strategic_metadata(strategic_metadata)
    except ValueError as error:
        raise _information_policy_error("/strategic_metadata") from error
    if (
        strategic_metadata.analysis_mode != "live_decision"
        or strategic_metadata.game_end_reason != "not_ended"
    ):
        raise _information_policy_error("/strategic_metadata")
    if not isinstance(game_declaration, GameDeclaration):
        raise ValueError("game_declaration must be a GameDeclaration.")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        raise ValueError("decision_index must be a non-negative integer.")
    for path, value in (
        ("/opponent_hand_sizes/left", left_hand_size),
        ("/opponent_hand_sizes/right", right_hand_size),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise _information_policy_error(path)
    if state.skat and not is_skat_visible_to_local_player(
        state.player_role,
        state.declarer_player,
        strategic_metadata.skat_visibility,
    ):
        raise _information_policy_error("/game_state/skat")
    valid_selection_methods = {
        "immediate_expected_value",
        *SEARCH_RECOMMENDATION_METHODS,
        *VALID_MULTI_STEP_POLICIES,
    }
    if selection_method not in valid_selection_methods:
        raise _information_policy_error("/selection/method")
    if not isinstance(selection_settings, Mapping):
        raise _information_policy_error("/selection/settings")
    _validate_seed_free_selection_settings(selection_settings)
    public_hand_constraints = _validated_live_public_hand_constraints(
        constraints=public_hand_constraints,
        state=state,
        declaration=game_declaration,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
    )

    document = {
        "game_state": build_serializable_game_state(state),
        "opponent_hand_sizes": {
            "left": left_hand_size,
            "right": right_hand_size,
        },
        "public_hand_constraints": build_serializable_public_hand_constraints(
            public_hand_constraints
        ),
        "strategic_metadata": {
            "analysis_mode": strategic_metadata.analysis_mode,
            "skat_visibility": strategic_metadata.skat_visibility,
            "game_end_reason": strategic_metadata.game_end_reason,
        },
        "game_declaration": build_serializable_game_declaration(game_declaration),
        "selection": {
            "method": selection_method,
            "settings": dict(selection_settings),
        },
    }
    state_source = (
        _reference("algorithm", "multi_step_simulation")
        if simulation_scope
        else _reference("request", "position_analysis_request")
    )
    request_source = _reference("request", "position_analysis_request")
    public_event_source = (
        _reference("algorithm", "multi_step_public_state")
        if simulation_scope
        else request_source
    )
    entries: list[FieldProvenanceEntry] = []
    for field_name in (
        "game_type",
        "player_role",
        "player_position",
        "declarer_player",
    ):
        entries.append(
            _entry(
                f"/game_state/{field_name}",
                origin="validated_copy",
                visibility="public",
                derivation="validated",
                decision_index=decision_index,
                source_references=(state_source,),
            )
        )
    entries.append(
        _entry(
            "/game_state/hand",
            origin="validated_copy",
            visibility="local_private",
            derivation="validated",
            decision_index=decision_index,
            source_references=(state_source,),
        )
    )
    for field_name in (
        "current_trick",
        "played_cards",
        "completed_tricks",
        "declarer_points",
        "defender_points",
        "next_player",
        "trick_leader",
    ):
        entries.append(
            _entry(
                f"/game_state/{field_name}",
                origin="public_game_event",
                visibility="public",
                derivation="direct",
                decision_index=decision_index,
                source_references=(public_event_source,),
            )
        )
    exemptions: tuple[FieldProvenanceExemption, ...] = ()
    if state.skat:
        entries.append(
            _entry(
                "/game_state/skat",
                origin="validated_copy",
                visibility="local_private",
                derivation="validated",
                decision_index=decision_index,
                source_references=(state_source,),
            )
        )
    else:
        exemptions = (
            FieldProvenanceExemption(
                field_path="/game_state/skat",
                coverage_kind="subtree",
                reason="not_applicable",
            ),
        )
    entries.extend(
        (
            _entry(
                "/opponent_hand_sizes",
                origin="public_game_event",
                visibility="public",
                derivation="direct",
                decision_index=decision_index,
                source_references=(public_event_source,),
            ),
            _entry(
                "/public_hand_constraints",
                origin="public_game_event",
                visibility="public",
                derivation="direct",
                decision_index=decision_index,
                source_references=(
                    _reference("rule_contract", "authorized_public_hand_constraints"),
                ),
            ),
            _entry(
                "/strategic_metadata",
                origin="validated_copy",
                visibility="public",
                derivation="validated",
                decision_index=decision_index,
                source_references=(request_source,),
            ),
            _entry(
                "/game_declaration",
                origin="validated_copy",
                visibility="public",
                derivation="validated",
                decision_index=decision_index,
                source_references=(request_source,),
            ),
            _entry(
                "/selection",
                origin="validated_copy",
                visibility="public",
                derivation="validated",
                decision_index=decision_index,
                source_references=(request_source,),
            ),
        )
    )
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=tuple(entries),
        exemptions=exemptions,
        limitations=(),
    )
    coverage = build_field_provenance_coverage_summary(document, ledger)
    context = _decision_context(state=state, decision_index=decision_index)
    for provenance_entry in ledger.entries:
        validate_field_provenance_entry_use(provenance_entry, context)
    return ApplicationProvenanceAttachment(
        name=name,
        document_role="consumed_input",
        document=document,
        ledger=ledger,
        coverage_summary=coverage,
        information_use_context=context,
    )


def _is_at_or_below(path: str, ancestor: str) -> bool:
    return ancestor == "" or path == ancestor or path.startswith(f"{ancestor}/")


def _visible_position_dependencies(leaf_paths: tuple[str, ...]) -> tuple[str, ...]:
    ancestors = (
        "/position",
        "/settings",
        "/opponent_policy_settings",
        "/left_opponent_policy_settings",
        "/right_opponent_policy_settings",
        "/information_policy_summary/public_hand_constraints",
        "/legal_cards",
    )
    return tuple(
        path
        for path in leaf_paths
        if any(_is_at_or_below(path, ancestor) for ancestor in ancestors)
    )


def _external_reference(
    opaque_reference: str | None,
) -> tuple[FieldProvenanceSourceReference, ...]:
    if opaque_reference is None:
        return ()
    reference_id = opaque_reference
    if not reference_id or reference_id != reference_id.strip():
        digest = hashlib.sha256(reference_id.encode("utf-8")).hexdigest()
        reference_id = f"external-reference-sha256:{digest}"
    return (
        _reference(
            "external_record",
            reference_id,
            visibility="engine_private",
        ),
    )


def _profile_dependencies_by_side(
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    summary = result.get("opponent_profile_application_summary")
    if not isinstance(summary, Mapping):
        return {}
    dependencies: dict[str, tuple[str, ...]] = {}
    for side in ("left", "right"):
        side_summary = summary.get(side)
        if not isinstance(side_summary, Mapping):
            continue
        if side_summary.get("application_status") != "applied":
            continue
        prefix = f"/opponent_profile_application_summary/{side}"
        dependencies[side] = tuple(
            path for path in leaf_paths if _is_at_or_below(path, prefix)
        )
    return dependencies


def _result_decision_index(
    result: Mapping[str, object],
    path: str,
    tokens: tuple[str, ...],
) -> int:
    if tokens[0] == "multi_step_result":
        if len(tokens) >= 3 and tokens[1] == "steps" and tokens[2].isdecimal():
            step = resolve_json_pointer(
                result,
                build_json_pointer(tokens[:3]),
            )
            if isinstance(step, Mapping) and type(step.get("step_index")) is int:
                return step["step_index"]
        stopped = result.get("multi_step_result")
        if (
            "stopped_recommendation_decision" in tokens
            and isinstance(stopped, Mapping)
        ):
            decision = stopped.get("stopped_recommendation_decision")
            if isinstance(decision, Mapping) and type(decision.get("step_index")) is int:
                return decision["step_index"]
    if tokens[0] == "policy_comparison_result" and "search_decision_diagnostics" in tokens:
        diagnostic = _find_mapping_ancestor(
            result,
            path,
            "search_decision_diagnostics",
        )
        if isinstance(diagnostic, Mapping) and type(diagnostic.get("step_index")) is int:
            return diagnostic["step_index"]
    return 0


def _recommendation_origin(result: Mapping[str, object]) -> tuple[str, str]:
    summary = result.get("recommendation_method_summary")
    if isinstance(summary, Mapping):
        requested_method = summary.get("requested_method")
        effective_method = summary.get("effective_method")
        if requested_method == BOUNDED_SEARCH_METHOD or (
            requested_method == AUTO_METHOD
            and effective_method == COMPATIBLE_WORLD_MINIMAX_METHOD
        ):
            return ("search_derived", "deterministic_rule")
    return ("heuristic_analysis", "heuristic")


def _search_recommendation_dependencies(
    result: Mapping[str, object],
    leaf_path_set: frozenset[str],
) -> tuple[str, ...]:
    search = result.get("bounded_search_result")
    if not isinstance(search, Mapping):
        return ()
    dependencies = {
        path
        for path in (
            "/bounded_search_result/status",
            "/bounded_search_result/stop_reason",
            "/bounded_search_result/world_coverage",
            "/bounded_search_result/consumed_budget/selected_world_count",
            "/bounded_search_result/consumed_budget/completed_world_count",
            "/bounded_search_result/recommended_card",
        )
        if path in leaf_path_set
    }
    recommended_card = search.get("recommended_card")
    candidate_results = search.get("candidate_results")
    if isinstance(candidate_results, (list, tuple)):
        for index, candidate in enumerate(candidate_results):
            if not isinstance(candidate, Mapping) or candidate.get("card") != recommended_card:
                continue
            for field_name in (
                "card",
                "local_contract_success_rate",
                "mean_local_side_game_score",
                "mean_local_side_card_point_margin",
            ):
                path = f"/bounded_search_result/candidate_results/{index}/{field_name}"
                if path in leaf_path_set:
                    dependencies.add(path)
            break
    return tuple(sorted(dependencies))


def _is_local_private_result_path(tokens: tuple[str, ...]) -> bool:
    if len(tokens) >= 2 and tokens[:2] in {
        ("position", "hand"),
        ("position", "skat"),
    }:
        return True
    return any(
        index + 1 < len(tokens)
        and tokens[index] in {"prepared_state", "final_state"}
        and tokens[index + 1] in {"hand", "skat"}
        for index in range(len(tokens))
    )


def _find_mapping_ancestor(
    document: Mapping[str, object],
    path: str,
    token: str,
) -> Mapping[str, object] | None:
    tokens = parse_json_pointer(path)
    if token not in tokens:
        return None
    index = len(tokens) - 1 - tuple(reversed(tokens)).index(token)
    end_index = index + 1
    if end_index < len(tokens) and tokens[end_index].isascii() and tokens[end_index].isdecimal():
        end_index += 1
    ancestor_path = build_json_pointer(tokens[:end_index])
    value = resolve_json_pointer(document, ancestor_path)
    return value if isinstance(value, Mapping) else None


def _generic_result_entry(
    *,
    path: str,
    tokens: tuple[str, ...],
    result: Mapping[str, object],
    leaf_path_set: frozenset[str],
    visible_dependencies: tuple[str, ...],
    profile_dependencies_by_side: Mapping[str, tuple[str, ...]],
    external_reference: str | None,
    decision_index: int,
) -> FieldProvenanceEntry:
    top = tokens[0]
    origin = "simulation_derived"
    visibility = "public"
    derivation = "direct"
    references = (_reference("algorithm", "live_position_analysis"),)
    dependencies: tuple[str, ...] = ()

    if _is_local_private_result_path(tokens):
        visibility = "local_private"

    if top == "input_file":
        origin = "caller_supplied"
        references = (_reference("request", "application_input_reference"),)
    elif top == "position":
        if len(tokens) >= 2 and tokens[1] in {"hand", "skat"}:
            visibility = "local_private"
        if len(tokens) >= 2 and tokens[1] in {
            "current_trick",
            "played_cards",
            "completed_tricks",
            "declarer_points",
            "defender_points",
            "next_player",
            "trick_leader",
        }:
            origin = "public_game_event"
            references = (_reference("request", "position_public_game_events"),)
        else:
            origin = "validated_copy"
            derivation = "validated"
            references = (_reference("request", "position_analysis_request"),)
    elif top in {
        "settings",
        "profile_preset_settings",
        "analysis_metadata",
        "game_declaration",
    }:
        origin = "validated_copy"
        derivation = "validated"
        references = (_reference("request", "position_analysis_request"),)
    elif top in {
        "opponent_policy_settings",
        "left_opponent_policy_settings",
        "right_opponent_policy_settings",
    }:
        origin = "heuristic_analysis"
        derivation = "heuristic"
        side = (
            "left"
            if top == "left_opponent_policy_settings"
            else "right"
            if top == "right_opponent_policy_settings"
            else None
        )
        dependencies = profile_dependencies_by_side.get(side or "", ())
        references = (
            _external_reference(external_reference)
            if dependencies
            else (_reference("algorithm", "effective_opponent_policy"),)
        )
    elif top == "information_policy_summary":
        origin = "rule_derived"
        derivation = "deterministic_rule"
        references = (_reference("rule_contract", "live_information_policy"),)
        dependencies = tuple(
            dependency
            for dependency in visible_dependencies
            if dependency.startswith("/position/")
        )
    elif top == "legal_cards":
        origin = "rule_derived"
        derivation = "deterministic_rule"
        references = (_reference("rule_contract", "legal_card_rules"),)
        dependencies = tuple(
            dependency
            for dependency in visible_dependencies
            if dependency.startswith("/position/")
        )
    elif top in {"analysis_report", "strategic_summary", "recommendation"}:
        origin, derivation = _recommendation_origin(result)
        references = (
            _reference(
                "algorithm",
                (
                    "compatible_world_minimax_v1"
                    if origin == "search_derived"
                    else "immediate_expected_value"
                ),
            ),
        )
        dependencies = visible_dependencies
        summary = result.get("recommendation_method_summary")
        requested_search = isinstance(summary, Mapping) and summary.get(
            "requested_method"
        ) in SEARCH_RECOMMENDATION_METHODS
        if origin == "search_derived" or requested_search:
            dependencies = tuple(
                sorted(
                    set(
                        (
                            *dependencies,
                            *_search_recommendation_dependencies(
                                result,
                                leaf_path_set,
                            ),
                        )
                    )
                )
            )
    elif top == "recommendation_method_summary":
        origin = "rule_derived"
        derivation = "deterministic_rule"
        references = (_reference("algorithm", "recommendation_method_routing"),)
        dependencies = tuple(
            candidate_path
            for candidate_path in (
                "/settings/recommendation_method",
                "/recommendation/card",
                "/bounded_search_result/status",
            )
            if candidate_path in leaf_path_set and candidate_path != path
        )
    elif top == "bounded_search_result":
        origin = "rule_derived"
        derivation = "deterministic_rule"
        references = (_reference("algorithm", "recommendation_method_routing"),)
    elif "hidden_card_inference_summary" in tokens:
        origin = "structural_inference"
        derivation = "exact_aggregate"
        references = (_reference("algorithm", "exact_evidence_constrained"),)
        dependencies = visible_dependencies
    elif top == "game_continuation_summary":
        origin = "public_game_event"
        derivation = "validated"
        references = (_reference("rule_contract", "authorized_public_hand_constraints"),)
    elif top == "opponent_profile_application_summary":
        origin = "external_source"
        derivation = "validated"
        references = _external_reference(external_reference)
    elif "search_decision_diagnostics" in tokens:
        diagnostic = _find_mapping_ancestor(result, path, "search_decision_diagnostics")
        origin = "search_derived"
        derivation = "direct"
        references = (_reference("algorithm", "compatible_world_minimax_v1"),)
        if isinstance(diagnostic, Mapping) and diagnostic.get("fallback_used") is True:
            if tokens[-1] == "recommendation_card":
                origin = "heuristic_analysis"
                derivation = "heuristic"
    elif "recommendation_decision" in tokens:
        decision = _find_mapping_ancestor(result, path, "recommendation_decision")
        effective_method = (
            decision.get("effective_method") if isinstance(decision, Mapping) else None
        )
        requested_method = (
            decision.get("requested_method") if isinstance(decision, Mapping) else None
        )
        uses_immediate_evidence = effective_method == IMMEDIATE_EXPECTED_VALUE_METHOD or (
            requested_method == AUTO_METHOD and effective_method == NONE_EFFECTIVE_METHOD
        )
        if uses_immediate_evidence and tokens[-1] in {
            "recommendation_card",
            "recommendation_reason",
        }:
            origin = "heuristic_analysis"
            derivation = "heuristic"
            references = (
                _reference("algorithm", "compatible_world_minimax_v1"),
                _reference("algorithm", "immediate_expected_value"),
            )
            decision_tokens = tokens[: tokens.index("recommendation_decision") + 1]
            search_status = build_json_pointer(
                (*decision_tokens, "bounded_search_result", "status")
            )
            if search_status in leaf_path_set:
                dependencies = (search_status,)
        else:
            origin = "search_derived"
            derivation = "direct"
            references = (_reference("algorithm", "compatible_world_minimax_v1"),)
    elif (
        top == "multi_step_result"
        and "summary" in tokens
        and tokens[-1]
        in {
            "requested_method",
            "decisions_attempted",
            "decisions_executed",
            "search_recommendations_used",
            "immediate_fallbacks_used",
            "no_recommendation_count",
        }
    ) or (top == "policy_comparison_result" and "recommendation_summary" in tokens):
        origin = "search_derived"
        derivation = "direct"
        references = (_reference("algorithm", "compatible_world_minimax_v1"),)
    elif top in {"multi_step_result", "policy_comparison_result"}:
        origin = "simulation_derived"
        references = (_reference("algorithm", "multi_step_simulation"),)

    if top in {"multi_step_result", "policy_comparison_result"} and tokens[-1] == "candidate_card":
        step = _find_mapping_ancestor(result, path, "steps")
        if isinstance(step, Mapping):
            decision = step.get("recommendation_decision")
            if isinstance(decision, Mapping):
                if decision.get("effective_method") == COMPATIBLE_WORLD_MINIMAX_METHOD:
                    origin = "search_derived"
                    derivation = "deterministic_rule"
                    references = (_reference("algorithm", "compatible_world_minimax_v1"),)
                elif decision.get("effective_method") == IMMEDIATE_EXPECTED_VALUE_METHOD:
                    origin = "heuristic_analysis"
                    derivation = "heuristic"
                    references = (_reference("algorithm", "immediate_expected_value"),)

    return _entry(
        path,
        origin=origin,
        visibility=visibility,
        derivation=derivation,
        decision_index=decision_index,
        source_references=references,
        dependency_paths=tuple(
            dependency for dependency in dependencies if dependency != path
        ),
        coverage_kind="field",
    )


def build_live_position_result_provenance_attachment(
    result: Mapping[str, object],
    *,
    search_entries_by_path: Mapping[str, FieldProvenanceEntry] | None = None,
    additional_entries_by_path: Mapping[str, FieldProvenanceEntry] | None = None,
    external_reference: str | None = None,
) -> ApplicationProvenanceAttachment:
    """Builds all-leaf partial-legacy provenance for the exact Position Result."""
    unknown_keys = sorted(set(result) - _TRACKED_RESULT_KEYS)
    if unknown_keys:
        raise ValueError(f"Untracked live Position Result keys: {unknown_keys}")
    leaf_paths = enumerate_json_leaf_paths(result)
    leaf_path_set = frozenset(leaf_paths)
    tokens_by_path = {path: parse_json_pointer(path) for path in leaf_paths}
    visible_dependencies = _visible_position_dependencies(leaf_paths)
    profile_dependencies = _profile_dependencies_by_side(result, leaf_paths)
    registered_additional_entries = dict(additional_entries_by_path or {})
    tracked_additional_paths = tuple(registered_additional_entries)
    present_legacy_paths = tuple(
        path
        for path in _LEGACY_RESULT_PATHS
        if path.removeprefix("/") in result
        and not any(_is_at_or_below(entry_path, path) for entry_path in tracked_additional_paths)
    )
    exemptions = tuple(
        FieldProvenanceExemption(
            field_path=path,
            coverage_kind="subtree",
            reason="legacy_untracked",
        )
        for path in present_legacy_paths
    )
    registered_search_entries = dict(search_entries_by_path or {})
    registered_entries = {**registered_search_entries}
    for additional_path, additional_entry in registered_additional_entries.items():
        if additional_path in registered_entries:
            raise ValueError(
                f"Duplicate registered Position Result provenance path: {additional_path}"
            )
        registered_entries[additional_path] = additional_entry
    for registered_path, registered_entry in registered_entries.items():
        if registered_entry.field_path != registered_path:
            raise ValueError(
                "Registered provenance key and entry path must match: "
                f"{registered_path}"
            )
    missing_registered_paths = sorted(set(registered_entries) - leaf_path_set)
    if missing_registered_paths:
        raise ValueError(
            "Registered Search provenance paths are absent from the Position Result: "
            f"{missing_registered_paths}"
        )
    entries = []
    consumed_registered_paths: set[str] = set()
    for path in leaf_paths:
        if any(_is_at_or_below(path, legacy_path) for legacy_path in present_legacy_paths):
            continue
        registered = registered_entries.get(path)
        if registered is not None:
            entries.append(registered)
            consumed_registered_paths.add(path)
            continue
        entries.append(
            _generic_result_entry(
                path=path,
                tokens=tokens_by_path[path],
                result=result,
                leaf_path_set=leaf_path_set,
                visible_dependencies=visible_dependencies,
                profile_dependencies_by_side=profile_dependencies,
                external_reference=external_reference,
                decision_index=_result_decision_index(
                    result,
                    path,
                    tokens_by_path[path],
                ),
            )
        )
    unused_registered_paths = sorted(
        set(registered_entries) - consumed_registered_paths
    )
    if unused_registered_paths:
        raise ValueError(
            "Registered Search provenance paths were not consumed: "
            f"{unused_registered_paths}"
        )
    ledger = FieldProvenanceLedger(
        status="partial_legacy",
        entries=tuple(entries),
        exemptions=exemptions,
        limitations=("legacy_untracked_fields",),
    )
    coverage = build_field_provenance_coverage_summary(result, ledger)
    context = InformationUseContext(
        workflow="position_analysis",
        stage="engine_internal",
        perspective_player_id="me",
        perspective_side=(
            "declarer"
            if result.get("position", {}).get("player_role") == "declarer"
            else "defenders"
        ),
        decision_index=max(
            (entry.available_from_decision_index or 0 for entry in ledger.entries),
            default=0,
        ),
        event_index=None,
    )
    return ApplicationProvenanceAttachment(
        name="position_result",
        document_role="result",
        document=result,
        ledger=ledger,
        coverage_summary=coverage,
        information_use_context=context,
    )


class LiveAnalysisProvenanceCollector:
    """Captures live decisions and existing aggregate Results without rerunning work."""

    def __init__(self) -> None:
        self._attachments: list[ApplicationProvenanceAttachment] = []
        self._search_entries_by_path: dict[str, FieldProvenanceEntry] = {}
        self._policy_recommendation_decisions: list[
            tuple[str, MultiStepRecommendationDecision]
        ] = []

    def _capture(
        self,
        *,
        name: str,
        state: GameState,
        left_hand_size: int,
        right_hand_size: int,
        public_hand_constraints: tuple[PublicHandConstraint, ...],
        strategic_metadata: StrategicMetadata,
        game_declaration: GameDeclaration,
        decision_index: int,
        selection_method: str,
        selection_settings: Mapping[str, object],
        simulation_scope: bool,
    ) -> None:
        attachment = build_live_decision_provenance_attachment(
            name=name,
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            public_hand_constraints=public_hand_constraints,
            strategic_metadata=strategic_metadata,
            game_declaration=game_declaration,
            decision_index=decision_index,
            selection_method=selection_method,
            selection_settings=selection_settings,
            simulation_scope=simulation_scope,
        )
        for entry in attachment.ledger.entries:
            validate_field_provenance_entry_use(
                entry,
                attachment.information_use_context,
            )
        self._attachments.append(attachment)

    def capture_flat_decision(self, **kwargs: Any) -> None:
        self._capture(name="flat_decision", simulation_scope=False, **kwargs)

    def capture_multi_step_decision(self, **kwargs: Any) -> None:
        decision_index = kwargs["decision_index"]
        self._capture(
            name=f"multi_step_decision/{decision_index}",
            simulation_scope=True,
            **kwargs,
        )

    def capture_policy_comparison_decision(self, **kwargs: Any) -> None:
        decision_index = kwargs["decision_index"]
        method = kwargs["selection_method"]
        policy_index = VALID_MULTI_STEP_POLICIES.index(method)
        self._capture(
            name=(
                f"policy_comparison_decision/{policy_index}/{method}/"
                f"{decision_index}"
            ),
            simulation_scope=True,
            **kwargs,
        )

    def retain_flat_recommendation_result(
        self,
        result: RecommendationWorkflowResult,
    ) -> None:
        if result.bounded_search_result is None:
            return
        self._register_search_result(
            "/bounded_search_result",
            result.bounded_search_result,
            decision_index=0,
        )

    def retain_multi_step_result(self, result: Mapping[str, object]) -> None:
        for output_index, step in enumerate(result.get("steps", ())):
            if not isinstance(step, Mapping):
                continue
            decision = step.get("recommendation_decision")
            if isinstance(decision, MultiStepRecommendationDecision):
                self._register_search_result(
                    (
                        f"/multi_step_result/steps/{output_index}/"
                        "recommendation_decision/bounded_search_result"
                    ),
                    decision.bounded_search_result,
                    decision_index=decision.step_index,
                )
        stopped = result.get("stopped_recommendation_decision")
        if isinstance(stopped, MultiStepRecommendationDecision):
            self._register_search_result(
                "/multi_step_result/stopped_recommendation_decision/bounded_search_result",
                stopped.bounded_search_result,
                decision_index=stopped.step_index,
            )

    def retain_policy_comparison_recommendation_decision(
        self,
        policy: str,
        decision: MultiStepRecommendationDecision,
    ) -> None:
        if not isinstance(decision, MultiStepRecommendationDecision):
            raise ValueError("Policy Comparison observer requires a recommendation decision.")
        self._policy_recommendation_decisions.append((policy, decision))

    def _register_search_result(
        self,
        path: str,
        result: object,
        *,
        decision_index: int,
    ) -> None:
        for entry in build_bounded_search_provenance_entries(
            result,
            field_path=path,
            decision_index=decision_index,
        ):
            if entry.field_path in self._search_entries_by_path:
                raise ValueError(f"Duplicate Search provenance path: {entry.field_path}")
            self._search_entries_by_path[entry.field_path] = entry

    def _register_policy_search_diagnostics(
        self,
        result: Mapping[str, object],
    ) -> None:
        comparison = result.get("policy_comparison_result")
        if not isinstance(comparison, Mapping):
            return
        policy_results = comparison.get("policy_results")
        if not isinstance(policy_results, (list, tuple)):
            return
        decisions_by_policy: dict[str, list[MultiStepRecommendationDecision]] = {}
        for policy, decision in self._policy_recommendation_decisions:
            decisions_by_policy.setdefault(policy, []).append(decision)
        for policy_index, policy_result in enumerate(policy_results):
            if not isinstance(policy_result, Mapping):
                continue
            policy = policy_result.get("policy")
            diagnostics = policy_result.get("search_decision_diagnostics")
            decisions = decisions_by_policy.get(policy, ())
            if not isinstance(diagnostics, (list, tuple)) or len(diagnostics) != len(decisions):
                continue
            for diagnostic_index, (diagnostic, decision) in enumerate(
                zip(diagnostics, decisions, strict=True)
            ):
                if not isinstance(diagnostic, Mapping):
                    continue
                prefix = (
                    f"/policy_comparison_result/policy_results/{policy_index}/"
                    f"search_decision_diagnostics/{diagnostic_index}"
                )
                search = decision.bounded_search_result
                for relative_path in enumerate_json_leaf_paths(diagnostic):
                    path = f"{prefix}{relative_path}"
                    field_name = parse_json_pointer(relative_path)[-1]
                    origin = "search_derived"
                    derivation = "direct"
                    references = (_reference("algorithm", search.search_method),)
                    if field_name in {"selected_world_count", "completed_world_count"} and (
                        search.consumed_budget.completed_world_count > 0
                    ):
                        origin = "compatible_world_aggregate"
                        derivation = (
                            "sampled_aggregate"
                            if search.world_coverage == "sampled_compatible_worlds"
                            else "exact_aggregate"
                        )
                    elif (
                        field_name == "recommendation_card"
                        and (
                            decision.effective_method == IMMEDIATE_EXPECTED_VALUE_METHOD
                            or (
                                decision.requested_method == AUTO_METHOD
                                and decision.effective_method == NONE_EFFECTIVE_METHOD
                            )
                        )
                    ):
                        origin = "heuristic_analysis"
                        derivation = "heuristic"
                        references = (
                            _reference("algorithm", search.search_method),
                            _reference("algorithm", "immediate_expected_value"),
                        )
                    self._search_entries_by_path[path] = _entry(
                        path,
                        origin=origin,
                        visibility="public",
                        derivation=derivation,
                        decision_index=decision.step_index,
                        source_references=references,
                        coverage_kind="field",
                    )

    def build_bundle(
        self,
        result: Mapping[str, object],
        *,
        external_reference: str | None,
    ) -> ApplicationProvenanceBundle:
        self._register_policy_search_diagnostics(result)
        result_attachment = build_live_position_result_provenance_attachment(
            result,
            search_entries_by_path=self._search_entries_by_path,
            external_reference=external_reference,
        )
        return ApplicationProvenanceBundle(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            attachments=(*self._attachments, result_attachment),
        )
