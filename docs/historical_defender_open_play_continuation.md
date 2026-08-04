# Historical defender open-play continuation

Version-1 historical games can record one timed non-terminal defender-open-play
continuation under ISkO 4.4.5 and 4.1.6. The declarer has required continued
play, the exposed cards are returned to the defender's hand, and the exact
returned hand remains known to all players. Actual later card play determines
the final result.

## Record contract

The containing game may end normally or through one later supported terminal
shortening. Normal completion uses:

```json
{
  "game_end_reason": "normal_completion",
  "game_events": [
    {
      "schema_version": 1,
      "kind": "defender_open_play_continuation",
      "after_play_count": 12,
      "exposing_defender_player_id": "player-a",
      "exposed_cards": ["CQ", "CJ", "C9", "C8", "C7", "S10"],
      "declarer_response": "request_continued_play"
    }
  ],
  "tricks": []
}
```

`game_events` is optional. When absent, canonical records and behavior are
unchanged and no empty array or event summary is emitted. Version 1 accepts at
most one event, either this kind or `declarer_card_exposure_continuation`, no
terminal `game_end` for normal completion, exactly ten complete tricks, and all
30 actual card plays. Alternatively, the same event may precede one of the five
existing terminal `game_end` kinds. The terminal object remains top-level and is
not copied into `game_events`. Multiple continuations and arbitrary event streams
remain unsupported.

The event schema version is independent of the historical-game schema version;
both currently equal `1`. Unsupported versions, kinds, missing fields, unknown
fields, and an explicitly empty or multi-event array are rejected.

## Exact play boundary

`after_play_count` is a strict integer from `0` through `29`. It identifies the
boundary after exactly that many chronological cards and before the next actual
play. Booleans, negative values, `30`, and larger values are invalid.

The historical replay engine replays exactly that prefix and derives completed
tricks, an optional one-card or two-card current trick, its leader and plays, the
next player, all exact remaining hands and sizes, and observed points. No card is
sampled and no hidden world is created for event validation. The event may occur
before play 1, between tricks, during a trick, or before play 30.

## Stable defender and exact hand

`exposing_defender_player_id` is one exact non-padded stable participant ID.
Relative `me`, `left`, and `right` identities, unknown players, and the declarer
are invalid. The exposing defender need not be next to act and may already have
played in the incomplete current trick, but must still hold at least one card.

`exposed_cards` contains one through ten unique valid cards and must equal the
defender's complete reconstructed hand at the boundary. Set reconciliation
rejects missing, additional, played, current-trick, discarded, skat, or
wrong-owner cards. Canonical serialization uses deck order and reports
`card_reconciliation: "confirmed"`. No other remaining hand is emitted.

## Continued-play semantics

Only `request_continued_play` is accepted. `accept_adjudication` belongs to the
terminal `game_end_reason: "defender_open_play"` contract.

The event summary records:

```text
cards_returned_to_hand = true
hand_physically_open = false
visibility_scope = all_players
rest_trick_claim = all_remaining_tricks
rest_trick_claim_status = not_adjudicated_due_to_continued_play
continued_play_effect = open_play_consequence_disregarded
exact_proof_applied = false
game_end_applied = false
settlement_applied = false
```

The event does not call the exact rest-trick solver, use the five-trick bound,
classify the original claim, produce proof or a counterexample, assign a trick or
point, select a winner, or create a settlement. It changes information only.

## Public hand over time

For an event after `N` plays, snapshots `1..N` are unchanged pre-event states and
snapshots `N+1..30` are post-event states. Post-event
`public_exposed_cards` contains the exposing defender's exact current hand. Each
actual exposing-defender play removes that card; no extra card is assigned and a
played card never returns. The constraint is empty after completed play.

For terminal shortening, `N` may equal the final recorded play count; otherwise
the public hand shrinks only when the exposing defender actually plays. At the
terminal boundary it must exactly equal that defender's reconstructed remaining
hand. The terminal adjudicator then applies independently. The continuation
summary keeps all proof, game-end, and settlement flags false and reports
`final_outcome_source: "subsequent_terminal_shortening"`.

Declared ouvert remains independent. When both hands are public, snapshots use
stable seat order. Visible matador inference treats the continuation hand as
known defending-party ownership and still treats declared-ouvert declarer cards
as declarer ownership. It infers no unrelated hidden ownership.
Historical review retains both disjoint exact constraints, samples no additional
card for either owner, and prefers source `declared_ouvert` if duplicate
declarer-exposure evidence describes the already-public declarer hand.
Confirmed attributed failure-to-follow evidence may constrain only the remaining
unknown ownership. Exact continuation and Ouvert hands remain authoritative and
contradictions are rejected.

## Review and training

Historical review maps the stable exposing defender to `me`, `left`, or `right`
for each acting player and creates the existing `PublicHandConstraint` with
source `defender_open_play_continuation`. Existing hidden-world sampling fixes
exactly those cards to the constrained hand, assigns no additional card to it,
and samples only genuinely unknown cards. Every policy compared at one decision
receives the same constraint and seeded behavior remains deterministic.

Base Historical Review remains Immediate Analysis and does not use the later
complete deal to construct a Multi-Step root. Optional Historical Search Review
and Replay Coaching use the same decision-time snapshots and public-hand
boundary. Actual future hands remain excluded from every pre-play decision
state. The model cannot use the actual next card, later hands or plays, event
facts before their boundary, final result, or settlement. See
[Hidden-card inference](hidden_card_inference.md).

The event is not a review decision. Normal review still has 30 actual-card
decisions; shortened chains use only their zero through 29 actual plays. Training
uses the same cardinality, feature-generation version `1`, stable
`record_id:decision_index` sample IDs, and the `actual_card_played` target.
Pre-event samples contain no event information. Post-event samples carry only
the authorized hand through the existing relative public-exposure feature.
There is no event, claim, proof, continuation-response, result, or settlement
target or model-facing feature. Hidden-card inference evidence, marginals,
confidence, and compatible-world statistics are likewise not version-1 training
features or labels.

## Result and opponent workflows

All actual trick winners remain authoritative. The event adds no level and cannot
itself change points, winner, Schneider, Schwarz, game value, overbid, or final
settlement. Normal play or the independently delegated terminal shortening
determines those values. The event may change only post-event card analysis
because more ownership is public.

Dataset membership and partition semantics remain participant-based. Historical
statistics count one ordinary completed game per participant and use only final
settlement. Rolling source games contribute one ordinary game-level result.
Rolling targets retain 30 actual decisions, hide the event before its boundary,
use the public hand afterward, and exclude the target result from its own
profile. No event-specific statistic, signal, classification, profile field, or
prediction is added.

See
[`examples/historical_grand_defender_open_play_continuation.json`](../examples/historical_grand_defender_open_play_continuation.json)
for the deterministic Grand example and
[Historical defender open play](historical_defender_open_play.md) for terminal
accepted adjudication. The sibling public-declarer-hand event is documented in
[Historical declarer-card-exposure continuation](historical_declarer_card_exposure_continuation.md).
