# Changelog

## v0.11.0

**Release theme: Information-safe Replay Coaching and structured historical outcomes**

### Normative settlement and historical event chains

* Add the immutable 61-case normative settlement matrix, classifying direct,
  bounded, compatibility-only legacy, undecided, and excluded scope without
  changing adjudication or settlement behavior (Issue #118).
* Document the current structured endings, bounded defender-open-play proof,
  jack-only open-card-throw exclusion, decision-required future claims, and the
  explicitly incomplete general claim, concession, and settlement boundary.
* Support one timed non-terminal historical continuation followed by normal
  completion or one supported terminal shortening, with unchanged terminal
  adjudicators and settlement semantics (Issue #119).

### Replay Coaching evidence and prioritization

* Build decision-time evidence before attaching the observed card, retain the
  observed card only as retrospective evidence rather than ground truth, and use
  Search-first Contract-success, settlement-score, then Suit/Grand-margin impact
  ordering with an explicit Immediate-only boundary (Issue #120).
* Treat forced and aggregate-equivalent decisions as non-errors. Add at most five
  deterministic Key Decisions plus separate decision-opportunity and recorded-
  outcome Turning Points without single-card causality claims (Issue #121).

### Patterns and actionable recommendations

* Add one-game player, role, phase, and contract patterns under a two-occurrence
  convention, separating actionable from descriptive patterns (Issue #122).
* Add deterministic objective-aware decision and pattern recommendations without
  tactical, psychological, skill, statistical-significance, causal, or
  generative-text claims (Issue #122).

### Complete report and public workflow

* Compose the complete internal one-game report from retained assessment,
  prioritization, and guidance artifacts, then attach isolated Outcome Context
  with non-ranking player, role, phase, and contract summaries (Issue #123).
* Expose the opt-in `--historical-replay-coaching` historical-game workflow under
  `historical_replay_coaching_summary`, validated by
  `historical_replay_coaching.schema.json` (Issue #124).
* Reuse `--search-seed`, `--search-budget-profile`, `--samples`, and `--seed`;
  support Coaching-only output or one-pass combination with Historical Search
  Review; preserve full JSON, concise CLI, and quiet-mode behavior (Issue #124).

### Information safety, determinism, and compatibility

* Keep final outcome context outside decision-time evidence: it describes how
  the recorded game ended and does not change Coaching classification.
* Recursively exclude hands, final hidden ownership, Skat identities, discards,
  compatible-world identities and contents, private Search states, derived
  seeds, caches, branches, principal variations, ratings, and rankings from
  public Coaching output.
* Preserve all schema, Search, Replay Coaching, normative-matrix, historical,
  budget-profile, and dataset versions. Existing workflows remain unchanged when
  Replay Coaching is omitted.

### Validation

* Validate 64 deterministic generated-output scenarios, including three public
  Replay Coaching scenarios and two continuation-before-shortening scenarios.
* Pass the complete pytest suite together with Ruff, input/example schema
  validation, and generated-output schema validation on Python 3.13.

## v0.10.0

**Release theme: Information-safe bounded Search across compatible worlds**

### Search contracts and exact-world solving

* Add immutable information-safe Search views, explicit eligibility, deterministic
  node/depth/sample budgets, a separate machine-dependent timeout, and stable
  `complete`, `partial`, `timeout`, and `unavailable` result semantics (Issue
  #107).
* Add immutable perspective-neutral exact states, canonical legal-card
  generation, pure transitions, neutral terminal facts, and shared exact
  transition reuse (Issue #108).
* Add bounded Perfect-Information Minimax for exact Suit and Grand worlds with
  deterministic Alpha-Beta search, exact-only transposition reuse, and existing
  result, value, overbid, settlement, and utility semantics (Issue #109).
* Extend exact-world solving to Null, Null Hand, Null Ouvert, and Null Hand
  Ouvert when they are normal non-overbid contracts (Issue #110). Search remains
  limited to the lower of five remaining tricks and the requested budget.

### Compatible worlds and aggregate Search

* Build private compatible-world spaces from the information-safe view, count
  worlds exactly, canonically enumerate bounded complete spaces, and sample
  larger spaces as deterministic uniform IID draws with replacement (Issue
  #111). Duplicate draws retain their repeated aggregate weight.
* Evaluate one frozen selected-world sequence with exact-world Minimax and retain
  only the common completed-world prefix (Issue #112). Exhaustive completion is
  exact across all compatible worlds, sampled completion is exact only per
  selected draw, and partial or timeout values are exact only over the retained
  completed prefix.
* Exact compatible-world counts do not identify the real deal, and sampled
  ownership quality is not calibrated probability. Compatible-world Minimax is
  determinization subject to Strategy Fusion, not an optimal imperfect-
  information policy.

### Live and simulated workflow integration

* Add explicit flat `bounded_search` and Search-first `auto` routing while
  preserving Immediate expected value as the omitted default (Issue #113).
  Strict Search never falls back; auto uses Immediate only after a valid Search
  result has no recommendation.
* Integrate opt-in Search into Multi-Step local decisions and Policy Comparison
  with fresh deterministic per-decision budgets and seeds, public-state
  reconstruction, coherent execution-world separation, and privacy-safe
  diagnostics (Issue #114).
* Keep Search opt-in and information-safe across live, Multi-Step, and Policy
  Comparison workflows. Existing omitted-method workflows require no migration.

### Retrospective review and evaluation

* Add flat post-game Search with an independently executed Immediate baseline,
  actual-card aggregate ranking, and Search-versus-Immediate comparison (Issue
  #115).
* Add information-safe Historical Search Review with private stable decision
  seeds and reconciled status, coverage, agreement, quality, and performance
  summaries (Issue #115).
* Add deterministic bounded-Search dataset evaluation over selected decision
  prefixes while preserving zero-decision records and existing dataset,
  feature, target, and schema versions (Issue #115).

### Budgets, quality, determinism, and performance

* Add the immutable `interactive_v1`, `historical_review_v1`, and
  `evaluation_v1` named work-budget profiles (Issue #115).
* Add Search-versus-Immediate quality gates, independent exhaustive Suit, Grand,
  and Null strict-improvement fixtures, and 32/64/128-draw convergence evidence
  against exhaustive references (Issue #115).
* Add the deterministic version-1 Suit/Grand/Null benchmark corpus and measured
  local reference performance with node and world diagnostics (Issue #115).
  Timings are reference measurements, not cross-machine guarantees, and
  wall-clock timeout activation is machine-dependent.
* Search remains bounded late-game determinization, not complete-contract Search.
  Overbid Null remains outside normal Search when no external replacement is
  available. No machine-learning model exists, four-player tables remain
  excluded, and complete official rule coverage is not claimed.

### Validation

* Validate 59 deterministic generated-output scenarios without changing schema,
  example, or generated-scenario versions.
* Pass 4,075 pytest tests together with Ruff, input/example schema validation,
  and generated-output schema validation on Python 3.13.

## v0.9.0

**Release theme: Structured game endings and coherent hidden information**

### Structured game-end handling

* Add structured declarer concession, defender concession, unanimously accepted
  declarer-card exposure, bounded exact defender open play, and open-card
  throwing for Suit, Grand, and all four Null variants (Issues #86 through #92).
* Continue play after rejected declarer-card exposure with the exact public
  declarer hand, or after defender open play with the exposing defender's exact
  returned public hand, without adjudication or settlement.
* Preserve preexisting results where required, enforce mandatory declaration
  levels and supported overbid behavior, and serialize privacy-safe proof and
  event summaries without exposing unrelated hands.
* Bound exact defender-open-play proof to five unresolved tricks. Open-card
  throwing uses bounded jack-only theoretical Schwarz exclusion; unsupported
  general claims and specific-trick claims remain outside this release.

### Historical shortened games

* Add versioned terminal events for declarer concession, defender concession,
  unanimously accepted declarer-card exposure, bounded defender open play, and
  open-card throwing (Issues #93 through #101).
* Replay exact legal prefixes, including an optional incomplete final trick,
  reconstruct exact remaining hands, preserve stable player identities, and
  round-trip canonical privacy-safe records and summaries.
* Add timed non-terminal defender-open-play and declarer-card-exposure
  continuations with exact public-hand visibility only after the event boundary.
* Keep continuations non-terminal. Version 1 supports at most one non-terminal
  event; continuation followed by a shortened terminal end remains unsupported,
  and terminal-event choices never become training targets.

### Decision, dataset, and opponent workflows

* Derive snapshot, review, and training-sample counts from the actual played-card
  count, including valid zero-decision and zero-sample shortened records.
* Preserve information-safe historical review, feature-generation version `1`,
  and target `actual_card_played`; no terminal-event target or event-specific
  profile field or signal is added.
* Apply existing dataset partition audits to shortened records while preserving
  strict temporal and partition safety.
* Aggregate one game of opponent-statistics weight per supported record and use
  actual decision counts plus participant-based target coverage in rolling
  opponent-policy evaluation.

### Ouvert-aware recommendation

* Apply declared-Ouvert public-hand constraints and exact declarer-hand
  reconciliation to live and historical Suit, Grand, Null Ouvert, and Null Hand
  Ouvert decisions (Issue #102).
* Reuse the exact public hand in Immediate Analysis, supported Multi-Step paths,
  Policy Comparison, flat review, and Historical Review, including coexistence
  with continuation public hands and information-safe matador evidence.
* Keep declaration and settlement rules unchanged. No Ouvert-specific tactical
  policy or perfect-information solver is added; current policies remain
  heuristic.

### Coherent hidden worlds

* Sample one immutable hidden execution root per Multi-Step path, preserve
  ownership through owner-aware transitions, and keep one fixed hypothetical
  skat (Issue #103).
* Give Policy Comparison paths independent copies of one shared root and use
  separated deterministic random streams for root sampling, opponent actions,
  and expected-value samples.
* Keep candidate selection on information-safe local state and serialize only
  privacy-safe coherence summaries. One coherent world is one hypothetical
  sample, not proof of the real deal; Immediate Analysis remains independently
  sampled and unsupported Multi-Step phases remain unchanged.

### Evidence-constrained hidden-card inference

* Constrain Suit, Grand, and Null hidden ownership using exact public ownership,
  legitimately known skat, attributed public play, and confirmed legal failure
  to follow the effective category (Issue #104).
* Count exact compatible labeled worlds and ownership marginals, then sample
  deterministic uniform compatible assignments with dynamic programming.
* Integrate common compatible worlds into Immediate Analysis, coherent roots
  into Multi-Step and Policy Comparison, and decision-time-safe evidence into
  Historical Review with strict privacy-safe output.
* Report `confirmed`, `high`, `medium`, and `low` concentration labels. Ownership
  estimates are conditional on uniformly weighted structurally compatible
  labeled assignments; confidence is not calibrated real-deal probability.
* Only confirmed structural evidence creates hard constraints. No behavioral,
  profile-weighted, Bayesian, or learned ownership model is added.

### Validation

* Validate 52 deterministic generated-output scenarios.
* Pass 3,558 pytest tests together with Ruff, input/example schema validation,
  and generated-output schema validation.

## v0.8.0

**Release theme: Explainable and time-safe opponent intelligence**

### Opponent statistics and profiles

* Add versioned external opponent-statistics records with stable player identity, required source provenance, all eight supported percentage statistics, and deterministic normalization to existing profile-rate semantics.
* Preserve optional exact historical role, win, Hand, and contract counts while keeping rounded external percentages distinguishable from exact evidence.
* Derive overall, declarer, and defender evidence scopes with heuristic confidence bands and explainable signals, classifications, reason codes, and preset recommendations.
* Distinguish actionable profile results from informational low-confidence, neutral, or insufficient-data results; profiles remain deterministic and rule-based rather than learned.

### Live and historical application

* Add explicit live left/right bindings by stable player ID, with independent relative-side behavior and actionable-only profile application.
* Preserve manual profile and explicit policy precedence over external profile presets.
* Add automatic historical participant matching with strict `captured_at < played_at` temporal safety and per-decision relative-side remapping.
* Preserve historical replay, settlement, deterministic seeds, and decision-time information boundaries when profiles are applied.

### Historical aggregation and export

* Aggregate exact opponent statistics from timestamped `training_dataset_input` games using canonical partition selection and an optional strict cutoff.
* Derive declarer and defender wins from final settlement and preserve exact role, win, Hand, and contract counts; both defenders receive a defender win when their side wins.
* Add versioned `historical_games` provenance and reusable standalone opponent-statistics export compatible with live bindings and time-safe historical matching.

### Behavioral evaluation

* Add rolling game-start as-of profiles using disjoint source and evaluation partition names and the fixed `simple_lowest` baseline.
* Evaluate the acting player's own observed card choice against ordered policy-equivalent preferred-card candidates.
* Report preferred-card and exact-card match metrics, actionable-only paired comparisons, coverage, and bounded breakdowns.
* Keep behavioral matching explicitly separate from strategic-quality, recommendation-quality, or optimal-play evaluation.

### Dataset partition policies

* Add optional `known_opponent` and `unseen_player` metadata while preserving backward compatibility for datasets without declared partition intent.
* Audit exact stable-player membership, pairwise and three-way overlap, and directed known-opponent coverage deterministically.
* Enforce strict player-disjoint partitions for declared unseen-player datasets while retaining rolling policy evaluation as a known-opponent workflow.

### Project scope and documentation

* Synchronize release-state documentation and record the approved pre-`v1.0.0`, post-`v1.0.0`, not-required, and unconditionally excluded product areas.
* Preserve the limitations of normal-play-only historical records, simplified claims and concessions, incomplete settlement nuance, heuristic opponent behavior, and bounded simulation and input interfaces.

### Validation

* Validate 33 deterministic generated-output scenarios.
* Pass 2,640 pytest tests together with Ruff, input/example schema validation, and generated-output schema validation.

## v0.7.0

**Release theme: Rules confidence and information-safe historical workflows**

### Rules and settlement

* Canonicalize Suit and Grand declaration dependencies and reject explicit contradictions while preserving the independent Null variants.
* Enforce official matador bounds of `1..11` for Suit and `1..4` for Grand.
* Align fixed three-player standings ties with SkWO 6.3.1 by using shared ranks for unresolved ties and optional externally executed lot order.
* Add bounded post-game settlement for impossible Null declarations while preserving the original Null contract and requiring an external Suit or Grand replacement selection.

### Historical-game workflows

* Add versioned complete normal-play historical-game records with full-deal, pickup or Hand, discard, ownership, play-order, follow-rule, winner, point, game-value, overbid, and settlement validation.
* Add 30 chronological information-safe pre-play snapshots without future-play, hidden-hand, or final-result leakage.
* Add bounded review of all 30 historical decisions through the existing immediate recommendation and post-game review logic, including deterministic seeds and reconciled game and player summaries.

### Training and evaluation data

* Add versioned training and evaluation dataset records with explicit provenance and `train`, `validation`, and `test` partitions.
* Deterministically derive 30 identity-safe decision samples per normal-play historical game using `actual_card_played` as the version-1 target.
* Reject duplicate record, game, and source identities and cross-partition game or source leakage.

### Project scope and documentation

* Establish the official November 2022 ISkO/SkWO publication as the normative rules source.
* Add an authoritative requirements traceability matrix and testable `v1.0.0` scope and completion gates.
* Synchronize release-state, roadmap, handoff, schema-validation, and user documentation for the `v0.7.0` baseline.

### Validation

* Validate 27 deterministic generated-output scenarios.
* Pass 2,302 pytest tests together with Ruff, input/example schema validation, and generated-output schema validation.

## v0.6.0

### List-aware review workflows

* Add fixed three-player list standings output for explicit list standings input.
* Expand list-performance examples and generated-output validation across aggregated totals, normalized contributions, local analysis results, and standings workflows.
* Improve post-game review examples and explanation coverage for mistakes, acceptable alternatives, Null objective reviews, and defender-perspective reviews.

### Opponent policy and settlement coverage

* Add controlled coverage for left/right opponent policy effects in immediate and multi-step paths.
* Use profile confidence in bounded opponent-policy behavior while preserving explicit policy override precedence.
* Audit settlement and overbid edge-case coverage, including supported Suit/Grand overbid settlement behavior.

## v0.5.0

### Late-game and history-heavy inputs

* Allow zero opponent hand sizes for late-game public inputs.
* Enforce stricter live completed-trick `winner_role` verifiability from concrete trick facts.
* Expand conservative matador inference from completed-trick ownership when `cards`, ordered `players`, and concrete declarer identity make ownership safe.

### Review wording and validation

* Add focused late-game and history-heavy workflow coverage, including generated-output validation.
* Improve objective-aware post-game review CLI wording, especially for Null contract-objective reviews.
* Expand regression coverage around late-game inputs, live winner metadata, matador inference, examples, CLI output, and post-game review behavior.

## v0.4.0

### Documentation and release-state updates

* Refresh roadmap and project handoff direction for the completed `v0.4.0` usability milestone.
* Add curated workflow walkthroughs for common CLI usage, JSON output, quiet automation, Multi-Step, policy comparison, side-specific opponent policies, post-game review, and schema validation.
* Clean stale metadata, player-profile, matador, and input/output documentation wording so docs match current behavior.
* Remove stale tracked generated output artifacts before release preparation.

### CLI usability and validation

* Improve CLI help text and command discoverability.
* Add optional `--quiet` mode for automation-friendly JSON-output runs.
* Expand generated-output validation for representative user-facing CLI workflows.
* Fix CLI `--comparison-only` behavior and sample-count maximum validation issues.

## v0.3.0

### Bug fixes

* Use Null contract-objective utility for live recommendations and expected-value ranking.
* Prevent advanced states from double-counting completed-trick points.
* Validate completed-trick ownership from cards, player order, game type, and concrete declarer identity when derivable.

### Validation and schemas

* Align runtime validation with documented schema bounds and public input shapes.
* Support `known_to_declarer` Skat visibility consistently in runtime validation, schemas, and output metadata.
* Reject malformed or out-of-bounds public inputs earlier and consistently.

### CLI and examples

* Return non-zero exit codes for invalid CLI usage and expected runtime/input failures.
* Send expected errors to `stderr`.
* Restore a valid documented default `python main.py` quick-start input.

### Documentation

* Document Null objective ranking, reusable final-state point representation, CLI exit codes, `known_to_declarer`, completed-trick ownership validation, and runtime validation parity.

### Internal compatibility

* Preserve public point fields as card-point metrics while using objective utility internally for Null ranking.
* Preserve explicit point fields as reusable state fields separate from completed-trick point contributions.
