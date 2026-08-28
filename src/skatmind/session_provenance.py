from __future__ import annotations

from collections.abc import Mapping

from skatmind.api.v1.session.provenance import (
    SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE,
    SESSION_FIELD_PROVENANCE_REDACTION_POLICY,
    SessionFieldProvenanceAttachmentV1,
    SessionFieldProvenanceBundleV1,
    SessionProvenanceContextV1,
)
from skatmind.errors import SkatMindInvariantError
from skatmind.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
    build_public_serializable_field_provenance_ledger,
    parse_json_pointer,
    resolve_json_pointer,
)
from skatmind.field_provenance_coverage import (
    build_serializable_field_provenance_coverage_summary,
    enumerate_json_leaf_paths,
    validate_field_provenance_coverage,
)
from skatmind.field_provenance_policy import (
    redact_field_provenance_ledger_for_public_output,
)
from skatmind.session_commands import serialize_session_command_v1
from skatmind.session_contracts import SessionStateV1
from skatmind.session_decision_checkpoint import SessionDecisionCheckpointV1
from skatmind.session_history_contracts import (
    SessionCorrectionResultV1,
    SessionUndoResultV1,
)
from skatmind.session_persistence_contracts import (
    SessionPersistenceDocumentV1,
    SessionResumeResultV1,
)
from skatmind.session_validation import SessionTransitionResultV1

_OFFLINE_OPERATIONS = {
    "rewind",
    "correct",
    "classify_checkpoint",
    "build_persistence_document",
    "resume_persistence_document",
    "observe_checkpoint",
    "export_checkpoint_review",
}
_DERIVED_FIELD_NAMES = {
    "capture_mode",
    "current_revision",
    "failed_original_revision",
    "phase",
    "previous_revision",
    "relationship",
    "revision",
    "source_revision",
    "state_revision",
    "status",
    "target_revision",
}
_DERIVED_SUBTREES = {
    "checkpoint_lineage",
    "completed_tricks",
    "diagnostics",
    "historical_export",
    "incomplete_trick",
    "position_export",
    "validation",
}
_HISTORICAL_PRIVATE_NAMES = {
    "discarded_cards",
    "initial_hand",
    "initial_hands",
    "initial_known_hands",
    "known_skat",
    "player_hands",
    "remaining_known_hands",
    "skat",
}
_LOCAL_PRIVATE_NAMES = {
    "discarded_cards",
    "hand",
    "initial_hand",
    "initial_known_hands",
    "known_skat",
    "remaining_known_hands",
    "skat",
}


def _state_for_context(
    *,
    operation: str,
    value: object,
    source_state: SessionStateV1 | None,
) -> SessionStateV1:
    if operation == "create" and type(value) is SessionStateV1:
        return value
    if type(value) in {
        SessionTransitionResultV1,
        SessionUndoResultV1,
        SessionCorrectionResultV1,
    }:
        return value.state
    if type(value) is SessionPersistenceDocumentV1:
        return value.state
    if type(value) is SessionResumeResultV1:
        return value.document.state
    if source_state is not None and type(source_state) is SessionStateV1:
        return source_state
    raise SkatMindInvariantError(
        "Session Provenance cannot derive context from the operation value.",
        path="",
    )


def _nearest_command_kind(document: Mapping[str, object], field_path: str) -> str | None:
    tokens = parse_json_pointer(field_path)
    for length in range(len(tokens), -1, -1):
        ancestor_path = "" if length == 0 else "/" + "/".join(
            token.replace("~", "~0").replace("/", "~1")
            for token in tokens[:length]
        )
        try:
            ancestor = resolve_json_pointer(document, ancestor_path)
        except Exception:
            continue
        if isinstance(ancestor, Mapping):
            kind = ancestor.get("kind")
            if isinstance(kind, str):
                return kind
    return None


def _origin_for(
    *,
    operation: str,
    field_path: str,
    document: Mapping[str, object],
) -> tuple[str, str]:
    tokens = parse_json_pointer(field_path)
    names = set(tokens)
    leaf_name = tokens[-1] if tokens else ""
    command_kind = _nearest_command_kind(document, field_path)

    if operation == "create":
        root_name = tokens[0] if tokens else ""
        if root_name in {
            "session_id",
            "initial_capture_mode",
            "capture_mode",
            "players",
            "local_player_id",
        }:
            return "caller_supplied", "direct"
        if root_name == "session_contract_version":
            return "defaulted", "direct"
        return "rule_derived", "deterministic_rule"
    if operation == "rewind" and leaf_name in {
        "expected_revision",
        "target_revision",
    }:
        return "caller_supplied", "direct"
    if operation == "correct" and (
        "replacement_command" in names
        or leaf_name in {"expected_revision", "target_revision"}
    ):
        return "caller_supplied", "direct"
    if operation == "build_persistence_document" and "decision_checkpoints" in names:
        return "caller_supplied", "direct"
    if operation == "export_position" and (
        leaf_name
        in {
            "sample_count",
            "random_seed",
            "use_basic_opponent_strategy",
            "recommendation_method",
            "bounded_search_settings",
        }
        or "bounded_search_settings" in names
    ):
        return "caller_supplied", "direct"
    if (
        operation == "observe_checkpoint"
        and leaf_name in {"actual_card", "observed_play_revision"}
        and resolve_json_pointer(document, field_path) is not None
    ):
        return "retrospective_attachment", "retrospective"
    if (
        operation == "export_checkpoint_review"
        and leaf_name in {"actual_card", "actual_card_played", "observed_play_revision"}
        and resolve_json_pointer(document, field_path) is not None
    ):
        return "retrospective_attachment", "retrospective"
    if operation == "export_checkpoint_review" and leaf_name == "analysis_mode":
        return "rule_derived", "deterministic_rule"
    if "state_fingerprint" in names or "content_fingerprint" in names:
        return "structural_inference", "deterministic_rule"
    if "decision_index" in names or "trick_number" in names or "play_index" in names:
        return "structural_inference", "deterministic_rule"
    if leaf_name == "relationship":
        return "structural_inference", "deterministic_rule"
    if names.intersection(_DERIVED_SUBTREES) or leaf_name in _DERIVED_FIELD_NAMES:
        if operation in {"rewind", "correct", "resume_persistence_document"}:
            return "historical_replay", "reconstruction"
        return "rule_derived", "deterministic_rule"
    if command_kind in {"record_play", "set_public_hand"} and not (
        operation == "apply_command"
        and tokens[:1] == ("command",)
        and document.get("status") != "applied"
    ):
        return "public_game_event", "validated"
    if operation == "apply_command" and "command" in names:
        return "caller_supplied", "direct"
    if operation == "resume_persistence_document" and "document" in names:
        return "validated_copy", "validated"
    if operation == "export_historical" and names.intersection(
        _HISTORICAL_PRIVATE_NAMES
    ):
        return "retrospective_attachment", "retrospective"
    if operation == "export_historical" and "request" in names:
        return "historical_replay", "reconstruction"
    if operation in {"rewind", "correct"} and (
        "removed_records" in names
        or "replayed_suffix_records" in names
        or "discarded_suffix_records" in names
    ):
        return "historical_replay", "reconstruction"
    return "validated_copy", "validated"


def _visibility_for(
    *,
    operation: str,
    field_path: str,
    document: Mapping[str, object],
    state: SessionStateV1,
    retained_inputs: Mapping[str, object],
) -> tuple[str, str | None]:
    tokens = parse_json_pointer(field_path)
    names = set(tokens)
    command_kind = _nearest_command_kind(document, field_path)
    if "request" in names and "hand" in names:
        if operation == "build_checkpoint":
            acting_player_id = document.get("acting_player_id")
            if isinstance(acting_player_id, str):
                return "local_private", acting_player_id
        if operation == "export_checkpoint_review":
            checkpoint = retained_inputs.get("checkpoint")
            acting_player_id = getattr(checkpoint, "acting_player_id", None)
            if isinstance(acting_player_id, str):
                return "local_private", acting_player_id
        checkpoint_player_id = _checkpoint_player_id(document, tokens)
        if checkpoint_player_id is not None:
            return "local_private", checkpoint_player_id
    if command_kind == "set_public_hand":
        return "public", None
    sensitive = bool(names.intersection(_LOCAL_PRIVATE_NAMES))
    if command_kind in {"record_dealt_card", "record_discard"}:
        sensitive = True
    if operation == "export_historical" and names.intersection(
        _HISTORICAL_PRIVATE_NAMES
    ):
        sensitive = True
    if not sensitive:
        return "public", None
    if state.capture_mode == "retrospective" or operation == "export_historical":
        return "post_game_only", None
    if state.local_player_id is not None:
        return "local_private", state.local_player_id
    return "public", None


def _checkpoint_player_id(
    document: Mapping[str, object],
    tokens: tuple[str, ...],
) -> str | None:
    try:
        checkpoint_token_index = tokens.index("decision_checkpoints")
    except ValueError:
        return None
    if len(tokens) <= checkpoint_token_index + 1:
        return None
    prefix = tokens[: checkpoint_token_index + 2]
    pointer = "/" + "/".join(
        token.replace("~", "~0").replace("/", "~1") for token in prefix
    )
    try:
        checkpoint = resolve_json_pointer(document, pointer)
    except Exception:
        return None
    if not isinstance(checkpoint, Mapping):
        return None
    acting_player_id = checkpoint.get("acting_player_id")
    return acting_player_id if isinstance(acting_player_id, str) else None


def _decision_index(state: SessionStateV1, value: object) -> int:
    if type(value) is SessionDecisionCheckpointV1:
        return value.decision_index
    decision_index = getattr(value, "decision_index", None)
    if isinstance(decision_index, int):
        return decision_index
    observation = getattr(value, "observation", None)
    decision_index = getattr(observation, "decision_index", None)
    if isinstance(decision_index, int):
        return decision_index
    play_count = sum(
        serialize_session_command_v1(record.command)["kind"] == "record_play"
        for record in state.command_log
    )
    return play_count + 1


def _event_index(state: SessionStateV1) -> int:
    return sum(
        serialize_session_command_v1(record.command)["kind"]
        in {"set_game_event", "set_public_hand"}
        for record in state.command_log
    )


def _availability_for(
    *,
    operation: str,
    field_path: str,
    document: Mapping[str, object],
    state: SessionStateV1,
    value: object,
) -> tuple[str, int | None, int | None]:
    if operation == "create":
        return "request_start", None, None
    tokens = parse_json_pointer(field_path)
    leaf_name = tokens[-1] if tokens else ""
    names = set(tokens)
    if (
        operation == "observe_checkpoint"
        and leaf_name in {"actual_card", "observed_play_revision"}
        and resolve_json_pointer(document, field_path) is not None
    ):
        return "after_actual_play", _decision_index(state, value), None
    if operation == "export_checkpoint_review":
        if (
            leaf_name in {"actual_card", "actual_card_played", "observed_play_revision"}
            and resolve_json_pointer(document, field_path) is not None
        ):
            return "after_actual_play", _decision_index(state, value), None
        if "request" in names and leaf_name != "analysis_mode":
            checkpoint = value.observation.decision_index
            return "current_decision", checkpoint, None
        if field_path == "/session_id":
            return "current_decision", value.observation.decision_index, None
    if operation in _OFFLINE_OPERATIONS:
        return "offline_review", None, None
    if operation == "export_historical" or state.phase == "ended":
        return "game_end", None, None
    command_kind = _nearest_command_kind(document, field_path)
    if command_kind in {"set_game_event", "set_public_hand"} and not (
        operation == "apply_command" and document.get("status") != "applied"
    ):
        return "after_public_event", None, _event_index(state)
    return "current_decision", _decision_index(state, value), None


def _build_internal_ledger(
    *,
    operation: str,
    value: object,
    document: Mapping[str, object],
    state: SessionStateV1,
    retained_inputs: Mapping[str, object],
) -> FieldProvenanceLedger:
    entries = []
    for field_path in enumerate_json_leaf_paths(document):
        origin, derivation = _origin_for(
            operation=operation,
            field_path=field_path,
            document=document,
        )
        visibility, perspective_player_id = _visibility_for(
            operation=operation,
            field_path=field_path,
            document=document,
            state=state,
            retained_inputs=retained_inputs,
        )
        available_from, decision_index, event_index = _availability_for(
            operation=operation,
            field_path=field_path,
            document=document,
            state=state,
            value=value,
        )
        source_references = _source_references_for(
            operation=operation,
            origin=origin,
            field_path=field_path,
            visibility=visibility,
            state=state,
            retained_inputs=retained_inputs,
        )
        dependency_path = _dependency_path_for(
            operation=operation,
            origin=origin,
            field_path=field_path,
            document=document,
        )
        entries.append(
            FieldProvenanceEntry(
                field_path=field_path,
                coverage_kind="field",
                origin=origin,
                visibility=visibility,
                available_from=available_from,
                available_from_decision_index=decision_index,
                available_from_event_index=event_index,
                derivation=derivation,
                source_references=source_references,
                dependency_paths=(dependency_path,) if dependency_path else (),
                subject_player_id=None,
                perspective_player_id=perspective_player_id,
            )
        )
    return FieldProvenanceLedger(
        status="complete",
        entries=tuple(entries),
        exemptions=(),
        limitations=(),
    )


def _source_references_for(
    *,
    operation: str,
    origin: str,
    field_path: str,
    visibility: str,
    state: SessionStateV1,
    retained_inputs: Mapping[str, object],
) -> tuple[FieldProvenanceSourceReference, ...]:
    checkpoint = retained_inputs.get("checkpoint")
    if origin == "retrospective_attachment" and operation in {
        "observe_checkpoint",
        "export_checkpoint_review",
    }:
        checkpoint_revision = getattr(checkpoint, "source_revision", None)
        acting_player_id = getattr(checkpoint, "acting_player_id", None)
        if not isinstance(checkpoint_revision, int) or not isinstance(
            acting_player_id, str
        ):
            raise SkatMindInvariantError(
                "Observed-card Provenance requires the retained Decision Checkpoint.",
                path="retained_inputs.checkpoint",
            )
        observed_revision = next(
            (
                record.revision
                for record in state.command_log[checkpoint_revision:]
                if getattr(record.command, "kind", None) == "record_play"
                and getattr(record.command, "player_id", None) == acting_player_id
            ),
            state.revision,
        )
        source_field = (
            f"/command_log/{observed_revision - 1}/command/card"
            if field_path.endswith(("/actual_card", "/actual_card_played"))
            else f"/command_log/{observed_revision - 1}/revision"
        )
        return (
            FieldProvenanceSourceReference(
                reference_type="retrospective_observation",
                reference_id=(
                    f"session:{state.session_id}:accepted-play:{observed_revision}"
                ),
                field_path=source_field,
                visibility="public",
            ),
        )
    if (
        operation == "export_checkpoint_review"
        and field_path.startswith("/request/")
        and checkpoint is not None
        and origin not in {"rule_derived", "structural_inference"}
    ):
        return (
            FieldProvenanceSourceReference(
                reference_type="request",
                reference_id=(
                    f"session:{state.session_id}:checkpoint:"
                    f"{checkpoint.source_revision}"
                ),
                field_path=field_path,
                visibility=visibility,
            ),
        )
    if origin in {"rule_derived", "structural_inference"}:
        return (
            FieldProvenanceSourceReference(
                reference_type="algorithm",
                reference_id=f"session-{operation}-v1",
                field_path=None,
                visibility="engine_private",
            ),
        )
    if origin in {"historical_replay", "retrospective_attachment"}:
        reference_type = "historical_game"
        reference_id = f"session:{state.session_id}:historical"
    elif origin == "public_game_event":
        reference_type = "historical_event"
        command = retained_inputs.get("command")
        expected_revision = getattr(command, "expected_revision", state.revision)
        reference_id = f"session:{state.session_id}:event:{expected_revision}"
    else:
        reference_type = "request"
        reference_id = f"session:{state.session_id}:{operation}"
    return (
        FieldProvenanceSourceReference(
            reference_type=reference_type,
            reference_id=reference_id,
            field_path=field_path,
            visibility=visibility,
        ),
    )


def _dependency_path_for(
    *,
    operation: str,
    origin: str,
    field_path: str,
    document: Mapping[str, object],
) -> str | None:
    if origin not in {"rule_derived", "structural_inference", "historical_replay"}:
        return None
    dependency_paths = {
        "create": "/session_id",
        "apply_command": "/state/session_id",
        "rewind": "/state/session_id",
        "correct": "/state/session_id",
        "export_position": "/session_id",
        "export_historical": "/session_id",
        "build_checkpoint": "/session_id",
        "classify_checkpoint": "/session_id",
        "build_persistence_document": "/state/session_id",
        "resume_persistence_document": "/document/state/session_id",
        "observe_checkpoint": "/session_id",
        "export_checkpoint_review": "/session_id",
    }
    dependency_path = dependency_paths[operation]
    if dependency_path == field_path:
        return None
    try:
        resolve_json_pointer(document, dependency_path)
    except Exception:
        return None
    return dependency_path


def build_session_field_provenance_bundle_v1(
    *,
    operation: str,
    value: object,
    source_state: SessionStateV1 | None,
    retained_inputs: Mapping[str, object],
) -> SessionFieldProvenanceBundleV1:
    """Builds one complete redacted sidecar over an existing Session value."""
    document = value.to_dict()
    if not isinstance(document, Mapping):
        raise SkatMindInvariantError(
            "Session operation values must serialize to JSON objects.",
            path="",
        )
    state = _state_for_context(
        operation=operation,
        value=value,
        source_state=source_state,
    )
    internal_ledger = _build_internal_ledger(
        operation=operation,
        value=value,
        document=document,
        state=state,
        retained_inputs=retained_inputs,
    )
    redacted_ledger = redact_field_provenance_ledger_for_public_output(
        internal_ledger
    )
    coverage = validate_field_provenance_coverage(document, redacted_ledger)
    if not coverage.provenance_complete:
        raise SkatMindInvariantError(
            "Public Session field provenance must remain complete after redaction.",
            path="field_provenance",
        )
    context = SessionProvenanceContextV1(
        operation=operation,
        session_id=state.session_id,
        revision=state.revision,
        capture_mode=state.capture_mode,
        phase=state.phase,
    )
    attachment = SessionFieldProvenanceAttachmentV1(
        attachment_name="session_operation_result",
        document_role="result",
        document_scope=SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE,
        ledger=build_public_serializable_field_provenance_ledger(redacted_ledger),
        coverage_summary=build_serializable_field_provenance_coverage_summary(
            coverage
        ),
        session_context=context.to_dict(),
    )
    return SessionFieldProvenanceBundleV1(
        operation=operation,
        redaction_policy=SESSION_FIELD_PROVENANCE_REDACTION_POLICY,
        result=attachment,
    )
