from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable, Collection

FRONTEND_PLAYER_ID_DOMAIN = b"skatmind\0frontend_player_id_v1\0"
FRONTEND_SESSION_ID_DOMAIN = b"skatmind\0frontend_session_id_v1\0"
FRONTEND_MATCH_ID_DOMAIN = b"skatmind\0frontend_match_id_v1\0"
FRONTEND_CORPUS_ID_DOMAIN = b"skatmind\0frontend_corpus_id_v1\0"
KNOWN_PLAYER_HANDLE_DOMAIN = b"skatmind\0frontend_known_player_handle_v1\0"

_MAX_GENERATION_ATTEMPTS = 16


def _generate_identifier(
    *,
    domain: bytes,
    prefix: str,
    existing_ids: Collection[str],
    entropy_source: Callable[[int], bytes],
) -> str:
    if not isinstance(existing_ids, (tuple, frozenset)):
        raise ValueError("existing_ids must be an immutable exact collection.")
    if any(type(value) is not str for value in existing_ids):
        raise ValueError("existing_ids must contain only strings.")
    for _attempt in range(_MAX_GENERATION_ATTEMPTS):
        entropy = entropy_source(32)
        if type(entropy) is not bytes or len(entropy) != 32:
            raise ValueError("Entropy source must return exactly 32 bytes.")
        candidate = prefix + hashlib.sha256(domain + entropy).hexdigest()
        if candidate not in existing_ids:
            return candidate
    raise RuntimeError("Frontend identifier generation collided on all 16 attempts.")


def generate_frontend_player_id_v1(
    *,
    existing_ids: Collection[str] = (),
    entropy_source: Callable[[int], bytes] = secrets.token_bytes,
) -> str:
    return _generate_identifier(
        domain=FRONTEND_PLAYER_ID_DOMAIN,
        prefix="frontend-player-",
        existing_ids=existing_ids,
        entropy_source=entropy_source,
    )


def generate_frontend_session_id_v1(
    *,
    existing_ids: Collection[str] = (),
    entropy_source: Callable[[int], bytes] = secrets.token_bytes,
) -> str:
    return _generate_identifier(
        domain=FRONTEND_SESSION_ID_DOMAIN,
        prefix="frontend-session-",
        existing_ids=existing_ids,
        entropy_source=entropy_source,
    )


def generate_frontend_match_id_v1(
    *,
    existing_ids: Collection[str] = (),
    entropy_source: Callable[[int], bytes] = secrets.token_bytes,
) -> str:
    return _generate_identifier(
        domain=FRONTEND_MATCH_ID_DOMAIN,
        prefix="frontend-match-",
        existing_ids=existing_ids,
        entropy_source=entropy_source,
    )


def generate_frontend_corpus_id_v1(
    *,
    existing_ids: Collection[str] = (),
    entropy_source: Callable[[int], bytes] = secrets.token_bytes,
) -> str:
    return _generate_identifier(
        domain=FRONTEND_CORPUS_ID_DOMAIN,
        prefix="frontend-corpus-",
        existing_ids=existing_ids,
        entropy_source=entropy_source,
    )


def build_known_player_handle_v1(player_id: str) -> str:
    if type(player_id) is not str or not player_id:
        raise ValueError("player_id must be non-empty text.")
    return hashlib.sha256(KNOWN_PLAYER_HANDLE_DOMAIN + player_id.encode("utf-8")).hexdigest()
