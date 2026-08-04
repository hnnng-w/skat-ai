import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.game_declaration import build_serializable_game_declaration
from skat_ai.historical_game import (
    HISTORICAL_GAME_END_REASON,
    HISTORICAL_SEATS,
    HistoricalGameRecord,
    build_historical_game_summary,
)

REPLAY_COACHING_PLAYER_SIDES = ("declarer", "defenders")
REPLAY_COACHING_TERMINAL_SUMMARY_FIELD_BY_END_REASON = MappingProxyType(
    {
        HISTORICAL_GAME_END_REASON: None,
        "declarer_concession": "historical_game_end_summary",
        "defender_concession": "historical_game_end_summary",
        "declarer_card_exposure": "historical_game_end_summary",
        "defender_open_play": "historical_game_end_summary",
        "open_card_throw": "historical_game_end_summary",
    }
)

_TERMINAL_SUMMARY_FIELDS = {
    "declarer_concession": (
        "schema_version",
        "kind",
        "rule_sections",
        "declarer_hand_cards_remaining",
        "hand_card_count_reconciliation",
        "consent_required",
        "defender_consent",
        "adjudicated_winner",
        "remaining_points_assigned",
        "settlement_level_policy",
        "declarer_player_id",
        "event_after_play_count",
        "event_after_completed_trick_count",
        "event_during_incomplete_trick",
    ),
    "defender_concession": (
        "schema_version",
        "kind",
        "rule_sections",
        "concession_form",
        "liable_party",
        "joint_liability",
        "decision_state_before_concession",
        "adjudicated_winner",
        "winner_basis",
        "remaining_points_assigned",
        "continued_play_requested",
        "settlement_level_policy",
        "conceding_defender_player_id",
        "non_conceding_defender_player_id",
        "event_after_play_count",
        "event_after_completed_trick_count",
        "event_during_incomplete_trick",
    ),
    "declarer_card_exposure": (
        "schema_version",
        "kind",
        "rule_sections",
        "exposure_form",
        "exposed_card_count",
        "unanimous_defender_acceptance",
        "claimed_play_level",
        "decision_state_before_shortening",
        "adjudicated_winner",
        "winner_basis",
        "continued_play_required",
        "remaining_points_assigned",
        "settlement_level_policy",
        "declarer_player_id",
        "shown_to_defender_player_id",
        "accepting_defender_player_ids",
        "acceptance_forms",
        "event_after_play_count",
        "event_after_completed_trick_count",
        "event_during_incomplete_trick",
    ),
    "defender_open_play": (
        "schema_version",
        "kind",
        "rule_sections",
        "declarer_player_id",
        "exposing_defender_player_id",
        "non_exposing_defender_player_id",
        "defending_party_player_ids",
        "exposed_card_count",
        "declarer_response",
        "decision_state_before_shortening",
        "remaining_trick_count",
        "rest_trick_assignment",
        "rest_tricks_recipient",
        "adjudicated_winner",
        "winner_basis",
        "continued_play_requested",
        "event_after_play_count",
        "event_after_completed_trick_count",
        "event_during_incomplete_trick",
    ),
    "open_card_throw": (
        "schema_version",
        "kind",
        "rule_sections",
        "throwing_party",
        "opposing_party",
        "joint_liability",
        "thrown_card_count",
        "statement_classification",
        "decision_state_before_shortening",
        "rest_trick_assignment",
        "rest_tricks_recipient",
        "remaining_trick_count",
        "observed_trick_counts",
        "rule_assigned_trick_counts",
        "final_trick_counts",
        "observed_points",
        "rule_assigned_points",
        "final_points",
        "adjudicated_winner",
        "winner_basis",
        "schneider_rule_level_applied",
        "schwarz_rule_level_applied",
        "theoretical_schwarz_status",
        "continued_play_supported",
        "declarer_player_id",
        "throwing_player_id",
        "event_after_play_count",
        "event_after_completed_trick_count",
        "event_during_incomplete_trick",
    ),
}

_EVENT_SUMMARY_FIELDS = (
    "event_index",
    "kind",
    "rule_sections",
    "after_play_count",
    "after_completed_trick_count",
    "event_during_incomplete_trick",
    "next_player_id",
    "declarer_player_id",
    "exposing_defender_player_id",
    "non_exposing_defender_player_id",
    "exposed_card_count",
    "declarer_response",
    "exposure_form",
    "shown_to_defender_player_id",
    "defender_responses",
    "continuing_defender_player_ids",
    "accepting_defender_player_ids",
    "unanimous_acceptance",
    "continuation_required",
    "public_declarer_card_count",
    "cards_returned_to_hand",
    "cards_remain_in_declarer_hand",
    "hand_physically_open",
    "visibility_scope",
    "claimed_play_level",
    "claimed_play_level_status",
    "rest_trick_claim",
    "rest_trick_claim_status",
    "continued_play_effect",
    "first_affected_decision_index",
    "actual_plays_after_event",
    "exact_proof_applied",
    "game_end_applied",
    "settlement_applied",
    "final_game_end_reason",
    "final_outcome_source",
)

_DECLARATION_FIELDS = (
    "game_type",
    "hand_game",
    "ouvert",
    "schneider_announced",
    "schwarz_announced",
    "matadors",
    "bid_value",
)
_GAME_RESULT_SUMMARY_FIELDS = (
    "declarer_points",
    "defender_points",
    "points_remaining",
    "is_complete",
    "winner",
    "status",
    "raw_schneider_status",
    "raw_schwarz_status",
    "effective_schneider_status",
    "effective_schwarz_status",
    "thresholds",
    "game_end_reason",
    "game_end_kind",
    "outcome_source",
    "winner_basis",
    "decision_state_before_game_end",
    "mandatory_level_awarded",
    "mandatory_level_source",
    "claimed_play_level",
    "declared_mandatory_schneider_applied",
    "declared_mandatory_schwarz_applied",
    "accepted_claimed_schneider_applied",
    "accepted_claimed_schwarz_applied",
    "achieved_schneider_applied",
    "achieved_schwarz_applied",
    "overbid_required_value_applied",
    "overbid_requirement_covered",
    "settlement_play_level_count",
    "rest_trick_proof_status",
    "rest_tricks_recipient",
    "mandatory_play_level",
    "rest_trick_assignment",
    "observed_trick_counts",
    "rule_assigned_trick_counts",
    "final_trick_counts",
    "observed_points",
    "rule_assigned_points",
    "final_points",
    "schneider_level_source",
    "schwarz_level_source",
    "theoretical_schwarz_status",
    "declared_mandatory_play_level",
    "mandatory_level_covered",
    "open_throw_schneider_applied",
    "open_throw_schwarz_applied",
    "overbid_required_level",
    "normally_played_declarer_trick_count",
    "rule_assigned_declarer_trick_count",
    "remaining_points_recipient",
    "remaining_points_assigned",
)
_GAME_VALUE_SUMMARY_FIELDS = (
    "game_type",
    "is_null_game",
    "base_value",
    "game_level",
    "game_value",
    "details",
)
_OVERBID_SUMMARY_FIELDS = (
    "bid_value",
    "game_value",
    "is_overbid",
    "margin",
    "required_game_value",
    "status",
)
_FINAL_SETTLEMENT_SUMMARY_FIELDS = (
    "is_complete",
    "missing_inputs",
    "declarer_won_by_card_points",
    "winner",
    "game_value",
    "effective_game_value",
    "bid_value",
    "settlement_score",
    "is_loss",
    "is_overbid",
    "overbid_margin",
    "overbid_status",
    "overbid_required_game_value",
    "settlement_basis",
    "notes",
)
_PRIVATE_CONTEXT_FIELDS = {
    "record",
    "initial_hand",
    "hand",
    "final_hidden_hands",
    "skat",
    "discarded_cards",
    "discards",
    "derived_tricks",
    "incomplete_current_trick",
    "selected_worlds",
    "ownership",
    "jack_ownership_evidence",
    "exact_proof",
    "theoretical_schwarz_assessment",
    "derived_child_seed",
    "cache",
    "branches",
    "principal_variation",
    "rating",
    "grade",
    "exposed_cards",
    "public_declarer_cards",
    "thrown_cards",
    "card_reconciliation",
}


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def _copy_allowed_fields(
    source: Mapping[str, Any],
    allowed_fields: tuple[str, ...],
) -> Mapping[str, Any]:
    return _freeze_json_value(
        {field: source[field] for field in allowed_fields if field in source}
    )


def _validate_json_value(value: Any, field_name: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must contain finite JSON numbers.")
        return
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError(f"{field_name} must contain only string object keys.")
        for key, item in value.items():
            _validate_json_value(item, f"{field_name}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{field_name}[{index}]")
        return
    raise ValueError(f"{field_name} must contain only JSON-compatible values.")


def _validate_no_private_fields(value: Any, field_name: str) -> None:
    if isinstance(value, Mapping):
        prohibited = tuple(key for key in value if key in _PRIVATE_CONTEXT_FIELDS)
        if prohibited:
            raise ValueError(f"{field_name} contains private fields: {prohibited}.")
        for key, item in value.items():
            _validate_no_private_fields(item, f"{field_name}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_no_private_fields(item, f"{field_name}[{index}]")


def _validate_allowed_mapping(
    value: Mapping[str, Any],
    allowed_fields: tuple[str, ...],
    field_name: str,
) -> None:
    unexpected = tuple(key for key in value if key not in allowed_fields)
    if unexpected:
        raise ValueError(f"{field_name} contains unsupported fields: {unexpected}.")
    _validate_json_value(value, field_name)
    _validate_no_private_fields(value, field_name)


@dataclass(frozen=True)
class ReplayCoachingPlayerContext:
    """Privacy-safe identity and table position for one historical player."""

    player_id: str
    player_label: str | None
    seat: str
    side: str

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, str) or not self.player_id:
            raise ValueError("player_id must be a non-empty string.")
        if self.player_label is not None and (
            not isinstance(self.player_label, str) or not self.player_label
        ):
            raise ValueError("player_label must be a non-empty string or null.")
        if self.seat not in HISTORICAL_SEATS:
            raise ValueError("seat must be a supported historical seat.")
        if self.side not in REPLAY_COACHING_PLAYER_SIDES:
            raise ValueError("side must be declarer or defenders.")


@dataclass(frozen=True)
class ReplayCoachingGameContext:
    """Privacy-safe source-game context without card ownership."""

    source_game_id: str
    played_at: str | None
    players: tuple[ReplayCoachingPlayerContext, ...]
    declarer_player_id: str
    game_type: str
    declaration: Mapping[str, Any]
    game_end_reason: str
    continuation_event_kinds: tuple[str, ...]
    recorded_play_count: int
    recorded_decision_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.players, tuple) or len(self.players) != 3:
            raise ValueError("players must contain exactly three player contexts.")
        if tuple(player.seat for player in self.players) != HISTORICAL_SEATS:
            raise ValueError("players must use historical seat order.")
        if len({player.player_id for player in self.players}) != 3:
            raise ValueError("player contexts must have unique player IDs.")
        declarers = tuple(player for player in self.players if player.side == "declarer")
        if (
            len(declarers) != 1
            or declarers[0].player_id != self.declarer_player_id
        ):
            raise ValueError("player sides must identify the source declarer.")
        if not isinstance(self.declaration, Mapping):
            raise ValueError("declaration must be a mapping.")
        if tuple(self.declaration) != _DECLARATION_FIELDS:
            raise ValueError("declaration must use the normalized declaration fields.")
        _validate_json_value(self.declaration, "declaration")
        if not isinstance(self.continuation_event_kinds, tuple):
            raise TypeError("continuation_event_kinds must be a tuple.")
        for field_name in ("recorded_play_count", "recorded_decision_count"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.recorded_play_count != self.recorded_decision_count:
            raise ValueError("Recorded plays and coaching decisions must reconcile.")
        object.__setattr__(self, "players", tuple(self.players))
        object.__setattr__(self, "declaration", _freeze_json_value(self.declaration))
        object.__setattr__(
            self, "continuation_event_kinds", tuple(self.continuation_event_kinds)
        )


@dataclass(frozen=True)
class ReplayCoachingOutcomeContext:
    """Final retrospective context kept separate from coaching evidence."""

    source_game_id: str
    game_end_reason: str
    status: str
    game_result_summary: Mapping[str, Any]
    game_value_summary: Mapping[str, Any]
    overbid_summary: Mapping[str, Any]
    final_settlement_summary: Mapping[str, Any]
    historical_game_events_summary: Mapping[str, Any] | None
    historical_game_end_summary: Mapping[str, Any] | None

    def __post_init__(self) -> None:
        expected_terminal_field = REPLAY_COACHING_TERMINAL_SUMMARY_FIELD_BY_END_REASON.get(
            self.game_end_reason
        )
        if self.game_end_reason not in REPLAY_COACHING_TERMINAL_SUMMARY_FIELD_BY_END_REASON:
            raise ValueError("Unsupported historical game-end reason.")
        if (self.historical_game_end_summary is None) != (
            expected_terminal_field is None
        ):
            raise ValueError("Terminal summary presence must match the game-end reason.")
        for field_name in (
            "game_result_summary",
            "game_value_summary",
            "overbid_summary",
            "final_settlement_summary",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, Mapping):
                raise ValueError(f"{field_name} must be a mapping.")
            _validate_allowed_mapping(
                value,
                {
                    "game_result_summary": _GAME_RESULT_SUMMARY_FIELDS,
                    "game_value_summary": _GAME_VALUE_SUMMARY_FIELDS,
                    "overbid_summary": _OVERBID_SUMMARY_FIELDS,
                    "final_settlement_summary": _FINAL_SETTLEMENT_SUMMARY_FIELDS,
                }[field_name],
                field_name,
            )
            object.__setattr__(self, field_name, _freeze_json_value(value))
        for field_name in (
            "historical_game_events_summary",
            "historical_game_end_summary",
        ):
            value = getattr(self, field_name)
            if value is not None:
                if not isinstance(value, Mapping):
                    raise ValueError(f"{field_name} must be a mapping or null.")
                _validate_json_value(value, field_name)
                _validate_no_private_fields(value, field_name)
                if field_name == "historical_game_events_summary":
                    if set(value) != {"schema_version", "event_count", "events"}:
                        raise ValueError("Historical event context fields are invalid.")
                    events = value["events"]
                    if not isinstance(events, (list, tuple)) or any(
                        not isinstance(event, Mapping)
                        or any(key not in _EVENT_SUMMARY_FIELDS for key in event)
                        for event in events
                    ):
                        raise ValueError("Historical event summaries are invalid.")
                elif any(
                    key not in _TERMINAL_SUMMARY_FIELDS[self.game_end_reason]
                    for key in value
                ):
                    raise ValueError("Historical terminal summary fields are invalid.")
                object.__setattr__(self, field_name, _freeze_json_value(value))


def build_replay_coaching_game_context(
    record: HistoricalGameRecord,
    *,
    recorded_decision_count: int,
) -> ReplayCoachingGameContext:
    """Builds context from public identity and declaration fields only."""
    players_by_seat = {player.seat: player for player in record.players}
    players = tuple(
        ReplayCoachingPlayerContext(
            player_id=players_by_seat[seat].player_id,
            player_label=players_by_seat[seat].player_label,
            seat=seat,
            side=(
                "declarer"
                if players_by_seat[seat].player_id == record.declarer_player_id
                else "defenders"
            ),
        )
        for seat in HISTORICAL_SEATS
    )
    recorded_play_count = sum(len(trick.plays) for trick in record.tricks)
    return ReplayCoachingGameContext(
        source_game_id=record.game_id,
        played_at=record.played_at,
        players=players,
        declarer_player_id=record.declarer_player_id,
        game_type=record.declaration.game_type,
        declaration=build_serializable_game_declaration(record.declaration),
        game_end_reason=record.game_end_reason,
        continuation_event_kinds=tuple(event.kind for event in record.game_events),
        recorded_play_count=recorded_play_count,
        recorded_decision_count=recorded_decision_count,
    )


def _build_safe_events_summary(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    events = summary.get("events")
    if not isinstance(events, (list, tuple)):
        raise ValueError("historical_game_events_summary.events must be an array.")
    return _freeze_json_value(
        {
            "schema_version": summary["schema_version"],
            "event_count": summary["event_count"],
            "events": [
                dict(_copy_allowed_fields(event, _EVENT_SUMMARY_FIELDS))
                for event in events
            ],
        }
    )


def build_replay_coaching_outcome_context(
    record: HistoricalGameRecord,
) -> ReplayCoachingOutcomeContext:
    """Builds the explicit privacy-safe final-context allowlist."""
    summary = build_historical_game_summary(record)
    terminal_field = REPLAY_COACHING_TERMINAL_SUMMARY_FIELD_BY_END_REASON.get(
        record.game_end_reason
    )
    terminal_summary = None
    if terminal_field is not None:
        raw_terminal = summary.get(terminal_field)
        if not isinstance(raw_terminal, Mapping):
            raise ValueError("Historical terminal summary is missing.")
        terminal_summary = _copy_allowed_fields(
            raw_terminal,
            _TERMINAL_SUMMARY_FIELDS[record.game_end_reason],
        )
    raw_events = summary.get("historical_game_events_summary")
    events_summary = (
        _build_safe_events_summary(raw_events)
        if isinstance(raw_events, Mapping)
        else None
    )
    return ReplayCoachingOutcomeContext(
        source_game_id=record.game_id,
        game_end_reason=record.game_end_reason,
        status=summary["status"],
        game_result_summary=_copy_allowed_fields(
            summary["game_result_summary"], _GAME_RESULT_SUMMARY_FIELDS
        ),
        game_value_summary=_copy_allowed_fields(
            summary["game_value_summary"], _GAME_VALUE_SUMMARY_FIELDS
        ),
        overbid_summary=_copy_allowed_fields(
            summary["overbid_summary"], _OVERBID_SUMMARY_FIELDS
        ),
        final_settlement_summary=_copy_allowed_fields(
            summary["final_settlement_summary"],
            _FINAL_SETTLEMENT_SUMMARY_FIELDS,
        ),
        historical_game_events_summary=events_summary,
        historical_game_end_summary=terminal_summary,
    )


def build_serializable_replay_coaching_player_context(
    context: ReplayCoachingPlayerContext,
) -> dict[str, Any]:
    return {
        "player_id": context.player_id,
        "player_label": context.player_label,
        "seat": context.seat,
        "side": context.side,
    }


def build_serializable_replay_coaching_game_context(
    context: ReplayCoachingGameContext,
) -> dict[str, Any]:
    return {
        "source_game_id": context.source_game_id,
        "played_at": context.played_at,
        "players": [
            build_serializable_replay_coaching_player_context(player)
            for player in context.players
        ],
        "declarer_player_id": context.declarer_player_id,
        "game_type": context.game_type,
        "declaration": _thaw_json_value(context.declaration),
        "game_end_reason": context.game_end_reason,
        "continuation_event_kinds": list(context.continuation_event_kinds),
        "recorded_play_count": context.recorded_play_count,
        "recorded_decision_count": context.recorded_decision_count,
    }


def build_serializable_replay_coaching_outcome_context(
    context: ReplayCoachingOutcomeContext,
) -> dict[str, Any]:
    result = {
        "source_game_id": context.source_game_id,
        "game_end_reason": context.game_end_reason,
        "status": context.status,
        "game_result_summary": _thaw_json_value(context.game_result_summary),
        "game_value_summary": _thaw_json_value(context.game_value_summary),
        "overbid_summary": _thaw_json_value(context.overbid_summary),
        "final_settlement_summary": _thaw_json_value(
            context.final_settlement_summary
        ),
    }
    if context.historical_game_events_summary is not None:
        result["historical_game_events_summary"] = _thaw_json_value(
            context.historical_game_events_summary
        )
    terminal_field = REPLAY_COACHING_TERMINAL_SUMMARY_FIELD_BY_END_REASON[
        context.game_end_reason
    ]
    if terminal_field is not None:
        result[terminal_field] = _thaw_json_value(
            context.historical_game_end_summary
        )
    return result
