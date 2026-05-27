from dataclasses import dataclass

VALID_ANALYSIS_MODES = [
    "live_decision",
    "post_game_review",
]

VALID_SKAT_VISIBILITIES = [
    "unknown",
    "known_to_declarer",
    "known_post_game",
]

VALID_GAME_END_REASONS = [
    "not_ended",
    "normal_completion",
    "declarer_claimed_remaining_tricks",
    "declarer_conceded_remaining_tricks",
    "defenders_conceded_remaining_tricks",
]


@dataclass(frozen=True)
class StrategicMetadata:
    """
    Describes strategic context around an analysis.

    This is a placeholder for future logic. It is not actively used
    by the simulation engine yet.
    """
    analysis_mode: str = "live_decision"
    skat_visibility: str = "unknown"
    game_end_reason: str = "not_ended"


def validate_analysis_mode(analysis_mode: str) -> None:
    """
    Validates analysis mode.
    """
    if analysis_mode not in VALID_ANALYSIS_MODES:
        raise ValueError(f"Invalid analysis mode: {analysis_mode}")


def validate_skat_visibility(skat_visibility: str) -> None:
    """
    Validates skat visibility.
    """
    if skat_visibility not in VALID_SKAT_VISIBILITIES:
        raise ValueError(f"Invalid skat visibility: {skat_visibility}")


def validate_game_end_reason(game_end_reason: str) -> None:
    """
    Validates game end reason.
    """
    if game_end_reason not in VALID_GAME_END_REASONS:
        raise ValueError(f"Invalid game end reason: {game_end_reason}")


def validate_strategic_metadata(metadata: StrategicMetadata) -> None:
    """
    Validates strategic metadata.
    """
    validate_analysis_mode(metadata.analysis_mode)
    validate_skat_visibility(metadata.skat_visibility)
    validate_game_end_reason(metadata.game_end_reason)
    validate_analysis_mode_skat_visibility_combination(
        analysis_mode=metadata.analysis_mode,
        skat_visibility=metadata.skat_visibility,
    )


def build_default_strategic_metadata() -> StrategicMetadata:
    """
    Builds default strategic metadata.
    """
    return StrategicMetadata()


def build_strategic_metadata_from_dict(
    data: dict[str, str],
) -> StrategicMetadata:
    """
    Builds strategic metadata from a dictionary.
    """
    metadata = StrategicMetadata(
        analysis_mode=data.get("analysis_mode", "live_decision"),
        skat_visibility=data.get("skat_visibility", "unknown"),
        game_end_reason=data.get("game_end_reason", "not_ended"),
    )

    validate_strategic_metadata(metadata)

    return metadata

def validate_analysis_mode_skat_visibility_combination(
    analysis_mode: str,
    skat_visibility: str,
) -> None:
    """
    Validates that skat visibility is compatible with the analysis mode.
    """
    if (
        analysis_mode == "live_decision"
        and skat_visibility == "known_post_game"
    ):
        raise ValueError(
            "skat_visibility='known_post_game' is only allowed "
            "for analysis_mode='post_game_review'."
        )