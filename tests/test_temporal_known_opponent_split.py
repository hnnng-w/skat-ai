from dataclasses import replace

import pytest
from test_dataset_partition_audit import game_with_players
from test_historical_declarer_concession import build_concession_prefix
from test_historical_game import build_historical_input, rebuild_historical_suffix
from test_training_dataset_preparation import build_preparation_input

import skatmind.dataset_partition_plan as partition_plan_module
import skatmind.temporal_known_opponent_split as split_module
import skatmind.training_dataset_preparation as preparation_module
from skatmind.dataset_partition_audit import (
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
)
from skatmind.dataset_partition_plan import (
    TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
    build_serializable_dataset_partition_plan,
    validate_dataset_partition_plan,
)
from skatmind.training_dataset_preparation import (
    DatasetPartitionWeights,
    build_dataset_preparation_source_facts,
    build_serializable_training_dataset_preparation_request,
    build_training_dataset_preparation_request,
    materialize_prepared_training_dataset,
)


def build_request(
    times: tuple[str | None, ...],
    *,
    games: list[dict] | None = None,
    weights: dict[str, int] | None = None,
    seed: int = 41,
    mode: str = "known_opponent",
):
    games = games or [build_historical_input() for _ in times]
    data = build_preparation_input(games, mode=mode, weights=weights, seed=seed)
    for record, played_at in zip(data["records"], times, strict=True):
        if played_at is not None:
            record["historical_game"]["played_at"] = played_at
    return build_training_dataset_preparation_request(data)


def mapping(plan) -> dict[str, str]:
    return {
        assignment.record_id: assignment.partition
        for assignment in plan.assignments
    }


def boundaries(plan) -> tuple[tuple[str, str], ...]:
    assert plan.temporal_audit is not None
    return tuple(
        (boundary.minimum_played_at, boundary.maximum_played_at)
        for boundary in plan.temporal_audit.partition_boundaries
    )


def test_entry_point_requires_typed_known_opponent_request() -> None:
    with pytest.raises(ValueError, match="TrainingDatasetPreparationRequest"):
        split_module.generate_temporal_known_opponent_dataset_partition_plan({})  # type: ignore[arg-type]

    unseen = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
        ),
        mode="unseen_player",
    )
    with pytest.raises(ValueError, match="requires request.mode 'known_opponent'"):
        split_module.generate_temporal_known_opponent_dataset_partition_plan(unseen)

    malformed = replace(unseen, mode="known_opponent", records=())
    with pytest.raises(ValueError, match="non-empty array"):
        split_module.generate_temporal_known_opponent_dataset_partition_plan(malformed)

    valid = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
        )
    )
    malformed_game = replace(
        valid.records[0].historical_game,
        played_at="not-rfc3339",
    )
    malformed_record = replace(valid.records[0], historical_game=malformed_game)
    malformed = replace(valid, records=(malformed_record, *valid.records[1:]))
    with pytest.raises(ValueError, match="RFC 3339"):
        split_module.generate_temporal_known_opponent_dataset_partition_plan(malformed)


def test_unavailable_reason_precedence_and_selector_reason_set() -> None:
    missing = build_request((None, None, "2026-01-03T00:00:00Z"))
    insufficient = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-01T01:00:00+01:00",
            "2026-01-02T00:00:00Z",
        )
    )
    uncovered = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
        ),
        games=[
            game_with_players("A", "B", "C"),
            game_with_players("A", "B", "D"),
            game_with_players("A", "B", "E"),
        ],
    )

    plans = [
        split_module.generate_temporal_known_opponent_dataset_partition_plan(request)
        for request in (missing, insufficient, uncovered)
    ]

    assert [plan.unavailable_reason for plan in plans] == [
        "missing_played_at",
        "insufficient_time_groups",
        "known_opponent_train_coverage_unsatisfied",
    ]
    assert all(plan.status == "unavailable" for plan in plans)
    assert all(
        plan.unavailable_reason != "non_empty_partition_requirement_unsatisfied"
        for plan in plans
    )
    for request, plan in zip((missing, insufficient, uncovered), plans, strict=True):
        validate_dataset_partition_plan(request, plan)
        assert plan.assignments == ()
        assert plan.partition_summaries == ()
        assert plan.temporal_audit is None
        assert plan.partition_audit is None
        assert plan.plan_fingerprint == (
            split_module.generate_temporal_known_opponent_dataset_partition_plan(
                request
            ).plan_fingerprint
        )


@pytest.mark.parametrize(
    "games",
    [
        [
            game_with_players("A", "B", "C"),
            game_with_players("A", "B", "D"),
            game_with_players("A", "B", "C"),
        ],
        [
            game_with_players("A", "B", "C"),
            game_with_players("A", "B", "C"),
            game_with_players("A", "B", "E"),
        ],
    ],
)
def test_validation_only_and_test_only_coverage_failures_are_unavailable(
    games: list[dict],
) -> None:
    request = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
        ),
        games=games,
    )

    plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(
        request
    )

    assert plan.unavailable_reason == "known_opponent_train_coverage_unsatisfied"


def test_time_groups_use_parsed_instants_stable_ids_and_every_valid_cut() -> None:
    request = build_request(
        (
            "2026-01-03T00:00:00Z",
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-02T01:00:00+01:00",
            "2026-01-04T00:00:00Z",
        )
    )
    facts = build_dataset_preparation_source_facts(request)
    groups = split_module._build_time_groups(facts)
    candidates = split_module._enumerate_valid_candidates(
        groups, request.partition_weights
    )

    assert [group.record_count for group in groups] == [1, 2, 1, 1]
    assert [fact.record_id for fact in groups[1].facts] == [
        "record-003",
        "record-004",
    ]
    assert [
        (candidate.train_cut, candidate.validation_cut)
        for candidate in candidates
    ] == [(1, 2), (1, 3), (2, 3)]


def test_selected_assignments_are_strict_contiguous_unsplit_time_blocks() -> None:
    request = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-02T01:00:00+01:00",
            "2026-01-03T00:00:00Z",
        )
    )

    plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(
        request
    )

    assert plan.status == "complete"
    assert [assignment.partition for assignment in plan.assignments] == [
        "train",
        "validation",
        "validation",
        "test",
    ]
    assert boundaries(plan) == (
        ("2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        ("2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z"),
        ("2026-01-03T00:00:00Z", "2026-01-03T00:00:00Z"),
    )


def test_zero_sample_train_record_supplies_player_coverage() -> None:
    request = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
        ),
        games=[
            build_concession_prefix(),
            build_historical_input(),
            build_historical_input(game_type="null"),
        ],
    )

    plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(
        request
    )

    assert plan.status == "complete"
    assert [summary.sample_count for summary in plan.partition_summaries] == [0, 30, 30]
    assert plan.source_sample_count == 60
    assert plan.temporal_audit is not None
    assert plan.temporal_audit.validation_train_coverage_complete is True
    assert plan.temporal_audit.test_train_coverage_complete is True
    prepared = materialize_prepared_training_dataset(request, plan)
    assert prepared.training_dataset_input.records[0].historical_game == (
        request.records[0].historical_game
    )


@pytest.mark.parametrize(
    ("weights", "expected_mapping", "expected_metrics"),
    [
        (
            {"train": 1, "validation": 1, "test": 2},
            ("train", "validation", "test", "test"),
            (0, 0, 0, 0, 0),
        ),
        (
            {"train": 2, "validation": 1, "test": 2},
            ("train", "train", "validation", "test"),
            (6, 3, 2, 1, 3),
        ),
        (
            {"train": 1, "validation": 1, "test": 1},
            ("train", "validation", "test", "test"),
            (4, 2, 1, 1, 2),
        ),
    ],
)
def test_exact_objective_selects_total_train_and_validation_levels(
    weights: dict[str, int],
    expected_mapping: tuple[str, ...],
    expected_metrics: tuple[int, int, int, int, int],
) -> None:
    request = build_request(
        tuple(f"2026-01-0{day}T00:00:00Z" for day in range(1, 5)),
        weights=weights,
    )

    plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(
        request
    )
    counts = tuple(summary.record_count for summary in plan.partition_summaries)
    metrics = split_module._build_record_count_objective(
        train_count=counts[0],
        validation_count=counts[1],
        test_count=counts[2],
        source_count=4,
        weights=request.partition_weights,
    )

    assert tuple(assignment.partition for assignment in plan.assignments) == expected_mapping
    assert metrics == expected_metrics


def test_objective_calculates_redundant_maximum_and_test_levels_exactly() -> None:
    weights = DatasetPartitionWeights(train=2, validation=3, test=5)
    objectives = {
        counts: split_module._build_record_count_objective(
            train_count=counts[0],
            validation_count=counts[1],
            test_count=counts[2],
            source_count=sum(counts),
            weights=weights,
        )
        for counts in ((1, 2, 5), (2, 3, 3), (4, 1, 3))
    }

    for total, maximum, train, validation, test in objectives.values():
        assert total == maximum * 2
        assert test == total - train - validation


def test_tie_keys_are_derived_only_for_exact_five_metric_ties(monkeypatch) -> None:
    calls = []
    original = split_module.derive_dataset_partition_tie_break_key

    def counted(*args):
        calls.append(args)
        return original(*args)

    monkeypatch.setattr(split_module, "derive_dataset_partition_tie_break_key", counted)
    unique = build_request(
        tuple(f"2026-01-0{day}T00:00:00Z" for day in range(1, 5)),
        weights={"train": 1, "validation": 1, "test": 2},
    )
    split_module.generate_temporal_known_opponent_dataset_partition_plan(unique)
    assert calls == []

    tied = build_request(
        tuple(f"2026-01-0{day}T00:00:00Z" for day in range(1, 5)),
        weights={"train": 2, "validation": 3, "test": 3},
    )
    split_module.generate_temporal_known_opponent_dataset_partition_plan(tied)
    assert len(calls) == 2
    assert all(call[0] == "known_opponent" for call in calls)
    assert all(TEMPORAL_KNOWN_OPPONENT_ALGORITHM in call[3] for call in calls)


def test_equal_tie_keys_fall_back_to_canonical_utc_boundaries(monkeypatch) -> None:
    request = build_request(
        tuple(f"2026-01-0{day}T00:00:00Z" for day in range(1, 5)),
        weights={"train": 2, "validation": 3, "test": 3},
    )
    monkeypatch.setattr(
        split_module,
        "derive_dataset_partition_tie_break_key",
        lambda *args: 7,
    )

    plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(
        request
    )

    assert tuple(assignment.partition for assignment in plan.assignments) == (
        "train",
        "validation",
        "test",
        "test",
    )


def test_seed_changes_only_exact_ties_and_always_changes_plan_fingerprint() -> None:
    times = tuple(f"2026-01-0{day}T00:00:00Z" for day in range(1, 5))
    unique_requests = [
        build_request(
            times,
            weights={"train": 1, "validation": 1, "test": 2},
            seed=seed,
        )
        for seed in (1, 999)
    ]
    unique_plans = [
        split_module.generate_temporal_known_opponent_dataset_partition_plan(request)
        for request in unique_requests
    ]
    assert mapping(unique_plans[0]) == mapping(unique_plans[1])
    assert unique_plans[0].plan_fingerprint != unique_plans[1].plan_fingerprint

    tied_plans = {}
    for seed in range(100):
        request = build_request(
            times,
            weights={"train": 2, "validation": 3, "test": 3},
            seed=seed,
        )
        plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(
            request
        )
        tied_plans.setdefault(tuple(mapping(plan).values()), plan)
        if len(tied_plans) == 2:
            break
    assert len(tied_plans) == 2

    repeated_request = build_request(
        times,
        weights={"train": 2, "validation": 3, "test": 3},
        seed=41,
    )
    assert split_module.generate_temporal_known_opponent_dataset_partition_plan(
        repeated_request
    ) == split_module.generate_temporal_known_opponent_dataset_partition_plan(
        repeated_request
    )


def test_source_order_independence_preserves_mapping_proofs_and_fingerprint() -> None:
    request = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
            "2026-01-04T00:00:00Z",
        ),
        weights={"train": 2, "validation": 1, "test": 1},
    )
    reordered_data = build_serializable_training_dataset_preparation_request(request)
    reordered_data["records"] = [
        reordered_data["records"][index] for index in (2, 4, 0, 3, 1)
    ]
    reordered = build_training_dataset_preparation_request(reordered_data)

    first = split_module.generate_temporal_known_opponent_dataset_partition_plan(request)
    second = split_module.generate_temporal_known_opponent_dataset_partition_plan(reordered)

    assert mapping(first) == mapping(second)
    assert boundaries(first) == boundaries(second)
    assert first.partition_summaries == second.partition_summaries
    assert first.temporal_audit == second.temporal_audit
    assert first.partition_audit == second.partition_audit
    assert first.plan_fingerprint == second.plan_fingerprint
    assert [assignment.record_id for assignment in second.assignments] == [
        record.record_id for record in reordered.records
    ]
    prepared = materialize_prepared_training_dataset(reordered, second)
    assert [
        record.record_id for record in prepared.training_dataset_input.records
    ] == [record.record_id for record in reordered.records]
    assert build_serializable_dataset_partition_audit(
        audit_training_dataset_partitions(
            prepared.training_dataset_input,
            "known_opponent",
            canonical_source_order=True,
        )
    ) == build_serializable_dataset_partition_audit(second.partition_audit)


def test_selection_isolated_from_content_outcome_samples_labels_and_notes() -> None:
    times = tuple(f"2026-01-0{day}T00:00:00Z" for day in range(1, 5))
    baseline = build_request(times)
    changed_games = [
        rebuild_historical_suffix(build_historical_input(), 5),
        build_historical_input(game_type="null"),
        build_concession_prefix(completed_trick_count=4, current_trick_card_count=2),
        build_concession_prefix(),
    ]
    changed_data = build_preparation_input(changed_games)
    for index, (record, played_at) in enumerate(
        zip(changed_data["records"], times, strict=True)
    ):
        record["historical_game"]["played_at"] = played_at
        record["historical_game"]["players"][0]["player_label"] = f"Changed {index}"
        record["provenance"]["notes"] = f"Changed note {index}"
    changed = build_training_dataset_preparation_request(changed_data)

    assert baseline.records[0].historical_game.tricks != changed.records[0].historical_game.tricks
    assert baseline.records[1].historical_game.declaration != (
        changed.records[1].historical_game.declaration
    )
    baseline_outcome = preparation_module.build_historical_game_summary(
        baseline.records[1].historical_game
    )
    changed_outcome = preparation_module.build_historical_game_summary(
        changed.records[1].historical_game
    )
    assert baseline_outcome["winner"] != changed_outcome["winner"]
    assert baseline_outcome["final_settlement_summary"] != (
        changed_outcome["final_settlement_summary"]
    )
    assert baseline.records[0].historical_game.players[0].player_label != (
        changed.records[0].historical_game.players[0].player_label
    )
    assert baseline.records[0].provenance.notes != changed.records[0].provenance.notes

    first = split_module.generate_temporal_known_opponent_dataset_partition_plan(baseline)
    second = split_module.generate_temporal_known_opponent_dataset_partition_plan(changed)

    assert first.source_identity_fingerprint == second.source_identity_fingerprint
    assert mapping(first) == mapping(second)
    assert boundaries(first) == boundaries(second)
    assert first.source_sample_count != second.source_sample_count
    assert first.source_content_fingerprint != second.source_content_fingerprint
    assert first.plan_fingerprint != second.plan_fingerprint


def test_complete_plan_validates_audits_and_materializes_losslessly() -> None:
    request = build_request(
        (
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
        )
    )

    plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(request)
    validate_dataset_partition_plan(request, plan)
    prepared = materialize_prepared_training_dataset(request, plan)
    serialized = build_serializable_dataset_partition_plan(plan)

    assert plan.algorithm == TEMPORAL_KNOWN_OPPONENT_ALGORITHM
    assert plan.partition_audit is not None
    assert plan.partition_audit.compliance_status == "compliant"
    assert prepared.partition_audit == plan.partition_audit
    assert [record.historical_game for record in prepared.training_dataset_input.records] == [
        record.historical_game for record in request.records
    ]
    assert "tie_break_key" not in str(serialized)


def test_candidate_scan_replays_sources_and_builds_final_plan_only_once(monkeypatch) -> None:
    request = build_request(
        tuple(f"2026-01-{day:02d}T00:00:00Z" for day in range(1, 9))
    )
    counts = {"summary": 0, "snapshots": 0, "materialization": 0, "audit": 0}
    original_summary = preparation_module.build_historical_game_summary
    original_snapshots = preparation_module.build_historical_decision_snapshots
    original_materialization = partition_plan_module._build_materialized_training_dataset
    original_audit = partition_plan_module.audit_training_dataset_partitions

    def counted_summary(*args, **kwargs):
        counts["summary"] += 1
        return original_summary(*args, **kwargs)

    def counted_snapshots(*args, **kwargs):
        counts["snapshots"] += 1
        return original_snapshots(*args, **kwargs)

    def counted_materialization(*args, **kwargs):
        counts["materialization"] += 1
        return original_materialization(*args, **kwargs)

    def counted_audit(*args, **kwargs):
        counts["audit"] += 1
        return original_audit(*args, **kwargs)

    monkeypatch.setattr(preparation_module, "build_historical_game_summary", counted_summary)
    monkeypatch.setattr(
        preparation_module,
        "build_historical_decision_snapshots",
        counted_snapshots,
    )
    monkeypatch.setattr(
        partition_plan_module,
        "_build_materialized_training_dataset",
        counted_materialization,
    )
    monkeypatch.setattr(
        partition_plan_module,
        "audit_training_dataset_partitions",
        counted_audit,
    )

    plan = split_module.generate_temporal_known_opponent_dataset_partition_plan(request)

    assert plan.status == "complete"
    assert counts == {
        "summary": len(request.records),
        "snapshots": len(request.records),
        "materialization": 1,
        "audit": 1,
    }
