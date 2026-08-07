import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_historical_game_event_chain import (
    CONTINUATION_KINDS,
    TERMINAL_BUILDERS,
    add_continuation,
)

import skat_ai.application.historical_game_workflow as historical_workflow_module
import skat_ai.application.position_workflow as position_workflow_module
from skat_ai.application import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.errors import SkatAIInformationPolicyError
from skat_ai.field_provenance import build_serializable_field_provenance_ledger
from skat_ai.field_provenance_policy import (
    redact_field_provenance_ledger_for_public_output,
)
from skat_ai.historical_result_provenance import (
    COMPLETE_RESULT_PROVENANCE_VERSION as HISTORICAL_COMPLETE_VERSION,
)
from skat_ai.historical_result_provenance import (
    build_historical_game_result_attachment,
    validate_historical_result_provenance_dependencies,
)
from skat_ai.position_result_provenance import (
    COMPLETE_RESULT_PROVENANCE_VERSION as POSITION_COMPLETE_VERSION,
)
from skat_ai.position_result_provenance import (
    validate_position_result_provenance_dependencies,
)
from skat_ai.settlement_result_provenance import COMPLETE_RESULT_PROVENANCE_VERSION

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def _load(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _execute_position(
    name: str,
    *,
    options: PositionAnalysisApplicationOptions | None = None,
):
    document = _load(name)
    return execute_application_invocation(
        build_application_invocation(
            document,
            input_reference=f"memory://{name}",
            options=ApplicationExecutionOptions(
                position_analysis=(
                    options
                    or PositionAnalysisApplicationOptions(
                        sample_count_override=1,
                        random_seed_override=42,
                    )
                )
            ),
        )
    )


def _execute_historical_document(
    document: dict[str, object],
    *,
    options: HistoricalGameApplicationOptions | None = None,
):
    return execute_application_invocation(
        build_application_invocation(
            document,
            input_reference="memory://historical-result",
            options=ApplicationExecutionOptions(
                historical_game=options or HistoricalGameApplicationOptions()
            ),
        )
    )


def _result_attachment(execution):
    assert execution.provenance is not None
    return execution.provenance.attachments[-1]


def _assert_complete(attachment) -> None:
    assert attachment.ledger.status == "complete"
    assert attachment.ledger.exemptions == ()
    assert attachment.ledger.limitations == ()
    assert attachment.coverage_summary.provenance_complete is True
    assert attachment.coverage_summary.all_paths_accounted_for is True
    assert attachment.coverage_summary.uncovered_paths == ()
    assert attachment.coverage_summary.orphaned_entry_paths == ()
    assert attachment.coverage_summary.overlapping_paths == ()


def test_complete_result_provenance_version_is_internal_version_one() -> None:
    assert COMPLETE_RESULT_PROVENANCE_VERSION == 1
    assert POSITION_COMPLETE_VERSION == 1
    assert HISTORICAL_COMPLETE_VERSION == 1


@pytest.mark.parametrize(
    "example_name",
    [
        "grand_second_position.json",
        "grand_overbid_declarer_card_points_win.json",
        "null_impossible_declaration_settlement.json",
        "grand_complete_declarer_win.json",
        "grand_list_performance_input.json",
        "grand_list_game_contributions.json",
        "grand_list_analysis_results.json",
        "grand_list_standings_input.json",
        "declarer_concession.json",
        "defender_concession.json",
        "declarer_card_exposure.json",
        "defender_open_play.json",
        "open_card_throw.json",
        "declarer_card_exposure_continuation.json",
        "defender_open_play_continuation.json",
    ],
)
def test_all_position_result_families_have_complete_non_legacy_ledgers(
    example_name: str,
) -> None:
    execution = _execute_position(example_name)
    attachment = _result_attachment(execution)

    assert attachment.name == "position_result"
    assert attachment.document_to_dict() == execution.result.to_dict()["document"]
    _assert_complete(attachment)


def test_position_value_result_settlement_and_performance_dependencies_are_forward_only() -> None:
    attachment = _result_attachment(_execute_position("grand_complete_declarer_win.json"))
    entries = {entry.field_path: entry for entry in attachment.ledger.entries}

    assert entries["/game_declaration/matadors"].origin in {
        "validated_copy",
        "structural_inference",
    }
    assert all(
        dependency.startswith("/game_declaration/")
        for dependency in entries["/game_value_summary/game_value"].dependency_paths
    )
    assert "/game_value_summary/game_value" in entries[
        "/overbid_summary/status"
    ].dependency_paths
    assert set(entries["/score_summary/total_declarer_points"].dependency_paths) == {
        "/score_summary/completed_trick_declarer_points",
        "/score_summary/explicit_declarer_points",
    }
    assert any(
        dependency.startswith("/score_summary/")
        for dependency in entries["/game_result_summary/winner"].dependency_paths
    )
    assert any(
        dependency.startswith("/game_result_summary/")
        for dependency in entries[
            "/adjusted_game_result_summary/winner"
        ].dependency_paths
    )
    settlement_dependencies = entries[
        "/final_settlement_summary/settlement_score"
    ].dependency_paths
    assert any(
        dependency.startswith("/adjusted_game_result_summary/")
        for dependency in settlement_dependencies
    )
    assert any(
        dependency.startswith("/game_value_summary/")
        for dependency in settlement_dependencies
    )
    assert any(
        dependency.startswith("/overbid_summary/")
        for dependency in settlement_dependencies
    )
    assert all(
        dependency.startswith("/final_settlement_summary/")
        for dependency in entries[
            "/performance_rating_summary/game_outcome"
        ].dependency_paths
    )


@pytest.mark.parametrize(
    ("example_name", "expected_rule_reference"),
    [
        ("declarer_concession.json", "structured_shortening.declarer_concession"),
        ("defender_concession.json", "structured_shortening.defender_concession"),
        (
            "declarer_card_exposure.json",
            "structured_shortening.declarer_card_exposure",
        ),
        ("defender_open_play.json", "structured_shortening.defender_open_play"),
        ("open_card_throw.json", "structured_shortening.open_card_throw"),
    ],
)
def test_position_terminal_endings_use_stable_normative_references(
    example_name: str,
    expected_rule_reference: str,
) -> None:
    attachment = _result_attachment(_execute_position(example_name))
    ending_entries = [
        entry
        for entry in attachment.ledger.entries
        if entry.field_path.startswith("/game_shortening_summary")
    ]

    assert ending_entries
    assert all(entry.available_from == "game_end" for entry in ending_entries)
    assert all(entry.visibility == "post_game_only" for entry in ending_entries)
    assert all(
        expected_rule_reference
        in {reference.reference_id for reference in entry.source_references}
        for entry in ending_entries
    )


@pytest.mark.parametrize(
    "example_name",
    [
        "declarer_card_exposure_continuation.json",
        "defender_open_play_continuation.json",
    ],
)
def test_position_continuations_are_non_adjudicating_dependencies(
    example_name: str,
) -> None:
    attachment = _result_attachment(_execute_position(example_name))
    entries = [
        entry
        for entry in attachment.ledger.entries
        if entry.field_path.startswith("/game_continuation_summary")
    ]

    assert entries
    assert all(entry.available_from == "current_decision" for entry in entries)
    assert all(
        not dependency.startswith(
            (
                "/game_result_summary",
                "/adjusted_game_result_summary",
                "/final_settlement_summary",
            )
        )
        for entry in entries
        for dependency in entry.dependency_paths
    )


def test_position_dependency_validator_rejects_reverse_settlement_input() -> None:
    attachment = _result_attachment(_execute_position("grand_second_position.json"))
    entries = list(attachment.ledger.entries)
    index = next(
        index
        for index, entry in enumerate(entries)
        if entry.field_path == "/game_value_summary/game_value"
    )
    entries[index] = replace(
        entries[index],
        dependency_paths=("/final_settlement_summary/settlement_score",),
    )

    with pytest.raises(SkatAIInformationPolicyError, match="cross-domain"):
        validate_position_result_provenance_dependencies(tuple(entries))


def test_position_private_proof_reference_is_redacted_without_mutating_source() -> None:
    attachment = _result_attachment(_execute_position("defender_open_play.json"))
    original = attachment.ledger
    assert "defender_open_play_exact_proof_v1" in repr(original)

    redacted = redact_field_provenance_ledger_for_public_output(original)
    serialized = json.dumps(
        build_serializable_field_provenance_ledger(redacted),
        sort_keys=True,
    ).lower()

    assert attachment.ledger is original
    assert "defender_open_play_exact_proof_v1" not in serialized
    assert "private_dependencies_redacted" in serialized
    for forbidden in (
        "exact_search_state",
        "principal_variation",
        "hidden_ownership",
        "private_seed",
        "private_sentinel",
    ):
        assert forbidden not in serialized


def test_position_core_result_branches_do_not_depend_on_analysis_domains() -> None:
    attachment = _result_attachment(_execute_position("grand_bounded_search_exhaustive.json"))
    core_prefixes = (
        "/game_declaration",
        "/game_value_summary",
        "/overbid_summary",
        "/score_summary",
        "/game_result_summary",
        "/adjusted_game_result_summary",
        "/final_settlement_summary",
    )
    forbidden = (
        "/bounded_search_result",
        "/post_game_review_summary",
        "/performance_rating_summary",
        "/list_",
    )

    assert all(
        not dependency.startswith(forbidden)
        for entry in attachment.ledger.entries
        if entry.field_path.startswith(core_prefixes)
        for dependency in entry.dependency_paths
    )


@pytest.mark.parametrize(
    "example_name",
    [
        "historical_grand_normal_completion.json",
        "historical_grand_declarer_concession.json",
        "historical_grand_defender_concession.json",
        "historical_grand_declarer_card_exposure.json",
        "historical_grand_defender_open_play.json",
        "historical_grand_open_card_throw.json",
        "historical_grand_defender_open_play_continuation.json",
        "historical_grand_declarer_card_exposure_continuation.json",
        "historical_grand_defender_open_play_continuation_declarer_concession.json",
        "historical_grand_declarer_card_exposure_continuation_defender_concession.json",
    ],
)
def test_historical_result_families_have_complete_non_legacy_ledgers(
    example_name: str,
) -> None:
    execution = _execute_historical_document(_load(example_name))
    attachment = _result_attachment(execution)

    assert [item.name for item in execution.provenance.attachments] == [
        "historical_game_result"
    ]
    assert attachment.name == "historical_game_result"
    assert attachment.document_to_dict() == execution.result.to_dict()["document"]
    _assert_complete(attachment)


def test_historical_record_tricks_points_result_and_settlement_are_chronological() -> None:
    attachment = _result_attachment(
        _execute_historical_document(_load("historical_grand_normal_completion.json"))
    )
    entries = {entry.field_path: entry for entry in attachment.ledger.entries}

    first_actual = entries[
        "/historical_game_summary/record/tricks/0/plays/0/card"
    ]
    first_winner = entries[
        "/historical_game_summary/derived_tricks/0/winner_player_id"
    ]
    assert first_actual.available_from == "after_actual_play"
    assert first_actual.available_from_decision_index == 1
    assert first_winner.available_from_decision_index == 3
    assert all(
        "/record/tricks/1/" not in dependency
        for dependency in first_winner.dependency_paths
    )
    assert entries["/historical_game_summary/declarer_points"].available_from == (
        "game_end"
    )
    settlement = entries[
        "/historical_game_summary/final_settlement_summary/settlement_score"
    ]
    assert any(
        dependency.startswith("/historical_game_summary/game_result_summary/")
        for dependency in settlement.dependency_paths
    )
    assert any(
        dependency.startswith("/historical_game_summary/game_value_summary/")
        for dependency in settlement.dependency_paths
    )
    assert any(
        dependency.startswith("/historical_game_summary/overbid_summary/")
        for dependency in settlement.dependency_paths
    )


def test_historical_incomplete_final_trick_has_no_winner_provenance() -> None:
    attachment = _result_attachment(
        _execute_historical_document(_load("historical_grand_declarer_concession.json"))
    )
    paths = {entry.field_path for entry in attachment.ledger.entries}

    assert any(
        path.startswith("/historical_game_summary/incomplete_current_trick/")
        for path in paths
    )
    assert not any(
        path.startswith("/historical_game_summary/incomplete_current_trick/")
        and "winner" in path
        for path in paths
    )


@pytest.mark.parametrize("continuation_kind", CONTINUATION_KINDS)
@pytest.mark.parametrize("terminal_kind", TERMINAL_BUILDERS)
def test_historical_all_continuation_terminal_combinations_remain_complete(
    continuation_kind: str,
    terminal_kind: str,
) -> None:
    data = add_continuation(TERMINAL_BUILDERS[terminal_kind](), continuation_kind)
    attachment = _result_attachment(
        _execute_historical_document({"historical_game_input": data})
    )
    _assert_complete(attachment)

    event_entries = [
        entry
        for entry in attachment.ledger.entries
        if entry.field_path.startswith(
            "/historical_game_summary/historical_game_events_summary"
        )
    ]
    assert event_entries
    assert all(
        not dependency.startswith(
            (
                "/historical_game_summary/game_result_summary",
                "/historical_game_summary/final_settlement_summary",
            )
        )
        for entry in event_entries
        for dependency in entry.dependency_paths
    )


def test_historical_dependency_validator_rejects_later_trick_and_review_inputs() -> None:
    execution = _execute_historical_document(
        _load("historical_grand_normal_completion.json"),
        options=HistoricalGameApplicationOptions(decision_snapshots=True),
    )
    attachment = _result_attachment(execution)
    entries = list(attachment.ledger.entries)
    first_index = next(
        index
        for index, entry in enumerate(entries)
        if entry.field_path
        == "/historical_game_summary/derived_tricks/0/winner_player_id"
    )
    first_entry = entries[first_index]
    entries[first_index] = replace(
        first_entry,
        dependency_paths=(
            "/historical_game_summary/record/tricks/1/plays/0/card",
        ),
    )
    with pytest.raises(SkatAIInformationPolicyError, match="later play"):
        validate_historical_result_provenance_dependencies(tuple(entries))
    entries[first_index] = first_entry

    settlement_index = next(
        index
        for index, entry in enumerate(entries)
        if entry.field_path
        == "/historical_game_summary/final_settlement_summary/settlement_score"
    )
    entries[settlement_index] = replace(
        entries[settlement_index],
        dependency_paths=(
            "/historical_game_summary/decision_snapshot_summary/snapshot_count",
        ),
    )
    with pytest.raises(SkatAIInformationPolicyError, match="cross-domain"):
        validate_historical_result_provenance_dependencies(tuple(entries))


def test_historical_private_replay_and_proof_references_are_redactable() -> None:
    attachment = _result_attachment(
        _execute_historical_document(_load("historical_grand_defender_open_play.json"))
    )
    original = attachment.ledger
    assert "defender_open_play_exact_proof_v1" in repr(original)
    assert "historical_remaining_card_reconstruction_v1" in repr(original)

    redacted = redact_field_provenance_ledger_for_public_output(original)
    serialized = json.dumps(
        build_serializable_field_provenance_ledger(redacted),
        sort_keys=True,
    ).lower()

    assert attachment.ledger is original
    assert "defender_open_play_exact_proof_v1" not in serialized
    assert "historical_remaining_card_reconstruction_v1" not in serialized
    assert "private_dependencies_redacted" in serialized
    for forbidden in (
        "exact_search_state",
        "principal_variation",
        "hidden_ownership",
        "private_seed",
        "private_sentinel",
    ):
        assert forbidden not in serialized


def test_result_builders_reject_unknown_root_and_summary_branches() -> None:
    execution = _execute_historical_document(
        _load("historical_grand_normal_completion.json")
    )
    document = execution.result.to_dict()["document"]
    document["unknown"] = True
    with pytest.raises(ValueError, match="Untracked Historical Result keys"):
        build_historical_game_result_attachment(
            document,
            external_reference=None,
        )

    document.pop("unknown")
    document["historical_game_summary"]["unknown"] = True
    with pytest.raises(ValueError, match="summary keys"):
        build_historical_game_result_attachment(
            document,
            external_reference=None,
        )


def test_complete_result_provenance_adds_no_core_position_builder_calls(
    monkeypatch,
) -> None:
    names = (
        "build_position_from_document",
        "get_game_declaration_from_input",
        "build_game_value_summary",
        "build_overbid_summary",
        "build_score_summary",
        "build_game_result_summary_from_score_summary",
        "apply_remaining_points_assignment",
        "build_final_settlement_summary",
        "build_performance_rating_summary",
    )
    counts = {name: 0 for name in names}
    for name in names:
        original = getattr(position_workflow_module, name)

        def counted(*args, _name=name, _original=original, **kwargs):
            counts[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(position_workflow_module, name, counted)

    execution = _execute_position("grand_complete_declarer_win.json")

    _assert_complete(_result_attachment(execution))
    assert counts == {name: 1 for name in names}


def test_complete_result_provenance_adds_no_ending_or_list_builder_calls(
    monkeypatch,
) -> None:
    counts = {"ending": 0, "list": 0}
    real_ending = position_workflow_module.adjudicate_defender_open_play
    real_list = position_workflow_module.build_list_standings_summary

    def counted_ending(*args, **kwargs):
        counts["ending"] += 1
        return real_ending(*args, **kwargs)

    def counted_list(*args, **kwargs):
        counts["list"] += 1
        return real_list(*args, **kwargs)

    monkeypatch.setattr(
        position_workflow_module,
        "adjudicate_defender_open_play",
        counted_ending,
    )
    monkeypatch.setattr(
        position_workflow_module,
        "build_list_standings_summary",
        counted_list,
    )

    ending_execution = _execute_position("defender_open_play.json")
    list_execution = _execute_position("grand_list_standings_input.json")

    _assert_complete(_result_attachment(ending_execution))
    _assert_complete(_result_attachment(list_execution))
    assert counts == {"ending": 1, "list": 1}


def test_complete_result_provenance_adds_no_historical_parse_or_summary_call(
    monkeypatch,
) -> None:
    counts = {"record": 0, "summary": 0}
    real_record = historical_workflow_module.build_historical_game_from_document
    real_summary = historical_workflow_module.build_historical_game_summary

    def counted_record(*args, **kwargs):
        counts["record"] += 1
        return real_record(*args, **kwargs)

    def counted_summary(*args, **kwargs):
        counts["summary"] += 1
        return real_summary(*args, **kwargs)

    monkeypatch.setattr(
        historical_workflow_module,
        "build_historical_game_from_document",
        counted_record,
    )
    monkeypatch.setattr(
        historical_workflow_module,
        "build_historical_game_summary",
        counted_summary,
    )

    execution = _execute_historical_document(
        _load("historical_grand_normal_completion.json")
    )

    _assert_complete(_result_attachment(execution))
    assert counts == {"record": 1, "summary": 1}


def test_complete_result_ledgers_are_deterministic_for_equal_execution() -> None:
    first_position = _result_attachment(_execute_position("grand_second_position.json"))
    second_position = _result_attachment(_execute_position("grand_second_position.json"))
    assert first_position.document == second_position.document
    assert first_position.ledger == second_position.ledger

    historical_document = _load("historical_grand_normal_completion.json")
    first_historical = _result_attachment(
        _execute_historical_document(historical_document)
    )
    second_historical = _result_attachment(
        _execute_historical_document(historical_document)
    )
    assert first_historical.document == second_historical.document
    assert first_historical.ledger == second_historical.ledger
