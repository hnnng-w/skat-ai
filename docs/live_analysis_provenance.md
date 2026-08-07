# Live analysis provenance

Issue #143 adds internal field-level provenance propagation and enforcement for
live Position Analysis. The propagation versions are:

```text
APPLICATION_PROVENANCE_VERSION = 1
LIVE_ANALYSIS_PROVENANCE_VERSION = 1
```

These versions are independent of the Package, public API, Application
orchestration, JSON Schema, Search, and shared field-provenance versions.

## Application attachments

`ApplicationProvenanceAttachment` retains one stable name, a consumed-input or
Result role, an immutable JSON document, its `FieldProvenanceLedger`, the exact
matching Coverage Summary, and its Information Use Context.
`ApplicationProvenanceBundle` retains the Application provenance version, the
Position workflow identity, and canonical unique attachments.

`ApplicationExecutionResult.provenance` is optional and defaults to `None`. A
live Position Application execution attaches one bundle. Retrospective Position
Analysis and every other Application workflow retain `None`.

The canonical live attachment order is:

1. `flat_decision`
2. `multi_step_decision/<decision-index>`
3. `policy_comparison_decision/<policy-index>/<policy>/<decision-index>`
4. `position_result`

## Decision information

Every local card-selection boundary first constructs and freezes one complete
decision-information document. It contains only:

* the serialized public/local Game State;
* the local hand;
* locally visible Skat cards;
* public current-trick, attributed play, completed-trick, point, and turn facts;
* public opponent hand-size counts;
* rule-authorized Public-hand Constraints;
* Strategic Metadata and Game Declaration;
* the effective recommendation or card-selection method and seed-free settings.

It never contains concrete hidden opponent hands, coherent-world ownership,
selected Compatible Worlds, hypothetical private Skat cards, Exact Search
States, caches, branches, principal variations, private random streams, or
derived seeds. A hidden Skat is represented by an empty state value and a
non-legacy `not_applicable` coverage exemption, not by concrete card identity.

Every decision ledger has status `complete`. Coverage is validated against the
frozen document, then every normal entry is validated against a decision-time
`InformationUseContext` with local perspective identity `me`. Analysis does not
execute if any entry is unavailable in that context.

## Visibility mapping

| Information | Origin | Visibility | Availability |
| --- | --- | --- | --- |
| Local hand | `validated_copy` | `local_private` | Current decision |
| Locally visible Skat | `validated_copy` | `local_private` | Current decision |
| Public trick, play, points, turn, and counts | `public_game_event` | `public` | Current decision |
| Authorized Public-hand Constraint | `public_game_event` | `public` | Current decision |
| Strategic Metadata and declaration | `validated_copy` | `public` | Current decision |
| Effective seed-free selection settings | `validated_copy` | `public` | Current decision |

A defender never receives declarer-private known Skat cards. Declared Ouvert,
declarer-card-exposure continuation, and defender-open-play continuation add only
their existing exact all-player Public-hand Constraints. Defender-open-play
adjudication proof hands remain private and produce no live provenance bundle.

## Immediate and inference

Immediate candidate reports, strategic summaries, and recommendations use
`heuristic_analysis` provenance. Their dependencies are restricted to the local
visible position, legal cards, effective settings, and authorized public
constraints. They do not reference sampled hidden hands.

The existing Hidden-card inference summary uses `structural_inference`
provenance and depends only on visible state and authorized public evidence. Its
existing Confidence and specialized `provenance_status` fields remain unchanged.
No provenance value identifies actual-world ownership.

## Search and auto

Search provenance is built from the already executed `BoundedSearchResult`; no
additional Search is run. Single-exact and all-compatible completed aggregates
use `compatible_world_aggregate` with `exact_aggregate`. Sampled compatible
coverage uses `sampled_aggregate`. Unavailable and valid zero-completion fields
remain direct `search_derived` status evidence.

Requested budget, consumed budget, status, stop reason, coverage, solution claim,
candidate aggregates, recommendation, and fallback fields are all covered.
Candidate rank dependencies include every aggregate ranking metric, candidate
card, and game type used by deterministic tie-breaking. Search recommendation
wording depends on status, stop reason, coverage, consumed world counts, and the
selected candidate aggregates it renders.
Search provenance contains no World ID, ownership map, private hand,
hypothetical Skat identity, derived seed, transposition state, or principal
variation. Complete, partial, timeout, and unavailable Results are supported.

Strict Search recommendations are Search-derived and never receive Immediate
fallback provenance. Search-first `auto` is Search-derived when Search selects a
card. Auto fallback remains Immediate heuristic provenance while retaining the
valid no-recommendation Search evidence as a dependency. If neither Search nor
Immediate can recommend a card, the combined `auto` reason and summary remain
Immediate heuristic provenance with the unsuccessful Search status as a
dependency.

## Multi-Step and Policy Comparison

Multi-Step accepts an optional internal decision-provenance hook. Application
execution first enforces the flat live-decision attachment before root inference
or simulation. The per-decision hook then runs after public opponent preparation
and before prepared-state Hidden-card inference, Search, or legacy card
selection. It receives only the prepared public/local state, public hand counts
and constraints, Strategic Metadata, declaration, selection method, and
seed-free settings. Direct Domain calls remain compatible when no hook is
supplied.

Live Position Application execution supplies the hook. Every attempted local
decision therefore produces one complete attachment, including a Search-aware
decision that stops without a recommendation. An unsupported turn phase creates
no decision attachment because no local selection is reached.

Policy Comparison threads the same hook through each policy path. Attachment
identity uses canonical policy order, not score-sorted Result order. The shared
private root and independent path copies never reach the hook. Existing one-root,
one-copy-per-policy execution and call counts are unchanged.

## Position Result ledger

The final `position_result` attachment retains the exact current Root Position
output and an all-leaf ledger with:

```text
status = partial_legacy
limitation = legacy_untracked_fields
```

Every leaf is accounted for exactly once. Critical live paths use normal
provenance entries, including Position and local visibility, settings, effective
policies, Analysis Metadata, Information Policy, declaration, legal cards,
Immediate analysis, recommendation routing, Search, Hidden-card inference,
external profile application, Multi-Step, Policy Comparison, and live
continuation summaries.

Explicit legacy exemptions are limited to existing retrospective, settlement,
rating, list, and terminal branches. Unknown top-level Position Result fields,
uncovered leaves, orphaned declarations, and overlapping coverage are rejected.

External Opponent Statistics are not embedded in provenance. Existing profile
application output retains the supplied opaque reference, while internal source
references are engine-private and removable through the shared public-redaction
helper. Manual profile, Profile Preset, and explicit policy precedence is
unchanged.

## Determinism and compatibility

Decision documents, ledgers, Coverage Summaries, attachment names, and bundle
ordering are deterministic for equal visible information. They are independent
of coherent private ownership and later path mutation. Provenance construction
does not add calls to Immediate recommendation, Search, Hidden-card inference,
Multi-Step, Policy Comparison, or external profile construction.

The bundle is internal. The public Python facade and all CLI transports
intentionally ignore it. There is no public export, execution option, Result
field, artifact, Root JSON field, Schema, example, generated scenario, or CLI
section for Provenance.

## Remaining work

The following remain open:

* retrospective Position, Historical Review, and Replay Coaching provenance;
* Dataset, list, Opponent Statistics, and other non-Position workflow provenance;
* complete non-legacy provenance for retrospective, settlement, rating, list,
  and terminal Position Result branches;
* public API and Root-output integration, schemas, artifacts, and CLI
  presentation.
