# Scoring and settlement

This document explains card points, game value, and single-game settlement in `skat-ai`.

## Card points

Skat card points are:

| Rank  | Points |
| ----- | -----: |
| Ace   |     11 |
| Ten   |     10 |
| King  |      4 |
| Queen |      3 |
| Jack  |      2 |
| Nine  |      0 |
| Eight |      0 |
| Seven |      0 |

A complete game has 120 card points.

## Game value

`game_value_summary` calculates the declared game value.

For suit and grand games, the game value is based on:

```text
base_value * game_level
```

Base values:

| Game type | Base value |
| --------- | ---------: |
| Clubs     |         12 |
| Spades    |         11 |
| Hearts    |         10 |
| Diamonds  |          9 |
| Grand     |         24 |

The game level is based on:

* matador multiplier
* hand game
* Schneider announced
* Schwarz announced
* ouvert

Suit and Grand declarations are canonical and cumulative. Schneider announced
includes Hand; Schwarz announced includes Schneider announced and Hand; ouvert
includes Schwarz announced, Schneider announced, and Hand. Omitted implied
prerequisites are normalized to `true`, while explicitly false prerequisites
are rejected before game-value calculation.

## Matadors

Suit and grand games use matadors.

If `matadors` is explicitly provided in the input, the explicit value is
authoritative and is used as provided. Non-null top-level `matadors` overrides
nested `game_declaration.matadors`. Suit games accept `1..11`; Grand games
accept `1..4`; and explicit `0` is invalid.

If top-level and nested `matadors` are missing or `null`, the count is unknown
and the engine may infer it when known ownership is deterministic.

Automatic inference can use known declarer-card context from:

* the local declarer `hand`
* `skat`, when available and allowed by the analysis mode
* completed-trick ownership facts, but only when `declarer_player` is concrete and the trick provides both `cards` and ordered `players`

Completed-trick inference can use declarer or defender perspective histories when the concrete declarer seat is known. It does not use `winner_role`, `winner_player`, or trick winner alone; it does not infer completed-trick ownership when `declarer_player` is missing or `unknown`; and it does not guess hidden cards. If ownership is incomplete or inconclusive, inference falls back to the existing known-card behavior.

If matadors still cannot be inferred for a suit or grand game, the game value remains incomplete.

Null games do not use matadors.

## Null games

Null games use fixed game values.

Null Hand and Null ouvert are independent flags. In particular, Null ouvert
does not imply Null Hand. Schneider announced, Schwarz announced, and matador
values are invalid for Null declarations.

Typical supported Null values:

| Type             | Value |
| ---------------- | ----: |
| Null             |    23 |
| Null hand        |    35 |
| Null ouvert      |    46 |
| Null ouvert hand |    59 |

## Schneider and Schwarz

`game_result_summary` tracks raw and effective Schneider/Schwarz status.

The engine distinguishes between:

* raw point-based Schneider/Schwarz status
* effective final-state-aware Schneider/Schwarz status

This prevents incomplete games from being treated as final Schneider or Schwarz outcomes too early.

For settlement, Schneider remains point-based: the losing side has 30 or fewer
card points. Schwarz is stricter: the losing side took zero tricks. Card points
alone do not prove Schwarz, because a zero-point trick still prevents Schwarz.

Suit and Grand Schwarz settlement therefore uses reliable completed-trick
ownership from `completed_tricks[].winner_role`, not card points or the
point-based `effective_schwarz_status` field. When concrete `players` and
declarer identity are known, validation derives the rule winner from `cards`
and checks that `winner_role` matches the canonical side ownership. The same
side-ownership check applies when concrete `winner_player` and declarer identity
are both known. In live-decision input, supplied `winner_role` must be
verifiable from `cards`, `players`, `game_type`, and concrete
`declarer_player`; unverifiable live side ownership is rejected instead of being
trusted by scoring or settlement summaries.

## Score summary

`score_summary` combines explicit points and completed-trick points.
Explicit side points exclude card points already represented by
`completed_tricks`; completed-trick cards provide their own point contribution.
Advanced simulation states preserve this reusable-state invariant by appending a
completed trick without adding its points to `declarer_points` or
`defender_points`.

Example:

```json
"score_summary": {
  "explicit_declarer_points": 20,
  "explicit_defender_points": 10,
  "completed_trick_declarer_points": 31,
  "completed_trick_defender_points": 25,
  "total_declarer_points": 51,
  "total_defender_points": 35
}
```

## Expected point swing perspective

Immediate card analysis is local-side based. `win_rate` means the local side
wins the trick, not necessarily that the candidate card itself takes the trick.
For a local defender, a partner trick win counts as a local win.

`expected_point_swing` is calculated as:

```text
average_points_won - average_points_lost
```

`average_points_won` and `average_points_lost` are measured from the local
player's side. Multi-step summaries keep the existing
`final_point_swing = declarer_points_gained - defender_points_gained` field and
add `local_point_swing` for local-side ranking. For a local defender,
`local_point_swing = defender_points_gained - declarer_points_gained`.
Multi-step point gains are calculated from canonical total score summaries, so
completed tricks and explicit side points are counted exactly once.

## Game result summary

`game_result_summary` describes the raw result before game-end adjustment.

For Suit and Grand games, the result is card-point based. For normally
completed Null games with ten reliable completed tricks, the result is based on
completed-trick ownership: the declarer wins only if the declarer took zero
tricks. Any declarer trick loses Null, including a trick worth zero card points.
Incomplete Null games are not declared wins merely because the declarer has not
yet taken a trick.

Important fields include:

| Field              | Meaning                                   |
| ------------------ | ----------------------------------------- |
| `declarer_points`  | Known declarer card points.               |
| `defender_points`  | Known defender card points.               |
| `points_remaining` | Remaining unassigned card points.         |
| `is_complete`      | Whether the result is complete. Suit/Grand use assigned card points; Null requires complete reliable trick ownership. |
| `winner`           | Game or contract winner: `declarer`, `defenders`, or `undecided`. |

## Adjusted game result summary

`adjusted_game_result_summary` applies legacy `game_end_reason` assignment or a
structured declarer-concession adjudication.

For claim and concession scenarios, remaining card points are assigned according to the declared game-end reason.

For structured declarer concession, observed points and unplayed points are
preserved. The winner is adjudicated as defenders, and zero remaining points are
assigned.

Examples:

| game_end_reason                       | Remaining points go to |
| ------------------------------------- | ---------------------- |
| `declarer_claimed_remaining_tricks`   | declarer               |
| `defenders_conceded_remaining_tricks` | declarer               |
| `declarer_conceded_remaining_tricks`  | defenders              |
| `not_ended`                           | no assignment          |
| `normal_completion`                   | no assignment          |

The adjusted result is used by final settlement.

## Final settlement

`final_settlement_summary` describes single-game settlement.

It combines:

```text
game_value_summary
adjusted_game_result_summary
overbid_summary
```

It does not calculate full list, series, or tournament performance rating.

That is handled separately by `performance_rating_summary`.

## Effective game value

`effective_game_value` is the value used for settlement scoring.

In normal non-Schneider cases:

```text
effective_game_value = game_value
```

For completed non-null suit and grand games, final settlement may add achieved
Schneider and achieved Schwarz base-value levels:

```text
effective_game_value = game_value + achieved levels * base_value
```

`game_value_summary.game_value` remains the declared/pre-result game value. If
Schneider was announced, that declared value already includes the announcement
level. A successful Schneider announcement adds only the separate achieved
Schneider level. A failed Schneider announcement does not add an achieved
Schneider level.

Achieved Schwarz adds one additional base-value level when reliable ten-trick
ownership proves that the losing side took no tricks. Achieved Schwarz also
implies achieved Schneider, so normal completed Schwarz settlements can include
both achieved levels. If Schwarz was announced, `game_value` already includes the
announced Schwarz level; settlement does not add that declared level again.

In supported Suit/Grand overbid cases:

```text
effective_game_value = required_game_value
```

For `impossible_null_declaration`, the separately selected Suit or Grand
replacement uses:

```text
minimum_multiplier = matadors + 1 + Hand
required_multiplier = max(minimum_multiplier, ceil(bid_value / base_value))
effective_game_value = base_value * required_multiplier
```

Here `Hand` is `1` only when the original Null was Hand. Null ouvert and all
Schneider/Schwarz levels are excluded. The original fixed Null `game_value`
remains unchanged.

## Settlement score

Current settlement scoring:

```text
Declarer wins: settlement_score = effective_game_value
Declarer loses: settlement_score = -2 * effective_game_value
```

Completed non-null suit and grand games include achieved Schneider by adding one base-value level to `effective_game_value`.

Completed non-null suit and grand games include achieved Schwarz by adding one more base-value level, but only when exactly ten reliable completed tricks prove the trick ownership. This applies in either direction: declarer Schwarz and defender Schwarz both affect the effective game value, consistent with achieved Schneider handling.

The public field `declarer_won_by_card_points` is retained for compatibility.
For Suit and Grand it is literal. For Null it mirrors whether the declarer won
the base contract, even though Null is not decided by card points.

If Schneider was announced but the completed game did not result in
`effective_schneider_status == "declarer_made_schneider"`, the declarer loses
for settlement purposes. The card-point `winner` remains unchanged, and
`effective_game_value` remains the declared game value that already includes the
Schneider announcement level.

If Schwarz was announced, the announcement succeeds only when reliable ten-trick
ownership proves declarer Schwarz. If reliable ownership proves any other result,
including a zero-point defender trick or defender Schwarz, the declarer loses for
settlement purposes. If fewer than ten reliable completed tricks are available,
the announced-Schwarz settlement remains incomplete with missing
`complete_trick_ownership`, unless overbid already determines the settlement
loss.

Supported Suit/Grand overbid cases force the declarer into a settlement loss and use the required game value. Overbid takes precedence over announcement failures and achieved levels: `effective_game_value` is `overbid_required_game_value`, and achieved Schneider or Schwarz levels are not added to that overbid-required value.

Structured declarer concession also forces a loss. Suit and Grand retain the
declared value, matadors, Hand, and announced levels. Supported overbid-required
valuation remains applicable. Null uses the fixed declared variant value. In all
cases the score is `-2 * effective_game_value`, no unplayed points are assigned,
and no achieved Schneider or Schwarz level is inferred from unfinished play.

An impossible Null declaration is also an immediate doubled loss, but it has no
card-point winner and requires no points or completed tricks. Zero assigned
points are not interpreted as Schneider or Schwarz. Missing replacement
metadata keeps settlement incomplete instead of inventing a contract.

Legacy claims and concessions assign remaining points. The structured declarer
concession deliberately does not assign them and does not claim future Schwarz.

Example:

```json
"final_settlement_summary": {
  "is_complete": true,
  "declarer_won_by_card_points": true,
  "winner": "declarer",
  "game_value": 48,
  "effective_game_value": 72,
  "bid_value": 60,
  "settlement_score": -144,
  "is_loss": true,
  "is_overbid": true,
  "overbid_required_game_value": 72
}
```

In this example, the declarer won by card points but loses settlement because the game was overbid.

## Performance rating separation

Single-game settlement and performance rating are intentionally separate.

`final_settlement_summary` answers:

* Did the declarer win or lose the individual game?
* What game value or effective game value is used?
* What is the settlement score?

`performance_rating_summary` answers:

* Which performance-rating system is active?
* Which part of the rating system is currently implemented?
* What single-game declarer rating score is calculated?
* Which counterparty/defender points are exposed?

Current partial SkWO-style performance scoring is documented in:

[Performance rating documentation](performance_rating.md)

## Current limitations

* Full official settlement nuances are not completely modeled yet.
* Legacy claim/concession handling assigns remaining points; structured declarer concession does not.
* Neither path simulates remaining tricks or establishes future Schwarz ownership.
* The engine does not yet verify whether a claim was strategically or legally justified.
* Impossible Null settlement remains incomplete when its external replacement selection is unavailable.
* List, series, and tournament performance rating are handled separately and are not fully implemented yet.
* Automatic matador inference is conservative and currently uses known declarer-card context from hand, skat context, and safe concrete-declarer completed-trick ownership facts where possible.
