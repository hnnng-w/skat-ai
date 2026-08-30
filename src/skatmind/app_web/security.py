from __future__ import annotations

import hmac
import secrets
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit

APP_WEB_BIND_HOST = "127.0.0.1"
APP_WEB_COOKIE_NAME = "skatmind_app_token"

APP_WEB_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; "
    "style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; "
    "font-src 'none'; media-src 'none'; object-src 'none'"
)
APP_WEB_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), "
    "bluetooth=(), browsing-topics=()"
)


def create_app_web_token_v1() -> str:
    return secrets.token_urlsafe(32)


def build_app_web_cookie_v1(token: str) -> str:
    return f"{APP_WEB_COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/"


def has_valid_app_web_cookie_v1(cookie_header: str | None, token: str) -> bool:
    if cookie_header is None or "\r" in cookie_header or "\n" in cookie_header:
        return False
    app_cookie_count = sum(
        item.partition("=")[0].strip() == APP_WEB_COOKIE_NAME
        for item in cookie_header.split(";")
    )
    if app_cookie_count != 1:
        return False
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except CookieError:
        return False
    morsel = cookie.get(APP_WEB_COOKIE_NAME)
    return morsel is not None and hmac.compare_digest(morsel.value, token)


def validate_app_web_host_v1(host_header: str | None, port: int) -> bool:
    if host_header is None:
        return False
    return host_header in {
        APP_WEB_BIND_HOST,
        f"{APP_WEB_BIND_HOST}:{port}",
        "localhost",
        f"localhost:{port}",
    }


def validate_app_web_origin_v1(
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
        and parsed.hostname in {APP_WEB_BIND_HOST, "localhost"}
        and parsed_port == port
        and parsed.path == ""
        and not parsed.query
        and not parsed.fragment
    )
    return valid and (host_header is None or parsed.netloc == host_header)


def app_web_security_headers_v1() -> tuple[tuple[str, str], ...]:
    return (
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("X-Frame-Options", "DENY"),
        ("Content-Security-Policy", APP_WEB_CONTENT_SECURITY_POLICY),
        ("Permissions-Policy", APP_WEB_PERMISSIONS_POLICY),
    )
