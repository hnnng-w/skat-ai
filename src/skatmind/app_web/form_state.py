from __future__ import annotations

from dataclasses import dataclass, field

from .validation_contracts import (
    FRONTEND_VALIDATION_ACTIVE_FAMILIES,
    FrontendSubmittedFormStateV1,
)


@dataclass(slots=True)
class ProcessLocalFrontendFeedbackStateV1:
    """Bounded latest rejected attempt for each unified frontend family."""

    _generation: int = field(default=0, repr=False)
    _feedback: dict[
        str,
        tuple[object | None, FrontendSubmittedFormStateV1],
    ] = field(default_factory=dict, repr=False)

    def next_generation(self) -> int:
        self._generation += 1
        return self._generation

    def retain(
        self,
        family: str,
        state: FrontendSubmittedFormStateV1,
        *,
        active_identity: object | None,
    ) -> None:
        if family not in FRONTEND_VALIDATION_ACTIVE_FAMILIES:
            raise ValueError("family must identify one frontend feedback family.")
        if type(state) is not FrontendSubmittedFormStateV1:
            raise ValueError("state must be exact submitted form state.")
        if state.active_family_binding != family:
            raise ValueError("Submitted form binding must match its feedback family.")
        self._feedback[family] = (active_identity, state)

    def current(
        self,
        family: str,
        *,
        active_identity: object | None,
    ) -> FrontendSubmittedFormStateV1 | None:
        retained = self._feedback.get(family)
        if retained is None:
            return None
        retained_identity, state = retained
        if retained_identity is not active_identity:
            self._feedback.pop(family, None)
            return None
        return state

    def clear(self, family: str) -> None:
        if family not in FRONTEND_VALIDATION_ACTIVE_FAMILIES:
            raise ValueError("family must identify one frontend feedback family.")
        self._feedback.pop(family, None)

    @property
    def retained_family_count(self) -> int:
        return len(self._feedback)
