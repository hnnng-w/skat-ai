import json
from pathlib import Path

import pytest
from test_historical_game_event_chain import TERMINAL_BUILDERS, add_continuation
from test_historical_search_review import _fake_immediate, _fake_search
from test_replay_coaching_contracts import _assessment, _evidence
from test_search_provenance import _result, _unavailable

from skatmind.application import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skatmind.replay_coaching_provenance import (
    REPLAY_COACHING_PROVENANCE_VERSION,
    build_replay_coaching_assessment_attachment,
    build_replay_coaching_decision_time_attachment,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def _execute(document: dict[str, object]):
    return execute_application_invocation(
        build_application_invocation(
            document,
            input_reference="memory://replay-coaching",
            options=ApplicationExecutionOptions(
                historical_game=HistoricalGameApplicationOptions(
                    search_review=True,
                    replay_coaching=True,
                    search_seed=71,
                    immediate_sample_count=1,
                    immediate_base_random_seed=42,
                )
            ),
        )
    )


def _attachment(execution, name: str):
    assert execution.provenance is not None
    return next(
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name == name
    )


@pytest.mark.parametrize(
    "search_result",
    [
        _result(coverage="all_compatible_worlds"),
        _result(coverage="sampled_compatible_worlds"),
        _result(
            status="partial",
            stop_reason="node_budget_exhausted",
            completed=2,
            selected=3,
        ),
        _result(
            status="timeout",
            stop_reason="wall_clock_timeout",
            completed=2,
            selected=3,
        ),
        _unavailable(),
    ],
)
def test_decision_evidence_and_assessment_provenance_support_every_search_status(
    search_result,
) -> None:
    evidence = _evidence(search_result)
    evidence_attachment = build_replay_coaching_decision_time_attachment(
        name=f"historical_decision/{evidence.decision_index}/analysis",
        evidence=evidence,
    )
    assessment = _assessment(evidence, evidence.legal_cards[-1])
    assessment_attachment = build_replay_coaching_assessment_attachment(
        name=f"historical_decision/{evidence.decision_index}/assessment",
        assessment=assessment,
    )

    assert REPLAY_COACHING_PROVENANCE_VERSION == 1
    assert evidence_attachment.coverage_summary.provenance_complete is True
    assert assessment_attachment.coverage_summary.provenance_complete is True
    assert "actual_card" not in json.dumps(evidence_attachment.document_to_dict())
    actual = next(
        entry
        for entry in assessment_attachment.ledger.entries
        if entry.field_path == "/actual_card"
    )
    assert (actual.origin, actual.available_from) == (
        "retrospective_attachment",
        "after_actual_play",
    )
    search_entries = [
        entry
        for entry in evidence_attachment.ledger.entries
        if entry.field_path.startswith("/bounded_search_result/")
    ]
    assert search_entries
    if search_result.consumed_budget.completed_world_count:
        assert any(
            entry.origin == "compatible_world_aggregate"
            for entry in search_entries
        )


def test_application_coaching_bundle_is_complete_ordered_and_one_pass(
    monkeypatch,
) -> None:
    calls = {"search": 0, "immediate": 0}

    def search(**kwargs):
        calls["search"] += 1
        return _fake_search(**kwargs)

    def immediate(**kwargs):
        calls["immediate"] += 1
        return _fake_immediate(**kwargs)

    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )
    execution = _execute(_load("historical_grand_normal_completion.json"))
    assert execution.provenance is not None
    names = [attachment.name for attachment in execution.provenance.attachments]

    assert calls == {"search": 30, "immediate": 30}
    assert names[:3] == [
        "historical_decision/1/input",
        "historical_decision/1/analysis",
        "historical_decision/1/assessment",
    ]
    assert names[-5:] == [
        "historical_search_review_summary",
        "replay_coaching/prioritization",
        "replay_coaching/guidance",
        "replay_coaching/report",
        "historical_game_result",
    ]
    analysis = _attachment(execution, "historical_decision/1/analysis")
    assessment = _attachment(execution, "historical_decision/1/assessment")
    assert "actual_card" not in json.dumps(analysis.document_to_dict())
    assert assessment.document["historical_search_review"]["actual_card"] == "CA"
    assert "decision_time_evidence" in assessment.document[
        "historical_search_review"
    ]["replay_coaching_assessment"]

    prioritization = _attachment(execution, "replay_coaching/prioritization")
    guidance = _attachment(execution, "replay_coaching/guidance")
    report = _attachment(execution, "replay_coaching/report")
    assert prioritization.coverage_summary.provenance_complete is True
    assert guidance.coverage_summary.provenance_complete is True
    assert report.coverage_summary.provenance_complete is True
    assert "outcome_context" not in prioritization.document
    assert "outcome_context" not in guidance.document
    public_report = execution.result.to_dict()["document"]["historical_game_summary"][
        "historical_replay_coaching_summary"
    ]
    assert report.document_to_dict() == public_report
    outcome_entries = [
        entry
        for entry in report.ledger.entries
        if entry.field_path.startswith("/outcome_context/")
    ]
    assert outcome_entries
    assert {entry.available_from for entry in outcome_entries} == {"game_end"}
    assert {entry.visibility for entry in outcome_entries} == {"post_game_only"}


def test_final_outcome_changes_do_not_change_assessment_prioritization_or_guidance(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    first = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "defender_open_play_continuation",
    )
    second = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](),
        "defender_open_play_continuation",
    )
    second["game_id"] = first["game_id"]
    first_execution = _execute({"historical_game_input": first})
    second_execution = _execute({"historical_game_input": second})

    first_assessments = [
        attachment
        for attachment in first_execution.provenance.attachments
        if attachment.name.endswith("/assessment")
    ]
    second_assessments = [
        attachment
        for attachment in second_execution.provenance.attachments
        if attachment.name.endswith("/assessment")
    ]
    assert [item.document for item in first_assessments] == [
        item.document for item in second_assessments
    ]
    for name in (
        "replay_coaching/prioritization",
        "replay_coaching/guidance",
    ):
        first_attachment = _attachment(first_execution, name)
        second_attachment = _attachment(second_execution, name)
        assert first_attachment.document == second_attachment.document
        assert first_attachment.ledger == second_attachment.ledger
    assert _attachment(first_execution, "replay_coaching/report").document[
        "outcome_context"
    ] != _attachment(second_execution, "replay_coaching/report").document[
        "outcome_context"
    ]


def test_coaching_ledgers_contain_no_engine_private_search_or_deal_details(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    execution = _execute(_load("historical_grand_normal_completion.json"))
    assert execution.provenance is not None
    provenance_tokens = {
        token.lower()
        for attachment in execution.provenance.attachments
        for entry in attachment.ledger.entries
        for path in (
            entry.field_path,
            *entry.dependency_paths,
        )
        for token in path.split("/")
    }
    reference_ids = {
        reference.reference_id.lower()
        for attachment in execution.provenance.attachments
        for entry in attachment.ledger.entries
        for reference in entry.source_references
    }
    for forbidden in (
        "final_hidden_hands",
        "private_remaining_hands",
        "selected_worlds",
        "ownership_assignments",
        "exact_search_state",
        "child_seed",
        "cache",
        "branches",
        "principal_variation",
        "private_profile_record",
        "private_sentinel",
    ):
        matches = sorted(
            value
            for value in (*provenance_tokens, *reference_ids)
            if value == forbidden
        )
        assert not matches, (forbidden, matches)
