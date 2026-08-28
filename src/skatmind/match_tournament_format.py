from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from skatmind.performance_rating import (
    validate_stable_list_entry_identifier,
    validate_stable_list_player_label,
)

MATCH_TOURNAMENT_FORMAT_VERSION = 1
MATCH_TOURNAMENT_FORMAT_REGISTRY_POLICY = "append_only_named_format_definitions"

SUPPORTED_MATCH_TOURNAMENT_FORMAT_IDS: Final[tuple[str, ...]] = (
    "euroskat_36_standard_v1",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchTournamentFormatV1:
    """Identity and fixed cardinality for one named executable Match format."""

    match_tournament_format_version: int = MATCH_TOURNAMENT_FORMAT_VERSION
    format_id: str
    provider: str
    display_name: str
    player_count: int
    game_count: int

    def __post_init__(self) -> None:
        if (
            type(self.match_tournament_format_version) is not int
            or self.match_tournament_format_version != MATCH_TOURNAMENT_FORMAT_VERSION
        ):
            raise ValueError(
                "match_tournament_format_version must equal "
                f"{MATCH_TOURNAMENT_FORMAT_VERSION}."
            )
        validate_stable_list_entry_identifier(self.format_id, "format_id")
        validate_stable_list_player_label(self.provider, "provider")
        validate_stable_list_player_label(self.display_name, "display_name")
        for field_name, value in (
            ("player_count", self.player_count),
            ("game_count", self.game_count),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_tournament_format_version": self.match_tournament_format_version,
            "format_id": self.format_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "player_count": self.player_count,
            "game_count": self.game_count,
        }


EUROSKAT_36_STANDARD_V1_FORMAT = MatchTournamentFormatV1(
    format_id="euroskat_36_standard_v1",
    provider="EuroSkat",
    display_name="36er Standard",
    player_count=3,
    game_count=36,
)

MATCH_TOURNAMENT_FORMAT_REGISTRY = MappingProxyType(
    {
        "euroskat_36_standard_v1": EUROSKAT_36_STANDARD_V1_FORMAT,
    }
)


def get_match_tournament_format_v1(format_id: str) -> MatchTournamentFormatV1:
    """Returns one exact immutable built-in Match format by canonical ID."""
    validate_stable_list_entry_identifier(format_id, "format_id")
    try:
        return MATCH_TOURNAMENT_FORMAT_REGISTRY[format_id]
    except KeyError as error:
        raise ValueError(f"Unknown Match tournament format: {format_id}") from error
