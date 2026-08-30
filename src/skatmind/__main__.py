"""Module entry point for ``python -m skatmind``."""

from skatmind.cli.entrypoint import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli(invocation_style="module"))
