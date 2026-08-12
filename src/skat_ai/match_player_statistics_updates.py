from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Final

from skat_ai.match_capture_contracts import MatchCaptureDefinitionV1
from skat_ai.match_player_snapshot import (
    MatchParticipantV1,
    MatchPlayerStatisticsSnapshotV1,
)
from skat_ai.match_player_statistics_context import MatchPlayerStatisticsContextV1
from skat_ai.match_player_statistics_preparation import (
    MatchPlayerStatisticsPreparationV1,
    build_match_player_statistics_preparation_v1,
)
from skat_ai.match_workspace_contracts import (
    MatchWorkspaceV1,
    _require_non_negative_integer,
    validate_match_workspace_v1,
)
from skat_ai.match_workspace_operations import (
    MatchWorkspaceChangeResultV1,
    replace_match_workspace_definition_v1,
)
from skat_ai.opponent_statistics import OpponentStatisticsRecord
from skat_ai.performance_rating import validate_stable_list_entry_identifier
from skat_ai.rfc3339 import parse_rfc3339_datetime

MATCH_PLAYER_STATISTICS_UPDATE_VERSION = 1

MATCH_PLAYER_STATISTICS_UPDATE_OPERATIONS: Final[tuple[str, ...]] = (
    "set_snapshot",
    "clear_snapshot",
)
MATCH_PLAYER_STATISTICS_UPDATE_STATUSES: Final[tuple[str, ...]] = (
    "applied",
    "unchanged",
    "revision_conflict",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchPlayerStatisticsUpdateResultV1:
    """One immutable Match-bound Snapshot update and its derived preparation."""

    match_player_statistics_update_version: int = MATCH_PLAYER_STATISTICS_UPDATE_VERSION
    operation: str
    status: str
    player_id: str
    workspace_change: MatchWorkspaceChangeResultV1
    player_context: MatchPlayerStatisticsContextV1
    preparation: MatchPlayerStatisticsPreparationV1

    def __post_init__(self) -> None:
        if (
            type(self.match_player_statistics_update_version) is not int
            or self.match_player_statistics_update_version
            != MATCH_PLAYER_STATISTICS_UPDATE_VERSION
        ):
            raise ValueError(
                "match_player_statistics_update_version must equal "
                f"{MATCH_PLAYER_STATISTICS_UPDATE_VERSION}."
            )
        if self.operation not in MATCH_PLAYER_STATISTICS_UPDATE_OPERATIONS:
            raise ValueError(
                f"operation must be one of {list(MATCH_PLAYER_STATISTICS_UPDATE_OPERATIONS)}."
            )
        if self.status not in MATCH_PLAYER_STATISTICS_UPDATE_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_PLAYER_STATISTICS_UPDATE_STATUSES)}."
            )
        validate_stable_list_entry_identifier(self.player_id, "player_id")
        if type(self.workspace_change) is not MatchWorkspaceChangeResultV1:
            raise ValueError("workspace_change must be MatchWorkspaceChangeResultV1.")
        if self.workspace_change.operation != "replace_definition":
            raise ValueError("Snapshot updates require one definition replacement.")
        if self.status != self.workspace_change.status:
            raise ValueError("status must equal workspace_change.status.")
        if type(self.player_context) is not MatchPlayerStatisticsContextV1:
            raise ValueError("player_context must be MatchPlayerStatisticsContextV1.")
        if type(self.preparation) is not MatchPlayerStatisticsPreparationV1:
            raise ValueError("preparation must be MatchPlayerStatisticsPreparationV1.")
        matching_contexts = tuple(
            context
            for context in self.preparation.participant_contexts
            if context.player_id == self.player_id
        )
        if matching_contexts != (self.player_context,):
            raise ValueError(
                "player_context must equal the selected returned participant Context."
            )
        if self.preparation.match_id != self.workspace_change.match_id:
            raise ValueError("preparation must describe the returned Workspace Match.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_player_statistics_update_version": (
                self.match_player_statistics_update_version
            ),
            "operation": self.operation,
            "status": self.status,
            "player_id": self.player_id,
            "workspace_change": self.workspace_change.to_dict(),
            "player_context": self.player_context.to_dict(),
            "preparation": self.preparation.to_dict(),
        }


def _participant(
    workspace: MatchWorkspaceV1,
    player_id: str,
) -> MatchParticipantV1:
    participant = next(
        (
            participant
            for participant in workspace.match_definition.participants
            if participant.player_id == player_id
        ),
        None,
    )
    if participant is None:
        raise ValueError("player_id must reference exactly one Match participant.")
    return participant


def _definition_with_snapshot(
    workspace: MatchWorkspaceV1,
    *,
    player_id: str,
    snapshot: MatchPlayerStatisticsSnapshotV1 | None,
) -> MatchCaptureDefinitionV1:
    definition = workspace.match_definition
    participants = tuple(
        MatchParticipantV1(
            player_id=participant.player_id,
            player_label=participant.player_label,
            platform_player_id=participant.platform_player_id,
            table_place=participant.table_place,
            statistics_snapshot=(
                snapshot
                if participant.player_id == player_id
                else participant.statistics_snapshot
            ),
        )
        for participant in definition.participants
    )
    return MatchCaptureDefinitionV1(
        match_capture_contract_version=definition.match_capture_contract_version,
        match_id=definition.match_id,
        title=definition.title,
        game_platform=definition.game_platform,
        external_match_id=definition.external_match_id,
        played_at=definition.played_at,
        tournament_format=definition.tournament_format,
        source=definition.source,
        participants=participants,
        perspective_player_id=definition.perspective_player_id,
    )


def _result(
    *,
    operation: str,
    player_id: str,
    workspace_change: MatchWorkspaceChangeResultV1,
) -> MatchPlayerStatisticsUpdateResultV1:
    preparation = build_match_player_statistics_preparation_v1(
        workspace_change.workspace.match_definition
    )
    player_context = next(
        context
        for context in preparation.participant_contexts
        if context.player_id == player_id
    )
    return MatchPlayerStatisticsUpdateResultV1(
        operation=operation,
        status=workspace_change.status,
        player_id=player_id,
        workspace_change=workspace_change,
        player_context=player_context,
        preparation=preparation,
    )


def build_default_match_player_statistics_snapshot_id_v1(
    workspace: MatchWorkspaceV1,
    *,
    player_id: str,
) -> str:
    """Builds the deterministic ID for the next applied participant update."""
    validate_match_workspace_v1(workspace)
    _participant(workspace, player_id)
    snapshot_id = (
        f"{workspace.match_definition.match_id}-{player_id}-statistics-"
        f"r{workspace.revision + 1}"
    )
    validate_stable_list_entry_identifier(snapshot_id, "snapshot_id")
    return snapshot_id


def _same_snapshot_content(
    existing: MatchPlayerStatisticsSnapshotV1,
    *,
    observed_at: str,
    statistics_record: OpponentStatisticsRecord,
) -> bool:
    existing_captured_at = existing.statistics_record.source.captured_at
    submitted_captured_at = statistics_record.source.captured_at
    return (
        existing.statistics_record
        == replace(
            statistics_record,
            source=replace(
                statistics_record.source,
                captured_at=existing_captured_at,
            ),
        )
        and parse_rfc3339_datetime(
            existing_captured_at,
            "existing statistics_record.source.captured_at",
        )
        == parse_rfc3339_datetime(
            submitted_captured_at,
            "statistics_record.source.captured_at",
        )
        and parse_rfc3339_datetime(existing.observed_at, "existing observed_at")
        == parse_rfc3339_datetime(observed_at, "observed_at")
    )


def set_match_player_statistics_snapshot_v1(
    workspace: MatchWorkspaceV1,
    *,
    player_id: str,
    observed_at: str,
    statistics_record: OpponentStatisticsRecord,
    expected_revision: int,
    snapshot_id: str | None = None,
) -> MatchPlayerStatisticsUpdateResultV1:
    """Sets or replaces one participant's immutable Match-bound Snapshot."""
    validate_match_workspace_v1(workspace)
    _require_non_negative_integer(expected_revision, "expected_revision")
    participant = _participant(workspace, player_id)
    if expected_revision != workspace.revision:
        return _result(
            operation="set_snapshot",
            player_id=player_id,
            workspace_change=replace_match_workspace_definition_v1(
                workspace,
                workspace.match_definition,
                expected_revision=expected_revision,
            ),
        )
    if type(statistics_record) is not OpponentStatisticsRecord:
        raise ValueError("statistics_record must be an OpponentStatisticsRecord.")
    if statistics_record.player_id != participant.player_id:
        raise ValueError("statistics_record Player ID must equal participant player_id.")
    if (
        participant.player_label is not None
        and statistics_record.player_label is not None
        and participant.player_label != statistics_record.player_label
    ):
        raise ValueError("Participant and statistics record non-null labels must agree.")
    if snapshot_id is not None:
        validate_stable_list_entry_identifier(snapshot_id, "snapshot_id")

    existing = participant.statistics_snapshot
    same_content = (
        existing is not None
        and _same_snapshot_content(
            existing,
            observed_at=observed_at,
            statistics_record=statistics_record,
        )
    )
    if same_content and (snapshot_id is None or snapshot_id == existing.snapshot_id):
        workspace_change = replace_match_workspace_definition_v1(
            workspace,
            workspace.match_definition,
            expected_revision=expected_revision,
        )
        return _result(
            operation="set_snapshot",
            player_id=player_id,
            workspace_change=workspace_change,
        )

    selected_snapshot_id = snapshot_id
    if selected_snapshot_id is None:
        selected_snapshot_id = build_default_match_player_statistics_snapshot_id_v1(
            workspace,
            player_id=player_id,
        )
    if (
        existing is not None
        and selected_snapshot_id == existing.snapshot_id
        and not same_content
    ):
        raise ValueError("An existing Snapshot ID cannot be reused with changed content.")
    for other in workspace.match_definition.participants:
        other_snapshot = other.statistics_snapshot
        if (
            other.player_id != player_id
            and other_snapshot is not None
            and other_snapshot.snapshot_id == selected_snapshot_id
        ):
            raise ValueError("Snapshot IDs must remain unique within one Match.")

    snapshot = MatchPlayerStatisticsSnapshotV1(
        snapshot_id=selected_snapshot_id,
        observed_at=observed_at,
        statistics_record=statistics_record,
    )
    workspace_change = replace_match_workspace_definition_v1(
        workspace,
        _definition_with_snapshot(
            workspace,
            player_id=player_id,
            snapshot=snapshot,
        ),
        expected_revision=expected_revision,
    )
    return _result(
        operation="set_snapshot",
        player_id=player_id,
        workspace_change=workspace_change,
    )


def clear_match_player_statistics_snapshot_v1(
    workspace: MatchWorkspaceV1,
    *,
    player_id: str,
    expected_revision: int,
) -> MatchPlayerStatisticsUpdateResultV1:
    """Clears one participant Snapshot or returns unchanged when absent."""
    validate_match_workspace_v1(workspace)
    _require_non_negative_integer(expected_revision, "expected_revision")
    participant = _participant(workspace, player_id)
    if expected_revision != workspace.revision or participant.statistics_snapshot is None:
        workspace_change = replace_match_workspace_definition_v1(
            workspace,
            workspace.match_definition,
            expected_revision=expected_revision,
        )
    else:
        workspace_change = replace_match_workspace_definition_v1(
            workspace,
            _definition_with_snapshot(
                workspace,
                player_id=player_id,
                snapshot=None,
            ),
            expected_revision=expected_revision,
        )
    return _result(
        operation="clear_snapshot",
        player_id=player_id,
        workspace_change=workspace_change,
    )
