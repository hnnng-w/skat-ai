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
* Pytest regression coverage
* Ruff checks
* Combined project check script

## Requirements

* Python 3.13 or newer
* PowerShell for helper scripts on Windows
* Development dependencies from `.[dev]`, including:

  * `pytest`
  * `ruff`
  * `jsonschema`

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

## Usage

Show available CLI options and common command examples:

```powershell
python main.py --help
```

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

These workflows accept only `--input`, `--output`, and `--quiet`. Single-list
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
`--output`, and `--quiet` are accepted. Plan data and concise CLI output are
card-free; a complete structured output necessarily retains source cards inside
the nested reusable dataset. See [Automatic dataset preparation
contracts](docs/automatic_dataset_preparation_contracts.md).

Training-dataset inputs form a separate workflow. Only `--input`,
`--output`, and `--quiet` are accepted for normal sample conversion. The same
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

Opponent-statistics inputs form a separate workflow. Only `--input`,
`--output`, and `--quiet` are accepted. Public values use percentage points;
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

The current published stable release is `v0.12.0`, with release theme "Fixed-
three-player historical lists and deterministic dataset preparation" and GitHub
Release title "v0.12.0 — Fixed-three-player historical lists and deterministic
dataset preparation". It points to commit `bbf955e`, validates 70 deterministic
generated-output scenarios, and passes 4,762 pytest tests. The package version is
`0.12.0` and requires Python 3.13 or newer. Issues #127 through #134 complete the
functional milestone, and Issue #135 completed release preparation. Publication
was performed manually by the maintainer, and GitHub Releases remains
authoritative for publication status.

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

Remaining work includes stronger information-set or policy search, tactical
motif detection and cross-game Coaching, approved settlement nuance, additional
dataset-preparation algorithms or overrides, global optimization, guaranteed
ratios, Sample- or Player-count balancing, component splitting, field-level live provenance, interactive input
and session capture, and a stable installed library and CLI interface. General
and specific-trick claims, defender-open-play proof beyond five unresolved
tricks, multiple continuation events, arbitrary event streams, and historical
end reasons outside the supported set remain unsupported. Current
recommendations, opponent policies, and confidence are heuristic; no learned
model or model-training workflow is included. The product supports fixed
three-player tables only; four-player tables are excluded, and complete official
rule coverage is not claimed.

The `v0.12.0` package baseline implements the bounded historical-list source,
aggregation, comparison, and public JSON/CLI workflow from Issues #127 through
#130. Issues #131 through #133 implement the retained preparation contracts and
mode-specific generators; Issue #134 exposes fixed mode dispatch through strict
JSON, schemas, CLI, three examples, and three appended generated-output
scenarios. Issue #135 completed release preparation before manual maintainer
publication. The active next planning milestone is `v0.13.0`, with the
provisional direction of stable API, packaging, and field-level information
provenance; its final issue sequence and architecture are not yet defined.

Current support and known limitations are tracked in the
[requirements traceability matrix](docs/requirements_traceability.md). Product
scope and completion gates are defined in the [v1.0 scope](docs/v1_scope.md).

## Disclaimer

This project is not a full official Skat rules engine, tournament system, general
hidden-information solver, or complete-contract solver.

It is intended as an experimental analysis and simulation tool.
