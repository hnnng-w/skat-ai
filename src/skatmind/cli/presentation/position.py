"""Position-analysis and game-ending presentation."""

from typing import Any

from skatmind.analysis_report import format_card_analysis_report
from skatmind.cli.presentation.common import (
    format_decision_factors,
    format_optional_cli_value,
    format_post_game_review_unavailable_reason,
    print_hidden_card_inference_summary,
)
from skatmind.objective_utility import calculate_expected_objective_utility


def is_null_review_result(result: dict[str, object]) -> bool:
    """Returns whether the CLI review output should use Null objective wording."""
    position = result.get("position")

    return isinstance(position, dict) and position.get("game_type") == "null"


def get_analysis_report_row_for_cli(
    result: dict[str, object],
    card: object,
) -> dict[str, object] | None:
    """Returns an analysis-report row for CLI-only presentation calculations."""
    analysis_report = result.get("analysis_report")

    if not isinstance(card, str) or not isinstance(analysis_report, list):
        return None

    for row in analysis_report:
        if isinstance(row, dict) and row.get("card") == card:
            return row

    return None


def calculate_missed_null_objective_gap_for_cli(
    result: dict[str, object],
    summary: dict[str, object],
) -> float | None:
    """Calculates the displayed Null objective gap without changing JSON output."""
    position = result.get("position")
    game_value_summary = result.get("game_value_summary")

    if not isinstance(position, dict) or not isinstance(game_value_summary, dict):
        return None

    actual_row = get_analysis_report_row_for_cli(
        result=result,
        card=summary.get("actual_card_played"),
    )
    recommended_row = get_analysis_report_row_for_cli(
        result=result,
        card=summary.get("recommended_card"),
    )

    if actual_row is None or recommended_row is None:
        return None

    try:
        actual_objective_utility = calculate_expected_objective_utility(
            game_type="null",
            player_role=str(position["player_role"]),
            value=actual_row,
        )
        recommended_objective_utility = calculate_expected_objective_utility(
            game_type="null",
            player_role=str(position["player_role"]),
            value=recommended_row,
        )
        game_value = float(game_value_summary["game_value"])
    except (KeyError, TypeError, ValueError):
        return None

    return max(
        0.0,
        (recommended_objective_utility - actual_objective_utility) * game_value,
    )


def print_post_game_review_rank_summary(summary: dict[str, object]) -> None:
    """Prints concise rank and better-alternative wording for review output."""
    candidate_count = format_optional_cli_value(summary.get("candidate_count"))
    actual_rank = format_optional_cli_value(summary.get("actual_card_rank"))
    recommended_rank = format_optional_cli_value(summary.get("recommended_card_rank"))
    actual_rank_text = actual_rank
    recommended_rank_text = recommended_rank

    if summary.get("actual_card_rank") is not None:
        actual_rank_text = f"{actual_rank} of {candidate_count}"

    if summary.get("recommended_card_rank") is not None:
        recommended_rank_text = f"{recommended_rank} of {candidate_count}"

    print(
        "Review ranks: "
        f"actual {actual_rank_text}; "
        f"recommended {recommended_rank_text}; "
        f"better alternatives {format_optional_cli_value(summary.get('better_card_count'))}."
    )

    better_card_count = summary.get("better_card_count")

    if better_card_count is None:
        print("Better alternatives: not available.")
        return

    if better_card_count == 0:
        print("Actual card is best-ranked by the review objective.")
        return

    suffix = "" if better_card_count == 1 else "s"
    print(
        f"Actual card has {better_card_count} better alternative{suffix} by the review objective."
    )


def print_post_game_review_value_summary(
    result: dict[str, object],
    summary: dict[str, object],
) -> None:
    """Prints point or objective-gap wording for post-game review output."""
    actual_expected_point_swing = float(summary["actual_expected_point_swing"])
    recommended_expected_point_swing = float(summary["recommended_expected_point_swing"])
    expected_point_swing_difference = float(summary["expected_point_swing_difference"])

    if is_null_review_result(result):
        missed_objective_gap = calculate_missed_null_objective_gap_for_cli(
            result=result,
            summary=summary,
        )
        missed_objective_gap_text = (
            format(missed_objective_gap, ".2f") if missed_objective_gap is not None else None
        )
        print("Objective basis: Null contract objective, not raw card points.")
        print(f"Actual card-point swing (informational): {actual_expected_point_swing:.2f}")
        print(
            f"Recommended card-point swing (informational): {recommended_expected_point_swing:.2f}"
        )
        print(f"Card-point swing difference (informational): {expected_point_swing_difference:.2f}")
        print(f"Missed Null objective gap: {format_optional_cli_value(missed_objective_gap_text)}")
        return

    print(f"Actual expected point swing: {actual_expected_point_swing:.2f}")
    print(f"Recommended expected point swing: {recommended_expected_point_swing:.2f}")
    print(f"Missed expected point swing: {max(0.0, expected_point_swing_difference):.2f}")


def print_post_game_review_summary(result: dict[str, object]) -> None:
    """Prints the post-game review summary for human-readable CLI output."""
    summary = result.get("post_game_review_summary")

    if not isinstance(summary, dict):
        return

    print()
    print("Post-game review summary")

    decision_factors = format_decision_factors(summary)
    decision_explanation = summary.get("decision_explanation", "")

    if summary.get("is_available") is not True:
        reason = summary.get("reason", "not_available")
        print("Review status: not available")
        print(f"Actual card played: {format_optional_cli_value(summary.get('actual_card_played'))}")
        print(f"Recommended card: {format_optional_cli_value(summary.get('recommended_card'))}")
        print(f"Unavailable reason: {format_post_game_review_unavailable_reason(reason)}")
        print(f"Reason code: {reason}")
        print(f"Decision factors: {decision_factors}")
        print(f"Decision explanation: {decision_explanation}")
        print_post_game_review_rank_summary(summary)
        return

    print(f"Actual card played: {summary['actual_card_played']}")
    print(f"Recommended card: {summary['recommended_card']}")
    print_post_game_review_value_summary(result=result, summary=summary)
    print(f"Decision quality: {summary['decision_quality']}")
    print(f"Decision factors: {decision_factors}")
    print(f"Decision explanation: {decision_explanation}")
    print_post_game_review_rank_summary(summary)


def print_analysis_result(result: dict[str, Any]) -> None:
    """Prints the analysis result in a readable text format."""
    position = result["position"]
    settings = result["settings"]
    score_summary = result["score_summary"]

    print("JSON position analysis")
    print("Input file:", result["input_file"])
    print("Game type:", position["game_type"])
    print("Player role:", position["player_role"])
    print("Player position:", position["player_position"])
    print("Declarer player:", position["declarer_player"])
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

    method_summary = result.get("recommendation_method_summary")
    if isinstance(method_summary, dict):
        print("Requested recommendation method:", method_summary["requested_method"])
        print("Effective recommendation method:", method_summary["effective_method"])
        search_settings = settings.get("bounded_search_settings")
        if isinstance(search_settings, dict):
            print("Search random seed:", search_settings["random_seed"])
        search_result = result.get("bounded_search_result")
        if isinstance(search_result, dict):
            consumed = search_result["consumed_budget"]
            print("Search status:", search_result["status"])
            print("Search stop reason:", search_result["stop_reason"])
            print("Search coverage:", search_result["world_coverage"])
            print(
                "Search completed worlds:",
                f"{consumed['completed_world_count']} of {consumed['selected_world_count']}",
            )
        if method_summary["fallback_used"]:
            print("Fallback method:", method_summary["fallback_method"])

    declaration = result["game_declaration"]
    if declaration["ouvert"]:
        constraints = result["information_policy_summary"].get(
            "public_hand_constraints", []
        )
        declared_constraint = next(
            constraint
            for constraint in constraints
            if constraint["source"] == "declared_ouvert"
        )
        print("Declared Ouvert: yes")
        print("Public declarer:", declared_constraint["player"])
        print("Public declarer cards:", declared_constraint["card_count"])
        print("Ouvert-aware simulation: applied")

    print_opponent_profile_application_summary(result)

    print_hidden_card_inference_summary(result.get("hidden_card_inference_summary"))

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
    print(
        "Recommended card:",
        format_optional_cli_value(result["recommendation"]["card"]),
    )
    print("Reason:", result["recommendation"]["reason"])

    print_game_shortening_summary(result)
    print_game_continuation_summary(result)
    print_post_game_review_summary(result)


def print_game_shortening_summary(result: dict[str, Any]) -> None:
    """Prints the supported structured game-shortening outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict):
        return
    if summary.get("kind") == "defender_concession":
        print_defender_concession_summary(result)
    elif summary.get("kind") == "declarer_card_exposure":
        print_declarer_card_exposure_summary(result)
    elif summary.get("kind") == "defender_open_play":
        print_defender_open_play_summary(result)
    elif summary.get("kind") == "open_card_throw":
        print_open_card_throw_summary(result)
    else:
        print_declarer_concession_summary(result)


def print_game_continuation_summary(result: dict[str, Any]) -> None:
    """Prints one supported ongoing continuation setup."""
    summary = result.get("game_continuation_summary")
    if not isinstance(summary, dict):
        return
    if summary.get("kind") == "defender_open_play":
        print_defender_open_play_continuation_summary(summary)
        return
    print()
    print("Declarer card exposure was not accepted unanimously.")
    continuing = summary["continuing_defenders"]
    if len(continuing) == 2:
        print("Both defenders requested continued play.")
    else:
        print(f"{continuing[0].title()} requested continued play.")
    print(
        f"The declarer's {summary['public_declarer_card_count']} remaining cards "
        "are public to all players."
    )
    print(
        f"Claimed level {summary['claimed_play_level'].title()} has no immediate settlement effect."
    )
    print("Analysis continues using the exposed declarer hand.")


def print_defender_open_play_continuation_summary(summary: dict[str, Any]) -> None:
    """Prints the non-adjudicating defender-open-play continuation state."""
    exposing_defender = summary["exposing_defender"]
    card_count = summary["public_exposing_defender_card_count"]
    print()
    print("Continued play was requested after defender open play.")
    if exposing_defender == "me":
        print(f"You took your {card_count} exposed cards back into the hand.")
        print("Your remaining hand is known to both opponents.")
    else:
        print(
            f"{exposing_defender.title()} took the {card_count} exposed cards back into the hand."
        )
        print("Those cards remain known to all players.")
    print("The original rest-trick claim is not adjudicated.")
    print("Analysis continues from the corrected legal position.")


def print_declarer_concession_summary(result: dict[str, Any]) -> None:
    """Prints the bounded structured declarer-concession outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "declarer_concession":
        return

    hand_count = summary["declarer_hand_cards_remaining"]
    consent = summary["defender_consent"]
    if summary["consent_required"]:
        consent_text = f"accepted by {consent['consenting_defender_count']} defender" + (
            "s" if consent["consenting_defender_count"] != 1 else ""
        )
    else:
        consent_text = "defender consent not required"

    settlement = result["final_settlement_summary"]
    print()
    print(f"Declarer concession: {hand_count} hand cards, {consent_text}.")
    print("Result: declarer lost; no remaining card points were assigned.")
    print(
        f"Settlement: {settlement['settlement_score']} using effective game value "
        f"{settlement['effective_game_value']}; no achieved Schneider or Schwarz "
        "level was added."
    )


def print_defender_concession_summary(result: dict[str, Any]) -> None:
    """Prints the bounded structured defender-concession outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "defender_concession":
        return

    settlement = result["final_settlement_summary"]
    decision_state = summary["decision_state_before_concession"]
    print()
    if decision_state == "defenders_already_won":
        print(
            f"Defender concession: {summary['conceding_player']} conceded after the "
            "game was already lost by the declarer."
        )
        print(
            "Result preserved: defenders won; the concession did not reverse the existing decision."
        )
    else:
        print(
            f"Defender concession: {summary['conceding_player']} conceded for the defending party."
        )
        print(f"Decision before concession: {decision_state}.")
        print(
            f"Result: {summary['adjudicated_winner']} won; no remaining card points were assigned."
        )
    print(
        f"Settlement: {settlement['settlement_score']} using effective game value "
        f"{settlement['effective_game_value']}."
    )


def print_declarer_card_exposure_summary(result: dict[str, Any]) -> None:
    """Prints the bounded accepted declarer-card-exposure outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != ("declarer_card_exposure"):
        return

    settlement = result["final_settlement_summary"]
    print()
    if summary["exposure_form"] == "laid_open":
        print(f"Declarer card exposure: {summary['exposed_card_count']} cards laid open.")
    else:
        print(f"Declarer showed all remaining cards to {summary['shown_to_player']}.")
    print("Both defenders accepted the shortening.")
    print(f"Claimed level: {summary['claimed_play_level'].title()}.")
    if summary["decision_state_before_shortening"] == "defenders_already_won":
        print("The game was already lost before the card exposure.")
        print("Defender acceptance did not reverse the existing result.")
    else:
        print(
            f"Result: {summary['adjudicated_winner']} won; no remaining card points were assigned."
        )
    claim_text = ""
    basis = settlement["settlement_basis"]
    if basis["accepted_claimed_schwarz_applied"]:
        claim_text = " using a unanimously accepted Schwarz claim"
    elif basis["accepted_claimed_schneider_applied"]:
        claim_text = " using a unanimously accepted Schneider claim"
    print(f"Settlement: {settlement['settlement_score']}{claim_text}.")


def print_defender_open_play_summary(result: dict[str, Any]) -> None:
    """Prints one privacy-safe exact defender-open-play adjudication."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "defender_open_play":
        return

    proof = summary["exact_proof"]
    settlement = result["final_settlement_summary"]
    print()
    print(
        f"Defender open play: {summary['exposing_defender']} exposed "
        f"{summary['exposed_card_count']} remaining cards."
    )
    if proof["status"] == "valid":
        print("Exact proof: valid across every legal declarer and partner response.")
        print("Rest tricks: defending party.")
    else:
        print("Exact proof: invalid; a legal counterplay can give the declarer a trick.")
        print("Rest tricks: declarer by rule.")
    decision_state = summary["decision_state_before_shortening"]
    if decision_state == "defenders_already_won":
        print("The declarer had already lost before the open play.")
        print("The later rest-trick adjudication did not reverse the existing result.")
    elif decision_state == "declarer_already_won":
        print("The declarer had already won before the open play.")
        print("The later rest-trick adjudication did not reverse the existing result.")
    else:
        result_text = "won" if summary["adjudicated_winner"] == "declarer" else "lost"
        print(f"Result: declarer {result_text}.")
    print(f"Settlement: {settlement['settlement_score']}.")


def print_open_card_throw_summary(result: dict[str, Any]) -> None:
    """Prints one privacy-safe ISkO 4.4.6 adjudication."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "open_card_throw":
        return

    assignment = summary["rest_trick_assignment"]
    observed_tricks = summary["observed_trick_counts"]
    observed_points = summary["observed_points"]
    settlement = result["final_settlement_summary"]
    print()
    print(
        f"Open card throw: {summary['throwing_player']} threw "
        f"{summary['thrown_card_count']} remaining cards."
    )
    throwing_party_label = (
        "defending" if summary["throwing_party"] == "defenders" else "declarer"
    )
    print(
        f"The {throwing_party_label} party keeps its "
        f"{observed_tricks[summary['throwing_party']]} completed tricks and "
        f"{observed_points[summary['throwing_party']]} points."
    )
    print(
        f"All {assignment['remaining_trick_count']} unresolved tricks and "
        f"{assignment['assigned_card_points']} outstanding points go to the "
        f"{summary['opposing_party']} party."
    )
    decision_state = summary["decision_state_before_shortening"]
    if decision_state != "undecided":
        existing_winner = "declarer" if decision_state == "declarer_already_won" else "defenders"
        print(f"The game had already been won by the {existing_winner} party.")
        print("The later open throw did not reverse the existing result.")
    else:
        levels = []
        if summary["schneider_rule_level_applied"]:
            levels.append("Schneider")
        if summary["schwarz_rule_level_applied"]:
            levels.append("Schwarz")
        level_text = f" with {' and '.join(levels)}" if levels else ""
        print(f"Result: {summary['adjudicated_winner']} won{level_text}.")
    if summary["theoretical_schwarz_status"] == "excluded":
        basis = summary["theoretical_schwarz_assessment"]["exclusion_basis"]
        print(f"Schwarz was theoretically excluded under the jack-only assessment: {basis}.")
    else:
        print("Schwarz was not theoretically excluded under the jack-only assessment.")
    print(f"Settlement: {settlement['settlement_score']}.")


def print_opponent_profile_application_summary(result: dict[str, Any]) -> None:
    """Prints one concise line per requested external opponent binding."""
    summary = result.get("opponent_profile_application_summary")
    if not isinstance(summary, dict):
        return

    for relative_player in ("left", "right"):
        side = summary[relative_player]
        if side["binding_status"] != "matched":
            continue
        external_profile = side["external_profile"]
        classification = external_profile["classification"]
        confidence = external_profile["confidence_level"]
        status = side["application_status"]
        if status == "applied":
            decision = f"applied {side['applied_policy_preset']}"
        elif status == "manual_profile_precedence":
            decision = "not applied; manual profile takes precedence"
        elif status == "explicit_policy_precedence":
            decision = "not applied; explicit policy takes precedence"
        else:
            decision = "not applied"
        print(
            f"{relative_player.title()} opponent {side['bound_player_id']}: "
            f"{classification}, {confidence} confidence, {decision}."
        )
