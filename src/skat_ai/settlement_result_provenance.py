from __future__ import annotations

from collections.abc import Iterable

from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceSourceReference,
)

COMPLETE_RESULT_PROVENANCE_VERSION = 1


def result_source_reference(
    reference_type: str,
    reference_id: str,
    *,
    field_path: str | None = None,
    visibility: str = "public",
) -> FieldProvenanceSourceReference:
    """Builds one value-free reference used by complete Result ledgers."""
    return FieldProvenanceSourceReference(
        reference_type=reference_type,
        reference_id=reference_id,
        field_path=field_path,
        visibility=visibility,
    )


def result_provenance_entry(
    field_path: str,
    *,
    origin: str,
    visibility: str,
    available_from: str,
    derivation: str,
    source_references: tuple[FieldProvenanceSourceReference, ...],
    dependency_paths: Iterable[str] = (),
    decision_index: int | None = None,
    event_index: int | None = None,
    perspective_player_id: str | None = None,
) -> FieldProvenanceEntry:
    """Builds one exact-leaf Result entry with canonical direct dependencies."""
    dependencies = tuple(
        sorted({dependency for dependency in dependency_paths if dependency != field_path})
    )
    return FieldProvenanceEntry(
        field_path=field_path,
        coverage_kind="field",
        origin=origin,
        visibility=visibility,
        available_from=available_from,
        available_from_decision_index=(
            decision_index
            if available_from in {"current_decision", "after_actual_play"}
            else None
        ),
        available_from_event_index=(
            event_index if available_from == "after_public_event" else None
        ),
        derivation=derivation,
        source_references=source_references,
        dependency_paths=dependencies,
        subject_player_id=None,
        perspective_player_id=perspective_player_id,
    )


def leaf_paths_below(
    leaf_paths: Iterable[str],
    *prefixes: str,
) -> tuple[str, ...]:
    """Returns exact leaves at or below any supplied JSON Pointer prefix."""
    return tuple(
        path
        for path in leaf_paths
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)
    )


def build_game_value_result_entry(
    field_path: str,
    *,
    leaf_paths: tuple[str, ...],
    declaration_prefix: str,
    available_from: str,
    decision_index: int | None,
    visibility: str = "public",
) -> FieldProvenanceEntry:
    """Maps a retained Game Value leaf to its retained declaration facts."""
    return result_provenance_entry(
        field_path,
        origin="rule_derived",
        visibility=visibility,
        available_from=available_from,
        derivation="deterministic_rule",
        source_references=(
            result_source_reference("rule_contract", "game_value_rules_v1"),
        ),
        dependency_paths=leaf_paths_below(leaf_paths, declaration_prefix),
        decision_index=decision_index,
    )


def build_overbid_result_entry(
    field_path: str,
    *,
    leaf_paths: tuple[str, ...],
    declaration_prefix: str,
    game_value_prefix: str,
    ending_prefixes: tuple[str, ...] = (),
    available_from: str,
    decision_index: int | None,
    visibility: str = "public",
) -> FieldProvenanceEntry:
    """Maps a retained Overbid leaf without recalculating the Overbid result."""
    declaration_dependencies = tuple(
        path
        for path in leaf_paths_below(leaf_paths, declaration_prefix)
        if path.endswith(("/bid_value", "/game_type", "/hand_game", "/matadors"))
    )
    return result_provenance_entry(
        field_path,
        origin="rule_derived",
        visibility=visibility,
        available_from=available_from,
        derivation="deterministic_rule",
        source_references=(
            result_source_reference("rule_contract", "overbid_rules_v1"),
        ),
        dependency_paths=(
            *declaration_dependencies,
            *leaf_paths_below(leaf_paths, game_value_prefix, *ending_prefixes),
        ),
        decision_index=decision_index,
    )


def build_settlement_result_entry(
    field_path: str,
    *,
    leaf_paths: tuple[str, ...],
    result_prefix: str,
    game_value_prefix: str,
    overbid_prefix: str,
    ending_prefixes: tuple[str, ...] = (),
    completed_trick_prefixes: tuple[str, ...] = (),
    available_from: str = "game_end",
    visibility: str = "public",
) -> FieldProvenanceEntry:
    """Maps retained Settlement output to approved forward-only inputs."""
    return result_provenance_entry(
        field_path,
        origin="rule_derived",
        visibility=visibility,
        available_from=available_from,
        derivation="deterministic_rule",
        source_references=(
            result_source_reference(
                "rule_contract",
                "settlement_normative_matrix_v1",
            ),
        ),
        dependency_paths=leaf_paths_below(
            leaf_paths,
            result_prefix,
            game_value_prefix,
            overbid_prefix,
            *ending_prefixes,
            *completed_trick_prefixes,
        ),
        decision_index=None,
    )
