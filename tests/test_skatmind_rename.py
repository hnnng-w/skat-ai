import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from test_learning_corpus_match_snapshot import _annotated_workspace
from test_learning_corpus_strategy_teacher import _source_bundle
from test_match_workspace_persistence import _documents as _workspace_documents
from test_session_persistence import _documents as _session_documents

from skatmind.capture_web.security import (
    MATCH_CAPTURE_WEB_COOKIE_NAME,
    has_valid_match_capture_web_cookie_v1,
)
from skatmind.coherent_hidden_world import derive_simulation_child_seed
from skatmind.corpus_web.security import (
    LEARNING_CORPUS_WEB_COOKIE_NAME,
    has_valid_learning_corpus_web_cookie_v1,
)
from skatmind.dataset_preparation_identity import (
    derive_dataset_partition_seed,
    derive_dataset_partition_tie_break_key,
)
from skatmind.historical_information_set_search_review import (
    derive_historical_information_set_search_decision_seed,
)
from skatmind.historical_search_review import derive_historical_search_decision_seed
from skatmind.learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
)
from skatmind.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
from skatmind.learning_corpus_persistence import (
    initialize_learning_corpus_directory_v1,
    load_learning_corpus_directory_v1,
    publish_learning_corpus_match_snapshot_object_v1,
    save_learning_corpus_catalog_v1,
)
from skatmind.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
    resume_learning_corpus_catalog_document_v1,
    resume_learning_corpus_match_snapshot_object_v1,
)
from skatmind.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skatmind.learning_dataset_v2_partition_identity import (
    derive_learning_dataset_partition_seed_v1,
    derive_learning_dataset_partition_tie_break_key_v1,
)
from skatmind.match_analysis_report_source_codec import (
    resume_match_analysis_report_source_export_v1,
)
from skatmind.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)
from skatmind.match_workspace_persistence import (
    load_match_workspace_file_v1,
    save_match_workspace_file_v1,
)
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
    resume_match_workspace_document_v1,
)
from skatmind.rename_contract import (
    SKATMIND_CLI_COMMAND,
    SKATMIND_DEFAULT_MEMORY_INPUT_REFERENCE,
    SKATMIND_DISTRIBUTION_NAME,
    SKATMIND_DOCUMENT_KIND_PREFIX,
    SKATMIND_FROZEN_DETERMINISTIC_SEED_PROTOCOLS,
    SKATMIND_IMPORT_NAMESPACE,
    SKATMIND_PRODUCT_DISPLAY_NAME,
    SKATMIND_RENAME_CONTRACT_VERSION,
    SKATMIND_RENAME_POLICIES,
    SKATMIND_REPOSITORY_SLUG,
    SKATMIND_SCHEMA_BASE_URI,
    SKATMIND_SHA256_DOMAIN_PREFIX,
)
from skatmind.session_persistence import (
    load_session_persistence_file_v1,
    save_session_persistence_file_v1,
)
from skatmind.session_persistence_codec import resume_session_document_v1

LEGACY_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "skatmind_rename"


def _load_legacy_fixture(name: str) -> dict:
    return json.loads((LEGACY_FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_bytes(value)).hexdigest()


def _legacy_session_document(document) -> dict:
    value = copy.deepcopy(document.to_dict())
    value["document_kind"] = "skat_ai_session"
    value["state_fingerprint"] = _fingerprint(
        b"skat-ai\0session_state_v1\0",
        value["state"],
    )
    content = copy.deepcopy(value)
    content.pop("content_fingerprint")
    value["content_fingerprint"] = _fingerprint(
        b"skat-ai\0session_persistence_v1\0",
        content,
    )
    return value


def _legacy_workspace_document(document) -> dict:
    value = copy.deepcopy(document.to_dict())
    value["document_kind"] = "skat_ai_match_workspace"
    value["workspace_fingerprint"] = _fingerprint(
        b"skat-ai\0match_workspace_v1\0",
        value["workspace"],
    )
    content = copy.deepcopy(value)
    content.pop("content_fingerprint")
    value["content_fingerprint"] = _fingerprint(
        b"skat-ai\0match_workspace_persistence_v1\0",
        content,
    )
    return value


def _legacy_catalog_document(document) -> dict:
    value = copy.deepcopy(document.to_dict())
    value["document_kind"] = "skat_ai_learning_corpus_catalog"
    value["catalog_fingerprint"] = _fingerprint(
        b"skat-ai\0learning_corpus_catalog_v1\0",
        value["catalog"],
    )
    content = copy.deepcopy(value)
    content.pop("content_fingerprint")
    value["content_fingerprint"] = _fingerprint(
        b"skat-ai\0learning_corpus_persistence_v1\0",
        content,
    )
    return value


def _legacy_report_source(document) -> dict:
    value = copy.deepcopy(document)
    value["document_kind"] = "skat_ai_match_analysis_report_source"
    identity = copy.deepcopy(value["report"])
    identity.pop("report_id")
    report_id = _fingerprint(b"skat-ai\0match_analysis_report_v1\0", identity)
    value["report_id"] = report_id
    value["report"]["report_id"] = report_id
    return value


def _json_file_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode()


def test_internal_rename_contract_has_exact_canonical_identity_and_policies() -> None:
    assert SKATMIND_RENAME_CONTRACT_VERSION == 1
    assert SKATMIND_PRODUCT_DISPLAY_NAME == "SkatMind"
    assert SKATMIND_REPOSITORY_SLUG == "hnnng-w/skatmind"
    assert SKATMIND_DISTRIBUTION_NAME == SKATMIND_IMPORT_NAMESPACE == SKATMIND_CLI_COMMAND == (
        "skatmind"
    )
    assert SKATMIND_SCHEMA_BASE_URI == "https://example.local/skatmind/"
    assert SKATMIND_DEFAULT_MEMORY_INPUT_REFERENCE == "memory://skatmind/request"
    assert SKATMIND_DOCUMENT_KIND_PREFIX == "skatmind_"
    assert SKATMIND_SHA256_DOMAIN_PREFIX == b"skatmind\0"
    assert SKATMIND_RENAME_POLICIES == (
        "single_canonical_skatmind_active_identity",
        "no_active_skat_ai_import_or_cli_alias",
        "legacy_persisted_identities_are_strict_input_only",
        "new_writes_use_skatmind_identifiers",
        "legacy_content_addressed_objects_keep_verified_opaque_ids",
        "historical_release_evidence_is_not_rewritten",
        "repository_rename_is_manual_after_merge",
    )
    assert len(SKATMIND_FROZEN_DETERMINISTIC_SEED_PROTOCOLS) == 7


def test_all_frozen_pre_rename_seed_protocol_outputs_remain_exact() -> None:
    v2_partition_seed = derive_learning_dataset_partition_seed_v1(
        "known_player",
        19,
        "e" * 64,
    )
    assert (
        derive_simulation_child_seed(42, "root_world"),
        derive_dataset_partition_seed("known_opponent", 73, "ab" * 32),
        derive_dataset_partition_tie_break_key(
            "known_opponent",
            73,
            "ab" * 32,
            "record-17",
        ),
        derive_historical_information_set_search_decision_seed(77, "game-7", 3),
        derive_historical_search_decision_seed(41, "game-7", 3),
        v2_partition_seed,
        derive_learning_dataset_partition_tie_break_key_v1(
            v2_partition_seed,
            "candidate",
        ),
    ) == (
        11054436669179514905,
        12382102493327604244,
        15752859041772727748,
        9231933580768959435,
        747167969371754881,
        10135302914552623671,
        12620082413584330158,
    )


def test_browser_cookie_rename_does_not_trust_legacy_cookie_names() -> None:
    token = "fixed-token"
    assert MATCH_CAPTURE_WEB_COOKIE_NAME == "skatmind_capture_token"
    assert LEARNING_CORPUS_WEB_COOKIE_NAME == "skatmind_corpus_token"
    assert not has_valid_match_capture_web_cookie_v1(
        f'{"skat" + "_ai"}_capture_token={token}',
        token,
    )
    assert not has_valid_learning_corpus_web_cookie_v1(
        f'{"skat" + "_ai"}_corpus_token={token}',
        token,
    )


def test_legacy_session_load_is_exact_and_explicit_save_is_canonical(tmp_path) -> None:
    canonical, _ = _session_documents()
    fixture_path = LEGACY_FIXTURE_ROOT / "legacy_session_v0_17.json"
    legacy = _load_legacy_fixture(fixture_path.name)
    resumed = resume_session_document_v1(legacy)
    assert resumed.document.to_dict() == legacy
    assert resumed.document.state == canonical.state

    mixed = copy.deepcopy(legacy)
    mixed["document_kind"] = canonical.document_kind
    with pytest.raises(ValueError):
        resume_session_document_v1(mixed)

    file_path = tmp_path / "legacy-session.json"
    original = fixture_path.read_bytes()
    file_path.write_bytes(original)
    loaded = load_session_persistence_file_v1(file_path)
    assert file_path.read_bytes() == original
    result = save_session_persistence_file_v1(
        file_path,
        loaded.document,
        expected_content_fingerprint=loaded.document.content_fingerprint,
    )
    assert result.status == "saved"
    rewritten = load_session_persistence_file_v1(file_path).document
    assert rewritten.document_kind == "skatmind_session"
    assert rewritten.state == loaded.document.state
    assert rewritten.content_fingerprint != loaded.document.content_fingerprint


def test_legacy_workspace_load_is_exact_and_explicit_save_is_canonical(tmp_path) -> None:
    canonical, _ = _workspace_documents()
    fixture_path = LEGACY_FIXTURE_ROOT / "legacy_match_workspace_v0_17.json"
    legacy = _load_legacy_fixture(fixture_path.name)
    resumed = resume_match_workspace_document_v1(legacy)
    assert resumed.document.to_dict() == legacy
    assert resumed.document.workspace == canonical.workspace

    mixed = copy.deepcopy(legacy)
    mixed["workspace_fingerprint"] = canonical.workspace_fingerprint
    with pytest.raises(ValueError):
        resume_match_workspace_document_v1(mixed)

    file_path = tmp_path / "legacy-workspace.json"
    original = fixture_path.read_bytes()
    file_path.write_bytes(original)
    loaded = load_match_workspace_file_v1(file_path)
    assert file_path.read_bytes() == original
    result = save_match_workspace_file_v1(
        file_path,
        loaded.document,
        expected_content_fingerprint=loaded.document.content_fingerprint,
    )
    assert result.status == "saved"
    rewritten = load_match_workspace_file_v1(file_path).document
    assert rewritten.document_kind == "skatmind_match_workspace"
    assert rewritten.workspace == loaded.document.workspace
    assert rewritten.content_fingerprint != loaded.document.content_fingerprint


def test_legacy_corpus_catalog_and_object_remain_exact_and_support_mixed_store(
    tmp_path,
) -> None:
    workspace = _annotated_workspace()

    current_workspace_document = build_match_workspace_persistence_document_v1(workspace)
    current_snapshot = build_learning_corpus_match_snapshot_v1(current_workspace_document)
    legacy_snapshot = resume_learning_corpus_match_snapshot_object_v1(
        _load_legacy_fixture("legacy_learning_corpus_match_snapshot_v0_17.json")
    )
    assert current_snapshot.match_snapshot_id != legacy_snapshot.match_snapshot_id
    assert resume_learning_corpus_match_snapshot_object_v1(legacy_snapshot.to_dict()) == (
        legacy_snapshot
    )

    entries = tuple(
        build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot)
        for snapshot in (legacy_snapshot, current_snapshot)
    )
    catalog = build_learning_corpus_catalog_v1(
        corpus_id="legacy-mixed-corpus",
        revision=1,
        match_snapshots=entries,
        current_matches=(
            build_learning_corpus_current_match_selection_v1(
                match_id=current_snapshot.match_id,
                match_snapshot_id=current_snapshot.match_snapshot_id,
            ),
        ),
    )
    current_catalog_document = build_learning_corpus_catalog_persistence_document_v1(catalog)
    legacy_catalog = _legacy_catalog_document(current_catalog_document)
    assert resume_learning_corpus_catalog_document_v1(legacy_catalog).to_dict() == legacy_catalog
    legacy_catalog_fixture = _load_legacy_fixture("legacy_learning_corpus_catalog_v0_17.json")
    assert resume_learning_corpus_catalog_document_v1(legacy_catalog_fixture).to_dict() == (
        legacy_catalog_fixture
    )

    root = tmp_path / "corpus"
    initialize_learning_corpus_directory_v1(root, corpus_id="temporary")
    assert publish_learning_corpus_match_snapshot_object_v1(root, legacy_snapshot) == "saved"
    assert publish_learning_corpus_match_snapshot_object_v1(root, current_snapshot) == "saved"
    legacy_object_path = (
        root
        / "objects"
        / "match_workspace_snapshot"
        / f"{legacy_snapshot.match_snapshot_id}.json"
    )
    legacy_object_bytes = legacy_object_path.read_bytes()
    (root / "catalog.json").write_bytes(_json_file_bytes(legacy_catalog))

    store = load_learning_corpus_directory_v1(root)
    assert store.document.to_dict() == legacy_catalog
    assert {item.match_snapshot_id for item in store.match_snapshots} == {
        legacy_snapshot.match_snapshot_id,
        current_snapshot.match_snapshot_id,
    }
    assert legacy_object_path.read_bytes() == legacy_object_bytes
    assert publish_learning_corpus_match_snapshot_object_v1(root, legacy_snapshot) == "unchanged"

    result = save_learning_corpus_catalog_v1(
        root,
        store.document,
        expected_content_fingerprint=store.document.content_fingerprint,
    )
    assert result.status == "saved"
    rewritten = load_learning_corpus_directory_v1(root)
    assert rewritten.document.document_kind == "skatmind_learning_corpus_catalog"
    assert legacy_object_path.read_bytes() == legacy_object_bytes


def test_legacy_report_source_loads_exactly_and_reserializes_canonically() -> None:
    _workspace, snapshot, _result, report, _source, _store = _source_bundle()
    current = build_match_analysis_report_source_export_v1(report).to_dict()
    legacy = _load_legacy_fixture("legacy_match_analysis_report_source_v0_17.json")
    resumed = resume_match_analysis_report_source_export_v1(legacy)
    assert resumed.to_dict() == legacy
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=resumed.report,
    )
    assert source.source_report_id == legacy["report_id"]

    mixed = copy.deepcopy(legacy)
    mixed["document_kind"] = current["document_kind"]
    with pytest.raises(ValueError):
        resume_match_analysis_report_source_export_v1(mixed)

    rewritten = json.loads(serialize_match_analysis_report_source_export_v1(resumed))
    assert rewritten == current
    assert rewritten["document_kind"] == "skatmind_match_analysis_report_source"


def test_repository_old_name_inventory_is_exact_and_reviewed() -> None:
    project_root = Path(__file__).parent.parent
    inventory = json.loads(
        (project_root / "docs" / "skatmind_rename_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    assert inventory["inventory_version"] == 1
    assert inventory["matching_policy"] == "exact_case_sensitive_line_occurrences"
    assert inventory["classifications"] == [
        "active_identity",
        "legacy_persisted_input",
        "historical_evidence",
        "external_or_legal_text",
    ]

    token_values = {
        "display_name_with_space": ("Skat" + " AI").encode(),
        "public_symbol_prefix": ("Skat" + "AI").encode(),
        "hyphenated_identity": ("skat" + "-ai").encode(),
        "underscore_identity": ("skat" + "_ai").encode(),
        "upper_underscore_identity": ("SKAT" + "_AI").encode(),
    }
    listed = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    actual = []
    for relative_path in sorted(listed.stdout.splitlines()):
        path = project_root / relative_path
        if not path.is_file():
            continue
        for line_number, line in enumerate(path.read_bytes().splitlines(), start=1):
            for token, value in token_values.items():
                count = line.count(value)
                if count:
                    actual.append(
                        (
                            relative_path,
                            line_number,
                            token,
                            count,
                            hashlib.sha256(line).hexdigest(),
                        )
                    )

    expected = []
    for occurrence in inventory["occurrences"]:
        assert occurrence["token"] in token_values
        assert occurrence["classification"] in inventory["classifications"]
        assert occurrence["classification"] != "active_identity"
        assert occurrence["reason"].strip()
        expected.append(
            (
                occurrence["path"],
                occurrence["line"],
                occurrence["token"],
                occurrence["count"],
                occurrence["line_sha256"],
            )
        )

    assert len(expected) == len(set(expected))
    assert sorted(actual) == sorted(expected)
