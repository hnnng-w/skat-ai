"""Multi-step and policy-comparison presentation."""

from typing import Any

from skat_ai.cli.presentation.common import print_hidden_card_inference_summary


def print_multi_step_result(result: dict[str, Any]) -> None:
    """Prints a multi-step simulation result in a readable text format."""
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
    print_hidden_card_inference_summary(result.get("hidden_card_inference_summary"))
    if "opponent_policy_settings" in result:
        print(
            "Opponent lead policy:",
            result["opponent_policy_settings"]["opponent_lead_policy"],
        )
        print(
            "Opponent response policy:",
            result["opponent_policy_settings"]["opponent_response_policy"],
        )
    if "context_summary" in result:
        context_summary = result["context_summary"]
        duplicate_cards = context_summary["duplicate_simulated_opponent_cards"]

        print("Context summary:", context_summary)

        hidden_world_summary = context_summary.get("hidden_world")
        if hidden_world_summary is not None:
            print("Hidden-world mode:", hidden_world_summary["mode"])
            print("Hidden world sampled once:", hidden_world_summary["sampled_once"])
            print(
                "Hidden world resampled after path start:",
                hidden_world_summary["resampled_after_path_start"],
            )
            print(
                "Hidden-world ownership preserved:",
                hidden_world_summary["ownership_preserved"],
            )

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

        decision = step.get("recommendation_decision")
        if decision is not None:
            if isinstance(decision, dict):
                search = decision["bounded_search_result"]
                consumed = search["consumed_budget"]
                requested_method = decision["requested_method"]
                effective_method = decision["effective_method"]
                search_status = search["status"]
                search_stop_reason = search["stop_reason"]
                completed_world_count = consumed["completed_world_count"]
                selected_world_count = consumed["selected_world_count"]
                fallback_used = decision["fallback_used"]
                fallback_method = decision["fallback_method"]
                recommendation_card = decision["recommendation_card"]
            else:
                search = decision.bounded_search_result
                consumed = search.consumed_budget
                requested_method = decision.requested_method
                effective_method = decision.effective_method
                search_status = search.status
                search_stop_reason = search.stop_reason
                completed_world_count = consumed.completed_world_count
                selected_world_count = consumed.selected_world_count
                fallback_used = decision.fallback_used
                fallback_method = decision.fallback_method
                recommendation_card = decision.recommendation_card
            print("Requested recommendation method:", requested_method)
            print("Effective recommendation method:", effective_method)
            print("Search status:", search_status)
            print("Search stop reason:", search_stop_reason)
            print(
                "Search completed worlds:",
                f"{completed_world_count} of {selected_world_count}",
            )
            if fallback_used:
                print("Fallback method:", fallback_method)
                print("Fallback chosen card:", recommendation_card)
            else:
                print("Search chosen card:", recommendation_card)

        if opponent_lead_result is not None:
            print("Opponent lead player:", opponent_lead_result["leader"])
            print("Opponent lead card:", opponent_lead_result["lead_card"])

            if "responder" in opponent_lead_result:
                print("Opponent response player:", opponent_lead_result["responder"])
                print("Opponent response card:", opponent_lead_result["response_card"])

        print("Candidate card:", step["candidate_card"])
        print("Trick:", detailed_result["trick"])
        print("Did win:", detailed_result["did_win"])
        if "candidate_card_won" in detailed_result:
            print("Candidate card won:", detailed_result["candidate_card_won"])
        if "local_side_won" in detailed_result:
            print("Local side won:", detailed_result["local_side_won"])
        print("Trick points:", detailed_result["trick_points"])
        print("Winner role:", completed_trick["winner_role"])

    stopped_decision = result.get("stopped_recommendation_decision")
    if stopped_decision is not None:
        if isinstance(stopped_decision, dict):
            search = stopped_decision["bounded_search_result"]
            consumed = search["consumed_budget"]
            step_index = stopped_decision["step_index"]
            requested_method = stopped_decision["requested_method"]
            effective_method = stopped_decision["effective_method"]
            search_status = search["status"]
            search_stop_reason = search["stop_reason"]
            completed_world_count = consumed["completed_world_count"]
            selected_world_count = consumed["selected_world_count"]
        else:
            search = stopped_decision.bounded_search_result
            consumed = search.consumed_budget
            step_index = stopped_decision.step_index
            requested_method = stopped_decision.requested_method
            effective_method = stopped_decision.effective_method
            search_status = search.status
            search_stop_reason = search.stop_reason
            completed_world_count = consumed.completed_world_count
            selected_world_count = consumed.selected_world_count
        print()
        print("Stopped recommendation decision:", step_index)
        print("Requested recommendation method:", requested_method)
        print("Effective recommendation method:", effective_method)
        print("Search status:", search_status)
        print("Search stop reason:", search_stop_reason)
        print(
            "Search completed worlds:",
            f"{completed_world_count} of {selected_world_count}",
        )
        print("No local recommendation was available; no local card was executed.")

    print()
    print("Final state")
    if isinstance(final_state, dict):
        print("Remaining hand:", final_state["hand"])
        print("Completed tricks:", final_state["completed_tricks"])
        print("Declarer points:", final_state["declarer_points"])
        print("Defender points:", final_state["defender_points"])
        print("Next player:", final_state["next_player"])
    else:
        print("Remaining hand:", final_state.hand)
        print("Completed tricks:", final_state.completed_tricks)
        print("Declarer points:", final_state.declarer_points)
        print("Defender points:", final_state.defender_points)
        print("Next player:", final_state.next_player)


def print_policy_comparison_result(result: dict[str, Any]) -> None:
    """Prints a compact policy comparison result."""
    print()
    print("Policy comparison")
    print("Requested steps:", result["requested_step_count"])
    print("Random seed:", result["random_seed"])
    print("Expected-value samples:", result["expected_value_sample_count"])
    print("Use basic opponent strategy:", result["use_basic_opponent_strategy"])
    print("Strict context:", result["strict_context"])
    print("Opponent lead policy:", result.get("opponent_lead_policy", "lowest_point"))
    print(
        "Opponent response policy:",
        result.get("opponent_response_policy", "lowest_point"),
    )
    if "hidden_world" in result:
        hidden_world_summary = result["hidden_world"]
        print("Hidden-world mode:", hidden_world_summary["mode"])
        print("Policies shared one root world:", hidden_world_summary["shared_root_world"])
        print(
            "Policy paths use independent worlds:",
            hidden_world_summary["independent_path_worlds"],
        )
    print_hidden_card_inference_summary(result.get("hidden_card_inference_summary"))

    print()
    print(f"{'Policy':<24}{'Steps':>7}{'Decl. +':>10}{'Def. +':>10}{'Swing':>10}{'Local':>10}")
    print("-" * 71)

    for policy_result in result["policy_results"]:
        local_point_swing = policy_result.get(
            "local_point_swing",
            policy_result["final_point_swing"],
        )
        print(
            f"{policy_result['policy']:<24}"
            f"{policy_result['steps_simulated']:>7}"
            f"{policy_result['declarer_points_gained']:>10}"
            f"{policy_result['defender_points_gained']:>10}"
            f"{policy_result['final_point_swing']:>10}"
            f"{local_point_swing:>10}"
        )
        if "recommendation_summary" in policy_result:
            recommendation_summary = policy_result["recommendation_summary"]
            print(
                "  Search decisions: "
                f"{recommendation_summary['decisions_attempted']} attempted, "
                f"{recommendation_summary['decisions_executed']} executed, "
                f"{recommendation_summary['search_recommendations_used']} Search, "
                f"{recommendation_summary['immediate_fallbacks_used']} fallback, "
                f"{recommendation_summary['no_recommendation_count']} no recommendation"
            )
        if "eligible_for_recommendation" in policy_result:
            print(
                "  Eligible for recommendation:",
                policy_result["eligible_for_recommendation"],
            )
            if policy_result["ineligible_reason"] is not None:
                print("  Ineligible reason:", policy_result["ineligible_reason"])

    recommended_policy = result.get("recommended_policy")
    print()

    if recommended_policy is not None:
        print("Recommended policy:", recommended_policy["policy"])
        print("Recommendation reason:", recommended_policy["reason"])
        print("Recommended final point swing:", recommended_policy["final_point_swing"])
        print(
            "Recommended local point swing:",
            recommended_policy.get(
                "local_point_swing",
                recommended_policy["final_point_swing"],
            ),
        )
    else:
        print("Recommended policy: none")


def print_multi_step_score_summary(summary: dict[str, Any]) -> None:
    """Prints a compact multi-step score summary."""
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
    if "local_point_swing" in score_summary:
        print("Local point swing:", score_summary["local_point_swing"])
