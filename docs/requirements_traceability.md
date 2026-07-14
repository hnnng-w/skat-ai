# Requirements traceability

This document is the authoritative audit of rule and product support in
`skat-ai`. It records the `v0.6.0` implementation baseline and does not claim
complete compliance with the official rules.

## Normative sources

The normative rules source is the official November 2022 publication:

* [Official ISkO/SkWO 2022 PDF](https://dskv.de/app/uploads/sites/43/2022/11/ISkO-2022.pdf)

ISkO governs an individual game: cards, bidding, declaration, play, game end,
valuation, and settlement. SkWO governs organized competition: table and list
procedures, performance calculation, standings, event administration, and
records. The explanatory `Wissenswertes fur Skatspieler` pages in the same PDF
are useful guidance, but are not numbered ISkO or SkWO provisions.

Analysis, simulation, historical-data, training-data, recommendation, and
opponent-model behavior are `skat-ai` product requirements. They are not
official game rules. Fixed three-player operation is a product constraint;
SkWO permits three-player tables in section 6.1.1 but does not define a
software product limited to them.

Rule references below are section numbers from the November 2022 PDF. The audit
was verified against source modules, schemas, examples, validation scripts, and
focused tests at the published `v0.6.0` baseline.

## Status vocabulary

Only these values are used in the `Current status` column:

* `supported`: implemented behavior has direct validation and focused tests for
  the stated bounded requirement.
* `partially_supported`: useful behavior exists, but a stated rule, input,
  continuity, validation, or coverage gap remains.
* `planned`: an approved direction has no implementation yet.
* `not_supported`: the current repository has no implementation of the stated
  requirement or cannot produce the required result.
* `not_applicable`: the requirement does not apply to the stated product area.
* `decision_required`: product intent is not sufficiently defined.

An output field alone is not evidence of support.

## ISkO individual-game matrix

| Requirement | Source | Rule section | Current status | Current implementation | Required input or information | Known limitation | Required validation or tests | Target milestone | Required before v1.0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Card ordering and card points | ISkO | 1.2.1-1.2.2; 2.2.1-2.2.4 | `supported` | `rules.py` defines all points and Suit, Grand, and Null rank strength; `test_rules.py` and opponent-policy tests exercise scoring and ordering. | Valid card notation and game type. | Tests do not use one exhaustive table that asserts every card/rank combination. | Add a parameterized full point and rank-order table while retaining trick tests. | v1.0 | Yes |
| Trump rules | ISkO | 2.2.1-2.2.4 | `supported` | `get_trump_suit`, `is_trump`, and effective-suit logic implement Suit jacks plus trump suit, Grand jacks, and no Null trumps. | Game type and card. | Does not adjudicate rule violations or exposed-card consequences. | Retain focused Suit, Grand, Null, and all-jack ordering tests. | v1.0 | Yes |
| Following suit and legal-card rules | ISkO | 4.1.1-4.1.2; 4.2.1-4.2.3 | `supported` | `get_legal_cards` requires the led effective suit or trump when held and otherwise permits any card. | Current hand, led cards, and game type. | Position legality is supported; retrospective revoke adjudication and ISkO 4.1.3-4.1.6 consequences are not. | Exhaustive follow-suit/trump tests for all game types and historical revoke cases when full histories are added. | v1.0 | Yes |
| Trick resolution | ISkO | 4.3.1-4.3.4 | `supported` | `get_trick_winner` and completed-trick validation derive the winner from three cards and player order. | Three ordered cards, game type, and player order for ownership validation. | Partial legacy histories without players cannot prove a concrete winner identity. | Retain rule-winner tests and require strict ownership validation for complete historical records. | v1.0 | Yes |
| Bidding and declarations | ISkO | 3.3.1-3.3.11; 3.5.1-3.5.6 | `partially_supported` | `GameDeclaration` represents the final contract and bid value; runtime validation canonicalizes Suit/Grand declaration dependencies and checks Null exclusions. | Final game type, declaration modifiers, optional matadors, and optional bid value. | No auction sequence, bid/hold/pass model, declarer derivation, legal bid-value validation, or passed-in game. | Retain final-declaration dependency and precedence tests; a full auction requires a separate product decision and tests. | v1.0 plus product decision | Final declaration: Yes; full auction: Decision required |
| Suit and Grand game values | ISkO | 2.4.1; 2.5.1-2.5.8 | `partially_supported` | Base values, cumulative canonical declaration levels, and multiplier calculation are implemented in `game_declaration.py` and `game_value.py`. | Valid final declaration and known matador count. | The complete official outcome and settlement combination matrix is not yet covered. | Parameterize every base value and retain legal-level, invalid-dependency, and boundary-count tests. | v1.0 | Yes |
| Null game values | ISkO | 2.4.2; 2.5.9 | `supported` | Null, Null Hand, Null ouvert, and Null ouvert Hand map to 23, 35, 46, and 59 with focused tests. | Null game type plus Hand and ouvert flags. | This row covers fixed values, not impossible Null overbid settlement. | Retain all four variant tests and declaration-exclusion tests. | v1.0 | Yes |
| Matadors | ISkO | 2.3.1-2.3.4; 2.5.2-2.5.3 | `partially_supported` | Explicit Suit `1..11` and Grand `1..4` bounds plus conservative inference from known declarer cards and concrete completed-trick ownership are tested. | Explicit count or deterministic declarer ownership including the skat where known. | No exhaustive reconstruction from a complete game; ambiguous ownership remains incomplete. | Retain boundary, with/without sequence, Hand skat, complete-history, and ambiguity tests. | v1.0 | Yes |
| Hand games | ISkO | 2.1.1-2.1.2; 2.6.1-2.6.4; 3.5.1 | `partially_supported` | `hand_game` contributes one game-value level and is enforced as a prerequisite for Suit/Grand announcements. | Final declaration and cards needed for valuation. | The engine cannot prove the skat was not inspected and does not model pickup/Hand history completely. | Add historical pickup/Hand validation and retain declaration hierarchy and skat-dependent valuation tests. | v1.0 | Yes |
| Schneider and Schwarz | ISkO | 2.5.4-2.5.8 | `partially_supported` | Card-point Schneider and ten-trick ownership-based Schwarz affect settlement; announced levels are canonicalized with their required Hand hierarchy. | Complete points; ten reliable trick owners for Schwarz; declaration flags. | Claims do not establish Schwarz; full rule-violation outcomes are absent. | Retain both-party, zero-point-trick, announcement, higher-level, incomplete-history, and invalid-declaration tests. | v1.0 | Yes |
| Ouvert declarations | ISkO | 2.5.8-2.5.9; 2.6.5; 3.5.1 | `partially_supported` | Suit/Grand ouvert is canonicalized to Hand, Schneider announced, and Schwarz announced; independent Null ouvert and Null Hand values are calculated. | Final declaration and completed result. | Exposure timing and card layout are not represented. | Retain invalid-combination, Suit/Grand all-trick, and Null no-trick outcome tests. | v1.0 | Yes |
| Overbid handling | ISkO | 3.5.6; 3.6.1; 3.6.3-3.6.4 | `partially_supported` | Suit/Grand comparison and the smallest base-value multiple covering the bid drive a doubled loss. | Bid, game value, base value, and complete result. | Does not model all pickup/Hand distinctions, pre-first-trick impossibility, or rule-violation interactions. | Add pickup, Hand, matador-in-skat, announcement, and rule-interaction cases against approved interpretations. | v1.0 | Yes |
| Impossible Null declarations | ISkO and International Skat Court decision collection | 3.6.2; inquiries 1-3 | `supported` | A post-game-only immediate loss preserves the original Null declaration and calculates a separately supplied Suit/Grand replacement from its base value, matadors, inherited Hand status, and final bid. | Final bid, original Null Hand/ouvert flags, and optional external replacement selection with contract-specific matadors. | The engine records the supplied favorable selection but does not optimize across alternatives or infer every alternative's matadors. | Retain all Null variants, replacement bases/bounds, rounding, Hand/ouvert, immediate-loss, incomplete-metadata, schema, CLI, example, and generated-output tests. | v1.0 | Yes |
| Normal game completion | ISkO | 3.2.6; 4.1.1; 4.3.1-4.3.2; 4.4.1 | `partially_supported` | Suit/Grand can complete from 120 assigned points; Null can complete from ten reliable trick owners. | Complete points or ten completed tricks, depending on contract. | Suit/Grand can be accepted without a complete ten-trick record; the full deal and play sequence are not represented. | Require coherent ten-trick complete-history evidence for historical completion and test all contract outcomes. | v1.0 | Yes |
| Claims | ISkO | 4.4.4-4.4.6 | `partially_supported` | `declarer_claimed_remaining_tricks` assigns all remaining card points to declarer. | End reason and known points. | This is a simplified scoring assertion, not ISkO exposure, defender consent, continued-play, exact-trick, or open-play adjudication. | Test the approved structured claim model; solver-backed claim verification remains a product decision. | v1.0 plus product decision | Basic compliant representation: Yes; solver verification: Decision required |
| Concessions | ISkO | 4.4.1-4.4.3 | `partially_supported` | Declarer and defender concession reasons assign remaining points to the other party. | End reason and known points. | Card-count timing, required consent, bid/matador minimum, joint defender responsibility, and dispute evidence are not modeled. | Add timing, consent, valuation, and invalid-concession tests for the approved v1 representation. | v1.0 | Yes |
| Final settlement | ISkO | 2.5.1-2.5.11; 3.6.1-3.6.4 | `partially_supported` | `final_settlement.py` covers wins, doubled losses, achieved/announced levels, Null variants, supported Suit/Grand overbids, and bounded impossible Null settlement. | Complete result, valid declaration, game value, bid, and reliable trick ownership where required; impossible Null instead needs its replacement selection. | Source and output explicitly call general logic simplified; claims, concessions, and other rule violations leave compliance gaps. | Build a normative contract/level/outcome table and settlement regression suite for every supported variant. | v1.0 | Yes |

## SkWO list and competition matrix

The public identifier `isko_list` is retained for compatibility. The formula it
selects is governed by SkWO 6.3.1, so documentation calls it SkWO-style
performance scoring.

| Requirement | Source | Rule section | Current status | Current implementation | Required input or information | Known limitation | Required validation or tests | Target milestone | Required before v1.0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed three-player list performance | SkWO | 6.1.1-6.1.5; 6.3.1 | `partially_supported` | Implements game points plus 50 per own win, minus 50 per own loss, and 40 per other declarer loss from totals, contributions, local results, or explicit standings games. | One player's totals/contributions or three identified players and declarer results. | Most modes trust normalized results; full list procedure and aggregation from complete historical records are not represented. | Verify every supported input mode against SkWO 6.3.1, reconcile explicit game contributions, and keep unsupported procedures explicit. | v1.0 | Yes |
| Standings | SkWO | 6.3.1 | `partially_supported` | Produces exactly three standings rows ordered by total performance points, own wins, own losses, then an optional externally executed lot; unresolved ties use shared ranks and explicit `lot_required` status. | Three player identities and supplied game outcomes/scores; optional exact tied-player `lot_order`. | Input order is presentation-only, and the engine does not execute the lot; complete historical aggregation and official reporting remain unsupported. | Retain ordering, shared-rank, exact lot-group validation, schema, CLI, and generated-output tests. | v1.0 | Yes |
| Series aggregation | SkWO | 4.2(c); 5.4; 6.1.3-6.1.4; 6.2.4 | `partially_supported` | Already aggregated values may be labeled list or series totals. | Pre-aggregated totals. | No series identity, list membership, multi-list rollup, seating, corrections, or series-level standings. | Define product scope before adding entities, validation, aggregation, and tests. | Product decision | Decision required |
| Tournament aggregation | SkWO | 1.1-1.6; 2.3-2.4; 3.1-3.4; 4.1-4.5; 5.1-5.5 | `not_supported` | No tournament model exists. | Event plan, participants, series, tables, officials, results, and accounting data. | Governance and procedural requirements are broader than score aggregation. | Product decision followed by event-plan, seating, adjudication, aggregation, and retention tests if approved. | Product decision | Decision required |
| Official reporting | SkWO | 4.5; 6.2.1-6.2.7; 6.4.1-6.4.3 | `not_supported` | General JSON and CLI reports exist, but no official list or federation report format. | List entries, running totals, signatures/approvals, corrections, submission, and retention metadata. | SkWO prescribes duties but no official digital interchange or layout in this PDF. | Define the target authority and format before schema and conformance tests. | Product decision | Decision required |

## skat-ai product matrix

| Requirement | Source | Rule section | Current status | Current implementation | Required input or information | Known limitation | Required validation or tests | Target milestone | Required before v1.0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Live information boundaries | skat-ai product | Not applicable | `partially_supported` | `information_policy.py` rejects ended games and post-game skat in live mode and the analysis view redacts declarer-private skat from defenders. | Explicit mode, visibility, end reason, perspective, and verifiable public history. | The engine trusts supplied context and has no provenance model proving every fact was available at decision time. | Field-provenance allowlist, rejection/redaction tests for every live input path, and no post-game leakage in output. | v1.0 | Yes |
| Retrospective information | skat-ai product | Not applicable | `partially_supported` | Post-game mode permits known skat, ended states, and less complete legacy winner metadata. | Post-game mode and supplied retrospective facts. | It represents a position, not a complete event timeline with fact provenance. | Test complete-history retrospective facts separately from live facts and legacy partial positions. | v1.0 | Yes |
| Immediate simulation | skat-ai product | Not applicable | `supported` | Monte Carlo analysis samples unseen cards and evaluates the current trick with legal opponent responses and deterministic seeds. | Valid position, hand sizes, sample count, seed, and policy settings. | It estimates immediate trick outcomes, not complete-contract expected value or perfect-information play. | Retain legality, reproducibility, perspective, point, Null-objective, and side-ownership tests. | v1.0 | Yes |
| Multi-step simulation | skat-ai product | Not applicable | `partially_supported` | Sequential local actions and selected opponent-turn preparations are serialized and tested. | Valid position, step count, hand sizes, seed, and policies. | Some valid phases stop as `unsupported_turn_phase`; opponent hands are resampled between steps rather than maintaining one fully assigned hidden world. | Test every canonical phase, stable hidden-card ownership, no reuse, deterministic stops, and state/point continuity. | v1.0 | Yes |
| Card recommendations | skat-ai product | Not applicable | `supported` | Legal candidates are ranked by immediate expected point swing for Suit/Grand and immediate contract-objective utility for Null. | A current local decision and simulation settings. | Recommendations are bounded immediate heuristics, not proof of optimal complete-game play. | Retain legal-candidate, perspective, deterministic-seed, tie, and objective-specific ranking tests. | v1.0 | Yes |
| Opponent policies | skat-ai product | Not applicable | `supported` | Global, left/right, preset, CLI, lead, response, and defender heuristics affect immediate and multi-step paths. | Policy settings and concrete side/perspective where needed. | Policies are simplified rule-based behavior, with incomplete tactical defender and Null models. | Retain precedence and controlled-effect tests; document each supported heuristic. | v1.0 | Yes |
| Player and opponent profiles | skat-ai product | Not applicable | `partially_supported` | Supplied profile fields can select bounded side-specific rule-based presets. | Supplied profile statistics and opt-in profile preset setting. | Profiles are not derived from historical games; several fields are informational only. | Test validation, side isolation, precedence, neutral behavior, and every actionable field. | v1.0 | Yes |
| Profile confidence | skat-ai product | Not applicable | `partially_supported` | Confidence is derived only from `games_played` and gates preset activation/conflict resolution. | `games_played` plus profile signals. | Fixed heuristic bands are not calibrated uncertainty and do not affect deeper tactical decisions. | Test boundaries, missing data, conflicts, and documented effect limits; approve the v1 confidence contract. | v1.0 | Yes |
| Post-game decision review | skat-ai product | Not applicable | `supported` | One supplied actual local card is validated and compared with the recommendation, including ranks, gaps, factors, and explanations. | A retrospective decision position, actual card, and enough simulation context. | It reviews one decision only and inherits immediate-simulation limitations. | Retain Suit, Grand, Null, declarer, defender, unavailable, and legality tests. | v1.0 | Yes |
| Complete-game retrospective analysis | skat-ai product | Not applicable | `not_supported` | No workflow iterates and reviews every eligible decision in a complete game. | Complete historical record plus analysis settings and information snapshot at each decision. | Current post-game review accepts only one reconstructed position. | Add end-to-end replay analysis that rebuilds each decision without future leakage and verifies final result/settlement. | v1.0 | Yes |
| Historical-game representation | skat-ai product | Not applicable | `partially_supported` | Completed tricks can store cards, players, winner, and sequence; selected complete results can be derived. | Position metadata and completed tricks. | Missing initial deal, bidding events, skat pickup/discards, declaration event, all plays as events, claims/disputes, and per-decision information snapshots. | Add schema/runtime round-trip and semantic tests for complete games and all supported end reasons. | v1.0 | Yes |
| Training-data representation | skat-ai product | Not applicable | `not_supported` | No dataset record, provenance, label, split, or evaluation schema exists. | Complete historical games, stable identities, provenance, intended labels/targets, and split metadata. | Storing training/evaluation data is distinct from deriving statistics or training a model. | Add schema, validation, deterministic conversion, leakage, duplicate, and train/evaluation separation tests. | v1.0 | Yes |
| Historical player statistics | skat-ai product | Not applicable | `not_supported` | Statistics can be supplied manually but are not derived from historical records. | Linked historical games and stable player identities. | Required statistics, windows, privacy, and update semantics are undecided. | Product decision before aggregation and provenance tests. | Product decision | Decision required |
| Learned opponent models | skat-ai product | Not applicable | `not_supported` | No learned model exists; current profiles and policies are rule-based. | Approved historical features, model artifact, versioning, and inference contract. | Training, evaluation, deployment, fallback, and explainability requirements are undecided. | Product decision and model-specific validation plan. | Product decision | Decision required |
| Machine-learning model training | skat-ai product | Not applicable | `not_supported` | No training pipeline exists. | Approved dataset, target, evaluation protocol, reproducibility, and artifact policy. | Historical training-data representation does not itself authorize model training. | Product decision and separate training/evaluation acceptance criteria. | Product decision | Decision required |
| Generated-output validation | skat-ai product | Not applicable | `supported` | `validate_generated_outputs_schema.py` generates, semantically checks, and schema-validates 23 deterministic CLI scenarios. | Repository examples/fixtures, schemas, and deterministic CLI settings. | The matrix is representative rather than exhaustive. | Keep the count and scenario list explicit; add a deterministic scenario for each new stable user-facing branch. | v1.0 | Yes |
| Release and regression checks | skat-ai product | Not applicable | `supported` | `scripts/check.ps1` and GitHub Actions run Ruff, input schema validation, generated-output validation, and pytest on Python 3.13. | Development dependencies and supported platform tooling. | Passing checks proves tested behavior, not complete ISkO/SkWO compliance. | Require clean local and CI checks, synchronized docs/schemas, and human-controlled release actions. | v1.0 | Yes |

## Interpretations and unresolved rule questions

* For ISkO 3.6.2, the International Skat Court decision collection section
  3.6.2, inquiries 1-3, permits the declarer to select an eligible favorable Suit
  or Grand replacement. `skat-ai` records an external selection and does not
  optimize across alternatives whose contract-specific matadors are unknown.
* ISkO 4.4.4-4.4.6 defines specific open-card shortcuts. It does not define a
  general solver-backed claim protocol. Claim representation required for v1.0
  and solver-backed verification are separate requirements.
* Ten cards per player and three cards per trick imply ten normal tricks, while
  ISkO 4.4.1 says games are generally played to the end. The numbered rules do
  not provide one standalone `normal_completion` data definition; the v1.0
  complete-history contract must state its software evidence explicitly.
* SkWO 6.3.1 standings use total performance points, more own wins, fewer own
  losses, then lot. The engine represents an unresolved lot explicitly or
  records an externally executed result; it does not perform a random lot.
* SkWO defines list, event, signature, correction, submission, and retention
  duties, but the November 2022 PDF does not prescribe an official digital file
  format. Any such format needs a named external authority and conformance
  source.

See [v1.0 scope](v1_scope.md) for product classifications and completion gates.
