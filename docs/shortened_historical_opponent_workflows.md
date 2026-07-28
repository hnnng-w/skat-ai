# Shortened historical opponent workflows

Historical opponent-statistics aggregation, statistics export, rolling as-of
profile construction, and rolling opponent-policy evaluation support exactly:

* `normal_completion`
* `declarer_concession`
* `defender_concession`

Other historical end reasons remain unsupported until their result, evidence,
and decision semantics receive an explicit implementation. A participating
unsupported record is rejected with its record ID, game ID, end reason, and the
supported reasons.

## Game-level statistics

Every selected historical record contributes exactly one game to each of its
three participants. Played-card, snapshot, review-decision, training-sample,
trick, observed-point, and unresolved-point counts do not weight the aggregate.
A zero-play concession is therefore full game-level evidence.

The existing `final_settlement_summary.is_loss` remains the winner authority.
For a declarer concession it records one solo game and no solo win for the
declarer, plus one defender game and one defender win for each defender. Suit,
Grand, Null, and Hand counts use the existing declaration categories. Overbid
losses remain losses.

For a typical undecided defender concession, final settlement records one solo
win for the declarer and one defender loss for each defender. If defenders had
already won, the declarer loss and both defender wins remain binding. The
conceding defender and concession form add no individual statistic.

No concession count, rate, timing feature, consent feature, classification,
signal, confidence threshold, or policy preset is added. Defender consent,
remaining cards, incomplete-trick details, and unresolved points cannot affect
statistics or profile derivation.

## Selection, provenance, and export

Aggregation preserves canonical partition selection, strict `played_at`
validation, and the exclusive cutoff:

```text
source.played_at < before
```

Ordered source record/game IDs, first and last timestamps, per-player
`captured_at`, dataset identity/version, included partitions, and optional
partition-policy provenance remain unchanged. Zero-sample records remain
eligible. Export uses the existing version-1 opponent-statistics contract and
round-trips through the existing loader; terminal-event details are not copied.

Standalone aggregation continues to support unspecified, `known_opponent`, and
compliant `unseen_player` partition intent. Rolling evaluation remains a
`known_opponent` workflow and rejects declared `unseen_player` intent.

## Rolling source games

Normal completions and both concession kinds in selected source partitions have
equal game-level weight. For each target, eligibility remains strictly:

```text
source partition selected and source.played_at < target.played_at
```

Equal-time and future sources are excluded, and the target never enters its own
profile. A completed zero-play concession can influence a later profile through
ordinary existing game-level statistics.

## Rolling target games

Normal completion contributes 30 actual card decisions. Either concession
contributes its validated zero through 29 actual plays. The shared historical
cardinality enforces:

```text
decision_count = snapshot_count = validated played_card_count
```

No decisions are padded, inferred, duplicated, or normalized. The concession
event is not a prediction target. Metrics remain decision-weighted, so a
14-play target contributes 14 comparison rows and a zero-play target contributes
none.

A zero-decision target remains in `target_games` with all three participants,
as-of profiles and source metadata, an empty decision array, zero match counts,
and null denominator-zero rates. An all-zero-decision target set is valid when
the existing prior-participant-history condition is met.

Target coverage uses all target participant IDs. Therefore
`target_player_game_count == target_game_count * 3`, including players who did
not act before concession. Decision breakdowns and profile-availability counts
continue to include only actual decision actors.

## Information safety

Decision rows and prediction inputs do not include the target end reason,
consent, conceding defender, concession form, final winner, settlement,
unresolved points, remaining cards, or
knowledge of the future terminal event. A normal target and concession target
with the same legal prefix produce the same prediction inputs and outputs for
that prefix, apart from record/game provenance. Changing valid consent does not
change statistics, profiles, or card predictions.

This workflow evaluates deterministic policy imitation, not strategic strength,
optimal play, expected value, concession quality, or learned behavior.

## CLI

The mixed example supports aggregation and export:

```powershell
python main.py --input examples/training_dataset_shortened_opponent_workflows.json --aggregate-opponent-statistics
python main.py --input examples/training_dataset_shortened_opponent_workflows.json --aggregate-opponent-statistics --output outputs/shortened-statistics.json --export-opponent-statistics outputs/shortened-opponent-statistics.json --quiet
```

It also supports rolling evaluation:

```powershell
python main.py --input examples/training_dataset_shortened_opponent_workflows.json --evaluate-rolling-opponent-policies
```

The existing `--evaluate-opponent-policy-profiles` spelling remains supported.
The rolling schema permits zero through 30 decisions per target, empty decision
arrays, zero total target decisions, and null zero-denominator rates without a
schema or evaluation-version change.
