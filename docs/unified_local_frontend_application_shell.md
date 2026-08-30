# Unified local frontend application shell

## Status

Issue #210 implements the first executable slice of the
[unified local frontend contract](unified_local_frontend_contract.md). The shell
is private Package behavior, not a Public API or an eighth Root workflow.

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
corpus            -> existing Corpus CLI
capture           -> existing Capture CLI
session           -> existing Session CLI
all other argv    -> existing Root CLI
```

`--version`, current technical Root `--help`, and direct `--input` options remain
unchanged. `skatmind run` and final top-level help remain Issue #213 work.

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

| Route | Label | Issue #210 state |
| --- | --- | --- |
| `/` | Home | Complete shell dashboard |
| `/analyze` | Analyze a position | HTTP-200 placeholder until Issue #211 |
| `/review` | Review a completed game | HTTP-200 placeholder until Issue #211 |
| `/sessions` | Sessions | HTTP-200 placeholder until Issue #212 |
| `/matches` | Match capture | HTTP-200 placeholder until Issue #212 |
| `/learning` | Learning & cross-game insights | HTTP-200 placeholder until Issue #212 |
| `/about` | About SkatMind | Complete shell page |

`/assets/app.css` is the only current app asset route. Unknown routes return
`404`; unsupported methods on known routes return `405`. There is no Product
operation endpoint.

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
requests. Mutation attempts additionally require one exact same-origin `Origin`.
Body requests reject duplicate or missing length/type headers, transfer encoding,
unsupported content types, short bodies, and bodies over 1 MiB. Token comparison
is constant-time.

All responses apply `no-store`, `nosniff`, `no-referrer`, frame denial,
restrictive Content Security Policy, and restrictive Permissions Policy headers.
The server emits no CORS or access log and loads no external resource.

## Rendering and accessibility

Pages are deterministic escaped server-rendered HTML with packaged local CSS.
No JavaScript is required or currently shipped for the app. Every page has a skip
link, semantic header/navigation/main/footer landmarks, one visible `h1`, current-
page indication, keyboard operation, visible focus, text status independent of
color, and responsive layouts. Home, navigation, About, placeholders, errors,
and the storage disclosure work without JavaScript. No raw user HTML is rendered.

## Boundaries

Opening the app only resolves and prepares storage, creates one context and
server, optionally opens a browser, and serves shell pages. It does not execute
Application workflows; create or load Sessions, Match Workspaces, or Corpora; run
Search; build Datasets; prepare Learning artifacts; persist Results; generate
Product IDs; or scan managed contents.

Guided analysis, completed-game Review, and Result presentation remain Issue #211
placeholders. Session, Match, and Learning item listing and lifecycles remain
Issue #212 placeholders. JSON import/export, Advanced Settings, `skatmind run`,
and final top-level help are not implemented by Issue #210.

Standalone `session`, `capture`, and `corpus` commands remain supported and
unchanged. The seven Root workflows, Public Python API, Schemas, persistence
formats, six Session examples, 98 generated outputs, and ten private Corpus
downloads remain unchanged.

## UAT and next action

Issue #210 partially remediates `UAT-FINDING-001` by adding the actual local
application shell, but the finding remains open. `UAT-FINDING-002` and
`UAT-FINDING-003` remain open. UAT-01 remains failed; it is not repeated.
UAT-02 through UAT-12 remain paused. B-09 and B-07 remain open, B-06 remains
closed, and the completed 53-row technical ledger is unchanged.

Issue #211, **Add guided position analysis, completed-game review, and Result
presentation**, is the exact next implementation action.
