# Unified local frontend application shell

## Status

Issue #210 implements the first executable slice of the
[unified local frontend contract](unified_local_frontend_contract.md). The shell
is private Package behavior, not a Public API or an eighth Root workflow.
Issue #211 now extends this shell with the separately documented
[guided analysis and Result workflows](unified_local_frontend_guided_analysis_and_results.md).
Issue #212 extends it with
[managed stateful workflows](unified_local_frontend_stateful_workflows.md).
Issue #213 completes the CLI onboarding separation documented in
[Advanced CLI automation](advanced_cli_automation_interface.md).
Issue #216 adds the private profile/localization foundation and bilingual common
shell documented in [Local frontend profile and localization](local_frontend_profile_and_localization.md).

The exact internal contract identities are:

```text
UNIFIED_LOCAL_FRONTEND_CONTRACT_VERSION = 1
LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION = 1
MANAGED_LOCAL_DATA_CONTRACT_VERSION = 1
```

Package version remains `0.17.0`, Python remains `>=3.13`, the license remains
`AGPL-3.0-only`, Public API contract version remains `1`, and the distribution
still installs exactly one `skatmind = skatmind.cli:main` Console Script.

## Launch

These normal entries now open the application shell:

```text
skatmind
skatmind app
python -m skatmind
python -m skatmind app
python main.py
python main.py app
```

The explicit advanced launch syntax is:

```text
skatmind app --data-root PATH --port INTEGER --no-open
```

The default port is `0`, and explicit `0` or a port from `1` through `65535` is
accepted. Normal launch opens the default browser. `--no-open` suppresses that
attempt. Browser-opening failure does not stop the server. Successful browser
opening prints only non-secret running and shutdown text; failure or `--no-open`
prints one usable bootstrap URL.

Leading dispatch is now:

```text
empty argv        -> app
app               -> app
run               -> canonical Root JSON automation
session           -> existing Session CLI
capture           -> existing Capture CLI
corpus            -> existing Corpus CLI
-h or --help      -> concise Product help
--version         -> Product version
other option      -> direct Root compatibility
other command     -> top-level usage error
```

`skatmind run --help` owns the grouped technical Root interface. Direct Root
options remain unchanged Package-1.x compatibility routes without warnings.

## Managed local data

The normal managed roots are exactly:

```text
Windows:
    %LOCALAPPDATA%\SkatMind

Linux:
    ${XDG_DATA_HOME:-$HOME/.local/share}/skatmind
```

The root contains exactly these managed categories:

```text
sessions
matches
corpora
```

Startup creates missing directories idempotently and rejects a file collision at
the root or any category. It creates no manifest, database, identifier,
persistence document, sample data, Session, Workspace, Corpus, or Product Result.
It does not enumerate or parse managed contents. `--data-root` is the one advanced
override.

Private `Path` values stay in the process-local context. The immutable browser-
safe state contains no path, port, token, cookie, environment value, user or
machine name, Product document, Card, fingerprint, or timestamp. The managed
root is passed separately only to render the closed About storage disclosure.

## Server and routes

The shell uses one Standard Library `ThreadingHTTPServer`, one context, one
cryptographically random bootstrap token, and one authenticated browser session.
It binds only to `127.0.0.1` and does not start, proxy, or iframe the standalone
Capture or Corpus servers.

The exact route and navigation order is:

| Route | Label | Current state |
| --- | --- | --- |
| `/` | Home | Complete shell dashboard |
| `/analyze` | Analyze a position | Usable process-local guided workflow |
| `/review` | Review a completed game | Usable process-local guided workflow |
| `/sessions` | Sessions | Managed listing, lifecycle, entry, and execution |
| `/matches` | Match capture | Managed listing and existing Capture workflow |
| `/learning` | Learning & cross-game insights | Managed Corpus lifecycle and workflow |
| `/about` | About SkatMind | Complete shell page |

`/assets/app.css` remains the shell asset. Existing Capture and Corpus CSS/JS are
also served from authenticated namespaced Package routes. Authenticated private
action and download routes for Analyze and Review are documented in
[Guided analysis and Results](unified_local_frontend_guided_analysis_and_results.md).
Unknown routes return `404`; unsupported methods on known routes return `405`.
The routes are private browser transport, not a public JSON API.

The Home dashboard contains the exact ordered tasks:

```text
Analyze a position
Review a completed game
Create or resume a Session
Capture a 36-game Match
Open Learning & cross-game insights
About SkatMind
```

Each task states what it does, required information, storage behavior, Live or
Retrospective status, expected Result, and current availability. Home states that
SkatMind runs locally and stores no cloud data. It exposes no JSON, path, port,
token, seed, sample, Search, Policy, Dataset, or Provenance controls.

## About

About shows Product and Package identity, `AGPL-3.0-only`, the 2026 copyright
notice, current Python runtime, Python `>=3.13`, the certified CPython 3.13
boundary, local-only/no-cloud operation, managed-storage behavior, advanced CLI
and Public Python API availability, and local documentation names. The escaped
storage root appears only inside one closed explicit disclosure. The page makes
no external documentation request.

## Security

The bootstrap token is accepted only as the sole query parameter on `/`. A valid
bootstrap request sets the distinct `skatmind_app_token` cookie with
`HttpOnly; SameSite=Strict; Path=/` and redirects to clean `/`. Capture and Corpus
cookies cannot authenticate the app, and the app cookie cannot authenticate
either standalone server.

The server validates exact Host and cookie header cardinality for authenticated
requests. Mutation attempts additionally require one concrete HTTP loopback
`Origin` whose hostname and port exactly match Host. Missing, `null`, duplicate,
malformed, external, credential-bearing, path/query/fragment-bearing,
wrong-port, and Host-mismatched Origins remain rejected. Referer and
`Sec-Fetch-Site` are not authorization fallbacks.
Body requests reject duplicate or missing length/type headers, transfer encoding,
unsupported content types, short bodies, and oversized bodies. Multipart framing
has a bounded allowance above the exact 1 MiB guided JSON file limit. Managed
Session/Match JSON content and existing Corpus operations retain their separate
16 MiB boundaries. Token comparison is constant-time.

All responses apply `no-store`, `nosniff`, `Referrer-Policy: origin`, frame
denial, restrictive Content Security Policy, and restrictive Permissions Policy
headers. The former `no-referrer` policy caused non-CORS browser POSTs to carry
`Origin: null` under Fetch and therefore conflicted with the strict validator.
`origin` preserves the concrete request Origin while any Referer contains only
scheme, host, and port, not path or query. The same policy applies to standalone
Match Capture and Learning Corpus. The server emits no CORS or access log and
loads no external resource. Unified-app authorization failures use one
deterministic HTML 403 page with no failed-check detail, request value, private
value, Product data, or external asset; parser-level failures retain their
minimal hardened response.

## Rendering and accessibility

Pages are deterministic escaped server-rendered HTML with packaged local CSS.
No JavaScript is required for shell navigation or managed lifecycle forms.
Existing packaged Capture and Corpus JavaScript remains progressive enhancement.
Every page has a skip link, semantic header/navigation/main/footer landmarks, one visible `h1`, current-
page indication, keyboard operation, visible focus, text status independent of
color, and responsive layouts. Home, navigation, About, guided forms, field-linked
errors, Result tables, downloads, managed lists, and the storage disclosure work
without JavaScript. No raw user HTML is rendered.

## Boundaries

Opening the app resolves and prepares storage, creates one context and server,
and optionally opens a browser. Explicit Analyze and Review Run actions can now
execute existing Position or Historical Application workflows exactly once.
They retain drafts and Results only in process memory. Explicit managed pages can
now discover direct children, create/open/reload Sessions, Match Workspaces, and
Corpora, reuse existing mutations and analyses, prepare existing process-local
Learning artifacts, and provide canonical downloads. No Result or derived
Learning artifact gains new persistence. Discovery is explicit and bounded.

Canonical `skatmind run` and concise top-level Product help are implemented.

Standalone `session`, `capture`, and `corpus` commands remain supported and
unchanged. The seven Root workflows, Public Python API, Schemas, persistence
formats, six Session examples, 98 generated outputs, and ten private Corpus
downloads remain unchanged.

## UAT and next action

Issues #210 through #213 implement the current shell, guided workflows, managed
stateful workflows, and advanced CLI onboarding. Repeated UAT-01 exposed
UAT-FINDING-004, and Issue #214 implemented its Origin-policy remediation.
Maintainer Microsoft Edge verification resolved Issue #214 and
UAT-FINDING-004. Repeated UAT-01 nevertheless failed.

Issue #208 remains open; UAT-02 through UAT-12 remain paused; B-09 and B-07
remain open; B-06 remains closed; and Package `1.0.0` and Release preparation
are not ready. Issue #215 freezes the authoritative
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
Issue #216 implements its private profile, locale, catalog, language-selector,
and bilingual common-shell subset without translating all workflow bodies. The
reopened Issue #216 follow-up remains pending both required Ubuntu jobs; Issue
#217 is blocked until they pass.
