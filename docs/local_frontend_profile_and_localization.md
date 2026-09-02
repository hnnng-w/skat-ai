# Local frontend profile and localization

## Status

Issue #216 implements the private local frontend profile and localization
foundation approved by the
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
This is private unified-browser behavior. It is not a Public API export, an
eighth Root workflow, a public Schema, or a Product persistence format.

The implemented contract versions are exactly:

```text
BILINGUAL_FRONTEND_CONTRACT_VERSION = 1
FRONTEND_TRANSLATION_CATALOG_VERSION = 1
LOCAL_FRONTEND_PROFILE_VERSION = 1
```

Issues #216 and #217 retain the complete frozen policy vocabulary and implement:

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

The policies for user-facing Player names, task-first profile-driven workflows,
secondary Advanced Settings, and validation preservation remain frozen but
future-owned by Issues #218 through #220. The grouped Home policy is implemented
by Issue #217 and documented in
[Bilingual Home information architecture](bilingual_home_information_architecture.md).

## Language boundary

Repository code, comments, Docstrings, tests, documentation, CLI output, Public
API values, JSON, Schemas, Routes, machine identifiers, Enum values, error codes,
persistence fields, hashes, fingerprints, and generated outputs remain English
and locale-neutral. German exists only as escaped visible unified-browser
presentation.

The supported locales are exactly:

```text
SUPPORTED_FRONTEND_LOCALES = ("de", "en")
FRONTEND_REFERENCE_LOCALE = "en"
FRONTEND_FALLBACK_LOCALE = "en"
```

Standalone `skatmind capture` and `skatmind corpus`, all CLI families, and the
Public Python API remain English and unchanged.

## Catalogs

The repository-owned Package Resources are:

```text
src/skatmind/app_web/locales/en.json
src/skatmind/app_web/locales/de.json
```

They are loaded through `importlib.resources`. Each catalog is one finite flat
JSON object with lexicographically ordered locale-neutral keys and non-empty text
values. Loading rejects a UTF-8 BOM, invalid UTF-8, duplicate object keys,
non-finite values, a non-object root, unsorted keys, non-text values, key drift,
and interpolation-placeholder drift. English is the reference catalog. Missing
German keys fail strictly; runtime lookup does not fall back from German to
English.

Translation lookup returns plain text. The HTML renderer escapes the translated
text and all interpolation results. The implementation uses no network,
translation service, runtime download, CDN, machine translation, generated
bundle, or Node toolchain.

## Locale resolution

Each request resolves locale in this order:

```text
1. saved profile language
2. one usable Accept-Language header when no language is saved
3. English fallback
```

`de` and `de-*` select German; `en` and `en-*` select English. Positive quality
values are ordered by descending quality and then original range order. Zero
quality, malformed, wildcard-only, unsupported, oversized, and unusable input is
ignored safely. Duplicate `Accept-Language` headers do not become trusted input.
The raw header is never retained.

Browser-derived language is process-request input only and is never persisted
automatically. A saved language always overrides later browser-language changes.
An invalid profile is trusted for no preference and forces English fallback.

## Profile document

One profile may exist as the regular non-link direct child:

```text
<managed-data-root>/frontend-profile.json
```

It is separate from the three managed categories `sessions`, `matches`, and
`corpora`, and managed discovery ignores it. Startup and browser-language
detection do not create it. Explicit language selection or explicit reset may
create it.

The exact Issue #216 document shape is:

```json
{
  "local_frontend_profile_version": 1,
  "document_kind": "skatmind_frontend_profile",
  "revision": 0,
  "language": "de",
  "interface_preferences": {
    "advanced_settings_expanded": false
  },
  "own_player_id": null,
  "known_players": [],
  "preferred_perspective_player_id": null,
  "preferred_game_platform": null,
  "workflow_preferences": {
    "position_analysis": null,
    "historical_review": null
  },
  "managed_item_display_labels": [],
  "content_fingerprint": "<lowercase-sha256>"
}
```

`language` may be `de`, `en`, or null. Every future-owned Player, perspective,
platform, workflow-default, display-label, and Advanced-settings value remains
at its canonical null, empty, or false value. Issue #216 exposes no Player
management UI.

Unknown, missing, reordered, or wrongly typed fields are invalid. Boolean
revisions are rejected. The maximum file size is `1,048,576` bytes.

## Fingerprint and bytes

The exact fingerprint domain is:

```text
skatmind\0frontend_profile_v1\0
```

SHA-256 covers the domain and canonical profile payload without
`content_fingerprint`. Final file bytes are deterministic finite JSON using
UTF-8 without BOM, two-space indentation, canonical field order, LF line
endings, and exactly one trailing LF. Loading verifies the fingerprint and exact
canonical byte round trip.

## Persistence

Load statuses are exactly:

```text
absent
available
invalid
```

Write statuses are exactly:

```text
saved
unchanged
conflict
```

Saving uses an expected valid fingerprint, an expected invalid raw-file digest,
or an absent-file expectation. It observes the target before writing and again
immediately before replacement, writes a complete same-directory temporary file,
flushes and syncs it, uses atomic `os.replace`, attempts directory durability,
and cleans up temporary files. It does not retry, merge, silently overwrite, or
repair.

For an oversized, unreadable, or nonregular direct entry that cannot safely
produce bounded raw bytes, the private invalid-digest slot retains a
domain-separated metadata observation instead. This permits a stable second
comparison without following a link or reading an unbounded file. Explicit
reset may replace a link or regular file and may remove an empty directory at
the reserved profile path; a nonempty directory is retained and produces a safe
filesystem failure.

The optimistic boundary is intentionally limited to the required second
pre-replacement observation. It is not a cross-process transaction or an
external lock; the focused contract explicitly adds no coordination outside the
profile file boundary.

Initial explicit creation uses revision zero. A changed valid profile increments
revision once. Selecting the already saved language returns `unchanged` and
writes nothing. The app context uses a separate profile-operation lock and a
process-local profile generation so language persistence does not hold or mutate
Product workflow contexts.

## Invalid profile and reset

An invalid profile remains byte-for-byte unchanged and does not prevent startup.
It contributes no language preference, selects English fallback, and produces
one safe common warning. Browser output includes no parser detail, raw bytes,
profile path, fingerprint, raw digest, stack trace, or failed security value.

Language saving is blocked until explicit reset. The reset action compares the
retained valid fingerprint or invalid raw-file digest and atomically publishes
the canonical empty profile. It changes no Session, Match, Learning Corpus,
Result, Report, source, prepared artifact, discovery, or active selection.

## Browser state

The private app context retains the profile path, load state, valid document,
expected fingerprint, invalid raw digest where available, process-local
generation, and safe warning state. Browser-safe rendering receives only:

```text
locale
resolution source
profile status
valid revision when available
profile generation
safe warning flag
```

It receives no path, fingerprint, digest, raw header, token, cookie, port,
environment value, or Product data. Profile loading occurs once during app
context creation; there is no watcher, polling loop, background worker, or
page-load disk read.

## Browser actions

The authenticated language mutation route is exactly:

```text
POST /actions/profile/language
```

Its exact fields are `language`, `profile_generation`, and `return_to`. The
reset route is `POST /actions/profile/reset` with explicit confirmation under
the same private namespace. Both require the app cookie, exact Host, exact
Origin, canonical form encoding, current generation, and a safe rendered local
HTML return path.

Allowed return paths cover the seven shell routes plus safe current Session,
Match, Match-position, Match-report, and Learning pages. Validation rejects
external and protocol-relative URLs, query strings, fragments, assets,
downloads, state/API routes, POST actions, bootstrap-token URLs, invalid dynamic
identities, and unknown paths. Referer is neither authorization input nor return
routing input.

Saved and unchanged actions return `303`. Malformed forms return `400`. Stale
generation, invalid-profile language save, and persistence conflict return
`409`.

To preserve an already retained managed-category discovery through the `303`
language redirect, the process-local app context may retain one pending safe
return Route. Only the matching authenticated HTML GET consumes it. This marker
contains no query, form value, profile digest, Product value, or browser secret.

## Visible coverage

Issue #216 provides German and English presentation for:

* the shared shell, skip link, Product accessibility label, navigation, footer,
  global language selector, and exact HTML `lang`;
* the grouped Home, scope guide, compact task cards, Product concepts, related
  links, and useful stateful empty states through Issue #217;
* About, managed-storage explanation, local/private and no-cloud statements,
  language source, profile status, future-work notice, and reset;
* authorization and generic common HTTP error wrappers;
* common shell status and action vocabulary.

Every unified page contains the textual `Deutsch` and `English` selector. It is
a native authenticated POST form and works without JavaScript.

Analyze, Review, Session, Match, and Learning workflow bodies are not fully
translated by Issue #216. When German is active, the shell shows a German
translation-status notice and wraps the future-owned English body in an explicit
`lang="en"` region. This avoids silent language mixing and does not claim complete
German workflow coverage. Complete workflow translation remains Issue #220.

## State and security

Language switching changes only profile/locale state. It does not execute or
rerun Product work and retains server-owned Analyze/Review drafts and Results,
Review step, active Session, active Match, active Learning Corpus, Match Reports,
Learning sources/prepared artifacts, discovery state, and the current safe
route. Preservation of arbitrary unsubmitted browser-only fields remains Issue
#218.

The implementation preserves loopback-only binding, bootstrap token and app
cookie, exact Host and Origin validation, `Referrer-Policy: origin`, CSP,
`no-store`, `nosniff`, frame denial, no CORS, no access log, no external
resource, and value-free authorization failures. Profile and locale values never
change Product semantics or information-use controls.

The reopened Issue #216 follow-up also keeps localized parser-level common
errors safe across CPython 3.13 patch releases. CPython 3.13.15 on Ubuntu left
`BaseHTTPRequestHandler.headers` as a plain empty dictionary for the rejected
two-token HTTP/0.9 request, while the Windows CPython 3.13.7 run exposed a
complete multi-value header object. Browser-language evidence is now accepted
only from the expected complete `email.message.Message` interface. Missing,
`None`, mapping, and partial containers are treated as absent browser evidence,
while saved-profile precedence and deterministic English fallback remain intact.
Malformed GET and POST targets still return hardened HTTP `400`; invalid HTTP
versions and HTTP/0.9 still return hardened HTTP `505`; every path retains all
security headers without access logging or a request-thread traceback.

## Packaging and compatibility

The two locale JSON files are `skatmind.app_web` Package Data. Source, Editable,
Wheel, sdist, clean Wheel, and clean sdist validation checks exact resource
bytes, strict catalog loading, no startup profile write, browser-derived German,
explicit language persistence, saved-language precedence, and restart loading
inside isolated temporary managed roots. Distribution tests use no real user
profile or browser.

The separate failed `source-resolved` matrix smoke was not caused by locale
handling, Linux, Package Resources, or a CPython patch difference. The outer
validator emitted distinct `compatibility` and canonical `run` Root output
files, but the installed smoke still requested the older unsuffixed filenames.
The smoke now validates both emitted files against the same Public API document.
Matrix child failures retain the installation form, dependency lane, exception
category, sanitized command, and bounded stdout/stderr excerpts with repository
and matrix roots replaced by stable placeholders.

Issue #216 preserves Package `0.17.0`, Python `>=3.13`, `AGPL-3.0-only`, the two
unchanged runtime dependencies, Public API contract `1`, seven Root workflows,
one Console Script, Settlement Matrix version `3` with 61 cases, 71 authoritative
and packaged Schemas, six Session examples, 98 generated outputs, and ten Corpus
downloads.

## Remaining work and UAT

Home grouping and Product terminology are implemented by Issue #217. Validation
and safe submitted-value preservation remain Issue #218. Known Players,
profile-driven Player/default behavior, generated IDs, and simplified creation
forms remain Issue #219. Task-first stateful layouts and complete bilingual
workflow coverage remain Issue #220.

The current finding state is:

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
    foundation implemented
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

Package `1.0.0` and Release preparation remain not ready. The Issue #216
correction and both required post-merge Ubuntu jobs passed. Issue #217 implements
its assigned Home and concept scope. Issue #218, "Preserve frontend form state
and localize validation feedback," is the exact next action.
