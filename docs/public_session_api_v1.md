# Public Session API version 1

## Contract identity

The stable, transport-free Session namespace is `skat_ai.api.v1.session`:

```text
PUBLIC_SESSION_API_VERSION = 1
PUBLIC_SESSION_API_NAMESPACE = skat_ai.api.v1.session
PUBLIC_SESSION_API_COMPATIBILITY_POLICY = additive_until_v1_0
```

`session` is appended to `skat_ai.api.v1.__all__`; every earlier export retains
its order and identity. `skat_ai.__all__`, `skat_ai.api.__all__`, and
`skat_ai.errors.__all__` are unchanged. Direct imports from `skat_ai.session_*`
remain unsupported. Only names in `skat_ai.api.v1.session.__all__` are stable.

The canonical operations are, in order:

```text
create
apply_command
rewind
correct
export_position
export_historical
build_checkpoint
classify_checkpoint
build_persistence_document
resume_persistence_document
```

## Stable exports

The exact 52-name surface is:

```text
PUBLIC_SESSION_API_VERSION
PUBLIC_SESSION_API_NAMESPACE
PUBLIC_SESSION_API_COMPATIBILITY_POLICY
SESSION_API_OPERATIONS
SESSION_FIELD_PROVENANCE_VERSION
SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE
SessionApiVersionInfoV1
SessionApiOptionsV1
SessionApiResultV1
SessionProvenanceContextV1
SessionFieldProvenanceAttachmentV1
SessionFieldProvenanceBundleV1
get_session_api_version_info_v1
SessionPlayerV1
SessionStateV1
SessionCommandRecordV1
SessionCommandV1
SetSessionGameMetadataCommandV1
RecordSessionDealtCardCommandV1
SetSessionDeclarerCommandV1
SetSessionDeclarationCommandV1
RecordSessionDiscardCommandV1
RecordSessionPlayCommandV1
SetSessionGameEventCommandV1
SetSessionGameEndCommandV1
PromoteSessionToRetrospectiveCommandV1
SetSessionPublicHandCommandV1
SessionValidationDiagnosticV1
SessionExportReadinessV1
SessionValidationResultV1
SessionTransitionResultV1
SessionPositionExportOptionsV1
SessionRequestExportV1
SessionDecisionCheckpointV1
SessionUndoResultV1
SessionCommandCorrectionV1
SessionCorrectionResultV1
SessionCheckpointLineageV1
SessionPersistenceDocumentV1
SessionResumeResultV1
parse_session_command
create_session
apply_session_command
rewind_session
correct_session_command
export_session_position_request
export_session_historical_request
build_session_decision_checkpoint
classify_session_decision_checkpoint
build_session_persistence_document
resume_session_document
serialize_session_result
```

The exposed domain types are the exact existing frozen internal types, not
copies or adapters. Type identity is therefore preserved. Projection values,
low-level validators, persistence codec and fingerprint helpers, file Save/Load,
`SessionPersistenceWriteResultV1`, temporary-file helpers, and internal ledger
builders remain internal.

## Versions and options

`SessionApiVersionInfoV1` reports Public API, Public Session API, Session,
Command, transition, projection, Request Export, Decision Checkpoint, history,
lineage, and persistence contract versions. Package and Schema versions are
intentionally absent because those version axes are independent.

`SessionApiOptionsV1` has two strict booleans:

```text
validate_output = true
include_provenance = false
```

Disabling `validate_output` skips only final Session Result Schema validation.
Python contract, replay, transition, export, persistence, and information-policy
validation remain mandatory.

## Result envelope

`SessionApiResultV1` contains `api_contract_version`,
`public_session_api_version`, `operation`, `value`, and nullable
`field_provenance`. It contains no path, transport metadata, request ID, or
timestamp. Null provenance is omitted from serialized output.

| Operation | Exact value |
| --- | --- |
| `create` | `SessionStateV1` |
| `apply_command` | `SessionTransitionResultV1` |
| `rewind` | `SessionUndoResultV1` |
| `correct` | `SessionCorrectionResultV1` |
| `export_position` | `SessionRequestExportV1`, target `position_analysis` |
| `export_historical` | `SessionRequestExportV1`, target `historical_game` |
| `build_checkpoint` | `SessionDecisionCheckpointV1` |
| `classify_checkpoint` | `SessionCheckpointLineageV1` |
| `build_persistence_document` | `SessionPersistenceDocumentV1` |
| `resume_persistence_document` | `SessionResumeResultV1` |

Rejected, conflicted, unavailable, unchanged, and partial domain outcomes are
normal typed Results, not transport failures.

## Parsing and execution

`parse_session_command()` validates a JSON-object mapping against the packaged
Session Schema, strictly reconstructs all ten Command kinds through the existing
persistence codec, preserves explicit nulls, and rejects missing, unknown, or
invalid fields. It performs no transition.

Each operation wrapper invokes exactly one corresponding internal operation.
Position and Historical exports return existing immutable `RequestDocumentV1`
values without executing Position Analysis, bounded Search, Historical review,
Application dispatch, or `execute()`. Persistence construction and resume are
public only in memory. Public file Save/Load remains unavailable.

The existing public error hierarchy is reused. Existing `SkatAIError` values
pass through; public-boundary `ValueError` and `TypeError` become
`SkatAIValidationError`; Schema, resource, invariant, and serialization failures
use their existing stable error classes.

## Schema and boundaries

`schemas/session.schema.json` is a strict Draft 2020-12 standalone contract,
loaded lazily from Package Resources. It does not add a Session Root workflow:
`WorkflowV1` remains seven values. Root JSON, all CLI forms, and 77 generated
outputs remain unchanged. The active tree has 63 authoritative and packaged
Schemas, while Package version remains `0.13.0`.

The installed, module, and Legacy CLIs do not support Session commands. Session-
triggered analysis, automatic Checkpoint collection, actual-card attachment,
public file transport, Session examples/generated outputs, end-to-end capture,
and UI remain open.

See [Session provenance](session_provenance.md) for the optional returned-value
sidecar.
