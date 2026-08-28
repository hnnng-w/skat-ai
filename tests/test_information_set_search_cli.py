import argparse
import inspect

import pytest

import main as legacy_main
import skatmind.cli.execution as root_cli
import skatmind.cli.session as session_cli
from skatmind.errors import SkatMindCliUsageError


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    result = {option for action in parser._actions for option in action.option_strings}
    subparsers = parser._subparsers
    if subparsers is None:
        return result
    for action in subparsers._group_actions:
        for child in action.choices.values():
            result.update(_option_strings(child))
    return result


def _metrics() -> dict[str, object]:
    agreement = {
        "comparable_decision_count": 3,
        "same_card_count": 2,
        "different_card_count": 1,
    }
    return {
        "decision_count": 4,
        "status_counts": {
            "complete": 1,
            "partial": 1,
            "timeout": 1,
            "not_available": 1,
        },
        "coverage_counts": {
            "none": 1,
            "single_exact_world": 1,
            "all_compatible_worlds": 1,
            "sampled_compatible_worlds": 1,
        },
        "selected_world_count_total": 7,
        "sampled_world_count_total": 5,
        "information_set_pimc_agreement": dict(agreement),
        "information_set_immediate_agreement": dict(agreement),
        "information_set_actual_agreement": dict(agreement),
        "pimc_actual_agreement": dict(agreement),
        "immediate_actual_agreement": dict(agreement),
        "decisions": [
            {
                "controlled_policy": "CONTROLLED_POLICY_SENTINEL",
                "observations": "OBSERVATION_SENTINEL",
                "hands": "HAND_SENTINEL",
                "states": "STATE_SENTINEL",
                "memoization": "MEMOIZATION_SENTINEL",
            }
        ],
    }


def _coaching_summary() -> dict[str, object]:
    return {
        "source_game_id": "game-information-set-coaching",
        "coverage": {
            "decision_count": 7,
            "assessable_decision_count": 4,
            "not_assessable_count": 3,
            "key_decision_count": 2,
            "turning_point_count": 1,
            "pattern_count": 2,
            "decision_recommendation_count": 2,
            "pattern_recommendation_count": 1,
            "information_set_status_counts": [
                {"information_set_status": "complete", "count": 4},
                {"information_set_status": "partial", "count": 1},
                {"information_set_status": "timeout", "count": 1},
                {"information_set_status": "unavailable", "count": 1},
                {"information_set_status": "not_available", "count": 0},
            ],
            "world_coverage_counts": [
                {"world_coverage": "none", "count": 3},
                {"world_coverage": "single_exact_world", "count": 1},
                {"world_coverage": "all_compatible_worlds", "count": 2},
                {"world_coverage": "sampled_compatible_worlds", "count": 1},
            ],
        },
        "private_policy": "POLICY_SENTINEL",
        "selected_worlds": "WORLD_SENTINEL",
    }
@pytest.mark.parametrize("style", root_cli.CLI_INVOCATION_STYLES)
def test_root_parser_has_information_set_modes_with_shared_options(style: str) -> None:
    parser = root_cli.build_argument_parser(style)
    historical = parser.parse_args(
        [
            "--historical-information-set-search-review",
            "--search-seed",
            "17",
            "--search-budget-profile",
            "historical_review_v1",
            "--samples",
            "3",
            "--seed",
            "19",
        ]
    )
    evaluation = parser.parse_args(
        [
            "--information-set-search-evaluation",
            "--search-seed",
            "23",
            "--search-budget-profile",
            "evaluation_v1",
            "--search-evaluation-partition",
            "test",
            "--search-evaluation-max-decisions",
            "5",
        ]
    )

    assert historical.historical_information_set_search_review is True
    assert historical.historical_information_set_replay_coaching is False
    assert historical.search_seed == 17
    assert historical.samples == 3
    assert historical.seed == 19
    assert evaluation.information_set_search_evaluation is True
    assert evaluation.search_evaluation_partition == ["test"]
    assert evaluation.search_evaluation_max_decisions == 5


def test_session_parser_has_no_information_set_search_root_options() -> None:
    options = _option_strings(session_cli.build_session_argument_parser())

    assert "--historical-information-set-search-review" not in options
    assert "--historical-information-set-replay-coaching" not in options
    assert "--information-set-search-evaluation" not in options


def test_historical_information_set_validation_accepts_shared_review_options() -> None:
    args = root_cli.parse_arguments(
        [
            "--historical-information-set-search-review",
            "--search-seed",
            "29",
            "--samples",
            "2",
            "--seed",
            "31",
        ]
    )

    root_cli.validate_cli_arguments(args, workflow="historical_game")
    root_cli.validate_historical_game_cli_arguments(args)

    coaching = root_cli.parse_arguments(
        [
            "--historical-information-set-search-review",
            "--historical-information-set-replay-coaching",
            "--search-seed",
            "29",
            "--samples",
            "2",
            "--seed",
            "31",
        ]
    )
    root_cli.validate_cli_arguments(coaching, workflow="historical_game")
    root_cli.validate_historical_game_cli_arguments(coaching)


def test_historical_information_set_validation_accepts_profile_options() -> None:
    args = root_cli.parse_arguments(
        [
            "--historical-information-set-search-review",
            "--search-seed",
            "29",
            "--opponent-statistics-file",
            "statistics.json",
            "--use-profile-presets",
            "--left-opponent-lead-policy",
            "highest_point",
        ]
    )

    root_cli.validate_cli_arguments(args, workflow="historical_game")
    root_cli.validate_historical_game_cli_arguments(args)

    coaching = root_cli.parse_arguments(
        [
            "--historical-information-set-replay-coaching",
            "--search-seed",
            "29",
            "--opponent-statistics-file",
            "statistics.json",
            "--use-profile-presets",
        ]
    )
    root_cli.validate_cli_arguments(coaching, workflow="historical_game")
    root_cli.validate_historical_game_cli_arguments(coaching)


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ((), "require --search-seed"),
        (("--historical-search-review",), "families cannot be combined"),
        (("--historical-replay-coaching",), "families cannot be combined"),
    ],
)
def test_historical_information_set_validation_rejects_missing_seed_and_conflicts(
    extra: tuple[str, ...],
    message: str,
) -> None:
    argv = ["--historical-information-set-search-review", *extra]
    if extra:
        argv.extend(("--search-seed", "37"))
    args = root_cli.parse_arguments(argv)

    with pytest.raises(SkatMindCliUsageError, match=message):
        root_cli.validate_cli_arguments(args, workflow="historical_game")


@pytest.mark.parametrize(
    "existing_mode",
    ("--historical-search-review", "--historical-replay-coaching"),
)
def test_information_set_coaching_rejects_existing_family(
    existing_mode: str,
) -> None:
    args = root_cli.parse_arguments(
        [
            "--historical-information-set-replay-coaching",
            existing_mode,
            "--search-seed",
            "37",
        ]
    )

    with pytest.raises(SkatMindCliUsageError, match="families cannot be combined"):
        root_cli.validate_cli_arguments(args, workflow="historical_game")


def test_information_set_modes_require_their_workflows() -> None:
    historical = root_cli.parse_arguments(
        ["--historical-information-set-search-review", "--search-seed", "41"]
    )
    evaluation = root_cli.parse_arguments(
        ["--information-set-search-evaluation", "--search-seed", "43"]
    )
    coaching = root_cli.parse_arguments(
        ["--historical-information-set-replay-coaching", "--search-seed", "41"]
    )

    with pytest.raises(SkatMindCliUsageError, match="requires historical-game input"):
        root_cli.validate_cli_arguments(historical, workflow="position_analysis")
    with pytest.raises(SkatMindCliUsageError, match="only for training_dataset_input"):
        root_cli.validate_cli_arguments(evaluation, workflow="position_analysis")
    with pytest.raises(SkatMindCliUsageError, match="requires historical-game input"):
        root_cli.validate_cli_arguments(coaching, workflow="position_analysis")


def test_information_set_evaluation_is_exclusive_and_reuses_bounded_options() -> None:
    accepted = root_cli.parse_arguments(
        [
            "--information-set-search-evaluation",
            "--search-seed",
            "47",
            "--search-evaluation-partition",
            "validation",
            "--search-evaluation-max-decisions",
            "7",
        ]
    )
    root_cli.validate_cli_arguments(accepted, workflow="training_dataset")
    root_cli.validate_training_dataset_cli_arguments(accepted)

    both = root_cli.parse_arguments(
        [
            "--information-set-search-evaluation",
            "--evaluate-bounded-search",
            "--search-seed",
            "47",
        ]
    )
    with pytest.raises(SkatMindCliUsageError, match="mutually exclusive"):
        root_cli.validate_cli_arguments(both, workflow="training_dataset")

    audit = root_cli.parse_arguments(
        [
            "--information-set-search-evaluation",
            "--audit-dataset-partitions",
            "--search-seed",
            "47",
        ]
    )
    root_cli.validate_cli_arguments(audit, workflow="training_dataset")
    with pytest.raises(SkatMindCliUsageError, match="--audit-dataset-partitions"):
        root_cli.validate_training_dataset_cli_arguments(audit)


def test_historical_transport_maps_information_set_options(monkeypatch) -> None:
    captured = []

    monkeypatch.setattr(root_cli, "load_json_object", lambda _path: {})

    def execute(_document, **kwargs):
        captured.append(kwargs)
        return {}, {}

    monkeypatch.setattr(root_cli, "execute_legacy_application", execute)

    root_cli.run_json_historical_game_analysis(
        file_path="historical.json",
        historical_information_set_search_review=True,
        historical_information_set_replay_coaching=True,
        search_seed=53,
        search_budget_profile="interactive_v1",
        sample_count=2,
        base_random_seed=59,
        quiet=True,
    )

    options = captured[0]["options"].historical_game
    assert options.information_set_search_review is True
    assert options.information_set_replay_coaching is True
    assert options.search_review is False
    assert options.replay_coaching is False
    assert options.search_seed == 53
    assert options.search_budget_profile == "interactive_v1"
    assert options.immediate_sample_count == 2
    assert options.immediate_base_random_seed == 59


def test_dataset_transport_maps_dedicated_information_set_fields(monkeypatch) -> None:
    captured = []

    monkeypatch.setattr(root_cli, "load_json_object", lambda _path: {})

    def execute(_document, **kwargs):
        captured.append(kwargs)
        return {}, {}

    monkeypatch.setattr(root_cli, "execute_legacy_application", execute)

    root_cli.run_json_information_set_search_evaluation(
        "dataset.json",
        search_seed=61,
        partitions=("test",),
        search_budget_profile="evaluation_v1",
        max_decisions=3,
        quiet=True,
    )

    options = captured[0]["options"].training_dataset
    assert options.operation == "information_set_search_evaluation"
    assert options.information_set_search_seed == 61
    assert options.information_set_search_partitions == ("test",)
    assert options.information_set_search_budget_profile == "evaluation_v1"
    assert options.information_set_search_max_decisions == 3
    assert options.bounded_search_seed is None


@pytest.mark.parametrize("style", root_cli.CLI_INVOCATION_STYLES)
def test_root_dispatch_parity_for_historical_information_set_review(
    style: str,
    monkeypatch,
) -> None:
    captured = []
    namespace = legacy_main if style == "legacy" else root_cli
    monkeypatch.setattr(
        namespace,
        "load_json_object",
        lambda _path: {"historical_game_input": {}},
    )
    monkeypatch.setattr(namespace, "validate_cli_arguments", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        namespace,
        "validate_historical_game_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(
        namespace,
        "run_json_historical_game_analysis",
        lambda **kwargs: captured.append(kwargs),
    )

    exit_code = root_cli.run_cli(
        [
            "--input",
            "historical.json",
            "--historical-information-set-search-review",
            "--historical-information-set-replay-coaching",
            "--search-seed",
            "67",
            "--samples",
            "2",
            "--seed",
            "71",
        ],
        invocation_style=style,
        legacy_namespace=legacy_main if style == "legacy" else None,
    )

    assert exit_code == 0
    assert captured[0]["historical_information_set_search_review"] is True
    assert captured[0]["historical_information_set_replay_coaching"] is True
    assert captured[0]["search_seed"] == 67
    assert captured[0]["sample_count"] == 2
    assert captured[0]["base_random_seed"] == 71


@pytest.mark.parametrize("style", root_cli.CLI_INVOCATION_STYLES)
def test_root_dispatch_parity_for_information_set_evaluation(
    style: str,
    monkeypatch,
) -> None:
    captured = []
    namespace = legacy_main if style == "legacy" else root_cli
    monkeypatch.setattr(
        namespace,
        "load_json_object",
        lambda _path: {"training_dataset_input": {}},
    )
    monkeypatch.setattr(namespace, "validate_cli_arguments", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        namespace,
        "validate_training_dataset_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(
        namespace,
        "run_json_information_set_search_evaluation",
        lambda **kwargs: captured.append(kwargs),
    )

    exit_code = root_cli.run_cli(
        [
            "--input",
            "dataset.json",
            "--information-set-search-evaluation",
            "--search-seed",
            "73",
            "--search-budget-profile",
            "evaluation_v1",
            "--search-evaluation-partition",
            "test",
            "--search-evaluation-max-decisions",
            "5",
        ],
        invocation_style=style,
        legacy_namespace=legacy_main if style == "legacy" else None,
    )

    assert exit_code == 0
    assert captured[0]["search_seed"] == 73
    assert captured[0]["partitions"] == ("test",)
    assert captured[0]["search_budget_profile"] == "evaluation_v1"
    assert captured[0]["max_decisions"] == 5


def test_legacy_dependency_seams_include_information_set_builders(
    monkeypatch,
) -> None:
    def build_review(*_args, **_kwargs):
        return {}

    def evaluate(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(
        legacy_main,
        "build_historical_information_set_search_review_v1",
        build_review,
    )

    def serialize_review(value):
        return value

    monkeypatch.setattr(
        legacy_main,
        "build_serializable_historical_information_set_search_review_v1",
        serialize_review,
    )
    monkeypatch.setattr(
        legacy_main,
        "evaluate_information_set_search_dataset_v1",
        evaluate,
    )

    with root_cli.legacy_patch_namespace(legacy_main):
        dependencies = root_cli.build_legacy_application_dependencies()

    assert dependencies.historical_game.build_information_set_search_review is build_review
    assert (
        dependencies.historical_game.serialize_information_set_search_review
        is serialize_review
    )
    assert dependencies.training_dataset.evaluate_information_set_search is evaluate
    assert hasattr(legacy_main, "run_json_information_set_search_evaluation")
    assert inspect.signature(
        legacy_main.run_json_information_set_search_evaluation
    ) == inspect.signature(root_cli.run_json_information_set_search_evaluation)


def test_information_set_presentations_are_concise_and_safe(capsys) -> None:
    historical = _metrics()
    dataset = {**_metrics(), "record_count": 2}

    root_cli.print_historical_information_set_search_review_result(historical)
    root_cli.print_historical_information_set_replay_coaching_result(
        _coaching_summary()
    )
    root_cli.print_information_set_search_evaluation_result(
        {"information_set_search_evaluation_summary": dataset}
    )

    output = capsys.readouterr().out
    assert "Evaluated decisions: 4" in output
    assert "complete 1, partial 1, timeout 1, unavailable 1" in output
    assert "Recommendation agreement:" in output
    assert "Actual-card agreement:" in output
    assert "Selected-world coverage:" in output
    assert "7 selected; 5 sampled draws." in output
    assert "Information-set Search evaluation records: 2" in output
    assert "Historical Information-set Replay Coaching Report" in output
    assert "Source game: game-information-set-coaching" in output
    assert "Assessable decisions: 4" in output
    assert "Not assessable: 3" in output
    assert "Key Decisions: 2" in output
    assert "Turning Points: 1" in output
    assert "Patterns: 2" in output
    assert "Recommendations: 3" in output
    assert "Information-set Search coverage:" in output
    for unsafe in (
        "controlled_policy",
        "observations",
        "hands",
        "states",
        "memoization",
        "SENTINEL",
        "private_policy",
        "selected_worlds",
    ):
        assert unsafe not in output
