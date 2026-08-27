# v1 official-rule evidence

## Purpose

Issue #201 closes the bounded `v1.0.0` official-rule evidence gate B-01 for
R-01, card ordering and card points, and R-06, Suit and Grand game values. It
adds independent executable evidence without changing product behavior, rule
interpretation, public contracts, Schemas, examples, generated scenarios, or
Package metadata.

The executable oracle is
[`tests/test_v1_official_rule_evidence.py`](../tests/test_v1_official_rule_evidence.py).
Its expected deck, points, effective-category sequences, base values, matador
counts, declaration variants, and normalized flags are test-owned literals. It
does not import production expectation constants such as `CARD_POINTS`,
`JACK_STRENGTH`, `SUIT_GAME_RANK_STRENGTH`, `NULL_RANK_STRENGTH`, `GAME_TYPES`,
or a production base-value mapping.

## Primary source

The primary source is the official DSkV November 2022 ISkO/SkWO publication:

<https://dskv.de/app/uploads/sites/43/2022/11/ISkO-2022.pdf>

The evidence uses only these cited sections:

| Sections | Evidence derived from the source |
| --- | --- |
| 1.2.1-1.2.2 | Four suits, eight cards per suit, 32 unique cards, literal card-point values, 30 points per suit, and 120 total points. |
| 2.2.1-2.2.4 | Suit, Grand, and Null effective categories, trump membership, and strongest-to-weakest card orders. |
| 2.4.1 | Literal base values: Clubs `12`, Spades `11`, Hearts `10`, Diamonds `9`, and Grand `24`. |
| 2.5.1-2.5.8 | Base game level, matador levels, Hand, Schneider announced, Schwarz announced, Ouvert, and multiplication by the contract base value. |

No secondary summary supplies an expected executable value.

## R-01 oracle

The deck and point oracle contains all 32 literal Cards. It proves:

* exactly eight unique Cards in each of Clubs, Spades, Hearts, and Diamonds;
* Ace `11`, Ten `10`, King `4`, Queen `3`, Jack `2`, and Nine/Eight/Seven `0`;
* exactly 30 points in each suit; and
* exactly 120 points in the deck.

The ordering oracle contains 25 literal strongest-to-weakest effective-category
sequences:

| Contract family | Sequence count | Pairwise comparisons |
| --- | ---: | ---: |
| Four Suit games | 16 | `4 * (C(11, 2) + 3 * C(7, 2)) = 472` |
| Grand | 5 | `C(4, 2) + 4 * C(7, 2) = 90` |
| Null | 4 | `4 * C(8, 2) = 112` |
| **Total** | **25** | **674** |

For each of the six game types, the sequences partition the same literal
32-Card deck exactly once. Every Card is checked against its expected effective
category and trump status. Every stronger/weaker pair within each category is
then checked through `get_card_strength()`, giving exactly 674 strict
comparisons without relying on production strength numbers.

## R-06 oracle

The declared-value oracle crosses the five literal base values with every
supported matador count and these five canonical variants:

| Variant | Supplied flag | Normalized flags in order `hand_game`, `schneider_announced`, `schwarz_announced`, `ouvert` | Added declared levels |
| --- | --- | --- | ---: |
| `simple` | none | `false, false, false, false` | 0 |
| `hand` | `hand_game` | `true, false, false, false` | 1 |
| `schneider_announced` | `schneider_announced` | `true, true, false, false` | 2 |
| `schwarz_announced` | `schwarz_announced` | `true, true, true, false` | 3 |
| `ouvert` | `ouvert` | `true, true, true, true` | 4 |

Suit games use literal matador counts `1..11`; Grand uses `1..4`. For every row,
the test independently derives:

```text
declared game level = matadors + 1 + added declared levels
declared game value = literal base value * declared game level
```

The exact matrix is:

| Contract family | Arithmetic | Rows |
| --- | --- | ---: |
| Four Suit games | `4 * 11 * 5` | 220 |
| Grand | `1 * 4 * 5` | 20 |
| **Total** | | **240** |

Each row checks declaration normalization,
`calculate_suit_or_grand_game_level()`, `calculate_game_value()`, and the exact
`build_game_value_summary()` result.

## Settlement boundary

The 240 rows prove declared/pre-result value only. They do not claim complete
official outcome or Settlement coverage.

`game_value_summary` owns the declaration, matador, base-value, and announced-
level result before play outcome is applied. `final_settlement_summary` remains
the owner of achieved Schneider/Schwarz levels and the final effective value.
The focused boundary test starts with a simple Grand declared value of `48` and
proves that a completed Schneider/Schwarz result leaves that declared value
unchanged while Final Settlement alone produces effective value `96`.

Broader Settlement behavior remains governed by the approved bounded R-17
contract and Settlement Normative Matrix version `3`.

## Closure

The executable evidence establishes all frozen Issue #201 counts:

* 32 unique Cards;
* 30 points per suit and 120 total points;
* 25 effective-category sequences;
* 674 strict pairwise ordering comparisons;
* 220 Suit declared-value rows;
* 20 Grand declared-value rows; and
* 240 total declared-value rows.

At Issue #201 closure, R-01 and the bounded v1 interpretation of R-06 were
therefore `satisfied`. B-01 was closed without product-code change; the
remaining blockers were B-02 through B-07, and the next action was Issue #202.
