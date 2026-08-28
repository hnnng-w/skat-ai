import copy
import json
from collections import Counter
from pathlib import Path

import pytest
from test_historical_information_set_search_review import _unavailable_builder

from skatmind.application import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skatmind.application.execution import (
    ApplicationWorkflowDependencies,
    validate_application_invocation,
)
from skatmind.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
)
from skatmind.errors import SkatMindValidationError, SkatMindWorkflowError
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_information_set_search_review import (
    build_historical_information_set_search_review_v1,
)
from skatmind.public_field_provenance import build_public_field_provenance_bundle

ROOT = Path(__file__).resolve().parents[1]


def _load(
    name: str = "historical_grand_normal_completion.json",
) -> dict[str, object]:
    return json.loads(
        (ROOT / "examples" / name).read_text(encoding="utf-8")
    )


def _zero_decision_root() -> dict[str, object]:
    source = json.loads(
        (ROOT / "examples" / "training_dataset_variable_length.json").read_text(
            encoding="utf-8"
        )
    )
    data = copy.deepcopy(
        source["training_dataset_input"]["records"][0]["historical_game"]
    )
    data["tricks"] = []
    data["game_end"]["declarer_hand_cards_remaining"] = 10
    data["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    return {"historical_game_input": data}


def _invocation(options: HistoricalGameApplicationOptions):
    return build_application_invocation(
        _load(),
        input_reference="memory://information-set-replay-coaching",
        options=ApplicationExecutionOptions(historical_game=options),
    )


def _review_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "review_method": "information_set_search_with_same_selection_pimc_and_immediate_v1",
        "information_policy": "decision_time",
        "source_game_id": "historical-grand-001",
        "game_end_reason": "normal_completion",
        "settings": {
            "base_search_seed": 17,
            "search_budget_profile": "historical_review_v1",
            "requested_budget": {"max_selected_worlds": 1},
            "immediate_sample_count": 1,
            "immediate_base_random_seed": 19,
        },
        "decision_count": 0,
        "decisions": [],
    }


def _report_document() -> dict[str, object]:
    assessment = {
        "decision_time_evidence": {
            "source_game_id": "historical-grand-001",
            "decision_index": 1,
            "acting_player_id": "player-a",
            "information_set_pre_actual_analysis": {
                "information_set_search_result": {"status": "complete"},
                "same_selection_pimc_result": {"status": "complete"},
                "immediate_recommended_card": "CA",
                "same_selected_world_sequence": True,
            },
        },
        "actual_card": "CA",
        "assessment_status": "best_or_equivalent",
        "impact_tier": "no_missed_impact",
        "comparison": {"information_set_actual_same_card": True},
    }
    return {
        "report_version": 1,
        "report_method": "historical_information_set_replay_coaching_v1",
        "information_policy": (
            "decision_time_analysis_then_actual_card_then_outcome_context"
        ),
        "source_game_id": "historical-grand-001",
        "source_review_settings": {
            "base_search_seed": 17,
            "search_budget_profile": "historical_review_v1",
        },
        "game_context": {
            "source_game_id": "historical-grand-001",
            "game_end_reason": "normal_completion",
        },
        "assessments": [assessment],
        "prioritization": {"key_decisions": [{"assessment": assessment}]},
        "guidance": {"patterns": [], "recommendations": []},
        "coverage": {"decision_count": 1, "assessable_decision_count": 1},
        "player_summaries": [],
        "role_summaries": [],
        "phase_summaries": [],
        "contract_summaries": [],
        "outcome_context": {
            "source_game_id": "historical-grand-001",
            "winner": "defenders",
        },
        "limitations": ["single_recorded_game_only"],
    }


def _dependencies(calls: Counter[str], retained_review: object):
    retained_report = object()

    def snapshots(summary):
        calls["snapshots"] += 1
        return build_historical_decision_snapshots(summary)

    def immediate_review(**_kwargs):
        calls["immediate_review"] += 1
        return {"decisions": []}

    def review(**_kwargs):
        calls["information_set_review"] += 1
        return retained_review

    def serialize_review(value):
        calls["review_serialization"] += 1
        assert value is retained_review
        return _review_document()

    def coaching(**kwargs):
        calls["coaching"] += 1
        assert kwargs["source_review"] is retained_review
        assert kwargs["historical_record"].game_id == "historical-grand-001"
        assert kwargs["historical_game_summary"]["game_id"] == (
            "historical-grand-001"
        )
        return retained_report

    def serialize_coaching(value):
        calls["report_serialization"] += 1
        assert value is retained_report
        return _report_document()

    return ApplicationWorkflowDependencies(
        historical_game=HistoricalGameWorkflowDependencies(
            build_snapshots=snapshots,
            build_immediate_review=immediate_review,
            build_information_set_search_review=review,
            serialize_information_set_search_review=serialize_review,
            build_information_set_replay_coaching=coaching,
            serialize_information_set_replay_coaching=serialize_coaching,
        )
    )


def _entry(attachment, path):
    return next(entry for entry in attachment.ledger.entries if entry.field_path == path)


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()


def test_option_defaults_to_false_and_rejects_non_boolean_values() -> None:
    assert HistoricalGameApplicationOptions().information_set_replay_coaching is False

    with pytest.raises(SkatMindValidationError, match="must be a boolean"):
        HistoricalGameApplicationOptions(information_set_replay_coaching=1)


@pytest.mark.parametrize("existing_mode", ["search_review", "replay_coaching"])
@pytest.mark.parametrize(
    "information_set_mode",
    ["information_set_search_review", "information_set_replay_coaching"],
)
def test_search_and_coaching_families_are_exactly_exclusive(
    existing_mode: str,
    information_set_mode: str,
) -> None:
    options = HistoricalGameApplicationOptions(
        **{existing_mode: True, information_set_mode: True, "search_seed": 1}
    )

    with pytest.raises(SkatMindWorkflowError, match="cannot be combined"):
        validate_application_invocation(_invocation(options))


def test_information_set_family_pair_and_shared_modes_validate_together() -> None:
    validate_application_invocation(
        _invocation(
            HistoricalGameApplicationOptions(
                decision_snapshots=True,
                immediate_review=True,
                information_set_search_review=True,
                information_set_replay_coaching=True,
                search_seed=17,
                immediate_sample_count=1,
            )
        )
    )

    with pytest.raises(SkatMindWorkflowError, match="require search_seed"):
        validate_application_invocation(
            _invocation(
                HistoricalGameApplicationOptions(
                    information_set_replay_coaching=True
                )
            )
        )


def test_combined_information_set_modes_share_one_retained_review() -> None:
    calls: Counter[str] = Counter()
    retained_review = object()
    execution = execute_application_invocation(
        _invocation(
            HistoricalGameApplicationOptions(
                decision_snapshots=True,
                immediate_review=True,
                information_set_search_review=True,
                information_set_replay_coaching=True,
                search_seed=17,
                immediate_sample_count=1,
                immediate_base_random_seed=19,
            )
        ),
        dependencies=_dependencies(calls, retained_review),
    )
    summary = execution.result.document["historical_game_summary"]

    assert calls == Counter(
        {
            "snapshots": 1,
            "immediate_review": 1,
            "information_set_review": 1,
            "review_serialization": 1,
            "coaching": 1,
            "report_serialization": 1,
        }
    )
    assert "decision_snapshot_summary" in summary
    assert "historical_game_review_summary" in summary
    assert "historical_information_set_search_review_summary" in summary
    assert "historical_information_set_replay_coaching_summary" in summary
    assert "historical_search_review_summary" not in summary
    assert "historical_replay_coaching_summary" not in summary


def test_default_core_builds_coaching_without_returning_the_retained_review() -> None:
    invocation = build_application_invocation(
        _zero_decision_root(),
        input_reference="memory://zero-decision-information-set-coaching",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                information_set_replay_coaching=True,
                search_seed=17,
                immediate_sample_count=1,
            )
        ),
    )

    execution = execute_application_invocation(invocation)
    summary = execution.result.to_dict()["document"]["historical_game_summary"]
    report = summary["historical_information_set_replay_coaching_summary"]

    assert "historical_information_set_search_review_summary" not in summary
    assert report["report_method"] == (
        "historical_information_set_replay_coaching_v1"
    )
    assert report["assessments"] == []
    assert report["coverage"]["decision_count"] == 0
    assert execution.provenance is not None
    report_attachment = next(
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name == "information_set_replay_coaching/report"
    )
    assert report_attachment.document_to_dict() == report


def test_default_core_report_and_provenance_reuse_one_nonempty_review() -> None:
    calls: Counter[str] = Counter()

    def review(**kwargs):
        calls["information_set_review"] += 1
        return build_historical_information_set_search_review_v1(
            kwargs["snapshot_summary"],
            kwargs["historical_record"],
            kwargs["settings"],
            pre_actual_analysis_builder=_unavailable_builder(),
            effective_policy_settings_by_decision=kwargs[
                "effective_policy_settings_by_decision"
            ],
        )

    invocation = build_application_invocation(
        _load("historical_grand_declarer_concession.json"),
        input_reference="memory://nonempty-information-set-coaching",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                information_set_replay_coaching=True,
                search_seed=17,
                immediate_sample_count=1,
            )
        ),
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=ApplicationWorkflowDependencies(
            historical_game=HistoricalGameWorkflowDependencies(
                build_information_set_search_review=review,
            )
        ),
    )
    summary = execution.result.to_dict()["document"]["historical_game_summary"]
    report_document = summary[
        "historical_information_set_replay_coaching_summary"
    ]

    assert calls == Counter({"information_set_review": 1})
    assert "historical_information_set_search_review_summary" not in summary
    assert report_document["assessments"]
    assert report_document["coverage"]["decision_count"] == len(
        report_document["assessments"]
    )
    assert execution.provenance is not None
    report_attachment = next(
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name == "information_set_replay_coaching/report"
    )
    assert report_attachment.coverage_summary.provenance_complete is True
    assert _entry(
        report_attachment,
        "/assessments/0/decision_time_evidence/information_policy",
    ).available_from == "current_decision"
    assert _entry(
        report_attachment,
        "/assessments/0/actual_card",
    ).available_from == "after_actual_play"
    assert _entry(
        report_attachment,
        "/outcome_context/game_end_reason",
    ).available_from == "game_end"


def test_coaching_only_omits_review_serialization_and_has_temporal_provenance() -> None:
    calls: Counter[str] = Counter()
    execution = execute_application_invocation(
        _invocation(
            HistoricalGameApplicationOptions(
                information_set_replay_coaching=True,
                search_seed=17,
                immediate_sample_count=1,
                immediate_base_random_seed=19,
            )
        ),
        dependencies=_dependencies(calls, object()),
    )
    summary = execution.result.document["historical_game_summary"]

    assert calls == Counter(
        {
            "snapshots": 1,
            "information_set_review": 1,
            "coaching": 1,
            "report_serialization": 1,
        }
    )
    assert "historical_information_set_search_review_summary" not in summary
    assert "historical_information_set_replay_coaching_summary" in summary
    assert execution.provenance is not None
    report = next(
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name == "information_set_replay_coaching/report"
    )
    root = execution.provenance.attachments[-1]

    decision_time = _entry(
        report,
        (
            "/assessments/0/decision_time_evidence/"
            "information_set_pre_actual_analysis/information_set_search_result/status"
        ),
    )
    pimc = _entry(
        report,
        (
            "/assessments/0/decision_time_evidence/"
            "information_set_pre_actual_analysis/same_selection_pimc_result/status"
        ),
    )
    immediate = _entry(
        report,
        (
            "/assessments/0/decision_time_evidence/"
            "information_set_pre_actual_analysis/immediate_recommended_card"
        ),
    )
    shared_worlds = _entry(
        report,
        (
            "/assessments/0/decision_time_evidence/"
            "information_set_pre_actual_analysis/same_selected_world_sequence"
        ),
    )
    actual = _entry(report, "/assessments/0/actual_card")
    assessment = _entry(report, "/assessments/0/assessment_status")
    outcome = _entry(report, "/outcome_context/winner")

    assert (decision_time.available_from, decision_time.origin) == (
        "current_decision",
        "search_derived",
    )
    assert pimc.source_references[0].reference_id == (
        "compatible_world_minimax_same_selection_v1"
    )
    assert immediate.origin == "heuristic_analysis"
    assert {
        reference.reference_id for reference in shared_worlds.source_references
    } == {
        "retained_historical_information_set_search_review",
        "compatible_world_minimax_same_selection_v1",
    }
    assert (actual.available_from, actual.origin) == (
        "after_actual_play",
        "retrospective_attachment",
    )
    assert assessment.available_from == "after_actual_play"
    assert (outcome.available_from, outcome.visibility) == (
        "game_end",
        "post_game_only",
    )
    assert _entry(
        report,
        "/prioritization/key_decisions/0/assessment/actual_card",
    ).available_from == "after_actual_play"
    assert _entry(
        report,
        (
            "/prioritization/key_decisions/0/assessment/decision_time_evidence/"
            "information_set_pre_actual_analysis/immediate_recommended_card"
        ),
    ).available_from == "current_decision"
    assert _entry(
        root,
        (
            "/historical_game_summary/"
            "historical_information_set_replay_coaching_summary/"
            "assessments/0/actual_card"
        ),
    ).available_from == "after_actual_play"
    assert _entry(
        root,
        (
            "/historical_game_summary/"
            "historical_information_set_replay_coaching_summary/"
            "outcome_context/winner"
        ),
    ).available_from == "game_end"
    assert _entry(
        root,
        (
            "/historical_game_summary/"
            "historical_information_set_replay_coaching_summary/"
            "prioritization/key_decisions/0/assessment/actual_card"
        ),
    ).available_from == "after_actual_play"

    public = build_public_field_provenance_bundle(execution)
    assert public.result.coverage_summary["provenance_complete"] is True
    public_keys = _all_keys(public.to_dict())
    for private_name in (
        "controlled_policy",
        "observation",
        "world_states",
        "selected_worlds",
        "child_seed",
        "cache",
    ):
        assert private_name not in public_keys
    assert calls["information_set_review"] == 1
    assert calls["coaching"] == 1
