from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import patch

import pytest

import skatmind.api.v1.session.files as session_files
import skatmind.api.v1.session.files.execution as file_execution
from skatmind.errors import (
    SkatMindSerializationError,
    SkatMindValidationError,
)
from skatmind.session_commands import SetSessionGameMetadataCommandV1
from skatmind.session_contracts import SessionPlayerV1
from skatmind.session_persistence_codec import build_session_persistence_document_v1
from skatmind.session_persistence_contracts import (
    SessionPersistenceDocumentV1,
    SessionResumeResultV1,
)
from skatmind.session_persistence_contracts import (
    SessionPersistenceWriteResultV1 as InternalWriteResult,
)
from skatmind.session_transitions import apply_session_command_v1, create_session_state_v1

FILE_EXPORTS = (
    "PUBLIC_SESSION_FILE_API_VERSION",
    "PUBLIC_SESSION_FILE_API_NAMESPACE",
    "PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY",
    "SESSION_FILE_API_OPERATIONS",
    "SessionFileApiVersionInfoV1",
    "SessionFileApiOptionsV1",
    "SessionFileApiResultV1",
    "SessionPersistenceWriteResultV1",
    "get_session_file_api_version_info_v1",
    "save_session_file",
    "load_session_file",
    "serialize_session_file_result",
)

NO_VALIDATION = session_files.SessionFileApiOptionsV1(validate_output=False)


def _document(session_id: str) -> SessionPersistenceDocumentV1:
    players = (
        SessionPlayerV1(
            player_id=f"{session_id}-a",
            player_label=None,
            seat="forehand",
        ),
        SessionPlayerV1(
            player_id=f"{session_id}-b",
            player_label=None,
            seat="middlehand",
        ),
        SessionPlayerV1(
            player_id=f"{session_id}-c",
            player_label=None,
            seat="rearhand",
        ),
    )
    state = create_session_state_v1(
        session_id=session_id,
        players=players,
        capture_mode="retrospective",
    )
    return build_session_persistence_document_v1(state)


def test_public_session_file_namespace_and_exports_are_exact() -> None:
    assert session_files.__all__ == FILE_EXPORTS
    assert session_files.PUBLIC_SESSION_FILE_API_VERSION == 1
    assert session_files.PUBLIC_SESSION_FILE_API_NAMESPACE == "skatmind.api.v1.session.files"
    assert session_files.PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY == "additive_until_v1_0"
    assert session_files.SESSION_FILE_API_OPERATIONS == ("save", "load")
    assert session_files.SessionPersistenceWriteResultV1 is InternalWriteResult
    assert not hasattr(session_files, "save_session_persistence_file_v1")
    assert not hasattr(session_files, "load_session_persistence_file_v1")


def test_version_info_is_exact_deterministic_immutable_and_keyword_only() -> None:
    first = session_files.get_session_file_api_version_info_v1()
    second = session_files.get_session_file_api_version_info_v1()

    assert first == second
    assert [field.name for field in fields(type(first))] == [
        "api_contract_version",
        "public_session_api_version",
        "public_session_file_api_version",
        "namespace",
        "compatibility_policy",
        "operations",
        "persistence_version",
    ]
    assert first.to_dict() == {
        "api_contract_version": 1,
        "public_session_api_version": 1,
        "public_session_file_api_version": 1,
        "namespace": "skatmind.api.v1.session.files",
        "compatibility_policy": "additive_until_v1_0",
        "operations": ["save", "load"],
        "persistence_version": 1,
    }
    assert not hasattr(first, "__dict__")
    assert not hasattr(first, "package_version")
    assert not hasattr(first, "schema_version")
    with pytest.raises(FrozenInstanceError):
        first.namespace = "changed"
    with pytest.raises(TypeError):
        session_files.SessionFileApiVersionInfoV1(1)


def test_options_and_result_are_strict_slotted_and_immutable() -> None:
    options = session_files.SessionFileApiOptionsV1()
    assert options.to_dict() == {"validate_output": True}
    assert not hasattr(options, "__dict__")
    with pytest.raises(FrozenInstanceError):
        options.validate_output = False
    with pytest.raises(TypeError):
        session_files.SessionFileApiOptionsV1(False)
    with pytest.raises(SkatMindValidationError, match="validate_output"):
        session_files.SessionFileApiOptionsV1(validate_output=1)

    write_result = InternalWriteResult(
        status="saved",
        session_id="session-1",
        revision=0,
        expected_content_fingerprint=None,
        existing_content_fingerprint=None,
        requested_content_fingerprint="a" * 64,
    )
    result = session_files.SessionFileApiResultV1(
        operation="save",
        value=write_result,
    )
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.operation = "load"
    with pytest.raises(SkatMindValidationError, match="value"):
        session_files.SessionFileApiResultV1(
            operation="load",
            value=write_result,
        )


def test_save_load_and_serialization_preserve_values_without_paths(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "private-session.json"
    first_document = _document("session-1")
    second_document = _document("session-2")

    saved = session_files.save_session_file(
        file_path,
        first_document,
        expected_content_fingerprint=None,
        options=NO_VALIDATION,
    )
    assert saved.operation == "save"
    assert type(saved.value) is InternalWriteResult
    assert saved.value.status == "saved"

    unchanged = session_files.save_session_file(
        file_path,
        first_document,
        expected_content_fingerprint=first_document.content_fingerprint,
        options=NO_VALIDATION,
    )
    assert unchanged.value.status == "unchanged"

    replaced = session_files.save_session_file(
        file_path,
        second_document,
        expected_content_fingerprint=first_document.content_fingerprint,
        options=NO_VALIDATION,
    )
    assert replaced.value.status == "saved"

    conflict = session_files.save_session_file(
        file_path,
        first_document,
        expected_content_fingerprint=first_document.content_fingerprint,
        options=NO_VALIDATION,
    )
    assert conflict.value.status == "conflict"

    loaded = session_files.load_session_file(file_path, options=NO_VALIDATION)
    assert loaded.operation == "load"
    assert type(loaded.value) is SessionResumeResultV1
    assert loaded.value.document == second_document

    serialized = session_files.serialize_session_file_result(loaded)
    assert serialized == loaded.to_dict()
    assert "path" not in serialized
    assert "file_path" not in serialized
    serialized["value"]["document"]["state"]["session_id"] = "changed"
    assert loaded.value.document.state.session_id == "session-2"
    with pytest.raises(SkatMindSerializationError):
        session_files.serialize_session_file_result(loaded.to_dict())


def test_each_file_operation_delegates_exactly_once(tmp_path: Path) -> None:
    file_path = tmp_path / "session.json"
    document = _document("delegation")

    with patch.object(
        file_execution,
        "save_session_persistence_file_v1",
        wraps=file_execution.save_session_persistence_file_v1,
    ) as save_spy:
        session_files.save_session_file(
            file_path,
            document,
            expected_content_fingerprint=None,
            options=NO_VALIDATION,
        )
    assert save_spy.call_count == 1

    with patch.object(
        file_execution,
        "load_session_persistence_file_v1",
        wraps=file_execution.load_session_persistence_file_v1,
    ) as load_spy:
        session_files.load_session_file(file_path, options=NO_VALIDATION)
    assert load_spy.call_count == 1


def test_filesystem_and_stable_validation_errors_are_preserved(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError) as missing:
        session_files.load_session_file(
            tmp_path / "missing.json",
            options=NO_VALIDATION,
        )
    assert missing.value.filename == str(tmp_path / "missing.json")

    filesystem_error = OSError("filesystem failure")
    with (
        patch.object(
            file_execution,
            "save_session_persistence_file_v1",
            side_effect=filesystem_error,
        ),
        pytest.raises(OSError) as raised_filesystem,
    ):
        session_files.save_session_file(
            tmp_path / "session.json",
            _document("filesystem-error"),
            expected_content_fingerprint=None,
            options=NO_VALIDATION,
        )
    assert raised_filesystem.value is filesystem_error

    validation_error = SkatMindValidationError("invalid persistence", path="/state")
    with (
        patch.object(
            file_execution,
            "load_session_persistence_file_v1",
            side_effect=validation_error,
        ),
        pytest.raises(SkatMindValidationError) as raised_validation,
    ):
        session_files.load_session_file(
            tmp_path / "session.json",
            options=NO_VALIDATION,
        )
    assert raised_validation.value is validation_error


@pytest.mark.parametrize("error", [ValueError("invalid value"), TypeError("invalid type")])
def test_plain_python_validation_errors_are_translated(
    tmp_path: Path,
    error: Exception,
) -> None:
    with (
        patch.object(
            file_execution,
            "load_session_persistence_file_v1",
            side_effect=error,
        ),
        pytest.raises(SkatMindValidationError) as raised,
    ):
        session_files.load_session_file(
            tmp_path / "session.json",
            options=NO_VALIDATION,
        )
    assert raised.value.__cause__ is error


def test_public_file_api_preserves_invalid_target_and_regular_file_checks(
    tmp_path: Path,
) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_bytes = b'{"not": "a session"}\n'
    invalid_path.write_bytes(invalid_bytes)
    with pytest.raises(SkatMindValidationError):
        session_files.save_session_file(
            invalid_path,
            _document("invalid-target"),
            expected_content_fingerprint=None,
            options=NO_VALIDATION,
        )
    assert invalid_path.read_bytes() == invalid_bytes

    directory_path = tmp_path / "directory"
    directory_path.mkdir()
    with pytest.raises(OSError):
        session_files.load_session_file(directory_path, options=NO_VALIDATION)


def test_public_save_reports_same_revision_corrected_history_conflict(
    tmp_path: Path,
) -> None:
    initial = _document("same-revision").state

    def changed_document(game_id: str) -> SessionPersistenceDocumentV1:
        transition = apply_session_command_v1(
            initial,
            SetSessionGameMetadataCommandV1(
                expected_revision=0,
                game_id=game_id,
                played_at=None,
            ),
        )
        assert transition.status == "applied"
        return build_session_persistence_document_v1(transition.state)

    first = changed_document("game-first")
    corrected = changed_document("game-corrected")
    assert first.state.revision == corrected.state.revision == 1
    assert first.content_fingerprint != corrected.content_fingerprint

    file_path = tmp_path / "same-revision.json"
    assert session_files.save_session_file(
        file_path,
        first,
        expected_content_fingerprint=None,
        options=NO_VALIDATION,
    ).value.status == "saved"
    before = file_path.read_bytes()
    conflict = session_files.save_session_file(
        file_path,
        corrected,
        expected_content_fingerprint=corrected.content_fingerprint,
        options=NO_VALIDATION,
    )
    assert conflict.value.status == "conflict"
    assert conflict.value.revision == 1
    assert conflict.value.existing_content_fingerprint == first.content_fingerprint
    assert file_path.read_bytes() == before
