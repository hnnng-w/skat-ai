# Bounded Search performance

`benchmarks/bounded_search_late_game_v1.json` is the deterministic late-game
compatible-world Search corpus. It covers Suit, Grand, and Null with both exhaustive
`all_compatible_worlds` and deterministic `sampled_compatible_worlds` selection. Each case
uses one immutable named budget from `src/skat_ai/search_budget_profiles.py`.

## Reproduce

Measured command from the repository root:

```powershell
py -3.13 scripts/benchmark_bounded_search.py --warmup-runs 1 --runs 5
```

The command emits machine-readable JSON to standard output. It records platform and Python
metadata, corpus and profile names, run counts, every measured run, per-case summaries, and
aggregate elapsed-time and node metrics. Every warm-up and measured run also asserts the
corpus's frozen recommendation, status, coverage, and structural work result.

## Local measurement

Measured on 2026-08-03 with one warm-up and five measured runs per case:

| Environment field | Value |
| --- | --- |
| Platform | Windows 11 (`Windows-11-10.0.26200-SP0`, AMD64) |
| Processor | Intel64 Family 6 Model 189 Stepping 1, GenuineIntel |
| Python | CPython 3.13.7 |
| Python executable | `C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe` |

| Case | Profile | Coverage | Recommendation | Nodes | Min ms | Median ms | Mean ms | Max ms |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Clubs | `interactive_v1` | sampled (32 of 90) | `D8` | 841 | 10.996 | 11.646 | 11.514 | 11.843 |
| Grand | `historical_review_v1` | all 90 | `H10` | 1,846 | 23.462 | 24.394 | 26.307 | 32.796 |
| Null | `evaluation_v1` | all 12 | `CK` | 99 | 1.458 | 1.643 | 1.711 | 2.172 |

Across 15 measured executions, elapsed time totaled 197.658 ms, with an 11.646 ms
median, 13.177 ms mean, 1.458 ms minimum, and 32.796 ms maximum. The runs expanded
13,930 nodes in total. Each case produced identical recommendations, statuses, coverage,
and node counts in all five measured repetitions; all statuses were `complete`.

## Interpretation

Node counts and functional results are deterministic for a fixed corpus, implementation,
profile, and random seed. Elapsed times are observations from one local machine and will vary
with hardware, operating-system scheduling, power state, Python build, and concurrent load.
They are not a service-level objective or regression threshold. The named profiles are
versioned work budgets, and these local measurements should not be generalized to another
environment or to production and interactive latency.
