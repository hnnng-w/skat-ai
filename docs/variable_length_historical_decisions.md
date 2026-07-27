# Variable-length historical decisions

Version-1 historical decision workflows support `normal_completion` and
`declarer_concession`. One shared cardinality is derived from the validated
historical play prefix:

```text
decision_count = played_card_count
snapshot_count = decision_count
review_decision_count = decision_count
training_sample_count = decision_count
```

Normal completion still requires exactly 30 plays and preserves its existing 30
snapshots, review decisions, ten decisions per player, and 30 training samples.
A declarer concession supports zero through 29 supplied plays. No missing card
is inferred, no array is padded, and the terminal concession is not a card
decision or training target.

## Snapshot and review behavior

A snapshot is created immediately before every supplied play and never after the
last play. An incomplete final trick contributes one or two snapshots for its
actual cards. It remains the current trick: no winner is derived and its points
are not added to completed-trick totals.

A zero-play concession produces an empty snapshot summary and a valid review
with zero reviewed, unavailable, and quality counts. All three player summaries
remain present with zero decisions. For other shortened prefixes, per-player
counts follow the actual actors and need not be equal.

External historical profiles retain exact stable-player matching, strict
`captured_at < played_at` eligibility, and per-decision left/right remapping.
They apply only to actual card decisions and produce zero application counts for
an empty prefix.

## Information safety

Decision-time visible state and model-facing training features never include the
future concession, defender consent, final winner, unresolved points, settlement,
or cards that were not yet visible. Records with a shared deal, declaration, and
play prefix therefore produce equivalent snapshot states, review inputs,
features, and actual-card labels for that prefix regardless of later normal
continuation, concession, or valid consent choice. Record IDs and provenance may
differ outside the feature view.

## Training and partitions

Training records preserve feature-generation version `1`, target
`actual_card_played`, sample IDs `<record_id>:<decision_index>`, existing feature
semantics, labels, and provenance. Each record reports its actual sample count;
partition and dataset totals sum those counts. Zero-sample records and datasets
whose total sample count is zero are valid.

Partition policies and audits remain record- and stable-player-based. A
zero-sample record still contributes all three participants to known-opponent
coverage and unseen-player overlap enforcement.

Historical opponent-statistics aggregation and rolling opponent-policy
evaluation remain explicitly normal-completion-only. Their shortened-game
semantics are not implemented. No other historical end kind, historical
continuation, concession-choice target, feature version, or learned model is
added by this support.
