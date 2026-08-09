# Public API contracts

This document defines the public Python contract introduced by Issue #137,
extended with executable facade contracts by Issue #140, and made available from
built distributions by Issue #141. The API contract version is `1`, and its
stable versioned namespace is:

```text
skat_ai.api.v1
```

The public facade parses and executes all seven Root workflows through the Issue
#139 internal Application layer. Packaged schemas support Editable, Wheel, and
sdist installations without adding a workflow-specific helper or public schema
API. Issue #142 adds Package CLI entry points as a separate transport contract;
it adds no public API export. Issue #138 remains a separate internal field-
provenance contract foundation, and Issue #143 applies it to internal live
Position execution. Issues #144 through #146 extend it through retrospective,
Dataset/list/opponent, and complete Position/Historical Result propagation. Issue
#147 adds bounded opt-in public Root Result and actual-artifact provenance.

## Public namespaces

The supported public namespaces are:

```text
skat_ai
skat_ai.api
skat_ai.api.v1
skat_ai.errors
```

Only names listed by each namespace's exact `__all__` are stable. The Package
Root exports only `api`, `errors`, and `__version__`, and `skat_ai.api` exports
only `v1`.
Technical importability does not make any other `skat_ai.*` module public.
Direct imports from workflow, Domain, builder, serializer, schema-loader, or
other internal modules have no compatibility guarantee.

Issues #150 through #153 Session contracts, projection, replay, incremental
validation, Command application, canonical Retrospective Historical and
information-safe Position Request export, and pre-Play Decision Checkpoints
remain internal under `skat_ai.session_*`. Internal construction and freezing of
the existing `RequestDocumentV1` adds no public Session type, function, Root
workflow, Request/Result field, or option. The exact public export surfaces in
this document are unchanged. See
[Interactive session contracts](interactive_session_contracts.md) and
[Retrospective Session export](retrospective_session_export.md), and
[Session Position export and Decision checkpoints](live_session_position_export.md).

The internal version-1 field-level provenance language is documented in
[Field-level information provenance](field_level_information_provenance.md).
Its sidecar ledgers, coverage audits, Information Use Context, redaction, and
all-seven-workflow complete Root Result propagation remain internal. Issue #147
selects only one mapped Root Result plus actual artifacts, applies the existing
redaction helper, and recomputes complete public coverage. It does not expose
consumed-input, decision, intermediate-stage, or unredacted Application
attachments. See [Complete Result provenance](complete_result_provenance.md) and
[Public field provenance](public_field_provenance.md).

The internal Application orchestration contract is documented in
[Application orchestration](application_orchestration.md). It consumes
`RequestDocumentV1` and produces `ResultDocumentV1`; the public facade is the
stable adapter over that boundary. Direct `skat_ai.application` imports have no
public compatibility guarantee. Its generic dispatcher, workflow options,
injected documents, and artifacts remain internal.

## Version And Policy Constants

The version-1 constants are:

```text
PUBLIC_API_CONTRACT_VERSION = 1
PUBLIC_API_NAMESPACE = skat_ai.api.v1
PUBLIC_API_COMPATIBILITY_POLICY = additive_until_v1_0
LEGACY_MAIN_COMPATIBILITY_TARGET = v1.0.0
DEFAULT_INPUT_REFERENCE_V1 = memory://skat-ai/request
EXECUTION_ARTIFACT_NAMES_V1 = (opponent_statistics_input,)
PUBLIC_FIELD_PROVENANCE_VERSION = 1
PUBLIC_FIELD_PROVENANCE_ROOT_FIELD = field_provenance
PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES = (
    root_result_without_field_provenance,
    artifact_document,
)
```

Package version, API contract version, JSON-schema versions, and Domain contract
versions are independent dimensions. The current Package version remains
`0.13.0`; API contract version `1` is not derived from it. A Package release does
not automatically increment the API contract, and an API change does not
silently rewrite JSON-schema or Domain versions. `ApiVersionInfoV1` intentionally
contains no Package version.

## Workflows

`WorkflowV1` is a string-valued enum containing exactly these Root workflows in
canonical order:

```text
position_analysis
historical_game
training_dataset
training_dataset_preparation
opponent_statistics
fixed_three_player_historical_list
fixed_three_player_historical_list_comparison
```

The values equal the existing `get_input_workflow()` results. Historical Review,
Search Review, Replay Coaching, evaluation, and audit modes remain options
inside existing Root workflows rather than separate workflows.

## Documents And Options

`RequestDocumentV1` and `ResultDocumentV1` are frozen, slotted, keyword-only
wrappers. Both contain API contract version `1`, one `WorkflowV1`, and a JSON
object document. Results also contain an immutable ordered warning tuple whose
entries must be non-empty strings.

The JSON boundary accepts only:

* objects with string keys;
* arrays;
* strings;
* integers and finite floating-point numbers;
* booleans;
* null.

Construction copies recursively. Stored objects use immutable mappings, and
stored arrays use tuples. Non-string keys, arbitrary Python objects, and NaN or
positive or negative infinity are rejected. `to_dict()` returns a fresh mutable
JSON-compatible representation of the complete wrapper.

`ExecutionOptionsV1` is a frozen, slotted, keyword-only public value with:

```text
validate_output = true
include_provenance = false
workflow_options = {}
opponent_statistics_document = null
opponent_statistics_reference = null
```

Its JSON documents and arrays are copied and stored recursively immutably.
`to_dict()` returns a fresh deterministic mutable representation. Opponent
Statistics document and reference values must be supplied together. No transport
option is accepted. `include_provenance` is a strict boolean and defaults to
`false`. `validate_output=false` disables only post-
execution Root output and artifact schema validation; Root input and Application
semantic validation always run.

The direct `workflow_options` keys map to the matching internal Position,
Historical Game, or Training Dataset Application option contract. The four
simple workflows require an empty object. Unknown, cross-workflow, transport,
invalid-type, and semantically incompatible values are rejected. Internal
Application types are not public exports. The complete key list is documented in
[Public Python API v1](public_python_api_v1.md).

`ExecutionArtifactV1` contains one recognized artifact `name` and one immutable
Root input `document`. Version 1 supports only `opponent_statistics_input`.
`ExecutionResultV1` contains API contract version `1`, one existing
`ResultDocumentV1`, an ordered immutable artifact tuple, and typed nullable
`field_provenance: FieldProvenanceBundleV1 | None`. When present, the typed value
must equal Root `document.field_provenance` and use the same workflow. Duplicate
artifact names are rejected. Its deterministic flattened serialization remains
unchanged and contains
`api_contract_version`, `workflow`, `document`, `warnings`, and `artifacts`.

The public provenance values are immutable
`FieldProvenanceAttachmentV1`, `FieldProvenanceArtifactV1`, and
`FieldProvenanceBundleV1`. The bundle has one Result attachment and provenance
only for artifacts actually returned. The seven workflow-to-Result mappings and
the `opponent_statistics_input` to
`training_dataset/opponent_statistics_input` mapping are authoritative in
[Public field provenance](public_field_provenance.md).

## Executable Facade

The additive public functions are:

```text
parse_request
execute
execute_document
serialize_result
```

`parse_request` validates the Root input schema, detects the Root workflow, and
returns an immutable defensive Request without execution. `execute` revalidates
directly constructed Requests, including API version and wrapper workflow
identity, translates public options, and executes the Application exactly once.
`execute_document` avoids duplicate Root validation and detection while matching
explicit parse-then-execute results. `serialize_result` returns a fresh mutable
flattened envelope and rejects wrong input types with
`SkatAISerializationError`.

The facade validates Root input through packaged `input.schema.json`, Root output
through packaged `output.schema.json`, and reusable artifacts through the Root
input schema. Provenance-enabled output additionally follows strict packaged
`field_provenance.schema.json`. Validation is lazy, current-working-directory
and repository-root
independent, local-only, deterministic, and reports RFC 6901 paths. Document
failures use
`SkatAISchemaError`, missing resources use `SkatAIResourceError`, and invalid
packaged schemas use `SkatAIInvariantError`. The backend uses
`importlib.resources` and the private `skat_ai.schema_resources` Package, with no
network retrieval or concrete filesystem-path requirement. The authoritative
repository `schemas/` files and packaged resources have exact filename and byte
parity.

Existing `SkatAIError` instances pass through unchanged. Raw boundary
`ValueError` becomes `SkatAIValidationError`, and raw boundary `OSError` becomes
`SkatAIResourceError`, preserving message and cause without inventing a path.
Unexpected exceptions are not caught.

## Compatibility Metadata

`CompatibilityPolicyV1` contains this exact policy:

| Field | Value |
| --- | --- |
| `policy_id` | `additive_until_v1_0` |
| `public_namespace` | `skat_ai.api.v1` |
| `public_name_removal_before_v1_allowed` | `false` |
| `public_name_renaming_before_v1_allowed` | `false` |
| `additive_public_exports_allowed` | `true` |
| `direct_internal_imports_stable` | `false` |
| `legacy_main_supported_through` | `v1.0.0` |
| `package_version_independent` | `true` |
| `schema_versions_independent` | `true` |
| `deprecation_warning_name` | `SkatAIDeprecationWarning` |

`ApiVersionInfoV1` contains the API contract version, namespace, canonical
supported workflows, canonical normal Result states, and compatibility policy.
`get_api_version_info_v1()` returns a fresh, deterministic, equal immutable value
without file or schema access.

## Normal Result States

`NORMAL_RESULT_STATES_V1` is:

```text
complete
partial
timeout
unavailable
final
lot_required
not_assessable
```

These are recognized normal state values used across different workflows. They
do not form a new global Domain enum and do not replace workflow-specific
schemas. A valid Search `partial`, `timeout`, or `unavailable` result, Dataset
Preparation `unavailable` Plan, list `lot_required` status, or Replay Coaching
`not_assessable` state remains a successful Result. Malformed combinations
remain validation failures under their existing contracts.

## Public Errors

The stable hierarchy is:

```text
SkatAIError
    SkatAIValidationError (ValueError)
        SkatAIWorkflowError
            SkatAICliUsageError
        SkatAIInformationPolicyError
        SkatAISchemaError
    SkatAISerializationError (ValueError)
    SkatAIResourceError (OSError)
    SkatAIInvariantError (RuntimeError)

SkatAIDeprecationWarning (DeprecationWarning)
```

Every `SkatAIError` has a non-empty human-readable `message`, a class-defined
stable `code`, and nullable `path`. Its deterministic `to_dict()` has exactly
`code`, `message`, and `path`. Codes are:

| Error | Code |
| --- | --- |
| `SkatAIError` | `skat_ai_error` |
| `SkatAIValidationError` | `validation_error` |
| `SkatAIWorkflowError` | `workflow_error` |
| `SkatAIInformationPolicyError` | `information_policy_error` |
| `SkatAISchemaError` | `schema_error` |
| `SkatAISerializationError` | `serialization_error` |
| `SkatAIResourceError` | `resource_error` |
| `SkatAIInvariantError` | `invariant_error` |
| `SkatAICliUsageError` | `cli_usage_error` |

Unrelated Domain code is not broadly migrated. The executable facade translates
only raw `ValueError` and `OSError` that cross its public boundary.

## CLI compatibility

Installed `skat-ai`, module `python -m skat_ai`, and Legacy `python main.py`
share one Package-owned CLI implementation. Root `python main.py` remains
supported through at least `v1.0.0`.
All three accept `--include-provenance`; without it, Root output remains
unchanged. With it, JSON includes the public sidecar, non-quiet output adds only
a concise aggregate provenance summary, and `--quiet` suppresses that summary
without removing the JSON field.
`main.CliUsageError` is an exact compatibility alias for
`SkatAICliUsageError`. Existing catches, messages, prefixes, patch points, and
argument validation remain unchanged.

The public Exit Code constants are:

```text
CLI_EXIT_CODE_SUCCESS = 0
CLI_EXIT_CODE_FAILURE = 1
CLI_EXIT_CODE_USAGE = 2
```

Normal unavailable or incomplete Results still return success. Semantic CLI
usage errors return `2`; caught input, resource, runtime, and output failures
retain `1`.

## Deprecation Policy

No version-1 public name may be removed or renamed before `v1.0.0`. Additive
public names and optional fields with defaults are allowed. A future removal
after `v1.0.0` requires a documented replacement, a migration note, and a prior
release that emits `SkatAIDeprecationWarning`. Internal imports receive no such
guarantee. No deprecation warning is emitted now.

## Package Version

`skat_ai.__version__` reports installed distribution metadata from
`importlib.metadata.version("skat-ai")`. Installed and Editable distributions
report `0.13.0`; a source-only environment without distribution metadata may
report `0+unknown`. The fallback reads no repository file.

This additive Package-Root export does not change `skat_ai.api.__all__`,
`skat_ai.api.v1.__all__`, or `skat_ai.errors.__all__`. Package version remains
absent from `ApiVersionInfoV1`, API Results, and Root JSON output.

## Remaining Work

Issue #147 implements bounded public Root Result and actual-artifact provenance.
Broader field-level enforcement and public exposure of consumed-input, decision,
and intermediate-stage attachments remain open before `v1.0.0`. Provenance does
not integrate or replace existing Confidence contracts.

The internal interactive Session contract foundation is implemented by Issue
#150, and deterministic transitions plus incremental validation are implemented
by Issue #151. Issue #152 constructs canonical Historical Requests internally
without executing them or changing this namespace. Issue #153 constructs
information-safe Position Requests and immutable pre-Play Decision Checkpoints
internally without executing analysis. Persistence and a Public Session API
remain later work; no version-1 public export changes at this boundary.

Internal Application orchestration version `1`, no-I/O execution for all seven
Root workflows, legacy CLI transport parity, and auxiliary artifacts are
implemented by Issue #139. Issue #140 exposes them through the stable public
facade without adding transport I/O or provenance. Issue #141 adds distribution
metadata, private Package Resource schemas, `py.typed`, Package version export,
and Wheel/sdist clean-install gates without changing the API facade exports.
Issue #142 adds the installed and module CLI transports without changing this
Public API surface. Issue #143 adds internal live Position enforcement without
changing it. Issue #144 adds internal retrospective Position, Historical Review,
Historical Search Review, and Replay Coaching propagation without changing it.
Issue #145 adds internal Dataset, Preparation, Opponent, Profile, list, and
comparison propagation without changing it. Issue #146 completes internal
Position and Historical Result provenance. Issue #147 adds the bounded public
types, option, Root field, strict Schema, and CLI transport while preserving the
flattened API envelope and default output.
See [Installed CLI](installed_cli.md) and
[Packaging and distribution](packaging_and_distribution.md).
