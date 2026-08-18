# Match analysis and exports

Issue #168 completes the functional `v0.15.0` local Match Capture milestone by
connecting the private Match Capture browser to the existing Position and
Historical Application workflows and to the Issue #167 materialization layer.
Execution remains explicit. Capture mutations, ordinary page rendering, state
inspection, and Workspace Resume never trigger analysis automatically.

This is an internal local capability. Issue #168 itself changed no Package
version, Public API contract version `1`, seven Root workflows, 63 authoritative
and packaged Schemas, six Session examples, or 85 generated-output scenarios.
Issue #169 completed Package version `0.15.0` and release-documentation
preparation without changing this capability. The maintainer published the
Release manually at commit `ec1c154`, and Issue #170 synchronizes publication
status.

## Contract identity

The private version-1 contracts cover:

```text
MATCH_ANALYSIS_EXECUTION_VERSION = 1
MATCH_DECISION_ANALYSIS_OPTIONS_VERSION = 1
MATCH_HISTORICAL_ANALYSIS_OPTIONS_VERSION = 1
MATCH_ANALYSIS_REPORT_VERSION = 1
MATCH_ANALYSIS_REPORT_STORE_VERSION = 1
MATCH_ARTIFACT_EXPORT_VERSION = 1
```

The three explicit browser operations are:

```text
prepare_materialization
analyze_decision
analyze_historical_game
```

The execution policy is one exact existing Application invocation for an
available selected Decision or strict Historical Game. Materialization prepares
existing values and executes no Root workflow.

## One-Decision Position analysis

`analyze_decision` selects exactly one retained prepared Decision by Match
position and one-based Decision index. It can execute from a partial observed
trace when Issue #167 can reconstruct the acting Player's exact current hand; it
does not require strict Historical materialization or all 30 Decisions. Normal
unavailability reports distinguish a non-observed Slot, an index not retained in
the trace, and a retained Decision that cannot be prepared.

The selected snapshot supplies only the Decision-time own hand, legal Cards,
public Trick prefix, points, public hand sizes, legitimate Skat visibility,
declared-Ouvert public hand, and relative Player mapping. It becomes one
validated nonterminal flat Position Request with
`analysis_mode = post_game_review`. The observed Card is attached only after the
visible-state cutoff as retrospective evidence. It is not an optimal label,
ground truth, Search target, hidden-ownership input, or permission to use future
opponent Cards. Commentary and Response Links are not copied into the Request.

The explicit methods are:

* `immediate_expected_value`;
* strict `bounded_search`;
* Search-first `auto` with the existing Immediate fallback semantics.

Immediate sample count and seed remain separate from the Search seed. Match
analysis accepts the immutable `interactive_v1` or `historical_review_v1` Search
budget profile, not a caller-defined budget or `evaluation_v1`. Search may
normally be complete, partial, timed out, or unavailable. An unavailable Search
inside a valid Position execution is still an executed Root Result.

The resulting Application output is schema-validated and reconciled against the
Match ID, Workspace revision, Match position, Decision index, actual Card, and
Profile binding before it becomes a report.

## Relative Profile application

Match-bound Statistics remain eligible only when `captured_at < played_at`.
For each selected Decision, eligible stable Players are remapped to the acting
Player's relative `left` and `right` opponents. The acting Player is always `me`
and is never bound as an opponent, even when that Player has an eligible
Snapshot.

When Profile Presets are enabled, an eligible and confidence-gated actionable
side Profile enters the existing Position Application policy-precedence path.
When Profile Presets are disabled, the binding may still be reported by the
private Match report, but the stable Root Profile summary is omitted. The
private report records `profile_presets_disabled`, and the existing default
policies remain effective. An eligible but nonactionable derivation records the
existing `not_actionable` reason and changes no policy. An absent or temporally
ineligible side is not injected as a bound opponent.

Profiles affect only behavior already supported by the existing Application.
They are not compatible-world weights and do not alter bounded Search. For a
strict Historical execution, Match Statistics are injected only when Immediate
Review and Profile Presets are both enabled, and then use the existing time-safe
Historical per-Decision behavior. This does not claim that Profiles alter
Historical Search Review or Replay Coaching. Coaching also does not consume
Workspace Commentary or Response Links.

## Strict Historical analysis

`analyze_historical_game` first applies the unchanged strict Issue #167
availability boundary. Execution requires a complete legal 30-Play trace,
Declarer and complete Declaration including bid, known original Skat, exact
Discards, and a reconstructable complete Deal. Empty Slots, Passed Deals, and
insufficient observed-Game evidence return the canonical materialization reason
without invoking Application.

For an available Game, the caller selects at least one existing mode:

* Decision Snapshots;
* Immediate Historical Review;
* Historical Search Review;
* Replay Coaching.

Search Review and Replay Coaching require an explicit Search seed and accept the
same two Match Search budget profiles. The complete selected configuration is
passed through one Historical Application invocation. When both Search Review
and Coaching are selected, the existing Historical workflow retains its shared
analysis behavior rather than adding a Match-specific rerun.

## Match materialization

`prepare_materialization` traverses the exact 36-Slot Workspace once and executes
no Position, Historical, Training Dataset, list, or other Root workflow. Its
revision-scoped report shows:

* occupied, empty, observed-Game, and Passed Deal counts;
* prepared and skipped Decision counts;
* strict Historical Game and unavailability counts;
* unpartitioned Training source Record counts;
* Commentary and Response Link counts as sidecar facts;
* fixed-list availability, final standings, unresolved `lot_required` Players,
  and applied external lot order;
* exactly the twelve round-end Progression snapshots when aggregation is
  available.

The prepared list reuses the existing fixed-three-player 36-position source and
aggregation contracts. The browser neither invents nor executes a random lot.
Materialization does not interpret Commentary, generate Dataset partitions or
samples, execute list comparison, or run any analysis workflow.

## Ephemeral reports and concurrency

Each report ID is a deterministic lowercase SHA-256 digest of the canonical
version-1 report identity, including its source Match and Workspace revision,
kind, selection, and value. Equal report content therefore has equal identity.
The process-local insertion-ordered store retains at most eight reports and
evicts the oldest report when a ninth distinct report is added.

Reports are not written into the Workspace or another server-side file. They are
cleared after an applied Workspace mutation, explicit Reload, or server shutdown.
Unchanged operations and revision or persistence conflicts do not clear them.
A report from a different current revision is stale and cannot be viewed or
downloaded as current.

Analysis captures the Match ID, Workspace revision, retained content fingerprint,
and private report-store generation under the context lock, then releases the
lock for potentially long workflow execution. It reacquires the lock before
publishing. If the Workspace or report-store generation changed meanwhile, the
stale result is discarded, HTTP `409` is returned, and there is no retry. This
ensures Reload or another invalidation discards in-flight work even if revision
and fingerprint alone would otherwise match. An already mismatched expected
revision also returns `409` without execution.

## Authenticated local downloads

Downloads reuse the existing token-established `HttpOnly`, `SameSite=Strict`
cookie and loopback Host checks. Mutation and analysis POSTs additionally retain
same-origin protection. No download accepts or exposes a server filesystem path.

An executed Decision or Historical report can download its exact existing Root
Result document. A current materialization report enables canonical JSON
downloads for:

* the complete Match materialization summary;
* the available strict Historical Game collection in Match-position order;
* the unpartitioned Training source collection;
* the existing fixed-three-player historical-list Root input, when available;
* the existing fixed-list aggregation, when available.

Exports use deterministic ASCII-safe filenames and canonical UTF-8 JSON with
two-space indentation, LF line endings, ASCII escaping, and exactly one trailing
LF. These are private browser downloads, not Public API artifacts or new Root
workflows.

## Privacy and product boundaries

Selected browser report pages expose curated summaries, while exact downloads
may contain private Cards, hands, Historical records and Results, Statistics, and
Profile application details. Neither reports nor downloads receive public field-
provenance redaction. Users must protect the Workspace and downloaded files as
private local data. Report IDs and Workspace fingerprints provide deterministic
identity and conflict detection, not confidentiality or authenticated authorship.

Issue #168 adds no Public Match API, Match Schema, Match Root workflow, public
Match JSON/data CLI, new Capture CLI option, persisted Workspace report, automatic
analysis, database, remote deployment, or public export contract. It does not add
Comments to Coaching, tactical interpretation, causal attribution, calibrated
machine learning, optimal hidden-information Search, complete-contract Search,
or complete official-rule coverage. Compatible-world Search remains bounded
late-game determinization subject to Strategy Fusion; sampled worlds are not
calibrated probability, and timeout behavior is machine-dependent.

Issue #168 completes the functional local Match Capture scope planned for
`v0.15.0`. Issue #169 completed Package/release metadata and documentation
preparation, and Issue #170 records the subsequent manual publication. Public
Match API and
Schema/data workflow, a public/persisted Player Catalog, public/task-specific
Dataset workflows and Dataset-v2 persistence,
database or remote deployment, YouTube and EuroSkat integration, and broader
pre-v1 rules, Search, Coaching, Settlement, and Provenance work remain open.

Issue #171's separate private Learning Corpus Match Snapshot and Catalog
contracts import no Match Analysis report and execute no analysis. Reports remain
ephemeral process-local values under this document's unchanged behavior. Derived
annotations remain separate open objects rather than Match Snapshot or Catalog
fields. Issue #176's separate in-memory Dataset version `2` also remains outside
Match Snapshot, Catalog, and report persistence. See
[Learning Corpus identity and Catalogs](learning_corpus_identity_and_catalogs.md)
and [Learning Dataset version 2](learning_dataset_v2.md).

Issue #172 persists and imports only exact Workspace Match Snapshots. It imports
no Match Analysis report, and Corpus initialization, Resume, import, and Current-
selection changes execute no analysis or materialization workflow. See
[Learning Corpus persistence and Workspace import](learning_corpus_persistence_and_import.md).

Issue #173 derives only Player, exact alias, and Match-bound Statistics history
from explicit Current Match Snapshots. It imports no report and executes no
analysis. See [Learning Corpus Player Catalog and Statistics history](learning_corpus_player_catalog_and_statistics_history.md).

Issue #174 derives a separate minimized exact human Commentary and linked
Response Evidence export from explicit Current Match Snapshots. Building or
serializing that export executes no Match Analysis, Search, Historical Review,
Replay Coaching, Profile application, or Training Dataset workflow and changes no
report or Application input. See
[Learning Corpus human Commentary and Response evidence](learning_corpus_human_commentary_and_response_evidence.md).

Issue #175 accepts caller-supplied exact executed Decision Analysis Reports as
non-persisted Strategy Teacher sources. It binds each Report to one explicit
Current Match Snapshot, rebuilds and compares one Position Request without
execution, validates the retained Result, and preserves exact Immediate/Search/
Auto method evidence plus actual-Card comparisons and Profile/policy context. It
does not change this document's Report Store lifetime, automatically capture a
Report, execute analysis, or import Historical Analysis Reports. See
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md).
