from dataclasses import FrozenInstanceError, replace
from functools import lru_cache

import pytest
from test_information_set_search_state_and_preparation import _find_view, _request

from skatmind.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.historical_information_set_search_review import (
    HistoricalInformationSetSearchDecisionReviewV1,
)
from skatmind.information_set_replay_coaching_evidence import (
    INFORMATION_SET_REPLAY_COACHING_EVIDENCE_VERSION,
    INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY,
    INFORMATION_SET_REPLAY_COACHING_PRIMARY_EVIDENCE_POLICY,
    INFORMATION_SET_REPLAY_COACHING_PUBLIC_POLICY,
    INFORMATION_SET_REPLAY_COACHING_SOURCE_POLICY,
    attach_retained_actual_card_to_information_set_replay_coaching_evidence_v1,
    build_information_set_replay_coaching_decision_time_evidence_v1,
    build_serializable_information_set_replay_coaching_decision_time_evidence_v1,
)
from skatmind.information_set_search_comparison import (
    attach_actual_card_to_information_set_search_comparison_v1,
    build_information_set_search_comparison_pre_actual_analysis_v1,
)
from skatmind.information_set_search_contracts import (
    InformationSetSearchConsumedBudgetV1,
    InformationSetSearchResultV1,
)
from skatmind.information_set_search_executor import execute_information_set_search_v1
from skatmind.information_set_search_preparation import prepare_information_set_search_v1
from skatmind.information_set_search_public import (
    build_public_information_set_search_result_v1,
)
from skatmind.replay_coaching_evidence import canonicalize_replay_coaching_cards
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION


@lru_cache(maxsize=1)
def _base_request_and_result():
    view, _state = _find_view(
        actor="me",
        remaining_tricks=2,
        current_trick_size=0,
        public_players=("left", "right"),
    )
    request = _request(view, max_selected_worlds=8, max_sampled_worlds=8)
    preparation = prepare_information_set_search_v1(request)
    result = execute_information_set_search_v1(preparation)
    assert result.status == "complete"
    assert len(result.candidate_results) >= 2
    return request, result


def _information_result(
    impact: str = "contract_success",
    *,
    coverage: str = "all_compatible_worlds",
) -> InformationSetSearchResultV1:
    _request_value, base = _base_request_and_result()
    completed = 1 if coverage == "single_exact_world" else 2
    cards = tuple(candidate.card for candidate in base.candidate_results)
    raw = []
    for index, card in enumerate(cards):
        is_best = index == 0
        successes = completed if impact != "contract_success" or is_best else 0
        score = 10.0 if impact != "settlement_score" or is_best else 0.0
        margin = 10.0 if impact != "card_point_margin" or is_best else 0.0
        if impact == "aggregate_equivalent":
            successes = completed
            score = 10.0
            margin = 10.0
        raw.append(
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
        )
    ranked = rank_search_candidate_results(tuple(raw), "grand", recommend=True)
    sampled = completed if coverage == "sampled_compatible_worlds" else 0
    consumed = replace(
        base.consumed_budget,
        selected_world_count=completed,
        completed_world_count=completed,
        sampled_world_count=sampled,
        unique_sampled_world_count=sampled,
    )
    controlled_policy = tuple(
        replace(
            decision,
            selected_card=ranked[0].card,
            reached_world_count=completed,
        )
        if decision.depth_plies == 0
        else decision
        for decision in base.controlled_policy
    )
    compatible_world_count = (
        10 if coverage == "sampled_compatible_worlds" else completed
    )
    world_coverage = (
        "all_compatible_worlds"
        if coverage == "single_exact_world"
        else coverage
    )
    return replace(
        base,
        world_coverage=world_coverage,
        consumed_budget=consumed,
        compatible_world_count=compatible_world_count,
        candidate_results=ranked,
        recommended_card=ranked[0].card,
        controlled_policy=controlled_policy,
    )


def _pimc_result(
    information_result: InformationSetSearchResultV1,
    recommended_card: str,
) -> BoundedSearchResult:
    completed = information_result.consumed_budget.selected_world_count
    candidates = tuple(
        AggregateSearchCandidateResult(
            card=candidate.card,
            rank=1,
            is_recommended=False,
            completed_world_count=completed,
            local_contract_success_count=(
                completed if candidate.card == recommended_card else 0
            ),
            local_contract_success_rate=(
                1.0 if candidate.card == recommended_card else 0.0
            ),
            mean_local_side_game_score=(
                20.0 if candidate.card == recommended_card else 0.0
            ),
            mean_local_side_card_point_margin=(
                10.0 if candidate.card == recommended_card else 0.0
            ),
        )
        for candidate in information_result.candidate_results
    )
    ranked = rank_search_candidate_results(candidates, "grand", recommend=True)
    requested = RequestedSearchBudget(
        max_remaining_tricks=3,
        max_depth_plies=9,
        max_nodes=20_000,
        max_selected_worlds=8,
        max_sampled_worlds=8,
        minimum_comparable_worlds=1,
    )
    sampled = (
        completed
        if information_result.world_coverage == "sampled_compatible_worlds"
        else 0
    )
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type="grand",
        status="complete",
        stop_reason="completed",
        world_coverage=information_result.world_coverage,
        solution_claim="exact_per_selected_world",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=6,
            nodes_expanded=20,
            selected_world_count=completed,
            completed_world_count=completed,
            sampled_world_count=sampled,
            unique_sampled_world_count=sampled,
            wall_clock_elapsed_ms=1,
        ),
        compatible_world_count=information_result.compatible_world_count,
        candidate_results=ranked,
        recommended_card=ranked[0].card,
        fallback_used=False,
        fallback_method=None,
    )


def _decision(
    information_result: InformationSetSearchResultV1 | None = None,
    *,
    actual_card: str | None = None,
    legal_cards: tuple[str, ...] | None = None,
    immediate_recommended_card: str | None = None,
) -> HistoricalInformationSetSearchDecisionReviewV1:
    result = information_result or _information_result()
    result_cards = tuple(candidate.card for candidate in result.candidate_results)
    retained_legal_cards = legal_cards or result_cards or ("CA", "S7")
    canonical_legal_cards = canonicalize_replay_coaching_cards(retained_legal_cards)
    actual = actual_card or canonical_legal_cards[-1]
    pimc = (
        _pimc_result(result, actual)
        if result.status == "complete" and result.candidate_results
        else None
    )
    immediate = immediate_recommended_card
    if immediate is None and result.status == "complete":
        immediate = actual
    pre_actual = build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=result,
        pimc_result=pimc,
        immediate_recommended_card=immediate,
        same_selected_world_sequence=pimc is not None,
    )
    comparison = attach_actual_card_to_information_set_search_comparison_v1(
        pre_actual,
        actual,
    )
    return HistoricalInformationSetSearchDecisionReviewV1(
        source_game_id="game-information-coaching",
        source_played_at="2026-08-23T12:00:00Z",
        decision_index=22,
        trick_number=8,
        play_index=1,
        acting_player_id="player-a",
        acting_seat="forehand",
        acting_role="declarer",
        contract="grand",
        decision_phase="lead",
        remaining_tricks=3,
        legal_cards=canonical_legal_cards,
        actual_card=actual,
        effective_immediate_random_seed=41,
        information_set_result=result,
        information_set_public_result=build_public_information_set_search_result_v1(
            result
        ),
        pimc_result=pimc,
        immediate_recommended_card=immediate,
        comparison=comparison,
    )


def _partial_or_timeout_result(status: str) -> InformationSetSearchResultV1:
    request, base = _base_request_and_result()
    root = next(
        decision for decision in base.controlled_policy if decision.depth_plies == 0
    )
    if status == "partial":
        consumed = InformationSetSearchConsumedBudgetV1(
            depth_reached=1,
            state_nodes_evaluated=request.requested_budget.max_state_nodes,
            information_sets_evaluated=1,
            controlled_policy_decisions=1,
            fixed_policy_decisions=0,
            selected_world_count=2,
            completed_world_count=0,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            wall_clock_elapsed_ms=1,
        )
        return replace(
            base,
            status="partial",
            stop_reason="state_node_budget_exhausted",
            world_coverage="all_compatible_worlds",
            policy_claim="common_policy_prefix",
            consumed_budget=consumed,
            compatible_world_count=2,
            candidate_results=(),
            recommended_card=None,
            controlled_policy=(replace(root, reached_world_count=2),),
        )
    requested = replace(request.requested_budget, wall_clock_timeout_ms=5)
    consumed = InformationSetSearchConsumedBudgetV1(
        depth_reached=1,
        state_nodes_evaluated=4,
        information_sets_evaluated=1,
        controlled_policy_decisions=0,
        fixed_policy_decisions=2,
        selected_world_count=2,
        completed_world_count=0,
        sampled_world_count=2,
        unique_sampled_world_count=2,
        wall_clock_elapsed_ms=5,
    )
    return replace(
        base,
        status="timeout",
        stop_reason="wall_clock_timeout",
        world_coverage="sampled_compatible_worlds",
        policy_claim="none",
        policy_consistency="not_assessed",
        requested_budget=requested,
        consumed_budget=consumed,
        compatible_world_count=10,
        candidate_results=(),
        recommended_card=None,
        controlled_policy=(),
    )


def _collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_collect_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_collect_keys(item) for item in value))
    return set()


def test_evidence_versions_and_policies_are_exact() -> None:
    assert INFORMATION_SET_REPLAY_COACHING_EVIDENCE_VERSION == 1
    assert not isinstance(INFORMATION_SET_REPLAY_COACHING_EVIDENCE_VERSION, bool)
    assert INFORMATION_SET_REPLAY_COACHING_SOURCE_POLICY == (
        "retained_historical_information_set_search_review_without_rerun"
    )
    assert INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY == (
        "decision_time_analysis_then_actual_card_then_outcome_context"
    )
    assert INFORMATION_SET_REPLAY_COACHING_PRIMARY_EVIDENCE_POLICY == (
        "information_set_candidates_primary_pimc_and_immediate_diagnostic_only"
    )
    assert INFORMATION_SET_REPLAY_COACHING_PUBLIC_POLICY == (
        "safe_report_without_private_policy_world_or_observation"
    )


def test_retained_evidence_is_exact_immutable_and_excludes_actual_card() -> None:
    decision = _decision()
    evidence = build_information_set_replay_coaching_decision_time_evidence_v1(
        decision
    )
    serialized = (
        build_serializable_information_set_replay_coaching_decision_time_evidence_v1(
            evidence
        )
    )

    assert evidence.source_game_id == decision.source_game_id
    assert evidence.decision_index == decision.decision_index
    assert evidence.remaining_tricks == 3
    assert evidence.legal_cards == canonicalize_replay_coaching_cards(
        decision.legal_cards
    )
    assert not hasattr(evidence, "actual_card")
    assert "actual_card" not in _collect_keys(serialized)
    assert {
        "controlled_policy",
        "information_set",
        "observation",
        "selected_worlds",
        "exact_state",
        "ownership",
    }.isdisjoint(_collect_keys(serialized))
    with pytest.raises(FrozenInstanceError):
        evidence.remaining_tricks = 2  # type: ignore[misc]
    public = evidence.information_set_pre_actual_analysis.information_set_public_result
    assert public is not None
    with pytest.raises(TypeError):
        public["status"] = "timeout"  # type: ignore[index]


def test_actual_card_attachment_requires_legal_card_and_exact_retained_comparison() -> None:
    decision = _decision()
    evidence = build_information_set_replay_coaching_decision_time_evidence_v1(
        decision
    )

    comparison = (
        attach_retained_actual_card_to_information_set_replay_coaching_evidence_v1(
            evidence,
            actual_card=decision.actual_card,
            retained_comparison=decision.comparison,
        )
    )

    assert comparison is not decision.comparison
    assert comparison == decision.comparison
    with pytest.raises(ValueError, match="legal"):
        attach_retained_actual_card_to_information_set_replay_coaching_evidence_v1(
            evidence,
            actual_card="D7",
            retained_comparison=decision.comparison,
        )
    alternate = next(card for card in evidence.legal_cards if card != decision.actual_card)
    with pytest.raises(ValueError, match="retained review comparison"):
        attach_retained_actual_card_to_information_set_replay_coaching_evidence_v1(
            evidence,
            actual_card=alternate,
            retained_comparison=decision.comparison,
        )


def test_historical_review_legal_cards_remain_private_in_existing_serialization() -> None:
    from skatmind.historical_information_set_search_review import (
        build_serializable_historical_information_set_search_decision_v1,
    )

    decision = _decision()
    serialized = build_serializable_historical_information_set_search_decision_v1(
        decision
    )

    assert decision.legal_cards
    assert "legal_cards" not in serialized
