"""Invocation-local raw Root CLI option presence."""

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

_SUPPLIED_ROOT_CLI_OPTIONS: ContextVar[tuple[str, ...] | None] = ContextVar(
    "supplied_root_cli_options",
    default=None,
)
_SUPPLIED_WORKFLOW_OPTION_NAMES: ContextVar[tuple[str, ...] | None] = ContextVar(
    "supplied_workflow_option_names",
    default=None,
)


def current_supplied_root_cli_options() -> tuple[str, ...] | None:
    """Returns raw option names for the active Root CLI invocation."""
    return _SUPPLIED_ROOT_CLI_OPTIONS.get()


def current_supplied_workflow_option_names() -> tuple[str, ...] | None:
    """Returns translated workflow option names for Application execution."""
    return _SUPPLIED_WORKFLOW_OPTION_NAMES.get()


def invoke_with_supplied_root_cli_options(
    callback: Callable[..., Any],
    supplied_options: tuple[str, ...],
    /,
    **kwargs: object,
) -> Any:
    """Invokes one compatibility wrapper with scoped option-presence metadata."""
    token = _SUPPLIED_ROOT_CLI_OPTIONS.set(supplied_options)
    try:
        return callback(**kwargs)
    finally:
        _SUPPLIED_ROOT_CLI_OPTIONS.reset(token)


def invoke_with_supplied_workflow_option_names(
    callback: Callable[..., Any],
    supplied_names: tuple[str, ...],
    /,
    *args: object,
    **kwargs: object,
) -> Any:
    """Invokes the frozen Application seam with scoped presence metadata."""
    token = _SUPPLIED_WORKFLOW_OPTION_NAMES.set(supplied_names)
    try:
        return callback(*args, **kwargs)
    finally:
        _SUPPLIED_WORKFLOW_OPTION_NAMES.reset(token)
