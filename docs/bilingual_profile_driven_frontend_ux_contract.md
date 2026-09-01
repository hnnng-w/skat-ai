# Bilingual profile-driven frontend UX contract

## Authority and status

This document is the authoritative Product and architecture contract for the
remaining v1 unified-frontend UX remediation frozen by Issue #215. Issue #216
implements its private profile/localization and common-shell foundation. Issues
#217 through #220 retain the remaining information-architecture, validation,
profile-driven form, task-first, and complete-translation ownership.

This document must keep three states distinct:

```text
Current behavior:
    the bilingual common-shell and private-profile foundation implemented
    through Issue #216, with explicitly marked English workflow bodies

Approved target contract:
    the future behavior frozen by Issue #215 in this document

Future implementation ownership:
    the focused implementation sequence in Issues #216 through #220
```

Issue #215 is documentation-only. Issue #216 implements only its assigned subset
without changing Product semantics, CLI/API/JSON/Schema behavior, Package
version, examples, generated outputs, or the future ownership of Issues #217
through #220. The exact implementation is documented in
[Local frontend profile and localization](local_frontend_profile_and_localization.md).

The implemented version-1 launch and frontend boundary remains authoritative in
[Unified local frontend contract](unified_local_frontend_contract.md). This
document is authoritative where it defines the future UX remediation beyond
that current implementation.

## UAT source and finding inventory

Issue #208 remains the open maintainer v1.0.0 user-acceptance-test umbrella.
The first UAT-01 attempt failed user acceptance. Issues #209 through #213 added
the unified frontend, guided Analyze and Review workflows, managed Session,
Match, and Learning workflows, concise Product-oriented CLI onboarding, and
canonical advanced `skatmind run` automation.

Repeated UAT-01 then exposed `UAT-FINDING-004`. Issue #214 corrected the browser
Origin-policy interaction, and maintainer Microsoft Edge verification resolved
Issue #214 and that finding. Repeated UAT-01 nevertheless failed because the
remaining Product UX was not acceptable.

The current finding inventory is:

```text
UAT-FINDING-001:
    A primary frontend exists, but normal stateful Product workflows are not yet
    acceptable.
    Severity: blocker
    Status: further partially remediated by Issue #216, open

UAT-FINDING-002:
    CLI onboarding was an unstructured expert interface.
    Status: resolved by Issue #213

UAT-FINDING-003:
    Session, Match, Review, and Learning are not sufficiently distinguished.
    Severity: major
    Status: open

UAT-FINDING-004:
    Valid browser form submissions were rejected as Forbidden.
    Status: resolved by Issue #214

UAT-FINDING-005:
    Normal forms expose internal identifiers, enums, timestamps, and technical
    metadata.
    Severity: major
    Status: open

UAT-FINDING-006:
    Validation failures can discard entered values and break the current
    workflow.
    Severity: major
    Status: open

UAT-FINDING-007:
    Stateful workflows expose too many fields and advanced concepts before the
    next normal Skat task is clear.
    Severity: major
    Status: foundation implemented by Issue #216, open

UAT-FINDING-008:
    Complete German and English workflow coverage is unavailable.
    Severity: major
    Status: foundation and common coverage implemented by Issue #216, open
    pending Issue #220
```

Issue #216 further partially remediates UAT-FINDING-001, implements the
foundation for UAT-FINDING-007, and implements foundation/common coverage for
UAT-FINDING-008. All remain open pending the assigned follow-up work and repeated
UAT.

## Maintainer decisions

The technical implementation language and repository documentation must remain
English. Code, comments, Docstrings, tests, CLI, Public API, JSON, Schemas,
machine identifiers, Routes, Enum values, error codes, persistence contracts,
hashes, and generated outputs must remain English and locale-neutral.

The unified local browser frontend must support German and English. German
translation must apply only to user-visible presentation. It must not translate
or rename technical contracts or change Product behavior.

The frontend must become profile-driven and task-first. Normal users must not
repeatedly provide internal Session, Match, Corpus, Snapshot, or Player IDs; raw
Enum values; RFC 3339 timestamps; protocol versions; Search-family names;
preparation terminology; repeated Player and perspective information; or
technical defaults already known from a local profile.

The frontend must distinguish these exact user units:

```text
one decision
one individual Skat game
one complete 36-position Match
multiple recorded Matches used for cross-game insights
```

Match Capture must be the primary normal recording workflow. Single-game
Session entry must remain available as the secondary recording workflow. JSON
import must remain available but secondary and advanced.

## Contract identity

The private contract versions are frozen as:

```text
BILINGUAL_FRONTEND_CONTRACT_VERSION = 1
FRONTEND_TRANSLATION_CATALOG_VERSION = 1
LOCAL_FRONTEND_PROFILE_VERSION = 1
FRONTEND_INFORMATION_ARCHITECTURE_VERSION = 1
PROFILE_DRIVEN_FORM_DEFAULTS_VERSION = 1
FRONTEND_VALIDATION_PRESERVATION_VERSION = 1
```

Issue #216 implements the first three versions. The information-architecture,
profile-driven-form-default, and validation-preservation versions remain
future-owned and unimplemented. All remain independent from Package version, Public API version, Root
workflows, Session version, Match Workspace version, Corpus version, Schema
versions, Dataset versions, and browser protocol versions.

The exact future private policies are:

```text
technical_contracts_and_machine_values_remain_english
unified_frontend_visible_content_supports_german_and_english
one_private_local_frontend_profile_per_managed_data_root
saved_language_overrides_browser_language
browser_language_bootstraps_only_without_saved_preference
user_facing_names_replace_required_manual_internal_ids
normal_workflows_are_task_first_and_profile_driven
advanced_settings_are_secondary_explicit_and_explained
validation_preserves_safe_values_and_workflow_context
home_separates_record_analyze_learn_and_product_information
language_and_profile_never_change_product_semantics
no_external_translation_profile_sync_or_cloud_service
```

These policies remain internal and must not become Public API exports. Issue
#216 implements exactly the seven-policy subset listed in
[Local frontend profile and localization](local_frontend_profile_and_localization.md);
the other five remain future-owned.

## Current behavior

Package `0.17.0` currently provides a German/English common shell, current flat
Home, About, authorization, and generic common-error presentation. Exact HTML
`lang`, global language selection, saved/browser/fallback resolution, strict
catalogs, and private profile persistence are implemented. Workflow-specific
Analyze, Review, Session, Match, and Learning bodies remain explicitly marked
English when the German shell is selected. Machine Routes and identifiers remain
English and locale-neutral.

Home currently presents one flat task sequence: Analyze, Review, Session,
Match, Learning, and About. It does not provide the approved grouped hierarchy.
Normal stateful creation forms still expose technical identifiers and metadata.
There is no known-Player directory, profile-driven form behavior, grouped Home,
validation-preservation redesign, or complete workflow translation.

The managed data root retains exactly the managed categories `sessions`,
`matches`, and `corpora`. An optional private `frontend-profile.json` is a direct
root child, not a fourth category. Startup creates missing managed directories
but does not create the profile, manifest, Product object, or Result.

The current Package baseline remains:

```text
Product:                 SkatMind
Package version:         0.17.0
Distribution/import:     skatmind
Python:                  >=3.13
License:                 AGPL-3.0-only
Public API contract:     1
Root workflows:          7
Console Scripts:         1
Settlement Matrix:       version 3, 61 cases
Authoritative Schemas:   71
Packaged Schemas:        71
Session examples:        6
Generated outputs:       98
Private Corpus downloads: 10
```

## Strict technical-English boundary

The following must remain English and locale-neutral:

* Python Package and module names;
* Python symbols and source-code identifiers;
* code comments and Docstrings;
* test names and test-data contracts;
* repository documentation;
* GitHub Issues and comments;
* CLI commands, options, help, errors, and terminal output;
* the Public Python API;
* JSON field names and document kinds;
* workflow identifiers;
* Schema IDs and field names;
* Enum values and machine-readable error codes;
* Routes and action paths;
* cookie names;
* persistence field names;
* hash domains and fingerprints;
* Schema errors shown in Technical details;
* file formats and internal logs;
* generated-output documents;
* benchmark identities;
* filenames required by technical contracts.

German frontend presentation must not change a technical value. For example:

```text
Machine value:          information_set_search
German frontend label: Informationsmengen-Suche

Machine value:          retrospective
German frontend label: Nachträgliche Erfassung
```

The machine value remains authoritative.

## Bilingual frontend boundary

The unified local frontend launched by `skatmind` or `skatmind app` must support
exactly these locale values:

```text
de
en
```

German and English must cover every normal browser-visible string, including
navigation, Home, Analyze, Review, Sessions, Match Capture, Learning, About,
headings, descriptions, form labels, buttons, help text, empty states, statuses,
validation and conflict messages, authorization pages, Result presentation,
Advanced Settings explanations, accessibility labels, and download
descriptions.

The frontend must not translate user-entered Player names, Match titles,
Commentary, source titles, imported text, JSON content, or exact machine values
shown in Technical details.

The advanced standalone CLI must remain English. Standalone `skatmind capture`
and `skatmind corpus` may retain English as their advanced default interface.
Shared rendering code must remain capable of receiving a locale when rendered
inside the unified frontend.

## Translation catalogs

The implementation must use stable locale-neutral message keys, such as:

```text
navigation.home
home.group.record_games
home.task.record_match.title
session.create.player_name
validation.required
learning.empty.primary_action
```

No user-visible sentence may be its own lookup key. English and German catalogs
must have exact key parity and deterministic ordering. They must be repository-
owned Package Resources. English remains the source and reference language for
catalog maintenance; German values are user-visible resources, not technical
source identifiers.

The catalog implementation must use no online translation API, CDN, runtime
download, machine translation, or locale-specific Product logic.
Interpolation values must be escaped. Missing production translations must fail
validation, and a normal page must not silently mix languages.

## Locale resolution and switching

The frontend locale must resolve in this exact order:

```text
1. saved local frontend profile language
2. browser Accept-Language on first use without a saved preference
3. English fallback
```

`de` and `de-*` must resolve to German. `en` and `en-*` must resolve to English.
Every unsupported language must resolve to English. Browser language is only an
initial suggestion. A manual selection must override browser detection and
persist across restarts; a later browser-language change must not override it.

Every unified frontend page must provide one global textual language selector
whose visible labels are:

```text
Deutsch
English
```

A flag may be decorative but must not be the only language indicator. The
current language must be identified in text and accessibility state, and the
HTML `lang` attribute must match the selected locale.

Changing language must retain the current Route; active Session, Match, or
Corpus; process-local Analyze or Review draft and Result; current wizard step;
safe entered values; validation errors; and, where practical, the selected
Advanced disclosure state.

Changing language must not execute or rerun a Product workflow, rebuild a
Result, create or mutate a Session, Match, or Corpus, select a Snapshot, run
preparation, clear a form, or clear a Result. It must not reload persistence
unnecessarily. The only persistence mutation is the explicit profile-language
update.

## Private local frontend profile

There must be one private profile file per managed data root at:

```text
<managed-data-root>/frontend-profile.json
```

Default examples are:

```text
Windows:
    %LOCALAPPDATA%\SkatMind\frontend-profile.json

Linux:
    ${XDG_DATA_HOME:-$HOME/.local/share}/skatmind/frontend-profile.json
```

The profile is private local data. It is not a managed Session, Match, or
Corpus; a managed-item discovery manifest; a Public API document; or a public
Schema. Managed-item discovery must work without it. Starting SkatMind alone
must not create it unless an explicit preference or onboarding choice is saved.

The profile must make no network request and must add no cloud or remote
synchronization, encryption, automatic backup, account, or login claim.

### Conceptual contents

The profile contract may retain:

```text
profile version
document kind
revision
language
interface preferences
own local Player identity
known local Players
preferred perspective
preferred game platform
explicitly saved normal workflow preferences
optional managed-item display labels
content fingerprint
```

It must not contain Cards, hands, Skat, Discards, Plays, Session Commands,
complete Sessions, Match Workspaces, Corpus Catalogs, Snapshots, Reports, Search
Worlds, Results, Commentary, authentication tokens, cookies, absolute imported
paths, or secrets.

Profile persistence must use immutable reconstruction, strict version
validation, deterministic serialization, content-fingerprint validation,
optimistic compare-and-swap, atomic same-directory replacement, explicit reset,
no silent repair, and no automatic migration from unrelated Product files.

### Not an opponent Profile

The local frontend profile is a usability and preference contract. It must not
be confused with existing rule-based opponent Profiles and must not contain or
derive opponent-strength classifications, behavior predictions, tactical
traits, Ratings, Confidence, Statistics, learned values, model features, or
Strategy Teacher evidence.

The user-facing name must be:

```text
Local settings and players
```

It must not be presented as an AI or opponent profile.

## Known-Player directory and perspective

The profile may retain a private local directory of known Players. Each entry
conceptually retains one system-generated stable opaque internal Player ID, one
user-facing display name, optional aliases, optional platform-specific IDs, and
whether the Player represents the local user.

Normal users must enter or select Player names, not internal IDs. Generated IDs
must not be editable in normal forms and must contain no semantic claim.
Imported Product documents must preserve their exact supplied IDs. Duplicate
display names require explicit disambiguation. The frontend must perform no
fuzzy Player merging, automatic identity merge, Player Statistics derivation,
or behavior inference. Technical IDs may be visible only under explicit
Technical details.

The frontend must allow the user to identify one optional own Player entry.
Normal perspective selection must use entered or saved Player names, for
example:

```text
Whose perspective are you recording?

Henning
Peter
Anna
```

The normal frontend must not ask for `Local Player ID` or `Perspective Player
ID`. A profile default may preselect a perspective but must not lock it. Every
active selection must remain visible and changeable before saving or execution.

## Saved frontend preferences

The profile may retain only explicit user-selected frontend preferences. At a
minimum, it must conceptually support selected language, whether Advanced
Settings are normally expanded, preferred capture mode, preferred game
platform, preferred perspective, explicitly saved Position-analysis choices,
and explicitly saved Historical-review choices.

Absent values must use existing Product defaults. Profile preferences must
never change rules or silently add analysis families. The active choice must be
visible before execution. Settings must be saved only through an explicit user
action, and the frontend must provide:

```text
Reset to recommended defaults
```

Seeds and exact technical settings must not persist unless explicitly saved.
There must be no hidden personalization or adaptive or learned configuration.

## Home information architecture

Machine Routes must remain English and unchanged. Visible Home presentation
must use these exact groups and order.

### English

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

### German

```text
Spiele erfassen

    Ein vollständiges 36er-Match erfassen

    Ein einzelnes Spiel erfassen oder fortsetzen

Analysieren und auswerten

    Eine Entscheidung analysieren

    Ein abgeschlossenes einzelnes Spiel auswerten

Über mehrere Matches lernen

    Muster über erfasste Matches hinweg untersuchen

Produktinformationen

    Über SkatMind
```

Match Capture must be the first normal recording task, single-game Session the
second, Learning after recording and analysis, and About last. View ordering
must remain separate from machine Route ordering. No Issue number may appear in
the frontend.

Every Home task must state the unit being handled, when to use the task, what
information is needed, what is stored, what Result is expected, and whether the
task is current/live, retrospective, or both.

The exact conceptual units are:

```text
Analyze:
    one decision

Review:
    one completed individual game

Session:
    one resumable individual game

Match:
    one complete 36-position Match

Learning:
    multiple recorded Matches and selected evidence
```

Analyze must not be labeled only as `Live`. It must use a boundary equivalent
to `Current or retrospective`.

## User-facing terminology

Normal presentation must prefer task language over technical Product nouns.
English and German presentation must use plain explanations equivalent to:

| Technical concept | English normal presentation | German normal presentation |
| --- | --- | --- |
| Session | Record or continue one individual game | Ein einzelnes Spiel erfassen oder fortsetzen |
| Learning Corpus | Learning & cross-game insights | Lernen und spielübergreifende Erkenntnisse |
| Preparation | Build insights | Erkenntnisse erstellen |
| Current Snapshot | Version used for insights | Für Erkenntnisse verwendete Version |
| Snapshot | Saved Match version | Gespeicherte Match-Version |
| Information-set Search Review | Advanced decision review with hidden-card uncertainty | Erweiterte Entscheidungsanalyse mit Unsicherheit über verdeckte Karten |
| Provenance | Technical source and timing details | Technische Angaben zu Quelle und Zeitpunkt |

Technical terms may appear in Advanced or Technical details after a plain
explanation. Translations must be conceptually accurate rather than
mechanically literal.

## JSON import hierarchy

JSON import must remain available but visually and structurally secondary. The
normal page order must be:

```text
primary Create, Continue, or Record action
existing managed items
secondary Advanced import action
```

JSON import must not precede the primary action or begin a normal empty state.
It must be under `Advanced` or `Import existing data`. Imported machine
documents and their fields must remain English and locale-neutral. Caller
filenames must remain non-authoritative.

## Normal creation forms

### Session

The normal Session creation form must ask for these user concepts and German
equivalents:

| English | German |
| --- | --- |
| Name of this game | Name dieses Spiels |
| How are you recording it? | Wie erfassen Sie es? |
| During play | Während des Spiels |
| After the game | Nach dem Spiel |
| Players | Spieler |
| Forehand name | Name in Vorhand |
| Middlehand name | Name in Mittelhand |
| Rearhand name | Name in Hinterhand |
| Whose perspective are you recording? | Aus wessen Perspektive erfassen Sie? |

The form must explain `During play` and `After the game` before selection. It
must use saved known Players where available, allow inline creation of a new
Player, and select perspective through a dropdown of the three named Players.

The normal form must not show Session ID or Player IDs. Internal identifiers
must be generated or safely derived and remain available only in Technical
details. JSON import must be secondary.

### Match

The normal Match creation form must prioritize:

| English | German |
| --- | --- |
| Match title | Titel des Matches |
| Date played, optional | Spieltag, optional |
| Platform, friendly dropdown | Plattform, verständliche Auswahlliste |
| Three Players | Drei Spieler |
| Perspective Player, selected from the three Players | Perspektivspieler, aus den drei Spielern ausgewählt |
| Optional source URL | Optionale Quell-URL |

These technical or uncommon fields must move to Advanced:

```text
External Match ID
Platform Player IDs
Source kind
Source title
Source channel
Exact timestamp
Video start time
Video end time
Technical format identifier
```

The normal form must not ask for a Match ID or expose raw
`euroskat_36_standard_v1`. It must show a friendly fixed-format label. It must
not use raw `RFC 3339` wording and must use locale-appropriate date controls and
text. Video-time fields must appear only when a media source is selected.
Perspective must use Player names.

Hidden fields must never remain conditionally required without explanation.
Required source metadata must either be visibly requested with a reason or
safely derived through an approved existing Product value. JSON import must be
secondary.

### Learning

The normal Learning page must not begin with Corpus terminology or an ID field.
Its primary action must be:

```text
English: Create a learning collection
German:  Lernsammlung erstellen
```

Its normal input must be:

```text
English: Name of this learning collection
German:  Name dieser Lernsammlung
```

The English empty state must explain:

```text
1. Record one or more 36-game Matches.
2. Add selected Matches to this collection.
3. Choose the saved Match version to use.
4. Build cross-game insights.
5. Review or download the resulting summaries.
```

The German empty state must explain:

```text
1. Erfassen Sie ein oder mehrere 36er-Matches.
2. Fügen Sie ausgewählte Matches dieser Sammlung hinzu.
3. Wählen Sie die gespeicherte Match-Version aus, die verwendet werden soll.
4. Erstellen Sie spielübergreifende Erkenntnisse.
5. Prüfen Sie die entstandenen Zusammenfassungen oder laden Sie sie herunter.
```

The normal form must not ask for a Corpus ID. `Corpus` may remain a technical
term only in Advanced explanation. `Current Snapshot` must not appear before
its plain-language explanation, and `Preparation` must not precede `Build
insights`. Zero Counts alone are not an acceptable empty state. The page must
explain that nothing is imported, selected, or analyzed automatically.

## Task-first stateful workflow hierarchy

### Session

The active Session page must begin with this hierarchy:

| English | German |
| --- | --- |
| Current game state | Aktueller Spielzustand |
| Next required Skat action | Nächste erforderliche Skat-Aktion |
| Primary action | Nächster Schritt |
| Cards and Players already entered | Bereits eingegebene Karten und Spieler |

The normal next action must be visually primary. Card entry must be
discoverable, the three Players visible by name, and current phase plus
Live/Retrospective translated and explained. Advanced review and analysis
options must appear later, with advanced review families collapsed.
`Information-set Search Review` must not be a primary control. Technical IDs
and lineage must be under Technical details. The frontend must reuse existing
Session operations unchanged.

### Match

The active Match page must prioritize:

| English | German |
| --- | --- |
| Match progress | Matchfortschritt |
| Next empty or active position | Nächste freie oder aktive Position |
| 36-position overview | Übersicht der 36 Positionen |
| Record this game or mark it passed | Dieses Spiel erfassen oder als eingepasst markieren |

Snapshot controls must not precede the normal Match task. The selected position
and next action must be obvious. One Game must use a concise step-by-step form;
source metadata must be secondary; and technical Match revision and Snapshot
information must be collapsed. Existing exact 36-position and persistence
contracts remain unchanged.

### Learning

The active Learning page must prioritize:

| English | German |
| --- | --- |
| What is needed next? | Was wird als Nächstes benötigt? |
| Recorded Matches available | Verfügbare erfasste Matches |
| Matches added to this collection | Dieser Sammlung hinzugefügte Matches |
| Versions selected for insights | Für Erkenntnisse ausgewählte Versionen |
| Build insights | Erkenntnisse erstellen |
| Results and downloads | Ergebnisse und Downloads |

The page must explain each prerequisite, use plain labels before technical
terms, not show preparation controls before required Match data exists, state
why an action is unavailable, and explain the concrete user benefit. Advanced
Dataset, Strategy Teacher, and Snapshot details must remain collapsed. Existing
Corpus operations and preparation semantics remain unchanged.

## Validation preservation

A normal validation error must render the originating form again. It must
preserve every safe entered text value, selected Players, Card selections,
checkboxes, radio buttons, dropdowns, current wizard step, selected language,
active managed item, and workflow context.

The response must provide one translated error summary and translated field-
local messages. The summary must receive focus, and safe field errors must link
to their controls. An invalid submission must not create or mutate a Product
object, redirect only to Home, or require re-entry of unrelated valid values.

Successful POSTs may continue using POST/Redirect/GET. Invalid file inputs may
require explicit file reselection. Secrets, cookies, tokens, and hidden private
values must never be reflected.

The language-switching state requirements in this document apply equally while
a validation error is visible.

## Security and privacy

Profile and localization implementation must preserve loopback-only binding,
the existing bootstrap and app cookie, Host and Origin validation,
`Referrer-Policy: origin`, Content Security Policy, no CORS, no external
resources, no external runtime request, no translation service, no analytics,
no tracking, no access log, path minimization, token and cookie secrecy, and
private local storage.

The profile may contain local Player names and preferences and therefore
remains private local unredacted data. No encryption or secure-storage claim is
added. Language and profile values must never change Product semantics,
information timing, or information-safety controls.

## Accessibility

Both languages must provide the correct HTML `lang`, equivalent navigation,
labels, error descriptions, status text, and accessibility names. Language
selection must be keyboard-operable and must not rely on flags alone. Focus must
remain visible, and status must not be communicated only by color.

A German page must not retain an English-only `aria-label`, and an English page
must not retain a German-only `aria-label`. Long German labels must remain
usable in responsive layouts.

## Exact implementation sequence

Issue #215 creates none of the following GitHub Issues. It freezes this exact
focused sequence and ownership.

### Issue #216

```text
Add the private local frontend profile and localization foundation
```

Issue #216 owns and implements private profile persistence; locale resolution; the global
language selector; translation catalogs and validation; shell, navigation,
About, common status, authorization, and common-error localization; and
separation of machine keys from presentation text.

### Issue #217

```text
Reorganize the Home dashboard and clarify Product concepts in German and English
```

Issue #217 owns grouped Home information architecture and task order; the
Decision/Game/Match/multiple-Matches distinction; bilingual Product terminology;
Analyze current/retrospective wording; Review single-game wording;
Session/Match/Learning explanations; and bilingual empty states.

### Issue #218

```text
Preserve frontend form state and localize validation feedback
```

Issue #218 owns same-form validation; safe-value, wizard-step, and language-
switch state preservation; translated error summaries and field-local messages;
and consistent HTTP `400`/`409` workflow return behavior.

### Issue #219

```text
Simplify profile-driven Session, Match, and Learning creation
```

Issue #219 owns the known-Player directory; own Player and perspective
selection; system-owned internal IDs; friendly normal creation fields; fixed
friendly format labels; date and conditional media-source input; secondary JSON
import; and local saved defaults.

### Issue #220

```text
Add task-first bilingual Session, Match, and Learning workflows
```

Issue #220 owns the next-action Session layout; minimal Match Game-entry flow;
Learning prerequisite and Build-insights flow; Snapshot and Preparation plain-
language presentation; Advanced/Technical-detail separation; and completion of
all remaining German and English frontend catalog coverage.

## Finding ownership

The exact remaining finding state and ownership is:

```text
UAT-FINDING-001:
    further partially remediated by Issue #216
    open across Issues #217 through #220

UAT-FINDING-003:
    Issues #217 and #220

UAT-FINDING-005:
    Issue #219 and relevant Issue #220 views

UAT-FINDING-006:
    Issue #218

UAT-FINDING-007:
    foundation implemented by Issue #216
    open for Issues #219 and #220

UAT-FINDING-008:
    foundation and common coverage implemented by Issue #216
    open pending complete coverage through Issue #220
```

The resolved finding state remains:

```text
UAT-FINDING-002:
    resolved by Issue #213

UAT-FINDING-004:
    resolved by Issue #214
```

## UAT repetition and gate state

Repeated UAT-01 remains failed. UAT-01 may be repeated again only after Issues
#217 through #220 are implemented and validated. UAT-02 through UAT-12 must
remain paused until that repeated UAT-01 passes.

The next repeated UAT-01 must verify at least:

* complete German and English frontend presentation;
* saved language across restart;
* no machine-contract translation;
* the grouped Home hierarchy;
* the Decision/Game/Match/multiple-Matches distinction;
* profile-backed Player selection;
* no required manual IDs in normal workflows;
* simplified Session, Match, and Learning creation;
* preserved form values after validation errors;
* task-first Session and Match entry;
* a useful Learning empty state;
* no JSON-first normal flow;
* no path, port, token, or private-state exposure.

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

Package 1.0.0 preparation:
    not ready
```

The completed 53-row technical ledger must not be reopened. The exact next
implementation action is:

```text
Issue #217 — Reorganize the Home dashboard and clarify Product concepts in
German and English
```

## Non-goals and accepted limitations

Issue #216 does not implement Home reordering, form simplification, validation
preservation, generated IDs, Player-directory behavior, profile-driven workflow
defaults, task-first stateful layouts, or complete workflow translation. Those
changes remain owned by Issues #217 through #220. It does not create a tag or
Release.

Issue #215 must not translate or change the CLI, Public Python API, JSON,
Schemas, IDs, Enums, Routes, errors, persistence, hashes, generated outputs, or
technical source language. It must not change Product persistence, Product
semantics, dependencies, Package version, Public API, Root workflows, browser
protocols, Schemas, examples, generated outputs, Release metadata, or the
completed technical ledger.

The approved target adds no external translation service, remote profile sync,
cloud service, account, login, encryption claim, secure-storage claim,
automatic backup claim, analytics, tracking, learned personalization, fuzzy
Player identity merge, or opponent-profile inference. Four-player table support
remains unconditionally out of scope; other Product limitations remain governed
by [v1.0 scope](v1_scope.md).

Package version remains `0.17.0`. Issue #208, B-09, and B-07 remain open,
repeated UAT-01 remains failed, UAT-02 through UAT-12 remain paused, B-06 remains
closed, and Package `1.0.0` and Release preparation remain not ready.
