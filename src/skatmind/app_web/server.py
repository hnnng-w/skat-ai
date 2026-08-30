from __future__ import annotations

import hmac
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, quote, urlsplit

from .context import AppWebContextV1
from .contracts import APP_ROUTE_PATHS
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

APP_WEB_MAX_REQUEST_BYTES = 1_048_576

_ASSETS = {
    "/assets/app.css": ("assets/app.css", "text/css; charset=utf-8"),
}
_BODY_METHODS = {"POST", "PUT", "PATCH"}
_MUTATION_METHODS = _BODY_METHODS | {"DELETE"}


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

    def log_message(self, _format: str, *_args: object) -> None:
        """Disables access logs so bootstrap tokens cannot enter logs."""

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

    def _page(self, route: str) -> None:
        storage_root = (
            self.server.app_context.managed_home.root if route == "/about" else None
        )
        self._send_text(
            HTTPStatus.OK,
            render_app_page_v1(
                self.server.app_context.browser_state,
                route,
                storage_root=storage_root,
            ),
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

    def _read_unsupported_body(self) -> None:
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
        media_type = content_types[0].split(";", 1)[0].strip().lower()
        if media_type != "application/x-www-form-urlencoded":
            raise TypeError("Content-Type is not supported.")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Request body ended before Content-Length bytes were read.")

    def do_GET(self) -> None:
        try:
            parsed = urlsplit(self.path)
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
            if parsed.path not in APP_ROUTE_PATHS:
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            self._page(parsed.path)
        except OSError:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Filesystem error")
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
            if parsed.path not in APP_ROUTE_PATHS and parsed.path not in _ASSETS:
                self._error_page(HTTPStatus.NOT_FOUND, "Page not found", "Not found.")
                return
            if method in _BODY_METHODS:
                self._read_unsupported_body()
            self._send_text(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "Method not allowed",
                extra_headers=(("Allow", "GET"),),
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
    do_POST = _unsupported_method
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
