import json
from pathlib import Path
from unittest.mock import patch

from test_historical_game import build_historical_input
from test_session_decision_checkpoint import _ready_live_state
from test_session_decision_observation import _observed
from test_session_transitions import _complete_retrospective_session

import skat_ai.api.v1.session as session_api
import skat_ai.api.v1.session.files as session_files
import skat_ai.cli.session as session_cli
import skat_ai.cli.session_application as session_application
import skat_ai.cli.session_assistant as assistant
import skat_ai.cli.session_checkpoints as session_checkpoints


def _input_from(values: list[str]):
    iterator = iter(values)

    def input_fn(_prompt: str) -> str:
        try:
            return next(iterator)
        except StopIteration as error:
            raise EOFError from error

    return input_fn


def _creation_responses(*, session_id: str = "assistant-live") -> list[str]:
    return [
        session_id,
        "live",
        "player-a",
        "player-a",
        "Local",
        "player-b",
        "",
        "player-c",
        "",
    ]


def _create_session(path: Path) -> None:
    output = []
    responses = [*_creation_responses(), "quit"]
    assert assistant.run_session_assistant(
        str(path),
        input_fn=_input_from(responses),
        output_fn=output.append,
    ) == 0
    assert path.exists()


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
    assert session_files.save_session_file(
        path,
        document,
        expected_content_fingerprint=None,
    ).value.status == "saved"


def test_assistant_builds_exact_deterministic_command_payloads() -> None:
    play = assistant._build_command_document(
        "play",
        revision=7,
        input_fn=_input_from(["player-b", "CA"]),
    )
    assert play == {
        "command_version": 1,
        "kind": "record_play",
        "expected_revision": 7,
        "player_id": "player-b",
        "card": "CA",
    }

    declaration = {
        "game_type": "grand",
        "hand_game": True,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": None,
        "bid_value": 24,
    }
    payload = assistant._build_command_document(
        "declaration",
        revision=4,
        input_fn=_input_from([json.dumps(declaration)]),
    )
    assert payload == {
        "command_version": 1,
        "kind": "set_declaration",
        "expected_revision": 4,
        "declaration": declaration,
    }

    end = assistant._build_command_document(
        "end",
        revision=30,
        input_fn=_input_from(
            [json.dumps({"game_end_reason": "normal_completion", "game_end": None})]
        ),
    )
    assert end == {
        "command_version": 1,
        "kind": "set_game_end",
        "expected_revision": 30,
        "game_end_reason": "normal_completion",
        "game_end": None,
    }

    event = assistant._build_command_document(
        "event",
        revision=8,
        input_fn=_input_from(['{"event_type":"defender_open_play"}']),
    )
    assert event == {
        "command_version": 1,
        "kind": "set_game_event",
        "expected_revision": 8,
        "event": {"event_type": "defender_open_play"},
    }
    public_hand = assistant._build_command_document(
        "public-hand",
        revision=9,
        input_fn=_input_from(["player-b", '["CA","C10"]']),
    )
    assert public_hand == {
        "command_version": 1,
        "kind": "set_public_hand",
        "expected_revision": 9,
        "source": "declared_ouvert",
        "player_id": "player-b",
        "cards": ["CA", "C10"],
    }
    assert assistant._build_command_document(
        "promote",
        revision=10,
        input_fn=_input_from([]),
    ) == {
        "command_version": 1,
        "kind": "promote_to_retrospective",
        "expected_revision": 10,
    }


def test_assistant_creates_new_session_and_eof_is_clean(tmp_path: Path) -> None:
    session_path = tmp_path / "new-session.json"
    output = []
    assert assistant.run_session_assistant(
        str(session_path),
        input_fn=_input_from(_creation_responses()),
        output_fn=output.append,
    ) == 0
    resumed = session_files.load_session_file(session_path).value.document
    assert resumed.state.session_id == "assistant-live"
    assert resumed.state.revision == 0
    assert output[-1] == "Assistant closed at end of input."
    joined = "\n".join(output)
    assert "content_fingerprint" not in joined
    assert "state_fingerprint" not in joined
    assert "command_log" not in joined


def test_assistant_resumes_applies_exact_command_and_saves_once(
    tmp_path: Path,
) -> None:
    session_path = tmp_path / "resume.json"
    _create_session(session_path)
    output = []
    responses = ["metadata", "game-1", "", "quit"]
    with (
        patch.object(
            session_api,
            "apply_session_command",
            wraps=session_api.apply_session_command,
        ) as operation_spy,
        patch.object(
            session_files,
            "save_session_file",
            wraps=session_files.save_session_file,
        ) as save_spy,
    ):
        assert assistant.run_session_assistant(
            str(session_path),
            input_fn=_input_from(responses),
            output_fn=output.append,
        ) == 0
    assert operation_spy.call_count == 1
    assert save_spy.call_count == 1
    resumed = session_files.load_session_file(session_path).value.document
    assert resumed.state.revision == 1
    assert resumed.state.command_log[0].command.to_dict() == {
        "command_version": 1,
        "kind": "set_game_metadata",
        "expected_revision": 0,
        "game_id": "game-1",
        "played_at": None,
    }
    assert "Persistence status: saved" in output


def test_assistant_validation_failure_and_eof_preserve_last_save(
    tmp_path: Path,
) -> None:
    session_path = tmp_path / "validation.json"
    _create_session(session_path)
    before = session_path.read_bytes()
    output = []
    assert assistant.run_session_assistant(
        str(session_path),
        input_fn=_input_from(["metadata", "", ""]),
        output_fn=output.append,
    ) == 0
    assert session_path.read_bytes() == before
    assert any(line.startswith("Error: ") for line in output)
    assert output[-1] == "Assistant closed at end of input."


def test_assistant_phase_actions_are_bounded_by_current_state(tmp_path: Path) -> None:
    session_path = tmp_path / "phase.json"
    _create_session(session_path)
    context, _loaded = session_cli._load_context(str(session_path))
    actions = assistant._available_actions(context)
    assert actions == (
        "metadata",
        "dealt-card",
        "skat",
        "promote",
        "quit",
    )
    assert "play" not in actions
    assert "finalize" not in actions


def test_assistant_local_play_collects_source_checkpoint_and_saves(
    tmp_path: Path,
) -> None:
    state = _ready_live_state()
    session_path = tmp_path / "play.json"
    _persist_state(session_path, state)
    options = session_api.SessionPositionExportOptionsV1(
        sample_count=session_cli.DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        random_seed=0,
        use_basic_opponent_strategy=True,
        recommendation_method=None,
        bounded_search_settings=None,
    )
    root = session_api.export_session_position_request(state, options).value.request.to_dict()[
        "document"
    ]
    output = []
    assert assistant.run_session_assistant(
        str(session_path),
        input_fn=_input_from(["play", state.local_player_id, root["hand"][0], "quit"]),
        output_fn=output.append,
    ) == 0
    resumed = session_files.load_session_file(session_path).value.document
    assert resumed.state.revision == state.revision + 1
    assert len(resumed.decision_checkpoints) == 1
    assert resumed.decision_checkpoints[0].source_revision == state.revision
    joined = "\n".join(output)
    assert str(root["hand"]) not in joined
    assert "content_fingerprint" not in joined


def test_assistant_analyze_persists_checkpoint_before_one_execution(
    tmp_path: Path,
) -> None:
    state = _ready_live_state()
    session_path = tmp_path / "analyze.json"
    _persist_state(session_path, state)
    output = []
    fake_result = {"recommendation": {"card": "CA"}}
    with patch.object(
        session_application,
        "execute_position_request",
        return_value=fake_result,
    ) as execution_spy:
        assert assistant.run_session_assistant(
            str(session_path),
            input_fn=_input_from(["analyze", "quit"]),
            output_fn=output.append,
        ) == 0
    assert execution_spy.call_count == 1
    assert len(
        session_files.load_session_file(session_path).value.document.decision_checkpoints
    ) == 1
    assert "Position analysis completed." in output
    assert "Recommended card: CA" in output


def test_assistant_conflict_stops_without_retry(tmp_path: Path) -> None:
    session_path = tmp_path / "conflict.json"
    _create_session(session_path)
    output = []
    conflict = session_api.files.SessionPersistenceWriteResultV1(
        status="conflict",
        session_id="assistant-live",
        revision=1,
        expected_content_fingerprint="a" * 64,
        existing_content_fingerprint="b" * 64,
        requested_content_fingerprint="c" * 64,
    )
    with patch.object(
        session_checkpoints,
        "persist_mutation",
        return_value=(conflict, ()),
    ) as persistence_spy:
        assert assistant.run_session_assistant(
            str(session_path),
            input_fn=_input_from(["metadata", "game-conflict", ""]),
            output_fn=output.append,
        ) == 1
    assert persistence_spy.call_count == 1
    assert "Persistence status: conflict" in output


def test_assistant_undo_and_correction_save_exact_results(tmp_path: Path) -> None:
    session_path = tmp_path / "history.json"
    _create_session(session_path)
    output = []
    assert assistant.run_session_assistant(
        str(session_path),
        input_fn=_input_from(["metadata", "game-1", "", "undo", "0", "quit"]),
        output_fn=output.append,
    ) == 0
    assert session_files.load_session_file(session_path).value.document.state.revision == 0
    assert "Undo status: applied" in output

    output.clear()
    correction = {
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
    }
    assert assistant.run_session_assistant(
        str(session_path),
        input_fn=_input_from(
            [
                "metadata",
                "game-original",
                "",
                "correct",
                json.dumps(correction),
                "quit",
            ]
        ),
        output_fn=output.append,
    ) == 0
    resumed = session_files.load_session_file(session_path).value.document.state
    assert resumed.command_log[0].command.game_id == "game-corrected"
    assert "Correction status: applied" in output


def test_assistant_review_and_finalize_execute_without_saving(tmp_path: Path) -> None:
    _source, observed_state, checkpoint = _observed()
    review_path = tmp_path / "review.json"
    _persist_state(review_path, observed_state, checkpoints=(checkpoint,))
    review_before = review_path.read_bytes()
    review_output = []
    with patch.object(
        session_application,
        "execute_position_request",
        return_value={"post_game_review_summary": {"decision_quality": "best"}},
    ) as review_spy:
        assert assistant.run_session_assistant(
            str(review_path),
            input_fn=_input_from(["review", "0", "quit"]),
            output_fn=review_output.append,
        ) == 0
    assert review_spy.call_count == 1
    assert review_path.read_bytes() == review_before
    assert "Decision quality: best" in review_output

    historical_state = _complete_retrospective_session(build_historical_input())
    finalize_path = tmp_path / "finalize.json"
    _persist_state(finalize_path, historical_state)
    finalize_before = finalize_path.read_bytes()
    finalize_output = []
    with patch.object(
        session_application,
        "execute_historical_request",
        return_value={"historical_game_summary": {"winner": "declarer"}},
    ) as finalize_spy:
        assert assistant.run_session_assistant(
            str(finalize_path),
            input_fn=_input_from(["finalize", "quit"]),
            output_fn=finalize_output.append,
        ) == 0
    assert finalize_spy.call_count == 1
    assert finalize_path.read_bytes() == finalize_before
    assert "Winner: declarer" in finalize_output
