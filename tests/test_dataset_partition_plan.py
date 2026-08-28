from dataclasses import FrozenInstanceError, replace

import pytest
from test_dataset_partition_audit import game_with_players
from test_historical_declarer_concession import build_concession_prefix
from test_historical_game import build_historical_input
from test_training_dataset_preparation import (
    build_preparation_input,
    build_unseen_request,
)

from skatmind.dataset_partition_plan import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
    DATASET_PARTITION_BALANCE_BASIS,
    DATASET_PARTITION_PLAN_STATUSES,
    DATASET_PARTITION_PLAN_VERSION,
    DATASET_PARTITION_UNAVAILABLE_REASONS,
    TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
    DatasetPartitionAssignment,
    build_complete_dataset_partition_plan,
    build_dataset_partition_plan_fingerprint,
    build_serializable_dataset_partition_plan,
    build_unavailable_dataset_partition_plan,
    validate_dataset_partition_plan,
)
from skatmind.training_dataset_preparation import (
    build_serializable_training_dataset_preparation_request,
    build_training_dataset_preparation_request,
    materialize_prepared_training_dataset,
)


def build_temporal_request(
    *,
    record_count: int = 3,
    weights: dict[str, int] | None = None,
):
    games = [build_historical_input() for _ in range(record_count)]
    data = build_preparation_input(games, weights=weights)
    for index, record in enumerate(data["records"], start=1):
        record["historical_game"]["played_at"] = (
            f"2026-01-{index:02d}T00:00:00Z"
        )
    return build_training_dataset_preparation_request(data)


def assignments_for(request, partitions: tuple[str, ...]):
    return tuple(
        DatasetPartitionAssignment(record.record_id, partition)
        for record, partition in zip(request.records, partitions, strict=True)
    )


def test_constants_assignments_and_plan_values_are_immutable() -> None:
    assignment = DatasetPartitionAssignment("record-1", "train")

    assert DATASET_PARTITION_PLAN_VERSION == 1
    assert DATASET_PARTITION_BALANCE_BASIS == "record_count"
    assert DATASET_PARTITION_PLAN_STATUSES == ("complete", "unavailable")
    assert len(DATASET_PARTITION_UNAVAILABLE_REASONS) == 6
    with pytest.raises(FrozenInstanceError):
        assignment.partition = "test"  # type: ignore[misc]
    with pytest.raises(ValueError, match="partition"):
        DatasetPartitionAssignment("record-1", "holdout")  # type: ignore[arg-type]


def test_complete_known_plan_has_exact_targets_audits_and_source_order() -> None:
    request = build_temporal_request(
        record_count=4,
        weights={"train": 2, "validation": 1, "test": 1},
    )
    supplied = assignments_for(
        request,
        ("train", "train", "validation", "test"),
    )

    plan = build_complete_dataset_partition_plan(
        request,
        algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
        assignments=tuple(reversed(supplied)),
    )

    assert plan.status == "complete"
    assert plan.unavailable_reason is None
    assert plan.balance_basis == "record_count"
    assert plan.source_record_count == 4
    assert plan.source_sample_count == 120
    assert plan.assignments == supplied
    assert len(plan.partition_summaries) == 3
    assert [summary.record_count for summary in plan.partition_summaries] == [2, 1, 1]
    assert [
        summary.target_record_count_numerator
        for summary in plan.partition_summaries
    ] == [8, 4, 4]
    assert [
        summary.target_record_count_denominator
        for summary in plan.partition_summaries
    ] == [4, 4, 4]
    assert [
        summary.record_count_deviation_numerator
        for summary in plan.partition_summaries
    ] == [0, 0, 0]
    assert plan.temporal_audit is not None
    assert [
        boundary.time_group_count
        for boundary in plan.temporal_audit.partition_boundaries
    ] == [2, 1, 1]
    assert plan.temporal_audit.validation_train_coverage_complete is True
    assert plan.temporal_audit.test_train_coverage_complete is True
    assert plan.temporal_audit.all_played_at_present is True
    assert plan.temporal_audit.time_group_count == 4
    assert plan.temporal_audit.strict_partition_order is True
    assert plan.temporal_audit.equal_timestamp_groups_preserved is True
    assert plan.partition_audit is not None
    assert plan.partition_audit.effective_audit_mode == "known_opponent"
    with pytest.raises(TypeError):
        plan.partition_audit.partition_summary["train"]["record_count"] = 99
    validate_dataset_partition_plan(request, plan)


def test_known_plan_rejects_missing_times_empty_or_nonchronological_blocks() -> None:
    request = build_temporal_request()
    missing_data = build_preparation_input([build_historical_input()] * 3)
    missing = build_training_dataset_preparation_request(missing_data)

    with pytest.raises(ValueError, match="requires historical_game.played_at"):
        build_complete_dataset_partition_plan(
            missing,
            algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            assignments=assignments_for(
                missing, ("train", "validation", "test")
            ),
        )
    with pytest.raises(ValueError, match="all three partitions.*non-empty"):
        build_complete_dataset_partition_plan(
            request,
            algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            assignments=assignments_for(request, ("train", "train", "test")),
        )
    with pytest.raises(ValueError, match=r"max\(train\) < min\(validation\)"):
        build_complete_dataset_partition_plan(
            request,
            algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            assignments=assignments_for(
                request, ("validation", "train", "test")
            ),
        )


def test_known_plan_groups_offset_equivalent_instants_and_rejects_splits() -> None:
    data = build_preparation_input([build_historical_input() for _ in range(4)])
    times = (
        "2026-01-01T00:00:00Z",
        "2026-01-02T00:00:00Z",
        "2026-01-02T01:00:00+01:00",
        "2026-01-03T00:00:00Z",
    )
    for record, played_at in zip(data["records"], times, strict=True):
        record["historical_game"]["played_at"] = played_at
    request = build_training_dataset_preparation_request(data)

    with pytest.raises(ValueError, match="time groups must not be split"):
        build_complete_dataset_partition_plan(
            request,
            algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            assignments=assignments_for(
                request, ("train", "validation", "test", "test")
            ),
        )


def test_known_plan_requires_validation_and_test_player_coverage_in_train() -> None:
    data = build_preparation_input(
        [
            game_with_players("A", "B", "C"),
            game_with_players("A", "B", "D"),
            game_with_players("A", "B", "E"),
        ]
    )
    for index, record in enumerate(data["records"], start=1):
        record["historical_game"]["played_at"] = (
            f"2026-01-0{index}T00:00:00Z"
        )
    request = build_training_dataset_preparation_request(data)

    with pytest.raises(ValueError, match="Uncovered Validation.*'D'.*Test.*'E'"):
        build_complete_dataset_partition_plan(
            request,
            algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            assignments=assignments_for(
                request, ("train", "validation", "test")
            ),
        )


def test_complete_unseen_plan_is_disjoint_and_zero_sample_records_participate() -> None:
    zero = build_concession_prefix()
    request_data = build_preparation_input(
        [
            game_with_players("A", "B", "C"),
            game_with_players("D", "E", "F"),
            zero,
        ],
        mode="unseen_player",
    )
    request = build_training_dataset_preparation_request(request_data)

    plan = build_complete_dataset_partition_plan(
        request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments_for(request, ("train", "validation", "test")),
    )

    assert plan.temporal_audit is None
    assert [summary.sample_count for summary in plan.partition_summaries] == [30, 30, 0]
    assert plan.source_sample_count == 60
    assert plan.partition_audit is not None
    assert plan.partition_audit.unseen_player_compliance["player_disjoint"] is True
    prepared = materialize_prepared_training_dataset(request, plan)
    assert len(prepared.training_dataset_input.records) == 3
    assert prepared.training_dataset_input.records[2].historical_game == (
        request.records[2].historical_game
    )


def test_unseen_plan_rejects_transitive_player_overlap_and_wrong_algorithm() -> None:
    data = build_preparation_input(
        [
            game_with_players("A", "B", "C"),
            game_with_players("C", "D", "E"),
            game_with_players("F", "G", "H"),
        ],
        mode="unseen_player",
    )
    request = build_training_dataset_preparation_request(data)

    with pytest.raises(ValueError, match="Conflicting players.*'C'"):
        build_complete_dataset_partition_plan(
            request,
            algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            assignments=assignments_for(
                request, ("train", "validation", "test")
            ),
        )
    with pytest.raises(ValueError, match="requires mode 'known_opponent'"):
        build_complete_dataset_partition_plan(
            request,
            algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            assignments=assignments_for(
                request, ("train", "validation", "test")
            ),
        )


def test_assignment_coverage_rejects_missing_unknown_and_duplicate_records() -> None:
    request = build_temporal_request()
    valid = assignments_for(request, ("train", "validation", "test"))

    for assignments, error in (
        (valid[:-1], "Missing record IDs"),
        (
            valid + (DatasetPartitionAssignment("unknown", "test"),),
            "Unknown record IDs",
        ),
        (valid + (valid[0],), "Duplicate assignment"),
    ):
        with pytest.raises(ValueError, match=error):
            build_complete_dataset_partition_plan(
                request,
                algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
                assignments=assignments,
            )


@pytest.mark.parametrize(
    ("mode", "algorithm", "reason"),
    [
        ("known_opponent", TEMPORAL_KNOWN_OPPONENT_ALGORITHM, "missing_played_at"),
        ("known_opponent", TEMPORAL_KNOWN_OPPONENT_ALGORITHM, "insufficient_time_groups"),
        (
            "known_opponent",
            TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            "known_opponent_train_coverage_unsatisfied",
        ),
        (
            "known_opponent",
            TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            "non_empty_partition_requirement_unsatisfied",
        ),
        (
            "unseen_player",
            COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "insufficient_player_components",
        ),
        (
            "unseen_player",
            COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "component_distribution_infeasible",
        ),
        (
            "unseen_player",
            COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "non_empty_partition_requirement_unsatisfied",
        ),
    ],
)
def test_all_mode_specific_unavailable_reasons_are_complete_contracts(
    mode: str,
    algorithm: str,
    reason: str,
) -> None:
    request = (
        build_temporal_request()
        if mode == "known_opponent"
        else build_unseen_request()
    )

    plan = build_unavailable_dataset_partition_plan(
        request,
        algorithm=algorithm,
        unavailable_reason=reason,
    )

    assert plan.status == "unavailable"
    assert plan.unavailable_reason == reason
    assert plan.assignments == ()
    assert plan.partition_summaries == ()
    assert plan.temporal_audit is None
    assert plan.partition_audit is None
    validate_dataset_partition_plan(request, plan)
    with pytest.raises(ValueError, match="Only a complete"):
        materialize_prepared_training_dataset(request, plan)


def test_unavailable_reason_mode_relationship_is_strict() -> None:
    request = build_unseen_request()

    with pytest.raises(ValueError, match="not valid for mode"):
        build_unavailable_dataset_partition_plan(
            request,
            algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            unavailable_reason="missing_played_at",
        )


def test_plan_fingerprint_and_full_validation_detect_tampering() -> None:
    request = build_unseen_request()
    assignments = assignments_for(request, ("train", "validation", "test"))
    plan = build_complete_dataset_partition_plan(
        request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
    )
    reassigned = build_complete_dataset_partition_plan(
        request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments_for(
            request, ("validation", "test", "train")
        ),
    )

    assert plan.plan_fingerprint == build_dataset_partition_plan_fingerprint(plan)
    assert plan.plan_fingerprint != reassigned.plan_fingerprint
    tampered = replace(plan, source_sample_count=plan.source_sample_count + 1)
    with pytest.raises(ValueError, match="do not match"):
        validate_dataset_partition_plan(request, tampered)
    tampered_fingerprint = replace(plan, plan_fingerprint="0" * 64)
    with pytest.raises(ValueError, match="do not match"):
        validate_dataset_partition_plan(request, tampered_fingerprint)


def test_plan_fingerprint_changes_with_seed_weight_status_and_source_content() -> None:
    games = [
        game_with_players("A", "B", "C"),
        game_with_players("D", "E", "F"),
        game_with_players("G", "H", "I"),
    ]
    baseline_data = build_preparation_input(games, mode="unseen_player")
    baseline = build_training_dataset_preparation_request(baseline_data)
    assignments = assignments_for(baseline, ("train", "validation", "test"))
    plan = build_complete_dataset_partition_plan(
        baseline,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
    )

    seed_data = build_preparation_input(games, mode="unseen_player", seed=42)
    seed_request = build_training_dataset_preparation_request(seed_data)
    seed_plan = build_complete_dataset_partition_plan(
        seed_request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
    )
    weight_data = build_preparation_input(
        games,
        mode="unseen_player",
        weights={"train": 4, "validation": 1, "test": 1},
    )
    weight_request = build_training_dataset_preparation_request(weight_data)
    weight_plan = build_complete_dataset_partition_plan(
        weight_request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
    )
    content_data = build_preparation_input(games, mode="unseen_player")
    content_data["records"][0]["historical_game"]["players"][0][
        "player_label"
    ] = "Changed label"
    content_request = build_training_dataset_preparation_request(content_data)
    content_plan = build_complete_dataset_partition_plan(
        content_request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
    )
    unavailable = build_unavailable_dataset_partition_plan(
        baseline,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        unavailable_reason="component_distribution_infeasible",
    )

    assert len(
        {
            plan.plan_fingerprint,
            seed_plan.plan_fingerprint,
            weight_plan.plan_fingerprint,
            content_plan.plan_fingerprint,
            unavailable.plan_fingerprint,
        }
    ) == 5


def test_plan_fingerprint_is_independent_of_source_and_assignment_order() -> None:
    request = build_unseen_request()
    assignments = assignments_for(request, ("train", "validation", "test"))
    first = build_complete_dataset_partition_plan(
        request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
    )
    reordered_data = build_serializable_training_dataset_preparation_request(
        request
    )
    reordered_data["records"] = list(reversed(reordered_data["records"]))
    reordered_request = build_training_dataset_preparation_request(reordered_data)
    second = build_complete_dataset_partition_plan(
        reordered_request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=tuple(reversed(assignments)),
    )

    assert second.assignments == tuple(reversed(first.assignments))
    assert second.plan_fingerprint == first.plan_fingerprint


def test_plan_serialization_is_deterministic_and_contains_no_game_cards_or_seeds() -> None:
    request = build_temporal_request()
    plan = build_complete_dataset_partition_plan(
        request,
        algorithm=TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
        assignments=assignments_for(request, ("train", "validation", "test")),
    )

    first = build_serializable_dataset_partition_plan(plan)
    second = build_serializable_dataset_partition_plan(plan)

    assert first == second
    assert first["assignments"] == [
        {"record_id": "record-001", "partition": "train"},
        {"record_id": "record-002", "partition": "validation"},
        {"record_id": "record-003", "partition": "test"},
    ]
    forbidden_keys = {
        "historical_game",
        "initial_hand",
        "skat",
        "discarded_cards",
        "declaration",
        "tricks",
        "samples",
        "features",
        "label",
        "derived_seed",
        "tie_break_key",
    }

    def collect_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(collect_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value), set())
        return set()

    assert forbidden_keys.isdisjoint(collect_keys(first))
