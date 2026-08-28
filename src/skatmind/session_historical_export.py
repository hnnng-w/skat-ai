from __future__ import annotations

from typing import Any

from skatmind.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skatmind.errors import SkatMindInvariantError
from skatmind.game_declaration import build_serializable_game_declaration
from skatmind.historical_game import (
    HISTORICAL_GAME_SCHEMA_VERSION,
    build_historical_game_record,
    build_serializable_historical_record,
)
from skatmind.historical_game_end import build_serializable_historical_game_end
from skatmind.historical_game_event import build_serializable_historical_game_event
from skatmind.session_contracts import SessionStateV1
from skatmind.session_export_contracts import SessionRequestExportV1
from skatmind.session_projection import SessionProjectionV1
from skatmind.session_transitions import replay_session_state_v1

_HISTORICAL_TARGET = "historical_game"


def _raise_export_invariant(
    message: str,
    *,
    path: str,
    cause: Exception | None = None,
) -> None:
    error = SkatMindInvariantError(message, path=path)
    if cause is None:
        raise error
    raise error from cause


def _build_serializable_players(projection: SessionProjectionV1) -> list[dict[str, Any]]:
    players = []
    for player in projection.players:
        initial_hand = projection.initial_hand_for(player.player_id)
        if initial_hand is None:
            raise ValueError(
                f"Historical-ready Session Player '{player.player_id}' has no initial hand."
            )
        serialized_player: dict[str, Any] = {
            "player_id": player.player_id,
            "seat": player.seat,
            "initial_hand": list(initial_hand),
        }
        if player.player_label is not None:
            serialized_player["player_label"] = player.player_label
        players.append(serialized_player)
    return players


def _build_serializable_declaration(projection: SessionProjectionV1) -> dict[str, Any]:
    if projection.declaration is None:
        raise ValueError("A Historical-ready Session has no Declaration.")
    declaration = build_serializable_game_declaration(projection.declaration)
    if projection.declaration.game_type == "null":
        for excluded_field in (
            "matadors",
            "schneider_announced",
            "schwarz_announced",
        ):
            declaration.pop(excluded_field)
    elif projection.declaration.matadors is None:
        declaration.pop("matadors")
    return declaration


def _build_serializable_trick(
    *,
    trick_number: int,
    leader_player_id: str,
    plays: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    return {
        "trick_number": trick_number,
        "leader_player_id": leader_player_id,
        "plays": [
            {"player_id": player_id, "card": card} for player_id, card in plays
        ],
    }


def _build_serializable_tricks(projection: SessionProjectionV1) -> list[dict[str, Any]]:
    tricks = [
        _build_serializable_trick(
            trick_number=trick.trick_number,
            leader_player_id=trick.leader_player_id,
            plays=trick.plays,
        )
        for trick in projection.completed_tricks
    ]
    if projection.incomplete_trick is not None:
        tricks.append(
            _build_serializable_trick(
                trick_number=projection.incomplete_trick.trick_number,
                leader_player_id=projection.incomplete_trick.leader_player_id,
                plays=projection.incomplete_trick.plays,
            )
        )
    flattened_plays = tuple(
        (play["player_id"], play["card"])
        for trick in tricks
        for play in trick["plays"]
    )
    if flattened_plays != projection.plays:
        _raise_export_invariant(
            "Session Projection Tricks do not preserve the accepted Play sequence.",
            path="/tricks",
        )
    return tricks


def _build_provisional_historical_document(
    projection: SessionProjectionV1,
) -> dict[str, Any]:
    if projection.game_id is None:
        raise ValueError("A Historical-ready Session has no Game ID.")
    if projection.declarer_player_id is None:
        raise ValueError("A Historical-ready Session has no Declarer.")
    if projection.game_end_reason is None:
        raise ValueError("A Historical-ready Session has no Game End reason.")

    document: dict[str, Any] = {
        "schema_version": HISTORICAL_GAME_SCHEMA_VERSION,
        "game_id": projection.game_id,
        "players": _build_serializable_players(projection),
        "skat": list(projection.known_skat),
        "declarer_player_id": projection.declarer_player_id,
        "declaration": _build_serializable_declaration(projection),
        "discarded_cards": list(projection.discarded_cards),
        "game_end_reason": projection.game_end_reason,
        "tricks": _build_serializable_tricks(projection),
    }
    if projection.played_at is not None:
        document["played_at"] = projection.played_at
    if projection.game_end is not None:
        document["game_end"] = build_serializable_historical_game_end(
            projection.game_end
        )
    if projection.continuation_event is not None:
        document["game_events"] = [
            build_serializable_historical_game_event(projection.continuation_event)
        ]
    return document


def export_session_historical_game_request_v1(
    state: SessionStateV1,
) -> SessionRequestExportV1:
    """Exports one Historical-ready Session without executing the workflow."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")

    projection = replay_session_state_v1(state)
    readiness = state.validation.historical_export
    blockers = tuple(
        diagnostic
        for diagnostic in state.validation.diagnostics
        if diagnostic.blocks_historical_export
    )
    if readiness.status == "unavailable":
        return SessionRequestExportV1(
            session_id=state.session_id,
            source_revision=state.revision,
            target=_HISTORICAL_TARGET,
            status="unavailable",
            request=None,
            diagnostics=blockers,
        )

    if (
        projection.capture_mode != "retrospective"
        or projection.phase != "ended"
        or blockers
    ):
        _raise_export_invariant(
            "Session Historical readiness disagrees with the replayed Projection.",
            path="/validation/historical_export",
        )

    try:
        provisional_document = _build_provisional_historical_document(projection)
        provisional_record = build_historical_game_record(provisional_document)
        canonical_document = build_serializable_historical_record(provisional_record)
        canonical_record = build_historical_game_record(canonical_document)
        if canonical_record != provisional_record:
            _raise_export_invariant(
                "Canonical Historical rebuild changed the validated record.",
                path="/historical_game_input",
            )
        request = RequestDocumentV1(
            workflow=WorkflowV1.HISTORICAL_GAME,
            document={"historical_game_input": canonical_document},
        )
        return SessionRequestExportV1(
            session_id=state.session_id,
            source_revision=state.revision,
            target=_HISTORICAL_TARGET,
            status="available",
            request=request,
            diagnostics=(),
        )
    except SkatMindInvariantError:
        raise
    except Exception as error:
        _raise_export_invariant(
            "Historical-ready Session could not produce a canonical Request.",
            path="/historical_game_input",
            cause=error,
        )
