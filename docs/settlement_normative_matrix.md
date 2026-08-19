# Settlement normative matrix

## Version and purpose

`src/skat_ai/settlement_normative_matrix.py` defines immutable Settlement
Normative Matrix version `2` with the same 61 canonical case IDs in the same
order as version `1`. It records current support, interpretation scope, one
approved but non-executable Claim, and durable v1 exclusions in deterministic
case-ID order.

The matrix is an internal specification and validation artifact. It is not a
stable package-root API, does not inspect runtime game state, and is not imported
by adjudication, settlement, Search, simulation, historical parsing, schemas,
CLI, examples, or generated-output paths. Issue #183 adds separate private Claim
contracts and exact-state preparation without changing Runtime adjudication or a
public serialized contract.

The matrix does not claim complete official-rule, claim, concession, or
Settlement coverage. Claims and Final Settlement remain partially supported
beyond the documented bounded cases. The closed v1 Claim decision is documented
in [Claim and Settlement v1 boundaries](claim_and_settlement_v1_boundaries.md).

## Normative source hierarchy

The sources have this order:

1. The November 2022 official ISkO and SkWO publication governs official game
   and competition rules.
2. The documented International Skat Court decision collection interpretation
   for ISkO 3.6.2 governs the bounded impossible-Null replacement case.
3. Approved `skat-ai` product contracts define bounded software evidence,
   privacy, continuation, historical representation, and unavailable behavior
   where the official rules do not define a software interface.
4. Existing runtime behavior retained only for compatibility is identified as
   legacy and is not promoted to an official-rule representation.

The matrix references the relevant rule sections and repository contracts per
case. `docs/requirements_traceability.md` remains the broader product audit.

## Status values

| Status | Meaning |
| --- | --- |
| `supported_as_is` | Current behavior is executable and names at least one implementation module. |
| `implementation_required` | Semantics are approved, but runtime implementation is still required. |
| `decision_required` | A separate product decision is required; no implementation-ready outcome is defined. |
| `not_supported_v1` | The behavior is not supported before v1, defines no approved outcome, and has no implementation module. |

`decision_required` remains available for future audits, but no canonical
version-2 case uses it. No canonical version-2 case uses the historical
`out_of_scope_v0_11` milestone classification.

## Interpretation scopes

| Scope | Meaning |
| --- | --- |
| `direct_rule` | Direct representation of the cited official rule within the stated contract scope. |
| `approved_bounded` | Approved product interpretation that deliberately implements only a documented subset. |
| `legacy_compatibility` | Existing simplified behavior retained for compatibility only. |
| `product_boundary` | Product representation, sequencing, decision, or exclusion rather than an official game rule. |
| `not_applicable` | No rule interpretation is asserted, such as rejected unsafe evidence. |

Implemented bounded behavior remains `approved_bounded`; implementation does not
turn a deliberate subset into `direct_rule`.

## Evidence classes

The stable evidence classes are:

* `complete_observed`
* `exact_complete_world`
* `bounded_exact_proof`
* `validated_public_continuation`
* `validated_rule_assignment`
* `legacy_simplified`
* `incomplete`
* `contradictory`
* `not_applicable`

`incomplete` and `contradictory` evidence always use unresolved winner,
remaining-assignment, level, overbid, and settlement policies. They never define
a definitive outcome.

## Policy dimensions

Winner policy values:

* `normal_completion`
* `preserve_preexisting_decision`
* `force_declarer`
* `force_defenders`
* `proof_dependent`
* `opposing_party_assignment`
* `continue_without_settlement`
* `unresolved`

Remaining-assignment policy values:

* `none`
* `assign_to_declarer`
* `assign_to_defenders`
* `assign_to_opposing_party`
* `proof_dependent`
* `continue_play`
* `legacy_remaining_points`
* `unresolved`

Level policy values:

* `normal_achieved_levels`
* `declared_and_required_levels`
* `accepted_claimed_level`
* `secured_observed_levels_only`
* `rule_assigned_if_not_excluded`
* `no_additional_level`
* `not_applicable`
* `unresolved`

Every case also has a separate `null_level_policy`, which is always
`not_applicable`. This makes the Null exclusion explicit even when one case spans
Suit, Grand, and Null contracts. Null never inherits the Suit/Grand
`level_policy`.
Declared, accepted-claimed, secured-observed, achieved-during-play, and
rule-assigned levels remain separate sources.

Overbid policy values:

* `normal_supported_overbid`
* `preserve_required_value`
* `impossible_null_external_replacement`
* `unsupported_without_required_input`
* `not_applicable`
* `unresolved`

Settlement policy values:

* `normal_settlement`
* `doubled_declarer_loss`
* `fixed_null_value`
* `existing_shortening_settlement`
* `impossible_null_external_replacement`
* `no_terminal_settlement`
* `unresolved`

Proof policy values:

* `none`
* `defender_open_play_v1`
* `open_throw_jack_exclusion_v1`
* `party_wide_all_remaining_tricks_claim_v1`
* `decision_required`
* `not_approved`

Terminal-effect values:

* `terminal`
* `non_terminal`
* `not_a_runtime_case`

Continuation kinds must be `non_terminal`, use `continue_without_settlement`,
`continue_play`, and `no_terminal_settlement`, and define no immediate level.

## Current structured boundary

The following are currently executable structured behaviors:

* `declarer_concession`
* `defender_concession`
* `declarer_card_exposure`
* `declarer_card_exposure_continuation`
* `defender_open_play`
* `defender_open_play_continuation`
* `open_card_throw`

The matrix also covers normal completion, achieved and announced levels,
supported Suit/Grand overbid, all four normal Null variants, bounded impossible
Null, every current historical terminal kind, and both historical continuation
kinds.

## Case-family summary

| Family or subcase | Status and interpretation | Normative policy boundary |
| --- | --- | --- |
| Normal Suit/Grand completion | `supported_as_is`, `direct_rule` | Observed winner, achieved levels, supported overbid, and normal settlement. |
| Normal Null, Null Hand, Null Ouvert, Null Hand Ouvert | `supported_as_is`, `direct_rule` | Completed-trick winner, fixed Null value, and no Schneider/Schwarz level. |
| Achieved and announced levels | `supported_as_is`, `direct_rule` | Achieved and declared/required sources remain distinct. |
| Supported Suit/Grand overbid | `supported_as_is`, `direct_rule` | Required value is retained and an overbid is a doubled declarer loss. |
| Impossible Null with replacement | `supported_as_is`, `approved_bounded` | Immediate defender win and externally selected Suit/Grand replacement settlement. |
| Impossible Null without replacement | `supported_as_is`, `approved_bounded` | Winner remains final; settlement is unavailable with reason `impossible_null_settlement`. |
| Declarer concession | `supported_as_is`, `approved_bounded` | Defender win, no remaining assignment or achieved level, doubled loss. |
| Defender concession | `supported_as_is`, `approved_bounded` | Undecided game goes to declarer; preexisting winner is preserved; no remaining assignment. |
| Accepted declarer exposure | `supported_as_is`, `approved_bounded` | Accepted claimed level can settle an undecided covered contract; preexisting winner is preserved. |
| Rejected declarer exposure | `supported_as_is`, `approved_bounded` | Public-hand continuation with no immediate outcome or settlement. |
| Defender open play | `supported_as_is`, `approved_bounded` | `defender_open_play_v1`, exact valid/invalid assignment, and preexisting-winner preservation. |
| Defender-open-play continuation | `supported_as_is`, `approved_bounded` | Returned public hand, no proof, assignment, winner, level, or settlement. |
| Open card throw | `supported_as_is`, `approved_bounded` | Opposing-party assignment, preexisting-winner preservation, and jack-only exclusion. |
| Legacy remaining-point reasons | `supported_as_is`, `legacy_compatibility` | Existing simplified point assignment only; no rest-trick proof. |
| Historical normal and five terminal kinds | `supported_as_is` | Exact replay adapters retain the corresponding current terminal policy. |
| Both historical continuation kinds | `supported_as_is`, `product_boundary` | One non-terminal event followed by independently settled normal completion or one supported terminal shortening. |
| One continuation then one terminal shortening | `supported_as_is`, `product_boundary` | The subsequent supported terminal kind retains its existing policy. |
| Party-wide all-remaining-Tricks Claim | `implementation_required`, `approved_bounded` | Private structured contracts and exact-state preparation exist; the Retrospective complete-world five-Trick proof is not executable. |
| Specific and generalized excluded Claims | `not_supported_v1`, `product_boundary` | No implementation or adjudication policy before v1. |
| Previous milestone exclusions | `not_supported_v1`, `product_boundary` | Durable v1 exclusion with no implementation or adjudication policy. |
| Incomplete or contradictory evidence | `supported_as_is`, `not_applicable` | Winner, assignment, level, overbid, and settlement remain unresolved. |

Within these families, declarer concession retains the existing `9..10` cards
without defender consent and `1..8` cards with one or two consenting defenders.
Normal Suit/Grand settlement covers both declarer wins and doubled losses;
failed announced requirements remain declarer losses. Defender-open-play cases
separate valid proof, invalid proof, and preexisting decisions for Suit, Grand,
and fixed-value Null. Open throw supports either throwing party, preserves an
earlier decision, and distinguishes jack-only `excluded` from `not_excluded`
Schwarz assessment without promoting either result to arbitrary-card proof.

## Legacy boundary

These reasons remain `legacy_compatibility` only:

* `declarer_claimed_remaining_tricks`
* `declarer_conceded_remaining_tricks`
* `defenders_conceded_remaining_tricks`

They retain simplified remaining-card-point assignment and do not prove actual
remaining trick ownership. They are not silently reinterpreted as structured
claims or concessions.

## Closed v1 Claim decision

Issue #182 closes the remaining Claim product-decision gate. Exactly one case is
`implementation_required`:

```text
claim_boundary.decision.party_wide_all_remaining_tricks_claim
```

It approves a structured post-game and Retrospective-only complete-world proof,
bounded to five unresolved Tricks, with claiming-party existential and opposing-
party universal legal choices. A valid proof will assign every unresolved Trick
to the claiming party and reuse existing result and Settlement behavior. Invalid
or unavailable proof will create no terminal outcome or Settlement, and there is
no opposing-party or Generic Search fallback. Issue #183 defines private
contracts and one untraversed exact-state preparation; proof execution,
adjudication, Historical and Settlement integration, and public exposure remain
open.

The following former decision cases are `not_supported_v1`:

* specific future-Trick-count Claims;
* specific future-Trick-identity Claims;
* generalized non-jack open-throw theoretical exclusion;
* generalized rule-violation correction.

## Durable v1 exclusions

The previous `v0.11.0` milestone exclusions now use `not_supported_v1`:

* free-text claims;
* natural-language interpretation;
* simultaneous throws;
* arbitrary event streams;
* defender-open-play proof beyond five unresolved tricks;
* multiple non-terminal continuation events;
* unlimited proof;
* generative adjudication;
* unclassified conduct.

Together with the four former decision cases, these form the exact 13-case
`V1_NOT_SUPPORTED_CLAIM_CASE_IDS` tuple. They are durable v1 exclusions, not
unconditional permanent exclusions or post-v1 implementation promises.
Four-player tables remain the repository's only unconditional exclusion.

## Proof boundaries

`defender_open_play_v1` preserves the existing exact quantifiers:

| Actor | Quantifier |
| --- | --- |
| exposing defender | existential |
| declarer | universal |
| non-exposing defender | universal |

The non-exposing defender is not cooperating. The proof is bounded to at most
five unresolved tricks.

`open_throw_jack_exclusion_v1` is only the existing jack-ownership theoretical
Schwarz exclusion. It is not arbitrary-card theoretical solving and is not an
exact rest-play proof.

`party_wide_all_remaining_tricks_claim_v1` has private version-1 contracts and
these exact quantifiers:

| Party | Quantifier |
| --- | --- |
| claiming party | existential |
| opposing party | universal |

It requires complete Retrospective evidence and is bounded to at most five
unresolved Tricks. The Matrix case remains Runtime-module-free and unavailable
with reason `party_wide_claim_not_implemented` until a dedicated proof and
adjudicator exist; the separate private contract modules do not enter
`implementation_modules`. A valid supplied Result assigns all unresolved Tricks
to the claiming party; invalid and unavailable Results create no terminal
outcome or Settlement.

Perfect-Information Minimax, compatible-world Minimax, and Search aggregation are
not generic claim proofs. Search remains separate from claim adjudication.

## Historical sequence boundary

Current version-1 historical records support at most one timed non-terminal
declarer-card-exposure or defender-open-play continuation followed by normal
completion or one supported terminal shortening. The continuation event itself
has no winner, assignment, level, proof, or terminal settlement effect; later
normal play or the independently delegated terminal case determines settlement.

The implemented bounded sequence is:

```text
at most one supported non-terminal continuation event
+
at most one subsequent supported terminal shortening
```

Its matrix status is `supported_as_is`. The runtime keeps the continuation in
`game_events[0]` and the optional terminal shortening in top-level
`game_end_reason` plus `game_end`, with both schema versions unchanged at `1`.
Multiple non-terminal events and arbitrary event streams are `not_supported_v1`.

The sequence case delegates by immutable case ID to every currently supported
terminal shortening subcase. Its own winner, assignment, level, and overbid
dimensions remain unresolved until one delegated terminal kind is selected;
that terminal case then supplies the existing approved policy and settlement.
Matrix validation permits this supported chain to delegate only to existing
supported terminal shortening cases and still requires all five terminal kinds.

## Validation

Internal helpers return all cases, look up one stable case ID, and validate the
matrix. Validation covers the exact 61 version-2 IDs and order, value
vocabularies, exact approved and excluded Claim tuples, required references,
status-policy compatibility, continuation non-settlement, Null level exclusion,
unsafe evidence, exact proof quantifiers and bounds, implementation-module
ownership, zero canonical decision-required and old-milestone cases, durable
exclusions, and the legacy-only boundary.

Focused tests import current runtime constants and require matrix coverage for
every `GameShortening` union member, every historical terminal kind, both
historical continuation kinds, every `VALID_GAME_END_REASONS` value, normal
completion, and impossible Null. A future runtime kind therefore requires an
explicit matrix decision.
