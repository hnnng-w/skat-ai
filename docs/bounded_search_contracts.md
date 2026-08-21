# Bounded search contracts

This document defines version 1 of the shared bounded-search contracts. The
contracts provide an information boundary, a private compatible-world selection
layer, an internal exact complete-world state and legal transition kernel,
eligibility semantics, budgets, terminal utility, aggregate results,
deterministic serialization, and a strict standalone schema. They also include
one executable bounded perfect-information Minimax solver for a caller-supplied
exact world and one executable compatible-world Minimax method over a frozen
selected-world sequence. Explicit flat live and post-game position analysis,
opt-in Multi-Step and Policy Comparison, Historical Search Review, and bounded-
Search dataset evaluation consume the same aggregate result contract.

## Current scope

The first supported search perspective is a current local decision at the fixed
three-player table. The implemented methods are:

* `perfect_information_minimax_v1`
* `compatible_world_minimax_v1`

The public result uses `analysis_method = bounded_search`, bounded-search schema
version `1`, and terminal-utility version `1`. These are internal contracts and
do not add a stable package-root API or a calibrated latency promise. Dedicated
Historical Search Review and dataset-evaluation CLI options select immutable,
versioned internal budget profiles; flat recommendation settings remain explicit
JSON and have no CLI method or budget override.

Issues #107 through #115 complete this functional scope for the `v0.10.0`
package baseline. That milestone does not close the broader v1.0 stronger-solver
gate described under remaining work.

The exact solver supports Suit, Grand, and normal non-overbid Null, including
Null, Null Hand, Null Ouvert, and Null Hand Ouvert. Null fixed values remain
owned by the existing game-value helpers.

Compatible Search-world selection version `1` remains a private layer between
`SearchInformationView` and `ExactSearchState`. The compatible-world solver
consumes that frozen selection directly. It is integrated into explicit ongoing
live-position recommendation, flat post-game Search review, opt-in local Multi-
Step and Policy Comparison decisions, Historical Search Review, and bounded-
Search dataset evaluation.

Issue #168 also allows the private local Match Capture browser to run strict
`bounded_search` or Search-first `auto` for one selected prepared Decision. The
adapter supplies the same information-safe flat nonterminal post-game Position
view and attaches the observed Card only for retrospective comparison. It accepts
`interactive_v1` or `historical_review_v1`, requires an explicit Search seed,
and makes exactly one existing Position Application invocation. Partial Match
evidence is sufficient only when the acting own hand and required public hand are
exactly preparable.

## Search information

`SearchInformationView` is frozen and uses canonical immutable tuples. Its
shared builder copies mutable source values and normalizes cards, declaration,
turn phase, public completed tricks, points, trick counts, hand sizes, public
hands, and confirmed hidden-card constraints.

The two sources are:

* `live_local_view`, built after enforcing local Skat visibility;
* `historical_decision_snapshot`, built only from an already reconstructed
  `HistoricalSnapshotPosition`.

Both use the explicit `current_decision` information cutoff. A complete
historical game is not an accepted historical adapter input.

Allowed information is limited to:

* the decision-relative perspective and concrete declarer when known;
* the local side, normalized declaration, and game type;
* the local remaining hand;
* the normalized current partial trick and completed public trick prefix;
* the next player;
* current declarer and defender card points and completed-trick totals;
* all three public remaining hand sizes;
* Skat cards legitimately visible to the local player;
* rule-authorized exact public hands;
* confirmed structural constraints derived from the decision-time public view.

The builder never accepts a private hidden world or caller-supplied exact hidden
constraints. It does not preserve actual unknown opponent hands, an unknown or
hypothetical Skat, sampled assignments, coherent execution roots, future plays,
future exposure or concession data, final historical outcomes, or settlement
labels. Invalid or contradictory public facts are validation errors rather than
`unavailable` search results.

The complete information view is internal and is never serialized in the public
bounded-search result.

## Exact complete-world state

`ExactSearchState` is the private, perspective-neutral representation of one
fully specified three-player world. It is not a local recommendation view and
does not contain utility orientation, rankings, random state, budgets, timing,
or result diagnostics. It stores the normalized declaration, concrete
declarer, all three exact remaining hands in fixed concrete-player order, an
ordered attributed partial trick, the concrete next player, completed-trick
points and trick counts for both sides, and the exact two final out-of-play Skat
or discard cards.

The strict builder defensively copies input, canonicalizes each hand and the two
out-of-play cards in full-deck order, preserves current-trick play order, and
validates the normal 32-card structure. Cards outside the remaining hands,
partial trick, and out-of-play pair are the completed-play cards. Their count
must equal three times the supplied completed-trick count, and their points must
equal the supplied declarer and defender awarded trick points. Partial-trick
points and out-of-play points have not yet been awarded to those fields.

The state supports zero through ten remaining tricks. `remaining_plies` counts
only cards still held, while `remaining_tricks` also includes cards already in
the partial trick. Late-game limits remain a search-budget concern rather than a
state restriction. A normal terminal state has empty hands, an empty current
trick, and ten completed tricks.

Legal-card generation calls the canonical `get_legal_cards()` rules and returns
an immutable canonical tuple. A pure single-card transition removes one owned
legal card, advances the fixed seat order, or resolves the third card with the
canonical trick-winner and trick-point rules. Completed resolution records the
ordered attributed plays, concrete winner, declarer or defender side, and trick
points; only that side's awarded points and trick count advance, and the winner
leads next. Parent states remain unchanged, and equal state-plus-move inputs
produce equal transitions.

Normal terminal facts remain neutral. They add the two out-of-play card points
to the declarer's awarded trick points, leave defender points unchanged, and
require 120 final card points and ten completed tricks. The facts themselves do
not determine contract success, Schneider, Schwarz, overbid, game value,
settlement, `TerminalUtility`, or card ranking; the exact terminal-utility
adapter composes those existing facilities separately.

The private compatible-world layer materializes strictly validated exact states
from `SearchInformationView`. Flat live and post-game position analysis use the
existing local-view adapter. Historical Search Review and dataset evaluation
adapt each already reconstructed decision-time snapshot independently.
The direct solver accepts an `ExactSearchState`, while compatible-world Minimax
passes each selected state to the same internal exact-world evaluator. Exact
hands and out-of-play cards remain private and are never serialized in a bounded-
search result. The specialized five-trick defender-open-play proof also reuses
this legal transition kernel while retaining its event-specific quantifiers,
memoization, proof line, and privacy-safe output.

## Compatible Search worlds

`CompatibleSearchWorldSpace` is frozen, internal, and builder-only. Its input is
one `SearchInformationView`; it does not accept actual opponent hands, an actual
unknown skat, a coherent execution root, future historical play, a complete
deal, final settlement, caller-supplied ownership, or profile weights. Non-empty
exact opponent ownership must be backed by an authorized exact public hand.

Assignment cards follow canonical full-deck order and exclude the local hand,
completed public cards, the current partial trick, and legitimately known
out-of-play cards. Exact public opponent cards remain assignment cards fixed to
their owner. Slot counts are the public left and right remaining-hand sizes plus
`2 - known out-of-play card count` for the skat, and must reconcile exactly.
Existing Suit, Grand, and Null effective-category helpers apply confirmed voids
only to opponents; the skat remains allowed. With no confirmed void, every
structurally valid labeled assignment remains compatible even though the
optional public `HiddenCardInferenceModel` remains absent.

The existing dynamic-programming counter returns the exact deterministic world
count, including zero. A reusable bounded enumerator first counts the space,
rejects a limit smaller than that count without truncation, and traverses cards
and owners canonically while pruning zero-completion branches. A reusable batch
sampler uses one caller-owned `random.Random`, one completion-count structure,
and IID uniform draws with replacement. It preserves order and duplicates and
does not alter the existing single-world sampler sequence.

Selection requires an explicit non-boolean integer base seed. Sampled selection
derives one process-stable SHA-256 child stream named
`bounded_search_compatible_world_selection_v1` and uses one RNG for the complete
sequence; exact enumeration consumes no random draws. A zero count reports
`incompatible_world_space`. A count no greater than `max_selected_worlds`
enumerates every world with `all_compatible_worlds`, including a one-world
space. A larger count draws exactly `max_sampled_worlds` with
`sampled_compatible_worlds`. `minimum_comparable_worlds`, node, depth, and
wall-clock budgets do not participate in selection, and
`compatible_world_limit_exceeded` remains reserved for a future exact-only
request.

Every selected assignment is validated for exact slots, complete one-owner card
coverage, allowed ownership, and canonical immutable card collections before
strict exact-state construction. The local hand, public completed-card prefix,
current trick, declaration, declarer, next player, awarded points, completed
trick counts, and exact public hands stay fixed. Only hidden opponent and
out-of-play ownership may vary, and the final out-of-play pair always has two
cards. All selected states must expose the same deterministic legal root-card
tuple. The frozen selected-state tuple, including retained sampled duplicates,
is the compatible-world evaluation order and is never reselected, reordered,
sorted, or deduplicated.

Compatible Search worlds are alternatives derived from the player's information
view. They are not and are never compared with the one private coherent
execution world used by Multi-Step simulation. Exact states, ownership,
hypothetical skat cards, hashes, fingerprints, DP tables, paths, and child seeds
remain private and are not added to results, schemas, CLI output, generated
outputs, or inference summaries.

## Eligibility

Eligibility is assessed without counting, enumerating, or sampling compatible
worlds. It reports eligibility, one stable unavailable reason, unresolved
plies, unresolved tricks, and the configured remaining-trick limit. Unresolved
card counting includes cards already in a current partial trick, so lead,
second-seat, and third-seat representations describe the same remaining trick
count.

The first supported domain requires:

* perspective `me`;
* a concrete declarer and known local side;
* an unfinished game;
* a normalized supported phase with the local player required to act;
* at least one legal local card;
* declaration inputs sufficient to resolve existing terminal settlement
  semantics at a leaf;
* no more than the configured number of remaining tricks.

Current assessment can return `unsupported_perspective`,
`missing_concrete_declarer`, `game_already_complete`,
`unsupported_turn_phase`, `local_player_not_to_act`, `no_legal_cards`,
`missing_terminal_utility_inputs`, or `remaining_trick_limit_exceeded`.
`incompatible_world_space` is now used by the private selection stage after
eligibility. `compatible_world_limit_exceeded` remains reserved for a future
explicit exact-only request; eligibility itself still does not inspect worlds.

Both Minimax methods require Suit, Grand, or normal non-overbid Null,
a non-terminal state, the concrete `perspective_player` to equal the state's
current `next_player`, at least one legal card, and no more remaining tricks than
the lower of the implementation limit of five and the requested limit. Suit and
Grand require known matadors and bid value. Null requires a bid value at or
below its fixed variant value; a missing bid or a bid above that value returns
`missing_terminal_utility_inputs` before search. The boundary uses the existing
game-value and overbid helpers and does not select or construct the Suit or Grand
replacement required by impossible-Null settlement. `unsupported_game_type`
remains a stable contract reason.

## Requested and consumed budgets

`RequestedSearchBudget` contains `max_remaining_tricks`, `max_depth_plies`,
`max_nodes`, `max_selected_worlds`, `max_sampled_worlds`,
`minimum_comparable_worlds`, and nullable `wall_clock_timeout_ms`. All configured
values are positive. Sampled worlds and minimum comparable worlds cannot exceed
selected worlds.

Remaining tricks, depth, nodes, selected worlds, sampled worlds, and the common
prefix minimum are deterministic structural limits. The optional wall-clock
timeout is a non-deterministic operational safety cutoff. It may vary across
machines and must not be described as a deterministic latency guarantee.

`ConsumedSearchBudget` records `depth_reached`, `nodes_expanded`, selected and
completed world counts, sampled and unique sampled world counts, and elapsed
wall-clock milliseconds. Counts are non-negative and reconcile with each other
and the requested structural limits. Elapsed wall-clock time is diagnostic and
is outside strict cross-machine determinism.

World selection consumes only `max_selected_worlds` and `max_sampled_worlds`.
It does not consume nodes or depth, apply `minimum_comparable_worlds`, or inspect
the wall-clock cutoff. Sampled counts include duplicate draws, while the unique
sampled count reports distinct exact states without deduplication or reordering.

For `perfect_information_minimax_v1`, every uncached state, including the root
and terminal leaves, consumes one node. Timeout is checked before node
exhaustion; a non-terminal state then aborts when its current ply depth reaches
the requested depth limit. Cache hits consume no node, while still contributing
to the maximum reached depth. The timeout and elapsed milliseconds remain
machine-dependent diagnostics rather than a latency promise.

For `compatible_world_minimax_v1`, `max_nodes` is global across the complete
selected sequence. Each attempted world root consumes one node when capacity is
available, every new uncached exact-state evaluation consumes one node, cache
hits consume none, and work from an aborted world remains consumed. Depth starts
at zero for each world, uses the same `max_depth_plies`, and reports the maximum
reached across attempted worlds. One monotonic execution window begins only
after successful selection and spans all exact-world evaluations; construction
and selection are outside it. Timeout is checked before each uncached evaluation.
If the final selected world completes, a later diagnostic elapsed-time reading
does not convert the complete result to timeout.

Each selected draw gets a fresh transposition table, shared only across that
world's root candidates. Exact cache entries are never reused across worlds.
Sampled duplicates are separate draws and are evaluated separately.

## Status and stopping

Status and stop reason are separate stable fields:

* `complete` uses `completed` and means every selected world has an exact
  terminal solution under the selected search contract;
* `partial` uses `node_budget_exhausted` or `depth_budget_exhausted`;
* `timeout` uses `wall_clock_timeout` and requires a requested wall-clock cutoff;
* `unavailable` uses one valid unsupported-domain reason and has no world
  coverage, solution claim, candidates, or search recommendation.

A partial or timed-out compatible-world recommendation is usable only when every
candidate has the same completed-world prefix and that prefix reaches
`minimum_comparable_worlds`. Otherwise no candidate is marked recommended.
The current exact solver is stricter: any node, depth, or timeout abort reports
zero completed worlds for every root candidate and returns no recommendation.
Compatible-world execution stops at the first incomplete world, discards all
values from that world, retains only earlier complete worlds, and never visits a
later world. Timeout uses `solution_claim = none`; this means there is no
reproducible complete selected-world solution claim, not that retained completed-
prefix values are inexact.

## Coverage and solution claims

World coverage describes which hidden worlds were selected:

* `none`;
* `single_exact_world`;
* `all_compatible_worlds`;
* `sampled_compatible_worlds`.

Solution claim describes work completed within selected worlds:

* `none`;
* `exact_per_selected_world`;
* `depth_limited_per_selected_world`;
* `node_limited_partial`.

These dimensions are orthogonal. In particular,
`sampled_compatible_worlds + exact_per_selected_world` means exact terminal
solutions for the selected sample only. It is not exact over all compatible
worlds, does not identify the real deal, and must not be shortened to an
"exact search" claim. Only `all_compatible_worlds` together with
`exact_per_selected_world` supports exact-all-compatible-world terminology.
That combination is an exact aggregate across all structurally compatible
worlds. A sampled completion is exact only within each selected sample. A
partial result is exact only over its completed prefix. Selected coverage is
therefore distinct from completed coverage.

Compatible-world Minimax is determinization-based. Independent exact play in
each world can choose world-specific continuation strategies, so the aggregate
is subject to strategy fusion. Even exhaustive compatible-world enumeration is
not proof of an optimal imperfect-information policy.

## Terminal utility version 1

Terminal values reuse existing result and settlement semantics and orient every
component toward the local side. Missing matadors for Suit or Grand, a missing
bid value, or another required leaf input makes search unavailable with
`missing_terminal_utility_inputs`; the search contract does not invent a score.

Suit and Grand compare lexicographically by:

1. local-side contract success;
2. local-side game or settlement score;
3. local-side card-point margin.

Null compares by:

1. local-side contract success;
2. local-side game or settlement score.

Null has no invented card-point secondary objective. Canonical root-card order
is the final aggregate candidate tie-break and is not terminal game utility.

Exact Suit, Grand, and Null leaves reuse `get_exact_search_terminal_facts()` and
the existing game-result, game-value, overbid, and final-settlement builders
before building terminal utility. Null first constructs ten role-only trick
owners from exact terminal trick counts and applies the completed Null result:
zero declarer tricks is a declarer win, while one or more is a defender win.
Card points remain factual settlement input but never determine Null success or
provide a Null secondary objective. The four fixed Null values therefore settle
through existing helpers as `+23/-46`, `+35/-70`, `+46/-92`, and `+59/-118`.
Final settlement is authoritative for winner orientation:
`settlement.is_loss = true` means a defender win, and `false` means a declarer
win. Utility is then oriented to the acting player's declarer or defender side.

## Perfect-information Minimax version 1

`solve_perfect_information_minimax()` solves one fully specified
`ExactSearchState` for Suit, Grand, or supported Null with at most five remaining
tricks. The current concrete acting player supplies the perspective. Declarer
actions optimize the declarer side, both defenders optimize one cooperating-
defenders side, and the side containing the perspective maximizes its local
terminal utility while the other side minimizes it. Null play continues to
normal card exhaustion even after the declarer has taken a contract-losing
trick.

Root legal cards use canonical order and are each searched with a fresh full
Alpha-Beta window, so every completed root candidate has a canonical exact
terminal value. Below each root card, deterministic Alpha-Beta follows canonical
legal-card order. One invocation-local transposition table is shared across root
candidates and reuses only exact values: terminal values and non-terminal values
that were not merely Alpha-Beta bounds. Nothing is persisted across calls.

A completed call reports one selected and completed exact world,
`single_exact_world`, `exact_per_selected_world`, exact aggregates for every
legal root card, and one deterministic recommendation. If any search branch
hits the node, depth, or timeout budget, the whole call is incomplete: it
reports one selected world but zero completed worlds, placeholder candidates
with absent rates and means, no recommendation, and no fallback. It does not
publish a partial root value, principal variation, or heuristic substitute.
Node exhaustion returns `partial + node_limited_partial`, depth exhaustion
returns `partial + depth_limited_per_selected_world`, and timeout returns
`timeout + none`.

The public direct solver and compatible-world method use the same internal
exact-world evaluator. It consumes one world-root node, evaluates every root
card with a fresh full Alpha-Beta window, keeps canonical below-root Alpha-Beta
and exact-only transposition semantics, and returns only exact root-card terminal
utilities to its caller. It returns no public result, private state, principal
variation, or searched branch information.

## Compatible-world Minimax version 1

`solve_compatible_world_minimax()` accepts one information-safe
`SearchInformationView`, one validated requested budget, and an explicit non-
boolean integer seed. Preflight applies the existing eligibility order with the
lower of the implementation five-trick limit and the requested limit. The shared
terminal-input check requires bid and matadors for Suit/Grand, requires a bid no
greater than the fixed Null value, and rejects overbid Null before world
construction.

After successful selection, worlds execute in frozen order. Every common legal
root card must receive an exact terminal utility before that world's values are
added to totals and its completed count advances. Node, depth, or timeout abort
discards the current world's values, stops immediately, and retains aggregate
totals only from the common completed prefix. Selection count, coverage, sampled
count, unique sampled count, exact-state order, and duplicate draws remain
unchanged.

For each card, each completed draw contributes equal weight to local contract
success count, local-side settlement score, and Suit/Grand local card-point
margin. Division by the shared completed count produces success rate and means;
Null always has a null margin. Duplicate draws contribute repeatedly. There is
no deduplication, marginal weighting, profile weighting, worst-case ranking, or
adaptive ordering. The existing aggregate rank order selects deterministic rank
1 when all worlds complete, or on a partial/timeout prefix only when the minimum
comparable-world threshold is reached. No fallback runs.

The solver itself never runs fallback. The caller-owned `auto` workflow may run
Immediate only after the solver has successfully returned a validated result
with no recommendation.

## Candidate aggregates

Candidate results contain only card-level aggregates over the common completed
world prefix: rank, recommendation marker, completed worlds, local contract
success count and rate, mean local-side game score, and the mean local-side
card-point margin for Suit and Grand. Null always omits the margin.

Aggregate ranking is deterministic and descending by success rate, mean local
game score, and, for Suit and Grand, mean local card-point margin. Canonical
deck order is the final tie-break. Rates and means are absent when no world is
complete. No candidate contains a world-specific ownership assignment or
principal variation.

## Flat recommendation workflow

`recommendation_method` is optional. Omission executes the exact preexisting
Immediate expected-value path and emits no method-specific fields. Explicit
values are `immediate_expected_value`, `bounded_search`, and `auto`.

Both Search methods require `bounded_search_settings` with one explicit non-
boolean integer `random_seed` plus every `RequestedSearchBudget` field. Unknown
or missing keys are rejected, nullable timeout remains supported, and no default
or named profile applies to flat JSON recommendation. Explicit Immediate and
omitted methods reject Search settings.

The Search workflow is restricted to `not_ended` flat positions. It accepts
`live_decision` without `actual_card_played`, or `post_game_review` with a legal
`actual_card_played`. It rejects terminal shortening, impossible Null, post-game
Skat, list and non-position workflows, legacy non-empty `played_cards`, and
unattributed completed history. Existing
declared-Ouvert and supported continuation public hands are allowed only after
their current information-policy resolution.

Strict `bounded_search` uses every solver result containing a recommendation,
including qualified partial or timeout common-prefix results. It never runs
Immediate and returns effective method `none` when Search has no recommendation.
`auto` behaves identically when Search recommends. Otherwise it attempts the
existing Immediate path. Fallback is marked only when Immediate returns a card;
if it does not, effective method remains `none` and the Search result is not
marked. Arbitrary exceptions, view contradictions, compatible-world failures,
invariant failures, invalid results, and serialization defects propagate rather
than causing fallback.

The immutable fallback helper requires a Search result with no recommendation
and no prior fallback. It changes only `fallback_used` to true and
`fallback_method` to `immediate_expected_value`; the Search recommendation stays
null, while every status, count, budget, aggregate, coverage, and claim remains
unchanged. The top-level recommendation carries the Immediate card.

`analysis_report` remains an Immediate one-trick report. Effective Search and
strict no-recommendation Search emit an empty report with method `none`. Explicit
Immediate and auto fallback retain the existing report with method
`immediate_expected_value`; Search aggregates remain only in
`candidate_results`.

The top-level `random_seed` controls Immediate and auto fallback. The separate
Search settings seed controls compatible-world selection. Exact enumeration
consumes no random draws, changing only the Immediate seed cannot change a
successful Search, and no derived child seed is serialized.

Issue #175's private Strategy Teacher Evidence preserves these exact existing
strict Search and Auto relationships from executed Decision Analysis Reports. It
copies aggregate status, stop reason, coverage, claim, requested/consumed budget,
compatible-world count, Candidate results, recommendation, fallback, actual-Card
comparison, and Search-versus-Immediate comparison without reconstructing Worlds
or rerunning Search. Operational `wall_clock_elapsed_ms` remains in exact source
identity but is excluded from semantic Teacher identity. See
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md).

## Multi-Step and Policy Comparison

The four legacy local policies remain `first_legal`, `lowest_point`,
`highest_point`, and `highest_expected_value`; only those policies execute
through `choose_card_by_policy()`. Multi-Step additionally accepts
`bounded_search` and `auto`, both routed through the existing recommendation
workflow. The omitted Multi-Step default remains `first_legal`, and Policy
Comparison remains the four legacy policies unless one Search method is
explicitly configured. In that case exactly the configured method is appended
last.

At each local decision, opponent preparation first executes in the private
coherent world. Those actions are then represented in the prepared public state,
public exact-hand constraints and failure-to-follow evidence are updated, and
Search runs only from that public boundary. It receives integer remaining hand
sizes derived from initial public counts and attributed public path actions. The
coherent root, private hands, hypothetical Skat, ownership map, root identity,
and future path are never Search inputs. Search independently reconstructs its
compatible worlds. The chosen legal local card is then executed in the coherent
world, preserving exact owner removal and fixed-Skat continuity.

Every decision reruns Search. Compatible selections, exact states, caches,
principal lines, and candidate values are not shared between decisions. The
same immutable requested budget applies freshly to each call, so total path cost
scales with the number of attempted local decisions multiplied by the configured
per-decision budget. There is no path-global budget.

Each decision derives a child Search seed from the explicit Search base seed
through `multi_step_bounded_search_decision_v1`. The decision index is the child
index. The stream excludes the coherent root, opponent RNG, Immediate seed,
policy name, policy result, and private ownership. Child seeds are not emitted.
Existing root, opponent-action, expected-value, and Search-internal streams are
unchanged.

Strict `bounded_search` executes complete and qualified partial or timeout
recommendations without Immediate fallback. A valid Search result without a
recommendation stops before local execution with
`local_policy_no_recommendation`; already prepared opponent actions remain in the
final state and coherent transition counts. `auto` uses Search whenever it
recommends, otherwise calls the existing Immediate fallback. If neither returns
a card, fallback remains unmarked and the path stops for the same reason.
Unexpected Search, information-view, result, or serialization errors propagate.

Executed Search-aware steps expose one aggregate-only
`recommendation_decision`; a pre-execution stop exposes
`stopped_recommendation_decision`. Search-aware summaries reconcile attempts,
executions, Search recommendations, Immediate fallbacks, and no-recommendation
stops. Search-inclusive comparison rows add recommendation eligibility and
compact ordered decision diagnostics. An ineligible Search row remains visible,
sorts after eligible rows, and cannot become `recommended_policy`.

Issue #190 extends this Search-aware boundary with strict
`information_set_search`. Each local decision receives a child world-selection
seed in domain `multi_step_information_set_search_decision_v1`, executes fresh
Search from the public state, and shares no Search World, controlled Policy, or
cache with another decision. The coherent execution World remains private and
independent. A no-recommendation Result stops before local execution with no
fallback. Policy Comparison appends the configured Information-set method exactly
once and last to the four defaults, keeps a stopped row visible but ineligible,
and emits a safe nested Decision Result plus exactly 16 compact diagnostics.
Existing ranking and `auto` behavior are unchanged; no `information_set_auto`
exists.

## Retrospective comparisons

Flat post-game Search runs the requested Search method first and then runs an
independent `immediate_expected_value` baseline with the ordinary top-level
Immediate sample count, seed, policies, and public information. The existing
`post_game_review_summary` is intentionally built from that Immediate report;
the configured Search or auto workflow keeps ownership of the top-level
recommendation and adds
`bounded_search_post_game_review_summary` with
`analysis_method = bounded_search_with_immediate_baseline`.

`search_actual_card_comparison` ranks the observed card in Search's candidate
aggregate and reports recommendation-minus-actual gaps in contract success rate,
mean local-side game score, and the Suit/Grand mean card-point margin. Its basis
is `all_compatible_worlds`, `sampled_compatible_worlds`, or
`completed_common_prefix`. `search_vs_immediate_comparison` aligns both cards in
the same Search aggregate while also reporting each card's rank under the other
method. Its aggregate relation is `search_better`, `aggregate_equivalent`, or
`not_available`; canonical card-order tie-breaking does not turn equal aggregate
metrics into a strict improvement. Null comparisons keep margin values null.

These are retrospective aggregate comparisons, not proof that Search selected
an optimal imperfect-information policy. Zero completed worlds or a missing
aligned candidate produces an explicit unavailable reason rather than invented
metrics.

Match-bound Profiles may affect the independent existing Immediate behavior when
eligible, actionable, and enabled, but they are not compatible-world weights and
do not alter Search candidate aggregates, coverage, or solution claims. The
actual observed Match Card remains behavior evidence, not an optimal label.

## Named budget profiles

The dedicated historical and evaluation workflows accept exactly these
immutable versioned profiles:

| Profile | Remaining tricks | Depth plies | Nodes | Selected worlds | Sampled worlds | Comparable worlds | Timeout ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `interactive_v1` | 3 | 9 | 500,000 | 64 | 32 | 8 | 1,000 |
| `historical_review_v1` | 4 | 12 | 2,000,000 | 128 | 64 | 16 | 5,000 |
| `evaluation_v1` | 5 | 15 | 10,000,000 | 512 | 256 | 32 | null |

The profile mapping and each `RequestedSearchBudget` are immutable. Profiles do
not contain seeds and do not change the explicit budget required by flat JSON
recommendation input. Historical Search Review defaults to
`historical_review_v1`; dataset evaluation defaults to `evaluation_v1`.

## Historical Search Review

`--historical-search-review --search-seed INTEGER` evaluates every actual card
decision in a validated historical record with Search and an independently run
Immediate baseline. `--search-budget-profile` selects one named profile.
`--samples` and `--seed` control the Immediate baseline; their defaults remain
100 samples and no explicit Immediate seed. The output uses schema version `1`,
`analysis_method = bounded_search_with_immediate_baseline`, and
`information_policy = decision_time`.

Each row contains stable decision identity, game type, local side, root seat,
remaining tricks, actual card, the Immediate baseline, bounded Search result,
and both retrospective comparisons. Search receives only the reconstructed
decision-time view. Both analyses finish before the observed card is introduced
for comparison, and future private cards, final outcomes, and settlement do not
enter either analysis.

The caller-supplied base Search seed is domain-separated with
`historical_bounded_search_decision_v1`, stable game ID, and one-based decision
index through SHA-256. The resulting 64-bit decision seed is stable across
processes and dataset record reordering. Derived Search seeds are private and
are never serialized.

Aggregate output reconciles attempted, available, unavailable, recommendation,
and no-recommendation decision counts; all Search statuses; exact, sampled, and
no-coverage counts; Search/Immediate agreement; actual-card top-1/top-3 rates;
aggregate quality; and performance totals, mean, nearest-rank p50/p95, maximum,
and fallback count. The same metrics are broken down by game type, local side,
root seat, remaining tricks, Search status, and coverage. Zero-decision records
produce empty rows, null rates/percentiles, zero totals, and a vacuously passing
quality gate.

## Dataset evaluation

`--evaluate-bounded-search --search-seed INTEGER` runs the same information-safe
decision comparison over `training_dataset_input`. Repeatable
`--search-evaluation-partition` accepts only `train`, `validation`, and `test`;
the default is canonical `validation`, then `test`. Evaluation uses
`evaluation_v1` unless `--search-budget-profile` selects another named profile.
Its independent Immediate baseline is fixed at 100 samples with base seed `0`.

`--search-evaluation-max-decisions` is an optional positive global cap over the
stable selected-record and decision order, not a per-record cap. All selected
records remain in output, including zero-decision records and records reached
after capacity is exhausted. Source and evaluated counts, cap status, and empty
decision arrays remain explicit.

The quality gate considers only available Search-versus-Immediate comparisons:
`search_not_worse_count = search_strictly_better_count +
search_equivalent_count`, and `quality_violation_count =
comparable_decision_count - search_not_worse_count`. It passes exactly when the
violation count is zero, including the zero-comparison case. This arithmetic
measures the two cards on Search's own aggregate; it is not independent policy
proof or calibrated sampled-world quality.

Independent exhaustive reference tests show one strict Search improvement over
Immediate in each of Suit, Grand, and Null. Separate 560-world fixtures exercise
IID sampled convergence at 32, 64, and 128 draws across five seeds per game type:
rank-1 agreement is at least 90% where the exhaustive success-rate gap is at
least 0.10, and the 128-draw mean absolute success-rate error is at most 0.05.
This is bounded regression evidence, not a statistical calibration guarantee.

The deterministic Suit/Grand/Null benchmark corpus, reproduction command, and
local measurements are documented in [Bounded Search performance](bounded_search_performance.md).
Named profiles are work budgets, and elapsed measurements are diagnostics. There
is no calibrated latency guarantee, service-level objective, or cross-machine
performance threshold.

## Result privacy and schema

`build_serializable_bounded_search_result` emits only the version, methods,
game type, status, stop semantics, independent coverage and claim, budgets,
compatible-world count, candidate aggregates, recommendation, and fallback
markers. Serialization is deterministic and does not include the information
view.

The strict Draft 2020-12 schema is
[`schemas/bounded_search_result.schema.json`](../schemas/bounded_search_result.schema.json).
Flat comparison, Historical Search Review, and dataset evaluation additionally
use [`schemas/bounded_search_post_game_review.schema.json`](../schemas/bounded_search_post_game_review.schema.json),
[`schemas/historical_search_review.schema.json`](../schemas/historical_search_review.schema.json),
and [`schemas/bounded_search_evaluation.schema.json`](../schemas/bounded_search_evaluation.schema.json).
These focused schemas recursively reject unknown properties. The serializers and schemas never
emit actual or sampled hidden hands, a hypothetical private Skat, compatible
world assignments, coherent roots, ownership-reconstructing fingerprints,
future historical data, derived Search seeds, or world-specific principal
variations.

Issue #189 adds separate strict Information-set Search Result, comparison,
Historical Review, and Training Dataset evaluation schemas. Their public
serializers likewise omit selected Worlds, exact states and hands, actor
Observations, the private controlled Policy table, caches, memoization, and
derived seeds. See
[Information-set Search workflows](information_set_search_workflows.md).

`fallback_used` and `fallback_method` are consistency checked. They remain false
for solver-only calls and strict Search; only the caller-owned auto workflow may
mark `immediate_expected_value` fallback on an otherwise unchanged no-
recommendation result. Live orchestration also rejects a solver result for a
different Search method, game type, or requested budget before strict or auto
routing can consume it.

## Remaining work

Existing bounded Search methods remain limited to late Suit, Grand, and supported
normal Null play. Overbid Null remains unavailable because Search does not select
an impossible-Null replacement. Compatible-world Minimax remains a
determinization aggregate, not an optimal imperfect-information Policy proof.
Issues #187 and #188 separately define and execute the private three-Trick
Information-set Policy Search. Issue #189 exposes it through strict flat routing,
same-selection retrospective comparison, separate Historical Review and Training
Dataset evaluation, safe public output, Provenance, CLI, Schemas, an example, and
generated scenarios. Issue #190 adds strict Multi-Step and Policy Comparison
integration with fresh per-decision Search and no fallback. Existing `auto`
remains PIMC first with Immediate fallback.

The integration does not add calibrated sampled quality, a latency guarantee,
adaptive sampling, Expectimax, complete Strategy-Fusion correction,
complete-contract solving, or a stable package-root Domain API. Multi-Step and
Policy Comparison are now integrated only for the bounded strict behavior above.
Match Capture, Match Analysis Reports, Strategy Teacher Evidence, Replay Coaching
classification, performance integration, cross-decision global Policy,
equilibrium, global optimality, and calibrated probabilities remain absent. The
stronger-search v1.0 completion gate therefore remains open.

See [Information-set Search contracts](information_set_search_contracts.md) and
the [Information-set Search executor](information_set_search_executor.md) for
the private controlled-Player policy-consistency claim, and
[Information-set Search workflows](information_set_search_workflows.md) for the
integrated public boundaries, and
[Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md)
for Issue #190.
