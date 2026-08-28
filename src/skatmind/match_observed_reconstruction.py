from dataclasses import dataclass

from skatmind.observed_game_contracts import (
    ObservedGameRecordV1,
    build_observed_perspective_playable_hand_v1,
)
from skatmind.observed_game_evidence import (
    ObservedGameEvidenceSummaryV1,
    build_observed_game_evidence_summary_from_trace_v1,
)
from skatmind.observed_game_trace import (
    ObservedGameTraceSummaryV1,
    validate_observed_game_trace_v1,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchObservedGameReconstructionV1:
    """One validated observed trace and only its exactly reconstructable hands."""

    observed_game: ObservedGameRecordV1
    trace: ObservedGameTraceSummaryV1
    evidence_summary: ObservedGameEvidenceSummaryV1
    playable_hands: tuple[tuple[str, tuple[str, ...]], ...]


def build_match_observed_game_reconstruction_v1(
    observed_game: ObservedGameRecordV1,
    *,
    validated_trace: ObservedGameTraceSummaryV1 | None = None,
) -> MatchObservedGameReconstructionV1:
    """Validates one trace once and retains exact playable-hand evidence."""
    if type(observed_game) is not ObservedGameRecordV1:
        raise ValueError("observed_game must be an ObservedGameRecordV1.")
    perspective_hand = build_observed_perspective_playable_hand_v1(
        perspective_player_id=observed_game.perspective_player_id,
        perspective_initial_hand=observed_game.perspective_initial_hand,
        declarer_player_id=observed_game.declarer_player_id,
        declaration=observed_game.declaration,
        original_skat=observed_game.original_skat,
        discarded_cards=observed_game.discarded_cards,
    )
    trace = validated_trace
    if trace is None:
        trace = validate_observed_game_trace_v1(
            plays=observed_game.plays,
            seat_order_player_ids=tuple(player.player_id for player in observed_game.players),
            perspective_player_id=observed_game.perspective_player_id,
            perspective_initial_hand=observed_game.perspective_initial_hand,
            perspective_playable_hand=perspective_hand,
            declarer_player_id=observed_game.declarer_player_id,
            declaration=observed_game.declaration,
            original_skat=observed_game.original_skat,
            discarded_cards=observed_game.discarded_cards,
            game_timecode=observed_game.game_timecode,
        )
    if trace.playable_hands is not None:
        playable_hands = trace.playable_hands
    elif perspective_hand is not None:
        playable_hands = ((observed_game.perspective_player_id, perspective_hand),)
    else:
        playable_hands = ()
    return MatchObservedGameReconstructionV1(
        observed_game=observed_game,
        trace=trace,
        evidence_summary=build_observed_game_evidence_summary_from_trace_v1(
            observed_game,
            trace,
        ),
        playable_hands=playable_hands,
    )
