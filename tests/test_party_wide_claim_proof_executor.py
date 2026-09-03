import ast
import copy
import inspect
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import get_args

import pytest
from test_exact_rest_trick_proof import build_one_trick_state
from test_historical_game import build_historical_input
from test_party_wide_claim_contracts import (
    SESSION_EXAMPLE_NAMES,
    _build_evidence,
    _claim_for_party,
    _party_for_trick_winner,
    _prefix_tricks,
)

import skatmind
import skatmind.api.v1 as api_v1
import skatmind.party_wide_claim_evidence as evidence_module
import skatmind.party_wide_claim_proof_contracts as proof_contracts_module
import skatmind.party_wide_claim_proof_executor as executor_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skatmind.api.v1 import WorkflowV1
from skatmind.errors import SkatMindInvariantError
from skatmind.game_end import VALID_GAME_END_REASONS
from skatmind.game_shortening import GameShortening
from skatmind.historical_game import build_historical_game_record
from skatmind.historical_game_end import HISTORICAL_GAME_END_REASONS
from skatmind.historical_game_event import HistoricalGameEvent
from skatmind.party_wide_claim_contracts import (
    build_party_wide_all_remaining_tricks_claim_v1,
)
from skatmind.party_wide_claim_proof_contracts import (
    PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS,
    PartyWideClaimProofMoveV1,
    build_unavailable_party_wide_claim_proof_preparation_v1,
    prepare_party_wide_claim_proof_request_v1,
)
from skatmind.party_wide_claim_proof_executor import (
    PARTY_WIDE_CLAIM_PROOF_ACTOR_POLICY,
    PARTY_WIDE_CLAIM_PROOF_COMPLETION_POLICY,
    PARTY_WIDE_CLAIM_PROOF_COUNTER_POLICY,
    PARTY_WIDE_CLAIM_PROOF_EXECUTION_METHOD,
    PARTY_WIDE_CLAIM_PROOF_EXECUTION_POLICY,
    PARTY_WIDE_CLAIM_PROOF_EXECUTOR_VERSION,
    PARTY_WIDE_CLAIM_PROOF_LINE_POLICY,
    PARTY_WIDE_CLAIM_PROOF_MEMOIZATION_POLICY,
    PARTY_WIDE_CLAIM_PROOF_MOVE_ORDER_POLICY,
    PARTY_WIDE_CLAIM_PROOF_TERMINAL_POLICY,
    execute_party_wide_claim_proof_v1,
)
from skatmind.settlement_normative_matrix import (
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1,
    SETTLEMENT_NORMATIVE_MATRIX_VERSION,
    SUPPORTED_AS_IS,
    get_normative_settlement_case,
    get_normative_settlement_cases,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_PATH = PROJECT_ROOT / "src" / "skatmind" / "party_wide_claim_proof_executor.py"

DECLARER_MIXED_DECK = (
    "CQ",
    "C7",
    "D9",
    "HJ",
    "HQ",
    "C9",
    "CA",
    "SK",
    "S8",
    "DK",
    "H10",
    "H9",
    "DQ",
    "H7",
    "CK",
    "H8",
    "CJ",
    "D10",
    "C8",
    "HK",
    "SQ",
    "D8",
    "S10",
    "SJ",
    "S7",
    "HA",
    "SA",
    "C10",
    "S9",
    "DJ",
    "D7",
    "DA",
)
NONCLAIMANT_DEFENDER_MIXED_DECK = (
    "DK",
    "H10",
    "SQ",
    "SK",
    "DJ",
    "C10",
    "C9",
    "CJ",
    "C7",
    "HA",
    "S10",
    "HQ",
    "D8",
    "S9",
    "H8",
    "CA",
    "H9",
    "D9",
    "C8",
    "SJ",
    "HJ",
    "H7",
    "S8",
    "S7",
    "CQ",
    "D7",
    "CK",
    "DA",
    "D10",
    "DQ",
    "HK",
    "SA",
)
OPPOSING_DEFENDER_MIXED_DECK = (
    "HQ",
    "C8",
    "S10",
    "HJ",
    "DA",
    "H8",
    "DQ",
    "C10",
    "SK",
    "DJ",
    "CQ",
    "S9",
    "CK",
    "C9",
    "HK",
    "D10",
    "H7",
    "H10",
    "C7",
    "S8",
    "D7",
    "S7",
    "DK",
    "CA",
    "SJ",
    "CJ",
    "SQ",
    "D9",
    "HA",
    "H9",
    "SA",
    "D8",
)
OPPOSING_DEFENDER_ALL_SUCCESS_DECK = (
    "SA",
    "C9",
    "HQ",
    "HJ",
    "DK",
    "S9",
    "C8",
    "SK",
    "H8",
    "D9",
    "S8",
    "HK",
    "DJ",
    "H9",
    "D10",
    "SQ",
    "HA",
    "C7",
    "C10",
    "D8",
    "H10",
    "DQ",
    "CA",
    "DA",
    "CK",
    "CJ",
    "D7",
    "SJ",
    "H7",
    "CQ",
    "S10",
    "S7",
)


def _preparation_from_deck(
    deck: tuple[str, ...],
    *,
    declarer_player_id: str,
    claiming_party: str,
    claimant_player_id: str,
):
    record = build_historical_game_record(
        build_historical_input(
            game_type="grand",
            hand_game=False,
            declarer_player_id=declarer_player_id,
            bid_value=18,
            deck=list(deck),
        )
    )
    evidence = evidence_module.build_party_wide_claim_evidence_v1(
        game_id=record.game_id,
        players=record.players,
        skat=record.skat,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        discarded_cards=record.discarded_cards,
        tricks=_prefix_tricks(record.tricks, 24),
    )
    claim = build_party_wide_all_remaining_tricks_claim_v1(
        claimant_player_id=claimant_player_id,
        claiming_party=claiming_party,
    )
    return prepare_party_wide_claim_proof_request_v1(claim, evidence)


def _runtime_union_kinds(union_alias) -> set[str]:
    kinds = set()
    for member in get_args(union_alias.__value__):
        module = __import__(member.__module__, fromlist=[member.__name__])
        kinds.update(
            value
            for name, value in vars(module).items()
            if name.endswith("_KIND") and isinstance(value, str)
        )
    return kinds


def test_executor_metadata_and_policies_are_exact() -> None:
    assert PARTY_WIDE_CLAIM_PROOF_EXECUTOR_VERSION == 1
    assert PARTY_WIDE_CLAIM_PROOF_EXECUTION_METHOD == (
        "party_wide_all_remaining_tricks_exact_and_or_v1"
    )
    assert (
        PARTY_WIDE_CLAIM_PROOF_EXECUTION_POLICY,
        PARTY_WIDE_CLAIM_PROOF_ACTOR_POLICY,
        PARTY_WIDE_CLAIM_PROOF_MOVE_ORDER_POLICY,
        PARTY_WIDE_CLAIM_PROOF_MEMOIZATION_POLICY,
        PARTY_WIDE_CLAIM_PROOF_TERMINAL_POLICY,
        PARTY_WIDE_CLAIM_PROOF_LINE_POLICY,
        PARTY_WIDE_CLAIM_PROOF_COUNTER_POLICY,
        PARTY_WIDE_CLAIM_PROOF_COMPLETION_POLICY,
    ) == (
        "exhaustive_complete_world_and_or_proof",
        "claiming_party_existential_opposing_party_universal",
        "canonical_legal_card_order",
        "exact_state_outcome_and_representative_suffix",
        "opposing_trick_invalidates_otherwise_normal_completion_validates",
        "first_canonical_decisive_branch",
        "unique_uncached_exact_states_and_proof_terminal_states",
        "complete_without_partial_timeout_or_budget",
    )


@pytest.mark.parametrize("reason", PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS)
def test_unavailable_preparation_passes_through_without_execution(reason: str, monkeypatch) -> None:
    evidence, _ = _build_evidence(play_count=27)
    claim = _claim_for_party(evidence, "declarer")
    preparation = build_unavailable_party_wide_claim_proof_preparation_v1(
        claim=claim,
        unavailable_reason=reason,
        evidence=(None if reason in PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS[:2] else evidence),
    )

    def unexpected(*_args, **_kwargs):
        pytest.fail("Unavailable proof execution performed forbidden work.")

    for name in (
        "build_party_wide_claim_proof_request_v1",
        "get_exact_search_legal_cards",
        "apply_exact_search_card",
        "build_party_wide_claim_proof_assignment_v1",
    ):
        monkeypatch.setattr(executor_module, name, unexpected)

    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "unavailable"
    assert result.preparation is preparation
    assert result.unavailable_reason == reason
    assert result.proof_complete is False
    assert result.claim_satisfied is None
    assert result.representative_line == ()
    assert (result.evaluated_state_count, result.memoized_state_count) == (0, 0)
    assert result.terminal_state_count == 0


def test_executor_rejects_non_preparation_and_forged_available_values() -> None:
    with pytest.raises(ValueError, match="PartyWideClaimProofPreparationV1"):
        execute_party_wide_claim_proof_v1("available")  # type: ignore[arg-type]

    evidence, _ = _build_evidence(play_count=24)
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, "defenders"), evidence
    )
    wrong_version = copy.copy(preparation)
    object.__setattr__(wrong_version, "party_wide_claim_proof_preparation_version", 2)
    with pytest.raises(SkatMindInvariantError):
        execute_party_wide_claim_proof_v1(wrong_version)

    forged_request = copy.copy(preparation.request)
    object.__setattr__(forged_request, "proof_policy", "compatible_world_minimax_v1")
    mismatched_request = copy.copy(preparation)
    object.__setattr__(mismatched_request, "request", forged_request)
    with pytest.raises(SkatMindInvariantError, match="canonical rebuild"):
        execute_party_wide_claim_proof_v1(mismatched_request)

    forged_context = copy.copy(preparation.request.exact_state_context)
    object.__setattr__(forged_context, "claiming_party_flat_players", ("left",))
    context_request = copy.copy(preparation.request)
    object.__setattr__(context_request, "exact_state_context", forged_context)
    mismatched_context = copy.copy(preparation)
    object.__setattr__(mismatched_context, "request", context_request)
    with pytest.raises(SkatMindInvariantError):
        execute_party_wide_claim_proof_v1(mismatched_context)

    for field_name, field_value in (
        ("status", "pending"),
        ("unavailable_reason", "party_wide_claim_proof_not_executed"),
        ("evidence", None),
        ("request", None),
    ):
        forged = copy.copy(preparation)
        object.__setattr__(forged, field_name, field_value)
        with pytest.raises(SkatMindInvariantError):
            execute_party_wide_claim_proof_v1(forged)

    for field_name, field_value in (
        ("proof_quantifiers", (("claiming_party", "universal"),)),
        ("maximum_unresolved_tricks", 4),
    ):
        forged_request = copy.copy(preparation.request)
        object.__setattr__(forged_request, field_name, field_value)
        forged = copy.copy(preparation)
        object.__setattr__(forged, "request", forged_request)
        with pytest.raises(SkatMindInvariantError, match="canonical rebuild"):
            execute_party_wide_claim_proof_v1(forged)

    changed_claim = copy.copy(preparation.claim)
    other_defender = next(
        player.player_id
        for player in evidence.players
        if player.player_id
        not in {evidence.declarer_player_id, preparation.claim.claimant_player_id}
    )
    object.__setattr__(changed_claim, "claimant_player_id", other_defender)
    claim_mismatch = copy.copy(preparation)
    object.__setattr__(claim_mismatch, "claim", changed_claim)
    with pytest.raises(SkatMindInvariantError):
        execute_party_wide_claim_proof_v1(claim_mismatch)

    changed_evidence = copy.copy(evidence)
    object.__setattr__(changed_evidence, "game_id", "forged-game-id")
    evidence_mismatch = copy.copy(preparation)
    object.__setattr__(evidence_mismatch, "evidence", changed_evidence)
    with pytest.raises(SkatMindInvariantError, match="canonical rebuild"):
        execute_party_wide_claim_proof_v1(evidence_mismatch)


def test_executor_rejects_forged_unavailable_values_without_execution(monkeypatch) -> None:
    evidence, _ = _build_evidence(play_count=27)
    claim = _claim_for_party(evidence, "declarer")
    preparation = build_unavailable_party_wide_claim_proof_preparation_v1(
        claim=claim,
        unavailable_reason="party_wide_claim_proof_not_executed",
        evidence=evidence,
    )

    def unexpected(*_args, **_kwargs):
        pytest.fail("Forged unavailable validation performed proof execution.")

    for name in (
        "build_party_wide_claim_proof_request_v1",
        "get_exact_search_legal_cards",
        "apply_exact_search_card",
        "build_party_wide_claim_proof_assignment_v1",
    ):
        monkeypatch.setattr(executor_module, name, unexpected)

    for field_name, field_value in (
        ("party_wide_claim_proof_preparation_version", 2),
        ("unavailable_reason", None),
        (
            "request",
            prepare_party_wide_claim_proof_request_v1(claim, evidence).request,
        ),
        ("evidence", None),
    ):
        forged = copy.copy(preparation)
        object.__setattr__(forged, field_name, field_value)
        with pytest.raises(SkatMindInvariantError):
            execute_party_wide_claim_proof_v1(forged)

    incomplete = build_unavailable_party_wide_claim_proof_preparation_v1(
        claim=claim,
        unavailable_reason="party_wide_claim_evidence_incomplete",
    )
    forged_incomplete = copy.copy(incomplete)
    object.__setattr__(forged_incomplete, "evidence", evidence)
    with pytest.raises(SkatMindInvariantError):
        execute_party_wide_claim_proof_v1(forged_incomplete)


def test_available_preparation_rebuilds_request_once_without_replay_or_state_rebuild(
    monkeypatch,
) -> None:
    evidence, _ = _build_evidence(play_count=24)
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, "defenders"), evidence
    )
    original = executor_module.build_party_wide_claim_proof_request_v1
    calls = []

    def counted(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    def unexpected(*_args, **_kwargs):
        pytest.fail("Execution rebuilt Retrospective Evidence or Exact State.")

    monkeypatch.setattr(executor_module, "build_party_wide_claim_proof_request_v1", counted)
    monkeypatch.setattr(evidence_module, "replay_historical_play_prefix", unexpected)
    monkeypatch.setattr(evidence_module, "build_exact_search_state", unexpected)
    monkeypatch.setattr(
        proof_contracts_module,
        "build_party_wide_claim_exact_state_context_v1",
        unexpected,
    )

    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "valid"
    assert len(calls) == 1
    assert calls[0] == {
        "claim": preparation.claim,
        "evidence": preparation.evidence,
        "exact_state_context": preparation.request.exact_state_context,
    }


def test_declarer_claim_uses_declarer_existential_and_defender_universal_choices() -> None:
    existential = _preparation_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        claimant_player_id="player-c",
    )
    existential_result = execute_party_wide_claim_proof_v1(existential)
    assert existential_result.status == "valid"
    assert existential_result.representative_line[0].player_id == "player-c"
    assert existential_result.representative_line[0].card == "DA"
    assert (
        existential_result.evaluated_state_count,
        existential_result.memoized_state_count,
        existential_result.terminal_state_count,
    ) == (7, 7, 1)

    universal = _preparation_from_deck(
        OPPOSING_DEFENDER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        claimant_player_id="player-c",
    )
    universal_result = execute_party_wide_claim_proof_v1(universal)
    assert universal_result.status == "invalid"
    assert universal_result.representative_line[0].player_id == "player-a"
    assert universal_result.representative_line[0].card == "C10"
    assert (
        universal_result.evaluated_state_count,
        universal_result.memoized_state_count,
        universal_result.terminal_state_count,
    ) == (5, 5, 2)


def test_defender_claim_uses_both_defenders_existentially_and_declarer_universally() -> None:
    cooperative = _preparation_from_deck(
        NONCLAIMANT_DEFENDER_MIXED_DECK,
        declarer_player_id="player-b",
        claiming_party="defenders",
        claimant_player_id="player-c",
    )
    cooperative_result = execute_party_wide_claim_proof_v1(cooperative)
    assert cooperative_result.status == "valid"
    assert cooperative.request.exact_state_context.claimant_flat_player == "left"
    assert cooperative.request.exact_state_context.exact_state.next_player == "right"
    assert cooperative_result.representative_line[0].player_id == "player-a"
    assert cooperative_result.representative_line[0].card == "CJ"
    assert (
        cooperative_result.evaluated_state_count,
        cooperative_result.memoized_state_count,
        cooperative_result.terminal_state_count,
    ) == (7, 7, 1)

    universal = _preparation_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="defenders",
        claimant_player_id="player-a",
    )
    universal_result = execute_party_wide_claim_proof_v1(universal)
    assert universal_result.status == "invalid"
    assert universal_result.representative_line[0].player_id == "player-c"
    assert universal_result.representative_line[0].card == "DA"
    assert (
        universal_result.evaluated_state_count,
        universal_result.memoized_state_count,
        universal_result.terminal_state_count,
    ) == (4, 4, 1)


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert"),
    [
        ("clubs", False, False),
        ("grand", False, False),
        ("null", False, False),
        ("null", True, False),
        ("null", False, True),
        ("null", True, True),
    ],
)
def test_executor_supports_suit_grand_and_all_four_null_variants(
    game_type: str, hand_game: bool, ouvert: bool
) -> None:
    evidence, record = _build_evidence(
        game_type=game_type,
        hand_game=hand_game,
        ouvert=ouvert,
        play_count=27,
    )
    winner_party = _party_for_trick_winner(record, record.tricks[-1])
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, winner_party), evidence
    )

    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "valid"
    assert result.assignment is not None
    assert result.assignment.recipient_party == winner_party
    assert len(result.representative_line) == 3
    assert result.representative_line[-1].completed_trick_winner_party == winner_party


@pytest.mark.parametrize(
    ("remaining_tricks", "expected_counts"),
    [
        (1, (4, 4, 1)),
        (2, (11, 11, 1)),
        (3, (27, 27, 1)),
        (4, (63, 63, 1)),
        (5, (143, 143, 1)),
    ],
)
def test_executor_completes_one_through_five_unresolved_tricks(
    remaining_tricks: int, expected_counts: tuple[int, int, int]
) -> None:
    evidence, _ = _build_evidence(play_count=30 - 3 * remaining_tricks)
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, "defenders"), evidence
    )

    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "valid"
    assert (
        result.evaluated_state_count,
        result.memoized_state_count,
        result.terminal_state_count,
    ) == expected_counts
    assert len(result.representative_line) == 3 * remaining_tricks


@pytest.mark.parametrize("play_count", [16, 17])
def test_current_incomplete_trick_is_retained_in_proof_and_assignment(play_count: int) -> None:
    evidence, _ = _build_evidence(play_count=play_count)
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, "defenders"), evidence
    )

    result = execute_party_wide_claim_proof_v1(preparation)

    assert evidence.current_trick is not None
    assert result.status == "valid"
    assert result.assignment is not None
    assert result.assignment.assigned_card_count == evidence.unresolved_card_count == 15
    assert len(result.representative_line) == sum(
        len(cards) for _, cards in evidence.remaining_hands
    )
    assert len(result.representative_line) + len(evidence.current_trick.plays) == 15


@pytest.mark.parametrize("play_count", [28, 29])
def test_current_incomplete_trick_fails_at_first_new_opposing_win(play_count: int) -> None:
    evidence, record = _build_evidence(play_count=play_count)
    winner_party = _party_for_trick_winner(record, record.tricks[-1])
    claiming_party = "defenders" if winner_party == "declarer" else "declarer"
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, claiming_party), evidence
    )

    result = execute_party_wide_claim_proof_v1(preparation)

    assert evidence.current_trick is not None
    assert result.status == "invalid"
    assert len(result.representative_line) == 3 - len(evidence.current_trick.plays)
    assert {move.card for move in result.representative_line}.isdisjoint(
        {card for _, card in evidence.current_trick.plays}
    )
    assert result.representative_line[-1].completed_trick_winner_party == winner_party


def test_existing_opposing_tricks_are_only_the_root_baseline() -> None:
    preparation = _preparation_from_deck(
        NONCLAIMANT_DEFENDER_MIXED_DECK,
        declarer_player_id="player-b",
        claiming_party="defenders",
        claimant_player_id="player-c",
    )
    root = preparation.request.exact_state_context.exact_state
    assert root.declarer_completed_tricks == 2

    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "valid"
    assert all(
        move.completed_trick_winner_party in (None, "defenders")
        for move in result.representative_line
    )


def test_failure_precedes_normal_terminal_success_for_the_final_trick() -> None:
    evidence, record = _build_evidence(play_count=27)
    winner_party = _party_for_trick_winner(record, record.tricks[-1])
    opposing_party = "defenders" if winner_party == "declarer" else "declarer"
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, opposing_party), evidence
    )

    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "invalid"
    assert result.terminal_state_count == 1
    assert len(result.representative_line) == 3
    assert result.representative_line[-1].completed_trick_winner_party == winner_party


def test_valid_line_is_full_stable_and_assignment_is_exact() -> None:
    preparation = _preparation_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        claimant_player_id="player-c",
    )
    evidence = preparation.evidence
    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "valid"
    assert all(isinstance(move, PartyWideClaimProofMoveV1) for move in result.representative_line)
    assert {move.player_id for move in result.representative_line} <= {
        player.player_id for player in evidence.players
    }
    assert {move.player_id for move in result.representative_line}.isdisjoint(
        {"me", "left", "right"}
    )
    assert len(result.representative_line) == sum(
        len(cards) for _, cards in evidence.remaining_hands
    )
    assert all(
        move.completed_trick_winner_party in (None, "declarer")
        for move in result.representative_line
    )
    assert result.assignment is not None
    assert result.assignment.to_dict() == {
        "recipient_party": "declarer",
        "assigned_trick_count": evidence.remaining_trick_count,
        "assigned_card_count": evidence.unresolved_card_count,
        "assigned_card_points": evidence.unresolved_card_points,
    }
    assert result.proof_complete is True
    assert result.claim_satisfied is True
    assert result.counterexample_found is False


def test_invalid_line_ends_at_first_opposing_trick_without_assignment() -> None:
    preparation = _preparation_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="defenders",
        claimant_player_id="player-a",
    )
    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "invalid"
    assert result.assignment is None
    assert result.proof_complete is True
    assert result.claim_satisfied is False
    assert result.counterexample_found is True
    assert len(result.representative_line) == 3
    assert all(
        move.completed_trick_winner_party is None for move in result.representative_line[:-1]
    )
    assert result.representative_line[-1].completed_trick_winner_party == "declarer"


def test_canonical_short_circuiting_and_exact_transition_calls(monkeypatch) -> None:
    preparation = _preparation_from_deck(
        OPPOSING_DEFENDER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        claimant_player_id="player-c",
    )
    root = preparation.request.exact_state_context.exact_state
    legal_calls = []
    root_transitions = []
    original_legal = executor_module.get_exact_search_legal_cards
    original_apply = executor_module.apply_exact_search_card

    def counted_legal(state):
        cards = original_legal(state)
        legal_calls.append((state, cards))
        return cards

    def counted_apply(state, card):
        if state == root:
            root_transitions.append(card)
        return original_apply(state, card)

    monkeypatch.setattr(executor_module, "get_exact_search_legal_cards", counted_legal)
    monkeypatch.setattr(executor_module, "apply_exact_search_card", counted_apply)

    result = execute_party_wide_claim_proof_v1(preparation)

    assert result.status == "invalid"
    assert legal_calls[0] == (root, ("C10", "SK"))
    assert root_transitions == ["C10"]
    assert result.representative_line[0].card == "C10"


def test_satisfied_universal_node_evaluates_all_children_and_memoizes_exact_states(
    monkeypatch,
) -> None:
    preparation = _preparation_from_deck(
        OPPOSING_DEFENDER_ALL_SUCCESS_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        claimant_player_id="player-c",
    )
    root = preparation.request.exact_state_context.exact_state
    root_transitions = []
    child_states = []
    legal_states = []
    original_legal = executor_module.get_exact_search_legal_cards
    original_apply = executor_module.apply_exact_search_card

    def counted_legal(state):
        legal_states.append(state)
        return original_legal(state)

    def counted_apply(state, card):
        transition = original_apply(state, card)
        child_states.append(transition.next_state)
        if state == root:
            root_transitions.append(card)
        return transition

    monkeypatch.setattr(executor_module, "get_exact_search_legal_cards", counted_legal)
    monkeypatch.setattr(executor_module, "apply_exact_search_card", counted_apply)

    first = execute_party_wide_claim_proof_v1(preparation)
    second = execute_party_wide_claim_proof_v1(preparation)

    assert first == second
    assert first.status == "valid"
    assert root_transitions[:2] == ["HA", "H9"]
    assert first.representative_line[0].card == "HA"
    assert (first.evaluated_state_count, first.memoized_state_count) == (16, 16)
    assert first.terminal_state_count == 3
    first_run_children = child_states[: len(child_states) // 2]
    first_run_legal_states = legal_states[: len(legal_states) // 2]
    assert len(first_run_children) > len(set(first_run_children))
    assert len(first_run_legal_states) == len(set(first_run_legal_states))
    assert first.evaluated_state_count == len({root, *first_run_children})


def test_executor_has_no_budget_time_random_search_settlement_or_direct_rule_path() -> None:
    source = EXECUTOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = tuple(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    )
    forbidden_imports = {
        "random",
        "time",
        "skatmind.api",
        "skatmind.cli",
        "skatmind.compatible_world_minimax",
        "skatmind.defender_open_play",
        "skatmind.exact_rest_trick_proof",
        "skatmind.final_settlement",
        "skatmind.game_end",
        "skatmind.historical_game",
        "skatmind.perfect_information_minimax",
        "skatmind.recommender",
        "skatmind.rules",
        "skatmind.settlement_normative_matrix",
    }
    assert forbidden_imports.isdisjoint(imports)
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {"get_exact_search_legal_cards", "apply_exact_search_card"} <= call_names
    assert {
        "get_legal_cards",
        "get_trick_winner",
        "get_trick_points",
        "build_exact_search_state",
        "prove_defender_rest_tricks",
    }.isdisjoint(call_names)
    forbidden_runtime_names = {
        "budget",
        "depth",
        "elapsed",
        "partial",
        "sample",
        "seed",
        "timeout",
    }
    runtime_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)
    }
    assert forbidden_runtime_names.isdisjoint(runtime_names)


def test_existing_defender_proof_and_runtime_matrix_boundaries_are_current() -> None:
    from skatmind.exact_rest_trick_proof import prove_defender_rest_tricks

    valid = prove_defender_rest_tricks(
        build_one_trick_state(me=("C7",), left=("CJ",), right=("C8",)),
        exposing_defender="left",
        declarer_player="me",
    )
    invalid = prove_defender_rest_tricks(
        build_one_trick_state(me=("CA",), left=("C7",), right=("C8",)),
        exposing_defender="left",
        declarer_player="me",
    )
    assert (valid.status, invalid.status) == ("valid", "invalid")
    assert invalid.line[-1].trick_winner == "me"
    for path in (
        PROJECT_ROOT / "src" / "skatmind" / "exact_rest_trick_proof.py",
        PROJECT_ROOT / "src" / "skatmind" / "defender_open_play.py",
    ):
        assert "party_wide_claim_proof_executor" not in path.read_text(encoding="utf-8")

    cases = get_normative_settlement_cases()
    approved = get_normative_settlement_case(
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
    )
    assert SETTLEMENT_NORMATIVE_MATRIX_VERSION == 3
    assert len(cases) == 61
    assert approved.implementation_status == SUPPORTED_AS_IS
    assert approved.implementation_modules == (
        "skatmind.historical_game_end",
        "skatmind.historical_party_wide_claim",
        "skatmind.party_wide_claim_proof_executor",
        "skatmind.party_wide_claim_adjudication",
    )
    assert approved.stable_unavailable_reason is None
    assert approved.proof_policy == PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1
    assert _runtime_union_kinds(GameShortening) == {
        "declarer_card_exposure",
        "declarer_concession",
        "defender_concession",
        "defender_open_play",
        "open_card_throw",
    }
    assert _runtime_union_kinds(HistoricalGameEvent) == {
        "declarer_card_exposure_continuation",
        "defender_open_play_continuation",
    }
    assert len(HISTORICAL_GAME_END_REASONS) == 7
    assert len(VALID_GAME_END_REASONS) == 6


def test_public_cli_schema_example_generated_and_package_boundaries_are_unchanged() -> None:
    private_names = (
        "PARTY_WIDE_CLAIM_PROOF_EXECUTOR_VERSION",
        "PARTY_WIDE_CLAIM_PROOF_EXECUTION_METHOD",
        "execute_party_wide_claim_proof_v1",
    )
    assert skatmind.__all__ == ("api", "errors", "__version__")
    assert all(name not in api_v1.__all__ for name in private_names)
    assert len(WorkflowV1) == 7
    cli_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "src" / "skatmind" / "cli").rglob("*.py")
    )
    assert "party_wide_claim" not in cli_source
    # Filesystem glob order is not stable across platforms; normalize before comparison.
    external_executor_references = tuple(
        sorted(
            (
                path
                for path in (PROJECT_ROOT / "src" / "skatmind").rglob("*.py")
                if path != EXECUTOR_PATH
                if "party_wide_claim_proof_executor" in path.read_text(encoding="utf-8")
            ),
            key=lambda path: path.relative_to(PROJECT_ROOT).as_posix(),
        )
    )
    assert external_executor_references == (
        PROJECT_ROOT / "src" / "skatmind" / "historical_party_wide_claim.py",
        PROJECT_ROOT / "src" / "skatmind" / "settlement_normative_matrix.py",
    )
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 71
    assert (
        len(tuple((PROJECT_ROOT / "src" / "skatmind" / "schema_resources").glob("*.schema.json")))
        == 71
    )
    assert {
        path.name for path in (PROJECT_ROOT / "examples").glob("session_*.json")
    } == SESSION_EXAMPLE_NAMES
    assert len(SCENARIOS) == 98
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["version"] == skatmind.__version__ == "0.17.0"
    assert project["requires-python"] == ">=3.13"
    assert project["scripts"] == {"skatmind": "skatmind.cli:main"}


def test_result_reuses_existing_contract_without_new_public_fields() -> None:
    preparation = _preparation_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        claimant_player_id="player-c",
    )
    result = execute_party_wide_claim_proof_v1(preparation)

    assert list(result.to_dict()) == [field.name for field in fields(result)]
    assert set(result.to_dict()).isdisjoint(
        {
            "elapsed_time",
            "game_end",
            "game_result",
            "partial_result",
            "recommendation",
            "search_result",
            "seed",
            "settlement",
            "timeout",
            "winner",
        }
    )
    assert inspect.signature(execute_party_wide_claim_proof_v1).parameters.keys() == {"preparation"}
