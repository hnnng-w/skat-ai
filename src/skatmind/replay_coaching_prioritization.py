from collections.abc import Callable
from dataclasses import InitVar, dataclass
from typing import Any

from skatmind.historical_game import HistoricalGameRecord
from skatmind.replay_coaching_evidence import REPLAY_COACHING_CONTRACT_VERSION
from skatmind.replay_coaching_key_decisions import (
    MAX_REPLAY_COACHING_KEY_DECISIONS,
    REPLAY_COACHING_PRIORITIZATION_VERSION,
    REPLAY_COACHING_TURNING_POINT_TYPES,
    ReplayCoachingKeyDecision,
    build_replay_coaching_key_decisions,
    build_serializable_replay_coaching_key_decision,
)
from skatmind.replay_coaching_method_neutral import (
    get_replay_coaching_assessment_version,
    validate_supported_replay_coaching_assessment,
)
from skatmind.replay_coaching_turning_points import (
    REPLAY_COACHING_RECORDED_STATES,
    ReplayCoachingTurningPoint,
    build_recorded_decision_state_timeline,
    build_replay_coaching_turning_points,
    build_serializable_replay_coaching_turning_point,
)


def _is_invalid_assessment(assessment: Any) -> bool:
    try:
        validate_supported_replay_coaching_assessment(assessment)
    except ValueError:
        return True
    return False


def _decision_index(assessment: Any) -> int:
    return assessment.decision_time_evidence.decision_index


def validate_replay_coaching_assessment_sequence(
    record: HistoricalGameRecord,
    assessments: tuple[Any, ...],
) -> None:
    """Validates one complete chronological assessment sequence against its record."""
    if not isinstance(record, HistoricalGameRecord):
        raise ValueError("record must be HistoricalGameRecord.")
    if not isinstance(assessments, tuple):
        raise TypeError("assessments must be a tuple.")
    if any(_is_invalid_assessment(assessment) for assessment in assessments):
        raise ValueError("assessments must contain coaching assessments.")
    actual_plays = tuple(
        (trick.trick_number, play_index, play.player_id, play.card)
        for trick in record.tricks
        for play_index, play in enumerate(trick.plays, start=1)
    )
    if len(actual_plays) != len(assessments):
        raise ValueError("Assessment count must match the historical card-play count.")
    if not 0 <= len(assessments) <= 30:
        raise ValueError("Replay Coaching supports zero through thirty decisions.")
    expected_indices = tuple(range(1, len(assessments) + 1))
    actual_indices = tuple(_decision_index(assessment) for assessment in assessments)
    if actual_indices != expected_indices or len(actual_indices) != len(set(actual_indices)):
        raise ValueError("Assessments must use unique contiguous chronological indices.")
    player_seats = {player.player_id: player.seat for player in record.players}
    for assessment, (trick_number, play_index, player_id, card) in zip(
        assessments, actual_plays, strict=True
    ):
        evidence = assessment.decision_time_evidence
        if (
            get_replay_coaching_assessment_version(assessment)
            != REPLAY_COACHING_CONTRACT_VERSION
        ):
            raise ValueError("Assessment contract version is unsupported.")
        if evidence.source_game_id != record.game_id:
            raise ValueError("Assessments must belong to one source game.")
        if (
            evidence.trick_number != trick_number
            or evidence.play_index != play_index
            or evidence.acting_player_id != player_id
            or evidence.acting_seat != player_seats[player_id]
            or evidence.local_side
            != ("declarer" if player_id == record.declarer_player_id else "defenders")
            or evidence.game_type != record.declaration.game_type
        ):
            raise ValueError("Assessment identity must match actual historical play order.")
        if assessment.actual_card != card:
            raise ValueError("Assessment actual_card must match the historical record.")


@dataclass(frozen=True)
class ReplayCoachingPrioritizationResult:
    """Version-1 game-level Key Decision and Turning Point prioritization."""

    prioritization_version: int
    source_game_id: str
    decision_count: int
    assessable_decision_count: int
    missed_impact_decision_count: int
    high_impact_decision_count: int
    recorded_initial_state: str
    recorded_final_state: str
    key_decisions: tuple[ReplayCoachingKeyDecision, ...]
    turning_points: tuple[ReplayCoachingTurningPoint, ...]
    record: InitVar[HistoricalGameRecord]
    assessments: InitVar[tuple[Any, ...]]

    def __post_init__(
        self,
        record: HistoricalGameRecord,
        assessments: tuple[Any, ...],
    ) -> None:
        if (
            isinstance(self.prioritization_version, bool)
            or not isinstance(self.prioritization_version, int)
            or self.prioritization_version != REPLAY_COACHING_PRIORITIZATION_VERSION
        ):
            raise ValueError("Unsupported replay-coaching prioritization version.")
        if (
            not isinstance(self.source_game_id, str)
            or not self.source_game_id
            or self.source_game_id != self.source_game_id.strip()
        ):
            raise ValueError("source_game_id must be a non-empty string.")
        if not isinstance(record, HistoricalGameRecord):
            raise ValueError("record must be HistoricalGameRecord.")
        if not isinstance(assessments, tuple):
            raise TypeError("assessments must be a tuple.")
        for field_name, value in (
            ("decision_count", self.decision_count),
            ("assessable_decision_count", self.assessable_decision_count),
            ("missed_impact_decision_count", self.missed_impact_decision_count),
            ("high_impact_decision_count", self.high_impact_decision_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        validate_replay_coaching_assessment_sequence(record, assessments)
        if record.game_id != self.source_game_id:
            raise ValueError("record must match the result source game.")
        if self.decision_count != len(assessments):
            raise ValueError("decision_count must match assessments.")
        if any(_is_invalid_assessment(assessment) for assessment in assessments):
            raise ValueError("assessments must contain coaching assessments.")
        if any(
            get_replay_coaching_assessment_version(assessment)
            != REPLAY_COACHING_CONTRACT_VERSION
            or assessment.decision_time_evidence.source_game_id != self.source_game_id
            for assessment in assessments
        ):
            raise ValueError("Assessments must match the result source and contract version.")
        assessable_count = sum(
            assessment.assessment_status != "not_assessable"
            for assessment in assessments
        )
        missed_count = sum(
            assessment.assessment_status == "strictly_below_best"
            for assessment in assessments
        )
        if self.assessable_decision_count != assessable_count:
            raise ValueError("assessable_decision_count does not reconcile.")
        if self.missed_impact_decision_count != missed_count:
            raise ValueError("missed_impact_decision_count does not reconcile.")
        if self.recorded_initial_state not in REPLAY_COACHING_RECORDED_STATES:
            raise ValueError("recorded_initial_state is unsupported.")
        if self.recorded_final_state not in REPLAY_COACHING_RECORDED_STATES:
            raise ValueError("recorded_final_state is unsupported.")
        if not isinstance(self.key_decisions, tuple) or not isinstance(
            self.turning_points, tuple
        ):
            raise TypeError("Key Decisions and Turning Points must be tuples.")
        if len(self.key_decisions) > MAX_REPLAY_COACHING_KEY_DECISIONS:
            raise ValueError("Too many Key Decisions.")
        if tuple(key.rank for key in self.key_decisions) != tuple(
            range(1, len(self.key_decisions) + 1)
        ):
            raise ValueError("Key Decision ranks must be contiguous and one-based.")
        assessment_by_index = {
            _decision_index(assessment): assessment for assessment in assessments
        }
        key_indices = tuple(
            _decision_index(key.assessment) for key in self.key_decisions
        )
        if len(key_indices) != len(set(key_indices)):
            raise ValueError("No decision may appear twice among Key Decisions.")
        for key in self.key_decisions:
            if assessment_by_index.get(_decision_index(key.assessment)) != key.assessment:
                raise ValueError("Key Decisions must be a subset of assessments.")
        turning_order = tuple(
            (
                _decision_index(point.assessment),
                REPLAY_COACHING_TURNING_POINT_TYPES.index(point.turning_point_type),
            )
            for point in self.turning_points
        )
        if turning_order != tuple(sorted(turning_order)) or len(turning_order) != len(
            set(turning_order)
        ):
            raise ValueError("Turning Points must be unique and canonically ordered.")
        for point in self.turning_points:
            if assessment_by_index.get(_decision_index(point.assessment)) != point.assessment:
                raise ValueError("Turning Points must be a subset of assessments.")
        recorded_count = sum(
            point.turning_point_type == "recorded_outcome"
            for point in self.turning_points
        )
        if recorded_count > 1:
            raise ValueError("At most one recorded-outcome Turning Point is allowed.")
        expected_turning_points = build_replay_coaching_turning_points(
            record,
            assessments,
        )
        if self.turning_points != expected_turning_points:
            raise ValueError("Turning Points do not match the source record and assessments.")
        expected_states = build_recorded_decision_state_timeline(record)
        if (
            self.recorded_initial_state != expected_states[0]
            or self.recorded_final_state != expected_states[-1]
        ):
            raise ValueError("Recorded states do not match the source record.")
        turning_types_by_decision = {
            decision_index: tuple(
                turning_type
                for turning_type in REPLAY_COACHING_TURNING_POINT_TYPES
                if any(
                    point.decision_index == decision_index
                    and point.turning_point_type == turning_type
                    for point in self.turning_points
                )
            )
            for decision_index in assessment_by_index
        }
        expected_keys = build_replay_coaching_key_decisions(
            assessments,
            turning_types_by_decision,
        )
        if self.key_decisions != expected_keys:
            raise ValueError("Key Decisions do not match deterministic selection and ranking.")
        recorded_point = next(
            (
                point
                for point in self.turning_points
                if point.turning_point_type == "recorded_outcome"
            ),
            None,
        )
        if recorded_point is not None and (
            self.recorded_initial_state != "undecided"
            or self.recorded_final_state != recorded_point.recorded_state_after
        ):
            raise ValueError("Recorded states do not match the outcome Turning Point.")
        high_impact_indices = {
            _decision_index(key.assessment)
            for key in self.key_decisions
            if key.is_high_impact
        }
        high_impact_indices.update(
            _decision_index(point.assessment) for point in self.turning_points
        )
        if self.high_impact_decision_count != len(high_impact_indices):
            raise ValueError("high_impact_decision_count does not reconcile.")


def build_replay_coaching_prioritization_result(
    record: HistoricalGameRecord,
    assessments: tuple[Any, ...],
) -> ReplayCoachingPrioritizationResult:
    """Builds deterministic game-level prioritization from one record and assessment tuple."""
    if not isinstance(assessments, tuple):
        raise TypeError("assessments must be a tuple.")
    copied_assessments = tuple(assessments)
    validate_replay_coaching_assessment_sequence(record, copied_assessments)
    turning_points = build_replay_coaching_turning_points(record, copied_assessments)
    turning_types_by_decision: dict[int, tuple[str, ...]] = {}
    for assessment in copied_assessments:
        decision_index = _decision_index(assessment)
        turning_types_by_decision[decision_index] = tuple(
            turning_type
            for turning_type in REPLAY_COACHING_TURNING_POINT_TYPES
            if any(
                _decision_index(point.assessment) == decision_index
                and point.turning_point_type == turning_type
                for point in turning_points
            )
        )
    key_decisions = build_replay_coaching_key_decisions(
        copied_assessments,
        turning_types_by_decision,
    )
    states = build_recorded_decision_state_timeline(record)
    high_impact_indices = {
        _decision_index(key.assessment)
        for key in key_decisions
        if key.is_high_impact
    }
    high_impact_indices.update(
        _decision_index(point.assessment) for point in turning_points
    )
    return ReplayCoachingPrioritizationResult(
        prioritization_version=REPLAY_COACHING_PRIORITIZATION_VERSION,
        source_game_id=record.game_id,
        decision_count=len(copied_assessments),
        assessable_decision_count=sum(
            assessment.assessment_status != "not_assessable"
            for assessment in copied_assessments
        ),
        missed_impact_decision_count=sum(
            assessment.assessment_status == "strictly_below_best"
            for assessment in copied_assessments
        ),
        high_impact_decision_count=len(high_impact_indices),
        recorded_initial_state=states[0],
        recorded_final_state=states[-1],
        key_decisions=key_decisions,
        turning_points=turning_points,
        record=record,
        assessments=copied_assessments,
    )


def build_serializable_replay_coaching_prioritization_result(
    result: ReplayCoachingPrioritizationResult,
    *,
    assessment_serializer: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "prioritization_version": result.prioritization_version,
        "source_game_id": result.source_game_id,
        "decision_count": result.decision_count,
        "assessable_decision_count": result.assessable_decision_count,
        "missed_impact_decision_count": result.missed_impact_decision_count,
        "high_impact_decision_count": result.high_impact_decision_count,
        "recorded_initial_state": result.recorded_initial_state,
        "recorded_final_state": result.recorded_final_state,
        "key_decisions": [
            build_serializable_replay_coaching_key_decision(
                key,
                assessment_serializer=assessment_serializer,
            )
            for key in result.key_decisions
        ],
        "turning_points": [
            build_serializable_replay_coaching_turning_point(
                point,
                assessment_serializer=assessment_serializer,
            )
            for point in result.turning_points
        ],
    }
