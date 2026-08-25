from __future__ import annotations

from skat_ai.learning_corpus_current_snapshots import (
    resolve_learning_corpus_current_match_snapshots_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.learning_corpus_references import (
    LearningCorpusDecisionReferenceV1,
    LearningCorpusGameReferenceV1,
)
from skat_ai.learning_corpus_tactical_motif_evidence import (
    LearningCorpusTacticalMotifEvidenceCollectionV1,
    _build_learning_corpus_skipped_tactical_motif_decision_v1,
    _build_learning_corpus_tactical_motif_collection_v1,
    _build_learning_corpus_tactical_motif_evidence_v1,
)
from skat_ai.match_decision_review_preparation import (
    _build_match_decision_states_from_reconstruction_v1,
)
from skat_ai.match_observed_reconstruction import (
    build_match_observed_game_reconstruction_v1,
)
from skat_ai.match_workspace_contracts import (
    _validate_match_workspace_with_traces_v1,
)
from skat_ai.tactical_motif_contracts import (
    TACTICAL_MOTIF_FAMILIES,
    TACTICAL_MOTIF_TYPES,
)
from skat_ai.tactical_motif_detection import (
    build_tactical_decision_observation_from_snapshot_v1,
)


def _find_game_reference(
    *,
    match_snapshot_id: str,
    game_references: tuple[LearningCorpusGameReferenceV1, ...],
    match_position: int,
    game_id: str,
) -> LearningCorpusGameReferenceV1:
    matches = tuple(
        item
        for item in game_references
        if item.match_snapshot_id == match_snapshot_id
        and item.match_position == match_position
        and item.game_id == game_id
    )
    if len(matches) != 1:
        raise ValueError("Observed Game must resolve to one exact Current Game Reference.")
    return matches[0]


def _reconcile_decision_reference(
    reference: LearningCorpusDecisionReferenceV1,
    *,
    game_reference: LearningCorpusGameReferenceV1,
    decision_index: int,
    acting_player_id: str,
) -> None:
    if (
        reference.match_snapshot_id != game_reference.match_snapshot_id
        or reference.game_reference_id != game_reference.game_reference_id
        or reference.match_id != game_reference.match_id
        or reference.game_id != game_reference.game_id
        or reference.match_position != game_reference.match_position
        or reference.decision_index != decision_index
        or reference.acting_player_id != acting_player_id
    ):
        raise ValueError("Observed Decision must reconcile with its exact reference.")


def build_learning_corpus_tactical_motif_evidence_collection_v1(
    store: LearningCorpusStoreResumeResultV1,
) -> LearningCorpusTacticalMotifEvidenceCollectionV1:
    """Builds exact Tactical coverage over explicit Current Match Snapshots."""
    current_snapshots = resolve_learning_corpus_current_match_snapshots_v1(store)
    evidences = []
    skipped_decisions = []
    observed_game_count = 0
    observed_decision_count = 0

    for match_snapshot in current_snapshots:
        workspace = match_snapshot.workspace
        validated_traces = dict(_validate_match_workspace_with_traces_v1(workspace))
        decision_references = {
            item.decision_reference_id: item for item in match_snapshot.decision_references
        }
        consumed_game_references: set[str] = set()
        consumed_decision_references: set[str] = set()
        for slot in workspace.slots:
            game = slot.observed_game
            if game is None:
                continue
            observed_game_count += 1
            game_reference = _find_game_reference(
                match_snapshot_id=match_snapshot.match_snapshot_id,
                game_references=match_snapshot.game_references,
                match_position=slot.match_position,
                game_id=game.game_id,
            )
            if game_reference.game_reference_id in consumed_game_references:
                raise ValueError("A Current Game Reference cannot be consumed twice.")
            consumed_game_references.add(game_reference.game_reference_id)
            reconstruction = build_match_observed_game_reconstruction_v1(
                game,
                validated_trace=validated_traces[slot.match_position],
            )
            snapshots, skipped, source_count = _build_match_decision_states_from_reconstruction_v1(
                reconstruction,
                source_played_at=workspace.match_definition.played_at,
            )
            if source_count != len(game.plays) or source_count != len(
                game_reference.decision_reference_ids
            ):
                raise ValueError("Observed Game Decision Counts must reconcile exactly.")
            observed_decision_count += source_count
            snapshots_by_index = {item.decision_index: item for item in snapshots}
            skipped_by_index = {item.decision_index: item for item in skipped}
            players_by_id = {item.player_id: item for item in game.players}
            participant_player_ids = tuple(item.player_id for item in game.players)
            if len(participant_player_ids) != 3 or game.declarer_player_id is None:
                if source_count:
                    raise ValueError(
                        "Observed Decisions require exactly three Players and Declarer."
                    )
            if game.declaration is None and source_count:
                raise ValueError("Observed Decisions require one exact Declaration.")

            for play, reference_id in zip(
                game.plays,
                game_reference.decision_reference_ids,
                strict=True,
            ):
                reference = decision_references.get(reference_id)
                if reference is None:
                    raise ValueError("Observed Decision Reference is missing.")
                _reconcile_decision_reference(
                    reference,
                    game_reference=game_reference,
                    decision_index=play.decision_index,
                    acting_player_id=play.player_id,
                )
                if reference_id in consumed_decision_references:
                    raise ValueError("A Current Decision Reference cannot be consumed twice.")
                consumed_decision_references.add(reference_id)
                snapshot = snapshots_by_index.get(play.decision_index)
                skipped = skipped_by_index.get(play.decision_index)
                if (snapshot is None) == (skipped is None):
                    raise ValueError(
                        "Each observed Decision must produce Evidence or a skip exactly once."
                    )
                trick_number = ((play.decision_index - 1) // 3) + 1
                play_index = ((play.decision_index - 1) % 3) + 1
                assert game.declarer_player_id is not None
                assert game.declaration is not None
                if skipped is not None:
                    player = players_by_id[play.player_id]
                    skipped_decisions.append(
                        _build_learning_corpus_skipped_tactical_motif_decision_v1(
                            match_snapshot_id=match_snapshot.match_snapshot_id,
                            workspace_revision=match_snapshot.workspace_revision,
                            game_reference_id=game_reference.game_reference_id,
                            decision_reference_id=reference.decision_reference_id,
                            match_id=reference.match_id,
                            match_position=reference.match_position,
                            game_id=reference.game_id,
                            decision_index=reference.decision_index,
                            trick_number=trick_number,
                            play_index=play_index,
                            acting_player_id=reference.acting_player_id,
                            acting_seat=player.seat,
                            acting_side=(
                                "declarer"
                                if play.player_id == game.declarer_player_id
                                else "defenders"
                            ),
                            game_type=game.declaration.game_type,
                            reason=skipped.reason,
                        )
                    )
                    continue

                assert snapshot is not None
                completed = trick_number <= reconstruction.trace.completed_trick_count
                winner_player_id = (
                    reconstruction.trace.winner_player_ids[trick_number - 1] if completed else None
                )
                observation = build_tactical_decision_observation_from_snapshot_v1(
                    snapshot=snapshot,
                    declarer_player_id=game.declarer_player_id,
                    participant_player_ids=participant_player_ids,
                    completed_trick_winner_player_id=winner_player_id,
                    completed_trick_winner_side=(
                        None
                        if winner_player_id is None
                        else "declarer"
                        if winner_player_id == game.declarer_player_id
                        else "defenders"
                    ),
                    completed_trick_points=(
                        reconstruction.trace.trick_points[trick_number - 1] if completed else None
                    ),
                )
                if observation.actual_card != play.card:
                    raise ValueError("Tactical Observation must retain the exact source Card.")
                evidences.append(
                    _build_learning_corpus_tactical_motif_evidence_v1(
                        match_snapshot_id=match_snapshot.match_snapshot_id,
                        workspace_revision=match_snapshot.workspace_revision,
                        game_reference_id=game_reference.game_reference_id,
                        decision_reference_id=reference.decision_reference_id,
                        match_id=reference.match_id,
                        match_position=reference.match_position,
                        game_id=reference.game_id,
                        decision_index=reference.decision_index,
                        acting_player_id=reference.acting_player_id,
                        actual_card_played=play.card,
                        observation=observation,
                    )
                )

        if consumed_game_references != {
            item.game_reference_id for item in match_snapshot.game_references
        }:
            raise ValueError("Every Current Game Reference must be consumed exactly once.")
        if consumed_decision_references != set(decision_references):
            raise ValueError("Every Current Decision Reference must be consumed exactly once.")

    motif_counts = tuple(
        (
            motif_type,
            sum(
                motif.motif_type == motif_type
                for evidence in evidences
                for motif in evidence.observation.motifs
            ),
        )
        for motif_type in TACTICAL_MOTIF_TYPES
    )
    family_counts = tuple(
        (
            family,
            sum(
                motif.motif_family == family
                for evidence in evidences
                for motif in evidence.observation.motifs
            ),
        )
        for family in TACTICAL_MOTIF_FAMILIES
    )
    source_catalog = store.document.catalog
    status = (
        "empty" if observed_decision_count == 0 else "partial" if skipped_decisions else "complete"
    )
    return _build_learning_corpus_tactical_motif_collection_v1(
        corpus_id=source_catalog.corpus_id,
        source_catalog_revision=source_catalog.revision,
        source_catalog_fingerprint=store.document.catalog_fingerprint,
        source_catalog_content_fingerprint=store.document.content_fingerprint,
        current_match_snapshot_ids=tuple(
            item.match_snapshot_id for item in source_catalog.current_matches
        ),
        retained_match_snapshot_count=len(store.match_snapshots),
        current_match_count=len(current_snapshots),
        orphan_match_snapshot_count=len(store.orphan_match_snapshot_ids),
        status=status,
        observed_game_count=observed_game_count,
        observed_decision_count=observed_decision_count,
        evidence_count=len(evidences),
        skipped_decision_count=len(skipped_decisions),
        complete_observation_count=sum(
            item.observation.observation_status == "complete" for item in evidences
        ),
        partial_observation_count=sum(
            item.observation.observation_status == "partial" for item in evidences
        ),
        motif_occurrence_count=sum(len(item.observation.motifs) for item in evidences),
        evidences=tuple(evidences),
        skipped_decisions=tuple(skipped_decisions),
        motif_counts=motif_counts,
        family_counts=family_counts,
    )
