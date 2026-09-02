# Advanced CLI automation interface

## Status and identity

Issue #213 implements the private version-1 CLI onboarding and advanced Root
automation boundary:

```text
CLI_ONBOARDING_CONTRACT_VERSION = 1
ADVANCED_ROOT_AUTOMATION_CLI_VERSION = 1
PRODUCT_TOP_LEVEL_HELP_VERSION = 1
```

The exact private policies are:

```text
bare_skatmind_remains_primary_frontend
top_level_help_is_product_oriented
run_is_canonical_root_json_automation
direct_root_options_remain_package_1_x_compatible
run_and_compatibility_share_one_root_implementation
advanced_command_families_remain_explicit
help_and_version_execute_no_product_work
advanced_options_are_grouped_by_user_purpose
task_examples_explain_goal_input_and_output
existing_cli_results_errors_and_exit_codes_remain_stable
```

These values are private Package contracts. They add no Public API export,
Root workflow, Console Script, Schema, persistence format, or Product behavior.

## Product entry and dispatch

Bare SkatMind remains the primary Product entry and opens the complete private
local browser application:

```powershell
skatmind
python -m skatmind
python main.py
```

Leading dispatch is exact and shared by installed, module, and Legacy forms:

```text
empty argv                       -> app
app                              -> app
run                              -> Root automation after removing only run
session                          -> existing Session CLI
capture                          -> existing Capture CLI
corpus                           -> existing Corpus CLI
-h or --help                     -> top-level Product help
--version                        -> Product version
another option-like first token  -> direct Root compatibility
another non-option first token   -> top-level unknown-command usage error
```

Help and version start no browser, create no managed storage, load no input or
Schema, and initialize no workflow handler, Search, replay, Session, Capture, or
Corpus implementation.

## Help layering

The help surfaces have separate purposes:

```text
skatmind --help          Product discovery
skatmind app --help      frontend launch
skatmind run --help      Root JSON automation
skatmind session --help  direct Session automation
skatmind capture --help  direct explicit Match Workspace interface
skatmind corpus --help   direct explicit Learning Corpus interface
```

Top-level help contains, in order, Product introduction, Start here, What the
local application includes, Advanced commands, Common options, and More help.
It lists these Product areas in order:

```text
Analyze a position
Review a completed game
Sessions
Match capture
Learning & cross-game insights
About SkatMind
```

About is identified as the location for version, license, local-operation, and
managed-storage information. The advanced commands are `app`, `run`, `session`,
`capture`, and `corpus`, in that order. Only `-h`, `--help`, and `--version` are
top-level options. Root options are intentionally absent.

## Canonical Root automation

The canonical advanced Root JSON forms are:

```powershell
skatmind run --input REQUEST.json
python -m skatmind run --input REQUEST.json
python main.py run --input REQUEST.json
```

`run` requires an explicit `--input`. `run --help` and `run --version` do not.
The command removes only its leading token and then uses the existing Root
parser, semantic validation, workflow selection, Application adaptation,
transport, presentation, output writer, errors, and Exit Codes exactly once.
It adds no subprocess, temporary file, wrapper Request, wrapper Result, or new
workflow.

The shared Root parser changes only command identity, help structure, examples,
and explicit-input presence in `run` mode. All option names, aliases,
destinations, actions, types, choices, repeatability, defaults, and supplied-
option tracking remain structurally equal to compatibility mode.

## Run help groups

Every Root option appears exactly once under these ordered user-purpose groups:

```text
Input and output
Immediate analysis and reproducibility
Historical review and coaching
Multi-Step simulation and Policy Comparison
Opponent behavior and Profiles
Dataset preparation, evaluation, and statistics
Technical evidence
```

The guide defines a Root JSON request as a portable automation document and
Result JSON as the structured workflow Result. JSON supports automation,
portability, and reproducibility; normal frontend use does not require JSON.

Samples are repeated randomized work. More samples may increase runtime and are
not calibrated probability. A random seed makes randomized work reproducible for
the same request and implementation. Opponent strategies and Policies are fixed
simulation behavior, not learned prediction or hidden truth. Search budgets are
bounded work limits, not quality, completeness, or optimality guarantees.
Provenance is field-origin and information-timing evidence, not Confidence,
correctness, or proof. Quiet mode suppresses successful terminal presentation,
but not errors or requested Result and auxiliary Artifact files.

## Task-oriented examples

### Analyze an exported Position request

Goal: analyze one Position exported from the frontend. Input: a Position Root
JSON request. Result: Position analysis Result JSON.

```powershell
skatmind run --input position-request.json --output position-result.json
```

`--output` is optional and writes the exact Result JSON when supplied.

### Review a completed Historical Game

Goal: evaluate recorded decisions in one completed game. Input: a Historical
Game Root JSON request. Result: Historical Game Result JSON with decision-time
review when available.

```powershell
skatmind run --input historical-game.json --historical-game-review --output historical-result.json
```

`--output` is optional and does not change the review Result.

### Run Multi-Step Policy Comparison

Goal: compare supported local Card Policies over bounded simulated steps. Input:
a Position Root JSON request. Result: Position Result JSON with Multi-Step and
Policy Comparison sections.

```powershell
skatmind run --input position-request.json --multi-step 2 --compare-policies --output comparison-result.json
```

`--output` is optional; `--quiet` may suppress only successful presentation.

### Prepare a Training Dataset

Goal: derive the existing bounded Dataset preparation Result. Input: a Training
Dataset Preparation Root JSON request. Result: a complete or normally unavailable
Preparation Result.

```powershell
skatmind run --input training-dataset-preparation.json --output preparation-result.json
```

`--output` is optional and retains the unchanged Result state.

### Audit Dataset partitions

Goal: inspect stable-player membership and overlap. Input: a Training Dataset
Root JSON request. Result: Dataset partition-audit Result JSON.

```powershell
skatmind run --input training-dataset.json --audit-dataset-partitions --output partition-audit.json
```

`--output` is optional. Normal unavailable Results remain successful.

### Aggregate reusable Opponent Statistics

Goal: derive reusable observed-behavior statistics. Input: a Training Dataset
Root JSON request. Result: aggregation Result JSON and, when requested, a
separate `opponent_statistics_input` Artifact.

```powershell
skatmind run --input training-dataset.json --aggregate-opponent-statistics --output aggregation-result.json --export-opponent-statistics opponent-statistics.json
```

Both output paths are optional. The auxiliary Artifact is written only when
explicitly requested.

Installed and module help uses generic caller-owned files. Legacy help may refer
to repository `examples/`; those examples are not installed Package Data.

## Package-1.x compatibility

The direct forms remain accepted without a warning:

```powershell
skatmind --input REQUEST.json
python -m skatmind --input REQUEST.json
python main.py --input REQUEST.json
```

They preserve the current default input, every other Root option, successful
stdout and stderr, Result JSON, output bytes, quiet behavior, warnings,
Provenance, auxiliary Artifacts, supplied-option tracking, defaults, errors, and
Exit Codes. They are compatibility routes rather than the primary automation
documentation.

Unknown option-like input remains a Root parser error. An unknown non-option
command produces concise invocation-specific top-level usage, points to
top-level help, writes only stderr, emits no traceback, and uses existing usage
Code `2`. No new public error code exists. Normal unavailable Results retain
their existing success behavior.

## Validation and preserved boundaries

Focused tests cover contract identity, dispatch, all three invocation forms,
help order and exclusion, structural parser parity, supplied-option tracking,
explicit input, groups, concepts, examples, errors, import boundaries, and
single Root execution. Representative requests for all seven Root workflows
prove canonical `run` and direct compatibility parity for Exit Code, stdout,
stderr, Result and output bytes, quiet behavior, Provenance, auxiliary Artifacts,
and execution counts.

The existing distribution validator covers Source, Editable, Wheel, sdist, and
clean-install command identities through the supported-platform matrix and local
artifact gates. Package `0.17.0`, Python `>=3.13`, `AGPL-3.0-only`, runtime
dependencies, Public API contract `1`, seven Root workflows, one Console Script,
Settlement Matrix version `3` with 61 cases, 71 Schemas, six Session examples,
98 generated outputs, and ten private Corpus downloads remain unchanged.

Frontend routes, managed workflows, browser security, persistence, Session,
Capture, Corpus, Public API, Root semantics, Schemas, example JSON, and generated
outputs are unchanged by Issue #213.

## UAT state and next action

Issue #213 completes the current CLI onboarding implementation. Repeated UAT-01
then exposed UAT-FINDING-004, and Issue #214 implemented the local browser
Origin-policy remediation. Maintainer Microsoft Edge verification resolved
Issue #214 and UAT-FINDING-004. Repeated UAT-01 nevertheless failed.

```text
Issue #208:
    open

Issue #214:
    resolved

UAT-FINDING-004:
    resolved

Repeated UAT-01:
    failed

UAT-02 through UAT-12:
    paused

B-09:
    open

B-07:
    open

B-06:
    closed

Package 1.0.0:
    not ready
```

Issue #215 freezes the authoritative
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
Issue #216 implements the separate private unified-browser profile/localization
foundation. Existing advanced CLI contracts remain English and unchanged. The
Issue #216 follow-up and both required Ubuntu jobs passed. Issue #217 implements
the separate grouped bilingual Home and Product-concept presentation without
changing this CLI. Issue #218 is the exact next action.
