from __future__ import annotations

from pathlib import Path

import pytest

from skatmind.corpus_web.contracts import LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES
from skatmind.corpus_web.uploads import (
    decode_learning_corpus_uploaded_json_v1,
    parse_learning_corpus_multipart_upload_v1,
)


def _multipart(
    fields: tuple[tuple[str, str], ...],
    files: tuple[tuple[str, str, bytes, str], ...],
    *,
    boundary: str = "skatmind-boundary",
) -> tuple[bytes, str]:
    parts: list[bytes] = []
    for name, value in fields:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
            f"\r\n\r\n{value}\r\n".encode()
        )
    for name, filename, content, content_type in files:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode()
            + content
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def test_strict_multipart_parses_one_file_ignores_filename_and_cleans_temp() -> None:
    content = b'{\n  "value": 1\n}\n'
    body, content_type = _multipart(
        (("operation", "import_match_workspace"), ("selection_mode", "keep_current")),
        (("workspace_file", "../../caller/path.json", content, "application/json"),),
    )
    upload = parse_learning_corpus_multipart_upload_v1(
        body,
        content_type=content_type,
    )
    assert dict(upload.fields) == {
        "operation": "import_match_workspace",
        "selection_mode": "keep_current",
    }
    assert upload.file_field == "workspace_file"
    assert upload.file_content == content
    assert "caller" not in repr(upload)

    with upload.temporary_file() as raw_path:
        path = Path(raw_path)
        assert path.is_file()
        assert path.read_bytes() == content
        assert "caller" not in path.name
    assert not path.exists()

    with pytest.raises(RuntimeError):
        with upload.temporary_file() as failing_path:
            temporary = Path(failing_path)
            raise RuntimeError("operation failed")
    assert not temporary.exists()


def test_multipart_ignores_non_ascii_filename_and_boundary_token_in_json() -> None:
    content = b'{"value":"--skatmind-boundary"}'
    body, content_type = _multipart(
        (("operation", "import_match_workspace"),),
        (("workspace_file", "Übung.json", content, "application/json"),),
    )
    upload = parse_learning_corpus_multipart_upload_v1(
        body,
        content_type=content_type,
    )
    assert upload.file_content == content
    assert "Übung" not in repr(upload)


@pytest.mark.parametrize(
    ("content", "message"),
    (
        (b"\xef\xbb\xbf{}", "BOM"),
        (b'{"value":1,"value":2}', "Duplicate"),
        (b'{"value":NaN}', "Non-finite"),
        (b'{"value":1e9999}', "Non-finite"),
        (b"[]", "root"),
        (b"\xff", "UTF-8"),
    ),
)
def test_uploaded_json_is_strict_finite_utf8_object(content: bytes, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        decode_learning_corpus_uploaded_json_v1(content)


def test_multipart_rejects_duplicates_nested_malformed_and_transfer_encoding() -> None:
    valid_file = (("workspace_file", "workspace.json", b"{}", "application/json"),)
    duplicate_fields, content_type = _multipart(
        (("operation", "one"), ("operation", "two")),
        valid_file,
    )
    with pytest.raises(ValueError, match="Duplicate multipart field"):
        parse_learning_corpus_multipart_upload_v1(
            duplicate_fields,
            content_type=content_type,
        )

    duplicate_files, content_type = _multipart(
        (("operation", "import_match_workspace"),),
        (
            ("workspace_file", "one.json", b"{}", "application/json"),
            ("report_source_file", "two.json", b"{}", "application/json"),
        ),
    )
    with pytest.raises(ValueError, match="one uploaded file"):
        parse_learning_corpus_multipart_upload_v1(
            duplicate_files,
            content_type=content_type,
        )

    nested, content_type = _multipart(
        (("operation", "import_match_workspace"),),
        (("workspace_file", "nested.json", b"{}", "multipart/mixed"),),
    )
    with pytest.raises(ValueError, match="Nested multipart"):
        parse_learning_corpus_multipart_upload_v1(nested, content_type=content_type)

    malformed, content_type = _multipart((), valid_file)
    with pytest.raises(ValueError, match="boundary"):
        parse_learning_corpus_multipart_upload_v1(
            malformed.removesuffix(b"--\r\n"),
            content_type=content_type,
        )

    transfer, content_type = _multipart((), valid_file)
    transfer = transfer.replace(
        b"Content-Type: application/json\r\n",
        b"Content-Type: application/json\r\nContent-Transfer-Encoding: base64\r\n",
    )
    with pytest.raises(ValueError, match="transfer encodings"):
        parse_learning_corpus_multipart_upload_v1(transfer, content_type=content_type)


def test_multipart_rejects_invalid_content_type_boundary_and_size() -> None:
    with pytest.raises(ValueError, match="multipart/form-data"):
        parse_learning_corpus_multipart_upload_v1(b"", content_type="application/json")
    with pytest.raises(ValueError, match="boundary"):
        parse_learning_corpus_multipart_upload_v1(
            b"",
            content_type='multipart/form-data; boundary="bad boundary"',
        )
    with pytest.raises(OverflowError, match="too large"):
        parse_learning_corpus_multipart_upload_v1(
            b"x" * (LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES + 1),
            content_type="multipart/form-data; boundary=x",
        )
