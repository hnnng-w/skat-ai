from dataclasses import dataclass
from typing import Any

from skatmind.matador_inference import JACK_ORDER
from skatmind.side_ownership import VALID_CONCRETE_PLAYERS, get_player_side
from skatmind.turn_phase import derive_next_player, normalize_turn_phase_for_position

TOP_JACK = "CJ"
LOWER_JACKS = frozenset({"SJ", "HJ", "DJ"})
VALID_PARTIES = {"declarer", "defenders"}


@dataclass(frozen=True)
class JackOwnershipEvidence:
    card: str
    ownership: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class TheoreticalSchwarzAssessment:
    status: str
    losing_party: str
    exclusion_basis: str | None
    jack_ownership_evidence: tuple[JackOwnershipEvidence, ...]


def build_reliable_jack_ownership_evidence(
    data: dict[str, Any],
    throwing_player: str,
    thrown_cards: tuple[str, ...],
) -> tuple[JackOwnershipEvidence, ...]:
    """Builds deterministic party ownership for jacks from bounded evidence."""
    declarer_player = data.get("declarer_player", "unknown")
    ownership_by_card: dict[str, str] = {}
    sources_by_card: dict[str, set[str]] = {card: set() for card in JACK_ORDER}

    def add(card: str, ownership: str, source: str) -> None:
        if card not in JACK_ORDER:
            return
        existing = ownership_by_card.get(card)
        if existing is not None and existing != ownership:
            raise ValueError(
                f"Reliable jack ownership for {card} is contradictory: "
                f"{existing} versus {ownership}."
            )
        ownership_by_card[card] = ownership
        sources_by_card[card].add(source)

    throwing_party = get_player_side(throwing_player, declarer_player)
    if throwing_party is None:
        raise ValueError("Jack ownership assessment requires a concrete declarer_player.")
    for card in thrown_cards:
        add(card, throwing_party, "thrown_cards")

    local_party = get_player_side("me", declarer_player)
    if local_party is not None:
        for card in data.get("hand", []):
            add(card, local_party, "local_exact_hand")

    completed_tricks = data.get("completed_tricks", [])
    for trick in completed_tricks:
        cards = trick.get("cards", [])
        players = trick.get("players")
        if not isinstance(players, list) or len(players) != 3:
            continue
        for card, player in zip(cards, players, strict=True):
            if player in VALID_CONCRETE_PLAYERS:
                party = get_player_side(player, declarer_player)
                if party is not None:
                    add(card, party, "completed_tricks")

    current_trick = data.get("current_trick", [])
    if current_trick:
        phase = normalize_turn_phase_for_position(
            data.get("trick_leader", "unknown"),
            data.get("next_player", "unknown"),
            current_trick,
            completed_tricks,
        )
        if phase.trick_leader in VALID_CONCRETE_PLAYERS:
            for index, card in enumerate(current_trick):
                player = derive_next_player(phase.trick_leader, index)
                party = get_player_side(player, declarer_player)
                if party is not None:
                    add(card, party, "current_trick")

    for card in data.get("skat", []):
        add(card, "skat", "skat")

    return tuple(
        JackOwnershipEvidence(
            card=card,
            ownership=ownership_by_card.get(card, "unknown"),
            sources=tuple(sorted(sources_by_card[card])),
        )
        for card in JACK_ORDER
    )


def assess_theoretical_schwarz_exclusion(
    losing_party: str,
    jack_ownership_evidence: tuple[JackOwnershipEvidence, ...],
) -> TheoreticalSchwarzAssessment:
    """Applies only the bounded top-jack and three-lower-jacks practice."""
    if losing_party not in VALID_PARTIES:
        raise ValueError("losing_party must be 'declarer' or 'defenders'.")

    ownership = {
        evidence.card: evidence.ownership for evidence in jack_ownership_evidence
    }
    if ownership.get(TOP_JACK) == losing_party:
        status = "excluded"
        exclusion_basis = "losing_party_owned_top_jack"
    elif all(ownership.get(card) == losing_party for card in LOWER_JACKS):
        status = "excluded"
        exclusion_basis = "losing_party_owned_all_three_lower_jacks"
    else:
        status = "not_excluded"
        exclusion_basis = None

    return TheoreticalSchwarzAssessment(
        status=status,
        losing_party=losing_party,
        exclusion_basis=exclusion_basis,
        jack_ownership_evidence=jack_ownership_evidence,
    )


def build_serializable_theoretical_schwarz_assessment(
    assessment: TheoreticalSchwarzAssessment,
) -> dict[str, Any]:
    """Builds the stable privacy-bounded theoretical assessment output."""
    return {
        "status": assessment.status,
        "losing_party": assessment.losing_party,
        "exclusion_basis": assessment.exclusion_basis,
        "assessment_scope": "jack_only",
        "jack_ownership_evidence": [
            {
                "card": evidence.card,
                "ownership": evidence.ownership,
                "sources": list(evidence.sources),
            }
            for evidence in assessment.jack_ownership_evidence
        ],
    }
