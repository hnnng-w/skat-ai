# Roadmap

This document tracks completed areas, known limitations, and planned improvements for `skat-ai`.

## Completed major areas

### Core analysis

Implemented:

* Core card rules and legal-card handling
* Card-point calculation
* Trump and trick-winner logic
* JSON-based position analysis
* Monte Carlo-style card analysis
* Expected point swing calculation
* Card recommendation
* JSON output for regression-friendly analysis

### Simulation

Implemented:

* Immediate trick simulation
* Multi-step simulation
* Simulation context tracking
* Strict simulation context checks
* Policy comparison across card-selection strategies
* Result serialization for multi-step and policy-comparison output

### Game history and scoring

Implemented:

* Completed-trick structure validation
* Completed-trick sequence validation
* Completed-trick rule-winner validation
* Explicit and completed-trick point summaries
* Game result summaries
* Schneider/Schwarz status summaries

### Game declaration and settlement

Implemented:

* Game declaration metadata
* Game value summaries for suit, grand, and null games
* Automatic matador inference from known declarer cards where possible
* Final single-game settlement summary
* Supported Suit/Grand overbid detection
* Supported Suit/Grand overbid settlement loss handling

### Game-end handling

Implemented:

* Normal completion
* Declarer claims remaining tricks
* Declarer concedes remaining tricks
* Defenders concede remaining tricks
* Remaining-point assignment for claim/concession scenarios
* Adjusted game-result summaries

### Performance rating

Implemented:

* Partial fixed-three-player ISkO-style single-game rating
* Declarer rating score
* Declarer rating points
* Counterparty/defender rating points
* Explicit separation between settlement score and rating score

### Metadata and information control

Implemented:

* Strategic metadata
* Player profiles
* Profile-based policy recommendations
* Profile confidence derived from `games_played`
* Live-vs-post-game information enforcement
* `information_policy_summary` output
* Rejection of post-game-only information in `live_decision`
* Requirement that ended game reasons use `post_game_review`

### Opponent modeling

Implemented:

* Opponent policy presets
* Optional profile-based policy presets
* Profile-confidence conflict resolution for cautious/aggressive preset evidence
* Separate left/right opponent policy settings
* Left/right profile-derived presets applied to effective left/right multi-step policies
* Left/right opponent policy input fields
* Left/right opponent policy CLI overrides
* Left/right opponent policy output settings
* Left/right policy handling in multi-step opponent lead and response paths
* Basic defender cooperation improvements and issue #22's current heuristic defender-partnership scope:

  * safer defender lead
  * avoiding overtaking a winning partner when a partner-safe legal card exists
  * safe smear while preserving the partner's winning position
  * forced partner overtake using the lowest-point legal winning card
  * equal-point forced-overtake tie-break using weakest sufficient trick strength
  * winning-card selection using the lowest-point legal winner
  * equal-point winning-card tie-break using weakest sufficient trick strength
  * equal-point safe-smear tie-break using weakest trick strength
  * narrow second-hand trump conservation on zero-point non-trump leads when only trump wins and a losing discard exists
  * safer discard when the declarer is winning and the defender cannot win

### Post-game review

Implemented:

* Optional `actual_card_played` input
* Validation that the actual card is valid and legal in the analyzed position
* `post_game_review_summary` output
* Comparison between actual card and recommended card
* Expected point swing difference between actual and recommended card
* Decision quality classification:

  * `not_available`
  * `optimal`
  * `acceptable`
  * `suboptimal`
  * `mistake`
* Machine-readable decision factors
* Human-readable decision explanation
* Recommendation gap details:

  * `actual_card_rank`
  * `recommended_card_rank`
  * `candidate_count`
  * `better_card_count`
* Human-readable CLI output for post-game review summaries

### Validation and documentation

Implemented:

* Input JSON schema
* Output JSON schema
* Input example schema validation
* Generated-output schema validation
* Full check script with Ruff, input schema validation, generated-output validation, and pytest
* Topic-specific documentation split into `docs/`
* Project handoff documentation

## Current known limitations

### Gameplay and rules

* The engine is not a full perfect-information solver.
* The engine is not a complete official tournament system.
* The engine focuses on analysis and simulation, not on training a machine-learning model.
* Full official settlement nuance coverage is not complete.
* Claim and concession handling assigns remaining card points according to `game_end_reason`; it does not simulate the actual remaining tricks.
* The engine does not yet verify whether a claim was strategically or legally justified.
* The engine does not yet model player agreement or disputes around claim/concession.
* Null-game overbid detection is supported, but settlement scoring remains conservative when no `required_game_value` is available.
* Matador inference uses currently known declarer cards from hand and skat context; it does not yet reconstruct all possible matador information from complete historical trick ownership in every scenario.

### Performance rating

* Performance rating is partially implemented for fixed three-player single-game declarer rating.
* `rating_score` currently equals `declarer_rating_score`.
* Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
* Full list, series, and tournament aggregation is not implemented yet.
* Four-player table performance rating is not modeled because the project assumes a fixed three-player table.

### Opponent modeling

* Opponent behavior is still simplified and rule-based.
* Defender cooperation has improved, but it is still heuristic and not a full tactical model.
* Defender cooperation assumes the fixed three-player table.
* Defender partnership inference is strongest in the currently supported second-hand path.
* There is no complete rear-hand partnership model.
* There is no dedicated null-game defender-partnership strategy.
* There is no stable declarer/partner identity when the local player itself is only known generically as `defender`.
* Defender cooperation does not use perfect-information solving, search, machine learning, or hidden-card inference.
* Player profiles influence recommendations and policy presets, but the model does not learn from historical player data.
* Profile-based presets use rough heuristics and are not learned from data.
* PlayerProfile confidence is currently used for profile-derived preset selection and conflict resolution, not deeper tactical simulation decisions.

### Information modeling

* The project enforces the main live-vs-post-game information boundaries.
* The engine still depends on the correctness of the provided position context.
* Some older or intentionally minimal completed-trick inputs may not contain enough metadata for full verification.
* Live decision examples should not contain post-game-only information.

## Recommended next milestone

### Milestone 21: Documentation and issue follow-up

Recommended scope:

* Update README feature summary.
* Update input and output JSON documentation.
* Update examples documentation for post-game review and matador inference.
* Update architecture documentation for new modules.
* Review open GitHub issues and close or update completed ones.
* Create new focused issues only for still-relevant future work.

## Open gameplay improvements

Potential future gameplay improvements:

* Add richer post-game review examples.
* Add more realistic profile-preset example variants.
* Add dedicated examples for separate left/right opponent policies.
* Explore deeper PlayerProfile confidence usage beyond preset selection.
* Explore broader defender strategy beyond issue #22's implemented heuristic scope.
* Add stronger tests for left/right opponent policy effects with controlled opponent hands.
* Improve matador inference from historical completed-trick context where safe and verifiable.
* Add richer explanation details for why a recommended card is preferred.

## Open performance-rating improvements

Potential future rating improvements:

* Aggregate multiple games into a full list result.
* Track scores per real player across a list.
* Separate declarer and counterparty perspectives explicitly for multi-game output.
* Add series/tournament aggregation.
* Add official list-report output formats if needed.

## Open technical cleanup

Recommended cleanup areas:

* Add clearer release notes or a changelog once the project stabilizes.
* Keep README short and topic-focused.
* Keep topic-specific docs in `docs/` aligned with implemented behavior.
* Continue improving JSON schema coverage where useful without duplicating too much Python validation logic.
* Centralize any remaining duplicated CLI/configuration constants.
* Review profile-preset behavior across immediate analysis and multi-step simulation.

## Related GitHub issues

Completed issues should be closed when their implementation is covered by tests and documentation.

Recommended current issue handling:

* Close or update issues for game score calculation, claim/concession handling, live-vs-post-game enforcement, JSON schema documentation, defender cooperation logic including issue #22, full Skat game value scoring, and post-game review decision quality if their implemented scope is covered.
* Keep full list/series/tournament rating work open as a future performance-rating issue.
* Close current PlayerProfile-confidence preset-selection work when tests and documentation are complete; keep deeper tactical opponent modeling as separate future work.
* Keep richer post-game review examples open as an examples/documentation task.
* Keep more realistic example positions open as an examples/testing task.
* Consider opening a focused issue for extended matador inference from completed-trick history if needed.
