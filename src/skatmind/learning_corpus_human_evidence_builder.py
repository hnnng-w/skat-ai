from __future__ import annotations

from typing import Any

from skatmind.learning_corpus_current_snapshots import (
    resolve_learning_corpus_current_match_snapshots_v1,
)
from skatmind.learning_corpus_human_evidence import (
    LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS,
    LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION,
    LearningCorpusCommentaryEvidenceV1,
    LearningCorpusHumanEvidenceCollectionV1,
    LearningCorpusHumanEvidenceGameV1,
    LearningCorpusResponseEvidenceV1,
    _build_collection_fingerprint_v1,
    _build_commentary_evidence_id_v1,
    _build_game_evidence_id_v1,
    _build_response_evidence_id_v1,
    build_learning_corpus_commentary_content_fingerprint_v1,
    build_learning_corpus_response_content_fingerprint_v1,
)
from skatmind.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)


def _commentator_identity_kind(
    *,
    player_id: str | None,
    commentator_name: str | None,
) -> str:
    if player_id is not None and commentator_name is not None:
        return LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS[2]
    if player_id is not None:
        return LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS[0]
    return LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS[1]


def _role(player_id: str, declarer_player_id: str) -> str:
    return "declarer" if player_id == declarer_player_id else "defender"


def _collection_material(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "learning_corpus_human_evidence_version": (LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION),
        **{
            key: (
                [item.to_dict() for item in value]
                if key in {"games", "commentaries", "responses"}
                else list(value)
                if key == "current_match_snapshot_ids"
                else value
            )
            for key, value in values.items()
        },
    }


def build_learning_corpus_human_evidence_collection_v1(
    store: LearningCorpusStoreResumeResultV1,
) -> LearningCorpusHumanEvidenceCollectionV1:
    """Builds minimized Human Evidence from explicit Current Match Snapshots."""
    current_snapshots = resolve_learning_corpus_current_match_snapshots_v1(store)
    source_document = store.document
    source_catalog = source_document.catalog

    games: list[LearningCorpusHumanEvidenceGameV1] = []
    commentaries: list[LearningCorpusCommentaryEvidenceV1] = []
    responses: list[LearningCorpusResponseEvidenceV1] = []
    current_observed_game_count = 0
    current_observed_decision_count = 0

    for snapshot in current_snapshots:
        workspace = snapshot.workspace
        definition = workspace.match_definition
        if snapshot.match_id != definition.match_id:
            raise ValueError("Current Snapshot Match identity must reconcile.")
        participant_labels = {
            participant.player_id: participant.player_label
            for participant in definition.participants
        }
        game_references_by_position = {
            reference.match_position: reference for reference in snapshot.game_references
        }
        decisions_by_id = {
            reference.decision_reference_id: reference for reference in snapshot.decision_references
        }
        commentaries_by_id = {
            reference.commentary_reference_id: reference
            for reference in snapshot.commentary_references
        }
        responses_by_id = {
            reference.response_reference_id: reference for reference in snapshot.response_references
        }
        consumed_game_reference_ids: set[str] = set()
        consumed_decision_reference_ids: set[str] = set()
        consumed_commentary_reference_ids: set[str] = set()
        consumed_response_reference_ids: set[str] = set()

        for slot in workspace.slots:
            game = slot.observed_game
            if game is None:
                continue
            current_observed_game_count += 1
            current_observed_decision_count += len(game.plays)
            game_reference = game_references_by_position.get(slot.match_position)
            if (
                game_reference is None
                or game_reference.match_snapshot_id != snapshot.match_snapshot_id
                or game_reference.match_id != snapshot.match_id
                or game_reference.game_id != game.game_id
                or game_reference.match_position != game.match_position
            ):
                raise ValueError("Observed Game must reconcile with its Corpus Reference.")
            consumed_game_reference_ids.add(game_reference.game_reference_id)

            if len(game_reference.decision_reference_ids) != len(game.plays):
                raise ValueError("Observed Game Decision References must reconcile.")
            plays_by_index = {}
            decision_references_by_index = {}
            for play, decision_reference_id in zip(
                game.plays,
                game_reference.decision_reference_ids,
                strict=True,
            ):
                decision_reference = decisions_by_id.get(decision_reference_id)
                if (
                    decision_reference is None
                    or decision_reference.game_reference_id != game_reference.game_reference_id
                    or decision_reference.decision_index != play.decision_index
                    or decision_reference.acting_player_id != play.player_id
                ):
                    raise ValueError("Observed Play must reconcile with its Decision Reference.")
                if play.decision_index in plays_by_index:
                    raise ValueError("Observed Decision indexes must be unique.")
                plays_by_index[play.decision_index] = play
                decision_references_by_index[play.decision_index] = decision_reference
                consumed_decision_reference_ids.add(decision_reference_id)

            if len(game_reference.commentary_reference_ids) != len(game.commentaries):
                raise ValueError("Observed Commentary References must reconcile.")
            source_commentaries = []
            commentary_by_source_id = {}
            for source_commentary, commentary_reference_id in zip(
                game.commentaries,
                game_reference.commentary_reference_ids,
                strict=True,
            ):
                commentary_reference = commentaries_by_id.get(commentary_reference_id)
                subject_reference = decision_references_by_index.get(
                    source_commentary.decision_index
                )
                if (
                    commentary_reference is None
                    or subject_reference is None
                    or commentary_reference.game_reference_id != game_reference.game_reference_id
                    or commentary_reference.commentary_id != source_commentary.commentary_id
                    or commentary_reference.subject_decision_reference_id
                    != subject_reference.decision_reference_id
                ):
                    raise ValueError(
                        "Observed Commentary must reconcile with its closed References."
                    )
                source_commentaries.append(
                    (source_commentary, commentary_reference, subject_reference)
                )
                commentary_by_source_id[source_commentary.commentary_id] = commentary_reference
                consumed_commentary_reference_ids.add(commentary_reference_id)

            if len(game_reference.response_reference_ids) != len(game.response_links):
                raise ValueError("Observed Response References must reconcile.")
            source_responses = []
            for source_response, response_reference_id in zip(
                game.response_links,
                game_reference.response_reference_ids,
                strict=True,
            ):
                response_reference = responses_by_id.get(response_reference_id)
                commentary_reference = commentary_by_source_id.get(source_response.commentary_id)
                response_decision_reference = decision_references_by_index.get(
                    source_response.response_decision_index
                )
                if (
                    response_reference is None
                    or commentary_reference is None
                    or response_decision_reference is None
                    or response_reference.game_reference_id != game_reference.game_reference_id
                    or response_reference.link_id != source_response.link_id
                    or response_reference.commentary_reference_id
                    != commentary_reference.commentary_reference_id
                    or response_reference.response_decision_reference_id
                    != response_decision_reference.decision_reference_id
                ):
                    raise ValueError("Observed Response must reconcile with its closed References.")
                source_responses.append(
                    (
                        source_response,
                        response_reference,
                        commentary_reference,
                        response_decision_reference,
                    )
                )
                consumed_response_reference_ids.add(response_reference_id)

            if not source_commentaries:
                continue
            if game.declarer_player_id is None:
                raise ValueError("Commented Games require an exact Declarer.")
            game_evidence_id = _build_game_evidence_id_v1(
                match_snapshot_id=snapshot.match_snapshot_id,
                game_reference_id=game_reference.game_reference_id,
                game_content_fingerprint=game_reference.game_content_fingerprint,
            )
            seats_by_player_id = {player.player_id: player.seat for player in game.players}

            commentary_values = []
            commentary_evidence_by_reference_id = {}
            for source_commentary, commentary_reference, subject_reference in source_commentaries:
                subject_play = plays_by_index[source_commentary.decision_index]
                content_fingerprint = build_learning_corpus_commentary_content_fingerprint_v1(
                    source_commentary
                )
                evidence_id = _build_commentary_evidence_id_v1(
                    commentary_content_fingerprint=content_fingerprint,
                    commentary_reference_id=(commentary_reference.commentary_reference_id),
                    game_evidence_id=game_evidence_id,
                )
                values = {
                    "commentary_evidence_id": evidence_id,
                    "commentary_content_fingerprint": content_fingerprint,
                    "commentary_reference_id": (commentary_reference.commentary_reference_id),
                    "game_evidence_id": game_evidence_id,
                    "match_snapshot_id": snapshot.match_snapshot_id,
                    "game_reference_id": game_reference.game_reference_id,
                    "commentary_id": source_commentary.commentary_id,
                    "subject_decision_reference_id": (subject_reference.decision_reference_id),
                    "subject_decision_index": subject_play.decision_index,
                    "subject_trick_number": ((subject_play.decision_index - 1) // 3) + 1,
                    "subject_play_index": ((subject_play.decision_index - 1) % 3) + 1,
                    "subject_player_id": subject_play.player_id,
                    "subject_player_label": participant_labels[subject_play.player_id],
                    "subject_seat": seats_by_player_id[subject_play.player_id],
                    "subject_role": _role(
                        subject_play.player_id,
                        game.declarer_player_id,
                    ),
                    "actual_card_played": subject_play.card,
                    "decision_timecode": subject_play.decision_timecode,
                    "commentary_timecode": source_commentary.commentary_timecode,
                    "commentator_identity_kind": _commentator_identity_kind(
                        player_id=source_commentary.commentator_player_id,
                        commentator_name=source_commentary.commentator_name,
                    ),
                    "commentator_player_id": source_commentary.commentator_player_id,
                    "commentator_name": source_commentary.commentator_name,
                    "text": source_commentary.text,
                }
                commentary_values.append(values)
                commentary_evidence_by_reference_id[
                    commentary_reference.commentary_reference_id
                ] = values

            game_responses: list[LearningCorpusResponseEvidenceV1] = []
            response_ids_by_commentary: dict[str, list[str]] = {
                values["commentary_evidence_id"]: [] for values in commentary_values
            }
            for (
                source_response,
                response_reference,
                commentary_reference,
                response_decision_reference,
            ) in source_responses:
                source_commentary_values = commentary_evidence_by_reference_id[
                    commentary_reference.commentary_reference_id
                ]
                response_play = plays_by_index[source_response.response_decision_index]
                content_fingerprint = build_learning_corpus_response_content_fingerprint_v1(
                    source_response
                )
                evidence_id = _build_response_evidence_id_v1(
                    response_content_fingerprint=content_fingerprint,
                    response_reference_id=response_reference.response_reference_id,
                    game_evidence_id=game_evidence_id,
                )
                response_trick_number = ((response_play.decision_index - 1) // 3) + 1
                game_responses.append(
                    LearningCorpusResponseEvidenceV1._from_validated(
                        response_evidence_id=evidence_id,
                        response_content_fingerprint=content_fingerprint,
                        response_reference_id=response_reference.response_reference_id,
                        game_evidence_id=game_evidence_id,
                        match_snapshot_id=snapshot.match_snapshot_id,
                        game_reference_id=game_reference.game_reference_id,
                        link_id=source_response.link_id,
                        commentary_evidence_id=source_commentary_values["commentary_evidence_id"],
                        commentary_reference_id=(commentary_reference.commentary_reference_id),
                        subject_decision_reference_id=source_commentary_values[
                            "subject_decision_reference_id"
                        ],
                        subject_decision_index=source_commentary_values["subject_decision_index"],
                        response_decision_reference_id=(
                            response_decision_reference.decision_reference_id
                        ),
                        response_decision_index=response_play.decision_index,
                        response_trick_number=response_trick_number,
                        response_play_index=((response_play.decision_index - 1) % 3) + 1,
                        response_player_id=response_play.player_id,
                        response_player_label=participant_labels[response_play.player_id],
                        response_seat=seats_by_player_id[response_play.player_id],
                        response_role=_role(
                            response_play.player_id,
                            game.declarer_player_id,
                        ),
                        response_card_played=response_play.card,
                        response_decision_timecode=response_play.decision_timecode,
                        decision_offset=(
                            response_play.decision_index
                            - source_commentary_values["subject_decision_index"]
                        ),
                        same_trick=(
                            response_trick_number
                            == source_commentary_values["subject_trick_number"]
                        ),
                    )
                )
                response_ids_by_commentary[
                    source_commentary_values["commentary_evidence_id"]
                ].append(evidence_id)

            game_commentaries = tuple(
                LearningCorpusCommentaryEvidenceV1._from_validated(
                    **values,
                    response_evidence_ids=tuple(
                        response_ids_by_commentary[values["commentary_evidence_id"]]
                    ),
                )
                for values in commentary_values
            )
            source = definition.source
            players_by_seat = {player.seat: player.player_id for player in game.players}
            game_evidence = LearningCorpusHumanEvidenceGameV1._from_validated(
                game_evidence_id=game_evidence_id,
                match_snapshot_id=snapshot.match_snapshot_id,
                game_reference_id=game_reference.game_reference_id,
                game_content_fingerprint=game_reference.game_content_fingerprint,
                match_id=snapshot.match_id,
                game_id=game.game_id,
                workspace_revision=snapshot.workspace_revision,
                match_position=game.match_position,
                match_title=definition.title,
                game_platform=definition.game_platform,
                external_match_id=definition.external_match_id,
                played_at=definition.played_at,
                source_kind=source.source_kind,
                source_url=source.source_url,
                source_title=source.source_title,
                source_channel_name=source.source_channel_name,
                match_timecode=source.match_timecode,
                game_timecode=game.game_timecode,
                perspective_player_id=game.perspective_player_id,
                forehand_player_id=players_by_seat["forehand"],
                middlehand_player_id=players_by_seat["middlehand"],
                rearhand_player_id=players_by_seat["rearhand"],
                declarer_player_id=game.declarer_player_id,
                declaration=game.declaration,
                decision_count=len(game.plays),
                commentary_evidence_ids=tuple(
                    item.commentary_evidence_id for item in game_commentaries
                ),
                response_evidence_ids=tuple(item.response_evidence_id for item in game_responses),
            )
            games.append(game_evidence)
            commentaries.extend(game_commentaries)
            responses.extend(game_responses)

        if consumed_game_reference_ids != set(
            reference.game_reference_id for reference in snapshot.game_references
        ):
            raise ValueError("Current observed Games must consume every Game Reference.")
        if consumed_decision_reference_ids != set(decisions_by_id):
            raise ValueError("Current observed Games must consume every Decision Reference.")
        if consumed_commentary_reference_ids != set(commentaries_by_id):
            raise ValueError("Current observed Games must consume every Commentary Reference.")
        if consumed_response_reference_ids != set(responses_by_id):
            raise ValueError("Current observed Games must consume every Response Reference.")

    current_snapshot_ids = tuple(
        selection.match_snapshot_id for selection in source_catalog.current_matches
    )
    collection_values = {
        "corpus_id": source_catalog.corpus_id,
        "source_catalog_revision": source_catalog.revision,
        "source_catalog_fingerprint": source_document.catalog_fingerprint,
        "source_catalog_content_fingerprint": source_document.content_fingerprint,
        "current_match_snapshot_ids": current_snapshot_ids,
        "retained_match_snapshot_count": len(store.match_snapshots),
        "current_match_count": len(current_snapshots),
        "orphan_match_snapshot_count": len(store.orphan_match_snapshot_ids),
        "observed_game_count": current_observed_game_count,
        "evidence_game_count": len(games),
        "decision_count": current_observed_decision_count,
        "commented_decision_count": len(
            {item.subject_decision_reference_id for item in commentaries}
        ),
        "commentary_count": len(commentaries),
        "response_count": len(responses),
        "games": tuple(games),
        "commentaries": tuple(commentaries),
        "responses": tuple(responses),
    }
    return LearningCorpusHumanEvidenceCollectionV1._from_validated(
        human_evidence_collection_fingerprint=_build_collection_fingerprint_v1(
            _collection_material(collection_values)
        ),
        **collection_values,
    )
