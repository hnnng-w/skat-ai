import re
from dataclasses import dataclass

SETTLEMENT_NORMATIVE_MATRIX_VERSION = 1

SUPPORTED_AS_IS = "supported_as_is"
IMPLEMENTATION_REQUIRED = "implementation_required"
DECISION_REQUIRED = "decision_required"
OUT_OF_SCOPE_V0_11 = "out_of_scope_v0_11"
VALID_IMPLEMENTATION_STATUSES = frozenset(
    {
        SUPPORTED_AS_IS,
        IMPLEMENTATION_REQUIRED,
        DECISION_REQUIRED,
        OUT_OF_SCOPE_V0_11,
    }
)

DIRECT_RULE = "direct_rule"
APPROVED_BOUNDED = "approved_bounded"
LEGACY_COMPATIBILITY = "legacy_compatibility"
PRODUCT_BOUNDARY = "product_boundary"
NOT_APPLICABLE = "not_applicable"
VALID_INTERPRETATION_SCOPES = frozenset(
    {
        DIRECT_RULE,
        APPROVED_BOUNDED,
        LEGACY_COMPATIBILITY,
        PRODUCT_BOUNDARY,
        NOT_APPLICABLE,
    }
)

COMPLETE_OBSERVED = "complete_observed"
EXACT_COMPLETE_WORLD = "exact_complete_world"
BOUNDED_EXACT_PROOF = "bounded_exact_proof"
VALIDATED_PUBLIC_CONTINUATION = "validated_public_continuation"
VALIDATED_RULE_ASSIGNMENT = "validated_rule_assignment"
LEGACY_SIMPLIFIED = "legacy_simplified"
INCOMPLETE = "incomplete"
CONTRADICTORY = "contradictory"
EVIDENCE_NOT_APPLICABLE = "not_applicable"
VALID_EVIDENCE_CLASSES = frozenset(
    {
        COMPLETE_OBSERVED,
        EXACT_COMPLETE_WORLD,
        BOUNDED_EXACT_PROOF,
        VALIDATED_PUBLIC_CONTINUATION,
        VALIDATED_RULE_ASSIGNMENT,
        LEGACY_SIMPLIFIED,
        INCOMPLETE,
        CONTRADICTORY,
        EVIDENCE_NOT_APPLICABLE,
    }
)

NORMAL_COMPLETION = "normal_completion"
PRESERVE_PREEXISTING_DECISION = "preserve_preexisting_decision"
FORCE_DECLARER = "force_declarer"
FORCE_DEFENDERS = "force_defenders"
PROOF_DEPENDENT = "proof_dependent"
OPPOSING_PARTY_ASSIGNMENT = "opposing_party_assignment"
CONTINUE_WITHOUT_SETTLEMENT = "continue_without_settlement"
WINNER_UNRESOLVED = "unresolved"
VALID_WINNER_POLICIES = frozenset(
    {
        NORMAL_COMPLETION,
        PRESERVE_PREEXISTING_DECISION,
        FORCE_DECLARER,
        FORCE_DEFENDERS,
        PROOF_DEPENDENT,
        OPPOSING_PARTY_ASSIGNMENT,
        CONTINUE_WITHOUT_SETTLEMENT,
        WINNER_UNRESOLVED,
    }
)

NO_REMAINING_ASSIGNMENT = "none"
ASSIGN_TO_DECLARER = "assign_to_declarer"
ASSIGN_TO_DEFENDERS = "assign_to_defenders"
ASSIGN_TO_OPPOSING_PARTY = "assign_to_opposing_party"
REMAINING_PROOF_DEPENDENT = "proof_dependent"
CONTINUE_PLAY = "continue_play"
LEGACY_REMAINING_POINTS = "legacy_remaining_points"
REMAINING_UNRESOLVED = "unresolved"
VALID_REMAINING_ASSIGNMENT_POLICIES = frozenset(
    {
        NO_REMAINING_ASSIGNMENT,
        ASSIGN_TO_DECLARER,
        ASSIGN_TO_DEFENDERS,
        ASSIGN_TO_OPPOSING_PARTY,
        REMAINING_PROOF_DEPENDENT,
        CONTINUE_PLAY,
        LEGACY_REMAINING_POINTS,
        REMAINING_UNRESOLVED,
    }
)

NORMAL_ACHIEVED_LEVELS = "normal_achieved_levels"
DECLARED_AND_REQUIRED_LEVELS = "declared_and_required_levels"
ACCEPTED_CLAIMED_LEVEL = "accepted_claimed_level"
SECURED_OBSERVED_LEVELS_ONLY = "secured_observed_levels_only"
RULE_ASSIGNED_IF_NOT_EXCLUDED = "rule_assigned_if_not_excluded"
NO_ADDITIONAL_LEVEL = "no_additional_level"
LEVEL_NOT_APPLICABLE = "not_applicable"
LEVEL_UNRESOLVED = "unresolved"
VALID_LEVEL_POLICIES = frozenset(
    {
        NORMAL_ACHIEVED_LEVELS,
        DECLARED_AND_REQUIRED_LEVELS,
        ACCEPTED_CLAIMED_LEVEL,
        SECURED_OBSERVED_LEVELS_ONLY,
        RULE_ASSIGNED_IF_NOT_EXCLUDED,
        NO_ADDITIONAL_LEVEL,
        LEVEL_NOT_APPLICABLE,
        LEVEL_UNRESOLVED,
    }
)

NORMAL_SUPPORTED_OVERBID = "normal_supported_overbid"
PRESERVE_REQUIRED_VALUE = "preserve_required_value"
IMPOSSIBLE_NULL_EXTERNAL_REPLACEMENT = "impossible_null_external_replacement"
UNSUPPORTED_WITHOUT_REQUIRED_INPUT = "unsupported_without_required_input"
OVERBID_NOT_APPLICABLE = "not_applicable"
OVERBID_UNRESOLVED = "unresolved"
VALID_OVERBID_POLICIES = frozenset(
    {
        NORMAL_SUPPORTED_OVERBID,
        PRESERVE_REQUIRED_VALUE,
        IMPOSSIBLE_NULL_EXTERNAL_REPLACEMENT,
        UNSUPPORTED_WITHOUT_REQUIRED_INPUT,
        OVERBID_NOT_APPLICABLE,
        OVERBID_UNRESOLVED,
    }
)

NORMAL_SETTLEMENT = "normal_settlement"
DOUBLED_DECLARER_LOSS = "doubled_declarer_loss"
FIXED_NULL_VALUE = "fixed_null_value"
EXISTING_SHORTENING_SETTLEMENT = "existing_shortening_settlement"
IMPOSSIBLE_NULL_REPLACEMENT_SETTLEMENT = "impossible_null_external_replacement"
NO_TERMINAL_SETTLEMENT = "no_terminal_settlement"
SETTLEMENT_UNRESOLVED = "unresolved"
VALID_SETTLEMENT_POLICIES = frozenset(
    {
        NORMAL_SETTLEMENT,
        DOUBLED_DECLARER_LOSS,
        FIXED_NULL_VALUE,
        EXISTING_SHORTENING_SETTLEMENT,
        IMPOSSIBLE_NULL_REPLACEMENT_SETTLEMENT,
        NO_TERMINAL_SETTLEMENT,
        SETTLEMENT_UNRESOLVED,
    }
)

NO_PROOF = "none"
DEFENDER_OPEN_PLAY_V1 = "defender_open_play_v1"
OPEN_THROW_JACK_EXCLUSION_V1 = "open_throw_jack_exclusion_v1"
PROOF_DECISION_REQUIRED = "decision_required"
PROOF_NOT_APPROVED = "not_approved"
VALID_PROOF_POLICIES = frozenset(
    {
        NO_PROOF,
        DEFENDER_OPEN_PLAY_V1,
        OPEN_THROW_JACK_EXCLUSION_V1,
        PROOF_DECISION_REQUIRED,
        PROOF_NOT_APPROVED,
    }
)

TERMINAL = "terminal"
NON_TERMINAL = "non_terminal"
NOT_A_RUNTIME_CASE = "not_a_runtime_case"
VALID_TERMINAL_EFFECTS = frozenset({TERMINAL, NON_TERMINAL, NOT_A_RUNTIME_CASE})

DEFENDER_OPEN_PLAY_V1_QUANTIFIERS = (
    ("exposing_defender", "existential"),
    ("declarer", "universal"),
    ("non_exposing_defender", "universal"),
)

LEGACY_GAME_END_KINDS = frozenset(
    {
        "declarer_claimed_remaining_tricks",
        "declarer_conceded_remaining_tricks",
        "defenders_conceded_remaining_tricks",
    }
)
CONTINUATION_GAME_END_KINDS = frozenset(
    {
        "not_ended",
        "declarer_card_exposure_continuation",
        "defender_open_play_continuation",
    }
)


@dataclass(frozen=True)
class NormativeSettlementCase:
    case_id: str
    scenario_family: str
    official_rule_references: tuple[str, ...]
    product_contract_references: tuple[str, ...]
    game_end_kind: str
    contract_scope: str
    pre_end_decision_state: str
    evidence_class: str
    implementation_status: str
    interpretation_scope: str
    winner_policy: str
    remaining_assignment_policy: str
    level_policy: str
    null_level_policy: str
    overbid_policy: str
    settlement_policy: str
    proof_policy: str
    terminal_effect: str
    stable_unavailable_reason: str | None
    implementation_modules: tuple[str, ...]
    proof_quantifiers: tuple[tuple[str, str], ...]
    proof_maximum_unresolved_tricks: int | None
    delegated_terminal_case_ids: tuple[str, ...]
    notes: tuple[str, ...]


def _case(
    *,
    case_id: str,
    scenario_family: str,
    official: tuple[str, ...],
    product: tuple[str, ...],
    game_end_kind: str,
    contract_scope: str,
    pre_end_decision_state: str,
    evidence_class: str,
    implementation_status: str,
    interpretation_scope: str,
    winner_policy: str,
    remaining_assignment_policy: str,
    level_policy: str,
    overbid_policy: str,
    settlement_policy: str,
    null_level_policy: str = LEVEL_NOT_APPLICABLE,
    proof_policy: str = NO_PROOF,
    terminal_effect: str = TERMINAL,
    stable_unavailable_reason: str | None = None,
    implementation_modules: tuple[str, ...] = (),
    proof_quantifiers: tuple[tuple[str, str], ...] = (),
    proof_maximum_unresolved_tricks: int | None = None,
    delegated_terminal_case_ids: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> NormativeSettlementCase:
    return NormativeSettlementCase(
        case_id=case_id,
        scenario_family=scenario_family,
        official_rule_references=official,
        product_contract_references=product,
        game_end_kind=game_end_kind,
        contract_scope=contract_scope,
        pre_end_decision_state=pre_end_decision_state,
        evidence_class=evidence_class,
        implementation_status=implementation_status,
        interpretation_scope=interpretation_scope,
        winner_policy=winner_policy,
        remaining_assignment_policy=remaining_assignment_policy,
        level_policy=level_policy,
        null_level_policy=null_level_policy,
        overbid_policy=overbid_policy,
        settlement_policy=settlement_policy,
        proof_policy=proof_policy,
        terminal_effect=terminal_effect,
        stable_unavailable_reason=stable_unavailable_reason,
        implementation_modules=implementation_modules,
        proof_quantifiers=proof_quantifiers,
        proof_maximum_unresolved_tricks=proof_maximum_unresolved_tricks,
        delegated_terminal_case_ids=delegated_terminal_case_ids,
        notes=notes,
    )


_GAME_END_DOC = ("docs/game_end.md", "docs/requirements_traceability.md")
_SETTLEMENT_DOC = ("docs/game_end.md", "docs/v1_scope.md")
_HISTORICAL_DOC = ("docs/v1_scope.md", "docs/requirements_traceability.md")
_CLAIM_BOUNDARY_DOC = ("docs/settlement_normative_matrix.md", "docs/v1_scope.md")


SETTLEMENT_NORMATIVE_MATRIX = (
    _case(
        case_id="claim_boundary.decision.generalized_non_jack_open_throw_exclusion",
        scenario_family="undecided_claim",
        official=("ISkO 4.4.6",),
        product=_CLAIM_BOUNDARY_DOC,
        game_end_kind="generalized_non_jack_open_throw_theoretical_exclusion",
        contract_scope="suit_grand",
        pre_end_decision_state="not_applicable",
        evidence_class=EVIDENCE_NOT_APPLICABLE,
        implementation_status=DECISION_REQUIRED,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        proof_policy=PROOF_DECISION_REQUIRED,
        terminal_effect=NOT_A_RUNTIME_CASE,
        stable_unavailable_reason="product_decision_required",
    ),
    _case(
        case_id="claim_boundary.decision.generalized_rule_violation_correction",
        scenario_family="undecided_claim",
        official=("ISkO 4.1.1-4.2.3",),
        product=_CLAIM_BOUNDARY_DOC,
        game_end_kind="generalized_rule_violation_correction",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="not_applicable",
        evidence_class=EVIDENCE_NOT_APPLICABLE,
        implementation_status=DECISION_REQUIRED,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        proof_policy=PROOF_DECISION_REQUIRED,
        terminal_effect=NOT_A_RUNTIME_CASE,
        stable_unavailable_reason="product_decision_required",
    ),
    _case(
        case_id="claim_boundary.decision.party_wide_all_remaining_tricks_claim",
        scenario_family="undecided_claim",
        official=("ISkO 4.4.4-4.4.6",),
        product=_CLAIM_BOUNDARY_DOC,
        game_end_kind="party_wide_all_remaining_tricks_claim",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided_or_preexisting",
        evidence_class=EVIDENCE_NOT_APPLICABLE,
        implementation_status=DECISION_REQUIRED,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        proof_policy=PROOF_DECISION_REQUIRED,
        terminal_effect=NOT_A_RUNTIME_CASE,
        stable_unavailable_reason="product_decision_required",
    ),
    _case(
        case_id="claim_boundary.decision.specific_future_trick_count_claim",
        scenario_family="undecided_claim",
        official=("ISkO 4.4.4-4.4.6",),
        product=_CLAIM_BOUNDARY_DOC,
        game_end_kind="specific_future_trick_count_claim",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided_or_preexisting",
        evidence_class=EVIDENCE_NOT_APPLICABLE,
        implementation_status=DECISION_REQUIRED,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        proof_policy=PROOF_DECISION_REQUIRED,
        terminal_effect=NOT_A_RUNTIME_CASE,
        stable_unavailable_reason="product_decision_required",
    ),
    _case(
        case_id="claim_boundary.decision.specific_future_trick_identity_claim",
        scenario_family="undecided_claim",
        official=("ISkO 4.4.4-4.4.6",),
        product=_CLAIM_BOUNDARY_DOC,
        game_end_kind="specific_future_trick_identity_claim",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided_or_preexisting",
        evidence_class=EVIDENCE_NOT_APPLICABLE,
        implementation_status=DECISION_REQUIRED,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        proof_policy=PROOF_DECISION_REQUIRED,
        terminal_effect=NOT_A_RUNTIME_CASE,
        stable_unavailable_reason="product_decision_required",
    ),
    *(
        _case(
            case_id=f"claim_boundary.excluded.{case_id}",
            scenario_family="excluded_claim",
            official=("Not applicable",),
            product=_CLAIM_BOUNDARY_DOC,
            game_end_kind=game_end_kind,
            contract_scope="not_applicable",
            pre_end_decision_state="not_applicable",
            evidence_class=EVIDENCE_NOT_APPLICABLE,
            implementation_status=OUT_OF_SCOPE_V0_11,
            interpretation_scope=PRODUCT_BOUNDARY,
            winner_policy=WINNER_UNRESOLVED,
            remaining_assignment_policy=REMAINING_UNRESOLVED,
            level_policy=LEVEL_UNRESOLVED,
            overbid_policy=OVERBID_UNRESOLVED,
            settlement_policy=SETTLEMENT_UNRESOLVED,
            proof_policy=(
                PROOF_NOT_APPROVED
                if case_id in {
                    "defender_open_play_beyond_five_tricks",
                    "unlimited_proof",
                }
                else NO_PROOF
            ),
            terminal_effect=NOT_A_RUNTIME_CASE,
            stable_unavailable_reason="out_of_scope_v0_11",
        )
        for case_id, game_end_kind in (
            ("arbitrary_event_streams", "arbitrary_length_event_streams"),
            (
                "defender_open_play_beyond_five_tricks",
                "defender_open_play_beyond_five_unresolved_tricks",
            ),
            ("free_text_claims", "free_text_claim"),
            ("generative_adjudication", "generative_adjudication"),
            ("natural_language_interpretation", "natural_language_interpretation"),
            ("simultaneous_throws", "simultaneous_throws"),
            ("unclassified_conduct", "unclassified_conduct"),
            ("unlimited_proof", "unlimited_claim_proof"),
        )
    ),
    _case(
        case_id="completion.normal.null.hand",
        scenario_family="normal_completion",
        official=("ISkO 2.4.2", "ISkO 2.5.9", "ISkO 4.4.1"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="null_hand",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=OVERBID_NOT_APPLICABLE,
        settlement_policy=FIXED_NULL_VALUE,
        implementation_modules=("skat_ai.game_result", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="completion.normal.null.hand_ouvert",
        scenario_family="normal_completion",
        official=("ISkO 2.4.2", "ISkO 2.5.9", "ISkO 4.4.1"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="null_hand_ouvert",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=OVERBID_NOT_APPLICABLE,
        settlement_policy=FIXED_NULL_VALUE,
        implementation_modules=("skat_ai.game_result", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="completion.normal.null.ouvert",
        scenario_family="normal_completion",
        official=("ISkO 2.4.2", "ISkO 2.5.9", "ISkO 4.4.1"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="null_ouvert",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=OVERBID_NOT_APPLICABLE,
        settlement_policy=FIXED_NULL_VALUE,
        implementation_modules=("skat_ai.game_result", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="completion.normal.null.plain",
        scenario_family="normal_completion",
        official=("ISkO 2.4.2", "ISkO 2.5.9", "ISkO 4.4.1"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="null",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=OVERBID_NOT_APPLICABLE,
        settlement_policy=FIXED_NULL_VALUE,
        implementation_modules=("skat_ai.game_result", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="completion.normal.suit_grand",
        scenario_family="normal_completion",
        official=("ISkO 2.5.1-2.5.8", "ISkO 4.4.1"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="suit_grand",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=NORMAL_ACHIEVED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=NORMAL_SETTLEMENT,
        implementation_modules=(
            "skat_ai.game_result",
            "skat_ai.game_value",
            "skat_ai.final_settlement",
        ),
    ),
    _case(
        case_id="contract.level.achieved_schneider_schwarz",
        scenario_family="contract_level",
        official=("ISkO 2.5.4-2.5.8",),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="suit_grand",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=NORMAL_ACHIEVED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=NORMAL_SETTLEMENT,
        implementation_modules=("skat_ai.game_result", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="contract.level.announced_schneider_schwarz_ouvert",
        scenario_family="contract_level",
        official=("ISkO 2.5.4-2.5.8", "ISkO 3.5.1"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="suit_grand",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=NORMAL_SETTLEMENT,
        implementation_modules=("skat_ai.game_declaration", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="contract.level.failed_announced_schneider_schwarz_ouvert",
        scenario_family="contract_level",
        official=("ISkO 2.5.4-2.5.8", "ISkO 3.5.1"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="suit_grand",
        pre_end_decision_state="failed_declared_requirement",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=DOUBLED_DECLARER_LOSS,
        implementation_modules=("skat_ai.game_declaration", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="contract.null.impossible.external_replacement",
        scenario_family="impossible_null",
        official=(
            "ISkO 3.6.2",
            "International Skat Court decision collection 3.6.2 inquiries 1-3",
        ),
        product=_GAME_END_DOC,
        game_end_kind="impossible_null_declaration",
        contract_scope="null_all_variants",
        pre_end_decision_state="immediate_declaration_loss",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=IMPOSSIBLE_NULL_EXTERNAL_REPLACEMENT,
        settlement_policy=IMPOSSIBLE_NULL_REPLACEMENT_SETTLEMENT,
        implementation_modules=(
            "skat_ai.game_end",
            "skat_ai.impossible_null_settlement",
            "skat_ai.final_settlement",
        ),
        notes=(
            "The replacement is externally selected; the engine does not optimize alternatives.",
        ),
    ),
    _case(
        case_id="contract.null.impossible.missing_external_replacement",
        scenario_family="impossible_null",
        official=(
            "ISkO 3.6.2",
            "International Skat Court decision collection 3.6.2 inquiries 1-3",
        ),
        product=_GAME_END_DOC,
        game_end_kind="impossible_null_declaration",
        contract_scope="null_all_variants",
        pre_end_decision_state="immediate_declaration_loss",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=UNSUPPORTED_WITHOUT_REQUIRED_INPUT,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        stable_unavailable_reason="impossible_null_settlement",
        implementation_modules=(
            "skat_ai.game_end",
            "skat_ai.impossible_null_settlement",
            "skat_ai.final_settlement",
        ),
        notes=("The winner is final even when replacement valuation is unavailable.",),
    ),
    _case(
        case_id="contract.overbid.suit_grand_supported",
        scenario_family="supported_overbid",
        official=("ISkO 3.5.6", "ISkO 3.6.1", "ISkO 3.6.3-3.6.4"),
        product=_SETTLEMENT_DOC,
        game_end_kind="normal_completion",
        contract_scope="suit_grand",
        pre_end_decision_state="complete_observed_result",
        evidence_class=COMPLETE_OBSERVED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=DIRECT_RULE,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=DOUBLED_DECLARER_LOSS,
        implementation_modules=("skat_ai.overbid", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="evidence.contradictory",
        scenario_family="invalid_evidence",
        official=("Not applicable",),
        product=_CLAIM_BOUNDARY_DOC,
        game_end_kind="contradictory_evidence",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="unavailable",
        evidence_class=CONTRADICTORY,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=NOT_APPLICABLE,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        stable_unavailable_reason="contradictory_evidence",
        implementation_modules=("skat_ai.input_validation",),
    ),
    _case(
        case_id="evidence.incomplete",
        scenario_family="unavailable_evidence",
        official=("Not applicable",),
        product=_CLAIM_BOUNDARY_DOC,
        game_end_kind="incomplete_evidence",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="unavailable",
        evidence_class=INCOMPLETE,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=NOT_APPLICABLE,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        stable_unavailable_reason="incomplete_evidence",
        implementation_modules=("skat_ai.final_settlement",),
    ),
    _case(
        case_id="historical.continuation.declarer_card_exposure_then_normal_completion",
        scenario_family="historical_continuation",
        official=("ISkO 4.4.4",),
        product=_HISTORICAL_DOC,
        game_end_kind="declarer_card_exposure_continuation",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="not_terminal",
        evidence_class=VALIDATED_PUBLIC_CONTINUATION,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=CONTINUE_WITHOUT_SETTLEMENT,
        remaining_assignment_policy=CONTINUE_PLAY,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=NO_TERMINAL_SETTLEMENT,
        terminal_effect=NON_TERMINAL,
        implementation_modules=(
            "skat_ai.historical_game_event",
            "skat_ai.historical_declarer_card_exposure_continuation",
        ),
        notes=("The later normal completion is settled independently from this event.",),
    ),
    _case(
        case_id="historical.continuation.defender_open_play_then_normal_completion",
        scenario_family="historical_continuation",
        official=("ISkO 4.4.5", "ISkO 4.1.6"),
        product=_HISTORICAL_DOC,
        game_end_kind="defender_open_play_continuation",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="not_terminal",
        evidence_class=VALIDATED_PUBLIC_CONTINUATION,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=CONTINUE_WITHOUT_SETTLEMENT,
        remaining_assignment_policy=CONTINUE_PLAY,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=NO_TERMINAL_SETTLEMENT,
        terminal_effect=NON_TERMINAL,
        implementation_modules=(
            "skat_ai.historical_game_event",
            "skat_ai.historical_defender_open_play_continuation",
        ),
        notes=("The later normal completion is settled independently from this event.",),
    ),
    _case(
        case_id="historical.sequence.continuation_then_terminal_shortening",
        scenario_family="historical_event_chain",
        official=("ISkO 4.4.1-4.4.6",),
        product=_HISTORICAL_DOC,
        game_end_kind="supported_terminal_shortening_after_continuation",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="delegated_to_supported_terminal_case",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        terminal_effect=TERMINAL,
        implementation_modules=(
            "skat_ai.historical_game",
            "skat_ai.historical_game_event",
        ),
        delegated_terminal_case_ids=(
            "structured_shortening.declarer_card_exposure.accepted_preexisting",
            "structured_shortening.declarer_card_exposure.accepted_undecided",
            "structured_shortening.declarer_card_exposure.accepted_undecided_uncovered",
            "structured_shortening.declarer_concession",
            "structured_shortening.defender_concession.preexisting",
            "structured_shortening.defender_concession.undecided",
            "structured_shortening.defender_open_play.invalid_proof",
            "structured_shortening.defender_open_play.preexisting",
            "structured_shortening.defender_open_play.proof_evaluation",
            "structured_shortening.defender_open_play.valid_proof",
            "structured_shortening.open_card_throw.preexisting",
            "structured_shortening.open_card_throw.undecided",
            "structured_shortening.open_card_throw.undecided_uncovered_requirement",
        ),
        notes=(
            "Approved bound: at most one supported non-terminal continuation event "
            "followed by at most one supported terminal shortening.",
        ),
    ),
    _case(
        case_id="historical.sequence.multiple_non_terminal_continuations",
        scenario_family="excluded_claim",
        official=("ISkO 4.4.4-4.4.5",),
        product=_HISTORICAL_DOC,
        game_end_kind="multiple_non_terminal_continuation_events",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="not_applicable",
        evidence_class=EVIDENCE_NOT_APPLICABLE,
        implementation_status=OUT_OF_SCOPE_V0_11,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=WINNER_UNRESOLVED,
        remaining_assignment_policy=REMAINING_UNRESOLVED,
        level_policy=LEVEL_UNRESOLVED,
        overbid_policy=OVERBID_UNRESOLVED,
        settlement_policy=SETTLEMENT_UNRESOLVED,
        proof_policy=NO_PROOF,
        terminal_effect=NOT_A_RUNTIME_CASE,
        stable_unavailable_reason="out_of_scope_v0_11",
    ),
    _case(
        case_id="historical.terminal.declarer_card_exposure",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.4",),
        product=_HISTORICAL_DOC,
        game_end_kind="declarer_card_exposure",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="undecided_with_covered_requirement",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DECLARER,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=ACCEPTED_CLAIMED_LEVEL,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_declarer_card_exposure",
        ),
    ),
    _case(
        case_id="historical.terminal.declarer_card_exposure.preexisting",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.4", "ISkO 4.1.3"),
        product=_HISTORICAL_DOC,
        game_end_kind="declarer_card_exposure",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=SECURED_OBSERVED_LEVELS_ONLY,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_declarer_card_exposure",
        ),
    ),
    _case(
        case_id="historical.terminal.declarer_card_exposure.uncovered_requirement",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.4", "ISkO 3.6.1-3.6.4"),
        product=_HISTORICAL_DOC,
        game_end_kind="declarer_card_exposure",
        contract_scope="historical_suit_grand",
        pre_end_decision_state="undecided_with_uncovered_requirement",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=ACCEPTED_CLAIMED_LEVEL,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_declarer_card_exposure",
        ),
    ),
    _case(
        case_id="historical.terminal.declarer_concession",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.1-4.4.2",),
        product=_HISTORICAL_DOC,
        game_end_kind="declarer_concession",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="accepted_concession",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=NO_ADDITIONAL_LEVEL,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=DOUBLED_DECLARER_LOSS,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_declarer_concession",
        ),
    ),
    _case(
        case_id="historical.terminal.defender_concession",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.3", "ISkO 4.1.3-4.1.5"),
        product=_HISTORICAL_DOC,
        game_end_kind="defender_concession",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="undecided",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DECLARER,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_defender_concession",
        ),
    ),
    _case(
        case_id="historical.terminal.defender_concession.preexisting",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.3", "ISkO 4.1.3"),
        product=_HISTORICAL_DOC,
        game_end_kind="defender_concession",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=SECURED_OBSERVED_LEVELS_ONLY,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_defender_concession",
        ),
    ),
    _case(
        case_id="historical.terminal.defender_open_play",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.5", "ISkO 4.1.3-4.1.5"),
        product=_HISTORICAL_DOC,
        game_end_kind="defender_open_play",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="proof_evaluation",
        evidence_class=BOUNDED_EXACT_PROOF,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PROOF_DEPENDENT,
        remaining_assignment_policy=REMAINING_PROOF_DEPENDENT,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=DEFENDER_OPEN_PLAY_V1,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_defender_open_play",
            "skat_ai.exact_rest_trick_proof",
        ),
        proof_quantifiers=DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        proof_maximum_unresolved_tricks=5,
    ),
    _case(
        case_id="historical.terminal.defender_open_play.preexisting",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.5", "ISkO 4.1.3"),
        product=_HISTORICAL_DOC,
        game_end_kind="defender_open_play",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=BOUNDED_EXACT_PROOF,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=REMAINING_PROOF_DEPENDENT,
        level_policy=SECURED_OBSERVED_LEVELS_ONLY,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=DEFENDER_OPEN_PLAY_V1,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_defender_open_play",
            "skat_ai.exact_rest_trick_proof",
        ),
        proof_quantifiers=DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        proof_maximum_unresolved_tricks=5,
    ),
    _case(
        case_id="historical.terminal.normal_completion",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.1",),
        product=_HISTORICAL_DOC,
        game_end_kind="normal_completion",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="complete_observed_result",
        evidence_class=EXACT_COMPLETE_WORLD,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=NORMAL_ACHIEVED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=NORMAL_SETTLEMENT,
        implementation_modules=("skat_ai.historical_game", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="historical.terminal.open_card_throw",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.6",),
        product=_HISTORICAL_DOC,
        game_end_kind="open_card_throw",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="undecided",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=OPPOSING_PARTY_ASSIGNMENT,
        remaining_assignment_policy=ASSIGN_TO_OPPOSING_PARTY,
        level_policy=RULE_ASSIGNED_IF_NOT_EXCLUDED,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=OPEN_THROW_JACK_EXCLUSION_V1,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_open_card_throw",
            "skat_ai.theoretical_level_exclusion",
        ),
    ),
    _case(
        case_id="historical.terminal.open_card_throw.preexisting",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.6", "ISkO 4.1.3"),
        product=_HISTORICAL_DOC,
        game_end_kind="open_card_throw",
        contract_scope="historical_all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=ASSIGN_TO_OPPOSING_PARTY,
        level_policy=RULE_ASSIGNED_IF_NOT_EXCLUDED,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=OPEN_THROW_JACK_EXCLUSION_V1,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_open_card_throw",
            "skat_ai.theoretical_level_exclusion",
        ),
    ),
    _case(
        case_id="historical.terminal.open_card_throw.uncovered_requirement",
        scenario_family="historical_terminal",
        official=("ISkO 4.4.6", "ISkO 3.6.1-3.6.4"),
        product=_HISTORICAL_DOC,
        game_end_kind="open_card_throw",
        contract_scope="historical_suit_grand",
        pre_end_decision_state="undecided_with_uncovered_requirement",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=ASSIGN_TO_OPPOSING_PARTY,
        level_policy=RULE_ASSIGNED_IF_NOT_EXCLUDED,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=OPEN_THROW_JACK_EXCLUSION_V1,
        implementation_modules=(
            "skat_ai.historical_game_end",
            "skat_ai.historical_open_card_throw",
            "skat_ai.theoretical_level_exclusion",
        ),
    ),
    _case(
        case_id="legacy.declarer_claimed_remaining_tricks",
        scenario_family="legacy_remaining_points",
        official=("Not a direct official-rule representation",),
        product=_GAME_END_DOC,
        game_end_kind="declarer_claimed_remaining_tricks",
        contract_scope="legacy_suit_grand",
        pre_end_decision_state="incomplete_observed_points",
        evidence_class=LEGACY_SIMPLIFIED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=LEGACY_COMPATIBILITY,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=LEGACY_REMAINING_POINTS,
        level_policy=NORMAL_ACHIEVED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=NORMAL_SETTLEMENT,
        implementation_modules=("skat_ai.game_end", "skat_ai.final_settlement"),
        notes=("Remaining points go to the declarer; remaining trick ownership is not proven.",),
    ),
    _case(
        case_id="legacy.declarer_conceded_remaining_tricks",
        scenario_family="legacy_remaining_points",
        official=("Not a direct official-rule representation",),
        product=_GAME_END_DOC,
        game_end_kind="declarer_conceded_remaining_tricks",
        contract_scope="legacy_suit_grand",
        pre_end_decision_state="incomplete_observed_points",
        evidence_class=LEGACY_SIMPLIFIED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=LEGACY_COMPATIBILITY,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=LEGACY_REMAINING_POINTS,
        level_policy=NORMAL_ACHIEVED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=NORMAL_SETTLEMENT,
        implementation_modules=("skat_ai.game_end", "skat_ai.final_settlement"),
        notes=("Remaining points go to the defenders; remaining trick ownership is not proven.",),
    ),
    _case(
        case_id="legacy.defenders_conceded_remaining_tricks",
        scenario_family="legacy_remaining_points",
        official=("Not a direct official-rule representation",),
        product=_GAME_END_DOC,
        game_end_kind="defenders_conceded_remaining_tricks",
        contract_scope="legacy_suit_grand",
        pre_end_decision_state="incomplete_observed_points",
        evidence_class=LEGACY_SIMPLIFIED,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=LEGACY_COMPATIBILITY,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=LEGACY_REMAINING_POINTS,
        level_policy=NORMAL_ACHIEVED_LEVELS,
        overbid_policy=NORMAL_SUPPORTED_OVERBID,
        settlement_policy=NORMAL_SETTLEMENT,
        implementation_modules=("skat_ai.game_end", "skat_ai.final_settlement"),
        notes=("Remaining points go to the declarer; remaining trick ownership is not proven.",),
    ),
    _case(
        case_id="ongoing.not_ended",
        scenario_family="ongoing_game",
        official=("ISkO 4.4.1",),
        product=_GAME_END_DOC,
        game_end_kind="not_ended",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="not_terminal",
        evidence_class=VALIDATED_PUBLIC_CONTINUATION,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=PRODUCT_BOUNDARY,
        winner_policy=CONTINUE_WITHOUT_SETTLEMENT,
        remaining_assignment_policy=CONTINUE_PLAY,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=NO_TERMINAL_SETTLEMENT,
        terminal_effect=NON_TERMINAL,
        implementation_modules=("skat_ai.game_end",),
    ),
    _case(
        case_id="structured_shortening.declarer_card_exposure.accepted_preexisting",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.4", "ISkO 4.1.3"),
        product=("docs/declarer_card_exposure.md", "docs/game_end.md"),
        game_end_kind="declarer_card_exposure",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=SECURED_OBSERVED_LEVELS_ONLY,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=("skat_ai.declarer_card_exposure", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="structured_shortening.declarer_card_exposure.accepted_undecided",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.4", "ISkO 4.1.4-4.1.5"),
        product=("docs/declarer_card_exposure.md", "docs/game_end.md"),
        game_end_kind="declarer_card_exposure",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DECLARER,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=ACCEPTED_CLAIMED_LEVEL,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=("skat_ai.declarer_card_exposure", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="structured_shortening.declarer_card_exposure.accepted_undecided_uncovered",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.4", "ISkO 3.6.1-3.6.4"),
        product=("docs/declarer_card_exposure.md", "docs/game_end.md"),
        game_end_kind="declarer_card_exposure",
        contract_scope="suit_grand",
        pre_end_decision_state="undecided_with_uncovered_requirement",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=ACCEPTED_CLAIMED_LEVEL,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=("skat_ai.declarer_card_exposure", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="structured_shortening.declarer_card_exposure.rejected_continuation",
        scenario_family="structured_continuation",
        official=("ISkO 4.4.4",),
        product=("docs/declarer_card_exposure_continuation.md",),
        game_end_kind="declarer_card_exposure_continuation",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="not_terminal",
        evidence_class=VALIDATED_PUBLIC_CONTINUATION,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=CONTINUE_WITHOUT_SETTLEMENT,
        remaining_assignment_policy=CONTINUE_PLAY,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=NO_TERMINAL_SETTLEMENT,
        terminal_effect=NON_TERMINAL,
        implementation_modules=("skat_ai.declarer_card_exposure_continuation",),
    ),
    _case(
        case_id="structured_shortening.declarer_concession",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.1-4.4.2",),
        product=("docs/declarer_concessions.md", "docs/game_end.md"),
        game_end_kind="declarer_concession",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="accepted_concession",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=NO_ADDITIONAL_LEVEL,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=DOUBLED_DECLARER_LOSS,
        implementation_modules=("skat_ai.declarer_concession", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="structured_shortening.defender_concession.preexisting",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.3", "ISkO 4.1.3"),
        product=("docs/defender_concessions.md", "docs/game_end.md"),
        game_end_kind="defender_concession",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=SECURED_OBSERVED_LEVELS_ONLY,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=("skat_ai.defender_concession", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="structured_shortening.defender_concession.undecided",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.3", "ISkO 4.1.4-4.1.5"),
        product=("docs/defender_concessions.md", "docs/game_end.md"),
        game_end_kind="defender_concession",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DECLARER,
        remaining_assignment_policy=NO_REMAINING_ASSIGNMENT,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        implementation_modules=("skat_ai.defender_concession", "skat_ai.final_settlement"),
    ),
    _case(
        case_id="structured_shortening.defender_open_play.invalid_proof",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.5", "ISkO 4.1.4-4.1.5"),
        product=("docs/defender_open_play.md", "docs/game_end.md"),
        game_end_kind="defender_open_play",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided",
        evidence_class=BOUNDED_EXACT_PROOF,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DECLARER,
        remaining_assignment_policy=ASSIGN_TO_DECLARER,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=DEFENDER_OPEN_PLAY_V1,
        implementation_modules=("skat_ai.defender_open_play", "skat_ai.exact_rest_trick_proof"),
        proof_quantifiers=DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        proof_maximum_unresolved_tricks=5,
    ),
    _case(
        case_id="structured_shortening.defender_open_play.preexisting",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.5", "ISkO 4.1.3"),
        product=("docs/defender_open_play.md", "docs/game_end.md"),
        game_end_kind="defender_open_play",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=BOUNDED_EXACT_PROOF,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=REMAINING_PROOF_DEPENDENT,
        level_policy=SECURED_OBSERVED_LEVELS_ONLY,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=DEFENDER_OPEN_PLAY_V1,
        implementation_modules=("skat_ai.defender_open_play", "skat_ai.exact_rest_trick_proof"),
        proof_quantifiers=DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        proof_maximum_unresolved_tricks=5,
    ),
    _case(
        case_id="structured_shortening.defender_open_play.proof_evaluation",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.5", "ISkO 4.1.3-4.1.5"),
        product=("docs/defender_open_play.md", "docs/game_end.md"),
        game_end_kind="defender_open_play",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="proof_evaluation",
        evidence_class=BOUNDED_EXACT_PROOF,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PROOF_DEPENDENT,
        remaining_assignment_policy=REMAINING_PROOF_DEPENDENT,
        level_policy=DECLARED_AND_REQUIRED_LEVELS,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=DEFENDER_OPEN_PLAY_V1,
        implementation_modules=("skat_ai.defender_open_play", "skat_ai.exact_rest_trick_proof"),
        proof_quantifiers=DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        proof_maximum_unresolved_tricks=5,
        notes=("The non-exposing defender is universal and is not cooperating.",),
    ),
    _case(
        case_id="structured_shortening.defender_open_play.valid_proof",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.5",),
        product=("docs/defender_open_play.md", "docs/game_end.md"),
        game_end_kind="defender_open_play",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided",
        evidence_class=BOUNDED_EXACT_PROOF,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=NORMAL_COMPLETION,
        remaining_assignment_policy=ASSIGN_TO_DEFENDERS,
        level_policy=SECURED_OBSERVED_LEVELS_ONLY,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=DEFENDER_OPEN_PLAY_V1,
        implementation_modules=("skat_ai.defender_open_play", "skat_ai.exact_rest_trick_proof"),
        proof_quantifiers=DEFENDER_OPEN_PLAY_V1_QUANTIFIERS,
        proof_maximum_unresolved_tricks=5,
    ),
    _case(
        case_id="structured_shortening.defender_open_play_continuation",
        scenario_family="structured_continuation",
        official=("ISkO 4.4.5", "ISkO 4.1.6"),
        product=("docs/defender_open_play_continuation.md",),
        game_end_kind="defender_open_play_continuation",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="not_terminal",
        evidence_class=VALIDATED_PUBLIC_CONTINUATION,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=CONTINUE_WITHOUT_SETTLEMENT,
        remaining_assignment_policy=CONTINUE_PLAY,
        level_policy=LEVEL_NOT_APPLICABLE,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=NO_TERMINAL_SETTLEMENT,
        terminal_effect=NON_TERMINAL,
        implementation_modules=("skat_ai.defender_open_play_continuation",),
    ),
    _case(
        case_id="structured_shortening.open_card_throw.preexisting",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.6", "ISkO 4.1.3"),
        product=("docs/open_card_throw.md", "docs/game_end.md"),
        game_end_kind="open_card_throw",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="preexisting_decision",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=PRESERVE_PREEXISTING_DECISION,
        remaining_assignment_policy=ASSIGN_TO_OPPOSING_PARTY,
        level_policy=RULE_ASSIGNED_IF_NOT_EXCLUDED,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=OPEN_THROW_JACK_EXCLUSION_V1,
        implementation_modules=("skat_ai.open_card_throw", "skat_ai.theoretical_level_exclusion"),
    ),
    _case(
        case_id="structured_shortening.open_card_throw.undecided",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.6",),
        product=("docs/open_card_throw.md", "docs/game_end.md"),
        game_end_kind="open_card_throw",
        contract_scope="all_supported_contracts",
        pre_end_decision_state="undecided",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=OPPOSING_PARTY_ASSIGNMENT,
        remaining_assignment_policy=ASSIGN_TO_OPPOSING_PARTY,
        level_policy=RULE_ASSIGNED_IF_NOT_EXCLUDED,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=OPEN_THROW_JACK_EXCLUSION_V1,
        implementation_modules=("skat_ai.open_card_throw", "skat_ai.theoretical_level_exclusion"),
        notes=(
            "The proof scope is jack-only theoretical Schwarz exclusion, not rest-play solving.",
        ),
    ),
    _case(
        case_id="structured_shortening.open_card_throw.undecided_uncovered_requirement",
        scenario_family="structured_shortening",
        official=("ISkO 4.4.6", "ISkO 3.6.1-3.6.4"),
        product=("docs/open_card_throw.md", "docs/game_end.md"),
        game_end_kind="open_card_throw",
        contract_scope="suit_grand",
        pre_end_decision_state="undecided_with_uncovered_requirement",
        evidence_class=VALIDATED_RULE_ASSIGNMENT,
        implementation_status=SUPPORTED_AS_IS,
        interpretation_scope=APPROVED_BOUNDED,
        winner_policy=FORCE_DEFENDERS,
        remaining_assignment_policy=ASSIGN_TO_OPPOSING_PARTY,
        level_policy=RULE_ASSIGNED_IF_NOT_EXCLUDED,
        overbid_policy=PRESERVE_REQUIRED_VALUE,
        settlement_policy=EXISTING_SHORTENING_SETTLEMENT,
        proof_policy=OPEN_THROW_JACK_EXCLUSION_V1,
        implementation_modules=("skat_ai.open_card_throw", "skat_ai.theoretical_level_exclusion"),
    ),
)


def get_normative_settlement_cases() -> tuple[NormativeSettlementCase, ...]:
    """Returns the immutable canonical version-1 matrix."""
    return SETTLEMENT_NORMATIVE_MATRIX


def get_normative_settlement_case(case_id: str) -> NormativeSettlementCase:
    """Returns one matrix case by its stable namespaced identifier."""
    for case in SETTLEMENT_NORMATIVE_MATRIX:
        if case.case_id == case_id:
            return case
    raise KeyError(f"Unknown normative settlement case: {case_id}")


def validate_normative_settlement_matrix(
    cases: tuple[NormativeSettlementCase, ...] | None = None,
) -> None:
    """Validates matrix structure and policy compatibility without runtime state."""
    cases = SETTLEMENT_NORMATIVE_MATRIX if cases is None else cases
    if not isinstance(cases, tuple):
        raise ValueError("Normative settlement cases must be an immutable tuple.")
    case_ids = tuple(case.case_id for case in cases)
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Normative settlement case IDs must be unique.")
    if case_ids != tuple(sorted(case_ids)):
        raise ValueError("Normative settlement cases must use canonical case_id order.")
    cases_by_id = {case.case_id: case for case in cases}

    allowed_values = (
        ("implementation_status", VALID_IMPLEMENTATION_STATUSES),
        ("interpretation_scope", VALID_INTERPRETATION_SCOPES),
        ("evidence_class", VALID_EVIDENCE_CLASSES),
        ("winner_policy", VALID_WINNER_POLICIES),
        ("remaining_assignment_policy", VALID_REMAINING_ASSIGNMENT_POLICIES),
        ("level_policy", VALID_LEVEL_POLICIES),
        ("null_level_policy", VALID_LEVEL_POLICIES),
        ("overbid_policy", VALID_OVERBID_POLICIES),
        ("settlement_policy", VALID_SETTLEMENT_POLICIES),
        ("proof_policy", VALID_PROOF_POLICIES),
        ("terminal_effect", VALID_TERMINAL_EFFECTS),
    )
    unresolved_policies = (
        WINNER_UNRESOLVED,
        REMAINING_UNRESOLVED,
        LEVEL_UNRESOLVED,
        OVERBID_UNRESOLVED,
        SETTLEMENT_UNRESOLVED,
    )

    for case in cases:
        if re.fullmatch(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+", case.case_id) is None:
            raise ValueError(f"Invalid namespaced case_id: {case.case_id}")
        if not case.official_rule_references or not case.product_contract_references:
            raise ValueError(f"{case.case_id} requires official and product source references.")
        tuple_fields = (
            "official_rule_references",
            "product_contract_references",
            "implementation_modules",
            "proof_quantifiers",
            "delegated_terminal_case_ids",
            "notes",
        )
        if any(not isinstance(getattr(case, field_name), tuple) for field_name in tuple_fields):
            raise ValueError(f"{case.case_id} must use immutable tuple fields.")
        if any(
            not isinstance(quantifier, tuple) or len(quantifier) != 2
            for quantifier in case.proof_quantifiers
        ):
            raise ValueError(f"{case.case_id} has invalid proof quantifiers.")
        for field_name, valid_values in allowed_values:
            value = getattr(case, field_name)
            if value not in valid_values:
                raise ValueError(f"{case.case_id} has invalid {field_name}: {value}")

        if case.implementation_status == SUPPORTED_AS_IS and not case.implementation_modules:
            raise ValueError(f"{case.case_id} requires an implementation module.")
        if case.implementation_status != SUPPORTED_AS_IS and case.implementation_modules:
            raise ValueError(f"{case.case_id} must not name an implementation module.")
        if case.implementation_status != SUPPORTED_AS_IS and case.stable_unavailable_reason is None:
            raise ValueError(f"{case.case_id} requires a stable unavailable reason.")

        if case.delegated_terminal_case_ids:
            if case.implementation_status not in {
                IMPLEMENTATION_REQUIRED,
                SUPPORTED_AS_IS,
            }:
                raise ValueError(f"{case.case_id} cannot delegate terminal behavior.")
            if len(case.delegated_terminal_case_ids) != len(
                set(case.delegated_terminal_case_ids)
            ):
                raise ValueError(f"{case.case_id} has duplicate delegated cases.")
            try:
                delegated_cases = tuple(
                    cases_by_id[delegated_case_id]
                    for delegated_case_id in case.delegated_terminal_case_ids
                )
            except KeyError as error:
                raise ValueError(
                    f"{case.case_id} delegates an unknown terminal case: {error.args[0]}"
                ) from error
            if any(
                delegated.implementation_status != SUPPORTED_AS_IS
                or delegated.scenario_family != "structured_shortening"
                or delegated.terminal_effect != TERMINAL
                for delegated in delegated_cases
            ):
                raise ValueError(
                    f"{case.case_id} must delegate only supported terminal shortening cases."
                )
            delegated_kinds = {delegated.game_end_kind for delegated in delegated_cases}
            if delegated_kinds != {
                "declarer_concession",
                "defender_concession",
                "declarer_card_exposure",
                "defender_open_play",
                "open_card_throw",
            }:
                raise ValueError(
                    f"{case.case_id} must delegate every supported terminal shortening kind."
                )
        elif case.game_end_kind == "supported_terminal_shortening_after_continuation":
            raise ValueError(f"{case.case_id} requires delegated terminal cases.")

        outcome_policies = (
            case.winner_policy,
            case.remaining_assignment_policy,
            case.level_policy,
            case.overbid_policy,
            case.settlement_policy,
        )
        if case.evidence_class in {INCOMPLETE, CONTRADICTORY}:
            if outcome_policies != unresolved_policies:
                raise ValueError(
                    f"{case.case_id} cannot define an outcome from incomplete or "
                    "contradictory evidence."
                )
        if case.implementation_status in {DECISION_REQUIRED, OUT_OF_SCOPE_V0_11}:
            if outcome_policies != unresolved_policies:
                raise ValueError(f"{case.case_id} cannot define an approved outcome.")

        if case.game_end_kind in CONTINUATION_GAME_END_KINDS:
            if case.terminal_effect != NON_TERMINAL:
                raise ValueError(f"{case.case_id} must remain non-terminal.")
        if case.terminal_effect == NON_TERMINAL:
            expected_continuation_policies = (
                CONTINUE_WITHOUT_SETTLEMENT,
                CONTINUE_PLAY,
                NO_TERMINAL_SETTLEMENT,
            )
            actual_continuation_policies = (
                case.winner_policy,
                case.remaining_assignment_policy,
                case.settlement_policy,
            )
            if actual_continuation_policies != expected_continuation_policies:
                raise ValueError(f"{case.case_id} cannot settle a continuation event.")
            if case.level_policy != LEVEL_NOT_APPLICABLE:
                raise ValueError(f"{case.case_id} cannot define a continuation level.")

        if case.null_level_policy != LEVEL_NOT_APPLICABLE:
            raise ValueError(f"{case.case_id} cannot apply Schneider or Schwarz to Null.")
        if case.contract_scope.startswith("null") and case.level_policy != LEVEL_NOT_APPLICABLE:
            raise ValueError(f"{case.case_id} cannot apply Schneider or Schwarz to Null.")

        if (
            case.pre_end_decision_state == "preexisting_decision"
            and case.winner_policy != PRESERVE_PREEXISTING_DECISION
        ):
            raise ValueError(f"{case.case_id} must preserve a preexisting decision.")

        if case.proof_policy == DEFENDER_OPEN_PLAY_V1:
            if "defender_open_play" not in case.game_end_kind:
                raise ValueError(f"{case.case_id} has unrelated defender-open-play proof.")
            if case.proof_quantifiers != DEFENDER_OPEN_PLAY_V1_QUANTIFIERS:
                raise ValueError(f"{case.case_id} has invalid defender-open-play quantifiers.")
            if case.proof_maximum_unresolved_tricks != 5:
                raise ValueError(f"{case.case_id} must retain the five-trick proof bound.")
        elif case.proof_policy == OPEN_THROW_JACK_EXCLUSION_V1:
            if case.game_end_kind != "open_card_throw":
                raise ValueError(f"{case.case_id} has unrelated open-throw proof.")
            if case.proof_quantifiers:
                raise ValueError(f"{case.case_id} must not define rest-play quantifiers.")
            if case.proof_maximum_unresolved_tricks is not None:
                raise ValueError(f"{case.case_id} must not define a rest-play proof bound.")
        elif case.proof_quantifiers or case.proof_maximum_unresolved_tricks is not None:
            raise ValueError(
                f"{case.case_id} has proof details without a related proof policy."
            )

        if (
            case.proof_policy == PROOF_DECISION_REQUIRED
            and case.scenario_family != "undecided_claim"
        ):
            raise ValueError(f"{case.case_id} has an unrelated undecided proof policy.")
        if case.proof_policy == PROOF_NOT_APPROVED and case.game_end_kind not in {
            "defender_open_play_beyond_five_unresolved_tricks",
            "unlimited_claim_proof",
        }:
            raise ValueError(f"{case.case_id} has an unrelated excluded proof policy.")

        if case.game_end_kind in LEGACY_GAME_END_KINDS:
            if case.interpretation_scope != LEGACY_COMPATIBILITY:
                raise ValueError(f"{case.case_id} must remain legacy compatibility only.")
            if case.evidence_class != LEGACY_SIMPLIFIED:
                raise ValueError(f"{case.case_id} must retain legacy simplified evidence.")
            if case.remaining_assignment_policy != LEGACY_REMAINING_POINTS:
                raise ValueError(f"{case.case_id} must retain legacy remaining-point assignment.")

    represented_legacy_kinds = {
        case.game_end_kind
        for case in cases
        if case.interpretation_scope == LEGACY_COMPATIBILITY
    }
    if represented_legacy_kinds != LEGACY_GAME_END_KINDS:
        raise ValueError("The matrix must represent exactly the three legacy game-end reasons.")
