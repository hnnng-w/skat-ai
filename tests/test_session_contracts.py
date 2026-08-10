import json
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import MappingProxyType

import pytest

import skat_ai
import skat_ai.api.v1 as api_v1
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1 import WorkflowV1
from skat_ai.cli import execution as cli
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.historical_game import (
    HistoricalGameRecord,
    build_historical_game_summary_from_input,
)
from skat_ai.session_commands import (
    SESSION_COMMAND_ALLOWED_PHASES,
    SESSION_COMMAND_KINDS,
    SESSION_COMMAND_TYPES,
    SESSION_COMMAND_VERSION,
    SESSION_DEAL_DESTINATIONS,
    SESSION_GAME_END_REASONS,
    SESSION_GAME_EVENT_KINDS,
    SESSION_PUBLIC_HAND_SOURCES,
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionDiscardCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionGameMetadataCommandV1,
    SetSessionPublicHandCommandV1,
)
from skat_ai.session_contracts import (
    SESSION_CAPTURE_MODES,
    SESSION_CONTRACT_VERSION,
    SESSION_IDENTIFIER_POLICY,
    SESSION_MODE_TRANSITION_POLICY,
    SESSION_PHASES,
    SESSION_REJECTED_COMMAND_POLICY,
    SESSION_REVISION_POLICY,
    SESSION_STATE_POLICY,
    SESSION_TIME_POLICY,
    SessionCommandRecordV1,
    SessionPlayerV1,
    SessionStateV1,
)
from skat_ai.session_validation import (
    SESSION_DIAGNOSTIC_CODES,
    SESSION_DIAGNOSTIC_SEVERITIES,
    SESSION_EXPORT_READINESS_STATUSES,
    SESSION_EXPORT_TARGETS,
    SESSION_TRANSITION_STATUSES,
    SessionExportReadinessV1,
    SessionTransitionResultV1,
    SessionValidationDiagnosticV1,
    SessionValidationResultV1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _players() -> tuple[SessionPlayerV1, ...]:
    return (
        SessionPlayerV1(
            player_id="player-c",
            player_label="Carol",
            seat="rearhand",
        ),
        SessionPlayerV1(
            player_id="player-a",
            player_label="Alice",
            seat="forehand",
        ),
        SessionPlayerV1(
            player_id="player-b",
            player_label=None,
            seat="middlehand",
        ),
    )


def _diagnostic(
    *,
    code: str = "invalid_value",
    path: str = "/value",
    message: str = "The value is invalid.",
    severity: str = "error",
    blocks_command: bool = False,
    blocks_position_export: bool = False,
    blocks_historical_export: bool = False,
) -> SessionValidationDiagnosticV1:
    return SessionValidationDiagnosticV1(
        code=code,
        path=path,
        message=message,
        severity=severity,
        blocks_command=blocks_command,
        blocks_position_export=blocks_position_export,
        blocks_historical_export=blocks_historical_export,
    )


def _readiness(
    target: str,
    status: str = "available",
    reason_codes: tuple[str, ...] = (),
) -> SessionExportReadinessV1:
    return SessionExportReadinessV1(
        target=target,
        status=status,
        reason_codes=reason_codes,
    )


def _validation(
    *,
    revision: int = 0,
    phase: str = "setup",
    structurally_valid: bool = True,
    position_available: bool = True,
) -> SessionValidationResultV1:
    game_complete = phase == "ended"
    diagnostics = []
    position = _readiness("position_analysis")
    if not position_available:
        diagnostics.append(
            _diagnostic(
                code="export_unavailable",
                path="",
                message="Position export is unavailable.",
                severity="info",
                blocks_position_export=True,
            )
        )
        position = _readiness(
            "position_analysis",
            "unavailable",
            ("export_unavailable",),
        )
    historical = _readiness("historical_game")
    if not game_complete:
        diagnostics.append(
            _diagnostic(
                code="missing_required_value",
                path="",
                message="Historical export requires a complete game.",
                severity="info",
                blocks_historical_export=True,
            )
        )
        historical = _readiness(
            "historical_game",
            "unavailable",
            ("missing_required_value",),
        )
    if not structurally_valid:
        invalid = _diagnostic(
            code="invalid_value",
            path="",
            message="The Session structure is invalid.",
            severity="error",
            blocks_position_export=position_available,
            blocks_historical_export=game_complete,
        )
        diagnostics.append(invalid)
        if position_available:
            position = _readiness(
                "position_analysis",
                "unavailable",
                ("invalid_value",),
            )
        if game_complete:
            historical = _readiness(
                "historical_game",
                "unavailable",
                ("invalid_value",),
            )
    return SessionValidationResultV1(
        revision=revision,
        phase=phase,
        structurally_valid=structurally_valid,
        valid_incomplete=structurally_valid and not game_complete,
        game_complete=game_complete,
        position_export=position,
        historical_export=historical,
        diagnostics=diagnostics,
    )


def _state(
    *,
    command_log: tuple[SessionCommandRecordV1, ...] = (),
    initial_capture_mode: str = "live",
    capture_mode: str | None = None,
    local_player_id: str | None = "player-a",
    phase: str = "setup",
) -> SessionStateV1:
    if capture_mode is None:
        capture_mode = initial_capture_mode
    revision = len(command_log)
    return SessionStateV1(
        session_id="session-150",
        initial_capture_mode=initial_capture_mode,
        capture_mode=capture_mode,
        revision=revision,
        phase=phase,
        players=_players(),
        local_player_id=local_player_id,
        command_log=command_log,
        validation=_validation(revision=revision, phase=phase),
    )


def _record(command) -> SessionCommandRecordV1:
    return SessionCommandRecordV1(
        revision=command.expected_revision + 1,
        command=command,
    )


def _all_commands(expected_revision: int = 0) -> tuple[object, ...]:
    return (
        SetSessionGameMetadataCommandV1(
            expected_revision=expected_revision,
            game_id="game-150",
        ),
        RecordSessionDealtCardCommandV1(
            expected_revision=expected_revision,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        ),
        SetSessionDeclarerCommandV1(
            expected_revision=expected_revision,
            declarer_player_id="player-b",
        ),
        SetSessionDeclarationCommandV1(
            expected_revision=expected_revision,
            declaration=GameDeclaration(
                game_type="grand",
                matadors=2,
                bid_value=24,
            ),
        ),
        RecordSessionDiscardCommandV1(
            expected_revision=expected_revision,
            card="D7",
        ),
        RecordSessionPlayCommandV1(
            expected_revision=expected_revision,
            player_id="player-a",
            card="S7",
        ),
        SetSessionGameEventCommandV1(
            expected_revision=expected_revision,
            event={
                "kind": "declarer_card_exposure_continuation",
                "nested": {"cards": ["CA"]},
            },
        ),
        SetSessionGameEndCommandV1(
            expected_revision=expected_revision,
            game_end_reason="normal_completion",
            game_end=None,
        ),
        PromoteSessionToRetrospectiveCommandV1(
            expected_revision=expected_revision,
        ),
        SetSessionPublicHandCommandV1(
            expected_revision=expected_revision,
            source="declared_ouvert",
            player_id="player-b",
            cards=["S10", "SA"],
        ),
    )


def test_session_constants_policies_and_canonical_orders_are_exact() -> None:
    assert SESSION_CONTRACT_VERSION == 1
    assert SESSION_COMMAND_VERSION == 1
    assert SESSION_CAPTURE_MODES == ("live", "retrospective")
    assert SESSION_PHASES == (
        "setup",
        "deal",
        "declaration",
        "skat_and_discard",
        "play",
        "ended",
    )
    assert SESSION_TRANSITION_STATUSES == (
        "applied",
        "rejected",
        "revision_conflict",
    )
    assert SESSION_EXPORT_TARGETS == ("position_analysis", "historical_game")
    assert SESSION_EXPORT_READINESS_STATUSES == ("available", "unavailable")
    assert SESSION_DIAGNOSTIC_SEVERITIES == ("error", "warning", "info")
    assert SESSION_COMMAND_KINDS == (
        "set_game_metadata",
        "record_dealt_card",
        "set_declarer",
        "set_declaration",
        "record_discard",
        "record_play",
        "set_game_event",
        "set_game_end",
        "promote_to_retrospective",
        "set_public_hand",
    )
    assert SESSION_PUBLIC_HAND_SOURCES == ("declared_ouvert",)
    assert SESSION_DEAL_DESTINATIONS == ("player_hand", "skat")
    assert SESSION_STATE_POLICY == "command_log_authoritative"
    assert SESSION_REVISION_POLICY == "linear_append_only"
    assert SESSION_REJECTED_COMMAND_POLICY == "not_recorded"
    assert SESSION_MODE_TRANSITION_POLICY == "live_to_retrospective_only"
    assert SESSION_IDENTIFIER_POLICY == "caller_supplied"
    assert SESSION_TIME_POLICY == "caller_supplied_or_null"


def test_allowed_phase_policy_is_exact_immutable_and_has_no_phase_command() -> None:
    assert isinstance(SESSION_COMMAND_ALLOWED_PHASES, MappingProxyType)
    assert dict(SESSION_COMMAND_ALLOWED_PHASES) == {
        "set_game_metadata": (
            "setup",
            "deal",
            "declaration",
            "skat_and_discard",
            "play",
        ),
        "record_dealt_card": (
            "setup",
            "deal",
            "declaration",
            "skat_and_discard",
        ),
        "set_declarer": ("declaration",),
        "set_declaration": ("declaration",),
        "record_discard": ("skat_and_discard",),
        "record_play": ("play",),
        "set_game_event": ("play",),
        "set_game_end": ("play",),
        "promote_to_retrospective": SESSION_PHASES,
        "set_public_hand": ("play",),
    }
    assert tuple(SESSION_COMMAND_ALLOWED_PHASES) == SESSION_COMMAND_KINDS
    assert all(
        "phase" not in {item.name for item in fields(command)} for command in _all_commands()
    )
    with pytest.raises(TypeError):
        SESSION_COMMAND_ALLOWED_PHASES["record_play"] = ("ended",)


def test_session_player_is_frozen_slotted_keyword_only_and_serializes_null() -> None:
    player = SessionPlayerV1(
        player_id="player-a",
        player_label=None,
        seat="forehand",
    )
    assert not hasattr(player, "__dict__")
    assert [item.name for item in fields(player)] == [
        "player_id",
        "player_label",
        "seat",
    ]
    assert player.to_dict() == {
        "player_id": "player-a",
        "player_label": None,
        "seat": "forehand",
    }
    assert "hand" not in player.to_dict()
    with pytest.raises(FrozenInstanceError):
        player.player_label = "Changed"
    with pytest.raises(TypeError):
        SessionPlayerV1("player-a", None, "forehand")


@pytest.mark.parametrize("value", ("", " padded", "padded ", "me", "left", "right"))
def test_session_player_rejects_invalid_or_relative_stable_ids(value: str) -> None:
    with pytest.raises(ValueError):
        SessionPlayerV1(player_id=value, player_label=None, seat="forehand")


@pytest.mark.parametrize("label", ("", " padded", "padded ", 1))
def test_session_player_rejects_invalid_labels(label: object) -> None:
    with pytest.raises(ValueError):
        SessionPlayerV1(
            player_id="player-a",
            player_label=label,
            seat="forehand",
        )


def test_state_canonicalizes_exactly_three_players_by_historical_seat() -> None:
    state = _state()
    assert tuple(player.player_id for player in state.players) == (
        "player-a",
        "player-b",
        "player-c",
    )
    assert tuple(player.seat for player in state.players) == (
        "forehand",
        "middlehand",
        "rearhand",
    )
    assert not hasattr(state, "__dict__")


def test_state_rejects_duplicate_ids_seats_missing_seat_and_four_players() -> None:
    base = list(_players())
    invalid_sets = (
        (
            base[0],
            base[1],
            SessionPlayerV1(
                player_id="player-a",
                player_label=None,
                seat="middlehand",
            ),
        ),
        (
            base[0],
            base[1],
            SessionPlayerV1(
                player_id="player-d",
                player_label=None,
                seat="forehand",
            ),
        ),
        (base[0], base[1]),
        (
            *base,
            SessionPlayerV1(player_id="player-d", player_label=None, seat="forehand"),
        ),
    )
    for players in invalid_sets:
        with pytest.raises(ValueError):
            SessionStateV1(
                session_id="session-150",
                initial_capture_mode="live",
                capture_mode="live",
                revision=0,
                phase="setup",
                players=players,
                local_player_id="player-a",
                command_log=(),
                validation=_validation(),
            )
    with pytest.raises(ValueError):
        SessionPlayerV1(
            player_id="player-d",
            player_label=None,
            seat="fourth",
        )


def test_live_and_retrospective_state_identity_relationships() -> None:
    live = _state()
    retrospective_without_local = _state(
        initial_capture_mode="retrospective",
        local_player_id=None,
    )
    retrospective_with_local = _state(
        initial_capture_mode="retrospective",
        local_player_id="player-c",
    )
    assert live.capture_mode == "live"
    assert live.revision == 0
    assert live.command_log == ()
    assert retrospective_without_local.capture_mode == "retrospective"
    assert retrospective_without_local.local_player_id is None
    assert retrospective_with_local.local_player_id == "player-c"
    with pytest.raises(ValueError, match="requires local_player_id"):
        _state(local_player_id=None)
    with pytest.raises(ValueError, match="declared Session Player"):
        _state(local_player_id="unknown-player")
    with pytest.raises(ValueError):
        _state(initial_capture_mode="retrospective", capture_mode="live")


@pytest.mark.parametrize("value", ("", " padded", "padded "))
def test_state_rejects_invalid_caller_supplied_session_id(value: str) -> None:
    with pytest.raises(ValueError):
        SessionStateV1(
            session_id=value,
            initial_capture_mode="live",
            capture_mode="live",
            revision=0,
            phase="setup",
            players=_players(),
            local_player_id="player-a",
            command_log=(),
            validation=_validation(),
        )


def test_every_command_has_exact_class_kind_version_and_closed_union_order() -> None:
    commands = _all_commands()
    assert tuple(type(command) for command in commands) == SESSION_COMMAND_TYPES
    assert tuple(command.kind for command in commands) == SESSION_COMMAND_KINDS
    assert all(command.command_version == 1 for command in commands)
    assert all(command.expected_revision == 0 for command in commands)
    for command in commands:
        assert not hasattr(command, "__dict__")
        with pytest.raises(FrozenInstanceError):
            command.expected_revision = 2
        with pytest.raises(TypeError):
            type(command)(expected_revision=0, kind="forged")


@pytest.mark.parametrize("command_type", SESSION_COMMAND_TYPES)
@pytest.mark.parametrize("version", (2, True, 1.0))
def test_every_command_rejects_wrong_command_version(command_type, version: object) -> None:
    source = next(command for command in _all_commands() if type(command) is command_type)
    values = source.to_dict()
    values.pop("kind")
    values["command_version"] = version
    if command_type is SetSessionDeclarationCommandV1:
        values["declaration"] = source.declaration
    with pytest.raises(ValueError, match="command_version"):
        command_type(**values)


@pytest.mark.parametrize("command_type", SESSION_COMMAND_TYPES)
@pytest.mark.parametrize("revision", (-1, True, 1.0, "0"))
def test_every_command_rejects_invalid_expected_revision(command_type, revision: object) -> None:
    source = next(command for command in _all_commands() if type(command) is command_type)
    values = source.to_dict()
    values.pop("kind")
    values["expected_revision"] = revision
    if command_type is SetSessionDeclarationCommandV1:
        values["declaration"] = source.declaration
    with pytest.raises(ValueError, match="expected_revision"):
        command_type(**values)


def test_metadata_requires_one_value_and_reuses_rfc3339_validation() -> None:
    command = SetSessionGameMetadataCommandV1(
        expected_revision=0,
        game_id=None,
        played_at="2026-08-07T12:34:56Z",
    )
    assert command.to_dict() == {
        "command_version": 1,
        "kind": "set_game_metadata",
        "expected_revision": 0,
        "game_id": None,
        "played_at": "2026-08-07T12:34:56Z",
    }
    with pytest.raises(ValueError, match="At least one"):
        SetSessionGameMetadataCommandV1(expected_revision=0)
    with pytest.raises(ValueError, match="RFC 3339"):
        SetSessionGameMetadataCommandV1(
            expected_revision=0,
            played_at="2026-08-07",
        )


def test_deal_commands_enforce_destination_player_relationship_and_one_card() -> None:
    hand = RecordSessionDealtCardCommandV1(
        expected_revision=0,
        destination="player_hand",
        player_id="player-a",
        card="CA",
    )
    skat = RecordSessionDealtCardCommandV1(
        expected_revision=0,
        destination="skat",
        player_id=None,
        card="D7",
    )
    assert hand.player_id == "player-a"
    assert skat.player_id is None
    for values in (
        {"destination": "player_hand", "player_id": None, "card": "CA"},
        {"destination": "skat", "player_id": "player-a", "card": "CA"},
        {"destination": "deck", "player_id": None, "card": "CA"},
        {"destination": "skat", "player_id": None, "card": "XX"},
        {"destination": "skat", "player_id": None, "card": ["CA", "D7"]},
    ):
        with pytest.raises(ValueError):
            RecordSessionDealtCardCommandV1(expected_revision=0, **values)


def test_card_commands_validate_existing_card_vocabulary_but_not_cross_command_ownership() -> None:
    first = RecordSessionDiscardCommandV1(expected_revision=0, card="CA")
    second = RecordSessionDiscardCommandV1(expected_revision=0, card="CA")
    play = RecordSessionPlayCommandV1(
        expected_revision=0,
        player_id="player-a",
        card="CA",
    )
    assert first == second
    assert play.card == "CA"
    with pytest.raises(ValueError):
        RecordSessionDiscardCommandV1(expected_revision=0, card="invalid")
    with pytest.raises(ValueError):
        RecordSessionPlayCommandV1(
            expected_revision=0,
            player_id="me",
            card="CA",
        )


@pytest.mark.parametrize(
    "declaration",
    (
        GameDeclaration(game_type="clubs", matadors=3, bid_value=36),
        GameDeclaration(game_type="grand", matadors=2, bid_value=48),
        GameDeclaration(game_type="null", bid_value=23),
        GameDeclaration(game_type="null", hand_game=True, bid_value=35),
        GameDeclaration(game_type="null", ouvert=True, bid_value=46),
        GameDeclaration(game_type="null", hand_game=True, ouvert=True, bid_value=59),
    ),
)
def test_declaration_command_reuses_every_existing_declaration_variant(
    declaration: GameDeclaration,
) -> None:
    command = SetSessionDeclarationCommandV1(
        expected_revision=0,
        declaration=declaration,
    )
    assert command.to_dict()["declaration"]["game_type"] == declaration.game_type
    assert command.declaration == declaration


def test_declaration_command_defensively_snapshots_existing_frozen_value() -> None:
    declaration = GameDeclaration(game_type="grand", matadors=2, bid_value=48)
    command = SetSessionDeclarationCommandV1(
        expected_revision=0,
        declaration=declaration,
    )
    object.__setattr__(declaration, "bid_value", 96)
    assert command.declaration.bid_value == 48
    assert command.to_dict()["declaration"]["bid_value"] == 48


@pytest.mark.parametrize("kind", SESSION_GAME_EVENT_KINDS)
def test_event_commands_accept_only_existing_continuation_kinds(kind: str) -> None:
    source = {"kind": kind, "nested": {"cards": ["CA"], "value": None}}
    command = SetSessionGameEventCommandV1(expected_revision=0, event=source)
    source["nested"]["cards"][0] = "D7"
    assert command.event["nested"]["cards"] == ("CA",)
    first = command.to_dict()
    second = command.to_dict()
    first["event"]["nested"]["cards"][0] = "H7"
    assert second["event"]["nested"]["cards"] == ["CA"]
    with pytest.raises(TypeError):
        command.event["new"] = True


def test_event_command_rejects_unknown_kind_and_non_json_payloads() -> None:
    for event in (
        {"kind": "unknown"},
        {},
        {"kind": SESSION_GAME_EVENT_KINDS[0], "bad": object()},
        {"kind": SESSION_GAME_EVENT_KINDS[0], 1: "bad"},
    ):
        with pytest.raises(ValueError):
            SetSessionGameEventCommandV1(expected_revision=0, event=event)


@pytest.mark.parametrize("reason", SESSION_GAME_END_REASONS[1:])
def test_terminal_game_end_commands_require_immutable_objects(reason: str) -> None:
    source = {"kind": reason, "nested": [1, {"card": "CA"}]}
    command = SetSessionGameEndCommandV1(
        expected_revision=0,
        game_end_reason=reason,
        game_end=source,
    )
    source["nested"][1]["card"] = "D7"
    assert command.to_dict()["game_end"]["nested"][1]["card"] == "CA"
    with pytest.raises(TypeError):
        command.game_end["new"] = True


def test_game_end_reason_object_relationships_are_exact() -> None:
    normal = SetSessionGameEndCommandV1(
        expected_revision=0,
        game_end_reason="normal_completion",
        game_end=None,
    )
    assert normal.to_dict()["game_end"] is None
    with pytest.raises(ValueError):
        SetSessionGameEndCommandV1(
            expected_revision=0,
            game_end_reason="normal_completion",
            game_end={},
        )
    with pytest.raises(ValueError):
        SetSessionGameEndCommandV1(
            expected_revision=0,
            game_end_reason="declarer_concession",
            game_end=None,
        )
    with pytest.raises(ValueError):
        SetSessionGameEndCommandV1(
            expected_revision=0,
            game_end_reason="unknown",
            game_end={},
        )


def test_command_record_enforces_positive_resulting_and_expected_revision() -> None:
    first_command = SetSessionGameMetadataCommandV1(
        expected_revision=0,
        game_id="game-150",
    )
    record = SessionCommandRecordV1(revision=1, command=first_command)
    assert record.to_dict()["revision"] == 1
    assert record.to_dict()["command"] == first_command.to_dict()
    assert not hasattr(record, "__dict__")
    for revision in (0, -1, True, 1.0):
        with pytest.raises(ValueError):
            SessionCommandRecordV1(revision=revision, command=first_command)
    with pytest.raises(ValueError, match="prior accepted revision"):
        SessionCommandRecordV1(
            revision=2,
            command=first_command,
        )
    with pytest.raises(ValueError, match="SessionCommandV1"):
        SessionCommandRecordV1(revision=1, command=object())


def test_state_enforces_contiguous_authoritative_log_and_matching_revision() -> None:
    first = _record(SetSessionGameMetadataCommandV1(expected_revision=0, game_id="game"))
    second = _record(
        RecordSessionDealtCardCommandV1(
            expected_revision=1,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        )
    )
    state = _state(command_log=(first, second))
    assert state.revision == 2
    assert state.command_log == (first, second)
    with pytest.raises(ValueError, match="contiguous"):
        SessionStateV1(
            session_id="session-150",
            initial_capture_mode="live",
            capture_mode="live",
            revision=2,
            phase="setup",
            players=_players(),
            local_player_id="player-a",
            command_log=(first, first),
            validation=_validation(revision=2),
        )
    with pytest.raises(ValueError, match="accepted command_log length"):
        SessionStateV1(
            session_id="session-150",
            initial_capture_mode="live",
            capture_mode="live",
            revision=1,
            phase="setup",
            players=_players(),
            local_player_id="player-a",
            command_log=(),
            validation=_validation(revision=1),
        )


def test_state_validation_revision_and_phase_must_match() -> None:
    for validation in (
        _validation(revision=1),
        _validation(phase="deal"),
    ):
        with pytest.raises(ValueError, match="validation"):
            SessionStateV1(
                session_id="session-150",
                initial_capture_mode="live",
                capture_mode="live",
                revision=0,
                phase="setup",
                players=_players(),
                local_player_id="player-a",
                command_log=(),
                validation=validation,
            )


def test_live_hand_restriction_changes_only_after_explicit_promotion() -> None:
    local = _record(
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        )
    )
    promotion = _record(PromoteSessionToRetrospectiveCommandV1(expected_revision=1))
    opponent = _record(
        RecordSessionDealtCardCommandV1(
            expected_revision=2,
            destination="player_hand",
            player_id="player-b",
            card="D7",
        )
    )
    assert _state(command_log=(local,)).capture_mode == "live"
    promoted = _state(
        command_log=(local, promotion, opponent),
        capture_mode="retrospective",
    )
    assert promoted.capture_mode == "retrospective"
    assert promoted.local_player_id == "player-a"
    assert len(promoted.command_log) == 3
    early_opponent = _record(
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="player-b",
            card="D7",
        )
    )
    with pytest.raises(ValueError, match="only the local"):
        _state(command_log=(early_opponent,))


def test_initial_retrospective_allows_every_hand_and_forbids_promotion() -> None:
    records = tuple(
        _record(
            RecordSessionDealtCardCommandV1(
                expected_revision=index,
                destination="player_hand",
                player_id=player_id,
                card=card,
            )
        )
        for index, (player_id, card) in enumerate(
            (("player-a", "CA"), ("player-b", "D7"), ("player-c", "H7"))
        )
    )
    state = _state(
        command_log=records,
        initial_capture_mode="retrospective",
        local_player_id=None,
    )
    assert state.capture_mode == "retrospective"
    promotion = _record(PromoteSessionToRetrospectiveCommandV1(expected_revision=0))
    with pytest.raises(ValueError, match="cannot contain a promotion"):
        _state(
            command_log=(promotion,),
            initial_capture_mode="retrospective",
            local_player_id=None,
        )


def test_state_rejects_duplicate_promotion_and_mode_history_mismatch() -> None:
    first = _record(PromoteSessionToRetrospectiveCommandV1(expected_revision=0))
    second = _record(PromoteSessionToRetrospectiveCommandV1(expected_revision=1))
    with pytest.raises(ValueError, match="at most one"):
        _state(
            command_log=(first, second),
            capture_mode="retrospective",
        )
    with pytest.raises(ValueError, match="promotion history"):
        _state(command_log=(first,), capture_mode="live")
    with pytest.raises(ValueError, match="promotion history"):
        _state(capture_mode="retrospective")


def test_state_validates_structurally_checkable_player_references() -> None:
    commands = (
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="unknown-player",
            card="CA",
        ),
        SetSessionDeclarerCommandV1(
            expected_revision=0,
            declarer_player_id="unknown-player",
        ),
        RecordSessionPlayCommandV1(
            expected_revision=0,
            player_id="unknown-player",
            card="CA",
        ),
    )
    for command in commands:
        with pytest.raises(ValueError, match="declared Session Player"):
            _state(
                command_log=(_record(command),),
                initial_capture_mode="retrospective",
                local_player_id=None,
            )


def test_diagnostic_registry_and_severities_are_all_constructible() -> None:
    assert SESSION_DIAGNOSTIC_CODES == (
        "missing_required_value",
        "invalid_value",
        "phase_violation",
        "player_reference_violation",
        "card_identity_violation",
        "card_ownership_violation",
        "turn_order_violation",
        "declaration_violation",
        "information_policy_violation",
        "event_sequence_violation",
        "game_end_violation",
        "export_unavailable",
        "revision_conflict",
        "history_revision_violation",
    )
    for code in SESSION_DIAGNOSTIC_CODES:
        assert _diagnostic(code=code).code == code
    for severity in SESSION_DIAGNOSTIC_SEVERITIES:
        assert _diagnostic(severity=severity).severity == severity


def test_diagnostic_enforces_pointer_message_boolean_and_blocking_relationships() -> None:
    assert _diagnostic(path="/a~1b/tilde~0value").path == "/a~1b/tilde~0value"
    for path in ("not-a-pointer", "/bad~2escape"):
        with pytest.raises(ValueError):
            _diagnostic(path=path)
    with pytest.raises(ValueError, match="non-empty"):
        _diagnostic(message="")
    for field_name in (
        "blocks_command",
        "blocks_position_export",
        "blocks_historical_export",
    ):
        values = {field_name: 1}
        with pytest.raises(ValueError, match="boolean"):
            _diagnostic(**values)
    for severity in ("warning", "info"):
        with pytest.raises(ValueError, match="Only error"):
            _diagnostic(severity=severity, blocks_command=True)


def test_validation_result_canonicalizes_diagnostics_and_rejects_duplicates() -> None:
    error = _diagnostic(code="invalid_value", path="/z", message="Z")
    warning = _diagnostic(
        code="export_unavailable",
        path="/a",
        message="A",
        severity="warning",
        blocks_historical_export=True,
    )
    info = _diagnostic(code="phase_violation", path="/a", message="I", severity="info")
    result = SessionValidationResultV1(
        revision=0,
        phase="setup",
        structurally_valid=True,
        valid_incomplete=True,
        game_complete=False,
        position_export=_readiness("position_analysis"),
        historical_export=_readiness(
            "historical_game",
            "unavailable",
            ("export_unavailable",),
        ),
        diagnostics=[info, warning, error],
    )
    assert result.diagnostics == (error, warning, info)
    with pytest.raises(ValueError, match="Duplicate"):
        SessionValidationResultV1(
            revision=0,
            phase="setup",
            structurally_valid=True,
            valid_incomplete=True,
            game_complete=False,
            position_export=_readiness("position_analysis"),
            historical_export=_readiness(
                "historical_game",
                "unavailable",
                ("export_unavailable",),
            ),
            diagnostics=(warning, warning),
        )


@pytest.mark.parametrize("target", SESSION_EXPORT_TARGETS)
def test_export_readiness_available_and_unavailable_are_normal_statuses(target: str) -> None:
    available = _readiness(target)
    unavailable = _readiness(
        target,
        "unavailable",
        ("export_unavailable", "missing_required_value"),
    )
    assert available.reason_codes == ()
    assert unavailable.reason_codes == (
        "missing_required_value",
        "export_unavailable",
    )


def test_export_readiness_enforces_status_reason_relationships() -> None:
    with pytest.raises(ValueError, match="requires no"):
        _readiness("position_analysis", "available", ("export_unavailable",))
    with pytest.raises(ValueError, match="requires reason"):
        _readiness("historical_game", "unavailable", ())
    with pytest.raises(ValueError, match="duplicates"):
        _readiness(
            "historical_game",
            "unavailable",
            ("export_unavailable", "export_unavailable"),
        )


def test_validation_result_represents_incomplete_position_ready_and_ended_history_ready() -> None:
    incomplete = _validation()
    complete = _validation(phase="ended")
    assert incomplete.structurally_valid is True
    assert incomplete.valid_incomplete is True
    assert incomplete.game_complete is False
    assert incomplete.position_export.status == "available"
    assert incomplete.historical_export.status == "unavailable"
    assert complete.valid_incomplete is False
    assert complete.game_complete is True
    assert complete.historical_export.status == "available"


def test_validation_result_enforces_boolean_ended_and_invalid_export_relationships() -> None:
    base = _validation().to_dict()
    for field_name in ("structurally_valid", "valid_incomplete", "game_complete"):
        values = {**base, field_name: 1}
        values["position_export"] = _readiness("position_analysis")
        values["historical_export"] = _readiness(
            "historical_game",
            "unavailable",
            ("missing_required_value",),
        )
        values["diagnostics"] = _validation().diagnostics
        with pytest.raises(ValueError):
            SessionValidationResultV1(**values)
    with pytest.raises(ValueError, match="exactly"):
        SessionValidationResultV1(
            revision=0,
            phase="ended",
            structurally_valid=True,
            valid_incomplete=True,
            game_complete=False,
            position_export=_readiness("position_analysis"),
            historical_export=_readiness(
                "historical_game", "unavailable", ("missing_required_value",)
            ),
            diagnostics=(
                _diagnostic(
                    code="missing_required_value",
                    blocks_historical_export=True,
                ),
            ),
        )
    invalid = _validation(structurally_valid=False)
    assert invalid.position_export.status == "unavailable"
    assert invalid.historical_export.status == "unavailable"


def test_validation_readiness_must_exactly_reconcile_with_export_blockers() -> None:
    blocker = _diagnostic(
        code="export_unavailable",
        blocks_position_export=True,
        blocks_historical_export=True,
    )
    with pytest.raises(ValueError, match="position_export"):
        SessionValidationResultV1(
            revision=0,
            phase="setup",
            structurally_valid=True,
            valid_incomplete=True,
            game_complete=False,
            position_export=_readiness("position_analysis"),
            historical_export=_readiness("historical_game", "unavailable", ("export_unavailable",)),
            diagnostics=(blocker,),
        )
    with pytest.raises(ValueError, match="historical_export"):
        SessionValidationResultV1(
            revision=0,
            phase="setup",
            structurally_valid=True,
            valid_incomplete=True,
            game_complete=False,
            position_export=_readiness("position_analysis"),
            historical_export=_readiness("historical_game", "unavailable", ("export_unavailable",)),
            diagnostics=(),
        )


def test_applied_transition_requires_increment_final_record_and_no_blocker() -> None:
    command = SetSessionGameMetadataCommandV1(expected_revision=0, game_id="game")
    state = _state(command_log=(_record(command),))
    result = SessionTransitionResultV1(
        status="applied",
        expected_revision=0,
        previous_revision=0,
        current_revision=1,
        command=command,
        state=state,
        diagnostics=(),
    )
    assert result.state.command_log[-1].command == command
    for values in (
        {"expected_revision": 1},
        {"current_revision": 0},
        {"state": _state()},
        {"diagnostics": (_diagnostic(blocks_command=True),)},
    ):
        kwargs = {
            "status": "applied",
            "expected_revision": 0,
            "previous_revision": 0,
            "current_revision": 1,
            "command": command,
            "state": state,
            "diagnostics": (),
            **values,
        }
        with pytest.raises(ValueError):
            SessionTransitionResultV1(**kwargs)


def test_rejected_transition_keeps_revision_and_requires_blocker_without_log_record() -> None:
    command = SetSessionGameMetadataCommandV1(expected_revision=0, game_id="game")
    state = _state()
    blocker = _diagnostic(code="phase_violation", blocks_command=True)
    result = SessionTransitionResultV1(
        status="rejected",
        expected_revision=0,
        previous_revision=0,
        current_revision=0,
        command=command,
        state=state,
        diagnostics=(blocker,),
    )
    assert result.current_revision == result.previous_revision == state.revision
    assert state.command_log == ()
    with pytest.raises(ValueError, match="blocking"):
        SessionTransitionResultV1(
            status="rejected",
            expected_revision=0,
            previous_revision=0,
            current_revision=0,
            command=command,
            state=state,
            diagnostics=(),
        )


def test_revision_conflict_keeps_state_and_accepts_stale_retry_not_new_log_record() -> None:
    accepted = SetSessionGameMetadataCommandV1(expected_revision=0, game_id="game")
    state = _state(command_log=(_record(accepted),))
    conflict = _diagnostic(code="revision_conflict", blocks_command=True)
    result = SessionTransitionResultV1(
        status="revision_conflict",
        expected_revision=0,
        previous_revision=1,
        current_revision=1,
        command=accepted,
        state=state,
        diagnostics=(conflict,),
    )
    assert result.state is state
    assert len(result.state.command_log) == 1
    with pytest.raises(ValueError, match="stale or future"):
        SessionTransitionResultV1(
            status="revision_conflict",
            expected_revision=1,
            previous_revision=1,
            current_revision=1,
            command=PromoteSessionToRetrospectiveCommandV1(expected_revision=1),
            state=state,
            diagnostics=(conflict,),
        )
    with pytest.raises(ValueError, match="exactly one"):
        SessionTransitionResultV1(
            status="revision_conflict",
            expected_revision=0,
            previous_revision=1,
            current_revision=1,
            command=accepted,
            state=state,
            diagnostics=(),
        )


def test_transition_expected_revision_must_equal_command_header() -> None:
    command = SetSessionGameMetadataCommandV1(expected_revision=1, game_id="game")
    with pytest.raises(ValueError, match="command.expected_revision"):
        SessionTransitionResultV1(
            status="revision_conflict",
            expected_revision=0,
            previous_revision=1,
            current_revision=1,
            command=command,
            state=_state(
                command_log=(
                    _record(
                        SetSessionGameMetadataCommandV1(
                            expected_revision=0,
                            game_id="accepted",
                        )
                    ),
                )
            ),
            diagnostics=(_diagnostic(code="revision_conflict", blocks_command=True),),
        )


def test_serialization_is_deterministic_explicit_and_returns_fresh_mutable_copies() -> None:
    command = SetSessionGameEventCommandV1(
        expected_revision=0,
        event={"z": None, "kind": SESSION_GAME_EVENT_KINDS[0], "a": ["CA"]},
    )
    state = _state(command_log=(_record(command),))
    transition = SessionTransitionResultV1(
        status="applied",
        expected_revision=0,
        previous_revision=0,
        current_revision=1,
        command=command,
        state=state,
        diagnostics=(),
    )
    first = transition.to_dict()
    second = transition.to_dict()
    assert first == second
    assert list(first) == [
        "session_contract_version",
        "status",
        "expected_revision",
        "previous_revision",
        "current_revision",
        "command",
        "state",
        "diagnostics",
    ]
    assert list(first["command"]["event"]) == ["a", "kind", "z"]
    assert first["command"]["event"]["z"] is None
    first["command"]["event"]["a"][0] = "D7"
    first["state"]["players"][0]["player_label"] = "Changed"
    assert second["command"]["event"]["a"] == ["CA"]
    assert second["state"]["players"][0]["player_label"] == "Alice"
    json.dumps(second)


def test_serialization_for_every_command_has_no_generated_protocol_data() -> None:
    forbidden = {
        "command_id",
        "created_at",
        "timestamp",
        "class_name",
        "filesystem_path",
        "source_path",
    }
    for command in _all_commands():
        document = command.to_dict()
        assert document["kind"] == command.kind
        assert forbidden.isdisjoint(document)
        assert document == command.to_dict()
        json.dumps(document)


def test_session_state_serialization_has_exact_fields_and_immutable_nested_values() -> None:
    source_players = list(_players())
    source_log = []
    state = SessionStateV1(
        session_id="session-150",
        initial_capture_mode="live",
        capture_mode="live",
        revision=0,
        phase="setup",
        players=source_players,
        local_player_id="player-a",
        command_log=source_log,
        validation=_validation(),
    )
    source_players.clear()
    source_log.append("changed")
    assert len(state.players) == 3
    assert state.command_log == ()
    assert list(state.to_dict()) == [
        "session_contract_version",
        "session_id",
        "initial_capture_mode",
        "capture_mode",
        "revision",
        "phase",
        "players",
        "local_player_id",
        "command_log",
        "validation",
    ]
    with pytest.raises(FrozenInstanceError):
        state.phase = "deal"


def test_no_unversioned_transition_export_parser_or_persistence_surface_exists() -> None:
    import skat_ai.session_commands as commands
    import skat_ai.session_contracts as contracts
    import skat_ai.session_incremental_validation as incremental_validation
    import skat_ai.session_projection as projection
    import skat_ai.session_transitions as transitions
    import skat_ai.session_validation as validation

    for module in (
        commands,
        contracts,
        incremental_validation,
        projection,
        transitions,
        validation,
    ):
        assert not hasattr(module, "apply_session_command")
        assert not hasattr(module, "export_session")
        assert not hasattr(module, "parse_session")
        assert not hasattr(module, "save_session")


def test_existing_engine_contracts_replay_public_api_cli_and_counts_are_unchanged() -> None:
    assert [item.name for item in fields(GameState)] == [
        "game_type",
        "player_role",
        "hand",
        "current_trick",
        "played_cards",
        "skat",
        "player_position",
        "declarer_player",
        "trick_leader",
        "completed_tricks",
        "declarer_points",
        "defender_points",
        "next_player",
    ]
    assert [item.name for item in fields(HistoricalGameRecord)] == [
        "schema_version",
        "game_id",
        "played_at",
        "players",
        "skat",
        "declarer_player_id",
        "declaration",
        "discarded_cards",
        "game_end_reason",
        "game_end",
        "game_events",
        "tricks",
    ]
    historical = json.loads(
        (PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json").read_text(
            encoding="utf-8"
        )
    )["historical_game_input"]
    assert build_historical_game_summary_from_input(historical)["status"] == "complete"

    assert skat_ai.__all__ == ("api", "errors", "__version__")
    assert tuple(workflow.value for workflow in WorkflowV1) == (
        "position_analysis",
        "historical_game",
        "training_dataset",
        "training_dataset_preparation",
        "opponent_statistics",
        "fixed_three_player_historical_list",
        "fixed_three_player_historical_list_comparison",
    )
    assert all("Session" not in name for name in api_v1.__all__)
    assert all(
        "session" not in option
        for action in cli.build_argument_parser()._actions
        for option in action.option_strings
    )
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 63
    packaged_schema_directory = PROJECT_ROOT / "src" / "skat_ai" / "schema_resources"
    assert len(tuple(packaged_schema_directory.glob("*.schema.json"))) == 63
    assert len(SCENARIOS) == 85
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == "0.14.0"
    assert skat_ai.__version__ == "0.14.0"
