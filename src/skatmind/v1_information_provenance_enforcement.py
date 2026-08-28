from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace

from skatmind.api.v1.contracts import WorkflowV1
from skatmind.application.contracts import ApplicationInvocation, _freeze_json_object
from skatmind.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceSourceReference,
    build_json_pointer,
    parse_json_pointer,
    resolve_json_pointer,
)
from skatmind.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
)
from skatmind.field_provenance_policy import validate_field_provenance_entry_use
from skatmind.information_view import is_skat_visible_to_local_player
from skatmind.v1_information_provenance_sources import (
    V1_INFORMATION_PROVENANCE_CONSUMED_REQUEST_SOURCE_NAME,
    V1InformationProvenanceSourceBinding,
    V1InformationProvenanceSources,
    exact_v1_json_equal,
    source_binding_map,
    validate_v1_information_provenance_sources,
)

V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION = 1
V1_INFORMATION_PROVENANCE_ENFORCEMENT_STAGES = (
    "loaded_request",
    "validated_consumed_input",
    "retained_stage_linkage",
    "final_serialization",
)
V1_INFORMATION_PROVENANCE_LOADING_POLICY = (
    "exact_verified_request_options_and_external_documents"
)
V1_INFORMATION_PROVENANCE_USE_POLICY = (
    "validate_information_use_context_before_downstream_use"
)
V1_INFORMATION_PROVENANCE_LINKAGE_POLICY = (
    "retained_values_link_to_authorized_loaded_or_retained_sources"
)
V1_INFORMATION_PROVENANCE_EXECUTION_POLICY = (
    "retained_stage_values_without_workflow_rerun"
)
V1_INFORMATION_PROVENANCE_SERIALIZATION_POLICY = (
    "exact_result_and_actual_artifact_reconciliation_before_return"
)
V1_INFORMATION_PROVENANCE_ADVERSARIAL_POLICY = (
    "reject_mutation_coverage_dependency_temporal_and_private_leakage"
)
V1_INFORMATION_PROVENANCE_PUBLIC_POLICY = (
    "preserve_existing_redacted_result_and_actual_artifact_boundary"
)
V1_INFORMATION_PROVENANCE_COMPATIBILITY_POLICY = (
    "no_public_field_version_schema_default_or_output_change"
)

_ALGORITHM_REFERENCE_IDS = frozenset({
    "baseline_opponent_policy",
    "bounded_information_set_policy_search_v1",
    "bounded_search_comparison",
    "bounded_search_immediate",
    "compatible_world_minimax_same_selection_v1",
    "compatible_world_minimax_v1",
    "decision_time_matador_inference",
    "dataset_preparation_complete_deal_matador_inference_v1",
    "dataset_preparation_declaration_normalization_v1",
    "defender_open_play_exact_proof_v1",
    "effective_opponent_policy",
    "exact_evidence_constrained",
    "game_declaration_defaults_v1",
    "historical_assessment",
    "historical_complete_deal_matador_inference_v1",
    "historical_decision_analysis",
    "historical_effective_opponent_policy",
    "historical_game_result_v1",
    "historical_game_validation_v1",
    "historical_immediate_review",
    "historical_information_set_replay_coaching_v1",
    "historical_legal_replay_v1",
    "historical_profile_application",
    "historical_remaining_card_reconstruction_v1",
    "historical_replay_coaching_v1",
    "historical_search_review",
    "immediate_expected_value",
    "information_set_replay_coaching_assessment_v1",
    "live_position_analysis",
    "multi_step_public_state",
    "multi_step_simulation",
    "open_throw_jack_exclusion_v1",
    "opponent_profile_normalization_v1",
    "party_wide_all_remaining_tricks_exact_and_or_v1",
    "party_wide_claim_adjudication_v1",
    "party_wide_claim_exact_state_v1",
    "perfect_information_minimax_v1",
    "position_matador_inference_v1",
    "post_game_review",
    "post_game_review_v1",
    "private_ownership_matador_evidence_v1",
    "recommendation_method_routing",
    "replay_coaching_assessment",
    "replay_coaching_guidance_v1",
    "replay_coaching_prioritization_v1",
    "retrospective_position_analysis",
    "retrospective_search_comparison",
    "search_vs_immediate_comparison",
    "temporal_known_opponent_v1",
    "component_balanced_unseen_player_v1",
})
_RULE_REFERENCE_IDS = frozenset({
    "authorized_public_hand_constraints",
    "canonical_declaration_dependencies_v1",
    "card_point_rules",
    "claim_boundary.decision.party_wide_all_remaining_tricks_claim",
    "game_result_rules_v1",
    "game_value_rules_v1",
    "fixed_three_player_historical_list_normalization_v1",
    "historical_legal_replay_v1",
    "historical_game_result_v1",
    "historical_raw_game_result_v1",
    "historical_tactical_motif_review_v1",
    "information_set_budget_profile_conversion_v1",
    "information_set_budget_to_same_selection_pimc_v1",
    "information_set_search_comparison_v1",
    "information_set_search_evaluation_defaults_v1",
    "information_set_search_multi_step_decision_v1",
    "legal_card_rules",
    "live_information_policy",
    "overbid_rules_v1",
    "performance_rating_v1",
    "settlement_normative_matrix_v1",
    "skwo_6.3.1_performance",
    "skwo_6.3.1_standings",
    "training_target_actual_card_played_v1",
    "trick_winner_and_point_rules",
})
_AGGREGATE_REFERENCE_IDS = frozenset({
    "historical_immediate_summary",
    "final_outcome_context",
    "historical_information_set_search_review_summary",
    "historical_opponent_statistics",
    "historical_review_summary",
    "historical_search_summary",
    "historical_snapshot_summary",
    "historical_tactical_motif_review_summary",
    "historical_list_comparison",
    "information_set_controlled_policy_decision_count_v1",
    "information_set_search_evaluation_summary",
    "opponent_statistics_summary",
    "party_wide_claim_complete_world_evidence_v1",
    "retained_historical_decision_snapshots",
    "retained_historical_information_set_search_review",
})
_RETROSPECTIVE_REFERENCE_IDS = frozenset({
    "flat_actual_card",
    "historical_actual_card",
})
_DATASET_PLAN_IDS = frozenset({"dataset_partition_plan", "dataset_preparation_result"})
_HISTORICAL_ONLY_ALGORITHM_IDS = frozenset({
    "historical_assessment",
    "historical_complete_deal_matador_inference_v1",
    "historical_decision_analysis",
    "historical_effective_opponent_policy",
    "historical_game_result_v1",
    "historical_game_validation_v1",
    "historical_immediate_review",
    "historical_information_set_replay_coaching_v1",
    "historical_legal_replay_v1",
    "historical_profile_application",
    "historical_remaining_card_reconstruction_v1",
    "historical_replay_coaching_v1",
    "historical_search_review",
    "information_set_replay_coaching_assessment_v1",
    "party_wide_all_remaining_tricks_exact_and_or_v1",
    "party_wide_claim_adjudication_v1",
    "party_wide_claim_exact_state_v1",
    "replay_coaching_assessment",
    "replay_coaching_guidance_v1",
    "replay_coaching_prioritization_v1",
})
_POSITION_ONLY_ALGORITHM_IDS = frozenset({
    "live_position_analysis",
    "multi_step_public_state",
    "multi_step_simulation",
    "position_matador_inference_v1",
    "private_ownership_matador_evidence_v1",
})
_PREPARATION_ALGORITHM_IDS = frozenset({
    "component_balanced_unseen_player_v1",
    "dataset_preparation_complete_deal_matador_inference_v1",
    "dataset_preparation_declaration_normalization_v1",
    "temporal_known_opponent_v1",
})
_HISTORICAL_ONLY_RULE_IDS = frozenset({
    "claim_boundary.decision.party_wide_all_remaining_tricks_claim",
    "historical_legal_replay_v1",
    "historical_game_result_v1",
    "historical_raw_game_result_v1",
    "historical_tactical_motif_review_v1",
})
_HISTORICAL_ONLY_AGGREGATE_IDS = frozenset({
    "historical_immediate_summary",
    "final_outcome_context",
    "historical_information_set_search_review_summary",
    "historical_review_summary",
    "historical_search_summary",
    "historical_snapshot_summary",
    "historical_tactical_motif_review_summary",
    "party_wide_claim_complete_world_evidence_v1",
    "retained_historical_decision_snapshots",
    "retained_historical_information_set_search_review",
})
_ENGINE_PRIVATE_REFERENCE_KEYS = frozenset({
    ("aggregate", "information_set_controlled_policy_decision_count_v1"),
    ("aggregate", "party_wide_claim_complete_world_evidence_v1"),
    ("algorithm", "defender_open_play_exact_proof_v1"),
    ("algorithm", "open_throw_jack_exclusion_v1"),
    ("algorithm", "party_wide_claim_exact_state_v1"),
    ("algorithm", "private_ownership_matador_evidence_v1"),
})
_TRAINING_OPERATIONS = frozenset({
    "summary",
    "partition_audit",
    "rolling_opponent_policy_evaluation",
    "bounded_search_evaluation",
    "information_set_search_evaluation",
    "historical_opponent_statistics_aggregation",
})
_STRUCTURED_RULE_PREFIXES = (
    "structured_shortening.",
    "historical.terminal.",
    "historical.continuation.",
)
_INDEXED_REFERENCE = re.compile(r"^[a-z_]+(?:/[a-z_]+)*/\d+(?:/\d+)?$")


def validate_v1_information_provenance_enforcement_version(value: object) -> None:
    """Requires the exact strict internal lifecycle version."""
    if (
        type(value) is not int
        or value != V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION
    ):
        raise SkatMindValidationError(
            "information provenance enforcement version must equal 1.",
            path="enforcement_version",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class V1InformationProvenanceRetainedLinkage:
    """Deterministic evidence that retained attachments were checked once."""

    workflow: WorkflowV1
    linked_attachment_names: tuple[str, ...]
    trusted_checkpoint_documents: tuple[
        tuple[str, Mapping[str, object]], ...
    ] = ()
    retained_stage_linkage_count: int = 1
    enforcement_version: int = V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION

    def __post_init__(self) -> None:
        validate_v1_information_provenance_enforcement_version(
            self.enforcement_version
        )
        if not isinstance(self.workflow, WorkflowV1):
            raise SkatMindValidationError("workflow must be a WorkflowV1.", path="workflow")
        names = tuple(self.linked_attachment_names)
        if any(not isinstance(name, str) or not name for name in names):
            raise SkatMindValidationError(
                "linked_attachment_names must contain non-empty strings.",
                path="linked_attachment_names",
            )
        if len(names) != len(set(names)):
            raise SkatMindValidationError(
                "linked_attachment_names must be unique.",
                path="linked_attachment_names",
            )
        checkpoints = tuple(self.trusted_checkpoint_documents)
        checkpoint_names = tuple(name for name, _document in checkpoints)
        if (
            any(not isinstance(name, str) or not name for name in checkpoint_names)
            or len(checkpoint_names) != len(set(checkpoint_names))
        ):
            raise SkatMindValidationError(
                "trusted checkpoint names must be unique non-empty strings.",
                path="trusted_checkpoint_documents",
            )
        if (
            type(self.retained_stage_linkage_count) is not int
            or self.retained_stage_linkage_count != 1
        ):
            raise SkatMindValidationError(
                "retained_stage_linkage_count must equal 1.",
                path="retained_stage_linkage_count",
            )
        object.__setattr__(self, "linked_attachment_names", names)
        object.__setattr__(
            self,
            "trusted_checkpoint_documents",
            tuple(
                (name, _freeze_json_object(document, path="checkpoint_document"))
                for name, document in checkpoints
            ),
        )


def _invariant(message: str) -> SkatMindInvariantError:
    return SkatMindInvariantError(message)


def _require_complete_attachment(attachment: ApplicationProvenanceAttachment) -> None:
    summary = build_field_provenance_coverage_summary(
        attachment.document,
        attachment.ledger,
    )
    if (
        attachment.ledger.status != "complete"
        or attachment.ledger.exemptions
        and any(item.reason == "legacy_untracked" for item in attachment.ledger.exemptions)
        or not summary.all_paths_accounted_for
        or not summary.provenance_complete
        or summary.uncovered_paths
        or summary.orphaned_entry_paths
        or summary.orphaned_exemption_paths
        or summary.overlapping_paths
        or summary != attachment.coverage_summary
    ):
        raise _invariant("V1 provenance attachment is not complete for its document.")


def enforce_v1_information_provenance_before_analysis(
    invocation: ApplicationInvocation,
    sources: V1InformationProvenanceSources,
) -> None:
    """Validates every exact consumed-source entry before handler dispatch."""
    if not isinstance(invocation, ApplicationInvocation):
        raise SkatMindValidationError(
            "invocation must be an ApplicationInvocation.",
            path="invocation",
        )
    if not isinstance(sources, V1InformationProvenanceSources):
        raise SkatMindValidationError(
            "sources must be V1InformationProvenanceSources.",
            path="sources",
        )
    validate_v1_information_provenance_sources(invocation, sources)
    for attachment in sources.attachments:
        _require_complete_attachment(attachment)
        if attachment.information_use_context.workflow != sources.workflow.value:
            raise _invariant("Consumed provenance source has the wrong workflow.")
        if attachment.name == V1_INFORMATION_PROVENANCE_CONSUMED_REQUEST_SOURCE_NAME:
            skat = attachment.document.get("skat")
            if (
                isinstance(skat, (list, tuple))
                and skat
                and not is_skat_visible_to_local_player(
                    player_role=str(attachment.document.get("player_role")),
                    declarer_player=attachment.document.get("declarer_player"),
                    skat_visibility=str(
                        attachment.document.get("skat_visibility", "unknown")
                    ),
                )
            ):
                raise _invariant(
                    "Live consumed Request retains Skat hidden from the local actor."
                )
        for entry in attachment.ledger.entries:
            if (
                invocation.request.workflow is WorkflowV1.POSITION_ANALYSIS
                and attachment.name == "v1_source/request"
                and entry.field_path.startswith("/skat/")
                and entry.available_from == "game_end"
            ):
                continue
            validate_field_provenance_entry_use(
                entry,
                attachment.information_use_context,
            )


def _collect_values(document: object, key: str) -> frozenset[str]:
    values: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            candidate = value.get(key)
            if isinstance(candidate, str):
                values.add(candidate)
            for item in value.values():
                visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(document)
    return frozenset(values)


def _reference_is_authorized(
    reference: FieldProvenanceSourceReference,
    *,
    invocation: ApplicationInvocation,
    bindings: Mapping[tuple[str, str], object],
) -> bool:
    key = (reference.reference_type, reference.reference_id)
    if key in bindings:
        return True
    reference_id = reference.reference_id
    request_document = invocation.request.document
    workflow = invocation.request.workflow
    if reference.reference_type == "algorithm":
        if reference_id == "opponent_profile_normalization_v1":
            return workflow is WorkflowV1.OPPONENT_STATISTICS
        if reference_id.startswith("training_dataset_"):
            operation = (
                invocation.options.training_dataset.operation
                if invocation.options.training_dataset is not None
                else None
            )
            return (
                workflow is WorkflowV1.TRAINING_DATASET
                and reference_id == f"training_dataset_{operation}"
            )
        if reference_id not in _ALGORITHM_REFERENCE_IDS:
            return False
        if reference_id in _HISTORICAL_ONLY_ALGORITHM_IDS:
            return workflow is WorkflowV1.HISTORICAL_GAME or (
                reference_id == "historical_effective_opponent_policy"
                and workflow is WorkflowV1.TRAINING_DATASET
                and invocation.options.training_dataset is not None
                and invocation.options.training_dataset.operation
                == "information_set_search_evaluation"
            )
        if reference_id in _POSITION_ONLY_ALGORITHM_IDS:
            return workflow is WorkflowV1.POSITION_ANALYSIS
        if reference_id in _PREPARATION_ALGORITHM_IDS:
            return workflow is WorkflowV1.TRAINING_DATASET_PREPARATION
        return workflow in {
            WorkflowV1.POSITION_ANALYSIS,
            WorkflowV1.HISTORICAL_GAME,
            WorkflowV1.TRAINING_DATASET,
        }
    if reference.reference_type == "rule_contract":
        if reference_id.startswith(_STRUCTURED_RULE_PREFIXES):
            return workflow in {
                WorkflowV1.POSITION_ANALYSIS,
                WorkflowV1.HISTORICAL_GAME,
            }
        if reference_id not in _RULE_REFERENCE_IDS:
            return False
        if reference_id in _HISTORICAL_ONLY_RULE_IDS:
            return workflow is WorkflowV1.HISTORICAL_GAME
        if reference_id == "information_set_search_evaluation_defaults_v1":
            return workflow is WorkflowV1.TRAINING_DATASET
        return workflow in {
            WorkflowV1.POSITION_ANALYSIS,
            WorkflowV1.HISTORICAL_GAME,
            WorkflowV1.TRAINING_DATASET,
            WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
            WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
        }
    if reference.reference_type == "aggregate":
        list_ids = _collect_values(request_document, "list_id")
        if reference_id in _HISTORICAL_ONLY_AGGREGATE_IDS:
            return workflow is WorkflowV1.HISTORICAL_GAME
        if reference_id == "historical_opponent_statistics":
            return (
                workflow is WorkflowV1.TRAINING_DATASET
                and invocation.options.training_dataset is not None
                and invocation.options.training_dataset.operation
                == "historical_opponent_statistics_aggregation"
            )
        if reference_id == "opponent_statistics_summary":
            return workflow is WorkflowV1.OPPONENT_STATISTICS
        if reference_id == "historical_list_comparison":
            return workflow is WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON
        if reference_id == "information_set_search_evaluation_summary":
            return (
                workflow is WorkflowV1.TRAINING_DATASET
                and invocation.options.training_dataset is not None
                and invocation.options.training_dataset.operation
                == "information_set_search_evaluation"
            )
        if reference_id == "information_set_controlled_policy_decision_count_v1":
            return workflow in {
                WorkflowV1.POSITION_ANALYSIS,
                WorkflowV1.HISTORICAL_GAME,
                WorkflowV1.TRAINING_DATASET,
            }
        if reference_id.startswith("training_feature/"):
            return (
                workflow is WorkflowV1.TRAINING_DATASET
                and invocation.options.training_dataset is not None
                and invocation.options.training_dataset.operation == "summary"
                and _INDEXED_REFERENCE.fullmatch(reference_id) is not None
            )
        if reference_id.startswith("training_dataset/"):
            parts = reference_id.split("/")
            return (
                workflow is WorkflowV1.TRAINING_DATASET
                and len(parts) >= 3
                and invocation.options.training_dataset is not None
                and parts[1] == invocation.options.training_dataset.operation
            )
        if reference_id.startswith("historical_list/"):
            parts = reference_id.split("/")
            return (
                workflow
                in {
                    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
                    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
                }
                and len(parts) == 3
                and parts[1] in list_ids
                and parts[2] == "aggregation"
            )
        return reference_id in _AGGREGATE_REFERENCE_IDS and workflow in {
            WorkflowV1.POSITION_ANALYSIS,
            WorkflowV1.HISTORICAL_GAME,
            WorkflowV1.TRAINING_DATASET,
        }
    if reference.reference_type == "historical_game":
        return (
            reference_id in _collect_values(request_document, "game_id")
        )
    if reference.reference_type == "historical_event":
        if workflow is not WorkflowV1.HISTORICAL_GAME:
            return False
        for game_id in _collect_values(request_document, "game_id"):
            if reference_id == f"{game_id}:terminal":
                return True
            prefix = f"{game_id}:event:"
            if reference_id.startswith(prefix):
                suffix = reference_id.removeprefix(prefix)
                return suffix.isdecimal() and int(suffix) < len(
                    request_document.get("historical_game_input", {}).get(
                        "game_events",
                        (),
                    )
                )
        return False
    if reference.reference_type == "external_record":
        return (
            workflow
            in {
                WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
                WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
            }
            and reference_id.startswith("historical_list/")
            and any(
                reference_id == f"historical_list/{list_id}"
                or reference_id.startswith(f"historical_list/{list_id}/entry/")
                for list_id in _collect_values(request_document, "list_id")
            )
        )
    if reference.reference_type == "retrospective_observation":
        if workflow is WorkflowV1.POSITION_ANALYSIS:
            return reference_id == "flat_actual_card"
        if workflow is WorkflowV1.HISTORICAL_GAME:
            if reference_id == "historical_actual_card":
                return True
        elif workflow is WorkflowV1.TRAINING_DATASET:
            if reference_id.startswith("training_target/"):
                return _INDEXED_REFERENCE.fullmatch(reference_id) is not None
        else:
            return False
        return any(
            reference_id.startswith(f"{game_id}/")
            and reference_id.removeprefix(f"{game_id}/").isdecimal()
            for game_id in _collect_values(request_document, "game_id")
        )
    if reference.reference_type == "dataset_plan":
        return (
            workflow is WorkflowV1.TRAINING_DATASET_PREPARATION
            and reference_id in _DATASET_PLAN_IDS
        )
    return False


def _source_document_for_reference(
    reference: FieldProvenanceSourceReference,
    *,
    bindings: Mapping[tuple[str, str], object],
) -> Mapping[str, object] | None:
    binding = bindings.get((reference.reference_type, reference.reference_id))
    if binding is not None:
        return binding.document
    if (
        reference.reference_type == "algorithm"
        and reference.reference_id == "game_declaration_defaults_v1"
    ):
        return {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "matadors": None,
            "bid_value": None,
        }
    if (
        reference.reference_type == "rule_contract"
        and reference.reference_id == "information_set_search_evaluation_defaults_v1"
    ):
        from skatmind.information_set_search_evaluation import (
            INFORMATION_SET_SEARCH_EVALUATION_IMMEDIATE_BASE_RANDOM_SEED,
        )
        from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

        return {
            "immediate_sample_count": DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
            "immediate_base_random_seed": (
                INFORMATION_SET_SEARCH_EVALUATION_IMMEDIATE_BASE_RANDOM_SEED
            ),
        }
    return None


_VISIBILITY_RESTRICTIONS = {
    "public": frozenset({
        "public",
        "local_private",
        "declarer_private",
        "defender_private",
        "post_game_only",
        "engine_private",
    }),
    "local_private": frozenset({
        "local_private",
        "post_game_only",
        "engine_private",
    }),
    "declarer_private": frozenset({
        "declarer_private",
        "post_game_only",
        "engine_private",
    }),
    "defender_private": frozenset({
        "defender_private",
        "post_game_only",
        "engine_private",
    }),
    "post_game_only": frozenset({"post_game_only", "engine_private"}),
    "engine_private": frozenset({"engine_private"}),
}
_AVAILABILITY_RANKS = {
    "request_start": 0,
    "current_decision": 1,
    "after_public_event": 1,
    "after_actual_play": 2,
    "game_end": 3,
    "offline_review": 4,
}
_PATHLESS_SCOPE_ORIGINS = frozenset({
    "caller_supplied",
    "defaulted",
    "public_game_event",
    "retrospective_attachment",
    "validated_copy",
})
_PATHLESS_VALUE_ORIGINS = frozenset({
    *_PATHLESS_SCOPE_ORIGINS,
    "external_source",
})
_EXACT_VALUE_ORIGINS = frozenset({*_PATHLESS_VALUE_ORIGINS, "historical_replay"})
_BOUND_SOURCE_REFERENCE_TYPES = frozenset({
    "external_record",
    "historical_event",
    "historical_game",
    "request",
    "retrospective_observation",
})
_FAIL_CLOSED_PATH_ORIGINS = frozenset({
    "caller_supplied",
    "historical_replay",
    "public_game_event",
    "retrospective_attachment",
    "validated_copy",
})


def _binding_prefixes(
    binding: V1InformationProvenanceSourceBinding,
    attachment: ApplicationProvenanceAttachment,
) -> tuple[tuple[str, ...], ...]:
    prefixes: list[tuple[str, ...]] = []

    def visit(value: object, tokens: tuple[str, ...]) -> None:
        if isinstance(value, Mapping) and exact_v1_json_equal(value, binding.document):
            prefixes.append(tokens)
            return
        if isinstance(value, Mapping):
            for key, child in value.items():
                visit(child, (*tokens, key))
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                visit(child, (*tokens, str(index)))

    visit(attachment.document, ())
    return tuple(prefixes)


def _source_entries_for_reference(
    reference: FieldProvenanceSourceReference,
    *,
    entry: FieldProvenanceEntry,
    binding: V1InformationProvenanceSourceBinding | None,
    sources: V1InformationProvenanceSources,
) -> tuple[FieldProvenanceEntry, ...]:
    if binding is None:
        return ()
    relative_path = reference.field_path or (
        _pathless_source_path(binding, entry)
    )
    if relative_path is None:
        return ()
    source_attachment = next(
        (
            attachment
            for attachment in sources.attachments
            if attachment.name == binding.attachment_name
        ),
        None,
    )
    if source_attachment is None:
        raise _invariant("Retained provenance source attachment is missing.")
    relative_tokens = parse_json_pointer(relative_path)
    paths = tuple(
        build_json_pointer((*prefix, *relative_tokens))
        for prefix in _binding_prefixes(binding, source_attachment)
    )
    return tuple(
        source_entry
        for source_entry in source_attachment.ledger.entries
        if any(
            source_entry.field_path == path
            or path != "" and source_entry.field_path.startswith(f"{path}/")
            for path in paths
        )
    )


def _pathless_source_path(
    binding: V1InformationProvenanceSourceBinding,
    entry: FieldProvenanceEntry,
) -> str | None:
    tokens = parse_json_pointer(entry.field_path)
    if not tokens:
        return ""
    for start in range(len(tokens)):
        candidate = build_json_pointer(tokens[start:])
        try:
            resolve_json_pointer(binding.document, candidate)
        except SkatMindValidationError:
            continue
        return candidate
    return None


def _retrospective_observation_source_path(
    reference: FieldProvenanceSourceReference,
    entry: FieldProvenanceEntry,
    binding: V1InformationProvenanceSourceBinding,
) -> str | None:
    if reference.reference_id == "flat_actual_card":
        return "/actual_card_played"
    if reference.reference_id == "historical_actual_card":
        decision_index = entry.available_from_decision_index
    else:
        index_token = reference.reference_id.rsplit("/", 1)[-1]
        decision_index = int(index_token) if index_token.isdecimal() else None
    if decision_index is None:
        return None
    tricks = binding.document.get("tricks", ())
    current_index = 1
    if not isinstance(tricks, (list, tuple)):
        return None
    for trick_index, trick in enumerate(tricks):
        plays = trick.get("plays", ()) if isinstance(trick, Mapping) else ()
        if not isinstance(plays, (list, tuple)):
            continue
        for play_index, _play in enumerate(plays):
            if current_index == decision_index:
                return build_json_pointer(
                    ("tricks", str(trick_index), "plays", str(play_index), "card")
                )
            current_index += 1
    return None


def _canonical_reordered_source_path(
    source_document: Mapping[str, object],
    source_path: str,
    attachment: ApplicationProvenanceAttachment,
    entry: FieldProvenanceEntry,
) -> str:
    source_tokens = parse_json_pointer(source_path)
    entry_tokens = parse_json_pointer(entry.field_path)
    if len(source_tokens) > len(entry_tokens) or tuple(
        entry_tokens[-len(source_tokens):]
    ) != source_tokens:
        return source_path
    try:
        source_value = resolve_json_pointer(source_document, source_path)
        retained_value = resolve_json_pointer(attachment.document, entry.field_path)
    except SkatMindValidationError:
        return source_path
    if exact_v1_json_equal(source_value, retained_value):
        return source_path
    entry_prefix = entry_tokens[: len(entry_tokens) - len(source_tokens)]
    for position in range(len(source_tokens) - 1, -1, -1):
        index_token = source_tokens[position]
        if not index_token.isdecimal():
            continue
        source_list_path = build_json_pointer(source_tokens[:position])
        retained_list_path = build_json_pointer(
            (*entry_prefix, *source_tokens[:position])
        )
        try:
            source_list = resolve_json_pointer(source_document, source_list_path)
            retained_list = resolve_json_pointer(
                attachment.document,
                retained_list_path,
            )
        except SkatMindValidationError:
            continue
        output_index = int(index_token)
        if (
            not isinstance(source_list, (list, tuple))
            or not isinstance(retained_list, (list, tuple))
            or output_index >= len(retained_list)
        ):
            continue
        retained_item = retained_list[output_index]
        source_index = None
        if isinstance(retained_item, Mapping):
            for identity_key in (
                "defender_player_id",
                "player_id",
                "entry_id",
                "game_id",
            ):
                identity = retained_item.get(identity_key)
                if identity is None:
                    continue
                source_index = next(
                    (
                        index
                        for index, item in enumerate(source_list)
                        if isinstance(item, Mapping)
                        and item.get(identity_key) == identity
                    ),
                    None,
                )
                if source_index is not None:
                    break
        else:
            source_index = next(
                (
                    index
                    for index, item in enumerate(source_list)
                    if exact_v1_json_equal(item, retained_item)
                ),
                None,
            )
        if source_index is not None:
            adjusted = list(source_tokens)
            adjusted[position] = str(source_index)
            return build_json_pointer(tuple(adjusted))
    return source_path


def _validate_source_scope(
    entry: FieldProvenanceEntry,
    source_entry: FieldProvenanceEntry,
    *,
    decision_index_offset: int,
) -> None:
    if entry.visibility not in _VISIBILITY_RESTRICTIONS[source_entry.visibility]:
        raise _invariant("Retained provenance widens exact-source visibility.")
    if (
        source_entry.visibility == "local_private"
        and entry.visibility == "local_private"
        and entry.perspective_player_id != source_entry.perspective_player_id
    ):
        raise _invariant("Retained provenance changes exact-source perspective.")
    source_rank = _AVAILABILITY_RANKS[source_entry.available_from]
    retained_rank = _AVAILABILITY_RANKS[entry.available_from]
    if retained_rank < source_rank:
        raise _invariant("Retained provenance predates its exact source.")
    retained_decision_index = entry.available_from_decision_index
    if retained_decision_index is not None:
        retained_decision_index += decision_index_offset
    if (
        source_entry.available_from_decision_index is not None
        and retained_decision_index is not None
        and retained_decision_index
        < source_entry.available_from_decision_index
    ):
        raise _invariant("Retained provenance predates its exact-source Decision.")
    if (
        source_entry.available_from_event_index is not None
        and entry.available_from_event_index is not None
        and entry.available_from_event_index < source_entry.available_from_event_index
    ):
        raise _invariant("Retained provenance predates its exact-source event.")
    if retained_rank != source_rank:
        return
    if entry.available_from != source_entry.available_from:
        raise _invariant("Retained provenance changes its exact-source boundary.")
    if (
        source_entry.available_from_decision_index is not None
        and (
            entry.available_from_decision_index is None
            or retained_decision_index
            < source_entry.available_from_decision_index
        )
    ):
        raise _invariant("Retained provenance predates its exact-source Decision.")
    if (
        source_entry.available_from_event_index is not None
        and (
            entry.available_from_event_index is None
            or entry.available_from_event_index < source_entry.available_from_event_index
        )
    ):
        raise _invariant("Retained provenance predates its exact-source event.")


def _reference_requires_exact_scope(
    reference: FieldProvenanceSourceReference,
    *,
    entry: FieldProvenanceEntry,
    attachment: ApplicationProvenanceAttachment,
    binding: V1InformationProvenanceSourceBinding | None,
) -> bool:
    reference_tokens = (
        parse_json_pointer(reference.field_path)
        if reference.field_path is not None
        else ()
    )
    entry_tokens = parse_json_pointer(entry.field_path)
    if (
        reference.reference_type == "request"
        and reference.reference_id != "application_input_reference"
        and reference_tokens
        and entry_tokens
        and reference_tokens[-1] != entry_tokens[-1]
        and not entry_tokens[-1].isdecimal()
    ):
        return False
    if (
        entry.origin in _EXACT_VALUE_ORIGINS
        or reference.reference_type in {"external_record", "historical_game"}
        or reference.reference_id
        in {
            "game_declaration_defaults_v1",
            "information_set_search_evaluation_defaults_v1",
        }
    ):
        return True
    if binding is None:
        return False
    source_path = reference.field_path
    if (
        source_path is None
        and reference.reference_type == "request"
        and reference.reference_id == "application_input_reference"
    ):
        source_path = "/input_reference"
    if source_path is None and reference.reference_type == "retrospective_observation":
        source_path = _retrospective_observation_source_path(reference, entry, binding)
    if source_path is None:
        source_path = _pathless_source_path(binding, entry)
    if source_path is None:
        return False
    try:
        source_value = resolve_json_pointer(binding.document, source_path)
        retained_value = resolve_json_pointer(attachment.document, entry.field_path)
    except SkatMindValidationError:
        return False
    if (
        reference.field_path is not None
        and isinstance(source_value, (list, tuple))
        and entry_tokens
        and entry_tokens[-1].isascii()
        and entry_tokens[-1].isdecimal()
        and int(entry_tokens[-1]) < len(source_value)
    ):
        source_value = source_value[int(entry_tokens[-1])]
    return exact_v1_json_equal(retained_value, source_value)


def _validate_reference(
    reference: FieldProvenanceSourceReference,
    *,
    entry: FieldProvenanceEntry,
    attachment: ApplicationProvenanceAttachment,
    invocation: ApplicationInvocation,
    bindings: Mapping[tuple[str, str], object],
    sources: V1InformationProvenanceSources,
) -> None:
    if (
        reference.reference_type == "request"
        and reference.reference_id == "application_input_reference"
        and (entry.origin != "caller_supplied" or entry.derivation != "direct")
    ):
        raise _invariant("Retained input-reference provenance classification changed.")
    if (
        reference.reference_type == "aggregate"
        and reference.reference_id == "final_outcome_context"
        and reference.field_path is None
        and entry.available_from not in {"game_end", "offline_review"}
    ):
        raise _invariant(
            "Retained provenance uses a final Historical source before game end."
        )
    if not _reference_is_authorized(
        reference,
        invocation=invocation,
        bindings=bindings,
    ):
        raise _invariant(
            "Retained provenance source reference is not authorized: "
            f"{reference.reference_type}/{reference.reference_id}."
        )
    if (
        (reference.reference_type, reference.reference_id)
        in _ENGINE_PRIVATE_REFERENCE_KEYS
        and reference.visibility != "engine_private"
    ):
        raise _invariant("Retained provenance source reference widens visibility.")
    binding = bindings.get((reference.reference_type, reference.reference_id))
    if (
        binding is not None
        and binding.visibility == "engine_private"
        and reference.visibility != "engine_private"
    ):
        raise _invariant("Retained provenance source reference widens visibility.")
    typed_binding = (
        binding
        if isinstance(binding, V1InformationProvenanceSourceBinding)
        else None
    )
    if (
        reference.reference_type in _BOUND_SOURCE_REFERENCE_TYPES
        and typed_binding is None
    ):
        raise _invariant("Retained provenance exact-source reference is unbound.")
    decision_index_offset = 0
    if invocation.request.workflow is WorkflowV1.POSITION_ANALYSIS and (
        attachment.name == "position_result"
        or attachment.name.startswith("flat_retrospective/")
    ):
        request_source = next(
            (
                item
                for item in sources.attachments
                if item.name == "v1_source/request"
            ),
            None,
        )
        if (
            request_source is not None
            and request_source.information_use_context.decision_index is not None
        ):
            decision_index_offset = (
                request_source.information_use_context.decision_index
            )
    if _reference_requires_exact_scope(
        reference,
        entry=entry,
        attachment=attachment,
        binding=typed_binding,
    ):
        for source_entry in _source_entries_for_reference(
            reference,
            entry=entry,
            binding=typed_binding,
            sources=sources,
        ):
            _validate_source_scope(
                entry,
                source_entry,
                decision_index_offset=decision_index_offset,
            )
    if reference.reference_type == "historical_event" and any(
        candidate.reference_type == "request" and candidate.field_path is not None
        for candidate in entry.source_references
    ):
        return
    effective_source_path = reference.field_path
    if (
        effective_source_path is None
        and reference.reference_type == "request"
        and reference.reference_id == "application_input_reference"
    ):
        effective_source_path = "/input_reference"
    if (
        effective_source_path is None
        and typed_binding is not None
        and reference.reference_type == "retrospective_observation"
    ):
        effective_source_path = _retrospective_observation_source_path(
            reference,
            entry,
            typed_binding,
        )
    if (
        effective_source_path is None
        and typed_binding is not None
        and reference.reference_type == "historical_game"
        and entry.origin == "historical_replay"
    ):
        raise _invariant(
            "Retained provenance exact-source path is unresolved for "
            f"{entry.field_path!r}."
        )
    if (
        effective_source_path is None
        and typed_binding is not None
        and (
            entry.origin in _PATHLESS_VALUE_ORIGINS
            or reference.reference_type in {"external_record", "historical_game"}
        )
    ):
        effective_source_path = _pathless_source_path(typed_binding, entry)
    if effective_source_path is None:
        if (
            typed_binding is not None
            and reference.reference_type in _BOUND_SOURCE_REFERENCE_TYPES
            and entry.origin in _FAIL_CLOSED_PATH_ORIGINS
        ):
            raise _invariant(
                "Retained provenance exact-source path is unresolved for "
                f"{entry.field_path!r}."
            )
        return
    source_document = _source_document_for_reference(reference, bindings=bindings)
    if source_document is None:
        raise _invariant("Retained provenance source reference has no exact document.")
    effective_source_path = _canonical_reordered_source_path(
        source_document,
        effective_source_path,
        attachment,
        entry,
    )
    try:
        source_value = resolve_json_pointer(source_document, effective_source_path)
    except SkatMindValidationError as error:
        if (
            reference.reference_type == "request"
            and reference.reference_id == "position_analysis_request"
            and effective_source_path == "/performance_rating_system"
        ):
            source_value = None
        elif (
            reference.field_path is None
            and entry.origin not in _FAIL_CLOSED_PATH_ORIGINS
        ):
            return
        else:
            raise _invariant(
                "Retained provenance source reference path is missing for "
                f"{entry.field_path!r}."
            ) from error
    reference_tokens = (
        parse_json_pointer(reference.field_path)
        if reference.field_path is not None
        else ()
    )
    entry_tokens = parse_json_pointer(entry.field_path)
    if (
        reference.reference_type == "request"
        and reference.reference_id != "application_input_reference"
        and reference_tokens
        and entry_tokens
        and reference_tokens[-1] != entry_tokens[-1]
        and not entry_tokens[-1].isdecimal()
    ):
        return
    if (
        entry.origin not in _EXACT_VALUE_ORIGINS
        and reference.reference_type not in {"external_record", "historical_game"}
        and reference.reference_id
        not in {
            "game_declaration_defaults_v1",
            "information_set_search_evaluation_defaults_v1",
        }
    ):
        return
    try:
        retained_value = resolve_json_pointer(attachment.document, entry.field_path)
    except SkatMindValidationError as error:
        raise _invariant("Retained provenance entry path is missing.") from error
    if (
        reference.field_path is not None
        and isinstance(source_value, (list, tuple))
        and entry_tokens
        and entry_tokens[-1].isascii()
        and entry_tokens[-1].isdecimal()
        and int(entry_tokens[-1]) < len(source_value)
    ):
        source_value = source_value[int(entry_tokens[-1])]
    if not exact_v1_json_equal(retained_value, source_value):
        raise _invariant(
            "Retained normalized value does not match its exact source for "
            f"{entry.field_path!r} via {effective_source_path!r}."
        )


def _validate_resolvable_bound_source_value(
    entry: FieldProvenanceEntry,
    attachment: ApplicationProvenanceAttachment,
    bindings: Mapping[tuple[str, str], object],
) -> None:
    requires_relabel_reconciliation = (
        attachment.name == "flat_decision"
        and entry.field_path == "/game_state/hand"
    )
    if entry.coverage_kind == "subtree" and not requires_relabel_reconciliation:
        return
    if any(
        (reference.reference_type, reference.reference_id) not in bindings
        for reference in entry.source_references
    ) and not requires_relabel_reconciliation:
        return
    if attachment.name.startswith("historical_decision/") and entry.field_path.startswith(
        "/effective_review_settings/"
    ):
        return
    if attachment.name == "position_result" and entry.field_path.startswith(
        "/settings/"
    ):
        return
    if attachment.name == "flat_retrospective/input" and entry.field_path.startswith(
        "/selection/settings/"
    ):
        return
    source_values: list[object] = []
    for reference in entry.source_references:
        binding = bindings.get((reference.reference_type, reference.reference_id))
        if not isinstance(binding, V1InformationProvenanceSourceBinding):
            continue
        source_path = reference.field_path
        if source_path is not None:
            source_tokens = parse_json_pointer(source_path)
            entry_tokens = parse_json_pointer(entry.field_path)
            if source_tokens and entry_tokens and source_tokens[-1] != entry_tokens[-1]:
                continue
        if (
            source_path is None
            and reference.reference_type == "request"
            and reference.reference_id == "application_input_reference"
        ):
            source_path = "/input_reference"
        if source_path is None and reference.reference_type == "retrospective_observation":
            source_path = _retrospective_observation_source_path(
                reference,
                entry,
                binding,
            )
        if source_path is None:
            source_path = _pathless_source_path(binding, entry)
        if source_path is None:
            continue
        source_path = _canonical_reordered_source_path(
            binding.document,
            source_path,
            attachment,
            entry,
        )
        try:
            source_value = resolve_json_pointer(binding.document, source_path)
        except SkatMindValidationError:
            continue
        entry_tokens = parse_json_pointer(entry.field_path)
        if (
            reference.field_path is not None
            and isinstance(source_value, (list, tuple))
            and entry_tokens
            and entry_tokens[-1].isascii()
            and entry_tokens[-1].isdecimal()
            and int(entry_tokens[-1]) < len(source_value)
        ):
            source_value = source_value[int(entry_tokens[-1])]
        if entry.origin not in _EXACT_VALUE_ORIGINS and source_value is None:
            continue
        source_values.append(source_value)
    if not source_values:
        return
    try:
        retained_value = resolve_json_pointer(attachment.document, entry.field_path)
    except SkatMindValidationError as error:
        raise _invariant("Retained provenance entry path is missing.") from error
    if not any(
        exact_v1_json_equal(retained_value, source_value)
        for source_value in source_values
    ):
        raise _invariant(
            "Retained value does not match any resolvable exact source for "
            f"{entry.field_path!r}."
        )


def _document_ancestors(
    document: Mapping[str, object],
    field_path: str,
) -> tuple[Mapping[str, object], ...]:
    ancestors: list[Mapping[str, object]] = [document]
    current: object = document
    for token in parse_json_pointer(field_path):
        if isinstance(current, Mapping):
            current = current.get(token)
        elif isinstance(current, (list, tuple)) and token.isdecimal():
            index = int(token)
            if index >= len(current):
                break
            current = current[index]
        else:
            break
        if isinstance(current, Mapping):
            ancestors.append(current)
    return tuple(ancestors)


def _nearest_document_context_value(
    attachment: ApplicationProvenanceAttachment,
    entry: FieldProvenanceEntry,
    key: str,
) -> object | None:
    for ancestor in reversed(_document_ancestors(attachment.document, entry.field_path)):
        direct = ancestor.get(key)
        if direct is not None:
            return direct
        for container_name in ("metadata", "decision_time_facts"):
            container = ancestor.get(container_name)
            if isinstance(container, Mapping) and container.get(key) is not None:
                return container[key]
    return None


def _max_document_index(document: object, key: str) -> int | None:
    values: list[int] = []

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            candidate = value.get(key)
            if type(candidate) is int:
                values.append(candidate)
            for item in value.values():
                visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(document)
    return max(values) if values else None


def _tactical_entry_decision_index(
    attachment: ApplicationProvenanceAttachment,
    entry: FieldProvenanceEntry,
) -> int | None:
    tokens = parse_json_pointer(entry.field_path)
    if (
        attachment.name != "historical_tactical_motif_review_summary"
        and "historical_tactical_motif_review_summary" not in tokens
    ):
        return None
    if "observations" not in tokens:
        return None
    observation = next(
        (
            ancestor
            for ancestor in reversed(
                _document_ancestors(attachment.document, entry.field_path)
            )
            if "observation_status" in ancestor
            and isinstance(ancestor.get("decision_time_facts"), Mapping)
        ),
        None,
    )
    if observation is None:
        return None
    facts = observation.get("decision_time_facts")
    if not isinstance(facts, Mapping):
        raise _invariant("Retained Tactical provenance has no Decision Facts.")
    decision_index = facts.get("decision_index")
    trick_number = facts.get("trick_number")
    if type(decision_index) is not int or type(trick_number) is not int:
        raise _invariant("Retained Tactical provenance identity changed.")
    if "decision_time_facts" in tokens or tokens[-1] == "actual_card":
        return decision_index
    after_completion_motif = False
    if "motifs" in tokens:
        motif_position = tokens.index("motifs") + 1
        motifs = observation.get("motifs")
        if (
            motif_position < len(tokens)
            and tokens[motif_position].isdecimal()
            and isinstance(motifs, (list, tuple))
        ):
            motif_index = int(tokens[motif_position])
            if motif_index < len(motifs) and isinstance(motifs[motif_index], Mapping):
                after_completion_motif = (
                    motifs[motif_index].get("evidence_time")
                    == "after_trick_completion"
                )
    completion_derived = observation.get("observation_status") == "complete" and (
        tokens[-1].startswith("completed_trick_")
        or tokens[-1] == "observation_status"
        or after_completion_motif
    )
    return trick_number * 3 if completion_derived else decision_index


def _independent_entry_context(
    attachment: ApplicationProvenanceAttachment,
    entry: FieldProvenanceEntry,
):
    context = attachment.information_use_context
    perspective_player_id = context.perspective_player_id
    decision_index = context.decision_index
    event_index = context.event_index

    if entry.visibility == "local_private":
        expected_player = _nearest_document_context_value(
            attachment,
            entry,
            "acting_player_id",
        )
        if expected_player is None:
            expected_player = perspective_player_id
        if not isinstance(expected_player, str) or not expected_player:
            raise _invariant(
                "Retained private provenance has no independent perspective."
            )
        if entry.perspective_player_id != expected_player:
            raise _invariant("Retained provenance perspective changed.")
        perspective_player_id = expected_player

    if entry.available_from_decision_index is not None:
        expected_index = _tactical_entry_decision_index(attachment, entry)
        if expected_index is None:
            expected_index = _nearest_document_context_value(
                attachment,
                entry,
                "decision_index",
            )
        if expected_index is not None and (
            type(expected_index) is not int
            or entry.available_from_decision_index != expected_index
        ):
            raise _invariant("Retained provenance decision index changed.")
        if (
            expected_index is None
            and decision_index is not None
            and context.stage == "decision_time"
            and entry.available_from_decision_index != decision_index
        ):
            raise _invariant("Retained provenance decision index changed.")
        if decision_index is None:
            decision_index = _max_document_index(attachment.document, "decision_index")
        if decision_index is None or entry.available_from_decision_index > decision_index:
            raise _invariant("Retained provenance decision index is not authorized.")

    if entry.available_from_event_index is not None:
        if event_index is None:
            serialized_index = _max_document_index(attachment.document, "event_index")
            event_index = None if serialized_index is None else serialized_index - 1
        if event_index is None or entry.available_from_event_index > event_index:
            raise _invariant("Retained provenance event index is not authorized.")

    return replace(
        context,
        perspective_player_id=perspective_player_id,
        decision_index=decision_index,
        event_index=event_index,
    )


def _validate_historical_decision_inputs(
    provenance: ApplicationProvenanceBundle,
    trusted_checkpoints: Mapping[str, Mapping[str, object]],
) -> None:
    if provenance.workflow is not WorkflowV1.HISTORICAL_GAME:
        return
    decision_inputs = tuple(
        attachment
        for attachment in provenance.attachments
        if re.fullmatch(r"historical_decision/(\d+)/input", attachment.name)
        is not None
    )
    result_attachment = next(
        (
            attachment
            for attachment in provenance.attachments
            if attachment.name == "historical_game_result"
        ),
        None,
    )
    if result_attachment is None:
        raise _invariant("Historical provenance has no exact Root Result attachment.")
    result_summary = result_attachment.document.get("historical_game_summary")
    serialized_result_snapshots = (
        result_summary.get("decision_snapshot_summary")
        if isinstance(result_summary, Mapping)
        else None
    )
    if not decision_inputs and serialized_result_snapshots is None:
        return
    snapshot_attachment = next(
        (
            attachment
            for attachment in provenance.attachments
            if attachment.name == "historical_snapshot_summary"
        ),
        None,
    )
    if snapshot_attachment is None:
        raise _invariant("Historical provenance has no retained safe Snapshot summary.")
    snapshot_summary = snapshot_attachment.document
    checkpoint = trusted_checkpoints.get("historical_snapshot_summary")
    if checkpoint is None:
        raise _invariant("Historical provenance has no trusted Snapshot checkpoint.")
    if not exact_v1_json_equal(snapshot_summary, checkpoint):
        raise _invariant(
            "Historical decision provenance changed from its trusted Snapshot checkpoint."
        )
    snapshots = (
        snapshot_summary.get("snapshots", ())
        if isinstance(snapshot_summary, Mapping)
        else ()
    )
    if decision_inputs and not snapshots:
        raise _invariant("Historical provenance retained no safe Snapshots.")
    if serialized_result_snapshots is not None and not exact_v1_json_equal(
        serialized_result_snapshots,
        snapshot_summary,
    ):
        raise _invariant(
            "Historical decision provenance changed from its retained Snapshot summary."
        )
    if not decision_inputs:
        return
    snapshots_by_index = {
        snapshot["decision_index"]: snapshot
        for snapshot in snapshots
        if isinstance(snapshot, Mapping)
        and type(snapshot.get("decision_index")) is int
    }
    projection_keys = (
        "source_game_id",
        "decision_index",
        "trick_number",
        "play_index",
        "acting_player_id",
        "acting_seat",
        "acting_side",
        "information_cutoff",
        "relative_player_map",
        "visible_state",
    )
    for attachment in decision_inputs:
        match = re.fullmatch(r"historical_decision/(\d+)/input", attachment.name)
        assert match is not None
        decision_index = int(match.group(1))
        snapshot = snapshots_by_index.get(decision_index)
        if snapshot is None:
            raise _invariant(
                "Historical decision provenance has no retained safe Snapshot."
            )
        document = attachment.document
        for entry in attachment.ledger.entries:
            expected_visibility = (
                "local_private"
                if entry.field_path.startswith(
                    ("/visible_state/own_hand/", "/visible_state/known_skat_cards/")
                )
                else entry.visibility
            )
            if entry.visibility != expected_visibility:
                raise _invariant(
                    "Historical decision provenance visibility changed."
                )
            if entry.available_from != "current_decision" or (
                entry.available_from_decision_index != decision_index
            ):
                raise _invariant(
                    "Historical decision provenance timing changed."
                )
        if document.get("information_policy") != "decision_time":
            raise _invariant("Historical decision information policy changed.")
        for key in projection_keys:
            if key not in document or key not in snapshot or not exact_v1_json_equal(
                document[key],
                snapshot[key],
            ):
                raise _invariant(
                    "Historical decision provenance changed from its safe Snapshot."
                )
        if ("source_played_at" in document) != ("source_played_at" in snapshot) or (
            "source_played_at" in document
            and not exact_v1_json_equal(
                document["source_played_at"],
                snapshot["source_played_at"],
            )
        ):
            raise _invariant(
                "Historical decision provenance changed its source time."
            )


def _validate_training_feature_aggregates(
    provenance: ApplicationProvenanceBundle,
) -> None:
    if provenance.workflow is not WorkflowV1.TRAINING_DATASET:
        return
    attachments = {item.name: item for item in provenance.attachments}
    for attachment in provenance.attachments:
        for entry in attachment.ledger.entries:
            feature_tokens = parse_json_pointer(entry.field_path)
            if "features" not in feature_tokens:
                continue
            feature_position = feature_tokens.index("features")
            source_path = build_json_pointer(feature_tokens[feature_position + 1 :])
            for reference in entry.source_references:
                if not reference.reference_id.startswith("training_feature/"):
                    continue
                reference_tokens = reference.reference_id.split("/")
                if len(reference_tokens) != 3:
                    raise _invariant("Retained Training feature identity changed.")
                source_attachment = attachments.get(
                    "training_dataset/sample/"
                    f"{reference_tokens[1]}/{reference_tokens[2]}/feature"
                )
                if source_attachment is None:
                    raise _invariant("Retained Training feature source is missing.")
                try:
                    retained_value = resolve_json_pointer(
                        attachment.document,
                        entry.field_path,
                    )
                    source_value = resolve_json_pointer(
                        source_attachment.document,
                        source_path,
                    )
                except SkatMindValidationError as error:
                    raise _invariant(
                        "Retained Training feature source path is missing."
                    ) from error
                if not exact_v1_json_equal(retained_value, source_value):
                    raise _invariant(
                        "Retained Training feature changed from its exact aggregate."
                    )


def validate_v1_retained_stage_linkage(
    invocation: ApplicationInvocation,
    sources: V1InformationProvenanceSources,
    provenance: ApplicationProvenanceBundle,
    *,
    trusted_checkpoint_documents: tuple[
        tuple[str, Mapping[str, object]], ...
    ] = (),
) -> V1InformationProvenanceRetainedLinkage:
    """Closes every retained source reference against this exact invocation."""
    if not isinstance(invocation, ApplicationInvocation):
        raise SkatMindValidationError(
            "invocation must be an ApplicationInvocation.",
            path="invocation",
        )
    if not isinstance(provenance, ApplicationProvenanceBundle):
        raise _invariant("Root execution retained no provenance bundle.")
    validate_v1_information_provenance_sources(invocation, sources)
    if provenance.workflow is not invocation.request.workflow:
        raise _invariant("Retained provenance bundle has the wrong workflow.")
    trusted_checkpoints = dict(trusted_checkpoint_documents)
    if len(trusted_checkpoints) != len(trusted_checkpoint_documents):
        raise _invariant("Retained provenance checkpoint identity is duplicated.")
    _validate_historical_decision_inputs(provenance, trusted_checkpoints)
    _validate_training_feature_aggregates(provenance)
    bindings = source_binding_map(sources)
    for attachment in provenance.attachments:
        _require_complete_attachment(attachment)
        if attachment.information_use_context.workflow != provenance.workflow.value:
            raise _invariant("Retained provenance attachment has the wrong workflow.")
        for entry in attachment.ledger.entries:
            if not entry.source_references:
                raise _invariant("Retained provenance entry has no source reference.")
            _validate_resolvable_bound_source_value(entry, attachment, bindings)
            context = _independent_entry_context(attachment, entry)
            validate_field_provenance_entry_use(
                entry,
                context,
            )
            for reference in entry.source_references:
                _validate_reference(
                    reference,
                    entry=entry,
                    attachment=attachment,
                    invocation=invocation,
                    bindings=bindings,
                    sources=sources,
                )
    return V1InformationProvenanceRetainedLinkage(
        workflow=provenance.workflow,
        linked_attachment_names=tuple(item.name for item in provenance.attachments),
        trusted_checkpoint_documents=trusted_checkpoint_documents,
    )
