# Roadmap

This document tracks completed areas, known limitations, and planned improvements for `skat-ai`.

## Completed major areas

### Core analysis

Implemented:

* Core card rules and legal-card handling
* Card-point calculation
* Trump and trick-winner logic
* JSON-based position analysis
* Monte Carlo-style card analysis
* Expected point swing calculation
* Card recommendation
* JSON output for regression-friendly analysis

### Simulation

Implemented:

* Immediate trick simulation
* Multi-step simulation
* Canonical turn-phase enforcement for Immediate and Multi-Step analysis
* Opponent-turn Multi-Step preparation for supported left/right lead and response phases
* Simulation context tracking
* Strict simulation context checks
* Policy comparison across card-selection strategies
* Result serialization for multi-step and policy-comparison output
* One immutable private hidden-world root per Multi-Step path with owner-aware card removal and a fixed hypothetical skat
* One shared Policy Comparison root with equal independent immutable copies for policy paths
* Privacy-safe coherent-world count and status summaries without hidden cards
* Exact hidden-card constraints from local/public ownership, legitimately known skat, attributed public play, and confirmed legal failure to follow
* Exact DP compatible-world counts and ownership marginals with deterministic uniform labeled-assignment sampling
* Common compatible worlds for Immediate candidates, compatible Multi-Step roots, shared Policy Comparison models/roots, and later visible evidence progression
* Version-1 bounded-search information, private immutable exact complete-world state, deterministic legal transitions, eligibility, structural budget, terminal utility, aggregate result, privacy, and strict standalone-schema contracts
* Executable `perfect_information_minimax_v1` for one exact Suit, Grand, or normal non-overbid Null state with at most five remaining tricks, canonical full-window root values, deterministic below-root Alpha-Beta, invocation-local exact-only transposition reuse, and exact terminal settlement utility; all four Null variants use trick ownership, fixed-value settlement, and no card-point secondary objective
* Private compatible Search-world construction from `SearchInformationView`, exact counting with or without void evidence, canonical bounded enumeration, deterministic uniform IID sampling with replacement, retained duplicate accounting, strict exact-state materialization, and one frozen common legal-root world order
* Executable `compatible_world_minimax_v1` with shared exact-world recursion, frozen-order common-prefix scheduling, global nodes, per-world depth and exact-only cache, one post-selection timeout window, equal duplicate-sample weighting, aggregate ranking, and threshold-gated partial or timeout recommendations
* Explicit flat live `immediate_expected_value`, strict `bounded_search`, and Search-first `auto` recommendation methods with validated budgets, separate seeds, explicit fallback, report separation, schema output, CLI summaries, and privacy-safe examples
* Opt-in Search-aware Multi-Step and Policy Comparison with public-state re-search at every local decision, fresh per-decision budgets, domain-separated child seeds, coherent execution-world separation, strict stopping, auto fallback, eligibility-aware ranking, and compact privacy-safe diagnostics
* Flat post-game bounded Search with an independently executed Immediate baseline plus actual-card and Search-versus-Immediate aggregate comparisons
* Historical Search Review over every decision-time snapshot with stable private per-decision seeds and reconciled status, coverage, agreement, quality, and performance summaries
* Bounded-Search dataset evaluation over canonical validation/test defaults, optional stable global decision-prefix caps, and preserved zero-decision records
* Immutable `interactive_v1`, `historical_review_v1`, and `evaluation_v1` work-budget profiles
* Independent exhaustive Suit, Grand, and Null strict-improvement fixtures plus 32/64/128-draw convergence evidence
* Deterministic Suit/Grand/Null benchmark corpus and measured performance documentation with no calibrated latency guarantee

### Game history and scoring

Implemented:

* Completed-trick structure validation
* Completed-trick sequence validation
* Completed-trick rule-winner validation
* Explicit and completed-trick point summaries
* Game result summaries
* Schneider/Schwarz status summaries
* Versioned complete normal-play historical-game records
* Full-deal, ownership, play-order, follow-rule, winner, point, and settlement replay validation
* Exact-prefix historical records for declarer concession, defender concession, accepted declarer-card exposure, bounded defender open play, and open-card throwing
* One timed non-terminal defender-open-play or declarer-card-exposure continuation before normal completion or one supported terminal shortening
* Variable-length decision artifacts based on actual supplied play count

### Game declaration and settlement

Implemented:

* Game declaration metadata
* Canonical Suit and Grand declaration dependencies
* Official Suit `1..11` and Grand `1..4` matador bounds
* Game value summaries for suit, grand, and null games
* Automatic matador inference from known declarer-card context and safe concrete-declarer completed-trick ownership facts where possible
* Final single-game settlement summary
* Supported Suit/Grand overbid detection
* Supported Suit/Grand overbid settlement loss handling
* Bounded impossible Null settlement from an externally supplied Suit or Grand replacement
* Immutable [version-1 normative settlement matrix](settlement_normative_matrix.md)
  with direct-rule,
  approved-bounded, legacy, implementation-required, decision-required, and
  `v0.11.0` exclusion classifications

### Game-end handling

Implemented:

* Normal completion
* Declarer claims remaining tricks
* Structured concealed or verbal declarer concession with exact hand-card and defender-consent rules
* Structured defender concession with concrete party validation, joint liability, and preexisting-result preservation
* Unanimously accepted declarer card exposure with complete-card reconciliation and claimed-level settlement
* Ongoing ISkO 4.4.4 play after an objection with an exact all-player public declarer hand across Immediate, Multi-Step, Policy Comparison, and flat review
* Bounded exact defender open play for at most five unresolved tricks
* Ongoing ISkO 4.4.5/4.1.6 play with the exposing defender's exact returned public hand
* Open-card throwing with opposing-party assignment and bounded jack-only theoretical Schwarz exclusion
* Legacy declarer concession remaining-point assignment
* Defenders concede remaining tricks
* Immediate impossible Null declaration end handling
* Remaining-point assignment for legacy claim/concession scenarios
* No-assignment adjudicated defender win and declared/overbid settlement for structured declarer concession
* No-assignment defender-concession adjudication for Suit, Grand, and all Null variants
* Adjusted game-result summaries

### Performance rating

Implemented:

* Partial fixed-three-player SkWO-style single-game performance rating
* Declarer rating score
* Declarer rating points
* Counterparty/defender rating points
* Explicit separation between settlement score and rating score
* Single-rated-player list performance summaries from already aggregated totals, normalized contributions, and local analysis results
* Explicit fixed three-player list standings output
* SkWO 6.3.1 shared ranks for unresolved ties and optional external lot order

### Metadata and information control

Implemented:

* Strategic metadata
* Player profiles
* Profile-based policy recommendations
* Versioned overall, declarer, and defender profile evidence and heuristic confidence
* Explainable confidence-gated signals, classifications, and preset metadata
* Live-vs-post-game information enforcement
* `information_policy_summary` output
* Rejection of post-game-only information in `live_decision`
* Requirement that ended game reasons use `post_game_review`
* Version-1 privacy-safe hidden-card inference summaries with explicit non-behavioral, non-calibrated, no-future-information flags

### Opponent modeling

Implemented:

* Opponent policy presets
* Optional profile-based policy presets
* Profile-confidence conflict resolution for cautious/aggressive preset evidence
* Deterministic aggressive-over-defender conflict precedence within one profile
* External opponent-statistics derivation and explicit stable-ID live application
* Independent left/right external bindings with actionable-only gating and manual/policy precedence
* Strict pre-game external-profile application to historical review through exact participant IDs and per-decision relative remapping
* Exact opponent-statistics aggregation from canonical timestamped training-dataset partitions with a strict optional cutoff
* Settlement-based role, win, Hand, and contract counts with per-player historical provenance and reusable export
* Rolling game-start as-of known-opponent profiles with strict temporal source selection
* Acting-player preferred-card and exact-card behavioral matching against the fixed `simple_lowest` baseline
* Actionable-only paired comparisons, coverage, and bounded evaluation breakdowns
* Separate left/right opponent policy settings
* Left/right profile-derived presets applied to effective left/right multi-step policies
* Left/right opponent policy input fields
* Left/right opponent policy CLI overrides
* Left/right opponent policy output settings
* Shared effective opponent-policy resolver for immediate, multi-step, and policy-comparison paths
* Left/right policy handling in multi-step opponent lead and response paths
* Explicitly activated opponent response policies in immediate analysis
* Explicitly activated opponent response policies in multi-step candidate completion
* Unified response-policy precedence for input presets, profile presets, and CLI overrides
* Basic defender cooperation improvements and issue #22's current heuristic defender-partnership scope:

  * safer defender lead
  * avoiding overtaking a winning partner when a partner-safe legal card exists
  * safe smear while preserving the partner's winning position
  * forced partner overtake using the lowest-point legal winning card
  * equal-point forced-overtake tie-break using weakest sufficient trick strength
  * winning-card selection using the lowest-point legal winner
  * equal-point winning-card tie-break using weakest sufficient trick strength
  * equal-point safe-smear tie-break using weakest trick strength
  * narrow second-hand trump conservation on zero-point non-trump leads when only trump wins and a losing discard exists
  * safer discard when the declarer is winning and the defender cannot win

### Post-game review

Implemented:

* Optional `actual_card_played` input
* Validation that the actual card is valid and legal in the analyzed position
* `post_game_review_summary` output
* Comparison between actual card and recommended card
* Expected point swing difference between actual and recommended card
* Decision quality classification:

  * `not_available`
  * `optimal`
  * `acceptable`
  * `suboptimal`
  * `mistake`
* Machine-readable decision factors
* Human-readable decision explanation
* Recommendation gap details:

  * `actual_card_rank`
  * `recommended_card_rank`
  * `candidate_count`
  * `better_card_count`
* Human-readable CLI output for post-game review summaries, including objective-aware Null review wording
* Unavailable post-game review shape when Immediate Analysis is unavailable
* Information-safe pre-play snapshots for every actual play in each supported historical terminal record
* Variable-length historical review, including zero-decision records, with deterministic seeds and reconciled player summaries
* Declared-Ouvert and continuation public hands at their exact decision-time visibility boundaries
* Flat and Historical Search review with independent Immediate baselines and strict aggregate comparison output
* Internal Replay Coaching contract version 1 with separate decision-time evidence and retrospective actual-card assessment, deterministic Search-first evidence priority, stable impact tiers/factors/limitations, and unchanged public review output

### Training and evaluation data

Implemented:

* Versioned normal-play and shortened-game training and evaluation dataset records
* Required source provenance and explicit `train`, `validation`, and `test` partitions
* Deterministic zero-through-30 sample conversion from each supported historical game
* Relative model-facing features and `actual_card_played` version-1 labels
* Duplicate identity and cross-partition game/source leakage rejection
* Optional version-1 known-opponent and unseen-player partition policy metadata
* Deterministic exact-player membership, pairwise/three-way overlap, directed known-opponent coverage, and unseen-player compliance audits
* Strict declared unseen-player disjointness with backward-compatible unspecified policy intent
* Reuse of the dataset as the multi-game source for sample-free historical opponent-statistics aggregation
* Deterministic bounded-Search evaluation on selected partitions with one global decision cap, zero-decision preservation, quality-gate arithmetic, and aggregate breakdowns

### Validation and documentation

Implemented:

* Input JSON schema
* Output JSON schema
* Focused historical-game, decision-snapshot, historical-review, training-dataset, and historical opponent-statistics aggregation schemas
* Focused strict hidden-card inference summary schema
* Focused strict bounded-search aggregate result schema
* Focused strict flat post-game Search, Historical Search Review, and bounded-Search evaluation schemas
* Input example schema validation
* Generated-output schema validation
* Full check script with Ruff, input schema validation, generated-output validation, and pytest
* Topic-specific documentation split into `docs/`
* Project handoff documentation
* Authoritative requirements traceability and testable `v1.0.0` scope
* Version-1 settlement normative matrix and table-driven runtime-kind coverage

### CLI and workflow usability

Implemented:

* Improved CLI help text and command discoverability
* Optional `--quiet` mode for automation-friendly JSON-output runs
* Curated workflow walkthroughs for common user-facing CLI commands
* Generated-output validation for representative user-facing workflows, including late-game history-heavy live input
* Policy-comparison-only CLI output handling
* CLI sample-bound validation fixes
* Complete historical-game validation, optional snapshot output, and optional historical review
* Separate training-dataset conversion with strict rejection of unrelated analysis options
* Historical opponent-statistics aggregation with partition/cutoff selection, separate normal output and export paths, and quiet output
* Isolated `--audit-dataset-partitions` workflow with optional policy-mode resolution
* `--historical-search-review` with explicit `--search-seed` and named profile selection
* `--evaluate-bounded-search` with repeatable partition selection and optional global decision cap

## Current known limitations

### Gameplay and rules

* The engine has one bounded exact-state Suit, Grand, and normal non-overbid Null
  perfect-information solver, not a full or general hidden-information solver.
* The engine is not a complete official tournament system.
* The engine focuses on analysis and simulation, not on training a machine-learning model.
* Full official settlement nuance coverage is not complete.
* Legacy claim and concession reasons assign remaining points; the first three structured shortening kinds preserve them as unplayed, bounded defender open play records exact rule assignment, and open card throw records unconditional opposing-party rule assignment.
* The engine verifies only bounded ISkO 4.4.5 defender rest-trick claims; no general claim-verification protocol exists.
* Structured declarer concession models accepted defender consent; structured defender concession applies joint liability without partner consent. Disputes are not modeled.
* Multi-Step intentionally does not auto-complete every opponent-only continuation; valid phases where the local player has already acted stop with `unsupported_turn_phase`.
* Impossible Null settlement requires an external Suit or Grand replacement selection; it remains incomplete when that selection or its required matadors are unavailable.
* Matador inference uses currently known declarer-card context and safe concrete-declarer completed-trick ownership facts; it does not reconstruct all possible matador information from complete historical trick ownership in every scenario.
* Historical records support normal completion and all five terminal shortenings with at most one optional timed defender-open-play or declarer-card-exposure continuation. Multiple non-terminal events, arbitrary event streams, other claims, and other end reasons are not represented there.
* Historical corrected play and isolated or specific-trick claims remain incomplete; unlimited proof, simultaneous throws, and arbitrary event streams are outside `v0.11.0`; general settlement coverage is incomplete.
* General live position inputs do not provide complete field-level provenance.
* A coherent Multi-Step root is one compatible hypothetical execution world, not proof of the real deal or exhaustive search. Hidden-card inference is bounded to confirmed structural decision-time evidence and does not infer tactics or actual ownership.
* Version-1 bounded-search contracts, direct exact-world and compatible-world
  Suit/Grand/Null Minimax, and private deterministic compatible-world selection
  with strict exact-state materialization exist. Compatible execution retains
  only one exact common completed prefix and remains determinization-based and
  subject to strategy fusion. Null requires a bid no greater than its fixed
  value; overbid Null replacement selection remains unsupported. Flat and
  opt-in Multi-Step/Policy Comparison live routing, CLI summaries, and explicit
  auto fallback exist. Flat post-game Search, Historical Search Review, and
  Search-versus-Immediate dataset evaluation now use immutable versioned work
  profiles. Search remains bounded late-game determinization, sampled quality is
  not calibrated, and measured performance provides no latency guarantee.
* Player-disjoint partitions can be declared and validated, but automatic splitting, balancing, and repartitioning are not implemented.
* Replay Coaching now has internal version-1 evidence and impact contracts, but key-decision ranking, turning points, patterns, recommendations, tactical detectors, and a complete report remain unimplemented.

### Performance rating

* Performance rating is partially implemented for fixed three-player single-game declarer rating and bounded list-aware summaries.
* `rating_score` currently equals `declarer_rating_score`.
* Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
* Formal series aggregation, tournament management, and official federation report formats are not required product workflows.
* Four-player table performance rating is not modeled because the project assumes a fixed three-player table.

### Opponent modeling

* Opponent behavior is still simplified and rule-based.
* Defender cooperation has improved, but it is still heuristic and not a full tactical model.
* Defender cooperation assumes the fixed three-player table.
* Defender partnership inference is strongest in the currently supported second-hand path.
* There is no complete rear-hand partnership model.
* There is no dedicated null-game defender-partnership strategy.
* There is no stable declarer/partner identity when the local player itself is only known generically as `defender`.
* Defender cooperation does not use perfect-information solving, search, machine learning, behavioral/Bayesian inference, or broader tactical hidden-card inference.
* Opt-in profiles can influence policy presets, and exact statistics can be aggregated from historical games, but profile behavior is not learned.
* Profile derivation uses documented deterministic thresholds and heuristic evidence bands, not calibrated uncertainty.
* External-statistics derivations require profile-preset opt-in plus either explicit live side bindings or exact time-safe historical participant matching.
* Historical aggregation accepts compliant known-opponent and unseen-player datasets but does not infer policy, weight or merge sources, manage multiple captures, apply policies automatically, or learn behavior. The separate rolling evaluation measures observed behavioral matching only, not profile quality or strategic strength.

### Information modeling

* The project enforces the main live-vs-post-game information boundaries.
* The engine still depends on the correctness of the provided position context.
* Some older or intentionally minimal completed-trick inputs may not contain enough metadata for full verification.
* Live decision examples should not contain post-game-only information.
* ISkO 4.4.4 continuation is a narrow rule-authorized exception that exposes only the exact current declarer hand; defender reaction cards remain hidden.
* ISkO 4.4.5/4.1.6 continuation is a second narrow exception that fixes only the exposing defender's returned complete current hand; the declarer, partner, and skat remain protected.
* Declared Ouvert fixes only the exact current declarer hand from declaration visibility; it can coexist with a disjoint returned defender hand.
* ISkO 4.4.6 open throw exposes only the complete thrown hand. A non-throwing local hand is redacted, and no hidden complete hand or exact proof is emitted.

## Release baselines

### v0.10.0: Information-safe bounded Search across compatible worlds

The current published stable release and package baseline are `v0.10.0`, and
Issues #107 through #115 complete the functional milestone. Issue #116 completed
release preparation, followed by manual maintainer publication. The latest
GitHub Release points to commit `b4c8738`, validates 59 deterministic generated-
output scenarios, and passes 4,075 pytest tests. GitHub Releases remains
authoritative for publication status.

The milestone provides bounded-Search contracts, immutable exact state, Suit,
Grand, and all four normal non-overbid Null solving, compatible-world counting
and selection, common-prefix aggregation, live and simulated integration,
fallback, Historical Search Review, dataset evaluation, immutable profiles,
quality and convergence evidence, and measured reference performance.

### v0.9.0: Structured game endings and coherent hidden information

The historical published `v0.9.0` release tag points to commit `0679760`, and
Issues #86 through #104 are complete:

* #86 through #92 added structured concessions and exposures, bounded defender-open-play adjudication, open-card throwing, and both exact-public-hand continuation paths.
* #93 through #101 added all five exact-prefix historical terminal events, both timed non-terminal continuation events, variable-length decision and dataset workflows, and shortened-game opponent workflows.
* #102 made Immediate, supported Multi-Step, Policy Comparison, flat review, and Historical Review recommendation paths declared-Ouvert-aware.
* #103 preserved one coherent private hidden world per Multi-Step path and one shared root across independent Policy Comparison copies.
* #104 added exact evidence-constrained compatible-world counts, marginals, deterministic uniform sampling, decision-time-safe workflow integration, and privacy-safe uncalibrated summaries.

The published baseline validates 52 deterministic generated-output scenarios
and passes 3,558 pytest tests. GitHub Releases is the authoritative publication
record.

### v0.8.0: Explainable and time-safe opponent intelligence

The bounded Issues #78 through #84 milestone is complete:

* #78 added versioned external opponent-statistics records with stable identity, provenance, eight percentages, and optional exact counts.
* #79 added deterministic explainable profile derivation with scoped heuristic confidence and actionable gating.
* #80 applied actionable profiles to independent live left/right sides through exact stable-ID bindings while preserving manual and explicit policy precedence.
* #81 applied profiles to historical review through exact participant matching, strict `captured_at < played_at` safety, and per-decision side remapping.
* #82 aggregated exact settlement-based statistics from timestamped historical dataset games and exported records for existing live and historical loaders.
* #83 evaluated rolling acting-player card imitation with strict as-of history, the fixed `simple_lowest` baseline, policy-equivalent preferred cards, and actionable paired metrics.
* #84 added known-opponent and unseen-player dataset policies, exact membership and overlap audits, directed coverage, and strict declared unseen-player disjointness.

### v0.7.0: Rules confidence and information-safe historical workflows

The documented `v0.7.0` issue scope is complete:

* #69 defined the v1.0 scope, requirements traceability, and project baseline.
* #70 enforced canonical Suit/Grand declaration dependencies and matador bounds.
* #71 aligned fixed three-player standings ties with SkWO 6.3.1.
* #72 added bounded settlement for impossible Null declarations.
* #73 added complete normal-play historical-game records.
* #74 added information-safe snapshots for all 30 historical decisions.
* #75 added bounded complete historical-game decision review.
* #76 added versioned historical training and evaluation dataset records.

### v0.6.0: From single-position analysis to credible list-aware review workflows

The documented `v0.6.0` issue scope is complete:

* #62 added fixed three-player list standings output.
* #63 expanded list-performance examples and generated-output validation.
* #64 improved post-game review example quality and explanation coverage.
* #65 added controlled left/right opponent policy effect coverage.
* #66 used profile confidence in bounded opponent-strategy decisions.
* #67 audited settlement and overbid edge-case coverage.
* #68 prepared release metadata, changelog, roadmap, and handoff documentation.

No `v0.6.0` commit, merge, tag, publication, release, or issue-closeout action
remains pending.

## v1.0 direction

The [requirements traceability matrix](requirements_traceability.md) is the
authoritative audit of current ISkO, SkWO, and skat-ai product support. The
[v1.0 scope](v1_scope.md) defines required product directions, unresolved
implementation details, and testable completion gates.

Before `v1.0.0`, the project still requires fuller Replay Coaching, remaining
approved settlement nuance,
fixed-three-player 36-game list aggregation, remaining automatic dataset
preparation, field-level live provenance, interactive live and retrospective
input/session capture, and a stable library API and installed CLI/package
interface. General claim verification and historical end reasons outside the
supported bounded set also remain incomplete. Structured concessions and
exposures, bounded defender open play, open-card throwing, supported historical
terminal and continuation events, variable-length workflows, Ouvert-aware
recommendation, coherent hidden worlds, and bounded structural inference are
already implemented.
The approved [settlement matrix](settlement_normative_matrix.md) defines their
normative scope, and the bounded continuation-plus-terminal-shortening sequence
is implemented through delegation to the existing terminal cases. Claims,
Concessions, and Final Settlement remain partially supported.

Full auction modeling, learned opponent profiles, machine-learning card-decision
models, and platform or browser adapters are planned after `v1.0.0`. Formal
series aggregation, tournament management, and official federation report
formats are not required. Four-player tables are the only unconditional
exclusion.

The published `v0.10.0` milestone is complete.
Version-1 bounded Search/Solver
information, quality, determinism, budget, exactness, aggregate-result, privacy,
exact complete-world state, and deterministic legal-transition contracts are
implemented together with bounded direct and compatible-world Minimax for late
Suit, Grand, and normal non-overbid Null states. Compatible execution uses the
same exact evaluator in frozen selected order, retains only complete common-
prefix aggregates, and preserves equal duplicate-draw weight. Exhaustive
coverage is exact across compatible worlds, while sampled and partial claims are
narrower; determinization and strategy fusion prevent an optimal imperfect-
information policy claim. Flat live workflow and explicit fallback integration
are implemented; opt-in Multi-Step and Policy Comparison, flat post-game review,
Historical Search Review, and Search-versus-Immediate dataset evaluation are also
integrated. Immutable work profiles, independent quality fixtures, sampled
convergence checks, and a reproducible performance corpus provide bounded
evidence. They do not provide calibrated sample quality, a latency guarantee,
information-set policy search, or complete-contract solving, so the stronger-
search completion gate is not closed.

The active next planning milestone is `v0.11.0`, directed at Replay Coaching and
remaining approved rule/claim/settlement completion. Its final theme,
feature issue split, and implementation details require a separate focused
repository analysis.
Issue #118 establishes the normative settlement matrix as the first contract
foundation for that milestone.
Issue #120 establishes the information-safe Replay Coaching evidence and impact
contracts without adding a public report, schema, CLI field, or causal outcome
claim. Full Replay Coaching remains open.
Later milestone numbers remain planning containers rather than fixed
contractual releases.

## Open technical cleanup

Recommended cleanup areas:

* Maintain `CHANGELOG.md` for release notes as future milestones are completed.
* Keep README short and topic-focused.
* Keep topic-specific docs in `docs/` aligned with implemented behavior.
* Continue improving JSON schema coverage where useful without duplicating too much Python validation logic.
* Centralize any remaining duplicated CLI/configuration constants.
* Consider fully centralizing immediate and multi-step opponent-policy precedence once the existing multi-step compatibility behavior can be changed safely.

## GitHub issue status

Issue tracking should continue to use small, focused follow-ups. New issues
should distinguish the published `v0.10.0` release baseline, the authoritative
publication state shown by GitHub Releases, requirements explicitly required
for `v1.0.0`, planned post-v1.0 work, not-required workflows, and unconditional
exclusions.
