import copy
from dataclasses import replace

import pytest
from test_historical_declarer_concession import build_concession_prefix
from test_historical_game import build_historical_input
from test_training_dataset import build_training_input

from skatmind.historical_game import build_historical_game_record
from skatmind.historical_opponent_profile_binding import (
    resolve_historical_opponent_profile_bindings,
)
from skatmind.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
    build_historical_opponent_statistics_aggregation_summary,
)
from skatmind.live_opponent_profile_binding import resolve_live_opponent_profile_bindings
from skatmind.opponent_statistics import (
    build_opponent_statistics_input,
    build_opponent_statistics_summary,
    build_serializable_opponent_statistics_input,
)
from skatmind.training_dataset import build_training_dataset_input


def build_dataset(
    game_specs: list[tuple[str, str, dict]] | None = None,
):
    specs = game_specs or [
        ("train", "2026-07-10T18:00:00+02:00", build_historical_input())
    ]
    games = []
    partitions = []
    for partition, played_at, game in specs:
        game = copy.deepcopy(game)
        game["played_at"] = played_at
        games.append(game)
        partitions.append(partition)
    return build_training_dataset_input(build_training_input(games, partitions))


def rotate_player_identities(game: dict) -> dict:
    game = copy.deepcopy(game)
    mapping = {"player-a": "player-b", "player-b": "player-c", "player-c": "player-a"}
    labels = {"player-a": "Alice", "player-b": None, "player-c": "Carol"}
    for player in game["players"]:
        player["player_id"] = mapping[player["player_id"]]
        label = labels[player["player_id"]]
        if label is None:
            player.pop("player_label", None)
        else:
            player["player_label"] = label
    game["declarer_player_id"] = mapping[game["declarer_player_id"]]
    for trick in game["tricks"]:
        trick["leader_player_id"] = mapping[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = mapping[play["player_id"]]
    return game


def aggregate(dataset, partitions=None, before=None):
    return aggregate_historical_opponent_statistics(
        dataset,
        included_partitions=partitions,
        before=before,
    )


def build_29_play_concession() -> dict:
    game = build_historical_input()
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
        ],
    }
    game.update(
        {
            "game_end_reason": "declarer_concession",
            "game_end": {
                "schema_version": 1,
                "kind": "declarer_concession",
                "declarer_hand_cards_remaining": 1,
                "defender_consent": {
                    "status": "granted",
                    "consenting_defender_player_ids": ["player-a"],
                },
            },
        }
    )
    return game


def test_selection_is_canonical_strict_and_deterministic() -> None:
    dataset = build_dataset(
        [
            ("validation", "2026-07-11T18:00:00+02:00", build_historical_input()),
            ("train", "2026-07-10T16:00:00Z", build_historical_input()),
            ("test", "2026-07-12T18:00:00+02:00", build_historical_input()),
        ]
    )

    first = aggregate(
        dataset,
        partitions=("validation", "train", "train"),
        before="2026-07-11T16:00:00Z",
    )
    second = aggregate(
        dataset,
        partitions=("train", "validation"),
        before="2026-07-11T18:00:00+02:00",
    )

    assert first.before != second.before
    assert first.records == second.records
    assert first.source_record_count == second.source_record_count
    assert first.included_partitions == ("train", "validation")
    assert first.source_record_count == 1
    assert first.excluded_record_counts_by_partition == {
        "train": 0,
        "validation": 0,
        "test": 1,
    }
    assert first.excluded_record_count_by_temporal_cutoff == 1


def test_default_selection_includes_all_populated_partitions() -> None:
    dataset = build_dataset(
        [
            ("test", "2026-07-12T18:00:00Z", build_historical_input()),
            ("train", "2026-07-10T18:00:00Z", build_historical_input()),
        ]
    )

    result = aggregate(dataset)

    assert result.included_partitions == ("train", "validation", "test")
    assert result.source_record_count == 2


@pytest.mark.parametrize(
    ("partitions", "before", "error_match"),
    [
        (("validation",), None, "contain no source records"),
        (("train",), "2026-07-10T16:00:00Z", "leaves no historical games"),
        ((), None, "At least one"),
    ],
)
def test_rejects_empty_selection_results(partitions, before, error_match: str) -> None:
    with pytest.raises(ValueError, match=error_match):
        aggregate(build_dataset(), partitions=partitions, before=before)


@pytest.mark.parametrize("before", [None, "2026-01-01T00:00:00Z"])
def test_requires_played_at_before_applying_temporal_filter(before) -> None:
    data = build_training_input([build_historical_input()], ["train"])
    dataset = build_training_dataset_input(data)

    with pytest.raises(ValueError, match="played_at is required"):
        aggregate(dataset, before=before)


def test_cutoff_excludes_later_games() -> None:
    result = aggregate(
        build_dataset(
            [
                ("train", "2026-07-10T18:00:00Z", build_historical_input()),
                ("train", "2026-07-12T18:00:00Z", build_historical_input()),
            ]
        ),
        before="2026-07-11T18:00:00Z",
    )

    assert result.source_game_count == 1
    assert result.excluded_record_count_by_temporal_cutoff == 1


def test_stable_case_sensitive_identity_labels_seats_and_first_appearance_order() -> None:
    first_game = build_historical_input()
    second_game = rotate_player_identities(first_game)
    extra_game = copy.deepcopy(first_game)
    extra_game["players"][0]["player_id"] = "Player-A"
    extra_game["players"][0].pop("player_label")
    for trick in extra_game["tricks"]:
        if trick["leader_player_id"] == "player-a":
            trick["leader_player_id"] = "Player-A"
        for play in trick["plays"]:
            if play["player_id"] == "player-a":
                play["player_id"] = "Player-A"
    dataset = build_dataset(
        [
            ("train", "2026-07-10T18:00:00Z", first_game),
            ("train", "2026-07-11T18:00:00Z", second_game),
            ("train", "2026-07-12T18:00:00Z", extra_game),
        ]
    )

    result = aggregate(dataset)

    assert [record.statistics_record.player_id for record in result.records] == [
        "player-a",
        "player-b",
        "player-c",
        "Player-A",
    ]
    player_a = result.records[0].statistics_record
    assert player_a.player_label == "Alice"
    assert player_a.games_played == 2


def test_null_then_consistent_label_resolves_and_conflicting_labels_reject() -> None:
    first = build_historical_input()
    first["players"][0].pop("player_label")
    second = copy.deepcopy(first)
    second["players"][0]["player_label"] = "Alice"
    resolved = aggregate(
        build_dataset(
            [
                ("train", "2026-07-10T18:00:00Z", first),
                ("train", "2026-07-11T18:00:00Z", second),
            ]
        )
    )
    assert resolved.records[0].statistics_record.player_label == "Alice"

    second["players"][0]["player_label"] = "ALICE"
    with pytest.raises(ValueError, match="Conflicting non-null player labels"):
        aggregate(
            build_dataset(
                [
                    ("train", "2026-07-10T18:00:00Z", build_historical_input()),
                    ("train", "2026-07-11T18:00:00Z", second),
                ]
            )
        )


def test_exact_counts_percentages_contracts_and_settlement_winner() -> None:
    specs = []
    for index, game_type in enumerate(
        ("clubs", "spades", "hearts", "diamonds", "grand", "null"),
        start=1,
    ):
        game = build_historical_input(
            game_type=game_type,
            hand_game=game_type == "clubs",
            declarer_player_id="player-a",
            bid_value=18,
        )
        specs.append(("train", f"2026-07-{index:02d}T18:00:00Z", game))
    result = aggregate(build_dataset(specs))
    player_a = result.records[0].statistics_record
    counts = player_a.exact_counts
    assert counts is not None
    assert counts.solo_games_played == 6
    assert counts.solo_hand_games == 1
    assert counts.suit_games == 4
    assert counts.grand_games == 1
    assert counts.null_games == 1
    assert counts.defender_games_played == 0
    assert player_a.statistics.solo_games_played_percent == 100.0
    assert player_a.statistics.suit_games_percent == pytest.approx(200 / 3)
    assert player_a.statistics.grand_games_percent == pytest.approx(100 / 6)
    assert player_a.statistics.defender_games_won_percent == 0.0

    overbid = build_historical_input(
        declarer_player_id="player-a",
        bid_value=60,
    )
    overbid_result = aggregate(
        build_dataset([("train", "2026-07-20T18:00:00Z", overbid)])
    )
    declarer_counts = overbid_result.records[0].statistics_record.exact_counts
    defender_counts = overbid_result.records[1].statistics_record.exact_counts
    assert declarer_counts is not None and defender_counts is not None
    assert declarer_counts.solo_games_won == 0
    assert defender_counts.defender_games_won == 1
    assert overbid_result.records[2].statistics_record.exact_counts == defender_counts


def test_one_third_two_thirds_and_zero_declarer_denominator() -> None:
    games = [
        build_historical_input(declarer_player_id=declarer)
        for declarer in ("player-a", "player-b", "player-b")
    ]
    result = aggregate(
        build_dataset(
            [
                ("train", f"2026-07-{index:02d}T18:00:00Z", game)
                for index, game in enumerate(games, start=1)
            ]
        )
    )
    player_a = result.records[0].statistics_record
    player_c = result.records[2].statistics_record
    assert player_a.statistics.solo_games_played_percent == pytest.approx(100 / 3)
    assert player_a.statistics.defender_games_played_percent == pytest.approx(200 / 3)
    assert player_c.statistics.solo_games_played_percent == 0.0
    assert player_c.statistics.solo_games_won_percent == 0.0
    assert player_c.statistics.suit_games_percent == 0.0


def test_export_round_trips_and_supports_live_and_strict_historical_bindings() -> None:
    dataset = build_dataset()
    original_dataset = copy.deepcopy(dataset)
    aggregation = aggregate(dataset)
    export_input = build_exportable_opponent_statistics_input(aggregation)
    serialized = build_serializable_opponent_statistics_input(export_input)
    round_tripped = build_opponent_statistics_input(serialized["opponent_statistics_input"])
    summary = build_opponent_statistics_summary(round_tripped)

    assert build_exportable_opponent_statistics_input(aggregation) == export_input
    assert dataset == original_dataset
    assert summary["records"][0]["exact_counts"] == serialized[
        "opponent_statistics_input"
    ]["records"][0]["exact_counts"]
    assert summary["records"][0]["profile_derivation"]["confidence"]["declarer"][
        "evidence_kind"
    ] == "exact"
    live = resolve_live_opponent_profile_bindings(
        round_tripped,
        left_player_id="player-a",
        right_player_id="player-c",
    )
    assert live.left is not None and live.right is not None

    target = build_historical_input()
    target["played_at"] = "2026-07-11T18:00:00+02:00"
    historical = resolve_historical_opponent_profile_bindings(
        build_historical_game_record(target),
        round_tripped,
        "export.json",
    )
    assert historical.application_summary["matched_player_count"] == 3

    target["played_at"] = "2026-07-10T18:00:00+02:00"
    with pytest.raises(ValueError, match="must be strictly before"):
        resolve_historical_opponent_profile_bindings(
            build_historical_game_record(target),
            round_tripped,
            "export.json",
        )


def test_summary_has_no_training_samples_or_policy_application() -> None:
    summary = build_historical_opponent_statistics_aggregation_summary(
        aggregate(build_dataset())
    )

    assert summary["source_record_count"] == summary["source_game_count"] == 1
    assert summary["player_count"] == 3
    assert "samples" not in str(summary)
    assert "recommendation" not in str(summary)
    assert "policy_application" not in str(summary)


@pytest.mark.parametrize("mode", ["known_opponent", "unseen_player"])
def test_aggregation_accepts_compliant_partition_policies_and_preserves_provenance(
    mode: str,
) -> None:
    game = build_historical_input()
    game["played_at"] = "2026-07-10T16:00:00Z"
    data = build_training_input([game], ["train"])
    data["partition_policy"] = {"policy_version": 1, "mode": mode}
    dataset = build_training_dataset_input(data)
    summary = build_historical_opponent_statistics_aggregation_summary(
        aggregate(dataset)
    )

    assert summary["source_dataset"]["partition_policy"] == data["partition_policy"]
    assert summary["source_game_count"] == 1


@pytest.mark.parametrize(
    ("completed_tricks", "current_trick_cards", "expected_plays"),
    [(0, 0, 0), (0, 1, 1), (1, 0, 3), (4, 2, 14), (9, 2, 29)],
)
def test_concessions_contribute_one_settled_game_independent_of_play_count(
    completed_tricks: int,
    current_trick_cards: int,
    expected_plays: int,
) -> None:
    game = (
        build_29_play_concession()
        if expected_plays == 29
        else build_concession_prefix(
            completed_trick_count=completed_tricks,
            current_trick_card_count=current_trick_cards,
        )
    )
    result = aggregate(
        build_dataset([("train", "2026-07-10T18:00:00Z", game)])
    )
    records = {
        record.statistics_record.player_id: record.statistics_record
        for record in result.records
    }
    declarer = records[game["declarer_player_id"]]
    defender_ids = set(records) - {game["declarer_player_id"]}

    assert sum(len(trick["plays"]) for trick in game["tricks"]) == expected_plays
    assert result.source_record_count == result.source_game_count == 1
    assert all(record.games_played == 1 for record in records.values())
    assert declarer.exact_counts is not None
    assert declarer.exact_counts.solo_games_played == 1
    assert declarer.exact_counts.solo_games_won == 0
    assert all(
        records[player_id].exact_counts is not None
        and records[player_id].exact_counts.defender_games_played == 1
        and records[player_id].exact_counts.defender_games_won == 1
        for player_id in defender_ids
    )


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert", "category"),
    [
        ("clubs", False, False, "suit_games"),
        ("spades", False, False, "suit_games"),
        ("hearts", False, False, "suit_games"),
        ("diamonds", False, False, "suit_games"),
        ("grand", True, False, "grand_games"),
        ("null", False, False, "null_games"),
        ("null", True, False, "null_games"),
        ("null", False, True, "null_games"),
        ("null", True, True, "null_games"),
    ],
)
def test_concession_contract_and_hand_counts_use_existing_categories(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
    category: str,
) -> None:
    game = build_concession_prefix()
    game["declaration"] = {
        "game_type": game_type,
        "hand_game": hand_game,
        "ouvert": ouvert,
        "bid_value": 18,
    }
    game["discarded_cards"] = [] if hand_game else ["SK", "SQ"]

    result = aggregate(
        build_dataset([("train", "2026-07-10T18:00:00Z", game)])
    )
    declarer = next(
        record.statistics_record
        for record in result.records
        if record.statistics_record.player_id == game["declarer_player_id"]
    )
    counts = declarer.exact_counts

    assert counts is not None
    assert getattr(counts, category) == 1
    assert counts.solo_hand_games == int(hand_game)


def test_mixed_concession_aggregation_preserves_provenance_export_and_consent_isolation(
) -> None:
    normal = build_historical_input()
    concession = build_concession_prefix(
        completed_trick_count=4,
        current_trick_card_count=2,
    )
    dataset = build_dataset(
        [
            ("train", "2026-07-10T18:00:00Z", normal),
            ("train", "2026-07-11T18:00:00Z", concession),
        ]
    )
    aggregation = aggregate(dataset)
    summary = build_historical_opponent_statistics_aggregation_summary(aggregation)
    serialized = build_serializable_opponent_statistics_input(
        build_exportable_opponent_statistics_input(aggregation)
    )

    assert summary["source_record_count"] == summary["source_game_count"] == 2
    assert summary["first_played_at"] == "2026-07-10T18:00:00Z"
    assert summary["last_played_at"] == "2026-07-11T18:00:00Z"
    assert all(record["games_played"] == 2 for record in summary["records"])
    assert all(
        record["source"]["historical_aggregation"]["source_record_ids"]
        == ["record-001", "record-002"]
        for record in summary["records"]
    )
    assert build_opponent_statistics_input(serialized["opponent_statistics_input"])

    changed_consent = copy.deepcopy(concession)
    changed_consent["game_end"]["defender_consent"][
        "consenting_defender_player_ids"
    ] = ["player-a", "player-c"]
    original_record = aggregate(
        build_dataset([("train", "2026-07-11T18:00:00Z", concession)])
    ).records
    changed_record = aggregate(
        build_dataset([("train", "2026-07-11T18:00:00Z", changed_consent)])
    ).records
    assert original_record == changed_record


def test_unsupported_selected_end_reason_names_record_game_and_supported_reasons() -> None:
    dataset = build_dataset()
    record = dataset.records[0]
    unsupported = replace(
        dataset,
        records=(
            replace(
                record,
                historical_game=replace(
                    record.historical_game,
                    game_end_reason="future_historical_end",
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "record-001.*dataset-game-1.*future_historical_end.*normal_completion"
            ".*declarer_concession"
        ),
    ):
        aggregate(unsupported)
