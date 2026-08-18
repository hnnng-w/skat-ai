# Learning Corpus Strategy Teacher Evidence

Issue #175 adds private internal method-bound Strategy Teacher Evidence for the
active `v0.16.0 - Learning-ready behavior and communication data` milestone. It
imports no report into Corpus persistence and creates no training label. It
derives one minimized immutable evidence value from each explicitly supplied
exact executed Decision Analysis Report.

## Source boundary

Version `1` accepts only an exact `MatchAnalysisReportV1` with:

* report kind `decision_analysis`;
* one exact `MatchDecisionAnalysisResultV1`;
* execution status `executed`;
* one Position `RequestDocumentV1`;
* one Position `ResultDocumentV1`.

Materialization Reports, Historical Analysis Reports, unavailable Decision
Reports, raw Position Results, and analysis mappings are not accepted. Historical
Immediate Review, Historical Search Review, and Replay Coaching evidence remain
separate future boundaries.

The caller binds every Report to one explicit Learning Corpus Match Snapshot ID.
The collection builder strictly resolves the Catalog's Current Match Snapshots
and requires the supplied ID to be the Current Snapshot for the Report Match.
Retained non-current revisions, same-revision non-current content, and orphan
objects cannot contribute.

For each accepted source, the builder reconciles:

* Match ID and Workspace revision;
* observed Match position and Game ID;
* one Snapshot-scoped Game Reference;
* one Snapshot-scoped Decision Reference;
* Decision index and acting stable Player ID;
* the observed source Play and actual Card.

No cross-revision Decision lineage is inferred.

## Request and Result reconciliation

The builder calls `build_match_decision_position_request_v1()` exactly once for
each source. It uses the Current Snapshot Workspace, source Match position,
source Decision index, and exact retained `MatchDecisionAnalysisOptionsV1`.
The rebuilt Request and relative Profile binding must equal the Report values.
The deterministic input reference and bounded Search settings must also equal
the Result values.

The existing output validation boundary validates each retained Position Result.
The builder then reconciles the input reference, requested method, Immediate
sample count and seed, Profile-Preset setting, Profile application summary, and
every applicable actual-Card copy. Rebuilding performs no Application execution,
Search, Profile derivation/application, Replay Coaching, Dataset generation, file
I/O, network request, or Workspace mutation.

## Exact and semantic identities

Source version, Evidence version, Collection version, and Export version are
independent strict integer version `1` contracts.

The implementation reuses the finite Learning Corpus canonical JSON contract:

```text
UTF-8
ensure_ascii = true
allow_nan = false
sort_keys = true
separators = (",", ":")
```

Domain-separated SHA-256 identities cover:

* the complete exact Match Analysis Report;
* the complete exact Position Request wrapper;
* the complete exact Position Result wrapper, including warnings;
* the caller's Snapshot-to-Report source binding;
* normalized semantic Teacher evidence;
* Snapshot-scoped Strategy Teacher Evidence;
* the complete collection except its own fingerprint;
* the complete export identity.

The exact source Report and Result fingerprints retain operational
`wall_clock_elapsed_ms`. The semantic Teacher fingerprint excludes only source
Report/Request/Result and source-binding identities, its own derived identities,
and every retained `wall_clock_elapsed_ms` value. It retains Search status, stop
reason, completed-world prefix, budgets, Candidate metrics, recommendation,
fallback, Profile context, and comparisons. Distinct Reports that differ only by
elapsed time therefore remain distinct source observations while sharing one
semantic Teacher fingerprint.

## Method-bound evidence

A recommendation is evidence from the exact retained method and settings. It is
not perfect-play ground truth, an optimal imperfect-information policy, a
calibrated probability, proof that the observed Card was wrong, or proof that a
different Card wins the actual deal.

Immediate evidence preserves the existing ordered `analysis_report` Candidate
array and its exact metrics. It does not rerank, normalize, rescale, or recompute
Candidates. Immediate remains heuristic sampled expected-value analysis.

When Search was attempted, evidence preserves the complete existing aggregate
bounded Search Result, including:

* `complete`, `partial`, `timeout`, or `unavailable` status;
* stop reason, world coverage, and solution claim;
* requested and consumed structural budgets;
* compatible-, selected-, completed-, sampled-, and unique-sampled-world counts;
* ordered aggregate Candidate ranks and metrics;
* Search recommendation and fallback state;
* exact operational elapsed time.

No compatible-world Cards, ownership assignments, Search state, cache, branch,
or Principal Variation is retained. Bounded Search remains compatible-world
determinization subject to Strategy Fusion, not a complete hidden-information
solver.

Auto evidence preserves whether Search supplied the effective recommendation,
whether Immediate fallback supplied it, or whether no recommendation was
available. The exact existing requested/effective method, Search-attempt,
fallback, fallback-method, and analysis-report-method fields remain unchanged.

`recommendation_available` means only that the retained recommendation Card is
non-null and the effective method is not `none`. Otherwise the status is
`recommendation_unavailable`. Search `partial`, `timeout`, and `unavailable`
remain valid evidence states.

## Review, Profile, and policy context

Evidence preserves the existing Immediate actual-Card review and, when Search
was attempted, the bounded Search actual-Card and Search-versus-Immediate
comparisons. Existing unavailable reasons, ranks, aggregate-equivalence facts,
completed-world counts, and metric gaps remain method-bound values. No new
quality scale or real-deal outcome claim is added.

The actual Card is the retained observed behavior from the source Play. It is not
an optimal label.

Evidence also preserves:

* the exact immutable relative Profile binding;
* generic and separate left/right effective opponent-policy settings;
* Profile-Preset settings;
* the optional existing Profile-application summary.

No Profile or Statistics value is derived or applied again. Complete Opponent
Statistics records are not copied.

## Multiple Reports and collection

Several distinct Reports may reference the same Decision Reference. Different
methods, sample counts, seeds, budget profiles, Profile-Preset settings, Search
outcomes, or elapsed times remain separate evidence values. Exact duplicate
source bindings are rejected. Equal semantic fingerprints do not merge source
observations, and no preferred Teacher, consensus, vote, average, weight, or
winner is selected.

The collection retains exact Store identity, Current Snapshot IDs, deterministic
coverage counts, and canonically ordered evidence. Ordering uses Match ID, Match
position, Decision index, existing requested-method order, source Report
fingerprint, and Evidence ID. Empty source input produces a valid empty
collection.

## Export and privacy

The path-free export document kind is:

```text
skat_ai_learning_corpus_strategy_teacher_evidence
```

The export builder wraps one already-built collection. Serialization performs one
JSON serialization with UTF-8, ASCII escaping, finite values, two-space
indentation, LF line endings, and one trailing LF. It accepts no path and writes
no file.

The private minimized export may contain stable Match/Game/Decision/Player
identity, legal Cards, actual/recommended Cards, Candidate aggregate metrics,
Search budgets and status, review comparisons, and Profile/policy context. It
does not contain a complete private hand, original Skat, Discards, unrelated
observed Cards, Search Worlds, private Search state, Commentary text, Response
associations, or complete Statistics records. Fingerprints provide deterministic
identity, not confidentiality, authenticated authorship, encryption, access
control, backup, or secure deletion.

Human Evidence remains a separate factual communication artifact. Issue #176
joins both exact supplied families through the same Decision Reference while
retaining separate normalized pools and Record ID references. It preserves every
Teacher in source order and still does not interpret Commentary, infer
communication meaning, select a preferred Teacher, or claim agreement between a
human and the engine. See [Learning Dataset version 2](learning_dataset_v2.md).

## Compatibility and open work

Issue #175 adds no Corpus object kind, Catalog field, persisted report, file
format, browser operation, CLI, Public API, Root workflow, Schema, example, or
generated scenario. Package version remains `0.15.0`; Python remains `>=3.13`;
seven Root workflows, one Console Script, 63 authoritative and packaged Schemas,
six Session examples, 85 generated outputs, and Training Dataset version `1`
target `actual_card_played` remain unchanged.

Strategy Teacher persistence, Corpus object storage, browser/CLI transport,
Public API, Schema, Historical Report import, Replay Coaching evidence import,
Teacher consensus/ranking, Dataset-v2 persistence and task builders, persisted
splits, cross-game summaries, and model training remain open.
