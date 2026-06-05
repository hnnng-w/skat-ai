# Roadmap

This document tracks completed areas, known limitations, and planned improvements.

## Completed major areas

The following areas are implemented or partially implemented.

### Core analysis

- Core card rules and legal-card handling
- Card-point calculation
- Trump and trick-winner logic
- JSON-based position analysis
- Monte Carlo-style card analysis
- Expected point swing calculation
- Card recommendation
- JSON output for regression-friendly analysis

### Simulation

- Immediate trick simulation
- Multi-step simulation
- Simulation context tracking
- Strict simulation context checks
- Policy comparison across card-selection strategies
- Result serialization for multi-step and policy-comparison output

### Game history and scoring

- Completed-trick structure validation
- Completed-trick sequence validation
- Completed-trick rule-winner validation
- Explicit and completed-trick point summaries
- Game result summaries
- Schneider/Schwarz status summaries

### Game declaration and settlement

- Game declaration metadata
- Game value summaries for suit, grand, and null games
- Final single-game settlement summary
- Supported Suit/Grand overbid detection
- Supported Suit/Grand overbid settlement loss handling

### Game-end handling

- Normal completion
- Declarer claims remaining tricks
- Declarer concedes remaining tricks
- Defenders concede remaining tricks
- Remaining-point assignment for claim/concession scenarios
- Adjusted game-result summaries

### Performance rating

- Partial fixed-three-player ISkO-style single-game rating
- Declarer rating score
- Declarer rating points
- Counterparty/defender rating points
- Explicit separation between settlement score and rating score

### Metadata and information control

- Strategic metadata
- Player profiles
- Profile-based policy recommendations
- Live-vs-post-game information enforcement
- `information_policy_summary` output
- Rejection of post-game-only information in `live_decision`
- Requirement that ended game reasons use `post_game_review`

### Opponent modeling

- Opponent policy presets
- Optional profile-based policy presets
- Separate left/right opponent policy settings
- Left/right opponent policy input fields
- Left/right opponent policy CLI overrides
- Left/right opponent policy output settings
- Left/right policy handling in multi-step opponent lead and response paths

### Validation and documentation

- Input JSON schema
- Output JSON schema
- Input example schema validation
- Generated-output schema validation
- Full check script with Ruff, schema validation, generated-output validation, and pytest
- Topic-specific documentation split into `docs/`
- Project handoff documentation

## Current known limitations

### Gameplay and rules

- The engine is not a full perfect-information solver.
- The engine is not a complete official tournament system.
- The engine focuses on analysis and simulation, not on training a machine-learning model.
- Game value calculation uses declared metadata and does not yet infer matadors automatically.
- Full official settlement nuance coverage is not complete.
- Claim and concession handling assigns remaining card points according to `game_end_reason`; it does not simulate the actual remaining tricks.
- The engine does not yet verify whether a claim was strategically or legally justified.
- The engine does not yet model player agreement or disputes around claim/concession.
- Null-game overbid detection is supported, but settlement scoring remains conservative when no `required_game_value` is available.

### Performance rating

- Performance rating is partially implemented for fixed three-player single-game declarer rating.
- `rating_score` currently equals `declarer_rating_score`.
- Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
- Full list, series, and tournament aggregation is not implemented yet.
- Four-player table performance rating is not modeled because the project assumes a fixed three-player table.

### Opponent modeling

- Opponent behavior is still simplified and rule-based.
- Defender cooperation logic is still simplified.
- Player profiles influence recommendations and policy presets, but the model does not learn from historical player data.
- Profile-based presets use rough heuristics and are not learned from data.
- PlayerProfile confidence is not yet deeply used in simulation decisions.

### Information modeling

- The project now enforces the main live-vs-post-game information boundaries.
- The engine still depends on the correctness of the provided position context.
- Some older or intentionally minimal completed-trick inputs may not contain enough metadata for full verification.
- Live decision examples should not contain post-game-only information.

## Recommended next milestone

### Milestone 14: Post-game review decision quality

Recommended scope:

- Add optional `actual_card_played` input field.
- Validate that `actual_card_played` is a valid card.
- Validate that `actual_card_played` is legal in the analyzed position.
- Compare `actual_card_played` with the recommended card.
- Calculate expected-value difference between actual and recommended card.
- Add `post_game_review_summary` to output.
- Classify decision quality, for example:
  - `optimal`
  - `acceptable`
  - `suboptimal`
  - `mistake`
- Add examples and tests.

## Open gameplay improvements

Potential future gameplay improvements:

- Infer matadors automatically from known declaration/card context where possible.
- Improve defender cooperation logic.
- Add richer post-game review examples.
- Add more realistic profile-preset example variants.
- Add dedicated examples for separate left/right opponent policies.
- Improve opponent modeling with PlayerProfile confidence.
- Add stronger tests for left/right opponent policy effects with controlled opponent hands.

## Open performance-rating improvements

Potential future rating improvements:

- Aggregate multiple games into a full list result.
- Track scores per real player across a list.
- Separate declarer and counterparty perspectives explicitly for multi-game output.
- Add series/tournament aggregation.
- Add official list-report output formats if needed.

## Open technical cleanup

Recommended cleanup areas:

- Add clearer release notes or a changelog once the project stabilizes.
- Keep README short and topic-focused.
- Keep topic-specific docs in `docs/` aligned with implemented behavior.
- Continue improving JSON schema coverage where useful without duplicating too much Python validation logic.
- Centralize any remaining duplicated CLI/configuration constants.
- Review profile-preset behavior across immediate analysis and multi-step simulation.

## Related GitHub issues

Completed issues should be closed when their implementation is covered by tests and documentation.

Recommended current issue focus:

- Keep full list/series/tournament rating work open as a future performance-rating issue.
- Keep defender cooperation logic open as a future opponent-modeling issue.
- Keep PlayerProfile confidence in opponent modeling open as a future strategy issue.
- Keep post-game review examples or decision-quality work open for the next milestone.
- Keep matador inference open as a focused future scoring/rules issue.