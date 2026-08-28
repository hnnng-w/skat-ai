from __future__ import annotations

import sys
import webbrowser
from collections.abc import Callable
from typing import Protocol

from skatmind.cli.corpus_parser import parse_corpus_arguments
from skatmind.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    SkatMindError,
)


class _LearningCorpusWebServer(Protocol):
    bootstrap_url: str

    def serve_forever(self) -> None: ...

    def server_close(self) -> None: ...


def run_corpus_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
    server_factory: Callable[..., _LearningCorpusWebServer] | None = None,
    browser_open: Callable[[str], object] = webbrowser.open,
) -> int:
    args = parse_corpus_arguments(argv, invocation_style=invocation_style)
    server: _LearningCorpusWebServer | None = None
    try:
        from skatmind.corpus_web.context import LearningCorpusWebContextV1

        factory = server_factory
        if factory is None:
            from skatmind.corpus_web.server import start_learning_corpus_web_server_v1

            factory = start_learning_corpus_web_server_v1

        context = LearningCorpusWebContextV1.open(args.corpus)
        server = factory(context, port=args.port)
        local_url = server.bootstrap_url
        print(f"Local Learning Corpus: {local_url}")
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
