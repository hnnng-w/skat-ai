import ast
import copy
import json
import tomllib
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from typing import get_args

import pytest

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.party_wide_claim_evidence as evidence_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1 import WorkflowV1
from skat_ai.deck import get_full_deck
from skat_ai.game_end import VALID_GAME_END_REASONS
from skat_ai.game_shortening import GameShortening
from skat_ai.historical_game import (
    HistoricalPlay,
    HistoricalTrick,
    build_historical_game_record,
)
from skat_ai.historical_game_end import HISTORICAL_GAME_END_REASONS
from skat_ai.party_wide_claim_contracts import (
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND,
    PARTY_WIDE_CLAIM_BOUND_POLICY,
    PARTY_WIDE_CLAIM_EVIDENCE_POLICY,
    PARTY_WIDE_CLAIM_EXACT_STATE_POLICY,
    PARTY_WIDE_CLAIM_INVALID_POLICY,
    PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS,
    PARTY_WIDE_CLAIM_PARTY_POLICY,
    PARTY_WIDE_CLAIM_PROOF_POLICY,
    PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS,
    PARTY_WIDE_CLAIM_PUBLIC_POLICY,
    PARTY_WIDE_CLAIM_SCOPE_POLICY,
    PARTY_WIDE_CLAIM_SEARCH_POLICY,
    PARTY_WIDE_CLAIM_UNAVAILABLE_POLICY,
    PARTY_WIDE_CLAIM_VALID_POLICY,
    PARTY_WIDE_CLAIM_VERSION,
    PARTY_WIDE_CLAIMING_PARTIES,
    PartyWideAllRemainingTricksClaimV1,
    build_party_wide_all_remaining_tricks_claim_v1,
    validate_party_wide_claim_against_evidence_v1,
)
from skat_ai.party_wide_claim_evidence import (
    PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
    PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION,
    PartyWideClaimEvidenceV1,
    PartyWideClaimExactStateContextV1,
    build_party_wide_claim_evidence_v1,
    build_party_wide_claim_exact_state_context_v1,
)
from skat_ai.party_wide_claim_proof_contracts import (
    PARTY_WIDE_CLAIM_PROOF_PREPARATION_STATUSES,
    PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION,
    PARTY_WIDE_CLAIM_PROOF_REQUEST_VERSION,
    PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
    PARTY_WIDE_CLAIM_PROOF_STATUSES,
    PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS,
    PartyWideClaimProofAssignmentV1,
    PartyWideClaimProofMoveV1,
    PartyWideClaimProofPreparationV1,
    PartyWideClaimProofRequestV1,
    PartyWideClaimProofResultV1,
    build_invalid_party_wide_claim_proof_result_v1,
    build_party_wide_claim_proof_assignment_v1,
    build_party_wide_claim_proof_move_v1,
    build_party_wide_claim_proof_request_v1,
    build_unavailable_party_wide_claim_proof_preparation_v1,
    build_unavailable_party_wide_claim_proof_result_v1,
    build_valid_party_wide_claim_proof_result_v1,
    prepare_party_wide_claim_proof_request_v1,
)
from skat_ai.rules import get_legal_cards, get_trick_points, get_trick_winner
from skat_ai.settlement_normative_matrix import (
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1,
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1_QUANTIFIERS,
    SETTLEMENT_NORMATIVE_MATRIX_VERSION,
    SUPPORTED_AS_IS,
    V1_NOT_SUPPORTED_CLAIM_CASE_IDS,
    get_normative_settlement_case,
    get_normative_settlement_cases,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYER_IDS = ("player-a", "player-b", "player-c")
SESSION_EXAMPLE_NAMES = {
    "session_command_record_play.json",
    "session_correction_record_play.json",
    "session_create_live.json",
    "session_create_retrospective.json",
    "session_live_persistence.json",
    "session_retrospective_persistence.json",
}


def _build_historical_input(
    *,
    game_type: str = "grand",
    hand_game: bool = False,
    ouvert: bool = False,
    declarer_player_id: str = "player-b",
    bid_value: int | None = 18,
) -> dict:
    deck = get_full_deck()
    initial_hands = {
        "player-a": deck[0:10],
        "player-b": deck[10:20],
        "player-c": deck[20:30],
    }
    skat = deck[30:32]
    discarded_cards = [] if hand_game else initial_hands[declarer_player_id][:2]
    playable_hands = copy.deepcopy(initial_hands)
    if not hand_game:
        playable_hands[declarer_player_id].extend(skat)
        for card in discarded_cards:
            playable_hands[declarer_player_id].remove(card)

    tricks = []
    leader_player_id = "player-a"
    for trick_number in range(1, 11):
        leader_index = PLAYER_IDS.index(leader_player_id)
        player_order = tuple(PLAYER_IDS[(leader_index + offset) % 3] for offset in range(3))
        trick_cards = []
        plays = []
        for player_id in player_order:
            legal_cards = get_legal_cards(playable_hands[player_id], trick_cards, game_type)
            card = legal_cards[0]
            playable_hands[player_id].remove(card)
            trick_cards.append(card)
            plays.append({"player_id": player_id, "card": card})
        leader_player_id = plays[get_trick_winner(trick_cards, game_type)]["player_id"]
        tricks.append(
            {
                "trick_number": trick_number,
                "leader_player_id": player_order[0],
                "plays": plays,
            }
        )

    declaration = {
        "game_type": game_type,
        "hand_game": hand_game,
        "ouvert": ouvert,
        "bid_value": bid_value,
    }
    return {
        "schema_version": 1,
        "game_id": f"claim-{game_type}-{hand_game}-{ouvert}",
        "players": [
            {
                "player_id": "player-a",
                "player_label": "Alice",
                "seat": "forehand",
                "initial_hand": initial_hands["player-a"],
            },
            {
                "player_id": "player-b",
                "seat": "middlehand",
                "initial_hand": initial_hands["player-b"],
            },
            {
                "player_id": "player-c",
                "player_label": "Carol",
                "seat": "rearhand",
                "initial_hand": initial_hands["player-c"],
            },
        ],
        "skat": skat,
        "declarer_player_id": declarer_player_id,
        "declaration": declaration,
        "discarded_cards": discarded_cards,
        "game_end_reason": "normal_completion",
        "tricks": tricks,
    }


def _prefix_tricks(
    tricks: tuple[HistoricalTrick, ...], play_count: int
) -> tuple[HistoricalTrick, ...]:
    remaining = play_count
    prefix = []
    for trick in tricks:
        if remaining == 0:
            break
        selected_count = min(remaining, len(trick.plays))
        prefix.append(replace(trick, plays=trick.plays[:selected_count]))
        remaining -= selected_count
        if selected_count < len(trick.plays):
            break
    assert remaining == 0
    return tuple(prefix)


def _build_evidence(
    *,
    game_type: str = "grand",
    hand_game: bool = False,
    ouvert: bool = False,
    play_count: int = 27,
    bid_value: int | None = 18,
) -> tuple[PartyWideClaimEvidenceV1, object]:
    record = build_historical_game_record(
        _build_historical_input(
            game_type=game_type,
            hand_game=hand_game,
            ouvert=ouvert,
            bid_value=bid_value,
        )
    )
    evidence = build_party_wide_claim_evidence_v1(
        game_id=record.game_id,
        players=record.players,
        skat=record.skat,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        discarded_cards=record.discarded_cards,
        tricks=_prefix_tricks(record.tricks, play_count),
    )
    return evidence, record


def _claim_for_party(
    evidence: PartyWideClaimEvidenceV1, claiming_party: str
) -> PartyWideAllRemainingTricksClaimV1:
    claimant = (
        evidence.declarer_player_id
        if claiming_party == "declarer"
        else next(
            player.player_id
            for player in evidence.players
            if player.player_id != evidence.declarer_player_id
        )
    )
    return build_party_wide_all_remaining_tricks_claim_v1(
        claimant_player_id=claimant,
        claiming_party=claiming_party,
    )


def _party_for_trick_winner(record: object, trick: HistoricalTrick) -> str:
    winner_index = get_trick_winner(
        [play.card for play in trick.plays], record.declaration.game_type
    )
    return (
        "declarer"
        if trick.plays[winner_index].player_id == record.declarer_player_id
        else "defenders"
    )


def _build_line_for_trick(
    record: object, trick: HistoricalTrick
) -> tuple[PartyWideClaimProofMoveV1, ...]:
    winner_index = get_trick_winner(
        [play.card for play in trick.plays], record.declaration.game_type
    )
    winner_id = trick.plays[winner_index].player_id
    winner_party = "declarer" if winner_id == record.declarer_player_id else "defenders"
    return tuple(
        build_party_wide_claim_proof_move_v1(
            player_id=play.player_id,
            card=play.card,
            completed_trick_winner_player_id=(winner_id if index == len(trick.plays) - 1 else None),
            completed_trick_winner_party=(winner_party if index == len(trick.plays) - 1 else None),
        )
        for index, play in enumerate(trick.plays)
    )


def _find_owned_bedienpflicht_violation(
    record: object, *, minimum_play_count: int
) -> tuple[int, HistoricalPlay, str]:
    hands = {player.player_id: list(player.initial_hand) for player in record.players}
    if not record.declaration.hand_game:
        hands[record.declarer_player_id].extend(record.skat)
        for card in record.discarded_cards:
            hands[record.declarer_player_id].remove(card)
    played_count = 0
    for trick in record.tricks:
        current_cards = []
        for play in trick.plays:
            legal_cards = get_legal_cards(
                hands[play.player_id], current_cards, record.declaration.game_type
            )
            illegal_owned_cards = tuple(
                card for card in hands[play.player_id] if card not in legal_cards
            )
            if played_count >= minimum_play_count and illegal_owned_cards:
                return played_count, play, illegal_owned_cards[0]
            hands[play.player_id].remove(play.card)
            current_cards.append(play.card)
            played_count += 1
    raise AssertionError("The deterministic fixture needs one Bedienpflicht alternative.")


def test_versions_vocabularies_policies_quantifiers_and_bound_are_exact() -> None:
    assert (
        PARTY_WIDE_CLAIM_VERSION,
        PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
        PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION,
        PARTY_WIDE_CLAIM_PROOF_REQUEST_VERSION,
        PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION,
        PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
    ) == (1, 1, 1, 1, 1, 1)
    assert PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND == ("party_wide_all_remaining_tricks_claim")
    assert PARTY_WIDE_CLAIMING_PARTIES == ("declarer", "defenders")
    assert PARTY_WIDE_CLAIM_PROOF_PREPARATION_STATUSES == (
        "available",
        "unavailable",
    )
    assert PARTY_WIDE_CLAIM_PROOF_STATUSES == ("valid", "invalid", "unavailable")
    assert PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS == (
        "party_wide_claim_evidence_incomplete",
        "party_wide_claim_evidence_contradictory",
        "party_wide_claim_unsupported_contract",
        "party_wide_claim_unsupported_turn_phase",
        "party_wide_claim_no_unresolved_tricks",
        "party_wide_claim_unresolved_trick_limit_exceeded",
        "party_wide_claim_proof_not_executed",
    )
    assert (
        PARTY_WIDE_CLAIM_SCOPE_POLICY,
        PARTY_WIDE_CLAIM_PARTY_POLICY,
        PARTY_WIDE_CLAIM_EVIDENCE_POLICY,
        PARTY_WIDE_CLAIM_EXACT_STATE_POLICY,
        PARTY_WIDE_CLAIM_PROOF_POLICY,
        PARTY_WIDE_CLAIM_BOUND_POLICY,
        PARTY_WIDE_CLAIM_VALID_POLICY,
        PARTY_WIDE_CLAIM_INVALID_POLICY,
        PARTY_WIDE_CLAIM_UNAVAILABLE_POLICY,
        PARTY_WIDE_CLAIM_SEARCH_POLICY,
        PARTY_WIDE_CLAIM_PUBLIC_POLICY,
    ) == (
        "structured_retrospective_complete_world_only",
        "claimant_must_belong_to_claiming_party",
        "complete_deal_and_exact_legal_play_prefix",
        "historical_replay_then_exact_state_validation",
        "claiming_party_existential_opposing_party_universal",
        "at_most_five_unresolved_tricks_including_current",
        "valid_proof_assigns_every_unresolved_trick_to_claiming_party",
        "invalid_proof_creates_no_terminal_outcome",
        "unavailable_proof_creates_no_terminal_outcome",
        "dedicated_exact_claim_proof_without_search_fallback",
        "private_internal_contract_without_public_surface",
    )
    assert PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS == 5
    assert (
        PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS
        == (PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1_QUANTIFIERS)
        == (("claiming_party", "existential"), ("opposing_party", "universal"))
    )


def test_structured_claim_is_strict_frozen_slotted_and_deterministic() -> None:
    claim = build_party_wide_all_remaining_tricks_claim_v1(
        claimant_player_id="Player-A", claiming_party="declarer"
    )
    assert [field.name for field in fields(claim)] == [
        "party_wide_claim_version",
        "kind",
        "claimant_player_id",
        "claiming_party",
    ]
    assert not hasattr(claim, "__dict__")
    assert claim.to_dict() == {
        "party_wide_claim_version": 1,
        "kind": "party_wide_all_remaining_tricks_claim",
        "claimant_player_id": "Player-A",
        "claiming_party": "declarer",
    }
    assert claim.to_dict() is not claim.to_dict()
    json.dumps(claim.to_dict(), allow_nan=False)
    with pytest.raises(FrozenInstanceError):
        claim.claiming_party = "defenders"  # type: ignore[misc]
    with pytest.raises(TypeError):
        PartyWideAllRemainingTricksClaimV1(1, "kind", "Player-A", "declarer")  # type: ignore[misc]


@pytest.mark.parametrize("player_id", ["", " Player-A", "Player-A ", "me", "left", "right"])
def test_structured_claim_rejects_invalid_or_relative_claimant_ids(player_id: str) -> None:
    with pytest.raises(ValueError):
        build_party_wide_all_remaining_tricks_claim_v1(
            claimant_player_id=player_id, claiming_party="declarer"
        )


def test_structured_claim_rejects_wrong_version_kind_and_party() -> None:
    common = {
        "party_wide_claim_version": 1,
        "kind": PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND,
        "claimant_player_id": "player-a",
        "claiming_party": "declarer",
    }
    for changes in (
        {"party_wide_claim_version": True},
        {"party_wide_claim_version": 2},
        {"kind": "free_text_claim"},
        {"claiming_party": "player"},
    ):
        with pytest.raises(ValueError):
            PartyWideAllRemainingTricksClaimV1(**(common | changes))


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
def test_exact_evidence_supports_suit_grand_and_all_null_variants(
    game_type: str, hand_game: bool, ouvert: bool
) -> None:
    evidence, _ = _build_evidence(
        game_type=game_type,
        hand_game=hand_game,
        ouvert=ouvert,
        play_count=15,
    )
    assert evidence.declaration.game_type == game_type
    assert evidence.declaration.hand_game is hand_game
    assert evidence.declaration.ouvert is ouvert
    assert evidence.remaining_trick_count == 5
    assert evidence.unresolved_card_count == 15
    assert len(evidence.players) == 3
    assert sum(len(player.initial_hand) for player in evidence.players) == 30


@pytest.mark.parametrize("play_count", [0, 3, 13, 14, 27, 28, 29, 30])
def test_evidence_derives_exact_prefix_remaining_and_point_facts(play_count: int) -> None:
    evidence, _ = _build_evidence(play_count=play_count)
    completed_count = play_count // 3
    current_count = play_count % 3
    assert evidence.played_card_count == play_count
    assert len(evidence.completed_tricks) == completed_count
    assert (len(evidence.current_trick.plays) if evidence.current_trick else 0) == (current_count)
    assert evidence.remaining_trick_count == 10 - completed_count
    assert evidence.unresolved_card_count == 3 * evidence.remaining_trick_count
    assert sum(len(cards) for _, cards in evidence.remaining_hands) + current_count == (
        evidence.unresolved_card_count
    )
    assert evidence.declarer_completed_tricks + evidence.defender_completed_tricks == (
        completed_count
    )
    assert evidence.declarer_trick_points + evidence.defender_trick_points == sum(
        trick.trick_points for trick in evidence.completed_tricks
    )
    assert (
        evidence.declarer_trick_points
        + evidence.defender_trick_points
        + evidence.unresolved_card_points
        + get_trick_points(list(evidence.out_of_play_cards))
        == 120
    )
    if evidence.current_trick is not None:
        assert evidence.next_player_id == evidence.current_trick.next_player_id


def test_hand_and_non_hand_out_of_play_cards_are_exact() -> None:
    hand, _ = _build_evidence(hand_game=True)
    non_hand, _ = _build_evidence(hand_game=False)
    assert hand.discarded_cards == ()
    assert hand.out_of_play_cards == hand.skat
    assert non_hand.discarded_cards
    assert non_hand.out_of_play_cards == non_hand.discarded_cards


def test_evidence_is_builder_controlled_canonical_and_defensively_serialized() -> None:
    evidence, _ = _build_evidence(play_count=14)
    assert [player.seat for player in evidence.players] == [
        "forehand",
        "middlehand",
        "rearhand",
    ]
    deck_order = {card: index for index, card in enumerate(get_full_deck())}
    for player in evidence.players:
        assert tuple(sorted(player.initial_hand, key=deck_order.__getitem__)) == (
            player.initial_hand
        )
    for _, cards in evidence.remaining_hands:
        assert tuple(sorted(cards, key=deck_order.__getitem__)) == cards
    first = evidence.to_dict()
    second = evidence.to_dict()
    first["players"][0]["initial_hand"].clear()
    first["remaining_hands"]["player-a"].clear()
    assert len(second["players"][0]["initial_hand"]) == 10
    assert second["remaining_hands"]["player-a"]
    assert list(second) == [field.name for field in fields(evidence)]
    json.dumps(second, allow_nan=False)
    assert not hasattr(evidence, "__dict__")
    with pytest.raises(TypeError, match="focused builder"):
        PartyWideClaimEvidenceV1()


def test_evidence_replays_historical_prefix_exactly_once(monkeypatch) -> None:
    record = build_historical_game_record(_build_historical_input())
    original = evidence_module.replay_historical_play_prefix
    calls = []

    def counted(source):
        calls.append(source)
        return original(source)

    monkeypatch.setattr(evidence_module, "replay_historical_play_prefix", counted)
    build_party_wide_claim_evidence_v1(
        game_id=record.game_id,
        players=record.players,
        skat=record.skat,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        discarded_cards=record.discarded_cards,
        tricks=_prefix_tricks(record.tricks, 17),
    )
    assert len(calls) == 1


def test_evidence_rejects_complete_deal_player_and_discard_failures() -> None:
    evidence, record = _build_evidence()
    del evidence
    common = {
        "game_id": record.game_id,
        "players": record.players,
        "skat": record.skat,
        "declarer_player_id": record.declarer_player_id,
        "declaration": record.declaration,
        "discarded_cards": record.discarded_cards,
        "tricks": _prefix_tricks(record.tricks, 27),
    }
    mutations = (
        {"players": record.players[:2]},
        {"players": (*record.players[:2], replace(record.players[2], player_id="player-a"))},
        {"players": (*record.players[:2], replace(record.players[2], seat="forehand"))},
        {
            "players": (
                replace(
                    record.players[0],
                    initial_hand=record.players[0].initial_hand[:-1],
                ),
                *record.players[1:],
            )
        },
        {"skat": record.skat[:1]},
        {"discarded_cards": ()},
        {"discarded_cards": (record.players[2].initial_hand[0], record.discarded_cards[0])},
    )
    for mutation in mutations:
        with pytest.raises(ValueError):
            build_party_wide_claim_evidence_v1(**(common | mutation))


def test_evidence_rejects_matador_trick_order_ownership_and_bedienpflicht_failures() -> None:
    _, record = _build_evidence(play_count=27)
    common = {
        "game_id": record.game_id,
        "players": record.players,
        "skat": record.skat,
        "declarer_player_id": record.declarer_player_id,
        "declaration": record.declaration,
        "discarded_cards": record.discarded_cards,
        "tricks": _prefix_tricks(record.tricks, 27),
    }
    first = common["tricks"][0]
    wrong_number = (replace(first, trick_number=2), *common["tricks"][1:])
    wrong_leader = (
        replace(first, leader_player_id="player-c"),
        *common["tricks"][1:],
    )
    wrong_order = (
        replace(first, plays=(first.plays[1], first.plays[0], first.plays[2])),
        *common["tricks"][1:],
    )
    wrong_owner = (
        replace(
            first,
            plays=(
                replace(first.plays[0], card=record.players[1].initial_hand[-1]),
                *first.plays[1:],
            ),
        ),
        *common["tricks"][1:],
    )
    incomplete_nonfinal = (
        replace(first, plays=first.plays[:2]),
        *common["tricks"][1:],
    )
    for tricks in (
        wrong_number,
        wrong_leader,
        wrong_order,
        wrong_owner,
        incomplete_nonfinal,
    ):
        with pytest.raises(ValueError):
            build_party_wide_claim_evidence_v1(**(common | {"tricks": tricks}))
    wrong_matadors = replace(
        record.declaration,
        matadors=(record.declaration.matadors % 4) + 1,
    )
    if wrong_matadors.matadors == record.declaration.matadors:
        wrong_matadors = replace(record.declaration, matadors=4)
    with pytest.raises(ValueError, match="matadors"):
        build_party_wide_claim_evidence_v1(**(common | {"declaration": wrong_matadors}))

    before_count, _, illegal_card = _find_owned_bedienpflicht_violation(
        record, minimum_play_count=0
    )
    illegal_prefix = list(_prefix_tricks(record.tricks, before_count + 1))
    final_prefix_trick = illegal_prefix[-1]
    illegal_prefix[-1] = replace(
        final_prefix_trick,
        plays=(
            *final_prefix_trick.plays[:-1],
            replace(final_prefix_trick.plays[-1], card=illegal_card),
        ),
    )
    with pytest.raises(ValueError, match="illegally plays"):
        build_party_wide_claim_evidence_v1(**(common | {"tricks": tuple(illegal_prefix)}))


def test_claimant_membership_and_party_reconciliation_are_exact() -> None:
    evidence, _ = _build_evidence()
    declarer_claim = _claim_for_party(evidence, "declarer")
    defender_ids = tuple(
        player.player_id
        for player in evidence.players
        if player.player_id != evidence.declarer_player_id
    )
    validate_party_wide_claim_against_evidence_v1(declarer_claim, evidence)
    for defender_id in defender_ids:
        validate_party_wide_claim_against_evidence_v1(
            build_party_wide_all_remaining_tricks_claim_v1(
                claimant_player_id=defender_id, claiming_party="defenders"
            ),
            evidence,
        )
    contradictions = (
        build_party_wide_all_remaining_tricks_claim_v1(
            claimant_player_id=evidence.declarer_player_id,
            claiming_party="defenders",
        ),
        build_party_wide_all_remaining_tricks_claim_v1(
            claimant_player_id=defender_ids[0], claiming_party="declarer"
        ),
        build_party_wide_all_remaining_tricks_claim_v1(
            claimant_player_id="unknown-player", claiming_party="defenders"
        ),
    )
    for claim in contradictions:
        with pytest.raises(ValueError):
            validate_party_wide_claim_against_evidence_v1(claim, evidence)


@pytest.mark.parametrize("claiming_party", PARTY_WIDE_CLAIMING_PARTIES)
def test_exact_state_context_maps_and_reconciles_every_exact_fact(
    claiming_party: str, monkeypatch
) -> None:
    evidence, _ = _build_evidence(play_count=17)
    claim = _claim_for_party(evidence, claiming_party)
    original = evidence_module.build_exact_search_state
    calls = []

    def counted(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(evidence_module, "build_exact_search_state", counted)
    context = build_party_wide_claim_exact_state_context_v1(claim, evidence)
    assert len(calls) == 1
    stable_to_flat = dict(context.stable_to_flat_player_map)
    assert stable_to_flat[evidence.declarer_player_id] == "me"
    assert context.claimant_flat_player == stable_to_flat[claim.claimant_player_id]
    assert set(context.claiming_party_flat_players).isdisjoint(context.opposing_party_flat_players)
    assert set(context.claiming_party_flat_players) | set(context.opposing_party_flat_players) == {
        "me",
        "left",
        "right",
    }
    state = context.exact_state
    assert state.declaration == evidence.declaration
    assert state.next_player == stable_to_flat[evidence.next_player_id]
    assert state.remaining_tricks == evidence.remaining_trick_count
    assert state.declarer_trick_points == evidence.declarer_trick_points
    assert state.defender_trick_points == evidence.defender_trick_points
    assert state.out_of_play_cards == evidence.out_of_play_cards
    assert list(context.to_dict()) == [field.name for field in fields(context)]
    json.dumps(context.to_dict(), allow_nan=False)
    assert not hasattr(context, "__dict__")
    with pytest.raises(TypeError, match="focused builder"):
        PartyWideClaimExactStateContextV1()


@pytest.mark.parametrize("remaining_tricks", range(0, 11))
def test_proof_preparation_enforces_zero_five_and_six_trick_boundaries(
    remaining_tricks: int,
) -> None:
    evidence, _ = _build_evidence(play_count=30 - 3 * remaining_tricks)
    claim = _claim_for_party(evidence, "declarer")
    preparation = prepare_party_wide_claim_proof_request_v1(claim, evidence)
    if remaining_tricks == 0:
        assert preparation.status == "unavailable"
        assert preparation.unavailable_reason == ("party_wide_claim_no_unresolved_tricks")
    elif remaining_tricks <= 5:
        assert preparation.status == "available"
        assert preparation.unavailable_reason is None
        assert preparation.request is not None
        assert preparation.request.exact_state_context.exact_state.remaining_tricks == (
            remaining_tricks
        )
    else:
        assert preparation.status == "unavailable"
        assert preparation.unavailable_reason == (
            "party_wide_claim_unresolved_trick_limit_exceeded"
        )
        assert preparation.request is None


@pytest.mark.parametrize(
    ("play_count", "expected_remaining", "expected_status"),
    [(13, 6, "unavailable"), (16, 5, "available")],
)
def test_current_incomplete_trick_counts_toward_preparation_bound(
    play_count: int, expected_remaining: int, expected_status: str
) -> None:
    evidence, _ = _build_evidence(play_count=play_count)
    assert evidence.current_trick is not None
    assert evidence.remaining_trick_count == expected_remaining
    assert (
        prepare_party_wide_claim_proof_request_v1(
            _claim_for_party(evidence, "defenders"), evidence
        ).status
        == expected_status
    )


def test_null_overbid_is_a_normal_unsupported_contract_preparation() -> None:
    evidence, _ = _build_evidence(game_type="null", play_count=27, bid_value=24)
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, "declarer"), evidence
    )
    assert preparation.status == "unavailable"
    assert preparation.unavailable_reason == "party_wide_claim_unsupported_contract"


def test_proof_request_retains_matrix_policy_quantifiers_and_exact_context() -> None:
    evidence, _ = _build_evidence(play_count=18)
    claim = _claim_for_party(evidence, "defenders")
    preparation = prepare_party_wide_claim_proof_request_v1(claim, evidence)
    request = preparation.request
    assert isinstance(request, PartyWideClaimProofRequestV1)
    assert request.proof_policy == PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1
    assert request.proof_quantifiers == (PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1_QUANTIFIERS)
    assert request.maximum_unresolved_tricks == 5
    assert request.claim is claim
    assert request.evidence is evidence
    assert request.exact_state_context.exact_state.remaining_tricks == 4
    forbidden = {
        "search_budget",
        "seed",
        "timeout",
        "sample_count",
        "compatible_worlds",
        "recommendation",
    }
    assert forbidden.isdisjoint(field.name for field in fields(request))
    first = request.to_dict()
    second = request.to_dict()
    first["claim"]["claimant_player_id"] = "changed"
    assert second["claim"]["claimant_player_id"] == claim.claimant_player_id
    json.dumps(second, allow_nan=False)
    with pytest.raises(TypeError, match="focused builder"):
        PartyWideClaimProofRequestV1()


def test_direct_proof_request_rejects_mismatched_context_and_unsupported_contract() -> None:
    grand_evidence, _ = _build_evidence(game_type="grand", play_count=27)
    grand_claim = _claim_for_party(grand_evidence, "declarer")
    clubs_evidence, _ = _build_evidence(game_type="clubs", play_count=27)
    clubs_context = build_party_wide_claim_exact_state_context_v1(grand_claim, clubs_evidence)
    with pytest.raises(ValueError, match="Declaration contradicts"):
        build_party_wide_claim_proof_request_v1(
            claim=grand_claim,
            evidence=grand_evidence,
            exact_state_context=clubs_context,
        )

    null_evidence, _ = _build_evidence(game_type="null", play_count=27, bid_value=24)
    null_claim = _claim_for_party(null_evidence, "declarer")
    null_context = build_party_wide_claim_exact_state_context_v1(null_claim, null_evidence)
    with pytest.raises(ValueError, match="supported Claim contract"):
        build_party_wide_claim_proof_request_v1(
            claim=null_claim,
            evidence=null_evidence,
            exact_state_context=null_context,
        )


@pytest.mark.parametrize("reason", PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS)
def test_strict_unavailable_preparation_accepts_only_canonical_reasons(reason: str) -> None:
    evidence, _ = _build_evidence(play_count=27)
    claim = _claim_for_party(evidence, "declarer")
    source_reason = reason in PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS[:2]
    preparation = build_unavailable_party_wide_claim_proof_preparation_v1(
        claim=claim,
        unavailable_reason=reason,
        evidence=None if source_reason else evidence,
    )
    assert preparation.status == "unavailable"
    assert preparation.unavailable_reason == reason
    assert preparation.request is None
    assert (preparation.evidence is None) is source_reason
    with pytest.raises(ValueError):
        build_unavailable_party_wide_claim_proof_preparation_v1(
            claim=claim,
            unavailable_reason="bounded_search_unavailable",
            evidence=evidence,
        )


def test_proof_move_winner_fields_are_strict_and_deterministic() -> None:
    move = build_party_wide_claim_proof_move_v1(player_id="player-a", card="CA")
    assert move.to_dict() == {
        "player_id": "player-a",
        "card": "CA",
        "completed_trick_winner_player_id": None,
        "completed_trick_winner_party": None,
    }
    completing = build_party_wide_claim_proof_move_v1(
        player_id="player-c",
        card="C7",
        completed_trick_winner_player_id="player-a",
        completed_trick_winner_party="declarer",
    )
    assert completing.completed_trick_winner_party == "declarer"
    for kwargs in (
        {"player_id": "me", "card": "CA"},
        {"player_id": "player-a", "card": "XX"},
        {
            "player_id": "player-a",
            "card": "CA",
            "completed_trick_winner_player_id": "player-a",
        },
        {
            "player_id": "player-a",
            "card": "CA",
            "completed_trick_winner_party": "declarer",
        },
    ):
        with pytest.raises(ValueError):
            build_party_wide_claim_proof_move_v1(**kwargs)
    with pytest.raises(TypeError, match="focused builder"):
        PartyWideClaimProofMoveV1()


def test_valid_invalid_and_unavailable_results_enforce_exact_relationships() -> None:
    evidence, record = _build_evidence(play_count=27)
    final_trick = record.tricks[-1]
    winner_party = _party_for_trick_winner(record, final_trick)
    line = _build_line_for_trick(record, final_trick)

    valid_claim = _claim_for_party(evidence, winner_party)
    valid_preparation = prepare_party_wide_claim_proof_request_v1(valid_claim, evidence)
    assignment = build_party_wide_claim_proof_assignment_v1(
        preparation=valid_preparation,
        recipient_party=winner_party,
        assigned_trick_count=evidence.remaining_trick_count,
        assigned_card_count=evidence.unresolved_card_count,
        assigned_card_points=evidence.unresolved_card_points,
    )
    valid = build_valid_party_wide_claim_proof_result_v1(
        preparation=valid_preparation,
        evaluated_state_count=4,
        memoized_state_count=3,
        terminal_state_count=1,
        assignment=assignment,
        representative_line=line,
    )
    assert valid.status == "valid"
    assert valid.proof_complete is True
    assert valid.claim_satisfied is True
    assert valid.unavailable_reason is None
    assert valid.counterexample_found is False
    assert valid.assignment is assignment
    assert valid.representative_line == line

    opposing_party = "defenders" if winner_party == "declarer" else "declarer"
    invalid_preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, opposing_party), evidence
    )
    invalid = build_invalid_party_wide_claim_proof_result_v1(
        preparation=invalid_preparation,
        evaluated_state_count=2,
        memoized_state_count=1,
        terminal_state_count=1,
        representative_line=line,
    )
    assert invalid.status == "invalid"
    assert invalid.proof_complete is True
    assert invalid.claim_satisfied is False
    assert invalid.assignment is None
    assert invalid.counterexample_found is True

    unavailable = build_unavailable_party_wide_claim_proof_result_v1(
        preparation=valid_preparation,
        unavailable_reason="party_wide_claim_proof_not_executed",
    )
    assert unavailable.status == "unavailable"
    assert unavailable.proof_complete is False
    assert unavailable.claim_satisfied is None
    assert unavailable.assignment is None
    assert unavailable.representative_line == ()
    assert (
        unavailable.evaluated_state_count,
        unavailable.memoized_state_count,
        unavailable.terminal_state_count,
    ) == (0, 0, 0)
    for result in (valid, invalid, unavailable):
        assert list(result.to_dict()) == [field.name for field in fields(result)]
        json.dumps(result.to_dict(), allow_nan=False)


def test_assignment_and_complete_result_counters_are_strict() -> None:
    evidence, record = _build_evidence(play_count=27)
    winner_party = _party_for_trick_winner(record, record.tricks[-1])
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, winner_party), evidence
    )
    valid_values = {
        "preparation": preparation,
        "recipient_party": winner_party,
        "assigned_trick_count": evidence.remaining_trick_count,
        "assigned_card_count": evidence.unresolved_card_count,
        "assigned_card_points": evidence.unresolved_card_points,
    }
    assignment = build_party_wide_claim_proof_assignment_v1(**valid_values)
    assert isinstance(assignment, PartyWideClaimProofAssignmentV1)
    for field_name in (
        "assigned_trick_count",
        "assigned_card_count",
        "assigned_card_points",
    ):
        with pytest.raises(ValueError):
            build_party_wide_claim_proof_assignment_v1(**(valid_values | {field_name: True}))
    line = _build_line_for_trick(record, record.tricks[-1])
    for counters in (
        {
            "evaluated_state_count": True,
            "memoized_state_count": 0,
            "terminal_state_count": 1,
        },
        {
            "evaluated_state_count": 1,
            "memoized_state_count": 2,
            "terminal_state_count": 1,
        },
        {
            "evaluated_state_count": 1,
            "memoized_state_count": 1,
            "terminal_state_count": 0,
        },
    ):
        with pytest.raises(ValueError):
            build_valid_party_wide_claim_proof_result_v1(
                preparation=preparation,
                assignment=assignment,
                representative_line=line,
                **counters,
            )


def test_representative_line_rejects_wrong_chronology_ownership_and_winner() -> None:
    evidence, record = _build_evidence(play_count=27)
    final_trick = record.tricks[-1]
    winner_party = _party_for_trick_winner(record, final_trick)
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, winner_party), evidence
    )
    assignment = build_party_wide_claim_proof_assignment_v1(
        preparation=preparation,
        recipient_party=winner_party,
        assigned_trick_count=evidence.remaining_trick_count,
        assigned_card_count=evidence.unresolved_card_count,
        assigned_card_points=evidence.unresolved_card_points,
    )
    line = _build_line_for_trick(record, final_trick)
    wrong_order = (line[1], line[0], line[2])
    wrong_owner = (
        build_party_wide_claim_proof_move_v1(
            player_id=line[0].player_id,
            card=line[1].card,
        ),
        line[1],
        line[2],
    )
    wrong_winner_id = next(
        player.player_id
        for player in evidence.players
        if player.player_id != line[2].completed_trick_winner_player_id
    )
    wrong_winner_party = (
        "declarer" if wrong_winner_id == evidence.declarer_player_id else "defenders"
    )
    wrong_winner = (
        line[0],
        line[1],
        build_party_wide_claim_proof_move_v1(
            player_id=line[2].player_id,
            card=line[2].card,
            completed_trick_winner_player_id=wrong_winner_id,
            completed_trick_winner_party=wrong_winner_party,
        ),
    )
    for invalid_line in (wrong_order, wrong_owner, wrong_winner):
        with pytest.raises(ValueError):
            build_valid_party_wide_claim_proof_result_v1(
                preparation=preparation,
                evaluated_state_count=1,
                memoized_state_count=1,
                terminal_state_count=1,
                assignment=assignment,
                representative_line=invalid_line,
            )


def test_representative_line_rejects_owned_bedienpflicht_violation() -> None:
    _, record = _build_evidence(play_count=27)
    before_count, play, illegal_card = _find_owned_bedienpflicht_violation(
        record, minimum_play_count=15
    )
    evidence = build_party_wide_claim_evidence_v1(
        game_id=record.game_id,
        players=record.players,
        skat=record.skat,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        discarded_cards=record.discarded_cards,
        tricks=_prefix_tricks(record.tricks, before_count),
    )
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, "declarer"), evidence
    )
    assert preparation.status == "available"
    illegal_move = build_party_wide_claim_proof_move_v1(
        player_id=play.player_id,
        card=illegal_card,
    )
    with pytest.raises(ValueError, match="Bedienpflicht"):
        build_invalid_party_wide_claim_proof_result_v1(
            preparation=preparation,
            evaluated_state_count=1,
            memoized_state_count=1,
            terminal_state_count=1,
            representative_line=(illegal_move,),
        )


def test_claim_modules_have_no_proof_search_runtime_or_settlement_execution() -> None:
    module_paths = tuple(
        PROJECT_ROOT / "src" / "skat_ai" / name
        for name in (
            "party_wide_claim_contracts.py",
            "party_wide_claim_evidence.py",
            "party_wide_claim_proof_contracts.py",
        )
    )
    forbidden_import_fragments = (
        "api",
        "cli",
        "compatible_world",
        "exact_rest_trick_proof",
        "final_settlement",
        "game_end",
        "perfect_information_minimax",
        "recommender",
        "replay_coaching",
    )
    forbidden_calls = {
        "apply_exact_search_card",
        "get_exact_search_legal_cards",
        "perfect_information_minimax",
        "compatible_world_minimax",
        "prove_defender_rest_tricks",
        "build_final_settlement_summary",
    }
    for path in module_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = tuple(
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        assert not any(
            fragment in imported for fragment in forbidden_import_fragments for imported in imports
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert forbidden_calls.isdisjoint(calls)


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


def test_matrix_runtime_public_cli_schema_example_and_package_baselines_are_current() -> None:
    cases = get_normative_settlement_cases()
    approved = get_normative_settlement_case(
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
    )
    assert SETTLEMENT_NORMATIVE_MATRIX_VERSION == 3
    assert len(cases) == 61
    assert approved.implementation_status == SUPPORTED_AS_IS
    assert approved.implementation_modules == (
        "skat_ai.historical_game_end",
        "skat_ai.historical_party_wide_claim",
        "skat_ai.party_wide_claim_proof_executor",
        "skat_ai.party_wide_claim_adjudication",
    )
    assert approved.stable_unavailable_reason is None
    assert approved.proof_policy == PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1
    assert approved.proof_maximum_unresolved_tricks == 5
    assert len(V1_NOT_SUPPORTED_CLAIM_CASE_IDS) == 13
    assert _runtime_union_kinds(GameShortening) == {
        "declarer_concession",
        "defender_concession",
        "declarer_card_exposure",
        "defender_open_play",
        "open_card_throw",
    }
    assert len(HISTORICAL_GAME_END_REASONS) == 7
    assert len(VALID_GAME_END_REASONS) == 6
    assert skat_ai.__all__ == ("api", "errors", "__version__")
    for name in (
        "PartyWideAllRemainingTricksClaimV1",
        "PartyWideClaimEvidenceV1",
        "PartyWideClaimProofRequestV1",
        "PartyWideClaimProofResultV1",
    ):
        assert name not in api_v1.__all__
    assert len(WorkflowV1) == 7
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 65
    assert (
        len(tuple((PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob("*.schema.json")))
        == 65
    )
    assert {
        path.name for path in (PROJECT_ROOT / "examples").glob("session_*.json")
    } == SESSION_EXAMPLE_NAMES
    assert len(SCENARIOS) == 88
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["version"] == skat_ai.__version__ == "0.16.0"
    assert project["requires-python"] == ">=3.13"
    assert project["scripts"] == {"skat-ai": "skat_ai.cli:main"}


def test_new_values_are_frozen_slotted_and_builder_controlled() -> None:
    evidence, record = _build_evidence(play_count=27)
    winner_party = _party_for_trick_winner(record, record.tricks[-1])
    preparation = prepare_party_wide_claim_proof_request_v1(
        _claim_for_party(evidence, winner_party), evidence
    )
    assignment = build_party_wide_claim_proof_assignment_v1(
        preparation=preparation,
        recipient_party=winner_party,
        assigned_trick_count=evidence.remaining_trick_count,
        assigned_card_count=evidence.unresolved_card_count,
        assigned_card_points=evidence.unresolved_card_points,
    )
    move = _build_line_for_trick(record, record.tricks[-1])[0]
    for value in (
        evidence,
        preparation.request.exact_state_context,
        preparation.request,
        preparation,
        move,
        assignment,
    ):
        assert not hasattr(value, "__dict__")
        with pytest.raises(FrozenInstanceError):
            value.__setattr__(fields(value)[0].name, None)
    for value_type in (
        PartyWideClaimProofPreparationV1,
        PartyWideClaimProofAssignmentV1,
        PartyWideClaimProofResultV1,
    ):
        with pytest.raises(TypeError, match="focused builder"):
            value_type()
