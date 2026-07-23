import copy
import math

import pytest

from skat_ai.opponent_statistics import (
    PERCENTAGE_SUM_TOLERANCE_POINTS,
    build_opponent_statistics_input,
    build_opponent_statistics_summary,
    build_player_profile_from_opponent_statistics,
)


def build_valid_record() -> dict[str, object]:
    return {
        "player_id": "opponent-123",
        "player_label": "Example Player",
        "source": {
            "source_type": "online_platform",
            "source_name": "Example platform",
            "source_player_id": "platform-user-456",
            "captured_at": "2026-07-23T12:00:00+02:00",
            "notes": "Public profile capture",
        },
        "games_played": 127,
        "statistics": {
            "solo_games_played_percent": 31,
            "solo_games_won_percent": 58,
            "solo_hand_percent": 12,
            "suit_games_percent": 61,
            "grand_games_percent": 29,
            "null_games_percent": 10,
            "defender_games_played_percent": 69,
            "defender_games_won_percent": 64,
        },
    }


def build_valid_input(*records: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "records": list(records or (build_valid_record(),)),
    }


def build_summary(data: dict[str, object]) -> dict[str, object]:
    return build_opponent_statistics_summary(build_opponent_statistics_input(data))


def test_builds_online_and_manual_records_with_integer_and_decimal_percentages() -> None:
    online_record = build_valid_record()
    manual_record = copy.deepcopy(online_record)
    manual_record["player_id"] = "Manual-Player"
    manual_record.pop("player_label")
    manual_record["source"] = {
        "source_type": "manual_entry",
        "source_name": "Local notes",
        "captured_at": "2026-07-23T10:00:00Z",
    }
    manual_record["statistics"]["solo_games_played_percent"] = 31.5
    manual_record["statistics"]["defender_games_played_percent"] = 68.5

    typed_input = build_opponent_statistics_input(build_valid_input(online_record, manual_record))

    assert [record.player_id for record in typed_input.records] == [
        "opponent-123",
        "Manual-Player",
    ]
    assert typed_input.records[1].source.source_type == "manual_entry"
    assert typed_input.records[1].statistics.solo_games_played_percent == 31.5


@pytest.mark.parametrize(
    ("solo_percent", "defender_percent", "suit_percent", "grand_percent", "null_percent"),
    [
        (31, 69, 61, 29, 10),
        (30, 68, 60, 30, 8),
        (32, 70, 62, 30, 10),
        (31.5, 68.5, 60.5, 29.5, 10),
    ],
)
def test_accepts_exact_and_inclusive_rounded_percentage_totals(
    solo_percent: float,
    defender_percent: float,
    suit_percent: float,
    grand_percent: float,
    null_percent: float,
) -> None:
    record = build_valid_record()
    statistics = record["statistics"]
    statistics.update(
        solo_games_played_percent=solo_percent,
        defender_games_played_percent=defender_percent,
        suit_games_percent=suit_percent,
        grand_games_percent=grand_percent,
        null_games_percent=null_percent,
    )

    build_opponent_statistics_input(build_valid_input(record))


def test_accepts_zero_individual_contract_type_and_zero_role_combinations() -> None:
    contract_record = build_valid_record()
    contract_record["statistics"].update(
        suit_games_percent=70,
        grand_games_percent=30,
        null_games_percent=0,
    )
    declarer_only_record = build_valid_record()
    declarer_only_record["player_id"] = "declarer-only"
    declarer_only_record["statistics"].update(
        solo_games_played_percent=100,
        defender_games_played_percent=0,
        defender_games_won_percent=0,
    )
    defender_only_record = build_valid_record()
    defender_only_record["player_id"] = "defender-only"
    defender_only_record["statistics"].update(
        solo_games_played_percent=0,
        solo_games_won_percent=0,
        solo_hand_percent=0,
        suit_games_percent=0,
        grand_games_percent=0,
        null_games_percent=0,
        defender_games_played_percent=100,
    )

    typed_input = build_opponent_statistics_input(
        build_valid_input(contract_record, declarer_only_record, defender_only_record)
    )

    assert len(typed_input.records) == 3


def test_normalizes_to_player_profile_semantics_without_inventing_counts() -> None:
    record = build_opponent_statistics_input(build_valid_input()).records[0]

    profile = build_player_profile_from_opponent_statistics(record)

    assert profile.games_played == 127
    assert profile.solo_games_played is None
    assert profile.defender_games_played is None
    assert profile.solo_rate == 0.31
    assert profile.defender_rate == 0.69
    assert profile.solo_win_rate == 0.58
    assert profile.hand_game_rate == 0.12
    assert profile.suit_game_rate == 0.61
    assert profile.grand_rate == 0.29
    assert profile.null_game_rate == 0.1
    assert profile.defender_win_rate == 0.64


def test_summary_is_deterministic_preserves_order_values_identity_and_provenance() -> None:
    first = build_valid_record()
    second = copy.deepcopy(first)
    second["player_id"] = "Opponent-ABC"
    second["source"]["source_player_id"] = "Case-Sensitive-ID"
    data = build_valid_input(first, second)

    first_summary = build_summary(data)
    second_summary = build_summary(copy.deepcopy(data))

    assert first_summary == second_summary
    assert [record["player_id"] for record in first_summary["records"]] == [
        "opponent-123",
        "Opponent-ABC",
    ]
    output_record = first_summary["records"][1]
    assert output_record["source"] == second["source"]
    assert output_record["statistics"] == second["statistics"]
    assert output_record["normalized_profile_statistics"]["solo_games_played"] is None
    assert output_record["normalized_profile_statistics"]["defender_games_played"] is None
    assert output_record["normalized_profile_statistics"]["defender_rate"] == 0.69
    assert output_record["validation_metadata"] == {
        "percentage_sum_tolerance_points": PERCENTAGE_SUM_TOLERANCE_POINTS,
    }
    derivation = output_record["profile_derivation"]
    assert derivation["profile_derivation_version"] == 1
    assert derivation["confidence"]["declarer"] == {
        "level": "low",
        "evidence_count": pytest.approx(39.37),
        "evidence_kind": "estimated_from_rate",
    }
    assert derivation["confidence"]["defender"] == {
        "level": "low",
        "evidence_count": pytest.approx(87.63),
        "evidence_kind": "estimated_from_rate",
    }
    assert derivation["classification"] == "aggressive"
    assert derivation["recommended_policy_preset"] == "aggressive_points"
    assert derivation["actionable_policy_preset"] is None
    assert derivation["derivation_status"] == "insufficient_confidence"
    assert len(derivation["signals"]) == 4
    assert derivation["explanations"]


@pytest.mark.parametrize(
    ("path", "value", "error_match"),
    [
        (("player_id",), "", "non-empty, non-padded"),
        (("player_id",), " padded", "non-empty, non-padded"),
        (("player_label",), "Label ", "non-empty, non-padded"),
        (("player_label",), None, "non-empty, non-padded"),
        (("source", "source_type"), "website", "source_type"),
        (("source", "source_name"), "", "non-empty, non-padded"),
        (("source", "source_player_id"), " padded", "non-empty, non-padded"),
        (("source", "source_player_id"), None, "non-empty, non-padded"),
        (("source", "notes"), " ", "non-empty, non-padded"),
        (("source", "notes"), None, "non-empty, non-padded"),
        (("source", "captured_at"), "2026-07-23T12:00:00", "time-zone offset"),
        (("source", "captured_at"), "2026-02-30T12:00:00+02:00", "time-zone offset"),
    ],
)
def test_rejects_invalid_identity_and_provenance(
    path: tuple[str, ...],
    value: object,
    error_match: str,
) -> None:
    record = build_valid_record()
    target = record
    for path_part in path[:-1]:
        target = target[path_part]
    target[path[-1]] = value

    with pytest.raises(ValueError, match=error_match):
        build_opponent_statistics_input(build_valid_input(record))


def test_rejects_missing_provenance_duplicate_ids_and_unknown_properties() -> None:
    missing_source = build_valid_record()
    missing_source.pop("source")
    with pytest.raises(ValueError, match="missing required fields"):
        build_opponent_statistics_input(build_valid_input(missing_source))

    duplicate = copy.deepcopy(build_valid_record())
    with pytest.raises(ValueError, match="Duplicate.*player_id"):
        build_opponent_statistics_input(build_valid_input(build_valid_record(), duplicate))

    unknown_source = build_valid_record()
    unknown_source["source"]["url"] = "https://example.test"
    with pytest.raises(ValueError, match="unsupported fields"):
        build_opponent_statistics_input(build_valid_input(unknown_source))

    unknown_record = build_valid_record()
    unknown_record["policy"] = "random"
    with pytest.raises(ValueError, match="unsupported fields"):
        build_opponent_statistics_input(build_valid_input(unknown_record))


@pytest.mark.parametrize("games_played", [0, -1, True, 1.5, "127"])
def test_rejects_invalid_games_played(games_played: object) -> None:
    record = build_valid_record()
    record["games_played"] = games_played

    with pytest.raises(ValueError, match="integer of at least 1"):
        build_opponent_statistics_input(build_valid_input(record))


@pytest.mark.parametrize("value", [True, False, -0.1, 100.1, math.nan, math.inf, "31"])
def test_rejects_invalid_percentage_values(value: object) -> None:
    record = build_valid_record()
    record["statistics"]["solo_games_won_percent"] = value

    with pytest.raises(ValueError, match="number from 0 through 100"):
        build_opponent_statistics_input(build_valid_input(record))


def test_rejects_missing_and_unknown_statistics_fields() -> None:
    missing = build_valid_record()
    missing["statistics"].pop("solo_hand_percent")
    with pytest.raises(ValueError, match="missing required fields"):
        build_opponent_statistics_input(build_valid_input(missing))

    unknown = build_valid_record()
    unknown["statistics"]["confidence"] = 90
    with pytest.raises(ValueError, match="unsupported fields"):
        build_opponent_statistics_input(build_valid_input(unknown))


@pytest.mark.parametrize(
    "updates",
    [
        {"solo_games_played_percent": 30, "defender_games_played_percent": 67.9},
        {"solo_games_played_percent": 31, "defender_games_played_percent": 71.1},
        {"suit_games_percent": 60, "grand_games_percent": 28, "null_games_percent": 9.9},
        {"suit_games_percent": 62, "grand_games_percent": 30, "null_games_percent": 10.1},
    ],
)
def test_rejects_percentage_totals_outside_tolerance(updates: dict[str, float]) -> None:
    record = build_valid_record()
    record["statistics"].update(updates)

    with pytest.raises(ValueError, match="must total from 98 through 102"):
        build_opponent_statistics_input(build_valid_input(record))


@pytest.mark.parametrize(
    "updates",
    [
        {"solo_games_played_percent": 0, "defender_games_played_percent": 100},
        {"defender_games_played_percent": 0, "solo_games_played_percent": 100},
    ],
)
def test_rejects_nonzero_dependent_percentages_for_zero_role(
    updates: dict[str, float],
) -> None:
    record = build_valid_record()
    record["statistics"].update(updates)

    with pytest.raises(ValueError, match="must be 0 when"):
        build_opponent_statistics_input(build_valid_input(record))


def test_accepts_empty_versioned_collection() -> None:
    summary = build_summary({"schema_version": 1, "records": []})

    assert summary == {"schema_version": 1, "record_count": 0, "records": []}
