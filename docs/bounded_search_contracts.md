# Bounded search contracts

This document defines version 1 of the shared bounded-search contracts. The
contracts provide an information boundary, an internal exact complete-world
state and legal transition kernel, eligibility semantics, budgets, terminal
utility, aggregate results, deterministic serialization, and a strict standalone
schema. They also include one executable bounded perfect-information Minimax
solver for a caller-supplied exact world. No existing recommendation workflow
emits a bounded-search result.

## Current scope

The first supported search perspective is a current local decision at the fixed
three-player table. The implemented exact-world solver uses:

* `perfect_information_minimax_v1`

The following hidden-world method remains reserved:

* `compatible_world_minimax_v1`

The public result uses `analysis_method = bounded_search`, bounded-search schema
version `1`, and terminal-utility version `1`. These are internal contracts and
do not add a stable package-root API, CLI branch, production budget profile, or
latency promise.

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

No adapter from `SearchInformationView`, compatible hidden worlds, or analysis
and review workflows exists yet. The exact solver accepts an `ExactSearchState`
directly. Exact hands and out-of-play cards remain private and are never
serialized in a bounded-search result. The specialized five-trick
defender-open-play proof also reuses this legal transition kernel while retaining
its event-specific quantifiers, memoization, proof line, and privacy-safe output.

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
`compatible_world_limit_exceeded` and `incompatible_world_space` are reserved
result reasons for a future world-selection stage; this contract does not
inspect compatible worlds.

The exact solver additionally requires Suit or Grand, a non-terminal state, the
concrete `perspective_player` to equal the state's current `next_player`, known
matadors and bid value, at least one legal card, and no more remaining tricks
than the lower of the implementation limit of five and the requested limit.
Null returns `unavailable` with `unsupported_game_type`.

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

For `perfect_information_minimax_v1`, every uncached state, including the root
and terminal leaves, consumes one node. Timeout is checked before node
exhaustion; a non-terminal state then aborts when its current ply depth reaches
the requested depth limit. Cache hits consume no node, while still contributing
to the maximum reached depth. The timeout and elapsed milliseconds remain
machine-dependent diagnostics rather than a latency promise.

## Status and stopping

Status and stop reason are separate stable fields:

* `complete` uses `completed` and means every selected world has an exact
  terminal solution under the selected search contract;
* `partial` uses `node_budget_exhausted` or `depth_budget_exhausted`;
* `timeout` uses `wall_clock_timeout` and requires a requested wall-clock cutoff;
* `unavailable` uses one valid unsupported-domain reason and has no world
  coverage, solution claim, candidates, or search recommendation.

A partial or timed-out search recommendation is usable only when every
candidate has the same completed-world prefix and that prefix reaches
`minimum_comparable_worlds`. Otherwise no candidate is marked recommended.
The current exact solver is stricter: any node, depth, or timeout abort reports
zero completed worlds for every root candidate and returns no recommendation.

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

Exact Suit/Grand leaves reuse `get_exact_search_terminal_facts()` and the
existing game-result, game-value, overbid, and final-settlement builders before
building terminal utility. Final settlement is authoritative for winner
orientation: `settlement.is_loss = true` means a defender win, and `false`
means a declarer win. Utility is then oriented to the acting player's declarer
or defender side.

## Perfect-information Minimax version 1

`solve_perfect_information_minimax()` solves one fully specified
`ExactSearchState` for Suit or Grand with at most five remaining tricks. The
current concrete acting player supplies the perspective. Declarer actions
optimize the declarer side, both defenders optimize one cooperating-defenders
side, and the side containing the perspective maximizes its local terminal
utility while the other side minimizes it.

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

## Result privacy and schema

`build_serializable_bounded_search_result` emits only the version, methods,
game type, status, stop semantics, independent coverage and claim, budgets,
compatible-world count, candidate aggregates, recommendation, and fallback
markers. Serialization is deterministic and does not include the information
view.

The strict Draft 2020-12 schema is
[`schemas/bounded_search_result.schema.json`](../schemas/bounded_search_result.schema.json).
It recursively rejects unknown properties. The serializer and schema never
emit actual or sampled hidden hands, a hypothetical private Skat, compatible
world assignments, coherent roots, ownership-reconstructing fingerprints,
future historical data, or world-specific principal variations.

`fallback_used` and `fallback_method` are consistency-checked placeholders. No
fallback is executed or connected to an existing recommendation workflow in
version 1.

## Remaining work

The executable solver is limited to one caller-supplied exact Suit or Grand
world. It has no compatible-world counting, enumeration, sampling, or selection;
no `SearchInformationView` adapter; and no recommendation workflow, review,
CLI, default budget, production profile, or latency integration. Null, hidden-
information search, Expectimax, and broader search remain unsupported. The
stronger-search v1.0 completion gate therefore remains open because compatible-
world, hidden-information, and product-workflow integration are absent.
