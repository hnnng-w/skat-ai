from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
from skatmind.api.v1.session.schema_validation import (
    validate_session_correction_document,
    validate_session_create_document,
)
from skatmind.errors import SkatMindValidationError

_CREATE_INPUT_FIELDS = {
    "session_id",
    "capture_mode",
    "local_player_id",
    "players",
}
_PLAYER_FIELDS = {"player_id", "player_label", "seat"}
_CORRECTION_FIELDS = {
    "session_history_edit_version",
    "expected_revision",
    "target_revision",
    "replacement_command",
}


@dataclass(slots=True)
class _SessionContext:
    file_path: str
    document: session_api.SessionPersistenceDocumentV1

    @property
    def state(self) -> session_api.SessionStateV1:
        return self.document.state

    @property
    def decision_checkpoints(
        self,
    ) -> tuple[session_api.SessionDecisionCheckpointV1, ...]:
        return self.document.decision_checkpoints


SessionContext = _SessionContext


def require_exact_fields(
    document: Mapping[str, object],
    expected: set[str],
    *,
    name: str,
) -> None:
    actual = set(document)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise SkatMindValidationError(
            f"{name} is missing required fields: {missing}.",
            path="",
        )
    if unknown:
        raise SkatMindValidationError(
            f"{name} has unsupported fields: {unknown}.",
            path="",
        )


def parse_create_input(
    document: Mapping[str, object],
) -> tuple[str, tuple[session_api.SessionPlayerV1, ...], str, str | None]:
    validate_session_create_document(document)
    require_exact_fields(document, _CREATE_INPUT_FIELDS, name="Session creation input")
    raw_players = document["players"]
    if isinstance(raw_players, (str, bytes)) or not isinstance(raw_players, list):
        raise SkatMindValidationError("players must be an array.", path="/players")
    players: list[session_api.SessionPlayerV1] = []
    for index, raw_player in enumerate(raw_players):
        if not isinstance(raw_player, Mapping):
            raise SkatMindValidationError(
                "Each Session Player must be an object.",
                path=f"/players/{index}",
            )
        require_exact_fields(raw_player, _PLAYER_FIELDS, name="Session Player")
        players.append(
            session_api.SessionPlayerV1(
                player_id=raw_player["player_id"],
                player_label=raw_player["player_label"],
                seat=raw_player["seat"],
            )
        )
    return (
        document["session_id"],
        tuple(players),
        document["capture_mode"],
        document["local_player_id"],
    )


def parse_correction_input(
    document: Mapping[str, object],
) -> session_api.SessionCommandCorrectionV1:
    validate_session_correction_document(document)
    require_exact_fields(
        document,
        _CORRECTION_FIELDS,
        name="Session Command Correction",
    )
    replacement = document["replacement_command"]
    if not isinstance(replacement, Mapping):
        raise SkatMindValidationError(
            "replacement_command must be an object.",
            path="/replacement_command",
        )
    return session_api.SessionCommandCorrectionV1(
        session_history_edit_version=document["session_history_edit_version"],
        expected_revision=document["expected_revision"],
        target_revision=document["target_revision"],
        replacement_command=session_api.parse_session_command(replacement),
    )


def session_options(include_provenance: bool) -> session_api.SessionApiOptionsV1:
    return session_api.SessionApiOptionsV1(include_provenance=include_provenance)


def load_context(
    file_path: str,
) -> tuple[SessionContext, session_files.SessionFileApiResultV1]:
    loaded = session_files.load_session_file(file_path)
    return (
        SessionContext(file_path=file_path, document=loaded.value.document),
        loaded,
    )


def save_context(
    context: SessionContext,
    *,
    state: session_api.SessionStateV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> session_files.SessionPersistenceWriteResultV1:
    expected_fingerprint = context.document.content_fingerprint
    persistence = session_api.build_session_persistence_document(
        state,
        decision_checkpoints=decision_checkpoints,
    ).value
    saved = session_files.save_session_file(
        context.file_path,
        persistence,
        expected_content_fingerprint=expected_fingerprint,
    ).value
    if saved.status != "conflict":
        context.document = persistence
    return saved


def create_context(
    file_path: str,
    document: Mapping[str, object],
    *,
    include_provenance: bool,
) -> tuple[
    session_api.SessionApiResultV1,
    SessionContext | None,
    session_files.SessionPersistenceWriteResultV1,
]:
    session_id, players, capture_mode, local_player_id = parse_create_input(document)
    created = session_api.create_session(
        session_id=session_id,
        players=players,
        capture_mode=capture_mode,
        local_player_id=local_player_id,
        options=session_options(include_provenance),
    )
    persistence = session_api.build_session_persistence_document(created.value).value
    saved = session_files.save_session_file(
        file_path,
        persistence,
        expected_content_fingerprint=None,
    ).value
    context = None
    if saved.status != "conflict":
        context = SessionContext(file_path=file_path, document=persistence)
    return created, context, saved


_require_exact_fields = require_exact_fields
_parse_create_input = parse_create_input
_parse_correction_input = parse_correction_input
_session_options = session_options
_load_context = load_context
_save_context = save_context
_create_context = create_context
