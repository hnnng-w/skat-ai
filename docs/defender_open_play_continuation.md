# Defender open play continuation

This bounded flat-position workflow represents continued play under ISkO 4.4.5
and 4.1.6 after the declarer has already requested continuation. The exposing
defender has taken the complete exposed hand back. The cards are no longer
physically open, but every player retains exact knowledge of them.

## Separate contract

Ongoing play uses `game_continuation`, not completed `game_shortening`:

```json
{
  "game_continuation": {
    "schema_version": 1,
    "kind": "defender_open_play",
    "exposing_defender": "left",
    "declarer_response": "request_continued_play",
    "public_exposing_defender_cards": ["C7", "H8", "D9"]
  }
}
```

Every property is required and unknown properties are rejected. The declarer
and exposing defender must be concrete and distinct, and the exposing player
must belong to the defending party. `accept_adjudication` is rejected with
guidance to use `game_shortening.kind = "defender_open_play"`.

## Returned hand and reconciliation

`public_exposing_defender_cards` is the complete current hand, after any cards
played since continuation began. It contains `1..10` valid unique cards. Output
uses canonical card order and reports:

```json
{
  "cards_returned_to_hand": true,
  "hand_physically_open": false,
  "visibility_scope": "all_players"
}
```

The supplied list is authoritative unless it contradicts reliable evidence.
Validation rejects overlap with completed tricks, the current trick, legacy
played cards, known skat cards, or a reliably different owner. It also checks
the local hand, direct opponent hand sizes, completed-trick progression,
current-trick contribution, and concrete turn phase. A local exposing
defender's list must exactly equal the local hand and reports `confirmed`.
Otherwise valid input without independent exact set evidence reports
`not_verifiable`; that status does not weaken or hide the supplied cards.

## Information and simulation

The resolver creates one exact `PublicHandConstraint` for the exposing defender
with source `defender_open_play_continuation`. It authorizes no declarer hand,
partner hand, private Issue #90 proof hand, hidden skat card, future play, or
future outcome. The physically returned hand remains visible to all players.

Every hidden-world sample assigns exactly those cards, and no additional card,
to the exposing defender. The other defender, declarer, and skat retain their
ordinary uncertainty unless independently known. Immediate Analysis, supported
Multi-Step, Policy Comparison, and flat post-game review use the same root
constraint. A played known card is removed in child states; every other known
card remains fixed, and the played card cannot be resampled or reintroduced.
Unknown cards retain the existing Multi-Step resampling limitation, so this is
not general globally coherent hidden-world continuity. No policy is added or
changed.

## No adjudication or settlement

The original claim is retained only as provenance:

```json
{
  "rest_trick_claim": "all_remaining_tricks",
  "rest_trick_claim_status": "not_adjudicated_due_to_continued_play",
  "continued_play_effect": "open_play_consequence_disregarded",
  "exact_proof_applied": false,
  "game_end_applied": false,
  "settlement_applied": false
}
```

The continuation never calls `prove_defender_rest_tricks`, does not use the
five-trick adjudication bound, and produces no proof, counterexample, rest-trick
or point assignment, decided winner, settlement basis, or final settlement.
Actual later play determines the result and achieved levels.

The original declaration remains authoritative. Hand, announced Schneider,
announced Schwarz, ouvert, and supported overbid requirements are unchanged.
Requesting continuation creates no new optional Schneider or Schwarz obligation.
Suit, Grand, Null, Null Hand, Null ouvert, and Null ouvert Hand remain accepted
where their ordinary declaration is valid.

## Supported workflows and boundaries

The contract supports flat `live_decision` and `post_game_review`, Immediate
Analysis, otherwise supported Multi-Step phases, Policy Comparison, and local
`actual_card_played` review. It requires an incomplete neutral game and is
exclusive with every shortening or ending, impossible Null, completed play,
list modes, and unrelated top-level workflows.

The separate historical contract supports completed normal games with a timed
continuation event, decision snapshots, review, datasets, statistics, rolling
evaluation, and partition audits; see
[Historical defender open-play continuation](historical_defender_open_play_continuation.md).
General corrected-play handling, new tactics, shortened endings after
continuation, and four-player tables are not added. ISkO 4.4.6 is a separate final workflow documented in
[Open card throw](open_card_throw.md). Accepted exact adjudication remains documented
in [Defender open play](defender_open_play.md).

See
[`examples/defender_open_play_continuation.json`](../examples/defender_open_play_continuation.json)
for the deterministic live example.
