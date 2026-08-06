from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from skat_ai.errors import SkatAIInformationPolicyError, SkatAIValidationError
from skat_ai.field_provenance import (
    _PUBLIC_REDACTION_TOKEN,
    FieldProvenanceEntry,
    FieldProvenanceLedger,
)

INFORMATION_USE_CONTEXT_STAGES = (
    "request_start",
    "decision_time",
    "after_actual_play",
    "game_end",
    "offline_review",
    "engine_internal",
)
INFORMATION_USE_CONTEXT_PERSPECTIVE_SIDES = ("declarer", "defenders")

_DECISION_TIME_OR_LATER_STAGES = {
    "decision_time",
    "after_actual_play",
    "game_end",
    "offline_review",
    "engine_internal",
}
_AFTER_ACTUAL_PLAY_STAGES = {
    "after_actual_play",
    "game_end",
    "offline_review",
    "engine_internal",
}
_GAME_END_STAGES = {"game_end", "offline_review", "engine_internal"}
_OFFLINE_REVIEW_STAGES = {"offline_review", "engine_internal"}


def _validate_optional_identifier(value: object, *, path: str) -> None:
    if value is not None and (
        not isinstance(value, str) or not value or value != value.strip()
    ):
        raise SkatAIValidationError(
            f"{path} must be a non-empty, non-padded string or null.",
            path=path,
        )


def _validate_optional_index(value: object, *, path: str) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value < 0
    ):
        raise SkatAIValidationError(
            f"{path} must be a non-negative integer or null.",
            path=path,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationUseContext:
    """Immutable workflow stage and perspective for one proposed field use."""

    workflow: str
    stage: str
    perspective_player_id: str | None
    perspective_side: str | None
    decision_index: int | None
    event_index: int | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.workflow, str)
            or not self.workflow
            or self.workflow != self.workflow.strip()
        ):
            raise SkatAIValidationError(
                "workflow must be a non-empty, non-padded string.",
                path="workflow",
            )
        if self.stage not in INFORMATION_USE_CONTEXT_STAGES:
            raise SkatAIValidationError(
                f"stage must be one of {list(INFORMATION_USE_CONTEXT_STAGES)}.",
                path="stage",
            )
        _validate_optional_identifier(
            self.perspective_player_id,
            path="perspective_player_id",
        )
        if (
            self.perspective_side is not None
            and self.perspective_side not in INFORMATION_USE_CONTEXT_PERSPECTIVE_SIDES
        ):
            raise SkatAIValidationError(
                "perspective_side must be declarer, defenders, or null.",
                path="perspective_side",
            )
        _validate_optional_index(self.decision_index, path="decision_index")
        _validate_optional_index(self.event_index, path="event_index")


def _visibility_allows_use(
    entry: FieldProvenanceEntry,
    context: InformationUseContext,
) -> bool:
    if entry.visibility == "public":
        return True
    if entry.visibility == "local_private":
        return context.perspective_player_id == entry.perspective_player_id
    if entry.visibility == "declarer_private":
        return context.perspective_side == "declarer"
    if entry.visibility == "defender_private":
        return context.perspective_side == "defenders"
    if entry.visibility == "post_game_only":
        return context.stage in _GAME_END_STAGES
    return context.stage == "engine_internal"


def _availability_allows_use(
    entry: FieldProvenanceEntry,
    context: InformationUseContext,
) -> bool:
    if entry.available_from == "request_start":
        return True
    if entry.available_from == "current_decision":
        return (
            context.stage in _DECISION_TIME_OR_LATER_STAGES
            and context.decision_index is not None
            and context.decision_index >= entry.available_from_decision_index
        )
    if entry.available_from == "after_public_event":
        return (
            context.stage in _DECISION_TIME_OR_LATER_STAGES
            and context.event_index is not None
            and context.event_index >= entry.available_from_event_index
        )
    if entry.available_from == "after_actual_play":
        return (
            context.stage in _AFTER_ACTUAL_PLAY_STAGES
            and context.decision_index is not None
            and context.decision_index >= entry.available_from_decision_index
        )
    if entry.available_from == "game_end":
        return context.stage in _GAME_END_STAGES
    return context.stage in _OFFLINE_REVIEW_STAGES


def is_field_provenance_entry_available(
    entry: FieldProvenanceEntry,
    context: InformationUseContext,
) -> bool:
    """Returns whether visibility and availability both permit one field use."""
    if not isinstance(entry, FieldProvenanceEntry):
        raise SkatAIValidationError(
            "entry must be a FieldProvenanceEntry.",
            path="entry",
        )
    if not isinstance(context, InformationUseContext):
        raise SkatAIValidationError(
            "context must be an InformationUseContext.",
            path="context",
        )
    return _visibility_allows_use(entry, context) and _availability_allows_use(
        entry,
        context,
    )


def validate_field_provenance_entry_use(
    entry: FieldProvenanceEntry,
    context: InformationUseContext,
) -> None:
    """Raises a stable non-disclosing information-policy error for denied use."""
    if not is_field_provenance_entry_available(entry, context):
        raise SkatAIInformationPolicyError(
            "Field provenance is not available in the requested information-use context.",
            path=entry.field_path,
        )


def redact_field_provenance_ledger_for_public_output(
    ledger: FieldProvenanceLedger,
) -> FieldProvenanceLedger:
    """Returns a new ledger with all engine-private provenance detail omitted."""
    if not isinstance(ledger, FieldProvenanceLedger):
        raise SkatAIValidationError(
            "ledger must be a FieldProvenanceLedger.",
            path="ledger",
        )
    removed_paths = {
        entry.field_path for entry in ledger.entries if entry.visibility == "engine_private"
    }
    redaction_occurred = bool(removed_paths)
    retained_entries: list[FieldProvenanceEntry] = []
    for entry in ledger.entries:
        if entry.field_path in removed_paths:
            continue
        references = tuple(
            reference
            for reference in entry.source_references
            if reference.visibility != "engine_private"
        )
        dependencies = tuple(
            path for path in entry.dependency_paths if path not in removed_paths
        )
        if references != entry.source_references or dependencies != entry.dependency_paths:
            redaction_occurred = True
        retained_entries.append(
            replace(
                entry,
                source_references=references,
                dependency_paths=dependencies,
            )
        )

    limitations = ledger.limitations
    if redaction_occurred and "private_dependencies_redacted" not in limitations:
        limitations = (*limitations, "private_dependencies_redacted")
    if not redaction_occurred:
        return ledger
    return FieldProvenanceLedger(
        provenance_version=ledger.provenance_version,
        status=ledger.status,
        entries=tuple(retained_entries),
        exemptions=ledger.exemptions,
        limitations=limitations,
        _public_redaction_token=_PUBLIC_REDACTION_TOKEN,
    )


def build_serializable_information_use_context(
    context: InformationUseContext,
) -> dict[str, Any]:
    """Builds the deterministic internal information-use representation."""
    return {
        "workflow": context.workflow,
        "stage": context.stage,
        "perspective_player_id": context.perspective_player_id,
        "perspective_side": context.perspective_side,
        "decision_index": context.decision_index,
        "event_index": context.event_index,
    }
