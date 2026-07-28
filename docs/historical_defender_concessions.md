# Historical defender concessions

Version-1 `historical_game_input` supports a structured defender concession
under ISkO 4.4.3:

```json
{
  "game_end_reason": "defender_concession",
  "game_end": {
    "schema_version": 1,
    "kind": "defender_concession",
    "conceding_defender_player_id": "player-b",
    "concession_form": "explicit_verbal"
  }
}
```

The conceding ID is an exact, non-padded stable participant ID and must identify
one of the two defenders. That defender binds the complete defending party. The
other defender is derived in fixed seat order; no consent field or second-
defender response exists. Output reports `liable_party: "defenders"` and
`joint_liability: true`, without creating individual defender settlement.

`concession_form` accepts exactly `explicit_verbal` and
`adjudicated_unambiguous_conduct`. The latter means the source record already
contains the conduct adjudication. Both forms score identically. The engine does
not parse free text, interpret gestures, or convert exposed cards, open card
throwing, defender open play, or rest-trick claims into concession.

## Prefix and replay

The event may follow zero through 29 actual plays. The existing exact historical
replay validates ownership, order, follow obligations, consecutive tricks, and
leaders. One final trick may contain one or two plays; its cards and points stay
unresolved. Concession after all 30 playable cards is invalid.

Replay reconstructs all remaining hands only to validate complete accounting.
Output includes remaining hand sizes, event timing, and the next player if play
had continued, but never emits reconstructed remaining hands. Continued play is
not part of this event and output fixes `continued_play_requested` to `false`.

Completed-trick points and applicable skat points remain observed. Current-
trick and remaining-hand points remain unresolved. Observed and unresolved
points reconcile to 120; no unresolved points are assigned, and
`remaining_points_recipient` remains null.

## Adjudication and settlement

Historical adjudication reuses the flat `DefenderConcession` and
`adjudicate_defender_concession(...)` behavior. An undecided game becomes a
declarer win, normally at the simple declared level. A declarer or defender win
already secured before concession remains binding. Optional Schneider or
Schwarz is not inferred from unfinished play.

Suit and Grand preserve matadors, Hand, announcements, ouvert, mandatory levels,
and supported overbid-required values. Existing bounded mandatory-level handling
may award a still-required level; a level already failed preserves a declarer
loss. Null, Null Hand, Null ouvert, and Null ouvert Hand use their fixed values
and completed declarer-trick ownership. Unsupported overbid Null remains invalid.

## Historical workflows

Snapshots, review decisions, and version-1 training samples are generated once
per actual played card and never for the concession event. Zero-decision and
zero-sample records are valid. Feature generation remains version `1`, and the
target remains `actual_card_played`. Event identity, concession form, final
result, settlement, and unresolved points stay outside decision-time features.

Partition audits retain exact stable-player membership, including zero-sample
records. Historical opponent statistics give every participant one game of
weight and use final settlement as winner authority. Rolling evaluation accepts
defender concessions as earlier source games and zero-through-29-decision target
games. It adds no concession-specific count, signal, profile field, policy,
prediction target, or coaching judgment.

Use the example with:

```powershell
python main.py --input examples/historical_grand_defender_concession.json
python main.py --input examples/historical_grand_defender_concession.json --historical-decision-snapshots
python main.py --input examples/historical_grand_defender_concession.json --historical-game-review
```

Historical defender open play, open-card throwing, continued play after the
event, concession-choice prediction, natural-language interpretation, learned
models, and other historical end kinds remain unsupported.
