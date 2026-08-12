# Local Match Capture interface

Issue #165 adds the first usable no-JSON interface for manually capturing one
EuroSkat 36er Standard Match. It is a private local browser transport over the
existing Match, observed-Game, Workspace persistence, and Match Capture
Application services.

## Startup

Start one server for one explicit Workspace file:

```powershell
skat-ai capture --workspace MATCH.json
python -m skat_ai capture --workspace MATCH.json
python main.py capture --workspace MATCH.json
```

`--workspace` is required. `--port` defaults to `0`, which asks the operating
system for a free local port; explicit ports range from `1` through `65535`.
`--no-open` suppresses automatic browser opening. There is no default path,
directory, host, remote-binding, force, authentication-disable, daemon, or
output-file option.

The Workspace parent directory must already exist. An existing file is strictly
loaded and resumed before the server starts. Invalid existing files are rejected
and never overwritten. An absent file remains absent until the browser creation
form is accepted.

## Workspace creation and Resume

The creation form captures Match identity, title, game platform, external Match
ID, played time, descriptive source metadata and media bounds, three stable
Players, labels and platform IDs, and one Perspective Player. Form rows map to
`place_1`, `place_2`, and `place_3`; the Tournament Format is fixed to
`euroskat_36_standard_v1`. Initial Player Statistics Snapshots are absent and can
be added after creation.

Creation builds one revision-zero 36-Slot Workspace and atomically saves it. If
another process creates the target first, the browser reports a persistence
conflict and retains its absent context. It does not overwrite or reload
silently.

After creation or strict Resume, the interface shows the Match and source
summary, Players and Perspective, Workspace revision and Progress, and all 36
positions grouped into twelve three-position rounds. Empty, setup, in-progress,
complete-trace, and passed positions use text and border treatment rather than
color alone. The first empty position is marked explicitly.

## Metadata correction

The focused metadata form can correct only fields already supported by
`replace_match_workspace_definition_v1()`:

* title, game platform, external Match ID, and played time;
* source kind, URL, title, channel, and Match media bounds;
* Player labels and platform Player IDs.

Match ID, Tournament Format, stable Player IDs, table places, Perspective, and
loaded Statistics observations remain retained. Platform-ID and Match-time edits
leave the Snapshot unchanged. A changed non-null Player label immutably
reconciles the retained record label under the deterministic ID for that same
metadata revision. Equal content is reported as no change and does not write the
file. Existing nested timecodes are revalidated by the Workspace operation.

Changing `played_at` also recomputes every Player Statistics temporal Context and
the Match-wide Preparation in the returned browser state. It does not mutate a
Snapshot and does not add a second revision.

## Player Statistics

Issue #166 appends `set_player_statistics_snapshot` and
`clear_player_statistics_snapshot` after the original 17 Web operations while
keeping Web Protocol version `1`. Each of the three participant cards supports
Add, Replace, and confirmed Clear through ordinary HTML forms.

The editor captures an optional Snapshot ID, one shared observed/captured RFC
3339 instant, manual-entry or online-platform source details, Games played, all
eight percentages, and either no exact Counts or the complete eight-Count set.
The server derives Player ID and label from the selected participant and builds
one exact existing Opponent Statistics record through its authoritative parser.
It never corrects a submitted value or contacts a platform.

Loaded historical-aggregation Snapshots retain and display their complete source
read-only. They can be cleared or replaced with a new manual or online Snapshot;
there is no partial historical provenance editor.

Every retained Snapshot displays temporal status, eligibility, normalized
Profile, scoped Confidence, Classification, derivation status, recommended and
actionable presets, and explanations from the existing Profile derivation. Only
`source.captured_at < match.played_at` is eligible. Missing Match time, equal
instants including different offsets, and later captures remain descriptive.
Prepared Profiles are not applied to Match analysis.

## Timecodes

Browser timecode fields accept `SS`, `MM:SS`, or `HH:MM:SS`, optionally followed
by exactly three millisecond digits such as `.500`. Blank means unknown. Values
with surrounding whitespace, negative values, or minute/second components above
59 are rejected. Only exact non-negative millisecond values in
`MediaTimecodeV1` are persisted; presentation strings are not stored.

## Current position

The selected-position page shows its Match position and round, Dealer and
historical seats, Slot and capture state, Game ID, Declarer, next Player, current
Trick, completed Tricks, per-Player and total Play counts, Evidence Summary,
Card-selection scope, record blockers, and Workspace Progress.

Slot actions start a Game with the existing deterministic ID by default, mark a
Passed Deal without a synthetic Game, replace an observed Game with an explicit
Passed Deal, or clear a position after browser confirmation. Rotation,
Perspective, Game seats, and the next Player are always derived by existing
services.

## Setup

Server-rendered forms cover:

* optional Game start and end timecodes;
* unknown or exact ten-Card Perspective hand evidence;
* Declarer, Game Type, Hand, Ouvert, announcements, optional Matadors, and bid;
* unknown or exact two-Card original Skat evidence;
* unknown, known-empty Hand, or exact two-Card Discard evidence.

The setup forms render canonical local Card selectors. The server sends selected
Card codes to the existing Capture Application functions. It does not duplicate
Declaration, Card reconciliation, ownership, trace, or timecode rules and never
infers a hidden Card.

## Card entry and correction

The 32-Card play palette uses canonical deck order and displays Card code plus a
readable suit/rank label. Already played, proven unavailable, or otherwise
non-selectable Cards are disabled from the authoritative Position View. The
scope is labeled exactly as either:

```text
Exact legal cards
Observed-card candidates; ownership may be unknown
```

The bounded palette is not an ownership or legality assertion. One Card button
appends one Play. The Card-code input accepts one code or an atomic whitespace-
or comma-separated batch. An optional Decision timecode is available for a
single Card. Player and one-based Decision index are never accepted from the
browser; existing services derive both.

Play history is chronological and grouped by Decision and Trick facts. Undo last
Play is one explicit truncation to the previous count. Another form truncates to
any selected retained count. The returned authoritative Workspace removes
invalid dependent Commentary and Response Links, and the saved result notice
lists their IDs. There is no second Undo history or branch model.

Local JavaScript adds focus retention, `/` focus for rapid Card entry,
`Alt+U` Undo, and `Alt+Left`/`Alt+Right` position navigation. It contains no Skat
rules, Player-order or Decision-index derivation, Card legality, or Workspace
construction. Core creation, setup, Card, correction, Commentary, Passed Deal,
clear, and Reload operations work through ordinary HTML forms without
JavaScript. Successful forms use POST/Redirect/GET and retain the selected
position. Progressive enhancement follows that authoritative response, replaces
the rendered page fragment, and enhances position navigation; ordinary form
submission remains the no-JavaScript fallback. Player Statistics forms use the
same server-authoritative fallback.

## Commentary and Response Links

Commentary can reference any retained Decision, including either opponent's
Play. The subject Player is derived from that Decision. A commentator may be a
Match Player, an external name, or both. Multiline original text and an optional
timecode are retained. Existing Commentary can be edited or removed; removal
also removes dependent Response Links after confirmation.

Each Commentary item offers only later retained Decisions for Response Links.
Links can be added, replaced by their retained ID, or removed. They remain
caller-authored associations and make no causality, correctness, tactical,
signal, quality, sentiment, error, or optimality claim.

## Autosave and conflicts

Every applied browser mutation is serialized through one context lock and:

1. carries the exact expected Workspace revision;
2. invokes one existing Match or Capture operation;
3. receives one returned immutable Workspace;
4. builds at most one persistence document;
5. performs one Save with the retained content fingerprint;
6. replaces context only after persisted `saved` or equivalent `unchanged` file
   content;
7. renders the persisted state.

An unchanged operation and a Workspace revision conflict perform no Save. A
persistence conflict returns HTTP `409`, leaves the old context untouched, and
shows an explicit `Reload Workspace from disk` action. Reload strictly reads the
same fixed file. No retry, merge, force overwrite, hidden Reload, default path,
backup, or distributed lock is provided.

## Local security

The Standard Library `ThreadingHTTPServer` binds only to `127.0.0.1`. Startup
creates one cryptographically random token. The initial token URL establishes an
`HttpOnly`, `SameSite=Strict` cookie and redirects to a token-free URL. Further
requests require the cookie; mutations also require an exact local same-origin
`Origin`. Unexpected `Host` values are rejected.

The server emits no permissive CORS header, disables default request logging,
caps request bodies at 1 MiB, rejects transfer encoding and path traversal,
serves only the allowlisted packaged HTML/CSS/JavaScript resources, and emits
`no-store`, `nosniff`, no-referrer, frame-denial, restrictive Content Security
Policy, and restrictive Permissions Policy headers. It makes no external
network request.

These controls protect the accidental local transport surface; they are not an
account system, encryption, secure storage, authenticated authorship, remote
deployment, cloud protection, or access-control claim.

## Source links and private data

A retained source URL appears only as an explicit user-clicked link with
`target="_blank"` and `rel="noopener noreferrer"`. The interface does not embed
video, fetch metadata or thumbnails, call an API, download content, scrape a
website, or contact YouTube, EuroSkat, or another source.

The interface is an explicit private transport and may display private values in
the selected Workspace, including Player identifiers, Perspective hand, Skat,
Discards, Plays, Commentary, and Response Links. Protect the Workspace file as
private local data. Browser state and HTML omit absolute paths, fingerprints,
transport tokens, persistence JSON, internal trace structures, stack traces,
Search Worlds, simulation ownership, and Analysis Results.

## Current boundaries

Match Capture Web, Web Protocol, and Capture CLI are independent internal
version-1 contracts. `capture` is a transport command family, not an eighth Root
workflow. Package version remains `0.14.0`; the seven Root workflows, Public
APIs, 63 Schemas, existing examples, and 85 generated-output scenarios are
unchanged.

Version 1 performs no Position or Historical analysis, Search, review, Replay
Coaching, materialization, list/report/Dataset generation, Player Profile
application, YouTube integration, EuroSkat integration, database
persistence, remote serving, cloud synchronization, encryption, or backup.
Public Match API, Match Schema, Match JSON/data CLI workflow, Player Statistics
global history, and downstream Historical/list/report/Dataset materialization
remain future work.
