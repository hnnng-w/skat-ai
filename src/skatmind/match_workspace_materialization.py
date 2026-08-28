from dataclasses import dataclass
from typing import Any, Final

from skatmind.errors import SkatMindInvariantError
from skatmind.fixed_three_player_historical_list import (
    FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION,
    FixedThreePlayerHistoricalList,
    FixedThreePlayerHistoricalListEntryFact,
    _build_fixed_three_player_historical_list,
    build_serializable_fixed_three_player_historical_list,
)
from skatmind.fixed_three_player_historical_list_aggregation import (
    FixedThreePlayerHistoricalListAggregation,
    _build_fixed_three_player_historical_list_aggregation,
    build_serializable_fixed_three_player_historical_list_aggregation,
)
from skatmind.match_decision_review_preparation import (
    MatchDecisionReviewPreparationV1,
    _build_match_decision_review_preparation_from_reconstruction_v1,
)
from skatmind.match_historical_materialization import (
    MatchHistoricalGameMaterializationV1,
    _materialize_match_observed_game_historical_from_reconstruction_v1,
    _unavailable,
)
from skatmind.match_observed_reconstruction import (
    build_match_observed_game_reconstruction_v1,
)
from skatmind.match_player_statistics_preparation import (
    MatchPlayerStatisticsPreparationV1,
    build_match_player_statistics_preparation_v1,
)
from skatmind.match_training_source_materialization import (
    MatchTrainingSourceCollectionV1,
    MatchTrainingSourceRecordMaterializationV1,
    build_match_training_source_collection_v1,
    materialize_match_training_source_record_v1,
)
from skatmind.match_workspace_contracts import (
    MatchWorkspaceV1,
    _validate_match_workspace_with_traces_v1,
)
from skatmind.observed_game_evidence import ObservedGameEvidenceSummaryV1
from skatmind.observed_game_trace import ObservedGameTraceSummaryV1
from skatmind.rfc3339 import parse_rfc3339_datetime

MATCH_WORKSPACE_MATERIALIZATION_VERSION = 1

MATCH_WORKSPACE_MATERIALIZATION_STATUSES: Final[tuple[str, ...]] = (
    "empty",
    "partial",
    "complete",
)
MATCH_LIST_MATERIALIZATION_UNAVAILABLE_REASONS: Final[tuple[str, ...]] = (
    "workspace_not_structurally_complete",
    "observed_game_not_historical_materializable",
)

MATCH_LIST_MATERIALIZATION_POLICY = "existing_fixed_three_player_36_position_contract"
MATCH_COMMENTARY_MATERIALIZATION_POLICY = "remain_workspace_sidecar_without_analysis_influence"


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspaceSlotMaterializationV1:
    """Downstream preparation for one authoritative Match position."""

    match_position: int
    slot_kind: str
    game_id: str | None
    evidence_summary: ObservedGameEvidenceSummaryV1 | None
    decision_review_preparation: MatchDecisionReviewPreparationV1 | None
    historical_materialization: MatchHistoricalGameMaterializationV1
    training_source_materialization: MatchTrainingSourceRecordMaterializationV1
    commentary_count: int
    response_link_count: int

    def __post_init__(self) -> None:
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        if self.slot_kind not in {"empty", "observed_game", "passed_deal"}:
            raise ValueError("slot_kind must be empty, observed_game, or passed_deal.")
        for field_name in ("commentary_count", "response_link_count"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.slot_kind == "observed_game":
            if (
                self.game_id is None
                or self.evidence_summary is None
                or self.decision_review_preparation is None
            ):
                raise ValueError("An observed_game Slot requires evidence and Decision values.")
            if (
                self.decision_review_preparation.match_position != self.match_position
                or self.decision_review_preparation.game_id != self.game_id
                or self.historical_materialization.game_id != self.game_id
            ):
                raise ValueError("Observed-Game nested values must retain Slot identity.")
        elif any(
            value is not None
            for value in (
                self.game_id,
                self.evidence_summary,
                self.decision_review_preparation,
            )
        ):
            raise ValueError("A non-Game Slot cannot contain Game preparation values.")
        if self.slot_kind != "observed_game" and (
            self.historical_materialization.status != "unavailable"
            or self.historical_materialization.unavailable_reason
            != ("slot_empty" if self.slot_kind == "empty" else "passed_deal")
        ):
            raise ValueError("Empty and passed Slots require their matching unavailable reason.")
        if (
            self.historical_materialization.match_position != self.match_position
            or self.training_source_materialization.match_position != self.match_position
            or self.training_source_materialization.status != self.historical_materialization.status
            or self.training_source_materialization.unavailable_reason
            != self.historical_materialization.unavailable_reason
        ):
            raise ValueError("Historical and Training values must reconcile with the Slot.")
        if self.slot_kind != "observed_game" and (
            self.commentary_count or self.response_link_count
        ):
            raise ValueError("A non-Game Slot cannot contain annotation counts.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_position": self.match_position,
            "slot_kind": self.slot_kind,
            "game_id": self.game_id,
            "evidence_summary": (
                None if self.evidence_summary is None else self.evidence_summary.to_dict()
            ),
            "decision_review_preparation": (
                None
                if self.decision_review_preparation is None
                else self.decision_review_preparation.to_dict()
            ),
            "historical_materialization": self.historical_materialization.to_dict(),
            "training_source_materialization": (self.training_source_materialization.to_dict()),
            "commentary_count": self.commentary_count,
            "response_link_count": self.response_link_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchHistoricalListMaterializationV1:
    """One complete existing 36-position list and aggregation, or why absent."""

    status: str
    unavailable_reason: str | None
    unavailable_positions: tuple[int, ...]
    historical_list: FixedThreePlayerHistoricalList | None
    aggregation: FixedThreePlayerHistoricalListAggregation | None

    def __post_init__(self) -> None:
        if not isinstance(self.unavailable_positions, (list, tuple)):
            raise ValueError("unavailable_positions must be an ordered array.")
        object.__setattr__(
            self,
            "unavailable_positions",
            tuple(self.unavailable_positions),
        )
        if self.status not in {"available", "unavailable"}:
            raise ValueError("status must be available or unavailable.")
        if self.status == "available":
            if (
                self.unavailable_reason is not None
                or self.unavailable_positions
                or self.historical_list is None
                or self.aggregation is None
            ):
                raise ValueError("Available list materialization requires list and aggregation.")
        elif (
            self.unavailable_reason not in MATCH_LIST_MATERIALIZATION_UNAVAILABLE_REASONS
            or not self.unavailable_positions
            or self.historical_list is not None
            or self.aggregation is not None
        ):
            raise ValueError("Unavailable list materialization requires positions and reason.")
        if tuple(sorted(self.unavailable_positions)) != self.unavailable_positions or any(
            type(position) is not int or not 1 <= position <= 36
            for position in self.unavailable_positions
        ):
            raise ValueError("unavailable_positions must use unique Match-position order.")
        if len(set(self.unavailable_positions)) != len(self.unavailable_positions):
            raise ValueError("unavailable_positions must not contain duplicates.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "unavailable_positions": list(self.unavailable_positions),
            "historical_list": (
                None
                if self.historical_list is None
                else build_serializable_fixed_three_player_historical_list(self.historical_list)
            ),
            "aggregation": (
                None
                if self.aggregation is None
                else build_serializable_fixed_three_player_historical_list_aggregation(
                    self.aggregation
                )
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspaceMaterializationV1:
    """Reconciled internal Match preparation without workflow execution."""

    match_workspace_materialization_version: int = MATCH_WORKSPACE_MATERIALIZATION_VERSION
    status: str
    match_id: str
    workspace_revision: int
    match_played_at: str | None
    player_statistics_preparation: MatchPlayerStatisticsPreparationV1
    slot_materializations: tuple[MatchWorkspaceSlotMaterializationV1, ...]
    prepared_decision_count: int
    skipped_decision_count: int
    historical_game_count: int
    training_record_count: int
    passed_deal_count: int
    commentary_count: int
    response_link_count: int
    training_source_collection: MatchTrainingSourceCollectionV1
    historical_list_materialization: MatchHistoricalListMaterializationV1

    def __post_init__(self) -> None:
        if (
            type(self.match_workspace_materialization_version) is not int
            or self.match_workspace_materialization_version
            != MATCH_WORKSPACE_MATERIALIZATION_VERSION
        ):
            raise ValueError(
                "match_workspace_materialization_version must equal "
                f"{MATCH_WORKSPACE_MATERIALIZATION_VERSION}."
            )
        if self.status not in MATCH_WORKSPACE_MATERIALIZATION_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_WORKSPACE_MATERIALIZATION_STATUSES)}."
            )
        if type(self.workspace_revision) is not int or self.workspace_revision < 0:
            raise ValueError("workspace_revision must be a non-negative integer.")
        if self.match_played_at is not None:
            parse_rfc3339_datetime(self.match_played_at, "match_played_at")
        if not isinstance(self.slot_materializations, (list, tuple)) or any(
            type(item) is not MatchWorkspaceSlotMaterializationV1
            for item in self.slot_materializations
        ):
            raise ValueError("slot_materializations must contain Slot Materialization values.")
        object.__setattr__(
            self,
            "slot_materializations",
            tuple(self.slot_materializations),
        )
        if len(self.slot_materializations) != 36:
            raise ValueError("slot_materializations must contain exactly 36 values.")
        if tuple(item.match_position for item in self.slot_materializations) != tuple(range(1, 37)):
            raise ValueError("Slot materializations must preserve Match-position order.")
        for field_name in (
            "prepared_decision_count",
            "skipped_decision_count",
            "historical_game_count",
            "training_record_count",
            "passed_deal_count",
            "commentary_count",
            "response_link_count",
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        expected_counts = {
            "prepared_decision_count": sum(
                0
                if item.decision_review_preparation is None
                else item.decision_review_preparation.prepared_decision_count
                for item in self.slot_materializations
            ),
            "skipped_decision_count": sum(
                0
                if item.decision_review_preparation is None
                else item.decision_review_preparation.skipped_decision_count
                for item in self.slot_materializations
            ),
            "historical_game_count": sum(
                item.historical_materialization.status == "available"
                for item in self.slot_materializations
            ),
            "training_record_count": sum(
                item.training_source_materialization.status == "available"
                for item in self.slot_materializations
            ),
            "passed_deal_count": sum(
                item.slot_kind == "passed_deal" for item in self.slot_materializations
            ),
            "commentary_count": sum(item.commentary_count for item in self.slot_materializations),
            "response_link_count": sum(
                item.response_link_count for item in self.slot_materializations
            ),
        }
        if any(getattr(self, field_name) != count for field_name, count in expected_counts.items()):
            raise ValueError("Workspace materialization counts must reconcile with Slots.")
        occupied_count = sum(item.slot_kind != "empty" for item in self.slot_materializations)
        expected_status = (
            "complete"
            if self.historical_list_materialization.status == "available"
            else "empty"
            if occupied_count == 0
            else "partial"
        )
        if self.status != expected_status:
            raise ValueError("status must match occupancy and list availability.")
        if self.training_source_collection.available_record_count != (self.training_record_count):
            raise ValueError("Training collection count must equal Workspace count.")
        if (
            self.player_statistics_preparation.match_id != self.match_id
            or self.player_statistics_preparation.match_played_at != self.match_played_at
            or self.training_source_collection.match_id != self.match_id
            or any(
                item.historical_materialization.match_id != self.match_id
                or (
                    item.decision_review_preparation is not None
                    and item.decision_review_preparation.match_id != self.match_id
                )
                for item in self.slot_materializations
            )
        ):
            raise ValueError("All nested materializations must retain the Match ID.")
        if self.historical_list_materialization.historical_list is not None and (
            self.historical_list_materialization.historical_list.list_id != f"{self.match_id}-list"
        ):
            raise ValueError("Historical list identity must derive from the Match ID.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_materialization_version": (
                self.match_workspace_materialization_version
            ),
            "status": self.status,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "match_played_at": self.match_played_at,
            "player_statistics_preparation": (self.player_statistics_preparation.to_dict()),
            "slot_materializations": [item.to_dict() for item in self.slot_materializations],
            "prepared_decision_count": self.prepared_decision_count,
            "skipped_decision_count": self.skipped_decision_count,
            "historical_game_count": self.historical_game_count,
            "training_record_count": self.training_record_count,
            "passed_deal_count": self.passed_deal_count,
            "commentary_count": self.commentary_count,
            "response_link_count": self.response_link_count,
            "training_source_collection": self.training_source_collection.to_dict(),
            "historical_list_materialization": (self.historical_list_materialization.to_dict()),
        }


def _materialize_historical_list_from_slots_v1(
    workspace: MatchWorkspaceV1,
    slot_materializations: tuple[MatchWorkspaceSlotMaterializationV1, ...],
    *,
    lot_order: tuple[str, ...] | None,
) -> MatchHistoricalListMaterializationV1:
    empty_positions = tuple(
        item.match_position for item in slot_materializations if item.slot_kind == "empty"
    )
    if empty_positions:
        return MatchHistoricalListMaterializationV1(
            status="unavailable",
            unavailable_reason="workspace_not_structurally_complete",
            unavailable_positions=empty_positions,
            historical_list=None,
            aggregation=None,
        )
    unavailable_positions = tuple(
        item.match_position
        for item in slot_materializations
        if item.slot_kind == "observed_game"
        and item.historical_materialization.status == "unavailable"
    )
    if unavailable_positions:
        return MatchHistoricalListMaterializationV1(
            status="unavailable",
            unavailable_reason="observed_game_not_historical_materializable",
            unavailable_positions=unavailable_positions,
            historical_list=None,
            aggregation=None,
        )

    definition = workspace.match_definition
    entries = []
    for item in slot_materializations:
        entry_id = f"{definition.match_id}-entry-{item.match_position:02d}"
        if item.slot_kind == "passed_deal":
            entries.append(
                {
                    "entry_id": entry_id,
                    "entry_kind": "passed_deal",
                    "played_at": definition.played_at,
                }
            )
        else:
            historical_game = item.historical_materialization.historical_game
            assert historical_game is not None
            entries.append(
                {
                    "entry_id": entry_id,
                    "entry_kind": "played_game",
                    "historical_game": item.historical_materialization.to_dict()["historical_game"],
                }
            )
    entry_facts_output: list[tuple[FixedThreePlayerHistoricalListEntryFact, ...]] = []
    try:
        historical_list = _build_fixed_three_player_historical_list(
            {
                "schema_version": FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION,
                "list_id": f"{definition.match_id}-list",
                "players": [
                    {
                        "player_id": participant.player_id,
                        "player_label": participant.player_label,
                        "table_place": participant.table_place,
                    }
                    for participant in definition.participants
                ],
                "entries": entries,
            },
            _entry_facts_output=entry_facts_output,
        )
    except ValueError as error:
        raise SkatMindInvariantError(
            "Available Match evidence did not build the existing fixed list."
        ) from error
    if len(entry_facts_output) != 1:
        raise SkatMindInvariantError("List materialization must derive Entry Facts exactly once.")
    try:
        aggregation = _build_fixed_three_player_historical_list_aggregation(
            historical_list,
            lot_order=None if lot_order is None else list(lot_order),
            _validated_entry_facts=entry_facts_output[0],
        )
    except ValueError as error:
        if lot_order is not None:
            try:
                _build_fixed_three_player_historical_list_aggregation(
                    historical_list,
                    lot_order=None,
                    _validated_entry_facts=entry_facts_output[0],
                )
            except ValueError as internal_error:
                raise SkatMindInvariantError(
                    "Available Match list did not build the existing aggregation."
                ) from internal_error
            raise
        raise SkatMindInvariantError(
            "Available Match list did not build the existing aggregation."
        ) from error
    return MatchHistoricalListMaterializationV1(
        status="available",
        unavailable_reason=None,
        unavailable_positions=(),
        historical_list=historical_list,
        aggregation=aggregation,
    )


def _build_slot_materializations_v1(
    workspace: MatchWorkspaceV1,
    statistics: MatchPlayerStatisticsPreparationV1,
    validated_traces: dict[int, ObservedGameTraceSummaryV1],
) -> tuple[MatchWorkspaceSlotMaterializationV1, ...]:
    results = []
    source_title = workspace.match_definition.source.source_title
    for slot in workspace.slots:
        if slot.observed_game is None:
            reason = "slot_empty" if slot.slot_kind == "empty" else "passed_deal"
            historical = _unavailable(
                workspace,
                match_position=slot.match_position,
                game_id=None,
                reason=reason,
            )
            training = materialize_match_training_source_record_v1(
                historical,
                source_title=source_title,
            )
            results.append(
                MatchWorkspaceSlotMaterializationV1(
                    match_position=slot.match_position,
                    slot_kind=slot.slot_kind,
                    game_id=None,
                    evidence_summary=None,
                    decision_review_preparation=None,
                    historical_materialization=historical,
                    training_source_materialization=training,
                    commentary_count=0,
                    response_link_count=0,
                )
            )
            continue

        reconstruction = build_match_observed_game_reconstruction_v1(
            slot.observed_game,
            validated_trace=validated_traces[slot.match_position],
        )
        decisions = _build_match_decision_review_preparation_from_reconstruction_v1(
            reconstruction,
            source_played_at=workspace.match_definition.played_at,
            statistics_preparation=statistics,
        )
        historical = _materialize_match_observed_game_historical_from_reconstruction_v1(
            workspace,
            reconstruction=reconstruction,
        )
        training = materialize_match_training_source_record_v1(
            historical,
            source_title=source_title,
        )
        results.append(
            MatchWorkspaceSlotMaterializationV1(
                match_position=slot.match_position,
                slot_kind=slot.slot_kind,
                game_id=slot.observed_game.game_id,
                evidence_summary=reconstruction.evidence_summary,
                decision_review_preparation=decisions,
                historical_materialization=historical,
                training_source_materialization=training,
                commentary_count=len(slot.observed_game.commentaries),
                response_link_count=len(slot.observed_game.response_links),
            )
        )
    return tuple(results)


def materialize_match_workspace_historical_list_v1(
    workspace: MatchWorkspaceV1,
    *,
    lot_order: tuple[str, ...] | None = None,
) -> MatchHistoricalListMaterializationV1:
    """Materializes the complete existing list without executing its Root workflow."""
    validated_traces = dict(_validate_match_workspace_with_traces_v1(workspace))
    statistics = build_match_player_statistics_preparation_v1(workspace.match_definition)
    slots = _build_slot_materializations_v1(
        workspace,
        statistics,
        validated_traces,
    )
    return _materialize_historical_list_from_slots_v1(
        workspace,
        slots,
        lot_order=lot_order,
    )


def build_match_workspace_materialization_v1(
    workspace: MatchWorkspaceV1,
    *,
    lot_order: tuple[str, ...] | None = None,
) -> MatchWorkspaceMaterializationV1:
    """Builds one deterministic evidence-aware Match materialization summary."""
    validated_traces = dict(_validate_match_workspace_with_traces_v1(workspace))
    statistics = build_match_player_statistics_preparation_v1(workspace.match_definition)
    slots = _build_slot_materializations_v1(
        workspace,
        statistics,
        validated_traces,
    )
    historical_list = _materialize_historical_list_from_slots_v1(
        workspace,
        slots,
        lot_order=lot_order,
    )
    training_materializations = tuple(item.training_source_materialization for item in slots)
    training_collection = build_match_training_source_collection_v1(
        match_id=workspace.match_definition.match_id,
        materializations=training_materializations,
    )
    occupied_count = sum(item.slot_kind != "empty" for item in slots)
    status = (
        "complete"
        if historical_list.status == "available"
        else "empty"
        if occupied_count == 0
        else "partial"
    )
    return MatchWorkspaceMaterializationV1(
        status=status,
        match_id=workspace.match_definition.match_id,
        workspace_revision=workspace.revision,
        match_played_at=workspace.match_definition.played_at,
        player_statistics_preparation=statistics,
        slot_materializations=slots,
        prepared_decision_count=sum(
            0
            if item.decision_review_preparation is None
            else item.decision_review_preparation.prepared_decision_count
            for item in slots
        ),
        skipped_decision_count=sum(
            0
            if item.decision_review_preparation is None
            else item.decision_review_preparation.skipped_decision_count
            for item in slots
        ),
        historical_game_count=sum(
            item.historical_materialization.status == "available" for item in slots
        ),
        training_record_count=training_collection.available_record_count,
        passed_deal_count=sum(item.slot_kind == "passed_deal" for item in slots),
        commentary_count=sum(item.commentary_count for item in slots),
        response_link_count=sum(item.response_link_count for item in slots),
        training_source_collection=training_collection,
        historical_list_materialization=historical_list,
    )
