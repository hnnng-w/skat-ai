# Observed Game capture contracts

Issue #161 extends the internal Match Capture foundation with immutable
version-1 contracts for one evidence-aware observed Game and caller-authored
free-text Decision commentary. The primary source is a post-game video, but the
contracts retain only caller-supplied observations and do not depend on a video
platform or network integration.

## Contract identity

The independent versions and policies are:

```text
OBSERVED_GAME_CONTRACT_VERSION = 1
OBSERVED_PLAY_VERSION = 1
OBSERVED_GAME_EVIDENCE_VERSION = 1
DECISION_COMMENTARY_VERSION = 1
DECISION_RESPONSE_LINK_VERSION = 1

OBSERVED_GAME_FACT_POLICY =
    caller_observed_without_hidden_completion
OBSERVED_GAME_TRACE_POLICY =
    chronological_public_play_trace
OBSERVED_GAME_EVIDENCE_POLICY =
    derived_from_retained_observations
DECISION_COMMENTARY_POLICY =
    free_text_without_required_taxonomy
DECISION_RESPONSE_LINK_POLICY =
    later_observed_decision_reference
```

These versions are independent from Match Capture, Historical Game, Session,
Dataset, Public API, Schema, and Package versions. Package version remains
`0.14.0`.

## Match linkage and Game Players

`build_observed_game_record_v1()` receives one exact
`MatchCaptureDefinitionV1`. It derives the retained `match_id` and perspective
Player from that Match rather than accepting duplicates from the caller.
`match_position` must be from `1` through the named Match format's Game count.

The caller supplies the Match participant IDs in per-Game historical seat order.
The builder requires the exact three Match IDs and creates
`ObservedGamePlayerV1` values in this canonical order:

```text
forehand
middlehand
rearhand
```

The Game Player values contain only `player_id` and `seat`. Match labels,
platform IDs, statistics snapshots, source URL, title, and channel remain in the
Match definition and are not copied into each Game. A later Workspace layer must
validate 36er seat rotation and Game-slot relationships.

## Observed versus derived facts

`ObservedGameRecordV1` retains:

```text
observed_game_contract_version
game_id
match_id
match_position
game_timecode
players
perspective_player_id
perspective_initial_hand
declarer_player_id
declaration
original_skat
discarded_cards
plays
commentaries
response_links
```

The record stores no derived Trick number, Play index, winner, points, next
Player, legal-card set, Result, Value, Overbid, Settlement, recommendation,
Decision quality, tactical category, or generated metadata. Derived trace facts
are validated and returned separately from the trace layer. Missing Card facts
remain null; a complete trace's two-card complement is never written into a
missing original-Skat or Discard field.

## Perspective hand, Skat, and Discards

`perspective_initial_hand` is null or exactly ten unique Cards. It represents the
original dealt hand visible for the Match perspective Player only. No opponent
initial hand is accepted. `original_skat` is null or exactly two unique Cards.
Both arrays use canonical full-deck order and must be disjoint when present.

`discarded_cards` has three distinct states:

```text
null:
    Discards were not observed
empty array:
    known Hand Game with no Discards
two Cards:
    known exact non-Hand Discards
```

Known discarded Cards cannot appear in Plays. Original-Skat Cards are not
generally excluded from Plays because they may enter the non-Hand Declarer's
playable hand. An original-Skat Card may also be discarded again; original Skat
and Discards are separate facts and may overlap.

The Declarer and existing validated `GameDeclaration` are both null or both
present. Any retained Play requires both. The declaration reuses existing Suit,
Grand, Null, Hand, Ouvert, announcement, Matador, and bid validation unchanged.

## Partial Play traces

`ObservedPlayV1` retains one positive contiguous `decision_index`, one exact Game
Player, one valid Card, and an optional `MediaTimecodeV1`. The Game record
preserves zero through 30 Plays in caller-observed chronological order and adds
no padding or synthetic events.

Every trace validates:

* contiguous one-based Decision indexes;
* unique played Cards;
* at most ten Plays per Player;
* Forehand as the first leader;
* circular historical seat order within each Trick;
* the existing rule winner as the next Trick leader;
* at most one incomplete final Trick;
* non-decreasing starts among present Decision timecodes.

For an incomplete trace, exact ownership and `get_legal_cards()` are enforced
only when the perspective playable hand is known exactly. A Defender's or Hand
Declarer's observed initial hand is already the playable hand. A non-Hand
Declarer's playable hand is exact only when the perspective initial hand,
original Skat, and Discards are all known. Unknown opponent hands are never
created, and an opponent Play is not rejected solely because unknown ownership
cannot prove Bedienpflicht.

## Complete Play traces

A complete trace contains exactly 30 unique Plays, ten per Player, and ten
complete Tricks. The trace validator groups each Player's ten observed Cards as
that Player's exact playable starting hand and replays every Decision through the
existing legal-card and Trick rules. Illegal Suit, Grand, or Null traces are
rejected.

For a complete Hand trace, each playable hand is also that Player's original
hand. A known original Skat must equal the two unplayed Cards, and known Discards
must be empty.

For a complete non-Hand trace, a known Discard array must equal the two unplayed
Cards. The reconstructed Declarer playable hand is not automatically described
as the original dealt hand. The original Declarer hand is reconstructed only
when original Skat and Discards are both retained:

```text
original Declarer hand = playable hand + discarded Cards - original Skat
```

A known Defender perspective hand must equal that Defender's complete playable
hand. A known Hand Declarer perspective hand must equal the complete Declarer
playable hand. A known non-Hand Declarer perspective hand is reconciled with the
formula only when both original Skat and Discards are known. Missing Card fields
remain missing after every check.

## Timecodes

Game, Decision, and commentary timecodes reuse `MediaTimecodeV1`. A Game
timecode must lie inside Match source bounds when both are present. Decision and
commentary timecodes must lie inside Game bounds when both are present. Equal
starts are valid, individual Decision or commentary timecodes may be null, and
commentary may occur later than its subject Decision.

No formatted time string or current timestamp is generated.

## Free-text Decision commentary

`ObservedDecisionCommentaryV1` attaches authoritative caller text to any
retained Player Decision. The `subject_player_id` must equal the referenced
Play's Player, so commentary can target the perspective Player or either
opponent.

A commentator may be identified by:

* one Match `commentator_player_id`;
* one descriptive external `commentator_name`;
* both a Match Player ID and a descriptive name.

At least one identity is required. Commentary text is non-empty and non-padded,
while internal whitespace and line breaks are preserved exactly. Version 1 does
not require or infer sentiment, error type, suit signal, requested action,
strategic value, optimality, or another tactical taxonomy.

Commentaries are canonicalized by subject Decision index, present commentary
timecode start, then commentary ID. Present timecodes sort before missing
timecodes for the same Decision.

## Linked later responses

`ObservedDecisionResponseLinkV1` links one retained commentary item to one later
retained Decision index. One commentary may have multiple later links. Link IDs
and commentary/response pairs are unique. Links are canonicalized by referenced
commentary order, response Decision index, then link ID.

The response Player is available through the referenced Play and is not copied
into the link. A link records only caller association. It does not prove
causality, a correct partner response, tactical meaning, strategic value,
success, failure, or optimality.

## Evidence summary

`build_observed_game_evidence_summary_v1()` revalidates the retained trace and
builds `ObservedGameEvidenceSummaryV1` without constructing an Engine Request.
It contains exact counts, known-fact flags, annotation counts, and four
capability flags.

`complete_play_trace` is true only for one legal 30-Play, ten-Trick trace with
ten Plays per Player. `all_player_decision_samples_reconstructable` is true only
for that complete trace.

`perspective_decision_samples_reconstructable` is true when the complete trace
provides the perspective playable hand or when the retained perspective initial
hand has an exact known Hand/non-Hand transformation.

`discard_review_reconstructable` is true only for a non-Hand Game with exact
original Skat and Discards plus an exact original Declarer hand. The original
hand may come directly from a visible Declarer perspective hand or from a
complete trace with the reconstruction formula.

`complete_initial_deal_reconstructable` is true only for a complete legal trace,
known original Skat, and exact known Discard evidence. For Hand, exact Discard
evidence is the retained empty array. The summary describes evidence capability;
it does not claim that Historical, Session, review, or Dataset materialization
has occurred.

## Serialization and boundaries

Every value is frozen, slotted, keyword-only, and defensively copied. Aggregate
Game and evidence values are builder-only so Match and trace validation cannot be
bypassed through ordinary construction. Serialization uses stable field order,
explicit nulls, canonical Players and Card sets, chronological Plays, canonical
annotations, and fresh mutable JSON-compatible output.

Issue #161 executes no Search, Immediate Analysis, Review, Coaching, Dataset
generation, profile derivation, Session operation, Historical construction,
Settlement, or list aggregation. It adds no persistence, Public Match API, Root
workflow, Schema, CLI, example, generated scenario, Workspace, rapid-entry
service, HTTP server, or UI. The Package remains `0.14.0` with seven Root
workflows, 63 authoritative and packaged Schemas, and 85 generated-output
scenarios.
