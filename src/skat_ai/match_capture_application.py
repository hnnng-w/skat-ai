from __future__ import annotations

from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_capture_application_contracts import (
    MatchCaptureApplicationResultV1,
    MatchCaptureCardEntryV1,
)
from skat_ai.match_capture_game_updates import (
    append_match_capture_game_plays_v1,
    build_default_match_capture_game_id_v1,
    build_started_match_capture_game_v1,
    rebuild_match_capture_game_v1,
    remove_match_capture_game_commentary_v1,
    remove_match_capture_game_response_link_v1,
    set_match_capture_game_commentary_v1,
    set_match_capture_game_response_link_v1,
    truncate_match_capture_game_plays_v1,
)
from skat_ai.match_capture_position_view import build_match_capture_position_view_v1
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.match_workspace_contracts import (
    MatchWorkspaceV1,
    _require_match_position,
    _require_non_negative_integer,
    validate_match_workspace_v1,
)
from skat_ai.match_workspace_operations import (
    MatchWorkspaceChangeResultV1,
    _conflict,
    clear_match_workspace_slot_v1,
    mark_match_workspace_passed_deal_v1,
    set_match_workspace_observed_game_v1,
)
from skat_ai.observed_game_contracts import ObservedGameRecordV1
from skat_ai.observed_game_trace import copy_observed_timecode_v1
from skat_ai.performance_rating import validate_stable_list_entry_identifier


def _capture_result(
    *,
    operation: str,
    workspace_change: MatchWorkspaceChangeResultV1,
    removed_commentary_ids: tuple[str, ...] = (),
    removed_response_link_ids: tuple[str, ...] = (),
    affected_commentary_id: str | None = None,
    affected_response_link_id: str | None = None,
) -> MatchCaptureApplicationResultV1:
    assert workspace_change.match_position is not None
    position_view = build_match_capture_position_view_v1(
        workspace_change.workspace,
        match_position=workspace_change.match_position,
    )
    return MatchCaptureApplicationResultV1._from_validated(
        operation=operation,
        status=workspace_change.status,
        workspace_change=workspace_change,
        position_view=position_view,
        removed_commentary_ids=removed_commentary_ids,
        removed_response_link_ids=removed_response_link_ids,
        affected_commentary_id=affected_commentary_id,
        affected_response_link_id=affected_response_link_id,
    )


def _prepare_game_operation(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    expected_revision: int,
) -> tuple[int, MatchWorkspaceChangeResultV1 | None]:
    validate_match_workspace_v1(workspace)
    _require_non_negative_integer(expected_revision, "expected_revision")
    position = _require_match_position(match_position)
    if expected_revision == workspace.revision:
        return position, None
    return position, _conflict(
        workspace,
        operation="set_observed_game",
        expected_revision=expected_revision,
        match_position=position,
        previous_slot=workspace.slots[position - 1],
    )


def _prepared_game(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
) -> ObservedGameRecordV1:
    game = workspace.slots[match_position - 1].observed_game
    if game is None:
        raise ValueError("The target Slot must contain an observed Game.")
    return game


def _apply_game(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    operation: str,
    expected_revision: int,
    removed_commentary_ids: tuple[str, ...] = (),
    removed_response_link_ids: tuple[str, ...] = (),
    affected_commentary_id: str | None = None,
    affected_response_link_id: str | None = None,
) -> MatchCaptureApplicationResultV1:
    workspace_change = set_match_workspace_observed_game_v1(
        workspace,
        game,
        expected_revision=expected_revision,
    )
    return _capture_result(
        operation=operation,
        workspace_change=workspace_change,
        removed_commentary_ids=removed_commentary_ids,
        removed_response_link_ids=removed_response_link_ids,
        affected_commentary_id=affected_commentary_id,
        affected_response_link_id=affected_response_link_id,
    )


def _conflict_result(
    *,
    operation: str,
    workspace_change: MatchWorkspaceChangeResultV1 | None,
) -> MatchCaptureApplicationResultV1 | None:
    if workspace_change is None:
        return None
    return _capture_result(operation=operation, workspace_change=workspace_change)


def start_match_capture_game_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    expected_revision: int,
    game_id: str | None = None,
    game_timecode: MediaTimecodeV1 | None = None,
) -> MatchCaptureApplicationResultV1:
    """Starts one rotated observed Game without erasing retained evidence."""
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(operation="start_game", workspace_change=conflict):
        return result
    retained_game_id = (
        build_default_match_capture_game_id_v1(
            workspace,
            match_position=position,
        )
        if game_id is None
        else game_id
    )
    validate_stable_list_entry_identifier(retained_game_id, "game_id")
    retained_timecode = copy_observed_timecode_v1(game_timecode, "game_timecode")
    existing_game = workspace.slots[position - 1].observed_game
    if existing_game is not None:
        if (
            existing_game.game_id != retained_game_id
            or existing_game.game_timecode != retained_timecode
        ):
            raise ValueError(
                "An existing observed Game requires matching identity and timecode; "
                "clear it or use the focused timecode operation."
            )
        return _apply_game(
            workspace,
            existing_game,
            operation="start_game",
            expected_revision=expected_revision,
        )
    game = build_started_match_capture_game_v1(
        workspace,
        match_position=position,
        game_id=retained_game_id,
        game_timecode=retained_timecode,
    )
    return _apply_game(
        workspace,
        game,
        operation="start_game",
        expected_revision=expected_revision,
    )


def set_match_capture_game_timecode_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    game_timecode: MediaTimecodeV1 | None,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="set_game_timecode",
        workspace_change=conflict,
    ):
        return result
    game = rebuild_match_capture_game_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        game_timecode=game_timecode,
    )
    return _apply_game(
        workspace,
        game,
        operation="set_game_timecode",
        expected_revision=expected_revision,
    )


def set_match_capture_perspective_initial_hand_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    cards: tuple[str, ...] | None,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="set_perspective_hand",
        workspace_change=conflict,
    ):
        return result
    game = rebuild_match_capture_game_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        perspective_initial_hand=cards,
    )
    return _apply_game(
        workspace,
        game,
        operation="set_perspective_hand",
        expected_revision=expected_revision,
    )


def set_match_capture_declaration_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    declarer_player_id: str | None,
    declaration: GameDeclaration | None,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="set_declaration",
        workspace_change=conflict,
    ):
        return result
    game = rebuild_match_capture_game_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        declarer_player_id=declarer_player_id,
        declaration=declaration,
    )
    return _apply_game(
        workspace,
        game,
        operation="set_declaration",
        expected_revision=expected_revision,
    )


def set_match_capture_original_skat_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    cards: tuple[str, ...] | None,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="set_original_skat",
        workspace_change=conflict,
    ):
        return result
    game = rebuild_match_capture_game_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        original_skat=cards,
    )
    return _apply_game(
        workspace,
        game,
        operation="set_original_skat",
        expected_revision=expected_revision,
    )


def set_match_capture_discarded_cards_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    cards: tuple[str, ...] | None,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="set_discarded_cards",
        workspace_change=conflict,
    ):
        return result
    game = rebuild_match_capture_game_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        discarded_cards=cards,
    )
    return _apply_game(
        workspace,
        game,
        operation="set_discarded_cards",
        expected_revision=expected_revision,
    )


def append_match_capture_plays_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    entries: tuple[MatchCaptureCardEntryV1, ...],
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="append_plays",
        workspace_change=conflict,
    ):
        return result
    game = append_match_capture_game_plays_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        entries=entries,
    )
    return _apply_game(
        workspace,
        game,
        operation="append_plays",
        expected_revision=expected_revision,
    )


def append_match_capture_play_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    entry: MatchCaptureCardEntryV1,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    """Delegates the ordinary single-Card path to atomic batch append."""
    return append_match_capture_plays_v1(
        workspace,
        match_position=match_position,
        entries=(entry,),
        expected_revision=expected_revision,
    )


def truncate_match_capture_plays_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    target_play_count: int,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="truncate_plays",
        workspace_change=conflict,
    ):
        return result
    game, removed_commentaries, removed_links = truncate_match_capture_game_plays_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        target_play_count=target_play_count,
    )
    return _apply_game(
        workspace,
        game,
        operation="truncate_plays",
        expected_revision=expected_revision,
        removed_commentary_ids=removed_commentaries,
        removed_response_link_ids=removed_links,
    )


def undo_match_capture_last_play_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="truncate_plays",
        workspace_change=conflict,
    ):
        return result
    game = _prepared_game(workspace, match_position=position)
    candidate, removed_commentaries, removed_links = truncate_match_capture_game_plays_v1(
        workspace,
        game,
        target_play_count=max(0, len(game.plays) - 1),
    )
    return _apply_game(
        workspace,
        candidate,
        operation="truncate_plays",
        expected_revision=expected_revision,
        removed_commentary_ids=removed_commentaries,
        removed_response_link_ids=removed_links,
    )


def set_match_capture_commentary_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    decision_index: int,
    commentator_player_id: str | None,
    commentator_name: str | None,
    text: str,
    commentary_timecode: MediaTimecodeV1 | None,
    expected_revision: int,
    commentary_id: str | None = None,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="set_commentary",
        workspace_change=conflict,
    ):
        return result
    game, affected_id, removed_links = set_match_capture_game_commentary_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        decision_index=decision_index,
        commentator_player_id=commentator_player_id,
        commentator_name=commentator_name,
        text=text,
        commentary_timecode=commentary_timecode,
        commentary_id=commentary_id,
    )
    return _apply_game(
        workspace,
        game,
        operation="set_commentary",
        expected_revision=expected_revision,
        removed_response_link_ids=removed_links,
        affected_commentary_id=affected_id,
    )


def remove_match_capture_commentary_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    commentary_id: str,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="remove_commentary",
        workspace_change=conflict,
    ):
        return result
    game, removed_commentaries, removed_links = remove_match_capture_game_commentary_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        commentary_id=commentary_id,
    )
    return _apply_game(
        workspace,
        game,
        operation="remove_commentary",
        expected_revision=expected_revision,
        removed_commentary_ids=removed_commentaries,
        removed_response_link_ids=removed_links,
    )


def set_match_capture_response_link_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    commentary_id: str,
    response_decision_index: int,
    expected_revision: int,
    link_id: str | None = None,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="set_response_link",
        workspace_change=conflict,
    ):
        return result
    game, affected_id = set_match_capture_game_response_link_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        commentary_id=commentary_id,
        response_decision_index=response_decision_index,
        link_id=link_id,
    )
    return _apply_game(
        workspace,
        game,
        operation="set_response_link",
        expected_revision=expected_revision,
        affected_response_link_id=affected_id,
    )


def remove_match_capture_response_link_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    link_id: str,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    position, conflict = _prepare_game_operation(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    if result := _conflict_result(
        operation="remove_response_link",
        workspace_change=conflict,
    ):
        return result
    game, removed_links = remove_match_capture_game_response_link_v1(
        workspace,
        _prepared_game(workspace, match_position=position),
        link_id=link_id,
    )
    return _apply_game(
        workspace,
        game,
        operation="remove_response_link",
        expected_revision=expected_revision,
        removed_response_link_ids=removed_links,
    )


def mark_match_capture_passed_deal_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    game_timecode: MediaTimecodeV1 | None,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    workspace_change = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=match_position,
        game_timecode=game_timecode,
        expected_revision=expected_revision,
    )
    return _capture_result(
        operation="mark_passed_deal",
        workspace_change=workspace_change,
    )


def clear_match_capture_position_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    workspace_change = clear_match_workspace_slot_v1(
        workspace,
        match_position=match_position,
        expected_revision=expected_revision,
    )
    return _capture_result(
        operation="clear_position",
        workspace_change=workspace_change,
    )
