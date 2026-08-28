import copy
from dataclasses import FrozenInstanceError, replace

import pytest
from test_historical_game import build_historical_input
from test_historical_game_event_chain import TERMINAL_BUILDERS, add_continuation
from test_replay_coaching_contracts import (
    _historical_fake_immediate,
    _historical_fake_search,
)
from test_replay_coaching_prioritization import (
    _analyzed_game,
    _immediate_gap_assessment,
    _search_gap_assessment,
    _turning_types,
    _zero_decision_data,
)

from skatmind.bounded_search_result import (
    ConsumedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skatmind.historical_search_review import (
    HistoricalSearchReviewCoachingAnalysis,
    build_historical_search_review_coaching_analysis,
    build_historical_search_review_internal_result,
)
from skatmind.replay_coaching_guidance import (
    ReplayCoachingGuidanceResult,
    build_replay_coaching_guidance,
    build_serializable_replay_coaching_guidance_result,
)
from skatmind.replay_coaching_key_decisions import build_replay_coaching_key_decisions
from skatmind.replay_coaching_patterns import (
    MIN_REPLAY_COACHING_PATTERN_OCCURRENCES,
    REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES,
    REPLAY_COACHING_DESCRIPTIVE_PATTERN_TYPES,
    REPLAY_COACHING_GUIDANCE_VERSION,
    REPLAY_COACHING_PATTERN_FACTORS,
    REPLAY_COACHING_PATTERN_LIMITATIONS,
    REPLAY_COACHING_PATTERN_SCOPES,
    REPLAY_COACHING_PATTERN_TYPES,
    build_replay_coaching_patterns,
    get_replay_coaching_pattern_ordering_key,
    is_replay_coaching_pattern_occurrence,
)
from skatmind.replay_coaching_prioritization import (
    build_replay_coaching_prioritization_result,
)
from skatmind.replay_coaching_recommendations import (
    MAX_REPLAY_COACHING_DECISION_RECOMMENDATIONS,
    MAX_REPLAY_COACHING_PATTERN_RECOMMENDATIONS,
    REPLAY_COACHING_DECISION_RECOMMENDATION_TYPES,
    REPLAY_COACHING_PATTERN_RECOMMENDATION_TYPES,
    REPLAY_COACHING_RECOMMENDATION_FACTORS,
    ReplayCoachingDecisionRecommendation,
    ReplayCoachingPatternRecommendation,
    build_replay_coaching_decision_recommendations,
    build_replay_coaching_pattern_recommendations,
)
from skatmind.rules import get_legal_cards, get_trick_winner


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


def _search_with_impact(impact: str):
    def search(**kwargs):
        exact = _historical_fake_search(**kwargs)
        candidates = []
        for index, candidate in enumerate(exact.candidate_results):
            success = 1
            score = 0.0
            margin = None if exact.game_type == "null" else 0.0
            if impact == "settlement_score":
                score = float(index)
            elif impact == "card_point_margin":
                margin = float(index)
            elif impact == "aggregate_equivalent":
                pass
            else:
                raise AssertionError(f"Unsupported test impact: {impact}")
            candidates.append(
                replace(
                    candidate,
                    local_contract_success_count=success,
                    local_contract_success_rate=1.0,
                    mean_local_side_game_score=score,
                    mean_local_side_card_point_margin=margin,
                )
            )
        ranked = rank_search_candidate_results(
            tuple(candidates), exact.game_type, recommend=True
        )
        return replace(
            exact,
            candidate_results=ranked,
            recommended_card=ranked[0].card,
        )

    return search


def _unavailable_search(**kwargs):
    exact = _historical_fake_search(**kwargs)
    return replace(
        exact,
        status="unavailable",
        stop_reason="remaining_trick_limit_exceeded",
        world_coverage="none",
        solution_claim="none",
        consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
        compatible_world_count=None,
        candidate_results=(),
        recommended_card=None,
    )


def _reverse_immediate(*, state, **_kwargs):
    legal_cards = get_legal_cards(state.hand, state.current_trick, state.game_type)
    recommended = legal_cards[-1]
    values = {
        card: {
            "win_rate": (
                0.0
                if state.game_type == "null" and card == recommended
                else 1.0
                if state.game_type == "null"
                else 1.0
                if card == recommended
                else 0.0
            ),
            "average_trick_points": 5.0 if card == recommended else 0.0,
            "average_points_won": 5.0 if card == recommended else 0.0,
            "average_points_lost": 0.0,
        }
        for card in legal_cards
    }
    return recommended, "replay coaching reverse Immediate", values


def _build_high_play_input() -> dict:
    data = build_historical_input()
    playable_hands = {
        player["player_id"]: list(player["initial_hand"])
        for player in data["players"]
    }
    playable_hands[data["declarer_player_id"]].extend(data["skat"])
    for card in data["discarded_cards"]:
        playable_hands[data["declarer_player_id"]].remove(card)
    player_ids = ["player-a", "player-b", "player-c"]
    leader = "player-a"
    tricks = []
    for trick_number in range(1, 11):
        leader_index = player_ids.index(leader)
        order = [player_ids[(leader_index + offset) % 3] for offset in range(3)]
        cards = []
        plays = []
        for player_id in order:
            legal_cards = get_legal_cards(
                playable_hands[player_id], cards, data["declaration"]["game_type"]
            )
            card = legal_cards[-1]
            playable_hands[player_id].remove(card)
            cards.append(card)
            plays.append({"player_id": player_id, "card": card})
        leader = plays[get_trick_winner(cards, data["declaration"]["game_type"])][
            "player_id"
        ]
        tricks.append(
            {
                "trick_number": trick_number,
                "leader_player_id": order[0],
                "plays": plays,
            }
        )
    data["tricks"] = tricks
    return data


def _build_two_decision_hand_concession() -> dict:
    data = _zero_decision_data()
    data["declaration"]["hand_game"] = True
    data["discarded_cards"] = []
    data["tricks"] = [
        {
            "trick_number": 1,
            "leader_player_id": "player-a",
            "plays": [
                {"player_id": "player-a", "card": "CA"},
                {"player_id": "player-b", "card": "SJ"},
            ],
        }
    ]
    data["game_end"]["declarer_hand_cards_remaining"] = 9
    return data


def _analyzed_patterns(
    monkeypatch,
    *,
    search,
    immediate=_historical_fake_immediate,
    data=None,
):
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )
    record = build_historical_game_record(data or build_historical_input())
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )
    review = build_historical_search_review_internal_result(
        snapshots,
        record,
        base_search_seed=17,
        immediate_sample_count=1,
    )
    assessments = review.assessments
    prioritization = build_replay_coaching_prioritization_result(record, assessments)
    patterns = build_replay_coaching_patterns(record, assessments, prioritization)
    return record, assessments, prioritization, patterns


def _pattern_of_type(patterns, pattern_type: str, scope: str = "contract"):
    return next(
        pattern
        for pattern in patterns
        if pattern.pattern_type == pattern_type and pattern.scope == scope
    )


def test_guidance_constants_and_vocabularies_are_stable() -> None:
    assert REPLAY_COACHING_GUIDANCE_VERSION == 1
    assert MIN_REPLAY_COACHING_PATTERN_OCCURRENCES == 2
    assert MAX_REPLAY_COACHING_DECISION_RECOMMENDATIONS == 5
    assert MAX_REPLAY_COACHING_PATTERN_RECOMMENDATIONS == 5
    assert REPLAY_COACHING_PATTERN_SCOPES == ("player", "role", "phase", "contract")
    assert REPLAY_COACHING_PATTERN_TYPES == (
        "repeated_lower_contract_success",
        "repeated_lower_settlement_score",
        "repeated_lower_card_point_margin",
        "repeated_immediate_only_gap",
        "repeated_search_immediate_divergence",
        "repeated_aggregate_equivalent_choice",
        "repeated_forced_move",
        "repeated_search_unavailable",
    )
    assert REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES == REPLAY_COACHING_PATTERN_TYPES[:5]
    assert REPLAY_COACHING_DESCRIPTIVE_PATTERN_TYPES == REPLAY_COACHING_PATTERN_TYPES[5:]
    assert REPLAY_COACHING_DECISION_RECOMMENDATION_TYPES == (
        "prioritize_contract_success",
        "prefer_higher_settlement_score",
        "prefer_higher_card_point_margin",
        "review_immediate_alternative",
    )
    assert REPLAY_COACHING_PATTERN_RECOMMENDATION_TYPES == (
        "review_repeated_contract_success_gaps",
        "review_repeated_settlement_score_gaps",
        "review_repeated_card_point_margin_gaps",
        "review_repeated_immediate_only_gaps",
        "review_search_immediate_divergence",
    )


@pytest.mark.parametrize(
    ("pattern_type", "assessment"),
    [
        ("repeated_lower_contract_success", _search_gap_assessment(1, "contract_success")),
        ("repeated_lower_settlement_score", _search_gap_assessment(1, "settlement_score")),
        ("repeated_lower_card_point_margin", _search_gap_assessment(1, "card_point_margin")),
        ("repeated_immediate_only_gap", _immediate_gap_assessment(1)),
    ],
)
def test_exact_missed_impact_occurrence_predicates(pattern_type, assessment) -> None:
    assert is_replay_coaching_pattern_occurrence(pattern_type, assessment) is True


def test_null_never_matches_margin_occurrence() -> None:
    assessment = _search_gap_assessment(
        1, "settlement_score", game_type="null"
    )
    assert is_replay_coaching_pattern_occurrence(
        "repeated_lower_card_point_margin", assessment
    ) is False


def test_all_pattern_scopes_receive_each_occurrence_once(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, _, _, patterns = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    contract_pattern = _pattern_of_type(
        patterns, "repeated_lower_contract_success", "contract"
    )
    for scope in REPLAY_COACHING_PATTERN_SCOPES:
        scoped = [
            pattern
            for pattern in patterns
            if pattern.pattern_type == "repeated_lower_contract_success"
            and pattern.scope == scope
        ]
        assert sum(pattern.occurrence_count for pattern in scoped) == (
            contract_pattern.occurrence_count
        )
    player_patterns = [
        pattern
        for pattern in patterns
        if pattern.pattern_type == "repeated_lower_contract_success"
        and pattern.scope == "player"
    ]
    seat_order = tuple(
        next(player.player_id for player in record.players if player.seat == seat)
        for seat in ("forehand", "middlehand", "rearhand")
    )
    assert tuple(pattern.scope_value for pattern in player_patterns) == seat_order
    assert {pattern.scope_value for pattern in patterns if pattern.scope == "role"} == {
        "declarer",
        "defenders",
    }
    assert {pattern.scope_value for pattern in patterns if pattern.scope == "phase"} == {
        "opening",
        "middle",
        "endgame",
    }


@pytest.mark.parametrize("game_type", ["clubs", "spades", "hearts", "diamonds", "grand", "null"])
def test_contract_scope_uses_every_normalized_game_type(monkeypatch, game_type: str) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    _, _, _, patterns = _analyzed_patterns(
        monkeypatch,
        search=_historical_reverse_search,
        data=build_historical_input(game_type=game_type),
    )
    contract_patterns = [pattern for pattern in patterns if pattern.scope == "contract"]
    assert contract_patterns
    assert {pattern.scope_value for pattern in contract_patterns} == {game_type}


@pytest.mark.parametrize(
    ("search", "immediate", "data", "pattern_type"),
    [
        (
            _search_with_impact("settlement_score"),
            _historical_fake_immediate,
            None,
            "repeated_lower_settlement_score",
        ),
        (
            _search_with_impact("card_point_margin"),
            _historical_fake_immediate,
            None,
            "repeated_lower_card_point_margin",
        ),
        (
            _unavailable_search,
            _reverse_immediate,
            None,
            "repeated_immediate_only_gap",
        ),
        (
            _search_with_impact("aggregate_equivalent"),
            _historical_fake_immediate,
            _build_high_play_input(),
            "repeated_aggregate_equivalent_choice",
        ),
        (
            _unavailable_search,
            _historical_fake_immediate,
            None,
            "repeated_search_unavailable",
        ),
    ],
)
def test_repeated_pattern_types_use_exact_existing_fields(
    monkeypatch, search, immediate, data, pattern_type: str
) -> None:
    _, _, _, patterns = _analyzed_patterns(
        monkeypatch, search=search, immediate=immediate, data=copy.deepcopy(data)
    )
    pattern = _pattern_of_type(patterns, pattern_type)
    assert pattern.occurrence_count >= 2
    assert pattern.occurrence_count == len(pattern.decision_indices)
    assert pattern.is_actionable is (
        pattern_type in REPLAY_COACHING_ACTIONABLE_PATTERN_TYPES
    )


def test_divergence_and_forced_move_patterns_are_distinct(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    _, _, _, patterns = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    divergence = _pattern_of_type(
        patterns, "repeated_search_immediate_divergence"
    )
    forced = _pattern_of_type(patterns, "repeated_forced_move")
    assert divergence.is_actionable is True
    assert forced.is_actionable is False
    assert set(divergence.decision_indices).isdisjoint(forced.decision_indices)


def test_one_occurrence_does_not_create_a_pattern(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    calls = 0

    def one_divergence(**kwargs):
        nonlocal calls
        calls += 1
        search = _historical_reverse_search if calls == 1 else _historical_fake_search
        return search(**kwargs)

    _, _, _, patterns = _analyzed_patterns(monkeypatch, search=one_divergence)
    assert all(
        pattern.pattern_type != "repeated_search_immediate_divergence"
        for pattern in patterns
    )


def test_pattern_counts_subsets_factors_limitations_and_immutability(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, assessments, prioritization, patterns = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    pattern = _pattern_of_type(patterns, "repeated_lower_contract_success")
    assert pattern.key_decision_indices == tuple(
        index
        for index in pattern.decision_indices
        if index
        in {
            key.assessment.decision_time_evidence.decision_index
            for key in prioritization.key_decisions
        }
    )
    assert sum(count for _, count in pattern.evidence_basis_counts) == pattern.occurrence_count
    assert sum(count for _, count in pattern.impact_tier_counts) == pattern.occurrence_count
    assert pattern.factors == ("repeated_contract_success_gap", "contract_scope")
    assert pattern.limitations[0:2] == (
        "single_recorded_game_only",
        "minimum_occurrence_product_rule",
    )
    assert pattern.limitations[-3:] == (
        "observed_card_not_ground_truth",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
    )
    assert "determinization_strategy_fusion" in pattern.limitations
    assert hash(pattern) == hash(pattern)
    with pytest.raises(FrozenInstanceError):
        pattern.occurrence_count = 0  # type: ignore[misc]
    with pytest.raises(ValueError, match="occurrence_count"):
        replace(
            pattern,
            occurrence_count=1,
            record=record,
            assessments=assessments,
            prioritization=prioritization,
        )


def test_duplicate_assessment_decision_indices_are_rejected(monkeypatch) -> None:
    record, assessments = _analyzed_game(monkeypatch, build_historical_input())
    changed = (assessments[0], assessments[0], *assessments[2:])
    prioritization = build_replay_coaching_prioritization_result(record, assessments)
    with pytest.raises(ValueError, match="unique contiguous"):
        build_replay_coaching_patterns(record, changed, prioritization)


def test_pattern_order_is_canonical_and_repeatable(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, assessments, prioritization, patterns = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    keys = tuple(
        get_replay_coaching_pattern_ordering_key(record, pattern)
        for pattern in patterns
    )
    assert keys == tuple(sorted(keys))
    assert patterns == build_replay_coaching_patterns(
        record, assessments, prioritization
    )


@pytest.mark.parametrize(
    ("impact", "expected_type"),
    [
        ("contract_success", "prioritize_contract_success"),
        ("settlement_score", "prefer_higher_settlement_score"),
        ("card_point_margin", "prefer_higher_card_point_margin"),
    ],
)
def test_search_key_decision_recommendation_templates(impact: str, expected_type: str) -> None:
    assessment = _search_gap_assessment(1, impact)
    key = build_replay_coaching_key_decisions(
        (assessment,), _turning_types(assessment)
    )[0]
    recommendation = build_replay_coaching_decision_recommendations((key,))[0]
    assert recommendation.recommendation_type == expected_type
    assert assessment.actual_card in recommendation.explanation
    assert str(assessment.best_card) in recommendation.explanation
    assert recommendation.rank == key.rank
    if impact == "contract_success":
        assert recommendation.action == (
            "Consider Contract success before settlement score or card-point margin "
            "when comparing the evaluated cards."
        )
    elif impact == "settlement_score":
        assert recommendation.action == (
            "Compare settlement score after Contract success and before card-point margin."
        )
    else:
        assert recommendation.action == "Use card-point margin as a tertiary objective."


def test_decision_recommendation_text_is_exact_and_deterministic() -> None:
    assessments = (
        _search_gap_assessment(1, "contract_success"),
        _search_gap_assessment(2, "settlement_score"),
        _search_gap_assessment(3, "card_point_margin"),
        _immediate_gap_assessment(4),
    )
    keys = build_replay_coaching_key_decisions(
        assessments, _turning_types(*assessments)
    )
    recommendations = build_replay_coaching_decision_recommendations(keys)
    assert recommendations[0].title == "Prioritize Contract success at decision 1"
    assert recommendations[0].explanation == (
        "The observed card S7 had a lower aggregate local-side Contract-success "
        "result than the best evaluated alternative CA (gap 1)."
    )
    assert recommendations[1].title == "Compare settlement score at decision 2"
    assert recommendations[1].explanation == (
        "The Contract-success result was equivalent, while the observed card S7 "
        "had a lower mean local-side settlement score than the best evaluated "
        "alternative CA (gap 1)."
    )
    assert recommendations[2].title == "Compare card-point margin at decision 3"
    assert recommendations[2].explanation == (
        "Contract success and settlement score were equivalent, while the observed "
        "card S7 had a lower mean local-side Suit or Grand card-point margin than "
        "the best evaluated alternative CA (gap 1)."
    )
    assert recommendations[3].title == (
        "Review the Immediate alternative at decision 4"
    )
    assert recommendations[3].explanation == (
        "Bounded Search did not provide an assessable actual-card comparison; the "
        "existing one-trick Immediate analysis preferred CA to the observed card S7 "
        "(objective-utility gap 4)."
    )
    assert recommendations == build_replay_coaching_decision_recommendations(keys)


def test_null_contract_recommendation_has_exact_objective_wording() -> None:
    assessment = _search_gap_assessment(
        1, "contract_success", game_type="null"
    )
    key = build_replay_coaching_key_decisions(
        (assessment,), _turning_types(assessment)
    )[0]
    recommendation = build_replay_coaching_decision_recommendations((key,))[0]
    assert (
        "For Null, the relevant contract objective is whether the declarer remains "
        "without a trick; card points are not a Search objective."
    ) in recommendation.explanation
    assert "card-point margin" not in recommendation.explanation
    assert recommendation.action == (
        "Consider Contract success before settlement score when comparing the "
        "evaluated cards."
    )
    assert "card-point margin" not in recommendation.action


def test_null_contract_pattern_recommendation_has_exact_objective_wording(
    monkeypatch,
) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, _, _, patterns = _analyzed_patterns(
        monkeypatch,
        search=_historical_reverse_search,
        data=build_historical_input(game_type="null"),
    )
    pattern = _pattern_of_type(patterns, "repeated_lower_contract_success")
    recommendation = build_replay_coaching_pattern_recommendations(
        record, (pattern,)
    )[0]
    assert (
        "For Null, the relevant contract objective is whether the declarer remains "
        "without a trick; card points are not a Search objective."
    ) in recommendation.explanation
    assert "card-point margin" not in recommendation.explanation


def test_null_settlement_recommendations_omit_margin(monkeypatch) -> None:
    assessment = _search_gap_assessment(
        1, "settlement_score", game_type="null"
    )
    key = build_replay_coaching_key_decisions(
        (assessment,), _turning_types(assessment)
    )[0]
    decision_recommendation = build_replay_coaching_decision_recommendations(
        (key,)
    )[0]
    assert decision_recommendation.action == (
        "Compare settlement score after Contract success."
    )
    assert "card-point margin" not in (
        decision_recommendation.explanation + decision_recommendation.action
    )

    record, _, _, patterns = _analyzed_patterns(
        monkeypatch,
        search=_search_with_impact("settlement_score"),
        data=build_historical_input(game_type="null"),
    )
    pattern = _pattern_of_type(patterns, "repeated_lower_settlement_score")
    pattern_recommendation = build_replay_coaching_pattern_recommendations(
        record, (pattern,)
    )[0]
    assert pattern_recommendation.action == (
        "When Contract-success results are equivalent, compare mean local-side "
        "settlement score."
    )
    assert "card-point margin" not in (
        pattern_recommendation.explanation + pattern_recommendation.action
    )


def test_immediate_only_recommendation_is_explicitly_one_trick() -> None:
    assessment = _immediate_gap_assessment(1)
    key = build_replay_coaching_key_decisions(
        (assessment,), _turning_types(assessment)
    )[0]
    recommendation = build_replay_coaching_decision_recommendations((key,))[0]
    assert recommendation.recommendation_type == "review_immediate_alternative"
    assert "one-trick Immediate analysis" in recommendation.explanation
    assert recommendation.action == (
        "Review this as one-trick Immediate evidence, not as multi-trick "
        "Contract-success evidence."
    )
    assert "immediate_expected_value_only" in recommendation.limitations
    assert "search_unavailable" in recommendation.limitations


def test_one_decision_recommendation_per_key_with_same_ranks() -> None:
    assessments = (
        _search_gap_assessment(1, "contract_success"),
        _search_gap_assessment(2, "settlement_score"),
        _search_gap_assessment(3, "card_point_margin"),
        _immediate_gap_assessment(4),
    )
    keys = build_replay_coaching_key_decisions(
        assessments, _turning_types(*assessments)
    )
    recommendations = build_replay_coaching_decision_recommendations(keys)
    assert len(recommendations) == len(keys) == 4
    assert tuple(item.rank for item in recommendations) == (1, 2, 3, 4)
    assert tuple(item.key_decision for item in recommendations) == keys


@pytest.mark.parametrize(
    (
        "search",
        "immediate",
        "pattern_type",
        "recommendation_type",
        "expected_action",
    ),
    [
        (
            _search_with_impact("settlement_score"),
            _historical_fake_immediate,
            "repeated_lower_settlement_score",
            "review_repeated_settlement_score_gaps",
            "When Contract-success results are equivalent, compare mean local-side "
            "settlement score before card-point margin.",
        ),
        (
            _search_with_impact("card_point_margin"),
            _historical_fake_immediate,
            "repeated_lower_card_point_margin",
            "review_repeated_card_point_margin_gaps",
            "Use card-point margin only after Contract success and settlement score are "
            "equivalent.",
        ),
        (
            _unavailable_search,
            _reverse_immediate,
            "repeated_immediate_only_gap",
            "review_repeated_immediate_only_gaps",
            "Review the listed one-trick alternatives while keeping the Immediate-only "
            "evidence limitation explicit.",
        ),
    ],
)
def test_pattern_recommendation_types_and_exact_actions(
    monkeypatch,
    search,
    immediate,
    pattern_type: str,
    recommendation_type: str,
    expected_action: str,
) -> None:
    record, _, _, patterns = _analyzed_patterns(
        monkeypatch, search=search, immediate=immediate
    )
    recommendations = build_replay_coaching_pattern_recommendations(record, patterns)
    recommendation = next(
        item
        for item in recommendations
        if item.recommendation_type == recommendation_type
    )
    assert recommendation.pattern.pattern_type == pattern_type
    assert recommendation.action == expected_action
    assert recommendation.decision_indices == recommendation.pattern.decision_indices
    assert str(recommendation.pattern.occurrence_count) in recommendation.explanation
    assert recommendation.pattern.scope_value in recommendation.explanation


def test_pattern_recommendation_ranking_deduplication_limit_and_divergence_wording(
    monkeypatch,
) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, _, _, patterns = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    recommendations = build_replay_coaching_pattern_recommendations(record, patterns)
    evidence_keys = tuple(
        (item.recommendation_type, item.decision_indices) for item in recommendations
    )
    assert len(evidence_keys) == len(set(evidence_keys))
    assert len(recommendations) == MAX_REPLAY_COACHING_PATTERN_RECOMMENDATIONS
    assert tuple(item.rank for item in recommendations) == (1, 2, 3, 4, 5)
    duplicate_indices = next(
        pattern.decision_indices
        for pattern in patterns
        if pattern.pattern_type == "repeated_lower_contract_success"
        and pattern.scope == "role"
        and any(
            other.pattern_type == pattern.pattern_type
            and other.scope == "player"
            and other.decision_indices == pattern.decision_indices
            for other in patterns
        )
    )
    kept = next(
        item
        for item in recommendations
        if item.recommendation_type == "review_repeated_contract_success_gaps"
        and item.decision_indices == duplicate_indices
    )
    assert kept.pattern.scope == "player"
    assert kept.action == (
        "Review these decisions together and prioritize contract preservation "
        "before lower-order objectives."
    )
    divergence_pattern = _pattern_of_type(
        patterns, "repeated_search_immediate_divergence"
    )
    divergence = build_replay_coaching_pattern_recommendations(
        record, (divergence_pattern,)
    )[0]
    assert divergence.action == (
        "Review these positions as bounded multi-trick evidence versus one-trick "
        "Immediate evidence; the divergence itself is not a player error."
    )


def test_descriptive_patterns_never_create_recommendations(monkeypatch) -> None:
    record, _, _, patterns = _analyzed_patterns(
        monkeypatch,
        search=_search_with_impact("aggregate_equivalent"),
        data=_build_high_play_input(),
    )
    recommendations = build_replay_coaching_pattern_recommendations(record, patterns)
    assert all(item.pattern.is_actionable for item in recommendations)
    assert all(
        item.pattern.pattern_type not in REPLAY_COACHING_DESCRIPTIVE_PATTERN_TYPES
        for item in recommendations
    )
    descriptive = _pattern_of_type(
        patterns, "repeated_aggregate_equivalent_choice"
    )
    with pytest.raises(ValueError, match="actionable pattern"):
        ReplayCoachingPatternRecommendation(
            guidance_version=1,
            rank=1,
            recommendation_type="review_repeated_contract_success_gaps",
            pattern=descriptive,
            title="x",
            explanation="x",
            action="x",
            decision_indices=descriptive.decision_indices,
            factors=("repeated_pattern", "contract_success_priority"),
            limitations=descriptive.limitations,
        )


def test_pattern_recommendations_reject_patterns_from_another_record(
    monkeypatch,
) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    null_record, _, _, null_patterns = _analyzed_patterns(
        monkeypatch,
        search=_historical_reverse_search,
        data=build_historical_input(game_type="null"),
    )
    grand_record = build_historical_game_record(build_historical_input())
    pattern = _pattern_of_type(null_patterns, "repeated_lower_contract_success")
    assert pattern.source_game_id == null_record.game_id
    with pytest.raises(ValueError, match="source game"):
        build_replay_coaching_pattern_recommendations(grand_record, (pattern,))


def test_guidance_result_counts_serialization_and_prohibited_claims(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, assessments, prioritization, _ = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    guidance = build_replay_coaching_guidance(
        record, assessments, prioritization
    )
    serialized = build_serializable_replay_coaching_guidance_result(guidance)
    assert isinstance(guidance, ReplayCoachingGuidanceResult)
    assert guidance.pattern_count == len(guidance.patterns)
    assert guidance.actionable_pattern_count == sum(
        pattern.is_actionable for pattern in guidance.patterns
    )
    assert guidance.decision_recommendation_count == len(
        prioritization.key_decisions
    )
    assert guidance.pattern_recommendation_count <= 5
    assert serialized == build_serializable_replay_coaching_guidance_result(guidance)
    forbidden_keys = {
        "private_hands",
        "final_skat",
        "selected_worlds",
        "ownership_assignments",
        "search_seed",
        "transposition_state",
        "principal_variation",
        "final_settlement",
    }
    assert forbidden_keys.isdisjoint(_collect_keys(serialized))
    text = str(serialized).lower()
    for prohibited in (
        "mistake",
        "suboptimal",
        "player is weak",
        "always makes this error",
        "caused the result",
        "lost the game",
        "certainly would have won",
        "statistically significant",
        "perfect play",
        "optimal hidden-information play",
        "poor trump control",
        "lost tempo",
        "bad entry management",
        "wrong signal",
        "card-counting error",
    ):
        assert prohibited not in text
    with pytest.raises(FrozenInstanceError):
        guidance.pattern_count = 0  # type: ignore[misc]


def test_zero_decision_guidance_is_valid_and_empty(monkeypatch) -> None:
    record, assessments = _analyzed_game(monkeypatch, _zero_decision_data())
    prioritization = build_replay_coaching_prioritization_result(record, assessments)
    guidance = build_replay_coaching_guidance(record, assessments, prioritization)
    assert guidance.decision_count == 0
    assert guidance.pattern_count == 0
    assert guidance.patterns == ()
    assert guidance.decision_recommendations == ()
    assert guidance.pattern_recommendations == ()


def test_guidance_rejects_other_assessment_sequence_and_count(monkeypatch) -> None:
    record, assessments = _analyzed_game(monkeypatch, build_historical_input())
    prioritization = build_replay_coaching_prioritization_result(record, assessments)
    guidance = build_replay_coaching_guidance(record, assessments, prioritization)
    other_data = build_historical_input()
    other_data["game_id"] = "other-game"
    other_record, other_assessments = _analyzed_game(monkeypatch, other_data)
    other_prioritization = build_replay_coaching_prioritization_result(
        other_record, other_assessments
    )
    with pytest.raises(ValueError, match="assessment sequence"):
        build_replay_coaching_guidance(
            record,
            assessments,
            other_prioritization,
        )
    with pytest.raises(ValueError, match="decision_count"):
        replace(
            guidance,
            decision_count=29,
            record=record,
            assessments=assessments,
        )


def test_pattern_builder_rejects_prioritization_from_other_same_game_analysis(
    monkeypatch,
) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, reverse_assessments = _analyzed_game(
        monkeypatch, build_historical_input(), search=_historical_reverse_search
    )
    _, baseline_assessments = _analyzed_game(
        monkeypatch, build_historical_input(), search=_historical_fake_search
    )
    baseline_prioritization = build_replay_coaching_prioritization_result(
        record, baseline_assessments
    )
    with pytest.raises(ValueError, match="same assessment sequence"):
        build_replay_coaching_patterns(
            record, reverse_assessments, baseline_prioritization
        )


def test_guidance_isolated_from_later_terminal_and_final_context(monkeypatch) -> None:
    first = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "defender_open_play_continuation",
    )
    second = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](),
        "defender_open_play_continuation",
    )
    second["game_id"] = first["game_id"]
    first_record, first_assessments = _analyzed_game(monkeypatch, first)
    second_record, second_assessments = _analyzed_game(monkeypatch, second)
    assert first_assessments == second_assessments
    first_priority = build_replay_coaching_prioritization_result(
        first_record, first_assessments
    )
    second_priority = build_replay_coaching_prioritization_result(
        second_record, second_assessments
    )
    first_guidance = build_replay_coaching_guidance(
        first_record, first_assessments, first_priority
    )
    second_guidance = build_replay_coaching_guidance(
        second_record, second_assessments, second_priority
    )
    assert build_historical_game_summary(first_record)["final_settlement_summary"] != (
        build_historical_game_summary(second_record)["final_settlement_summary"]
    )
    assert build_serializable_replay_coaching_guidance_result(first_guidance) == (
        build_serializable_replay_coaching_guidance_result(second_guidance)
    )


def test_zero_decision_guidance_ignores_final_hidden_ownership_and_skat(
    monkeypatch,
) -> None:
    original = _zero_decision_data()
    changed = copy.deepcopy(original)
    changed["players"][2]["initial_hand"][-1], changed["skat"][0] = (
        changed["skat"][0],
        changed["players"][2]["initial_hand"][-1],
    )
    original_record, original_assessments = _analyzed_game(monkeypatch, original)
    changed_record, changed_assessments = _analyzed_game(monkeypatch, changed)
    original_priority = build_replay_coaching_prioritization_result(
        original_record, original_assessments
    )
    changed_priority = build_replay_coaching_prioritization_result(
        changed_record, changed_assessments
    )
    assert original_record.skat != changed_record.skat
    assert original_assessments == changed_assessments == ()
    assert original_priority == changed_priority
    original_guidance = build_replay_coaching_guidance(
        original_record, original_assessments, original_priority
    )
    changed_guidance = build_replay_coaching_guidance(
        changed_record, changed_assessments, changed_priority
    )
    assert build_serializable_replay_coaching_guidance_result(original_guidance) == (
        build_serializable_replay_coaching_guidance_result(changed_guidance)
    )


def test_nonempty_guidance_ignores_unseen_hand_and_skat_ownership_changes(
    monkeypatch,
) -> None:
    original = _build_two_decision_hand_concession()
    changed = copy.deepcopy(original)
    changed["players"][2]["initial_hand"][3], changed["skat"][0] = (
        changed["skat"][0],
        changed["players"][2]["initial_hand"][3],
    )
    original_record, original_assessments = _analyzed_game(monkeypatch, original)
    changed_record, changed_assessments = _analyzed_game(monkeypatch, changed)
    assert original_record.skat != changed_record.skat
    assert len(original_assessments) == 2
    assert original_assessments == changed_assessments
    original_priority = build_replay_coaching_prioritization_result(
        original_record, original_assessments
    )
    changed_priority = build_replay_coaching_prioritization_result(
        changed_record, changed_assessments
    )
    assert original_priority == changed_priority
    original_guidance = build_replay_coaching_guidance(
        original_record, original_assessments, original_priority
    )
    changed_guidance = build_replay_coaching_guidance(
        changed_record, changed_assessments, changed_priority
    )
    assert build_serializable_replay_coaching_guidance_result(original_guidance) == (
        build_serializable_replay_coaching_guidance_result(changed_guidance)
    )


def test_historical_search_review_coaching_orchestration_reuses_one_pass(
    monkeypatch,
) -> None:
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
        "skatmind.historical_search_review.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )
    analysis = build_historical_search_review_coaching_analysis(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
    )
    assert calls == {"search": 30, "immediate": 30}
    assert len(analysis.assessments) == 30
    assert analysis.guidance.prioritization == analysis.prioritization
    public = _plain(analysis.public_review_summary)
    assert "guidance" not in _collect_keys(public)
    assert "prioritization" not in _collect_keys(public)
    assert len(public["decisions"]) == 30
    with pytest.raises(TypeError):
        analysis.public_review_summary["settings"]["base_search_seed"] = 9  # type: ignore[index]

    wrong_public = dict(analysis.public_review_summary)
    wrong_public["source_game_id"] = "wrong-game"
    with pytest.raises(ValueError, match="Public review summary"):
        HistoricalSearchReviewCoachingAnalysis(
            public_review_summary=wrong_public,
            assessments=analysis.assessments,
            prioritization=analysis.prioritization,
            guidance=analysis.guidance,
            historical_record=record,
        )
    with pytest.raises(ValueError, match="coaching assessments"):
        HistoricalSearchReviewCoachingAnalysis(
            public_review_summary=analysis.public_review_summary,
            assessments=(object(),),  # type: ignore[arg-type]
            prioritization=analysis.prioritization,
            guidance=analysis.guidance,
            historical_record=record,
        )


def test_recommendation_contracts_reject_noncanonical_fields() -> None:
    assessment = _search_gap_assessment(1, "contract_success")
    key = build_replay_coaching_key_decisions(
        (assessment,), _turning_types(assessment)
    )[0]
    recommendation = build_replay_coaching_decision_recommendations((key,))[0]
    assert isinstance(recommendation, ReplayCoachingDecisionRecommendation)
    assert recommendation.factors == (
        "decision_specific",
        "contract_success_priority",
    )
    assert recommendation.limitations[-2:] == (
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
    )
    with pytest.raises(ValueError, match="fixed template"):
        replace(recommendation, action="Invented advice")
    with pytest.raises(ValueError, match="do not reconcile"):
        replace(
            recommendation,
            factors=("contract_success_priority", "decision_specific"),
        )
    with pytest.raises(ValueError, match="guidance version"):
        replace(recommendation, guidance_version=True)
    with pytest.raises(ValueError, match="rank"):
        replace(recommendation, rank=True)


def test_pattern_recommendation_indices_reject_numeric_aliases(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, _, _, patterns = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    recommendation = build_replay_coaching_pattern_recommendations(
        record, patterns
    )[0]
    with pytest.raises(ValueError, match="positive integers"):
        replace(
            recommendation,
            decision_indices=tuple(float(index) for index in recommendation.decision_indices),
        )


def test_pattern_and_guidance_versions_reject_numeric_aliases(monkeypatch) -> None:
    from test_replay_coaching_prioritization import _historical_reverse_search

    record, assessments, prioritization, patterns = _analyzed_patterns(
        monkeypatch, search=_historical_reverse_search
    )
    pattern = patterns[0]
    with pytest.raises(ValueError, match="guidance version"):
        replace(
            pattern,
            guidance_version=1.0,
            record=record,
            assessments=assessments,
            prioritization=prioritization,
        )
    guidance = build_replay_coaching_guidance(record, assessments, prioritization)
    with pytest.raises(ValueError, match="guidance version"):
        replace(
            guidance,
            guidance_version=True,
            record=record,
            assessments=assessments,
        )


def test_contract_vocabulary_contains_only_machine_readable_factors() -> None:
    assert REPLAY_COACHING_PATTERN_FACTORS == (
        "repeated_contract_success_gap",
        "repeated_settlement_score_gap",
        "repeated_card_point_margin_gap",
        "repeated_immediate_only_gap",
        "repeated_search_immediate_divergence",
        "repeated_aggregate_equivalent_choice",
        "repeated_forced_move",
        "repeated_search_unavailable",
        "player_scope",
        "role_scope",
        "phase_scope",
        "contract_scope",
    )
    assert REPLAY_COACHING_PATTERN_LIMITATIONS == (
        "single_recorded_game_only",
        "minimum_occurrence_product_rule",
        "bounded_late_game_search",
        "determinization_strategy_fusion",
        "sampled_compatible_worlds",
        "completed_common_prefix",
        "immediate_expected_value_only",
        "search_unavailable",
        "observed_card_not_ground_truth",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
    )
    assert REPLAY_COACHING_RECOMMENDATION_FACTORS == (
        "decision_specific",
        "repeated_pattern",
        "contract_success_priority",
        "settlement_score_priority",
        "card_point_margin_priority",
        "immediate_only_evidence",
        "search_immediate_divergence",
        "player_scope",
        "role_scope",
        "phase_scope",
        "contract_scope",
    )
