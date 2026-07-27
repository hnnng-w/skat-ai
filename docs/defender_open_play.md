# Defender open play

`skat-ai` supports bounded exact post-game adjudication of defender open play
under the November 2022 wording of ISkO 4.4.5.

This branch is different from defender concession and declarer card exposure. A
defender may expose the complete remaining hand only when the declarer cannot
win another trick regardless of every legal choice by the declarer and the
non-exposing defender. The exposing defender may choose a legal,
state-dependent strategy.

## Input

The version-1 `game_shortening` member is:

```json
{
  "schema_version": 1,
  "kind": "defender_open_play",
  "exposing_defender": "left",
  "remaining_hands": {
    "me": ["..."],
    "left": ["..."],
    "right": ["..."]
  },
  "declarer_response": "accept_adjudication"
}
```

The input is accepted only in the flat `post_game_review` position workflow.
It requires a concrete declarer, a concrete exposing defender who is not the
declarer, and exact physical hands for all three players. Cards already in the
current trick are not repeated in those hands. The exposing defender must have
at least one card.

Version 1 accepts only `accept_adjudication`. A
`request_continued_play` response is rejected with guidance to use the separate
ongoing `game_continuation` contract documented in
[Defender open play continuation](defender_open_play_continuation.md).

## Exact evidence

Runtime validation reconciles:

* all completed-trick cards;
* zero, one, or two ordered current-trick cards;
* the three exact remaining hands;
* the local hand and both opponent hand sizes;
* concrete turn order and the next player;
* supplied skat or discarded-card evidence;
* existing concrete ownership evidence.

Exactly 30 cards must be accounted for as in-play cards. The other two deck
cards are inferred as the out-of-play skat or discarded cards. A supplied skat
must match that inferred pair. Cards are never inferred into a missing hand or
moved between hands.

At least one and at most five tricks may remain unresolved. An incomplete
current trick counts as one of those unresolved tricks. Larger positions and
contradictory positions are rejected before search.

## Exact proof

`exact_rest_trick_proof.py` uses immutable states containing canonical hands,
the ordered current trick, the next player, and the game type. It traverses
cards in canonical deck order and memoizes every evaluated state.

The recursive property is: the declarer wins no remaining trick.

* An exposing-defender node is existential. One legal continuation is enough.
* A declarer node is universal. Every legal continuation must preserve the property.
* A non-exposing-defender node is universal. Every legal continuation must preserve the property.

The exposing defender can therefore adapt to the reached state; no fixed card
order is required. The other defender is not assumed to cooperate. The solver
reuses `get_legal_cards` for follow-suit and `get_trick_winner` for each completed
trick. It contains no sampling, random seed, Monte Carlo fallback, opponent
policy, or tactical heuristic.

The proof result is always complete inside the supported bound. It reports
`valid` or `invalid`, the quantifier policy, deterministic evaluated and
memoized state counts, and one canonical explanatory line. One line is not the
proof by itself; completeness comes from exhaustive traversal. An invalid line
contains a declarer-trick counterexample.

## Adjudication

A valid proof ends the game, assigns every remaining trick and all outstanding
points to the defending party, and settles from that guaranteed final state.
The assignment source is `exact_rest_trick_proof`. Guaranteed trick ownership
can establish Schwarz, but it is not described as normally played cards.

An invalid proof ends the game and records that all rest tricks and outstanding
points go to the declarer by rule. If the game was undecided, Suit or Grand is
awarded as a simple declarer win under ISkO 4.1.4. A mandatory announced or
supported overbid-required Schneider or Schwarz level is awarded only under the
bounded ISkO 4.1.5 conditions. Rule-assigned tricks do not create optional
achieved Schneider or Schwarz.

For Null, a prior declarer trick preserves an existing loss. Otherwise a valid
proof produces a declarer win because no declarer trick remains possible. An
invalid pre-decision claim also produces a declarer win because the defending
party caused the invalid open play; rule-assigned tricks are not treated as
played Null tricks. Null, Null Hand, Null ouvert, and Null ouvert Hand retain
their fixed values.

ISkO 4.1.3 preserves every result already decided before exposure. Rule
assignment, the preexisting or adjudicated winner, achieved levels, mandatory
awarded levels, overbid-required valuation, and final settlement remain separate
output concepts.

## Output and privacy

`game_shortening_summary` identifies both defenders, exposes the opening
defender's complete open hand, reports exact proof metadata, and includes the
party-level rest-trick assignment. `adjusted_game_result_summary` records final
point accounting, and `final_settlement_summary.settlement_basis` records the
proof and level sources.

The declarer's and non-exposing defender's exact hands are private post-game
proof evidence. They are not emitted as hand arrays, CLI text, or unredacted
proof-line cards. If the local player is one of those private actors, the normal
output position hand is suppressed for this workflow. The exact evidence is not
turned into an Immediate, Multi-Step, Policy Comparison, or live-analysis hand.

## Boundaries

This feature does not implement:

* more than five unresolved tricks;
* heuristic or Monte Carlo proof;
* isolated decisive-card showing;
* historical defender-open-play records or snapshots;
* training records from shortened games;
* general coherent hidden-world solving;
* ISkO 4.4.6 open throwing;
* four-player tables.

Existing concessions, accepted declarer exposure, exposed-declarer
continuation, legacy reasons, normal completion, impossible Null, and unrelated
analysis workflows remain separate.

Continued play under ISkO 4.1.6 is also separate. It uses only the public
exposing-defender hand, does not import the private exact proof hands, does not
call this solver, and does not produce adjudication or settlement.
