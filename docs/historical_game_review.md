# Historical game review

Historical game review evaluates all 30 actual plays in a validated normal-play
historical game through the existing immediate recommendation and post-game
review logic. It does not introduce a separate historical recommendation
algorithm.

## CLI

Use the historical-only flag with an optional sample count and base seed:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --samples 100 --seed 42
```

`--historical-game-review` automatically generates the decision snapshots used
internally. Adding `--historical-decision-snapshots` also emits those snapshots;
it does not generate them a second time. `--samples` and `--seed` are accepted
for historical input only with review. Other recommendation, policy, profile,
comparison, and multi-step overrides remain unsupported.

When `--samples` is omitted, review uses the existing immediate-analysis default
of 100 samples. A supplied base seed is converted to a per-decision seed with:

```text
effective_random_seed = base_random_seed + decision_index - 1
```

Decision 1 therefore uses the base seed and decision 30 uses the base seed plus
29. Without a base seed, every row exposes `effective_random_seed: null` and
keeps the existing unseeded simulation behavior. The opponent policy mode is
fixed to `default` in this workflow.

## Information boundary

Each decision is independently adapted from its corresponding decision-time
snapshot. The acting player becomes `me`; stable left/right and declarer IDs are
mapped to the local model; prior completed tricks, the current trick, public
point totals, opponent hand sizes, permitted skat knowledge, and visible
matadors come only from that snapshot. The position is analyzed as not ended
with `next_player: "me"`.

The actual card remains outside the analysis state and is passed separately to
post-game review. Hidden initial opponent hands, future plays, later decision
results, final points, final winner, achieved Schneider or Schwarz, final game
value, overbid outcome, and settlement are not analysis inputs. The final
historical outcome remains available beside the review in the parent summary,
but it cannot influence an earlier recommendation or quality classification.

## Review output

`historical_game_review_summary` is nested under `historical_game_summary`. It
contains:

* schema version, analysis method, and `decision_time` information policy
* effective sample, base-seed, and default-policy settings
* exactly 30 chronological decision rows
* reviewed and unavailable totals
* counts for `optimal`, `acceptable`, `suboptimal`, `mistake`, and
  `not_available`
* exactly three player summaries in input order, with ten decisions each

Every reviewed row contains the full legal-card list, one recommendation, the
existing candidate analysis report for all legal alternatives, and the existing
post-game review summary with ranks, quality, factors, and explanation. One-card
decisions, including the final three plays, are still reviewed.

Player and overall counts reconcile with the decision rows. They are descriptive
summaries only. They are not grades, percentages, skill ratings, winners, or
cross-player rankings.

## Ouvert limitation

Current opponent-hand simulation cannot consume publicly exposed opponent-card
identities. Every snapshot with `public_exposed_cards` therefore skips
simulation and returns:

```text
public_exposed_cards_not_supported
```

The row preserves its identity, actual card, and effective seed, while exposing
an empty legal-card list and analysis report, a null recommendation card, and
the existing unavailable post-game review shape with `not_available` quality.
Counts still reconcile across all 30 rows and all three players. Exposed-card-
aware simulation is not implemented by this workflow.

## Scope

This review evaluates the current immediate expected-value or Null-objective
heuristic at each historical decision. It is not a perfect-information solver
and does not optimize complete-contract expected value or complete-game play.
Historical opponent policies and profiles are not configurable. The output is
not a training or evaluation dataset record. The separate training-data workflow
uses decision snapshots directly; recommendation cards, candidate reports, and
decision-quality values are never training features or labels.

Complete-game retrospective analysis remains `partially_supported` because
ouvert simulation, additional approved historical end reasons, complete auction
representation, and other approved v1 gaps remain open.

The stable structure is defined by
[`schemas/historical_game_review.schema.json`](../schemas/historical_game_review.schema.json)
and referenced by the public output schema.
