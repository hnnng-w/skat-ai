import copy
import hashlib
import json
from collections import OrderedDict

import pytest
from test_learning_corpus_match_snapshot import _annotated_workspace, _snapshot_for_workspace
from test_match_workspace_persistence_codec import _rich_document

from skat_ai.errors import SkatAIValidationError
from skat_ai.learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
    create_empty_learning_corpus_catalog_v1,
)
from skat_ai.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
from skat_ai.learning_corpus_persistence_codec import (
    _build_learning_corpus_catalog_file_bytes_v1,
    _build_learning_corpus_match_snapshot_object_file_bytes_v1,
    build_learning_corpus_catalog_fingerprint_v1,
    build_learning_corpus_catalog_persistence_document_v1,
    resume_learning_corpus_catalog_document_v1,
    resume_learning_corpus_match_snapshot_object_v1,
)


def _canonical(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _document_for_snapshot(snapshot):
    entry = build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot)
    selection = build_learning_corpus_current_match_selection_v1(
        match_id=snapshot.match_id,
        match_snapshot_id=snapshot.match_snapshot_id,
    )
    return build_learning_corpus_catalog_persistence_document_v1(
        build_learning_corpus_catalog_v1(
            corpus_id="corpus-172",
            revision=1,
            match_snapshots=(entry,),
            current_matches=(selection,),
        )
    )


def test_catalog_and_content_fingerprints_match_independent_oracles() -> None:
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    document = _document_for_snapshot(snapshot)
    expected_catalog = hashlib.sha256(
        b"skat-ai\0learning_corpus_catalog_v1\0"
        + _canonical(document.catalog.to_dict())
    ).hexdigest()
    content = document.to_dict()
    del content["content_fingerprint"]
    expected_content = hashlib.sha256(
        b"skat-ai\0learning_corpus_persistence_v1\0" + _canonical(content)
    ).hexdigest()
    assert document.catalog_fingerprint == expected_catalog
    assert document.content_fingerprint == expected_content
    assert build_learning_corpus_catalog_fingerprint_v1(document.catalog) == expected_catalog
    assert len(expected_catalog) == len(expected_content) == 64


def test_catalog_fingerprints_change_with_revision_entry_and_selection() -> None:
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    base = _document_for_snapshot(snapshot)
    changed_revision = build_learning_corpus_catalog_persistence_document_v1(
        build_learning_corpus_catalog_v1(
            corpus_id=base.catalog.corpus_id,
            revision=2,
            match_snapshots=base.catalog.match_snapshots,
            current_matches=base.catalog.current_matches,
        )
    )
    assert changed_revision.catalog_fingerprint != base.catalog_fingerprint
    assert changed_revision.content_fingerprint != base.content_fingerprint


def test_strict_catalog_resume_accepts_mapping_order_and_rebuilds_exact_values() -> None:
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    document = _document_for_snapshot(snapshot)
    reversed_root = OrderedDict(reversed(tuple(document.to_dict().items())))
    resumed = resume_learning_corpus_catalog_document_v1(reversed_root)
    assert resumed == document
    assert resumed.catalog is not document.catalog


@pytest.mark.parametrize(
    "tamper",
    (
        "missing",
        "unknown",
        "persistence_version",
        "kind",
        "catalog_version",
        "entry",
        "selection",
        "catalog_fingerprint",
        "content_fingerprint",
        "entry_order",
    ),
)
def test_strict_catalog_resume_rejects_field_version_relationship_and_hash_drift(
    tamper,
) -> None:
    first_workspace = _annotated_workspace()
    _, first = _snapshot_for_workspace(first_workspace)
    document = _document_for_snapshot(first)
    value = copy.deepcopy(document.to_dict())
    if tamper == "missing":
        value.pop("document_kind")
    elif tamper == "unknown":
        value["path"] = "corpus"
    elif tamper == "persistence_version":
        value["learning_corpus_persistence_version"] = True
    elif tamper == "kind":
        value["document_kind"] = "wrong"
    elif tamper == "catalog_version":
        value["catalog"]["learning_corpus_catalog_version"] = 2
    elif tamper == "entry":
        value["catalog"]["match_snapshots"][0]["unknown"] = None
    elif tamper == "selection":
        value["catalog"]["current_matches"][0]["match_id"] = "wrong"
    elif tamper == "catalog_fingerprint":
        value["catalog_fingerprint"] = "0" * 64
    elif tamper == "content_fingerprint":
        value["content_fingerprint"] = "f" * 64
    else:
        value["catalog"]["match_snapshots"] *= 2
    with pytest.raises(SkatAIValidationError):
        resume_learning_corpus_catalog_document_v1(value)


def test_empty_catalog_resume_and_canonical_catalog_file_bytes() -> None:
    document = build_learning_corpus_catalog_persistence_document_v1(
        create_empty_learning_corpus_catalog_v1("corpus-empty")
    )
    assert resume_learning_corpus_catalog_document_v1(document.to_dict()) == document
    raw = _build_learning_corpus_catalog_file_bytes_v1(document)
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert json.loads(raw) == document.to_dict()


@pytest.mark.parametrize("source", ("empty", "annotated", "rich"))
def test_strict_match_snapshot_object_rebuilds_workspace_and_all_references(source) -> None:
    if source == "rich":
        snapshot = build_learning_corpus_match_snapshot_v1(_rich_document())
    else:
        workspace = _annotated_workspace() if source == "annotated" else None
        if workspace is None:
            from test_match_workspace_contracts import _definition

            from skat_ai.match_workspace_contracts import create_match_workspace_v1

            workspace = create_match_workspace_v1(_definition())
        _, snapshot = _snapshot_for_workspace(workspace)
    resumed = resume_learning_corpus_match_snapshot_object_v1(snapshot.to_dict())
    assert resumed == snapshot
    assert resumed.workspace is not snapshot.workspace


@pytest.mark.parametrize(
    "tamper",
    (
        "missing",
        "unknown",
        "version",
        "snapshot_id",
        "source_fingerprint",
        "workspace",
        "derived_reference",
        "reference_unknown",
    ),
)
def test_strict_match_snapshot_object_rejects_source_and_derived_tampering(tamper) -> None:
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    value = copy.deepcopy(snapshot.to_dict())
    if tamper == "missing":
        value.pop("match_id")
    elif tamper == "unknown":
        value["path"] = "source.json"
    elif tamper == "version":
        value["learning_corpus_match_snapshot_version"] = True
    elif tamper == "snapshot_id":
        value["match_snapshot_id"] = "0" * 64
    elif tamper == "source_fingerprint":
        value["source_content_fingerprint"] = "0" * 64
    elif tamper == "workspace":
        value["workspace"]["revision"] = 999
    elif tamper == "derived_reference":
        value["decision_references"][0]["acting_player_id"] = "wrong"
    else:
        value["game_references"][0]["unknown"] = None
    with pytest.raises(SkatAIValidationError):
        resume_learning_corpus_match_snapshot_object_v1(value)


def test_snapshot_object_file_bytes_are_canonical_and_private() -> None:
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    raw = _build_learning_corpus_match_snapshot_object_file_bytes_v1(snapshot)
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert json.loads(raw) == snapshot.to_dict()
    assert snapshot.workspace.match_definition.source.source_title.encode() in raw
    assert b'"path"' not in raw
