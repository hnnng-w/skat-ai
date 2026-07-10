import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from skat_ai.input_validation import validate_position_input
from skat_ai.opponent_policy import VALID_OPPONENT_CARD_POLICIES
from skat_ai.opponent_policy_preset import VALID_OPPONENT_POLICY_PRESETS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "input.schema.json"
POLICY_FIELDS = [
    "opponent_lead_policy",
    "opponent_response_policy",
    "left_opponent_lead_policy",
    "left_opponent_response_policy",
    "right_opponent_lead_policy",
    "right_opponent_response_policy",
]


def load_input_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


INPUT_VALIDATOR = Draft202012Validator(load_input_schema())


def build_valid_input() -> dict[str, object]:
    return {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "right",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["D7"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }


def assert_schema_valid(data: dict[str, object]) -> None:
    errors = sorted(
        INPUT_VALIDATOR.iter_errors(data),
        key=lambda validation_error: list(validation_error.absolute_path),
    )

    assert not errors, [
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def assert_schema_invalid(data: dict[str, object]) -> None:
    errors = list(INPUT_VALIDATOR.iter_errors(data))

    assert errors


def assert_schema_and_runtime_valid(data: dict[str, object]) -> None:
    assert_schema_valid(data)
    validate_position_input(copy.deepcopy(data))


def assert_schema_and_runtime_invalid(data: dict[str, object]) -> None:
    assert_schema_invalid(data)

    with pytest.raises(ValueError):
        validate_position_input(copy.deepcopy(data))


@pytest.mark.parametrize("field_name", ["left_hand_size", "right_hand_size"])
def test_schema_and_runtime_accept_zero_opponent_hand_size(field_name: str) -> None:
    data = build_valid_input()
    data[field_name] = 0

    assert_schema_and_runtime_valid(data)


def test_schema_and_runtime_accept_zero_for_both_opponent_hand_sizes() -> None:
    data = build_valid_input()
    data["left_hand_size"] = 0
    data["right_hand_size"] = 0

    assert_schema_and_runtime_valid(data)


@pytest.mark.parametrize("field_name", ["left_hand_size", "right_hand_size"])
def test_schema_and_runtime_reject_negative_opponent_hand_size(
    field_name: str,
) -> None:
    data = build_valid_input()
    data[field_name] = -1

    assert_schema_and_runtime_invalid(data)


@pytest.mark.parametrize("field_name", ["left_hand_size", "right_hand_size"])
@pytest.mark.parametrize("invalid_value", [True, False, 1.5, "0"])
def test_schema_and_runtime_reject_non_integer_opponent_hand_size(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_valid_input()
    data[field_name] = invalid_value

    assert_schema_and_runtime_invalid(data)


@pytest.mark.parametrize("field_name", ["left_hand_size", "right_hand_size"])
def test_schema_and_runtime_reject_opponent_hand_size_above_maximum(
    field_name: str,
) -> None:
    data = build_valid_input()
    data[field_name] = 11

    assert_schema_and_runtime_invalid(data)


@pytest.mark.parametrize(
    "field_name",
    [
        "left_hand_size",
        "right_hand_size",
        "sample_count",
        "random_seed",
        "declarer_points",
        "defender_points",
    ],
)
@pytest.mark.parametrize("invalid_value", [True, False])
def test_schema_rejects_boolean_integer_fields(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_valid_input()
    data[field_name] = invalid_value

    assert_schema_invalid(data)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("sample_count", 100_001),
        ("left_hand_size", 11),
        ("right_hand_size", 11),
    ],
)
def test_schema_rejects_upper_integer_bounds(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_valid_input()
    data[field_name] = invalid_value

    assert_schema_invalid(data)


def test_schema_rejects_hand_above_maximum() -> None:
    data = build_valid_input()
    data["hand"] = [
        "C7",
        "C8",
        "C9",
        "CJ",
        "CQ",
        "CK",
        "D7",
        "D8",
        "D9",
        "DJ",
        "DQ",
    ]

    assert_schema_invalid(data)


def test_schema_rejects_skat_above_maximum() -> None:
    data = build_valid_input()
    data["skat"] = ["C7", "D8", "H9"]

    assert_schema_invalid(data)


@pytest.mark.parametrize(
    "field_name",
    ["hand", "current_trick", "played_cards", "completed_tricks", "skat"],
)
def test_schema_rejects_null_card_arrays(field_name: str) -> None:
    data = build_valid_input()
    data[field_name] = None

    assert_schema_invalid(data)


@pytest.mark.parametrize("field_name", ["left_player_profile", "right_player_profile"])
def test_schema_rejects_null_player_profiles(field_name: str) -> None:
    data = build_valid_input()
    data[field_name] = None

    assert_schema_invalid(data)


def test_schema_rejects_null_known_player_profile_field() -> None:
    data = build_valid_input()
    data["left_player_profile"] = {
        "games_played": None,
    }

    assert_schema_invalid(data)


def test_schema_accepts_nested_game_declaration() -> None:
    data = build_valid_input()
    data["game_declaration"] = {
        "hand_game": True,
        "ouvert": False,
        "schneider_announced": True,
        "schwarz_announced": False,
        "matadors": 2,
        "bid_value": 48,
    }

    assert_schema_valid(data)


def test_schema_accepts_nested_numeric_nulls() -> None:
    data = build_valid_input()
    data["game_declaration"] = {
        "matadors": None,
        "bid_value": None,
    }

    assert_schema_valid(data)


def test_schema_accepts_unknown_nested_declaration_properties() -> None:
    data = build_valid_input()
    data["game_declaration"] = {
        "matadors": 2,
        "comment": "accepted metadata",
    }

    assert_schema_valid(data)


@pytest.mark.parametrize(
    "field_name",
    [
        "hand_game",
        "ouvert",
        "schneider_announced",
        "schwarz_announced",
    ],
)
@pytest.mark.parametrize("invalid_value", [None, "false", 0, 1])
def test_schema_rejects_invalid_nested_declaration_booleans(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_valid_input()
    data["game_declaration"] = {
        field_name: invalid_value,
    }

    assert_schema_invalid(data)


@pytest.mark.parametrize("invalid_value", [True, -1, 1.5, "1"])
def test_schema_rejects_invalid_nested_matadors(invalid_value: object) -> None:
    data = build_valid_input()
    data["game_declaration"] = {
        "matadors": invalid_value,
    }

    assert_schema_invalid(data)


@pytest.mark.parametrize("invalid_value", [True, 0, -1, 1.5, "18"])
def test_schema_rejects_invalid_nested_bid_value(invalid_value: object) -> None:
    data = build_valid_input()
    data["game_declaration"] = {
        "bid_value": invalid_value,
    }

    assert_schema_invalid(data)


@pytest.mark.parametrize("game_declaration", [True, 1, "declaration", []])
def test_schema_rejects_non_object_game_declaration(game_declaration: object) -> None:
    data = build_valid_input()
    data["game_declaration"] = game_declaration

    assert_schema_invalid(data)


def test_schema_accepts_null_game_declaration() -> None:
    data = build_valid_input()
    data["game_declaration"] = None

    assert_schema_valid(data)


def test_schema_accepts_declarer_player_enum_values_for_valid_roles() -> None:
    declarer_data = build_valid_input()
    declarer_data["declarer_player"] = "me"
    assert_schema_valid(declarer_data)

    left_defender_data = build_valid_input()
    left_defender_data["player_role"] = "defender"
    left_defender_data["declarer_player"] = "left"
    assert_schema_valid(left_defender_data)

    right_defender_data = build_valid_input()
    right_defender_data["player_role"] = "defender"
    right_defender_data["declarer_player"] = "right"
    assert_schema_valid(right_defender_data)

    unknown_data = build_valid_input()
    unknown_data["player_role"] = "unknown"
    unknown_data["declarer_player"] = "unknown"
    assert_schema_valid(unknown_data)


def test_schema_rejects_invalid_declarer_player_value() -> None:
    data = build_valid_input()
    data["declarer_player"] = "dealer"

    assert_schema_invalid(data)


def test_schema_accepts_local_declarer_missing_declarer_player() -> None:
    data = build_valid_input()

    assert_schema_valid(data)


@pytest.mark.parametrize("declarer_player", ["unknown", "left", "right"])
def test_schema_rejects_invalid_local_declarer_combinations(
    declarer_player: str,
) -> None:
    data = build_valid_input()
    data["declarer_player"] = declarer_player

    assert_schema_invalid(data)


@pytest.mark.parametrize("declarer_player", ["left", "right"])
def test_schema_accepts_valid_local_defender_combinations(
    declarer_player: str,
) -> None:
    data = build_valid_input()
    data["player_role"] = "defender"
    data["declarer_player"] = declarer_player

    assert_schema_valid(data)


@pytest.mark.parametrize("declarer_player", [None, "unknown", "me"])
def test_schema_rejects_invalid_local_defender_combinations(
    declarer_player: str | None,
) -> None:
    data = build_valid_input()
    data["player_role"] = "defender"
    if declarer_player is None:
        data.pop("declarer_player", None)
    else:
        data["declarer_player"] = declarer_player

    assert_schema_invalid(data)


def test_schema_accepts_unknown_role_missing_declarer_player() -> None:
    data = build_valid_input()
    data["player_role"] = "unknown"

    assert_schema_valid(data)


@pytest.mark.parametrize("declarer_player", ["me", "left", "right"])
def test_schema_rejects_unknown_role_concrete_declarer(
    declarer_player: str,
) -> None:
    data = build_valid_input()
    data["player_role"] = "unknown"
    data["declarer_player"] = declarer_player

    assert_schema_invalid(data)


def build_list_game_contribution_input(
    entries: list[dict[str, object]],
) -> dict[str, object]:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_game_contributions"] = entries

    return data


def build_list_analysis_result_input(
    entries: list[dict[str, object]],
) -> dict[str, object]:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = entries

    return data


def build_schema_game_contribution() -> dict[str, object]:
    return {
        "player_role": "declarer",
        "game_outcome": "declarer_win",
        "settlement_score": 96,
    }


def build_schema_analysis_result() -> dict[str, object]:
    return {
        "position": {
            "player_role": "declarer",
        },
        "final_settlement_summary": {
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 96,
        },
    }


@pytest.mark.parametrize("field_name", POLICY_FIELDS)
@pytest.mark.parametrize("policy", VALID_OPPONENT_CARD_POLICIES)
def test_policy_fields_accept_canonical_values(
    field_name: str,
    policy: str,
) -> None:
    data = build_valid_input()
    data[field_name] = policy

    assert_schema_valid(data)


@pytest.mark.parametrize("field_name", POLICY_FIELDS)
@pytest.mark.parametrize("value", ["unsupported_policy", "", True, 1])
def test_policy_fields_reject_invalid_values(
    field_name: str,
    value: object,
) -> None:
    data = build_valid_input()
    data[field_name] = value

    assert_schema_invalid(data)


@pytest.mark.parametrize("field_name", POLICY_FIELDS)
def test_policy_fields_may_be_omitted(field_name: str) -> None:
    data = build_valid_input()
    data.pop(field_name, None)

    assert_schema_valid(data)


@pytest.mark.parametrize("field_name", POLICY_FIELDS)
def test_policy_fields_accept_explicit_lowest_point_default(field_name: str) -> None:
    data = build_valid_input()
    data[field_name] = "lowest_point"

    assert_schema_valid(data)


@pytest.mark.parametrize("preset", VALID_OPPONENT_POLICY_PRESETS)
def test_opponent_policy_preset_accepts_canonical_values(preset: str) -> None:
    data = build_valid_input()
    data["opponent_policy_preset"] = preset

    assert_schema_valid(data)


@pytest.mark.parametrize("value", ["unsupported_preset", "", False, 1])
def test_opponent_policy_preset_rejects_invalid_values(value: object) -> None:
    data = build_valid_input()
    data["opponent_policy_preset"] = value

    assert_schema_invalid(data)


def test_opponent_policy_preset_may_be_omitted() -> None:
    data = build_valid_input()

    assert_schema_valid(data)


def build_input_with_completed_trick(
    completed_trick: dict[str, object],
) -> dict[str, object]:
    data = build_valid_input()
    data["completed_tricks"] = [completed_trick]

    return data


def test_completed_trick_accepts_minimal_documented_entry() -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
        }
    )

    assert_schema_valid(data)


def test_completed_trick_rejects_additional_properties() -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
            "table_size": 3,
        }
    )

    assert_schema_invalid(data)


def test_completed_trick_rejects_missing_winner_role() -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
        }
    )

    assert_schema_invalid(data)


@pytest.mark.parametrize("winner_role", ["unknown", "soloist", True])
def test_completed_trick_rejects_invalid_winner_role(
    winner_role: object,
) -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": winner_role,
        }
    )

    assert_schema_invalid(data)


def test_completed_trick_accepts_full_entry() -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "players": ["me", "left", "right"],
            "winner_role": "declarer",
            "winner_player": "me",
        }
    )

    assert_schema_valid(data)


@pytest.mark.parametrize(
    "players",
    [
        ["me", "left", "unknown"],
        ["me", "left", "left"],
        ["me", "left", 1],
    ],
)
def test_completed_trick_rejects_invalid_players(players: object) -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "players": players,
            "winner_role": "declarer",
            "winner_player": "me",
        }
    )

    assert_schema_invalid(data)


@pytest.mark.parametrize("winner_player", ["unknown", "dealer", 1])
def test_completed_trick_rejects_invalid_winner_player(
    winner_player: object,
) -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "players": ["me", "left", "right"],
            "winner_role": "declarer",
            "winner_player": winner_player,
        }
    )

    assert_schema_invalid(data)


def test_completed_trick_players_may_be_omitted() -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
            "winner_player": "me",
        }
    )

    assert_schema_valid(data)


def test_completed_trick_winner_player_may_be_omitted() -> None:
    data = build_input_with_completed_trick(
        {
            "cards": ["CA", "C10", "CK"],
            "players": ["me", "left", "right"],
            "winner_role": "declarer",
        }
    )

    assert_schema_valid(data)


def test_completed_trick_rule_winner_consistency_remains_python_only() -> None:
    data = build_valid_input()
    data.update(
        {
            "player_role": "unknown",
            "trick_leader": "unknown",
            "hand": ["S10", "S9", "D7"],
            "current_trick": [],
            "next_player": "unknown",
            "completed_tricks": [
                {
                    "cards": ["S7", "S8", "SA"],
                    "players": ["left", "right", "me"],
                    "winner_role": "declarer",
                    "winner_player": "left",
                }
            ],
        }
    )

    schema_data = copy.deepcopy(data)
    assert_schema_valid(schema_data)

    with pytest.raises(
        ValueError,
        match="winner_player is inconsistent with trick rules",
    ):
        validate_position_input(data)


@pytest.mark.parametrize(
    "mode_builder,entry_builder",
    [
        (build_list_game_contribution_input, build_schema_game_contribution),
        (build_list_analysis_result_input, build_schema_analysis_result),
    ],
)
def test_list_entry_schema_accepts_optional_stable_identifiers(
    mode_builder,
    entry_builder,
) -> None:
    entry = entry_builder()
    entry["rated_player_id"] = "player-1"
    entry["game_id"] = "game-1"

    assert_schema_valid(mode_builder([entry]))


@pytest.mark.parametrize(
    "mode_builder,entry_builder",
    [
        (build_list_game_contribution_input, build_schema_game_contribution),
        (build_list_analysis_result_input, build_schema_analysis_result),
    ],
)
def test_list_entry_schema_accepts_missing_stable_identifiers(
    mode_builder,
    entry_builder,
) -> None:
    assert_schema_valid(mode_builder([entry_builder()]))


@pytest.mark.parametrize("field_name", ["rated_player_id", "game_id"])
@pytest.mark.parametrize(
    "mode_builder,entry_builder",
    [
        (build_list_game_contribution_input, build_schema_game_contribution),
        (build_list_analysis_result_input, build_schema_analysis_result),
    ],
)
def test_list_entry_schema_rejects_empty_stable_identifier(
    mode_builder,
    entry_builder,
    field_name: str,
) -> None:
    entry = entry_builder()
    entry[field_name] = ""

    assert_schema_invalid(mode_builder([entry]))


@pytest.mark.parametrize("field_name", ["rated_player_id", "game_id"])
@pytest.mark.parametrize("invalid_value", [True, 123, 1.5, [], {}, None])
@pytest.mark.parametrize(
    "mode_builder,entry_builder",
    [
        (build_list_game_contribution_input, build_schema_game_contribution),
        (build_list_analysis_result_input, build_schema_analysis_result),
    ],
)
def test_list_entry_schema_rejects_non_string_stable_identifier(
    mode_builder,
    entry_builder,
    invalid_value: object,
    field_name: str,
) -> None:
    entry = entry_builder()
    entry[field_name] = invalid_value

    assert_schema_invalid(mode_builder([entry]))


def test_list_entry_schema_allows_cross_entry_conflicts_for_python_validation() -> None:
    first_entry = build_schema_game_contribution()
    second_entry = build_schema_game_contribution()
    first_entry["rated_player_id"] = "player-1"
    second_entry["rated_player_id"] = "player-2"
    first_entry["game_id"] = "game-1"
    second_entry["game_id"] = "game-1"
    data = build_list_game_contribution_input([first_entry, second_entry])

    assert_schema_valid(data)

    with pytest.raises(ValueError, match="rated_player_id values conflict"):
        validate_position_input(data)
