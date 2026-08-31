# Information-set Search workflows

## Scope

Issue #189 integrates the private version-1 Information-set Search foundation
and executor from Issues #187 and #188 into bounded public workflows. The new
flat recommendation method is:

```text
information_set_search
```

It executes `bounded_information_set_policy_search_v1` for controlled Player
`me` against separate deterministic fixed Policies for `left` and `right`. Equal
controlled Observations over the selected Compatible-world sequence receive one
common action. This is a bounded selected-world best response, not a three-player
equilibrium, joint Defender optimization, globally optimal imperfect-information
Policy, complete-contract solver, or calibrated probability model.

The current Package version is `0.17.0`; Public API contract version `1`, the seven Root
workflows, and the one `skat-ai = skat_ai.cli:main` Console Script are unchanged.

## Flat method and settings

Flat Position input selects `recommendation_method = information_set_search` and
must provide exactly these nine `information_set_search_settings` fields:

| Field | Contract |
| --- | --- |
| `random_seed` | Explicit integer world-selection seed; booleans are invalid. |
| `max_remaining_tricks` | Positive integer from `1` through `3`. |
| `max_depth_plies` | Positive integer. |
| `max_state_nodes` | Positive integer. |
| `max_information_sets` | Positive integer. |
| `max_selected_worlds` | Positive integer. |
| `max_sampled_worlds` | Positive integer, not greater than selected worlds. |
| `minimum_comparable_worlds` | Positive integer, not greater than selected worlds. |
| `wall_clock_timeout_ms` | Null or a positive integer operational cutoff. |

Missing and unknown fields are rejected. `bounded_search_settings` is also
rejected for this method. The existing flat Search boundary remains in force:
the game is ongoing, the local Player is to act, completed Tricks are attributed,
Skat visibility is decision-safe, and the input is either a Live Decision with
no actual Card or a Post-game Review with one actual Card.

Live routing is strict. It executes Information-set Search once and runs no PIMC
baseline, Immediate baseline, or fallback. A complete Result can provide the
top-level recommendation. Partial, timeout, and unavailable Results provide no
recommendation and do not trigger another method.

The existing omitted `immediate_expected_value`, strict `bounded_search`, and
Search-first `auto` behavior is unchanged. In particular, `auto` still tries
compatible-world PIMC first and only then uses its existing explicit Immediate
fallback; it does not route to Information-set Search.

## Fixed Player Policies

The workflow derives `left` and `right` lead and response Policies from the
existing effective opponent-policy settings after the established global,
side-specific, profile, and explicit-override precedence has been resolved. It
does not introduce a second policy configuration or expose source Profile,
Statistics, Confidence, or precedence details in the Search request.

Deterministic supported names remain `lowest_point`, `highest_point`,
`basic_trick_play`, `basic_defender_response`, and `basic_defender_lead`.
`random_legal` is not silently replaced: any effective left/right use produces
`unavailable` with `nondeterministic_fixed_policy`. A deterministic Policy that
is invalid for the fixed actor's role produces `unavailable` with
`unsupported_fixed_policy`. Neither case falls back.

## Public Result and privacy

`information_set_search_result` exposes only the safe version-1 aggregate:

* method, game type, status, stop reason, coverage, and bounded Policy claim;
* requested and consumed budgets;
* Compatible-world count and aggregate Candidate metrics;
* recommendation and controlled-Policy Decision count; and
* the effective left/right fixed Policy names.

It omits selected Worlds and assignments, exact World States, private hands,
actor Observations and Information Sets, the controlled contingent Policy table
and actions, hidden ownership, derived seeds, caches, memoization, and branches.
The count of controlled Policy Decisions does not reveal the private table.

## Post-game comparison

Flat Post-game Review executes the stages in this order:

1. Run Information-set Search from decision-time information.
2. Run compatible-world PIMC on the exact retained selected-world sequence when
   that selection is available.
3. Run Immediate independently with the ordinary flat Immediate sample count and
   seed, without receiving the retained selection.
4. Read and attach `actual_card_played` only after all three analyses finish.

The separate `information_set_search_comparison` reports method availability,
recommendation agreement, cross-method ranks, actual-card agreement, and
same-denominator Information-set-minus-PIMC aggregate deltas. It is descriptive.
Agreement with the observed Card is not an accuracy, truth, optimal-label,
causal, skill, or strategic-strength claim. The observed Card never changes
world selection, Search, PIMC, or Immediate analysis.

## Historical Review

Historical Information-set Search Review is a separate opt-in Historical Game
mode:

```powershell
skatmind run --input historical.json --historical-information-set-search-review --search-seed 71
```

It requires `--search-seed`. It reuses `--search-budget-profile`, `--samples`,
and `--seed`; the default profile is `historical_review_v1`. It conflicts with
both `--historical-search-review` and `--historical-replay-coaching` rather than
combining or reclassifying either workflow.

Each actual play is reconstructed from its information-safe pre-play Snapshot.
The decision Search seed is deterministically derived from the explicit base
seed, stable Game identity, and decision index and is not serialized. Effective
left/right Policies reuse existing time-safe Historical profile and explicit
override precedence. Information-set Search, same-selection PIMC, and an
independently seeded Immediate baseline run before the observed Card is attached.

`historical_information_set_search_review_summary` preserves one row per actual
play, including zero-decision compatibility, and reconciles status, coverage,
selection, recommendation, agreement, and bounded breakdown counts. It makes no
accuracy or ground-truth claim.

## Training Dataset evaluation

Training Dataset version `1` has a separate evaluation-only mode:

```powershell
skatmind run --input dataset.json --information-set-search-evaluation --search-seed 71
```

It defaults to canonical `validation`, then `test`, and to profile
`evaluation_v1`. Repeatable `--search-evaluation-partition` can select `train`,
`validation`, or `test`; `--search-evaluation-max-decisions` applies one positive
global cap to the stable selected Decision prefix. Source Record order and
Decision order are preserved, zero-decision Records remain represented, Search
seeds are deterministically derived per stable Game Decision, and the Immediate
baseline uses deterministic independent seeds.

The mode returns `information_set_search_evaluation_summary` with the same safe
per-Decision comparison and reconciled aggregate breakdowns. It is mutually
exclusive with bounded-Search evaluation and the other Training Dataset
operations. It performs no model training, ordinary sample conversion, target
generation, or partition mutation. Training Dataset schema version `1`, Feature
generation version `1`, target `actual_card_played`, Features, labels, and sample
IDs are unchanged.

## Provenance

Application execution captures complete internal Information-set Search
provenance for the stages actually retained: input/settings, Information-set
Result, same-selection PIMC, independent Immediate, observed Card, comparison,
and aggregate Result as applicable. Provenance construction consumes those
retained values and does not rerun Search, selection, PIMC, Immediate,
Historical replay, or Dataset evaluation.

Public provenance remains default-omitted. `include_provenance=True` or
`--include-provenance` exposes only the existing redacted complete Root Result
mapping. Public Result and provenance attachments omit the private controlled
Policy table, Observations, exact Worlds and hands, selected assignments, caches,
memoization, and derived seeds.

## Multi-Step and Policy Comparison

Issue #190 adds version-1 strict Multi-Step and Policy Comparison routing without
changing the flat, Historical Review, or Training Dataset behavior above. Every
local decision derives a child of the explicit Information-set Search seed,
executes a fresh Search from the current public state, and then executes any
recommended Card in the separate private coherent World. Search Worlds and the
private controlled Policy are not reused across decisions.

A Result without a recommendation stops before local play with
`local_policy_no_recommendation`; there is no fallback. Safe output retains one
Decision with the existing aggregate Result nested beneath it. Policy Comparison
retains the default four policies and appends `information_set_search` exactly
once and last. All paths use independent copies of one shared coherent root; a
stopped Search row remains visible but ineligible under the existing ranking.
The row exposes exact 16-field compact diagnostics and no private World or Policy
table. Existing `auto` remains unchanged, and there is no `information_set_auto`.

See [Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md)
for the seed, Decision, diagnostics, provenance, and stop contracts.

## Schemas, examples, and scenarios

Issue #189 adds exactly four authoritative schemas with byte-identical Packaged
Schema Resources:

* `information_set_search_result.schema.json`;
* `information_set_search_comparison.schema.json`;
* `historical_information_set_search_review.schema.json`; and
* `information_set_search_evaluation.schema.json`.

`examples/information_set_search.json` is the Issue #189 flat input example.
Issue #190 adds `examples/information_set_search_multi_step.json`. Four Issue
#189 generated-output scenarios cover complete Live routing, flat Post-game
comparison, Historical Information-set Search Review, and Training Dataset
evaluation. Two appended Issue #190 scenarios cover Multi-Step and Policy
Comparison. The Issue #190 baseline therefore reached 69 authoritative and
packaged Schemas, six unchanged Session examples, and 94 generated-output
scenarios. Issue #191 changed neither count. Issue #192 subsequently adds one
strict Information-set Replay Coaching Schema, one Root example, and two
append-only scenarios, bringing the Issue #192 totals to 70 Schemas, six
Session examples, and 96 scenarios. The historical published `v0.16.0` totals remain
historical Release facts.

Issue #193 adds only a synthetic benchmark corpus, repository-local runner,
focused tests, and performance documentation. It adds no Schema, example,
generated scenario, route, profile, Public API, Package version, or count change.
Issue #194 separately adds one Tactical Motif Review Schema, one Root example,
and two scenarios, bringing the final published totals to 71 Schemas and 98
scenarios without changing Information-set Search.

## Integration boundary

Issue #190 completes only Multi-Step and Policy Comparison integration. Issue
#191 subsequently adds strict one-Decision Match Capture and Analysis Reports,
exact Report-source transfer, focused Strategy Teacher Evidence, Dataset-v2
propagation, cross-game Summary counts, and existing local Corpus workflow
support. It adds no Root workflow, Public API, Schema, example, or generated
scenario. Issue #192 separately adds Match Historical Information-set Review and
Coaching plus complete-Candidate-only Replay Coaching with diagnostic PIMC and
Immediate and no fallback. Issue #193 adds separate local benchmark evidence
only. Production routing, product/runtime performance gates, existing profiles,
and `auto` remain unchanged.
See [Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md)
and [Information-set Replay Coaching and Match Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md).
See [Information-set Search performance](information_set_search_performance.md)
for the benchmark corpus, frozen evidence, local measurements, and limitations.

The implementation remains limited to at most three unresolved Tricks and to the
selected Compatible-world sequence under supplied fixed Policies. Exact
Compatible-world counts do not identify the real deal; sampled Worlds are not
calibrated probabilities. No equilibrium, Nash, global-optimality,
complete-contract, full Strategy-Fusion correction, or latency guarantee is
claimed.
