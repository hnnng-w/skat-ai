# v1 information provenance enforcement

Issue #202 completes the internal version-1 field-level information-provenance
lifecycle for all seven Root workflows. It makes P-10 and P-13 `satisfied` and
closes blocker B-02
without widening public Provenance or changing a public version, field, default,
Schema, example, generated scenario, workflow, Console Script, or Package
version.

## Contract identity

The strict internal lifecycle is:

```text
V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION = 1

loaded_request
validated_consumed_input
retained_stage_linkage
final_serialization
```

The version is independent of Package `0.17.0`, Public API contract version `1`,
field-provenance version `1`, public field-provenance version `1`, Application
orchestration version `1`, and every Root Schema version.

The implementation is split across:

* `v1_information_provenance_sources.py`, which builds exact immutable consumed
  Request, effective Application-option, and optional injected Opponent
  Statistics sources;
* `v1_information_provenance_enforcement.py`, which validates complete source
  coverage and Information Use Context before analysis and closes retained-stage
  source references afterward;
* `v1_information_provenance_serialization.py`, which reconciles the exact Root
  Result and artifacts actually returned and retains the immutable checkpoint.

## Exact consumed sources

Each invocation builds its source collection exactly once after the Root Request
has been verified and before its workflow handler runs. The collection contains:

* `v1_source/request`, the exact consumed Root Request document;
* `v1_source/application_options`, the effective workflow, execution mode,
  workflow options, wrapper-level and workflow-option caller-presence names,
  validation/provenance settings, input reference, and external-document
  presence/reference;
* `v1_source/external_opponent_statistics` only when an Opponent Statistics
  document is injected.

The option source distinguishes omitted defaults from explicitly supplied values,
including explicitly supplied default values. Public `ExecutionOptionsV1`
retains this distinction privately while preserving its exact five public
dataclass fields, equality, immutable JSON values, and `to_dict()` output. Root
CLI parsing retains the exact supplied option names as private transport metadata,
so effective CLI defaults are not misclassified as caller-supplied values.

Every source attachment has complete exact JSON-leaf coverage, no legacy
exemption, and one Information Use Context. Live local hands are
`local_private`; retrospective full hands, Skat, discards, and exact shortened
remaining hands are `post_game_only` from `game_end`; actual plays are indexed
`after_actual_play`; structured Historical continuation events are indexed
`after_public_event`; injected external records are `engine_private`.

Invocation-local bindings connect stable retained reference identities to exact
source documents. Validation reconstructs and compares those bindings and the
canonical source ledgers, so stale or substituted documents, identities,
visibility, timing, origins, or contexts are rejected.

## Pre-analysis enforcement

Before dispatch, the source documents, canonical ledgers, contexts, bindings,
and caller-presence metadata are reconstructed from and compared with the exact
immutable invocation. Every source attachment must remain complete for its exact
document, and every entry is then checked against its independently retained
Information Use Context. A stale source raises an invariant error and a denied
value raises the existing non-disclosing information-policy error before any
Root handler is called.

The check covers all seven workflows:

1. `position_analysis`
2. `historical_game`
3. `training_dataset`
4. `training_dataset_preparation`
5. `opponent_statistics`
6. `fixed_three_player_historical_list`
7. `fixed_three_player_historical_list_comparison`

## Retained-stage linkage

The workflow executes once and retains its existing Application provenance
bundle. Issue #202 does not replay a Snapshot, rerun analysis, reconstruct a
second Result, or invoke a workflow-specific helper again.

Every retained attachment must remain complete and match the invocation
workflow. Each source reference must be authorized for that workflow and exact
invocation. Loaded Request, option, external-record, historical-game, list, and
Dataset identities resolve through exact bindings. Rule, algorithm, aggregate,
event, retrospective-observation, and Dataset-plan identities are limited to
their supported workflow families and invocation data.

References cannot widen an engine-private source. Direct, copied, defaulted, and
external values with exact field paths are resolved through RFC 6901 and compared
with the retained value. Pathless direct copies must resolve the retained leaf
path against their exact bound source; normalized or reconstructed values use
derived provenance instead of a fabricated exact-copy claim. Exact source-ledger
entries also prevent a directly retained value from widening source visibility
or moving before its source availability boundary or index. Aggregate
perspective and Decision indexes are derived from the attached document or its
independently retained context, never from the ledger entry under validation.

## Final serialization checkpoint

Immediately before `ApplicationExecutionResult` returns, the lifecycle:

* selects the one exact complete Root Result attachment for the workflow;
* requires equal JSON key order, value types, arrays, and scalar values between
  that attachment and the current Result document;
* requires provenance for exactly the artifacts actually returned;
* rejects duplicate, unexpected, missing, reordered, or mutated Results and
  artifacts;
* freezes and reconciles the complete Result envelope, including API contract
  version, workflow identity, document, and warnings;
* retains one immutable
  `V1InformationProvenanceSerializationCheckpoint` containing the exact sources,
  linked attachment names, complete Result envelope, Result document, artifact
  documents, four ordered stages, and one count for each stage.

Public conversion revalidates this checkpoint without executing product work.

## Adversarial rejection

Focused evidence rejects:

* non-version-1 lifecycle values;
* incomplete, orphaned, overlapping, or legacy source and retained coverage;
* source-document, source-ledger, source-binding, Result-envelope, Result-value,
  key-order, and artifact mutation;
* unknown, cross-workflow, missing-path, pathless-copy mutation, or
  visibility-widening references;
* self-authorized private perspectives or future Decision indexes;
* premature event, actual-play, post-game, engine-private, or exact-source use;
* missing, self, cyclic, or temporally inverted dependencies;
* missing or mismatched actual-artifact provenance.

The focused suites are:

* `tests/test_v1_input_provenance.py`
* `tests/test_v1_provenance_enforcement.py`
* `tests/test_v1_provenance_serialization.py`
* `tests/test_v1_provenance_adversarial.py`

Existing Application, live, retrospective, Dataset/list/opponent, complete
Result, public-redaction, Public API, CLI, Session, and Match tests provide the
transport and workflow integration evidence.

## Public boundary

Public field-provenance version `1` remains omitted by default. Opt-in conversion
still exposes only:

* one redacted mapped Root Result under scope
  `root_result_without_field_provenance`; and
* provenance for artifacts actually returned under scope `artifact_document`.

Consumed-input, Decision, intermediate-stage, unredacted, exact hidden-world,
private proof, source-binding, and lifecycle-checkpoint values remain internal.
Redaction still removes engine-private entries and references and recomputes
complete coverage over the exact public document.

Root Provenance remains separate from Public Session returned-value Provenance,
Confidence, Match/Corpus identities and persistence fingerprints, Strategy
Teacher fingerprints, Tactical identities, and Dataset-v2 fingerprints.

Issue #202 changes no Package/API/workflow/Console-Script/Schema/example/
generated-scenario count. The current baseline remains Package `0.17.0`, seven
Root workflows, one Console Script, 71 authoritative and packaged Schemas, six
Session examples, 98 generated outputs, and ten private Corpus downloads.
