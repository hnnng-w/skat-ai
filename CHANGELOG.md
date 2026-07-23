# Changelog

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
