# Complete Result provenance

Issue #146 completes the remaining internal Root Result-ledger boundary for
Position Analysis and Historical Game execution. It uses the unchanged shared
field-provenance language and Application sidecar contracts.

This propagation is internal. It adds no public API option, Result field,
artifact, Root JSON field, Schema, CLI option or section, example, generated
scenario, or generated output. Package version remains `0.12.0`.

## Contract identity

The focused propagation version is:

```text
COMPLETE_RESULT_PROVENANCE_VERSION = 1
```

It is independent of Package, Public API, Application orchestration, shared
field-provenance, Domain, and JSON Schema versions. The constant is not exported
from any public namespace.

The focused implementation modules are:

* `position_result_provenance.py`;
* `historical_result_provenance.py`;
* `settlement_result_provenance.py`.

## Complete ledgers

Both exact Root Result attachments now use:

```text
status = complete
limitations = ()
```

They contain no `legacy_untracked` exemption or
`legacy_untracked_fields` limitation. Every current Result leaf is covered
exactly once. Unknown Root or summary branches are rejected rather than assigned
a generic fallback.

The attachment names remain:

```text
position_result
historical_game_result
```

Each Result attachment remains last in canonical Application bundle order.

## Position Result

The complete Position ledger preserves the existing entries for normalized
Position and settings, Information Policy, Immediate recommendation, Search,
post-game review, Hidden-card inference, Multi-Step, Policy Comparison, external
Profile application, and continuation output.

Issue #146 adds branch-specific mappings for:

* validated, defaulted, canonically implied, or structurally inferred Game
  Declaration fields;
* retained Suit, Grand, Null, Hand, Ouvert, announcement, Matador, Game Value,
  Overbid, and impossible-Null values;
* explicit and completed-trick score values;
* raw and game-ending-adjusted Game Results;
* final Settlement;
* single-game Performance Rating;
* all three retained list Performance input modes;
* fixed-three-player standings, shared ranks, and external lot state;
* declarer concession, defender concession, accepted declarer-card exposure,
  bounded defender open play, and open-card throw;
* declarer-exposure and defender-open-play continuation.

The retained public values are not recalculated. Structured terminal branches
reference stable normative cases. Continuations remain non-adjudicating and do
not depend on Game Result or Settlement. External lot input can affect only tied
ordering, ranks, and lot state; it does not feed Player metrics.

## Historical Result

Every Historical Application execution now has a non-null internal provenance
bundle. Base execution without Snapshot, Review, Search Review, or Replay
Coaching options contains only the complete `historical_game_result` attachment.
Selected retrospective attachments remain unchanged and precede that Result.

The complete Historical ledger covers:

* schema, Game identity, optional timestamp, stable Players and seats;
* all post-game-only initial hands, Skat, and discard or Hand handling;
* canonical declaration and complete-deal Matador inference;
* exact supplied play or shortened prefix;
* an optional incomplete final trick without a winner;
* replay-derived completed tricks, deterministic winners, and trick points;
* observed, unresolved, assigned, and final point accounting;
* raw and adjudicated Result facts, Game Value, Overbid, and Settlement;
* both timed continuation events and their exact public-hand boundaries;
* all five supported terminal endings and their public proof metadata;
* the existing Snapshot, Immediate Review, Search Review, Replay Coaching,
  Outcome Context, and historical Profile application branches.

Historical actual plays become available in exact chronology. A completed trick
depends only on its matching supplied trick and contract rules, never on a later
trick. Full private deal facts remain post-game-only and never become
decision-time evidence. A continuation event has no immediate Result or
Settlement dependency; later terminal adjudication remains a separate game-end
stage.

## Dependency direction

Focused validators enforce these forward-only chains:

```text
declaration -> Game Value -> Overbid

play -> score -> raw Result

raw Result + approved ending -> adjusted Result

adjusted Result + Game Value + Overbid -> Settlement

approved game outcome -> Performance -> list standings

Historical record -> tricks -> points -> Result -> Value/Overbid -> Settlement
```

Settlement cannot feed Value or Overbid. Search, Review, Coaching, Rating, list,
or standings output cannot feed Declaration, score, Game Result, or Settlement.
Historical Review and Coaching branches cannot feed the canonical Historical
record, replay, points, Result, Value, Overbid, terminal adjudication, or
Settlement.

Availability follows the shared contract: request input starts at
`request_start`, live facts at `current_decision`, Historical actual play at
`after_actual_play`, continuation evidence at its validated public-event
boundary, final outcome and Settlement at `game_end`, and Performance/list
reporting at `offline_review`.

## Privacy and redaction

Publicly retained proof summaries remain ordinary post-game Result fields. Their
private proof and exact ownership sources are opaque engine-private references.
The shared redaction helper removes those references and dependencies, adds only
`private_dependencies_redacted`, and leaves the original complete ledger
unchanged.

Redacted Result ledgers retain no private proof hand, exact private Search state,
cache, branch, Principal Variation, hidden ownership assignment, derived private
seed, private sentinel, removed path, or removed reference identity.

## Execution and compatibility

Provenance consumes only the original request and already retained Result. It
does not add parser, Declaration, Value, Overbid, score, Result, Settlement,
Rating, list, ending-adjudication, exact-proof, Historical replay, Search,
Review, or Coaching calls. Equal retained inputs and Results produce equal
ledgers and attachment order.

Public Python API and all CLI adapters continue to ignore
`ApplicationExecutionResult.provenance`. The exact Root JSON, 61 Schema
resources, examples, 70 generated-output scenarios, Wheel, and sdist contracts
remain unchanged.

## Remaining work

The following remain open:

* any additive public provenance API contract;
* public provenance Schemas, Root fields, and artifacts;
* CLI presentation or export;
* broader end-to-end information-policy enforcement outside the implemented
  Application boundaries.
