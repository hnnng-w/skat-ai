from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from skat_ai.errors import SkatAIValidationError
from skat_ai.field_provenance import (
    FieldProvenanceLedger,
    build_json_pointer,
    parse_json_pointer,
    resolve_json_pointer,
)


def _validate_json_scalar(value: object, *, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    raise SkatAIValidationError(
        "Document values must be JSON-compatible and numbers must be finite.",
        path=path,
    )


def enumerate_json_leaf_paths(document: object) -> tuple[str, ...]:
    """Enumerates deterministic current JSON leaves, including empty containers."""
    leaves: list[str] = []
    active_container_ids: set[int] = set()

    def visit(value: object, tokens: tuple[str, ...]) -> None:
        path = build_json_pointer(tokens)
        if isinstance(value, Mapping):
            container_id = id(value)
            if container_id in active_container_ids:
                raise SkatAIValidationError(
                    "JSON-compatible documents cannot contain container cycles.",
                    path=path,
                )
            if any(not isinstance(key, str) for key in value):
                raise SkatAIValidationError(
                    "JSON object keys must be strings.",
                    path=path,
                )
            if not value:
                leaves.append(path)
                return
            active_container_ids.add(container_id)
            try:
                for key in sorted(value):
                    visit(value[key], (*tokens, key))
            finally:
                active_container_ids.remove(container_id)
            return
        if isinstance(value, (list, tuple)):
            container_id = id(value)
            if container_id in active_container_ids:
                raise SkatAIValidationError(
                    "JSON-compatible documents cannot contain container cycles.",
                    path=path,
                )
            if not value:
                leaves.append(path)
                return
            active_container_ids.add(container_id)
            try:
                for index, item in enumerate(value):
                    visit(item, (*tokens, str(index)))
            finally:
                active_container_ids.remove(container_id)
            return
        _validate_json_scalar(value, path=path)
        leaves.append(path)

    visit(document, ())
    if len(leaves) != len(set(leaves)):
        raise SkatAIValidationError(
            "JSON leaf paths must be unique.",
            path="",
        )
    return tuple(leaves)


def _canonicalize_path_tuple(value: object, *, path: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise SkatAIValidationError(f"{path} must be an immutable-compatible array.", path=path)
    copied = tuple(value)
    for item in copied:
        if not isinstance(item, str):
            raise SkatAIValidationError(f"{path} must contain JSON Pointer strings.", path=path)
        parse_json_pointer(item)
    if len(copied) != len(set(copied)):
        raise SkatAIValidationError(
            f"{path} must contain unique paths.",
            path=path,
        )
    return tuple(sorted(copied))


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceCoverageSummary:
    """Deterministic leaf-level coverage audit for one document and ledger."""

    leaf_path_count: int
    provenanced_path_count: int
    exempted_path_count: int
    uncovered_paths: tuple[str, ...]
    orphaned_entry_paths: tuple[str, ...]
    orphaned_exemption_paths: tuple[str, ...]
    overlapping_paths: tuple[str, ...]
    all_paths_accounted_for: bool
    provenance_complete: bool

    def __post_init__(self) -> None:
        for field_name in (
            "leaf_path_count",
            "provenanced_path_count",
            "exempted_path_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SkatAIValidationError(
                    f"{field_name} must be a non-negative integer.",
                    path=field_name,
                )
        if self.provenanced_path_count > self.leaf_path_count:
            raise SkatAIValidationError(
                "provenanced_path_count cannot exceed leaf_path_count.",
                path="provenanced_path_count",
            )
        if self.exempted_path_count > self.leaf_path_count:
            raise SkatAIValidationError(
                "exempted_path_count cannot exceed leaf_path_count.",
                path="exempted_path_count",
            )
        for field_name in (
            "uncovered_paths",
            "orphaned_entry_paths",
            "orphaned_exemption_paths",
            "overlapping_paths",
        ):
            object.__setattr__(
                self,
                field_name,
                _canonicalize_path_tuple(getattr(self, field_name), path=field_name),
            )
        for field_name in ("all_paths_accounted_for", "provenance_complete"):
            if not isinstance(getattr(self, field_name), bool):
                raise SkatAIValidationError(
                    f"{field_name} must be a boolean.",
                    path=field_name,
                )
        if (
            self.provenanced_path_count
            + self.exempted_path_count
            + len(self.uncovered_paths)
            != self.leaf_path_count
        ):
            raise SkatAIValidationError(
                "Coverage counts do not reconcile with leaf_path_count.",
                path="leaf_path_count",
            )
        if set(self.uncovered_paths).intersection(self.overlapping_paths):
            raise SkatAIValidationError(
                "A path cannot be both uncovered and overlapping.",
                path="overlapping_paths",
            )
        if len(self.overlapping_paths) > (
            self.provenanced_path_count + self.exempted_path_count
        ):
            raise SkatAIValidationError(
                "overlapping_paths exceed the covered path counts.",
                path="overlapping_paths",
            )
        expected_accounting = not self.uncovered_paths and not self.overlapping_paths
        if self.all_paths_accounted_for != expected_accounting:
            raise SkatAIValidationError(
                "all_paths_accounted_for does not match leaf coverage.",
                path="all_paths_accounted_for",
            )
        if self.provenance_complete and (
            not self.all_paths_accounted_for
            or self.orphaned_entry_paths
            or self.orphaned_exemption_paths
        ):
            raise SkatAIValidationError(
                "provenance_complete requires unambiguous, non-orphaned coverage.",
                path="provenance_complete",
            )


def _path_is_at_or_below(path: str, ancestor: str) -> bool:
    path_tokens = parse_json_pointer(path)
    ancestor_tokens = parse_json_pointer(ancestor)
    return path_tokens[: len(ancestor_tokens)] == ancestor_tokens


def _resolve_covered_leaf_paths(
    document: object,
    leaf_paths: tuple[str, ...],
    leaf_path_set: frozenset[str],
    field_path: str,
    coverage_kind: str,
) -> tuple[str, ...] | None:
    try:
        resolve_json_pointer(document, field_path)
    except SkatAIValidationError:
        return None
    if coverage_kind == "field":
        return (field_path,) if field_path in leaf_path_set else None
    covered = tuple(
        leaf_path
        for leaf_path in leaf_paths
        if _path_is_at_or_below(leaf_path, field_path)
    )
    return covered or None


def build_field_provenance_coverage_summary(
    document: object,
    ledger: FieldProvenanceLedger,
) -> FieldProvenanceCoverageSummary:
    """Audits exact and subtree declarations against current document leaves."""
    if not isinstance(ledger, FieldProvenanceLedger):
        raise SkatAIValidationError(
            "ledger must be a FieldProvenanceLedger.",
            path="ledger",
        )
    leaf_paths = enumerate_json_leaf_paths(document)
    leaf_path_set = frozenset(leaf_paths)
    coverage_count = {path: 0 for path in leaf_paths}
    provenanced_paths: set[str] = set()
    exempted_paths: set[str] = set()
    orphaned_entry_paths: list[str] = []
    orphaned_exemption_paths: list[str] = []

    for entry in ledger.entries:
        covered = _resolve_covered_leaf_paths(
            document,
            leaf_paths,
            leaf_path_set,
            entry.field_path,
            entry.coverage_kind,
        )
        if covered is None:
            orphaned_entry_paths.append(entry.field_path)
            continue
        for path in covered:
            coverage_count[path] += 1
            provenanced_paths.add(path)

    for exemption in ledger.exemptions:
        covered = _resolve_covered_leaf_paths(
            document,
            leaf_paths,
            leaf_path_set,
            exemption.field_path,
            exemption.coverage_kind,
        )
        if covered is None:
            orphaned_exemption_paths.append(exemption.field_path)
            continue
        for path in covered:
            coverage_count[path] += 1
            exempted_paths.add(path)

    uncovered_paths = tuple(sorted(path for path, count in coverage_count.items() if count == 0))
    overlapping_paths = tuple(sorted(path for path, count in coverage_count.items() if count > 1))
    orphaned_entries = tuple(sorted(orphaned_entry_paths))
    orphaned_exemptions = tuple(sorted(orphaned_exemption_paths))
    all_paths_accounted_for = not uncovered_paths and not overlapping_paths
    has_legacy_exemption = any(
        exemption.reason == "legacy_untracked" for exemption in ledger.exemptions
    )
    provenance_complete = (
        ledger.status == "complete"
        and all_paths_accounted_for
        and not orphaned_entries
        and not orphaned_exemptions
        and not has_legacy_exemption
    )
    return FieldProvenanceCoverageSummary(
        leaf_path_count=len(leaf_paths),
        provenanced_path_count=len(provenanced_paths),
        exempted_path_count=len(exempted_paths),
        uncovered_paths=uncovered_paths,
        orphaned_entry_paths=orphaned_entries,
        orphaned_exemption_paths=orphaned_exemptions,
        overlapping_paths=overlapping_paths,
        all_paths_accounted_for=all_paths_accounted_for,
        provenance_complete=provenance_complete,
    )


def validate_field_provenance_coverage(
    document: object,
    ledger: FieldProvenanceLedger,
) -> FieldProvenanceCoverageSummary:
    """Requires status-appropriate current-document coverage and returns its audit."""
    summary = build_field_provenance_coverage_summary(document, ledger)
    if ledger.status == "not_available":
        return summary
    if summary.orphaned_entry_paths:
        raise SkatAIValidationError(
            "A provenance entry does not identify a current document leaf or subtree.",
            path=summary.orphaned_entry_paths[0],
        )
    if summary.orphaned_exemption_paths:
        raise SkatAIValidationError(
            "A provenance exemption does not identify a current document leaf or subtree.",
            path=summary.orphaned_exemption_paths[0],
        )
    if summary.overlapping_paths:
        raise SkatAIValidationError(
            "A document leaf has overlapping provenance coverage.",
            path=summary.overlapping_paths[0],
        )
    if summary.uncovered_paths:
        raise SkatAIValidationError(
            "A document leaf has no provenance entry or exemption.",
            path=summary.uncovered_paths[0],
        )
    if ledger.status == "complete" and not summary.provenance_complete:
        raise SkatAIValidationError(
            "A complete ledger requires complete non-legacy provenance.",
            path="status",
        )
    if ledger.status == "partial_legacy" and not summary.all_paths_accounted_for:
        raise SkatAIValidationError(
            "A partial_legacy ledger must account for every document leaf.",
            path="status",
        )
    return summary


def build_serializable_field_provenance_coverage_summary(
    summary: FieldProvenanceCoverageSummary,
) -> dict[str, Any]:
    """Builds the deterministic coverage-summary representation."""
    return {
        "leaf_path_count": summary.leaf_path_count,
        "provenanced_path_count": summary.provenanced_path_count,
        "exempted_path_count": summary.exempted_path_count,
        "uncovered_paths": list(summary.uncovered_paths),
        "orphaned_entry_paths": list(summary.orphaned_entry_paths),
        "orphaned_exemption_paths": list(summary.orphaned_exemption_paths),
        "overlapping_paths": list(summary.overlapping_paths),
        "all_paths_accounted_for": summary.all_paths_accounted_for,
        "provenance_complete": summary.provenance_complete,
    }
