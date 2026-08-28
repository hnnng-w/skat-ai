from skatmind.errors import SkatMindInvariantError
from skatmind.exact_search_state import (
    ExactSearchState,
    ExactSearchTransition,
    apply_exact_search_card,
    get_exact_search_legal_cards,
)
from skatmind.party_wide_claim_contracts import (
    PartyWideAllRemainingTricksClaimV1,
    validate_party_wide_claim_against_evidence_v1,
)
from skatmind.party_wide_claim_evidence import (
    PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
    PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION,
    PartyWideClaimEvidenceV1,
    PartyWideClaimExactStateContextV1,
)
from skatmind.party_wide_claim_proof_contracts import (
    PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION,
    PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS,
    PartyWideClaimProofMoveV1,
    PartyWideClaimProofPreparationV1,
    PartyWideClaimProofRequestV1,
    PartyWideClaimProofResultV1,
    build_invalid_party_wide_claim_proof_result_v1,
    build_party_wide_claim_proof_assignment_v1,
    build_party_wide_claim_proof_move_v1,
    build_party_wide_claim_proof_request_v1,
    build_unavailable_party_wide_claim_proof_result_v1,
    build_valid_party_wide_claim_proof_result_v1,
)

PARTY_WIDE_CLAIM_PROOF_EXECUTOR_VERSION = 1

PARTY_WIDE_CLAIM_PROOF_EXECUTION_METHOD = (
    "party_wide_all_remaining_tricks_exact_and_or_v1"
)
PARTY_WIDE_CLAIM_PROOF_EXECUTION_POLICY = "exhaustive_complete_world_and_or_proof"
PARTY_WIDE_CLAIM_PROOF_ACTOR_POLICY = (
    "claiming_party_existential_opposing_party_universal"
)
PARTY_WIDE_CLAIM_PROOF_MOVE_ORDER_POLICY = "canonical_legal_card_order"
PARTY_WIDE_CLAIM_PROOF_MEMOIZATION_POLICY = (
    "exact_state_outcome_and_representative_suffix"
)
PARTY_WIDE_CLAIM_PROOF_TERMINAL_POLICY = (
    "opposing_trick_invalidates_otherwise_normal_completion_validates"
)
PARTY_WIDE_CLAIM_PROOF_LINE_POLICY = "first_canonical_decisive_branch"
PARTY_WIDE_CLAIM_PROOF_COUNTER_POLICY = (
    "unique_uncached_exact_states_and_proof_terminal_states"
)
PARTY_WIDE_CLAIM_PROOF_COMPLETION_POLICY = (
    "complete_without_partial_timeout_or_budget"
)

type _ProofOutcome = tuple[bool, tuple[PartyWideClaimProofMoveV1, ...]]

_SOURCE_EVIDENCE_UNAVAILABLE_REASONS = frozenset(
    PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS[:2]
)


def _require_exact_version(value: object, expected: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"{field_name} must be exactly {expected}.")


def _reconcile_available_preparation(
    preparation: PartyWideClaimProofPreparationV1,
) -> PartyWideClaimProofRequestV1:
    try:
        _require_exact_version(
            preparation.party_wide_claim_proof_preparation_version,
            PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION,
            "party_wide_claim_proof_preparation_version",
        )
        if preparation.status != "available":
            raise ValueError("Execution requires an available or unavailable preparation.")
        if preparation.unavailable_reason is not None:
            raise ValueError("An available preparation cannot have an unavailable reason.")
        if not isinstance(preparation.claim, PartyWideAllRemainingTricksClaimV1):
            raise ValueError("An available preparation must retain one structured Claim.")
        preparation.claim.__post_init__()
        if not isinstance(preparation.evidence, PartyWideClaimEvidenceV1):
            raise ValueError("An available preparation must retain exact Evidence.")
        _require_exact_version(
            preparation.evidence.party_wide_claim_evidence_version,
            PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
            "party_wide_claim_evidence_version",
        )
        if not isinstance(preparation.request, PartyWideClaimProofRequestV1):
            raise ValueError("An available preparation must retain one Proof Request.")
        retained_context = preparation.request.exact_state_context
        if not isinstance(retained_context, PartyWideClaimExactStateContextV1):
            raise ValueError("An available preparation must retain one Exact State Context.")
        _require_exact_version(
            retained_context.party_wide_claim_exact_state_context_version,
            PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION,
            "party_wide_claim_exact_state_context_version",
        )
        if not isinstance(retained_context.exact_state, ExactSearchState):
            raise ValueError("An available preparation must retain one ExactSearchState.")

        rebuilt_request = build_party_wide_claim_proof_request_v1(
            claim=preparation.claim,
            evidence=preparation.evidence,
            exact_state_context=retained_context,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Available party-wide Claim proof preparation is internally inconsistent."
        ) from error

    if rebuilt_request != preparation.request:
        raise SkatMindInvariantError(
            "Available party-wide Claim Proof Request does not equal its canonical rebuild."
        )
    return rebuilt_request


def _build_unavailable_result(
    preparation: PartyWideClaimProofPreparationV1,
) -> PartyWideClaimProofResultV1:
    try:
        _require_exact_version(
            preparation.party_wide_claim_proof_preparation_version,
            PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION,
            "party_wide_claim_proof_preparation_version",
        )
        if preparation.status != "unavailable":
            raise ValueError("Unavailable passthrough requires an unavailable preparation.")
        if not isinstance(preparation.claim, PartyWideAllRemainingTricksClaimV1):
            raise ValueError("An unavailable preparation must retain one structured Claim.")
        preparation.claim.__post_init__()
        unavailable_reason = preparation.unavailable_reason
        if unavailable_reason not in PARTY_WIDE_CLAIM_PROOF_UNAVAILABLE_REASONS:
            raise ValueError("Unavailable preparation reason is not canonical.")
        if preparation.request is not None:
            raise ValueError("An unavailable preparation cannot retain a Proof Request.")
        if unavailable_reason in _SOURCE_EVIDENCE_UNAVAILABLE_REASONS:
            if preparation.evidence is not None:
                raise ValueError("Unavailable source Evidence must not be retained.")
        else:
            if not isinstance(preparation.evidence, PartyWideClaimEvidenceV1):
                raise ValueError("Unavailable structural preparation must retain exact Evidence.")
            _require_exact_version(
                preparation.evidence.party_wide_claim_evidence_version,
                PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
                "party_wide_claim_evidence_version",
            )
            validate_party_wide_claim_against_evidence_v1(
                preparation.claim, preparation.evidence
            )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Unavailable party-wide Claim proof preparation is internally inconsistent."
        ) from error

    return build_unavailable_party_wide_claim_proof_result_v1(
        preparation=preparation,
        unavailable_reason=unavailable_reason,
    )


def _build_proof_move(
    transition: ExactSearchTransition,
    flat_to_stable: dict[str, str],
) -> PartyWideClaimProofMoveV1:
    try:
        resolution = transition.completed_trick
        return build_party_wide_claim_proof_move_v1(
            player_id=flat_to_stable[transition.actor],
            card=transition.card,
            completed_trick_winner_player_id=(
                flat_to_stable[resolution.winner_player] if resolution is not None else None
            ),
            completed_trick_winner_party=(
                resolution.winner_side if resolution is not None else None
            ),
        )
    except (KeyError, ValueError) as error:
        raise SkatMindInvariantError(
            "Exact Claim-proof transition cannot be represented with retained stable Players."
        ) from error


def execute_party_wide_claim_proof_v1(
    preparation: PartyWideClaimProofPreparationV1,
) -> PartyWideClaimProofResultV1:
    """Exhaustively proves one available exact party-wide all-remaining-Tricks Claim."""
    if not isinstance(preparation, PartyWideClaimProofPreparationV1):
        raise ValueError("preparation must be a PartyWideClaimProofPreparationV1.")
    if preparation.status == "unavailable":
        return _build_unavailable_result(preparation)

    request = _reconcile_available_preparation(preparation)
    evidence = request.evidence
    context = request.exact_state_context
    root = context.exact_state
    claiming_players = frozenset(context.claiming_party_flat_players)
    opposing_players = frozenset(context.opposing_party_flat_players)
    flat_to_stable = dict(context.flat_to_stable_player_map)
    if (
        claiming_players & opposing_players
        or claiming_players | opposing_players != frozenset(flat_to_stable)
        or len(flat_to_stable) != len(context.flat_to_stable_player_map)
    ):
        raise SkatMindInvariantError("Exact Claim-proof party mapping is internally inconsistent.")

    if preparation.claim.claiming_party == "declarer":
        root_opposing_completed_tricks = root.defender_completed_tricks

        def opposing_completed_tricks(state: ExactSearchState) -> int:
            return state.defender_completed_tricks

    else:
        root_opposing_completed_tricks = root.declarer_completed_tricks

        def opposing_completed_tricks(state: ExactSearchState) -> int:
            return state.declarer_completed_tricks

    memo: dict[ExactSearchState, _ProofOutcome] = {}
    evaluated_state_count = 0
    terminal_state_count = 0

    def traverse(state: ExactSearchState) -> _ProofOutcome:
        nonlocal evaluated_state_count, terminal_state_count
        if state in memo:
            return memo[state]

        evaluated_state_count += 1
        if opposing_completed_tricks(state) > root_opposing_completed_tricks:
            terminal_state_count += 1
            outcome: _ProofOutcome = (False, ())
            memo[state] = outcome
            return outcome
        if state.is_terminal:
            terminal_state_count += 1
            outcome = (True, ())
            memo[state] = outcome
            return outcome

        legal_cards = get_exact_search_legal_cards(state)
        if not legal_cards:
            raise SkatMindInvariantError(
                "A non-terminal exact Claim-proof state has no legal Card."
            )
        actor = state.next_player
        if actor in claiming_players:
            existential = True
        elif actor in opposing_players:
            existential = False
        else:
            raise SkatMindInvariantError(
                "Exact Claim-proof actor belongs to neither retained party."
            )

        fallback: _ProofOutcome | None = None
        for card in legal_cards:
            transition = apply_exact_search_card(state, card)
            child_satisfied, child_line = traverse(transition.next_state)
            candidate = (
                child_satisfied,
                (_build_proof_move(transition, flat_to_stable), *child_line),
            )
            if fallback is None:
                fallback = candidate
            if child_satisfied is existential:
                memo[state] = candidate
                return candidate

        if fallback is None:
            raise SkatMindInvariantError(
                "A non-terminal exact Claim-proof state produced no child outcome."
            )
        memo[state] = fallback
        return fallback

    satisfied, representative_line = traverse(root)
    memoized_state_count = len(memo)
    if memoized_state_count != evaluated_state_count:
        raise SkatMindInvariantError(
            "Exact Claim-proof memo size does not match unique evaluated-state count."
        )

    try:
        if satisfied:
            assignment = build_party_wide_claim_proof_assignment_v1(
                preparation=preparation,
                recipient_party=preparation.claim.claiming_party,
                assigned_trick_count=evidence.remaining_trick_count,
                assigned_card_count=evidence.unresolved_card_count,
                assigned_card_points=evidence.unresolved_card_points,
            )
            return build_valid_party_wide_claim_proof_result_v1(
                preparation=preparation,
                evaluated_state_count=evaluated_state_count,
                memoized_state_count=memoized_state_count,
                terminal_state_count=terminal_state_count,
                assignment=assignment,
                representative_line=representative_line,
            )
        return build_invalid_party_wide_claim_proof_result_v1(
            preparation=preparation,
            evaluated_state_count=evaluated_state_count,
            memoized_state_count=memoized_state_count,
            terminal_state_count=terminal_state_count,
            representative_line=representative_line,
        )
    except ValueError as error:
        raise SkatMindInvariantError(
            "Exact Claim-proof traversal produced an inconsistent complete Result."
        ) from error
