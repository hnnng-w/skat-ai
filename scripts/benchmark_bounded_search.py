from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from itertools import permutations
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "benchmarks" / "bounded_search_late_game_v1.json"
SUPPORTED_CORPUS_SCHEMA_VERSION = 1


def _load_corpus(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        corpus = json.load(file)

    from skat_ai.search_budget_profiles import SEARCH_BUDGET_PROFILE_IDENTIFIERS

    if corpus.get("schema_version") != SUPPORTED_CORPUS_SCHEMA_VERSION:
        raise ValueError("Unsupported bounded-search benchmark corpus schema version.")
    if not isinstance(corpus.get("corpus_name"), str) or not corpus["corpus_name"]:
        raise ValueError("Benchmark corpus_name must be a non-empty string.")
    cases = corpus.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark corpus cases must be a non-empty array.")

    names = [case.get("name") for case in cases]
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("Every benchmark case requires a non-empty name.")
    if len(names) != len(set(names)):
        raise ValueError("Benchmark case names must be unique.")

    for case in cases:
        profile_name = case.get("profile_name")
        if profile_name not in SEARCH_BUDGET_PROFILE_IDENTIFIERS:
            raise ValueError(f"Unknown benchmark profile_name: {profile_name!r}.")
        declaration = case.get("declaration")
        position = case.get("position")
        expected = case.get("expected_result")
        if not isinstance(declaration, dict) or not isinstance(position, dict):
            raise ValueError(f"Benchmark case {case['name']!r} requires declaration and position.")
        if not isinstance(expected, dict):
            raise ValueError(f"Benchmark case {case['name']!r} requires expected_result.")

    return corpus


def _build_information_view(case: dict[str, Any]) -> Any:
    from skat_ai.bounded_search_information import (
        SearchCompletedTrick,
        SearchPublicPlay,
        build_live_search_information_view,
    )
    from skat_ai.deck import get_full_deck
    from skat_ai.game_declaration import GameDeclaration
    from skat_ai.game_state import GameState
    from skat_ai.hidden_card_inference import (
        EFFECTIVE_CATEGORY_ORDER,
        get_public_effective_category,
    )
    from skat_ai.rules import get_trick_points, get_trick_winner

    declaration = GameDeclaration(**case["declaration"])
    position = case["position"]
    local_hand = tuple(position["local_hand"])
    hidden_cards = tuple(position["hidden_cards"])
    current_trick = tuple(tuple(play) for play in position["current_trick"])
    unresolved_cards = {
        *local_hand,
        *hidden_cards,
        *(card for _, card in current_trick),
    }
    completed_cards = tuple(card for card in get_full_deck() if card not in unresolved_cards)
    cards_by_category = {
        category: [
            card
            for card in completed_cards
            if get_public_effective_category(card, declaration.game_type) == category
        ]
        for category in EFFECTIVE_CATEGORY_ORDER
    }
    card_groups = []
    for category_cards in cards_by_category.values():
        if len(category_cards) % 3:
            raise ValueError(
                f"Benchmark case {case['name']!r} cannot form full-follow completed tricks."
            )
        card_groups.extend(
            tuple(category_cards[index : index + 3])
            for index in range(0, len(category_cards), 3)
        )
    card_groups = tuple(card_groups)
    point_values = tuple(get_trick_points(group) for group in card_groups)
    required_final_winner = current_trick[0][0] if current_trick else "me"
    winner_mask = next(
        mask
        for mask in range(1 << len(card_groups))
        if sum(
            points for index, points in enumerate(point_values) if mask & (1 << index)
        )
        == position["declarer_points"]
        and (
            ("me" if mask & (1 << (len(card_groups) - 1)) else "left")
            == required_final_winner
        )
    )
    players = ("me", "left", "right")
    leader = "left"
    completed_trick_rows = []
    for index, group in enumerate(card_groups):
        winner_player = "me" if winner_mask & (1 << index) else "left"
        leader_index = players.index(leader)
        play_order = players[leader_index:] + players[:leader_index]
        ordered_cards = next(
            ordered
            for ordered in permutations(group)
            if play_order[get_trick_winner(list(ordered), declaration.game_type)]
            == winner_player
        )
        completed_trick_rows.append(
            SearchCompletedTrick(
                plays=tuple(
                    SearchPublicPlay(player, card)
                    for player, card in zip(play_order, ordered_cards, strict=True)
                ),
                winner_player=winner_player,
                winner_side="declarer" if winner_player == "me" else "defenders",
                trick_points=point_values[index],
            )
        )
        leader = winner_player
    if leader != required_final_winner:
        raise AssertionError("Completed benchmark prefix has an inconsistent next leader.")
    completed_tricks = tuple(completed_trick_rows)
    completed_points = get_trick_points(completed_cards)
    declarer_points = position["declarer_points"]
    current_players = {player for player, _ in current_trick}
    remaining_tricks = len(local_hand)
    state = GameState(
        game_type=declaration.game_type,
        player_role="declarer",
        declarer_player="me",
        hand=list(local_hand),
        current_trick=[card for _, card in current_trick],
        played_cards=[],
        completed_tricks=[
            {
                "cards": [play.card for play in trick.plays],
                "players": [play.player for play in trick.plays],
                "winner_player": trick.winner_player,
                "winner_role": trick.winner_side,
            }
            for trick in completed_tricks
        ],
        declarer_points=0,
        defender_points=0,
        trick_leader=current_trick[0][0] if current_trick else "me",
        next_player="me",
    )
    information_view = build_live_search_information_view(
        state=state,
        declaration=declaration,
        left_hand_size=remaining_tricks - int("left" in current_players),
        right_hand_size=remaining_tricks - int("right" in current_players),
    )
    if information_view.declarer_points != declarer_points:
        raise AssertionError("Benchmark declarer points changed while building the live view.")
    if information_view.defender_points != completed_points - declarer_points:
        raise AssertionError("Benchmark defender points changed while building the live view.")
    return information_view


def _functional_result(result: Any) -> dict[str, Any]:
    consumed = result.consumed_budget
    return {
        "status": result.status,
        "stop_reason": result.stop_reason,
        "world_coverage": result.world_coverage,
        "recommended_card": result.recommended_card,
        "compatible_world_count": result.compatible_world_count,
        "depth_reached": consumed.depth_reached,
        "nodes_expanded": consumed.nodes_expanded,
        "selected_world_count": consumed.selected_world_count,
        "completed_world_count": consumed.completed_world_count,
        "sampled_world_count": consumed.sampled_world_count,
    }


def _execute_case(case: dict[str, Any], information_view: Any) -> tuple[dict[str, Any], float]:
    from skat_ai.compatible_world_minimax import solve_compatible_world_minimax
    from skat_ai.search_budget_profiles import get_search_budget_profile

    started_at = time.perf_counter_ns()
    result = solve_compatible_world_minimax(
        information_view=information_view,
        requested_budget=get_search_budget_profile(case["profile_name"]),
        random_seed=case["random_seed"],
    )
    elapsed_ms = (time.perf_counter_ns() - started_at) / 1_000_000
    functional = _functional_result(result)
    if functional != case["expected_result"]:
        raise AssertionError(
            f"Functional result changed for {case['name']!r}: "
            f"expected {case['expected_result']!r}, got {functional!r}"
        )
    return functional, elapsed_ms


def _metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "minimum": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "mean": round(statistics.fmean(values), 3),
        "maximum": round(max(values), 3),
    }


def run_benchmark(
    *,
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    warmup_run_count: int = 1,
    measured_run_count: int = 5,
) -> dict[str, Any]:
    if warmup_run_count < 0:
        raise ValueError("warmup_run_count must be non-negative.")
    if measured_run_count < 2:
        raise ValueError("measured_run_count must be at least 2.")

    corpus = _load_corpus(corpus_path)
    case_outputs = []
    all_elapsed_ms = []
    all_nodes = []
    for case in corpus["cases"]:
        information_view = _build_information_view(case)
        for _ in range(warmup_run_count):
            _execute_case(case, information_view)

        runs = []
        signatures = []
        for run_number in range(1, measured_run_count + 1):
            functional, elapsed_ms = _execute_case(case, information_view)
            signatures.append(functional)
            all_elapsed_ms.append(elapsed_ms)
            all_nodes.append(functional["nodes_expanded"])
            runs.append(
                {
                    "run_number": run_number,
                    "elapsed_ms": round(elapsed_ms, 3),
                    "nodes_expanded": functional["nodes_expanded"],
                }
            )
        if any(signature != signatures[0] for signature in signatures[1:]):
            raise AssertionError(f"Measured functional results varied for {case['name']!r}.")

        elapsed_values = [run["elapsed_ms"] for run in runs]
        node_values = [run["nodes_expanded"] for run in runs]
        case_outputs.append(
            {
                "case_name": case["name"],
                "game_type": case["declaration"]["game_type"],
                "profile_name": case["profile_name"],
                "random_seed": case["random_seed"],
                "functional_result": signatures[0],
                "deterministic_across_measured_runs": True,
                "timing_ms": _metric_summary(elapsed_values),
                "nodes_expanded": {
                    **_metric_summary(node_values),
                    "deterministic": len(set(node_values)) == 1,
                },
                "runs": runs,
            }
        )

    return {
        "schema_version": 1,
        "benchmark_name": "bounded_search_compatible_world_performance_v1",
        "corpus": {
            "name": corpus["corpus_name"],
            "path": str(corpus_path.resolve()),
        },
        "profile_names": list(dict.fromkeys(case["profile_name"] for case in corpus["cases"])),
        "warmup_run_count": warmup_run_count,
        "measured_run_count": measured_run_count,
        "environment": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_executable": sys.executable,
        },
        "cases": case_outputs,
        "aggregate": {
            "measured_execution_count": len(all_elapsed_ms),
            "timing_ms": {
                **_metric_summary(all_elapsed_ms),
                "total": round(sum(all_elapsed_ms), 3),
            },
            "nodes_expanded": {
                **_metric_summary(all_nodes),
                "total": sum(all_nodes),
            },
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark deterministic late-game compatible-world bounded Search."
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--runs", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output = run_benchmark(
        corpus_path=args.corpus,
        warmup_run_count=args.warmup_runs,
        measured_run_count=args.runs,
    )
    json.dump(output, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
