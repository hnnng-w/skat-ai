# Examples

This document describes the example input files in `examples/`.

## Live decision examples

These examples represent ongoing positions where the tool recommends a card.

| File | Purpose |
|---|---|
| `grand_second_position.json` | Grand game, local player acts second. Default incomplete game-value example. |
| `grand_second_position_with_metadata.json` | Grand second-position example with strategic metadata. |
| `grand_third_position.json` | Grand game, local player acts third. |
| `grand_leading.json` | Grand game where local player leads the trick. |
| `hearts_leading.json` | Suit game example. |
| `null_second_position.json` | Null game example. |

## Midgame examples

| File | Purpose |
|---|---|
| `grand_midgame_declarer_ahead.json` | Midgame position where declarer is ahead by known points. |
| `grand_midgame_defenders_ahead.json` | Midgame position where defenders are ahead by known points. |

## Post-game review examples

| File | Purpose |
|---|---|
| `grand_post_game_known_skat.json` | Post-game review with known skat and completed tricks. |
| `grand_complete_declarer_win.json` | Complete game where declarer wins. Also demonstrates `bid_value` and partial ISkO performance-rating metadata. |
| `grand_complete_declarer_loss.json` | Complete game where declarer loses. Also demonstrates fixed three-player ISkO counterparty points. |

## Claim and concession examples

| File | Purpose |
|---|---|
| `grand_claimed_remaining_tricks.json` | Declarer claims remaining tricks. |
| `grand_declarer_conceded_remaining_tricks.json` | Declarer concedes remaining tricks. |
| `grand_defenders_conceded_remaining_tricks.json` | Defenders concede remaining tricks. |

## Overbid examples

| File | Purpose |
|---|---|
| `grand_overbid_declarer_card_points_win.json` | Declarer wins by card points but loses settlement because the game is overbid. |

## Example commands

Run a basic analysis:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Run a post-game review example:

```powershell
python main.py --input examples/grand_post_game_known_skat.json --output outputs/post_game_review.json
```

Run an overbid example:

```powershell
python main.py --input examples/grand_overbid_declarer_card_points_win.json --output outputs/overbid_test.json
```

Run a claim example:

```powershell
python main.py --input examples/grand_claimed_remaining_tricks.json --output outputs/claim_test.json
```

Run a declarer-concession example:

```powershell
python main.py --input examples/grand_declarer_conceded_remaining_tricks.json --output outputs/declarer_concession_test.json
```

Run a defenders-concession example:

```powershell
python main.py --input examples/grand_defenders_conceded_remaining_tricks.json --output outputs/defenders_concession_test.json
```

## Multi-step simulation examples

Run a two-step simulation:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Run a two-step simulation with explicit opponent policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --opponent-lead-policy highest_point --opponent-response-policy basic_trick_play
```

## Policy comparison examples

Run a policy comparison:

```powershell
python main.py --input examples/grand_second_position.json --compare-policies
```

## Notes

The examples are also used as regression fixtures in `tests/test_examples.py`.

When adding new examples:

- keep card notation valid
- avoid duplicate known cards
- keep point totals within 120
- set `game_end_reason` consistently with known card points
- prefer `completed_tricks` over `played_cards`
- use `performance_rating_system: "isko_list"` only when partial ISkO rating output should be demonstrated