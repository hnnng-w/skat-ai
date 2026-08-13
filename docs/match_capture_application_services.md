# Match Capture Application services

Issue #164 adds the internal transport-free rapid-entry Application foundation
for one `euroskat_36_standard_v1` Match Workspace. The services receive one
already loaded immutable `MatchWorkspaceV1`, apply at most one existing Workspace
change, and return an immutable Capture Result and a derived current-position
View. They perform no file, network, Root workflow, Public API, CLI, browser,
analysis, or materialization operation.

## Contract identity

The independent versions are:

```text
MATCH_CAPTURE_APPLICATION_VERSION = 1
MATCH_CAPTURE_POSITION_VIEW_VERSION = 1
MATCH_CAPTURE_APPLICATION_RESULT_VERSION = 1
```

The exact policies are:

```text
MATCH_CAPTURE_APPLICATION_POLICY =
    transport_free_workspace_observed_game_updates

MATCH_CAPTURE_GAME_ID_POLICY =
    match_id_plus_zero_padded_position

MATCH_CAPTURE_ANNOTATION_ID_POLICY =
    match_id_position_workspace_revision

MATCH_CAPTURE_CARD_SELECTION_POLICY =
    exclude_only_observed_or_proven_unavailable_cards

MATCH_CAPTURE_TRUNCATION_POLICY =
    remove_suffix_and_invalid_annotations

MATCH_CAPTURE_INFORMATION_POLICY =
    no_hidden_completion
```

These versions remain independent from Package version `0.14.0`, Public API,
Match Capture, observed-Game, Workspace, Session, Historical Game, Dataset,
Provenance, Schema, and Domain versions.

## Operations and statuses

The canonical operations are:

```text
start_game
set_game_timecode
set_perspective_hand
set_declaration
set_original_skat
set_discarded_cards
append_plays
truncate_plays
set_commentary
remove_commentary
set_response_link
remove_response_link
mark_passed_deal
clear_position
```

Every operation returns one of:

```text
applied
unchanged
revision_conflict
```

Revision conflicts precede operation-specific payload validation and return the
source Workspace plus a View derived from it. Applied operations increment the
Workspace revision exactly once. Unchanged operations preserve the source
revision and Workspace. The service layer does not implement retry, merge,
autosave, or a persistent Undo log.

## Card entry

`MatchCaptureCardEntryV1` contains only:

```text
card
decision_timecode
```

The Card must use the existing Skat notation. The optional timecode reuses
`MediaTimecodeV1`. A caller never supplies Player ID, Decision index, Trick
number, Play index, or next Player. Batch and single-Card append derive those
facts from the retained trace and existing rules.

## Position View

`build_match_capture_position_view_v1()` validates one exact Workspace revision
and derives `MatchCapturePositionViewV1`. The View contains:

```text
Match identity, revision, position, and round
Slot kind and capture state
Dealer and Forehand/Middlehand/Rearhand rotation
perspective, Game, and Declarer identities
Play and Trick counts
chronological current-Trick Players and Cards
next Player and Historical-seat Player Play counts
chronological played Cards
Card-selection scope and selectable Cards
record-Play blockers and truncation availability
observed-Game Evidence Summary
Workspace Progress
```

The View is derived and is never persisted. It contains no path, transport
value, hidden ownership, Analysis Result, Result, Settlement, recommendation, or
tactical interpretation.

## Capture states and blockers

The exact capture states are:

```text
empty
setup
ready_for_play
play_in_progress
play_complete
passed_deal
```

`setup` is an observed Game with no Declaration and no Plays.
`ready_for_play` has a Declarer and Declaration but no Plays.
`play_in_progress` has one through 29 Plays. `play_complete` has one legal
30-Play trace. This state is distinct from Workspace `complete`, which only means
that all 36 Slots are classified, and from evidence-reconstruction capabilities.

The canonical blockers are:

```text
empty_slot
passed_deal
missing_declaration
complete_play_trace
```

`can_record_play` is true exactly when no blocker applies.
`can_truncate_plays` is true exactly when the observed Game has at least one
Play. A complete trace has no next Player in the Capture View even though the
lower trace summary retains its final winner for rule reconstruction.

## Selectable Cards

The exact Card-selection scopes are:

```text
unavailable
exact_legal_cards
bounded_observation_candidates
```

Selection is unavailable when another Play cannot be recorded.

`exact_legal_cards` is used only when the next Player's current playable hand is
known exactly. Version 1 obtains that exact hand for the perspective Player when
the retained evidence is one of:

* a Defender perspective initial hand;
* a Hand Declarer perspective initial hand;
* a non-Hand Declarer perspective initial hand plus original Skat and exact
  Discards.

Already played Cards are removed, and the existing `get_legal_cards()` helper
applies Bedienpflicht against the current Trick. Output uses canonical deck
order.

`bounded_observation_candidates` is used when the next Player's exact hand is
unknown. It starts from the canonical deck and removes only Cards proven
unavailable through retained evidence:

* already played Cards;
* known Discards;
* known remaining perspective Cards when another Player acts;
* known Hand-game original Skat;
* known non-Hand original-Skat Cards when a Defender acts.

Unknown opponent ownership and unproved Bedienpflicht are not inferred. A
bounded candidate is a possible observation palette entry, not an assertion that
the Player owns the Card or can legally play it.

## Starting and setup updates

The default Game ID is deterministic:

```text
{match_id}-game-{match_position:02d}
```

Starting a Game derives historical seats through the existing Workspace
rotation and creates an observed Game with unknown hand, Declaration, original
Skat, and Discard evidence plus empty Plays and annotations. Starting an empty or
passed position is allowed. Starting an existing observed Game is unchanged only
when requested identity and timecode match; it never erases retained evidence.

Focused updates set or clear Game timecode, perspective initial hand,
Declaration, original Skat, and Discards. Every update retains all other fields,
rebuilds the complete candidate through `build_observed_game_record_v1()`, and
sets it through `set_match_workspace_observed_game_v1()`. Existing time,
ownership, declaration, trace, and complete-card reconciliation remains
authoritative.

## Play append and truncation

Single-Card append delegates to atomic batch append. Batch append:

1. validates a non-empty ordered Card-entry tuple;
2. derives each one-based Decision index;
3. derives each acting Player from retained and newly appended Plays;
4. reuses the existing Trick winner rules for each completed Trick;
5. builds one final observed-Game candidate;
6. applies one Workspace change.

Duplicate Cards, invalid chronology, ownership conflicts, Bedienpflicht
violations supported by exact evidence, and traces over 30 Plays reject the
whole batch without changing the source Workspace.

Truncation keeps an exact chronological prefix. It removes commentary whose
Decision no longer exists and response links that reference removed commentary
or removed response Decisions. Still-valid annotations remain. Removed IDs are
reported in deterministic retained order. Undo-last-Play is a convenience
wrapper over the same truncation operation; it adds no history object.

## Commentary and response links

Commentary remains caller-authored free text without taxonomy, sentiment,
tactical category, error label, signal, optimality, or AI interpretation. The
service derives its subject Player from the referenced Play. Match-Player,
external-name, and combined commentator identities reuse the existing contract.

Default annotation identities are:

```text
{game_id}-commentary-r{next_workspace_revision}
{game_id}-response-r{next_workspace_revision}
```

Explicit valid IDs are also accepted. An explicit existing ID replaces that
annotation. Equal replacement is unchanged. Commentary replacement removes only
links that are no longer later than the replacement subject Decision. Removing
commentary cascades to all links that reference it.

Response links continue to represent only a caller association with a later
retained Decision. They make no causal, tactical, correctness, or strategic
claim. Explicit existing Link IDs can be replaced; duplicate
Commentary/response pairs remain invalid.

## Passed Deals and clearing

Passed Deal and clear services wrap the existing Workspace operations. They
preserve replacement, unchanged, and revision-conflict behavior, create no
synthetic observed Game, and return a Position View and Progress for the returned
Workspace.

## Application Result

`MatchCaptureApplicationResultV1` contains:

```text
match_capture_application_result_version
operation
status
workspace_change
position_view
removed_commentary_ids
removed_response_link_ids
affected_commentary_id
affected_response_link_id
```

The status equals the nested `MatchWorkspaceChangeResultV1` status. The View
uses the returned Workspace and affected position, and Progress is available as
`position_view.workspace_progress`. Annotation effects are immutable tuples or
nullable exact IDs. Serialization is deterministic and returns fresh mutable
JSON-compatible containers.

## Architecture and current boundary

The dependency direction is:

```text
Domain and rules
    <- Application and Public APIs
        <- Capture Application services
            <- local Capture CLI and browser transport
```

Capture services do not import CLI or browser code. CLI modules do not own
Capture rules. Services perform no Workspace Load or Save, file autosave,
network access, Session operation, Historical construction, Position or
Historical analysis, Search, Review, Replay Coaching, Dataset generation, list
aggregation, Opponent Profile derivation, or background work.

Issue #165 composes these services into the private local loopback browser and
Capture CLI with optimistic autosave; this does not change the transport-free
service contract. Issue #166 adds a separate Match Player Statistics update
layer that the browser composes alongside, not into, these canonical Capture
Application operations. These services still perform no Statistics conversion,
Profile derivation, or Profile application. Future work includes Public Match
API, Match Schema/data workflow, Profile application, analysis, report export,
and browser execution controls. Issue #167 adds separate internal Decision,
Historical, unpartitioned Training-source, and complete fixed-list preparation;
it is not part of these mutation services and executes no workflow. YouTube and
EuroSkat integration remain absent. Package version
`0.14.0`, seven Root workflows, 63 authoritative and packaged Schemas, current
examples, and 85 generated-output scenarios remain unchanged.
