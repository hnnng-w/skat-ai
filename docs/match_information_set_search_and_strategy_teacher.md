# Match Information-set Search and Strategy Teacher Evidence

## Scope and compatibility

Issue #191 adds one private version-1 integration path from an explicit Match
Decision through strict `information_set_search`, an exact Match Analysis Report
source, Current-Snapshot Strategy Teacher Evidence, Learning Dataset version `2`,
cross-game summaries, and the existing local Learning Corpus browser workflow.

The focused internal contract identities are:

* `MATCH_INFORMATION_SET_SEARCH_INTEGRATION_VERSION = 1`
* `LEARNING_CORPUS_INFORMATION_SET_STRATEGY_TEACHER_EXTENSION_VERSION = 1`

The integration does not change Package version `0.16.0`, Public API contract
version `1`, the seven Root workflows, the one Console Script, any existing
Match, Strategy Teacher, Dataset, Summary, Report-source, or Web Protocol
contract version, or any public Schema. The working baseline remains 69
authoritative and packaged Schemas, six Session examples, and 94 generated-
output scenarios.

That 69/94 count is the Issue #191 point-in-time baseline. Issue #192
subsequently adds separate Information-set Replay Coaching and Match Historical
Information-set Review/Coaching, one Schema, one Root example, and two scenarios.
The Issue #192 point-in-time baseline is therefore 70 authoritative and packaged
Schemas, six Session examples, and 96 generated-output scenarios. The one-
Decision Teacher path in this document remains unchanged.

Issue #193 changes neither count, and Issue #194 adds one Tactical Motif Review
Schema and two scenarios. The
current working baseline is 71 Schemas and 98 scenarios; the one-Decision Teacher
path remains unchanged.

## Match execution

`information_set_search` is the fourth explicit flat Match Decision method,
alongside `immediate_expected_value`, `bounded_search`, and `auto`. A caller must
supply `search_random_seed`. The local Match browser supplies seed `0` when the
method is selected and the seed field is empty.

The Match adapter builds one existing Position Request and executes the existing
Position Application exactly once. Information-set Search, same-selection PIMC,
the independently seeded Immediate baseline, and actual-Card comparison remain
inside that one Application invocation. The Match layer validates the resulting
safe aggregates and does not rerun Search.

Information-set Search is strict. Complete, partial, timeout, and unavailable
Results are retained as produced. A Result without an Information-set
recommendation does not fall back to Immediate or another method. Existing
`auto` behavior is unchanged, and there is no `information_set_auto` method.

Capture mutation, rendering, upload, and artifact preparation do not execute
analysis automatically. Execution remains one explicit user action.

## Budget mapping

The existing Match Search profiles map to all nine Information-set settings:

| Match profile | Remaining Tricks | Depth plies | State nodes | Information Sets | Selected Worlds | Sampled Worlds | Minimum comparable | Timeout |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `interactive_v1` | 3 | 9 | 500,000 | 500,000 | 64 | 32 | 8 | 1,000 ms |
| `historical_review_v1` | 3 | 9 | 2,000,000 | 2,000,000 | 128 | 64 | 16 | 5,000 ms |

The ninth setting is the explicit Match `search_random_seed`. Match Decision
analysis does not accept caller-defined Information-set budgets or the separate
Training Dataset `evaluation_v1` profile.

## Fixed opponent policies

The existing Position policy precedence remains authoritative. Effective left
and right lead/response policies, including eligible time-safe Profile effects,
become the deterministic fixed-player policies for Information-set Search.
Profile Statistics do not weight Compatible Worlds, alter World selection, or
claim calibrated probabilities.

Match execution reconciles the top-level effective policy settings, Profile
application summary, and safe Information-set fixed-policy settings. Strategy
Teacher preparation rebuilds the exact Match Request and eligible Statistics
context and performs the same reconciliation before accepting evidence.

## Retrospective comparison

The Post-game sequence is fixed:

1. Execute Information-set Search from the decision-time information boundary.
2. Execute PIMC over the exact same selected-World sequence when available.
3. Execute the existing independently seeded Immediate baseline.
4. Attach the observed actual Card only after all decision-time analysis.

The comparison is descriptive. Agreement flags, ranks, and same-denominator
metric deltas do not identify ground truth, prove accuracy, or make one method a
preferred Teacher. Match reconciliation checks every comparison fact derivable
from the retained safe Search aggregates and Card values.

## Reports and browser diagnostics

The existing revision-scoped `MatchAnalysisReportV1` retains the exact
schema-valid Position Result. The local Match browser projects only curated safe
diagnostics:

* status, stop reason, World coverage, Policy claim, and Policy consistency;
* Compatible, selected, completed, Information-set, and Policy-decision counts;
* Information-set, PIMC, Immediate, and actual Cards;
* bounded Card-agreement facts.

The browser view excludes Candidate tables, wall-clock time, fixed-policy
details, private Worlds, hidden hands, Exact States, Observations, controlled
Policy tables, memoization caches, branches, and derived child seeds.

## Exact Report-source transfer

The unchanged Match Analysis Report-source export version `1` transfers the
exact options, Profile binding, Position Request, Result, warnings, report
identity, and revision identity. Strict reconstruction validates the input and
output Schemas, requested settings and budgets, legal Cards, consumed-budget
relationships, Candidate arithmetic and deterministic ranking, method summary,
fixed policies, and retained comparison facts. Canonical identity fields and
unknown-field rejection remain unchanged.

The source envelope is an explicit transfer boundary. Match Capture does not
discover a Corpus root, publish to a Corpus automatically, or persist a derived
Teacher artifact.

## Focused Strategy Teacher Evidence

`LearningCorpusInformationSetStrategyTeacherEvidenceV1` is a builder-only,
immutable, minimized extension nested in the existing private Strategy Teacher
Evidence. It retains:

* the complete safe aggregate Information-set Result;
* the complete safe retrospective comparison;
* requested and consumed budgets;
* Candidate aggregates and deterministic recommendation;
* World coverage and bounded Policy claims;
* fixed left/right policy settings and aggregate Policy counts;
* Information-set, PIMC, Immediate, and actual Cards.

Its governing policy is
`method_bound_information_set_evidence_not_ground_truth`. Exact source and
Evidence identities include `wall_clock_elapsed_ms`; the semantic Teacher
identity normalizes that diagnostic field. An elapsed-time-only change therefore
changes exact identities without changing semantic identity.

The focused Evidence excludes private Worlds, exact ownership, observations,
hidden hands, the controlled contingent Policy table, caches, branches, Profile
Statistics Records, Commentary, and Responses. It does not create a correctness,
causal, calibrated-probability, or preferred-Teacher label.

## Dataset and summary propagation

Learning Dataset version `2` uses its existing normalized Strategy Teacher pool
and exact Decision Reference joins. No new top-level Dataset field or Evidence
family is introduced. A Decision Record ID remains stable when Teacher Evidence
is added, while the Record content fingerprint and Dataset fingerprint change to
close over the added evidence.

The existing Strategy Teacher collection adds
`information_set_search_requested_count`. Cross-game Strategy summaries use the
four canonical flat requested methods and count `information_set_search` and its
effective `bounded_information_set_policy_search_v1` method. They do not
aggregate Candidate quality, infer accuracy, or rate Players.

Dataset version `2`, Strategy Teacher, partition, and Summary contract versions
remain unchanged.

## Learning Corpus workflow

The existing local Corpus workflow accepts the exact Report-source upload,
retains it in the bounded process-local source store, orders it after the three
existing flat methods, and carries it through explicit Strategy Teacher,
Dataset-v2, partition, and Summary preparation. The same seven authenticated
canonical downloads remain available.

Issue #191 adds no Corpus route, operation, download kind, persisted object,
automatic Report capture, Public API, Schema, example, or generated scenario.

## Remaining boundaries

The following remain open or intentionally unchanged:

* performance and latency evidence;
* automatic Report capture and Report or derived-artifact persistence;
* Historical Strategy Teacher Report import and automatic Coaching Report
  transfer;
* public Match, Corpus, Strategy Teacher, or Dataset-v2 APIs and Schemas;
* a global cross-decision Policy, equilibrium, calibrated probability, or
  complete-contract solver;
* broader Strategy-Fusion correction beyond the bounded controlled-player scope;
* `information_set_auto` or any change to existing `auto`.

See also [Match analysis and exports](match_analysis_and_exports.md),
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md),
[Learning Dataset version 2](learning_dataset_v2.md), and
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).
Issue #192's separate Historical path is documented in
[Information-set Replay Coaching and Match Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md).
