# Unified local frontend contract

## Authority and status

This document is the authoritative version-1 Product and architecture contract
for the unified local SkatMind frontend and its application-launch boundary.
Issue #209 froze this contract in response to the accepted Issue #208 UAT
findings. Issue #210 implements launch routing, the managed home, Home,
navigation, About, secure serving, packaged assets, and honest placeholders.
Issue #211 implements guided Analyze/Review and Result presentation. Issue #212
implements managed stateful workflows. Issue #213 implements the final CLI
onboarding and advanced-automation slice frozen below.
Issue #216 implements the private profile/localization foundation and bilingual
common-shell slice documented in
[Local frontend profile and localization](local_frontend_profile_and_localization.md).
Issue #217 implements grouped Home/Product concepts, and Issue #218 implements
validation preservation and localized feedback documented in
[Frontend validation state and localized feedback](frontend_validation_state_and_localized_feedback.md).
Issue #219 implements private profile-driven Session/Match/Learning creation,
known Players, generated identities, saved defaults, and display labels as
documented in [Profile-driven stateful creation](profile_driven_stateful_creation.md).

This document remains authoritative for the implemented version-1 frontend.
The authoritative implemented-foundation and remaining bilingual, profile-driven
UX boundary is frozen
separately in the
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).

The three states in this document must remain distinct:

```text
Current behavior:
    the behavior implemented by Package 0.17.0

Approved target contract:
    the complete required behavior frozen by Issue #209

Implemented behavior:
    the Issue #209 target plus the Issue #216 through #219 profile,
    information-architecture, validation-preservation, and creation slices
```

Current executable contracts, Public APIs, persistence formats, browser
protocols, Schemas, and information controls remain authoritative while the
implemented target remains in use. Issue #209 changed none of them; Issues #210
through #219 add only their assigned private frontend and onboarding boundaries.

## UAT source

UAT-01 technically executed successfully on the tested installation but failed
user acceptance. Issue #208 records these accepted findings:

```text
UAT-FINDING-001:
    No acceptable primary Product user interface exists.
    Severity: blocker
    Disposition: accepted_for_remediation

UAT-FINDING-002:
    Root CLI onboarding is an unstructured expert interface.
    Severity: major
    Disposition: accepted_for_remediation

UAT-FINDING-003:
    Session, Match Workspace, and Learning Corpus are not understandable
    user concepts.
    Severity: major
    Disposition: accepted_for_remediation
```

Issue #209 defines the remediation contract but closes none of these findings,
does not repeat UAT-01, and does not resume the remaining UAT cases.

## Contract identity

The frozen internal contract versions are:

```text
UNIFIED_LOCAL_FRONTEND_CONTRACT_VERSION = 1
LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION = 1
MANAGED_LOCAL_DATA_CONTRACT_VERSION = 1
```

Issue #210 implements these identities as private Product-code constants. They
remain independent of the Package version, Public API contract version,
seven Root workflow contracts, Session contracts, Match Workspace contracts,
Learning Corpus contracts, Schema versions, and browser-protocol versions.

The exact internal policies are:

```text
bare_skatmind_opens_unified_local_frontend
one_loopback_server_one_browser_application
managed_local_data_without_required_user_paths
guided_normal_workflows_with_advanced_settings_separated
human_readable_results_with_optional_json_import_and_export
reuse_existing_application_session_match_and_corpus_contracts
no_product_semantics_change_from_frontend_translation
no_external_frontend_resources_or_runtime_requests
advanced_cli_and_public_python_api_remain_supported
existing_private_information_boundaries_remain_authoritative
```

These policy strings are private internal policies, not Public API exports.

## Current behavior

Package `0.17.0` currently exposes one Console Script,
`skatmind = skatmind.cli:main`, and supports installed, module, and repository-
root Legacy invocation. Empty argv and leading `app` select the unified shell;
leading `corpus`, `capture`, and `session` retain their separate command families;
leading `run` selects canonical Root JSON automation; top-level help and version
remain lightweight; option-like first tokens retain direct Root compatibility.

Consequently, current behavior is:

```text
skatmind
    launch the unified local application shell

skatmind app
    explicitly launch the unified local application shell

skatmind --help
    show concise Product-oriented help

skatmind run --input ...
    run canonical advanced Root JSON automation

skatmind run --help
    show the complete grouped Root option interface

skatmind --input ...
    run the Package-1.x direct Root compatibility route

skatmind session ...
    run the direct Session CLI with an explicit Session path

skatmind capture --workspace PATH ...
    run one standalone Match Capture server for one explicit Workspace file

skatmind corpus --corpus PATH ...
    run one standalone Learning Corpus server for one explicit Corpus root
```

`python -m skatmind` enters the same Package-owned dispatch. Repository-root
`python main.py` remains the Legacy facade. Match Capture and Learning Corpus
retain separate advanced server contexts, bootstrap URLs, cookies, navigation,
and process entries. The unified shell and `app` command now exist with one
managed root and shared shell navigation. Guided Position/Historical workflows,
strict optional JSON transfer, readable Results, managed item lifecycles, and
Session browser operations now exist. Canonical `run`, concise Product help, and
grouped advanced help are implemented by Issue #213.

These current commands are the implemented Product and automation instructions.

## Approved launch contract

The approved primary Product entry is the bare command:

```text
skatmind
    launch the unified frontend

skatmind app
    explicitly launch the unified frontend

python -m skatmind
    launch the unified frontend when no arguments are supplied

python main.py
    launch the unified frontend when no arguments are supplied
```

Normal launch must:

1. bind only to `127.0.0.1`;
2. request port `0` and let the operating system select a free port;
3. create or open the managed local data root;
4. start one local application server;
5. open the default browser automatically;
6. remain active as one foreground process until interrupted;
7. shut down cleanly on `Ctrl+C`.

The normal user must not provide `--input`, `--output`, `--workspace`,
`--corpus`, `--port`, `--samples`, `--seed`, a Search method, a Policy, or a
Provenance option.

The explicit advanced application form is:

```text
skatmind app --data-root PATH --port INTEGER --no-open
```

These options must be limited to development, diagnostics, automation, isolated
testing, and explicit advanced local-storage selection. The bare command must
use none of them, and this advanced form must not become the documented normal
user path.

A native desktop launcher, Start Menu shortcut, hosted service, public website,
or domain is not required for the initial v1 boundary. The initial frontend must
add no daemon, system service, tray application, or desktop installer.

## CLI routing and help

The implemented top-level routing contract is:

```text
skatmind
    primary frontend

skatmind app
    explicit frontend launch

skatmind run
    canonical advanced Root JSON automation

skatmind session
    advanced direct Session interface

skatmind capture
    advanced direct Match Capture interface

skatmind corpus
    advanced direct Learning Corpus interface

skatmind --version
    concise version output

skatmind --help
    concise Product-oriented help
```

The direct Root syntax:

```text
skatmind --input ...
```

remains accepted as a Package-1.x compatibility route. It is not the primary
documented user path. The canonical automation form is:

```text
skatmind run --input ...
```

Top-level `skatmind --help` explains that bare `skatmind` opens the
local application, identify the six primary Product areas, identify
`skatmind run` as advanced JSON automation, identify `session`, `capture`, and
`corpus` as advanced direct interfaces, and state where version and licensing
information are available. It does not enumerate every Search, Dataset, Policy,
seed, sample, Profile, and Provenance option.

The complete technical Root options are available at:

```text
skatmind run --help
```

Issue #210 owns bare and explicit frontend launch routing. Issue #213 implements
`skatmind run`, Root compatibility routing, and layered help without changing
Root Product semantics. See
[Advanced CLI automation](advanced_cli_automation_interface.md).

## Application architecture

The unified application architecture is exactly:

```text
one process
one loopback server
one bootstrap flow
one authenticated browser session
one top-level navigation
one managed data root
```

The unified application must reuse the existing transport-free Application,
Session, Match Capture, Learning Corpus, and persistence operations directly. It
must not launch three additional child servers, proxy HTTP requests to the
standalone Capture or Corpus servers, embed separate applications through remote
iframes, communicate through an external network service, or add a second rules,
validation, Search, Settlement, or persistence implementation.

The standalone `skatmind capture` and `skatmind corpus` servers remain supported
advanced interfaces. Their continued support does not permit the unified
application to compose them as nested servers.

The target technology boundary is:

* Python Standard Library local HTTP server;
* server-rendered HTML;
* packaged local CSS;
* packaged local JavaScript only where useful;
* progressive enhancement;
* no external CDN or font;
* no analytics or tracking;
* no Node or frontend build chain;
* no new runtime web-framework dependency unless a later focused Issue finds an
  unavoidable blocker and separately approves that dependency.

Core navigation, item lists, forms, and Result display must remain usable
without a complex client-side application framework.

## Navigation and Home

Every page must present this exact route, label, and order:

```text
/
    Home

/analyze
    Analyze one decision

/review
    Review one completed game

/sessions
    Record one game

/matches
    Record a 36-game Match

/learning
    Learn across Matches

/about
    About SkatMind
```

Internal Root workflow identifiers must not be primary navigation labels.

The Home dashboard presents these exact groups and tasks:

```text
Record games
    Record a complete 36-game Match
    Record or continue one individual game

Analyze and review
    Analyze one decision
    Review one completed individual game

Learn across Matches
    Explore patterns across recorded Matches

Product information
    About SkatMind
```

Each compact Home task states its purpose, unit, and timing, with required
information, storage, use case, and Result in a native closed disclosure. The
scope guide distinguishes one Decision, one resumable Game, one completed Game,
one complete 36-position Match, and multiple Matches. Home must not begin with a
JSON-file selector. See
[Bilingual Home information architecture](bilingual_home_information_architecture.md).

## Plain-language Product concepts

Normal Product presentation must use these frozen definitions.

### Position analysis

> Enter the information visible now, or reconstruct one retrospective decision,
> and receive a bounded Card recommendation with alternatives and limitations.

### Completed-game review

> Enter or import a played game and review recorded decisions using only the
> information available at each decision.

### Session

> A resumable record of one Skat game entered step by step, either while it is
> being played or afterward.

### Match capture

> A private local record of one fixed three-player EuroSkat 36-game Match.

### Learning Corpus

The normal navigation label is `Learn across Matches`.
Explanatory text may retain the technical term Learning Corpus and must define
it as:

> A private local collection of selected Match snapshots and analysis evidence
> used for cross-game summaries, Coaching evidence, and future opponent learning.

### Provenance

> Technical evidence describing where Result fields came from and when their
> information was allowed to be used.

Normal users must not need to enable or understand Provenance to use SkatMind.

## Managed local data

Normal managed storage roots are frozen as:

```text
Windows:
    %LOCALAPPDATA%\SkatMind

Ubuntu:
    ${XDG_DATA_HOME:-$HOME/.local/share}/skatmind
```

Managed categories are exactly:

```text
sessions
matches
corpora
```

The frontend must create missing managed directories. Normal Create, Open, and
Resume actions must use managed items selected by display name and state, not by
a typed filesystem path. Implementation paths and filenames must remain internal
and must not appear in normal browser state or errors. An explicit About/Storage
action may reveal the managed storage location. Advanced launch may override the
root with `--data-root`.

The managed home is an ownership and discovery layer over existing persistence
contracts. It must not define a new Session, Match Workspace, or Learning Corpus
persistence format. Existing strict reconstruction, fingerprints, immutable
objects, optimistic compare-and-swap, atomic replacement, and conflict behavior
remain authoritative.

No cloud, synchronization, database, remote account, collaborative editing,
distributed lock, encryption, automatic backup, or destructive repair behavior
is implied. Concurrent changes must surface as explicit conflicts and must never
silently overwrite persisted data.

## Data actions

The user-facing actions have these exact meanings:

```text
Create:
    create a new managed local item

Open:
    open an existing managed local item

Resume:
    continue an existing valid persisted item

Import:
    copy and validate an external supported document through a browser file
    upload

Export:
    download an exact supported JSON document through the browser
```

Normal use must require no typed server path. Browser uploads must ignore caller
filenames as authority and strictly validate imported data. Import must never
silently overwrite an item. Invalid or incompatible persisted data must be
reported without destructive repair. Exports must use browser downloads.

JSON remains available for portability and automation. Hand-editing JSON must
not be required for normal operation.

## Guided workflows and settings

Normal analysis and review must use guided forms and Card selectors. The
frontend must construct existing canonical `RequestDocumentV1` values, Session
Commands, Match operations, Corpus operations, and existing Application options.
Validation must occur before execution, with field-local messages where
possible.

Raw JSON must be available only through explicit:

```text
Import JSON
Export JSON
Advanced automation
```

Normal forms must use existing canonical omitted/default Product behavior and
show only settings needed to describe the user's situation. Frontend translation
must not select new Product defaults, change game rules, or introduce new
analysis semantics.

Advanced Settings must be initially collapsed and grouped exactly as:

```text
Analysis method

Runtime and reproducibility

Opponent behavior

Simulation and comparison

Technical evidence

Dataset and evaluation
```

Applicable Advanced Settings include samples, random seeds, Search method,
Search budget, Multi-Step count, local Card Policy, opponent Policies, Profile
presets, Provenance, Dataset partitions, and evaluation limits. Every setting
must explain what it changes, its existing default, when it is useful, whether
it affects runtime, whether it affects reproducibility, and whether it changes
evidence scope rather than game rules.

## Result presentation

The browser must present human-readable Results before raw JSON and use these
exact sections:

```text
Summary
Recommendation
Alternatives
Evidence and limits
Technical details
```

Summary must appear first. Recommendation must identify the selected Card or an
explicit unavailability. Alternatives must explain relevant Candidate
comparisons. Evidence and limits must explain method, coverage, boundedness,
uncertainty, and information cutoff. Technical details must be collapsed by
default. An exact JSON download must remain available; using it is optional.

Normal `unavailable`, `partial`, and `timeout` Results must remain distinct from
errors. Observed Cards must not be presented as ground truth, and Search must not
be presented as perfect play. Private Search Worlds, hidden ownership, tokens,
paths, persistence values, and internal fingerprints must remain hidden.

Analysis Results must remain process-local unless explicitly exported or
retained under an existing supported Product contract. The frontend must not add
implicit Result persistence.

## Session, Match, and Corpus relationships

The exact relationship is:

```text
Session:
    one resumable game

Match capture:
    one fixed 36-game Match containing individual game records

Learning Corpus:
    selected immutable Match snapshots and related evidence for cross-game use
```

The frontend must explain that a Session and a Match Workspace are different
persisted objects. A Match Workspace is the persisted, revisioned 36-position
record edited by Match Capture. Match Capture can produce Workspace evidence,
and Learning Corpus imports Match Workspaces as immutable Snapshots. A retained
Snapshot remains immutable whether or not it is Current; Current Snapshot means
the explicitly selected Snapshot for that logical Match. Current selection must
remain explicit. Preparation must remain explicit. Downloads must not rebuild
analysis. Human, Strategy, Tactical, and Coaching evidence must remain separate.

The frontend must not invent or imply automatic Session-to-Match conversion,
automatic Match-to-Corpus analysis, automatic Current selection, automatic
preparation, or automatic Report capture. Existing explicit transfer,
selection, preparation, and retention contracts remain authoritative.

## About SkatMind

`/about` must display:

* Product name;
* installed Package version;
* `AGPL-3.0-only`;
* `Copyright (C) 2026 Henning Wiese`;
* a local-only execution statement;
* the supported Python `>=3.13` and certified v1 CPython 3.13 runtime boundary;
* the managed-storage explanation;
* a no-cloud and no-remote-service statement;
* link names for the current local README, installed CLI, Public Python API, and
  unified frontend contract documentation;
* the availability of the advanced CLI and Public Python API.

The installed version must be visible without `--version`. An About or Storage
action may reveal the managed storage location. About must not imply a hosted
service, Package-index publication, or external documentation request.

## Security and privacy

The unified application must preserve or strengthen the existing private local
browser boundary. It must:

* bind only to `127.0.0.1`;
* use port `0` by default;
* use one unguessable bootstrap token;
* exchange the token for one `HttpOnly; SameSite=Strict` application cookie;
* redirect to a clean token-free URL;
* validate Host;
* validate mutation Origin;
* reject duplicate security-sensitive headers;
* use restrictive CSP;
* use `nosniff`;
* deny framing;
* use no CORS;
* use no external resources;
* perform no external runtime request;
* emit no access log;
* enforce request-size limits;
* use generic internal errors;
* expose no private path or token in ordinary page content.

The unified app and both standalone local browser surfaces use
`Referrer-Policy: origin`. The former `no-referrer` policy conflicted with the
strict mutation boundary because Fetch serializes the Origin header as `null`
for a non-CORS request whose method is neither GET nor HEAD under that policy.
The `origin` policy preserves the concrete request Origin while limiting Referer
information to scheme, host, and port, without source path or query. Mutation
authorization still requires exactly one concrete HTTP loopback Origin whose
hostname and port match the sole Host. Missing, `null`, duplicate, malformed,
external, credential-bearing, path-bearing, query-bearing, fragment-bearing,
wrong-port, and Host-mismatched Origins remain rejected. Referer and
`Sec-Fetch-Site` are not authorization inputs.

After successful automatic browser opening, stdout should contain only a concise
local-running and shutdown message. A token-bearing fallback URL may be printed
only when browser opening fails or `--no-open` is explicitly used.

The existing private-data, origin, token, cookie, Host, CSP, and information-use
boundaries must not be weakened. This is a private local transport boundary, not
an account, encryption, authenticated-authorship, secure-storage, remote-
deployment, or multi-user authorization claim.

## Accessibility and progressive enhancement

The target minimum is exactly:

* semantic headings and landmarks;
* explicit form labels;
* keyboard-operable navigation and controls;
* visible focus;
* error summaries plus field-local messages;
* status not communicated by color alone;
* readable mobile and desktop layout;
* no-JavaScript support for navigation, item lists, normal forms, and downloads
  where the underlying operation permits it;
* JavaScript may enhance Card selection, previews, and progressive disclosure;
* no external accessibility dependency.

## Existing-interface preservation

These interfaces remain supported:

```text
Public Python API:
    skatmind.api.v1

Advanced CLI:
    canonical skatmind run Root JSON execution

Direct Root compatibility:
    existing option-like Root execution

Direct Session CLI:
    skatmind session

Direct Match Capture:
    skatmind capture

Direct Learning Corpus:
    skatmind corpus
```

The frontend is an additional local Product surface. It must not become an
eighth Root workflow, replacement Public Python API, new public Dataset API,
remote server, or Package-index publication.

## Future implementation ownership

The implementation sequence is frozen exactly as follows. Issue #209 creates
none of these GitHub Issues.

### Issue #210

```text
Add the unified local SkatMind application shell and managed data home
```

Issue #210 owns bare and explicit frontend launch, one local server, the
security context, packaged app assets, the managed data root, Home, navigation,
About, and placeholder states for later Product areas.

### Issue #211

```text
Add guided position analysis, completed-game review, and Result presentation
```

Issue #211 owns guided analysis and Historical input/import forms, existing
defaults, Advanced Settings, existing Application execution, human-readable
Result views, and optional JSON import/export.

### Issue #212

```text
Integrate Session, Match Capture, and Learning Corpus into the unified
frontend
```

Issue #212 owns and now implements managed Create/Open/Resume, the Session browser flow, Match
Workspace and Corpus lifecycles, plain-language concepts, direct reuse of
existing operations, and removal of required normal-user paths and ports.

### Issue #213

```text
Reframe the CLI as the advanced automation interface
```

Issue #213 owns concise top-level help, canonical `skatmind run`, preservation
of direct Root compatibility syntax, task-oriented examples, plain-language
advanced documentation, and frontend/automation separation.

The exact finding ownership is:

```text
UAT-FINDING-001:
    primary remediation across Issues #210, #211, and #212

UAT-FINDING-002:
    primary remediation in Issue #213

UAT-FINDING-003:
    primary remediation in Issue #212
```

Issues #210 through #213 implement their assigned shell, guided-workflow,
managed-stateful, and advanced-automation slices. See
[Unified local frontend application shell](unified_local_frontend_application_shell.md)
and [Guided analysis and Results](unified_local_frontend_guided_analysis_and_results.md),
and [Managed stateful workflows](unified_local_frontend_stateful_workflows.md)
and [Advanced CLI automation](advanced_cli_automation_interface.md) for the
implemented boundaries.
The later profile-driven creation implementation is documented separately in
[Profile-driven stateful creation](profile_driven_stateful_creation.md).

## UAT repetition and Release state

Repeated UAT-01 after Issue #213 exposed UAT-FINDING-004. Issue #214 implemented
the browser-Origin policy remediation. Maintainer Microsoft Edge verification
subsequently resolved Issue #214 and UAT-FINDING-004. Repeated UAT-01
nevertheless failed.

The current Release-process state is:

```text
Issue #208:
    open

Repeated UAT-01:
    failed

UAT-02 through UAT-12:
    paused

B-09:
    open

B-07:
    open

B-06:
    closed

UAT-FINDING-004:
    resolved

Issue #214:
    resolved

Package 1.0.0:
    not ready

Release preparation:
    not ready
```

Issue #215 freezes the authoritative
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md)
without changing the completed 53-row technical ledger. Issue #216 implements
its private profile/localization and bilingual common-shell foundation while
full workflow translation remains incomplete, and its Ubuntu follow-up passed.
Issue #217 implements the grouped bilingual Home and Product-concept slice, and
Issue #218 implements registered contextual validation with safe submitted-value,
workflow-context, Result, wizard-step, and language-switch preservation.
Issue #219 implements private known Players, generated identities, local
defaults/display labels, and friendly bilingual Session/Match/Learning creation.
UAT-FINDING-001 is further partially remediated and open; UAT-FINDING-003 has its
Home/concept remediation implemented and remains open pending Issue #220 and
repeated UAT-01; UAT-FINDING-007 has its profile/default/creation scope
implemented and remains open pending Issue #220; and UAT-FINDING-008 has
bilingual Home/concept/creation coverage and remains open pending Issue #220. UAT-FINDING-006 has
its Issue #218 implementation complete and remains open pending repeated UAT-01.
The creation-form scope of UAT-FINDING-005 is implemented but remains open for
relevant Issue-#220 views and repeated UAT-01. Issue #220 is the exact next action.

UAT-02 through UAT-12 remain paused. Frontend work remains part of B-09 outside
the technical ledger and must not reopen B-06. B-07 remains open.

The completed technical required-row ledger remains:

```text
19 satisfied
34 satisfied_with_approved_bounded_scope
0 evidence_required
0 implementation_required
0 product_decision_required
53 total
```

B-06 remains closed by Issue #207. Frontend remediation belongs to B-09 outside
the 53-row ledger and must not reopen B-06 or reclassify a completed row. B-07
must remain open, Package `1.0.0` must remain unprepared, and Release preparation
must remain not ready.

## Issue #209 historical non-goals and current accepted limitations

Issue #209 must not implement launch routing, `app`, `run`, a server, routes,
assets, managed storage, forms, Result views, CLI help, Session browser
operations, Match integration, Corpus integration, or Product defaults. It must
not change Product behavior, public or private contracts, persistence, security,
dependencies, Package Resources, Package metadata, Schemas, examples, tests,
benchmarks, scripts, CI, generated scenarios, generated outputs, Package version,
Changelog, license files, or Release metadata. In particular, it must not modify
`src/`, `tests/`, `schemas/`, `examples/`, `benchmarks/`, `scripts/`, `.github/`,
browser assets, `pyproject.toml`, `LICENSE`, `COPYRIGHT`, `CHANGELOG.md`, or
generated outputs.

The approved target remains a foreground private loopback browser application.
It makes no desktop, hosted, cloud, sync, database, backup, remote-account,
collaboration, encryption, complete-solver, perfect-play, or ground-truth claim.
Four-player table support remains unconditionally out of scope. Other Product
limitations remain governed by `docs/v1_scope.md` and the completed technical
traceability ledger.
