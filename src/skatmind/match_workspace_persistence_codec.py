from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.game_declaration import GameDeclaration, build_serializable_game_declaration
from skatmind.match_capture_contracts import MatchCaptureDefinitionV1
from skatmind.match_player_snapshot import (
    MatchParticipantV1,
    MatchPlayerStatisticsSnapshotV1,
)
from skatmind.match_source_metadata import MatchSourceMetadataV1, MediaTimecodeV1
from skatmind.match_tournament_format import (
    MatchTournamentFormatV1,
    get_match_tournament_format_v1,
)
from skatmind.match_workspace_contracts import (
    MATCH_PASSED_DEAL_VERSION,
    MATCH_WORKSPACE_CONTRACT_VERSION,
    MATCH_WORKSPACE_SLOT_VERSION,
    MatchPassedDealV1,
    MatchWorkspaceSlotV1,
    MatchWorkspaceV1,
    _build_match_workspace_v1,
    validate_match_workspace_v1,
)
from skatmind.match_workspace_persistence_contracts import (
    LEGACY_MATCH_WORKSPACE_DOCUMENT_KIND,
    MATCH_WORKSPACE_DOCUMENT_KIND,
    MATCH_WORKSPACE_PERSISTENCE_VERSION,
    MatchWorkspacePersistenceDocumentV1,
    MatchWorkspaceResumeResultV1,
    _build_verified_match_workspace_persistence_document_v1,
    _canonical_json_bytes,
)
from skatmind.match_workspace_progress import _build_validated_match_workspace_progress_v1
from skatmind.observed_game_commentary import (
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
)
from skatmind.observed_game_contracts import (
    OBSERVED_GAME_CONTRACT_VERSION,
    ObservedGamePlayerV1,
    ObservedGameRecordV1,
    build_observed_game_record_v1,
)
from skatmind.observed_game_trace import ObservedPlayV1
from skatmind.opponent_statistics import (
    OPPONENT_STATISTICS_SCHEMA_VERSION,
    build_opponent_statistics_input,
)

_WORKSPACE_FINGERPRINT_DOMAIN = b"skatmind\0match_workspace_v1\0"
_PERSISTENCE_FINGERPRINT_DOMAIN = b"skatmind\0match_workspace_persistence_v1\0"
_LEGACY_WORKSPACE_FINGERPRINT_DOMAIN = b"skat-ai\0match_workspace_v1\0"
_LEGACY_PERSISTENCE_FINGERPRINT_DOMAIN = b"skat-ai\0match_workspace_persistence_v1\0"

_DOCUMENT_FIELDS = {
    "match_workspace_persistence_version",
    "document_kind",
    "workspace_fingerprint",
    "content_fingerprint",
    "workspace",
}
_WORKSPACE_FIELDS = {
    "match_workspace_contract_version",
    "revision",
    "match_definition",
    "slots",
}
_SLOT_FIELDS = {
    "match_workspace_slot_version",
    "match_position",
    "slot_kind",
    "observed_game",
    "passed_deal",
}
_PASSED_DEAL_FIELDS = {"match_passed_deal_version", "game_timecode"}
_MATCH_DEFINITION_FIELDS = {
    "match_capture_contract_version",
    "match_id",
    "title",
    "game_platform",
    "external_match_id",
    "played_at",
    "tournament_format",
    "source",
    "participants",
    "perspective_player_id",
}
_TOURNAMENT_FORMAT_FIELDS = {
    "match_tournament_format_version",
    "format_id",
    "provider",
    "display_name",
    "player_count",
    "game_count",
}
_SOURCE_FIELDS = {
    "match_source_metadata_version",
    "source_kind",
    "source_url",
    "source_title",
    "source_channel_name",
    "match_timecode",
}
_TIMECODE_FIELDS = {
    "media_timecode_version",
    "start_offset_ms",
    "end_offset_ms",
}
_PARTICIPANT_FIELDS = {
    "player_id",
    "player_label",
    "platform_player_id",
    "table_place",
    "statistics_snapshot",
}
_SNAPSHOT_FIELDS = {
    "match_player_statistics_snapshot_version",
    "snapshot_id",
    "observed_at",
    "statistics_record",
}
_OBSERVED_GAME_FIELDS = {
    "observed_game_contract_version",
    "game_id",
    "match_id",
    "match_position",
    "game_timecode",
    "players",
    "perspective_player_id",
    "perspective_initial_hand",
    "declarer_player_id",
    "declaration",
    "original_skat",
    "discarded_cards",
    "plays",
    "commentaries",
    "response_links",
}
_OBSERVED_PLAYER_FIELDS = {"player_id", "seat"}
_DECLARATION_FIELDS = {
    "game_type",
    "hand_game",
    "ouvert",
    "schneider_announced",
    "schwarz_announced",
    "matadors",
    "bid_value",
}
_PLAY_FIELDS = {
    "observed_play_version",
    "decision_index",
    "player_id",
    "card",
    "decision_timecode",
}
_COMMENTARY_FIELDS = {
    "decision_commentary_version",
    "commentary_id",
    "decision_index",
    "subject_player_id",
    "commentator_player_id",
    "commentator_name",
    "text",
    "commentary_timecode",
}
_RESPONSE_LINK_FIELDS = {
    "decision_response_link_version",
    "link_id",
    "commentary_id",
    "response_decision_index",
}


def _raise_validation(message: str, *, path: str) -> None:
    raise SkatMindValidationError(message, path=path)


def _require_object(
    value: object,
    *,
    fields: set[str],
    path: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise_validation("Value must be a JSON object.", path=path)
    if any(not isinstance(key, str) for key in value):
        _raise_validation("JSON object keys must be strings.", path=path)
    actual_fields = set(value)
    missing = sorted(fields - actual_fields)
    if missing:
        _raise_validation(f"Missing required fields: {missing}.", path=path)
    unknown = sorted(actual_fields - fields)
    if unknown:
        _raise_validation(f"Unsupported fields: {unknown}.", path=path)
    return value


def _require_array(value: object, *, path: str) -> list[object]:
    if not isinstance(value, list):
        _raise_validation("Value must be a JSON array.", path=path)
    return value


def _require_optional_array(value: object, *, path: str) -> tuple[object, ...] | None:
    if value is None:
        return None
    return tuple(_require_array(value, path=path))


def _require_version(
    value: object,
    expected: int,
    *,
    field_name: str,
    path: str,
) -> None:
    if type(value) is not int or value != expected:
        _raise_validation(f"{field_name} must equal {expected}.", path=path)


def _construct(
    constructor: Callable[..., Any],
    *,
    path: str,
    **values: object,
) -> Any:
    try:
        return constructor(**values)
    except SkatMindValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path=path) from error


def _require_exact_round_trip(
    source: Mapping[str, object],
    rebuilt: object,
    *,
    path: str,
) -> None:
    if not hasattr(rebuilt, "to_dict") or rebuilt.to_dict() != dict(source):
        _raise_validation("Persisted value is not in canonical form.", path=path)


def _build_timecode(value: object, *, path: str) -> MediaTimecodeV1 | None:
    if value is None:
        return None
    data = _require_object(value, fields=_TIMECODE_FIELDS, path=path)
    timecode = _construct(
        MediaTimecodeV1,
        path=path,
        media_timecode_version=data["media_timecode_version"],
        start_offset_ms=data["start_offset_ms"],
        end_offset_ms=data["end_offset_ms"],
    )
    _require_exact_round_trip(data, timecode, path=path)
    return timecode


def _build_source(value: object, *, path: str) -> MatchSourceMetadataV1:
    data = _require_object(value, fields=_SOURCE_FIELDS, path=path)
    source = _construct(
        MatchSourceMetadataV1,
        path=path,
        match_source_metadata_version=data["match_source_metadata_version"],
        source_kind=data["source_kind"],
        source_url=data["source_url"],
        source_title=data["source_title"],
        source_channel_name=data["source_channel_name"],
        match_timecode=_build_timecode(
            data["match_timecode"],
            path=f"{path}/match_timecode",
        ),
    )
    _require_exact_round_trip(data, source, path=path)
    return source


def _build_tournament_format(
    value: object,
    *,
    path: str,
) -> MatchTournamentFormatV1:
    data = _require_object(value, fields=_TOURNAMENT_FORMAT_FIELDS, path=path)
    try:
        canonical = get_match_tournament_format_v1(data["format_id"])
    except (TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path=f"{path}/format_id") from error
    if canonical.to_dict() != dict(data):
        _raise_validation(
            "Persisted tournament_format must equal the exact registry object.",
            path=path,
        )
    return canonical


def _build_snapshot(
    value: object,
    *,
    path: str,
) -> MatchPlayerStatisticsSnapshotV1 | None:
    if value is None:
        return None
    data = _require_object(value, fields=_SNAPSHOT_FIELDS, path=path)
    statistics_data = _require_object(
        data["statistics_record"],
        fields=set(data["statistics_record"])
        if isinstance(data["statistics_record"], Mapping)
        else set(),
        path=f"{path}/statistics_record",
    )
    try:
        statistics_record = build_opponent_statistics_input(
            {
                "schema_version": OPPONENT_STATISTICS_SCHEMA_VERSION,
                "records": [dict(statistics_data)],
            }
        ).records[0]
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path=f"{path}/statistics_record") from error
    snapshot = _construct(
        MatchPlayerStatisticsSnapshotV1,
        path=path,
        match_player_statistics_snapshot_version=data[
            "match_player_statistics_snapshot_version"
        ],
        snapshot_id=data["snapshot_id"],
        observed_at=data["observed_at"],
        statistics_record=statistics_record,
    )
    _require_exact_round_trip(data, snapshot, path=path)
    return snapshot


def _build_participant(value: object, *, path: str) -> MatchParticipantV1:
    data = _require_object(value, fields=_PARTICIPANT_FIELDS, path=path)
    participant = _construct(
        MatchParticipantV1,
        path=path,
        player_id=data["player_id"],
        player_label=data["player_label"],
        platform_player_id=data["platform_player_id"],
        table_place=data["table_place"],
        statistics_snapshot=_build_snapshot(
            data["statistics_snapshot"],
            path=f"{path}/statistics_snapshot",
        ),
    )
    _require_exact_round_trip(data, participant, path=path)
    return participant


def _build_match_definition(value: object, *, path: str) -> MatchCaptureDefinitionV1:
    data = _require_object(value, fields=_MATCH_DEFINITION_FIELDS, path=path)
    participants = tuple(
        _build_participant(item, path=f"{path}/participants/{index}")
        for index, item in enumerate(
            _require_array(data["participants"], path=f"{path}/participants")
        )
    )
    definition = _construct(
        MatchCaptureDefinitionV1,
        path=path,
        match_capture_contract_version=data["match_capture_contract_version"],
        match_id=data["match_id"],
        title=data["title"],
        game_platform=data["game_platform"],
        external_match_id=data["external_match_id"],
        played_at=data["played_at"],
        tournament_format=_build_tournament_format(
            data["tournament_format"],
            path=f"{path}/tournament_format",
        ),
        source=_build_source(data["source"], path=f"{path}/source"),
        participants=participants,
        perspective_player_id=data["perspective_player_id"],
    )
    _require_exact_round_trip(data, definition, path=path)
    return definition


def _build_declaration(value: object, *, path: str) -> GameDeclaration | None:
    if value is None:
        return None
    data = _require_object(value, fields=_DECLARATION_FIELDS, path=path)
    declaration = _construct(
        GameDeclaration,
        path=path,
        game_type=data["game_type"],
        hand_game=data["hand_game"],
        ouvert=data["ouvert"],
        schneider_announced=data["schneider_announced"],
        schwarz_announced=data["schwarz_announced"],
        matadors=data["matadors"],
        bid_value=data["bid_value"],
    )
    if build_serializable_game_declaration(declaration) != dict(data):
        _raise_validation("Persisted declaration is not in canonical form.", path=path)
    return declaration


def _build_observed_player(value: object, *, path: str) -> ObservedGamePlayerV1:
    data = _require_object(value, fields=_OBSERVED_PLAYER_FIELDS, path=path)
    player = _construct(
        ObservedGamePlayerV1,
        path=path,
        player_id=data["player_id"],
        seat=data["seat"],
    )
    _require_exact_round_trip(data, player, path=path)
    return player


def _build_play(value: object, *, path: str) -> ObservedPlayV1:
    data = _require_object(value, fields=_PLAY_FIELDS, path=path)
    play = _construct(
        ObservedPlayV1,
        path=path,
        observed_play_version=data["observed_play_version"],
        decision_index=data["decision_index"],
        player_id=data["player_id"],
        card=data["card"],
        decision_timecode=_build_timecode(
            data["decision_timecode"],
            path=f"{path}/decision_timecode",
        ),
    )
    _require_exact_round_trip(data, play, path=path)
    return play


def _build_commentary(value: object, *, path: str) -> ObservedDecisionCommentaryV1:
    data = _require_object(value, fields=_COMMENTARY_FIELDS, path=path)
    commentary = _construct(
        ObservedDecisionCommentaryV1,
        path=path,
        decision_commentary_version=data["decision_commentary_version"],
        commentary_id=data["commentary_id"],
        decision_index=data["decision_index"],
        subject_player_id=data["subject_player_id"],
        commentator_player_id=data["commentator_player_id"],
        commentator_name=data["commentator_name"],
        text=data["text"],
        commentary_timecode=_build_timecode(
            data["commentary_timecode"],
            path=f"{path}/commentary_timecode",
        ),
    )
    _require_exact_round_trip(data, commentary, path=path)
    return commentary


def _build_response_link(
    value: object,
    *,
    path: str,
) -> ObservedDecisionResponseLinkV1:
    data = _require_object(value, fields=_RESPONSE_LINK_FIELDS, path=path)
    link = _construct(
        ObservedDecisionResponseLinkV1,
        path=path,
        decision_response_link_version=data["decision_response_link_version"],
        link_id=data["link_id"],
        commentary_id=data["commentary_id"],
        response_decision_index=data["response_decision_index"],
    )
    _require_exact_round_trip(data, link, path=path)
    return link


def _build_observed_game(
    value: object,
    *,
    match_definition: MatchCaptureDefinitionV1,
    path: str,
) -> ObservedGameRecordV1:
    data = _require_object(value, fields=_OBSERVED_GAME_FIELDS, path=path)
    _require_version(
        data["observed_game_contract_version"],
        OBSERVED_GAME_CONTRACT_VERSION,
        field_name="observed_game_contract_version",
        path=f"{path}/observed_game_contract_version",
    )
    players = tuple(
        _build_observed_player(item, path=f"{path}/players/{index}")
        for index, item in enumerate(
            _require_array(data["players"], path=f"{path}/players")
        )
    )
    plays = tuple(
        _build_play(item, path=f"{path}/plays/{index}")
        for index, item in enumerate(
            _require_array(data["plays"], path=f"{path}/plays")
        )
    )
    commentaries = tuple(
        _build_commentary(item, path=f"{path}/commentaries/{index}")
        for index, item in enumerate(
            _require_array(data["commentaries"], path=f"{path}/commentaries")
        )
    )
    response_links = tuple(
        _build_response_link(item, path=f"{path}/response_links/{index}")
        for index, item in enumerate(
            _require_array(data["response_links"], path=f"{path}/response_links")
        )
    )
    game = _construct(
        build_observed_game_record_v1,
        path=path,
        match_definition=match_definition,
        game_id=data["game_id"],
        match_position=data["match_position"],
        game_timecode=_build_timecode(
            data["game_timecode"],
            path=f"{path}/game_timecode",
        ),
        seat_order_player_ids=tuple(player.player_id for player in players),
        perspective_initial_hand=_require_optional_array(
            data["perspective_initial_hand"],
            path=f"{path}/perspective_initial_hand",
        ),
        declarer_player_id=data["declarer_player_id"],
        declaration=_build_declaration(
            data["declaration"],
            path=f"{path}/declaration",
        ),
        original_skat=_require_optional_array(
            data["original_skat"],
            path=f"{path}/original_skat",
        ),
        discarded_cards=_require_optional_array(
            data["discarded_cards"],
            path=f"{path}/discarded_cards",
        ),
        plays=plays,
        commentaries=commentaries,
        response_links=response_links,
    )
    _require_exact_round_trip(data, game, path=path)
    return game


def _build_passed_deal(value: object, *, path: str) -> MatchPassedDealV1:
    data = _require_object(value, fields=_PASSED_DEAL_FIELDS, path=path)
    _require_version(
        data["match_passed_deal_version"],
        MATCH_PASSED_DEAL_VERSION,
        field_name="match_passed_deal_version",
        path=f"{path}/match_passed_deal_version",
    )
    passed_deal = _construct(
        MatchPassedDealV1,
        path=path,
        match_passed_deal_version=data["match_passed_deal_version"],
        game_timecode=_build_timecode(
            data["game_timecode"],
            path=f"{path}/game_timecode",
        ),
    )
    _require_exact_round_trip(data, passed_deal, path=path)
    return passed_deal


def _build_slot(
    value: object,
    *,
    match_definition: MatchCaptureDefinitionV1,
    path: str,
) -> MatchWorkspaceSlotV1:
    data = _require_object(value, fields=_SLOT_FIELDS, path=path)
    _require_version(
        data["match_workspace_slot_version"],
        MATCH_WORKSPACE_SLOT_VERSION,
        field_name="match_workspace_slot_version",
        path=f"{path}/match_workspace_slot_version",
    )
    observed_game = (
        None
        if data["observed_game"] is None
        else _build_observed_game(
            data["observed_game"],
            match_definition=match_definition,
            path=f"{path}/observed_game",
        )
    )
    passed_deal = (
        None
        if data["passed_deal"] is None
        else _build_passed_deal(data["passed_deal"], path=f"{path}/passed_deal")
    )
    try:
        slot = MatchWorkspaceSlotV1._from_validated(
            match_position=data["match_position"],
            slot_kind=data["slot_kind"],
            observed_game=observed_game,
            passed_deal=passed_deal,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path=path) from error
    _require_exact_round_trip(data, slot, path=path)
    return slot


def _build_workspace(value: object, *, path: str) -> MatchWorkspaceV1:
    data = _require_object(value, fields=_WORKSPACE_FIELDS, path=path)
    _require_version(
        data["match_workspace_contract_version"],
        MATCH_WORKSPACE_CONTRACT_VERSION,
        field_name="match_workspace_contract_version",
        path=f"{path}/match_workspace_contract_version",
    )
    match_definition = _build_match_definition(
        data["match_definition"],
        path=f"{path}/match_definition",
    )
    slots = tuple(
        _build_slot(
            item,
            match_definition=match_definition,
            path=f"{path}/slots/{index}",
        )
        for index, item in enumerate(
            _require_array(data["slots"], path=f"{path}/slots")
        )
    )
    try:
        workspace = _build_match_workspace_v1(
            revision=data["revision"],
            match_definition=match_definition,
            slots=slots,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path=path) from error
    _require_exact_round_trip(data, workspace, path=path)
    return workspace


def _sha256_domain_fingerprint(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json_bytes(value)).hexdigest()


def _fingerprint_profile_for_document_kind(
    document_kind: object,
) -> tuple[bytes, bytes, str]:
    if document_kind == MATCH_WORKSPACE_DOCUMENT_KIND:
        return (
            _WORKSPACE_FINGERPRINT_DOMAIN,
            _PERSISTENCE_FINGERPRINT_DOMAIN,
            MATCH_WORKSPACE_DOCUMENT_KIND,
        )
    if document_kind == LEGACY_MATCH_WORKSPACE_DOCUMENT_KIND:
        return (
            _LEGACY_WORKSPACE_FINGERPRINT_DOMAIN,
            _LEGACY_PERSISTENCE_FINGERPRINT_DOMAIN,
            LEGACY_MATCH_WORKSPACE_DOCUMENT_KIND,
        )
    _raise_validation("document_kind is unsupported.", path="/document_kind")


def _build_validated_workspace_fingerprint_v1(
    workspace: MatchWorkspaceV1,
    *,
    fingerprint_domain: bytes = _WORKSPACE_FINGERPRINT_DOMAIN,
) -> str:
    return _sha256_domain_fingerprint(
        fingerprint_domain,
        workspace.to_dict(),
    )


def build_match_workspace_fingerprint_v1(workspace: MatchWorkspaceV1) -> str:
    """Builds one deterministic fingerprint over the complete canonical Workspace."""
    if type(workspace) is not MatchWorkspaceV1:
        raise ValueError("workspace must be a MatchWorkspaceV1.")
    try:
        validate_match_workspace_v1(workspace)
        return _build_validated_workspace_fingerprint_v1(workspace)
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Internally supplied Match Workspace is inconsistent or not finite JSON.",
            path="",
        ) from error


def _content_fingerprint_material(
    *,
    workspace_fingerprint: str,
    workspace: MatchWorkspaceV1,
    document_kind: str = MATCH_WORKSPACE_DOCUMENT_KIND,
) -> dict[str, Any]:
    return {
        "match_workspace_persistence_version": MATCH_WORKSPACE_PERSISTENCE_VERSION,
        "document_kind": document_kind,
        "workspace_fingerprint": workspace_fingerprint,
        "workspace": workspace.to_dict(),
    }


def _build_match_workspace_content_fingerprint_v1(
    *,
    workspace_fingerprint: str,
    workspace: MatchWorkspaceV1,
    document_kind: str = MATCH_WORKSPACE_DOCUMENT_KIND,
    fingerprint_domain: bytes = _PERSISTENCE_FINGERPRINT_DOMAIN,
) -> str:
    return _sha256_domain_fingerprint(
        fingerprint_domain,
        _content_fingerprint_material(
            workspace_fingerprint=workspace_fingerprint,
            workspace=workspace,
            document_kind=document_kind,
        ),
    )


def _validate_match_workspace_persistence_document_fingerprints_v1(
    document: MatchWorkspacePersistenceDocumentV1,
) -> None:
    workspace_domain, persistence_domain, document_kind = (
        _fingerprint_profile_for_document_kind(document.document_kind)
    )
    workspace_fingerprint = _build_validated_workspace_fingerprint_v1(
        document.workspace,
        fingerprint_domain=workspace_domain,
    )
    if document.workspace_fingerprint != workspace_fingerprint:
        raise ValueError("workspace_fingerprint must match the exact Workspace.")
    content_fingerprint = _build_match_workspace_content_fingerprint_v1(
        workspace_fingerprint=workspace_fingerprint,
        workspace=document.workspace,
        document_kind=document_kind,
        fingerprint_domain=persistence_domain,
    )
    if document.content_fingerprint != content_fingerprint:
        raise ValueError(
            "content_fingerprint must match the complete persistence document."
        )


def build_match_workspace_persistence_document_v1(
    workspace: MatchWorkspaceV1,
) -> MatchWorkspacePersistenceDocumentV1:
    """Builds one validated private persistence document without file I/O."""
    if type(workspace) is not MatchWorkspaceV1:
        raise ValueError("workspace must be a MatchWorkspaceV1.")
    try:
        validate_match_workspace_v1(workspace)
        workspace_fingerprint = _build_validated_workspace_fingerprint_v1(workspace)
        content_fingerprint = _build_match_workspace_content_fingerprint_v1(
            workspace_fingerprint=workspace_fingerprint,
            workspace=workspace,
        )
        return _build_verified_match_workspace_persistence_document_v1(
            workspace_fingerprint=workspace_fingerprint,
            content_fingerprint=content_fingerprint,
            workspace=workspace,
        )
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Match Workspace persistence document assembly violated its contract.",
            path="",
        ) from error


def resume_match_workspace_document_v1(
    document: Mapping[str, object],
) -> MatchWorkspaceResumeResultV1:
    """Strictly reconstructs one Workspace document and derives current Progress."""
    if not isinstance(document, Mapping):
        raise SkatMindValidationError(
            "Match Workspace persistence document root must be a JSON object.",
            path="",
        )
    data = _require_object(document, fields=_DOCUMENT_FIELDS, path="")
    _require_version(
        data["match_workspace_persistence_version"],
        MATCH_WORKSPACE_PERSISTENCE_VERSION,
        field_name="match_workspace_persistence_version",
        path="/match_workspace_persistence_version",
    )
    workspace_domain, persistence_domain, document_kind = (
        _fingerprint_profile_for_document_kind(data["document_kind"])
    )
    workspace = _build_workspace(data["workspace"], path="/workspace")
    workspace_fingerprint = _build_validated_workspace_fingerprint_v1(
        workspace,
        fingerprint_domain=workspace_domain,
    )
    if data["workspace_fingerprint"] != workspace_fingerprint:
        _raise_validation(
            "workspace_fingerprint does not match the persisted Workspace.",
            path="/workspace_fingerprint",
        )
    content_fingerprint = _build_match_workspace_content_fingerprint_v1(
        workspace_fingerprint=workspace_fingerprint,
        workspace=workspace,
        document_kind=document_kind,
        fingerprint_domain=persistence_domain,
    )
    if data["content_fingerprint"] != content_fingerprint:
        _raise_validation(
            "content_fingerprint does not match the persistence document.",
            path="/content_fingerprint",
        )
    try:
        typed_document = _build_verified_match_workspace_persistence_document_v1(
            match_workspace_persistence_version=data[
                "match_workspace_persistence_version"
            ],
            document_kind=data["document_kind"],
            workspace_fingerprint=data["workspace_fingerprint"],
            content_fingerprint=data["content_fingerprint"],
            workspace=workspace,
        )
    except (TypeError, ValueError) as error:
        raise SkatMindValidationError(str(error), path="") from error
    if typed_document.to_dict() != dict(data):
        _raise_validation(
            "Persistence document values are not in canonical form.",
            path="",
        )
    try:
        progress = _build_validated_match_workspace_progress_v1(workspace)
        return MatchWorkspaceResumeResultV1(
            document=typed_document,
            progress=progress,
        )
    except (SkatMindInvariantError, AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Validated Match Workspace Progress reconstruction disagreed internally.",
            path="/workspace",
        ) from error
