from __future__ import annotations

import hmac
import json
import re
import threading
from email.message import Message
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, quote, urlsplit

from skatmind.capture_web.contracts import MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES
from skatmind.capture_web.rendering import render_match_capture_web_body_v1
from skatmind.corpus_web.contracts import LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES
from skatmind.corpus_web.downloads import (
    LearningCorpusPreparedDownloadUnavailableError,
)
from skatmind.corpus_web.rendering import render_learning_corpus_web_body_v1
from skatmind.corpus_web.uploads import parse_learning_corpus_multipart_upload_v1
from skatmind.errors import SkatMindError, SkatMindInvariantError, SkatMindWorkflowError
from skatmind.match_workspace_persistence_codec import resume_match_workspace_document_v1

from .context import AppWebContextV1
from .contracts import APP_ROUTE_PATHS
from .cross_area_transfer import (
    transfer_active_match_report_to_corpus_v1,
    transfer_active_match_workspace_to_corpus_v1,
)
from .frontend_profile_operations import (
    FRONTEND_LANGUAGE_ACTION_ROUTE,
    FRONTEND_PROFILE_ACTION_ROUTES,
    FRONTEND_PROFILE_RESET_ACTION_ROUTE,
    FrontendProfilePersistenceConflictError,
    InvalidFrontendProfileResetRequiredError,
    StaleFrontendProfileGenerationError,
    is_safe_frontend_return_path_v1,
    reset_frontend_profile_v1,
    set_frontend_language_v1,
)
from .frontend_profile_state import (
    project_browser_safe_frontend_profile_state_v1,
)
from .guided_contracts import (
    ANALYZE_ACTION_ROUTE_PATHS,
    ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESET_ACTION_ROUTE_PATH,
    ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
    ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
    GUIDED_ACTION_ROUTE_PATHS,
    GUIDED_DOWNLOAD_ROUTE_PATHS,
    POSITION_REQUEST_DOWNLOAD_FILENAME,
    POSITION_RESULT_DOWNLOAD_FILENAME,
    REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
    REVIEW_BACK_ACTION_ROUTE_PATH,
    REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_FILENAME,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESET_ACTION_ROUTE_PATH,
    REVIEW_RESULT_DOWNLOAD_FILENAME,
    REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
    REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_START_ACTION_ROUTE_PATH,
    REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
)
from .json_transfer import FRONTEND_JSON_MAX_FILE_BYTES, parse_frontend_json_import_v1
from .learning_frontend import (
    build_unified_learning_download_v1,
    build_unified_learning_state_v1,
    clear_unified_learning_report_sources_v1,
    create_unified_learning_corpus_v1,
    import_report_source_bytes_into_unified_learning_v1,
    import_workspace_bytes_into_unified_learning_v1,
    open_unified_learning_corpus_v1,
    prepare_unified_learning_artifacts_v1,
    reload_unified_learning_corpus_v1,
    remove_unified_learning_report_source_v1,
    select_unified_learning_current_snapshot_v1,
)
from .managed_item_contracts import MANAGED_ITEM_MAX_IMPORT_BYTES
from .managed_item_discovery import discover_managed_items_v1
from .managed_item_import import parse_managed_item_json_upload_v1
from .managed_item_storage import (
    build_managed_item_handle_v1,
    build_managed_item_storage_name_v1,
)
from .match_frontend import (
    apply_unified_match_operation_v1,
    build_unified_match_creation_state_v1,
    build_unified_match_export_download_v1,
    build_unified_match_report_download_v1,
    build_unified_match_state_v1,
    build_unified_match_workspace_download_v1,
    create_unified_match_v1,
    execute_unified_match_analysis_v1,
    get_unified_match_report_v1,
    import_unified_match_v1,
    open_unified_match_v1,
    reload_unified_match_v1,
    select_unified_match_position_v1,
)
from .rendering import (
    render_app_content_page_v1,
    render_app_error_page_v1,
    render_app_page_v1,
    render_authorization_failure_v1,
)
from .security import (
    APP_WEB_BIND_HOST,
    app_web_security_headers_v1,
    build_app_web_cookie_v1,
    create_app_web_token_v1,
    has_valid_app_web_cookie_v1,
    validate_app_web_host_v1,
    validate_app_web_origin_v1,
)
from .session_form_translation import (
    build_session_edit_from_form_v1,
    build_session_historical_execution_options_from_form_v1,
    build_session_position_options_from_form_v1,
)
from .session_frontend import (
    apply_guided_session_edit_v1,
    build_guided_session_persistence_download_v1,
    build_guided_session_players_v1,
    create_guided_session_v1,
    default_guided_session_execution_options_v1,
    execute_guided_session_historical_v1,
    execute_guided_session_position_v1,
    get_guided_session_import_product_id_v1,
    import_guided_session_v1,
    open_guided_session_v1,
    reload_guided_session_v1,
    rewind_guided_session_v1,
)
from .stateful_rendering import (
    render_guided_session_v1,
    render_managed_category_landing_v1,
    render_match_to_learning_transfer_v1,
)
from .workflow_operations import (
    FrontendWorkflowValidationError,
    back_review_v1,
    reset_workflow_v1,
    run_guided_analyze_v1,
    run_guided_review_v1,
    run_imported_request_v1,
    start_review_v1,
    store_frontend_import_v1,
    undo_review_play_v1,
    update_review_v1,
)
from .workflow_state import (
    FrontendWorkflowExecutionConflictError,
    StaleFrontendWorkflowRevisionError,
)

APP_WEB_MAX_REQUEST_BYTES = FRONTEND_JSON_MAX_FILE_BYTES + 4_096
_MANAGED_IMPORT_MAX_REQUEST_BYTES = MANAGED_ITEM_MAX_IMPORT_BYTES + 4_096

_ASSETS = {
    "/assets/app.css": (
        "skatmind.app_web",
        "assets/app.css",
        "text/css; charset=utf-8",
    ),
    "/matches/assets/capture.css": (
        "skatmind.capture_web",
        "assets/capture.css",
        "text/css; charset=utf-8",
    ),
    "/matches/assets/capture.js": (
        "skatmind.capture_web",
        "assets/capture.js",
        "text/javascript; charset=utf-8",
    ),
    "/learning/assets/corpus.css": (
        "skatmind.corpus_web",
        "assets/corpus.css",
        "text/css; charset=utf-8",
    ),
    "/learning/assets/corpus.js": (
        "skatmind.corpus_web",
        "assets/corpus.js",
        "text/javascript; charset=utf-8",
    ),
}
_BODY_METHODS = {"POST", "PUT", "PATCH"}
_MUTATION_METHODS = _BODY_METHODS | {"DELETE"}
_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_MATCH_POSITION_PATTERN = re.compile(r"^/matches/position/([1-9]|[12][0-9]|3[0-6])$")
_MATCH_REPORT_PATTERN = re.compile(r"^/matches/reports/([0-9a-f]{64})$")
_MATCH_REPORT_JSON_PATTERN = re.compile(
    r"^/matches/api/v1/reports/([0-9a-f]{64})\.json$"
)
_MATCH_REPORT_SOURCE_PATTERN = re.compile(
    r"^/matches/api/v1/reports/([0-9a-f]{64})/strategy-source\.json$"
)
_MATCH_EXPORT_ROUTES = {
    "/matches/api/v1/exports/materialization.json": "materialization",
    "/matches/api/v1/exports/historical-games.json": "historical_games",
    "/matches/api/v1/exports/training-sources.json": "training_sources",
    "/matches/api/v1/exports/historical-list-input.json": "historical_list_input",
    "/matches/api/v1/exports/historical-list-aggregation.json": (
        "historical_list_aggregation"
    ),
}
_LEARNING_DOWNLOAD_ROUTES = {
    "/learning/downloads/player-catalog.json": "player_catalog",
    "/learning/downloads/human-evidence.json": "human_evidence",
    "/learning/downloads/strategy-teacher-evidence.json": (
        "strategy_teacher_evidence"
    ),
    "/learning/downloads/learning-dataset-v2.json": "learning_dataset_v2",
    "/learning/downloads/known-player-partitions.json": "known_player_partitions",
    "/learning/downloads/unseen-player-partitions.json": "unseen_player_partitions",
    "/learning/downloads/cross-game-summary.json": "cross_game_summary",
    "/learning/downloads/tactical-motif-evidence.json": "tactical_motif_evidence",
    "/learning/downloads/tactical-motif-cross-game-summary.json": (
        "tactical_motif_cross_game_summary"
    ),
    "/learning/downloads/tactical-cross-game-coaching.json": (
        "tactical_cross_game_coaching"
    ),
}
_SESSION_DOWNLOAD_ROUTES = {
    "/sessions/downloads/session.json",
    "/sessions/downloads/request.json",
    "/sessions/downloads/result.json",
}
_STATEFUL_POST_ROUTES = {
    "/sessions/create",
    "/sessions/import",
    "/sessions/open",
    "/sessions/reload",
    "/sessions/command",
    "/sessions/undo",
    "/sessions/analyze",
    "/sessions/review",
    "/matches/import",
    "/matches/open",
    "/matches/api/v1/create",
    "/matches/api/v1/reload",
    "/matches/api/v1/operation",
    "/matches/api/v1/analysis",
    "/matches/transfer-workspace",
    "/matches/transfer-report",
    "/learning/create",
    "/learning/open",
    "/learning/api/v1/operations",
}
_CONTENT_TITLE_KEYS = {
    "Sessions": "page.sessions.title",
    "Match capture": "page.matches.title",
    "Learning & cross-game insights": "page.learning.title",
    "Guided Session": "page.session_current.title",
    "Managed Match capture": "page.match_current.title",
    "Create a managed Match": "page.match_create.title",
    "Managed Learning Corpus": "page.learning.title",
}
_COMMON_ERROR_MESSAGE_KEYS = {
    "A local filesystem operation failed.": "error.filesystem.message",
    "An internal server error occurred.": "error.internal.message",
    "The request could not be validated.": "error.bad_request.message",
    "This method is not available for the requested page.": (
        "error.method_not_allowed.message"
    ),
    "Not found.": "error.not_found.message",
    "Prepared sources changed.": "error.conflict.message",
    "The selected process-local artifact is stale.": "error.conflict.message",
    "This form is stale. Reload the page and try again.": "error.stale_form.message",
    "The imported SkatMind workflow is not supported on this page.": (
        "error.bad_request.message"
    ),
    "The submitted request is too large.": "error.request_too_large.message",
    "Use the form content type shown by this page.": (
        "error.unsupported_content_type.message"
    ),
    "The submitted form could not be validated.": "error.bad_request.message",
    "Reset the invalid local profile from About before saving a language preference.": (
        "error.profile_invalid.message"
    ),
}


def _is_stateful_get_route(path: str) -> bool:
    return (
        path
        in {
            "/sessions/current",
            "/matches/new",
            "/matches/current",
            "/matches/api/v1/state",
            "/matches/downloads/workspace.json",
            "/learning/current",
            "/learning/api/v1/state",
        }
        or path in _SESSION_DOWNLOAD_ROUTES
        or path in _MATCH_EXPORT_ROUTES
        or path in _LEARNING_DOWNLOAD_ROUTES
        or _MATCH_POSITION_PATTERN.fullmatch(path) is not None
        or _MATCH_REPORT_PATTERN.fullmatch(path) is not None
        or _MATCH_REPORT_JSON_PATTERN.fullmatch(path) is not None
        or _MATCH_REPORT_SOURCE_PATTERN.fullmatch(path) is not None
    )


class SkatMindAppWebServerV1(ThreadingHTTPServer):
    """One loopback-only server for the unified local application shell."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        context: AppWebContextV1,
        *,
        port: int = 0,
        token: str | None = None,
    ) -> None:
        if type(context) is not AppWebContextV1:
            raise ValueError("context must be an exact AppWebContextV1.")
        if type(port) is not int or not 0 <= port <= 65_535:
            raise ValueError("port must be 0 or an integer from 1 through 65535.")
        if token is not None and (
            type(token) is not str
            or not token
            or any(character in token for character in ";\r\n")
        ):
            raise ValueError("token must be null or safe non-empty text.")
        self.app_context = context
        self.app_token = token if token is not None else create_app_web_token_v1()
        super().__init__((APP_WEB_BIND_HOST, port), SkatMindAppWebRequestHandlerV1)

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    @property
    def bootstrap_url(self) -> str:
        token = quote(self.app_token, safe="")
        return f"http://{APP_WEB_BIND_HOST}:{self.port}/?token={token}"

    @property
    def origin(self) -> str:
        return f"http://{APP_WEB_BIND_HOST}:{self.port}"


class SkatMindAppWebRequestHandlerV1(BaseHTTPRequestHandler):
    server: SkatMindAppWebServerV1

    def __getattr__(self, name: str):
        if name.startswith("do_"):
            return self._unsupported_method
        raise AttributeError(name)

    def parse_request(self) -> bool:
        parsed = super().parse_request()
        if parsed and self.request_version == "HTTP/0.9":
            self.request_version = self.protocol_version
            self.send_error(HTTPStatus.HTTP_VERSION_NOT_SUPPORTED)
            return False
        return parsed

    def log_message(self, _format: str, *_args: object) -> None:
        """Disables access logs so bootstrap tokens cannot enter logs."""

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        """Keeps parser-level HTTP failures on the hardened response path."""

        del message, explain
        if self.request_version == "HTTP/0.9":
            self.request_version = self.protocol_version
        self._send_common_error(code)

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
        for name, value in app_web_security_headers_v1():
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

    def _host_is_valid(self) -> bool:
        if len(self.headers.get_all("Host", [])) != 1:
            return False
        return validate_app_web_host_v1(self.headers.get("Host"), self.server.port)

    def _cookie_is_valid(self) -> bool:
        if len(self.headers.get_all("Cookie", [])) != 1:
            return False
        return has_valid_app_web_cookie_v1(
            self.headers.get("Cookie"),
            self.server.app_token,
        )

    def _send_authorization_failure(self) -> None:
        self._send_text(
            HTTPStatus.FORBIDDEN,
            render_authorization_failure_v1(self._frontend_state()),
            content_type="text/html; charset=utf-8",
        )

    def _frontend_state(self):
        request_headers = getattr(self, "headers", None)
        accept_language_values: list[str] = []
        if isinstance(request_headers, Message):
            try:
                candidate_values = request_headers.get_all("Accept-Language", [])
            except Exception:
                # Parser errors may leave an incomplete optional-locale container.
                candidate_values = []
            if type(candidate_values) is list and all(
                type(value) is str for value in candidate_values
            ):
                accept_language_values = candidate_values
        accept_language = (
            accept_language_values[0] if len(accept_language_values) == 1 else None
        )
        with self.server.app_context.lock:
            profile_state = self.server.app_context.frontend_profile
        return project_browser_safe_frontend_profile_state_v1(
            profile_state,
            accept_language=accept_language,
        )

    def _safe_current_return_path(self) -> str:
        raw_path = getattr(self, "path", None)
        if type(raw_path) is not str:
            return "/"
        try:
            path = urlsplit(raw_path).path
        except ValueError:
            return "/"
        return path if is_safe_frontend_return_path_v1(path) else "/"

    def _authorize_get(self, path: str, query: str) -> bool:
        if not self._host_is_valid():
            self._send_authorization_failure()
            return False
        if path == "/" and query:
            try:
                query_values = parse_qs(
                    query,
                    keep_blank_values=True,
                    strict_parsing=True,
                )
            except ValueError:
                query_values = {}
            candidate_tokens = query_values.get("token", [])
            if (
                set(query_values) != {"token"}
                or len(candidate_tokens) != 1
                or not hmac.compare_digest(
                    candidate_tokens[0],
                    self.server.app_token,
                )
            ):
                self._send_authorization_failure()
                return False
            self._send_text(
                HTTPStatus.SEE_OTHER,
                "",
                extra_headers=(
                    ("Location", "/"),
                    ("Set-Cookie", build_app_web_cookie_v1(self.server.app_token)),
                ),
            )
            return False
        if query or not self._cookie_is_valid():
            self._send_authorization_failure()
            return False
        return True

    def _authorize_mutation(self) -> bool:
        if not self._host_is_valid() or not self._cookie_is_valid():
            self._drain_rejected_body()
            self._send_authorization_failure()
            return False
        if len(self.headers.get_all("Origin", [])) != 1 or not validate_app_web_origin_v1(
            self.headers.get("Origin"),
            self.server.port,
            self.headers.get("Host"),
        ):
            self._drain_rejected_body()
            self._send_authorization_failure()
            return False
        return True

    def _drain_rejected_body(self) -> None:
        """Avoids a Windows TCP reset without changing authorization precedence."""

        if self.headers.get_all("Transfer-Encoding", []):
            return
        raw_lengths = self.headers.get_all("Content-Length", [])
        if len(raw_lengths) != 1:
            return
        try:
            length = int(raw_lengths[0])
        except ValueError:
            return
        if 0 <= length <= APP_WEB_MAX_REQUEST_BYTES:
            self.rfile.read(length)

    def _page(self, route: str, *, status: int = HTTPStatus.OK) -> None:
        storage_root = (
            self.server.app_context.managed_home.root if route == "/about" else None
        )
        with self.server.app_context.lock:
            frontend = self._frontend_state()
            rendered = render_app_page_v1(
                self.server.app_context.browser_state,
                route,
                storage_root=storage_root,
                analyze_state=self.server.app_context.analyze_state,
                review_state=self.server.app_context.review_state,
                frontend=frontend,
                return_to=self._safe_current_return_path(),
            )
        self._send_text(
            status,
            rendered,
            content_type="text/html; charset=utf-8",
        )

    def _error_page(
        self,
        status: int,
        title: str,
        message: str,
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        exact_title_key = {
            "Input validation": "error.bad_request.title",
            "Unsupported workflow": "error.unsupported_workflow.title",
        }.get(title)
        if exact_title_key is not None:
            title_key = exact_title_key
        elif title == "Filesystem error":
            title_key = "error.filesystem.title"
        elif status == HTTPStatus.NOT_FOUND:
            title_key = (
                "error.artifact_unavailable.title"
                if title in {"Artifact unavailable", "Download unavailable"}
                else "error.not_found.title"
            )
        elif status == HTTPStatus.CONFLICT:
            title_key = "error.conflict.title"
        elif status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
            title_key = "error.request_too_large.title"
        elif status == HTTPStatus.UNSUPPORTED_MEDIA_TYPE:
            title_key = "error.unsupported_content_type.title"
        elif status == HTTPStatus.METHOD_NOT_ALLOWED:
            title_key = "error.method_not_allowed.title"
        elif status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            title_key = "error.internal.title"
        else:
            title_key = "error.bad_request.title"
        message_key = _COMMON_ERROR_MESSAGE_KEYS.get(message)
        if status == HTTPStatus.NOT_FOUND and title in {
            "Artifact unavailable",
            "Download unavailable",
        }:
            message_key = "error.artifact_unavailable.message"
        self._send_text(
            status,
            render_app_error_page_v1(
                self.server.app_context.browser_state,
                title_key=title_key,
                message=None if message_key is not None else message,
                message_key=message_key,
                frontend=self._frontend_state(),
                return_to=getattr(
                    self,
                    "_profile_action_return_to",
                    self._safe_current_return_path(),
                ),
                untranslated_message=message_key is None,
            ),
            content_type="text/html; charset=utf-8",
            extra_headers=extra_headers,
        )

    def _send_common_error(
        self,
        status: int,
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        title, message = {
            HTTPStatus.BAD_REQUEST: ("Invalid request", "The request could not be validated."),
            HTTPStatus.NOT_FOUND: ("Page not found", "Not found."),
            HTTPStatus.METHOD_NOT_ALLOWED: (
                "Method not allowed",
                "This method is not available for the requested page.",
            ),
            HTTPStatus.CONFLICT: ("State changed", "Prepared sources changed."),
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE: (
                "Upload too large",
                "The submitted request is too large.",
            ),
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE: (
                "Unsupported content type",
                "Use the form content type shown by this page.",
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR: (
                "Internal server error",
                "An internal server error occurred.",
            ),
        }.get(int(status), ("Invalid request", "The request could not be validated."))
        self._error_page(status, title, message, extra_headers=extra_headers)

    def _content_page(
        self,
        route: str,
        *,
        title: str,
        content: str,
        status: int = HTTPStatus.OK,
        extra_stylesheets: tuple[str, ...] = (),
        extra_scripts: tuple[str, ...] = (),
        empty_state_key: str | None = None,
    ) -> None:
        with self.server.app_context.lock:
            state = self.server.app_context.browser_state
            frontend = self._frontend_state()
        title_key = _CONTENT_TITLE_KEYS.get(title)
        rendered = render_app_content_page_v1(
            state,
            route,
            title=None if title_key is not None else title,
            title_key=title_key,
            content=content,
            frontend=frontend,
            return_to=self._safe_current_return_path(),
            empty_state_key=empty_state_key,
            extra_stylesheets=extra_stylesheets,
            extra_scripts=extra_scripts,
        )
        self._send_text(
            status,
            rendered,
            content_type="text/html; charset=utf-8",
        )

    def _read_body(
        self,
        *,
        max_bytes: int = APP_WEB_MAX_REQUEST_BYTES,
    ) -> tuple[bytes, str]:
        if self.headers.get_all("Transfer-Encoding", []):
            raise ValueError("Transfer-Encoding is not supported.")
        raw_lengths = self.headers.get_all("Content-Length", [])
        if len(raw_lengths) != 1:
            raise ValueError("Content-Length is required exactly once.")
        try:
            length = int(raw_lengths[0])
        except ValueError as error:
            raise ValueError("Content-Length must be an integer.") from error
        if length < 0:
            raise ValueError("Content-Length must not be negative.")
        if length > max_bytes:
            raise OverflowError("Request body is too large.")
        content_types = self.headers.get_all("Content-Type", [])
        if len(content_types) != 1:
            raise ValueError("Content-Type is required exactly once.")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Request body ended before Content-Length bytes were read.")
        return body, content_types[0]

    def _flat_form(
        self,
        body: bytes,
        content_type: str,
        *,
        repeated_cards: bool = False,
    ) -> dict[str, str | list[str]]:
        parsed = self._urlencoded_form(body, content_type)
        duplicates = sorted(
            name
            for name, items in parsed.items()
            if len(items) != 1 and not (repeated_cards and name == "cards")
        )
        if duplicates:
            raise ValueError(f"Form fields must not repeat: {', '.join(duplicates)}.")
        return {
            name: items if repeated_cards and name == "cards" and len(items) > 1 else items[0]
            for name, items in parsed.items()
        }

    def _text_form(self, body: bytes, content_type: str) -> dict[str, str]:
        values = self._flat_form(body, content_type)
        if any(type(value) is not str for value in values.values()):
            raise ValueError("Form fields must contain text.")
        return {name: str(value) for name, value in values.items()}

    def _send_json(self, status: int, value: object) -> None:
        content = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        self._send_bytes(
            status,
            content,
            content_type="application/json; charset=utf-8",
        )

    @staticmethod
    def _form_integer(
        values: dict[str, str],
        name: str,
        *,
        minimum: int | None = None,
    ) -> int:
        raw = values.get(name)
        if raw is None or not re.fullmatch(r"-?[0-9]+", raw):
            raise ValueError(f"{name} must be an integer.")
        value = int(raw)
        if minimum is not None and value < minimum:
            raise ValueError(f"{name} must be at least {minimum}.")
        return value

    @staticmethod
    def _exact_fields(values: dict[str, str], fields: set[str]) -> None:
        missing = sorted(fields - set(values))
        unknown = sorted(set(values) - fields)
        if missing:
            raise ValueError(f"Form is missing required fields: {missing}.")
        if unknown:
            raise ValueError(f"Form has unsupported fields: {unknown}.")

    def _read_unsupported_body(self) -> None:
        _body, content_type = self._read_body()
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/x-www-form-urlencoded":
            raise TypeError("Content-Type is not supported.")

    def _urlencoded_form(self, body: bytes, content_type: str) -> dict[str, list[str]]:
        media_type, separator, parameters = content_type.partition(";")
        if media_type.strip().lower() != "application/x-www-form-urlencoded":
            raise TypeError("Content-Type is not supported.")
        if separator and parameters.strip().lower() not in {"charset=utf-8", "charset=\"utf-8\""}:
            raise TypeError("Content-Type is not supported.")
        if body.startswith(b"\xef\xbb\xbf"):
            raise ValueError("Form data must not contain a UTF-8 BOM.")
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Form data must be valid UTF-8.") from error
        if _PERCENT_ESCAPE.search(text):
            raise ValueError("Form data contains an invalid percent escape.")
        try:
            return parse_qs(
                text,
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=256,
                encoding="utf-8",
                errors="strict",
            )
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError("Form data is malformed.") from error

    def _revision(self, values: dict[str, list[str]]) -> int:
        raw = values.pop("revision", None)
        if raw is None or len(raw) != 1 or not raw[0].isascii() or not raw[0].isdecimal():
            raise ValueError("revision must appear exactly once as a non-negative integer.")
        if len(raw[0]) > 1 and raw[0].startswith("0"):
            raise ValueError("revision must not contain leading zeroes.")
        return int(raw[0])

    def _redirect(self, location: str) -> None:
        self._send_text(
            HTTPStatus.SEE_OTHER,
            "",
            extra_headers=(("Location", location),),
        )

    def _profile_operation(self, path: str, body: bytes, content_type: str) -> None:
        values = self._text_form(body, content_type)
        if path == FRONTEND_LANGUAGE_ACTION_ROUTE:
            self._exact_fields(
                values,
                {"language", "profile_generation", "return_to"},
            )
        else:
            self._exact_fields(
                values,
                {"confirm_reset", "profile_generation", "return_to"},
            )
        return_to = values["return_to"]
        if not is_safe_frontend_return_path_v1(return_to):
            raise ValueError("return_to must identify one safe rendered HTML path.")
        self._profile_action_return_to = return_to
        if path == FRONTEND_PROFILE_RESET_ACTION_ROUTE:
            if values["confirm_reset"] != "on":
                raise ValueError("Profile reset requires explicit confirmation.")
        raw_generation = values["profile_generation"]
        if (
            not raw_generation.isascii()
            or not raw_generation.isdecimal()
            or (len(raw_generation) > 1 and raw_generation.startswith("0"))
        ):
            raise ValueError("profile_generation must be a non-negative integer.")
        generation = int(raw_generation)
        if path == FRONTEND_LANGUAGE_ACTION_ROUTE:
            set_frontend_language_v1(
                self.server.app_context,
                language=values["language"],
                expected_generation=generation,
            )
        elif path == FRONTEND_PROFILE_RESET_ACTION_ROUTE:
            reset_frontend_profile_v1(
                self.server.app_context,
                expected_generation=generation,
            )
        else:
            raise RuntimeError("Profile action route dispatch is incomplete.")
        with self.server.app_context.profile_lock:
            self.server.app_context.profile_redirect_return_to = return_to
        self._redirect(return_to)

    def _download(self, path: str) -> None:
        with self.server.app_context.lock:
            if path == ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH:
                content = self.server.app_context.analyze_state.request_json_bytes
                filename = POSITION_REQUEST_DOWNLOAD_FILENAME
            elif path == ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH:
                content = self.server.app_context.analyze_state.result_json_bytes
                filename = POSITION_RESULT_DOWNLOAD_FILENAME
            elif path == REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH:
                content = self.server.app_context.review_state.request_json_bytes
                filename = REVIEW_REQUEST_DOWNLOAD_FILENAME
            else:
                content = self.server.app_context.review_state.result_json_bytes
                filename = REVIEW_RESULT_DOWNLOAD_FILENAME
        if content is None:
            self._error_page(HTTPStatus.NOT_FOUND, "Download unavailable", "Not found.")
            return
        self._send_bytes(
            HTTPStatus.OK,
            content,
            content_type="application/json; charset=utf-8",
            extra_headers=(("Content-Disposition", f'attachment; filename="{filename}"'),),
        )

    def _send_artifact(self, filename: str, content: bytes) -> None:
        if (
            not filename
            or not filename.isascii()
            or any(character in filename for character in '/\\"\r\n')
        ):
            raise ValueError("Artifact filename must be one safe ASCII basename.")
        self._send_bytes(
            HTTPStatus.OK,
            content,
            content_type="application/json; charset=utf-8",
            extra_headers=(
                ("Content-Disposition", f'attachment; filename="{filename}"'),
            ),
        )

    def _refresh_category(self, family: str):
        context = self.server.app_context
        with context.lock:
            root, generation, active_handle = context.managed_stateful.begin_refresh(
                family
            )
        discovery = discover_managed_items_v1(
            root,
            family=family,
            generation=generation,
            active_handle=active_handle,
        )
        with context.lock:
            if context.managed_stateful.publish_refresh(family, discovery):
                return discovery
            current = context.managed_stateful.discoveries.get(family)
        if current is None:
            raise RuntimeError("Managed discovery publication was superseded.")
        return current

    def _activate_session(self, active) -> None:
        with self.server.app_context.lock:
            previous = self.server.app_context.managed_stateful.activate_session(active)
        if previous is not None:
            with previous.lock:
                previous.execution = None

    def _activate_match(self, active) -> None:
        with self.server.app_context.lock:
            previous = self.server.app_context.managed_stateful.activate_match(active)
        if previous is not None:
            with previous.capture.lock:
                previous.capture.report_store.clear()

    def _activate_learning(self, active) -> None:
        with self.server.app_context.lock:
            previous = self.server.app_context.managed_stateful.activate_learning(active)
        if previous is not None:
            previous.corpus.shutdown()

    def _active_session(self):
        with self.server.app_context.lock:
            active = self.server.app_context.managed_stateful.active_session
        if active is None:
            raise KeyError("No managed Session is active.")
        return active

    def _active_match(self):
        with self.server.app_context.lock:
            active = self.server.app_context.managed_stateful.active_match
        if active is None:
            raise KeyError("No managed Match is active.")
        return active

    def _active_learning(self):
        with self.server.app_context.lock:
            active = self.server.app_context.managed_stateful.active_learning
        if active is None:
            raise KeyError("No managed Learning Corpus is active.")
        return active

    def _bound_active(self, family: str, values: dict):
        submitted_handle = values.pop("managed_handle", None)
        with self.server.app_context.lock:
            managed = self.server.app_context.managed_stateful
            if family == "sessions":
                active = managed.active_session
            elif family == "matches":
                active = managed.active_match
            elif family == "corpora":
                active = managed.active_learning
            else:
                raise ValueError("family must identify one managed item family.")
            if active is None:
                raise KeyError("No managed item is active for this form.")
            if submitted_handle != active.handle:
                raise StaleFrontendWorkflowRevisionError
        return active

    def _managed_category_page(self, family: str) -> None:
        route = {
            "sessions": "/sessions",
            "matches": "/matches",
            "corpora": "/learning",
        }[family]
        discovery = None
        if getattr(self, "_profile_return_without_refresh", False):
            with self.server.app_context.lock:
                discovery = self.server.app_context.managed_stateful.discoveries.get(family)
        if discovery is None:
            discovery = self._refresh_category(family)
        title = {
            "sessions": "Sessions",
            "matches": "Match capture",
            "corpora": "Learning & cross-game insights",
        }[family]
        self._content_page(
            route,
            title=title,
            content=render_managed_category_landing_v1(discovery.view),
            empty_state_key=(
                {
                    "sessions": "sessions",
                    "matches": "matches",
                    "corpora": "learning_collections",
                }[family]
                if not discovery.view.items
                else None
            ),
        )

    def _session_page(self, *, status: int = HTTPStatus.OK) -> None:
        active = self._active_session()
        self._content_page(
            "/sessions",
            title="Guided Session",
            content=render_guided_session_v1(active),
            status=status,
        )

    def _match_page(
        self,
        active,
        *,
        position: int,
        report_id: str | None = None,
        status: int = HTTPStatus.OK,
        error_notice: str | None = None,
        operation_notice: str | None = None,
        operation_notice_kind: str = "info",
    ) -> None:
        with active.capture.lock:
            select_unified_match_position_v1(active, position)
            state = build_unified_match_state_v1(
                active,
                selected_report_id=report_id,
            )
            result = active.last_result
            transfer_notice = active.transfer_notice
            active.transfer_notice = None
        notice = (
            operation_notice
            or transfer_notice
            or error_notice
            or (None if result is None else result.message)
        )
        notice_kind = (
            operation_notice_kind
            if operation_notice is not None
            else "info"
            if transfer_notice is not None
            else "error"
            if error_notice is not None
            else "warning"
            if result is not None and result.http_status == HTTPStatus.CONFLICT
            else "info"
        )
        with self.server.app_context.lock:
            learning = self.server.app_context.managed_stateful.active_learning
        learning_state = (
            None if learning is None else build_unified_learning_state_v1(learning)
        )
        transfer = render_match_to_learning_transfer_v1(
            learning_state,
            report_id=report_id,
            target_managed_handle=None if learning is None else learning.handle,
        )
        body = render_match_capture_web_body_v1(
            state,
            route_prefix="/matches",
            notice=notice,
            notice_kind=notice_kind,
            managed_handle=active.handle,
            additional_content=transfer,
        )
        self._content_page(
            "/matches",
            title="Managed Match capture",
            content=body,
            status=status,
            extra_stylesheets=("/matches/assets/capture.css",),
            extra_scripts=("/matches/assets/capture.js",),
        )

    def _match_creation_page(self) -> None:
        body = render_match_capture_web_body_v1(
            build_unified_match_creation_state_v1(),
            route_prefix="/matches",
        )
        self._content_page(
            "/matches",
            title="Create a managed Match",
            content=body,
            extra_stylesheets=("/matches/assets/capture.css",),
            extra_scripts=("/matches/assets/capture.js",),
        )

    def _learning_page(
        self,
        *,
        status: int = HTTPStatus.OK,
        error_notice: str | None = None,
    ) -> None:
        active = self._active_learning()
        state = build_unified_learning_state_v1(active)
        result = active.last_result
        notice = error_notice or (None if result is None else result.message)
        notice_kind = (
            "error"
            if error_notice is not None
            else "warning"
            if result is not None and result.http_status == HTTPStatus.CONFLICT
            else "info"
        )
        body = render_learning_corpus_web_body_v1(
            state,
            route_prefix="/learning",
            notice=notice,
            notice_kind=notice_kind,
            managed_handle=active.handle,
        )
        self._content_page(
            "/learning",
            title="Managed Learning Corpus",
            content=body,
            status=status,
            empty_state_key=(
                "learning_data"
                if isinstance(state.get("matches"), list) and not state["matches"]
                else None
            ),
            extra_stylesheets=("/learning/assets/corpus.css",),
            extra_scripts=("/learning/assets/corpus.js",),
        )

    def _stateful_download(self, path: str) -> bool:
        if path in _SESSION_DOWNLOAD_ROUTES:
            active = self._active_session()
            with active.lock:
                if path.endswith("session.json"):
                    content = build_guided_session_persistence_download_v1(active)
                    filename = "skatmind-managed-session.json"
                elif active.execution is None:
                    raise KeyError("Session execution download is unavailable.")
                elif path.endswith("request.json"):
                    content = active.execution.request_json_bytes
                    filename = "skatmind-session-request.json"
                else:
                    content = active.execution.result_json_bytes
                    filename = "skatmind-session-result.json"
            self._send_artifact(filename, content)
            return True
        report_source = _MATCH_REPORT_SOURCE_PATTERN.fullmatch(path)
        if report_source is not None:
            filename, content = build_unified_match_report_download_v1(
                self._active_match(),
                report_source.group(1),
                strategy_source=True,
            )
            self._send_artifact(filename, content)
            return True
        report_json = _MATCH_REPORT_JSON_PATTERN.fullmatch(path)
        if report_json is not None:
            filename, content = build_unified_match_report_download_v1(
                self._active_match(),
                report_json.group(1),
                strategy_source=False,
            )
            self._send_artifact(filename, content)
            return True
        if path in _MATCH_EXPORT_ROUTES:
            filename, content = build_unified_match_export_download_v1(
                self._active_match(),
                kind=_MATCH_EXPORT_ROUTES[path],
            )
            self._send_artifact(filename, content)
            return True
        if path == "/matches/downloads/workspace.json":
            self._send_artifact(
                "skatmind-managed-match.json",
                build_unified_match_workspace_download_v1(self._active_match()),
            )
            return True
        if path in _LEARNING_DOWNLOAD_ROUTES:
            download = build_unified_learning_download_v1(
                self._active_learning(),
                kind=_LEARNING_DOWNLOAD_ROUTES[path],
            )
            self._send_artifact(download.filename, download.content)
            return True
        return False

    def _stateful_get(self, path: str) -> bool:
        if path == "/sessions":
            self._managed_category_page("sessions")
            return True
        if path == "/matches":
            self._managed_category_page("matches")
            return True
        if path == "/learning":
            self._managed_category_page("corpora")
            return True
        if path == "/sessions/current":
            self._session_page()
            return True
        if path == "/matches/new":
            self._match_creation_page()
            return True
        if path == "/matches/current":
            active = self._active_match()
            self._match_page(active, position=active.selected_position)
            return True
        if path == "/learning/current":
            self._learning_page()
            return True
        position = _MATCH_POSITION_PATTERN.fullmatch(path)
        if position is not None:
            self._match_page(self._active_match(), position=int(position.group(1)))
            return True
        report_page = _MATCH_REPORT_PATTERN.fullmatch(path)
        if report_page is not None:
            active = self._active_match()
            report_id = report_page.group(1)
            report_status, report = get_unified_match_report_v1(active, report_id)
            if report_status == "missing" or report is None:
                raise KeyError("Match Report is unavailable.")
            if report_status == "stale":
                raise RuntimeError("Match Report revision is stale.")
            self._match_page(
                active,
                position=report.match_position or 1,
                report_id=report_id,
            )
            return True
        if path == "/matches/api/v1/state":
            active = self._active_match()
            self._send_json(HTTPStatus.OK, build_unified_match_state_v1(active))
            return True
        if path == "/learning/api/v1/state":
            self._send_json(
                HTTPStatus.OK,
                build_unified_learning_state_v1(self._active_learning()),
            )
            return True
        return self._stateful_download(path)

    def _consume_profile_redirect_return(self, path: str) -> None:
        self._profile_return_without_refresh = False
        if not is_safe_frontend_return_path_v1(path):
            return
        with self.server.app_context.profile_lock:
            return_to = self.server.app_context.profile_redirect_return_to
            if return_to == path:
                self.server.app_context.profile_redirect_return_to = None
                self._profile_return_without_refresh = True

    def _open_managed_item(self, family: str, values: dict[str, str]) -> None:
        self._exact_fields(values, {"handle", "generation"})
        generation = self._form_integer(values, "generation", minimum=1)
        with self.server.app_context.lock:
            entry = self.server.app_context.managed_stateful.resolve(
                family,
                handle=values["handle"],
                generation=generation,
            )
            root = self.server.app_context.managed_stateful.root(family)
        if family == "sessions":
            self._activate_session(open_guided_session_v1(root, entry))
            location = "/sessions/current"
        elif family == "matches":
            self._activate_match(open_unified_match_v1(root, entry))
            location = "/matches/current"
        else:
            self._activate_learning(open_unified_learning_corpus_v1(root, entry))
            location = "/learning/current"
        self._refresh_category(family)
        self._redirect(location)

    def _create_session(self, values: dict[str, str]) -> None:
        fields = {"session_id", "capture_mode", "local_player_id"}
        for index in (1, 2, 3):
            fields.update({f"player_{index}_id", f"player_{index}_label"})
        self._exact_fields(values, fields)
        session_id = values["session_id"]
        storage_name = build_managed_item_storage_name_v1(
            family="sessions",
            product_id=session_id,
        )
        players = build_guided_session_players_v1(values)
        with self.server.app_context.lock:
            root = self.server.app_context.managed_stateful.root("sessions")
        active = create_guided_session_v1(
            root,
            handle=build_managed_item_handle_v1(
                family="sessions",
                basename=storage_name,
            ),
            session_id=session_id,
            players=players,
            capture_mode=values["capture_mode"],
            local_player_id=values["local_player_id"] or None,
        )
        self._activate_session(active)
        self._refresh_category("sessions")
        self._redirect("/sessions/current")

    def _import_session(self, body: bytes, content_type: str) -> None:
        upload = parse_managed_item_json_upload_v1(
            body,
            content_type=content_type,
            expected_file_field="session_file",
        )
        session_id = get_guided_session_import_product_id_v1(upload.document)
        storage_name = build_managed_item_storage_name_v1(
            family="sessions",
            product_id=session_id,
        )
        with self.server.app_context.lock:
            root = self.server.app_context.managed_stateful.root("sessions")
        active = import_guided_session_v1(
            root,
            handle=build_managed_item_handle_v1(
                family="sessions",
                basename=storage_name,
            ),
            document=dict(upload.document),
        )
        self._activate_session(active)
        self._refresh_category("sessions")
        self._redirect("/sessions/current")

    def _session_operation(self, path: str, values: dict[str, str]) -> None:
        active = self._bound_active("sessions", values)
        expected_revision = self._form_integer(
            values,
            "expected_revision",
            minimum=0,
        )
        with active.lock:
            if active.state.revision != expected_revision:
                raise StaleFrontendWorkflowRevisionError
        values = dict(values)
        del values["expected_revision"]
        if path == "/sessions/command":
            edit = build_session_edit_from_form_v1(
                values,
                current_revision=expected_revision,
            )
            apply_guided_session_edit_v1(active, edit)
        elif path == "/sessions/undo":
            self._exact_fields(values, {"target_revision"})
            rewind_guided_session_v1(
                active,
                target_revision=self._form_integer(
                    values,
                    "target_revision",
                    minimum=0,
                ),
            )
        elif path == "/sessions/analyze":
            export_options = build_session_position_options_from_form_v1(values)
            execute_guided_session_position_v1(
                active,
                export_options=export_options,
                execution_options=default_guided_session_execution_options_v1(),
            )
        else:
            execution_options = build_session_historical_execution_options_from_form_v1(
                values
            )
            execute_guided_session_historical_v1(
                active,
                execution_options=execution_options,
            )
        self._redirect("/sessions/current")

    def _create_match(self, values: dict[str, str | list[str]]) -> None:
        match_id = values.get("match_id")
        if type(match_id) is not str:
            raise ValueError("match_id is required as form text.")
        storage_name = build_managed_item_storage_name_v1(
            family="matches",
            product_id=match_id,
        )
        with self.server.app_context.lock:
            root = self.server.app_context.managed_stateful.root("matches")
        active = create_unified_match_v1(
            root,
            handle=build_managed_item_handle_v1(
                family="matches",
                basename=storage_name,
            ),
            values=values,
        )
        self._activate_match(active)
        self._refresh_category("matches")
        self._redirect("/matches/position/1")

    def _import_match(self, body: bytes, content_type: str) -> None:
        upload = parse_managed_item_json_upload_v1(
            body,
            content_type=content_type,
            expected_file_field="workspace_file",
        )
        resumed = resume_match_workspace_document_v1(upload.document).document
        match_id = resumed.workspace.match_definition.match_id
        storage_name = build_managed_item_storage_name_v1(
            family="matches",
            product_id=match_id,
        )
        with self.server.app_context.lock:
            root = self.server.app_context.managed_stateful.root("matches")
        active = import_unified_match_v1(
            root,
            handle=build_managed_item_handle_v1(
                family="matches",
                basename=storage_name,
            ),
            document=upload.document,
        )
        self._activate_match(active)
        self._refresh_category("matches")
        self._redirect("/matches/current")

    def _match_operation(
        self,
        path: str,
        values: dict[str, str | list[str]],
    ) -> None:
        active = self._bound_active("matches", values)
        if path.endswith("/reload"):
            if set(values) - {"match_position"}:
                raise ValueError("Reload accepts only match_position.")
            position = int(values.get("match_position", "1"))
            select_unified_match_position_v1(active, position)
            result = reload_unified_match_v1(active)
        elif path.endswith("/analysis"):
            result = execute_unified_match_analysis_v1(active, values)
        else:
            result = apply_unified_match_operation_v1(active, values)
        selected = result.state.get("selected_position", active.selected_position)
        position = selected if type(selected) is int and 1 <= selected <= 36 else 1
        if result.http_status == HTTPStatus.OK:
            if path.endswith("/analysis"):
                report_id = result.state.get("selected_report_id")
                if type(report_id) is not str:
                    raise SkatMindInvariantError("Applied analysis did not retain a Report.")
                self._redirect(f"/matches/reports/{report_id}")
            else:
                self._redirect(f"/matches/position/{position}")
            return
        self._match_page(
            active,
            position=position,
            status=result.http_status,
        )

    def _transfer_match(self, path: str, values: dict[str, str]) -> None:
        source_handle = values.pop("managed_handle", None)
        target_handle = values.pop("target_managed_handle", None)
        with self.server.app_context.lock:
            source = self.server.app_context.managed_stateful.active_match
            target = self.server.app_context.managed_stateful.active_learning
            if source is None or target is None:
                raise ValueError("Open both a managed Match and Learning Corpus first.")
            if source_handle != source.handle or target_handle != target.handle:
                raise StaleFrontendWorkflowRevisionError
        if path.endswith("transfer-workspace"):
            self._exact_fields(
                values,
                {
                    "selection_mode",
                    "same_revision_resolution",
                    "expected_catalog_revision",
                },
            )
            result = transfer_active_match_workspace_to_corpus_v1(
                source,
                target,
                selection_mode=values["selection_mode"],
                same_revision_resolution=values["same_revision_resolution"],
                expected_catalog_revision=self._form_integer(
                    values,
                    "expected_catalog_revision",
                    minimum=0,
                ),
            )
            report_id = None
        else:
            self._exact_fields(values, {"report_id", "match_snapshot_id"})
            result = transfer_active_match_report_to_corpus_v1(
                source,
                target,
                report_id=values["report_id"],
                match_snapshot_id=values["match_snapshot_id"],
            )
            report_id = values["report_id"]
        target_result = target.last_result
        status = HTTPStatus.OK if target_result is None else target_result.http_status
        if status == HTTPStatus.OK:
            with source.capture.lock:
                source.transfer_notice = result.message
            location = (
                f"/matches/position/{source.selected_position}"
                if report_id is None
                else f"/matches/reports/{report_id}"
            )
            self._redirect(location)
            return
        self._match_page(
            source,
            position=source.selected_position,
            report_id=report_id,
            status=status,
            operation_notice=result.message,
            operation_notice_kind="warning" if status == HTTPStatus.CONFLICT else "info",
        )

    def _create_learning(self, values: dict[str, str]) -> None:
        self._exact_fields(values, {"corpus_id"})
        corpus_id = values["corpus_id"]
        storage_name = build_managed_item_storage_name_v1(
            family="corpora",
            product_id=corpus_id,
        )
        with self.server.app_context.lock:
            root = self.server.app_context.managed_stateful.root("corpora")
        active = create_unified_learning_corpus_v1(
            root,
            handle=build_managed_item_handle_v1(
                family="corpora",
                basename=storage_name,
            ),
            corpus_id=corpus_id,
        )
        self._activate_learning(active)
        self._refresh_category("corpora")
        self._redirect("/learning/current")

    def _learning_operation(
        self,
        body: bytes,
        content_type: str,
    ) -> None:
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type == "multipart/form-data":
            upload = parse_learning_corpus_multipart_upload_v1(
                body,
                content_type=content_type,
            )
            fields = dict(upload.fields)
            active = self._bound_active("corpora", fields)
            operation = fields.get("operation")
            if operation == "import_match_workspace":
                expected = {
                    "operation",
                    "selection_mode",
                    "same_revision_resolution",
                    "expected_catalog_revision",
                }
                if set(fields) != expected or upload.file_field != "workspace_file":
                    raise ValueError("Workspace import fields are incomplete or unsupported.")
                import_workspace_bytes_into_unified_learning_v1(
                    active,
                    upload.file_content,
                    selection_mode=fields["selection_mode"],
                    same_revision_resolution=fields["same_revision_resolution"],
                    expected_catalog_revision=int(
                        fields["expected_catalog_revision"]
                    ),
                )
            elif operation == "import_strategy_teacher_report":
                expected = {"operation", "match_snapshot_id"}
                if (
                    set(fields) != expected
                    or upload.file_field != "report_source_file"
                ):
                    raise ValueError("Report-source import fields are incomplete or unsupported.")
                import_report_source_bytes_into_unified_learning_v1(
                    active,
                    upload.file_content,
                    match_snapshot_id=fields["match_snapshot_id"],
                )
            else:
                raise ValueError("Multipart operation is not supported.")
        else:
            values = self._text_form(body, content_type)
            active = self._bound_active("corpora", values)
            operation = values.get("operation")
            if operation == "reload_corpus":
                self._exact_fields(values, {"operation"})
                reload_unified_learning_corpus_v1(active)
            elif operation == "select_current_snapshot":
                self._exact_fields(
                    values,
                    {
                        "operation",
                        "match_id",
                        "match_snapshot_id",
                        "expected_catalog_revision",
                    },
                )
                select_unified_learning_current_snapshot_v1(
                    active,
                    match_id=values["match_id"],
                    match_snapshot_id=values["match_snapshot_id"],
                    expected_catalog_revision=self._form_integer(
                        values,
                        "expected_catalog_revision",
                        minimum=0,
                    ),
                )
            elif operation == "remove_strategy_teacher_report":
                self._exact_fields(values, {"operation", "source_binding_id"})
                remove_unified_learning_report_source_v1(
                    active,
                    source_binding_id=values["source_binding_id"],
                )
            elif operation == "clear_strategy_teacher_reports":
                self._exact_fields(values, {"operation"})
                clear_unified_learning_report_sources_v1(active)
            elif operation == "prepare_learning_artifacts":
                self._exact_fields(
                    values,
                    {
                        "operation",
                        "dataset_id",
                        "known_player_seed",
                        "unseen_player_seed",
                        "train_weight",
                        "validation_weight",
                        "test_weight",
                    },
                )
                prepare_unified_learning_artifacts_v1(
                    active,
                    dataset_id=values["dataset_id"],
                    known_player_seed=self._form_integer(values, "known_player_seed"),
                    unseen_player_seed=self._form_integer(values, "unseen_player_seed"),
                    train_weight=self._form_integer(values, "train_weight", minimum=1),
                    validation_weight=self._form_integer(
                        values,
                        "validation_weight",
                        minimum=1,
                    ),
                    test_weight=self._form_integer(values, "test_weight", minimum=1),
                )
            else:
                raise ValueError("Learning operation is not supported.")
        result = active.last_result
        self._learning_page(
            status=HTTPStatus.OK if result is None else result.http_status,
        )

    def _stateful_post(
        self,
        path: str,
        body: bytes,
        content_type: str,
    ) -> None:
        if path == "/sessions/import":
            self._import_session(body, content_type)
            return
        if path == "/matches/import":
            self._import_match(body, content_type)
            return
        if path == "/learning/api/v1/operations":
            self._learning_operation(body, content_type)
            return
        if path in {
            "/matches/api/v1/reload",
            "/matches/api/v1/operation",
            "/matches/api/v1/analysis",
        }:
            self._match_operation(
                path,
                self._flat_form(body, content_type, repeated_cards=True),
            )
            return
        values = self._text_form(body, content_type)
        if path == "/sessions/create":
            self._create_session(values)
        elif path == "/sessions/open":
            self._open_managed_item("sessions", values)
        elif path == "/sessions/reload":
            active = self._bound_active("sessions", values)
            if values:
                raise ValueError("Session reload accepts only its managed handle.")
            reload_guided_session_v1(active)
            self._redirect("/sessions/current")
        elif path.startswith("/sessions/"):
            self._session_operation(path, values)
        elif path == "/matches/open":
            self._open_managed_item("matches", values)
        elif path == "/matches/api/v1/create":
            self._create_match(values)
        elif path.startswith("/matches/transfer-"):
            self._transfer_match(path, values)
        elif path == "/learning/create":
            self._create_learning(values)
        elif path == "/learning/open":
            self._open_managed_item("corpora", values)
        else:
            raise RuntimeError("Stateful POST route dispatch is incomplete.")

    def do_GET(self) -> None:
        try:
            try:
                parsed = urlsplit(self.path)
            except ValueError:
                self._send_common_error(HTTPStatus.BAD_REQUEST)
                return
            if not self._authorize_get(parsed.path, parsed.query):
                return
            if parsed.path in _ASSETS:
                package, resource_name, content_type = _ASSETS[parsed.path]
                content = files(package).joinpath(resource_name).read_bytes()
                self._send_bytes(HTTPStatus.OK, content, content_type=content_type)
                return
            if parsed.path in _STATEFUL_POST_ROUTES:
                self._send_common_error(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    extra_headers=(("Allow", "POST"),),
                )
                return
            if parsed.path in FRONTEND_PROFILE_ACTION_ROUTES:
                self._send_common_error(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    extra_headers=(("Allow", "POST"),),
                )
                return
            self._consume_profile_redirect_return(parsed.path)
            if self._stateful_get(parsed.path):
                return
            if "/assets/" in parsed.path:
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            if parsed.path in GUIDED_DOWNLOAD_ROUTE_PATHS:
                self._download(parsed.path)
                return
            if parsed.path in GUIDED_ACTION_ROUTE_PATHS:
                self._send_common_error(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    extra_headers=(("Allow", "POST"),),
                )
                return
            if parsed.path not in APP_ROUTE_PATHS:
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            self._page(parsed.path)
        except KeyError:
            self._error_page(HTTPStatus.NOT_FOUND, "Artifact unavailable", "Not found.")
        except LearningCorpusPreparedDownloadUnavailableError as error:
            status = (
                HTTPStatus.NOT_FOUND
                if error.reason == "missing"
                else HTTPStatus.CONFLICT
            )
            self._error_page(status, "Artifact unavailable", "Prepared sources changed.")
        except RuntimeError as error:
            if "stale" in str(error).lower():
                self._error_page(
                    HTTPStatus.CONFLICT,
                    "State changed",
                    "The selected process-local artifact is stale.",
                )
            else:
                self._send_common_error(HTTPStatus.INTERNAL_SERVER_ERROR)
        except Exception:
            self._send_common_error(HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        try:
            try:
                parsed = urlsplit(self.path)
            except ValueError:
                self._send_common_error(HTTPStatus.BAD_REQUEST)
                return
            if not self._authorize_mutation():
                return
            if parsed.query:
                self._send_authorization_failure()
                return
            if parsed.path in FRONTEND_PROFILE_ACTION_ROUTES:
                body, content_type = self._read_body()
                self._profile_operation(parsed.path, body, content_type)
                return
            if parsed.path in _STATEFUL_POST_ROUTES:
                if parsed.path in {"/sessions/import", "/matches/import"}:
                    max_bytes = _MANAGED_IMPORT_MAX_REQUEST_BYTES
                elif parsed.path == "/learning/api/v1/operations":
                    max_bytes = LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES
                elif parsed.path.startswith("/matches/api/v1/"):
                    max_bytes = MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES
                else:
                    max_bytes = APP_WEB_MAX_REQUEST_BYTES
                body, content_type = self._read_body(max_bytes=max_bytes)
                self._stateful_post(parsed.path, body, content_type)
                return
            if parsed.path not in GUIDED_ACTION_ROUTE_PATHS:
                if (
                    parsed.path in APP_ROUTE_PATHS
                    or parsed.path in _ASSETS
                    or parsed.path in GUIDED_DOWNLOAD_ROUTE_PATHS
                    or _is_stateful_get_route(parsed.path)
                ):
                    self._read_unsupported_body()
                    self._send_common_error(
                        HTTPStatus.METHOD_NOT_ALLOWED,
                        extra_headers=(("Allow", "GET"),),
                    )
                else:
                    self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return

            body, content_type = self._read_body()
            page = "analyze" if parsed.path in ANALYZE_ACTION_ROUTE_PATHS else "review"
            redirect = "/analyze" if page == "analyze" else "/review"
            if parsed.path in {
                ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
                REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
            }:
                if content_type.split(";", 1)[0].strip().lower() != "multipart/form-data":
                    raise TypeError("Content-Type is not supported.")
                imported = parse_frontend_json_import_v1(
                    body,
                    content_type=content_type,
                    page=page,
                )
                if not imported.revision.isascii() or not imported.revision.isdecimal():
                    raise ValueError("revision must be a non-negative integer.")
                if len(imported.revision) > 1 and imported.revision.startswith("0"):
                    raise ValueError("revision must not contain leading zeroes.")
                expected_revision = int(imported.revision)
                store_frontend_import_v1(
                    self.server.app_context,
                    page=page,
                    expected_revision=expected_revision,
                    imported=imported,
                )
                self._redirect(redirect)
                return

            values = self._urlencoded_form(body, content_type)
            expected_revision = self._revision(values)
            if parsed.path == ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH:
                run_guided_analyze_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                    values=values,
                )
            elif parsed.path == ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH:
                if values:
                    raise ValueError("Run imported accepts only the revision.")
                run_imported_request_v1(
                    self.server.app_context,
                    page="analyze",
                    expected_revision=expected_revision,
                )
            elif parsed.path == ANALYZE_RESET_ACTION_ROUTE_PATH:
                if values != {"confirm_reset": ["on"]}:
                    raise ValueError("Reset requires explicit confirmation.")
                reset_workflow_v1(
                    self.server.app_context,
                    page="analyze",
                    expected_revision=expected_revision,
                )
            elif parsed.path == REVIEW_START_ACTION_ROUTE_PATH:
                if values:
                    raise ValueError("Start accepts only the revision.")
                start_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                )
            elif parsed.path == REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH:
                update_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                    operation="players",
                    values=values,
                )
            elif parsed.path == REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH:
                update_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                    operation="deal",
                    values=values,
                )
            elif parsed.path == REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH:
                update_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                    operation="declaration",
                    values=values,
                )
            elif parsed.path == REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH:
                update_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                    operation="discards",
                    values=values,
                )
            elif parsed.path == REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH:
                update_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                    operation="play",
                    values=values,
                )
            elif parsed.path == REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH:
                if values:
                    raise ValueError("Undo accepts only the revision.")
                undo_review_play_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                )
            elif parsed.path == REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH:
                update_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                    operation="options",
                    values=values,
                )
            elif parsed.path == REVIEW_BACK_ACTION_ROUTE_PATH:
                if values:
                    raise ValueError("Back accepts only the revision.")
                back_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                )
            elif parsed.path == REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH:
                if values:
                    raise ValueError("Run guided accepts only the revision.")
                run_guided_review_v1(
                    self.server.app_context,
                    expected_revision=expected_revision,
                )
            elif parsed.path == REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH:
                if values:
                    raise ValueError("Run imported accepts only the revision.")
                run_imported_request_v1(
                    self.server.app_context,
                    page="review",
                    expected_revision=expected_revision,
                )
            elif parsed.path == REVIEW_RESET_ACTION_ROUTE_PATH:
                if values != {"confirm_reset": ["on"]}:
                    raise ValueError("Reset requires explicit confirmation.")
                reset_workflow_v1(
                    self.server.app_context,
                    page="review",
                    expected_revision=expected_revision,
                )
            else:
                raise RuntimeError("Guided action route dispatch is incomplete.")
            self._redirect(redirect)
        except (
            FrontendWorkflowExecutionConflictError,
            StaleFrontendWorkflowRevisionError,
            StaleFrontendProfileGenerationError,
            FrontendProfilePersistenceConflictError,
        ):
            self._error_page(
                HTTPStatus.CONFLICT,
                "Form conflict",
                "This form is stale. Reload the page and try again.",
            )
        except InvalidFrontendProfileResetRequiredError:
            self._error_page(
                HTTPStatus.CONFLICT,
                "State changed",
                "Reset the invalid local profile from About before saving a language preference.",
            )
        except FrontendWorkflowValidationError:
            page = (
                "/analyze"
                if urlsplit(self.path).path in ANALYZE_ACTION_ROUTE_PATHS
                else "/review"
            )
            self._page(page, status=HTTPStatus.BAD_REQUEST)
        except SkatMindWorkflowError as error:
            if urlsplit(self.path).path in _STATEFUL_POST_ROUTES:
                self._error_page(
                    HTTPStatus.BAD_REQUEST,
                    "Unsupported workflow",
                    str(error),
                )
                return
            self._error_page(
                HTTPStatus.BAD_REQUEST,
                "Unsupported workflow",
                "The imported SkatMind workflow is not supported on this page.",
            )
        except OverflowError:
            self._error_page(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "Upload too large",
                "The submitted request is too large.",
            )
        except TypeError:
            self._error_page(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Unsupported content type",
                "Use the form content type shown by this page.",
            )
        except FileExistsError as error:
            self._error_page(
                HTTPStatus.CONFLICT,
                "Managed item already exists",
                str(error),
            )
        except SkatMindInvariantError:
            self._send_common_error(HTTPStatus.INTERNAL_SERVER_ERROR)
        except (SkatMindError, ValueError) as error:
            path = urlsplit(self.path).path
            if path in _STATEFUL_POST_ROUTES and path.startswith("/matches/"):
                try:
                    active = self._active_match()
                    self._match_page(
                        active,
                        position=active.selected_position,
                        status=HTTPStatus.BAD_REQUEST,
                        error_notice=str(error),
                    )
                    return
                except KeyError:
                    pass
            if path in _STATEFUL_POST_ROUTES and path.startswith("/learning/"):
                try:
                    self._learning_page(
                        status=HTTPStatus.BAD_REQUEST,
                        error_notice=str(error),
                    )
                    return
                except KeyError:
                    pass
            self._error_page(
                HTTPStatus.BAD_REQUEST,
                "Input validation",
                (
                    str(error)
                    if path in _STATEFUL_POST_ROUTES
                    else "The submitted form could not be validated."
                ),
            )
        except OSError:
            self._error_page(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Filesystem error",
                "A local filesystem operation failed.",
            )
        except Exception:
            self._send_common_error(HTTPStatus.INTERNAL_SERVER_ERROR)

    def _unsupported_method(self) -> None:
        try:
            parsed = urlsplit(self.path)
            method = self.command
            if method in _MUTATION_METHODS:
                if not self._authorize_mutation():
                    return
            elif not self._host_is_valid() or not self._cookie_is_valid():
                self._send_authorization_failure()
                return
            if parsed.query:
                self._send_authorization_failure()
                return
            known_paths = (
                set(APP_ROUTE_PATHS)
                | set(_ASSETS)
                | set(GUIDED_ACTION_ROUTE_PATHS)
                | set(GUIDED_DOWNLOAD_ROUTE_PATHS)
                | set(_STATEFUL_POST_ROUTES)
                | set(FRONTEND_PROFILE_ACTION_ROUTES)
            )
            if parsed.path not in known_paths and not _is_stateful_get_route(parsed.path):
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            if method in _BODY_METHODS:
                self._read_unsupported_body()
            allow = (
                "POST"
                if parsed.path in GUIDED_ACTION_ROUTE_PATHS
                or parsed.path in _STATEFUL_POST_ROUTES
                or parsed.path in FRONTEND_PROFILE_ACTION_ROUTES
                else "GET"
            )
            self._send_common_error(
                HTTPStatus.METHOD_NOT_ALLOWED,
                extra_headers=(("Allow", allow),),
            )
        except OverflowError:
            self._send_common_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        except TypeError:
            self._send_common_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        except ValueError:
            self._send_common_error(HTTPStatus.BAD_REQUEST)
        except Exception:
            self._send_common_error(HTTPStatus.INTERNAL_SERVER_ERROR)

    do_CONNECT = _unsupported_method
    do_DELETE = _unsupported_method
    do_HEAD = _unsupported_method
    do_OPTIONS = _unsupported_method
    do_PATCH = _unsupported_method
    do_PUT = _unsupported_method
    do_TRACE = _unsupported_method


def start_app_web_server_v1(
    context: AppWebContextV1,
    *,
    port: int = 0,
    token: str | None = None,
) -> SkatMindAppWebServerV1:
    return SkatMindAppWebServerV1(context, port=port, token=token)


def serve_app_web_in_thread_v1(server: SkatMindAppWebServerV1) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
