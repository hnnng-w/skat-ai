# Project handoff

This document summarizes the current state of `skat-ai` for continuing development in a new thread or with a new contributor.

## Project overview

`skat-ai` is a local Python-based Skat analysis and simulation tool.

The project focuses on:

- legal-card detection
- rule-based Skat position analysis
- Monte Carlo-style card analysis
- expected point swing estimation
- card recommendations
- multi-step simulation
- opponent policy modeling
- game result and settlement summaries
- post-game review support
- JSON input/output for regression-friendly testing

The project is not a machine-learning model, not a full official tournament system, and not a perfect-information Skat solver.

## Current development style

Development is milestone-based and test-driven.

Each milestone is split into small parts. Each part should:

- add one focused behavior or cleanup
- include tests
- keep existing behavior backward-compatible where possible
- run the full check script before committing

The standard check command is:

```powershell
.\scripts\check.ps1
```

The project check currently covers:

- Ruff checks
- input JSON schema validation
- generated output JSON schema validation
- pytest regression tests

## Important assumptions

### Table size

The project assumes a fixed three-player Skat table.

Four-player table support is not a priority unless explicitly requested.

### Performance rating

ISkO-style performance rating is partially implemented for fixed three-player single-game declarer perspective.

Full list, series, and tournament aggregation is not implemented yet.

### Live vs post-game mode

The project separates live decision analysis from post-game review.

`live_decision` is intended for in-game decisions and must not use post-game-only information.

`post_game_review` is intended for completed or retrospectively analyzed games.

## Major completed milestones

### Core rules and simulation

Implemented:

- card notation
- card points
- trump logic
- legal-card detection
- trick winner logic
- immediate trick simulation
- expected point swing calculation
- card recommendation

### Multi-step simulation

Implemented:

- sequential player-action simulation
- configurable card-selection policy
- strict simulation context checks
- policy comparison
- result serialization

### Game history and scoring

Implemented:

- completed-trick structure validation
- completed-trick sequence validation
- completed-trick winner validation
- explicit and completed-trick point summaries
- game result summaries
- Schneider/Schwarz status summaries

### Game declaration and settlement

Implemented:

- game declaration metadata
- game value summaries for suit, grand, and null games
- final single-game settlement summary
- supported Suit/Grand overbid detection
- supported Suit/Grand overbid settlement loss handling

Known remaining areas:

- automatic matador inference is not implemented yet
- full official settlement nuance coverage is not complete

### Game-end handling

Implemented:

- normal completion
- declarer claims remaining tricks
- declarer concedes remaining tricks
- defenders concede remaining tricks
- remaining-point assignment
- adjusted game-result summaries

### Performance rating

Implemented:

- `performance_rating_system`
- partial `isko_list` support
- fixed three-player table assumption
- single-game declarer rating score
- declarer rating points
- counterparty/defender rating points
- clear distinction between settlement score and rating score

Not implemented:

- full list aggregation
- series aggregation
- tournament aggregation
- full player-by-player list output

### JSON schema validation

Implemented:

- `schemas/input.schema.json`
- `schemas/output.schema.json`
- input example schema validation
- generated output schema validation
- schema validation documentation

### Live-vs-post-game information enforcement

Implemented:

- rejects `live_decision + known_post_game`
- rejects known skat cards in `live_decision`
- rejects ended game reasons in `live_decision`
- requires `post_game_review` for ended game reasons
- rejects complete 120-point game states in `live_decision`
- restricts unverifiable completed-trick winner metadata in `live_decision`
- adds `information_policy_summary` to output
- centralizes information policy in `information_policy.py`

### Left/right opponent policies

Implemented:

- global opponent policy settings remain backward-compatible
- normalized `left_opponent_policy_settings`
- normalized `right_opponent_policy_settings`
- left/right policy input fields
- left/right policy validation
- left/right CLI overrides
- centralized CLI policy choices via `VALID_OPPONENT_CARD_POLICIES`
- left/right settings in output
- left/right settings in multi-step serialization
- left/right settings threaded into multi-step simulation
- opponent lead uses the specific left/right lead policy
- right response uses `right_opponent_policy_settings` when left leads

Known remaining areas:

- further defender-cooperation strategy can still be improved
- profile confidence is not yet used deeply in simulation decisions

## Current important modules

### Entry point

- `main.py`
  - CLI entry point
  - analysis orchestration
  - output construction
  - multi-step execution
  - policy comparison

### Input and validation

- `input_loader.py`
  - JSON loading
  - game state construction
  - settings extraction
  - left/right opponent policy normalization

- `input_validation.py`
  - raw input validation
  - card validation
  - completed-trick validation hooks
  - optional policy validation

- `information_policy.py`
  - live-vs-post-game information policy rules
  - information policy output summary

### Game state and rules

- `game_state.py`
- `rules.py`
- `deck.py`
- `known_cards.py`
- `game_history.py`

### Game result and settlement

- `game_declaration.py`
- `game_value.py`
- `game_result.py`
- `game_end.py`
- `overbid.py`
- `final_settlement.py`
- `performance_rating.py`

### Simulation

- `simulation.py`
- `simulation_step.py`
- `multi_step_simulation.py`
- `multi_step_summary.py`
- `simulation_context.py`
- `state_transition.py`

### Opponent modeling

- `opponent_policy.py`
- `opponent_lead.py`
- `opponent_sequence.py`
- `opponent_policy_preset.py`
- `opponent_profile_policy.py`
- `player_profile.py`

### Output

- `output_writer.py`
- `result_serialization.py`

## Current documentation structure

Main documentation files:

- `README.md`
- `docs/architecture.md`
- `docs/input_json.md`
- `docs/output_json.md`
- `docs/schema_validation.md`
- `docs/scoring.md`
- `docs/game_end.md`
- `docs/overbid.md`
- `docs/performance_rating.md`
- `docs/examples.md`
- `docs/roadmap.md`
- `docs/project_handoff.md`

## Recommended next development milestone

The next useful development milestone is:

**Milestone 14: Post-game review decision quality**

Potential scope:

- add `actual_card_played` to post-game inputs
- compare actual card with recommended card
- calculate expected-value difference
- classify decision quality
- add `post_game_review_summary` to output
- add examples and tests

## Open future topics

Recommended future topics:

- post-game review decision quality
- full ISkO list/series aggregation
- improved defender cooperation logic
- PlayerProfile confidence in opponent modeling
- automatic matador inference where enough information is available
- richer realistic example positions

## GitHub issue cleanup recommendations

Likely completed and closable:

- Add game score calculation
- Add claim and concession handling
- Add live-vs-post-game information enforcement
- Add JSON schema documentation

Likely partially completed and should be updated:

- Add performance rating for Skat lists and series
- Add full Skat game value scoring
- Add profile-aware opponent policy
- Add realistic examples with metadata and policy presets

Likely still open:

- Improve defender cooperation logic
- Use PlayerProfile confidence in opponent modeling
- Add post-game review examples
- Add more realistic example positions

## New-thread starter instruction

When continuing in a new ChatGPT thread, provide:

1. the repository URL
2. this file
3. the current roadmap
4. the next desired milestone
5. the instruction that code and program output should remain in English while discussion can remain in German