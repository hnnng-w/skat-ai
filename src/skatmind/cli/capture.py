from __future__ import annotations

import sys
import webbrowser
from collections.abc import Callable

from skatmind.capture_web.context import MatchCaptureWebContextV1
from skatmind.capture_web.server import (
    MatchCaptureWebServerV1,
    start_match_capture_web_server_v1,
)
from skatmind.cli.capture_parser import parse_capture_arguments
from skatmind.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    SkatMindError,
)


def run_capture_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
    server_factory: Callable[..., MatchCaptureWebServerV1] = (
        start_match_capture_web_server_v1
    ),
    browser_open: Callable[[str], object] = webbrowser.open,
) -> int:
    args = parse_capture_arguments(argv, invocation_style=invocation_style)
    server: MatchCaptureWebServerV1 | None = None
    try:
        context = MatchCaptureWebContextV1.open(args.workspace)
        server = server_factory(context, port=args.port)
        local_url = server.bootstrap_url
        print(f"Local Match capture: {local_url}")
        if not args.no_open:
            try:
                opened = browser_open(local_url)
                if opened is False:
                    print(
                        f"Warning: Could not open the browser. Use {local_url}",
                        file=sys.stderr,
                    )
            except Exception:
                print(
                    f"Warning: Could not open the browser. Use {local_url}",
                    file=sys.stderr,
                )
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
