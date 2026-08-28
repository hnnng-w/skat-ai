from dataclasses import dataclass
from typing import Any

from skatmind.historical_game_end import (
    HISTORICAL_DECLARER_CARD_EXPOSURE,
    HISTORICAL_DECLARER_CONCESSION,
    HISTORICAL_DEFENDER_CONCESSION,
    HISTORICAL_DEFENDER_OPEN_PLAY,
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_OPEN_CARD_THROW,
    HISTORICAL_PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM,
)

MAX_HISTORICAL_DECISION_COUNT = 30
SUPPORTED_HISTORICAL_DECISION_END_REASONS = {
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_DECLARER_CONCESSION,
    HISTORICAL_DEFENDER_CONCESSION,
    HISTORICAL_DECLARER_CARD_EXPOSURE,
    HISTORICAL_DEFENDER_OPEN_PLAY,
    HISTORICAL_OPEN_CARD_THROW,
    HISTORICAL_PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM,
}


@dataclass(frozen=True)
class HistoricalDecisionCardinality:
    """Shared artifact counts derived from one validated historical play prefix."""

    game_end_reason: str
    played_card_count: int
    expected_snapshot_count: int
    expected_review_decision_count: int
    expected_training_sample_count: int


def derive_historical_decision_cardinality(
    historical_game_result: dict[str, Any],
) -> HistoricalDecisionCardinality:
    """Derives all decision artifact counts from the supplied historical plays."""
    record = historical_game_result["record"]
    game_end_reason = record["game_end_reason"]
    if game_end_reason not in SUPPORTED_HISTORICAL_DECISION_END_REASONS:
        raise ValueError(
            "Historical decision workflows support only normal_completion, "
            "declarer_concession, defender_concession, and "
            "declarer_card_exposure, defender_open_play, open_card_throw, and "
            "party_wide_all_remaining_tricks_claim, got "
            f"'{game_end_reason}'."
        )

    played_card_count = sum(
        len(trick["plays"]) for trick in record["tricks"]
    )
    if game_end_reason == HISTORICAL_NORMAL_COMPLETION:
        if played_card_count != MAX_HISTORICAL_DECISION_COUNT:
            raise ValueError(
                "A validated normal-completion record must contain exactly 30 plays."
            )
    elif not 0 <= played_card_count < MAX_HISTORICAL_DECISION_COUNT:
        raise ValueError(
            "A validated shortened record must contain between 0 and 29 plays."
        )

    return HistoricalDecisionCardinality(
        game_end_reason=game_end_reason,
        played_card_count=played_card_count,
        expected_snapshot_count=played_card_count,
        expected_review_decision_count=played_card_count,
        expected_training_sample_count=played_card_count,
    )
