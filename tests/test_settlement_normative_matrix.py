import importlib
from dataclasses import FrozenInstanceError, replace
from typing import get_args

import pytest

from skat_ai import settlement_normative_matrix as matrix
from skat_ai.game_end import VALID_GAME_END_REASONS
from skat_ai.game_shortening import GameShortening
from skat_ai.historical_game_end import HISTORICAL_GAME_END_REASONS
from skat_ai.historical_game_event import HistoricalGameEvent

EXPECTED_CASE_IDS = (
    "claim_boundary.decision.generalized_non_jack_open_throw_exclusion",
    "claim_boundary.decision.generalized_rule_violation_correction",
    "claim_boundary.decision.party_wide_all_remaining_tricks_claim",
    "claim_boundary.decision.specific_future_trick_count_claim",
    "claim_boundary.decision.specific_future_trick_identity_claim",
    "claim_boundary.excluded.arbitrary_event_streams",
    "claim_boundary.excluded.defender_open_play_beyond_five_tricks",
    "claim_boundary.excluded.free_text_claims",
    "claim_boundary.excluded.generative_adjudication",
    "claim_boundary.excluded.natural_language_interpretation",
    "claim_boundary.excluded.simultaneous_throws",
    "claim_boundary.excluded.unclassified_conduct",
    "claim_boundary.excluded.unlimited_proof",
    "completion.normal.null.hand",
    "completion.normal.null.hand_ouvert",
    "completion.normal.null.ouvert",
    "completion.normal.null.plain",
    "completion.normal.suit_grand",
    "contract.level.achieved_schneider_schwarz",
    "contract.level.announced_schneider_schwarz_ouvert",
    "contract.level.failed_announced_schneider_schwarz_ouvert",
    "contract.null.impossible.external_replacement",
    "contract.null.impossible.missing_external_replacement",
    "contract.overbid.suit_grand_supported",
    "evidence.contradictory",
    "evidence.incomplete",
    "historical.continuation.declarer_card_exposure_then_normal_completion",
    "historical.continuation.defender_open_play_then_normal_completion",
    "historical.sequence.continuation_then_terminal_shortening",
    "historical.sequence.multiple_non_terminal_continuations",
    "historical.terminal.declarer_card_exposure",
    "historical.terminal.declarer_card_exposure.preexisting",
    "historical.terminal.declarer_card_exposure.uncovered_requirement",
    "historical.terminal.declarer_concession",
    "historical.terminal.defender_concession",
    "historical.terminal.defender_concession.preexisting",
    "historical.terminal.defender_open_play",
    "historical.terminal.defender_open_play.preexisting",
    "historical.terminal.normal_completion",
    "historical.terminal.open_card_throw",
    "historical.terminal.open_card_throw.preexisting",
    "historical.terminal.open_card_throw.uncovered_requirement",
    "legacy.declarer_claimed_remaining_tricks",
    "legacy.declarer_conceded_remaining_tricks",
    "legacy.defenders_conceded_remaining_tricks",
    "ongoing.not_ended",
    "structured_shortening.declarer_card_exposure.accepted_preexisting",
    "structured_shortening.declarer_card_exposure.accepted_undecided",
    "structured_shortening.declarer_card_exposure.accepted_undecided_uncovered",
    "structured_shortening.declarer_card_exposure.rejected_continuation",
    "structured_shortening.declarer_concession",
    "structured_shortening.defender_concession.preexisting",
    "structured_shortening.defender_concession.undecided",
    "structured_shortening.defender_open_play.invalid_proof",
    "structured_shortening.defender_open_play.preexisting",
    "structured_shortening.defender_open_play.proof_evaluation",
    "structured_shortening.defender_open_play.valid_proof",
    "structured_shortening.defender_open_play_continuation",
    "structured_shortening.open_card_throw.preexisting",
    "structured_shortening.open_card_throw.undecided",
    "structured_shortening.open_card_throw.undecided_uncovered_requirement",
)

EXPECTED_SUPPORTED_CLAIM_CASE_IDS = (
    "claim_boundary.decision.party_wide_all_remaining_tricks_claim",
)

EXPECTED_IMPLEMENTATION_REQUIRED_CLAIM_CASE_IDS: tuple[str, ...] = ()

EXPECTED_NOT_SUPPORTED_CLAIM_CASE_IDS = (
    "claim_boundary.decision.generalized_non_jack_open_throw_exclusion",
    "claim_boundary.decision.generalized_rule_violation_correction",
    "claim_boundary.decision.specific_future_trick_count_claim",
    "claim_boundary.decision.specific_future_trick_identity_claim",
    "claim_boundary.excluded.arbitrary_event_streams",
    "claim_boundary.excluded.defender_open_play_beyond_five_tricks",
    "claim_boundary.excluded.free_text_claims",
    "claim_boundary.excluded.generative_adjudication",
    "claim_boundary.excluded.natural_language_interpretation",
    "claim_boundary.excluded.simultaneous_throws",
    "claim_boundary.excluded.unclassified_conduct",
    "claim_boundary.excluded.unlimited_proof",
    "historical.sequence.multiple_non_terminal_continuations",
)


def _cases_for_family(scenario_family: str) -> tuple[matrix.NormativeSettlementCase, ...]:
    return tuple(
        case
        for case in matrix.get_normative_settlement_cases()
        if case.scenario_family == scenario_family
    )


def _runtime_union_kinds(union_alias) -> set[str]:
    kinds = set()
    for member in get_args(union_alias.__value__):
        member_module = importlib.import_module(member.__module__)
        member_kinds = {
            value
            for name, value in vars(member_module).items()
            if name.endswith("_KIND") and isinstance(value, str)
        }
        assert len(member_kinds) == 1, (
            f"Cannot derive one runtime kind for union member {member.__name__}."
        )
        kinds.update(member_kinds)
    return kinds


def test_matrix_version_order_identity_and_lookup_are_stable() -> None:
    cases = matrix.get_normative_settlement_cases()
    case_ids = tuple(case.case_id for case in cases)

    assert matrix.SETTLEMENT_NORMATIVE_MATRIX_VERSION == 3
    assert cases is matrix.get_normative_settlement_cases()
    assert case_ids == EXPECTED_CASE_IDS
    assert case_ids == tuple(sorted(case_ids))
    assert len(case_ids) == len(set(case_ids)) == 61
    for case in cases:
        assert matrix.get_normative_settlement_case(case.case_id) is case
    with pytest.raises(KeyError, match="Unknown normative settlement case"):
        matrix.get_normative_settlement_case("missing.case")


def test_matrix_and_nested_contract_values_are_immutable() -> None:
    cases = matrix.get_normative_settlement_cases()
    case = cases[0]

    assert isinstance(cases, tuple)
    assert isinstance(case.official_rule_references, tuple)
    assert isinstance(case.product_contract_references, tuple)
    assert isinstance(case.implementation_modules, tuple)
    assert isinstance(case.proof_quantifiers, tuple)
    assert isinstance(case.delegated_terminal_case_ids, tuple)
    assert isinstance(case.notes, tuple)
    with pytest.raises(FrozenInstanceError):
        case.case_id = "changed.case"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "valid_values"),
    [
        ("implementation_status", matrix.VALID_IMPLEMENTATION_STATUSES),
        ("interpretation_scope", matrix.VALID_INTERPRETATION_SCOPES),
        ("evidence_class", matrix.VALID_EVIDENCE_CLASSES),
        ("winner_policy", matrix.VALID_WINNER_POLICIES),
        (
            "remaining_assignment_policy",
            matrix.VALID_REMAINING_ASSIGNMENT_POLICIES,
        ),
        ("level_policy", matrix.VALID_LEVEL_POLICIES),
        ("null_level_policy", frozenset({matrix.LEVEL_NOT_APPLICABLE})),
        ("overbid_policy", matrix.VALID_OVERBID_POLICIES),
        ("settlement_policy", matrix.VALID_SETTLEMENT_POLICIES),
        ("proof_policy", matrix.VALID_PROOF_POLICIES),
        ("terminal_effect", matrix.VALID_TERMINAL_EFFECTS),
    ],
)
def test_every_enum_like_value_is_stable_and_represented(
    field_name: str,
    valid_values: frozenset[str],
) -> None:
    represented = {getattr(case, field_name) for case in matrix.get_normative_settlement_cases()}

    assert represented <= valid_values
    assert represented


def test_matrix_self_validation_passes() -> None:
    matrix.validate_normative_settlement_matrix()


@pytest.mark.parametrize(
    ("case_id", "mutation"),
    [
        (
            "claim_boundary.decision.generalized_non_jack_open_throw_exclusion",
            lambda case: replace(case, implementation_status="future_status"),
        ),
        (
            "claim_boundary.decision.generalized_non_jack_open_throw_exclusion",
            lambda case: replace(case, winner_policy="future_winner"),
        ),
        (
            "claim_boundary.decision.generalized_non_jack_open_throw_exclusion",
            lambda case: replace(case, official_rule_references=()),
        ),
        (
            "claim_boundary.decision.party_wide_all_remaining_tricks_claim",
            lambda case: replace(case, proof_maximum_unresolved_tricks=6),
        ),
        (
            "claim_boundary.decision.party_wide_all_remaining_tricks_claim",
            lambda case: replace(case, implementation_modules=("skat_ai.future_claim",)),
        ),
        (
            "completion.normal.suit_grand",
            lambda case: replace(case, implementation_modules=()),
        ),
        (
            "completion.normal.suit_grand",
            lambda case: replace(case, notes=[]),
        ),
    ],
)
def test_invalid_values_and_supported_case_contracts_are_rejected(
    case_id: str,
    mutation,
) -> None:
    cases = list(matrix.get_normative_settlement_cases())
    index = next(index for index, case in enumerate(cases) if case.case_id == case_id)
    cases[index] = mutation(cases[index])

    with pytest.raises(ValueError):
        matrix.validate_normative_settlement_matrix(tuple(cases))


def test_duplicate_and_noncanonical_case_ids_are_rejected() -> None:
    cases = matrix.get_normative_settlement_cases()
    duplicate = (cases[0], replace(cases[1], case_id=cases[0].case_id), *cases[2:])
    reversed_cases = tuple(reversed(cases))

    with pytest.raises(ValueError, match="unique"):
        matrix.validate_normative_settlement_matrix(duplicate)
    with pytest.raises(ValueError, match="canonical"):
        matrix.validate_normative_settlement_matrix(reversed_cases)


def test_invalid_status_policy_combinations_are_rejected() -> None:
    cases = matrix.get_normative_settlement_cases()
    by_id = {case.case_id: index for index, case in enumerate(cases)}

    mutations = {
        "evidence.incomplete": {"winner_policy": matrix.FORCE_DECLARER},
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim": {
            "settlement_policy": matrix.NORMAL_SETTLEMENT
        },
        "claim_boundary.decision.specific_future_trick_count_claim": {
            "winner_policy": matrix.FORCE_DECLARER
        },
        "claim_boundary.excluded.free_text_claims": {"implementation_modules": ("skat_ai.future",)},
        "completion.normal.null.plain": {"level_policy": matrix.NORMAL_ACHIEVED_LEVELS},
        "ongoing.not_ended": {"settlement_policy": matrix.NORMAL_SETTLEMENT},
        "structured_shortening.defender_open_play_continuation": {
            "terminal_effect": matrix.TERMINAL
        },
        "completion.normal.suit_grand": {
            "proof_policy": matrix.DEFENDER_OPEN_PLAY_V1,
            "proof_quantifiers": matrix.DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        },
        "legacy.declarer_claimed_remaining_tricks": {"interpretation_scope": matrix.DIRECT_RULE},
        "structured_shortening.defender_concession.preexisting": {
            "winner_policy": matrix.FORCE_DECLARER
        },
        "historical.sequence.continuation_then_terminal_shortening": {
            "delegated_terminal_case_ids": ()
        },
    }
    for case_id, changes in mutations.items():
        changed = list(cases)
        index = by_id[case_id]
        changed[index] = replace(changed[index], **changes)
        with pytest.raises(ValueError):
            matrix.validate_normative_settlement_matrix(tuple(changed))


def test_every_runtime_game_shortening_kind_has_a_supported_matrix_case() -> None:
    represented = {
        case.game_end_kind
        for case in _cases_for_family("structured_shortening")
        if case.implementation_status == matrix.SUPPORTED_AS_IS
    }

    assert represented == _runtime_union_kinds(GameShortening)


def test_every_historical_terminal_kind_has_a_supported_matrix_case() -> None:
    represented = {
        case.game_end_kind
        for case in matrix.get_normative_settlement_cases()
        if case.implementation_status == matrix.SUPPORTED_AS_IS
        and case.game_end_kind in HISTORICAL_GAME_END_REASONS
    }

    assert represented == HISTORICAL_GAME_END_REASONS


def test_both_historical_continuation_kinds_have_supported_matrix_cases() -> None:
    represented = {
        case.game_end_kind
        for case in _cases_for_family("historical_continuation")
        if case.implementation_status == matrix.SUPPORTED_AS_IS
    }

    assert represented == _runtime_union_kinds(HistoricalGameEvent)


def test_every_legacy_runtime_game_end_reason_has_matrix_coverage() -> None:
    represented_supported = {
        case.game_end_kind
        for case in matrix.get_normative_settlement_cases()
        if case.implementation_status == matrix.SUPPORTED_AS_IS
    }

    assert set(VALID_GAME_END_REASONS) <= represented_supported
    legacy_cases = tuple(
        case
        for case in matrix.get_normative_settlement_cases()
        if case.game_end_kind in matrix.LEGACY_GAME_END_KINDS
    )
    assert {case.game_end_kind for case in legacy_cases} == matrix.LEGACY_GAME_END_KINDS
    assert all(
        case.interpretation_scope == matrix.LEGACY_COMPATIBILITY
        and case.remaining_assignment_policy == matrix.LEGACY_REMAINING_POINTS
        for case in legacy_cases
    )


def test_normal_completion_and_impossible_null_are_explicit() -> None:
    normal_cases = _cases_for_family("normal_completion")
    impossible_cases = _cases_for_family("impossible_null")

    assert {case.contract_scope for case in normal_cases} == {
        "suit_grand",
        "null",
        "null_hand",
        "null_ouvert",
        "null_hand_ouvert",
    }
    assert all(case.game_end_kind == "normal_completion" for case in normal_cases)
    assert {case.overbid_policy for case in impossible_cases} == {
        matrix.IMPOSSIBLE_NULL_EXTERNAL_REPLACEMENT,
        matrix.UNSUPPORTED_WITHOUT_REQUIRED_INPUT,
    }
    assert all(case.winner_policy == matrix.FORCE_DEFENDERS for case in impossible_cases)


def test_structured_claim_boundary_is_complete() -> None:
    represented = {
        case.game_end_kind
        for case in matrix.get_normative_settlement_cases()
        if case.implementation_status == matrix.SUPPORTED_AS_IS
    }

    assert {
        "declarer_concession",
        "defender_concession",
        "declarer_card_exposure",
        "declarer_card_exposure_continuation",
        "defender_open_play",
        "defender_open_play_continuation",
        "open_card_throw",
    } <= represented


def test_proof_policies_are_unique_to_their_approved_boundaries() -> None:
    proof_cases = tuple(
        case
        for case in matrix.get_normative_settlement_cases()
        if case.proof_policy != matrix.NO_PROOF
    )
    defender_proofs = tuple(
        case for case in proof_cases if case.proof_policy == matrix.DEFENDER_OPEN_PLAY_V1
    )
    open_throw_proofs = tuple(
        case for case in proof_cases if case.proof_policy == matrix.OPEN_THROW_JACK_EXCLUSION_V1
    )
    party_wide_proofs = tuple(
        case
        for case in proof_cases
        if case.proof_policy == matrix.PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1
    )

    assert defender_proofs
    assert all("defender_open_play" in case.game_end_kind for case in defender_proofs)
    assert all(
        case.proof_quantifiers
        == (
            ("exposing_defender", "existential"),
            ("declarer", "universal"),
            ("non_exposing_defender", "universal"),
        )
        for case in defender_proofs
    )
    assert all(case.proof_maximum_unresolved_tricks == 5 for case in defender_proofs)
    assert open_throw_proofs
    assert all(case.game_end_kind == "open_card_throw" for case in open_throw_proofs)
    assert all(not case.proof_quantifiers for case in open_throw_proofs)
    assert len(party_wide_proofs) == 1
    assert party_wide_proofs[0].proof_quantifiers == (
        ("claiming_party", "existential"),
        ("opposing_party", "universal"),
    )
    assert party_wide_proofs[0].proof_maximum_unresolved_tricks == 5
    assert not any(case.proof_policy == matrix.PROOF_DECISION_REQUIRED for case in proof_cases)
    assert {
        case.game_end_kind for case in proof_cases if case.proof_policy == matrix.PROOF_NOT_APPROVED
    } == {
        "defender_open_play_beyond_five_unresolved_tricks",
        "generalized_non_jack_open_throw_theoretical_exclusion",
        "specific_future_trick_count_claim",
        "specific_future_trick_identity_claim",
        "unlimited_claim_proof",
    }


def test_no_generic_search_is_a_claim_proof() -> None:
    forbidden_fragments = {
        "perfect_information_minimax",
        "compatible_world_minimax",
        "search_aggregation",
        "bounded_search",
    }

    for case in matrix.get_normative_settlement_cases():
        proof_contract = " ".join((case.proof_policy, *case.implementation_modules)).lower()
        assert all(fragment not in proof_contract for fragment in forbidden_fragments)

    approved_claim = matrix.get_normative_settlement_case(
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
    )
    assert any("no Generic Search fallback" in note for note in approved_claim.notes)


def test_level_sources_remain_distinct_and_null_has_no_levels() -> None:
    cases = matrix.get_normative_settlement_cases()
    represented_sources = {case.level_policy for case in cases}

    assert {
        matrix.NORMAL_ACHIEVED_LEVELS,
        matrix.DECLARED_AND_REQUIRED_LEVELS,
        matrix.ACCEPTED_CLAIMED_LEVEL,
        matrix.SECURED_OBSERVED_LEVELS_ONLY,
        matrix.RULE_ASSIGNED_IF_NOT_EXCLUDED,
        matrix.NO_ADDITIONAL_LEVEL,
    } <= represented_sources
    assert all(
        case.level_policy == matrix.LEVEL_NOT_APPLICABLE
        for case in cases
        if case.contract_scope.startswith("null")
    )
    assert all(case.null_level_policy == matrix.LEVEL_NOT_APPLICABLE for case in cases)


def test_continuations_never_define_terminal_settlement() -> None:
    continuations = tuple(
        case
        for case in matrix.get_normative_settlement_cases()
        if case.terminal_effect == matrix.NON_TERMINAL
    )

    assert continuations
    assert all(
        case.winner_policy == matrix.CONTINUE_WITHOUT_SETTLEMENT
        and case.remaining_assignment_policy == matrix.CONTINUE_PLAY
        and case.settlement_policy == matrix.NO_TERMINAL_SETTLEMENT
        and case.proof_policy == matrix.NO_PROOF
        for case in continuations
    )


def test_incomplete_and_contradictory_evidence_never_define_outcomes() -> None:
    unsafe_cases = tuple(
        case
        for case in matrix.get_normative_settlement_cases()
        if case.evidence_class in {matrix.INCOMPLETE, matrix.CONTRADICTORY}
    )

    assert {case.evidence_class for case in unsafe_cases} == {
        matrix.INCOMPLETE,
        matrix.CONTRADICTORY,
    }
    assert all(
        case.winner_policy == matrix.WINNER_UNRESOLVED
        and case.remaining_assignment_policy == matrix.REMAINING_UNRESOLVED
        and case.level_policy == matrix.LEVEL_UNRESOLVED
        and case.overbid_policy == matrix.OVERBID_UNRESOLVED
        and case.settlement_policy == matrix.SETTLEMENT_UNRESOLVED
        for case in unsafe_cases
    )


def test_bounded_historical_sequence_is_supported_by_terminal_delegation() -> None:
    case = matrix.get_normative_settlement_case(
        "historical.sequence.continuation_then_terminal_shortening"
    )

    assert case.implementation_status == matrix.SUPPORTED_AS_IS
    assert case.interpretation_scope == matrix.PRODUCT_BOUNDARY
    assert case.implementation_modules == (
        "skat_ai.historical_game",
        "skat_ai.historical_game_event",
    )
    assert case.stable_unavailable_reason is None
    assert case.winner_policy == matrix.WINNER_UNRESOLVED
    assert case.remaining_assignment_policy == matrix.REMAINING_UNRESOLVED
    assert case.level_policy == matrix.LEVEL_UNRESOLVED
    assert case.overbid_policy == matrix.OVERBID_UNRESOLVED
    delegated_cases = tuple(
        matrix.get_normative_settlement_case(case_id)
        for case_id in case.delegated_terminal_case_ids
    )
    assert {delegated.game_end_kind for delegated in delegated_cases} == (
        _runtime_union_kinds(GameShortening) | {"party_wide_all_remaining_tricks_claim"}
    )
    assert all(
        delegated.implementation_status == matrix.SUPPORTED_AS_IS
        and delegated.scenario_family in {"approved_claim", "structured_shortening"}
        and delegated.terminal_effect == matrix.TERMINAL
        for delegated in delegated_cases
    )
    assert "at most one supported non-terminal continuation event" in case.notes[0]
    assert "at most one supported terminal shortening" in case.notes[0]


def test_v1_claim_status_groups_are_exact_disjoint_and_complete() -> None:
    cases = matrix.get_normative_settlement_cases()
    supported_ids = tuple(
        case.case_id for case in cases if case.case_id in matrix.V1_SUPPORTED_CLAIM_CASE_IDS
    )
    implementation_required_ids = tuple(
        case.case_id
        for case in cases
        if case.implementation_status == matrix.IMPLEMENTATION_REQUIRED
    )
    not_supported_ids = tuple(
        case.case_id for case in cases if case.implementation_status == matrix.NOT_SUPPORTED_V1
    )

    assert matrix.V1_SUPPORTED_CLAIM_CASE_IDS == EXPECTED_SUPPORTED_CLAIM_CASE_IDS
    assert (
        matrix.V1_IMPLEMENTATION_REQUIRED_CLAIM_CASE_IDS
        == EXPECTED_IMPLEMENTATION_REQUIRED_CLAIM_CASE_IDS
    )
    assert matrix.V1_NOT_SUPPORTED_CLAIM_CASE_IDS == EXPECTED_NOT_SUPPORTED_CLAIM_CASE_IDS
    assert matrix.VALID_IMPLEMENTATION_STATUSES == frozenset(
        {
            matrix.SUPPORTED_AS_IS,
            matrix.IMPLEMENTATION_REQUIRED,
            matrix.DECISION_REQUIRED,
            matrix.NOT_SUPPORTED_V1,
        }
    )
    assert supported_ids == EXPECTED_SUPPORTED_CLAIM_CASE_IDS
    assert implementation_required_ids == EXPECTED_IMPLEMENTATION_REQUIRED_CLAIM_CASE_IDS
    assert not_supported_ids == EXPECTED_NOT_SUPPORTED_CLAIM_CASE_IDS
    assert set(implementation_required_ids).isdisjoint(not_supported_ids)
    assert not any(case.implementation_status == matrix.DECISION_REQUIRED for case in cases)
    assert not any(case.implementation_status == "out_of_scope_v0_11" for case in cases)


def test_approved_party_wide_claim_boundary_is_exact_and_executable() -> None:
    case = matrix.get_normative_settlement_case(
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
    )

    assert case.scenario_family == "approved_claim"
    assert case.game_end_kind == "party_wide_all_remaining_tricks_claim"
    assert case.contract_scope == "all_supported_contracts"
    assert case.pre_end_decision_state == "undecided_or_preexisting"
    assert case.implementation_status == matrix.SUPPORTED_AS_IS
    assert case.interpretation_scope == matrix.APPROVED_BOUNDED
    assert case.evidence_class == matrix.BOUNDED_EXACT_PROOF
    assert case.winner_policy == matrix.PROOF_DEPENDENT
    assert case.remaining_assignment_policy == matrix.REMAINING_PROOF_DEPENDENT
    assert case.level_policy == matrix.NORMAL_ACHIEVED_LEVELS
    assert case.null_level_policy == matrix.LEVEL_NOT_APPLICABLE
    assert case.overbid_policy == matrix.PRESERVE_REQUIRED_VALUE
    assert case.settlement_policy == matrix.EXISTING_SHORTENING_SETTLEMENT
    assert case.proof_policy == matrix.PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1
    assert case.proof_quantifiers == (
        ("claiming_party", "existential"),
        ("opposing_party", "universal"),
    )
    assert case.proof_quantifiers == matrix.PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1_QUANTIFIERS
    assert case.proof_maximum_unresolved_tricks == 5
    assert case.terminal_effect == matrix.TERMINAL
    assert case.implementation_modules == (
        "skat_ai.historical_game_end",
        "skat_ai.historical_party_wide_claim",
        "skat_ai.party_wide_claim_proof_executor",
        "skat_ai.party_wide_claim_adjudication",
    )
    assert case.stable_unavailable_reason is None
    notes = " ".join(case.notes)
    assert "Retrospective-only complete-world evidence" in notes
    assert "maximum of five unresolved Tricks" in notes
    assert "valid proof assigns every unresolved Trick to the claiming party" in notes
    assert "invalid proof creates no terminal outcome" in notes
    assert "Unavailable proof creates no terminal outcome" in notes
    assert "no automatic opposing-party penalty fallback" in notes
    assert "no Generic Search fallback" in notes
    assert "not an information-set-policy Claim" in notes


def test_every_durable_v1_exclusion_is_unresolved_and_module_free() -> None:
    cases = tuple(
        matrix.get_normative_settlement_case(case_id)
        for case_id in EXPECTED_NOT_SUPPORTED_CLAIM_CASE_IDS
    )

    assert {case.game_end_kind for case in cases} == {
        "arbitrary_length_event_streams",
        "defender_open_play_beyond_five_unresolved_tricks",
        "free_text_claim",
        "generalized_non_jack_open_throw_theoretical_exclusion",
        "generalized_rule_violation_correction",
        "generative_adjudication",
        "multiple_non_terminal_continuation_events",
        "natural_language_interpretation",
        "simultaneous_throws",
        "specific_future_trick_count_claim",
        "specific_future_trick_identity_claim",
        "unclassified_conduct",
        "unlimited_claim_proof",
    }
    assert all(
        case.implementation_status == matrix.NOT_SUPPORTED_V1
        and case.interpretation_scope == matrix.PRODUCT_BOUNDARY
        and case.evidence_class == matrix.EVIDENCE_NOT_APPLICABLE
        and case.winner_policy == matrix.WINNER_UNRESOLVED
        and case.remaining_assignment_policy == matrix.REMAINING_UNRESOLVED
        and case.level_policy == matrix.LEVEL_UNRESOLVED
        and case.overbid_policy == matrix.OVERBID_UNRESOLVED
        and case.settlement_policy == matrix.SETTLEMENT_UNRESOLVED
        and case.terminal_effect == matrix.NOT_A_RUNTIME_CASE
        and case.stable_unavailable_reason == matrix.NOT_SUPPORTED_V1
        and not case.implementation_modules
        and not case.proof_quantifiers
        and case.proof_maximum_unresolved_tricks is None
        and not case.delegated_terminal_case_ids
        for case in cases
    )


def test_existing_defender_open_play_proof_outcomes_are_unchanged() -> None:
    expected_policies = {
        "structured_shortening.defender_open_play.invalid_proof": (
            matrix.FORCE_DECLARER,
            matrix.ASSIGN_TO_DECLARER,
            matrix.DECLARED_AND_REQUIRED_LEVELS,
        ),
        "structured_shortening.defender_open_play.preexisting": (
            matrix.PRESERVE_PREEXISTING_DECISION,
            matrix.REMAINING_PROOF_DEPENDENT,
            matrix.SECURED_OBSERVED_LEVELS_ONLY,
        ),
        "structured_shortening.defender_open_play.proof_evaluation": (
            matrix.PROOF_DEPENDENT,
            matrix.REMAINING_PROOF_DEPENDENT,
            matrix.DECLARED_AND_REQUIRED_LEVELS,
        ),
        "structured_shortening.defender_open_play.valid_proof": (
            matrix.NORMAL_COMPLETION,
            matrix.ASSIGN_TO_DEFENDERS,
            matrix.SECURED_OBSERVED_LEVELS_ONLY,
        ),
    }

    for case_id, expected in expected_policies.items():
        case = matrix.get_normative_settlement_case(case_id)
        assert (
            case.winner_policy,
            case.remaining_assignment_policy,
            case.level_policy,
        ) == expected
        assert case.proof_policy == matrix.DEFENDER_OPEN_PLAY_V1
        assert case.proof_quantifiers == matrix.DEFENDER_OPEN_PLAY_V1_QUANTIFIERS
        assert case.proof_maximum_unresolved_tricks == 5
        assert case.settlement_policy == matrix.EXISTING_SHORTENING_SETTLEMENT


def test_claim_group_mutations_are_rejected() -> None:
    cases = matrix.get_normative_settlement_cases()
    by_id = {case.case_id: index for index, case in enumerate(cases)}
    mutations = (
        (
            EXPECTED_SUPPORTED_CLAIM_CASE_IDS[0],
            {"implementation_status": matrix.NOT_SUPPORTED_V1},
        ),
        (
            EXPECTED_NOT_SUPPORTED_CLAIM_CASE_IDS[0],
            {"implementation_status": matrix.IMPLEMENTATION_REQUIRED},
        ),
        (
            EXPECTED_NOT_SUPPORTED_CLAIM_CASE_IDS[-1],
            {"stable_unavailable_reason": "old_milestone_reason"},
        ),
        (
            "claim_boundary.excluded.defender_open_play_beyond_five_tricks",
            {"proof_policy": matrix.NO_PROOF},
        ),
        (
            "claim_boundary.excluded.unlimited_proof",
            {"proof_policy": matrix.NO_PROOF},
        ),
    )

    for case_id, changes in mutations:
        changed = list(cases)
        index = by_id[case_id]
        changed[index] = replace(changed[index], **changes)
        with pytest.raises(ValueError):
            matrix.validate_normative_settlement_matrix(tuple(changed))
