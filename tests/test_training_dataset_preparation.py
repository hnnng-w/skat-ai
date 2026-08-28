import copy
from dataclasses import FrozenInstanceError

import pytest
from test_dataset_partition_audit import game_with_players
from test_historical_declarer_concession import build_concession_prefix
from test_historical_game import build_historical_input
from test_training_dataset import build_training_input

from skatmind.dataset_partition_plan import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
    DatasetPartitionAssignment,
    build_complete_dataset_partition_plan,
)
from skatmind.training_dataset import (
    build_serializable_training_dataset_input,
    build_training_dataset_input,
)
from skatmind.training_dataset_preparation import (
    TRAINING_DATASET_PREPARATION_VERSION,
    DatasetPartitionWeights,
    build_dataset_partition_weights,
    build_dataset_preparation_source_facts,
    build_serializable_dataset_preparation_source_fact,
    build_serializable_prepared_training_dataset,
    build_serializable_training_dataset_preparation_request,
    build_training_dataset_preparation_request,
    materialize_prepared_training_dataset,
)


def build_preparation_input(
    games: list[dict] | None = None,
    *,
    mode: str = "known_opponent",
    weights: dict[str, int] | None = None,
    seed: int = 41,
) -> dict:
    data = build_training_input(games)
    records = copy.deepcopy(data["records"])
    for record in records:
        del record["partition"]
    return {
        "preparation_version": 1,
        "dataset_id": data["dataset_id"],
        "dataset_version": data["dataset_version"],
        "feature_generation_version": data["feature_generation_version"],
        "target": data["target"],
        "mode": mode,
        "base_random_seed": seed,
        "partition_weights": weights or {
            "train": 3,
            "validation": 1,
            "test": 1,
        },
        "records": records,
    }


def build_unseen_request():
    return build_training_dataset_preparation_request(
        build_preparation_input(
            [
                game_with_players("A", "B", "C"),
                game_with_players("D", "E", "F"),
                game_with_players("G", "H", "I"),
            ],
            mode="unseen_player",
        )
    )


def test_constants_values_are_frozen_and_source_records_are_unpartitioned() -> None:
    data = build_preparation_input()
    original = copy.deepcopy(data)

    request = build_training_dataset_preparation_request(data)
    data["records"][0]["record_id"] = "changed"

    assert TRAINING_DATASET_PREPARATION_VERSION == 1
    assert request.preparation_version == 1
    assert request.records[0].record_id == original["records"][0]["record_id"]
    assert not hasattr(request.records[0], "partition")
    with pytest.raises(FrozenInstanceError):
        request.dataset_id = "changed"  # type: ignore[misc]

    partitioned = build_preparation_input()
    partitioned["records"][0]["partition"] = "train"
    with pytest.raises(ValueError, match="unsupported fields.*partition"):
        build_training_dataset_preparation_request(partitioned)


def test_explicit_weights_preserve_positive_integers_and_are_strict() -> None:
    weights = build_dataset_partition_weights(
        {"train": 17, "validation": 5, "test": 3}
    )

    assert weights == DatasetPartitionWeights(train=17, validation=5, test=3)
    assert weights.total == 25
    assert weights.total_weight == 25

    for invalid in (True, 0, -1, 1.0):
        with pytest.raises(ValueError, match="train.*positive integer"):
            build_dataset_partition_weights(
                {"train": invalid, "validation": 1, "test": 1}
            )
    with pytest.raises(ValueError, match="missing required fields.*test"):
        build_dataset_partition_weights({"train": 1, "validation": 1})
    with pytest.raises(ValueError, match="unsupported fields.*holdout"):
        build_dataset_partition_weights(
            {"train": 1, "validation": 1, "test": 1, "holdout": 1}
        )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("preparation_version", 2, "preparation_version"),
        ("feature_generation_version", 2, "feature_generation_version"),
        ("target", "winner", "target"),
        ("mode", "report_only", "mode"),
        ("base_random_seed", True, "must not be a boolean"),
        ("dataset_id", " padded", "dataset_id"),
    ],
)
def test_request_versions_target_mode_seed_and_identifiers_are_strict(
    field: str,
    value: object,
    error: str,
) -> None:
    data = build_preparation_input()
    data[field] = value

    with pytest.raises(ValueError, match=error):
        build_training_dataset_preparation_request(data)


def test_request_requires_records_exact_fields_and_unique_source_identities() -> None:
    empty = build_preparation_input()
    empty["records"] = []
    with pytest.raises(ValueError, match="non-empty array"):
        build_training_dataset_preparation_request(empty)

    unknown = build_preparation_input()
    unknown["shuffle"] = True
    with pytest.raises(ValueError, match="unsupported fields.*shuffle"):
        build_training_dataset_preparation_request(unknown)

    for duplicate_kind, error in (
        ("record", "Duplicate training record_id"),
        ("game", "Duplicate historical game_id"),
        ("source", "Duplicate source record"),
    ):
        data = build_preparation_input(
            [build_historical_input(), build_historical_input(game_type="null")]
        )
        first, second = data["records"]
        if duplicate_kind == "record":
            second["record_id"] = first["record_id"]
        elif duplicate_kind == "game":
            second["historical_game"]["game_id"] = first["historical_game"][
                "game_id"
            ]
        else:
            second["provenance"] = copy.deepcopy(first["provenance"])
        with pytest.raises(ValueError, match=error):
            build_training_dataset_preparation_request(data)


def test_source_facts_count_snapshots_and_retain_zero_sample_records() -> None:
    normal = build_historical_input()
    shortened = build_concession_prefix(
        completed_trick_count=4,
        current_trick_card_count=2,
    )
    zero = build_concession_prefix()
    request = build_training_dataset_preparation_request(
        build_preparation_input([normal, shortened, zero])
    )

    facts = build_dataset_preparation_source_facts(request)
    serialized = [
        build_serializable_dataset_preparation_source_fact(fact)
        for fact in facts
    ]

    assert [fact.source_index for fact in facts] == [0, 1, 2]
    assert [fact.sample_count for fact in facts] == [30, 14, 0]
    assert [fact.zero_sample for fact in facts] == [False, False, True]
    assert facts[0].player_ids == tuple(sorted(facts[0].player_ids))
    assert serialized[0]["source_identity"] == {
        "source_type": "online_platform",
        "source_name": "Fixture platform",
        "source_record_id": "source-001",
    }
    assert "historical_game" not in serialized[0]
    assert "samples" not in serialized[0]
    assert "actual_card_played" not in str(serialized)


def test_preparation_serialization_is_deterministic_and_round_trips() -> None:
    request = build_training_dataset_preparation_request(build_preparation_input())

    first = build_serializable_training_dataset_preparation_request(request)
    second = build_serializable_training_dataset_preparation_request(request)

    assert first == second
    assert "partition" not in first["records"][0]
    assert build_training_dataset_preparation_request(first) == request


def test_materialization_adds_only_partitions_and_reuses_existing_audit() -> None:
    request = build_unseen_request()
    assignments = tuple(
        DatasetPartitionAssignment(record.record_id, partition)
        for record, partition in zip(
            request.records,
            ("train", "validation", "test"),
            strict=True,
        )
    )
    plan = build_complete_dataset_partition_plan(
        request,
        algorithm=COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
        assignments=assignments,
    )

    prepared = materialize_prepared_training_dataset(request, plan)
    dataset = prepared.training_dataset_input
    serialized = build_serializable_training_dataset_input(dataset)

    assert dataset.partition_policy is not None
    assert dataset.partition_policy.policy_version == 1
    assert dataset.partition_policy.mode == "unseen_player"
    assert [record.record_id for record in dataset.records] == [
        record.record_id for record in request.records
    ]
    assert [record.historical_game for record in dataset.records] == [
        record.historical_game for record in request.records
    ]
    assert [record.provenance for record in dataset.records] == [
        record.provenance for record in request.records
    ]
    assert prepared.partition_audit == plan.partition_audit
    assert prepared.partition_audit.compliance_status == "compliant"
    assert build_training_dataset_input(serialized) == dataset
    serialized_prepared = build_serializable_prepared_training_dataset(prepared)
    assert serialized_prepared["preparation_version"] == 1
    assert serialized_prepared["plan"]["plan_fingerprint"] == plan.plan_fingerprint
    assert serialized_prepared["training_dataset_input"] == serialized
    assert prepared.training_dataset is dataset
