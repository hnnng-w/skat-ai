# Bilingual Home information architecture

## Status

Issue #217 implements the Home and Product-concept slice frozen by the
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
This is private unified-browser presentation. It adds no Public API export, Root
workflow, Schema, persistence format, dependency, or Product behavior.

The private version is exactly:

```text
FRONTEND_INFORMATION_ARCHITECTURE_VERSION = 1
```

Issue #217 extends the implemented subset of the complete Issue #215 policy
vocabulary with exactly:

```text
home_separates_record_analyze_learn_and_product_information
```

The complete implemented subset, in canonical vocabulary order, is:

```text
technical_contracts_and_machine_values_remain_english
unified_frontend_visible_content_supports_german_and_english
one_private_local_frontend_profile_per_managed_data_root
saved_language_overrides_browser_language
browser_language_bootstraps_only_without_saved_preference
home_separates_record_analyze_learn_and_product_information
language_and_profile_never_change_product_semantics
no_external_translation_profile_sync_or_cloud_service
```

The future policies for user-facing names instead of manual IDs, task-first
profile-driven workflows, secondary explained Advanced Settings, and validation
preservation remain unimplemented by this Issue.

## Private values

The exact group keys and order are:

```text
record_games
analyze_and_review
learn_across_matches
product_information
```

The exact task keys and Home presentation order are:

```text
record_match
record_session
analyze_decision
review_game
learning_insights
about
```

The exact mapping is:

```text
record_match       -> /matches
record_session     -> /sessions
analyze_decision   -> /analyze
review_game        -> /review
learning_insights  -> /learning
about              -> /about
```

The exact group membership is:

```text
record_games:
    record_match
    record_session

analyze_and_review:
    analyze_decision
    review_game

learn_across_matches:
    learning_insights

product_information:
    about
```

Contract validation rejects a boolean or changed version and every duplicate,
missing, reordered, orphaned, or extra group, task, mapping, membership, related
area, or empty-state key. These values remain private under
`src/skatmind/app_web/`.

## Routes and navigation

Machine Route order remains independent and unchanged:

```text
/
/analyze
/review
/sessions
/matches
/learning
/about
```

The concise visible navigation labels are:

| Route | English | German |
| --- | --- | --- |
| `/` | Home | Startseite |
| `/analyze` | Analyze one decision | Eine Entscheidung analysieren |
| `/review` | Review one completed game | Ein abgeschlossenes Spiel auswerten |
| `/sessions` | Record one game | Ein Spiel erfassen |
| `/matches` | Record a 36-game Match | 36er-Match erfassen |
| `/learning` | Learn across Matches | Über Matches lernen |
| `/about` | About SkatMind | Über SkatMind |

No action, download, Public API, cookie, form-field, workflow, persistence, or
document identity changes.

## Home groups

The exact bilingual headings are:

| Key | English | German |
| --- | --- | --- |
| `record_games` | Record games | Spiele erfassen |
| `analyze_and_review` | Analyze and review | Analysieren und auswerten |
| `learn_across_matches` | Learn across Matches | Über mehrere Matches lernen |
| `product_information` | Product information | Produktinformationen |

The exact bilingual task titles are:

| Key | English | German |
| --- | --- | --- |
| `record_match` | Record a complete 36-game Match | Ein vollständiges 36er-Match erfassen |
| `record_session` | Record or continue one individual game | Ein einzelnes Spiel erfassen oder fortsetzen |
| `analyze_decision` | Analyze one decision | Eine Entscheidung analysieren |
| `review_game` | Review one completed individual game | Ein abgeschlossenes einzelnes Spiel auswerten |
| `learning_insights` | Explore patterns across recorded Matches | Muster über erfasste Matches hinweg untersuchen |
| `about` | About SkatMind | Über SkatMind |

The introductory copy is followed by the scope guide and then the four semantic
group sections. Each group has an H2; each task card has an H3. Match Capture is
the first normal recording task, Session is second, and About remains last.

Each compact card initially shows only its title, one purpose sentence, explicit
unit, timing, and one clear GET link. A native closed `details` disclosure retains
when to use the area, required information, storage, and expected Result. The
cards require no JavaScript and no repeated availability line.

## Scope guide

The Home scope guide begins with:

```text
Which area do I need?
Welchen Bereich brauche ich?
```

It maps one Decision to Analyze, one Game being recorded or resumed to Session,
one completed Game being evaluated to Review, one complete 36-position Match to
Match Capture, and multiple recorded Matches to Learning. It explicitly states
that Session records or continues one Game while Review evaluates one Game that
is already completed. The guide uses no internal IDs or analysis, data, or
reproducibility terminology.

## Product units

The visible concepts are:

| Area | Scope | Timing |
| --- | --- | --- |
| Analyze | one Decision | current or retrospective |
| Review | one completed individual Game | retrospective |
| Session | one resumable individual Game | during play or afterward |
| Match | one complete 36-position Match | during observation or afterward |
| Learning | multiple recorded Matches and selected evidence | after Match recording |
| About | Product and local-installation information | any time |

Analyze explains that one Decision may use current visible information or a
reconstructed retrospective Decision. It does not promise guaranteed real-time
speed and changes no Position input, setting, execution, or Result.

Review explicitly covers one completed individual Skat game. It may present
recorded Decisions, alternatives, Result, Overbid, Settlement, and selected
optional evidence. A complete 36-position list belongs under Match Capture.

One Session equals one Game. It may be recorded during play or afterward, can be
resumed, and is appropriate for a standalone Game. It is not automatically
inserted into a Match.

Match Capture is the primary recording workflow for one complete EuroSkat 36er
Standard Match with the same three participants. It retains all 36 authoritative
positions, including Played Games and Passed Deals, persists locally, and can be
resumed. A one-Game Session remains a separate object.

Learning explores descriptive patterns across explicitly selected evidence from
multiple recorded Matches. Its visible journey is:

```text
1. record one or more complete 36-position Matches;
2. explicitly add selected Matches to a learning collection;
3. explicitly choose the saved Match version to use;
4. explicitly build insights;
5. review or download the summaries.
```

Nothing is imported, selected, analyzed, or built automatically. The summaries
do not establish Player truth, Rating, intent, or learned behavior. Corpus
operations and preparation remain unchanged.

## Empty states

The Session landing explains that no standalone one-Game record exists, defines
the resumable during-or-afterward unit, distinguishes it from Match Capture, and
points to the unchanged creation form.

The Match landing explains that no complete Match is recorded, defines the same-
three-participant 36-position unit with Played Games and Passed Deals, and points
to the existing Match creation action.

The Learning landing explains that no learning collection exists, defines its
cross-Match purpose and recorded-Match prerequisite, and directs the user to
record Matches before explicitly creating a collection.

An active Learning collection with no imported Match data explains why no cross-
game summary is available and directs the user to record a Match, add it
explicitly, select the saved Match version, and explicitly build insights. The
existing zero counts remain secondary diagnostics. No empty state creates,
opens, imports, selects, analyzes, or prepares anything.

## Related areas

Only safe existing-route GET links are added:

```text
Analyze -> Review
Review -> Analyze and Match
Session -> Match
Match -> Session and Learning
Learning -> Match
```

They contain no query string and perform no mutation, selection, import,
preparation, or Product execution.

## Localization and rendering

The English and German catalogs add sorted parity-checked `home.group.*`,
`home.scope_guide.*`, `home.task.*`, `concept.*`, `empty.*`, and `related.*`
keys. Visible German or English Issue #217 copy is not hard-coded in Python.

On a German workflow page, the localized Product concept, related links, and any
Issue #217 empty state appear in German before the existing transition notice.
The future-owned form or dashboard body remains inside an explicit `lang="en"`
region. Home is fully localized and has no transitional region. This does not
claim complete workflow translation; that remains Issue #220.

The packaged CSS adds only the semantic Home grouping, compact cards, scope and
concept guides, empty states, responsive long-label handling, native disclosure,
and existing visible-focus integration. There is no external resource,
framework, or new JavaScript.

## Security and compatibility

Home rendering performs no Product execution or managed-item discovery. The
implementation preserves loopback binding, bootstrap and app cookie, Host and
Origin validation, `Referrer-Policy: origin`, CSP, no CORS, no external request,
no access log, retained active contexts, and all existing information
boundaries. It renders no private path, identifier, fingerprint, Card, document,
token, cookie, or port.

The compatibility baseline remains:

```text
Package:                    0.17.0
Python:                     >=3.13
License:                    AGPL-3.0-only
Runtime dependencies:       unchanged
Public API contract:        1
Root workflows:             7
Console Scripts:            1
Settlement Matrix:          version 3, 61 cases
Authoritative Schemas:      71
Packaged Schemas:           71
Session examples:           6
Generated outputs:          98
Private Corpus downloads:   10
```

## UAT and next action

The post-Issue-#217 state is:

```text
UAT-FINDING-001:
    further partially remediated
    open

UAT-FINDING-002:
    resolved by Issue #213

UAT-FINDING-003:
    Home and concept remediation implemented
    open pending Issue #220 and repeated UAT-01

UAT-FINDING-004:
    resolved by Issue #214

UAT-FINDING-005:
    open

UAT-FINDING-006:
    open
    owned by Issue #218

UAT-FINDING-007:
    open

UAT-FINDING-008:
    bilingual Home and concept coverage implemented
    open pending Issue #220

Repeated UAT-01:
    failed

UAT-02 through UAT-12:
    paused

Issue #208:
    open

B-09:
    open

B-07:
    open
```

Issue #217 does not repeat UAT or close a finding. Package `1.0.0` and Release
preparation remain not ready. The exact next action is:

```text
Issue #218 — Preserve frontend form state and localize validation feedback
```
