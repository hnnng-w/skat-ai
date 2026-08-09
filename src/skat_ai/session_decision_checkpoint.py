from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skat_ai.errors import SkatAIInvariantError
from skat_ai.historical_game import HISTORICAL_SEATS
from skat_ai.session_contracts import SESSION_CAPTURE_MODES, SessionStateV1
from skat_ai.session_export_contracts import SessionRequestExportV1
from skat_ai.session_position_export import (
    SessionPositionExportOptionsV1,
    _build_relative_player_map,
    _export_replayed_session_position_analysis_request_v1,
)
from skat_ai.session_projection import SessionProjectionV1
from skat_ai.session_transitions import replay_session_state_v1

SESSION_DECISION_CHECKPOINT_VERSION = 1
SESSION_DECISION_CHECKPOINT_POLICY = "frozen_pre_play_request"
SESSION_DECISION_INFORMATION_CUTOFF = "before_local_play"


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_player_identifier(value: object, field_name: str) -> str:
    player_id = _require_identifier(value, field_name)
    if player_id in {"me", "left", "right"}:
        raise ValueError(f"{field_name} must be a stable, non-relative Player ID.")
    return player_id


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_bounded_positive_integer(
    value: object,
    field_name: str,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise ValueError(f"{field_name} must be an integer from 1 through {maximum}.")
    return value


def _freeze_relative_player_map(value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"me", "left", "right"}:
        raise ValueError("relative_player_map must contain exactly me, left, and right.")
    relative_player_map = {
        relative_player: _require_player_identifier(
            value[relative_player],
            f"relative_player_map.{relative_player}",
        )
        for relative_player in ("me", "left", "right")
    }
    if len(set(relative_player_map.values())) != 3:
        raise ValueError("relative_player_map must identify exactly three Players.")
    return MappingProxyType(relative_player_map)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionDecisionCheckpointV1:
    """One immutable local pre-Play Position Request checkpoint."""

    session_decision_checkpoint_version: int = SESSION_DECISION_CHECKPOINT_VERSION
    session_id: str
    source_revision: int
    source_capture_mode: str
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: str
    information_cutoff: str
    relative_player_map: Mapping[str, str]
    request: RequestDocumentV1

    def __post_init__(self) -> None:
        if (
            type(self.session_decision_checkpoint_version) is not int
            or self.session_decision_checkpoint_version
            != SESSION_DECISION_CHECKPOINT_VERSION
        ):
            raise ValueError(
                "session_decision_checkpoint_version must equal "
                f"{SESSION_DECISION_CHECKPOINT_VERSION}."
            )
        _require_identifier(self.session_id, "session_id")
        _require_non_negative_integer(self.source_revision, "source_revision")
        if self.source_capture_mode not in SESSION_CAPTURE_MODES:
            raise ValueError(
                f"source_capture_mode must be one of {list(SESSION_CAPTURE_MODES)}."
            )
        _require_bounded_positive_integer(self.decision_index, "decision_index", 30)
        _require_bounded_positive_integer(self.trick_number, "trick_number", 10)
        _require_bounded_positive_integer(self.play_index, "play_index", 3)
        if self.decision_index != (self.trick_number - 1) * 3 + self.play_index:
            raise ValueError(
                "decision_index must reconcile with trick_number and play_index."
            )
        _require_player_identifier(self.acting_player_id, "acting_player_id")
        if self.acting_seat not in HISTORICAL_SEATS:
            raise ValueError(f"acting_seat must be one of {list(HISTORICAL_SEATS)}.")
        if self.information_cutoff != SESSION_DECISION_INFORMATION_CUTOFF:
            raise ValueError(
                "information_cutoff must equal "
                f"{SESSION_DECISION_INFORMATION_CUTOFF!r}."
            )
        relative_player_map = _freeze_relative_player_map(self.relative_player_map)
        if relative_player_map["me"] != self.acting_player_id:
            raise ValueError("relative_player_map.me must equal acting_player_id.")
        if not isinstance(self.request, RequestDocumentV1):
            raise ValueError("request must be a RequestDocumentV1.")
        if self.request.workflow is not WorkflowV1.POSITION_ANALYSIS:
            raise ValueError("request must target Position Analysis.")
        SessionRequestExportV1(
            session_id=self.session_id,
            source_revision=self.source_revision,
            target="position_analysis",
            status="available",
            request=self.request,
            diagnostics=(),
        )
        if (
            self.request.document.get("next_player") != "me"
            or self.request.document.get("player_position") != self.acting_seat
            or self.request.document.get("analysis_mode") != "live_decision"
            or self.request.document.get("game_end_reason") != "not_ended"
        ):
            raise ValueError("request must describe the matching local pre-Play decision.")
        completed_tricks = self.request.document.get("completed_tricks")
        current_trick = self.request.document.get("current_trick")
        if not isinstance(completed_tricks, tuple) or not isinstance(
            current_trick, tuple
        ):
            raise ValueError("request must contain completed and current Trick arrays.")
        if (
            self.trick_number != len(completed_tricks) + 1
            or self.play_index != len(current_trick) + 1
            or self.decision_index
            != len(completed_tricks) * 3 + len(current_trick) + 1
        ):
            raise ValueError("decision indexes must match the frozen Position Request.")
        object.__setattr__(self, "relative_player_map", relative_player_map)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_decision_checkpoint_version": (
                self.session_decision_checkpoint_version
            ),
            "session_id": self.session_id,
            "source_revision": self.source_revision,
            "source_capture_mode": self.source_capture_mode,
            "decision_index": self.decision_index,
            "trick_number": self.trick_number,
            "play_index": self.play_index,
            "acting_player_id": self.acting_player_id,
            "acting_seat": self.acting_seat,
            "information_cutoff": self.information_cutoff,
            "relative_player_map": {
                relative_player: self.relative_player_map[relative_player]
                for relative_player in ("me", "left", "right")
            },
            "request": self.request.to_dict(),
        }


def _raise_checkpoint_invariant(
    message: str,
    *,
    path: str,
    cause: Exception | None = None,
) -> None:
    error = SkatAIInvariantError(message, path=path)
    if cause is None:
        raise error
    raise error from cause


def _options_from_request(request: RequestDocumentV1) -> SessionPositionExportOptionsV1:
    root = request.to_dict()["document"]
    return SessionPositionExportOptionsV1(
        sample_count=root["sample_count"],
        random_seed=root["random_seed"],
        use_basic_opponent_strategy=root["use_basic_opponent_strategy"],
        recommendation_method=root.get("recommendation_method"),
        bounded_search_settings=root.get("bounded_search_settings"),
    )


def _build_replayed_session_decision_checkpoint_v1(
    *,
    state: SessionStateV1,
    projection: SessionProjectionV1,
    position_export: SessionRequestExportV1,
) -> SessionDecisionCheckpointV1:
    """Builds a Checkpoint from an already replay-verified Position export."""
    if (
        projection.local_player_id is None
        or projection.next_player_id != projection.local_player_id
    ):
        _raise_checkpoint_invariant(
            "The local Player is not next in the replayed Session.",
            path="/next_player_id",
        )
    if (
        position_export.session_id != state.session_id
        or position_export.source_revision != state.revision
        or position_export.target != "position_analysis"
        or position_export.status != "available"
        or position_export.request is None
    ):
        _raise_checkpoint_invariant(
            "The replayed Position export cannot form a Decision Checkpoint.",
            path="/request",
        )

    relative_player_map = _build_relative_player_map(projection)
    local_player_id = relative_player_map["me"]
    local_player = next(
        player for player in projection.players if player.player_id == local_player_id
    )
    play_index = (
        1
        if projection.incomplete_trick is None
        else len(projection.incomplete_trick.plays) + 1
    )
    return SessionDecisionCheckpointV1(
        session_id=state.session_id,
        source_revision=state.revision,
        source_capture_mode=projection.capture_mode,
        decision_index=projection.played_card_count + 1,
        trick_number=len(projection.completed_tricks) + 1,
        play_index=play_index,
        acting_player_id=local_player_id,
        acting_seat=local_player.seat,
        information_cutoff=SESSION_DECISION_INFORMATION_CUTOFF,
        relative_player_map=relative_player_map,
        request=position_export.request,
    )


def build_session_decision_checkpoint_v1(
    *,
    state: SessionStateV1,
    position_export: SessionRequestExportV1,
) -> SessionDecisionCheckpointV1:
    """Freezes one replay-verified Position export before the local Play."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    if type(position_export) is not SessionRequestExportV1:
        raise ValueError("position_export must be a SessionRequestExportV1.")
    if (
        position_export.target != "position_analysis"
        or position_export.status != "available"
        or position_export.request is None
    ):
        raise ValueError("position_export must be an available Position export.")
    if position_export.session_id != state.session_id:
        _raise_checkpoint_invariant(
            "Position export Session ID does not match the Session State.",
            path="/session_id",
        )
    if position_export.source_revision != state.revision:
        _raise_checkpoint_invariant(
            "Position export revision does not match the Session State.",
            path="/source_revision",
        )

    try:
        options = _options_from_request(position_export.request)
    except Exception as error:
        _raise_checkpoint_invariant(
            "Position export does not contain valid Session export options.",
            path="/request/document",
            cause=error,
        )
    projection = replay_session_state_v1(state)
    expected_export = _export_replayed_session_position_analysis_request_v1(
        state=state,
        projection=projection,
        options=options,
    )
    if expected_export != position_export:
        _raise_checkpoint_invariant(
            "Position export does not equal the expected Session Request.",
            path="/request",
        )
    if expected_export.request is None:
        _raise_checkpoint_invariant(
            "Expected Session Position export has no Request.",
            path="/request",
        )
    return _build_replayed_session_decision_checkpoint_v1(
        state=state,
        projection=projection,
        position_export=expected_export,
    )
