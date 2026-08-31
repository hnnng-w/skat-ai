from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from skatmind.api.v1 import ExecutionResultV1, ResultDocumentV1, WorkflowV1
from skatmind.app_web.guided_contracts import (
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESULT_DOWNLOAD_ROUTE_PATH,
)
from skatmind.app_web.result_presentation import (
    RESULT_SECTION_TITLES_V1,
    TEXTUAL_NORMAL_RESULT_STATES_V1,
    BrowserSafeResultPresentationV1,
    build_result_presentation_v1,
)
from skatmind.app_web.result_rendering import (
    render_result_presentation_v1,
    render_safe_result_error_summary_v1,
)


def _execution(
    workflow: WorkflowV1,
    document: dict[str, object],
    *,
    warnings: tuple[str, ...] = (),
) -> ExecutionResultV1:
    return ExecutionResultV1(
        result=ResultDocumentV1(
            workflow=workflow,
            document=document,
            warnings=warnings,
        )
    )


def _position_document(*, status: str = "partial") -> dict[str, object]:
    return {
        "input_file": "C:/private/result-input.json",
        "position": {
            "game_type": "grand",
            "player_role": "defender",
            "player_position": "rearhand",
            "next_player": "me",
            "current_trick": ["S7", "S8"],
            "completed_tricks": [{"private_cards": ["CA"]}],
            "declarer_points": 41,
            "defender_points": 30,
            "private_hand": ["CA"],
        },
        "settings": {"sample_count": 20, "recommendation_method": "auto"},
        "game_declaration": {
            "game_type": "grand",
            "hand_game": False,
            "ouvert": False,
            "matadors": 2,
            "bid_value": 24,
        },
        "legal_cards": ["S7", "H9"],
        "recommendation": {
            "card": "H9",
            "reason": "Prefer H9 over <unsafe & unescaped>.",
            "private_reason": "do-not-render-private-reason",
        },
        "recommendation_method_summary": {
            "requested_method": "auto",
            "effective_method": "immediate_expected_value",
            "fallback_used": True,
            "fallback_method": "immediate_expected_value",
            "private_seed": 999,
        },
        "analysis_report": [
            {
                "card": "H9",
                "is_recommended": True,
                "win_rate": 0.75,
                "expected_point_swing": 3.5,
                "average_trick_points": 7.0,
                "private_world": "first-secret",
            },
            {
                "card": "S7",
                "is_recommended": False,
                "win_rate": 0.5,
                "expected_point_swing": 1.0,
                "average_trick_points": 4.0,
                "private_world": "second-secret",
            },
        ],
        "bounded_search_result": {
            "status": status,
            "stop_reason": "node_budget_exhausted",
            "world_coverage": "sampled_compatible_worlds",
            "compatible_world_count": 18,
            "candidate_results": [
                {"card": "CA", "private_world": "unused-secret"},
            ],
            "requested_budget": {
                "max_remaining_tricks": 3,
                "max_depth_plies": 9,
                "max_selected_worlds": 4,
                "max_sampled_worlds": 4,
                "minimum_comparable_worlds": 2,
                "wall_clock_timeout_ms": None,
            },
            "consumed_budget": {
                "selected_world_count": 4,
                "completed_world_count": 2,
                "sampled_world_count": 4,
                "unique_sampled_world_count": 3,
                "nodes_expanded": 12,
            },
            "private_states": ["raw-complete-marker"],
        },
        "information_policy_summary": {
            "analysis_mode": "post_game_review",
            "skat_visibility": "known_post_game",
            "game_end_reason": "not_ended",
        },
        "post_game_review_summary": {
            "actual_card_played": "S7",
            "decision_quality": "acceptable",
        },
        "private_provenance": {"fingerprint": "raw-complete-marker"},
    }


def _historical_document() -> dict[str, object]:
    return {
        "input_file": "C:/private/history.json",
        "historical_game_summary": {
            "schema_version": 1,
            "game_id": "game-<unsafe>",
            "status": "complete",
            "played_at": "2026-08-31T10:00:00+00:00",
            "record": {
                "game_id": "game-<unsafe>",
                "declarer_player_id": "player-b",
                "declaration": {
                    "game_type": "clubs",
                    "hand_game": True,
                    "ouvert": False,
                    "bid_value": 36,
                    "matadors": 2,
                },
                "game_end_reason": "party_wide_all_remaining_tricks_claim",
                "tricks": [{"raw_cards": ["CA"]}],
                "players": [
                    {
                        "player_id": "player-a",
                        "player_label": "Alex",
                        "seat": "forehand",
                        "initial_hand": ["raw-complete-marker"],
                    },
                    {
                        "player_id": "player-b",
                        "player_label": "Blair",
                        "seat": "middlehand",
                    },
                    {"player_id": "player-c", "seat": "rearhand"},
                ],
            },
            "derived_tricks": [
                {"trick_number": 1, "private_plays": ["CA"]},
                {"trick_number": 2, "private_plays": ["SA"]},
            ],
            "declarer_points": 72,
            "defender_points": 48,
            "winner": "declarer",
            "schneider_status": "none",
            "schwarz_status": "none",
            "game_result_summary": {
                "status": "final",
                "winner": "declarer",
                "game_end_reason": "party_wide_all_remaining_tricks_claim",
            },
            "game_value_summary": {"game_value": 36},
            "overbid_summary": {"status": "not_overbid", "required_game_value": 36},
            "final_settlement_summary": {
                "is_complete": True,
                "effective_game_value": 36,
                "settlement_score": 36,
            },
            "historical_game_review_summary": {
                "analysis_method": "immediate_expected_value",
                "decision_count": 2,
                "reviewed_decision_count": 1,
                "unavailable_decision_count": 1,
                "decisions": [
                    {
                        "decision_index": 1,
                        "trick_number": 1,
                        "play_index": 1,
                        "acting_player_id": "player-<a>",
                        "actual_card_played": "CA",
                        "recommendation": {"card": "CA"},
                        "post_game_review_summary": {"decision_quality": "optimal"},
                        "private_snapshot": "first-decision-secret",
                    },
                    {
                        "decision_index": 2,
                        "trick_number": 1,
                        "play_index": 2,
                        "acting_player_id": "player-b",
                        "actual_card_played": "S7",
                        "recommendation": {"card": "S8"},
                        "post_game_review_summary": {"decision_quality": "mistake"},
                        "private_snapshot": "second-decision-secret",
                    },
                ],
            },
            "historical_search_review_summary": {
                "analysis_method": "bounded_search_with_immediate_baseline",
                "decision_counts": {"decision_count": 1},
                "status_counts": {
                    "complete": 0,
                    "partial": 0,
                    "timeout": 1,
                    "unavailable": 0,
                },
                "coverage": {
                    "exact_coverage_decision_count": 0,
                    "sampled_coverage_decision_count": 1,
                    "no_coverage_decision_count": 0,
                },
                "decisions": [
                    {
                        "decision_index": 2,
                        "trick_number": 1,
                        "play_index": 2,
                        "actual_card": "S7",
                        "bounded_search_result": {
                            "status": "timeout",
                            "recommended_card": None,
                        },
                        "immediate_baseline": {"recommendation": {"card": "S8"}},
                        "search_actual_card_comparison": {"is_available": False},
                    }
                ],
            },
            "historical_replay_coaching_summary": {
                "report_method": "historical_replay_coaching_v1",
                "limitations": [
                    "single_recorded_game_only",
                    "no_causal_outcome_claim",
                    "private_coaching_secret",
                ],
            },
            "historical_tactical_motif_review_summary": {
                "review_method": "historical_tactical_motif_review_v1",
                "observation_count": 2,
                "motif_occurrence_count": 3,
                "limitations": [
                    "structural_observation_not_quality_assessment",
                    "no_hidden_ownership_inference",
                ],
            },
            "historical_game_end_summary": {
                "kind": "party_wide_all_remaining_tricks_claim",
                "proof_maximum_unresolved_tricks": 5,
                "exact_proof": {
                    "status": "valid",
                    "evaluated_state_count": 12,
                    "terminal_state_count": 3,
                    "representative_line": ["raw-complete-marker"],
                },
            },
            "private_review": "raw-complete-marker",
        },
        "private_provenance": {"fingerprint": "raw-complete-marker"},
    }


def test_position_projection_is_immutable_minimized_and_preserves_candidate_order() -> None:
    execution = _execution(
        WorkflowV1.POSITION_ANALYSIS,
        _position_document(),
        warnings=("Warning <one> & retained.",),
    )

    presentation = build_result_presentation_v1(execution)

    assert type(presentation) is BrowserSafeResultPresentationV1
    assert tuple(section.title for section in presentation.sections) == RESULT_SECTION_TITLES_V1
    assert presentation.warnings == ("Warning <one> & retained.",)
    alternatives = presentation.sections[2].tables[0]
    assert [row[0] for row in alternatives.rows] == ["H9", "S7"]
    assert alternatives.rows[0][2] == "75.00%"
    serialized_projection = repr(presentation)
    for forbidden in (
        "private_world",
        "private_hand",
        "private_seed",
        "raw-complete-marker",
        "result-input.json",
        "fingerprint",
        "unused-secret",
    ):
        assert forbidden not in serialized_projection
    with pytest.raises(FrozenInstanceError):
        presentation.workflow = "historical_game"  # type: ignore[misc]


def test_position_renderer_has_exact_semantic_sections_escaping_and_downloads() -> None:
    presentation = build_result_presentation_v1(
        _execution(
            WorkflowV1.POSITION_ANALYSIS,
            _position_document(),
            warnings=("Warning <one> & retained.",),
        )
    )

    html = render_result_presentation_v1(
        presentation,
        request_download_available=True,
        result_download_available=True,
    )

    assert html.count("<section ") == 5
    heading_positions = [html.index(f">{title}</h2>") for title in RESULT_SECTION_TITLES_V1]
    assert heading_positions == sorted(heading_positions)
    assert html.count("<h2 ") == 5
    assert "<table>" in html and '<th scope="col">Card</th>' in html
    assert "Prefer H9 over &lt;unsafe &amp; unescaped&gt;." in html
    assert "Warning &lt;one&gt; &amp; retained." in html
    assert "<unsafe" not in html
    assert "<details>" in html
    assert "<details open" not in html
    assert f'href="{ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH}" download' in html
    assert f'href="{ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH}" download' in html
    assert REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH not in html
    assert REVIEW_RESULT_DOWNLOAD_ROUTE_PATH not in html
    assert "partial" in html
    assert "not a perfect-play claim" in html
    assert "not calibrated probability" in html
    assert "analysis cutoff" in html
    assert "fixed public policy" in html
    for forbidden in (
        "private_world",
        "private_hand",
        "raw-complete-marker",
        "result-input.json",
        "fingerprint",
        "field_provenance",
        "unused-secret",
    ):
        assert forbidden not in html


@pytest.mark.parametrize("status", TEXTUAL_NORMAL_RESULT_STATES_V1)
def test_normal_result_states_remain_textual_non_error_states(status: str) -> None:
    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.POSITION_ANALYSIS, _position_document(status=status))
    )

    html = render_result_presentation_v1(presentation)

    assert f"<dd>{status}</dd>" in html
    assert "result-error" not in html
    assert ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH not in html
    assert ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH not in html


def test_historical_projection_covers_outcome_reviews_and_bounded_families() -> None:
    presentation = build_result_presentation_v1(
        _execution(
            WorkflowV1.HISTORICAL_GAME,
            _historical_document(),
            warnings=("Imported ending retained.",),
        )
    )

    summary = {detail.label: detail.value for detail in presentation.sections[0].details}
    assert summary == {
        "Game": "game-<unsafe>",
        "Status": "complete",
        "Players": "Alex, Blair, Rearhand",
        "Declarer": "Blair",
        "Declaration": "clubs",
        "Game end": "party_wide_all_remaining_tricks_claim",
        "Completed Tricks": "2",
        "Declarer points": "72",
        "Defender points": "48",
        "Winner": "declarer",
        "Result": "final",
        "Overbid": "not_overbid",
        "Settlement": "36",
        "Hand game": "Yes",
        "Ouvert": "No",
        "Bid value": "36",
        "Matadors": "2",
        "Immediate review Decisions": "2",
        "Bounded Search review Decisions": "1",
    }
    assert presentation.sections[1].paragraphs == (
        "A completed game has no single whole-game Card recommendation.",
        "Decision reviews remain bounded to their retained public evidence and do not "
        "establish one globally optimal game policy.",
    )
    alternatives = presentation.sections[2].tables
    assert [row[0] for row in alternatives[0].rows] == ["1", "2"]
    assert alternatives[1].rows[0][6] == "timeout"
    evidence = " ".join(presentation.sections[3].items)
    assert "Replay Coaching" in evidence
    assert "Tactical motifs are structural observations" in evidence
    assert "Claim adjudication is limited" in evidence
    assert "no_causal_outcome_claim" in evidence
    assert "private_coaching_secret" not in evidence
    assert "no_hidden_ownership_inference" not in evidence


def test_historical_renderer_escapes_values_and_excludes_raw_result_content() -> None:
    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, _historical_document())
    )

    html = render_result_presentation_v1(
        presentation,
        request_download_available=True,
        result_download_available=True,
    )

    assert html.count("<section ") == 5
    assert "game-&lt;unsafe&gt;" in html
    assert "player-&lt;a&gt;" in html
    assert "A completed game has no single whole-game Card recommendation." in html
    assert html.index('<th scope="row">1</th>') < html.index('<th scope="row">2</th>')
    assert "timeout" in html
    assert REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH in html
    assert REVIEW_RESULT_DOWNLOAD_ROUTE_PATH in html
    assert ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH not in html
    assert ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH not in html
    for forbidden in (
        "raw-complete-marker",
        "private_review",
        "private_snapshot",
        "history.json",
        "fingerprint",
        "field_provenance",
        "representative_line",
        "no_hidden_ownership_inference",
    ):
        assert forbidden not in html


def test_information_set_and_simulation_results_use_retained_public_order() -> None:
    document = _position_document(status="complete")
    document["recommendation_method_summary"] = {
        "requested_method": "information_set_search",
        "effective_method": "bounded_information_set_policy_search_v1",
        "fallback_used": False,
    }
    document["information_set_search_result"] = {
        "status": "complete",
        "candidate_results": [
            {
                "card": "D8",
                "rank": 1,
                "is_recommended": True,
                "completed_world_count": 3,
            },
            {
                "card": "D7",
                "rank": 2,
                "is_recommended": False,
                "completed_world_count": 3,
            },
        ],
    }
    document["multi_step_result"] = {
        "requested_step_count": 2,
        "steps_simulated": 2,
        "stop_reason": "completed",
        "card_selection_policy": "highest_expected_value",
    }
    document["policy_comparison_result"] = {
        "requested_step_count": 2,
        "recommended_policy": {"policy": "highest_expected_value"},
    }

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.POSITION_ANALYSIS, document)
    )

    alternatives = presentation.sections[2].tables[0]
    assert [row[0] for row in alternatives.rows] == ["D8", "D7"]
    technical = {detail.label: detail.value for detail in presentation.sections[4].details}
    assert technical["Multi-Step requested Decisions"] == "2"
    assert technical["Multi-Step simulated Decisions"] == "2"
    assert technical["Recommended comparison Policy"] == "highest_expected_value"


def test_bounded_search_effective_method_uses_search_candidates() -> None:
    document = _position_document(status="complete")
    document["recommendation_method_summary"] = {
        "requested_method": "bounded_search",
        "effective_method": "compatible_world_minimax_v1",
        "fallback_used": False,
    }
    document["bounded_search_result"] = {
        "status": "complete",
        "candidate_results": [
            {
                "card": "D8",
                "rank": 1,
                "is_recommended": True,
                "completed_world_count": 3,
            }
        ],
    }

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.POSITION_ANALYSIS, document)
    )

    assert presentation.sections[2].tables[0].rows[0][0] == "D8"


def test_historical_information_set_coaching_is_separate_bounded_evidence() -> None:
    document = _historical_document()
    summary = document["historical_game_summary"]
    assert isinstance(summary, dict)
    summary["historical_information_set_search_review_summary"] = {
        "review_method": "historical_information_set_search_review_v1",
        "decision_count": 1,
        "status_counts": {"complete": 1, "not_available": 0},
        "selected_world_count_total": 2,
        "sampled_world_count_total": 2,
        "decisions": [
            {
                "decision_index": 1,
                "trick_number": 1,
                "play_index": 1,
                "actual_card": "CA",
                "information_set_search_result": {
                    "recommended_card": "CA",
                    "status": "complete",
                },
                "same_selection_pimc_result": {"recommended_card": "CA"},
                "immediate_baseline": {"recommended_card": "C10"},
                "comparison": {"comparison_status": "available"},
            }
        ],
    }
    summary["historical_information_set_replay_coaching_summary"] = {
        "report_method": "historical_information_set_replay_coaching_v1",
        "limitations": ("complete_candidate_evidence_only",),
    }

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, document)
    )

    assert len(presentation.sections[2].tables) == 3
    evidence = " ".join(presentation.sections[3].items)
    assert "Information-set Coaching uses complete Candidate evidence without fallback." in evidence
    assert "complete_candidate_evidence_only" in evidence
    assert "ground truth" in evidence


@pytest.mark.parametrize(
    "ending",
    (
        "defender_concession",
        "declarer_card_exposure_continuation",
        "impossible_null",
    ),
)
def test_supported_historical_endings_remain_normal_presented_results(ending: str) -> None:
    document = _historical_document()
    summary = document["historical_game_summary"]
    assert isinstance(summary, dict)
    record = summary["record"]
    assert isinstance(record, dict)
    record["game_end_reason"] = ending
    summary["historical_game_end_summary"] = {"kind": ending}

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, document)
    )

    details = {detail.label: detail.value for detail in presentation.sections[0].details}
    assert details["Game end"] == ending
    assert details["Settlement"] == "36"
    assert presentation.sections[1].title == "Recommendation"


def test_safe_error_summary_is_separate_and_escaped() -> None:
    html = render_safe_result_error_summary_v1(
        title="Could not <run>",
        message="Invalid & rejected input.",
    )

    assert "Could not &lt;run&gt;" in html
    assert "Invalid &amp; rejected input." in html
    assert "<run>" not in html
