# Bounded Search performance

`benchmarks/bounded_search_late_game_v1.json` is the deterministic schema-version
`1` late-game compatible-world Search corpus named
`bounded_search_late_game_v1`. It covers one Suit, one Grand, and one Null local-
declarer position with two remaining tricks. Together the cases exercise
exhaustive `all_compatible_worlds` and deterministic
`sampled_compatible_worlds` selection. Each case uses one immutable named budget
from `src/skat_ai/search_budget_profiles.py`.

## Reproduce

Measured command from the repository root:

```powershell
py -3.13 scripts/benchmark_bounded_search.py --warmup-runs 1 --runs 5
```

The command emits machine-readable JSON to standard output. It records platform and Python
metadata, corpus and profile names, run counts, every measured run, per-case summaries, and
aggregate elapsed-time and node metrics. Every warm-up and measured run also asserts the
corpus's frozen recommendation, status, coverage, and structural work result.

Use `--corpus PATH` to select another compatible schema-version `1` corpus,
`--warmup-runs` to change warm-up count, and `--runs` to change measured count.
At least two measured runs are required. The command does not write a file;
redirect standard output when a retained JSON artifact is needed.

## Named profile values

| Profile | Remaining tricks | Depth plies | Nodes | Selected worlds | Sampled worlds | Comparable worlds | Timeout ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `interactive_v1` | 3 | 9 | 500,000 | 64 | 32 | 8 | 1,000 |
| `historical_review_v1` | 4 | 12 | 2,000,000 | 128 | 64 | 16 | 5,000 |
| `evaluation_v1` | 5 | 15 | 10,000,000 | 512 | 256 | 32 | none |

These are immutable structural work profiles, not latency targets. The optional
timeouts are operational cutoffs. Their activation is wall-clock and therefore
machine-dependent; a profile does not guarantee completion or response time.

## Local measurement

Measured on 2026-08-03 with one warm-up and five measured runs per case:

| Environment field | Value |
| --- | --- |
| Platform | Windows 11 (`Windows-11-10.0.26200-SP0`, AMD64) |
| Processor | Intel64 Family 6 Model 189 Stepping 1, GenuineIntel |
| Python | CPython 3.13.7 |
| Python executable | `C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe` |

| Case | Profile | Coverage | Recommendation | Depth | Nodes | Selected/completed/sampled | Min ms | Median ms | Mean ms | Max ms |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Clubs | `interactive_v1` | sampled (32 of 90) | `D8` | 6 | 841 | 32/32/32 | 10.996 | 11.646 | 11.514 | 11.843 |
| Grand | `historical_review_v1` | all 90 | `H10` | 6 | 1,846 | 90/90/0 | 23.462 | 24.394 | 26.307 | 32.796 |
| Null | `evaluation_v1` | all 12 | `CK` | 4 | 99 | 12/12/0 | 1.458 | 1.643 | 1.711 | 2.172 |

Across 15 measured executions, elapsed time totaled 197.658 ms, with an 11.646 ms
median, 13.177 ms mean, 1.458 ms minimum, and 32.796 ms maximum. The runs expanded
13,930 nodes in total. Each case produced identical recommendations, statuses, coverage,
and node counts in all five measured repetitions; all statuses were `complete`.

## Reference objectives

The corpus has two bounded objectives:

* detect changes to each frozen recommendation, status, stop reason, coverage,
  compatible-world count, depth, node count, and selected/completed/sampled world
  counts; and
* preserve one reproducible local timing reference for the exact tracked corpus
  and environment without creating an elapsed-time test assertion.

The runner reports minimum, median, mean, and maximum elapsed time. It does not
define or report a P95 objective, service-level objective, or production latency
threshold. The three cases are a deterministic reference corpus, not broad
coverage of every player perspective, seat, remaining-trick depth, or compatible-
world size.

## Interpretation

Node counts and functional results are deterministic for a fixed corpus,
implementation, profile, and random seed. Elapsed times are observations from one
local machine and will vary with hardware, operating-system scheduling, power
state, Python build, and concurrent load. They are reference measurements, not
cross-machine guarantees, a service-level objective, or a regression threshold.

The exhaustive Grand and Null cases are exact aggregates across all structurally
compatible worlds. The sampled Clubs case is exact only for its 32 selected IID
draws; sampling is with replacement and duplicate draws retain repeated weight.
A partial or timeout result would be exact only over its common completed-world
prefix. Exact compatible-world counts do not identify the real deal, and sampled
ownership quality is not calibrated probability.

Compatible-world Minimax remains bounded late-game determinization subject to
Strategy Fusion. Even exhaustive enumeration is not an optimal imperfect-
information policy, and the benchmark is not complete-contract Search evidence.
The normal Search implementation maximum remains five unresolved tricks.
Issue #187's separate private information-set Search contracts and three-Trick
Preparation execute no Policy Search and add no timing, quality, or latency
evidence; this corpus continues to measure only the existing executable methods.
Overbid Null remains outside normal Search because Search does not select its
external Suit or Grand replacement.
No benchmark result changes the project's lack of a machine-learning model,
four-player support, complete official rule coverage, or latency guarantees.
