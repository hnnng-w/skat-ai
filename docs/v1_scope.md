# v1.0 scope

This document defines the product requirements and observable completion gates
for `skat-ai` `v1.0.0`. Current implementation status remains in
[Requirements traceability](requirements_traceability.md).

The November 2022 ISkO and SkWO publication is the normative source for official
rules and competition behavior. Product capabilities such as simulation,
recommendations, historical data, and opponent modeling are specified here and
must not be presented as official-rule requirements.

## Product concepts

| Concept | Definition for skat-ai | Explicit boundary |
| --- | --- | --- |
| Live position | A position analyzed using only facts legitimately available to the selected player at that decision time. | Post-game skat, future plays, later outcomes, and retrospective labels must be rejected or redacted. |
| Retrospective single-decision review | One historical decision reconstructed with the actual card and facts available at that point, then compared with the engine recommendation. | It is not a complete-game replay. Retrospective facts may explain the result but must not leak into the reconstructed decision analysis. |
| Complete historical game review | All eligible decisions from one complete historical game, independently reconstructed from decision-time snapshots and compared with the existing immediate recommendation. | It is not a perfect-information solver, complete-contract optimization, player rating, or training/evaluation record. |
| Complete historical game | One coherent record of the deal, players/seats, final bid and declaration facts, skat handling, ordered play events, end reason, result, and settlement. | A position plus selected completed tricks is not a complete historical game; a full auction sequence is planned after v1.0. |
| Historical game used as training or evaluation data | A complete historical game wrapped in a validated record with provenance, stable identity, intended labels/targets, and explicit dataset partition metadata. | Representation and evaluation use do not imply that a machine-learning model is trained. |
| Externally captured opponent statistics | A versioned record of supplied total games and percentage-point statistics with stable player identity, source provenance, capture time, and deterministic explainable profile derivation. | Explicit live side bindings or strict pre-game historical participant matching may apply confidence-gated actionable presets; external values do not imply exact counts, predict behavior, or learn a profile. |
| Statistics derived from historical player data | Reproducible exact aggregates computed from selected timestamped normal-play dataset games for a stable case-sensitive player identity, with per-player source provenance and reusable export. | Bounded aggregation differs from manually supplied values and learned parameters; it does not weight or merge sources, manage multiple captures, or apply a policy automatically. |
| Rule-based player or opponent profile | Explicit fields and deterministic rules that select or parameterize explainable behavior. | It is not learned from data, even when its input statistics were historically derived. |
| Rolling opponent-policy evaluation | A strict game-start as-of comparison of an acting player's observed cards with an actionable deterministic profile policy and the fixed `simple_lowest` baseline. | Preferred-card and exact-card matches measure behavioral imitation only, not strategic strength, optimality, recommendation quality, statistical significance, or unseen-player generalization. |
| Dataset partition policy | Optional declared `known_opponent` or `unseen_player` intent plus exact stable-player membership and overlap auditing. | Known-opponent evaluation intentionally permits player overlap; declared unseen-player datasets require player-disjoint partitions but are not automatically split or balanced. |
| Learned opponent model | A versioned artifact whose behavior or parameters were fit from data and are used during inference. | It requires separate training, evaluation, deployment, fallback, and explainability decisions. |
| Training a machine-learning model | Running a reproducible process that fits model parameters from an approved training dataset and evaluates them on separated data. | It is distinct from storing historical games, generating labels, calculating statistics, or running rule-based simulation. |

## Required before v1.0.0

The following directions are required for `v1.0.0`:

* Analyze live game situations at fixed three-player tables.
* Enforce field-level live-information provenance across inputs, analysis,
  simulation, recommendations, and output. The current broad live/post-game
  boundary is only partial support for this requirement.
* Support retrospective single-decision review and complete-game coaching
  without future-information leakage into reconstructed decisions. Bounded
  30-decision review exists, but a complete coaching workflow does not.
* Represent complete historical games with structured claims, concessions, and
  approved additional game-end reasons, then analyze rules, result, approved
  settlement, and eligible decisions retrospectively. Current complete records
  support normal completion only.
* Complete the approved normative settlement matrix, including structured claim
  and concession outcomes, while preserving the bounded impossible Null
  interpretation from the International Skat Court decision collection.
* Represent complete historical games as validated training and evaluation data
  without requiring model training.
* Preserve versioned external and exact historically aggregated opponent
  statistics, scoped exact or estimated evidence, deterministic explainable
  profiles, actionable gating, explicit live stable-ID bindings, strict time-safe
  historical application, and rolling known-opponent behavioral evaluation.
  These bounded requirements are implemented; profiles remain rule-based and
  confidence remains heuristic.
* Preserve optional known-opponent and unseen-player dataset policies, exact
  stable-player overlap audits, and strict declared unseen-player disjointness.
  This bounded requirement is implemented.
* Add stronger search or solver functionality with documented information,
  quality, determinism, and latency contracts.
* Preserve one coherent hidden-world assignment across each simulated path.
* Add broader information-safe hidden-card inference with explicit allowed
  evidence and confidence semantics.
* Use exposed cards in Ouvert-aware recommendation simulation without violating
  decision-time information boundaries.
* Aggregate complete fixed-three-player 36-game lists while preserving SkWO
  6.3.1 performance formulas and tie handling.
* Support interactive live and retrospective input and session capture.
* Provide a stable library API and installed CLI/package interface.
* Support all final declared Suit, Grand, and Null variants in the approved v1.0
  contract, including valid dependencies, matadors, Hand, Schneider, Schwarz,
  Ouvert, game end, and final settlement.
* Preserve stable, schema-validated JSON inputs and outputs and deterministic
  regression workflows.

The Python baseline for v1.0 development and release is Python 3.13 or newer.

## Planned after v1.0.0

These areas are useful planned later work, not requirements for the first major
release. Their implementation details and acceptance criteria are not yet
approved:

* Full bidding and auction sequence modeling.
* Learned opponent profiles.
* Machine-learning models for the engine's own card decisions.
* Online-platform adapters or browser integration.

## Not required

These areas are not required for the intended product:

* Formal series aggregation as a dedicated workflow. A simple comparison or
  summary across independent completed lists may be added later without a formal
  series model.
* Tournament management.
* Official federation list or report formats.

## Unconditional exclusion

Four-player table support is the project's only unconditional out-of-scope
area. No other area is unconditionally excluded.

## Completion gates

Every gate below must have automated evidence unless it explicitly names a
manual release artifact. A feature field or example without source behavior,
validation, and tests does not satisfy a gate.

| Area | Observable completion condition |
| --- | --- |
| Rules and settlement coverage | Every ISkO row marked required before v1.0 in the traceability matrix is `supported`, or has an explicitly approved bounded interpretation; a normative table-driven suite covers winning, losing, achieved/announced levels, overbid, impossible Null, claim, concession, and incomplete-evidence outcomes. |
| Supported contract variants | Input validation accepts every legal Suit, Grand, Null, Hand, and ouvert variant in the documented v1 contract; rejects every documented illegal modifier dependency; and produces tested game values and settlement for each accepted variant. |
| Live-position analysis | Every canonical three-player turn phase is either analyzed when the local player acts or advances through a documented opponent-preparation path; unsupported states fail explicitly without mutating the supplied position. |
| Live information control | A documented field-level provenance policy rejects or redacts every post-game-only or opponent-private fact in live mode across loading, matador inference, simulation, recommendation, review, and serialization; adversarial regression fixtures prove no future event or post-game skat changes a live result. |
| Post-game analysis | A legal actual card can be compared with all legal alternatives for Suit, Grand, and Null from declarer and defender perspectives; unavailable and invalid cases have stable schema-valid output and focused tests. |
| Complete-game retrospective analysis and coaching | A complete historical record can be replayed in order, each eligible decision is reconstructed using only information available then, rule/result/settlement summaries and actionable coaching explanations are produced, and end-to-end tests detect future-information leakage and event-order corruption. |
| Complete-game historical representation | A versioned schema and runtime model represent stable game/player IDs, fixed seats, initial deal, final bid/declaration facts, skat pickup/discards or Hand state, every play, structured claims/concessions and approved additional end reasons, final result, and settlement; valid records round-trip and inconsistent ownership, order, legality, totals, or outcomes are rejected. |
| Training-data representation | A versioned schema links a complete historical game to provenance, labels/targets, feature-generation version, explicit training/evaluation partition, and optional partition policy; conversion and exact-player overlap audits are deterministic, and tests reject duplicates, missing provenance, invalid labels, partition leakage, and declared unseen-player overlap. |
| Input validation | JSON Schema and runtime validation agree on public types, bounds, enums, and cross-field requirements for every stable input branch; parity tests cover malformed and contradictory records. |
| Structured output stability | Every stable output branch has a documented versioned schema, deterministic serialization, explicit unavailable/incomplete states, and compatibility tests; intentional breaking changes are recorded before release. |
| Simulation behavior | Seeded immediate and multi-step simulations are reproducible, play only legal cards, preserve one coherent hidden-card ownership assignment across a simulated path, never reuse cards, maintain point/trick ownership exactly once, and terminate every canonical phase with a documented reason. |
| Search and hidden-card inference | The approved stronger search or solver produces reproducible, explainable results under documented information assumptions and quality/latency bounds; broader hidden-card inference uses only documented decision-time evidence and exposes bounded confidence without leaking private or future facts. |
| Ouvert-aware simulation | Historical and live Ouvert analysis uses legitimately exposed cards in recommendation simulation, never treats unexposed cards as public, and has deterministic contract- and perspective-specific tests. |
| Recommendation behavior | Recommendations always select from legal candidates, use the documented Suit/Grand or Null objective, preserve player-side perspective, expose enough evidence to reproduce ranking, and have deterministic tie behavior under fixed settings. |
| Opponent modeling | Every supported global and left/right rule-based policy has documented semantics, precedence, and controlled tests proving its effect in each analysis path where it is claimed to apply; no policy is described as learned. External and historical statistics preserve stable identity and provenance, and strict time-safe historical application never uses a capture from the target game or later. |
| Profile confidence and behavioral evaluation | Accepted profile fields, exact or estimated evidence scopes, heuristic confidence, activation boundaries, conflict rules, and exact behavioral influence are documented and tested at every boundary. Rolling evaluation uses strict game-start as-of history and reports preferred/exact behavioral matching without strategic, optimality, significance, or unseen-player claims. |
| Dataset partition policies | Optional known-opponent and unseen-player intent remains backward-compatible; exact membership, pairwise/three-way overlap, directed known-opponent coverage, and strict declared unseen-player disjointness are deterministic and schema-valid. |
| List and standings functionality | Every documented totals, contribution, local-result, and explicit three-player standings input mode produces SkWO 6.3.1 performance totals from validated inputs; complete historical records aggregate into fixed-three-player 36-game lists; standings use more own wins, fewer own losses, then an explicit unresolved or executed lot; tests reconcile every supplied game contribution and tie case. |
| Interactive input and session capture | Supported live and retrospective sessions can be entered interactively, validated incrementally, resumed or completed without hidden state, and serialized to the same documented information-safe records. |
| Stable installed interface | A versioned public library API and installed CLI/package entry point have documented compatibility guarantees, installation tests, stable error behavior, and no dependence on running repository-root `main.py`. |
| Examples | Examples cover each supported contract family, live/post-game boundary, complete historical record, training/evaluation record, claim/concession, overbid including impossible Null, rule-based profile, list aggregation, and standings; every example passes schema and semantic validation. |
| Generated-output validation | The deterministic scenario matrix covers every stable top-level output branch and representative unavailable/incomplete/error boundaries; the documented scenario count equals the executable matrix count. |
| Python 3.13 | `pyproject.toml` requires Python 3.13 or newer, Ruff targets `py313`, GitHub Actions uses Python 3.13, installation succeeds on Python 3.13, and the full check passes there without a version matrix. |
| Regression testing | Ruff, input example schema validation, generated-output schema validation, and the complete pytest suite all pass locally and in GitHub Actions from a clean checkout of the release candidate. |
| Documentation | README, architecture, input/output, scoring, game-end, overbid, performance, examples, schema validation, roadmap, handoff, traceability, and scope documentation agree with behavior, rule ownership, stable fields, limitations, Python baseline, and release baseline. |
| Release hygiene | The human-reviewed release candidate has only intended changes; package metadata and changelog use the approved v1.0.0 version; `git diff --check` and the full check pass; the tag and GitHub Release are created by a human only after those facts are verified. |

The normal-play historical-game workflow satisfies the deal-through-settlement
portion of complete-game representation for `normal_completion` and can
reconstruct information-safe pre-play states for all 30 actual cards. It also
evaluates non-ouvert normal-play snapshots through bounded review and wraps all
normal-play snapshots in versioned provenance-aware training/evaluation records.
Training-data representation remains partial because approved later historical
end reasons are not supported. Optional partition intent, exact overlap audits,
and strict declared unseen-player disjointness are implemented; automatic
splitting and unseen-player model evaluation are not v1 requirements. The v1
gate remains open for exposed-card-aware recommendation analysis and approved
later end reasons. Full auction representation is planned after v1.0.

Bounded historical player-statistics aggregation is supported from the same
dataset container under either compliant policy, but it does not infer or change policy and is not a
training, quality-evaluation, or automatic policy-application gate.
Rolling known-opponent policy imitation is also supported with disjoint
partition names, intentional stable-player overlap, and strict as-of profiles. Its preferred-card match delta is not a
strategic recommendation-quality, optimality, significance, or unseen-player
generalization claim and does not close those broader gates.

## Release decision rule

`v1.0.0` is not ready while any required gate lacks evidence, any validation or
test listed for a v1.0-required traceability row remains incomplete, any such
row remains less than `supported` without an approved bounded interpretation,
or any unresolved rule ambiguity affects a required settlement.
Post-v1.0 and not-required areas do not block the first major release. Remaining
implementation details for required areas must be approved and recorded before
their implementation begins.
