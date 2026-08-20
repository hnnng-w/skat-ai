from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skat_ai.bounded_search_information import SearchEligibility, assess_search_eligibility
from skat_ai.bounded_search_result import RequestedSearchBudget
from skat_ai.compatible_search_world import (
    CompatibleSearchWorldSelection,
    build_compatible_search_world_space,
    select_compatible_search_worlds,
)
from skat_ai.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS,
    INFORMATION_SET_SEARCH_PREPARATION_STATUSES,
    INFORMATION_SET_SEARCH_PREPARATION_VERSION,
    INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS,
    InformationSetSearchBudgetV1,
    InformationSetSearchRequestV1,
    validate_information_set_search_request_v1,
)
from skat_ai.information_set_search_policy import (
    is_information_set_fixed_policy_supported_for_actor_v1,
)
from skat_ai.information_set_search_state import (
    InformationSetSearchObservationV1,
    InformationSetSearchWorldStateV1,
    _serialize_exact_state,
    build_information_set_search_observation_v1,
    build_information_set_search_world_state_v1,
)
from skat_ai.rules import GAME_TYPES


def _serialize_eligibility(eligibility: SearchEligibility) -> dict[str, Any]:
    return {
        "eligible": eligibility.eligible,
        "unavailable_reason": eligibility.unavailable_reason,
        "remaining_plies": eligibility.remaining_plies,
        "remaining_tricks": eligibility.remaining_tricks,
        "configured_remaining_trick_limit": (
            eligibility.configured_remaining_trick_limit
        ),
    }


def _serialize_world_selection(
    selection: CompatibleSearchWorldSelection,
) -> dict[str, Any]:
    return {
        "selection_version": selection.selection_version,
        "available": selection.available,
        "unavailable_reason": selection.unavailable_reason,
        "selection_method": selection.selection_method,
        "world_coverage": selection.world_coverage,
        "compatible_world_count": selection.compatible_world_count,
        "selected_world_count": selection.selected_world_count,
        "sampled_world_count": selection.sampled_world_count,
        "unique_sampled_world_count": selection.unique_sampled_world_count,
        "legal_root_cards": list(selection.legal_root_cards),
        "exact_states": [
            _serialize_exact_state(state) for state in selection.exact_states
        ],
    }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class InformationSetSearchPreparationV1:
    information_set_search_preparation_version: int
    status: str
    unavailable_reason: str | None
    request: InformationSetSearchRequestV1
    eligibility: SearchEligibility
    world_selection: CompatibleSearchWorldSelection | None = field(repr=False)
    world_states: tuple[InformationSetSearchWorldStateV1, ...] = field(repr=False)
    root_information_set: InformationSetSearchObservationV1 | None
    root_legal_cards: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "InformationSetSearchPreparationV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> InformationSetSearchPreparationV1:
        result = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(result, field_name, field_value)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_set_search_preparation_version": (
                self.information_set_search_preparation_version
            ),
            "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "request": self.request.to_dict(),
            "eligibility": _serialize_eligibility(self.eligibility),
            "world_selection": (
                _serialize_world_selection(self.world_selection)
                if self.world_selection is not None
                else None
            ),
            "world_states": [state.to_dict() for state in self.world_states],
            "root_information_set": (
                self.root_information_set.to_dict()
                if self.root_information_set is not None
                else None
            ),
            "root_legal_cards": list(self.root_legal_cards),
        }


def _selection_budget(budget: InformationSetSearchBudgetV1) -> RequestedSearchBudget:
    return RequestedSearchBudget(
        max_remaining_tricks=budget.max_remaining_tricks,
        max_depth_plies=budget.max_depth_plies,
        max_nodes=budget.max_state_nodes,
        max_selected_worlds=budget.max_selected_worlds,
        max_sampled_worlds=budget.max_sampled_worlds,
        minimum_comparable_worlds=budget.minimum_comparable_worlds,
        wall_clock_timeout_ms=budget.wall_clock_timeout_ms,
    )


def _unavailable_preparation(
    *,
    request: InformationSetSearchRequestV1,
    eligibility: SearchEligibility,
    reason: str,
    world_selection: CompatibleSearchWorldSelection | None = None,
) -> InformationSetSearchPreparationV1:
    if reason not in INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS:
        raise ValueError("Unavailable preparation requires a canonical reason.")
    if world_selection is not None and world_selection.available:
        raise ValueError("Unavailable preparation cannot retain an available selection.")
    return InformationSetSearchPreparationV1._from_validated(
        information_set_search_preparation_version=(
            INFORMATION_SET_SEARCH_PREPARATION_VERSION
        ),
        status="unavailable",
        unavailable_reason=reason,
        request=request,
        eligibility=eligibility,
        world_selection=world_selection,
        world_states=(),
        root_information_set=None,
        root_legal_cards=(),
    )


def _information_model_is_available(request: InformationSetSearchRequestV1) -> bool:
    view = request.information_view
    if view.declarer_player == "me" and not view.declaration.hand_game:
        return len(view.known_skat_cards) == 2
    return not view.known_skat_cards


def _fixed_policies_are_role_supported(
    request: InformationSetSearchRequestV1,
) -> bool:
    return all(
        is_information_set_fixed_policy_supported_for_actor_v1(
            actor_player=player,
            declarer_player=request.information_view.declarer_player,
            policy_settings=request.policy_settings,
        )
        for player in ("left", "right")
    )


def prepare_information_set_search_v1(
    request: InformationSetSearchRequestV1,
) -> InformationSetSearchPreparationV1:
    """Builds one deterministic selected-world preparation without executing Search."""
    validate_information_set_search_request_v1(request)
    view = request.information_view
    eligibility = assess_search_eligibility(
        view,
        min(
            INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS,
            request.requested_budget.max_remaining_tricks,
        ),
    )
    if not eligibility.eligible:
        if eligibility.unavailable_reason not in INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS:
            raise ValueError("Eligibility returned a noncanonical unavailable reason.")
        return _unavailable_preparation(
            request=request,
            eligibility=eligibility,
            reason=eligibility.unavailable_reason,
        )
    if view.game_type not in GAME_TYPES:
        return _unavailable_preparation(
            request=request,
            eligibility=eligibility,
            reason="unsupported_game_type",
        )
    if not _fixed_policies_are_role_supported(request):
        return _unavailable_preparation(
            request=request,
            eligibility=eligibility,
            reason="unsupported_fixed_policy",
        )
    if not _information_model_is_available(request):
        return _unavailable_preparation(
            request=request,
            eligibility=eligibility,
            reason="information_set_model_unavailable",
        )

    world_space = build_compatible_search_world_space(view)
    selection = select_compatible_search_worlds(
        world_space=world_space,
        requested_budget=_selection_budget(request.requested_budget),
        random_seed=request.world_selection_seed,
    )
    if not selection.available:
        return _unavailable_preparation(
            request=request,
            eligibility=eligibility,
            reason="incompatible_world_space",
            world_selection=selection,
        )

    world_states = tuple(
        build_information_set_search_world_state_v1(
            information_view=view,
            exact_state=exact_state,
        )
        for exact_state in selection.exact_states
    )
    root_observations = tuple(
        build_information_set_search_observation_v1(world_state)
        for world_state in world_states
    )
    if not root_observations or any(
        observation != root_observations[0]
        for observation in root_observations[1:]
    ):
        return _unavailable_preparation(
            request=request,
            eligibility=eligibility,
            reason="information_set_model_unavailable",
        )
    root_information_set = root_observations[0]
    if root_information_set.actor_player != "me":
        raise ValueError("An available root Information Set must belong to me.")
    if root_information_set.legal_cards != selection.legal_root_cards:
        raise ValueError("Selected worlds have contradictory root legal Cards.")

    return InformationSetSearchPreparationV1._from_validated(
        information_set_search_preparation_version=(
            INFORMATION_SET_SEARCH_PREPARATION_VERSION
        ),
        status=INFORMATION_SET_SEARCH_PREPARATION_STATUSES[0],
        unavailable_reason=None,
        request=request,
        eligibility=eligibility,
        world_selection=selection,
        world_states=world_states,
        root_information_set=root_information_set,
        root_legal_cards=root_information_set.legal_cards,
    )
