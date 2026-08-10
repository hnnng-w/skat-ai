import json
from pathlib import Path
from unittest.mock import patch

import pytest
from test_historical_game import build_historical_input
from test_session_decision_checkpoint import _ready_live_state
from test_session_decision_observation import _observed
from test_session_transitions import _complete_retrospective_session

import skat_ai.api.v1.session as session_api
import skat_ai.api.v1.session.files as session_files
import skat_ai.cli.execution as root_cli
import skat_ai.cli.session as session_cli


def _write_json(path: Path, document: object) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def _creation_document(*, capture_mode: str = "live") -> dict[str, object]:
    return {
        "session_id": f"cli-{capture_mode}",
        "capture_mode": capture_mode,
        "local_player_id": "player-a" if capture_mode == "live" else None,
        "players": [
            {
                "player_id": "player-a",
                "player_label": "Player A",
                "seat": "forehand",
            },
            {
                "player_id": "player-b",
                "player_label": None,
                "seat": "middlehand",
            },
            {
                "player_id": "player-c",
                "player_label": None,
                "seat": "rearhand",
            },
        ],
    }


def _new_session(tmp_path: Path, *, capture_mode: str = "live") -> Path:
    create_path = tmp_path / f"create-{capture_mode}.json"
    session_path = tmp_path / f"session-{capture_mode}.json"
    _write_json(create_path, _creation_document(capture_mode=capture_mode))
    assert session_cli.run_session_cli(
        [
            "new",
            "--session",
            str(session_path),
            "--input",
            str(create_path),
            "--quiet",
        ]
    ) == 0
    return session_path


def _persist_state(
    path: Path,
    state: session_api.SessionStateV1,
    *,
    checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...] = (),
) -> None:
    document = session_api.build_session_persistence_document(
        state,
        decision_checkpoints=checkpoints,
    ).value
    saved = session_files.save_session_file(
        path,
        document,
        expected_content_fingerprint=None,
    )
    assert saved.value.status == "saved"


def test_session_cli_contract_parser_order_and_no_default_path_are_exact() -> None:
    assert session_cli.SESSION_CLI_CONTRACT_VERSION == 1
    assert session_cli.SESSION_CLI_COMMAND == "session"
    assert session_cli.SESSION_CLI_SUBCOMMANDS == (
        "new",
        "show",
        "apply",
        "undo",
        "correct",
        "checkpoint",
        "export-position",
        "export-historical",
        "analyze",
        "review",
        "finalize",
        "assistant",
    )
    assert (
        session_cli.SESSION_CLI_PERSISTENCE_POLICY
        == "load_operate_compare_and_swap_save"
    )
    assert (
        session_cli.SESSION_CLI_ANALYSIS_POLICY
        == "export_then_existing_application_once"
    )
    assert (
        session_cli.SESSION_CLI_AUTOMATIC_CHECKPOINT_POLICY
        == "collect_without_automatic_analysis"
    )

    root_contract = tuple(
        (tuple(action.option_strings), action.default)
        for action in root_cli.build_argument_parser()._actions
    )
    parser = session_cli.build_session_argument_parser()
    subparsers = parser._subparsers._group_actions[0].choices
    assert tuple(subparsers) == session_cli.SESSION_CLI_SUBCOMMANDS
    for name, subparser in subparsers.items():
        session_action = next(
            action for action in subparser._actions if action.dest == "session"
        )
        assert session_action.required is True, name
        assert session_action.default is None, name
    assert root_contract == tuple(
        (tuple(action.option_strings), action.default)
        for action in root_cli.build_argument_parser()._actions
    )


@pytest.mark.parametrize("style", root_cli.CLI_INVOCATION_STYLES)
def test_leading_session_token_dispatches_with_invocation_specific_help(
    style: str,
    capsys,
) -> None:
    with pytest.raises(SystemExit) as raised:
        root_cli.run_cli(["session", "--help"], invocation_style=style)
    output = capsys.readouterr()
    commands = {
        "installed": "skat-ai session",
        "module": "python -m skat_ai session",
        "legacy": "python main.py session",
    }
    assert raised.value.code == 0
    assert output.out.startswith(f"usage: {commands[style]}")
    assert output.err == ""


def test_dispatch_selects_session_only_for_the_leading_token(monkeypatch) -> None:
    calls = []

    def fake_session(argv, *, invocation_style):
        calls.append((argv, invocation_style))
        return 17

    monkeypatch.setattr(session_cli, "run_session_cli", fake_session)
    assert root_cli.run_cli(["session", "show"], invocation_style="module") == 17
    assert calls == [(('show',), "module")]

    monkeypatch.setattr(root_cli, "_run_cli", lambda argv, style: (argv, style))
    assert root_cli.run_cli(["--input", "session"]) == (["--input", "session"], "installed")


@pytest.mark.parametrize("style", root_cli.CLI_INVOCATION_STYLES)
def test_new_and_show_share_installed_module_legacy_dispatch(
    tmp_path: Path,
    style: str,
) -> None:
    create_path = tmp_path / f"create-{style}.json"
    session_path = tmp_path / f"session-{style}.json"
    output_path = tmp_path / f"show-{style}.json"
    _write_json(create_path, _creation_document())
    assert root_cli.run_cli(
        [
            "session",
            "new",
            "--session",
            str(session_path),
            "--input",
            str(create_path),
            "--quiet",
        ],
        invocation_style=style,
    ) == 0
    assert root_cli.run_cli(
        [
            "session",
            "show",
            "--session",
            str(session_path),
            "--output",
            str(output_path),
            "--quiet",
        ],
        invocation_style=style,
    ) == 0
    assert json.loads(output_path.read_text(encoding="utf-8"))["operation"] == "load"


def test_new_show_apply_correct_undo_and_normal_no_save_statuses(
    tmp_path: Path,
    capsys,
) -> None:
    session_path = _new_session(tmp_path)
    show_output = tmp_path / "show.json"
    assert session_cli.run_session_cli(
        [
            "show",
            "--session",
            str(session_path),
            "--output",
            str(show_output),
            "--quiet",
        ]
    ) == 0
    assert json.loads(show_output.read_text(encoding="utf-8"))["operation"] == "load"

    command_path = tmp_path / "command.json"
    _write_json(
        command_path,
        {
            "command_version": 1,
            "kind": "set_game_metadata",
            "expected_revision": 0,
            "game_id": "game-1",
            "played_at": None,
        },
    )
    apply_output = tmp_path / "apply.json"
    assert session_cli.run_session_cli(
        [
            "apply",
            "--session",
            str(session_path),
            "--input",
            str(command_path),
            "--output",
            str(apply_output),
            "--quiet",
        ]
    ) == 0
    applied = json.loads(apply_output.read_text(encoding="utf-8"))
    assert applied["operation"] == "apply_command"
    assert applied["value"]["status"] == "applied"

    correction_path = tmp_path / "correction.json"
    _write_json(
        correction_path,
        {
            "session_history_edit_version": 1,
            "expected_revision": 1,
            "target_revision": 1,
            "replacement_command": {
                "command_version": 1,
                "kind": "set_game_metadata",
                "expected_revision": 0,
                "game_id": "game-corrected",
                "played_at": None,
            },
        },
    )
    assert session_cli.run_session_cli(
        [
            "correct",
            "--session",
            str(session_path),
            "--input",
            str(correction_path),
            "--quiet",
        ]
    ) == 0
    corrected = session_files.load_session_file(session_path).value.document
    assert corrected.state.command_log[0].command.game_id == "game-corrected"

    assert session_cli.run_session_cli(
        [
            "undo",
            "--session",
            str(session_path),
            "--target-revision",
            "0",
            "--quiet",
        ]
    ) == 0
    rewound = session_files.load_session_file(session_path).value.document
    assert rewound.state.revision == 0

    before = session_path.read_bytes()
    rejected_output = tmp_path / "rejected.json"
    assert session_cli.run_session_cli(
        [
            "undo",
            "--session",
            str(session_path),
            "--target-revision",
            "1",
            "--output",
            str(rejected_output),
            "--quiet",
        ]
    ) == 0
    assert session_path.read_bytes() == before
    assert json.loads(rejected_output.read_text(encoding="utf-8"))["value"][
        "status"
    ] == "rejected"
    assert capsys.readouterr().out == ""


def test_accepted_local_play_loads_operates_collects_builds_and_saves_once(
    tmp_path: Path,
) -> None:
    state = _ready_live_state()
    session_path = tmp_path / "ready-live.json"
    _persist_state(session_path, state)
    position = session_api.export_session_position_request(
        state,
        session_api.SessionPositionExportOptionsV1(
            sample_count=1,
            random_seed=0,
            use_basic_opponent_strategy=True,
            recommendation_method=None,
            bounded_search_settings=None,
        ),
    ).value.request.to_dict()["document"]
    command_path = tmp_path / "play.json"
    _write_json(
        command_path,
        {
            "command_version": 1,
            "kind": "record_play",
            "expected_revision": state.revision,
            "player_id": state.local_player_id,
            "card": position["hand"][0],
        },
    )
    call_order = []
    original_collection = session_cli.collect_session_decision_checkpoint_v1
    original_operation = session_api.apply_session_command

    def collect_first(**kwargs):
        call_order.append("collect")
        return original_collection(**kwargs)

    def apply_after_collection(*args, **kwargs):
        call_order.append("apply")
        return original_operation(*args, **kwargs)

    with (
        patch.object(
            session_files,
            "load_session_file",
            wraps=session_files.load_session_file,
        ) as load_spy,
        patch.object(
            session_api,
            "apply_session_command",
            side_effect=apply_after_collection,
        ) as operation_spy,
        patch.object(
            session_cli,
            "collect_session_decision_checkpoint_v1",
            side_effect=collect_first,
        ) as collection_spy,
        patch.object(
            session_api,
            "build_session_persistence_document",
            wraps=session_api.build_session_persistence_document,
        ) as build_spy,
        patch.object(
            session_files,
            "save_session_file",
            wraps=session_files.save_session_file,
        ) as save_spy,
        patch.object(
            session_cli,
            "execute_legacy_application",
            side_effect=AssertionError("ordinary mutation ran analysis"),
        ),
    ):
        assert session_cli.run_session_cli(
            [
                "apply",
                "--session",
                str(session_path),
                "--input",
                str(command_path),
                "--samples",
                "1",
                "--seed",
                "0",
                "--quiet",
            ]
        ) == 0

    assert load_spy.call_count == 1
    assert operation_spy.call_count == 1
    assert collection_spy.call_count == 1
    assert call_order == ["collect", "apply"]
    assert build_spy.call_count == 1
    assert save_spy.call_count == 1
    resumed = session_files.load_session_file(session_path).value
    assert resumed.document.state.revision == state.revision + 1
    assert len(resumed.document.decision_checkpoints) == 1
    assert resumed.document.decision_checkpoints[0].source_revision == state.revision


def test_revision_conflict_is_normal_and_performs_no_build_or_save(
    tmp_path: Path,
) -> None:
    session_path = _new_session(tmp_path)
    command_path = tmp_path / "stale.json"
    _write_json(
        command_path,
        {
            "command_version": 1,
            "kind": "set_game_metadata",
            "expected_revision": 7,
            "game_id": "stale",
            "played_at": None,
        },
    )
    before = session_path.read_bytes()
    with (
        patch.object(
            session_api,
            "build_session_persistence_document",
            side_effect=AssertionError("conflict built persistence"),
        ),
        patch.object(
            session_files,
            "save_session_file",
            side_effect=AssertionError("conflict saved persistence"),
        ),
    ):
        assert session_cli.run_session_cli(
            [
                "apply",
                "--session",
                str(session_path),
                "--input",
                str(command_path),
                "--quiet",
            ]
        ) == 0
    assert session_path.read_bytes() == before


def test_correction_collects_missing_checkpoint_from_local_play_prefix(
    tmp_path: Path,
) -> None:
    source = _ready_live_state()
    export_options = session_api.SessionPositionExportOptionsV1(
        sample_count=1,
        random_seed=0,
        use_basic_opponent_strategy=True,
        recommendation_method=None,
        bounded_search_settings=None,
    )
    hand = session_api.export_session_position_request(
        source,
        export_options,
    ).value.request.document["hand"]
    original = session_api.RecordSessionPlayCommandV1(
        expected_revision=source.revision,
        player_id=source.local_player_id,
        card=hand[0],
    )
    advanced = session_api.apply_session_command(source, original).value
    assert advanced.status == "applied"

    session_path = tmp_path / "corrected-play.json"
    _persist_state(session_path, advanced.state)
    correction_path = tmp_path / "corrected-play-input.json"
    _write_json(
        correction_path,
        {
            "session_history_edit_version": 1,
            "expected_revision": advanced.state.revision,
            "target_revision": advanced.state.revision,
            "replacement_command": {
                "command_version": 1,
                "kind": "record_play",
                "expected_revision": source.revision,
                "player_id": source.local_player_id,
                "card": hand[1],
            },
        },
    )
    assert session_cli.run_session_cli(
        [
            "correct",
            "--session",
            str(session_path),
            "--input",
            str(correction_path),
            "--samples",
            "1",
            "--seed",
            "0",
            "--quiet",
        ]
    ) == 0
    resumed = session_files.load_session_file(session_path).value.document
    assert resumed.state.command_log[-1].command.card == hand[1]
    assert len(resumed.decision_checkpoints) == 1
    assert resumed.decision_checkpoints[0].source_revision == source.revision


def test_optimistic_save_conflict_returns_failure_without_replacing_target(
    tmp_path: Path,
    capsys,
) -> None:
    session_path = _new_session(tmp_path)
    command_path = tmp_path / "accepted.json"
    _write_json(
        command_path,
        {
            "command_version": 1,
            "kind": "set_game_metadata",
            "expected_revision": 0,
            "game_id": "accepted-in-memory",
            "played_at": None,
        },
    )
    before = session_path.read_bytes()
    conflict = session_files.SessionFileApiResultV1(
        operation="save",
        value=session_files.SessionPersistenceWriteResultV1(
            status="conflict",
            session_id="cli-live",
            revision=1,
            expected_content_fingerprint="a" * 64,
            existing_content_fingerprint="b" * 64,
            requested_content_fingerprint="c" * 64,
        ),
    )
    with patch.object(
        session_files,
        "save_session_file",
        return_value=conflict,
    ) as save_spy:
        assert session_cli.run_session_cli(
            [
                "apply",
                "--session",
                str(session_path),
                "--input",
                str(command_path),
                "--quiet",
            ]
        ) == 1
    assert save_spy.call_count == 1
    assert session_path.read_bytes() == before
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        "Error: Session file changed since it was loaded; no changes were saved.\n"
    )


def test_position_export_and_analyze_persist_one_checkpoint_before_execution(
    tmp_path: Path,
) -> None:
    state = _ready_live_state()
    session_path = tmp_path / "analyze.json"
    _persist_state(session_path, state)
    export_output = tmp_path / "position-export.json"
    with patch.object(
        session_api,
        "export_session_position_request",
        wraps=session_api.export_session_position_request,
    ) as export_spy:
        assert session_cli.run_session_cli(
            [
                "export-position",
                "--session",
                str(session_path),
                "--output",
                str(export_output),
                "--samples",
                "1",
                "--seed",
                "19",
                "--quiet",
            ]
        ) == 0
    assert export_spy.call_count == 1
    exported = json.loads(export_output.read_text(encoding="utf-8"))
    assert exported["operation"] == "export_position"
    assert exported["value"]["status"] == "available"
    persisted = session_files.load_session_file(session_path).value.document
    assert len(persisted.decision_checkpoints) == 1

    analysis_output = tmp_path / "analysis.json"
    with patch.object(
        session_cli,
        "execute_legacy_application",
        wraps=session_cli.execute_legacy_application,
    ) as execution_spy:
        assert session_cli.run_session_cli(
            [
                "analyze",
                "--session",
                str(session_path),
                "--output",
                str(analysis_output),
                "--samples",
                "1",
                "--seed",
                "19",
                "--quiet",
            ]
        ) == 0
    assert execution_spy.call_count == 1
    result = json.loads(analysis_output.read_text(encoding="utf-8"))
    assert "recommendation" in result
    assert result["input_file"] == (
        f"session:{state.session_id}:revision:{state.revision}"
    )
    persisted = session_files.load_session_file(session_path).value.document
    assert len(persisted.decision_checkpoints) == 1


def test_unavailable_exports_execute_nothing_and_write_typed_results(
    tmp_path: Path,
) -> None:
    session_path = _new_session(tmp_path)
    paths = {
        "analyze": tmp_path / "analyze-unavailable.json",
        "export-historical": tmp_path / "historical-unavailable.json",
        "finalize": tmp_path / "finalize-unavailable.json",
    }
    with patch.object(
        session_cli,
        "execute_legacy_application",
        side_effect=AssertionError("unavailable export executed Application"),
    ):
        assert session_cli.run_session_cli(
            [
                "analyze",
                "--session",
                str(session_path),
                "--output",
                str(paths["analyze"]),
                "--quiet",
            ]
        ) == 0
        assert session_cli.run_session_cli(
            [
                "export-historical",
                "--session",
                str(session_path),
                "--output",
                str(paths["export-historical"]),
                "--quiet",
            ]
        ) == 0
        assert session_cli.run_session_cli(
            [
                "finalize",
                "--session",
                str(session_path),
                "--output",
                str(paths["finalize"]),
                "--quiet",
            ]
        ) == 0
    for path in paths.values():
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["value"]["status"] == "unavailable"


def test_review_and_finalize_execute_once_without_mutating_session(
    tmp_path: Path,
) -> None:
    _source, observed_state, checkpoint = _observed()
    review_session = tmp_path / "review.json"
    _persist_state(review_session, observed_state, checkpoints=(checkpoint,))
    review_before = review_session.read_bytes()
    review_output = tmp_path / "review-output.json"
    with patch.object(
        session_cli,
        "execute_legacy_application",
        wraps=session_cli.execute_legacy_application,
    ) as review_spy:
        assert session_cli.run_session_cli(
            [
                "review",
                "--session",
                str(review_session),
                "--checkpoint-index",
                "0",
                "--output",
                str(review_output),
                "--quiet",
            ]
        ) == 0
    assert review_spy.call_count == 1
    assert "post_game_review_summary" in json.loads(
        review_output.read_text(encoding="utf-8")
    )
    assert review_session.read_bytes() == review_before

    historical_state = _complete_retrospective_session(build_historical_input())
    historical_session = tmp_path / "historical.json"
    _persist_state(historical_session, historical_state)
    historical_before = historical_session.read_bytes()
    historical_output = tmp_path / "historical-output.json"
    with patch.object(
        session_cli,
        "execute_legacy_application",
        wraps=session_cli.execute_legacy_application,
    ) as finalize_spy:
        assert session_cli.run_session_cli(
            [
                "finalize",
                "--session",
                str(historical_session),
                "--output",
                str(historical_output),
                "--quiet",
            ]
        ) == 0
    assert finalize_spy.call_count == 1
    assert "historical_game_summary" in json.loads(
        historical_output.read_text(encoding="utf-8")
    )
    assert historical_session.read_bytes() == historical_before


def test_human_position_output_redacts_complete_private_card_arrays(
    tmp_path: Path,
    capsys,
) -> None:
    state = _ready_live_state()
    session_path = tmp_path / "private.json"
    _persist_state(session_path, state)
    output_path = tmp_path / "result.json"
    assert session_cli.run_session_cli(
        [
            "analyze",
            "--session",
            str(session_path),
            "--output",
            str(output_path),
            "--samples",
            "1",
            "--quiet",
        ]
    ) == 0
    capsys.readouterr()
    assert session_cli.run_session_cli(
        [
            "analyze",
            "--session",
            str(session_path),
            "--output",
            str(output_path),
            "--samples",
            "1",
        ]
    ) == 0
    output = capsys.readouterr()
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert str(result["position"]["hand"]) not in output.out
    assert "Skat: [0 private cards]" in output.out
    assert "private cards" in output.out
    assert "field_path" not in output.out


def test_strict_json_and_parser_misuse_use_failure_and_usage_codes(
    tmp_path: Path,
    capsys,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"session_id": "a", "session_id": "b"}', encoding="utf-8")
    assert session_cli.run_session_cli(
        [
            "new",
            "--session",
            str(tmp_path / "session.json"),
            "--input",
            str(malformed),
        ]
    ) == 1
    assert "Duplicate JSON object key" in capsys.readouterr().err

    with pytest.raises(SystemExit) as raised:
        session_cli.run_session_cli(["show"])
    assert raised.value.code == 2
