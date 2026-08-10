# Public Python API v1

The executable version-1 Python facade is available from:

```text
skat_ai.api.v1
```

It accepts the same Root JSON documents as the legacy repository CLI, executes
the existing internal Application layer, and returns the Root output document
inside immutable public contracts. Output is unchanged by default; an explicit
option adds bounded public field provenance. It performs no caller transport I/O.

Issue #156 adds a separate additive `skat_ai.api.v1.session` facade. Issue #157
extends it with Decision Observation and Checkpoint review export and adds the
stable `skat_ai.api.v1.session.files` Save/Load subnamespace. Session API exports
still construct existing Root Requests without executing them. The separate
Session CLI may explicitly pass those Requests to the existing Application once;
that transport does not call this Root public facade as an intermediate layer or
add a workflow. See [Public Session API version 1](public_session_api_v1.md) and
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).

## Public functions

```python
from skat_ai.api.v1 import (
    ExecutionOptionsV1,
    execute,
    execute_document,
    parse_request,
    serialize_result,
)
```

The functions are:

* `parse_request(document) -> RequestDocumentV1`: always validates the Root
  input schema, detects one of the seven Root workflows, and defensively copies
  the document without executing it.
* `execute(request, *, options=None, input_reference=...) -> ExecutionResultV1`:
  revalidates even a directly constructed Request, verifies the wrapper workflow,
  translates public options, and invokes the Application dispatcher exactly once.
* `execute_document(document, *, options=None, input_reference=...) ->
  ExecutionResultV1`: parses and executes one raw document without duplicate Root
  schema validation or workflow detection inside this convenience path.
* `serialize_result(result) -> dict[str, object]`: returns a fresh mutable,
  deterministic flattened API envelope and performs no file write.

Example:

```python
import json

from skat_ai.api.v1 import ExecutionOptionsV1, execute_document, serialize_result

document = {
    "game_type": "grand",
    "player_role": "declarer",
    "player_position": "middlehand",
    "trick_leader": "right",
    "hand": ["CJ", "SJ", "HJ"],
    "current_trick": ["C7"],
    "played_cards": [],
    "completed_tricks": [],
    "declarer_points": 0,
    "defender_points": 0,
    "next_player": "me",
    "skat": [],
    "left_hand_size": 3,
    "right_hand_size": 3,
    "sample_count": 20,
    "random_seed": 42,
    "use_basic_opponent_strategy": True,
}
result = execute_document(
    document,
    options=ExecutionOptionsV1(
        include_provenance=True,
        workflow_options={"sample_count_override": 10},
    ),
)
serialized = serialize_result(result)
assert result.field_provenance is not None
assert serialized["document"]["field_provenance"] == result.field_provenance.to_dict()
json.dumps(serialized)
```

## Constants

```text
DEFAULT_INPUT_REFERENCE_V1 = memory://skat-ai/request
EXECUTION_ARTIFACT_NAMES_V1 = (opponent_statistics_input,)
PUBLIC_FIELD_PROVENANCE_VERSION = 1
PUBLIC_FIELD_PROVENANCE_ROOT_FIELD = field_provenance
```

The input reference is opaque descriptive metadata. The facade never resolves,
opens, normalizes, or otherwise treats it as a path or URI. The exact value is
preserved in the Root output `input_file` field.

## Execution options

`ExecutionOptionsV1` is frozen, slotted, keyword-only, defensively copied, and
recursively immutable. Its deterministic `to_dict()` returns fresh mutable JSON:

```text
validate_output = true
include_provenance = false
workflow_options = {}
opponent_statistics_document = null
opponent_statistics_reference = null
```

The Opponent Statistics document and reference must be supplied together. No
transport path, output destination, or quiet mode is accepted.
`include_provenance` is a strict boolean. Its default `False` preserves the prior
Root document; `True` adds one public-safe Root `field_provenance` sidecar.

`workflow_options` is one direct object. Its exact Position Analysis keys are:

```text
sample_count_override
random_seed_override
opponent_strategy_override
opponent_policy_preset_override
opponent_lead_policy_override
opponent_response_policy_override
use_profile_presets_override
left_opponent_lead_policy_override
left_opponent_response_policy_override
right_opponent_lead_policy_override
right_opponent_response_policy_override
multi_step_count
card_selection_policy
expected_value_sample_count
strict_context
compare_policies
comparison_only
left_opponent_player_id
right_opponent_player_id
```

Its exact Historical Game keys are:

```text
decision_snapshots
immediate_review
search_review
replay_coaching
search_seed
search_budget_profile
immediate_sample_count
immediate_base_random_seed
opponent_policy_preset_override
opponent_lead_policy_override
opponent_response_policy_override
left_opponent_lead_policy_override
left_opponent_response_policy_override
right_opponent_lead_policy_override
right_opponent_response_policy_override
use_profile_presets_override
```

Its exact Training Dataset keys are:

```text
operation
partition_audit_mode
rolling_source_partitions
rolling_evaluation_partitions
bounded_search_seed
bounded_search_partitions
bounded_search_budget_profile
bounded_search_max_decisions
aggregation_included_partitions
aggregation_before
export_opponent_statistics
```

The five Training Dataset operation values remain:

```text
summary
partition_audit
rolling_opponent_policy_evaluation
bounded_search_evaluation
historical_opponent_statistics_aggregation
```

`training_dataset_preparation`, `opponent_statistics`,
`fixed_three_player_historical_list`, and
`fixed_three_player_historical_list_comparison` require an empty options object.
Unknown keys, keys from another workflow, transport-only keys, invalid types, and
semantically incompatible combinations are rejected. The translated values are
still validated by the existing Application contracts; the facade does not
duplicate workflow rules.

## External Opponent Statistics

An external document is validated as a Root input and must select the
`opponent_statistics` workflow. It is injected into Position Analysis or
Historical Game execution and is not executed separately. The existing live
stable-ID binding, Profile Preset, historical participant matching, and strict
time-safety rules remain authoritative. The descriptive reference is preserved
exactly in the existing profile-application output.

## Results and artifacts

`ExecutionArtifactV1` and `ExecutionResultV1` are frozen, slotted, keyword-only
public values. The only current artifact name is `opponent_statistics_input`.
It is returned only when historical Opponent Statistics aggregation requests a
reusable export. It remains separate from the primary Root result and has no
output path.

`ExecutionResultV1` contains one existing `ResultDocumentV1`, an ordered artifact
tuple, and `field_provenance: FieldProvenanceBundleV1 | None`. Duplicate artifact
names are rejected. When provenance is requested, the typed bundle must equal
`result.document["field_provenance"]`; otherwise both are absent.
`to_dict()` and `serialize_result()` still produce the same flattened envelope:

```text
api_contract_version
workflow
document
warnings
artifacts
```

`document` is the unchanged Root output. Each artifact entry contains `name` and
its complete reusable Root input `document`. With provenance opt-in, `document`
contains the additive Root `field_provenance` field; no sixth envelope field is
added.

The stable public provenance exports are
`FieldProvenanceAttachmentV1`, `FieldProvenanceArtifactV1`, and
`FieldProvenanceBundleV1`. The bundle contains one explicitly mapped Root Result
attachment plus only artifacts actually returned. Current artifact provenance
maps `opponent_statistics_input` to
`training_dataset/opponent_statistics_input`. See
[Public field provenance](public_field_provenance.md) for exact fields, all seven
Result mappings, document scopes, redaction, and coverage requirements.

Normal workflow states remain successful Results, including `complete`,
`partial`, `timeout`, `unavailable`, `final`, `lot_required`, and
`not_assessable`. The facade does not reinterpret Domain state values.

## Schema validation

Schema resources are read lazily. Importing `skat_ai` or `skat_ai.api.v1` does
not read a schema. The backend uses `importlib.resources` and the private
`skat_ai.schema_resources` Package, independent of both the current working
directory and a repository checkout. It uses Draft 2020-12, preloads packaged
local schemas into a registry, and rejects all unregistered resolution instead
of performing network access.

The facade validates:

* every Root input through packaged `input.schema.json`;
* every Root output through packaged `output.schema.json` by default;
* every reusable auxiliary artifact as a Root input by default.

Provenance-enabled Root output is validated through the strict referenced
`field_provenance.schema.json`. Session creation input, Commands, persistence and
file API mappings, Decision Observations, review exports, and final Session
Results use lazy standalone `session.schema.json` validation through the same
local-only Package Resource registry. The repository and packaged mirrors
contain 63 active Schema resources.

`validate_output=False` skips only post-execution output and artifact schema
validation. Input schema validation and Application semantic validation always
run. The first schema failure is selected deterministically and reports an RFC
6901 JSON Pointer, with the empty string representing the Root.

Document failures use `SkatAISchemaError`, missing resources use
`SkatAIResourceError`, and invalid packaged schemas use
`SkatAIInvariantError`. The Package Resource mirror is checked for exact filename
and byte parity with authoritative repository schemas.

## Error boundary

Existing `SkatAIError` instances pass through unchanged. Raw `ValueError` at the
facade boundary becomes `SkatAIValidationError`; raw `OSError` becomes
`SkatAIResourceError`. The message and exception cause are preserved, and no path
is invented when no reliable public path exists. Unexpected exception classes
are not caught.

## Determinism and I/O

The facade adds no random stream, timestamp, request ID, output reordering, or
warning. It performs no user-file read, user-file write, command-line parsing,
or printing. Callers provide already loaded documents and decide whether and
where to persist serialized results or artifacts. Lazy schema-resource reads are
validation resources, not caller transport I/O.

The Package-owned CLI directly consumes the same Application layer and keeps its
file, printing, and Exit Code behavior outside this no-I/O Root facade. Installed
`skat-ai`, module `python -m skat_ai`, and Legacy `python main.py` preserve Root
JSON parity; the Root CLI does not call this Public API as an intermediate layer.
The additive Session command family uses the stable Public Session and file APIs
for Session operations and invokes Application only for explicit `analyze`,
available `review`, or available `finalize`.

## Current boundaries

The facade adds no workflow-specific helper functions or public Domain
dataclasses. Issue #147 exposes only the redacted complete Root Result attachment
and actual-artifact attachments from the Issue #143 through #146 internal
bundles. It does not expose consumed-input, decision, retrospective-stage,
aggregate-stage, or unredacted attachments. Coverage is recomputed against each
exact declared public document and must remain complete. See
[Complete Result provenance](complete_result_provenance.md) and
[Public field provenance](public_field_provenance.md).
Issue #141 adds private Package Resources, build-
system metadata, Package Data, `py.typed`, Package-Root `__version__`, and
Wheel/sdist validation without a Package version change. Issue #142 adds a
separate installed CLI contract. The current Package version is `0.13.0`. Broader
field-level enforcement and Confidence integration are not implied. See
[Installed CLI](installed_cli.md) and
[Packaging and distribution](packaging_and_distribution.md).

The active Issue #157 tree has 63 Schemas and 85 generated outputs. The
published `v0.13.0` baseline remains 62 Schemas and 77 scenarios. The functional
`v0.14.0` Session milestone is complete pending release preparation; GUI,
platform, cloud, locking, encryption, and unrelated pre-v1 work remain separate.
