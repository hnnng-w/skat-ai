from __future__ import annotations

from collections.abc import Mapping

from skat_ai.errors import SkatAIInformationPolicyError
from skat_ai.field_provenance import FieldProvenanceEntry
from skat_ai.settlement_result_provenance import (
    COMPLETE_RESULT_PROVENANCE_VERSION as COMPLETE_RESULT_PROVENANCE_VERSION,
)
from skat_ai.settlement_result_provenance import (
    build_game_value_result_entry,
    build_overbid_result_entry,
    build_settlement_result_entry,
    leaf_paths_below,
    result_provenance_entry,
    result_source_reference,
)

POSITION_RESULT_KEYS = frozenset(
    {
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
)

_POSITION_RESULT_BRANCHES = frozenset(
    {
        "game_declaration",
        "game_value_summary",
        "overbid_summary",
        "score_summary",
        "game_result_summary",
        "adjusted_game_result_summary",
        "final_settlement_summary",
        "performance_rating_summary",
        "list_performance_summary",
        "list_standings_summary",
        "game_shortening_summary",
        "game_continuation_summary",
        "post_game_review_summary",
        "bounded_search_post_game_review_summary",
    }
)

_ENDING_RULE_REFERENCES = {
    "declarer_concession": "structured_shortening.declarer_concession",
    "defender_concession": "structured_shortening.defender_concession",
    "declarer_card_exposure": "structured_shortening.declarer_card_exposure",
    "defender_open_play": "structured_shortening.defender_open_play",
    "open_card_throw": "structured_shortening.open_card_throw",
}

_CONTINUATION_RULE_REFERENCES = {
    "declarer_card_exposure": (
        "structured_shortening.declarer_card_exposure.rejected_continuation"
    ),
    "defender_open_play": "structured_shortening.defender_open_play_continuation",
}


def _request_reference(
    field_path: str | None = None,
    *,
    visibility: str = "public",
):
    return result_source_reference(
        "request",
        "position_analysis_request",
        field_path=field_path,
        visibility=visibility,
    )


def _source_declaration_path(
    source_document: Mapping[str, object] | None,
    field_name: str,
) -> str | None:
    if source_document is None:
        return None
    if field_name in source_document:
        return f"/{field_name}"
    nested = source_document.get("game_declaration")
    if isinstance(nested, Mapping) and field_name in nested:
        return f"/game_declaration/{field_name}"
    return None


def _declaration_entry(
    path: str,
    field_name: str,
    *,
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    source_document: Mapping[str, object] | None,
) -> FieldProvenanceEntry:
    source_path = _source_declaration_path(source_document, field_name)
    if field_name == "game_type":
        source_path = "/game_type"
    if source_path is not None:
        return result_provenance_entry(
            path,
            origin="validated_copy",
            visibility="public",
            available_from="request_start",
            derivation="validated",
            source_references=(_request_reference(source_path),),
        )

    declaration = result.get("game_declaration")
    if not isinstance(declaration, Mapping):
        declaration = {}
    if field_name == "matadors" and declaration.get("matadors") is not None:
        terminal_private_inference = bool(
            source_document is not None and "game_shortening" in source_document
        )
        references = [
            result_source_reference(
                "algorithm",
                "position_matador_inference_v1",
            )
        ]
        if terminal_private_inference:
            references.append(
                result_source_reference(
                    "algorithm",
                    "private_ownership_matador_evidence_v1",
                    visibility="engine_private",
                )
            )
        return result_provenance_entry(
            path,
            origin="structural_inference",
            visibility="post_game_only" if terminal_private_inference else "public",
            available_from="game_end" if terminal_private_inference else "current_decision",
            derivation="exact_aggregate",
            source_references=tuple(references),
            dependency_paths=leaf_paths_below(
                leaf_paths,
                "/position/hand",
                "/position/skat",
                "/position/completed_tricks",
                "/information_policy_summary/public_hand_constraints",
            ),
            decision_index=None if terminal_private_inference else 0,
            perspective_player_id="me",
        )

    implied_by = None
    if declaration.get(field_name) is True:
        if field_name == "hand_game":
            implied_by = next(
                (
                    candidate
                    for candidate in (
                        "schneider_announced",
                        "schwarz_announced",
                        "ouvert",
                    )
                    if declaration.get(candidate) is True
                ),
                None,
            )
        elif field_name == "schneider_announced":
            implied_by = next(
                (
                    candidate
                    for candidate in ("schwarz_announced", "ouvert")
                    if declaration.get(candidate) is True
                ),
                None,
            )
        elif field_name == "schwarz_announced" and declaration.get("ouvert") is True:
            implied_by = "ouvert"
    if implied_by is not None:
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="public",
            available_from="request_start",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference(
                    "rule_contract",
                    "canonical_declaration_dependencies_v1",
                ),
            ),
            dependency_paths=(f"/game_declaration/{implied_by}",),
        )
    return result_provenance_entry(
        path,
        origin="defaulted",
        visibility="public",
        available_from="request_start",
        derivation="direct",
        source_references=(
            result_source_reference("algorithm", "game_declaration_defaults_v1"),
        ),
    )


def _score_entry(
    path: str,
    *,
    leaf_paths: tuple[str, ...],
) -> FieldProvenanceEntry:
    if path.endswith("explicit_declarer_points"):
        dependencies = ("/position/declarer_points",)
    elif path.endswith("explicit_defender_points"):
        dependencies = ("/position/defender_points",)
    elif path.endswith("completed_trick_declarer_points") or path.endswith(
        "completed_trick_defender_points"
    ):
        dependencies = leaf_paths_below(leaf_paths, "/position/completed_tricks")
    elif path.endswith("total_declarer_points"):
        dependencies = (
            "/score_summary/explicit_declarer_points",
            "/score_summary/completed_trick_declarer_points",
        )
    else:
        dependencies = (
            "/score_summary/explicit_defender_points",
            "/score_summary/completed_trick_defender_points",
        )
    return result_provenance_entry(
        path,
        origin="rule_derived",
        visibility="public",
        available_from="current_decision",
        derivation="deterministic_rule",
        source_references=(result_source_reference("rule_contract", "card_point_rules"),),
        dependency_paths=dependencies,
        decision_index=0,
        perspective_player_id="me",
    )


def _raw_result_entry(
    path: str,
    *,
    leaf_paths: tuple[str, ...],
) -> FieldProvenanceEntry:
    dependencies = [
        *leaf_paths_below(leaf_paths, "/score_summary"),
        "/game_declaration/game_type",
    ]
    if path.endswith(("/winner", "/is_complete", "/status")):
        dependencies.extend(
            leaf_paths_below(leaf_paths, "/position/completed_tricks")
        )
    return result_provenance_entry(
        path,
        origin="rule_derived",
        visibility="public",
        available_from="current_decision",
        derivation="deterministic_rule",
        source_references=(
            result_source_reference("rule_contract", "game_result_rules_v1"),
        ),
        dependency_paths=dependencies,
        decision_index=0,
        perspective_player_id="me",
    )


def _ending_entry(
    path: str,
    *,
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
) -> FieldProvenanceEntry:
    summary = result.get("game_shortening_summary")
    kind = summary.get("kind") if isinstance(summary, Mapping) else None
    reference_id = _ENDING_RULE_REFERENCES.get(str(kind))
    if reference_id is None:
        raise ValueError(f"Unsupported Position game_shortening_summary kind: {kind}")
    references = [result_source_reference("rule_contract", reference_id)]
    if kind == "defender_open_play" and (
        "/exact_proof/" in path
        or "/proof_" in path
        or path.endswith("/exact_proof")
    ):
        references.append(
            result_source_reference(
                "algorithm",
                "defender_open_play_exact_proof_v1",
                visibility="engine_private",
            )
        )
    return result_provenance_entry(
        path,
        origin="rule_derived",
        visibility="post_game_only",
        available_from="game_end",
        derivation="deterministic_rule",
        source_references=tuple(references),
        dependency_paths=leaf_paths_below(
            leaf_paths,
            "/game_result_summary",
            "/game_declaration",
            "/game_value_summary",
            "/overbid_summary",
            "/position/completed_tricks",
        ),
    )


def _continuation_entry(
    path: str,
    *,
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
) -> FieldProvenanceEntry:
    summary = result.get("game_continuation_summary")
    kind = summary.get("kind") if isinstance(summary, Mapping) else None
    reference_id = _CONTINUATION_RULE_REFERENCES.get(str(kind))
    if reference_id is None:
        raise ValueError(f"Unsupported Position game_continuation_summary kind: {kind}")
    return result_provenance_entry(
        path,
        origin=(
            "public_game_event"
            if path.endswith(
                (
                    "/kind",
                    "/exposure_form",
                    "/exposed_cards",
                    "/public_declarer_cards",
                    "/declarer_response",
                )
            )
            or "/cards/" in path
            else "rule_derived"
        ),
        visibility="public",
        available_from="current_decision",
        derivation=(
            "validated"
            if path.endswith(("/kind", "/exposure_form", "/declarer_response"))
            or "/cards/" in path
            else "deterministic_rule"
        ),
        source_references=(result_source_reference("rule_contract", reference_id),),
        dependency_paths=leaf_paths_below(
            leaf_paths,
            "/position",
            "/game_declaration",
            "/information_policy_summary/public_hand_constraints",
        ),
        decision_index=0,
        perspective_player_id="me",
    )


def build_position_result_branch_entry(
    *,
    path: str,
    tokens: tuple[str, ...],
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    source_document: Mapping[str, object] | None,
) -> FieldProvenanceEntry | None:
    """Builds one complete branch-specific Position Result entry when applicable."""
    top = tokens[0]
    if top not in _POSITION_RESULT_BRANCHES:
        return None
    if top == "game_declaration":
        return _declaration_entry(
            path,
            tokens[-1],
            result=result,
            leaf_paths=leaf_paths,
            source_document=source_document,
        )
    declaration_matador = result.get("game_declaration")
    terminal_inferred_value = bool(
        isinstance(declaration_matador, Mapping)
        and declaration_matador.get("matadors") is not None
        and _source_declaration_path(source_document, "matadors") is None
        and source_document is not None
        and "game_shortening" in source_document
    )
    if top == "game_value_summary":
        return build_game_value_result_entry(
            path,
            leaf_paths=leaf_paths,
            declaration_prefix="/game_declaration",
            available_from="game_end" if terminal_inferred_value else "current_decision",
            decision_index=None if terminal_inferred_value else 0,
            visibility="post_game_only" if terminal_inferred_value else "public",
        )
    if top == "overbid_summary":
        return build_overbid_result_entry(
            path,
            leaf_paths=leaf_paths,
            declaration_prefix="/game_declaration",
            game_value_prefix="/game_value_summary",
            ending_prefixes=("/analysis_metadata/strategic_metadata/game_end_reason",),
            available_from=(
                "game_end"
                if terminal_inferred_value
                or (
                    source_document is not None
                    and source_document.get("game_end_reason")
                    == "impossible_null_declaration"
                )
                else "current_decision"
            ),
            decision_index=None if terminal_inferred_value else 0,
            visibility="post_game_only" if terminal_inferred_value else "public",
        )
    if top == "score_summary":
        return _score_entry(path, leaf_paths=leaf_paths)
    if top == "game_result_summary":
        return _raw_result_entry(path, leaf_paths=leaf_paths)
    if top == "game_shortening_summary":
        return _ending_entry(path, result=result, leaf_paths=leaf_paths)
    if top == "game_continuation_summary":
        return _continuation_entry(path, result=result, leaf_paths=leaf_paths)
    if top == "adjusted_game_result_summary":
        ended = bool(
            "game_shortening_summary" in result
            or (
                isinstance(result.get("analysis_metadata"), Mapping)
                and isinstance(result["analysis_metadata"].get("strategic_metadata"), Mapping)
                and result["analysis_metadata"]["strategic_metadata"].get("game_end_reason")
                != "not_ended"
            )
        )
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="post_game_only" if ended else "public",
            available_from="game_end" if ended else "current_decision",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference(
                    "rule_contract",
                    "settlement_normative_matrix_v1",
                ),
            ),
            dependency_paths=leaf_paths_below(
                leaf_paths,
                "/game_result_summary",
                "/game_shortening_summary",
                "/game_declaration",
                "/game_value_summary",
                "/overbid_summary",
                "/analysis_metadata/strategic_metadata/game_end_reason",
            ),
            decision_index=None if ended else 0,
            perspective_player_id="me",
        )
    if top == "final_settlement_summary":
        return build_settlement_result_entry(
            path,
            leaf_paths=leaf_paths,
            result_prefix="/adjusted_game_result_summary",
            game_value_prefix="/game_value_summary",
            overbid_prefix="/overbid_summary",
            ending_prefixes=("/game_shortening_summary",),
            completed_trick_prefixes=("/position/completed_tricks",),
        )
    if top == "performance_rating_summary":
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="public",
            available_from="offline_review",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference("rule_contract", "performance_rating_v1"),
                _request_reference("/performance_rating_system"),
            ),
            dependency_paths=leaf_paths_below(
                leaf_paths,
                "/final_settlement_summary",
            ),
        )
    if top == "list_performance_summary":
        basis = result.get("list_performance_summary")
        basis_name = basis.get("basis") if isinstance(basis, Mapping) else None
        source_path = {
            "aggregated_list_or_series_totals": "/list_performance_input",
            "normalized_game_contributions": "/list_game_contributions",
            "local_analysis_results": "/list_analysis_results",
        }.get(str(basis_name))
        if source_path is None:
            raise ValueError(f"Unsupported list_performance_summary basis: {basis_name}")
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="public",
            available_from="offline_review",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference("rule_contract", "skwo_6.3.1_performance"),
                _request_reference(source_path),
            ),
        )
    if top == "list_standings_summary":
        lot_affected = (
            tokens[-1] in {"rank", "ranking_status", "applied_lot_order"}
            or "lot_required_player_ids" in tokens
            or (
                len(tokens) >= 3
                and tokens[:2] == ("list_standings_summary", "standings")
                and tokens[-1] in {"player_id", "player_label", "input_order"}
            )
        )
        references = [
            result_source_reference("rule_contract", "skwo_6.3.1_standings"),
            _request_reference("/list_standings_input"),
        ]
        if lot_affected and source_document is not None:
            standings_input = source_document.get("list_standings_input")
            if isinstance(standings_input, Mapping) and "lot_order" in standings_input:
                references.append(_request_reference("/list_standings_input/lot_order"))
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="public",
            available_from="offline_review",
            derivation="deterministic_rule",
            source_references=tuple(references),
        )
    if top in {"post_game_review_summary", "bounded_search_post_game_review_summary"}:
        actual_available = bool(
            source_document is not None
            and source_document.get("actual_card_played") is not None
        )
        return result_provenance_entry(
            path,
            origin=(
                "retrospective_attachment"
                if tokens[-1] in {"actual_card", "actual_card_played"}
                and actual_available
                else "heuristic_analysis"
            ),
            visibility="public",
            available_from="after_actual_play" if actual_available else "current_decision",
            derivation=(
                "retrospective"
                if tokens[-1] in {"actual_card", "actual_card_played"}
                and actual_available
                else "heuristic"
            ),
            source_references=(
                result_source_reference(
                    "retrospective_observation" if actual_available else "algorithm",
                    "flat_actual_card" if actual_available else "post_game_review_v1",
                ),
            ),
            dependency_paths=leaf_paths_below(
                leaf_paths,
                "/legal_cards",
                "/analysis_report",
                "/recommendation",
                "/bounded_search_result",
            ),
            decision_index=0,
            perspective_player_id="me",
        )
    raise AssertionError(f"Unhandled Position Result provenance branch: {top}")


_ALLOWED_POSITION_DEPENDENCY_PREFIXES = {
    "game_declaration": ("/position", "/game_declaration"),
    "game_value_summary": ("/game_declaration",),
    "overbid_summary": (
        "/game_declaration",
        "/game_value_summary",
        "/analysis_metadata/strategic_metadata/game_end_reason",
    ),
    "score_summary": ("/position", "/score_summary"),
    "game_result_summary": (
        "/score_summary",
        "/position/completed_tricks",
        "/game_declaration/game_type",
    ),
    "game_shortening_summary": (
        "/game_result_summary",
        "/game_declaration",
        "/game_value_summary",
        "/overbid_summary",
        "/position/completed_tricks",
    ),
    "game_continuation_summary": (
        "/position",
        "/game_declaration",
        "/information_policy_summary/public_hand_constraints",
    ),
    "adjusted_game_result_summary": (
        "/game_result_summary",
        "/game_shortening_summary",
        "/game_declaration",
        "/game_value_summary",
        "/overbid_summary",
        "/analysis_metadata/strategic_metadata/game_end_reason",
    ),
    "final_settlement_summary": (
        "/adjusted_game_result_summary",
        "/game_value_summary",
        "/overbid_summary",
        "/game_shortening_summary",
        "/position/completed_tricks",
    ),
    "performance_rating_summary": ("/final_settlement_summary",),
    "list_performance_summary": (),
    "list_standings_summary": (),
}


def validate_position_result_provenance_dependencies(
    entries: tuple[FieldProvenanceEntry, ...],
) -> None:
    """Rejects reverse or cross-domain dependencies in protected Position branches."""
    for entry in entries:
        tokens = entry.field_path.split("/")
        top = tokens[1] if len(tokens) > 1 else ""
        allowed = _ALLOWED_POSITION_DEPENDENCY_PREFIXES.get(top)
        if allowed is None:
            continue
        for dependency in entry.dependency_paths:
            if not any(
                dependency == prefix or dependency.startswith(f"{prefix}/")
                for prefix in allowed
            ):
                raise SkatAIInformationPolicyError(
                    "Position Result provenance contains a reverse or cross-domain dependency.",
                    path=entry.field_path,
                )
