from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import InitVar, dataclass
from typing import Any

from skat_ai.errors import SkatAISerializationError, SkatAIValidationError

FIELD_PROVENANCE_VERSION = 1
FIELD_PROVENANCE_PATH_POLICY = "rfc6901_json_pointer"
FIELD_PROVENANCE_CONFIDENCE_POLICY = "separate_contract"
FIELD_PROVENANCE_PUBLIC_REDACTION_POLICY = "omit_engine_private_details"

FIELD_PROVENANCE_STATUSES = ("complete", "partial_legacy", "not_available")
FIELD_PROVENANCE_COVERAGE_KINDS = ("field", "subtree")
FIELD_PROVENANCE_ORIGINS = (
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
FIELD_PROVENANCE_VISIBILITY_SCOPES = (
    "public",
    "local_private",
    "declarer_private",
    "defender_private",
    "post_game_only",
    "engine_private",
)
FIELD_PROVENANCE_AVAILABILITY_BOUNDARIES = (
    "request_start",
    "current_decision",
    "after_public_event",
    "after_actual_play",
    "game_end",
    "offline_review",
)
FIELD_PROVENANCE_DERIVATION_TYPES = (
    "direct",
    "validated",
    "deterministic_rule",
    "reconstruction",
    "exact_aggregate",
    "sampled_aggregate",
    "heuristic",
    "retrospective",
)
FIELD_PROVENANCE_REFERENCE_TYPES = (
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
FIELD_PROVENANCE_EXEMPTION_REASONS = (
    "legacy_untracked",
    "schema_constant",
    "not_applicable",
)
FIELD_PROVENANCE_LIMITATIONS = (
    "legacy_untracked_fields",
    "private_dependencies_redacted",
    "provenance_not_available",
)

_PUBLIC_REDACTION_TOKEN = object()

_AVAILABILITY_RANKS = {
    "request_start": 0,
    "current_decision": 1,
    "after_public_event": 1,
    "after_actual_play": 2,
    "game_end": 3,
    "offline_review": 4,
}


def _validation_error(message: str, *, path: str) -> SkatAIValidationError:
    return SkatAIValidationError(message, path=path)


def _validate_choice(value: object, choices: tuple[str, ...], *, path: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise _validation_error(
            f"{path} must be one of {list(choices)}.",
            path=path,
        )
    return value


def _validate_identifier(value: object, *, path: str, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise _validation_error(
            f"{path} must be a non-empty, non-padded string"
            + (" or null." if optional else "."),
            path=path,
        )
    return value


def _validate_optional_index(value: object, *, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _validation_error(
            f"{path} must be a non-negative integer or null.",
            path=path,
        )
    return value


def _copy_tuple(value: object, *, path: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise _validation_error(f"{path} must be an immutable-compatible array.", path=path)
    return tuple(value)


def escape_json_pointer_token(token: str) -> str:
    """Escapes one RFC 6901 JSON Pointer reference token."""
    if not isinstance(token, str):
        raise _validation_error("JSON Pointer tokens must be strings.", path="token")
    return token.replace("~", "~0").replace("/", "~1")


def unescape_json_pointer_token(token: str) -> str:
    """Strictly decodes one RFC 6901 JSON Pointer reference token."""
    if not isinstance(token, str):
        raise _validation_error("JSON Pointer tokens must be strings.", path="token")
    result: list[str] = []
    index = 0
    while index < len(token):
        character = token[index]
        if character != "~":
            result.append(character)
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise _validation_error(
                "JSON Pointer tokens may use only '~0' and '~1' escapes.",
                path="token",
            )
        result.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(result)


def build_json_pointer(tokens: Sequence[str]) -> str:
    """Builds the canonical JSON Pointer for an ordered token sequence."""
    if isinstance(tokens, (str, bytes)) or not isinstance(tokens, Sequence):
        raise _validation_error("tokens must be an ordered string sequence.", path="tokens")
    copied = tuple(tokens)
    if any(not isinstance(token, str) for token in copied):
        raise _validation_error("tokens must contain only strings.", path="tokens")
    if not copied:
        return ""
    return "/" + "/".join(escape_json_pointer_token(token) for token in copied)


def parse_json_pointer(pointer: str) -> tuple[str, ...]:
    """Parses and validates one canonical RFC 6901 JSON Pointer."""
    if not isinstance(pointer, str):
        raise _validation_error("JSON Pointer paths must be strings.", path="field_path")
    if pointer == "":
        return ()
    if not pointer.startswith("/"):
        raise _validation_error(
            "Non-root JSON Pointer paths must begin with '/'.",
            path=pointer,
        )
    try:
        tokens = tuple(unescape_json_pointer_token(token) for token in pointer[1:].split("/"))
    except SkatAIValidationError as error:
        raise _validation_error(error.message, path=pointer) from error
    if build_json_pointer(tokens) != pointer:
        raise _validation_error("JSON Pointer path is not canonical.", path=pointer)
    return tokens


def resolve_json_pointer(document: object, pointer: str) -> object:
    """Resolves one JSON Pointer without applying filesystem-path semantics."""
    tokens = parse_json_pointer(pointer)
    value = document
    for token in tokens:
        if isinstance(value, Mapping):
            if token not in value:
                raise _validation_error(
                    "JSON Pointer does not identify an existing object key.",
                    path=pointer,
                )
            value = value[token]
            continue
        if isinstance(value, (list, tuple)):
            if not token.isascii() or not token.isdecimal() or (
                len(token) > 1 and token.startswith("0")
            ):
                raise _validation_error(
                    "JSON Pointer array index must be a canonical non-negative integer.",
                    path=pointer,
                )
            index = int(token)
            if index >= len(value):
                raise _validation_error(
                    "JSON Pointer array index is outside the array.",
                    path=pointer,
                )
            value = value[index]
            continue
        raise _validation_error(
            "JSON Pointer cannot traverse into a scalar value.",
            path=pointer,
        )
    return value


def _validate_json_pointer(pointer: object, *, path: str) -> str:
    if not isinstance(pointer, str):
        raise _validation_error(f"{path} must be a JSON Pointer string.", path=path)
    try:
        parse_json_pointer(pointer)
    except SkatAIValidationError as error:
        raise _validation_error(error.message, path=path) from error
    return pointer


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceSourceReference:
    """Structured identity for one source without embedding its value."""

    reference_type: str
    reference_id: str
    field_path: str | None
    visibility: str

    def __post_init__(self) -> None:
        _validate_choice(
            self.reference_type,
            FIELD_PROVENANCE_REFERENCE_TYPES,
            path="reference_type",
        )
        _validate_identifier(self.reference_id, path="reference_id")
        if self.field_path is not None:
            _validate_json_pointer(self.field_path, path="field_path")
        _validate_choice(
            self.visibility,
            FIELD_PROVENANCE_VISIBILITY_SCOPES,
            path="visibility",
        )


def _source_reference_sort_key(
    reference: FieldProvenanceSourceReference,
) -> tuple[str, str, bool, str, str]:
    return (
        reference.reference_type,
        reference.reference_id,
        reference.field_path is not None,
        reference.field_path or "",
        reference.visibility,
    )


def _canonicalize_source_references(value: object) -> tuple[FieldProvenanceSourceReference, ...]:
    copied = _copy_tuple(value, path="source_references")
    if any(not isinstance(item, FieldProvenanceSourceReference) for item in copied):
        raise _validation_error(
            "source_references must contain only FieldProvenanceSourceReference values.",
            path="source_references",
        )
    if len(copied) != len(set(copied)):
        raise _validation_error(
            "Duplicate source references are not allowed.",
            path="source_references",
        )
    return tuple(sorted(copied, key=_source_reference_sort_key))


def _canonicalize_dependency_paths(value: object, *, field_path: str) -> tuple[str, ...]:
    copied = _copy_tuple(value, path="dependency_paths")
    paths = tuple(
        _validate_json_pointer(item, path="dependency_paths") for item in copied
    )
    if len(paths) != len(set(paths)):
        raise _validation_error(
            "Duplicate dependency paths are not allowed.",
            path=field_path,
        )
    if field_path in paths:
        raise _validation_error(
            "A provenance entry cannot depend on itself.",
            path=field_path,
        )
    return tuple(sorted(paths))


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceEntry:
    """Immutable provenance for one exact field or current document subtree."""

    field_path: str
    coverage_kind: str
    origin: str
    visibility: str
    available_from: str
    available_from_decision_index: int | None
    available_from_event_index: int | None
    derivation: str
    source_references: tuple[FieldProvenanceSourceReference, ...]
    dependency_paths: tuple[str, ...]
    subject_player_id: str | None
    perspective_player_id: str | None

    def __post_init__(self) -> None:
        field_path = _validate_json_pointer(self.field_path, path="field_path")
        _validate_choice(
            self.coverage_kind,
            FIELD_PROVENANCE_COVERAGE_KINDS,
            path=field_path,
        )
        _validate_choice(self.origin, FIELD_PROVENANCE_ORIGINS, path=field_path)
        _validate_choice(
            self.visibility,
            FIELD_PROVENANCE_VISIBILITY_SCOPES,
            path=field_path,
        )
        _validate_choice(
            self.available_from,
            FIELD_PROVENANCE_AVAILABILITY_BOUNDARIES,
            path=field_path,
        )
        decision_index = _validate_optional_index(
            self.available_from_decision_index,
            path="available_from_decision_index",
        )
        event_index = _validate_optional_index(
            self.available_from_event_index,
            path="available_from_event_index",
        )
        _validate_choice(
            self.derivation,
            FIELD_PROVENANCE_DERIVATION_TYPES,
            path=field_path,
        )
        references = _canonicalize_source_references(self.source_references)
        dependencies = _canonicalize_dependency_paths(
            self.dependency_paths,
            field_path=field_path,
        )
        _validate_identifier(
            self.subject_player_id,
            path="subject_player_id",
            optional=True,
        )
        _validate_identifier(
            self.perspective_player_id,
            path="perspective_player_id",
            optional=True,
        )

        if self.available_from in {"current_decision", "after_actual_play"}:
            if decision_index is None:
                raise _validation_error(
                    f"{self.available_from} requires available_from_decision_index.",
                    path=field_path,
                )
        elif self.available_from == "after_public_event" and event_index is None:
            raise _validation_error(
                "after_public_event requires available_from_event_index.",
                path=field_path,
            )
        elif self.available_from in {"request_start", "game_end", "offline_review"} and (
            decision_index is not None or event_index is not None
        ):
            raise _validation_error(
                f"{self.available_from} requires both availability indexes to be null.",
                path=field_path,
            )

        if self.visibility == "local_private" and self.perspective_player_id is None:
            raise _validation_error(
                "local_private visibility requires perspective_player_id.",
                path=field_path,
            )

        required_derivations: dict[str, tuple[str, ...]] = {
            "rule_derived": ("deterministic_rule",),
            "dataset_assignment": ("deterministic_rule",),
            "retrospective_attachment": ("retrospective",),
            "sampled_estimate": ("sampled_aggregate",),
            "compatible_world_aggregate": ("exact_aggregate", "sampled_aggregate"),
        }
        allowed_derivations = required_derivations.get(self.origin)
        if allowed_derivations is not None and self.derivation not in allowed_derivations:
            raise _validation_error(
                f"origin {self.origin!r} requires derivation in {list(allowed_derivations)}.",
                path=field_path,
            )
        if self.origin == "retrospective_attachment" and self.available_from not in {
            "after_actual_play",
            "game_end",
            "offline_review",
        }:
            raise _validation_error(
                "retrospective_attachment requires retrospective availability.",
                path=field_path,
            )
        if self.visibility == "post_game_only" and self.available_from not in {
            "game_end",
            "offline_review",
        }:
            raise _validation_error(
                "post_game_only visibility requires game_end or offline_review availability.",
                path=field_path,
            )

        object.__setattr__(self, "source_references", references)
        object.__setattr__(self, "dependency_paths", dependencies)


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceExemption:
    """Explicit reason why one exact field or subtree has no normal provenance."""

    field_path: str
    coverage_kind: str
    reason: str

    def __post_init__(self) -> None:
        field_path = _validate_json_pointer(self.field_path, path="field_path")
        _validate_choice(
            self.coverage_kind,
            FIELD_PROVENANCE_COVERAGE_KINDS,
            path=field_path,
        )
        _validate_choice(
            self.reason,
            FIELD_PROVENANCE_EXEMPTION_REASONS,
            path=field_path,
        )


def _is_path_at_or_below(path: str, ancestor: str) -> bool:
    path_tokens = parse_json_pointer(path)
    ancestor_tokens = parse_json_pointer(ancestor)
    return path_tokens[: len(ancestor_tokens)] == ancestor_tokens


def _coverage_declarations_overlap(
    first_path: str,
    first_kind: str,
    second_path: str,
    second_kind: str,
) -> bool:
    if first_kind == "field" and second_kind == "field":
        return first_path == second_path
    if first_kind == "subtree" and _is_path_at_or_below(second_path, first_path):
        return True
    return second_kind == "subtree" and _is_path_at_or_below(first_path, second_path)


def _canonicalize_entries(value: object) -> tuple[FieldProvenanceEntry, ...]:
    copied = _copy_tuple(value, path="entries")
    if any(not isinstance(item, FieldProvenanceEntry) for item in copied):
        raise _validation_error(
            "entries must contain only FieldProvenanceEntry values.",
            path="entries",
        )
    paths = tuple(item.field_path for item in copied)
    if len(paths) != len(set(paths)):
        raise _validation_error("Duplicate entry paths are not allowed.", path="entries")
    return tuple(sorted(copied, key=lambda item: item.field_path))


def _canonicalize_exemptions(value: object) -> tuple[FieldProvenanceExemption, ...]:
    copied = _copy_tuple(value, path="exemptions")
    if any(not isinstance(item, FieldProvenanceExemption) for item in copied):
        raise _validation_error(
            "exemptions must contain only FieldProvenanceExemption values.",
            path="exemptions",
        )
    paths = tuple(item.field_path for item in copied)
    if len(paths) != len(set(paths)):
        raise _validation_error(
            "Duplicate exemption paths are not allowed.",
            path="exemptions",
        )
    return tuple(sorted(copied, key=lambda item: item.field_path))


def _canonicalize_limitations(value: object) -> tuple[str, ...]:
    copied = _copy_tuple(value, path="limitations")
    limitations = tuple(
        _validate_choice(item, FIELD_PROVENANCE_LIMITATIONS, path="limitations")
        for item in copied
    )
    if len(limitations) != len(set(limitations)):
        raise _validation_error(
            "Duplicate limitations are not allowed.",
            path="limitations",
        )
    order = {item: index for index, item in enumerate(FIELD_PROVENANCE_LIMITATIONS)}
    return tuple(sorted(limitations, key=order.__getitem__))


def _validate_entry_exemption_overlap(
    entries: tuple[FieldProvenanceEntry, ...],
    exemptions: tuple[FieldProvenanceExemption, ...],
) -> None:
    for entry in entries:
        for exemption in exemptions:
            if _coverage_declarations_overlap(
                entry.field_path,
                entry.coverage_kind,
                exemption.field_path,
                exemption.coverage_kind,
            ):
                raise _validation_error(
                    "Provenance entry and exemption coverage may not overlap.",
                    path=entry.field_path,
                )


def _validate_status_relationships(
    status: str,
    entries: tuple[FieldProvenanceEntry, ...],
    exemptions: tuple[FieldProvenanceExemption, ...],
    limitations: tuple[str, ...],
) -> None:
    has_legacy_exemption = any(item.reason == "legacy_untracked" for item in exemptions)
    if status == "complete":
        if has_legacy_exemption:
            raise _validation_error(
                "complete provenance cannot contain legacy_untracked exemptions.",
                path="status",
            )
        if {"legacy_untracked_fields", "provenance_not_available"}.intersection(limitations):
            raise _validation_error(
                "complete provenance cannot contain legacy or unavailable limitations.",
                path="limitations",
            )
        return
    if status == "partial_legacy":
        if not has_legacy_exemption:
            raise _validation_error(
                "partial_legacy requires a legacy_untracked exemption.",
                path="status",
            )
        if "legacy_untracked_fields" not in limitations:
            raise _validation_error(
                "partial_legacy requires legacy_untracked_fields.",
                path="limitations",
            )
        if "provenance_not_available" in limitations:
            raise _validation_error(
                "partial_legacy cannot contain provenance_not_available.",
                path="limitations",
            )
        return
    if entries or exemptions or limitations != ("provenance_not_available",):
        raise _validation_error(
            "not_available requires no entries or exemptions and only "
            "provenance_not_available.",
            path="status",
        )


def _validate_dependency_graph(
    entries: tuple[FieldProvenanceEntry, ...],
    exemptions: tuple[FieldProvenanceExemption, ...],
) -> None:
    entries_by_path = {entry.field_path: entry for entry in entries}
    exemption_paths = {exemption.field_path for exemption in exemptions}
    for entry in entries:
        for dependency_path in entry.dependency_paths:
            dependency_is_exempted = dependency_path in exemption_paths or any(
                _coverage_declarations_overlap(
                    dependency_path,
                    "field",
                    exemption.field_path,
                    exemption.coverage_kind,
                )
                for exemption in exemptions
            )
            if dependency_is_exempted:
                raise _validation_error(
                    "A provenance dependency cannot identify an exemption.",
                    path=entry.field_path,
                )
            dependency = entries_by_path.get(dependency_path)
            if dependency is None:
                raise _validation_error(
                    "Every provenance dependency must identify an existing entry.",
                    path=entry.field_path,
                )
            if _AVAILABILITY_RANKS[entry.available_from] < _AVAILABILITY_RANKS[
                dependency.available_from
            ]:
                raise _validation_error(
                    "A derived entry cannot precede its dependency availability.",
                    path=entry.field_path,
                )
            if entry.available_from == dependency.available_from:
                if entry.available_from in {"current_decision", "after_actual_play"} and (
                    entry.available_from_decision_index
                    < dependency.available_from_decision_index
                ):
                    raise _validation_error(
                        "A derived entry cannot precede its dependency availability index.",
                        path=entry.field_path,
                    )
                if entry.available_from == "after_public_event" and (
                    entry.available_from_event_index < dependency.available_from_event_index
                ):
                    raise _validation_error(
                        "A derived entry cannot precede its dependency availability index.",
                        path=entry.field_path,
                    )

    visit_state: dict[str, int] = {}

    def visit(path: str) -> None:
        state = visit_state.get(path, 0)
        if state == 1:
            raise _validation_error(
                "Field provenance dependencies contain a cycle.",
                path=path,
            )
        if state == 2:
            return
        visit_state[path] = 1
        for dependency_path in entries_by_path[path].dependency_paths:
            visit(dependency_path)
        visit_state[path] = 2

    for path in sorted(entries_by_path):
        visit(path)


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceLedger:
    """Immutable version-1 sidecar ledger for one JSON document."""

    status: str
    entries: tuple[FieldProvenanceEntry, ...]
    exemptions: tuple[FieldProvenanceExemption, ...]
    limitations: tuple[str, ...]
    provenance_version: int = FIELD_PROVENANCE_VERSION
    _public_redaction_token: InitVar[object | None] = None

    def __post_init__(self, _public_redaction_token: object | None) -> None:
        if type(self.provenance_version) is not int or (
            self.provenance_version != FIELD_PROVENANCE_VERSION
        ):
            raise _validation_error(
                f"provenance_version must equal {FIELD_PROVENANCE_VERSION}.",
                path="provenance_version",
            )
        _validate_choice(self.status, FIELD_PROVENANCE_STATUSES, path="status")
        entries = _canonicalize_entries(self.entries)
        exemptions = _canonicalize_exemptions(self.exemptions)
        limitations = _canonicalize_limitations(self.limitations)
        if (
            "private_dependencies_redacted" in limitations
            and _public_redaction_token is not _PUBLIC_REDACTION_TOKEN
        ):
            raise _validation_error(
                "private_dependencies_redacted may be added only by public redaction.",
                path="limitations",
            )
        _validate_entry_exemption_overlap(entries, exemptions)
        _validate_status_relationships(
            self.status,
            entries,
            exemptions,
            limitations,
        )
        _validate_dependency_graph(entries, exemptions)
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "exemptions", exemptions)
        object.__setattr__(self, "limitations", limitations)


def build_serializable_field_provenance_source_reference(
    reference: FieldProvenanceSourceReference,
) -> dict[str, str | None]:
    """Serializes one source reference without embedding source values."""
    return {
        "reference_type": reference.reference_type,
        "reference_id": reference.reference_id,
        "field_path": reference.field_path,
        "visibility": reference.visibility,
    }


def build_serializable_field_provenance_entry(
    entry: FieldProvenanceEntry,
) -> dict[str, Any]:
    """Serializes one provenance entry without expanding dependency closure."""
    return {
        "field_path": entry.field_path,
        "coverage_kind": entry.coverage_kind,
        "origin": entry.origin,
        "visibility": entry.visibility,
        "available_from": entry.available_from,
        "available_from_decision_index": entry.available_from_decision_index,
        "available_from_event_index": entry.available_from_event_index,
        "derivation": entry.derivation,
        "source_references": [
            build_serializable_field_provenance_source_reference(reference)
            for reference in entry.source_references
        ],
        "dependency_paths": list(entry.dependency_paths),
        "subject_player_id": entry.subject_player_id,
        "perspective_player_id": entry.perspective_player_id,
    }


def build_serializable_field_provenance_exemption(
    exemption: FieldProvenanceExemption,
) -> dict[str, str]:
    """Serializes one explicit provenance exemption."""
    return {
        "field_path": exemption.field_path,
        "coverage_kind": exemption.coverage_kind,
        "reason": exemption.reason,
    }


def build_serializable_field_provenance_ledger(
    ledger: FieldProvenanceLedger,
) -> dict[str, Any]:
    """Builds the deterministic internal ledger representation."""
    if not isinstance(ledger, FieldProvenanceLedger):
        raise SkatAISerializationError("Value is not a FieldProvenanceLedger.")
    return {
        "provenance_version": ledger.provenance_version,
        "status": ledger.status,
        "entries": [build_serializable_field_provenance_entry(entry) for entry in ledger.entries],
        "exemptions": [
            build_serializable_field_provenance_exemption(exemption)
            for exemption in ledger.exemptions
        ],
        "limitations": list(ledger.limitations),
    }


def build_public_serializable_field_provenance_ledger(
    ledger: FieldProvenanceLedger,
) -> dict[str, Any]:
    """Serializes only a ledger that contains no unredacted engine-private detail."""
    if not isinstance(ledger, FieldProvenanceLedger):
        raise SkatAISerializationError("Value is not a FieldProvenanceLedger.")
    entry_paths = {entry.field_path for entry in ledger.entries}
    unsafe = any(entry.visibility == "engine_private" for entry in ledger.entries)
    unsafe = unsafe or any(
        reference.visibility == "engine_private"
        for entry in ledger.entries
        for reference in entry.source_references
    )
    unsafe = unsafe or any(
        dependency_path not in entry_paths
        for entry in ledger.entries
        for dependency_path in entry.dependency_paths
    )
    if unsafe:
        raise SkatAISerializationError(
            "Field provenance ledger contains details that are unsafe for public output."
        )
    return build_serializable_field_provenance_ledger(ledger)


build_public_safe_serializable_field_provenance_ledger = (
    build_public_serializable_field_provenance_ledger
)
