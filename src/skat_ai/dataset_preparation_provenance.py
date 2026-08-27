from __future__ import annotations

from collections.abc import Mapping

from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceSourceReference,
    build_json_pointer,
)
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.retrospective_review_provenance import (
    _entry,
    _reference,
    build_complete_provenance_attachment,
)
from skat_ai.training_dataset_preparation import (
    DatasetPreparationSourceFact,
    TrainingDatasetPreparationRequest,
    build_serializable_dataset_preparation_source_fact,
    build_serializable_training_dataset_preparation_request,
)
from skat_ai.training_dataset_preparation_workflow import TrainingDatasetPreparationResult

DATASET_PREPARATION_PROVENANCE_VERSION = 1

_KNOWN_ASSIGNMENT_FIELDS = {
    "record_id",
    "historical_game_id",
    "played_at",
    "player_ids",
}
_UNSEEN_ASSIGNMENT_FIELDS = {
    "record_id",
    "historical_game_id",
    "player_ids",
}
_DECLARATION_DEFAULT_FIELDS = frozenset({
    "hand_game",
    "ouvert",
    "schneider_announced",
    "schwarz_announced",
})


def _context() -> InformationUseContext:
    return InformationUseContext(
        workflow="training_dataset_preparation",
        stage="offline_review",
        perspective_player_id=None,
        perspective_side=None,
        decision_index=None,
        event_index=None,
    )


def _source_fact(
    request: TrainingDatasetPreparationRequest,
    source_index: int,
) -> DatasetPreparationSourceFact:
    record = request.records[source_index]
    provenance = record.provenance
    source_identity = (
        (
            provenance.source_type,
            provenance.source_name,
            provenance.source_record_id,
        )
        if provenance.source_record_id is not None
        else None
    )
    sample_count = sum(len(trick.plays) for trick in record.historical_game.tricks)
    return DatasetPreparationSourceFact(
        source_index=source_index,
        record_id=record.record_id,
        historical_game_id=record.historical_game.game_id,
        source_identity=source_identity,
        played_at=record.historical_game.played_at,
        player_ids=tuple(sorted(player.player_id for player in record.historical_game.players)),
        sample_count=sample_count,
        zero_sample=sample_count == 0,
    )


def _source_reference(source_index: int) -> FieldProvenanceSourceReference:
    return _reference("request", f"dataset_preparation_source/{source_index}")


def _offline_entry(
    path: str,
    *,
    origin: str,
    derivation: str,
    references: tuple[FieldProvenanceSourceReference, ...],
    dependencies: tuple[str, ...] = (),
) -> FieldProvenanceEntry:
    return _entry(
        path,
        origin=origin,
        visibility="post_game_only",
        available_from="offline_review",
        derivation=derivation,
        decision_index=None,
        perspective_player_id=None,
        source_references=references,
        dependency_paths=dependencies,
    )


def _input_attachment(
    request: TrainingDatasetPreparationRequest,
) -> ApplicationProvenanceAttachment:
    document = build_serializable_training_dataset_preparation_request(request)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        inferred_matadors = (
            len(tokens) >= 5
            and tokens[0] == "records"
            and tokens[1].isdecimal()
            and tokens[-3:] == ("historical_game", "declaration", "matadors")
        )
        normalized_declaration_default = (
            len(tokens) >= 5
            and tokens[0] == "records"
            and tokens[1].isdecimal()
            and tokens[-2] == "declaration"
            and tokens[-1] in _DECLARATION_DEFAULT_FIELDS
        )
        if inferred_matadors:
            references = (
                _reference(
                    "algorithm",
                    "dataset_preparation_complete_deal_matador_inference_v1",
                ),
            )
            origin = "structural_inference"
            derivation = "exact_aggregate"
        elif normalized_declaration_default:
            references = (
                _reference(
                    "algorithm",
                    "dataset_preparation_declaration_normalization_v1",
                ),
            )
            origin = "rule_derived"
            derivation = "deterministic_rule"
        elif len(tokens) >= 2 and tokens[0] == "records" and tokens[1].isdecimal():
            references = (_source_reference(int(tokens[1])),)
            origin = "external_source"
            derivation = "validated"
        else:
            references = (_reference("request", "training_dataset_preparation_input"),)
            origin = "validated_copy"
            derivation = "validated"
        return _offline_entry(
            path,
            origin=origin,
            derivation=derivation,
            references=references,
        )

    return build_complete_provenance_attachment(
        name="dataset_preparation/input",
        document_role="consumed_input",
        document=document,
        information_use_context=_context(),
        entry_builder=build,
    )


def _source_fact_attachment(
    request: TrainingDatasetPreparationRequest,
    source_index: int,
) -> ApplicationProvenanceAttachment:
    document = build_serializable_dataset_preparation_source_fact(
        _source_fact(request, source_index)
    )
    record = request.records[source_index]

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        source_path = {
            ("record_id",): "/record_id",
            ("historical_game_id",): "/historical_game/game_id",
            ("source_identity", "source_type"): "/provenance/source_type",
            ("source_identity", "source_name"): "/provenance/source_name",
            ("source_identity", "source_record_id"): (
                "/provenance/source_record_id"
            ),
        }.get(tokens)
        if len(tokens) == 2 and tokens[0] == "player_ids" and tokens[1].isdecimal():
            player_id = document["player_ids"][int(tokens[1])]
            source_player_index = next(
                index
                for index, player in enumerate(record.historical_game.players)
                if player.player_id == player_id
            )
            source_path = build_json_pointer(
                ("historical_game", "players", str(source_player_index), "player_id")
            )
        direct = source_path is not None
        diagnostic = bool(
            tokens and tokens[0] in {"source_index", "sample_count", "zero_sample"}
        )
        return _offline_entry(
            path,
            origin=(
                "historical_aggregation"
                if diagnostic
                else "validated_copy"
                if direct
                else "rule_derived"
            ),
            derivation=(
                "exact_aggregate"
                if diagnostic
                else "validated"
                if direct
                else "deterministic_rule"
            ),
            references=(
                FieldProvenanceSourceReference(
                    reference_type="request",
                    reference_id=f"dataset_preparation_source/{source_index}",
                    field_path=source_path,
                    visibility="public",
                ),
            ),
        )

    return build_complete_provenance_attachment(
        name=f"dataset_preparation/source/{source_index}",
        document_role="consumed_input",
        document=document,
        information_use_context=_context(),
        entry_builder=build,
    )


def _assignment_references(
    request: TrainingDatasetPreparationRequest,
    record_id: str,
) -> tuple[FieldProvenanceSourceReference, ...]:
    source_index = next(
        index for index, record in enumerate(request.records) if record.record_id == record_id
    )
    allowed_fields = (
        _KNOWN_ASSIGNMENT_FIELDS if request.mode == "known_opponent" else _UNSEEN_ASSIGNMENT_FIELDS
    )
    references = [
        _reference(
            "algorithm",
            "temporal_known_opponent_v1"
            if request.mode == "known_opponent"
            else "component_balanced_unseen_player_v1",
        ),
        _reference(
            "request",
            "source_identity_fingerprint"
            if request.mode == "known_opponent"
            else "unseen_player_selector_identity",
        ),
        _reference("request", "dataset_preparation_partition_weights"),
        _reference("request", "dataset_preparation_base_seed"),
    ]
    if allowed_fields:
        references.append(_source_reference(source_index))
    return tuple(references)


def _plan_attachment(
    request: TrainingDatasetPreparationRequest,
    document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    assignments = document["assignments"]
    assert isinstance(assignments, list)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if len(tokens) >= 2 and tokens[0] == "assignments":
            assignment = assignments[int(tokens[1])]
            assert isinstance(assignment, Mapping)
            references = _assignment_references(request, str(assignment["record_id"]))
            return _offline_entry(
                path,
                origin="dataset_assignment",
                derivation="deterministic_rule",
                references=references,
            )
        if tokens and tokens[0] in {
            "partition_summaries",
            "temporal_audit",
            "partition_audit",
        }:
            return _offline_entry(
                path,
                origin="historical_aggregation",
                derivation="exact_aggregate",
                references=(_reference("dataset_plan", "dataset_partition_plan"),),
            )
        source_path = None
        if tokens == ("mode",):
            source_path = "/mode"
        elif tokens == ("base_random_seed",):
            source_path = "/base_random_seed"
        elif tokens[:1] == ("requested_partition_weights",):
            source_path = build_json_pointer(("partition_weights", *tokens[1:]))
        if source_path is not None:
            return _offline_entry(
                path,
                origin="validated_copy",
                derivation="validated",
                references=(
                    FieldProvenanceSourceReference(
                        reference_type="request",
                        reference_id="training_dataset_preparation_input",
                        field_path=source_path,
                        visibility="public",
                    ),
                ),
            )
        algorithm = (
            "temporal_known_opponent_v1"
            if request.mode == "known_opponent"
            else "component_balanced_unseen_player_v1"
        )
        return _offline_entry(
            path,
            origin="historical_aggregation",
            derivation="exact_aggregate",
            references=(
                _reference("algorithm", algorithm),
                FieldProvenanceSourceReference(
                    reference_type="request",
                    reference_id="training_dataset_preparation_input",
                    field_path="/mode",
                    visibility="public",
                ),
            ),
        )

    return build_complete_provenance_attachment(
        name="dataset_preparation/plan",
        document_role="result",
        document=document,
        information_use_context=_context(),
        entry_builder=build,
    )


def _materialized_attachment(
    request: TrainingDatasetPreparationRequest,
    document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if (
            len(tokens) == 3
            and tokens[0] == "records"
            and tokens[1].isdecimal()
            and tokens[2] == "partition"
        ):
            source_index = int(tokens[1])
            return _offline_entry(
                path,
                origin="dataset_assignment",
                derivation="deterministic_rule",
                references=(
                    _reference("dataset_plan", "dataset_partition_plan"),
                    _source_reference(source_index),
                ),
            )
        if tokens and tokens[0] in {"schema_version", "partition_policy"}:
            return _offline_entry(
                path,
                origin="rule_derived",
                derivation="deterministic_rule",
                references=(
                    _reference("dataset_plan", "dataset_partition_plan"),
                ),
            )
        if (
            len(tokens) >= 5
            and tokens[0] == "records"
            and tokens[1].isdecimal()
            and tokens[-3:] == ("historical_game", "declaration", "matadors")
        ):
            return _offline_entry(
                path,
                origin="structural_inference",
                derivation="exact_aggregate",
                references=(
                    _reference(
                        "algorithm",
                        "dataset_preparation_complete_deal_matador_inference_v1",
                    ),
                ),
            )
        if (
            len(tokens) >= 5
            and tokens[0] == "records"
            and tokens[1].isdecimal()
            and tokens[-2] == "declaration"
            and tokens[-1] in _DECLARATION_DEFAULT_FIELDS
        ):
            return _offline_entry(
                path,
                origin="rule_derived",
                derivation="deterministic_rule",
                references=(
                    _reference(
                        "algorithm",
                        "dataset_preparation_declaration_normalization_v1",
                    ),
                ),
            )
        if len(tokens) >= 2 and tokens[0] == "records" and tokens[1].isdecimal():
            references = (_source_reference(int(tokens[1])),)
            origin = "validated_copy"
        else:
            references = (_reference("request", "training_dataset_preparation_input"),)
            origin = "validated_copy"
        return _offline_entry(
            path,
            origin=origin,
            derivation="validated",
            references=references,
        )

    return build_complete_provenance_attachment(
        name="dataset_preparation/materialized_dataset",
        document_role="result",
        document=document,
        information_use_context=_context(),
        entry_builder=build,
    )


def _root_attachment(
    result: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if tokens == ("input_file",):
            return _offline_entry(
                path,
                origin="caller_supplied",
                derivation="direct",
                references=(_reference("request", "application_input_reference"),),
            )
        return _offline_entry(
            path,
            origin="historical_aggregation",
            derivation="exact_aggregate",
            references=(_reference("dataset_plan", "dataset_preparation_result"),),
        )

    return build_complete_provenance_attachment(
        name="dataset_preparation_result",
        document_role="result",
        document=result,
        information_use_context=_context(),
        entry_builder=build,
    )


def validate_dataset_preparation_assignment_references(
    mode: str,
    references: tuple[FieldProvenanceSourceReference, ...],
) -> None:
    """Rejects information outside the selected assignment policy."""
    if mode not in {"known_opponent", "unseen_player"}:
        raise ValueError(f"Unsupported Dataset Preparation mode {mode!r}.")
    allowed = _KNOWN_ASSIGNMENT_FIELDS if mode == "known_opponent" else _UNSEEN_ASSIGNMENT_FIELDS
    for reference in references:
        if reference.reference_type != "external_record" or reference.field_path is None:
            continue
        field_name = reference.field_path.removeprefix("/").split("/", 1)[0]
        if field_name not in allowed:
            raise ValueError(
                f"{mode} assignment provenance cannot use source field {field_name!r}."
            )


class DatasetPreparationProvenanceCollector:
    """Builds preparation provenance from the retained request and result."""

    def __init__(self) -> None:
        self._request: TrainingDatasetPreparationRequest | None = None
        self._result: TrainingDatasetPreparationResult | None = None

    def capture(
        self,
        request: TrainingDatasetPreparationRequest,
        result: TrainingDatasetPreparationResult,
    ) -> None:
        self._request = request
        self._result = result

    def build_bundle(
        self,
        root_result: Mapping[str, object],
    ) -> ApplicationProvenanceBundle:
        if self._request is None or self._result is None:
            raise ValueError("Dataset Preparation provenance did not capture its values.")
        summary = root_result["training_dataset_preparation_summary"]
        assert isinstance(summary, Mapping)
        plan = summary["plan"]
        assert isinstance(plan, Mapping)
        attachments: list[ApplicationProvenanceAttachment] = [
            _input_attachment(self._request),
            *(
                _source_fact_attachment(self._request, source_index)
                for source_index in range(len(self._request.records))
            ),
            _plan_attachment(self._request, plan),
        ]
        materialized = summary["training_dataset_input"]
        if materialized is not None:
            assert isinstance(materialized, Mapping)
            attachments.append(_materialized_attachment(self._request, materialized))
        attachments.append(_root_attachment(root_result))
        bundle = ApplicationProvenanceBundle(
            workflow=WorkflowV1.TRAINING_DATASET_PREPARATION,
            attachments=tuple(attachments),
        )
        for attachment in bundle.attachments:
            if attachment.name != "dataset_preparation/plan":
                continue
            for entry in attachment.ledger.entries:
                if entry.origin == "dataset_assignment":
                    validate_dataset_preparation_assignment_references(
                        self._request.mode,
                        entry.source_references,
                    )
        return bundle
