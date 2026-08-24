# Information-set Search performance

Issue #193 adds reproducible repository-local performance evidence for the
unchanged bounded Information-set Search executor. The evidence consists of a
strict synthetic corpus, a standalone runner, frozen functional and structural
signatures, focused regression tests, and one documented local wall-clock
measurement.

It does not add a production route, a runtime performance gate, a service-level
objective, or a latency guarantee.

## Corpus

`benchmarks/information_set_search_late_game_v1.json` is corpus
`information_set_search_late_game_v1`, schema version `1`. Its eight complete
synthetic deals and legal replay prefixes reconstruct safe live Information
Views before invoking the existing Preparation, executor, exact-world solver,
same-selection PIMC, and independent Immediate implementations.

| Case | Contract | Actor | Turn | Unresolved Tricks | Profile | Selection |
| --- | --- | --- | --- | ---: | --- | --- |
| `clubs_declarer_lead_sampled_three_tricks` | Suit | declarer | lead | 3 | `historical_review_v1` | sampled |
| `grand_defender_second_seat_exhaustive_two_tricks` | Grand | defender | second seat | 2 | `historical_review_v1` | all compatible Worlds |
| `null_defender_third_seat_exhaustive_one_trick` | Null | defender | third seat | 1 | `interactive_v1` | all compatible Worlds |
| `null_hand_declarer_lead_exhaustive_two_tricks` | Null Hand | declarer | lead | 2 | `evaluation_v1` | all compatible Worlds |
| `null_ouvert_defender_second_seat_sampled_two_tricks` | Null Ouvert | defender | second seat | 2 | `interactive_v1` | all compatible Worlds |
| `null_hand_ouvert_declarer_third_seat_exhaustive_one_trick` | Null Hand Ouvert | declarer | third seat | 1 | `interactive_v1` | all compatible Worlds |
| `clubs_strategy_fusion_sampled_two_tricks` | Suit | declarer | lead | 2 | `interactive_v1` | sampled |
| `grand_sampled_duplicate_weight_two_tricks` | Grand | defender | lead | 2 | `interactive_v1` | sampled |

The stable fifth case name contains `sampled`, but its exact position has only
three compatible Worlds. The existing `interactive_v1` budget therefore selects
all three, and the frozen truthful coverage is `all_compatible_worlds` with zero
sampled Worlds.

Together the matrix covers Suit, Grand, Null, Null Hand, Null Ouvert, and Null
Hand Ouvert; declarer and defender decisions; lead, second-seat, and third-seat
turns; one through three unresolved Tricks; all three existing work profiles;
and exhaustive and sampled Compatible-world selection.

The strict loader rejects a UTF-8 byte-order mark, malformed JSON, duplicate
object keys, non-finite numbers, missing fields, unknown fields, invalid enum
values, changed case order, declaration/complete-deal matador conflicts, and
incompatible or cross-contradictory expected signatures.

## Reproduce

Run from the repository root with Python 3.13:

```powershell
py -3.13 scripts/benchmark_information_set_search.py --warmup-runs 1 --runs 5
```

The command emits finite JSON followed by one newline to standard output and
writes no repository artifact. At least two measured runs are required.

Available options are:

* `--corpus PATH` selects another strict schema-version `1` corpus;
* `--case NAME` restricts execution to one canonical case;
* `--warmup-runs N` controls untimed warm-up repetitions; and
* `--runs N` controls measured repetitions.

Each warm-up and measured execution validates the frozen functional result. A
measured case is also rejected if its structural counters differ across runs.
The runner retains each exact mapped Profile Budget but freezes the executors'
operational timeout clocks during benchmark work. External stage timing remains
real. Machine speed therefore cannot turn a frozen complete signature into a
timeout, while existing production timeout semantics remain unchanged and are
covered by their focused deterministic-clock tests.

## Frozen evidence

Each case freezes:

* Information-set status, stop reason, coverage, policy claims, recommendation,
  Candidate order and aggregate values, depth, selected/completed/sample counts,
  and structural work counters;
* PIMC status, coverage, recommendation, Candidate values, depth, exact-solver
  node count, and the exact same selected-world sequence;
* independently seeded Immediate recommendation and canonical legal Candidate
  order, not an Immediate-value ranking; and
* descriptive recommendation agreement and cross-method Candidate ranks.

The Strategy-Fusion diagnostic separately freezes one equal controlled root
Observation across 32 selected draws. Exact per-World preferences choose `DA`
30 times and `DQ` twice, while Information-set Search retains one common `DA`
root action for all 32 draws. This demonstrates the bounded controlled-Player
policy-consistency behavior; it is not complete Strategy-Fusion correction.

The duplicate-weight diagnostic freezes 32 sampled draws, 28 unique exact
Worlds, four duplicate draws, maximum multiplicity two, and Candidate/root
denominators of 32. Repeated draws therefore retain repeated aggregate weight.

The fixtures are synthetic and contain no public or user game data. The runner
does not serialize the synthetic initial hands, Skat, exact Worlds, opponent
ownership, actor Observations, controlled Policy table, branches, or caches.

## Measured stages

The runner records minimum, median, mean, and maximum milliseconds for:

* Compatible-world Preparation;
* Information-set executor execution;
* combined Preparation plus Information-set execution;
* same-selection PIMC; and
* independently seeded Immediate.

It also reports descriptive median ratios for Information-set execution versus
same-selection PIMC and combined Information-set time versus Immediate. These
baselines intentionally measure different algorithms and claims. Their ratios
are observations, not quality, accuracy, or acceptance comparisons.

## Local measurement

Measured on 2026-08-24 with one warm-up and five measured runs per case:

| Environment field | Value |
| --- | --- |
| Platform | Windows 11 (`Windows-11-10.0.26200-SP0`, AMD64) |
| Processor | Intel64 Family 6 Model 189 Stepping 1, GenuineIntel |
| Python | CPython 3.13.7 |

Median timings in milliseconds:

| Case | Recommendation | Preparation | Information-set execution | Information-set total | Same-selection PIMC | Immediate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `clubs_declarer_lead_sampled_three_tricks` | `D7` | 14.215 | 3485.334 | 3499.987 | 235.106 | 13.376 |
| `grand_defender_second_seat_exhaustive_two_tricks` | `D9` | 2.436 | 14.314 | 16.708 | 1.868 | 8.019 |
| `null_defender_third_seat_exhaustive_one_trick` | `D7` | 0.456 | 0.485 | 1.264 | 0.115 | 3.492 |
| `null_hand_declarer_lead_exhaustive_two_tricks` | `DK` | 4.318 | 33.169 | 37.488 | 7.381 | 9.406 |
| `null_ouvert_defender_second_seat_sampled_two_tricks` | `D9` | 0.850 | 3.221 | 4.045 | 0.834 | 7.582 |
| `null_hand_ouvert_declarer_third_seat_exhaustive_one_trick` | `D7` | 0.389 | 0.503 | 1.222 | 0.122 | 4.714 |
| `clubs_strategy_fusion_sampled_two_tricks` | `DA` | 6.665 | 77.704 | 84.827 | 10.965 | 12.919 |
| `grand_sampled_duplicate_weight_two_tricks` | `DK` | 8.818 | 67.769 | 76.587 | 15.209 | 11.683 |

Frozen structural work per measured execution:

| Case | Selected/completed Worlds | State nodes | Information Sets | Controlled decisions | Fixed decisions |
| --- | ---: | ---: | ---: | ---: | ---: |
| `clubs_declarer_lead_sampled_three_tricks` | 64/64 | 1948 | 262 | 262 | 1256 |
| `grand_defender_second_seat_exhaustive_two_tricks` | 9/9 | 99 | 15 | 15 | 54 |
| `null_defender_third_seat_exhaustive_one_trick` | 1/1 | 2 | 1 | 1 | 0 |
| `null_hand_declarer_lead_exhaustive_two_tricks` | 18/18 | 234 | 18 | 18 | 144 |
| `null_ouvert_defender_second_seat_sampled_two_tricks` | 3/3 | 33 | 5 | 5 | 18 |
| `null_hand_ouvert_declarer_third_seat_exhaustive_one_trick` | 1/1 | 2 | 1 | 1 | 0 |
| `clubs_strategy_fusion_sampled_two_tricks` | 32/32 | 390 | 32 | 32 | 240 |
| `grand_sampled_duplicate_weight_two_tricks` | 32/32 | 364 | 30 | 30 | 224 |

All 40 measured executions reproduced their frozen functional and structural
results. Across those executions, the aggregate median combined Information-set
time was 26.189 ms, the aggregate median executor time was 22.792 ms, and the
aggregate median Preparation time was 3.543 ms. Aggregate median same-selection
PIMC and Immediate times were 4.176 ms and 9.169 ms. The corresponding
descriptive aggregate ratios were 5.458 and 2.856.

## Interpretation

Functional results and structural counters are deterministic for the frozen
corpus, implementation, profiles, and seeds. Wall-clock values vary with
hardware, Python build, power state, operating-system scheduling, and concurrent
load.

The benchmark defines no P95 or P99 objective, elapsed-time assertion,
cross-machine threshold, service-level objective, calibrated quality measure,
accuracy claim, statistical-significance claim, production acceptance gate, or
latency guarantee. Timeout activation remains machine-dependent. The tests
freeze functional and structural work and the timing-output shape, not measured
milliseconds.

Exact exhaustive coverage remains exact only across the Compatible Worlds for
that bounded position. Sampled coverage is exact only over the selected IID
draws. Compatible-world counts do not identify the real deal, sampled ownership
is not calibrated probability, fixed opponents remain model Policies, and the
three-Trick executor is not a global Policy, equilibrium, globally optimal
imperfect-information solver, complete Strategy-Fusion correction, or complete-
contract solver.

## Compatibility

Issue #193 changes no production code, Search algorithm, route, work profile,
Public API, Package version, Schema, example, generated-output scenario, Session
example, Root workflow, Console Script, or Settlement Matrix case. The current
Issue #193 point-in-time counts remain 70 authoritative and packaged Schemas,
six Session examples, and 96 generated-output scenarios. Issue #194 subsequently
adds one unrelated Tactical Motif Review Schema and two scenarios, so the current
working totals are 71 Schemas and 98 scenarios without changing this benchmark.

The existing `benchmarks/bounded_search_late_game_v1.json` corpus and
`scripts/benchmark_bounded_search.py` runner remain byte-identical and continue
to measure `compatible_world_minimax_v1` separately.

See [Information-set Search contracts](information_set_search_contracts.md),
[Information-set Search executor](information_set_search_executor.md),
[Information-set Search workflows](information_set_search_workflows.md),
[Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md),
and [Bounded Search performance](bounded_search_performance.md).
