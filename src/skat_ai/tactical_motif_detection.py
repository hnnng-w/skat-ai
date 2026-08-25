from skat_ai.deck import get_full_deck
from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshot
from skat_ai.opponent_policy import (
    determine_current_trick_winner_index,
    get_partner_safe_legal_cards,
    get_winning_legal_cards,
)
from skat_ai.rules import (
    get_card_points,
    get_card_strength,
    get_effective_suit,
    get_legal_cards,
    is_trump,
)
from skat_ai.tactical_motif_contracts import (
    TACTICAL_DECISION_FACTS_VERSION,
    TACTICAL_DECISION_OBSERVATION_VERSION,
    TACTICAL_MOTIF_FAMILY_BY_TYPE,
    TACTICAL_MOTIF_OCCURRENCE_VERSION,
    TACTICAL_MOTIF_TYPES,
    TacticalDecisionFactsV1,
    TacticalDecisionObservationV1,
    TacticalMotifOccurrenceV1,
)


def _side_for_player(player_id: str, declarer_player_id: str) -> str:
    return "declarer" if player_id == declarer_player_id else "defenders"


def _validate_participants(
    participant_player_ids: tuple[str, str, str],
    *,
    acting_player_id: str,
    declarer_player_id: str,
) -> None:
    if (
        not isinstance(participant_player_ids, tuple)
        or len(participant_player_ids) != 3
        or len(set(participant_player_ids)) != 3
        or any(
            not isinstance(player_id, str) or not player_id or player_id != player_id.strip()
            for player_id in participant_player_ids
        )
    ):
        raise ValueError("participant_player_ids must contain exactly three unique IDs.")
    if acting_player_id not in participant_player_ids:
        raise ValueError("The acting Player must be one of participant_player_ids.")
    if declarer_player_id not in participant_player_ids:
        raise ValueError("The Declarer must be one of participant_player_ids.")


def build_tactical_decision_facts_v1(
    *,
    snapshot: HistoricalDecisionSnapshot,
    declarer_player_id: str,
    participant_player_ids: tuple[str, str, str],
) -> TacticalDecisionFactsV1:
    """Builds safe structural facts without inspecting the actual played Card."""
    if not isinstance(snapshot, HistoricalDecisionSnapshot):
        raise ValueError("snapshot must be HistoricalDecisionSnapshot.")
    _validate_participants(
        participant_player_ids,
        acting_player_id=snapshot.acting_player_id,
        declarer_player_id=declarer_player_id,
    )
    expected_side = _side_for_player(snapshot.acting_player_id, declarer_player_id)
    if snapshot.acting_side != expected_side:
        raise ValueError("Snapshot acting side does not match the Declarer identity.")

    visible = snapshot.visible_state
    current_cards = [play.card for play in visible.current_trick]
    legal_cards = get_legal_cards(
        list(visible.own_hand),
        current_cards,
        visible.game_type,
    )
    if tuple(legal_cards) != visible.legal_cards:
        raise ValueError("Snapshot legal Cards do not match its decision-time state.")

    partner_player_id = None
    if snapshot.acting_side == "defenders":
        partner_player_id = next(
            player_id
            for player_id in participant_player_ids
            if player_id not in {snapshot.acting_player_id, declarer_player_id}
        )

    required_category = (
        None if not current_cards else get_effective_suit(current_cards[0], visible.game_type)
    )
    can_follow = (
        None
        if required_category is None
        else any(
            get_effective_suit(card, visible.game_type) == required_category
            for card in visible.own_hand
        )
    )
    pre_winner_player_id = None
    pre_winner_side = None
    if current_cards:
        pre_winner_index = determine_current_trick_winner_index(
            current_cards,
            visible.game_type,
        )
        pre_winner_player_id = visible.current_trick[pre_winner_index].player_id
        pre_winner_side = _side_for_player(pre_winner_player_id, declarer_player_id)

    winning_cards = get_winning_legal_cards(
        list(visible.own_hand),
        current_cards,
        visible.game_type,
        len(current_cards),
    )
    partner_safe_cards: list[str] = []
    if partner_player_id is not None and pre_winner_player_id == partner_player_id:
        partner_index = next(
            index
            for index, play in enumerate(visible.current_trick)
            if play.player_id == partner_player_id
        )
        partner_safe_cards = get_partner_safe_legal_cards(
            list(visible.own_hand),
            current_cards,
            visible.game_type,
            partner_index,
        )

    previous_leads = tuple(
        get_effective_suit(trick.plays[0].card, visible.game_type)
        for trick in visible.completed_tricks
    )
    partner_last_lead = next(
        (
            get_effective_suit(trick.plays[0].card, visible.game_type)
            for trick in reversed(visible.completed_tricks)
            if trick.plays[0].player_id == partner_player_id
        ),
        None,
    )
    return TacticalDecisionFactsV1(
        tactical_decision_facts_version=TACTICAL_DECISION_FACTS_VERSION,
        source_game_id=snapshot.source_game_id,
        decision_index=snapshot.decision_index,
        trick_number=snapshot.trick_number,
        play_index=snapshot.play_index,
        acting_player_id=snapshot.acting_player_id,
        acting_seat=snapshot.acting_seat,
        acting_side=snapshot.acting_side,
        partner_player_id=partner_player_id,
        game_type=visible.game_type,
        information_cutoff=snapshot.information_cutoff,
        required_effective_category=required_category,
        can_follow_required_effective_category=can_follow,
        legal_card_count=len(legal_cards),
        legal_trump_count=sum(is_trump(card, visible.game_type) for card in legal_cards),
        legal_current_winning_card_count=len(winning_cards),
        legal_partner_safe_card_count=len(partner_safe_cards),
        pre_play_current_winner_player_id=pre_winner_player_id,
        pre_play_current_winner_side=pre_winner_side,
        partner_currently_winning_before=(
            partner_player_id is not None and pre_winner_player_id == partner_player_id
        ),
        previous_lead_effective_categories=previous_leads,
        partner_last_lead_effective_category=partner_last_lead,
    )


def _lowest_cost_winning_card(
    *,
    winning_cards: list[str],
    current_cards: list[str],
    game_type: str,
) -> str | None:
    if not winning_cards:
        return None
    deck_order = {card: index for index, card in enumerate(get_full_deck())}

    def cost(card: str) -> tuple[int, ...]:
        lead_category = get_effective_suit(
            current_cards[0] if current_cards else card,
            game_type,
        )
        strength = get_card_strength(card, game_type, lead_category)
        if game_type == "null":
            return (strength, deck_order[card])
        return (get_card_points(card), strength, deck_order[card])

    return min(winning_cards, key=cost)


def _build_occurrences(motif_presence: dict[str, bool]) -> tuple[TacticalMotifOccurrenceV1, ...]:
    return tuple(
        TacticalMotifOccurrenceV1(
            tactical_motif_occurrence_version=TACTICAL_MOTIF_OCCURRENCE_VERSION,
            motif_type=motif_type,
            motif_family=TACTICAL_MOTIF_FAMILY_BY_TYPE[motif_type],
            evidence_time=(
                "after_trick_completion"
                if motif_type
                in {
                    "point_card_captured_by_partner",
                    "point_card_lost_to_opposing_side",
                }
                else "after_actual_play"
            ),
        )
        for motif_type in TACTICAL_MOTIF_TYPES
        if motif_presence.get(motif_type, False)
    )


def build_tactical_decision_observation_v1(
    *,
    decision_time_facts: TacticalDecisionFactsV1,
    snapshot: HistoricalDecisionSnapshot,
    actual_card: str,
    declarer_player_id: str,
    completed_trick_winner_player_id: str | None = None,
    completed_trick_winner_side: str | None = None,
    completed_trick_points: int | None = None,
) -> TacticalDecisionObservationV1:
    """Attaches one legal actual Card and optional retained completed-Trick outcome."""
    if not isinstance(decision_time_facts, TacticalDecisionFactsV1):
        raise ValueError("decision_time_facts must be TacticalDecisionFactsV1.")
    if not isinstance(snapshot, HistoricalDecisionSnapshot):
        raise ValueError("snapshot must be HistoricalDecisionSnapshot.")
    for field_name in (
        "source_game_id",
        "decision_index",
        "trick_number",
        "play_index",
        "acting_player_id",
        "acting_seat",
        "acting_side",
    ):
        if getattr(decision_time_facts, field_name) != getattr(snapshot, field_name):
            raise ValueError("Decision Facts and Snapshot identities do not match.")
    visible = snapshot.visible_state
    if decision_time_facts.game_type != visible.game_type:
        raise ValueError("Decision Facts and Snapshot game types do not match.")

    current_cards = [play.card for play in visible.current_trick]
    legal_cards = get_legal_cards(
        list(visible.own_hand),
        current_cards,
        visible.game_type,
    )
    if actual_card not in legal_cards:
        raise ValueError("actual_card must be legal in the retained decision-time state.")
    completed_values = (
        completed_trick_winner_player_id,
        completed_trick_winner_side,
        completed_trick_points,
    )
    if any(value is None for value in completed_values) and any(
        value is not None for value in completed_values
    ):
        raise ValueError("Completed-Trick outcome facts must be supplied together.")
    if completed_trick_winner_player_id is not None:
        expected_completed_side = _side_for_player(
            completed_trick_winner_player_id,
            declarer_player_id,
        )
        if completed_trick_winner_side != expected_completed_side:
            raise ValueError("Completed-Trick winner side does not reconcile.")

    post_plays = [*visible.current_trick]
    post_cards = [*current_cards, actual_card]
    post_winner_index = determine_current_trick_winner_index(
        post_cards,
        visible.game_type,
    )
    post_player_ids = [play.player_id for play in post_plays] + [snapshot.acting_player_id]
    post_winner_player_id = post_player_ids[post_winner_index]
    post_winner_side = _side_for_player(post_winner_player_id, declarer_player_id)
    actual_is_current_winner = post_winner_player_id == snapshot.acting_player_id
    actual_keeps_partner_winning = (
        decision_time_facts.partner_player_id is not None
        and post_winner_player_id == decision_time_facts.partner_player_id
    )
    actual_overtakes_partner = (
        decision_time_facts.partner_currently_winning_before and actual_is_current_winner
    )
    winning_cards = get_winning_legal_cards(
        list(visible.own_hand),
        current_cards,
        visible.game_type,
        len(current_cards),
    )
    lowest_cost_winner = _lowest_cost_winning_card(
        winning_cards=winning_cards,
        current_cards=current_cards,
        game_type=visible.game_type,
    )
    actual_category = get_effective_suit(actual_card, visible.game_type)
    remaining_hand = list(visible.own_hand)
    remaining_hand.remove(actual_card)
    remaining_category_count = sum(
        get_effective_suit(card, visible.game_type) == actual_category for card in remaining_hand
    )
    actual_trump = is_trump(actual_card, visible.game_type)
    actual_points = get_card_points(actual_card)
    is_lead = snapshot.play_index == 1
    unable_to_follow = (
        not is_lead and decision_time_facts.can_follow_required_effective_category is False
    )
    is_complete = completed_trick_winner_player_id is not None
    opposing_side = "defenders" if snapshot.acting_side == "declarer" else "declarer"

    motif_presence = {
        "trump_lead": is_lead and visible.game_type != "null" and actual_trump,
        "non_trump_lead": is_lead and not actual_trump,
        "new_effective_category_lead": (
            is_lead
            and actual_category not in decision_time_facts.previous_lead_effective_categories
        ),
        "repeat_effective_category_lead": (
            is_lead and actual_category in decision_time_facts.previous_lead_effective_categories
        ),
        "void_trump_play": unable_to_follow and actual_trump,
        "void_non_trump_discard": unable_to_follow and not actual_trump,
        "available_trump_not_used": (
            unable_to_follow and decision_time_facts.legal_trump_count > 0 and not actual_trump
        ),
        "opposing_side_overtake": (
            decision_time_facts.pre_play_current_winner_side == opposing_side
            and actual_is_current_winner
        ),
        "current_trick_win_available_not_taken": (
            bool(winning_cards) and not actual_is_current_winner
        ),
        "lowest_cost_current_winner": (
            actual_is_current_winner and actual_card == lowest_cost_winner
        ),
        "partner_effective_category_return": (
            snapshot.acting_side == "defenders"
            and is_lead
            and decision_time_facts.partner_last_lead_effective_category is not None
            and actual_category == decision_time_facts.partner_last_lead_effective_category
        ),
        "partner_overtake": actual_overtakes_partner,
        "partner_safe_point_load": (
            visible.game_type != "null"
            and snapshot.acting_side == "defenders"
            and decision_time_facts.partner_currently_winning_before
            and actual_points > 0
            and actual_keeps_partner_winning
        ),
        "point_card_captured_by_partner": (
            visible.game_type != "null"
            and snapshot.acting_side == "defenders"
            and actual_points > 0
            and is_complete
            and completed_trick_winner_player_id == decision_time_facts.partner_player_id
        ),
        "effective_category_exhausted": remaining_category_count == 0,
        "point_card_lost_to_opposing_side": (
            visible.game_type != "null"
            and actual_points > 0
            and is_complete
            and completed_trick_winner_side == opposing_side
        ),
    }
    return TacticalDecisionObservationV1(
        tactical_decision_observation_version=TACTICAL_DECISION_OBSERVATION_VERSION,
        decision_time_facts=decision_time_facts,
        actual_card=actual_card,
        actual_effective_category=actual_category,
        actual_is_trump=actual_trump,
        actual_card_points=actual_points,
        post_play_current_winner_player_id=post_winner_player_id,
        post_play_current_winner_side=post_winner_side,
        actual_is_current_winner=actual_is_current_winner,
        actual_keeps_partner_winning=actual_keeps_partner_winning,
        actual_overtakes_partner=actual_overtakes_partner,
        actual_is_lowest_cost_current_winner=actual_card == lowest_cost_winner,
        remaining_actual_effective_category_count=remaining_category_count,
        completed_trick_winner_player_id=completed_trick_winner_player_id,
        completed_trick_winner_side=completed_trick_winner_side,
        completed_trick_points=completed_trick_points,
        observation_status="complete" if is_complete else "partial",
        motifs=_build_occurrences(motif_presence),
    )


def build_tactical_decision_observation_from_snapshot_v1(
    *,
    snapshot: HistoricalDecisionSnapshot,
    declarer_player_id: str,
    participant_player_ids: tuple[str, str, str],
    completed_trick_winner_player_id: str | None = None,
    completed_trick_winner_side: str | None = None,
    completed_trick_points: int | None = None,
) -> TacticalDecisionObservationV1:
    """Builds facts before attaching the retained actual Card and Trick outcome."""
    decision_time_facts = build_tactical_decision_facts_v1(
        snapshot=snapshot,
        declarer_player_id=declarer_player_id,
        participant_player_ids=participant_player_ids,
    )
    return build_tactical_decision_observation_v1(
        decision_time_facts=decision_time_facts,
        snapshot=snapshot,
        actual_card=snapshot.actual_card_played,
        declarer_player_id=declarer_player_id,
        completed_trick_winner_player_id=completed_trick_winner_player_id,
        completed_trick_winner_side=completed_trick_winner_side,
        completed_trick_points=completed_trick_points,
    )
