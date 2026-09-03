# Profile-driven stateful creation

## Status and boundary

Issue #219 implements the private version-1 profile-driven creation layer in the
unified local browser application. It simplifies creation of one Session Game,
one EuroSkat 36-position Match, and one Learning collection without changing the
underlying Session, Match Workspace, or Learning Corpus persistence contracts.

The private contract identity is:

```text
PROFILE_DRIVEN_FORM_DEFAULTS_VERSION = 1
```

The implementation does not change Package version `0.17.0`, Python `>=3.13`,
the `AGPL-3.0-only` license, Public API contract version `1`, the seven Root
workflows, the one Console Script, Schemas, examples, generated outputs, Product
persistence formats, or standalone technical interfaces.

## Local settings and Players

Issue #219 activates the reserved version-1 fields in the existing private
`frontend-profile.json` document. `LOCAL_FRONTEND_PROFILE_VERSION` remains `1`,
and the historical canonical empty-profile bytes and fingerprint remain
unchanged. The profile may now retain:

* known Players with a display name, aliases, and optional platform Player IDs;
* one own Player and one preferred perspective Player;
* one preferred friendly game platform;
* the existing Advanced-settings display preference;
* private display names for managed Sessions, Matches, and Learning collections;
* an optional date-only Match display label.

The About page provides authenticated bilingual operations to add, edit, and
remove known Players, edit creation defaults, reset recommended defaults, and
reset the complete profile. Stateful landing pages allow display labels to be
edited for both created and imported managed Products. Labels never rename the
authoritative Product identity or persistence file.

The strict bounds are:

```text
known Players:                         512
aliases per Player:                    16
platform IDs per Player:               16
Player and platform-name characters:  120
platform Player-ID characters:         255
managed display labels:                2,048
managed display-name characters:       160
profile file bytes:                    1,048,576
```

Duplicate Player display names require explicit disambiguation. Profile writes
remain canonical, revisioned, fingerprinted, same-directory atomic replacements
with optimistic compare-and-swap behavior. A profile file changed outside the
running process requires restarting SkatMind before another profile-only write.
An invalid profile must be explicitly reset from About before profile-driven
creation or local-setting mutation; opening existing Products remains separate.

## Generated identities

Normal creation owns technical identifiers. Each identifier uses 32 bytes from
an injected entropy source, a domain-separated SHA-256 digest, and at most 16
generation attempts. The exact prefixes are:

```text
frontend-player-
frontend-session-
frontend-match-
frontend-corpus-
```

The frozen domains are:

```text
b"skatmind\0frontend_player_id_v1\0"
b"skatmind\0frontend_session_id_v1\0"
b"skatmind\0frontend_match_id_v1\0"
b"skatmind\0frontend_corpus_id_v1\0"
b"skatmind\0frontend_known_player_handle_v1\0"
```

Known-Player selection uses one-way SHA-256 browser handles together with the
current profile generation. Internal Player IDs, Product paths, profile
fingerprints, and platform IDs are not presented as normal visible values.
Imported Session and Match identities are retained unchanged; frontend identity
generation applies only to normal creation.

## Creation forms

The Session form asks for a Game name, during-play or retrospective capture,
three named Players, and an optional perspective seat where permitted. A Player
seat may select one saved Player or enter one new display name. Saving new
Players and the selected perspective is explicit. Capture mode is not a saved
profile preference.

The Match form presents the fixed `EuroSkat 36-game standard` format as a
friendly non-editable fact. It asks for a Match title, an optional date-only
display value, a friendly platform, three named Players, and a perspective
seat. Friendly platform values are `euroskat`, `in_person`, `other_online`,
`unknown`, and `custom`. An optional Source URL is a normal field; source kind,
title, channel, timecodes, and other exact Product metadata remain inside
Advanced settings. A date-only value is private display metadata and does not
invent `played_at`; only an explicit Advanced RFC 3339 value populates that
Product field. Saved platform account IDs are not copied invisibly into a new
Match; only values explicitly submitted for that Match enter Product metadata.

The Learning form asks only for a collection name and generates the internal
Corpus ID. It does not import Matches, select a Current Snapshot, prepare
artifacts, or run analysis.

Session and Match JSON import remain secondary actions after normal creation and
saved items. Import preserves the supplied Product identity. There is no new
whole-Corpus JSON import path.

All creation and settings forms use the Issue-#218 registered validation layer.
Safe submitted values survive localized `400` and `409` responses and language
changes. Field-specific errors attach to the exact form and open their containing
Advanced disclosure when necessary. Opaque handles are retained only as bounded
hidden or select identity values and are never included in visible error text.

## Persistence ordering

The creation sequence is strict:

```text
validate submitted values and current profile generation
generate collision-checked private identities
create and persist the authoritative Product exactly once
attempt the optional profile update exactly once
publish the active Product and redirect to its normal page
```

A Product creation failure makes no profile change. Once Product persistence
succeeds, a profile conflict, capacity limit, size limit, or storage failure does
not roll back or delete the Product. The Product remains persisted, active, and
discoverable, and the browser displays a localized non-destructive warning.
There is no cross-file transaction claim. Creation runs no analysis,
preparation, automatic Learning import, or Match-to-Corpus transfer.

## Validation and packaging

The unified frontend now has exactly 44 POST routes and 77 registered form
definitions. The strict German and English catalogs contain the same 463 keys.
Focused tests cover profile compatibility and persistence, generated domains and
collision handling, known-Player operations, friendly creation translation,
safe validation retention, bilingual rendering, one-call Product/profile
ordering, and Product survival across profile conflict, size, and storage
failures for Session, Match, and Learning creation.

The private modules, translation catalogs, and local CSS remain packaged
resources. No new dependency, route outside the loopback application, Public API,
Schema, example, generated output, or Package entry point is introduced.

## Remaining frontend work

Issue #219 further partially remediates UAT-FINDING-001, implements the creation-
form portion of UAT-FINDING-005, implements the profile/default/creation portion
of UAT-FINDING-007, and adds bilingual creation pages toward UAT-FINDING-008.
Those findings remain open pending their applicable Issue-#220 work and repeated
UAT-01.

The exact next action is:

```text
Issue #220 - Add task-first bilingual Session, Match, and Learning workflows
```

Issue #220 owns next-action active Session layout, minimal Match Game entry,
Learning prerequisites and Build-insights flow, plain-language Snapshot and
Preparation presentation, complete Advanced/Technical-detail separation, and
remaining German and English workflow coverage. UAT-02 through UAT-12 remain
paused; B-09 and B-07 remain open; Package `1.0.0` and Release preparation are
not ready.
