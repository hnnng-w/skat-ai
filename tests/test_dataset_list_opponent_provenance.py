import copy
import json
from pathlib import Path

import pytest
from test_historical_declarer_concession import build_concession_prefix
from test_search_provenance import _result as build_search_result
from test_search_provenance import _unavailable as build_unavailable_search_result
from test_training_dataset import build_training_input

from skat_ai.api.v1 import WorkflowV1
from skat_ai.application import (
    ApplicationExecutionOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.bounded_search_result import build_serializable_bounded_search_result
from skat_ai.dataset_preparation_provenance import (
    DATASET_PREPARATION_PROVENANCE_VERSION,
    validate_dataset_preparation_assignment_references,
)
from skat_ai.errors import SkatAIValidationError
from skat_ai.field_provenance import FieldProvenanceSourceReference
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.historical_list_provenance import (
    HISTORICAL_LIST_PROVENANCE_VERSION,
    validate_historical_list_progression_dependencies,
)
from skat_ai.opponent_workflow_provenance import OPPONENT_WORKFLOW_PROVENANCE_VERSION
from skat_ai.retrospective_review_provenance import build_complete_provenance_attachment
from skat_ai.training_dataset_provenance import (
    TRAINING_DATASET_PROVENANCE_VERSION,
    _search_result_entry_builder,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"


def _load(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _execute(
    name: str,
    *,
    training_options: TrainingDatasetApplicationOptions | None = None,
):
    options = (
        ApplicationExecutionOptions(training_dataset=training_options)
        if training_options is not None
        else None
    )
    invocation = build_application_invocation(
        _load(name),
        input_reference="fixture://145",
        options=options,
    )
    return execute_application_invocation(invocation)


def _attachment(execution, name: str):
    assert execution.provenance is not None
    return next(item for item in execution.provenance.attachments if item.name == name)


def _assert_complete(execution, root_name: str) -> None:
    assert execution.provenance is not None
    assert execution.provenance.attachments[-1].name == root_name
    for attachment in execution.provenance.attachments:
        assert attachment.ledger.status == "complete"
        assert attachment.ledger.exemptions == ()
        assert attachment.coverage_summary.provenance_complete is True


def test_propagation_versions_are_independent_version_one_constants() -> None:
    assert TRAINING_DATASET_PROVENANCE_VERSION == 1
    assert DATASET_PREPARATION_PROVENANCE_VERSION == 1
    assert OPPONENT_WORKFLOW_PROVENANCE_VERSION == 1
    assert HISTORICAL_LIST_PROVENANCE_VERSION == 1


@pytest.mark.parametrize(
    ("name", "workflow", "root_attachment"),
    [
        (
            "training_dataset_normal_play.json",
            WorkflowV1.TRAINING_DATASET,
            "training_dataset_result",
        ),
        (
            "training_dataset_preparation_unavailable.json",
            WorkflowV1.TRAINING_DATASET_PREPARATION,
            "dataset_preparation_result",
        ),
        (
            "opponent_statistics.json",
            WorkflowV1.OPPONENT_STATISTICS,
            "opponent_statistics_result",
        ),
        (
            "fixed_three_player_historical_list_mixed.json",
            WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
            "historical_list_result",
        ),
        (
            "fixed_three_player_historical_list_comparison.json",
            WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
            "historical_list_comparison_result",
        ),
    ],
)
def test_all_five_root_workflows_have_complete_internal_bundles(
    name: str,
    workflow: WorkflowV1,
    root_attachment: str,
) -> None:
    execution = _execute(name)

    assert execution.provenance is not None
    assert execution.provenance.workflow is workflow
    _assert_complete(execution, root_attachment)
    assert (
        _attachment(execution, root_attachment).document_to_dict()
        == (execution.result.to_dict()["document"])
    )


def test_training_summary_separates_records_features_targets_and_aggregates() -> None:
    execution = _execute("training_dataset_normal_play.json")
    assert execution.provenance is not None
    names = [attachment.name for attachment in execution.provenance.attachments]
    summary = execution.result.to_dict()["document"]["training_dataset_summary"]

    assert names[:3] == [
        "training_dataset/input",
        "training_dataset/record/0",
        "training_dataset/record/1",
    ]
    assert len([name for name in names if name.endswith("/feature")]) == summary["sample_count"]
    assert len([name for name in names if name.endswith("/target")]) == summary["sample_count"]
    feature = _attachment(execution, "training_dataset/sample/0/1/feature")
    target = _attachment(execution, "training_dataset/sample/0/1/target")
    feature_text = str(feature.document_to_dict())
    assert "actual_card_played" not in feature_text
    assert "settlement" not in feature_text
    assert target.information_use_context.stage == "after_actual_play"
    assert all(entry.available_from == "after_actual_play" for entry in target.ledger.entries)
    assert any(entry.visibility == "local_private" for entry in feature.ledger.entries)

    summary_attachment = _attachment(execution, "training_dataset/summary")
    feature_entry = next(
        entry
        for entry in summary_attachment.ledger.entries
        if entry.field_path == "/records/0/samples/0/features/game_type"
    )
    target_entry = next(
        entry
        for entry in summary_attachment.ledger.entries
        if entry.field_path == "/records/0/samples/0/label/card"
    )
    assert feature_entry.available_from == "current_decision"
    assert target_entry.available_from == "after_actual_play"
    assert feature_entry.source_references[0].reference_id == "training_feature/0/1"
    assert target_entry.source_references[0].reference_id == "training_target/0/1"


def test_zero_sample_record_has_record_but_no_artificial_sample_attachment() -> None:
    root = {"training_dataset_input": build_training_input([build_concession_prefix()])}
    invocation = build_application_invocation(root, input_reference="fixture://zero")
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    names = [attachment.name for attachment in execution.provenance.attachments]
    summary = execution.result.to_dict()["document"]["training_dataset_summary"]

    assert summary["sample_count"] == 0
    assert "training_dataset/record/0" in names
    assert not any(name.startswith("training_dataset/sample/") for name in names)


@pytest.mark.parametrize(
    ("mode", "expected_status"),
    [
        ("report_only", "not_evaluated"),
        ("known_opponent", "compliant"),
        ("unseen_player", "non_compliant"),
    ],
)
def test_every_partition_audit_mode_has_complete_card_independent_provenance(
    mode: str,
    expected_status: str,
) -> None:
    execution = _execute(
        "training_dataset_partition_audit.json",
        training_options=TrainingDatasetApplicationOptions(
            operation="partition_audit",
            partition_audit_mode=mode,
        ),
    )
    audit = _attachment(execution, "training_dataset/partition_audit")
    assert audit.document["effective_audit_mode"] == mode
    assert audit.document["compliance_status"] == expected_status
    assert audit.coverage_summary.provenance_complete is True


@pytest.mark.parametrize(
    ("operation", "example", "operation_attachment"),
    [
        ("summary", "training_dataset_normal_play.json", "training_dataset/summary"),
        (
            "partition_audit",
            "training_dataset_partition_audit.json",
            "training_dataset/partition_audit",
        ),
        (
            "rolling_opponent_policy_evaluation",
            "historical_opponent_policy_evaluation_dataset.json",
            "training_dataset/rolling_evaluation",
        ),
        (
            "bounded_search_evaluation",
            "training_dataset_normal_play.json",
            "training_dataset/bounded_search_evaluation",
        ),
        (
            "historical_opponent_statistics_aggregation",
            "training_dataset_normal_play.json",
            "training_dataset/opponent_statistics_aggregation",
        ),
    ],
)
def test_all_training_operations_have_one_complete_operation_and_root_ledger(
    operation: str,
    example: str,
    operation_attachment: str,
) -> None:
    options = TrainingDatasetApplicationOptions(
        operation=operation,
        **(
            {"bounded_search_seed": 71, "bounded_search_max_decisions": 1}
            if operation == "bounded_search_evaluation"
            else {}
        ),
    )
    execution = _execute(example, training_options=options)

    _assert_complete(execution, "training_dataset_result")
    assert _attachment(execution, operation_attachment).ledger.status == "complete"


def test_partition_audit_provenance_references_no_card_or_result_information() -> None:
    execution = _execute(
        "training_dataset_partition_audit.json",
        training_options=TrainingDatasetApplicationOptions(
            operation="partition_audit",
            partition_audit_mode="report_only",
        ),
    )
    audit = _attachment(execution, "training_dataset/partition_audit")
    serialized_references = str(
        [reference for entry in audit.ledger.entries for reference in entry.source_references]
    ).lower()
    assert "card" not in serialized_references
    assert "settlement" not in serialized_references
    assert "target" not in serialized_references


def test_rolling_and_search_keep_prediction_and_actual_stages_separate() -> None:
    rolling = _execute(
        "historical_opponent_policy_evaluation_dataset.json",
        training_options=TrainingDatasetApplicationOptions(
            operation="rolling_opponent_policy_evaluation"
        ),
    )
    assert rolling.provenance is not None
    prediction = next(
        attachment
        for attachment in rolling.provenance.attachments
        if attachment.name.endswith("/prediction")
    )
    actual = next(
        attachment
        for attachment in rolling.provenance.attachments
        if attachment.name.endswith("/actual")
    )
    assert "actual_card" not in prediction.document_to_dict()
    assert prediction.information_use_context.stage == "decision_time"
    assert actual.information_use_context.stage == "after_actual_play"

    search = _execute(
        "training_dataset_normal_play.json",
        training_options=TrainingDatasetApplicationOptions(
            operation="bounded_search_evaluation",
            bounded_search_seed=71,
            bounded_search_max_decisions=1,
        ),
    )
    names = [attachment.name for attachment in search.provenance.attachments]
    prefix = "training_dataset/search/0/1/"
    assert [name for name in names if name.startswith(prefix)] == [
        f"{prefix}input",
        f"{prefix}immediate",
        f"{prefix}search",
        f"{prefix}comparison",
        f"{prefix}actual",
        f"{prefix}retrospective",
    ]
    assert (
        "effective_random_seed" not in _attachment(search, f"{prefix}immediate").document_to_dict()
    )


@pytest.mark.parametrize(
    "result",
    [
        build_search_result(),
        build_search_result(coverage="all_compatible_worlds"),
        build_search_result(
            status="partial",
            stop_reason="node_budget_exhausted",
            completed=2,
            selected=3,
        ),
        build_search_result(
            status="timeout",
            stop_reason="wall_clock_timeout",
            completed=0,
            selected=3,
            recommend=False,
        ),
        build_unavailable_search_result(),
    ],
)
def test_bounded_search_stage_mapping_covers_all_statuses_without_private_state(
    result,
) -> None:
    document = build_serializable_bounded_search_result(result)
    attachment = build_complete_provenance_attachment(
        name="training_dataset/search/0/1/search",
        document_role="result",
        document=document,
        information_use_context=InformationUseContext(
            workflow="training_dataset",
            stage="decision_time",
            perspective_player_id="me",
            perspective_side="declarer",
            decision_index=1,
            event_index=None,
        ),
        entry_builder=_search_result_entry_builder(
            document,
            decision_index=1,
            player_id="me",
        ),
    )
    assert attachment.coverage_summary.provenance_complete is True
    serialized = str(attachment.document_to_dict()).lower()
    for forbidden in (
        "ownership",
        "exact_search_state",
        "cache",
        "branch",
        "principal_variation",
    ):
        assert forbidden not in serialized


def test_historical_aggregation_export_has_separate_internal_attachment() -> None:
    execution = _execute(
        "training_dataset_normal_play.json",
        training_options=TrainingDatasetApplicationOptions(
            operation="historical_opponent_statistics_aggregation",
            export_opponent_statistics=True,
        ),
    )

    assert [artifact.name for artifact in execution.artifacts] == ["opponent_statistics_input"]
    artifact_attachment = _attachment(execution, "training_dataset/opponent_statistics_input")
    assert artifact_attachment.document_to_dict() == execution.artifacts[0].to_dict()
    assert "opponent_statistics_input" not in execution.result.to_dict()["document"]


@pytest.mark.parametrize(
    ("name", "mode", "materialized"),
    [
        ("training_dataset_preparation_known_opponent.json", "known_opponent", True),
        ("training_dataset_preparation_unseen_player.json", "unseen_player", True),
        ("training_dataset_preparation_unavailable.json", "known_opponent", False),
    ],
)
def test_preparation_assignment_sources_and_materialization_are_information_safe(
    name: str,
    mode: str,
    materialized: bool,
) -> None:
    execution = _execute(name)
    assert execution.provenance is not None
    plan = _attachment(execution, "dataset_preparation/plan")
    assignment_entries = [
        entry for entry in plan.ledger.entries if entry.origin == "dataset_assignment"
    ]
    for entry in assignment_entries:
        validate_dataset_preparation_assignment_references(mode, entry.source_references)
    reference_text = str(
        [reference for entry in assignment_entries for reference in entry.source_references]
    ).lower()
    for forbidden in ("card", "settlement", "outcome", "sample_count", "notes"):
        assert forbidden not in reference_text
    if mode == "unseen_player":
        assert "played_at" not in reference_text

    names = [attachment.name for attachment in execution.provenance.attachments]
    assert ("dataset_preparation/materialized_dataset" in names) is materialized
    if materialized:
        dataset = _attachment(execution, "dataset_preparation/materialized_dataset")
        derived = [
            entry for entry in dataset.ledger.entries if entry.origin == "dataset_assignment"
        ]
        assert derived
        assert all(entry.field_path.endswith("/partition") for entry in derived)


def test_opponent_records_profiles_and_source_notes_remain_separate() -> None:
    execution = _execute("opponent_statistics.json")
    assert execution.provenance is not None
    names = [attachment.name for attachment in execution.provenance.attachments]
    record_names = [name for name in names if name.startswith("opponent_statistics/record/")]
    profile_names = [name for name in names if name.startswith("opponent_statistics/profile/")]
    assert len(record_names) == len(profile_names) > 0
    profile = _attachment(execution, profile_names[0])
    profile_document = profile.document_to_dict()
    assert set(profile_document) == {
        "player_id",
        "normalized_profile_statistics",
        "profile_derivation",
    }
    assert "confidence" not in profile.ledger.__dataclass_fields__
    assert all(
        reference.field_path != "/source/notes"
        for entry in profile.ledger.entries
        for reference in entry.source_references
    )


@pytest.mark.parametrize(
    ("name", "expected_reference_type"),
    [
        ("opponent_statistics.json", "external_record"),
        ("historical_aggregation_export", "aggregate"),
    ],
)
def test_opponent_source_types_remain_distinct(
    name: str,
    expected_reference_type: str,
) -> None:
    if name == "historical_aggregation_export":
        aggregation = _execute(
            "training_dataset_normal_play.json",
            training_options=TrainingDatasetApplicationOptions(
                operation="historical_opponent_statistics_aggregation",
                export_opponent_statistics=True,
            ),
        )
        invocation = build_application_invocation(
            aggregation.artifacts[0].to_dict(),
            input_reference="fixture://historical-statistics",
        )
        execution = execute_application_invocation(invocation)
    else:
        execution = _execute(name)
    record = _attachment(execution, "opponent_statistics/record/0")
    assert {
        reference.reference_type
        for entry in record.ledger.entries
        for reference in entry.source_references
    } == {expected_reference_type}


def test_historical_list_has_36_entry_attachments_and_prefix_only_progression() -> None:
    execution = _execute("fixed_three_player_historical_list_mixed.json")
    assert execution.provenance is not None
    entries = [
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name.startswith("historical_list/entry/")
    ]
    assert len(entries) == 36
    assert entries[0].name == "historical_list/entry/1"
    assert entries[-1].name == "historical_list/entry/36"
    aggregation = _attachment(execution, "historical_list/aggregation")
    validate_historical_list_progression_dependencies(aggregation.ledger.entries)
    assert all(
        "initial_hand" not in reference.reference_id
        and "skat" not in reference.reference_id.lower()
        for entry in aggregation.ledger.entries
        for reference in entry.source_references
    )


def test_passed_deal_has_no_historical_game_or_settlement_provenance() -> None:
    execution = _execute("fixed_three_player_historical_list_all_passed.json")
    entry = _attachment(execution, "historical_list/entry/1")
    document = entry.document_to_dict()

    assert document["entry_kind"] == "passed_deal"
    assert document["game_id"] is None
    assert document["declarer_player_id"] is None
    assert document["settlement_score"] is None
    assert all(
        reference.reference_type != "historical_game"
        for provenance_entry in entry.ledger.entries
        for reference in provenance_entry.source_references
    )
    for contribution in document["player_contributions"]:
        assert contribution["played_game_count"] == 0
        assert contribution["declarer_game_count"] == 0
        assert contribution["defender_game_count"] == 0
        assert contribution["total_performance_points"] == 0


def test_external_lot_changes_only_final_tied_ordering_provenance() -> None:
    unresolved = _execute("fixed_three_player_historical_list_all_passed.json")
    root = _load("fixed_three_player_historical_list_all_passed.json")
    request = root["fixed_three_player_historical_list_input"]
    player_ids = [player["player_id"] for player in request["historical_list"]["players"]]
    request["lot_order"] = list(reversed(player_ids))
    invocation = build_application_invocation(root, input_reference="fixture://lot")
    resolved = execute_application_invocation(invocation)

    unresolved_aggregation = _attachment(
        unresolved, "historical_list/aggregation"
    ).document_to_dict()
    resolved_aggregation = _attachment(resolved, "historical_list/aggregation").document_to_dict()
    assert unresolved_aggregation["progression"] == resolved_aggregation["progression"]
    assert unresolved_aggregation["player_totals"] == resolved_aggregation["player_totals"]
    assert resolved_aggregation["applied_lot_order"] == list(reversed(player_ids))
    assert resolved_aggregation["ranking_status"] == "final"


def test_list_comparison_attaches_ordered_sources_pairs_and_rank_statuses() -> None:
    execution = _execute("fixed_three_player_historical_list_comparison.json")
    assert execution.provenance is not None
    names = [attachment.name for attachment in execution.provenance.attachments]
    assert [name for name in names if name.startswith("historical_list_comparison/source/")] == [
        "historical_list_comparison/source/0",
        "historical_list_comparison/source/1",
    ]
    assert [name for name in names if name.startswith("historical_list_comparison/pair/")] == [
        "historical_list_comparison/pair/0"
    ]
    pair = _attachment(execution, "historical_list_comparison/pair/0").document_to_dict()
    assert pair["reference_list_id"] != pair["comparison_list_id"]
    for player in pair["player_comparisons"]:
        assert player["rank_comparison_status"] in {
            "available",
            "reference_lot_required",
            "comparison_lot_required",
            "both_lot_required",
        }
        for field, delta in player["deltas"].items():
            assert delta == player["comparison_totals"][field] - player["reference_totals"][field]


def test_temporal_and_split_dependency_guards_reject_forbidden_sources() -> None:
    forbidden = FieldProvenanceSourceReference(
        reference_type="external_record",
        reference_id="dataset_preparation_source/0",
        field_path="/played_at",
        visibility="public",
    )
    with pytest.raises(ValueError, match="cannot use"):
        validate_dataset_preparation_assignment_references("unseen_player", (forbidden,))

    execution = _execute("fixed_three_player_historical_list_mixed.json")
    aggregation = _attachment(execution, "historical_list/aggregation")
    first = next(
        entry
        for entry in aggregation.ledger.entries
        if entry.field_path == "/progression/0/cumulative_player_totals/0/list_entry_count"
    )
    tampered = copy.copy(first)
    object.__setattr__(tampered, "dependency_paths", ("/progression/1/entry_fact/entry_id",))
    with pytest.raises(ValueError, match="later entry"):
        validate_historical_list_progression_dependencies((tampered,))


def test_public_result_documents_still_contain_no_provenance_field() -> None:
    for name in (
        "training_dataset_normal_play.json",
        "training_dataset_preparation_unavailable.json",
        "opponent_statistics.json",
        "fixed_three_player_historical_list_mixed.json",
        "fixed_three_player_historical_list_comparison.json",
    ):
        execution = _execute(name)
        assert "provenance" not in execution.result.to_dict()
        assert "provenance" not in execution.result.to_dict()["document"]


def test_assignment_reference_validator_rejects_unknown_mode_fields() -> None:
    reference = FieldProvenanceSourceReference(
        reference_type="external_record",
        reference_id="dataset_preparation_source/0",
        field_path="/notes",
        visibility="public",
    )
    with pytest.raises(ValueError, match="notes"):
        validate_dataset_preparation_assignment_references("known_opponent", (reference,))

    with pytest.raises(SkatAIValidationError):
        FieldProvenanceSourceReference(
            reference_type="external_record",
            reference_id="hidden",
            field_path="not-a-pointer",
            visibility="engine_private",
        )
