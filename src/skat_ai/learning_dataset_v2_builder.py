from __future__ import annotations

from dataclasses import dataclass, field

from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshot
from skat_ai.learning_corpus_current_snapshots import (
    resolve_learning_corpus_current_match_snapshots_v1,
)
from skat_ai.learning_corpus_human_evidence import (
    LearningCorpusCommentaryEvidenceV1,
    LearningCorpusHumanEvidenceCollectionV1,
    LearningCorpusResponseEvidenceV1,
    _validate_learning_corpus_human_evidence_collection_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.learning_corpus_player_catalog import (
    LearningCorpusPlayerCatalogV1,
    _validate_learning_corpus_player_catalog_v1,
)
from skat_ai.learning_corpus_player_statistics import (
    LearningCorpusPlayerStatisticsObservationV1,
    LearningCorpusPlayerStatisticsSelectionV1,
    _select_learning_corpus_player_statistics_as_of_validated_v1,
)
from skat_ai.learning_corpus_references import (
    LearningCorpusDecisionReferenceV1,
    LearningCorpusGameReferenceV1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    LearningCorpusStrategyTeacherEvidenceV1,
    _validate_learning_corpus_strategy_teacher_collection_v1,
)
from skat_ai.learning_dataset_v2_contracts import (
    LEARNING_DATASET_RELATIVE_PLAYERS,
    LearningDatasetDecisionStateV1,
    LearningDatasetObservedBehaviorV1,
    LearningDatasetPlayerContextV1,
    LearningDatasetRecordV1,
    LearningDatasetSourceContextV1,
    LearningDatasetV2,
    _build_decision_state_v1,
    _build_learning_dataset_v2,
    _build_observed_behavior_v1,
    _build_player_context_v1,
    _build_record_v1,
    _build_skipped_decision_v1,
    _build_source_context_v1,
    _require_identifier,
)
from skat_ai.match_decision_review_preparation import (
    MatchSkippedDecisionV1,
    _build_match_decision_states_from_reconstruction_v1,
)
from skat_ai.match_observed_reconstruction import (
    build_match_observed_game_reconstruction_v1,
)
from skat_ai.match_workspace_contracts import (
    _validate_match_workspace_with_traces_v1,
)
from skat_ai.observed_game_trace import ObservedPlayV1
from skat_ai.rfc3339 import parse_rfc3339_datetime


@dataclass(slots=True)
class _RecordParts:
    source_context: LearningDatasetSourceContextV1
    decision_state: LearningDatasetDecisionStateV1
    observed_behavior: LearningDatasetObservedBehaviorV1
    player_contexts: tuple[LearningDatasetPlayerContextV1, ...]
    strategy_teacher_ids: list[str] = field(default_factory=list)
    commentary_ids: list[str] = field(default_factory=list)
    outgoing_response_ids: list[str] = field(default_factory=list)
    incoming_response_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _SkippedParts:
    reference: LearningCorpusDecisionReferenceV1
    skipped: MatchSkippedDecisionV1
    commentary_ids: list[str] = field(default_factory=list)
    outgoing_response_ids: list[str] = field(default_factory=list)
    incoming_response_ids: list[str] = field(default_factory=list)


def _source_identity(store: LearningCorpusStoreResumeResultV1) -> tuple[object, ...]:
    catalog = store.document.catalog
    return (
        catalog.corpus_id,
        catalog.revision,
        store.document.catalog_fingerprint,
        store.document.content_fingerprint,
        tuple(item.match_snapshot_id for item in catalog.current_matches),
        len(store.match_snapshots),
        len(catalog.current_matches),
        len(store.orphan_match_snapshot_ids),
    )


def _derived_source_identity(
    value: (
        LearningCorpusPlayerCatalogV1
        | LearningCorpusHumanEvidenceCollectionV1
        | LearningCorpusStrategyTeacherEvidenceCollectionV1
    ),
) -> tuple[object, ...]:
    return (
        value.corpus_id,
        value.source_catalog_revision,
        value.source_catalog_fingerprint,
        value.source_catalog_content_fingerprint,
        value.current_match_snapshot_ids,
        value.retained_match_snapshot_count,
        value.current_match_count,
        value.orphan_match_snapshot_count,
    )


def _reconcile_sources(
    store: LearningCorpusStoreResumeResultV1,
    player_catalog: LearningCorpusPlayerCatalogV1,
    human_evidence: LearningCorpusHumanEvidenceCollectionV1,
    strategy_teacher_evidence: LearningCorpusStrategyTeacherEvidenceCollectionV1,
) -> None:
    if type(store) is not LearningCorpusStoreResumeResultV1:
        raise ValueError("store must be an exact LearningCorpusStoreResumeResultV1.")
    _validate_learning_corpus_player_catalog_v1(player_catalog)
    _validate_learning_corpus_human_evidence_collection_v1(human_evidence)
    _validate_learning_corpus_strategy_teacher_collection_v1(strategy_teacher_evidence)
    expected = _source_identity(store)
    for source_name, source in (
        ("player_catalog", player_catalog),
        ("human_evidence", human_evidence),
        ("strategy_teacher_evidence", strategy_teacher_evidence),
    ):
        if _derived_source_identity(source) != expected:
            raise ValueError(f"{source_name} must match the exact Corpus Store source identity.")


def _find_game_reference(
    snapshot_id: str,
    game_references: tuple[LearningCorpusGameReferenceV1, ...],
    *,
    match_position: int,
    game_id: str,
) -> LearningCorpusGameReferenceV1:
    matches = tuple(
        item
        for item in game_references
        if item.match_snapshot_id == snapshot_id
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
        raise ValueError("Observed Decision must reconcile with its exact Decision Reference.")


def _build_source_context(
    *,
    match_snapshot_id: str,
    workspace_revision: int,
    game_reference: LearningCorpusGameReferenceV1,
    workspace,
    game,
    play: ObservedPlayV1,
) -> LearningDatasetSourceContextV1:
    definition = workspace.match_definition
    source = definition.source
    players_by_seat = {player.seat: player.player_id for player in game.players}
    if game.declarer_player_id is None:
        raise ValueError("Observed Decisions require one exact Declarer Player.")
    return _build_source_context_v1(
        match_snapshot_id=match_snapshot_id,
        game_reference_id=game_reference.game_reference_id,
        match_id=definition.match_id,
        workspace_revision=workspace_revision,
        match_position=game.match_position,
        game_id=game.game_id,
        match_title=definition.title,
        external_match_id=definition.external_match_id,
        played_at=definition.played_at,
        game_platform=definition.game_platform,
        source_kind=source.source_kind,
        source_url=source.source_url,
        source_title=source.source_title,
        source_channel_name=source.source_channel_name,
        match_timecode=source.match_timecode,
        game_timecode=game.game_timecode,
        decision_timecode=play.decision_timecode,
        perspective_player_id=game.perspective_player_id,
        forehand_player_id=players_by_seat["forehand"],
        middlehand_player_id=players_by_seat["middlehand"],
        rearhand_player_id=players_by_seat["rearhand"],
        declarer_player_id=game.declarer_player_id,
    )


def _build_player_contexts(
    snapshot: HistoricalDecisionSnapshot,
    *,
    player_catalog: LearningCorpusPlayerCatalogV1,
    selection_cache: dict[
        tuple[str, str | None],
        LearningCorpusPlayerStatisticsSelectionV1,
    ],
) -> tuple[LearningDatasetPlayerContextV1, ...]:
    contexts = []
    for relative_player in LEARNING_DATASET_RELATIVE_PLAYERS:
        player_id = snapshot.relative_player_map[relative_player]
        key = (player_id, snapshot.source_played_at)
        selection = selection_cache.get(key)
        if selection is None:
            selection = _select_learning_corpus_player_statistics_as_of_validated_v1(
                player_catalog,
                player_id=player_id,
                target_played_at=snapshot.source_played_at,
                selection_mode="latest_unambiguous",
            )
            selection_cache[key] = selection
        contexts.append(_build_player_context_v1(relative_player, selection))
    return tuple(contexts)


def _validate_behavior(
    snapshot: HistoricalDecisionSnapshot,
    play: ObservedPlayV1,
    reference: LearningCorpusDecisionReferenceV1,
) -> None:
    state = snapshot.visible_state
    current_cards = {item.card for item in state.current_trick}
    if (
        snapshot.decision_index != play.decision_index
        or snapshot.acting_player_id != play.player_id
        or snapshot.actual_card_played != play.card
        or reference.decision_reference_id == ""
        or play.card not in state.own_hand
        or play.card not in state.legal_cards
        or play.card in current_cards
    ):
        raise ValueError("Observed Behavior must be legal in its exact Decision State.")


def _referenced_statistics_ids(
    records: tuple[LearningDatasetRecordV1, ...],
) -> set[str]:
    result: set[str] = set()
    for record in records:
        for context in record.player_contexts:
            result.update(context.candidate_observation_ids)
            result.update(context.equivalent_observation_ids)
            result.update(context.ambiguous_observation_ids)
            if context.selected_statistics_observation_id is not None:
                result.add(context.selected_statistics_observation_id)
    return result


def _statistics_observation_pool(
    player_catalog: LearningCorpusPlayerCatalogV1,
    referenced_ids: set[str],
) -> tuple[LearningCorpusPlayerStatisticsObservationV1, ...]:
    observations = {
        item.statistics_observation_id: item
        for player in player_catalog.players
        for item in player.statistics_observations
    }
    if not referenced_ids <= observations.keys():
        raise ValueError("Every Player Context Statistics ID must resolve through the Catalog.")
    return tuple(
        sorted(
            (observations[item_id] for item_id in referenced_ids),
            key=lambda item: (
                item.player_id,
                parse_rfc3339_datetime(item.captured_at, "captured_at"),
                item.statistics_observation_id,
            ),
        )
    )


def _reconcile_teacher(
    evidence: LearningCorpusStrategyTeacherEvidenceV1,
    parts: _RecordParts,
) -> None:
    source = parts.source_context
    state = parts.decision_state
    behavior = parts.observed_behavior
    if (
        evidence.match_snapshot_id != source.match_snapshot_id
        or evidence.game_reference_id != source.game_reference_id
        or evidence.match_id != source.match_id
        or evidence.workspace_revision != source.workspace_revision
        or evidence.match_position != source.match_position
        or evidence.game_id != source.game_id
        or evidence.decision_index != state.decision_index
        or evidence.acting_player_id != state.acting_player_id
        or evidence.actual_card_played != behavior.actual_card_played
    ):
        raise ValueError("Strategy Teacher Evidence must reconcile with its exact Record.")


def _reconcile_commentary(
    evidence: LearningCorpusCommentaryEvidenceV1,
    parts: _RecordParts,
) -> None:
    if (
        evidence.match_snapshot_id != parts.source_context.match_snapshot_id
        or evidence.game_reference_id != parts.source_context.game_reference_id
        or evidence.subject_decision_index != parts.decision_state.decision_index
        or evidence.subject_player_id != parts.decision_state.acting_player_id
        or evidence.actual_card_played != parts.observed_behavior.actual_card_played
    ):
        raise ValueError("Commentary Evidence must reconcile with its subject Record.")


def _reconcile_response(
    response: LearningCorpusResponseEvidenceV1,
    subject: _RecordParts,
    target: _RecordParts,
) -> None:
    if (
        response.match_snapshot_id != subject.source_context.match_snapshot_id
        or response.match_snapshot_id != target.source_context.match_snapshot_id
        or response.game_reference_id != subject.source_context.game_reference_id
        or response.game_reference_id != target.source_context.game_reference_id
        or response.subject_decision_index != subject.decision_state.decision_index
        or response.response_decision_index != target.decision_state.decision_index
        or response.response_player_id != target.decision_state.acting_player_id
        or response.response_card_played != target.observed_behavior.actual_card_played
    ):
        raise ValueError("Response Evidence must reconcile with its subject and response Records.")


def build_learning_dataset_v2(
    store: LearningCorpusStoreResumeResultV1,
    player_catalog: LearningCorpusPlayerCatalogV1,
    human_evidence: LearningCorpusHumanEvidenceCollectionV1,
    strategy_teacher_evidence: LearningCorpusStrategyTeacherEvidenceCollectionV1,
    *,
    dataset_id: str,
) -> LearningDatasetV2:
    """Builds one private task-neutral Dataset from exact Current Corpus sources."""
    _require_identifier(dataset_id, "dataset_id")
    current_snapshots = resolve_learning_corpus_current_match_snapshots_v1(store)
    _reconcile_sources(store, player_catalog, human_evidence, strategy_teacher_evidence)

    record_parts: dict[str, _RecordParts] = {}
    skipped_parts: dict[str, _SkippedParts] = {}
    selection_cache: dict[
        tuple[str, str | None],
        LearningCorpusPlayerStatisticsSelectionV1,
    ] = {}
    observed_game_count = 0
    observed_decision_count = 0

    for match_snapshot in current_snapshots:
        workspace = match_snapshot.workspace
        validated_traces = dict(_validate_match_workspace_with_traces_v1(workspace))
        decision_references = {
            item.decision_reference_id: item for item in match_snapshot.decision_references
        }
        for slot in workspace.slots:
            game = slot.observed_game
            if game is None:
                continue
            observed_game_count += 1
            game_reference = _find_game_reference(
                match_snapshot.match_snapshot_id,
                match_snapshot.game_references,
                match_position=slot.match_position,
                game_id=game.game_id,
            )
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
                raise ValueError("Observed Game Decision counts must reconcile exactly.")
            observed_decision_count += source_count
            snapshots_by_index = {item.decision_index: item for item in snapshots}
            skipped_by_index = {item.decision_index: item for item in skipped}
            for play, reference_id in zip(
                game.plays,
                game_reference.decision_reference_ids,
                strict=True,
            ):
                reference = decision_references[reference_id]
                _reconcile_decision_reference(
                    reference,
                    game_reference=game_reference,
                    decision_index=play.decision_index,
                    acting_player_id=play.player_id,
                )
                snapshot = snapshots_by_index.get(play.decision_index)
                skipped_value = skipped_by_index.get(play.decision_index)
                if (snapshot is None) == (skipped_value is None):
                    raise ValueError(
                        "Each observed Decision must be prepared or skipped exactly once."
                    )
                if skipped_value is not None:
                    skipped_parts[reference_id] = _SkippedParts(
                        reference=reference,
                        skipped=skipped_value,
                    )
                    continue
                assert snapshot is not None
                _validate_behavior(snapshot, play, reference)
                source_context = _build_source_context(
                    match_snapshot_id=match_snapshot.match_snapshot_id,
                    workspace_revision=match_snapshot.workspace_revision,
                    game_reference=game_reference,
                    workspace=workspace,
                    game=game,
                    play=play,
                )
                decision_state = _build_decision_state_v1(
                    snapshot,
                    decision_reference_id=reference_id,
                )
                observed_behavior = _build_observed_behavior_v1(
                    decision_reference_id=reference_id,
                    actual_card_played=play.card,
                )
                record_parts[reference_id] = _RecordParts(
                    source_context=source_context,
                    decision_state=decision_state,
                    observed_behavior=observed_behavior,
                    player_contexts=_build_player_contexts(
                        snapshot,
                        player_catalog=player_catalog,
                        selection_cache=selection_cache,
                    ),
                )

    if observed_game_count != human_evidence.observed_game_count:
        raise ValueError("Human Evidence observed_game_count must match Current Snapshots.")
    if observed_decision_count != human_evidence.decision_count:
        raise ValueError("Human Evidence decision_count must match Current Snapshots.")

    for evidence in strategy_teacher_evidence.evidences:
        parts = record_parts.get(evidence.decision_reference_id)
        if parts is None:
            raise ValueError("Every Strategy Teacher Evidence value must join one Record.")
        _reconcile_teacher(evidence, parts)
        parts.strategy_teacher_ids.append(evidence.strategy_teacher_evidence_id)

    joined_commentary_ids: set[str] = set()
    unjoined_commentary_ids: list[str] = []
    commentaries_by_id = {
        item.commentary_evidence_id: item for item in human_evidence.commentaries
    }
    for commentary in human_evidence.commentaries:
        parts = record_parts.get(commentary.subject_decision_reference_id)
        if parts is not None:
            _reconcile_commentary(commentary, parts)
            parts.commentary_ids.append(commentary.commentary_evidence_id)
            joined_commentary_ids.add(commentary.commentary_evidence_id)
            continue
        skipped = skipped_parts.get(commentary.subject_decision_reference_id)
        if skipped is None:
            raise ValueError("Commentary Evidence must resolve to a Record or skipped Decision.")
        skipped.commentary_ids.append(commentary.commentary_evidence_id)
        unjoined_commentary_ids.append(commentary.commentary_evidence_id)

    joined_response_ids: set[str] = set()
    unjoined_response_ids: list[str] = []
    for response in human_evidence.responses:
        commentary = commentaries_by_id.get(response.commentary_evidence_id)
        if commentary is None:
            raise ValueError("Response Evidence must resolve to exact Commentary Evidence.")
        subject = record_parts.get(response.subject_decision_reference_id)
        target = record_parts.get(response.response_decision_reference_id)
        joinable = (
            response.commentary_evidence_id in joined_commentary_ids
            and subject is not None
            and target is not None
        )
        if joinable:
            assert subject is not None and target is not None
            _reconcile_response(response, subject, target)
            subject.outgoing_response_ids.append(response.response_evidence_id)
            target.incoming_response_ids.append(response.response_evidence_id)
            joined_response_ids.add(response.response_evidence_id)
            continue
        unjoined_response_ids.append(response.response_evidence_id)
        skipped_subject = skipped_parts.get(response.subject_decision_reference_id)
        skipped_target = skipped_parts.get(response.response_decision_reference_id)
        if skipped_subject is not None:
            skipped_subject.outgoing_response_ids.append(response.response_evidence_id)
        if skipped_target is not None:
            skipped_target.incoming_response_ids.append(response.response_evidence_id)

    records = tuple(
        sorted(
            (
                _build_record_v1(
                    source_context=parts.source_context,
                    decision_state=parts.decision_state,
                    observed_behavior=parts.observed_behavior,
                    player_contexts=parts.player_contexts,
                    evidence_families_present=(
                        "observed_behavior",
                        "player_context",
                        *(("strategy_teacher",) if parts.strategy_teacher_ids else ()),
                        *(("human_commentary",) if parts.commentary_ids else ()),
                        *(
                            ("linked_response",)
                            if parts.outgoing_response_ids or parts.incoming_response_ids
                            else ()
                        ),
                    ),
                    strategy_teacher_evidence_ids=tuple(parts.strategy_teacher_ids),
                    commentary_evidence_ids=tuple(parts.commentary_ids),
                    outgoing_response_evidence_ids=tuple(parts.outgoing_response_ids),
                    incoming_response_evidence_ids=tuple(parts.incoming_response_ids),
                )
                for parts in record_parts.values()
            ),
            key=lambda item: (
                item.source_context.match_id,
                item.source_context.match_position,
                item.decision_state.decision_index,
                item.record_id,
            ),
        )
    )
    skipped_decisions = tuple(
        sorted(
            (
                _build_skipped_decision_v1(
                    match_snapshot_id=parts.reference.match_snapshot_id,
                    game_reference_id=parts.reference.game_reference_id,
                    decision_reference_id=parts.reference.decision_reference_id,
                    match_id=parts.reference.match_id,
                    match_position=parts.reference.match_position,
                    game_id=parts.reference.game_id,
                    decision_index=parts.reference.decision_index,
                    acting_player_id=parts.reference.acting_player_id,
                    reason=parts.skipped.reason,
                    commentary_evidence_ids=tuple(parts.commentary_ids),
                    outgoing_response_evidence_ids=tuple(parts.outgoing_response_ids),
                    incoming_response_evidence_ids=tuple(parts.incoming_response_ids),
                )
                for parts in skipped_parts.values()
            ),
            key=lambda item: (
                item.match_id,
                item.match_position,
                item.decision_index,
                item.skipped_decision_id,
            ),
        )
    )
    statistics_observations = _statistics_observation_pool(
        player_catalog,
        _referenced_statistics_ids(records),
    )
    commentary_evidences = tuple(
        item
        for item in human_evidence.commentaries
        if item.commentary_evidence_id in joined_commentary_ids
    )
    response_evidences = tuple(
        item
        for item in human_evidence.responses
        if item.response_evidence_id in joined_response_ids
    )
    source_catalog = store.document.catalog
    status = (
        "empty"
        if observed_decision_count == 0
        else "unavailable"
        if not records
        else "partial"
        if skipped_decisions
        else "complete"
    )
    return _build_learning_dataset_v2(
        dataset_id=dataset_id,
        status=status,
        corpus_id=source_catalog.corpus_id,
        source_catalog_revision=source_catalog.revision,
        source_catalog_fingerprint=store.document.catalog_fingerprint,
        source_catalog_content_fingerprint=store.document.content_fingerprint,
        current_match_snapshot_ids=tuple(
            item.match_snapshot_id for item in source_catalog.current_matches
        ),
        player_catalog_fingerprint=player_catalog.player_catalog_fingerprint,
        human_evidence_collection_fingerprint=(
            human_evidence.human_evidence_collection_fingerprint
        ),
        strategy_teacher_collection_fingerprint=(
            strategy_teacher_evidence.strategy_teacher_collection_fingerprint
        ),
        retained_match_snapshot_count=len(store.match_snapshots),
        current_match_count=len(current_snapshots),
        orphan_match_snapshot_count=len(store.orphan_match_snapshot_ids),
        observed_game_count=observed_game_count,
        observed_decision_count=observed_decision_count,
        record_count=len(records),
        skipped_decision_count=len(skipped_decisions),
        selected_statistics_context_count=sum(
            context.selected_statistics_observation_id is not None
            for record in records
            for context in record.player_contexts
        ),
        statistics_observation_count=len(statistics_observations),
        strategy_teacher_evidence_count=len(strategy_teacher_evidence.evidences),
        commentary_evidence_count=len(commentary_evidences),
        response_evidence_count=len(response_evidences),
        records_with_strategy_teacher_count=sum(
            bool(item.strategy_teacher_evidence_ids) for item in records
        ),
        records_with_commentary_count=sum(bool(item.commentary_evidence_ids) for item in records),
        records_with_outgoing_response_count=sum(
            bool(item.outgoing_response_evidence_ids) for item in records
        ),
        records_with_incoming_response_count=sum(
            bool(item.incoming_response_evidence_ids) for item in records
        ),
        unjoined_commentary_evidence_count=len(unjoined_commentary_ids),
        unjoined_response_evidence_count=len(unjoined_response_ids),
        records=records,
        skipped_decisions=skipped_decisions,
        player_statistics_observations=statistics_observations,
        strategy_teacher_evidences=strategy_teacher_evidence.evidences,
        commentary_evidences=commentary_evidences,
        response_evidences=response_evidences,
        unjoined_commentary_evidence_ids=tuple(unjoined_commentary_ids),
        unjoined_response_evidence_ids=tuple(unjoined_response_ids),
    )
