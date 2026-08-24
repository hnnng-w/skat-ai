"""Historical-game and retrospective review presentation."""

from typing import Any

from skat_ai.cli.presentation.common import print_information_set_search_metrics


def _print_historical_continuation_event(event: dict[str, Any]) -> None:
    if event["kind"] == "defender_open_play_continuation":
        print("Non-terminal event: defender open-play continuation")
        print("Event after played cards:", event["after_play_count"])
        print("Exposing defender:", event["exposing_defender_player_id"])
        print("Returned public cards:", event["exposed_card_count"])
        print("Continued play requested: yes")
        print("Rest-trick claim adjudicated: no")
    else:
        print("Non-terminal event: declarer card-exposure continuation")
        print("Event after played cards:", event["after_play_count"])
        if event["exposure_form"] == "shown_to_defender":
            print(
                "Exposure: declarer showed "
                f"{event['public_declarer_card_count']} remaining cards to "
                f"{event['shown_to_defender_player_id']}"
            )
        else:
            print(
                "Exposure: declarer laid open "
                f"{event['public_declarer_card_count']} remaining cards"
            )
        continuing_ids = event["continuing_defender_player_ids"]
        if len(continuing_ids) == 2:
            print("Both defenders required continued play.")
        else:
            print("Continuing defender:", continuing_ids[0])
        print("Claimed play level:", event["claimed_play_level"].title())
        print("Claimed level applied immediately: no")
        print("The game continued with the declarer's cards open.")
    print("Actual plays after the event:", event["actual_plays_after_event"])


def print_historical_game_result(result: dict[str, Any]) -> None:
    """Prints a concise complete historical-game summary."""
    summary = result["historical_game_summary"]
    declaration = summary["record"]["declaration"]
    settlement = summary["final_settlement_summary"]

    game_end_summary = summary.get("historical_game_end_summary")
    game_events_summary = summary.get("historical_game_events_summary")
    if game_end_summary is not None:
        print(f"Historical game: {summary['game_id']}")
        end_kind = game_end_summary["kind"]
        if end_kind == "defender_concession":
            print("End reason: defender concession")
            print(
                "Conceding defender:",
                game_end_summary["conceding_defender_player_id"],
            )
            print("Joint liability: yes")
        elif end_kind == "declarer_concession":
            consent_ids = game_end_summary["defender_consent"]["consenting_defender_player_ids"]
            consent_text = (
                "not required" if not consent_ids else f"granted by {', '.join(consent_ids)}"
            )
            print("End reason: declarer concession")
        elif end_kind == "defender_open_play":
            print("End reason: defender open play")
            print(
                "Exposing defender:",
                game_end_summary["exposing_defender_player_id"],
            )
            print(
                "Non-exposing defender:",
                game_end_summary["non_exposing_defender_player_id"],
            )
            print("Exposed defender cards:", game_end_summary["exposed_card_count"])
            print("Exact proof:", game_end_summary["exact_proof"]["status"])
            print("Rest tricks assigned to:", game_end_summary["rest_tricks_recipient"])
        elif end_kind == "open_card_throw":
            print("End reason: open card throw")
            print("Throwing player:", game_end_summary["throwing_player_id"])
            print("Throwing party:", game_end_summary["throwing_party"])
            print(
                "Joint liability:",
                "yes" if game_end_summary["joint_liability"] else "no",
            )
            print("Thrown cards:", game_end_summary["thrown_card_count"])
            print("Statement:", game_end_summary["statement_classification"])
            print("Rest tricks assigned to:", game_end_summary["rest_tricks_recipient"])
            print(
                "Theoretical Schwarz:",
                game_end_summary["theoretical_schwarz_status"],
            )
        elif end_kind == "party_wide_all_remaining_tricks_claim":
            print("End reason: party-wide all-remaining-Tricks Claim")
            print("Claimant:", game_end_summary["claimant_player_id"])
            print("Claiming party:", game_end_summary["claiming_party"])
            print("Exact proof:", game_end_summary["exact_proof"]["status"])
            print(
                "Proof states evaluated:",
                game_end_summary["exact_proof"]["evaluated_state_count"],
            )
        else:
            print("End reason: accepted declarer card exposure")
            print("Exposure form:", game_end_summary["exposure_form"])
            shown_to_id = game_end_summary["shown_to_defender_player_id"]
            if shown_to_id is not None:
                print("Shown to defender:", shown_to_id)
            print("Exposed declarer cards:", game_end_summary["exposed_card_count"])
            print(
                "Accepted by defenders:",
                ", ".join(game_end_summary["accepting_defender_player_ids"]),
            )
            print("Claimed play level:", game_end_summary["claimed_play_level"])
        print("Played cards:", summary["play_prefix_summary"]["played_card_count"])
        if end_kind == "defender_concession":
            print(f"Result: {summary['winner']} won")
            if game_end_summary["decision_state_before_concession"] == "defenders_already_won":
                print("The defending party had already won before the concession.")
                print("The later concession did not reverse the existing result.")
        elif end_kind == "declarer_concession":
            print(
                "Declarer cards remaining:",
                game_end_summary["declarer_hand_cards_remaining"],
            )
            print("Consent:", consent_text)
            print("Result: declarer lost")
        elif end_kind == "defender_open_play":
            print(
                "Decision before open play:",
                game_end_summary["decision_state_before_shortening"],
            )
            print(f"Result: {summary['winner']} won")
        elif end_kind == "open_card_throw":
            print(
                "Decision before throw:",
                game_end_summary["decision_state_before_shortening"],
            )
            print(f"Result: {summary['winner']} won")
        elif end_kind == "party_wide_all_remaining_tricks_claim":
            print(
                "Decision before Claim:",
                game_end_summary["adjudication"]["decision_state_before_claim"],
            )
            print(f"Result: {summary['winner']} won")
        else:
            print("Decision before exposure:", game_end_summary["decision_state_before_shortening"])
            print(f"Result: {summary['winner']} won")
        print(
            "Unresolved points assigned:",
            (
                "yes"
                if end_kind
                in {
                    "defender_open_play",
                    "open_card_throw",
                    "party_wide_all_remaining_tricks_claim",
                }
                else "no"
            ),
        )
        print("Settlement:", settlement["settlement_score"])
        if game_events_summary is not None:
            _print_historical_continuation_event(game_events_summary["events"][0])
    else:
        if game_events_summary is not None:
            event = game_events_summary["events"][0]
            print(f"Historical game: {summary['game_id']}")
            print("End reason: normal completion")
            _print_historical_continuation_event(event)
            print(f"Final result: {summary['winner']} won")
            print("Settlement:", settlement["settlement_score"])
        else:
            print("Historical game summary")
            print("Input file:", result["input_file"])
            print("Game ID:", summary["game_id"])
            print("Game type:", declaration["game_type"])
            print("Declarer:", summary["record"]["declarer_player_id"])
            print("Result winner:", summary["winner"])
            print("Declarer points:", summary["declarer_points"])
            print("Defender points:", summary["defender_points"])
            print("Game value:", summary["game_value_summary"]["game_value"])
            print("Overbid status:", summary["overbid_summary"]["status"])
            print("Settlement score:", settlement["settlement_score"])
    decision_snapshot_summary = summary.get("decision_snapshot_summary")
    if decision_snapshot_summary is not None:
        snapshot_count = decision_snapshot_summary["snapshot_count"]
        if game_end_summary is not None:
            print("Historical decision snapshots:", snapshot_count)
            if snapshot_count == 0:
                print("No card decisions occurred before the terminal event.")
        else:
            print("Decision snapshots generated:", snapshot_count)
        if game_events_summary is not None:
            event = game_events_summary["events"][0]
            print(
                (
                    "Public defender hand begins at decision:"
                    if event["kind"] == "defender_open_play_continuation"
                    else "Public declarer hand begins at decision:"
                ),
                event["first_affected_decision_index"],
            )
    review_summary = summary.get("historical_game_review_summary")
    if review_summary is not None:
        profile_summary = result.get("historical_opponent_profile_application_summary")
        if profile_summary is not None:
            participant_count = len(profile_summary["participant_matches"])
            matched_count = profile_summary["matched_player_count"]
            print(
                f"Historical profile application: {matched_count} of "
                f"{participant_count} participants matched."
            )
            print("Temporal eligibility: all matched captures predate the game.")
            application_counts = review_summary["opponent_profile_application_counts"]
            applied_decisions = sum(
                any(
                    application[side]["application_status"] == "applied"
                    for side in ("left", "right")
                )
                for application in (
                    decision["opponent_profile_application"]
                    for decision in review_summary["decisions"]
                )
            )
            print(
                "Reviewed decisions with an applied external profile: "
                f"{applied_decisions} of {application_counts['total_decisions']}."
            )
        print()
        if game_end_summary is not None:
            print(
                "Historical game review:",
                review_summary["decision_count"],
                "decisions",
            )
        else:
            print("Historical game review")
            print("Total decisions:", review_summary["decision_count"])
        print("Reviewed decisions:", review_summary["reviewed_decision_count"])
        print("Unavailable decisions:", review_summary["unavailable_decision_count"])
        inference_decision_count = sum(
            "hidden_card_inference_summary" in decision for decision in review_summary["decisions"]
        )
        if inference_decision_count:
            print(
                "Hidden-card inference applied at reviewed decisions:",
                inference_decision_count,
            )
        if game_end_summary is not None:
            print(
                "Terminal event:",
                game_end_summary["kind"].replace("_", " "),
            )
            print("The terminal event itself was not reviewed as a card decision.")
        for quality, count in review_summary["quality_counts"].items():
            print(f"{quality.replace('_', ' ').title()} decisions:", count)
        for decision in review_summary["decisions"]:
            decision_quality = decision["post_game_review_summary"]["decision_quality"]
            if decision_quality not in {"suboptimal", "mistake"}:
                continue
            print(
                f"Decision {decision['decision_index']} ({decision['acting_player_id']}): "
                f"{decision_quality}; actual {decision['actual_card_played']}, "
                f"recommended {decision['recommendation']['card']}."
            )


def print_historical_search_review_result(summary: dict[str, Any]) -> None:
    """Prints a concise Historical Search Review summary."""
    quality = summary["quality_gate"]
    counts = summary["decision_counts"]
    print()
    print("Historical Search Review")
    print("Decisions attempted:", counts["search_attempted_count"])
    print("Search recommendations:", counts["search_recommendation_count"])
    print(
        "Search not-worse gate:",
        f"{quality['search_not_worse_count']} of "
        f"{quality['comparable_decision_count']} comparable decisions; "
        f"violations {quality['quality_violation_count']}.",
    )


def print_historical_information_set_search_review_result(
    summary: dict[str, Any],
) -> None:
    """Prints only aggregate, information-safe Information-set review metrics."""
    print()
    print("Historical Information-set Search Review")
    print_information_set_search_metrics(summary)


def print_historical_tactical_motif_review_result(
    summary: dict[str, Any],
) -> None:
    """Prints only safe aggregate tactical-motif observations."""
    print()
    print("Historical Tactical Motif Review")
    print("Source game:", summary["source_game_id"])
    print("Observations:", summary["observation_count"])
    print("Complete observations:", summary["complete_observation_count"])
    print("Partial observations:", summary["partial_observation_count"])
    print("Motif occurrences:", summary["motif_occurrence_count"])
    motif_counts = ", ".join(
        f"{row['motif_type']}={row['count']}"
        for row in summary["motif_counts"]
        if row["count"] > 0
    )
    family_counts = ", ".join(
        f"{row['motif_family']}={row['count']}"
        for row in summary["family_counts"]
        if row["count"] > 0
    )
    print("Motif counts:", motif_counts or "none")
    print("Family counts:", family_counts or "none")


def _count_rows(
    rows: object,
    key_name: str,
) -> dict[str, int]:
    if not isinstance(rows, list):
        return {}
    return {
        row[key_name]: row["count"]
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get(key_name), str)
        and type(row.get("count")) is int
    }


def print_historical_information_set_replay_coaching_result(
    summary: dict[str, Any],
) -> None:
    """Prints aggregate Information-set Coaching without private Search state."""
    coverage = summary["coverage"]
    statuses = _count_rows(
        coverage.get("information_set_status_counts"),
        "information_set_status",
    )
    unavailable_count = statuses.get("unavailable", 0) + statuses.get(
        "not_available", 0
    )
    worlds = _count_rows(coverage.get("world_coverage_counts"), "world_coverage")
    recommendation_count = coverage["decision_recommendation_count"] + coverage[
        "pattern_recommendation_count"
    ]

    print()
    print("Historical Information-set Replay Coaching Report")
    print("Source game:", summary["source_game_id"])
    print("Decisions:", coverage["decision_count"])
    print("Assessable decisions:", coverage["assessable_decision_count"])
    print("Not assessable:", coverage["not_assessable_count"])
    print("Key Decisions:", coverage["key_decision_count"])
    print("Turning Points:", coverage["turning_point_count"])
    print("Patterns:", coverage["pattern_count"])
    print("Recommendations:", recommendation_count)
    print(
        "Information-set Search coverage: "
        f"complete {statuses.get('complete', 0)}, "
        f"partial {statuses.get('partial', 0)}, "
        f"timeout {statuses.get('timeout', 0)}, "
        f"unavailable {unavailable_count}; "
        f"single exact {worlds.get('single_exact_world', 0)}, "
        f"all compatible {worlds.get('all_compatible_worlds', 0)}, "
        f"sampled compatible {worlds.get('sampled_compatible_worlds', 0)}, "
        f"none {worlds.get('none', 0)}."
    )


def print_historical_replay_coaching_result(summary: dict[str, Any]) -> None:
    """Prints the concise public Replay Coaching view without private analysis state."""
    game = summary["game_context"]
    declaration = game["declaration"]
    coverage = summary["coverage_summary"]
    prioritization = summary["prioritization"]
    guidance = summary["guidance"]
    outcome = summary["outcome_context"]

    print()
    print("Historical Replay Coaching Report")
    print("Source game:", summary["source_game_id"])
    print("Method:", summary["report_method"])
    print(
        "Game type and declaration:",
        f"{game['game_type']}; Hand {str(declaration['hand_game']).lower()}; "
        f"Ouvert {str(declaration['ouvert']).lower()}; bid {declaration['bid_value']}.",
    )
    print("Game-end reason:", game["game_end_reason"].replace("_", " "))
    print(
        "Decision coverage:",
        f"{coverage['assessable_decision_count']} of {coverage['decision_count']} assessable; "
        f"{coverage['not_assessable_count']} not assessable.",
    )
    print("High-impact decisions:", coverage["high_impact_decision_count"])

    print("Key Decisions")
    if not prioritization["key_decisions"]:
        print("None.")
    for key_decision in prioritization["key_decisions"]:
        assessment = key_decision["assessment"]
        evidence = assessment["decision_time_evidence"]
        marker = "high impact" if key_decision["is_high_impact"] else "review focus"
        print(
            f"{key_decision['rank']}. Decision {evidence['decision_index']}; "
            f"actor {evidence['acting_player_id']}; trick {evidence['trick_number']}, "
            f"play {evidence['play_index']}; actual {assessment['actual_card']}; "
            f"best evaluated {assessment['best_card']}; impact "
            f"{assessment['impact_tier'].replace('_', ' ')}; evidence "
            f"{assessment['evidence_basis'].replace('_', ' ')}; {marker}."
        )

    print("Turning Points")
    if not prioritization["turning_points"]:
        print("None.")
    for turning_point in prioritization["turning_points"]:
        assessment = turning_point["assessment"]
        evidence = assessment["decision_time_evidence"]
        before = turning_point["recorded_state_before"]
        after = turning_point["recorded_state_after"]
        transition = (
            f"{before.replace('_', ' ')} -> {after.replace('_', ' ')}"
            if before is not None and after is not None
            else "counterfactual aggregate opportunity; no recorded transition"
        )
        print(
            f"{turning_point['turning_point_type'].replace('_', ' ')}; decision "
            f"{turning_point['decision_index']}; actor {evidence['acting_player_id']}; "
            f"{transition}; high impact."
        )

    print("Decision Recommendations")
    if not guidance["decision_recommendations"]:
        print("None.")
    for recommendation in guidance["decision_recommendations"]:
        print(f"{recommendation['rank']}. {recommendation['title']}")
        print("Action:", recommendation["action"])

    print("Pattern Recommendations")
    if not guidance["pattern_recommendations"]:
        print("None.")
    for recommendation in guidance["pattern_recommendations"]:
        print(f"{recommendation['rank']}. {recommendation['title']}")
        print("Action:", recommendation["action"])

    for label, field_name in (
        ("Player summaries", "player_summaries"),
        ("Role summaries", "role_summaries"),
        ("Phase summaries", "phase_summaries"),
        ("Contract summary", "contract_summaries"),
    ):
        rows = summary[field_name]
        compact = "; ".join(
            f"{row['scope_value']}: {row['decision_count']} decisions, "
            f"{row['key_decision_count']} key, {row['turning_point_count']} turning"
            for row in rows
        )
        print(f"{label}: {compact}.")

    print("Retrospective outcome context")
    print("Recorded end:", outcome["game_end_reason"].replace("_", " "))
    print("Recorded winner:", outcome["game_result_summary"]["winner"])
    print(
        "Recorded settlement score:",
        outcome["final_settlement_summary"]["settlement_score"],
    )
    print("This final outcome is retrospective context, not decision-time evidence.")
    print("Report limitations:", ", ".join(summary["limitations"]))
