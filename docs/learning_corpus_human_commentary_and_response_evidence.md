# Learning Corpus human Commentary and Response evidence

Issue #174 adds a private internal deterministic export of minimized original
human Commentary and explicitly linked observed Response behavior. It is the
Human Evidence foundation for the active
`v0.16.0 - Learning-ready behavior and communication data` milestone.

The export is derived data. It does not change Match Snapshots, Catalog fields,
Current selections, Corpus persistence, Match Workspace persistence, Session
persistence, Match Analysis, Training Dataset version `1`, or a public contract.

## Source boundary

`build_learning_corpus_human_evidence_collection_v1()` accepts one exact
in-memory `LearningCorpusStoreResumeResultV1`. It strictly reconstructs the
Catalog document once, strictly validates the Store once, and resolves only the
Match Snapshots explicitly selected by:

```text
LearningCorpusCatalogV1.current_matches
```

Current Matches remain in Match-ID order. Retained non-current revisions and
valid orphan Match Snapshot objects do not contribute evidence. The builder does
not change a Current selection or infer a newest Snapshot.

The narrow shared Current-Snapshot resolver is also used by the existing Player
Catalog. Human Evidence does not import or derive that Player Catalog, aliases,
Statistics history, Profiles, or policy values.

## Versions and tuples

The five independent internal versions are:

```text
LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION = 1
LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION = 1
LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION = 1
LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION = 1
LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION = 1
```

The evidence kinds are:

```text
LEARNING_CORPUS_HUMAN_EVIDENCE_KINDS = (
    commentary,
    linked_response,
)
```

The commentator identity kinds are direct source-nullability facts:

```text
LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS = (
    match_player,
    external,
    match_player_and_external,
)
```

No identity kind performs Player resolution, alias lookup, fuzzy matching, or
canonical-label selection.

## Policies

The ten exact policies are:

```text
LEARNING_CORPUS_HUMAN_EVIDENCE_SOURCE_POLICY =
    explicit_current_match_snapshots_only

LEARNING_CORPUS_HUMAN_TEXT_POLICY =
    preserve_exact_human_text_without_normalization_or_taxonomy

LEARNING_CORPUS_RESPONSE_RELATION_POLICY =
    caller_linked_later_observed_decision_without_causal_claim

LEARNING_CORPUS_OBSERVED_BEHAVIOR_POLICY =
    actual_cards_are_observed_behavior_not_optimal_labels

LEARNING_CORPUS_MEDIA_CONTEXT_POLICY =
    retain_descriptive_source_metadata_and_exact_timecodes

LEARNING_CORPUS_DERIVED_TAG_POLICY =
    no_derived_tags_in_version_1

LEARNING_CORPUS_ANALYSIS_SEPARATION_POLICY =
    human_evidence_does_not_influence_analysis_search_or_coaching

LEARNING_CORPUS_HUMAN_EVIDENCE_ORDER_POLICY =
    current_match_game_commentary_response_canonical_order

LEARNING_CORPUS_HUMAN_EVIDENCE_PRIVACY_POLICY =
    private_local_minimized_unredacted_human_evidence

LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_POLICY =
    deterministic_path_free_json_document
```

The export document kind is:

```text
skat_ai_learning_corpus_human_evidence
```

## Canonical identities

All seven new identities reuse the Issue #171 finite canonical JSON contract:

```text
UTF-8
ensure_ascii = true
allow_nan = false
sort_keys = true
separators = (",", ":")
```

The SHA-256 domains are:

```text
skat-ai\0learning_corpus_human_evidence_collection_v1\0
skat-ai\0learning_corpus_human_evidence_game_v1\0
skat-ai\0learning_corpus_commentary_content_v1\0
skat-ai\0learning_corpus_commentary_evidence_v1\0
skat-ai\0learning_corpus_response_content_v1\0
skat-ai\0learning_corpus_response_evidence_v1\0
skat-ai\0learning_corpus_human_evidence_export_v1\0
```

The Commentary content fingerprint covers the exact complete
`ObservedDecisionCommentaryV1.to_dict()` value. Text, line breaks, Unicode,
commentator identities, source Commentary ID, subject Decision, and Commentary
timecode are therefore preserved without normalization.

The Response content fingerprint covers the exact complete
`ObservedDecisionResponseLinkV1.to_dict()` value. It identifies the caller's
original association. The observed response Card and response Decision timecode
come from the referenced Play and remain separate factual fields. A changed
response Card changes the existing Game content and Snapshot-scoped evidence
identity, but not the unchanged source Response Link content fingerprint.

Game, Commentary, and Response Evidence IDs include existing Snapshot-scoped
closed Reference identity. Equal source text in distinct Snapshots may have an
equal source content fingerprint while retaining distinct Evidence IDs.

## Human Evidence Game

`LearningCorpusHumanEvidenceGameV1` exists only for an observed Game containing
at least one Commentary item. It retains:

* Match Snapshot, Game Reference, and exact Game-content identity;
* Match ID, Game ID, Workspace revision, and Match position;
* Match title, game platform, external Match ID, and played time;
* source kind, URL, title, channel, and Match timecode;
* Game timecode and Perspective Player;
* exact Forehand, Middlehand, and Rearhand Player IDs;
* Declarer and the exact existing `GameDeclaration` or null;
* Decision count;
* complete ordered Commentary and Response Evidence child IDs.

It contains no initial hand, remaining hand, original Skat, Discards, Statistics,
Analysis Result, Profile, or full Play trace.

## Commentary Evidence

`LearningCorpusCommentaryEvidenceV1` retains:

* Commentary Evidence ID, exact source content fingerprint, and closed Commentary
  Reference ID;
* parent Game, Match Snapshot, Game Reference, source Commentary, and subject
  Decision identities;
* one-based subject Decision, Trick, and play indexes;
* subject Player ID, nullable exact Match label, seat, and declarer/defender role;
* exact observed subject Card and Decision timecode;
* exact Commentary timecode;
* direct commentator identity kind plus original Player ID and external name;
* exact original multiline human text;
* all ordered linked Response Evidence IDs.

The observed subject Card is behavior evidence. It is not an optimal label,
recommendation, quality assessment, strategy label, or communication tag.

## Response Evidence

`LearningCorpusResponseEvidenceV1` retains:

* Response Evidence ID, source Response Link content fingerprint, and closed
  Response Reference ID;
* parent Game, Match Snapshot, Game Reference, source Link, Commentary Evidence,
  and Commentary Reference identities;
* subject and response Decision Reference IDs and one-based indexes;
* response Trick and play indexes;
* response Player ID, nullable exact Match label, seat, and role;
* exact observed response Card and response Decision timecode;
* positive Decision offset;
* the factual same-Trick boolean.

A Response Link remains only a caller association. Human Evidence does not infer
signaling, understanding, causality, correctness, success, quality, or strategic
meaning.

## Collection and ordering

`LearningCorpusHumanEvidenceCollectionV1` retains exact Corpus and Catalog
identity, Current Match Snapshot IDs, retained/current/orphan Snapshot counts,
and reconciled counts for:

* all Current observed Games;
* evidence Games;
* all Current observed Decisions;
* distinct commented Decisions;
* Commentary Evidence items;
* Response Evidence items.

It stores flattened immutable Game, Commentary, and Response Evidence tuples. An
empty Corpus produces one valid empty deterministic collection.

Ordering preserves Current Matches by Match ID. Games use Match ID, Match
position, and Game Reference ID. Commentary uses Match ID, Match position,
existing canonical source Commentary order, and Commentary Evidence ID as the
final tie-break. Responses use Match ID, Match position, existing canonical
source Response Link order, and Response Evidence ID as the final tie-break.
Text, commentator identity, inferred category, and importance never affect
order.

The collection fingerprint covers every collection field except the fingerprint
itself and is computed once by the builder.

## Export and serialization

`build_learning_corpus_human_evidence_export_v1()` accepts an already built,
fingerprint-verified collection. It does not resolve the Store or rebuild Human
Evidence. `LearningCorpusHumanEvidenceExportV1` contains exactly:

```text
learning_corpus_human_evidence_export_version
document_kind
export_id
collection_fingerprint
human_evidence
```

The export ID covers export version, document kind, exact collection fingerprint,
and the complete Human Evidence value.
`serialize_learning_corpus_human_evidence_export_v1()` accepts no path, writes no
file, and returns deterministic bytes using UTF-8,
`ensure_ascii=true`, finite JSON, two-space indentation, LF, and exactly one
trailing LF.

## Media and privacy boundaries

The descriptive source kind, URL, title, channel, and every retained Match/Game,
subject Decision, Commentary, and response Decision timecode are copied exactly.
The builder performs no URL fetch, embed, transcript lookup, metadata lookup,
source-platform request, or absolute-time derivation.

The export is private local minimized evidence. It may contain source URLs,
Player identities and labels, human text, observed Cards, and timecodes. It has no
public redaction, encryption, access-control, cloud, network, secure-storage, or
authorship claim. Fingerprints provide deterministic content identity only.

## Compatibility and open work

Issue #174 adds no Corpus object kind, Catalog field, persistence file, browser
operation, CLI, Public API, Root workflow, Schema, example, or generated
scenario. Package version remains `0.15.0`; Python remains `>=3.13`; seven Root
workflows, one Console Script, 63 authoritative and packaged Schemas, six Session
examples, 85 generated outputs, and Training Dataset version `1` target
`actual_card_played` remain unchanged.

Human Evidence never enters Match Analysis, Search, Historical Review, Replay
Coaching, Profile application, or Training Dataset version `1`. Human Evidence
persistence, browser/CLI download, Public API, Schema, derived human or AI tags,
strategy-teacher evidence, Dataset version `2`, samples, partitions, splits,
cross-game summaries, evaluation, and model training remain open.
