# Examples

This document describes the example input files in `examples/`.

The repository-root quick-start command `python main.py` opens the unified local
application shell. Advanced automation uses `python main.py run --input`; the
root fixture and `examples/` files remain repository development data.

The examples are used for:

* manual testing
* regression tests
* input schema validation
* generated-output schema validation
* documentation of supported workflows

## Example validation

All example JSON files should remain valid.

Run the full project check:

```powershell
.\scripts\check.ps1
```

The historical published `v0.16.0` baseline at commit `91b1360` contains 63
authoritative Schemas and 63 Packaged Schema Resources, includes six strict
Session examples, validates 85 deterministic generated-output scenarios, and
passes 6,925 pytest tests in 1083.48s. Issues #171 through #179 complete the
functional milestone, Issue #180 completed Release preparation without changing
any example or generated scenario file, and Issue #181 synchronizes publication
status after manual maintainer publication on 2026-08-18. GitHub Releases is the
authoritative publication record; no Package-index or PyPI publication is
claimed.

The current published `v0.17.0` Package baseline at commit `8187fbe` uses Package
version `0.17.0`, Python `>=3.13`, Public API contract version `1`, seven Root
workflows, one Console Script, and six
Session examples. Issue #186 adds two authoritative and packaged Historical
Claim Schemas plus three append-only generated-output scenarios, bringing the
working totals to 65 Schemas and 88 scenarios. Issue #189 adds four authoritative
and packaged Information-set Search Schemas, one input example, and four append-
only generated-output scenarios. Issue #190 adds one Multi-Step input example
and two append-only scenarios without adding a Schema, bringing the totals to 69
Schemas and 94 scenarios without changing the published `v0.16.0` facts above.
Issue #191 changes neither count. Issue #192 adds one strict Information-set
Replay Coaching Schema, one Root example, and two append-only scenarios, bringing
the Issue #192 point-in-time totals to 70 Schemas and 96 scenarios while preserving the
Issue #190 and published baselines. Issue #193 changes neither count. Issue #194
adds one strict Historical Tactical Motif Review Schema, one Root example, and
two append-only scenarios, bringing the published totals to 71 Schemas and
98 scenarios. The maintainer published `v0.17.0` on 2026-08-25; Issue #199
synchronizes that publication without changing examples or scenarios.

The historical published `v0.15.0` baseline at commit `ec1c154` contains 63
authoritative Schemas and 63 Packaged Schema Resources, includes six strict
Session examples, validates 85 deterministic generated-output scenarios, and
passes 6,510 pytest tests. Issues #160 through #168 complete the functional
milestone, Issue #169 completed Release preparation without changing any example
or generated scenario file, and Issue #170 synchronized publication status.

The historical published `v0.14.0` baseline at commit `d5589f8` contains the same
63 authoritative and packaged Schemas, six Session examples, and 85 scenarios,
and passes 5,892 pytest tests. Issues #150 through #157 complete its functional
milestone, Issue #158 completed Release preparation, and Issue #159 synchronized
publication status.

The historical published `v0.13.0` baseline at commit `abd1ad3` contains 62
authoritative Schemas and 62 Packaged Schema Resources, validates 77 deterministic
generated-output scenarios, and passes 5,399 pytest tests. Issue #147 leaves the
70 historical published `v0.12.0` scenarios unchanged and appends seven public
field-provenance scenarios, one per Root workflow. Issue #148 completed Release
preparation, and Issue #149 synchronized publication status. The historical
published `v0.12.0` baseline at commit `bbf955e` remains evidence for 70
scenarios and 4,762 pytest tests; Issue #135 completed its release preparation.
The historical published
`v0.11.0` baseline remains evidence for 64 scenarios and 4,392 pytest tests. The
historical published `v0.10.0` baseline remains evidence for 59 scenarios and
4,075 pytest tests. The historical
published `v0.9.0` baseline covers 52 deterministic scenarios and 3,558 pytest
tests.

The check script validates:

* Ruff checks
* packaged-Schema filename and byte parity
* input JSON schema validation
* generated output JSON schema validation
* Wheel, sdist, and clean-install API/CLI validation
* pytest regression tests

Run input schema validation directly:

```powershell
python scripts/validate_examples_schema.py
```

Run generated-output schema validation directly:

```powershell
python scripts/validate_generated_outputs_schema.py
```

## Session examples

Issue #157 adds exactly six strict Session examples:

| File | Purpose |
| --- | --- |
| `session_create_live.json` | Explicit Live Session identity, local Player, and fixed three-player seats. |
| `session_create_retrospective.json` | Explicit Retrospective Session identity and fixed three-player seats. |
| `session_command_record_play.json` | One strict expected-revision `record_play` Command. |
| `session_correction_record_play.json` | One strict one-command correction replacing a recorded Play. |
| `session_live_persistence.json` | Canonical private Live persistence document with valid State/content fingerprints and frozen Checkpoints. |
| `session_retrospective_persistence.json` | Canonical private Retrospective persistence document with valid fingerprints and complete capture facts. |

Creation, Command, and correction examples validate against their focused
definitions in `session.schema.json`. Persistence examples additionally undergo
strict resume, fingerprint, accepted-Log replay, and Checkpoint-lineage
validation. They are repository development files, not installed Package Data.

Representative Session CLI use is:

```powershell
skatmind session new --session session.json --input examples/session_create_live.json
skatmind session show --session session.json
skatmind session apply --session session.json --input examples/session_command_record_play.json
skatmind session assistant --session session.json
```

All 12 subcommands and exact options are documented in
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).

## Workflow walkthroughs

These commands cover the main user-facing CLI workflows. They reuse existing repository fixtures and can be run from the repository root.

Show the complete advanced automation help and task examples:

```powershell
python main.py run --help
```

Run live recommendation using the root `input_position.json` fixture:

```powershell
python main.py run --input input_position.json
```

Run live recommendation with an explicit input file:

```powershell
python main.py run --input examples/grand_second_position.json
```

Run a complete one-world exhaustive bounded Search recommendation:

```powershell
python main.py run --input examples/grand_bounded_search_exhaustive.json
```

Run Search-first auto routing with a structural node-budget fallback to
Immediate expected value:

```powershell
python main.py run --input examples/grand_auto_search_fallback.json
```

Run flat post-game bounded Search with independent Immediate and actual-card
comparisons:

```powershell
python main.py run --input examples/grand_bounded_search_post_game_review.json
```

Run strict flat Information-set Search with the example's exact nine settings:

```powershell
python main.py run --input examples/information_set_search.json
```

Live Information-set Search has no PIMC or Immediate baseline and no fallback.
Its public Result is aggregate-only and omits exact Worlds, hidden hands,
Observations, controlled Policy tables, caches, and derived seeds.
The four Issue #189 generated scenarios cover this complete Live result with
Provenance, flat Post-game same-selection comparison, Historical Review, and
Training Dataset evaluation.

Run strict Information-set Search through one Multi-Step decision and the
five-policy comparison:

```powershell
python main.py run --input examples/information_set_search_multi_step.json --multi-step 1
python main.py run --input examples/information_set_search_multi_step.json --multi-step 1 --compare-policies
```

Each local decision starts fresh Search from public state with a domain-separated
child seed. The coherent execution World remains private and independent; Search
Worlds and controlled Policies are not reused. A missing recommendation stops
without fallback. Policy Comparison appends `information_set_search` exactly once
and last, retains stopped rows as visible but ineligible, and emits the safe
nested Result plus 16 compact diagnostics.

Write structured JSON output:

```powershell
python main.py run --input examples/grand_second_position.json --output outputs/result.json
```

Write JSON output without successful human-readable stdout output:

```powershell
python main.py run --input examples/grand_second_position.json --output outputs/result.json --quiet
```

The `--quiet` flag suppresses successful human-readable stdout output, including the output-file confirmation. Expected errors still go to `stderr`.

Write public-safe Root Result provenance and print its concise aggregate summary:

```powershell
python main.py run --input examples/opponent_statistics.json --include-provenance --output outputs/opponent-statistics-with-provenance.json
```

Retain the same JSON sidecar while suppressing successful stdout:

```powershell
python main.py run --input examples/opponent_statistics.json --include-provenance --output outputs/opponent-statistics-with-provenance.json --quiet
```

Validate and summarize a complete normally played historical game:

```powershell
python main.py run --input examples/historical_grand_normal_completion.json
```

Aggregate a mixed fixed-three-player historical 36-position list or inspect an
all-Passed-Deal unresolved tie:

```powershell
python main.py run --input examples/fixed_three_player_historical_list_mixed.json
python main.py run --input examples/fixed_three_player_historical_list_all_passed.json
```

Compare two independent completed lists with the first as reference:

```powershell
python main.py run --input examples/fixed_three_player_historical_list_comparison.json
```

These root-selected workflows accept only `--input`, `--output`, `--quiet`, and
the cross-workflow `--include-provenance` option. They add no list-specific CLI
flag.

Validate a historical Grand prefix ending in declarer concession:

```powershell
python main.py run --input examples/historical_grand_declarer_concession.json
```

Validate a historical Grand prefix ending in defender concession:

```powershell
python main.py run --input examples/historical_grand_defender_concession.json
```

Validate a historical Grand prefix ending in unanimously accepted declarer-card
exposure:

```powershell
python main.py run --input examples/historical_grand_declarer_card_exposure.json
```

Validate bounded exact terminal historical defender open play:

```powershell
python main.py run --input examples/historical_grand_defender_open_play.json
```

```powershell
python main.py run --input examples/historical_grand_open_card_throw.json
```

Validate the Historical-only bounded party-wide Claim:

```powershell
python main.py run --input examples/historical_party_wide_claim.json
```

Validate a normal historical Grand with timed defender-open-play continuation:

```powershell
python main.py run --input examples/historical_grand_defender_open_play_continuation.json --historical-decision-snapshots
```

Validate a normal historical Grand with timed declarer-card-exposure continuation:

```powershell
python main.py run --input examples/historical_grand_declarer_card_exposure_continuation.json --historical-decision-snapshots
```

Validate defender-open-play continuation followed by declarer concession, with
two actual cards after the continuation:

```powershell
python main.py run --input examples/historical_grand_defender_open_play_continuation_declarer_concession.json --historical-decision-snapshots
```

Validate declarer-card exposure followed immediately by defender concession at
the same play boundary:

```powershell
python main.py run --input examples/historical_grand_declarer_card_exposure_continuation_defender_concession.json --historical-decision-snapshots
```

Write its separate structured result without successful stdout:

```powershell
python main.py run --input examples/historical_grand_normal_completion.json --output outputs/historical.json --quiet
```

Generate its 30 pre-play decision snapshots:

```powershell
python main.py run --input examples/historical_grand_normal_completion.json --historical-decision-snapshots
```

Review all 30 decisions with deterministic settings:

```powershell
python main.py run --input examples/historical_grand_normal_completion.json --historical-game-review --samples 20 --seed 42
```

Run Historical Search Review with an explicit Search seed and the default
immutable `historical_review_v1` budget:

```powershell
python main.py run --input examples/historical_grand_normal_completion.json --historical-search-review --search-seed 71
```

Build the complete public Replay Coaching Report, or emit it with the retained
Historical Search Review summary from one analysis pass:

```powershell
python main.py run --input examples/historical_grand_normal_completion.json --historical-replay-coaching --search-seed 71 --samples 20 --seed 42
python main.py run --input examples/historical_grand_normal_completion.json --historical-search-review --historical-replay-coaching --search-seed 71 --samples 20 --seed 42
```

Replay Coaching is an opt-in historical-game workflow. It reuses
`--search-seed`, `--search-budget-profile`, `--samples`, and `--seed`; combined
Historical Search Review and Coaching run in one pass. `--output` writes the full
JSON report, while the default CLI is concise and `--quiet` preserves the normal
automation behavior. Public output excludes hands, final hidden ownership, Skat
identities, discards, compatible-world identities and contents, private Search
states, derived seeds, caches, branches, principal variations, ratings, and
rankings. Aggregate compatible-world counts and coverage remain public evidence
metadata.

Exercise Null-specific coaching wording without Suit/Grand card-point-margin
advice:

```powershell
python main.py run --input examples/historical_null_replay_coaching.json --historical-replay-coaching --search-seed 73 --samples 1 --seed 43
```

Review a complete Grand Ouvert through the same deterministic path:

```powershell
python main.py run --input examples/historical_grand_ouvert_review.json --historical-game-review --samples 20 --seed 42
```

Run the separate Historical Information-set Search Review. Existing bounded
Search/Coaching and Information-set Search/Coaching are separate families and
cannot be mixed:

```powershell
python main.py run --input examples/historical_grand_normal_completion.json --historical-information-set-search-review --search-seed 83 --search-budget-profile interactive_v1 --samples 1 --seed 47
```

Build the separate Information-set Replay Coaching report alone or return it
with the exact retained Information-set Review from one pass:

```powershell
python main.py run --input examples/historical_information_set_replay_coaching.json --historical-information-set-replay-coaching --search-seed 83 --search-budget-profile interactive_v1 --samples 1 --seed 47
python main.py run --input examples/historical_information_set_replay_coaching.json --historical-information-set-search-review --historical-information-set-replay-coaching --search-seed 83 --search-budget-profile interactive_v1 --samples 1 --seed 47
```

Information-set Coaching uses complete Information-set Candidate aggregates as
primary evidence. Same-selection PIMC and independent Immediate are diagnostics
only and never provide fallback. A partial, timeout, unavailable, or incomplete-
Candidate Search Decision is not assessable unless exactly one legal Card makes
it a factual forced move. The actual Card is attached after decision-time
analysis, and final Outcome Context is attached after Coaching.

Convert the versioned training/evaluation dataset example:

```powershell
python main.py run --input examples/training_dataset_normal_play.json
```

Evaluate bounded Search against Immediate on the default validation/test
partitions with one stable global decision-prefix cap:

```powershell
python main.py run --input examples/training_dataset_normal_play.json --evaluate-bounded-search --search-seed 71 --search-evaluation-max-decisions 10
```

Evaluate Information-set Search, same-selection PIMC, and independently seeded
Immediate on the same default validation/test partitions and deterministic
global prefix:

```powershell
python main.py run --input examples/training_dataset_normal_play.json --information-set-search-evaluation --search-seed 89 --search-evaluation-max-decisions 1
```

Audit exact stable-player overlap without generating samples:

```powershell
python main.py run --input examples/training_dataset_partition_audit.json --audit-dataset-partitions --dataset-partition-mode known_opponent
```

Run complete Known-opponent and unseen-player preparation, then the successful
unavailable boundary:

```powershell
python main.py run --input examples/training_dataset_preparation_known_opponent.json
python main.py run --input examples/training_dataset_preparation_unseen_player.json
python main.py run --input examples/training_dataset_preparation_unavailable.json
```

These root-selected workflows accept only `--input`, `--output`, `--quiet`, and
the cross-workflow `--include-provenance` option. Mode derives the algorithm;
there is no algorithm field, default weight, CLI override, or fallback.

Aggregate exact reusable player statistics from the same two-game container and
export a standalone statistics input:

```powershell
python main.py run --input examples/training_dataset_normal_play.json --aggregate-opponent-statistics --opponent-statistics-partition train --opponent-statistics-partition validation --opponent-statistics-before 2026-07-21T00:00:00Z --output outputs/historical-statistics.json --export-opponent-statistics outputs/opponent-statistics.json
```

Validate, normalize, and explain the external opponent-statistics example:

```powershell
python main.py run --input examples/opponent_statistics.json
```

Prepare an opponent-turn position with Multi-Step until the local player acts:

```powershell
python main.py run --input examples/grand_left_to_act_live.json --multi-step 1 --card-policy highest_point
```

Run local live Multi-Step analysis:

```powershell
python main.py run --input examples/grand_second_position.json --multi-step 2
```

Run one strict Search-aware Multi-Step decision and a Search-inclusive Policy
Comparison using the example's explicit small structural budget and Search seed:

```powershell
python main.py run --input examples/grand_bounded_search_exhaustive.json --multi-step 1
python main.py run --input examples/grand_bounded_search_exhaustive.json --multi-step 1 --compare-policies
```

Compare local card-selection policies:

```powershell
python main.py run --input examples/grand_second_position.json --multi-step 1 --compare-policies
```

Run the deterministic three-step coherent-world Policy Comparison example:

```powershell
python main.py run --input examples/grand_coherent_hidden_world.json --multi-step 3 --card-policy highest_expected_value --expected-value-samples 20 --compare-policies
```

Run exact evidence-constrained hidden-card inference through two Multi-Step
decisions:

```powershell
python main.py run --input examples/grand_hidden_card_inference.json --multi-step 2
```

The attributed Grand history confirms that `right` failed to follow clubs. The
root has exactly `275275` compatible labeled worlds, and a later simulated
public failure demonstrates evidence progression at a later step.

Print only policy-comparison output in the human-readable CLI view:

```powershell
python main.py run --input examples/grand_second_position.json --multi-step 1 --compare-policies --comparison-only
```

Run Multi-Step with side-specific opponent lead policies:

```powershell
python main.py run --input examples/grand_left_right_opponent_policies.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-lead-policy basic_defender_lead
```

Run post-game review with actual-card comparison:

```powershell
python main.py run --input examples/spades_post_game_actual_card_played.json
```

Validate example inputs and generated output workflows:

```powershell
python scripts/validate_examples_schema.py
python scripts/validate_generated_outputs_schema.py
```

## Live decision examples

These examples represent ongoing positions where the tool recommends a card.

Typical metadata:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended"
}
```

Live decision examples must not include post-game-only information such as `known_post_game` Skat visibility or completed game-end reasons. They may include `known_to_declarer` Skat cards when those cards are declarer-private live information.

| File                                       | Purpose                                                                                                                      |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `grand_second_position.json`               | Grand game, local player acts second. Also demonstrates automatic matador inference from known declarer-card context when possible. |
| `grand_declarer_known_to_declarer_live.json` | Grand live declarer position where the local declarer has declarer-private Skat visibility.                                 |
| `grand_third_position.json`                | Grand game, local player acts third.                                                                                         |
| `grand_leading.json`                       | Grand game where local player leads the trick.                                                                               |
| `grand_late_game_history_heavy_live.json`  | Late-game live defender position with zero opponent hand sizes, nine ordered completed tricks, and completed-trick matador inference. |
| `grand_left_right_opponent_policies.json`  | Grand game with distinct global, left-opponent, and right-opponent policy settings.                                           |
| `grand_coherent_hidden_world.json`         | Late Grand position used by three-step Policy Comparison to verify one shared root world, independent immutable policy paths, fixed hypothetical skat, and privacy-safe summaries. |
| `grand_hidden_card_inference.json`         | Grand position with attributed failure-to-follow evidence, exact compatible-world count and marginals, privacy-safe inference output, and later Multi-Step evidence progression. |
| `grand_bounded_search_exhaustive.json`     | One legal late Grand card, one compatible world, exact exhaustive Search completion, and a direct Search recommendation. |
| `grand_auto_search_fallback.json`          | The same late Grand information state with a one-node Search budget, a valid below-threshold partial result, and explicit Immediate fallback. |
| `information_set_search.json`              | One legal late Grand defender Card, one selected World, strict complete Information-set Search, exact nine settings, and safe aggregate output. |
| `information_set_search_multi_step.json`   | One legal late Grand defender Card for strict Information-set Search Multi-Step and five-policy comparison with no fallback. |
| `hearts_leading.json`                      | Suit game example.                                                                                                           |
| `null_second_position.json`                | Null game example.                                                                                                           |

## Midgame examples

| File                                      | Purpose                                                                                       |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| `grand_midgame_declarer_ahead.json`       | Midgame position where declarer is ahead by known points.                                     |
| `grand_midgame_defenders_ahead.json`      | Midgame position where defenders are ahead by known points.                                   |
| `grand_midgame_profile_preset_live.json`  | Live midgame position with strategic metadata, player profiles, and profile preset settings.  |
| `spades_midgame_defender_rearhand_live.json` | Live midgame defender rearhand position with explicit declarer seat, completed-trick metadata, and unknown skat. |

## Opponent-turn multi-step examples

These examples represent live positions where the local player is not the next
player to act. They are intended for the supported multi-step workflow, where
opponent action is simulated until the local player reaches a decision point.
Their Immediate Analysis output is intentionally unavailable: `legal_cards` and
`analysis_report` are empty, and `recommendation.card` is `null`.

| File                            | Purpose                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------- |
| `grand_left_to_act_live.json`   | `next_player: "left"`; multi-step simulates a left lead, right response, then local action. |
| `grand_right_to_act_live.json`  | `next_player: "right"`; multi-step simulates a right lead, then local action.               |

Run the left-to-act example:

```powershell
python main.py run --input examples/grand_left_to_act_live.json --multi-step 1 --card-policy highest_point
```

Run the right-to-act example:

```powershell
python main.py run --input examples/grand_right_to_act_live.json --multi-step 1 --card-policy highest_point
```

Both files are input-schema validated with all examples. They are covered by
focused behavioral assertions in `tests/test_examples.py` because their primary
supported workflow is multi-step opponent-turn preparation. Selected
opponent-turn generated outputs are also covered by generated-output schema
validation.

Multi-step also supports a one-card partial trick where `left` has already led
and `right` is next. In that phase the existing lead card is preserved and only
right's response is simulated before the local third-hand decision.

## Historical-game example

| File                                              | Purpose |
| ------------------------------------------------- | ------- |
| `historical_grand_normal_completion.json`         | Complete 32-card Grand deal with stable player IDs, non-Hand pickup/discards, ten legal tricks, inferred matadors, final points, and settlement. |
| `historical_grand_ouvert_review.json`              | Complete Grand Ouvert Hand game with exact declarer exposure from decision 1 and deterministic review of all 30 decisions. |
| `historical_grand_declarer_concession.json`       | Complete deal, exact 14-play Grand prefix with a two-card final trick, stable-ID defender consent, unresolved-point accounting, and adjudicated settlement. |
| `historical_grand_defender_concession.json`       | Complete deal, exact 14-play Grand prefix with a two-card final trick, stable conceding defender, joint liability, unresolved-point accounting, and adjudicated declarer win. |
| `historical_grand_declarer_card_exposure.json`    | Complete deal, exact 14-play Grand prefix, exact exposed declarer hand, stable shown-to defender and unanimous acceptances, accepted Schneider result, and settlement. |
| `historical_grand_declarer_card_exposure_continuation.json` | Complete normal Grand, exact timed public declarer hand, one stable defender continuation response, 30 actual plays, and ordinary settlement. |
| `historical_grand_defender_open_play.json` | Complete deal, exact 24-play Grand prefix, stable exposing defender, exact valid two-trick proof, privacy-safe assignment, and settlement. |
| `historical_grand_open_card_throw.json` | Complete deal, exact 24-play Grand prefix, stable defender throw, confirmed canonical hand, opposing-party assignment, and shared settlement. |
| `historical_party_wide_claim.json` | Complete deal, exact five-Trick Spades prefix, stable Declarer claimant, bounded exact valid party-wide Proof, diagnostic public summary, and reused Final Settlement. |
| `historical_information_set_replay_coaching.json` | Complete historical Game configured for separate Information-set Replay Coaching with retained Review reuse, complete-Candidate primary evidence, diagnostic baselines, and no fallback. |
| `historical_tactical_motif_review.json` | Complete historical Game configured for deterministic structural Tactical Motif Review without Search, quality, signaling, communication, or causal claims. |
| `historical_grand_defender_open_play_continuation.json` | Complete normal Grand with one timed exact returned defender hand and 30 actual plays. |
| `historical_grand_defender_open_play_continuation_declarer_concession.json` | Timed public defender hand after play 12, two later plays with exact hand shrinkage, then delegated declarer concession. |
| `historical_grand_declarer_card_exposure_continuation_defender_concession.json` | Public declarer hand after play 14 followed immediately by delegated defender concession with no post-event card decision. |
| `historical_null_replay_coaching.json` | Complete 32-card Null deal with stable player IDs and deterministic public Replay Coaching coverage for Null objective wording. |

This is a separate historical-game workflow, not a reconstructed local
post-game position. Dedicated generated-output scenarios cover the base
`historical_game_summary`, its optional decision-time snapshots, and the
seeded complete Immediate and Search reviews. Five scenarios cover the earlier
shortened base outputs. Three Issue #186 scenarios cover a Declarer Suit Claim, a
Defender Null Claim during an incomplete Trick, and one continuation before a
terminal Claim; at least one includes public Provenance. Snapshot-only generation does not run recommendation or
simulation. Review uses the normal and Grand Ouvert examples with 20 samples and
base seed 42; Ouvert rows are reviewed with the exact public declarer hand.
Historical Search Review uses an explicit Search seed and records eligible late
decisions alongside early out-of-profile decisions without serializing derived
per-decision Search seeds. Replay Coaching adds three generated-output scenarios:
normal Grand with Key Decisions and a Turning Point, normal Null with no margin
recommendation, and defender-open-play continuation before declarer concession.
Issue #189 adds a separate Historical Information-set Search Review scenario with
deterministic decision-time routing, no future leakage, and descriptive
Information-set/PIMC/Immediate/actual-Card metrics.
Issue #192 adds the separate Information-set Replay Coaching example and two
append-only scenarios: one normal Historical Coaching report and one party-wide
Claim ending with Information-set Coaching. They cover retained Review reuse,
complete-Candidate-only assessment, diagnostic baselines without fallback,
Outcome Context isolation, and opt-in public Provenance.
Issue #194 adds the separate Tactical Motif Review example and appends
`historical_tactical_motif_review_defender_partnership` and
`historical_party_wide_claim_tactical_motif_review`. They cover complete
30-Decision structural evidence including Defender partnership aggregates and
the exact 15-Decision pre-Claim prefix with complete Claim Result Provenance.
The two chain examples keep the continuation summary
separate from the reason-specific terminal summary and retain schema versions `1`.

## Historical-list examples

| File | Purpose |
| ---- | ------- |
| `fixed_three_player_historical_list_mixed.json` | One Played Game and 35 Passed Deals with a valid applied two-player external lot. |
| `fixed_three_player_historical_list_all_passed.json` | 36 Passed Deals with a three-player unresolved tie and explicit null lot. |
| `fixed_three_player_historical_list_comparison.json` | Two independent sources with changed table places, disjoint Played Game IDs, different Passed Deal counts, resolved ranks, and comparison-minus-reference deltas. |

Every source contains exactly 36 positions and uses mostly Passed Deals to keep
the fixtures bounded. Public output includes privacy-safe Entry Facts only in the
single-list progression. It never echoes Historical Game Records, hands, Skat,
discards, trick cards, ownership, Search state, or proof state. Comparison output
contains no progression or Entry Facts and makes no series, rating, skill,
winner, official cross-list ranking, or recommendation claim.

The three generated scenarios are appended after the previous unchanged 64 and
bring the Issue #130 matrix stage to exactly 67 outputs. Issue #134 preserves
those scenarios and adds three preparation outputs, as described below.

## Training-dataset example

| File | Purpose |
| ---- | ------- |
| `training_dataset_normal_play.json` | Two versioned Grand records in train and validation, with timestamps, repeated players in changed seats, opposite settlement outcomes, and 60 information-safe actual-card samples. It is also the historical-statistics aggregation source. |
| `training_dataset_variable_length.json` | One 14-play declarer-concession record ending with a two-card incomplete trick and producing exactly 14 information-safe actual-card samples. |
| `historical_opponent_policy_evaluation_dataset.json` | One earlier train source and one later validation target with repeated stable players in changed seats for rolling behavioral evaluation. |
| `training_dataset_partition_audit.json` | One timestamped normal-completion record in each partition, with the same exact stable players changing seats and no declared policy, for report-only or requested policy auditing. |
| `training_dataset_shortened_opponent_workflows.json` | Known-opponent dataset with an earlier normal source, an earlier zero-play concession source, and a later 14-decision concession target for mixed aggregation, export, and rolling evaluation. |
| `training_dataset_preparation_known_opponent.json` | Three timestamped zero-play Records producing one complete `temporal_known_opponent_v1` Plan, reusable version-1 dataset, and compliant audit. |
| `training_dataset_preparation_unseen_player.json` | Three Player-disjoint zero-play components producing one complete `component_balanced_unseen_player_v1` Plan, reusable version-1 dataset, and compliant audit. |
| `training_dataset_preparation_unavailable.json` | One Known-opponent Record without `played_at`, producing successful `missing_played_at` unavailability with null dataset/audit and no partial Plan. |

This separate workflow runs historical validation and snapshot generation but
does not run recommendations, review, or simulation. Its generated-output
scenario verifies the dedicated branch, all three partition-count entries,
stable sample IDs, legal labels, and identity-free features.
Each game contributes one sample per actual play; normal completion contributes
30 and any supported shortened event contributes zero through 29 subject to its
event prerequisites. Aggregation reuses the
dataset container but emits no samples, recommendations, review, or policy
application.

The three preparation examples use root `training_dataset_preparation_input` and
workflow identifier `training_dataset_preparation`. Output uses
`training_dataset_preparation_summary` with exactly `preparation_version`,
`plan`, `training_dataset_input`, and `partition_audit`. Plan and CLI output are
card-free. Complete output retains source cards only inside the nested losslessly
reusable Training Dataset. Preparation does not generate samples, train a model,
or automatically evaluate one.

The separate `--evaluate-bounded-search` mode does run Search and an independent
Immediate baseline over selected dataset records. It defaults to validation and
test partitions, preserves zero-decision records, optionally caps one global
stable decision prefix, and emits strict aggregate quality and performance
summaries instead of training samples.

The separate `--information-set-search-evaluation` mode runs Information-set
Search, PIMC on the exact retained selected-world sequence, and independently
seeded Immediate before attaching the actual Card. It has the same default
validation/test ordering and global decision cap. It produces descriptive
evaluation only; it does not change samples or targets, train a model, or claim a
ground-truth optimal Card.

## Opponent-statistics example

| File | Purpose |
| ---- | ------- |
| `opponent_statistics.json` | Two ordered online-platform captures with required provenance and distinct actionable cautious-defender and aggressive derivations. |
| `historical_opponent_statistics.json` | Two pre-game captures matching `player-a` and `player-c` in the historical Grand example with distinct actionable presets. |

This separate workflow validates the documented denominators and bounded source
rounding, preserves source values, and emits normalized `0..1` profile rates.
Its deterministic generated-output scenario verifies identity/order,
provenance, source percentages, additive `defender_rate`, null exact role counts,
unrounded role-evidence estimates, scoped confidence, signal explanations,
distinct classifications and presets, and fixed `2.0` tolerance metadata. It
also verifies that no recommendation or simulation output is produced.

The same file is reused with `grand_second_position.json` in a separate seeded
live generated-output scenario. Exact bindings map `opponent-123` to left and
`opponent-789` to right with `--use-profile-presets`; the output verifies
distinct cautious-defender/aggressive side policies and summary reconciliation.
The historical companion file drives one fixed-seed, bounded-sample review that
checks strict temporal eligibility, partial participant coverage, per-decision
side remapping, and aggregate application counts. A separate deterministic
scenario aggregates both timestamped training-dataset games with canonical
train/validation selection and a strict cutoff, checks exact counts and both
defender wins for the settlement loss, and validates the reusable export.
The focused rolling example demonstrates strict temporal selection, stable
identity, complete `simple_lowest` baseline evaluation, and low-confidence
coverage without upgrading profiles. Its generated-output scenario has no
actionable paired predictions; focused programmatic tests use 100 repeated
source records for medium-confidence actionable coverage.
The shortened opponent-workflow scenario verifies equal source-game weighting,
strict as-of construction, variable target cardinality, participant coverage,
and baseline/profile reconciliation without exposing terminal-event details.
The focused audit scenario uses `known_opponent`, verifies complete deterministic
membership, three-way overlap, directed coverage, unseen-player violations, and
the absence of samples or analysis products. The published `v0.11.0` generated-
output matrix therefore covers 64 scenarios, including the two explicit flat live Search method
branches, variable-length training data,
all five historical shortened kinds, declared-Ouvert historical review, both flat ongoing public-hand
continuations, both timed historical continuations, bounded exact defender-open-
play adjudication, open-card-throw adjudication, and the generated three-step
coherent hidden-world Policy Comparison scenario based on
`grand_coherent_hidden_world.json`, plus the exact hidden-card inference scenario
with a `275275`-world root and later evidence progression.
The two additional Search integration scenarios cover one executed strict
Search-aware Multi-Step decision and one comparison containing the unchanged
four legacy policies followed by `bounded_search`.
Three further scenarios cover flat post-game Search comparison through
`grand_bounded_search_post_game_review.json`, Historical Search Review with both
eligible and unavailable decisions, and a capped bounded-Search dataset
evaluation using the default validation/test partition selection.
Two Issue #119 scenarios cover defender continuation followed by terminal
declarer concession and immediate declarer-exposure continuation followed by
terminal defender concession. The previous 59 scenarios are unchanged.
Three Issue #124 scenarios then add normal Grand, Null, and shortened Replay
Coaching, bringing the published `v0.11.0` matrix to 64. Three Issue #130 scenarios append
the mixed list, all-passed list, and independent comparison, bringing the
`v0.12.0` milestone matrix at that stage to 67. Three Issue #134 scenarios append
complete Known-opponent, complete unseen-player, and unavailable preparation
without changing those prior 67, bringing the published `v0.12.0` baseline to 70.
Seven Issue #147 scenarios then append public provenance for Position Analysis,
Historical Game, Training Dataset, Training Dataset Preparation, Opponent
Statistics, Historical List, and Historical List Comparison. They reuse existing
fixtures, keep the first 70 scenarios unchanged, and bring the published
`v0.13.0` matrix to 77. The Training Dataset scenario also covers actual export-
artifact provenance.
Eight Issue #157 scenarios then append Live creation, apply/resume, analysis with
automatic Checkpoint, observed-card review, Undo/partial Correction, persistence
conflict, Retrospective export, and Retrospective finalization. The first 77
remain unchanged and the historical published `v0.16.0`, `v0.15.0`, and
`v0.14.0` totals are 85. Session operation JSON
uses `session.schema.json`; executed Position/Historical output uses
`output.schema.json`.
Issue #186 appends three Historical Claim scenarios, Issue #189 appends four
flat/Historical/Dataset Information-set Search scenarios, and Issue #190 appends
`information_set_search_multi_step` and
`information_set_search_policy_comparison`, reaching the prior 94-scenario
baseline. Issue #192 preserves those 94 definitions and order, then appends
`historical_information_set_replay_coaching` and
`historical_party_wide_claim_information_set_replay_coaching`. Issue #194
preserves those 96 definitions and order, then appends
`historical_tactical_motif_review_defender_partnership` and
`historical_party_wide_claim_tactical_motif_review`. The published `v0.17.0`
total is 98; the historical published 85-scenario facts remain unchanged. Issues
#198 and #199 change no example or generated-scenario definition.
The behavioral match
comparison does not evaluate recommendation quality or strategic strength.

The two aggregation games keep the same three case-sensitive players while
changing seats. `player-b` declares both Grand games, loses the first by final
settlement, and wins the second. This yields exact opposite settlement outcomes
without treating raw card points as the aggregation winner. The export retains
per-player latest-game `captured_at` provenance and can be loaded by standalone,
live, and strict time-safe historical profile workflows.

## Post-game review examples

These examples represent completed or retrospectively analyzed games.

Typical metadata:

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "game_end_reason": "normal_completion"
}
```

Post-game review examples may include known skat cards and completed game
information. The bounded-Search post-game workflow is narrower: it requires
`game_end_reason: "not_ended"`, rejects `known_post_game` Skat, and treats the
actual card only as a retrospective comparison label.

| File                                       | Purpose                                                                                                                      |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `grand_second_position_with_metadata.json` | Post-game metadata example with known post-game skat visibility, profile presets, and player profiles.                       |
| `grand_post_game_known_skat.json`          | Post-game review with known skat and completed tricks.                                                                       |
| `grand_post_game_mistake_actual_card.json` | Post-game review where the actual card is ranked below the recommendation and gap details are populated.                     |
| `grand_post_game_acceptable_actual_card.json` | Post-game review where the actual card is a stable acceptable alternative with only a small recommendation gap.            |
| `spades_post_game_actual_card_played.json` | Post-game review with `actual_card_played`, decision quality, decision factors, explanation, and recommendation gap details. |
| `null_post_game_objective_actual_card.json` | Null post-game review where the actual card differs from the recommendation but has no missed Null contract-objective utility. |
| `spades_post_game_defender_actual_card.json` | Defender-perspective post-game review with a concrete declarer seat and a suboptimal actual card.                          |
| `grand_bounded_search_post_game_review.json` | Late Grand flat Search review with an actual card, independent Immediate baseline, and Search aggregate comparisons.      |
| `grand_complete_declarer_win.json`         | Completed-result position where declarer wins; also demonstrates `bid_value` and partial SkWO performance metadata.          |
| `grand_complete_declarer_loss.json`        | Completed-result position where declarer loses; also demonstrates fixed three-player SkWO counterparty points.               |
| `grand_list_performance_input.json`        | Completed-result position plus already aggregated list performance input and output.                                         |
| `grand_list_game_contributions.json`       | Completed-result position plus list performance aggregated from normalized per-game contributions.                          |
| `grand_list_analysis_results.json`         | Completed-result position plus list performance aggregated from local analysis-result objects.                              |
| `grand_list_standings_input.json`          | Completed-result position plus explicit fixed three-player list standings output.                                            |

Run a post-game review example with actual-card comparison:

```powershell
python main.py run --input examples/spades_post_game_actual_card_played.json
```

Run a post-game review example with a missed recommendation:

```powershell
python main.py run --input examples/grand_post_game_mistake_actual_card.json
```

Run a post-game review example with an acceptable alternative:

```powershell
python main.py run --input examples/grand_post_game_acceptable_actual_card.json
```

Run a Null post-game review example where the objective, not raw card points,
determines decision quality:

```powershell
python main.py run --input examples/null_post_game_objective_actual_card.json
```

Run a defender-perspective post-game review example:

```powershell
python main.py run --input examples/spades_post_game_defender_actual_card.json
```

Run the bounded-Search post-game example:

```powershell
python main.py run --input examples/grand_bounded_search_post_game_review.json
```

Representative review outcomes covered by examples:

* `grand_post_game_mistake_actual_card.json` demonstrates `decision_quality: "mistake"`, two better alternatives, and a large expected-point-swing gap.
* `grand_post_game_acceptable_actual_card.json` demonstrates `decision_quality: "acceptable"` with a small expected-point-swing gap.
* `null_post_game_objective_actual_card.json` demonstrates `decision_quality: "optimal"` by Null contract objective even though the actual and recommended card-point swings differ.
* `spades_post_game_defender_actual_card.json` demonstrates local defender review with a concrete `declarer_player` and a suboptimal actual card.
* `grand_bounded_search_post_game_review.json` keeps Search and Immediate independent, then compares the actual and Immediate cards on Search's aggregate.
* Opponent-turn and completed-game examples demonstrate unavailable Immediate Analysis output; selected unavailable branches are covered by generated-output validation.

The output includes:

* `post_game_review_summary.is_available`
* `actual_card_played`
* `recommended_card`
* `actual_expected_point_swing`
* `recommended_expected_point_swing`
* `expected_point_swing_difference`
* `decision_quality`
* `decision_factors`
* `decision_explanation`
* `actual_card_rank`
* `recommended_card_rank`
* `candidate_count`
* `better_card_count`

## Claim and concession examples

The preferred `declarer_concession.json` example demonstrates a structured Grand
concession with nine hand cards, no required defender consent, preserved
unplayed points, a final adjudicated loss, and no achieved-level addition.
The `defender_concession.json` example identifies one concrete defender, binds
the full defending party, grants an undecided Grand to the declarer, preserves
all observed and unplayed points, and adds no optional achieved level.
The `declarer_card_exposure.json` example lays open the exact nine-card remaining
Grand hand, records both concrete acceptances, applies an accepted Schneider
claim without marking achieved Schneider, and assigns no remaining points.
The `declarer_card_exposure_continuation.json` example instead keeps a live
Spades game ongoing after one defender objects, makes the opponent declarer's
six current cards public, retains the co-defender and skat as unknown, and runs
deterministic Immediate Analysis without settlement.
The `defender_open_play.json` example supplies private exact hands for all three
players with two tricks left, exposes the local defender's two cards, proves the
claim exactly, assigns the rest tricks and 12 outstanding points to the
defenders, and omits both hidden proof hands from output.
The `defender_open_play_continuation.json` example instead keeps a live Grand
game ongoing after a 4.1.6 request. The exposing left defender has taken three
cards back, those exact cards remain known to all players, and deterministic
Immediate Analysis runs without proof, assignment, game end, or settlement.
The `open_card_throw.json` example records the left defender's complete two-card
throw with joint liability. Eight observed declarer tricks remain separate from
two rule-assigned tricks; all 63 outstanding points go to the declarer and create
open-throw Schneider and Schwarz after a deterministic non-excluded jack-only
assessment. The non-throwing local hand is redacted.
The `historical_party_wide_claim.json` example is separate from flat
`game_shortening`. It supplies one complete Historical world and a terminal
stable-ID Claim, executes one bounded exact Proof, accepts only a valid Result,
and emits no private exact state or complete proof tree.

Run the continuation example:

```powershell
python main.py run --input examples/declarer_card_exposure_continuation.json
```

Run the bounded exact defender-open-play example:

```powershell
python main.py run --input examples/defender_open_play.json
```

Run the defender-open-play continuation example:

```powershell
python main.py run --input examples/defender_open_play_continuation.json
```

Run the open-card-throw example:

```powershell
python main.py run --input examples/open_card_throw.json
```

The older examples retain simplified legacy game-end reasons:

* `declarer_claimed_remaining_tricks`
* `declarer_conceded_remaining_tricks`
* `defenders_conceded_remaining_tricks`

These examples should use:

```json
{
  "analysis_mode": "post_game_review"
}
```

because ended game reasons are post-game review information.

| File                                             | Purpose                             |
| ------------------------------------------------ | ----------------------------------- |
| `declarer_concession.json`                       | Structured no-assignment declarer concession under ISkO 4.4.1. |
| `defender_concession.json`                       | Structured joint-liability defender concession under ISkO 4.4.3. |
| `declarer_card_exposure.json`                    | Unanimously accepted no-assignment declarer card exposure under ISkO 4.4.4. |
| `declarer_card_exposure_continuation.json`       | Live ongoing play with the exact public opponent-declarer hand after an ISkO 4.4.4 objection. |
| `defender_open_play.json`                        | Exact final adjudication of a valid two-trick defender open play under ISkO 4.4.5. |
| `defender_open_play_continuation.json`           | Live ongoing play with the exposing defender's exact returned public hand under ISkO 4.4.5 and 4.1.6. |
| `open_card_throw.json`                            | Final joint-liability defender throw with opposing-party assignment and jack-only Schwarz assessment under ISkO 4.4.6. |
| `grand_claimed_remaining_tricks.json`            | Declarer claims remaining tricks.   |
| `grand_declarer_conceded_remaining_tricks.json`  | Legacy simplified declarer concession assignment. |
| `grand_defenders_conceded_remaining_tricks.json` | Defenders concede remaining tricks. |

Each structured flat example has deterministic generated-output and quiet JSON
coverage. The five earlier terminal Historical shortened kinds retain one
separate generated scenario each. The Historical party-wide Claim adds three
append-only scenarios, including incomplete-Trick and continuation coverage.
Both historical continuation kinds retain dedicated snapshot-transition
scenarios.

## Overbid examples

| File                                          | Purpose                                                                        |
| --------------------------------------------- | ------------------------------------------------------------------------------ |
| `grand_overbid_declarer_card_points_win.json` | Declarer wins by card points but loses settlement because the game is overbid. |
| `null_impossible_declaration_settlement.json`  | Null Hand Ouvert ends immediately and is settled from a separate Clubs Hand replacement selection. |

The impossible Null example preserves the original Null declaration, transfers
only Hand status to the replacement, and demonstrates the doubled loss without
card play. It also has a dedicated generated-output validation scenario.

## Performance rating examples

`grand_list_performance_input.json` demonstrates `performance_rating_system: "isko_list"` with optional already aggregated list or series totals:

```json
"list_performance_input": {
  "player_game_points": 120,
  "own_games_won": 3,
  "own_games_lost": 1,
  "other_players_lost_games": 2
}
```

Expected list performance calculation for the fixed three-player table:

* `own_game_bonus_points`: `3 * 50 + 1 * -50 = 100`
* `opponent_loss_bonus_points`: `2 * 40 = 80`
* `total_performance_points`: `120 + 100 + 80 = 300`
* `table_size`: `3` in the emitted `list_performance_summary`

The example still emits the normal single-game `performance_rating_summary`; `list_performance_summary` is additional and does not change it.

`grand_list_game_contributions.json` demonstrates `performance_rating_system: "isko_list"` with normalized per-game contributions:

```json
"list_game_contributions": [
  {
    "player_role": "declarer",
    "game_outcome": "declarer_win",
    "settlement_score": 96
  }
]
```

The example file includes one local declarer win with score `96`, one local declarer loss with score `-72`, and one local defender game where the declarer loses with score `-120`. It also includes stable `rated_player_id` and `game_id` metadata to demonstrate duplicate and same-player validation without changing output fields.

Expected normalized contribution list calculation for the example:

* `player_game_points`: `96 + (-72) = 24`
* `own_game_bonus_points`: `1 * 50 + 1 * (-50) = 0`
* `opponent_loss_bonus_points`: `1 * 40 = 40`
* `total_performance_points`: `24 + 0 + 40 = 64`
* `basis`: `normalized_game_contributions`
* `table_size`: `3` in the emitted `list_performance_summary`

`grand_list_analysis_results.json` demonstrates `performance_rating_system: "isko_list"` with local analysis-result objects for one consistently represented local player:

```json
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
  }
]
```

The example file includes one local declarer win with score `96`, one local declarer loss with score `-72`, and one local defender game where the declarer loses with score `-120`.

Expected local analysis-result list calculation for the example:

* `player_game_points`: `96 + (-72) = 24`
* `own_game_bonus_points`: `1 * 50 + 1 * (-50) = 0`
* `opponent_loss_bonus_points`: `1 * 40 = 40`
* `total_performance_points`: `24 + 0 + 40 = 64`
* `basis`: `local_analysis_results`
* `table_size`: `3` in the emitted `list_performance_summary`

The top-level completed game still emits its normal single-game `performance_rating_summary`; the local analysis-result aggregation only adds `list_performance_summary`.

`grand_list_standings_input.json` demonstrates `performance_rating_system:
"isko_list"` with explicit fixed three-player standings input:

```json
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
  ]
}
```

The example emits `list_standings_summary` with exactly three rows. Expected
standing totals are Alice `186`, Carol `138`, and Bob `-122`, ranked in that
order. Existing single-rated-player list examples continue to emit only
`list_performance_summary`.

## Matador inference examples

Automatic matador inference is demonstrated by examples where `matadors` is missing or `null`, but known declarer-card context is sufficient.

The engine currently infers matadors from known declarer-card context in:

* `hand`
* `skat`, when available and allowed by the analysis mode
* `completed_tricks`, but only from conservative concrete-declarer ownership facts with both `cards`, ordered `players`, and concrete `declarer_player`

If an explicit `matadors` value is provided, the explicit value is preserved.

`grand_late_game_history_heavy_live.json` omits explicit `matadors` and uses ordered completed-trick ownership from a concrete defender perspective to infer the Grand game value late in the game.

Null games do not use matadors.

## Left/right opponent policy examples

The project supports separate left/right opponent policy settings.

Input fields:

```json
{
  "opponent_lead_policy": "lowest_point",
  "opponent_response_policy": "lowest_point",
  "left_opponent_lead_policy": "highest_point",
  "left_opponent_response_policy": "basic_trick_play",
  "right_opponent_lead_policy": "basic_defender_lead",
  "right_opponent_response_policy": "basic_defender_response"
}
```

Global policy fields remain backward-compatible and cascade to both opponents. Side-specific fields override only their side.

Multi-step behavior:

* if `right` leads, `right_opponent_lead_policy` is used
* if `left` leads, `left_opponent_lead_policy` is used
* if `left` leads and `right` responds, `right_opponent_response_policy` is used
* candidate trick completion uses activated side response policies when an explicit response source exists

Run a multi-step simulation with separate left/right opponent policies:

```powershell
python main.py run --input examples/grand_left_right_opponent_policies.json --multi-step 2
```

Override side-specific opponent policies from the CLI:

```powershell
python main.py run --input examples/grand_left_right_opponent_policies.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-response-policy basic_defender_response
```

## Notes

The examples are also used as regression fixtures in `tests/test_examples.py`.

When adding new examples:

* keep card notation valid
* avoid duplicate known cards
* keep point totals within 120
* set `analysis_mode` consistently with the example type
* keep live decision examples free of post-game-only information
* include `declarer_player` as `left` or `right` when `player_role` is `defender`
* use `post_game_review` for completed games, claim/concession scenarios, known post-game skat, and `actual_card_played`
* set `game_end_reason` consistently with known card points
* add explicit `players` to completed tricks when winner metadata must be verifiable
* prefer `completed_tricks` over `played_cards`
* include ordered `completed_tricks[].players` when public ownership or failure-to-follow evidence should drive hidden-card inference; never rely on guessed ownership from legacy `played_cards`
* use attributed `completed_tricks` and empty legacy `played_cards` for Search methods
* give Search examples explicit structural budgets and separate Immediate/Search seeds; do not use wall-clock timeouts in deterministic generated examples
* use `performance_rating_system: "isko_list"` only when partial SkWO performance output should be demonstrated
* omit `matadors` only when automatic inference from known declarer-card context is intended
* prefer either top-level declaration fields or nested `game_declaration`; mixing is supported, with top-level fields taking precedence
* use documented declaration fields inside nested `game_declaration`; unknown nested metadata may be accepted for compatibility but is ignored by declaration, settlement, and overbid logic
* run `.\scripts\check.ps1` before manual review
* keep historical and training-dataset examples separate from flat position fields
* give every training record provenance and an explicit partition

## Expected output behavior

Generated outputs may include:

* `position`
* `settings`
* `opponent_policy_settings`
* `left_opponent_policy_settings`
* `right_opponent_policy_settings`
* `analysis_metadata`
* `information_policy_summary`
* `game_declaration`
* `game_value_summary`
* `overbid_summary`
* `score_summary`
* `game_result_summary`
* `adjusted_game_result_summary`
* `final_settlement_summary`
* `performance_rating_summary`
* `list_performance_summary`, if a list performance input mode is provided
* `list_standings_summary`, if fixed three-player standings input is provided
* `recommendation`
* `recommendation_method_summary` and `bounded_search_result`, only for an explicitly supplied recommendation method
* `bounded_search_post_game_review_summary`, for an explicit flat post-game Search method
* `information_set_search_result`, for strict flat Information-set Search
* `information_set_search_comparison`, for flat Post-game Information-set Search
* `post_game_review_summary`
* `multi_step_result`, if multi-step simulation is requested
* `policy_comparison_result`, if policy comparison is requested
* `hidden_card_inference_summary`, when confirmed attributed failure-to-follow evidence is available
* `field_provenance`, only when `--include-provenance` is supplied

Complete historical and training-dataset inputs instead use the mutually
exclusive `historical_game_summary` and `training_dataset_summary` branches.
Historical Search Review is nested under `historical_game_summary`; bounded-
Historical Replay Coaching is nested there as
`historical_replay_coaching_summary`; bounded-Search dataset evaluation uses the
separate
`bounded_search_evaluation_summary` branch.
Historical Information-set Search Review is nested under
`historical_game_summary` as
`historical_information_set_search_review_summary`; its Dataset evaluation uses
the separate `information_set_search_evaluation_summary` branch.
Separate Information-set Replay Coaching is nested under
`historical_game_summary` as
`historical_information_set_replay_coaching_summary`. It may be returned with
the Review attachment, but both reuse one retained Review execution.
Information-set Search Multi-Step nests the existing safe aggregate Result under
each executed or stopped recommendation Decision; Policy Comparison exposes only
the corresponding 16-field compact diagnostics.
Training-dataset aggregation instead uses
`historical_opponent_statistics_aggregation_summary`.
Fixed-three-player historical-list roots instead use the mutually exclusive
`fixed_three_player_historical_list_summary` or
`fixed_three_player_historical_list_comparison_summary` branch.

For detailed output field descriptions, see:

* [Output JSON documentation](output_json.md)
* [Hidden-card inference](hidden_card_inference.md)
* [Public field provenance](public_field_provenance.md)
