from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.dataset_partition_policy import (
    build_serializable_dataset_partition_policy,
    collect_player_partition_memberships,
)
from skat_ai.game_declaration import build_serializable_game_declaration
from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    build_historical_decision_snapshots,
)
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.historical_opponent_statistics import (
    HistoricalOpponentStatisticsAggregation,
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
)
from skat_ai.opponent_policy import (
    choose_opponent_lead_card_by_policy,
    choose_opponent_response_card_by_policy,
    determine_current_trick_winner_index,
    get_preferred_opponent_cards_by_policy,
)
from skat_ai.opponent_policy_preset import get_opponent_policy_settings_for_preset
from skat_ai.opponent_statistics import build_opponent_statistics_summary
from skat_ai.rfc3339 import parse_rfc3339_datetime
from skat_ai.training_dataset import (
    SAMPLES_PER_TRAINING_RECORD,
    TRAINING_PARTITIONS,
    TrainingDatasetInput,
    TrainingDatasetRecord,
)

ROLLING_OPPONENT_POLICY_EVALUATION_VERSION = 1
ROLLING_TEMPORAL_RULE = "source_played_at_strictly_before_target_played_at"
BASELINE_POLICY_PRESET = "simple_lowest"
DEFAULT_SOURCE_PARTITIONS = ("train",)
DEFAULT_EVALUATION_PARTITIONS = ("validation", "test")

ProfilePredictionStatus = Literal[
    "actionable",
    "no_prior_source_games",
    "no_player_history",
    "insufficient_confidence",
    "neutral_profile",
    "insufficient_data",
]
ComparisonOutcome = Literal[
    "both_match",
    "profile_only",
    "baseline_only",
    "neither_match",
    "not_available",
]


@dataclass(frozen=True)
class RollingOpponentPolicyEvaluation:
    """One deterministic rolling as-of opponent-policy evaluation."""

    schema_version: int
    evaluation_version: int
    source_dataset: dict[str, Any]
    selection: dict[str, Any]
    coverage: dict[str, int]
    baseline_results: dict[str, Any]
    actionable_profile_paired_results: dict[str, Any]
    breakdowns: dict[str, list[dict[str, Any]]]
    target_games: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class _PlayerAsOfState:
    status: ProfilePredictionStatus
    summary: dict[str, Any]


def _canonicalize_partitions(
    partitions: tuple[str, ...],
    *,
    option_name: str,
) -> tuple[str, ...]:
    if not partitions:
        raise ValueError(f"At least one {option_name} partition must be selected.")
    unsupported = sorted(set(partitions) - set(TRAINING_PARTITIONS))
    if unsupported:
        raise ValueError(f"Unsupported {option_name} partitions: {unsupported}.")
    return tuple(partition for partition in TRAINING_PARTITIONS if partition in partitions)


def _validate_selection(
    dataset: TrainingDatasetInput,
    source_partitions: tuple[str, ...],
    evaluation_partitions: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], list[TrainingDatasetRecord]]:
    source = _canonicalize_partitions(source_partitions, option_name="profile-source")
    evaluation = _canonicalize_partitions(
        evaluation_partitions,
        option_name="profile-evaluation",
    )
    overlap = [
        partition
        for partition in TRAINING_PARTITIONS
        if partition in source and partition in evaluation
    ]
    if overlap:
        raise ValueError(
            "Profile source and evaluation partitions must be disjoint; overlap: "
            f"{overlap}."
        )

    populated = {record.partition for record in dataset.records}
    empty_source = [partition for partition in source if partition not in populated]
    if empty_source:
        raise ValueError(
            "Selected profile-source partitions contain no source records: "
            f"{empty_source}."
        )
    targets = [record for record in dataset.records if record.partition in evaluation]
    if not targets:
        raise ValueError("Selected profile-evaluation partitions contain no target records.")

    for record in dataset.records:
        if record.partition not in source and record.partition not in evaluation:
            continue
        played_at = record.historical_game.played_at
        if played_at is None:
            role = "source" if record.partition in source else "target"
            raise ValueError(
                f"Historical {role} game '{record.historical_game.game_id}' played_at "
                "is required for rolling opponent-policy evaluation."
            )
        parse_rfc3339_datetime(
            played_at,
            f"Historical game '{record.historical_game.game_id}' played_at",
        )
    return source, evaluation, targets


def _rate(count: int, denominator: int) -> float | None:
    return count / denominator * 100 if denominator else None


def _build_match_results(
    decisions: list[dict[str, Any]],
    *,
    prediction_key: str,
) -> dict[str, Any]:
    count = len(decisions)
    exact_count = sum(decision[prediction_key]["exact_card_match"] for decision in decisions)
    preferred_count = sum(
        decision[prediction_key]["preferred_card_match"] for decision in decisions
    )
    return {
        "decision_count": count,
        "exact_card_match_count": exact_count,
        "exact_card_match_rate": _rate(exact_count, count),
        "preferred_card_match_count": preferred_count,
        "preferred_card_match_rate": _rate(preferred_count, count),
    }


def _comparison_outcome(profile_match: bool, baseline_match: bool) -> ComparisonOutcome:
    if profile_match and baseline_match:
        return "both_match"
    if profile_match:
        return "profile_only"
    if baseline_match:
        return "baseline_only"
    return "neither_match"


def _build_paired_results(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    paired = [decision for decision in decisions if decision["profile_prediction"] is not None]
    count = len(paired)
    profile_exact = sum(
        decision["profile_prediction"]["exact_card_match"] for decision in paired
    )
    baseline_exact = sum(
        decision["baseline_prediction"]["exact_card_match"] for decision in paired
    )
    profile_preferred = sum(
        decision["profile_prediction"]["preferred_card_match"] for decision in paired
    )
    baseline_preferred = sum(
        decision["baseline_prediction"]["preferred_card_match"] for decision in paired
    )
    exact_outcomes = {
        outcome: sum(decision["exact_comparison_outcome"] == outcome for decision in paired)
        for outcome in ("both_match", "profile_only", "baseline_only", "neither_match")
    }
    preferred_outcomes = {
        outcome: sum(
            decision["preferred_comparison_outcome"] == outcome for decision in paired
        )
        for outcome in ("both_match", "profile_only", "baseline_only", "neither_match")
    }
    profile_exact_rate = _rate(profile_exact, count)
    baseline_exact_rate = _rate(baseline_exact, count)
    profile_preferred_rate = _rate(profile_preferred, count)
    baseline_preferred_rate = _rate(baseline_preferred, count)
    return {
        "paired_decision_count": count,
        "profile_exact_card_match_count": profile_exact,
        "profile_exact_card_match_rate": profile_exact_rate,
        "baseline_exact_card_match_count": baseline_exact,
        "baseline_exact_card_match_rate": baseline_exact_rate,
        "exact_card_rate_delta_percentage_points": (
            profile_exact_rate - baseline_exact_rate
            if profile_exact_rate is not None and baseline_exact_rate is not None
            else None
        ),
        "profile_preferred_card_match_count": profile_preferred,
        "profile_preferred_card_match_rate": profile_preferred_rate,
        "baseline_preferred_card_match_count": baseline_preferred,
        "baseline_preferred_card_match_rate": baseline_preferred_rate,
        "preferred_card_rate_delta_percentage_points": (
            profile_preferred_rate - baseline_preferred_rate
            if profile_preferred_rate is not None and baseline_preferred_rate is not None
            else None
        ),
        "exact_comparison_outcome_counts": exact_outcomes,
        "preferred_comparison_outcome_counts": preferred_outcomes,
    }


def _build_prediction(
    snapshot: HistoricalDecisionSnapshot,
    *,
    preset: str,
    policy: str,
    partner_currently_winning: bool,
) -> dict[str, Any]:
    state = snapshot.visible_state
    hand = list(state.own_hand)
    current_trick = [play.card for play in state.current_trick]
    if current_trick:
        predicted = choose_opponent_response_card_by_policy(
            hand=hand,
            current_trick=current_trick,
            game_type=state.game_type,
            player_index=len(current_trick),
            policy=policy,
            partner_currently_winning=partner_currently_winning,
        )
    else:
        predicted = choose_opponent_lead_card_by_policy(
            hand=hand,
            policy=policy,
            game_type=state.game_type,
        )
    preferred = get_preferred_opponent_cards_by_policy(
        hand=hand,
        current_trick=current_trick,
        game_type=state.game_type,
        player_index=len(current_trick),
        policy=policy,
        partner_currently_winning=partner_currently_winning,
    )
    if predicted not in preferred:
        raise ValueError(
            f"Policy '{policy}' selected a card outside its preferred-card candidates."
        )
    actual = snapshot.actual_card_played
    return {
        "policy_preset": preset,
        "concrete_policy": policy,
        "decision_phase": "response" if current_trick else "lead",
        "predicted_card": predicted,
        "preferred_cards": preferred,
        "actual_card": actual,
        "exact_card_match": predicted == actual,
        "preferred_card_match": actual in preferred,
    }


def _partner_currently_winning(
    snapshot: HistoricalDecisionSnapshot,
    declarer_player_id: str,
) -> bool:
    current_trick = snapshot.visible_state.current_trick
    if snapshot.acting_side != "defenders" or not current_trick:
        return False
    winner_index = determine_current_trick_winner_index(
        [play.card for play in current_trick],
        snapshot.visible_state.game_type,
    )
    return current_trick[winner_index].player_id != declarer_player_id


def _status_from_derivation(derivation_status: str) -> ProfilePredictionStatus:
    return {
        "actionable": "actionable",
        "insufficient_confidence": "insufficient_confidence",
        "neutral": "neutral_profile",
        "insufficient_data": "insufficient_data",
    }[derivation_status]


def _build_player_states(
    target: TrainingDatasetRecord,
    aggregation: HistoricalOpponentStatisticsAggregation | None,
) -> dict[str, _PlayerAsOfState]:
    serialized_by_id: dict[str, dict[str, Any]] = {}
    aggregate_by_id = {}
    if aggregation is not None:
        aggregate_by_id = {
            record.statistics_record.player_id: record for record in aggregation.records
        }
        statistics_summary = build_opponent_statistics_summary(
            build_exportable_opponent_statistics_input(aggregation)
        )
        serialized_by_id = {
            record["player_id"]: record for record in statistics_summary["records"]
        }

    states = {}
    for player in target.historical_game.players:
        aggregate_record = aggregate_by_id.get(player.player_id)
        serialized = serialized_by_id.get(player.player_id)
        if aggregation is None:
            status: ProfilePredictionStatus = "no_prior_source_games"
        elif aggregate_record is None or serialized is None:
            status = "no_player_history"
        else:
            status = _status_from_derivation(
                serialized["profile_derivation"]["derivation_status"]
            )

        summary: dict[str, Any] = {
            "player_id": player.player_id,
            "player_label": player.player_label,
            "history_status": (
                "prior_player_history"
                if status not in ("no_prior_source_games", "no_player_history")
                else status
            ),
            "profile_prediction_status": status,
            "source_game_count": 0,
            "source_record_ids": [],
            "source_game_ids": [],
            "first_source_played_at": None,
            "last_source_played_at": None,
            "normalized_profile_statistics": None,
            "exact_counts": None,
            "profile_derivation": None,
        }
        if aggregate_record is not None and serialized is not None:
            summary.update(
                {
                    "source_game_count": len(aggregate_record.source_game_ids),
                    "source_record_ids": list(aggregate_record.source_record_ids),
                    "source_game_ids": list(aggregate_record.source_game_ids),
                    "first_source_played_at": aggregate_record.first_played_at,
                    "last_source_played_at": aggregate_record.last_played_at,
                    "normalized_profile_statistics": serialized[
                        "normalized_profile_statistics"
                    ],
                    "exact_counts": serialized["exact_counts"],
                    "profile_derivation": serialized["profile_derivation"],
                }
            )
        states[player.player_id] = _PlayerAsOfState(status=status, summary=summary)
    return states


def _build_decision(
    snapshot: HistoricalDecisionSnapshot,
    *,
    player_state: _PlayerAsOfState,
    declarer_player_id: str,
) -> dict[str, Any]:
    phase = "response" if snapshot.visible_state.current_trick else "lead"
    partner_winning = _partner_currently_winning(snapshot, declarer_player_id)
    baseline_settings = get_opponent_policy_settings_for_preset(BASELINE_POLICY_PRESET)
    baseline_policy = baseline_settings[f"opponent_{phase}_policy"]
    baseline = _build_prediction(
        snapshot,
        preset=BASELINE_POLICY_PRESET,
        policy=baseline_policy,
        partner_currently_winning=partner_winning,
    )

    derivation = player_state.summary["profile_derivation"]
    profile_prediction = None
    if player_state.status == "actionable":
        preset = derivation["actionable_policy_preset"]
        if preset not in ("aggressive_points", "cautious_defender"):
            raise ValueError("Only existing actionable profile presets may be evaluated.")
        settings = get_opponent_policy_settings_for_preset(preset)
        profile_prediction = _build_prediction(
            snapshot,
            preset=preset,
            policy=settings[f"opponent_{phase}_policy"],
            partner_currently_winning=partner_winning,
        )

    if profile_prediction is None:
        preferred_outcome: ComparisonOutcome = "not_available"
        exact_outcome: ComparisonOutcome = "not_available"
    else:
        preferred_outcome = _comparison_outcome(
            profile_prediction["preferred_card_match"],
            baseline["preferred_card_match"],
        )
        exact_outcome = _comparison_outcome(
            profile_prediction["exact_card_match"],
            baseline["exact_card_match"],
        )
    return {
        "game_id": snapshot.source_game_id,
        "decision_index": snapshot.decision_index,
        "trick_number": snapshot.trick_number,
        "play_index": snapshot.play_index,
        "acting_player_id": snapshot.acting_player_id,
        "acting_side": snapshot.acting_side,
        "game_type": snapshot.visible_state.game_type,
        "decision_phase": phase,
        "actual_card": snapshot.actual_card_played,
        "legal_cards": list(snapshot.visible_state.legal_cards),
        "profile_history_status": player_state.summary["history_status"],
        "profile_prediction_status": player_state.status,
        "profile_derivation_status": (
            derivation["derivation_status"] if derivation is not None else None
        ),
        "overall_profile_confidence": (
            derivation["confidence"]["overall"]["level"]
            if derivation is not None
            else None
        ),
        "relevant_role_confidence": (
            derivation["confidence"][
                "declarer" if snapshot.acting_side == "declarer" else "defender"
            ]["level"]
            if derivation is not None
            else None
        ),
        "actionable_profile_preset": (
            derivation["actionable_policy_preset"] if derivation is not None else None
        ),
        "baseline_prediction": baseline,
        "profile_prediction": profile_prediction,
        "profile_prediction_unavailable_reason": (
            None if profile_prediction is not None else player_state.status
        ),
        "preferred_comparison_outcome": preferred_outcome,
        "exact_comparison_outcome": exact_outcome,
    }


def _build_coverage(decisions: list[dict[str, Any]], target_game_count: int) -> dict[str, int]:
    status_field_names = {
        "actionable": "decisions_with_actionable_profile",
        "no_prior_source_games": "decisions_without_prior_source_games",
        "no_player_history": "decisions_without_player_history",
        "insufficient_confidence": "decisions_with_insufficient_confidence",
        "neutral_profile": "decisions_with_neutral_profiles",
        "insufficient_data": "decisions_with_insufficient_data",
    }
    coverage = {
        "target_game_count": target_game_count,
        "target_player_game_count": target_game_count * 3,
        "distinct_target_player_count": len(
            {decision["acting_player_id"] for decision in decisions}
        ),
        "target_decisions": len(decisions),
        "decisions_with_prior_player_history": sum(
            decision["profile_history_status"] == "prior_player_history"
            for decision in decisions
        ),
        "decisions_with_explainable_derived_profile": sum(
            decision["profile_derivation_status"] is not None for decision in decisions
        ),
    }
    coverage.update(
        {
            field_name: sum(
                decision["profile_prediction_status"] == status for decision in decisions
            )
            for status, field_name in status_field_names.items()
        }
    )
    status_total = sum(coverage[field_name] for field_name in status_field_names.values())
    if status_total != len(decisions):
        raise ValueError("Profile availability coverage does not reconcile.")
    return coverage


def _build_breakdown_rows(
    decisions: list[dict[str, Any]],
    *,
    field_name: str,
    output_name: str,
    include_missing: bool = False,
) -> list[dict[str, Any]]:
    values = []
    for decision in decisions:
        value = decision[field_name]
        if value is None and not include_missing:
            continue
        if value not in values:
            values.append(value)
    rows = []
    for value in values:
        selected = [decision for decision in decisions if decision[field_name] == value]
        paired = [decision for decision in selected if decision["profile_prediction"] is not None]
        profile_matches = sum(
            decision["profile_prediction"]["preferred_card_match"] for decision in paired
        )
        baseline_matches = sum(
            decision["baseline_prediction"]["preferred_card_match"] for decision in paired
        )
        profile_rate = _rate(profile_matches, len(paired))
        baseline_rate = _rate(baseline_matches, len(paired))
        rows.append(
            {
                output_name: value,
                "coverage_count": len(selected),
                "actionable_paired_count": len(paired),
                "profile_preferred_card_match_count": profile_matches,
                "profile_preferred_card_match_rate": profile_rate,
                "paired_baseline_preferred_card_match_count": baseline_matches,
                "paired_baseline_preferred_card_match_rate": baseline_rate,
                "preferred_card_rate_delta_percentage_points": (
                    profile_rate - baseline_rate
                    if profile_rate is not None and baseline_rate is not None
                    else None
                ),
            }
        )
    return rows


def _build_breakdowns(decisions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "by_player": _build_breakdown_rows(
            decisions, field_name="acting_player_id", output_name="player_id"
        ),
        "by_acting_side": _build_breakdown_rows(
            decisions, field_name="acting_side", output_name="acting_side"
        ),
        "by_game_type": _build_breakdown_rows(
            decisions, field_name="game_type", output_name="game_type"
        ),
        "by_decision_phase": _build_breakdown_rows(
            decisions, field_name="decision_phase", output_name="decision_phase"
        ),
        "by_actionable_profile_preset": _build_breakdown_rows(
            decisions,
            field_name="actionable_profile_preset",
            output_name="actionable_profile_preset",
        ),
        "by_overall_profile_confidence": _build_breakdown_rows(
            decisions,
            field_name="overall_profile_confidence",
            output_name="overall_profile_confidence",
        ),
        "by_relevant_role_confidence": _build_breakdown_rows(
            decisions,
            field_name="relevant_role_confidence",
            output_name="relevant_role_confidence",
        ),
    }


def _validate_reconciliation(
    *,
    decisions: list[dict[str, Any]],
    target_games: list[dict[str, Any]],
    baseline: dict[str, Any],
    paired: dict[str, Any],
    breakdowns: dict[str, list[dict[str, Any]]],
    coverage: dict[str, int],
) -> None:
    total = len(decisions)
    if baseline["decision_count"] != total:
        raise ValueError("Baseline decision totals do not reconcile.")
    if sum(game["decision_count"] for game in target_games) != total:
        raise ValueError("Target-game decision totals do not reconcile.")
    for game in target_games:
        expected_baseline = _build_match_results(
            game["decisions"],
            prediction_key="baseline_prediction",
        )
        if game["baseline_results"] != expected_baseline:
            raise ValueError("Target-game baseline results do not reconcile.")
        if game["actionable_profile_paired_results"] != _build_paired_results(
            game["decisions"]
        ):
            raise ValueError("Target-game paired results do not reconcile.")
    for count_name in (
        "exact_card_match_count",
        "preferred_card_match_count",
    ):
        if sum(game["baseline_results"][count_name] for game in target_games) != baseline[
            count_name
        ]:
            raise ValueError("Per-game and overall baseline results do not reconcile.")
    for count_name in (
        "paired_decision_count",
        "profile_exact_card_match_count",
        "baseline_exact_card_match_count",
        "profile_preferred_card_match_count",
        "baseline_preferred_card_match_count",
    ):
        if sum(
            game["actionable_profile_paired_results"][count_name]
            for game in target_games
        ) != paired[count_name]:
            raise ValueError("Per-game and overall paired results do not reconcile.")
    for outcomes_name in (
        "exact_comparison_outcome_counts",
        "preferred_comparison_outcome_counts",
    ):
        if sum(paired[outcomes_name].values()) != paired["paired_decision_count"]:
            raise ValueError("Paired comparison outcomes do not reconcile.")
    for prefix, outcomes_name in (
        ("exact_card", "exact_comparison_outcome_counts"),
        ("preferred_card", "preferred_comparison_outcome_counts"),
    ):
        outcomes = paired[outcomes_name]
        if paired[f"profile_{prefix}_match_count"] != (
            outcomes["both_match"] + outcomes["profile_only"]
        ):
            raise ValueError("Profile match counts do not reconcile with outcomes.")
        if paired[f"baseline_{prefix}_match_count"] != (
            outcomes["both_match"] + outcomes["baseline_only"]
        ):
            raise ValueError("Baseline match counts do not reconcile with outcomes.")

    full_coverage_breakdowns = (
        "by_player",
        "by_acting_side",
        "by_game_type",
        "by_decision_phase",
    )
    for breakdown_name, rows in breakdowns.items():
        expected_coverage = (
            total
            if breakdown_name in full_coverage_breakdowns
            else paired["paired_decision_count"]
            if breakdown_name == "by_actionable_profile_preset"
            else coverage["decisions_with_explainable_derived_profile"]
        )
        if sum(row["coverage_count"] for row in rows) != expected_coverage:
            raise ValueError(f"{breakdown_name} coverage does not reconcile.")
        if sum(row["actionable_paired_count"] for row in rows) != paired[
            "paired_decision_count"
        ]:
            raise ValueError(f"{breakdown_name} paired coverage does not reconcile.")
        if sum(
            row["profile_preferred_card_match_count"] for row in rows
        ) != paired["profile_preferred_card_match_count"]:
            raise ValueError(f"{breakdown_name} profile matches do not reconcile.")
        if sum(
            row["paired_baseline_preferred_card_match_count"] for row in rows
        ) != paired["baseline_preferred_card_match_count"]:
            raise ValueError(f"{breakdown_name} baseline matches do not reconcile.")


def evaluate_rolling_opponent_policy_predictions(
    dataset: TrainingDatasetInput,
    source_partitions: tuple[str, ...] = DEFAULT_SOURCE_PARTITIONS,
    evaluation_partitions: tuple[str, ...] = DEFAULT_EVALUATION_PARTITIONS,
) -> RollingOpponentPolicyEvaluation:
    """Evaluates time-safe profile policy imitation against a fixed baseline."""
    if (
        dataset.partition_policy is not None
        and dataset.partition_policy.mode == "unseen_player"
    ):
        raise ValueError(
            "Rolling opponent-policy evaluation is a known_opponent workflow and is "
            "incompatible with a declared unseen_player partition policy."
        )
    source, evaluation, targets = _validate_selection(
        dataset,
        source_partitions,
        evaluation_partitions,
    )
    source_records = [record for record in dataset.records if record.partition in source]
    all_decisions: list[dict[str, Any]] = []
    target_games = []
    any_prior_player_history = False

    for target in targets:
        target_played_at = target.historical_game.played_at
        if target_played_at is None:
            raise AssertionError("Validated target game lost its played_at timestamp.")
        target_instant = parse_rfc3339_datetime(target_played_at, "target played_at")
        eligible_sources = [
            record
            for record in source_records
            if parse_rfc3339_datetime(
                record.historical_game.played_at or "",
                f"Historical game '{record.historical_game.game_id}' played_at",
            )
            < target_instant
        ]
        aggregation = (
            aggregate_historical_opponent_statistics(
                dataset,
                included_partitions=source,
                before=target_played_at,
            )
            if eligible_sources
            else None
        )
        player_states = _build_player_states(target, aggregation)
        any_prior_player_history = any_prior_player_history or any(
            state.summary["history_status"] == "prior_player_history"
            for state in player_states.values()
        )
        historical_summary = build_historical_game_summary(target.historical_game)
        snapshots = build_historical_decision_snapshots(historical_summary)
        if snapshots.snapshot_count != SAMPLES_PER_TRAINING_RECORD:
            raise ValueError(
                f"Target game '{target.historical_game.game_id}' must contribute exactly "
                f"{SAMPLES_PER_TRAINING_RECORD} decisions."
            )
        decisions = [
            _build_decision(
                snapshot,
                player_state=player_states[snapshot.acting_player_id],
                declarer_player_id=target.historical_game.declarer_player_id,
            )
            for snapshot in snapshots.snapshots
        ]
        all_decisions.extend(decisions)
        target_games.append(
            {
                "target_record_id": target.record_id,
                "partition": target.partition,
                "game_id": target.historical_game.game_id,
                "played_at": target_played_at,
                "contract": build_serializable_game_declaration(
                    target.historical_game.declaration
                ),
                "participant_ids": [
                    player.player_id for player in target.historical_game.players
                ],
                "as_of_source_game_count": len(eligible_sources),
                "latest_eligible_source_played_at": (
                    aggregation.last_played_at if aggregation is not None else None
                ),
                "player_as_of_profiles": [
                    player_states[player.player_id].summary
                    for player in target.historical_game.players
                ],
                "decision_count": len(decisions),
                "baseline_results": _build_match_results(
                    decisions,
                    prediction_key="baseline_prediction",
                ),
                "actionable_profile_paired_results": _build_paired_results(decisions),
                "decisions": decisions,
            }
        )

    if not any_prior_player_history:
        raise ValueError(
            "Rolling opponent-policy evaluation requires at least one target participant "
            "with prior source history."
        )

    baseline = _build_match_results(
        all_decisions,
        prediction_key="baseline_prediction",
    )
    baseline.update(
        {
            "baseline_policy_preset": BASELINE_POLICY_PRESET,
            **get_opponent_policy_settings_for_preset(BASELINE_POLICY_PRESET),
        }
    )
    paired = _build_paired_results(all_decisions)
    breakdowns = _build_breakdowns(all_decisions)
    coverage = _build_coverage(all_decisions, len(targets))
    _validate_reconciliation(
        decisions=all_decisions,
        target_games=target_games,
        baseline=baseline,
        paired=paired,
        breakdowns=breakdowns,
        coverage=coverage,
    )
    memberships = collect_player_partition_memberships(dataset.records)
    source_player_ids = [
        membership.player_id
        for membership in memberships
        if any(partition in source for partition in membership.partitions)
    ]
    evaluation_player_ids = [
        membership.player_id
        for membership in memberships
        if any(partition in evaluation for partition in membership.partitions)
    ]
    source_player_lookup = set(source_player_ids)
    shared_player_ids = [
        player_id
        for player_id in evaluation_player_ids
        if player_id in source_player_lookup
    ]
    source_dataset = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "training_dataset_schema_version": dataset.schema_version,
        "feature_generation_version": dataset.feature_generation_version,
        "target": dataset.target,
    }
    if dataset.partition_policy is not None:
        source_dataset["partition_policy"] = (
            build_serializable_dataset_partition_policy(dataset.partition_policy)
        )
    return RollingOpponentPolicyEvaluation(
        schema_version=1,
        evaluation_version=ROLLING_OPPONENT_POLICY_EVALUATION_VERSION,
        source_dataset=source_dataset,
        selection={
            "evaluation_mode": "known_opponent",
            "source_partitions": list(source),
            "evaluation_partitions": list(evaluation),
            "temporal_rule": ROLLING_TEMPORAL_RULE,
            "selected_partition_player_overlap": {
                "source_distinct_player_count": len(source_player_ids),
                "evaluation_distinct_player_count": len(evaluation_player_ids),
                "shared_player_count": len(shared_player_ids),
                "shared_player_ids": shared_player_ids,
                "eligibility_basis": (
                    "partition_membership_only_not_temporal_eligibility"
                ),
            },
            "source_record_count": len(source_records),
            "target_record_count": len(targets),
            "target_game_count": len(targets),
            "target_decision_count": len(all_decisions),
        },
        coverage=coverage,
        baseline_results=baseline,
        actionable_profile_paired_results=paired,
        breakdowns=breakdowns,
        target_games=tuple(target_games),
    )


def build_serializable_rolling_opponent_policy_evaluation(
    evaluation: RollingOpponentPolicyEvaluation,
) -> dict[str, Any]:
    """Builds the stable public representation of a rolling evaluation."""
    return {
        "schema_version": evaluation.schema_version,
        "evaluation_version": evaluation.evaluation_version,
        "source_dataset": evaluation.source_dataset,
        "selection": evaluation.selection,
        "coverage": evaluation.coverage,
        "baseline_results": evaluation.baseline_results,
        "actionable_profile_paired_results": (
            evaluation.actionable_profile_paired_results
        ),
        "breakdowns": evaluation.breakdowns,
        "target_games": list(evaluation.target_games),
    }
