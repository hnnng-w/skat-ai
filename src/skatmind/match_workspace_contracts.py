from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from skatmind.match_capture_contracts import MatchCaptureDefinitionV1
from skatmind.match_player_snapshot import MatchParticipantV1
from skatmind.match_source_metadata import MatchSourceMetadataV1, MediaTimecodeV1
from skatmind.observed_game_contracts import (
    ObservedGameRecordV1,
    _build_observed_game_record_v1,
)
from skatmind.observed_game_trace import (
    ObservedGameTraceSummaryV1,
    copy_observed_timecode_v1,
    validate_observed_timecode_containment_v1,
)

MATCH_WORKSPACE_CONTRACT_VERSION = 1
MATCH_WORKSPACE_SLOT_VERSION = 1
MATCH_PASSED_DEAL_VERSION = 1

MATCH_WORKSPACE_SLOT_KINDS: Final[tuple[str, ...]] = (
    "empty",
    "observed_game",
    "passed_deal",
)
MATCH_WORKSPACE_STATUSES: Final[tuple[str, ...]] = (
    "empty",
    "in_progress",
    "complete",
)

MATCH_WORKSPACE_SLOT_POLICY = "fixed_authoritative_36_position_array"

_EUROSKAT_36_STANDARD_FORMAT_ID = "euroskat_36_standard_v1"
_MATCH_POSITION_COUNT = 36


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_match_position(value: object) -> int:
    if type(value) is not int or not 1 <= value <= _MATCH_POSITION_COUNT:
        raise ValueError("match_position must be an integer from 1 through 36.")
    return value


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _copy_match_definition_v1(
    value: MatchCaptureDefinitionV1,
) -> MatchCaptureDefinitionV1:
    if type(value) is not MatchCaptureDefinitionV1:
        raise ValueError("match_definition must be a MatchCaptureDefinitionV1.")
    copied = MatchCaptureDefinitionV1(
        match_capture_contract_version=value.match_capture_contract_version,
        match_id=value.match_id,
        title=value.title,
        game_platform=value.game_platform,
        external_match_id=value.external_match_id,
        played_at=value.played_at,
        tournament_format=value.tournament_format,
        source=MatchSourceMetadataV1(
            match_source_metadata_version=value.source.match_source_metadata_version,
            source_kind=value.source.source_kind,
            source_url=value.source.source_url,
            source_title=value.source.source_title,
            source_channel_name=value.source.source_channel_name,
            match_timecode=value.source.match_timecode,
        ),
        participants=tuple(
            MatchParticipantV1(
                player_id=participant.player_id,
                player_label=participant.player_label,
                platform_player_id=participant.platform_player_id,
                table_place=participant.table_place,
                statistics_snapshot=participant.statistics_snapshot,
            )
            for participant in value.participants
        ),
        perspective_player_id=value.perspective_player_id,
    )
    if copied.to_dict() != value.to_dict():
        raise ValueError("match_definition must be in canonical form.")
    return copied


def _copy_observed_game_record_v1(
    value: ObservedGameRecordV1,
    *,
    match_definition: MatchCaptureDefinitionV1,
    validated_trace_output: list[ObservedGameTraceSummaryV1] | None = None,
) -> ObservedGameRecordV1:
    if type(value) is not ObservedGameRecordV1:
        raise ValueError("observed_game must be an ObservedGameRecordV1.")
    copied = _build_observed_game_record_v1(
        match_definition,
        game_id=value.game_id,
        match_position=value.match_position,
        game_timecode=value.game_timecode,
        seat_order_player_ids=tuple(player.player_id for player in value.players),
        perspective_initial_hand=value.perspective_initial_hand,
        declarer_player_id=value.declarer_player_id,
        declaration=value.declaration,
        original_skat=value.original_skat,
        discarded_cards=value.discarded_cards,
        plays=value.plays,
        commentaries=value.commentaries,
        response_links=value.response_links,
        _validated_trace_output=validated_trace_output,
    )
    if copied.to_dict() != value.to_dict():
        raise ValueError("observed_game must be in canonical form.")
    return copied


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchPassedDealV1:
    """One explicit passed Match position without a synthetic Game identity."""

    match_passed_deal_version: int = MATCH_PASSED_DEAL_VERSION
    game_timecode: MediaTimecodeV1 | None

    def __post_init__(self) -> None:
        _require_version(
            self.match_passed_deal_version,
            MATCH_PASSED_DEAL_VERSION,
            "match_passed_deal_version",
        )
        object.__setattr__(
            self,
            "game_timecode",
            copy_observed_timecode_v1(self.game_timecode, "game_timecode"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_passed_deal_version": self.match_passed_deal_version,
            "game_timecode": (None if self.game_timecode is None else self.game_timecode.to_dict()),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class MatchWorkspaceSlotV1:
    """One authoritative empty, observed-Game, or passed Match position."""

    match_workspace_slot_version: int = MATCH_WORKSPACE_SLOT_VERSION
    match_position: int
    slot_kind: str
    observed_game: ObservedGameRecordV1 | None
    passed_deal: MatchPassedDealV1 | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("MatchWorkspaceSlotV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        match_position: int,
        slot_kind: str,
        observed_game: ObservedGameRecordV1 | None,
        passed_deal: MatchPassedDealV1 | None,
    ) -> MatchWorkspaceSlotV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "match_workspace_slot_version",
            MATCH_WORKSPACE_SLOT_VERSION,
        )
        object.__setattr__(value, "match_position", match_position)
        object.__setattr__(value, "slot_kind", slot_kind)
        object.__setattr__(value, "observed_game", observed_game)
        object.__setattr__(value, "passed_deal", passed_deal)
        value._validate_relationships()
        return value

    def _validate_relationships(self) -> None:
        _require_version(
            self.match_workspace_slot_version,
            MATCH_WORKSPACE_SLOT_VERSION,
            "match_workspace_slot_version",
        )
        _require_match_position(self.match_position)
        if self.slot_kind not in MATCH_WORKSPACE_SLOT_KINDS:
            raise ValueError(f"slot_kind must be one of {list(MATCH_WORKSPACE_SLOT_KINDS)}.")
        if self.slot_kind == "empty":
            valid = self.observed_game is None and self.passed_deal is None
        elif self.slot_kind == "observed_game":
            valid = type(self.observed_game) is ObservedGameRecordV1 and self.passed_deal is None
        else:
            valid = self.observed_game is None and type(self.passed_deal) is MatchPassedDealV1
        if not valid:
            raise ValueError("slot_kind and Slot payloads are inconsistent.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_slot_version": self.match_workspace_slot_version,
            "match_position": self.match_position,
            "slot_kind": self.slot_kind,
            "observed_game": (None if self.observed_game is None else self.observed_game.to_dict()),
            "passed_deal": (None if self.passed_deal is None else self.passed_deal.to_dict()),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class MatchWorkspaceV1:
    """One immutable authoritative 36-position EuroSkat Match Workspace."""

    match_workspace_contract_version: int = MATCH_WORKSPACE_CONTRACT_VERSION
    revision: int
    match_definition: MatchCaptureDefinitionV1
    slots: tuple[MatchWorkspaceSlotV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("MatchWorkspaceV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        revision: int,
        match_definition: MatchCaptureDefinitionV1,
        slots: tuple[MatchWorkspaceSlotV1, ...],
    ) -> MatchWorkspaceV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "match_workspace_contract_version",
            MATCH_WORKSPACE_CONTRACT_VERSION,
        )
        object.__setattr__(value, "revision", revision)
        object.__setattr__(value, "match_definition", match_definition)
        object.__setattr__(value, "slots", slots)
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_contract_version": self.match_workspace_contract_version,
            "revision": self.revision,
            "match_definition": self.match_definition.to_dict(),
            "slots": [slot.to_dict() for slot in self.slots],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspacePositionFactV1:
    """Derived rotation and retained-evidence facts for one Workspace position."""

    match_position: int
    round_number: int
    slot_kind: str
    dealer_player_id: str
    forehand_player_id: str
    middlehand_player_id: str
    rearhand_player_id: str
    game_id: str | None
    play_count: int
    complete_play_trace: bool

    def __post_init__(self) -> None:
        _require_match_position(self.match_position)
        expected_round = ((self.match_position - 1) // 3) + 1
        if type(self.round_number) is not int or self.round_number != expected_round:
            raise ValueError("round_number must match the canonical Match position.")
        if self.slot_kind not in MATCH_WORKSPACE_SLOT_KINDS:
            raise ValueError(f"slot_kind must be one of {list(MATCH_WORKSPACE_SLOT_KINDS)}.")
        player_ids = (
            self.dealer_player_id,
            self.forehand_player_id,
            self.middlehand_player_id,
            self.rearhand_player_id,
        )
        if any(
            not isinstance(player_id, str) or not player_id or player_id != player_id.strip()
            for player_id in player_ids
        ):
            raise ValueError("Position Fact Player IDs must be non-empty strings.")
        if self.dealer_player_id != self.rearhand_player_id:
            raise ValueError("The Dealer must equal Rearhand.")
        if (
            len(
                {
                    self.forehand_player_id,
                    self.middlehand_player_id,
                    self.rearhand_player_id,
                }
            )
            != 3
        ):
            raise ValueError("Historical seats must contain three distinct Players.")
        _require_non_negative_integer(self.play_count, "play_count")
        if self.play_count > 30:
            raise ValueError("play_count must not exceed 30.")
        if type(self.complete_play_trace) is not bool:
            raise ValueError("complete_play_trace must be a boolean.")
        if self.slot_kind == "observed_game":
            if (
                not isinstance(self.game_id, str)
                or not self.game_id
                or self.game_id != self.game_id.strip()
            ):
                raise ValueError("Observed-Game Position Facts require game_id.")
        elif self.game_id is not None or self.play_count != 0 or self.complete_play_trace:
            raise ValueError("Non-Game Position Facts cannot contain Game evidence.")
        if self.complete_play_trace != (self.play_count == 30):
            raise ValueError("complete_play_trace must be true exactly when play_count is 30.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_position": self.match_position,
            "round_number": self.round_number,
            "slot_kind": self.slot_kind,
            "dealer_player_id": self.dealer_player_id,
            "forehand_player_id": self.forehand_player_id,
            "middlehand_player_id": self.middlehand_player_id,
            "rearhand_player_id": self.rearhand_player_id,
            "game_id": self.game_id,
            "play_count": self.play_count,
            "complete_play_trace": self.complete_play_trace,
        }


def _build_match_workspace_slot_v1(
    *,
    match_position: int,
    slot_kind: str,
    observed_game: ObservedGameRecordV1 | None,
    passed_deal: MatchPassedDealV1 | None,
    match_definition: MatchCaptureDefinitionV1,
) -> MatchWorkspaceSlotV1:
    _require_match_position(match_position)
    if slot_kind not in MATCH_WORKSPACE_SLOT_KINDS:
        raise ValueError(f"slot_kind must be one of {list(MATCH_WORKSPACE_SLOT_KINDS)}.")
    copied_game = None
    copied_passed_deal = None
    if slot_kind == "observed_game":
        if passed_deal is not None:
            raise ValueError("An observed_game Slot cannot contain passed_deal.")
        copied_game = _copy_observed_game_record_v1(
            observed_game,
            match_definition=match_definition,
        )
    elif slot_kind == "passed_deal":
        if observed_game is not None or type(passed_deal) is not MatchPassedDealV1:
            raise ValueError("A passed_deal Slot requires only MatchPassedDealV1.")
        copied_passed_deal = MatchPassedDealV1(
            match_passed_deal_version=passed_deal.match_passed_deal_version,
            game_timecode=passed_deal.game_timecode,
        )
    elif observed_game is not None or passed_deal is not None:
        raise ValueError("An empty Slot cannot contain a payload.")
    return MatchWorkspaceSlotV1._from_validated(
        match_position=match_position,
        slot_kind=slot_kind,
        observed_game=copied_game,
        passed_deal=copied_passed_deal,
    )


def _build_match_workspace_v1(
    *,
    revision: int,
    match_definition: MatchCaptureDefinitionV1,
    slots: tuple[MatchWorkspaceSlotV1, ...] | list[MatchWorkspaceSlotV1],
    validated_traces: list[tuple[int, ObservedGameTraceSummaryV1]] | None = None,
) -> MatchWorkspaceV1:
    _require_non_negative_integer(revision, "revision")
    copied_definition = _copy_match_definition_v1(match_definition)
    tournament_format = copied_definition.tournament_format
    if (
        tournament_format.format_id != _EUROSKAT_36_STANDARD_FORMAT_ID
        or tournament_format.game_count != _MATCH_POSITION_COUNT
    ):
        raise ValueError("Match Workspaces require exact canonical euroskat_36_standard_v1.")
    if isinstance(slots, (str, bytes)) or not isinstance(slots, (list, tuple)):
        raise ValueError("slots must be an ordered array.")
    if len(slots) != _MATCH_POSITION_COUNT:
        raise ValueError("slots must contain exactly 36 authoritative positions.")

    copied_slots: list[MatchWorkspaceSlotV1] = []
    game_ids: set[str] = set()
    occupied_slot_count = 0
    previous_present_start: int | None = None
    from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1

    for expected_position, source_slot in enumerate(slots, start=1):
        if type(source_slot) is not MatchWorkspaceSlotV1:
            raise ValueError("slots must contain only MatchWorkspaceSlotV1 values.")
        source_slot._validate_relationships()
        if source_slot.match_position != expected_position:
            raise ValueError("Slot positions must be exactly 1 through 36 in order.")
        trace_output: list[ObservedGameTraceSummaryV1] = []
        if source_slot.slot_kind == "observed_game":
            copied_game = _copy_observed_game_record_v1(
                source_slot.observed_game,
                match_definition=copied_definition,
                validated_trace_output=trace_output,
            )
            copied_slot = MatchWorkspaceSlotV1._from_validated(
                match_position=source_slot.match_position,
                slot_kind=source_slot.slot_kind,
                observed_game=copied_game,
                passed_deal=None,
            )
        else:
            copied_slot = _build_match_workspace_slot_v1(
                match_position=source_slot.match_position,
                slot_kind=source_slot.slot_kind,
                observed_game=source_slot.observed_game,
                passed_deal=source_slot.passed_deal,
                match_definition=copied_definition,
            )
        copied_slots.append(copied_slot)
        if trace_output:
            if len(trace_output) != 1:
                raise ValueError("Observed Game validation must produce exactly one trace.")
            if validated_traces is not None:
                validated_traces.append((expected_position, trace_output[0]))
        assignment = build_match_workspace_seat_assignment_v1(
            copied_definition,
            expected_position,
        )

        timecode = None
        if copied_slot.observed_game is not None:
            occupied_slot_count += 1
            game = copied_slot.observed_game
            if game.match_id != copied_definition.match_id:
                raise ValueError("Observed Game Match ID must equal the Workspace Match ID.")
            if game.match_position != expected_position:
                raise ValueError("Observed Game position must equal its Workspace Slot.")
            if game.perspective_player_id != copied_definition.perspective_player_id:
                raise ValueError("Observed Game perspective must equal the Match perspective.")
            expected_seat_order = (
                assignment.forehand_player_id,
                assignment.middlehand_player_id,
                assignment.rearhand_player_id,
            )
            actual_seat_order = tuple(player.player_id for player in game.players)
            if actual_seat_order != expected_seat_order:
                raise ValueError(
                    "Observed Game Players must match the canonical historical-seat rotation."
                )
            if game.game_id in game_ids:
                raise ValueError("Observed Game IDs must be unique within one Workspace.")
            game_ids.add(game.game_id)
            timecode = game.game_timecode
        elif copied_slot.passed_deal is not None:
            occupied_slot_count += 1
            timecode = copied_slot.passed_deal.game_timecode
            validate_observed_timecode_containment_v1(
                timecode,
                copied_definition.source.match_timecode,
                child_name=f"slots[{expected_position - 1}].passed_deal.game_timecode",
                parent_name="Match source match_timecode",
            )
        if timecode is not None:
            if (
                previous_present_start is not None
                and timecode.start_offset_ms < previous_present_start
            ):
                raise ValueError(
                    "Present Workspace Slot timecodes must be non-decreasing by position."
                )
            previous_present_start = timecode.start_offset_ms

    if revision < occupied_slot_count:
        raise ValueError("revision must be at least the number of currently occupied Slots.")

    return MatchWorkspaceV1._from_validated(
        revision=revision,
        match_definition=copied_definition,
        slots=tuple(copied_slots),
    )


def validate_match_workspace_v1(workspace: MatchWorkspaceV1) -> None:
    """Validates the complete canonical Workspace and all retained nested facts."""
    _validate_match_workspace_with_traces_v1(workspace)


def _validate_match_workspace_with_traces_v1(
    workspace: MatchWorkspaceV1,
) -> tuple[tuple[int, ObservedGameTraceSummaryV1], ...]:
    """Validates one Workspace and returns its already-validated observed traces."""
    if type(workspace) is not MatchWorkspaceV1:
        raise ValueError("workspace must be a MatchWorkspaceV1.")
    _require_version(
        workspace.match_workspace_contract_version,
        MATCH_WORKSPACE_CONTRACT_VERSION,
        "match_workspace_contract_version",
    )
    validated_traces: list[tuple[int, ObservedGameTraceSummaryV1]] = []
    rebuilt = _build_match_workspace_v1(
        revision=workspace.revision,
        match_definition=workspace.match_definition,
        slots=workspace.slots,
        validated_traces=validated_traces,
    )
    if rebuilt.to_dict() != workspace.to_dict():
        raise ValueError("workspace must be in canonical form.")
    return tuple(validated_traces)


def create_match_workspace_v1(
    match_definition: MatchCaptureDefinitionV1,
) -> MatchWorkspaceV1:
    """Creates revision zero with exactly 36 canonical empty Slots."""
    empty_slots = tuple(
        MatchWorkspaceSlotV1._from_validated(
            match_position=position,
            slot_kind="empty",
            observed_game=None,
            passed_deal=None,
        )
        for position in range(1, _MATCH_POSITION_COUNT + 1)
    )
    return _build_match_workspace_v1(
        revision=0,
        match_definition=match_definition,
        slots=empty_slots,
    )
