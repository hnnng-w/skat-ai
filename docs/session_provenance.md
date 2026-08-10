# Session provenance

## Contract identity

Public Session Provenance has an independent version and scope:

```text
SESSION_FIELD_PROVENANCE_VERSION = 1
SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE = session_operation_value
SESSION_FIELD_PROVENANCE_REDACTION_POLICY = omit_engine_private_details
```

It is separate from internal `FIELD_PROVENANCE_VERSION = 1` and public Root
Result `PUBLIC_FIELD_PROVENANCE_VERSION = 1`; those contracts are unchanged.

## Opt-in sequence

Provenance is omitted by default. With `include_provenance=false`, no Session
ledger is built, no public redaction runs, and no coverage is recomputed.

With `include_provenance=true`, the wrapper:

1. Executes the requested internal operation exactly once.
2. Builds one complete internal ledger over the exact returned `value`.
3. Redacts engine-private entries, references, and dependencies.
4. Recomputes coverage against that unchanged returned value.
5. Requires complete post-redaction coverage.
6. Constructs one public attachment and bundle.
7. Validates the complete Result when output validation is enabled.

Provenance inspection never reruns creation, transition, Undo, correction,
export, Checkpoint work, lineage classification, persistence construction,
resume, Decision Observation, or Checkpoint Review Export. It covers neither
consumed inputs nor itself.

## Public values

`SessionProvenanceContextV1` contains exactly `operation`, `session_id`,
`revision`, `capture_mode`, and `phase`. Context is derived from the returned
State, the contained persistence State, or the retained source State where an
export, Checkpoint, or lineage value lacks Mode or phase.

The single attachment contains:

```text
attachment_name = session_operation_result
document_role = result
document_scope = session_operation_value
ledger
coverage_summary
session_context
```

The bundle contains `session_field_provenance_version`, `operation`,
`redaction_policy`, and exactly one `result` attachment. No consumed-input,
Projection, validator, or intermediate replay attachment is public.

## Coverage semantics

Every operation ledger has `status = complete`, and every serialized operation-
value leaf is covered exactly once. Uncovered paths, overlaps, orphaned entries,
orphaned exemptions, `legacy_untracked`, and legacy limitations are forbidden.
Only genuine `schema_constant` or `not_applicable` exemptions are permitted.

Operation coverage includes:

| Operation | Covered result semantics |
| --- | --- |
| Create | Identity, Players, Mode/local Player, revision zero, setup, empty Log, Validation, readiness |
| Apply | Command, source revision, status, Diagnostics, resulting or unchanged State, accepted record |
| Undo | Source State relationships, expected/target revisions, status, removed suffix, rebuilt State, Diagnostics |
| Correction | Replacement, original/replayed/discarded records, failed revision, State, status, Diagnostics |
| Position export | Source State/options reflected in the result, availability, Diagnostics, exact information-safe Request |
| Historical export | Ended Retrospective State facts, availability, Diagnostics, exact canonical Request |
| Checkpoint | Source revision/export, indexes, actor/seat/map, frozen Request |
| Lineage | Source State relationship to the frozen Checkpoint |
| Persistence | State, supplied Checkpoints, canonical order, State and content fingerprints |
| Resume | Supplied document, strict reconstruction, fingerprint/replay verification, recomputed lineage |
| Observation | Checkpoint, source State, lineage, status/reasons, and accepted observed Play revision/Card when available |
| Checkpoint review export | Frozen Request, observation, retrospective Card attachment, generated post-game-review Request, status, and Diagnostics |

Origins distinguish caller-supplied, validated-copy, rule-derived, structural-
inference, historical-replay, public-game-event, and retrospective-attachment
facts. Visibility distinguishes public, concrete-player `local_private`, and
`post_game_only` returned facts; `engine_private` is reserved for details removed
from the public sidecar. Availability uses `request_start`, `current_decision`,
`after_public_event`, `game_end`, and `offline_review` at their Session
boundaries. No field may depend on a later-availability field.

Source references contain stable identity only, never Command payloads or Cards.
Position provenance does not reveal private opponent ownership. Private values
appear only when already present in the returned operation value; the sidecar
does not widen access or duplicate those values.

For `observe_checkpoint` and `export_checkpoint_review`, the frozen decision-time
Request remains `current_decision`. The observed actual Card has origin
`retrospective_attachment` and is available only retrospectively. Review export
adds that Card to an exact copy of the frozen Request and does not admit later
private Session facts. See
[Session Decision observations](session_decision_observations.md).

## Redaction and exclusions

Public redaction removes engine-private entries, source references, and
dependencies, adds `private_dependencies_redacted` only when removal occurred,
and leaves the original internal ledger unchanged. Post-redaction coverage is
recomputed and must remain complete.

The sidecar contains no private replay Projection, hidden ownership or world,
proof state, cache, branch, principal variation, file or temporary path, host,
process ID, or removed private identifier/path.

Session Provenance is not a persistence fingerprint, authenticated authorship,
Confidence, probability, severity, quality, or calibration. Fingerprints remain
integrity identities. The separate Public Session File API has no provenance
option; its Result retains no path. Broader end-to-end field-enforcement work
remains open.
