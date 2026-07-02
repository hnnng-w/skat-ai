from skat_ai.game_state import GameState
from skat_ai.objective_utility import (
    calculate_expected_objective_utility,
    sort_cards_by_expected_objective,
)
from skat_ai.objective_utility import (
    calculate_expected_point_swing as calculate_value_expected_point_swing,
)
from skat_ai.simulation import estimate_immediate_trick_values_for_legal_cards


def calculate_expected_point_swing(value: dict[str, float]) -> float:
    """
    Calculates the expected point swing for one card.

    Expected point swing:
    average_points_won - average_points_lost
    """
    return calculate_value_expected_point_swing(value)


def build_card_analysis_report(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    opponent_response_policy_by_player: dict[str, str] | None = None,
) -> list[dict[str, float | str | bool]]:
    """
    Builds an analysis report for all legal cards.

    The report is sorted by expected point swing in descending order.
    The first row is marked as recommended.
    """
    values = estimate_immediate_trick_values_for_legal_cards(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        sample_count=sample_count,
        random_seed=random_seed,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
    )

    report = []

    for card, value in values.items():
        expected_point_swing = calculate_expected_point_swing(value)

        report.append(
            {
                "card": card,
                "win_rate": value["win_rate"],
                "average_trick_points": value["average_trick_points"],
                "average_points_won": value["average_points_won"],
                "average_points_lost": value["average_points_lost"],
                "expected_point_swing": expected_point_swing,
                "is_recommended": False,
            }
        )

    row_by_card = {str(row["card"]): row for row in report}
    sorted_cards = sort_cards_by_expected_objective(
        cards=list(values.keys()),
        values=values,
        game_type=state.game_type,
        player_role=state.player_role,
    )
    sorted_report = [row_by_card[card] for card in sorted_cards]

    if sorted_report:
        sorted_report[0]["is_recommended"] = True

    return sorted_report


def format_card_analysis_report(report: list[dict[str, float | str | bool]]) -> str:
    """
    Formats a card analysis report as a readable text table.
    """
    if not report:
        return "No legal cards available."

    lines = [
        "Card analysis report",
        "",
        (
            f"{'Card':<6} "
            f"{'Win rate':>8} "
            f"{'Avg trick':>10} "
            f"{'Avg won':>10} "
            f"{'Avg lost':>10} "
            f"{'Swing':>10} "
            f"{'Recommendation':>15}"
        ),
        "-" * 77,
    ]

    for row in report:
        recommendation_marker = "<-- best" if row["is_recommended"] else ""

        lines.append(
            f"{row['card']:<6} "
            f"{row['win_rate']:>8.3f} "
            f"{row['average_trick_points']:>10.2f} "
            f"{row['average_points_won']:>10.2f} "
            f"{row['average_points_lost']:>10.2f} "
            f"{row['expected_point_swing']:>10.2f} "
            f"{recommendation_marker:>15}"
        )

    return "\n".join(lines)


def build_strategic_summary(
    report: list[dict[str, float | str | bool]],
    game_type: str = "grand",
    player_role: str = "unknown",
) -> str:
    """
    Builds a short strategic interpretation from the card analysis report.
    """
    if not report:
        return "Strategic summary: No legal cards are available."

    best_row = report[0]
    best_card = best_row["card"]
    best_swing = best_row["expected_point_swing"]
    best_win_rate = best_row["win_rate"]

    if game_type == "null":
        return build_null_strategic_summary(
            report=report,
            player_role=player_role,
        )

    if len(report) == 1:
        return (
            "Strategic summary: "
            f"{best_card} is the only legal card. "
            f"Its estimated expected point swing is {best_swing:.2f} "
            f"with a win rate of {best_win_rate:.3f}."
        )

    second_row = report[1]
    second_card = second_row["card"]
    second_swing = second_row["expected_point_swing"]
    second_win_rate = second_row["win_rate"]

    swing_gap = best_swing - second_swing
    win_rate_gap = best_win_rate - second_win_rate

    if best_swing <= 0:
        return (
            "Strategic summary: "
            f"{best_card} is recommended because it is the least damaging option in this position. "
            f"Even the best option has a non-positive expected point swing of {best_swing:.2f}."
        )

    if swing_gap >= 5:
        return (
            "Strategic summary: "
            f"{best_card} is recommended because it has the best expected point swing. "
            f"It is ahead of {second_card} by {swing_gap:.2f} expected points "
            f"and by {win_rate_gap:.3f} win rate."
        )

    return (
        "Strategic summary: "
        f"{best_card} is recommended, but the advantage over {second_card} is modest. "
        f"The expected point swing gap is {swing_gap:.2f}, so this position may be close."
    )


def build_null_strategic_summary(
    report: list[dict[str, float | str | bool]],
    player_role: str,
) -> str:
    """Builds a Null-specific strategic summary from an objective-sorted report."""
    best_row = report[0]
    best_card = str(best_row["card"])
    best_utility = calculate_expected_objective_utility(
        game_type="null",
        player_role=player_role,
        value=best_row,
    )

    if player_role == "declarer":
        objective_text = "avoid taking any evaluated trick"
    elif player_role == "defender":
        objective_text = "make the concrete declarer take an evaluated trick"
    else:
        raise ValueError(
            "Null strategic summary requires player_role to be declarer or defender."
        )

    if len(report) == 1:
        return (
            "Strategic summary: "
            f"{best_card} is the only legal card. Its estimated Null objective "
            f"utility is {best_utility:.3f}; the objective is to {objective_text}."
        )

    second_row = report[1]
    second_card = str(second_row["card"])
    second_utility = calculate_expected_objective_utility(
        game_type="null",
        player_role=player_role,
        value=second_row,
    )
    utility_gap = best_utility - second_utility

    if utility_gap > 0.0:
        return (
            "Strategic summary: "
            f"{best_card} is recommended because it best supports the Null "
            f"contract objective to {objective_text}. It is ahead of {second_card} "
            f"by {utility_gap:.3f} objective utility."
        )

    return (
        "Strategic summary: "
        f"{best_card} is recommended by stable legal-card order because the Null "
        f"objective utility is tied with {second_card}. The objective is to "
        f"{objective_text}."
    )
