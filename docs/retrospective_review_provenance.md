# Retrospective review provenance

Issue #144 extends the internal field-level provenance system through flat
retrospective Position Analysis, Historical Review, Historical Search Review,
and Replay Coaching. It uses the shared version-1 provenance language and the
existing Application sidecar boundary.

The propagation versions are:

```text
APPLICATION_PROVENANCE_VERSION = 1
RETROSPECTIVE_REVIEW_PROVENANCE_VERSION = 1
REPLAY_COACHING_PROVENANCE_VERSION = 1
```

These versions are independent of the Package, Public API, Application
orchestration, Root Schema, Historical Review, Search, and Replay Coaching
contract versions.

This work changes no Root input or output field, JSON Schema, example,
generated-output scenario, CLI option or presentation, Public Python API export,
Package version, or distribution contract. The Public API and every CLI
transport intentionally discard the internal Application provenance bundle.

## Retained-stage model

Provenance collectors observe values already produced by the existing workflow.
They do not run a second Immediate analysis, Search, Snapshot pass, Historical
Review, Replay Coaching assessment, prioritization, guidance, or Outcome Context
build. Optional internal hooks preserve direct Domain-call compatibility when no
collector is supplied.

The ordered retrospective stages are:

```text
decision_input
decision_time_analysis
actual_card_attachment
retrospective_assessment
prioritization
guidance
final_report
```

A consumer cannot depend on a later stage. Decision-time analysis is retained
before the observed card is introduced. The observed card is represented only
as a `retrospective_attachment` available `after_actual_play`. Final Outcome
Context is available only at `game_end` and is attached to the final report; it
cannot feed prioritization or guidance.

## Canonical attachment order

`ApplicationProvenanceBundle` sorts retrospective attachments in this order:

1. `flat_retrospective/input`
2. `flat_retrospective/analysis`
3. `flat_retrospective/assessment`, when an actual card is supplied
4. `historical_decision/<decision-index>/input`
5. `historical_decision/<decision-index>/analysis`, when review analysis runs
6. `historical_decision/<decision-index>/assessment`, when assessment runs
7. `historical_snapshot_summary`, when requested
8. `historical_immediate_review_summary`, when requested
9. `historical_search_review_summary`, when requested
10. `replay_coaching/prioritization`, when requested
11. `replay_coaching/guidance`, when requested
12. `replay_coaching/report`, when requested
13. `position_result` or `historical_game_result`

Historical decision attachments are ordered by positive decision index and then
by input, analysis, and assessment. Supported shortened games and continuations
therefore retain their exact zero-through-30 decision cardinality without
inventing missing decisions.

## Flat retrospective Position Analysis

The flat input attachment freezes the validated pre-recommendation state,
opponent hand sizes, authorized Public-hand Constraints, Strategic Metadata,
Game Declaration, selection method, and seed-free settings. It excludes
`actual_card_played`.

The analysis attachment retains the already executed recommendation result. It
covers legal cards, recommendation, candidate report, strategic and method
summaries, Hidden-card inference summary, and optional bounded-Search result.
Search entries reuse the existing aggregate Search provenance mapping over the
retained `BoundedSearchResult`.

When an actual card is present, the assessment attachment introduces it together
with the existing Immediate and optional Search post-game summaries. The exact
Position Result receives matching non-legacy entries for
`post_game_review_summary` and
`bounded_search_post_game_review_summary`; Issue #146 adds complete non-legacy
provenance for every other current Result branch.

Changing only the actual card or later result cannot change the retained input
or decision-time analysis attachment. A retrospective request without an actual
card has input and analysis provenance but no assessment attachment.

## Historical decision inputs

Each Historical decision input is an allowlisted reconstruction of the existing
information-safe Snapshot. It includes:

* stable game, decision, trick, play, actor, seat, and side identities;
* `decision_time` Information Policy and the exact information cutoff;
* relative Player mapping;
* the actor's visible state, legal cards, public history, points, turn, and
  opponent hand sizes;
* exact declared-Ouvert or continuation Public-hand information already present
  at that decision boundary;
* effective review settings;
* time-safe external profile application and effective policies when enabled.

The acting Player's own hand and legitimately known Skat are `local_private`.
Public event history is reconstructed from the validated Historical Game. Legal
cards are rule-derived, and matadors are structural inference where available.
External Opponent Statistics are not copied into the attachment. Only the
existing compact application values are retained; an internal source reference
to the supplied external document is engine-private.

No future play, later continuation event, actual card, final hidden hand, final
Skat, winner, result, settlement, private compatible-world ownership, Search
state, cache, branch, principal variation, or random-stream detail is accepted in
a decision input.

## Historical analysis and assessment

Immediate Historical Review and Historical Search Review feed the same collector
through optional hooks at their existing boundaries:

* decision-time Immediate reports and recommendations enter the analysis
  attachment before the actual card;
* Search Review retains its already built decision position, Immediate baseline,
  decision-time Coaching evidence, and aggregate Search result before the actual
  card;
* the actual card, Search actual-card comparison, and Replay Coaching decision
  assessment enter the assessment attachment afterward.

Every complete per-decision attachment is audited against its exact serialized
document. Search fields use the existing exhaustive, sampled, partial, timeout,
and unavailable provenance semantics. The collector never receives concrete
selected worlds or actual hidden ownership.

The optional Snapshot, Immediate Review, and Search Review aggregate summaries
also receive complete all-leaf ledgers. Their per-decision actual-card fields are
retrospective attachments; decision-time rows retain their original decision
indexes. Aggregate counts and reconciliations are available only during offline
review.

## Replay Coaching

Replay Coaching provenance is constructed from the single retained Historical
Search Review pass:

* decision-time evidence remains available at `current_decision`;
* each actual card and impact assessment becomes available
  `after_actual_play`;
* Key Decisions and Turning Points are retained in
  `replay_coaching/prioritization` during offline review;
* patterns and deterministic recommendations are retained in
  `replay_coaching/guidance` during offline review;
* the complete existing serialized report is covered by
  `replay_coaching/report`.

Prioritization and guidance reject Outcome Context. The final report maps its
Outcome Context to `post_game_only` visibility at `game_end`, while its embedded
decision evidence and assessments retain their earlier availability. This
preserves the existing `decision_time_then_retrospective_attachment` policy and
does not make final outcome evidence causal input to Coaching guidance.

## Result ledgers

The flat workflow uses a complete all-leaf `position_result` ledger. The Issue
#144 retrospective review entries remain unchanged beside the Issue #146
Declaration, scoring, Result, Settlement, Performance, list, ending, and
continuation mappings.

Every Historical Game execution attaches a complete `historical_game_result`.
Base execution without review options has a bundle containing only that Result.
Snapshot, Immediate Review, Search Review, Replay Coaching, and historical
profile-application entries remain unchanged when selected. Canonical record,
replay, points, Result, Value, Overbid, Settlement, events, and terminal endings
use complete non-legacy mappings described in
[Complete Result provenance](complete_result_provenance.md).

## Privacy and determinism

Every complete attachment rejects known engine-private document fields before
ledger construction. Provenance documents contain no final hidden hands,
selected Compatible Worlds, ownership assignments, hypothetical private Skat,
Exact Search States, caches, branches, principal variations, private seeds, or
private profile records.

Attachment documents, ledgers, coverage summaries, contexts, names, and ordering
are deterministic for equal retained workflow values. Existing public redaction
removes engine-private source references without revealing which private source
was removed. Existing Confidence, Coaching impact, specialized provenance
status, Search exactness, and profile confidence contracts remain separate and
unchanged.

## Remaining work

The following remain open:

* any additive public provenance API, Root output, Schema, artifact, example, or
  CLI presentation;
* broader adversarial enforcement outside implemented Application workflows.

Issue #145 implements the former Dataset, Preparation, Opponent, Profile, list,
and comparison propagation scopes. See
[Dataset, list, and opponent provenance](dataset_list_and_opponent_provenance.md).
