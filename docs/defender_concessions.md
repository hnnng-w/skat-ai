# Defender concessions

This document describes the bounded version-1 adjudication for a defender
concession under ISkO 4.4.3 with the applicable effects from ISkO 4.1.3 through
4.1.5.

## Scope

The structured contract is supported only in the flat position/result workflow
with `analysis_mode: "post_game_review"`. It records an already accepted game
end. The declarer has not requested continued play.

One concrete defender concedes for the complete defending party. Joint
liability means the other defender does not need to consent and has no veto.
The engine does not assign blame, points, or settlement separately to either
defender.

The contract does not parse natural language or decide whether conduct was
unambiguous. `adjudicated_unambiguous_conduct` means that determination was made
externally before the input was created.

## Input contract

Use the existing `game_shortening` union with exactly schema version `1`:

```json
{
  "analysis_mode": "post_game_review",
  "declarer_player": "me",
  "game_shortening": {
    "schema_version": 1,
    "kind": "defender_concession",
    "conceding_player": "left",
    "concession_form": "explicit_verbal"
  }
}
```

`conceding_player` must be exactly `me`, `left`, or `right`. The declaration
must identify a different concrete `declarer_player`, so the conceding player is
necessarily a defender. Missing, unknown, padded, and unsupported identities
are rejected.

Supported forms are:

* `explicit_verbal`
* `adjudicated_unambiguous_conduct`

All properties are required and unknown properties are rejected. There is no
partner-consent or free-text field.

## Workflow and exclusivity

Structured defender concession requires incomplete normal play and enough final
declaration information to calculate the game value and any supported overbid
requirement. It may occur between tricks or during an incomplete current trick.
The current trick is not completed or simulated.

It is rejected with:

* live-decision analysis
* any active legacy `game_end_reason`
* impossible Null settlement
* all ten completed tricks
* an unvalued declaration
* an overbid requirement beyond the supported Schneider and Schwarz levels
* Multi-Step simulation or policy comparison
* historical-game, training-dataset, opponent-statistics, partition-audit,
  list-performance, or other unrelated workflows

An absent legacy reason or neutral `not_ended` remains compatible. The other
version-1 union member, `declarer_concession`, remains unchanged.

## Decision before concession

The adjudicator derives one of:

* `undecided`
* `declarer_already_won`
* `defenders_already_won`

For Suit and Grand, 61 observed declarer points secure the base game and 60
observed defender points secure it for the defenders. Mandatory contract
conditions remain relevant:

* Schneider announced or an overbid-required Schneider level has failed when
  defenders already have more than 30 observed points.
* Schwarz announced, ouvert, or an overbid-required Schwarz level has failed
  when reliable completed-trick ownership shows a defender trick.
* A base declarer win remains undecided while a mandatory Schneider or Schwarz
  condition is still pending.
* An overbid requirement more than two levels above the declared multiplier is
  rejected rather than awarded.

For every Null variant, a reliable completed declarer trick means the contract
was already lost. Otherwise an incomplete Null game remains undecided. Card
points do not determine the Null result.

Cards in an incomplete current trick are never treated as completed-trick
ownership evidence.

## Adjudicated result

An undecided game becomes a final adjudicated declarer win under ISkO 4.1.4. A
still-possible mandatory announced or supported overbid-required level is
awarded under the bounded application of ISkO 4.1.5.

If the game was already decided, ISkO 4.1.3 preserves that winner. In
particular, a declarer who had already lost remains the loser despite the later
defender concession.

`game_shortening_summary` records:

* the concrete conceding player
* `liable_party: "defenders"`
* `joint_liability: true`
* the pre-concession decision state and final winner
* `winner_basis` as either `defender_concession` or
  `preexisting_game_decision`
* deterministic rule sections
* `continued_play_requested: false`
* the applied settlement-level policy

## Points

Observed declarer and defender points remain unchanged. Unplayed points remain
in `points_remaining` and no side receives them:

```json
{
  "remaining_points_recipient": null,
  "remaining_points_assigned": 0
}
```

The adjudicated winner is independent from point completion. No fictitious
120-point result is created, and no cards from an incomplete trick or remaining
hands are assigned.

## Settlement

An undecided Suit or Grand game uses the declared game value, including its
matadors, Hand status, and declared levels. A supported overbid-required value
replaces it when applicable. The resulting declarer win is positive.

Optional unannounced Schneider or Schwarz is not inferred from unfinished play.
Mandatory announced or overbid-required levels are reported as
`mandatory_level_awarded`, not `achieved_during_play`. The settlement basis
separates the mandatory source, achieved-level application, and overbid
valuation.

For an already-decided game, only levels secured by evidence before concession
can affect settlement. Schneider needs sufficient observed points. Schwarz
needs reliable complete trick ownership; hypothetical continuation and an
incomplete current trick are not proof.

Null, Null Hand, Null ouvert, and Null ouvert Hand use their fixed values. A
prior completed declarer trick preserves the doubled loss; otherwise the
adjudicated win uses the positive fixed value.

## Compatibility and limitations

The legacy `defenders_conceded_remaining_tricks` reason remains valid and still
assigns all remaining card points to the declarer. It is a simplified
compatibility workflow, cannot coexist with `game_shortening`, and is not
silently reinterpreted as structured adjudication.

Version 1 does not support continued play under ISkO 4.1.6, declarer card
exposure, defender open play, open card throwing, natural-language detection,
solver-backed proof, or historical defender-concession records. These remain
separate future workflows.
