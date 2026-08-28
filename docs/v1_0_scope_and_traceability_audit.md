# v1.0.0 scope and traceability audit

## Audit purpose

This document is the authoritative Issue #200 audit of the bounded product scope,
traceability, and release gates for `skatmind` `v1.0.0`. It classifies every row
marked required before v1.0 in
[Requirements traceability](requirements_traceability.md), resolves the open v1
scope boundaries that can be resolved from approved repository decisions, and
records exact remaining blockers.

Issue #200 changes documentation only. It does not change product behavior,
Package metadata, dependencies, public exports, Schemas, persistence formats,
examples, generated scenarios, benchmark values, tests, or build configuration.
It does not make `v1.0.0` ready and does not freeze a Release title, theme, date,
publication commit, tag, or Package-index publication.

Issues #182 through #196 remain the frozen `v0.17.0` functional history. Issues
#197 through #199 remain audit, Release preparation, and publication
synchronization only.

Issue #201 adds independent exhaustive official-rule evidence for R-01 and R-06,
closes B-01 without product-code change, and synchronizes this current audit.
Issue #202 completes mandatory internal load-to-final-serialization information-
Provenance enforcement for all seven Root workflows, closes B-02, makes P-10 and
P-13 `satisfied`, and preserves the bounded public Provenance contract.
Issue #203 completes all nine concrete canonical Multi-Step phases, closes B-03,
makes P-19 `satisfied`, and preserves coherent-World, Search, Provenance, public-
contract, Schema, and generated-scenario-count boundaries.
Issue #204 applies the exact `AGPL-3.0-only` Package boundary and closes B-04.
Issue #205 completes the hard-cut SkatMind product, distribution, import, CLI,
resource, Schema, identifier, and strict legacy-input migration boundary, makes
P-09 `satisfied`, and closes B-08. The GitHub repository rename and local remote
update remain explicit maintainer verification steps before Issue #205 is closed.

## Source hierarchy

Conflicts are resolved through this seven-level hierarchy:

1. The official November 2022 ISkO/SkWO publication governs game and competition
   rules; International Skat Court material governs the accepted impossible-Null
   interpretation where the audit cites it.
2. Approved repository product decisions, including the Settlement Normative
   Matrix and this audit's bounded v1 decisions, govern skatmind-specific scope.
3. Current Package metadata, executable source constants, contracts, validators,
   and canonical persisted or serialized definitions govern implemented
   behavior.
4. Authoritative Schemas and byte-identical packaged Schema Resources govern
   stable JSON document surfaces.
5. Root and Session examples, generated-output registries, benchmark corpora,
   validators, focused tests, benchmark tests, distribution scripts, the complete
   repository check, and CI results provide executable evidence.
6. This audit governs v1 classifications; supporting current-state documentation
   explains the same current facts.
7. Historical Changelog, issue-era, readiness-audit, and Release documentation
   remains point-in-time evidence and is not rewritten with later counts.

GitHub Releases is authoritative for publication status. No Package-index or
PyPI publication is claimed.

## Verified baseline

The current published stable and latest stable GitHub Release is:

| Dimension | Verified value |
| --- | --- |
| Release | `v0.17.0 — Rules, Search, Coaching, and performance closure` |
| Publication commit | `8187fbe684559f9c0c2ba444be1bf33950359ad2` (`8187fbe`) |
| Publication date | 2026-08-25 |
| Package | `0.17.0` |
| Python requirement | `>=3.13` |
| Public API contract | `1` |
| Root workflows | 7 |
| Console Scripts | 1 |
| Settlement Matrix | version `3` |
| Canonical Settlement cases | 61 |
| Authoritative Schemas | 71 |
| Packaged Schema Resources | 71 |
| Session examples | 6 |
| Generated outputs | 98 |
| Private Corpus downloads | 10 |
| Published pytest result | 7,479 passed in 921.96s |

The current development baseline intentionally remains Package `0.17.0` while
the v1 blockers below are open.

## Audit status vocabulary

This audit uses exactly these statuses:

| Status | Meaning |
| --- | --- |
| `satisfied` | The complete frozen v1 requirement is implemented with direct automated evidence. |
| `satisfied_with_approved_bounded_scope` | The accepted v1 requirement is implemented and evidenced within an explicit limitation; broader behavior is not a v1 gate. |
| `evidence_required` | The accepted behavior exists, but required direct automated or supported-platform evidence is incomplete. |
| `implementation_required` | The frozen behavior is incomplete and requires product or supporting validation/tooling implementation plus direct evidence. |
| `product_decision_required` | Implementation or validation cannot finish until the maintainer records a decision. |
| `post_v1` | The candidate capability is a valid future direction but is not required for v1. |
| `not_required` | The candidate capability is explicitly unnecessary for the frozen v1 product. |
| `unconditionally_excluded` | The capability is excluded from the product rather than merely deferred. |

They classify v1 gates, not the broader implementation-status vocabulary in the
traceability matrix. In particular, a traceability row may remain
`partially_supported` while this audit classifies its exact bounded v1
interpretation as `satisfied_with_approved_bounded_scope`.

## Complete Gate ledger

There are exactly 53 traceability rows whose `Required before v1.0` cell contains
`Yes`. Every one is classified below.

### Required-row totals

| Audit status | Count |
| --- | ---: |
| `satisfied` | 18 |
| `satisfied_with_approved_bounded_scope` | 34 |
| `evidence_required` | 1 |
| `implementation_required` | 0 |
| `product_decision_required` | 0 |
| `post_v1` | 0 |
| `not_required` | 0 |
| `unconditionally_excluded` | 0 |
| **Total** | **53** |

The last three zero counts apply only to required rows. Separate non-required,
post-v1, and excluded product areas are classified later in this audit.

### Direct evidence anchors

Every required row cites at least one direct automated evidence anchor:

| Anchor | Direct executable evidence |
| --- | --- |
| E-Rules | `tests/test_rules.py`, `tests/test_game_declaration.py`, `tests/test_game_value.py`, `tests/test_v1_official_rule_evidence.py` |
| E-Settlement | `tests/test_final_settlement.py`, `tests/test_settlement_normative_matrix.py`, `tests/test_claim_and_settlement_v1_compatibility.py` |
| E-Historical | `tests/test_historical_game.py`, `tests/test_historical_game_event_chain.py`, and focused shortening/Claim tests |
| E-List | `tests/test_fixed_three_player_historical_list.py`, `tests/test_fixed_three_player_historical_list_aggregation.py`, `tests/test_fixed_three_player_historical_list_comparison.py` |
| E-Match | `tests/test_match_capture_contracts.py`, `tests/test_match_workspace_persistence.py`, `tests/test_match_analysis_exports.py`, `tests/test_local_match_capture_web.py` |
| E-Session | `tests/test_public_session_api.py`, `tests/test_public_session_files.py`, `tests/test_session_transitions.py`, `tests/test_session_cli.py` |
| E-API | `tests/test_public_api_contracts.py`, `tests/test_public_python_api_v1.py`, `tests/test_installed_cli.py` |
| E-Provenance | `tests/test_field_provenance_coverage.py`, `tests/test_application_provenance.py`, `tests/test_complete_result_provenance.py`, `tests/test_public_field_provenance.py`, `tests/test_v1_input_provenance.py`, `tests/test_v1_provenance_enforcement.py`, `tests/test_v1_provenance_serialization.py`, `tests/test_v1_provenance_adversarial.py` |
| E-Simulation | `tests/test_simulation.py`, `tests/test_multi_step_simulation.py`, `tests/test_canonical_multi_step_phase.py`, `tests/test_canonical_multi_step_phase_execution.py`, `tests/test_simulation_provenance.py` |
| E-Inference | `tests/test_hidden_card_inference.py`, `tests/test_bounded_search_information.py` |
| E-Search | `tests/test_bounded_search_result.py`, `tests/test_bounded_search_quality_baselines.py`, `tests/test_bounded_search_benchmark.py` |
| E-Information-set | `tests/test_information_set_search_executor.py`, `tests/test_information_set_search_multi_step.py`, `tests/test_canonical_multi_step_phase_execution.py`, `tests/test_information_set_search_benchmark.py` |
| E-Recommendation | `tests/test_recommender.py`, `tests/test_recommendation_workflow.py`, `tests/test_live_search_recommendations.py` |
| E-Policy | `tests/test_opponent_policy.py`, `tests/test_opponent_profile_policy.py`, `tests/test_opponent_statistics.py`, `tests/test_opponent_profile_derivation.py`, `tests/test_historical_opponent_statistics.py`, `tests/test_rolling_opponent_policy_evaluation.py` |
| E-Review | `tests/test_post_game_review.py`, `tests/test_historical_search_review.py`, `tests/test_flat_retrospective_search_review.py` |
| E-Coaching | `tests/test_replay_coaching_report.py`, `tests/test_information_set_replay_coaching_report.py`, `tests/test_learning_corpus_tactical_coaching.py` |
| E-Tactical | `tests/test_historical_tactical_motif_review.py`, `tests/test_learning_corpus_tactical_motif.py` |
| E-Dataset | `tests/test_training_dataset.py`, `tests/test_training_dataset_preparation.py`, `tests/test_dataset_partition_audit.py`, `tests/test_learning_dataset_v2.py` |
| E-Output | `tests/test_examples.py`, `scripts/validate_examples_schema.py`, `scripts/validate_generated_outputs_schema.py` |
| E-Distribution | `tests/test_v1_package_license.py`, `tests/test_packaging_and_distribution.py`, `tests/test_installed_cli.py`, `scripts/validate_distribution_artifacts.py`, and `scripts/check.ps1` |

### ISkO required rows

| ID | Requirement | Current state | Audit status | Frozen v1 disposition and executable evidence | Blocker / owner |
| --- | --- | --- | --- | --- | --- |
| R-01 | Card ordering and card points | `supported` | `satisfied` | The independent literal oracle proves 32 unique Cards, 30 points per suit, 120 total points, 25 effective-category sequences, and 674 strict Suit, Grand, and Null pairwise comparisons. | None |
| R-02 | Trump rules | `supported` | `satisfied` | Current Suit, Grand, Null, and jack behavior is the v1 contract. | None |
| R-03 | Following suit and legal-card rules | `supported` | `satisfied` | Current legal-card and strict historical replay behavior satisfies the v1 gate. General revoke adjudication is not part of this row's v1 contract. | None |
| R-04 | Trick resolution | `supported` | `satisfied` | Current winner, ownership, points, and next-leader derivation satisfies the v1 gate. | None |
| R-05 | Bidding and declarations | `partially_supported` | `satisfied_with_approved_bounded_scope` | Final declaration, bid value, dependencies, and exclusions are v1; full auction modeling is `post_v1`. | None |
| R-06 | Suit and Grand game values | `partially_supported` | `satisfied` | The independent literal oracle proves all five bases and five canonical declaration variants across 220 Suit and 20 Grand rows while preserving the declared-value/Final-Settlement boundary. | None |
| R-07 | Null game values | `supported` | `satisfied` | Fixed values `23`, `35`, `46`, and `59` are complete for v1. | None |
| R-08 | Matadors | `partially_supported` | `satisfied_with_approved_bounded_scope` | Explicit bounds and deterministic complete-historical inference are v1; ambiguous partial positions may remain unavailable. | None |
| R-09 | Hand games | `partially_supported` | `satisfied_with_approved_bounded_scope` | Declaration, value, historical no-pickup, Skat ownership, point, and matador behavior are v1; physical inspection is not inferable. | None |
| R-10 | Schneider and Schwarz | `partially_supported` | `satisfied_with_approved_bounded_scope` | Current point, trick, announcement, bounded proof, and open-throw semantics are v1; general rule-violation correction and generalized theoretical exclusion are not. | None |
| R-11 | Ouvert declarations | `supported` | `satisfied` | Current dependency, fixed-value, public-hand, result, and Settlement behavior satisfies v1. | None |
| R-12 | Overbid handling | `partially_supported` | `satisfied_with_approved_bounded_scope` | Current Suit/Grand doubled-loss and separate supplied-replacement impossible-Null paths are v1. General rule-violation adjudication and replacement optimization are not required. | None |
| R-13 | Impossible Null declarations | `supported` | `satisfied_with_approved_bounded_scope` | The approved externally supplied favorable Suit/Grand replacement interpretation is the complete v1 boundary. | None |
| R-14 | Normal game completion | `partially_supported` | `satisfied_with_approved_bounded_scope` | Strict 32-card/30-play Historical completion and compatible legacy completed positions are retained. | None |
| R-15 | Claims | `partially_supported` | `satisfied_with_approved_bounded_scope` | The only v1 Claim is the Historical party-wide all-remaining-Tricks Claim with one through five unresolved Tricks and valid exact proof. | None |
| R-16 | Concessions | `partially_supported` | `satisfied_with_approved_bounded_scope` | Current structured declarer/defender flat and Historical concession behavior is the v1 boundary. Prediction, disputes, and language interpretation are not required. | None |
| R-17 | Final settlement | `partially_supported` | `satisfied_with_approved_bounded_scope` | Matrix version `3`, supported completion/shortening paths, bounded Claim composition, and approved impossible Null behavior define v1 Settlement. Complete official Settlement coverage is not claimed. | None |

### SkWO required rows

| ID | Requirement | Current state | Audit status | Frozen v1 disposition and executable evidence | Blocker / owner |
| --- | --- | --- | --- | --- | --- |
| W-01 | Fixed three-player list performance | `supported` | `satisfied_with_approved_bounded_scope` | The fixed-three-player 36-position formula, aggregation, and independent-list comparison are complete for v1. | None |
| W-02 | Standings | `supported` | `satisfied_with_approved_bounded_scope` | Current performance-point, win/loss, unresolved-tie, and externally supplied lot behavior is complete for v1. | None |

### Product required rows

| ID | Requirement | Current state | Audit status | Frozen v1 disposition and executable evidence | Blocker / owner |
| --- | --- | --- | --- | --- | --- |
| P-01 | Match Capture identity and metadata | `partially_supported` | `satisfied_with_approved_bounded_scope` | The private local fixed-format Match contract is the v1 surface. | None |
| P-02 | Observed Game evidence and commentary | `partially_supported` | `satisfied_with_approved_bounded_scope` | Exact observed behavior and uninterpreted Commentary/Response Links are the v1 boundary. | None |
| P-03 | Persistent EuroSkat Match Workspace | `partially_supported` | `satisfied_with_approved_bounded_scope` | Strict private version-1 one-file persistence and optimistic local Save are complete for v1. | None |
| P-04 | Rapid post-game Match Capture Application services | `partially_supported` | `satisfied_with_approved_bounded_scope` | Existing transport-free capture operations plus private browser orchestration are complete for v1. | None |
| P-05 | Match review and materialization preparation | `supported` | `satisfied_with_approved_bounded_scope` | Existing information-safe Decision, strict Historical, Training-source, and fixed-list preparation is complete for v1. | None |
| P-06 | Match analysis and private exports | `supported` | `satisfied_with_approved_bounded_scope` | Explicit bounded analysis, ephemeral reports, and private canonical downloads are the v1 surface. | None |
| P-07 | Local Match Capture browser and CLI transport | `supported` | `satisfied_with_approved_bounded_scope` | Loopback-only `capture` through one Console Script is complete for v1. | None |
| P-08 | Public Session APIs | `supported` | `satisfied_with_approved_bounded_scope` | Existing `skatmind.api.v1.session` and `.files` surfaces are frozen for v1. | None |
| P-09 | Stable public Python and installed CLI contract | `supported` | `satisfied` | Issue #205 completes the hard-cut `skatmind` distribution, import, module, CLI, Package Resource, Schema, active identifier, and strict legacy persisted-input migration boundary while preserving API contract version `1`, seven Root workflows, and one Console Script. | None |
| P-10 | Field-level information provenance | `partially_supported` | `satisfied` | Exact Request/effective-option/external sources, pre-analysis context enforcement, retained-stage authorization, exact final Result/artifact reconciliation, and adversarial evidence are complete without widening public Provenance. | None |
| P-11 | Interactive Session capture | `supported` | `satisfied_with_approved_bounded_scope` | Existing local API/file/CLI/Assistant workflow is complete; GUI, cloud, and platform adapters are not required. | None |
| P-12 | Private Session persistence and resume | `supported` | `satisfied_with_approved_bounded_scope` | Strict version-1 persistence, replay, fingerprints, CAS, and atomic replacement are complete for v1. | None |
| P-13 | Live information boundaries | `partially_supported` | `satisfied` | Exact source contexts are enforced before analysis and linked through retained Decisions/stages to final serialization; private and retrospective timing boundaries remain closed under adversarial mutation. | None |
| P-14 | Retrospective information | `supported` | `satisfied_with_approved_bounded_scope` | Existing decision-time, observed-card, and final-outcome separation is the v1 contract. | None |
| P-15 | Immediate simulation | `supported` | `satisfied` | Current deterministic bounded immediate simulation satisfies v1. | None |
| P-16 | Evidence-constrained hidden-card inference | `supported` | `satisfied_with_approved_bounded_scope` | Exact structural compatible-world inference with uncalibrated concentration labels is the v1 contract. | None |
| P-17 | Bounded search contracts | `partially_supported` | `satisfied_with_approved_bounded_scope` | Exact-world and compatible-world late-game PIMC, its integrations, work profiles, and deterministic evidence satisfy the bounded v1 solver contract. | None |
| P-18 | Information-set Search | `partially_supported` | `satisfied_with_approved_bounded_scope` | Current three-Trick controlled-player selected-world Search and integrations satisfy the bounded v1 solver contract. | None |
| P-19 | Multi-step simulation | `partially_supported` | `satisfied` | All nine concrete canonical phases analyze directly, prepare to the first new local Decision, or complete the existing Trick and continue from its exact winner under one coherent World. Completion consumes no local step, Search remains public-state-only, terminal completion uses an existing non-error reason, and unresolved non-concrete phases retain the bounded fallback. | None |
| P-20 | Card recommendations | `supported` | `satisfied` | Existing legal, objective-aware Immediate/Search/Auto recommendation behavior satisfies v1. | None |
| P-21 | Opponent policies | `supported` | `satisfied` | Existing deterministic global and side-specific policies satisfy v1. | None |
| P-22 | Player and opponent profiles | `partially_supported` | `satisfied_with_approved_bounded_scope` | Explainable rule-based, time-safe profile application is v1; learned profiles are `post_v1`. | None |
| P-23 | Profile confidence | `partially_supported` | `satisfied_with_approved_bounded_scope` | Current heuristic evidence bands and activation gates are v1; calibrated uncertainty is not claimed. | None |
| P-24 | Post-game decision review | `supported` | `satisfied` | Existing Suit/Grand/Null, declarer/defender, unavailable, and Search-comparison behavior satisfies v1. | None |
| P-25 | Complete-game retrospective analysis | `partially_supported` | `satisfied_with_approved_bounded_scope` | Existing one-game Replay Coaching, Information-set Coaching, and structural Tactical Review satisfy v1. Broader tactical truth, Ratings, and causality are not required. | None |
| P-26 | Historical tactical motif evidence | `supported` | `satisfied_with_approved_bounded_scope` | The exact structural, timed, non-quality taxonomy is the complete v1 boundary. | None |
| P-27 | Historical-game representation | `partially_supported` | `satisfied_with_approved_bounded_scope` | Normal completion, six terminal shortenings, one continuation, and the one bounded Claim form the v1 event boundary. | None |
| P-28 | Training-data representation | `partially_supported` | `satisfied_with_approved_bounded_scope` | Existing Dataset v1 representation and deterministic two-mode preparation satisfy v1 without training. | None |
| P-29 | Dataset partition policies and overlap audits | `supported` | `satisfied_with_approved_bounded_scope` | Current Known-opponent and Player-disjoint unseen-player policies satisfy v1. | None |
| P-30 | External opponent-statistics representation | `supported` | `satisfied` | Current version-1 external representation and Profile derivation satisfies v1. | None |
| P-31 | Historical player statistics | `supported` | `satisfied` | Current exact supported-game aggregation and export satisfies v1. | None |
| P-32 | Rolling opponent-policy evaluation | `supported` | `satisfied_with_approved_bounded_scope` | Current known-opponent behavioral imitation evaluation satisfies v1 without a strategic-quality claim. | None |
| P-33 | Generated-output validation | `supported` | `satisfied` | The frozen append-only 98-scenario matrix is the v1 baseline unless a blocker changes stable behavior. | None |
| P-34 | Release and regression checks | `supported` | `evidence_required` | Repository gates exist; #206 must reconcile the direct `referencing` import with supported dependency declarations/lower bounds before fresh final-candidate local and CI evidence. | B-05 / #206, then B-06 / #207 |

No required row remains unclassified or merely partially supported without an
approved bounded interpretation or exact blocker. B-09 is a separate Release-
process Gate outside the 53-row ledger and therefore does not alter these totals.

The ledger's `Current state` reproduces the pre-audit traceability status. The
disposition freezes the accepted behavior. The companion map below separately
records direct automated evidence and missing v1 work for every row. B-06 and
B-07 are aggregate final-audit and Release-preparation gates rather than
additional required rows, so they do not change the 53-row reconciliation.
B-09 is likewise a separate maintainer-acceptance Gate outside that ledger.

### Required-row evidence and missing-work map

| ID | Direct evidence | Missing v1 work | Blocker / owner |
| --- | --- | --- | --- |
| R-01 | E-Rules | None | None |
| R-02 | E-Rules | None | None |
| R-03 | E-Rules, E-Historical | None | None |
| R-04 | E-Rules, E-Historical | None | None |
| R-05 | E-Rules | None within approved final-declaration scope | None |
| R-06 | E-Rules | None within the declared/pre-result value scope | None |
| R-07 | E-Rules | None | None |
| R-08 | E-Rules, E-Historical | None within approved inference scope | None |
| R-09 | E-Rules, E-Historical | None within approved Hand scope | None |
| R-10 | E-Rules, E-Settlement | None within approved proof/throw scope | None |
| R-11 | E-Rules, E-Historical | None | None |
| R-12 | E-Rules, E-Settlement | None within approved overbid scope | None |
| R-13 | E-Settlement | None within approved supplied-replacement scope | None |
| R-14 | E-Historical, E-Settlement | None within approved completion scope | None |
| R-15 | E-Historical, E-Settlement | None within approved Claim scope | None |
| R-16 | E-Historical, E-Settlement | None within approved concession scope | None |
| R-17 | E-Settlement | None within Matrix version `3` scope | None |
| W-01 | E-List | None within fixed-three-player scope | None |
| W-02 | E-List | None within unresolved/external-lot scope | None |
| P-01 | E-Match | None within private local scope | None |
| P-02 | E-Match | None within observed/non-interpretive scope | None |
| P-03 | E-Match | None within one-file local persistence scope | None |
| P-04 | E-Match | None within private rapid-entry scope | None |
| P-05 | E-Match | None within no-execution preparation scope | None |
| P-06 | E-Match, E-Information-set | None within private analysis/export scope | None |
| P-07 | E-Match, E-API | None within loopback transport scope | None |
| P-08 | E-Session, E-API | None within stable Session API scope | None |
| P-09 | E-API, E-Distribution | None; Issue #205 completes the approved SkatMind Package/import/CLI/resource/identifier and migration boundary | None |
| P-10 | E-Provenance | None | None |
| P-11 | E-Session | None within local API/file/CLI scope | None |
| P-12 | E-Session | None within strict version-1 persistence scope | None |
| P-13 | E-Provenance, E-Simulation | None | None |
| P-14 | E-Historical, E-Provenance | None within decision-time/retrospective separation | None |
| P-15 | E-Simulation | None | None |
| P-16 | E-Inference | None within structural uncalibrated scope | None |
| P-17 | E-Search | None within bounded PIMC scope | None |
| P-18 | E-Information-set | None within three-Trick selected-world scope | None |
| P-19 | E-Simulation, E-Information-set | None | None |
| P-20 | E-Recommendation | None | None |
| P-21 | E-Policy | None | None |
| P-22 | E-Policy | None within rule-based Profile scope | None |
| P-23 | E-Policy | None within heuristic Confidence scope | None |
| P-24 | E-Review | None | None |
| P-25 | E-Coaching, E-Review | None within bounded one-game/selected-world scope | None |
| P-26 | E-Tactical | None within structural non-quality scope | None |
| P-27 | E-Historical | None within approved event boundary | None |
| P-28 | E-Dataset | None within Dataset-v1/no-training scope | None |
| P-29 | E-Dataset | None within two fixed partition algorithms | None |
| P-30 | E-Policy, E-Dataset | None | None |
| P-31 | E-Policy, E-Historical | None | None |
| P-32 | E-Policy, E-Dataset | None within behavioral-imitation scope | None |
| P-33 | E-Output | None | None |
| P-34 | E-Distribution | Reconcile the direct `referencing` import and runtime lower bounds; then produce fresh final source/Editable/Wheel/sdist and Windows/Ubuntu evidence and the final technical audit | B-05 / #206, then B-06 / #207 |

## Rules and Settlement

The bounded v1 rules contract is final declaration and play, not auction
reconstruction or general conduct adjudication. Issue #201 completes the
exhaustive card/ordering and accepted Suit/Grand declared-value evidence without
redesigning rules or Settlement code.

Settlement Normative Matrix version `3` retains exactly 61 canonical case IDs:

| Matrix classification | Count |
| --- | ---: |
| `supported_as_is` | 48 |
| `not_supported_v1` | 13 |
| `implementation_required` | 0 |
| `decision_required` | 0 |

The only supported v1 Claim is Retrospective Historical input for one stable
claimant's party claiming every unresolved Trick. The complete Deal and legal
prefix must reconstruct exact remaining hands; the incomplete current Trick is
allowed; one through five unresolved Tricks are supported; claimant-party choices
are existential and opposing-party choices are universal. Only a valid Proof
creates assignment, Result, and existing Final Settlement. Invalid or unavailable
Proof rejects the terminal record and creates no fallback outcome.

The durable v1 Claim exclusions remain unchanged: specific future-Trick Claims,
generalized correction, generalized non-jack theoretical exclusion, flat
Position, Session, Match, or Corpus Claim entry, multiple non-terminal events,
arbitrary event streams, simultaneous throws, free-text or natural-language
interpretation, generative adjudication, unclassified conduct, unlimited proof,
and defender proof beyond five unresolved Tricks.

## Search and solver

The approved v1 solver contract is the implemented bounded contract:

| Capability | Audit status | v1 boundary |
| --- | --- | --- |
| Immediate simulation | `satisfied` | Deterministic bounded one-Trick expected-value analysis. |
| Compatible-world PIMC | `satisfied_with_approved_bounded_scope` | Late exact-world Minimax and selected compatible-world aggregation with explicit exactness and Strategy-Fusion limitations. |
| Information-set Search | `satisfied_with_approved_bounded_scope` | At most three unresolved Tricks, controlled Player `me`, fixed deterministic other actors, one action for equal controlled Observations, and selected-world exactness only. |
| Broader solver algorithms | `post_v1` | Require separate product and acceptance contracts. |
| Complete-contract Search | `post_v1` | No v1 global complete-contract solver claim. |
| Equilibrium or CFR | `post_v1` | No equilibrium, Nash, or CFR requirement or claim. |
| Calibrated probabilities | `post_v1` | Compatible-world and concentration values remain structural and uncalibrated. |
| Wider Search bounds | `post_v1` | More than current five-Trick exact/PIMC or three-Trick Information-set bounds is later work. |
| Production performance acceptance | `satisfied_with_approved_bounded_scope` | Deterministic functional and structural-work signatures, bounded completion, and local reference measurements are the acceptance contract; elapsed time is diagnostic only. |
| Supported hardware/platform evidence | `evidence_required` | Final CPython 3.13 Windows and Ubuntu evidence is required after implementation blockers close. |
| Cross-machine latency guarantees | `not_required` | No SLO, P95/P99, or millisecond guarantee is part of v1. |
| Dedicated production Budget profiles | `not_required` | Existing immutable work profiles remain budgets, not latency contracts. |

No Search implementation issue follows from this audit. The Multi-Step blocker is
phase coverage and termination behavior, not a request for a broader solver.

## Provenance

Provenance is classified by lifecycle boundary rather than by whether a ledger
type exists:

| Lifecycle boundary | Audit status | v1 requirement |
| --- | --- | --- |
| Input loading and normalization | `satisfied` | Complete exact Request, effective-option, and optional injected-external sources retain the values consumed by all seven Root workflows. |
| Schema and contract validation | `satisfied` | Every exact source has complete canonical coverage and an independently retained Information Use Context enforced before handler dispatch. |
| Decision State construction | `satisfied_with_approved_bounded_scope` | Existing live and historical pre-selection/pre-play ledgers remain authoritative; general supplied context is completed by the loading closure. |
| Inference and analysis | `satisfied_with_approved_bounded_scope` | Existing hidden-card inference, profile, Immediate, Search, and retained analysis-stage evidence is sufficient. |
| Simulation and comparison | `satisfied_with_approved_bounded_scope` | Existing Multi-Step, Policy Comparison, Historical Review, and evaluation retained-stage evidence is sufficient within their bounded contracts. |
| Recommendation construction | `satisfied_with_approved_bounded_scope` | Existing legal-candidate, selected-method, fallback, and no-recommendation evidence is sufficient. |
| Retrospective actual-card and outcome attachment | `satisfied_with_approved_bounded_scope` | Existing decision-time/actual-card/final-outcome separation and isolated retained attachments are authoritative. |
| Coaching and Tactical derivation | `satisfied_with_approved_bounded_scope` | Existing Replay, Information-set, Tactical, and cross-game retained evidence is sufficient without truth or causal claims. |
| Root Result output | `satisfied` | All seven non-legacy Root Results have complete exact leaf coverage. |
| Actual artifacts | `satisfied` | The returned `opponent_statistics_input` artifact has its own complete attachment. |
| Final serialization | `satisfied` | The exact Root Result and actual artifact tuple are reconciled with retained complete ledgers immediately before Application return and revalidated before optional public conversion. |
| Public redaction | `satisfied` | Existing engine-private removal and recomputed exact coverage remains the v1 contract. |
| Public consumed-input provenance | `not_required` | Remains internal. |
| Public Decision provenance | `not_required` | Remains internal. |
| Public intermediate provenance | `not_required` | Remains internal. |
| Confidence integration | `not_required` | Provenance and Confidence remain separate contracts. |

Issue #202 completes the required internal v1 Provenance closure:

1. It covers validated loading and normalization for all seven Root workflows,
   including caller-supplied, copied, defaulted, canonically implied, inferred,
   replayed, and external-source values.
2. It enforces Information Use Context before analysis, with focused live,
   input, and retrospective reconstruction coverage.
3. It reconciles existing Decision and intermediate attachments to authorized loaded
   or retained values without rerunning analysis.
4. It reconciles final Root Result and returned artifact serialization with complete
   retained ledgers; reject mutation, uncovered leaves, orphaned entries,
   dependency errors, and leaked engine-private evidence.
5. It adds adversarial evidence for all seven workflows and entry-form
   serialization parity while preserving default omission and public redaction.

The mandatory stage sequence is `loaded_request`,
`validated_consumed_input`, `retained_stage_linkage`, and
`final_serialization`. See
[v1 information provenance enforcement](v1_information_provenance_enforcement.md).

Root and Session public provenance remain separate. Match and Corpus source
identities, persistence fingerprints, Teacher fingerprints, Tactical identities,
and Dataset-v2 fingerprints remain specialized private evidence rather than being
relabeled as field-level Provenance.

## API and Schema freeze

The intended v1 public boundary is frozen as follows:

* Stable namespaces are `skatmind`, `skatmind.api`, `skatmind.api.v1`,
  `skatmind.api.v1.session`, `skatmind.api.v1.session.files`, and
  `skatmind.errors`.
* Only each namespace's exact ordered `__all__` is stable. Direct internal
  imports remain unsupported.
* Public API contract version remains `1`.
* The seven Root workflows remain `position_analysis`, `historical_game`,
  `training_dataset`, `training_dataset_preparation`, `opponent_statistics`,
  `fixed_three_player_historical_list`, and
  `fixed_three_player_historical_list_comparison`.
* The normal Result states remain `complete`, `partial`, `timeout`,
  `unavailable`, `final`, `lot_required`, and `not_assessable`.
* The stable public error hierarchy, exact error codes, `code`/`message`/`path`
  serialization, and CLI Exit Codes `0`, `1`, and `2` remain unchanged.
* The Package Root remains exactly `api`, `errors`, and `__version__`.
* The only execution artifact remains `opponent_statistics_input`, returned by
  the explicit Training Dataset historical-aggregation export path.
* Root provenance remains optional, default false, and mapped only to one exact
  redacted Root Result plus artifacts actually returned.
* The Session API remains twelve operations with its current 59 exports. The
  Session file API remains Save/Load with its current 12 exports.
* Installed `skatmind`, module `python -m skatmind`, and repository Legacy
  `python main.py` remain the three supported CLI forms through Package 1.x.
* Private `capture` and `corpus` command families remain dispatch families under
  the one Console Script, not Root workflows or public Python namespaces.
* Existing optional fields and omission behavior are frozen. No new public field
  or export is required before v1.

The Schema freeze is the current exact set of 71 authoritative
`schemas/*.schema.json` filenames, `$id` values, bytes, and their 71 packaged
mirrors. The current `$id` convention remains
`https://example.local/skatmind/<filename>`. Existing document and focused Schema
versions remain unchanged. Session, Historical, Search, Coaching, Tactical,
Dataset, list, Provenance, and persistence version-1 contracts are not renumbered
for Package `1.0.0`.

No Public Match, Corpus, or Learning Dataset-v2 Schema is added to the v1 freeze.

## Deprecation and migrations

`SkatMindDeprecationWarning` remains the only public deprecation warning category.
No warning is emitted at the Issue #200 baseline.

The v1 policy is:

* existing `skatmind.api.v1`, Session, Session file, error, and Package-Root names
  remain source-compatible throughout Package 1.x;
* existing required fields and meanings are not removed or changed in Package
  1.x;
* compatible additive optional fields require defaults and omission-compatible
  behavior;
* removal requires a documented replacement, migration note, and at least one
  prior published 1.x release that emits `SkatMindDeprecationWarning`;
* removal is permitted no earlier than Package `2.0.0`;
* Legacy `python main.py` remains supported throughout Package 1.x and can be
  removed no earlier than `2.0.0` under the same warning and migration policy;
* direct internal imports receive no compatibility guarantee.

The existing exported compatibility-policy strings ending in
`additive_until_v1_0` and the Legacy target string `v1.0.0` remain immutable
version-1 contract values that record the original minimum pre-v1 commitment.
They do not prohibit the stronger Package-1.x source-compatibility policy frozen
here, and Issue #200 does not rename them or add replacement metadata. A future
machine-readable policy revision would be additive and is not required for v1.

Current SkatMind persisted Session, Match Workspace, Corpus Catalog, immutable
Corpus object, and Match Analysis Report-source values use canonical SkatMind
kinds and identity domains. Exact released pre-rename version-1 values remain
strict input-only compatibility profiles: readers verify their original kinds
and domains, reject mixed profiles, and never mutate files on Load. Explicit
successful Save or rewritten serialization emits canonical SkatMind identities;
verified immutable legacy Corpus object IDs remain opaque and are not rekeyed or
duplicated. Unsupported future document versions remain rejected explicitly.

## Persistence

| Surface | Audit status | Frozen v1 policy |
| --- | --- | --- |
| Session files | `satisfied_with_approved_bounded_scope` | Support all valid current private version-1 documents; preserve strict replay, fingerprints, CAS, and atomic replacement. |
| Match Workspaces | `satisfied_with_approved_bounded_scope` | Support all valid current private version-1 Workspaces; preserve one explicit file and optimistic local persistence. |
| Corpus Catalog and Snapshot objects | `satisfied_with_approved_bounded_scope` | Support current private version-1 root/catalog/object contracts, explicit Current selection, no-clobber objects, and orphan reporting. |
| Unsupported future versions | `satisfied` | Reject explicitly with no implicit conversion. |
| Pre-v1 document migration | `satisfied` | Issue #205 provides strict legacy input-only verification, no mutation on Load, canonical explicit rewrites, and opaque immutable Corpus ID retention without a compatibility Package or CLI alias. |
| Recovery, merge, distributed lock, encryption, cloud sync, backup | `not_required` | Not v1 persistence gates. |

Fingerprints continue to prove deterministic identity and conflict state, not
confidentiality, authorship, field provenance, or cryptographic access control.

## Match, Corpus, and Dataset boundaries

| Product surface | Audit status | v1 classification |
| --- | --- | --- |
| Private local Match Capture and analysis | `satisfied_with_approved_bounded_scope` | Supported through the existing loopback browser, one Workspace, explicit analysis, ephemeral reports, and private downloads. |
| Public Match API | `not_required` | No v1 namespace or exported Python contract. |
| Public Match Schema or Root workflow | `not_required` | No eighth Root workflow or Match data Schema. |
| Private local Corpus workflow | `satisfied_with_approved_bounded_scope` | Supported through one explicit root, explicit preparation, process-local derived artifacts, and ten authenticated downloads. |
| Public Corpus API or Schema | `not_required` | No v1 public surface. |
| Public Dataset-v2 API or Schema | `not_required` | Learning Dataset version `2` remains private and task-neutral. |
| Player Catalog persistence | `not_required` | Remains derived from explicit Current Snapshots. |
| Dataset-v2 or partition persistence | `not_required` | Remains process-local with canonical path-free export. |
| Tactical or Coaching derived persistence | `not_required` | Remains process-local and reproducible from exact sources. |
| Automatic Report capture | `not_required` | Report creation remains explicit. |
| Historical Report import | `not_required` | Historical Reports remain ineligible Teacher sources. |
| Database deployment | `not_required` | Local files remain authoritative for v1. |
| Remote, hosted, or collaborative deployment | `post_v1` | Requires separate security, identity, concurrency, and operations contracts. |

These classifications are v1 release requirements, not permanent exclusions.
Any later public or persisted surface requires a new product decision and cannot
be inferred from current private canonical exports.

## Dataset and evaluation

The two Dataset generations and their evaluations remain separate:

| Capability | Audit status | Frozen v1 evidence and boundary |
| --- | --- | --- |
| Public Training Dataset version `1` | `satisfied_with_approved_bounded_scope` | Information-safe historical Decision samples, explicit train/validation/test partitions, provenance, and actual-card targets are stable without claiming optimal labels. |
| Public Dataset preparation version `1` | `satisfied_with_approved_bounded_scope` | Deterministic `known_opponent` and `unseen_player` plans, explicit unavailable Results, exact arithmetic, fingerprints, seeds, and lossless materialization are complete; no additional algorithm is required. |
| Partition policy and overlap audits | `satisfied_with_approved_bounded_scope` | Temporal Known-player and Player-component unseen-player assignment, Match/Player disjointness, and exact overlap reporting are accepted without global balancing or ratio guarantees. |
| Bounded Search Dataset evaluation | `satisfied_with_approved_bounded_scope` | Validation/test evaluation with immutable work profiles and explicit coverage/status metrics is accepted without calibrated quality or latency claims. |
| Information-set Dataset evaluation | `satisfied_with_approved_bounded_scope` | Selected-world evaluation reuses strict information-safe Records, fixed Policies, bounded Budgets, and safe aggregates without exposing private Worlds or controlled Policies. |
| Rolling opponent-policy evaluation | `satisfied_with_approved_bounded_scope` | Time-safe known-opponent behavioral imitation against a fixed baseline is complete; it is not a strategic-quality evaluation. |
| Private Learning Dataset version `2` | `satisfied_with_approved_bounded_scope` | Current-Snapshot-only task-neutral Decision State, observed behavior, Player Context, Teacher, Commentary, Response, and skip/join evidence remain private and process-local. Tactical evidence remains a separate family and does not change Dataset version `2`. |
| Dataset-v2 partition preparation and summaries | `satisfied_with_approved_bounded_scope` | Match-Snapshot-safe indexes, temporal/component assignment, leakage audits, exact descriptive counts, and supplied-partition readiness are complete without derived persistence. |
| Model training or model-readiness claim | `post_v1` | No training workflow, learned model, target-specific builder, performance claim, or deployment contract is part of v1. |

Observed Cards remain behavior evidence rather than perfect-play labels. Teacher
evidence remains method-specific and bounded by its retained executed Result.
Dataset-v2 does not replace, version-bump, or broaden the stable public Training
Dataset version `1` workflow.

## Coaching, Tactical, and Rating boundary

The v1 Coaching and Tactical contract consists of separate evidence families:

* bounded Replay Coaching;
* Information-set Replay Coaching;
* Historical Tactical Motif Review;
* Current-Snapshot Tactical Motif Evidence;
* Tactical Cross-game Summary; and
* Tactical Cross-game Coaching.

Replay Coaching remains one-game, decision-time-safe, method-bound guidance.
Information-set Coaching treats complete Information-set Candidates as primary
evidence and PIMC/Immediate as diagnostics, not fallback truth. Tactical Motifs
remain structural observations with exact timing. Cross-game focus remains a
bounded review aid requiring unanimous complete-Search Teacher evidence and the
existing recurrence threshold.

The following are `not_required` for v1: tactical ground truth, actual-card
optimal-label claims, Player traits, broader tactical-quality classification,
signaling or communication interpretation, causal attribution, statistical
significance, and broader Player Ratings. Existing fixed-three-player SkWO-style
performance scoring remains a bounded list calculation and is not a general
Player Rating.

## Privacy and product claims

The v1 privacy boundary preserves decision-time information cutoffs, explicit
retrospective attachment, private hidden Worlds and hands, path-free public and
download documents, and existing public redaction. Private Match and Corpus
loopback transports remain authenticated, same-origin, local-only workflows;
that boundary is not a remote security, encryption, account, or cloud claim.

Permitted product claims are limited to deterministic local analysis,
information-safe bounded simulation and review, exact evidence-constrained world
handling, selected-world Search under its stated limits, structural Tactical
evidence, exact descriptive counts, and the supported rule/Settlement matrix.
The product does not claim:

* the actual hidden deal or calibrated hidden-card probabilities;
* perfect play, equilibrium, global optimality, or complete official Skat
  solving;
* tactical truth, signaling, communication, intent, traits, causality, or
  statistical significance;
* Player skill Ratings or strategic-quality evaluation;
* learned behavior, model readiness, or model training;
* latency, cross-machine performance, availability, or hosted-service guarantees;
  or
* complete official rule, conduct, correction, tournament, or reporting
  coverage.

## Performance and platforms

The v1 performance gate is deterministic and structural. The existing bounded
Search and Information-set Search corpora must preserve functional signatures,
structural work signatures, privacy, deterministic budgets, and completion or
explicit bounded stop semantics. Recorded elapsed measurements remain local
observations. No elapsed-time threshold is added.

The v1 platform boundary is:

* Package metadata accepts Python `>=3.13`;
* release acceptance executes on CPython 3.13;
* Windows 11 with Windows PowerShell 5.1 is the supported local full-check path;
* Ubuntu GitHub Actions with Python 3.13 is the supported CI path using the
  equivalent explicit commands;
* Wheel and sdist remain pure-Python artifacts;
* no macOS support or test-matrix claim is made;
* no processor, memory, or cross-machine latency guarantee is made;
* private browser transports are supported as loopback HTTP contracts with
  packaged standards-based assets, without a named browser-vendor matrix; and
* remote binding remains unsupported.

Fresh Windows and Ubuntu evidence is required for the final v1 candidate. Wider
Python and operating-system matrices may be added later but are not v1 gates.

## Packaging and license

The v1 Package boundary retains Setuptools PEP 517, one Wheel, one sdist,
`py.typed`, 71 packaged byte-identical Schemas, packaged Capture/Corpus assets,
one runtime dependency, one `dev` extra, and exactly one Console Script.

| Metadata dimension | Frozen pre-v1 value and v1 acceptance |
| --- | --- |
| Build backend | `setuptools.build_meta` with `setuptools>=77.0.3` |
| Python metadata | `requires-python = ">=3.13"`; metadata permits later compatible Python versions, while the frozen v1 evidence matrix certifies CPython 3.13 only |
| Runtime dependency | Issue #204 preserves `jsonschema>=4.0.0`; #206 must reconcile the direct `referencing` import with supported declarations and lower bounds before final acceptance |
| Development extra | `build>=1.2.2`, `pytest>=9.0.0`, and `ruff>=0.14.0` |
| Console Script | Exactly `skatmind = skatmind.cli:main` |
| Artifact forms | One pure-Python Wheel and one sdist, plus source and Editable-install validation |
| Package data | `py.typed`, 71 Schema Resources, and packaged Capture/Corpus templates, CSS, and JavaScript |
| Package license | `AGPL-3.0-only` with exact root `LICENSE` and `COPYRIGHT`, PEP 639 Core Metadata, Wheel/sdist/installed bytes, and focused dependency/asset audit |
| Final evidence | Clean source, Editable, Wheel, and sdist acceptance with fresh Windows/Ubuntu results under #206 |

Clean-install validation for the final candidate must cover:

* exact Package/Python/API metadata and Package Root;
* all seven Root workflows through the public API and installed/module CLI where
  applicable;
* normal successful unavailable/incomplete Results;
* exact public errors and Exit Codes;
* Root provenance omission and opt-in;
* Session API/files and installed/module Session commands;
* private Capture and Corpus help, assets, loopback smoke, and all ten Corpus
  downloads;
* Wheel/sdist equality and absence of a second Console Script or GUI Script; and
* repository-only Legacy parity in the checkout.

Author, classifier, project URL, Package-index, and PyPI metadata are
`not_required` for v1. Publication remains a human-controlled GitHub Release.

Issue #204 applies the maintainer-approved GNU Affero General Public License
version 3 only under exact SPDX expression `AGPL-3.0-only`. Root `LICENSE` and
`COPYRIGHT`, PEP 639 metadata, exact Wheel/sdist/installed legal-file bytes,
Wheel `RECORD`, focused tests, and the direct-dependency/bundled-asset audit close
B-04 without changing product behavior. See
[v1 Package license](v1_package_license.md). Issue #205 subsequently completes
the SkatMind Package and migration boundary, makes P-09 `satisfied`, and closes
B-08 without changing the license, dependency set, or Package version.

## Examples and generated outputs

The final v1 example and output matrix is frozen to the current set unless a
blocker changes stable behavior:

| Matrix | Frozen v1 coverage |
| --- | --- |
| Root examples | Every current repository Root example remains schema-valid and semantically validated across Position, Historical, Training Dataset, Preparation, Opponent Statistics, and both fixed-list workflow families. |
| Session examples | Exactly `session_create_live.json`, `session_create_retrospective.json`, `session_command_record_play.json`, `session_correction_record_play.json`, `session_live_persistence.json`, and `session_retrospective_persistence.json`. |
| Generated outputs 1-70 | Pre-Provenance Root workflow and bounded behavior matrix. |
| Generated outputs 71-77 | One public Provenance scenario for each of seven Root workflows. |
| Generated outputs 78-85 | Eight Session scenarios. |
| Generated outputs 86-88 | Three Historical Claim scenarios. |
| Generated outputs 89-92 | Four Information-set Search flat/Historical/Dataset scenarios. |
| Generated outputs 93-94 | Information-set Multi-Step and Policy Comparison. |
| Generated outputs 95-96 | Information-set Replay Coaching, including Claim. |
| Generated outputs 97-98 | Historical Tactical Motif Review, including Claim. |
| Private Match/Corpus | Distribution and focused tests, not public Root examples or generated outputs. Corpus coverage includes all ten canonical downloads. |

The cross-surface coverage matrix is:

| Workflow or stable major submode | Schema | Root example | Session example | Generated output | Public API | Installed CLI | Module CLI | Legacy CLI | Distribution smoke | Provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Position: Immediate, Search, Auto, Information-set, Multi-Step, Policy Comparison | Yes | Yes | Position export path | Yes | Yes | Yes | Yes | Yes | Current; refresh #206 | Complete Root Result plus retained stages |
| Historical: flat/Search/Information-set Review, Replay Coaching, Tactical Review, bounded Claim | Yes | Yes | Historical export path | Yes | Yes | Yes | Yes | Yes | Current; refresh #206 | Complete Root Result plus retained stages |
| Training Dataset: materialization, Search/Information-set evaluation, statistics export | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Current; refresh #206 | Complete Root Result and actual artifact |
| Training Dataset Preparation: Known-player and unseen-player | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Current; refresh #206 | Complete Root Result |
| Opponent Statistics | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Current; refresh #206 | Complete Root Result |
| Fixed three-player Historical List | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Current; refresh #206 | Complete Root Result |
| Fixed three-player Historical List Comparison | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Current; refresh #206 | Complete Root Result |
| Session API/files, 12 Commands, Assistant, Position/Historical execution | Yes | N/A | Six exact files | Eight scenarios | Session API | Yes | Yes | Yes | Current; refresh #206 | Separate complete Session provenance |
| Private Match Capture and analysis | No public Schema | N/A | N/A | N/A | Private only | Yes | Yes | Yes | Packaged assets and loopback smoke; refresh #206 | Specialized source/report evidence only |
| Private Corpus and ten downloads | No public Schema | N/A | N/A | N/A | Private only | Yes | Yes | Yes | Packaged assets/download smoke; refresh #206 | Specialized fingerprints and evidence only |

This matrix records stable public and private transport coverage without turning
private Match or Corpus surfaces into Root workflows. B-05/#206 requires fresh final
candidate execution across the current source, Editable, Wheel, sdist, Windows,
and Ubuntu boundaries; it does not imply a missing example, Schema, or workflow.

The exact ordered `SCENARIOS` tuple in
`scripts/validate_generated_outputs_schema.py` remains authoritative. No rewrite
of historical Release counts or scenario order is allowed. A later blocker may
append a scenario only when stable public behavior actually changes; no current
blocker is expected to require a Schema or generated-output addition.

## Accepted bounded v1 limitations

The following are accepted limitations, not blockers:

* fixed three-player tables only;
* final declaration rather than auction-sequence reconstruction;
* one Historical-only party-wide Claim bounded to five unresolved Tricks;
* only the six supported Historical terminal shortenings and at most one
  supported continuation before completion or shortening;
* externally supplied impossible-Null replacement rather than optimization;
* bounded late-game exact and compatible-world PIMC Search;
* three-Trick selected-world Information-set Search for controlled Player `me`
  against fixed deterministic actors;
* no global Policy, equilibrium, calibrated probability, complete Strategy-
  Fusion correction, or complete-contract optimality claim;
* rule-based opponent profiles and heuristic Confidence;
* structural hidden-card inference and Tactical Motifs without real-deal,
  tactical-truth, trait, signaling, communication, significance, or causal
  claims;
* private local Match and Corpus surfaces;
* process-local derived Player, Dataset-v2, Tactical, and Coaching artifacts;
* one-game public Coaching plus bounded private cross-game Coaching;
* structural performance acceptance without latency guarantees;
* strict version-1 local persistence with bounded legacy input-only rename
  migration, but without remote access, encryption, merge, or backup; and
* Package-index/PyPI publication is not required.

## Post-v1 work

These are approved later directions and are not v1 blockers:

* full bidding and auction sequence modeling;
* broader and complete-contract solver algorithms;
* wider Information-set Search bounds and broader imperfect-information policy
  solving;
* equilibrium/CFR research and calibrated probability models;
* learned opponent profiles;
* machine-learning card-decision models and training;
* online-platform adapters, browser extensions, hosted or remote browser
  integration; and
* remote or collaborative deployment after separate security and operations
  contracts.

## Not-required work

The following are not required for v1 and have no approved implementation issue
in the ordered plan:

* formal series aggregation;
* tournament management;
* official federation report formats;
* Public Match, Corpus, or Dataset-v2 APIs or Schemas;
* Match or Corpus Root workflows;
* Player Catalog, Dataset-v2, Tactical, or Coaching derived persistence;
* automatic Report capture or Historical Report import;
* database deployment;
* broader Player Ratings;
* tactical truth, trait, communication, signaling, causal, or significance
  classification;
* public consumed-input, Decision, or intermediate Provenance attachments;
* Provenance/Confidence unification;
* Session GUI/browser UI;
* distributed locking, merge/retry, encryption/key management, or automatic
  backup;
* additional general pre-v1 persisted-document migration tooling beyond the
  strict Issue #205 rename adapters;
* dedicated production Budget profiles;
* cross-machine latency, SLO, P95, or P99 guarantees;
* a macOS or named-browser certification matrix;
* Package authors, classifiers, project URLs, Package-index, or PyPI publication;
* an Information-set-aware `auto`; and
* general natural-language or generative Claim adjudication.

`not_required` here means not required for the bounded v1 product. It does not
mean permanently excluded unless separately classified below.

## Unconditional exclusion

Four-player table support is `unconditionally_excluded`. It is the only
unconditional exclusion.

## Exact blockers

Issue #201 closes B-01 with the independent evidence documented in
[v1 official-rule evidence](v1_official_rule_evidence.md). Issue #202 closes
B-02 with the internal lifecycle documented in
[v1 information provenance enforcement](v1_information_provenance_enforcement.md).
Issue #203 closes B-03 with the contract and direct evidence documented in
[Canonical Multi-Step phase coverage](canonical_multi_step_phase_coverage.md).
Issue #204 closes B-04 with the decision and direct evidence documented in
[v1 Package license](v1_package_license.md). Issue #205 closes B-08 with the
rename and migration boundary documented in
[SkatMind rename and migration](skatmind_rename_and_migration.md). `v1.0.0` is
not ready. Exactly these four blockers remain; B-09 is outside the 53-row ledger:

| Blocker | Status | Required closure |
| --- | --- | --- |
| B-05 | `evidence_required` | After the rename, reconcile the direct `referencing` import with supported dependency declarations/lower bounds, then complete the final all-seven-workflow source/Editable/Wheel/sdist matrix and fresh CPython 3.13 Windows/Ubuntu evidence under #206. |
| B-06 | `evidence_required` | After B-05, record the final technical v1 scope/readiness audit, full local check, CI result, and clean worktree evidence under #207. |
| B-07 | `implementation_required` | After B-09 and resolution of accepted UAT findings, prepare Package `1.0.0`, matching version expectations, Changelog, and Release-candidate documentation without product behavior changes. Its Issue number is not frozen. |
| B-09 | `evidence_required` | After the final technical audit, complete hands-on maintainer v1.0.0 user acceptance testing under #208 and resolve every accepted finding before Release preparation. |

No blocker requires a new Claim interpretation, broader Search algorithm,
Public Match/Corpus/Dataset-v2 surface, Player Rating, latency threshold, or
persisted-format migration.

## Exact ordered Issue plan

The smallest coherent follow-up sequence is frozen as:

| Order | Issue and type | Primary Gate and blocking requirements | Scope | Dependencies | Expected product-code change | Expected public-contract change | Expected Schema change | Release relevance |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **#201 - Complete v1 official-rule evidence closure**; evidence | Rules and Settlement; R-01, R-06, B-01 | Add exhaustive card/rank and accepted Suit/Grand value/variant tables; change no approved rule interpretation. | #200; completed | No; focused tests/evidence only | None | None | Closed the official-rule evidence gate. |
| 2 | **#202 - Complete internal v1 information-Provenance enforcement**; implementation and evidence | Provenance/privacy; P-10, P-13, B-02 | Implement and test loading, retained-stage linkage, final serialization, and adversarial closure. | #200 and completed #201; completed | Yes, internal enforcement | No new public field, version, or default behavior | None | Closed internal information-safety implementation before candidate validation. |
| 3 | **#203 - Complete canonical Multi-Step phase coverage**; implementation and evidence | Simulation; P-19, B-03 | Analyze, prepare, or terminate every valid canonical phase under documented semantics; preserve coherent-world and Search boundaries. | Completed #202; completed | Yes, bounded phase handling | Existing fields only; one existing generated scenario changes from unsupported to executable without changing its identity, public shape, or the count | None | Closed the final functional behavior gate. |
| 4 | **#204 - Decide and apply the v1 Package license boundary**; product decision and metadata | Packaging/license; B-04 and P-09's license portion | Apply exact `AGPL-3.0-only` legal files, PEP 639 metadata, artifact evidence, audit, and documentation. | #200; ordered after #203; completed | No product behavior; metadata/files only | Package license metadata only, not Python API or CLI behavior | None | Closes B-04 before the rename and distribution evidence. |
| 5 | **#205 - Rename the complete project and public Package surface to SkatMind**; implementation and migration | Public Package identity; P-09, B-08 | Coordinate repository `hnnng-w/skatmind`, distribution/import/CLI/resource/current-documentation migration, compatibility, and persisted/hashed identifier boundaries. | Completed #204; completed, with manual GitHub rename verification retained before Issue closure | Yes, focused rename and migration work | Public Package/import/module/CLI identity changes under the approved migration contract | No count or structure change; all 71 Schema identities migrate | Completes the required pre-v1 public identity. |
| 6 | **#206 - Complete the v1 installation and supported-platform matrix**; evidence | Packaging/platforms; P-34, B-05 | Reconcile the direct `referencing` import with supported dependency declarations/lower bounds, add all-seven-Root-workflow source/Editable/Wheel/sdist evidence, and verify CPython 3.13 on Windows and Ubuntu with the renamed CLI/browser/download boundaries. | Completed #205 | No product behavior expected; Package dependency metadata and validation scripts/tests may change | Package dependency metadata may be corrected; no Python API or CLI behavior change | None | Produces final candidate installation/platform evidence. |
| 7 | **#207 - Perform the final technical v1.0.0 Release-readiness audit**; documentation audit | All technical Gate clusters; B-06 | Reconcile #201 through #206, the 53-row ledger, exact counts, final full check, CI, diff, and technical Release blockers. | #206 and successful CI | No | None | None | Decides whether maintainer UAT may begin. |
| 8 | **#208 - Perform maintainer v1.0.0 user acceptance testing**; evidence | Release process; B-09 | Execute hands-on maintainer UAT after #207 and record and resolve every accepted finding before Release preparation. | #207 technical-readiness approval | No product behavior expected; accepted findings may require separate remediation Issues | None expected | None expected | Provides the required human acceptance Gate outside the 53-row ledger. |

B-01 is closed by #201, B-02 by #202, B-03 by #203, B-04 by #204, and B-08 by
#205. The exact next action is B-05/#206, followed by B-06/#207 and B-09/#208.
Release preparation remains B-07 and occurs only after #208 and remediation of
all accepted findings. Its Issue number is not frozen; it is expected to be #209
only when #208 produces no remediation Issues. Publication, tagging, GitHub
Release creation, and post-publication synchronization remain human-controlled
and unnumbered here.

## Final conclusion

The exact bounded v1 product scope is frozen by this audit. Current Claims,
Settlement, bounded PIMC, selected-world Information-set Search, one-game
Coaching, structural Tactical evidence, private Match/Corpus/Dataset-v2
workflows, stable Public API/Session/CLI surfaces, 71 Schemas, six Session
examples, 98 generated outputs, and ten Corpus downloads are accepted as the v1
baseline under their documented limitations.

The 53 required traceability rows are completely classified as 18 `satisfied`,
34 `satisfied_with_approved_bounded_scope`, 1 `evidence_required`, 0
`implementation_required`, and 0 `product_decision_required`. Issue #201 closes
B-01 without product-code change, Issue #202 closes B-02, and Issue #203 closes
B-03. Issue #204 applies `AGPL-3.0-only` and closes B-04 without product-code
change. Issue #205 completes the SkatMind migration and closes B-08. Four blockers
B-05, B-06, B-07, and B-09 remain, with B-09 outside the 53-row ledger.
Therefore:

```text
v1.0.0 scope:
    frozen

v1.0.0 implementation and evidence:
    incomplete

v1.0.0 Release readiness:
    blocked by B-05, B-06, B-07, and B-09

v1.0.0 Release title, theme, date, tag, and publication commit:
    not frozen
```

The traceability audit is fully classified, every remaining blocker is mapped to
the exact ordered plan, and Release preparation is not ready. The exact next
action is Issue #206, **Complete the v1 installation and supported-platform
matrix**.

## Exact next action

| Conclusion field | Current result |
| --- | --- |
| Traceability | Fully classified: all 53 required rows have one audit status, direct evidence, missing-work state, and blocker owner. |
| Blocker mapping | B-01 closed by #201, B-02 by #202, B-03 by #203, B-04 by #204, and B-08 by #205; B-05/#206, B-06/#207, and B-09/#208 remain, followed by unnumbered B-07 Release preparation. |
| Issue #200 implementation | Complete; this audit changes documentation only. |
| Issue #201 evidence closure | Complete; R-01 and R-06 are `satisfied`, and B-01 is closed without product-code change. |
| Issue #202 Provenance closure | Complete; P-10 and P-13 are `satisfied`, and B-02 is closed without widening public Provenance. |
| Issue #203 canonical phase closure | Complete; P-19 is `satisfied`, and B-03 is closed without widening Search or public contracts. |
| Issue #204 Package license closure | Complete after successful validation; exact `AGPL-3.0-only` legal files and PEP 639 evidence close B-04 without product behavior or active-name changes. |
| Issue #205 SkatMind rename closure | Complete after successful validation; P-09 is `satisfied`, B-08 is closed, and the maintainer must verify the manual GitHub repository rename before closing the Issue. |
| Release preparation | Not ready while B-05, B-06, B-07, and B-09 remain open; B-09 is outside the required-row ledger. |
| Next action | Issue #206, **Complete the v1 installation and supported-platform matrix**. |
