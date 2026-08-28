import copy
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from test_historical_game import build_historical_input
from test_training_dataset import build_training_input

from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import build_historical_game_summary
from skatmind.rolling_opponent_policy_evaluation import (
    _build_paired_results,
    _build_prediction,
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skatmind.training_dataset import build_training_dataset_input


def build_dataset(specs: list[tuple[str, str, dict]]):
    games = []
    partitions = []
    for partition, played_at, game in specs:
        game = copy.deepcopy(game)
        game["played_at"] = played_at
        games.append(game)
        partitions.append(partition)
    return build_training_dataset_input(build_training_input(games, partitions))


def serialize(dataset, source=("train",), evaluation=("validation", "test")):
    return build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(
            dataset,
            source_partitions=source,
            evaluation_partitions=evaluation,
        )
    )


def build_concession_from_game(game: dict, played_card_count: int) -> dict:
    game = copy.deepcopy(game)
    if played_card_count == 29:
        game["players"][0]["initial_hand"].remove("C7")
        game["players"][0]["initial_hand"].append("DQ")
        game["players"][2]["initial_hand"].remove("DQ")
        game["players"][2]["initial_hand"].append("C7")
        game["tricks"][0]["plays"][2]["card"] = "C7"
        game["tricks"][4]["plays"][2]["card"] = "D9"
        game["tricks"][8]["plays"][0]["card"] = "DQ"
        game["tricks"][8]["plays"][2]["card"] = "DA"
        game["tricks"][9] = {
            "trick_number": 10,
            "leader_player_id": "player-c",
            "plays": [
                {"player_id": "player-c", "card": "HJ"},
                {"player_id": "player-a", "card": "S10"},
                {"player_id": "player-b", "card": "D7"},
            ],
        }
    complete_trick_count, current_trick_card_count = divmod(played_card_count, 3)
    tricks = copy.deepcopy(game["tricks"][:complete_trick_count])
    if current_trick_card_count:
        current_trick = copy.deepcopy(game["tricks"][complete_trick_count])
        current_trick["plays"] = current_trick["plays"][:current_trick_card_count]
        tricks.append(current_trick)
    declarer_id = game["declarer_player_id"]
    declarer_play_count = sum(
        play["player_id"] == declarer_id for trick in tricks for play in trick["plays"]
    )
    declarer_cards_remaining = 10 - declarer_play_count
    defenders = [
        player["player_id"]
        for player in game["players"]
        if player["player_id"] != declarer_id
    ]
    game.update(
        {
            "game_end_reason": "declarer_concession",
            "game_end": {
                "schema_version": 1,
                "kind": "declarer_concession",
                "declarer_hand_cards_remaining": declarer_cards_remaining,
                "defender_consent": {
                    "status": (
                        "granted" if declarer_cards_remaining < 9 else "not_required"
                    ),
                    "consenting_defender_player_ids": (
                        [defenders[0]] if declarer_cards_remaining < 9 else []
                    ),
                },
            },
            "tricks": tricks,
        }
    )
    return game


def test_default_selection_is_canonical_deterministic_and_reconciled() -> None:
    dataset = build_dataset(
        [
            ("train", "2026-07-10T16:00:00Z", build_historical_input()),
            ("validation", "2026-07-11T18:00:00+02:00", build_historical_input()),
        ]
    )

    first = serialize(dataset)
    second = serialize(dataset)

    assert first == second
    assert first["selection"] == {
        "evaluation_mode": "known_opponent",
        "source_partitions": ["train"],
        "evaluation_partitions": ["validation", "test"],
        "temporal_rule": "source_played_at_strictly_before_target_played_at",
        "selected_partition_player_overlap": {
            "source_distinct_player_count": 3,
            "evaluation_distinct_player_count": 3,
            "shared_player_count": 3,
            "shared_player_ids": ["player-a", "player-b", "player-c"],
            "eligibility_basis": "partition_membership_only_not_temporal_eligibility",
        },
        "source_record_count": 1,
        "target_record_count": 1,
        "target_game_count": 1,
        "target_decision_count": 30,
    }
    assert first["coverage"]["target_decisions"] == 30
    assert first["baseline_results"]["decision_count"] == 30
    assert first["actionable_profile_paired_results"]["paired_decision_count"] == 0
    assert first["actionable_profile_paired_results"][
        "profile_preferred_card_match_rate"
    ] is None
    assert sum(
        row["coverage_count"] for row in first["breakdowns"]["by_player"]
    ) == 30
    assert "recommendation" not in str(first)
    assert "expected_point" not in str(first)


def test_known_opponent_policy_is_accepted_and_preserved() -> None:
    data = build_training_input(
        [build_historical_input(), build_historical_input()],
        ["train", "validation"],
    )
    data["records"][0]["historical_game"]["played_at"] = "2026-07-10T16:00:00Z"
    data["records"][1]["historical_game"]["played_at"] = "2026-07-11T16:00:00Z"
    data["partition_policy"] = {
        "policy_version": 1,
        "mode": "known_opponent",
    }

    result = serialize(build_training_dataset_input(data))

    assert result["source_dataset"]["partition_policy"] == data["partition_policy"]
    assert result["selection"]["evaluation_mode"] == "known_opponent"


def test_unseen_player_policy_is_semantically_incompatible() -> None:
    source = build_historical_input()
    target = build_historical_input()
    mapping = {
        "player-a": "target-a",
        "player-b": "target-b",
        "player-c": "target-c",
    }
    for player in target["players"]:
        player["player_id"] = mapping[player["player_id"]]
    target["declarer_player_id"] = mapping[target["declarer_player_id"]]
    for trick in target["tricks"]:
        trick["leader_player_id"] = mapping[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = mapping[play["player_id"]]
    data = build_training_input([source, target], ["train", "validation"])
    data["records"][0]["historical_game"]["played_at"] = "2026-07-10T16:00:00Z"
    data["records"][1]["historical_game"]["played_at"] = "2026-07-11T16:00:00Z"
    data["partition_policy"] = {
        "policy_version": 1,
        "mode": "unseen_player",
    }

    with pytest.raises(ValueError, match="known_opponent workflow.*unseen_player"):
        serialize(build_training_dataset_input(data))


def test_explicit_partitions_are_deduplicated_canonical_and_disjoint() -> None:
    dataset = build_dataset(
        [
            ("validation", "2026-07-10T16:00:00Z", build_historical_input()),
            ("test", "2026-07-11T16:00:00Z", build_historical_input()),
        ]
    )

    result = serialize(
        dataset,
        source=("validation", "validation"),
        evaluation=("test", "test"),
    )

    assert result["selection"]["source_partitions"] == ["validation"]
    assert result["selection"]["evaluation_partitions"] == ["test"]
    with pytest.raises(ValueError, match="must be disjoint"):
        serialize(dataset, source=("validation",), evaluation=("validation", "test"))


@pytest.mark.parametrize(
    ("source", "evaluation", "error_match"),
    [
        (("test",), ("validation",), "contain no source records"),
        (("train",), ("test",), "contain no target records"),
    ],
)
def test_rejects_empty_source_or_target_selection(source, evaluation, error_match) -> None:
    dataset = build_dataset(
        [
            ("train", "2026-07-10T16:00:00Z", build_historical_input()),
            ("validation", "2026-07-11T16:00:00Z", build_historical_input()),
        ]
    )

    with pytest.raises(ValueError, match=error_match):
        serialize(dataset, source=source, evaluation=evaluation)


def test_strict_as_of_excludes_equal_equivalent_and_later_source_instants() -> None:
    dataset = build_dataset(
        [
            ("train", "2026-07-09T16:00:00Z", build_historical_input()),
            ("train", "2026-07-10T18:00:00+02:00", build_historical_input()),
            ("train", "2026-07-11T16:00:00Z", build_historical_input()),
            ("validation", "2026-07-10T16:00:00Z", build_historical_input()),
        ]
    )

    result = serialize(dataset)
    target = result["target_games"][0]

    assert target["as_of_source_game_count"] == 1
    assert target["latest_eligible_source_played_at"] == "2026-07-09T16:00:00Z"
    assert all(
        profile["source_game_count"] == 1
        and profile["last_source_played_at"] == "2026-07-09T16:00:00Z"
        for profile in target["player_as_of_profiles"]
    )
    assert {decision["profile_prediction_status"] for decision in target["decisions"]} == {
        "insufficient_confidence"
    }


def test_target_before_source_is_retained_without_in_game_profile_updates() -> None:
    dataset = build_dataset(
        [
            ("validation", "2026-07-09T16:00:00Z", build_historical_input()),
            ("train", "2026-07-10T16:00:00Z", build_historical_input()),
            ("validation", "2026-07-11T16:00:00Z", build_historical_input()),
        ]
    )

    result = serialize(dataset)
    early, late = result["target_games"]

    assert early["as_of_source_game_count"] == 0
    assert {decision["profile_prediction_status"] for decision in early["decisions"]} == {
        "no_prior_source_games"
    }
    assert all(
        profile["source_game_count"] == 0 for profile in early["player_as_of_profiles"]
    )
    assert late["as_of_source_game_count"] == 1
    assert all(
        profile["source_game_count"] == 1 for profile in late["player_as_of_profiles"]
    )
    assert result["coverage"]["decisions_without_prior_source_games"] == 30


def test_case_sensitive_stable_identity_does_not_match_different_player_id() -> None:
    target = build_historical_input()
    target["players"][0]["player_id"] = "Player-A"
    target["players"][0].pop("player_label", None)
    for trick in target["tricks"]:
        if trick["leader_player_id"] == "player-a":
            trick["leader_player_id"] = "Player-A"
        for play in trick["plays"]:
            if play["player_id"] == "player-a":
                play["player_id"] = "Player-A"
    dataset = build_dataset(
        [
            ("train", "2026-07-10T16:00:00Z", build_historical_input()),
            ("validation", "2026-07-11T16:00:00Z", target),
        ]
    )

    result = serialize(dataset)
    profile = result["target_games"][0]["player_as_of_profiles"][0]

    assert profile["player_id"] == "Player-A"
    assert profile["profile_prediction_status"] == "no_player_history"
    assert result["coverage"]["decisions_without_player_history"] == 10


def test_rejects_invocation_without_any_target_participant_history() -> None:
    source = build_historical_input()
    mapping = {
        "player-a": "source-player-a",
        "player-b": "source-player-b",
        "player-c": "source-player-c",
    }
    for player in source["players"]:
        player["player_id"] = mapping[player["player_id"]]
        player.pop("player_label", None)
    source["declarer_player_id"] = mapping[source["declarer_player_id"]]
    for trick in source["tricks"]:
        trick["leader_player_id"] = mapping[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = mapping[play["player_id"]]
    dataset = build_dataset(
        [
            ("train", "2026-07-10T16:00:00Z", source),
            ("validation", "2026-07-11T16:00:00Z", build_historical_input()),
        ]
    )

    with pytest.raises(ValueError, match="at least one target participant"):
        serialize(dataset)


def build_actionable_dataset(source_game_count: int):
    target_game = build_historical_input()
    identity_rotation = {
        "player-a": "player-b",
        "player-b": "player-c",
        "player-c": "player-a",
    }
    for player in target_game["players"]:
        player["player_id"] = identity_rotation[player["player_id"]]
    target_game["declarer_player_id"] = identity_rotation[
        target_game["declarer_player_id"]
    ]
    for trick in target_game["tricks"]:
        trick["leader_player_id"] = identity_rotation[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = identity_rotation[play["player_id"]]
    base = build_dataset(
        [
            ("train", "2026-01-01T00:00:00Z", build_historical_input()),
            ("validation", "2030-01-01T00:00:00Z", target_game),
        ]
    )
    source_template, target = base.records
    start = datetime(2026, 1, 1, tzinfo=UTC)
    sources = tuple(
        replace(
            source_template,
            record_id=f"source-record-{index:03d}",
            historical_game=replace(
                source_template.historical_game,
                game_id=f"source-game-{index:03d}",
                played_at=(start + timedelta(days=index)).isoformat().replace("+00:00", "Z"),
            ),
        )
        for index in range(source_game_count)
    )
    return replace(base, records=(*sources, target))


@pytest.mark.parametrize(
    ("source_game_count", "expected_confidence"),
    [(100, "medium"), (500, "high")],
)
def test_medium_and_high_confidence_profiles_produce_actionable_paired_results(
    source_game_count: int,
    expected_confidence: str,
) -> None:
    dataset = build_actionable_dataset(source_game_count)

    result = serialize(dataset)
    target = result["target_games"][0]
    paired = result["actionable_profile_paired_results"]

    assert target["as_of_source_game_count"] == source_game_count
    assert {
        profile["profile_prediction_status"]
        for profile in target["player_as_of_profiles"]
    } == {"actionable"}
    assert {
        profile["profile_derivation"]["confidence"]["overall"]["level"]
        for profile in target["player_as_of_profiles"]
    } == {expected_confidence}
    assert {
        profile["profile_derivation"]["actionable_policy_preset"]
        for profile in target["player_as_of_profiles"]
    } == {"aggressive_points", "cautious_defender"}
    profiles_by_id = {
        profile["player_id"]: profile for profile in target["player_as_of_profiles"]
    }
    assert profiles_by_id["player-b"]["profile_derivation"][
        "actionable_policy_preset"
    ] == "aggressive_points"
    assert profiles_by_id["player-b"]["source_game_count"] == source_game_count
    assert target["participant_ids"] == ["player-b", "player-c", "player-a"]
    assert all(
        decision["actionable_profile_preset"]
        == profiles_by_id[decision["acting_player_id"]]["profile_derivation"][
            "actionable_policy_preset"
        ]
        for decision in target["decisions"]
    )
    assert paired["paired_decision_count"] == 30
    assert sum(paired["preferred_comparison_outcome_counts"].values()) == 30
    assert paired["profile_preferred_card_match_rate"] is not None
    assert paired["baseline_preferred_card_match_rate"] is not None
    assert paired["preferred_card_rate_delta_percentage_points"] == 10.0
    assert all(
        count > 0 for count in paired["preferred_comparison_outcome_counts"].values()
    )
    assert all(
        decision["profile_prediction"]["predicted_card"]
        in decision["profile_prediction"]["preferred_cards"]
        for decision in target["decisions"]
    )
    assert dataset == build_actionable_dataset(source_game_count)


def test_preferred_match_can_be_true_when_exact_card_match_is_false() -> None:
    dataset = build_actionable_dataset(100)
    target = dataset.records[-1]
    snapshot = build_historical_decision_snapshots(
        build_historical_game_summary(target.historical_game)
    ).snapshots[0]
    prediction = _build_prediction(
        replace(snapshot, actual_card_played="C8"),
        preset="simple_lowest",
        policy="lowest_point",
        partner_currently_winning=False,
    )

    assert prediction["predicted_card"] == "C9"
    assert prediction["preferred_cards"] == ["C9", "C8", "C7"]
    assert prediction["exact_card_match"] is False
    assert prediction["preferred_card_match"] is True


@pytest.mark.parametrize(
    ("profile_match", "baseline_match", "expected_delta"),
    [(True, False, 100.0), (True, True, 0.0), (False, True, -100.0)],
)
def test_paired_metric_delta_uses_only_actionable_decisions(
    profile_match: bool,
    baseline_match: bool,
    expected_delta: float,
) -> None:
    outcome = (
        "both_match"
        if profile_match and baseline_match
        else "profile_only"
        if profile_match
        else "baseline_only"
    )
    actionable = {
        "profile_prediction": {
            "exact_card_match": profile_match,
            "preferred_card_match": profile_match,
        },
        "baseline_prediction": {
            "exact_card_match": baseline_match,
            "preferred_card_match": baseline_match,
        },
        "exact_comparison_outcome": outcome,
        "preferred_comparison_outcome": outcome,
    }
    unavailable = {
        "profile_prediction": None,
        "baseline_prediction": {
            "exact_card_match": True,
            "preferred_card_match": True,
        },
        "exact_comparison_outcome": "not_available",
        "preferred_comparison_outcome": "not_available",
    }

    result = _build_paired_results([actionable, unavailable])

    assert result["paired_decision_count"] == 1
    assert result["preferred_card_rate_delta_percentage_points"] == expected_delta
    assert sum(result["preferred_comparison_outcome_counts"].values()) == 1


@pytest.mark.parametrize("played_card_count", [0, 1, 2, 14, 29])
def test_concession_targets_use_exact_variable_decision_cardinality(
    played_card_count: int,
) -> None:
    source = build_historical_input()
    target = build_concession_from_game(build_historical_input(), played_card_count)
    result = serialize(
        build_dataset(
            [
                ("train", "2026-07-10T16:00:00Z", source),
                ("validation", "2026-07-11T16:00:00Z", target),
            ]
        )
    )
    target_result = result["target_games"][0]

    assert target_result["decision_count"] == played_card_count
    assert len(target_result["decisions"]) == played_card_count
    assert [decision["decision_index"] for decision in target_result["decisions"]] == list(
        range(1, played_card_count + 1)
    )
    assert result["selection"]["target_decision_count"] == played_card_count
    assert result["coverage"]["target_decisions"] == played_card_count
    assert result["baseline_results"]["decision_count"] == played_card_count


def test_zero_decision_target_retains_profiles_participants_and_nullable_metrics() -> None:
    result = serialize(
        build_dataset(
            [
                ("train", "2026-07-10T16:00:00Z", build_historical_input()),
                (
                    "validation",
                    "2026-07-11T16:00:00Z",
                    build_concession_from_game(build_historical_input(), 0),
                ),
            ]
        )
    )
    target = result["target_games"][0]

    assert target["participant_ids"] == ["player-a", "player-b", "player-c"]
    assert len(target["player_as_of_profiles"]) == 3
    assert target["as_of_source_game_count"] == 1
    assert target["decision_count"] == 0
    assert target["decisions"] == []
    assert target["baseline_results"] == {
        "decision_count": 0,
        "exact_card_match_count": 0,
        "exact_card_match_rate": None,
        "preferred_card_match_count": 0,
        "preferred_card_match_rate": None,
    }
    assert target["actionable_profile_paired_results"]["paired_decision_count"] == 0
    assert result["coverage"]["target_game_count"] == 1
    assert result["coverage"]["target_player_game_count"] == 3
    assert result["coverage"]["distinct_target_player_count"] == 3
    assert result["coverage"]["target_decisions"] == 0
    assert all(rows == [] for rows in result["breakdowns"].values())


def test_mixed_concession_sources_have_equal_game_weight_and_strict_as_of_selection() -> None:
    normal_source = build_historical_input()
    zero_play_source = build_concession_from_game(build_historical_input(), 0)
    partial_source = build_concession_from_game(build_historical_input(), 14)
    target = build_concession_from_game(build_historical_input(), 2)
    result = serialize(
        build_dataset(
            [
                ("train", "2026-07-08T16:00:00Z", normal_source),
                ("train", "2026-07-09T16:00:00Z", zero_play_source),
                ("train", "2026-07-10T16:00:00Z", partial_source),
                ("train", "2026-07-11T18:00:00+02:00", partial_source),
                ("train", "2026-07-12T16:00:00Z", partial_source),
                ("validation", "2026-07-11T16:00:00Z", target),
            ]
        )
    )
    target_result = result["target_games"][0]

    assert target_result["as_of_source_game_count"] == 3
    assert target_result["latest_eligible_source_played_at"] == "2026-07-10T16:00:00Z"
    assert all(
        profile["source_game_count"] == 3
        and profile["source_record_ids"] == ["record-001", "record-002", "record-003"]
        and profile["exact_counts"] is not None
        for profile in target_result["player_as_of_profiles"]
    )


def test_normal_and_concession_shared_prefixes_have_identical_safe_decisions() -> None:
    source = build_historical_input()
    normal_target = build_historical_input()
    concession_target = build_concession_from_game(normal_target, 14)
    result = serialize(
        build_dataset(
            [
                ("train", "2026-07-10T16:00:00Z", source),
                ("validation", "2026-07-11T16:00:00Z", normal_target),
                ("validation", "2026-07-11T16:00:00Z", concession_target),
            ]
        )
    )
    normal, concession = result["target_games"]

    def without_game_id(decision: dict) -> dict:
        return {key: value for key, value in decision.items() if key != "game_id"}

    assert [without_game_id(decision) for decision in normal["decisions"][:14]] == [
        without_game_id(decision) for decision in concession["decisions"]
    ]
    serialized_decisions = str(concession["decisions"])
    for forbidden in (
        "game_end_reason",
        "concession",
        "consent",
        "winner",
        "settlement",
        "unresolved",
        "remaining",
    ):
        assert forbidden not in serialized_decisions


def test_concession_consent_does_not_change_rolling_decisions_or_profiles() -> None:
    target = build_concession_from_game(build_historical_input(), 14)
    changed_consent = copy.deepcopy(target)
    declarer_id = changed_consent["declarer_player_id"]
    changed_consent["game_end"]["defender_consent"][
        "consenting_defender_player_ids"
    ] = [
        player["player_id"]
        for player in changed_consent["players"]
        if player["player_id"] != declarer_id
    ]
    specs = [("train", "2026-07-10T16:00:00Z", build_historical_input())]

    original = serialize(
        build_dataset([*specs, ("validation", "2026-07-11T16:00:00Z", target)])
    )
    changed = serialize(
        build_dataset(
            [*specs, ("validation", "2026-07-11T16:00:00Z", changed_consent)]
        )
    )

    assert original == changed


def test_rolling_rejects_unsupported_selected_end_reason_with_record_and_game() -> None:
    dataset = build_dataset(
        [
            ("train", "2026-07-10T16:00:00Z", build_historical_input()),
            ("validation", "2026-07-11T16:00:00Z", build_historical_input()),
        ]
    )
    target = dataset.records[1]
    unsupported = replace(
        dataset,
        records=(
            dataset.records[0],
            replace(
                target,
                historical_game=replace(
                    target.historical_game,
                    game_end_reason="future_historical_end",
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "record-002.*dataset-game-2.*future_historical_end.*normal_completion"
            ".*declarer_concession"
        ),
    ):
        serialize(unsupported)
