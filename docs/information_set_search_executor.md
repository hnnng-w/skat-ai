# Information-set Search executor

## Purpose

Issue #188 adds the private version-1 bounded Information-set Policy Search
executor. It consumes one retained Issue-#187 Preparation and computes a best
response for controlled Player `me` over the selected Compatible-world sequence.
`left` and `right` remain separate deterministic fixed-policy actors.

The executor version and algorithm are:

```text
INFORMATION_SET_SEARCH_EXECUTOR_VERSION = 1
selected_world_information_set_best_response_v1
```

The implementation is private in
`src/skat_ai/information_set_search_executor.py`. It adds no existing Search
method, route, fallback, profile, Public API, CLI, Schema, example, generated
scenario, or Package-version change.

## Selected-world best response

The executor optimizes one complete contingent Policy for `me` against the
supplied fixed Policies. It does not solve a three-player equilibrium and does
not jointly optimize a Defender partner.

One recursive subproblem retains the selected World States as an ordered tuple.
Order is part of the subproblem identity. Repeated sampled draws remain repeated
tuple entries and therefore retain equal repeated aggregate weight.

For each subproblem:

1. advance every non-controlled actor through its own Observation and fixed
   Policy until the World is terminal or `me` must act;
2. select the first non-terminal `me` Observation in selected order;
3. group every World currently exposing an equal Observation;
4. evaluate every legal Card in canonical order;
5. apply one common Card to every World in the group;
6. solve the resulting complete ordered bundle recursively;
7. retain the first canonical Card with the best aggregate utility.

Worlds waiting at different controlled Information Sets remain unchanged until
their group is selected. Hidden World identity and sampled-draw index cannot
split an equal Observation. Different Observations may select different Cards.

## Fixed-player rollout

Fixed actors receive only values already exposed by
`build_information_set_search_observation_v1()`. Selection delegates to
`select_information_set_fixed_policy_card_v1()`, and each Card is applied through
`apply_information_set_search_card_v1()`.

No random generator, private partner hand, opponent hidden hand, or controlled-
Player logic enters fixed rollout. Fixed rollout continues until terminal play
or the next controlled Information Set.

## Objective and root Candidates

Every canonical root legal Card is evaluated over the complete selected World
sequence with an independently optimized controlled continuation. Completed
terminal utilities are aggregated lexicographically by:

1. total local Contract-success count;
2. total local-side Game score;
3. Suit/Grand total local-side card-point margin;
4. canonical Card order.

Null omits the card-point-margin objective. Every selected draw has unit weight,
so a duplicate IID draw contributes again to each total.

The executor builds existing `AggregateSearchCandidateResult` values and ranks
them through `rank_search_candidate_results()`. A complete rank-1 Candidate is
the recommendation. No alternate score, settlement calculation, or Candidate
contract is introduced. Every terminal World delegates to
`build_exact_terminal_utility()` with the root local side.

## Complete contingent Policy

A complete Result retains one controlled Decision for every evaluated
controlled Information Set across every root Candidate branch. This includes
off-path Information Sets reached while evaluating non-recommended root Cards.

The root Decision is first. Remaining Decisions use deterministic first-
evaluation order. Equal Information Sets occur once, conflicting actions are
invariant errors, and sampled duplicate draws contribute to
`reached_world_count`.

A complete Result requires:

```text
retained controlled Policy count
    = controlled Policy Decision count
    = evaluated Information-set count
```

The claim `exact_selected_world_policy` is exact only for the retained selected
World sequence and supplied fixed Policies. Sampled coverage is not an exact
claim over unselected Compatible Worlds.

## Memoization

Both caches are invocation-local and are discarded after execution.

The World State cache is keyed by `InformationSetSearchWorldStateV1`. Cache hits
do not consume another state node. A retained entry can include terminal
utility, actor Observation, fixed-policy Card, and fixed successor. Equal sampled
draws reuse this computation while remaining repeated aggregate entries.

The completed-subproblem memo is keyed by the exact ordered World State tuple.
Selected order and duplicate multiplicity are therefore significant. Entries
retain ordered terminal utilities and a fully resolved controlled Policy suffix.
Only completed subproblems are memoized; interrupted subproblems are not.

## Counters and budgets

Depth is the number of public Card plays after the prepared root. Root depth is
zero, and incomplete current-root-Trick Cards are not future depth.

For each new uncached World State, stop checks occur in this order:

1. wall-clock timeout;
2. state-node limit;
3. unique World State registration;
4. reached-depth update;
5. terminal evaluation;
6. depth limit before non-terminal expansion.

Before each previously unseen controlled Information Set, timeout is checked
before the Information-set limit and registration. Terminal states at the exact
depth limit remain valid.

Consumed budget retains exact unique state nodes, started Information Sets,
fully resolved controlled Decisions, fixed decisions, maximum depth, selected
and completed draws, sampled and unique sampled draws, and operational elapsed
milliseconds. Elapsed time is diagnostic, not a latency guarantee.

## Incomplete execution

A structural stop returns `partial` with the exact exhausted reason,
`common_policy_prefix`, and controlled consistency. It retains only fully
resolved Decisions completed before interruption. Started unresolved Information
Sets are counted but omitted. Version 1 conservatively returns no Candidates, no
recommendation, and zero completed Worlds.

A wall-clock stop returns `timeout`, `none`, and `not_assessed`. It retains no
Candidates, controlled Policy, or recommendation and reports zero completed
Worlds. Structural counters remain diagnostic.

An unavailable Preparation is strictly reconciled and passed through without
World evaluation, fixed-policy selection, transition, or terminal utility. It
preserves its canonical reason and available Compatible-world count where the
retained selection provides one, and returns zero consumed budget.

## Retained-Preparation validation

Execution validates the exact retained Request, eligibility, selection shape and
budgets, selected Exact State and World State order, sampled multiplicity, root
public and ownership facts, root Information Set and legal Cards, fixed-policy
roles, and three-Trick eligibility. Validation does not rebuild the Compatible-
world space, rerun selection, or reconstruct selected Exact or World States.

Malformed direct executor arguments are validation errors. Forged retained
builder-controlled values raise `SkatAIInvariantError`.

## Strategy-Fusion boundary

The executor prevents Strategy Fusion for controlled Player `me` over the
selected sequence: equal controlled Observations receive one common action. It
does not prove that the selected Worlds are calibrated probabilities, identify
the real deal, optimize either fixed Player, establish Nash behavior, solve a
joint Defender Policy, cover unselected Worlds, or provide globally optimal or
complete-contract Skat play.

Existing `compatible_world_minimax_v1` remains unchanged and retains its broader
per-World Strategy-Fusion limitation. Issue #188 does not compare or route the
new private Result against PIMC or Immediate.

## Open integration work

PIMC and Immediate comparison, recommendation routing, `auto`, Multi-Step,
Policy Comparison, Historical Review, Dataset evaluation, Replay Coaching,
performance baselines, Provenance, Public API, CLI, Schemas, examples, and
generated scenarios remain separate future work.
