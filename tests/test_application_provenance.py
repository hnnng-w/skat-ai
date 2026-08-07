from dataclasses import FrozenInstanceError, fields, replace

import pytest

from skat_ai.api.v1 import ResultDocumentV1, WorkflowV1
from skat_ai.application import (
    APPLICATION_PROVENANCE_VERSION,
    ApplicationExecutionResult,
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.errors import SkatAIValidationError
from skat_ai.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.live_analysis_provenance import (
    LIVE_ANALYSIS_PROVENANCE_VERSION,
    build_live_decision_provenance_attachment,
)
from skat_ai.strategic_metadata import StrategicMetadata


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
    with pytest.raises(SkatAIValidationError, match="does not match"):
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
    with pytest.raises(SkatAIValidationError, match="unique names"):
        ApplicationProvenanceBundle(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            attachments=(attachments[0], attachments[0]),
        )


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
    with pytest.raises(SkatAIValidationError, match="workflow"):
        ApplicationExecutionResult(result=result, provenance=wrong_bundle)
