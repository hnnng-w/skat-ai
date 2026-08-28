# Ouvert-aware simulation

Declared Ouvert makes the declarer's complete current hand public to all three
players. `skatmind` represents that exact ownership with source
`declared_ouvert` and visibility scope `all_players`.

This support applies to every valid existing Ouvert declaration: Suit Ouvert,
Grand Ouvert, Null Ouvert, and Null Hand Ouvert. Suit and Grand retain the
existing Hand, Schneider-announced, and Schwarz-announced dependencies. Null
retains its independent Hand modifier and fixed values. Declaration validation,
matadors, game value, result, overbid, and settlement are unchanged.

## Flat input

An opponent declarer requires the exact complete current hand:

```json
{
  "ouvert": true,
  "declarer_player": "left",
  "public_declarer_cards": ["SK", "SQ", "SJ"]
}
```

`public_declarer_cards` is allowed only for an Ouvert declaration. The declarer
must be `me`, `left`, or `right`. For `left` or `right`, the field is required
and its count must equal the corresponding hand-size field. For `me`, the public
hand is derived from `hand`; an explicitly supplied field must identify exactly
the same cards.

Cards must use valid notation, be unique, and exclude every played, current-
trick, completed-trick, known skat, local defender, or independently public
other-player card. Output uses canonical deck order. Successful reconciliation
is exact and confirmed; contradictions are rejected rather than corrected.

No defender hand is required. A declared-Ouvert hand authorizes no hidden skat
card and no second complete hand.

## Constraint resolution

There is at most one effective public-hand constraint per player. Identical
same-player constraints are deduplicated; contradictory card sets and cross-
player card overlap are rejected. When declared Ouvert and declarer-exposure
continuation describe the same hand, `declared_ouvert` takes precedence while
the continuation event summary remains present.

A defender-open-play continuation may coexist with declared Ouvert. The exact
declarer and exposing-defender hands remain separate, disjoint constraints, and
sampling assigns only the remaining cards to the last hidden hand and skat.

## Immediate Analysis

Every hidden-world sample fixes the exact public declarer hand to its owner. No
additional declarer card is sampled, and no public declarer card enters a
defender hand or skat. If the local player is declarer, the public constraint
must equal the local hand while both defender hands and a hidden skat remain
uncertain.

Under a fixed seed, every local candidate starts from the same public state and
the same unknown-card sample sequence. Legal candidates and the existing Suit or
Grand expected-point objective and Null contract objective are unchanged.
Opponent lead and response preparation receives the same exact ownership facts.
The existing simple policies are not claimed to be optimal Ouvert strategy.

When attributed public play also confirms a failure to follow, the exact Ouvert
hand remains authoritative while hidden-card inference constrains only the
remaining unknown ownership. A conflict between the public hand and confirmed
evidence is rejected rather than reweighted or ignored.

## Multi-Step and Policy Comparison

The root `SimulationContext` retains the exact public hand inside one coherent
private execution world. A declarer play removes that card from the declarer's
ownership; a defender play does not remove an unplayed declarer card. All other
unknown ownership and the hypothetical skat are sampled once at path start and
remain coherent through preparation and completion. Played cards never return
and no extra declarer card is sampled.

Policy Comparison samples one shared root and gives every existing policy an
equal independent immutable copy with the same public constraint and source. No
Ouvert-only policy or precedence rule is added. Supported turn phases and stop
reasons are unchanged. See
[Coherent hidden-world simulation](coherent_hidden_world_simulation.md).

## Historical workflows

Decision snapshots expose the exact shrinking current declarer hand from
decision 1. The snapshot adapter maps the stable declarer to `me`, `left`, or
`right` for each actor and builds a `declared_ouvert` constraint. Historical
Review uses the ordinary reviewed-decision path rather than
`public_exposed_cards_not_supported` solely because the declaration is Ouvert.

The actual card remains a retrospective label. No future play, complete defender
hand, hidden skat, future winner, final result, or settlement enters a decision
state. A normal-completion Ouvert game therefore has 30 reviewed decisions and
zero unavailable decisions unless an independent limitation applies.

Flat post-game review uses the same public constraint, legal-card validation,
decision-quality classification, recommendation gaps, and Null-specific wording.
It does not infer a final result from the declaration.

## Matadors, training, and rolling evaluation

Rule-authorized public declarer cards may contribute declarer ownership to
visible matador inference together with local ownership, public play, and only
legitimately visible skat cards. Hidden defender and skat ownership is not
inferred. Declaration-level validation remains unchanged.

Training samples continue to use feature-generation version `1`, target
`actual_card_played`, and stable `record_id:decision_index` IDs. Declared-Ouvert
cards remain legitimate decision-time `public_exposed_cards`; no Ouvert or
exposure target is added.

Rolling evaluation reconstructs the same snapshots for baseline and profile
predictions under strict game-start as-of safety. Source statistics remain
game-level and settlement-based, while metrics remain decision-weighted. There
is no Ouvert statistic, profile signal, preset, or prediction target.

## Boundaries

This feature adds public ownership information to the existing seeded sampler.
Coherent Multi-Step execution does not add a solver, minimax, complete-contract
proof, learned model, Ouvert-specific strategy, general hidden-card inference,
or proof that a sampled private root matches the real deal. Other hands, hidden
skat cards, future events, and post-game-only evidence remain protected.

The separate bounded exact evidence model is documented in
[Hidden-card inference](hidden_card_inference.md). It uses only structural
decision-time evidence and does not infer from Ouvert declaration behavior,
profiles, results, or settlement.
