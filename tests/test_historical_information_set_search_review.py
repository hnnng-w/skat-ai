import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skat_ai.historical_information_set_search_review import (
    HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD,
    HistoricalInformationSetSearchReviewSettingsV1,
    build_historical_information_set_search_review_summary_v1,
    build_historical_information_set_search_review_v1,
    build_information_set_search_budget_from_profile_v1,
)
from skat_ai.information_set_search_comparison import (
    build_information_set_search_comparison_pre_actual_analysis_v1,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_record(example_name: str):
    data = json.loads((ROOT / "examples" / example_name).read_text("utf-8"))
    record = build_historical_game_record(data["historical_game_input"])
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )
    return record, snapshots


def _zero_decision_record():
    data = json.loads(
        (ROOT / "examples" / "training_dataset_variable_length.json").read_text(
            "utf-8"
        )
    )["training_dataset_input"]["records"][0]["historical_game"]
    data = copy.deepcopy(data)
    data["tricks"] = []
    data["game_end"]["declarer_hand_cards_remaining"] = 10
    data["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    record = build_historical_game_record(data)
    return record, build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )


def _unavailable_builder(observed_inputs: list | None = None):
    def build(decision_input):
        if observed_inputs is not None:
            observed_inputs.append(decision_input)
        assert not hasattr(decision_input, "actual_card")
        assert not hasattr(decision_input, "historical_record")
        return build_information_set_search_comparison_pre_actual_analysis_v1(
            information_set_result=None,
            pimc_result=None,
            immediate_recommended_card=decision_input.visible_state.legal_cards[0],
            same_selected_world_sequence=False,
        )

    return build


def test_profile_conversion_is_exact_and_settings_are_immutable() -> None:
    budget = build_information_set_search_budget_from_profile_v1(
        "historical_review_v1"
    )
    settings = HistoricalInformationSetSearchReviewSettingsV1(  # type: ignore[call-arg]
        base_search_seed=7
    )

    assert budget.max_remaining_tricks == 3
    assert budget.max_depth_plies == 9
    assert budget.max_state_nodes == 2_000_000
    assert budget.max_information_sets == 2_000_000
    assert budget.max_selected_worlds == 128
    assert budget.max_sampled_worlds == 64
    assert budget.minimum_comparable_worlds == 16
    assert budget.wall_clock_timeout_ms == 5_000
    with pytest.raises(FrozenInstanceError):
        settings.base_search_seed = 8  # type: ignore[misc]
    with pytest.raises(ValueError, match="base_search_seed"):
        HistoricalInformationSetSearchReviewSettingsV1(  # type: ignore[call-arg]
            base_search_seed=True
        )


def test_review_has_one_unavailable_row_per_play_and_reconciled_breakdowns() -> None:
    record, snapshots = _load_record("historical_grand_declarer_concession.json")
    observed_inputs = []
    settings = HistoricalInformationSetSearchReviewSettingsV1(
        base_search_seed=11,
        immediate_sample_count=1,
        immediate_base_random_seed=20,
    )

    summary = build_historical_information_set_search_review_v1(
        snapshots,
        record,
        settings,
        pre_actual_analysis_builder=_unavailable_builder(observed_inputs),
    )
    serialized = build_historical_information_set_search_review_summary_v1(
        snapshots,
        record,
        settings,
        pre_actual_analysis_builder=_unavailable_builder(),
    )

    assert summary.review_method == HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD
    assert len(summary.decisions) == snapshots.snapshot_count
    assert len(observed_inputs) == snapshots.snapshot_count
    assert summary.metrics.decision_count == snapshots.snapshot_count
    assert dict(summary.metrics.status_counts) == {
        "not_available": snapshots.snapshot_count
    }
    assert summary.metrics.comparison_unavailable_count == snapshots.snapshot_count
    assert all(
        decision.comparison.unavailable_reason
        == "information_set_result_not_available"
        for decision in summary.decisions
    )
    assert [
        decision.effective_immediate_random_seed for decision in summary.decisions
    ] == list(range(20, 20 + snapshots.snapshot_count))
    assert all(
        sum(row["metrics"]["decision_count"] for row in rows)
        == snapshots.snapshot_count
        for rows in serialized["breakdowns"].values()
    )
    assert len(serialized["decisions"]) == snapshots.snapshot_count
    with pytest.raises(FrozenInstanceError):
        summary.decisions = ()  # type: ignore[misc]


def test_zero_decision_review_is_valid_and_does_not_call_builder() -> None:
    record, snapshots = _zero_decision_record()
    calls = []

    summary = build_historical_information_set_search_review_v1(
        snapshots,
        record,
        HistoricalInformationSetSearchReviewSettingsV1(base_search_seed=3),
        pre_actual_analysis_builder=_unavailable_builder(calls),
    )

    assert snapshots.snapshot_count == 0
    assert summary.decisions == ()
    assert summary.metrics.decision_count == 0
    assert summary.metrics.status_counts == ()
    assert all(breakdown.rows == () for breakdown in summary.breakdowns)
    assert calls == []


@pytest.mark.parametrize(
    "example_name,end_reason",
    [
        (
            "historical_grand_defender_open_play.json",
            "defender_open_play",
        ),
        (
            "historical_party_wide_claim.json",
            "party_wide_all_remaining_tricks_claim",
        ),
    ],
)
def test_variable_and_claim_endings_have_only_played_card_rows(
    example_name: str,
    end_reason: str,
) -> None:
    record, snapshots = _load_record(example_name)

    summary = build_historical_information_set_search_review_v1(
        snapshots,
        record,
        HistoricalInformationSetSearchReviewSettingsV1(base_search_seed=5),
        pre_actual_analysis_builder=_unavailable_builder(),
    )

    assert summary.game_end_reason == end_reason
    assert len(summary.decisions) == sum(
        len(trick.plays) for trick in record.tricks
    )
    assert len(summary.decisions) == snapshots.snapshot_count
    assert all(
        decision.actual_card == snapshot.actual_card_played
        for decision, snapshot in zip(
            summary.decisions, snapshots.snapshots, strict=True
        )
    )
