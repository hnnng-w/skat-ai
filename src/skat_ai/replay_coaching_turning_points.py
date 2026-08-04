from dataclasses import dataclass
from typing import Any

from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_decision import determine_decision_state_before_game_end
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_value import build_game_value_summary
from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.historical_game_end import HISTORICAL_NORMAL_COMPLETION
from skat_ai.overbid import build_overbid_summary
from skat_ai.replay_coaching_assessment import ReplayCoachingDecisionAssessment
from skat_ai.replay_coaching_key_decisions import (
    REPLAY_COACHING_PRIORITIZATION_VERSION,
    REPLAY_COACHING_TURNING_POINT_TYPES,
)
from skat_ai.rules import get_trick_points, get_trick_winner

REPLAY_COACHING_RECORDED_STATES = (
    "undecided",
    "declarer_already_won",
    "defenders_already_won",
)
REPLAY_COACHING_TURNING_POINT_FACTORS = (
    "lower_contract_success_opportunity",
    "recorded_contract_became_decided",
    "recorded_declarer_became_decided",
    "recorded_defenders_became_decided",
    "forced_recorded_outcome_transition",
)
REPLAY_COACHING_TURNING_POINT_LIMITATIONS = (
    "counterfactual_aggregate_not_causal",
    "recorded_path_only",
    "decision_not_single_cause",
    "observed_card_not_ground_truth",
)


def _ordered_subset(values: tuple[str, ...], canonical: tuple[str, ...], name: str) -> None:
    if len(values) != len(set(values)) or any(value not in canonical for value in values):
        raise ValueError(f"{name} must contain unique supported values.")
    if values != tuple(value for value in canonical if value in values):
        raise ValueError(f"{name} must use deterministic canonical order.")


@dataclass(frozen=True)
class ReplayCoachingTurningPoint:
    """One counterfactual opportunity or recorded-path state transition."""

    prioritization_version: int
    turning_point_type: str
    decision_index: int
    assessment: ReplayCoachingDecisionAssessment
    is_high_impact: bool
    recorded_state_before: str | None
    recorded_state_after: str | None
    decided_side: str | None
    factors: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.prioritization_version, bool)
            or not isinstance(self.prioritization_version, int)
            or self.prioritization_version != REPLAY_COACHING_PRIORITIZATION_VERSION
        ):
            raise ValueError("Unsupported replay-coaching prioritization version.")
        if self.turning_point_type not in REPLAY_COACHING_TURNING_POINT_TYPES:
            raise ValueError("Unsupported Turning Point type.")
        if (
            isinstance(self.decision_index, bool)
            or not isinstance(self.decision_index, int)
            or self.decision_index <= 0
        ):
            raise ValueError("Turning Point decision_index must be positive.")
        if not isinstance(self.assessment, ReplayCoachingDecisionAssessment):
            raise ValueError("assessment must be ReplayCoachingDecisionAssessment.")
        if (
            self.decision_index
            != self.assessment.decision_time_evidence.decision_index
        ):
            raise ValueError("Turning Point decision_index must match its assessment.")
        if self.is_high_impact is not True:
            raise ValueError("Every Turning Point must be high impact.")
        if not isinstance(self.factors, tuple) or not isinstance(self.limitations, tuple):
            raise TypeError("Turning Point factors and limitations must be tuples.")
        _ordered_subset(self.factors, REPLAY_COACHING_TURNING_POINT_FACTORS, "factors")
        if self.turning_point_type == "decision_opportunity":
            if (
                self.assessment.assessment_status != "strictly_below_best"
                or self.assessment.impact_tier != "contract_success"
                or self.assessment.evidence_basis
                not in {
                    "all_compatible_worlds",
                    "sampled_compatible_worlds",
                    "completed_common_prefix",
                }
                or self.assessment.search_actual_card_comparison.contract_success_rate_gap
                is None
                or self.assessment.search_actual_card_comparison.contract_success_rate_gap
                <= 0
            ):
                raise ValueError(
                    "Decision-opportunity Turning Points require a positive Search "
                    "contract-success gap."
                )
            if (
                self.recorded_state_before is not None
                or self.recorded_state_after is not None
                or self.decided_side is not None
            ):
                raise ValueError("Decision opportunities do not contain recorded states.")
            if self.factors != ("lower_contract_success_opportunity",):
                raise ValueError("Decision-opportunity factors are inconsistent.")
            expected_limitations = (
                *self.assessment.limitations,
                "counterfactual_aggregate_not_causal",
            )
        else:
            if (
                self.recorded_state_before != "undecided"
                or self.recorded_state_after
                not in {"declarer_already_won", "defenders_already_won"}
            ):
                raise ValueError(
                    "Recorded-outcome Turning Points require an undecided-to-decided transition."
                )
            expected_decided_side = (
                "declarer"
                if self.recorded_state_after == "declarer_already_won"
                else "defenders"
            )
            if self.decided_side != expected_decided_side:
                raise ValueError("decided_side must match the recorded transition.")
            expected_factor_set = {
                "recorded_contract_became_decided",
                (
                    "recorded_declarer_became_decided"
                    if self.recorded_state_after == "declarer_already_won"
                    else "recorded_defenders_became_decided"
                ),
            }
            if self.assessment.assessment_status == "forced_move":
                expected_factor_set.add("forced_recorded_outcome_transition")
            expected_factors = tuple(
                factor
                for factor in REPLAY_COACHING_TURNING_POINT_FACTORS
                if factor in expected_factor_set
            )
            if self.factors != expected_factors:
                raise ValueError("Recorded-outcome factors are inconsistent.")
            expected_limitations = (
                "recorded_path_only",
                "decision_not_single_cause",
                "observed_card_not_ground_truth",
            )
        if self.limitations != expected_limitations:
            raise ValueError("Turning Point limitations are inconsistent.")


def validate_recorded_decision_state_timeline(states: tuple[str, ...]) -> None:
    """Rejects a recorded timeline that reverses or switches a decided contract."""
    if not isinstance(states, tuple) or not states:
        raise ValueError("Recorded state timeline must be a non-empty tuple.")
    if any(state not in REPLAY_COACHING_RECORDED_STATES for state in states):
        raise ValueError("Recorded state timeline contains an unsupported state.")
    decided_state = states[0] if states[0] != "undecided" else None
    for state in states[1:]:
        if decided_state is None:
            if state != "undecided":
                decided_state = state
        elif state != decided_state:
            raise ValueError("A recorded decided state cannot reverse or switch sides.")


def _completed_prefix_facts(
    record: HistoricalGameRecord,
    after_play_count: int,
) -> tuple[list[dict[str, Any]], int, int]:
    """Derives public trick facts without reading hands, the Skat, or later plays."""
    remaining_count = after_play_count
    completed_tricks = []
    declarer_points = 0
    defender_points = 0
    for trick in record.tricks:
        if remaining_count < len(trick.plays) or len(trick.plays) != 3:
            break
        cards = [play.card for play in trick.plays]
        winner_index = get_trick_winner(cards, record.declaration.game_type)
        winner_side = (
            "declarer"
            if trick.plays[winner_index].player_id == record.declarer_player_id
            else "defenders"
        )
        trick_points = get_trick_points(cards)
        completed_tricks.append({"cards": cards, "winner_role": winner_side})
        if winner_side == "declarer":
            declarer_points += trick_points
        else:
            defender_points += trick_points
        remaining_count -= 3
        if remaining_count == 0:
            break
    return completed_tricks, declarer_points, defender_points


def _state_at_boundary(
    record: HistoricalGameRecord,
    after_play_count: int,
    total_play_count: int,
    game_value_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
) -> str:
    completed_tricks, declarer_points, defender_points = _completed_prefix_facts(
        record,
        after_play_count,
    )
    game_result = build_game_result_summary_from_score_summary(
        {
            "total_declarer_points": declarer_points,
            "total_defender_points": defender_points,
        },
        game_type=record.declaration.game_type,
        completed_tricks=completed_tricks,
        game_end_reason="not_ended",
    )
    state = determine_decision_state_before_game_end(
        game_result,
        game_value_summary,
        overbid_summary,
        completed_tricks,
    )
    if (
        state == "undecided"
        and record.game_end_reason == HISTORICAL_NORMAL_COMPLETION
        and total_play_count == 30
        and after_play_count == 30
    ):
        terminal_result = build_game_result_summary_from_score_summary(
            {
                "total_declarer_points": 120 - defender_points,
                "total_defender_points": defender_points,
            },
            game_type=record.declaration.game_type,
            completed_tricks=completed_tricks,
            game_end_reason=HISTORICAL_NORMAL_COMPLETION,
        )
        settlement = build_final_settlement_summary(
            game_value_summary,
            terminal_result,
            overbid_summary,
            completed_tricks,
        )
        if settlement["is_complete"] is not True or not isinstance(
            settlement["is_loss"], bool
        ):
            raise ValueError("Complete normal-play fallback requires final settlement.")
        state = (
            "defenders_already_won"
            if settlement["is_loss"]
            else "declarer_already_won"
        )
    return state


def build_recorded_decision_state_timeline(
    record: HistoricalGameRecord,
) -> tuple[str, ...]:
    """Builds the contract-decision state at every actual card-play boundary."""
    if not isinstance(record, HistoricalGameRecord):
        raise ValueError("record must be HistoricalGameRecord.")
    total_play_count = sum(len(trick.plays) for trick in record.tricks)
    game_value_summary = build_game_value_summary(record.declaration)
    overbid_summary = build_overbid_summary(
        game_value_summary,
        record.declaration.bid_value,
    )
    states = tuple(
        _state_at_boundary(
            record,
            boundary,
            total_play_count,
            game_value_summary,
            overbid_summary,
        )
        for boundary in range(total_play_count + 1)
    )
    validate_recorded_decision_state_timeline(states)
    return states


def build_replay_coaching_turning_points(
    record: HistoricalGameRecord,
    assessments: tuple[ReplayCoachingDecisionAssessment, ...],
) -> tuple[ReplayCoachingTurningPoint, ...]:
    """Builds separate counterfactual and first recorded-path Turning Points."""
    opportunities = [
        ReplayCoachingTurningPoint(
            prioritization_version=REPLAY_COACHING_PRIORITIZATION_VERSION,
            turning_point_type="decision_opportunity",
            decision_index=assessment.decision_time_evidence.decision_index,
            assessment=assessment,
            is_high_impact=True,
            recorded_state_before=None,
            recorded_state_after=None,
            decided_side=None,
            factors=("lower_contract_success_opportunity",),
            limitations=(
                *assessment.limitations,
                "counterfactual_aggregate_not_causal",
            ),
        )
        for assessment in assessments
        if assessment.assessment_status == "strictly_below_best"
        and assessment.impact_tier == "contract_success"
        and assessment.evidence_basis
        in {
            "all_compatible_worlds",
            "sampled_compatible_worlds",
            "completed_common_prefix",
        }
    ]
    states = build_recorded_decision_state_timeline(record)
    recorded = []
    for decision_index, (before, after) in enumerate(
        zip(states, states[1:], strict=False), start=1
    ):
        if before == "undecided" and after != "undecided":
            assessment = assessments[decision_index - 1]
            factor_set = {
                "recorded_contract_became_decided",
                (
                    "recorded_declarer_became_decided"
                    if after == "declarer_already_won"
                    else "recorded_defenders_became_decided"
                ),
            }
            if assessment.assessment_status == "forced_move":
                factor_set.add("forced_recorded_outcome_transition")
            recorded.append(
                ReplayCoachingTurningPoint(
                    prioritization_version=REPLAY_COACHING_PRIORITIZATION_VERSION,
                    turning_point_type="recorded_outcome",
                    decision_index=decision_index,
                    assessment=assessment,
                    is_high_impact=True,
                    recorded_state_before=before,
                    recorded_state_after=after,
                    decided_side=(
                        "declarer"
                        if after == "declarer_already_won"
                        else "defenders"
                    ),
                    factors=tuple(
                        factor
                        for factor in REPLAY_COACHING_TURNING_POINT_FACTORS
                        if factor in factor_set
                    ),
                    limitations=(
                        "recorded_path_only",
                        "decision_not_single_cause",
                        "observed_card_not_ground_truth",
                    ),
                )
            )
            break
    points = [*opportunities, *recorded]
    points.sort(
        key=lambda point: (
            point.assessment.decision_time_evidence.decision_index,
            REPLAY_COACHING_TURNING_POINT_TYPES.index(point.turning_point_type),
        )
    )
    return tuple(points)


def build_serializable_replay_coaching_turning_point(
    turning_point: ReplayCoachingTurningPoint,
) -> dict[str, Any]:
    from skat_ai.replay_coaching_assessment import (
        build_serializable_replay_coaching_decision_assessment,
    )

    return {
        "prioritization_version": turning_point.prioritization_version,
        "turning_point_type": turning_point.turning_point_type,
        "decision_index": turning_point.decision_index,
        "assessment": build_serializable_replay_coaching_decision_assessment(
            turning_point.assessment
        ),
        "is_high_impact": turning_point.is_high_impact,
        "recorded_state_before": turning_point.recorded_state_before,
        "recorded_state_after": turning_point.recorded_state_after,
        "decided_side": turning_point.decided_side,
        "factors": list(turning_point.factors),
        "limitations": list(turning_point.limitations),
    }
