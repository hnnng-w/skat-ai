from dataclasses import dataclass
from typing import Any

from skat_ai.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
)
from skat_ai.match_player_snapshot import (
    MatchParticipantV1,
    copy_match_participant_v1,
)
from skat_ai.match_source_metadata import (
    MatchSourceMetadataV1,
    copy_match_source_metadata_v1,
)
from skat_ai.match_tournament_format import (
    MatchTournamentFormatV1,
    get_match_tournament_format_v1,
)
from skat_ai.performance_rating import (
    validate_stable_list_entry_identifier,
    validate_stable_list_player_label,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime

MATCH_CAPTURE_CONTRACT_VERSION = 1
MATCH_PERSPECTIVE_POLICY = "one_declared_match_player"

_RELATIVE_PLAYER_IDS = frozenset({"me", "left", "right"})


def _validate_perspective_player_id(value: object) -> None:
    validate_stable_list_entry_identifier(value, "perspective_player_id")
    if value in _RELATIVE_PLAYER_IDS:
        raise ValueError(
            "perspective_player_id must be a stable, non-relative Player ID."
        )


def _require_unique_non_null(
    values: tuple[str | None, ...],
    field_name: str,
) -> None:
    present = tuple(value for value in values if value is not None)
    if len(present) != len(set(present)):
        raise ValueError(f"Match participants must have unique non-null {field_name} values.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchCaptureDefinitionV1:
    """Immutable identity and metadata for one three-Player Match capture."""

    match_capture_contract_version: int = MATCH_CAPTURE_CONTRACT_VERSION
    match_id: str
    title: str
    game_platform: str
    external_match_id: str | None
    played_at: str | None
    tournament_format: MatchTournamentFormatV1
    source: MatchSourceMetadataV1
    participants: tuple[MatchParticipantV1, ...]
    perspective_player_id: str

    def __post_init__(self) -> None:
        if (
            type(self.match_capture_contract_version) is not int
            or self.match_capture_contract_version != MATCH_CAPTURE_CONTRACT_VERSION
        ):
            raise ValueError(
                "match_capture_contract_version must equal "
                f"{MATCH_CAPTURE_CONTRACT_VERSION}."
            )
        validate_stable_list_entry_identifier(self.match_id, "match_id")
        validate_stable_list_player_label(self.title, "title")
        validate_stable_list_player_label(self.game_platform, "game_platform")
        if self.external_match_id is not None:
            validate_stable_list_entry_identifier(
                self.external_match_id,
                "external_match_id",
            )
        if self.played_at is not None:
            validate_stable_list_entry_identifier(self.played_at, "played_at")
            parse_rfc3339_datetime(self.played_at, "played_at")

        if not isinstance(self.tournament_format, MatchTournamentFormatV1):
            raise ValueError("tournament_format must be MatchTournamentFormatV1.")
        canonical_format = get_match_tournament_format_v1(
            self.tournament_format.format_id
        )
        if self.tournament_format is not canonical_format:
            raise ValueError(
                "tournament_format must be the exact canonical supported format object."
            )

        source = copy_match_source_metadata_v1(self.source)
        if isinstance(self.participants, (str, bytes)) or not isinstance(
            self.participants, (list, tuple)
        ):
            raise ValueError("participants must be an ordered array.")
        if len(self.participants) != canonical_format.player_count:
            raise ValueError(
                f"participants must contain exactly {canonical_format.player_count} Players."
            )
        participants = tuple(
            copy_match_participant_v1(participant)
            for participant in self.participants
        )
        table_places = tuple(participant.table_place for participant in participants)
        if table_places != FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
            raise ValueError(
                "participants must cover all fixed table places in canonical order."
            )
        player_ids = tuple(participant.player_id for participant in participants)
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Match participant Player IDs must be unique.")
        _require_unique_non_null(
            tuple(participant.platform_player_id for participant in participants),
            "platform_player_id",
        )
        _require_unique_non_null(
            tuple(
                None
                if participant.statistics_snapshot is None
                else participant.statistics_snapshot.snapshot_id
                for participant in participants
            ),
            "snapshot_id",
        )

        _validate_perspective_player_id(self.perspective_player_id)
        if self.perspective_player_id not in player_ids:
            raise ValueError(
                "perspective_player_id must reference exactly one Match participant."
            )

        object.__setattr__(self, "source", source)
        object.__setattr__(self, "participants", participants)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_capture_contract_version": self.match_capture_contract_version,
            "match_id": self.match_id,
            "title": self.title,
            "game_platform": self.game_platform,
            "external_match_id": self.external_match_id,
            "played_at": self.played_at,
            "tournament_format": self.tournament_format.to_dict(),
            "source": self.source.to_dict(),
            "participants": [participant.to_dict() for participant in self.participants],
            "perspective_player_id": self.perspective_player_id,
        }
