# Information-set Replay Coaching and Match Historical analysis

## Scope and compatibility

Issue #192 adds a separate version-1 Information-set Replay Coaching path and
integrates Historical Information-set Search Review and Coaching into private
Match analysis. The existing bounded-PIMC Replay Coaching path remains unchanged.

The new path reuses one retained
`HistoricalInformationSetSearchReviewSummaryV1` and adds no Search rerun, new
Root workflow, Console Script, or Match browser operation. Package version
`0.16.0`, Python `>=3.13`, Public API contract version `1`, seven Root workflows,
one Console Script, Match Historical Analysis Options version `1`, Settlement
Normative Matrix version `3` with 61 cases, and six Session examples remain
unchanged.

Issue #190 established the prior working baseline of 69 authoritative and
packaged Schemas and 94 generated-output scenarios. Issue #191 changed neither
count. Issue #192 adds one Schema and two append-only scenarios, bringing the
Issue #192 point-in-time baseline to 70 authoritative and packaged Schemas and
96 scenarios. Issue #193 changes neither count. Issue #194 subsequently adds one
Tactical Motif Review Schema and two scenarios, bringing the current unreleased
working baseline to 71 Schemas and 98 scenarios. The published `v0.16.0`
baseline remains 63 Schemas, six Session examples, and 85 scenarios.

## Separate Coaching families

The existing family remains:

```text
Historical Search Review
    -> bounded compatible-world PIMC Search
    -> independent Immediate baseline
    -> actual-Card assessment
    -> Replay Coaching
```

Its evidence remains Search-first and can use its existing Immediate-only
fallback when bounded Search is unavailable. Its method, public shape, Schema,
serialization, evidence bases, factors, limitations, wording, and generated
outputs are unchanged. In particular, it remains subject to
`determinization_strategy_fusion`.

The new family is:

```text
Historical Information-set Search Review
    -> complete Information-set Candidate evidence only
    -> diagnostic same-selection PIMC and independent Immediate
    -> actual-Card assessment
    -> Information-set Replay Coaching
```

Its method is:

```text
historical_information_set_replay_coaching_v1
```

The two families are distinct contracts and distinct Historical output
attachments:

```text
historical_replay_coaching_summary
historical_information_set_replay_coaching_summary
```

Existing Search Review and Replay Coaching may be requested together.
Information-set Search Review and Information-set Replay Coaching may be
requested together. The existing and Information-set families cannot be mixed
in one invocation. Decision Snapshots and Immediate Historical Review may be
combined with either family.

## Versions and policies

The focused versions are all `1`:

```text
INFORMATION_SET_REPLAY_COACHING_EVIDENCE_VERSION
INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_VERSION
INFORMATION_SET_REPLAY_COACHING_REPORT_VERSION
MATCH_HISTORICAL_INFORMATION_SET_COACHING_INTEGRATION_VERSION
```

The stable policies are:

```text
source:
    retained_historical_information_set_search_review_without_rerun
information:
    decision_time_analysis_then_actual_card_then_outcome_context
primary evidence:
    information_set_candidates_primary_pimc_and_immediate_diagnostic_only
assessment:
    complete_information_set_candidates_or_not_assessable
prioritization:
    existing_objective_priority_without_baseline_fallback
guidance:
    existing_deterministic_templates_without_tactical_inference
outcome:
    final_context_after_coaching
public output:
    safe_report_without_private_policy_world_or_observation
Match execution:
    one_historical_application_with_shared_information_set_review
Match mode separation:
    separate_from_existing_pimc_replay_coaching
```

These strings describe validated behavior. They do not independently execute an
operation or claim equilibrium, accuracy, causality, or global optimality.

## Retained Review reuse

Information-set Coaching consumes exactly one retained Historical
Information-set Search Review. For each actually played Card, the workflow:

1. Builds the decision-time snapshot once.
2. Executes Information-set Search, same-selection PIMC, and independent
   Immediate once while building the retained Review row.
3. Reconstructs the exact pre-actual comparison from that row without analysis.
4. Attaches the legal observed Card and requires exact equality with the retained
   final comparison.
5. Builds the assessment, prioritization, patterns, Guidance, and report without
   rerunning the Review.
6. Attaches final Outcome Context only after Coaching derivation is complete.

When both Information-set Review and Coaching are requested, the same retained
Review produces both public attachments. Coaching alone still builds that Review
once internally but does not return the separate Review attachment.

## Information boundary

`InformationSetReplayCoachingDecisionTimeEvidenceV1` contains source Game and
Decision identity, trick/play position, acting Player and seat, local side,
contract, root seat, Replay Coaching phase, remaining Tricks, canonical legal
Cards, and one exact
`InformationSetSearchComparisonPreActualAnalysisV1`.

That pre-actual value may retain:

* the private Information-set Result for internal validation;
* its safe public aggregate projection;
* same-selection PIMC on the exact retained selected-World sequence;
* the independently executed Immediate recommendation; and
* the exact same-selection flag.

It contains no actual Card, future Play, final outcome, final Settlement,
controlled Policy table, actor Observation, selected World, Exact State, hidden
hand, ownership assignment, cache, branch, or child seed.

The actual Card is attached only in the retrospective assessment and must be one
of the decision-time legal Cards. Final outcome is attached later in the report
and cannot change evidence selection, assessment, impact, prioritization,
patterns, or Guidance.

## Primary and diagnostic evidence

Complete Information-set Candidate aggregates are the only primary strategic
evidence. The evidence bases, in canonical order, are:

```text
information_set_single_exact_world
information_set_all_compatible_worlds
information_set_sampled_compatible_worlds
none
```

Same-selection PIMC and Immediate remain descriptive diagnostics. Their
recommendations and agreement values may appear in the comparison and coverage
summaries, but they never:

* make an incomplete Information-set result assessable;
* replace a missing Information-set recommendation;
* change Candidate metrics, ranking, or best Card;
* select an impact tier;
* act as fallback evidence; or
* become preferred Teacher evidence or ground truth.

Information-set/PIMC or Information-set/Immediate divergence can contribute
descriptive one-game pattern evidence, but it is not an actionable error pattern
for this method.

## Assessability and forced moves

A Decision with exactly one legal Card is always the factual `forced_move` case,
even when Search is partial, timed out, unavailable, or absent. It has
`no_missed_impact` and creates no alternative-card claim.

A Decision with multiple legal Cards is assessable only when the Information-set
Result is `complete`, includes internally valid Candidate Results for every legal
root Card, and retains a valid recommendation. Complete coverage may be one exact
World, all compatible Worlds, or selected sampled compatible Worlds.

A partial, timeout, unavailable, missing, or incomplete-Candidate result is
`not_assessable`, with evidence basis `none` and impact tier `not_assessable`.
Diagnostic PIMC or Immediate availability does not change that result. The
report explicitly counts forced, assessable, best-or-equivalent,
strictly-below-best, and not-assessable Decisions.

## Candidate assessment and impact

The exact Information-set recommendation is the best Card. Candidate comparison
uses the existing local-side objective order:

1. Contract-success rate.
2. Mean local-side Game score.
3. Suit or Grand mean local-side card-point margin.
4. Canonical Card order only for deterministic ranking.

Equal supported aggregate metrics are `best_or_equivalent`, even when canonical
rank or Card identity differs. Otherwise the actual Card is
`strictly_below_best`, and the first positive objective gap selects
`contract_success`, `settlement_score`, or `card_point_margin`. Null never uses a
card-point-margin objective.

The assessment statuses are:

```text
forced_move
best_or_equivalent
strictly_below_best
not_assessable
```

The Information-set impact tiers are:

```text
no_missed_impact
contract_success
settlement_score
card_point_margin
not_assessable
```

There is no `immediate_only` tier. Factors are limited to factual forced,
aggregate-equivalence, objective-gap, Search-unavailable, no-evidence, and Null-
margin facts. PIMC and Immediate agreement is not an impact factor.

## Coaching composition

The new assessment type reuses the existing deterministic method-neutral
Coaching algorithms rather than duplicating their ranking or outcome logic:

* at most five Key Decisions;
* Contract success before Settlement score before card-point margin;
* positive primary-gap ordering and canonical ties;
* decision-opportunity and recorded-outcome Turning Points;
* Player, role, opening/middle/endgame phase, and contract scopes;
* a two-distinct-decision threshold for one-game patterns;
* actionable and descriptive pattern separation;
* at most five deterministic decision and five pattern recommendations;
* existing fixed English templates without tactical inference; and
* the existing privacy-safe Game and final Outcome Context builders.

Forced moves, best-or-equivalent choices, and not-assessable Decisions are not
Key Decisions. Decision-opportunity Turning Points require supported complete
Information-set Contract-success evidence. Recorded-outcome Turning Points
remain facts about the actual recorded prefix and may occur at a forced move.

Patterns describe recurrence within one recorded Game only. They are not cross-
game statistics, confidence estimates, permanent Player traits, grades, ratings,
or significance tests. Guidance does not infer tactical motifs, intent,
signaling, communication, or causality.

## Report and Outcome Context

`InformationSetReplayCoachingReportV1` contains exact report policies and source
Review settings, privacy-safe Game context, one chronological assessment per
actually played Card, retained prioritization and Guidance, complete coverage,
Player/role/phase/contract summaries, final Outcome Context, and canonical
limitations. Zero-decision and supported variable-length shortened Games,
including the party-wide Claim ending, are valid.

Coverage includes assessment, evidence-basis, impact, Search-status, World-
coverage, Information-set/PIMC agreement, Information-set/Immediate agreement,
Key Decision, Turning Point, pattern, and recommendation counts. PIMC and
Immediate counts remain diagnostic.

Outcome Context describes the recorded final result and Settlement only. It is
attached after Coaching and is explicitly not decision evidence or proof that a
Card caused the result.

## Historical and CLI execution

Historical Application and public execution options add the default-false
`information_set_replay_coaching` option. The Root CLI adds:

```text
--historical-information-set-replay-coaching
```

It reuses:

```text
--historical-information-set-search-review
--search-seed
--search-budget-profile
--samples
--seed
--include-provenance
--quiet
```

Every Search/Coaching family requires an explicit Search seed. The Immediate
sample count and seed remain the independent diagnostic baseline settings. The
installed `skat-ai`, `python -m skat_ai`, and Legacy `python main.py` forms have
the same validation and output.

Concise presentation reports source Game, Decision and assessable counts,
not-assessable Decisions, Key Decisions, Turning Points, patterns,
recommendations, and Information-set status/World coverage. It emits no private
Policy, Observation, World, hand, cache, branch, or seed. `--quiet` preserves the
existing JSON automation behavior.

## Match Historical integration

Private `MatchHistoricalAnalysisOptionsV1` adds default-false
`information_set_search_review` and `information_set_replay_coaching` fields
without changing its version. The existing Historical analysis form adds both
controls and reuses its Search seed, Search budget profile, Immediate sample and
seed, and Profile-Preset controls. It adds no raw Budget form, browser operation,
automatic analysis, or persisted report.

One available Match Historical action still performs exactly one strict
Historical materialization, one Historical Request build, one Historical
Application invocation, one Root Result validation, one Match reconciliation,
and at most one revision-scoped ephemeral Report insertion. Existing report ID,
generation, invalidation, eviction, stale-result rejection, concurrency, and
authenticated exact Root Result download behavior remains unchanged.

The Match page renders only curated safe Review and Coaching facts: status and
World coverage, diagnostic agreement, assessment coverage, Key Decisions, both
Turning Point types, recommendations, and bounded Outcome Context. Historical
Reports remain ineligible for Strategy Teacher Report-source download.

## Match Profiles and fixed Policies

For Match Historical Information-set Review or Coaching with Profile Presets
enabled, the adapter reuses the existing strict-before-Match Statistics
preparation and injects the eligible document through the Historical Application
external-document boundary. Existing time-safe behavior derives effective
left/right deterministic Policies for each Decision. Those effective Policies
become fixed Information-set Search actors.

Profiles do not weight compatible Worlds, alter World selection probabilities,
or expose Statistics Records in Coaching output. Existing bounded-PIMC
Historical Search Review and existing Replay Coaching remain unaffected by
Profile settings unless independently requested Immediate Review already uses
the existing profile path. Workspace Commentary and Response Links remain
outside Review and Coaching evidence.

## Provenance

Issue #192 adds complete internal retained-stage and opt-in public field
Provenance without rerunning any stage:

* Review settings retain caller or execution-option origins;
* decision-time Search aggregates are `search_derived` and available at the
  current Decision;
* same-selection PIMC retains its compatible-world selection reference;
* Immediate retains its heuristic-analysis origin;
* the same-selected-World flag depends on the retained Review and PIMC selection;
* the actual Card is a retrospective attachment available after actual play;
* assessments, impact, prioritization, patterns, and Guidance derive from the
  retained evidence and observed Card; and
* Outcome Context is post-game-only and available at Game end.

The complete Historical Root Result ledger covers the optional
`historical_information_set_replay_coaching_summary`. Public provenance exposes
only the redacted complete Root Result mapping. Private Policies, Observations,
Worlds, Exact States, caches, branches, and child seeds remain engine-private,
with no orphan or overlapping public paths.

## Schema, example, and scenarios

Issue #192 adds exactly one strict authoritative Schema and byte-identical
packaged resource:

```text
schemas/historical_information_set_replay_coaching.schema.json
```

The existing bounded Replay Coaching and Historical Information-set Review
Schemas remain unchanged. The new Root example is:

```text
examples/historical_information_set_replay_coaching.json
```

Exactly two scenarios follow the existing 94 in unchanged order:

```text
historical_information_set_replay_coaching
historical_party_wide_claim_information_set_replay_coaching
```

At least one includes opt-in public Provenance. The resulting Issue #192
point-in-time totals are 70 authoritative Schemas, 70 packaged Schema Resources,
six Session examples, and 96 generated-output scenarios. Issue #194 later brings
the current working totals to 71/71 Schemas and 98 scenarios without changing
this Coaching family.

## Privacy and claims

The public report may expose safe aggregate Search Results, actual and
recommended Cards, Candidate ranks and objective gaps, diagnostic PIMC/Immediate
agreement, deterministic Coaching summaries, and final recorded Outcome Context.
It does not expose controlled Policies, actor Observations, selected Worlds,
exact opponent ownership, unauthorized Skat or Discards, Search caches or
branches, memoized bundles, Profile Statistics Records, Workspace Commentary, or
Response associations.

The report does not claim actual-Card correctness, Search accuracy, calibrated
probability, equilibrium, globally optimal or perfect play, complete Strategy-
Fusion correction, tactical intent, signaling success, causality, Player skill,
or statistical significance. Information-set Search enforces one common action
for equal controlled-Player Observations only over the selected bounded sequence;
fixed opponents remain model Policies.

Issue #193 separately benchmarks the unchanged executor on a synthetic local
corpus. Those measurements are not Coaching runtime gates, cross-machine
thresholds, or latency promises.

## Open work

The following remain open:

* tactical quality assessment and human Commentary interpretation;
* signaling or communication inference;
* cross-game Coaching and Player Ratings;
* Historical Strategy Teacher Report import or automatic Coaching Report
  transfer;
* automatic Coaching execution or Capture-to-Corpus transfer;
* Information-set-aware `auto` and dedicated Information-set budget profiles;
* product/runtime performance acceptance gates and cross-machine latency
  guarantees;
* complete Strategy-Fusion correction; and
* complete-contract or equilibrium solving.

See [Information-set Search contracts](information_set_search_contracts.md),
[Information-set Search workflows](information_set_search_workflows.md),
[Match analysis and exports](match_analysis_and_exports.md), and
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md).
See also [Information-set Search performance](information_set_search_performance.md).
