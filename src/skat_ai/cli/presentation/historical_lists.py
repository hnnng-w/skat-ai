"""Fixed-three-player historical-list presentation."""

from typing import Any


def _format_list_player_identity(player_id: str, player_label: str | None) -> str:
    return player_id if player_label is None else f"{player_id} ({player_label})"


def print_fixed_three_player_historical_list_result(result: dict[str, Any]) -> None:
    """Prints complete final facts and round-end progression for one list."""
    summary = result["fixed_three_player_historical_list_summary"]
    print("Fixed three-player historical list summary")
    print("List ID:", summary["list_id"])
    print(f"Positions: {summary['entry_count']}; rounds: {summary['round_count']}")
    print(
        "Entries:",
        f"{summary['played_game_count']} Played Games; "
        f"{summary['passed_deal_count']} Passed Deals",
    )
    print(
        "Declarer results:",
        f"{summary['declarer_win_count']} wins; "
        f"{summary['declarer_loss_count']} losses",
    )
    print("Ranking status:", summary["ranking_status"])
    if summary["ranking_status"] == "lot_required":
        print(
            "Unresolved tie; external lot required:",
            ", ".join(summary["lot_required_player_ids"]),
        )
    elif summary["applied_lot_order"] is not None:
        print("Applied external lot:", ", ".join(summary["applied_lot_order"]))
    else:
        print("External lot: not required")

    print("Final standings")
    for standing in summary["final_standings"]:
        totals = standing["player_totals"]
        print(
            f"Rank {standing['rank']}: "
            f"{_format_list_player_identity(totals['player_id'], totals['player_label'])}; "
            f"table place {totals['table_place']}; "
            f"total performance points {totals['total_performance_points']}; "
            f"game points {totals['player_game_points']}; "
            f"own-game bonus {totals['own_game_bonus_points']}; "
            f"opponent-loss bonus {totals['opponent_loss_bonus_points']}; "
            f"own wins {totals['own_games_won']}; own losses {totals['own_games_lost']}; "
            f"Played Games {totals['played_game_count']}; "
            f"Passed Deals {totals['passed_deal_count']}."
        )

    print("Round-end progression")
    for snapshot in summary["progression"][2::3]:
        standings_text = ", ".join(
            f"rank {standing['rank']} {standing['player_totals']['player_id']} "
            f"{standing['player_totals']['total_performance_points']}"
            for standing in snapshot["provisional_standings"]
        )
        print(
            f"Entry {snapshot['entry_fact']['entry_number']} "
            f"(round {snapshot['entry_fact']['round_number']}): {standings_text}."
        )


def _print_comparison_source_summary(summary: dict[str, Any]) -> None:
    print(
        f"Source list {summary['list_id']}: {summary['entry_count']} positions, "
        f"{summary['played_game_count']} Played Games, "
        f"{summary['passed_deal_count']} Passed Deals, "
        f"{summary['declarer_win_count']} declarer wins, "
        f"{summary['declarer_loss_count']} declarer losses; "
        f"ranking status {summary['ranking_status']}."
    )
    for standing in summary["final_standings"]:
        print(
            f"  Rank {standing['rank']}: "
            f"{_format_list_player_identity(standing['player_id'], standing['player_label'])}; "
            f"table place {standing['table_place']}; "
            f"total performance points {standing['total_performance_points']}; "
            f"own wins {standing['own_games_won']}; own losses {standing['own_games_lost']}."
        )


def print_fixed_three_player_historical_list_comparison_result(
    result: dict[str, Any],
) -> None:
    """Prints compact independent-list sources and comparison-minus-reference deltas."""
    summary = result["fixed_three_player_historical_list_comparison_summary"]
    print("Fixed three-player historical list comparison")
    print("Reference list:", summary["reference_list_id"])
    print("Source-list count:", summary["list_count"])
    print("Source summaries")
    for source in summary["source_lists"]:
        _print_comparison_source_summary(source)

    delta_labels = (
        ("list_entry_count", "list entries"),
        ("played_game_count", "Played Games"),
        ("passed_deal_count", "Passed Deals"),
        ("declarer_game_count", "declarer games"),
        ("defender_game_count", "defender games"),
        ("own_games_won", "own wins"),
        ("own_games_lost", "own losses"),
        ("defender_games_won", "defender wins"),
        ("defender_games_lost", "defender losses"),
        ("other_players_lost_games", "other-player losses"),
        ("player_game_points", "game points"),
        ("own_game_bonus_points", "own-game bonus"),
        ("opponent_loss_bonus_points", "opponent-loss bonus"),
        ("total_performance_points", "total performance points"),
    )
    for comparison in summary["comparisons"]:
        print(
            f"Comparison list {comparison['comparison_list_id']} against "
            f"{comparison['reference_list_id']}"
        )
        print(
            "List-count deltas (comparison - reference): "
            f"Played Games {comparison['played_game_count_delta']:+d}; "
            f"Passed Deals {comparison['passed_deal_count_delta']:+d}; "
            f"declarer wins {comparison['declarer_win_count_delta']:+d}; "
            f"declarer losses {comparison['declarer_loss_count_delta']:+d}."
        )
        for player in comparison["player_comparisons"]:
            identity = _format_list_player_identity(
                player["player_id"],
                player["player_label"],
            )
            print(
                f"Player {identity}: "
                f"reference table place {player['reference_table_place']}; "
                f"comparison table place {player['comparison_table_place']}."
            )
            print(
                "  Metric deltas (comparison - reference): "
                + "; ".join(
                    f"{label} {player['deltas'][field_name]:+d}"
                    for field_name, label in delta_labels
                )
                + "."
            )
            print("  Rank status:", player["rank_comparison_status"])
            if player["rank_comparison_status"] == "available":
                print(
                    f"  Reference rank {player['reference_rank']}; "
                    f"comparison rank {player['comparison_rank']}; "
                    f"rank-position change {player['rank_position_change']:+d}."
                )
            else:
                print("  Rank-position change: unavailable while a lot remains unresolved.")
