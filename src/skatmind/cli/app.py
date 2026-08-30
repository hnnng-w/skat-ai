from __future__ import annotations

import sys
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import (
    prepare_managed_home_v1,
    resolve_managed_data_root_v1,
)
from skatmind.cli.app_parser import parse_app_arguments
from skatmind.errors import CLI_EXIT_CODE_FAILURE, CLI_EXIT_CODE_SUCCESS, SkatMindError


class _AppWebServer(Protocol):
    bootstrap_url: str

    def serve_forever(self) -> None: ...

    def server_close(self) -> None: ...


def run_app_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
    server_factory: Callable[..., _AppWebServer] | None = None,
    browser_open: Callable[[str], object] = webbrowser.open,
    managed_root_resolver: Callable[[], Path] = resolve_managed_data_root_v1,
) -> int:
    args = parse_app_arguments(argv, invocation_style=invocation_style)
    server: _AppWebServer | None = None
    running = False
    try:
        root = (
            managed_root_resolver()
            if args.data_root is None
            else resolve_managed_data_root_v1(args.data_root)
        )
        managed_home = prepare_managed_home_v1(root)
        context = AppWebContextV1.create(managed_home)
        factory = server_factory
        if factory is None:
            from skatmind.app_web.server import start_app_web_server_v1

            factory = start_app_web_server_v1
        server = factory(context, port=args.port)
        local_url = server.bootstrap_url
        opened = False
        if not args.no_open:
            try:
                opened = bool(browser_open(local_url))
            except Exception:
                opened = False
        if opened:
            print("SkatMind is running locally. Press Ctrl+C to stop.")
        else:
            print(f"Open SkatMind in your browser: {local_url}")
        running = True
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return CLI_EXIT_CODE_SUCCESS
    except (SkatMindError, TypeError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return CLI_EXIT_CODE_FAILURE
    finally:
        if server is not None:
            server.server_close()
        if running:
            print("SkatMind stopped.")
