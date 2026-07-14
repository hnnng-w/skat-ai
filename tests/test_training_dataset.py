import copy

import pytest
from test_historical_game import build_historical_input

from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.output_writer import write_analysis_result_to_json
from skat_ai.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)


def build_training_input(
    historical_games: list[dict] | None = None,
    partitions: list[str] | None = None,
) -> dict:
    games = historical_games or [build_historical_input()]
    partitions = partitions or ["train"] * len(games)
    records = []
    for index, (historical_game, partition) in enumerate(
        zip(games, partitions, strict=True),
        start=1,
    ):
        historical_game = copy.deepcopy(historical_game)
        historical_game["game_id"] = f"dataset-game-{index}"
        records.append(
            {
                "record_id": f"record-{index:03d}",
                "partition": partition,
                "provenance": {
                    "source_type": "online_platform",
                    "source_name": "Fixture platform",
                    "source_record_id": f"source-{index:03d}",
                    "collected_at": f"2026-01-{index:02d}T12:00:00Z",
                    "notes": f"Fixture record {index}",
                },
                "historical_game": historical_game,
            }
        )
    return {
        "schema_version": 1,
        "dataset_id": "fixture-dataset",
        "dataset_version": "1",
        "feature_generation_version": 1,
        "target": "actual_card_played",
        "records": records,
    }


def convert(data: dict) -> dict:
    return build_training_dataset_summary(build_training_dataset_input(data))


def test_multi_partition_dataset_is_deterministic_ordered_and_reconciled() -> None:
    data = build_training_input(
        historical_games=[
            build_historical_input(game_type="grand"),
            build_historical_input(game_type="clubs", hand_game=True),
            build_historical_input(game_type="null"),
        ],
        partitions=["validation", "train", "test"],
    )

    first = convert(data)
    second = convert(data)

    assert first == second
    assert first["schema_version"] == 1
    assert first["feature_generation_version"] == 1
    assert first["target"] == "actual_card_played"
    assert first["record_count"] == 3
    assert first["sample_count"] == 90
    assert [record["record_id"] for record in first["records"]] == [
        "record-001",
        "record-002",
        "record-003",
    ]
    assert first["partition_counts"] == {
        "train": {"record_count": 1, "sample_count": 30},
        "validation": {"record_count": 1, "sample_count": 30},
        "test": {"record_count": 1, "sample_count": 30},
    }
    assert all(
        record["sample_count"] == len(record["samples"]) == 30
        for record in first["records"]
    )


def test_repeated_conversion_writes_byte_stable_output(tmp_path) -> None:
    summary = convert(build_training_input())
    result = {
        "input_file": "fixture.json",
        "training_dataset_summary": summary,
    }
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    write_analysis_result_to_json(str(first_path), result)
    write_analysis_result_to_json(str(second_path), result)

    assert first_path.read_bytes() == second_path.read_bytes()


def test_samples_separate_traceability_features_and_actual_card_labels() -> None:
    data = build_training_input()
    typed_dataset = build_training_dataset_input(data)
    summary = build_training_dataset_summary(typed_dataset)
    record = summary["records"][0]
    samples = record["samples"]
    source_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(typed_dataset.records[0].historical_game)
    ).snapshots

    assert record["provenance"] == data["records"][0]["provenance"]
    assert [sample["sample_id"] for sample in samples] == [
        f"record-001:{decision_index}" for decision_index in range(1, 31)
    ]
    assert [sample["metadata"]["decision_index"] for sample in samples] == list(
        range(1, 31)
    )

    forbidden_feature_keys = {
        "dataset_id",
        "dataset_version",
        "record_id",
        "source_game_id",
        "source_record_id",
        "source_name",
        "player_id",
        "acting_player_id",
        "winner_player_id",
        "actual_card_played",
        "game_result_summary",
        "game_value_summary",
        "overbid_summary",
        "final_settlement_summary",
        "recommendation",
        "decision_quality",
    }

    def collect_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(collect_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value), set())
        return set()

    for sample, snapshot in zip(samples, source_snapshots, strict=True):
        metadata = sample["metadata"]
        features = sample["features"]
        label = sample["label"]
        assert metadata["dataset_id"] == "fixture-dataset"
        assert metadata["record_id"] == "record-001"
        assert metadata["source_game_id"] == "dataset-game-1"
        assert metadata["acting_player_id"] == snapshot.acting_player_id
        assert metadata["provenance"] == data["records"][0]["provenance"]
        assert forbidden_feature_keys.isdisjoint(collect_keys(features))
        assert features["own_hand"] == list(snapshot.visible_state.own_hand)
        assert features["legal_cards"] == list(snapshot.visible_state.legal_cards)
        assert label == {
            "target": "actual_card_played",
            "card": snapshot.actual_card_played,
        }
        assert label["card"] in features["own_hand"]
        assert label["card"] in features["legal_cards"]
        assert label["card"] not in {
            play["card"] for play in features["current_trick"]
        }
        relative_players = {
            play["player"]
            for trick in features["completed_tricks"]
            for play in trick["plays"]
        }
        relative_players.update(
            play["player"] for play in features["current_trick"]
        )
        relative_players.update(
            exposure["player"] for exposure in features["public_exposed_cards"]
        )
        assert relative_players <= {"me", "left", "right"}


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert"),
    [
        ("clubs", True, False),
        ("grand", False, False),
        ("null", False, False),
        ("null", True, True),
    ],
)
def test_contract_and_visibility_variants_generate_all_samples(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
) -> None:
    game = build_historical_input(game_type=game_type, hand_game=hand_game)
    game["declaration"]["ouvert"] = ouvert

    samples = convert(build_training_input([game]))["records"][0]["samples"]

    assert len(samples) == 30
    assert {sample["features"]["game_type"] for sample in samples} == {game_type}
    assert {sample["features"]["acting_side"] for sample in samples} == {
        "declarer",
        "defenders",
    }
    if hand_game:
        assert all(
            sample["features"]["skat_visibility"] == "unknown"
            and sample["features"]["known_skat_cards"] == []
            for sample in samples
        )
    if not hand_game:
        declarer_samples = [
            sample
            for sample in samples
            if sample["features"]["acting_side"] == "declarer"
        ]
        assert all(
            sample["features"]["skat_visibility"] == "known_to_declarer"
            and sample["features"]["known_skat_cards"] == game["discarded_cards"]
            for sample in declarer_samples
        )
    if ouvert:
        assert all(sample["features"]["public_exposed_cards"] for sample in samples)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("feature_generation_version", 2),
        ("target", "decision_quality"),
        ("dataset_id", ""),
        ("dataset_id", " padded"),
        ("dataset_version", "1 "),
    ],
)
def test_invalid_dataset_versions_target_and_identifiers_are_rejected(
    field: str,
    invalid_value: object,
) -> None:
    data = build_training_input()
    data[field] = invalid_value

    with pytest.raises(ValueError, match=field):
        build_training_dataset_input(data)


@pytest.mark.parametrize(
    ("field", "invalid_value", "error_match"),
    [
        ("record_id", "record-001 ", "record_id"),
        ("partition", "holdout", "partition"),
        ("provenance.source_type", "website", "source_type"),
        ("provenance.source_name", "", "source_name"),
        ("provenance.source_record_id", " source", "source_record_id"),
        ("provenance.collected_at", "2026-02-30T12:00:00Z", "RFC 3339"),
        ("provenance.notes", " ", "notes"),
    ],
)
def test_invalid_record_partition_and_provenance_are_rejected(
    field: str,
    invalid_value: object,
    error_match: str,
) -> None:
    data = build_training_input()
    record = data["records"][0]
    if field.startswith("provenance."):
        record["provenance"][field.removeprefix("provenance.")] = invalid_value
    else:
        record[field] = invalid_value

    with pytest.raises(ValueError, match=error_match):
        build_training_dataset_input(data)


def test_missing_and_unknown_provenance_are_rejected() -> None:
    missing = build_training_input()
    del missing["records"][0]["provenance"]
    with pytest.raises(ValueError, match="missing required fields.*provenance"):
        build_training_dataset_input(missing)

    unknown = build_training_input()
    unknown["records"][0]["provenance"]["platform_url"] = "https://example.test"
    with pytest.raises(ValueError, match="unsupported fields.*platform_url"):
        build_training_dataset_input(unknown)


@pytest.mark.parametrize(
    "collected_at",
    ["2026-01-01t12:00:00z", "2016-12-31T23:59:60Z"],
)
def test_valid_rfc3339_provenance_date_times_are_preserved(collected_at: str) -> None:
    data = build_training_input()
    data["records"][0]["provenance"]["collected_at"] = collected_at

    dataset = build_training_dataset_input(data)

    assert dataset.records[0].provenance.collected_at == collected_at


@pytest.mark.parametrize(
    ("duplicate_kind", "second_partition", "error_match"),
    [
        ("record", "train", "Duplicate training record_id"),
        ("game", "train", "Duplicate historical game_id"),
        ("game", "test", "appears in both 'train' and 'test' partitions"),
        ("source", "train", "Duplicate source record"),
        ("source", "validation", "appears in both 'train' and 'validation' partitions"),
    ],
)
def test_duplicate_and_partition_leakage_are_rejected_before_replay(
    duplicate_kind: str,
    second_partition: str,
    error_match: str,
) -> None:
    data = build_training_input(
        [build_historical_input(), build_historical_input(game_type="clubs", hand_game=True)],
        ["train", second_partition],
    )
    first, second = data["records"]
    if duplicate_kind == "record":
        second["record_id"] = first["record_id"]
    elif duplicate_kind == "game":
        second["historical_game"]["game_id"] = first["historical_game"]["game_id"]
    else:
        second["provenance"] = copy.deepcopy(first["provenance"])

    with pytest.raises(ValueError, match=error_match):
        build_training_dataset_input(data)


def test_empty_records_and_unknown_dataset_fields_are_rejected() -> None:
    empty = build_training_input()
    empty["records"] = []
    with pytest.raises(ValueError, match="non-empty array"):
        build_training_dataset_input(empty)

    unknown = build_training_input()
    unknown["shuffle"] = True
    with pytest.raises(ValueError, match="unsupported fields.*shuffle"):
        build_training_dataset_input(unknown)
