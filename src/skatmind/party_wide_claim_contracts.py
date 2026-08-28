from dataclasses import dataclass
from typing import Any

from skatmind.settlement_normative_matrix import (
    PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1_QUANTIFIERS,
)

PARTY_WIDE_CLAIM_VERSION = 1

PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND = "party_wide_all_remaining_tricks_claim"
PARTY_WIDE_CLAIMING_PARTIES = ("declarer", "defenders")

PARTY_WIDE_CLAIM_SCOPE_POLICY = "structured_retrospective_complete_world_only"
PARTY_WIDE_CLAIM_PARTY_POLICY = "claimant_must_belong_to_claiming_party"
PARTY_WIDE_CLAIM_EVIDENCE_POLICY = "complete_deal_and_exact_legal_play_prefix"
PARTY_WIDE_CLAIM_EXACT_STATE_POLICY = "historical_replay_then_exact_state_validation"
PARTY_WIDE_CLAIM_PROOF_POLICY = "claiming_party_existential_opposing_party_universal"
PARTY_WIDE_CLAIM_BOUND_POLICY = "at_most_five_unresolved_tricks_including_current"
PARTY_WIDE_CLAIM_VALID_POLICY = "valid_proof_assigns_every_unresolved_trick_to_claiming_party"
PARTY_WIDE_CLAIM_INVALID_POLICY = "invalid_proof_creates_no_terminal_outcome"
PARTY_WIDE_CLAIM_UNAVAILABLE_POLICY = "unavailable_proof_creates_no_terminal_outcome"
PARTY_WIDE_CLAIM_SEARCH_POLICY = "dedicated_exact_claim_proof_without_search_fallback"
PARTY_WIDE_CLAIM_PUBLIC_POLICY = "private_internal_contract_without_public_surface"

PARTY_WIDE_CLAIM_MAXIMUM_UNRESOLVED_TRICKS = 5
PARTY_WIDE_CLAIM_PROOF_QUANTIFIERS = PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1_QUANTIFIERS

_RELATIVE_PLAYER_IDS = frozenset({"me", "left", "right"})


def _require_stable_player_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    if value in _RELATIVE_PLAYER_IDS:
        raise ValueError(f"{field_name} must be a stable non-relative Player ID.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class PartyWideAllRemainingTricksClaimV1:
    """One private structured assertion by a member of a complete claiming party."""

    party_wide_claim_version: int
    kind: str
    claimant_player_id: str
    claiming_party: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.party_wide_claim_version, bool)
            or not isinstance(self.party_wide_claim_version, int)
            or self.party_wide_claim_version != PARTY_WIDE_CLAIM_VERSION
        ):
            raise ValueError(
                f"party_wide_claim_version must be exactly {PARTY_WIDE_CLAIM_VERSION}."
            )
        if self.kind != PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND:
            raise ValueError("kind must be 'party_wide_all_remaining_tricks_claim'.")
        _require_stable_player_id(self.claimant_player_id, "claimant_player_id")
        if self.claiming_party not in PARTY_WIDE_CLAIMING_PARTIES:
            raise ValueError(f"claiming_party must be one of {list(PARTY_WIDE_CLAIMING_PARTIES)}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_version": self.party_wide_claim_version,
            "kind": self.kind,
            "claimant_player_id": self.claimant_player_id,
            "claiming_party": self.claiming_party,
        }


def build_party_wide_all_remaining_tricks_claim_v1(
    *,
    claimant_player_id: str,
    claiming_party: str,
) -> PartyWideAllRemainingTricksClaimV1:
    return PartyWideAllRemainingTricksClaimV1(
        party_wide_claim_version=PARTY_WIDE_CLAIM_VERSION,
        kind=PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_KIND,
        claimant_player_id=claimant_player_id,
        claiming_party=claiming_party,
    )


def validate_party_wide_claim_against_evidence_v1(
    claim: PartyWideAllRemainingTricksClaimV1,
    evidence: object,
) -> None:
    """Reconciles the asserting Player with the complete claiming party."""
    if not isinstance(claim, PartyWideAllRemainingTricksClaimV1):
        raise ValueError("claim must be a PartyWideAllRemainingTricksClaimV1.")
    players = getattr(evidence, "players", None)
    declarer_player_id = getattr(evidence, "declarer_player_id", None)
    if not isinstance(players, tuple) or not isinstance(declarer_player_id, str):
        raise ValueError("evidence must provide exact party-wide Claim participants.")
    participant_ids = tuple(getattr(player, "player_id", None) for player in players)
    if claim.claimant_player_id not in participant_ids:
        raise ValueError("claimant_player_id must identify one Evidence participant.")
    if claim.claiming_party == "declarer":
        if claim.claimant_player_id != declarer_player_id:
            raise ValueError("A Declarer Claim must be asserted by the Declarer.")
    elif claim.claimant_player_id == declarer_player_id:
        raise ValueError("A Defender Claim must be asserted by one of the two Defenders.")
