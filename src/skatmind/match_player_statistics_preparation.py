from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from skatmind.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
)
from skatmind.match_capture_contracts import MatchCaptureDefinitionV1
from skatmind.match_player_statistics_context import (
    MatchPlayerStatisticsContextV1,
    build_match_player_statistics_context_v1,
)
from skatmind.opponent_statistics import (
    OPPONENT_STATISTICS_SCHEMA_VERSION,
    OpponentStatisticsInput,
    build_serializable_opponent_statistics_input,
)
from skatmind.performance_rating import validate_stable_list_entry_identifier
from skatmind.rfc3339 import parse_rfc3339_datetime

MATCH_PLAYER_STATISTICS_PREPARATION_VERSION = 1

MATCH_PLAYER_STATISTICS_PREPARATION_STATUSES: Final[tuple[str, ...]] = (
    "available",
    "unavailable",
)
MATCH_PLAYER_STATISTICS_INPUT_POLICY = (
    "eligible_records_in_canonical_table_place_order"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchPlayerStatisticsPreparationV1:
    """Canonical eligible Match statistics prepared without policy application."""

    match_player_statistics_preparation_version: int = (
        MATCH_PLAYER_STATISTICS_PREPARATION_VERSION
    )
    status: str
    match_id: str
    match_played_at: str | None
    participant_contexts: tuple[MatchPlayerStatisticsContextV1, ...]
    opponent_statistics_input: OpponentStatisticsInput | None
    eligible_player_ids: tuple[str, ...]
    actionable_player_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.match_player_statistics_preparation_version) is not int
            or self.match_player_statistics_preparation_version
            != MATCH_PLAYER_STATISTICS_PREPARATION_VERSION
        ):
            raise ValueError(
                "match_player_statistics_preparation_version must equal "
                f"{MATCH_PLAYER_STATISTICS_PREPARATION_VERSION}."
            )
        if self.status not in MATCH_PLAYER_STATISTICS_PREPARATION_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_PLAYER_STATISTICS_PREPARATION_STATUSES)}."
            )
        validate_stable_list_entry_identifier(self.match_id, "match_id")
        if self.match_played_at is not None:
            validate_stable_list_entry_identifier(
                self.match_played_at,
                "match_played_at",
            )
            parse_rfc3339_datetime(self.match_played_at, "match_played_at")
        if not isinstance(self.participant_contexts, (list, tuple)):
            raise ValueError("participant_contexts must be an ordered array.")
        contexts = tuple(self.participant_contexts)
        if len(contexts) != 3 or any(
            type(context) is not MatchPlayerStatisticsContextV1
            for context in contexts
        ):
            raise ValueError(
                "participant_contexts must contain exactly three Context values."
            )
        if tuple(context.table_place for context in contexts) != (
            FIXED_THREE_PLAYER_LIST_TABLE_PLACES
        ):
            raise ValueError("participant_contexts must use canonical table-place order.")
        if len({context.player_id for context in contexts}) != 3:
            raise ValueError("participant_contexts must contain unique Player IDs.")
        object.__setattr__(self, "participant_contexts", contexts)

        eligible_ids = tuple(
            context.player_id
            for context in contexts
            if context.eligible_for_match_analysis
        )
        actionable_ids = tuple(
            context.player_id
            for context in contexts
            if context.eligible_for_match_analysis
            and context.profile_derivation is not None
            and context.profile_derivation.actionable_policy_preset is not None
        )
        if self.eligible_player_ids != eligible_ids:
            raise ValueError("eligible_player_ids must equal the canonical eligible subset.")
        if self.actionable_player_ids != actionable_ids:
            raise ValueError(
                "actionable_player_ids must equal the canonical actionable eligible subset."
            )
        available = bool(eligible_ids)
        if self.status != ("available" if available else "unavailable"):
            raise ValueError("status must report whether eligible statistics are available.")
        if available:
            if type(self.opponent_statistics_input) is not OpponentStatisticsInput:
                raise ValueError("Available Preparation requires opponent_statistics_input.")
            if (
                type(self.opponent_statistics_input.schema_version) is not int
                or self.opponent_statistics_input.schema_version
                != OPPONENT_STATISTICS_SCHEMA_VERSION
            ):
                raise ValueError(
                    "opponent_statistics_input.schema_version must equal "
                    f"{OPPONENT_STATISTICS_SCHEMA_VERSION}."
                )
            if tuple(
                record.player_id for record in self.opponent_statistics_input.records
            ) != eligible_ids:
                raise ValueError(
                    "opponent_statistics_input records must equal eligible_player_ids."
                )
        elif self.opponent_statistics_input is not None:
            raise ValueError("Unavailable Preparation cannot contain statistics input.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_player_statistics_preparation_version": (
                self.match_player_statistics_preparation_version
            ),
            "status": self.status,
            "match_id": self.match_id,
            "match_played_at": self.match_played_at,
            "participant_contexts": [
                context.to_dict() for context in self.participant_contexts
            ],
            "opponent_statistics_input": (
                None
                if self.opponent_statistics_input is None
                else build_serializable_opponent_statistics_input(
                    self.opponent_statistics_input
                )["opponent_statistics_input"]
            ),
            "eligible_player_ids": list(self.eligible_player_ids),
            "actionable_player_ids": list(self.actionable_player_ids),
        }


def build_match_player_statistics_preparation_v1(
    match_definition: MatchCaptureDefinitionV1,
) -> MatchPlayerStatisticsPreparationV1:
    """Builds canonical strict-before-Match statistics input for later analysis."""
    if type(match_definition) is not MatchCaptureDefinitionV1:
        raise ValueError("match_definition must be a MatchCaptureDefinitionV1.")
    contexts = tuple(
        build_match_player_statistics_context_v1(
            match_definition,
            player_id=participant.player_id,
        )
        for participant in match_definition.participants
    )
    eligible_records = tuple(
        participant.statistics_snapshot.statistics_record
        for participant, context in zip(
            match_definition.participants,
            contexts,
            strict=True,
        )
        if context.eligible_for_match_analysis
        and participant.statistics_snapshot is not None
    )
    eligible_player_ids = tuple(record.player_id for record in eligible_records)
    actionable_player_ids = tuple(
        context.player_id
        for context in contexts
        if context.eligible_for_match_analysis
        and context.profile_derivation is not None
        and context.profile_derivation.actionable_policy_preset is not None
    )
    statistics_input = (
        OpponentStatisticsInput(
            schema_version=OPPONENT_STATISTICS_SCHEMA_VERSION,
            records=eligible_records,
        )
        if eligible_records
        else None
    )
    return MatchPlayerStatisticsPreparationV1(
        status="available" if eligible_records else "unavailable",
        match_id=match_definition.match_id,
        match_played_at=match_definition.played_at,
        participant_contexts=contexts,
        opponent_statistics_input=statistics_input,
        eligible_player_ids=eligible_player_ids,
        actionable_player_ids=actionable_player_ids,
    )
