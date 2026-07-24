import json
from pathlib import Path
from typing import Any

from skat_ai.analysis_metadata import (
    AnalysisMetadata,
    build_analysis_metadata_from_input,
)
from skat_ai.declarer_concession import (
    DeclarerConcession,
)
from skat_ai.game_declaration import (
    GameDeclaration,
    build_game_declaration_from_input,
)
from skat_ai.game_shortening import (
    GameShortening,
)
from skat_ai.game_shortening import (
    get_game_shortening_from_input as build_game_shortening_from_input,
)
from skat_ai.game_state import GameState
from skat_ai.historical_game import HistoricalGameRecord, build_historical_game_record
from skat_ai.impossible_null_settlement import (
    ImpossibleNullSettlementSelection,
    build_impossible_null_settlement_selection_from_input,
)
from skat_ai.information_view import build_local_analysis_input
from skat_ai.input_validation import validate_position_input
from skat_ai.opponent_policy_preset import apply_opponent_policy_preset
from skat_ai.opponent_statistics import (
    OpponentStatisticsInput,
    build_opponent_statistics_input,
)
from skat_ai.side_ownership import normalize_declarer_player
from skat_ai.training_dataset import TrainingDatasetInput, build_training_dataset_input
from skat_ai.turn_phase import normalize_turn_phase_for_position


def load_json_object(file_path: str) -> dict[str, Any]:
    """Loads one JSON input file and requires an object at the root."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Input JSON root must be an object.")

    return data


def get_input_workflow(data: dict[str, Any]) -> str:
    """Returns the public workflow selected by one top-level input object."""
    if "opponent_statistics_input" in data:
        if set(data) != {"opponent_statistics_input"}:
            raise ValueError(
                "opponent_statistics_input cannot be combined with historical-game, "
                "training-dataset, position-analysis, list-performance, profile, policy, "
                "simulation, recommendation, or settlement fields."
            )
        return "opponent_statistics"

    if "training_dataset_input" in data:
        if set(data) != {"training_dataset_input"}:
            raise ValueError(
                "training_dataset_input cannot be combined with historical-game, "
                "position-analysis, list-performance, profile, policy, or settlement fields."
            )
        return "training_dataset"

    if "historical_game_input" in data:
        if set(data) != {"historical_game_input"}:
            raise ValueError(
                "historical_game_input cannot be combined with position-analysis, "
                "list-performance, profile, policy, or settlement fields."
            )
        return "historical_game"

    return "position_analysis"


def load_position_from_json(file_path: str) -> dict[str, Any]:
    """
    Loads and validates a position configuration from a JSON file.
    """
    data = load_json_object(file_path)

    validate_position_input(data)

    return data


def load_historical_game_from_json(file_path: str) -> HistoricalGameRecord:
    """Loads and validates a complete historical-game input file."""
    data = load_json_object(file_path)
    if get_input_workflow(data) != "historical_game":
        raise ValueError("Input file does not contain historical_game_input.")

    historical_data = data["historical_game_input"]
    if not isinstance(historical_data, dict):
        raise ValueError("historical_game_input must be an object.")
    return build_historical_game_record(historical_data)


def load_training_dataset_from_json(file_path: str) -> TrainingDatasetInput:
    """Loads and validates a versioned training-dataset input file."""
    data = load_json_object(file_path)
    if get_input_workflow(data) != "training_dataset":
        raise ValueError("Input file does not contain training_dataset_input.")
    training_data = data["training_dataset_input"]
    if not isinstance(training_data, dict):
        raise ValueError("training_dataset_input must be an object.")
    return build_training_dataset_input(training_data)


def load_opponent_statistics_from_json(file_path: str) -> OpponentStatisticsInput:
    """Loads and validates a versioned opponent-statistics input file."""
    data = load_json_object(file_path)
    if get_input_workflow(data) != "opponent_statistics":
        raise ValueError("Input file does not contain opponent_statistics_input.")
    statistics_data = data["opponent_statistics_input"]
    if not isinstance(statistics_data, dict):
        raise ValueError("opponent_statistics_input must be an object.")
    return build_opponent_statistics_input(statistics_data)


def build_game_state_from_input(data: dict[str, Any]) -> GameState:
    """
    Builds a GameState object from parsed input data.
    """
    turn_phase = normalize_turn_phase_for_position(
        trick_leader=data.get("trick_leader", "unknown"),
        next_player=data.get("next_player", "unknown"),
        current_trick=data["current_trick"],
        completed_tricks=data.get("completed_tricks", []),
    )

    return GameState(
        game_type=data["game_type"],
        player_role=data["player_role"],
        hand=data["hand"],
        current_trick=data["current_trick"],
        played_cards=data.get("played_cards", []),
        skat=data.get("skat", []),
        player_position=data.get("player_position", "unknown"),
        declarer_player=normalize_declarer_player(
            player_role=data["player_role"],
            declarer_player=data.get("declarer_player"),
        ),
        trick_leader=turn_phase.trick_leader,
        completed_tricks=data.get("completed_tricks", []),
        declarer_points=data.get("declarer_points", 0),
        defender_points=data.get("defender_points", 0),
        next_player=turn_phase.next_player,
    )


def build_local_game_state_from_input(data: dict[str, Any]) -> GameState:
    """Builds a GameState from the local-information view of input data."""
    return build_game_state_from_input(build_local_analysis_input(data))


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

def get_left_opponent_policy_settings_from_input(
    data: dict[str, Any],
) -> dict[str, str]:
    """
    Extracts normalized left-opponent policy settings from input data.

    Falls back to the normalized global opponent policy settings for backward
    compatibility.
    """
    global_settings = get_opponent_policy_settings_from_input(data)

    return {
        "opponent_lead_policy": data.get(
            "left_opponent_lead_policy",
            global_settings["opponent_lead_policy"],
        ),
        "opponent_response_policy": data.get(
            "left_opponent_response_policy",
            global_settings["opponent_response_policy"],
        ),
    }


def get_right_opponent_policy_settings_from_input(
    data: dict[str, Any],
) -> dict[str, str]:
    """
    Extracts normalized right-opponent policy settings from input data.

    Falls back to the normalized global opponent policy settings for backward
    compatibility.
    """
    global_settings = get_opponent_policy_settings_from_input(data)

    return {
        "opponent_lead_policy": data.get(
            "right_opponent_lead_policy",
            global_settings["opponent_lead_policy"],
        ),
        "opponent_response_policy": data.get(
            "right_opponent_response_policy",
            global_settings["opponent_response_policy"],
        ),
    }

def get_profile_preset_settings_from_input(
    data: dict[str, Any],
) -> dict[str, bool]:
    """
    Extracts profile-preset settings from input data.
    """
    return {
        "use_profile_presets": data.get("use_profile_presets", False),
    }

def get_game_declaration_from_input(
    data: dict[str, Any],
) -> GameDeclaration:
    """
    Extracts game declaration metadata from input data.
    """
    return build_game_declaration_from_input(data)


def get_declarer_concession_from_input(
    data: dict[str, Any],
) -> DeclarerConcession | None:
    """Extracts the optional structured declarer concession."""
    game_shortening = build_game_shortening_from_input(data)
    if isinstance(game_shortening, DeclarerConcession):
        return game_shortening
    return None


def get_game_shortening_from_input(
    data: dict[str, Any],
) -> GameShortening | None:
    """Extracts the optional supported structured game shortening."""
    return build_game_shortening_from_input(data)


def get_impossible_null_settlement_from_input(
    data: dict[str, Any],
) -> ImpossibleNullSettlementSelection | None:
    """Extracts the optional external impossible Null replacement selection."""
    return build_impossible_null_settlement_selection_from_input(data)

def get_performance_rating_system_from_input(
    data: dict[str, Any],
) -> str | None:
    """
    Extracts the optional performance rating system from input data.
    """
    return data.get("performance_rating_system")


def get_list_performance_input_from_input(
    data: dict[str, Any],
) -> dict[str, int] | None:
    """
    Extracts optional aggregated list/series performance totals from input data.
    """
    return data.get("list_performance_input")


def get_list_game_contributions_from_input(
    data: dict[str, Any],
) -> list[dict[str, Any]] | None:
    """
    Extracts optional normalized list/series game contributions from input data.
    """
    return data.get("list_game_contributions")


def get_list_analysis_results_from_input(
    data: dict[str, Any],
) -> list[dict[str, Any]] | None:
    """
    Extracts optional local analysis results for list/series performance input.
    """
    return data.get("list_analysis_results")


def get_list_standings_input_from_input(
    data: dict[str, Any],
) -> dict[str, Any] | None:
    """Extracts optional fixed three-player list standings input."""
    return data.get("list_standings_input")


def get_actual_card_played_from_input(data: dict[str, Any]) -> str | None:
    """Extracts the optional actual card played from parsed input data."""
    return data.get("actual_card_played")
