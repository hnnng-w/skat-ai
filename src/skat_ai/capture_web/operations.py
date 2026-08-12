from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_capture_application import (
    append_match_capture_plays_v1,
    clear_match_capture_position_v1,
    mark_match_capture_passed_deal_v1,
    remove_match_capture_commentary_v1,
    remove_match_capture_response_link_v1,
    set_match_capture_commentary_v1,
    set_match_capture_declaration_v1,
    set_match_capture_discarded_cards_v1,
    set_match_capture_game_timecode_v1,
    set_match_capture_original_skat_v1,
    set_match_capture_perspective_initial_hand_v1,
    set_match_capture_response_link_v1,
    start_match_capture_game_v1,
    truncate_match_capture_plays_v1,
)
from skat_ai.match_capture_application_contracts import (
    MatchCaptureApplicationResultV1,
    MatchCaptureCardEntryV1,
)
from skat_ai.match_capture_contracts import MatchCaptureDefinitionV1
from skat_ai.match_player_snapshot import MatchParticipantV1
from skat_ai.match_source_metadata import MatchSourceMetadataV1, MediaTimecodeV1
from skat_ai.match_tournament_format import EUROSKAT_36_STANDARD_V1_FORMAT
from skat_ai.match_workspace_contracts import (
    MatchWorkspaceV1,
    create_match_workspace_v1,
)
from skat_ai.match_workspace_operations import (
    MatchWorkspaceChangeResultV1,
    replace_match_workspace_definition_v1,
)

from .context import MatchCaptureWebContextV1
from .contracts import MATCH_CAPTURE_WEB_OPERATIONS, MatchCaptureWebResultV1
from .state import build_match_capture_web_state_v1
from .timecodes import build_presentation_timecode_v1

_CARD_SPLIT_PATTERN = re.compile(r"[\s,]+")


def _text(
    values: Mapping[str, object],
    name: str,
    *,
    required: bool = False,
) -> str:
    value = values.get(name, "")
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text.")
    if required and not value:
        raise ValueError(f"{name} is required.")
    return value


def _optional_text(values: Mapping[str, object], name: str) -> str | None:
    value = _text(values, name)
    return value or None


def _integer(
    values: Mapping[str, object],
    name: str,
    *,
    minimum: int | None = None,
) -> int:
    value = values.get(name)
    if type(value) is int:
        result = value
    elif isinstance(value, str):
        try:
            result = int(value)
        except ValueError as error:
            raise ValueError(f"{name} must be an integer.") from error
    else:
        raise ValueError(f"{name} must be an integer.")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return result


def _optional_integer(
    values: Mapping[str, object],
    name: str,
    *,
    minimum: int | None = None,
) -> int | None:
    if values.get(name, "") in {"", None}:
        return None
    return _integer(values, name, minimum=minimum)


def _checked(values: Mapping[str, object], name: str) -> bool:
    value = values.get(name, False)
    if type(value) is bool:
        return value
    if isinstance(value, str):
        normalized = value.lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"", "0", "false", "off", "no"}:
            return False
    raise ValueError(f"{name} must be a boolean.")


def _cards(values: Mapping[str, object], name: str) -> tuple[str, ...]:
    value = values.get(name, "")
    if isinstance(value, (list, tuple)):
        return tuple(str(card) for card in value)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be Card-code text or an array.")
    return tuple(part for part in _CARD_SPLIT_PATTERN.split(value) if part)


def _point_timecode(values: Mapping[str, object], name: str) -> MediaTimecodeV1 | None:
    return build_presentation_timecode_v1(_text(values, name))


def _range_timecode(
    values: Mapping[str, object],
    start_name: str,
    end_name: str,
) -> MediaTimecodeV1 | None:
    return build_presentation_timecode_v1(
        _text(values, start_name),
        _text(values, end_name),
    )


def _creation_definition(values: Mapping[str, object]) -> MatchCaptureDefinitionV1:
    source_kind = _text(values, "source_kind", required=True)
    source = MatchSourceMetadataV1(
        source_kind=source_kind,
        source_url=(
            None
            if source_kind == "manual_observation"
            else _optional_text(values, "source_url")
        ),
        source_title=_text(values, "source_title", required=True),
        source_channel_name=(
            None
            if source_kind == "manual_observation"
            else _optional_text(values, "source_channel_name")
        ),
        match_timecode=_range_timecode(
            values,
            "match_timecode_start",
            "match_timecode_end",
        ),
    )
    participants = tuple(
        MatchParticipantV1(
            player_id=_text(values, f"player_{index}_id", required=True),
            player_label=_optional_text(values, f"player_{index}_label"),
            platform_player_id=_optional_text(
                values,
                f"player_{index}_platform_id",
            ),
            table_place=f"place_{index}",
            statistics_snapshot=None,
        )
        for index in range(1, 4)
    )
    return MatchCaptureDefinitionV1(
        match_id=_text(values, "match_id", required=True),
        title=_text(values, "title", required=True),
        game_platform=_text(values, "game_platform", required=True),
        external_match_id=_optional_text(values, "external_match_id"),
        played_at=_optional_text(values, "played_at"),
        tournament_format=EUROSKAT_36_STANDARD_V1_FORMAT,
        source=source,
        participants=participants,
        perspective_player_id=_text(
            values,
            "perspective_player_id",
            required=True,
        ),
    )


def _replacement_definition(
    workspace: MatchWorkspaceV1,
    values: Mapping[str, object],
) -> MatchCaptureDefinitionV1:
    source = workspace.match_definition
    source_kind = _text(values, "source_kind", required=True)
    return MatchCaptureDefinitionV1(
        match_id=source.match_id,
        title=_text(values, "title", required=True),
        game_platform=_text(values, "game_platform", required=True),
        external_match_id=_optional_text(values, "external_match_id"),
        played_at=_optional_text(values, "played_at"),
        tournament_format=source.tournament_format,
        source=MatchSourceMetadataV1(
            source_kind=source_kind,
            source_url=(
                None
                if source_kind == "manual_observation"
                else _optional_text(values, "source_url")
            ),
            source_title=_text(values, "source_title", required=True),
            source_channel_name=(
                None
                if source_kind == "manual_observation"
                else _optional_text(values, "source_channel_name")
            ),
            match_timecode=_range_timecode(
                values,
                "match_timecode_start",
                "match_timecode_end",
            ),
        ),
        participants=tuple(
            MatchParticipantV1(
                player_id=participant.player_id,
                player_label=_optional_text(values, f"player_{index}_label"),
                platform_player_id=_optional_text(
                    values,
                    f"player_{index}_platform_id",
                ),
                table_place=participant.table_place,
                statistics_snapshot=participant.statistics_snapshot,
            )
            for index, participant in enumerate(source.participants, start=1)
        ),
        perspective_player_id=source.perspective_player_id,
    )


def _app_result(
    workspace: MatchWorkspaceV1,
    operation: str,
    values: Mapping[str, object],
    *,
    position: int,
    expected_revision: int,
) -> MatchCaptureApplicationResultV1:
    if operation == "start_game":
        return start_match_capture_game_v1(
            workspace,
            match_position=position,
            game_id=_optional_text(values, "game_id"),
            game_timecode=_range_timecode(
                values,
                "game_timecode_start",
                "game_timecode_end",
            ),
            expected_revision=expected_revision,
        )
    if operation == "set_game_timecode":
        return set_match_capture_game_timecode_v1(
            workspace,
            match_position=position,
            game_timecode=_range_timecode(
                values,
                "game_timecode_start",
                "game_timecode_end",
            ),
            expected_revision=expected_revision,
        )
    if operation == "set_perspective_hand":
        mode = _text(values, "card_evidence_mode", required=True)
        cards = None if mode == "unknown" else _cards(values, "cards")
        return set_match_capture_perspective_initial_hand_v1(
            workspace,
            match_position=position,
            cards=cards,
            expected_revision=expected_revision,
        )
    if operation == "set_declaration":
        declarer = _optional_text(values, "declarer_player_id")
        game_type = _optional_text(values, "game_type")
        declaration = (
            None
            if declarer is None and game_type is None
            else GameDeclaration(
                game_type=_text(values, "game_type", required=True),
                hand_game=_checked(values, "hand_game"),
                ouvert=_checked(values, "ouvert"),
                schneider_announced=_checked(values, "schneider_announced"),
                schwarz_announced=_checked(values, "schwarz_announced"),
                matadors=_optional_integer(values, "matadors", minimum=1),
                bid_value=_optional_integer(values, "bid_value", minimum=1),
            )
        )
        return set_match_capture_declaration_v1(
            workspace,
            match_position=position,
            declarer_player_id=declarer,
            declaration=declaration,
            expected_revision=expected_revision,
        )
    if operation == "set_original_skat":
        mode = _text(values, "card_evidence_mode", required=True)
        return set_match_capture_original_skat_v1(
            workspace,
            match_position=position,
            cards=None if mode == "unknown" else _cards(values, "cards"),
            expected_revision=expected_revision,
        )
    if operation == "set_discarded_cards":
        mode = _text(values, "card_evidence_mode", required=True)
        cards = (
            None
            if mode == "unknown"
            else ()
            if mode == "known_empty"
            else _cards(values, "cards")
        )
        return set_match_capture_discarded_cards_v1(
            workspace,
            match_position=position,
            cards=cards,
            expected_revision=expected_revision,
        )
    if operation == "append_plays":
        cards = _cards(values, "cards")
        decision_timecode = _point_timecode(values, "decision_timecode")
        if decision_timecode is not None and len(cards) != 1:
            raise ValueError("Decision timecode is supported only for one-Card entry.")
        return append_match_capture_plays_v1(
            workspace,
            match_position=position,
            entries=tuple(
                MatchCaptureCardEntryV1(
                    card=card,
                    decision_timecode=decision_timecode,
                )
                for card in cards
            ),
            expected_revision=expected_revision,
        )
    if operation == "truncate_plays":
        return truncate_match_capture_plays_v1(
            workspace,
            match_position=position,
            target_play_count=_integer(values, "target_play_count", minimum=0),
            expected_revision=expected_revision,
        )
    if operation == "set_commentary":
        return set_match_capture_commentary_v1(
            workspace,
            match_position=position,
            decision_index=_integer(values, "decision_index", minimum=1),
            commentator_player_id=_optional_text(
                values,
                "commentator_player_id",
            ),
            commentator_name=_optional_text(values, "commentator_name"),
            text=_text(values, "text", required=True),
            commentary_timecode=_point_timecode(values, "commentary_timecode"),
            expected_revision=expected_revision,
            commentary_id=_optional_text(values, "commentary_id"),
        )
    if operation == "remove_commentary":
        return remove_match_capture_commentary_v1(
            workspace,
            match_position=position,
            commentary_id=_text(values, "commentary_id", required=True),
            expected_revision=expected_revision,
        )
    if operation == "set_response_link":
        return set_match_capture_response_link_v1(
            workspace,
            match_position=position,
            commentary_id=_text(values, "commentary_id", required=True),
            response_decision_index=_integer(
                values,
                "response_decision_index",
                minimum=1,
            ),
            expected_revision=expected_revision,
            link_id=_optional_text(values, "link_id"),
        )
    if operation == "remove_response_link":
        return remove_match_capture_response_link_v1(
            workspace,
            match_position=position,
            link_id=_text(values, "link_id", required=True),
            expected_revision=expected_revision,
        )
    if operation == "mark_passed_deal":
        if (
            workspace.slots[position - 1].observed_game is not None
            and not _checked(values, "confirm_replace")
        ):
            raise ValueError(
                "Replacing an observed Game with a Passed Deal requires confirmation."
            )
        return mark_match_capture_passed_deal_v1(
            workspace,
            match_position=position,
            game_timecode=_range_timecode(
                values,
                "game_timecode_start",
                "game_timecode_end",
            ),
            expected_revision=expected_revision,
        )
    if operation == "clear_position":
        if (
            workspace.slots[position - 1].slot_kind != "empty"
            and not _checked(values, "confirm_clear")
        ):
            raise ValueError("Clearing an occupied position requires confirmation.")
        return clear_match_capture_position_v1(
            workspace,
            match_position=position,
            expected_revision=expected_revision,
        )
    raise ValueError(f"Unsupported Match Capture Web operation: {operation}")


def _state(
    context: MatchCaptureWebContextV1,
    selected_position: int,
) -> dict[str, Any]:
    return build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
        selected_position=selected_position,
    )


def _result(
    context: MatchCaptureWebContextV1,
    *,
    operation: str,
    status: str,
    http_status: int,
    message: str,
    selected_position: int,
    removed_commentary_ids: tuple[str, ...] = (),
    removed_response_link_ids: tuple[str, ...] = (),
) -> MatchCaptureWebResultV1:
    return MatchCaptureWebResultV1(
        operation=operation,
        status=status,
        http_status=http_status,
        message=message,
        state=_state(context, selected_position),
        removed_commentary_ids=removed_commentary_ids,
        removed_response_link_ids=removed_response_link_ids,
    )


def _persist_change(
    context: MatchCaptureWebContextV1,
    *,
    operation: str,
    status: str,
    workspace: MatchWorkspaceV1,
    selected_position: int,
    removed_commentary_ids: tuple[str, ...] = (),
    removed_response_link_ids: tuple[str, ...] = (),
) -> MatchCaptureWebResultV1:
    if status == "revision_conflict":
        return _result(
            context,
            operation=operation,
            status=status,
            http_status=409,
            message="Workspace revision conflict; no file change occurred.",
            selected_position=selected_position,
        )
    if status == "unchanged":
        return _result(
            context,
            operation=operation,
            status=status,
            http_status=200,
            message="No change; the Workspace file was not written.",
            selected_position=selected_position,
        )
    save_status = context.save_candidate(workspace)
    if save_status == "conflict":
        return _result(
            context,
            operation=operation,
            status="persistence_conflict",
            http_status=409,
            message=(
                "The Workspace file changed outside this server; no local change was "
                "saved. Reload explicitly before continuing."
            ),
            selected_position=selected_position,
        )
    effects = ""
    if removed_commentary_ids:
        effects += " Removed Commentary: " + ", ".join(removed_commentary_ids) + "."
    if removed_response_link_ids:
        effects += " Removed Response Links: " + ", ".join(removed_response_link_ids) + "."
    return _result(
        context,
        operation=operation,
        status="applied",
        http_status=200,
        message=f"Change saved.{effects}",
        selected_position=selected_position,
        removed_commentary_ids=removed_commentary_ids,
        removed_response_link_ids=removed_response_link_ids,
    )


def create_match_capture_workspace_v1(
    context: MatchCaptureWebContextV1,
    values: Mapping[str, object],
) -> MatchCaptureWebResultV1:
    with context.lock:
        if context.workspace is not None:
            return _result(
                context,
                operation="create_workspace",
                status="revision_conflict",
                http_status=409,
                message="A Workspace is already loaded; no file change occurred.",
                selected_position=1,
            )
        workspace = create_match_workspace_v1(_creation_definition(values))
        return _persist_change(
            context,
            operation="create_workspace",
            status="applied",
            workspace=workspace,
            selected_position=1,
        )


def reload_match_capture_workspace_v1(
    context: MatchCaptureWebContextV1,
    *,
    selected_position: int = 1,
) -> MatchCaptureWebResultV1:
    with context.lock:
        context.reload()
        return _result(
            context,
            operation="reload_workspace",
            status="reloaded",
            http_status=200,
            message="Workspace reloaded from disk.",
            selected_position=selected_position,
        )


def apply_match_capture_web_operation_v1(
    context: MatchCaptureWebContextV1,
    values: Mapping[str, object],
) -> MatchCaptureWebResultV1:
    operation = _text(values, "operation", required=True)
    if operation not in MATCH_CAPTURE_WEB_OPERATIONS[2:]:
        raise ValueError("operation must identify one supported Workspace mutation.")
    position = _integer(values, "match_position", minimum=1)
    if position > 36:
        raise ValueError("match_position must be an integer from 1 through 36.")
    expected_revision = _integer(values, "expected_revision", minimum=0)
    with context.lock:
        workspace = context.workspace
        if workspace is None:
            raise ValueError("Create the Workspace before applying Match operations.")
        if expected_revision != workspace.revision:
            return _result(
                context,
                operation=operation,
                status="revision_conflict",
                http_status=409,
                message="Workspace revision conflict; no file change occurred.",
                selected_position=position,
            )
        if operation == "update_match_metadata":
            change: MatchWorkspaceChangeResultV1 | MatchCaptureApplicationResultV1 = (
                replace_match_workspace_definition_v1(
                    workspace,
                    _replacement_definition(workspace, values),
                    expected_revision=expected_revision,
                )
            )
            status = change.status
            candidate = change.workspace
            removed_commentary_ids: tuple[str, ...] = ()
            removed_response_link_ids: tuple[str, ...] = ()
        else:
            capture_result = _app_result(
                workspace,
                operation,
                values,
                position=position,
                expected_revision=expected_revision,
            )
            status = capture_result.status
            candidate = capture_result.workspace_change.workspace
            removed_commentary_ids = capture_result.removed_commentary_ids
            removed_response_link_ids = capture_result.removed_response_link_ids
        return _persist_change(
            context,
            operation=operation,
            status=status,
            workspace=candidate,
            selected_position=position,
            removed_commentary_ids=removed_commentary_ids,
            removed_response_link_ids=removed_response_link_ids,
        )
