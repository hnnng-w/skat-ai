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

### Game-end handling

Implemented:

* Normal completion
* Declarer claims remaining tricks
* Declarer concedes remaining tricks
* Defenders concede remaining tricks
* Immediate impossible Null declaration end handling
* Remaining-point assignment for claim/concession scenarios
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
* Information-safe pre-play snapshots for all 30 decisions in a normal-play historical game
* Bounded 30-decision historical review with deterministic seeds and reconciled player summaries

### Training and evaluation data

Implemented:

* Versioned normal-play training and evaluation dataset records
* Required source provenance and explicit `train`, `validation`, and `test` partitions
* Deterministic 30-sample conversion from each historical game
* Relative model-facing features and `actual_card_played` version-1 labels
* Duplicate identity and cross-partition game/source leakage rejection
* Reuse of the dataset as the multi-game source for sample-free historical opponent-statistics aggregation

### Validation and documentation

Implemented:

* Input JSON schema
* Output JSON schema
* Focused historical-game, decision-snapshot, historical-review, training-dataset, and historical opponent-statistics aggregation schemas
* Input example schema validation
* Generated-output schema validation
* Full check script with Ruff, input schema validation, generated-output validation, and pytest
* Topic-specific documentation split into `docs/`
* Project handoff documentation
* Authoritative requirements traceability and testable `v1.0.0` scope

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

## Current known limitations

### Gameplay and rules

* The engine is not a full perfect-information solver.
* The engine is not a complete official tournament system.
* The engine focuses on analysis and simulation, not on training a machine-learning model.
* Full official settlement nuance coverage is not complete.
* Claim and concession handling assigns remaining card points according to `game_end_reason`; it does not simulate the actual remaining tricks.
* The engine does not yet verify whether a claim was strategically or legally justified.
* The engine does not yet model player agreement or disputes around claim/concession.
* Multi-Step intentionally does not auto-complete every opponent-only continuation; valid phases where the local player has already acted stop with `unsupported_turn_phase`.
* Impossible Null settlement requires an external Suit or Grand replacement selection; it remains incomplete when that selection or its required matadors are unavailable.
* Matador inference uses currently known declarer-card context and safe concrete-declarer completed-trick ownership facts; it does not reconstruct all possible matador information from complete historical trick ownership in every scenario.
* Complete historical-game records currently support normal completion only; claims, concessions, and other later end reasons are not represented there.
* Claims and concessions remain simplified, and general settlement coverage is incomplete.
* Historical ouvert decisions expose public cards in snapshots but do not run exposed-card-aware recommendation simulation.
* General live position inputs do not provide complete field-level provenance.
* Multi-Step does not preserve one coherent hidden-world assignment across every simulated path.
* Training-dataset partitions are not player-disjoint.

### Performance rating

* Performance rating is partially implemented for fixed three-player single-game declarer rating and bounded list-aware summaries.
* `rating_score` currently equals `declarer_rating_score`.
* Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
* Series aggregation, tournament aggregation, and official report formats are not implemented yet.
* Four-player table performance rating is not modeled because the project assumes a fixed three-player table.

### Opponent modeling

* Opponent behavior is still simplified and rule-based.
* Defender cooperation has improved, but it is still heuristic and not a full tactical model.
* Defender cooperation assumes the fixed three-player table.
* Defender partnership inference is strongest in the currently supported second-hand path.
* There is no complete rear-hand partnership model.
* There is no dedicated null-game defender-partnership strategy.
* There is no stable declarer/partner identity when the local player itself is only known generically as `defender`.
* Defender cooperation does not use perfect-information solving, search, machine learning, or hidden-card inference.
* Opt-in profiles can influence policy presets, and exact statistics can be aggregated from historical games, but profile behavior is not learned.
* Profile derivation uses documented deterministic thresholds and heuristic evidence bands, not calibrated uncertainty.
* External-statistics derivations require profile-preset opt-in plus either explicit live side bindings or exact time-safe historical participant matching.
* Historical aggregation does not enforce player-disjoint partitions, weight or merge sources, manage multiple captures, apply policies automatically, evaluate policy effects or profile quality, or learn behavior.

### Information modeling

* The project enforces the main live-vs-post-game information boundaries.
* The engine still depends on the correctness of the provided position context.
* Some older or intentionally minimal completed-trick inputs may not contain enough metadata for full verification.
* Live decision examples should not contain post-game-only information.

## Release baselines

### v0.7.0: Rules confidence and information-safe historical workflows

The current code and package version is `0.7.0`. Generated-output validation
covers 31 deterministic scenarios. Issues #69 through #76 are complete, and
Issues #80 through #82 add bounded reusable opponent-profile data workflows:

* #69 defined the v1.0 scope, requirements traceability, and project baseline.
* #70 enforced canonical Suit/Grand declaration dependencies and matador bounds.
* #71 aligned fixed three-player standings ties with SkWO 6.3.1.
* #72 added bounded settlement for impossible Null declarations.
* #73 added complete normal-play historical-game records.
* #74 added information-safe snapshots for all 30 historical decisions.
* #75 added bounded complete historical-game decision review.
* #76 added versioned historical training and evaluation dataset records.
* #80 attached reusable external statistics to live analysis through exact,
  independent left/right player bindings and existing actionable profile presets.
* #81 applies captures strictly older than `played_at` to historical review by
  exact participant ID while preserving per-decision side mapping and precedence.
* #82 aggregates exact settlement-based statistics from selected timestamped
  historical dataset games and exports them for existing live and historical
  profile loaders without training, automatic application, or quality claims.

`v0.6.0` remains the latest human-published release until a maintainer tags and
publishes `v0.7.0`.

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
decisions, and testable completion gates.

Four-player tables are the only area unconditionally out of scope. Series,
tournament, official reporting, historical-statistics extensions, learned
behavior, machine-learning training, stronger solving, broader hidden-card
inference, claim verification, and complete-game coaching must retain the
classifications in `docs/v1_scope.md` until explicit product decisions change
them.

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
should distinguish the `v0.7.0` implementation baseline, the latest published
release, requirements explicitly required for `v1.0.0`, planned post-v1.0 work,
and topics that still require a product decision.
