from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from skatmind.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
    build_fixed_three_player_list_seat_assignment,
)
from skatmind.learning_corpus_human_evidence import (
    LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS,
    LearningCorpusCommentaryEvidenceV1,
    LearningCorpusResponseEvidenceV1,
)
from skatmind.learning_corpus_player_catalog import (
    LearningCorpusPlayerCatalogEntryV1,
    LearningCorpusPlayerCatalogV1,
    _validate_learning_corpus_player_catalog_v1,
)
from skatmind.learning_corpus_strategy_teacher import (
    LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES,
    LearningCorpusStrategyTeacherEvidenceV1,
)
from skatmind.learning_dataset_v2_contracts import (
    LearningDatasetRecordV1,
    LearningDatasetSkippedDecisionV1,
    LearningDatasetV2,
    _validate_learning_dataset_v2,
)
from skatmind.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_PARTITION_MODES,
    LEARNING_DATASET_PARTITION_PLAN_STATUSES,
    LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
    LearningDatasetPartitionedViewV1,
    LearningDatasetPartitionPlanV1,
    LearningDatasetPartitionPreparationResultV1,
)
from skatmind.learning_dataset_v2_partition_preparation import (
    _build_learning_dataset_partition_preparation_request_from_validated_sources_v1,
    _reconcile_partition_sources,
)
from skatmind.learning_dataset_v2_summary_contracts import (
    LEARNING_DATASET_COMMUNICATION_SUMMARY_VERSION,
    LEARNING_DATASET_CROSS_GAME_SUMMARY_VERSION,
    LEARNING_DATASET_MATCH_SUMMARY_VERSION,
    LEARNING_DATASET_PARTITION_READINESS_VERSION,
    LEARNING_DATASET_PLAYER_SUMMARY_VERSION,
    LEARNING_DATASET_READINESS_SUMMARY_VERSION,
    LEARNING_DATASET_STRATEGY_SUMMARY_VERSION,
    LEARNING_DATASET_SUMMARY_ACTING_SIDES,
    LEARNING_DATASET_SUMMARY_CARDS,
    LEARNING_DATASET_SUMMARY_EFFECTIVE_METHODS,
    LEARNING_DATASET_SUMMARY_GAME_TYPES,
    LEARNING_DATASET_SUMMARY_HUMAN_ROLES,
    LEARNING_DATASET_SUMMARY_PLAYER_CONTEXT_UNAVAILABLE_REASONS,
    LEARNING_DATASET_SUMMARY_SEATS,
    LearningDatasetCrossGameSummaryV1,
    LearningDatasetSummaryCategoricalCountV1,
    LearningDatasetSummaryIntegerCountV1,
    _build_communication_summary_v1,
    _build_cross_game_summary_v1,
    _build_match_summary_v1,
    _build_partition_readiness_v1,
    _build_player_summary_v1,
    _build_readiness_summary_v1,
    _build_strategy_summary_v1,
    build_learning_dataset_summary_coverage_v1,
)
from skatmind.match_decision_review_preparation import (
    MATCH_DECISION_REVIEW_SKIP_REASONS,
)
from skatmind.recommendation_workflow import FLAT_RECOMMENDATION_METHODS


@dataclass(slots=True)
class _BehaviorAggregate:
    game_types: Counter[str] = field(default_factory=Counter)
    acting_sides: Counter[str] = field(default_factory=Counter)
    acting_seats: Counter[str] = field(default_factory=Counter)
    trick_numbers: Counter[int] = field(default_factory=Counter)
    play_indexes: Counter[int] = field(default_factory=Counter)
    forced_choice_record_count: int = 0
    choice_record_count: int = 0


@dataclass(slots=True)
class _MatchAggregate:
    match_snapshot_id: str
    match_id: str
    played_at: str | None
    player_ids: tuple[str, ...]
    perspective_player_id: str
    behavior: _BehaviorAggregate = field(default_factory=_BehaviorAggregate)
    observed_game_reference_ids: set[str] = field(default_factory=set)
    record_count: int = 0
    skipped_decision_count: int = 0
    player_context_available_count: int = 0
    player_context_unavailable_count: int = 0
    strategy_teacher_evidence_count: int = 0
    commentary_evidence_count: int = 0
    response_evidence_count: int = 0
    records_with_strategy_teacher_count: int = 0
    records_with_commentary_count: int = 0
    records_with_linked_response_count: int = 0
    unjoined_commentary_evidence_ids: set[str] = field(default_factory=set)
    unjoined_response_evidence_ids: set[str] = field(default_factory=set)


@dataclass(slots=True)
class _PlayerAggregate:
    entry: LearningCorpusPlayerCatalogEntryV1
    perspective_match_count: int = 0
    behavior: _BehaviorAggregate = field(default_factory=_BehaviorAggregate)
    actual_cards: Counter[str] = field(default_factory=Counter)
    record_count: int = 0
    skipped_decision_count: int = 0
    player_context_reference_count: int = 0
    player_context_available_count: int = 0
    player_context_unavailable_count: int = 0
    player_context_unavailable_reasons: Counter[str] = field(default_factory=Counter)
    strategy_teacher_evidence_count: int = 0
    teacher_decision_reference_ids: set[str] = field(default_factory=set)
    recommendation_available_count: int = 0
    recommendation_unavailable_count: int = 0
    teacher_actual_card_match_count: int = 0
    teacher_actual_card_difference_count: int = 0
    commentary_subject_count: int = 0
    commented_decision_reference_ids: set[str] = field(default_factory=set)
    commentary_authored_count: int = 0
    outgoing_response_count: int = 0
    incoming_response_count: int = 0
    same_trick_response_count: int = 0
    later_trick_response_count: int = 0


@dataclass(slots=True)
class _CommunicationAggregate:
    commentary_count: int = 0
    commented_decision_reference_ids: set[str] = field(default_factory=set)
    commentator_identity_kinds: Counter[str] = field(default_factory=Counter)
    commentary_on_perspective_player_count: int = 0
    commentary_ids_with_response: set[str] = field(default_factory=set)
    response_count: int = 0
    same_trick_response_count: int = 0
    later_trick_response_count: int = 0
    decision_offsets: Counter[int] = field(default_factory=Counter)
    subject_roles: Counter[str] = field(default_factory=Counter)
    response_roles: Counter[str] = field(default_factory=Counter)
    subject_seats: Counter[str] = field(default_factory=Counter)
    response_seats: Counter[str] = field(default_factory=Counter)
    subject_response_role_pairs: Counter[str] = field(default_factory=Counter)
    subject_response_seat_pairs: Counter[str] = field(default_factory=Counter)


@dataclass(slots=True)
class _StrategyAggregate:
    evidence_count: int = 0
    decision_counts: Counter[str] = field(default_factory=Counter)
    semantic_counts: Counter[str] = field(default_factory=Counter)
    recommendation_available_count: int = 0
    recommendation_unavailable_count: int = 0
    requested_methods: Counter[str] = field(default_factory=Counter)
    effective_methods: Counter[str] = field(default_factory=Counter)
    search_statuses: Counter[str] = field(default_factory=Counter)
    fallback_count: int = 0
    profile_presets_enabled_count: int = 0
    profile_application_summary_count: int = 0
    actual_card_match_evidence_count: int = 0
    actual_card_difference_evidence_count: int = 0
    actual_card_comparison_unavailable_count: int = 0


@dataclass(slots=True)
class _ReadinessAggregate:
    skipped_reasons: Counter[str] = field(default_factory=Counter)
    player_context_total_count: int = 0
    player_context_available_count: int = 0
    player_context_unavailable_count: int = 0
    player_context_unavailable_reasons: Counter[str] = field(default_factory=Counter)
    records_with_linked_response_count: int = 0


@dataclass(slots=True)
class _SummaryIndexes:
    records_by_id: dict[str, LearningDatasetRecordV1]
    records_by_decision: dict[str, LearningDatasetRecordV1]
    records_by_snapshot: dict[str, list[LearningDatasetRecordV1]]
    skipped_by_snapshot: dict[str, list[LearningDatasetSkippedDecisionV1]]
    teachers_by_id: dict[str, LearningCorpusStrategyTeacherEvidenceV1]
    teachers_by_decision: dict[str, list[LearningCorpusStrategyTeacherEvidenceV1]]
    commentaries_by_id: dict[str, LearningCorpusCommentaryEvidenceV1]
    commentaries_by_decision: dict[str, list[LearningCorpusCommentaryEvidenceV1]]
    responses_by_id: dict[str, LearningCorpusResponseEvidenceV1]
    responses_by_subject_decision: dict[str, list[LearningCorpusResponseEvidenceV1]]
    responses_by_response_decision: dict[str, list[LearningCorpusResponseEvidenceV1]]
    player_entries_by_id: dict[str, LearningCorpusPlayerCatalogEntryV1]
    match_aggregates: dict[str, _MatchAggregate]
    player_aggregates: dict[str, _PlayerAggregate]
    communication: _CommunicationAggregate
    strategy: _StrategyAggregate
    readiness: _ReadinessAggregate


def _append(mapping: dict[str, list[Any]], key: str, value: Any) -> None:
    mapping.setdefault(key, []).append(value)


def _traverse_source_once(values: tuple[Any, ...]):
    return iter(values)


def _match_facts(observations: list[Any]) -> tuple[str, str | None, tuple[str, ...], str]:
    if len(observations) != 3:
        raise ValueError("Every Current Match Summary requires exactly three Player observations.")
    by_place = {item.table_place: item for item in observations}
    if tuple(sorted(by_place, key=FIXED_THREE_PLAYER_LIST_TABLE_PLACES.index)) != (
        FIXED_THREE_PLAYER_LIST_TABLE_PLACES
    ):
        raise ValueError("Match Player observations must use exact table-place identities.")
    ordered = tuple(by_place[place] for place in FIXED_THREE_PLAYER_LIST_TABLE_PLACES)
    match_ids = {item.match_id for item in ordered}
    played_times = {item.played_at for item in ordered}
    perspectives = tuple(item.player_id for item in ordered if item.perspective_player)
    if len(match_ids) != 1 or len(played_times) != 1 or len(perspectives) != 1:
        raise ValueError("Match Player observations must reconcile exact Match facts.")
    return (
        match_ids.pop(),
        played_times.pop(),
        tuple(item.player_id for item in ordered),
        perspectives[0],
    )


def _add_behavior_record(
    aggregates: tuple[_BehaviorAggregate, ...],
    record: LearningDatasetRecordV1,
) -> None:
    state = record.decision_state
    game_type = _record_game_type(record)
    legal_card_count = _record_legal_card_count(record)
    for aggregate in aggregates:
        aggregate.game_types[game_type] += 1
        aggregate.acting_sides[state.acting_side] += 1
        aggregate.acting_seats[state.acting_seat] += 1
        aggregate.trick_numbers[state.trick_number] += 1
        aggregate.play_indexes[state.play_index] += 1
        if legal_card_count == 1:
            aggregate.forced_choice_record_count += 1
        else:
            aggregate.choice_record_count += 1


def _teacher_card_comparison(
    teacher: LearningCorpusStrategyTeacherEvidenceV1,
) -> str:
    recommendation = teacher.recommendation.get("card")
    if recommendation is None:
        return "unavailable"
    if recommendation == teacher.actual_card_played:
        return "match"
    return "difference"


def _build_indexes(
    dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
) -> _SummaryIndexes:
    player_entries_by_id = {}
    player_aggregates = {}
    match_observations_by_snapshot: dict[str, list[Any]] = {}
    for entry in _traverse_source_once(player_catalog.players):
        player_entries_by_id[entry.player_id] = entry
        player_aggregates[entry.player_id] = _PlayerAggregate(entry=entry)
        for observation in entry.match_observations:
            player_aggregates[
                entry.player_id
            ].perspective_match_count += observation.perspective_player
            _append(
                match_observations_by_snapshot,
                observation.match_snapshot_id,
                observation,
            )

    match_aggregates = {}
    for snapshot_id in dataset.current_match_snapshot_ids:
        match_id, played_at, player_ids, perspective_player_id = _match_facts(
            match_observations_by_snapshot.get(snapshot_id, [])
        )
        match_aggregates[snapshot_id] = _MatchAggregate(
            match_snapshot_id=snapshot_id,
            match_id=match_id,
            played_at=played_at,
            player_ids=player_ids,
            perspective_player_id=perspective_player_id,
        )

    records_by_id: dict[str, LearningDatasetRecordV1] = {}
    records_by_decision: dict[str, LearningDatasetRecordV1] = {}
    records_by_snapshot: dict[str, list[LearningDatasetRecordV1]] = {}
    readiness = _ReadinessAggregate()
    for record in _traverse_source_once(dataset.records):
        records_by_id[record.record_id] = record
        records_by_decision[record.decision_state.decision_reference_id] = record
        _append(records_by_snapshot, record.source_context.match_snapshot_id, record)
        match = match_aggregates[record.source_context.match_snapshot_id]
        player = player_aggregates[record.decision_state.acting_player_id]
        source = record.source_context
        seat_assignment = build_fixed_three_player_list_seat_assignment(
            source.match_position,
            dict(zip(FIXED_THREE_PLAYER_LIST_TABLE_PLACES, match.player_ids, strict=True)),
        )
        if (
            source.match_id != match.match_id
            or source.played_at != match.played_at
            or source.perspective_player_id != match.perspective_player_id
            or (
                source.forehand_player_id,
                source.middlehand_player_id,
                source.rearhand_player_id,
            )
            != (
                seat_assignment.forehand_player_id,
                seat_assignment.middlehand_player_id,
                seat_assignment.rearhand_player_id,
            )
        ):
            raise ValueError("Dataset Record and Player Catalog Match facts must reconcile.")
        match.record_count += 1
        match.observed_game_reference_ids.add(source.game_reference_id)
        _add_behavior_record((match.behavior, player.behavior), record)
        player.record_count += 1
        player.actual_cards[record.observed_behavior.actual_card_played] += 1
        if record.strategy_teacher_evidence_ids:
            match.records_with_strategy_teacher_count += 1
        if record.commentary_evidence_ids:
            match.records_with_commentary_count += 1
        if record.outgoing_response_evidence_ids or record.incoming_response_evidence_ids:
            match.records_with_linked_response_count += 1
            readiness.records_with_linked_response_count += 1
        for context in record.player_contexts:
            context_player = player_aggregates[context.player_id]
            context_player.player_context_reference_count += 1
            readiness.player_context_total_count += 1
            if context.selection_status == "available":
                match.player_context_available_count += 1
                context_player.player_context_available_count += 1
                readiness.player_context_available_count += 1
            else:
                reason = context.unavailable_reason
                if reason not in LEARNING_DATASET_SUMMARY_PLAYER_CONTEXT_UNAVAILABLE_REASONS:
                    raise ValueError(
                        "Player Context unavailability must use the existing vocabulary."
                    )
                assert reason is not None
                match.player_context_unavailable_count += 1
                context_player.player_context_unavailable_count += 1
                context_player.player_context_unavailable_reasons[reason] += 1
                readiness.player_context_unavailable_count += 1
                readiness.player_context_unavailable_reasons[reason] += 1

    skipped_by_snapshot: dict[str, list[LearningDatasetSkippedDecisionV1]] = {}
    unjoined_commentary = set(dataset.unjoined_commentary_evidence_ids)
    unjoined_response = set(dataset.unjoined_response_evidence_ids)
    for skipped in _traverse_source_once(dataset.skipped_decisions):
        _append(skipped_by_snapshot, skipped.match_snapshot_id, skipped)
        match = match_aggregates[skipped.match_snapshot_id]
        if skipped.match_id != match.match_id or skipped.acting_player_id not in match.player_ids:
            raise ValueError("Skipped Decision and Player Catalog Match identity must reconcile.")
        match.skipped_decision_count += 1
        match.observed_game_reference_ids.add(skipped.game_reference_id)
        match.unjoined_commentary_evidence_ids.update(
            item for item in skipped.commentary_evidence_ids if item in unjoined_commentary
        )
        match.unjoined_response_evidence_ids.update(
            item
            for item in (
                *skipped.outgoing_response_evidence_ids,
                *skipped.incoming_response_evidence_ids,
            )
            if item in unjoined_response
        )
        player_aggregates[skipped.acting_player_id].skipped_decision_count += 1
        readiness.skipped_reasons[skipped.reason] += 1

    teachers_by_id: dict[str, LearningCorpusStrategyTeacherEvidenceV1] = {}
    teachers_by_decision: dict[str, list[LearningCorpusStrategyTeacherEvidenceV1]] = {}
    strategy = _StrategyAggregate()
    for teacher in _traverse_source_once(dataset.strategy_teacher_evidences):
        teachers_by_id[teacher.strategy_teacher_evidence_id] = teacher
        _append(teachers_by_decision, teacher.decision_reference_id, teacher)
        match_aggregates[teacher.match_snapshot_id].strategy_teacher_evidence_count += 1
        player = player_aggregates[teacher.acting_player_id]
        player.strategy_teacher_evidence_count += 1
        player.teacher_decision_reference_ids.add(teacher.decision_reference_id)
        strategy.evidence_count += 1
        strategy.decision_counts[teacher.decision_reference_id] += 1
        strategy.semantic_counts[teacher.teacher_semantic_fingerprint] += 1
        strategy.requested_methods[teacher.options.recommendation_method] += 1
        effective_method = teacher.recommendation_method_summary["effective_method"]
        if not isinstance(effective_method, str):
            raise ValueError("Teacher effective method must be a string.")
        strategy.effective_methods[effective_method] += 1
        strategy.search_statuses[teacher.search_status] += 1
        if teacher.status == "recommendation_available":
            player.recommendation_available_count += 1
            strategy.recommendation_available_count += 1
        else:
            player.recommendation_unavailable_count += 1
            strategy.recommendation_unavailable_count += 1
        comparison = _teacher_card_comparison(teacher)
        if comparison == "match":
            player.teacher_actual_card_match_count += 1
            strategy.actual_card_match_evidence_count += 1
        elif comparison == "difference":
            player.teacher_actual_card_difference_count += 1
            strategy.actual_card_difference_evidence_count += 1
        else:
            strategy.actual_card_comparison_unavailable_count += 1
        strategy.fallback_count += (
            teacher.recommendation_method_summary.get("fallback_used") is True
        )
        strategy.profile_presets_enabled_count += (
            teacher.profile_preset_settings.get("use_profile_presets") is True
        )
        strategy.profile_application_summary_count += (
            teacher.opponent_profile_application_summary is not None
        )

    commentaries_by_id: dict[str, LearningCorpusCommentaryEvidenceV1] = {}
    commentaries_by_decision: dict[str, list[LearningCorpusCommentaryEvidenceV1]] = {}
    communication = _CommunicationAggregate()
    for commentary in _traverse_source_once(dataset.commentary_evidences):
        commentaries_by_id[commentary.commentary_evidence_id] = commentary
        _append(
            commentaries_by_decision,
            commentary.subject_decision_reference_id,
            commentary,
        )
        match_aggregates[commentary.match_snapshot_id].commentary_evidence_count += 1
        subject = player_aggregates[commentary.subject_player_id]
        subject.commentary_subject_count += 1
        subject.commented_decision_reference_ids.add(commentary.subject_decision_reference_id)
        author_id = commentary.commentator_player_id
        if author_id is not None and author_id in player_aggregates:
            player_aggregates[author_id].commentary_authored_count += 1
        communication.commentary_count += 1
        communication.commented_decision_reference_ids.add(commentary.subject_decision_reference_id)
        communication.commentator_identity_kinds[commentary.commentator_identity_kind] += 1
        subject_record = records_by_decision[commentary.subject_decision_reference_id]
        communication.commentary_on_perspective_player_count += (
            commentary.subject_player_id == subject_record.source_context.perspective_player_id
        )
        communication.subject_roles[commentary.subject_role] += 1
        communication.subject_seats[commentary.subject_seat] += 1

    responses_by_id: dict[str, LearningCorpusResponseEvidenceV1] = {}
    responses_by_subject_decision: dict[str, list[LearningCorpusResponseEvidenceV1]] = {}
    responses_by_response_decision: dict[str, list[LearningCorpusResponseEvidenceV1]] = {}
    for response in _traverse_source_once(dataset.response_evidences):
        commentary = commentaries_by_id[response.commentary_evidence_id]
        responses_by_id[response.response_evidence_id] = response
        _append(responses_by_subject_decision, response.subject_decision_reference_id, response)
        _append(responses_by_response_decision, response.response_decision_reference_id, response)
        match_aggregates[response.match_snapshot_id].response_evidence_count += 1
        subject = player_aggregates[commentary.subject_player_id]
        subject.outgoing_response_count += 1
        subject.same_trick_response_count += response.same_trick
        subject.later_trick_response_count += not response.same_trick
        player_aggregates[response.response_player_id].incoming_response_count += 1
        communication.commentary_ids_with_response.add(response.commentary_evidence_id)
        communication.response_count += 1
        communication.same_trick_response_count += response.same_trick
        communication.later_trick_response_count += not response.same_trick
        communication.decision_offsets[response.decision_offset] += 1
        communication.response_roles[response.response_role] += 1
        communication.response_seats[response.response_seat] += 1
        communication.subject_response_role_pairs[
            f"{commentary.subject_role}->{response.response_role}"
        ] += 1
        communication.subject_response_seat_pairs[
            f"{commentary.subject_seat}->{response.response_seat}"
        ] += 1

    return _SummaryIndexes(
        records_by_id=records_by_id,
        records_by_decision=records_by_decision,
        records_by_snapshot=records_by_snapshot,
        skipped_by_snapshot=skipped_by_snapshot,
        teachers_by_id=teachers_by_id,
        teachers_by_decision=teachers_by_decision,
        commentaries_by_id=commentaries_by_id,
        commentaries_by_decision=commentaries_by_decision,
        responses_by_id=responses_by_id,
        responses_by_subject_decision=responses_by_subject_decision,
        responses_by_response_decision=responses_by_response_decision,
        player_entries_by_id=player_entries_by_id,
        match_aggregates=match_aggregates,
        player_aggregates=player_aggregates,
        communication=communication,
        strategy=strategy,
        readiness=readiness,
    )


def _categorical_counts(
    values: Counter[str],
    *,
    canonical: tuple[str, ...] | None = None,
    include_zero: bool = False,
) -> tuple[LearningDatasetSummaryCategoricalCountV1, ...]:
    categories = (
        canonical
        if canonical is not None and include_zero
        else tuple(category for category in canonical if category in values)
        if canonical is not None
        else tuple(sorted(values))
    )
    return tuple(
        LearningDatasetSummaryCategoricalCountV1(
            category=category,
            count=values[category],
        )
        for category in categories
    )


def _integer_counts(
    values: Counter[int],
) -> tuple[LearningDatasetSummaryIntegerCountV1, ...]:
    return tuple(
        LearningDatasetSummaryIntegerCountV1(value=value, count=values[value])
        for value in sorted(values)
    )


def _record_game_type(record: LearningDatasetRecordV1) -> str:
    game_type = record.decision_state.visible_state["game_type"]
    if not isinstance(game_type, str) or game_type not in LEARNING_DATASET_SUMMARY_GAME_TYPES:
        raise ValueError("Decision State game type must use the existing canonical vocabulary.")
    return game_type


def _record_legal_card_count(record: LearningDatasetRecordV1) -> int:
    legal_cards = record.decision_state.visible_state["legal_cards"]
    if not isinstance(legal_cards, tuple) or not legal_cards:
        raise ValueError("Every safe Decision requires at least one exact legal Card.")
    return len(legal_cards)


def _behavior_counts(aggregate: _BehaviorAggregate) -> dict[str, object]:
    return {
        "records_by_game_type": _categorical_counts(
            aggregate.game_types,
            canonical=LEARNING_DATASET_SUMMARY_GAME_TYPES,
            include_zero=True,
        ),
        "records_by_acting_side": _categorical_counts(
            aggregate.acting_sides,
            canonical=LEARNING_DATASET_SUMMARY_ACTING_SIDES,
            include_zero=True,
        ),
        "records_by_acting_seat": _categorical_counts(
            aggregate.acting_seats,
            canonical=LEARNING_DATASET_SUMMARY_SEATS,
            include_zero=True,
        ),
        "records_by_trick_number": _integer_counts(aggregate.trick_numbers),
        "records_by_play_index": _integer_counts(aggregate.play_indexes),
        "forced_choice_record_count": aggregate.forced_choice_record_count,
        "choice_record_count": aggregate.choice_record_count,
    }


def _build_match_summaries(
    indexes: _SummaryIndexes,
) -> tuple[Any, ...]:
    summaries = []
    for aggregate in indexes.match_aggregates.values():
        observed_decision_count = aggregate.record_count + aggregate.skipped_decision_count
        summaries.append(
            _build_match_summary_v1(
                learning_dataset_match_summary_version=LEARNING_DATASET_MATCH_SUMMARY_VERSION,
                match_snapshot_id=aggregate.match_snapshot_id,
                match_id=aggregate.match_id,
                played_at=aggregate.played_at,
                player_ids=aggregate.player_ids,
                perspective_player_id=aggregate.perspective_player_id,
                observed_game_count=len(aggregate.observed_game_reference_ids),
                record_count=aggregate.record_count,
                skipped_decision_count=aggregate.skipped_decision_count,
                observed_decision_count=observed_decision_count,
                record_coverage=build_learning_dataset_summary_coverage_v1(
                    family="decision_state",
                    covered_count=aggregate.record_count,
                    total_count=observed_decision_count,
                ),
                **_behavior_counts(aggregate.behavior),
                player_context_available_count=aggregate.player_context_available_count,
                player_context_unavailable_count=aggregate.player_context_unavailable_count,
                strategy_teacher_evidence_count=aggregate.strategy_teacher_evidence_count,
                commentary_evidence_count=aggregate.commentary_evidence_count,
                response_evidence_count=aggregate.response_evidence_count,
                records_with_strategy_teacher_count=(aggregate.records_with_strategy_teacher_count),
                records_with_commentary_count=aggregate.records_with_commentary_count,
                records_with_linked_response_count=aggregate.records_with_linked_response_count,
                unjoined_commentary_evidence_count=len(aggregate.unjoined_commentary_evidence_ids),
                unjoined_response_evidence_count=len(aggregate.unjoined_response_evidence_ids),
            )
        )
    return tuple(sorted(summaries, key=lambda item: (item.match_id, item.match_snapshot_id)))


def _build_player_summaries(
    indexes: _SummaryIndexes,
) -> tuple[Any, ...]:
    summaries = []
    for aggregate in indexes.player_aggregates.values():
        entry = aggregate.entry
        player_id = entry.player_id
        observed_decision_count = aggregate.record_count + aggregate.skipped_decision_count
        summaries.append(
            _build_player_summary_v1(
                learning_dataset_player_summary_version=LEARNING_DATASET_PLAYER_SUMMARY_VERSION,
                player_id=player_id,
                observed_labels=entry.observed_labels,
                match_ids=entry.match_ids,
                current_match_snapshot_ids=entry.current_match_snapshot_ids,
                match_count=entry.match_count,
                perspective_match_count=aggregate.perspective_match_count,
                record_count=aggregate.record_count,
                skipped_decision_count=aggregate.skipped_decision_count,
                observed_decision_count=observed_decision_count,
                **_behavior_counts(aggregate.behavior),
                actual_card_counts=_categorical_counts(
                    aggregate.actual_cards,
                    canonical=LEARNING_DATASET_SUMMARY_CARDS,
                ),
                player_context_reference_count=aggregate.player_context_reference_count,
                player_context_available_count=aggregate.player_context_available_count,
                player_context_unavailable_count=aggregate.player_context_unavailable_count,
                player_context_unavailable_reason_counts=_categorical_counts(
                    aggregate.player_context_unavailable_reasons,
                    canonical=(LEARNING_DATASET_SUMMARY_PLAYER_CONTEXT_UNAVAILABLE_REASONS),
                ),
                statistics_observation_count=entry.statistics_observation_count,
                strategy_teacher_evidence_count=aggregate.strategy_teacher_evidence_count,
                teacher_distinct_decision_count=len(aggregate.teacher_decision_reference_ids),
                recommendation_available_count=aggregate.recommendation_available_count,
                recommendation_unavailable_count=aggregate.recommendation_unavailable_count,
                teacher_actual_card_match_count=aggregate.teacher_actual_card_match_count,
                teacher_actual_card_difference_count=aggregate.teacher_actual_card_difference_count,
                commentary_subject_count=aggregate.commentary_subject_count,
                commented_decision_count=len(aggregate.commented_decision_reference_ids),
                commentary_authored_count=aggregate.commentary_authored_count,
                outgoing_response_count=aggregate.outgoing_response_count,
                incoming_response_count=aggregate.incoming_response_count,
                same_trick_response_count=aggregate.same_trick_response_count,
                later_trick_response_count=aggregate.later_trick_response_count,
            )
        )
    return tuple(summaries)


def _build_communication_summary(
    dataset: LearningDatasetV2,
    indexes: _SummaryIndexes,
) -> Any:
    aggregate = indexes.communication
    role_pairs = tuple(
        f"{subject}->{response}"
        for subject in LEARNING_DATASET_SUMMARY_HUMAN_ROLES
        for response in LEARNING_DATASET_SUMMARY_HUMAN_ROLES
    )
    seat_pairs = tuple(
        f"{subject}->{response}"
        for subject in LEARNING_DATASET_SUMMARY_SEATS
        for response in LEARNING_DATASET_SUMMARY_SEATS
    )
    commentaries_with_response_count = len(aggregate.commentary_ids_with_response)
    return _build_communication_summary_v1(
        learning_dataset_communication_summary_version=(
            LEARNING_DATASET_COMMUNICATION_SUMMARY_VERSION
        ),
        commentary_count=aggregate.commentary_count,
        commented_decision_count=len(aggregate.commented_decision_reference_ids),
        commentator_identity_kind_counts=_categorical_counts(
            aggregate.commentator_identity_kinds,
            canonical=LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS,
            include_zero=True,
        ),
        commentary_on_perspective_player_count=(aggregate.commentary_on_perspective_player_count),
        commentary_on_non_perspective_player_count=(
            aggregate.commentary_count - aggregate.commentary_on_perspective_player_count
        ),
        commentaries_with_response_count=commentaries_with_response_count,
        commentaries_without_response_count=(
            aggregate.commentary_count - commentaries_with_response_count
        ),
        response_count=aggregate.response_count,
        same_trick_response_count=aggregate.same_trick_response_count,
        later_trick_response_count=aggregate.later_trick_response_count,
        decision_offset_counts=_integer_counts(aggregate.decision_offsets),
        subject_role_counts=_categorical_counts(
            aggregate.subject_roles,
            canonical=LEARNING_DATASET_SUMMARY_HUMAN_ROLES,
            include_zero=True,
        ),
        response_role_counts=_categorical_counts(
            aggregate.response_roles,
            canonical=LEARNING_DATASET_SUMMARY_HUMAN_ROLES,
            include_zero=True,
        ),
        subject_seat_counts=_categorical_counts(
            aggregate.subject_seats,
            canonical=LEARNING_DATASET_SUMMARY_SEATS,
            include_zero=True,
        ),
        response_seat_counts=_categorical_counts(
            aggregate.response_seats,
            canonical=LEARNING_DATASET_SUMMARY_SEATS,
            include_zero=True,
        ),
        subject_response_role_pair_counts=_categorical_counts(
            aggregate.subject_response_role_pairs,
            canonical=role_pairs,
            include_zero=True,
        ),
        subject_response_seat_pair_counts=_categorical_counts(
            aggregate.subject_response_seat_pairs,
            canonical=seat_pairs,
            include_zero=True,
        ),
        unjoined_commentary_evidence_count=dataset.unjoined_commentary_evidence_count,
        unjoined_response_evidence_count=dataset.unjoined_response_evidence_count,
    )


def _build_strategy_summary(indexes: _SummaryIndexes) -> Any:
    aggregate = indexes.strategy
    if any(item not in FLAT_RECOMMENDATION_METHODS for item in aggregate.requested_methods):
        raise ValueError("Teacher requested methods must use the existing vocabulary.")
    if any(
        item not in LEARNING_DATASET_SUMMARY_EFFECTIVE_METHODS
        for item in aggregate.effective_methods
    ):
        raise ValueError("Teacher effective methods must use the existing vocabulary.")
    if any(
        item not in LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES
        for item in aggregate.search_statuses
    ):
        raise ValueError("Teacher Search statuses must use the existing vocabulary.")
    return _build_strategy_summary_v1(
        learning_dataset_strategy_summary_version=LEARNING_DATASET_STRATEGY_SUMMARY_VERSION,
        evidence_count=aggregate.evidence_count,
        distinct_decision_count=len(aggregate.decision_counts),
        multi_teacher_decision_count=sum(count > 1 for count in aggregate.decision_counts.values()),
        maximum_teacher_count_per_decision=max(aggregate.decision_counts.values(), default=0),
        semantic_fingerprint_count=len(aggregate.semantic_counts),
        semantic_duplicate_group_count=sum(
            count > 1 for count in aggregate.semantic_counts.values()
        ),
        recommendation_available_count=aggregate.recommendation_available_count,
        recommendation_unavailable_count=aggregate.recommendation_unavailable_count,
        requested_method_counts=_categorical_counts(
            aggregate.requested_methods,
            canonical=tuple(FLAT_RECOMMENDATION_METHODS),
            include_zero=True,
        ),
        effective_method_counts=_categorical_counts(
            aggregate.effective_methods,
            canonical=LEARNING_DATASET_SUMMARY_EFFECTIVE_METHODS,
            include_zero=True,
        ),
        search_status_counts=_categorical_counts(
            aggregate.search_statuses,
            canonical=LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES,
            include_zero=True,
        ),
        fallback_count=aggregate.fallback_count,
        profile_presets_enabled_count=aggregate.profile_presets_enabled_count,
        profile_application_summary_count=aggregate.profile_application_summary_count,
        actual_card_match_evidence_count=aggregate.actual_card_match_evidence_count,
        actual_card_difference_evidence_count=(aggregate.actual_card_difference_evidence_count),
        actual_card_comparison_unavailable_count=(
            aggregate.actual_card_comparison_unavailable_count
        ),
    )


def _reconcile_partition_result(
    result: LearningDatasetPartitionPreparationResultV1,
    dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
    *,
    expected_mode: str,
) -> Any:
    if type(result) is not LearningDatasetPartitionPreparationResultV1:
        raise ValueError("Partition inputs must be exact preparation Results.")
    if (
        type(result.learning_dataset_partition_preparation_version) is not int
        or result.learning_dataset_partition_preparation_version
        != LEARNING_DATASET_PARTITION_PREPARATION_VERSION
    ):
        raise ValueError(
            "learning_dataset_partition_preparation_version must equal "
            f"{LEARNING_DATASET_PARTITION_PREPARATION_VERSION}."
        )
    if result.status not in LEARNING_DATASET_PARTITION_PLAN_STATUSES:
        raise ValueError("Partition Result status must be complete or unavailable.")
    if type(result.plan) is not LearningDatasetPartitionPlanV1:
        raise ValueError("Partition Result must retain one exact Plan.")
    result.plan._validate()
    plan = result.plan
    if result.status != plan.status or result.request_fingerprint != plan.request_fingerprint:
        raise ValueError(
            "Partition Result status and request fingerprint must reconcile with its exact Plan."
        )
    if result.status == "complete":
        if (
            result.unavailable_reason is not None
            or type(result.partitioned_view) is not LearningDatasetPartitionedViewV1
        ):
            raise ValueError("A complete Partition Result requires one exact view and no reason.")
        if result.partitioned_view.plan_fingerprint != plan.plan_fingerprint:
            raise ValueError("Partitioned View must reference the exact supplied Plan.")
    elif (
        result.unavailable_reason != plan.unavailable_reason
        or result.unavailable_reason is None
        or result.partitioned_view is not None
    ):
        raise ValueError("An unavailable Partition Result requires its Plan reason and no view.")
    if plan.mode != expected_mode:
        raise ValueError(f"The {expected_mode} input must use the exact matching mode.")
    rebuilt_request = (
        _build_learning_dataset_partition_preparation_request_from_validated_sources_v1(
            dataset,
            player_catalog,
            mode=plan.mode,
            base_random_seed=plan.base_random_seed,
            partition_weights=plan.requested_partition_weights,
        )
    )
    if rebuilt_request.request_fingerprint != result.request_fingerprint or (
        rebuilt_request.request_fingerprint != plan.request_fingerprint
    ):
        raise ValueError("Partition Result request fingerprint must match exact supplied sources.")
    if (
        plan.source_current_match_count != dataset.current_match_count
        or plan.source_active_match_group_count + plan.source_inactive_match_count
        != dataset.current_match_count
        or plan.source_record_count != dataset.record_count
        or plan.source_skipped_decision_count != dataset.skipped_decision_count
    ):
        raise ValueError("Partition Plan source Counts must match the exact Dataset.")
    if result.status == "complete":
        if (
            result.partitioned_view is None
            or result.partitioned_view.learning_dataset is not dataset
        ):
            raise ValueError("A complete Partitioned View must retain the exact source Dataset.")
        audit = plan.leakage_audit
        assert audit is not None
        all_partitions_have_records = all(
            item.record_count > 0 for item in plan.partition_summaries
        )
        if plan.mode == "known_player":
            temporal = plan.known_player_temporal_audit
            assert temporal is not None
            mode_constraints_satisfied = all(
                (
                    temporal.all_played_at_present,
                    temporal.strict_partition_order,
                    temporal.equal_timestamp_groups_preserved,
                    temporal.validation_train_coverage_complete,
                    temporal.test_train_coverage_complete,
                    all_partitions_have_records,
                    audit.status == "compliant",
                )
            )
            known_values = {
                "known_player_time_group_count": temporal.time_group_count,
                "known_player_validation_train_coverage_complete": (
                    temporal.validation_train_coverage_complete
                ),
                "known_player_test_train_coverage_complete": (
                    temporal.test_train_coverage_complete
                ),
            }
            unseen_values = {
                "unseen_player_component_count": None,
                "unseen_player_player_disjoint": None,
                "unseen_player_local_move_optimal": None,
                "unseen_player_local_swap_optimal": None,
            }
        else:
            component = plan.unseen_player_component_audit
            assert component is not None
            mode_constraints_satisfied = all(
                (
                    component.player_disjoint,
                    component.components_indivisible,
                    component.all_partitions_have_records,
                    component.local_move_optimal,
                    component.local_swap_optimal,
                    all_partitions_have_records,
                    audit.status == "compliant",
                )
            )
            known_values = {
                "known_player_time_group_count": None,
                "known_player_validation_train_coverage_complete": None,
                "known_player_test_train_coverage_complete": None,
            }
            unseen_values = {
                "unseen_player_component_count": component.component_count,
                "unseen_player_player_disjoint": component.player_disjoint,
                "unseen_player_local_move_optimal": component.local_move_optimal,
                "unseen_player_local_swap_optimal": component.local_swap_optimal,
            }
        complete_values = {
            "leakage_audit_status": audit.status,
            "all_partitions_have_records": all_partitions_have_records,
            "mode_constraints_satisfied": mode_constraints_satisfied,
            "partition_summaries": plan.partition_summaries,
            **known_values,
            **unseen_values,
        }
    else:
        complete_values = {
            "leakage_audit_status": None,
            "all_partitions_have_records": None,
            "mode_constraints_satisfied": False,
            "partition_summaries": (),
            "known_player_time_group_count": None,
            "known_player_validation_train_coverage_complete": None,
            "known_player_test_train_coverage_complete": None,
            "unseen_player_component_count": None,
            "unseen_player_player_disjoint": None,
            "unseen_player_local_move_optimal": None,
            "unseen_player_local_swap_optimal": None,
        }
    return _build_partition_readiness_v1(
        learning_dataset_partition_readiness_version=(LEARNING_DATASET_PARTITION_READINESS_VERSION),
        mode=plan.mode,
        algorithm=plan.algorithm,
        status=result.status,
        unavailable_reason=result.unavailable_reason,
        request_fingerprint=result.request_fingerprint,
        plan_fingerprint=plan.plan_fingerprint,
        base_random_seed=plan.base_random_seed,
        requested_partition_weights=plan.requested_partition_weights,
        source_active_match_group_count=plan.source_active_match_group_count,
        source_inactive_match_count=plan.source_inactive_match_count,
        source_record_count=plan.source_record_count,
        source_skipped_decision_count=plan.source_skipped_decision_count,
        **complete_values,
    )


def _build_readiness_summary(
    dataset: LearningDatasetV2,
    indexes: _SummaryIndexes,
    partition_readiness: tuple[Any, ...],
) -> Any:
    aggregate = indexes.readiness
    coverage_counts = {
        "observed_behavior": dataset.record_count,
        "player_context": dataset.record_count,
        "strategy_teacher": dataset.records_with_strategy_teacher_count,
        "human_commentary": dataset.records_with_commentary_count,
        "linked_response": aggregate.records_with_linked_response_count,
    }
    selected_count = aggregate.player_context_available_count
    if selected_count != dataset.selected_statistics_context_count:
        raise ValueError("Available Player Contexts must match selected Statistics Count.")
    return _build_readiness_summary_v1(
        learning_dataset_readiness_summary_version=(LEARNING_DATASET_READINESS_SUMMARY_VERSION),
        dataset_status=dataset.status,
        decision_state_coverage=build_learning_dataset_summary_coverage_v1(
            family="decision_state",
            covered_count=dataset.record_count,
            total_count=dataset.observed_decision_count,
        ),
        evidence_family_coverages=tuple(
            build_learning_dataset_summary_coverage_v1(
                family=family,
                covered_count=coverage_counts[family],
                total_count=dataset.record_count,
            )
            for family in (
                "observed_behavior",
                "player_context",
                "strategy_teacher",
                "human_commentary",
                "linked_response",
            )
        ),
        skipped_reason_counts=_categorical_counts(
            aggregate.skipped_reasons,
            canonical=MATCH_DECISION_REVIEW_SKIP_REASONS,
            include_zero=True,
        ),
        player_context_total_count=aggregate.player_context_total_count,
        player_context_available_count=selected_count,
        player_context_unavailable_count=aggregate.player_context_unavailable_count,
        player_context_unavailable_reason_counts=_categorical_counts(
            aggregate.player_context_unavailable_reasons,
            canonical=LEARNING_DATASET_SUMMARY_PLAYER_CONTEXT_UNAVAILABLE_REASONS,
        ),
        selected_statistics_context_count=dataset.selected_statistics_context_count,
        statistics_observation_pool_count=dataset.statistics_observation_count,
        unjoined_commentary_evidence_count=dataset.unjoined_commentary_evidence_count,
        unjoined_response_evidence_count=dataset.unjoined_response_evidence_count,
        partition_readiness=partition_readiness,
    )


def build_learning_dataset_v2_cross_game_summary_v1(
    learning_dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
    *,
    known_player_partition_result: LearningDatasetPartitionPreparationResultV1,
    unseen_player_partition_result: LearningDatasetPartitionPreparationResultV1,
) -> LearningDatasetCrossGameSummaryV1:
    """Builds one private descriptive cross-game Summary without source regeneration."""
    _validate_learning_dataset_v2(learning_dataset)
    _validate_learning_corpus_player_catalog_v1(player_catalog)
    _reconcile_partition_sources(learning_dataset, player_catalog)

    partition_readiness = (
        _reconcile_partition_result(
            known_player_partition_result,
            learning_dataset,
            player_catalog,
            expected_mode=LEARNING_DATASET_PARTITION_MODES[0],
        ),
        _reconcile_partition_result(
            unseen_player_partition_result,
            learning_dataset,
            player_catalog,
            expected_mode=LEARNING_DATASET_PARTITION_MODES[1],
        ),
    )
    indexes = _build_indexes(learning_dataset, player_catalog)
    match_summaries = _build_match_summaries(indexes)
    player_summaries = _build_player_summaries(indexes)
    communication_summary = _build_communication_summary(learning_dataset, indexes)
    strategy_summary = _build_strategy_summary(indexes)
    readiness_summary = _build_readiness_summary(
        learning_dataset,
        indexes,
        partition_readiness,
    )
    return _build_cross_game_summary_v1(
        learning_dataset_cross_game_summary_version=(LEARNING_DATASET_CROSS_GAME_SUMMARY_VERSION),
        dataset_id=learning_dataset.dataset_id,
        dataset_fingerprint=learning_dataset.dataset_fingerprint,
        player_catalog_fingerprint=player_catalog.player_catalog_fingerprint,
        corpus_id=learning_dataset.corpus_id,
        source_catalog_revision=learning_dataset.source_catalog_revision,
        source_catalog_fingerprint=learning_dataset.source_catalog_fingerprint,
        source_catalog_content_fingerprint=(learning_dataset.source_catalog_content_fingerprint),
        current_match_snapshot_ids=learning_dataset.current_match_snapshot_ids,
        dataset_status=learning_dataset.status,
        retained_match_snapshot_count=learning_dataset.retained_match_snapshot_count,
        current_match_count=learning_dataset.current_match_count,
        orphan_match_snapshot_count=learning_dataset.orphan_match_snapshot_count,
        observed_game_count=learning_dataset.observed_game_count,
        observed_decision_count=learning_dataset.observed_decision_count,
        record_count=learning_dataset.record_count,
        skipped_decision_count=learning_dataset.skipped_decision_count,
        player_count=player_catalog.player_count,
        match_summaries=match_summaries,
        player_summaries=player_summaries,
        communication_summary=communication_summary,
        strategy_summary=strategy_summary,
        readiness_summary=readiness_summary,
    )
