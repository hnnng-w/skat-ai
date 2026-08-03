import importlib
from dataclasses import FrozenInstanceError, replace
from typing import get_args

import pytest

from skat_ai import settlement_normative_matrix as matrix
from skat_ai.game_end import VALID_GAME_END_REASONS
from skat_ai.game_shortening import GameShortening
from skat_ai.historical_game_end import HISTORICAL_GAME_END_REASONS
from skat_ai.historical_game_event import HistoricalGameEvent


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

    assert matrix.SETTLEMENT_NORMATIVE_MATRIX_VERSION == 1
    assert cases is matrix.get_normative_settlement_cases()
    assert case_ids == tuple(sorted(case_ids))
    assert len(case_ids) == len(set(case_ids))
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
    represented = {
        getattr(case, field_name) for case in matrix.get_normative_settlement_cases()
    }

    assert represented == valid_values


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
        "claim_boundary.excluded.free_text_claims": {
            "implementation_modules": ("skat_ai.future",)
        },
        "completion.normal.null.plain": {
            "level_policy": matrix.NORMAL_ACHIEVED_LEVELS
        },
        "ongoing.not_ended": {"settlement_policy": matrix.NORMAL_SETTLEMENT},
        "structured_shortening.defender_open_play_continuation": {
            "terminal_effect": matrix.TERMINAL
        },
        "completion.normal.suit_grand": {
            "proof_policy": matrix.DEFENDER_OPEN_PLAY_V1,
            "proof_quantifiers": matrix.DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        },
        "legacy.declarer_claimed_remaining_tricks": {
            "interpretation_scope": matrix.DIRECT_RULE
        },
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
        for case in _cases_for_family("historical_terminal")
        if case.implementation_status == matrix.SUPPORTED_AS_IS
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
    assert {
        case.overbid_policy for case in impossible_cases
    } == {
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
        case
        for case in proof_cases
        if case.proof_policy == matrix.DEFENDER_OPEN_PLAY_V1
    )
    open_throw_proofs = tuple(
        case
        for case in proof_cases
        if case.proof_policy == matrix.OPEN_THROW_JACK_EXCLUSION_V1
    )

    assert defender_proofs
    assert all("defender_open_play" in case.game_end_kind for case in defender_proofs)
    assert all(
        case.proof_quantifiers == (
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
    assert all(
        case.scenario_family == "undecided_claim"
        for case in proof_cases
        if case.proof_policy == matrix.PROOF_DECISION_REQUIRED
    )
    assert {
        case.game_end_kind
        for case in proof_cases
        if case.proof_policy == matrix.PROOF_NOT_APPROVED
    } == {
        "defender_open_play_beyond_five_unresolved_tricks",
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
        proof_contract = " ".join(
            (
                case.proof_policy,
                *case.implementation_modules,
                *case.notes,
            )
        ).lower()
        assert all(fragment not in proof_contract for fragment in forbidden_fragments)


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


def test_bounded_historical_sequence_is_approved_but_not_implemented() -> None:
    case = matrix.get_normative_settlement_case(
        "historical.sequence.continuation_then_terminal_shortening"
    )

    assert case.implementation_status == matrix.IMPLEMENTATION_REQUIRED
    assert case.interpretation_scope == matrix.PRODUCT_BOUNDARY
    assert case.implementation_modules == ()
    assert case.winner_policy == matrix.WINNER_UNRESOLVED
    assert case.remaining_assignment_policy == matrix.REMAINING_UNRESOLVED
    assert case.level_policy == matrix.LEVEL_UNRESOLVED
    assert case.overbid_policy == matrix.OVERBID_UNRESOLVED
    delegated_cases = tuple(
        matrix.get_normative_settlement_case(case_id)
        for case_id in case.delegated_terminal_case_ids
    )
    assert {
        delegated.game_end_kind for delegated in delegated_cases
    } == _runtime_union_kinds(GameShortening)
    assert all(
        delegated.implementation_status == matrix.SUPPORTED_AS_IS
        and delegated.scenario_family == "structured_shortening"
        and delegated.terminal_effect == matrix.TERMINAL
        for delegated in delegated_cases
    )
    assert "at most one supported non-terminal continuation event" in case.notes[0]
    assert "at most one supported terminal shortening" in case.notes[0]


def test_undecided_specific_claims_and_exclusions_remain_non_executable() -> None:
    decision_kinds = {
        case.game_end_kind
        for case in matrix.get_normative_settlement_cases()
        if case.implementation_status == matrix.DECISION_REQUIRED
    }
    excluded_kinds = {
        case.game_end_kind
        for case in matrix.get_normative_settlement_cases()
        if case.implementation_status == matrix.OUT_OF_SCOPE_V0_11
    }

    assert {
        "party_wide_all_remaining_tricks_claim",
        "specific_future_trick_count_claim",
        "specific_future_trick_identity_claim",
        "generalized_non_jack_open_throw_theoretical_exclusion",
        "generalized_rule_violation_correction",
    } == decision_kinds
    assert {
        "free_text_claim",
        "natural_language_interpretation",
        "simultaneous_throws",
        "arbitrary_length_event_streams",
        "unlimited_claim_proof",
        "generative_adjudication",
        "unclassified_conduct",
        "multiple_non_terminal_continuation_events",
        "defender_open_play_beyond_five_unresolved_tricks",
    } == excluded_kinds
