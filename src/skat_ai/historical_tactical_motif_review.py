from collections.abc import Callable
from typing import Any

from skat_ai.historical_decision_snapshot import (
    HISTORICAL_DECISION_INFORMATION_POLICY,
    HISTORICAL_DECISION_SNAPSHOT_SCHEMA_VERSION,
    HistoricalDecisionSnapshotSummary,
)
from skat_ai.tactical_motif_contracts import (
    HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD,
    HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION,
    TACTICAL_MOTIF_FAMILIES,
    TACTICAL_MOTIF_INFORMATION_POLICY,
    TACTICAL_MOTIF_REVIEW_LIMITATIONS,
    TACTICAL_MOTIF_TYPES,
    HistoricalTacticalMotifReviewV1,
    TacticalDecisionObservationV1,
    TacticalMotifScopeSummaryV1,
    build_serializable_historical_tactical_motif_review_v1,
)
from skat_ai.tactical_motif_detection import (
    build_tactical_decision_observation_from_snapshot_v1,
)


def _game_phase(trick_number: int) -> str:
    if 1 <= trick_number <= 3:
        return "opening"
    if 4 <= trick_number <= 7:
        return "middle"
    if 8 <= trick_number <= 10:
        return "endgame"
    raise ValueError("Historical tactical observations require Tricks 1 through 10.")


def _canonical_counts(
    observations: tuple[TacticalDecisionObservationV1, ...],
) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
    motif_counts = tuple(
        (
            motif_type,
            sum(
                motif.motif_type == motif_type
                for observation in observations
                for motif in observation.motifs
            ),
        )
        for motif_type in TACTICAL_MOTIF_TYPES
    )
    family_counts = tuple(
        (
            family,
            sum(
                motif.motif_family == family
                for observation in observations
                for motif in observation.motifs
            ),
        )
        for family in TACTICAL_MOTIF_FAMILIES
    )
    return motif_counts, family_counts


def _build_scope_summary(
    *,
    scope: str,
    scope_value: str,
    observations: tuple[TacticalDecisionObservationV1, ...],
    selector: Callable[[TacticalDecisionObservationV1], str],
) -> TacticalMotifScopeSummaryV1:
    selected = tuple(
        observation for observation in observations if selector(observation) == scope_value
    )
    motif_counts, family_counts = _canonical_counts(selected)
    return TacticalMotifScopeSummaryV1(
        scope=scope,
        scope_value=scope_value,
        observation_count=len(selected),
        complete_observation_count=sum(
            observation.observation_status == "complete" for observation in selected
        ),
        partial_observation_count=sum(
            observation.observation_status == "partial" for observation in selected
        ),
        motif_occurrence_count=sum(len(observation.motifs) for observation in selected),
        decision_indices=tuple(
            observation.decision_time_facts.decision_index for observation in selected
        ),
        motif_counts=motif_counts,
        family_counts=family_counts,
    )


def _build_scope_summaries(
    *,
    observations: tuple[TacticalDecisionObservationV1, ...],
    participant_player_ids: tuple[str, str, str],
    game_type: str,
) -> tuple[
    tuple[TacticalMotifScopeSummaryV1, ...],
    tuple[TacticalMotifScopeSummaryV1, ...],
    tuple[TacticalMotifScopeSummaryV1, ...],
    tuple[TacticalMotifScopeSummaryV1, ...],
]:
    selectors: dict[str, Callable[[TacticalDecisionObservationV1], str]] = {
        "player": lambda item: item.decision_time_facts.acting_player_id,
        "role": lambda item: item.decision_time_facts.acting_side,
        "phase": lambda item: _game_phase(item.decision_time_facts.trick_number),
        "contract": lambda item: item.decision_time_facts.game_type,
    }
    values = {
        "player": participant_player_ids,
        "role": ("declarer", "defenders"),
        "phase": ("opening", "middle", "endgame"),
        "contract": (game_type,),
    }
    return tuple(
        tuple(
            _build_scope_summary(
                scope=scope,
                scope_value=scope_value,
                observations=observations,
                selector=selectors[scope],
            )
            for scope_value in values[scope]
        )
        for scope in ("player", "role", "phase", "contract")
    )


def build_historical_tactical_motif_review_v1(
    *,
    historical_game_result: dict[str, object],
    decision_snapshot_summary: HistoricalDecisionSnapshotSummary,
) -> HistoricalTacticalMotifReviewV1:
    """Builds a tactical report from one retained Result and Snapshot sequence."""
    if not isinstance(historical_game_result, dict):
        raise ValueError("historical_game_result must be a validated object.")
    if historical_game_result.get("status") != "complete":
        raise ValueError("historical_game_result must be complete.")
    if not isinstance(decision_snapshot_summary, HistoricalDecisionSnapshotSummary):
        raise ValueError("decision_snapshot_summary must be HistoricalDecisionSnapshotSummary.")
    if (
        decision_snapshot_summary.schema_version != HISTORICAL_DECISION_SNAPSHOT_SCHEMA_VERSION
        or decision_snapshot_summary.information_policy != HISTORICAL_DECISION_INFORMATION_POLICY
    ):
        raise ValueError("Decision Snapshot contract metadata is invalid.")

    record = historical_game_result.get("record")
    derived_tricks = historical_game_result.get("derived_tricks")
    if not isinstance(record, dict) or not isinstance(derived_tricks, list):
        raise ValueError("historical_game_result is missing retained replay facts.")
    source_game_id = record.get("game_id")
    declarer_player_id = record.get("declarer_player_id")
    declaration = record.get("declaration")
    players = record.get("players")
    tricks = record.get("tricks")
    if (
        not isinstance(source_game_id, str)
        or not isinstance(declarer_player_id, str)
        or not isinstance(declaration, dict)
        or not isinstance(declaration.get("game_type"), str)
        or not isinstance(players, list)
        or not isinstance(tricks, list)
    ):
        raise ValueError("historical_game_result record metadata is invalid.")
    if historical_game_result.get("game_id") != source_game_id:
        raise ValueError("Historical Result and record Game identities do not match.")
    players_by_seat = {
        player.get("seat"): player.get("player_id")
        for player in players
        if isinstance(player, dict)
    }
    participant_player_ids = tuple(
        players_by_seat.get(seat) for seat in ("forehand", "middlehand", "rearhand")
    )
    if any(not isinstance(player_id, str) for player_id in participant_player_ids):
        raise ValueError("Historical Result must retain exactly three seated Players.")

    source_plays: list[tuple[int, int, dict[str, Any], bool]] = []
    for trick in tricks:
        if not isinstance(trick, dict) or not isinstance(trick.get("plays"), list):
            raise ValueError("Historical Result retained Tricks are invalid.")
        trick_number = trick.get("trick_number")
        plays = trick["plays"]
        for play_index, play in enumerate(plays, start=1):
            if not isinstance(trick_number, int) or not isinstance(play, dict):
                raise ValueError("Historical Result retained Plays are invalid.")
            source_plays.append((trick_number, play_index, play, len(plays) == 3))
    if decision_snapshot_summary.snapshot_count != len(source_plays) or len(
        decision_snapshot_summary.snapshots
    ) != len(source_plays):
        raise ValueError("Decision Snapshots do not reconcile with source Plays.")

    completed_by_trick: dict[int, dict[str, Any]] = {}
    for outcome in derived_tricks:
        if not isinstance(outcome, dict) or not isinstance(outcome.get("trick_number"), int):
            raise ValueError("Historical Result derived Tricks are invalid.")
        completed_by_trick[outcome["trick_number"]] = outcome

    observations = []
    for decision_index, (snapshot, source_play) in enumerate(
        zip(
            decision_snapshot_summary.snapshots,
            source_plays,
            strict=True,
        ),
        start=1,
    ):
        trick_number, play_index, play, source_trick_complete = source_play
        if (
            snapshot.source_game_id != source_game_id
            or snapshot.decision_index != decision_index
            or snapshot.trick_number != trick_number
            or snapshot.play_index != play_index
            or snapshot.acting_player_id != play.get("player_id")
        ):
            raise ValueError("Decision Snapshot and source Play identities do not match.")
        outcome = completed_by_trick.get(trick_number) if source_trick_complete else None
        if source_trick_complete and outcome is None:
            raise ValueError("A completed source Trick is missing its retained outcome.")
        observation = build_tactical_decision_observation_from_snapshot_v1(
            snapshot=snapshot,
            declarer_player_id=declarer_player_id,
            participant_player_ids=participant_player_ids,
            completed_trick_winner_player_id=(
                None if outcome is None else outcome.get("winner_player_id")
            ),
            completed_trick_winner_side=(None if outcome is None else outcome.get("winner_side")),
            completed_trick_points=(None if outcome is None else outcome.get("trick_points")),
        )
        if observation.actual_card != play.get("card"):
            raise ValueError("Decision Snapshot and source Play Cards do not match.")
        observations.append(observation)
    if set(completed_by_trick) != {
        trick_number
        for trick_number, _, _, source_trick_complete in source_plays
        if source_trick_complete
    }:
        raise ValueError("Retained completed-Trick outcomes do not reconcile.")

    observation_tuple = tuple(observations)
    motif_counts, family_counts = _canonical_counts(observation_tuple)
    player, role, phase, contract = _build_scope_summaries(
        observations=observation_tuple,
        participant_player_ids=participant_player_ids,
        game_type=declaration["game_type"],
    )
    return HistoricalTacticalMotifReviewV1(
        historical_tactical_motif_review_version=(HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION),
        review_method=HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD,
        information_policy=TACTICAL_MOTIF_INFORMATION_POLICY,
        source_game_id=source_game_id,
        observation_count=len(observation_tuple),
        complete_observation_count=sum(
            observation.observation_status == "complete" for observation in observation_tuple
        ),
        partial_observation_count=sum(
            observation.observation_status == "partial" for observation in observation_tuple
        ),
        motif_occurrence_count=sum(len(observation.motifs) for observation in observation_tuple),
        observations=observation_tuple,
        motif_counts=motif_counts,
        family_counts=family_counts,
        player_summaries=player,
        role_summaries=role,
        phase_summaries=phase,
        contract_summaries=contract,
        limitations=TACTICAL_MOTIF_REVIEW_LIMITATIONS,
    )


__all__ = (
    "build_historical_tactical_motif_review_v1",
    "build_serializable_historical_tactical_motif_review_v1",
)
