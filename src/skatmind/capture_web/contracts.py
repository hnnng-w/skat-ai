from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

MATCH_CAPTURE_WEB_VERSION = 1
MATCH_CAPTURE_WEB_PROTOCOL_VERSION = 1

MATCH_CAPTURE_WEB_BIND_HOST = "127.0.0.1"
MATCH_CAPTURE_WEB_API_PREFIX = "/api/v1"
MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES = 1_048_576

MATCH_CAPTURE_WEB_WORKSPACE_POLICY = "one_explicit_workspace_file_per_server"
MATCH_CAPTURE_WEB_PERSISTENCE_POLICY = "load_operate_compare_and_swap_save"
MATCH_CAPTURE_WEB_SECURITY_POLICY = "loopback_same_origin_token"
MATCH_CAPTURE_WEB_ASSET_POLICY = "packaged_local_assets_without_external_dependencies"
MATCH_CAPTURE_WEB_RENDERING_POLICY = "server_rendered_with_progressive_enhancement"
MATCH_CAPTURE_WEB_NETWORK_POLICY = "no_external_requests"

MATCH_CAPTURE_WEB_OPERATIONS: Final[tuple[str, ...]] = (
    "create_workspace",
    "reload_workspace",
    "update_match_metadata",
    "start_game",
    "set_game_timecode",
    "set_perspective_hand",
    "set_declaration",
    "set_original_skat",
    "set_discarded_cards",
    "append_plays",
    "truncate_plays",
    "set_commentary",
    "remove_commentary",
    "set_response_link",
    "remove_response_link",
    "mark_passed_deal",
    "clear_position",
    "set_player_statistics_snapshot",
    "clear_player_statistics_snapshot",
    "prepare_materialization",
    "analyze_decision",
    "analyze_historical_game",
)

MATCH_CAPTURE_WEB_MUTATION_OPERATIONS: Final[tuple[str, ...]] = (
    "update_match_metadata",
    "start_game",
    "set_game_timecode",
    "set_perspective_hand",
    "set_declaration",
    "set_original_skat",
    "set_discarded_cards",
    "append_plays",
    "truncate_plays",
    "set_commentary",
    "remove_commentary",
    "set_response_link",
    "remove_response_link",
    "mark_passed_deal",
    "clear_position",
    "set_player_statistics_snapshot",
    "clear_player_statistics_snapshot",
)

MATCH_CAPTURE_WEB_RESULT_STATUSES: Final[tuple[str, ...]] = (
    "applied",
    "unchanged",
    "revision_conflict",
    "persistence_conflict",
    "reloaded",
)


def _freeze_json(value: object) -> object:
    if value is None or type(value) in {bool, int, float, str}:
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    raise ValueError("state must contain only JSON-compatible values.")


def _thaw_json(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchCaptureWebResultV1:
    """One path-free result returned by the private browser transport."""

    match_capture_web_protocol_version: int = MATCH_CAPTURE_WEB_PROTOCOL_VERSION
    operation: str
    status: str
    http_status: int
    message: str
    state: Mapping[str, Any]
    removed_commentary_ids: tuple[str, ...] = ()
    removed_response_link_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.match_capture_web_protocol_version != MATCH_CAPTURE_WEB_PROTOCOL_VERSION:
            raise ValueError(
                "match_capture_web_protocol_version must equal "
                f"{MATCH_CAPTURE_WEB_PROTOCOL_VERSION}."
            )
        if self.operation not in MATCH_CAPTURE_WEB_OPERATIONS:
            raise ValueError(f"operation must be one of {list(MATCH_CAPTURE_WEB_OPERATIONS)}.")
        if self.status not in MATCH_CAPTURE_WEB_RESULT_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_CAPTURE_WEB_RESULT_STATUSES)}."
            )
        if type(self.http_status) is not int or not 100 <= self.http_status <= 599:
            raise ValueError("http_status must be one valid HTTP status code.")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("message must be a non-empty string.")
        if not isinstance(self.state, Mapping):
            raise ValueError("state must be a browser-safe mapping.")
        object.__setattr__(self, "state", _freeze_json(self.state))

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_capture_web_protocol_version": (
                self.match_capture_web_protocol_version
            ),
            "operation": self.operation,
            "status": self.status,
            "message": self.message,
            "state": _thaw_json(self.state),
            "removed_commentary_ids": list(self.removed_commentary_ids),
            "removed_response_link_ids": list(self.removed_response_link_ids),
        }
