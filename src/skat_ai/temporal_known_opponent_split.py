import json
from dataclasses import dataclass
from datetime import UTC, datetime

from skat_ai.dataset_partition_objective import build_record_count_objective
from skat_ai.dataset_partition_plan import (
    TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
    CompleteDatasetPartitionPlan,
    DatasetPartitionAssignment,
    UnavailableDatasetPartitionPlan,
    _build_complete_dataset_partition_plan_from_source_facts,
    _build_unavailable_dataset_partition_plan_from_source_facts,
)
from skat_ai.dataset_preparation_identity import (
    build_source_identity_fingerprint,
    derive_dataset_partition_tie_break_key,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime
from skat_ai.training_dataset_preparation import (
    DatasetPartitionWeights,
    DatasetPreparationSourceFact,
    TrainingDatasetPreparationRequest,
    build_dataset_preparation_source_facts,
    build_serializable_training_dataset_preparation_request,
    build_training_dataset_preparation_request,
)


@dataclass(frozen=True)
class _TimeGroup:
    instant: datetime
    canonical_played_at: str
    facts: tuple[DatasetPreparationSourceFact, ...]
    player_ids: frozenset[str]

    @property
    def record_count(self) -> int:
        return len(self.facts)


@dataclass(frozen=True)
class _Candidate:
    train_cut: int
    validation_cut: int
    train_count: int
    validation_count: int
    test_count: int
    objective: tuple[int, int, int, int, int]
    train_boundary_utc: str
    validation_boundary_utc: str


def _canonical_instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _build_time_groups(
    facts: tuple[DatasetPreparationSourceFact, ...],
) -> tuple[_TimeGroup, ...]:
    facts_by_instant: dict[datetime, list[DatasetPreparationSourceFact]] = {}
    for fact in facts:
        if fact.played_at is None:
            raise ValueError("Time groups require played_at on every source fact.")
        instant = parse_rfc3339_datetime(
            fact.played_at,
            f"record_id '{fact.record_id}' historical_game.played_at",
        )
        facts_by_instant.setdefault(instant, []).append(fact)

    return tuple(
        _TimeGroup(
            instant=instant,
            canonical_played_at=_canonical_instant(instant),
            facts=tuple(
                sorted(
                    grouped_facts,
                    key=lambda fact: (fact.record_id, fact.historical_game_id),
                )
            ),
            player_ids=frozenset(
                player_id for fact in grouped_facts for player_id in fact.player_ids
            ),
        )
        for instant, grouped_facts in sorted(facts_by_instant.items())
    )


def _build_record_count_objective(
    *,
    train_count: int,
    validation_count: int,
    test_count: int,
    source_count: int,
    weights: DatasetPartitionWeights,
) -> tuple[int, int, int, int, int]:
    return build_record_count_objective(
        train_count=train_count,
        validation_count=validation_count,
        test_count=test_count,
        source_count=source_count,
        weights=weights,
    )


def _enumerate_valid_candidates(
    groups: tuple[_TimeGroup, ...],
    weights: DatasetPartitionWeights,
) -> tuple[_Candidate, ...]:
    group_count = len(groups)
    source_count = sum(group.record_count for group in groups)
    cumulative_record_counts = [0]
    cumulative_player_ids: list[frozenset[str]] = [frozenset()]
    for group in groups:
        cumulative_record_counts.append(cumulative_record_counts[-1] + group.record_count)
        cumulative_player_ids.append(cumulative_player_ids[-1] | group.player_ids)

    suffix_player_ids: list[frozenset[str]] = [frozenset()] * (group_count + 1)
    for group_index in range(group_count - 1, -1, -1):
        suffix_player_ids[group_index] = (
            suffix_player_ids[group_index + 1] | groups[group_index].player_ids
        )

    candidates = []
    for train_cut in range(1, group_count - 1):
        train_players = cumulative_player_ids[train_cut]
        if not suffix_player_ids[train_cut] <= train_players:
            continue
        train_count = cumulative_record_counts[train_cut]
        for validation_cut in range(train_cut + 1, group_count):
            validation_count = cumulative_record_counts[validation_cut] - train_count
            test_count = source_count - cumulative_record_counts[validation_cut]
            candidates.append(
                _Candidate(
                    train_cut=train_cut,
                    validation_cut=validation_cut,
                    train_count=train_count,
                    validation_count=validation_count,
                    test_count=test_count,
                    objective=_build_record_count_objective(
                        train_count=train_count,
                        validation_count=validation_count,
                        test_count=test_count,
                        source_count=source_count,
                        weights=weights,
                    ),
                    train_boundary_utc=groups[train_cut - 1].canonical_played_at,
                    validation_boundary_utc=groups[validation_cut - 1].canonical_played_at,
                )
            )
    return tuple(candidates)


def _build_candidate_stable_identity(candidate: _Candidate) -> str:
    return json.dumps(
        {
            "algorithm": TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            "train_end": candidate.train_boundary_utc,
            "validation_end": candidate.validation_boundary_utc,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _select_candidate(
    request: TrainingDatasetPreparationRequest,
    candidates: tuple[_Candidate, ...],
) -> _Candidate | None:
    if not candidates:
        return None
    best_objective = min(candidate.objective for candidate in candidates)
    tied_candidates = tuple(
        candidate for candidate in candidates if candidate.objective == best_objective
    )
    if len(tied_candidates) == 1:
        return tied_candidates[0]

    source_identity_fingerprint = build_source_identity_fingerprint(request)
    return min(
        tied_candidates,
        key=lambda candidate: (
            derive_dataset_partition_tie_break_key(
                "known_opponent",
                request.base_random_seed,
                source_identity_fingerprint,
                _build_candidate_stable_identity(candidate),
            ),
            candidate.train_boundary_utc,
            candidate.validation_boundary_utc,
        ),
    )


def _build_assignments(
    request: TrainingDatasetPreparationRequest,
    groups: tuple[_TimeGroup, ...],
    candidate: _Candidate,
) -> tuple[DatasetPartitionAssignment, ...]:
    partitions_by_record_id = {
        fact.record_id: partition
        for partition, selected_groups in (
            ("train", groups[: candidate.train_cut]),
            (
                "validation",
                groups[candidate.train_cut : candidate.validation_cut],
            ),
            ("test", groups[candidate.validation_cut :]),
        )
        for group in selected_groups
        for fact in group.facts
    }
    return tuple(
        DatasetPartitionAssignment(
            record_id=record.record_id,
            partition=partitions_by_record_id[record.record_id],
        )
        for record in request.records
    )


def _build_unavailable_plan(
    request: TrainingDatasetPreparationRequest,
    facts: tuple[DatasetPreparationSourceFact, ...],
    reason: str,
) -> UnavailableDatasetPartitionPlan:
    return _build_unavailable_dataset_partition_plan_from_source_facts(
        request,
        algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
        unavailable_reason=reason,
        source_facts=facts,
    )


def generate_temporal_known_opponent_dataset_partition_plan(
    request: TrainingDatasetPreparationRequest,
) -> CompleteDatasetPartitionPlan | UnavailableDatasetPartitionPlan:
    """Generates the exact deterministic version-1 temporal Known-opponent split."""
    if not isinstance(request, TrainingDatasetPreparationRequest):
        raise ValueError("request must be a TrainingDatasetPreparationRequest value.")
    if request.mode != "known_opponent":
        raise ValueError("temporal_known_opponent_v1 requires request.mode 'known_opponent'.")
    try:
        validated_request = build_training_dataset_preparation_request(
            build_serializable_training_dataset_preparation_request(request)
        )
    except (AttributeError, KeyError, TypeError) as error:
        raise ValueError("request does not satisfy the preparation contract.") from error
    if validated_request != request:
        raise ValueError("request does not satisfy the preparation contract.")

    facts = build_dataset_preparation_source_facts(request)
    if any(fact.played_at is None for fact in facts):
        return _build_unavailable_plan(request, facts, "missing_played_at")

    groups = _build_time_groups(facts)
    if len(groups) < 3:
        return _build_unavailable_plan(request, facts, "insufficient_time_groups")

    candidate = _select_candidate(
        request,
        _enumerate_valid_candidates(groups, request.partition_weights),
    )
    if candidate is None:
        return _build_unavailable_plan(
            request,
            facts,
            "known_opponent_train_coverage_unsatisfied",
        )

    assignments = _build_assignments(request, groups, candidate)
    return _build_complete_dataset_partition_plan_from_source_facts(
        request,
        algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
        assignments=assignments,
        source_facts=facts,
    )
