# Learning Corpus Tactical Cross-game Coaching

Issue #196 adds a private, deterministic Tactical Cross-game Coaching artifact
over explicit Current Match Snapshots. It joins retained Tactical Motif Evidence
with retained method-bound Strategy Teacher Evidence. It does not execute Search,
Immediate analysis, PIMC, Match Analysis, Historical replay, Tactical detection,
Profile derivation, Dataset generation, or Commentary processing.

The report method is:

```text
learning_corpus_tactical_cross_game_coaching_v1
```

The artifact is process-local and private. It has no Public API, Root workflow,
CLI option, Schema, example, generated scenario, or persistence format.

## Exact source join

One Tactical Evidence value and one Strategy Teacher Evidence value join only on
all five exact facts:

```text
match_snapshot_id
game_reference_id
decision_reference_id
acting_player_id
actual_card_played
```

The builder also reconciles the retained Match, Workspace revision, Match
position, Game, Decision index, and legal-Card count. It performs no fuzzy match,
cross-revision lineage lookup, nearest-Decision search, or Player alias inference.
A Teacher for a skipped or absent Tactical Decision remains explicitly unjoined;
no Tactical Observation is invented.

## Teacher Assessments

Every exact joined Teacher Report produces one immutable method-bound Teacher
Assessment. Exact Reports remain distinct and no Report or method is selected,
deleted, averaged, weighted, or preferred.

Assessment scopes are:

```text
complete_search
completed_common_prefix
immediate_only
none
```

Immediate uses the retained Immediate post-game comparison and is always
descriptive. Bounded Search uses the retained actual-Card Search comparison.
Complete single-exact, all-compatible, and sampled coverage receives
`complete_search`; retained partial or timeout common-prefix aggregates receive
`completed_common_prefix`. Auto follows its exact effective method. Information-
set Search uses only its retained complete Information-set Candidates and
comparison; PIMC and Immediate diagnostic baselines never replace it. Partial,
timeout, unavailable, or incomplete Information-set evidence is not assessable.

Only `complete_search` can be eligible for an action-oriented focus. Immediate
and completed-common-prefix values remain visible in the private report but can
never create one.

Assessment statuses are:

```text
forced_move
best_or_equivalent
strictly_below_best
not_assessable
```

The actual Card is observed behavior, not ground truth. `best_or_equivalent` and
`strictly_below_best` describe only the retained aggregate ordering of one exact
method-bound Teacher. Null assessments never use card-point-margin impact.

## Semantic duplicates

Elapsed-time-only or otherwise semantically equal exact Reports can share one
existing `teacher_semantic_fingerprint`. Every exact Assessment remains in the
report, but one semantic fingerprint contributes once to Decision consensus.
Assessments under one semantic fingerprint must have identical semantic output;
a contradiction is rejected as an invariant violation.

This preserves exact source counts while preventing repeated uploads of equal
Teacher evidence from multiplying a Decision classification or focus threshold.

## Decision consensus

One Decision Summary exists for every Tactical Evidence value. It retains every
exact Assessment ID, every unique semantic fingerprint, canonical status and
impact Counts, and the Tactical motifs.

Decision statuses are:

```text
forced_move
no_teacher
not_assessable
best_or_equivalent
strictly_below_best
mixed
```

The precedence is deterministic:

1. One legal Card is `forced_move`.
2. No joined Teacher is `no_teacher`.
3. No distinct semantic complete-Search Teacher is `not_assessable`.
4. Unanimous complete-Search best/equivalent Teachers are `best_or_equivalent`.
5. Unanimous complete-Search below-best Teachers are `strictly_below_best`.
6. Disagreement between those complete-Search classifications is `mixed`.

No method has priority over another. Mixed evidence never creates an actionable
focus. If unanimously below-best Teachers retain different objective-impact
components, the Decision remains below-best and its consensus impact is `mixed`.

## Cross-game focus

One Player/motif pair becomes a focus only when both exact thresholds hold:

```text
strictly_below_best Decision count >= 2
distinct Game Reference count >= 2
```

Two Decisions in one Game are insufficient. Qualifying Decisions can occur in
several Games of one Match or across Matches. Each Decision contributes once to
the focus regardless of exact Report count, and semantic duplicates do not
increase any threshold.

Focus priority is:

1. Contract-success impact.
2. Settlement-score impact.
3. Suit/Grand card-point-margin impact.
4. Mixed retained Search-impact components.
5. Distinct Match count descending.
6. Distinct Game count descending.
7. Qualifying Decision count descending.
8. Canonical Tactical Motif order.

At most five focus areas are retained per Player. The Player report keeps the
full eligible-candidate count so bounded selection is explicit. Priority chooses
review order only; it is not a Player or method ranking.

## Guidance

Each retained focus uses one fixed Guidance code and one fixed English template:

```text
review_repeated_contract_success_gap
review_repeated_settlement_score_gap
review_repeated_card_point_margin_gap
review_repeated_mixed_search_gap
```

Guidance states only that repeated Decisions merit review because every distinct
semantic complete-Search Teacher ranked the observed Card below at least one
alternative under retained evidence. It does not claim a mistake, objective
correctness, perfect play, a winning real-deal Card, Player strength or weakness,
a stable trait, intent, signaling, communication, causality, statistical
significance, equilibrium, global optimality, or calibrated probability.

No generated free text or model is used.

## Player and global reports

One Player Report exists for every Player Catalog entry in exact Catalog order,
including Players with zero Tactical or Teacher evidence. Exact observed labels
remain non-canonical. Reports contain Counts and bounded focus areas but no
Player comparison, grade, score, trait, Rating, strength, or weakness.

The global report status is:

```text
empty
    no Tactical Evidence and no Decision Summary

insufficient_evidence
    at least one Decision Summary but no qualifying focus

available
    at least one retained focus
```

The global report retains exact source fingerprints, Assessments, Decision
Summaries, unjoined Teacher IDs, Player Reports, focus areas, Counts, and all
canonical limitations. Its fingerprint and every nested identity use separate
domain-separated canonical-JSON SHA-256 material. No path, current time, process
value, random value, or environment value enters an identity.

## Artifact separation

The private artifact families remain separate:

```text
Human Evidence
Strategy Teacher Evidence
Tactical Motif Evidence and Summary
Tactical Cross-game Coaching
```

Human Commentary and Response Links are not joined or interpreted. Tactical
motifs remain structural observations. Strategy Teacher Evidence remains method-
bound evidence rather than ground truth.

Learning Dataset version `2`, its evidence-family vocabulary, Dataset Records,
Dataset fingerprint behavior, and the existing Dataset-v2 Cross-game Summary are
unchanged. No Coaching ID becomes a Dataset field, Target, Label, Feature, task,
evaluation, or model value.

## Corpus preparation

The existing explicit `prepare_learning_artifacts` operation now builds:

1. The existing Player, Human, Strategy Teacher, Dataset, partition, and Summary
   family exactly as before.
2. The existing Tactical Evidence and Tactical Summary family exactly as before.
3. One Tactical Cross-game Coaching Report from those retained values.

All builders run outside the context lock. The existing Store identity, Catalog
revision and content fingerprint, Strategy source revision, and context
generation are checked after the build. Existing, Tactical, and Coaching
prepared wrappers publish together only if every check still matches. Stale work
publishes none, receives no retry, and cannot erase a newer prepared generation.
Every existing applied source invalidation clears all three families; unchanged,
conflicted, and failed source operations preserve all still-valid families.

Downloads serialize retained artifacts and never rebuild Coaching.

## Dashboard and download

The ordinary browser state exposes only:

```text
tactical_coaching_status
tactical_coaching_decision_count
tactical_coaching_teacher_assessment_count
tactical_coaching_focus_area_count
tactical_coaching_player_with_focus_count
```

It does not expose Guidance, Player focus rows, motifs, Decision References,
Cards, ranks, metrics, fingerprints, or paths.

The tenth authenticated private prepared download is:

```text
/downloads/tactical-cross-game-coaching.json
```

It uses canonical UTF-8 JSON with ASCII escaping, two-space indentation, LF line
endings, exactly one trailing LF, a deterministic identity-prefixed ASCII-safe
filename, and no file I/O. It is unavailable before successful current
preparation and after source invalidation.

## Remaining boundaries

Issue #196 does not add broad tactical truth labels, Commentary or Response-Link
interpretation, Player Ratings, traits, causal attribution, significance tests,
preferred Teachers, method voting, learned guidance, model training, derived
persistence, automatic Report capture, or a public Coaching surface. These areas
remain separate candidate work subject to their existing product classifications.
