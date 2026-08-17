import ast
import builtins
from pathlib import Path

import pytest
from test_learning_corpus_human_evidence import _rich_snapshot, _store
from test_match_workspace_contracts import _definition, _observed_game, _set_game

import skat_ai.application.execution as application_execution
import skat_ai.learning_corpus_current_snapshots as current_snapshots_module
import skat_ai.learning_corpus_human_evidence as evidence_module
import skat_ai.learning_corpus_human_evidence_builder as builder_module
import skat_ai.training_dataset as training_dataset_module
from skat_ai.errors import SkatAIValidationError
from skat_ai.learning_corpus_human_evidence_builder import (
    build_learning_corpus_human_evidence_collection_v1,
)
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    _build_learning_corpus_catalog_file_bytes_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence import _build_match_workspace_file_bytes_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _commentless_snapshot(match_id: str = "match-commentless"):
    definition = _definition(match_id=match_id)
    game = _observed_game(definition, match_position=3)
    workspace = _set_game(create_match_workspace_v1(definition), game)
    return build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )


def test_game_evidence_is_created_only_for_games_containing_commentary() -> None:
    _, commented = _rich_snapshot("match-commented")
    commentless = _commentless_snapshot()
    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(commentless, commented, current=(commentless, commented))
    )
    assert collection.observed_game_count == 2
    assert collection.evidence_game_count == 1
    assert tuple(item.match_id for item in collection.games) == ("match-commented",)
    assert collection.decision_count == 6


def test_current_match_without_observed_games_produces_empty_evidence() -> None:
    definition = _definition(match_id="match-empty-current")
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(create_match_workspace_v1(definition))
    )
    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(snapshot, current=(snapshot,))
    )
    assert collection.current_match_count == 1
    assert collection.observed_game_count == 0
    assert collection.decision_count == 0
    assert collection.games == collection.commentaries == collection.responses == ()


def test_commentless_current_game_produces_empty_evidence() -> None:
    snapshot = _commentless_snapshot()
    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(snapshot, current=(snapshot,))
    )
    assert collection.observed_game_count == 1
    assert collection.evidence_game_count == 0
    assert collection.commentary_count == collection.response_count == 0
    assert collection.games == collection.commentaries == collection.responses == ()


def test_commentary_change_updates_source_evidence_and_collection_identities() -> None:
    _, first_snapshot = _rich_snapshot("match-change", first_text="First exact text.")
    _, changed_snapshot = _rich_snapshot(
        "match-change",
        first_text="Changed exact text.",
    )
    first = build_learning_corpus_human_evidence_collection_v1(
        _store(first_snapshot, changed_snapshot, current=(first_snapshot,))
    )
    changed = build_learning_corpus_human_evidence_collection_v1(
        _store(first_snapshot, changed_snapshot, current=(changed_snapshot,))
    )
    assert first.commentaries[0].commentary_content_fingerprint != (
        changed.commentaries[0].commentary_content_fingerprint
    )
    assert first.commentaries[0].commentary_evidence_id != (
        changed.commentaries[0].commentary_evidence_id
    )
    assert first.games[0].game_evidence_id != changed.games[0].game_evidence_id
    assert first.human_evidence_collection_fingerprint != (
        changed.human_evidence_collection_fingerprint
    )
    assert first.commentaries[1].text == changed.commentaries[1].text


def test_builder_strictly_revalidates_store_catalog_fingerprints() -> None:
    _, snapshot = _rich_snapshot()
    store = _store(snapshot, current=(snapshot,))
    object.__setattr__(store.document, "catalog_fingerprint", "0" * 64)
    with pytest.raises(SkatAIValidationError, match="catalog_fingerprint"):
        build_learning_corpus_human_evidence_collection_v1(store)


def test_duplicate_derived_commentary_ids_are_rejected(monkeypatch) -> None:
    _, snapshot = _rich_snapshot()
    monkeypatch.setattr(
        builder_module,
        "_build_commentary_evidence_id_v1",
        lambda **_kwargs: "a" * 64,
    )
    with pytest.raises(ValueError, match="commentary_evidence_ids must contain unique"):
        build_learning_corpus_human_evidence_collection_v1(_store(snapshot, current=(snapshot,)))


def test_builder_validates_store_once_and_computes_each_identity_once(
    monkeypatch,
) -> None:
    _, snapshot = _rich_snapshot()
    store = _store(snapshot, current=(snapshot,))
    counts = {
        "resume": 0,
        "store_validation": 0,
        "identifier": 0,
        "commentary_content": 0,
        "response_content": 0,
    }
    original_resume = current_snapshots_module.resume_learning_corpus_catalog_document_v1
    original_validation = LearningCorpusStoreResumeResultV1._validate_structure
    original_identifier = evidence_module._build_identifier
    original_commentary = builder_module.build_learning_corpus_commentary_content_fingerprint_v1
    original_response = builder_module.build_learning_corpus_response_content_fingerprint_v1

    def counted_resume(*args, **kwargs):
        counts["resume"] += 1
        return original_resume(*args, **kwargs)

    def counted_validation(self, *args, **kwargs):
        counts["store_validation"] += 1
        return original_validation(self, *args, **kwargs)

    def counted_identifier(*args, **kwargs):
        counts["identifier"] += 1
        return original_identifier(*args, **kwargs)

    def counted_commentary(*args, **kwargs):
        counts["commentary_content"] += 1
        return original_commentary(*args, **kwargs)

    def counted_response(*args, **kwargs):
        counts["response_content"] += 1
        return original_response(*args, **kwargs)

    monkeypatch.setattr(
        current_snapshots_module,
        "resume_learning_corpus_catalog_document_v1",
        counted_resume,
    )
    monkeypatch.setattr(
        LearningCorpusStoreResumeResultV1,
        "_validate_structure",
        counted_validation,
    )
    monkeypatch.setattr(evidence_module, "_build_identifier", counted_identifier)
    monkeypatch.setattr(
        builder_module,
        "build_learning_corpus_commentary_content_fingerprint_v1",
        counted_commentary,
    )
    monkeypatch.setattr(
        builder_module,
        "build_learning_corpus_response_content_fingerprint_v1",
        counted_response,
    )
    collection = build_learning_corpus_human_evidence_collection_v1(store)
    assert counts == {
        "resume": 1,
        "store_validation": 1,
        "identifier": 14,
        "commentary_content": 3,
        "response_content": 3,
    }
    assert collection.human_evidence_collection_fingerprint


def test_builder_performs_no_io_analysis_profile_or_dataset_generation(
    monkeypatch,
) -> None:
    source_document, snapshot = _rich_snapshot()
    store = _store(snapshot, current=(snapshot,))
    source_workspace_bytes = _build_match_workspace_file_bytes_v1(source_document)
    source_catalog_bytes = _build_learning_corpus_catalog_file_bytes_v1(store.document)
    source_store = store.to_dict()

    def fail(*_args, **_kwargs):
        raise AssertionError("Forbidden Human Evidence execution boundary was called.")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(application_execution, "execute_application_invocation", fail)
    monkeypatch.setattr(training_dataset_module, "build_training_dataset_summary", fail)
    collection = build_learning_corpus_human_evidence_collection_v1(store)
    assert collection.commentary_count == 3
    assert _build_match_workspace_file_bytes_v1(source_document) == (source_workspace_bytes)
    assert _build_learning_corpus_catalog_file_bytes_v1(store.document) == (source_catalog_bytes)
    assert store.to_dict() == source_store


def test_human_evidence_modules_have_no_io_analysis_profile_dataset_api_or_cli_imports() -> None:
    forbidden = (
        "pathlib",
        "skat_ai.api",
        "skat_ai.application",
        "skat_ai.capture_web",
        "skat_ai.cli",
        "skat_ai.match_analysis",
        "skat_ai.player_profile",
        "skat_ai.training_dataset",
    )
    paths = (
        PROJECT_ROOT / "src/skat_ai/learning_corpus_current_snapshots.py",
        PROJECT_ROOT / "src/skat_ai/learning_corpus_human_evidence.py",
        PROJECT_ROOT / "src/skat_ai/learning_corpus_human_evidence_builder.py",
        PROJECT_ROOT / "src/skat_ai/learning_corpus_human_evidence_export.py",
    )
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = ()
            if isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                modules = (node.module,)
            for module in modules:
                if module.startswith(forbidden):
                    violations.append((path.name, node.lineno, module))
    assert violations == []
