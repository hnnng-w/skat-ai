import copy
from dataclasses import FrozenInstanceError

import pytest
from test_historical_declarer_card_exposure import build_exposure_prefix
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_defender_open_play import build_open_play_prefix
from test_historical_game import build_historical_input
from test_historical_game_event_chain import add_continuation
from test_historical_open_card_throw import build_throw_prefix

from skat_ai.fixed_three_player_historical_list import (
    FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION,
    FIXED_THREE_PLAYER_LIST_ENTRIES_PER_ROUND,
    FIXED_THREE_PLAYER_LIST_ENTRY_COUNT,
    FIXED_THREE_PLAYER_LIST_ENTRY_KINDS,
    FIXED_THREE_PLAYER_LIST_ENTRY_OUTCOMES,
    FIXED_THREE_PLAYER_LIST_PLAYER_COUNT,
    FIXED_THREE_PLAYER_LIST_ROUND_COUNT,
    FixedThreePlayerHistoricalListPlayer,
    build_fixed_three_player_historical_list,
    build_fixed_three_player_historical_list_entry_facts,
    build_serializable_fixed_three_player_historical_list,
    build_serializable_fixed_three_player_historical_list_entry_facts,
)
from skat_ai.fixed_three_player_list_contribution import (
    FixedThreePlayerListContribution,
    build_fixed_three_player_list_contributions,
)
from skat_ai.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
    FixedThreePlayerListSeatAssignment,
    build_fixed_three_player_list_seat_assignment,
)
from skat_ai.performance_rating import (
    build_list_performance_summary,
    build_list_performance_summary_from_game_contributions,
    build_list_standings_summary,
)

PLAYER_IDS_BY_PLACE = {
    "place_1": "player-a",
    "place_2": "player-b",
    "place_3": "player-c",
}
SOURCE_PLAYER_IDS_BY_SEAT = {
    "forehand": "player-a",
    "middlehand": "player-b",
    "rearhand": "player-c",
}


def build_passed_entry(entry_number: int, played_at: str | None = None) -> dict:
    return {
        "entry_id": f"entry-{entry_number:03d}",
        "entry_kind": "passed_deal",
        "played_at": played_at,
    }


def replace_player_ids(value, replacements: dict[str, str]):
    if isinstance(value, str):
        return replacements.get(value, value)
    if isinstance(value, list):
        return [replace_player_ids(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: replace_player_ids(item, replacements)
            for key, item in value.items()
        }
    return value


def rotate_historical_game(
    historical_game: dict,
    entry_number: int,
    *,
    game_id: str | None = None,
    keep_labels: bool = False,
) -> dict:
    assignment = build_fixed_three_player_list_seat_assignment(
        entry_number,
        PLAYER_IDS_BY_PLACE,
    )
    expected_by_seat = {
        "forehand": assignment.forehand_player_id,
        "middlehand": assignment.middlehand_player_id,
        "rearhand": assignment.rearhand_player_id,
    }
    replacements = {
        source_player_id: expected_by_seat[seat]
        for seat, source_player_id in SOURCE_PLAYER_IDS_BY_SEAT.items()
    }
    result = replace_player_ids(copy.deepcopy(historical_game), replacements)
    result["game_id"] = game_id or f"game-{entry_number:03d}"
    if not keep_labels:
        for player in result["players"]:
            player.pop("player_label", None)
    return result


def build_list_input(
    *,
    played_games: dict[int, dict] | None = None,
    players: list[dict] | None = None,
) -> dict:
    entries = [build_passed_entry(entry_number) for entry_number in range(1, 37)]
    for entry_number, historical_game in (played_games or {}).items():
        entries[entry_number - 1] = {
            "entry_id": f"entry-{entry_number:03d}",
            "entry_kind": "played_game",
            "historical_game": rotate_historical_game(
                historical_game,
                entry_number,
            ),
        }
    return {
        "schema_version": 1,
        "list_id": "list-001",
        "players": players
        or [
            {"player_id": "player-a", "table_place": "place_1"},
            {"player_id": "player-b", "table_place": "place_2"},
            {"player_id": "player-c", "table_place": "place_3"},
        ],
        "entries": entries,
    }


def build_one_played_list(historical_game: dict, entry_number: int = 1):
    return build_fixed_three_player_historical_list(
        build_list_input(played_games={entry_number: historical_game})
    )


def contribution_by_player(fact) -> dict[str, FixedThreePlayerListContribution]:
    return {
        contribution.player_id: contribution
        for contribution in fact.player_contributions
    }


def test_version_one_constants_and_canonical_tuples_are_stable() -> None:
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION == 1
    assert FIXED_THREE_PLAYER_LIST_PLAYER_COUNT == 3
    assert FIXED_THREE_PLAYER_LIST_ENTRY_COUNT == 36
    assert FIXED_THREE_PLAYER_LIST_ENTRIES_PER_ROUND == 3
    assert FIXED_THREE_PLAYER_LIST_ROUND_COUNT == 12
    assert FIXED_THREE_PLAYER_LIST_TABLE_PLACES == (
        "place_1",
        "place_2",
        "place_3",
    )
    assert FIXED_THREE_PLAYER_LIST_ENTRY_KINDS == ("played_game", "passed_deal")
    assert FIXED_THREE_PLAYER_LIST_ENTRY_OUTCOMES == (
        "declarer_win",
        "declarer_loss",
        "passed_deal",
    )


def test_new_contract_values_are_frozen() -> None:
    historical_list = build_fixed_three_player_historical_list(build_list_input())
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)

    frozen_values = [
        historical_list,
        historical_list.players[0],
        historical_list.entries[0],
        facts[0],
        facts[0].seat_assignment,
        facts[0].player_contributions[0],
    ]
    for value in frozen_values:
        with pytest.raises(FrozenInstanceError):
            value.schema_version = 2


@pytest.mark.parametrize("player_count", [2, 4])
def test_list_requires_exact_player_cardinality(player_count: int) -> None:
    data = build_list_input()
    data["players"] = data["players"][:player_count]
    if player_count == 4:
        data["players"].append(
            {"player_id": "player-d", "table_place": "place_3"}
        )

    with pytest.raises(ValueError, match="exactly three players"):
        build_fixed_three_player_historical_list(data)


@pytest.mark.parametrize("entry_count", [35, 37])
def test_list_requires_exact_entry_cardinality(entry_count: int) -> None:
    data = build_list_input()
    data["entries"] = data["entries"][:entry_count]
    if entry_count == 37:
        data["entries"].append(build_passed_entry(37))

    with pytest.raises(ValueError, match="exactly 36 entries"):
        build_fixed_three_player_historical_list(data)


def test_players_require_unique_ids_places_and_canonical_place_order() -> None:
    duplicate_id = build_list_input()
    duplicate_id["players"][1]["player_id"] = "player-a"
    with pytest.raises(ValueError, match="duplicate player_id"):
        build_fixed_three_player_historical_list(duplicate_id)

    duplicate_place = build_list_input()
    duplicate_place["players"][1]["table_place"] = "place_1"
    with pytest.raises(ValueError, match="canonical order"):
        build_fixed_three_player_historical_list(duplicate_place)

    reordered = build_list_input()
    reordered["players"][0], reordered["players"][1] = (
        reordered["players"][1],
        reordered["players"][0],
    )
    with pytest.raises(ValueError, match="canonical order"):
        build_fixed_three_player_historical_list(reordered)


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("list_id",), " list-001"),
        (("players", 0, "player_id"), "Player-A "),
        (("players", 0, "player_label"), " "),
        (("entries", 0, "entry_id"), "entry-001 "),
    ],
)
def test_stable_identity_and_label_values_are_not_normalized(
    field_path: tuple,
    value,
) -> None:
    data = build_list_input()
    if field_path[-1] == "player_label":
        data["players"][0]["player_label"] = None
    target = data
    for part in field_path[:-1]:
        target = target[part]
    target[field_path[-1]] = value

    with pytest.raises(ValueError, match="without leading or trailing whitespace"):
        build_fixed_three_player_historical_list(data)


def test_labels_are_nullable_and_use_the_one_non_null_label_canonically() -> None:
    game = rotate_historical_game(
        build_historical_input(game_type="null", declarer_player_id="player-b"),
        1,
        keep_labels=True,
    )
    data = build_list_input()
    data["entries"][0] = {
        "entry_id": "entry-001",
        "entry_kind": "played_game",
        "historical_game": game,
    }

    historical_list = build_fixed_three_player_historical_list(data)
    labels = {player.player_id: player.player_label for player in historical_list.players}

    assert labels == {
        "player-a": "Carol",
        "player-b": "Alice",
        "player-c": None,
    }


def test_distinct_non_null_labels_for_one_stable_player_are_rejected() -> None:
    game = rotate_historical_game(
        build_historical_input(game_type="null", declarer_player_id="player-b"),
        1,
        keep_labels=True,
    )
    data = build_list_input(
        players=[
            {"player_id": "player-a", "player_label": "Different", "table_place": "place_1"},
            {"player_id": "player-b", "table_place": "place_2"},
            {"player_id": "player-c", "table_place": "place_3"},
        ]
    )
    data["entries"][0] = {
        "entry_id": "entry-001",
        "entry_kind": "played_game",
        "historical_game": game,
    }

    with pytest.raises(ValueError, match="conflicting non-null labels"):
        build_fixed_three_player_historical_list(data)


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (
            {
                "entry_id": "entry-001",
                "entry_kind": "passed_deal",
                "played_at": None,
                "historical_game": {},
            },
            "unsupported fields",
        ),
        (
            {
                "entry_id": "entry-001",
                "entry_kind": "played_game",
                "historical_game": {},
                "played_at": None,
            },
            "unsupported fields",
        ),
        (
            {"entry_id": "entry-001", "entry_kind": "future_kind", "played_at": None},
            "entry_kind",
        ),
    ],
)
def test_played_and_passed_entries_form_a_strict_union(entry: dict, message: str) -> None:
    data = build_list_input()
    data["entries"][0] = entry

    with pytest.raises(ValueError, match=message):
        build_fixed_three_player_historical_list(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data.update({"lot_order": []}),
        lambda data: data["players"][0].update({"rating": 100}),
        lambda data: data["entries"][0].update({"standing": 1}),
    ],
)
def test_unknown_list_fields_are_rejected_recursively(mutation) -> None:
    data = build_list_input()
    mutation(data)

    with pytest.raises(ValueError, match="unsupported fields"):
        build_fixed_three_player_historical_list(data)


def test_unknown_nested_historical_game_fields_are_rejected() -> None:
    data = build_list_input(played_games={1: build_historical_input()})
    data["entries"][0]["historical_game"]["declaration"]["winner"] = "declarer"

    with pytest.raises(ValueError, match="unsupported fields"):
        build_fixed_three_player_historical_list(data)


def test_duplicate_entry_and_historical_game_ids_are_rejected() -> None:
    duplicate_entry = build_list_input()
    duplicate_entry["entries"][1]["entry_id"] = "entry-001"
    with pytest.raises(ValueError, match="duplicate entry_id"):
        build_fixed_three_player_historical_list(duplicate_entry)

    first_game = build_historical_input(game_type="null", declarer_player_id="player-b")
    second_game = copy.deepcopy(first_game)
    duplicate_game = build_list_input(played_games={1: first_game, 2: second_game})
    duplicate_game["entries"][1]["historical_game"]["game_id"] = duplicate_game[
        "entries"
    ][0]["historical_game"]["game_id"]
    with pytest.raises(ValueError, match="duplicate historical game IDs"):
        build_fixed_three_player_historical_list(duplicate_game)


def test_all_positions_rounds_and_passed_deal_rotations_are_authoritative() -> None:
    historical_list = build_fixed_three_player_historical_list(build_list_input())
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)

    assert len(facts) == 36
    assert [fact.entry_number for fact in facts] == list(range(1, 37))
    assert [fact.round_number for fact in facts] == [
        round_number for round_number in range(1, 13) for _ in range(3)
    ]
    assert [fact.dealer_player_id for fact in facts] == [
        "player-a",
        "player-b",
        "player-c",
    ] * 12
    assert facts[0].seat_assignment == FixedThreePlayerListSeatAssignment(
        dealer_player_id="player-a",
        forehand_player_id="player-b",
        middlehand_player_id="player-c",
        rearhand_player_id="player-a",
    )
    assert all(fact.entry_outcome == "passed_deal" for fact in facts)
    assert all(fact.game_id is None and fact.settlement_score is None for fact in facts)


def test_rotation_helper_rejects_duplicate_or_padded_player_ids() -> None:
    with pytest.raises(ValueError, match="three distinct players"):
        build_fixed_three_player_list_seat_assignment(
            1,
            {place: "same-player" for place in FIXED_THREE_PLAYER_LIST_TABLE_PLACES},
        )
    with pytest.raises(ValueError, match="stable player IDs"):
        build_fixed_three_player_list_seat_assignment(
            1,
            {
                "place_1": "player-a ",
                "place_2": "player-b",
                "place_3": "player-c",
            },
        )


def test_played_historical_seats_must_match_the_derived_rotation() -> None:
    data = build_list_input()
    game = rotate_historical_game(build_historical_input(), 2)
    data["entries"][0] = {
        "entry_id": "entry-001",
        "entry_kind": "played_game",
        "historical_game": game,
    }

    with pytest.raises(ValueError, match="seats do not match"):
        build_fixed_three_player_historical_list(data)


def test_played_game_requires_exact_stable_participant_set() -> None:
    data = build_list_input()
    game = rotate_historical_game(build_historical_input(), 1)
    game = replace_player_ids(game, {"player-b": "substitute"})
    data["entries"][0] = {
        "entry_id": "entry-001",
        "entry_kind": "played_game",
        "historical_game": game,
    }

    with pytest.raises(ValueError, match="exact fixed list players"):
        build_fixed_three_player_historical_list(data)


def test_present_timestamps_allow_equal_and_missing_but_must_not_decrease() -> None:
    data = build_list_input()
    data["entries"][0]["played_at"] = "2026-08-05T10:00:00+02:00"
    data["entries"][2]["played_at"] = "2026-08-05T08:00:00Z"
    build_fixed_three_player_historical_list(data)

    data["entries"][3]["played_at"] = "2026-08-05T07:59:59Z"
    with pytest.raises(ValueError, match="non-decreasing"):
        build_fixed_three_player_historical_list(data)


def test_played_game_timestamp_is_used_for_chronology_and_facts() -> None:
    game = build_historical_input(game_type="null", declarer_player_id="player-b")
    game["played_at"] = "2026-08-05T08:00:00Z"
    data = build_list_input(played_games={2: game})
    data["entries"][0]["played_at"] = "2026-08-05T07:00:00Z"

    historical_list = build_fixed_three_player_historical_list(data)
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[1]

    assert fact.played_at == "2026-08-05T08:00:00Z"


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert"),
    [
        ("clubs", True, False),
        ("spades", True, False),
        ("hearts", True, False),
        ("diamonds", True, False),
        ("grand", False, False),
        ("null", False, False),
        ("null", True, False),
        ("null", False, True),
        ("null", True, True),
    ],
)
def test_all_current_historical_game_types_extract_complete_settlement(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
) -> None:
    game = build_historical_input(game_type=game_type, hand_game=hand_game)
    if ouvert:
        game["declaration"]["ouvert"] = True
    historical_list = build_one_played_list(game)
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]

    assert fact.game_id == "game-001"
    assert fact.game_end_reason == "normal_completion"
    assert fact.entry_outcome in {"declarer_win", "declarer_loss"}
    assert fact.settlement_score is not None


@pytest.mark.parametrize(
    "builder",
    [
        build_concession_prefix,
        build_defender_concession_prefix,
        build_exposure_prefix,
        build_open_play_prefix,
        build_throw_prefix,
    ],
)
def test_all_current_historical_terminal_endings_are_supported(builder) -> None:
    historical_list = build_one_played_list(builder())
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]

    assert fact.game_end_reason in {
        "declarer_concession",
        "defender_concession",
        "declarer_card_exposure",
        "defender_open_play",
        "open_card_throw",
    }
    assert fact.settlement_score is not None


@pytest.mark.parametrize(
    "continuation_kind",
    [
        "defender_open_play_continuation",
        "declarer_card_exposure_continuation",
    ],
)
def test_both_current_non_terminal_historical_continuations_are_supported(
    continuation_kind: str,
) -> None:
    game = add_continuation(build_historical_input(), continuation_kind)
    historical_list = build_one_played_list(game)
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]

    assert fact.game_end_reason == "normal_completion"
    assert fact.settlement_score is not None


@pytest.mark.parametrize(
    "continuation_kind",
    [
        "defender_open_play_continuation",
        "declarer_card_exposure_continuation",
    ],
)
def test_continuation_before_terminal_shortening_is_supported(
    continuation_kind: str,
) -> None:
    game = build_defender_concession_prefix(
        completed_trick_count=5,
        current_trick_card_count=2,
    )
    historical_list = build_one_played_list(add_continuation(game, continuation_kind))
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]

    assert fact.game_end_reason == "defender_concession"
    assert fact.settlement_score is not None


def test_shortened_game_with_incomplete_final_trick_is_supported() -> None:
    historical_list = build_one_played_list(
        build_concession_prefix(
            completed_trick_count=4,
            current_trick_card_count=2,
        )
    )
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]

    assert fact.game_end_reason == "declarer_concession"
    assert fact.settlement_score is not None


def test_incomplete_historical_settlement_is_rejected(monkeypatch) -> None:
    from skat_ai import fixed_three_player_historical_list as list_module

    original = list_module.build_historical_game_summary

    def build_incomplete_summary(record):
        summary = original(record)
        summary["final_settlement_summary"] = {
            **summary["final_settlement_summary"],
            "is_complete": False,
        }
        return summary

    monkeypatch.setattr(list_module, "build_historical_game_summary", build_incomplete_summary)

    with pytest.raises(ValueError, match="complete final settlement"):
        build_one_played_list(build_historical_input())


def test_incomplete_historical_summary_status_is_rejected(monkeypatch) -> None:
    from skat_ai import fixed_three_player_historical_list as list_module

    original = list_module.build_historical_game_summary

    def build_incomplete_summary(record):
        return {**original(record), "status": "incomplete"}

    monkeypatch.setattr(list_module, "build_historical_game_summary", build_incomplete_summary)

    with pytest.raises(ValueError, match="summary must be complete"):
        build_one_played_list(build_historical_input())


def test_declarer_win_contributions_use_settlement_and_plus_fifty() -> None:
    historical_list = build_one_played_list(
        build_historical_input(game_type="null", declarer_player_id="player-b")
    )
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]
    rows = contribution_by_player(fact)
    declarer = rows[fact.declarer_player_id]
    defenders = [row for player_id, row in rows.items() if player_id != fact.declarer_player_id]

    assert fact.entry_outcome == "declarer_win"
    assert declarer.player_game_points == fact.settlement_score
    assert declarer.own_games_won == 1
    assert declarer.own_game_bonus_points == 50
    assert declarer.total_performance_points == fact.settlement_score + 50
    assert all(row.defender_games_lost == 1 for row in defenders)
    assert all(row.opponent_loss_bonus_points == 0 for row in defenders)


def test_declarer_loss_contributions_award_both_defenders_plus_forty() -> None:
    historical_list = build_one_played_list(
        build_historical_input(game_type="null", declarer_player_id="player-a")
    )
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]
    rows = contribution_by_player(fact)
    declarer = rows[fact.declarer_player_id]
    defenders = [row for player_id, row in rows.items() if player_id != fact.declarer_player_id]

    assert fact.entry_outcome == "declarer_loss"
    assert declarer.player_game_points == fact.settlement_score
    assert declarer.own_games_lost == 1
    assert declarer.own_game_bonus_points == -50
    assert declarer.total_performance_points == fact.settlement_score - 50
    assert all(row.defender_games_won == 1 for row in defenders)
    assert all(row.other_players_lost_games == 1 for row in defenders)
    assert all(row.opponent_loss_bonus_points == 40 for row in defenders)
    assert all(row.total_performance_points == 40 for row in defenders)


def test_passed_deal_contributions_are_zero_and_not_defender_games() -> None:
    historical_list = build_fixed_three_player_historical_list(build_list_input())
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]

    assert fact.entry_outcome == "passed_deal"
    for contribution in fact.player_contributions:
        assert contribution.list_entry_count == 1
        assert contribution.passed_deal_count == 1
        assert contribution.played_game_count == 0
        assert contribution.declarer_game_count == 0
        assert contribution.defender_game_count == 0
        assert contribution.total_performance_points == 0


@pytest.mark.parametrize(
    ("player_ids", "entry_outcome", "declarer_player_id", "settlement_score", "message"),
    [
        (
            ("player-a", "player-b"),
            "passed_deal",
            None,
            None,
            "exactly three players",
        ),
        (
            ("player-a", "player-a", "player-c"),
            "passed_deal",
            None,
            None,
            "three distinct players",
        ),
        (
            ("player-a", "player-b", "player-c"),
            "declarer_win",
            "player-a",
            -24,
            "positive settlement score",
        ),
        (
            ("player-a", "player-b", "player-c"),
            "declarer_loss",
            "player-a",
            24,
            "negative settlement score",
        ),
    ],
)
def test_contribution_helper_rejects_invalid_contract_inputs(
    player_ids,
    entry_outcome,
    declarer_player_id,
    settlement_score,
    message,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_fixed_three_player_list_contributions(
            player_ids=player_ids,
            entry_outcome=entry_outcome,
            declarer_player_id=declarer_player_id,
            settlement_score=settlement_score,
        )


def test_entry_facts_reconcile_role_bonus_and_player_order() -> None:
    historical_list = build_fixed_three_player_historical_list(
        build_list_input(
            played_games={
                1: build_historical_input(
                    game_type="null",
                    declarer_player_id="player-b",
                ),
                2: build_historical_input(
                    game_type="null",
                    declarer_player_id="player-a",
                ),
            }
        )
    )
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)

    assert len(facts) == 36
    assert sum(fact.entry_kind == "played_game" for fact in facts) == 2
    assert sum(fact.entry_kind == "passed_deal" for fact in facts) == 34
    assert all(
        tuple(row.player_id for row in fact.player_contributions)
        == ("player-a", "player-b", "player-c")
        for fact in facts
    )
    assert sum(
        row.opponent_loss_bonus_points == 40
        for fact in facts
        for row in fact.player_contributions
    ) == 2


def test_list_and_fact_serialization_are_deterministic_and_round_trip() -> None:
    historical_list = build_one_played_list(
        build_historical_input(game_type="null", declarer_player_id="player-b")
    )
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)

    first_list_data = build_serializable_fixed_three_player_historical_list(
        historical_list
    )
    second_list_data = build_serializable_fixed_three_player_historical_list(
        historical_list
    )
    round_trip = build_fixed_three_player_historical_list(first_list_data)
    serialized_facts = build_serializable_fixed_three_player_historical_list_entry_facts(
        facts
    )

    assert first_list_data == second_list_data
    assert round_trip == historical_list
    assert serialized_facts == (
        build_serializable_fixed_three_player_historical_list_entry_facts(facts)
    )
    assert [player["player_id"] for player in first_list_data["players"]] == [
        "player-a",
        "player-b",
        "player-c",
    ]
    assert [entry["entry_id"] for entry in first_list_data["entries"]] == [
        f"entry-{entry_number:03d}" for entry_number in range(1, 37)
    ]
    assert serialized_facts[1]["game_id"] is None
    assert serialized_facts[1]["settlement_score"] is None


def test_list_contract_defensively_copies_raw_input_and_is_hashable() -> None:
    data = build_list_input()
    historical_list = build_fixed_three_player_historical_list(data)

    data["players"][0]["player_id"] = "mutated"
    data["entries"][0]["entry_id"] = "mutated"

    assert historical_list.players[0].player_id == "player-a"
    assert historical_list.entries[0].entry_id == "entry-001"
    assert isinstance(hash(historical_list), int)


def test_all_36_positions_may_be_played_with_unique_rotating_games() -> None:
    played_games = {
        entry_number: build_historical_input(
            game_type="null",
            declarer_player_id=(
                "player-b" if entry_number % 2 else "player-a"
            ),
        )
        for entry_number in range(1, 37)
    }
    historical_list = build_fixed_three_player_historical_list(
        build_list_input(played_games=played_games)
    )
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)

    assert len(facts) == 36
    assert all(fact.entry_kind == "played_game" for fact in facts)
    assert len({fact.game_id for fact in facts}) == 36


def test_existing_performance_inputs_and_standings_remain_unchanged() -> None:
    assert build_list_performance_summary(
        {
            "player_game_points": 120,
            "own_games_won": 3,
            "own_games_lost": 1,
            "other_players_lost_games": 2,
        },
        "isko_list",
    )["total_performance_points"] == 300
    assert build_list_performance_summary_from_game_contributions(
        [
            {
                "player_role": "defender",
                "game_outcome": "declarer_loss",
                "settlement_score": -72,
            }
        ],
        "isko_list",
    )["total_performance_points"] == 40
    standings = build_list_standings_summary(
        {
            "players": [
                {"player_id": "player-a"},
                {"player_id": "player-b"},
                {"player_id": "player-c"},
            ],
            "games": [
                {
                    "game_id": "game-1",
                    "declarer_player_id": "player-a",
                    "game_outcome": "declarer_win",
                    "settlement_score": 72,
                }
            ],
        },
        "isko_list",
    )
    assert standings["game_count"] == 1
    assert standings["standings"][0]["player_id"] == "player-a"


def test_type_annotations_reference_frozen_contract_types() -> None:
    assert FixedThreePlayerHistoricalListPlayer.__dataclass_params__.frozen is True
    assert FixedThreePlayerListSeatAssignment.__dataclass_params__.frozen is True
    assert FixedThreePlayerListContribution.__dataclass_params__.frozen is True
