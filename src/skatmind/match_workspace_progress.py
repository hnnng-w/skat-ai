from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skatmind.match_workspace_contracts import (
    MATCH_WORKSPACE_STATUSES,
    MatchWorkspaceV1,
    _require_match_position,
    _require_non_negative_integer,
    validate_match_workspace_v1,
)
from skatmind.observed_game_evidence import build_observed_game_evidence_summary_v1

MATCH_WORKSPACE_PROGRESS_VERSION = 1
MATCH_WORKSPACE_PROGRESS_POLICY = "derived_from_slot_occupancy_and_observed_evidence"


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspaceProgressV1:
    """Deterministic occupancy and evidence progress for one Workspace revision."""

    match_workspace_progress_version: int = MATCH_WORKSPACE_PROGRESS_VERSION
    status: str
    revision: int
    total_slot_count: int
    empty_slot_count: int
    observed_game_count: int
    passed_deal_count: int
    occupied_slot_count: int
    complete_play_trace_count: int
    perspective_sample_ready_game_count: int
    all_player_sample_ready_game_count: int
    discard_review_ready_game_count: int
    complete_initial_deal_ready_game_count: int
    commentary_count: int
    response_link_count: int
    next_empty_position: int | None

    def __post_init__(self) -> None:
        if (
            type(self.match_workspace_progress_version) is not int
            or self.match_workspace_progress_version != MATCH_WORKSPACE_PROGRESS_VERSION
        ):
            raise ValueError(
                "match_workspace_progress_version must equal "
                f"{MATCH_WORKSPACE_PROGRESS_VERSION}."
            )
        if self.status not in MATCH_WORKSPACE_STATUSES:
            raise ValueError(f"status must be one of {list(MATCH_WORKSPACE_STATUSES)}.")
        for field_name in (
            "revision",
            "total_slot_count",
            "empty_slot_count",
            "observed_game_count",
            "passed_deal_count",
            "occupied_slot_count",
            "complete_play_trace_count",
            "perspective_sample_ready_game_count",
            "all_player_sample_ready_game_count",
            "discard_review_ready_game_count",
            "complete_initial_deal_ready_game_count",
            "commentary_count",
            "response_link_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.total_slot_count != 36:
            raise ValueError("total_slot_count must equal 36.")
        if self.occupied_slot_count != self.observed_game_count + self.passed_deal_count:
            raise ValueError("occupied_slot_count must reconcile occupied Slot kinds.")
        if self.empty_slot_count + self.occupied_slot_count != self.total_slot_count:
            raise ValueError("Empty and occupied Slot counts must reconcile.")
        evidence_counts = (
            self.complete_play_trace_count,
            self.perspective_sample_ready_game_count,
            self.all_player_sample_ready_game_count,
            self.discard_review_ready_game_count,
            self.complete_initial_deal_ready_game_count,
        )
        if any(count > self.observed_game_count for count in evidence_counts):
            raise ValueError("Evidence-ready counts cannot exceed observed_game_count.")
        if self.all_player_sample_ready_game_count != self.complete_play_trace_count:
            raise ValueError(
                "all_player_sample_ready_game_count must equal complete_play_trace_count."
            )
        if self.complete_play_trace_count > self.perspective_sample_ready_game_count:
            raise ValueError(
                "Complete traces must be perspective-sample ready."
            )
        if self.complete_initial_deal_ready_game_count > self.complete_play_trace_count:
            raise ValueError(
                "Complete initial Deals require complete Play traces."
            )
        expected_status = (
            "empty"
            if self.occupied_slot_count == 0
            else "complete"
            if self.occupied_slot_count == self.total_slot_count
            else "in_progress"
        )
        if self.status != expected_status:
            raise ValueError("status must match Slot occupancy.")
        if self.empty_slot_count == 0:
            if self.next_empty_position is not None:
                raise ValueError("A complete Workspace has no next empty position.")
        else:
            _require_match_position(self.next_empty_position)
            if self.status == "empty" and self.next_empty_position != 1:
                raise ValueError("An empty Workspace has next_empty_position 1.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_progress_version": self.match_workspace_progress_version,
            "status": self.status,
            "revision": self.revision,
            "total_slot_count": self.total_slot_count,
            "empty_slot_count": self.empty_slot_count,
            "observed_game_count": self.observed_game_count,
            "passed_deal_count": self.passed_deal_count,
            "occupied_slot_count": self.occupied_slot_count,
            "complete_play_trace_count": self.complete_play_trace_count,
            "perspective_sample_ready_game_count": (
                self.perspective_sample_ready_game_count
            ),
            "all_player_sample_ready_game_count": (
                self.all_player_sample_ready_game_count
            ),
            "discard_review_ready_game_count": self.discard_review_ready_game_count,
            "complete_initial_deal_ready_game_count": (
                self.complete_initial_deal_ready_game_count
            ),
            "commentary_count": self.commentary_count,
            "response_link_count": self.response_link_count,
            "next_empty_position": self.next_empty_position,
        }


def build_match_workspace_progress_v1(
    workspace: MatchWorkspaceV1,
) -> MatchWorkspaceProgressV1:
    """Derives Workspace completion and observed-evidence counts without materialization."""
    validate_match_workspace_v1(workspace)
    return _build_validated_match_workspace_progress_v1(workspace)


def _build_validated_match_workspace_progress_v1(
    workspace: MatchWorkspaceV1,
) -> MatchWorkspaceProgressV1:
    """Derives Progress after the caller has validated the complete Workspace."""
    empty_count = 0
    observed_count = 0
    passed_count = 0
    complete_trace_count = 0
    perspective_ready_count = 0
    all_player_ready_count = 0
    discard_ready_count = 0
    initial_deal_ready_count = 0
    commentary_count = 0
    response_link_count = 0
    next_empty_position = None

    for slot in workspace.slots:
        if slot.slot_kind == "empty":
            empty_count += 1
            if next_empty_position is None:
                next_empty_position = slot.match_position
        elif slot.slot_kind == "passed_deal":
            passed_count += 1
        else:
            observed_count += 1
            assert slot.observed_game is not None
            evidence = build_observed_game_evidence_summary_v1(slot.observed_game)
            complete_trace_count += int(evidence.complete_play_trace)
            perspective_ready_count += int(
                evidence.perspective_decision_samples_reconstructable
            )
            all_player_ready_count += int(
                evidence.all_player_decision_samples_reconstructable
            )
            discard_ready_count += int(evidence.discard_review_reconstructable)
            initial_deal_ready_count += int(
                evidence.complete_initial_deal_reconstructable
            )
            commentary_count += evidence.commentary_count
            response_link_count += evidence.response_link_count

    occupied_count = observed_count + passed_count
    status = (
        "empty"
        if occupied_count == 0
        else "complete"
        if occupied_count == 36
        else "in_progress"
    )
    return MatchWorkspaceProgressV1(
        status=status,
        revision=workspace.revision,
        total_slot_count=36,
        empty_slot_count=empty_count,
        observed_game_count=observed_count,
        passed_deal_count=passed_count,
        occupied_slot_count=occupied_count,
        complete_play_trace_count=complete_trace_count,
        perspective_sample_ready_game_count=perspective_ready_count,
        all_player_sample_ready_game_count=all_player_ready_count,
        discard_review_ready_game_count=discard_ready_count,
        complete_initial_deal_ready_game_count=initial_deal_ready_count,
        commentary_count=commentary_count,
        response_link_count=response_link_count,
        next_empty_position=next_empty_position,
    )
