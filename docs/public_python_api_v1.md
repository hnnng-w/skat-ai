# Public Python API v1

The executable version-1 Python facade is available from:

```text
skat_ai.api.v1
```

It accepts the same Root JSON documents as the legacy repository CLI, executes
the existing internal Application layer, and returns the unchanged Root output
document inside immutable public contracts. It performs no caller transport I/O.

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
        workflow_options={"sample_count_override": 10},
    ),
)
serialized = serialize_result(result)
json.dumps(serialized)
```

## Constants

```text
DEFAULT_INPUT_REFERENCE_V1 = memory://skat-ai/request
EXECUTION_ARTIFACT_NAMES_V1 = (opponent_statistics_input,)
```

The input reference is opaque descriptive metadata. The facade never resolves,
opens, normalizes, or otherwise treats it as a path or URI. The exact value is
preserved in the Root output `input_file` field.

## Execution options

`ExecutionOptionsV1` is frozen, slotted, keyword-only, defensively copied, and
recursively immutable. Its deterministic `to_dict()` returns fresh mutable JSON:

```text
validate_output = true
workflow_options = {}
opponent_statistics_document = null
opponent_statistics_reference = null
```

The Opponent Statistics document and reference must be supplied together. No
transport path, output destination, quiet mode, provenance ledger, or provenance
option is accepted.

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

`ExecutionResultV1` contains one existing `ResultDocumentV1` plus an ordered
artifact tuple. Duplicate artifact names are rejected. `to_dict()` and
`serialize_result()` produce:

```text
api_contract_version
workflow
document
warnings
artifacts
```

`document` is the unchanged Root output. Each artifact entry contains `name` and
its complete reusable Root input `document`.

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
file, printing, and Exit Code behavior outside this no-I/O facade. Installed
`skat-ai`, module `python -m skat_ai`, and Legacy `python main.py` preserve Root
JSON parity; the CLI does not call this Public API as an intermediate layer.

## Current boundaries

The facade adds no workflow-specific helper functions, public Domain dataclasses,
or field-level provenance. Issue #141 adds private Package Resources, build-
system metadata, Package Data, `py.typed`, Package-Root `__version__`, and
Wheel/sdist validation without a Package version change. Issue #142 adds a
separate installed CLI contract without adding API options or exports. See
[Installed CLI](installed_cli.md) and
[Packaging and distribution](packaging_and_distribution.md).
