from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.rules import GAME_TYPES, get_card_points, get_effective_suit, is_trump

TACTICAL_DECISION_FACTS_VERSION = 1
TACTICAL_MOTIF_OCCURRENCE_VERSION = 1
TACTICAL_DECISION_OBSERVATION_VERSION = 1
HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION = 1
MATCH_HISTORICAL_TACTICAL_MOTIF_INTEGRATION_VERSION = 1

HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD = "historical_tactical_motif_review_v1"

TACTICAL_MOTIF_SOURCE_POLICY = (
    "retained_historical_decision_snapshots_without_replay_rerun"
)
TACTICAL_MOTIF_INFORMATION_POLICY = (
    "decision_time_facts_then_actual_play_then_optional_trick_outcome"
)
TACTICAL_MOTIF_DETECTION_POLICY = "exact_rule_derived_structural_observations"
TACTICAL_MOTIF_INTERPRETATION_POLICY = (
    "descriptive_presence_without_quality_intent_signal_or_causality"
)
TACTICAL_MOTIF_PARTNERSHIP_POLICY = (
    "defender_partner_facts_without_communication_inference"
)
TACTICAL_MOTIF_COMMENTARY_POLICY = (
    "human_commentary_and_response_links_remain_separate"
)
TACTICAL_MOTIF_PUBLIC_POLICY = (
    "safe_facts_and_motif_types_without_private_hand_or_alternative_cards"
)
TACTICAL_MOTIF_REUSE_POLICY = (
    "one_snapshot_sequence_shared_across_requested_historical_attachments"
)
TACTICAL_MOTIF_CROSS_GAME_POLICY = (
    "reusable_single_game_evidence_without_cross_game_aggregation"
)

TACTICAL_MOTIF_FAMILIES = (
    "lead_structure",
    "void_response",
    "trick_control",
    "defender_partnership",
    "hand_shape",
    "trick_outcome",
)

TACTICAL_MOTIF_TYPES = (
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

TACTICAL_MOTIF_FAMILY_BY_TYPE = {
    "trump_lead": "lead_structure",
    "non_trump_lead": "lead_structure",
    "new_effective_category_lead": "lead_structure",
    "repeat_effective_category_lead": "lead_structure",
    "void_trump_play": "void_response",
    "void_non_trump_discard": "void_response",
    "available_trump_not_used": "void_response",
    "opposing_side_overtake": "trick_control",
    "current_trick_win_available_not_taken": "trick_control",
    "lowest_cost_current_winner": "trick_control",
    "partner_effective_category_return": "defender_partnership",
    "partner_overtake": "defender_partnership",
    "partner_safe_point_load": "defender_partnership",
    "point_card_captured_by_partner": "defender_partnership",
    "effective_category_exhausted": "hand_shape",
    "point_card_lost_to_opposing_side": "trick_outcome",
}

TACTICAL_MOTIF_EVIDENCE_TIMES = (
    "after_actual_play",
    "after_trick_completion",
)
TACTICAL_DECISION_OBSERVATION_STATUSES = ("complete", "partial")
TACTICAL_MOTIF_REVIEW_LIMITATIONS = (
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

_AFTER_TRICK_COMPLETION_MOTIFS = {
    "point_card_captured_by_partner",
    "point_card_lost_to_opposing_side",
}
_EFFECTIVE_CATEGORIES = ("TRUMP", "C", "S", "H", "D")
_ACTING_SEATS = ("forehand", "middlehand", "rearhand")
_SIDES = ("declarer", "defenders")
_SCOPES = ("player", "role", "phase", "contract")


def _require_version(value: int, expected: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"{field_name} must equal version {expected}.")


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")


def _require_non_negative_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")


def _require_positive_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


def _validate_canonical_counts(
    counts: tuple[tuple[str, int], ...],
    canonical_values: tuple[str, ...],
    field_name: str,
) -> None:
    if not isinstance(counts, tuple) or tuple(value for value, _ in counts) != canonical_values:
        raise ValueError(f"{field_name} must follow the canonical value order.")
    for _, count in counts:
        _require_non_negative_integer(count, field_name)


@dataclass(frozen=True, slots=True, kw_only=True)
class TacticalDecisionFactsV1:
    """Safe structural facts derived before one actual historical play."""

    tactical_decision_facts_version: int
    source_game_id: str
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: str
    acting_side: str
    partner_player_id: str | None
    game_type: str
    information_cutoff: str
    required_effective_category: str | None
    can_follow_required_effective_category: bool | None
    legal_card_count: int
    legal_trump_count: int
    legal_current_winning_card_count: int
    legal_partner_safe_card_count: int
    pre_play_current_winner_player_id: str | None
    pre_play_current_winner_side: str | None
    partner_currently_winning_before: bool
    previous_lead_effective_categories: tuple[str, ...]
    partner_last_lead_effective_category: str | None

    def __post_init__(self) -> None:
        _require_version(
            self.tactical_decision_facts_version,
            TACTICAL_DECISION_FACTS_VERSION,
            "tactical_decision_facts_version",
        )
        for field_name in ("source_game_id", "acting_player_id"):
            _require_identifier(getattr(self, field_name), field_name)
        for field_name in ("decision_index", "trick_number", "play_index"):
            _require_positive_integer(getattr(self, field_name), field_name)
        if self.play_index not in (1, 2, 3):
            raise ValueError("play_index must be 1, 2, or 3.")
        if self.decision_index != (self.trick_number - 1) * 3 + self.play_index:
            raise ValueError("decision_index must match trick_number and play_index.")
        if self.decision_index > 30 or self.trick_number > 10:
            raise ValueError("Decision Facts must stay within one 10-Trick Game.")
        if self.acting_seat not in _ACTING_SEATS:
            raise ValueError("acting_seat is invalid.")
        if self.acting_side not in _SIDES:
            raise ValueError("acting_side is invalid.")
        if self.partner_player_id is not None:
            _require_identifier(self.partner_player_id, "partner_player_id")
        if (self.acting_side == "declarer") != (self.partner_player_id is None):
            raise ValueError("Only Defenders have a partner_player_id.")
        if self.game_type not in GAME_TYPES:
            raise ValueError("game_type is invalid.")
        if self.information_cutoff != "before_actual_play":
            raise ValueError("information_cutoff must be before_actual_play.")
        if self.required_effective_category not in (None, *_EFFECTIVE_CATEGORIES):
            raise ValueError("required_effective_category is invalid.")
        if self.play_index == 1:
            if (
                self.required_effective_category is not None
                or self.can_follow_required_effective_category is not None
                or self.pre_play_current_winner_player_id is not None
                or self.pre_play_current_winner_side is not None
            ):
                raise ValueError("Lead facts cannot contain response-only values.")
        else:
            if self.required_effective_category is None or not isinstance(
                self.can_follow_required_effective_category, bool
            ):
                raise ValueError("Response facts require a category and follow status.")
            if self.pre_play_current_winner_player_id is None:
                raise ValueError("Response facts require a pre-play current winner.")
            _require_identifier(
                self.pre_play_current_winner_player_id,
                "pre_play_current_winner_player_id",
            )
            if self.pre_play_current_winner_side not in _SIDES:
                raise ValueError("pre_play_current_winner_side is invalid.")
        for field_name in (
            "legal_card_count",
            "legal_trump_count",
            "legal_current_winning_card_count",
            "legal_partner_safe_card_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.legal_card_count <= 0:
            raise ValueError("legal_card_count must be positive.")
        if self.legal_card_count > 10:
            raise ValueError("legal_card_count cannot exceed 10.")
        if any(
            value > self.legal_card_count
            for value in (
                self.legal_trump_count,
                self.legal_current_winning_card_count,
                self.legal_partner_safe_card_count,
            )
        ):
            raise ValueError("Legal subset counts cannot exceed legal_card_count.")
        if not isinstance(self.partner_currently_winning_before, bool):
            raise ValueError("partner_currently_winning_before must be a boolean.")
        if self.partner_currently_winning_before != (
            self.partner_player_id is not None
            and self.partner_player_id == self.pre_play_current_winner_player_id
        ):
            raise ValueError("partner_currently_winning_before does not reconcile.")
        if not isinstance(self.previous_lead_effective_categories, tuple) or any(
            value not in _EFFECTIVE_CATEGORIES
            for value in self.previous_lead_effective_categories
        ):
            raise ValueError("previous_lead_effective_categories are invalid.")
        if len(self.previous_lead_effective_categories) > min(9, self.trick_number - 1):
            raise ValueError("previous_lead_effective_categories contain future Tricks.")
        if self.partner_last_lead_effective_category not in (
            None,
            *_EFFECTIVE_CATEGORIES,
        ):
            raise ValueError("partner_last_lead_effective_category is invalid.")
        if self.acting_side == "declarer" and self.partner_last_lead_effective_category is not None:
            raise ValueError("Declarer facts cannot contain a partner lead category.")
        object.__setattr__(
            self,
            "previous_lead_effective_categories",
            tuple(self.previous_lead_effective_categories),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TacticalMotifOccurrenceV1:
    """One exact structural motif attached at its evidence time."""

    tactical_motif_occurrence_version: int
    motif_type: str
    motif_family: str
    evidence_time: str

    def __post_init__(self) -> None:
        _require_version(
            self.tactical_motif_occurrence_version,
            TACTICAL_MOTIF_OCCURRENCE_VERSION,
            "tactical_motif_occurrence_version",
        )
        if self.motif_type not in TACTICAL_MOTIF_TYPES:
            raise ValueError("motif_type is invalid.")
        if self.motif_family != TACTICAL_MOTIF_FAMILY_BY_TYPE[self.motif_type]:
            raise ValueError("motif_family does not match motif_type.")
        expected_time = (
            "after_trick_completion"
            if self.motif_type in _AFTER_TRICK_COMPLETION_MOTIFS
            else "after_actual_play"
        )
        if self.evidence_time != expected_time:
            raise ValueError("evidence_time does not match motif_type.")


@dataclass(frozen=True, slots=True, kw_only=True)
class TacticalDecisionObservationV1:
    """One actual play attached to safe decision-time and optional outcome facts."""

    tactical_decision_observation_version: int
    decision_time_facts: TacticalDecisionFactsV1
    actual_card: str
    actual_effective_category: str
    actual_is_trump: bool
    actual_card_points: int
    post_play_current_winner_player_id: str
    post_play_current_winner_side: str
    actual_is_current_winner: bool
    actual_keeps_partner_winning: bool
    actual_overtakes_partner: bool
    actual_is_lowest_cost_current_winner: bool
    remaining_actual_effective_category_count: int
    completed_trick_winner_player_id: str | None
    completed_trick_winner_side: str | None
    completed_trick_points: int | None
    observation_status: str
    motifs: tuple[TacticalMotifOccurrenceV1, ...]

    def __post_init__(self) -> None:
        _require_version(
            self.tactical_decision_observation_version,
            TACTICAL_DECISION_OBSERVATION_VERSION,
            "tactical_decision_observation_version",
        )
        if not isinstance(self.decision_time_facts, TacticalDecisionFactsV1):
            raise ValueError("decision_time_facts must be TacticalDecisionFactsV1.")
        if self.actual_card not in get_full_deck():
            raise ValueError("actual_card is invalid.")
        if self.actual_effective_category not in _EFFECTIVE_CATEGORIES:
            raise ValueError("actual_effective_category is invalid.")
        if self.actual_effective_category != get_effective_suit(
            self.actual_card,
            self.decision_time_facts.game_type,
        ):
            raise ValueError("actual_effective_category does not match actual_card.")
        for field_name in (
            "actual_is_trump",
            "actual_is_current_winner",
            "actual_keeps_partner_winning",
            "actual_overtakes_partner",
            "actual_is_lowest_cost_current_winner",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean.")
        if self.actual_is_trump != is_trump(
            self.actual_card,
            self.decision_time_facts.game_type,
        ):
            raise ValueError("actual_is_trump does not match actual_card.")
        for field_name in (
            "actual_card_points",
            "remaining_actual_effective_category_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.actual_card_points != get_card_points(self.actual_card):
            raise ValueError("actual_card_points does not match actual_card.")
        if self.remaining_actual_effective_category_count > 9:
            raise ValueError("remaining_actual_effective_category_count cannot exceed 9.")
        _require_identifier(
            self.post_play_current_winner_player_id,
            "post_play_current_winner_player_id",
        )
        if self.post_play_current_winner_side not in _SIDES:
            raise ValueError("post_play_current_winner_side is invalid.")
        if self.observation_status not in TACTICAL_DECISION_OBSERVATION_STATUSES:
            raise ValueError("observation_status is invalid.")
        completed_values = (
            self.completed_trick_winner_player_id,
            self.completed_trick_winner_side,
            self.completed_trick_points,
        )
        if self.observation_status == "complete":
            if any(value is None for value in completed_values):
                raise ValueError("Complete observations require completed-Trick facts.")
            _require_identifier(
                self.completed_trick_winner_player_id,
                "completed_trick_winner_player_id",
            )
            if self.completed_trick_winner_side not in _SIDES:
                raise ValueError("completed_trick_winner_side is invalid.")
            _require_non_negative_integer(self.completed_trick_points, "completed_trick_points")
            if self.completed_trick_points > 33:
                raise ValueError("completed_trick_points cannot exceed 33.")
        elif any(value is not None for value in completed_values):
            raise ValueError("Partial observations cannot contain completed-Trick facts.")
        if not isinstance(self.motifs, tuple):
            raise TypeError("motifs must be a tuple.")
        if len(self.motifs) > len(TACTICAL_MOTIF_TYPES):
            raise ValueError("motifs cannot exceed the canonical taxonomy.")
        motif_types = tuple(motif.motif_type for motif in self.motifs)
        if len(motif_types) != len(set(motif_types)):
            raise ValueError("A motif type may occur at most once per Decision.")
        if motif_types != tuple(
            motif_type for motif_type in TACTICAL_MOTIF_TYPES if motif_type in motif_types
        ):
            raise ValueError("motifs must follow canonical motif order.")
        if self.observation_status == "partial" and any(
            motif.evidence_time == "after_trick_completion" for motif in self.motifs
        ):
            raise ValueError("Partial observations cannot contain completed-Trick motifs.")
        object.__setattr__(self, "motifs", tuple(self.motifs))


@dataclass(frozen=True, slots=True, kw_only=True)
class TacticalMotifScopeSummaryV1:
    """One descriptive motif-count summary for a complete canonical scope."""

    scope: str
    scope_value: str
    observation_count: int
    complete_observation_count: int
    partial_observation_count: int
    motif_occurrence_count: int
    decision_indices: tuple[int, ...]
    motif_counts: tuple[tuple[str, int], ...]
    family_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if self.scope not in _SCOPES:
            raise ValueError("scope is invalid.")
        _require_identifier(self.scope_value, "scope_value")
        for field_name in (
            "observation_count",
            "complete_observation_count",
            "partial_observation_count",
            "motif_occurrence_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.complete_observation_count + self.partial_observation_count != (
            self.observation_count
        ):
            raise ValueError("Scope observation status counts do not reconcile.")
        if (
            not isinstance(self.decision_indices, tuple)
            or self.decision_indices != tuple(sorted(set(self.decision_indices)))
            or len(self.decision_indices) != self.observation_count
        ):
            raise ValueError("decision_indices must be unique and chronological.")
        _validate_canonical_counts(self.motif_counts, TACTICAL_MOTIF_TYPES, "motif_counts")
        _validate_canonical_counts(self.family_counts, TACTICAL_MOTIF_FAMILIES, "family_counts")
        if sum(count for _, count in self.motif_counts) != self.motif_occurrence_count:
            raise ValueError("Scope motif counts do not reconcile.")
        if sum(count for _, count in self.family_counts) != self.motif_occurrence_count:
            raise ValueError("Scope family counts do not reconcile.")
        object.__setattr__(self, "decision_indices", tuple(self.decision_indices))
        object.__setattr__(self, "motif_counts", tuple(self.motif_counts))
        object.__setattr__(self, "family_counts", tuple(self.family_counts))


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalTacticalMotifReviewV1:
    """One complete structural tactical-motif report for a recorded game."""

    historical_tactical_motif_review_version: int
    review_method: str
    information_policy: str
    source_game_id: str
    observation_count: int
    complete_observation_count: int
    partial_observation_count: int
    motif_occurrence_count: int
    observations: tuple[TacticalDecisionObservationV1, ...]
    motif_counts: tuple[tuple[str, int], ...]
    family_counts: tuple[tuple[str, int], ...]
    player_summaries: tuple[TacticalMotifScopeSummaryV1, ...]
    role_summaries: tuple[TacticalMotifScopeSummaryV1, ...]
    phase_summaries: tuple[TacticalMotifScopeSummaryV1, ...]
    contract_summaries: tuple[TacticalMotifScopeSummaryV1, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_version(
            self.historical_tactical_motif_review_version,
            HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION,
            "historical_tactical_motif_review_version",
        )
        if self.review_method != HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD:
            raise ValueError("review_method is invalid.")
        if self.information_policy != TACTICAL_MOTIF_INFORMATION_POLICY:
            raise ValueError("information_policy is invalid.")
        _require_identifier(self.source_game_id, "source_game_id")
        for field_name in (
            "observation_count",
            "complete_observation_count",
            "partial_observation_count",
            "motif_occurrence_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if not isinstance(self.observations, tuple) or len(self.observations) != (
            self.observation_count
        ):
            raise ValueError("observations must match observation_count.")
        if tuple(
            observation.decision_time_facts.decision_index
            for observation in self.observations
        ) != tuple(range(1, self.observation_count + 1)):
            raise ValueError("observations must preserve complete source order.")
        if any(
            observation.decision_time_facts.source_game_id != self.source_game_id
            for observation in self.observations
        ):
            raise ValueError("observations must match source_game_id.")
        if self.complete_observation_count != sum(
            observation.observation_status == "complete"
            for observation in self.observations
        ) or self.partial_observation_count != sum(
            observation.observation_status == "partial"
            for observation in self.observations
        ):
            raise ValueError("Observation status counts do not reconcile.")
        _validate_canonical_counts(self.motif_counts, TACTICAL_MOTIF_TYPES, "motif_counts")
        _validate_canonical_counts(self.family_counts, TACTICAL_MOTIF_FAMILIES, "family_counts")
        if self.motif_occurrence_count != sum(
            len(observation.motifs) for observation in self.observations
        ):
            raise ValueError("motif_occurrence_count does not reconcile.")
        if sum(count for _, count in self.motif_counts) != self.motif_occurrence_count:
            raise ValueError("motif_counts do not reconcile.")
        if sum(count for _, count in self.family_counts) != self.motif_occurrence_count:
            raise ValueError("family_counts do not reconcile.")
        expected_groups = (
            ("player", self.player_summaries, 3),
            ("role", self.role_summaries, 2),
            ("phase", self.phase_summaries, 3),
            ("contract", self.contract_summaries, 1),
        )
        for scope, summaries, count in expected_groups:
            if (
                not isinstance(summaries, tuple)
                or len(summaries) != count
                or any(summary.scope != scope for summary in summaries)
                or sum(summary.observation_count for summary in summaries)
                != self.observation_count
                or sum(summary.motif_occurrence_count for summary in summaries)
                != self.motif_occurrence_count
            ):
                raise ValueError(f"{scope} summaries do not reconcile.")
        if self.limitations != TACTICAL_MOTIF_REVIEW_LIMITATIONS:
            raise ValueError("limitations are invalid.")
        for field_name in (
            "observations",
            "motif_counts",
            "family_counts",
            "player_summaries",
            "role_summaries",
            "phase_summaries",
            "contract_summaries",
            "limitations",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))


def build_serializable_tactical_decision_facts_v1(
    facts: TacticalDecisionFactsV1,
) -> dict[str, Any]:
    return {
        "tactical_decision_facts_version": facts.tactical_decision_facts_version,
        "source_game_id": facts.source_game_id,
        "decision_index": facts.decision_index,
        "trick_number": facts.trick_number,
        "play_index": facts.play_index,
        "acting_player_id": facts.acting_player_id,
        "acting_seat": facts.acting_seat,
        "acting_side": facts.acting_side,
        "partner_player_id": facts.partner_player_id,
        "game_type": facts.game_type,
        "information_cutoff": facts.information_cutoff,
        "required_effective_category": facts.required_effective_category,
        "can_follow_required_effective_category": (
            facts.can_follow_required_effective_category
        ),
        "legal_card_count": facts.legal_card_count,
        "legal_trump_count": facts.legal_trump_count,
        "legal_current_winning_card_count": facts.legal_current_winning_card_count,
        "legal_partner_safe_card_count": facts.legal_partner_safe_card_count,
        "pre_play_current_winner_player_id": facts.pre_play_current_winner_player_id,
        "pre_play_current_winner_side": facts.pre_play_current_winner_side,
        "partner_currently_winning_before": facts.partner_currently_winning_before,
        "previous_lead_effective_categories": list(
            facts.previous_lead_effective_categories
        ),
        "partner_last_lead_effective_category": (
            facts.partner_last_lead_effective_category
        ),
    }


def build_serializable_tactical_motif_occurrence_v1(
    occurrence: TacticalMotifOccurrenceV1,
) -> dict[str, Any]:
    return {
        "tactical_motif_occurrence_version": occurrence.tactical_motif_occurrence_version,
        "motif_type": occurrence.motif_type,
        "motif_family": occurrence.motif_family,
        "evidence_time": occurrence.evidence_time,
    }


def build_serializable_tactical_decision_observation_v1(
    observation: TacticalDecisionObservationV1,
) -> dict[str, Any]:
    return {
        "tactical_decision_observation_version": (
            observation.tactical_decision_observation_version
        ),
        "decision_time_facts": build_serializable_tactical_decision_facts_v1(
            observation.decision_time_facts
        ),
        "actual_card": observation.actual_card,
        "actual_effective_category": observation.actual_effective_category,
        "actual_is_trump": observation.actual_is_trump,
        "actual_card_points": observation.actual_card_points,
        "post_play_current_winner_player_id": (
            observation.post_play_current_winner_player_id
        ),
        "post_play_current_winner_side": observation.post_play_current_winner_side,
        "actual_is_current_winner": observation.actual_is_current_winner,
        "actual_keeps_partner_winning": observation.actual_keeps_partner_winning,
        "actual_overtakes_partner": observation.actual_overtakes_partner,
        "actual_is_lowest_cost_current_winner": (
            observation.actual_is_lowest_cost_current_winner
        ),
        "remaining_actual_effective_category_count": (
            observation.remaining_actual_effective_category_count
        ),
        "completed_trick_winner_player_id": (
            observation.completed_trick_winner_player_id
        ),
        "completed_trick_winner_side": observation.completed_trick_winner_side,
        "completed_trick_points": observation.completed_trick_points,
        "observation_status": observation.observation_status,
        "motifs": [
            build_serializable_tactical_motif_occurrence_v1(motif)
            for motif in observation.motifs
        ],
    }


def build_serializable_tactical_motif_scope_summary_v1(
    summary: TacticalMotifScopeSummaryV1,
) -> dict[str, Any]:
    return {
        "scope": summary.scope,
        "scope_value": summary.scope_value,
        "observation_count": summary.observation_count,
        "complete_observation_count": summary.complete_observation_count,
        "partial_observation_count": summary.partial_observation_count,
        "motif_occurrence_count": summary.motif_occurrence_count,
        "decision_indices": list(summary.decision_indices),
        "motif_counts": [
            {"motif_type": motif_type, "count": count}
            for motif_type, count in summary.motif_counts
        ],
        "family_counts": [
            {"motif_family": family, "count": count}
            for family, count in summary.family_counts
        ],
    }


def build_serializable_historical_tactical_motif_review_v1(
    review: HistoricalTacticalMotifReviewV1,
) -> dict[str, Any]:
    return {
        "historical_tactical_motif_review_version": (
            review.historical_tactical_motif_review_version
        ),
        "review_method": review.review_method,
        "information_policy": review.information_policy,
        "source_game_id": review.source_game_id,
        "observation_count": review.observation_count,
        "complete_observation_count": review.complete_observation_count,
        "partial_observation_count": review.partial_observation_count,
        "motif_occurrence_count": review.motif_occurrence_count,
        "observations": [
            build_serializable_tactical_decision_observation_v1(observation)
            for observation in review.observations
        ],
        "motif_counts": [
            {"motif_type": motif_type, "count": count}
            for motif_type, count in review.motif_counts
        ],
        "family_counts": [
            {"motif_family": family, "count": count}
            for family, count in review.family_counts
        ],
        "player_summaries": [
            build_serializable_tactical_motif_scope_summary_v1(summary)
            for summary in review.player_summaries
        ],
        "role_summaries": [
            build_serializable_tactical_motif_scope_summary_v1(summary)
            for summary in review.role_summaries
        ],
        "phase_summaries": [
            build_serializable_tactical_motif_scope_summary_v1(summary)
            for summary in review.phase_summaries
        ],
        "contract_summaries": [
            build_serializable_tactical_motif_scope_summary_v1(summary)
            for summary in review.contract_summaries
        ],
        "limitations": list(review.limitations),
    }
