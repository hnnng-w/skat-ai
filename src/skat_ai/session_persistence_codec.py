from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from skat_ai.api.v1.contracts import (
    PUBLIC_API_CONTRACT_VERSION,
    RequestDocumentV1,
    WorkflowV1,
)
from skat_ai.errors import SkatAIInvariantError, SkatAIValidationError
from skat_ai.game_declaration import GameDeclaration
from skat_ai.input_loader import build_position_from_document
from skat_ai.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionDiscardCommandV1,
    RecordSessionPlayCommandV1,
    SessionCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionGameMetadataCommandV1,
    SetSessionPublicHandCommandV1,
)
from skat_ai.session_contracts import (
    SessionCommandRecordV1,
    SessionPlayerV1,
    SessionStateV1,
)
from skat_ai.session_decision_checkpoint import (
    SessionDecisionCheckpointV1,
    _build_replayed_session_decision_checkpoint_v1,
    _options_from_request,
)
from skat_ai.session_history import _reconstruct_session_prefix_v1
from skat_ai.session_history_contracts import SessionCheckpointLineageV1
from skat_ai.session_persistence_contracts import (
    SESSION_PERSISTENCE_DOCUMENT_KIND,
    SESSION_PERSISTENCE_VERSION,
    SessionPersistenceDocumentV1,
    SessionResumeResultV1,
    _build_verified_session_persistence_document_v1,
    _canonical_json_bytes,
    _canonicalize_checkpoints,
)
from skat_ai.session_position_export import (
    _export_replayed_session_position_analysis_request_v1,
)
from skat_ai.session_projection import SessionProjectionV1
from skat_ai.session_transitions import replay_session_state_v1
from skat_ai.session_validation import (
    SessionExportReadinessV1,
    SessionValidationDiagnosticV1,
    SessionValidationResultV1,
)

_SESSION_STATE_FINGERPRINT_DOMAIN = b"skat-ai\0session_state_v1\0"
_SESSION_PERSISTENCE_FINGERPRINT_DOMAIN = b"skat-ai\0session_persistence_v1\0"

_DOCUMENT_FIELDS = {
    "session_persistence_version",
    "document_kind",
    "state_fingerprint",
    "content_fingerprint",
    "state",
    "decision_checkpoints",
}
_STATE_FIELDS = {
    "session_contract_version",
    "session_id",
    "initial_capture_mode",
    "capture_mode",
    "revision",
    "phase",
    "players",
    "local_player_id",
    "command_log",
    "validation",
}
_PLAYER_FIELDS = {"player_id", "player_label", "seat"}
_COMMAND_RECORD_FIELDS = {"revision", "command"}
_DIAGNOSTIC_FIELDS = {
    "code",
    "path",
    "message",
    "severity",
    "blocks_command",
    "blocks_position_export",
    "blocks_historical_export",
}
_READINESS_FIELDS = {"target", "status", "reason_codes"}
_VALIDATION_FIELDS = {
    "session_contract_version",
    "revision",
    "phase",
    "structurally_valid",
    "valid_incomplete",
    "game_complete",
    "position_export",
    "historical_export",
    "diagnostics",
}
_REQUEST_FIELDS = {"api_contract_version", "workflow", "document"}
_CHECKPOINT_FIELDS = {
    "session_decision_checkpoint_version",
    "session_id",
    "source_revision",
    "source_capture_mode",
    "decision_index",
    "trick_number",
    "play_index",
    "acting_player_id",
    "acting_seat",
    "information_cutoff",
    "relative_player_map",
    "request",
}

_COMMAND_FIELDS = {
    "set_game_metadata": {
        "command_version",
        "kind",
        "expected_revision",
        "game_id",
        "played_at",
    },
    "record_dealt_card": {
        "command_version",
        "kind",
        "expected_revision",
        "destination",
        "player_id",
        "card",
    },
    "set_declarer": {
        "command_version",
        "kind",
        "expected_revision",
        "declarer_player_id",
    },
    "set_declaration": {
        "command_version",
        "kind",
        "expected_revision",
        "declaration",
    },
    "record_discard": {
        "command_version",
        "kind",
        "expected_revision",
        "card",
    },
    "record_play": {
        "command_version",
        "kind",
        "expected_revision",
        "player_id",
        "card",
    },
    "set_game_event": {
        "command_version",
        "kind",
        "expected_revision",
        "event",
    },
    "set_game_end": {
        "command_version",
        "kind",
        "expected_revision",
        "game_end_reason",
        "game_end",
    },
    "promote_to_retrospective": {
        "command_version",
        "kind",
        "expected_revision",
    },
    "set_public_hand": {
        "command_version",
        "kind",
        "expected_revision",
        "source",
        "player_id",
        "cards",
    },
}

_DECLARATION_FIELDS = {
    "game_type",
    "hand_game",
    "ouvert",
    "schneider_announced",
    "schwarz_announced",
    "matadors",
    "bid_value",
}


def _sha256_domain_fingerprint(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json_bytes(value)).hexdigest()


def _build_replayed_state_fingerprint_v1(state: SessionStateV1) -> str:
    return _sha256_domain_fingerprint(
        _SESSION_STATE_FINGERPRINT_DOMAIN,
        state.to_dict(),
    )


def build_session_state_fingerprint_v1(state: SessionStateV1) -> str:
    """Builds the deterministic fingerprint of one replay-verified Session State."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    replay_session_state_v1(state)
    return _build_replayed_state_fingerprint_v1(state)


def _content_fingerprint_material(
    *,
    state_fingerprint: str,
    state: SessionStateV1,
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...],
) -> dict[str, Any]:
    return {
        "session_persistence_version": SESSION_PERSISTENCE_VERSION,
        "document_kind": SESSION_PERSISTENCE_DOCUMENT_KIND,
        "state_fingerprint": state_fingerprint,
        "state": state.to_dict(),
        "decision_checkpoints": [checkpoint.to_dict() for checkpoint in decision_checkpoints],
    }


def _build_session_persistence_content_fingerprint_v1(
    *,
    state_fingerprint: str,
    state: SessionStateV1,
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...],
) -> str:
    return _sha256_domain_fingerprint(
        _SESSION_PERSISTENCE_FINGERPRINT_DOMAIN,
        _content_fingerprint_material(
            state_fingerprint=state_fingerprint,
            state=state,
            decision_checkpoints=decision_checkpoints,
        ),
    )


def _validate_session_persistence_document_fingerprints_v1(
    document: SessionPersistenceDocumentV1,
) -> None:
    try:
        state_fingerprint = build_session_state_fingerprint_v1(document.state)
    except SkatAIInvariantError as error:
        raise ValueError("state must be canonical and replay-valid before persistence.") from error
    if document.state_fingerprint != state_fingerprint:
        raise ValueError("state_fingerprint must match the exact Session State.")
    content_fingerprint = _build_session_persistence_content_fingerprint_v1(
        state_fingerprint=state_fingerprint,
        state=document.state,
        decision_checkpoints=document.decision_checkpoints,
    )
    if document.content_fingerprint != content_fingerprint:
        raise ValueError("content_fingerprint must match the complete persistence document.")


def _raise_validation(message: str, *, path: str) -> None:
    raise SkatAIValidationError(message, path=path)


def _require_object(
    value: object,
    *,
    fields: set[str],
    path: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise_validation("Value must be a JSON object.", path=path)
    if any(not isinstance(key, str) for key in value):
        _raise_validation("JSON object keys must be strings.", path=path)
    actual_fields = set(value)
    missing = sorted(fields - actual_fields)
    if missing:
        _raise_validation(f"Missing required fields: {missing}.", path=path)
    unknown = sorted(actual_fields - fields)
    if unknown:
        _raise_validation(f"Unsupported fields: {unknown}.", path=path)
    return value


def _require_array(value: object, *, path: str) -> list[object]:
    if not isinstance(value, list):
        _raise_validation("Value must be a JSON array.", path=path)
    return value


def _construct(
    constructor: Callable[..., Any],
    *,
    path: str,
    **values: object,
) -> Any:
    try:
        return constructor(**values)
    except SkatAIValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error), path=path) from error


def _require_exact_round_trip(
    source: Mapping[str, object],
    rebuilt: object,
    *,
    path: str,
) -> None:
    if not hasattr(rebuilt, "to_dict") or rebuilt.to_dict() != dict(source):
        _raise_validation("Persisted value is not in canonical form.", path=path)


def _build_player(value: object, *, path: str) -> SessionPlayerV1:
    data = _require_object(value, fields=_PLAYER_FIELDS, path=path)
    player = _construct(
        SessionPlayerV1,
        path=path,
        player_id=data["player_id"],
        player_label=data["player_label"],
        seat=data["seat"],
    )
    _require_exact_round_trip(data, player, path=path)
    return player


def _validate_response_objects(value: object, *, path: str) -> None:
    for index, response in enumerate(_require_array(value, path=path)):
        _require_object(
            response,
            fields={"defender_player_id", "response", "form"},
            path=f"{path}/{index}",
        )


def _validate_event_shape(value: object, *, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise_validation("Value must be a JSON object.", path=path)
    kind = value.get("kind")
    if kind == "declarer_card_exposure_continuation":
        fields = {
            "schema_version",
            "kind",
            "after_play_count",
            "exposure",
            "claimed_play_level",
            "defender_responses",
            "public_declarer_cards",
        }
        data = _require_object(value, fields=fields, path=path)
        exposure = data["exposure"]
        if not isinstance(exposure, Mapping):
            _raise_validation("Value must be a JSON object.", path=f"{path}/exposure")
        exposure_fields = {"form"}
        if exposure.get("form") == "shown_to_defender":
            exposure_fields.add("shown_to_defender_player_id")
        _require_object(
            exposure,
            fields=exposure_fields,
            path=f"{path}/exposure",
        )
        _validate_response_objects(
            data["defender_responses"],
            path=f"{path}/defender_responses",
        )
        _require_array(data["public_declarer_cards"], path=f"{path}/public_declarer_cards")
        return data
    if kind == "defender_open_play_continuation":
        data = _require_object(
            value,
            fields={
                "schema_version",
                "kind",
                "after_play_count",
                "exposing_defender_player_id",
                "exposed_cards",
                "declarer_response",
            },
            path=path,
        )
        _require_array(data["exposed_cards"], path=f"{path}/exposed_cards")
        return data
    _raise_validation("Unsupported Session game-event kind.", path=f"{path}/kind")


def _validate_game_end_shape(
    value: object,
    *,
    game_end_reason: object,
    path: str,
) -> Mapping[str, object] | None:
    if not isinstance(game_end_reason, str):
        _raise_validation(
            "game_end_reason must be a string.",
            path=path.rsplit("/", 1)[0] + "/game_end_reason",
        )
    if game_end_reason == "normal_completion":
        if value is not None:
            _raise_validation("normal_completion requires null game_end.", path=path)
        return None
    if not isinstance(value, Mapping):
        _raise_validation("A terminal game_end must be a JSON object.", path=path)
    fields_by_reason = {
        "declarer_concession": {
            "schema_version",
            "kind",
            "declarer_hand_cards_remaining",
            "defender_consent",
        },
        "defender_concession": {
            "schema_version",
            "kind",
            "conceding_defender_player_id",
            "concession_form",
        },
        "declarer_card_exposure": {
            "schema_version",
            "kind",
            "exposure",
            "claimed_play_level",
            "defender_responses",
        },
        "defender_open_play": {
            "schema_version",
            "kind",
            "exposing_defender_player_id",
            "exposed_cards",
            "declarer_response",
        },
        "open_card_throw": {
            "schema_version",
            "kind",
            "throwing_player_id",
            "thrown_cards",
            "statement_classification",
        },
    }
    if game_end_reason not in fields_by_reason:
        _raise_validation("Unsupported Session game-end reason.", path=path)
    data = _require_object(value, fields=fields_by_reason[game_end_reason], path=path)
    if game_end_reason == "declarer_concession":
        _require_object(
            data["defender_consent"],
            fields={"status", "consenting_defender_player_ids"},
            path=f"{path}/defender_consent",
        )
        _require_array(
            data["defender_consent"]["consenting_defender_player_ids"],
            path=f"{path}/defender_consent/consenting_defender_player_ids",
        )
    elif game_end_reason == "declarer_card_exposure":
        exposure = data["exposure"]
        if not isinstance(exposure, Mapping):
            _raise_validation("Value must be a JSON object.", path=f"{path}/exposure")
        exposure_fields = {"form", "exposed_cards"}
        if exposure.get("form") == "shown_to_defender":
            exposure_fields.add("shown_to_defender_player_id")
        _require_object(
            exposure,
            fields=exposure_fields,
            path=f"{path}/exposure",
        )
        _require_array(exposure["exposed_cards"], path=f"{path}/exposure/exposed_cards")
        _validate_response_objects(
            data["defender_responses"],
            path=f"{path}/defender_responses",
        )
    elif game_end_reason == "defender_open_play":
        _require_array(data["exposed_cards"], path=f"{path}/exposed_cards")
    elif game_end_reason == "open_card_throw":
        _require_array(data["thrown_cards"], path=f"{path}/thrown_cards")
    return data


def _build_declaration(value: object, *, path: str) -> GameDeclaration:
    data = _require_object(value, fields=_DECLARATION_FIELDS, path=path)
    return _construct(
        GameDeclaration,
        path=path,
        game_type=data["game_type"],
        hand_game=data["hand_game"],
        ouvert=data["ouvert"],
        schneider_announced=data["schneider_announced"],
        schwarz_announced=data["schwarz_announced"],
        matadors=data["matadors"],
        bid_value=data["bid_value"],
    )


def _build_command(value: object, *, path: str) -> SessionCommandV1:
    if not isinstance(value, Mapping):
        _raise_validation("Value must be a JSON object.", path=path)
    kind = value.get("kind")
    if not isinstance(kind, str) or kind not in _COMMAND_FIELDS:
        _raise_validation("Unsupported Session Command kind.", path=f"{path}/kind")
    data = _require_object(value, fields=_COMMAND_FIELDS[kind], path=path)
    common = {
        "command_version": data["command_version"],
        "expected_revision": data["expected_revision"],
    }
    if kind == "set_game_metadata":
        command = _construct(
            SetSessionGameMetadataCommandV1,
            path=path,
            **common,
            game_id=data["game_id"],
            played_at=data["played_at"],
        )
    elif kind == "record_dealt_card":
        command = _construct(
            RecordSessionDealtCardCommandV1,
            path=path,
            **common,
            destination=data["destination"],
            player_id=data["player_id"],
            card=data["card"],
        )
    elif kind == "set_declarer":
        command = _construct(
            SetSessionDeclarerCommandV1,
            path=path,
            **common,
            declarer_player_id=data["declarer_player_id"],
        )
    elif kind == "set_declaration":
        command = _construct(
            SetSessionDeclarationCommandV1,
            path=path,
            **common,
            declaration=_build_declaration(
                data["declaration"],
                path=f"{path}/declaration",
            ),
        )
    elif kind == "record_discard":
        command = _construct(
            RecordSessionDiscardCommandV1,
            path=path,
            **common,
            card=data["card"],
        )
    elif kind == "record_play":
        command = _construct(
            RecordSessionPlayCommandV1,
            path=path,
            **common,
            player_id=data["player_id"],
            card=data["card"],
        )
    elif kind == "set_game_event":
        command = _construct(
            SetSessionGameEventCommandV1,
            path=path,
            **common,
            event=_validate_event_shape(data["event"], path=f"{path}/event"),
        )
    elif kind == "set_game_end":
        command = _construct(
            SetSessionGameEndCommandV1,
            path=path,
            **common,
            game_end_reason=data["game_end_reason"],
            game_end=_validate_game_end_shape(
                data["game_end"],
                game_end_reason=data["game_end_reason"],
                path=f"{path}/game_end",
            ),
        )
    elif kind == "promote_to_retrospective":
        command = _construct(
            PromoteSessionToRetrospectiveCommandV1,
            path=path,
            **common,
        )
    else:
        cards = _require_array(data["cards"], path=f"{path}/cards")
        command = _construct(
            SetSessionPublicHandCommandV1,
            path=path,
            **common,
            source=data["source"],
            player_id=data["player_id"],
            cards=cards,
        )
    _require_exact_round_trip(data, command, path=path)
    return command


def _build_command_record(value: object, *, path: str) -> SessionCommandRecordV1:
    data = _require_object(value, fields=_COMMAND_RECORD_FIELDS, path=path)
    record = _construct(
        SessionCommandRecordV1,
        path=path,
        revision=data["revision"],
        command=_build_command(data["command"], path=f"{path}/command"),
    )
    _require_exact_round_trip(data, record, path=path)
    return record


def _build_diagnostic(
    value: object,
    *,
    path: str,
) -> SessionValidationDiagnosticV1:
    data = _require_object(value, fields=_DIAGNOSTIC_FIELDS, path=path)
    try:
        diagnostic = SessionValidationDiagnosticV1(**dict(data))
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error), path=path) from error
    _require_exact_round_trip(data, diagnostic, path=path)
    return diagnostic


def _build_readiness(value: object, *, path: str) -> SessionExportReadinessV1:
    data = _require_object(value, fields=_READINESS_FIELDS, path=path)
    readiness = _construct(
        SessionExportReadinessV1,
        path=path,
        target=data["target"],
        status=data["status"],
        reason_codes=_require_array(data["reason_codes"], path=f"{path}/reason_codes"),
    )
    _require_exact_round_trip(data, readiness, path=path)
    return readiness


def _build_validation(value: object, *, path: str) -> SessionValidationResultV1:
    data = _require_object(value, fields=_VALIDATION_FIELDS, path=path)
    diagnostics = tuple(
        _build_diagnostic(item, path=f"{path}/diagnostics/{index}")
        for index, item in enumerate(
            _require_array(data["diagnostics"], path=f"{path}/diagnostics")
        )
    )
    validation = _construct(
        SessionValidationResultV1,
        path=path,
        session_contract_version=data["session_contract_version"],
        revision=data["revision"],
        phase=data["phase"],
        structurally_valid=data["structurally_valid"],
        valid_incomplete=data["valid_incomplete"],
        game_complete=data["game_complete"],
        position_export=_build_readiness(
            data["position_export"],
            path=f"{path}/position_export",
        ),
        historical_export=_build_readiness(
            data["historical_export"],
            path=f"{path}/historical_export",
        ),
        diagnostics=diagnostics,
    )
    _require_exact_round_trip(data, validation, path=path)
    return validation


def _build_state(value: object, *, path: str) -> SessionStateV1:
    data = _require_object(value, fields=_STATE_FIELDS, path=path)
    players = tuple(
        _build_player(item, path=f"{path}/players/{index}")
        for index, item in enumerate(_require_array(data["players"], path=f"{path}/players"))
    )
    command_log = tuple(
        _build_command_record(item, path=f"{path}/command_log/{index}")
        for index, item in enumerate(
            _require_array(data["command_log"], path=f"{path}/command_log")
        )
    )
    state = _construct(
        SessionStateV1,
        path=path,
        session_contract_version=data["session_contract_version"],
        session_id=data["session_id"],
        initial_capture_mode=data["initial_capture_mode"],
        capture_mode=data["capture_mode"],
        revision=data["revision"],
        phase=data["phase"],
        players=players,
        local_player_id=data["local_player_id"],
        command_log=command_log,
        validation=_build_validation(data["validation"], path=f"{path}/validation"),
    )
    _require_exact_round_trip(data, state, path=path)
    return state


def _build_request(value: object, *, path: str) -> RequestDocumentV1:
    data = _require_object(value, fields=_REQUEST_FIELDS, path=path)
    if (
        data["api_contract_version"] != PUBLIC_API_CONTRACT_VERSION
        or type(data["api_contract_version"]) is not int
    ):
        _raise_validation(
            f"api_contract_version must equal {PUBLIC_API_CONTRACT_VERSION}.",
            path=f"{path}/api_contract_version",
        )
    if data["workflow"] != WorkflowV1.POSITION_ANALYSIS.value:
        _raise_validation(
            "Persisted Decision Checkpoints must target Position Analysis.",
            path=f"{path}/workflow",
        )
    if not isinstance(data["document"], Mapping):
        _raise_validation("Value must be a JSON object.", path=f"{path}/document")
    root = dict(data["document"])
    try:
        validated_root = build_position_from_document(root)
        request = RequestDocumentV1(
            api_contract_version=data["api_contract_version"],
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document=validated_root,
        )
    except SkatAIValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error), path=f"{path}/document") from error
    _require_exact_round_trip(data, request, path=path)
    return request


def _build_checkpoint(
    value: object,
    *,
    path: str,
) -> SessionDecisionCheckpointV1:
    data = _require_object(value, fields=_CHECKPOINT_FIELDS, path=path)
    checkpoint = _construct(
        SessionDecisionCheckpointV1,
        path=path,
        session_decision_checkpoint_version=data["session_decision_checkpoint_version"],
        session_id=data["session_id"],
        source_revision=data["source_revision"],
        source_capture_mode=data["source_capture_mode"],
        decision_index=data["decision_index"],
        trick_number=data["trick_number"],
        play_index=data["play_index"],
        acting_player_id=data["acting_player_id"],
        acting_seat=data["acting_seat"],
        information_cutoff=data["information_cutoff"],
        relative_player_map=_require_object(
            data["relative_player_map"],
            fields={"me", "left", "right"},
            path=f"{path}/relative_player_map",
        ),
        request=_build_request(data["request"], path=f"{path}/request"),
    )
    _require_exact_round_trip(data, checkpoint, path=path)
    try:
        _options_from_request(checkpoint.request)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIValidationError(
            "Persisted Checkpoint Request has invalid Session export options.",
            path=f"{path}/request/document",
        ) from error
    return checkpoint


def _validate_internal_checkpoint(
    checkpoint: SessionDecisionCheckpointV1,
) -> SessionDecisionCheckpointV1:
    if type(checkpoint) is not SessionDecisionCheckpointV1:
        raise ValueError(
            "decision_checkpoints must contain only SessionDecisionCheckpointV1 values."
        )
    try:
        rebuilt = _build_checkpoint(checkpoint.to_dict(), path="/decision_checkpoints")
    except SkatAIValidationError as error:
        raise ValueError("Decision Checkpoint is not canonical or valid.") from error
    if rebuilt != checkpoint:
        raise ValueError("Decision Checkpoint is not canonical.")
    return rebuilt


def build_session_persistence_document_v1(
    state: SessionStateV1,
    *,
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...]
    | list[SessionDecisionCheckpointV1] = (),
) -> SessionPersistenceDocumentV1:
    """Builds one replay-verified private persistence document without file I/O."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    replay_session_state_v1(state)
    if isinstance(decision_checkpoints, (str, bytes)) or not isinstance(
        decision_checkpoints, (list, tuple)
    ):
        raise ValueError("decision_checkpoints must be an ordered array.")
    checkpoints = tuple(
        _validate_internal_checkpoint(checkpoint) for checkpoint in decision_checkpoints
    )
    if any(checkpoint.session_id != state.session_id for checkpoint in checkpoints):
        raise ValueError("Every Decision Checkpoint must match the Session State ID.")

    canonical_checkpoints = _canonicalize_checkpoints(
        checkpoints,
        session_id=state.session_id,
    )
    state_fingerprint = _build_replayed_state_fingerprint_v1(state)
    content_fingerprint = _build_session_persistence_content_fingerprint_v1(
        state_fingerprint=state_fingerprint,
        state=state,
        decision_checkpoints=canonical_checkpoints,
    )
    try:
        return _build_verified_session_persistence_document_v1(
            state_fingerprint=state_fingerprint,
            content_fingerprint=content_fingerprint,
            state=state,
            decision_checkpoints=canonical_checkpoints,
        )
    except (TypeError, ValueError) as error:
        raise SkatAIInvariantError(
            "Session persistence document assembly violated its contract.",
            path="",
        ) from error


def _classify_replayed_checkpoint(
    *,
    state: SessionStateV1,
    source_projection: SessionProjectionV1,
    checkpoint: SessionDecisionCheckpointV1,
    prefix_cache: dict[int, tuple[SessionStateV1, SessionProjectionV1]],
) -> SessionCheckpointLineageV1:
    common = {
        "session_id": state.session_id,
        "checkpoint_revision": checkpoint.source_revision,
        "state_revision": state.revision,
    }
    if checkpoint.source_revision > state.revision:
        return SessionCheckpointLineageV1(**common, relationship="future")
    if checkpoint.source_revision == state.revision:
        prefix_state = state
        prefix_projection = source_projection
    else:
        cached = prefix_cache.get(checkpoint.source_revision)
        if cached is None:
            cached = _reconstruct_session_prefix_v1(
                state,
                target_revision=checkpoint.source_revision,
            )
            prefix_cache[checkpoint.source_revision] = cached
        prefix_state, prefix_projection = cached

    options = _options_from_request(checkpoint.request)
    expected_export = _export_replayed_session_position_analysis_request_v1(
        state=prefix_state,
        projection=prefix_projection,
        options=options,
    )
    if expected_export.status == "unavailable":
        return SessionCheckpointLineageV1(**common, relationship="diverged")
    expected_checkpoint = _build_replayed_session_decision_checkpoint_v1(
        state=prefix_state,
        projection=prefix_projection,
        position_export=expected_export,
    )
    if expected_checkpoint != checkpoint:
        return SessionCheckpointLineageV1(**common, relationship="diverged")
    return SessionCheckpointLineageV1(
        **common,
        relationship=("current" if checkpoint.source_revision == state.revision else "ancestor"),
    )


def _resume_session_document_v1(
    document: Mapping[str, object],
) -> SessionResumeResultV1:
    data = _require_object(document, fields=_DOCUMENT_FIELDS, path="")
    if (
        type(data["session_persistence_version"]) is not int
        or data["session_persistence_version"] != SESSION_PERSISTENCE_VERSION
    ):
        _raise_validation(
            f"session_persistence_version must equal {SESSION_PERSISTENCE_VERSION}.",
            path="/session_persistence_version",
        )
    if data["document_kind"] != SESSION_PERSISTENCE_DOCUMENT_KIND:
        _raise_validation(
            f"document_kind must equal {SESSION_PERSISTENCE_DOCUMENT_KIND!r}.",
            path="/document_kind",
        )

    state = _build_state(data["state"], path="/state")
    checkpoints = tuple(
        _build_checkpoint(item, path=f"/decision_checkpoints/{index}")
        for index, item in enumerate(
            _require_array(
                data["decision_checkpoints"],
                path="/decision_checkpoints",
            )
        )
    )
    if any(checkpoint.session_id != state.session_id for checkpoint in checkpoints):
        _raise_validation(
            "Every Decision Checkpoint must match the Session State ID.",
            path="/decision_checkpoints",
        )

    try:
        source_projection = replay_session_state_v1(state)
    except SkatAIInvariantError as error:
        error_path = "/state"
        if error.path:
            error_path += error.path if error.path.startswith("/") else f"/{error.path}"
        raise SkatAIValidationError(
            "Persisted Session State conflicts with its accepted Command Log.",
            path=error_path,
        ) from error
    state_fingerprint = _build_replayed_state_fingerprint_v1(state)
    if data["state_fingerprint"] != state_fingerprint:
        _raise_validation(
            "state_fingerprint does not match the persisted Session State.",
            path="/state_fingerprint",
        )

    try:
        canonical_checkpoints = _canonicalize_checkpoints(
            checkpoints,
            session_id=state.session_id,
        )
    except (TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error), path="") from error
    content_fingerprint = _build_session_persistence_content_fingerprint_v1(
        state_fingerprint=state_fingerprint,
        state=state,
        decision_checkpoints=canonical_checkpoints,
    )
    if data["content_fingerprint"] != content_fingerprint:
        _raise_validation(
            "content_fingerprint does not match the persistence document.",
            path="/content_fingerprint",
        )
    try:
        typed_document = _build_verified_session_persistence_document_v1(
            session_persistence_version=data["session_persistence_version"],
            document_kind=data["document_kind"],
            state_fingerprint=data["state_fingerprint"],
            content_fingerprint=data["content_fingerprint"],
            state=state,
            decision_checkpoints=canonical_checkpoints,
        )
    except (TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error), path="") from error
    if typed_document.to_dict() != dict(data):
        _raise_validation(
            "Persistence document values are not in canonical form.",
            path="",
        )

    prefix_cache: dict[int, tuple[SessionStateV1, SessionProjectionV1]] = {
        state.revision: (state, source_projection)
    }
    try:
        lineage = tuple(
            _classify_replayed_checkpoint(
                state=state,
                source_projection=source_projection,
                checkpoint=checkpoint,
                prefix_cache=prefix_cache,
            )
            for checkpoint in typed_document.decision_checkpoints
        )
        return SessionResumeResultV1(
            document=typed_document,
            checkpoint_lineage=lineage,
        )
    except SkatAIValidationError:
        raise
    except (SkatAIInvariantError, AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIValidationError(
            "Persisted Decision Checkpoint lineage cannot be reconstructed.",
            path="/decision_checkpoints",
        ) from error


def resume_session_document_v1(
    document: Mapping[str, object] | SessionPersistenceDocumentV1,
) -> SessionResumeResultV1:
    """Strictly reconstructs one persistence document and derived Checkpoint Lineage."""
    if type(document) is SessionPersistenceDocumentV1:
        source: object = document.to_dict()
    else:
        source = document
    if not isinstance(source, Mapping):
        raise SkatAIValidationError(
            "Session persistence document root must be a JSON object.",
            path="",
        )
    return _resume_session_document_v1(source)
