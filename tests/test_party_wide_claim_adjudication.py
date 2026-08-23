import ast
import copy
import json
import tomllib
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from types import MappingProxyType
from typing import get_args

import pytest
from test_historical_game import build_historical_input
from test_party_wide_claim_contracts import (
    SESSION_EXAMPLE_NAMES,
    _build_evidence,
    _claim_for_party,
    _party_for_trick_winner,
    _prefix_tricks,
)
from test_party_wide_claim_proof_executor import (
    DECLARER_MIXED_DECK,
    NONCLAIMANT_DEFENDER_MIXED_DECK,
    _preparation_from_deck,
)

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.party_wide_claim_adjudication as adjudication_module
import skat_ai.party_wide_claim_evidence as evidence_module
import skat_ai.party_wide_claim_proof_contracts as proof_contracts_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1 import WorkflowV1
from skat_ai.errors import SkatAIInvariantError
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_end import VALID_GAME_END_REASONS
from skat_ai.game_result import build_game_result_summary_from_points
from skat_ai.game_shortening import GameShortening
from skat_ai.game_value import build_game_value_summary
from skat_ai.historical_game import build_historical_game_record
from skat_ai.historical_game_end import HISTORICAL_GAME_END_REASONS
from skat_ai.historical_game_event import HistoricalGameEvent
from skat_ai.party_wide_claim_adjudication import adjudicate_party_wide_claim_proof_v1
from skat_ai.party_wide_claim_adjudication_contracts import (
    PARTY_WIDE_CLAIM_ADJUDICATION_ASSIGNMENT_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_EXECUTION_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_FACTS_VERSION,
    PARTY_WIDE_CLAIM_ADJUDICATION_LEVEL_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_NO_OUTCOME_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_OUTCOME_SOURCES,
    PARTY_WIDE_CLAIM_ADJUDICATION_OVERBID_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_PREEXISTING_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_PROOF_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_REASONS,
    PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_VERSION,
    PARTY_WIDE_CLAIM_ADJUDICATION_RUNTIME_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_SETTLEMENT_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_SETTLEMENT_PROJECTION_POLICY,
    PARTY_WIDE_CLAIM_ADJUDICATION_STATUSES,
    PARTY_WIDE_CLAIM_ADJUDICATION_WINNER_BASES,
    PartyWideClaimAdjudicationFactsV1,
    PartyWideClaimAdjudicationResultV1,
    build_party_wide_claim_adjudication_facts_v1,
    build_party_wide_claim_adjudication_result_v1,
)
from skat_ai.party_wide_claim_contracts import PARTY_WIDE_CLAIM_VERSION
from skat_ai.party_wide_claim_evidence import build_party_wide_claim_evidence_v1
from skat_ai.party_wide_claim_proof_contracts import (
    PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
    build_unavailable_party_wide_claim_proof_preparation_v1,
    build_unavailable_party_wide_claim_proof_result_v1,
    prepare_party_wide_claim_proof_request_v1,
)
from skat_ai.party_wide_claim_proof_executor import execute_party_wide_claim_proof_v1
from skat_ai.rules import get_card_points
from skat_ai.settlement_normative_matrix import (
    SETTLEMENT_NORMATIVE_MATRIX_VERSION,
    SUPPORTED_AS_IS,
    V1_NOT_SUPPORTED_CLAIM_CASE_IDS,
    get_normative_settlement_case,
    get_normative_settlement_cases,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADJUDICATION_PATH = PROJECT_ROOT / "src" / "skat_ai" / "party_wide_claim_adjudication.py"
CONTRACTS_PATH = PROJECT_ROOT / "src" / "skat_ai" / "party_wide_claim_adjudication_contracts.py"

PREEXISTING_DECLARER_DECK = (
    "CJ",
    "H9",
    "D8",
    "C10",
    "CA",
    "D9",
    "C8",
    "H8",
    "S10",
    "S7",
    "S9",
    "SQ",
    "DJ",
    "SJ",
    "HK",
    "DA",
    "HA",
    "DQ",
    "SK",
    "D10",
    "SA",
    "C9",
    "CQ",
    "DK",
    "D7",
    "HJ",
    "HQ",
    "H10",
    "S8",
    "H7",
    "CK",
    "C7",
)
PREEXISTING_DEFENDERS_DECK = (
    "CJ",
    "C10",
    "SA",
    "CA",
    "S10",
    "S8",
    "SK",
    "S9",
    "H8",
    "SQ",
    "DQ",
    "CK",
    "DK",
    "HK",
    "H10",
    "D7",
    "S7",
    "HQ",
    "C7",
    "CQ",
    "D8",
    "DJ",
    "H9",
    "HA",
    "H7",
    "D10",
    "DA",
    "C9",
    "C8",
    "D9",
    "HJ",
    "SJ",
)
DEFENDER_SCHWARZ_DECK = (
    "DA",
    "S8",
    "C7",
    "CJ",
    "S7",
    "H10",
    "CQ",
    "CK",
    "SA",
    "D8",
    "HJ",
    "DJ",
    "D9",
    "D10",
    "HA",
    "H9",
    "H8",
    "S9",
    "H7",
    "S10",
    "CA",
    "C8",
    "SQ",
    "C10",
    "SK",
    "HQ",
    "C9",
    "DQ",
    "SJ",
    "DK",
    "D7",
    "HK",
)
DECLARER_SCHWARZ_DECK = (
    "C8",
    "C9",
    "HQ",
    "D8",
    "HK",
    "HJ",
    "HA",
    "H9",
    "C7",
    "S7",
    "D10",
    "CA",
    "DK",
    "CJ",
    "C10",
    "CQ",
    "DJ",
    "DA",
    "DQ",
    "S9",
    "CK",
    "S10",
    "SJ",
    "D9",
    "H7",
    "D7",
    "SQ",
    "H8",
    "H10",
    "S8",
    "SK",
    "SA",
)
ZERO_POINT_TRICK_DECK = (
    "DJ",
    "C8",
    "CK",
    "CQ",
    "S10",
    "S9",
    "DA",
    "DQ",
    "CJ",
    "HA",
    "D9",
    "D8",
    "D7",
    "HJ",
    "HK",
    "HQ",
    "SK",
    "DK",
    "S7",
    "D10",
    "C7",
    "SA",
    "CA",
    "SJ",
    "H10",
    "H7",
    "S8",
    "C10",
    "H9",
    "C9",
    "H8",
    "SQ",
)


def _proof_from_record(
    record,
    *,
    play_count: int,
    claiming_party: str | None = None,
):
    evidence = build_party_wide_claim_evidence_v1(
        game_id=record.game_id,
        players=record.players,
        skat=record.skat,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        discarded_cards=record.discarded_cards,
        tricks=_prefix_tricks(record.tricks, play_count),
    )
    if claiming_party is None:
        assert play_count == 27
        claiming_party = _party_for_trick_winner(record, record.tricks[-1])
    claim = _claim_for_party(evidence, claiming_party)
    preparation = prepare_party_wide_claim_proof_request_v1(claim, evidence)
    return execute_party_wide_claim_proof_v1(preparation)


def _proof_from_deck(
    deck: tuple[str, ...],
    *,
    declarer_player_id: str = "player-b",
    claiming_party: str | None = None,
    play_count: int = 24,
    game_type: str = "grand",
    hand_game: bool = False,
    bid_value: int = 18,
    schneider_announced: bool = False,
    schwarz_announced: bool = False,
    ouvert: bool = False,
):
    data = build_historical_input(
        game_type=game_type,
        hand_game=hand_game,
        declarer_player_id=declarer_player_id,
        bid_value=bid_value,
        deck=list(deck),
    )
    data["declaration"]["ouvert"] = ouvert
    if game_type != "null":
        data["declaration"].update(
            {
                "schneider_announced": schneider_announced,
                "schwarz_announced": schwarz_announced,
            }
        )
    return _proof_from_record(
        build_historical_game_record(data),
        play_count=play_count,
        claiming_party=claiming_party,
    )


def _default_valid_proof(
    *,
    game_type: str = "grand",
    hand_game: bool = False,
    ouvert: bool = False,
    play_count: int = 27,
):
    evidence, record = _build_evidence(
        game_type=game_type,
        hand_game=hand_game,
        ouvert=ouvert,
        play_count=play_count,
    )
    party = _party_for_trick_winner(record, record.tricks[-1])
    return execute_party_wide_claim_proof_v1(
        prepare_party_wide_claim_proof_request_v1(_claim_for_party(evidence, party), evidence)
    )


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


def _replace_proof_evidence(proof, evidence, *, exact_state_context=None):
    request = proof.preparation.request
    assert request is not None
    forged_request = copy.copy(request)
    object.__setattr__(forged_request, "evidence", evidence)
    if exact_state_context is not None:
        object.__setattr__(forged_request, "exact_state_context", exact_state_context)
    forged_preparation = copy.copy(proof.preparation)
    object.__setattr__(forged_preparation, "evidence", evidence)
    object.__setattr__(forged_preparation, "request", forged_request)
    forged_proof = copy.copy(proof)
    object.__setattr__(forged_proof, "preparation", forged_preparation)
    return forged_proof


def test_versions_vocabularies_and_policies_are_exact() -> None:
    assert (
        PARTY_WIDE_CLAIM_ADJUDICATION_FACTS_VERSION,
        PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_VERSION,
        PARTY_WIDE_CLAIM_VERSION,
        PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
    ) == (1, 1, 1, 1)
    assert PARTY_WIDE_CLAIM_ADJUDICATION_STATUSES == ("adjudicated", "no_outcome")
    assert PARTY_WIDE_CLAIM_ADJUDICATION_REASONS == (
        "valid_proof",
        "invalid_proof",
        "unavailable_proof",
    )
    assert PARTY_WIDE_CLAIM_ADJUDICATION_OUTCOME_SOURCES == (
        "preexisting_game_decision",
        "exact_party_wide_claim_adjudication",
    )
    assert PARTY_WIDE_CLAIM_ADJUDICATION_WINNER_BASES == (
        "preexisting_game_decision",
        "completed_claim_assignment",
    )
    assert (
        PARTY_WIDE_CLAIM_ADJUDICATION_PROOF_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_PREEXISTING_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_ASSIGNMENT_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_LEVEL_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_OVERBID_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_SETTLEMENT_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_SETTLEMENT_PROJECTION_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_NO_OUTCOME_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_RUNTIME_POLICY,
        PARTY_WIDE_CLAIM_ADJUDICATION_EXECUTION_POLICY,
    ) == (
        "valid_proof_only_terminal_adjudication",
        "preserve_preexisting_game_decision",
        "assign_all_unresolved_tricks_cards_and_points_to_claiming_party",
        "complete_points_and_trick_ownership_before_result",
        "normal_achieved_levels_with_null_not_applicable",
        "preserve_declared_and_overbid_required_value",
        "reuse_existing_result_and_final_settlement",
        "exact_claim_assignment_reuses_normal_completion_settlement_projection",
        "invalid_or_unavailable_proof_produces_no_outcome",
        "private_internal_without_runtime_or_historical_union",
        "no_proof_rerun_search_or_fallback",
    )
    with pytest.raises(TypeError, match="focused builder"):
        PartyWideClaimAdjudicationFactsV1()
    with pytest.raises(TypeError, match="focused builder"):
        PartyWideClaimAdjudicationResultV1()


def test_invalid_and_unavailable_proofs_create_no_outcome_or_downstream_work(
    monkeypatch,
) -> None:
    evidence, record = _build_evidence(play_count=27)
    winner_party = _party_for_trick_winner(record, record.tricks[-1])
    opposing_party = "defenders" if winner_party == "declarer" else "declarer"
    invalid = execute_party_wide_claim_proof_v1(
        prepare_party_wide_claim_proof_request_v1(
            _claim_for_party(evidence, opposing_party), evidence
        )
    )
    available = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, winner_party), evidence
    )
    not_executed = build_unavailable_party_wide_claim_proof_result_v1(
        preparation=available,
        unavailable_reason="party_wide_claim_proof_not_executed",
    )
    source_unavailable_preparation = build_unavailable_party_wide_claim_proof_preparation_v1(
        claim=available.claim,
        unavailable_reason="party_wide_claim_evidence_incomplete",
        evidence=None,
    )
    source_unavailable = build_unavailable_party_wide_claim_proof_result_v1(
        preparation=source_unavailable_preparation,
        unavailable_reason="party_wide_claim_evidence_incomplete",
    )

    def unexpected(*_args, **_kwargs):
        pytest.fail("No-outcome adjudication performed downstream scoring work.")

    for name in (
        "build_game_value_summary",
        "build_overbid_summary",
        "build_game_result_summary_from_points",
        "determine_decision_state_before_game_end",
        "build_final_settlement_summary",
    ):
        monkeypatch.setattr(adjudication_module, name, unexpected)
    monkeypatch.setattr(proof_contracts_module, "build_game_value_summary", unexpected)
    monkeypatch.setattr(proof_contracts_module, "build_overbid_summary", unexpected)
    monkeypatch.setattr(evidence_module, "replay_historical_play_prefix", unexpected)
    monkeypatch.setattr(
        evidence_module,
        "build_party_wide_claim_exact_state_context_v1",
        unexpected,
    )

    for proof, reason in (
        (invalid, "invalid_proof"),
        (not_executed, "unavailable_proof"),
        (source_unavailable, "unavailable_proof"),
    ):
        before = copy.deepcopy(proof.to_dict())
        result = adjudicate_party_wide_claim_proof_v1(proof)
        assert result.status == "no_outcome"
        assert result.reason == reason
        assert result.proof_result is proof
        assert result.facts is None
        assert result.game_value_summary is None
        assert result.overbid_summary is None
        assert result.game_result_summary is None
        assert result.final_settlement_summary is None
        assert proof.to_dict() == before


def test_valid_proof_is_strictly_reconciled_without_proof_execution(monkeypatch) -> None:
    proof = _default_valid_proof()
    original = copy.deepcopy(proof.to_dict())

    def unexpected(*_args, **_kwargs):
        pytest.fail("Adjudication reran proof or exact-state traversal.")

    for module_name in (
        "skat_ai.party_wide_claim_proof_executor",
        "skat_ai.exact_search_state",
    ):
        module = __import__(module_name, fromlist=["unused"])
        for name in (
            "execute_party_wide_claim_proof_v1",
            "build_exact_search_state",
            "get_exact_search_legal_cards",
            "apply_exact_search_card",
        ):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, unexpected)
    monkeypatch.setattr(proof_contracts_module, "build_game_value_summary", unexpected)
    monkeypatch.setattr(proof_contracts_module, "build_overbid_summary", unexpected)
    monkeypatch.setattr(evidence_module, "replay_historical_play_prefix", unexpected)
    monkeypatch.setattr(
        evidence_module,
        "build_party_wide_claim_exact_state_context_v1",
        unexpected,
    )

    assert adjudicate_party_wide_claim_proof_v1(proof).status == "adjudicated"
    assert proof.to_dict() == original

    with pytest.raises(ValueError, match="PartyWideClaimProofResultV1"):
        adjudicate_party_wide_claim_proof_v1("valid")  # type: ignore[arg-type]
    for field_name, value in (
        ("status", "invalid"),
        ("claim_satisfied", False),
        ("assignment", None),
        ("representative_line", ()),
    ):
        forged = copy.copy(proof)
        object.__setattr__(forged, field_name, value)
        with pytest.raises(SkatAIInvariantError):
            adjudicate_party_wide_claim_proof_v1(forged)
    forged_assignment = copy.copy(proof.assignment)
    object.__setattr__(
        forged_assignment,
        "assigned_card_points",
        proof.assignment.assigned_card_points + 1,
    )
    forged = copy.copy(proof)
    object.__setattr__(forged, "assignment", forged_assignment)
    with pytest.raises(SkatAIInvariantError):
        adjudicate_party_wide_claim_proof_v1(forged)


def test_forged_retained_request_and_evidence_are_rejected() -> None:
    proof = _default_valid_proof()
    preparation = proof.preparation
    request = preparation.request
    evidence = preparation.evidence
    assert request is not None and evidence is not None

    forged_request = copy.copy(request)
    object.__setattr__(forged_request, "proof_policy", "forged")
    forged_preparation = copy.copy(preparation)
    object.__setattr__(forged_preparation, "request", forged_request)
    forged_proof = copy.copy(proof)
    object.__setattr__(forged_proof, "preparation", forged_preparation)
    with pytest.raises(SkatAIInvariantError):
        adjudicate_party_wide_claim_proof_v1(forged_proof)

    forged_evidence = copy.copy(evidence)
    object.__setattr__(forged_evidence, "played_card_count", evidence.played_card_count + 1)
    with pytest.raises(SkatAIInvariantError):
        adjudicate_party_wide_claim_proof_v1(_replace_proof_evidence(proof, forged_evidence))

    forged_evidence = copy.copy(evidence)
    object.__setattr__(
        forged_evidence, "remaining_hands", tuple(reversed(evidence.remaining_hands))
    )
    with pytest.raises(SkatAIInvariantError):
        adjudicate_party_wide_claim_proof_v1(_replace_proof_evidence(proof, forged_evidence))


def test_forged_play_ownership_and_matadors_are_rejected() -> None:
    proof = _default_valid_proof()
    evidence = proof.preparation.evidence
    request = proof.preparation.request
    assert evidence is not None and request is not None

    tricks = list(evidence.tricks)
    trick = tricks[2]
    tricks[2] = replace(
        trick,
        plays=(
            trick.plays[0],
            replace(trick.plays[1], card="H8"),
            replace(trick.plays[2], card="S8"),
        ),
    )
    completed_tricks = list(evidence.completed_tricks)
    completed_tricks[2] = replace(
        completed_tricks[2],
        plays=tuple((play.player_id, play.card) for play in tricks[2].plays),
    )
    forged_evidence = copy.copy(evidence)
    object.__setattr__(forged_evidence, "tricks", tuple(tricks))
    object.__setattr__(forged_evidence, "completed_tricks", tuple(completed_tricks))
    with pytest.raises(SkatAIInvariantError):
        adjudicate_party_wide_claim_proof_v1(_replace_proof_evidence(proof, forged_evidence))

    declaration = evidence.declaration
    assert declaration.matadors == 1
    forged_declaration = GameDeclaration(
        declaration.game_type,
        hand_game=declaration.hand_game,
        ouvert=declaration.ouvert,
        schneider_announced=declaration.schneider_announced,
        schwarz_announced=declaration.schwarz_announced,
        matadors=4,
        bid_value=declaration.bid_value,
    )
    forged_evidence = copy.copy(evidence)
    object.__setattr__(forged_evidence, "declaration", forged_declaration)
    forged_state = copy.copy(request.exact_state_context.exact_state)
    object.__setattr__(forged_state, "declaration", forged_declaration)
    forged_context = copy.copy(request.exact_state_context)
    object.__setattr__(forged_context, "exact_state", forged_state)
    with pytest.raises(SkatAIInvariantError):
        adjudicate_party_wide_claim_proof_v1(
            _replace_proof_evidence(
                proof,
                forged_evidence,
                exact_state_context=forged_context,
            )
        )


@pytest.mark.parametrize("hand_game", [False, True])
def test_out_of_play_points_and_assignment_reconcile_exactly(hand_game: bool) -> None:
    proof = _default_valid_proof(hand_game=hand_game)
    result = adjudicate_party_wide_claim_proof_v1(proof)
    evidence = proof.preparation.evidence
    assignment = proof.assignment
    facts = result.facts
    assert evidence is not None and assignment is not None and facts is not None
    assert facts.out_of_play_points == sum(
        get_card_points(card) for card in evidence.out_of_play_cards
    )
    assert facts.observed_declarer_points == (
        evidence.declarer_trick_points + facts.out_of_play_points
    )
    assert facts.observed_defender_points == evidence.defender_trick_points
    assert (
        facts.observed_declarer_points
        + facts.observed_defender_points
        + (assignment.assigned_card_points)
        == 120
    )
    assert facts.remaining_points_recipient == proof.preparation.claim.claiming_party
    assert facts.remaining_points_assigned == assignment.assigned_card_points
    assert facts.final_declarer_points + facts.final_defender_points == 120
    if hand_game:
        assert evidence.out_of_play_cards == evidence.skat
    else:
        assert evidence.out_of_play_cards == evidence.discarded_cards


def test_declarer_and_defender_claims_assign_points_and_tricks_only_to_claiming_party() -> None:
    declarer_proof = execute_party_wide_claim_proof_v1(
        _preparation_from_deck(
            DECLARER_MIXED_DECK,
            declarer_player_id="player-c",
            claiming_party="declarer",
            claimant_player_id="player-c",
        )
    )
    defender_proof = execute_party_wide_claim_proof_v1(
        _preparation_from_deck(
            NONCLAIMANT_DEFENDER_MIXED_DECK,
            declarer_player_id="player-b",
            claiming_party="defenders",
            claimant_player_id="player-c",
        )
    )
    for proof, expected in (
        (declarer_proof, ("declarer", True)),
        (defender_proof, ("defenders", False)),
    ):
        result = adjudicate_party_wide_claim_proof_v1(proof)
        facts = result.facts
        assignment = proof.assignment
        assert facts is not None and assignment is not None
        assert facts.remaining_points_recipient == expected[0]
        assert (
            facts.final_completed_trick_winner_parties[-assignment.assigned_trick_count :]
            == (expected[0],) * assignment.assigned_trick_count
        )
        if expected[1]:
            assert facts.assigned_declarer_points == assignment.assigned_card_points
            assert facts.assigned_defender_points == 0
            assert facts.assigned_declarer_tricks == assignment.assigned_trick_count
            assert facts.assigned_defender_tricks == 0
        else:
            assert facts.assigned_declarer_points == 0
            assert facts.assigned_defender_points == assignment.assigned_card_points
            assert facts.assigned_declarer_tricks == 0
            assert facts.assigned_defender_tricks == assignment.assigned_trick_count
        assert len(facts.final_completed_trick_winner_parties) == 10
        assert facts.final_declarer_tricks + facts.final_defender_tricks == 10


@pytest.mark.parametrize("play_count", [28, 29])
def test_current_incomplete_trick_is_assigned_exactly_once(play_count: int) -> None:
    proof = _default_valid_proof(play_count=play_count)
    evidence = proof.preparation.evidence
    result = adjudicate_party_wide_claim_proof_v1(proof)
    facts = result.facts
    assert evidence is not None and evidence.current_trick is not None
    assert proof.assignment is not None and facts is not None
    assert len(evidence.current_trick.plays) == play_count % 3
    assert proof.assignment.assigned_card_count == evidence.unresolved_card_count == 3
    assert proof.assignment.assigned_trick_count == evidence.remaining_trick_count == 1
    assert facts.observed_declarer_tricks + facts.observed_defender_tricks == 9
    assert facts.final_declarer_tricks + facts.final_defender_tricks == 10
    assert facts.remaining_points_assigned == evidence.unresolved_card_points


def test_preexisting_winners_are_preserved_against_opposing_valid_claims() -> None:
    declarer_won = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            PREEXISTING_DECLARER_DECK,
            claiming_party="defenders",
            play_count=24,
        )
    )
    defenders_won = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            PREEXISTING_DEFENDERS_DECK,
            claiming_party="declarer",
            play_count=24,
        )
    )
    assert declarer_won.facts is not None
    assert declarer_won.facts.claiming_party == "defenders"
    assert declarer_won.facts.decision_state_before_claim == "declarer_already_won"
    assert declarer_won.facts.adjudicated_winner == "declarer"
    assert defenders_won.facts is not None
    assert defenders_won.facts.claiming_party == "declarer"
    assert defenders_won.facts.decision_state_before_claim == "defenders_already_won"
    assert defenders_won.facts.adjudicated_winner == "defenders"
    for result in (declarer_won, defenders_won):
        assert result.facts.outcome_source == "preexisting_game_decision"
        assert result.facts.winner_basis == "preexisting_game_decision"
        assert result.game_result_summary["status"] == "final_decided"


def test_undecided_suit_and_grand_winners_use_completed_assignment() -> None:
    declarer = adjudicate_party_wide_claim_proof_v1(
        execute_party_wide_claim_proof_v1(
            _preparation_from_deck(
                DECLARER_MIXED_DECK,
                declarer_player_id="player-c",
                claiming_party="declarer",
                claimant_player_id="player-c",
            )
        )
    )
    defenders = adjudicate_party_wide_claim_proof_v1(
        execute_party_wide_claim_proof_v1(
            _preparation_from_deck(
                NONCLAIMANT_DEFENDER_MIXED_DECK,
                declarer_player_id="player-b",
                claiming_party="defenders",
                claimant_player_id="player-c",
            )
        )
    )
    assert declarer.facts is not None and defenders.facts is not None
    assert declarer.facts.adjudicated_winner == "declarer"
    assert defenders.facts.adjudicated_winner == "defenders"
    for result in (declarer, defenders):
        assert result.facts.decision_state_before_claim == "undecided"
        assert result.facts.outcome_source == "exact_party_wide_claim_adjudication"
        assert result.facts.winner_basis == "completed_claim_assignment"
        assert result.game_result_summary["status"] == "final_adjudicated"


def test_simple_suit_contract_uses_existing_result_and_settlement_behavior() -> None:
    proof = _proof_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        play_count=27,
        game_type="clubs",
    )
    result = adjudicate_party_wide_claim_proof_v1(proof)
    assert result.facts is not None
    assert result.game_value_summary["game_type"] == "clubs"
    assert result.game_value_summary["base_value"] == 12
    assert result.facts.claiming_party == "declarer"
    assert result.facts.decision_state_before_claim == "undecided"
    assert result.facts.adjudicated_winner == "declarer"
    assert result.final_settlement_summary["winner"] == "declarer"
    assert result.final_settlement_summary["settlement_score"] == 24


@pytest.mark.parametrize(
    ("hand_game", "ouvert"),
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_all_null_variants_use_trick_ownership_and_no_levels(
    hand_game: bool,
    ouvert: bool,
) -> None:
    proof = _default_valid_proof(
        game_type="null",
        hand_game=hand_game,
        ouvert=ouvert,
    )
    result = adjudicate_party_wide_claim_proof_v1(proof)
    facts = result.facts
    assert facts is not None
    expected_winner = "declarer" if facts.final_declarer_tricks == 0 else "defenders"
    if facts.decision_state_before_claim != "undecided":
        expected_winner = (
            "declarer"
            if facts.decision_state_before_claim == "declarer_already_won"
            else "defenders"
        )
    assert facts.adjudicated_winner == expected_winner
    assert facts.achieved_schneider_status == "not_applicable"
    assert facts.achieved_schwarz_status == "not_applicable"
    assert facts.achieved_schneider_applied is False
    assert facts.achieved_schwarz_applied is False
    assert result.game_result_summary["effective_schneider_status"] == "not_applicable"
    assert result.game_result_summary["effective_schwarz_status"] == "not_applicable"
    assert result.final_settlement_summary["effective_game_value"] in {23, 35, 46, 59}


def test_valid_declarer_null_claim_preserves_preexisting_defender_win() -> None:
    result = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            DECLARER_MIXED_DECK,
            declarer_player_id="player-c",
            claiming_party="declarer",
            play_count=27,
            game_type="null",
        )
    )
    assert result.facts is not None
    assert result.facts.claiming_party == "declarer"
    assert result.facts.decision_state_before_claim == "defenders_already_won"
    assert result.facts.final_declarer_tricks >= 1
    assert result.facts.adjudicated_winner == "defenders"
    assert result.final_settlement_summary["winner"] == "defenders"


def test_undecided_declarer_null_claim_assigns_trick_and_loses_contract() -> None:
    result = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            DECLARER_SCHWARZ_DECK,
            declarer_player_id="player-c",
            claiming_party="declarer",
            play_count=27,
            game_type="null",
        )
    )
    assert result.facts is not None
    assert result.facts.decision_state_before_claim == "undecided"
    assert result.facts.outcome_source == "exact_party_wide_claim_adjudication"
    assert result.facts.final_declarer_tricks == 1
    assert result.facts.adjudicated_winner == "defenders"
    assert result.game_result_summary["status"] == "final_adjudicated"
    assert result.final_settlement_summary["winner"] == "defenders"


def test_schneider_schwarz_and_zero_point_trick_use_existing_exact_semantics() -> None:
    declarer_schneider = adjudicate_party_wide_claim_proof_v1(
        execute_party_wide_claim_proof_v1(
            _preparation_from_deck(
                DECLARER_MIXED_DECK,
                declarer_player_id="player-c",
                claiming_party="declarer",
                claimant_player_id="player-c",
            )
        )
    )
    defender_schneider = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            PREEXISTING_DEFENDERS_DECK,
            claiming_party="declarer",
            play_count=24,
        )
    )
    declarer_schwarz = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            DECLARER_SCHWARZ_DECK,
            claiming_party="declarer",
            play_count=15,
        )
    )
    defender_schwarz = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            DEFENDER_SCHWARZ_DECK,
            claiming_party="defenders",
            play_count=15,
        )
    )
    zero_point_trick = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            ZERO_POINT_TRICK_DECK,
            claiming_party="defenders",
            play_count=24,
        )
    )
    assert declarer_schneider.facts.achieved_schneider_status == ("declarer_made_schneider")
    assert defender_schneider.facts.achieved_schneider_status == ("defenders_made_schneider")
    assert declarer_schwarz.facts.achieved_schwarz_status == "declarer_made_schwarz"
    assert defender_schwarz.facts.achieved_schwarz_status == "defenders_made_schwarz"
    assert zero_point_trick.facts.final_declarer_points == 0
    assert zero_point_trick.facts.final_declarer_tricks == 1
    assert zero_point_trick.facts.achieved_schwarz_status == "none"
    for result in (declarer_schwarz, defender_schwarz):
        assert result.facts.achieved_schneider_applied is True
        assert result.facts.achieved_schwarz_applied is True


@pytest.mark.parametrize(
    ("schneider_announced", "schwarz_announced", "ouvert", "expected_level"),
    [
        (True, False, False, "schneider"),
        (True, True, False, "schwarz"),
        (True, True, True, "schwarz"),
    ],
)
def test_declared_levels_remain_mandatory_without_automatic_award(
    schneider_announced: bool,
    schwarz_announced: bool,
    ouvert: bool,
    expected_level: str,
) -> None:
    proof = _proof_from_deck(
        tuple(build_historical_input()["players"][0]["initial_hand"])
        + tuple(build_historical_input()["players"][1]["initial_hand"])
        + tuple(build_historical_input()["players"][2]["initial_hand"])
        + tuple(build_historical_input()["skat"]),
        claiming_party=None,
        play_count=27,
        hand_game=True,
        schneider_announced=schneider_announced,
        schwarz_announced=schwarz_announced,
        ouvert=ouvert,
    )
    result = adjudicate_party_wide_claim_proof_v1(proof)
    assert result.game_result_summary["declared_mandatory_play_level"] == expected_level
    assert result.game_result_summary["mandatory_play_level"] == expected_level
    assert result.game_result_summary["mandatory_level_awarded"] is False
    assert result.game_result_summary["mandatory_level_source"] == "declared_announcement"
    assert result.game_result_summary["mandatory_level_covered"] is False
    assert result.facts.adjudicated_winner == "defenders"
    assert result.final_settlement_summary["is_loss"] is True
    assert result.final_settlement_summary["is_complete"] is True


@pytest.mark.parametrize(
    ("schwarz_announced", "expected_level", "expected_score"),
    [(False, "schneider", 144), (True, "schwarz", 168)],
)
def test_declared_levels_can_be_satisfied_by_exact_completed_assignment(
    schwarz_announced: bool,
    expected_level: str,
    expected_score: int,
) -> None:
    result = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            DECLARER_SCHWARZ_DECK,
            claiming_party=None,
            play_count=27,
            hand_game=True,
            schneider_announced=True,
            schwarz_announced=schwarz_announced,
        )
    )
    assert result.facts is not None
    assert result.facts.adjudicated_winner == "declarer"
    assert result.game_result_summary["mandatory_play_level"] == expected_level
    assert result.game_result_summary["mandatory_level_covered"] is True
    assert result.final_settlement_summary["is_loss"] is False
    assert result.final_settlement_summary["settlement_score"] == expected_score


def test_supported_overbid_required_level_is_retained_and_uses_existing_score() -> None:
    proof = _proof_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        play_count=24,
        bid_value=49,
    )
    result = adjudicate_party_wide_claim_proof_v1(proof)
    assert result.facts is not None
    assert result.facts.overbid_required_level == "schneider"
    assert result.facts.overbid_required_value_applied is True
    assert result.overbid_summary["is_overbid"] is True
    assert result.overbid_summary["required_game_value"] == 72
    assert result.game_result_summary["overbid_requirement_covered"] is True
    assert result.game_result_summary["mandatory_level_awarded"] is False
    assert result.final_settlement_summary["effective_game_value"] == 72
    assert result.final_settlement_summary["settlement_score"] == -144


@pytest.mark.parametrize(
    ("deck", "bid_value", "expected_level", "expected_covered", "expected_winner"),
    [
        (DECLARER_MIXED_DECK, 49, "schneider", True, "declarer"),
        (DECLARER_MIXED_DECK, 73, "schwarz", False, "defenders"),
        (DECLARER_SCHWARZ_DECK, 73, "schwarz", True, "declarer"),
    ],
)
def test_supported_overbid_schneider_and_schwarz_requirements_are_exact(
    deck: tuple[str, ...],
    bid_value: int,
    expected_level: str,
    expected_covered: bool,
    expected_winner: str,
) -> None:
    declarer_player_id = "player-c" if deck == DECLARER_MIXED_DECK else "player-b"
    result = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            deck,
            declarer_player_id=declarer_player_id,
            claiming_party="declarer",
            play_count=24,
            bid_value=bid_value,
        )
    )
    assert result.facts is not None
    assert result.facts.overbid_required_level == expected_level
    assert result.facts.overbid_required_value_applied is True
    assert result.game_result_summary["overbid_requirement_covered"] is expected_covered
    assert result.facts.adjudicated_winner == expected_winner
    assert result.final_settlement_summary["is_complete"] is True
    assert result.final_settlement_summary["is_overbid"] is True
    assert result.final_settlement_summary["is_loss"] is True


def test_private_game_result_and_normal_completion_settlement_projection_are_exact(
    monkeypatch,
) -> None:
    proof = _default_valid_proof()
    original = adjudication_module.build_final_settlement_summary
    calls = []

    def counted(*args, **kwargs):
        calls.append((copy.deepcopy(args), copy.deepcopy(kwargs)))
        return original(*args, **kwargs)

    monkeypatch.setattr(adjudication_module, "build_final_settlement_summary", counted)
    result = adjudicate_party_wide_claim_proof_v1(proof)
    game_result = result.game_result_summary
    settlement = result.final_settlement_summary
    assert result.status == "adjudicated"
    assert result.reason == "valid_proof"
    assert len(calls) == 1
    projection = calls[0][0][1]
    assert projection["game_end_reason"] == "normal_completion"
    assert projection["game_end_kind"] == "normal_completion"
    assert game_result["game_end_reason"] == "party_wide_all_remaining_tricks_claim"
    assert game_result["game_end_kind"] == "party_wide_all_remaining_tricks_claim"
    assert game_result["points_remaining"] == 0
    assert game_result["is_complete"] is True
    assert game_result["party_wide_claim_proof_status"] == "valid"
    assert game_result["mandatory_level_awarded"] is False
    assert game_result["rest_trick_assignment"] == {
        "source": "party_wide_claim_proof_assignment",
        "recipient": proof.preparation.claim.claiming_party,
        "remaining_trick_count": proof.assignment.assigned_trick_count,
        "assigned_card_count": proof.assignment.assigned_card_count,
        "assigned_card_points": proof.assignment.assigned_card_points,
    }
    changed = {key for key in game_result if projection.get(key) != game_result.get(key)}
    assert changed == {"game_end_reason", "game_end_kind"}
    assert settlement["is_complete"] is True
    assert settlement["missing_inputs"] == ()
    assert settlement["winner"] == game_result["winner"]
    assert settlement["game_value"] == result.game_value_summary["game_value"]
    assert settlement["bid_value"] == proof.preparation.evidence.declaration.bid_value
    assert settlement["settlement_score"] in {
        settlement["effective_game_value"],
        -2 * settlement["effective_game_value"],
    }


def test_result_builder_rejects_forged_facts_and_downstream_summaries() -> None:
    proof = _proof_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        play_count=24,
    )
    result = adjudicate_party_wide_claim_proof_v1(proof)
    assert result.facts is not None
    assert result.facts.decision_state_before_claim == "undecided"
    serialized = result.to_dict()

    mutations = (
        ("game_value_summary", "game_value", serialized["game_value_summary"]["game_value"] + 1),
        (
            "game_value_summary",
            "game_value",
            float(serialized["game_value_summary"]["game_value"]),
        ),
        ("overbid_summary", "bid_value", 20),
        ("game_result_summary", "points_remaining", 1),
        (
            "final_settlement_summary",
            "settlement_score",
            -serialized["final_settlement_summary"]["settlement_score"],
        ),
    )
    for summary_name, field_name, forged_value in mutations:
        summaries = {
            name: copy.deepcopy(serialized[name])
            for name in (
                "game_value_summary",
                "overbid_summary",
                "game_result_summary",
                "final_settlement_summary",
            )
        }
        summaries[summary_name][field_name] = forged_value
        with pytest.raises(ValueError):
            build_party_wide_claim_adjudication_result_v1(
                status="adjudicated",
                reason="valid_proof",
                proof_result=proof,
                facts=result.facts,
                **summaries,
            )

    summaries = {
        name: copy.deepcopy(serialized[name])
        for name in (
            "game_value_summary",
            "overbid_summary",
            "game_result_summary",
            "final_settlement_summary",
        )
    }
    forged_game_value = summaries["game_value_summary"]["game_value"] + 1
    bid_value = summaries["overbid_summary"]["bid_value"]
    summaries["game_value_summary"]["game_value"] = forged_game_value
    summaries["overbid_summary"].update(
        {
            "game_value": forged_game_value,
            "margin": forged_game_value - bid_value,
            "required_game_value": forged_game_value,
        }
    )
    summaries["final_settlement_summary"].update(
        {
            "game_value": forged_game_value,
            "effective_game_value": forged_game_value,
            "settlement_score": forged_game_value,
            "overbid_margin": forged_game_value - bid_value,
            "overbid_required_game_value": forged_game_value,
        }
    )
    with pytest.raises(ValueError, match="Game-value summary contradicts"):
        build_party_wide_claim_adjudication_result_v1(
            status="adjudicated",
            reason="valid_proof",
            proof_result=proof,
            facts=result.facts,
            **summaries,
        )

    overbid_proof = _proof_from_deck(
        DECLARER_MIXED_DECK,
        declarer_player_id="player-c",
        claiming_party="declarer",
        play_count=24,
        bid_value=49,
    )
    overbid_result = adjudicate_party_wide_claim_proof_v1(overbid_proof)
    assert overbid_result.facts is not None
    forged_overbid_facts = copy.copy(overbid_result.facts)
    object.__setattr__(forged_overbid_facts, "adjudicated_winner", "defenders")
    object.__setattr__(forged_overbid_facts, "overbid_required_level", "schwarz")
    overbid_summaries = overbid_result.to_dict()
    overbid_summaries["overbid_summary"]["required_game_value"] = 96
    overbid_summaries["game_result_summary"].update(
        {
            "winner": "defenders",
            "mandatory_play_level": "schwarz",
            "mandatory_level_covered": False,
            "overbid_required_level": "schwarz",
            "overbid_requirement_covered": False,
        }
    )
    overbid_summaries["final_settlement_summary"].update(
        {
            "declarer_won_by_card_points": False,
            "winner": "defenders",
            "effective_game_value": 96,
            "settlement_score": -192,
            "overbid_required_game_value": 96,
        }
    )
    with pytest.raises(ValueError, match="strict covering game value"):
        build_party_wide_claim_adjudication_result_v1(
            status="adjudicated",
            reason="valid_proof",
            proof_result=overbid_proof,
            facts=forged_overbid_facts,
            game_value_summary=overbid_summaries["game_value_summary"],
            overbid_summary=overbid_summaries["overbid_summary"],
            game_result_summary=overbid_summaries["game_result_summary"],
            final_settlement_summary=overbid_summaries["final_settlement_summary"],
        )

    forged_accounting = copy.copy(result.facts)
    object.__setattr__(
        forged_accounting,
        "out_of_play_points",
        result.facts.out_of_play_points + 1,
    )
    with pytest.raises(ValueError, match="Proof accounting"):
        build_party_wide_claim_adjudication_result_v1(
            status="adjudicated",
            reason="valid_proof",
            proof_result=proof,
            facts=forged_accounting,
            game_value_summary=serialized["game_value_summary"],
            overbid_summary=serialized["overbid_summary"],
            game_result_summary=serialized["game_result_summary"],
            final_settlement_summary=serialized["final_settlement_summary"],
        )

    forged_facts = copy.copy(result.facts)
    object.__setattr__(forged_facts, "adjudicated_winner", "defenders")
    game_result = copy.deepcopy(serialized["game_result_summary"])
    settlement = copy.deepcopy(serialized["final_settlement_summary"])
    game_result["winner"] = "defenders"
    settlement["winner"] = "defenders"
    with pytest.raises(ValueError, match="winner contradicts"):
        build_party_wide_claim_adjudication_result_v1(
            status="adjudicated",
            reason="valid_proof",
            proof_result=proof,
            facts=forged_facts,
            game_value_summary=serialized["game_value_summary"],
            overbid_summary=serialized["overbid_summary"],
            game_result_summary=game_result,
            final_settlement_summary=settlement,
        )

    undecided_fact_values = {
        field.name: getattr(result.facts, field.name)
        for field in fields(result.facts)
        if field.name
        not in {
            "party_wide_claim_adjudication_facts_version",
            "claim_kind",
            "claimant_player_id",
            "claiming_party",
        }
    }
    undecided_fact_values["adjudicated_winner"] = "defenders"
    with pytest.raises(ValueError, match="winner contradicts"):
        build_party_wide_claim_adjudication_facts_v1(
            proof_result=proof,
            **undecided_fact_values,
        )
    undecided_fact_values["adjudicated_winner"] = result.facts.adjudicated_winner
    undecided_fact_values["overbid_required_level"] = "schneider"
    undecided_fact_values["overbid_required_value_applied"] = True
    undecided_fact_values["achieved_schneider_applied"] = False
    undecided_fact_values["achieved_schwarz_applied"] = False
    with pytest.raises(ValueError, match="Overbid-required facts contradict"):
        build_party_wide_claim_adjudication_facts_v1(
            proof_result=proof,
            **undecided_fact_values,
        )

    schneider_result = adjudicate_party_wide_claim_proof_v1(
        _proof_from_deck(
            PREEXISTING_DEFENDERS_DECK,
            claiming_party="declarer",
            play_count=24,
        )
    )
    schneider_facts = schneider_result.facts
    assert schneider_facts is not None
    assert schneider_facts.achieved_schneider_status == "defenders_made_schneider"
    fact_values = {
        field.name: getattr(schneider_facts, field.name)
        for field in fields(schneider_facts)
        if field.name
        not in {
            "party_wide_claim_adjudication_facts_version",
            "claim_kind",
            "claimant_player_id",
            "claiming_party",
        }
    }
    fact_values["achieved_schneider_status"] = "none"
    with pytest.raises(ValueError, match="achieved levels contradict"):
        build_party_wide_claim_adjudication_facts_v1(
            proof_result=schneider_result.proof_result,
            **fact_values,
        )


def test_valid_builder_call_counts_are_bounded(monkeypatch) -> None:
    proof = _default_valid_proof()
    names = (
        "build_game_value_summary",
        "build_overbid_summary",
        "build_game_result_summary_from_points",
        "determine_decision_state_before_game_end",
        "build_final_settlement_summary",
        "build_party_wide_claim_adjudication_facts_v1",
        "build_party_wide_claim_adjudication_result_v1",
    )
    counts = {name: 0 for name in names}
    for name in names:
        original = getattr(adjudication_module, name)

        def counted(*args, _name=name, _original=original, **kwargs):
            counts[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(adjudication_module, name, counted)
    first = adjudicate_party_wide_claim_proof_v1(proof)
    assert counts == {name: 1 for name in names}
    second = adjudicate_party_wide_claim_proof_v1(proof)
    assert first == second
    assert counts == {name: 2 for name in names}


def test_contracts_are_frozen_recursive_defensive_and_deterministic() -> None:
    proof = _default_valid_proof()
    result = adjudicate_party_wide_claim_proof_v1(proof)
    assert result.proof_result is proof
    assert list(result.to_dict()) == [field.name for field in fields(result)]
    assert list(result.facts.to_dict()) == [field.name for field in fields(result.facts)]
    assert isinstance(result.game_result_summary, MappingProxyType)
    assert isinstance(result.game_result_summary["thresholds"], MappingProxyType)
    assert isinstance(result.game_result_summary["rest_trick_assignment"], MappingProxyType)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.status = "no_outcome"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.game_result_summary["winner"] = "undecided"  # type: ignore[index]
    serialized = result.to_dict()
    serialized["game_result_summary"]["thresholds"]["declarer_win"] = 999
    assert result.game_result_summary["thresholds"]["declarer_win"] == 61
    assert result.to_dict() == adjudicate_party_wide_claim_proof_v1(proof).to_dict()
    json.dumps(result.to_dict(), allow_nan=False)


def test_no_proof_search_io_logging_or_public_surface_is_added() -> None:
    for path in (ADJUDICATION_PATH, CONTRACTS_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imported_roots.isdisjoint(
            {
                "asyncio",
                "logging",
                "pathlib",
                "random",
                "requests",
                "secrets",
                "socket",
                "subprocess",
                "time",
                "urllib",
            }
        )
    source = ADJUDICATION_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "build_party_wide_claim_proof_request_v1",
        "build_party_wide_claim_exact_state_context_v1",
        "build_exact_search_state",
        "execute_party_wide_claim_proof_v1",
        "get_exact_search_legal_cards",
        "apply_exact_search_card",
        "perfect_information_minimax",
        "compatible_world_minimax",
    ):
        assert forbidden not in source
    assert not hasattr(api_v1, "PartyWideClaimAdjudicationResultV1")
    assert not hasattr(skat_ai, "PartyWideClaimAdjudicationResultV1")


def test_matrix_runtime_historical_public_and_artifact_boundaries_are_current() -> None:
    cases = get_normative_settlement_cases()
    claim_case = get_normative_settlement_case(
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
    )
    assert SETTLEMENT_NORMATIVE_MATRIX_VERSION == 3
    assert len(cases) == 61
    assert claim_case.implementation_status == SUPPORTED_AS_IS
    assert claim_case.implementation_modules == (
        "skat_ai.historical_game_end",
        "skat_ai.historical_party_wide_claim",
        "skat_ai.party_wide_claim_proof_executor",
        "skat_ai.party_wide_claim_adjudication",
    )
    assert claim_case.stable_unavailable_reason is None
    assert len(V1_NOT_SUPPORTED_CLAIM_CASE_IDS) == 13
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
    assert "party_wide_all_remaining_tricks_claim" not in VALID_GAME_END_REASONS
    assert "party_wide_all_remaining_tricks_claim" in HISTORICAL_GAME_END_REASONS
    assert len(tuple(WorkflowV1)) == 7
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 70
    assert (
        len(tuple((PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob("*.schema.json")))
        == 70
    )
    assert {path.name for path in (PROJECT_ROOT / "examples").glob("session_*.json")} == (
        SESSION_EXAMPLE_NAMES
    )
    assert len(SCENARIOS) == 96
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]
    assert project["version"] == skat_ai.__version__ == "0.16.0"
    assert project["requires-python"] == ">=3.13"


def test_existing_normal_result_and_final_settlement_output_remain_unchanged() -> None:
    game_value = build_game_value_summary(_default_valid_proof().preparation.evidence.declaration)
    game_result = build_game_result_summary_from_points(61, 59)
    settlement = build_final_settlement_summary(
        game_value,
        game_result,
        {
            "bid_value": 18,
            "game_value": game_value["game_value"],
            "is_overbid": False,
            "margin": game_value["game_value"] - 18,
            "required_game_value": game_value["game_value"],
            "status": "not_overbid",
        },
    )
    assert game_result["winner"] == "declarer"
    assert game_result["status"] == "final_decided"
    assert settlement["winner"] == "declarer"
    assert settlement["settlement_score"] == game_value["game_value"]
