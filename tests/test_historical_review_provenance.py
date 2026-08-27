import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_historical_game import build_historical_input, rebuild_historical_suffix
from test_replay_coaching_prioritization import _zero_decision_data

from skat_ai.application import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    HistoricalGameApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.field_provenance import build_serializable_field_provenance_ledger
from skat_ai.field_provenance_policy import (
    redact_field_provenance_ledger_for_public_output,
)
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skat_ai.historical_review_provenance import (
    HistoricalReviewProvenanceCollector,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def _execute(
    document: dict[str, object],
    options: HistoricalGameApplicationOptions,
    *,
    external_documents: ApplicationExternalDocuments | None = None,
):
    return execute_application_invocation(
        build_application_invocation(
            document,
            input_reference="memory://historical-review",
            options=ApplicationExecutionOptions(historical_game=options),
            external_documents=external_documents,
        )
    )


def _attachment(execution, name: str):
    assert execution.provenance is not None
    return next(
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name == name
    )


def test_snapshot_inputs_use_acting_player_perspective_and_separate_actual_cards() -> None:
    execution = _execute(
        _load("historical_grand_normal_completion.json"),
        HistoricalGameApplicationOptions(decision_snapshots=True),
    )
    assert execution.provenance is not None
    inputs = [
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name.endswith("/input")
    ]

    assert len(inputs) == 30
    assert inputs[0].name == "historical_decision/1/input"
    assert inputs[-1].name == "historical_decision/30/input"
    for attachment in inputs:
        document = attachment.document_to_dict()
        assert "actual_card_played" not in document
        assert "seed" not in json.dumps(document, sort_keys=True).lower()
        assert document["information_policy"] == "decision_time"
        assert document["information_cutoff"] == "before_actual_play"
        assert document["relative_player_map"]["me"] == document["acting_player_id"]
        hand_entry = next(
            entry
            for entry in attachment.ledger.entries
            if entry.field_path.startswith("/visible_state/own_hand")
        )
        assert hand_entry.visibility == "local_private"
        assert hand_entry.perspective_player_id == document["acting_player_id"]
        assert attachment.coverage_summary.provenance_complete is True

    snapshot = _attachment(execution, "historical_snapshot_summary")
    actual_entry = next(
        entry
        for entry in snapshot.ledger.entries
        if entry.field_path == "/snapshots/0/actual_card_played"
    )
    assert (
        actual_entry.origin,
        actual_entry.available_from,
        actual_entry.available_from_decision_index,
    ) == ("retrospective_attachment", "after_actual_play", 1)
    root = execution.provenance.attachments[-1]
    assert root.name == "historical_game_result"
    assert root.ledger.status == "complete"
    assert root.ledger.exemptions == ()
    assert root.ledger.limitations == ()
    assert root.coverage_summary.provenance_complete is True
    assert root.coverage_summary.all_paths_accounted_for is True


def test_immediate_review_retains_one_analysis_and_assessment_per_decision() -> None:
    execution = _execute(
        _load("historical_grand_normal_completion.json"),
        HistoricalGameApplicationOptions(
            immediate_review=True,
            immediate_sample_count=1,
            immediate_base_random_seed=42,
        ),
    )
    assert execution.provenance is not None
    names = [attachment.name for attachment in execution.provenance.attachments]

    assert sum(name.endswith("/input") for name in names) == 30
    assert sum(name.endswith("/analysis") for name in names) == 30
    assert sum(name.endswith("/assessment") for name in names) == 30
    assert names[-3:] == [
        "historical_snapshot_summary",
        "historical_immediate_review_summary",
        "historical_game_result",
    ]
    assert "decision_snapshot_summary" not in execution.result.document[
        "historical_game_summary"
    ]
    analysis = _attachment(execution, "historical_decision/1/analysis")
    assessment = _attachment(execution, "historical_decision/1/assessment")
    assert "actual_card" not in json.dumps(analysis.document_to_dict())
    assert assessment.document["immediate_review"]["actual_card_played"] == "CA"
    assert analysis.information_use_context.stage == "decision_time"
    assert assessment.information_use_context.stage == "after_actual_play"
    assert analysis.coverage_summary.provenance_complete is True
    assert assessment.coverage_summary.provenance_complete is True


@pytest.mark.parametrize("decision_count", range(31))
def test_historical_input_provenance_supports_zero_through_thirty_decisions(
    decision_count: int,
) -> None:
    record = build_historical_game_record(build_historical_input())
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )
    truncated = replace(
        snapshots,
        snapshot_count=decision_count,
        snapshots=snapshots.snapshots[:decision_count],
    )
    collector = HistoricalReviewProvenanceCollector(external_reference=None)
    collector.capture_decision_inputs(
        truncated,
        effective_review_settings={"decision_snapshots": True},
    )
    bundle = collector.build_bundle(
        {
            "input_file": "memory://cardinality",
            "historical_game_summary": {"status": "complete"},
        }
    )
    assert sum(
        attachment.name.endswith("/input") for attachment in bundle.attachments
    ) == decision_count
    assert bundle.attachments[-1].name == "historical_game_result"


@pytest.mark.parametrize(
    "example_name",
    [
        "historical_grand_declarer_concession.json",
        "historical_grand_defender_concession.json",
        "historical_grand_declarer_card_exposure.json",
        "historical_grand_defender_open_play.json",
        "historical_grand_open_card_throw.json",
    ],
)
def test_shortened_and_incomplete_prefix_snapshots_have_complete_provenance(
    example_name: str,
) -> None:
    execution = _execute(
        _load(example_name),
        HistoricalGameApplicationOptions(decision_snapshots=True),
    )
    assert execution.provenance is not None
    inputs = [
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name.endswith("/input")
    ]
    result = execution.result.to_dict()["document"]["historical_game_summary"]
    assert len(inputs) == result["decision_snapshot_summary"]["snapshot_count"]
    assert all(
        attachment.coverage_summary.provenance_complete
        for attachment in inputs
    )


@pytest.mark.parametrize(
    "example_name",
    [
        "historical_grand_defender_open_play_continuation.json",
        "historical_grand_declarer_card_exposure_continuation.json",
    ],
)
def test_continuation_hands_enter_inputs_only_after_the_event(
    example_name: str,
) -> None:
    execution = _execute(
        _load(example_name),
        HistoricalGameApplicationOptions(decision_snapshots=True),
    )
    assert execution.provenance is not None
    inputs = [
        attachment.document_to_dict()
        for attachment in execution.provenance.attachments
        if attachment.name.endswith("/input")
    ]
    first_exposed = next(
        index
        for index, document in enumerate(inputs)
        if document["visible_state"]["public_exposed_cards"]
    )
    assert first_exposed > 0
    assert all(
        not document["visible_state"]["public_exposed_cards"]
        for document in inputs[:first_exposed]
    )
    exposed_counts = [
        len(document["visible_state"]["public_exposed_cards"][0]["cards"])
        for document in inputs[first_exposed:]
    ]
    assert exposed_counts == sorted(exposed_counts, reverse=True)


def test_external_historical_profile_provenance_uses_only_opaque_reference() -> None:
    reference = "private-historical-profile-reference"
    execution = _execute(
        _load("historical_grand_normal_completion.json"),
        HistoricalGameApplicationOptions(
            immediate_review=True,
            immediate_sample_count=1,
            use_profile_presets_override=True,
        ),
        external_documents=ApplicationExternalDocuments(
            opponent_statistics_document=_load(
                "historical_opponent_statistics.json"
            ),
            opponent_statistics_reference=reference,
        ),
    )
    first = _attachment(execution, "historical_decision/1/input")
    assert "external_profile_application" in first.document
    assert reference in repr(first.ledger)
    redacted = redact_field_provenance_ledger_for_public_output(first.ledger)
    serialized = json.dumps(
        build_serializable_field_provenance_ledger(redacted),
        sort_keys=True,
    )
    assert reference not in serialized
    assert "private_dependencies_redacted" in serialized
    assert "records" not in json.dumps(first.document_to_dict()).lower()


def test_future_suffix_changes_do_not_change_earlier_input_or_analysis() -> None:
    original = build_historical_input()
    changed = rebuild_historical_suffix(original, completed_prefix_tricks=5)
    options = HistoricalGameApplicationOptions(
        immediate_review=True,
        immediate_sample_count=1,
        immediate_base_random_seed=42,
    )
    first = _execute({"historical_game_input": original}, options)
    second = _execute({"historical_game_input": changed}, options)

    for stage in ("input", "analysis"):
        first_attachment = _attachment(
            first,
            f"historical_decision/15/{stage}",
        )
        second_attachment = _attachment(
            second,
            f"historical_decision/15/{stage}",
        )
        assert first_attachment.document == second_attachment.document
        assert first_attachment.ledger == second_attachment.ledger


def test_zero_decision_historical_coaching_still_builds_aggregate_attachments() -> None:
    execution = _execute(
        {"historical_game_input": _zero_decision_data()},
        HistoricalGameApplicationOptions(
            replay_coaching=True,
            search_seed=71,
            immediate_sample_count=1,
        ),
    )
    assert execution.provenance is not None
    assert [attachment.name for attachment in execution.provenance.attachments] == [
        "replay_coaching/prioritization",
        "replay_coaching/guidance",
        "replay_coaching/report",
        "historical_game_result",
    ]
