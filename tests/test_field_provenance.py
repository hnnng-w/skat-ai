from dataclasses import FrozenInstanceError, fields

import pytest

from skatmind.errors import SkatMindSerializationError, SkatMindValidationError
from skatmind.field_provenance import (
    FIELD_PROVENANCE_AVAILABILITY_BOUNDARIES,
    FIELD_PROVENANCE_CONFIDENCE_POLICY,
    FIELD_PROVENANCE_COVERAGE_KINDS,
    FIELD_PROVENANCE_DERIVATION_TYPES,
    FIELD_PROVENANCE_EXEMPTION_REASONS,
    FIELD_PROVENANCE_LIMITATIONS,
    FIELD_PROVENANCE_ORIGINS,
    FIELD_PROVENANCE_PATH_POLICY,
    FIELD_PROVENANCE_PUBLIC_REDACTION_POLICY,
    FIELD_PROVENANCE_REFERENCE_TYPES,
    FIELD_PROVENANCE_STATUSES,
    FIELD_PROVENANCE_VERSION,
    FIELD_PROVENANCE_VISIBILITY_SCOPES,
    FieldProvenanceEntry,
    FieldProvenanceExemption,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
    build_json_pointer,
    build_public_serializable_field_provenance_ledger,
    build_serializable_field_provenance_entry,
    build_serializable_field_provenance_exemption,
    build_serializable_field_provenance_ledger,
    build_serializable_field_provenance_source_reference,
    escape_json_pointer_token,
    parse_json_pointer,
    resolve_json_pointer,
    unescape_json_pointer_token,
)


def _entry(
    field_path: str,
    *,
    coverage_kind: str = "field",
    origin: str = "caller_supplied",
    visibility: str = "public",
    available_from: str = "request_start",
    available_from_decision_index: int | None = None,
    available_from_event_index: int | None = None,
    derivation: str = "direct",
    source_references: tuple[FieldProvenanceSourceReference, ...] = (),
    dependency_paths: tuple[str, ...] = (),
    subject_player_id: str | None = None,
    perspective_player_id: str | None = None,
) -> FieldProvenanceEntry:
    return FieldProvenanceEntry(
        field_path=field_path,
        coverage_kind=coverage_kind,
        origin=origin,
        visibility=visibility,
        available_from=available_from,
        available_from_decision_index=available_from_decision_index,
        available_from_event_index=available_from_event_index,
        derivation=derivation,
        source_references=source_references,
        dependency_paths=dependency_paths,
        subject_player_id=subject_player_id,
        perspective_player_id=perspective_player_id,
    )


def test_field_provenance_constants_and_canonical_orders_are_exact() -> None:
    assert FIELD_PROVENANCE_VERSION == 1
    assert FIELD_PROVENANCE_PATH_POLICY == "rfc6901_json_pointer"
    assert FIELD_PROVENANCE_CONFIDENCE_POLICY == "separate_contract"
    assert FIELD_PROVENANCE_PUBLIC_REDACTION_POLICY == "omit_engine_private_details"
    assert FIELD_PROVENANCE_STATUSES == ("complete", "partial_legacy", "not_available")
    assert FIELD_PROVENANCE_COVERAGE_KINDS == ("field", "subtree")
    assert FIELD_PROVENANCE_ORIGINS == (
        "caller_supplied",
        "defaulted",
        "validated_copy",
        "public_game_event",
        "historical_replay",
        "external_source",
        "rule_derived",
        "structural_inference",
        "compatible_world_aggregate",
        "sampled_estimate",
        "heuristic_analysis",
        "simulation_derived",
        "search_derived",
        "retrospective_attachment",
        "historical_aggregation",
        "dataset_assignment",
    )
    assert FIELD_PROVENANCE_VISIBILITY_SCOPES == (
        "public",
        "local_private",
        "declarer_private",
        "defender_private",
        "post_game_only",
        "engine_private",
    )
    assert FIELD_PROVENANCE_AVAILABILITY_BOUNDARIES == (
        "request_start",
        "current_decision",
        "after_public_event",
        "after_actual_play",
        "game_end",
        "offline_review",
    )
    assert FIELD_PROVENANCE_DERIVATION_TYPES == (
        "direct",
        "validated",
        "deterministic_rule",
        "reconstruction",
        "exact_aggregate",
        "sampled_aggregate",
        "heuristic",
        "retrospective",
    )
    assert FIELD_PROVENANCE_REFERENCE_TYPES == (
        "request",
        "historical_game",
        "historical_event",
        "external_record",
        "rule_contract",
        "algorithm",
        "aggregate",
        "retrospective_observation",
        "dataset_plan",
    )
    assert FIELD_PROVENANCE_EXEMPTION_REASONS == (
        "legacy_untracked",
        "schema_constant",
        "not_applicable",
    )
    assert FIELD_PROVENANCE_LIMITATIONS == (
        "legacy_untracked_fields",
        "private_dependencies_redacted",
        "provenance_not_available",
    )


@pytest.mark.parametrize(
    ("token", "escaped"),
    (("", ""), ("foo", "foo"), ("a/b", "a~1b"), ("tilde~value", "tilde~0value")),
)
def test_json_pointer_token_escaping_round_trips(token: str, escaped: str) -> None:
    assert escape_json_pointer_token(token) == escaped
    assert unescape_json_pointer_token(escaped) == token


@pytest.mark.parametrize(
    ("tokens", "pointer"),
    (
        ((), ""),
        (("foo",), "/foo"),
        (("foo", "bar"), "/foo/bar"),
        (("items", "0", "name"), "/items/0/name"),
        (("a/b",), "/a~1b"),
        (("tilde~value",), "/tilde~0value"),
        (("", ""), "//"),
        ((".", ".."), "/./.."),
    ),
)
def test_json_pointer_build_parse_and_resolution(
    tokens: tuple[str, ...], pointer: str
) -> None:
    assert build_json_pointer(tokens) == pointer
    assert parse_json_pointer(pointer) == tokens


def test_json_pointer_resolves_root_objects_arrays_and_escaped_keys() -> None:
    document = {
        "foo": {"bar": 3},
        "items": [{"name": "first"}],
        "a/b": 4,
        "tilde~value": 5,
        "": {"": 6},
    }

    assert resolve_json_pointer(document, "") is document
    assert resolve_json_pointer(document, "/foo/bar") == 3
    assert resolve_json_pointer(document, "/items/0/name") == "first"
    assert resolve_json_pointer(document, "/a~1b") == 4
    assert resolve_json_pointer(document, "/tilde~0value") == 5
    assert resolve_json_pointer(document, "//") == 6


@pytest.mark.parametrize("value", ("~", "~2", "a~x", "/foo~"))
def test_json_pointer_rejects_invalid_escapes(value: str) -> None:
    helper = parse_json_pointer if value.startswith("/") else unescape_json_pointer_token
    with pytest.raises(SkatMindValidationError):
        helper(value)


@pytest.mark.parametrize("pointer", ("foo", "foo/bar"))
def test_json_pointer_rejects_missing_leading_slash(pointer: str) -> None:
    with pytest.raises(SkatMindValidationError, match="begin with"):
        parse_json_pointer(pointer)


@pytest.mark.parametrize(
    ("document", "pointer", "message"),
    (
        ({"foo": 1}, "/missing", "object key"),
        ([1], "/01", "array index"),
        ([1], "/-", "array index"),
        ([1], "/1", "outside"),
        ({"foo": 1}, "/foo/bar", "scalar"),
    ),
)
def test_json_pointer_rejects_invalid_resolution(
    document: object, pointer: str, message: str
) -> None:
    with pytest.raises(SkatMindValidationError, match=message) as exc_info:
        resolve_json_pointer(document, pointer)
    assert exc_info.value.path == pointer


@pytest.mark.parametrize("reference_type", FIELD_PROVENANCE_REFERENCE_TYPES)
def test_source_reference_supports_every_reference_type(reference_type: str) -> None:
    reference = FieldProvenanceSourceReference(
        reference_type=reference_type,
        reference_id="source-1",
        field_path=None,
        visibility="public",
    )
    assert reference.reference_type == reference_type


def test_source_reference_is_frozen_slotted_and_serializes_explicit_null() -> None:
    reference = FieldProvenanceSourceReference(
        reference_type="historical_game",
        reference_id="game-1",
        field_path=None,
        visibility="engine_private",
    )

    with pytest.raises(FrozenInstanceError):
        reference.reference_id = "other"  # type: ignore[misc]
    assert not hasattr(reference, "__dict__")
    assert build_serializable_field_provenance_source_reference(reference) == {
        "reference_type": "historical_game",
        "reference_id": "game-1",
        "field_path": None,
        "visibility": "engine_private",
    }


@pytest.mark.parametrize("reference_id", ("", " source", "source ", 1, None))
def test_source_reference_rejects_invalid_stable_id(reference_id: object) -> None:
    with pytest.raises(SkatMindValidationError) as exc_info:
        FieldProvenanceSourceReference(
            reference_type="request",
            reference_id=reference_id,  # type: ignore[arg-type]
            field_path="/field",
            visibility="public",
        )
    assert exc_info.value.path == "reference_id"


def test_entry_defensively_canonicalizes_references_and_dependencies() -> None:
    references = [
        FieldProvenanceSourceReference(
            reference_type="request",
            reference_id="b",
            field_path="/z",
            visibility="public",
        ),
        FieldProvenanceSourceReference(
            reference_type="request",
            reference_id="a",
            field_path=None,
            visibility="public",
        ),
    ]
    dependencies = ["/z", "/a"]
    entry = _entry(
        "/field",
        source_references=references,  # type: ignore[arg-type]
        dependency_paths=dependencies,  # type: ignore[arg-type]
    )
    references.clear()
    dependencies.clear()

    assert tuple(reference.reference_id for reference in entry.source_references) == ("a", "b")
    assert entry.dependency_paths == ("/a", "/z")
    with pytest.raises(FrozenInstanceError):
        entry.origin = "defaulted"  # type: ignore[misc]
    assert not hasattr(entry, "__dict__")


def test_entry_rejects_duplicate_references_dependencies_and_self_dependency() -> None:
    reference = FieldProvenanceSourceReference(
        reference_type="request",
        reference_id="request-1",
        field_path=None,
        visibility="public",
    )
    with pytest.raises(SkatMindValidationError, match="Duplicate source"):
        _entry("/field", source_references=(reference, reference))
    with pytest.raises(SkatMindValidationError, match="Duplicate dependency"):
        _entry("/field", dependency_paths=("/a", "/a"))
    with pytest.raises(SkatMindValidationError, match="itself"):
        _entry("/field", dependency_paths=("/field",))


@pytest.mark.parametrize("origin", FIELD_PROVENANCE_ORIGINS)
def test_entry_supports_every_origin(origin: str) -> None:
    derivation = {
        "rule_derived": "deterministic_rule",
        "dataset_assignment": "deterministic_rule",
        "retrospective_attachment": "retrospective",
        "sampled_estimate": "sampled_aggregate",
        "compatible_world_aggregate": "exact_aggregate",
    }.get(origin, "direct")
    available_from = (
        "after_actual_play" if origin == "retrospective_attachment" else "request_start"
    )
    entry = _entry(
        "/field",
        origin=origin,
        derivation=derivation,
        available_from=available_from,
        available_from_decision_index=(0 if available_from == "after_actual_play" else None),
    )
    assert entry.origin == origin


@pytest.mark.parametrize("visibility", FIELD_PROVENANCE_VISIBILITY_SCOPES)
def test_entry_supports_every_visibility(visibility: str) -> None:
    entry = _entry(
        "/field",
        visibility=visibility,
        perspective_player_id=("player-1" if visibility == "local_private" else None),
        available_from=("game_end" if visibility == "post_game_only" else "request_start"),
    )
    assert entry.visibility == visibility


@pytest.mark.parametrize(
    ("available_from", "decision_index", "event_index"),
    (
        ("request_start", None, None),
        ("current_decision", 0, None),
        ("after_public_event", None, 0),
        ("after_actual_play", 0, None),
        ("game_end", None, None),
        ("offline_review", None, None),
    ),
)
def test_entry_supports_every_availability_boundary(
    available_from: str, decision_index: int | None, event_index: int | None
) -> None:
    entry = _entry(
        "/field",
        available_from=available_from,
        available_from_decision_index=decision_index,
        available_from_event_index=event_index,
    )
    assert entry.available_from == available_from


@pytest.mark.parametrize("derivation", FIELD_PROVENANCE_DERIVATION_TYPES)
def test_entry_supports_every_derivation_type(derivation: str) -> None:
    assert _entry("/field", derivation=derivation).derivation == derivation


@pytest.mark.parametrize(
    ("origin", "derivation"),
    (
        ("rule_derived", "direct"),
        ("dataset_assignment", "heuristic"),
        ("retrospective_attachment", "direct"),
        ("sampled_estimate", "exact_aggregate"),
        ("compatible_world_aggregate", "direct"),
    ),
)
def test_entry_enforces_hard_origin_derivation_rules(origin: str, derivation: str) -> None:
    with pytest.raises(SkatMindValidationError) as exc_info:
        _entry(
            "/field",
            origin=origin,
            derivation=derivation,
            available_from=(
                "after_actual_play"
                if origin == "retrospective_attachment"
                else "request_start"
            ),
            available_from_decision_index=(0 if origin == "retrospective_attachment" else None),
        )
    assert exc_info.value.path == "/field"


@pytest.mark.parametrize("derivation", ("exact_aggregate", "sampled_aggregate"))
def test_compatible_world_aggregate_accepts_both_aggregate_derivations(
    derivation: str,
) -> None:
    assert (
        _entry(
            "/field",
            origin="compatible_world_aggregate",
            derivation=derivation,
        ).derivation
        == derivation
    )


@pytest.mark.parametrize(
    ("available_from", "decision_index", "event_index"),
    (
        ("current_decision", None, None),
        ("after_actual_play", None, None),
        ("after_public_event", None, None),
        ("request_start", 0, None),
        ("game_end", None, 0),
        ("offline_review", 0, None),
    ),
)
def test_entry_enforces_availability_index_requirements(
    available_from: str, decision_index: int | None, event_index: int | None
) -> None:
    with pytest.raises(SkatMindValidationError):
        _entry(
            "/field",
            available_from=available_from,
            available_from_decision_index=decision_index,
            available_from_event_index=event_index,
        )


@pytest.mark.parametrize("index", (-1, True, 1.5, "1"))
def test_entry_rejects_invalid_availability_indexes(index: object) -> None:
    with pytest.raises(SkatMindValidationError):
        _entry(
            "/field",
            available_from="current_decision",
            available_from_decision_index=index,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("player_id", ("", " player", "player ", 1))
def test_entry_rejects_invalid_optional_player_id(player_id: object) -> None:
    with pytest.raises(SkatMindValidationError):
        _entry("/field", subject_player_id=player_id)  # type: ignore[arg-type]


def test_local_private_requires_a_perspective_player() -> None:
    with pytest.raises(SkatMindValidationError, match="perspective_player_id"):
        _entry("/field", visibility="local_private")


@pytest.mark.parametrize(
    "available_from",
    ("request_start", "current_decision", "after_public_event"),
)
def test_retrospective_origin_rejects_early_availability(available_from: str) -> None:
    with pytest.raises(SkatMindValidationError):
        _entry(
            "/field",
            origin="retrospective_attachment",
            derivation="retrospective",
            available_from=available_from,
            available_from_decision_index=(0 if available_from == "current_decision" else None),
            available_from_event_index=(0 if available_from == "after_public_event" else None),
        )


@pytest.mark.parametrize(
    "available_from",
    ("request_start", "current_decision", "after_public_event", "after_actual_play"),
)
def test_post_game_visibility_rejects_early_availability(available_from: str) -> None:
    with pytest.raises(SkatMindValidationError):
        _entry(
            "/field",
            visibility="post_game_only",
            available_from=available_from,
            available_from_decision_index=(
                0
                if available_from in {"current_decision", "after_actual_play"}
                else None
            ),
            available_from_event_index=(0 if available_from == "after_public_event" else None),
        )


def test_entry_has_no_confidence_or_free_text_fields() -> None:
    field_names = {item.name for item in fields(FieldProvenanceEntry)}
    assert field_names == {
        "field_path",
        "coverage_kind",
        "origin",
        "visibility",
        "available_from",
        "available_from_decision_index",
        "available_from_event_index",
        "derivation",
        "source_references",
        "dependency_paths",
        "subject_player_id",
        "perspective_player_id",
    }
    assert not field_names.intersection(
        {"confidence", "probability", "severity", "quality", "calibration", "notes"}
    )


@pytest.mark.parametrize("reason", FIELD_PROVENANCE_EXEMPTION_REASONS)
def test_exemption_supports_every_reason_and_is_immutable(reason: str) -> None:
    exemption = FieldProvenanceExemption(
        field_path="/field",
        coverage_kind="subtree",
        reason=reason,
    )
    assert exemption.reason == reason
    with pytest.raises(FrozenInstanceError):
        exemption.reason = "not_applicable"  # type: ignore[misc]


def test_ledger_canonicalizes_entries_exemptions_and_limitations() -> None:
    source_entries = [_entry("/z"), _entry("/a")]
    source_exemptions = [
        FieldProvenanceExemption(
            field_path="/y", coverage_kind="field", reason="schema_constant"
        ),
        FieldProvenanceExemption(
            field_path="/b", coverage_kind="field", reason="not_applicable"
        ),
    ]
    ledger = FieldProvenanceLedger(
        entries=source_entries,  # type: ignore[arg-type]
        exemptions=source_exemptions,  # type: ignore[arg-type]
        limitations=[],  # type: ignore[arg-type]
        status="complete",
    )
    source_entries.clear()
    source_exemptions.clear()
    assert tuple(entry.field_path for entry in ledger.entries) == ("/a", "/z")
    assert tuple(exemption.field_path for exemption in ledger.exemptions) == ("/b", "/y")
    assert ledger.limitations == ()
    assert ledger.provenance_version == 1
    with pytest.raises(FrozenInstanceError):
        ledger.status = "not_available"  # type: ignore[misc]
    assert not hasattr(ledger, "__dict__")


def test_ledger_status_relationships_are_exact() -> None:
    complete = FieldProvenanceLedger(
        status="complete", entries=(_entry("/field"),), exemptions=(), limitations=()
    )
    partial = FieldProvenanceLedger(
        status="partial_legacy",
        entries=(),
        exemptions=(
            FieldProvenanceExemption(
                field_path="", coverage_kind="subtree", reason="legacy_untracked"
            ),
        ),
        limitations=("legacy_untracked_fields",),
    )
    unavailable = FieldProvenanceLedger(
        status="not_available",
        entries=(),
        exemptions=(),
        limitations=("provenance_not_available",),
    )
    assert complete.status == "complete"
    assert partial.status == "partial_legacy"
    assert unavailable.status == "not_available"


@pytest.mark.parametrize(
    ("status", "entries", "exemptions", "limitations"),
    (
        (
            "complete",
            (),
            (
                FieldProvenanceExemption(
                    field_path="",
                    coverage_kind="subtree",
                    reason="legacy_untracked",
                ),
            ),
            (),
        ),
        ("complete", (), (), ("legacy_untracked_fields",)),
        ("complete", (), (), ("provenance_not_available",)),
        ("partial_legacy", (), (), ("legacy_untracked_fields",)),
        (
            "partial_legacy",
            (),
            (
                FieldProvenanceExemption(
                    field_path="",
                    coverage_kind="subtree",
                    reason="legacy_untracked",
                ),
            ),
            (),
        ),
        ("not_available", (_entry("/field"),), (), ("provenance_not_available",)),
        (
            "not_available",
            (),
            (
                FieldProvenanceExemption(
                    field_path="",
                    coverage_kind="field",
                    reason="not_applicable",
                ),
            ),
            ("provenance_not_available",),
        ),
        ("not_available", (), (), ()),
    ),
)
def test_ledger_rejects_invalid_status_combinations(
    status: str,
    entries: tuple[FieldProvenanceEntry, ...],
    exemptions: tuple[FieldProvenanceExemption, ...],
    limitations: tuple[str, ...],
) -> None:
    with pytest.raises(SkatMindValidationError):
        FieldProvenanceLedger(
            status=status,
            entries=entries,
            exemptions=exemptions,
            limitations=limitations,
        )


def test_ledger_rejects_duplicate_paths_limitations_and_entry_exemption_overlap() -> None:
    with pytest.raises(SkatMindValidationError, match="Duplicate entry"):
        FieldProvenanceLedger(
            status="complete",
            entries=(_entry("/field"), _entry("/field")),
            exemptions=(),
            limitations=(),
        )
    with pytest.raises(SkatMindValidationError, match="Duplicate limitation"):
        FieldProvenanceLedger(
            status="complete",
            entries=(),
            exemptions=(),
            limitations=("legacy_untracked_fields", "legacy_untracked_fields"),
        )
    with pytest.raises(SkatMindValidationError, match="only by public redaction"):
        FieldProvenanceLedger(
            status="complete",
            entries=(),
            exemptions=(),
            limitations=("private_dependencies_redacted",),
        )
    with pytest.raises(SkatMindValidationError, match="only by public redaction"):
        FieldProvenanceLedger(
            status="complete",
            entries=(),
            exemptions=(),
            limitations=("private_dependencies_redacted",),
            _public_redaction_token=True,
        )
    with pytest.raises(SkatMindValidationError, match="overlap"):
        FieldProvenanceLedger(
            status="complete",
            entries=(_entry("/object", coverage_kind="subtree"),),
            exemptions=(
                FieldProvenanceExemption(
                    field_path="/object/value",
                    coverage_kind="field",
                    reason="schema_constant",
                ),
            ),
            limitations=(),
        )


def test_ledger_validates_dependencies_cycles_and_temporal_monotonicity() -> None:
    valid = FieldProvenanceLedger(
        status="complete",
        entries=(
            _entry("/source"),
            _entry(
                "/derived",
                origin="rule_derived",
                derivation="deterministic_rule",
                dependency_paths=("/source",),
            ),
        ),
        exemptions=(),
        limitations=(),
    )
    assert valid.entries[0].field_path == "/derived"

    with pytest.raises(SkatMindValidationError, match="existing entry"):
        FieldProvenanceLedger(
            status="complete",
            entries=(_entry("/derived", dependency_paths=("/missing",)),),
            exemptions=(),
            limitations=(),
        )
    with pytest.raises(SkatMindValidationError, match="exemption"):
        FieldProvenanceLedger(
            status="complete",
            entries=(_entry("/derived", dependency_paths=("/constant",)),),
            exemptions=(
                FieldProvenanceExemption(
                    field_path="/constant", coverage_kind="field", reason="schema_constant"
                ),
            ),
            limitations=(),
        )
    with pytest.raises(SkatMindValidationError, match="exemption"):
        FieldProvenanceLedger(
            status="complete",
            entries=(_entry("/derived", dependency_paths=("/legacy/value",)),),
            exemptions=(
                FieldProvenanceExemption(
                    field_path="/legacy",
                    coverage_kind="subtree",
                    reason="schema_constant",
                ),
            ),
            limitations=(),
        )
    with pytest.raises(SkatMindValidationError, match="cycle"):
        FieldProvenanceLedger(
            status="complete",
            entries=(
                _entry("/a", dependency_paths=("/b",)),
                _entry("/b", dependency_paths=("/a",)),
            ),
            exemptions=(),
            limitations=(),
        )
    with pytest.raises(SkatMindValidationError, match="cycle"):
        FieldProvenanceLedger(
            status="complete",
            entries=(
                _entry("/a", dependency_paths=("/b",)),
                _entry("/b", dependency_paths=("/c",)),
                _entry("/c", dependency_paths=("/a",)),
            ),
            exemptions=(),
            limitations=(),
        )


@pytest.mark.parametrize(
    ("derived", "dependency"),
    (
        (
            _entry(
                "/derived",
                available_from="current_decision",
                available_from_decision_index=2,
                dependency_paths=("/source",),
            ),
            _entry(
                "/source",
                available_from="current_decision",
                available_from_decision_index=3,
            ),
        ),
        (
            _entry(
                "/derived",
                available_from="current_decision",
                available_from_decision_index=1,
                dependency_paths=("/source",),
            ),
            _entry(
                "/source",
                available_from="after_actual_play",
                available_from_decision_index=1,
            ),
        ),
        (
            _entry(
                "/derived",
                available_from="after_actual_play",
                available_from_decision_index=1,
                dependency_paths=("/source",),
            ),
            _entry("/source", available_from="game_end"),
        ),
        (
            _entry("/derived", available_from="game_end", dependency_paths=("/source",)),
            _entry("/source", available_from="offline_review"),
        ),
    ),
)
def test_ledger_rejects_backward_temporal_dependencies(
    derived: FieldProvenanceEntry, dependency: FieldProvenanceEntry
) -> None:
    with pytest.raises(SkatMindValidationError, match="availability") as exc_info:
        FieldProvenanceLedger(
            status="complete",
            entries=(derived, dependency),
            exemptions=(),
            limitations=(),
        )
    assert exc_info.value.path == "/derived"


def test_ledger_accepts_earlier_and_same_index_dependencies() -> None:
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=(
            _entry("/request"),
            _entry(
                "/decision-1",
                available_from="current_decision",
                available_from_decision_index=1,
                dependency_paths=("/request",),
            ),
            _entry(
                "/decision-2",
                available_from="current_decision",
                available_from_decision_index=2,
                dependency_paths=("/decision-1",),
            ),
            _entry(
                "/review",
                available_from="offline_review",
                dependency_paths=("/decision-2",),
            ),
        ),
        exemptions=(),
        limitations=(),
    )
    assert len(ledger.entries) == 4


def test_field_provenance_serialization_is_deterministic_explicit_and_not_transitive() -> None:
    reference = FieldProvenanceSourceReference(
        reference_type="request",
        reference_id="request-1",
        field_path="/input",
        visibility="public",
    )
    source = _entry("/source", source_references=(reference,))
    derived = _entry(
        "/derived",
        origin="rule_derived",
        derivation="deterministic_rule",
        dependency_paths=("/source",),
        subject_player_id="player-1",
    )
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=(source, derived),
        exemptions=(
            FieldProvenanceExemption(
                field_path="/constant", coverage_kind="field", reason="schema_constant"
            ),
        ),
        limitations=(),
    )

    assert build_serializable_field_provenance_entry(derived) == {
        "field_path": "/derived",
        "coverage_kind": "field",
        "origin": "rule_derived",
        "visibility": "public",
        "available_from": "request_start",
        "available_from_decision_index": None,
        "available_from_event_index": None,
        "derivation": "deterministic_rule",
        "source_references": [],
        "dependency_paths": ["/source"],
        "subject_player_id": "player-1",
        "perspective_player_id": None,
    }
    assert build_serializable_field_provenance_exemption(ledger.exemptions[0]) == {
        "field_path": "/constant",
        "coverage_kind": "field",
        "reason": "schema_constant",
    }
    serialized = build_serializable_field_provenance_ledger(ledger)
    assert serialized == build_serializable_field_provenance_ledger(ledger)
    assert serialized["provenance_version"] == 1
    assert serialized["status"] == "complete"
    assert serialized["limitations"] == []
    assert serialized["entries"][0]["dependency_paths"] == ["/source"]
    assert "/input" not in serialized["entries"][0]["dependency_paths"]
    assert "confidence" not in repr(serialized)


def test_public_ledger_serialization_rejects_unredacted_private_details_generically() -> None:
    private_reference_ledger = FieldProvenanceLedger(
        status="complete",
        entries=(
            _entry(
                "/public",
                source_references=(
                    FieldProvenanceSourceReference(
                        reference_type="algorithm",
                        reference_id="secret-reference-id",
                        field_path="/secret/reference/path",
                        visibility="engine_private",
                    ),
                ),
            ),
        ),
        exemptions=(),
        limitations=(),
    )
    with pytest.raises(SkatMindSerializationError) as exc_info:
        build_public_serializable_field_provenance_ledger(private_reference_ledger)
    serialized_error = repr(exc_info.value.to_dict())
    assert "secret-reference-id" not in serialized_error
    assert "/secret/reference/path" not in serialized_error

    private_entry_ledger = FieldProvenanceLedger(
        status="complete",
        entries=(_entry("/secret/entry", visibility="engine_private"),),
        exemptions=(),
        limitations=(),
    )
    with pytest.raises(SkatMindSerializationError) as private_entry_error:
        build_public_serializable_field_provenance_ledger(private_entry_ledger)
    assert "/secret/entry" not in repr(private_entry_error.value.to_dict())
