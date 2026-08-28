from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.learning_corpus_catalog import (
    LEARNING_CORPUS_CATALOG_VERSION,
    LearningCorpusCatalogV1,
    LearningCorpusCurrentMatchSelectionV1,
    LearningCorpusMatchSnapshotCatalogEntryV1,
    _validate_learning_corpus_catalog_v1,
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
)
from skatmind.learning_corpus_identity import (
    LEARNING_CORPUS_OBJECT_KINDS,
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_match_snapshot import (
    LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION,
    LearningCorpusMatchSnapshotV1,
    build_learning_corpus_match_snapshot_v1,
)
from skatmind.learning_corpus_persistence_contracts import (
    LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
    LEARNING_CORPUS_PERSISTENCE_ENCODING,
    LEARNING_CORPUS_PERSISTENCE_VERSION,
    LEGACY_LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
    LearningCorpusCatalogPersistenceDocumentV1,
    _build_verified_learning_corpus_catalog_persistence_document_v1,
)
from skatmind.learning_corpus_references import (
    LEARNING_CORPUS_REFERENCE_VERSION,
    LearningCorpusCommentaryReferenceV1,
    LearningCorpusDecisionReferenceV1,
    LearningCorpusGameReferenceV1,
    LearningCorpusPlayerObservationV1,
    LearningCorpusResponseReferenceV1,
)
from skatmind.match_workspace_persistence_codec import resume_match_workspace_document_v1
from skatmind.match_workspace_persistence_contracts import (
    LEGACY_MATCH_WORKSPACE_DOCUMENT_KIND,
    MATCH_WORKSPACE_DOCUMENT_KIND,
    MATCH_WORKSPACE_PERSISTENCE_VERSION,
)

_CATALOG_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_catalog_v1\0"
_PERSISTENCE_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_persistence_v1\0"
_LEGACY_CATALOG_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_catalog_v1\0"
_LEGACY_PERSISTENCE_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_persistence_v1\0"
_MATCH_SNAPSHOT_OBJECT_KIND = LEARNING_CORPUS_OBJECT_KINDS[0]

_DOCUMENT_FIELDS = {
    "learning_corpus_persistence_version",
    "document_kind",
    "catalog_fingerprint",
    "content_fingerprint",
    "catalog",
}
_CATALOG_FIELDS = {
    "learning_corpus_catalog_version",
    "corpus_id",
    "revision",
    "match_snapshots",
    "current_matches",
}
_CATALOG_ENTRY_FIELDS = {
    "learning_corpus_catalog_version",
    "object_kind",
    "match_snapshot_id",
    "match_id",
    "workspace_revision",
    "source_workspace_fingerprint",
    "source_content_fingerprint",
    "played_at",
    "source_kind",
    "source_title",
    "game_platform",
    "perspective_player_id",
    "player_ids",
    "observed_game_count",
    "passed_deal_count",
    "empty_slot_count",
    "decision_count",
    "commentary_count",
    "response_link_count",
}
_CURRENT_SELECTION_FIELDS = {
    "learning_corpus_catalog_version",
    "match_id",
    "match_snapshot_id",
}
_MATCH_SNAPSHOT_FIELDS = {
    "learning_corpus_match_snapshot_version",
    "object_kind",
    "match_snapshot_id",
    "match_id",
    "workspace_revision",
    "source_workspace_fingerprint",
    "source_content_fingerprint",
    "workspace",
    "player_observations",
    "game_references",
    "decision_references",
    "commentary_references",
    "response_references",
}
_PLAYER_OBSERVATION_FIELDS = {
    "learning_corpus_reference_version",
    "player_observation_id",
    "match_snapshot_id",
    "player_id",
    "table_place",
    "player_label",
    "game_platform",
    "platform_player_id",
    "statistics_snapshot_id",
}
_GAME_REFERENCE_FIELDS = {
    "learning_corpus_reference_version",
    "game_reference_id",
    "game_content_fingerprint",
    "match_snapshot_id",
    "match_id",
    "match_position",
    "game_id",
    "decision_reference_ids",
    "commentary_reference_ids",
    "response_reference_ids",
}
_DECISION_REFERENCE_FIELDS = {
    "learning_corpus_reference_version",
    "decision_reference_id",
    "match_snapshot_id",
    "game_reference_id",
    "match_id",
    "game_id",
    "match_position",
    "decision_index",
    "acting_player_id",
}
_COMMENTARY_REFERENCE_FIELDS = {
    "learning_corpus_reference_version",
    "commentary_reference_id",
    "match_snapshot_id",
    "game_reference_id",
    "commentary_id",
    "subject_decision_reference_id",
}
_RESPONSE_REFERENCE_FIELDS = {
    "learning_corpus_reference_version",
    "response_reference_id",
    "match_snapshot_id",
    "game_reference_id",
    "link_id",
    "commentary_reference_id",
    "response_decision_reference_id",
}


def _raise_validation(message: str, *, path: str) -> None:
    raise SkatMindValidationError(message, path=path)


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


def _require_version(
    value: object,
    expected: int,
    *,
    field_name: str,
    path: str,
) -> None:
    if type(value) is not int or value != expected:
        _raise_validation(f"{field_name} must equal {expected}.", path=path)


def _require_non_negative_integer(value: object, *, field_name: str, path: str) -> int:
    if type(value) is not int or value < 0:
        _raise_validation(f"{field_name} must be a non-negative integer.", path=path)
    return value


def _require_identifier(value: object, *, field_name: str, path: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        _raise_validation(
            f"{field_name} must be a non-empty, non-padded string.",
            path=path,
        )
    return value


def _require_hash(value: object, *, field_name: str, path: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _raise_validation(
            f"{field_name} must be a lowercase SHA-256 hexadecimal value.",
            path=path,
        )
    return value


def _construct(
    constructor: Callable[..., Any],
    *,
    path: str,
    **values: object,
) -> Any:
    try:
        return constructor(**values)
    except SkatMindValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path=path) from error


def _require_exact_round_trip(
    source: Mapping[str, object],
    rebuilt: object,
    *,
    path: str,
) -> None:
    if not hasattr(rebuilt, "to_dict") or rebuilt.to_dict() != dict(source):
        _raise_validation("Persisted value is not in canonical form.", path=path)


def _sha256_domain_fingerprint(domain: bytes, value: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(value)
    ).hexdigest()


def _fingerprint_profile_for_document_kind(
    document_kind: object,
) -> tuple[bytes, bytes, str]:
    if document_kind == LEARNING_CORPUS_CATALOG_DOCUMENT_KIND:
        return (
            _CATALOG_FINGERPRINT_DOMAIN,
            _PERSISTENCE_FINGERPRINT_DOMAIN,
            LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
        )
    if document_kind == LEGACY_LEARNING_CORPUS_CATALOG_DOCUMENT_KIND:
        return (
            _LEGACY_CATALOG_FINGERPRINT_DOMAIN,
            _LEGACY_PERSISTENCE_FINGERPRINT_DOMAIN,
            LEGACY_LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
        )
    _raise_validation("document_kind is unsupported.", path="/document_kind")


def _build_validated_catalog_fingerprint_v1(
    catalog: LearningCorpusCatalogV1,
    *,
    fingerprint_domain: bytes = _CATALOG_FINGERPRINT_DOMAIN,
) -> str:
    return _sha256_domain_fingerprint(fingerprint_domain, catalog.to_dict())


def build_learning_corpus_catalog_fingerprint_v1(
    catalog: LearningCorpusCatalogV1,
) -> str:
    """Fingerprints one exact validated Catalog independent of file formatting."""
    if type(catalog) is not LearningCorpusCatalogV1:
        raise ValueError("catalog must be an exact LearningCorpusCatalogV1.")
    try:
        _validate_learning_corpus_catalog_v1(catalog)
        return _build_validated_catalog_fingerprint_v1(catalog)
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Internally supplied Learning Corpus Catalog is inconsistent.",
            path="",
        ) from error


def _persistence_content_fingerprint_material(
    *,
    catalog_fingerprint: str,
    catalog: LearningCorpusCatalogV1,
    document_kind: str = LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
) -> dict[str, Any]:
    return {
        "learning_corpus_persistence_version": LEARNING_CORPUS_PERSISTENCE_VERSION,
        "document_kind": document_kind,
        "catalog_fingerprint": catalog_fingerprint,
        "catalog": catalog.to_dict(),
    }


def _build_learning_corpus_persistence_content_fingerprint_v1(
    *,
    catalog_fingerprint: str,
    catalog: LearningCorpusCatalogV1,
    document_kind: str = LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
    fingerprint_domain: bytes = _PERSISTENCE_FINGERPRINT_DOMAIN,
) -> str:
    return _sha256_domain_fingerprint(
        fingerprint_domain,
        _persistence_content_fingerprint_material(
            catalog_fingerprint=catalog_fingerprint,
            catalog=catalog,
            document_kind=document_kind,
        ),
    )


def build_learning_corpus_persistence_content_fingerprint_v1(
    *,
    catalog_fingerprint: str,
    catalog: LearningCorpusCatalogV1,
) -> str:
    """Fingerprints the complete Catalog persistence content except itself."""
    _require_hash(
        catalog_fingerprint,
        field_name="catalog_fingerprint",
        path="/catalog_fingerprint",
    )
    if type(catalog) is not LearningCorpusCatalogV1:
        raise ValueError("catalog must be an exact LearningCorpusCatalogV1.")
    try:
        _validate_learning_corpus_catalog_v1(catalog)
        expected_catalog_fingerprint = _build_validated_catalog_fingerprint_v1(catalog)
        if catalog_fingerprint != expected_catalog_fingerprint:
            raise ValueError("catalog_fingerprint must match the exact Catalog.")
        return _build_learning_corpus_persistence_content_fingerprint_v1(
            catalog_fingerprint=catalog_fingerprint,
            catalog=catalog,
        )
    except SkatMindValidationError as error:
        raise ValueError(error.message) from error
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Learning Corpus persistence fingerprint material is inconsistent.",
            path="",
        ) from error


def _validate_learning_corpus_catalog_persistence_document_fingerprints_v1(
    document: LearningCorpusCatalogPersistenceDocumentV1,
) -> None:
    catalog_domain, persistence_domain, document_kind = (
        _fingerprint_profile_for_document_kind(document.document_kind)
    )
    catalog_fingerprint = _build_validated_catalog_fingerprint_v1(
        document.catalog,
        fingerprint_domain=catalog_domain,
    )
    if document.catalog_fingerprint != catalog_fingerprint:
        raise ValueError("catalog_fingerprint must match the exact Catalog.")
    content_fingerprint = _build_learning_corpus_persistence_content_fingerprint_v1(
        catalog_fingerprint=catalog_fingerprint,
        catalog=document.catalog,
        document_kind=document_kind,
        fingerprint_domain=persistence_domain,
    )
    if document.content_fingerprint != content_fingerprint:
        raise ValueError(
            "content_fingerprint must match the complete Catalog persistence document."
        )


def build_learning_corpus_catalog_persistence_document_v1(
    catalog: LearningCorpusCatalogV1,
) -> LearningCorpusCatalogPersistenceDocumentV1:
    """Builds one validated authoritative Catalog document without file I/O."""
    if type(catalog) is not LearningCorpusCatalogV1:
        raise ValueError("catalog must be an exact LearningCorpusCatalogV1.")
    try:
        _validate_learning_corpus_catalog_v1(catalog)
        catalog_fingerprint = _build_validated_catalog_fingerprint_v1(catalog)
        content_fingerprint = _build_learning_corpus_persistence_content_fingerprint_v1(
            catalog_fingerprint=catalog_fingerprint,
            catalog=catalog,
        )
        return _build_verified_learning_corpus_catalog_persistence_document_v1(
            catalog_fingerprint=catalog_fingerprint,
            content_fingerprint=content_fingerprint,
            catalog=catalog,
        )
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Learning Corpus Catalog persistence document assembly violated its contract.",
            path="",
        ) from error


def _build_catalog_entry(
    value: object,
    *,
    path: str,
) -> LearningCorpusMatchSnapshotCatalogEntryV1:
    data = _require_object(value, fields=_CATALOG_ENTRY_FIELDS, path=path)
    _require_version(
        data["learning_corpus_catalog_version"],
        LEARNING_CORPUS_CATALOG_VERSION,
        field_name="learning_corpus_catalog_version",
        path=f"{path}/learning_corpus_catalog_version",
    )
    if data["object_kind"] != _MATCH_SNAPSHOT_OBJECT_KIND:
        _raise_validation(
            "Catalog entry object_kind must be match_workspace_snapshot.",
            path=f"{path}/object_kind",
        )
    entry = _construct(
        LearningCorpusMatchSnapshotCatalogEntryV1._from_validated,
        path=path,
        match_snapshot_id=data["match_snapshot_id"],
        match_id=data["match_id"],
        workspace_revision=data["workspace_revision"],
        source_workspace_fingerprint=data["source_workspace_fingerprint"],
        source_content_fingerprint=data["source_content_fingerprint"],
        played_at=data["played_at"],
        source_kind=data["source_kind"],
        source_title=data["source_title"],
        game_platform=data["game_platform"],
        perspective_player_id=data["perspective_player_id"],
        player_ids=tuple(_require_array(data["player_ids"], path=f"{path}/player_ids")),
        observed_game_count=data["observed_game_count"],
        passed_deal_count=data["passed_deal_count"],
        empty_slot_count=data["empty_slot_count"],
        decision_count=data["decision_count"],
        commentary_count=data["commentary_count"],
        response_link_count=data["response_link_count"],
    )
    _require_exact_round_trip(data, entry, path=path)
    return entry


def _build_current_selection(
    value: object,
    *,
    path: str,
) -> LearningCorpusCurrentMatchSelectionV1:
    data = _require_object(value, fields=_CURRENT_SELECTION_FIELDS, path=path)
    _require_version(
        data["learning_corpus_catalog_version"],
        LEARNING_CORPUS_CATALOG_VERSION,
        field_name="learning_corpus_catalog_version",
        path=f"{path}/learning_corpus_catalog_version",
    )
    selection = _construct(
        build_learning_corpus_current_match_selection_v1,
        path=path,
        match_id=data["match_id"],
        match_snapshot_id=data["match_snapshot_id"],
    )
    _require_exact_round_trip(data, selection, path=path)
    return selection


def _build_catalog(value: object, *, path: str) -> LearningCorpusCatalogV1:
    data = _require_object(value, fields=_CATALOG_FIELDS, path=path)
    _require_version(
        data["learning_corpus_catalog_version"],
        LEARNING_CORPUS_CATALOG_VERSION,
        field_name="learning_corpus_catalog_version",
        path=f"{path}/learning_corpus_catalog_version",
    )
    entries = tuple(
        _build_catalog_entry(item, path=f"{path}/match_snapshots/{index}")
        for index, item in enumerate(
            _require_array(data["match_snapshots"], path=f"{path}/match_snapshots")
        )
    )
    selections = tuple(
        _build_current_selection(item, path=f"{path}/current_matches/{index}")
        for index, item in enumerate(
            _require_array(data["current_matches"], path=f"{path}/current_matches")
        )
    )
    catalog = _construct(
        build_learning_corpus_catalog_v1,
        path=path,
        corpus_id=data["corpus_id"],
        revision=data["revision"],
        match_snapshots=entries,
        current_matches=selections,
    )
    _require_exact_round_trip(data, catalog, path=path)
    return catalog


def resume_learning_corpus_catalog_document_v1(
    document: Mapping[str, object],
) -> LearningCorpusCatalogPersistenceDocumentV1:
    """Strictly reconstructs one authoritative Catalog persistence document."""
    if not isinstance(document, Mapping):
        raise SkatMindValidationError(
            "Learning Corpus Catalog persistence document root must be a JSON object.",
            path="",
        )
    data = _require_object(document, fields=_DOCUMENT_FIELDS, path="")
    _require_version(
        data["learning_corpus_persistence_version"],
        LEARNING_CORPUS_PERSISTENCE_VERSION,
        field_name="learning_corpus_persistence_version",
        path="/learning_corpus_persistence_version",
    )
    catalog_domain, persistence_domain, document_kind = (
        _fingerprint_profile_for_document_kind(data["document_kind"])
    )
    catalog = _build_catalog(data["catalog"], path="/catalog")
    catalog_fingerprint = _build_validated_catalog_fingerprint_v1(
        catalog,
        fingerprint_domain=catalog_domain,
    )
    if data["catalog_fingerprint"] != catalog_fingerprint:
        _raise_validation(
            "catalog_fingerprint does not match the persisted Catalog.",
            path="/catalog_fingerprint",
        )
    content_fingerprint = _build_learning_corpus_persistence_content_fingerprint_v1(
        catalog_fingerprint=catalog_fingerprint,
        catalog=catalog,
        document_kind=document_kind,
        fingerprint_domain=persistence_domain,
    )
    if data["content_fingerprint"] != content_fingerprint:
        _raise_validation(
            "content_fingerprint does not match the Catalog persistence document.",
            path="/content_fingerprint",
        )
    try:
        typed_document = (
            _build_verified_learning_corpus_catalog_persistence_document_v1(
                learning_corpus_persistence_version=data[
                    "learning_corpus_persistence_version"
                ],
                document_kind=data["document_kind"],
                catalog_fingerprint=data["catalog_fingerprint"],
                content_fingerprint=data["content_fingerprint"],
                catalog=catalog,
            )
        )
    except (TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path="") from error
    if typed_document.to_dict() != dict(data):
        _raise_validation(
            "Catalog persistence document values are not in canonical form.",
            path="",
        )
    return typed_document


def _build_player_observation(value: object, *, path: str) -> None:
    data = _require_object(value, fields=_PLAYER_OBSERVATION_FIELDS, path=path)
    _require_version(
        data["learning_corpus_reference_version"],
        LEARNING_CORPUS_REFERENCE_VERSION,
        field_name="learning_corpus_reference_version",
        path=f"{path}/learning_corpus_reference_version",
    )
    reference = _construct(
        LearningCorpusPlayerObservationV1._from_validated,
        path=path,
        player_observation_id=data["player_observation_id"],
        match_snapshot_id=data["match_snapshot_id"],
        player_id=data["player_id"],
        table_place=data["table_place"],
        player_label=data["player_label"],
        game_platform=data["game_platform"],
        platform_player_id=data["platform_player_id"],
        statistics_snapshot_id=data["statistics_snapshot_id"],
    )
    _require_exact_round_trip(data, reference, path=path)


def _build_game_reference(value: object, *, path: str) -> None:
    data = _require_object(value, fields=_GAME_REFERENCE_FIELDS, path=path)
    _require_version(
        data["learning_corpus_reference_version"],
        LEARNING_CORPUS_REFERENCE_VERSION,
        field_name="learning_corpus_reference_version",
        path=f"{path}/learning_corpus_reference_version",
    )
    reference = _construct(
        LearningCorpusGameReferenceV1._from_validated,
        path=path,
        game_reference_id=data["game_reference_id"],
        game_content_fingerprint=data["game_content_fingerprint"],
        match_snapshot_id=data["match_snapshot_id"],
        match_id=data["match_id"],
        match_position=data["match_position"],
        game_id=data["game_id"],
        decision_reference_ids=tuple(
            _require_array(
                data["decision_reference_ids"],
                path=f"{path}/decision_reference_ids",
            )
        ),
        commentary_reference_ids=tuple(
            _require_array(
                data["commentary_reference_ids"],
                path=f"{path}/commentary_reference_ids",
            )
        ),
        response_reference_ids=tuple(
            _require_array(
                data["response_reference_ids"],
                path=f"{path}/response_reference_ids",
            )
        ),
    )
    _require_exact_round_trip(data, reference, path=path)


def _build_decision_reference(value: object, *, path: str) -> None:
    data = _require_object(value, fields=_DECISION_REFERENCE_FIELDS, path=path)
    _require_version(
        data["learning_corpus_reference_version"],
        LEARNING_CORPUS_REFERENCE_VERSION,
        field_name="learning_corpus_reference_version",
        path=f"{path}/learning_corpus_reference_version",
    )
    reference = _construct(
        LearningCorpusDecisionReferenceV1._from_validated,
        path=path,
        decision_reference_id=data["decision_reference_id"],
        match_snapshot_id=data["match_snapshot_id"],
        game_reference_id=data["game_reference_id"],
        match_id=data["match_id"],
        game_id=data["game_id"],
        match_position=data["match_position"],
        decision_index=data["decision_index"],
        acting_player_id=data["acting_player_id"],
    )
    _require_exact_round_trip(data, reference, path=path)


def _build_commentary_reference(value: object, *, path: str) -> None:
    data = _require_object(value, fields=_COMMENTARY_REFERENCE_FIELDS, path=path)
    _require_version(
        data["learning_corpus_reference_version"],
        LEARNING_CORPUS_REFERENCE_VERSION,
        field_name="learning_corpus_reference_version",
        path=f"{path}/learning_corpus_reference_version",
    )
    reference = _construct(
        LearningCorpusCommentaryReferenceV1._from_validated,
        path=path,
        commentary_reference_id=data["commentary_reference_id"],
        match_snapshot_id=data["match_snapshot_id"],
        game_reference_id=data["game_reference_id"],
        commentary_id=data["commentary_id"],
        subject_decision_reference_id=data["subject_decision_reference_id"],
    )
    _require_exact_round_trip(data, reference, path=path)


def _build_response_reference(value: object, *, path: str) -> None:
    data = _require_object(value, fields=_RESPONSE_REFERENCE_FIELDS, path=path)
    _require_version(
        data["learning_corpus_reference_version"],
        LEARNING_CORPUS_REFERENCE_VERSION,
        field_name="learning_corpus_reference_version",
        path=f"{path}/learning_corpus_reference_version",
    )
    reference = _construct(
        LearningCorpusResponseReferenceV1._from_validated,
        path=path,
        response_reference_id=data["response_reference_id"],
        match_snapshot_id=data["match_snapshot_id"],
        game_reference_id=data["game_reference_id"],
        link_id=data["link_id"],
        commentary_reference_id=data["commentary_reference_id"],
        response_decision_reference_id=data["response_decision_reference_id"],
    )
    _require_exact_round_trip(data, reference, path=path)


def _validate_reference_array(
    value: object,
    *,
    path: str,
    builder: Callable[..., None],
) -> None:
    for index, item in enumerate(_require_array(value, path=path)):
        builder(item, path=f"{path}/{index}")


def resume_learning_corpus_match_snapshot_object_v1(
    document: Mapping[str, object],
) -> LearningCorpusMatchSnapshotV1:
    """Strictly rebuilds one Match Snapshot object from its Workspace source."""
    if not isinstance(document, Mapping):
        raise SkatMindValidationError(
            "Learning Corpus Match Snapshot object root must be a JSON object.",
            path="",
        )
    data = _require_object(document, fields=_MATCH_SNAPSHOT_FIELDS, path="")
    _require_version(
        data["learning_corpus_match_snapshot_version"],
        LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION,
        field_name="learning_corpus_match_snapshot_version",
        path="/learning_corpus_match_snapshot_version",
    )
    if data["object_kind"] != _MATCH_SNAPSHOT_OBJECT_KIND:
        _raise_validation(
            "object_kind must equal match_workspace_snapshot.",
            path="/object_kind",
        )
    _require_hash(
        data["match_snapshot_id"],
        field_name="match_snapshot_id",
        path="/match_snapshot_id",
    )
    _require_identifier(data["match_id"], field_name="match_id", path="/match_id")
    _require_non_negative_integer(
        data["workspace_revision"],
        field_name="workspace_revision",
        path="/workspace_revision",
    )
    _require_hash(
        data["source_workspace_fingerprint"],
        field_name="source_workspace_fingerprint",
        path="/source_workspace_fingerprint",
    )
    _require_hash(
        data["source_content_fingerprint"],
        field_name="source_content_fingerprint",
        path="/source_content_fingerprint",
    )
    _validate_reference_array(
        data["player_observations"],
        path="/player_observations",
        builder=_build_player_observation,
    )
    _validate_reference_array(
        data["game_references"],
        path="/game_references",
        builder=_build_game_reference,
    )
    _validate_reference_array(
        data["decision_references"],
        path="/decision_references",
        builder=_build_decision_reference,
    )
    _validate_reference_array(
        data["commentary_references"],
        path="/commentary_references",
        builder=_build_commentary_reference,
    )
    _validate_reference_array(
        data["response_references"],
        path="/response_references",
        builder=_build_response_reference,
    )

    matches: list[LearningCorpusMatchSnapshotV1] = []
    for document_kind in (
        MATCH_WORKSPACE_DOCUMENT_KIND,
        LEGACY_MATCH_WORKSPACE_DOCUMENT_KIND,
    ):
        workspace_document = {
            "match_workspace_persistence_version": MATCH_WORKSPACE_PERSISTENCE_VERSION,
            "document_kind": document_kind,
            "workspace_fingerprint": data["source_workspace_fingerprint"],
            "content_fingerprint": data["source_content_fingerprint"],
            "workspace": data["workspace"],
        }
        try:
            resumed_workspace = resume_match_workspace_document_v1(workspace_document)
            rebuilt = build_learning_corpus_match_snapshot_v1(resumed_workspace.document)
        except SkatMindValidationError:
            continue
        if rebuilt.to_dict() == dict(data):
            matches.append(rebuilt)
    if len(matches) != 1:
        _raise_validation(
            "Persisted Match Snapshot does not equal one supported exact Workspace derivation.",
            path="",
        )
    return matches[0]


def _build_pretty_json_file_bytes(value: object, *, description: str) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
        )
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            f"{description} cannot be serialized as finite JSON.",
            path="",
        ) from error
    return f"{text}\n".encode(LEARNING_CORPUS_PERSISTENCE_ENCODING)


def _build_learning_corpus_catalog_file_bytes_v1(
    document: LearningCorpusCatalogPersistenceDocumentV1,
) -> bytes:
    return _build_pretty_json_file_bytes(
        document.to_dict(),
        description="Learning Corpus Catalog persistence document",
    )


def _build_learning_corpus_match_snapshot_object_file_bytes_v1(
    snapshot: LearningCorpusMatchSnapshotV1,
) -> bytes:
    if type(snapshot) is not LearningCorpusMatchSnapshotV1:
        raise ValueError("snapshot must be an exact LearningCorpusMatchSnapshotV1.")
    return _build_pretty_json_file_bytes(
        snapshot.to_dict(),
        description="Learning Corpus Match Snapshot object",
    )
