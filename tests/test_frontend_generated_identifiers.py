from __future__ import annotations

import hashlib

import pytest

from skatmind.app_web.frontend_identifier_generation import (
    FRONTEND_CORPUS_ID_DOMAIN,
    FRONTEND_MATCH_ID_DOMAIN,
    FRONTEND_PLAYER_ID_DOMAIN,
    FRONTEND_SESSION_ID_DOMAIN,
    KNOWN_PLAYER_HANDLE_DOMAIN,
    build_known_player_handle_v1,
    generate_frontend_corpus_id_v1,
    generate_frontend_match_id_v1,
    generate_frontend_player_id_v1,
    generate_frontend_session_id_v1,
)


@pytest.mark.parametrize(
    ("generator", "domain", "prefix"),
    (
        (generate_frontend_player_id_v1, FRONTEND_PLAYER_ID_DOMAIN, "frontend-player-"),
        (generate_frontend_session_id_v1, FRONTEND_SESSION_ID_DOMAIN, "frontend-session-"),
        (generate_frontend_match_id_v1, FRONTEND_MATCH_ID_DOMAIN, "frontend-match-"),
        (generate_frontend_corpus_id_v1, FRONTEND_CORPUS_ID_DOMAIN, "frontend-corpus-"),
    ),
)
def test_generated_identifiers_use_exact_domains_entropy_and_formats(
    generator,
    domain: bytes,
    prefix: str,
) -> None:
    calls: list[int] = []

    def entropy(size: int) -> bytes:
        calls.append(size)
        return bytes(range(32))

    result = generator(entropy_source=entropy)
    assert calls == [32]
    assert result == prefix + hashlib.sha256(domain + bytes(range(32))).hexdigest()
    assert len(result) == len(prefix) + 64
    assert result.removeprefix(prefix).isalnum()
    assert result == result.lower()


def test_identifier_domains_are_the_exact_frozen_literals() -> None:
    assert FRONTEND_PLAYER_ID_DOMAIN == b"skatmind\0frontend_player_id_v1\0"
    assert FRONTEND_SESSION_ID_DOMAIN == b"skatmind\0frontend_session_id_v1\0"
    assert FRONTEND_MATCH_ID_DOMAIN == b"skatmind\0frontend_match_id_v1\0"
    assert FRONTEND_CORPUS_ID_DOMAIN == b"skatmind\0frontend_corpus_id_v1\0"
    assert KNOWN_PLAYER_HANDLE_DOMAIN == b"skatmind\0frontend_known_player_handle_v1\0"


def test_identifier_collision_retries_and_stops_after_sixteen_attempts() -> None:
    entropy_values = iter((b"a" * 32, b"b" * 32))
    first = generate_frontend_session_id_v1(entropy_source=lambda _size: b"a" * 32)
    second = generate_frontend_session_id_v1(
        existing_ids=frozenset({first}),
        entropy_source=lambda _size: next(entropy_values),
    )
    assert second != first

    calls = 0

    def colliding(_size: int) -> bytes:
        nonlocal calls
        calls += 1
        return b"a" * 32

    with pytest.raises(RuntimeError, match="16"):
        generate_frontend_session_id_v1(
            existing_ids=frozenset({first}),
            entropy_source=colliding,
        )
    assert calls == 16


def test_identifier_generation_rejects_wrong_entropy_size_and_non_exact_ids() -> None:
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        generate_frontend_player_id_v1(entropy_source=lambda _size: b"short")
    with pytest.raises(ValueError, match="existing_ids"):
        generate_frontend_player_id_v1(existing_ids={"value"})  # type: ignore[arg-type]


def test_known_player_handle_is_exact_private_one_way_digest() -> None:
    player_id = "frontend-player-" + "a" * 64
    assert (
        build_known_player_handle_v1(player_id)
        == hashlib.sha256(KNOWN_PLAYER_HANDLE_DOMAIN + player_id.encode("utf-8")).hexdigest()
    )
    assert player_id not in build_known_player_handle_v1(player_id)
    with pytest.raises(ValueError):
        build_known_player_handle_v1("")
