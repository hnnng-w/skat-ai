# Skat AI

![Check](https://github.com/hnnng-w/skat-ai/actions/workflows/check.yml/badge.svg)

Skat AI is a local Python-based analysis, simulation, and historical-data engine
for Skat positions and supported complete or shortened historical games.

It evaluates legal card choices, estimates expected point swings, recommends cards, tracks game state, simulates multi-step play, and supports post-game review workflows. The project focuses on rule-based and probability-based analysis rather than machine learning.

Skat AI is experimental. It includes bounded late-game Perfect-Information
Minimax for exact worlds, but it is not a general hidden-information or complete-
contract solver, a full official tournament system, or a replacement for
official Skat rules arbitration.

## Features

### Core analysis

* JSON-based Skat position analysis
* Legal-card detection
* Card-point calculation
* Trump and trick-winner logic
* Immediate trick simulation
* Configured opponent response policies for immediate analysis and multi-step candidate completion
* Expected point swing calculation
* Card recommendations
* Optional bounded compatible-world Minimax recommendations for eligible late live positions
* Strict Search and Search-first `auto` routing with explicit Immediate fallback metadata
* Flat post-game bounded Search with an independently executed Immediate baseline
* JSON output for regression-friendly analysis

### Simulation and policy comparison

* Multi-step simulation
* Configurable card-selection policies
* Policy comparison across card-selection strategies
* Opt-in bounded Search or `auto` at every Multi-Step local decision
* Optional five-policy comparison with one configured Search method appended last
* Declared-Ouvert exact public-hand ownership in Immediate Analysis, supported Multi-Step paths, and Policy Comparison
* Opponent lead and response simulation
* Opponent policy presets
* Optional profile-based policy presets
* Separate left/right opponent policy settings
* Left/right opponent policy CLI overrides
* Shared opponent-policy precedence for immediate and multi-step paths
* Basic defender cooperation heuristics
* Exact evidence-constrained hidden-card worlds from confirmed public failures to follow
* Exact compatible-world counts and ownership marginals with privacy-safe confidence summaries

### Game history, scoring, and settlement

* Completed-trick structure validation
* Completed-trick sequence validation
* Completed-trick rule-winner validation
* Explicit and completed-trick point summaries
* Score and game-result summaries
* Game declaration and game-value summaries
* Automatic matador inference from known declarer-card context where possible
* Structured concealed or verbal declarer-concession adjudication under ISkO 4.4.1 and 4.4.2
* Structured defender-concession adjudication under ISkO 4.4.3
* Unanimously accepted declarer-card-exposure adjudication under ISkO 4.4.4
* Continued play with the exact public declarer hand after rejected shortening under ISkO 4.4.4
* Bounded exact defender open-play adjudication under ISkO 4.4.5 for up to five unresolved tricks
* Continued play with the exposing defender's exact returned public hand under ISkO 4.4.5 and 4.1.6
* Legacy claim/concession remaining-point assignment
* Adjusted game-result summaries
* Final single-game settlement summaries
* Supported Suit/Grand overbid settlement
* Bounded impossible Null settlement with an externally supplied Suit or Grand replacement
* Partial fixed-three-player SkWO-style performance rating
* SkWO 6.3.1 shared ranks for unresolved standings ties and optional external lot order
* Public fixed-three-player historical 36-position list aggregation with Played Games, Passed Deals, progression, final standings, and optional external lot application
* Compact comparison of two or more independent completed lists with one reference, final deltas, and resolved-only rank movement
* Versioned complete historical-game records for normal play and five supported shortened terminal events
* Two timed non-terminal historical continuation events with exact public-hand boundaries
* Bounded historical chains with at most one continuation followed by normal completion or one supported terminal shortening
* Full deal, pickup/discard, Hand, ownership, play-order, and follow-rule validation
* Derived historical trick winners, points, game value, overbid, and settlement
* Optional information-safe pre-play snapshots for every actual play in supported historical endings
* Optional decision-time review of those actual historical plays through the existing immediate recommendation logic
* Optional Historical Search Review with per-decision and aggregate Search-versus-Immediate comparisons
* Optional complete Historical Replay Coaching Report with Key Decisions, Turning Points, one-game patterns, actionable recommendations, scope summaries, and separately attached retrospective outcome context
* Versioned training/evaluation dataset records with provenance and explicit train, validation, and test partitions
* Deterministic bounded-Search dataset evaluation over selected decision prefixes
* Optional known-opponent or unseen-player partition policies with deterministic stable-player overlap audits
* Deterministic information-safe samples using the legal historical actual card as the version-1 target
* Versioned external opponent-statistics records with required provenance
* Percentage-point validation and deterministic normalization to existing profile-rate semantics
* Versioned explainable rule-based profile derivation with scoped heuristic confidence
* Exact reusable opponent-statistics aggregation from selected timestamped historical games
* Standalone historical-statistics export compatible with existing live and historical profile loaders
* Strict time-safe historical profile application by stable participant identity
* Rolling known-opponent policy evaluation against the fixed `simple_lowest` baseline

### Information policy

* Live-vs-post-game information enforcement
* Rejection of post-game-only information in live-decision mode
* Information policy summary output
* Rule-authorized all-player public-hand constraints for bounded exposure continuations
* Rule-authorized exact current declarer hands for declared Ouvert
* Private exact defender-open-play proof evidence with only the exposing defender's cards emitted
* Internal version-1 field-level provenance language with immutable sidecar
  ledgers, RFC 6901 paths, deterministic coverage auditing, dependency and
  temporal validation, Information Use Context, public redaction, and safe
  serialization
* Internal version-1 live Position provenance with complete pre-selection
  decision ledgers and Immediate, Search, inference, Multi-Step, Policy
  Comparison propagation
* Internal version-1 retrospective provenance across flat post-game Position
  Analysis, Historical Snapshots, Immediate and Search Review, and Replay
  Coaching
* Internal version-1 Dataset, Preparation, Opponent, Profile, historical-list,
  and independent-list comparison provenance with complete non-legacy Root
  Result ledgers
* Internal version-1 complete Position and Historical Result provenance covering
  Declaration, Value, Overbid, scoring, Results, Settlement, Performance, lists,
  endings, continuations, canonical Historical records, replay, and points
* Opt-in public field-provenance version `1` for one complete redacted Root Result
  plus artifacts actually returned, with recomputed exact-document coverage and
  no consumed-input, decision, intermediate-stage, or unredacted exposure

### Post-game review

* Optional `actual_card_played` input
* Validation that the actual card is valid and legal
* Comparison between actual card and recommended card
* Expected point swing difference
* Decision quality classification:

  * `not_available`
  * `optimal`
  * `acceptable`
  * `suboptimal`
  * `mistake`
* Machine-readable decision factors
* Human-readable decision explanations
* Recommendation gap details:

  * `actual_card_rank`
  * `recommended_card_rank`
  * `candidate_count`
  * `better_card_count`
* Human-readable CLI output for post-game review summaries
* Complete historical-game quality counts and three reconciled player summaries

### Validation

* Input JSON schema validation
* Output JSON schema validation
* Generated-output schema validation for selected examples
* Packaged-schema byte parity and Wheel/sdist clean-install API/CLI validation
* Pytest regression coverage
* Ruff checks
* Combined project check script

### Public Python API contracts

* Stable API contract version `1` under `skat_ai.api.v1`
* Exact seven-value Root `WorkflowV1` contract
* Recursively immutable JSON `RequestDocumentV1` and `ResultDocumentV1` wrappers
* Immutable `ExecutionOptionsV1`, compatibility policy, and API-version metadata
* Stable public errors, error codes, serialization, and CLI Exit Code constants
* Minimal Package-Root exports: `api`, `errors`, and `__version__`
* Internal Application orchestration version `1` with immutable invocations,
  options, results, external documents, and auxiliary artifacts
* Generic no-I/O dispatch for all seven Root workflows, including five isolated
  Training Dataset operations and optional injected Opponent Statistics
* Executable `parse_request`, `execute`, `execute_document`, and
  `serialize_result` facade functions for all seven workflows
* Lazy Package Resource Root input, Root output, and artifact schema validation
  with stable public boundary errors
* Immutable public field-provenance attachments, artifacts, and bundles with
  seven explicit Result mappings and default-false execution opt-in
* Setuptools Wheel and sdist builds with `py.typed`, packaged byte-identical JSON
  Schemas, and clean-install validation

### End-to-end Live and Retrospective Session capture

* Internal Session and Command contract version `1`
* Exactly three stable Players with canonical forehand, middlehand, and rearhand seats
* Live and Retrospective Capture Modes with explicit one-way promotion
* Immutable typed incremental Commands and an authoritative accepted Command Log
* Linear revisions, validation Diagnostics, Position/Historical export readiness,
  and applied/rejected/revision-conflict Result semantics
* Deterministic internal serialization with no generated IDs or timestamps
* Internal transition engine and projection version `1` with canonical revision-
  zero creation, full accepted-Log replay, atomic Command application, monotonic
  phase advancement, and forged-State detection
* Incremental Deal, Declaration, Skat/Discard, Play, trick, continuation,
  Game-end, promotion, information-policy, and readiness validation
* Internal Session Request Export version `1` with normal available/unavailable
  Results and exact one-replay Historical readiness gating
* Exact Retrospective projection mapping through the existing Historical builder,
  canonical serialization and rebuild, and immutable `RequestDocumentV1`
* Internal Position Export Options version `1` and information-safe one-replay
  export to the existing flat Position Analysis `RequestDocumentV1`
* Stable-to-relative Player mapping, decision-visible Matadors, legitimate Skat
  visibility, and declared-Ouvert or continuation public-hand mapping
* Appended `set_public_hand` Command for the exact current declared-Ouvert
  Declarer hand, with owner-aware coexistence and shrinking
* Immutable replay-verified pre-Play Decision Checkpoint version `1` with source
  revision, actor, seat, decision/trick/play indexes, relative map, and frozen
  Position Request
* Internal Session History Edit version `1` with immutable strict-prefix Undo,
  exact removed-suffix reporting, and Mode, phase, Validation, and readiness
  recomputation
* Immutable one-command correction with deterministic original-suffix replay,
  normal partial corrected States at the first rejected later Command, and exact
  replayed/discarded record reporting
* Derived Checkpoint Lineage version `1` with `current`, `ancestor`, `future`, and
  `diverged` relationships from exact accepted-prefix and Position Request
  reconstruction
* Internal Session Persistence version `1` with an authoritative accepted-Log
  State, optional caller-supplied frozen Decision Checkpoints, and recomputed
  lineage on resume
* Domain-separated compact canonical SHA-256 State and complete-content
  fingerprints, including distinct identity for corrected equal-revision Logs
* Strict private-document reconstruction, accepted-Log replay, canonical round
  trips, and State/content fingerprint verification
* Optimistic expected-content-fingerprint `saved`, `unchanged`, and `conflict`
  results plus canonical pretty UTF-8/LF save bytes and same-directory atomic
  replacement
* Stable in-memory `skat_ai.api.v1.session` version-1 namespace with exact
  immutable Session type identity, strict public Command parsing, one-call
  wrappers for twelve operations, and one immutable Result envelope
* Default-omitted, opt-in Session Provenance version `1` with complete exact-
  value coverage, engine-private redaction, and recomputed coverage
* Strict standalone Draft 2020-12 `session.schema.json` mirrored into Package
  Resources, bringing the active authoritative and packaged Schema count to 63
* Stable `skat_ai.api.v1.session.files` version `1` with path-free Save/Load
  Results, strict resume, expected-content-fingerprint compare-and-swap, and
  atomic same-directory replacement
* Immutable Decision Observation version `1` with explicit observed, pending,
  future, diverged, and ended-without-play statuses derived from accepted history
* Frozen-request-plus-observed-Card Checkpoint review export with no later private
  facts and no interpretation of the Card as an optimal label
* Automatic exact Checkpoint collection before accepted local Plays and at
  Position-ready resulting States, with equality deduplication and no automatic
  analysis
* Installed/module/Legacy `session` CLI parity with 12 subcommands for creation,
  status, mutation, history editing, Checkpoints, export, explicit Position and
  Historical execution, review, and the phase-aware Assistant
* Six strict Session examples and eight append-only generated scenarios, bringing
  the `v0.14.0` Package total to 85 while preserving the previous 77

The stable Python Session API exposes creation, Command application, Undo,
correction, both Request exports, Checkpoint construction/classification,
persistence-document construction/resume, Decision Observation, and Checkpoint
review export. Stable public file Save/Load and the end-to-end Session CLI are
implemented. Export-only operations still do not execute workflows; explicit
`analyze`, `review`, and `finalize` invoke the existing Application once when an
export is available. No Session Root workflow exists. Session State itself still
contains no filesystem path or fingerprint; those values belong to the private
persistence envelope and caller-supplied file transport. These capabilities are
part of the published stable `v0.14.0` Release. See
[Public Session API version 1](docs/public_session_api_v1.md),
[Session provenance](docs/session_provenance.md),
[Session Decision observations](docs/session_decision_observations.md),
[Session CLI and end-to-end capture](docs/session_cli_and_end_to_end_capture.md),
[Interactive session contracts](docs/interactive_session_contracts.md),
[Incremental Session transitions](docs/incremental_session_transitions.md),
[Retrospective Session export](docs/retrospective_session_export.md),
[Session Position export and Decision checkpoints](docs/live_session_position_export.md),
[Session Undo, correction, and Checkpoint lineage](docs/session_undo_and_correction.md),
and [Session persistence and resume](docs/session_persistence_and_resume.md).

Session persistence files are private local working data. They may contain
complete retrospective cards and local-private Checkpoint Position Requests,
receive no public redaction, and make no encryption or access-control claim.
Their fingerprints provide deterministic content identity and verification, not
confidentiality or authenticated authorship.

### Match Capture foundation and rapid-entry services

The active `v0.15.0` milestone targets usable manual post-game capture of one
EuroSkat 36er Standard Match from a video source. Issue #160 adds internal
immutable version-1 Match source, media-timecode, tournament-format,
participant, optional Player-statistics snapshot, identity, and perspective
contracts. `euroskat_36_standard_v1` is the only executable format definition
and requires exactly three Players and 36 Games.

The game platform and media source are separate: a Match may have game platform
`EuroSkat` and descriptive source kind `youtube_video`. The source stores the
caller URL, title, optional channel, and optional Match bounds without any
YouTube or EuroSkat integration. The perspective is one observed Match Player,
not the application user. Issue #161 adds internal immutable observed-Game,
chronological Play-trace, free-text Decision commentary, linked later-response,
and derived evidence-summary contracts. Partial traces validate only provable
ownership and legal play; complete traces reconstruct all playable hands and
replay all 30 Decisions. Missing original Skat and Discards remain null.

Issue #163 adds internal persistent EuroSkat 36er Standard Workspaces with
exactly 36 authoritative Slots, existing Dealer and historical-seat rotation,
partial observed Games, explicit passed deals, immutable revisioned changes,
evidence-derived Progress, domain-separated Workspace/content fingerprints,
strict Resume, and optimistic same-directory atomic Save. Structural `complete`
means all Slots are classified, not that all evidence is complete.

Issue #164 adds internal transport-free rapid-entry Application services over an
already loaded Workspace. They derive a UI-ready Position View, rotation,
current Trick, next Player, Play counts, Evidence Summary, and Progress; start
Games with deterministic IDs; update setup evidence; derive Players and Decision
indexes while appending one or more Cards atomically; truncate mistaken Play
suffixes; reconcile free-text commentary and later-response links; and wrap
passed-deal and clear operations. Selectable Cards are exact legal choices only
for an exactly known current perspective hand and otherwise bounded observation
candidates that exclude only proven-unavailable Cards.

Workspace files are private local data and receive no public redaction. The
Capture foundation adds no autosave orchestration, materialization, Public API,
CLI, Schema, example, generated scenario, browser server, or UI.
See [Match capture contracts](docs/match_capture_contracts.md),
[Observed Game capture contracts](docs/observed_game_capture_contracts.md),
[Match Workspace contracts](docs/match_workspace_contracts.md), and
[Match Capture Application services](docs/match_capture_application_services.md).

The facade executes already loaded Root documents without caller transport I/O
and preserves Root JSON output by default. Its lazy schema backend uses packaged
resources and works from source, Editable, Wheel, and sdist installations. Installed CLI
contract version `1` adds the exact `skat-ai` Console Script and
`python -m skat_ai`; repository-root `main.py` remains a compatible Legacy
facade over the same Package implementation. Field-level provenance is
internally enforced and attached for live and retrospective Position and
Historical execution and for Dataset, Preparation, Opponent, Profile, list, and
comparison workflows. All seven Root workflows have complete internal Result
ledgers. Issue #147 additively exposes only the mapped Root Result and actual
artifacts through Public API `include_provenance=True`, Root
`field_provenance`, strict Schema, and CLI `--include-provenance`. Broader end-
to-end field-level enforcement remains incomplete. See
[Public Python API v1](docs/public_python_api_v1.md),
[Application orchestration](docs/application_orchestration.md),
[Complete Result provenance](docs/complete_result_provenance.md), and
[Public field provenance](docs/public_field_provenance.md).

## Requirements

* Python 3.13 or newer
* PowerShell for helper scripts on Windows
* Runtime dependency:

  * `jsonschema`
* Development dependencies from `.[dev]`, including:

  * `build`
  * `pytest`
  * `ruff`

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the combined check script:

```powershell
.\scripts\check.ps1
```

Build one Wheel and one sdist without publishing them:

```powershell
python -m build
```

See [Packaging and distribution](docs/packaging_and_distribution.md) for Package
Data, schema synchronization, clean-install validation, and current boundaries.

The installation exposes both Package CLI forms:

```powershell
skat-ai --help
python -m skat_ai --help
skat-ai session --help
python -m skat_ai session --help
```

See [Installed CLI](docs/installed_cli.md) for invocation identities, output,
errors, compatibility, and clean-install validation. Repository examples are not
installed as Package Data.

The behavior-preserving internal Root and Session transport split, Legacy patch
facades, and one-way import boundary are documented in
[CLI internal architecture](docs/cli_internal_architecture.md).

## Usage

Parse and execute an already loaded Root JSON document:

```python
import json
from pathlib import Path

from skat_ai.api.v1 import ExecutionOptionsV1, execute_document, serialize_result

document = json.loads(Path("examples/grand_second_position.json").read_text())
result = execute_document(
    document,
    options=ExecutionOptionsV1(
        include_provenance=True,
        workflow_options={"sample_count_override": 20},
    ),
)
serialized = serialize_result(result)
```

See [Public API contracts](docs/public_api_contracts.md) for exports,
compatibility, errors, and normal Result states, and
[Public Python API v1](docs/public_python_api_v1.md) for executable facade usage.

Show available CLI options and common command examples:

```powershell
skat-ai --help
python -m skat_ai --help
python main.py --help
```

The first two commands are installed Package interfaces. `python main.py` is the
Legacy repository interface and remains compatible through at least `v1.0.0`.

Create, inspect, and continue one explicit private Session file:

```powershell
skat-ai session new --session session.json --input examples/session_create_live.json
skat-ai session show --session session.json
skat-ai session assistant --session session.json
```

The same `session` family is available through `python -m skat_ai` and
`python main.py`. It has no default path. See
[Session CLI and end-to-end capture](docs/session_cli_and_end_to_end_capture.md)
for all 12 subcommands, options, persistence conflicts, privacy, and Exit Codes.

Run the default analysis from the repository root. This reads the root
`input_position.json` quick-start fixture:

```powershell
python main.py
```

Run analysis with a specific input file:

```powershell
python main.py --input examples/grand_second_position.json
```

Aggregate one complete fixed-three-player historical list or compare independent
completed lists. The JSON root selects the workflow; there is no list-specific
CLI flag:

```powershell
python main.py --input examples/fixed_three_player_historical_list_mixed.json
python main.py --input examples/fixed_three_player_historical_list_all_passed.json
python main.py --input examples/fixed_three_player_historical_list_comparison.json
```

These workflows accept only `--input`, `--output`, `--quiet`, and
`--include-provenance`. Single-list
output retains all 36 privacy-safe progression Entry Facts and final standings.
Comparison output is compact: it retains source summaries and final deltas but no
progression, Historical Game Records, series rollup, ratings, or winner claim.

The existing Immediate expected-value recommendation remains the default. JSON
input may explicitly select `immediate_expected_value`, strict `bounded_search`,
or `auto`. Search methods require a complete `bounded_search_settings` object and
support ongoing `live_decision` positions plus bounded flat
`post_game_review` positions with `actual_card_played`:

```powershell
python main.py --input examples/grand_bounded_search_exhaustive.json
python main.py --input examples/grand_auto_search_fallback.json
python main.py --input examples/grand_bounded_search_post_game_review.json
```

Strict Search never falls back. `auto` runs Immediate only when Search returns a
valid result without a recommendation, and marks fallback only when Immediate
returns a card. Search uses its own required seed; the existing top-level seed
continues to control Immediate and auto fallback. No CLI method override is
provided.

The same configured Search method becomes the local Multi-Step policy when
`--multi-step` is supplied and `--card-policy` is omitted. An explicit
`--card-policy` must match that Search method; a legacy policy conflict, a
strict/auto mismatch, or a Search card policy without matching JSON settings is
rejected. Legacy inputs still default to `first_legal`.

```powershell
python main.py --input examples/grand_bounded_search_exhaustive.json --multi-step 1
python main.py --input examples/grand_bounded_search_exhaustive.json --multi-step 1 --compare-policies
```

Search is rerun from the prepared public state at every local decision. Each
decision receives the full configured budget freshly and a deterministic child
of the explicit Search seed. Search never receives the coherent execution root;
the selected public recommendation is executed separately in that root.

Run Historical Search Review with an explicit Search seed. It uses the immutable
`historical_review_v1` profile by default and runs an independent Immediate
baseline at every decision:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-search-review --search-seed 71 --output outputs/historical-search.json
```

Build the complete public Replay Coaching Report from the same information-safe
decision analysis. Coaching-only output omits the separate Historical Search
Review summary; supplying both flags emits both summaries from one shared pass:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-replay-coaching --search-seed 71 --samples 20 --seed 42 --output outputs/replay-coaching.json
python main.py --input examples/historical_grand_normal_completion.json --historical-search-review --historical-replay-coaching --search-seed 71 --samples 20 --seed 42
```

Evaluate bounded Search against Immediate on the default `validation` and `test`
dataset partitions. `evaluation_v1` is the default profile, and the optional cap
is one stable global decision prefix:

```powershell
python main.py --input examples/training_dataset_normal_play.json --evaluate-bounded-search --search-seed 71 --search-evaluation-max-decisions 10 --output outputs/search-evaluation.json
```

`--search-budget-profile` accepts `interactive_v1`, `historical_review_v1`, or
`evaluation_v1`. These profiles are immutable work budgets, not latency
guarantees. See [Bounded search contracts](docs/bounded_search_contracts.md) and
[Bounded Search performance](docs/bounded_search_performance.md).

Run immediate analysis with a configured opponent response policy:

```powershell
python main.py --input examples/grand_second_position.json --opponent-response-policy highest_point
```

Run a multi-step analysis:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Run the deterministic hidden-card inference example with two Multi-Step decisions:

```powershell
python main.py --input examples/grand_hidden_card_inference.json --multi-step 2
```

Its attributed public Grand history confirms that `right` failed to follow
clubs. The exact root compatible-world count is `275275`, and the generated
scenario also demonstrates later simulated public-evidence progression.

Compare all multi-step local card-selection policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies
```

Print only policy-comparison output, suppressing the normal analysis and
individual multi-step details:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies --comparison-only
```

Run a multi-step analysis with separate left/right opponent policies:

```powershell
python main.py --input examples/grand_left_right_opponent_policies.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-response-policy basic_defender_response
```

Global policy presets and policies cascade to both opponents. Side-specific input fields or CLI overrides win for their side.

Write output to JSON:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Add the bounded public-safe field-provenance sidecar through any supported CLI
form:

```powershell
skat-ai --input examples/grand_second_position.json --include-provenance --output outputs/result.json
python -m skat_ai --input examples/grand_second_position.json --include-provenance --output outputs/result.json
python main.py --input examples/grand_second_position.json --include-provenance --output outputs/result.json
```

Without `--quiet`, all forms append one concise aggregate Field Provenance
section. With `--quiet`, the section is suppressed while the JSON sidecar is
still written.

Suppress successful human-readable stdout output for automation-friendly JSON runs:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json --quiet
```

Without `--quiet`, default CLI behavior is unchanged and successful analysis output is still printed to `stdout`. With `--quiet`, analysis still runs normally and JSON output is still written when `--output` is provided. Expected errors are not suppressed and still go to `stderr`.

Run an overbid example where the declarer wins card points but loses settlement:

```powershell
python main.py --input examples/grand_overbid_declarer_card_points_win.json --output outputs/overbid_test.json
```

Run a structured declarer concession that preserves all unplayed points:

```powershell
python main.py --input examples/declarer_concession.json
```

Run a structured defender concession with joint defender liability and no
remaining-point assignment:

```powershell
python main.py --input examples/defender_concession.json
```

Run a post-game review example with an actual played card:

```powershell
python main.py --input examples/spades_post_game_actual_card_played.json
```

Validate and summarize a complete normally played historical game:

```powershell
python main.py --input examples/historical_grand_normal_completion.json
```

Validate timed continued play after historical defender open play:

```powershell
python main.py --input examples/historical_grand_defender_open_play_continuation.json --historical-decision-snapshots
```

Validate timed continued play after historical declarer-card exposure:

```powershell
python main.py --input examples/historical_grand_declarer_card_exposure_continuation.json --historical-decision-snapshots
```

Validate an exact historical play prefix ending in declarer concession:

```powershell
python main.py --input examples/historical_grand_declarer_concession.json
```

Validate an exact historical prefix ending in joint-liability defender concession:

```powershell
python main.py --input examples/historical_grand_defender_concession.json
```

Validate an exact historical prefix ending in unanimously accepted declarer-card
exposure:

```powershell
python main.py --input examples/historical_grand_declarer_card_exposure.json
```

Add one information-safe snapshot immediately before each actual play:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-decision-snapshots
```

Review all 30 historical decisions with deterministic immediate analysis:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --samples 100 --seed 42
```

Review a complete Grand Ouvert with the exact shrinking declarer hand from
decision 1:

```powershell
python main.py --input examples/historical_grand_ouvert_review.json --historical-game-review --samples 20 --seed 42
```

Apply exact stable-ID external profiles captured strictly before the game:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --opponent-statistics-file examples/historical_opponent_statistics.json --use-profile-presets --samples 20 --seed 42
```

Historical-game inputs form a separate workflow. External profile application
requires `played_at`, historical review, profile-preset opt-in, at least one exact
participant match, and captures strictly older than the game. Live-only relative
binding IDs are rejected. `--samples` and `--seed` are accepted only with review.
Historical declarer and defender concessions, accepted declarer-card exposure,
and terminal defender open play support snapshots, review, time-safe external
profiles, variable training samples, and record/player partition audits for every
actual supplied play. The terminal event is not reviewed or used as a target.
Either timed continuation may precede normal completion or one supported terminal
shortening; only post-event card decisions receive the exact shrinking public
defender or declarer hand, and the terminal action is never a decision target.
Historical opponent statistics, reusable export, rolling profile construction,
and rolling policy evaluation support normal completion and all five shortened
terminal events, including open-card throwing.
Normal-completion event details add no statistic or profile signal.
Each source record has one game of statistics weight, while targets contribute
only actual card decisions, including valid zero-decision targets. See
[Shortened historical opponent workflows](docs/shortened_historical_opponent_workflows.md).

Convert a versioned training/evaluation dataset without running
recommendations or simulation:

```powershell
python main.py --input examples/training_dataset_normal_play.json
```

The variable-length example produces 14 samples from a concession prefix:

```powershell
python main.py --input examples/training_dataset_variable_length.json
```

Audit exact stable-player membership without generating samples:

```powershell
python main.py --input examples/training_dataset_partition_audit.json --audit-dataset-partitions --dataset-partition-mode known_opponent
```

Known-opponent policy permits cross-partition player overlap. Unseen-player
policy enforces player-disjoint partitions. Datasets without policy metadata
remain valid with unspecified intent. See
[Dataset partition policies](docs/dataset_partition_policies.md).

Automatically prepare a reusable partitioned version-1 Training Dataset from
unpartitioned Records:

```powershell
python main.py --input examples/training_dataset_preparation_known_opponent.json
python main.py --input examples/training_dataset_preparation_unseen_player.json
python main.py --input examples/training_dataset_preparation_unavailable.json
```

The root `training_dataset_preparation_input` selects the separate
`training_dataset_preparation` workflow. Mode `known_opponent` dispatches to
`temporal_known_opponent_v1`; mode `unseen_player` dispatches to
`component_balanced_unseen_player_v1`. The request has no algorithm selector,
default weights, CLI overrides, or fallback. A complete Plan materializes a
losslessly reusable existing version-1 `training_dataset_input` and its audit. An
unavailable Plan is still a successful result and returns explicit null dataset
and audit values without partial assignments or summaries. Only `--input`,
`--output`, `--quiet`, and `--include-provenance` are accepted. Plan data and
concise CLI output are
card-free; a complete structured output necessarily retains source cards inside
the nested reusable dataset. See [Automatic dataset preparation
contracts](docs/automatic_dataset_preparation_contracts.md).

Training-dataset inputs form a separate workflow. Only `--input`, `--output`,
`--quiet`, and `--include-provenance` are accepted for normal sample conversion.
The same
input can instead act as the versioned multi-game container for exact historical
opponent-statistics aggregation:

```powershell
python main.py --input examples/training_dataset_normal_play.json --aggregate-opponent-statistics --opponent-statistics-partition train --opponent-statistics-partition validation --opponent-statistics-before 2026-07-21T00:00:00Z --output outputs/historical-statistics.json --export-opponent-statistics outputs/opponent-statistics.json
```

Aggregation requires `played_at` on every partition-selected game, uses a strict
exclusive cutoff, derives wins from final settlement, emits no decision samples,
and does not apply a policy. See
[Historical opponent statistics](docs/historical_opponent_statistics.md).

The mixed normal/concession example supports aggregation and export with the
same commands:

```powershell
python main.py --input examples/training_dataset_shortened_opponent_workflows.json --aggregate-opponent-statistics
```

Evaluate rolling game-start profiles against observed known-opponent card choices:

```powershell
python main.py --input examples/historical_opponent_policy_evaluation_dataset.json --evaluate-opponent-policy-profiles --output outputs/opponent-policy-evaluation.json
```

Use `--evaluate-rolling-opponent-policies` with
`examples/training_dataset_shortened_opponent_workflows.json` to evaluate its
14-decision concession target against two strictly earlier source games.

This workflow uses disjoint source and evaluation partition names, strict as-of
history, and preferred-card matching. It measures behavioral imitation only, not
strategic quality or optimal play. See
[Rolling opponent-policy evaluation](docs/opponent_policy_evaluation.md).

Validate, normalize, and derive an explainable profile from externally supplied
opponent statistics:

```powershell
python main.py --input examples/opponent_statistics.json
```

Opponent-statistics inputs form a separate workflow. Only `--input`, `--output`,
`--quiet`, and `--include-provenance` are accepted. Public values use percentage
points;
canonical profile rates use `0..1`. When optional exact counts are absent, they
are not inferred; role evidence may instead be exposed as an unrounded estimate.
The standalone conversion does not run analysis.

Attach the same validated statistics file to a live position with exact,
case-sensitive left/right player IDs:

```powershell
python main.py --input examples/grand_second_position.json --opponent-statistics-file examples/opponent_statistics.json --left-opponent-player-id opponent-123 --right-opponent-player-id opponent-789 --use-profile-presets --samples 20 --seed 42
```

Either side may be bound. Only confidence-gated actionable presets affect the
existing side-specific live policy path. Manual side profiles and existing
explicit policy settings retain precedence. See
[Live opponent profiles](docs/live_opponent_profiles.md) and
[Historical opponent profiles](docs/historical_opponent_profiles.md).

CLI exit codes:

* `0` = success
* `1` = expected input, runtime, or output failure
* `2` = invalid CLI usage

Expected errors are written to `stderr`. Successful analysis output remains on `stdout`.

For a concise walkthrough of common CLI workflows, see [Examples documentation](docs/examples.md#workflow-walkthroughs).

## Documentation

Detailed documentation is split into topic-specific files:

* [Input JSON](docs/input_json.md)
* [Public API contracts](docs/public_api_contracts.md)
* [Public Python API v1](docs/public_python_api_v1.md)
* [Public Session API version 1](docs/public_session_api_v1.md)
* [Session provenance](docs/session_provenance.md)
* [Session Decision observations](docs/session_decision_observations.md)
* [Session CLI and end-to-end capture](docs/session_cli_and_end_to_end_capture.md)
* [Installed CLI](docs/installed_cli.md)
* [CLI internal architecture](docs/cli_internal_architecture.md)
* [Packaging and distribution](docs/packaging_and_distribution.md)
* [Application orchestration](docs/application_orchestration.md)
* [Interactive session contracts](docs/interactive_session_contracts.md)
* [Match capture contracts](docs/match_capture_contracts.md)
* [Observed Game capture contracts](docs/observed_game_capture_contracts.md)
* [Match Workspace contracts](docs/match_workspace_contracts.md)
* [Match Capture Application services](docs/match_capture_application_services.md)
* [Incremental Session transitions](docs/incremental_session_transitions.md)
* [Retrospective Session export](docs/retrospective_session_export.md)
* [Session Position export and Decision checkpoints](docs/live_session_position_export.md)
* [Session Undo, correction, and Checkpoint lineage](docs/session_undo_and_correction.md)
* [Session persistence and resume](docs/session_persistence_and_resume.md)
* [Field-level information provenance](docs/field_level_information_provenance.md)
* [Public field provenance](docs/public_field_provenance.md)
* [Live analysis provenance](docs/live_analysis_provenance.md)
* [Retrospective review provenance](docs/retrospective_review_provenance.md)
* [Dataset, list, and opponent provenance](docs/dataset_list_and_opponent_provenance.md)
* [Complete Result provenance](docs/complete_result_provenance.md)
* [Input JSON schema](schemas/input.schema.json)
* [Declarer concessions](docs/declarer_concessions.md)
* [Defender concessions](docs/defender_concessions.md)
* [Accepted declarer card exposure](docs/declarer_card_exposure.md)
* [Declarer card exposure continuation](docs/declarer_card_exposure_continuation.md)
* [Defender open play](docs/defender_open_play.md)
* [Defender open play continuation](docs/defender_open_play_continuation.md)
* [Open card throw](docs/open_card_throw.md)
* [Game-shortening input schema](schemas/game_shortening.schema.json)
* [Game-continuation input schema](schemas/game_continuation.schema.json)
* [Declarer-concession output schema](schemas/declarer_concession_output.schema.json)
* [Defender-concession output schema](schemas/defender_concession_output.schema.json)
* [Declarer-card-exposure output schema](schemas/declarer_card_exposure_output.schema.json)
* [Declarer-card-exposure continuation output schema](schemas/declarer_card_exposure_continuation_output.schema.json)
* [Defender-open-play input schema](schemas/defender_open_play.schema.json)
* [Defender-open-play output schema](schemas/defender_open_play_output.schema.json)
* [Defender-open-play continuation input schema](schemas/defender_open_play_continuation.schema.json)
* [Defender-open-play continuation output schema](schemas/defender_open_play_continuation_output.schema.json)
* [Open-card-throw input schema](schemas/open_card_throw.schema.json)
* [Open-card-throw output schema](schemas/open_card_throw_output.schema.json)
* [Theoretical-level assessment schema](schemas/theoretical_level_assessment.schema.json)
* [Exact rest-trick proof schema](schemas/exact_rest_trick_proof.schema.json)
* [Public-hand constraint schema](schemas/public_hand_constraint.schema.json)
* [Historical games](docs/historical_games.md)
* [Historical declarer card exposure](docs/historical_declarer_card_exposure.md)
* [Historical declarer-card-exposure continuation](docs/historical_declarer_card_exposure_continuation.md)
* [Historical defender open play](docs/historical_defender_open_play.md)
* [Historical open card throw](docs/historical_open_card_throw.md)
* [Historical defender open-play continuation](docs/historical_defender_open_play_continuation.md)
* [Historical decision snapshots](docs/historical_decision_snapshots.md)
* [Historical game review](docs/historical_game_review.md)
* [Replay coaching contracts](docs/replay_coaching_contracts.md)
* [Ouvert-aware simulation](docs/ouvert_aware_simulation.md)
* [Coherent hidden-world simulation](docs/coherent_hidden_world_simulation.md)
* [Hidden-card inference](docs/hidden_card_inference.md)
* [Bounded search contracts](docs/bounded_search_contracts.md)
* [Bounded Search performance](docs/bounded_search_performance.md)
* [Bounded Search post-game review schema](schemas/bounded_search_post_game_review.schema.json)
* [Historical Search Review schema](schemas/historical_search_review.schema.json)
* [Historical Replay Coaching schema](schemas/historical_replay_coaching.schema.json)
* [Bounded Search evaluation schema](schemas/bounded_search_evaluation.schema.json)
* [Hidden-card inference summary schema](schemas/hidden_card_inference_summary.schema.json)
* [Historical opponent profiles](docs/historical_opponent_profiles.md)
* [Training data](docs/training_data.md)
* [Dataset partition policies](docs/dataset_partition_policies.md)
* [Automatic dataset preparation contracts](docs/automatic_dataset_preparation_contracts.md)
* [Temporal Known-opponent dataset splits](docs/temporal_known_opponent_dataset_splits.md)
* [Player-disjoint unseen-player dataset splits](docs/player_disjoint_unseen_player_dataset_splits.md)
* [Opponent statistics](docs/opponent_statistics.md)
* [Historical opponent statistics](docs/historical_opponent_statistics.md)
* [Rolling opponent-policy evaluation](docs/opponent_policy_evaluation.md)
* [Shortened historical opponent workflows](docs/shortened_historical_opponent_workflows.md)
* [Fixed-three-player historical-list contracts](docs/fixed_three_player_36_game_list_contracts.md)
* [Fixed-three-player historical-list aggregation](docs/fixed_three_player_36_game_list_aggregation.md)
* [Fixed-three-player historical-list comparison](docs/fixed_three_player_36_game_list_comparison.md)
* [Opponent profile derivation](docs/opponent_profile_derivation.md)
* [Live opponent profiles](docs/live_opponent_profiles.md)
* [Historical-game schema](schemas/historical_game.schema.json)
* [Historical defender-open-play input schema](schemas/historical_defender_open_play.schema.json)
* [Historical defender-open-play output schema](schemas/historical_defender_open_play_output.schema.json)
* [Historical open-card-throw input schema](schemas/historical_open_card_throw.schema.json)
* [Historical open-card-throw output schema](schemas/historical_open_card_throw_output.schema.json)
* [Historical game-event schema](schemas/historical_game_event.schema.json)
* [Historical declarer-card-exposure continuation event schema](schemas/historical_declarer_card_exposure_continuation_event.schema.json)
* [Historical declarer-card-exposure continuation output schema](schemas/historical_declarer_card_exposure_continuation_event_output.schema.json)
* [Historical defender-open-play continuation event schema](schemas/historical_defender_open_play_continuation_event.schema.json)
* [Historical game-events output schema](schemas/historical_game_events_output.schema.json)
* [Historical decision snapshot schema](schemas/historical_decision_snapshot.schema.json)
* [Historical game review schema](schemas/historical_game_review.schema.json)
* [Historical opponent profile application schema](schemas/historical_opponent_profile_application.schema.json)
* [Training dataset input schema](schemas/training_dataset.schema.json)
* [Training dataset output schema](schemas/training_dataset_output.schema.json)
* [Dataset partition policy schema](schemas/dataset_partition_policy.schema.json)
* [Dataset partition audit schema](schemas/dataset_partition_audit.schema.json)
* [Training Dataset preparation input schema](schemas/training_dataset_preparation.schema.json)
* [Dataset partition Plan schema](schemas/dataset_partition_plan.schema.json)
* [Training Dataset preparation output schema](schemas/training_dataset_preparation_output.schema.json)
* [Opponent statistics input schema](schemas/opponent_statistics.schema.json)
* [Opponent statistics output schema](schemas/opponent_statistics_output.schema.json)
* [Historical opponent statistics aggregation schema](schemas/historical_opponent_statistics_aggregation.schema.json)
* [Rolling opponent-policy evaluation schema](schemas/rolling_opponent_policy_evaluation.schema.json)
* [Fixed-three-player historical-list schema](schemas/fixed_three_player_historical_list.schema.json)
* [Fixed-three-player historical-list request schema](schemas/fixed_three_player_historical_list_input.schema.json)
* [Fixed-three-player historical-list comparison request schema](schemas/fixed_three_player_historical_list_comparison_input.schema.json)
* [Fixed-three-player historical-list aggregation schema](schemas/fixed_three_player_historical_list_aggregation.schema.json)
* [Fixed-three-player historical-list comparison schema](schemas/fixed_three_player_historical_list_comparison.schema.json)
* [Opponent profile derivation schema](schemas/opponent_profile_derivation.schema.json)
* [Live opponent profile application schema](schemas/opponent_profile_application.schema.json)
* [Output JSON](docs/output_json.md)
* [Output JSON schema](schemas/output.schema.json)
* [Schema validation](docs/schema_validation.md)
* [Scoring and settlement](docs/scoring.md)
* [Game-end handling](docs/game_end.md)
* [Overbid handling](docs/overbid.md)
* [Performance rating](docs/performance_rating.md)
* [Examples](docs/examples.md)
* [Architecture](docs/architecture.md)
* [Requirements traceability](docs/requirements_traceability.md)
* [v1.0 scope](docs/v1_scope.md)
* [Roadmap](docs/roadmap.md)
* [Project handoff](docs/project_handoff.md)

## Development

Run all checks:

```powershell
.\scripts\check.ps1
```

Run tests directly:

```powershell
python -m pytest
```

Run Ruff checks:

```powershell
python -m ruff check .
```

Apply Ruff fixes and format code:

```powershell
.\scripts\format.ps1
```

The test suite also validates JSON files in `examples/`. If an example contains invalid cards, duplicate known cards, inconsistent completed-trick metadata, invalid game-end metadata, invalid information-policy metadata, or invalid simulation settings, the tests will fail.

## Project status

The current published stable GitHub Release is `v0.14.0`, with release theme
"End-to-end Live and Retrospective Session capture" and GitHub Release title
"v0.14.0 — End-to-end Live and Retrospective Session capture". It points to
commit `d5589f8`. Package version `0.14.0` requires Python 3.13 or newer, retains
Public API contract version `1` and exactly seven Root workflows, contains 63
authoritative Schemas and 63 Packaged Schema Resources, includes six Session
examples, validates 85 deterministic generated-output scenarios, and passes
5,892 pytest tests. Issues #150 through #157 complete the functional milestone,
and Issue #158 completed Release preparation. Publication was performed manually
by the maintainer. GitHub Releases remains authoritative for publication status;
no Package-index or PyPI publication is claimed.

The active development milestone is `v0.15.0`, targeting usable manual
post-game capture of one EuroSkat 36er Standard Match from descriptive video
evidence. Issue #160 provides the internal immutable Match identity and metadata
foundation. Issue #161 adds internal evidence-aware observed Games, partial and
complete Play validation, free-text Decision commentary on any Player, linked
later responses, and deterministic evidence summaries. Issue #163 adds persistent
internal 36-position Workspaces, exact rotation, passed deals, Progress,
fingerprints, strict Resume, and optimistic atomic Save. Issue #164 adds the
internal transport-free rapid-entry Application foundation, including derived
Position Views, setup updates, automatic Player/Decision append, truncation, and
annotation editing. Materialization, autosave orchestration, Public API, CLI,
Schema, browser transport, and UI remain later milestone work. Package
version, Public APIs, seven Root workflows, 63 Schemas, and 85 generated outputs
remain unchanged.

The historical published `v0.13.0` release has release theme "Stable API,
installable tooling, and public field provenance" and GitHub Release title
"v0.13.0 — Stable API, installable tooling, and public field provenance". It
points to commit `abd1ad3`, contains 62 authoritative Schemas and 62 Packaged
Schema Resources, validates 77 deterministic generated-output scenarios, and
passes 5,399 pytest tests. Issues #137 through #147 complete its functional
milestone, Issue #148 completed Release preparation, and Issue #149 synchronized
its publication status.

The historical published `v0.12.0` release has release theme
"Fixed-three-player historical lists and deterministic dataset preparation" and
GitHub Release title
"v0.12.0 — Fixed-three-player historical lists and deterministic dataset
preparation". It points to commit `bbf955e`, validates 70 deterministic
generated-output scenarios, and passes 4,762 pytest tests. Issues #127 through
#134 complete the functional milestone, and Issue #135 completed release
preparation. Issue #136 synchronized the historical publication status.

The historical published `v0.11.0` release, with release theme "Information-safe
Replay Coaching and structured historical outcomes", points to commit `cfd28e5`,
validates 64 deterministic generated-output scenarios, and passes 4,392 pytest
tests. Issues #118 through #124 complete that functional milestone, and Issue
#125 completed release preparation.

The historical published `v0.10.0` release points to commit `b4c8738`, validates
59 deterministic generated-output scenarios, and passes 4,075 pytest tests.

The historical `v0.11.0` package baseline adds an immutable 61-case normative settlement
matrix and the bounded historical sequence of at most one continuation followed
by normal completion or one supported terminal shortening. Existing terminal
adjudicators remain authoritative. Direct, bounded, compatibility-only legacy,
undecided, and excluded scopes are explicit. Current structured endings include
declarer and defender concessions, accepted declarer-card exposure, bounded
defender open play, and open-card throwing. Defender-open-play proof remains
bounded to five unresolved tricks, and open-card-throw exclusion remains jack-
only. General claims, specific-trick claims, generalized correction, broader
settlement, and complete official-rule coverage remain incomplete.

Replay Coaching builds decision-time evidence before attaching the observed card
as retrospective evidence rather than ground truth. Search-first impact follows
Contract success, settlement score, then Suit/Grand card-point margin; Null has no
margin objective. Forced and aggregate-equivalent decisions are non-errors, and
Immediate-only evidence remains explicitly bounded to one-trick analysis.
Deterministic Key Decisions, separate decision-opportunity and recorded-outcome
Turning Points, two-occurrence one-game patterns, and deterministic decision and
pattern recommendations make no tactical, causal, psychological, skill, or
statistical-significance claims.

The opt-in historical-game command `--historical-replay-coaching` emits the full
`historical_replay_coaching_summary`, validated by
`historical_replay_coaching.schema.json`. It reuses `--search-seed`,
`--search-budget-profile`, `--samples`, and `--seed`, and can run alone or in one
pass with Historical Search Review. JSON retains the complete report while CLI
output stays concise; `--quiet` behavior is unchanged. Three deterministic public
scenarios cover normal Grand, Null, and a shortened chain.

Final outcome context describes how the recorded game ended. It is not decision-
time evidence and does not change Coaching classification. Public Coaching output
does not expose hands, final hidden ownership, Skat identities, discards,
compatible-world identities or contents, private Search states, derived seeds,
caches, branches, principal variations, ratings, or rankings. Aggregate world
counts and coverage remain privacy-safe evidence metadata. Player, role, phase,
and contract summaries are descriptive counts, not rankings.

The published `v0.10.0` milestone adds five structured game-shortening forms,
five matching historical terminal events, two historical non-terminal continuations, and
variable-length decision snapshots, Historical Review, training samples, and
shortened-game opponent workflows. Declared-Ouvert decisions use exact public
declarer ownership in supported recommendation paths. See
[Historical games](docs/historical_games.md),
[Historical game review](docs/historical_game_review.md), and
[Shortened historical opponent workflows](docs/shortened_historical_opponent_workflows.md).

Multi-Step preserves one coherent hypothetical hidden world per path, while
Policy Comparison gives independent path copies of one shared root. Exact
evidence-constrained inference counts and samples uniformly weighted labeled
assignments compatible with public ownership and confirmed failure-to-follow
evidence. These worlds do not prove the real deal, and confidence is not
calibrated. See
[Coherent hidden-world simulation](docs/coherent_hidden_world_simulation.md) and
[Hidden-card inference](docs/hidden_card_inference.md).

Bounded Search supports flat post-game comparison, Historical Search Review,
and deterministic Search-versus-Immediate dataset evaluation with immutable
named work profiles. Independent Suit, Grand, and Null fixtures demonstrate
strict improvements and 32/64/128-draw convergence against exhaustive references.
It provides exact compatible-world counts, canonical enumeration, deterministic
uniform IID sampling with replacement and retained duplicate weighting, and
common completed-world-prefix aggregation. Exhaustive results are exact across
all compatible worlds; sampled and partial exactness claims are limited to their
selected draws or completed prefix.

Search remains bounded late-game determinization with a five-remaining-trick
implementation maximum. It is subject to Strategy Fusion, is not an optimal
imperfect-information policy or complete-contract Search, and exact compatible-
world counts do not identify the real deal. Sampled ownership quality is not
calibrated probability. Benchmark timings are reference measurements rather than
cross-machine guarantees, and wall-clock timeout activation is machine-
dependent. Overbid Null remains outside normal Search when no external
replacement is available. Immediate remains the omitted default and Search is
opt-in, so existing omitted-method workflows require no migration.

Remaining work includes observed Match Games, annotations, persistence, Public
Match interfaces and UI; stronger information-set or policy search, tactical
motif detection and cross-game Coaching, approved settlement nuance, additional
dataset-preparation algorithms or overrides, global optimization, guaranteed
ratios, Sample- or Player-count balancing, component splitting, broader field-
level provenance enforcement, and GUI/browser or online-platform Session
integration beyond the completed local end-to-end Issue #150 through #157
capture milestone. General
and specific-trick claims, defender-open-play proof beyond five unresolved
tricks, multiple continuation events, arbitrary event streams, and historical
end reasons outside the supported set remain unsupported. Current
recommendations, opponent policies, and confidence are heuristic; no learned
model or model-training workflow is included. The product supports fixed
three-player tables only; four-player tables are excluded, and complete official
rule coverage is not claimed.

The published `v0.12.0` package baseline implements the bounded historical-list
source, aggregation, comparison, and public JSON/CLI workflow from Issues #127 through
#130. Issues #131 through #133 implement the retained preparation contracts and
mode-specific generators; Issue #134 exposes fixed mode dispatch through strict
JSON, schemas, CLI, three examples, and three appended generated-output
scenarios. Issue #135 completed release preparation before manual maintainer
publication. Issue #137 is the first implemented `v0.13.0` foundation: it adds
API contract version `1`, exact public exports, immutable JSON Request and Result
wrappers, compatibility metadata, stable public errors, and unchanged legacy
Root CLI behavior. Issue #138 adds the internal version-1 field-provenance
contract foundation with RFC 6901 paths, immutable sidecar ledgers, coverage,
dependency, context-use, redaction, and serialization contracts. Issue #139 adds
internal all-seven-workflow Application orchestration. Issue #140 adds the
executable public facade, direct immutable options, public results and artifacts,
lazy schema validation, and stable boundary errors. Issue #141 adds explicit
Setuptools build metadata, byte-identical packaged Schema resources, `py.typed`,
Package `__version__`, Wheel/sdist inspection, and clean installation gates.
Issue #142 adds installed CLI contract version `1`, the exact `skat-ai` Console
Script, `python -m skat_ai`, a Package-owned canonical implementation, Legacy
Root compatibility, and clean-install CLI/API parity. Issue #143 adds internal
live Position provenance enforcement across Immediate, Search, Hidden-card
inference, Multi-Step, and Policy Comparison while preserving every public
surface. Issue #144 extends the same internal sidecars through flat
retrospective Position Analysis, Historical Snapshots and Review, Historical
Search Review, Replay Coaching, and selected partial-legacy Result branches.
Issue #145 propagates complete internal field provenance through all five
Training Dataset operations, automatic Dataset Preparation, Opponent Statistics
and Profiles, fixed-three-player list aggregation, and independent-list
comparison, with complete non-legacy Root ledgers. Complete non-legacy Position
and base Historical Result ledgers are completed by Issue #146 from retained
workflow values, including scoring, Settlement, endings, Historical replay, and
private-proof-safe dependencies. Issue #147 adds public field-provenance contract
version `1`, immutable public attachments/artifacts/bundles, seven explicit Root
Result mappings, one actual-artifact mapping, opt-in Public API and all-three-
form CLI transport, strict `field_provenance.schema.json`, and seven append-only
generated-output scenarios. The published `v0.13.0` release matrix has 77
scenarios and 62 schemas. Together, Issues #137 through #147 define the
published baseline with 77 scenarios and 62 schemas; the historical published
`v0.12.0` facts remain 70 scenarios and 4,762 pytest tests. Issue #148 completed Release preparation before
manual maintainer publication at commit `abd1ad3`. Broader end-to-end field-level
enforcement remains incomplete before `v1.0.0`.

The published `v0.14.0` milestone begins with Issue #150's immutable internal
Session contract foundation, Issue #151's deterministic transition engine,
Issue #152's canonical Retrospective Historical Request export, and Issue #153's
information-safe Position Request export and Decision Checkpoints. Issue #154
adds deterministic strict-prefix Undo, one-command correction, suffix replay,
partial corrected States, and Checkpoint lineage. Issue #155 adds private
internal Session Persistence version `1`, strict reconstruction/replay and
fingerprint verification, caller-supplied frozen Checkpoint retention with
recomputed lineage, optimistic expected-content-fingerprint writes, and canonical
atomic local file replacement.
Issue #156 adds the stable `skat_ai.api.v1.session` namespace, exact immutable
contract exports, all ten in-memory operations, public Command parsing, the
Session Result envelope, optional complete Session Provenance, strict standalone
Session Schema, 63-Schema Package Resource parity, and clean-install validation.
Session and Command version `1`, transition and projection version `1`, stable
Players, Capture Modes, typed Commands, an authoritative accepted Log, full
replay, atomic application, monotonic phases, incremental validation, Diagnostics,
export readiness, immutable export Results, exact Historical and information-safe
Position mapping, declared-Ouvert public-hand capture, canonical Request
construction, frozen local pre-Play Checkpoints, and internal history editing now
exist. Private file persistence and public in-memory persistence construction and
strict resume also exist. Issue #157 adds the stable public Session file
namespace, accepted-Log Decision Observation and isolated Checkpoint review
export, automatic exact Checkpoint collection, all 12 installed/module/Legacy
Session subcommands, explicit Position/Historical execution, the phase-aware
Assistant, six examples, and eight append-only scenarios for a total of 85.
Issue #158 completed Package version `0.14.0` and Release-documentation
preparation under the release theme "End-to-end Live and Retrospective Session
capture" without changing product behavior. The maintainer subsequently
published `v0.14.0` at commit `d5589f8`; its baseline has 63 Schemas, six Session
examples, 85 generated outputs, and 5,892 passing pytest tests. The historical
published `v0.13.0` baseline remains 62 Schemas and 77 scenarios. GUI/browser
UI, online-platform adapters, browser
extensions, website scraping, cloud synchronization, distributed locking,
encryption/key management, automatic backups, and unrelated pre-v1 gaps remain
open.

The active milestone is `v0.15.0` for usable EuroSkat 36er Standard post-game
capture. Issue #160 establishes internal Match metadata, and Issue #161 adds
internal evidence-aware observed Games and free-text Decision commentary. Issue
#163 adds private persistent Workspaces, and Issue #164 adds transport-free rapid
entry over those Workspaces. Public Match API, Schema, CLI, browser transport and
UI, Player Statistics application, and materialization remain open.
`v1.0.0` remains unready after this milestone; its final Issue sequence and
implementation architecture still require focused scope and traceability review.

Current support and known limitations are tracked in the
[requirements traceability matrix](docs/requirements_traceability.md). Product
scope and completion gates are defined in the [v1.0 scope](docs/v1_scope.md).

## Disclaimer

This project is not a full official Skat rules engine, tournament system, general
hidden-information solver, or complete-contract solver.

It is intended as an experimental analysis and simulation tool.
