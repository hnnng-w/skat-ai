import copy
import json
from dataclasses import FrozenInstanceError, replace

import pytest
from test_historical_game import build_historical_input
from test_historical_game_event_chain import TERMINAL_BUILDERS, add_continuation
from test_replay_coaching_contracts import (
    _historical_fake_immediate,
    _historical_fake_search,
)
from test_replay_coaching_prioritization import _zero_decision_data

from skat_ai.bounded_search_result import (
    ConsumedSearchBudget,
    build_serializable_bounded_search_result,
)
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    HISTORICAL_SEATS,
    build_historical_game_record,
    build_historical_game_summary,
)
from skat_ai.historical_search_review import (
    HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD,
    HistoricalSearchReviewCoachingAnalysis,
    build_historical_search_review_coaching_analysis,
    build_historical_search_review_metrics,
    build_historical_search_review_summary,
)
from skat_ai.post_game_review import NOT_AVAILABLE_DECISION_QUALITY
from skat_ai.replay_coaching_assessment import (
    build_replay_coaching_decision_assessment,
)
from skat_ai.replay_coaching_evidence import (
    REPLAY_COACHING_INFORMATION_POLICY,
    build_immediate_replay_coaching_evidence,
)
from skat_ai.replay_coaching_guidance import build_replay_coaching_guidance
from skat_ai.replay_coaching_prioritization import (
    build_replay_coaching_prioritization_result,
)
from skat_ai.replay_coaching_report import (
    REPLAY_COACHING_OUTCOME_CONTEXT_POLICY,
    REPLAY_COACHING_REPORT_LIMITATIONS,
    REPLAY_COACHING_REPORT_METHOD,
    REPLAY_COACHING_REPORT_VERSION,
    HistoricalReplayCoachingAnalysis,
    build_historical_replay_coaching_analysis,
    build_historical_replay_coaching_public_summaries,
    build_replay_coaching_report,
    build_serializable_replay_coaching_report,
)
from skat_ai.replay_coaching_report_context import (
    REPLAY_COACHING_TERMINAL_SUMMARY_FIELD_BY_END_REASON,
    ReplayCoachingGameContext,
    ReplayCoachingPlayerContext,
    build_replay_coaching_game_context,
    build_serializable_replay_coaching_game_context,
)
from skat_ai.retrospective_search_comparison import (
    build_search_actual_card_comparison,
    build_search_vs_immediate_comparison,
    build_serializable_search_actual_card_comparison,
    build_serializable_search_vs_immediate_comparison,
)


def _plain(value):
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_collect_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_collect_keys(item) for item in value))
    return set()


def _analyze(monkeypatch, data: dict, *, search=_historical_fake_search):
    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    record = build_historical_game_record(data)
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )
    analysis = build_historical_search_review_coaching_analysis(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
    )
    return record, snapshots, analysis


def _report(monkeypatch, data: dict):
    record, _, analysis = _analyze(monkeypatch, data)
    return record, analysis, build_replay_coaching_report(record, analysis)


def test_report_constants_and_canonical_limitations_are_stable() -> None:
    assert REPLAY_COACHING_REPORT_VERSION == 1
    assert REPLAY_COACHING_REPORT_METHOD == "historical_replay_coaching_v1"
    assert REPLAY_COACHING_OUTCOME_CONTEXT_POLICY == "final_context_after_coaching"
    assert REPLAY_COACHING_INFORMATION_POLICY == (
        "decision_time_then_retrospective_attachment"
    )
    assert REPLAY_COACHING_REPORT_LIMITATIONS == (
        "outcome_context_not_decision_evidence",
        "single_recorded_game_only",
        "bounded_late_game_search",
        "determinization_strategy_fusion",
        "sampled_compatible_worlds",
        "completed_common_prefix",
        "immediate_expected_value_only",
        "search_unavailable",
        "observed_card_not_ground_truth",
        "incomplete_assessment_coverage",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
        "no_player_skill_rating",
    )
    assert dict(REPLAY_COACHING_TERMINAL_SUMMARY_FIELD_BY_END_REASON) == {
        "normal_completion": None,
        "declarer_concession": "historical_game_end_summary",
        "defender_concession": "historical_game_end_summary",
        "declarer_card_exposure": "historical_game_end_summary",
        "defender_open_play": "historical_game_end_summary",
        "open_card_throw": "historical_game_end_summary",
    }


def test_player_and_game_context_are_immutable_privacy_safe_and_defensive() -> None:
    record = build_historical_game_record(build_historical_input())
    context = build_replay_coaching_game_context(record, recorded_decision_count=30)
    serialized = build_serializable_replay_coaching_game_context(context)

    assert len(context.players) == 3
    assert tuple(player.seat for player in context.players) == HISTORICAL_SEATS
    assert tuple(player.side for player in context.players) == (
        "defenders",
        "declarer",
        "defenders",
    )
    assert serialized["players"] == [
        {
            "player_id": "player-a",
            "player_label": "Alice",
            "seat": "forehand",
            "side": "defenders",
        },
        {
            "player_id": "player-b",
            "player_label": None,
            "seat": "middlehand",
            "side": "declarer",
        },
        {
            "player_id": "player-c",
            "player_label": "Carol",
            "seat": "rearhand",
            "side": "defenders",
        },
    ]
    assert serialized["declaration"] == {
        "game_type": "grand",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": record.declaration.matadors,
        "bid_value": 18,
    }
    assert serialized["recorded_play_count"] == 30
    assert serialized["recorded_decision_count"] == 30
    assert not {
        "initial_hand",
        "skat",
        "discarded_cards",
        "tricks",
    }.intersection(_collect_keys(serialized))
    with pytest.raises(FrozenInstanceError):
        context.game_type = "clubs"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        context.players[0].seat = "rearhand"  # type: ignore[misc]
    with pytest.raises(TypeError):
        context.declaration["game_type"] = "clubs"  # type: ignore[index]

    declaration = {
        "game_type": "grand",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 1,
        "bid_value": 18,
    }
    direct = ReplayCoachingGameContext(
        source_game_id="game",
        played_at=None,
        players=(
            ReplayCoachingPlayerContext("a", None, "forehand", "declarer"),
            ReplayCoachingPlayerContext("b", None, "middlehand", "defenders"),
            ReplayCoachingPlayerContext("c", None, "rearhand", "defenders"),
        ),
        declarer_player_id="a",
        game_type="grand",
        declaration=declaration,
        game_end_reason="normal_completion",
        continuation_event_kinds=(),
        recorded_play_count=0,
        recorded_decision_count=0,
    )
    declaration["game_type"] = "clubs"
    assert direct.declaration["game_type"] == "grand"


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert"),
    [
        ("clubs", False, False),
        ("spades", False, False),
        ("hearts", False, False),
        ("diamonds", False, False),
        ("grand", False, False),
        ("null", False, False),
        ("null", True, False),
        ("null", False, True),
        ("null", True, True),
    ],
)
def test_report_supports_suit_grand_and_all_null_variants(
    monkeypatch,
    game_type: str,
    hand_game: bool,
    ouvert: bool,
) -> None:
    data = build_historical_input(game_type=game_type, hand_game=hand_game)
    if ouvert:
        data["declaration"]["ouvert"] = True
    _, _, report = _report(monkeypatch, data)

    assert report.game_context.game_type == game_type
    assert report.game_context.declaration["hand_game"] is hand_game
    assert report.game_context.declaration["ouvert"] is ouvert
    assert len(report.contract_summaries) == 1
    assert report.contract_summaries[0].scope_value == game_type


@pytest.mark.parametrize(
    "end_reason",
    ["normal_completion", *TERMINAL_BUILDERS],
)
def test_outcome_context_allowlists_every_supported_end_reason(
    monkeypatch,
    end_reason: str,
) -> None:
    data = (
        build_historical_input()
        if end_reason == "normal_completion"
        else TERMINAL_BUILDERS[end_reason]()
    )
    record, _, report = _report(monkeypatch, data)
    serialized = build_serializable_replay_coaching_report(report)["outcome_context"]

    assert serialized["source_game_id"] == record.game_id
    assert serialized["game_end_reason"] == end_reason
    assert serialized["status"] == "complete"
    assert set(serialized).issuperset(
        {
            "game_result_summary",
            "game_value_summary",
            "overbid_summary",
            "final_settlement_summary",
        }
    )
    if end_reason == "normal_completion":
        assert "historical_game_end_summary" not in serialized
    else:
        terminal = serialized["historical_game_end_summary"]
        assert terminal["kind"] == end_reason
        assert not {
            "exposed_cards",
            "thrown_cards",
            "card_reconciliation",
            "exact_proof",
            "theoretical_schwarz_assessment",
        }.intersection(_collect_keys(terminal))


@pytest.mark.parametrize(
    "continuation_kind",
    ("defender_open_play_continuation", "declarer_card_exposure_continuation"),
)
@pytest.mark.parametrize("end_reason", TERMINAL_BUILDERS)
def test_outcome_context_supports_continuation_before_terminal_shortening(
    monkeypatch,
    continuation_kind: str,
    end_reason: str,
) -> None:
    data = add_continuation(TERMINAL_BUILDERS[end_reason](), continuation_kind)
    _, _, report = _report(monkeypatch, data)
    serialized = build_serializable_replay_coaching_report(report)
    game_context = serialized["game_context"]
    outcome = serialized["outcome_context"]

    assert game_context["continuation_event_kinds"] == [continuation_kind]
    assert outcome["historical_game_end_summary"]["kind"] == end_reason
    events = outcome["historical_game_events_summary"]
    assert events["event_count"] == 1
    assert events["events"][0]["kind"] == continuation_kind
    assert events["events"][0]["final_game_end_reason"] == end_reason
    assert not {
        "exposed_cards",
        "public_declarer_cards",
        "card_reconciliation",
    }.intersection(_collect_keys(events))


@pytest.mark.parametrize(
    "continuation_kind",
    ("defender_open_play_continuation", "declarer_card_exposure_continuation"),
)
def test_outcome_context_supports_continuation_before_normal_completion(
    monkeypatch,
    continuation_kind: str,
) -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](), continuation_kind
    )
    normal = build_historical_input()
    normal["game_events"] = data["game_events"]
    _, _, report = _report(monkeypatch, normal)

    assert report.game_context.continuation_event_kinds == (continuation_kind,)
    assert report.outcome_context.historical_game_events_summary is not None
    assert report.outcome_context.historical_game_end_summary is None


def test_zero_decision_report_has_complete_zero_coverage_and_rows(monkeypatch) -> None:
    _, _, report = _report(monkeypatch, _zero_decision_data())
    coverage = report.coverage_summary

    assert coverage.decision_count == 0
    assert all(
        getattr(coverage, field_name) == 0
        for field_name in (
            "assessable_decision_count",
            "forced_move_count",
            "best_or_equivalent_count",
            "strictly_below_best_count",
            "not_assessable_count",
            "high_impact_decision_count",
            "key_decision_count",
            "turning_point_count",
            "pattern_count",
            "actionable_pattern_count",
            "decision_recommendation_count",
            "pattern_recommendation_count",
            "search_recommendation_count",
            "immediate_available_count",
        )
    )
    assert all(
        count == 0
        for counts in (
            coverage.assessment_status_counts,
            coverage.evidence_basis_counts,
            coverage.impact_tier_counts,
            coverage.search_status_counts,
            coverage.world_coverage_counts,
        )
        for _, count in counts
    )
    assert len(report.player_summaries) == 3
    assert len(report.role_summaries) == 2
    assert len(report.phase_summaries) == 3
    assert len(report.contract_summaries) == 1
    assert all(
        summary.decision_count == 0
        for summaries in (
            report.player_summaries,
            report.role_summaries,
            report.phase_summaries,
            report.contract_summaries,
        )
        for summary in summaries
    )
    assert report.limitations == (
        "outcome_context_not_decision_evidence",
        "single_recorded_game_only",
        "observed_card_not_ground_truth",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
        "no_player_skill_rating",
    )


def test_incomplete_assessment_coverage_adds_conditional_limitations(
    monkeypatch,
) -> None:
    record, _, analysis = _analyze(monkeypatch, build_historical_input())
    index = next(
        index
        for index, assessment in enumerate(analysis.assessments)
        if len(assessment.decision_time_evidence.legal_cards) > 1
    )
    original = analysis.assessments[index]
    original_evidence = original.decision_time_evidence
    unavailable_search = replace(
        original_evidence.bounded_search_result,
        status="unavailable",
        stop_reason="remaining_trick_limit_exceeded",
        world_coverage="none",
        solution_claim="none",
        consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
        compatible_world_count=None,
        candidate_results=(),
        recommended_card=None,
    )
    unavailable_immediate = build_immediate_replay_coaching_evidence(
        legal_cards=original_evidence.legal_cards,
        analysis_report=[],
        recommended_card=None,
        unavailable_reason="immediate_analysis_unavailable",
        game_type=original_evidence.game_type,
        player_role=(
            "declarer" if original_evidence.local_side == "declarer" else "defender"
        ),
    )
    search_vs_immediate = build_search_vs_immediate_comparison(
        unavailable_search,
        None,
        None,
        original_evidence.game_type,
        "declarer" if original_evidence.local_side == "declarer" else "defender",
    )
    evidence = replace(
        original_evidence,
        immediate_evidence=unavailable_immediate,
        bounded_search_result=unavailable_search,
        search_vs_immediate_comparison=search_vs_immediate,
    )
    search_actual = build_search_actual_card_comparison(
        unavailable_search, original.actual_card
    )
    unavailable_assessment = build_replay_coaching_decision_assessment(
        decision_time_evidence=evidence,
        actual_card=original.actual_card,
        search_actual_card_comparison=search_actual,
        immediate_baseline_quality=NOT_AVAILABLE_DECISION_QUALITY,
    )
    assessments = (
        *analysis.assessments[:index],
        unavailable_assessment,
        *analysis.assessments[index + 1 :],
    )
    public = _plain(analysis.public_review_summary)
    public_decision = public["decisions"][index]
    public_decision["bounded_search_result"] = build_serializable_bounded_search_result(
        unavailable_search
    )
    public_decision["search_actual_card_comparison"] = (
        build_serializable_search_actual_card_comparison(search_actual)
    )
    public_decision["search_vs_immediate_comparison"] = (
        build_serializable_search_vs_immediate_comparison(search_vs_immediate)
    )
    public_decision["immediate_baseline"]["recommendation"]["card"] = None
    public_decision["immediate_baseline"]["analysis_report"] = []
    metrics = build_historical_search_review_metrics(public["decisions"])
    public.update(metrics)
    prioritization = build_replay_coaching_prioritization_result(record, assessments)
    guidance = build_replay_coaching_guidance(record, assessments, prioritization)
    incomplete_analysis = HistoricalSearchReviewCoachingAnalysis(
        public_review_summary=public,
        assessments=assessments,
        prioritization=prioritization,
        guidance=guidance,
        historical_record=record,
    )
    report = build_replay_coaching_report(record, incomplete_analysis)

    assert report.coverage_summary.not_assessable_count == 1
    assert "search_unavailable" in report.limitations
    assert "incomplete_assessment_coverage" in report.limitations
    assert "immediate_expected_value_only" not in report.limitations


def test_coverage_and_all_scope_dimensions_reconcile(monkeypatch) -> None:
    record, analysis, report = _report(monkeypatch, build_historical_input())
    coverage = report.coverage_summary

    assert coverage.decision_count == len(analysis.assessments) == 30
    assert dict(coverage.search_status_counts) == dict(
        analysis.public_review_summary["status_counts"]
    )
    assert coverage.search_recommendation_count == (
        analysis.public_review_summary["decision_counts"][
            "search_recommendation_count"
        ]
    )
    assert tuple(summary.scope_value for summary in report.player_summaries) == tuple(
        next(player.player_id for player in record.players if player.seat == seat)
        for seat in HISTORICAL_SEATS
    )
    assert tuple(summary.scope_value for summary in report.role_summaries) == (
        "declarer",
        "defenders",
    )
    assert tuple(summary.scope_value for summary in report.phase_summaries) == (
        "opening",
        "middle",
        "endgame",
    )
    assert tuple(summary.scope_value for summary in report.contract_summaries) == (
        "grand",
    )
    for summaries in (
        report.player_summaries,
        report.role_summaries,
        report.phase_summaries,
        report.contract_summaries,
    ):
        assert sum(summary.decision_count for summary in summaries) == 30
        assert sum(
            summary.assessable_decision_count for summary in summaries
        ) == coverage.assessable_decision_count
        assert sum(
            summary.strictly_below_best_count for summary in summaries
        ) == coverage.strictly_below_best_count
        assert sum(summary.key_decision_count for summary in summaries) == (
            coverage.key_decision_count
        )
        assert sum(summary.turning_point_count for summary in summaries) == (
            coverage.turning_point_count
        )
        assert sum(
            summary.decision_recommendation_count for summary in summaries
        ) == coverage.decision_recommendation_count
        assert all(
            summary.decision_indices
            == tuple(sorted(summary.decision_indices))
            for summary in summaries
        )


def test_report_structure_reuses_artifacts_and_serializes_deterministically(
    monkeypatch,
) -> None:
    record, analysis, report = _report(monkeypatch, build_historical_input())
    first = build_serializable_replay_coaching_report(report)
    second = build_serializable_replay_coaching_report(report)

    assert report.decision_assessments is analysis.assessments
    assert report.prioritization is analysis.prioritization
    assert report.guidance is analysis.guidance
    assert list(first) == [
        "report_version",
        "report_method",
        "information_policy",
        "outcome_context_policy",
        "source_game_id",
        "source_review_method",
        "source_review_settings",
        "game_context",
        "outcome_context",
        "coverage_summary",
        "decision_assessments",
        "prioritization",
        "guidance",
        "player_summaries",
        "role_summaries",
        "phase_summaries",
        "contract_summaries",
        "limitations",
    ]
    assert first == second
    assert json.dumps(first, sort_keys=False) == json.dumps(second, sort_keys=False)
    assert first["source_review_method"] == HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD
    assert "derived_child_seed" not in _collect_keys(first["source_review_settings"])
    with pytest.raises(FrozenInstanceError):
        report.report_version = 2  # type: ignore[misc]
    with pytest.raises(TypeError):
        report.source_review_settings["base_search_seed"] = 2  # type: ignore[index]

    other = build_historical_input()
    other["game_id"] = "other-game"
    other_record = build_historical_game_record(other)
    with pytest.raises(ValueError, match="source"):
        build_replay_coaching_report(other_record, analysis)
    assert record.game_id == report.source_game_id


def test_report_rejects_noncanonical_contexts_settings_and_scope_indices(
    monkeypatch,
) -> None:
    record, analysis, report = _report(monkeypatch, build_historical_input())
    with pytest.raises(ValueError, match="unsupported fields"):
        replace(
            report.outcome_context,
            game_result_summary={"initial_hand": ["CA"]},
        )

    unsafe_result = dict(report.outcome_context.game_result_summary)
    unsafe_result["thresholds"] = {"initial_hand": ["CA"]}
    with pytest.raises(ValueError, match="private fields"):
        replace(
            report.outcome_context,
            game_result_summary=unsafe_result,
        )

    changed_result = dict(report.outcome_context.game_result_summary)
    changed_result["thresholds"] = {"declarer_win": 999}
    changed_outcome = replace(
        report.outcome_context,
        game_result_summary=changed_result,
    )
    with pytest.raises(ValueError, match="contexts"):
        replace(
            report,
            outcome_context=changed_outcome,
            historical_record=record,
            coaching_analysis=analysis,
        )

    changed_settings = _plain(report.source_review_settings)
    changed_settings["base_search_seed"] = 99
    with pytest.raises(ValueError, match="source settings"):
        replace(
            report,
            source_review_settings=changed_settings,
            historical_record=record,
            coaching_analysis=analysis,
        )

    summary = report.player_summaries[0]
    outside_index = next(
        index
        for index in range(1, report.coverage_summary.decision_count + 1)
        if index not in summary.decision_indices
    )
    with pytest.raises(ValueError, match="Key Decision indices"):
        replace(
            summary,
            key_decision_count=1,
            key_decision_indices=(outside_index,),
        )

    changed_public = _plain(analysis.public_review_summary)
    changed_public["decisions"][0]["immediate_baseline"]["recommendation"][
        "card"
    ] = "XX"
    changed_analysis = HistoricalSearchReviewCoachingAnalysis(
        public_review_summary=changed_public,
        assessments=analysis.assessments,
        prioritization=analysis.prioritization,
        guidance=analysis.guidance,
        historical_record=record,
    )
    with pytest.raises(ValueError, match="Immediate evidence"):
        build_replay_coaching_report(record, changed_analysis)


def test_report_serialization_excludes_private_deal_and_search_state(monkeypatch) -> None:
    for data in (
        add_continuation(
            TERMINAL_BUILDERS["defender_open_play"](),
            "declarer_card_exposure_continuation",
        ),
        TERMINAL_BUILDERS["open_card_throw"](),
    ):
        _, _, report = _report(monkeypatch, data)
        serialized = build_serializable_replay_coaching_report(report)
        keys = _collect_keys(serialized)

        assert not {
            "record",
            "initial_hand",
            "hand",
            "final_hidden_hands",
            "skat",
            "discarded_cards",
            "discards",
            "derived_tricks",
            "incomplete_current_trick",
            "selected_worlds",
            "ownership",
            "jack_ownership_evidence",
            "exact_proof",
            "theoretical_schwarz_assessment",
            "derived_child_seed",
            "cache",
            "branches",
            "principal_variation",
            "rating",
            "grade",
        }.intersection(keys)
        assert not {
            "exposed_cards",
            "public_declarer_cards",
            "thrown_cards",
            "card_reconciliation",
        }.intersection(_collect_keys(serialized["outcome_context"]))


def _decision_quality_counts(report):
    fields = (
        "decision_count",
        "assessable_decision_count",
        "forced_move_count",
        "best_or_equivalent_count",
        "strictly_below_best_count",
        "not_assessable_count",
    )
    return tuple(
        tuple(getattr(summary, field) for field in fields)
        for summaries in (
            report.player_summaries,
            report.role_summaries,
            report.phase_summaries,
            report.contract_summaries,
        )
        for summary in summaries
    )


def test_final_outcome_differences_do_not_change_coaching_or_scope_quality(
    monkeypatch,
) -> None:
    first_data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "defender_open_play_continuation",
    )
    second_data = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](),
        "defender_open_play_continuation",
    )
    second_data["game_id"] = first_data["game_id"]
    _, first_analysis, first_report = _report(monkeypatch, first_data)
    _, second_analysis, second_report = _report(monkeypatch, second_data)

    assert first_analysis.assessments == second_analysis.assessments
    assert first_analysis.prioritization.key_decisions == (
        second_analysis.prioritization.key_decisions
    )
    assert tuple(
        point
        for point in first_analysis.prioritization.turning_points
        if point.turning_point_type == "decision_opportunity"
    ) == tuple(
        point
        for point in second_analysis.prioritization.turning_points
        if point.turning_point_type == "decision_opportunity"
    )
    assert first_analysis.guidance.patterns == second_analysis.guidance.patterns
    assert first_analysis.guidance.decision_recommendations == (
        second_analysis.guidance.decision_recommendations
    )
    assert first_analysis.guidance.pattern_recommendations == (
        second_analysis.guidance.pattern_recommendations
    )
    assert _decision_quality_counts(first_report) == _decision_quality_counts(
        second_report
    )
    assert first_report.game_context.game_end_reason != (
        second_report.game_context.game_end_reason
    )
    assert first_report.outcome_context.final_settlement_summary != (
        second_report.outcome_context.final_settlement_summary
    )


def test_report_ignores_private_ownership_for_zero_decision_coaching(monkeypatch) -> None:
    original = _zero_decision_data()
    changed = copy.deepcopy(original)
    changed["players"][2]["initial_hand"][-1], changed["skat"][0] = (
        changed["skat"][0],
        changed["players"][2]["initial_hand"][-1],
    )
    _, original_analysis, original_report = _report(monkeypatch, original)
    _, changed_analysis, changed_report = _report(monkeypatch, changed)

    assert original_analysis.assessments == changed_analysis.assessments == ()
    assert original_analysis.prioritization == changed_analysis.prioritization
    assert original_analysis.guidance == changed_analysis.guidance
    assert original_report.coverage_summary == changed_report.coverage_summary
    assert _decision_quality_counts(original_report) == _decision_quality_counts(
        changed_report
    )


def test_one_pass_wrapper_preserves_public_review_and_call_counts(monkeypatch) -> None:
    record = build_historical_game_record(build_historical_input())
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )
    calls = {"search": 0, "immediate": 0}

    def search(**kwargs):
        calls["search"] += 1
        return _historical_fake_search(**kwargs)

    def immediate(**kwargs):
        calls["immediate"] += 1
        return _historical_fake_immediate(**kwargs)

    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )
    result = build_historical_replay_coaching_analysis(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
    )

    assert isinstance(result, HistoricalReplayCoachingAnalysis)
    assert calls == {"search": 30, "immediate": 30}
    assert result.report.decision_assessments is result.assessments
    assert result.report.prioritization is result.prioritization
    assert result.report.guidance is result.guidance

    calls = {"search": 0, "immediate": 0}
    public = build_historical_search_review_summary(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
    )
    assert calls == {"search": 30, "immediate": 30}
    assert _plain(result.public_review_summary) == public
    assert "report" not in _collect_keys(public)
    assert "guidance" not in _collect_keys(public)
    assert "prioritization" not in _collect_keys(public)


def test_public_builder_serializes_both_summaries_from_one_pass(monkeypatch) -> None:
    record = build_historical_game_record(build_historical_input())
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )
    calls = {"search": 0, "immediate": 0}

    def search(**kwargs):
        calls["search"] += 1
        return _historical_fake_search(**kwargs)

    def immediate(**kwargs):
        calls["immediate"] += 1
        return _historical_fake_immediate(**kwargs)

    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )

    result = build_historical_replay_coaching_public_summaries(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
        immediate_base_random_seed=7,
    )

    assert calls == {"search": 30, "immediate": 30}
    assert tuple(result) == (
        "historical_search_review_summary",
        "historical_replay_coaching_summary",
    )
    search_review = result["historical_search_review_summary"]
    coaching = result["historical_replay_coaching_summary"]
    assert search_review["decision_counts"]["decision_count"] == 30
    assert coaching["coverage_summary"]["decision_count"] == 30
    assert coaching["source_review_settings"] == search_review["settings"]
    assert coaching["outcome_context"]["source_game_id"] == record.game_id
    assert "derived_child_seed" not in _collect_keys(coaching)
