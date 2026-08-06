# Public API contracts

This document defines the public Python contract foundation introduced by Issue
#137. The API contract version is `1`, and its stable versioned namespace is:

```text
skat_ai.api.v1
```

This foundation does not execute workflows. It adds no `execute`,
`parse_request`, `execute_document`, workflow-specific helper, installed CLI,
packaged schema, or provenance contract.

## Public namespaces

The supported public namespaces are:

```text
skat_ai
skat_ai.api
skat_ai.api.v1
skat_ai.errors
```

Only names listed by each namespace's exact `__all__` are stable. The Package
Root exports only `api` and `errors`, and `skat_ai.api` exports only `v1`.
Technical importability does not make any other `skat_ai.*` module public.
Direct imports from workflow, Domain, builder, serializer, schema-loader, or
other internal modules have no compatibility guarantee.

## Version And Policy Constants

The version-1 constants are:

```text
PUBLIC_API_CONTRACT_VERSION = 1
PUBLIC_API_NAMESPACE = skat_ai.api.v1
PUBLIC_API_COMPATIBILITY_POLICY = additive_until_v1_0
LEGACY_MAIN_COMPATIBILITY_TARGET = v1.0.0
```

Package version, API contract version, JSON-schema versions, and Domain contract
versions are independent dimensions. The current Package version remains
`0.12.0`; API contract version `1` is not derived from it. A Package release does
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

`ExecutionOptionsV1` is a frozen, slotted, keyword-only placeholder with one
boolean field:

```text
validate_output = true
```

It describes later post-execution output-schema validation. It does not disable
semantic input validation and is not consumed by an execution function yet.

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

This issue does not migrate unrelated existing raw Domain exceptions. Later
executable API work will define where existing failures are translated into
these public boundary types.

## Legacy CLI

Root `python main.py` remains supported through at least `v1.0.0`.
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

## Remaining Work

The following remain open for later `v0.13.0` issues:

* reusable Application orchestration;
* executable Python API facade;
* Package-version metadata export;
* build metadata plus Wheel and sdist validation;
* Package Resource schemas;
* `py.typed`;
* installed `skat-ai` and `python -m skat_ai` CLIs;
* field-level provenance contracts, propagation, and leakage enforcement.
