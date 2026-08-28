# Information-set Search Multi-Step and Policy Comparison

## Scope

Issue #190 completes version-1 integration of strict `information_set_search`
into Multi-Step and Policy Comparison. It does not add another Search method,
Root workflow, CLI flag, Public API version, or Schema.

The integration versions are:

```text
INFORMATION_SET_SEARCH_MULTI_STEP_INTEGRATION_VERSION = 1
INFORMATION_SET_SEARCH_MULTI_STEP_DECISION_VERSION = 1
INFORMATION_SET_SEARCH_POLICY_COMPARISON_INTEGRATION_VERSION = 1
```

The current Package version is `0.17.0`; Public API contract version `1`, the seven Root
workflows, and the one `skat-ai = skat_ai.cli:main` Console Script are unchanged.

## Multi-Step decision boundary

`information_set_search` is a strict Search-aware Multi-Step policy. At every
local decision, the simulation:

1. completes any existing canonical Trick and advances opponent preparation in
   the coherent execution World;
2. represents those actions in the current public state, hand sizes, public-hand
   constraints, and failure-to-follow evidence;
3. derives one decision-local Search configuration;
4. executes a fresh strict Information-set Search from that public boundary;
5. validates a recommended legal local Card; and
6. executes that Card in the separate coherent World.

Opponent preparation, completion, and Search fixed-Player rollout reuse the
same already resolved `EffectiveOpponentPolicySettings`; the simulation does not
repeat Profile or precedence resolution.

Issue #203 applies this boundary to all nine concrete canonical phases. In the
three former gaps, only the missing old-Trick opponent Cards execute before the
winner and continuation are derived. That prelude consumes no local Decision
index or Search child seed. Search starts only if continuation reaches the first
new public local Decision. See
[Canonical Multi-Step phase coverage](canonical_multi_step_phase_coverage.md).

The coherent execution World remains private. Its exact hands, hypothetical
Skat, ownership map, root identity, and future path are not Search inputs. Search
constructs its own Compatible-world selection from current public information,
so the Search Worlds remain independent of the one hypothetical World used to
execute the simulated path.

Each local decision starts a new Search. Selected Worlds, World States,
Observations, controlled Policy, caches, memoized bundles, candidate work, and
consumed budget are not reused across decisions. There is no path-global Search
budget or cross-decision controlled Policy.

## Decision seed

Each local decision derives its world-selection seed from the explicit
`information_set_search_settings.random_seed` with domain:

```text
multi_step_information_set_search_decision_v1
```

The zero-based Multi-Step decision index is the child index. Derivation changes
only the child Search `random_seed`; all other eight strict Information-set Search
settings remain equal. The child seed is separate from coherent-root sampling,
opponent actions, Immediate samples, and Search-internal work, and is never
serialized.

## Strict stop behavior

Every decision runs strict `information_set_search`. It never invokes Immediate,
PIMC, `bounded_search`, or another fallback. Complete Results may recommend a
Card. Partial, timeout, and unavailable Results without a recommendation stop the
path before local play with:

```text
local_policy_no_recommendation
```

Opponent preparation already made public at that decision remains represented in
the final state and coherent transition counts. The stopped Decision remains
visible under `stopped_recommendation_decision`; `fallback_used` is false and
`fallback_method` is null.

Existing `auto` remains compatible-world PIMC followed by its existing Immediate
fallback. There is no `information_set_auto`, and Issue #190 does not change flat,
Historical Review, or Training Dataset evaluation routing.

## Safe Decision output

Each executed step retains one version-1 `recommendation_decision`. A stopped
attempt retains the same shape under `stopped_recommendation_decision`. The safe
Decision has exactly these fields:

```text
schema_version
step_index
requested_method
effective_method
search_attempted
recommendation_card
recommendation_reason
fallback_used
fallback_method
information_set_search_result
```

The nested `information_set_search_result` is the existing safe aggregate public
Result. It contains no selected World, exact hand, Observation, controlled Policy
table, ownership assignment, child seed, cache, memoized bundle, or branch. An
executed Decision's `recommendation_card` equals the step's `candidate_card`.

Multi-Step summary counts retain the existing Search-aware fields:
`requested_method`, `decisions_attempted`, `decisions_executed`,
`search_recommendations_used`, `immediate_fallbacks_used`, and
`no_recommendation_count`. For `information_set_search`, Immediate fallback count
is always zero.

## Policy Comparison

Policy Comparison retains the default four policies in their existing order:

```text
first_legal
lowest_point
highest_point
highest_expected_value
```

When the Position configures `information_set_search`, that method is appended
exactly once and last. No other Information-set method or implicit auto row is
added.

All five paths receive independent copies of one shared coherent root World.
Each path evolves its own copy. The Information-set Search row still performs a
fresh public-state Search at every local decision and never receives or reuses
the shared root, another path's Search Worlds, or a prior controlled Policy.
The same effective opponent Policies drive any canonical completion prelude for
every path, so no compared local Policy can affect play before its first local
Decision.

A Search path stopped without a recommendation remains visible with
`eligible_for_recommendation = false` and
`ineligible_reason = local_policy_no_recommendation`. It sorts after eligible
rows and cannot become `recommended_policy`. Eligible rows retain the existing
Policy Comparison ranking, including the existing Null objective and existing
tie-breakers; Issue #190 adds no ranking objective. If canonical completion ends
the local hand before any local Decision, every zero-step row remains visible and
`recommended_policy` is null.

## Compact diagnostics

The Information-set Search comparison row exposes one compact diagnostic per
attempted local decision. Each diagnostic has exactly 16 fields:

| Field | Meaning |
| --- | --- |
| `step_index` | Zero-based local decision index. |
| `requested_method` | Always `information_set_search`. |
| `effective_method` | Effective Search method, or `none` without a recommendation. |
| `search_method` | Executor method identifier exposed by the safe Result. |
| `search_status` | Complete, partial, timeout, or unavailable status. |
| `search_stop_reason` | Exact safe stop reason. |
| `world_coverage` | Existing safe coverage classification. |
| `policy_claim` | Existing bounded Policy claim. |
| `policy_consistency` | Existing controlled consistency classification. |
| `selected_world_count` | Selected draw count consumed by this decision. |
| `completed_world_count` | Completed draw count consumed by this decision. |
| `information_sets_evaluated` | Started controlled Information-set count. |
| `controlled_policy_decision_count` | Safe count only, not the private Policy table. |
| `fixed_policy_decision_count` | Fixed-player decision count. |
| `recommendation_card` | Recommended Card or null. |
| `fallback_used` | Always false for this strict method. |

The diagnostics do not expose private World or Policy identity.

## Provenance

Live Position provenance captures the current public decision boundary before
each local Search. It then maps the retained safe Decision and its private
Information-set Search Result when present into complete provenance for the
nested public Result, including a stopped Decision when present. Policy
Comparison additionally maps every compact diagnostic from the retained per-
decision values.

Provenance construction does not rerun Search, select Worlds, rebuild a coherent
root, or reconstruct the controlled Policy. The complete `position_result`
ledger covers the serialized Multi-Step and Policy Comparison branches. Public
opt-in provenance remains the existing redacted Root Result mapping and does not
expose intermediate attachments or private retained values.

Canonical completion before a local boundary creates no synthetic Search
Decision. Its completed Trick, public-state transition, constraints, void
evidence, and final serialization remain retained by the same version-1 internal
Provenance lifecycle.

## CLI, example, and validation

The existing CLI fields and flags are sufficient:

```powershell
skatmind --input position.json --multi-step 1
skatmind --input position.json --multi-step 1 --compare-policies
```

The input selects `recommendation_method: "information_set_search"` and provides
the existing exact nine `information_set_search_settings` fields. Existing
`--card-policy` matching rules, `--comparison-only`, `--quiet`, and
`--include-provenance` behavior are unchanged. Issue #190 adds no CLI flag.

`examples/information_set_search_multi_step.json` is the focused one-decision
input. Two append-only generated-output scenarios cover strict Multi-Step with
opt-in Provenance and the five-row Policy Comparison. The Issue #190 point-in-time
totals are 69 authoritative and packaged Schemas, six Session examples, and 94
generated-output scenarios. Published `v0.16.0` facts remain 63 Schemas, six
Session examples, and 85 scenarios.

## Limitations

Issue #190 does not integrate Information-set Search into Match Capture, Match
Analysis Reports, Strategy Teacher Evidence, Replay Coaching classification, or
performance measurement. Issue #191 subsequently adds only the bounded private
one-Decision Match/Report/Teacher/Dataset/Corpus path; this Multi-Step integration
is unchanged. Issue #192 subsequently adds separate Information-set Replay
Coaching and Match Historical integration, and Issue #193 adds separate bounded
repository-local performance evidence. Production latency guarantees remain
outside the v0.17.0 contract.

The integration does not create a cross-decision global Policy, a joint
Defender-team Policy, an equilibrium, Nash behavior, global optimization, or
global optimality. It does not identify the real deal, turn selected Worlds into
calibrated probabilities, cover unselected Worlds, solve a complete contract, or
provide a latency guarantee. Existing flat, Post-game, Historical Review, and
Training Dataset evaluation behavior remains unchanged.

Issue #203 subsequently completes only the canonical phase boundary. It changes
no Information-set Search contract, budget, fixed-Player Policy, safe aggregate
Result, Schema, CLI flag, example, or generated-scenario count.

See [Information-set Search contracts](information_set_search_contracts.md), the
[Information-set Search executor](information_set_search_executor.md), and
[Information-set Search workflows](information_set_search_workflows.md). See
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md)
for the later Issue #191 boundary, [Information-set Replay Coaching and Match
Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md)
for Issue #192, and [Information-set Search performance](information_set_search_performance.md)
for Issue #193.
