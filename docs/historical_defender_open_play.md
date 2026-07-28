# Historical defender open play

`skat-ai` supports terminal historical defender-open-play adjudication under the
November 2022 wording of ISkO 4.4.5. The historical adapter reconstructs an
exact late-game state from the complete deal and legal play prefix, then reuses
the existing flat bounded adjudicator. It does not implement historical
continued play.

## Event contract

Version 1 adds `game_end_reason: "defender_open_play"` with:

```json
{
  "schema_version": 1,
  "kind": "defender_open_play",
  "exposing_defender_player_id": "player-a",
  "exposed_cards": ["C7", "S10"],
  "declarer_response": "accept_adjudication"
}
```

The player ID must be one exact stable participant ID, must not be `me`, `left`,
or `right`, and must identify one of the two defenders. `exposed_cards` must be
unique valid cards and must exactly equal that defender's reconstructed complete
current hand. Callers do not supply the declarer's or non-exposing defender's
remaining cards.

Only `accept_adjudication` is supported. `request_continued_play` is rejected
with guidance that historical defender-open-play continuation remains separate
future work. The existing flat ongoing continuation contract is unchanged.

The focused schemas are:

* [`historical_defender_open_play.schema.json`](../schemas/historical_defender_open_play.schema.json)
* [`historical_defender_open_play_output.schema.json`](../schemas/historical_defender_open_play_output.schema.json)

## Exact reconstruction and bound

Replay validates ownership, circular play order, follow obligations, completed
trick winners, and the optional one-card or two-card incomplete final trick.
From the exact deal and prefix it derives all three current hands, current
leader, next player, completed trick ownership, current trick, and final skat.

Exactly one through five tricks may remain unresolved, so at least five tricks
must already be complete. All ten complete tricks, all 30 played cards, more
than five unresolved tricks, or an exposing defender with no remaining hand
card are rejected. Search is never truncated.

Stable players are mapped deterministically to the existing flat circular order
with the declarer as `me`; clockwise successors become `left` and `right`.
Declarer, both defenders, completed and current trick players, leaders, next
player, and remaining hands use that same mapping. Public proof output maps all
identities back to stable IDs.

## Exact proof

The adapter reuses `DefenderOpenPlay`, `DefenderOpenPlayContext`,
`build_exact_remaining_play_state(...)`, `prove_defender_rest_tricks(...)`, and
`adjudicate_defender_open_play(...)`. No historical solver exists.

The exhaustive quantifiers remain:

* exposing defender: `exists_legal_strategy`
* declarer: `all_legal_plays`
* non-exposing defender: `all_legal_plays`

The exposing strategy may depend on the reached exact state. Canonical card
traversal, immutable states, and per-proof memoization make the result
deterministic. Every supported proof is complete. There is no random, Monte
Carlo, tactical-policy, heuristic, timeout, or truncated-valid result.

## Result and settlement

A valid proof assigns every unresolved trick and point to defenders. An invalid
proof assigns every unresolved trick and point to the declarer under the
existing simple-win and bounded mandatory-level rules. A result already decided
before the event remains binding.

Observed completed-trick and skat points remain separate from unresolved current-
trick and hand points. Output then reports the rule-assigned points and final
120-point allocation. Rule-assigned levels remain distinct from normally
achieved Schneider or Schwarz.

Suit, Grand, overbid-required values, announced mandatory levels, Null, Null
Hand, Null ouvert, and Null ouvert Hand use the existing flat adjudicator and
settlement builder without historical-only scoring semantics. Equivalent flat
and historical facts therefore produce the same proof status, final result, and
settlement.

## Privacy

Only the exposing defender's reconstructed current hand is public. Proof lines:

* show exposing-defender cards;
* redact declarer cards;
* redact non-exposing-defender cards;
* use stable `player_id` values;
* map trick winners to stable `trick_winner_player_id` values.

Output does not emit private remaining hands, exact solver states, memoization
keys, or alternative private branches. The CLI prints stable identities, proof
status, party-level assignment, result, and settlement without private cards.

## Historical workflows

Snapshots, review, external-profile review, training conversion, dataset
summaries, partition audits, historical opponent statistics/export, and rolling
opponent-policy evaluation accept this end reason explicitly. Each actual card
played before the event creates exactly one decision artifact. Opening the hand,
the all-rest-tricks claim, proof, adjudication, and any continuation response
create none.

Training retains feature-generation version `1` and target
`actual_card_played`. Earlier decision features and predictions contain no event
identity, exposed hand, private proof evidence, proof result or line, assignment,
winner, or settlement.

Each completed record contributes one game per participant to opponent
statistics, using final settlement as the sole winner authority. Proof status,
search-state counts, remaining tricks, and play count do not weight the game.
No open-play count, validity rate, exposing-defender blame, signal, threshold,
classification, profile, policy, preset, proof target, or event target is added.
Rolling targets contain only actual historical card decisions.

## Example

```powershell
python main.py --input examples/historical_grand_defender_open_play.json
```

The deterministic example has eight completed Grand tricks, a valid two-trick
proof, 13 points assigned to defenders, and a `-144` settlement.

## Boundaries

This feature does not add historical continuation, historical open-card
throwing, unlimited or heuristic proof, single-trick claims, open-play or proof
prediction, learned models, or four-player support.
