from collections.abc import Mapping, Sequence
from typing import Any

from skat_ai.game_result import get_null_contract_winner_from_completed_tricks

VALID_NULL_OBJECTIVE_PLAYER_ROLES = ["declarer", "defender"]
VALID_WINNER_ROLES = ["declarer", "defenders"]


def calculate_expected_point_swing(value: Mapping[str, float]) -> float:
    """Calculates expected local card-point swing for one simulated value."""
    return float(value["average_points_won"]) - float(value["average_points_lost"])


def validate_null_objective_player_role(player_role: str) -> None:
    """Validates that a local Null objective can be determined."""
    if player_role not in VALID_NULL_OBJECTIVE_PLAYER_ROLES:
        raise ValueError(
            "Null objective utility requires player_role to be declarer or defender."
        )


def validate_winner_role(winner_role: str) -> None:
    """Validates a completed-trick winner role."""
    if winner_role not in VALID_WINNER_ROLES:
        raise ValueError(f"Invalid winner_role for objective utility: {winner_role}")


def calculate_null_trick_objective_utility(
    player_role: str,
    winner_role: str,
) -> float:
    """Returns one-trick Null contract-objective utility for the local player."""
    validate_null_objective_player_role(player_role)
    validate_winner_role(winner_role)

    declarer_won_trick = winner_role == "declarer"

    if player_role == "declarer":
        return 0.0 if declarer_won_trick else 1.0

    return 1.0 if declarer_won_trick else 0.0


def calculate_null_horizon_objective_utility(
    player_role: str,
    evaluated_completed_tricks: Sequence[Mapping[str, Any]],
    terminal_contract_winner: str | None = None,
) -> float:
    """Returns Null objective utility across all newly evaluated tricks."""
    validate_null_objective_player_role(player_role)

    if terminal_contract_winner is not None:
        validate_winner_role(terminal_contract_winner)

        if player_role == "declarer":
            return 1.0 if terminal_contract_winner == "declarer" else 0.0

        return 1.0 if terminal_contract_winner == "defenders" else 0.0

    declarer_won_any_trick = False

    for completed_trick in evaluated_completed_tricks:
        winner_role = str(completed_trick["winner_role"])
        validate_winner_role(winner_role)

        if winner_role == "declarer":
            declarer_won_any_trick = True

    if player_role == "declarer":
        return 0.0 if declarer_won_any_trick else 1.0

    return 1.0 if declarer_won_any_trick else 0.0


def get_reliable_terminal_null_contract_winner(
    completed_tricks: Sequence[Mapping[str, Any]],
) -> str | None:
    """Returns the terminal Null winner only when ten trick owners are available."""
    if len(completed_tricks) != 10:
        return None

    return get_null_contract_winner_from_completed_tricks(
        [dict(completed_trick) for completed_trick in completed_tricks]
    )


def calculate_null_horizon_utility_from_states(
    player_role: str,
    initial_completed_tricks: Sequence[Mapping[str, Any]],
    final_completed_tricks: Sequence[Mapping[str, Any]],
) -> float:
    """Calculates Null horizon utility from the newly appended completed tricks."""
    evaluated_completed_tricks = final_completed_tricks[len(initial_completed_tricks):]
    terminal_contract_winner = get_reliable_terminal_null_contract_winner(
        final_completed_tricks
    )

    return calculate_null_horizon_objective_utility(
        player_role=player_role,
        evaluated_completed_tricks=evaluated_completed_tricks,
        terminal_contract_winner=terminal_contract_winner,
    )


def calculate_expected_objective_utility(
    game_type: str,
    player_role: str,
    value: Mapping[str, float],
) -> float:
    """Returns the game-type-aware expected utility used for candidate ranking."""
    if game_type == "null":
        validate_null_objective_player_role(player_role)

        if "expected_objective_utility" in value:
            return float(value["expected_objective_utility"])

        # Public report rows intentionally keep point fields informational. For
        # immediate Null analysis, objective success is the local side losing.
        return 1.0 - float(value["win_rate"])

    return calculate_expected_point_swing(value)


def sort_cards_by_expected_objective(
    cards: Sequence[str],
    values: Mapping[str, Mapping[str, float]],
    game_type: str,
    player_role: str,
) -> list[str]:
    """Sorts cards best-first by the correct game-type-aware objective."""
    indexed_cards = list(enumerate(cards))

    return [
        card
        for _, card in sorted(
            indexed_cards,
            key=lambda item: (
                -calculate_expected_objective_utility(
                    game_type=game_type,
                    player_role=player_role,
                    value=values[item[1]],
                ),
                item[0],
            ),
        )
    ]


def choose_best_card_by_expected_objective(
    values: Mapping[str, Mapping[str, float]],
    game_type: str,
    player_role: str,
) -> str:
    """Chooses the best card by the correct game-type-aware objective."""
    if not values:
        raise ValueError("No legal cards available.")

    return sort_cards_by_expected_objective(
        cards=list(values.keys()),
        values=values,
        game_type=game_type,
        player_role=player_role,
    )[0]
