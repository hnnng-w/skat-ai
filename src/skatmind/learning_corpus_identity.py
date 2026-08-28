from __future__ import annotations

import hashlib
import json

LEARNING_CORPUS_IDENTITY_VERSION = 1

LEARNING_CORPUS_OBJECT_KINDS = (
    "match_workspace_snapshot",
)

LEARNING_CORPUS_SOURCE_OF_TRUTH_POLICY = "immutable_imported_workspace_snapshot"
LEARNING_CORPUS_IDENTITY_POLICY = "logical_identity_plus_content_addressed_revision"
LEARNING_CORPUS_OBJECT_KIND_POLICY = "append_only_object_kinds"
LEARNING_CORPUS_DUPLICATE_POLICY = "equal_content_deduplicates_by_snapshot_id"
LEARNING_CORPUS_REVISION_POLICY = "same_match_distinct_content_retains_distinct_snapshot"
LEARNING_CORPUS_SAME_REVISION_POLICY = (
    "same_revision_distinct_content_requires_explicit_resolution"
)
LEARNING_CORPUS_CURRENT_SELECTION_POLICY = (
    "explicit_current_snapshot_per_logical_match"
)
LEARNING_CORPUS_PLAYER_IDENTITY_POLICY = "exact_stable_player_ids_without_fuzzy_merge"
LEARNING_CORPUS_REFERENCE_POLICY = "snapshot_closed_derived_references"
LEARNING_CORPUS_PRIVACY_POLICY = "private_local_unredacted_learning_data"

_MATCH_SNAPSHOT_ID_DOMAIN = b"skatmind\0learning_corpus_match_snapshot_v1\0"
_PLAYER_OBSERVATION_ID_DOMAIN = b"skatmind\0learning_corpus_player_observation_v1\0"
_GAME_CONTENT_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_game_content_v1\0"
_GAME_REFERENCE_ID_DOMAIN = b"skatmind\0learning_corpus_game_reference_v1\0"
_DECISION_REFERENCE_ID_DOMAIN = b"skatmind\0learning_corpus_decision_reference_v1\0"
_COMMENTARY_REFERENCE_ID_DOMAIN = b"skatmind\0learning_corpus_commentary_reference_v1\0"
_RESPONSE_REFERENCE_ID_DOMAIN = b"skatmind\0learning_corpus_response_reference_v1\0"

_LEGACY_MATCH_SNAPSHOT_ID_DOMAIN = b"skat-ai\0learning_corpus_match_snapshot_v1\0"
_LEGACY_PLAYER_OBSERVATION_ID_DOMAIN = b"skat-ai\0learning_corpus_player_observation_v1\0"
_LEGACY_GAME_CONTENT_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_game_content_v1\0"
_LEGACY_GAME_REFERENCE_ID_DOMAIN = b"skat-ai\0learning_corpus_game_reference_v1\0"
_LEGACY_DECISION_REFERENCE_ID_DOMAIN = b"skat-ai\0learning_corpus_decision_reference_v1\0"
_LEGACY_COMMENTARY_REFERENCE_ID_DOMAIN = b"skat-ai\0learning_corpus_commentary_reference_v1\0"
_LEGACY_RESPONSE_REFERENCE_ID_DOMAIN = b"skat-ai\0learning_corpus_response_reference_v1\0"


def build_learning_corpus_canonical_json_bytes_v1(value: object) -> bytes:
    """Serializes finite identity material as compact canonical UTF-8 JSON."""
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _build_learning_corpus_identifier_v1(domain: bytes, value: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(value)
    ).hexdigest()


def _build_match_snapshot_id_v1(value: object, *, legacy_identity: bool = False) -> str:
    domain = _LEGACY_MATCH_SNAPSHOT_ID_DOMAIN if legacy_identity else _MATCH_SNAPSHOT_ID_DOMAIN
    return _build_learning_corpus_identifier_v1(domain, value)


def _build_player_observation_id_v1(value: object, *, legacy_identity: bool = False) -> str:
    domain = (
        _LEGACY_PLAYER_OBSERVATION_ID_DOMAIN
        if legacy_identity
        else _PLAYER_OBSERVATION_ID_DOMAIN
    )
    return _build_learning_corpus_identifier_v1(domain, value)


def _build_game_content_fingerprint_v1(value: object, *, legacy_identity: bool = False) -> str:
    domain = (
        _LEGACY_GAME_CONTENT_FINGERPRINT_DOMAIN
        if legacy_identity
        else _GAME_CONTENT_FINGERPRINT_DOMAIN
    )
    return _build_learning_corpus_identifier_v1(domain, value)


def _build_game_reference_id_v1(value: object, *, legacy_identity: bool = False) -> str:
    domain = _LEGACY_GAME_REFERENCE_ID_DOMAIN if legacy_identity else _GAME_REFERENCE_ID_DOMAIN
    return _build_learning_corpus_identifier_v1(domain, value)


def _build_decision_reference_id_v1(value: object, *, legacy_identity: bool = False) -> str:
    domain = (
        _LEGACY_DECISION_REFERENCE_ID_DOMAIN
        if legacy_identity
        else _DECISION_REFERENCE_ID_DOMAIN
    )
    return _build_learning_corpus_identifier_v1(domain, value)


def _build_commentary_reference_id_v1(value: object, *, legacy_identity: bool = False) -> str:
    domain = (
        _LEGACY_COMMENTARY_REFERENCE_ID_DOMAIN
        if legacy_identity
        else _COMMENTARY_REFERENCE_ID_DOMAIN
    )
    return _build_learning_corpus_identifier_v1(domain, value)


def _build_response_reference_id_v1(value: object, *, legacy_identity: bool = False) -> str:
    domain = (
        _LEGACY_RESPONSE_REFERENCE_ID_DOMAIN
        if legacy_identity
        else _RESPONSE_REFERENCE_ID_DOMAIN
    )
    return _build_learning_corpus_identifier_v1(domain, value)
