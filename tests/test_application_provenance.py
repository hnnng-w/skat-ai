from dataclasses import FrozenInstanceError, fields, replace

import pytest

from skatmind.api.v1 import ResultDocumentV1, WorkflowV1
from skatmind.application import (
    APPLICATION_PROVENANCE_VERSION,
    ApplicationExecutionResult,
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skatmind.dataset_preparation_provenance import (
    DATASET_PREPARATION_PROVENANCE_VERSION,
)
from skatmind.errors import SkatMindValidationError
from skatmind.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
)
from skatmind.game_declaration import GameDeclaration
from skatmind.game_state import GameState
from skatmind.historical_list_provenance import HISTORICAL_LIST_PROVENANCE_VERSION
from skatmind.live_analysis_provenance import (
    LIVE_ANALYSIS_PROVENANCE_VERSION,
    build_live_decision_provenance_attachment,
)
from skatmind.opponent_workflow_provenance import OPPONENT_WORKFLOW_PROVENANCE_VERSION
from skatmind.replay_coaching_provenance import REPLAY_COACHING_PROVENANCE_VERSION
from skatmind.retrospective_review_provenance import (
    RETROSPECTIVE_REVIEW_PROVENANCE_VERSION,
)
from skatmind.strategic_metadata import StrategicMetadata
from skatmind.training_dataset_provenance import TRAINING_DATASET_PROVENANCE_VERSION


def _attachment(name: str = "flat_decision") -> ApplicationProvenanceAttachment:
    return build_live_decision_provenance_attachment(
        name=name,
        state=GameState(
            game_type="grand",
            player_role="declarer",
            declarer_player="me",
            hand=["CA"],
            current_trick=["C7", "C8"],
            trick_leader="left",
            next_player="me",
        ),
        left_hand_size=0,
        right_hand_size=0,
        public_hand_constraints=(),
        strategic_metadata=StrategicMetadata(),
        game_declaration=GameDeclaration("grand", matadors=1, bid_value=24),
        decision_index=0,
        selection_method="immediate_expected_value",
        selection_settings={
            "sample_count": 1,
            "use_basic_opponent_strategy": True,
            "opponent_response_policy_by_player": {},
            "bounded_search_budget": None,
        },
        simulation_scope=False,
    )


def test_application_provenance_contracts_are_versioned_and_exact() -> None:
    assert APPLICATION_PROVENANCE_VERSION == 1
    assert LIVE_ANALYSIS_PROVENANCE_VERSION == 1
    assert RETROSPECTIVE_REVIEW_PROVENANCE_VERSION == 1
    assert REPLAY_COACHING_PROVENANCE_VERSION == 1
    assert TRAINING_DATASET_PROVENANCE_VERSION == 1
    assert DATASET_PREPARATION_PROVENANCE_VERSION == 1
    assert OPPONENT_WORKFLOW_PROVENANCE_VERSION == 1
    assert HISTORICAL_LIST_PROVENANCE_VERSION == 1
    assert tuple(field.name for field in fields(ApplicationProvenanceAttachment)) == (
        "name",
        "document_role",
        "document",
        "ledger",
        "coverage_summary",
        "information_use_context",
    )
    assert tuple(field.name for field in fields(ApplicationProvenanceBundle)) == (
        "workflow",
        "attachments",
        "provenance_version",
    )


def test_attachment_is_frozen_defensive_and_requires_matching_coverage() -> None:
    attachment = _attachment()
    mutable = attachment.document_to_dict()
    mutable["game_state"]["hand"].append("D7")

    assert attachment.document["game_state"]["hand"] == ("CA",)
    assert attachment.ledger.status == "complete"
    assert attachment.coverage_summary.provenance_complete is True
    with pytest.raises(FrozenInstanceError):
        attachment.name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        attachment.document["extra"] = True

    mismatched = build_field_provenance_coverage_summary(
        {"other": True},
        attachment.ledger,
    )
    with pytest.raises(SkatMindValidationError, match="does not match"):
        replace(attachment, coverage_summary=mismatched)


def test_bundle_canonicalizes_names_and_rejects_duplicates() -> None:
    attachments = [
        _attachment("position_result"),
        _attachment("multi_step_decision/10"),
        _attachment("multi_step_decision/2"),
        _attachment("flat_decision"),
    ]
    bundle = ApplicationProvenanceBundle(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        attachments=attachments,
    )

    assert [item.name for item in bundle.attachments] == [
        "flat_decision",
        "multi_step_decision/2",
        "multi_step_decision/10",
        "position_result",
    ]
    with pytest.raises(SkatMindValidationError, match="unique names"):
        ApplicationProvenanceBundle(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            attachments=(attachments[0], attachments[0]),
        )


def test_bundle_orders_retrospective_historical_and_coaching_attachments() -> None:
    bundle = ApplicationProvenanceBundle(
        workflow=WorkflowV1.HISTORICAL_GAME,
        attachments=[
            _attachment("historical_game_result"),
            _attachment("replay_coaching/report"),
            _attachment("historical_decision/10/assessment"),
            _attachment("historical_search_review_summary"),
            _attachment("historical_decision/2/analysis"),
            _attachment("replay_coaching/guidance"),
            _attachment("historical_snapshot_summary"),
            _attachment("historical_decision/2/input"),
            _attachment("replay_coaching/prioritization"),
            _attachment("historical_immediate_review_summary"),
            _attachment("historical_decision/2/assessment"),
            _attachment("historical_decision/10/input"),
            _attachment("historical_decision/10/analysis"),
        ],
    )
    assert [attachment.name for attachment in bundle.attachments] == [
        "historical_decision/2/input",
        "historical_decision/2/analysis",
        "historical_decision/2/assessment",
        "historical_decision/10/input",
        "historical_decision/10/analysis",
        "historical_decision/10/assessment",
        "historical_snapshot_summary",
        "historical_immediate_review_summary",
        "historical_search_review_summary",
        "replay_coaching/prioritization",
        "replay_coaching/guidance",
        "replay_coaching/report",
        "historical_game_result",
    ]


def test_bundle_orders_dataset_preparation_opponent_and_list_families() -> None:
    bundle = ApplicationProvenanceBundle(
        workflow=WorkflowV1.TRAINING_DATASET,
        attachments=[
            _attachment("historical_list_comparison_result"),
            _attachment("historical_list_comparison/pair/10"),
            _attachment("historical_list_comparison/pair/2"),
            _attachment("historical_list/entry/10"),
            _attachment("historical_list/entry/2"),
            _attachment("opponent_statistics/profile/10"),
            _attachment("opponent_statistics/profile/2"),
            _attachment("dataset_preparation/source/10"),
            _attachment("dataset_preparation/source/2"),
            _attachment("training_dataset_result"),
            _attachment("training_dataset/search/1/10/actual"),
            _attachment("training_dataset/search/1/2/search"),
            _attachment("training_dataset/sample/1/10/target"),
            _attachment("training_dataset/sample/1/2/feature"),
            _attachment("training_dataset/record/10"),
            _attachment("training_dataset/record/2"),
            _attachment("training_dataset/input"),
        ],
    )

    assert [attachment.name for attachment in bundle.attachments] == [
        "training_dataset/input",
        "training_dataset/record/2",
        "training_dataset/record/10",
        "training_dataset/sample/1/2/feature",
        "training_dataset/sample/1/10/target",
        "training_dataset/search/1/2/search",
        "training_dataset/search/1/10/actual",
        "training_dataset_result",
        "dataset_preparation/source/2",
        "dataset_preparation/source/10",
        "opponent_statistics/profile/2",
        "opponent_statistics/profile/10",
        "historical_list/entry/2",
        "historical_list/entry/10",
        "historical_list_comparison/pair/2",
        "historical_list_comparison/pair/10",
        "historical_list_comparison_result",
    ]


def test_application_result_defaults_to_no_provenance_and_validates_workflow() -> None:
    result = ResultDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document={"input_file": "fixture"},
    )
    execution = ApplicationExecutionResult(result=result)
    assert execution.provenance is None

    wrong_bundle = ApplicationProvenanceBundle(
        workflow=WorkflowV1.HISTORICAL_GAME,
        attachments=(_attachment(),),
    )
    with pytest.raises(SkatMindValidationError, match="workflow"):
        ApplicationExecutionResult(result=result, provenance=wrong_bundle)
