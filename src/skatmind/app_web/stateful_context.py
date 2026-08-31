from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .contracts import ManagedHomeV1
from .learning_frontend import UnifiedLearningContextV1
from .managed_item_contracts import (
    MANAGED_ITEM_FAMILIES,
    ManagedCategoryDiscoveryV1,
)
from .managed_item_discovery import discover_managed_items_v1
from .match_frontend import UnifiedMatchContextV1
from .session_frontend import GuidedSessionContextV1


@dataclass(slots=True, kw_only=True)
class ManagedStatefulContextV1:
    """App-lock-owned discovery and one active context per stateful family."""

    managed_home: ManagedHomeV1
    discoveries: dict[str, ManagedCategoryDiscoveryV1] = field(
        default_factory=dict,
        repr=False,
    )
    generations: dict[str, int] = field(
        default_factory=lambda: {family: 0 for family in MANAGED_ITEM_FAMILIES},
        repr=False,
    )
    active_session: GuidedSessionContextV1 | None = field(default=None, repr=False)
    active_match: UnifiedMatchContextV1 | None = field(default=None, repr=False)
    active_learning: UnifiedLearningContextV1 | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.managed_home) is not ManagedHomeV1:
            raise ValueError("managed_home must be an exact ManagedHomeV1.")
        if set(self.generations) != set(MANAGED_ITEM_FAMILIES) or any(
            type(value) is not int or value < 0 for value in self.generations.values()
        ):
            raise ValueError("generations must cover all managed item families.")

    def root(self, family: str) -> Path:
        if family not in MANAGED_ITEM_FAMILIES:
            raise ValueError("family must identify one managed item family.")
        return self.managed_home.category(family).path

    def active_handle(self, family: str) -> str | None:
        if family == "sessions":
            active = self.active_session
        elif family == "matches":
            active = self.active_match
        elif family == "corpora":
            active = self.active_learning
        else:
            raise ValueError("family must identify one managed item family.")
        return None if active is None else active.handle

    def begin_refresh(self, family: str) -> tuple[Path, int, str | None]:
        generation = self.generations[family] + 1
        self.generations[family] = generation
        return self.root(family), generation, self.active_handle(family)

    def publish_refresh(
        self,
        family: str,
        discovery: ManagedCategoryDiscoveryV1,
    ) -> bool:
        if discovery.view.family != family:
            raise ValueError("Discovery family does not match its publication target.")
        if self.generations[family] != discovery.view.generation:
            return False
        self.discoveries[family] = discovery
        return True

    def refresh(self, family: str) -> ManagedCategoryDiscoveryV1:
        root, generation, active_handle = self.begin_refresh(family)
        discovery = discover_managed_items_v1(
            root,
            family=family,
            generation=generation,
            active_handle=active_handle,
        )
        self.publish_refresh(family, discovery)
        return discovery

    def resolve(
        self,
        family: str,
        *,
        handle: str,
        generation: int,
    ):
        discovery = self.discoveries.get(family)
        if discovery is None or discovery.view.generation != generation:
            raise ValueError("Managed discovery changed; refresh before opening an item.")
        entry = discovery.resolve(handle)
        if entry is None:
            raise ValueError("Managed item handle is stale or unknown.")
        return entry

    def activate_session(
        self,
        context: GuidedSessionContextV1,
    ) -> GuidedSessionContextV1 | None:
        if type(context) is not GuidedSessionContextV1:
            raise ValueError("context must be an exact guided Session context.")
        previous = self.active_session if self.active_session is not context else None
        self.active_session = context
        return previous

    def activate_match(
        self,
        context: UnifiedMatchContextV1,
    ) -> UnifiedMatchContextV1 | None:
        if type(context) is not UnifiedMatchContextV1:
            raise ValueError("context must be an exact unified Match context.")
        previous = self.active_match if self.active_match is not context else None
        self.active_match = context
        return previous

    def activate_learning(
        self,
        context: UnifiedLearningContextV1,
    ) -> UnifiedLearningContextV1 | None:
        if type(context) is not UnifiedLearningContextV1:
            raise ValueError("context must be an exact unified Learning context.")
        previous = self.active_learning if self.active_learning is not context else None
        self.active_learning = context
        return previous
