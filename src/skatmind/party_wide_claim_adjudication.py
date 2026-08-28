from skatmind.deck import get_full_deck
from skatmind.declarer_card_exposure import (
    get_declared_mandatory_play_level,
    get_play_level_rank,
)
from skatmind.errors import SkatMindInvariantError
from skatmind.exact_search_state import ExactSearchState
from skatmind.final_settlement import (
    build_final_settlement_summary,
    is_schneider_announced,
)
from skatmind.game_decision import (
    determine_decision_state_before_game_end,
    get_mandatory_level_source,
)
from skatmind.game_declaration import GameDeclaration
from skatmind.game_result import (
    apply_completed_null_contract_result,
    build_game_result_summary_from_points,
    get_card_point_result_status,
    get_card_point_winner,
    get_completed_trick_schwarz_status,
    get_effective_schneider_status,
    get_schneider_status,
    get_schwarz_status,
)
from skatmind.game_value import build_game_value_summary
from skatmind.matador_inference import infer_matadors_from_known_ownership
from skatmind.overbid import build_overbid_summary, get_overbid_required_level
from skatmind.party_wide_claim_adjudication_contracts import (
    PartyWideClaimAdjudicationResultV1,
    build_party_wide_claim_adjudication_facts_v1,
    build_party_wide_claim_adjudication_result_v1,
)
from skatmind.party_wide_claim_contracts import (
    PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS,
    PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS,
    PartyWideAllRemainingTricksClaimV1,
    validate_party_wide_claim_against_evidence_v1,
)
from skatmind.party_wide_claim_evidence import (
    PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
    PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION,
    PartyWideClaimEvidenceV1,
    PartyWideClaimExactStateContextV1,
    validate_party_wide_claim_exact_state_context_v1,
)
from skatmind.party_wide_claim_proof_contracts import (
    PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION,
    PARTY_WIDE_CLAIM_PROOF_REQUEST_VERSION,
    PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
    PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS,
    PartyWideClaimProofPreparationV1,
    PartyWideClaimProofRequestV1,
    PartyWideClaimProofResultV1,
    build_invalid_party_wide_claim_proof_result_v1,
    build_unavailable_party_wide_claim_proof_result_v1,
    build_valid_party_wide_claim_proof_result_v1,
)
from skatmind.rules import get_card_points, get_legal_cards, get_trick_winner
from skatmind.settlement_normative_matrix import PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1

_SOURCE_EVIDENCE_UNAVAILABLE_REASONS = frozenset(PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS[:2])


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must be exactly {expected}.")


def _reconcile_evidence(evidence: PartyWideClaimEvidenceV1) -> None:
    """Reconciles retained Evidence facts without replaying the historical prefix."""
    _require_version(
        evidence.party_wide_claim_evidence_version,
        PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
        "party_wide_claim_evidence_version",
    )
    participant_ids = tuple(player.player_id for player in evidence.players)
    seats = tuple(player.seat for player in evidence.players)
    if (
        len(participant_ids) != 3
        or len(set(participant_ids)) != 3
        or seats != ("forehand", "middlehand", "rearhand")
        or evidence.declarer_player_id not in participant_ids
    ):
        raise ValueError("Claim Evidence participants are not canonical.")

    full_deck = tuple(get_full_deck())
    card_order = {card: index for index, card in enumerate(full_deck)}
    dealt_cards = tuple(
        card for player in evidence.players for card in player.initial_hand
    ) + tuple(evidence.skat)
    if (
        any(len(player.initial_hand) != 10 for player in evidence.players)
        or len(evidence.skat) != 2
        or len(dealt_cards) != 32
        or len(set(dealt_cards)) != 32
        or set(dealt_cards) != set(full_deck)
    ):
        raise ValueError("Claim Evidence initial Deal is not one complete Skat deck.")
    card_collections = (
        *(player.initial_hand for player in evidence.players),
        evidence.skat,
        evidence.discarded_cards,
        evidence.out_of_play_cards,
        *(cards for _player_id, cards in evidence.remaining_hands),
    )
    if any(
        tuple(cards) != tuple(sorted(cards, key=card_order.__getitem__))
        for cards in card_collections
    ):
        raise ValueError("Claim Evidence Card collections are not canonically ordered.")

    expected_out_of_play = (
        evidence.skat if evidence.declaration.hand_game else evidence.discarded_cards
    )
    if evidence.declaration.hand_game:
        discards_valid = evidence.discarded_cards == ()
    else:
        declarer = next(
            player for player in evidence.players if player.player_id == evidence.declarer_player_id
        )
        discards_valid = len(evidence.discarded_cards) == 2 and set(evidence.discarded_cards) <= {
            *declarer.initial_hand,
            *evidence.skat,
        }
    if not discards_valid or evidence.out_of_play_cards != expected_out_of_play:
        raise ValueError("Claim Evidence out-of-play Cards contradict the Deal.")
    declaration = GameDeclaration(
        game_type=evidence.declaration.game_type,
        hand_game=evidence.declaration.hand_game,
        ouvert=evidence.declaration.ouvert,
        schneider_announced=evidence.declaration.schneider_announced,
        schwarz_announced=evidence.declaration.schwarz_announced,
        matadors=evidence.declaration.matadors,
        bid_value=evidence.declaration.bid_value,
    )
    if declaration != evidence.declaration:
        raise ValueError("Claim Evidence Declaration is not canonical.")
    declarer = next(
        player for player in evidence.players if player.player_id == evidence.declarer_player_id
    )
    defender_cards = tuple(
        card
        for player in evidence.players
        if player.player_id != evidence.declarer_player_id
        for card in player.initial_hand
    )
    inferred_matadors = infer_matadors_from_known_ownership(
        game_type=declaration.game_type,
        declarer_owned_cards=(*declarer.initial_hand, *evidence.skat),
        non_declarer_owned_cards=defender_cards,
    )
    if declaration.matadors != inferred_matadors:
        raise ValueError("Claim Evidence Matadors contradict complete Deal ownership.")

    playable_hands = {player.player_id: list(player.initial_hand) for player in evidence.players}
    if not declaration.hand_game:
        playable_hands[evidence.declarer_player_id].extend(evidence.skat)
        for card in evidence.discarded_cards:
            playable_hands[evidence.declarer_player_id].remove(card)

    expected_leader = participant_ids[0]
    completed_tricks = []
    current_trick = None
    played_cards = []
    resolved_cards = []
    for index, trick in enumerate(evidence.tricks):
        plays = tuple((play.player_id, play.card) for play in trick.plays)
        if (
            trick.trick_number != index + 1
            or trick.leader_player_id != expected_leader
            or not 1 <= len(plays) <= 3
            or any(player_id not in participant_ids for player_id, _card in plays)
        ):
            raise ValueError("Claim Evidence source Trick chronology is inconsistent.")
        leader_index = participant_ids.index(trick.leader_player_id)
        expected_players = tuple(
            participant_ids[(leader_index + offset) % 3] for offset in range(len(plays))
        )
        if tuple(player_id for player_id, _card in plays) != expected_players:
            raise ValueError("Claim Evidence source Trick Player order is inconsistent.")
        prior_cards = []
        for player_id, card in plays:
            hand = playable_hands[player_id]
            if card not in hand or card not in get_legal_cards(
                hand,
                prior_cards,
                declaration.game_type,
            ):
                raise ValueError("Claim Evidence source Trick contains an illegal Card play.")
            hand.remove(card)
            prior_cards.append(card)
        played_cards.extend(card for _player_id, card in plays)
        if len(plays) == 3:
            resolved_cards.extend(card for _player_id, card in plays)
            winner_index = get_trick_winner(
                [card for _player_id, card in plays], evidence.declaration.game_type
            )
            winner_player_id = plays[winner_index][0]
            winner_side = (
                "declarer" if winner_player_id == evidence.declarer_player_id else "defenders"
            )
            completed_tricks.append(
                (
                    trick.trick_number,
                    trick.leader_player_id,
                    plays,
                    winner_player_id,
                    winner_side,
                    sum(get_card_points(card) for _player_id, card in plays),
                )
            )
            expected_leader = winner_player_id
        else:
            if index != len(evidence.tricks) - 1:
                raise ValueError("Only the final Claim Evidence Trick may be incomplete.")
            next_player_id = participant_ids[(leader_index + len(plays)) % 3]
            current_trick = (
                trick.trick_number,
                trick.leader_player_id,
                plays,
                next_player_id,
            )
            expected_leader = next_player_id

    retained_completed = tuple(
        (
            trick.trick_number,
            trick.leader_player_id,
            trick.plays,
            trick.winner_player_id,
            trick.winner_side,
            trick.trick_points,
        )
        for trick in evidence.completed_tricks
    )
    retained_current = (
        (
            evidence.current_trick.trick_number,
            evidence.current_trick.leader_player_id,
            evidence.current_trick.plays,
            evidence.current_trick.next_player_id,
        )
        if evidence.current_trick is not None
        else None
    )
    if retained_completed != tuple(completed_tricks) or retained_current != current_trick:
        raise ValueError("Claim Evidence derived Tricks contradict source Tricks.")
    if evidence.next_player_id != expected_leader:
        raise ValueError("Claim Evidence next Player contradicts its Trick prefix.")

    remaining_player_ids = tuple(player_id for player_id, _cards in evidence.remaining_hands)
    if remaining_player_ids != participant_ids:
        raise ValueError("Claim Evidence remaining hands are not canonical.")
    remaining_hands = dict(evidence.remaining_hands)
    if any(
        len(playable_hands[player_id]) != len(remaining_hands[player_id])
        or set(playable_hands[player_id]) != set(remaining_hands[player_id])
        for player_id in participant_ids
    ):
        raise ValueError("Claim Evidence remaining hands contradict retained legal plays.")
    current_cards = (
        tuple(card for _player_id, card in evidence.current_trick.plays)
        if evidence.current_trick is not None
        else ()
    )
    unresolved_cards = (
        tuple(card for _player_id, cards in evidence.remaining_hands for card in cards)
        + current_cards
    )
    accounted_cards = (*resolved_cards, *unresolved_cards, *evidence.out_of_play_cards)
    if (
        len(accounted_cards) != 32
        or len(set(accounted_cards)) != 32
        or set(accounted_cards) != set(full_deck)
    ):
        raise ValueError("Claim Evidence Card partitions do not form one complete Deal.")

    declarer_completed = sum(trick[4] == "declarer" for trick in completed_tricks)
    defender_completed = len(completed_tricks) - declarer_completed
    declarer_points = sum(trick[5] for trick in completed_tricks if trick[4] == "declarer")
    defender_points = sum(trick[5] for trick in completed_tricks if trick[4] == "defenders")
    unresolved_points = sum(get_card_points(card) for card in unresolved_cards)
    if (
        evidence.played_card_count != len(played_cards)
        or evidence.unresolved_card_count != len(unresolved_cards)
        or evidence.unresolved_card_points != unresolved_points
        or evidence.remaining_trick_count != len(unresolved_cards) // 3
        or len(unresolved_cards) % 3 != 0
        or evidence.declarer_completed_tricks != declarer_completed
        or evidence.defender_completed_tricks != defender_completed
        or evidence.declarer_trick_points != declarer_points
        or evidence.defender_trick_points != defender_points
        or len(completed_tricks) + evidence.remaining_trick_count != 10
    ):
        raise ValueError("Claim Evidence retained counters do not reconcile.")


def _reconcile_preparation(
    preparation: PartyWideClaimProofPreparationV1,
) -> None:
    _require_version(
        preparation.party_wide_claim_proof_preparation_version,
        PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION,
        "party_wide_claim_proof_preparation_version",
    )
    if not isinstance(preparation.claim, PartyWideAllRemainingTricksClaimV1):
        raise ValueError("Proof preparation must retain one structured Claim.")
    preparation.claim.__post_init__()

    if preparation.status == "available":
        if preparation.unavailable_reason is not None:
            raise ValueError("Available preparation cannot have an unavailable reason.")
        if not isinstance(preparation.evidence, PartyWideClaimEvidenceV1):
            raise ValueError("Available preparation must retain exact Evidence.")
        _reconcile_evidence(preparation.evidence)
        if not isinstance(preparation.request, PartyWideClaimProofRequestV1):
            raise ValueError("Available preparation must retain one Proof Request.")
        _require_version(
            preparation.request.party_wide_claim_proof_request_version,
            PARTY_WIDE_CLAIM_PROOF_REQUEST_VERSION,
            "party_wide_claim_proof_request_version",
        )
        context = preparation.request.exact_state_context
        if not isinstance(context, PartyWideClaimExactStateContextV1):
            raise ValueError("Available preparation must retain one Exact State Context.")
        _require_version(
            context.party_wide_claim_exact_state_context_version,
            PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION,
            "party_wide_claim_exact_state_context_version",
        )
        if not isinstance(context.exact_state, ExactSearchState):
            raise ValueError("Exact State Context must retain one ExactSearchState.")
        if (
            preparation.request.proof_policy != PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1
            or preparation.request.proof_quantifiers != PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS
            or preparation.request.maximum_unresolved_tricks
            != PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS
            or preparation.request.claim is not preparation.claim
            or preparation.request.evidence is not preparation.evidence
            or not 1
            <= preparation.evidence.remaining_trick_count
            <= PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS
        ):
            raise ValueError("Retained Proof Request does not match its canonical inputs.")
        validate_party_wide_claim_exact_state_context_v1(
            preparation.claim,
            preparation.evidence,
            context,
        )
        return

    if preparation.status != "unavailable":
        raise ValueError("Proof preparation status is not canonical.")
    if preparation.unavailable_reason not in PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS:
        raise ValueError("Unavailable preparation reason is not canonical.")
    if preparation.request is not None:
        raise ValueError("Unavailable preparation cannot retain a Proof Request.")
    if preparation.unavailable_reason in _SOURCE_EVIDENCE_UNAVAILABLE_REASONS:
        if preparation.evidence is not None:
            raise ValueError("Unavailable source Evidence must not be retained.")
    else:
        if not isinstance(preparation.evidence, PartyWideClaimEvidenceV1):
            raise ValueError("Unavailable structural preparation must retain exact Evidence.")
        _reconcile_evidence(preparation.evidence)
        validate_party_wide_claim_against_evidence_v1(
            preparation.claim,
            preparation.evidence,
        )


def _reconcile_proof_result(proof_result: PartyWideClaimProofResultV1) -> None:
    """Rebuilds one retained Result through the existing status-specific contract."""
    try:
        _require_version(
            proof_result.party_wide_claim_proof_result_version,
            PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION,
            "party_wide_claim_proof_result_version",
        )
        if not isinstance(proof_result.preparation, PartyWideClaimProofPreparationV1):
            raise ValueError("Proof Result must retain one proof preparation.")
        _reconcile_preparation(proof_result.preparation)
        if proof_result.status == "valid":
            if proof_result.assignment is None:
                raise ValueError("Valid proof Result must retain one assignment.")
            rebuilt = build_valid_party_wide_claim_proof_result_v1(
                preparation=proof_result.preparation,
                evaluated_state_count=proof_result.evaluated_state_count,
                memoized_state_count=proof_result.memoized_state_count,
                terminal_state_count=proof_result.terminal_state_count,
                assignment=proof_result.assignment,
                representative_line=proof_result.representative_line,
            )
        elif proof_result.status == "invalid":
            rebuilt = build_invalid_party_wide_claim_proof_result_v1(
                preparation=proof_result.preparation,
                evaluated_state_count=proof_result.evaluated_state_count,
                memoized_state_count=proof_result.memoized_state_count,
                terminal_state_count=proof_result.terminal_state_count,
                representative_line=proof_result.representative_line,
            )
        elif proof_result.status == "unavailable":
            if proof_result.unavailable_reason is None:
                raise ValueError("Unavailable proof Result requires one reason.")
            rebuilt = build_unavailable_party_wide_claim_proof_result_v1(
                preparation=proof_result.preparation,
                unavailable_reason=proof_result.unavailable_reason,
            )
        else:
            raise ValueError("Proof Result status is not canonical.")
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Party-wide Claim Proof Result is internally inconsistent."
        ) from error
    if rebuilt != proof_result:
        raise SkatMindInvariantError(
            "Party-wide Claim Proof Result does not equal its canonical reconstruction."
        )


def _highest_required_level(
    declared_level: str | None,
    overbid_required_level: str | None,
) -> str | None:
    return max(
        (level for level in (declared_level, overbid_required_level) if level is not None),
        key=get_play_level_rank,
        default=None,
    )


def _build_no_outcome_result(
    proof_result: PartyWideClaimProofResultV1,
) -> PartyWideClaimAdjudicationResultV1:
    return build_party_wide_claim_adjudication_result_v1(
        status="no_outcome",
        reason=("invalid_proof" if proof_result.status == "invalid" else "unavailable_proof"),
        proof_result=proof_result,
        facts=None,
        game_value_summary=None,
        overbid_summary=None,
        game_result_summary=None,
        final_settlement_summary=None,
    )


def adjudicate_party_wide_claim_proof_v1(
    proof_result: PartyWideClaimProofResultV1,
) -> PartyWideClaimAdjudicationResultV1:
    """Adjudicates one existing valid proof without executing proof or Search."""
    if not isinstance(proof_result, PartyWideClaimProofResultV1):
        raise ValueError("proof_result must be a PartyWideClaimProofResultV1.")
    _reconcile_proof_result(proof_result)
    if proof_result.status != "valid":
        return _build_no_outcome_result(proof_result)

    preparation = proof_result.preparation
    evidence = preparation.evidence
    assignment = proof_result.assignment
    if evidence is None or assignment is None:
        raise SkatMindInvariantError("Valid party-wide Claim proof lacks adjudication inputs.")
    claim = preparation.claim

    out_of_play_points = sum(get_card_points(card) for card in evidence.out_of_play_cards)
    observed_declarer_points = evidence.declarer_trick_points + out_of_play_points
    observed_defender_points = evidence.defender_trick_points
    if observed_declarer_points + observed_defender_points + evidence.unresolved_card_points != 120:
        raise SkatMindInvariantError("Claim point accounting does not total 120 points.")

    game_value_summary = build_game_value_summary(evidence.declaration)
    overbid_summary = build_overbid_summary(
        game_value_summary,
        evidence.declaration.bid_value,
    )
    observed_result = build_game_result_summary_from_points(
        observed_declarer_points,
        observed_defender_points,
    )
    observed_completed_tricks = [
        {"winner_role": trick.winner_side} for trick in evidence.completed_tricks
    ]
    decision_state = determine_decision_state_before_game_end(
        observed_result,
        game_value_summary,
        overbid_summary,
        observed_completed_tricks,
    )

    assigned_declarer_points = (
        assignment.assigned_card_points if claim.claiming_party == "declarer" else 0
    )
    assigned_defender_points = (
        assignment.assigned_card_points if claim.claiming_party == "defenders" else 0
    )
    final_declarer_points = observed_declarer_points + assigned_declarer_points
    final_defender_points = observed_defender_points + assigned_defender_points
    if final_declarer_points + final_defender_points != 120:
        raise SkatMindInvariantError("Adjudicated Claim points do not total 120.")

    assigned_declarer_tricks = (
        assignment.assigned_trick_count if claim.claiming_party == "declarer" else 0
    )
    assigned_defender_tricks = (
        assignment.assigned_trick_count if claim.claiming_party == "defenders" else 0
    )
    final_declarer_tricks = evidence.declarer_completed_tricks + assigned_declarer_tricks
    final_defender_tricks = evidence.defender_completed_tricks + assigned_defender_tricks
    final_winner_parties = (
        tuple(trick.winner_side for trick in evidence.completed_tricks)
        + (claim.claiming_party,) * assignment.assigned_trick_count
    )
    if len(final_winner_parties) != 10 or final_declarer_tricks + final_defender_tricks != 10:
        raise SkatMindInvariantError("Adjudicated Claim Trick ownership does not total ten.")
    final_completed_tricks = [
        {"winner_role": winner_party} for winner_party in final_winner_parties
    ]

    is_null = game_value_summary.get("is_null_game") is True
    achieved_schneider_status = "not_applicable"
    achieved_schwarz_status = "not_applicable"
    achieved_schneider_applied = False
    achieved_schwarz_applied = False
    if not is_null:
        achieved_schneider_status = get_effective_schneider_status(
            final_declarer_points,
            final_defender_points,
        )
        completed_schwarz = get_completed_trick_schwarz_status(final_completed_tricks)
        achieved_schwarz_status = {
            "declarer": "declarer_made_schwarz",
            "defenders": "defenders_made_schwarz",
            "none": "none",
        }[completed_schwarz]
        achieved_schneider_applied = (
            achieved_schneider_status in {"declarer_made_schneider", "defenders_made_schneider"}
            and overbid_summary.get("is_overbid") is not True
            and not (
                achieved_schneider_status == "defenders_made_schneider"
                and is_schneider_announced(game_value_summary)
            )
        )
        achieved_schwarz_applied = (
            achieved_schwarz_status in {"declarer_made_schwarz", "defenders_made_schwarz"}
            and overbid_summary.get("is_overbid") is not True
        )

    completed_result = observed_result.copy()
    completed_result.update(
        {
            "declarer_points": final_declarer_points,
            "defender_points": final_defender_points,
            "points_remaining": 0,
            "is_complete": True,
            "winner": get_card_point_winner(final_declarer_points, final_defender_points),
            "status": get_card_point_result_status(
                final_declarer_points,
                final_defender_points,
            ),
            "raw_schneider_status": get_schneider_status(
                final_declarer_points,
                final_defender_points,
            ),
            "raw_schwarz_status": get_schwarz_status(
                final_declarer_points,
                final_defender_points,
            ),
            "effective_schneider_status": (
                achieved_schneider_status if not is_null else "not_applicable"
            ),
            "effective_schwarz_status": (
                achieved_schwarz_status if not is_null else "not_applicable"
            ),
        }
    )
    if is_null:
        completed_result = apply_completed_null_contract_result(
            completed_result,
            final_completed_tricks,
        )
        completed_result["effective_schneider_status"] = "not_applicable"
        completed_result["effective_schwarz_status"] = "not_applicable"

    candidate_winner = completed_result["winner"]
    overbid_required_level = get_overbid_required_level(
        game_value_summary,
        overbid_summary,
    )
    declared_level = get_declared_mandatory_play_level(game_value_summary)
    mandatory_level = _highest_required_level(declared_level, overbid_required_level)
    achieved_declarer_level_rank = 0
    if not is_null and achieved_schneider_status == "declarer_made_schneider":
        achieved_declarer_level_rank = 1
    if not is_null and achieved_schwarz_status == "declarer_made_schwarz":
        achieved_declarer_level_rank = 2
    mandatory_level_covered = (
        mandatory_level is None
        or candidate_winner == "declarer"
        and achieved_declarer_level_rank >= get_play_level_rank(mandatory_level)
    )
    overbid_requirement_covered = (
        overbid_required_level is None
        or candidate_winner == "declarer"
        and achieved_declarer_level_rank >= get_play_level_rank(overbid_required_level)
    )

    if decision_state == "declarer_already_won":
        winner = "declarer"
    elif decision_state == "defenders_already_won":
        winner = "defenders"
    elif candidate_winner == "declarer" and not mandatory_level_covered:
        winner = "defenders"
    else:
        winner = candidate_winner
    if winner not in {"declarer", "defenders"}:
        raise SkatMindInvariantError("Completed Claim assignment did not decide the Game.")

    is_preexisting = decision_state != "undecided"
    outcome_source = (
        "preexisting_game_decision" if is_preexisting else "exact_party_wide_claim_adjudication"
    )
    winner_basis = "preexisting_game_decision" if is_preexisting else "completed_claim_assignment"
    overbid_required_value_applied = overbid_summary.get("is_overbid") is True
    rest_assignment = {
        "source": "party_wide_claim_proof_assignment",
        "recipient": claim.claiming_party,
        "remaining_trick_count": assignment.assigned_trick_count,
        "assigned_card_count": assignment.assigned_card_count,
        "assigned_card_points": assignment.assigned_card_points,
    }
    game_result_summary = completed_result.copy()
    game_result_summary.update(
        {
            "winner": winner,
            "status": "final_decided" if is_preexisting else "final_adjudicated",
            "game_end_reason": claim.kind,
            "game_end_kind": claim.kind,
            "outcome_source": outcome_source,
            "winner_basis": winner_basis,
            "decision_state_before_game_end": decision_state,
            "party_wide_claim_proof_status": proof_result.status,
            "claimant_player_id": claim.claimant_player_id,
            "claiming_party": claim.claiming_party,
            "mandatory_level_awarded": False,
            "mandatory_level_source": get_mandatory_level_source(
                game_value_summary,
                overbid_required_level,
            ),
            "declared_mandatory_play_level": declared_level,
            "mandatory_play_level": mandatory_level,
            "mandatory_level_covered": mandatory_level_covered,
            "achieved_schneider_applied": achieved_schneider_applied,
            "achieved_schwarz_applied": achieved_schwarz_applied,
            "overbid_required_level": overbid_required_level,
            "overbid_requirement_covered": overbid_requirement_covered,
            "overbid_required_value_applied": overbid_required_value_applied,
            "rest_tricks_recipient": claim.claiming_party,
            "remaining_points_recipient": claim.claiming_party,
            "remaining_points_assigned": assignment.assigned_card_points,
            "rest_trick_assignment": rest_assignment,
        }
    )

    settlement_projection = game_result_summary.copy()
    settlement_projection["game_end_reason"] = "normal_completion"
    settlement_projection["game_end_kind"] = "normal_completion"
    final_settlement_summary = build_final_settlement_summary(
        game_value_summary,
        settlement_projection,
        overbid_summary,
        final_completed_tricks,
    )
    if (
        final_settlement_summary.get("is_complete") is not True
        or final_settlement_summary.get("missing_inputs") != []
        or final_settlement_summary.get("winner") != winner
        or final_settlement_summary.get("game_value") != game_value_summary["game_value"]
        or final_settlement_summary.get("bid_value") != evidence.declaration.bid_value
        or final_settlement_summary.get("overbid_status") != overbid_summary["status"]
        or final_settlement_summary.get("overbid_required_game_value")
        != overbid_summary["required_game_value"]
        or not isinstance(final_settlement_summary.get("settlement_score"), int)
        or not isinstance(final_settlement_summary.get("is_loss"), bool)
    ):
        raise SkatMindInvariantError(
            "Existing Final Settlement did not produce a complete reconciled Claim outcome."
        )

    facts = build_party_wide_claim_adjudication_facts_v1(
        proof_result=proof_result,
        decision_state_before_claim=decision_state,
        outcome_source=outcome_source,
        winner_basis=winner_basis,
        adjudicated_winner=winner,
        observed_declarer_points=observed_declarer_points,
        observed_defender_points=observed_defender_points,
        out_of_play_points=out_of_play_points,
        assigned_declarer_points=assigned_declarer_points,
        assigned_defender_points=assigned_defender_points,
        final_declarer_points=final_declarer_points,
        final_defender_points=final_defender_points,
        observed_declarer_tricks=evidence.declarer_completed_tricks,
        observed_defender_tricks=evidence.defender_completed_tricks,
        assigned_declarer_tricks=assigned_declarer_tricks,
        assigned_defender_tricks=assigned_defender_tricks,
        final_declarer_tricks=final_declarer_tricks,
        final_defender_tricks=final_defender_tricks,
        final_completed_trick_winner_parties=final_winner_parties,
        remaining_points_recipient=claim.claiming_party,
        remaining_points_assigned=assignment.assigned_card_points,
        achieved_schneider_status=achieved_schneider_status,
        achieved_schwarz_status=achieved_schwarz_status,
        achieved_schneider_applied=achieved_schneider_applied,
        achieved_schwarz_applied=achieved_schwarz_applied,
        overbid_required_level=overbid_required_level,
        overbid_required_value_applied=overbid_required_value_applied,
    )
    return build_party_wide_claim_adjudication_result_v1(
        status="adjudicated",
        reason="valid_proof",
        proof_result=proof_result,
        facts=facts,
        game_value_summary=game_value_summary,
        overbid_summary=overbid_summary,
        game_result_summary=game_result_summary,
        final_settlement_summary=final_settlement_summary,
    )
