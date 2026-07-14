from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.analysis_report import build_card_analysis_report_from_values
from skat_ai.game_value import get_null_game_value
from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    HistoricalDecisionSnapshotSummary,
)
from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.historical_snapshot_adapter import (
    build_position_from_historical_snapshot,
)
from skat_ai.input_validation import MAX_SAMPLE_COUNT, validate_positive_integer_maximum
from skat_ai.post_game_review import (
    ACCEPTABLE_DECISION_QUALITY,
    MISTAKE_DECISION_QUALITY,
    NOT_AVAILABLE_DECISION_QUALITY,
    OPTIMAL_DECISION_QUALITY,
    SUBOPTIMAL_DECISION_QUALITY,
    build_post_game_review_summary,
    build_unavailable_post_game_review_summary,
)
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

HISTORICAL_GAME_REVIEW_SCHEMA_VERSION = 1
HISTORICAL_GAME_REVIEW_ANALYSIS_METHOD = "immediate_expected_value"
HISTORICAL_GAME_REVIEW_INFORMATION_POLICY = "decision_time"
PUBLIC_EXPOSED_CARDS_UNAVAILABLE_REASON = "public_exposed_cards_not_supported"
QUALITY_NAMES = (
    OPTIMAL_DECISION_QUALITY,
    ACCEPTABLE_DECISION_QUALITY,
    SUBOPTIMAL_DECISION_QUALITY,
    MISTAKE_DECISION_QUALITY,
    NOT_AVAILABLE_DECISION_QUALITY,
)


@dataclass(frozen=True)
class HistoricalGameReviewSettings:
    """The fixed settings shared by all decisions in one historical review."""

    sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    base_random_seed: int | None = None
    opponent_policy_mode: Literal["default"] = "default"


def _build_empty_quality_counts() -> dict[str, int]:
    return {quality: 0 for quality in QUALITY_NAMES}


def _build_unavailable_decision(
    snapshot: HistoricalDecisionSnapshot,
    effective_random_seed: int | None,
) -> dict[str, Any]:
    explanation = (
        "No post-game review decision quality is available because public exposed "
        "cards are not supported by immediate simulation."
    )
    post_game_review_summary = build_unavailable_post_game_review_summary(
        reason=PUBLIC_EXPOSED_CARDS_UNAVAILABLE_REASON,
        actual_card_played=snapshot.actual_card_played,
        decision_explanation=explanation,
    )
    return {
        **_build_decision_identity(snapshot),
        "status": "unavailable",
        "unavailable_reason": PUBLIC_EXPOSED_CARDS_UNAVAILABLE_REASON,
        "effective_random_seed": effective_random_seed,
        "legal_cards": [],
        "recommendation": {
            "card": None,
            "reason": explanation,
        },
        "analysis_report": [],
        "post_game_review_summary": post_game_review_summary,
    }


def _build_decision_identity(
    snapshot: HistoricalDecisionSnapshot,
) -> dict[str, str | int]:
    return {
        "source_game_id": snapshot.source_game_id,
        "decision_index": snapshot.decision_index,
        "trick_number": snapshot.trick_number,
        "play_index": snapshot.play_index,
        "acting_player_id": snapshot.acting_player_id,
        "acting_seat": snapshot.acting_seat,
        "acting_side": snapshot.acting_side,
        "actual_card_played": snapshot.actual_card_played,
    }


def _build_reviewed_decision(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    sample_count: int,
    effective_random_seed: int | None,
) -> dict[str, Any]:
    position = build_position_from_historical_snapshot(
        snapshot=snapshot,
        historical_record=historical_record,
    )
    recommended_card, recommendation_reason, values = (
        recommend_card_by_expected_value(
            state=position.state,
            left_hand_size=position.left_hand_size,
            right_hand_size=position.right_hand_size,
            sample_count=sample_count,
            random_seed=effective_random_seed,
        )
    )
    analysis_report = build_card_analysis_report_from_values(
        state=position.state,
        values=values,
    )
    recommended_rows = [
        row for row in analysis_report if row["is_recommended"] is True
    ]
    if len(recommended_rows) != 1 or recommended_rows[0]["card"] != recommended_card:
        raise ValueError("Historical recommendation and analysis report are inconsistent.")

    game_value = (
        get_null_game_value(position.game_declaration)
        if position.state.game_type == "null"
        else None
    )
    post_game_review_summary = build_post_game_review_summary(
        actual_card_played=snapshot.actual_card_played,
        analysis_report=analysis_report,
        game_type=position.state.game_type,
        player_role=position.state.player_role,
        game_value=game_value,
    )
    return {
        **_build_decision_identity(snapshot),
        "status": "reviewed",
        "unavailable_reason": None,
        "effective_random_seed": effective_random_seed,
        "legal_cards": list(position.legal_cards),
        "recommendation": {
            "card": recommended_card,
            "reason": recommendation_reason,
        },
        "analysis_report": analysis_report,
        "post_game_review_summary": post_game_review_summary,
    }


def _build_player_summaries(
    historical_record: HistoricalGameRecord,
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summaries = []
    for player in historical_record.players:
        player_decisions = [
            decision
            for decision in decisions
            if decision["acting_player_id"] == player.player_id
        ]
        quality_counts = _build_empty_quality_counts()
        for decision in player_decisions:
            quality = decision["post_game_review_summary"]["decision_quality"]
            quality_counts[quality] += 1
        reviewed_count = sum(
            decision["status"] == "reviewed" for decision in player_decisions
        )
        unavailable_count = len(player_decisions) - reviewed_count
        summaries.append(
            {
                "player_id": player.player_id,
                "player_label": player.player_label,
                "seat": player.seat,
                "side": (
                    "declarer"
                    if player.player_id == historical_record.declarer_player_id
                    else "defenders"
                ),
                "decision_count": len(player_decisions),
                "reviewed_decision_count": reviewed_count,
                "unavailable_decision_count": unavailable_count,
                "quality_counts": quality_counts,
            }
        )
    return summaries


def build_historical_game_review_summary(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    base_random_seed: int | None = None,
) -> dict[str, Any]:
    """Evaluates all historical decisions through the immediate review pipeline."""
    if snapshot_summary.snapshot_count != 30 or len(snapshot_summary.snapshots) != 30:
        raise ValueError("Historical game review requires exactly 30 snapshots.")
    validate_positive_integer_maximum(
        sample_count,
        "sample_count",
        MAX_SAMPLE_COUNT,
    )

    settings = HistoricalGameReviewSettings(
        sample_count=sample_count,
        base_random_seed=base_random_seed,
    )
    decisions = []
    for snapshot in snapshot_summary.snapshots:
        effective_random_seed = (
            None
            if settings.base_random_seed is None
            else settings.base_random_seed + snapshot.decision_index - 1
        )
        if snapshot.visible_state.public_exposed_cards:
            decision = _build_unavailable_decision(
                snapshot=snapshot,
                effective_random_seed=effective_random_seed,
            )
        else:
            decision = _build_reviewed_decision(
                snapshot=snapshot,
                historical_record=historical_record,
                sample_count=settings.sample_count,
                effective_random_seed=effective_random_seed,
            )
        decisions.append(decision)

    quality_counts = _build_empty_quality_counts()
    for decision in decisions:
        quality = decision["post_game_review_summary"]["decision_quality"]
        quality_counts[quality] += 1
    reviewed_count = sum(decision["status"] == "reviewed" for decision in decisions)
    unavailable_count = len(decisions) - reviewed_count
    player_summaries = _build_player_summaries(
        historical_record=historical_record,
        decisions=decisions,
    )

    if len(player_summaries) != 3 or any(
        summary["decision_count"] != 10 for summary in player_summaries
    ):
        raise ValueError("Historical game review requires ten decisions per player.")
    if sum(summary["reviewed_decision_count"] for summary in player_summaries) != reviewed_count:
        raise ValueError("Historical player reviewed-decision totals do not reconcile.")
    if sum(
        summary["unavailable_decision_count"] for summary in player_summaries
    ) != unavailable_count:
        raise ValueError("Historical player unavailable-decision totals do not reconcile.")
    for quality in QUALITY_NAMES:
        if sum(
            summary["quality_counts"][quality] for summary in player_summaries
        ) != quality_counts[quality]:
            raise ValueError("Historical player quality totals do not reconcile.")

    return {
        "schema_version": HISTORICAL_GAME_REVIEW_SCHEMA_VERSION,
        "analysis_method": HISTORICAL_GAME_REVIEW_ANALYSIS_METHOD,
        "information_policy": HISTORICAL_GAME_REVIEW_INFORMATION_POLICY,
        "decision_count": len(decisions),
        "reviewed_decision_count": reviewed_count,
        "unavailable_decision_count": unavailable_count,
        "settings": {
            "sample_count": settings.sample_count,
            "base_random_seed": settings.base_random_seed,
            "opponent_policy_mode": settings.opponent_policy_mode,
        },
        "quality_counts": quality_counts,
        "player_summaries": player_summaries,
        "decisions": decisions,
    }
