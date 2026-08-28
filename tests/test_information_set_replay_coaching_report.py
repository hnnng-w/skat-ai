import json
from dataclasses import FrozenInstanceError

import pytest
from test_historical_information_set_search_review import (
    _load_record,
    _unavailable_builder,
    _zero_decision_record,
)

from skatmind.historical_information_set_search_review import (
    HistoricalInformationSetSearchReviewSettingsV1,
    build_historical_information_set_search_review_v1,
)
from skatmind.information_set_replay_coaching_report import (
    INFORMATION_SET_REPLAY_COACHING_GUIDANCE_POLICY,
    INFORMATION_SET_REPLAY_COACHING_LIMITATIONS,
    INFORMATION_SET_REPLAY_COACHING_METHOD,
    INFORMATION_SET_REPLAY_COACHING_OUTCOME_POLICY,
    INFORMATION_SET_REPLAY_COACHING_PRIORITIZATION_POLICY,
    INFORMATION_SET_REPLAY_COACHING_REPORT_VERSION,
    build_information_set_replay_coaching_report_v1,
    build_serializable_information_set_replay_coaching_report_v1,
)
from skatmind.replay_coaching_report import (
    build_replay_coaching_report,
    build_serializable_replay_coaching_report,
)


def _report(example_name: str):
    record, snapshots = _load_record(example_name)
    review = build_historical_information_set_search_review_v1(
        snapshots,
        record,
        HistoricalInformationSetSearchReviewSettingsV1(
            base_search_seed=17,
            immediate_sample_count=1,
            immediate_base_random_seed=41,
        ),
        pre_actual_analysis_builder=_unavailable_builder(),
    )
    return record, review, build_information_set_replay_coaching_report_v1(
        record,
        review,
    )


def _collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_collect_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_collect_keys(item) for item in value))
    return set()


def test_report_constants_method_policies_and_limitations_are_exact() -> None:
    assert INFORMATION_SET_REPLAY_COACHING_REPORT_VERSION == 1
    assert INFORMATION_SET_REPLAY_COACHING_METHOD == (
        "historical_information_set_replay_coaching_v1"
    )
    assert INFORMATION_SET_REPLAY_COACHING_PRIORITIZATION_POLICY == (
        "existing_objective_priority_without_baseline_fallback"
    )
    assert INFORMATION_SET_REPLAY_COACHING_GUIDANCE_POLICY == (
        "existing_deterministic_templates_without_tactical_inference"
    )
    assert INFORMATION_SET_REPLAY_COACHING_OUTCOME_POLICY == (
        "final_context_after_coaching"
    )
    assert INFORMATION_SET_REPLAY_COACHING_LIMITATIONS == (
        "outcome_context_not_decision_evidence",
        "single_recorded_game_only",
        "bounded_three_trick_information_set_search",
        "controlled_player_selected_world_consistency",
        "fixed_opponent_policy_model",
        "sampled_compatible_worlds",
        "search_unavailable",
        "observed_card_not_ground_truth",
        "incomplete_assessment_coverage",
        "no_equilibrium_or_global_optimality_claim",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
        "no_player_skill_rating",
    )


@pytest.mark.parametrize(
    "example_name",
    [
        "historical_grand_declarer_concession.json",
        "historical_party_wide_claim.json",
    ],
)
def test_shortened_and_claim_reports_have_complete_parallel_coverage(
    example_name: str,
) -> None:
    record, review, report = _report(example_name)

    assert len(report.assessments) == len(review.decisions)
    assert report.coverage.decision_count == sum(
        len(trick.plays) for trick in record.tricks
    )
    assert report.coverage.assessable_decision_count + (
        report.coverage.not_assessable_count
    ) == report.coverage.decision_count
    assert len(report.player_summaries) == 3
    assert len(report.role_summaries) == 2
    assert len(report.phase_summaries) == 3
    assert len(report.contract_summaries) == 1
    assert report.outcome_context.game_end_reason == record.game_end_reason
    assert "search_unavailable" in report.limitations
    assert "incomplete_assessment_coverage" in report.limitations


def test_zero_decision_report_is_valid_and_attaches_outcome_last() -> None:
    record, snapshots = _zero_decision_record()
    review = build_historical_information_set_search_review_v1(
        snapshots,
        record,
        HistoricalInformationSetSearchReviewSettingsV1(base_search_seed=3),
        pre_actual_analysis_builder=_unavailable_builder(),
    )
    report = build_information_set_replay_coaching_report_v1(record, review)

    assert report.assessments == ()
    assert report.coverage.decision_count == 0
    assert report.prioritization.key_decisions == ()
    assert report.guidance.patterns == ()
    assert report.outcome_context.source_game_id == record.game_id
    assert "search_unavailable" not in report.limitations


def test_report_serialization_is_deterministic_and_privacy_safe() -> None:
    _record, _review, report = _report("historical_party_wide_claim.json")
    first = build_serializable_information_set_replay_coaching_report_v1(report)
    second = build_serializable_information_set_replay_coaching_report_v1(report)
    keys = _collect_keys(first)

    assert first == second
    assert json.dumps(first, sort_keys=False) == json.dumps(second, sort_keys=False)
    assert first["report_method"] == INFORMATION_SET_REPLAY_COACHING_METHOD
    assert first["coverage"]["decision_count"] == len(first["assessments"])
    assert {
        "initial_hand",
        "hand",
        "skat",
        "discarded_cards",
        "controlled_policy",
        "information_set",
        "observation",
        "selected_worlds",
        "exact_state",
        "ownership",
        "cache",
        "branches",
        "derived_child_seed",
    }.isdisjoint(keys)
    text = json.dumps(first).lower()
    assert "equilibrium_or_global_optimality_claim" in text
    assert "perfect play" not in text
    assert "caused the result" not in text
    with pytest.raises(FrozenInstanceError):
        report.report_version = 2  # type: ignore[misc]


def test_existing_bounded_report_serializer_defaults_remain_unchanged(monkeypatch) -> None:
    from test_historical_game import build_historical_input
    from test_replay_coaching_report import _analyze

    record, _snapshots, analysis = _analyze(monkeypatch, build_historical_input())
    report = build_replay_coaching_report(record, analysis)

    first = build_serializable_replay_coaching_report(report)
    second = build_serializable_replay_coaching_report(report)

    assert first == second
    assert first["report_method"] == "historical_replay_coaching_v1"
    assert "information_set_replay_coaching_assessment_version" not in str(first)
