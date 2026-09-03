# Frontend validation state and localized feedback

## Status

Issue #218 implements safe submitted-form preservation and localized validation
feedback in the private unified local frontend. It implements the frozen policy:

```text
validation_preserves_safe_values_and_workflow_context
```

It changes no Skat rule, Product algorithm, persistence format, Public API, CLI,
Root workflow, Schema, example, generated output, dependency, or Package version.
Standalone `skatmind capture`, `skatmind corpus`, and `skatmind session` behavior
remains unchanged.

## Contract Identity

The private contract identity is:

```text
FRONTEND_VALIDATION_PRESERVATION_VERSION = 1
```

`FrontendValidationIssueV1` retains only a locale-neutral message key, an
optional registered field key, and bounded interpolation arguments.
`FrontendSubmittedFormStateV1` retains one rejected form key, originating route,
active-family binding, optional Review step, optional opaque rendered-form
ordinal, allowlisted visible values, structured issues, status, and process-local
feedback generation.

These immutable values are private implementation contracts. They are not Public
API exports and are not persisted.

## Canonical Form Registry

`FRONTEND_FORM_REGISTRY` covers all 44 unified frontend POST routes through 77
exact definitions. Shared routes are split by their existing discriminator:

```text
Session Command kind
Match mutation operation
Match analysis operation
Learning operation
```

Each definition records its media type, request bound, safe visible fields,
cardinality, control type, fixed choices where applicable, originating page,
active context, Review step, upload reselection rule, success redirect, and
contextual failure page. Registry validation rejects missing routes, orphaned
routes, duplicate identities, and incomplete Session or Match operation coverage.

The registry excludes revisions, optimistic fingerprints, tokens, cookies,
caller paths, caller filenames, and other hidden transport or private state.
Opaque known-Player and managed handles may be retained only as bounded hidden
or select identity values for exact form targeting; they are never visible IDs
or raw error text. File inputs and destructive confirmations are never
retained. Text and repeated values are bounded; fixed select and radio values
use explicit allowlists; Card selections use canonical Card limits. Omitted
checkbox and repeated Card groups retain an explicit empty presentation value so
a rejected form does not restore an older accepted selection.

When one definition has several rendered instances, the unified renderer adds a
bounded process-local ordinal hidden field. It identifies only the rendered form
instance and contains no Product identity. Multipart forms are not instrumented.
The standalone Capture and Corpus renderers are not modified.

## Accepted And Submitted State

Rejected submitted state is separate from authoritative Product and accepted
workflow state. Validation occurs before Product creation or mutation wherever
the existing operation permits it. Analyze candidate execution validates and
executes without accepting its draft; only successful publication atomically
accepts the draft and Result.

A rejected Analyze or Review attempt does not advance its accepted revision,
replace its draft or imported Request, clear its last successful Result, or
replace Request/Result download bytes. Review parser rejection therefore remains
on the exact accepted wizard step. Session, Match, and Learning rejection keeps
the exact active managed context. Existing Product conflict results remain
authoritative, but their raw messages are not used as frontend validation text.

The process-local feedback store retains at most one rejected attempt for each
of these families:

```text
analyze
review
profile
local_settings
sessions
matches
learning
```

A later rejection replaces the prior attempt in that family. Successful form
submission clears that family's feedback. Switching an active Session, Match, or
Learning Corpus invalidates feedback bound to the previous exact active object.
Closing the process discards all feedback.

## HTTP And Rendering

Successful browser actions retain POST/Redirect/GET and HTTP `303`. Normal
validation and unsupported-workflow failures return contextual HTML with HTTP
`400`. Stale form, optimistic persistence, duplicate identity, and Product
conflict failures return contextual HTML with HTTP `409`. Existing `413`, `415`,
authorization, method, not-found, and generic internal-error boundaries remain
in force. Shared-route failures that occur before one unique registered
discriminator and media type can be recovered remain fixed, localized, form-
agnostic errors; they never bind feedback to an arbitrary form.

Once the originating form is uniquely identified, the failed response renders
that form rather than a generic error page. Safe values are applied to text
controls, textareas, checkboxes, radios, repeated Card controls, and selects. The
Review disclosure containing the exact accepted step and any disclosure
containing the failed form or failed field is opened. Issue #219 creation errors
may declare their exact registered field. Repeated Player and managed-label
forms bind feedback to opaque form identity values so only the rejected item is
annotated; if that exact item is no longer renderable, a page-level summary is
used instead.

Each response contains one translated error summary for the rejected form and
translated field-local messages where a visible control exists. The summary is a
focus target with `role="alert"`; summary links target the corresponding control;
controls use `aria-invalid="true"` and `aria-describedby`; focus styling and
status presentation do not depend on color alone. If a prior valid Result remains
visible, the summary says that it was retained.

Translation occurs from structured message keys at render time. A language
change preserves the rejected form and values, then renders its summary and
messages in the newly selected German or English locale. Technical contracts,
Routes, field names, and Product values remain English and locale-neutral.

## Uploads And Security

Upload failures never reflect file paths, filenames, bytes, or multipart
metadata. The user receives a localized size, media-type, invalid-file, or
unsupported-workflow message and, when the exact upload form is identified, an
explicit instruction to select the file again. Failures before form identity is
available use only a fixed localized generic response. Successful parsed upload
content is never retained as submitted-form state.

Known exceptions are mapped to a finite localized vocabulary. Unknown validation
exceptions use one generic Product-rejection message. Browser output therefore
contains no raw exception text, stack trace, filesystem path, visible managed or
Player handle, token, cookie, fingerprint, hidden Card, or uploaded document.
Opaque handles may remain in bounded hidden/select values and are never copied
into validation messages. Existing escaping,
loopback binding, Host/Origin checks, app cookie, Content Security Policy,
`Referrer-Policy: origin`, no-CORS, and no-external-request boundaries remain
unchanged.

## Packaging And Verification

The implementation consists of private `skatmind.app_web` modules plus the
existing packaged German/English catalogs and `app.css`. Wheel and sdist
discovery includes the Python modules automatically; existing Package Resource
rules include the changed catalogs and stylesheet.

Focused tests cover immutable contracts, exact registry coverage, safe-value
limits, feedback lifecycle, exact form-instance targeting, repeated-select order,
German/English render-time translation, accessibility, accepted Result
retention, contextual Analyze/Review/Session/Match/Learning responses, upload
reselection, POST/Redirect/GET, standalone regression, and Package discovery.
Issue #219 adds profile-driven creation/settings, language-switch retention,
exact repeated-form identity, Advanced-field opening, and Product-first/profile-
second failure coverage.

## Current Boundary

Issue #218 implements the validation-preservation policy and further partially
remediates `UAT-FINDING-001`. Its assigned implementation for
`UAT-FINDING-006` is complete, but that finding remains open until repeated
maintainer UAT-01. UAT-02 through UAT-12 remain paused; B-09 and B-07 remain
open; Package `1.0.0` and Release preparation remain not ready.

Issue #219 integrates profile-driven Session, Match, and Learning creation,
friendly fields, generated internal IDs, known-Player selection, saved defaults,
and local display labels into this validation layer. Its implementation is
documented in [Profile-driven stateful creation](profile_driven_stateful_creation.md).
Issue #220 is the exact next action and retains task-first active-workflow layout
and complete workflow translation ownership.
