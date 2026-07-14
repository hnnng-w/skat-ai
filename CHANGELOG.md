# Changelog

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
