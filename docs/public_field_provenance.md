# Public field provenance

This document is the authoritative bounded public field-provenance contract
implemented by Issue #147. It exposes public-safe provenance for the exact Root
Result and for auxiliary artifacts actually returned by one execution. It does
not expose the complete internal Application provenance bundle.

The contract version is:

```text
PUBLIC_FIELD_PROVENANCE_VERSION = 1
```

This version is independent of Package version `0.14.0`, Public API contract
version `1`, Application orchestration version `1`, internal field-provenance
version `1`, JSON Schema versions, and Domain contract versions.

## Public identity

The stable `skat_ai.api.v1` namespace exports:

```text
PUBLIC_FIELD_PROVENANCE_VERSION
PUBLIC_FIELD_PROVENANCE_ROOT_FIELD
PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES
FieldProvenanceAttachmentV1
FieldProvenanceArtifactV1
FieldProvenanceBundleV1
```

The constants fix:

```text
PUBLIC_FIELD_PROVENANCE_ROOT_FIELD = field_provenance
PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES = (
    root_result_without_field_provenance,
    artifact_document,
)
```

The public values are frozen, slotted, keyword-only dataclasses. Nested JSON is
defensively copied and recursively immutable, and `to_dict()` returns a fresh
deterministic mutable representation.

`FieldProvenanceAttachmentV1` contains exactly:

```text
attachment_name
document_role
document_scope
ledger
coverage_summary
information_use_context
```

Public attachments always use `document_role = result`.

`FieldProvenanceArtifactV1` contains exactly `artifact_name` and its matching
`attachment`. `FieldProvenanceBundleV1` contains exactly `workflow`, one
`result`, the ordered `artifacts`, `provenance_version`, and
`redaction_policy = omit_engine_private_details`.

## Result mappings

Each of the seven Root workflows has one explicit Result mapping:

| Root workflow | Result attachment |
| --- | --- |
| `position_analysis` | `position_result` |
| `historical_game` | `historical_game_result` |
| `training_dataset` | `training_dataset_result` |
| `training_dataset_preparation` | `dataset_preparation_result` |
| `opponent_statistics` | `opponent_statistics_result` |
| `fixed_three_player_historical_list` | `historical_list_result` |
| `fixed_three_player_historical_list_comparison` | `historical_list_comparison_result` |

The Result attachment covers the exact Root Result before the
`field_provenance` field is added, so its scope is always
`root_result_without_field_provenance`. This avoids recursive self-provenance.

The only current public artifact mapping is:

| Artifact | Workflow | Attachment | Scope |
| --- | --- | --- | --- |
| `opponent_statistics_input` | `training_dataset` | `training_dataset/opponent_statistics_input` | `artifact_document` |

Artifact provenance is emitted only when that artifact is actually returned.
The exported reusable Opponent Statistics JSON document itself remains unchanged
and does not receive a nested `field_provenance` field.

## Selection boundary

Public conversion requires exactly one internal attachment matching the selected
Root Result. It includes only:

* that one Root Result attachment;
* one artifact attachment for each artifact actually returned by the execution.

It does not expose consumed-input attachments, decision attachments,
retrospective stage attachments, internal aggregate attachments, or any other
retained Application sidecar. It also does not attach provenance for a possible
artifact that was not produced.

The public attachment contains ledger metadata, coverage, and Information Use
Context. It does not embed another copy of the document whose fields the ledger
describes.

## Redaction and coverage

Public conversion uses the existing pure
`redact_field_provenance_ledger_for_public_output()` helper. It removes
engine-private entries, source references, and dependencies without mutating the
internal ledger. A redacted attachment may report only the generic
`private_dependencies_redacted` limitation; it never identifies the removed
path, reference, value, or private category.

After redaction, coverage is recomputed against the exact public document in the
attachment's declared scope. Publication fails unless:

```text
ledger.status = complete
all_paths_accounted_for = true
provenance_complete = true
uncovered_paths = []
orphaned_entry_paths = []
orphaned_exemption_paths = []
overlapping_paths = []
```

Legacy exemptions and unavailable or legacy limitations are rejected. Every
retained dependency must identify a retained public entry. Redaction is not a
way to publish incomplete coverage: if removing an engine-private entry would
leave a document leaf uncovered, public conversion fails.

Public output exposes no unredacted ledger, concrete Compatible World, hidden
ownership assignment, private proof hand or proof state, exact private Search
state, private seed, tie key, component identity, cache, branch, or Principal
Variation.

## Root JSON shape

Opt-in execution adds one Root field beside the existing workflow output:

```json
{
  "input_file": "example.json",
  "field_provenance": {
    "provenance_version": 1,
    "workflow": "opponent_statistics",
    "redaction_policy": "omit_engine_private_details",
    "result": {
      "attachment_name": "opponent_statistics_result",
      "document_role": "result",
      "document_scope": "root_result_without_field_provenance",
      "ledger": {
        "provenance_version": 1,
        "status": "complete",
        "entries": [],
        "exemptions": [],
        "limitations": []
      },
      "coverage_summary": {},
      "information_use_context": {}
    },
    "artifacts": []
  }
}
```

The abbreviated arrays and objects above show placement only. Real output
contains the complete strict ledger, coverage summary, and Information Use
Context required by `field_provenance.schema.json`.

Without opt-in, `field_provenance` is omitted and the prior Root Result remains
unchanged in field structure.

## Public Python API

`ExecutionOptionsV1.include_provenance` is a strict boolean and defaults to
`False`. Set it to `True` to request the public sidecar:

```python
import json
from pathlib import Path

from skat_ai.api.v1 import ExecutionOptionsV1, execute_document, serialize_result

document = json.loads(Path("examples/opponent_statistics.json").read_text())
result = execute_document(
    document,
    options=ExecutionOptionsV1(include_provenance=True),
    input_reference="examples/opponent_statistics.json",
)

assert result.field_provenance is not None
assert result.result.to_dict()["document"]["field_provenance"] == (
    result.field_provenance.to_dict()
)
serialized = serialize_result(result)
```

`ExecutionResultV1.field_provenance` is the typed
`FieldProvenanceBundleV1 | None` view. When present, it must equal the serialized
Root `document["field_provenance"]` and use the same workflow.

The flattened execution envelope remains unchanged:

```text
api_contract_version
workflow
document
warnings
artifacts
```

There is no sixth envelope-level provenance field. Provenance is inside the Root
`document`, while `ExecutionResultV1.field_provenance` provides the typed view.
The existing `validate_output` option validates provenance-enabled Root output
and actual artifacts through the registered schemas by default.

## CLI

All three CLI forms accept the same opt-in flag:

```powershell
skat-ai --input examples/opponent_statistics.json --include-provenance --output outputs/statistics.json
python -m skat_ai --input examples/opponent_statistics.json --include-provenance --output outputs/statistics.json
python main.py --input examples/opponent_statistics.json --include-provenance --output outputs/statistics.json
```

Without `--quiet`, successful output adds one concise aggregate section:

```text
Field Provenance
Version: 1
Status: complete
Result attachment: opponent_statistics_result
Covered leaves: <covered>/<total>
Private dependencies redacted: no
Artifact attachment count: 0
```

The section does not print field paths, source-reference IDs, Player IDs, cards,
or ledger entries. `--quiet` suppresses the human-readable section and file
confirmations while retaining `field_provenance` in JSON written with
`--output`:

```powershell
skat-ai --input examples/opponent_statistics.json --include-provenance --output outputs/statistics.json --quiet
```

Historical Opponent Statistics aggregation can include Result and actual export
artifact provenance together:

```powershell
skat-ai --input examples/training_dataset_variable_length.json --aggregate-opponent-statistics --export-opponent-statistics outputs/opponent-statistics.json --include-provenance --output outputs/aggregation.json --quiet
```

The `aggregation.json` sidecar maps the actual export artifact. The separate
`opponent-statistics.json` export remains the unchanged reusable input document.

## Schema and validation

`schemas/field_provenance.schema.json` is a strict Draft 2020-12 contract. It
rejects unknown bundle, attachment, ledger, entry, exemption, coverage, context,
and artifact fields; fixes version and redaction constants; enforces all seven
workflow-to-Result mappings; permits only complete public ledgers; excludes
`engine_private` visibility and legacy exemptions; requires complete empty-error
coverage; and permits at most one mapped artifact entry. Runtime conversion also
requires that entry to match the artifact actually returned.

`schemas/output.schema.json` references that contract from every Root output
branch and constrains the sidecar workflow to the selected branch. The published
`v0.13.0` baseline contains 62 Schemas. The active tree contains 63 because the
separate standalone Session Schema is packaged byte-identically.

The `v0.13.0` package baseline has 77 deterministic generated-output scenarios.
The original 70 published `v0.12.0` scenarios remain unchanged, and seven
append-only Issue #147 scenarios cover one provenance-enabled Result for every
Root workflow. The Training Dataset scenario also covers the actual
`opponent_statistics_input` artifact mapping. The published `v0.12.0` historical
facts remain 70 scenarios and 4,762 pytest tests.

Issue #157 appends eight Session scenarios for an active total of 85 without
changing any of those 77 published Root scenarios. Session operation provenance
uses the independent Session Provenance contract, while Session-triggered
`analyze`, available `review`, and available `finalize` can request this existing
Root Result sidecar on their Position or Historical output.

## Session distinction

`skat_ai.api.v1.session` has its own default-omitted complete returned-value
provenance and standalone Schema. Its appended `observe_checkpoint` and
`export_checkpoint_review` operations preserve the frozen decision-time Request
and classify the actual Card as `retrospective_attachment`. The stable
`skat_ai.api.v1.session.files` Save/Load Result has no provenance option and
retains no path.

The Session CLI `--include-provenance` applies to public Session operation JSON
or to this existing Root Result provenance when an explicit analysis command
executes Application. It does not publish persistence fingerprints, file paths,
complete private Session data, or internal Session ledgers in human-readable
output. See [Session provenance](session_provenance.md) and
[Session Decision observations](session_decision_observations.md).

## Boundaries

This contract proves complete field coverage only for the selected public Root
Result without its sidecar and for actual public artifacts. It does not expose or
claim public coverage for consumed inputs, individual decisions, intermediate
stages, or the full internal Application bundle.

Provenance describes where and how a value was obtained. It does not add a
Confidence, probability, quality, calibration, severity, or optimality claim.
Existing Hidden-card Confidence, Profile confidence, Replay Coaching evidence,
Search exactness, and specialized source-provenance contracts remain separate.

Issue #147 completes the bounded public Root Result and actual-artifact exposure
in the `v0.13.0` package baseline. Broader field-level information
enforcement across loading and every internal boundary remains incomplete before
`v1.0.0`; this public sidecar must not be described as complete end-to-end
provenance for the product.
