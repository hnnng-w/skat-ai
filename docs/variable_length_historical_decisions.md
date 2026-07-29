# Variable-length historical decisions

Version-1 historical decision workflows support `normal_completion`,
`declarer_concession`, `defender_concession`, `declarer_card_exposure`, and
`defender_open_play`, and `open_card_throw`. One shared cardinality is derived from the validated
historical play prefix:

```text
decision_count = played_card_count
snapshot_count = decision_count
review_decision_count = decision_count
training_sample_count = decision_count
rolling_target_decision_count = decision_count
```

Normal completion still requires exactly 30 plays and preserves its existing 30
snapshots, review decisions, ten decisions per player, and 30 training samples.
A declarer concession, defender concession, accepted exposure, or open-card throw supports zero
through 29 supplied plays while defender open play requires at least five
completed tricks and one through five unresolved tricks. No missing card
is inferred, no array is padded, and the terminal event is not a card
decision or training target.

## Snapshot and review behavior

A snapshot is created immediately before every supplied play and never after the
last play. An incomplete final trick contributes one or two snapshots for its
actual cards. It remains the current trick: no winner is derived and its points
are not added to completed-trick totals.

A zero-play shortened record produces an empty snapshot summary and a valid review
with zero reviewed, unavailable, and quality counts. All three player summaries
remain present with zero decisions. For other shortened prefixes, per-player
counts follow the actual actors and need not be equal.

External historical profiles retain exact stable-player matching, strict
`captured_at < played_at` eligibility, and per-decision left/right remapping.
They apply only to actual card decisions and produce zero application counts for
an empty prefix.

## Information safety

Decision-time visible state and model-facing training features never include the
future concession, exposure, open play, or open-card throw; defender consent or acceptance;
conceding, shown-to, or exposing defender; event form; exposed hand; proof;
claimed level; final
winner, unresolved points, settlement,
or cards that were not yet visible. Records with a shared deal, declaration, and
play prefix therefore produce equivalent snapshot states, review inputs,
features, and actual-card labels for that prefix regardless of later normal
continuation, concession, exposure, open play, or valid terminal-event choice. Record IDs and provenance may
differ outside the feature view.

The private coherent root used for live Multi-Step execution does not change
this equivalence. Historical future hands and root-world ownership remain absent
from snapshots, review inputs, training features, and rolling predictions.

## Training and partitions

Training records preserve feature-generation version `1`, target
`actual_card_played`, sample IDs `<record_id>:<decision_index>`, existing feature
semantics, labels, and provenance. Each record reports its actual sample count;
partition and dataset totals sum those counts. Zero-sample records and datasets
whose total sample count is zero are valid.

Partition policies and audits remain record- and stable-player-based. A
zero-sample record still contributes all three participants to known-opponent
coverage and unseen-player overlap enforcement.

Historical opponent statistics count each supported record once, independently
of this decision count. Rolling targets use the same exact cardinality without
padding; zero-decision targets remain present with all participants and as-of
profiles. Completed shortened source games may affect later profiles through normal
game statistics, but a target outcome never affects its own profile or card
predictions. Both timed continuation kinds remain 30-play normal completions
rather than variable-length ends. No other historical end kind or continuation,
concession/exposure/open-play choice, proof, acceptance, or continuation target,
feature version, or learned model is added. See
[Shortened historical opponent workflows](shortened_historical_opponent_workflows.md).
