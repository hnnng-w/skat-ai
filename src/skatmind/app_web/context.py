from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .contracts import BrowserSafeApplicationStateV1, ManagedHomeV1
from .state import build_browser_safe_application_state_v1
from .workflow_state import ProcessLocalFrontendWorkflowStateV1


@dataclass(slots=True)
class AppWebContextV1:
    """Process-local private context for one managed application home."""

    managed_home: ManagedHomeV1
    browser_state: BrowserSafeApplicationStateV1
    analyze_state: ProcessLocalFrontendWorkflowStateV1 = field(
        default_factory=ProcessLocalFrontendWorkflowStateV1,
        repr=False,
    )
    review_state: ProcessLocalFrontendWorkflowStateV1 = field(
        default_factory=ProcessLocalFrontendWorkflowStateV1,
        repr=False,
    )
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def __post_init__(self) -> None:
        if type(self.managed_home) is not ManagedHomeV1:
            raise ValueError("managed_home must be an exact ManagedHomeV1.")
        if type(self.browser_state) is not BrowserSafeApplicationStateV1:
            raise ValueError("browser_state must be an exact browser-safe state.")
        if type(self.analyze_state) is not ProcessLocalFrontendWorkflowStateV1:
            raise ValueError("analyze_state must be exact process-local workflow state.")
        if type(self.review_state) is not ProcessLocalFrontendWorkflowStateV1:
            raise ValueError("review_state must be exact process-local workflow state.")

    @classmethod
    def create(cls, managed_home: ManagedHomeV1) -> AppWebContextV1:
        return cls(
            managed_home=managed_home,
            browser_state=build_browser_safe_application_state_v1(),
        )
