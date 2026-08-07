# Application orchestration

This document defines the internal Application orchestration foundation
introduced by Issue #139. Its contract version is:

```text
APPLICATION_ORCHESTRATION_VERSION = 1
APPLICATION_INPUT_REFERENCE_POLICY = caller_supplied
```

The version is independent of the Package version, public API contract version,
JSON-schema versions, field-provenance version, and other Domain contract
versions.

The Application layer executes existing workflows from already loaded in-memory
Root documents. It remains an internal boundary under `skat_ai.application`.
Issue #140 adds the stable `skat_ai.api.v1` facade over this boundary without
making Application contracts public.
Issue #141 packages that facade and its private Schema resources without moving
build, resource, metadata, or installation concerns into Application.
Issue #142 adds Package-owned installed and module CLI transports that construct
these same Application options and execute this dispatcher directly.
Issue #143 adds an internal optional live Position provenance sidecar without
changing the orchestration version or public Result document.
Issue #144 extends that sidecar through retrospective Position Analysis,
Historical Review, Historical Search Review, and Replay Coaching without
changing the orchestration version or public Result document.
Issue #145 extends it through all five Training Dataset operations, automatic
Dataset Preparation, Opponent Statistics and Profiles, historical-list
aggregation, and independent-list comparison under the same boundary.

## Contracts

The main contract values are frozen, slotted, keyword-only dataclasses:

* `ApplicationInvocation` contains orchestration version `1`, one immutable
  `RequestDocumentV1`, a non-empty caller-supplied `input_reference`, matching
  workflow options, and optional injected external documents.
* `ApplicationExecutionOptions` contains at most the options for Position
  Analysis, Historical Game, or Training Dataset execution. The four simpler
  Root workflows require no workflow-specific option object.
* `ApplicationExternalDocuments` contains an optional Opponent Statistics Root
  document and its non-empty caller-supplied reference. The document and
  reference must be supplied together.
* `ApplicationExecutionResult` contains orchestration version `1`, one immutable
  `ResultDocumentV1`, an ordered immutable tuple of auxiliary artifacts, and an
  optional internal `ApplicationProvenanceBundle`.
* `ApplicationArtifact` contains one recognized artifact name and one immutable
  JSON object document.
* `ApplicationProvenanceAttachment` and `ApplicationProvenanceBundle` retain
  immutable matching live, retrospective, Dataset, Preparation, Opponent,
  Profile, list, comparison, and Root Result sidecars under Application
  provenance version `1`.

Construction defensively copies JSON documents and option sequences. Stored
objects use immutable mappings and stored arrays use tuples. Artifact and
external-document conversion methods return fresh mutable JSON-compatible
copies. Non-string object keys, arbitrary Python objects, and non-finite numbers
are rejected.

The `input_reference` is descriptive caller data. Application execution does not
open or resolve it. Existing result documents continue to place that exact value
in `input_file`, preserving legacy JSON parity without claiming that it is a
filesystem path or provenance ledger.

## Workflow options

`PositionAnalysisApplicationOptions` represents non-transport Position settings,
including Immediate sample and seed overrides, opponent-policy overrides,
Profile Preset opt-in and stable opponent bindings, Multi-Step settings, and
Policy Comparison selection.

`HistoricalGameApplicationOptions` represents snapshot, Immediate Review,
Historical Search Review, and Replay Coaching selection; Search and Immediate
settings; and injected-profile policy overrides.

`TrainingDatasetApplicationOptions` selects exactly one Training Dataset
operation and its operation-specific partition, Search, aggregation, or export
settings. Options are validated against the selected Root workflow before
dispatch. Settings for one workflow cannot be attached to another workflow.

## Seven handlers

The generic dispatcher has one handler for every canonical `WorkflowV1` value:

| Workflow | Application handler result |
| --- | --- |
| `position_analysis` | Existing Position Analysis result, optionally including Multi-Step, Policy Comparison, and live injected-profile application. |
| `historical_game` | Existing Historical Game result, optionally including snapshots, Immediate Review, Search Review, Replay Coaching, and time-safe injected-profile application. |
| `training_dataset` | Exactly one of the five Training Dataset operation results. |
| `training_dataset_preparation` | Existing automatic Training Dataset preparation result. |
| `opponent_statistics` | Existing normalized Opponent Statistics result. |
| `fixed_three_player_historical_list` | Existing single-list aggregation result. |
| `fixed_three_player_historical_list_comparison` | Existing independent-list comparison result. |

`build_application_invocation()` derives the workflow with the existing
`get_input_workflow()` contract, wraps the Root document in
`RequestDocumentV1`, and supplies default options where required.
`validate_application_invocation()` enforces workflow and option compatibility.
`execute_application_invocation()` validates once, dispatches exactly one
handler, and returns a `ResultDocumentV1` with the same workflow identity and an
empty warning tuple.

Normal workflow states such as an unavailable Dataset Preparation Plan remain
successful result documents. The Application layer does not redefine existing
workflow result semantics or schemas.

## Training Dataset operations

The Training Dataset handler supports exactly these isolated operations:

| Operation | Result field |
| --- | --- |
| `summary` | `training_dataset_summary` |
| `partition_audit` | `dataset_partition_audit_summary` |
| `rolling_opponent_policy_evaluation` | `rolling_opponent_policy_evaluation_summary` |
| `bounded_search_evaluation` | `bounded_search_evaluation_summary` |
| `historical_opponent_statistics_aggregation` | `historical_opponent_statistics_aggregation_summary` |

Each result also retains `input_file`; no unselected Training Dataset operation
is executed or attached.

## External documents and artifacts

Opponent Statistics may be injected only into Position Analysis and Historical
Game invocations. The Application layer receives the already loaded Root
document and an opaque descriptive reference. Position Analysis still requires
valid live stable-ID bindings and effective Profile Preset opt-in. Historical
Game injection still requires Immediate Historical Review, effective Profile
Preset opt-in, and the existing strict pre-game temporal checks.

Historical Opponent Statistics aggregation can optionally return one auxiliary
artifact:

```text
name = opponent_statistics_input
```

The artifact is the existing reusable export document. It is deliberately kept
outside the primary result document and has no output path. A transport adapter
decides whether and where to write it. Duplicate or unknown artifact names are
rejected.

## No-I/O boundary

Application execution is generic and transport-free. Modules under
`src/skat_ai/application/` do not parse command-line arguments, open input or
output paths, print human-readable output, or select output destinations.
Callers must provide loaded Root and external documents and consume the returned
result and artifacts.

The Application layer still performs existing semantic parsing, validation,
Domain construction, workflow execution, and deterministic serialization. No-I/O
means transport I/O is outside this layer; it does not mean validation-free or
computation-free execution.

## CLI boundary

The Package-owned CLI owns argument parsing, file loading, output writing, human-
readable presentation, Exit Codes, and expected CLI-error handling. Installed
`skat-ai` and module `python -m skat_ai` use it directly. Repository-root
`main.py` remains a thin Legacy facade with its existing wrapper names.

Those wrappers now translate CLI selections into immutable Application options,
inject already loaded Opponent Statistics where requested, execute the generic
dispatcher, thaw the result and artifacts for transport, and preserve established
JSON and human-readable behavior. Internal dependency seams retain established
Root-module monkeypatch behavior. Focused parity coverage compares Application
Position output with the legacy wrapper output.

The installed CLI remains a transport interface and does not make `main.py` or
CLI functions part of the Public Python API.

## Public API and provenance boundaries

Issue #140 exposes these additive public facade functions:

```text
parse_request
execute
execute_document
serialize_result
```

The facade schema-validates and immutably wraps Root input, translates direct
public workflow options into these internal option contracts, constructs one
Invocation, and executes this dispatcher exactly once. It converts the existing
Result and artifacts into public contracts without changing the Root document.
Direct imports from `skat_ai.application` remain internal and have no public API
compatibility guarantee. The public boundary preserves `SkatAIError`, translates
raw `ValueError` and `OSError`, and does not broadly migrate Domain exceptions.
No workflow-specific public helper is added.

Live Position Application execution constructs and enforces complete decision
ledgers before flat, Multi-Step, and Policy Comparison local selections, then
attaches an all-leaf partial-legacy ledger for the exact Position Result.
Retrospective Position execution separates pre-actual input and analysis from
actual-card assessment. Historical execution attaches decision-time inputs,
retained Immediate/Search analysis, post-actual assessment, requested aggregate
summaries, Replay Coaching stages, and an all-leaf partial-legacy Historical
Result ledger. Dataset, Preparation, Opponent, list, and comparison execution
attach complete non-legacy input, retained-stage, aggregate, and exact Root
Result ledgers. A Historical execution with no selected review operation retains
`provenance=None`.
The facade and CLI intentionally ignore the internal bundle, so all public
provenance output remains open. See
[Live analysis provenance](live_analysis_provenance.md),
[Retrospective review provenance](retrospective_review_provenance.md), and
[Dataset, list, and opponent provenance](dataset_list_and_opponent_provenance.md).

Packaging does not change this boundary. Clean Wheel and sdist smoke tests call
the public facade, which delegates to the same Application handlers and preserves
the same Root Results and artifacts. Application still performs no Package
Resource discovery and imports no repository-root `main.py`.
The same clean environments also compare installed/module CLI Root JSON with the
Public API result.

## Remaining work

The following remain separate follow-up scopes:

* public error translation across existing Domain failures;
* complete non-legacy Position and Historical Result provenance;
* all public provenance schemas, API exposure, Root output integration, and CLI
  presentation.

Package and distribution metadata, private Package Resource schemas, `py.typed`,
Package `__version__`, and clean Wheel/sdist validation are implemented by Issue
#141. Installed and module entry points are implemented by Issue #142. See
[Installed CLI](installed_cli.md) and
[Packaging and distribution](packaging_and_distribution.md).
