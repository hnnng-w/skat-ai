import argparse
from typing import Any

from skat_ai.analysis_report import (
    build_card_analysis_report,
    build_strategic_summary,
    format_card_analysis_report,
)
from skat_ai.card_selection import VALID_CARD_SELECTION_POLICIES
from skat_ai.game_history import build_score_summary
from skat_ai.input_loader import (
    build_game_state_from_input,
    get_simulation_settings_from_input,
    load_position_from_json,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.output_writer import write_analysis_result_to_json
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.rules import get_legal_cards


def apply_cli_overrides(
    settings: dict[str, Any],
    sample_count: int | None,
    random_seed: int | None,
    opponent_strategy: str | None,
) -> dict[str, Any]:
    """
    Applies optional command-line overrides to simulation settings.
    """
    updated_settings = settings.copy()

    if sample_count is not None:
        updated_settings["sample_count"] = sample_count

    if random_seed is not None:
        updated_settings["random_seed"] = random_seed

    if opponent_strategy == "basic":
        updated_settings["use_basic_opponent_strategy"] = True

    if opponent_strategy == "random":
        updated_settings["use_basic_opponent_strategy"] = False

    return updated_settings


def build_analysis_result(
    file_path: str,
    sample_count_override: int | None = None,
    random_seed_override: int | None = None,
    opponent_strategy_override: str | None = None,
) -> dict[str, Any]:
    """
    Builds the full analysis result as a structured dictionary.
    """
    data = load_position_from_json(file_path)
    state = build_game_state_from_input(data)
    settings = get_simulation_settings_from_input(data)

    settings = apply_cli_overrides(
        settings=settings,
        sample_count=sample_count_override,
        random_seed=random_seed_override,
        opponent_strategy=opponent_strategy_override,
    )

    legal_cards = get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )

    recommended_card, reason, _ = recommend_card_by_expected_value(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        sample_count=settings["sample_count"],
        random_seed=settings["random_seed"],
        use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        sample_count=settings["sample_count"],
        random_seed=settings["random_seed"],
        use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
    )

    strategic_summary = build_strategic_summary(report)

    score_summary = build_score_summary(state)

    return {
        "input_file": file_path,
        "position": {
            "game_type": state.game_type,
            "player_role": state.player_role,
            "player_position": state.player_position,
            "trick_leader": state.trick_leader,
            "hand": state.hand,
            "current_trick": state.current_trick,
            "played_cards": state.played_cards,
            "completed_tricks": state.completed_tricks,
            "declarer_points": state.declarer_points,
            "defender_points": state.defender_points,
            "next_player": state.next_player,
            "skat": state.skat,
        },
        "settings": settings,
        "legal_cards": legal_cards,
        "analysis_report": report,
        "strategic_summary": strategic_summary,
        "score_summary": score_summary,
        "recommendation": {
            "card": recommended_card,
            "reason": reason,
        },
    }


def print_analysis_result(result: dict[str, Any]) -> None:
    """
    Prints the analysis result in a readable text format.
    """
    position = result["position"]
    settings = result["settings"]
    score_summary = result["score_summary"]

    print("JSON position analysis")
    print("Input file:", result["input_file"])
    print("Game type:", position["game_type"])
    print("Player role:", position["player_role"])
    print("Player position:", position["player_position"])
    print("Trick leader:", position["trick_leader"])
    print("Hand:", position["hand"])
    print("Current trick:", position["current_trick"])
    print("Played cards:", position["played_cards"])
    print("Skat:", position["skat"])
    print("Completed tricks:", position["completed_tricks"])
    print("Declarer points:", position["declarer_points"])
    print("Defender points:", position["defender_points"])
    print("Next player:", position["next_player"])
    print("Legal cards:", result["legal_cards"])
    print("Left hand size:", settings["left_hand_size"])
    print("Right hand size:", settings["right_hand_size"])
    print("Sample count:", settings["sample_count"])
    print("Random seed:", settings["random_seed"])
    print("Use basic opponent strategy:", settings["use_basic_opponent_strategy"])

    print()
    print("Score summary")
    print("Explicit declarer points:", score_summary["explicit_declarer_points"])
    print("Explicit defender points:", score_summary["explicit_defender_points"])
    print(
        "Completed-trick declarer points:",
        score_summary["completed_trick_declarer_points"],
    )
    print(
        "Completed-trick defender points:",
        score_summary["completed_trick_defender_points"],
    )
    print("Total declarer points:", score_summary["total_declarer_points"])
    print("Total defender points:", score_summary["total_defender_points"])

    print()
    print(format_card_analysis_report(result["analysis_report"]))

    print()
    print(result["strategic_summary"])

    print()
    print("Recommended card:", result["recommendation"]["card"])
    print("Reason:", result["recommendation"]["reason"])


def print_multi_step_result(result: dict[str, Any]) -> None:
    """
    Prints a multi-step simulation result in a readable text format.
    """
    final_state = result["final_state"]
    steps = result["steps"]

    if "summary" in result:
        print_multi_step_score_summary(result["summary"])

    print()
    print("Multi-step simulation")
    print("Card selection policy:", result["card_selection_policy"])
    print("Requested steps:", result.get("requested_step_count", len(steps)))
    print("Steps simulated:", result.get("steps_simulated", len(steps)))
    print("Stop reason:", result.get("stop_reason", "unknown"))
    if "context_summary" in result:
        context_summary = result["context_summary"]
        duplicate_cards = context_summary["duplicate_simulated_opponent_cards"]

        print("Context summary:", context_summary)

        if duplicate_cards:
            print(
                "Context warning: duplicate simulated opponent cards detected:",
                duplicate_cards,
            )
        else:
            print("Context warning: none")

    for step in steps:
        detailed_result = step["detailed_result"]
        completed_trick = detailed_result["completed_trick"]
        opponent_lead_result = step.get("opponent_lead_result")

        print()
        print("Step:", step["step_index"])

        if opponent_lead_result is not None:
            print("Opponent lead player:", opponent_lead_result["leader"])
            print("Opponent lead card:", opponent_lead_result["lead_card"])

            if "responder" in opponent_lead_result:
                print("Opponent response player:", opponent_lead_result["responder"])
                print("Opponent response card:", opponent_lead_result["response_card"])

        print("Candidate card:", step["candidate_card"])
        print("Trick:", detailed_result["trick"])
        print("Did win:", detailed_result["did_win"])
        print("Trick points:", detailed_result["trick_points"])
        print("Winner role:", completed_trick["winner_role"])

    print()
    print("Final state")
    print("Remaining hand:", final_state.hand)
    print("Completed tricks:", final_state.completed_tricks)
    print("Declarer points:", final_state.declarer_points)
    print("Defender points:", final_state.defender_points)
    print("Next player:", final_state.next_player)


def print_multi_step_score_summary(summary: dict[str, Any]) -> None:
    """
    Prints a compact multi-step score summary.
    """
    score_summary = summary["score_summary"]

    print()
    print("Multi-step score summary")
    print("Requested steps:", summary["requested_step_count"])
    print("Steps simulated:", summary["steps_simulated"])
    print("Stop reason:", summary["stop_reason"])
    print("Card selection policy:", summary["card_selection_policy"])
    print("Strict context:", summary["strict_context"])
    print("Initial declarer points:", score_summary["initial_declarer_points"])
    print("Initial defender points:", score_summary["initial_defender_points"])
    print("Final declarer points:", score_summary["final_declarer_points"])
    print("Final defender points:", score_summary["final_defender_points"])
    print("Declarer points gained:", score_summary["declarer_points_gained"])
    print("Defender points gained:", score_summary["defender_points_gained"])
    print("Final point swing:", score_summary["final_point_swing"])


def run_json_position_analysis(
    file_path: str,
    sample_count_override: int | None = None,
    random_seed_override: int | None = None,
    opponent_strategy_override: str | None = None,
    output_path: str | None = None,
    multi_step_count: int | None = None,
    card_selection_policy: str = "first_legal",
    expected_value_sample_count: int = 100,
    strict_context: bool = False,
) -> None:
    result = build_analysis_result(
        file_path=file_path,
        sample_count_override=sample_count_override,
        random_seed_override=random_seed_override,
        opponent_strategy_override=opponent_strategy_override,
    )

    print_analysis_result(result)

    if multi_step_count is not None:
        if multi_step_count <= 0:
            raise ValueError("multi_step_count must be a positive integer.")

        position_data = load_position_from_json(file_path)
        state = build_game_state_from_input(position_data)
        settings = get_simulation_settings_from_input(position_data)

        settings = apply_cli_overrides(
            settings=settings,
            sample_count=sample_count_override,
            random_seed=random_seed_override,
            opponent_strategy=opponent_strategy_override,
        )

        multi_step_result = simulate_multiple_steps(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            step_count=multi_step_count,
            random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
            card_selection_policy=card_selection_policy,
            expected_value_sample_count=expected_value_sample_count,
            strict_context=strict_context,
        )

        result["multi_step_result"] = {
            "card_selection_policy": multi_step_result["card_selection_policy"],
            "requested_step_count": multi_step_result["requested_step_count"],
            "steps_simulated": multi_step_result["steps_simulated"],
            "stop_reason": multi_step_result["stop_reason"],
            "strict_context": multi_step_result["strict_context"],
            "summary": multi_step_result["summary"],
            "context_summary": multi_step_result["context_summary"],
            "steps": [
                {
                    "step_index": step["step_index"],
                    "opponent_lead_result": (
                        {
                            "leader": step["opponent_lead_result"]["leader"],
                            "lead_card": step["opponent_lead_result"]["lead_card"],
                            "responder": step["opponent_lead_result"].get("responder"),
                            "response_card": step["opponent_lead_result"].get("response_card"),
                        }
                        if step["opponent_lead_result"] is not None
                        else None
                    ),
                    "candidate_card": step["candidate_card"],
                    "card_selection_policy": step["card_selection_policy"],
                    "detailed_result": step["detailed_result"],
                }
                for step in multi_step_result["steps"]
            ],
            "final_state": {
                "hand": multi_step_result["final_state"].hand,
                "current_trick": multi_step_result["final_state"].current_trick,
                "completed_tricks": multi_step_result["final_state"].completed_tricks,
                "declarer_points": multi_step_result["final_state"].declarer_points,
                "defender_points": multi_step_result["final_state"].defender_points,
                "next_player": multi_step_result["final_state"].next_player,
            },
        }

        print_multi_step_result(multi_step_result)

    if output_path is not None:
        write_analysis_result_to_json(
            output_path=output_path,
            result=result,
        )
        print()
        print("Output file written:", output_path)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a Skat position from a JSON input file.",
    )

    parser.add_argument(
        "--input",
        default="input_position.json",
        help="Path to the JSON input file. Default: input_position.json",
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Override sample_count from the JSON input file.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random_seed from the JSON input file.",
    )

    parser.add_argument(
        "--opponent-strategy",
        choices=["basic", "random"],
        default=None,
        help="Override opponent strategy from the JSON input file. Choices: basic, random.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write the analysis result as JSON.",
    )

    parser.add_argument(
        "--multi-step",
        type=int,
        default=None,
        help="Optionally run a multi-step simulation with the given number of steps.",
    )

    parser.add_argument(
        "--card-policy",
        choices=VALID_CARD_SELECTION_POLICIES,
        default="first_legal",
        help="Card-selection policy for multi-step simulation.",
    )

    parser.add_argument(
        "--expected-value-samples",
        type=int,
        default=100,
        help="Sample count used by the highest_expected_value card policy.",
    )

    parser.add_argument(
        "--strict-context",
        action="store_true",
        help="Fail if duplicate simulated opponent cards are detected.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    try:
        run_json_position_analysis(
            file_path=args.input,
            sample_count_override=args.samples,
            random_seed_override=args.seed,
            opponent_strategy_override=args.opponent_strategy,
            output_path=args.output,
            multi_step_count=args.multi_step,
            card_selection_policy=args.card_policy,
            expected_value_sample_count=args.expected_value_samples,
            strict_context=args.strict_context,
        )
    except (ValueError, FileNotFoundError) as error:
        print("Input error:", error)


if __name__ == "__main__":
    main()