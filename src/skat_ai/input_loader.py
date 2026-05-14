import json
from pathlib import Path
from typing import Any

from skat_ai.analysis_metadata import (
    AnalysisMetadata,
    build_analysis_metadata_from_input,
)
from skat_ai.game_state import GameState
from skat_ai.input_validation import validate_position_input
from skat_ai.opponent_policy_preset import apply_opponent_policy_preset


def load_position_from_json(file_path: str) -> dict[str, Any]:
    """
    Loads and validates a position configuration from a JSON file.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    validate_position_input(data)

    return data


def build_game_state_from_input(data: dict[str, Any]) -> GameState:
    """
    Builds a GameState object from parsed input data.
    """
    return GameState(
        game_type=data["game_type"],
        player_role=data["player_role"],
        hand=data["hand"],
        current_trick=data["current_trick"],
        played_cards=data.get("played_cards", []),
        skat=data.get("skat", []),
        player_position=data.get("player_position", "unknown"),
        trick_leader=data.get("trick_leader", "unknown"),
        completed_tricks=data.get("completed_tricks", []),
        declarer_points=data.get("declarer_points", 0),
        defender_points=data.get("defender_points", 0),
        next_player=data.get("next_player", "unknown"),
    )


def get_simulation_settings_from_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extracts simulation settings from parsed input data.
    """
    return {
        "left_hand_size": data["left_hand_size"],
        "right_hand_size": data["right_hand_size"],
        "sample_count": data["sample_count"],
        "random_seed": data.get("random_seed"),
        "use_basic_opponent_strategy": data.get("use_basic_opponent_strategy", True),
    }

def get_analysis_metadata_from_input(
    data: dict[str, Any],
) -> AnalysisMetadata:
    """
    Extracts analysis metadata from input data.
    """
    return build_analysis_metadata_from_input(data)

def get_opponent_policy_settings_from_input(
    data: dict[str, Any],
) -> dict[str, str]:
    """
    Extracts opponent policy settings from input data.

    A preset is applied first. Explicit lead/response policy fields then
    override the preset.
    """
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    settings = apply_opponent_policy_preset(
        opponent_policy_settings=settings,
        preset=data.get("opponent_policy_preset"),
    )

    if "opponent_lead_policy" in data:
        settings["opponent_lead_policy"] = data["opponent_lead_policy"]

    if "opponent_response_policy" in data:
        settings["opponent_response_policy"] = data["opponent_response_policy"]

    return settings