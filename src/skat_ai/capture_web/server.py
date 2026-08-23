from __future__ import annotations

import json
import math
import re
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import parse_qs, urlsplit

from skat_ai.errors import SkatAIError, SkatAIInvariantError
from skat_ai.match_analysis_contracts import MatchDecisionAnalysisResultV1
from skat_ai.match_analysis_exports import (
    MatchArtifactExportV1,
    build_match_historical_game_collection_export_v1,
    build_match_historical_list_aggregation_export_v1,
    build_match_historical_list_input_export_v1,
    build_match_materialization_summary_export_v1,
    build_match_report_result_export_v1,
    build_match_training_source_collection_export_v1,
)
from skat_ai.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)

from .analysis import (
    execute_match_capture_web_analysis_v1,
    get_current_match_analysis_report_v1,
    get_current_materialization_report_v1,
)
from .context import MatchCaptureWebContextV1
from .contracts import (
    MATCH_CAPTURE_WEB_API_PREFIX,
    MATCH_CAPTURE_WEB_BIND_HOST,
    MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES,
)
from .operations import (
    apply_match_capture_web_operation_v1,
    create_match_capture_workspace_v1,
    reload_match_capture_workspace_v1,
)
from .rendering import render_match_capture_web_page_v1
from .security import (
    build_match_capture_web_cookie_v1,
    create_match_capture_web_token_v1,
    has_valid_match_capture_web_cookie_v1,
    match_capture_web_security_headers_v1,
    validate_match_capture_web_host_v1,
    validate_match_capture_web_origin_v1,
)
from .state import build_match_capture_web_state_v1

_ASSETS = {
    "/assets/capture.css": ("assets/capture.css", "text/css; charset=utf-8"),
    "/assets/capture.js": ("assets/capture.js", "text/javascript; charset=utf-8"),
}
_POST_ROUTES = {
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/create",
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/reload",
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/operation",
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/analysis",
}
_REPORT_PAGE_PATTERN = re.compile(r"^/reports/([0-9a-f]{64})$")
_REPORT_JSON_PATTERN = re.compile(
    rf"^{re.escape(MATCH_CAPTURE_WEB_API_PREFIX)}/reports/([0-9a-f]{{64}})\.json$"
)
_REPORT_STRATEGY_SOURCE_PATTERN = re.compile(
    rf"^{re.escape(MATCH_CAPTURE_WEB_API_PREFIX)}/reports/"
    r"([0-9a-f]{64})/strategy-source\.json$"
)
_EXPORT_BUILDERS = {
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/exports/materialization.json": (
        build_match_materialization_summary_export_v1
    ),
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/exports/historical-games.json": (
        build_match_historical_game_collection_export_v1
    ),
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/exports/training-sources.json": (
        build_match_training_source_collection_export_v1
    ),
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/exports/historical-list-input.json": (
        build_match_historical_list_input_export_v1
    ),
    f"{MATCH_CAPTURE_WEB_API_PREFIX}/exports/historical-list-aggregation.json": (
        build_match_historical_list_aggregation_export_v1
    ),
}
_JSON_INTEGER_FIELDS = {
    "expected_revision",
    "match_position",
    "games_played",
    "solo_games_played",
    "solo_games_won",
    "solo_hand_games",
    "suit_games",
    "grand_games",
    "null_games",
    "defender_games_played",
    "defender_games_won",
    "matadors",
    "bid_value",
    "target_play_count",
    "decision_index",
    "response_decision_index",
    "immediate_sample_count",
    "immediate_random_seed",
    "search_random_seed",
}
_JSON_NULLABLE_INTEGER_FIELDS = {
    "solo_games_played",
    "solo_games_won",
    "solo_hand_games",
    "suit_games",
    "grand_games",
    "null_games",
    "defender_games_played",
    "defender_games_won",
    "matadors",
    "bid_value",
    "search_random_seed",
}
_JSON_NUMBER_FIELDS = {
    "solo_games_played_percent",
    "solo_games_won_percent",
    "solo_hand_percent",
    "suit_games_percent",
    "grand_games_percent",
    "null_games_percent",
    "defender_games_played_percent",
    "defender_games_won_percent",
}
_JSON_BOOLEAN_FIELDS = {
    "hand_game",
    "ouvert",
    "schneider_announced",
    "schwarz_announced",
    "confirm_replace",
    "confirm_clear",
    "confirm_clear_snapshot",
    "decision_snapshots",
    "immediate_review",
    "search_review",
    "information_set_search_review",
    "replay_coaching",
    "information_set_replay_coaching",
    "use_profile_presets",
}


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key {key!r} is not allowed.")
        result[key] = value
    return result


def _reject_non_finite_json_number(value: str) -> object:
    raise ValueError(f"Non-finite JSON number {value!r} is not allowed.")


def _validate_request_value_types(
    values: Mapping[str, object],
    *,
    wants_json: bool,
) -> None:
    """Keeps form text coercion separate from strict native JSON scalar types."""
    for name, value in values.items():
        if not wants_json:
            valid_form_value = isinstance(value, str) or (
                name == "cards"
                and isinstance(value, list)
                and all(isinstance(item, str) for item in value)
            )
            if not valid_form_value:
                raise ValueError(f"{name} must be form text.")
            continue
        if name in _JSON_INTEGER_FIELDS:
            if value is None and name in _JSON_NULLABLE_INTEGER_FIELDS:
                continue
            if type(value) is not int:
                raise ValueError(f"{name} must be a JSON integer.")
        elif name in _JSON_NUMBER_FIELDS:
            if type(value) not in {int, float} or (
                type(value) is float and not math.isfinite(value)
            ):
                raise ValueError(f"{name} must be a JSON number.")
        elif name in _JSON_BOOLEAN_FIELDS:
            if type(value) is not bool:
                raise ValueError(f"{name} must be a JSON boolean.")
        elif name == "cards":
            if not (
                isinstance(value, str)
                or (isinstance(value, list) and all(isinstance(item, str) for item in value))
            ):
                raise ValueError("cards must be JSON text or an array of text values.")
        elif not isinstance(value, str):
            raise ValueError(f"{name} must be JSON text.")


class MatchCaptureWebServerV1(ThreadingHTTPServer):
    """One loopback-only local server for one explicit Match Workspace file."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        context: MatchCaptureWebContextV1,
        *,
        port: int = 0,
        token: str | None = None,
    ) -> None:
        if type(port) is not int or not 0 <= port <= 65_535:
            raise ValueError("port must be 0 or an integer from 1 through 65535.")
        self.capture_context = context
        self.capture_token = token or create_match_capture_web_token_v1()
        self.capture_notice: tuple[str, str] | None = None
        super().__init__(
            (MATCH_CAPTURE_WEB_BIND_HOST, port),
            MatchCaptureWebRequestHandlerV1,
        )

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    @property
    def bootstrap_url(self) -> str:
        return f"http://{MATCH_CAPTURE_WEB_BIND_HOST}:{self.port}/?token={self.capture_token}"

    @property
    def origin(self) -> str:
        return f"http://{MATCH_CAPTURE_WEB_BIND_HOST}:{self.port}"

    def set_notice(self, message: str, kind: str) -> None:
        with self.capture_context.lock:
            self.capture_notice = (message, kind)

    def take_notice(self) -> tuple[str, str] | None:
        with self.capture_context.lock:
            notice = self.capture_notice
            self.capture_notice = None
            return notice

    def server_close(self) -> None:
        with self.capture_context.lock:
            self.capture_context.report_store.clear()
        super().server_close()


class MatchCaptureWebRequestHandlerV1(BaseHTTPRequestHandler):
    server: MatchCaptureWebServerV1

    def log_message(self, _format: str, *_args: object) -> None:
        """Disables default logging so the bootstrap token cannot enter logs."""

    def _headers(
        self,
        status: int,
        content_type: str,
        length: int,
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        for name, value in match_capture_web_security_headers_v1():
            self.send_header(name, value)
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()

    def _send_bytes(
        self,
        status: int,
        content: bytes,
        *,
        content_type: str,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self._headers(
            status,
            content_type,
            len(content),
            extra_headers=extra_headers,
        )
        self.wfile.write(content)

    def _send_text(
        self,
        status: int,
        content: str,
        *,
        content_type: str = "text/plain; charset=utf-8",
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self._send_bytes(
            status,
            content.encode("utf-8"),
            content_type=content_type,
            extra_headers=extra_headers,
        )

    def _send_json(self, status: int, value: Mapping[str, object]) -> None:
        content = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self._send_bytes(
            status,
            content,
            content_type="application/json; charset=utf-8",
        )

    def _host_is_valid(self) -> bool:
        return validate_match_capture_web_host_v1(
            self.headers.get("Host"),
            self.server.port,
        )

    def _cookie_is_valid(self) -> bool:
        return has_valid_match_capture_web_cookie_v1(
            self.headers.get("Cookie"),
            self.server.capture_token,
        )

    def _authorize_get(self, path: str, query: str) -> bool:
        if not self._host_is_valid():
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        if path == "/" and query:
            query_values = parse_qs(query, keep_blank_values=True)
            if set(query_values) != {"token"} or query_values["token"] != [
                self.server.capture_token
            ]:
                self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
                return False
            self._send_text(
                HTTPStatus.SEE_OTHER,
                "",
                extra_headers=(
                    ("Location", "/"),
                    (
                        "Set-Cookie",
                        build_match_capture_web_cookie_v1(self.server.capture_token),
                    ),
                ),
            )
            return False
        if query or not self._cookie_is_valid():
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        return True

    def _authorize_mutation(self) -> bool:
        if not self._host_is_valid() or not self._cookie_is_valid():
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        if not validate_match_capture_web_origin_v1(
            self.headers.get("Origin"),
            self.server.port,
            self.headers.get("Host"),
        ):
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        return True

    def _state(
        self,
        position: int,
        *,
        selected_report_id: str | None = None,
    ) -> dict[str, Any]:
        with self.server.capture_context.lock:
            return build_match_capture_web_state_v1(
                self.server.capture_context.workspace,
                workspace_filename=(self.server.capture_context.workspace_filename),
                selected_position=position,
                report_store=self.server.capture_context.report_store,
                selected_report_id=selected_report_id,
            )

    def _parse_body(self) -> tuple[dict[str, object], bool]:
        if self.headers.get("Transfer-Encoding") is not None:
            raise ValueError("Transfer-Encoding is not supported.")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required.")
        try:
            length = int(raw_length)
        except ValueError as error:
            raise ValueError("Content-Length must be an integer.") from error
        if length < 0:
            raise ValueError("Content-Length must not be negative.")
        if length > MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES:
            raise OverflowError("Request body is too large.")
        raw_body = self.rfile.read(length)
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type == "application/json":
            try:
                value = json.loads(
                    raw_body.decode("utf-8"),
                    object_pairs_hook=_reject_duplicate_json_keys,
                    parse_constant=_reject_non_finite_json_number,
                )
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("Request body must be valid UTF-8 JSON.") from error
            if not isinstance(value, dict):
                raise ValueError("JSON request body must be an object.")
            return value, True
        if media_type != "application/x-www-form-urlencoded":
            raise ValueError(
                "Content-Type must be application/json or application/x-www-form-urlencoded."
            )
        try:
            decoded = raw_body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Form request body must be valid UTF-8.") from error
        parsed = parse_qs(decoded, keep_blank_values=True, strict_parsing=True)
        duplicates = sorted(
            name for name, items in parsed.items() if name != "cards" and len(items) != 1
        )
        if duplicates:
            raise ValueError(f"Form fields must not repeat: {', '.join(duplicates)}.")
        return {
            name: items if name == "cards" and len(items) > 1 else items[0]
            for name, items in parsed.items()
        }, False

    def _position_from_path(self, path: str) -> int | None:
        prefix = "/position/"
        if not path.startswith(prefix):
            return None
        suffix = path.removeprefix(prefix)
        try:
            position = int(suffix)
        except ValueError:
            return None
        return position if 1 <= position <= 36 else None

    def _send_artifact(self, filename: str, content: bytes) -> None:
        self._send_bytes(
            HTTPStatus.OK,
            content,
            content_type="application/json; charset=utf-8",
            extra_headers=(
                (
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                ),
            ),
        )

    def _report_status(self, report_id: str):
        status, report = get_current_match_analysis_report_v1(
            self.server.capture_context,
            report_id,
        )
        if status == "missing":
            self._send_text(HTTPStatus.NOT_FOUND, "Not found")
            return None
        if status == "stale":
            self._send_text(HTTPStatus.CONFLICT, "Report revision is stale")
            return None
        return report

    def _materialization_report(self):
        status, report = get_current_materialization_report_v1(self.server.capture_context)
        if status == "missing":
            self._send_text(HTTPStatus.NOT_FOUND, "Artifact unavailable")
            return None
        if status == "stale":
            self._send_text(HTTPStatus.CONFLICT, "Report revision is stale")
            return None
        return report

    def _build_materialization_export(
        self,
        path: str,
        report,
    ) -> MatchArtifactExportV1:
        materialization = report.value.materialization
        source = report.value if path.endswith("/exports/materialization.json") else materialization
        return _EXPORT_BUILDERS[path](source)

    def _is_get_route(self, path: str) -> bool:
        return (
            path == "/"
            or path in _ASSETS
            or path == f"{MATCH_CAPTURE_WEB_API_PREFIX}/state"
            or path in _EXPORT_BUILDERS
            or self._position_from_path(path) is not None
            or _REPORT_PAGE_PATTERN.fullmatch(path) is not None
            or _REPORT_JSON_PATTERN.fullmatch(path) is not None
            or _REPORT_STRATEGY_SOURCE_PATTERN.fullmatch(path) is not None
        )

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        if not self._authorize_get(path, parsed.query):
            return
        try:
            if path in _POST_ROUTES:
                self._method_not_allowed()
                return
            report_page = _REPORT_PAGE_PATTERN.fullmatch(path)
            if report_page is not None:
                with self.server.capture_context.lock:
                    report = self._report_status(report_page.group(1))
                    if report is None:
                        return
                    position = report.match_position or 1
                    state = self._state(
                        position,
                        selected_report_id=report.report_id,
                    )
                self._send_text(
                    HTTPStatus.OK,
                    render_match_capture_web_page_v1(state),
                    content_type="text/html; charset=utf-8",
                )
                return
            strategy_source = _REPORT_STRATEGY_SOURCE_PATTERN.fullmatch(path)
            if strategy_source is not None:
                with self.server.capture_context.lock:
                    report = self._report_status(strategy_source.group(1))
                    if report is None:
                        return
                    if (
                        report.report_kind != "decision_analysis"
                        or type(report.value) is not MatchDecisionAnalysisResultV1
                        or report.value.status != "executed"
                    ):
                        self._send_text(HTTPStatus.NOT_FOUND, "Artifact unavailable")
                        return
                    root_artifact = build_match_report_result_export_v1(report)
                    export = build_match_analysis_report_source_export_v1(report)
                    filename = (
                        f"{root_artifact.filename.removesuffix('.json')}-strategy-source.json"
                    )
                    content = serialize_match_analysis_report_source_export_v1(export)
                self._send_artifact(filename, content)
                return
            report_json = _REPORT_JSON_PATTERN.fullmatch(path)
            if report_json is not None:
                with self.server.capture_context.lock:
                    report = self._report_status(report_json.group(1))
                    if report is None:
                        return
                    try:
                        artifact = build_match_report_result_export_v1(report)
                        filename = artifact.filename
                        content = artifact.to_bytes()
                    except ValueError:
                        self._send_text(HTTPStatus.NOT_FOUND, "Artifact unavailable")
                        return
                self._send_artifact(filename, content)
                return
            if path in _EXPORT_BUILDERS:
                with self.server.capture_context.lock:
                    report = self._materialization_report()
                    if report is None:
                        return
                    try:
                        artifact = self._build_materialization_export(path, report)
                        filename = artifact.filename
                        content = artifact.to_bytes()
                    except ValueError:
                        self._send_text(HTTPStatus.NOT_FOUND, "Artifact unavailable")
                        return
                self._send_artifact(filename, content)
                return
            if path in _ASSETS:
                resource_name, content_type = _ASSETS[path]
                content = files("skat_ai.capture_web").joinpath(resource_name).read_bytes()
                self._send_bytes(
                    HTTPStatus.OK,
                    content,
                    content_type=content_type,
                )
                return
            if path.startswith("/assets/"):
                self._send_text(HTTPStatus.NOT_FOUND, "Not found")
                return
            if path == f"{MATCH_CAPTURE_WEB_API_PREFIX}/state":
                self._send_json(HTTPStatus.OK, self._state(1))
                return
            position = 1 if path == "/" else self._position_from_path(path)
            if position is None:
                self._send_text(HTTPStatus.NOT_FOUND, "Not found")
                return
            state = self._state(position)
            notice = self.server.take_notice()
            self._send_text(
                HTTPStatus.OK,
                render_match_capture_web_page_v1(
                    state,
                    notice=None if notice is None else notice[0],
                    notice_kind="info" if notice is None else notice[1],
                ),
                content_type="text/html; charset=utf-8",
            )
        except (SkatAIError, TypeError, ValueError):
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
        except OSError:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Filesystem error")
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        if not self._authorize_mutation():
            return
        if parsed.query:
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        if parsed.path not in _POST_ROUTES:
            if self._is_get_route(parsed.path):
                self._method_not_allowed()
                return
            self._send_text(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            values, wants_json = self._parse_body()
            _validate_request_value_types(values, wants_json=wants_json)
            if parsed.path.endswith("/reload") and set(values) - {"match_position"}:
                raise ValueError("Reload accepts only match_position.")
        except OverflowError:
            self._send_text(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body is too large")
            return
        except ValueError as error:
            self._send_text(HTTPStatus.BAD_REQUEST, str(error))
            return
        try:
            if parsed.path.endswith("/create"):
                result = create_match_capture_workspace_v1(
                    self.server.capture_context,
                    values,
                )
            elif parsed.path.endswith("/reload"):
                selected = values.get("match_position", 1)
                try:
                    position = int(selected)
                except (TypeError, ValueError) as error:
                    raise ValueError("match_position must be an integer.") from error
                if not 1 <= position <= 36:
                    raise ValueError("match_position must be an integer from 1 through 36.")
                result = reload_match_capture_workspace_v1(
                    self.server.capture_context,
                    selected_position=position,
                )
            elif parsed.path.endswith("/operation"):
                result = apply_match_capture_web_operation_v1(
                    self.server.capture_context,
                    values,
                )
            else:
                result = execute_match_capture_web_analysis_v1(
                    self.server.capture_context,
                    values,
                    browser_form=not wants_json,
                )
            if wants_json:
                self._send_json(result.http_status, result.to_dict())
                return
            notice_kind = "warning" if result.http_status == 409 else "info"
            if result.http_status == 200:
                if parsed.path.endswith("/analysis"):
                    report_id = result.state["selected_report_id"]
                    self._send_text(
                        HTTPStatus.SEE_OTHER,
                        "",
                        extra_headers=(("Location", f"/reports/{report_id}"),),
                    )
                    return
                self.server.set_notice(result.message, notice_kind)
                selected_position = result.state["selected_position"]
                location = (
                    "/"
                    if not result.state["workspace_exists"]
                    else f"/position/{selected_position}"
                )
                self._send_text(
                    HTTPStatus.SEE_OTHER,
                    "",
                    extra_headers=(("Location", location),),
                )
                return
            self._send_text(
                result.http_status,
                render_match_capture_web_page_v1(
                    result.state,
                    notice=result.message,
                    notice_kind=notice_kind,
                ),
                content_type="text/html; charset=utf-8",
            )
        except SkatAIInvariantError:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
        except SkatAIError as error:
            if parsed.path.endswith("/analysis"):
                self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
                return
            if wants_json:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "validation_error", "message": str(error)},
                )
                return
            position_value = values.get("match_position", 1)
            try:
                position = int(position_value)
            except (TypeError, ValueError):
                position = 1
            if not 1 <= position <= 36:
                position = 1
            self._send_text(
                HTTPStatus.BAD_REQUEST,
                render_match_capture_web_page_v1(
                    self._state(position),
                    notice=str(error),
                    notice_kind="error",
                ),
                content_type="text/html; charset=utf-8",
            )
        except (TypeError, ValueError) as error:
            if wants_json:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "validation_error", "message": str(error)},
                )
                return
            position_value = values.get("match_position", 1)
            try:
                position = int(position_value)
            except (TypeError, ValueError):
                position = 1
            if not 1 <= position <= 36:
                position = 1
            self._send_text(
                HTTPStatus.BAD_REQUEST,
                render_match_capture_web_page_v1(
                    self._state(position),
                    notice=str(error),
                    notice_kind="error",
                ),
                content_type="text/html; charset=utf-8",
            )
        except OSError:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Filesystem error")
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def _method_not_allowed(self) -> None:
        self._send_text(
            HTTPStatus.METHOD_NOT_ALLOWED,
            "Method not allowed",
            extra_headers=(("Allow", "GET, POST"),),
        )

    def do_DELETE(self) -> None:
        if self._host_is_valid() and self._cookie_is_valid():
            self._method_not_allowed()
        else:
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")

    do_HEAD = do_DELETE
    do_OPTIONS = do_DELETE
    do_PATCH = do_DELETE
    do_PUT = do_DELETE


def start_match_capture_web_server_v1(
    context: MatchCaptureWebContextV1,
    *,
    port: int = 0,
    token: str | None = None,
) -> MatchCaptureWebServerV1:
    return MatchCaptureWebServerV1(context, port=port, token=token)


def serve_match_capture_web_in_thread_v1(
    server: MatchCaptureWebServerV1,
) -> threading.Thread:
    """Starts one testable in-process server thread; callers own shutdown."""
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
