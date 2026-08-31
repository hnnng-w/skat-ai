from __future__ import annotations

import hmac
import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, quote, urlsplit

from skatmind.errors import SkatMindWorkflowError

from .context import AppWebContextV1
from .contracts import APP_ROUTE_PATHS
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
from .rendering import render_app_error_page_v1, render_app_page_v1
from .security import (
    APP_WEB_BIND_HOST,
    app_web_security_headers_v1,
    build_app_web_cookie_v1,
    create_app_web_token_v1,
    has_valid_app_web_cookie_v1,
    validate_app_web_host_v1,
    validate_app_web_origin_v1,
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

_ASSETS = {
    "/assets/app.css": ("assets/app.css", "text/css; charset=utf-8"),
}
_BODY_METHODS = {"POST", "PUT", "PATCH"}
_MUTATION_METHODS = _BODY_METHODS | {"DELETE"}
_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


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
        self._send_text(code, "Invalid request")

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

    def _authorize_get(self, path: str, query: str) -> bool:
        if not self._host_is_valid():
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
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
                self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
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
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        return True

    def _authorize_mutation(self) -> bool:
        if not self._host_is_valid() or not self._cookie_is_valid():
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        if len(self.headers.get_all("Origin", [])) != 1 or not validate_app_web_origin_v1(
            self.headers.get("Origin"),
            self.server.port,
            self.headers.get("Host"),
        ):
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        return True

    def _page(self, route: str, *, status: int = HTTPStatus.OK) -> None:
        storage_root = (
            self.server.app_context.managed_home.root if route == "/about" else None
        )
        with self.server.app_context.lock:
            rendered = render_app_page_v1(
                self.server.app_context.browser_state,
                route,
                storage_root=storage_root,
                analyze_state=self.server.app_context.analyze_state,
                review_state=self.server.app_context.review_state,
            )
        self._send_text(
            status,
            rendered,
            content_type="text/html; charset=utf-8",
        )

    def _error_page(self, status: int, title: str, message: str) -> None:
        self._send_text(
            status,
            render_app_error_page_v1(
                self.server.app_context.browser_state,
                title=title,
                message=message,
            ),
            content_type="text/html; charset=utf-8",
        )

    def _read_body(self) -> tuple[bytes, str]:
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
        if length > APP_WEB_MAX_REQUEST_BYTES:
            raise OverflowError("Request body is too large.")
        content_types = self.headers.get_all("Content-Type", [])
        if len(content_types) != 1:
            raise ValueError("Content-Type is required exactly once.")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Request body ended before Content-Length bytes were read.")
        return body, content_types[0]

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

    def do_GET(self) -> None:
        try:
            try:
                parsed = urlsplit(self.path)
            except ValueError:
                self._send_text(HTTPStatus.BAD_REQUEST, "Invalid request")
                return
            if not self._authorize_get(parsed.path, parsed.query):
                return
            if parsed.path in _ASSETS:
                resource_name, content_type = _ASSETS[parsed.path]
                content = files("skatmind.app_web").joinpath(resource_name).read_bytes()
                self._send_bytes(HTTPStatus.OK, content, content_type=content_type)
                return
            if parsed.path.startswith("/assets/"):
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            if parsed.path in GUIDED_DOWNLOAD_ROUTE_PATHS:
                self._download(parsed.path)
                return
            if parsed.path in GUIDED_ACTION_ROUTE_PATHS:
                self._send_text(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "Method not allowed",
                    extra_headers=(("Allow", "POST"),),
                )
                return
            if parsed.path not in APP_ROUTE_PATHS:
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            self._page(parsed.path)
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def do_POST(self) -> None:
        try:
            parsed = urlsplit(self.path)
            if not self._authorize_mutation():
                return
            if parsed.query:
                self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
                return
            if parsed.path not in GUIDED_ACTION_ROUTE_PATHS:
                if (
                    parsed.path in APP_ROUTE_PATHS
                    or parsed.path in _ASSETS
                    or parsed.path in GUIDED_DOWNLOAD_ROUTE_PATHS
                ):
                    self._read_unsupported_body()
                    self._send_text(
                        HTTPStatus.METHOD_NOT_ALLOWED,
                        "Method not allowed",
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
        ):
            self._error_page(
                HTTPStatus.CONFLICT,
                "Form conflict",
                "This form is stale. Reload the page and try again.",
            )
        except FrontendWorkflowValidationError:
            page = (
                "/analyze"
                if urlsplit(self.path).path in ANALYZE_ACTION_ROUTE_PATHS
                else "/review"
            )
            self._page(page, status=HTTPStatus.BAD_REQUEST)
        except SkatMindWorkflowError:
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
        except ValueError:
            self._error_page(
                HTTPStatus.BAD_REQUEST,
                "Input validation",
                "The submitted form could not be validated.",
            )
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def _unsupported_method(self) -> None:
        try:
            parsed = urlsplit(self.path)
            method = self.command
            if method in _MUTATION_METHODS:
                if not self._authorize_mutation():
                    return
            elif not self._host_is_valid() or not self._cookie_is_valid():
                self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
                return
            if parsed.query:
                self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
                return
            known_paths = (
                set(APP_ROUTE_PATHS)
                | set(_ASSETS)
                | set(GUIDED_ACTION_ROUTE_PATHS)
                | set(GUIDED_DOWNLOAD_ROUTE_PATHS)
            )
            if parsed.path not in known_paths:
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            if method in _BODY_METHODS:
                self._read_unsupported_body()
            allow = "POST" if parsed.path in GUIDED_ACTION_ROUTE_PATHS else "GET"
            self._send_text(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "Method not allowed",
                extra_headers=(("Allow", allow),),
            )
        except OverflowError:
            self._send_text(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body is too large")
        except TypeError:
            self._send_text(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Unsupported content type")
        except ValueError:
            self._send_text(HTTPStatus.BAD_REQUEST, "Invalid request")
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

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
