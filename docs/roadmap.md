# Roadmap

This document tracks completed areas, known limitations, and planned improvements.

## Completed major areas

The following areas are implemented or partially implemented:

- Core card rules and legal-card handling
- Monte Carlo card analysis
- Multi-step simulation
- Opponent policy presets
- Profile-based policy recommendations
- Game declaration metadata
- Game value calculation for suit, grand, and null games
- Card-point score summaries
- Game result summaries
- Completed-trick structure and sequence validation
- Completed-trick rule-winner validation
- Game-end handling for normal completion, claim, and concession
- Remaining-point assignment for claim/concession scenarios
- Final single-game settlement summary
- Supported Suit/Grand overbid detection and settlement
- Partial fixed-three-player ISkO-style single-game rating
- Example regression tests
- Topic-specific documentation split into `docs/`

## Current known limitations

### Gameplay and rules

- The engine is not a full perfect-information or full-game solver.
- The engine focuses on analysis and simulation, not on training a machine-learning model.
- Game value calculation uses declared metadata and does not yet infer matadors automatically.
- Full official settlement nuances are not completely modeled yet.
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
- Player profiles influence recommendations and policy presets, but the model does not learn from historical player data.
- Profile-based presets use rough heuristics and are not learned from data.
- The same combined opponent preset may still be used in places where separate left/right opponent behavior would be more realistic.
- Defender cooperation logic is still simplified.

### Information modeling

- Skat visibility and analysis mode are tracked as metadata, but stricter live-vs-post-game enforcement should still be improved.
- The engine depends on the correctness of the provided position context.
- Older completed-trick inputs without `players` or `winner_player` are supported but cannot be fully validated.

## Open technical cleanup

Recommended cleanup areas:

- Keep README short and topic-focused.
- Continue improving topic-specific docs in `docs/`.
- Add or generate JSON schema documentation for input and output.
- Centralize completed-trick validation responsibilities more clearly.
- Review profile-preset behavior across immediate analysis and multi-step simulation.
- Add clearer release notes or changelog once the project stabilizes.

## Open gameplay improvements

Potential future gameplay improvements:

- Infer matadors automatically from known declaration/card context where possible.
- Improve defender cooperation logic.
- Support separate left/right opponent policies consistently across simulation paths.
- Improve live-vs-post-game information enforcement.
- Add more realistic post-game review examples.
- Add more realistic profile-preset example variants.
- Improve opponent modeling with player-profile confidence.

## Open performance-rating improvements

Potential future rating improvements:

- Aggregate multiple games into a full list result.
- Track scores per real player across a list.
- Separate declarer and counterparty perspectives explicitly for multi-game output.
- Add series/tournament aggregation.
- Add official list-report output formats if needed.

## Related GitHub issues

Some historical GitHub issues may now be completed or partially completed.

Suggested issue cleanup:

- Close completed claim/concession handling issues.
- Close completed completed-trick sequence-validation issues.
- Update performance-rating issues to reflect the current partial ISkO implementation.
- Update game-value issues to focus on missing automatic matador inference, if still desired.
- Keep JSON schema documentation issues open until schema docs are complete.