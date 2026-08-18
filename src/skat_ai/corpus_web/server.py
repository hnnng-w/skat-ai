from __future__ import annotations

import json
import re
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from skat_ai.errors import SkatAIError, SkatAIInvariantError
from skat_ai.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skat_ai.match_analysis_report_source_codec import (
    resume_match_analysis_report_source_export_v1,
)

from .context import LearningCorpusWebContextV1
from .contracts import LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES
from .downloads import (
    LearningCorpusPreparedDownloadUnavailableError,
    build_learning_corpus_prepared_download_v1,
)
from .operations import (
    clear_strategy_teacher_reports_from_learning_corpus_web_v1,
    import_match_workspace_into_learning_corpus_web_v1,
    import_strategy_teacher_report_into_learning_corpus_web_v1,
    initialize_learning_corpus_web_v1,
    reload_learning_corpus_web_v1,
    remove_strategy_teacher_report_from_learning_corpus_web_v1,
    select_current_learning_corpus_snapshot_web_v1,
)
from .preparation import prepare_learning_corpus_artifacts_web_v1
from .rendering import render_learning_corpus_web_page_v1
from .security import (
    LEARNING_CORPUS_WEB_BIND_HOST,
    build_learning_corpus_web_cookie_v1,
    create_learning_corpus_web_token_v1,
    has_valid_learning_corpus_web_cookie_v1,
    learning_corpus_web_security_headers_v1,
    validate_learning_corpus_web_host_v1,
    validate_learning_corpus_web_origin_v1,
)
from .state import build_learning_corpus_web_state_v1
from .uploads import (
    LearningCorpusMultipartUploadV1,
    decode_learning_corpus_uploaded_json_v1,
    parse_learning_corpus_multipart_upload_v1,
)

_ASSETS = {
    "/assets/corpus.css": ("assets/corpus.css", "text/css; charset=utf-8"),
    "/assets/corpus.js": ("assets/corpus.js", "text/javascript; charset=utf-8"),
}
_POST_ROUTE = "/api/v1/operations"
_STATE_ROUTE = "/api/v1/state"
_DOWNLOAD_ROUTES = {
    "/downloads/player-catalog.json": "player_catalog",
    "/downloads/human-evidence.json": "human_evidence",
    "/downloads/strategy-teacher-evidence.json": "strategy_teacher_evidence",
    "/downloads/learning-dataset-v2.json": "learning_dataset_v2",
    "/downloads/known-player-partitions.json": "known_player_partitions",
    "/downloads/unseen-player-partitions.json": "unseen_player_partitions",
    "/downloads/cross-game-summary.json": "cross_game_summary",
}
_FORM_OPERATIONS = {
    "initialize_corpus": {"operation", "corpus_id"},
    "reload_corpus": {"operation"},
    "select_current_snapshot": {
        "operation",
        "match_id",
        "match_snapshot_id",
        "expected_catalog_revision",
    },
    "remove_strategy_teacher_report": {"operation", "source_binding_id"},
    "clear_strategy_teacher_reports": {"operation"},
    "prepare_learning_artifacts": {
        "operation",
        "dataset_id",
        "known_player_seed",
        "unseen_player_seed",
        "train_weight",
        "validation_weight",
        "test_weight",
    },
}
_UPLOAD_OPERATIONS = {
    "import_match_workspace": (
        "workspace_file",
        {
            "operation",
            "selection_mode",
            "same_revision_resolution",
            "expected_catalog_revision",
        },
    ),
    "import_strategy_teacher_report": (
        "report_source_file",
        {"operation", "match_snapshot_id"},
    ),
}


def _integer(values: Mapping[str, str], name: str) -> int:
    value = values.get(name)
    if value is None or not re.fullmatch(r"-?[0-9]+", value):
        raise ValueError(f"{name} must be an integer.")
    return int(value)


def _text(values: Mapping[str, str], name: str) -> str:
    value = values.get(name)
    if value is None or not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty, non-padded text.")
    return value


def _require_fields(values: Mapping[str, str], expected: set[str]) -> None:
    missing = sorted(expected - set(values))
    unknown = sorted(set(values) - expected)
    if missing:
        raise ValueError("Missing form fields: " + ", ".join(missing) + ".")
    if unknown:
        raise ValueError("Unsupported form fields: " + ", ".join(unknown) + ".")


class LearningCorpusWebServerV1(ThreadingHTTPServer):
    """One loopback-only server for one explicit Learning Corpus root."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        context: LearningCorpusWebContextV1,
        *,
        port: int = 8766,
        token: str | None = None,
    ) -> None:
        if type(context) is not LearningCorpusWebContextV1:
            raise ValueError("context must be an exact LearningCorpusWebContextV1.")
        if type(port) is not int or not 0 <= port <= 65_535:
            raise ValueError("port must be 0 or an integer from 1 through 65535.")
        self.corpus_context = context
        self.corpus_token = token or create_learning_corpus_web_token_v1()
        self.corpus_notice: tuple[str, str] | None = None
        super().__init__(
            (LEARNING_CORPUS_WEB_BIND_HOST, port),
            LearningCorpusWebRequestHandlerV1,
        )

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    @property
    def bootstrap_url(self) -> str:
        return f"http://{LEARNING_CORPUS_WEB_BIND_HOST}:{self.port}/?token={self.corpus_token}"

    @property
    def origin(self) -> str:
        return f"http://{LEARNING_CORPUS_WEB_BIND_HOST}:{self.port}"

    def set_notice(self, message: str, kind: str) -> None:
        with self.corpus_context.lock:
            self.corpus_notice = (message, kind)

    def take_notice(self) -> tuple[str, str] | None:
        with self.corpus_context.lock:
            notice = self.corpus_notice
            self.corpus_notice = None
            return notice

    def server_close(self) -> None:
        self.corpus_context.shutdown()
        super().server_close()


class LearningCorpusWebRequestHandlerV1(BaseHTTPRequestHandler):
    server: LearningCorpusWebServerV1

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
        for name, value in learning_corpus_web_security_headers_v1():
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
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self._send_bytes(
            status,
            content,
            content_type="application/json; charset=utf-8",
        )

    def _host_is_valid(self) -> bool:
        if len(self.headers.get_all("Host", [])) != 1:
            return False
        return validate_learning_corpus_web_host_v1(
            self.headers.get("Host"),
            self.server.port,
        )

    def _cookie_is_valid(self) -> bool:
        if len(self.headers.get_all("Cookie", [])) != 1:
            return False
        return has_valid_learning_corpus_web_cookie_v1(
            self.headers.get("Cookie"),
            self.server.corpus_token,
        )

    def _authorize_get(self, path: str, query: str) -> bool:
        if not self._host_is_valid():
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        if path == "/" and query:
            query_values = parse_qs(query, keep_blank_values=True)
            if set(query_values) != {"token"} or query_values["token"] != [
                self.server.corpus_token
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
                        build_learning_corpus_web_cookie_v1(self.server.corpus_token),
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
        if len(self.headers.get_all("Origin", [])) != 1 or not (
            validate_learning_corpus_web_origin_v1(
                self.headers.get("Origin"),
                self.server.port,
                self.headers.get("Host"),
            )
        ):
            self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
            return False
        return True

    def _state(self) -> dict[str, object]:
        return build_learning_corpus_web_state_v1(self.server.corpus_context)

    def _page(
        self,
        status: int,
        *,
        notice: str | None = None,
        notice_kind: str = "info",
    ) -> None:
        self._send_text(
            status,
            render_learning_corpus_web_page_v1(
                self._state(),
                notice=notice,
                notice_kind=notice_kind,
            ),
            content_type="text/html; charset=utf-8",
        )

    def _validation_page(self, message: str) -> None:
        try:
            self._page(
                HTTPStatus.BAD_REQUEST,
                notice=message,
                notice_kind="error",
            )
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def _read_body(self) -> bytes:
        if self.headers.get_all("Transfer-Encoding", []):
            raise ValueError("Transfer-Encoding is not supported.")
        raw_lengths = self.headers.get_all("Content-Length", [])
        if len(raw_lengths) != 1:
            raise ValueError("Content-Length is required.")
        raw_length = raw_lengths[0]
        try:
            length = int(raw_length)
        except ValueError as error:
            raise ValueError("Content-Length must be an integer.") from error
        if length < 0:
            raise ValueError("Content-Length must not be negative.")
        if length > LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES:
            raise OverflowError("Request body is too large.")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Request body ended before Content-Length bytes were read.")
        return body

    def _parse_form(
        self,
    ) -> tuple[dict[str, str], LearningCorpusMultipartUploadV1 | None]:
        body = self._read_body()
        content_type = self.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type == "multipart/form-data":
            upload = parse_learning_corpus_multipart_upload_v1(
                body,
                content_type=content_type,
            )
            return dict(upload.fields), upload
        if media_type != "application/x-www-form-urlencoded":
            raise ValueError(
                "Content-Type must be application/x-www-form-urlencoded or multipart/form-data."
            )
        try:
            decoded = body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Form request body must be valid UTF-8.") from error
        parsed = parse_qs(decoded, keep_blank_values=True, strict_parsing=True)
        duplicates = sorted(name for name, items in parsed.items() if len(items) != 1)
        if duplicates:
            raise ValueError("Form fields must not repeat: " + ", ".join(duplicates) + ".")
        return {name: items[0] for name, items in parsed.items()}, None

    def _dispatch_upload(
        self,
        values: dict[str, str],
        upload: LearningCorpusMultipartUploadV1,
    ):
        operation = _text(values, "operation")
        try:
            expected_file_field, expected_fields = _UPLOAD_OPERATIONS[operation]
        except KeyError as error:
            raise ValueError("Multipart is supported only for upload operations.") from error
        _require_fields(values, expected_fields)
        if upload.file_field != expected_file_field:
            raise ValueError("Uploaded file field does not match the requested operation.")
        if operation == "import_match_workspace":
            with upload.temporary_file() as raw_path:
                return import_match_workspace_into_learning_corpus_web_v1(
                    self.server.corpus_context,
                    Path(raw_path),
                    selection_mode=_text(values, "selection_mode"),
                    same_revision_resolution=_text(
                        values,
                        "same_revision_resolution",
                    ),
                    expected_catalog_revision=_integer(
                        values,
                        "expected_catalog_revision",
                    ),
                )
        document = decode_learning_corpus_uploaded_json_v1(upload.file_content)
        export = resume_match_analysis_report_source_export_v1(document)
        source = build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=_text(values, "match_snapshot_id"),
            report=export.report,
        )
        return import_strategy_teacher_report_into_learning_corpus_web_v1(
            self.server.corpus_context,
            source,
        )

    def _dispatch_form(self, values: dict[str, str]):
        operation = _text(values, "operation")
        try:
            expected_fields = _FORM_OPERATIONS[operation]
        except KeyError as error:
            raise ValueError("operation must identify one supported operation.") from error
        _require_fields(values, expected_fields)
        context = self.server.corpus_context
        if operation == "initialize_corpus":
            return initialize_learning_corpus_web_v1(
                context,
                corpus_id=_text(values, "corpus_id"),
            )
        if operation == "reload_corpus":
            return reload_learning_corpus_web_v1(context)
        if operation == "select_current_snapshot":
            return select_current_learning_corpus_snapshot_web_v1(
                context,
                match_id=_text(values, "match_id"),
                match_snapshot_id=_text(values, "match_snapshot_id"),
                expected_catalog_revision=_integer(values, "expected_catalog_revision"),
            )
        if operation == "remove_strategy_teacher_report":
            return remove_strategy_teacher_report_from_learning_corpus_web_v1(
                context,
                source_binding_id=_text(values, "source_binding_id"),
            )
        if operation == "clear_strategy_teacher_reports":
            return clear_strategy_teacher_reports_from_learning_corpus_web_v1(context)
        return prepare_learning_corpus_artifacts_web_v1(
            context,
            dataset_id=_text(values, "dataset_id"),
            known_player_seed=_integer(values, "known_player_seed"),
            unseen_player_seed=_integer(values, "unseen_player_seed"),
            train_weight=_integer(values, "train_weight"),
            validation_weight=_integer(values, "validation_weight"),
            test_weight=_integer(values, "test_weight"),
        )

    def _allowed_methods(self, path: str) -> tuple[str, ...] | None:
        if path == _POST_ROUTE:
            return ("POST",)
        if path == "/" or path in _ASSETS or path in _DOWNLOAD_ROUTES or path == _STATE_ROUTE:
            return ("GET",)
        return None

    def do_GET(self) -> None:
        try:
            parsed = urlsplit(self.path)
            if not self._authorize_get(parsed.path, parsed.query):
                return
            if parsed.path == _POST_ROUTE:
                self._method_not_allowed(("POST",))
                return
            if parsed.path in _ASSETS:
                resource_name, content_type = _ASSETS[parsed.path]
                content = files("skat_ai.corpus_web").joinpath(resource_name).read_bytes()
                self._send_bytes(
                    HTTPStatus.OK,
                    content,
                    content_type=content_type,
                )
                return
            if parsed.path.startswith("/assets/"):
                self._send_text(HTTPStatus.NOT_FOUND, "Not found")
                return
            if parsed.path == _STATE_ROUTE:
                self._send_json(HTTPStatus.OK, self._state())
                return
            if parsed.path in _DOWNLOAD_ROUTES:
                try:
                    download = build_learning_corpus_prepared_download_v1(
                        self.server.corpus_context,
                        kind=_DOWNLOAD_ROUTES[parsed.path],
                    )
                except LearningCorpusPreparedDownloadUnavailableError as error:
                    if error.reason == "source_mismatch":
                        self._send_text(HTTPStatus.CONFLICT, "Prepared sources changed")
                    else:
                        self._send_text(HTTPStatus.NOT_FOUND, "Artifact unavailable")
                    return
                self._send_bytes(
                    HTTPStatus.OK,
                    download.content,
                    content_type="application/json; charset=utf-8",
                    extra_headers=(
                        (
                            "Content-Disposition",
                            f'attachment; filename="{download.filename}"',
                        ),
                    ),
                )
                return
            if parsed.path != "/":
                self._send_text(HTTPStatus.NOT_FOUND, "Not found")
                return
            notice = self.server.take_notice()
            self._page(
                HTTPStatus.OK,
                notice=None if notice is None else notice[0],
                notice_kind="info" if notice is None else notice[1],
            )
        except (SkatAIError, SkatAIInvariantError, TypeError, ValueError):
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
        except OSError:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Filesystem error")
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def do_POST(self) -> None:
        if not self._authorize_mutation():
            return
        try:
            parsed = urlsplit(self.path)
            if parsed.query:
                self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
                return
            if parsed.path != _POST_ROUTE:
                allowed = self._allowed_methods(parsed.path)
                if allowed is None:
                    self._send_text(HTTPStatus.NOT_FOUND, "Not found")
                else:
                    self._method_not_allowed(allowed)
                return
            values, upload = self._parse_form()
        except OverflowError:
            self._send_text(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body is too large")
            return
        except ValueError as error:
            self._validation_page(str(error))
            return
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
            return
        try:
            result = (
                self._dispatch_form(values)
                if upload is None
                else self._dispatch_upload(values, upload)
            )
            notice_kind = "warning" if result.http_status == 409 else "info"
            self._page(
                result.http_status,
                notice=result.message,
                notice_kind=notice_kind,
            )
        except SkatAIInvariantError:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
        except (SkatAIError, TypeError, ValueError) as error:
            self._validation_page(str(error))
        except OSError:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Filesystem error")
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def _method_not_allowed(self, allowed: tuple[str, ...]) -> None:
        self._send_text(
            HTTPStatus.METHOD_NOT_ALLOWED,
            "Method not allowed",
            extra_headers=(("Allow", ", ".join(allowed)),),
        )

    def _unsupported_method(self) -> None:
        try:
            parsed = urlsplit(self.path)
            if not self._host_is_valid() or not self._cookie_is_valid():
                self._send_text(HTTPStatus.FORBIDDEN, "Forbidden")
                return
            allowed = self._allowed_methods(parsed.path)
            if allowed is None:
                self._send_text(HTTPStatus.NOT_FOUND, "Not found")
                return
            self._method_not_allowed(allowed)
        except Exception:
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    do_DELETE = _unsupported_method
    do_HEAD = _unsupported_method
    do_OPTIONS = _unsupported_method
    do_PATCH = _unsupported_method
    do_PUT = _unsupported_method


def start_learning_corpus_web_server_v1(
    context: LearningCorpusWebContextV1,
    *,
    port: int = 8766,
    token: str | None = None,
) -> LearningCorpusWebServerV1:
    return LearningCorpusWebServerV1(context, port=port, token=token)


def serve_learning_corpus_web_in_thread_v1(
    server: LearningCorpusWebServerV1,
) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
