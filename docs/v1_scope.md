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
| Complete historical game | One coherent record of the deal, players/seats, bidding and declaration facts, skat handling, ordered play events, end reason, result, and settlement. | A position plus selected completed tricks is not a complete historical game. |
| Historical game used as training or evaluation data | A complete historical game wrapped in a validated record with provenance, stable identity, intended labels/targets, and explicit dataset partition metadata. | Representation and evaluation use do not imply that a machine-learning model is trained. |
| Externally captured opponent statistics | A versioned record of supplied total games and percentage-point statistics with stable player identity, source provenance, capture time, and deterministic explainable profile derivation. | Explicit live side bindings or strict pre-game historical participant matching may apply confidence-gated actionable presets; external values do not imply exact counts, predict behavior, learn a profile, or evaluate policy effects. |
| Statistics derived from historical player data | Reproducible exact aggregates computed from selected timestamped normal-play dataset games for a stable case-sensitive player identity, with per-player source provenance and reusable export. | Bounded aggregation differs from manually supplied values and learned parameters; it does not weight or merge sources, manage multiple captures, apply a policy automatically, or evaluate policy effects. |
| Rule-based player or opponent profile | Explicit fields and deterministic rules that select or parameterize explainable behavior. | It is not learned from data, even when its input statistics were historically derived. |
| Learned opponent model | A versioned artifact whose behavior or parameters were fit from data and are used during inference. | It requires separate training, evaluation, deployment, fallback, and explainability decisions. |
| Training a machine-learning model | Running a reproducible process that fits model parameters from an approved training dataset and evaluates them on separated data. | It is distinct from storing historical games, generating labels, calculating statistics, or running rule-based simulation. |

## Established v1.0 product requirements

The following directions are required for `v1.0.0`:

* Analyze live game situations at fixed three-player tables.
* Enforce a strict live-information boundary for every input, internal analysis
  view, simulation path, recommendation, and output.
* Support retrospective single-decision review without future-information
  leakage into the reconstructed decision.
* Represent complete historical games and analyze their rules, result,
  settlement, and eligible decisions retrospectively.
* Represent complete historical games as validated training and evaluation data
  without requiring a model-training implementation.
* Use explicit player and opponent information through explainable rule-based
  profiles and policies, including a documented confidence contract.
* Support all declared Suit, Grand, and Null variants in the approved v1.0
  contract, including valid declaration dependencies, matadors, Hand,
  Schneider, Schwarz, ouvert, normal completion, and final settlement.
* Preserve the bounded impossible Null settlement interpretation from the
  International Skat Court decision collection: external favorable Suit/Grand
  selection, original Null declaration retained, and immediate doubled loss.
* Represent claims and concessions sufficiently to apply the approved ISkO
  outcome and settlement rules. General solver-backed verification is a
  separate decision.
* Preserve bounded SkWO-style fixed-three-player list performance and standings
  with correct formulas, explicit input provenance, and SkWO 6.3.1 tie handling.
* Preserve stable, schema-validated JSON inputs and outputs and deterministic
  regression workflows.

The Python baseline for v1.0 development and release is Python 3.13 or newer.

## Future-scope classification

Only the exact values in the `Classification` column are used for candidate
areas.

| Candidate area | Classification | Rationale or decision needed |
| --- | --- | --- |
| Complete-game coaching and replay | `decision required` | Complete historical representation and retrospective analysis are required, but interactive replay, coaching presentation, annotations, and user workflow are not defined. |
| Full fixed-three-player list aggregation | `decision required` | Current bounded totals, contribution, local-result, and standings modes exist, but whether complete historical records must feed a full official list workflow is not defined. |
| Series aggregation | `decision required` | Series identity, list membership, rollup, seating, correction, and standings semantics are not approved. |
| Tournament management | `decision required` | Event plans, registration, officials, tables, schedules, adjudication, accounting, and retention are not product-defined. |
| Official list and report formats | `decision required` | SkWO defines duties but not a digital format; the target authority and conformance artifact must be named. |
| Historical opponent-statistics extensions | `decision required` | Exact selected-partition aggregation with an optional strict cutoff is supported. Rolling/count-based windows, privacy and update policy, weighting, merging, multiple captures, capture persistence/selection, and policy-effect evaluation are not defined. |
| Learned opponent profiles | `decision required` | Model type, features, evaluation, versioning, explainability, and fallback behavior are not defined. |
| Machine-learning model training | `decision required` | Training-data representation is required, but no model objective, training protocol, or quality gate is approved. |
| Stronger search or solver functionality | `decision required` | Search depth, information assumptions, latency, determinism, and quality measurement are not defined. |
| Broader hidden-card inference | `decision required` | Allowed evidence, probabilistic output, live-information safety, and confidence semantics are not defined. |
| Claim and concession verification | `decision required` | v1.0 representation and settlement are required; general proof, solver use, disagreement, and adjudication scope are not defined. |
| Full bidding and auction modeling | `decision required` | A valid final declaration is required, but auction events, passed-in games, illegal bids, and declarer derivation are not yet a product requirement. |

## Unconditional exclusion

Four-player table support is the project's only unconditional out-of-scope
area. No other candidate area is permanently out of scope.

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
| Complete-game retrospective analysis | A complete historical record can be replayed in order, each eligible decision is reconstructed using only information available then, rule/result/settlement summaries are produced, and end-to-end tests detect future-information leakage and event-order corruption. |
| Complete-game historical representation | A versioned schema and runtime model represent stable game/player IDs, fixed seats, initial deal, bidding/declaration facts, skat pickup/discards or Hand state, every play, claims/concessions, final result, and settlement; valid records round-trip and inconsistent ownership, order, legality, totals, or outcomes are rejected. |
| Training-data representation | A versioned schema links a complete historical game to provenance, labels/targets, feature-generation version, and explicit training/evaluation partition; conversion is deterministic and tests reject duplicates, missing provenance, invalid labels, and partition leakage. |
| Input validation | JSON Schema and runtime validation agree on public types, bounds, enums, and cross-field requirements for every stable input branch; parity tests cover malformed and contradictory records. |
| Structured output stability | Every stable output branch has a documented versioned schema, deterministic serialization, explicit unavailable/incomplete states, and compatibility tests; intentional breaking changes are recorded before release. |
| Simulation behavior | Seeded immediate and multi-step simulations are reproducible, play only legal cards, preserve one coherent hidden-card ownership assignment across a simulated path, never reuse cards, maintain point/trick ownership exactly once, and terminate every canonical phase with a documented reason. |
| Recommendation behavior | Recommendations always select from legal candidates, use the documented Suit/Grand or Null objective, preserve player-side perspective, expose enough evidence to reproduce ranking, and have deterministic tie behavior under fixed settings. |
| Opponent modeling | Every supported global and left/right rule-based policy has documented semantics, precedence, and controlled tests proving its effect in each analysis path where it is claimed to apply; no policy is described as learned. |
| Profile confidence | The accepted profile fields, confidence derivation, activation boundaries, conflict rules, and exact behavioral influence are documented and tested at every boundary, including missing, neutral, conflicting, and side-specific profiles. |
| List and standings functionality | Every documented totals, contribution, local-result, and explicit three-player standings input mode produces SkWO 6.3.1 performance totals from validated inputs; standings use more own wins, fewer own losses, then an explicit unresolved or executed lot; tests reconcile every supplied game contribution and tie case. |
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
Training-data representation remains partial because later historical end
reasons and player-disjoint partition policy are not supported. The v1 gate also
remains open for exposed-card-aware recommendation analysis, approved later end
reasons, and complete auction representation.

Bounded historical player-statistics aggregation is supported from the same
dataset container, but it does not make partitions player-disjoint and is not a
training, quality-evaluation, or automatic policy-application gate.
Rolling known-opponent policy imitation is also supported with disjoint
partitions and strict as-of profiles. Its preferred-card match delta is not a
strategic recommendation-quality, optimality, significance, or unseen-player
generalization claim and does not close those broader gates.

## Release decision rule

`v1.0.0` is not ready while any required gate lacks evidence, any validation or
test listed for a v1.0-required traceability row remains incomplete, any such
row remains less than `supported` without an approved bounded interpretation,
or any unresolved rule ambiguity affects a required settlement.
Topics classified `decision required` do not block v1.0 unless their decision is
needed to satisfy a required gate. The decision and resulting scope must be
recorded before implementation begins.
