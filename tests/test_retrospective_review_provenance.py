import copy
import json
from pathlib import Path

import pytest

from skat_ai.application import (
    ApplicationExecutionOptions,
    PositionAnalysisApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.errors import SkatAIInformationPolicyError
from skat_ai.retrospective_review_provenance import (
    RETROSPECTIVE_REVIEW_PROVENANCE_VERSION,
    validate_retrospective_provenance_dependency,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "generated_output_schema"


def _load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def _execute(document: dict[str, object]):
    return execute_application_invocation(
        build_application_invocation(
            document,
            input_reference="memory://retrospective-position",
            options=ApplicationExecutionOptions(
                position_analysis=PositionAnalysisApplicationOptions(
                    sample_count_override=1,
                    random_seed_override=42,
                )
            ),
        )
    )


def test_flat_review_separates_input_analysis_actual_and_assessment() -> None:
    execution = _execute(_load("grand_post_game_mistake_actual_card.json"))
    assert execution.provenance is not None
    attachments = execution.provenance.attachments

    assert RETROSPECTIVE_REVIEW_PROVENANCE_VERSION == 1
    assert [attachment.name for attachment in attachments] == [
        "flat_retrospective/input",
        "flat_retrospective/analysis",
        "flat_retrospective/assessment",
        "position_result",
    ]
    input_attachment, analysis, assessment, result = attachments
    assert input_attachment.coverage_summary.provenance_complete is True
    assert analysis.coverage_summary.provenance_complete is True
    assert assessment.coverage_summary.provenance_complete is True
    assert "actual_card" not in json.dumps(input_attachment.document_to_dict())
    assert "actual_card" not in json.dumps(analysis.document_to_dict())
    assert assessment.document["actual_card_played"] == "S9"
    actual_entry = next(
        entry
        for entry in assessment.ledger.entries
        if entry.field_path == "/actual_card_played"
    )
    assert (
        actual_entry.origin,
        actual_entry.derivation,
        actual_entry.visibility,
        actual_entry.available_from,
    ) == (
        "retrospective_attachment",
        "retrospective",
        "public",
        "after_actual_play",
    )
    assert not any(
        exemption.field_path == "/post_game_review_summary"
        for exemption in result.ledger.exemptions
    )


def test_flat_search_review_reuses_search_mapping_and_tracks_both_review_branches() -> None:
    execution = _execute(_load("grand_bounded_search_post_game_review.json"))
    assert execution.provenance is not None
    analysis = execution.provenance.attachments[1]
    result = execution.provenance.attachments[-1]

    search_entries = [
        entry
        for entry in analysis.ledger.entries
        if "/primary_analysis/bounded_search_result/" in entry.field_path
    ]
    assert search_entries
    assert any(
        entry.origin == "compatible_world_aggregate" for entry in search_entries
    )
    exempted = {exemption.field_path for exemption in result.ledger.exemptions}
    assert "/post_game_review_summary" not in exempted
    assert "/bounded_search_post_game_review_summary" not in exempted
    assert any(
        entry.field_path.startswith("/bounded_search_post_game_review_summary/")
        for entry in result.ledger.entries
    )


def test_actual_card_change_cannot_change_pre_actual_provenance() -> None:
    first = _load("grand_post_game_mistake_actual_card.json")
    second = copy.deepcopy(first)
    second["actual_card_played"] = "S10"

    first_execution = _execute(first)
    second_execution = _execute(second)
    assert first_execution.provenance is not None
    assert second_execution.provenance is not None

    for index in (0, 1):
        first_attachment = first_execution.provenance.attachments[index]
        second_attachment = second_execution.provenance.attachments[index]
        assert first_attachment.document == second_attachment.document
        assert first_attachment.ledger == second_attachment.ledger
        assert (
            first_attachment.coverage_summary
            == second_attachment.coverage_summary
        )
    assert (
        first_execution.provenance.attachments[2].document
        != second_execution.provenance.attachments[2].document
    )


def test_flat_review_keeps_multi_step_outside_retrospective_decision_hooks() -> None:
    document = json.loads(
        (FIXTURES / "grand_unsupported_multi_step_phase.json").read_text(
            encoding="utf-8"
        )
    )
    execution = execute_application_invocation(
        build_application_invocation(
            document,
            input_reference="memory://retrospective-multi-step",
            options=ApplicationExecutionOptions(
                position_analysis=PositionAnalysisApplicationOptions(
                    sample_count_override=1,
                    random_seed_override=42,
                    multi_step_count=1,
                    card_selection_policy="highest_point",
                    expected_value_sample_count=20,
                )
            ),
        )
    )

    assert execution.result.document["multi_step_result"]["stop_reason"] == (
        "Requested step count reached."
    )
    assert execution.provenance is not None
    assert [attachment.name for attachment in execution.provenance.attachments] == [
        "flat_retrospective/input",
        "flat_retrospective/analysis",
        "flat_retrospective/assessment",
        "position_result",
    ]


@pytest.mark.parametrize(
    ("consumer", "dependency"),
    [
        ("decision_time_analysis", "actual_card_attachment"),
        ("retrospective_assessment", "final_report"),
        ("prioritization", "guidance"),
        ("guidance", "final_report"),
    ],
)
def test_retrospective_temporal_dependencies_reject_backward_use(
    consumer: str,
    dependency: str,
) -> None:
    with pytest.raises(SkatAIInformationPolicyError):
        validate_retrospective_provenance_dependency(
            consumer_stage=consumer,
            dependency_stage=dependency,
            path="/forbidden",
        )
