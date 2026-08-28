from __future__ import annotations

from typing import TYPE_CHECKING

from skatmind.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
    FixedThreePlayerListSeatAssignment,
    build_fixed_three_player_list_seat_assignment,
)
from skatmind.match_capture_contracts import MatchCaptureDefinitionV1

if TYPE_CHECKING:
    from skatmind.match_workspace_contracts import (
        MatchWorkspacePositionFactV1,
        MatchWorkspaceV1,
    )

MATCH_WORKSPACE_ROTATION_POLICY = "reuse_fixed_three_player_list_rotation"


def build_match_workspace_seat_assignment_v1(
    match_definition: MatchCaptureDefinitionV1,
    match_position: int,
) -> FixedThreePlayerListSeatAssignment:
    """Delegates one Match position to the existing fixed-list rotation."""
    if type(match_definition) is not MatchCaptureDefinitionV1:
        raise ValueError("match_definition must be a MatchCaptureDefinitionV1.")
    player_id_by_place = {
        participant.table_place: participant.player_id
        for participant in match_definition.participants
    }
    if tuple(player_id_by_place) != FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
        raise ValueError("Match participants must use canonical fixed table-place order.")
    return build_fixed_three_player_list_seat_assignment(
        match_position,
        player_id_by_place,
    )


def _build_position_fact(
    workspace: MatchWorkspaceV1,
    match_position: int,
) -> MatchWorkspacePositionFactV1:
    from skatmind.match_workspace_contracts import MatchWorkspacePositionFactV1
    from skatmind.observed_game_evidence import build_observed_game_evidence_summary_v1

    slot = workspace.slots[match_position - 1]
    assignment = build_match_workspace_seat_assignment_v1(
        workspace.match_definition,
        match_position,
    )
    game_id = None
    play_count = 0
    complete_play_trace = False
    if slot.observed_game is not None:
        evidence = build_observed_game_evidence_summary_v1(slot.observed_game)
        game_id = slot.observed_game.game_id
        play_count = evidence.play_count
        complete_play_trace = evidence.complete_play_trace
    return MatchWorkspacePositionFactV1(
        match_position=match_position,
        round_number=((match_position - 1) // 3) + 1,
        slot_kind=slot.slot_kind,
        dealer_player_id=assignment.dealer_player_id,
        forehand_player_id=assignment.forehand_player_id,
        middlehand_player_id=assignment.middlehand_player_id,
        rearhand_player_id=assignment.rearhand_player_id,
        game_id=game_id,
        play_count=play_count,
        complete_play_trace=complete_play_trace,
    )


def build_match_workspace_position_fact_v1(
    workspace: MatchWorkspaceV1,
    match_position: int,
) -> MatchWorkspacePositionFactV1:
    """Builds one non-persisted rotation and evidence fact."""
    from skatmind.match_workspace_contracts import (
        _require_match_position,
        validate_match_workspace_v1,
    )

    validate_match_workspace_v1(workspace)
    _require_match_position(match_position)
    return _build_position_fact(workspace, match_position)


def build_match_workspace_position_facts_v1(
    workspace: MatchWorkspaceV1,
) -> tuple[MatchWorkspacePositionFactV1, ...]:
    """Builds all 36 non-persisted position facts in canonical order."""
    from skatmind.match_workspace_contracts import validate_match_workspace_v1

    validate_match_workspace_v1(workspace)
    return tuple(_build_position_fact(workspace, position) for position in range(1, 37))
