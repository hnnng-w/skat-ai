import hashlib
import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_historical_game import build_historical_input
from test_match_capture_contracts import _participants
from test_match_workspace_contracts import (
    _definition,
    _observed_game,
    _seat_order,
    _set_game,
)
from test_observed_game_contracts import (
    declaration_from_historical,
    observed_plays_from_historical,
)

from skat_ai.learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
    create_empty_learning_corpus_catalog_v1,
)
from skat_ai.learning_corpus_human_evidence import (
    LEARNING_CORPUS_ANALYSIS_SEPARATION_POLICY,
    LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION,
    LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS,
    LEARNING_CORPUS_DERIVED_TAG_POLICY,
    LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION,
    LEARNING_CORPUS_HUMAN_EVIDENCE_KINDS,
    LEARNING_CORPUS_HUMAN_EVIDENCE_ORDER_POLICY,
    LEARNING_CORPUS_HUMAN_EVIDENCE_PRIVACY_POLICY,
    LEARNING_CORPUS_HUMAN_EVIDENCE_SOURCE_POLICY,
    LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION,
    LEARNING_CORPUS_HUMAN_TEXT_POLICY,
    LEARNING_CORPUS_MEDIA_CONTEXT_POLICY,
    LEARNING_CORPUS_OBSERVED_BEHAVIOR_POLICY,
    LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION,
    LEARNING_CORPUS_RESPONSE_RELATION_POLICY,
    LearningCorpusCommentaryEvidenceV1,
    LearningCorpusHumanEvidenceCollectionV1,
    LearningCorpusHumanEvidenceGameV1,
    LearningCorpusResponseEvidenceV1,
    build_learning_corpus_commentary_content_fingerprint_v1,
    build_learning_corpus_response_content_fingerprint_v1,
)
from skat_ai.learning_corpus_human_evidence_builder import (
    build_learning_corpus_human_evidence_collection_v1,
)
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)
from skat_ai.observed_game_commentary import (
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
)
from skat_ai.observed_game_trace import ObservedPlayV1


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def _store(
    *snapshots,
    current=(),
    revision: int = 1,
    orphans: tuple[str, ...] = (),
) -> LearningCorpusStoreResumeResultV1:
    if not snapshots:
        catalog = create_empty_learning_corpus_catalog_v1("corpus-174")
        return LearningCorpusStoreResumeResultV1(
            document=build_learning_corpus_catalog_persistence_document_v1(catalog),
            match_snapshots=(),
            orphan_match_snapshot_ids=orphans,
        )
    entries = tuple(
        build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot) for snapshot in snapshots
    )
    selections = tuple(
        build_learning_corpus_current_match_selection_v1(
            match_id=snapshot.match_id,
            match_snapshot_id=snapshot.match_snapshot_id,
        )
        for snapshot in current
    )
    catalog = build_learning_corpus_catalog_v1(
        corpus_id="corpus-174",
        revision=revision,
        match_snapshots=entries,
        current_matches=selections,
    )
    snapshots_by_id = {snapshot.match_snapshot_id: snapshot for snapshot in snapshots}
    return LearningCorpusStoreResumeResultV1(
        document=build_learning_corpus_catalog_persistence_document_v1(catalog),
        match_snapshots=tuple(
            snapshots_by_id[entry.match_snapshot_id] for entry in catalog.match_snapshots
        ),
        orphan_match_snapshot_ids=orphans,
    )


def _rich_snapshot(
    match_id: str = "match-174",
    *,
    first_text: str = "Überlegt genau.\nDie Folge bleibt unverändert.",
    with_responses: bool = True,
    shared_subject_decision: bool = False,
):
    definition = _definition(
        match_id=match_id,
        title=f"Evidence {match_id}",
        external_match_id=f"external-{match_id}",
        participants=_participants(),
    )
    historical = build_historical_input(game_type="grand", hand_game=False)
    source_plays = observed_plays_from_historical(historical, count=6)
    plays = tuple(
        ObservedPlayV1(
            decision_index=play.decision_index,
            player_id=play.player_id,
            card=play.card,
            decision_timecode=MediaTimecodeV1(
                start_offset_ms=221_000 + index * 1_000,
                end_offset_ms=221_400 + index * 1_000,
            ),
        )
        for index, play in enumerate(source_plays)
    )
    commentaries = (
        ObservedDecisionCommentaryV1(
            commentary_id="comment-perspective",
            decision_index=1,
            subject_player_id=plays[0].player_id,
            commentator_player_id="player-a",
            commentator_name=None,
            text=first_text,
            commentary_timecode=MediaTimecodeV1(
                start_offset_ms=230_000,
                end_offset_ms=231_000,
            ),
        ),
        ObservedDecisionCommentaryV1(
            commentary_id="comment-external",
            decision_index=1 if shared_subject_decision else 2,
            subject_player_id=(
                plays[0].player_id if shared_subject_decision else plays[1].player_id
            ),
            commentator_player_id=None,
            commentator_name="Video analyst",
            text="Exact external observation.",
            commentary_timecode=None,
        ),
        ObservedDecisionCommentaryV1(
            commentary_id="comment-combined",
            decision_index=3,
            subject_player_id=plays[2].player_id,
            commentator_player_id="player-c",
            commentator_name="Carol on source audio",
            text="Exact combined observation.",
            commentary_timecode=MediaTimecodeV1(
                start_offset_ms=234_000,
                end_offset_ms=None,
            ),
        ),
    )
    response_links = (
        (
            ObservedDecisionResponseLinkV1(
                link_id="response-same-trick",
                commentary_id="comment-perspective",
                response_decision_index=2,
            ),
            ObservedDecisionResponseLinkV1(
                link_id="response-later-trick",
                commentary_id="comment-perspective",
                response_decision_index=4,
            ),
            ObservedDecisionResponseLinkV1(
                link_id="response-external",
                commentary_id="comment-external",
                response_decision_index=5,
            ),
        )
        if with_responses
        else ()
    )
    perspective_hand = next(
        player["initial_hand"]
        for player in historical["players"]
        if player["player_id"] == definition.perspective_player_id
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"game-{match_id}",
        perspective_initial_hand=perspective_hand,
        declarer_player_id=historical["declarer_player_id"],
        declaration=declaration_from_historical(historical),
        original_skat=historical["skat"],
        discarded_cards=historical["discarded_cards"],
        plays=plays,
        commentaries=commentaries,
        response_links=response_links,
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    document = build_match_workspace_persistence_document_v1(workspace)
    return document, build_learning_corpus_match_snapshot_v1(document)


def _rich_collection() -> tuple[
    LearningCorpusHumanEvidenceCollectionV1,
    object,
]:
    _, snapshot = _rich_snapshot()
    return (
        build_learning_corpus_human_evidence_collection_v1(_store(snapshot, current=(snapshot,))),
        snapshot,
    )


def test_versions_tuples_policies_and_contract_fields_are_exact() -> None:
    assert (
        LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION,
        LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION,
        LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION,
        LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION,
    ) == (1, 1, 1, 1)
    assert LEARNING_CORPUS_HUMAN_EVIDENCE_KINDS == (
        "commentary",
        "linked_response",
    )
    assert LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS == (
        "match_player",
        "external",
        "match_player_and_external",
    )
    assert (
        LEARNING_CORPUS_HUMAN_EVIDENCE_SOURCE_POLICY,
        LEARNING_CORPUS_HUMAN_TEXT_POLICY,
        LEARNING_CORPUS_RESPONSE_RELATION_POLICY,
        LEARNING_CORPUS_OBSERVED_BEHAVIOR_POLICY,
        LEARNING_CORPUS_MEDIA_CONTEXT_POLICY,
        LEARNING_CORPUS_DERIVED_TAG_POLICY,
        LEARNING_CORPUS_ANALYSIS_SEPARATION_POLICY,
        LEARNING_CORPUS_HUMAN_EVIDENCE_ORDER_POLICY,
        LEARNING_CORPUS_HUMAN_EVIDENCE_PRIVACY_POLICY,
    ) == (
        "explicit_current_match_snapshots_only",
        "preserve_exact_human_text_without_normalization_or_taxonomy",
        "caller_linked_later_observed_decision_without_causal_claim",
        "actual_cards_are_observed_behavior_not_optimal_labels",
        "retain_descriptive_source_metadata_and_exact_timecodes",
        "no_derived_tags_in_version_1",
        "human_evidence_does_not_influence_analysis_search_or_coaching",
        "current_match_game_commentary_response_canonical_order",
        "private_local_minimized_unredacted_human_evidence",
    )
    assert tuple(field.name for field in fields(LearningCorpusHumanEvidenceGameV1)) == (
        "learning_corpus_human_evidence_game_version",
        "game_evidence_id",
        "match_snapshot_id",
        "game_reference_id",
        "game_content_fingerprint",
        "match_id",
        "workspace_revision",
        "match_position",
        "game_id",
        "match_title",
        "external_match_id",
        "played_at",
        "game_platform",
        "source_kind",
        "source_url",
        "source_title",
        "source_channel_name",
        "match_timecode",
        "game_timecode",
        "perspective_player_id",
        "forehand_player_id",
        "middlehand_player_id",
        "rearhand_player_id",
        "declarer_player_id",
        "declaration",
        "decision_count",
        "commentary_evidence_ids",
        "response_evidence_ids",
    )
    assert tuple(field.name for field in fields(LearningCorpusCommentaryEvidenceV1)) == (
        "learning_corpus_commentary_evidence_version",
        "commentary_evidence_id",
        "commentary_content_fingerprint",
        "commentary_reference_id",
        "game_evidence_id",
        "match_snapshot_id",
        "game_reference_id",
        "commentary_id",
        "subject_decision_reference_id",
        "subject_decision_index",
        "subject_trick_number",
        "subject_play_index",
        "subject_player_id",
        "subject_player_label",
        "subject_seat",
        "subject_role",
        "actual_card_played",
        "decision_timecode",
        "commentary_timecode",
        "commentator_identity_kind",
        "commentator_player_id",
        "commentator_name",
        "text",
        "response_evidence_ids",
    )
    assert tuple(field.name for field in fields(LearningCorpusResponseEvidenceV1)) == (
        "learning_corpus_response_evidence_version",
        "response_evidence_id",
        "response_content_fingerprint",
        "response_reference_id",
        "game_evidence_id",
        "match_snapshot_id",
        "game_reference_id",
        "link_id",
        "commentary_evidence_id",
        "commentary_reference_id",
        "subject_decision_reference_id",
        "subject_decision_index",
        "response_decision_reference_id",
        "response_decision_index",
        "response_trick_number",
        "response_play_index",
        "response_player_id",
        "response_player_label",
        "response_seat",
        "response_role",
        "response_card_played",
        "response_decision_timecode",
        "decision_offset",
        "same_trick",
    )
    assert tuple(field.name for field in fields(LearningCorpusHumanEvidenceCollectionV1)) == (
        "learning_corpus_human_evidence_version",
        "human_evidence_collection_fingerprint",
        "corpus_id",
        "source_catalog_revision",
        "source_catalog_fingerprint",
        "source_catalog_content_fingerprint",
        "current_match_snapshot_ids",
        "retained_match_snapshot_count",
        "current_match_count",
        "orphan_match_snapshot_count",
        "observed_game_count",
        "evidence_game_count",
        "decision_count",
        "commented_decision_count",
        "commentary_count",
        "response_count",
        "games",
        "commentaries",
        "responses",
    )


def test_empty_collection_is_valid_deterministic_and_fingerprinted() -> None:
    source = _store()
    first = build_learning_corpus_human_evidence_collection_v1(source)
    second = build_learning_corpus_human_evidence_collection_v1(source)
    assert first == second
    assert first.current_match_snapshot_ids == ()
    assert first.games == first.commentaries == first.responses == ()
    assert (
        first.retained_match_snapshot_count,
        first.current_match_count,
        first.orphan_match_snapshot_count,
        first.observed_game_count,
        first.evidence_game_count,
        first.decision_count,
        first.commented_decision_count,
        first.commentary_count,
        first.response_count,
    ) == (0, 0, 0, 0, 0, 0, 0, 0, 0)
    material = first.to_dict()
    del material["human_evidence_collection_fingerprint"]
    assert first.human_evidence_collection_fingerprint == _hash(
        b"skat-ai\0learning_corpus_human_evidence_collection_v1\0",
        material,
    )


def test_game_evidence_retains_exact_source_context_without_full_trace() -> None:
    collection, snapshot = _rich_collection()
    source_game = snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    game = collection.games[0]
    definition = snapshot.workspace.match_definition
    reference = snapshot.game_references[0]
    assert game.game_evidence_id == _hash(
        b"skat-ai\0learning_corpus_human_evidence_game_v1\0",
        {
            "learning_corpus_human_evidence_game_version": 1,
            "match_snapshot_id": snapshot.match_snapshot_id,
            "game_reference_id": reference.game_reference_id,
            "game_content_fingerprint": reference.game_content_fingerprint,
        },
    )
    assert (game.match_snapshot_id, game.game_reference_id) == (
        snapshot.match_snapshot_id,
        reference.game_reference_id,
    )
    assert (game.match_id, game.game_id, game.workspace_revision) == (
        snapshot.match_id,
        source_game.game_id,
        snapshot.workspace_revision,
    )
    assert (game.match_title, game.game_platform, game.external_match_id) == (
        definition.title,
        definition.game_platform,
        definition.external_match_id,
    )
    assert (
        game.source_kind,
        game.source_url,
        game.source_title,
        game.source_channel_name,
    ) == (
        definition.source.source_kind,
        definition.source.source_url,
        definition.source.source_title,
        definition.source.source_channel_name,
    )
    assert game.match_timecode == definition.source.match_timecode
    assert game.game_timecode == source_game.game_timecode
    assert game.declaration == source_game.declaration
    assert game.decision_count == 6
    assert game.commentary_evidence_ids == tuple(
        item.commentary_evidence_id for item in collection.commentaries
    )
    assert game.response_evidence_ids == tuple(
        item.response_evidence_id for item in collection.responses
    )


def test_commentary_fingerprints_identity_kinds_text_cards_timecodes_seats_and_roles() -> None:
    collection, snapshot = _rich_collection()
    source_game = snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    assert tuple(item.commentator_identity_kind for item in collection.commentaries) == (
        "match_player",
        "external",
        "match_player_and_external",
    )
    assert tuple(item.text for item in collection.commentaries) == tuple(
        item.text for item in source_game.commentaries
    )
    for evidence, source, reference in zip(
        collection.commentaries,
        source_game.commentaries,
        snapshot.commentary_references,
        strict=True,
    ):
        source_play = source_game.plays[source.decision_index - 1]
        decision_reference = snapshot.decision_references[source.decision_index - 1]
        expected_fingerprint = _hash(
            b"skat-ai\0learning_corpus_commentary_content_v1\0",
            source.to_dict(),
        )
        assert evidence.commentary_content_fingerprint == expected_fingerprint
        assert build_learning_corpus_commentary_content_fingerprint_v1(source) == (
            expected_fingerprint
        )
        assert evidence.commentary_evidence_id == _hash(
            b"skat-ai\0learning_corpus_commentary_evidence_v1\0",
            {
                "learning_corpus_commentary_evidence_version": 1,
                "game_evidence_id": collection.games[0].game_evidence_id,
                "commentary_reference_id": reference.commentary_reference_id,
                "commentary_content_fingerprint": expected_fingerprint,
            },
        )
        assert evidence.subject_decision_reference_id == (decision_reference.decision_reference_id)
        assert evidence.actual_card_played == source_play.card
        assert evidence.decision_timecode == source_play.decision_timecode
        assert evidence.commentary_timecode == source.commentary_timecode
        assert evidence.subject_seat == next(
            player.seat
            for player in source_game.players
            if player.player_id == source_play.player_id
        )
        assert evidence.subject_role == (
            "declarer" if source_play.player_id == source_game.declarer_player_id else "defender"
        )
    assert collection.commentaries[0].subject_player_id == (source_game.perspective_player_id)
    assert {item.subject_player_id for item in collection.commentaries[1:]} != {
        source_game.perspective_player_id
    }


def test_commentary_content_fingerprint_covers_every_mutable_source_fact() -> None:
    _, snapshot = _rich_snapshot()
    source_game = snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    source = source_game.commentaries[0]
    fingerprint = build_learning_corpus_commentary_content_fingerprint_v1(source)
    variants = (
        replace(source, text="Changed multiline text.\nSecond line."),
        replace(source, commentator_player_id="player-b"),
        replace(source, commentator_name="External analyst"),
        replace(source, subject_player_id="player-b"),
        replace(
            source,
            commentary_timecode=MediaTimecodeV1(
                start_offset_ms=230_001,
                end_offset_ms=231_000,
            ),
        ),
    )
    assert build_learning_corpus_commentary_content_fingerprint_v1(replace(source)) == (fingerprint)
    assert all(
        build_learning_corpus_commentary_content_fingerprint_v1(variant) != fingerprint
        for variant in variants
    )


def test_response_fingerprints_same_and_later_tricks_and_one_to_many_relationships() -> None:
    collection, snapshot = _rich_collection()
    source_game = snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    assert tuple(item.same_trick for item in collection.responses) == (
        True,
        False,
        False,
    )
    assert tuple(item.decision_offset for item in collection.responses) == (1, 3, 3)
    assert len(collection.commentaries[0].response_evidence_ids) == 2
    assert collection.commentaries[1].response_evidence_ids == (
        collection.responses[2].response_evidence_id,
    )
    assert collection.commentaries[2].response_evidence_ids == ()
    response_references = {
        item.response_reference_id: item for item in snapshot.response_references
    }
    for evidence, source in zip(
        collection.responses,
        source_game.response_links,
        strict=True,
    ):
        response_reference = response_references[evidence.response_reference_id]
        response_play = source_game.plays[source.response_decision_index - 1]
        expected_fingerprint = _hash(
            b"skat-ai\0learning_corpus_response_content_v1\0",
            source.to_dict(),
        )
        assert evidence.response_content_fingerprint == expected_fingerprint
        assert build_learning_corpus_response_content_fingerprint_v1(source) == (
            expected_fingerprint
        )
        assert evidence.response_evidence_id == _hash(
            b"skat-ai\0learning_corpus_response_evidence_v1\0",
            {
                "learning_corpus_response_evidence_version": 1,
                "game_evidence_id": evidence.game_evidence_id,
                "response_reference_id": response_reference.response_reference_id,
                "response_content_fingerprint": expected_fingerprint,
            },
        )
        assert evidence.response_card_played == response_play.card
        assert evidence.response_decision_timecode == response_play.decision_timecode
        assert evidence.response_seat == next(
            player.seat
            for player in source_game.players
            if player.player_id == response_play.player_id
        )
        assert evidence.response_role == (
            "declarer" if response_play.player_id == source_game.declarer_player_id else "defender"
        )


def test_response_content_fingerprint_covers_every_source_fact() -> None:
    _, snapshot = _rich_snapshot()
    source_game = snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    source = source_game.response_links[0]
    fingerprint = build_learning_corpus_response_content_fingerprint_v1(source)
    variants = (
        replace(source, link_id="changed-link"),
        replace(source, commentary_id="changed-commentary"),
        replace(source, response_decision_index=3),
    )
    assert build_learning_corpus_response_content_fingerprint_v1(replace(source)) == fingerprint
    assert all(
        build_learning_corpus_response_content_fingerprint_v1(variant) != fingerprint
        for variant in variants
    )


def test_commentary_without_responses_produces_a_closed_zero_response_collection() -> None:
    _, snapshot = _rich_snapshot(with_responses=False)
    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(snapshot, current=(snapshot,))
    )
    assert collection.commentary_count == 3
    assert collection.response_count == 0
    assert collection.responses == ()
    assert collection.games[0].response_evidence_ids == ()
    assert all(item.response_evidence_ids == () for item in collection.commentaries)


def test_commented_decision_count_is_distinct_from_commentary_count() -> None:
    _, snapshot = _rich_snapshot(shared_subject_decision=True)
    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(snapshot, current=(snapshot,))
    )
    assert collection.commentary_count == 3
    assert collection.commented_decision_count == 2
    assert tuple(item.subject_decision_index for item in collection.commentaries[:2]) == (
        1,
        1,
    )


def test_collection_counts_references_order_and_fingerprint_reconcile() -> None:
    collection, snapshot = _rich_collection()
    assert collection.current_match_snapshot_ids == (snapshot.match_snapshot_id,)
    assert (
        collection.retained_match_snapshot_count,
        collection.current_match_count,
        collection.orphan_match_snapshot_count,
        collection.observed_game_count,
        collection.evidence_game_count,
        collection.decision_count,
        collection.commented_decision_count,
        collection.commentary_count,
        collection.response_count,
    ) == (1, 1, 0, 1, 1, 6, 3, 3, 3)
    assert tuple(item.subject_decision_index for item in collection.commentaries) == (
        1,
        2,
        3,
    )
    assert tuple(item.response_decision_index for item in collection.responses) == (
        2,
        4,
        5,
    )
    material = collection.to_dict()
    del material["human_evidence_collection_fingerprint"]
    assert collection.human_evidence_collection_fingerprint == _hash(
        b"skat-ai\0learning_corpus_human_evidence_collection_v1\0",
        material,
    )


def test_only_current_snapshots_contribute_and_orphans_are_counted_not_resolved() -> None:
    _, old = _rich_snapshot("match-revision", first_text="Old exact text.")
    _, changed_source = _rich_snapshot(
        "match-revision",
        first_text="Current exact text.",
    )
    changed_game = changed_source.workspace.slots[2].observed_game
    assert changed_game is not None
    current = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(_set_game(old.workspace, changed_game))
    )
    assert old.workspace_revision == 1
    assert current.workspace_revision == 2

    retained_old = build_learning_corpus_human_evidence_collection_v1(
        _store(old, current, current=(old,))
    )
    assert retained_old.current_match_snapshot_ids == (old.match_snapshot_id,)
    assert "Old exact text." in tuple(item.text for item in retained_old.commentaries)
    assert "Current exact text." not in tuple(item.text for item in retained_old.commentaries)

    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(old, current, current=(current,), orphans=("f" * 64,))
    )
    assert collection.current_match_snapshot_ids == (current.match_snapshot_id,)
    assert collection.retained_match_snapshot_count == 2
    assert collection.current_match_count == 1
    assert collection.orphan_match_snapshot_count == 1
    assert "Current exact text." in tuple(item.text for item in collection.commentaries)
    assert "Old exact text." not in tuple(item.text for item in collection.commentaries)
    assert collection.games[0].match_snapshot_id == current.match_snapshot_id


def test_commented_games_use_match_position_order_within_one_match() -> None:
    _, snapshot = _rich_snapshot("match-two-games")
    definition = snapshot.workspace.match_definition
    seat_order = _seat_order(definition, 1)
    earlier_plays = (
        ObservedPlayV1(
            decision_index=1,
            player_id=seat_order[0],
            card="CA",
            decision_timecode=None,
        ),
        ObservedPlayV1(
            decision_index=2,
            player_id=seat_order[1],
            card="C7",
            decision_timecode=None,
        ),
    )
    earlier_commentary = ObservedDecisionCommentaryV1(
        commentary_id="earlier-commentary",
        decision_index=1,
        subject_player_id=seat_order[0],
        commentator_player_id=seat_order[0],
        commentator_name=None,
        text="Earlier Match-position Commentary.",
        commentary_timecode=None,
    )
    earlier_game = _observed_game(
        definition,
        match_position=1,
        game_id="earlier-commented-game",
        declarer_player_id=seat_order[0],
        declaration=declaration_from_historical(
            build_historical_input(game_type="grand", hand_game=False)
        ),
        plays=earlier_plays,
        commentaries=(earlier_commentary,),
    )
    current = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(_set_game(snapshot.workspace, earlier_game))
    )
    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(snapshot, current, current=(current,))
    )
    assert tuple(item.match_position for item in collection.games) == (1, 3)
    assert tuple(item.text for item in collection.commentaries[:2]) == (
        "Earlier Match-position Commentary.",
        "Überlegt genau.\nDie Folge bleibt unverändert.",
    )


def test_current_match_and_game_order_is_canonical_not_text_or_commentator_order() -> None:
    _, second = _rich_snapshot("match-z", first_text="A text that sorts first.")
    _, first = _rich_snapshot("match-a", first_text="Z text that sorts last.")
    collection = build_learning_corpus_human_evidence_collection_v1(
        _store(second, first, current=(second, first))
    )
    assert tuple(item.match_id for item in collection.games) == (
        "match-a",
        "match-z",
    )
    assert tuple(item.text for item in collection.commentaries[::3]) == (
        "Z text that sorts last.",
        "A text that sorts first.",
    )


def test_exported_evidence_is_minimized_and_human_text_is_not_processed() -> None:
    collection, snapshot = _rich_collection()
    document = collection.to_dict()
    serialized = json.dumps(document, ensure_ascii=False)

    def collect_keys(value):
        if isinstance(value, dict):
            return set(value).union(*(collect_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value))
        return set()

    keys = collect_keys(document)
    assert {
        "perspective_initial_hand",
        "initial_hand",
        "hand",
        "hands",
        "original_skat",
        "skat",
        "discarded_cards",
        "discards",
        "plays",
        "statistics_snapshot",
        "statistics_record",
        "profile",
        "recommendation",
        "search",
        "coaching",
        "strategy_label",
        "communication_tag",
        "confidence",
        "legal_cards",
        "quality",
    }.isdisjoint(keys)
    assert collection.commentaries[0].text == ("Überlegt genau.\nDie Folge bleibt unverändert.")
    assert "Überlegt genau.\\nDie Folge bleibt unverändert." in serialized
    source_game = snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    retained_cards = {item.actual_card_played for item in collection.commentaries} | {
        item.response_card_played for item in collection.responses
    }
    unrelated_card = source_game.plays[5].card
    assert unrelated_card not in retained_cards
    scalar_strings = set()

    def collect_strings(value):
        if isinstance(value, str):
            scalar_strings.add(value)
        elif isinstance(value, dict):
            for item in value.values():
                collect_strings(item)
        elif isinstance(value, list):
            for item in value:
                collect_strings(item)

    collect_strings(document)
    assert unrelated_card not in scalar_strings


def test_values_are_frozen_slotted_builder_only_and_defensively_serialized() -> None:
    collection, _ = _rich_collection()
    values = (
        collection,
        collection.games[0],
        collection.commentaries[0],
        collection.responses[0],
    )
    assert all(not hasattr(value, "__dict__") for value in values)
    with pytest.raises(FrozenInstanceError):
        collection.commentary_count = 0
    with pytest.raises(TypeError):
        LearningCorpusHumanEvidenceCollectionV1()
    first = collection.to_dict()
    first["commentaries"][0]["text"] = "Changed"
    assert collection.to_dict()["commentaries"][0]["text"] != "Changed"


def test_commentary_contract_rejects_a_missing_commentator_identity() -> None:
    collection, _ = _rich_collection()
    source = collection.commentaries[0]
    values = {
        field.name: getattr(source, field.name)
        for field in fields(LearningCorpusCommentaryEvidenceV1)
        if field.name != "learning_corpus_commentary_evidence_version"
    }
    values.update(
        commentator_identity_kind="external",
        commentator_player_id=None,
        commentator_name=None,
    )
    with pytest.raises(ValueError, match="At least one commentator identity"):
        LearningCorpusCommentaryEvidenceV1._from_validated(**values)
