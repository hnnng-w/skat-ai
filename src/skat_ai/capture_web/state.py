from __future__ import annotations

from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import VALID_DECLARATION_GAME_TYPES
from skat_ai.match_capture_position_view import build_match_capture_position_view_v1
from skat_ai.match_workspace_contracts import MatchWorkspaceV1
from skat_ai.match_workspace_progress import build_match_workspace_progress_v1
from skat_ai.match_workspace_rotation import build_match_workspace_position_fact_v1

from .contracts import MATCH_CAPTURE_WEB_PROTOCOL_VERSION
from .timecodes import format_media_timecode_v1

_ORDERED_DECK = tuple(get_full_deck())
_SUIT_NAMES = {"C": "Clubs", "S": "Spades", "H": "Hearts", "D": "Diamonds"}
_RANK_NAMES = {
    "A": "Ace",
    "10": "Ten",
    "K": "King",
    "Q": "Queen",
    "J": "Jack",
    "9": "Nine",
    "8": "Eight",
    "7": "Seven",
}


def _card_summary(card: str, selectable: set[str]) -> dict[str, Any]:
    return {
        "code": card,
        "label": f"{_SUIT_NAMES[card[0]]} {_RANK_NAMES[card[1:]]}",
        "selectable": card in selectable,
    }


def _participant_summary(participant) -> dict[str, Any]:
    snapshot = participant.statistics_snapshot
    return {
        "player_id": participant.player_id,
        "player_label": participant.player_label,
        "platform_player_id": participant.platform_player_id,
        "table_place": participant.table_place,
        "statistics_snapshot": (
            None
            if snapshot is None
            else {
                "snapshot_id": snapshot.snapshot_id,
                "observed_at": snapshot.observed_at,
            }
        ),
    }


def _game_summary(game) -> dict[str, Any] | None:
    if game is None:
        return None
    declaration = game.declaration
    return {
        "game_id": game.game_id,
        "game_timecode": format_media_timecode_v1(game.game_timecode),
        "perspective_initial_hand": (
            None
            if game.perspective_initial_hand is None
            else list(game.perspective_initial_hand)
        ),
        "declarer_player_id": game.declarer_player_id,
        "declaration": (
            None
            if declaration is None
            else {
                "game_type": declaration.game_type,
                "hand_game": declaration.hand_game,
                "ouvert": declaration.ouvert,
                "schneider_announced": declaration.schneider_announced,
                "schwarz_announced": declaration.schwarz_announced,
                "matadors": declaration.matadors,
                "bid_value": declaration.bid_value,
            }
        ),
        "original_skat": None if game.original_skat is None else list(game.original_skat),
        "discarded_cards": (
            None if game.discarded_cards is None else list(game.discarded_cards)
        ),
        "plays": [
            {
                **play.to_dict(),
                "decision_timecode_text": format_media_timecode_v1(
                    play.decision_timecode
                )["start"],
                "trick_number": ((play.decision_index - 1) // 3) + 1,
            }
            for play in game.plays
        ],
        "commentaries": [
            {
                **commentary.to_dict(),
                "commentary_timecode_text": format_media_timecode_v1(
                    commentary.commentary_timecode
                )["start"],
            }
            for commentary in game.commentaries
        ],
        "response_links": [link.to_dict() for link in game.response_links],
    }


def build_match_capture_web_state_v1(
    workspace: MatchWorkspaceV1 | None,
    *,
    workspace_filename: str,
    selected_position: int = 1,
) -> dict[str, Any]:
    """Builds deterministic private browser state without paths or fingerprints."""
    if type(selected_position) is not int or not 1 <= selected_position <= 36:
        raise ValueError("selected_position must be an integer from 1 through 36.")
    base: dict[str, Any] = {
        "match_capture_web_protocol_version": MATCH_CAPTURE_WEB_PROTOCOL_VERSION,
        "workspace_exists": workspace is not None,
        "workspace_filename": workspace_filename,
        "selected_position": selected_position,
    }
    if workspace is None:
        return {
            **base,
            "creation_defaults": {
                "game_platform": "EuroSkat",
                "source_kind": "youtube_video",
                "tournament_format_id": "euroskat_36_standard_v1",
                "perspective_player_id": "",
            },
        }

    definition = workspace.match_definition
    progress = build_match_workspace_progress_v1(workspace)
    selected_slot = workspace.slots[selected_position - 1]
    view = build_match_capture_position_view_v1(
        workspace,
        match_position=selected_position,
    )
    first_empty = progress.next_empty_position
    slot_summaries = []
    for slot in workspace.slots:
        fact = build_match_workspace_position_fact_v1(workspace, slot.match_position)
        game = slot.observed_game
        slot_summaries.append(
            {
                **fact.to_dict(),
                "game_state": build_match_capture_position_view_v1(
                    workspace,
                    match_position=slot.match_position,
                ).game_state,
                "commentary_count": 0 if game is None else len(game.commentaries),
                "first_empty": slot.match_position == first_empty,
                "selected": slot.match_position == selected_position,
            }
        )
    selectable = set(view.selectable_cards)
    return {
        **base,
        "match": {
            "match_id": definition.match_id,
            "title": definition.title,
            "game_platform": definition.game_platform,
            "external_match_id": definition.external_match_id,
            "played_at": definition.played_at,
            "tournament_format_id": definition.tournament_format.format_id,
        },
        "source": {
            "source_kind": definition.source.source_kind,
            "source_url": definition.source.source_url,
            "source_title": definition.source.source_title,
            "source_channel_name": definition.source.source_channel_name,
            "match_timecode": format_media_timecode_v1(
                definition.source.match_timecode
            ),
        },
        "participants": [
            _participant_summary(participant) for participant in definition.participants
        ],
        "perspective_player_id": definition.perspective_player_id,
        "workspace_revision": workspace.revision,
        "progress": progress.to_dict(),
        "slots": slot_summaries,
        "selected_slot": selected_slot.to_dict(),
        "position_view": view.to_dict(),
        "game": _game_summary(selected_slot.observed_game),
        "declaration_options": list(VALID_DECLARATION_GAME_TYPES),
        "card_palette": [
            _card_summary(card, selectable) for card in _ORDERED_DECK
        ],
    }
