import argparse

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


@pytest.mark.parametrize("style", root_cli.CLI_INVOCATION_STYLES)
def test_root_parser_has_historical_tactical_motif_option(style: str) -> None:
    args = root_cli.build_argument_parser(style).parse_args(["--historical-tactical-motif-review"])

    assert args.historical_tactical_motif_review is True
    assert "--historical-tactical-motif-review" not in _option_strings(
        session_cli.build_session_argument_parser()
    )


def test_tactical_motif_cli_option_is_historical_only() -> None:
    args = root_cli.parse_arguments(["--historical-tactical-motif-review"])

    root_cli.validate_cli_arguments(args, workflow="historical_game")
    root_cli.validate_historical_game_cli_arguments(args)
    with pytest.raises(SkatMindCliUsageError, match="requires historical-game input"):
        root_cli.validate_cli_arguments(args, workflow="position")


def test_historical_transport_maps_tactical_motif_option(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(root_cli, "load_json_object", lambda _path: {})

    def execute(_document, **kwargs):
        captured.append(kwargs)
        return {}, {}

    monkeypatch.setattr(root_cli, "execute_legacy_application", execute)

    root_cli.run_json_historical_game_analysis(
        file_path="historical.json",
        historical_tactical_motif_review=True,
        quiet=True,
    )

    assert captured[0]["options"].historical_game.historical_tactical_motif_review is True


@pytest.mark.parametrize("style", root_cli.CLI_INVOCATION_STYLES)
def test_root_dispatch_parity_for_historical_tactical_motif_review(
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
            "--historical-tactical-motif-review",
        ],
        invocation_style=style,
        legacy_namespace=legacy_main if style == "legacy" else None,
    )

    assert exit_code == 0
    assert captured[0]["historical_tactical_motif_review"] is True


def test_tactical_motif_presentation_is_aggregate_only(capsys) -> None:
    root_cli.print_historical_tactical_motif_review_result(
        {
            "source_game_id": "game-1",
            "observation_count": 3,
            "complete_observation_count": 3,
            "partial_observation_count": 0,
            "motif_occurrence_count": 2,
            "motif_counts": [
                {"motif_type": "partner_overtake", "count": 2},
                {"motif_type": "trump_lead", "count": 0},
            ],
            "family_counts": [{"motif_family": "defender_partnership", "count": 2}],
            "observations": "PRIVATE_SENTINEL",
        }
    )

    output = capsys.readouterr().out
    assert "Historical Tactical Motif Review" in output
    assert "partner_overtake=2" in output
    assert "defender_partnership=2" in output
    assert "trump_lead" not in output
    assert "PRIVATE_SENTINEL" not in output
