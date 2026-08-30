from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from .contracts import (
    MANAGED_LOCAL_DATA_CATEGORIES,
    ManagedCategoryV1,
    ManagedHomeV1,
)


def resolve_platform_managed_data_root_v1(
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolves the platform-managed SkatMind data root without creating it."""

    platform_value = sys.platform if platform_name is None else platform_name
    environment = os.environ if environ is None else dict(environ)
    if platform_value == "win32":
        base = environment.get("LOCALAPPDATA", "").strip()
        if not base:
            raise OSError("LOCALAPPDATA is required for the Windows managed data root.")
        return Path(base) / "SkatMind"
    if platform_value.startswith("linux"):
        xdg_data_home = environment.get("XDG_DATA_HOME", "").strip()
        if xdg_data_home:
            return Path(xdg_data_home) / "skatmind"
        home = environment.get("HOME", "").strip()
        if not home:
            raise OSError("HOME is required for the Linux managed data root.")
        return Path(home) / ".local" / "share" / "skatmind"
    raise OSError("SkatMind managed local data supports Windows and Linux.")


def resolve_managed_data_root_v1(
    override: str | os.PathLike[str] | None = None,
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    if override is None:
        return resolve_platform_managed_data_root_v1(
            platform_name=platform_name,
            environ=environ,
        )
    raw_override = os.fspath(override)
    if not raw_override.strip():
        raise ValueError("Managed data root override must not be empty.")
    return Path(raw_override).expanduser()


def _prepare_directory(path: Path, label: str) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError as error:
        raise NotADirectoryError(f"{label} must be a directory: {path}") from error
    if not path.is_dir():
        raise NotADirectoryError(f"{label} must be a directory: {path}")


def prepare_managed_home_v1(
    root_path: str | os.PathLike[str],
) -> ManagedHomeV1:
    """Creates only the managed root and its three canonical categories."""

    root = Path(root_path).expanduser()
    _prepare_directory(root, "Managed data root")
    categories = []
    for name in MANAGED_LOCAL_DATA_CATEGORIES:
        path = root / name
        _prepare_directory(path, f"Managed data category '{name}'")
        categories.append(ManagedCategoryV1(name=name, path=path))
    return ManagedHomeV1(root=root, categories=tuple(categories))
