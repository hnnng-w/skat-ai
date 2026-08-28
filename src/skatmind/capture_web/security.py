from __future__ import annotations

import hmac
import secrets
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

from .contracts import MATCH_CAPTURE_WEB_BIND_HOST

MATCH_CAPTURE_WEB_COOKIE_NAME = "skatmind_capture_token"

MATCH_CAPTURE_WEB_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; "
    "style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; "
    "font-src 'none'; media-src 'none'; object-src 'none'"
)
MATCH_CAPTURE_WEB_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), "
    "bluetooth=(), browsing-topics=()"
)


def create_match_capture_web_token_v1() -> str:
    return secrets.token_urlsafe(32)


def build_match_capture_web_cookie_v1(token: str) -> str:
    return (
        f"{MATCH_CAPTURE_WEB_COOKIE_NAME}={token}; Path=/; HttpOnly; "
        "SameSite=Strict"
    )


def has_valid_match_capture_web_cookie_v1(cookie_header: str | None, token: str) -> bool:
    if cookie_header is None:
        return False
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except cookie.CookieError:
        return False
    morsel = cookie.get(MATCH_CAPTURE_WEB_COOKIE_NAME)
    return morsel is not None and hmac.compare_digest(morsel.value, token)


def validate_match_capture_web_host_v1(host_header: str | None, port: int) -> bool:
    if host_header is None:
        return False
    return host_header in {
        MATCH_CAPTURE_WEB_BIND_HOST,
        f"{MATCH_CAPTURE_WEB_BIND_HOST}:{port}",
        "localhost",
        f"localhost:{port}",
    }


def validate_match_capture_web_origin_v1(
    origin_header: str | None,
    port: int,
    host_header: str | None = None,
) -> bool:
    if origin_header is None:
        return False
    try:
        parsed = urlsplit(origin_header)
        parsed_port = parsed.port
    except ValueError:
        return False
    valid = (
        parsed.scheme == "http"
        and parsed.username is None
        and parsed.password is None
        and parsed.hostname in {MATCH_CAPTURE_WEB_BIND_HOST, "localhost"}
        and parsed_port == port
        and not parsed.path.rstrip("/")
        and not parsed.query
        and not parsed.fragment
    )
    return valid and (host_header is None or parsed.netloc == host_header)


def match_capture_web_security_headers_v1() -> tuple[tuple[str, str], ...]:
    return (
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("X-Frame-Options", "DENY"),
        ("Content-Security-Policy", MATCH_CAPTURE_WEB_CONTENT_SECURITY_POLICY),
        ("Permissions-Policy", MATCH_CAPTURE_WEB_PERMISSIONS_POLICY),
    )
