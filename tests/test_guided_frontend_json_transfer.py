from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

import skatmind.app_web.json_transfer as transfer_module
from skatmind.api.v1 import WorkflowV1
from skatmind.app_web.json_transfer import (
    FRONTEND_JSON_MAX_FILE_BYTES,
    FRONTEND_JSON_TRANSFER_VERSION,
    build_frontend_request_json_bytes_v1,
    canonical_frontend_json_bytes_v1,
    decode_frontend_json_object_v1,
    parse_frontend_json_import_v1,
)
from skatmind.errors import SkatMindWorkflowError

ROOT = Path(__file__).resolve().parents[1]


def _example(name: str) -> dict[str, object]:
    value = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _multipart(
    *,
    content: bytes,
    revision_parts: tuple[bytes, ...] = (b"0",),
    file_count: int = 1,
    file_field: str = "request_file",
    filename: str = "request.json",
    file_content_type: str = "application/json",
    boundary: str = "skatmind-guided-boundary",
) -> tuple[bytes, str]:
    parts: list[bytes] = []
    for revision in revision_parts:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="revision"'
            "\r\n\r\n".encode()
            + revision
            + b"\r\n"
        )
    for _index in range(file_count):
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{filename}"\r\nContent-Type: {file_content_type}\r\n\r\n'.encode()
            + content
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _encoded(value: object) -> bytes:
    return json.dumps(value, allow_nan=False).encode("utf-8")


def test_transfer_version_and_canonical_json_contract() -> None:
    assert type(FRONTEND_JSON_TRANSFER_VERSION) is int
    assert FRONTEND_JSON_TRANSFER_VERSION == 1
    assert FRONTEND_JSON_MAX_FILE_BYTES == 1_048_576
    assert canonical_frontend_json_bytes_v1({"z": 1, "a": "ä"}) == (
        b'{\n  "a": "\\u00e4",\n  "z": 1\n}\n'
    )
    with pytest.raises(ValueError, match="JSON"):
        canonical_frontend_json_bytes_v1({"value": float("nan")})


def test_valid_position_import_calls_public_parser_once_and_does_not_execute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _example("grand_second_position.json")
    body, content_type = _multipart(
        content=_encoded(document),
        filename="../../caller/private/request.json",
    )
    calls: list[object] = []
    real_parse = transfer_module.parse_request

    def parse_request(value: object):
        calls.append(value)
        return real_parse(value)

    monkeypatch.setattr(transfer_module, "parse_request", parse_request)
    imported = parse_frontend_json_import_v1(
        body,
        content_type=content_type,
        page="analyze",
    )

    assert len(calls) == 1
    assert imported.revision == "0"
    assert imported.request.workflow is WorkflowV1.POSITION_ANALYSIS
    assert imported.summary.to_dict() == {
        "workflow": "position_analysis",
        "analysis_mode": None,
        "game_end_reason": None,
    }
    assert tuple(item.name for item in fields(imported.summary)) == (
        "workflow",
        "analysis_mode",
        "game_end_reason",
    )
    assert json.loads(imported.request_json_bytes) == document
    assert imported.request_json_bytes == build_frontend_request_json_bytes_v1(
        imported.request
    )
    assert "caller" not in repr(imported)
    assert not hasattr(imported, "filename")
    assert not hasattr(imported, "file_content")
    assert not hasattr(transfer_module, "execute")


@pytest.mark.parametrize(
    ("name", "expected_end"),
    (
        ("historical_grand_normal_completion.json", "normal_completion"),
        ("historical_grand_defender_concession.json", "defender_concession"),
        (
            "historical_grand_defender_open_play_continuation.json",
            "normal_completion",
        ),
        (
            "historical_party_wide_claim.json",
            "party_wide_all_remaining_tricks_claim",
        ),
    ),
)
def test_review_import_accepts_supported_historical_endings(
    name: str,
    expected_end: str,
) -> None:
    body, content_type = _multipart(content=_encoded(_example(name)))
    imported = parse_frontend_json_import_v1(
        body,
        content_type=content_type,
        page="review",
    )
    assert imported.request.workflow is WorkflowV1.HISTORICAL_GAME
    assert imported.summary.analysis_mode is None
    assert imported.summary.game_end_reason == expected_end


def test_review_import_accepts_only_exact_post_game_position_mode() -> None:
    review_document = _example("grand_post_game_acceptable_actual_card.json")
    body, content_type = _multipart(content=_encoded(review_document))
    imported = parse_frontend_json_import_v1(
        body,
        content_type=content_type,
        page="review",
    )
    assert imported.summary.analysis_mode == "post_game_review"
    assert imported.summary.game_end_reason == "not_ended"

    live_body, live_type = _multipart(
        content=_encoded(_example("grand_second_position.json"))
    )
    with pytest.raises(SkatMindWorkflowError, match="post_game_review"):
        parse_frontend_json_import_v1(
            live_body,
            content_type=live_type,
            page="review",
        )


def test_page_boundaries_reject_other_workflows_without_reinterpretation() -> None:
    opponent = _example("opponent_statistics.json")
    body, content_type = _multipart(content=_encoded(opponent))
    for page in ("analyze", "review"):
        with pytest.raises(SkatMindWorkflowError, match="opponent_statistics"):
            parse_frontend_json_import_v1(
                body,
                content_type=content_type,
                page=page,
            )

    historical = _example("historical_grand_normal_completion.json")
    body, content_type = _multipart(content=_encoded(historical))
    with pytest.raises(SkatMindWorkflowError, match="historical_game"):
        parse_frontend_json_import_v1(
            body,
            content_type=content_type,
            page="analyze",
        )


@pytest.mark.parametrize(
    ("content", "message"),
    (
        (b"{", "valid UTF-8 JSON"),
        (b"[]", "root"),
        (b'{"value":NaN}', "Non-finite"),
        (b'{"value":1e9999}', "Non-finite"),
        (b'{"outer":{"same":1,"same":2}}', "Duplicate"),
        (b"\xef\xbb\xbf{}", "BOM"),
        (b"\xff", "UTF-8"),
    ),
)
def test_uploaded_json_is_strict_finite_utf8_object(
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        decode_frontend_json_object_v1(content)


def test_json_file_size_boundary_is_exact() -> None:
    exact = b'{"value":"' + b"x" * (FRONTEND_JSON_MAX_FILE_BYTES - 12) + b'"}'
    assert len(exact) == FRONTEND_JSON_MAX_FILE_BYTES
    assert decode_frontend_json_object_v1(exact)["value"]
    with pytest.raises(OverflowError, match="too large"):
        decode_frontend_json_object_v1(exact + b" ")


def test_multipart_rejects_duplicate_missing_and_unknown_parts() -> None:
    content = _encoded(_example("grand_second_position.json"))
    duplicate, content_type = _multipart(content=content, file_count=2)
    with pytest.raises(ValueError, match="one uploaded request file"):
        parse_frontend_json_import_v1(
            duplicate,
            content_type=content_type,
            page="analyze",
        )

    duplicate_revision, content_type = _multipart(
        content=content,
        revision_parts=(b"0", b"1"),
    )
    with pytest.raises(ValueError, match="revision must appear exactly once"):
        parse_frontend_json_import_v1(
            duplicate_revision,
            content_type=content_type,
            page="analyze",
        )

    missing_revision, content_type = _multipart(content=content, revision_parts=())
    with pytest.raises(ValueError, match="revision must appear exactly once"):
        parse_frontend_json_import_v1(
            missing_revision,
            content_type=content_type,
            page="analyze",
        )

    wrong_file, content_type = _multipart(content=content, file_field="other_file")
    with pytest.raises(ValueError, match="unsupported file field"):
        parse_frontend_json_import_v1(
            wrong_file,
            content_type=content_type,
            page="analyze",
        )


def test_multipart_retains_revision_text_for_transport_level_integer_validation() -> None:
    content = _encoded(_example("grand_second_position.json"))
    body, content_type = _multipart(content=content, revision_parts=(b"01",))

    imported = parse_frontend_json_import_v1(
        body,
        content_type=content_type,
        page="analyze",
    )

    assert imported.revision == "01"


def test_multipart_rejects_nested_malformed_headers_and_framing() -> None:
    content = _encoded(_example("grand_second_position.json"))
    nested, content_type = _multipart(
        content=content,
        file_content_type="multipart/mixed",
    )
    with pytest.raises(ValueError, match="Nested multipart"):
        parse_frontend_json_import_v1(nested, content_type=content_type, page="analyze")

    transfer, content_type = _multipart(content=content)
    transfer = transfer.replace(
        b"Content-Type: application/json\r\n",
        b"Content-Type: application/json\r\nContent-Transfer-Encoding: base64\r\n",
    )
    with pytest.raises(ValueError, match="transfer encodings"):
        parse_frontend_json_import_v1(
            transfer,
            content_type=content_type,
            page="analyze",
        )

    duplicate_header, content_type = _multipart(content=content)
    duplicate_header = duplicate_header.replace(
        b"Content-Type: application/json\r\n",
        b"Content-Type: application/json\r\nContent-Type: application/json\r\n",
    )
    with pytest.raises(ValueError, match="must not repeat"):
        parse_frontend_json_import_v1(
            duplicate_header,
            content_type=content_type,
            page="analyze",
        )

    malformed, content_type = _multipart(content=content)
    with pytest.raises(ValueError, match="boundary"):
        parse_frontend_json_import_v1(
            malformed.removesuffix(b"--\r\n"),
            content_type=content_type,
            page="analyze",
        )


@pytest.mark.parametrize(
    "content_type",
    (
        "application/json",
        "multipart/form-data",
        "multipart/form-data; boundary=bad boundary",
        "multipart/form-data; boundary=x; boundary=y",
        "multipart/form-data; boundary=x; charset=utf-8",
        "multipart/form-data; boundary=\"unterminated",
    ),
)
def test_multipart_requires_one_strict_boundary(content_type: str) -> None:
    with pytest.raises(ValueError, match="Content-Type|boundary|parameters"):
        parse_frontend_json_import_v1(b"", content_type=content_type, page="analyze")


def test_multipart_enforces_file_content_limit_not_total_body_limit() -> None:
    valid = _encoded(_example("grand_second_position.json"))
    exact = valid + b" " * (FRONTEND_JSON_MAX_FILE_BYTES - len(valid))
    body, content_type = _multipart(content=exact)
    assert len(body) > FRONTEND_JSON_MAX_FILE_BYTES
    imported = parse_frontend_json_import_v1(
        body,
        content_type=content_type,
        page="analyze",
    )
    assert imported.request.workflow is WorkflowV1.POSITION_ANALYSIS

    oversized, content_type = _multipart(content=exact + b" ")
    with pytest.raises(OverflowError, match="too large"):
        parse_frontend_json_import_v1(
            oversized,
            content_type=content_type,
            page="analyze",
        )
