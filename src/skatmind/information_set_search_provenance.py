from __future__ import annotations

from collections.abc import Mapping

from skatmind.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceSourceReference,
    build_json_pointer,
    parse_json_pointer,
)
from skatmind.field_provenance_coverage import enumerate_json_leaf_paths
from skatmind.information_set_search_contracts import (
    BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
    InformationSetSearchResultV1,
)
from skatmind.information_set_search_public import (
    build_public_information_set_search_result_v1,
)

INFORMATION_SET_SEARCH_PROVENANCE_VERSION = 1


def _reference(
    reference_type: str,
    reference_id: str,
    *,
    field_path: str | None = None,
    visibility: str = "public",
) -> FieldProvenanceSourceReference:
    return FieldProvenanceSourceReference(
        reference_type=reference_type,
        reference_id=reference_id,
        field_path=field_path,
        visibility=visibility,
    )


def _prefixed_path(prefix: str, path: str) -> str:
    return build_json_pointer(
        (*parse_json_pointer(prefix), *parse_json_pointer(path))
    )


def _settings_leaf_reference(
    reference: FieldProvenanceSourceReference,
    field_name: str,
) -> FieldProvenanceSourceReference:
    if reference.field_path != "/information_set_search_settings":
        return reference
    return _reference(
        reference.reference_type,
        reference.reference_id,
        field_path=f"{reference.field_path}/{field_name}",
        visibility=reference.visibility,
    )


def _entry(
    path: str,
    *,
    origin: str,
    derivation: str,
    decision_index: int,
    perspective_player_id: str | None,
    references: tuple[FieldProvenanceSourceReference, ...],
    available_from: str = "current_decision",
    visibility: str = "public",
    dependencies: tuple[str, ...] = (),
) -> FieldProvenanceEntry:
    return FieldProvenanceEntry(
        field_path=path,
        coverage_kind="field",
        origin=origin,
        visibility=visibility,
        available_from=available_from,
        available_from_decision_index=(
            decision_index
            if available_from in {"current_decision", "after_actual_play"}
            else None
        ),
        available_from_event_index=None,
        derivation=derivation,
        source_references=references,
        dependency_paths=dependencies,
        subject_player_id=None,
        perspective_player_id=perspective_player_id,
    )


def _candidate_aggregate_provenance(
    document: Mapping[str, object],
) -> tuple[str, str]:
    consumed = document.get("consumed_budget")
    completed = (
        consumed.get("completed_world_count")
        if isinstance(consumed, Mapping)
        else 0
    )
    if not isinstance(completed, int) or completed == 0:
        return ("search_derived", "direct")
    if document.get("world_coverage") == "sampled_compatible_worlds":
        return ("compatible_world_aggregate", "sampled_aggregate")
    return ("compatible_world_aggregate", "exact_aggregate")


def build_information_set_search_provenance_entries(
    document: Mapping[str, object],
    *,
    retained_result: InformationSetSearchResultV1 | None,
    field_path: str,
    decision_index: int,
    perspective_player_id: str | None,
    settings_reference: FieldProvenanceSourceReference,
    fixed_policy_reference: FieldProvenanceSourceReference,
) -> tuple[FieldProvenanceEntry, ...]:
    """Maps one retained privacy-safe Information-set Search Result."""
    if retained_result is not None:
        expected = build_public_information_set_search_result_v1(retained_result)
        if expected != document:
            raise ValueError(
                "Retained Information-set Search Result does not match its public projection."
            )
        search_method = retained_result.search_method
    else:
        search_method = document.get("search_method")
        if not isinstance(search_method, str) or not search_method:
            raise ValueError("Public Information-set Search Result has no method.")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        raise ValueError("decision_index must be a non-negative integer.")

    relative_paths = enumerate_json_leaf_paths(document)
    all_paths = frozenset(
        _prefixed_path(field_path, path) for path in relative_paths
    )
    search_reference = _reference("algorithm", search_method)
    aggregate_origin, aggregate_derivation = _candidate_aggregate_provenance(
        document
    )
    entries: list[FieldProvenanceEntry] = []
    for relative_path in relative_paths:
        tokens = parse_json_pointer(relative_path)
        path = _prefixed_path(field_path, relative_path)
        origin = "search_derived"
        derivation = "direct"
        references = (search_reference,)
        dependencies: tuple[str, ...] = ()

        if tokens and tokens[0] == "requested_budget":
            if settings_reference.field_path == "/information_set_search_settings":
                origin = "validated_copy"
                derivation = "validated"
                references = (
                    _settings_leaf_reference(settings_reference, tokens[-1]),
                )
            else:
                origin = "rule_derived"
                derivation = "deterministic_rule"
                references = (
                    settings_reference,
                    _reference(
                        "rule_contract",
                        "information_set_budget_profile_conversion_v1",
                    ),
                )
        elif tokens and tokens[0] == "fixed_policy_settings":
            origin = "heuristic_analysis"
            derivation = "deterministic_rule"
            references = (fixed_policy_reference,)
        elif tokens == ("compatible_world_count",) and document.get(
            "compatible_world_count"
        ) is not None:
            origin = "compatible_world_aggregate"
            derivation = "exact_aggregate"
        elif len(tokens) >= 3 and tokens[0] == "candidate_results":
            metric = tokens[2]
            if metric in {
                "completed_world_count",
                "local_contract_success_count",
                "local_contract_success_rate",
                "mean_local_side_game_score",
                "mean_local_side_card_point_margin",
            }:
                origin = aggregate_origin
                derivation = aggregate_derivation
            elif metric == "rank":
                dependencies = tuple(
                    sorted(
                        candidate_path
                        for candidate_path in all_paths
                        if (
                            "/candidate_results/" in candidate_path
                            and candidate_path.rsplit("/", 1)[-1]
                            in {
                                "card",
                                "local_contract_success_rate",
                                "mean_local_side_game_score",
                                "mean_local_side_card_point_margin",
                            }
                        )
                        or candidate_path
                        == _prefixed_path(field_path, "/game_type")
                    )
                )
                derivation = "deterministic_rule"
            elif metric == "is_recommended":
                rank_path = _prefixed_path(
                    field_path,
                    f"/candidate_results/{tokens[1]}/rank",
                )
                if rank_path in all_paths:
                    dependencies = (rank_path,)
                derivation = "deterministic_rule"
        elif tokens == ("recommended_card",):
            dependencies = tuple(
                sorted(
                    candidate_path
                    for candidate_path in all_paths
                    if "/candidate_results/" in candidate_path
                    and candidate_path.endswith("/is_recommended")
                )
            )
            if dependencies:
                derivation = "deterministic_rule"
        elif tokens == ("controlled_policy_decision_count",):
            references = (
                search_reference,
                _reference(
                    "aggregate",
                    "information_set_controlled_policy_decision_count_v1",
                    visibility="engine_private",
                ),
            )

        entries.append(
            _entry(
                path,
                origin=origin,
                derivation=derivation,
                decision_index=decision_index,
                perspective_player_id=perspective_player_id,
                references=references,
                dependencies=dependencies,
            )
        )
    return tuple(entries)


def build_serialized_pimc_provenance_entries(
    document: Mapping[str, object],
    *,
    field_path: str,
    decision_index: int,
    perspective_player_id: str | None,
    settings_reference: FieldProvenanceSourceReference,
) -> tuple[FieldProvenanceEntry, ...]:
    """Maps a retained serialized same-selection PIMC Result."""
    search_method = document.get("search_method")
    if not isinstance(search_method, str) or not search_method:
        raise ValueError("Serialized PIMC Result has no Search method.")
    relative_paths = enumerate_json_leaf_paths(document)
    all_paths = frozenset(
        _prefixed_path(field_path, path) for path in relative_paths
    )
    search_reference = _reference("algorithm", search_method)
    aggregate_origin, aggregate_derivation = _candidate_aggregate_provenance(
        document
    )
    entries = []
    for relative_path in relative_paths:
        tokens = parse_json_pointer(relative_path)
        path = _prefixed_path(field_path, relative_path)
        origin = "search_derived"
        derivation = "direct"
        references = (search_reference,)
        dependencies: tuple[str, ...] = ()
        if tokens and tokens[0] == "requested_budget":
            origin = "rule_derived"
            derivation = "deterministic_rule"
            references = (
                settings_reference,
                _reference(
                    "rule_contract",
                    "information_set_budget_to_same_selection_pimc_v1",
                ),
            )
        elif tokens == ("compatible_world_count",) and document.get(
            "compatible_world_count"
        ) is not None:
            origin = "compatible_world_aggregate"
            derivation = "exact_aggregate"
        elif len(tokens) >= 3 and tokens[0] == "candidate_results":
            metric = tokens[2]
            if metric in {
                "completed_world_count",
                "local_contract_success_count",
                "local_contract_success_rate",
                "mean_local_side_game_score",
                "mean_local_side_card_point_margin",
            }:
                origin = aggregate_origin
                derivation = aggregate_derivation
            elif metric == "rank":
                dependencies = tuple(
                    sorted(
                        candidate_path
                        for candidate_path in all_paths
                        if (
                            "/candidate_results/" in candidate_path
                            and candidate_path.rsplit("/", 1)[-1]
                            in {
                                "card",
                                "local_contract_success_rate",
                                "mean_local_side_game_score",
                                "mean_local_side_card_point_margin",
                            }
                        )
                        or candidate_path
                        == _prefixed_path(field_path, "/game_type")
                    )
                )
                derivation = "deterministic_rule"
            elif metric == "is_recommended":
                rank_path = _prefixed_path(
                    field_path,
                    f"/candidate_results/{tokens[1]}/rank",
                )
                dependencies = (rank_path,) if rank_path in all_paths else ()
                derivation = "deterministic_rule"
        elif tokens == ("recommended_card",):
            dependencies = tuple(
                sorted(
                    candidate_path
                    for candidate_path in all_paths
                    if "/candidate_results/" in candidate_path
                    and candidate_path.endswith("/is_recommended")
                )
            )
            if dependencies:
                derivation = "deterministic_rule"
        entries.append(
            _entry(
                path,
                origin=origin,
                derivation=derivation,
                decision_index=decision_index,
                perspective_player_id=perspective_player_id,
                references=references,
                dependencies=dependencies,
            )
        )
    return tuple(entries)


def build_information_set_search_comparison_provenance_entries(
    document: Mapping[str, object],
    *,
    field_path: str,
    decision_index: int,
    perspective_player_id: str | None,
    actual_reference_id: str,
) -> tuple[FieldProvenanceEntry, ...]:
    """Maps one retained descriptive comparison without private Search state."""
    information_reference = _reference(
        "algorithm", BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD
    )
    pimc_reference = _reference(
        "algorithm", "compatible_world_minimax_same_selection_v1"
    )
    immediate_reference = _reference("algorithm", "immediate_expected_value")
    comparison_reference = _reference(
        "rule_contract", "information_set_search_comparison_v1"
    )
    actual_reference = _reference(
        "retrospective_observation", actual_reference_id
    )
    entries = []
    for relative_path in enumerate_json_leaf_paths(document):
        tokens = parse_json_pointer(relative_path)
        field_name = tokens[-1] if tokens else ""
        path = _prefixed_path(field_path, relative_path)
        origin = "rule_derived"
        derivation = "deterministic_rule"
        available_from = "current_decision"
        references: tuple[FieldProvenanceSourceReference, ...] = (
            comparison_reference,
        )

        uses_actual = "actual" in field_name
        uses_information = "information_set" in field_name
        uses_pimc = "pimc" in field_name
        uses_immediate = "immediate" in field_name
        if field_name == "actual_card":
            origin = "retrospective_attachment"
            derivation = "retrospective"
            available_from = "after_actual_play"
            references = (actual_reference,)
        else:
            method_references = []
            if uses_information:
                method_references.append(information_reference)
            if uses_pimc:
                method_references.append(pimc_reference)
            if uses_immediate:
                method_references.append(immediate_reference)
            if field_name in {
                "same_selected_world_sequence",
                "selected_world_count",
                "sampled_world_count",
            }:
                method_references.extend(
                    (information_reference, pimc_reference)
                )
            if field_name == "strategy_fusion_mitigation_scope":
                method_references = []
            if uses_actual:
                available_from = "after_actual_play"
                method_references.append(actual_reference)
            references = tuple(dict.fromkeys((*method_references, comparison_reference)))

        entries.append(
            _entry(
                path,
                origin=origin,
                derivation=derivation,
                decision_index=decision_index,
                perspective_player_id=perspective_player_id,
                references=references,
                available_from=available_from,
            )
        )
    return tuple(entries)


def information_set_settings_reference(
    reference_type: str,
    reference_id: str,
    *,
    field_path: str | None = None,
) -> FieldProvenanceSourceReference:
    """Builds a public exact settings Source Reference for collector reuse."""
    return _reference(
        reference_type,
        reference_id,
        field_path=field_path,
    )
