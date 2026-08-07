# Input JSON

This document describes the supported input JSON format for `skat-ai`.

## JSON schema

The input JSON schema is available at:

[`schemas/input.schema.json`](../schemas/input.schema.json)

Structured game shortening uses:

[`schemas/game_shortening.schema.json`](../schemas/game_shortening.schema.json)

Defender open play additionally uses:

[`schemas/defender_open_play.schema.json`](../schemas/defender_open_play.schema.json)

Open card throw additionally uses:

[`schemas/open_card_throw.schema.json`](../schemas/open_card_throw.schema.json)

Supported historical records use the focused referenced schemas:

[`schemas/historical_game.schema.json`](../schemas/historical_game.schema.json)

[`schemas/historical_game_end.schema.json`](../schemas/historical_game_end.schema.json)

[`schemas/historical_game_event.schema.json`](../schemas/historical_game_event.schema.json)
and
[`schemas/historical_declarer_card_exposure_continuation_event.schema.json`](../schemas/historical_declarer_card_exposure_continuation_event.schema.json)
and
[`schemas/historical_defender_open_play_continuation_event.schema.json`](../schemas/historical_defender_open_play_continuation_event.schema.json)

[`schemas/historical_declarer_concession.schema.json`](../schemas/historical_declarer_concession.schema.json)
and
[`schemas/historical_defender_concession.schema.json`](../schemas/historical_defender_concession.schema.json)

[`schemas/historical_declarer_card_exposure.schema.json`](../schemas/historical_declarer_card_exposure.schema.json)

[`schemas/historical_defender_open_play.schema.json`](../schemas/historical_defender_open_play.schema.json)

[`schemas/historical_open_card_throw.schema.json`](../schemas/historical_open_card_throw.schema.json)

Training/evaluation datasets use:

[`schemas/training_dataset.schema.json`](../schemas/training_dataset.schema.json)

Automatic Training Dataset preparation uses:

[`schemas/training_dataset_preparation.schema.json`](../schemas/training_dataset_preparation.schema.json)

Optional partition policy uses
[`schemas/dataset_partition_policy.schema.json`](../schemas/dataset_partition_policy.schema.json).

External opponent-statistics records use:

[`schemas/opponent_statistics.schema.json`](../schemas/opponent_statistics.schema.json)

Fixed-three-player historical 36-position lists and requests use:

[`schemas/fixed_three_player_historical_list.schema.json`](../schemas/fixed_three_player_historical_list.schema.json)

[`schemas/fixed_three_player_historical_list_input.schema.json`](../schemas/fixed_three_player_historical_list_input.schema.json)

Independent-list comparison requests use:

[`schemas/fixed_three_player_historical_list_comparison_input.schema.json`](../schemas/fixed_three_player_historical_list_comparison_input.schema.json)

The schema is intended as a documentation and validation aid.

Example files can be validated against the schema with:

```powershell
python scripts/validate_examples_schema.py
```

The project check script also runs input schema validation:

```powershell
.\scripts\check.ps1
```

The schema checks stable structural constraints such as:

* valid card notation
* maximum hand size
* maximum skat size
* maximum current-trick size
* maximum opponent hand sizes and sample count
* required array/object shapes for supplied public fields
* unique cards within individual card arrays
* card-point fields between 0 and 120
* supported analysis metadata values
* supported game-end metadata values
* supported player profile field types and numeric ranges
* supported opponent policy values
* supported performance rating values
* matador values from 1 through 11 and direct top-level Grand values through 4
* direct top-level Suit/Grand declaration contradictions
* strict version-1 declarer-concession, defender-concession, declarer-card-exposure, defender-open-play, and open-card-throw union shapes

More advanced cross-field validation is handled by the Python validation layer.

Python validation covers Skat-specific rules such as:

* duplicate known cards across all known-card lists
* completed-trick sequence consistency
* completed-trick winner validation where enough metadata is available
* live-vs-post-game information rules
* game-end consistency
* declarer-concession consent and hand-count reconciliation
* defender-concession concrete party membership, joint liability, decision state, and mandatory-level feasibility
* structured game-shortening exclusivity, incomplete-play, and settlement prerequisites
* legality of `actual_card_played`
* point consistency
* stable historical player/seat references and complete 32-card deals
* historical pickup/discard ownership, final playable hands, all normal plays or an exact shortened prefix, follow obligations, winners, points, matadors, and settlement
* training dataset versions, optional partition policy, unpadded identities, RFC 3339 provenance, duplicate game/source detection, partition leakage, and declared unseen-player disjointness
* automatic preparation version, unpartitioned Records, positive explicit partition weights, mode-specific requirements, and duplicate source identities
* opponent-statistics identity/provenance, finite percentages, rounded-value consistency, zero-role rules, optional exact-count reconciliation, historical aggregation provenance, and duplicate player IDs
* historical opponent-statistics canonical partition selection, required source timestamps, strict cutoff, stable identity/label aggregation, and settlement-based exact counts
* historical-list identities, canonical table places, exactly 36 rotating positions, chronology, settlement-derived contributions, lot applicability, and independent comparison-source reconciliation

For the validation-layer overview and schema limitations, see:

[Schema validation documentation](schema_validation.md)

## Input workflows

The public schema has seven mutually exclusive branches:

* the existing flat position-analysis input described below
* a normal-completion or explicitly supported shortened historical game under `historical_game_input`
* a versioned training/evaluation dataset under `training_dataset_input`
* an automatic Training Dataset preparation request under `training_dataset_preparation_input`
* versioned external opponent statistics under `opponent_statistics_input`
* one complete fixed-three-player historical list under `fixed_three_player_historical_list_input`
* two or more independent complete lists under `fixed_three_player_historical_list_comparison_input`

A historical-game file contains no position fields, simulation settings,
`actual_card_played`, profiles, policies, list inputs, or impossible-Null
settlement selection:

```json
{
  "historical_game_input": {
    "schema_version": 1,
    "game_id": "game-001",
    "players": [],
    "skat": [],
    "declarer_player_id": "player-a",
    "declaration": {},
    "discarded_cards": [],
    "game_end_reason": "normal_completion",
    "tricks": []
  }
}
```

See [Historical games](historical_games.md) for the complete identity, deal,
declaration, skat, play, and runtime-validation contract.
Historical declarer concession adds a required version-1 `game_end` object with
stable defender consent IDs and permits an exact prefix whose final trick alone
may have one or two plays. See
[Historical declarer concessions](historical_declarer_concessions.md).

Historical defender concession instead requires `kind: "defender_concession"`,
one exact stable `conceding_defender_player_id`, and a supported structured
`concession_form`. No second-defender consent exists. See
[Historical defender concessions](historical_defender_concessions.md).

Historical accepted declarer-card exposure requires the exact remaining
declarer hand, an optional stable shown-to defender, and exactly two stable
defender `accept` responses. See
[Historical declarer card exposure](historical_declarer_card_exposure.md).

Historical defender open play requires one stable exposing defender, that
defender's exact reconstructed current hand, at least five completed tricks, and
`declarer_response: "accept_adjudication"`. See
[Historical defender open play](historical_defender_open_play.md).

Historical open card throw requires one exact stable participant ID and that
player's complete reconstructed current hand. It supports zero through 29 plays,
and assigns every unresolved trick and point to the opposing party. See
[Historical open card throw](historical_open_card_throw.md).

Any supported historical record may include one optional non-terminal
`game_events` array containing exactly one timed
`defender_open_play_continuation` or
`declarer_card_exposure_continuation`. Both require strict `after_play_count`
from 0 through 29 and an exact reconstructed complete hand. Declarer exposure
also requires both stable defender responses with at least one `continue`.
Normal completion still requires ten complete tricks, all 30 actual plays, no
`game_end`, and ordinary final scoring. Alternatively, the same continuation may
precede one matching existing terminal `game_end` after zero or more additional
plays. Its boundary must not exceed the terminal prefix, and terminal shortening
must occur before play 30. The public hand must shrink only through its owner's
actual plays and equal that owner's exact reconstructed terminal hand. Historical
game and event schema versions remain `1`; `game_events` remains exactly one item
when present, and the terminal object is not serialized inside it. See
[Historical defender open-play continuation](historical_defender_open_play_continuation.md)
and [Historical declarer-card-exposure continuation](historical_declarer_card_exposure_continuation.md).

A training-dataset file contains only its dataset branch:

```json
{
  "training_dataset_input": {
    "schema_version": 1,
    "dataset_id": "online-games-2026",
    "dataset_version": "1",
    "feature_generation_version": 1,
    "target": "actual_card_played",
    "partition_policy": {
      "policy_version": 1,
      "mode": "known_opponent"
    },
    "records": []
  }
}
```

Each record supplies a unique `record_id`, a `train`, `validation`, or `test`
partition, required provenance, and one supported historical
historical game. Samples follow the exact validated played-card count, including
zero. See
[Training data](training_data.md) for identity, duplicate, provenance, sample,
and information-safety rules.

`partition_policy` is optional. `known_opponent` permits exact stable players in
multiple partitions; `unseen_player` rejects cross-partition player overlap.
Without metadata, intent is unspecified. `--audit-dataset-partitions` reports
complete ordered membership and overlap without producing samples. Its optional
`--dataset-partition-mode` accepts `report_only`, `known_opponent`, or
`unseen_player`; a requested policy cannot contradict declared metadata. See
[Dataset partition policies](dataset_partition_policies.md).

An automatic preparation file contains only its preparation branch:

```json
{
  "training_dataset_preparation_input": {
    "preparation_version": 1,
    "dataset_id": "prepared-games-2026",
    "dataset_version": "1",
    "feature_generation_version": 1,
    "target": "actual_card_played",
    "mode": "known_opponent",
    "base_random_seed": 42,
    "partition_weights": {
      "train": 3,
      "validation": 1,
      "test": 1
    },
    "records": []
  }
}
```

The public schema requires a non-empty `records` array. Each Record contains only
`record_id`, `provenance`, and one complete supported `historical_game`; it has no
`partition`. The request has no `algorithm` field. Mode is the complete dispatch
contract:

| `mode` | Derived algorithm |
| --- | --- |
| `known_opponent` | `temporal_known_opponent_v1` |
| `unseen_player` | `component_balanced_unseen_player_v1` |

Weights are explicit positive integers. There are no default weights,
percentages, normalization, algorithm overrides, CLI overrides, or fallback.
Only `--input`, `--output`, `--quiet`, and the cross-workflow
`--include-provenance` option are accepted. The root selects workflow identifier
`training_dataset_preparation`; no preparation-specific CLI flag is used. See
[Automatic dataset preparation
contracts](automatic_dataset_preparation_contracts.md).

With `--aggregate-opponent-statistics`, this same branch is reused only as the
versioned multi-game container. Every partition-selected game then requires
`played_at`; repeatable partition selection is canonicalized and the optional
`--opponent-statistics-before` comparison is strict. Aggregation creates no new
JSON input branch and emits no training samples. See
[Historical opponent statistics](historical_opponent_statistics.md).
Both supported end reasons contribute one statistics game per record, including
zero-play concessions. Other historical end reasons remain rejected.

With `--evaluate-opponent-policy-profiles`, the same dataset branch supplies
disjoint rolling profile-source and policy-evaluation partitions under an
explicit known-opponent workflow. Declared unseen-player data is rejected. Source
defaults to `train`; evaluation defaults to `validation` and `test`. Every
selected source and target game requires `played_at`, and only source instants
strictly earlier than each target are eligible. Repeated stable players across
partitions are expected. Normal targets use 30 decisions; concession targets use
their validated zero through 29 actual plays. The alias
`--evaluate-rolling-opponent-policies` selects the same workflow. See
[Rolling opponent-policy evaluation](opponent_policy_evaluation.md).

With `--evaluate-bounded-search`, the dataset branch instead runs deterministic
Search-versus-Immediate evaluation. It requires `--search-seed`. Repeatable
`--search-evaluation-partition` accepts `train`, `validation`, or `test`; when
omitted, selection is canonical `validation`, then `test`. The optional
`--search-evaluation-max-decisions` must be positive and caps one stable global
decision prefix across selected records, not each record separately. Selected
zero-decision records remain present. `--search-budget-profile` accepts exactly
`interactive_v1`, `historical_review_v1`, or `evaluation_v1`, with
`evaluation_v1` as the default. This mode is mutually exclusive with ordinary
dataset conversion, partition audit, statistics aggregation, and opponent-policy
evaluation.

An opponent-statistics file contains only its statistics branch:

```json
{
  "opponent_statistics_input": {
    "schema_version": 1,
    "records": []
  }
}
```

Public statistics use percentage points from `0` through `100`; canonical
normalized profile rates use `0..1`. Provenance and capture time are required,
rounded role and contract sums use a fixed `2.0` percentage-point tolerance,
and exact role-specific counts are not inferred when omitted. A complete
optional `exact_counts` object supplies exact role, result, Hand, and contract
counts and must reconcile with total games and percentages. The
`historical_games` source type additionally requires versioned dataset,
partition, source-game, and timestamp provenance. The output includes a
deterministic explainable profile derivation with unrounded role-evidence
estimates and scoped heuristic confidence. See
[Opponent statistics](opponent_statistics.md) for all denominator and
consistency definitions. The derived preset is not applied, and this branch
cannot be combined with existing manually supplied position profiles.

## Fixed-three-player historical-list workflows

The single-list root request is:

```json
{
  "fixed_three_player_historical_list_input": {
    "schema_version": 1,
    "historical_list": {
      "schema_version": 1,
      "list_id": "list-001",
      "players": [],
      "entries": []
    },
    "lot_order": null
  }
}
```

`players` contains exactly three stable participants in canonical `place_1`,
`place_2`, `place_3` order. `entries` contains exactly 36 authoritative
positions. A strict `played_game` entry contains only `entry_id`, `entry_kind`,
and one existing Historical Game Record. A strict `passed_deal` entry contains
only `entry_id`, `entry_kind`, and required nullable RFC 3339 `played_at`.
Passed Deals advance rotation but have no game, declarer, result, or settlement.

The request-level `lot_order` is required even when null. A non-null value is an
external two- or three-player order for the exact final unresolved tie group;
the engine does not execute a random lot. Runtime validation remains
authoritative for identities, labels, rotating seats, timestamp order,
historical settlement, tie membership, and lot applicability.

The comparison root request is:

```json
{
  "fixed_three_player_historical_list_comparison_input": {
    "schema_version": 1,
    "lists": [
      {
        "schema_version": 1,
        "historical_list": {},
        "lot_order": null
      },
      {
        "schema_version": 1,
        "historical_list": {},
        "lot_order": null
      }
    ]
  }
}
```

At least two sources are required. Array order is authoritative and the first
source is the reference. Each source is built and aggregated exactly once.
Source list IDs must be unique, Played Game IDs must be disjoint across sources,
and every source must contain the same stable player IDs; table places may
change. The result is an independent comparison, not a cross-list aggregation
or series.

No new CLI flag selects either workflow. The JSON root field selects it, and
only `--input`, `--output`, `--quiet`, and the cross-workflow
`--include-provenance` option are valid. Analysis, Search, review, simulation,
profile, dataset, and policy options are rejected.

## Minimal position input

A basic input position requires:

```json
{
  "game_type": "grand",
  "player_role": "declarer",
  "player_position": "middlehand",
  "trick_leader": "right",
  "hand": ["SA", "S10", "S9"],
  "current_trick": ["S7"],
  "played_cards": [],
  "completed_tricks": [],
  "declarer_points": 0,
  "defender_points": 0,
  "next_player": "me",
  "skat": [],
  "left_hand_size": 5,
  "right_hand_size": 5,
  "sample_count": 1000,
  "random_seed": 42,
  "use_basic_opponent_strategy": true
}
```

## Core fields

| Field                         | Meaning                                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------------------- |
| `game_type`                   | One of `clubs`, `spades`, `hearts`, `diamonds`, `grand`, or `null`.                            |
| `player_role`                 | Local player role, usually `declarer` or `defender`.                                           |
| `declarer_player`             | Concrete declarer seat: `me`, `left`, `right`, or `unknown`.                                   |
| `player_position`             | Local player position such as `forehand`, `middlehand`, `rearhand`, or `unknown`.              |
| `trick_leader`                | Player who leads the current trick.                                                            |
| `hand`                        | Known local hand cards.                                                                        |
| `public_declarer_cards`       | Optional exact current opponent declarer hand, required for opponent-declarer Ouvert analysis. |
| `current_trick`               | Cards already played in the current trick.                                                     |
| `played_cards`                | Backward-compatible list of previously played cards. Prefer `completed_tricks` for new inputs. |
| `completed_tricks`            | Detailed completed trick history.                                                              |
| `declarer_points`             | Explicit declarer points already known outside completed tricks.                               |
| `defender_points`             | Explicit defender points already known outside completed tricks.                               |
| `next_player`                 | Player whose turn it is.                                                                       |
| `skat`                        | Known skat cards, if visible.                                                                  |
| `left_hand_size`              | Number of unknown cards held by the left opponent. Late-game positions may use `0`.             |
| `right_hand_size`             | Number of unknown cards held by the right opponent. Late-game positions may use `0`.            |
| `sample_count`                | Number of Monte Carlo samples.                                                                 |
| `random_seed`                 | Random seed for reproducibility.                                                               |
| `use_basic_opponent_strategy` | Whether to use basic opponent strategy.                                                        |

## Turn phase

`current_trick` is card-only. It contains the cards already played in the
current trick, in play order, but it does not contain player-card ownership.

For concrete turn phases, `trick_leader`, `len(current_trick)`, and
`next_player` must follow the fixed three-player order `me -> left -> right`:

| `trick_leader` | `len(current_trick)` | `next_player` |
| -------------- | -------------------: | ------------- |
| `me`           |                    0 | `me`          |
| `me`           |                    1 | `left`        |
| `me`           |                    2 | `right`       |
| `left`         |                    0 | `left`        |
| `left`         |                    1 | `right`       |
| `left`         |                    2 | `me`          |
| `right`        |                    0 | `right`       |
| `right`        |                    1 | `me`          |
| `right`        |                    2 | `left`        |

If both `trick_leader` and `next_player` are concrete, contradictory
combinations are rejected. If one field is concrete and the other is missing or
`unknown`, the missing or unknown counterpart is derived from the table when the
answer is deterministic.

For a non-empty `current_trick`, both `trick_leader` and `next_player` cannot be
missing or `unknown`, because the card ownership cannot be reconstructed safely.
For an empty `current_trick`, `unknown`/`unknown` remains supported for legacy,
historical, or unavailable states.

When the last completed trick provides a concrete
`completed_tricks[-1].winner_player`, that player is the leader of the following
current trick. A missing or `unknown` current `trick_leader` is normalized to
that winner. A conflicting concrete `trick_leader` is rejected. Side-only
`winner_role` values never determine a concrete leader or next player.

Immediate Analysis is available only for normalized local-action positions where
`next_player` is `me` and the game has not ended. If the normalized current actor
is `left` or `right`, the input remains valid when the phase is canonical, but
Immediate Analysis returns an unavailable recommendation instead of analyzing a
nonexistent local decision.

Multi-Step can prepare these opponent-turn phases until the local player is next:

| Starting phase | Preparation |
| -------------- | ----------- |
| `trick_leader = left`, empty `current_trick`, `next_player = left` | Simulate left lead and right response. |
| `trick_leader = right`, empty `current_trick`, `next_player = right` | Simulate right lead. |
| `trick_leader = left`, one-card `current_trick`, `next_player = right` | Preserve the lead card and simulate only right's response. |

Valid phases where the local player has already acted and only an opponent action
remains are not automatically completed. Multi-Step stops with
`unsupported_turn_phase` and leaves the state unchanged for those phases.

Multi-Step requires no new input field for hidden-world coherence. It samples one
private execution root from the validated position, hand sizes, and any exact
public-hand constraints, then preserves that ownership and a fixed hypothetical
skat across all supported steps. Preparation and trick completion use the same
world. Public constraints, including the supported two-hand combination, remain
exact. Local decision policies never receive private unplayed ownership.

Seeded execution uses stable separate derived streams for the path root,
opponent actions, and each step's `highest_expected_value` counterfactual Monte
Carlo samples. Those counterfactual samples remain public decision-time samples
and do not replace the execution root. Immediate Analysis, supported phases,
stops, and existing input settings are unchanged. See
[Coherent hidden-world simulation](coherent_hidden_world_simulation.md).

The local Multi-Step policy registry keeps the four legacy policies unchanged:
`first_legal`, `lowest_point`, `highest_point`, and
`highest_expected_value`. It additionally accepts the Search-aware identifiers
`bounded_search` and `auto`. `first_legal` remains the omitted default whenever
no Search recommendation method is configured.

### Hidden-card inference evidence

Hidden-card inference requires no new input field. When public play confirms a
legal failure to follow, the engine derives an exact decision-time constraint
from the existing position. Allowed hard evidence is limited to `hand`, exact
authorized public hands, legitimately known `skat`, attributed public played
ownership, and confirmed failure to follow the led effective category.

Effective categories reuse `get_effective_suit`: Suit and Grand separate trump
from side suits, and Null uses printed suits. Evidence begins after the public
off-category play, persists for later decisions, and is never retroactive. A
non-empty `current_trick` contributes only when concrete `trick_leader` and the
fixed seating order attribute every supplied card. Exact Ouvert and continuation
hands remain authoritative; a conflict with inferred evidence is rejected.

Tactical choices, bids and declarations, profiles, concessions, timing, future
play, complete post-game hands, final results, game values, overbid, and
settlement never create inference constraints or weights. See
[Hidden-card inference](hidden_card_inference.md).

## Flat recommendation method

Omitting `recommendation_method` preserves the existing Immediate expected-value
path and output exactly. An explicit method accepts:

* `immediate_expected_value`
* `bounded_search`
* `auto`

Explicit Immediate also uses the existing `sample_count`, top-level
`random_seed`, opponent policy, inference, and public-hand settings. It rejects
`bounded_search_settings`.

`bounded_search` is strict: it runs `compatible_world_minimax_v1` and never runs
Immediate fallback. `auto` runs the same Search first and uses Immediate only
when Search successfully returns a validated result whose `recommended_card` is
null. A qualified partial or timeout Search recommendation is used directly.
Search errors, contradictions, invariant failures, and serialization failures do
not trigger fallback.

Both Search methods require this exact object with no unknown or missing keys:

```json
{
  "recommendation_method": "bounded_search",
  "bounded_search_settings": {
    "random_seed": 113,
    "max_remaining_tricks": 3,
    "max_depth_plies": 9,
    "max_nodes": 100000,
    "max_selected_worlds": 20,
    "max_sampled_worlds": 20,
    "minimum_comparable_worlds": 5,
    "wall_clock_timeout_ms": null
  }
}
```

The Search seed must be a non-boolean integer. Every structural budget field is
positive; sampled and minimum-comparable worlds cannot exceed selected worlds.
The timeout is positive or null. There is no default or named production budget.
The top-level `random_seed` remains independent and controls Immediate, legacy
Multi-Step streams, or auto fallback. The derived private Search child seed is
never input or output.

Search methods are accepted only in the flat position workflow with
`game_end_reason: "not_ended"`. Live mode requires
`analysis_mode: "live_decision"` and rejects `actual_card_played`. Flat Search
review requires `analysis_mode: "post_game_review"` and a legal
`actual_card_played`. Both reject `known_post_game` Skat visibility, terminal
shortening, impossible Null settlement, list modes, and
historical/training/statistics workflows. Non-empty legacy `played_cards`
is rejected; prior public play must use `completed_tricks` with ordered concrete
`players`. Existing concrete turn-phase validation still applies.

Flat Search review runs the configured Search method and an independent
Immediate baseline. Search uses `bounded_search_settings.random_seed`; Immediate
uses the top-level `sample_count` and `random_seed`. The actual card is used only
after both analyses to build Search actual-card and Search-versus-Immediate
aggregate comparisons. See
`examples/grand_bounded_search_post_game_review.json`.

Declared Ouvert and either supported ongoing continuation remain valid because
their exact public hands are already authorized and resolved by the information
policy. Search receives only the local state, normalized declaration, public
hand sizes, legitimately visible Skat, those public-hand constraints, and
confirmed structural evidence. It never receives private opponent hands,
coherent execution roots, historical hidden ownership, future play, profile
weights, or tactical ownership assumptions.

With `--multi-step`, an explicitly configured `bounded_search` or `auto` method
becomes the local policy when `--card-policy` is omitted. An explicit legacy
policy conflicts with configured Search, the two Search identifiers cannot be
mismatched, and a Search card policy without the matching JSON method and full
settings is rejected. The dedicated historical-review and dataset-evaluation
Search flags do not override this flat JSON configuration.

At every prepared local decision, Multi-Step reruns the existing recommendation
workflow from the current public state. Public left/right hand sizes are derived
from initial counts and attributed public path actions; only those integers enter
Search. The immutable requested budget applies freshly to each decision, so the
total path cost scales with local decisions multiplied by the per-decision
budget. Child seeds use the versioned
`multi_step_bounded_search_decision_v1` stream from the explicit Search base
seed, independently of the coherent root, opponent actions, Immediate seed,
policy result, and private ownership.

Strict `bounded_search` executes every qualified Search recommendation and stops
with `local_policy_no_recommendation` without rolling back prepared opponent
actions when Search has no card. `auto` executes Search when available and
otherwise uses only the existing validated Immediate fallback. If neither
method returns a card, it stops with the same reason and does not mark fallback.

Policy Comparison remains the four legacy policies when Search is absent. With
an explicit Search method, exactly that method is appended last. Every path gets
an independent copy of one shared coherent execution root, but the Search path
uses that root only after its public recommendation has been selected.

### Historical Search Review and Replay Coaching CLI

Replay Coaching is opt-in and requires historical-game input. It adds no input
JSON fields and supports normal completion, current shortened records, and valid
zero-decision records. Historical-game input can add Search review with the same
public settings:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-search-review --search-seed 71
```

The complete public Replay Coaching Report uses the same Search and Immediate
settings:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-replay-coaching --search-seed 71 --samples 20 --seed 42
```

Supplying `--historical-search-review` and `--historical-replay-coaching`
together emits both public summaries from one shared Search/Immediate analysis.
Coaching alone emits only `historical_replay_coaching_summary`.

Exact options are:

| Option | Meaning |
| --- | --- |
| `--historical-decision-snapshots` | Also emit the existing decision-time snapshot summary. |
| `--historical-game-review` | Also emit the existing Immediate Historical Review summary. |
| `--historical-search-review` | Evaluate every supplied historical decision with Search and Immediate. |
| `--historical-replay-coaching` | Build the complete public one-game Coaching Report from Search, Immediate, and retrospective context. |
| `--search-seed INTEGER` | Required Search base seed. |
| `--search-budget-profile PROFILE` | One of `interactive_v1`, `historical_review_v1`, or `evaluation_v1`; default `historical_review_v1`. |
| `--samples INTEGER` | Immediate samples per decision; default `100`. |
| `--seed INTEGER` | Optional Immediate base seed; decision `n` uses base plus `n - 1`. |
| `--output PATH` | Write the complete strict output branch. |
| `--quiet` | Suppress successful human-readable output. |

JSON output retains the complete strict report. The default CLI presentation is
concise, and `--quiet` continues to suppress successful human-readable output
without suppressing JSON written through `--output`.

The named profiles are immutable internal budgets, not editable JSON objects:

| Profile | Remaining tricks | Depth | Nodes | Selected | Sampled | Minimum comparable | Timeout ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `interactive_v1` | 3 | 9 | 500000 | 64 | 32 | 8 | 1000 |
| `historical_review_v1` | 4 | 12 | 2000000 | 128 | 64 | 16 | 5000 |
| `evaluation_v1` | 5 | 15 | 10000000 | 512 | 256 | 32 | null |

Historical Search and Replay Coaching receive only each reconstructed decision-
time snapshot before the observed card is attached. Their
private per-decision seed is stably derived from the base seed, domain
`historical_bounded_search_decision_v1`, source game ID, and decision index; it
is not an input field and is never serialized. Replay Coaching attaches the
allowlisted final result and settlement only after all coaching classifications
are complete.

### Bounded-Search dataset evaluation CLI

```powershell
python main.py --input examples/training_dataset_normal_play.json --evaluate-bounded-search --search-seed 71 --search-evaluation-max-decisions 10
```

The evaluation-only options are
`--search-evaluation-partition {train,validation,test}` (repeatable) and
`--search-evaluation-max-decisions INTEGER`. The default profile is
`evaluation_v1`; `--search-budget-profile` may select any profile above. The
Immediate baseline is fixed to 100 samples and base seed `0`; position-analysis
`--samples` and `--seed` are not accepted. Selected records retain source and
evaluated decision counts even when the global cap leaves their `decisions`
array empty.

## Declarer identity

`player_role` describes the local player's side. `declarer_player` identifies the concrete player who declared the game.

Valid combinations are:

| `player_role` | `declarer_player` input | Normalized meaning |
| ------------- | ----------------------- | ------------------ |
| `declarer`    | missing                 | `me`               |
| `declarer`    | `me`                    | `me`               |
| `defender`    | `left`                  | declarer is left, local defender partner is right |
| `defender`    | `right`                 | declarer is right, local defender partner is left |
| `unknown`     | missing                 | `unknown`          |
| `unknown`     | `unknown`               | `unknown`          |

Invalid combinations are rejected. In particular, defender inputs must provide `declarer_player` as `left` or `right`. The engine does not infer `declarer_player` from completed tricks, trick leaders, player positions, hand sizes, player profiles, or seating heuristics.

## Card notation

Cards are represented as short strings.

Suits:

| Suit | Meaning  |
| ---- | -------- |
| `C`  | Clubs    |
| `S`  | Spades   |
| `H`  | Hearts   |
| `D`  | Diamonds |

Ranks:

```text
A, 10, K, Q, J, 9, 8, 7
```

Examples:

```text
SA = Ace of Spades
H10 = Ten of Hearts
CJ = Jack of Clubs
```

## Game declaration fields

Game declaration fields describe the announced game.

The project supports backward-compatible top-level declaration fields:

```json
{
  "game_type": "grand",
  "hand_game": false,
  "ouvert": false,
  "schneider_announced": false,
  "schwarz_announced": false,
  "matadors": 2,
  "bid_value": 72
}
```

The project also supports nested declaration metadata:

```json
{
  "game_declaration": {
    "hand_game": false,
    "ouvert": false,
    "schneider_announced": false,
    "schwarz_announced": false,
    "matadors": 2,
    "bid_value": 72
  }
}
```

Both forms are supported for the same fields. If both forms provide the same
field, the explicit top-level field overrides the nested `game_declaration`
field. Mixing forms is supported for compatibility, but using one form is
clearer.

| Field                 | Meaning                                                       |
| --------------------- | ------------------------------------------------------------- |
| `hand_game`           | Whether the game was announced as a hand game.                |
| `ouvert`              | Whether the game was announced as ouvert.                     |
| `schneider_announced` | Whether Schneider was announced.                              |
| `schwarz_announced`   | Whether Schwarz was announced.                                |
| `matadors`            | Matador count for suit and grand games.                       |
| `bid_value`           | Optional bid value used for overbid detection and settlement. |

Boolean declaration fields must be JSON booleans. Explicit `false` values are
preserved and override nested `true` values. Boolean `null` is invalid.

Suit and Grand declaration levels are hierarchical. The effective declaration
is normalized after top-level-over-nested precedence is applied:

* `schneider_announced: true` implies `hand_game: true`.
* `schwarz_announced: true` implies `schneider_announced: true` and
  `hand_game: true`.
* `ouvert: true` implies `schwarz_announced: true`,
  `schneider_announced: true`, and `hand_game: true`.

An omitted prerequisite is added as `true` to the canonical declaration. An
explicit `false` prerequisite is a contradiction and is rejected instead of
being overwritten. This applies equally to nested, top-level, and mixed inputs
after the documented precedence rules are resolved.

`matadors` uses this resolution order: non-null top-level `matadors`, non-null
nested `game_declaration.matadors`, safe deterministic inference, then `null`.
Explicit Suit values must be from `1` through `11`; explicit Grand values must
be from `1` through `4`. Zero is invalid. `matadors: null` means the count is
unknown and the field is missing for precedence and inference purposes.

`bid_value` uses this resolution order: non-null top-level `bid_value`, non-null
nested `game_declaration.bid_value`, then `null`. It must be a positive integer
when provided. `bid_value: null` means the bid value is unknown.

Null declarations use `game_type: "null"` plus `hand_game` and `ouvert` to
represent Null, Null Hand, Null Ouvert, and Null Hand Ouvert. Null games do not
use `matadors`, `schneider_announced`, or `schwarz_announced`; those combinations
are rejected by runtime validation. Null `ouvert` and Null Hand are independent:
`ouvert: true` does not imply `hand_game: true` for a Null game.

### Declared Ouvert public hand

Declared Ouvert authorizes the complete current declarer hand as public. If the
declarer is `me`, analysis derives the constraint from `hand`; an optional
`public_declarer_cards` value must match it exactly. If the declarer is `left` or
`right`, `public_declarer_cards` is required and its count must equal the
corresponding hand-size field.

The field is rejected for non-Ouvert declarations or an unknown declarer. Cards
must be valid and unique and cannot overlap played cards, the current trick,
completed tricks, known skat, the local defender hand, or an independently
public other-player hand. Output card order is canonical. Defender hands are not
required. See [Ouvert-aware simulation](ouvert_aware_simulation.md).

### Impossible Null settlement selection

An impossible Null declaration can optionally record the externally selected
Suit or Grand game used only for settlement:

```json
{
  "game_end_reason": "impossible_null_declaration",
  "impossible_null_settlement": {
    "replacement_game_type": "clubs",
    "matadors": 1
  }
}
```

`replacement_game_type` accepts `clubs`, `spades`, `hearts`, `diamonds`, or
`grand`. Both fields are required when the object is present. Suit matadors must
be `1..11`; Grand matadors must be `1..4`; zero, booleans, Null, missing fields,
and unknown fields are rejected.

This object is separate from `game_declaration`. The original declaration stays
Null and does not receive matadors. The replacement inherits `hand_game` from
the original Null skat-pickup status, but Null `ouvert`, Schneider announced,
and Schwarz announced are not transferred. The selection is supplied by an
online result, historical import, manual record, or adjudication; `skat-ai` does
not optimize across alternatives whose contract-specific matador counts are
unknown.

Automatic matador inference can use known declarer-card context from:

* the local declarer `hand`
* the exact declared-Ouvert `public_declarer_cards`, when the declarer is an opponent
* `skat`, when available and allowed by the analysis mode
* `completed_tricks`, but only from tricks that provide both `cards` and ordered `players`, and only when `declarer_player` is concrete

Completed-trick ownership inference is intentionally conservative:

* It maps each completed-trick card to declarer or non-declarer ownership from the paired `cards`, ordered `players`, and concrete `declarer_player` entries.
* It can use completed-trick ownership from declarer or defender perspective when the concrete declarer seat is known.
* It does not infer ownership from `winner_role`, `winner_player`, or trick winner alone.
* It does not infer completed-trick ownership when `declarer_player` is missing or `unknown`.
* It does not guess hidden cards.
* If completed-trick ownership is incomplete or inconclusive, inference falls back only to deterministic known-card behavior.

If matadors still cannot be inferred for a suit or grand game, the game value may remain incomplete.

For Suit and Grand games, the canonical hierarchy makes declaration levels
cumulative: Hand adds one level; Schneider announced includes Hand and adds two
levels; Schwarz announced includes Schneider announced and Hand and adds three
levels; ouvert includes all three prerequisites and adds four levels.

## Structured declarer concession

The flat position workflow can end an announced game through a concealed or
verbal declarer concession:

```json
{
  "analysis_mode": "post_game_review",
  "game_shortening": {
    "schema_version": 1,
    "kind": "declarer_concession",
    "declarer_hand_cards_remaining": 6,
    "defender_consent": {
      "status": "granted",
      "consenting_defender_count": 1
    }
  }
}
```

At least nine cards require `not_required` and zero consenting defenders. One
through eight cards require `granted` and one or two consenting defenders.
Reliable current-hand and play-history timing evidence must match the supplied
count; insufficient evidence is allowed and reported as `not_verifiable`.

The object requires incomplete play and a calculable final declaration. It is
exclusive with active legacy `game_end_reason` values, impossible Null,
list-performance modes, Multi-Step simulation, and every non-position workflow.
It does not represent open throwing or historical game shortening. Accepted
declarer card exposure uses the separate union member below. See
[Declarer concessions](declarer_concessions.md).

## Structured defender concession

The second version-1 `game_shortening` variant records one accepted defender
concession under ISkO 4.4.3:

```json
{
  "analysis_mode": "post_game_review",
  "declarer_player": "me",
  "game_shortening": {
    "schema_version": 1,
    "kind": "defender_concession",
    "conceding_player": "left",
    "concession_form": "explicit_verbal"
  }
}
```

`conceding_player` must identify one concrete defender and cannot equal the
concrete `declarer_player`. Supported forms are `explicit_verbal` and
`adjudicated_unambiguous_conduct`. The latter records an external adjudication;
the engine does not parse language or decide whether conduct was unambiguous.

One defender binds the complete defending party. No partner consent is required
and the other defender has no veto. The object is post-game, flat-position-only,
requires incomplete play and a calculable declaration, and is exclusive with
legacy endings, impossible Null, simulation, policy comparison, list, and
historical/data workflows. See [Defender concessions](defender_concessions.md).

## Accepted declarer card exposure

The third version-1 `game_shortening` variant records ISkO 4.4.4 exposure that
both concrete defenders accepted:

```json
{
  "analysis_mode": "post_game_review",
  "declarer_player": "me",
  "game_shortening": {
    "schema_version": 1,
    "kind": "declarer_card_exposure",
    "exposure": {
      "form": "shown_to_defender",
      "shown_to_player": "left",
      "exposed_cards": ["CA", "C10", "CJ"]
    },
    "claimed_play_level": "schneider",
    "defender_responses": [
      {"player": "left", "response": "accept", "form": "explicit"},
      {"player": "right", "response": "accept", "form": "explicit"}
    ]
  }
}
```

`laid_open` forbids `shown_to_player`; `shown_to_defender` requires one concrete
defender. The card list must contain every remaining declarer card. Reliable
hand, played-card, current-trick, skat, and ownership contradictions are rejected;
incomplete evidence reports `not_verifiable` without inventing cards.

Both defenders must occur exactly once and accept explicitly or through conduct
already externally classified as unambiguous acceptance. One defender cannot
bind the other. A rejection or continuation response belongs to the separate
ongoing `game_continuation` contract below, not this game-ending union member.

Suit and Grand support `simple`, `schneider`, and `schwarz`; Null requires
`simple`. The object is exclusive with every other game ending and every live,
simulation, policy-comparison, list, historical, training, statistics, or audit
workflow. See [Accepted declarer card exposure](declarer_card_exposure.md).

## Defender open play

The fourth version-1 `game_shortening` variant adjudicates ISkO 4.4.5:

```json
{
  "analysis_mode": "post_game_review",
  "declarer_player": "left",
  "game_shortening": {
    "schema_version": 1,
    "kind": "defender_open_play",
    "exposing_defender": "me",
    "remaining_hands": {
      "me": ["CK", "S9"],
      "left": ["D7", "D8"],
      "right": ["D9", "H8"]
    },
    "declarer_response": "accept_adjudication"
  }
}
```

All three exact hands are required as private post-game proof evidence. Runtime
validation reconciles them with completed and current tricks, local ownership,
hand sizes, turn order, and supplied skat or discard evidence. Exactly 30
in-play cards must be accounted for, leaving two inferred out-of-play cards.
The current trick may contain zero, one, or two cards. One through five tricks
may remain unresolved.

Only `accept_adjudication` is supported in this completed-game object.
`request_continued_play` must use the separate defender-open-play
`game_continuation` member below. The
branch is exclusive with every other ending or continuation and all historical,
dataset, statistics, audit, list, and simulation workflows. See
[Defender open play](defender_open_play.md).

## Open card throw

The fifth version-1 `game_shortening` member records ISkO 4.4.6:

```json
{
  "analysis_mode": "post_game_review",
  "declarer_player": "me",
  "game_shortening": {
    "schema_version": 1,
    "kind": "open_card_throw",
    "throwing_player": "left",
    "thrown_cards": ["C10", "S10"],
    "statement_classification": "attempted_level_limitation"
  }
}
```

The concrete throwing player determines the throwing and opposing parties. One
defender binds both defenders. `thrown_cards` is the complete current physical
hand and is reconciled against exact local evidence, reliable hand size, played
and completed cards, the current trick, skat, and ownership. Output reports
`confirmed` or `not_verifiable`; contradictions are rejected.

Empty, one-card, and two-card current tricks are supported. An incomplete
current trick remains unresolved. Every unresolved trick and outstanding point
goes to the opposing party, while the throwing party keeps only completed tricks
and observed points. `none`, `generic_concession`, and
`attempted_level_limitation` are provenance only. Free text and specific future-
trick assertions are rejected.

The object is post-game flat-position-only and exclusive with continuation,
legacy endings, normal completion, impossible Null, completed ten-trick play,
historical/data/statistics/list workflows, Multi-Step, and Policy Comparison.
See [Open card throw](open_card_throw.md).

## Declarer card exposure continuation

When at least one defender rejects the attempted shortening, use the separate
top-level `game_continuation` object:

```json
{
  "game_continuation": {
    "schema_version": 1,
    "kind": "declarer_card_exposure",
    "exposure": {"form": "shown_to_defender", "shown_to_player": "left"},
    "claimed_play_level": "simple",
    "defender_responses": [
      {"player": "left", "response": "continue", "form": "explicit"},
      {"player": "right", "response": "accept", "form": "explicit"}
    ],
    "public_declarer_cards": ["CA", "C10", "CJ"]
  }
}
```

The object requires exactly both concrete defenders and at least one
`continue`; two acceptances must use `game_shortening`. The public list is the
complete current remaining declarer hand. It is validated against reliable
hand, size, trick, played-card, skat, and local-defender ownership evidence.
Valid evidence reports `confirmed` or `not_verifiable`; either status keeps the
explicit list public and authoritative.

The continuation supports flat live and post-game decision positions,
Immediate Analysis, supported Multi-Step, Policy Comparison, and
`actual_card_played` review. It requires an ongoing incomplete game, concrete
declarer, and calculable final declaration. It is exclusive with every ending,
impossible Null, list mode, and historical/data/statistics workflow. Suit and
Grand preserve all three claimed levels; Null variants permit only `simple`.
The requested level has no immediate result or settlement effect. See
[Declarer card exposure continuation](declarer_card_exposure_continuation.md).

## Defender open play continuation

After the declarer has requested continued play under ISkO 4.1.6, use the
second version-1 `game_continuation` member:

```json
{
  "game_continuation": {
    "schema_version": 1,
    "kind": "defender_open_play",
    "exposing_defender": "left",
    "declarer_response": "request_continued_play",
    "public_exposing_defender_cards": ["C7", "H8", "D9"]
  }
}
```

The defender has physically taken the cards back, but the complete current hand
remains known to all players. Runtime validation requires concrete distinct
declarer and exposing-defender identities, defending-party membership, a
concrete legal turn phase, `1..10` valid unique current hand cards, an incomplete
neutral game, and a calculable original declaration. Reliable local ownership,
hand-size, completed/current-trick, played-card, and skat contradictions are
rejected. `confirmed` and `not_verifiable` both keep the explicit list exact and
authoritative.

Flat live analysis, supported Multi-Step, Policy Comparison, and flat review use
the same exact known hand. No proof is run, the five-trick exact-adjudication
bound does not apply, and no rest tricks, points, decided winner, or settlement
are produced. Accepted adjudication remains in `game_shortening`. See
[Defender open play continuation](defender_open_play_continuation.md).

## Analysis metadata fields

Input files may include optional analysis metadata:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended"
}
```

Supported `analysis_mode` values:

| Value              | Meaning                 |
| ------------------ | ----------------------- |
| `live_decision`    | Live decision state.    |
| `post_game_review` | Post-game review state. |

Supported `skat_visibility` values:

| Value                 | Meaning                                           |
| --------------------- | ------------------------------------------------- |
| `unknown`             | Skat is not visible.                              |
| `known_to_declarer`   | Skat is known only to the declarer during play.   |
| `known_post_game`     | Skat is known for post-game review.               |

Supported legacy `game_end_reason` values:

| Value                                 | Meaning                                                |
| ------------------------------------- | ------------------------------------------------------ |
| `not_ended`                           | Game is still in progress.                             |
| `normal_completion`                   | Game ended normally with all 120 card points assigned. |
| `declarer_claimed_remaining_tricks`   | Declarer claimed the remaining tricks.                 |
| `declarer_conceded_remaining_tricks`  | Simplified legacy assignment of remaining points to defenders. |
| `defenders_conceded_remaining_tricks` | Simplified legacy assignment of remaining points to declarer. |
| `impossible_null_declaration`          | Impossible Null declaration; immediate declarer loss.   |

`impossible_null_declaration` is post-game only. It requires a Null contract,
a bid above the fixed value of the declared Null variant, no played cards,
empty current and completed tricks, and zero assigned card points. The
replacement object may be omitted; the loss is then known but settlement stays
incomplete.

The structured `game_shortening` contract is not silently mapped to any legacy
reason. An absent reason or neutral `not_ended` can accompany it; active legacy
claim, concession, completion, and impossible-Null reasons cannot.

## Player profile fields

Input files may include optional left/right player profiles:

```json
{
  "left_player_profile": {
    "games_played": 860,
    "solo_rate": 0.2,
    "defender_rate": 0.8,
    "grand_rate": 0.13,
    "hand_game_rate": 0.03,
    "defender_win_rate": 0.56
  },
  "right_player_profile": {
    "games_played": 720,
    "solo_rate": 0.42,
    "defender_rate": 0.58,
    "grand_rate": 0.28,
    "hand_game_rate": 0.11,
    "defender_win_rate": 0.48
  }
}
```

Supported profile fields:

| Field                   | Validation                      | Current policy use                                      |
| ----------------------- | ------------------------------- | ------------------------------------------------------- |
| `games_played`          | Non-negative integer.           | Exact overall evidence and rate-estimate denominator.   |
| `solo_games_played`     | Non-negative integer.           | Preferred exact declarer evidence.                      |
| `defender_games_played` | Non-negative integer.           | Preferred exact defender evidence.                      |
| `solo_rate`             | Number between `0` and `1`.     | Aggressive-profile signal at `0.35` or higher.          |
| `defender_rate`         | Number between `0` and `1`.     | Defender evidence estimate when exact count is absent.  |
| `solo_win_rate`         | Number between `0` and `1`.     | Informational only.                                     |
| `hand_game_rate`        | Number between `0` and `1`.     | Aggressive-profile signal at `0.10` or higher.          |
| `suit_game_rate`        | Number between `0` and `1`.     | Informational only.                                     |
| `grand_rate`            | Number between `0` and `1`.     | Aggressive-profile signal at `0.25` or higher.          |
| `null_game_rate`        | Number between `0` and `1`.     | Informational only.                                     |
| `defender_win_rate`     | Number between `0` and `1`.     | Cautious-defender signal at `0.52` or higher with enough defender evidence. |

Profile derivation uses separate overall, declarer, and defender evidence.
Exact role counts take precedence; otherwise role evidence is estimated from
the matching rate, with `1 - solo_rate` as the final defender fallback. Decimal
estimates remain estimates. Every scope uses these heuristic bands:

| Evidence count | Confidence |
| -------------- | ---------- |
| Missing              | `unknown`  |
| `0` to `99`          | `low`      |
| `100` to `499`       | `medium`   |
| `500` or more        | `high`     |

These bands are not confidence intervals or probabilities. `solo_rate` uses
overall confidence, Grand and Hand signals use declarer confidence, and defender
win rate uses defender confidence. Within one profile, actionable aggressive
signals take precedence over defender evidence. Low-confidence matches remain
explanatory but are not actionable. See
[Opponent profile derivation](opponent_profile_derivation.md).

When `use_profile_presets` is enabled for position profiles, only an
actionable non-simple preset can affect opponent policy settings. Neutral
`simple_lowest` never overwrites existing explicit or default policies. The
existing combined left/right helper retains its established conflict behavior,
and explicit side-specific input and CLI overrides remain authoritative.

When a player profile is supplied, it must be a JSON object. Explicit `null` is
not accepted for `left_player_profile`, `right_player_profile`, or known profile
fields such as `games_played`. Unknown extra profile fields remain accepted as
metadata.

Left and right actionable profiles affect their respective effective policies
in immediate analysis and multi-step simulation. A reusable external statistics
file may be attached through `--opponent-statistics-file` and bound through
exact, case-sensitive `--left-opponent-player-id` and
`--right-opponent-player-id` values. These are CLI bindings, so no new position
input field is added. Manual side profiles take precedence, profiles are not
merged, and effective profile-preset opt-in is required. See
[Live opponent profiles](live_opponent_profiles.md).

## Live vs post-game information rules

The project separates live decision analysis from post-game review.

`live_decision` is intended for in-game decisions and must not use post-game-only information.

`post_game_review` is intended for completed or retrospectively analyzed games.

Important validation rules:

* `analysis_mode = "live_decision"` cannot use `skat_visibility = "known_post_game"`.
* `analysis_mode = "live_decision"` can include concrete Skat cards only with `skat_visibility = "known_to_declarer"`.
* With `skat_visibility = "known_to_declarer"`, declarer analysis may use the supplied Skat cards, while defender analysis validates them and then redacts them from the local analysis view.
* `skat_visibility = "unknown"` cannot include concrete Skat cards in `skat`.
* `skat_visibility = "known_to_declarer"` and `skat_visibility = "known_post_game"` require either zero or two concrete Skat cards.
* `skat` must be an array and can contain at most two cards.
* `game_end_reason` values other than `not_ended` require `analysis_mode = "post_game_review"`.
* `analysis_mode = "live_decision"` cannot describe a completed game with all 120 card points assigned.
* In `live_decision`, completed-trick winner metadata such as `winner_player` or `winner_role` must be verifiable.
* In `live_decision`, `winner_role` is accepted only when the winning side can be derived from `cards`, `players`, `game_type`, and concrete `declarer_player`.
* In `live_decision`, completed tricks with `winner_role` but without `players` are rejected.
* In `live_decision`, completed tricks with `players` are rejected if `winner_role` contradicts the rule-derived winner side or if the winner side cannot be derived.
* A validated `game_continuation` is a narrow exception: its exact current declarer hand is public to all players.
* The exception does not authorize the co-defender hand, reactionary defender cards, future plays, future winners, or post-game opponent information.

Examples:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "known_to_declarer",
  "game_end_reason": "not_ended",
  "skat": ["C7", "D8"]
}
```

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended"
}
```

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "game_end_reason": "normal_completion",
  "skat": ["C7", "D8"]
}
```

## Post-game review fields

Post-game review can include the optional `actual_card_played` field.

Example:

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "actual_card_played": "C7"
}
```

| Field                | Meaning                                                     |
| -------------------- | ----------------------------------------------------------- |
| `actual_card_played` | The card that was actually played in the analyzed position. |

Validation rules:

* `actual_card_played` is optional.
* If provided, it must be valid card notation.
* If provided, it must be in the local player's known `hand`.
* If provided, it must be legal in the analyzed position.
* `actual_card_played` is intended for `post_game_review`.

When `actual_card_played` is provided, the output contains a `post_game_review_summary` comparing the actual card with the recommended card.

## Performance rating fields

Input files may optionally include:

```json
{
  "performance_rating_system": "isko_list"
}
```

Supported values:

| Value         | Meaning                                                                               |
| ------------- | ------------------------------------------------------------------------------------- |
| `placeholder` | Generic placeholder rating system.                                                    |
| `isko_list`   | Partially implemented SkWO-style performance scoring for the fixed three-player table. |

If omitted, `performance_rating_summary.rating_system` is `null`.

The project assumes a fixed three-player table. There is no supported public `table_size` input field. A top-level `table_size`, if supplied as extra metadata, is ignored by rating logic and should not be used for workflow configuration.

Input files may also include already aggregated list or series totals:

```json
{
  "performance_rating_system": "isko_list",
  "list_performance_input": {
    "player_game_points": 120,
    "own_games_won": 3,
    "own_games_lost": 1,
    "other_players_lost_games": 2
  }
}
```

Fields:

| Field                       | Meaning                                                               |
| --------------------------- | --------------------------------------------------------------------- |
| `player_game_points`        | Already aggregated game points for the rated player. May be negative. |
| `own_games_won`             | Count of the rated player's won own games.                            |
| `own_games_lost`            | Count of the rated player's lost own games.                           |
| `other_players_lost_games`  | Count of lost games by the other two players.                         |

Validation rules:

* `list_performance_input` is optional.
* If provided, `performance_rating_system` must be `isko_list`.
* All four fields are required and must be integers.
* `player_game_points` may be negative, zero, or positive.
* The three game counters must be non-negative.
* `table_size` is fixed at `3`. Do not include `table_size` inside `list_performance_input`; a top-level `table_size`, if supplied as extra metadata, is ignored and is not part of the supported public contract.
* Raw individual games are not aggregated in this input mode.

As an alternative to already aggregated totals, input files may include
normalized per-game list or series contributions:

```json
{
  "performance_rating_system": "isko_list",
  "list_game_contributions": [
    {
      "player_role": "declarer",
      "game_outcome": "declarer_win",
      "settlement_score": 96
    },
    {
      "player_role": "defender",
      "game_outcome": "declarer_loss",
      "settlement_score": -144
    }
  ]
}
```

Contribution fields:

| Field              | Meaning                                                            |
| ------------------ | ------------------------------------------------------------------ |
| `player_role`      | Rated player's role in that game: `declarer` or `defender`.        |
| `game_outcome`     | Declarer's game outcome: `declarer_win` or `declarer_loss`.        |
| `settlement_score` | Declarer's single-game settlement score before performance points. |
| `rated_player_id`  | Optional opaque stable identifier for the rated player.            |
| `game_id`          | Optional opaque stable identifier for the game.                    |

Validation rules:

* `list_game_contributions` is optional.
* If provided, `performance_rating_system` must be `isko_list`.
* It must be an array. An empty array is valid.
* Each contribution must contain `player_role`, `game_outcome`, and `settlement_score`.
* Each contribution may also contain `rated_player_id` and `game_id`.
* Other additional contribution fields are rejected.
* `player_role` must be `declarer` or `defender`.
* `game_outcome` must be `declarer_win` or `declarer_loss`.
* `settlement_score` must be an integer.
* `declarer_win` requires a positive `settlement_score`.
* `declarer_loss` requires a negative `settlement_score`.
* `rated_player_id` and `game_id`, when supplied, must be non-empty strings without leading or trailing whitespace.
* Identifiers are opaque and case-sensitive. They are not lowercased, uppercased, trimmed, parsed, inferred, or generated.
* If any contribution supplies `rated_player_id`, every contribution must supply the same `rated_player_id`.
* Partial `rated_player_id` presence is rejected because same-player verification would be ambiguous.
* `game_id` may be supplied for all, some, or no contributions.
* Duplicate supplied `game_id` values are rejected. Duplicate detection applies only to supplied IDs.
* Identifiers are input validation metadata only and are not echoed in output summaries.
As another alternative, input files may include explicit fixed three-player list
standings input:

```json
{
  "performance_rating_system": "isko_list",
  "list_standings_input": {
    "players": [
      {"player_id": "alice", "player_label": "Alice"},
      {"player_id": "bob", "player_label": "Bob"},
      {"player_id": "carol", "player_label": "Carol"}
    ],
    "games": [
      {
        "game_id": "game-1",
        "declarer_player_id": "alice",
        "game_outcome": "declarer_win",
        "settlement_score": 96
      }
    ],
    "lot_order": ["carol", "bob"]
  }
}
```

Standings input fields:

| Field                         | Meaning                                                    |
| ----------------------------- | ---------------------------------------------------------- |
| `players[].player_id`         | Required stable player identifier.                         |
| `players[].player_label`      | Optional display label.                                    |
| `games[].game_id`             | Optional stable game identifier.                           |
| `games[].declarer_player_id`  | Declarer player identifier for the game.                   |
| `games[].game_outcome`        | `declarer_win` or `declarer_loss`.                         |
| `games[].settlement_score`    | Declarer's settlement score before performance bonuses.    |
| `lot_order`                   | Optional externally determined best-to-worst lot order.    |

Validation rules:

* exactly three players are required
* player IDs must be unique non-empty strings without leading or trailing whitespace
* player labels are optional non-empty strings without leading or trailing whitespace
* `games` may be empty
* every `declarer_player_id` must reference one of the declared players
* `declarer_win` requires a positive `settlement_score`
* `declarer_loss` requires a negative `settlement_score`
* supplied `game_id` values must be unique
* `lot_order`, when supplied, must be an array of two or three unique declared player IDs
* `lot_order` must contain exactly every player in the one tie group remaining after total performance points, own wins, and own losses are compared
* omitted tied players, unknown players, players outside the tie, and a lot result supplied without an unresolved tie are rejected
* the engine does not execute a random lot; `lot_order` only records an externally executed decision
* `list_standings_input` emits `list_standings_summary`, not `list_performance_summary`

Existing single-rated-player modes do not emit standings because they do not
safely describe all three player identities and totals.

The standings formula and tie handling follow SkWO 6.3.1. The public
`performance_rating_system: "isko_list"` identifier remains unchanged for
compatibility. Without a valid external `lot_order`, an official tie remains
unresolved and the resulting standings are not final.

* `list_performance_input`, `list_game_contributions`, `list_analysis_results`, and `list_standings_input` are alternative input modes and cannot be combined.
* `table_size` is fixed at `3`. There is no supported `table_size` input for this mode; a top-level `table_size`, if supplied as extra metadata, is ignored.

As another alternative, input files may include already-built local analysis
results. Each entry is assumed to represent the same rated player as local
`me`; the project does not validate stable player identities across entries.

```json
{
  "performance_rating_system": "isko_list",
  "list_analysis_results": [
    {
      "position": {
        "player_role": "declarer"
      },
      "final_settlement_summary": {
        "is_complete": true,
        "is_loss": false,
        "settlement_score": 96
      }
    },
    {
      "position": {
        "player_role": "defender"
      },
      "final_settlement_summary": {
        "is_complete": true,
        "is_loss": true,
        "settlement_score": -144
      }
    }
  ]
}
```

Required analysis-result subset:

| Field                                             | Meaning                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------ |
| `rated_player_id`                                 | Optional opaque stable identifier for the rated player.            |
| `game_id`                                         | Optional opaque stable identifier for the game.                    |
| `position.player_role`                            | Rated player's local role: `declarer`, `defender`, or `unknown`.   |
| `final_settlement_summary.is_complete`            | Whether the settlement is complete.                                |
| `final_settlement_summary.is_loss`                | Required only for complete settlements.                            |
| `final_settlement_summary.settlement_score`       | Required only for complete settlements.                            |

Validation rules:

* `list_analysis_results` is optional.
* If provided, `performance_rating_system` must be `isko_list`.
* It must be an array. An empty array is valid.
* Each item must be an object with `position` and `final_settlement_summary` objects.
* Additional fields are accepted on each item, on `position`, and on `final_settlement_summary`, so complete generated analysis-result objects can be supplied.
* Complete output objects are accepted as supersets, but the input schema does not embed the full output schema.
* `final_settlement_summary.is_complete` must be a boolean.
* If `is_complete` is `false`, the result is valid and skipped for list aggregation.
* If `is_complete` is `true`, `is_loss` must be a boolean and `settlement_score` must be an integer.
* `is_loss: false` requires a positive `settlement_score`.
* `is_loss: true` requires a negative `settlement_score`.
* Results with `position.player_role: "unknown"` are skipped.
* Malformed results are rejected and include the list index in validation errors.
* `rated_player_id` and `game_id` are optional top-level fields on each list entry, not fields inside `position` or `final_settlement_summary`.
* `rated_player_id` and `game_id`, when supplied, must be non-empty strings without leading or trailing whitespace.
* Identifiers are opaque and case-sensitive. They are not lowercased, uppercased, trimmed, parsed, inferred, or generated.
* No identity is inferred from `me`, `left`, `right`, `player_role`, `player_position`, `trick_leader`, display names, or player profiles.
* If any analysis result supplies `rated_player_id`, every analysis result must supply the same `rated_player_id`.
* Partial `rated_player_id` presence is rejected because same-player verification would be ambiguous.
* `game_id` may be supplied for all, some, or no analysis results.
* Duplicate supplied `game_id` values are rejected. Duplicate detection applies only to supplied IDs.
* Identical content without `game_id` is not treated as a duplicate. Identical content with different `game_id` values is valid. Different content with the same `game_id` is rejected.
* Identifiers are input validation metadata only and are not echoed in output summaries.
* `list_performance_input`, `list_game_contributions`, `list_analysis_results`, and `list_standings_input` are mutually exclusive.

Already aggregated `list_performance_input` cannot support game-level duplicate detection because per-game records are no longer present. A future player label could be added for aggregated totals, but issue #29 duplicate protection applies only to per-game input modes.

## Opponent policy fields

Input files can define opponent card-selection policies.

Global opponent policy fields are backward-compatible and apply as defaults:

```json
{
  "opponent_lead_policy": "lowest_point",
  "opponent_response_policy": "lowest_point"
}
```

Supported opponent card policies:

Policy values are canonical, exact, and case-sensitive. The runtime does not accept aliases or perform case normalization.

| Value                     | Meaning                               |
| ------------------------- | ------------------------------------- |
| `lowest_point`            | Choose the lowest-point legal card.   |
| `highest_point`           | Choose the highest-point legal card.  |
| `random_legal`            | Choose a random legal card.           |
| `basic_trick_play`        | Use basic trick-play behavior.        |
| `basic_defender_lead`     | Use a cautious defender lead policy.  |
| `basic_defender_response` | Use a basic defender response policy. |

Named presets can set both lead and response policies:

```json
{
  "opponent_policy_preset": "cautious_defender"
}
```

Supported opponent policy presets:

| Value                | Lead policy             | Response policy             |
| -------------------- | ----------------------- | --------------------------- |
| `simple_lowest`      | `lowest_point`          | `lowest_point`              |
| `cautious_defender`  | `basic_defender_lead`   | `basic_defender_response`   |
| `aggressive_points`  | `highest_point`         | `highest_point`             |
| `random`             | `random_legal`          | `random_legal`              |

Preset values are also exact and case-sensitive. Aliases and normalized casing are not supported.

The project also supports separate left/right opponent policy fields:

```json
{
  "left_opponent_lead_policy": "highest_point",
  "left_opponent_response_policy": "basic_trick_play",
  "right_opponent_lead_policy": "basic_defender_lead",
  "right_opponent_response_policy": "basic_defender_response"
}
```

Effective policy behavior:

* Global presets and global lead/response policies cascade to both `left` and `right`.
* Left/right fields override only their side.
* Actionable profile-derived policies affect only their side when `use_profile_presets` is enabled.
* CLI policy overrides use the same resolver as input fields, and side-specific CLI overrides win last.

Multi-step behavior:

* If `right` leads, the engine uses `right_opponent_lead_policy`.
* If `left` leads, the engine uses `left_opponent_lead_policy`.
* If `left` leads and `right` responds, the engine uses `right_opponent_response_policy`.
* Candidate trick completion uses activated side response policies when an explicit response source exists.

Global policy fields remain supported for backward compatibility.

Immediate candidate analysis starts with the local candidate card and only simulates remaining opponent responses. It does not simulate a new opponent lead. Opponent lead policies are used during multi-step opponent-turn preparation.

Immediate response-policy behavior is activated only by explicit policy sources:

* `opponent_policy_preset`
* `opponent_response_policy`
* `left_opponent_response_policy`
* `right_opponent_response_policy`
* `use_profile_presets: true`
* relevant CLI overrides

Absent fields normalized to defaults, `use_profile_presets: false`, lead-only policy sources, and player profiles without enabled actionable profile presets do not activate policy-driven immediate analysis or multi-step candidate completion. In those cases, those paths keep the legacy basic or random opponent response behavior from `use_basic_opponent_strategy`.

Shared policy precedence, from lowest to highest, is:

1. built-in lowest-point defaults
2. input global policy preset
3. explicit input global lead and response policies
4. input-activated profile-derived side policies
5. explicit input side lead and response policies
6. global CLI policy preset
7. CLI-activated profile-derived side policies
8. explicit global CLI lead and response policies
9. explicit side-specific CLI lead and response policies

Response-policy activation uses the same order but only response-bearing sources activate the sparse response map:

1. input global policy preset
2. explicit input global response policy
3. input-activated profile-derived side response policies
4. explicit input side response policies
5. global CLI policy preset
6. CLI-activated profile-derived side response policies
7. explicit global CLI response policy
8. explicit side-specific CLI response policies

Global presets and global response policies apply to both `left` and `right`. Profile-derived policies and side-specific response policies affect only their side. The activated response-policy map is sparse, so an explicit left-side policy alone does not populate a right-side default entry.

## Completed tricks

The preferred way to record completed tricks is `completed_tricks`.

A detailed completed trick can include:

```json
{
  "cards": ["CJ", "SJ", "DJ"],
  "players": ["me", "left", "right"],
  "winner_role": "declarer",
  "winner_player": "me"
}
```

For input, every completed-trick entry requires `cards` and `winner_role`. The `players` and `winner_player` fields remain optional for backward-compatible partial histories.

Validation rules:

* `cards` must contain exactly three cards.
* `winner_role` is required and must be `declarer` or `defenders`.
* `players` must contain exactly three unique players when provided.
* Completed-trick entries reject unsupported keys; supported keys are `cards`, `players`, `winner_role`, and `winner_player`.
* Input trick players are `me`, `left`, or `right`; `unknown` is not accepted inside `completed_tricks[].players` or `completed_tricks[].winner_player`.
* `players` must follow the known seating order:

  * `["me", "left", "right"]`
  * `["left", "right", "me"]`
  * `["right", "me", "left"]`
* `winner_player` must be valid when provided.
* `winner_role` is checked against `winner_player` when concrete declarer identity allows safe side ownership resolution.
* The winner of one completed trick must lead the next completed trick.
* If `current_trick` is not empty, `trick_leader` must match the winner of the last completed trick.
* When `cards` and `players` are provided, the engine derives the actual trick winner according to the implemented Skat rules.
* When `winner_player` is provided with `cards` and `players`, it must match the derived trick winner.
* When `winner_role` is provided with `cards`, `players`, and concrete declarer identity, it must match the derived winner side even if `winner_player` is omitted.
* In `live_decision`, `winner_role` must be verifiable from `cards`, `players`, `game_type`, and concrete `declarer_player`; unverifiable or contradictory live `winner_role` values are rejected.

Older completed-trick entries without `players` or `winner_player` remain supported, but they cannot be checked as strictly. Existing explicit `winner_role` values remain accepted as side-level facts unless concrete `players` plus declarer identity, or concrete `winner_player` plus declarer identity, prove a conflict.

For hidden-card inference, canonical `cards` plus ordered `players` provide
trusted legal attributed public history after ordinary position validation.
Complete historical replay proves ownership, order, and follow legality more
strictly. Legacy `played_cards` and completed tricks without `players` are never
assigned to a guessed owner; mixed attributed and unattributed history is
reported as partial provenance.

For matador inference, completed tricks contribute ownership facts only when `cards`, ordered `players`, and concrete `declarer_player` are present. `winner_role`, `winner_player`, and trick winner alone are not used to infer matador ownership.

Basic structural schema acceptance does not require ten completed tricks. Ten reliable trick owners are required only for particular final-result features, such as completed Null contract derivation and Schwarz settlement reliability.

## Historical game timestamps

Version-1 `historical_game_input` optionally accepts `played_at`, the RFC 3339
instant when the game began. It must contain an explicit UTC offset and is
preserved exactly. It is required only when `--opponent-statistics-file` is used
with `--historical-game-review`, or when its dataset record is selected for
`--aggregate-opponent-statistics` or rolling source/target evaluation. Existing historical, snapshot, and normal
training conversion inputs remain valid without it when neither feature is
requested.

Historical profile application automatically matches exact case-sensitive
participant `player_id` values. It does not accept live-only left/right binding
IDs. Every matched statistics `source.captured_at` instant must be strictly
earlier than `played_at`; equality and later captures reject the invocation.
See [Historical opponent profiles](historical_opponent_profiles.md).

## Validation rules

Input validation rejects:

* invalid game types
* invalid card notation
* explicit `null` or non-array values for card-array fields
* hands with more than 10 cards
* negative opponent hand sizes
* opponent hand sizes above 10
* sample counts above 100000
* duplicate known cards
* invalid completed-trick structures
* unsupported completed-trick keys
* invalid completed-trick winner metadata
* inconsistent completed-trick sequence
* negative point values
* known card points above 120
* unknown `game_end_reason`
* inconsistent `game_end_reason` and remaining card points
* invalid `bid_value`
* contradictory Suit or Grand declaration prerequisites
* zero or out-of-range explicit matador values
* Null declarations with Schneider, Schwarz, or matador values
* unknown `performance_rating_system`
* invalid `list_performance_input`
* invalid `list_standings_input`
* invalid opponent policy values
* invalid live-vs-post-game information combinations
* known Skat cards in live decision mode unless `skat_visibility = "known_to_declarer"`
* ended game reasons outside post-game review mode
* complete 120-point game states in live decision mode
* invalid or illegal `actual_card_played`
* impossible Null metadata outside `impossible_null_declaration`
* impossible Null reasons with live mode, a non-Null contract, an absent or
  insufficient bid, played cards/tricks, or assigned card points
* incomplete, unknown, or out-of-range impossible Null replacement fields
