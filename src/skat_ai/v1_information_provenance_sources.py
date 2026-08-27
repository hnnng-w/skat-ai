from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING

from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.errors import SkatAIInvariantError, SkatAIValidationError
from skat_ai.field_provenance import FieldProvenanceEntry, FieldProvenanceLedger
from skat_ai.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
    enumerate_json_leaf_paths,
)
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.information_view import is_skat_visible_to_local_player

if TYPE_CHECKING:
    from skat_ai.application.contracts import ApplicationInvocation
    from skat_ai.application.provenance import ApplicationProvenanceAttachment


V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME = "v1_source/request"
V1_INFORMATION_PROVENANCE_OPTIONS_SOURCE_NAME = "v1_source/application_options"
V1_INFORMATION_PROVENANCE_EXTERNAL_SOURCE_NAME = (
    "v1_source/external_opponent_statistics"
)
V1_INFORMATION_PROVENANCE_CONSUMED_REQUEST_SOURCE_NAME = (
    "v1_source/consumed_request"
)

_REQUEST_REFERENCE_IDS = {
    WorkflowV1.POSITION_ANALYSIS: (
        "position_analysis_request",
        "position_public_game_events",
        "retrospective_position_request",
        "retrospective_position_public_state",
    ),
    WorkflowV1.HISTORICAL_GAME: ("historical_game_request",),
    WorkflowV1.TRAINING_DATASET: ("training_dataset_input",),
    WorkflowV1.TRAINING_DATASET_PREPARATION: (
        "training_dataset_preparation_input",
        "dataset_preparation_partition_weights",
        "dataset_preparation_base_seed",
        "source_identity_fingerprint",
        "unseen_player_selector_identity",
    ),
    WorkflowV1.OPPONENT_STATISTICS: ("opponent_statistics_input",),
    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST: ("historical_list_input",),
    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON: (
        "historical_list_comparison_input",
    ),
}


def exact_v1_json_equal(first: object, second: object) -> bool:
    """Compares canonical JSON values with exact types and object-key order."""
    if isinstance(first, Mapping) and isinstance(second, Mapping):
        if tuple(first) != tuple(second):
            return False
        return all(exact_v1_json_equal(first[key], second[key]) for key in first)
    if isinstance(first, (list, tuple)) and isinstance(second, (list, tuple)):
        return len(first) == len(second) and all(
            exact_v1_json_equal(left, right)
            for left, right in zip(first, second, strict=True)
        )
    return type(first) is type(second) and first == second


def canonical_v1_external_reference(reference: str) -> str:
    """Returns the stable private identity for one accepted opaque reference."""
    if reference and reference == reference.strip():
        return reference
    digest = hashlib.sha256(reference.encode("utf-8")).hexdigest()
    return f"external-reference-sha256:{digest}"


def _validate_identifier(value: object, *, path: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SkatAIValidationError(
            f"{path} must be a non-empty, non-padded string.",
            path=path,
        )
    return value


def _ordered_string_tuple(value: object, *, path: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise SkatAIValidationError(
            f"{path} must be an ordered string sequence.",
            path=path,
        )
    copied = tuple(value)
    if any(not isinstance(item, str) or not item for item in copied):
        raise SkatAIValidationError(
            f"{path} must contain non-empty strings.",
            path=path,
        )
    if len(copied) != len(set(copied)):
        raise SkatAIValidationError(
            f"{path} must not contain duplicates.",
            path=path,
        )
    return tuple(sorted(copied))


@dataclass(frozen=True, slots=True, kw_only=True)
class V1InformationProvenanceSourceMetadata:
    """Caller-presence metadata lost by effective option normalization."""

    enforcement_version: int = 1
    application_options_supplied: bool = False
    supplied_execution_option_names: tuple[str, ...] = ()
    supplied_workflow_option_names: tuple[str, ...] = ()
    validate_output: bool = True
    validate_output_supplied: bool = False
    include_provenance: bool = False
    include_provenance_supplied: bool = False

    def __post_init__(self) -> None:
        if type(self.enforcement_version) is not int or self.enforcement_version != 1:
            raise SkatAIValidationError(
                "enforcement_version must equal 1.",
                path="enforcement_version",
            )
        for name in (
            "application_options_supplied",
            "validate_output",
            "validate_output_supplied",
            "include_provenance",
            "include_provenance_supplied",
        ):
            if not isinstance(getattr(self, name), bool):
                raise SkatAIValidationError(
                    f"{name} must be a boolean.",
                    path=name,
                )
        object.__setattr__(
            self,
            "supplied_execution_option_names",
            _ordered_string_tuple(
                self.supplied_execution_option_names,
                path="supplied_execution_option_names",
            ),
        )
        object.__setattr__(
            self,
            "supplied_workflow_option_names",
            _ordered_string_tuple(
                self.supplied_workflow_option_names,
                path="supplied_workflow_option_names",
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class V1InformationProvenanceSourceBinding:
    """One invocation-local stable reference identity and its exact source."""

    workflow: WorkflowV1
    reference_type: str
    reference_id: str
    attachment_name: str
    document: Mapping[str, object]
    visibility: str = "public"

    def __post_init__(self) -> None:
        from skat_ai.application.contracts import _freeze_json_object

        if not isinstance(self.workflow, WorkflowV1):
            raise SkatAIValidationError("workflow must be a WorkflowV1.", path="workflow")
        if self.reference_type not in {
            "request",
            "historical_game",
            "historical_event",
            "external_record",
            "rule_contract",
            "algorithm",
            "aggregate",
            "retrospective_observation",
            "dataset_plan",
        }:
            raise SkatAIValidationError(
                "reference_type is not supported.",
                path="reference_type",
            )
        _validate_identifier(self.reference_id, path="reference_id")
        _validate_identifier(self.attachment_name, path="attachment_name")
        if self.visibility not in {"public", "engine_private"}:
            raise SkatAIValidationError(
                "visibility must be public or engine_private.",
                path="visibility",
            )
        object.__setattr__(
            self,
            "document",
            _freeze_json_object(self.document, path="document"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class V1InformationProvenanceSources:
    """Exact invocation-local consumed sources built once before analysis."""

    workflow: WorkflowV1
    attachments: tuple[object, ...]
    bindings: tuple[V1InformationProvenanceSourceBinding, ...]
    source_build_count: int = 1

    def __post_init__(self) -> None:
        from skat_ai.application.provenance import ApplicationProvenanceAttachment

        if not isinstance(self.workflow, WorkflowV1):
            raise SkatAIValidationError("workflow must be a WorkflowV1.", path="workflow")
        attachments = tuple(self.attachments)
        if any(not isinstance(item, ApplicationProvenanceAttachment) for item in attachments):
            raise SkatAIValidationError(
                "attachments must contain ApplicationProvenanceAttachment values.",
                path="attachments",
            )
        names = tuple(item.name for item in attachments)
        if len(names) != len(set(names)):
            raise SkatAIValidationError(
                "source attachment names must be unique.",
                path="attachments",
            )
        bindings = tuple(self.bindings)
        if any(not isinstance(item, V1InformationProvenanceSourceBinding) for item in bindings):
            raise SkatAIValidationError(
                "bindings must contain source bindings.",
                path="bindings",
            )
        keys = tuple((item.reference_type, item.reference_id) for item in bindings)
        if len(keys) != len(set(keys)):
            raise SkatAIValidationError(
                "source binding identities must be unique.",
                path="bindings",
            )
        if type(self.source_build_count) is not int or self.source_build_count != 1:
            raise SkatAIValidationError(
                "source_build_count must equal 1.",
                path="source_build_count",
            )
        object.__setattr__(self, "attachments", attachments)
        object.__setattr__(
            self,
            "bindings",
            tuple(sorted(bindings, key=lambda item: (item.reference_type, item.reference_id))),
        )

def _entry(
    path: str,
    *,
    origin: str,
    visibility: str,
    available_from: str,
    derivation: str,
    decision_index: int | None = None,
    event_index: int | None = None,
    perspective_player_id: str | None = None,
) -> FieldProvenanceEntry:
    return FieldProvenanceEntry(
        field_path=path,
        coverage_kind="field",
        origin=origin,
        visibility=visibility,
        available_from=available_from,
        available_from_decision_index=decision_index,
        available_from_event_index=event_index,
        derivation=derivation,
        source_references=(),
        dependency_paths=(),
        subject_player_id=None,
        perspective_player_id=perspective_player_id,
    )


def _position_decision_index(document: Mapping[str, object]) -> int:
    played = document.get("played_cards", ())
    current = document.get("current_trick", ())
    completed = document.get("completed_tricks", ())
    completed_count = sum(
        len(cards)
        for trick in completed
        if isinstance(trick, Mapping)
        and isinstance((cards := trick.get("cards", trick.get("plays", ()))), (list, tuple))
    ) if isinstance(completed, (list, tuple)) else 0
    return completed_count + sum(
        len(value) if isinstance(value, (list, tuple)) else 0
        for value in (played, current)
    )


def _historical_play_count(document: Mapping[str, object]) -> int:
    historical = document.get("historical_game_input")
    if not isinstance(historical, Mapping):
        return 0
    tricks = historical.get("tricks", ())
    if not isinstance(tricks, (list, tuple)):
        return 0
    return sum(
        len(plays)
        for trick in tricks
        if isinstance(trick, Mapping)
        and isinstance((plays := trick.get("plays", ())), (list, tuple))
    )


def _historical_event_count(document: Mapping[str, object]) -> int:
    historical = document.get("historical_game_input")
    if not isinstance(historical, Mapping):
        return 0
    events = historical.get("game_events", historical.get("continuation_events", ()))
    return len(events) if isinstance(events, (list, tuple)) else 0


def _request_context(
    workflow: WorkflowV1,
    document: Mapping[str, object],
) -> InformationUseContext:
    if workflow is WorkflowV1.POSITION_ANALYSIS:
        analysis_mode = document.get("analysis_mode", "live_decision")
        decision_index = _position_decision_index(document)
        role = document.get("player_role")
        return InformationUseContext(
            workflow=workflow.value,
            stage="decision_time" if analysis_mode == "live_decision" else "offline_review",
            perspective_player_id="me",
            perspective_side="declarer" if role == "declarer" else "defenders",
            decision_index=decision_index,
            event_index=decision_index,
        )
    if workflow is WorkflowV1.HISTORICAL_GAME:
        return InformationUseContext(
            workflow=workflow.value,
            stage="offline_review",
            perspective_player_id=None,
            perspective_side=None,
            decision_index=_historical_play_count(document),
            event_index=_historical_event_count(document),
        )
    return InformationUseContext(
        workflow=workflow.value,
        stage="offline_review",
        perspective_player_id=None,
        perspective_side=None,
        decision_index=None,
        event_index=None,
    )


def _historical_card_index(tokens: tuple[str, ...]) -> int | None:
    try:
        trick_index = tokens.index("tricks")
    except ValueError:
        return None
    if len(tokens) <= trick_index + 4 or tokens[trick_index + 2] != "plays":
        return None
    if tokens[-1] != "card":
        return None
    trick = tokens[trick_index + 1]
    play = tokens[trick_index + 3]
    if not trick.isdecimal() or not play.isdecimal():
        return None
    return int(trick) * 3 + int(play) + 1


def _historical_event_index(tokens: tuple[str, ...]) -> int | None:
    for event_key in ("game_events", "continuation_events"):
        try:
            event_position = tokens.index(event_key)
        except ValueError:
            continue
        if len(tokens) <= event_position + 1:
            return None
        event_index = tokens[event_position + 1]
        return int(event_index) if event_index.isdecimal() else None
    return None


def _request_entry(
    workflow: WorkflowV1,
    document: Mapping[str, object],
    path: str,
) -> FieldProvenanceEntry:
    from skat_ai.field_provenance import parse_json_pointer

    tokens = parse_json_pointer(path)
    if workflow is WorkflowV1.POSITION_ANALYSIS:
        analysis_mode = document.get("analysis_mode", "live_decision")
        decision_index = _position_decision_index(document)
        if tokens and tokens[0] in {"hand", "skat"}:
            if analysis_mode != "live_decision":
                return _entry(
                    path,
                    origin="caller_supplied",
                    visibility="post_game_only",
                    available_from="game_end",
                    derivation="direct",
                )
            if (
                tokens[0] == "skat"
                and document.get("skat")
                and not is_skat_visible_to_local_player(
                player_role=str(document.get("player_role")),
                declarer_player=(
                    str(document["declarer_player"])
                    if document.get("declarer_player") is not None
                    else None
                ),
                    skat_visibility=str(document.get("skat_visibility", "unknown")),
                )
            ):
                return _entry(
                    path,
                    origin="caller_supplied",
                    visibility="post_game_only",
                    available_from="game_end",
                    derivation="direct",
                )
            return _entry(
                path,
                origin="caller_supplied",
                visibility="local_private",
                available_from="current_decision",
                derivation="direct",
                decision_index=decision_index,
                perspective_player_id="me",
            )
        if (
            analysis_mode != "live_decision"
            and len(tokens) >= 2
            and tokens[:2] == ("game_shortening", "remaining_hands")
        ):
            return _entry(
                path,
                origin="caller_supplied",
                visibility="post_game_only",
                available_from="game_end",
                derivation="direct",
            )
        if analysis_mode != "live_decision" and tokens and tokens[-1] in {
            "actual_card",
            "actual_card_played",
        }:
            return _entry(
                path,
                origin="caller_supplied",
                visibility="public",
                available_from="after_actual_play",
                derivation="direct",
                decision_index=decision_index,
            )
    if workflow is WorkflowV1.HISTORICAL_GAME:
        card_index = _historical_card_index(tokens)
        if card_index is not None:
            return _entry(
                path,
                origin="caller_supplied",
                visibility="public",
                available_from="after_actual_play",
                derivation="direct",
                decision_index=card_index,
            )
        event_index = _historical_event_index(tokens)
        if event_index is not None:
            return _entry(
                path,
                origin="caller_supplied",
                visibility="public",
                available_from="after_public_event",
                derivation="direct",
                event_index=event_index,
            )
        private_tokens = {"initial_hand", "skat", "discarded_cards"}
        if any(token in private_tokens for token in tokens):
            return _entry(
                path,
                origin="caller_supplied",
                visibility="post_game_only",
                available_from="game_end",
                derivation="direct",
            )
        if any(token in {"game_end", "game_end_reason"} for token in tokens):
            return _entry(
                path,
                origin="caller_supplied",
                visibility="post_game_only",
                available_from="game_end",
                derivation="direct",
            )
    if workflow in {
        WorkflowV1.TRAINING_DATASET,
        WorkflowV1.TRAINING_DATASET_PREPARATION,
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
    }:
        return _entry(
            path,
            origin="caller_supplied",
            visibility="post_game_only",
            available_from="offline_review",
            derivation="direct",
        )
    return _entry(
        path,
        origin="caller_supplied",
        visibility="public",
        available_from="request_start",
        derivation="direct",
    )


def _build_attachment(
    *,
    name: str,
    document: Mapping[str, object],
    context: InformationUseContext,
    entries: tuple[FieldProvenanceEntry, ...],
) -> ApplicationProvenanceAttachment:
    from skat_ai.application.provenance import ApplicationProvenanceAttachment

    ledger = FieldProvenanceLedger(
        status="complete",
        entries=entries,
        exemptions=(),
        limitations=(),
    )
    return ApplicationProvenanceAttachment(
        name=name,
        document_role="consumed_input",
        document=document,
        ledger=ledger,
        coverage_summary=build_field_provenance_coverage_summary(document, ledger),
        information_use_context=context,
    )


def _json_option_value(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_option_value(item) for item in value]
    return value


def _effective_workflow_options(invocation: ApplicationInvocation) -> dict[str, object]:
    selected = {
        WorkflowV1.POSITION_ANALYSIS: invocation.options.position_analysis,
        WorkflowV1.HISTORICAL_GAME: invocation.options.historical_game,
        WorkflowV1.TRAINING_DATASET: invocation.options.training_dataset,
    }.get(invocation.request.workflow)
    if selected is None:
        return {}
    return {
        item.name: _json_option_value(getattr(selected, item.name))
        for item in fields(selected)
    }


def build_v1_application_options_document(
    invocation: ApplicationInvocation,
) -> dict[str, object]:
    """Builds the exact effective internal Application-option document."""
    metadata = invocation.provenance_source_metadata
    request_document = invocation.request.document
    workflow_options = _effective_workflow_options(invocation)
    if invocation.request.workflow is WorkflowV1.POSITION_ANALYSIS:
        execution_mode = request_document.get("analysis_mode", "live_decision")
    elif invocation.request.workflow is WorkflowV1.TRAINING_DATASET:
        execution_mode = workflow_options.get("operation", "summary")
    else:
        execution_mode = invocation.request.workflow.value
    return {
        "workflow": invocation.request.workflow.value,
        "execution_mode": execution_mode,
        "application_options_supplied": metadata.application_options_supplied,
        "supplied_execution_option_names": list(
            metadata.supplied_execution_option_names
        ),
        "supplied_workflow_option_names": list(
            metadata.supplied_workflow_option_names
        ),
        "workflow_options": workflow_options,
        "include_provenance": metadata.include_provenance,
        "validate_output": metadata.validate_output,
        "external_document_present": (
            invocation.external_documents.opponent_statistics_document is not None
        ),
        "external_document_reference": (
            invocation.external_documents.opponent_statistics_reference
        ),
        "input_reference": invocation.input_reference,
    }


def _options_entry(
    invocation: ApplicationInvocation,
    path: str,
) -> FieldProvenanceEntry:
    from skat_ai.field_provenance import parse_json_pointer

    tokens = parse_json_pointer(path)
    metadata = invocation.provenance_source_metadata
    origin = "rule_derived"
    derivation = "deterministic_rule"
    if len(tokens) >= 2 and tokens[0] == "workflow_options":
        origin = (
            "caller_supplied"
            if tokens[1] in metadata.supplied_workflow_option_names
            else "defaulted"
        )
        derivation = "direct"
    elif tokens and tokens[0] in {
        "application_options_supplied",
        "supplied_execution_option_names",
        "supplied_workflow_option_names",
    }:
        origin = (
            "caller_supplied"
            if metadata.application_options_supplied
            else "defaulted"
        )
        derivation = "direct"
    elif tokens == ("include_provenance",):
        origin = "caller_supplied" if metadata.include_provenance_supplied else "defaulted"
        derivation = "direct"
    elif tokens == ("validate_output",):
        origin = "caller_supplied" if metadata.validate_output_supplied else "defaulted"
        derivation = "direct"
    elif tokens in {
        ("external_document_reference",),
        ("input_reference",),
    }:
        origin = (
            "caller_supplied"
            if tokens == ("input_reference",)
            or invocation.external_documents.opponent_statistics_document is not None
            else "defaulted"
        )
        derivation = "direct"
    return _entry(
        path,
        origin=origin,
        visibility="public",
        available_from="request_start",
        derivation=derivation,
    )


def _source_binding(
    invocation: ApplicationInvocation,
    *,
    reference_type: str,
    reference_id: str,
    attachment_name: str,
    document: Mapping[str, object],
    visibility: str = "public",
) -> V1InformationProvenanceSourceBinding:
    return V1InformationProvenanceSourceBinding(
        workflow=invocation.request.workflow,
        reference_type=reference_type,
        reference_id=reference_id,
        attachment_name=attachment_name,
        document=document,
        visibility=visibility,
    )


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _record_bindings(
    invocation: ApplicationInvocation,
    request_document: Mapping[str, object],
) -> list[V1InformationProvenanceSourceBinding]:
    bindings: list[V1InformationProvenanceSourceBinding] = []
    workflow = invocation.request.workflow

    def append_game_bindings(
        game: Mapping[str, object],
        *,
        historical_actual_alias: bool = False,
        training_record_index: int | None = None,
    ) -> None:
        game_id = game.get("game_id")
        if not isinstance(game_id, str):
            return
        bindings.append(
            _source_binding(
                invocation,
                reference_type="historical_game",
                reference_id=game_id,
                attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                document=game,
            )
        )
        events = game.get("game_events", game.get("continuation_events", ()))
        if isinstance(events, (list, tuple)):
            for index, event in enumerate(events):
                if isinstance(event, Mapping):
                    bindings.append(
                        _source_binding(
                            invocation,
                            reference_type="historical_event",
                            reference_id=f"{game_id}:event:{index}",
                            attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                            document=event,
                        )
                    )
        game_end = _mapping(game.get("game_end"))
        bindings.append(
            _source_binding(
                invocation,
                reference_type="historical_event",
                reference_id=f"{game_id}:terminal",
                attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                document=game_end if game_end is not None else game,
            )
        )
        if historical_actual_alias:
            bindings.append(
                _source_binding(
                    invocation,
                    reference_type="retrospective_observation",
                    reference_id="historical_actual_card",
                    attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                    document=game,
                )
            )
        tricks = game.get("tricks", ())
        decision_index = 1
        if isinstance(tricks, (list, tuple)):
            for trick in tricks:
                plays = trick.get("plays", ()) if isinstance(trick, Mapping) else ()
                if not isinstance(plays, (list, tuple)):
                    continue
                for _play in plays:
                    bindings.append(
                        _source_binding(
                            invocation,
                            reference_type="retrospective_observation",
                            reference_id=f"{game_id}/{decision_index}",
                            attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                            document=game,
                        )
                    )
                    if training_record_index is not None:
                        bindings.append(
                            _source_binding(
                                invocation,
                                reference_type="retrospective_observation",
                                reference_id=(
                                    f"training_target/{training_record_index}/"
                                    f"{decision_index}"
                                ),
                                attachment_name=(
                                    V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME
                                ),
                                document=game,
                            )
                        )
                    decision_index += 1

    if workflow is WorkflowV1.HISTORICAL_GAME:
        game = _mapping(request_document.get("historical_game_input"))
        if game is not None:
            append_game_bindings(game, historical_actual_alias=True)
    elif workflow in {
        WorkflowV1.TRAINING_DATASET,
        WorkflowV1.TRAINING_DATASET_PREPARATION,
    }:
        input_name = (
            "training_dataset_input"
            if workflow is WorkflowV1.TRAINING_DATASET
            else "training_dataset_preparation_input"
        )
        dataset = _mapping(request_document.get(input_name))
        records = dataset.get("records", ()) if dataset is not None else ()
        if isinstance(records, (list, tuple)):
            for index, record in enumerate(records):
                if not isinstance(record, Mapping):
                    continue
                reference_id = (
                    f"training_dataset_record/{index}"
                    if workflow is WorkflowV1.TRAINING_DATASET
                    else f"dataset_preparation_source/{index}"
                )
                bindings.append(
                    _source_binding(
                        invocation,
                        reference_type="request",
                        reference_id=reference_id,
                        attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                        document=record,
                    )
                )
                record_id = record.get("record_id")
                if isinstance(record_id, str):
                    bindings.append(
                        _source_binding(
                            invocation,
                            reference_type="external_record",
                            reference_id=record_id,
                            attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                            document=record,
                        )
                    )
                game = _mapping(record.get("historical_game"))
                if game is not None:
                    append_game_bindings(
                        game,
                        training_record_index=(
                            index if workflow is WorkflowV1.TRAINING_DATASET else None
                        ),
                    )
    elif workflow in {
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
    }:
        if workflow is WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST:
            source_requests: object = (
                request_document.get("fixed_three_player_historical_list_input"),
            )
        else:
            comparison = _mapping(
                request_document.get("fixed_three_player_historical_list_comparison_input")
            )
            source_requests = comparison.get("lists", ()) if comparison is not None else ()
        if isinstance(source_requests, (list, tuple)):
            for source_request in source_requests:
                if not isinstance(source_request, Mapping):
                    continue
                historical_list = _mapping(source_request.get("historical_list"))
                if historical_list is None:
                    continue
                list_id = historical_list.get("list_id")
                if not isinstance(list_id, str):
                    continue
                bindings.append(
                    _source_binding(
                        invocation,
                        reference_type="external_record",
                        reference_id=f"historical_list/{list_id}",
                        attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                        document=source_request,
                    )
                )
                entries = historical_list.get("entries", ())
                if not isinstance(entries, (list, tuple)):
                    continue
                for entry_number, entry in enumerate(entries, start=1):
                    if not isinstance(entry, Mapping):
                        continue
                    bindings.append(
                        _source_binding(
                            invocation,
                            reference_type="external_record",
                            reference_id=(
                                f"historical_list/{list_id}/entry/{entry_number}"
                            ),
                            attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                            document=entry,
                        )
                    )
                    game = _mapping(entry.get("historical_game"))
                    if game is not None:
                        append_game_bindings(game)
    elif workflow is WorkflowV1.OPPONENT_STATISTICS:
        statistics = _mapping(request_document.get("opponent_statistics_input"))
        records = statistics.get("records", ()) if statistics is not None else ()
        if isinstance(records, (list, tuple)):
            for index, record in enumerate(records):
                if not isinstance(record, Mapping):
                    continue
                source = _mapping(record.get("source")) or {}
                source_type = source.get("source_type")
                bindings.append(
                    _source_binding(
                        invocation,
                        reference_type=(
                            "aggregate" if source_type == "historical_games" else "external_record"
                        ),
                        reference_id=f"opponent_statistics_record/{index}",
                        attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                        document=record,
                    )
                )
    return bindings


def _build_bindings(
    invocation: ApplicationInvocation,
    request_document: Mapping[str, object],
    options_document: Mapping[str, object],
    external_document: Mapping[str, object] | None,
) -> tuple[V1InformationProvenanceSourceBinding, ...]:
    request_binding_documents = {
        "training_dataset_input": _mapping(
            request_document.get("training_dataset_input")
        ),
        "training_dataset_preparation_input": _mapping(
            request_document.get("training_dataset_preparation_input")
        ),
        "opponent_statistics_input": _mapping(
            request_document.get("opponent_statistics_input")
        ),
        "historical_list_comparison_input": _mapping(
            request_document.get("fixed_three_player_historical_list_comparison_input")
        ),
        "historical_list_input": _mapping(
            request_document.get("fixed_three_player_historical_list_input")
        ),
    }
    bindings = [
        _source_binding(
            invocation,
            reference_type="request",
            reference_id=reference_id,
            attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
            document=request_binding_documents.get(reference_id) or request_document,
        )
        for reference_id in _REQUEST_REFERENCE_IDS[invocation.request.workflow]
    ]
    bindings.append(
        _source_binding(
            invocation,
            reference_type="request",
            reference_id="application_input_reference",
            attachment_name=V1_INFORMATION_PROVENANCE_OPTIONS_SOURCE_NAME,
            document=options_document,
        )
    )
    if invocation.request.workflow is WorkflowV1.POSITION_ANALYSIS:
        bindings.append(
            _source_binding(
                invocation,
                reference_type="retrospective_observation",
                reference_id="flat_actual_card",
                attachment_name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
                document=request_document,
            )
        )
    workflow_options = _mapping(options_document.get("workflow_options")) or {}
    option_reference = {
        WorkflowV1.POSITION_ANALYSIS: "position_analysis_options",
        WorkflowV1.HISTORICAL_GAME: "historical_review_options",
        WorkflowV1.TRAINING_DATASET: "training_dataset_execution_options",
    }.get(invocation.request.workflow)
    if option_reference is not None:
        bindings.append(
            _source_binding(
                invocation,
                reference_type="request",
                reference_id=option_reference,
                attachment_name=V1_INFORMATION_PROVENANCE_OPTIONS_SOURCE_NAME,
                document=workflow_options,
            )
        )
    bindings.extend(_record_bindings(invocation, request_document))
    if external_document is not None:
        reference = invocation.external_documents.opponent_statistics_reference
        if reference is None:
            raise SkatAIInvariantError(
                "Injected external provenance has no retained source identity."
            )
        bindings.append(
            _source_binding(
                invocation,
                reference_type="external_record",
                reference_id=canonical_v1_external_reference(reference),
                attachment_name=V1_INFORMATION_PROVENANCE_EXTERNAL_SOURCE_NAME,
                document=external_document,
                visibility="engine_private",
            )
        )
    unique: dict[tuple[str, str], V1InformationProvenanceSourceBinding] = {}
    for binding in bindings:
        key = (binding.reference_type, binding.reference_id)
        previous = unique.get(key)
        if previous is not None and previous != binding:
            raise SkatAIInvariantError(
                "Provenance source identity resolves to different documents."
            )
        unique[key] = binding
    return tuple(unique.values())


def build_v1_information_provenance_sources(
    invocation: ApplicationInvocation,
) -> V1InformationProvenanceSources:
    """Builds exact Request, effective-option, and supplied-external sources once."""
    from skat_ai.application.contracts import ApplicationInvocation

    if not isinstance(invocation, ApplicationInvocation):
        raise SkatAIValidationError(
            "invocation must be an ApplicationInvocation.",
            path="invocation",
        )
    request_document = invocation.request.to_dict()["document"]
    if not isinstance(request_document, dict):
        raise SkatAIInvariantError("Verified Root Request did not thaw to an object.")
    request_context = _request_context(invocation.request.workflow, request_document)
    request_attachment = _build_attachment(
        name=V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME,
        document=request_document,
        context=request_context,
        entries=tuple(
            _request_entry(invocation.request.workflow, request_document, path)
            for path in enumerate_json_leaf_paths(request_document)
        ),
    )
    options_document = build_v1_application_options_document(invocation)
    options_attachment = _build_attachment(
        name=V1_INFORMATION_PROVENANCE_OPTIONS_SOURCE_NAME,
        document=options_document,
        context=InformationUseContext(
            workflow=invocation.request.workflow.value,
            stage="engine_internal",
            perspective_player_id=None,
            perspective_side=None,
            decision_index=None,
            event_index=None,
        ),
        entries=tuple(
            _options_entry(invocation, path)
            for path in enumerate_json_leaf_paths(options_document)
        ),
    )
    attachments: list[ApplicationProvenanceAttachment] = [
        request_attachment,
        options_attachment,
    ]
    if (
        invocation.request.workflow is WorkflowV1.POSITION_ANALYSIS
        and request_document.get("analysis_mode", "live_decision") == "live_decision"
    ):
        from skat_ai.information_view import build_local_analysis_input

        consumed_request = build_local_analysis_input(request_document)
        attachments.append(
            _build_attachment(
                name=V1_INFORMATION_PROVENANCE_CONSUMED_REQUEST_SOURCE_NAME,
                document=consumed_request,
                context=_request_context(invocation.request.workflow, consumed_request),
                entries=tuple(
                    _request_entry(
                        invocation.request.workflow,
                        consumed_request,
                        path,
                    )
                    for path in enumerate_json_leaf_paths(consumed_request)
                ),
            )
        )
    external_document = (
        invocation.external_documents.opponent_statistics_to_dict()
    )
    if external_document is not None:
        attachments.append(
            _build_attachment(
                name=V1_INFORMATION_PROVENANCE_EXTERNAL_SOURCE_NAME,
                document=external_document,
                context=InformationUseContext(
                    workflow=invocation.request.workflow.value,
                    stage="engine_internal",
                    perspective_player_id=None,
                    perspective_side=None,
                    decision_index=None,
                    event_index=None,
                ),
                entries=tuple(
                    _entry(
                        path,
                        origin="external_source",
                        visibility="engine_private",
                        available_from="request_start",
                        derivation="validated",
                    )
                    for path in enumerate_json_leaf_paths(external_document)
                ),
            )
        )
    return V1InformationProvenanceSources(
        workflow=invocation.request.workflow,
        attachments=tuple(attachments),
        bindings=_build_bindings(
            invocation,
            request_document,
            options_document,
            external_document,
        ),
    )


def consumed_v1_request_document(
    sources: V1InformationProvenanceSources,
) -> Mapping[str, object]:
    """Returns the exact request document authorized for handler dispatch."""
    attachment = next(
        (
            item
            for item in sources.attachments
            if item.name == V1_INFORMATION_PROVENANCE_CONSUMED_REQUEST_SOURCE_NAME
        ),
        None,
    )
    if attachment is not None:
        return attachment.document
    request_attachment = next(
        (
            item
            for item in sources.attachments
            if item.name == V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME
        ),
        None,
    )
    if request_attachment is None:
        raise SkatAIInvariantError("Provenance sources have no consumed Request.")
    return request_attachment.document


def validate_v1_information_provenance_sources(
    invocation: ApplicationInvocation,
    sources: V1InformationProvenanceSources,
) -> None:
    """Rejects a stale or substituted consumed source without rebuilding it."""
    if sources.workflow is not invocation.request.workflow:
        raise SkatAIInvariantError("Consumed provenance source workflow changed.")
    by_name = {item.name: item for item in sources.attachments}
    if len(by_name) != len(sources.attachments):
        raise SkatAIInvariantError("Consumed provenance source attachment is duplicated.")
    request = by_name.get(V1_INFORMATION_PROVENANCE_REQUEST_SOURCE_NAME)
    options = by_name.get(V1_INFORMATION_PROVENANCE_OPTIONS_SOURCE_NAME)
    if request is None or options is None:
        raise SkatAIInvariantError("Required consumed provenance source is missing.")
    if not exact_v1_json_equal(
        request.document_to_dict(),
        invocation.request.to_dict()["document"],
    ):
        raise SkatAIInvariantError("Verified Root Request provenance source changed.")
    request_document = invocation.request.document
    request_context = _request_context(invocation.request.workflow, request_document)
    expected_request_entries = tuple(
        _request_entry(invocation.request.workflow, request_document, path)
        for path in enumerate_json_leaf_paths(request_document)
    )
    if (
        request.document_role != "consumed_input"
        or request.information_use_context != request_context
        or request.ledger
        != FieldProvenanceLedger(
            status="complete",
            entries=expected_request_entries,
            exemptions=(),
            limitations=(),
        )
    ):
        raise SkatAIInvariantError("Verified Root Request provenance ledger changed.")
    retained_consumed = by_name.get(
        V1_INFORMATION_PROVENANCE_CONSUMED_REQUEST_SOURCE_NAME
    )
    expects_local_consumed = (
        invocation.request.workflow is WorkflowV1.POSITION_ANALYSIS
        and request_document.get("analysis_mode", "live_decision") == "live_decision"
    )
    if not expects_local_consumed and retained_consumed is not None:
        raise SkatAIInvariantError("Unexpected local consumed Request is retained.")
    if expects_local_consumed:
        if retained_consumed is None:
            raise SkatAIInvariantError("Local consumed Request is missing.")
        expected_consumed = request.document_to_dict()
        visible_skat = is_skat_visible_to_local_player(
            player_role=str(expected_consumed["player_role"]),
            declarer_player=expected_consumed.get("declarer_player"),
            skat_visibility=str(expected_consumed.get("skat_visibility", "unknown")),
        )
        expected_consumed["skat"] = (
            list(expected_consumed.get("skat", ())) if visible_skat else []
        )
        expected_consumed_context = _request_context(
            invocation.request.workflow,
            expected_consumed,
        )
        expected_consumed_entries = tuple(
            _request_entry(invocation.request.workflow, expected_consumed, path)
            for path in enumerate_json_leaf_paths(expected_consumed)
        )
        if (
            not exact_v1_json_equal(
                retained_consumed.document_to_dict(),
                expected_consumed,
            )
            or retained_consumed.document_role != "consumed_input"
            or retained_consumed.information_use_context != expected_consumed_context
            or retained_consumed.ledger
            != FieldProvenanceLedger(
                status="complete",
                entries=expected_consumed_entries,
                exemptions=(),
                limitations=(),
            )
        ):
            raise SkatAIInvariantError("Local consumed Request provenance changed.")
    options_document = build_v1_application_options_document(invocation)
    if not exact_v1_json_equal(options.document_to_dict(), options_document):
        raise SkatAIInvariantError("Application-option provenance source changed.")
    expected_options_context = InformationUseContext(
        workflow=invocation.request.workflow.value,
        stage="engine_internal",
        perspective_player_id=None,
        perspective_side=None,
        decision_index=None,
        event_index=None,
    )
    expected_options_entries = tuple(
        _options_entry(invocation, path)
        for path in enumerate_json_leaf_paths(options_document)
    )
    if (
        options.document_role != "consumed_input"
        or options.information_use_context != expected_options_context
        or options.ledger
        != FieldProvenanceLedger(
            status="complete",
            entries=expected_options_entries,
            exemptions=(),
            limitations=(),
        )
    ):
        raise SkatAIInvariantError("Application-option provenance ledger changed.")
    external = invocation.external_documents.opponent_statistics_to_dict()
    retained_external = by_name.get(V1_INFORMATION_PROVENANCE_EXTERNAL_SOURCE_NAME)
    if external is None and retained_external is not None:
        raise SkatAIInvariantError("Unexpected external provenance source is retained.")
    if external is not None and (
        retained_external is None
        or not exact_v1_json_equal(retained_external.document_to_dict(), external)
    ):
        raise SkatAIInvariantError("Injected external provenance source changed.")
    if retained_external is not None:
        expected_external_context = InformationUseContext(
            workflow=invocation.request.workflow.value,
            stage="engine_internal",
            perspective_player_id=None,
            perspective_side=None,
            decision_index=None,
            event_index=None,
        )
        expected_external_entries = tuple(
            _entry(
                path,
                origin="external_source",
                visibility="engine_private",
                available_from="request_start",
                derivation="validated",
            )
            for path in enumerate_json_leaf_paths(external)
        )
        if (
            retained_external.document_role != "consumed_input"
            or retained_external.information_use_context != expected_external_context
            or retained_external.ledger
            != FieldProvenanceLedger(
                status="complete",
                entries=expected_external_entries,
                exemptions=(),
                limitations=(),
            )
        ):
            raise SkatAIInvariantError("Injected external provenance ledger changed.")
    expected_bindings = tuple(
        sorted(
            _build_bindings(
                invocation,
                request_document,
                options_document,
                external,
            ),
            key=lambda item: (item.reference_type, item.reference_id),
        )
    )
    bindings_match = len(sources.bindings) == len(expected_bindings) and all(
        current.workflow is expected.workflow
        and current.reference_type == expected.reference_type
        and current.reference_id == expected.reference_id
        and current.attachment_name == expected.attachment_name
        and current.visibility == expected.visibility
        and exact_v1_json_equal(current.document, expected.document)
        for current, expected in zip(sources.bindings, expected_bindings, strict=True)
    )
    if not bindings_match:
        raise SkatAIInvariantError(
            "Consumed provenance source binding changed from the exact invocation."
        )


def source_binding_map(
    sources: V1InformationProvenanceSources,
) -> dict[tuple[str, str], V1InformationProvenanceSourceBinding]:
    """Returns a fresh lookup over the immutable invocation-local bindings."""
    return {
        (binding.reference_type, binding.reference_id): binding
        for binding in sources.bindings
    }
