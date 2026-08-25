from dataclasses import replace

import pytest

from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    HistoricalSnapshotDeclaration,
    HistoricalSnapshotPlay,
    HistoricalSnapshotVisibleState,
)
from skat_ai.tactical_motif_detection import (
    build_tactical_decision_facts_v1,
    build_tactical_decision_observation_from_snapshot_v1,
    build_tactical_decision_observation_v1,
)


def _snapshot(
    *,
    actual_card: str = "C10",
    own_hand: tuple[str, ...] = ("C10", "HJ", "H7"),
    current_trick: tuple[HistoricalSnapshotPlay, ...] = (
        HistoricalSnapshotPlay(player_id="player-c", card="CA"),
    ),
    game_type: str = "grand",
) -> HistoricalDecisionSnapshot:
    return HistoricalDecisionSnapshot(
        source_game_id="game-1",
        source_played_at=None,
        decision_index=2,
        trick_number=1,
        play_index=2,
        acting_player_id="player-b",
        acting_seat="middlehand",
        acting_side="defenders",
        actual_card_played=actual_card,
        information_cutoff="before_actual_play",
        relative_player_map={
            "me": "player-b",
            "left": "player-c",
            "right": "player-a",
        },
        visible_state=HistoricalSnapshotVisibleState(
            game_type=game_type,
            declaration=HistoricalSnapshotDeclaration(
                hand_game=False,
                ouvert=False,
                schneider_announced=False,
                schwarz_announced=False,
                matadors=1 if game_type != "null" else None,
                bid_value=18,
            ),
            own_hand=own_hand,
            legal_cards=("C10",) if "C10" in own_hand else own_hand,
            skat_visibility="unknown",
            known_skat_cards=(),
            public_exposed_cards=(),
            completed_tricks=(),
            current_trick=current_trick,
            declarer_trick_points=0,
            defender_trick_points=0,
            opponent_hand_sizes=(),
        ),
    )


def test_decision_facts_do_not_depend_on_actual_card() -> None:
    snapshot = _snapshot()
    changed = replace(snapshot, actual_card_played="HJ")

    first = build_tactical_decision_facts_v1(
        snapshot=snapshot,
        declarer_player_id="player-a",
        participant_player_ids=("player-a", "player-b", "player-c"),
    )
    second = build_tactical_decision_facts_v1(
        snapshot=changed,
        declarer_player_id="player-a",
        participant_player_ids=("player-a", "player-b", "player-c"),
    )

    assert first == second
    assert first.partner_player_id == "player-c"
    assert first.required_effective_category == "C"
    assert first.can_follow_required_effective_category is True
    assert first.legal_card_count == 1
    assert first.legal_trump_count == 0
    assert first.legal_current_winning_card_count == 0
    assert first.legal_partner_safe_card_count == 1
    assert first.pre_play_current_winner_player_id == "player-c"
    assert first.partner_currently_winning_before is True
    assert not hasattr(first, "actual_card")


def test_actual_play_attachment_detects_partner_and_completion_motifs() -> None:
    snapshot = _snapshot()
    facts = build_tactical_decision_facts_v1(
        snapshot=snapshot,
        declarer_player_id="player-a",
        participant_player_ids=("player-a", "player-b", "player-c"),
    )
    observation = build_tactical_decision_observation_v1(
        decision_time_facts=facts,
        snapshot=snapshot,
        actual_card="C10",
        declarer_player_id="player-a",
        completed_trick_winner_player_id="player-c",
        completed_trick_winner_side="defenders",
        completed_trick_points=25,
    )

    assert observation.actual_keeps_partner_winning is True
    assert observation.completed_trick_winner_player_id == "player-c"
    assert observation.observation_status == "complete"
    assert [motif.motif_type for motif in observation.motifs] == [
        "partner_safe_point_load",
        "point_card_captured_by_partner",
        "effective_category_exhausted",
    ]
    assert observation.motifs[1].evidence_time == "after_trick_completion"


def test_void_trump_and_partner_overtake_are_structural() -> None:
    snapshot = _snapshot(actual_card="HJ", own_hand=("HJ", "H7"))
    facts = build_tactical_decision_facts_v1(
        snapshot=snapshot,
        declarer_player_id="player-a",
        participant_player_ids=("player-a", "player-b", "player-c"),
    )
    observation = build_tactical_decision_observation_v1(
        decision_time_facts=facts,
        snapshot=snapshot,
        actual_card="HJ",
        declarer_player_id="player-a",
    )

    assert facts.can_follow_required_effective_category is False
    assert observation.observation_status == "partial"
    assert observation.actual_overtakes_partner is True
    assert [motif.motif_type for motif in observation.motifs] == [
        "void_trump_play",
        "lowest_cost_current_winner",
        "partner_overtake",
        "effective_category_exhausted",
    ]


def test_illegal_actual_card_is_rejected() -> None:
    snapshot = _snapshot()
    facts = build_tactical_decision_facts_v1(
        snapshot=snapshot,
        declarer_player_id="player-a",
        participant_player_ids=("player-a", "player-b", "player-c"),
    )

    with pytest.raises(ValueError, match="legal"):
        build_tactical_decision_observation_v1(
            decision_time_facts=facts,
            snapshot=snapshot,
            actual_card="HJ",
            declarer_player_id="player-a",
        )


def test_shared_snapshot_seam_preserves_exact_observation() -> None:
    snapshot = _snapshot()
    facts = build_tactical_decision_facts_v1(
        snapshot=snapshot,
        declarer_player_id="player-a",
        participant_player_ids=("player-a", "player-b", "player-c"),
    )
    expected = build_tactical_decision_observation_v1(
        decision_time_facts=facts,
        snapshot=snapshot,
        actual_card=snapshot.actual_card_played,
        declarer_player_id="player-a",
    )

    assert build_tactical_decision_observation_from_snapshot_v1(
        snapshot=snapshot,
        declarer_player_id="player-a",
        participant_player_ids=("player-a", "player-b", "player-c"),
    ) == expected
