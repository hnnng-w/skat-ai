from collections.abc import Iterable

from skat_ai.historical_game_end import (
    HISTORICAL_DECLARER_CONCESSION,
    HISTORICAL_NORMAL_COMPLETION,
)

SUPPORTED_HISTORICAL_OPPONENT_WORKFLOW_END_REASONS = {
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_DECLARER_CONCESSION,
}


def validate_historical_opponent_workflow_records(records: Iterable[object]) -> None:
    """Rejects selected records whose end reason lacks explicit workflow support."""
    supported = [HISTORICAL_NORMAL_COMPLETION, HISTORICAL_DECLARER_CONCESSION]
    for record in records:
        historical_game = record.historical_game
        end_reason = historical_game.game_end_reason
        if end_reason not in SUPPORTED_HISTORICAL_OPPONENT_WORKFLOW_END_REASONS:
            raise ValueError(
                f"Historical opponent workflow record '{record.record_id}' game "
                f"'{historical_game.game_id}' has unsupported end reason "
                f"'{end_reason}'; supported end reasons: {supported}."
            )
