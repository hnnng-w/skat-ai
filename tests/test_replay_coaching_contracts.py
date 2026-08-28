from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest
from test_historical_game import (
    build_historical_input,
    rebuild_historical_suffix,
)
from test_historical_game_event_chain import (
    TERMINAL_BUILDERS,
    add_continuation,
)

from skatmind.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.deck import get_full_deck
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skatmind.historical_search_review import (
    HistoricalSearchReviewSettings,
    attach_historical_search_decision_retrospective_assessment,
    build_historical_search_decision_pre_actual_analysis,
    build_historical_search_decision_review,
)
from skatmind.replay_coaching_assessment import (
    REPLAY_COACHING_ASSESSMENT_STATUSES,
    REPLAY_COACHING_EVIDENCE_BASES,
    REPLAY_COACHING_FACTORS,
    REPLAY_COACHING_IMPACT_TIERS,
    REPLAY_COACHING_LIMITATIONS,
    ReplayCoachingDecisionAssessment,
    build_replay_coaching_decision_assessment,
    build_serializable_replay_coaching_decision_assessment,
)
from skatmind.replay_coaching_evidence import (
    REPLAY_COACHING_CONTRACT_VERSION,
    REPLAY_COACHING_GAME_PHASES,
    REPLAY_COACHING_INFORMATION_POLICY,
    DecisionTimeReplayCoachingEvidence,
    ImmediateReplayCoachingCandidate,
    ImmediateReplayCoachingEvidence,
    build_decision_time_replay_coaching_evidence,
    build_immediate_replay_coaching_evidence,
    build_serializable_decision_time_replay_coaching_evidence,
    canonicalize_replay_coaching_cards,
    get_replay_coaching_game_phase,
)
from skatmind.retrospective_search_comparison import (
    build_search_actual_card_comparison,
    build_search_vs_immediate_comparison,
)
from skatmind.rules import get_legal_cards
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION


def _budget() -> RequestedSearchBudget:
    return RequestedSearchBudget(
        max_remaining_tricks=5,
        max_depth_plies=15,
        max_nodes=10_000,
        max_selected_worlds=8,
        max_sampled_worlds=8,
        minimum_comparable_worlds=2,
        wall_clock_timeout_ms=100,
    )


def _search_result(
    metrics: tuple[tuple[str, int, float, float | None], ...],
    *,
    game_type: str = "grand",
    status: str = "complete",
    coverage: str = "all_compatible_worlds",
) -> BoundedSearchResult:
    if status == "unavailable":
        return BoundedSearchResult(
            schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
            analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
            search_method="compatible_world_minimax_v1",
            game_type=game_type,
            status="unavailable",
            stop_reason="remaining_trick_limit_exceeded",
            world_coverage="none",
            solution_claim="none",
            terminal_utility_version=TERMINAL_UTILITY_VERSION,
            requested_budget=_budget(),
            consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
            compatible_world_count=None,
            candidate_results=(),
            recommended_card=None,
            fallback_used=False,
            fallback_method=None,
        )

    selected = 4
    completed = 4 if status == "complete" else 2
    sampled = selected if coverage == "sampled_compatible_worlds" else 0
    candidates = tuple(
        AggregateSearchCandidateResult(
            card=card,
            rank=1,
            is_recommended=False,
            completed_world_count=completed,
            local_contract_success_count=successes,
            local_contract_success_rate=successes / completed,
            mean_local_side_game_score=score,
            mean_local_side_card_point_margin=margin,
        )
        for card, successes, score, margin in metrics
    )
    ranked = rank_search_candidate_results(candidates, game_type, recommend=True)
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type=game_type,
        status=status,
        stop_reason=(
            "completed"
            if status == "complete"
            else "wall_clock_timeout"
            if status == "timeout"
            else "node_budget_exhausted"
        ),
        world_coverage=coverage,
        solution_claim=(
            "exact_per_selected_world"
            if status == "complete"
            else "none"
            if status == "timeout"
            else "node_limited_partial"
        ),
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=_budget(),
        consumed_budget=ConsumedSearchBudget(
            depth_reached=8,
            nodes_expanded=100,
            selected_world_count=selected,
            completed_world_count=completed,
            sampled_world_count=sampled,
            unique_sampled_world_count=sampled,
            wall_clock_elapsed_ms=5,
        ),
        compatible_world_count=selected if coverage == "all_compatible_worlds" else 20,
        candidate_results=ranked,
        recommended_card=ranked[0].card,
        fallback_used=False,
        fallback_method=None,
    )


def _immediate_evidence(
    values: tuple[tuple[str, float, float], ...],
    *,
    game_type: str = "grand",
    available: bool = True,
) -> ImmediateReplayCoachingEvidence:
    if not available:
        return ImmediateReplayCoachingEvidence(
            is_available=False,
            unavailable_reason="immediate_analysis_unavailable",
            recommended_card=None,
            candidate_count=0,
            candidates=(),
        )
    best_card = min(
        values,
        key=lambda item: (-item[2], get_full_deck().index(item[0])),
    )[0]
    report = [
        {
            "card": card,
            "win_rate": 1.0 - objective if game_type == "null" else 0.5,
            "average_trick_points": 5.0,
            "average_points_won": swing,
            "average_points_lost": 0.0,
            "expected_point_swing": swing,
            "expected_objective_utility": objective,
            "is_recommended": card == best_card,
        }
        for card, swing, objective in values
    ]
    return build_immediate_replay_coaching_evidence(
        legal_cards=[card for card, _, _ in reversed(values)],
        analysis_report=report,
        recommended_card=best_card,
        unavailable_reason=None,
        game_type=game_type,
        player_role="declarer",
    )


def _evidence(
    search_result: BoundedSearchResult,
    *,
    immediate: ImmediateReplayCoachingEvidence | None = None,
    trick_number: int = 8,
    play_index: int = 1,
    local_side: str = "declarer",
    acting_seat: str = "forehand",
) -> DecisionTimeReplayCoachingEvidence:
    legal_cards = (
        tuple(candidate.card for candidate in search_result.candidate_results)
        if search_result.candidate_results
        else ("CA", "S7")
    )
    immediate = immediate or _immediate_evidence(
        tuple((card, float(len(legal_cards) - index), float(len(legal_cards) - index))
              for index, card in enumerate(legal_cards)),
        game_type=search_result.game_type,
    )
    report = [
        {
            "card": candidate.card,
            "win_rate": (
                1.0 - candidate.objective_utility
                if search_result.game_type == "null"
                else 0.5
            ),
            "average_points_won": candidate.expected_point_swing,
            "average_points_lost": 0.0,
            "expected_point_swing": candidate.expected_point_swing,
            "expected_objective_utility": candidate.objective_utility,
            "is_recommended": candidate.is_recommended,
        }
        for candidate in immediate.candidates
    ]
    comparison = build_search_vs_immediate_comparison(
        search_result,
        immediate.recommended_card,
        report,
        search_result.game_type,
        "declarer",
    )
    return build_decision_time_replay_coaching_evidence(
        source_game_id="game-120",
        decision_index=(trick_number - 1) * 3 + play_index,
        trick_number=trick_number,
        play_index=play_index,
        acting_player_id="player-a",
        acting_seat=acting_seat,
        local_side=local_side,
        game_type=search_result.game_type,
        legal_cards=legal_cards,
        immediate_evidence=immediate,
        bounded_search_result=search_result,
        search_vs_immediate_comparison=comparison,
    )


def _assessment(
    evidence: DecisionTimeReplayCoachingEvidence,
    actual_card: str,
    quality: str = "optimal",
) -> ReplayCoachingDecisionAssessment:
    return build_replay_coaching_decision_assessment(
        decision_time_evidence=evidence,
        actual_card=actual_card,
        search_actual_card_comparison=build_search_actual_card_comparison(
            evidence.bounded_search_result, actual_card
        ),
        immediate_baseline_quality=quality,
    )


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_collect_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_collect_keys(item) for item in value))
    return set()


@pytest.mark.parametrize(
    ("trick_number", "phase"),
    [(1, "opening"), (3, "opening"), (4, "middle"), (7, "middle"), (8, "endgame"), (10, "endgame")],
)
def test_versioned_game_phase_boundaries(trick_number: int, phase: str) -> None:
    assert REPLAY_COACHING_CONTRACT_VERSION == 1
    assert REPLAY_COACHING_GAME_PHASES == ("opening", "middle", "endgame")
    assert get_replay_coaching_game_phase(trick_number) == phase


@pytest.mark.parametrize("trick_number", [0, 11, True, 1.5])
def test_game_phase_rejects_other_trick_numbers(trick_number) -> None:
    with pytest.raises(ValueError, match="1 through 10"):
        get_replay_coaching_game_phase(trick_number)


def test_contract_vocabularies_have_stable_priority_and_order() -> None:
    assert REPLAY_COACHING_INFORMATION_POLICY == (
        "decision_time_then_retrospective_attachment"
    )
    assert REPLAY_COACHING_ASSESSMENT_STATUSES == (
        "forced_move",
        "best_or_equivalent",
        "strictly_below_best",
        "not_assessable",
    )
    assert REPLAY_COACHING_EVIDENCE_BASES == (
        "all_compatible_worlds",
        "sampled_compatible_worlds",
        "completed_common_prefix",
        "immediate_expected_value",
        "none",
    )
    assert REPLAY_COACHING_IMPACT_TIERS == (
        "no_missed_impact",
        "contract_success",
        "settlement_score",
        "card_point_margin",
        "immediate_only",
        "not_assessable",
    )
    assert REPLAY_COACHING_FACTORS[0] == "forced_move"
    assert REPLAY_COACHING_FACTORS[-1] == "null_margin_not_applicable"
    assert REPLAY_COACHING_LIMITATIONS[0:2] == (
        "bounded_late_game_search",
        "determinization_strategy_fusion",
    )
    assert REPLAY_COACHING_LIMITATIONS[-1] == "no_assessable_evidence"


def test_evidence_is_frozen_defensively_copied_and_deterministically_serialized() -> None:
    legal_cards = ["S7", "CA"]
    report = [
        {
            "card": "CA",
            "win_rate": 0.6,
            "average_points_won": 2.0,
            "average_points_lost": 0.0,
            "expected_point_swing": 2.0,
            "is_recommended": True,
        },
        {
            "card": "S7",
            "win_rate": 0.4,
            "average_points_won": 1.0,
            "average_points_lost": 0.0,
            "expected_point_swing": 1.0,
            "is_recommended": False,
        },
    ]
    immediate = build_immediate_replay_coaching_evidence(
        legal_cards=legal_cards,
        analysis_report=report,
        recommended_card="CA",
        unavailable_reason=None,
        game_type="grand",
        player_role="declarer",
    )
    search = _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
    evidence = _evidence(search, immediate=immediate)
    serialized = build_serializable_decision_time_replay_coaching_evidence(evidence)
    legal_cards.clear()
    report[0]["card"] = "D7"

    assert evidence.legal_cards == ("CA", "S7")
    assert tuple(candidate.card for candidate in immediate.candidates) == ("CA", "S7")
    assert serialized == build_serializable_decision_time_replay_coaching_evidence(evidence)
    with pytest.raises(FrozenInstanceError):
        evidence.game_phase = "opening"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        immediate.candidates[0].rank = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    ("game_type", "play_index", "acting_seat", "local_side"),
    [
        ("clubs", 1, "forehand", "declarer"),
        ("spades", 2, "middlehand", "defenders"),
        ("hearts", 3, "rearhand", "declarer"),
        ("diamonds", 1, "middlehand", "defenders"),
        ("grand", 2, "rearhand", "declarer"),
        ("null", 3, "forehand", "defenders"),
    ],
)
def test_evidence_supports_all_game_types_sides_seats_and_root_seats(
    game_type: str,
    play_index: int,
    acting_seat: str,
    local_side: str,
) -> None:
    margin = None if game_type == "null" else 5.0
    evidence = _evidence(
        _search_result((("CA", 4, 10.0, margin), ("S7", 2, 0.0, margin)), game_type=game_type),
        immediate=_immediate_evidence((("CA", 2.0, 2.0), ("S7", 1.0, 1.0)), game_type=game_type),
        play_index=play_index,
        acting_seat=acting_seat,
        local_side=local_side,
    )

    assert evidence.game_type == game_type
    assert evidence.root_seat == ("lead", "second", "third")[play_index - 1]
    assert evidence.local_side == local_side


def test_decision_time_serialization_excludes_retrospective_and_private_search_data() -> None:
    evidence = _evidence(
        _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
    )
    serialized = build_serializable_decision_time_replay_coaching_evidence(evidence)
    forbidden = {
        "actual_card",
        "actual_card_played",
        "future_plays",
        "final_winner",
        "final_game_result",
        "final_settlement",
        "final_hidden_hands",
        "final_skat",
        "derived_seed",
        "private_hand",
        "transposition_state",
        "principal_variation",
    }

    assert forbidden.isdisjoint(_collect_keys(serialized))
    assert "hidden" not in str(serialized).lower()


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("contract_version", 2, "contract version"),
        ("decision_index", 23, "decision_index"),
        ("game_phase", "opening", "game_phase"),
        ("root_seat", "third", "root_seat"),
        ("local_side", "unknown", "local_side"),
        ("acting_seat", "left", "acting_seat"),
        ("game_type", "ramsch", "game_type"),
    ],
)
def test_decision_time_contract_rejects_identity_and_relationship_mismatches(
    field_name: str, value, message: str
) -> None:
    evidence = _evidence(
        _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
    )
    with pytest.raises(ValueError, match=message):
        replace(evidence, **{field_name: value})


def test_canonical_cards_and_immediate_alignment_are_strict() -> None:
    assert canonicalize_replay_coaching_cards(["D7", "CA", "S7"]) == (
        "CA",
        "S7",
        "D7",
    )
    with pytest.raises(ValueError, match="unique"):
        canonicalize_replay_coaching_cards(["CA", "CA"])
    with pytest.raises(ValueError, match="canonical deck order"):
        replace(
            _evidence(
                _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
            ),
            legal_cards=("S7", "CA"),
        )
    tied = ImmediateReplayCoachingEvidence(
        is_available=True,
        unavailable_reason=None,
        recommended_card="S7",
        candidate_count=2,
        candidates=(
            ImmediateReplayCoachingCandidate("S7", 1, True, 1.0, 1.0),
            ImmediateReplayCoachingCandidate("CA", 2, False, 1.0, 1.0),
        ),
    )
    assert tied.recommended_card == "S7"
    assert tuple(candidate.card for candidate in tied.candidates) == ("S7", "CA")
    normalized_tie = build_immediate_replay_coaching_evidence(
        legal_cards=["CA", "S7"],
        analysis_report=[
            {
                "card": "S7",
                "win_rate": 0.5,
                "average_points_won": 1.0,
                "average_points_lost": 0.0,
                "expected_point_swing": 1.0,
                "is_recommended": True,
            },
            {
                "card": "CA",
                "win_rate": 0.5,
                "average_points_won": 1.0,
                "average_points_lost": 0.0,
                "expected_point_swing": 1.0,
                "is_recommended": False,
            },
        ],
        recommended_card="S7",
        unavailable_reason=None,
        game_type="grand",
        player_role="declarer",
    )
    assert normalized_tie.recommended_card == "S7"
    assert tuple(candidate.card for candidate in normalized_tie.candidates) == (
        "S7",
        "CA",
    )
    with pytest.raises(ValueError, match="existing objective ranking"):
        replace(
            tied,
            candidates=(
                ImmediateReplayCoachingCandidate("S7", 1, True, 1.0, 0.0),
                ImmediateReplayCoachingCandidate("CA", 2, False, 1.0, 1.0),
            ),
        )


@pytest.mark.parametrize(
    ("status", "coverage", "expected_basis", "expected_extra_limitation"),
    [
        ("complete", "all_compatible_worlds", "all_compatible_worlds", None),
        (
            "complete",
            "sampled_compatible_worlds",
            "sampled_compatible_worlds",
            "sampled_compatible_worlds",
        ),
        (
            "partial",
            "sampled_compatible_worlds",
            "completed_common_prefix",
            "completed_common_prefix",
        ),
        (
            "timeout",
            "sampled_compatible_worlds",
            "completed_common_prefix",
            "completed_common_prefix",
        ),
    ],
)
def test_search_evidence_bases_and_limitations_cover_exact_sampled_partial_and_timeout(
    status: str,
    coverage: str,
    expected_basis: str,
    expected_extra_limitation: str | None,
) -> None:
    evidence = _evidence(
        _search_result(
            (("CA", 4 if status == "complete" else 2, 20.0, 10.0), ("S7", 1, 0.0, 0.0)),
            status=status,
            coverage=coverage,
        )
    )
    assessment = _assessment(evidence, "CA")

    assert assessment.evidence_basis == expected_basis
    assert assessment.limitations[:2] == (
        "bounded_late_game_search",
        "determinization_strategy_fusion",
    )
    assert assessment.limitations[-1] == "observed_card_not_ground_truth"
    if expected_extra_limitation is not None:
        assert expected_extra_limitation in assessment.limitations


def test_forced_move_precedes_evidence_quality() -> None:
    evidence = _evidence(
        _search_result((("CA", 4, 20.0, 10.0),)),
        immediate=_immediate_evidence((("CA", 2.0, 2.0),)),
    )
    assessment = _assessment(evidence, "CA", quality="mistake")

    assert assessment.assessment_status == "forced_move"
    assert assessment.impact_tier == "no_missed_impact"
    assert assessment.strictly_better_card_count == 0
    assert assessment.factors == ("forced_move",)
    assert assessment.immediate_baseline_quality == "mistake"


def test_aggregate_equivalent_canonical_tie_is_best_without_missed_impact() -> None:
    evidence = _evidence(
        _search_result((("S7", 3, 20.0, 8.0), ("CA", 3, 20.0, 8.0)))
    )
    assessment = _assessment(evidence, "S7")

    assert evidence.bounded_search_result.recommended_card == "CA"
    assert assessment.actual_card_rank == 2
    assert assessment.aggregate_equivalent is True
    assert assessment.assessment_status == "best_or_equivalent"
    assert assessment.impact_tier == "no_missed_impact"
    assert assessment.factors == ("aggregate_equivalent_choice",)


def test_exact_search_best_card_needs_no_equivalent_alternative_factor() -> None:
    evidence = _evidence(
        _search_result((("CA", 4, 20.0, 8.0), ("S7", 3, 10.0, 4.0)))
    )
    assessment = _assessment(evidence, "CA")

    assert assessment.assessment_status == "best_or_equivalent"
    assert assessment.aggregate_equivalent is True
    assert assessment.factors == ()


@pytest.mark.parametrize(
    ("metrics", "impact", "factor"),
    [
        (
            (("CA", 4, 20.0, 10.0), ("S7", 2, 40.0, 30.0)),
            "contract_success",
            "strictly_lower_contract_success",
        ),
        (
            (("CA", 4, 20.0, 10.0), ("S7", 4, 10.0, 30.0)),
            "settlement_score",
            "strictly_lower_settlement_score",
        ),
        (
            (("CA", 4, 20.0, 10.0), ("S7", 4, 20.0, 5.0)),
            "card_point_margin",
            "strictly_lower_card_point_margin",
        ),
    ],
)
def test_search_uses_first_positive_lexicographic_impact(
    metrics, impact: str, factor: str
) -> None:
    assessment = _assessment(_evidence(_search_result(metrics)), "S7")

    assert assessment.assessment_status == "strictly_below_best"
    assert assessment.impact_tier == impact
    assert assessment.factors == (factor,)


def test_null_never_uses_card_point_margin_impact() -> None:
    evidence = _evidence(
        _search_result(
            (("CA", 4, 23.0, None), ("S7", 4, -46.0, None)),
            game_type="null",
        ),
        immediate=_immediate_evidence(
            (("CA", -2.0, 1.0), ("S7", 10.0, 0.0)), game_type="null"
        ),
    )
    assessment = _assessment(evidence, "S7", quality="mistake")

    assert assessment.impact_tier == "settlement_score"
    assert assessment.search_actual_card_comparison.mean_local_side_card_point_margin_gap is None
    assert assessment.factors == (
        "strictly_lower_settlement_score",
        "null_margin_not_applicable",
    )
    with pytest.raises(ValueError, match="Null assessments"):
        replace(assessment, impact_tier="card_point_margin")


@pytest.mark.parametrize(
    ("actual_card", "status", "impact", "factor"),
    [
        ("CA", "best_or_equivalent", "no_missed_impact", "immediate_only_best_or_equivalent"),
        ("S7", "strictly_below_best", "immediate_only", "immediate_only_better_alternative"),
    ],
)
def test_immediate_only_classification_does_not_map_quality_names(
    actual_card: str, status: str, impact: str, factor: str
) -> None:
    search = _search_result((), status="unavailable")
    immediate = _immediate_evidence((("CA", 5.0, 5.0), ("S7", 1.0, 1.0)))
    assessment = _assessment(
        _evidence(search, immediate=immediate), actual_card, quality="mistake"
    )

    assert assessment.assessment_status == status
    assert assessment.impact_tier == impact
    assert assessment.immediate_baseline_quality == "mistake"
    assert assessment.factors == (factor, "search_unavailable")
    assert assessment.limitations == (
        "immediate_expected_value_only",
        "search_unavailable",
        "observed_card_not_ground_truth",
    )


def test_no_evidence_is_not_assessable_with_consistent_empty_fields() -> None:
    search = _search_result((), status="unavailable")
    evidence = _evidence(
        search,
        immediate=_immediate_evidence((), available=False),
    )
    assessment = _assessment(evidence, "CA", quality="not_available")

    assert assessment.assessment_status == "not_assessable"
    assert assessment.evidence_basis == "none"
    assert assessment.impact_tier == "not_assessable"
    assert assessment.best_card is None
    assert assessment.actual_card_rank is None
    assert assessment.strictly_better_card_count is None
    assert assessment.factors == ("search_unavailable", "no_assessable_evidence")
    assert assessment.limitations == (
        "search_unavailable",
        "observed_card_not_ground_truth",
        "no_assessable_evidence",
    )


def test_strictly_below_search_requires_a_positive_supported_gap() -> None:
    evidence = _evidence(
        _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
    )
    comparison = build_search_actual_card_comparison(evidence.bounded_search_result, "S7")
    object.__setattr__(comparison, "contract_success_rate_gap", 0.0)
    object.__setattr__(comparison, "mean_local_side_game_score_gap", 0.0)
    object.__setattr__(comparison, "mean_local_side_card_point_margin_gap", 0.0)

    with pytest.raises(ValueError, match="positive supported gap"):
        build_replay_coaching_decision_assessment(
            decision_time_evidence=evidence,
            actual_card="S7",
            search_actual_card_comparison=comparison,
            immediate_baseline_quality="mistake",
        )


def test_assessment_rejects_search_comparison_from_other_aggregate() -> None:
    evidence = _evidence(
        _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
    )
    comparison = build_search_actual_card_comparison(
        _search_result((("CA", 4, 20.0, 10.0), ("S7", 4, 0.0, 0.0))),
        "S7",
    )

    with pytest.raises(ValueError, match="bounded Search result"):
        build_replay_coaching_decision_assessment(
            decision_time_evidence=evidence,
            actual_card="S7",
            search_actual_card_comparison=comparison,
            immediate_baseline_quality="mistake",
        )


def test_assessment_validation_rejects_invalid_combinations_and_order() -> None:
    assessment = _assessment(
        _evidence(
            _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
        ),
        "S7",
        quality="mistake",
    )

    with pytest.raises(ValueError, match="actual_card must be legal"):
        replace(assessment, actual_card="D7")
    with pytest.raises(ValueError, match="first positive gap"):
        replace(assessment, impact_tier="settlement_score")
    with pytest.raises(ValueError, match="canonical order"):
        replace(
            assessment,
            factors=("strictly_lower_contract_success", "forced_move"),
        )
    with pytest.raises(ValueError, match="evidence basis"):
        replace(assessment, limitations=("observed_card_not_ground_truth",))
    with pytest.raises(FrozenInstanceError):
        assessment.impact_tier = "no_missed_impact"  # type: ignore[misc]


def test_assessment_serialization_adds_only_observed_comparison_context() -> None:
    assessment = _assessment(
        _evidence(
            _search_result((("CA", 4, 20.0, 10.0), ("S7", 2, 0.0, 0.0)))
        ),
        "S7",
        quality="mistake",
    )
    serialized = build_serializable_replay_coaching_decision_assessment(assessment)

    assert serialized["actual_card"] == "S7"
    assert "actual_card" not in serialized["decision_time_evidence"]
    assert {
        "final_winner",
        "final_game_result",
        "final_settlement",
        "final_hidden_hands",
        "final_skat",
        "later_event_details",
    }.isdisjoint(_collect_keys(serialized))
    assert "principal_variation" not in _collect_keys(serialized)


def _historical_fake_immediate(*, state, **_kwargs):
    legal_cards = get_legal_cards(state.hand, state.current_trick, state.game_type)
    recommended = canonicalize_replay_coaching_cards(legal_cards)[0]
    values = {
        card: {
            "win_rate": (
                0.0 if card == recommended else 1.0
                if state.game_type == "null"
                else 1.0 if card == recommended else 0.0
            ),
            "average_trick_points": 5.0 if card == recommended else 0.0,
            "average_points_won": 5.0 if card == recommended else 0.0,
            "average_points_lost": 0.0,
        }
        for card in legal_cards
    }
    return recommended, "replay coaching test Immediate", values


def _historical_fake_search(*, information_view, requested_budget, random_seed):
    del random_seed
    legal_cards = canonicalize_replay_coaching_cards(
        get_legal_cards(
            list(information_view.local_remaining_hand),
            [play.card for play in information_view.current_trick],
            information_view.game_type,
        )
    )
    completed = 1
    candidates = rank_search_candidate_results(
        tuple(
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=completed,
                local_contract_success_count=int(index == 0),
                local_contract_success_rate=float(index == 0),
                mean_local_side_game_score=float(len(legal_cards) - index),
                mean_local_side_card_point_margin=(
                    None
                    if information_view.game_type == "null"
                    else float(len(legal_cards) - index)
                ),
            )
            for index, card in enumerate(legal_cards)
        ),
        information_view.game_type,
        recommend=True,
    )
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type=information_view.game_type,
        status="complete",
        stop_reason="completed",
        world_coverage="all_compatible_worlds",
        solution_claim="exact_per_selected_world",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(1, 1, 1, 1, 0, 0, 0),
        compatible_world_count=1,
        candidate_results=candidates,
        recommended_card=candidates[0].card,
        fallback_used=False,
        fallback_method=None,
    )


def _historical_inputs(data: dict):
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    return record, summary, build_historical_decision_snapshots(summary)


@pytest.mark.parametrize(
    ("hand_game", "ouvert"),
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_pre_actual_path_supports_all_four_null_variants(
    monkeypatch, hand_game: bool, ouvert: bool
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    data = build_historical_input(game_type="null", hand_game=hand_game)
    data["declaration"]["ouvert"] = ouvert
    record, _, snapshots = _historical_inputs(data)

    analysis = build_historical_search_decision_pre_actual_analysis(
        snapshots.snapshots[-1],
        record,
        HistoricalSearchReviewSettings(17, immediate_sample_count=1),
    )

    assert analysis.position.game_declaration.hand_game is hand_game
    assert analysis.position.game_declaration.ouvert is ouvert
    assert analysis.decision_time_evidence.game_type == "null"


def test_historical_path_preserves_declarer_defender_and_all_root_seats(monkeypatch) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    record, _, snapshots = _historical_inputs(build_historical_input())
    analyses = [
        build_historical_search_decision_pre_actual_analysis(
            snapshot,
            record,
            HistoricalSearchReviewSettings(19, immediate_sample_count=1),
        )
        for snapshot in snapshots.snapshots[:3]
    ]

    assert {item.decision_time_evidence.local_side for item in analyses} == {
        "declarer",
        "defenders",
    }
    assert [item.decision_time_evidence.root_seat for item in analyses] == [
        "lead",
        "second",
        "third",
    ]


def test_null_defender_immediate_utility_comes_from_original_analysis_values(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )

    def null_defender_immediate(*, state, **_kwargs):
        legal_cards = canonicalize_replay_coaching_cards(
            get_legal_cards(state.hand, state.current_trick, state.game_type)
        )
        recommended = legal_cards[0]
        values = {
            card: {
                "win_rate": 0.1 if card == recommended else 0.9,
                "average_trick_points": 5.0,
                "average_points_won": 5.0,
                "average_points_lost": 0.0,
                "expected_objective_utility": (
                    0.9 if card == recommended else 0.1
                ),
            }
            for card in legal_cards
        }
        return recommended, "Null defender objective fixture", values

    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        null_defender_immediate,
    )
    record, _, snapshots = _historical_inputs(
        build_historical_input(game_type="null")
    )
    snapshot = next(item for item in snapshots.snapshots if item.acting_side == "defenders")
    analysis = build_historical_search_decision_pre_actual_analysis(
        snapshot,
        record,
        HistoricalSearchReviewSettings(21, immediate_sample_count=1),
    )

    immediate = analysis.decision_time_evidence.immediate_evidence
    assert immediate.recommended_card == immediate.candidates[0].card
    assert immediate.candidates[0].objective_utility == 0.9


def test_pre_actual_analysis_report_is_deeply_read_only(monkeypatch) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    record, _, snapshots = _historical_inputs(build_historical_input())
    analysis = build_historical_search_decision_pre_actual_analysis(
        snapshots.snapshots[0],
        record,
        HistoricalSearchReviewSettings(22, immediate_sample_count=1),
    )

    with pytest.raises(TypeError):
        analysis.immediate_report[0]["card"] = "D7"  # type: ignore[index]


def test_actual_card_changes_only_retrospective_attachment(monkeypatch) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    record, _, snapshots = _historical_inputs(build_historical_input())
    snapshot = snapshots.snapshots[0]
    alternate_card = next(
        card
        for card in snapshot.visible_state.legal_cards
        if card != snapshot.actual_card_played
    )
    changed_snapshot = replace(snapshot, actual_card_played=alternate_card)
    settings = HistoricalSearchReviewSettings(23, immediate_sample_count=1)
    original = build_historical_search_decision_pre_actual_analysis(snapshot, record, settings)
    changed = build_historical_search_decision_pre_actual_analysis(
        changed_snapshot, record, settings
    )
    original_attachment = attach_historical_search_decision_retrospective_assessment(
        snapshot, original
    )
    changed_attachment = attach_historical_search_decision_retrospective_assessment(
        changed_snapshot, changed
    )

    assert original.decision_time_evidence == changed.decision_time_evidence
    assert original_attachment.coaching_assessment.actual_card != (
        changed_attachment.coaching_assessment.actual_card
    )
    assert original_attachment.coaching_assessment.decision_time_evidence == (
        changed_attachment.coaching_assessment.decision_time_evidence
    )


def test_future_plays_hidden_hands_winner_and_settlement_do_not_change_evidence(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    original_data = build_historical_input()
    changed_data = rebuild_historical_suffix(original_data, completed_prefix_tricks=5)
    original_record, _, original_snapshots = _historical_inputs(original_data)
    changed_record, _, changed_snapshots = _historical_inputs(changed_data)
    settings = HistoricalSearchReviewSettings(29, immediate_sample_count=1)
    original = build_historical_search_decision_pre_actual_analysis(
        original_snapshots.snapshots[14], original_record, settings
    )
    changed = build_historical_search_decision_pre_actual_analysis(
        changed_snapshots.snapshots[14], changed_record, settings
    )

    assert original_data["tricks"][5:] != changed_data["tricks"][5:]
    assert original_record.players == changed_record.players
    assert original.decision_time_evidence == changed.decision_time_evidence


def test_final_hidden_skat_does_not_change_first_decision_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    original_deck = get_full_deck()
    changed_deck = original_deck.copy()
    changed_deck[20], changed_deck[30] = changed_deck[30], changed_deck[20]
    original_record, _, original_snapshots = _historical_inputs(
        build_historical_input(deck=original_deck)
    )
    changed_record, _, changed_snapshots = _historical_inputs(
        build_historical_input(deck=changed_deck)
    )
    settings = HistoricalSearchReviewSettings(31, immediate_sample_count=1)
    original = build_historical_search_decision_pre_actual_analysis(
        original_snapshots.snapshots[0], original_record, settings
    )
    changed = build_historical_search_decision_pre_actual_analysis(
        changed_snapshots.snapshots[0], changed_record, settings
    )

    assert original_record.skat != changed_record.skat
    assert original_snapshots.snapshots[0] == changed_snapshots.snapshots[0]
    assert original.decision_time_evidence == changed.decision_time_evidence


@pytest.mark.parametrize(
    "continuation_kind",
    ["defender_open_play_continuation", "declarer_card_exposure_continuation"],
)
def test_later_terminal_shortening_does_not_change_decision_time_evidence(
    monkeypatch, continuation_kind: str
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    first = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](), continuation_kind
    )
    second = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](), continuation_kind
    )
    second["game_id"] = first["game_id"]
    first_record, first_summary, first_snapshots = _historical_inputs(first)
    second_record, second_summary, second_snapshots = _historical_inputs(second)
    settings = HistoricalSearchReviewSettings(37, immediate_sample_count=1)
    first_analysis = build_historical_search_decision_pre_actual_analysis(
        first_snapshots.snapshots[16], first_record, settings
    )
    second_analysis = build_historical_search_decision_pre_actual_analysis(
        second_snapshots.snapshots[16], second_record, settings
    )

    assert first["game_end_reason"] != second["game_end_reason"]
    assert first_summary["game_result_summary"] != second_summary["game_result_summary"]
    assert first_summary["final_settlement_summary"] != (
        second_summary["final_settlement_summary"]
    )
    assert first_analysis.decision_time_evidence == second_analysis.decision_time_evidence


def test_legacy_historical_search_review_contains_no_coaching_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    record, _, snapshots = _historical_inputs(build_historical_input())
    decision = build_historical_search_decision_review(
        snapshots.snapshots[0],
        record,
        HistoricalSearchReviewSettings(41, immediate_sample_count=1),
    )

    assert set(decision) == {
        "source_game_id",
        "decision_index",
        "trick_number",
        "play_index",
        "acting_player_id",
        "acting_seat",
        "acting_side",
        "game_type",
        "local_side",
        "root_seat",
        "remaining_tricks",
        "actual_card",
        "immediate_baseline",
        "bounded_search_result",
        "search_actual_card_comparison",
        "search_vs_immediate_comparison",
    }
    assert all("coaching" not in key for key in _collect_keys(decision))
