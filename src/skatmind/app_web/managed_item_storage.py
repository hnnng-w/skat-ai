from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

from .managed_item_contracts import MANAGED_ITEM_FAMILIES

_MANAGED_ITEM_HANDLE_DOMAIN = b"skatmind\0managed_item_handle_v1\0"
_MANAGED_ITEM_STORAGE_DOMAIN = b"skatmind\0managed_item_storage_v1\0"

_STORAGE_SHAPES = {
    "sessions": ("session-", ".json"),
    "matches": ("match-", ".json"),
    "corpora": ("corpus-", ""),
}


def _canonical_identity_bytes(*, family: str, value_name: str, value: str) -> bytes:
    if family not in MANAGED_ITEM_FAMILIES:
        raise ValueError("family must identify one managed item family.")
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{value_name} must be non-empty, non-padded text.")
    return json.dumps(
        {"family": family, value_name: value},
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_managed_item_handle_v1(*, family: str, basename: str) -> str:
    """Builds one opaque route handle over a family and exact direct-child name."""

    material = _canonical_identity_bytes(
        family=family,
        value_name="basename",
        value=basename,
    )
    return hashlib.sha256(_MANAGED_ITEM_HANDLE_DOMAIN + material).hexdigest()


def build_managed_item_storage_name_v1(*, family: str, product_id: str) -> str:
    """Builds one canonical opaque storage basename over an existing Product ID."""

    material = _canonical_identity_bytes(
        family=family,
        value_name="product_id",
        value=product_id,
    )
    digest = hashlib.sha256(_MANAGED_ITEM_STORAGE_DOMAIN + material).hexdigest()
    prefix, suffix = _STORAGE_SHAPES[family]
    return f"{prefix}{digest}{suffix}"


def build_managed_item_storage_path_v1(
    category_root: Path,
    *,
    family: str,
    product_id: str,
) -> Path:
    if not isinstance(category_root, Path):
        raise ValueError("category_root must be a Path.")
    return category_root / build_managed_item_storage_name_v1(
        family=family,
        product_id=product_id,
    )


def validate_managed_direct_child_path_v1(
    category_root: Path,
    path: Path,
    *,
    expected_kind: str,
) -> None:
    """Revalidates lexical containment and non-link type before every item access."""

    if expected_kind not in {"file", "directory"}:
        raise ValueError("expected_kind must be file or directory.")
    if not isinstance(category_root, Path) or not isinstance(path, Path):
        raise ValueError("Managed containment values must be Paths.")
    if path.parent != category_root or path.name in {"", ".", ".."}:
        raise ValueError("Managed item must remain one direct category child.")
    root_mode = category_root.stat(follow_symlinks=False).st_mode
    if not stat.S_ISDIR(root_mode) or category_root.is_symlink():
        raise ValueError("Managed category root must remain a non-link directory.")
    if hasattr(category_root, "is_junction") and category_root.is_junction():
        raise ValueError("Managed category root must not be a junction.")
    item_mode = path.stat(follow_symlinks=False).st_mode
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("Managed item links and junctions are not followed.")
    expected = stat.S_ISREG(item_mode) if expected_kind == "file" else stat.S_ISDIR(item_mode)
    if not expected:
        raise ValueError(f"Managed item must remain a regular {expected_kind}.")
    if os.path.commonpath((os.fspath(category_root), os.fspath(path))) != os.fspath(
        category_root
    ):
        raise ValueError("Managed item escaped its category root.")
