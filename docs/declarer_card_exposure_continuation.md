# Declarer card exposure continuation

This document describes the bounded ongoing-play branch of ISkO 4.4.4. It
applies after the declarer exposes every remaining hand card and at least one
defender rejects the attempted shortening. The game does not end. All current
remaining declarer cards become public to all three players and play continues
under the ordinary trick rules.

## Separate contract

Continuation uses top-level `game_continuation`, not the game-ending
`game_shortening` union:

```json
{
  "game_continuation": {
    "schema_version": 1,
    "kind": "declarer_card_exposure",
    "exposure": {"form": "laid_open"},
    "claimed_play_level": "schneider",
    "defender_responses": [
      {"player": "left", "response": "continue", "form": "explicit"},
      {
        "player": "right",
        "response": "accept",
        "form": "unambiguous_conduct"
      }
    ],
    "public_declarer_cards": ["CA", "C10", "CJ"]
  }
}
```

This version-1 object is the `declarer_card_exposure` member of the
`game_continuation` union. Unknown properties are rejected. `laid_open` forbids `shown_to_player`;
`shown_to_defender` requires one concrete defender. Once continuation is
requested, visibility is `all_players` regardless of who initially saw the
cards.

Exactly both concrete defenders must occur once. Responses are `accept` or
`continue`, with an externally classified `explicit` or
`unambiguous_conduct` form. At least one response must be `continue`. Two
acceptances are rejected with guidance to use the accepted
`game_shortening.kind = "declarer_card_exposure"` workflow. Input order has no
semantic effect; output uses deterministic concrete-player order.

## Public hand and information control

`public_declarer_cards` is the complete current declarer hand, not necessarily
the original exposed list. Cards played since exposure are omitted. The list
contains `1..10` valid unique cards and is authoritative even when independent
confirmation is unavailable.

The resolver checks reliable local-hand ownership, opponent hand-size and play
count evidence, completed tricks, the current trick, legacy played cards, known
skat cards, and the local defender hand. Contradictions and count mismatches are
rejected. An independently exact local declarer-hand match reports `confirmed`;
otherwise valid incomplete evidence reports `not_verifiable` without hiding or
changing the supplied cards.

The exception applies only to the concrete declarer and listed cards. The
co-defender hand and skat remain hidden unless independently authorized by
existing rules. Cards thrown or exposed by an accepting defender in reaction
to the attempted shortening are taken back and must not be supplied as public
information. The continuation does not authorize future plays, future trick
winners, or arbitrary post-game opponent information in live analysis.

## Analysis and simulation

Flat `live_decision` and `post_game_review` positions support Immediate
Analysis, supported Multi-Step phases, Policy Comparison, and flat review with
`actual_card_played`. A local declarer's hand must exactly match the public
hand. A local defender's actual card continues to use ordinary local-hand and
follow-suit validation.

Every hidden-world sample assigns exactly the public cards to the declarer. No
additional card enters that hand, and no public declarer card enters a defender
hand or the skat. Immediate candidate rollouts use the same exact hand and
otherwise retain their existing behavior.

Confirmed attributed failure-to-follow evidence may further constrain unknown
defender and skat assignments. The exact public declarer hand remains
authoritative, and a conflict with a persistent void constraint is rejected.
The continuation response and claimed level never become inference evidence.

Multi-Step samples one coherent private root per path. The exposed declarer hand,
both defender hands, and hypothetical skat retain their root ownership through
opponent preparation and trick completion. A card is removed only when its owner
plays it. Policy Comparison samples one shared root and gives every policy an
equal independent immutable copy. Local card-selection policies never receive
private root ownership, and no tactical policy is added or changed. See
[Coherent hidden-world simulation](coherent_hidden_world_simulation.md).

## Claimed level and result

Suit and Grand preserve `simple`, `schneider`, or `schwarz` as event
provenance. All four Null variants permit only `simple`. The stable status is
`continuation_required_no_immediate_settlement_effect`.

The requested level is not an accepted claim, declaration, mandatory
announcement, or achieved level. Failure to reach it does not itself cause a
loss. The continuation produces no winner, point assignment, game end, or
settlement. Actual completed play and the original declaration determine the
later result and valuation.

## Boundaries

The flat contract is exclusive with active `game_shortening`, legacy endings,
normal completion, impossible Null, completed play, list modes, and unrelated
top-level workflows. Historical continuation uses the separate stable-ID
`game_events` contract and complete-game replay.

Declared-Ouvert analysis reuses this exact-hand infrastructure and deterministically
deduplicates identical declarer evidence in favor of source `declared_ouvert`.
The historical counterpart supports one continuation followed by one existing
terminal shortening, but this flat continuation still adds no terminal
settlement itself. Neither form adds multiple continuations, arbitrary event
streams, new policies, or
behavioral/Bayesian or broader hidden-card inference or proof that the sampled
world is the real deal. The bounded structural model is documented in
[Hidden-card inference](hidden_card_inference.md).
Bounded exact ISkO 4.4.5 adjudication is a
separate final workflow documented in [Defender open play](defender_open_play.md).
ISkO 4.4.6 is the separate final non-continuing workflow documented in
[Open card throw](open_card_throw.md).
The sibling ongoing 4.4.5/4.1.6 workflow is documented in
[Defender open play continuation](defender_open_play_continuation.md).
The timed complete-game form is documented in
[Historical declarer-card-exposure continuation](historical_declarer_card_exposure_continuation.md).

See
[`examples/declarer_card_exposure_continuation.json`](../examples/declarer_card_exposure_continuation.json)
for the deterministic live example.
