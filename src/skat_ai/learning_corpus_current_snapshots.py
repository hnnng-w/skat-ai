from __future__ import annotations

from skat_ai.learning_corpus_match_snapshot import LearningCorpusMatchSnapshotV1
from skat_ai.learning_corpus_persistence_codec import (
    resume_learning_corpus_catalog_document_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)


def resolve_learning_corpus_current_match_snapshots_v1(
    store: LearningCorpusStoreResumeResultV1,
) -> tuple[LearningCorpusMatchSnapshotV1, ...]:
    """Strictly resolves explicit Current Match Snapshots without file I/O."""
    if type(store) is not LearningCorpusStoreResumeResultV1:
        raise ValueError("store must be an exact LearningCorpusStoreResumeResultV1.")
    resumed_document = resume_learning_corpus_catalog_document_v1(store.document.to_dict())
    if resumed_document != store.document:
        raise ValueError("Store Catalog document must equal its strict reconstruction.")
    store._validate_structure(validate_snapshots=True)
    snapshots_by_id = {snapshot.match_snapshot_id: snapshot for snapshot in store.match_snapshots}
    return tuple(
        snapshots_by_id[selection.match_snapshot_id]
        for selection in store.document.catalog.current_matches
    )
