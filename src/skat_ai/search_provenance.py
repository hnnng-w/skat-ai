from __future__ import annotations

from skat_ai.bounded_search_result import (
    BoundedSearchResult,
    build_serializable_bounded_search_result,
)
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
    build_json_pointer,
    parse_json_pointer,
)
from skat_ai.field_provenance_coverage import (
    enumerate_json_leaf_paths,
    validate_field_provenance_coverage,
)


def _prefixed_path(prefix: str, path: str) -> str:
    return build_json_pointer((*parse_json_pointer(prefix), *parse_json_pointer(path)))


def _search_reference(result: BoundedSearchResult) -> FieldProvenanceSourceReference:
    return FieldProvenanceSourceReference(
        reference_type="algorithm",
        reference_id=result.search_method,
        field_path=None,
        visibility="public",
    )


def _candidate_aggregate_provenance(
    result: BoundedSearchResult,
) -> tuple[str, str]:
    if result.consumed_budget.completed_world_count == 0:
        return ("search_derived", "direct")
    if result.world_coverage == "sampled_compatible_worlds":
        return ("compatible_world_aggregate", "sampled_aggregate")
    return ("compatible_world_aggregate", "exact_aggregate")


def build_bounded_search_provenance_entries(
    result: BoundedSearchResult,
    *,
    field_path: str = "",
    decision_index: int = 0,
) -> tuple[FieldProvenanceEntry, ...]:
    """Maps one existing aggregate Search Result without private world details."""
    if not isinstance(result, BoundedSearchResult):
        raise ValueError("result must be a BoundedSearchResult.")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        raise ValueError("decision_index must be a non-negative integer.")
    parse_json_pointer(field_path)
    document = build_serializable_bounded_search_result(result)
    leaf_paths = enumerate_json_leaf_paths(document)
    all_paths = {_prefixed_path(field_path, path) for path in leaf_paths}
    reference = _search_reference(result)
    aggregate_origin, aggregate_derivation = _candidate_aggregate_provenance(result)
    entries: list[FieldProvenanceEntry] = []

    for relative_path in leaf_paths:
        tokens = parse_json_pointer(relative_path)
        path = _prefixed_path(field_path, relative_path)
        origin = "search_derived"
        derivation = "direct"
        dependencies: tuple[str, ...] = ()

        if tokens and tokens[0] == "requested_budget":
            origin = "validated_copy"
            derivation = "validated"
        elif tokens == ("compatible_world_count",) and result.compatible_world_count is not None:
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
            elif metric in {"rank", "is_recommended"}:
                candidate_prefix = build_json_pointer(
                    (*parse_json_pointer(field_path), "candidate_results", tokens[1])
                )
                if metric == "rank":
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
                else:
                    rank_path = f"{candidate_prefix}/rank"
                    if rank_path in all_paths:
                        dependencies = (rank_path,)
                derivation = "deterministic_rule"
        elif tokens == ("recommended_card",):
            candidate_dependencies = tuple(
                sorted(
                    candidate_path
                    for candidate_path in all_paths
                    if candidate_path.startswith(
                        f"{field_path}/candidate_results/"
                        if field_path
                        else "/candidate_results/"
                    )
                    and candidate_path.endswith("/is_recommended")
                )
            )
            dependencies = candidate_dependencies
            derivation = "deterministic_rule" if candidate_dependencies else "direct"

        entries.append(
            FieldProvenanceEntry(
                field_path=path,
                coverage_kind="field",
                origin=origin,
                visibility="public",
                available_from="current_decision",
                available_from_decision_index=decision_index,
                available_from_event_index=None,
                derivation=derivation,
                source_references=(reference,),
                dependency_paths=dependencies,
                subject_player_id=None,
                perspective_player_id="me",
            )
        )
    return tuple(entries)


def build_bounded_search_provenance_ledger(
    result: BoundedSearchResult,
) -> FieldProvenanceLedger:
    """Builds a complete standalone ledger for one serialized Search Result."""
    document = build_serializable_bounded_search_result(result)
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=build_bounded_search_provenance_entries(result),
        exemptions=(),
        limitations=(),
    )
    validate_field_provenance_coverage(document, ledger)
    return ledger
