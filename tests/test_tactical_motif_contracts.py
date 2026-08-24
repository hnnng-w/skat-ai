from dataclasses import FrozenInstanceError

import pytest

from skat_ai.tactical_motif_contracts import (
    HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD,
    HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION,
    MATCH_HISTORICAL_TACTICAL_MOTIF_INTEGRATION_VERSION,
    TACTICAL_DECISION_FACTS_VERSION,
    TACTICAL_DECISION_OBSERVATION_STATUSES,
    TACTICAL_DECISION_OBSERVATION_VERSION,
    TACTICAL_MOTIF_COMMENTARY_POLICY,
    TACTICAL_MOTIF_CROSS_GAME_POLICY,
    TACTICAL_MOTIF_DETECTION_POLICY,
    TACTICAL_MOTIF_EVIDENCE_TIMES,
    TACTICAL_MOTIF_FAMILIES,
    TACTICAL_MOTIF_INFORMATION_POLICY,
    TACTICAL_MOTIF_INTERPRETATION_POLICY,
    TACTICAL_MOTIF_OCCURRENCE_VERSION,
    TACTICAL_MOTIF_PARTNERSHIP_POLICY,
    TACTICAL_MOTIF_PUBLIC_POLICY,
    TACTICAL_MOTIF_REUSE_POLICY,
    TACTICAL_MOTIF_REVIEW_LIMITATIONS,
    TACTICAL_MOTIF_SOURCE_POLICY,
    TACTICAL_MOTIF_TYPES,
    TacticalMotifOccurrenceV1,
)


def test_tactical_motif_contract_vocabularies_are_exact() -> None:
    assert (
        TACTICAL_DECISION_FACTS_VERSION,
        TACTICAL_MOTIF_OCCURRENCE_VERSION,
        TACTICAL_DECISION_OBSERVATION_VERSION,
        HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION,
        MATCH_HISTORICAL_TACTICAL_MOTIF_INTEGRATION_VERSION,
    ) == (1, 1, 1, 1, 1)
    assert HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD == (
        "historical_tactical_motif_review_v1"
    )
    assert (
        TACTICAL_MOTIF_SOURCE_POLICY,
        TACTICAL_MOTIF_INFORMATION_POLICY,
        TACTICAL_MOTIF_DETECTION_POLICY,
        TACTICAL_MOTIF_INTERPRETATION_POLICY,
        TACTICAL_MOTIF_PARTNERSHIP_POLICY,
        TACTICAL_MOTIF_COMMENTARY_POLICY,
        TACTICAL_MOTIF_PUBLIC_POLICY,
        TACTICAL_MOTIF_REUSE_POLICY,
        TACTICAL_MOTIF_CROSS_GAME_POLICY,
    ) == (
        "retained_historical_decision_snapshots_without_replay_rerun",
        "decision_time_facts_then_actual_play_then_optional_trick_outcome",
        "exact_rule_derived_structural_observations",
        "descriptive_presence_without_quality_intent_signal_or_causality",
        "defender_partner_facts_without_communication_inference",
        "human_commentary_and_response_links_remain_separate",
        "safe_facts_and_motif_types_without_private_hand_or_alternative_cards",
        "one_snapshot_sequence_shared_across_requested_historical_attachments",
        "reusable_single_game_evidence_without_cross_game_aggregation",
    )
    assert TACTICAL_MOTIF_FAMILIES == (
        "lead_structure",
        "void_response",
        "trick_control",
        "defender_partnership",
        "hand_shape",
        "trick_outcome",
    )
    assert TACTICAL_MOTIF_TYPES == (
        "trump_lead",
        "non_trump_lead",
        "new_effective_category_lead",
        "repeat_effective_category_lead",
        "void_trump_play",
        "void_non_trump_discard",
        "available_trump_not_used",
        "opposing_side_overtake",
        "current_trick_win_available_not_taken",
        "lowest_cost_current_winner",
        "partner_effective_category_return",
        "partner_overtake",
        "partner_safe_point_load",
        "point_card_captured_by_partner",
        "effective_category_exhausted",
        "point_card_lost_to_opposing_side",
    )
    assert TACTICAL_MOTIF_EVIDENCE_TIMES == (
        "after_actual_play",
        "after_trick_completion",
    )
    assert TACTICAL_DECISION_OBSERVATION_STATUSES == ("complete", "partial")
    assert TACTICAL_MOTIF_REVIEW_LIMITATIONS == (
        "single_recorded_game_only",
        "structural_observation_not_quality_assessment",
        "actual_card_not_ground_truth",
        "no_intent_or_signaling_claim",
        "no_communication_success_claim",
        "no_causal_outcome_claim",
        "no_hidden_ownership_inference",
        "no_search_or_optimality_claim",
        "no_commentary_interpretation",
        "no_cross_game_player_trait",
    )


def test_motif_occurrence_is_strict_immutable_and_reconciled() -> None:
    occurrence = TacticalMotifOccurrenceV1(
        tactical_motif_occurrence_version=1,
        motif_type="partner_safe_point_load",
        motif_family="defender_partnership",
        evidence_time="after_actual_play",
    )

    with pytest.raises(FrozenInstanceError):
        occurrence.motif_type = "partner_overtake"  # type: ignore[misc]
    with pytest.raises(ValueError, match="version"):
        TacticalMotifOccurrenceV1(
            tactical_motif_occurrence_version=True,
            motif_type="partner_safe_point_load",
            motif_family="defender_partnership",
            evidence_time="after_actual_play",
        )
    with pytest.raises(ValueError, match="family"):
        TacticalMotifOccurrenceV1(
            tactical_motif_occurrence_version=1,
            motif_type="partner_safe_point_load",
            motif_family="trick_control",
            evidence_time="after_actual_play",
        )
    with pytest.raises(ValueError, match="evidence_time"):
        TacticalMotifOccurrenceV1(
            tactical_motif_occurrence_version=1,
            motif_type="point_card_captured_by_partner",
            motif_family="defender_partnership",
            evidence_time="after_actual_play",
        )
