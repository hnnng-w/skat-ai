from typing import Any

from skat_ai.objective_utility import calculate_expected_objective_utility

NOT_AVAILABLE_DECISION_QUALITY = "not_available"
OPTIMAL_DECISION_QUALITY = "optimal"
ACCEPTABLE_DECISION_QUALITY = "acceptable"
SUBOPTIMAL_DECISION_QUALITY = "suboptimal"
MISTAKE_DECISION_QUALITY = "mistake"
IMMEDIATE_ANALYSIS_UNAVAILABLE_REASON = "immediate_analysis_unavailable"
NO_MISSED_NULL_OBJECTIVE_FACTOR = "no_missed_null_objective"
LOWER_NULL_OBJECTIVE_FACTOR = "lower_null_objective_than_recommendation"
SMALL_NULL_OBJECTIVE_GAP_FACTOR = "small_null_objective_gap"
MEDIUM_NULL_OBJECTIVE_GAP_FACTOR = "medium_null_objective_gap"
LARGE_NULL_OBJECTIVE_GAP_FACTOR = "large_null_objective_gap"


def classify_decision_quality(expected_point_swing_difference: float) -> str:
    """Classifies decision quality from a scaled missed-value gap."""
    if expected_point_swing_difference <= 0.0:
        return OPTIMAL_DECISION_QUALITY

    if expected_point_swing_difference <= 2.0:
        return ACCEPTABLE_DECISION_QUALITY

    if expected_point_swing_difference <= 6.0:
        return SUBOPTIMAL_DECISION_QUALITY

    return MISTAKE_DECISION_QUALITY


def get_recommended_report_row(
    analysis_report: list[dict[str, Any]],
) -> dict[str, Any]:
    """Returns the single recommended row from the card analysis report."""
    recommended_rows = [
        row for row in analysis_report if row.get("is_recommended") is True
    ]

    if len(recommended_rows) != 1:
        raise ValueError("analysis_report must contain exactly one recommended row.")

    return recommended_rows[0]


def get_report_row_for_card(
    analysis_report: list[dict[str, Any]],
    card: str,
) -> dict[str, Any]:
    """Returns the report row for the given card."""
    matching_rows = [row for row in analysis_report if row.get("card") == card]

    if len(matching_rows) != 1:
        raise ValueError("actual_card_played must be present exactly once in analysis_report.")

    return matching_rows[0]


def build_card_rank_lookup(
    analysis_report: list[dict[str, Any]],
    game_type: str = "grand",
    player_role: str = "unknown",
) -> dict[str, int]:
    """Builds one-based card ranks by the game-type-aware objective."""
    indexed_rows = list(enumerate(analysis_report))
    sorted_rows = [
        row
        for _, row in sorted(
            indexed_rows,
            key=lambda item: (
                -calculate_report_row_objective_utility(
                    row=item[1],
                    game_type=game_type,
                    player_role=player_role,
                ),
                item[0],
            ),
        )
    ]

    return {
        str(row["card"]): index + 1
        for index, row in enumerate(sorted_rows)
    }


def calculate_report_row_objective_utility(
    row: dict[str, Any],
    game_type: str = "grand",
    player_role: str = "unknown",
) -> float:
    """Returns the objective utility for a card analysis report row."""
    return calculate_expected_objective_utility(
        game_type=game_type,
        player_role=player_role,
        value=row,
    )


def count_better_cards(
    analysis_report: list[dict[str, Any]],
    actual_expected_point_swing: float,
    game_type: str = "grand",
    player_role: str = "unknown",
    actual_objective_utility: float | None = None,
) -> int:
    """Counts cards that are better than the actual card by the review objective."""
    if game_type == "null":
        if actual_objective_utility is None:
            raise ValueError("actual_objective_utility is required for Null review.")

        return sum(
            1
            for row in analysis_report
            if calculate_report_row_objective_utility(
                row=row,
                game_type=game_type,
                player_role=player_role,
            ) > actual_objective_utility
        )

    return sum(
        1
        for row in analysis_report
        if float(row["expected_point_swing"]) > actual_expected_point_swing
    )


def build_post_game_review_summary(
    actual_card_played: str | None,
    analysis_report: list[dict[str, Any]],
    game_type: str = "grand",
    player_role: str = "unknown",
    game_value: int | None = None,
) -> dict[str, Any]:
    """Builds a post-game review summary for the actual card played."""
    if not analysis_report:
        return build_unavailable_post_game_review_summary(
            reason=IMMEDIATE_ANALYSIS_UNAVAILABLE_REASON,
            actual_card_played=actual_card_played,
            decision_explanation=(
                "No post-game review decision quality is available because "
                "immediate analysis is unavailable."
            ),
        )

    recommended_row = get_recommended_report_row(analysis_report)
    recommended_card = recommended_row["card"]
    recommended_expected_point_swing = recommended_row["expected_point_swing"]
    card_rank_lookup = build_card_rank_lookup(
        analysis_report=analysis_report,
        game_type=game_type,
        player_role=player_role,
    )
    candidate_count = len(analysis_report)
    recommended_card_rank = card_rank_lookup[str(recommended_card)]

    if actual_card_played is None:
        decision_quality = NOT_AVAILABLE_DECISION_QUALITY
        decision_factors = build_decision_factors(
            actual_card_played=None,
            expected_point_swing_difference=None,
            game_type=game_type,
        )
        decision_explanation = build_decision_explanation(
            decision_quality=decision_quality,
            expected_point_swing_difference=None,
            game_type=game_type,
            player_role=player_role,
        )

        return {
            "is_available": False,
            "reason": "actual_card_played_not_provided",
            "actual_card_played": None,
            "recommended_card": recommended_card,
            "actual_expected_point_swing": None,
            "recommended_expected_point_swing": recommended_expected_point_swing,
            "expected_point_swing_difference": None,
            "decision_quality": decision_quality,
            "decision_factors": decision_factors,
            "decision_explanation": decision_explanation,
            "actual_card_rank": None,
            "recommended_card_rank": recommended_card_rank,
            "candidate_count": candidate_count,
            "better_card_count": None,
        }

    actual_row = get_report_row_for_card(
        analysis_report=analysis_report,
        card=actual_card_played,
    )
    actual_expected_point_swing = actual_row["expected_point_swing"]
    expected_point_swing_difference = (
        recommended_expected_point_swing - actual_expected_point_swing
    )

    actual_expected_point_swing_float = float(actual_expected_point_swing)
    actual_objective_utility = calculate_report_row_objective_utility(
        row=actual_row,
        game_type=game_type,
        player_role=player_role,
    )
    recommended_objective_utility = calculate_report_row_objective_utility(
        row=recommended_row,
        game_type=game_type,
        player_role=player_role,
    )
    actual_card_rank = card_rank_lookup[actual_card_played]
    better_card_count = count_better_cards(
        analysis_report=analysis_report,
        actual_expected_point_swing=actual_expected_point_swing_float,
        game_type=game_type,
        player_role=player_role,
        actual_objective_utility=actual_objective_utility,
    )

    classification_gap = expected_point_swing_difference
    if game_type == "null":
        classification_gap = calculate_scaled_null_objective_gap(
            recommended_objective_utility=recommended_objective_utility,
            actual_objective_utility=actual_objective_utility,
            game_value=game_value,
        )

    decision_quality = classify_decision_quality(classification_gap)
    decision_factors = build_decision_factors(
        actual_card_played=actual_card_played,
        expected_point_swing_difference=classification_gap,
        game_type=game_type,
    )
    decision_explanation = build_decision_explanation(
        decision_quality=decision_quality,
        expected_point_swing_difference=classification_gap,
        game_type=game_type,
        player_role=player_role,
    )

    return {
        "is_available": True,
        "reason": "actual_card_played_provided",
        "actual_card_played": actual_card_played,
        "recommended_card": recommended_card,
        "actual_expected_point_swing": actual_expected_point_swing,
        "recommended_expected_point_swing": recommended_expected_point_swing,
        "expected_point_swing_difference": expected_point_swing_difference,
        "decision_quality": decision_quality,
        "decision_factors": decision_factors,
        "decision_explanation": decision_explanation,
        "actual_card_rank": actual_card_rank,
        "recommended_card_rank": recommended_card_rank,
        "candidate_count": candidate_count,
        "better_card_count": better_card_count,
    }


def build_unavailable_post_game_review_summary(
    reason: str,
    actual_card_played: str | None = None,
    decision_explanation: str | None = None,
) -> dict[str, Any]:
    """Builds the stable unavailable post-game review shape."""
    if decision_explanation is None:
        decision_explanation = (
            "No post-game review decision quality is available because "
            "immediate analysis is unavailable."
        )

    return {
        "is_available": False,
        "reason": reason,
        "actual_card_played": actual_card_played,
        "recommended_card": None,
        "actual_expected_point_swing": None,
        "recommended_expected_point_swing": None,
        "expected_point_swing_difference": None,
        "decision_quality": NOT_AVAILABLE_DECISION_QUALITY,
        "decision_factors": [reason],
        "decision_explanation": decision_explanation,
        "actual_card_rank": None,
        "recommended_card_rank": None,
        "candidate_count": 0,
        "better_card_count": None,
    }


def build_decision_factors(
    actual_card_played: str | None,
    expected_point_swing_difference: float | None,
    game_type: str = "grand",
) -> list[str]:
    """Builds machine-readable factors for the post-game decision quality."""
    if actual_card_played is None:
        return ["actual_card_played_not_provided"]

    if expected_point_swing_difference is None:
        return ["expected_point_swing_difference_not_available"]

    if game_type == "null":
        return build_null_decision_factors(expected_point_swing_difference)

    if expected_point_swing_difference <= 0.0:
        return ["no_missed_expected_point_swing"]

    factors = ["lower_expected_point_swing_than_recommendation"]

    if expected_point_swing_difference <= 2.0:
        factors.append("small_expected_point_swing_gap")
    elif expected_point_swing_difference <= 6.0:
        factors.append("medium_expected_point_swing_gap")
    else:
        factors.append("large_expected_point_swing_gap")

    return factors


def build_decision_explanation(
    decision_quality: str,
    expected_point_swing_difference: float | None,
    game_type: str = "grand",
    player_role: str = "unknown",
) -> str:
    """Builds a human-readable explanation for the post-game decision quality."""
    if decision_quality == NOT_AVAILABLE_DECISION_QUALITY:
        return (
            "No post-game review decision quality is available because "
            "actual_card_played was not provided."
        )

    if game_type == "null":
        return build_null_decision_explanation(
            decision_quality=decision_quality,
            scaled_objective_gap=expected_point_swing_difference,
            player_role=player_role,
        )

    if decision_quality == OPTIMAL_DECISION_QUALITY:
        return (
            "The actual card matches the recommended card or has no missed "
            "expected point swing."
        )

    if decision_quality == ACCEPTABLE_DECISION_QUALITY:
        return (
            "The actual card is close to the recommended card with only a small "
            f"missed expected point swing of {expected_point_swing_difference:.2f}."
        )

    if decision_quality == SUBOPTIMAL_DECISION_QUALITY:
        return (
            "The actual card has a clearly lower expected point swing than the "
            f"recommended card. Missed expected point swing: "
            f"{expected_point_swing_difference:.2f}."
        )

    if decision_quality == MISTAKE_DECISION_QUALITY:
        return (
            "The actual card has a much lower expected point swing than the "
            f"recommended card. Missed expected point swing: "
            f"{expected_point_swing_difference:.2f}."
        )

    raise ValueError(f"Unsupported decision quality: {decision_quality}")


def calculate_scaled_null_objective_gap(
    recommended_objective_utility: float,
    actual_objective_utility: float,
    game_value: int | None,
) -> float:
    """Scales a Null objective-utility gap by the Null game value."""
    if game_value is None:
        raise ValueError("game_value is required for Null decision quality.")

    return (recommended_objective_utility - actual_objective_utility) * game_value


def build_null_decision_factors(
    scaled_objective_gap: float,
) -> list[str]:
    """Builds Null-specific decision factors from the objective gap."""
    if scaled_objective_gap <= 0.0:
        return [NO_MISSED_NULL_OBJECTIVE_FACTOR]

    factors = [LOWER_NULL_OBJECTIVE_FACTOR]

    if scaled_objective_gap <= 2.0:
        factors.append(SMALL_NULL_OBJECTIVE_GAP_FACTOR)
    elif scaled_objective_gap <= 6.0:
        factors.append(MEDIUM_NULL_OBJECTIVE_GAP_FACTOR)
    else:
        factors.append(LARGE_NULL_OBJECTIVE_GAP_FACTOR)

    return factors


def get_null_objective_text(player_role: str) -> str:
    """Returns human-readable Null objective text for the local player."""
    if player_role == "declarer":
        return "avoid taking any evaluated trick"

    if player_role == "defender":
        return "make the concrete declarer take an evaluated trick"

    raise ValueError("Null review requires player_role to be declarer or defender.")


def build_null_decision_explanation(
    decision_quality: str,
    scaled_objective_gap: float | None,
    player_role: str,
) -> str:
    """Builds a Null-specific decision explanation without reusing point-gap wording."""
    objective_text = get_null_objective_text(player_role)

    if decision_quality == OPTIMAL_DECISION_QUALITY:
        return (
            "The actual card has no missed Null contract-objective utility. "
            f"The Null objective is to {objective_text}."
        )

    if scaled_objective_gap is None:
        raise ValueError("scaled_objective_gap is required for Null review.")

    if decision_quality == ACCEPTABLE_DECISION_QUALITY:
        return (
            "The actual card is close to the recommendation by the Null contract "
            f"objective. The objective is to {objective_text}. Scaled objective "
            f"gap: {scaled_objective_gap:.2f}."
        )

    if decision_quality == SUBOPTIMAL_DECISION_QUALITY:
        return (
            "The actual card is clearly worse than the recommendation by the "
            f"Null contract objective. The objective is to {objective_text}. "
            f"Scaled objective gap: {scaled_objective_gap:.2f}."
        )

    if decision_quality == MISTAKE_DECISION_QUALITY:
        return (
            "The actual card is much worse than the recommendation by the Null "
            f"contract objective. The objective is to {objective_text}. Scaled "
            f"objective gap: {scaled_objective_gap:.2f}."
        )

    raise ValueError(f"Unsupported decision quality: {decision_quality}")
