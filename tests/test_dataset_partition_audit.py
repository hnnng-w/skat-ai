import copy

import pytest
from test_historical_game import build_historical_input
from test_training_dataset import build_training_input

from skat_ai.dataset_partition_audit import (
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
    resolve_dataset_partition_audit_mode,
)
from skat_ai.training_dataset import build_training_dataset_input


def rename_players(game: dict, mapping: dict[str, str]) -> dict:
    game = copy.deepcopy(game)
    for player in game["players"]:
        player["player_id"] = mapping[player["player_id"]]
    game["declarer_player_id"] = mapping[game["declarer_player_id"]]
    for trick in game["tricks"]:
        trick["leader_player_id"] = mapping[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = mapping[play["player_id"]]
    return game


def game_with_players(first: str, second: str, third: str) -> dict:
    return rename_players(
        build_historical_input(),
        {"player-a": first, "player-b": second, "player-c": third},
    )


def build_overlap_dataset():
    games = [
        game_with_players("A", "B", "C"),
        game_with_players("A", "D", "E"),
        game_with_players("F", "A", "B"),
        game_with_players("G", "H", "I"),
        game_with_players("C", "G", "A"),
        game_with_players("J", "K", "L"),
    ]
    return build_training_dataset_input(
        build_training_input(
            games,
            ["train", "train", "validation", "validation", "test", "test"],
        )
    )


def serialize(dataset, mode="report_only") -> dict:
    return build_serializable_dataset_partition_audit(
        audit_training_dataset_partitions(dataset, mode)
    )


def test_membership_identity_order_seat_changes_and_partition_counts() -> None:
    dataset = build_overlap_dataset()
    original = copy.deepcopy(dataset)

    result = serialize(dataset)

    assert dataset == original
    assert [player["player_id"] for player in result["players"]] == [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
    ]
    player_a = result["players"][0]
    assert player_a["partitions"] == ["train", "validation", "test"]
    assert player_a["game_count_by_partition"] == {
        "train": 2,
        "validation": 1,
        "test": 1,
    }
    assert player_a["record_ids_by_partition"] == {
        "train": ["record-001", "record-002"],
        "validation": ["record-003"],
        "test": ["record-005"],
    }
    assert player_a["first_appearance_index"] == 0
    assert player_a["classification"] == "three_partition_overlap"
    assert result["partition_summary"]["train"] == {
        "record_count": 2,
        "game_count": 2,
        "distinct_player_count": 5,
        "total_player_game_appearances": 6,
        "player_ids": ["A", "B", "C", "D", "E"],
    }
    assert result["player_summary"] == {
        "total_distinct_player_count": 12,
        "single_partition_player_count": 8,
        "pairwise_overlap_player_count": 3,
        "three_partition_overlap_player_count": 1,
        "train_player_count": 5,
        "validation_player_count": 6,
        "test_player_count": 6,
    }


def test_pairwise_groups_include_three_way_players_in_deterministic_order() -> None:
    overlaps = serialize(build_overlap_dataset())["overlap_summary"]

    assert overlaps["train_validation"]["player_ids"] == ["A", "B"]
    assert overlaps["train_test"]["player_ids"] == ["A", "C"]
    assert overlaps["validation_test"]["player_ids"] == ["A", "G"]
    assert overlaps["train_validation_test"]["player_ids"] == ["A"]
    assert overlaps["train_validation"]["player_count"] == 2
    assert overlaps["train_validation_test"]["player_memberships"] == [
        {"player_id": "A", "partitions": ["train", "validation", "test"]}
    ]


def test_known_opponent_coverage_is_partition_based_and_reconciled() -> None:
    result = serialize(build_overlap_dataset(), "known_opponent")

    assert result["compliance_status"] == "compliant"
    train_to_validation = result["known_opponent_coverage"]["train_to_validation"]
    assert train_to_validation == {
        "source_partition": "train",
        "target_partition": "validation",
        "source_distinct_player_count": 5,
        "target_distinct_player_count": 6,
        "shared_player_count": 2,
        "shared_player_ids": ["A", "B"],
        "target_player_count_with_source_history": 2,
        "target_player_count_without_source_history": 4,
        "target_game_count_with_at_least_one_previously_seen_participant": 1,
        "target_game_count_with_all_three_participants_previously_seen": 0,
        "target_player_game_appearances_with_source_history": 2,
        "target_player_game_appearances_without_source_history": 4,
        "eligibility_basis": "partition_membership_only_not_temporal_eligibility",
    }
    assert result["known_opponent_coverage"]["train_to_test"][
        "shared_player_ids"
    ] == ["A", "C"]
    assert result["known_opponent_coverage"]["validation_to_test"][
        "shared_player_ids"
    ] == ["A", "G"]


def test_known_opponent_mode_accepts_zero_overlap_and_reports_zero_coverage() -> None:
    dataset = build_training_dataset_input(
        build_training_input(
            [
                game_with_players("A", "B", "C"),
                game_with_players("D", "E", "F"),
            ],
            ["train", "validation"],
        )
    )

    result = serialize(dataset, "known_opponent")

    assert result["compliance_status"] == "compliant"
    assert result["overlap_summary"]["train_validation"]["player_count"] == 0
    coverage = result["known_opponent_coverage"]["train_to_validation"]
    assert coverage["shared_player_ids"] == []
    assert coverage["target_player_count_with_source_history"] == 0
    assert coverage["target_player_count_without_source_history"] == 3


def test_report_only_and_requested_unseen_mode_return_complete_overlap_report() -> None:
    dataset = build_overlap_dataset()

    report_only = serialize(dataset)
    unseen = serialize(dataset, "unseen_player")

    assert report_only["compliance_status"] == "not_evaluated"
    assert unseen["compliance_status"] == "non_compliant"
    assert unseen["unseen_player_compliance"] == {
        "player_disjoint": False,
        "violating_player_count": 4,
        "violating_player_ids": ["A", "B", "C", "G"],
        "violations": [
            {"player_id": "A", "partitions": ["train", "validation", "test"]},
            {"player_id": "B", "partitions": ["train", "validation"]},
            {"player_id": "C", "partitions": ["train", "test"]},
            {"player_id": "G", "partitions": ["validation", "test"]},
        ],
        "pairwise_violation_counts": {
            "train_validation": 2,
            "train_test": 2,
            "validation_test": 2,
        },
        "three_way_violation_count": 1,
    }
    assert len(unseen["players"]) == 12
    assert "samples" not in str(unseen)
    assert "recommendation" not in str(unseen)
    assert "simulation" not in str(unseen)
    assert "model" not in str(unseen)


def test_player_disjoint_policy_accepts_repetition_inside_one_partition() -> None:
    data = build_training_input(
        [
            game_with_players("A", "B", "C"),
            game_with_players("A", "D", "E"),
            game_with_players("F", "G", "H"),
            game_with_players("I", "J", "K"),
        ],
        ["train", "train", "validation", "test"],
    )
    data["partition_policy"] = {
        "policy_version": 1,
        "mode": "unseen_player",
    }
    dataset = build_training_dataset_input(data)
    result = serialize(dataset, "unseen_player")

    assert result["declared_partition_policy"] == data["partition_policy"]
    assert result["compliance_status"] == "compliant"
    assert result["unseen_player_compliance"]["player_disjoint"] is True
    assert result["unseen_player_compliance"]["violating_player_ids"] == []
    assert result["players"][0]["game_count_by_partition"]["train"] == 2


def test_exact_case_sensitive_ids_and_identical_labels_remain_distinct() -> None:
    first = game_with_players("Player", "B", "C")
    second = game_with_players("player", "D", "E")
    first["players"][0]["player_label"] = "Same label"
    second["players"][0]["player_label"] = "Same label"
    dataset = build_training_dataset_input(
        build_training_input([first, second], ["train", "validation"])
    )

    result = serialize(dataset, "unseen_player")

    assert result["compliance_status"] == "compliant"
    assert result["players"][0]["player_id"] == "Player"
    assert result["players"][3]["player_id"] == "player"
    assert result["players"][0]["player_label"] == "Same label"
    assert result["players"][3]["player_label"] == "Same label"


def test_audit_mode_resolution_uses_cli_then_declaration_then_report_only() -> None:
    undeclared = build_overlap_dataset()
    assert resolve_dataset_partition_audit_mode(undeclared, None) == "report_only"
    assert (
        resolve_dataset_partition_audit_mode(undeclared, "known_opponent")
        == "known_opponent"
    )

    data = build_training_input()
    data["partition_policy"] = {
        "policy_version": 1,
        "mode": "known_opponent",
    }
    declared = build_training_dataset_input(data)
    assert resolve_dataset_partition_audit_mode(declared, None) == "known_opponent"
    assert resolve_dataset_partition_audit_mode(declared, "report_only") == "report_only"
    with pytest.raises(ValueError, match="contradicts declared partition policy"):
        resolve_dataset_partition_audit_mode(declared, "unseen_player")
