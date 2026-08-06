"""Module entry point for ``python -m skat_ai``."""

from skat_ai.cli.execution import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli(invocation_style="module"))
