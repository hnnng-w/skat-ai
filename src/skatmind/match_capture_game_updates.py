from __future__ import annotations

from typing import cast

from skatmind.game_declaration import GameDeclaration
from skatmind.match_capture_application_contracts import MatchCaptureCardEntryV1
from skatmind.match_source_metadata import MediaTimecodeV1
from skatmind.match_workspace_contracts import (
    MatchWorkspaceV1,
    _require_match_position,
    validate_match_workspace_v1,
)
from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1
from skatmind.observed_game_commentary import (
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
)
from skatmind.observed_game_contracts import (
    ObservedGameRecordV1,
    build_observed_game_record_v1,
    build_observed_perspective_playable_hand_v1,
)
from skatmind.observed_game_trace import (
    ObservedPlayV1,
    validate_observed_game_trace_v1,
)
from skatmind.performance_rating import validate_stable_list_entry_identifier
from skatmind.rules import get_trick_winner

_RETAIN = object()


def build_default_match_capture_game_id_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
) -> str:
    """Builds the deterministic default Game ID for one Match position."""
    validate_match_workspace_v1(workspace)
    position = _require_match_position(match_position)
    game_id = f"{workspace.match_definition.match_id}-game-{position:02d}"
    validate_stable_list_entry_identifier(game_id, "game_id")
    return game_id


def build_default_match_capture_commentary_id_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
) -> str:
    """Builds one revision-derived default Commentary ID."""
    validate_match_workspace_v1(workspace)
    position = _require_match_position(match_position)
    game = workspace.slots[position - 1].observed_game
    if game is None:
        raise ValueError("The target Slot must contain an observed Game.")
    commentary_id = f"{game.game_id}-commentary-r{workspace.revision + 1}"
    validate_stable_list_entry_identifier(commentary_id, "commentary_id")
    return commentary_id


def build_default_match_capture_response_link_id_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
) -> str:
    """Builds one revision-derived default Response Link ID."""
    validate_match_workspace_v1(workspace)
    position = _require_match_position(match_position)
    game = workspace.slots[position - 1].observed_game
    if game is None:
        raise ValueError("The target Slot must contain an observed Game.")
    link_id = f"{game.game_id}-response-r{workspace.revision + 1}"
    validate_stable_list_entry_identifier(link_id, "link_id")
    return link_id


def build_started_match_capture_game_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    game_id: str,
    game_timecode: MediaTimecodeV1 | None,
) -> ObservedGameRecordV1:
    """Builds one empty-evidence observed Game with canonical rotation."""
    position = _require_match_position(match_position)
    assignment = build_match_workspace_seat_assignment_v1(
        workspace.match_definition,
        position,
    )
    return build_observed_game_record_v1(
        workspace.match_definition,
        game_id=game_id,
        match_position=position,
        game_timecode=game_timecode,
        seat_order_player_ids=(
            assignment.forehand_player_id,
            assignment.middlehand_player_id,
            assignment.rearhand_player_id,
        ),
        perspective_initial_hand=None,
        declarer_player_id=None,
        declaration=None,
        original_skat=None,
        discarded_cards=None,
        plays=(),
        commentaries=(),
        response_links=(),
    )


def rebuild_match_capture_game_v1(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    game_timecode: MediaTimecodeV1 | None | object = _RETAIN,
    perspective_initial_hand: tuple[str, ...] | None | object = _RETAIN,
    declarer_player_id: str | None | object = _RETAIN,
    declaration: GameDeclaration | None | object = _RETAIN,
    original_skat: tuple[str, ...] | None | object = _RETAIN,
    discarded_cards: tuple[str, ...] | None | object = _RETAIN,
    plays: tuple[ObservedPlayV1, ...] | object = _RETAIN,
    commentaries: tuple[ObservedDecisionCommentaryV1, ...] | object = _RETAIN,
    response_links: tuple[ObservedDecisionResponseLinkV1, ...] | object = _RETAIN,
) -> ObservedGameRecordV1:
    """Defensively rebuilds a complete Game while replacing focused facts."""
    if type(workspace) is not MatchWorkspaceV1:
        raise ValueError("workspace must be a MatchWorkspaceV1.")
    if type(game) is not ObservedGameRecordV1:
        raise ValueError("game must be an ObservedGameRecordV1.")
    return build_observed_game_record_v1(
        workspace.match_definition,
        game_id=game.game_id,
        match_position=game.match_position,
        game_timecode=cast(
            MediaTimecodeV1 | None,
            game.game_timecode if game_timecode is _RETAIN else game_timecode,
        ),
        seat_order_player_ids=tuple(player.player_id for player in game.players),
        perspective_initial_hand=cast(
            tuple[str, ...] | None,
            game.perspective_initial_hand
            if perspective_initial_hand is _RETAIN
            else perspective_initial_hand,
        ),
        declarer_player_id=cast(
            str | None,
            game.declarer_player_id if declarer_player_id is _RETAIN else declarer_player_id,
        ),
        declaration=cast(
            GameDeclaration | None,
            game.declaration if declaration is _RETAIN else declaration,
        ),
        original_skat=cast(
            tuple[str, ...] | None,
            game.original_skat if original_skat is _RETAIN else original_skat,
        ),
        discarded_cards=cast(
            tuple[str, ...] | None,
            game.discarded_cards if discarded_cards is _RETAIN else discarded_cards,
        ),
        plays=cast(tuple[ObservedPlayV1, ...], game.plays if plays is _RETAIN else plays),
        commentaries=cast(
            tuple[ObservedDecisionCommentaryV1, ...],
            game.commentaries if commentaries is _RETAIN else commentaries,
        ),
        response_links=cast(
            tuple[ObservedDecisionResponseLinkV1, ...],
            game.response_links if response_links is _RETAIN else response_links,
        ),
    )


def _validated_trace(game: ObservedGameRecordV1):
    perspective_playable_hand = build_observed_perspective_playable_hand_v1(
        perspective_player_id=game.perspective_player_id,
        perspective_initial_hand=game.perspective_initial_hand,
        declarer_player_id=game.declarer_player_id,
        declaration=game.declaration,
        original_skat=game.original_skat,
        discarded_cards=game.discarded_cards,
    )
    return validate_observed_game_trace_v1(
        plays=game.plays,
        seat_order_player_ids=tuple(player.player_id for player in game.players),
        perspective_player_id=game.perspective_player_id,
        perspective_initial_hand=game.perspective_initial_hand,
        perspective_playable_hand=perspective_playable_hand,
        declarer_player_id=game.declarer_player_id,
        declaration=game.declaration,
        original_skat=game.original_skat,
        discarded_cards=game.discarded_cards,
        game_timecode=game.game_timecode,
    )


def append_match_capture_game_plays_v1(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    entries: tuple[MatchCaptureCardEntryV1, ...],
) -> ObservedGameRecordV1:
    """Derives actors and indexes, then rebuilds one final atomic Game candidate."""
    if type(entries) is not tuple or not entries:
        raise ValueError("entries must be a non-empty ordered tuple.")
    if any(type(entry) is not MatchCaptureCardEntryV1 for entry in entries):
        raise ValueError("entries must contain only MatchCaptureCardEntryV1 values.")
    if len(game.plays) + len(entries) > 30:
        raise ValueError("The retained trace may contain at most 30 Plays.")
    if game.declarer_player_id is None or game.declaration is None:
        raise ValueError("Observed Plays require both Declarer and Declaration facts.")

    trace = _validated_trace(game)
    seat_order = tuple(player.player_id for player in game.players)
    next_player_id = trace.next_player_id
    current_trick_plays = (
        list(game.plays[-trace.current_trick_play_count :])
        if trace.current_trick_play_count
        else []
    )
    candidate_plays = list(game.plays)

    for entry in entries:
        play = ObservedPlayV1(
            decision_index=len(candidate_plays) + 1,
            player_id=next_player_id,
            card=entry.card,
            decision_timecode=entry.decision_timecode,
        )
        candidate_plays.append(play)
        current_trick_plays.append(play)
        if len(current_trick_plays) == 3:
            winner_index = get_trick_winner(
                [item.card for item in current_trick_plays],
                game.declaration.game_type,
            )
            next_player_id = current_trick_plays[winner_index].player_id
            current_trick_plays = []
        else:
            player_index = seat_order.index(next_player_id)
            next_player_id = seat_order[(player_index + 1) % len(seat_order)]

    return rebuild_match_capture_game_v1(
        workspace,
        game,
        plays=tuple(candidate_plays),
    )


def truncate_match_capture_game_plays_v1(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    target_play_count: int,
) -> tuple[ObservedGameRecordV1, tuple[str, ...], tuple[str, ...]]:
    """Removes one Play suffix and every annotation made invalid by it."""
    if type(target_play_count) is not int or not 0 <= target_play_count <= len(game.plays):
        raise ValueError("target_play_count must be from 0 through current Play count.")
    retained_commentaries = tuple(
        item for item in game.commentaries if item.decision_index <= target_play_count
    )
    retained_commentary_ids = {item.commentary_id for item in retained_commentaries}
    retained_links = tuple(
        item
        for item in game.response_links
        if item.commentary_id in retained_commentary_ids
        and item.response_decision_index <= target_play_count
    )
    removed_commentary_ids = tuple(
        item.commentary_id
        for item in game.commentaries
        if item.commentary_id not in retained_commentary_ids
    )
    retained_link_ids = {item.link_id for item in retained_links}
    removed_response_link_ids = tuple(
        item.link_id for item in game.response_links if item.link_id not in retained_link_ids
    )
    candidate = rebuild_match_capture_game_v1(
        workspace,
        game,
        plays=game.plays[:target_play_count],
        commentaries=retained_commentaries,
        response_links=retained_links,
    )
    return candidate, removed_commentary_ids, removed_response_link_ids


def set_match_capture_game_commentary_v1(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    decision_index: int,
    commentator_player_id: str | None,
    commentator_name: str | None,
    text: str,
    commentary_timecode: MediaTimecodeV1 | None,
    commentary_id: str | None,
) -> tuple[ObservedGameRecordV1, str, tuple[str, ...]]:
    """Adds or replaces one free-text Commentary and reconciles its links."""
    plays_by_index = {play.decision_index: play for play in game.plays}
    play = plays_by_index.get(decision_index)
    if play is None:
        raise ValueError("decision_index must reference one retained Play.")
    retained_id = commentary_id
    if retained_id is None:
        retained_id = build_default_match_capture_commentary_id_v1(
            workspace,
            match_position=game.match_position,
        )
        if any(item.commentary_id == retained_id for item in game.commentaries):
            raise ValueError("The generated Commentary ID collides with retained commentary.")
    commentary = ObservedDecisionCommentaryV1(
        commentary_id=retained_id,
        decision_index=decision_index,
        subject_player_id=play.player_id,
        commentator_player_id=commentator_player_id,
        commentator_name=commentator_name,
        text=text,
        commentary_timecode=commentary_timecode,
    )
    replaced = False
    commentaries: list[ObservedDecisionCommentaryV1] = []
    for existing in game.commentaries:
        if existing.commentary_id == retained_id:
            commentaries.append(commentary)
            replaced = True
        else:
            commentaries.append(existing)
    if not replaced:
        commentaries.append(commentary)

    retained_links = tuple(
        link
        for link in game.response_links
        if link.commentary_id != retained_id or link.response_decision_index > decision_index
    )
    retained_link_ids = {link.link_id for link in retained_links}
    removed_link_ids = tuple(
        link.link_id for link in game.response_links if link.link_id not in retained_link_ids
    )
    candidate = rebuild_match_capture_game_v1(
        workspace,
        game,
        commentaries=tuple(commentaries),
        response_links=retained_links,
    )
    return candidate, retained_id, removed_link_ids


def remove_match_capture_game_commentary_v1(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    commentary_id: str,
) -> tuple[ObservedGameRecordV1, tuple[str, ...], tuple[str, ...]]:
    """Removes one Commentary and all Response Links that reference it."""
    validate_stable_list_entry_identifier(commentary_id, "commentary_id")
    retained_commentaries = tuple(
        item for item in game.commentaries if item.commentary_id != commentary_id
    )
    removed_commentary_ids = (
        (commentary_id,) if len(retained_commentaries) != len(game.commentaries) else ()
    )
    retained_links = tuple(
        link for link in game.response_links if link.commentary_id != commentary_id
    )
    removed_link_ids = tuple(
        link.link_id for link in game.response_links if link.commentary_id == commentary_id
    )
    candidate = rebuild_match_capture_game_v1(
        workspace,
        game,
        commentaries=retained_commentaries,
        response_links=retained_links,
    )
    return candidate, removed_commentary_ids, removed_link_ids


def set_match_capture_game_response_link_v1(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    commentary_id: str,
    response_decision_index: int,
    link_id: str | None,
) -> tuple[ObservedGameRecordV1, str]:
    """Adds or replaces one caller-authored later-response association."""
    if not any(item.commentary_id == commentary_id for item in game.commentaries):
        raise ValueError("commentary_id must reference retained commentary.")
    retained_id = link_id
    if retained_id is None:
        retained_id = build_default_match_capture_response_link_id_v1(
            workspace,
            match_position=game.match_position,
        )
        if any(item.link_id == retained_id for item in game.response_links):
            raise ValueError("The generated Response Link ID collides with a retained link.")
    link = ObservedDecisionResponseLinkV1(
        link_id=retained_id,
        commentary_id=commentary_id,
        response_decision_index=response_decision_index,
    )
    replaced = False
    links: list[ObservedDecisionResponseLinkV1] = []
    for existing in game.response_links:
        if existing.link_id == retained_id:
            links.append(link)
            replaced = True
        else:
            links.append(existing)
    if not replaced:
        links.append(link)
    candidate = rebuild_match_capture_game_v1(
        workspace,
        game,
        response_links=tuple(links),
    )
    return candidate, retained_id


def remove_match_capture_game_response_link_v1(
    workspace: MatchWorkspaceV1,
    game: ObservedGameRecordV1,
    *,
    link_id: str,
) -> tuple[ObservedGameRecordV1, tuple[str, ...]]:
    """Removes one Response Link when retained."""
    validate_stable_list_entry_identifier(link_id, "link_id")
    retained_links = tuple(item for item in game.response_links if item.link_id != link_id)
    removed_link_ids = (link_id,) if len(retained_links) != len(game.response_links) else ()
    candidate = rebuild_match_capture_game_v1(
        workspace,
        game,
        response_links=retained_links,
    )
    return candidate, removed_link_ids
