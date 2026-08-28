"""Opponent-statistics presentation."""

from typing import Any


def print_opponent_statistics_result(result: dict[str, Any]) -> None:
    """Prints one concise summary per external opponent-statistics record."""
    summary = result["opponent_statistics_summary"]
    print("Opponent statistics summary")
    print("Input file:", result["input_file"])
    print("Records:", summary["record_count"])
    for record in summary["records"]:
        statistics = record["statistics"]
        derivation = record["profile_derivation"]
        label = record.get("player_label")
        identity = record["player_id"] if label is None else f"{record['player_id']} ({label})"
        print(
            f"{identity}: {record['games_played']} games; "
            f"declarer {statistics['solo_games_played_percent']:g}%; "
            f"declarer wins {statistics['solo_games_won_percent']:g}%; "
            f"defender {statistics['defender_games_played_percent']:g}%; "
            f"defender wins {statistics['defender_games_won_percent']:g}%."
        )
        confidence = derivation["confidence"]
        actionable = derivation["actionable_policy_preset"] is not None
        print(
            "  Profile derivation: "
            f"overall {confidence['overall']['level']}, "
            f"declarer {confidence['declarer']['level']}, "
            f"defender {confidence['defender']['level']}; "
            f"classification {derivation['classification']}; "
            f"recommended preset {derivation['recommended_policy_preset']}; "
            f"actionable {'yes' if actionable else 'no'}."
        )
        print(f"  Explanation: {derivation['explanations'][-1]}")


def print_historical_opponent_statistics_result(result: dict[str, Any]) -> None:
    """Prints a concise historical aggregation summary."""
    summary = result["historical_opponent_statistics_aggregation_summary"]
    print(
        "Historical opponent statistics: "
        f"{summary['source_game_count']} games, {summary['player_count']} players."
    )
    print(
        "Included partitions:",
        ", ".join(summary["selection"]["included_partitions"]),
    )
    for record in summary["records"]:
        statistics = record["statistics"]
        confidence = record["profile_derivation"]["confidence"]["overall"]["level"]
        print(
            f"{record['player_id']}: {record['games_played']} games, "
            f"{statistics['solo_games_played_percent']:.2f}% declarer, "
            f"{statistics['defender_games_played_percent']:.2f}% defender, "
            f"{confidence} confidence."
        )
