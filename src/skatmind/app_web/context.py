from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .contracts import BrowserSafeApplicationStateV1, ManagedHomeV1
from .form_state import ProcessLocalFrontendFeedbackStateV1
from .frontend_profile_state import (
    FrontendProfileStateV1,
    build_frontend_profile_state_v1,
)
from .state import build_browser_safe_application_state_v1
from .workflow_state import ProcessLocalFrontendWorkflowStateV1

if TYPE_CHECKING:
    from .stateful_context import ManagedStatefulContextV1


@dataclass(slots=True)
class AppWebContextV1:
    """Process-local private context for one managed application home."""

    managed_home: ManagedHomeV1
    browser_state: BrowserSafeApplicationStateV1
    managed_stateful: ManagedStatefulContextV1 = field(repr=False)
    frontend_profile: FrontendProfileStateV1 = field(repr=False)
    analyze_state: ProcessLocalFrontendWorkflowStateV1 = field(
        default_factory=ProcessLocalFrontendWorkflowStateV1,
        repr=False,
    )
    review_state: ProcessLocalFrontendWorkflowStateV1 = field(
        default_factory=ProcessLocalFrontendWorkflowStateV1,
        repr=False,
    )
    form_feedback: ProcessLocalFrontendFeedbackStateV1 = field(
        default_factory=ProcessLocalFrontendFeedbackStateV1,
        repr=False,
    )
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    profile_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    profile_redirect_return_to: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        from .stateful_context import ManagedStatefulContextV1

        if type(self.managed_home) is not ManagedHomeV1:
            raise ValueError("managed_home must be an exact ManagedHomeV1.")
        if type(self.browser_state) is not BrowserSafeApplicationStateV1:
            raise ValueError("browser_state must be an exact browser-safe state.")
        if type(self.analyze_state) is not ProcessLocalFrontendWorkflowStateV1:
            raise ValueError("analyze_state must be exact process-local workflow state.")
        if type(self.review_state) is not ProcessLocalFrontendWorkflowStateV1:
            raise ValueError("review_state must be exact process-local workflow state.")
        if type(self.form_feedback) is not ProcessLocalFrontendFeedbackStateV1:
            raise ValueError("form_feedback must be exact process-local feedback state.")
        if type(self.managed_stateful) is not ManagedStatefulContextV1:
            raise ValueError("managed_stateful must be exact managed stateful context.")
        if type(self.frontend_profile) is not FrontendProfileStateV1:
            raise ValueError("frontend_profile must be exact private profile state.")
        if self.frontend_profile.profile_path != self.managed_home.root / "frontend-profile.json":
            raise ValueError("Frontend profile path must be one direct managed-root child.")
        if self.profile_redirect_return_to is not None:
            raise ValueError("A new app context must not retain a profile redirect.")

    @classmethod
    def create(cls, managed_home: ManagedHomeV1) -> AppWebContextV1:
        from .stateful_context import ManagedStatefulContextV1

        return cls(
            managed_home=managed_home,
            browser_state=build_browser_safe_application_state_v1(),
            managed_stateful=ManagedStatefulContextV1(managed_home=managed_home),
            frontend_profile=build_frontend_profile_state_v1(managed_home.root),
        )
