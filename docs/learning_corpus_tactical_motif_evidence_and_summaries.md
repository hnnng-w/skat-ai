# Learning Corpus Tactical Motif evidence and summaries

Issue #195 adds a separate private Learning Corpus Tactical Motif Evidence
family and a descriptive cross-game Summary. It reuses the exact deterministic
single-game detector from Issue #194 over explicit Current Match Snapshots. It
does not run Historical Application analysis, Search, Coaching, a Profile,
Commentary interpretation, or Strategy Teacher preparation.

The family is process-local and non-persisted. It adds no Corpus object kind,
Catalog field, Public API, Root workflow, Schema, example, generated-output
scenario, Package-version change, or Learning Dataset version `2` change.
Package `0.16.0`, Public API contract version `1`, seven Root workflows, one
Console Script, 71 authoritative and packaged Schemas, six Session examples, and
98 generated-output scenarios remain unchanged.

## Source boundary

The only source is the exact strict Learning Corpus Store and its explicit
Current Match Snapshot selection:

```text
LearningCorpusStoreResumeResultV1
    -> explicit Current Match Snapshots only
    -> safe reconstructed Decisions or explicit skips
    -> exact shared Tactical detector
    -> Tactical Motif Evidence Collection
    -> exact Player Catalog reconciliation
    -> Tactical Motif Cross-game Summary
```

Retained non-current Match Snapshots and valid orphan objects do not contribute.
Changing the Current selection changes the source. The builder retains the
source Catalog revision, Catalog fingerprint, Catalog content fingerprint,
ordered Current Match Snapshot IDs, and retained, Current, and orphan Snapshot
counts so the source boundary can be reconciled exactly.

The Tactical family remains separate from both other evidence families:

* Human Evidence preserves caller-supplied Commentary and Response associations.
* Strategy Teacher Evidence preserves method-bound executed Decision Analysis
  Report evidence.
* Tactical Motif Evidence preserves deterministic structural observations from
  recorded Cards.

No family is merged into, preferred over, or interpreted through another.

## Evidence and explicit skips

Every observed Decision in every observed Game of a Current Match Snapshot is
accounted for exactly once as either:

* one `LearningCorpusTacticalMotifEvidenceV1`; or
* one `LearningCorpusSkippedTacticalMotifDecisionV1`.

Evidence is created only when the existing Match Decision-state seam can safely
reconstruct the acting Player's decision-time state. A skip reuses the existing
bounded Match reasons:

```text
acting_hand_unavailable
required_public_hand_unavailable
```

A skipped value retains exact Snapshot, Game, Decision, Player, role, seat,
Trick, play-index, contract, and reason context. It contains no actual Card and
does not infer the missing state or motif.

Collection status is exact coverage status:

```text
empty       no observed Decision exists
partial     at least one observed Decision exists and at least one is skipped
complete    observed Decisions exist and none is skipped
```

An all-skipped non-empty collection is therefore `partial`, not `empty` or an
inferred complete collection. Counts reconcile as:

```text
observed_decision_count = evidence_count + skipped_decision_count
evidence_count = complete_observation_count + partial_observation_count
```

An observed Game with no recorded play contributes to `observed_game_count` but
creates no Evidence or skip.

## Shared exact detector

Issue #195 calls
`build_tactical_decision_observation_from_snapshot_v1()` directly. This is the
same pure detector used by the Issue #194 Historical Tactical Motif Review. The
Corpus layer does not copy, fork, broaden, or reinterpret the taxonomy.

The exact families and 16 motif types remain those documented in
[Tactical motif evidence](tactical_motif_evidence.md):

```text
lead_structure
void_response
trick_control
defender_partnership
hand_shape
trick_outcome
```

Decision-time facts are constructed before the actual Card is attached. The
actual Card and immediate after-play facts are retrospective evidence. Completed-
Trick winner, side, points, and outcome motifs are attached only when the source
trace contains that completed Trick.

## Partial Match safety

Partial observed Games and partial Matches are valid sources. The builder
validates each Current Workspace and observed trace, reconstructs only safe
Decision states, emits Evidence for those Decisions, and emits explicit skips
for the rest. It does not require strict Historical Game materialization and does
not complete missing hands, Skat, Discards, future plays, or hidden ownership
from deck complements.

The final recorded Trick may be incomplete. A safely reconstructable Decision in
that Trick receives an Observation with status `partial`, null completed-Trick
fields, and no `after_trick_completion` motif. Its valid decision-time and after-
play motifs remain available. Earlier completed Tricks and all Decisions in a
completed final Trick retain status `complete` and exact completed-Trick facts.

This behavior is independent of Match structural completion. Empty Slots and
Passed Deals create no observed Game, Decision, Evidence, or skip.

## Versions and policies

The ten Issue #195 contract, export, and prepared-artifact versions are
independently `1`:

```text
Learning Corpus Tactical Motif Evidence
Learning Corpus skipped Tactical Motif Decision
Learning Corpus Tactical Motif Collection
Learning Corpus Tactical Motif Scope Summary
Learning Corpus Tactical Motif Player Summary
Learning Corpus Tactical Motif Recurrence
Learning Corpus Tactical Motif Cross-game Summary
Learning Corpus Tactical Motif Evidence Export
Learning Corpus Tactical Motif Summary Export
Learning Corpus Tactical Prepared Artifacts
```

The exact policy boundaries are:

```text
explicit_current_match_snapshots_only
safe_reconstructed_decision_or_explicit_skip
reuse_exact_tactical_detector_without_search_or_coaching
exact_snapshot_game_and_decision_reference_identity
every_observed_decision_is_evidence_or_skipped
distinct_game_and_match_counts_without_trait_inference
exact_counts_without_rates_quality_or_significance
tactical_human_and_strategy_evidence_remain_separate
no_learning_dataset_v2_contract_or_record_mutation
process_local_explicit_generation_safe_preparation
deterministic_path_free_private_json
private_corpus_downloads_without_public_schema_or_api
```

## Deterministic identities

Every Issue #195 Evidence ID, skipped-Decision ID, Scope Summary ID, Player
Summary ID, Recurrence ID, collection fingerprint, Summary fingerprint, and
export ID is SHA-256 over a distinct version-1 domain prefix and finite canonical
Learning Corpus JSON. Canonical identity JSON uses UTF-8, ASCII escaping, finite
values, sorted keys, and compact separators.

An Evidence ID covers the exact Snapshot/Game/Decision references, Workspace
revision, logical Match/Game identities, position/index, acting Player, actual
Card, and complete safe Tactical Observation. A skipped-Decision ID covers its
same exact source context and skip reason. Collection and Summary fingerprints
cover their complete values except the fingerprint field itself.

Source order is deterministic: Current Snapshot order, Match position, then
Decision index. Player Summaries follow exact Player Catalog order. Motif,
family, role, seat, phase, and contract tuples use their canonical orders.
Identifiers provide content identity and reconciliation, not confidentiality,
authorship, quality, or Confidence.

## Exact descriptive counts

The Evidence Collection reports exact observed Game and Decision coverage,
Evidence and skip counts, complete and partial Observation counts, total motif
occurrences, and complete zero-preserving motif and family counts.

The separate `LearningCorpusTacticalMotifCrossGameSummaryV1` validates the exact
Collection and exact Current-Snapshot Player Catalog without rebuilding either.
It reports the same exact global coverage plus:

* occurrence Counts for every motif and family;
* distinct Game Counts for every motif, using Snapshot-scoped Game Reference
  identity;
* distinct logical Match Counts for every motif;
* one Summary for every exact stable Player in Player Catalog order;
* complete global and per-Player role, seat, phase, and contract scope tuples;
* one recurrence value for every observed `(player_id, motif_type)` pair.

Each global or per-Player scope Summary reports exact Decision, Evidence, skip,
complete/partial Observation, motif occurrence, distinct Game, distinct Match,
per-motif occurrence, per-motif Game, per-motif Match, and family Counts. Scope
groups partition all Decisions and reconcile to their parent totals.

The exact scope values are:

```text
role:      declarer, defenders
seat:      forehand, middlehand, rearhand
phase:     opening, middle, endgame
contract:  clubs, spades, hearts, diamonds, grand, null
```

Opening is Tricks 1 through 3, middle is Tricks 4 through 7, and endgame is
Tricks 8 through 10. Counts include zero-valued canonical categories. They are
integers only: no rates, percentages, averages, scores, grades, thresholds, or
significance values are derived.

Game and Match Counts are intentionally distinct. Repeated motif occurrences in
one Game increase the occurrence Count but not that motif's distinct Game Count.
Occurrences in multiple Games of one logical Match increase Game Count while
Match Count remains one. Snapshot-scoped Game Reference identity prevents equal
source Game IDs in different Snapshots from being treated as one Game.

## Recurrence scopes

Recurrence is descriptive grouping by exact stable Player ID and motif type. The
exact scopes are:

```text
single_game_only
multiple_games_one_match
multiple_matches
```

`multiple_matches` applies when the Player/motif pair occurs in at least two
logical Matches. Otherwise `multiple_games_one_match` applies when it occurs in
at least two distinct Game References. Every other positive occurrence group is
`single_game_only`.

Each recurrence retains occurrence and Decision Counts, distinct Game and Match
Counts, exact Evidence IDs, Game Reference IDs, Game IDs, and Match IDs.
One motif type can occur at most once per Decision, so recurrence occurrence and
Decision Counts are equal. A recurrence, including `multiple_matches`, is not a
Player trait, tendency, skill estimate, stable behavior, recommendation, or
statistical result.

## Interpretation boundary

The collection and Summary are factual structural descriptions only. They make
no claim about:

* tactical quality, correctness, optimality, mistakes, or preferred play;
* Player traits, ratings, rankings, tendencies, or skill;
* intent, signaling, communication, partnership understanding, or causality;
* probability, representativeness, calibration, rates, or statistical
  significance;
* Strategy Teacher quality, Teacher preference, model readiness, or model
  training;
* cross-game Coaching, Guidance, or Recommendations inside Issue #195 artifacts.

The actual Card is observed behavior, not ground truth. Missing Decisions are
explicit skips and are never imputed. Issue #196 supplies a separate exact
Tactical/Teacher join and bounded complete-Search Coaching contract without
mutating or reinterpreting these structural source artifacts.

## Learning Dataset version 2 compatibility

Learning Dataset version `2` is unchanged. Tactical Motif Evidence is not a new
Dataset-v2 input, evidence family, Record sibling, normalized pool, join,
Coverage family, partition fact, Summary field, target, label, Feature, or task.
The existing Dataset builder still consumes exactly the Store, Player Catalog,
Human Evidence Collection, and Strategy Teacher Evidence Collection.

Human, Strategy Teacher, and Tactical Evidence may describe the same source
Decision through separate exact identities, but Issue #195 creates no cross-
family join. Issue #196 performs a separate private Coaching join outside the
Dataset. Existing Dataset-v2 bytes change only when their existing sources
change, not because Tactical preparation is enabled.

## Explicit process-local preparation

The existing `Prepare Learning Artifacts` browser action remains the only
preparation trigger. It now builds, once and in order:

1. Current-Snapshot Player Catalog.
2. Current-Snapshot Human Commentary and Response Evidence.
3. Current-Snapshot-bound Strategy Teacher Evidence.
4. Unpartitioned Learning Dataset version `2`.
5. Known-player partition Result.
6. Unseen-player partition Result.
7. Dataset-v2 Cross-game Summary.
8. Current-Snapshot Tactical Motif Evidence Collection.
9. Tactical Motif Cross-game Summary from that exact Collection and Player
   Catalog.
10. Tactical Cross-game Coaching Report from the exact retained Tactical,
    Strategy Teacher, and Player Catalog values.

The first seven Issue #179 artifacts and their contracts are unchanged. The two
Tactical artifacts are held in a separate immutable process-local family but are
published with the existing family and the separate Coaching family as one
complete prepared generation.
Preparation executes no Match Analysis, Position, Historical, Training Dataset,
Search, Profile derivation, or other Root workflow. Coaching construction uses
only retained evidence and executes no analysis or Tactical detection.

## Atomic publication and invalidation

Preparation runs outside the synchronized context lock. Before publication, it
rechecks the exact retained Store object, Catalog revision, Catalog content
fingerprint, Strategy Teacher source-store revision, and context generation. A
change to any source returns `source_changed` with HTTP `409`, invalidates all
three prepared families, and publishes none. There is no retry or partial
Tactical-only, Coaching-only, or Dataset-only publication.

Successful publication requires all three families to share the exact Catalog
revision and content fingerprint, and requires the Tactical Summary to use the
same Player Catalog fingerprint as the existing prepared family. Applied
Workspace import, applied Current-selection change, applied Strategy source add/
remove/clear, successful Reload, source change during preparation, and shutdown
invalidate all three families together. No-change/conflicted operations and
failed Reload preserve all still-matching families. A successful preparation
replaces all three with the new exact generation.

Downloads verify the retained Store object, context generation, Strategy source
revision, Catalog revision/content fingerprint, and shared Player Catalog
fingerprint. Missing artifacts return HTTP `404`; a detected source mismatch
returns HTTP `409`. Downloading never rebuilds an artifact, writes a server file,
or mutates the Corpus.

## Minimized dashboard

The server-rendered dashboard adds only these Tactical preparation facts:

```text
collection status
Evidence count
skipped Decision count
motif occurrence count
Player Summary count
recurrence count
```

It does not display individual Tactical Observations, actual Cards, per-Player
motif counts, recurrence identities, complete hands, legal-Card sets, hidden
ownership, Commentary, Strategy Teacher values, source JSON, fingerprints, or
paths. The dashboard remains a private minimized projection, not a public
redaction boundary.

## Tactical authenticated downloads

Issue #179 historically introduced seven authenticated canonical downloads.
Issue #195 adds exactly two more, bringing its prepared baseline to nine. Issue
#196 adds a separate tenth Coaching download without changing these two routes:

| Artifact | Route | Filename suffix |
| --- | --- | --- |
| Tactical Motif Evidence | `/downloads/tactical-motif-evidence.json` | `tactical-motif-evidence` |
| Tactical Motif Cross-game Summary | `/downloads/tactical-motif-cross-game-summary.json` | `tactical-motif-cross-game-summary` |

Both use `corpus_id` as the readable source ID and their deterministic export ID
as artifact identity. They follow the existing ASCII-safe filename contract:

```text
<safe-source-id>-<artifact-suffix>-<identity-first-12>.json
```

The Evidence document kind is
`skat_ai_learning_corpus_tactical_motif_evidence`. The Summary document kind is
`skat_ai_learning_corpus_tactical_motif_cross_game_summary`. Both are path-free,
finite UTF-8 JSON with ASCII escaping, two-space indentation, LF line endings,
and exactly one trailing LF. Routes require the existing authenticated cookie
and valid loopback Host and expose no server path or query option.

## Privacy and persistence

Current Match Snapshots remain private local unredacted source data and may
contain complete cards, Skat, Discards, Commentary, Statistics, URLs, titles, and
timecodes. The Tactical exports are also private local artifacts. Their safe
structural observations still contain stable Player/Match/Game/Decision
identities, actual Cards, public Trick structure, and motif facts that can be
sensitive in aggregate.

Issue #195 adds no public-redaction, confidentiality, encryption, account,
access-control, authorship, remote-storage, cloud, backup, or secure-deletion
claim. Loopback authentication reduces accidental local exposure but does not
make downloads public or provide multi-user authorization.

The Evidence Collection, Cross-game Summary, prepared wrapper, and downloads are
never added to `catalog.json`, Match Snapshot objects, source Workspaces, or
another persisted file. They disappear on invalidation or server shutdown.
The separate Coaching artifact consumes exact retained values but does not alter
these bytes or identities. See [Learning Corpus Tactical Cross-game
Coaching](learning_corpus_tactical_cross_game_coaching.md).
Deletion, garbage collection, derived-artifact persistence, Public API/Schema
transport, Dataset-v2 joins, broader tactical quality beyond retained complete-
Search evidence, Player Ratings, and causal interpretation remain separate future
work.
