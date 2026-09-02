# Unified local frontend guided analysis and Results

## Status

Issue #211 implements the guided Analyze and Review slice of the
[unified local frontend contract](unified_local_frontend_contract.md). It extends
the Issue #210 [application shell](unified_local_frontend_application_shell.md)
without adding a Root workflow, Public API export, Schema, persistence format,
dependency, or Product algorithm.

The implemented browser areas are:

```text
/analyze
    guided current or retrospective one-Decision analysis
    guided one-Decision Post-game Review
    strict Position JSON import

/review
    guided normal-completion Historical entry
    strict Historical and retrospective Position JSON import

/sessions
/matches
/learning
    managed stateful workflows implemented by Issue #212
```

Package version remains `0.17.0`, Public API contract version remains `1`, the
Root workflow count remains seven, and the one Console Script remains
`skatmind = skatmind.cli:main`.

## Private contracts

The private versions are exactly:

```text
GUIDED_ANALYSIS_FRONTEND_VERSION = 1
GUIDED_POSITION_FORM_VERSION = 1
GUIDED_HISTORICAL_REVIEW_FORM_VERSION = 1
FRONTEND_RESULT_PRESENTATION_VERSION = 1
FRONTEND_JSON_TRANSFER_VERSION = 1
PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION = 1
```

The private policy tuple is exactly:

```text
guided_forms_build_existing_root_documents
one_explicit_application_execution_per_run
normal_forms_reuse_existing_product_defaults
advanced_settings_are_collapsed_and_explained
strict_json_import_is_explicit_and_non_executing
exact_json_download_uses_retained_values
public_result_is_the_only_presentation_source
normal_result_states_are_not_transport_errors
process_local_state_without_implicit_persistence
private_engine_state_never_enters_browser_state
```

These identities are independent from Package, Public API, Root workflow,
Schema, Session, Match, Corpus, Search, and persistence versions.

## Process-local state

Analyze and Review have independent immutable revisioned state under the existing
application-context lock. Each area retains at most one draft or imported
`RequestDocumentV1`, one latest successful Request/options/Result tuple, exact
precomputed download bytes, safe validation messages, and one in-progress source
revision.

Every accepted input mutation advances its route-specific revision once and
invalidates older output. Validation failure retains safe form values. Execution
failure publishes no successful Result. Reset requires explicit confirmation.
Stale forms and duplicate Run attempts return HTTP `409`; stale completed work
cannot overwrite newer state. Product execution occurs outside the context lock,
and publication rechecks the exact source revision without retry.

State contains no timestamp, caller path, persistent Product identifier, Session,
Match Workspace, Corpus object, or managed-storage reference. Closing the process
discards drafts, imports, and Results unless the user explicitly downloaded JSON.

## Position form

`/analyze` begins with the normal choice between a current decision and one
actually played retrospective Card. The normal sections are:

```text
Your role and the contract
Cards you can currently see
Completed tricks and current trick
Current score and turn
Run analysis
```

The form supports Suit, Grand, and all four Null declaration variants; Declarer
and Defender perspectives; all three local seats; declaration flags; bid value;
optional Matadors; the local hand; legitimately visible Skat and public Declarer
Cards; completed and current Tricks; points; opponent Cards remaining; and the
retrospective actual Card.

The canonical 32-Card control order and readable labels come from the existing
Deck and Card-name contracts. Existing Product helpers validate Card uniqueness,
declaration dependencies, Trick order and winners, Turn Phase, all three
remaining hand sizes, information visibility, and actual-Card legality. The
frontend does not infer hidden ownership or calculate Game value independently.

Normal Position translation preserves:

```text
sample_count = 1000
random_seed = 42
use_basic_opponent_strategy = true
recommendation_method = omitted
analysis_mode = live_decision unless retrospective was selected
game_end_reason = not_ended
validate_output = true
```

## Advanced Settings

Both workflows use the six initially collapsed groups:

```text
Analysis method
Runtime and reproducibility
Opponent behavior
Simulation and comparison
Technical evidence
Dataset and evaluation
```

Analyze maps understandable controls to the existing Immediate, bounded Search,
Auto, Information-set Search, Multi-Step, Policy Comparison, opponent Policy,
Profile-preset, sample, seed, and public Provenance options. Existing versioned
interactive Search settings are reused rather than duplicated.

Review exposes the existing Decision Snapshot, Immediate Review, bounded Search
Review, Information-set Search Review, Replay Coaching, Information-set Replay
Coaching, Tactical Motif Review, seed/sample, Historical Review budget-profile,
and public Provenance options. Selected dependent families show their existing
implied prerequisites before Run. The two pages contain no fake Dataset control;
the Dataset group states that those operations remain advanced automation.

Settings explain runtime, reproducibility, evidence scope, fixed-policy behavior,
and boundedness. They do not change Skat rules, promise calibrated probability,
describe Search as perfect play, or describe rule-based behavior as a learned
prediction.

## Historical editor

The normal `/review` editor has exactly seven server-rendered steps:

```text
1. Players and seats
2. Deal
3. Declarer and declaration
4. Skat pickup and Discards
5. Card play
6. Review options
7. Validate and run
```

It uses deterministic process-local IDs `frontend-forehand`,
`frontend-middlehand`, and `frontend-rearhand`, and Game ID
`frontend-historical-review`. Optional non-empty display labels must be unique.
The editor accepts one exact 10/10/10/2 Deal, validates pickup or Hand-game
Discards, derives each acting Player and legal Card set, and delegates actor,
winner, and next-leader replay to the existing observed-trace and rule helpers.
It appends one chronological Card at a time and can undo only the final play.
Back preserves valid entered facts; a completed Play step can return to Review
options without re-entry.

The bounded manual editor emits only `normal_completion` after exactly 30 legal
plays. It does not remove broader Historical support. Existing shortened endings,
continuations, party-wide Claims, concession/exposure/open-play variants, and
other supported Historical documents remain available through optional strict
JSON import and receive the same Result presentation.

## JSON import

Import is a secondary explicit action and never executes. Each page accepts one
strict multipart upload containing one finite UTF-8 JSON object without a BOM,
duplicate object keys, nested multipart, duplicate file fields, or unsupported
headers. The maximum file content is exactly `1,048,576` bytes; bounded multipart
framing is accounted for separately. Caller filenames are ignored and retained
nowhere. Parsing uses no temporary file.

Analyze accepts only `position_analysis`. Review accepts `historical_game` and
`position_analysis` with exact `analysis_mode=post_game_review`. Existing public
input parsing constructs one immutable Request, and a separate explicit Run is
required. Incompatible workflows produce a distinct safe HTTP `400` response.

## Application execution

Every explicit Run constructs or reuses one immutable Request and one immutable
`ExecutionOptionsV1`, then calls the existing Public/Application execution
boundary exactly once with one of:

```text
memory://skatmind/app/analyze
memory://skatmind/app/review
```

No CLI subprocess, Root input file, external request, execution retry, Search
workflow rerun, Historical workflow rerun, or render/download execution exists.
The retained public `ExecutionResultV1` is the only Product source for
presentation. Presentation
does not inspect private Search Worlds, Application bundles, private Provenance,
or hidden ownership and does not recompute recommendations, settlement, winner,
score, or decision quality.

## Result presentation

Successful Results appear before the secondary raw-JSON import controls. Result
content uses these exact sections and order:

```text
Summary
Recommendation
Alternatives
Evidence and limits
Technical details
```

Technical details use a native disclosure closed by default. Candidate and
Decision tables preserve retained public order. Whole-game Results explicitly
state that there is no single whole-game Card recommendation. Review coverage,
warnings, fallback, boundedness, information cutoffs, fixed-policy limits,
selected-world limits, observed-Card limits, Coaching/Tactical limits, and Claim
scope are shown only from retained public fields.

Existing normal states such as `complete`, `partial`, `timeout`, `unavailable`,
`final`, `lot_required`, and `not_assessable` remain successful Result pages, not
HTTP failures. Observed Cards are not described as ground truth, and Search is
not described as perfect play or calibrated probability.

## Errors and HTTP behavior

The private browser transport uses these status meanings:

```text
303    accepted POST followed by redirect
400    input, import, or public validation failure
404    unknown route or unavailable retained download
405    unsupported method on a known route
409    stale revision, stale publication, or duplicate execution
413    oversized request or JSON file
415    unsupported media type
500    generic unexpected internal failure
```

Form failures show an error summary and field-local escaped messages where a safe
public path maps to a visible control. Safe submitted Deal selections remain in
the process-local draft for correction. Unexpected, resource, serialization, and
invariant failures expose no internal message, stack, token, path, fingerprint,
private Source Reference, hidden Card, or complete uploaded document.

## Private routes

The documented private action paths are:

```text
/actions/analyze/run-guided
/actions/analyze/import-json
/actions/analyze/run-imported
/actions/analyze/reset

/actions/review/start
/actions/review/update-players
/actions/review/update-deal
/actions/review/update-declaration
/actions/review/update-discards
/actions/review/append-play
/actions/review/undo-play
/actions/review/update-options
/actions/review/back
/actions/review/run-guided
/actions/review/import-json
/actions/review/run-imported
/actions/review/reset
```

The exact authenticated GET download paths and filenames are:

```text
/downloads/analyze/request.json
    skatmind-position-request.json

/downloads/analyze/result.json
    skatmind-position-result.json

/downloads/review/request.json
    skatmind-review-request.json

/downloads/review/result.json
    skatmind-review-result.json
```

Request downloads use the retained canonical Root document. Result downloads use
the full existing public serializer envelope, including public warnings and
artifacts. Both use deterministic finite UTF-8 JSON bytes, LF line endings, and
one trailing newline. They rebuild and execute nothing and are unavailable before
the corresponding retained value exists.

## Security and accessibility

Issue #211 preserves the Issue #210 loopback token/cookie boundary, exact Host
and mutation-Origin checks, duplicate-header rejection, bounded reads,
`Transfer-Encoding` rejection, restrictive CSP, `no-store`, `nosniff`, frame
denial, no CORS, no access log, and no external resource or runtime request.
Issue #214 changes the response policy from `no-referrer`, which makes non-CORS
browser POST Origin serialization `null`, to `Referrer-Policy: origin`. Concrete
same-origin Review POSTs are accepted; missing, null, forged, malformed, and
Host-mismatched Origins remain rejected. Any Referer is origin-only and therefore
contains no source path or query.

Normal workflows use semantic server-rendered forms, visible labels, text status,
keyboard-operable native Card controls, field-linked error summaries, local error
descriptions, native collapsed disclosures, semantic Result headings and tables,
normal download links, visible focus, and responsive packaged CSS. No JavaScript
is required or currently shipped.

## Current boundary and UAT state

Analyze and Review remain usable and process-local. Session, Match Capture, and
Learning Corpus lifecycle integration is implemented by Issue #212, and Issue
#213 provides canonical `skatmind run` and layered CLI help.

Repeated UAT-01 exposed UAT-FINDING-004. Issue #214 implemented the browser-
Origin correction, and maintainer Microsoft Edge verification resolved both
Issue #214 and UAT-FINDING-004. Repeated UAT-01 nevertheless failed. Issue #208
remains open; UAT-02 through UAT-12 remain paused; B-09 and B-07 remain open;
B-06 remains closed; and Package `1.0.0` and Release preparation are not ready.

Issue #215 freezes the authoritative
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
Issue #216 implements the shared private profile/localization foundation. When
German is active, future-owned Analyze and Review bodies remain explicitly
marked English pending Issue #220. Issue #217 adds localized one-Decision
current/retrospective and one-completed-Game guidance plus safe related links
outside that English region without changing either workflow. Issue #218 is the
exact next action.
