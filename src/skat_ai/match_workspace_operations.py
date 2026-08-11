from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from skat_ai.match_capture_contracts import MatchCaptureDefinitionV1
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.match_workspace_contracts import (
    MatchPassedDealV1,
    MatchWorkspaceSlotV1,
    MatchWorkspaceV1,
    _build_match_workspace_v1,
    _copy_match_definition_v1,
    _require_match_position,
    _require_non_negative_integer,
    validate_match_workspace_v1,
)
from skat_ai.observed_game_contracts import ObservedGameRecordV1

MATCH_WORKSPACE_CHANGE_VERSION = 1
MATCH_WORKSPACE_CHANGE_OPERATIONS: Final[tuple[str, ...]] = (
    "replace_definition",
    "set_observed_game",
    "mark_passed_deal",
    "clear_slot",
)
MATCH_WORKSPACE_CHANGE_STATUSES: Final[tuple[str, ...]] = (
    "applied",
    "unchanged",
    "revision_conflict",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspaceChangeResultV1:
    """One immutable applied, unchanged, or revision-conflict outcome."""

    match_workspace_change_version: int = MATCH_WORKSPACE_CHANGE_VERSION
    operation: str
    status: str
    match_id: str
    expected_revision: int
    source_revision: int
    current_revision: int
    match_position: int | None
    previous_slot: MatchWorkspaceSlotV1 | None
    workspace: MatchWorkspaceV1

    def __post_init__(self) -> None:
        if (
            type(self.match_workspace_change_version) is not int
            or self.match_workspace_change_version != MATCH_WORKSPACE_CHANGE_VERSION
        ):
            raise ValueError(
                f"match_workspace_change_version must equal {MATCH_WORKSPACE_CHANGE_VERSION}."
            )
        if self.operation not in MATCH_WORKSPACE_CHANGE_OPERATIONS:
            raise ValueError(
                f"operation must be one of {list(MATCH_WORKSPACE_CHANGE_OPERATIONS)}."
            )
        if self.status not in MATCH_WORKSPACE_CHANGE_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_WORKSPACE_CHANGE_STATUSES)}."
            )
        if not isinstance(self.match_id, str) or not self.match_id:
            raise ValueError("match_id must be a non-empty string.")
        for field_name in ("expected_revision", "source_revision", "current_revision"):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if type(self.workspace) is not MatchWorkspaceV1:
            raise ValueError("workspace must be a MatchWorkspaceV1.")
        if self.workspace.match_definition.match_id != self.match_id:
            raise ValueError("match_id must equal the returned Workspace Match ID.")
        if self.workspace.revision != self.current_revision:
            raise ValueError("current_revision must equal the returned Workspace revision.")

        if self.operation == "replace_definition":
            if self.match_position is not None or self.previous_slot is not None:
                raise ValueError(
                    "Definition replacement cannot contain match_position or previous_slot."
                )
        else:
            _require_match_position(self.match_position)
            if type(self.previous_slot) is not MatchWorkspaceSlotV1:
                raise ValueError("Slot operations require previous_slot.")
            self.previous_slot._validate_relationships()
            if self.previous_slot.match_position != self.match_position:
                raise ValueError("previous_slot must match match_position.")

        if self.status == "applied":
            if self.expected_revision != self.source_revision:
                raise ValueError("An applied Result requires the expected source revision.")
            if self.current_revision != self.source_revision + 1:
                raise ValueError("An applied Result must increment revision by one.")
        elif self.status == "unchanged":
            if self.expected_revision != self.source_revision:
                raise ValueError("An unchanged Result requires the expected source revision.")
            if self.current_revision != self.source_revision:
                raise ValueError("An unchanged Result must preserve revision.")
        else:
            if self.expected_revision == self.source_revision:
                raise ValueError("A revision conflict requires different revisions.")
            if self.current_revision != self.source_revision:
                raise ValueError("A revision conflict must preserve the source revision.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_change_version": self.match_workspace_change_version,
            "operation": self.operation,
            "status": self.status,
            "match_id": self.match_id,
            "expected_revision": self.expected_revision,
            "source_revision": self.source_revision,
            "current_revision": self.current_revision,
            "match_position": self.match_position,
            "previous_slot": (
                None if self.previous_slot is None else self.previous_slot.to_dict()
            ),
            "workspace": self.workspace.to_dict(),
        }


def _result(
    *,
    workspace: MatchWorkspaceV1,
    operation: str,
    status: str,
    expected_revision: int,
    source_revision: int,
    match_position: int | None,
    previous_slot: MatchWorkspaceSlotV1 | None,
) -> MatchWorkspaceChangeResultV1:
    return MatchWorkspaceChangeResultV1(
        operation=operation,
        status=status,
        match_id=workspace.match_definition.match_id,
        expected_revision=expected_revision,
        source_revision=source_revision,
        current_revision=workspace.revision,
        match_position=match_position,
        previous_slot=previous_slot,
        workspace=workspace,
    )


def _conflict(
    workspace: MatchWorkspaceV1,
    *,
    operation: str,
    expected_revision: int,
    match_position: int | None,
    previous_slot: MatchWorkspaceSlotV1 | None,
) -> MatchWorkspaceChangeResultV1:
    return _result(
        workspace=workspace,
        operation=operation,
        status="revision_conflict",
        expected_revision=expected_revision,
        source_revision=workspace.revision,
        match_position=match_position,
        previous_slot=previous_slot,
    )


def _replace_slot(
    workspace: MatchWorkspaceV1,
    *,
    operation: str,
    expected_revision: int,
    match_position: int,
    candidate_slot: MatchWorkspaceSlotV1,
) -> MatchWorkspaceChangeResultV1:
    previous_slot = workspace.slots[match_position - 1]
    candidate_slots = list(workspace.slots)
    candidate_slots[match_position - 1] = candidate_slot
    candidate = _build_match_workspace_v1(
        revision=workspace.revision + 1,
        match_definition=workspace.match_definition,
        slots=candidate_slots,
    )
    if candidate.slots[match_position - 1] == previous_slot:
        return _result(
            workspace=workspace,
            operation=operation,
            status="unchanged",
            expected_revision=expected_revision,
            source_revision=workspace.revision,
            match_position=match_position,
            previous_slot=previous_slot,
        )
    return _result(
        workspace=candidate,
        operation=operation,
        status="applied",
        expected_revision=expected_revision,
        source_revision=workspace.revision,
        match_position=match_position,
        previous_slot=previous_slot,
    )


def set_match_workspace_observed_game_v1(
    workspace: MatchWorkspaceV1,
    observed_game: ObservedGameRecordV1,
    *,
    expected_revision: int,
) -> MatchWorkspaceChangeResultV1:
    """Sets or replaces one partial or complete observed Game."""
    validate_match_workspace_v1(workspace)
    _require_non_negative_integer(expected_revision, "expected_revision")
    target_position = getattr(observed_game, "match_position", None)
    if expected_revision != workspace.revision:
        _require_match_position(target_position)
        return _conflict(
            workspace,
            operation="set_observed_game",
            expected_revision=expected_revision,
            match_position=target_position,
            previous_slot=workspace.slots[target_position - 1],
        )
    if type(observed_game) is not ObservedGameRecordV1:
        raise ValueError("observed_game must be an ObservedGameRecordV1.")
    match_position = _require_match_position(observed_game.match_position)
    candidate_slot = MatchWorkspaceSlotV1._from_validated(
        match_position=match_position,
        slot_kind="observed_game",
        observed_game=observed_game,
        passed_deal=None,
    )
    return _replace_slot(
        workspace,
        operation="set_observed_game",
        expected_revision=expected_revision,
        match_position=match_position,
        candidate_slot=candidate_slot,
    )


def mark_match_workspace_passed_deal_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    game_timecode: MediaTimecodeV1 | None,
    expected_revision: int,
) -> MatchWorkspaceChangeResultV1:
    """Marks one position as passed without creating a synthetic Game."""
    validate_match_workspace_v1(workspace)
    _require_non_negative_integer(expected_revision, "expected_revision")
    if expected_revision != workspace.revision:
        position = _require_match_position(match_position)
        return _conflict(
            workspace,
            operation="mark_passed_deal",
            expected_revision=expected_revision,
            match_position=position,
            previous_slot=workspace.slots[position - 1],
        )
    position = _require_match_position(match_position)
    candidate_slot = MatchWorkspaceSlotV1._from_validated(
        match_position=position,
        slot_kind="passed_deal",
        observed_game=None,
        passed_deal=MatchPassedDealV1(game_timecode=game_timecode),
    )
    return _replace_slot(
        workspace,
        operation="mark_passed_deal",
        expected_revision=expected_revision,
        match_position=position,
        candidate_slot=candidate_slot,
    )


def clear_match_workspace_slot_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    expected_revision: int,
) -> MatchWorkspaceChangeResultV1:
    """Clears one occupied Slot or returns unchanged for an empty Slot."""
    validate_match_workspace_v1(workspace)
    _require_non_negative_integer(expected_revision, "expected_revision")
    if expected_revision != workspace.revision:
        position = _require_match_position(match_position)
        return _conflict(
            workspace,
            operation="clear_slot",
            expected_revision=expected_revision,
            match_position=position,
            previous_slot=workspace.slots[position - 1],
        )
    position = _require_match_position(match_position)
    candidate_slot = MatchWorkspaceSlotV1._from_validated(
        match_position=position,
        slot_kind="empty",
        observed_game=None,
        passed_deal=None,
    )
    return _replace_slot(
        workspace,
        operation="clear_slot",
        expected_revision=expected_revision,
        match_position=position,
        candidate_slot=candidate_slot,
    )


def replace_match_workspace_definition_v1(
    workspace: MatchWorkspaceV1,
    new_match_definition: MatchCaptureDefinitionV1,
    *,
    expected_revision: int,
) -> MatchWorkspaceChangeResultV1:
    """Corrects descriptive metadata while preserving structural Match identity."""
    validate_match_workspace_v1(workspace)
    _require_non_negative_integer(expected_revision, "expected_revision")
    if expected_revision != workspace.revision:
        return _conflict(
            workspace,
            operation="replace_definition",
            expected_revision=expected_revision,
            match_position=None,
            previous_slot=None,
        )
    candidate_definition = _copy_match_definition_v1(new_match_definition)
    source_definition = workspace.match_definition
    if candidate_definition.match_id != source_definition.match_id:
        raise ValueError("Match definition replacement must preserve match_id.")
    if candidate_definition.tournament_format is not source_definition.tournament_format:
        raise ValueError("Match definition replacement must preserve tournament format.")
    source_participant_identity = tuple(
        (participant.player_id, participant.table_place)
        for participant in source_definition.participants
    )
    candidate_participant_identity = tuple(
        (participant.player_id, participant.table_place)
        for participant in candidate_definition.participants
    )
    if candidate_participant_identity != source_participant_identity:
        raise ValueError(
            "Match definition replacement must preserve Participant IDs and table places."
        )
    if candidate_definition.perspective_player_id != source_definition.perspective_player_id:
        raise ValueError("Match definition replacement must preserve perspective.")

    candidate = _build_match_workspace_v1(
        revision=workspace.revision + 1,
        match_definition=candidate_definition,
        slots=workspace.slots,
    )
    if candidate.match_definition == source_definition:
        return _result(
            workspace=workspace,
            operation="replace_definition",
            status="unchanged",
            expected_revision=expected_revision,
            source_revision=workspace.revision,
            match_position=None,
            previous_slot=None,
        )
    return _result(
        workspace=candidate,
        operation="replace_definition",
        status="applied",
        expected_revision=expected_revision,
        source_revision=workspace.revision,
        match_position=None,
        previous_slot=None,
    )
