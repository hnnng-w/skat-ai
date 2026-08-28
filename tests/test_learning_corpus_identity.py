import hashlib
import json
from dataclasses import FrozenInstanceError, fields

import pytest
from test_match_workspace_contracts import (
    _annotated_observed_game,
    _definition,
    _set_game,
)

from skatmind.learning_corpus_catalog import (
    LEARNING_CORPUS_CATALOG_VERSION,
    LEARNING_CORPUS_MATCH_SNAPSHOT_RELATIONS,
    LEARNING_CORPUS_SNAPSHOT_CLASSIFICATION_VERSION,
    LearningCorpusCatalogV1,
    LearningCorpusCurrentMatchSelectionV1,
    LearningCorpusMatchSnapshotCatalogEntryV1,
    LearningCorpusMatchSnapshotClassificationV1,
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
    classify_learning_corpus_match_snapshot_v1,
)
from skatmind.learning_corpus_identity import (
    LEARNING_CORPUS_CURRENT_SELECTION_POLICY,
    LEARNING_CORPUS_DUPLICATE_POLICY,
    LEARNING_CORPUS_IDENTITY_POLICY,
    LEARNING_CORPUS_IDENTITY_VERSION,
    LEARNING_CORPUS_OBJECT_KIND_POLICY,
    LEARNING_CORPUS_OBJECT_KINDS,
    LEARNING_CORPUS_PLAYER_IDENTITY_POLICY,
    LEARNING_CORPUS_PRIVACY_POLICY,
    LEARNING_CORPUS_REFERENCE_POLICY,
    LEARNING_CORPUS_REVISION_POLICY,
    LEARNING_CORPUS_SAME_REVISION_POLICY,
    LEARNING_CORPUS_SOURCE_OF_TRUTH_POLICY,
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_match_snapshot import (
    LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION,
    LearningCorpusMatchSnapshotV1,
    build_learning_corpus_match_snapshot_v1,
)
from skatmind.learning_corpus_references import (
    LEARNING_CORPUS_REFERENCE_VERSION,
    LearningCorpusCommentaryReferenceV1,
    LearningCorpusDecisionReferenceV1,
    LearningCorpusGameReferenceV1,
    LearningCorpusPlayerObservationV1,
    LearningCorpusResponseReferenceV1,
    build_learning_corpus_game_content_fingerprint_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_bytes(value)).hexdigest()


def _annotated_snapshot() -> LearningCorpusMatchSnapshotV1:
    definition = _definition()
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _annotated_observed_game(definition),
    )
    return build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )


def test_versions_tuples_policies_and_contract_fields_are_exact() -> None:
    assert (
        LEARNING_CORPUS_IDENTITY_VERSION,
        LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION,
        LEARNING_CORPUS_REFERENCE_VERSION,
        LEARNING_CORPUS_CATALOG_VERSION,
        LEARNING_CORPUS_SNAPSHOT_CLASSIFICATION_VERSION,
    ) == (1, 1, 1, 1, 1)
    assert LEARNING_CORPUS_OBJECT_KINDS == ("match_workspace_snapshot",)
    assert LEARNING_CORPUS_MATCH_SNAPSHOT_RELATIONS == (
        "new_match",
        "duplicate_snapshot",
        "newer_revision",
        "older_revision",
        "same_revision_content_conflict",
    )
    assert LEARNING_CORPUS_SOURCE_OF_TRUTH_POLICY == (
        "immutable_imported_workspace_snapshot"
    )
    assert LEARNING_CORPUS_IDENTITY_POLICY == (
        "logical_identity_plus_content_addressed_revision"
    )
    assert LEARNING_CORPUS_OBJECT_KIND_POLICY == "append_only_object_kinds"
    assert LEARNING_CORPUS_DUPLICATE_POLICY == (
        "equal_content_deduplicates_by_snapshot_id"
    )
    assert LEARNING_CORPUS_REVISION_POLICY == (
        "same_match_distinct_content_retains_distinct_snapshot"
    )
    assert LEARNING_CORPUS_SAME_REVISION_POLICY == (
        "same_revision_distinct_content_requires_explicit_resolution"
    )
    assert LEARNING_CORPUS_CURRENT_SELECTION_POLICY == (
        "explicit_current_snapshot_per_logical_match"
    )
    assert LEARNING_CORPUS_PLAYER_IDENTITY_POLICY == (
        "exact_stable_player_ids_without_fuzzy_merge"
    )
    assert LEARNING_CORPUS_REFERENCE_POLICY == "snapshot_closed_derived_references"
    assert LEARNING_CORPUS_PRIVACY_POLICY == "private_local_unredacted_learning_data"

    assert tuple(field.name for field in fields(LearningCorpusMatchSnapshotV1)) == (
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
    )
    assert tuple(field.name for field in fields(LearningCorpusPlayerObservationV1)) == (
        "learning_corpus_reference_version",
        "player_observation_id",
        "match_snapshot_id",
        "player_id",
        "table_place",
        "player_label",
        "game_platform",
        "platform_player_id",
        "statistics_snapshot_id",
    )
    assert tuple(field.name for field in fields(LearningCorpusGameReferenceV1)) == (
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
    )
    assert tuple(field.name for field in fields(LearningCorpusDecisionReferenceV1)) == (
        "learning_corpus_reference_version",
        "decision_reference_id",
        "match_snapshot_id",
        "game_reference_id",
        "match_id",
        "game_id",
        "match_position",
        "decision_index",
        "acting_player_id",
    )
    assert tuple(field.name for field in fields(LearningCorpusCommentaryReferenceV1)) == (
        "learning_corpus_reference_version",
        "commentary_reference_id",
        "match_snapshot_id",
        "game_reference_id",
        "commentary_id",
        "subject_decision_reference_id",
    )
    assert tuple(field.name for field in fields(LearningCorpusResponseReferenceV1)) == (
        "learning_corpus_reference_version",
        "response_reference_id",
        "match_snapshot_id",
        "game_reference_id",
        "link_id",
        "commentary_reference_id",
        "response_decision_reference_id",
    )
    assert tuple(
        field.name for field in fields(LearningCorpusMatchSnapshotCatalogEntryV1)
    ) == (
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
    )
    assert tuple(field.name for field in fields(LearningCorpusCurrentMatchSelectionV1)) == (
        "learning_corpus_catalog_version",
        "match_id",
        "match_snapshot_id",
    )
    assert tuple(field.name for field in fields(LearningCorpusCatalogV1)) == (
        "learning_corpus_catalog_version",
        "corpus_id",
        "revision",
        "match_snapshots",
        "current_matches",
    )
    assert tuple(
        field.name for field in fields(LearningCorpusMatchSnapshotClassificationV1)
    ) == (
        "learning_corpus_snapshot_classification_version",
        "relation",
        "match_id",
        "candidate_snapshot_id",
        "candidate_workspace_revision",
        "current_snapshot_id",
        "current_workspace_revision",
        "same_match_snapshot_ids",
        "same_revision_snapshot_ids",
    )


def test_canonical_json_is_ascii_sorted_compact_finite_utf8() -> None:
    value = {"z": "ä", "a": [1, None, True]}
    canonical = build_learning_corpus_canonical_json_bytes_v1(value)
    assert canonical == b'{"a":[1,null,true],"z":"\\u00e4"}'
    assert canonical == _canonical_bytes(value)
    with pytest.raises(ValueError, match="Out of range float values"):
        build_learning_corpus_canonical_json_bytes_v1({"invalid": float("nan")})


def test_all_seven_hash_domains_match_independent_oracles() -> None:
    snapshot = _annotated_snapshot()
    workspace = snapshot.workspace
    game = workspace.slots[2].observed_game
    assert game is not None
    snapshot_material = {
        "learning_corpus_match_snapshot_version": 1,
        "object_kind": "match_workspace_snapshot",
        "source_workspace_fingerprint": snapshot.source_workspace_fingerprint,
        "source_content_fingerprint": snapshot.source_content_fingerprint,
        "workspace": workspace.to_dict(),
    }
    assert snapshot.match_snapshot_id == _hash(
        b"skatmind\0learning_corpus_match_snapshot_v1\0",
        snapshot_material,
    )

    player = snapshot.player_observations[0]
    player_material = player.to_dict()
    del player_material["player_observation_id"]
    assert player.player_observation_id == _hash(
        b"skatmind\0learning_corpus_player_observation_v1\0",
        player_material,
    )

    game_reference = snapshot.game_references[0]
    assert game_reference.game_content_fingerprint == _hash(
        b"skatmind\0learning_corpus_game_content_v1\0",
        game.to_dict(),
    )
    assert build_learning_corpus_game_content_fingerprint_v1(game) == (
        game_reference.game_content_fingerprint
    )
    game_material = {
        "learning_corpus_reference_version": 1,
        "game_content_fingerprint": game_reference.game_content_fingerprint,
        "match_snapshot_id": snapshot.match_snapshot_id,
        "match_id": snapshot.match_id,
        "match_position": game_reference.match_position,
        "game_id": game_reference.game_id,
    }
    assert game_reference.game_reference_id == _hash(
        b"skatmind\0learning_corpus_game_reference_v1\0",
        game_material,
    )

    decision = snapshot.decision_references[0]
    decision_material = decision.to_dict()
    del decision_material["decision_reference_id"]
    assert decision.decision_reference_id == _hash(
        b"skatmind\0learning_corpus_decision_reference_v1\0",
        decision_material,
    )

    commentary = snapshot.commentary_references[0]
    commentary_material = commentary.to_dict()
    del commentary_material["commentary_reference_id"]
    assert commentary.commentary_reference_id == _hash(
        b"skatmind\0learning_corpus_commentary_reference_v1\0",
        commentary_material,
    )

    response = snapshot.response_references[0]
    response_material = response.to_dict()
    del response_material["response_reference_id"]
    assert response.response_reference_id == _hash(
        b"skatmind\0learning_corpus_response_reference_v1\0",
        response_material,
    )


def test_all_values_are_builder_controlled_frozen_slotted_and_freshly_serialized() -> None:
    snapshot = _annotated_snapshot()
    entry = build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot)
    selection = build_learning_corpus_current_match_selection_v1(
        match_id=snapshot.match_id,
        match_snapshot_id=snapshot.match_snapshot_id,
    )
    catalog = build_learning_corpus_catalog_v1(
        corpus_id="corpus-171",
        revision=1,
        match_snapshots=(entry,),
        current_matches=(selection,),
    )
    classification = classify_learning_corpus_match_snapshot_v1(catalog, snapshot)
    values = (
        snapshot,
        *snapshot.player_observations,
        *snapshot.game_references,
        *snapshot.decision_references,
        *snapshot.commentary_references,
        *snapshot.response_references,
        entry,
        selection,
        catalog,
        classification,
    )
    for value in values:
        assert not hasattr(value, "__dict__")
        serialized = value.to_dict()
        second = value.to_dict()
        serialized["test_mutation"] = True
        assert "test_mutation" not in second
        first_field = fields(value)[0].name
        with pytest.raises(FrozenInstanceError):
            setattr(value, first_field, getattr(value, first_field))

    for contract in (
        LearningCorpusMatchSnapshotV1,
        LearningCorpusPlayerObservationV1,
        LearningCorpusGameReferenceV1,
        LearningCorpusDecisionReferenceV1,
        LearningCorpusCommentaryReferenceV1,
        LearningCorpusResponseReferenceV1,
        LearningCorpusMatchSnapshotCatalogEntryV1,
        LearningCorpusCurrentMatchSelectionV1,
        LearningCorpusCatalogV1,
        LearningCorpusMatchSnapshotClassificationV1,
    ):
        with pytest.raises(TypeError, match="focused builder"):
            contract()
