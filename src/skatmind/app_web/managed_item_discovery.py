from __future__ import annotations

import os
import stat
from dataclasses import replace
from pathlib import Path

import skatmind.api.v1.session.files as session_files
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

from .managed_item_contracts import (
    MANAGED_ITEM_MAX_CANDIDATES,
    DiscoveredManagedItemV1,
    ManagedCategoryDiscoveryV1,
    ManagedCategoryViewV1,
    ManagedItemSummaryV1,
)
from .managed_item_storage import build_managed_item_handle_v1


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except AttributeError:
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()) or (
        _is_reparse_point(path)
    )


def _candidate_paths(category_root: Path, family: str) -> tuple[tuple[Path, ...], bool]:
    if not isinstance(category_root, Path):
        raise ValueError("category_root must be a Path.")
    mode = category_root.stat().st_mode
    if not stat.S_ISDIR(mode) or _is_link_or_junction(category_root):
        raise ValueError("Managed category root must be one direct non-link directory.")
    candidates = []
    with os.scandir(category_root) as scanned:
        for entry in scanned:
            path = category_root / entry.name
            if family in {"sessions", "matches"}:
                if entry.name.lower().endswith(".json"):
                    candidates.append(path)
            elif (
                entry.is_dir(follow_symlinks=False)
                or entry.is_symlink()
                or (hasattr(entry, "is_junction") and entry.is_junction())
            ):
                candidates.append(path)
    candidates.sort(key=lambda path: (path.name.casefold(), path.name))
    return tuple(candidates[:MANAGED_ITEM_MAX_CANDIDATES]), (
        len(candidates) > MANAGED_ITEM_MAX_CANDIDATES
    )


def _invalid_summary(
    *,
    family: str,
    handle: str,
    generation: int,
    active_handle: str | None,
) -> ManagedItemSummaryV1:
    return ManagedItemSummaryV1(
        family=family,
        handle=handle,
        semantic_product_id=None,
        display_label=None,
        status="invalid",
        revision=None,
        phase=None,
        summary=("This managed item could not be validated.",),
        active=handle == active_handle,
        discovery_generation=generation,
    )


def _session_summary(
    path: Path,
    *,
    handle: str,
    generation: int,
    active_handle: str | None,
) -> ManagedItemSummaryV1:
    resumed = session_files.load_session_file(path).value
    state = resumed.document.state
    return ManagedItemSummaryV1(
        family="sessions",
        handle=handle,
        semantic_product_id=state.session_id,
        display_label=state.session_id,
        status="available",
        revision=state.revision,
        phase=state.phase,
        summary=(
            state.capture_mode.title(),
            f"{len(resumed.document.decision_checkpoints)} Decision Checkpoints",
        ),
        active=handle == active_handle,
        discovery_generation=generation,
    )


def _match_summary(
    path: Path,
    *,
    handle: str,
    generation: int,
    active_handle: str | None,
) -> ManagedItemSummaryV1:
    resumed = load_match_workspace_file_v1(path)
    workspace = resumed.document.workspace
    definition = workspace.match_definition
    progress = resumed.progress
    participants = ", ".join(
        participant.player_label or participant.player_id
        for participant in definition.participants
    )
    return ManagedItemSummaryV1(
        family="matches",
        handle=handle,
        semantic_product_id=definition.match_id,
        display_label=definition.title,
        status="available",
        revision=workspace.revision,
        phase=progress.status,
        summary=(
            participants,
            f"Perspective: {definition.perspective_player_id}",
            (
                f"{progress.observed_game_count} observed, "
                f"{progress.passed_deal_count} passed, "
                f"{progress.empty_slot_count} empty"
            ),
        ),
        active=handle == active_handle,
        discovery_generation=generation,
    )


def _corpus_summary(
    path: Path,
    *,
    handle: str,
    generation: int,
    active_handle: str | None,
) -> ManagedItemSummaryV1:
    store = load_learning_corpus_directory_v1(path)
    catalog = store.document.catalog
    match_ids = {entry.match_id for entry in catalog.match_snapshots}
    return ManagedItemSummaryV1(
        family="corpora",
        handle=handle,
        semantic_product_id=catalog.corpus_id,
        display_label=catalog.corpus_id,
        status="available",
        revision=catalog.revision,
        phase="catalog_ready",
        summary=(
            f"{len(match_ids)} Matches",
            f"{len(catalog.current_matches)} Current Snapshots",
            f"{len(catalog.match_snapshots)} retained revisions",
        ),
        active=handle == active_handle,
        discovery_generation=generation,
    )


def _strict_summary(
    path: Path,
    *,
    family: str,
    handle: str,
    generation: int,
    active_handle: str | None,
) -> ManagedItemSummaryV1:
    if _is_link_or_junction(path):
        raise ValueError("Managed item links are not traversed.")
    mode = path.stat(follow_symlinks=False).st_mode
    if family in {"sessions", "matches"} and not stat.S_ISREG(mode):
        raise ValueError("Managed Session and Match candidates must be regular files.")
    if family == "corpora" and not stat.S_ISDIR(mode):
        raise ValueError("Managed Corpus candidates must be directories.")
    if family == "sessions":
        return _session_summary(
            path,
            handle=handle,
            generation=generation,
            active_handle=active_handle,
        )
    if family == "matches":
        return _match_summary(
            path,
            handle=handle,
            generation=generation,
            active_handle=active_handle,
        )
    return _corpus_summary(
        path,
        handle=handle,
        generation=generation,
        active_handle=active_handle,
    )


def discover_managed_items_v1(
    category_root: Path,
    *,
    family: str,
    generation: int,
    active_handle: str | None = None,
) -> ManagedCategoryDiscoveryV1:
    """Strictly classifies at most 2,048 direct children without recursion."""

    if type(generation) is not int or generation < 1:
        raise ValueError("generation must be a positive integer.")
    candidates, limit_reached = _candidate_paths(category_root, family)
    provisional: list[DiscoveredManagedItemV1] = []
    identities: dict[str, list[int]] = {}
    handles: set[str] = set()
    for path in candidates:
        handle = build_managed_item_handle_v1(family=family, basename=path.name)
        if handle in handles:
            raise RuntimeError("Managed browser handle collision.")
        handles.add(handle)
        try:
            summary = _strict_summary(
                path,
                family=family,
                handle=handle,
                generation=generation,
                active_handle=active_handle,
            )
        except Exception:
            summary = _invalid_summary(
                family=family,
                handle=handle,
                generation=generation,
                active_handle=active_handle,
            )
        provisional.append(DiscoveredManagedItemV1(summary=summary, path=path))
        if summary.semantic_product_id is not None:
            identities.setdefault(summary.semantic_product_id, []).append(
                len(provisional) - 1
            )

    for duplicate_indexes in identities.values():
        if len(duplicate_indexes) < 2:
            continue
        for index in duplicate_indexes:
            entry = provisional[index]
            provisional[index] = DiscoveredManagedItemV1(
                summary=replace(
                    entry.summary,
                    status="resolution_required",
                    summary=(
                        "Multiple managed items claim this Product identity; "
                        "manual storage resolution is required.",
                    ),
                ),
                path=entry.path,
            )

    entries = tuple(provisional)
    return ManagedCategoryDiscoveryV1(
        view=ManagedCategoryViewV1(
            family=family,
            generation=generation,
            items=tuple(entry.summary for entry in entries),
            candidate_limit_reached=limit_reached,
        ),
        entries=entries,
    )
