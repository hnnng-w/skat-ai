from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

import skat_ai.api.v1.session as session_api
from skat_ai.errors import SkatAIError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "input.schema.json"
SESSION_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "session.schema.json"
FIELD_PROVENANCE_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "field_provenance.schema.json"
HISTORICAL_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game.schema.json"
HISTORICAL_GAME_END_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game_end.schema.json"
HISTORICAL_GAME_EVENT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game_event.schema.json"
HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_EVENT_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "historical_defender_open_play_continuation_event.schema.json"
)
HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_EVENT_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "historical_declarer_card_exposure_continuation_event.schema.json"
)
HISTORICAL_DECLARER_CONCESSION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_declarer_concession.schema.json"
)
HISTORICAL_DEFENDER_CONCESSION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_defender_concession.schema.json"
)
HISTORICAL_DECLARER_CARD_EXPOSURE_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_declarer_card_exposure.schema.json"
)
HISTORICAL_DEFENDER_OPEN_PLAY_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_defender_open_play.schema.json"
)
HISTORICAL_OPEN_CARD_THROW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_open_card_throw.schema.json"
)
HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_party_wide_claim.schema.json"
)
TRAINING_DATASET_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "training_dataset.schema.json"
TRAINING_DATASET_PREPARATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "training_dataset_preparation.schema.json"
)
OPPONENT_STATISTICS_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "opponent_statistics.schema.json"
FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "fixed_three_player_historical_list.schema.json"
)
FIXED_THREE_PLAYER_HISTORICAL_LIST_INPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "fixed_three_player_historical_list_input.schema.json"
)
FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_INPUT_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "fixed_three_player_historical_list_comparison_input.schema.json"
)
DATASET_PARTITION_POLICY_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "dataset_partition_policy.schema.json"
)
GAME_SHORTENING_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "game_shortening.schema.json"
DEFENDER_OPEN_PLAY_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "defender_open_play.schema.json"
OPEN_CARD_THROW_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "open_card_throw.schema.json"
GAME_CONTINUATION_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "game_continuation.schema.json"
DEFENDER_OPEN_PLAY_CONTINUATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "defender_open_play_continuation.schema.json"
)
ROOT_INPUT_PATH = PROJECT_ROOT / "input_position.json"
EXAMPLES_DIR = PROJECT_ROOT / "examples"

SESSION_EXAMPLE_DEFINITIONS = {
    "session_create_live.json": "session_create_input",
    "session_create_retrospective.json": "session_create_input",
    "session_command_record_play.json": "session_command",
    "session_correction_record_play.json": "command_correction",
    "session_live_persistence.json": "session_persistence_document",
    "session_retrospective_persistence.json": "session_persistence_document",
}


def load_json_file(file_path: Path) -> dict:
    """
    Loads a JSON file.
    """
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_example_files() -> list[Path]:
    """
    Returns all example JSON files.
    """
    return sorted(EXAMPLES_DIR.glob("*.json"))


def get_schema_input_files() -> list[Path]:
    """
    Returns all input files covered by input schema validation.
    """
    return [
        ROOT_INPUT_PATH,
        *(
            path
            for path in get_example_files()
            if path.name not in SESSION_EXAMPLE_DEFINITIONS
        ),
    ]


def get_session_example_files() -> list[Path]:
    """Returns the exact Session example set in deterministic order."""
    return [EXAMPLES_DIR / name for name in sorted(SESSION_EXAMPLE_DEFINITIONS)]


def format_validation_error(file_path: Path, error) -> str:
    """
    Formats a JSON schema validation error.
    """
    location = ".".join(str(part) for part in error.absolute_path)

    if not location:
        location = "<root>"

    return f"{file_path}: {location}: {error.message}"


def validate_example_files() -> list[str]:
    """
    Validates all example JSON files against the input JSON schema.
    """
    schema = load_json_file(SCHEMA_PATH)
    session_schema = load_json_file(SESSION_SCHEMA_PATH)
    field_provenance_schema = load_json_file(FIELD_PROVENANCE_SCHEMA_PATH)
    historical_schema = load_json_file(HISTORICAL_SCHEMA_PATH)
    historical_game_end_schema = load_json_file(HISTORICAL_GAME_END_SCHEMA_PATH)
    historical_game_event_schema = load_json_file(HISTORICAL_GAME_EVENT_SCHEMA_PATH)
    historical_continuation_event_schema = load_json_file(
        HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_EVENT_SCHEMA_PATH
    )
    historical_declarer_continuation_event_schema = load_json_file(
        HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_EVENT_SCHEMA_PATH
    )
    historical_declarer_concession_schema = load_json_file(
        HISTORICAL_DECLARER_CONCESSION_SCHEMA_PATH
    )
    historical_defender_concession_schema = load_json_file(
        HISTORICAL_DEFENDER_CONCESSION_SCHEMA_PATH
    )
    historical_declarer_card_exposure_schema = load_json_file(
        HISTORICAL_DECLARER_CARD_EXPOSURE_SCHEMA_PATH
    )
    historical_defender_open_play_schema = load_json_file(
        HISTORICAL_DEFENDER_OPEN_PLAY_SCHEMA_PATH
    )
    historical_open_card_throw_schema = load_json_file(
        HISTORICAL_OPEN_CARD_THROW_SCHEMA_PATH
    )
    historical_party_wide_claim_schema = load_json_file(
        HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_PATH
    )
    training_dataset_schema = load_json_file(TRAINING_DATASET_SCHEMA_PATH)
    training_dataset_preparation_schema = load_json_file(
        TRAINING_DATASET_PREPARATION_SCHEMA_PATH
    )
    opponent_statistics_schema = load_json_file(OPPONENT_STATISTICS_SCHEMA_PATH)
    historical_list_schema = load_json_file(FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_PATH)
    historical_list_input_schema = load_json_file(
        FIXED_THREE_PLAYER_HISTORICAL_LIST_INPUT_SCHEMA_PATH
    )
    historical_list_comparison_input_schema = load_json_file(
        FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_INPUT_SCHEMA_PATH
    )
    dataset_partition_policy_schema = load_json_file(DATASET_PARTITION_POLICY_SCHEMA_PATH)
    game_shortening_schema = load_json_file(GAME_SHORTENING_SCHEMA_PATH)
    defender_open_play_schema = load_json_file(DEFENDER_OPEN_PLAY_SCHEMA_PATH)
    open_card_throw_schema = load_json_file(OPEN_CARD_THROW_SCHEMA_PATH)
    game_continuation_schema = load_json_file(GAME_CONTINUATION_SCHEMA_PATH)
    defender_open_play_continuation_schema = load_json_file(
        DEFENDER_OPEN_PLAY_CONTINUATION_SCHEMA_PATH
    )
    registry = Registry().with_resources(
        [
            (historical_schema["$id"], Resource.from_contents(historical_schema)),
            (
                historical_game_end_schema["$id"],
                Resource.from_contents(historical_game_end_schema),
            ),
            (
                historical_game_event_schema["$id"],
                Resource.from_contents(historical_game_event_schema),
            ),
            (
                historical_continuation_event_schema["$id"],
                Resource.from_contents(historical_continuation_event_schema),
            ),
            (
                historical_declarer_continuation_event_schema["$id"],
                Resource.from_contents(historical_declarer_continuation_event_schema),
            ),
            (
                historical_declarer_concession_schema["$id"],
                Resource.from_contents(historical_declarer_concession_schema),
            ),
            (
                historical_defender_concession_schema["$id"],
                Resource.from_contents(historical_defender_concession_schema),
            ),
            (
                historical_declarer_card_exposure_schema["$id"],
                Resource.from_contents(historical_declarer_card_exposure_schema),
            ),
            (
                historical_defender_open_play_schema["$id"],
                Resource.from_contents(historical_defender_open_play_schema),
            ),
            (
                historical_open_card_throw_schema["$id"],
                Resource.from_contents(historical_open_card_throw_schema),
            ),
            (
                historical_party_wide_claim_schema["$id"],
                Resource.from_contents(historical_party_wide_claim_schema),
            ),
            (
                training_dataset_schema["$id"],
                Resource.from_contents(training_dataset_schema),
            ),
            (
                training_dataset_preparation_schema["$id"],
                Resource.from_contents(training_dataset_preparation_schema),
            ),
            (
                opponent_statistics_schema["$id"],
                Resource.from_contents(opponent_statistics_schema),
            ),
            (
                historical_list_schema["$id"],
                Resource.from_contents(historical_list_schema),
            ),
            (
                historical_list_input_schema["$id"],
                Resource.from_contents(historical_list_input_schema),
            ),
            (
                historical_list_comparison_input_schema["$id"],
                Resource.from_contents(historical_list_comparison_input_schema),
            ),
            (
                dataset_partition_policy_schema["$id"],
                Resource.from_contents(dataset_partition_policy_schema),
            ),
            (
                game_shortening_schema["$id"],
                Resource.from_contents(game_shortening_schema),
            ),
            (
                defender_open_play_schema["$id"],
                Resource.from_contents(defender_open_play_schema),
            ),
            (
                open_card_throw_schema["$id"],
                Resource.from_contents(open_card_throw_schema),
            ),
            (
                game_continuation_schema["$id"],
                Resource.from_contents(game_continuation_schema),
            ),
            (
                defender_open_play_continuation_schema["$id"],
                Resource.from_contents(defender_open_play_continuation_schema),
            ),
            (schema["$id"], Resource.from_contents(schema)),
            (session_schema["$id"], Resource.from_contents(session_schema)),
            (
                field_provenance_schema["$id"],
                Resource.from_contents(field_provenance_schema),
            ),
        ]
    )
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )

    errors = []

    actual_session_names = {
        path.name for path in EXAMPLES_DIR.glob("session_*.json")
    }
    expected_session_names = set(SESSION_EXAMPLE_DEFINITIONS)
    if actual_session_names != expected_session_names:
        errors.append(
            "Session examples must be exactly "
            f"{sorted(expected_session_names)}; found {sorted(actual_session_names)}."
        )

    for example_file in get_schema_input_files():
        data = load_json_file(example_file)

        for error in sorted(
            validator.iter_errors(data),
            key=lambda validation_error: list(validation_error.absolute_path),
        ):
            errors.append(format_validation_error(example_file, error))

    session_schema_id = session_schema["$id"]
    for example_file in get_session_example_files():
        if not example_file.is_file():
            errors.append(f"Missing Session example: {example_file}")
            continue
        data = load_json_file(example_file)
        definition = SESSION_EXAMPLE_DEFINITIONS[example_file.name]
        session_validator = Draft202012Validator(
            {"$ref": f"{session_schema_id}#/$defs/{definition}"},
            registry=registry,
            format_checker=FormatChecker(),
        )
        validation_errors = sorted(
            session_validator.iter_errors(data),
            key=lambda validation_error: list(validation_error.absolute_path),
        )
        errors.extend(
            format_validation_error(example_file, error)
            for error in validation_errors
        )
        if definition != "session_persistence_document" or validation_errors:
            continue
        try:
            resumed = session_api.resume_session_document(data).value
        except (SkatAIError, TypeError, ValueError) as error:
            errors.append(
                f"{example_file}: semantic Session resume failed: {error}"
            )
            continue
        if resumed.document.to_dict() != data:
            errors.append(
                f"{example_file}: semantic Session resume changed the persistence document."
            )
        if len(resumed.checkpoint_lineage) != len(data["decision_checkpoints"]):
            errors.append(
                f"{example_file}: resumed Checkpoint lineage does not match the document."
            )

    return errors


def main() -> int:
    """
    Runs example schema validation.
    """
    errors = validate_example_files()

    if errors:
        print("JSON schema validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("All root and Session example JSON files match their declared schemas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
