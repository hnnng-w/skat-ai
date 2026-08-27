# Canonical Multi-Step phase coverage

## Scope

Issue #203 adds internal Canonical Multi-Step Phase Coverage version `1`. It
closes the three valid fixed-table phase gaps without adding a solver, Search
method, opponent Policy, public field, Schema, example, or generated scenario.

The exact internal action vocabulary is:

```text
local_action
prepare_to_local_action
complete_current_trick_then_continue
```

The retained contract policy identifiers are:

| Policy | Exact value |
| --- | --- |
| Source | `normalized_concrete_turn_phase_only` |
| Classification | `exact_leader_length_and_next_player_table` |
| Completion | `complete_existing_trick_without_replaying_local_card` |
| Continuation | `continue_from_completed_winner_to_next_local_decision` |
| Step count | `count_new_local_decisions_only` |
| World | `one_coherent_world_without_resampling_or_search_disclosure` |
| Randomness | `chronological_existing_opponent_action_stream` |
| Search | `search_only_at_new_local_decision_boundaries` |
| Termination | `existing_non_error_stop_without_synthetic_local_action` |
| Compatibility | `preserve_supported_phase_outputs_and_public_shape` |
| Provenance | `retained_transition_evidence_without_workflow_rerun` |

Classification uses only the normalized concrete `TurnPhase` and the exact
leader, current-Trick length, and next-Player table. Contradictory concrete
values remain validation errors. An unresolved empty `unknown/unknown` phase
remains outside canonical coverage and may still stop as
`unsupported_turn_phase`.

## Canonical table

| Trick leader | Current-Trick length | Next Player | Action |
| --- | ---: | --- | --- |
| `me` | 0 | `me` | `local_action` |
| `me` | 1 | `left` | `complete_current_trick_then_continue` |
| `me` | 2 | `right` | `complete_current_trick_then_continue` |
| `left` | 0 | `left` | `prepare_to_local_action` |
| `left` | 1 | `right` | `prepare_to_local_action` |
| `left` | 2 | `me` | `local_action` |
| `right` | 0 | `right` | `prepare_to_local_action` |
| `right` | 1 | `me` | `local_action` |
| `right` | 2 | `left` | `complete_current_trick_then_continue` |

The six previously supported rows retain their existing behavior. The former
gaps complete these exact initial sequences:

```text
(me, 1, left):
    left second, right third

(me, 2, right):
    right third

(right, 2, left):
    left third; the local Card is already second
```

## Existing-Trick completion

The local Card in each completion row is already in `current_trick` and already
outside the local remaining hand. Completion therefore never selects, removes,
replays, seeds, recommends, or creates a step for that Card. Only the missing
opponent Cards are selected through their existing effective per-Player response
Policies and legal-card rules.

Existing rule helpers derive the completed-Trick winner, concrete winner Player,
winner side, and Card points. One completed Trick is appended, the existing Card
prefix is preserved, `current_trick` is cleared, and the winner becomes the next
Trick leader. Prior completed Tricks and explicit point fields remain unchanged;
score summaries continue to derive completed-Trick points exactly once.

If `me` wins, the next local Decision is immediately on lead. If `left` wins,
the existing left-lead and right-response preparation is reused. If `right`
wins, the existing right-lead preparation is reused. The prelude is bounded to
at most two missing old-Trick plays plus two next-Trick preparation plays and
must stop at the first new local Decision.

## Steps and termination

`requested_step_count` remains the maximum number of newly selected local Cards.
Initial completion and opponent preparation consume no local step and no Search
child index. The first new local Decision remains `step_index = 0`; public
`steps` entries remain local-action-only.

When completion leaves the local remaining hand empty, the engine retains the
completed Trick, executes no local Policy or Recommendation workflow, returns
zero simulated steps, and uses the existing non-error reason
`Player has no cards left.`. Metadata that already marks the Game complete still
stops as `Game is already complete.` before any additional play.

## Coherent World and public evidence

One immutable coherent root is constructed or accepted once per path. Old-Trick
completion and any following preparation create chronological immutable owner-
Card transitions against that same root; no Card is removed twice, ownership is
not resampled, and the hypothetical Skat remains fixed.

Each opponent play decrements the matching public hand size once and removes the
Card from any exact public-hand constraint. The updated public state reconstructs
confirmed failure-to-follow evidence in chronological order. Terminal completion
also rebuilds and validates that evidence even though no local Decision follows.
The private coherent ownership is never serialized or supplied to Search.

All missing opponent actions consume the existing chronological
`opponent_actions` stream. The six existing rows consume the same draws as
before. Local Immediate, bounded-Search, and Information-set Search seeds remain
indexed only by newly attempted local Decisions.

## Search and Policy Comparison

The four legacy local Policies, `bounded_search`, existing `auto`, and strict
`information_set_search` use their unchanged local-selection paths after a new
public Decision boundary is reached. Search receives updated public history,
hand sizes, exact public constraints, and confirmed void evidence, but never the
coherent execution World. Strict no-recommendation behavior still has no
fallback.

Policy Comparison constructs one shared root and gives every Policy one equal
independent immutable copy. Effective opponent Policies are common across every
path, so the completion prelude is Policy-neutral until local selection. Normal
ranking remains unchanged when at least one local Decision occurs. If completion
leaves every path with zero local Decisions, every row remains visible and
`recommended_policy` is null.

## Provenance and compatibility

The Issue #202 internal provenance lifecycle remains version `1`. Phase handling
uses the retained validated input; the resulting completed Trick, simulated-
opponent transitions, updated public Decision cutoff, and final serialization
are retained by normal execution. Decision provenance is captured only after the
prelude reaches a new local boundary. Terminal completion creates no synthetic
Decision attachment, and provenance construction reruns no workflow stage.

Public Multi-Step and Policy Comparison fields, public redaction, Schemas,
Package `0.17.0`, Public API contract `1`, seven Root workflows, one Console
Script, Settlement Matrix version `3` with 61 cases, 71 authoritative and
packaged Schemas, six Session examples, 98 generated scenarios, and ten private
Corpus downloads remain unchanged. One existing generated scenario keeps its
name and registry position but now exercises executable canonical completion
instead of the former `unsupported_turn_phase` result.

Issue #203 makes P-19 `satisfied` and closes B-03. The four remaining v1 blockers
are B-04 through B-07. The exact next action is Issue #204, **Decide and apply the
v1 Package license boundary**. `v1.0.0` is not ready.
