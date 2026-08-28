from typing import Any

from skatmind.bounded_search_result import BoundedSearchResult
from skatmind.retrospective_search_comparison import (
    build_search_actual_card_comparison,
    build_search_vs_immediate_comparison,
    build_serializable_search_actual_card_comparison,
    build_serializable_search_vs_immediate_comparison,
)

BOUNDED_SEARCH_POST_GAME_REVIEW_SCHEMA_VERSION = 1
BOUNDED_SEARCH_POST_GAME_REVIEW_ANALYSIS_METHOD = (
    "bounded_search_with_immediate_baseline"
)


def build_bounded_search_post_game_review_summary(
    *,
    search_result: BoundedSearchResult,
    actual_card: str,
    immediate_card: str | None,
    immediate_analysis_report: list[dict[str, Any]],
    game_type: str,
    player_role: str,
) -> dict[str, Any]:
    """Builds retrospective comparisons after Search and Immediate have finished."""
    actual_comparison = build_search_actual_card_comparison(
        search_result,
        actual_card,
    )
    immediate_comparison = build_search_vs_immediate_comparison(
        search_result,
        immediate_card,
        immediate_analysis_report,
        game_type,
        player_role,
    )
    return {
        "schema_version": BOUNDED_SEARCH_POST_GAME_REVIEW_SCHEMA_VERSION,
        "analysis_method": BOUNDED_SEARCH_POST_GAME_REVIEW_ANALYSIS_METHOD,
        "game_type": search_result.game_type,
        "search_actual_card_comparison": (
            build_serializable_search_actual_card_comparison(actual_comparison)
        ),
        "search_vs_immediate_comparison": (
            build_serializable_search_vs_immediate_comparison(immediate_comparison)
        ),
    }
