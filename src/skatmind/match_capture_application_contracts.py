from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from skatmind.deck import get_full_deck
from skatmind.match_source_metadata import MediaTimecodeV1
from skatmind.match_workspace_contracts import (
    MATCH_WORKSPACE_SLOT_KINDS,
    _require_match_position,
)
from skatmind.match_workspace_operations import MatchWorkspaceChangeResultV1
from skatmind.match_workspace_progress import MatchWorkspaceProgressV1
from skatmind.observed_game_evidence import ObservedGameEvidenceSummaryV1
from skatmind.observed_game_trace import copy_observed_timecode_v1
from skatmind.performance_rating import validate_stable_list_entry_identifier

MATCH_CAPTURE_APPLICATION_VERSION = 1
MATCH_CAPTURE_POSITION_VIEW_VERSION = 1
MATCH_CAPTURE_APPLICATION_RESULT_VERSION = 1

MATCH_CAPTURE_APPLICATION_OPERATIONS: Final[tuple[str, ...]] = (
    "start_game",
    "set_game_timecode",
    "set_perspective_hand",
    "set_declaration",
    "set_original_skat",
    "set_discarded_cards",
    "append_plays",
    "truncate_plays",
    "set_commentary",
    "remove_commentary",
    "set_response_link",
    "remove_response_link",
    "mark_passed_deal",
    "clear_position",
)
MATCH_CAPTURE_APPLICATION_STATUSES: Final[tuple[str, ...]] = (
    "applied",
    "unchanged",
    "revision_conflict",
)
MATCH_CAPTURE_GAME_STATES: Final[tuple[str, ...]] = (
    "empty",
    "setup",
    "ready_for_play",
    "play_in_progress",
    "play_complete",
    "passed_deal",
)
MATCH_CAPTURE_CARD_SELECTION_SCOPES: Final[tuple[str, ...]] = (
    "unavailable",
    "exact_legal_cards",
    "bounded_observation_candidates",
)
MATCH_CAPTURE_RECORD_PLAY_BLOCKERS: Final[tuple[str, ...]] = (
    "empty_slot",
    "passed_deal",
    "missing_declaration",
    "complete_play_trace",
)

MATCH_CAPTURE_APPLICATION_POLICY = "transport_free_workspace_observed_game_updates"
MATCH_CAPTURE_GAME_ID_POLICY = "match_id_plus_zero_padded_position"
MATCH_CAPTURE_ANNOTATION_ID_POLICY = "match_id_position_workspace_revision"
MATCH_CAPTURE_CARD_SELECTION_POLICY = "exclude_only_observed_or_proven_unavailable_cards"
MATCH_CAPTURE_TRUNCATION_POLICY = "remove_suffix_and_invalid_annotations"
MATCH_CAPTURE_INFORMATION_POLICY = "no_hidden_completion"

_ORDERED_DECK = tuple(get_full_deck())
_FULL_DECK = frozenset(_ORDERED_DECK)
_CARD_ORDER = {card: index for index, card in enumerate(_ORDERED_DECK)}
_GAME_WORKSPACE_OPERATIONS = frozenset(
    {
        "start_game",
        "set_game_timecode",
        "set_perspective_hand",
        "set_declaration",
        "set_original_skat",
        "set_discarded_cards",
        "append_plays",
        "truncate_plays",
        "set_commentary",
        "remove_commentary",
        "set_response_link",
        "remove_response_link",
    }
)


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_boolean(value: object, field_name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean.")


def _require_identifier_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for index, item in enumerate(value):
        validate_stable_list_entry_identifier(item, f"{field_name}[{index}]")
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must not contain duplicate IDs.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchCaptureCardEntryV1:
    """One caller-observed Card without Player or Decision metadata."""

    card: str
    decision_timecode: MediaTimecodeV1 | None

    def __post_init__(self) -> None:
        if not isinstance(self.card, str) or self.card not in _FULL_DECK:
            raise ValueError("card must be one valid Skat Card.")
        object.__setattr__(
            self,
            "decision_timecode",
            copy_observed_timecode_v1(self.decision_timecode, "decision_timecode"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "card": self.card,
            "decision_timecode": (
                None if self.decision_timecode is None else self.decision_timecode.to_dict()
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class MatchCapturePositionViewV1:
    """One immutable UI-ready view derived from an exact Workspace revision."""

    match_capture_position_view_version: int = MATCH_CAPTURE_POSITION_VIEW_VERSION
    match_id: str
    workspace_revision: int
    match_position: int
    round_number: int
    slot_kind: str
    game_state: str
    dealer_player_id: str
    forehand_player_id: str
    middlehand_player_id: str
    rearhand_player_id: str
    perspective_player_id: str
    game_id: str | None
    declarer_player_id: str | None
    play_count: int
    completed_trick_count: int
    current_trick_play_count: int
    current_trick_player_ids: tuple[str, ...]
    current_trick_cards: tuple[str, ...]
    next_player_id: str | None
    player_play_counts: tuple[tuple[str, int], ...]
    played_cards: tuple[str, ...]
    card_selection_scope: str
    selectable_cards: tuple[str, ...]
    can_record_play: bool
    record_play_blockers: tuple[str, ...]
    can_truncate_plays: bool
    evidence_summary: ObservedGameEvidenceSummaryV1 | None
    workspace_progress: MatchWorkspaceProgressV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("MatchCapturePositionViewV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        match_id: str,
        workspace_revision: int,
        match_position: int,
        round_number: int,
        slot_kind: str,
        game_state: str,
        dealer_player_id: str,
        forehand_player_id: str,
        middlehand_player_id: str,
        rearhand_player_id: str,
        perspective_player_id: str,
        game_id: str | None,
        declarer_player_id: str | None,
        play_count: int,
        completed_trick_count: int,
        current_trick_play_count: int,
        current_trick_player_ids: tuple[str, ...],
        current_trick_cards: tuple[str, ...],
        next_player_id: str | None,
        player_play_counts: tuple[tuple[str, int], ...],
        played_cards: tuple[str, ...],
        card_selection_scope: str,
        selectable_cards: tuple[str, ...],
        can_record_play: bool,
        record_play_blockers: tuple[str, ...],
        can_truncate_plays: bool,
        evidence_summary: ObservedGameEvidenceSummaryV1 | None,
        workspace_progress: MatchWorkspaceProgressV1,
    ) -> MatchCapturePositionViewV1:
        value = object.__new__(cls)
        fields = {
            "match_capture_position_view_version": MATCH_CAPTURE_POSITION_VIEW_VERSION,
            "match_id": match_id,
            "workspace_revision": workspace_revision,
            "match_position": match_position,
            "round_number": round_number,
            "slot_kind": slot_kind,
            "game_state": game_state,
            "dealer_player_id": dealer_player_id,
            "forehand_player_id": forehand_player_id,
            "middlehand_player_id": middlehand_player_id,
            "rearhand_player_id": rearhand_player_id,
            "perspective_player_id": perspective_player_id,
            "game_id": game_id,
            "declarer_player_id": declarer_player_id,
            "play_count": play_count,
            "completed_trick_count": completed_trick_count,
            "current_trick_play_count": current_trick_play_count,
            "current_trick_player_ids": current_trick_player_ids,
            "current_trick_cards": current_trick_cards,
            "next_player_id": next_player_id,
            "player_play_counts": player_play_counts,
            "played_cards": played_cards,
            "card_selection_scope": card_selection_scope,
            "selectable_cards": selectable_cards,
            "can_record_play": can_record_play,
            "record_play_blockers": record_play_blockers,
            "can_truncate_plays": can_truncate_plays,
            "evidence_summary": evidence_summary,
            "workspace_progress": workspace_progress,
        }
        for field_name, field_value in fields.items():
            object.__setattr__(value, field_name, field_value)
        value._validate_relationships()
        return value

    def _validate_relationships(self) -> None:
        _require_version(
            self.match_capture_position_view_version,
            MATCH_CAPTURE_POSITION_VIEW_VERSION,
            "match_capture_position_view_version",
        )
        validate_stable_list_entry_identifier(self.match_id, "match_id")
        if type(self.workspace_revision) is not int or self.workspace_revision < 0:
            raise ValueError("workspace_revision must be a non-negative integer.")
        _require_match_position(self.match_position)
        expected_round = ((self.match_position - 1) // 3) + 1
        if type(self.round_number) is not int or self.round_number != expected_round:
            raise ValueError("round_number must match match_position.")
        if self.slot_kind not in MATCH_WORKSPACE_SLOT_KINDS:
            raise ValueError(f"slot_kind must be one of {list(MATCH_WORKSPACE_SLOT_KINDS)}.")
        if self.game_state not in MATCH_CAPTURE_GAME_STATES:
            raise ValueError(f"game_state must be one of {list(MATCH_CAPTURE_GAME_STATES)}.")

        seat_player_ids = (
            self.forehand_player_id,
            self.middlehand_player_id,
            self.rearhand_player_id,
        )
        for field_name in (
            "dealer_player_id",
            "forehand_player_id",
            "middlehand_player_id",
            "rearhand_player_id",
            "perspective_player_id",
        ):
            validate_stable_list_entry_identifier(getattr(self, field_name), field_name)
        if len(set(seat_player_ids)) != 3 or self.dealer_player_id != self.rearhand_player_id:
            raise ValueError("Position View rotation must contain three seats and Rearhand Dealer.")
        if self.perspective_player_id not in seat_player_ids:
            raise ValueError("perspective_player_id must reference one rotated Match Player.")

        for field_name in (
            "play_count",
            "completed_trick_count",
            "current_trick_play_count",
        ):
            field_value = getattr(self, field_name)
            if type(field_value) is not int or field_value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.play_count > 30 or self.current_trick_play_count > 2:
            raise ValueError("Position View Play counts exceed one normal Game.")
        if self.completed_trick_count * 3 + self.current_trick_play_count != self.play_count:
            raise ValueError("Position View Trick counts must reconcile with play_count.")
        if (
            len(self.current_trick_player_ids) != self.current_trick_play_count
            or len(self.current_trick_cards) != self.current_trick_play_count
        ):
            raise ValueError("Current Trick arrays must match current_trick_play_count.")
        if any(
            player_id not in seat_player_ids for player_id in self.current_trick_player_ids
        ) or len(self.current_trick_player_ids) != len(set(self.current_trick_player_ids)):
            raise ValueError("Current Trick Players must be distinct rotated Game Players.")
        if len(self.played_cards) != self.play_count:
            raise ValueError("played_cards must match play_count.")
        played_current_trick = (
            tuple(self.played_cards[-self.current_trick_play_count :])
            if self.current_trick_play_count
            else ()
        )
        if played_current_trick != self.current_trick_cards:
            raise ValueError("current_trick_cards must be the chronological Play suffix.")
        if len(self.played_cards) != len(set(self.played_cards)) or any(
            card not in _FULL_DECK for card in self.played_cards
        ):
            raise ValueError("played_cards must contain unique valid Cards.")
        if any(card not in _FULL_DECK for card in self.selectable_cards) or len(
            self.selectable_cards
        ) != len(set(self.selectable_cards)):
            raise ValueError("selectable_cards must contain unique valid Cards.")
        if tuple(sorted(self.selectable_cards, key=_CARD_ORDER.__getitem__)) != (
            self.selectable_cards
        ):
            raise ValueError("selectable_cards must use canonical deck order.")

        if tuple(player_id for player_id, _count in self.player_play_counts) != (seat_player_ids):
            raise ValueError("player_play_counts must use Historical-seat order.")
        if any(
            type(count) is not int or not 0 <= count <= 10
            for _player_id, count in self.player_play_counts
        ):
            raise ValueError("Player Play counts must be integers from 0 through 10.")
        if sum(count for _player_id, count in self.player_play_counts) != self.play_count:
            raise ValueError("Player Play counts must sum to play_count.")

        if self.card_selection_scope not in MATCH_CAPTURE_CARD_SELECTION_SCOPES:
            raise ValueError(
                f"card_selection_scope must be one of {list(MATCH_CAPTURE_CARD_SELECTION_SCOPES)}."
            )
        _require_boolean(self.can_record_play, "can_record_play")
        _require_boolean(self.can_truncate_plays, "can_truncate_plays")
        if type(self.record_play_blockers) is not tuple or any(
            blocker not in MATCH_CAPTURE_RECORD_PLAY_BLOCKERS
            for blocker in self.record_play_blockers
        ):
            raise ValueError("record_play_blockers must contain canonical blockers.")
        expected_blocker_order = tuple(
            blocker
            for blocker in MATCH_CAPTURE_RECORD_PLAY_BLOCKERS
            if blocker in self.record_play_blockers
        )
        if self.record_play_blockers != expected_blocker_order:
            raise ValueError("record_play_blockers must use canonical order without duplicates.")
        if self.can_record_play != (not self.record_play_blockers):
            raise ValueError("can_record_play must be true exactly without blockers.")
        if self.can_truncate_plays != (self.play_count > 0):
            raise ValueError("can_truncate_plays must be true exactly when Plays exist.")
        if self.can_record_play != (self.next_player_id is not None):
            raise ValueError("next_player_id must be present exactly when another Play is allowed.")
        if self.next_player_id is not None and self.next_player_id not in seat_player_ids:
            raise ValueError("next_player_id must reference one rotated Game Player.")
        if self.card_selection_scope == "unavailable":
            if self.selectable_cards or self.can_record_play:
                raise ValueError("Unavailable Card selection cannot expose selectable Cards.")
        elif not self.can_record_play or not self.selectable_cards:
            raise ValueError("Available Card selection requires selectable Cards and next Player.")

        expected_state = (
            "empty"
            if self.slot_kind == "empty"
            else "passed_deal"
            if self.slot_kind == "passed_deal"
            else "setup"
            if self.declarer_player_id is None
            else "ready_for_play"
            if self.play_count == 0
            else "play_complete"
            if self.play_count == 30
            else "play_in_progress"
        )
        if self.game_state != expected_state:
            raise ValueError("game_state must match retained Slot and Game evidence.")
        if self.game_state == "setup" and self.play_count != 0:
            raise ValueError("A setup Game cannot contain Plays.")
        expected_blockers = (
            ("empty_slot",)
            if self.game_state == "empty"
            else ("passed_deal",)
            if self.game_state == "passed_deal"
            else ("missing_declaration",)
            if self.game_state == "setup"
            else ("complete_play_trace",)
            if self.game_state == "play_complete"
            else ()
        )
        if self.record_play_blockers != expected_blockers:
            raise ValueError("record_play_blockers must match game_state.")

        if self.slot_kind == "observed_game":
            if self.game_id is None or type(self.evidence_summary) is not (
                ObservedGameEvidenceSummaryV1
            ):
                raise ValueError("Observed-Game Views require Game ID and Evidence Summary.")
            validate_stable_list_entry_identifier(self.game_id, "game_id")
            if self.evidence_summary.play_count != self.play_count:
                raise ValueError("Evidence Summary must match Position View play_count.")
            if (
                self.evidence_summary.completed_trick_count != self.completed_trick_count
                or self.evidence_summary.current_trick_play_count != self.current_trick_play_count
                or self.evidence_summary.complete_play_trace != (self.play_count == 30)
            ):
                raise ValueError("Evidence Summary Trick facts must match the Position View.")
        elif any(
            value is not None
            for value in (self.game_id, self.declarer_player_id, self.evidence_summary)
        ):
            raise ValueError("Non-Game Views cannot contain Game evidence.")
        elif any(
            (
                self.play_count,
                self.completed_trick_count,
                self.current_trick_play_count,
                self.current_trick_player_ids,
                self.current_trick_cards,
                self.played_cards,
                any(count for _player_id, count in self.player_play_counts),
            )
        ):
            raise ValueError("Non-Game Views cannot contain Play or Trick evidence.")
        if self.declarer_player_id is not None:
            validate_stable_list_entry_identifier(
                self.declarer_player_id,
                "declarer_player_id",
            )
            if self.declarer_player_id not in seat_player_ids:
                raise ValueError("declarer_player_id must reference one Game Player.")
        if type(self.workspace_progress) is not MatchWorkspaceProgressV1:
            raise ValueError("workspace_progress must be MatchWorkspaceProgressV1.")
        if self.workspace_progress.revision != self.workspace_revision:
            raise ValueError("Workspace Progress revision must match the Position View.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_capture_position_view_version": (self.match_capture_position_view_version),
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "match_position": self.match_position,
            "round_number": self.round_number,
            "slot_kind": self.slot_kind,
            "game_state": self.game_state,
            "dealer_player_id": self.dealer_player_id,
            "forehand_player_id": self.forehand_player_id,
            "middlehand_player_id": self.middlehand_player_id,
            "rearhand_player_id": self.rearhand_player_id,
            "perspective_player_id": self.perspective_player_id,
            "game_id": self.game_id,
            "declarer_player_id": self.declarer_player_id,
            "play_count": self.play_count,
            "completed_trick_count": self.completed_trick_count,
            "current_trick_play_count": self.current_trick_play_count,
            "current_trick_player_ids": list(self.current_trick_player_ids),
            "current_trick_cards": list(self.current_trick_cards),
            "next_player_id": self.next_player_id,
            "player_play_counts": [
                {"player_id": player_id, "play_count": play_count}
                for player_id, play_count in self.player_play_counts
            ],
            "played_cards": list(self.played_cards),
            "card_selection_scope": self.card_selection_scope,
            "selectable_cards": list(self.selectable_cards),
            "can_record_play": self.can_record_play,
            "record_play_blockers": list(self.record_play_blockers),
            "can_truncate_plays": self.can_truncate_plays,
            "evidence_summary": (
                None if self.evidence_summary is None else self.evidence_summary.to_dict()
            ),
            "workspace_progress": self.workspace_progress.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchCaptureApplicationResultV1:
    """One immutable Capture operation result over one Workspace change."""

    match_capture_application_result_version: int = MATCH_CAPTURE_APPLICATION_RESULT_VERSION
    operation: str
    status: str
    workspace_change: MatchWorkspaceChangeResultV1
    position_view: MatchCapturePositionViewV1
    removed_commentary_ids: tuple[str, ...]
    removed_response_link_ids: tuple[str, ...]
    affected_commentary_id: str | None
    affected_response_link_id: str | None

    def __post_init__(self) -> None:
        self._validate_relationships(validate_exact_position_view=True)

    @classmethod
    def _from_validated(
        cls,
        *,
        operation: str,
        status: str,
        workspace_change: MatchWorkspaceChangeResultV1,
        position_view: MatchCapturePositionViewV1,
        removed_commentary_ids: tuple[str, ...],
        removed_response_link_ids: tuple[str, ...],
        affected_commentary_id: str | None,
        affected_response_link_id: str | None,
    ) -> MatchCaptureApplicationResultV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "match_capture_application_result_version",
                MATCH_CAPTURE_APPLICATION_RESULT_VERSION,
            ),
            ("operation", operation),
            ("status", status),
            ("workspace_change", workspace_change),
            ("position_view", position_view),
            ("removed_commentary_ids", removed_commentary_ids),
            ("removed_response_link_ids", removed_response_link_ids),
            ("affected_commentary_id", affected_commentary_id),
            ("affected_response_link_id", affected_response_link_id),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate_relationships(validate_exact_position_view=False)
        return value

    def _validate_relationships(self, *, validate_exact_position_view: bool) -> None:
        _require_version(
            self.match_capture_application_result_version,
            MATCH_CAPTURE_APPLICATION_RESULT_VERSION,
            "match_capture_application_result_version",
        )
        if self.operation not in MATCH_CAPTURE_APPLICATION_OPERATIONS:
            raise ValueError(
                f"operation must be one of {list(MATCH_CAPTURE_APPLICATION_OPERATIONS)}."
            )
        if self.status not in MATCH_CAPTURE_APPLICATION_STATUSES:
            raise ValueError(f"status must be one of {list(MATCH_CAPTURE_APPLICATION_STATUSES)}.")
        if type(self.workspace_change) is not MatchWorkspaceChangeResultV1:
            raise ValueError("workspace_change must be MatchWorkspaceChangeResultV1.")
        if type(self.position_view) is not MatchCapturePositionViewV1:
            raise ValueError("position_view must be MatchCapturePositionViewV1.")
        if self.status != self.workspace_change.status:
            raise ValueError("status must equal workspace_change.status.")
        expected_workspace_operation = (
            "set_observed_game"
            if self.operation in _GAME_WORKSPACE_OPERATIONS
            else "mark_passed_deal"
            if self.operation == "mark_passed_deal"
            else "clear_slot"
        )
        if self.workspace_change.operation != expected_workspace_operation:
            raise ValueError("workspace_change operation does not match Capture operation.")
        if (
            self.position_view.match_id != self.workspace_change.match_id
            or self.position_view.workspace_revision != self.workspace_change.current_revision
            or self.position_view.match_position != self.workspace_change.match_position
        ):
            raise ValueError("position_view must describe the returned Workspace and position.")
        if validate_exact_position_view:
            from skatmind.match_capture_position_view import (
                build_match_capture_position_view_v1,
            )

            expected_view = build_match_capture_position_view_v1(
                self.workspace_change.workspace,
                match_position=self.position_view.match_position,
            )
            if self.position_view != expected_view:
                raise ValueError("position_view must exactly describe the returned Workspace.")

        _require_identifier_tuple(
            self.removed_commentary_ids,
            "removed_commentary_ids",
        )
        _require_identifier_tuple(
            self.removed_response_link_ids,
            "removed_response_link_ids",
        )
        if self.affected_commentary_id is not None:
            validate_stable_list_entry_identifier(
                self.affected_commentary_id,
                "affected_commentary_id",
            )
            if self.operation != "set_commentary":
                raise ValueError("affected_commentary_id is available only for set_commentary.")
        if self.affected_response_link_id is not None:
            validate_stable_list_entry_identifier(
                self.affected_response_link_id,
                "affected_response_link_id",
            )
            if self.operation != "set_response_link":
                raise ValueError(
                    "affected_response_link_id is available only for set_response_link."
                )
        if self.removed_commentary_ids and self.operation not in {
            "truncate_plays",
            "remove_commentary",
        }:
            raise ValueError("This operation cannot report removed Commentary IDs.")
        if self.removed_response_link_ids and self.operation not in {
            "truncate_plays",
            "set_commentary",
            "remove_commentary",
            "remove_response_link",
        }:
            raise ValueError("This operation cannot report removed Response Link IDs.")
        if self.status == "revision_conflict" and any(
            (
                self.removed_commentary_ids,
                self.removed_response_link_ids,
                self.affected_commentary_id,
                self.affected_response_link_id,
            )
        ):
            raise ValueError("Revision conflicts cannot report annotation effects.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_capture_application_result_version": (
                self.match_capture_application_result_version
            ),
            "operation": self.operation,
            "status": self.status,
            "workspace_change": self.workspace_change.to_dict(),
            "position_view": self.position_view.to_dict(),
            "removed_commentary_ids": list(self.removed_commentary_ids),
            "removed_response_link_ids": list(self.removed_response_link_ids),
            "affected_commentary_id": self.affected_commentary_id,
            "affected_response_link_id": self.affected_response_link_id,
        }
