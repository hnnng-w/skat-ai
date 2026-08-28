import copy
from dataclasses import FrozenInstanceError, replace

import pytest
from test_historical_game import (
    build_historical_input,
    build_typed_historical_review_inputs,
    rebuild_historical_suffix,
)
from test_historical_game_event_chain import TERMINAL_BUILDERS, add_continuation
from test_replay_coaching_contracts import (
    _assessment,
    _evidence,
    _historical_fake_immediate,
    _historical_fake_search,
    _immediate_evidence,
    _search_result,
)

from skatmind.bounded_search_result import rank_search_candidate_results
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skatmind.historical_search_review import (
    build_historical_search_review_internal_result,
)
from skatmind.replay_coaching_assessment import ReplayCoachingDecisionAssessment
from skatmind.replay_coaching_key_decisions import (
    MAX_REPLAY_COACHING_KEY_DECISIONS,
    REPLAY_COACHING_KEY_DECISION_SELECTION_REASONS,
    REPLAY_COACHING_PRIORITIZATION_VERSION,
    ReplayCoachingKeyDecision,
    build_replay_coaching_key_decisions,
    build_serializable_replay_coaching_key_decision,
    get_replay_coaching_primary_gap,
)
from skatmind.replay_coaching_prioritization import (
    ReplayCoachingPrioritizationResult,
    build_replay_coaching_prioritization_result,
    build_serializable_replay_coaching_prioritization_result,
    validate_replay_coaching_assessment_sequence,
)
from skatmind.replay_coaching_turning_points import (
    REPLAY_COACHING_TURNING_POINT_FACTORS,
    REPLAY_COACHING_TURNING_POINT_LIMITATIONS,
    ReplayCoachingTurningPoint,
    build_recorded_decision_state_timeline,
    build_serializable_replay_coaching_turning_point,
    validate_recorded_decision_state_timeline,
)


def _at_decision(
    assessment: ReplayCoachingDecisionAssessment,
    decision_index: int,
) -> ReplayCoachingDecisionAssessment:
    trick_number = (decision_index - 1) // 3 + 1
    play_index = (decision_index - 1) % 3 + 1
    evidence = replace(
        assessment.decision_time_evidence,
        decision_index=decision_index,
        trick_number=trick_number,
        play_index=play_index,
        root_seat=("lead", "second", "third")[play_index - 1],
        game_phase=(
            "opening" if trick_number <= 3 else "middle" if trick_number <= 7 else "endgame"
        ),
    )
    return _assessment(evidence, assessment.actual_card, assessment.immediate_baseline_quality)


def _search_gap_assessment(
    decision_index: int,
    impact: str,
    *,
    evidence_basis: str = "all_compatible_worlds",
    primary_gap: float = 1.0,
    better_card_count: int = 1,
    game_type: str = "grand",
    local_side: str = "declarer",
) -> ReplayCoachingDecisionAssessment:
    cards = ("CA", "S7", "H7")[: better_card_count + 1]
    completed_world_count = 2 if evidence_basis == "completed_common_prefix" else 4
    if impact == "contract_success":
        metrics = tuple(
            (
                card,
                completed_world_count if index < better_card_count else 0,
                0.0,
                None if game_type == "null" else 0.0,
            )
            for index, card in enumerate(cards)
        )
    elif impact == "settlement_score":
        metrics = tuple(
            (
                card,
                completed_world_count,
                primary_gap if index < better_card_count else 0.0,
                None if game_type == "null" else 0.0,
            )
            for index, card in enumerate(cards)
        )
    elif impact == "card_point_margin":
        metrics = tuple(
            (
                card,
                completed_world_count,
                0.0,
                primary_gap if index < better_card_count else 0.0,
            )
            for index, card in enumerate(cards)
        )
    else:
        raise AssertionError(f"Unsupported test impact: {impact}")
    status = "partial" if evidence_basis == "completed_common_prefix" else "complete"
    coverage = (
        "sampled_compatible_worlds"
        if evidence_basis != "all_compatible_worlds"
        else "all_compatible_worlds"
    )
    assessment = _assessment(
        _evidence(
            _search_result(
                metrics,
                game_type=game_type,
                status=status,
                coverage=coverage,
            ),
            local_side=local_side,
        ),
        cards[-1],
        quality="mistake",
    )
    return _at_decision(assessment, decision_index)


def _immediate_gap_assessment(
    decision_index: int,
    *,
    game_type: str = "grand",
    local_side: str = "declarer",
    best_swing: float = 5.0,
    actual_swing: float = 1.0,
    best_utility: float = 5.0,
    actual_utility: float = 1.0,
) -> ReplayCoachingDecisionAssessment:
    evidence = _evidence(
        _search_result((), game_type=game_type, status="unavailable"),
        immediate=_immediate_evidence(
            (
                ("CA", best_swing, best_utility),
                ("S7", actual_swing, actual_utility),
            ),
            game_type=game_type,
        ),
        local_side=local_side,
    )
    return _at_decision(_assessment(evidence, "S7", quality="mistake"), decision_index)


def _turning_types(*assessments: ReplayCoachingDecisionAssessment):
    return {
        assessment.decision_time_evidence.decision_index: ()
        for assessment in assessments
    }


def _collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_collect_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_collect_keys(item) for item in value))
    return set()


def _plain_json_value(value):
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    return value


def _historical_reverse_search(**kwargs):
    exact = _historical_fake_search(**kwargs)
    candidate_count = len(exact.candidate_results)
    candidates = tuple(
        replace(
            candidate,
            local_contract_success_count=int(index == candidate_count - 1),
            local_contract_success_rate=float(index == candidate_count - 1),
            mean_local_side_game_score=float(index),
            mean_local_side_card_point_margin=(
                None if exact.game_type == "null" else float(index)
            ),
        )
        for index, candidate in enumerate(exact.candidate_results)
    )
    ranked = rank_search_candidate_results(candidates, exact.game_type, recommend=True)
    return replace(
        exact,
        candidate_results=ranked,
        recommended_card=ranked[0].card,
    )


def _analyzed_game(monkeypatch, data: dict, *, search=_historical_fake_search):
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)
    review = build_historical_search_review_internal_result(
        snapshots,
        record,
        base_search_seed=17,
        immediate_sample_count=1,
    )
    return record, review.assessments


def _zero_decision_data() -> dict:
    data = TERMINAL_BUILDERS["declarer_concession"]()
    data["tricks"] = []
    data["game_end"]["declarer_hand_cards_remaining"] = 10
    data["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    return data


def test_contract_constants_vocabularies_and_frozen_values() -> None:
    assessment = _search_gap_assessment(1, "contract_success")
    key = build_replay_coaching_key_decisions((assessment,), _turning_types(assessment))[0]

    assert REPLAY_COACHING_PRIORITIZATION_VERSION == 1
    assert MAX_REPLAY_COACHING_KEY_DECISIONS == 5
    assert REPLAY_COACHING_KEY_DECISION_SELECTION_REASONS == (
        "contract_success_gap",
        "settlement_score_gap",
        "card_point_margin_gap",
        "immediate_only_gap",
    )
    assert REPLAY_COACHING_TURNING_POINT_FACTORS == (
        "lower_contract_success_opportunity",
        "recorded_contract_became_decided",
        "recorded_declarer_became_decided",
        "recorded_defenders_became_decided",
        "forced_recorded_outcome_transition",
    )
    assert REPLAY_COACHING_TURNING_POINT_LIMITATIONS == (
        "counterfactual_aggregate_not_causal",
        "recorded_path_only",
        "decision_not_single_cause",
        "observed_card_not_ground_truth",
    )
    with pytest.raises(FrozenInstanceError):
        key.rank = 2  # type: ignore[misc]


def test_key_decision_defensively_copies_turning_point_types() -> None:
    assessment = _search_gap_assessment(1, "contract_success")
    source_types = ["decision_opportunity"]
    key = ReplayCoachingKeyDecision(
        prioritization_version=1,
        rank=1,
        assessment=assessment,
        selection_reason="contract_success_gap",
        primary_gap=1.0,
        is_high_impact=True,
        turning_point_types=tuple(source_types),
    )
    source_types.append("recorded_outcome")

    assert key.turning_point_types == ("decision_opportunity",)


@pytest.mark.parametrize(
    ("impact", "reason"),
    [
        ("contract_success", "contract_success_gap"),
        ("settlement_score", "settlement_score_gap"),
        ("card_point_margin", "card_point_margin_gap"),
    ],
)
def test_search_key_decision_eligibility_and_reason(impact: str, reason: str) -> None:
    assessment = _search_gap_assessment(1, impact)
    result = build_replay_coaching_key_decisions((assessment,), _turning_types(assessment))

    assert len(result) == 1
    assert result[0].selection_reason == reason
    assert result[0].primary_gap > 0


def test_immediate_only_key_decision_uses_objective_utility_gap_for_null() -> None:
    assessment = _immediate_gap_assessment(
        1,
        game_type="null",
        best_swing=-10.0,
        actual_swing=100.0,
        best_utility=1.0,
        actual_utility=0.0,
    )
    key = build_replay_coaching_key_decisions((assessment,), _turning_types(assessment))[0]

    assert assessment.immediate_expected_point_swing_gap == -110.0
    assert key.selection_reason == "immediate_only_gap"
    assert key.primary_gap == 1.0
    assert key.is_high_impact is False


def test_key_decisions_exclude_forced_best_and_not_assessable_choices() -> None:
    forced = _at_decision(
        _assessment(
            _evidence(
                _search_result((("CA", 4, 1.0, 1.0),)),
                immediate=_immediate_evidence((("CA", 1.0, 1.0),)),
            ),
            "CA",
        ),
        1,
    )
    best = _at_decision(
        _assessment(
            _evidence(_search_result((("CA", 4, 1.0, 1.0), ("S7", 2, 0.0, 0.0)))),
            "CA",
        ),
        2,
    )
    unavailable_evidence = _evidence(
        _search_result((), status="unavailable"),
        immediate=_immediate_evidence((), available=False),
    )
    not_assessable = _at_decision(
        _assessment(unavailable_evidence, "CA", quality="not_available"),
        3,
    )

    result = build_replay_coaching_key_decisions(
        (forced, best, not_assessable),
        _turning_types(forced, best, not_assessable),
    )

    assert result == ()


def test_aggregate_equivalent_choice_is_not_a_key_decision() -> None:
    equivalent = _at_decision(
        _assessment(
            _evidence(_search_result((("S7", 4, 1.0, 1.0), ("CA", 4, 1.0, 1.0)))),
            "S7",
        ),
        1,
    )

    assert equivalent.assessment_status == "best_or_equivalent"
    assert equivalent.aggregate_equivalent is True
    assert build_replay_coaching_key_decisions(
        (equivalent,), _turning_types(equivalent)
    ) == ()


def test_exact_selection_reason_priority_precedes_other_ranking_fields() -> None:
    assessments = (
        _immediate_gap_assessment(1, best_utility=100.0, actual_utility=0.0),
        _search_gap_assessment(2, "card_point_margin", primary_gap=100.0),
        _search_gap_assessment(3, "settlement_score", primary_gap=100.0),
        _search_gap_assessment(4, "contract_success"),
    )
    result = build_replay_coaching_key_decisions(assessments, _turning_types(*assessments))

    assert tuple(key.selection_reason for key in result) == (
        "contract_success_gap",
        "settlement_score_gap",
        "card_point_margin_gap",
        "immediate_only_gap",
    )


def test_evidence_priority_precedes_primary_gap() -> None:
    assessments = (
        _search_gap_assessment(
            1,
            "settlement_score",
            evidence_basis="completed_common_prefix",
            primary_gap=100.0,
        ),
        _search_gap_assessment(
            2,
            "settlement_score",
            evidence_basis="sampled_compatible_worlds",
            primary_gap=10.0,
        ),
        _search_gap_assessment(
            3,
            "settlement_score",
            evidence_basis="all_compatible_worlds",
            primary_gap=1.0,
        ),
    )
    result = build_replay_coaching_key_decisions(assessments, _turning_types(*assessments))

    assert tuple(key.assessment.evidence_basis for key in result) == (
        "all_compatible_worlds",
        "sampled_compatible_worlds",
        "completed_common_prefix",
    )


def test_primary_gap_better_count_and_decision_index_break_ties_in_order() -> None:
    assessments = (
        _search_gap_assessment(5, "settlement_score", primary_gap=5.0),
        _search_gap_assessment(4, "settlement_score", primary_gap=10.0),
        _search_gap_assessment(
            3,
            "settlement_score",
            primary_gap=5.0,
            better_card_count=2,
        ),
        _search_gap_assessment(2, "settlement_score", primary_gap=5.0),
    )
    result = build_replay_coaching_key_decisions(assessments, _turning_types(*assessments))

    assert tuple(key.assessment.decision_time_evidence.decision_index for key in result) == (
        4,
        3,
        2,
        5,
    )


def test_key_decisions_truncate_to_five_with_contiguous_ranks() -> None:
    assessments = tuple(
        _search_gap_assessment(index, "settlement_score", primary_gap=float(index))
        for index in range(1, 7)
    )
    result = build_replay_coaching_key_decisions(assessments, _turning_types(*assessments))

    assert len(result) == 5
    assert tuple(key.rank for key in result) == (1, 2, 3, 4, 5)
    assert tuple(key.primary_gap for key in result) == (6.0, 5.0, 4.0, 3.0, 2.0)


@pytest.mark.parametrize(
    ("game_type", "local_side", "impact"),
    [
        ("clubs", "declarer", "settlement_score"),
        ("grand", "defenders", "card_point_margin"),
        ("null", "declarer", "settlement_score"),
        ("null", "defenders", "contract_success"),
    ],
)
def test_key_decisions_support_suit_grand_null_and_both_sides(
    game_type: str, local_side: str, impact: str
) -> None:
    assessment = _search_gap_assessment(
        1,
        impact,
        game_type=game_type,
        local_side=local_side,
    )
    key = build_replay_coaching_key_decisions((assessment,), _turning_types(assessment))[0]

    assert key.assessment.decision_time_evidence.game_type == game_type
    assert key.assessment.decision_time_evidence.local_side == local_side


def test_primary_gap_rejects_noneligible_assessment() -> None:
    best = _assessment(
        _evidence(_search_result((("CA", 4, 1.0, 1.0), ("S7", 2, 0.0, 0.0)))),
        "CA",
    )

    with pytest.raises(ValueError, match="strictly_below_best"):
        get_replay_coaching_primary_gap(best)


def test_decision_opportunity_requires_search_contract_success() -> None:
    contract = _search_gap_assessment(1, "contract_success")
    settlement = _search_gap_assessment(2, "settlement_score")
    immediate = _immediate_gap_assessment(3)
    keys = build_replay_coaching_key_decisions(
        (contract, settlement, immediate),
        {1: ("decision_opportunity",), 2: (), 3: ()},
    )

    point = ReplayCoachingTurningPoint(
        prioritization_version=1,
        turning_point_type="decision_opportunity",
        decision_index=1,
        assessment=contract,
        is_high_impact=True,
        recorded_state_before=None,
        recorded_state_after=None,
        decided_side=None,
        factors=("lower_contract_success_opportunity",),
        limitations=(*contract.limitations, "counterfactual_aggregate_not_causal"),
    )

    assert keys[0].turning_point_types == ("decision_opportunity",)
    assert point.limitations[-1] == "counterfactual_aggregate_not_causal"
    with pytest.raises(ValueError, match="positive Search contract-success gap"):
        replace(point, decision_index=2, assessment=settlement)
    with pytest.raises(ValueError, match="positive Search contract-success gap"):
        replace(point, decision_index=3, assessment=immediate)


@pytest.mark.parametrize(
    ("evidence_basis", "status", "coverage"),
    [
        ("all_compatible_worlds", "complete", "all_compatible_worlds"),
        ("sampled_compatible_worlds", "complete", "sampled_compatible_worlds"),
        ("completed_common_prefix", "partial", "sampled_compatible_worlds"),
    ],
)
def test_decision_opportunity_supports_every_search_evidence_basis(
    evidence_basis: str, status: str, coverage: str
) -> None:
    del status, coverage
    assessment = _search_gap_assessment(
        1,
        "contract_success",
        evidence_basis=evidence_basis,
    )
    point = ReplayCoachingTurningPoint(
        prioritization_version=1,
        turning_point_type="decision_opportunity",
        decision_index=1,
        assessment=assessment,
        is_high_impact=True,
        recorded_state_before=None,
        recorded_state_after=None,
        decided_side=None,
        factors=("lower_contract_success_opportunity",),
        limitations=(
            *assessment.limitations,
            "counterfactual_aggregate_not_causal",
        ),
    )

    assert point.assessment.evidence_basis == evidence_basis


@pytest.mark.parametrize(
    ("game_type", "declarer_player_id", "expected_final_state"),
    [
        ("clubs", "player-a", "declarer_already_won"),
        ("grand", "player-b", "defenders_already_won"),
    ],
)
def test_recorded_suit_and_grand_timeline_has_one_first_transition(
    game_type: str,
    declarer_player_id: str,
    expected_final_state: str,
) -> None:
    record = build_historical_game_record(
        build_historical_input(
            game_type=game_type,
            declarer_player_id=declarer_player_id,
        )
    )
    states = build_recorded_decision_state_timeline(record)
    transitions = [
        index
        for index, (before, after) in enumerate(zip(states, states[1:], strict=False), start=1)
        if before == "undecided" and after != "undecided"
    ]

    assert len(transitions) == 1
    assert states[-1] == expected_final_state


def test_null_defender_card_after_declarer_trick_is_recorded_outcome(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(game_type="null", declarer_player_id="player-a"),
    )
    result = build_replay_coaching_prioritization_result(record, assessments)
    recorded = next(
        point for point in result.turning_points if point.turning_point_type == "recorded_outcome"
    )

    assert recorded.assessment.decision_time_evidence.decision_index == 3
    assert recorded.assessment.decision_time_evidence.local_side == "defenders"
    assert recorded.recorded_state_after == "defenders_already_won"


def test_complete_null_declarer_win_uses_only_complete_normal_fallback(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(game_type="null", declarer_player_id="player-b"),
    )
    states = build_recorded_decision_state_timeline(record)
    result = build_replay_coaching_prioritization_result(record, assessments)
    recorded = next(
        point for point in result.turning_points if point.turning_point_type == "recorded_outcome"
    )

    assert states[:-1] == ("undecided",) * 30
    assert states[-1] == "declarer_already_won"
    assert recorded.assessment.decision_time_evidence.decision_index == 30
    assert recorded.assessment.assessment_status == "forced_move"
    assert "forced_recorded_outcome_transition" in recorded.factors
    assert all(
        key.assessment.decision_time_evidence.decision_index != 30
        for key in result.key_decisions
    )


@pytest.mark.parametrize(
    ("hand_game", "ouvert"),
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_recorded_timeline_supports_all_normal_null_variants(
    hand_game: bool, ouvert: bool
) -> None:
    data = build_historical_input(
        game_type="null",
        hand_game=hand_game,
        declarer_player_id="player-b",
    )
    data["declaration"]["ouvert"] = ouvert
    record = build_historical_game_record(data)

    states = build_recorded_decision_state_timeline(record)

    assert states[-1] == "declarer_already_won"


@pytest.mark.parametrize(
    "declaration_update",
    [
        {"hand_game": True, "schneider_announced": True},
        {
            "hand_game": True,
            "schneider_announced": True,
            "schwarz_announced": True,
        },
    ],
)
def test_recorded_timeline_supports_announced_levels(declaration_update: dict) -> None:
    data = build_historical_input(
        game_type="grand",
        hand_game=True,
        declarer_player_id="player-a",
    )
    data["declaration"].update(declaration_update)
    record = build_historical_game_record(data)

    states = build_recorded_decision_state_timeline(record)

    assert states[-1] in {"declarer_already_won", "defenders_already_won"}


@pytest.mark.parametrize("bid_value", [72, 96])
def test_recorded_timeline_supports_overbid_required_levels(bid_value: int) -> None:
    record = build_historical_game_record(
        build_historical_input(
            game_type="grand",
            declarer_player_id="player-a",
            bid_value=bid_value,
        )
    )

    states = build_recorded_decision_state_timeline(record)

    assert states[-1] in {"declarer_already_won", "defenders_already_won"}


@pytest.mark.parametrize(
    "states",
    [
        ("undecided", "declarer_already_won", "undecided"),
        ("undecided", "defenders_already_won", "declarer_already_won"),
    ],
)
def test_timeline_monotonicity_rejects_reversal_and_side_switch(states: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="cannot reverse or switch"):
        validate_recorded_decision_state_timeline(states)


def test_initially_decided_timeline_is_allowed_without_transition() -> None:
    validate_recorded_decision_state_timeline(
        ("declarer_already_won", "declarer_already_won")
    )


def test_one_decision_can_have_both_turning_point_types(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(game_type="grand", declarer_player_id="player-a"),
        search=_historical_reverse_search,
    )
    result = build_replay_coaching_prioritization_result(record, assessments)
    by_decision: dict[int, set[str]] = {}
    for point in result.turning_points:
        by_decision.setdefault(
            point.assessment.decision_time_evidence.decision_index, set()
        ).add(point.turning_point_type)

    assert any(
        types == {"decision_opportunity", "recorded_outcome"}
        for types in by_decision.values()
    )
    dual_index = next(
        index
        for index, types in by_decision.items()
        if types == {"decision_opportunity", "recorded_outcome"}
    )
    dual_assessment = next(
        assessment
        for assessment in assessments
        if assessment.decision_time_evidence.decision_index == dual_index
    )
    key = build_replay_coaching_key_decisions(
        (dual_assessment,),
        {dual_index: ("decision_opportunity", "recorded_outcome")},
    )[0]
    assert key.turning_point_types == ("decision_opportunity", "recorded_outcome")
    assert key.is_high_impact is True


def test_zero_decision_record_has_empty_prioritization(monkeypatch) -> None:
    record, assessments = _analyzed_game(monkeypatch, _zero_decision_data())
    result = build_replay_coaching_prioritization_result(record, assessments)

    assert result.decision_count == 0
    assert result.assessable_decision_count == 0
    assert result.missed_impact_decision_count == 0
    assert result.high_impact_decision_count == 0
    assert result.recorded_initial_state == "undecided"
    assert result.recorded_final_state == "undecided"
    assert result.key_decisions == ()
    assert result.turning_points == ()


def test_shortened_game_does_not_use_terminal_event_as_a_card_transition(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        TERMINAL_BUILDERS["declarer_concession"](),
    )
    result = build_replay_coaching_prioritization_result(record, assessments)

    assert result.decision_count < 30
    assert result.recorded_final_state == "undecided"
    assert all(
        point.turning_point_type != "recorded_outcome"
        for point in result.turning_points
    )


@pytest.mark.parametrize("terminal_kind", tuple(TERMINAL_BUILDERS))
def test_prioritization_supports_every_current_shortened_record(
    monkeypatch, terminal_kind: str
) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        TERMINAL_BUILDERS[terminal_kind](),
    )

    result = build_replay_coaching_prioritization_result(record, assessments)

    assert result.decision_count == sum(len(trick.plays) for trick in record.tricks)
    assert 0 <= result.decision_count <= 29


@pytest.mark.parametrize(
    "continuation_kind",
    ["defender_open_play_continuation", "declarer_card_exposure_continuation"],
)
def test_continuation_followed_by_terminal_shortening_uses_only_cards(
    monkeypatch, continuation_kind: str
) -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        continuation_kind,
    )
    record, assessments = _analyzed_game(monkeypatch, data)
    result = build_replay_coaching_prioritization_result(record, assessments)

    assert result.decision_count == sum(len(trick.plays) for trick in record.tricks)
    assert result.recorded_final_state == "undecided"
    assert all(
        point.turning_point_type != "recorded_outcome"
        for point in result.turning_points
    )


def test_assessment_sequence_accepts_zero_through_thirty_supported_decisions(monkeypatch) -> None:
    zero_record, zero_assessments = _analyzed_game(monkeypatch, _zero_decision_data())
    full_record, full_assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(),
    )

    validate_replay_coaching_assessment_sequence(zero_record, zero_assessments)
    validate_replay_coaching_assessment_sequence(full_record, full_assessments)
    assert len(zero_assessments) == 0
    assert len(full_assessments) == 30


@pytest.mark.parametrize(
    "mutation",
    ["count", "order", "duplicate", "source", "identity", "actual_card", "version"],
)
def test_assessment_sequence_rejects_invalid_identity_and_order(
    monkeypatch, mutation: str
) -> None:
    record, assessments = _analyzed_game(monkeypatch, build_historical_input())
    changed = list(assessments)
    if mutation == "count":
        changed.pop()
    elif mutation == "order":
        changed[0], changed[1] = changed[1], changed[0]
    elif mutation == "duplicate":
        changed[1] = changed[0]
    elif mutation == "source":
        evidence = replace(changed[0].decision_time_evidence, source_game_id="other-game")
        changed[0] = _assessment(evidence, changed[0].actual_card)
    elif mutation == "identity":
        evidence = replace(changed[0].decision_time_evidence, acting_player_id="other-player")
        changed[0] = _assessment(evidence, changed[0].actual_card)
    elif mutation == "actual_card":
        alternate = next(
            card
            for card in changed[0].decision_time_evidence.legal_cards
            if card != changed[0].actual_card
        )
        changed[0] = _assessment(changed[0].decision_time_evidence, alternate)
    else:
        object.__setattr__(changed[0], "contract_version", 2)

    with pytest.raises(ValueError):
        validate_replay_coaching_assessment_sequence(record, tuple(changed))


def test_prioritization_counts_high_impact_decisions_once_for_dual_points(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(game_type="grand", declarer_player_id="player-a"),
    )
    result = build_replay_coaching_prioritization_result(record, assessments)
    high_indices = {
        point.assessment.decision_time_evidence.decision_index
        for point in result.turning_points
    }
    high_indices.update(
        key.assessment.decision_time_evidence.decision_index
        for key in result.key_decisions
        if key.is_high_impact
    )

    assert result.high_impact_decision_count == len(high_indices)


def test_settlement_margin_and_immediate_keys_are_not_high_without_recorded_transition() -> None:
    assessments = (
        _search_gap_assessment(1, "settlement_score"),
        _search_gap_assessment(2, "card_point_margin"),
        _immediate_gap_assessment(3),
    )
    keys = build_replay_coaching_key_decisions(assessments, _turning_types(*assessments))

    assert all(key.is_high_impact is False for key in keys)


def test_recorded_transition_makes_noncontract_key_high_impact() -> None:
    assessment = _search_gap_assessment(1, "settlement_score")
    key = build_replay_coaching_key_decisions(
        (assessment,),
        {1: ("recorded_outcome",)},
    )[0]

    assert key.is_high_impact is True


def test_serializers_are_deterministic_and_exclude_private_or_causal_fields(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(game_type="grand", declarer_player_id="player-a"),
        search=_historical_reverse_search,
    )
    result = build_replay_coaching_prioritization_result(record, assessments)
    serialized = build_serializable_replay_coaching_prioritization_result(result)

    assert serialized == build_serializable_replay_coaching_prioritization_result(result)
    assert build_serializable_replay_coaching_key_decision(result.key_decisions[0]) == (
        serialized["key_decisions"][0]
    )
    assert build_serializable_replay_coaching_turning_point(result.turning_points[0]) == (
        serialized["turning_points"][0]
    )
    assert all(
        point["decision_index"]
        == point["assessment"]["decision_time_evidence"]["decision_index"]
        for point in serialized["turning_points"]
    )
    text = str(serialized).lower()
    keys = _collect_keys(serialized)
    for forbidden in (
        "final_skat",
        "hidden_hands",
        "search_seed",
        "transposition_state",
        "principal_variation",
        "final_settlement",
    ):
        assert forbidden not in keys
    assert "caused" not in text


def test_later_plays_do_not_change_shared_recorded_timeline_prefix() -> None:
    original_data = build_historical_input()
    changed_data = rebuild_historical_suffix(original_data, completed_prefix_tricks=5)
    original_states = build_recorded_decision_state_timeline(
        build_historical_game_record(original_data)
    )
    changed_states = build_recorded_decision_state_timeline(
        build_historical_game_record(changed_data)
    )

    assert original_data["tricks"][:5] == changed_data["tricks"][:5]
    assert original_data["tricks"][5:] != changed_data["tricks"][5:]
    assert original_states[:16] == changed_states[:16]


@pytest.mark.parametrize(
    "continuation_kind",
    ["defender_open_play_continuation", "declarer_card_exposure_continuation"],
)
def test_terminal_shortening_and_settlement_changes_do_not_change_shared_timeline(
    continuation_kind: str,
) -> None:
    first = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](), continuation_kind
    )
    second = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](), continuation_kind
    )
    second["game_id"] = first["game_id"]
    first_record = build_historical_game_record(first)
    second_record = build_historical_game_record(second)

    assert first["game_end_reason"] != second["game_end_reason"]
    assert build_historical_game_summary(first_record)["final_settlement_summary"] != (
        build_historical_game_summary(second_record)["final_settlement_summary"]
    )
    assert build_recorded_decision_state_timeline(first_record) == (
        build_recorded_decision_state_timeline(second_record)
    )


@pytest.mark.parametrize(
    "continuation_kind",
    ["defender_open_play_continuation", "declarer_card_exposure_continuation"],
)
def test_terminal_and_settlement_changes_do_not_change_shared_prioritization(
    monkeypatch, continuation_kind: str
) -> None:
    first = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](), continuation_kind
    )
    second = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](), continuation_kind
    )
    second["game_id"] = first["game_id"]
    first_record, first_assessments = _analyzed_game(monkeypatch, first)
    second_record, second_assessments = _analyzed_game(monkeypatch, second)

    first_result = build_replay_coaching_prioritization_result(
        first_record, first_assessments
    )
    second_result = build_replay_coaching_prioritization_result(
        second_record, second_assessments
    )

    assert first_assessments == second_assessments
    assert build_serializable_replay_coaching_prioritization_result(first_result) == (
        build_serializable_replay_coaching_prioritization_result(second_result)
    )


def test_hidden_ownership_and_skat_changes_do_not_change_first_prefix_state() -> None:
    original = _zero_decision_data()
    changed = copy.deepcopy(original)
    changed["players"][2]["initial_hand"][-1], changed["skat"][0] = (
        changed["skat"][0],
        changed["players"][2]["initial_hand"][-1],
    )
    original_record = build_historical_game_record(original)
    changed_record = build_historical_game_record(changed)

    assert original_record.skat != changed_record.skat
    assert build_recorded_decision_state_timeline(original_record)[0] == (
        build_recorded_decision_state_timeline(changed_record)[0]
    )


def test_result_contract_rejects_count_and_subset_inconsistency(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(),
        search=_historical_reverse_search,
    )
    result = build_replay_coaching_prioritization_result(record, assessments)

    with pytest.raises(ValueError, match="decision_count"):
        replace(result, decision_count=29, record=record, assessments=assessments)
    with pytest.raises(ValueError, match="ranks"):
        replace(
            result,
            key_decisions=(replace(result.key_decisions[0], rank=2),),
            record=record,
            assessments=assessments,
        )
    with pytest.raises(ValueError, match="source"):
        replace(
            result,
            source_game_id="other-game",
            record=record,
            assessments=assessments,
        )
    changed_key = replace(result.key_decisions[0], turning_point_types=())
    with pytest.raises(ValueError, match="deterministic selection and ranking"):
        replace(
            result,
            key_decisions=(changed_key, *result.key_decisions[1:]),
            record=record,
            assessments=assessments,
        )
    with pytest.raises(ValueError, match="Turning Points"):
        replace(
            result,
            turning_points=(),
            record=record,
            assessments=assessments,
        )
    with pytest.raises(FrozenInstanceError):
        result.decision_count = 0  # type: ignore[misc]


def test_numeric_contract_fields_reject_booleans(monkeypatch) -> None:
    assessment = _search_gap_assessment(1, "contract_success")
    key = build_replay_coaching_key_decisions((assessment,), _turning_types(assessment))[0]
    with pytest.raises(ValueError, match="primary_gap"):
        replace(key, primary_gap=True)

    record, assessments = _analyzed_game(monkeypatch, build_historical_input())
    result = build_replay_coaching_prioritization_result(record, assessments)
    with pytest.raises(ValueError, match="decision_count"):
        replace(
            result,
            decision_count=True,
            record=record,
            assessments=assessments,
        )


def test_prioritization_builder_requires_an_immutable_assessment_tuple(monkeypatch) -> None:
    record, assessments = _analyzed_game(monkeypatch, build_historical_input())

    with pytest.raises(TypeError, match="tuple"):
        build_replay_coaching_prioritization_result(record, list(assessments))  # type: ignore[arg-type]


def test_turning_point_is_frozen_and_serializes_decided_side(monkeypatch) -> None:
    record, assessments = _analyzed_game(
        monkeypatch,
        build_historical_input(game_type="grand", declarer_player_id="player-a"),
    )
    result = build_replay_coaching_prioritization_result(record, assessments)
    recorded = next(
        point for point in result.turning_points if point.turning_point_type == "recorded_outcome"
    )
    serialized = build_serializable_replay_coaching_turning_point(recorded)

    assert serialized["decided_side"] in {"declarer", "defenders"}
    with pytest.raises(FrozenInstanceError):
        recorded.decided_side = None  # type: ignore[misc]


def test_prioritization_does_not_rerun_search_or_immediate(monkeypatch) -> None:
    record, snapshots = build_typed_historical_review_inputs(build_historical_input())
    calls = {"search": 0, "immediate": 0}

    def search(**kwargs):
        calls["search"] += 1
        return _historical_fake_search(**kwargs)

    def immediate(**kwargs):
        calls["immediate"] += 1
        return _historical_fake_immediate(**kwargs)

    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )
    internal = build_historical_search_review_internal_result(
        snapshots,
        record,
        43,
        immediate_sample_count=1,
    )
    calls_after_review = calls.copy()

    build_replay_coaching_prioritization_result(record, internal.assessments)

    assert calls == calls_after_review == {"search": 30, "immediate": 30}


def test_public_game_builder_supports_record_and_assessments_from_typed_adapter(
    monkeypatch,
) -> None:
    data = build_historical_input(game_type="clubs", declarer_player_id="player-a")
    record, snapshots = build_typed_historical_review_inputs(data)
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    internal = build_historical_search_review_internal_result(
        snapshots,
        record,
        31,
        immediate_sample_count=1,
    )

    result = build_replay_coaching_prioritization_result(record, internal.assessments)

    assert isinstance(result, ReplayCoachingPrioritizationResult)
    assert result.source_game_id == record.game_id
    assert result.decision_count == 30
