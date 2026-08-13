# CLI internal architecture

Issue #162 characterizes and modularizes the internal Root and Session CLI
boundaries without changing their observable contracts. The refactor adds no
Root workflow, Session subcommand, option, Match Capture behavior, Schema,
example, generated scenario, Console Script, Public API export, or Package
version.

## Import direction

The intended dependency direction is:

```text
Domain and rules
    <- Application and Public APIs
        <- Capture Application services
            <- CLI and browser transports
```

Arrows point from a consumer toward the lower layer it may import. CLI modules
are leaf transport adapters. Application, Public API, Match Capture, and
observed-Game modules do not import CLI modules. Issue #164 adds the internal
transport-free Capture Application service over the existing Match,
observed-Game, Workspace, rotation, rule, evidence, and Progress boundaries. It
receives an already loaded Workspace and performs no persistence. Workspace and
Capture modules do not import CLI modules, and CLI modules do not own Capture
rules. Issue #165 adds the leaf `capture_web` transport and Capture CLI. They
delegate to Issue #164 services and Workspace persistence without adding rules,
Application execution, a Root workflow, or a Public API.

The current Session CLI is a bounded transport adapter over the stable Public
Session and Public Session File APIs. Available `analyze`, `review`, and
`finalize` operations additionally pass an already exported Request to the
existing internal Application adapter once. This remains separate from any
Match Capture Application boundary.

## Entry points

The three supported invocation forms remain:

```text
skat-ai
python -m skat_ai
python main.py
```

`skat-ai` is still the only Console Script and resolves exactly to
`skat_ai.cli:main`. `python -m skat_ai` calls the same Package-owned Root CLI
with module invocation identity. Repository-root `main.py` remains a thin
Legacy compatibility facade and is not included in distributions.

`skat_ai.cli.__all__` remains exactly `("main",)`. Leading dispatch precedence
is `capture`, then `session`, then the existing Root parser. Both command-family
imports remain lazy.

## Capture CLI and browser transport

`src/skat_ai/cli/capture_parser.py` owns Capture CLI version `1`, the exact
`capture` command identity, invocation-specific help, required `--workspace`,
optional `--port`, and `--no-open`. `src/skat_ai/cli/capture.py` owns startup,
browser opening, interrupt shutdown, and Exit Code translation. It delegates the
server to the focused Web package and imports no Match Capture rules directly.

The internal `src/skat_ai/capture_web/` package separates independent Web and
Protocol contracts, transport-only timecodes, the locked one-file context,
browser-safe state, operation parsing, server rendering, packaged assets,
security, and Standard Library HTTP lifecycle. Every applied mutation invokes
one existing operation and at most one CAS Save. Unchanged and revision-conflict
outcomes do not Save; persistence conflicts retain context and require explicit
Reload. No Root Application, Session, Search, analysis, materialization, or
external network path is present.

## Root CLI modules

`src/skat_ai/cli/execution.py` is the compatibility facade. It retains the
historically required constants, aliases, helpers, wrappers, presentation
functions, dependency names, `_run_cli`, `run_cli`, and `main`. Its broad import
surface exists for repository-root Legacy compatibility; new Package code should
import the focused internal module that owns a responsibility.

The focused modules are:

| Module | Responsibility |
| --- | --- |
| `root_parser.py` | Root command identity, invocation examples, exact parser construction, and argument parsing. |
| `root_validation.py` | CLI-only semantic option validation and `CliUsageError` wording. |
| `root_compatibility.py` | Legacy patch metadata, captured default dependency values, active Root namespace, dependency resolution, and Legacy-compatible Application dependency construction. |
| `root_application.py` | One internal Application invocation, optional public Root provenance attachment, Result/artifact thawing, external Opponent Statistics adaptation, and retained Legacy Position helper functions. |
| `root_dispatch.py` | One Root input load for dispatch, one workflow detection, workflow precedence, CLI validation order, argument forwarding, and Root Exit Code translation. |
| `root_transport.py` | Existing `run_json_*` file loading, Application option mapping, output and auxiliary export writing, quiet behavior, confirmations, and presentation selection. |
| `presentation/` | Human-only formatting of already produced Root Result mappings. |

The Root presentation modules are grouped by Position, Historical Game,
Dataset, Opponent Statistics, Historical Lists, simulation, provenance, and
shared formatting. They do not load or write files, execute Application or
Public API workflows, or mutate Result mappings.

The Root CLI calls internal Application orchestration directly. It does not
execute through `skat_ai.api.v1.execute()`.

## Legacy compatibility

Repository-root `main.py` continues to star-import the Root compatibility facade
and wraps established functions inside `legacy_patch_namespace()`. This keeps:

* the exact `main.CliUsageError` identity;
* zero-argument Legacy `main()` and `parse_arguments()` signatures;
* Root wrapper and formatter imports;
* wrapper signatures through `functools.wraps`;
* the ordered `_LEGACY_PATCH_POINT_FUNCTIONS` identities;
* the ordered captured `_DEFAULT_LEGACY_PATCH_VALUES` identities;
* dynamic Legacy parser, loader, workflow, validator, runner, and dependency
  patch behavior.

Captured default dependency values continue to isolate installed and module
execution from later mutation of repository-root `main.py`. While the Legacy
namespace is active, established dependency lookups resolve from that namespace.
Nested contexts restore the previous namespace.

This compatibility state is internal, process-global state, as before. It is not
a Public Python API or a concurrency mechanism.

## Root execution sequence

Root dispatch preserves this order:

1. Parse Root arguments.
2. Load the input once for dispatch.
3. Detect the Root workflow once.
4. Apply common or preparation-specific CLI validation.
5. Apply workflow-specific CLI validation.
6. Select exactly one of the seven Root workflow transports.
7. Load the transport document and optional external document through the
   established wrapper boundary.
8. Build one immutable Application invocation and execute it once.
9. Optionally attach public Root provenance without rerunning the workflow.
10. Write requested Result and auxiliary artifact files.
11. Present the already produced Result unless quiet mode is active.

The split preserves existing file access and call counts rather than combining
dispatch characterization with transport execution.

## Session CLI modules

`src/skat_ai/cli/session.py` is the Session compatibility facade. It retains the
Session CLI constants, parser functions, strict JSON loader, `run_session_cli`,
and existing helper aliases and signatures used by Package tests and internal
callers. It builds explicit operation services so the characterized collector
and Legacy Application executor seams remain replaceable through the facade.

The focused modules are:

| Module | Responsibility |
| --- | --- |
| `session_parser.py` | Separate 12-subcommand parser, option validators, exact defaults, and Position export-option construction. |
| `session_transport.py` | Strict caller-file JSON loading with UTF-8, no-BOM, duplicate-key, finite-number, malformed-JSON, object-root, and missing-file behavior. |
| `session_context.py` | Session context creation/loading, strict create/correction parsing, persistence-document construction, optimistic Save, and context replacement. |
| `session_checkpoints.py` | Source, resulting-State, correction-prefix, explicit, export, and analysis Checkpoint collection, deduplication handoff, canonical retention, and persistence orchestration. |
| `session_operations.py` | All 12 subcommand handlers, operation dispatch, Save/no-Save decisions, output shape selection, and explicit-only analysis policy. |
| `session_application.py` | Position and Historical Request execution through the existing Root Application adapter, input references, and Historical option mapping. It performs no Session file I/O. |
| `session_presentation.py` | Session summaries, Diagnostics, lineage and observation display, privacy-safe Position masking, Save/conflict status, JSON output writing, and confirmations. |
| `session_assistant.py` | Deterministic prompt loop and action handling through explicit focused Session services. |

## Session persistence and checkpoints

The Session context retains only the caller path and current persistence
document. Load and Save still use the stable Public Session File API. A mutation
retains the loaded content fingerprint, builds one replacement persistence
document, performs one compare-and-swap Save, and replaces the in-memory context
document only for `saved` or `unchanged`. A conflict performs no retry, reload,
merge, or force overwrite.

Checkpoint orchestration keeps source collection before an accepted local Play,
resulting-State collection after an applicable mutation, and correction-prefix
collection before suffix replay. Exact equal Checkpoints are reused and
persistence remains responsible for canonical ordering. Collection never starts
analysis.

The Session Application adapter executes only an available explicit request:

* `analyze`: one Position execution;
* `review`: one Position execution;
* `finalize`: one Historical execution.

Unavailable values execute no Application workflow. The adapter does not load or
save Session files.

## Assistant boundary

The Assistant no longer imports `skat_ai.cli.session` or reaches through that
facade to private underscore-prefixed implementation functions. It imports the
focused parser, context, Checkpoint, and Application services directly. Its
action order, phase availability, prompts, strict inline JSON wording, injected
I/O, Save behavior, conflict handling, privacy, explicit analysis, EOF behavior,
and Exit Codes remain unchanged.

The Assistant remains a deterministic transport. It adds no natural-language
rule interpretation or Match Capture behavior.

## Characterization and enforcement

Focused tests freeze:

* Root and Session parser action metadata and invocation identities;
* compatibility facade names and callable signatures;
* Legacy patch metadata, default identities, active behavior, and installed
  isolation;
* all seven Root workflow selection and Application execution counts;
* all 12 Session subcommands and representative operation, persistence,
  Checkpoint, and Application counts;
* strict Session JSON failures;
* human, JSON, quiet, provenance, auxiliary export, privacy, Assistant, and EOF
  behavior;
* import-order safety and the prohibition on Application, Public API, Match, and
  observed-Game imports from CLI, including the internal Workspace modules;
* Root presentation isolation from transport and execution dependencies.

Existing distribution checks retain installed/module/Legacy help, version,
Root/Session execution, one Console Script, Wheel/sdist, and clean-install
coverage. Issue #165 adds installed/module Capture help, exact packaged browser
resources, and one in-process create/start/declare/Card/persist/shutdown smoke
flow in the same clean environments. Package version `0.14.0`, seven Root
workflows, 12 Session subcommands, 63 authoritative and packaged Schemas, and 85
generated-output scenarios remain unchanged by Issue #165. The prepared current
Package version is `0.15.0`; the workflow, subcommand, Schema, scenario, and one-
Console-Script baselines remain unchanged.
