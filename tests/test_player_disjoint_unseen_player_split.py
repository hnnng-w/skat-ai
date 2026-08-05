import hashlib
import json
from dataclasses import replace

import pytest
from test_dataset_partition_audit import (
    game_with_players,
    rename_players,
)
from test_historical_declarer_concession import build_concession_prefix
from test_historical_game import build_historical_input, rebuild_historical_suffix
from test_training_dataset_preparation import build_preparation_input

import skat_ai.dataset_partition_plan as partition_plan_module
import skat_ai.player_disjoint_unseen_player_split as split_module
import skat_ai.training_dataset_preparation as preparation_module
from skat_ai.dataset_partition_objective import build_record_count_objective
from skat_ai.dataset_partition_plan import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
    build_complete_dataset_partition_plan,
    build_serializable_dataset_partition_plan,
    validate_dataset_partition_plan,
)
from skat_ai.dataset_preparation_identity import (
    build_source_identity_fingerprint,
    build_unseen_player_selection_fingerprint,
)
from skat_ai.training_dataset_preparation import (
    build_dataset_preparation_source_facts,
    build_serializable_training_dataset_preparation_request,
    build_training_dataset_preparation_request,
    materialize_prepared_training_dataset,
)


def build_request(
    component_sizes: tuple[int, ...],
    *,
    weights: dict[str, int] | None = None,
    seed: int = 41,
):
    games = []
    for component_index, component_size in enumerate(component_sizes):
        for member_index in range(component_size):
            games.append(
                game_with_players(
                    f"shared-{component_index}",
                    f"player-{component_index}-{member_index}-b",
                    f"player-{component_index}-{member_index}-c",
                )
            )
    return build_training_dataset_preparation_request(
        build_preparation_input(
            games,
            mode="unseen_player",
            weights=weights,
            seed=seed,
        )
    )


def mapping(plan) -> dict[str, str]:
    return {assignment.record_id: assignment.partition for assignment in plan.assignments}


def rename_all_stable_players(game: dict, player_ids: tuple[str, str, str]) -> dict:
    replacements = dict(zip(("player-a", "player-b", "player-c"), player_ids, strict=True))

    def replace_value(value):
        if isinstance(value, dict):
            return {key: replace_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace_value(item) for item in value]
        if isinstance(value, str):
            return replacements.get(value, value)
        return value

    return replace_value(game)


def fake_components(sizes: tuple[int, ...]):
    return tuple(
        split_module._PlayerConnectedComponent(
            component_identity=str(index),
            record_ids=(),
            historical_game_ids=(),
            player_ids=(),
            source_facts=(),
            record_count=size,
            sample_count=0,
            zero_sample_record_count=0,
        )
        for index, size in enumerate(sizes)
    )


def independent_component_record_ids(request) -> set[frozenset[str]]:
    players_by_record = {
        record.record_id: {player.player_id for player in record.historical_game.players}
        for record in request.records
    }
    remaining = set(players_by_record)
    components = set()
    while remaining:
        pending = [min(remaining)]
        selected = set()
        while pending:
            record_id = pending.pop()
            if record_id in selected:
                continue
            selected.add(record_id)
            remaining.discard(record_id)
            connected = {
                candidate_id
                for candidate_id in remaining
                if players_by_record[record_id] & players_by_record[candidate_id]
            }
            pending.extend(sorted(connected))
        components.add(frozenset(selected))
    return components


def independent_objective(request, counts: dict[str, int]):
    total_weight = request.partition_weights.total_weight
    deviations = (
        counts["train"] * total_weight - len(request.records) * request.partition_weights.train,
        counts["validation"] * total_weight
        - len(request.records) * request.partition_weights.validation,
        counts["test"] * total_weight - len(request.records) * request.partition_weights.test,
    )
    absolute = tuple(abs(value) for value in deviations)
    return (sum(absolute), max(absolute), *absolute)


def assert_no_independent_move_or_swap_improves(request, plan) -> None:
    assignments = mapping(plan)
    components = independent_component_record_ids(request)
    component_partition = {
        component: assignments[next(iter(component))] for component in components
    }
    component_sizes = {component: len(component) for component in components}
    partition_components = {
        partition: [
            component for component in components if component_partition[component] == partition
        ]
        for partition in ("train", "validation", "test")
    }
    counts = {
        partition: sum(component_sizes[value] for value in selected)
        for partition, selected in partition_components.items()
    }
    objective = independent_objective(request, counts)
    for source_partition, selected in partition_components.items():
        if len(selected) <= 1:
            continue
        for component in selected:
            for target_partition in counts:
                if target_partition == source_partition:
                    continue
                projected = dict(counts)
                projected[source_partition] -= component_sizes[component]
                projected[target_partition] += component_sizes[component]
                assert independent_objective(request, projected) >= objective
    partitions = ("train", "validation", "test")
    for first_index, first_partition in enumerate(partitions):
        for second_partition in partitions[first_index + 1 :]:
            for first_component in partition_components[first_partition]:
                for second_component in partition_components[second_partition]:
                    projected = dict(counts)
                    projected[first_partition] += (
                        component_sizes[second_component] - component_sizes[first_component]
                    )
                    projected[second_partition] += (
                        component_sizes[first_component] - component_sizes[second_component]
                    )
                    assert independent_objective(request, projected) >= objective


def test_entry_point_requires_validated_typed_unseen_player_request() -> None:
    with pytest.raises(ValueError, match="TrainingDatasetPreparationRequest"):
        split_module.generate_component_balanced_unseen_player_dataset_partition_plan(  # type: ignore[arg-type]
            {}
        )

    known = build_training_dataset_preparation_request(build_preparation_input())
    with pytest.raises(ValueError, match="requires request.mode 'unseen_player'"):
        split_module.generate_component_balanced_unseen_player_dataset_partition_plan(known)

    malformed = replace(build_request((1, 1, 1)), records=())
    with pytest.raises(ValueError, match="non-empty array"):
        split_module.generate_component_balanced_unseen_player_dataset_partition_plan(malformed)


def test_components_use_direct_and_transitive_player_connectivity_and_stable_identity() -> None:
    request = build_training_dataset_preparation_request(
        build_preparation_input(
            [
                game_with_players("A", "B", "C"),
                game_with_players("C", "D", "E"),
                game_with_players("E", "F", "G"),
                game_with_players("H", "I", "J"),
            ],
            mode="unseen_player",
        )
    )
    facts = build_dataset_preparation_source_facts(request)

    components = split_module._build_player_connected_components(facts)
    connected = next(component for component in components if component.record_count == 3)

    assert connected.record_ids == ("record-001", "record-002", "record-003")
    assert connected.historical_game_ids == (
        "dataset-game-1",
        "dataset-game-2",
        "dataset-game-3",
    )
    assert connected.player_ids == tuple("ABCDEFG")
    assert connected.source_facts == facts[:3]
    assert connected.sample_count == 90
    assert connected.zero_sample_record_count == 0
    identity_material = json.dumps(
        {
            "algorithm": COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "record_ids": connected.record_ids,
            "historical_game_ids": connected.historical_game_ids,
            "player_ids": connected.player_ids,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    assert connected.component_identity == hashlib.sha256(identity_material).hexdigest()
    assert independent_component_record_ids(request) == {
        frozenset(("record-001", "record-002", "record-003")),
        frozenset(("record-004",)),
    }
    assert not set(components[0].player_ids) & set(components[1].player_ids)


def test_zero_sample_record_connects_components_and_remains_diagnostic() -> None:
    zero = rename_players(
        build_concession_prefix(),
        {"player-a": "C", "player-b": "D", "player-c": "E"},
    )
    request = build_training_dataset_preparation_request(
        build_preparation_input(
            [
                game_with_players("A", "B", "C"),
                zero,
                game_with_players("F", "G", "H"),
                game_with_players("I", "J", "K"),
            ],
            mode="unseen_player",
        )
    )
    facts = build_dataset_preparation_source_facts(request)
    components = split_module._build_player_connected_components(facts)
    connected = next(component for component in components if component.record_count == 2)

    assert connected.record_ids == ("record-001", "record-002")
    assert connected.sample_count == 30
    assert connected.zero_sample_record_count == 1

    plan = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(request)
    assert mapping(plan)["record-001"] == mapping(plan)["record-002"]
    assert plan.source_record_count == 4
    assert plan.source_sample_count == 90
    prepared = materialize_prepared_training_dataset(request, plan)
    assert len(prepared.training_dataset_input.records) == 4
    assert prepared.training_dataset_input.records[1].historical_game == (
        request.records[1].historical_game
    )


@pytest.mark.parametrize("component_sizes", [(1,), (2, 1)])
def test_fewer_than_three_components_returns_only_insufficient_components(
    component_sizes: tuple[int, ...],
) -> None:
    request = build_request(component_sizes)

    plan = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(request)

    assert plan.status == "unavailable"
    assert plan.unavailable_reason == "insufficient_player_components"
    assert plan.assignments == ()
    assert plan.partition_summaries == ()
    assert plan.temporal_audit is None
    assert plan.partition_audit is None
    validate_dataset_partition_plan(request, plan)


def test_selection_fingerprint_has_exact_allowlist_and_ignores_source_order() -> None:
    request = build_request((2, 1, 1))
    facts = build_dataset_preparation_source_facts(request)
    fingerprint = build_unseen_player_selection_fingerprint(request, facts)
    player_ids_by_record = sorted(
        (
            {
                "record_id": fact.record_id,
                "player_ids": sorted(fact.player_ids),
            }
            for fact in facts
        ),
        key=lambda value: value["record_id"],
    )
    expected = hashlib.sha256(
        json.dumps(
            {
                "preparation_version": 1,
                "dataset_id": request.dataset_id,
                "dataset_version": request.dataset_version,
                "algorithm": COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
                "record_ids": sorted(fact.record_id for fact in facts),
                "historical_game_ids": sorted(fact.historical_game_id for fact in facts),
                "player_ids_by_record": player_ids_by_record,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    reordered_data = build_serializable_training_dataset_preparation_request(request)
    reordered_data["records"] = list(reversed(reordered_data["records"]))
    reordered = build_training_dataset_preparation_request(reordered_data)

    assert fingerprint == expected
    assert len(fingerprint) == 64
    assert (
        build_unseen_player_selection_fingerprint(
            reordered,
            build_dataset_preparation_source_facts(reordered),
        )
        == fingerprint
    )


def test_component_order_is_size_then_unseen_tie_key_then_identity(monkeypatch) -> None:
    request = build_request((2, 1, 1, 1))
    components = fake_components((1, 3, 3, 2))
    keys = {"0": 5, "1": 9, "2": 2, "3": 1}
    monkeypatch.setattr(
        split_module,
        "_tie_key",
        lambda request, fingerprint, identity: keys[identity],
    )

    ordered = split_module._order_components(request, components, "ab" * 32)

    assert [component.component_identity for component in ordered] == ["2", "1", "3", "0"]


def test_shared_objective_matches_independent_five_metric_integer_oracle() -> None:
    request = build_request(
        (3, 2, 1),
        weights={"train": 2, "validation": 3, "test": 5},
    )
    counts = {"train": 1, "validation": 2, "test": 3}

    assert build_record_count_objective(
        train_count=1,
        validation_count=2,
        test_count=3,
        source_count=6,
        weights=request.partition_weights,
    ) == independent_objective(request, counts)


def test_greedy_placement_is_non_empty_and_uses_ties_only_after_objective(
    monkeypatch,
) -> None:
    equal_request = build_request(
        (2, 1, 1),
        weights={"train": 2, "validation": 1, "test": 1},
    )
    equal_components = fake_components((1, 2, 1))

    def prefer_test(request, fingerprint, identity):
        del request, fingerprint
        if '"target_partition":"test"' in identity:
            return 0
        if '"target_partition":"validation"' in identity:
            return 1
        return 2

    monkeypatch.setattr(split_module, "_tie_key", prefer_test)
    allocation = split_module._build_initial_allocation(
        equal_request,
        equal_components,
        "ab" * 32,
    )
    assert allocation["0"] == "train"
    assert allocation["1"] == "test"
    assert set(allocation.values()) == {"train", "validation", "test"}

    weighted_request = build_request(
        (5, 1, 1),
        weights={"train": 10, "validation": 1, "test": 1},
    )
    weighted_components = fake_components((5, 1, 1))
    weighted = split_module._build_initial_allocation(
        weighted_request,
        weighted_components,
        "ab" * 32,
    )
    assert weighted["0"] == "train"


def test_local_improvement_accepts_strict_move_and_terminates_locally_optimal() -> None:
    request = build_request(
        (3, 1, 1, 1),
        weights={"train": 1, "validation": 1, "test": 1},
    )
    components = fake_components((3, 1, 1, 1))
    initial = {"0": "train", "1": "train", "2": "validation", "3": "test"}

    candidates = split_module._strict_improvement_candidates(request, components, initial)
    improved = split_module._improve_allocation(
        request,
        components,
        initial,
        "ab" * 32,
    )

    assert "move" in {candidate.kind for candidate in candidates}
    assert split_module._allocation_counts(components, initial) == {
        "train": 4,
        "validation": 1,
        "test": 1,
    }
    assert sorted(split_module._allocation_counts(components, improved).values()) == [1, 2, 3]
    assert split_module._strict_improvement_candidates(request, components, improved) == ()


def test_local_improvement_accepts_strict_swap_without_equal_objective_steps() -> None:
    request = build_request(
        (2, 2, 2, 1),
        weights={"train": 3, "validation": 1, "test": 1},
    )
    components = fake_components((2, 2, 2, 1))
    selection_fingerprint = "ab" * 32
    ordered = split_module._order_components(request, components, selection_fingerprint)
    initial = split_module._build_initial_allocation(request, ordered, selection_fingerprint)
    initial_objective = split_module._objective_for_counts(
        request,
        split_module._allocation_counts(components, initial),
    )

    candidates = split_module._strict_improvement_candidates(request, components, initial)
    improved = split_module._improve_allocation(
        request,
        components,
        initial,
        selection_fingerprint,
    )
    improved_objective = split_module._objective_for_counts(
        request,
        split_module._allocation_counts(components, improved),
    )

    assert {candidate.kind for candidate in candidates} == {"swap"}
    assert improved_objective < initial_objective
    assert split_module._strict_improvement_candidates(request, components, improved) == ()


def test_seed_changes_only_tied_choices_and_repeated_requests_are_identical() -> None:
    tied_plans = {}
    for seed in range(20):
        request = build_request(
            (1, 1, 1),
            weights={"train": 1, "validation": 1, "test": 1},
            seed=seed,
        )
        plan = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(
            request
        )
        tied_plans.setdefault(tuple(mapping(plan).values()), seed)
    assert len(tied_plans) > 1

    uniquely_sized_plans = []
    for seed in (1, 999):
        request = build_request(
            (3, 2, 1),
            weights={"train": 3, "validation": 2, "test": 1},
            seed=seed,
        )
        uniquely_sized_plans.append(
            split_module.generate_component_balanced_unseen_player_dataset_partition_plan(request)
        )
    assert mapping(uniquely_sized_plans[0]) == mapping(uniquely_sized_plans[1])
    assert uniquely_sized_plans[0].plan_fingerprint != (uniquely_sized_plans[1].plan_fingerprint)

    repeated_request = build_request((2, 1, 1), seed=73)
    assert split_module.generate_component_balanced_unseen_player_dataset_partition_plan(
        repeated_request
    ) == split_module.generate_component_balanced_unseen_player_dataset_partition_plan(
        repeated_request
    )


def test_source_order_independence_preserves_mapping_proofs_and_fingerprint() -> None:
    request = build_request((3, 2, 1, 1))
    reordered_data = build_serializable_training_dataset_preparation_request(request)
    reordered_data["records"] = [
        reordered_data["records"][index] for index in (4, 0, 6, 2, 1, 5, 3)
    ]
    reordered = build_training_dataset_preparation_request(reordered_data)

    first_facts = build_dataset_preparation_source_facts(request)
    second_facts = build_dataset_preparation_source_facts(reordered)
    first_components = split_module._build_player_connected_components(first_facts)
    second_components = split_module._build_player_connected_components(second_facts)
    first_selection_fingerprint = build_unseen_player_selection_fingerprint(request, first_facts)
    second_selection_fingerprint = build_unseen_player_selection_fingerprint(
        reordered, second_facts
    )
    assert [
        component.component_identity
        for component in split_module._order_components(
            request, first_components, first_selection_fingerprint
        )
    ] == [
        component.component_identity
        for component in split_module._order_components(
            reordered, second_components, second_selection_fingerprint
        )
    ]

    first = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(request)
    second = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(
        reordered
    )

    assert mapping(first) == mapping(second)
    assert first.partition_summaries == second.partition_summaries
    assert first.partition_audit == second.partition_audit
    assert first.plan_fingerprint == second.plan_fingerprint
    assert [assignment.record_id for assignment in second.assignments] == [
        record.record_id for record in reordered.records
    ]
    prepared = materialize_prepared_training_dataset(reordered, second)
    assert [record.record_id for record in prepared.training_dataset_input.records] == [
        record.record_id for record in reordered.records
    ]


def test_selection_ignores_timestamps_provenance_content_outcome_labels_and_samples() -> None:
    player_sets = [
        ("A", "B", "C"),
        ("D", "E", "F"),
        ("G", "H", "I"),
        ("J", "K", "L"),
    ]
    baseline_games = [game_with_players(*players) for players in player_sets]
    baseline = build_training_dataset_preparation_request(
        build_preparation_input(baseline_games, mode="unseen_player")
    )

    changed_games = [
        rename_all_stable_players(
            rebuild_historical_suffix(build_historical_input(), 5),
            player_sets[0],
        ),
        rename_all_stable_players(
            build_historical_input(game_type="null"),
            player_sets[1],
        ),
        rename_all_stable_players(
            build_concession_prefix(completed_trick_count=4, current_trick_card_count=2),
            player_sets[2],
        ),
        rename_all_stable_players(
            build_concession_prefix(),
            player_sets[3],
        ),
    ]
    changed_data = build_preparation_input(changed_games, mode="unseen_player")
    for index, record in enumerate(changed_data["records"]):
        record["historical_game"]["played_at"] = f"2027-02-0{index + 1}T03:00:00Z"
        record["historical_game"]["players"][0]["player_label"] = f"Changed {index}"
        record["provenance"]["source_name"] = f"Changed source {index}"
        record["provenance"]["notes"] = f"Changed note {index}"
    changed = build_training_dataset_preparation_request(changed_data)

    baseline_facts = build_dataset_preparation_source_facts(baseline)
    changed_facts = build_dataset_preparation_source_facts(changed)
    assert build_unseen_player_selection_fingerprint(
        baseline, baseline_facts
    ) == build_unseen_player_selection_fingerprint(changed, changed_facts)
    assert build_source_identity_fingerprint(baseline) != build_source_identity_fingerprint(changed)
    assert [fact.sample_count for fact in baseline_facts] != [
        fact.sample_count for fact in changed_facts
    ]

    first = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(baseline)
    second = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(changed)

    assert mapping(first) == mapping(second)
    assert first.source_sample_count != second.source_sample_count
    assert first.source_content_fingerprint != second.source_content_fingerprint
    assert first.plan_fingerprint != second.plan_fingerprint


def test_complete_plan_is_whole_component_locally_optimal_audited_and_lossless() -> None:
    request = build_request(
        (4, 3, 2, 2, 1),
        weights={"train": 3, "validation": 2, "test": 1},
    )

    plan = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(request)
    validate_dataset_partition_plan(request, plan)
    prepared = materialize_prepared_training_dataset(request, plan)

    assert plan.status == "complete"
    assert plan.algorithm == COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM
    assert plan.mode == "unseen_player"
    assert plan.temporal_audit is None
    assert all(summary.record_count > 0 for summary in plan.partition_summaries)
    assert plan.partition_audit is not None
    assert plan.partition_audit.compliance_status == "compliant"
    assert plan.partition_audit.unseen_player_compliance["player_disjoint"] is True
    assert len(mapping(plan)) == len(request.records)
    for component in independent_component_record_ids(request):
        assert len({mapping(plan)[record_id] for record_id in component}) == 1
    assert_no_independent_move_or_swap_improves(request, plan)
    assert prepared.partition_audit == plan.partition_audit
    assert prepared.training_dataset_input.partition_policy is not None
    assert prepared.training_dataset_input.partition_policy.mode == "unseen_player"
    assert [record.historical_game for record in prepared.training_dataset_input.records] == [
        record.historical_game for record in request.records
    ]
    assert [record.provenance for record in prepared.training_dataset_input.records] == [
        record.provenance for record in request.records
    ]


def test_generator_builds_facts_and_final_plan_only_once(monkeypatch) -> None:
    request = build_request((3, 2, 1, 1))
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

    plan = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(request)

    assert plan.status == "complete"
    assert counts == {
        "summary": len(request.records),
        "snapshots": len(request.records),
        "materialization": 1,
        "audit": 1,
    }


def test_generated_plan_uses_unchanged_complete_plan_serialization() -> None:
    request = build_request((2, 1, 1))
    generated = split_module.generate_component_balanced_unseen_player_dataset_partition_plan(
        request
    )
    supplied = build_complete_dataset_partition_plan(
        request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=generated.assignments,
    )

    assert generated == supplied
    serialized = build_serializable_dataset_partition_plan(generated)
    assert set(serialized) == {
        "plan_version",
        "algorithm",
        "mode",
        "status",
        "unavailable_reason",
        "source_identity_fingerprint",
        "source_content_fingerprint",
        "base_random_seed",
        "balance_basis",
        "requested_partition_weights",
        "source_record_count",
        "source_sample_count",
        "assignments",
        "partition_summaries",
        "temporal_audit",
        "partition_audit",
        "plan_fingerprint",
    }
    assert "component_identity" not in str(serialized)
    assert "selection_fingerprint" not in str(serialized)
