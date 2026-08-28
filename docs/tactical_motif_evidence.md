# Tactical motif evidence

Issue #194 adds a separate deterministic Historical Tactical Motif Review. It
describes structural facts about each recorded Card play without changing either
existing Replay Coaching family.

The report method is:

```text
historical_tactical_motif_review_v1
```

All Tactical Decision Facts, Motif Occurrences, Decision Observations,
Historical Reviews, and Match integration contracts are version `1`.

## Scope

One tactical motif occurrence is a deterministic structural observation about
one actual Card play. It is not a quality assessment, correctness label,
mistake, Recommendation, signal, communication claim, causal explanation,
Player trait, or cross-game conclusion.

The detector uses one retained Historical Decision Snapshot and existing rule
helpers. It executes no Search, simulation, opponent Policy, Profile, Coaching,
Commentary, Response-Link, or Settlement stage.

## Evidence timing

Decision-time facts are built before the actual Card is read. They retain safe
counts and public structure, but not the complete own hand or complete legal-Card
set. Their information cutoff is `before_actual_play`.

The actual Card and immediate partial-Trick winner facts are attached afterward.
These facts and their motifs use `after_actual_play`.

Completed-Trick winner, side, points, and outcome motifs are attached only from
the retained completed Historical Trick. They use `after_trick_completion`.

A Decision in the final incomplete Trick has status `partial`. That status and
its null completed-Trick fields are available after the recorded play. It retains
after-play motifs and cannot contain an after-completion motif. For a completed
Trick, `complete`, completed-Trick fields, and outcome motifs become available
only after the third play.

## Taxonomy

The exact family and motif order is stable.

| Family | Motifs |
| --- | --- |
| `lead_structure` | `trump_lead`, `non_trump_lead`, `new_effective_category_lead`, `repeat_effective_category_lead` |
| `void_response` | `void_trump_play`, `void_non_trump_discard`, `available_trump_not_used` |
| `trick_control` | `opposing_side_overtake`, `current_trick_win_available_not_taken`, `lowest_cost_current_winner` |
| `defender_partnership` | `partner_effective_category_return`, `partner_overtake`, `partner_safe_point_load`, `point_card_captured_by_partner` |
| `hand_shape` | `effective_category_exhausted` |
| `trick_outcome` | `point_card_lost_to_opposing_side` |

Overlapping factual motifs are valid. Every motif type may occur at most once per
Decision and serialization follows the canonical taxonomy order.

## Lead motifs

`trump_lead` identifies a Suit or Grand lead whose actual Card is trump.
`non_trump_lead` identifies any lead whose actual Card is not trump.

`new_effective_category_lead` means the actual lead category has not appeared as
a lead in any earlier completed Trick. `repeat_effective_category_lead` means it
has appeared. Grand Jacks and Suit trumps use the existing effective-category
rules; Null has no trump.

## Void responses

When the acting Player cannot follow the required effective category,
`void_trump_play` records an actual trump play and `void_non_trump_discard`
records an actual non-trump discard. `available_trump_not_used` additionally
records that at least one legal trump was available but the actual Card was not
trump.

These are ownership facts about the acting Player's decision-time hand. They do
not infer hidden opponent ownership or assess the choice.

## Trick control

`opposing_side_overtake` records that the pre-play current winner belonged to the
other side and the actual Card made the actor the current winner.

`current_trick_win_available_not_taken` records that a legal current-winning Card
existed but the actual Card did not make the actor the current winner.

`lowest_cost_current_winner` records that the actual winning Card was the
canonical lowest-cost legal current winner. Suit and Grand order by Card points,
then Trick strength, then canonical deck order. Null orders by Trick strength,
then canonical deck order. This is a neutral deterministic ordering, not an
optimality or quality claim.

## Defender partnership

`partner_effective_category_return` records a Defender lead in the most recent
effective category previously led by that Defender's partner.

`partner_overtake` records that the partner was the current winner before the
play and the acting Defender became the current winner afterward.

`partner_safe_point_load` records a positive-point Suit or Grand Card played by a
Defender while the partner remained the current winner immediately afterward.
It does not claim signaling, communication, intent, understanding, or quality.

`point_card_captured_by_partner` is available only after Trick completion. It
records a positive-point Suit or Grand Card whose completed Trick was won by the
Defender partner.

Declarer Decisions have no partner and cannot produce partnership motifs.

## Hand shape and outcome

`effective_category_exhausted` records that no Card of the actual Card's
effective category remained in the acting hand after the play.

`point_card_lost_to_opposing_side` is available only after Trick completion. It
records a positive-point Suit or Grand Card captured by the opposing side. Null
does not produce point-load or point-loss motifs.

## Historical execution

The default-false Historical Application option is:

```text
historical_tactical_motif_review
```

It requires no Search seed, Search Budget, or Immediate samples. It may accompany
Decision Snapshots, Immediate Review, either Search Review, or either Replay
Coaching family. Historical execution builds Decision Snapshots at most once and
reuses that exact retained sequence across requested attachments.

The optional Root attachment is:

```text
historical_tactical_motif_review_summary
```

It contains one observation per actual recorded Card, canonical motif and family
counts, complete Player/role/phase/contract summaries, and all ten report
limitations. Normal completion, shortened Games, party-wide Claims, zero-play
Games, and supported incomplete final Tricks retain their recorded lengths.

## Match controls

Private Match Historical options add default-false `tactical_motif_review` while
keeping Options version `1`. The Capture browser exposes one explicit `Tactical
Motif Review` checkbox under the existing `analyze_historical_game` operation.

One Match materialization, Historical Request, Application invocation, Root
validation, Result reconciliation, and revision-scoped Report build are used.
Ordinary rendering never runs analysis automatically.

The browser renders only source identity, observation/status counts, motif and
family counts, per-Player counts, chronological motif rows, and limitations. It
does not render complete own hands, legal-Card sets, hidden ownership, Search
Worlds, Commentary, Response Links, or quality labels. Historical Reports remain
ineligible for Strategy Teacher source download.

## CLI

Installed, module, and Legacy Root forms accept:

```powershell
skatmind --input examples/historical_tactical_motif_review.json --historical-tactical-motif-review
python -m skatmind --input examples/historical_tactical_motif_review.json --historical-tactical-motif-review
python main.py --input examples/historical_tactical_motif_review.json --historical-tactical-motif-review
```

Human-readable output includes source Game, observation/status totals, motif
occurrence count, and non-zero motif/family counts. `--quiet` preserves normal
JSON-only behavior.

## Provenance

Internal and opt-in public Field Provenance covers the complete attachment
without rerunning replay, Snapshot, motif, or summary stages.

Decision Facts are deterministic rule-derived values available at the current
Decision from retained Historical Snapshots. The actual Card is a retrospective
attachment available after actual play. Completed-Trick fields and their two
outcome motif types are available only after Trick completion. Motif and summary
counts are exact derived values.

Complete own hands and legal-Card tuples remain engine-private. Commentary and
Response Evidence remain separate caller-supplied evidence families.

## Schema and examples

The strict standalone Schema and byte-identical packaged resource are:

```text
schemas/historical_tactical_motif_review.schema.json
src/skatmind/schema_resources/historical_tactical_motif_review.schema.json
```

The Schema closes every object, fixes motif-type-to-family-and-evidence-time
relationships, rejects duplicate motif occurrences, and reconciles complete
versus partial completed-Trick fields. Runtime contracts additionally reconcile
actual Card points, trump/category facts, canonical motif order, and one-Game
numeric bounds.

The Root example is:

```text
examples/historical_tactical_motif_review.json
```

Two scenarios are appended after the existing 96:

```text
historical_tactical_motif_review_defender_partnership
historical_party_wide_claim_tactical_motif_review
```

The working totals are 71 authoritative Schemas, 71 packaged Schema Resources,
six Session examples, and 98 generated-output scenarios.

## Privacy and reuse

Public evidence may include actual Cards, effective categories, trump booleans,
Card points, public current-winner facts, safe legal-choice counts, Defender
partner identity, motif types, completed public Trick outcomes, and descriptive
counts.

It excludes complete own hands, complete legal-Card sets, hidden opponent hands,
unauthorized Skat or Discards, Search Worlds or Policies, private Search state,
Commentary, Response associations, and Statistics Records.

Issue #194 itself adds no aggregation, trait, rating, model-training, Learning
Dataset-v2 join, tactical Recommendation, Commentary interpretation, signaling
inference, communication inference, or causal attribution.

## Learning Corpus reuse

Issue #195 reuses the exact pure
`build_tactical_decision_observation_from_snapshot_v1()` detector for a separate
private Current-Match-Snapshot-only Learning Corpus family. The Corpus builder
first uses the existing Match Decision-state reconstruction seam. Every observed
Decision then produces one exact Tactical Evidence value or one explicit skip;
the detector, taxonomy, canonical order, timing cutoffs, Null exclusions, role/
partner rules, overlap behavior, and complete/partial final-Trick semantics do
not change.

The separate cross-game Summary adds only exact descriptive occurrence,
distinct-Game, distinct-Match, Player, role, seat, phase, contract, and bounded
recurrence Counts. It does not reinterpret a motif as quality, correctness,
intent, signaling, communication, causality, significance, a Player trait, or
Coaching. Human, Strategy Teacher, and Tactical Evidence remain separate, and
Learning Dataset version `2` is unchanged. See [Learning Corpus Tactical Motif
evidence and summaries](learning_corpus_tactical_motif_evidence_and_summaries.md).

Issue #196 consumes those exact retained observations in a separate private
Tactical Cross-game Coaching artifact. It exact-joins Strategy Teacher Evidence,
preserves one Assessment per exact Teacher Report, counts semantic duplicates
once for Decision consensus, and permits bounded repeated cross-Game focus only
for unanimous complete-Search below-best evidence. Immediate, partial,
unavailable, and mixed evidence remains descriptive. The detector, observations,
taxonomy, Summary, Dataset version `2`, and existing Coaching families remain
unchanged. Fixed Guidance makes no ground-truth, perfect-play, trait, Rating,
intent, signaling, communication, causal, or significance claim. See [Learning
Corpus Tactical Cross-game Coaching](learning_corpus_tactical_cross_game_coaching.md).
