from dataclasses import FrozenInstanceError

import pytest

from skatmind.errors import SkatMindValidationError
from skatmind.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceExemption,
    FieldProvenanceLedger,
)
from skatmind.field_provenance_coverage import (
    FieldProvenanceCoverageSummary,
    build_field_provenance_coverage_summary,
    build_serializable_field_provenance_coverage_summary,
    enumerate_json_leaf_paths,
    validate_field_provenance_coverage,
)


def _entry(path: str, coverage_kind: str = "field") -> FieldProvenanceEntry:
    return FieldProvenanceEntry(
        field_path=path,
        coverage_kind=coverage_kind,
        origin="caller_supplied",
        visibility="public",
        available_from="request_start",
        available_from_decision_index=None,
        available_from_event_index=None,
        derivation="direct",
        source_references=(),
        dependency_paths=(),
        subject_player_id=None,
        perspective_player_id=None,
    )


def _complete(
    *entries: FieldProvenanceEntry,
    exemptions: tuple[FieldProvenanceExemption, ...] = (),
) -> FieldProvenanceLedger:
    return FieldProvenanceLedger(
        status="complete",
        entries=entries,
        exemptions=exemptions,
        limitations=(),
    )


@pytest.mark.parametrize(
    ("document", "expected"),
    (
        ({"a": 1, "b": {"c": None}}, ("/a", "/b/c")),
        ({"items": [{"name": "a"}, {"name": "b"}]}, ("/items/0/name", "/items/1/name")),
        ({"empty_array": [], "empty_object": {}}, ("/empty_array", "/empty_object")),
        ({"a/b": {"~key": True}}, ("/a~1b/~0key",)),
        (None, ("",)),
        (7, ("",)),
        ({}, ("",)),
        ([], ("",)),
    ),
)
def test_leaf_enumeration_is_deterministic_and_handles_all_leaf_kinds(
    document: object, expected: tuple[str, ...]
) -> None:
    assert enumerate_json_leaf_paths(document) == expected


def test_leaf_enumeration_uses_sorted_object_keys_and_numeric_array_order() -> None:
    document = {"z": 1, "items": list(range(12)), "a": 2}
    assert enumerate_json_leaf_paths(document) == (
        "/a",
        *(f"/items/{index}" for index in range(12)),
        "/z",
    )


@pytest.mark.parametrize(
    "document",
    (
        {1: "not a string key"},
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": object()},
    ),
)
def test_leaf_enumeration_rejects_non_json_values(document: object) -> None:
    with pytest.raises(SkatMindValidationError):
        enumerate_json_leaf_paths(document)


def test_leaf_enumeration_rejects_container_cycles_with_the_public_path() -> None:
    document: list[object] = []
    document.append(document)
    with pytest.raises(SkatMindValidationError, match="cycles") as exc_info:
        enumerate_json_leaf_paths(document)
    assert exc_info.value.path == "/0"


def test_exact_subtree_and_mixed_coverage_are_audited() -> None:
    document = {"a": 1, "object": {"x": 2, "y": [3, 4]}}
    exact = _complete(
        _entry("/a"),
        _entry("/object/x"),
        _entry("/object/y/0"),
        _entry("/object/y/1"),
    )
    subtree = _complete(_entry("", "subtree"))
    mixed = _complete(_entry("/a"), _entry("/object", "subtree"))

    for ledger in (exact, subtree, mixed):
        summary = validate_field_provenance_coverage(document, ledger)
        assert summary.leaf_path_count == 4
        assert summary.provenanced_path_count == 4
        assert summary.exempted_path_count == 0
        assert summary.uncovered_paths == ()
        assert summary.orphaned_entry_paths == ()
        assert summary.overlapping_paths == ()
        assert summary.all_paths_accounted_for is True
        assert summary.provenance_complete is True


def test_partial_legacy_can_account_for_all_leaves_without_complete_provenance() -> None:
    document = {"tracked": 1, "legacy": {"a": 2, "b": 3}}
    ledger = FieldProvenanceLedger(
        status="partial_legacy",
        entries=(_entry("/tracked"),),
        exemptions=(
            FieldProvenanceExemption(
                field_path="/legacy", coverage_kind="subtree", reason="legacy_untracked"
            ),
        ),
        limitations=("legacy_untracked_fields",),
    )

    summary = validate_field_provenance_coverage(document, ledger)
    assert summary.provenanced_path_count == 1
    assert summary.exempted_path_count == 2
    assert summary.all_paths_accounted_for is True
    assert summary.provenance_complete is False


def test_not_available_summary_reports_every_document_leaf_as_uncovered() -> None:
    ledger = FieldProvenanceLedger(
        status="not_available",
        entries=(),
        exemptions=(),
        limitations=("provenance_not_available",),
    )
    summary = validate_field_provenance_coverage({"a": 1, "b": 2}, ledger)
    assert summary.leaf_path_count == 2
    assert summary.provenanced_path_count == 0
    assert summary.exempted_path_count == 0
    assert summary.uncovered_paths == ("/a", "/b")
    assert summary.all_paths_accounted_for is False
    assert summary.provenance_complete is False


def test_coverage_summary_reports_uncovered_orphaned_and_overlapping_paths() -> None:
    document = {"a": 1, "object": {"x": 2}}
    ledger = _complete(
        _entry("/object", "subtree"),
        _entry("/object/x"),
        _entry("/missing"),
    )

    summary = build_field_provenance_coverage_summary(document, ledger)
    assert summary.uncovered_paths == ("/a",)
    assert summary.orphaned_entry_paths == ("/missing",)
    assert summary.orphaned_exemption_paths == ()
    assert summary.overlapping_paths == ("/object/x",)
    assert summary.all_paths_accounted_for is False
    assert summary.provenance_complete is False


def test_coverage_summary_reports_orphaned_exemption() -> None:
    ledger = _complete(
        _entry("/a"),
        exemptions=(
            FieldProvenanceExemption(
                field_path="/missing", coverage_kind="field", reason="schema_constant"
            ),
        ),
    )
    summary = build_field_provenance_coverage_summary({"a": 1}, ledger)
    assert summary.orphaned_exemption_paths == ("/missing",)
    with pytest.raises(SkatMindValidationError) as exc_info:
        validate_field_provenance_coverage({"a": 1}, ledger)
    assert exc_info.value.path == "/missing"


@pytest.mark.parametrize(
    ("document", "ledger", "error_path"),
    (
        ({"a": 1}, _complete(), "/a"),
        ({"a": 1}, _complete(_entry("/missing")), "/missing"),
        (
            {"object": {"x": 1}},
            _complete(_entry("/object", "subtree"), _entry("/object/x")),
            "/object/x",
        ),
        (
            {"object": {"x": 1}},
            _complete(_entry("", "subtree"), _entry("/object", "subtree")),
            "/object/x",
        ),
    ),
)
def test_complete_coverage_validation_uses_public_json_pointer_error_paths(
    document: object, ledger: FieldProvenanceLedger, error_path: str
) -> None:
    with pytest.raises(SkatMindValidationError) as exc_info:
        validate_field_provenance_coverage(document, ledger)
    assert exc_info.value.path == error_path


def test_coverage_summary_serialization_is_deterministic() -> None:
    summary = build_field_provenance_coverage_summary(
        {"a": 1, "b": 2}, _complete(_entry("/a"))
    )
    expected = {
        "leaf_path_count": 2,
        "provenanced_path_count": 1,
        "exempted_path_count": 0,
        "uncovered_paths": ["/b"],
        "orphaned_entry_paths": [],
        "orphaned_exemption_paths": [],
        "overlapping_paths": [],
        "all_paths_accounted_for": False,
        "provenance_complete": False,
    }
    assert build_serializable_field_provenance_coverage_summary(summary) == expected
    assert build_serializable_field_provenance_coverage_summary(summary) == expected


def test_coverage_summary_rejects_unreconciled_counts() -> None:
    with pytest.raises(SkatMindValidationError, match="reconcile"):
        FieldProvenanceCoverageSummary(
            leaf_path_count=1,
            provenanced_path_count=1,
            exempted_path_count=1,
            uncovered_paths=(),
            orphaned_entry_paths=(),
            orphaned_exemption_paths=(),
            overlapping_paths=(),
            all_paths_accounted_for=True,
            provenance_complete=True,
        )


def test_coverage_summary_defensively_copies_paths_and_is_immutable() -> None:
    uncovered = ["/z", "/a"]
    summary = FieldProvenanceCoverageSummary(
        leaf_path_count=2,
        provenanced_path_count=0,
        exempted_path_count=0,
        uncovered_paths=uncovered,  # type: ignore[arg-type]
        orphaned_entry_paths=[],  # type: ignore[arg-type]
        orphaned_exemption_paths=[],  # type: ignore[arg-type]
        overlapping_paths=[],  # type: ignore[arg-type]
        all_paths_accounted_for=False,
        provenance_complete=False,
    )
    uncovered.clear()
    assert summary.uncovered_paths == ("/a", "/z")
    with pytest.raises(FrozenInstanceError):
        summary.leaf_path_count = 0  # type: ignore[misc]
    assert not hasattr(summary, "__dict__")
