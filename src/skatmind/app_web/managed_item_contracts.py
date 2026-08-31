from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

MANAGED_STATEFUL_FRONTEND_VERSION = 1
MANAGED_ITEM_DISCOVERY_VERSION = 1
GUIDED_SESSION_FRONTEND_VERSION = 1
UNIFIED_MATCH_CAPTURE_FRONTEND_VERSION = 1
UNIFIED_LEARNING_FRONTEND_VERSION = 1
FRONTEND_CROSS_AREA_TRANSFER_VERSION = 1

MANAGED_STATEFUL_FRONTEND_POLICIES: Final[tuple[str, ...]] = (
    "managed_category_discovery_is_explicit_and_non_recursive",
    "opaque_browser_handles_never_expose_filesystem_paths",
    "canonical_item_paths_are_derived_from_existing_product_identities",
    "strict_create_import_open_resume_reload_without_silent_overwrite",
    "existing_session_match_and_corpus_persistence_remains_authoritative",
    "one_active_process_local_context_per_stateful_family",
    "switching_items_discards_only_process_local_artifacts",
    "all_mutations_reuse_existing_operations_and_conflict_semantics",
    "cross_area_match_to_corpus_transfer_is_explicit_and_source_verified",
    "unified_app_cookie_and_security_context_only",
    "no_child_server_proxy_iframe_or_background_worker",
    "no_implicit_analysis_selection_preparation_or_conversion",
)

MANAGED_ITEM_FAMILIES: Final[tuple[str, ...]] = (
    "sessions",
    "matches",
    "corpora",
)
MANAGED_ITEM_DISCOVERY_STATUSES: Final[tuple[str, ...]] = (
    "available",
    "invalid",
    "resolution_required",
)
MANAGED_ITEM_MAX_CANDIDATES = 2_048
MANAGED_ITEM_MAX_IMPORT_BYTES = 16_777_216


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def validate_managed_stateful_frontend_contract_v1(
    *,
    managed_stateful_frontend_version: int = MANAGED_STATEFUL_FRONTEND_VERSION,
    managed_item_discovery_version: int = MANAGED_ITEM_DISCOVERY_VERSION,
    guided_session_frontend_version: int = GUIDED_SESSION_FRONTEND_VERSION,
    unified_match_capture_frontend_version: int = (
        UNIFIED_MATCH_CAPTURE_FRONTEND_VERSION
    ),
    unified_learning_frontend_version: int = UNIFIED_LEARNING_FRONTEND_VERSION,
    frontend_cross_area_transfer_version: int = FRONTEND_CROSS_AREA_TRANSFER_VERSION,
    policies: tuple[str, ...] = MANAGED_STATEFUL_FRONTEND_POLICIES,
) -> None:
    for field_name, value, expected in (
        (
            "managed_stateful_frontend_version",
            managed_stateful_frontend_version,
            MANAGED_STATEFUL_FRONTEND_VERSION,
        ),
        (
            "managed_item_discovery_version",
            managed_item_discovery_version,
            MANAGED_ITEM_DISCOVERY_VERSION,
        ),
        (
            "guided_session_frontend_version",
            guided_session_frontend_version,
            GUIDED_SESSION_FRONTEND_VERSION,
        ),
        (
            "unified_match_capture_frontend_version",
            unified_match_capture_frontend_version,
            UNIFIED_MATCH_CAPTURE_FRONTEND_VERSION,
        ),
        (
            "unified_learning_frontend_version",
            unified_learning_frontend_version,
            UNIFIED_LEARNING_FRONTEND_VERSION,
        ),
        (
            "frontend_cross_area_transfer_version",
            frontend_cross_area_transfer_version,
            FRONTEND_CROSS_AREA_TRANSFER_VERSION,
        ),
    ):
        _require_version(value, expected, field_name)
    if type(policies) is not tuple or policies != MANAGED_STATEFUL_FRONTEND_POLICIES:
        raise ValueError("policies must equal the exact Issue-#212 ordered policies.")


def _require_text(value: object, field_name: str, *, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty, non-padded text.")


def _require_handle(value: object) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("handle must be one lowercase SHA-256 hexadecimal value.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ManagedItemSummaryV1:
    """One browser-safe managed candidate without storage identity or Product data."""

    managed_item_discovery_version: int = MANAGED_ITEM_DISCOVERY_VERSION
    family: str
    handle: str
    semantic_product_id: str | None
    display_label: str | None
    status: str
    revision: int | None
    phase: str | None
    summary: tuple[str, ...]
    active: bool
    discovery_generation: int

    def __post_init__(self) -> None:
        _require_version(
            self.managed_item_discovery_version,
            MANAGED_ITEM_DISCOVERY_VERSION,
            "managed_item_discovery_version",
        )
        if self.family not in MANAGED_ITEM_FAMILIES:
            raise ValueError("family must identify one managed item family.")
        _require_handle(self.handle)
        _require_text(self.semantic_product_id, "semantic_product_id", allow_none=True)
        _require_text(self.display_label, "display_label", allow_none=True)
        if self.status not in MANAGED_ITEM_DISCOVERY_STATUSES:
            raise ValueError("status must identify one managed discovery status.")
        if self.status == "invalid" and (
            self.semantic_product_id is not None or self.display_label is not None
        ):
            raise ValueError("Invalid summaries must not retain Product identity.")
        if self.revision is not None and (type(self.revision) is not int or self.revision < 0):
            raise ValueError("revision must be null or a non-negative integer.")
        _require_text(self.phase, "phase", allow_none=True)
        if type(self.summary) is not tuple or any(
            type(item) is not str or not item for item in self.summary
        ):
            raise ValueError("summary must contain safe non-empty text values.")
        if type(self.active) is not bool:
            raise ValueError("active must be a boolean.")
        if type(self.discovery_generation) is not int or self.discovery_generation < 1:
            raise ValueError("discovery_generation must be a positive integer.")

    def to_dict(self) -> dict[str, object]:
        return {
            "managed_item_discovery_version": self.managed_item_discovery_version,
            "family": self.family,
            "handle": self.handle,
            "semantic_product_id": self.semantic_product_id,
            "display_label": self.display_label,
            "status": self.status,
            "revision": self.revision,
            "phase": self.phase,
            "summary": list(self.summary),
            "active": self.active,
            "discovery_generation": self.discovery_generation,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ManagedCategoryViewV1:
    """One deterministic browser-safe category discovery result."""

    managed_item_discovery_version: int = MANAGED_ITEM_DISCOVERY_VERSION
    family: str
    generation: int
    items: tuple[ManagedItemSummaryV1, ...]
    candidate_limit_reached: bool

    def __post_init__(self) -> None:
        _require_version(
            self.managed_item_discovery_version,
            MANAGED_ITEM_DISCOVERY_VERSION,
            "managed_item_discovery_version",
        )
        if self.family not in MANAGED_ITEM_FAMILIES:
            raise ValueError("family must identify one managed item family.")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("generation must be a positive integer.")
        if type(self.items) is not tuple or any(
            type(item) is not ManagedItemSummaryV1 for item in self.items
        ):
            raise ValueError("items must contain exact managed summaries.")
        if any(
            item.family != self.family or item.discovery_generation != self.generation
            for item in self.items
        ):
            raise ValueError("Every item must belong to this category generation.")
        handles = tuple(item.handle for item in self.items)
        if len(handles) != len(set(handles)):
            raise ValueError("Managed browser handles must be unique.")
        if len(self.items) > MANAGED_ITEM_MAX_CANDIDATES:
            raise ValueError("Managed category view exceeds its candidate limit.")
        if type(self.candidate_limit_reached) is not bool:
            raise ValueError("candidate_limit_reached must be a boolean.")

    @property
    def available_count(self) -> int:
        return sum(item.status == "available" for item in self.items)

    @property
    def invalid_count(self) -> int:
        return sum(item.status == "invalid" for item in self.items)

    @property
    def resolution_required_count(self) -> int:
        return sum(item.status == "resolution_required" for item in self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "managed_item_discovery_version": self.managed_item_discovery_version,
            "family": self.family,
            "generation": self.generation,
            "items": [item.to_dict() for item in self.items],
            "available_count": self.available_count,
            "invalid_count": self.invalid_count,
            "resolution_required_count": self.resolution_required_count,
            "candidate_limit_reached": self.candidate_limit_reached,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class DiscoveredManagedItemV1:
    """Private handle-to-direct-child resolution retained only in process memory."""

    summary: ManagedItemSummaryV1
    path: Path

    def __post_init__(self) -> None:
        if type(self.summary) is not ManagedItemSummaryV1:
            raise ValueError("summary must be an exact ManagedItemSummaryV1.")
        if not isinstance(self.path, Path):
            raise ValueError("path must be a private Path.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ManagedCategoryDiscoveryV1:
    view: ManagedCategoryViewV1
    entries: tuple[DiscoveredManagedItemV1, ...]

    def __post_init__(self) -> None:
        if type(self.view) is not ManagedCategoryViewV1:
            raise ValueError("view must be an exact ManagedCategoryViewV1.")
        if type(self.entries) is not tuple or any(
            type(entry) is not DiscoveredManagedItemV1 for entry in self.entries
        ):
            raise ValueError("entries must contain exact private discovered items.")
        if tuple(entry.summary for entry in self.entries) != self.view.items:
            raise ValueError("Private entries must correspond exactly to browser summaries.")

    def resolve(self, handle: str) -> DiscoveredManagedItemV1 | None:
        return next((entry for entry in self.entries if entry.summary.handle == handle), None)
