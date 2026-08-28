import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest
from test_fixed_three_player_historical_list import (
    build_list_input,
    build_one_played_list,
)
from test_historical_game_event_chain import add_continuation
from test_output_schema import OUTPUT_VALIDATOR, build_valid_output
from test_party_wide_claim_contracts import (
    _build_historical_input,
    _party_for_trick_winner,
)
from test_replay_coaching_contracts import (
    _historical_fake_immediate,
    _historical_fake_search,
)
from test_training_dataset import build_training_input

import skatmind.historical_game as historical_game_module
import skatmind.historical_party_wide_claim as adapter_module
import skatmind.party_wide_claim_adjudication as adjudication_module
from skatmind.api.v1 import ExecutionOptionsV1, execute_document, serialize_result
from skatmind.errors import SkatMindInvariantError
from skatmind.fixed_three_player_historical_list import (
    build_fixed_three_player_historical_list,
    build_fixed_three_player_historical_list_entry_facts,
)
from skatmind.fixed_three_player_historical_list_aggregation import (
    build_fixed_three_player_historical_list_aggregation,
)
from skatmind.fixed_three_player_historical_list_comparison import (
    build_fixed_three_player_historical_list_comparison,
)
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_historical_game_summary_from_input,
    build_serializable_historical_record,
)
from skatmind.historical_game_end import (
    HISTORICAL_GAME_END_REASONS,
    HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_VERSION,
    HistoricalPartyWideAllRemainingTricksClaim,
    build_serializable_historical_game_end,
)
from skatmind.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
)
from skatmind.historical_result_provenance import (
    build_historical_game_result_attachment,
)
from skatmind.historical_search_review import (
    build_historical_search_review_coaching_analysis,
)
from skatmind.party_wide_claim_proof_contracts import (
    build_unavailable_party_wide_claim_proof_preparation_v1,
    build_unavailable_party_wide_claim_proof_result_v1,
)
from skatmind.replay_coaching_report import build_replay_coaching_report
from skatmind.replay_coaching_report_context import (
    build_replay_coaching_outcome_context,
)
from skatmind.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skatmind.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLAIM_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_party_wide_claim.json"
NULL_INCOMPLETE_PATH = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "generated_output_schema"
    / "historical_party_wide_claim_defenders_null_incomplete_trick.json"
)


def _load_historical_input(path: Path = CLAIM_EXAMPLE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["historical_game_input"]


def _truncate_raw_tricks(tricks: list[dict], play_count: int) -> list[dict]:
    remaining = play_count
    prefix = []
    for trick in tricks:
        if remaining == 0:
            break
        copied = copy.deepcopy(trick)
        selected_count = min(remaining, len(copied["plays"]))
        copied["plays"] = copied["plays"][:selected_count]
        prefix.append(copied)
        remaining -= selected_count
        if selected_count < 3:
            break
    assert remaining == 0
    return prefix


def _build_claim_input(
    *,
    game_type: str = "grand",
    hand_game: bool = False,
    ouvert: bool = False,
    play_count: int = 27,
    schneider_announced: bool = False,
    schwarz_announced: bool = False,
    bid_value: int = 18,
    declarer_player_id: str = "player-b",
) -> dict:
    data = _build_historical_input(
        game_type=game_type,
        hand_game=hand_game,
        ouvert=ouvert,
        bid_value=bid_value,
        declarer_player_id=declarer_player_id,
    )
    if schneider_announced:
        data["declaration"]["schneider_announced"] = True
    if schwarz_announced:
        data["declaration"]["schwarz_announced"] = True
    complete_record = build_historical_game_record(data)
    claiming_party = _party_for_trick_winner(complete_record, complete_record.tricks[-1])
    claimant_player_id = (
        complete_record.declarer_player_id
        if claiming_party == "declarer"
        else next(
            player.player_id
            for player in complete_record.players
            if player.player_id != complete_record.declarer_player_id
        )
    )
    data["game_id"] = (
        f"historical-claim-{game_type}-{hand_game}-{ouvert}-{play_count}-"
        f"{schneider_announced}-{schwarz_announced}-{bid_value}"
    )
    data["played_at"] = "2026-08-20T18:30:00+02:00"
    data["game_end_reason"] = "party_wide_all_remaining_tricks_claim"
    data["tricks"] = _truncate_raw_tricks(data["tricks"], play_count)
    data["game_end"] = {
        "schema_version": 1,
        "kind": "party_wide_all_remaining_tricks_claim",
        "claimant_player_id": claimant_player_id,
        "claiming_party": claiming_party,
    }
    return data


def _all_nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_nested_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_nested_keys(item) for item in value))
    return set()


def test_historical_claim_contract_policies_serialization_and_round_trip_are_exact() -> None:
    assert HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_VERSION == 1
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_VERSION == 1
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_SUMMARY_VERSION == 1
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_SOURCE_POLICY == (
        "complete_historical_record_and_terminal_claim_event"
    )
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_EXECUTION_POLICY == (
        "replay_prepare_execute_adjudicate_once"
    )
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_VALIDITY_POLICY == (
        "valid_proof_required_for_terminal_historical_record"
    )
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_INVALID_POLICY == (
        "invalid_or_unavailable_proof_rejects_terminal_record"
    )
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_CONTINUATION_POLICY == (
        "one_supported_continuation_before_terminal_claim"
    )
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_OUTPUT_POLICY == (
        "diagnostic_proof_and_adjudication_summary_without_private_state_duplication"
    )
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_DOWNSTREAM_POLICY == (
        "played_prefix_only_decisions_without_terminal_target"
    )
    assert adapter_module.HISTORICAL_PARTY_WIDE_CLAIM_PUBLIC_POLICY == (
        "historical_root_workflow_only_without_flat_shortening"
    )
    assert "party_wide_all_remaining_tricks_claim" in HISTORICAL_GAME_END_REASONS

    record = build_historical_game_record(_load_historical_input())
    assert isinstance(record.game_end, HistoricalPartyWideAllRemainingTricksClaim)
    assert build_serializable_historical_game_end(record.game_end) == {
        "schema_version": 1,
        "kind": "party_wide_all_remaining_tricks_claim",
        "claimant_player_id": "player-b",
        "claiming_party": "declarer",
    }
    serialized = build_serializable_historical_record(record)
    assert build_historical_game_record(serialized) == record
    with pytest.raises(FrozenInstanceError):
        record.game_end.claiming_party = "defenders"


@pytest.mark.parametrize(
    ("field", "value", "error_match"),
    [
        ("schema_version", 2, "schema_version must be exactly 1"),
        ("kind", "defender_concession", "kind must match game_end_reason"),
        ("claimant_player_id", "unknown", "exact stable participant"),
        ("claimant_player_id", "me", "relative player identity"),
        ("claiming_party", "left", "declarer.*defenders"),
    ],
)
def test_historical_claim_rejects_invalid_contract_fields(
    field: str,
    value: object,
    error_match: str,
) -> None:
    data = _load_historical_input()
    data["game_end"][field] = value
    with pytest.raises(ValueError, match=error_match):
        build_historical_game_record(data)


def test_historical_claim_rejects_unknown_missing_and_party_mismatch_fields() -> None:
    unknown = _load_historical_input()
    unknown["game_end"]["proof"] = {"status": "valid"}
    with pytest.raises(ValueError, match="unsupported fields"):
        build_historical_game_record(unknown)

    missing = _load_historical_input()
    missing["game_end"].pop("claiming_party")
    with pytest.raises(ValueError, match="missing required fields"):
        build_historical_game_record(missing)

    declarer_mismatch = _load_historical_input()
    declarer_mismatch["game_end"]["claimant_player_id"] = "player-a"
    with pytest.raises(ValueError, match="Declarer Claim"):
        build_historical_game_record(declarer_mismatch)

    defender_mismatch = _load_historical_input()
    defender_mismatch["game_end"]["claiming_party"] = "defenders"
    with pytest.raises(ValueError, match="Defender Claim"):
        build_historical_game_record(defender_mismatch)


def test_either_exact_defender_can_assert_the_historical_claim() -> None:
    data = _build_claim_input(game_type="clubs")
    assert data["game_end"]["claiming_party"] == "defenders"
    first_claimant = data["game_end"]["claimant_player_id"]
    data["game_end"]["claimant_player_id"] = next(
        player["player_id"]
        for player in data["players"]
        if player["player_id"] not in {data["declarer_player_id"], first_claimant}
    )

    summary = build_historical_game_summary_from_input(data)

    assert (
        summary["historical_game_end_summary"]["claimant_player_id"]
        == (data["game_end"]["claimant_player_id"])
    )
    assert summary["historical_game_end_summary"]["exact_proof"]["status"] == "valid"


def test_historical_claim_reason_and_event_must_match_exactly() -> None:
    missing_event = _load_historical_input()
    missing_event.pop("game_end")
    with pytest.raises(ValueError, match="game_end is required"):
        build_historical_game_record(missing_event)

    normal_with_claim = _load_historical_input()
    normal_with_claim["game_end_reason"] = "normal_completion"
    with pytest.raises(ValueError, match="game_end must be absent"):
        build_historical_game_record(normal_with_claim)

    existing_reason_with_claim = _load_historical_input()
    existing_reason_with_claim["game_end_reason"] = "defender_concession"
    with pytest.raises(ValueError):
        build_historical_game_record(existing_reason_with_claim)

    other_event = _load_historical_input()
    other_event["game_end"] = {
        "schema_version": 1,
        "kind": "defender_concession",
        "conceding_defender_player_id": "player-a",
        "concession_form": "explicit",
    }
    with pytest.raises(ValueError, match="game_end"):
        build_historical_game_record(other_event)


@pytest.mark.parametrize(
    (
        "game_type",
        "hand_game",
        "ouvert",
        "schneider_announced",
        "schwarz_announced",
    ),
    [
        ("clubs", False, False, False, False),
        ("spades", False, False, False, False),
        ("hearts", False, False, False, False),
        ("diamonds", False, False, False, False),
        ("grand", False, False, False, False),
        ("grand", True, False, True, False),
        ("grand", True, False, True, True),
        ("grand", True, True, True, True),
        ("null", False, False, False, False),
        ("null", True, False, False, False),
        ("null", False, True, False, False),
        ("null", True, True, False, False),
    ],
)
def test_historical_claim_supports_all_contract_and_declaration_families(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
    schneider_announced: bool,
    schwarz_announced: bool,
) -> None:
    summary = build_historical_game_summary_from_input(
        _build_claim_input(
            game_type=game_type,
            hand_game=hand_game,
            ouvert=ouvert,
            schneider_announced=schneider_announced,
            schwarz_announced=schwarz_announced,
        )
    )

    assert summary["status"] == "complete"
    assert summary["historical_game_end_summary"]["exact_proof"]["status"] == "valid"
    assert summary["historical_game_end_summary"]["adjudication"]["status"] == ("adjudicated")
    assert summary["declarer_points"] + summary["defender_points"] == 120
    assert summary["game_result_summary"]["is_complete"] is True
    assert summary["final_settlement_summary"]["is_complete"] is True
    if game_type == "null":
        assert summary["schneider_status"] == "not_applicable"
        assert summary["schwarz_status"] == "not_applicable"


def test_historical_claim_preserves_supported_suit_grand_overbid_and_null_boundary() -> None:
    supported = build_historical_game_summary_from_input(
        _build_claim_input(game_type="grand", hand_game=True, bid_value=72)
    )
    assert supported["overbid_summary"]["bid_value"] == 72
    assert supported["final_settlement_summary"]["is_complete"] is True

    impossible_null = _build_claim_input(game_type="null", bid_value=48)
    with pytest.raises(ValueError, match="party_wide_claim_unsupported_contract"):
        build_historical_game_summary_from_input(impossible_null)


@pytest.mark.parametrize(
    ("game_type", "declarer_player_id", "decision_state", "claiming_party", "winner"),
    [
        ("clubs", "player-a", "declarer_already_won", "defenders", "declarer"),
        ("hearts", "player-b", "defenders_already_won", "declarer", "defenders"),
        ("diamonds", "player-c", "undecided", "declarer", "declarer"),
    ],
)
def test_historical_claim_preserves_preexisting_winners_or_uses_completed_assignment(
    game_type: str,
    declarer_player_id: str,
    decision_state: str,
    claiming_party: str,
    winner: str,
) -> None:
    summary = build_historical_game_summary_from_input(
        _build_claim_input(
            game_type=game_type,
            declarer_player_id=declarer_player_id,
        )
    )
    end = summary["historical_game_end_summary"]

    assert end["adjudication"]["decision_state_before_claim"] == decision_state
    assert end["claiming_party"] == claiming_party
    assert summary["winner"] == winner


@pytest.mark.parametrize(("play_count", "current_card_count"), [(27, 0), (28, 1), (29, 2)])
def test_historical_claim_supports_zero_one_or_two_current_trick_cards_once(
    play_count: int,
    current_card_count: int,
) -> None:
    data = _build_claim_input(play_count=play_count)
    summary = build_historical_game_summary_from_input(data)
    end = summary["historical_game_end_summary"]
    line = end["exact_proof"]["representative_line"]

    assert end["event_during_incomplete_trick"] is (current_card_count > 0)
    assert summary["play_prefix_summary"]["current_trick_card_count"] == current_card_count
    assert end["exact_proof"]["assignment"]["assigned_trick_count"] == 1
    assert (
        end["adjudication"]["final_declarer_tricks"] + end["adjudication"]["final_defender_tricks"]
        == 10
    )
    current_cards = (
        {play["card"] for play in data["tricks"][-1]["plays"]} if current_card_count else set()
    )
    assert current_cards.isdisjoint(move["card"] for move in line)
    assert len(line) + current_card_count == 3


def test_historical_claim_output_is_complete_strict_and_privacy_bounded() -> None:
    root = {
        "input_file": "historical_party_wide_claim.json",
        "historical_game_summary": build_historical_game_summary_from_input(
            _load_historical_input()
        ),
    }
    summary = root["historical_game_summary"]
    end = summary["historical_game_end_summary"]
    adjudication = end["adjudication"]

    assert list(OUTPUT_VALIDATOR.iter_errors(root)) == []
    assert summary["record"] == build_serializable_historical_record(
        build_historical_game_record(_load_historical_input())
    )
    assert len(summary["derived_tricks"]) == 5
    assert summary["point_accounting"]["total_card_points"] == 120
    assert summary["point_accounting"]["final_declarer_points"] == summary["declarer_points"]
    assert summary["point_accounting"]["final_defender_points"] == summary["defender_points"]
    assert end["normative_matrix_case_id"] == (
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
    )
    assert end["exact_proof"]["representative_line_scope"] == ("diagnostic_decisive_branch_only")
    assert adjudication["reason"] == "valid_proof"
    assert adjudication["adjudicated_winner"] == summary["winner"]
    assert not {
        "exact_state",
        "hands",
        "hidden_world",
        "memo_table",
        "proof_tree",
        "universal_branch_tree",
    }.intersection(_all_nested_keys(end))


def test_historical_claim_rejects_invalid_and_unavailable_without_fallback() -> None:
    invalid = _load_historical_input()
    invalid["game_end"] = {
        "schema_version": 1,
        "kind": "party_wide_all_remaining_tricks_claim",
        "claimant_player_id": "player-a",
        "claiming_party": "defenders",
    }
    with pytest.raises(ValueError, match="party-wide Claim proof is invalid"):
        build_historical_game_summary_from_input(invalid)

    six_unresolved = _build_claim_input(play_count=12)
    with pytest.raises(
        ValueError,
        match="party_wide_claim_unresolved_trick_limit_exceeded",
    ):
        build_historical_game_summary_from_input(six_unresolved)

    no_unresolved = _build_claim_input(play_count=30)
    with pytest.raises(ValueError, match="party_wide_claim_no_unresolved_tricks"):
        build_historical_game_summary_from_input(no_unresolved)


def test_historical_claim_rejects_nonfinal_incomplete_trick() -> None:
    data = _build_claim_input(play_count=27)
    data["tricks"][0]["plays"] = data["tricks"][0]["plays"][:2]
    with pytest.raises(ValueError, match="only the final historical trick may be incomplete"):
        build_historical_game_summary_from_input(data)


def test_retained_claim_replay_must_match_exact_historical_record() -> None:
    record = build_historical_game_record(_load_historical_input())
    other_record = build_historical_game_record(_build_claim_input())
    other_replay = historical_game_module.replay_historical_play_prefix(other_record)

    with pytest.raises(ValueError, match="does not match its Historical record"):
        adapter_module.build_party_wide_claim_evidence_from_historical_replay_v1(
            record,
            other_replay,
        )


def test_valid_historical_claim_executes_every_pipeline_stage_and_settlement_once() -> None:
    data = _load_historical_input()
    with (
        patch.object(
            historical_game_module,
            "replay_historical_play_prefix",
            wraps=historical_game_module.replay_historical_play_prefix,
        ) as replay,
        patch.object(
            adapter_module,
            "build_party_wide_all_remaining_tricks_claim_v1",
            wraps=adapter_module.build_party_wide_all_remaining_tricks_claim_v1,
        ) as claim_builder,
        patch.object(
            adapter_module,
            "build_party_wide_claim_evidence_from_historical_replay_v1",
            wraps=adapter_module.build_party_wide_claim_evidence_from_historical_replay_v1,
        ) as evidence_builder,
        patch.object(
            adapter_module,
            "prepare_party_wide_claim_proof_request_v1",
            wraps=adapter_module.prepare_party_wide_claim_proof_request_v1,
        ) as prepare,
        patch.object(
            adapter_module,
            "execute_party_wide_claim_proof_v1",
            wraps=adapter_module.execute_party_wide_claim_proof_v1,
        ) as execute,
        patch.object(
            adapter_module,
            "adjudicate_party_wide_claim_proof_v1",
            wraps=adapter_module.adjudicate_party_wide_claim_proof_v1,
        ) as adjudicate,
        patch.object(
            adjudication_module,
            "build_final_settlement_summary",
            wraps=adjudication_module.build_final_settlement_summary,
        ) as settlement,
    ):
        result = execute_document(
            {"historical_game_input": data},
            options=ExecutionOptionsV1(include_provenance=True, validate_output=True),
            input_reference="historical-party-wide-claim.json",
        )

    assert result.field_provenance is not None
    assert replay.call_count == 1
    assert claim_builder.call_count == 1
    assert evidence_builder.call_count == 1
    assert prepare.call_count == 1
    assert execute.call_count == 1
    assert adjudicate.call_count == 1
    assert settlement.call_count == 1


def test_continuation_claim_summary_reuses_one_full_prefix_replay() -> None:
    data = add_continuation(
        _build_claim_input(),
        "defender_open_play_continuation",
    )
    record = build_historical_game_record(data)
    with patch.object(
        historical_game_module,
        "replay_historical_play_prefix",
        wraps=historical_game_module.replay_historical_play_prefix,
    ) as replay:
        summary = build_historical_game_summary(record)

    assert replay.call_count == 1
    assert summary["historical_game_events_summary"]["event_count"] == 1

    with patch.object(
        historical_game_module,
        "replay_historical_play_prefix",
        wraps=historical_game_module.replay_historical_play_prefix,
    ) as workflow_replay:
        execute_document(
            {"historical_game_input": data},
            options=ExecutionOptionsV1(validate_output=True),
            input_reference="claim-chain.json",
        )

    assert workflow_replay.call_count == 1


def test_unavailable_preparation_skips_executor_adjudicator_and_settlement() -> None:
    data = _build_claim_input(play_count=30)
    with (
        patch.object(
            adapter_module,
            "prepare_party_wide_claim_proof_request_v1",
            wraps=adapter_module.prepare_party_wide_claim_proof_request_v1,
        ) as prepare,
        patch.object(adapter_module, "execute_party_wide_claim_proof_v1") as execute,
        patch.object(adapter_module, "adjudicate_party_wide_claim_proof_v1") as adjudicate,
        patch.object(adjudication_module, "build_final_settlement_summary") as settlement,
    ):
        with pytest.raises(ValueError, match="party_wide_claim_no_unresolved_tricks"):
            build_historical_game_summary_from_input(data)

    assert prepare.call_count == 1
    execute.assert_not_called()
    adjudicate.assert_not_called()
    settlement.assert_not_called()


@pytest.mark.parametrize(
    "reason",
    [
        "party_wide_claim_unsupported_turn_phase",
        "party_wide_claim_evidence_incomplete",
        "party_wide_claim_evidence_contradictory",
    ],
)
def test_historical_adapter_preserves_every_remaining_unavailable_reason_without_execution(
    reason: str,
) -> None:
    data = _build_claim_input()
    record = build_historical_game_record(data)
    replay = historical_game_module.replay_historical_play_prefix(record)
    evidence = adapter_module.build_party_wide_claim_evidence_from_historical_replay_v1(
        record,
        replay,
    )
    claim = adapter_module.build_party_wide_all_remaining_tricks_claim_v1(
        claimant_player_id=record.game_end.claimant_player_id,
        claiming_party=record.game_end.claiming_party,
    )
    preparation = build_unavailable_party_wide_claim_proof_preparation_v1(
        claim=claim,
        unavailable_reason=reason,
        evidence=(
            None
            if reason
            in {
                "party_wide_claim_evidence_incomplete",
                "party_wide_claim_evidence_contradictory",
            }
            else evidence
        ),
    )
    with (
        patch.object(
            adapter_module,
            "prepare_party_wide_claim_proof_request_v1",
            return_value=preparation,
        ),
        patch.object(adapter_module, "execute_party_wide_claim_proof_v1") as execute,
        patch.object(adapter_module, "adjudicate_party_wide_claim_proof_v1") as adjudicate,
        pytest.raises(ValueError, match=reason),
    ):
        build_historical_game_summary(record)

    execute.assert_not_called()
    adjudicate.assert_not_called()


def test_invalid_proof_skips_adjudicator_and_settlement() -> None:
    data = _load_historical_input()
    data["game_end"] = {
        "schema_version": 1,
        "kind": "party_wide_all_remaining_tricks_claim",
        "claimant_player_id": "player-a",
        "claiming_party": "defenders",
    }
    with (
        patch.object(
            adapter_module,
            "execute_party_wide_claim_proof_v1",
            wraps=adapter_module.execute_party_wide_claim_proof_v1,
        ) as execute,
        patch.object(adapter_module, "adjudicate_party_wide_claim_proof_v1") as adjudicate,
        patch.object(adjudication_module, "build_final_settlement_summary") as settlement,
    ):
        with pytest.raises(ValueError, match="party-wide Claim proof is invalid"):
            build_historical_game_summary_from_input(data)

    assert execute.call_count == 1
    adjudicate.assert_not_called()
    settlement.assert_not_called()


def test_unexpected_executor_and_adjudicator_states_are_invariant_errors() -> None:
    data = _build_claim_input()
    record = build_historical_game_record(data)
    replay = historical_game_module.replay_historical_play_prefix(record)
    evidence = adapter_module.build_party_wide_claim_evidence_from_historical_replay_v1(
        record, replay
    )
    claim = adapter_module.build_party_wide_all_remaining_tricks_claim_v1(
        claimant_player_id=record.game_end.claimant_player_id,
        claiming_party=record.game_end.claiming_party,
    )
    preparation = adapter_module.prepare_party_wide_claim_proof_request_v1(claim, evidence)
    unavailable_proof = build_unavailable_party_wide_claim_proof_result_v1(
        preparation=preparation,
        unavailable_reason="party_wide_claim_proof_not_executed",
    )
    with (
        patch.object(
            adapter_module,
            "execute_party_wide_claim_proof_v1",
            return_value=unavailable_proof,
        ),
        pytest.raises(SkatMindInvariantError, match="did not return a complete Result"),
    ):
        build_historical_game_summary(record)


@pytest.mark.parametrize(
    "continuation_kind",
    ["declarer_card_exposure_continuation", "defender_open_play_continuation"],
)
def test_one_supported_continuation_can_precede_terminal_claim(
    continuation_kind: str,
) -> None:
    data = add_continuation(_build_claim_input(), continuation_kind)
    summary = build_historical_game_summary_from_input(data)
    event = summary["historical_game_events_summary"]["events"][0]

    assert event["kind"] == continuation_kind
    assert event["final_game_end_reason"] == "party_wide_all_remaining_tricks_claim"
    assert event["final_outcome_source"] == "subsequent_terminal_shortening"
    assert event["game_end_applied"] is False
    assert event["settlement_applied"] is False
    assert summary["historical_game_end_summary"]["event_after_play_count"] == 27


def test_claim_snapshots_training_lists_and_statistics_use_played_cards_only() -> None:
    data = _load_historical_input()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)
    assert snapshots.snapshot_count == 15
    assert [snapshot.decision_index for snapshot in snapshots.snapshots] == list(range(1, 16))
    assert "exact_proof" not in repr(snapshots.snapshots)

    dataset_input = build_training_dataset_input(build_training_input([data]))
    dataset = build_training_dataset_summary(dataset_input)
    assert dataset["target"] == "actual_card_played"
    assert dataset["sample_count"] == 15
    assert dataset["records"][0]["sample_count"] == 15

    historical_list = build_one_played_list(data)
    fact = build_fixed_three_player_historical_list_entry_facts(historical_list)[0]
    assert fact.game_end_reason == "party_wide_all_remaining_tricks_claim"
    assert fact.settlement_score == summary["final_settlement_summary"]["settlement_score"]

    aggregation = aggregate_historical_opponent_statistics(dataset_input)
    assert aggregation.source_record_count == 1

    first_aggregation = build_fixed_three_player_historical_list_aggregation(historical_list)
    second_data = build_list_input(played_games={1: data})
    second_data["list_id"] = "list-002"
    second_data["entries"][0]["historical_game"]["game_id"] = "claim-list-game-002"
    second_list = build_fixed_three_player_historical_list(second_data)
    second_aggregation = build_fixed_three_player_historical_list_aggregation(second_list)
    comparison = build_fixed_three_player_historical_list_comparison(
        (first_aggregation, second_aggregation)
    )
    assert first_aggregation.played_game_count == 1
    assert comparison.list_count == 2

    later = copy.deepcopy(data)
    later["played_at"] = "2026-08-21T18:30:00+02:00"
    rolling_input = build_training_dataset_input(
        build_training_input([data, later], ["train", "validation"])
    )
    rolling = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(rolling_input)
    )
    assert rolling["selection"]["source_record_count"] == 1
    assert rolling["selection"]["target_record_count"] == 1
    assert rolling["selection"]["target_decision_count"] == 15


def test_claim_replay_coaching_uses_retained_settlement_without_rerunning_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _load_historical_input()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    coaching = build_historical_search_review_coaching_analysis(
        snapshots,
        record,
        41,
        immediate_sample_count=1,
    )

    with (
        patch(
            "skatmind.replay_coaching_report.build_historical_game_summary",
            wraps=build_historical_game_summary,
        ) as summary_builder,
        patch.object(
            adapter_module,
            "execute_party_wide_claim_proof_v1",
            wraps=adapter_module.execute_party_wide_claim_proof_v1,
        ) as execute,
    ):
        report = build_replay_coaching_report(record, coaching)

    assert summary_builder.call_count == 1
    assert execute.call_count == 1
    assert report.outcome_context.game_end_reason == ("party_wide_all_remaining_tricks_claim")
    assert report.outcome_context.final_settlement_summary["is_complete"] is True
    assert report.outcome_context.historical_game_end_summary["kind"] == (
        "party_wide_all_remaining_tricks_claim"
    )


def test_public_historical_reviews_and_coaching_support_claim_game(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _historical_fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    with (
        patch.object(
            historical_game_module,
            "replay_historical_play_prefix",
            wraps=historical_game_module.replay_historical_play_prefix,
        ) as replay,
        patch.object(
            adapter_module,
            "execute_party_wide_claim_proof_v1",
            wraps=adapter_module.execute_party_wide_claim_proof_v1,
        ) as proof,
        patch.object(
            adapter_module,
            "adjudicate_party_wide_claim_proof_v1",
            wraps=adapter_module.adjudicate_party_wide_claim_proof_v1,
        ) as adjudicate,
    ):
        result_document = serialize_result(
            execute_document(
                {"historical_game_input": _load_historical_input()},
                options=ExecutionOptionsV1(
                    validate_output=True,
                    include_provenance=True,
                    workflow_options={
                        "decision_snapshots": True,
                        "immediate_review": True,
                        "search_review": True,
                        "replay_coaching": True,
                        "search_seed": 41,
                        "immediate_sample_count": 1,
                    },
                ),
                input_reference="claim.json",
            )
        )["document"]

    result = result_document["historical_game_summary"]

    assert result["decision_snapshot_summary"]["snapshot_count"] == 15
    assert len(result["historical_game_review_summary"]["decisions"]) == 15
    assert len(result["historical_search_review_summary"]["decisions"]) == 15
    coaching = result["historical_replay_coaching_summary"]
    assert coaching["outcome_context"]["game_end_reason"] == (
        "party_wide_all_remaining_tricks_claim"
    )
    assert coaching["outcome_context"]["final_settlement_summary"]["is_complete"] is True
    assert "exact_proof" not in json.dumps(coaching["decision_assessments"])
    assert replay.call_count == 1
    assert proof.call_count == 1
    assert adjudicate.call_count == 1
    review_entries = {
        entry["field_path"]: entry
        for entry in result_document["field_provenance"]["result"]["ledger"]["entries"]
    }
    outcome_settlement = review_entries[
        "/historical_game_summary/historical_replay_coaching_summary/"
        "outcome_context/final_settlement_summary/settlement_score"
    ]
    assert outcome_settlement["dependency_paths"] == [
        "/historical_game_summary/final_settlement_summary/settlement_score"
    ]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("final_settlement_summary", "settlement_score"), 34),
        (("game_result_summary", "claimant_player_id"), "player-a"),
        (("game_result_summary", "claiming_party"), "defenders"),
        (("game_result_summary", "game_end_kind"), "declarer_concession"),
        (("game_result_summary", "party_wide_claim_proof_status"), "invalid"),
    ],
)
def test_replay_coaching_rejects_modified_retained_claim_outcome(
    path: tuple[str, str],
    value: object,
) -> None:
    data = _load_historical_input()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    changed = copy.deepcopy(summary)
    changed[path[0]][path[1]] = value

    with pytest.raises(ValueError, match="reconcile"):
        build_replay_coaching_outcome_context(record, changed)


def test_claim_public_provenance_is_complete_causal_and_redacted() -> None:
    document = {"historical_game_input": _load_historical_input()}
    default = serialize_result(
        execute_document(
            document,
            options=ExecutionOptionsV1(validate_output=True),
            input_reference="claim.json",
        )
    )["document"]
    with_provenance = serialize_result(
        execute_document(
            document,
            options=ExecutionOptionsV1(validate_output=True, include_provenance=True),
            input_reference="claim.json",
        )
    )["document"]
    provenance = with_provenance.pop("field_provenance")
    assert with_provenance == default
    assert provenance["result"]["coverage_summary"]["provenance_complete"] is True
    entries = {entry["field_path"]: entry for entry in provenance["result"]["ledger"]["entries"]}
    claimant = entries["/historical_game_summary/historical_game_end_summary/claimant_player_id"]
    proof = entries["/historical_game_summary/historical_game_end_summary/exact_proof/status"]
    adjudication = entries[
        "/historical_game_summary/historical_game_end_summary/adjudication/status"
    ]
    prefix = entries["/historical_game_summary/play_prefix_summary/played_card_count"]
    assert claimant["origin"] == "validated_copy"
    assert claimant["dependency_paths"] == [
        "/historical_game_summary/record/game_end/claimant_player_id"
    ]
    assert any(
        reference["reference_id"] == "party_wide_all_remaining_tricks_exact_and_or_v1"
        for reference in proof["source_references"]
    )
    assert any(path.endswith("/initial_hand/0") for path in proof["dependency_paths"])
    assert any("/exact_proof/assignment/" in path for path in adjudication["dependency_paths"])
    assert all(
        "party_wide_claim" not in reference["reference_id"]
        for reference in prefix["source_references"]
    )
    serialized_provenance = json.dumps(provenance)
    assert "party_wide_claim_complete_world_evidence_v1" not in serialized_provenance
    assert "party_wide_claim_exact_state_v1" not in serialized_provenance

    internal = build_historical_game_result_attachment(
        default,
        source_document=document,
        external_reference="claim.json",
    )
    internal_entries = {entry.field_path: entry for entry in internal.ledger.entries}
    internal_proof = internal_entries[
        "/historical_game_summary/historical_game_end_summary/exact_proof/status"
    ]
    internal_line = internal_entries[
        "/historical_game_summary/historical_game_end_summary/exact_proof/representative_line/0/card"
    ]
    assert internal_line.visibility == "post_game_only"
    assert {reference.reference_id for reference in internal_proof.source_references}.issuperset(
        {
            "party_wide_claim_complete_world_evidence_v1",
            "party_wide_claim_exact_state_v1",
        }
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("game_end_reason", "party_wide_all_remaining_tricks_claim"),
        ("game_end_kind", "party_wide_all_remaining_tricks_claim"),
        ("outcome_source", "exact_party_wide_claim_adjudication"),
        ("winner_basis", "completed_claim_assignment"),
        ("party_wide_claim_proof_status", "valid"),
        ("claimant_player_id", "player-b"),
        ("claiming_party", "declarer"),
        (
            "rest_trick_assignment",
            {
                "source": "party_wide_claim_proof_assignment",
                "recipient": "declarer",
                "remaining_trick_count": 1,
                "assigned_card_count": 3,
                "assigned_card_points": 10,
            },
        ),
    ],
)
def test_flat_position_output_schema_rejects_all_historical_only_claim_semantics(
    field: str,
    value: object,
) -> None:
    output = build_valid_output()
    output["adjusted_game_result_summary"][field] = value
    assert list(OUTPUT_VALIDATOR.iter_errors(output))


def test_historical_claim_output_schema_binds_exact_claim_game_result() -> None:
    output = {
        "input_file": "historical_party_wide_claim.json",
        "historical_game_summary": build_historical_game_summary_from_input(
            _load_historical_input()
        ),
    }
    assert list(OUTPUT_VALIDATOR.iter_errors(output)) == []

    wrong_reason = copy.deepcopy(output)
    wrong_reason["historical_game_summary"]["game_result_summary"]["game_end_reason"] = (
        "declarer_concession"
    )
    assert list(OUTPUT_VALIDATOR.iter_errors(wrong_reason))

    missing_proof = copy.deepcopy(output)
    missing_proof["historical_game_summary"]["game_result_summary"].pop(
        "party_wide_claim_proof_status"
    )
    assert list(OUTPUT_VALIDATOR.iter_errors(missing_proof))

    preexisting = {
        "input_file": "historical_party_wide_claim.json",
        "historical_game_summary": build_historical_game_summary_from_input(
            _build_claim_input(game_type="clubs", declarer_player_id="player-a")
        ),
    }
    assert (
        preexisting["historical_game_summary"]["game_result_summary"]["outcome_source"]
        == "preexisting_game_decision"
    )
    assert list(OUTPUT_VALIDATOR.iter_errors(preexisting)) == []
