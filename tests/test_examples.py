from pathlib import Path

from skat_ai.analysis_report import build_card_analysis_report
from skat_ai.input_loader import (
    build_game_state_from_input,
    get_simulation_settings_from_input,
    load_position_from_json,
)
from skat_ai.rules import get_legal_cards


def get_example_json_files() -> list[Path]:
    examples_dir = Path("examples")

    return sorted(examples_dir.glob("*.json"))


def test_examples_folder_contains_json_files() -> None:
    example_files = get_example_json_files()

    assert len(example_files) > 0


def test_all_example_json_files_can_be_loaded_and_validated() -> None:
    example_files = get_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))

        assert isinstance(data, dict)


def test_all_example_json_files_can_build_game_state_and_settings() -> None:
    example_files = get_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))
        state = build_game_state_from_input(data)
        settings = get_simulation_settings_from_input(data)

        assert state.game_type in [
            "clubs",
            "spades",
            "hearts",
            "diamonds",
            "grand",
            "null",
        ]
        assert isinstance(state.hand, list)
        assert isinstance(state.current_trick, list)
        assert settings["sample_count"] > 0


def test_all_example_json_files_have_legal_cards() -> None:
    example_files = get_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))
        state = build_game_state_from_input(data)

        legal_cards = get_legal_cards(
            hand=state.hand,
            current_trick=state.current_trick,
            game_type=state.game_type,
        )

        assert len(legal_cards) > 0


def test_all_example_json_files_can_build_analysis_report() -> None:
    example_files = get_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))
        state = build_game_state_from_input(data)
        settings = get_simulation_settings_from_input(data)

        report = build_card_analysis_report(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            sample_count=20,
            random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
        )

        assert len(report) > 0
        assert report[0]["is_recommended"] is True
