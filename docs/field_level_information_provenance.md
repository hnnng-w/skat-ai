# Field-level information provenance

This document defines the internal version-1 field-level information provenance
language introduced by Issue #138.

Issue #138 defines the shared provenance language. Issue #143 applies it
internally to live Position Analysis, Issue #144 applies it to retrospective
Position Analysis, Historical Review, Historical Search Review, and Replay
Coaching, and Issue #145 applies it to Dataset, Preparation, Opponent, Profile,
historical-list, and comparison workflows. Issue #146 completes internal
Position and Historical Root Result provenance. Issue #147 exposes the bounded
public-safe Root Result and actual-artifact subset described in
[Public field provenance](public_field_provenance.md).

All seven Root workflows have complete internal Result ledgers. Public exposure
is opt-in and intentionally narrower than those internal bundles: it selects one
exact Root Result attachment plus attachments for artifacts actually returned,
not consumed inputs, decisions, or intermediate stages. Broader end-to-end
field-level enforcement remains separate work before `v1.0.0`.

Issue #139 adds internal Application orchestration version `1`; Issue #140 adds
the executable public facade; Issues #141 and #142 add packaged resources,
distributions, and installed/module/Legacy CLI parity.
Issue #143 adds internal live decision and Position Result attachments. Issue
#144 adds internal retained-stage retrospective attachments and selected
Position/Historical Result propagation. Issue #145 adds complete non-legacy Root
ledgers for the five remaining Root workflows while the same public boundary
remains unchanged. Issue #146 completes the Position and Historical Result
ledgers from retained workflow values. Issue #147 adds public API types, the
default-false execution option, Root `field_provenance`, strict Schema, and CLI
flag without changing the internal contract version. See
[Complete Result provenance](complete_result_provenance.md),
[Live analysis provenance](live_analysis_provenance.md),
[Retrospective review provenance](retrospective_review_provenance.md), and
[Dataset, list, and opponent provenance](dataset_list_and_opponent_provenance.md).

## Contract identity

The contract constants are:

```text
FIELD_PROVENANCE_VERSION = 1
FIELD_PROVENANCE_PATH_POLICY = rfc6901_json_pointer
FIELD_PROVENANCE_CONFIDENCE_POLICY = separate_contract
FIELD_PROVENANCE_PUBLIC_REDACTION_POLICY = omit_engine_private_details
```

The provenance version is independent of the Package version, public API
version, JSON-schema versions, and other Domain contract versions.

The implementation is split across:

* `field_provenance.py` for JSON Pointer helpers, immutable values, ledger and
  dependency validation, and serialization;
* `field_provenance_coverage.py` for JSON-leaf enumeration and document coverage
  auditing;
* `field_provenance_policy.py` for Information Use Context, use validation, and
  public redaction.

These modules are internal. They are not exported from `skat_ai`, `skat_ai.api`,
`skat_ai.api.v1`, or `skat_ai.errors`.

Issue #150's separate internal Session contracts reuse canonical RFC 6901 paths
for validation Diagnostics but do not produce or propagate field Provenance.
Session Command, State, transition, and export Provenance remains later work and
does not change this contract version.

## Sidecar design

Provenance is an immutable sidecar ledger for a JSON-compatible document. It
does not wrap every Domain value. One `FieldProvenanceEntry` identifies one
exact field or one current subtree. A `FieldProvenanceLedger` stores canonical
tuples of entries, exemptions, and limitations.

A ledger belongs to one specific document instance. It is not a reusable schema
rule. If fields are added, removed, or rearranged, callers must construct and
audit a new ledger for the changed document.

All new contract values are frozen, slotted, keyword-only dataclasses. Input
collections are copied to immutable tuples, canonicalized, and checked for
duplicates. Optional Player and source identities are stable non-empty,
non-padded strings.

## JSON Pointer paths

Every field path uses RFC 6901 JSON Pointer syntax. The Root pointer is the empty
string:

```text
""
/foo
/foo/bar
/items/0/name
/a~1b
/tilde~0value
```

`~0` encodes `~`, and `~1` encodes `/`. Invalid escapes, non-root paths without
a leading slash, non-canonical array indices, missing keys, out-of-range
indices, and traversal into scalars are rejected. Empty tokens and repeated or
trailing separators remain meaningful. `.` and `..` are ordinary object-key
tokens, not filesystem navigation.

The helpers escape, unescape, build, parse, and resolve pointers. Decode and
re-encode must reproduce the supplied path exactly.

## Coverage

Coverage kinds are:

```text
field
subtree
```

`field` covers one exact current JSON leaf. `subtree` covers every current leaf
at or below its pointer. A subtree may point to an object, array, scalar, or
empty container. Coverage is evaluated against the supplied document; it does
not make a future field implicitly covered in a different document.

A leaf may be covered exactly once by an entry or exemption. Exact/subtree and
subtree/subtree overlaps are rejected rather than resolved by precedence.

JSON leaf enumeration is deterministic:

* scalars and `null` are leaves;
* arrays are traversed by serialized index;
* object keys are traversed in canonical sorted order;
* empty objects and arrays are leaves at their own paths;
* a Root scalar or empty container uses `""`.

`FieldProvenanceCoverageSummary` reports:

```text
leaf_path_count
provenanced_path_count
exempted_path_count
uncovered_paths
orphaned_entry_paths
orphaned_exemption_paths
overlapping_paths
all_paths_accounted_for
provenance_complete
```

`all_paths_accounted_for` requires exactly one declaration for every leaf.
`provenance_complete` additionally requires a `complete` ledger, no legacy
exemption, and no orphaned declaration. A `partial_legacy` ledger can account
for every leaf while remaining intentionally incomplete. A `not_available`
ledger reports the document leaves as uncovered and remains a valid explicit
unavailable state.

## Origins and derivations

Origins answer where a field came from:

```text
caller_supplied
defaulted
validated_copy
public_game_event
historical_replay
external_source
rule_derived
structural_inference
compatible_world_aggregate
sampled_estimate
heuristic_analysis
simulation_derived
search_derived
retrospective_attachment
historical_aggregation
dataset_assignment
```

Derivations answer how it was produced:

```text
direct
validated
deterministic_rule
reconstruction
exact_aggregate
sampled_aggregate
heuristic
retrospective
```

Version 1 enforces these hard combinations:

| Origin | Required derivation |
| --- | --- |
| `rule_derived` | `deterministic_rule` |
| `dataset_assignment` | `deterministic_rule` |
| `retrospective_attachment` | `retrospective` |
| `sampled_estimate` | `sampled_aggregate` |
| `compatible_world_aggregate` | `exact_aggregate` or `sampled_aggregate` |

Other origin/derivation combinations remain available for later narrower
workflow validation.

## Visibility and availability

Visibility scopes are:

```text
public
local_private
declarer_private
defender_private
post_game_only
engine_private
```

`local_private` requires a concrete perspective Player ID. `post_game_only`
requires `game_end` or `offline_review` availability. `engine_private` covers
internal details such as concrete hidden worlds, private ownership, hypothetical
Skat contents, transposition tables, branches, principal variations, and random-
stream internals.

Availability boundaries are:

```text
request_start
current_decision
after_public_event
after_actual_play
game_end
offline_review
```

`current_decision` and `after_actual_play` require a non-negative decision
index. `after_public_event` requires a non-negative event index. Booleans are not
indexes. `request_start`, `game_end`, and `offline_review` require both indexes
to be null. A retrospective attachment can begin only after actual play, at game
end, or during offline review.

## Source references

`FieldProvenanceSourceReference` contains only:

```text
reference_type
reference_id
field_path
visibility
```

Reference types are:

```text
request
historical_game
historical_event
external_record
rule_contract
algorithm
aggregate
retrospective_observation
dataset_plan
```

`reference_id` is a stable identity. `field_path` is nullable and otherwise uses
the same JSON Pointer contract. A reference does not contain notes, source
values, card collections, or arbitrary Python objects. References are ordered
by type, ID, null-first field path, and visibility. Duplicate references are
rejected.

## Entries and dependencies

Each `FieldProvenanceEntry` contains:

```text
field_path
coverage_kind
origin
visibility
available_from
available_from_decision_index
available_from_event_index
derivation
source_references
dependency_paths
subject_player_id
perspective_player_id
```

Dependency paths identify other entry paths in the same ledger. They cannot
identify exemptions, missing entries, or the entry itself. Duplicate paths and
directed cycles are rejected. Serialization retains only direct dependencies;
it does not expand transitive closure.

The coarse temporal ranks are:

```text
request_start = 0
current_decision = 1
after_public_event = 1
after_actual_play = 2
game_end = 3
offline_review = 4
```

A derived entry cannot become available before a dependency. When both use the
same indexed kind, the derived index cannot precede the dependency index. Cross-
kind relationships at the same coarse rank remain available for later workflow-
specific validation.

## Exemptions and statuses

Exemption reasons are:

```text
legacy_untracked
schema_constant
not_applicable
```

An exemption has a field path, coverage kind, and reason. It uses the same
coverage rules as an entry and cannot overlap entry coverage.

Ledger statuses are:

```text
complete
partial_legacy
not_available
```

`complete` forbids legacy exemptions and legacy/unavailable limitations.
`partial_legacy` requires at least one `legacy_untracked` exemption and the
`legacy_untracked_fields` limitation. `not_available` has no entries or
exemptions and has only `provenance_not_available`.

Limitations are:

```text
legacy_untracked_fields
private_dependencies_redacted
provenance_not_available
```

`private_dependencies_redacted` can be added only by actual public redaction.
Limitations are unique and stored in canonical order.

## Information Use Context

`InformationUseContext` contains:

```text
workflow
stage
perspective_player_id
perspective_side
decision_index
event_index
```

Stages are:

```text
request_start
decision_time
after_actual_play
game_end
offline_review
engine_internal
```

Perspective sides are `declarer` and `defenders`. Context indexes are nullable
non-negative integers.

Visibility and availability are both required for use. Local-private fields
require the matching Player, declarer- and defender-private fields require the
matching side, post-game-only fields require `game_end`, `offline_review`, or
`engine_internal`, and engine-private fields require `engine_internal`. Indexed
availability requires a matching context index at or after the entry index.

`is_field_provenance_entry_available()` returns the policy result.
`validate_field_provenance_entry_use()` raises
`SkatAIInformationPolicyError` with the entry path and a generic message when
use is denied. It does not include source values or private identities.

## Public redaction and serialization

Public redaction is pure. It removes engine-private entries, engine-private
source references, and dependencies to removed entries. When anything is
removed, the result receives only the generic
`private_dependencies_redacted` limitation. Removed paths, reference IDs, and
field-specific private counts are not retained. The source ledger is unchanged.

Internal serializers are deterministic and explicit about nullable fields. The
public-safe ledger serializer rejects any unredacted engine-private entry or
reference, and rejects unresolved dependency paths, with
`SkatAISerializationError`. It does not silently redact; callers with engine-
private details must invoke the redaction helper first. An already-safe ledger
can be serialized directly.

Issue #147 reuses this redaction and serialization behavior for the strict public
`field_provenance.schema.json` contract. Public conversion redacts first and then
recomputes coverage against the exact Root Result without `field_provenance` or
the exact actual artifact. It fails if complete coverage is not preserved. See
[Public field provenance](public_field_provenance.md).

## Confidence separation

Provenance answers where a value came from.

Confidence answers how strongly an inference is supported.

The provenance contracts therefore contain no Confidence, probability,
severity, quality, or calibration field. Existing Hidden-card Confidence and
Replay Coaching evidence semantics remain unchanged. A confirmed inference may
still have derived provenance, and a direct source may have a separate
uncertainty contract.

## Workflow mapping guidance

The shared vocabulary supports these mappings without changing the existing
specialized contracts:

| Existing or future field | Intended shared provenance |
| --- | --- |
| Caller input | `caller_supplied` |
| Validated immutable copy | `validated_copy` |
| Public-hand constraint | `public_game_event`, `public` |
| Historical visible state | `historical_replay`, `current_decision` |
| Historical actual card | `retrospective_attachment`, `after_actual_play` |
| Settlement or list contribution | `rule_derived`, `deterministic_rule` |
| Compatible-world aggregate | `compatible_world_aggregate`, exact or sampled aggregate |
| Replay Coaching recommendation | `search_derived` or `heuristic_analysis` |
| Training source field | `external_source` |
| Generated Dataset partition | `dataset_assignment`, `deterministic_rule` |

`Information Policy`, Historical Snapshot cutoffs, Replay Coaching information
policy and evidence, public-hand sources, Hidden-card evidence, Confidence and
specialized provenance status, Training Provenance, Opponent source provenance,
Dataset Plan fingerprints, and historical-list identities remain authoritative
and unchanged.

## Remaining work

The internal Application boundary carries live and retrospective Position,
Historical Review, Historical Search Review, Replay Coaching, Dataset,
Preparation, Opponent, Profile, list, comparison, and complete Result
provenance. Every Root Result ledger is complete and non-legacy. Issue #147
publishes only one redacted Root Result ledger plus actual-artifact ledgers.

Broader adversarial enforcement outside implemented Application boundaries and
complete field-level enforcement across every load, decision, intermediate, and
serialization boundary remain open before `v1.0.0`. Confidence integration is
not part of the provenance contract. Session Provenance propagation also remains
open after the Issue #150 contract-only foundation.
