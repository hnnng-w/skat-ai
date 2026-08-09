import copy
import json
import tomllib
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest
from test_historical_declarer_card_exposure import build_exposure_prefix
from test_historical_declarer_card_exposure_continuation import (
    build_event_record as build_declarer_exposure_continuation,
)
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_defender_open_play import build_open_play_prefix
from test_historical_defender_open_play_continuation import (
    build_event_record as build_defender_open_play_continuation,
)
from test_historical_game import build_historical_input
from test_historical_game_event_chain import (
    CONTINUATION_KINDS,
    TERMINAL_BUILDERS,
    add_continuation,
)
from test_historical_open_card_throw import build_throw_prefix
from test_input_schema import INPUT_VALIDATOR
from test_session_transitions import (
    _apply,
    _complete_retrospective_session,
    _declaration_from_data,
    _metadata,
    _play_commands_from_data,
    _players,
)

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.session_historical_export as historical_export_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skat_ai.cli import execution as cli
from skat_ai.errors import SkatAIInvariantError
from skat_ai.game_declaration import GameDeclaration
from skat_ai.historical_game import (
    build_historical_game_record,
    build_serializable_historical_record,
)
from skat_ai.input_loader import build_historical_game_from_document
from skat_ai.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionDiscardCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEndCommandV1,
)
from skat_ai.session_contracts import SessionStateV1
from skat_ai.session_export_contracts import (
    SESSION_EXPORT_STATUSES,
    SESSION_HISTORICAL_EXPORT_POLICY,
    SESSION_REQUEST_EXPORT_POLICY,
    SESSION_REQUEST_EXPORT_VERSION,
    SessionRequestExportV1,
)
from skat_ai.session_historical_export import (
    export_session_historical_game_request_v1,
)
from skat_ai.session_transitions import (
    apply_session_command_v1,
    create_session_state_v1,
    replay_session_state_v1,
)
from skat_ai.session_validation import SessionValidationDiagnosticV1

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _historical_input(result: SessionRequestExportV1) -> dict:
    assert result.request is not None
    return result.request.to_dict()["document"]["historical_game_input"]


def _canonical_input(data: dict) -> dict:
    return build_serializable_historical_record(build_historical_game_record(data))


def _export_data(data: dict) -> tuple[SessionStateV1, SessionRequestExportV1]:
    state = _complete_retrospective_session(data)
    return state, export_session_historical_game_request_v1(state)


def _blocking_diagnostic(
    *,
    path: str = "/phase",
    code: str = "phase_violation",
    position: bool = False,
) -> SessionValidationDiagnosticV1:
    return SessionValidationDiagnosticV1(
        code=code,
        path=path,
        message="The export target is blocked.",
        severity="info",
        blocks_command=False,
        blocks_position_export=position,
        blocks_historical_export=not position,
    )


def _late_promoted_normal_session(data: dict) -> SessionStateV1:
    local_player_id = data["players"][0]["player_id"]
    state = create_session_state_v1(
        session_id="session-late-promotion",
        players=_players(),
        capture_mode="live",
        local_player_id=local_player_id,
    )
    state = _metadata(state, game_id="late-promoted-game")
    for card in reversed(data["players"][0]["initial_hand"]):
        state = _apply(
            state,
            RecordSessionDealtCardCommandV1(
                expected_revision=state.revision,
                destination="player_hand",
                player_id=local_player_id,
                card=card,
            ),
        )
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id=data["declarer_player_id"],
        ),
    )
    state = _apply(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=_declaration_from_data(data),
        ),
    )
    state = _play_commands_from_data(state, data)
    state = _apply(
        state,
        SetSessionGameEndCommandV1(
            expected_revision=state.revision,
            game_end_reason="normal_completion",
            game_end=None,
        ),
    )
    return _apply(
        state,
        PromoteSessionToRetrospectiveCommandV1(expected_revision=state.revision),
    )


def _early_promoted_normal_session(data: dict) -> SessionStateV1:
    local_player_id = data["players"][0]["player_id"]
    state = create_session_state_v1(
        session_id="session-early-promotion",
        players=_players(),
        capture_mode="live",
        local_player_id=local_player_id,
    )
    state = _metadata(
        state,
        game_id="early-promoted-game",
        **({"played_at": data["played_at"]} if "played_at" in data else {}),
    )
    for card in reversed(data["players"][0]["initial_hand"]):
        state = _apply(
            state,
            RecordSessionDealtCardCommandV1(
                expected_revision=state.revision,
                destination="player_hand",
                player_id=local_player_id,
                card=card,
            ),
        )
    state = _apply(
        state,
        PromoteSessionToRetrospectiveCommandV1(expected_revision=state.revision),
    )
    for player in data["players"][1:]:
        for card in reversed(player["initial_hand"]):
            state = _apply(
                state,
                RecordSessionDealtCardCommandV1(
                    expected_revision=state.revision,
                    destination="player_hand",
                    player_id=player["player_id"],
                    card=card,
                ),
            )
    for card in reversed(data["skat"]):
        state = _apply(
            state,
            RecordSessionDealtCardCommandV1(
                expected_revision=state.revision,
                destination="skat",
                player_id=None,
                card=card,
            ),
        )
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id=data["declarer_player_id"],
        ),
    )
    state = _apply(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=_declaration_from_data(data),
        ),
    )
    for card in data["discarded_cards"]:
        state = _apply(
            state,
            RecordSessionDiscardCommandV1(
                expected_revision=state.revision,
                card=card,
            ),
        )
    state = _play_commands_from_data(state, data)
    return _apply(
        state,
        SetSessionGameEndCommandV1(
            expected_revision=state.revision,
            game_end_reason="normal_completion",
            game_end=None,
        ),
    )


def test_export_constants_and_contract_shape_are_exact() -> None:
    assert SESSION_REQUEST_EXPORT_VERSION == 1
    assert SESSION_REQUEST_EXPORT_POLICY == "existing_root_request_contract"
    assert SESSION_HISTORICAL_EXPORT_POLICY == "exact_ready_retrospective_state"
    assert SESSION_EXPORT_STATUSES == ("available", "unavailable")
    assert [field.name for field in fields(SessionRequestExportV1)] == [
        "session_request_export_version",
        "session_id",
        "source_revision",
        "target",
        "status",
        "request",
        "diagnostics",
    ]


def test_export_contract_available_and_unavailable_invariants_are_exact() -> None:
    request = RequestDocumentV1(
        workflow=WorkflowV1.HISTORICAL_GAME,
        document={"historical_game_input": {}},
    )
    available = SessionRequestExportV1(
        session_id="session-152",
        source_revision=3,
        target="historical_game",
        status="available",
        request=request,
        diagnostics=(),
    )
    first = _blocking_diagnostic(path="/z", code="game_end_violation")
    second = _blocking_diagnostic(path="/a", code="phase_violation")
    unavailable = SessionRequestExportV1(
        session_id="session-152",
        source_revision=2,
        target="historical_game",
        status="unavailable",
        request=None,
        diagnostics=[first, second],
    )

    assert not hasattr(available, "__dict__")
    assert unavailable.diagnostics == (second, first)
    assert available.to_dict()["request"]["workflow"] == "historical_game"
    assert unavailable.to_dict()["request"] is None
    mutable = available.to_dict()
    mutable["request"]["document"]["historical_game_input"]["changed"] = True
    assert "changed" not in available.to_dict()["request"]["document"][
        "historical_game_input"
    ]
    with pytest.raises(FrozenInstanceError):
        available.status = "unavailable"

    invalid_values = (
        {"status": "available", "request": None, "diagnostics": ()},
        {
            "status": "available",
            "request": request,
            "diagnostics": (first,),
        },
        {
            "status": "unavailable",
            "request": request,
            "diagnostics": (first,),
        },
        {"status": "unavailable", "request": None, "diagnostics": ()},
        {
            "status": "unavailable",
            "request": None,
            "diagnostics": (_blocking_diagnostic(position=True),),
        },
    )
    for values in invalid_values:
        with pytest.raises(ValueError):
            SessionRequestExportV1(
                session_id="session-152",
                source_revision=0,
                target="historical_game",
                **values,
            )

    position_request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document={},
    )
    with pytest.raises(ValueError, match="target"):
        SessionRequestExportV1(
            session_id="session-152",
            source_revision=0,
            target="position_analysis",
            status="available",
            request=position_request,
            diagnostics=(),
        )
    with pytest.raises(ValueError, match="workflow"):
        SessionRequestExportV1(
            session_id="session-152",
            source_revision=0,
            target="historical_game",
            status="available",
            request=position_request,
            diagnostics=(),
        )


@pytest.mark.parametrize("session_id", ("", " padded", "padded "))
def test_export_contract_rejects_invalid_session_id(session_id: str) -> None:
    with pytest.raises(ValueError, match="session_id"):
        SessionRequestExportV1(
            session_id=session_id,
            source_revision=0,
            target="historical_game",
            status="unavailable",
            request=None,
            diagnostics=(_blocking_diagnostic(),),
        )


@pytest.mark.parametrize("source_revision", (-1, True, 1.0, "0"))
def test_export_contract_rejects_invalid_source_revision(source_revision: object) -> None:
    with pytest.raises(ValueError, match="source_revision"):
        SessionRequestExportV1(
            session_id="session-152",
            source_revision=source_revision,
            target="historical_game",
            status="unavailable",
            request=None,
            diagnostics=(_blocking_diagnostic(),),
        )


@pytest.mark.parametrize("version", (2, True, 1.0))
def test_export_contract_rejects_wrong_version(version: object) -> None:
    with pytest.raises(ValueError, match="session_request_export_version"):
        SessionRequestExportV1(
            session_request_export_version=version,
            session_id="session-152",
            source_revision=0,
            target="historical_game",
            status="unavailable",
            request=None,
            diagnostics=(_blocking_diagnostic(),),
        )


def test_unavailable_export_replays_once_retains_current_blockers_and_skips_builder(
    monkeypatch,
) -> None:
    state = create_session_state_v1(
        session_id="session-unavailable",
        players=_players(),
        capture_mode="retrospective",
    )
    before = state.to_dict()
    replay_count = 0
    original_replay = historical_export_module.replay_session_state_v1

    def counted_replay(value):
        nonlocal replay_count
        replay_count += 1
        return original_replay(value)

    def forbidden_builder(value):
        del value
        raise AssertionError("Historical Builder must not run while unavailable.")

    monkeypatch.setattr(
        historical_export_module,
        "replay_session_state_v1",
        counted_replay,
    )
    monkeypatch.setattr(
        historical_export_module,
        "build_historical_game_record",
        forbidden_builder,
    )

    result = historical_export_module.export_session_historical_game_request_v1(
        state
    )

    expected_blockers = tuple(
        diagnostic
        for diagnostic in state.validation.diagnostics
        if diagnostic.blocks_historical_export
    )
    assert replay_count == 1
    assert result.status == "unavailable"
    assert result.request is None
    assert result.diagnostics == expected_blockers
    assert result.source_revision == 0
    assert state.to_dict() == before


def test_normal_completion_exports_exact_canonical_root_and_immutable_request() -> None:
    data = build_historical_input()
    expected_record = build_historical_game_record(data)
    expected_input = build_serializable_historical_record(expected_record)
    state, result = _export_data(data)
    assert result.status == "available"
    assert result.session_id == state.session_id
    assert result.source_revision == state.revision
    assert result.target == "historical_game"
    assert result.diagnostics == ()
    assert result.request is not None
    assert result.request.workflow is WorkflowV1.HISTORICAL_GAME

    root = result.request.to_dict()["document"]
    assert list(root) == ["historical_game_input"]
    assert root["historical_game_input"] == expected_input
    assert list(INPUT_VALIDATOR.iter_errors(root)) == []
    assert build_historical_game_from_document(root) == expected_record
    assert len(root["historical_game_input"]["tricks"]) == 10
    assert sum(
        len(trick["plays"])
        for trick in root["historical_game_input"]["tricks"]
    ) == 30
    assert "game_end" not in root["historical_game_input"]

    forbidden_fields = {
        "session_id",
        "revision",
        "phase",
        "capture_mode",
        "command_log",
        "validation",
        "winner_player_id",
        "winner_side",
        "trick_points",
        "next_player_id",
        "field_provenance",
    }
    serialized = json.dumps(root["historical_game_input"])
    assert all(f'"{field}"' not in serialized for field in forbidden_fields)
    with pytest.raises(TypeError):
        result.request.document["new"] = {}
    with pytest.raises(TypeError):
        result.request.document["historical_game_input"]["players"][0][
            "player_id"
        ] = "changed"


def test_players_initial_hands_labels_seats_skat_and_discards_map_canonically() -> None:
    data = build_historical_input()
    state, result = _export_data(data)
    projection = replay_session_state_v1(state)
    exported = _historical_input(result)

    assert [player["player_id"] for player in exported["players"]] == [
        "player-a",
        "player-b",
        "player-c",
    ]
    assert [player["seat"] for player in exported["players"]] == [
        "forehand",
        "middlehand",
        "rearhand",
    ]
    assert exported["players"][0]["player_label"] == "Alice"
    assert "player_label" not in exported["players"][1]
    assert exported["players"][2]["player_label"] == "Carol"
    assert all(len(player["initial_hand"]) == 10 for player in exported["players"])
    assert exported["skat"] == list(projection.known_skat)
    assert exported["discarded_cards"] == list(projection.discarded_cards)
    assert {
        card
        for player in exported["players"]
        for card in player["initial_hand"]
    } | set(exported["skat"]) == set(
        card
        for player in data["players"]
        for card in player["initial_hand"]
    ) | set(data["skat"])
    assert all(
        player["initial_hand"] != list(projection.remaining_hand_for(player["player_id"]) or ())
        for player in exported["players"]
    )


@pytest.mark.parametrize("played_at", (None, "2026-08-09T12:34:56Z"))
def test_optional_played_at_is_omitted_or_preserved(played_at: str | None) -> None:
    data = build_historical_input()
    if played_at is not None:
        data["played_at"] = played_at
    _, result = _export_data(data)
    exported = _historical_input(result)
    assert exported["game_id"] == data["game_id"]
    if played_at is None:
        assert "played_at" not in exported
    else:
        assert exported["played_at"] == played_at


@pytest.mark.parametrize(
    (
        "game_type",
        "hand_game",
        "ouvert",
        "schneider_announced",
        "schwarz_announced",
    ),
    (
        ("clubs", False, False, False, False),
        ("clubs", True, False, True, False),
        ("clubs", True, True, True, True),
        ("grand", True, False, False, False),
        ("grand", True, False, True, True),
        ("grand", True, True, True, True),
        ("null", False, False, False, False),
        ("null", True, False, False, False),
        ("null", False, True, False, False),
        ("null", True, True, False, False),
    ),
)
def test_suit_grand_and_all_null_variants_export_canonical_declarations(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
    schneider_announced: bool,
    schwarz_announced: bool,
) -> None:
    data = build_historical_input(game_type=game_type, hand_game=hand_game)
    data["declaration"]["ouvert"] = ouvert
    if game_type != "null":
        data["declaration"]["schneider_announced"] = schneider_announced
        data["declaration"]["schwarz_announced"] = schwarz_announced
    _, result = _export_data(data)
    exported = _historical_input(result)
    assert exported == _canonical_input(data)
    declaration = exported["declaration"]
    assert declaration["game_type"] == game_type
    assert declaration["hand_game"] is hand_game
    assert declaration["ouvert"] is ouvert
    assert exported["discarded_cards"] == ([] if hand_game else data["discarded_cards"])
    if game_type == "null":
        assert "matadors" not in declaration
        assert "schneider_announced" not in declaration
        assert "schwarz_announced" not in declaration
    else:
        assert isinstance(declaration["matadors"], int)


@pytest.mark.parametrize("game_type", ("clubs", "grand"))
def test_omitted_and_matching_matadors_use_existing_builder_inference(
    game_type: str,
) -> None:
    omitted = build_historical_input(game_type=game_type)
    inferred = _canonical_input(omitted)["declaration"]["matadors"]
    _, omitted_result = _export_data(omitted)
    assert _historical_input(omitted_result)["declaration"]["matadors"] == inferred

    matching = copy.deepcopy(omitted)
    matching["declaration"]["matadors"] = inferred
    _, matching_result = _export_data(matching)
    assert _historical_input(matching_result) == _canonical_input(matching)


@pytest.mark.parametrize("game_type", ("clubs", "grand"))
def test_conflicting_matadors_remain_rejected_before_export(game_type: str) -> None:
    data = build_historical_input(game_type=game_type)
    inferred = _canonical_input(data)["declaration"]["matadors"]
    state = create_session_state_v1(
        session_id="session-matador-conflict",
        players=_players(),
        capture_mode="retrospective",
    )
    state = _metadata(state, game_id="matador-conflict")
    for player in data["players"]:
        for card in player["initial_hand"]:
            state = _apply(
                state,
                RecordSessionDealtCardCommandV1(
                    expected_revision=state.revision,
                    destination="player_hand",
                    player_id=player["player_id"],
                    card=card,
                ),
            )
    for card in data["skat"]:
        state = _apply(
            state,
            RecordSessionDealtCardCommandV1(
                expected_revision=state.revision,
                destination="skat",
                player_id=None,
                card=card,
            ),
        )
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id=data["declarer_player_id"],
        ),
    )
    conflict = apply_session_command_v1(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=GameDeclaration(
                game_type=game_type,
                matadors=1 if inferred != 1 else 2,
                bid_value=18,
            ),
        ),
    )
    assert conflict.status == "rejected"
    assert conflict.diagnostics[0].code == "declaration_violation"
    result = export_session_historical_game_request_v1(state)
    assert result.status == "unavailable"
    assert result.request is None


@pytest.mark.parametrize(
    "builder",
    (
        lambda: build_concession_prefix(
            completed_trick_count=5,
            current_trick_card_count=2,
        ),
        lambda: build_defender_concession_prefix(
            completed_trick_count=5,
            current_trick_card_count=2,
        ),
        lambda: build_exposure_prefix(
            completed_trick_count=5,
            current_trick_card_count=2,
        ),
        lambda: build_open_play_prefix(
            completed_trick_count=5,
            current_trick_card_count=2,
        ),
        lambda: build_throw_prefix(
            completed_trick_count=5,
            current_trick_card_count=2,
        ),
    ),
    ids=(
        "declarer_concession",
        "defender_concession",
        "declarer_card_exposure",
        "defender_open_play",
        "open_card_throw",
    ),
)
def test_every_terminal_game_end_exports_exact_variable_prefix(builder) -> None:
    data = builder()
    _, result = _export_data(data)
    exported = _historical_input(result)
    assert exported == _canonical_input(data)
    assert exported["game_end_reason"] == data["game_end_reason"]
    assert exported["game_end"] == _canonical_input(data)["game_end"]
    assert sum(len(trick["plays"]) for trick in exported["tricks"]) < 30
    assert len(exported["tricks"][-1]["plays"]) == 2
    assert set(exported["tricks"][-1]) == {
        "trick_number",
        "leader_player_id",
        "plays",
    }


@pytest.mark.parametrize(
    ("completed_tricks", "current_plays"),
    ((0, 0), (4, 0), (4, 1), (4, 2)),
)
def test_terminal_prefix_preserves_complete_and_optional_incomplete_final_trick(
    completed_tricks: int,
    current_plays: int,
) -> None:
    data = build_concession_prefix(
        completed_trick_count=completed_tricks,
        current_trick_card_count=current_plays,
    )
    _, result = _export_data(data)
    exported = _historical_input(result)
    assert exported == _canonical_input(data)
    assert len(exported["tricks"]) == completed_tricks + (current_plays > 0)
    if current_plays:
        assert len(exported["tricks"][-1]["plays"]) == current_plays


@pytest.mark.parametrize(
    "builder",
    (
        build_defender_open_play_continuation,
        build_declarer_exposure_continuation,
    ),
    ids=(
        "defender_open_play_continuation",
        "declarer_card_exposure_continuation",
    ),
)
def test_both_continuations_preserve_original_authorized_cards_through_completion(
    builder,
) -> None:
    data = builder()
    state, result = _export_data(data)
    projection = replay_session_state_v1(state)
    exported = _historical_input(result)
    assert exported == _canonical_input(data)
    assert exported["game_events"] == _canonical_input(data)["game_events"]
    event = exported["game_events"][0]
    assert event["after_play_count"] == data["game_events"][0]["after_play_count"]
    original_cards = event.get("exposed_cards", event.get("public_declarer_cards"))
    owner_id = event.get(
        "exposing_defender_player_id",
        exported["declarer_player_id"],
    )
    assert original_cards
    assert projection.public_hand_for(owner_id) == ()


@pytest.mark.parametrize("continuation_kind", CONTINUATION_KINDS)
@pytest.mark.parametrize("terminal_kind", TERMINAL_BUILDERS)
def test_every_continuation_terminal_chain_exports_canonically(
    continuation_kind: str,
    terminal_kind: str,
) -> None:
    data = add_continuation(TERMINAL_BUILDERS[terminal_kind](), continuation_kind)
    _, result = _export_data(data)
    exported = _historical_input(result)
    assert exported == _canonical_input(data)
    assert len(exported["game_events"]) == 1
    assert exported["game_events"][0]["kind"] == continuation_kind
    assert exported["game_end"]["kind"] == terminal_kind


def test_canonical_record_round_trip_and_repeated_export_are_stable() -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["declarer_concession"](),
        "declarer_card_exposure_continuation",
    )
    state = _complete_retrospective_session(data)
    before = state.to_dict()
    first = export_session_historical_game_request_v1(state)
    second = export_session_historical_game_request_v1(state)
    canonical = _historical_input(first)
    rebuilt = build_historical_game_record(canonical)
    assert first == second
    assert first.to_dict() == second.to_dict()
    assert json.dumps(first.to_dict()) == json.dumps(second.to_dict())
    assert rebuilt == build_historical_game_record(data)
    assert build_serializable_historical_record(rebuilt) == canonical
    assert state.to_dict() == before
    assert state.command_log == tuple(state.command_log)


def test_early_promotion_can_become_ready_but_late_incomplete_promotion_cannot() -> None:
    data = build_historical_input()
    early = _early_promoted_normal_session(data)
    late = _late_promoted_normal_session(data)

    early_result = export_session_historical_game_request_v1(early)
    late_result = export_session_historical_game_request_v1(late)

    assert early.initial_capture_mode == "live"
    assert early.capture_mode == "retrospective"
    assert early_result.status == "available"
    assert _historical_input(early_result)["game_id"] == "early-promoted-game"
    assert late.initial_capture_mode == "live"
    assert late.capture_mode == "retrospective"
    assert late.phase == "ended"
    assert late_result.status == "unavailable"
    assert late_result.request is None
    assert {diagnostic.path for diagnostic in late_result.diagnostics} >= {
        "/initial_known_hands",
        "/discarded_cards",
    }


def test_export_rejects_wrong_type_and_forged_state() -> None:
    with pytest.raises(ValueError, match="SessionStateV1"):
        export_session_historical_game_request_v1(object())

    state = _complete_retrospective_session(build_historical_input())
    subclass = type("SessionStateSubclass", (SessionStateV1,), {})
    subclass_state = subclass(
        session_contract_version=state.session_contract_version,
        session_id=state.session_id,
        initial_capture_mode=state.initial_capture_mode,
        capture_mode=state.capture_mode,
        revision=state.revision,
        phase=state.phase,
        players=state.players,
        local_player_id=state.local_player_id,
        command_log=state.command_log,
        validation=state.validation,
    )
    with pytest.raises(ValueError, match="SessionStateV1"):
        export_session_historical_game_request_v1(subclass_state)

    forged = copy.copy(state)
    object.__setattr__(forged, "phase", "play")
    with pytest.raises(SkatAIInvariantError, match="phase"):
        export_session_historical_game_request_v1(forged)

    forged_revision = copy.copy(state)
    object.__setattr__(forged_revision, "revision", state.revision + 1)
    with pytest.raises(SkatAIInvariantError, match="revision"):
        export_session_historical_game_request_v1(forged_revision)


def test_ready_builder_failure_is_an_invariant_with_original_cause(monkeypatch) -> None:
    state = _complete_retrospective_session(build_historical_input())

    def fail_builder(data):
        del data
        raise ValueError("builder disagreement")

    monkeypatch.setattr(
        historical_export_module,
        "build_historical_game_record",
        fail_builder,
    )
    with pytest.raises(SkatAIInvariantError, match="canonical Request") as captured:
        historical_export_module.export_session_historical_game_request_v1(state)
    assert isinstance(captured.value.__cause__, ValueError)
    assert str(captured.value.__cause__) == "builder disagreement"


def test_changed_canonical_rebuild_is_an_invariant(monkeypatch) -> None:
    state = _complete_retrospective_session(build_historical_input())
    original_builder = historical_export_module.build_historical_game_record
    builder_count = 0

    def changed_rebuild(data):
        nonlocal builder_count
        builder_count += 1
        record = original_builder(data)
        if builder_count == 2:
            return replace(record, game_id="changed-game")
        return record

    monkeypatch.setattr(
        historical_export_module,
        "build_historical_game_record",
        changed_rebuild,
    )
    with pytest.raises(SkatAIInvariantError, match="rebuild changed"):
        historical_export_module.export_session_historical_game_request_v1(state)
    assert builder_count == 2


def test_available_export_execution_count_boundary(monkeypatch) -> None:
    state = _complete_retrospective_session(build_historical_input())
    replay_count = 0
    builder_count = 0
    serializer_count = 0
    original_replay = historical_export_module.replay_session_state_v1
    original_builder = historical_export_module.build_historical_game_record
    original_serializer = historical_export_module.build_serializable_historical_record

    def counted_replay(value):
        nonlocal replay_count
        replay_count += 1
        return original_replay(value)

    def counted_builder(value):
        nonlocal builder_count
        builder_count += 1
        return original_builder(value)

    def counted_serializer(value):
        nonlocal serializer_count
        serializer_count += 1
        return original_serializer(value)

    monkeypatch.setattr(
        historical_export_module,
        "replay_session_state_v1",
        counted_replay,
    )
    monkeypatch.setattr(
        historical_export_module,
        "build_historical_game_record",
        counted_builder,
    )
    monkeypatch.setattr(
        historical_export_module,
        "build_serializable_historical_record",
        counted_serializer,
    )

    result = historical_export_module.export_session_historical_game_request_v1(
        state
    )
    assert result.status == "available"
    assert replay_count == 1
    assert builder_count == 2
    assert serializer_count == 1


def test_public_api_cli_schema_output_and_package_boundaries_are_unchanged() -> None:
    assert skat_ai.__all__ == ("api", "errors", "__version__")
    assert all("Session" not in name for name in api_v1.__all__)
    assert not hasattr(api_v1, "export_session_historical_game_request_v1")
    assert tuple(workflow.value for workflow in WorkflowV1) == (
        "position_analysis",
        "historical_game",
        "training_dataset",
        "training_dataset_preparation",
        "opponent_statistics",
        "fixed_three_player_historical_list",
        "fixed_three_player_historical_list_comparison",
    )
    assert all(
        "session" not in option
        for action in cli.build_argument_parser()._actions
        for option in action.option_strings
    )
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 62
    assert len(
        tuple(
            (PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob(
                "*.schema.json"
            )
        )
    ) == 62
    assert len(SCENARIOS) == 77
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["version"] == "0.13.0"
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert skat_ai.__version__ == "0.13.0"
