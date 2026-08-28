import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skatmind.historical_tactical_motif_review import (
    build_historical_tactical_motif_review_v1,
    build_serializable_historical_tactical_motif_review_v1,
)
from skatmind.tactical_motif_contracts import (
    TACTICAL_MOTIF_FAMILIES,
    TACTICAL_MOTIF_TYPES,
)

ROOT = Path(__file__).resolve().parents[1]


def _build_review(path: Path):
    source = json.loads(path.read_text(encoding="utf-8"))["historical_game_input"]
    record = build_historical_game_record(source)
    historical_result = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(historical_result)
    return build_historical_tactical_motif_review_v1(
        historical_game_result=historical_result,
        decision_snapshot_summary=snapshots,
    )


def test_normal_historical_review_has_one_complete_observation_per_play() -> None:
    review = _build_review(ROOT / "examples" / "historical_grand_normal_completion.json")
    serialized = build_serializable_historical_tactical_motif_review_v1(review)

    assert review.observation_count == 30
    assert review.complete_observation_count == 30
    assert review.partial_observation_count == 0
    assert [item.decision_time_facts.decision_index for item in review.observations] == list(
        range(1, 31)
    )
    assert [item[0] for item in review.motif_counts] == list(TACTICAL_MOTIF_TYPES)
    assert [item[0] for item in review.family_counts] == list(TACTICAL_MOTIF_FAMILIES)
    assert len(review.player_summaries) == 3
    assert len(review.role_summaries) == 2
    assert len(review.phase_summaries) == 3
    assert len(review.contract_summaries) == 1
    assert sum(item.motif_occurrence_count for item in review.player_summaries) == (
        review.motif_occurrence_count
    )
    assert "own_hand" not in json.dumps(serialized)
    assert "legal_cards" not in json.dumps(serialized)
    assert serialized == build_serializable_historical_tactical_motif_review_v1(review)


def test_claim_review_uses_only_recorded_plays() -> None:
    review = _build_review(ROOT / "examples" / "historical_party_wide_claim.json")

    assert review.source_game_id == "historical-party-wide-claim-declarer-suit"
    assert review.observation_count == 15
    assert review.complete_observation_count == 15
    assert review.partial_observation_count == 0


def test_incomplete_final_trick_has_partial_observations_without_outcome_motifs() -> None:
    review = _build_review(
        ROOT
        / "tests"
        / "fixtures"
        / "generated_output_schema"
        / "historical_party_wide_claim_defenders_null_incomplete_trick.json"
    )

    assert review.observation_count == 26
    assert review.complete_observation_count == 24
    assert review.partial_observation_count == 2
    for observation in review.observations[-2:]:
        assert observation.completed_trick_winner_player_id is None
        assert all(
            motif.evidence_time == "after_actual_play" for motif in observation.motifs
        )


def test_zero_decision_game_retains_complete_zero_count_scopes() -> None:
    dataset = json.loads(
        (ROOT / "examples" / "training_dataset_variable_length.json").read_text(
            encoding="utf-8"
        )
    )
    source = copy.deepcopy(
        dataset["training_dataset_input"]["records"][0]["historical_game"]
    )
    source["tricks"] = []
    source["game_end"]["declarer_hand_cards_remaining"] = 10
    source["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    historical_result = build_historical_game_summary(
        build_historical_game_record(source)
    )
    review = build_historical_tactical_motif_review_v1(
        historical_game_result=historical_result,
        decision_snapshot_summary=build_historical_decision_snapshots(
            historical_result
        ),
    )

    assert review.observation_count == 0
    assert all(summary.observation_count == 0 for summary in review.player_summaries)
    assert all(summary.observation_count == 0 for summary in review.role_summaries)
    assert all(summary.observation_count == 0 for summary in review.phase_summaries)
    assert review.contract_summaries[0].observation_count == 0


def test_observation_contract_reconciles_card_semantics_and_schema_bounds() -> None:
    review = _build_review(ROOT / "examples" / "historical_grand_normal_completion.json")
    observation = review.observations[0]

    with pytest.raises(ValueError, match="actual_card_points"):
        replace(observation, actual_card_points=observation.actual_card_points + 1)
    with pytest.raises(ValueError, match="actual_effective_category"):
        replace(observation, actual_effective_category="D")
    with pytest.raises(ValueError, match="legal_card_count"):
        replace(observation.decision_time_facts, legal_card_count=11)
    with pytest.raises(ValueError, match="completed_trick_points"):
        replace(observation, completed_trick_points=34)
