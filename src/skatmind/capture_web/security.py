from __future__ import annotations

import hmac
import secrets
from http.cookies import CookieError, SimpleCookie
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
    if cookie_header is None or any(value in cookie_header for value in "\r\n,"):
        return False
    capture_cookie_count = sum(
        item.partition("=")[0].strip() == MATCH_CAPTURE_WEB_COOKIE_NAME
        for item in cookie_header.split(";")
    )
    if capture_cookie_count != 1:
        return False
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except CookieError:
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
        parsed_port = parsed.port if parsed.port is not None else 80
    except ValueError:
        return False
    valid_netlocs = {
        f"{hostname}:{port}"
        for hostname in {MATCH_CAPTURE_WEB_BIND_HOST, "localhost"}
    }
    if port == 80:
        valid_netlocs.update({MATCH_CAPTURE_WEB_BIND_HOST, "localhost"})
    valid = (
        parsed.scheme == "http"
        and parsed.username is None
        and parsed.password is None
        and parsed.hostname in {MATCH_CAPTURE_WEB_BIND_HOST, "localhost"}
        and parsed.netloc in valid_netlocs
        and parsed_port == port
        and parsed.path == ""
        and not parsed.query
        and not parsed.fragment
        and "?" not in origin_header
        and "#" not in origin_header
    )
    if not valid or host_header is None:
        return valid
    try:
        parsed_host = urlsplit(f"http://{host_header}")
        host_port = parsed_host.port if parsed_host.port is not None else 80
    except ValueError:
        return False
    return (
        parsed_host.hostname == parsed.hostname
        and host_port == parsed_port
        and parsed_host.username is None
        and parsed_host.password is None
        and parsed_host.path == ""
        and not parsed_host.query
        and not parsed_host.fragment
    )


def match_capture_web_security_headers_v1() -> tuple[tuple[str, str], ...]:
    return (
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "origin"),
        ("X-Frame-Options", "DENY"),
        ("Content-Security-Policy", MATCH_CAPTURE_WEB_CONTENT_SECURITY_POLICY),
        ("Permissions-Policy", MATCH_CAPTURE_WEB_PERMISSIONS_POLICY),
    )
