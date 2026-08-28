from __future__ import annotations

from dataclasses import replace

from skatmind.learning_corpus_player_catalog import (
    LearningCorpusPlayerCatalogV1,
    _validate_learning_corpus_player_catalog_v1,
)
from skatmind.learning_dataset_v2_contracts import (
    LearningDatasetV2,
    _validate_learning_dataset_v2,
)
from skatmind.learning_dataset_v2_partition_algorithms import (
    _PartitionAlgorithmResult,
    generate_component_balanced_unseen_player_match_group_assignments_v1,
    generate_temporal_known_player_match_group_assignments_v1,
)
from skatmind.learning_dataset_v2_partition_audit import (
    audit_learning_dataset_v2_partitions_v1,
)
from skatmind.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_MATCH_GROUP_VERSION,
    LEARNING_DATASET_PARTITION_ALGORITHM_BY_MODE,
    LEARNING_DATASET_PARTITION_MODES,
    LEARNING_DATASET_PARTITION_PLAN_VERSION,
    LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
    LEARNING_DATASET_PARTITIONED_VIEW_VERSION,
    LEARNING_DATASET_PARTITIONS,
    LearningDatasetMatchGroupV1,
    LearningDatasetPartitionedViewV1,
    LearningDatasetPartitionPlanV1,
    LearningDatasetPartitionPreparationRequestV1,
    LearningDatasetPartitionPreparationResultV1,
    LearningDatasetPartitionSliceV1,
    LearningDatasetPartitionSummaryV1,
    LearningDatasetPartitionWeightsV1,
)
from skatmind.learning_dataset_v2_partition_identity import (
    build_learning_dataset_match_group_id_v1,
    build_learning_dataset_partition_plan_fingerprint_v1,
    build_learning_dataset_partition_request_fingerprint_v1,
    build_learning_dataset_partition_source_content_fingerprint_v1,
    build_learning_dataset_partition_source_identity_fingerprint_v1,
    build_learning_dataset_partitioned_view_fingerprint_v1,
    validate_learning_dataset_partition_request_fingerprint_v1,
)


def _reconcile_partition_sources(
    dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
) -> None:
    expected = (
        dataset.corpus_id,
        dataset.source_catalog_revision,
        dataset.source_catalog_fingerprint,
        dataset.source_catalog_content_fingerprint,
        dataset.current_match_snapshot_ids,
        dataset.retained_match_snapshot_count,
        dataset.current_match_count,
        dataset.orphan_match_snapshot_count,
    )
    actual = (
        player_catalog.corpus_id,
        player_catalog.source_catalog_revision,
        player_catalog.source_catalog_fingerprint,
        player_catalog.source_catalog_content_fingerprint,
        player_catalog.current_match_snapshot_ids,
        player_catalog.retained_match_snapshot_count,
        player_catalog.current_match_count,
        player_catalog.orphan_match_snapshot_count,
    )
    if actual != expected:
        raise ValueError(
            "Learning Dataset and Player Catalog source identities must match exactly."
        )
    if dataset.player_catalog_fingerprint != player_catalog.player_catalog_fingerprint:
        raise ValueError("Learning Dataset must reference the exact supplied Player Catalog.")


def build_learning_dataset_partition_preparation_request_v1(
    learning_dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
    *,
    mode: str,
    base_random_seed: int,
    partition_weights: LearningDatasetPartitionWeightsV1,
) -> LearningDatasetPartitionPreparationRequestV1:
    """Builds one exact no-rebuild partition preparation Request."""
    _validate_learning_dataset_v2(learning_dataset)
    _validate_learning_corpus_player_catalog_v1(player_catalog)
    _reconcile_partition_sources(learning_dataset, player_catalog)
    return _build_learning_dataset_partition_preparation_request_from_validated_sources_v1(
        learning_dataset,
        player_catalog,
        mode=mode,
        base_random_seed=base_random_seed,
        partition_weights=partition_weights,
    )


def _build_learning_dataset_partition_preparation_request_from_validated_sources_v1(
    learning_dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
    *,
    mode: str,
    base_random_seed: int,
    partition_weights: LearningDatasetPartitionWeightsV1,
) -> LearningDatasetPartitionPreparationRequestV1:
    """Builds a Request after one caller-owned exact source validation."""
    if mode not in LEARNING_DATASET_PARTITION_MODES:
        raise ValueError(f"mode must be one of {list(LEARNING_DATASET_PARTITION_MODES)}.")
    if type(base_random_seed) is not int:
        raise ValueError("base_random_seed must be an integer and not a boolean.")
    if type(partition_weights) is not LearningDatasetPartitionWeightsV1:
        raise ValueError("partition_weights must be exact LearningDatasetPartitionWeightsV1.")
    algorithm = LEARNING_DATASET_PARTITION_ALGORITHM_BY_MODE[mode]
    fingerprint = build_learning_dataset_partition_request_fingerprint_v1(
        mode=mode,
        algorithm=algorithm,
        base_random_seed=base_random_seed,
        partition_weights=partition_weights,
        learning_dataset=learning_dataset,
        player_catalog=player_catalog,
    )
    return LearningDatasetPartitionPreparationRequestV1._from_validated(
        learning_dataset_partition_preparation_version=(
            LEARNING_DATASET_PARTITION_PREPARATION_VERSION
        ),
        request_fingerprint=fingerprint,
        mode=mode,
        algorithm=algorithm,
        base_random_seed=base_random_seed,
        partition_weights=partition_weights,
        learning_dataset=learning_dataset,
        player_catalog=player_catalog,
    )


def _catalog_match_facts(
    player_catalog: LearningCorpusPlayerCatalogV1,
) -> dict[str, tuple[str, str | None, tuple[str, ...]]]:
    observations_by_snapshot: dict[str, list[object]] = {}
    for player in player_catalog.players:
        for observation in player.match_observations:
            observations_by_snapshot.setdefault(observation.match_snapshot_id, []).append(
                observation
            )
    result = {}
    for snapshot_id in player_catalog.current_match_snapshot_ids:
        observations = observations_by_snapshot.get(snapshot_id, [])
        if len(observations) != 3:
            raise ValueError("Each Current Match Snapshot must resolve to exactly three Players.")
        match_ids = {item.match_id for item in observations}
        played_times = {item.played_at for item in observations}
        player_ids = tuple(sorted(item.player_id for item in observations))
        if len(match_ids) != 1 or len(played_times) != 1 or len(set(player_ids)) != 3:
            raise ValueError("Player Catalog Match observations must reconcile exactly.")
        result[snapshot_id] = (match_ids.pop(), played_times.pop(), player_ids)
    return result


def derive_learning_dataset_match_groups_v1(
    dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
) -> tuple[tuple[LearningDatasetMatchGroupV1, ...], tuple[str, ...]]:
    """Derives active Match groups and inactive Current Snapshot IDs once."""
    match_facts = _catalog_match_facts(player_catalog)
    records_by_snapshot = {
        snapshot_id: tuple(
            record
            for record in dataset.records
            if record.source_context.match_snapshot_id == snapshot_id
        )
        for snapshot_id in dataset.current_match_snapshot_ids
    }
    skipped_by_snapshot = {
        snapshot_id: tuple(
            item for item in dataset.skipped_decisions if item.match_snapshot_id == snapshot_id
        )
        for snapshot_id in dataset.current_match_snapshot_ids
    }
    active_groups = []
    inactive = []
    for snapshot_id in dataset.current_match_snapshot_ids:
        records = records_by_snapshot[snapshot_id]
        skipped = skipped_by_snapshot[snapshot_id]
        if not records and not skipped:
            inactive.append(snapshot_id)
            continue
        match_id, played_at, player_ids = match_facts[snapshot_id]
        if any(record.source_context.match_id != match_id for record in records) or any(
            item.match_id != match_id for item in skipped
        ):
            raise ValueError("Dataset Match identity must reconcile with Player Catalog facts.")
        if any(record.source_context.played_at != played_at for record in records):
            raise ValueError("Dataset Match time must reconcile with Player Catalog facts.")
        record_ids = tuple(item.record_id for item in records)
        skipped_ids = tuple(item.skipped_decision_id for item in skipped)
        joined_commentary = tuple(
            item for item in dataset.commentary_evidences if item.match_snapshot_id == snapshot_id
        )
        joined_responses = tuple(
            item for item in dataset.response_evidences if item.match_snapshot_id == snapshot_id
        )
        unjoined_commentary_ids = {
            evidence_id
            for item in skipped
            for evidence_id in item.commentary_evidence_ids
            if evidence_id in dataset.unjoined_commentary_evidence_ids
        }
        unjoined_response_ids = {
            evidence_id
            for item in skipped
            for evidence_id in (
                *item.outgoing_response_evidence_ids,
                *item.incoming_response_evidence_ids,
            )
            if evidence_id in dataset.unjoined_response_evidence_ids
        }
        active_groups.append(
            LearningDatasetMatchGroupV1(
                learning_dataset_match_group_version=LEARNING_DATASET_MATCH_GROUP_VERSION,
                match_group_id=build_learning_dataset_match_group_id_v1(
                    match_snapshot_id=snapshot_id,
                    match_id=match_id,
                    played_at=played_at,
                    player_ids=player_ids,
                    record_ids=record_ids,
                    skipped_decision_ids=skipped_ids,
                ),
                match_snapshot_id=snapshot_id,
                match_id=match_id,
                played_at=played_at,
                player_ids=player_ids,
                record_ids=record_ids,
                skipped_decision_ids=skipped_ids,
                record_count=len(records),
                skipped_decision_count=len(skipped),
                observed_decision_count=len(records) + len(skipped),
                strategy_teacher_evidence_count=sum(
                    item.match_snapshot_id == snapshot_id
                    for item in dataset.strategy_teacher_evidences
                ),
                commentary_evidence_count=len(joined_commentary),
                response_evidence_count=len(joined_responses),
                unjoined_commentary_evidence_count=len(unjoined_commentary_ids),
                unjoined_response_evidence_count=len(unjoined_response_ids),
                zero_record=not records,
            )
        )
    if (
        sum(item.record_count for item in active_groups) != dataset.record_count
        or sum(item.skipped_decision_count for item in active_groups)
        != dataset.skipped_decision_count
    ):
        raise ValueError("Active Match groups must cover every Record and skipped Decision.")
    return tuple(active_groups), tuple(inactive)


def _source_fingerprints(
    request: LearningDatasetPartitionPreparationRequestV1,
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    inactive: tuple[str, ...],
) -> tuple[str, str]:
    return (
        build_learning_dataset_partition_source_identity_fingerprint_v1(
            mode=request.mode,
            dataset=request.learning_dataset,
            active_match_groups=groups,
            inactive_current_match_snapshot_ids=inactive,
        ),
        build_learning_dataset_partition_source_content_fingerprint_v1(
            mode=request.mode,
            dataset=request.learning_dataset,
            player_catalog=request.player_catalog,
            active_match_groups=groups,
            inactive_current_match_snapshot_ids=inactive,
        ),
    )


def _plan_values(
    request: LearningDatasetPartitionPreparationRequestV1,
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    inactive: tuple[str, ...],
    *,
    status: str,
    unavailable_reason: str | None,
    source_identity_fingerprint: str,
    source_content_fingerprint: str,
    assignments=(),
    summaries=(),
    known_audit=None,
    unseen_audit=None,
    leakage_audit=None,
) -> dict[str, object]:
    return {
        "learning_dataset_partition_plan_version": LEARNING_DATASET_PARTITION_PLAN_VERSION,
        "algorithm": request.algorithm,
        "mode": request.mode,
        "status": status,
        "unavailable_reason": unavailable_reason,
        "source_identity_fingerprint": source_identity_fingerprint,
        "source_content_fingerprint": source_content_fingerprint,
        "request_fingerprint": request.request_fingerprint,
        "base_random_seed": request.base_random_seed,
        "balance_basis": "record_count",
        "secondary_balance_basis": "match_snapshot_count",
        "requested_partition_weights": request.partition_weights,
        "source_current_match_count": request.learning_dataset.current_match_count,
        "source_active_match_group_count": len(groups),
        "source_inactive_match_count": len(inactive),
        "source_record_count": request.learning_dataset.record_count,
        "source_skipped_decision_count": request.learning_dataset.skipped_decision_count,
        "assignments": assignments,
        "partition_summaries": summaries,
        "known_player_temporal_audit": known_audit,
        "unseen_player_component_audit": unseen_audit,
        "leakage_audit": leakage_audit,
        "plan_fingerprint": "0" * 64,
    }


def _serializable_plan_values(values: dict[str, object]) -> dict[str, object]:
    return {
        "learning_dataset_partition_plan_version": values[
            "learning_dataset_partition_plan_version"
        ],
        "algorithm": values["algorithm"],
        "mode": values["mode"],
        "status": values["status"],
        "unavailable_reason": values["unavailable_reason"],
        "source_identity_fingerprint": values["source_identity_fingerprint"],
        "source_content_fingerprint": values["source_content_fingerprint"],
        "request_fingerprint": values["request_fingerprint"],
        "base_random_seed": values["base_random_seed"],
        "balance_basis": values["balance_basis"],
        "secondary_balance_basis": values["secondary_balance_basis"],
        "requested_partition_weights": values["requested_partition_weights"].to_dict(),
        "source_current_match_count": values["source_current_match_count"],
        "source_active_match_group_count": values["source_active_match_group_count"],
        "source_inactive_match_count": values["source_inactive_match_count"],
        "source_record_count": values["source_record_count"],
        "source_skipped_decision_count": values["source_skipped_decision_count"],
        "assignments": [item.to_dict() for item in values["assignments"]],
        "partition_summaries": [item.to_dict() for item in values["partition_summaries"]],
        "known_player_temporal_audit": (
            None
            if values["known_player_temporal_audit"] is None
            else values["known_player_temporal_audit"].to_dict()
        ),
        "unseen_player_component_audit": (
            None
            if values["unseen_player_component_audit"] is None
            else values["unseen_player_component_audit"].to_dict()
        ),
        "leakage_audit": (
            None if values["leakage_audit"] is None else values["leakage_audit"].to_dict()
        ),
        "plan_fingerprint": values["plan_fingerprint"],
    }


def _build_unavailable_plan(
    request: LearningDatasetPartitionPreparationRequestV1,
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    inactive: tuple[str, ...],
    reason: str,
    source_identity_fingerprint: str,
    source_content_fingerprint: str,
) -> LearningDatasetPartitionPlanV1:
    values = _plan_values(
        request,
        groups,
        inactive,
        status="unavailable",
        unavailable_reason=reason,
        source_identity_fingerprint=source_identity_fingerprint,
        source_content_fingerprint=source_content_fingerprint,
    )
    values["plan_fingerprint"] = build_learning_dataset_partition_plan_fingerprint_v1(
        _serializable_plan_values(values)
    )
    return LearningDatasetPartitionPlanV1._from_validated(**values)


def _build_partition_summaries(
    request: LearningDatasetPartitionPreparationRequestV1,
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    assignments,
) -> tuple[LearningDatasetPartitionSummaryV1, ...]:
    partition_by_snapshot = {item.match_snapshot_id: item.partition for item in assignments}
    total_weight = request.partition_weights.total_weight
    weights = request.partition_weights.to_dict()
    summaries = []
    for partition in LEARNING_DATASET_PARTITIONS:
        selected = tuple(
            group for group in groups if partition_by_snapshot[group.match_snapshot_id] == partition
        )
        record_count = sum(item.record_count for item in selected)
        match_count = len(selected)
        player_ids = tuple(
            sorted({player_id for item in selected for player_id in item.player_ids})
        )
        record_target = request.learning_dataset.record_count * weights[partition]
        match_target = len(groups) * weights[partition]
        summaries.append(
            LearningDatasetPartitionSummaryV1(
                partition=partition,
                requested_weight=weights[partition],
                match_snapshot_count=match_count,
                record_count=record_count,
                skipped_decision_count=sum(item.skipped_decision_count for item in selected),
                observed_decision_count=sum(item.observed_decision_count for item in selected),
                strategy_teacher_evidence_count=sum(
                    item.strategy_teacher_evidence_count for item in selected
                ),
                commentary_evidence_count=sum(item.commentary_evidence_count for item in selected),
                response_evidence_count=sum(item.response_evidence_count for item in selected),
                distinct_player_count=len(player_ids),
                player_ids=player_ids,
                target_record_count_numerator=record_target,
                target_record_count_denominator=total_weight,
                record_count_deviation_numerator=(record_count * total_weight - record_target),
                target_match_count_numerator=match_target,
                target_match_count_denominator=total_weight,
                match_count_deviation_numerator=(match_count * total_weight - match_target),
            )
        )
    return tuple(summaries)


def _build_complete_plan(
    request: LearningDatasetPartitionPreparationRequestV1,
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    inactive: tuple[str, ...],
    algorithm_result: _PartitionAlgorithmResult,
    source_identity_fingerprint: str,
    source_content_fingerprint: str,
) -> LearningDatasetPartitionPlanV1:
    summaries = _build_partition_summaries(
        request,
        groups,
        algorithm_result.assignments,
    )
    leakage_audit = audit_learning_dataset_v2_partitions_v1(
        request,
        groups,
        inactive,
        algorithm_result.assignments,
        plan_fingerprint="0" * 64,
    )
    if leakage_audit.status != "compliant":
        raise ValueError("A complete partition Plan requires a compliant leakage audit.")
    values = _plan_values(
        request,
        groups,
        inactive,
        status="complete",
        unavailable_reason=None,
        source_identity_fingerprint=source_identity_fingerprint,
        source_content_fingerprint=source_content_fingerprint,
        assignments=algorithm_result.assignments,
        summaries=summaries,
        known_audit=algorithm_result.known_player_temporal_audit,
        unseen_audit=algorithm_result.unseen_player_component_audit,
        leakage_audit=leakage_audit,
    )
    plan_fingerprint = build_learning_dataset_partition_plan_fingerprint_v1(
        _serializable_plan_values(values)
    )
    values["plan_fingerprint"] = plan_fingerprint
    values["leakage_audit"] = replace(
        leakage_audit,
        plan_fingerprint=plan_fingerprint,
    )
    return LearningDatasetPartitionPlanV1._from_validated(**values)


def generate_learning_dataset_partition_plan_v1(
    request: LearningDatasetPartitionPreparationRequestV1,
) -> LearningDatasetPartitionPlanV1:
    """Runs one fixed group-safe assignment algorithm and one final Plan build."""
    if type(request) is not LearningDatasetPartitionPreparationRequestV1:
        raise ValueError("request must be an exact partition preparation Request.")
    request._validate()
    validate_learning_dataset_partition_request_fingerprint_v1(request)
    groups, inactive = derive_learning_dataset_match_groups_v1(
        request.learning_dataset,
        request.player_catalog,
    )
    source_identity, source_content = _source_fingerprints(request, groups, inactive)
    if request.learning_dataset.record_count == 0:
        return _build_unavailable_plan(
            request,
            groups,
            inactive,
            "dataset_has_no_records",
            source_identity,
            source_content,
        )
    if len(groups) < 3:
        return _build_unavailable_plan(
            request,
            groups,
            inactive,
            "insufficient_match_groups",
            source_identity,
            source_content,
        )
    if request.learning_dataset.record_count < 3:
        return _build_unavailable_plan(
            request,
            groups,
            inactive,
            "non_empty_record_partition_requirement_unsatisfied",
            source_identity,
            source_content,
        )
    if request.mode == "known_player":
        result = generate_temporal_known_player_match_group_assignments_v1(
            groups,
            weights=request.partition_weights,
            base_random_seed=request.base_random_seed,
            source_identity_fingerprint=source_identity,
        )
    else:
        result = generate_component_balanced_unseen_player_match_group_assignments_v1(
            groups,
            weights=request.partition_weights,
            base_random_seed=request.base_random_seed,
            source_identity_fingerprint=source_identity,
        )
    if result.status == "unavailable":
        if result.unavailable_reason is None:
            raise RuntimeError("Unavailable algorithm Result requires one reason.")
        return _build_unavailable_plan(
            request,
            groups,
            inactive,
            result.unavailable_reason,
            source_identity,
            source_content,
        )
    return _build_complete_plan(
        request,
        groups,
        inactive,
        result,
        source_identity,
        source_content,
    )


def _statistics_ids_for_records(records) -> set[str]:
    result = set()
    for record in records:
        for context in record.player_contexts:
            result.update(context.candidate_observation_ids)
            result.update(context.equivalent_observation_ids)
            result.update(context.ambiguous_observation_ids)
            if context.selected_statistics_observation_id is not None:
                result.add(context.selected_statistics_observation_id)
    return result


def _build_partitioned_view(
    request: LearningDatasetPartitionPreparationRequestV1,
    plan: LearningDatasetPartitionPlanV1,
) -> LearningDatasetPartitionedViewV1:
    dataset = request.learning_dataset
    partition_by_snapshot = {item.match_snapshot_id: item.partition for item in plan.assignments}
    slices = []
    for partition in LEARNING_DATASET_PARTITIONS:
        snapshot_ids = tuple(
            item.match_snapshot_id for item in plan.assignments if item.partition == partition
        )
        snapshot_set = set(snapshot_ids)
        records = tuple(
            item
            for item in dataset.records
            if item.source_context.match_snapshot_id in snapshot_set
        )
        skipped = tuple(
            item for item in dataset.skipped_decisions if item.match_snapshot_id in snapshot_set
        )
        statistics_ids = _statistics_ids_for_records(records)
        unjoined_commentary_ids = {
            item_id
            for item in skipped
            for item_id in item.commentary_evidence_ids
            if item_id in dataset.unjoined_commentary_evidence_ids
        }
        unjoined_response_ids = {
            item_id
            for item in skipped
            for item_id in (
                *item.outgoing_response_evidence_ids,
                *item.incoming_response_evidence_ids,
            )
            if item_id in dataset.unjoined_response_evidence_ids
        }
        slices.append(
            LearningDatasetPartitionSliceV1(
                partition=partition,
                match_snapshot_ids=snapshot_ids,
                record_ids=tuple(item.record_id for item in records),
                skipped_decision_ids=tuple(item.skipped_decision_id for item in skipped),
                statistics_observation_ids=tuple(
                    item.statistics_observation_id
                    for item in dataset.player_statistics_observations
                    if item.statistics_observation_id in statistics_ids
                ),
                strategy_teacher_evidence_ids=tuple(
                    item.strategy_teacher_evidence_id
                    for item in dataset.strategy_teacher_evidences
                    if item.match_snapshot_id in snapshot_set
                ),
                commentary_evidence_ids=tuple(
                    item.commentary_evidence_id
                    for item in dataset.commentary_evidences
                    if item.match_snapshot_id in snapshot_set
                ),
                response_evidence_ids=tuple(
                    item.response_evidence_id
                    for item in dataset.response_evidences
                    if item.match_snapshot_id in snapshot_set
                ),
                unjoined_commentary_evidence_ids=tuple(
                    item_id
                    for item_id in dataset.unjoined_commentary_evidence_ids
                    if item_id in unjoined_commentary_ids
                ),
                unjoined_response_evidence_ids=tuple(
                    item_id
                    for item_id in dataset.unjoined_response_evidence_ids
                    if item_id in unjoined_response_ids
                ),
            )
        )
    del partition_by_snapshot
    values = {
        "learning_dataset_partitioned_view_version": (LEARNING_DATASET_PARTITIONED_VIEW_VERSION),
        "partitioned_view_fingerprint": "0" * 64,
        "source_dataset_fingerprint": dataset.dataset_fingerprint,
        "plan_fingerprint": plan.plan_fingerprint,
        "learning_dataset": dataset,
        "partitions": tuple(slices),
    }
    serializable = {
        "learning_dataset_partitioned_view_version": (LEARNING_DATASET_PARTITIONED_VIEW_VERSION),
        "partitioned_view_fingerprint": "0" * 64,
        "source_dataset_fingerprint": dataset.dataset_fingerprint,
        "plan_fingerprint": plan.plan_fingerprint,
        "learning_dataset": dataset.to_dict(),
        "partitions": [item.to_dict() for item in slices],
    }
    values["partitioned_view_fingerprint"] = build_learning_dataset_partitioned_view_fingerprint_v1(
        serializable
    )
    return LearningDatasetPartitionedViewV1._from_validated(**values)


def prepare_learning_dataset_v2_partitions_v1(
    request: LearningDatasetPartitionPreparationRequestV1,
) -> LearningDatasetPartitionPreparationResultV1:
    """Builds one complete partitioned index or one reasoned unavailable Result."""
    plan = generate_learning_dataset_partition_plan_v1(request)
    view = _build_partitioned_view(request, plan) if plan.status == "complete" else None
    return LearningDatasetPartitionPreparationResultV1._from_validated(
        learning_dataset_partition_preparation_version=(
            LEARNING_DATASET_PARTITION_PREPARATION_VERSION
        ),
        status=plan.status,
        unavailable_reason=plan.unavailable_reason,
        request_fingerprint=request.request_fingerprint,
        plan=plan,
        partitioned_view=view,
    )
