import json
from collections.abc import Callable
from pathlib import Path

import pytest

import skat_ai.compatible_world_minimax as compatible_world_minimax_module
import skat_ai.information_set_search_executor as information_set_search_executor_module
from skat_ai.application import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.application.execution import ApplicationWorkflowDependencies
from skat_ai.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
)
from skat_ai.errors import SkatAIValidationError
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_tactical_motif_review import (
    build_historical_tactical_motif_review_v1,
)

ROOT = Path(__file__).resolve().parents[1]


def _source() -> dict[str, object]:
    return json.loads(
        (ROOT / "examples" / "historical_grand_normal_completion.json").read_text(encoding="utf-8")
    )


def _execute(
    options: HistoricalGameApplicationOptions,
    *,
    dependencies=None,
    source: dict[str, object] | None = None,
):
    invocation = build_application_invocation(
        _source() if source is None else source,
        input_reference="historical-tactical.json",
        options=ApplicationExecutionOptions(historical_game=options),
    )
    return execute_application_invocation(invocation, dependencies=dependencies)


def _attachment(execution, name: str):
    assert execution.provenance is not None
    return next(
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name == name
    )


def _without_wall_clock_elapsed(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: 0 if key == "wall_clock_elapsed_ms" else _without_wall_clock_elapsed(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_without_wall_clock_elapsed(child) for child in value]
    return value


def _deterministic_timeout_clock() -> Callable[[], float]:
    value = -2.0

    def clock() -> float:
        nonlocal value
        value += 2.0
        return value

    return clock


def _set_deterministic_search_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        compatible_world_minimax_module,
        "_monotonic",
        _deterministic_timeout_clock(),
    )
    monkeypatch.setattr(
        information_set_search_executor_module,
        "_monotonic",
        _deterministic_timeout_clock(),
    )


def test_tactical_review_alone_requires_no_search_or_immediate_settings() -> None:
    execution = _execute(HistoricalGameApplicationOptions(historical_tactical_motif_review=True))
    document = execution.result.to_dict()["document"]
    summary = document["historical_game_summary"]
    review = summary["historical_tactical_motif_review_summary"]

    assert review["source_game_id"] == "historical-grand-001"
    assert review["observation_count"] == 30
    assert "decision_snapshot_summary" not in summary
    assert execution.provenance is not None
    assert "historical_tactical_motif_review_summary" in [
        attachment.name for attachment in execution.provenance.attachments
    ]


def test_tactical_review_reuses_one_snapshot_sequence_when_combined() -> None:
    snapshot_calls = 0
    tactical_calls = 0

    def counted_snapshots(summary):
        nonlocal snapshot_calls
        snapshot_calls += 1
        return build_historical_decision_snapshots(summary)

    def counted_tactical(**kwargs):
        nonlocal tactical_calls
        tactical_calls += 1
        return build_historical_tactical_motif_review_v1(**kwargs)

    dependencies = ApplicationWorkflowDependencies(
        historical_game=HistoricalGameWorkflowDependencies(
            build_snapshots=counted_snapshots,
            build_tactical_motif_review=counted_tactical,
        )
    )
    execution = _execute(
        HistoricalGameApplicationOptions(
            decision_snapshots=True,
            historical_tactical_motif_review=True,
        ),
        dependencies=dependencies,
    )

    assert snapshot_calls == 1
    assert tactical_calls == 1
    summary = execution.result.to_dict()["document"]["historical_game_summary"]
    assert summary["decision_snapshot_summary"]["snapshot_count"] == 30
    assert summary["historical_tactical_motif_review_summary"]["observation_count"] == 30


def test_tactical_option_is_strict_boolean_and_omitted_by_default() -> None:
    with pytest.raises(SkatAIValidationError, match="must be a boolean"):
        HistoricalGameApplicationOptions(
            historical_tactical_motif_review=1  # type: ignore[arg-type]
        )

    execution = _execute(HistoricalGameApplicationOptions())
    summary = execution.result.to_dict()["document"]["historical_game_summary"]
    assert "historical_tactical_motif_review_summary" not in summary


def test_disabled_tactical_review_does_not_change_existing_decision_input() -> None:
    execution = _execute(HistoricalGameApplicationOptions(decision_snapshots=True))
    decision_input = _attachment(execution, "historical_decision/1/input").document_to_dict()

    assert "historical_tactical_motif_review" not in decision_input["effective_review_settings"]


def test_incomplete_final_trick_keeps_partial_provenance_at_recorded_decisions() -> None:
    source = json.loads(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "generated_output_schema"
            / "historical_party_wide_claim_defenders_null_incomplete_trick.json"
        ).read_text(encoding="utf-8")
    )
    execution = _execute(
        HistoricalGameApplicationOptions(historical_tactical_motif_review=True),
        source=source,
    )
    report = execution.result.to_dict()["document"]["historical_game_summary"][
        "historical_tactical_motif_review_summary"
    ]
    tactical = _attachment(execution, "historical_tactical_motif_review_summary")
    entries = {entry.field_path: entry for entry in tactical.ledger.entries}

    assert report["observation_count"] == 26
    assert report["partial_observation_count"] == 2
    assert entries[
        "/observations/0/observation_status"
    ].available_from_decision_index == 3
    assert entries[
        "/observations/0/completed_trick_points"
    ].available_from_decision_index == 3
    assert entries[
        "/observations/24/observation_status"
    ].available_from_decision_index == 25
    assert entries[
        "/observations/24/completed_trick_points"
    ].available_from_decision_index == 25
    assert entries[
        "/observations/25/observation_status"
    ].available_from_decision_index == 26
    assert entries[
        "/observations/25/completed_trick_points"
    ].available_from_decision_index == 26


def test_claim_tactical_provenance_accepts_observations_without_motifs() -> None:
    source = json.loads(
        (ROOT / "examples" / "historical_party_wide_claim.json").read_text(encoding="utf-8")
    )
    invocation = build_application_invocation(
        source,
        input_reference="historical-claim-tactical.json",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(historical_tactical_motif_review=True)
        ),
    )

    execution = execute_application_invocation(invocation)
    report = execution.result.to_dict()["document"]["historical_game_summary"][
        "historical_tactical_motif_review_summary"
    ]

    assert report["observation_count"] == 15
    assert any(not observation["motifs"] for observation in report["observations"])
    assert execution.provenance is not None


@pytest.mark.parametrize(
    ("option_name", "attachment_name"),
    (
        ("replay_coaching", "historical_replay_coaching_summary"),
        (
            "information_set_replay_coaching",
            "historical_information_set_replay_coaching_summary",
        ),
    ),
)
def test_tactical_review_does_not_change_existing_coaching_attachment(
    option_name: str,
    attachment_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    options = {
        option_name: True,
        "search_seed": 31,
        "search_budget_profile": "interactive_v1",
        "immediate_sample_count": 1,
        "immediate_base_random_seed": 37,
    }
    _set_deterministic_search_clocks(monkeypatch)
    baseline = _execute(HistoricalGameApplicationOptions(**options))
    _set_deterministic_search_clocks(monkeypatch)
    combined = _execute(
        HistoricalGameApplicationOptions(
            **options,
            historical_tactical_motif_review=True,
        )
    )

    baseline_summary = baseline.result.to_dict()["document"]["historical_game_summary"]
    combined_summary = combined.result.to_dict()["document"]["historical_game_summary"]
    assert _without_wall_clock_elapsed(combined_summary[attachment_name]) == (
        _without_wall_clock_elapsed(baseline_summary[attachment_name])
    )
