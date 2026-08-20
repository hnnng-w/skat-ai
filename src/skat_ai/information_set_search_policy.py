from skat_ai.deck import get_full_deck
from skat_ai.information_set_search_contracts import (
    InformationSetSearchPolicySettingsV1,
)
from skat_ai.information_set_search_state import InformationSetSearchObservationV1
from skat_ai.opponent_policy import (
    determine_current_trick_winner_index,
    get_preferred_opponent_cards_by_policy,
)

_CARD_ORDER = {card: index for index, card in enumerate(get_full_deck())}
_DEFENDER_ONLY_POLICIES = {"basic_defender_lead", "basic_defender_response"}


def is_information_set_fixed_policy_supported_for_actor_v1(
    *,
    actor_player: str,
    declarer_player: str,
    policy_settings: InformationSetSearchPolicySettingsV1,
) -> bool:
    """Returns whether one fixed actor's configured Policies match its side."""
    if actor_player not in {"left", "right"}:
        raise ValueError("A fixed information-set actor must be left or right.")
    policy = policy_settings.for_player(actor_player)
    if actor_player != declarer_player:
        return True
    return not _DEFENDER_ONLY_POLICIES.intersection(
        {policy.lead_policy, policy.response_policy}
    )


def select_information_set_fixed_policy_card_v1(
    *,
    observation: InformationSetSearchObservationV1,
    policy_settings: InformationSetSearchPolicySettingsV1,
) -> str:
    """Selects one deterministic fixed-policy Card from actor-visible facts."""
    if not isinstance(observation, InformationSetSearchObservationV1):
        raise ValueError("observation must be an InformationSetSearchObservationV1.")
    if not isinstance(policy_settings, InformationSetSearchPolicySettingsV1):
        raise ValueError(
            "policy_settings must be an InformationSetSearchPolicySettingsV1."
        )
    actor = observation.actor_player
    if actor == policy_settings.controlled_player:
        raise ValueError("The controlled Player cannot use a fixed Policy.")
    if actor not in {"left", "right"}:
        raise ValueError("A fixed information-set actor must be left or right.")
    if not observation.legal_cards:
        raise ValueError("A fixed information-set actor requires legal Cards.")
    if not is_information_set_fixed_policy_supported_for_actor_v1(
        actor_player=actor,
        declarer_player=observation.declarer_player,
        policy_settings=policy_settings,
    ):
        raise ValueError("The acting Declarer has a Defender-only fixed Policy.")

    settings = policy_settings.for_player(actor)
    policy = settings.lead_policy if not observation.current_trick else settings.response_policy
    current_cards = [play.card for play in observation.current_trick]
    partner_currently_winning = False
    partner_index = 0
    if current_cards and observation.actor_side == "defenders":
        partner_index = determine_current_trick_winner_index(
            current_cards,
            observation.game_type,
        )
        current_winner = observation.current_trick[partner_index].player
        partner_currently_winning = current_winner != observation.declarer_player

    preferred = get_preferred_opponent_cards_by_policy(
        hand=list(observation.own_remaining_hand),
        current_trick=current_cards,
        game_type=observation.game_type,
        player_index=len(current_cards),
        policy=policy,
        partner_currently_winning=partner_currently_winning,
        partner_index=partner_index,
    )
    legal_preferred = tuple(
        card for card in preferred if card in observation.legal_cards
    )
    if not legal_preferred:
        raise ValueError("The fixed Policy returned no preferred legal Card.")
    return min(legal_preferred, key=_CARD_ORDER.__getitem__)
