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
        "trick_leader": "left",
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
