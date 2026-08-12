from __future__ import annotations

from skat_ai.deck import get_full_deck
from skat_ai.match_capture_application_contracts import (
    MatchCapturePositionViewV1,
)
from skat_ai.match_workspace_contracts import (
    MatchWorkspaceV1,
    _require_match_position,
    validate_match_workspace_v1,
)
from skat_ai.match_workspace_progress import (
    _build_validated_match_workspace_progress_v1,
)
from skat_ai.match_workspace_rotation import build_match_workspace_seat_assignment_v1
from skat_ai.observed_game_contracts import (
    ObservedGameRecordV1,
    build_observed_perspective_playable_hand_v1,
)
from skat_ai.observed_game_evidence import (
    ObservedGameEvidenceSummaryV1,
    build_observed_game_evidence_summary_v1,
)
from skat_ai.observed_game_trace import (
    ObservedGameTraceSummaryV1,
    validate_observed_game_trace_v1,
)
from skat_ai.rules import get_legal_cards

_FULL_DECK = tuple(get_full_deck())


def _build_trace(
    game: ObservedGameRecordV1,
) -> tuple[ObservedGameTraceSummaryV1, tuple[str, ...] | None]:
    perspective_playable_hand = build_observed_perspective_playable_hand_v1(
        perspective_player_id=game.perspective_player_id,
        perspective_initial_hand=game.perspective_initial_hand,
        declarer_player_id=game.declarer_player_id,
        declaration=game.declaration,
        original_skat=game.original_skat,
        discarded_cards=game.discarded_cards,
    )
    trace = validate_observed_game_trace_v1(
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
    return trace, perspective_playable_hand


def _build_bounded_candidates(
    game: ObservedGameRecordV1,
    *,
    next_player_id: str,
    perspective_playable_hand: tuple[str, ...] | None,
) -> tuple[str, ...]:
    unavailable = {play.card for play in game.plays}
    if game.discarded_cards is not None:
        unavailable.update(game.discarded_cards)

    if next_player_id != game.perspective_player_id:
        known_perspective_cards = (
            perspective_playable_hand
            if perspective_playable_hand is not None
            else game.perspective_initial_hand
        )
        if known_perspective_cards is not None:
            unavailable.update(known_perspective_cards)

    assert game.declaration is not None
    if game.original_skat is not None and (
        game.declaration.hand_game or next_player_id != game.declarer_player_id
    ):
        unavailable.update(game.original_skat)
    return tuple(card for card in _FULL_DECK if card not in unavailable)


def _build_selectable_cards(
    game: ObservedGameRecordV1,
    *,
    next_player_id: str,
    current_trick_cards: tuple[str, ...],
    perspective_playable_hand: tuple[str, ...] | None,
) -> tuple[str, tuple[str, ...]]:
    if next_player_id == game.perspective_player_id and perspective_playable_hand is not None:
        played_by_perspective = {
            play.card for play in game.plays if play.player_id == game.perspective_player_id
        }
        remaining_hand = [
            card
            for card in _FULL_DECK
            if card in perspective_playable_hand and card not in played_by_perspective
        ]
        assert game.declaration is not None
        legal_cards = set(
            get_legal_cards(
                remaining_hand,
                list(current_trick_cards),
                game.declaration.game_type,
            )
        )
        return (
            "exact_legal_cards",
            tuple(card for card in _FULL_DECK if card in legal_cards),
        )
    return (
        "bounded_observation_candidates",
        _build_bounded_candidates(
            game,
            next_player_id=next_player_id,
            perspective_playable_hand=perspective_playable_hand,
        ),
    )


def build_match_capture_position_view_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
) -> MatchCapturePositionViewV1:
    """Builds one information-safe UI view without persistence or analysis."""
    validate_match_workspace_v1(workspace)
    position = _require_match_position(match_position)
    slot = workspace.slots[position - 1]
    assignment = build_match_workspace_seat_assignment_v1(
        workspace.match_definition,
        position,
    )
    seat_player_ids = (
        assignment.forehand_player_id,
        assignment.middlehand_player_id,
        assignment.rearhand_player_id,
    )

    game = slot.observed_game
    game_id = None
    declarer_player_id = None
    play_count = 0
    completed_trick_count = 0
    current_trick_play_count = 0
    current_trick_player_ids: tuple[str, ...] = ()
    current_trick_cards: tuple[str, ...] = ()
    next_player_id = None
    player_play_counts = tuple((player_id, 0) for player_id in seat_player_ids)
    played_cards: tuple[str, ...] = ()
    card_selection_scope = "unavailable"
    selectable_cards: tuple[str, ...] = ()
    evidence_summary: ObservedGameEvidenceSummaryV1 | None = None

    if slot.slot_kind == "empty":
        game_state = "empty"
        blockers = ("empty_slot",)
    elif slot.slot_kind == "passed_deal":
        game_state = "passed_deal"
        blockers = ("passed_deal",)
    else:
        assert game is not None
        trace, perspective_playable_hand = _build_trace(game)
        evidence_summary = build_observed_game_evidence_summary_v1(game)
        game_id = game.game_id
        declarer_player_id = game.declarer_player_id
        play_count = len(trace.plays)
        completed_trick_count = trace.completed_trick_count
        current_trick_play_count = trace.current_trick_play_count
        player_play_counts = trace.player_play_counts
        played_cards = tuple(play.card for play in trace.plays)
        if current_trick_play_count:
            current_trick_plays = trace.plays[-current_trick_play_count:]
            current_trick_player_ids = tuple(play.player_id for play in current_trick_plays)
            current_trick_cards = tuple(play.card for play in current_trick_plays)

        if game.declaration is None:
            game_state = "setup"
            blockers = ("missing_declaration",)
        elif trace.complete_play_trace:
            game_state = "play_complete"
            blockers = ("complete_play_trace",)
        else:
            game_state = "ready_for_play" if play_count == 0 else "play_in_progress"
            blockers = ()
            next_player_id = trace.next_player_id
            card_selection_scope, selectable_cards = _build_selectable_cards(
                game,
                next_player_id=next_player_id,
                current_trick_cards=current_trick_cards,
                perspective_playable_hand=perspective_playable_hand,
            )

    progress = _build_validated_match_workspace_progress_v1(workspace)
    return MatchCapturePositionViewV1._from_validated(
        match_id=workspace.match_definition.match_id,
        workspace_revision=workspace.revision,
        match_position=position,
        round_number=((position - 1) // 3) + 1,
        slot_kind=slot.slot_kind,
        game_state=game_state,
        dealer_player_id=assignment.dealer_player_id,
        forehand_player_id=assignment.forehand_player_id,
        middlehand_player_id=assignment.middlehand_player_id,
        rearhand_player_id=assignment.rearhand_player_id,
        perspective_player_id=workspace.match_definition.perspective_player_id,
        game_id=game_id,
        declarer_player_id=declarer_player_id,
        play_count=play_count,
        completed_trick_count=completed_trick_count,
        current_trick_play_count=current_trick_play_count,
        current_trick_player_ids=current_trick_player_ids,
        current_trick_cards=current_trick_cards,
        next_player_id=next_player_id,
        player_play_counts=player_play_counts,
        played_cards=played_cards,
        card_selection_scope=card_selection_scope,
        selectable_cards=selectable_cards,
        can_record_play=not blockers,
        record_play_blockers=blockers,
        can_truncate_plays=play_count > 0,
        evidence_summary=evidence_summary,
        workspace_progress=progress,
    )
