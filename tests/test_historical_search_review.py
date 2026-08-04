import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from test_historical_game import build_historical_input, rebuild_historical_suffix

from skat_ai.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    rank_search_candidate_results,
)
from skat_ai.deck import get_full_deck
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skat_ai.historical_search_review import (
    HISTORICAL_SEARCH_DECISION_SEED_DOMAIN,
    HistoricalSearchReviewSettings,
    build_historical_search_decision_review,
    build_historical_search_review_internal_result,
    build_historical_search_review_metrics,
    build_historical_search_review_summary,
    derive_historical_search_decision_seed,
)
from skat_ai.rules import get_legal_cards
from skat_ai.terminal_utility import TERMINAL_UTILITY_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _load_historical(name: str):
    data = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    record = build_historical_game_record(data["historical_game_input"])
    summary = build_historical_game_summary(record)
    return record, build_historical_decision_snapshots(summary)


def _fake_immediate(*, state, **_kwargs):
    legal_cards = get_legal_cards(state.hand, state.current_trick, state.game_type)
    recommended = legal_cards[-1]
    values = {
        card: {
            "win_rate": 1.0 if card == recommended else 0.0,
            "average_trick_points": 10.0 if card == recommended else 0.0,
            "average_points_won": 10.0 if card == recommended else 0.0,
            "average_points_lost": 0.0,
        }
        for card in legal_cards
    }
    return recommended, "deterministic test baseline", values


def _fake_search(*, information_view, requested_budget, random_seed):
    legal_cards = tuple(
        get_legal_cards(
            list(information_view.local_remaining_hand),
            [play.card for play in information_view.current_trick],
            information_view.game_type,
        )
    )
    candidates = tuple(
        AggregateSearchCandidateResult(
            card=card,
            rank=1,
            is_recommended=False,
            completed_world_count=1,
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
    )
    ranked = rank_search_candidate_results(
        candidates, information_view.game_type, recommend=True
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
        consumed_budget=ConsumedSearchBudget(
            depth_reached=1,
            nodes_expanded=random_seed % 100 + 1,
            selected_world_count=1,
            completed_world_count=1,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            wall_clock_elapsed_ms=2,
        ),
        compatible_world_count=1,
        candidate_results=ranked,
        recommended_card=ranked[0].card,
        fallback_used=False,
        fallback_method=None,
    )


def _collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(
            *(_collect_keys(item) for item in value.values()),
        )
    if isinstance(value, list):
        return set().union(*(_collect_keys(item) for item in value))
    return set()


def _collect_card_values(value) -> set[str]:
    deck = set(get_full_deck())
    if isinstance(value, str):
        return {value} if value in deck else set()
    if isinstance(value, dict):
        return set().union(*(_collect_card_values(item) for item in value.values()))
    if isinstance(value, (list, tuple)):
        return set().union(*(_collect_card_values(item) for item in value))
    return set()


def _plain_json_value(value):
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    return value


def test_decision_seed_uses_only_stable_identity_material() -> None:
    expected_material = (
        f"skat-ai\0{41}\0{HISTORICAL_SEARCH_DECISION_SEED_DOMAIN}\0game-7\0{3}"
    ).encode()
    expected = int.from_bytes(hashlib.sha256(expected_material).digest()[:8], "big")

    assert derive_historical_search_decision_seed(41, "game-7", 3) == expected
    assert derive_historical_search_decision_seed(41, "game-7", 3) == expected
    assert derive_historical_search_decision_seed(41, "game-8", 3) != expected
    with pytest.raises(ValueError, match="base_search_seed"):
        derive_historical_search_decision_seed(True, "game-7", 3)
    with pytest.raises(ValueError, match="stable_game_identity"):
        derive_historical_search_decision_seed(41, "", 3)
    with pytest.raises(ValueError, match="decision_index"):
        derive_historical_search_decision_seed(41, "game-7", 0)


def test_actual_top_n_metrics_ignore_canonical_tie_order(monkeypatch) -> None:
    record, snapshots = _load_historical("historical_grand_normal_completion.json")
    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax",
        _fake_search,
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    decision = build_historical_search_decision_review(
        snapshots.snapshots[0],
        record,
        HistoricalSearchReviewSettings(base_search_seed=41),
        stable_game_identity=record.game_id,
    )
    comparison = decision["search_actual_card_comparison"]
    comparison["actual_card_rank"] = 4
    comparison["strictly_better_card_count"] = 0
    metrics = build_historical_search_review_metrics(
        [
            {
                **decision,
                "search_status": decision["bounded_search_result"]["status"],
                "search_coverage": decision["bounded_search_result"]["world_coverage"],
            }
        ]
    )

    assert metrics["actual_card_agreement"]["actual_top_1_count"] == 1
    assert metrics["actual_card_agreement"]["actual_top_3_count"] == 1


def test_sampled_decision_seed_is_stable_domain_separated_and_not_serialized(
    monkeypatch,
) -> None:
    record, snapshots = _load_historical("historical_grand_normal_completion.json")
    snapshot = snapshots.snapshots[0]
    first_seed = derive_historical_search_decision_seed(
        41, record.game_id, snapshot.decision_index
    )
    changed_root_seed = next(
        root_seed
        for root_seed in range(42, 10_000)
        if derive_historical_search_decision_seed(
            root_seed, record.game_id, snapshot.decision_index
        )
        % 100
        != first_seed % 100
    )
    observed_search_seeds = []

    def sampled_search(**kwargs):
        observed_search_seeds.append(kwargs["random_seed"])
        exact = _fake_search(**kwargs)
        return replace(
            exact,
            world_coverage="sampled_compatible_worlds",
            consumed_budget=replace(
                exact.consumed_budget,
                sampled_world_count=1,
                unique_sampled_world_count=1,
            ),
            compatible_world_count=2,
        )

    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax",
        sampled_search,
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )

    first = build_historical_search_decision_review(
        snapshot, record, HistoricalSearchReviewSettings(41, immediate_sample_count=1)
    )
    repeated = build_historical_search_decision_review(
        snapshot, record, HistoricalSearchReviewSettings(41, immediate_sample_count=1)
    )
    changed = build_historical_search_decision_review(
        snapshot,
        record,
        HistoricalSearchReviewSettings(changed_root_seed, immediate_sample_count=1),
    )

    assert observed_search_seeds == [first_seed, first_seed, derive_historical_search_decision_seed(
        changed_root_seed, record.game_id, snapshot.decision_index
    )]
    assert first == repeated
    assert first["bounded_search_result"]["world_coverage"] == (
        "sampled_compatible_worlds"
    )
    assert first["bounded_search_result"]["consumed_budget"]["nodes_expanded"] != (
        changed["bounded_search_result"]["consumed_budget"]["nodes_expanded"]
    )
    assert {"decision_seed", "derived_seed", "search_seed"}.isdisjoint(
        _collect_keys(first)
    )
    assert all(
        "seed" not in key for key in _collect_keys(first["bounded_search_result"])
    )


def test_settings_are_frozen_and_validate_all_required_inputs() -> None:
    settings = HistoricalSearchReviewSettings(base_search_seed=9)
    assert settings.immediate_sample_count == 100
    assert settings.search_budget_profile == "historical_review_v1"
    with pytest.raises(FrozenInstanceError):
        settings.base_search_seed = 10  # type: ignore[misc]
    with pytest.raises(ValueError, match="Unknown Search budget profile"):
        HistoricalSearchReviewSettings(9, search_budget_profile="missing")
    with pytest.raises(ValueError, match="immediate_sample_count"):
        HistoricalSearchReviewSettings(9, immediate_sample_count=0)


def test_single_decision_runs_both_analyses_before_observed_comparisons(
    monkeypatch,
) -> None:
    record, snapshots = _load_historical("historical_grand_normal_completion.json")
    events = []

    def search(**kwargs):
        events.append("search")
        return _fake_search(**kwargs)

    def immediate(**kwargs):
        events.append("immediate")
        return _fake_immediate(**kwargs)

    def coaching_evidence(**kwargs):
        events.append("coaching_evidence")
        from skat_ai.replay_coaching_evidence import (
            build_decision_time_replay_coaching_evidence,
        )

        return build_decision_time_replay_coaching_evidence(**kwargs)

    def actual_comparison(result, actual_card):
        events.append(("actual", actual_card))
        from skat_ai.retrospective_search_comparison import (
            build_search_actual_card_comparison,
        )

        return build_search_actual_card_comparison(result, actual_card)

    def coaching_assessment(**kwargs):
        events.append(("coaching_assessment", kwargs["actual_card"]))
        from skat_ai.replay_coaching_assessment import (
            build_replay_coaching_decision_assessment,
        )

        return build_replay_coaching_decision_assessment(**kwargs)

    monkeypatch.setattr("skat_ai.historical_search_review.solve_compatible_world_minimax", search)
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.build_decision_time_replay_coaching_evidence",
        coaching_evidence,
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.build_search_actual_card_comparison",
        actual_comparison,
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.build_replay_coaching_decision_assessment",
        coaching_assessment,
    )
    decision = build_historical_search_decision_review(
        snapshots.snapshots[0],
        record,
        HistoricalSearchReviewSettings(17, immediate_base_random_seed=30),
    )

    assert events == [
        "search",
        "immediate",
        "coaching_evidence",
        ("actual", snapshots.snapshots[0].actual_card_played),
        ("coaching_assessment", snapshots.snapshots[0].actual_card_played),
    ]
    assert decision["root_seat"] == "lead"
    assert decision["immediate_baseline"]["effective_random_seed"] == 30
    assert decision["actual_card"] == snapshots.snapshots[0].actual_card_played
    assert "random_seed" not in decision["bounded_search_result"]
    assert "hidden" not in json.dumps(decision).lower()


def test_shared_prefix_search_output_ignores_changed_future_private_cards(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", _fake_search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    original_data = build_historical_input()
    changed_data = rebuild_historical_suffix(original_data, completed_prefix_tricks=5)
    original_record = build_historical_game_record(original_data)
    changed_record = build_historical_game_record(changed_data)
    original_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(original_record)
    )
    changed_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(changed_record)
    )
    shared_index = 14
    original_snapshot = original_snapshots.snapshots[shared_index]
    changed_snapshot = changed_snapshots.snapshots[shared_index]

    assert original_data["tricks"][:5] == changed_data["tricks"][:5]
    assert original_data["tricks"][5:] != changed_data["tricks"][5:]
    assert original_snapshot == changed_snapshot

    settings = HistoricalSearchReviewSettings(73, immediate_sample_count=1)
    original_decision = build_historical_search_decision_review(
        original_snapshot, original_record, settings
    )
    changed_decision = build_historical_search_decision_review(
        changed_snapshot, changed_record, settings
    )

    assert original_decision == changed_decision
    assert original_decision["bounded_search_result"]["recommended_card"] == (
        changed_decision["bounded_search_result"]["recommended_card"]
    )
    assert original_decision["bounded_search_result"]["candidate_results"] == (
        changed_decision["bounded_search_result"]["candidate_results"]
    )
    assert (
        original_decision["bounded_search_result"]["status"],
        original_decision["bounded_search_result"]["world_coverage"],
    ) == (
        changed_decision["bounded_search_result"]["status"],
        changed_decision["bounded_search_result"]["world_coverage"],
    )
    hidden_future_cards = {
        card
        for player in original_record.players
        if player.player_id != original_snapshot.acting_player_id
        for card in player.initial_hand
        if card not in _collect_card_values(original_snapshot.visible_state)
    }
    assert hidden_future_cards
    assert hidden_future_cards.isdisjoint(_collect_card_values(original_decision))
    assert {"decision_seed", "derived_seed", "search_seed"}.isdisjoint(
        _collect_keys(original_decision)
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
    ],
)
def test_summary_supports_every_historical_end_type(
    monkeypatch, example_name: str
) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", _fake_search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    record, snapshots = _load_historical(example_name)

    result = build_historical_search_review_summary(
        snapshots,
        record,
        base_search_seed=5,
        immediate_sample_count=1,
    )

    decision_count = result["decision_counts"]["decision_count"]
    assert decision_count == snapshots.snapshot_count
    assert sum(result["status_counts"].values()) == decision_count
    assert sum(result["coverage"].values()) == decision_count
    assert result["quality_gate"]["quality_gate_passed"] is True
    assert all(
        sum(row["metrics"]["decision_counts"]["decision_count"] for row in rows)
        == decision_count
        for rows in result["breakdowns"].values()
    )


def test_zero_decision_summary_has_reconciled_empty_metrics() -> None:
    data = json.loads(
        (ROOT / "examples" / "training_dataset_variable_length.json").read_text(
            encoding="utf-8"
        )
    )["training_dataset_input"]["records"][0]["historical_game"]
    data["tricks"] = []
    data["game_end"]["declarer_hand_cards_remaining"] = 10
    data["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    record = build_historical_game_record(data)
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )

    result = build_historical_search_review_summary(snapshots, record, 5)

    assert result["decision_counts"]["decision_count"] == 0
    assert result["decision_counts"]["search_attempted_count"] == 0
    assert result["search_vs_immediate_agreement"]["same_recommended_card_rate"] is None
    assert result["actual_card_agreement"]["actual_top_1_rate"] is None
    assert result["quality_gate"]["quality_gate_passed"] is True
    assert result["performance"]["nodes_expanded"] == {
        "total": 0,
        "mean": None,
        "p50": None,
        "p95": None,
        "max": None,
    }
    assert all(rows == [] for rows in result["breakdowns"].values())
    assert result["decisions"] == []


def test_internal_review_retains_assessments_without_changing_public_summary(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", _fake_search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    record, snapshots = _load_historical("historical_grand_normal_completion.json")

    internal = build_historical_search_review_internal_result(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
    )
    public = build_historical_search_review_summary(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
    )

    assert _plain_json_value(internal.public_review_summary) == public
    assert len(internal.assessments) == len(public["decisions"]) == 30
    assert [assessment.actual_card for assessment in internal.assessments] == [
        decision["actual_card"] for decision in public["decisions"]
    ]
    assert all("coaching" not in key for key in _collect_keys(public))
    with pytest.raises(TypeError):
        internal.public_review_summary["settings"]["base_search_seed"] = 9  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        internal.assessments = ()  # type: ignore[misc]


def test_internal_review_runs_search_and_immediate_once_per_decision(monkeypatch) -> None:
    record, snapshots = _load_historical("historical_grand_normal_completion.json")
    call_counts = {"search": 0, "immediate": 0}

    def search(**kwargs):
        call_counts["search"] += 1
        return _fake_search(**kwargs)

    def immediate(**kwargs):
        call_counts["immediate"] += 1
        return _fake_immediate(**kwargs)

    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        immediate,
    )

    result = build_historical_search_review_internal_result(
        snapshots,
        record,
        43,
        immediate_sample_count=1,
    )

    assert len(result.assessments) == snapshots.snapshot_count
    assert call_counts == {
        "search": snapshots.snapshot_count,
        "immediate": snapshots.snapshot_count,
    }


def test_real_search_reports_early_unavailable_and_late_eligible(monkeypatch) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    record, snapshots = _load_historical("historical_grand_normal_completion.json")
    settings = HistoricalSearchReviewSettings(23, immediate_sample_count=1)

    early = build_historical_search_decision_review(
        snapshots.snapshots[0], record, settings
    )
    late = build_historical_search_decision_review(
        snapshots.snapshots[-1], record, settings
    )

    assert early["bounded_search_result"]["status"] == "unavailable"
    assert early["bounded_search_result"]["stop_reason"] in {
        "missing_terminal_utility_inputs",
        "remaining_trick_limit_exceeded",
    }
    assert late["bounded_search_result"]["status"] == "complete"
    assert late["bounded_search_result"]["world_coverage"] in {
        "all_compatible_worlds",
        "sampled_compatible_worlds",
    }
