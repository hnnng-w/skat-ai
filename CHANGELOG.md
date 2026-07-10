# Changelog

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
