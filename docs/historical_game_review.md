# Historical game review

Historical game review evaluates every actual card play in a validated normal-
completion, including either timed public-hand continuation, declarer-concession,
defender-concession, declarer-card-exposure, or terminal defender-open-play record through the existing immediate
recommendation and post-game review logic. Normal completion remains 30
decisions; shortened review contains zero through 29 decisions. The terminal
event is not evaluated as a card choice.

Rolling opponent-policy evaluation is a separate workflow. It predicts the
acting player's observed card with their own game-start profile and the fixed
baseline, and it does not call this expected-value recommendation or decision-
quality review path. See
[Rolling opponent-policy evaluation](opponent_policy_evaluation.md).

## CLI

Use the historical-only flag with an optional sample count and base seed:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --samples 100 --seed 42
```

The complete Grand Ouvert example uses the same reviewed path:

```powershell
python main.py --input examples/historical_grand_ouvert_review.json --historical-game-review --samples 20 --seed 42
```

`--historical-game-review` automatically generates the decision snapshots used
internally. Adding `--historical-decision-snapshots` also emits those snapshots;
it does not generate them a second time. `--samples` and `--seed` are accepted
for historical input only with review. A time-safe external profile file may be
added with `--opponent-statistics-file` and `--use-profile-presets`; comparison
and multi-step overrides remain unsupported.

When `--samples` is omitted, review uses the existing immediate-analysis default
of 100 samples. A supplied base seed is converted to a per-decision seed with:

```text
effective_random_seed = base_random_seed + decision_index - 1
```

Decision 1 therefore uses the base seed and the final actual decision uses its
one-based index offset. Without a base seed, every row exposes
`effective_random_seed: null` and
keeps the existing unseeded simulation behavior. The opponent policy mode is
`default` without external profiles and `external_profiles` when the validated
historical binding is active.

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

When the visible attributed prefix confirms a legal failure to follow, review
derives one exact hidden-card inference model for that decision. It uses only the
local hand, public prefix and current trick, authorized public hands, and
legitimately known skat. Canonical historical replay proves the supplied prefix
is legal; complete actual hands, the actual next card, future cards, result,
game value, overbid, settlement, and not-yet-visible events are not model inputs.

For declared Ouvert, the exact current declarer hand is public from decision 1.
After either continuation boundary, the stable public-hand owner is mapped
relative to each actor and supplied through the existing exact
`PublicHandConstraint`. No extra card enters that hand. Pre-event decisions are
identical to the no-event record, and no event, claim, or response decision is
reviewed.

The coherent private root used by Multi-Step is not created from the historical
deal for review. Comparison and Multi-Step overrides remain unsupported, and
actual future opponent hands never enter an earlier decision. Each row continues
to use only its Immediate Analysis counterfactual samples from public decision-
time information.

## Review output

`historical_game_review_summary` is nested under `historical_game_summary`. It
contains:

* schema version, analysis method, and `decision_time` information policy
* effective sample, base-seed, and default-policy settings
* one chronological decision row per actual supplied play
* reviewed and unavailable totals
* counts for `optimal`, `acceptable`, `suboptimal`, `mistake`, and
  `not_available`
* exactly three player summaries in input order, with actual per-player counts

A zero-play concession has an empty decision array, zero overall counts, and
three zero-decision player summaries. In shortened non-empty records, player
counts may differ and always sum to the total.

With external profiles, each row additionally reconciles acting, left, and right
stable identities, match/actionability status, precedence, and effective side
policies. The review also exposes bounded profile-application counts; the root
output exposes participant matching and strict temporal eligibility. See
[Historical opponent profiles](historical_opponent_profiles.md).

Every reviewed row contains the full legal-card list, one recommendation, the
existing candidate analysis report for all legal alternatives, and the existing
post-game review summary with ranks, quality, factors, and explanation. One-card
decisions, including the final three plays, are still reviewed.

A reviewed row with confirmed failure-to-follow evidence also contains the
strict version-1 privacy-safe `hidden_card_inference_summary`. It reports exact
compatible-world counts and marginals, never actual or sampled hands, sampled
skat, coherent-root ownership, or dynamic-programming tables. See
[Hidden-card inference](hidden_card_inference.md).

Player and overall counts reconcile with the decision rows. They are descriptive
summaries only. They are not grades, percentages, skill ratings, winners, or
cross-player rankings.

## Ouvert review

Declared-Ouvert snapshots are adapted into the exact `declared_ouvert` public-
hand constraint and use normal recommendation and actual-card comparison. A
normal completed game has 30 reviewed and zero unavailable decisions unless an
independent limitation applies. Played declarer cards disappear from later
constraints. Each Ouvert row serializes only the authorized public hand; hidden
defender hands, skat, and future cards remain absent.

## Scope

This review evaluates the current immediate expected-value or Null-objective
heuristic at each historical decision. It is not a perfect-information solver
and does not optimize complete-contract expected value or complete-game play.
Historical review can consume time-safe actionable external profiles and existing
explicit policy precedence, but it does not evaluate policy effects. The output
is not a training or evaluation dataset record. The separate training-data workflow
uses decision snapshots directly; recommendation cards, candidate reports, and
decision-quality values are never training features or labels.

Issue #104 preserves the review seed rule, decision count, recommendation
objective, policy behavior, and quality classification while adding the optional
inference summary to reviewed rows.

Complete-game retrospective analysis remains `partially_supported` because
additional approved historical end reasons, complete auction
representation, and other approved v1 gaps remain open.

The stable structure is defined by
[`schemas/historical_game_review.schema.json`](../schemas/historical_game_review.schema.json)
and referenced by the public output schema.
