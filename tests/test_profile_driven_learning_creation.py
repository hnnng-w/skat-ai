from __future__ import annotations

from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.profile_driven_creation import (
    prepare_profile_driven_learning_creation_v1,
)


def test_learning_form_generates_identity_and_only_adds_private_display_label() -> None:
    profile = build_local_frontend_profile_v1(language="de")
    prepared = prepare_profile_driven_learning_creation_v1(
        {"collection_name": "Meine Lernsammlung"},
        profile=profile,
        expected_profile_generation=4,
        existing_corpus_ids=(),
        entropy_source=lambda _size: b"l" * 32,
    )
    assert prepared.corpus_id.startswith("frontend-corpus-")
    assert prepared.expected_profile_generation == 4
    assert prepared.profile_document.language == "de"
    label = prepared.profile_document.managed_item_display_labels[-1]
    assert label.family == "corpora"
    assert label.product_id == prepared.corpus_id
    assert label.display_name == "Meine Lernsammlung"
    assert label.played_date is None
