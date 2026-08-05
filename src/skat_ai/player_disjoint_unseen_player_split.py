import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from skat_ai.dataset_partition_objective import build_record_count_objective
from skat_ai.dataset_partition_plan import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
    CompleteDatasetPartitionPlan,
    DatasetPartitionAssignment,
    UnavailableDatasetPartitionPlan,
    _build_complete_dataset_partition_plan_from_source_facts,
    _build_unavailable_dataset_partition_plan_from_source_facts,
)
from skat_ai.dataset_partition_policy import CANONICAL_DATASET_PARTITIONS
from skat_ai.dataset_preparation_identity import (
    build_unseen_player_selection_fingerprint,
    derive_dataset_partition_tie_break_key,
)
from skat_ai.training_dataset import TrainingPartition
from skat_ai.training_dataset_preparation import (
    DatasetPreparationSourceFact,
    TrainingDatasetPreparationRequest,
    build_dataset_preparation_source_facts,
    build_serializable_training_dataset_preparation_request,
    build_training_dataset_preparation_request,
)

_PARTITION_INDEX = {
    partition: index for index, partition in enumerate(CANONICAL_DATASET_PARTITIONS)
}


@dataclass(frozen=True)
class _PlayerConnectedComponent:
    component_identity: str
    record_ids: tuple[str, ...]
    historical_game_ids: tuple[str, ...]
    player_ids: tuple[str, ...]
    source_facts: tuple[DatasetPreparationSourceFact, ...]
    record_count: int
    sample_count: int
    zero_sample_record_count: int


@dataclass(frozen=True)
class _AllocationOperation:
    kind: Literal["move", "swap"]
    component_identities: tuple[str, ...]
    source_partitions: tuple[TrainingPartition, ...]
    target_partitions: tuple[TrainingPartition, ...]
    resulting_objective: tuple[int, int, int, int, int]
    operation_identity: str


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_identity(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _build_component_identity(
    record_ids: tuple[str, ...],
    historical_game_ids: tuple[str, ...],
    player_ids: tuple[str, ...],
) -> str:
    return _sha256_identity(
        {
            "algorithm": COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "record_ids": record_ids,
            "historical_game_ids": historical_game_ids,
            "player_ids": player_ids,
        }
    )


def _build_player_connected_components(
    facts: tuple[DatasetPreparationSourceFact, ...],
) -> tuple[_PlayerConnectedComponent, ...]:
    """Builds exact transitive Record components through shared stable players."""
    parent = {fact.record_id: fact.record_id for fact in facts}

    def find(record_id: str) -> str:
        root = record_id
        while parent[root] != root:
            root = parent[root]
        while parent[record_id] != record_id:
            next_record_id = parent[record_id]
            parent[record_id] = root
            record_id = next_record_id
        return root

    def union(first_record_id: str, second_record_id: str) -> None:
        first_root = find(first_record_id)
        second_root = find(second_record_id)
        if first_root == second_root:
            return
        lower_root, higher_root = sorted((first_root, second_root))
        parent[higher_root] = lower_root

    first_record_by_player: dict[str, str] = {}
    for fact in sorted(facts, key=lambda value: (value.record_id, value.historical_game_id)):
        for player_id in fact.player_ids:
            first_record_id = first_record_by_player.setdefault(player_id, fact.record_id)
            union(first_record_id, fact.record_id)

    facts_by_root: dict[str, list[DatasetPreparationSourceFact]] = {}
    for fact in facts:
        facts_by_root.setdefault(find(fact.record_id), []).append(fact)

    components = []
    for grouped_facts in facts_by_root.values():
        stable_facts = tuple(
            sorted(
                grouped_facts,
                key=lambda value: (value.record_id, value.historical_game_id),
            )
        )
        record_ids = tuple(fact.record_id for fact in stable_facts)
        historical_game_ids = tuple(sorted(fact.historical_game_id for fact in stable_facts))
        player_ids = tuple(
            sorted({player_id for fact in stable_facts for player_id in fact.player_ids})
        )
        components.append(
            _PlayerConnectedComponent(
                component_identity=_build_component_identity(
                    record_ids,
                    historical_game_ids,
                    player_ids,
                ),
                record_ids=record_ids,
                historical_game_ids=historical_game_ids,
                player_ids=player_ids,
                source_facts=stable_facts,
                record_count=len(stable_facts),
                sample_count=sum(fact.sample_count for fact in stable_facts),
                zero_sample_record_count=sum(fact.zero_sample for fact in stable_facts),
            )
        )

    result = tuple(sorted(components, key=lambda value: value.component_identity))
    if sum(component.record_count for component in result) != len(facts):
        raise RuntimeError("Player-component construction lost a source Record.")
    component_players = [set(component.player_ids) for component in result]
    if any(
        component_players[first_index] & component_players[second_index]
        for first_index in range(len(result))
        for second_index in range(first_index + 1, len(result))
    ):
        raise RuntimeError("Player-component construction did not produce disjoint components.")
    return result


def _tie_key(
    request: TrainingDatasetPreparationRequest,
    selection_fingerprint: str,
    stable_identity: str,
) -> int:
    return derive_dataset_partition_tie_break_key(
        "unseen_player",
        request.base_random_seed,
        selection_fingerprint,
        stable_identity,
    )


def _order_components(
    request: TrainingDatasetPreparationRequest,
    components: tuple[_PlayerConnectedComponent, ...],
    selection_fingerprint: str,
) -> tuple[_PlayerConnectedComponent, ...]:
    return tuple(
        sorted(
            components,
            key=lambda component: (
                -component.record_count,
                _tie_key(
                    request,
                    selection_fingerprint,
                    component.component_identity,
                ),
                component.component_identity,
            ),
        )
    )


def _objective_for_counts(
    request: TrainingDatasetPreparationRequest,
    counts: dict[str, int],
) -> tuple[int, int, int, int, int]:
    return build_record_count_objective(
        train_count=counts["train"],
        validation_count=counts["validation"],
        test_count=counts["test"],
        source_count=len(request.records),
        weights=request.partition_weights,
    )


def _build_placement_identity(
    component: _PlayerConnectedComponent,
    partition: str,
) -> str:
    return _canonical_json(
        {
            "algorithm": COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "phase": "initial_placement",
            "component_identity": component.component_identity,
            "target_partition": partition,
        }
    )


def _build_initial_allocation(
    request: TrainingDatasetPreparationRequest,
    ordered_components: tuple[_PlayerConnectedComponent, ...],
    selection_fingerprint: str,
) -> dict[str, TrainingPartition]:
    counts = {partition: 0 for partition in CANONICAL_DATASET_PARTITIONS}
    allocation: dict[str, TrainingPartition] = {}
    component_count = len(ordered_components)
    for component_index, component in enumerate(ordered_components):
        remaining_components = component_count - component_index - 1
        candidates = []
        for partition in CANONICAL_DATASET_PARTITIONS:
            projected_counts = dict(counts)
            projected_counts[partition] += component.record_count
            remaining_empty_partitions = sum(
                projected_counts[candidate_partition] == 0
                for candidate_partition in CANONICAL_DATASET_PARTITIONS
            )
            if remaining_components < remaining_empty_partitions:
                continue
            placement_identity = _build_placement_identity(component, partition)
            candidates.append(
                (
                    _objective_for_counts(request, projected_counts),
                    _tie_key(request, selection_fingerprint, placement_identity),
                    _PARTITION_INDEX[partition],
                    partition,
                )
            )
        if not candidates:
            raise RuntimeError("Greedy component placement has no eligible partition.")
        selected_partition = min(candidates)[3]
        allocation[component.component_identity] = selected_partition
        counts[selected_partition] += component.record_count
    if any(counts[partition] == 0 for partition in CANONICAL_DATASET_PARTITIONS):
        raise RuntimeError("Greedy component placement produced an empty partition.")
    return allocation


def _build_operation_identity(
    *,
    kind: str,
    component_identities: tuple[str, ...],
    source_partitions: tuple[str, ...],
    target_partitions: tuple[str, ...],
) -> str:
    return _canonical_json(
        {
            "algorithm": COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "phase": "local_improvement",
            "operation": kind,
            "component_identities": component_identities,
            "source_partitions": source_partitions,
            "target_partitions": target_partitions,
        }
    )


def _allocation_counts(
    components: tuple[_PlayerConnectedComponent, ...],
    allocation: dict[str, TrainingPartition],
) -> dict[str, int]:
    counts = {partition: 0 for partition in CANONICAL_DATASET_PARTITIONS}
    for component in components:
        counts[allocation[component.component_identity]] += component.record_count
    return counts


def _strict_improvement_candidates(
    request: TrainingDatasetPreparationRequest,
    components: tuple[_PlayerConnectedComponent, ...],
    allocation: dict[str, TrainingPartition],
) -> tuple[_AllocationOperation, ...]:
    counts = _allocation_counts(components, allocation)
    current_objective = _objective_for_counts(request, counts)
    components_by_partition = {
        partition: tuple(
            sorted(
                (
                    component
                    for component in components
                    if allocation[component.component_identity] == partition
                ),
                key=lambda component: component.component_identity,
            )
        )
        for partition in CANONICAL_DATASET_PARTITIONS
    }
    candidates = []
    for source_partition in CANONICAL_DATASET_PARTITIONS:
        source_components = components_by_partition[source_partition]
        if len(source_components) <= 1:
            continue
        for component in source_components:
            for target_partition in CANONICAL_DATASET_PARTITIONS:
                if target_partition == source_partition:
                    continue
                projected_counts = dict(counts)
                projected_counts[source_partition] -= component.record_count
                projected_counts[target_partition] += component.record_count
                objective = _objective_for_counts(request, projected_counts)
                if objective >= current_objective:
                    continue
                identity = _build_operation_identity(
                    kind="move",
                    component_identities=(component.component_identity,),
                    source_partitions=(source_partition,),
                    target_partitions=(target_partition,),
                )
                candidates.append(
                    _AllocationOperation(
                        kind="move",
                        component_identities=(component.component_identity,),
                        source_partitions=(source_partition,),
                        target_partitions=(target_partition,),
                        resulting_objective=objective,
                        operation_identity=identity,
                    )
                )

    for first_index, first_partition in enumerate(CANONICAL_DATASET_PARTITIONS):
        for second_partition in CANONICAL_DATASET_PARTITIONS[first_index + 1 :]:
            for first_component in components_by_partition[first_partition]:
                for second_component in components_by_partition[second_partition]:
                    projected_counts = dict(counts)
                    projected_counts[first_partition] += (
                        second_component.record_count - first_component.record_count
                    )
                    projected_counts[second_partition] += (
                        first_component.record_count - second_component.record_count
                    )
                    objective = _objective_for_counts(request, projected_counts)
                    if objective >= current_objective:
                        continue
                    identity = _build_operation_identity(
                        kind="swap",
                        component_identities=(
                            first_component.component_identity,
                            second_component.component_identity,
                        ),
                        source_partitions=(first_partition, second_partition),
                        target_partitions=(second_partition, first_partition),
                    )
                    candidates.append(
                        _AllocationOperation(
                            kind="swap",
                            component_identities=(
                                first_component.component_identity,
                                second_component.component_identity,
                            ),
                            source_partitions=(first_partition, second_partition),
                            target_partitions=(second_partition, first_partition),
                            resulting_objective=objective,
                            operation_identity=identity,
                        )
                    )
    return tuple(candidates)


def _improve_allocation(
    request: TrainingDatasetPreparationRequest,
    components: tuple[_PlayerConnectedComponent, ...],
    allocation: dict[str, TrainingPartition],
    selection_fingerprint: str,
) -> dict[str, TrainingPartition]:
    improved = dict(allocation)
    while True:
        candidates = _strict_improvement_candidates(request, components, improved)
        if not candidates:
            return improved
        operation = min(
            candidates,
            key=lambda candidate: (
                candidate.resulting_objective,
                _tie_key(
                    request,
                    selection_fingerprint,
                    candidate.operation_identity,
                ),
                candidate.operation_identity,
            ),
        )
        for component_identity, target_partition in zip(
            operation.component_identities,
            operation.target_partitions,
            strict=True,
        ):
            improved[component_identity] = target_partition


def _build_assignments(
    request: TrainingDatasetPreparationRequest,
    components: tuple[_PlayerConnectedComponent, ...],
    allocation: dict[str, TrainingPartition],
) -> tuple[DatasetPartitionAssignment, ...]:
    partition_by_record_id = {
        record_id: allocation[component.component_identity]
        for component in components
        for record_id in component.record_ids
    }
    return tuple(
        DatasetPartitionAssignment(
            record_id=record.record_id,
            partition=partition_by_record_id[record.record_id],
        )
        for record in request.records
    )


def generate_component_balanced_unseen_player_dataset_partition_plan(
    request: TrainingDatasetPreparationRequest,
) -> CompleteDatasetPartitionPlan | UnavailableDatasetPartitionPlan:
    """Generates a deterministic locally balanced player-disjoint split."""
    if not isinstance(request, TrainingDatasetPreparationRequest):
        raise ValueError("request must be a TrainingDatasetPreparationRequest value.")
    if request.mode != "unseen_player":
        raise ValueError(
            "component_balanced_unseen_player_v1 requires request.mode 'unseen_player'."
        )
    try:
        validated_request = build_training_dataset_preparation_request(
            build_serializable_training_dataset_preparation_request(request)
        )
    except (AttributeError, KeyError, TypeError) as error:
        raise ValueError("request does not satisfy the preparation contract.") from error
    if validated_request != request:
        raise ValueError("request does not satisfy the preparation contract.")

    facts = build_dataset_preparation_source_facts(request)
    components = _build_player_connected_components(facts)
    if len(components) < 3:
        return _build_unavailable_dataset_partition_plan_from_source_facts(
            request,
            algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            unavailable_reason="insufficient_player_components",
            source_facts=facts,
        )

    selection_fingerprint = build_unseen_player_selection_fingerprint(request, facts)
    ordered_components = _order_components(
        request,
        components,
        selection_fingerprint,
    )
    allocation = _build_initial_allocation(
        request,
        ordered_components,
        selection_fingerprint,
    )
    allocation = _improve_allocation(
        request,
        components,
        allocation,
        selection_fingerprint,
    )
    if _strict_improvement_candidates(request, components, allocation):
        raise RuntimeError("Unseen-player allocation did not reach a local optimum.")
    assignments = _build_assignments(request, components, allocation)
    return _build_complete_dataset_partition_plan_from_source_facts(
        request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
        source_facts=facts,
    )
