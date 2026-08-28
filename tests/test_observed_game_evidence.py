from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_historical_game import build_historical_input
from test_observed_game_commentary import commentary, link
from test_observed_game_contracts import (
    build_complete_observed_record,
    build_observed_match,
    build_observed_record,
    declaration_from_historical,
    observed_plays_from_historical,
)

from skatmind.game_declaration import GameDeclaration
from skatmind.observed_game_evidence import (
    ObservedGameEvidenceSummaryV1,
    build_observed_game_evidence_summary_v1,
)


def test_empty_observation_has_zero_counts_and_no_reconstruction_capability() -> None:
    summary = build_observed_game_evidence_summary_v1(build_observed_record())
    assert summary.to_dict() == {
        "observed_game_evidence_version": 1,
        "play_count": 0,
        "completed_trick_count": 0,
        "current_trick_play_count": 0,
        "perspective_initial_hand_known": False,
        "original_skat_known": False,
        "discarded_cards_known": False,
        "complete_play_trace": False,
        "perspective_decision_samples_reconstructable": False,
        "all_player_decision_samples_reconstructable": False,
        "discard_review_reconstructable": False,
        "complete_initial_deal_reconstructable": False,
        "commentary_count": 0,
        "response_link_count": 0,
    }


def test_perspective_hand_requires_an_exact_known_transformation_for_samples() -> None:
    data = build_historical_input()
    hand = data["players"][0]["initial_hand"]
    hand_only = build_observed_game_evidence_summary_v1(
        build_observed_record(perspective_initial_hand=hand)
    )
    defender = build_observed_game_evidence_summary_v1(
        build_observed_record(
            perspective_initial_hand=hand,
            declarer_player_id="player-b",
            declaration=GameDeclaration(game_type="grand"),
        )
    )
    assert hand_only.perspective_initial_hand_known is True
    assert hand_only.perspective_decision_samples_reconstructable is False
    assert defender.perspective_decision_samples_reconstructable is True


def test_partial_trace_counts_and_perspective_sample_capability_reconcile() -> None:
    data = build_historical_input()
    record = build_observed_record(
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=observed_plays_from_historical(data, count=8),
    )
    summary = build_observed_game_evidence_summary_v1(record)
    counts = (
        summary.play_count,
        summary.completed_trick_count,
        summary.current_trick_play_count,
    )
    assert counts == (
        8,
        2,
        2,
    )
    assert summary.perspective_decision_samples_reconstructable is True
    assert summary.complete_play_trace is False
    assert summary.all_player_decision_samples_reconstructable is False


@pytest.mark.parametrize(
    ("game_type", "hand_game"),
    (("clubs", True), ("grand", False), ("null", False)),
)
def test_complete_legal_trace_reconstructs_all_player_decision_samples(
    game_type: str,
    hand_game: bool,
) -> None:
    summary = build_observed_game_evidence_summary_v1(
        build_complete_observed_record(game_type=game_type, hand_game=hand_game)
    )
    assert summary.play_count == 30
    assert summary.completed_trick_count == 10
    assert summary.current_trick_play_count == 0
    assert summary.complete_play_trace is True
    assert summary.perspective_decision_samples_reconstructable is True
    assert summary.all_player_decision_samples_reconstructable is True


def test_complete_trace_does_not_infer_missing_skat_or_discards() -> None:
    missing_both = build_observed_game_evidence_summary_v1(
        build_complete_observed_record(
            include_original_skat=False,
            include_discards=False,
        )
    )
    missing_skat = build_observed_game_evidence_summary_v1(
        build_complete_observed_record(include_original_skat=False)
    )
    missing_discards = build_observed_game_evidence_summary_v1(
        build_complete_observed_record(include_discards=False)
    )
    assert missing_both.complete_play_trace is True
    assert missing_both.original_skat_known is False
    assert missing_both.discarded_cards_known is False
    assert missing_both.complete_initial_deal_reconstructable is False
    assert missing_skat.complete_initial_deal_reconstructable is False
    assert missing_discards.complete_initial_deal_reconstructable is False


def test_full_non_hand_evidence_supports_discard_review_and_complete_initial_deal() -> None:
    summary = build_observed_game_evidence_summary_v1(build_complete_observed_record())
    assert summary.original_skat_known is True
    assert summary.discarded_cards_known is True
    assert summary.discard_review_reconstructable is True
    assert summary.complete_initial_deal_reconstructable is True


def test_full_hand_evidence_has_known_empty_discards_but_no_discard_review() -> None:
    summary = build_observed_game_evidence_summary_v1(
        build_complete_observed_record(game_type="clubs", hand_game=True)
    )
    assert summary.discarded_cards_known is True
    assert summary.discard_review_reconstructable is False
    assert summary.complete_initial_deal_reconstructable is True


def test_visible_non_hand_declarer_evidence_supports_discard_review_without_plays() -> None:
    data = build_historical_input()
    declarer = data["declarer_player_id"]
    declarer_hand = next(
        player["initial_hand"]
        for player in data["players"]
        if player["player_id"] == declarer
    )
    record = build_observed_record(
        match_definition=build_observed_match(perspective_player_id=declarer),
        perspective_initial_hand=declarer_hand,
        declarer_player_id=declarer,
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
    )
    summary = build_observed_game_evidence_summary_v1(record)
    assert summary.complete_play_trace is False
    assert summary.perspective_decision_samples_reconstructable is True
    assert summary.discard_review_reconstructable is True
    assert summary.complete_initial_deal_reconstructable is False


def test_commentary_and_response_counts_use_canonical_retained_values() -> None:
    data = build_historical_input()
    plays = observed_plays_from_historical(data, count=3)
    record = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=plays,
        commentaries=(commentary("comment-1", 1, plays[0].player_id),),
        response_links=(link("link-1", "comment-1", 2),),
    )
    summary = build_observed_game_evidence_summary_v1(record)
    assert summary.commentary_count == 1
    assert summary.response_link_count == 1


def test_evidence_builder_is_deterministic_fresh_and_executes_no_workflow(monkeypatch) -> None:
    import skatmind.historical_game as historical_game
    import skatmind.training_dataset as training_dataset

    def unexpected_execution(*_args, **_kwargs):
        raise AssertionError("Evidence summary attempted workflow materialization.")

    monkeypatch.setattr(
        historical_game,
        "build_historical_game_summary",
        unexpected_execution,
    )
    monkeypatch.setattr(
        training_dataset,
        "build_training_dataset_summary",
        unexpected_execution,
    )
    record = build_complete_observed_record()
    first = build_observed_game_evidence_summary_v1(record)
    second = build_observed_game_evidence_summary_v1(record)
    first_dict = first.to_dict()
    second_dict = second.to_dict()
    first_dict["play_count"] = 0
    assert first == second
    assert second_dict["play_count"] == 30


def test_evidence_builder_defensively_revalidates_a_mutated_record() -> None:
    record = build_complete_observed_record()
    forged_plays = list(record.plays)
    forged_plays[1] = replace(forged_plays[1], card=forged_plays[0].card)
    object.__setattr__(record, "plays", tuple(forged_plays))
    with pytest.raises(ValueError, match="more than once"):
        build_observed_game_evidence_summary_v1(record)


def test_evidence_value_enforces_types_relationships_and_immutability() -> None:
    summary = build_observed_game_evidence_summary_v1(build_observed_record())
    assert [field.name for field in fields(summary)] == [
        "observed_game_evidence_version",
        "play_count",
        "completed_trick_count",
        "current_trick_play_count",
        "perspective_initial_hand_known",
        "original_skat_known",
        "discarded_cards_known",
        "complete_play_trace",
        "perspective_decision_samples_reconstructable",
        "all_player_decision_samples_reconstructable",
        "discard_review_reconstructable",
        "complete_initial_deal_reconstructable",
        "commentary_count",
        "response_link_count",
    ]
    assert not hasattr(summary, "__dict__")
    with pytest.raises(FrozenInstanceError):
        summary.play_count = 1
    with pytest.raises(TypeError, match="focused builder"):
        ObservedGameEvidenceSummaryV1()
