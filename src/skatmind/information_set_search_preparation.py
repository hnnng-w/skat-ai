from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skatmind.bounded_search_information import (
    SearchEligibility,
    SearchPublicPlay,
    assess_search_eligibility,
)
from skatmind.bounded_search_result import RequestedSearchBudget
from skatmind.compatible_search_world import (
    CompatibleSearchWorldSelection,
    build_compatible_search_world_space,
    select_compatible_search_worlds,
)
from skatmind.errors import SkatMindInvariantError
from skatmind.exact_search_state import ExactSearchState
from skatmind.hidden_card_inference import PLAYER_ORDER
from skatmind.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS,
    INFORMATION_SET_SEARCH_OBSERVATION_VERSION,
    INFORMATION_SET_SEARCH_PREPARATION_STATUSES,
    INFORMATION_SET_SEARCH_PREPARATION_VERSION,
    INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS,
    INFORMATION_SET_SEARCH_WORLD_STATE_VERSION,
    InformationSetFixedPlayerPolicyV1,
    InformationSetSearchBudgetV1,
    InformationSetSearchPolicySettingsV1,
    InformationSetSearchRequestV1,
    validate_information_set_search_request_v1,
)
from skatmind.information_set_search_policy import (
    is_information_set_fixed_policy_supported_for_actor_v1,
)
from skatmind.information_set_search_state import (
    InformationSetSearchObservationV1,
    InformationSetSearchWorldStateV1,
    _copy_and_validate_public_hands,
    _derive_public_void_constraints,
    _serialize_exact_state,
    _validate_hidden_constraints,
    _validate_public_history,
    build_information_set_search_observation_v1,
    build_information_set_search_world_state_v1,
)
from skatmind.rules import GAME_TYPES


def _serialize_eligibility(eligibility: SearchEligibility) -> dict[str, Any]:
    return {
        "eligible": eligibility.eligible,
        "unavailable_reason": eligibility.unavailable_reason,
        "remaining_plies": eligibility.remaining_plies,
        "remaining_tricks": eligibility.remaining_tricks,
        "configured_remaining_trick_limit": (eligibility.configured_remaining_trick_limit),
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
        "exact_states": [_serialize_exact_state(state) for state in selection.exact_states],
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
        information_set_search_preparation_version=(INFORMATION_SET_SEARCH_PREPARATION_VERSION),
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
        build_information_set_search_observation_v1(world_state) for world_state in world_states
    )
    if not root_observations or any(
        observation != root_observations[0] for observation in root_observations[1:]
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
        information_set_search_preparation_version=(INFORMATION_SET_SEARCH_PREPARATION_VERSION),
        status=INFORMATION_SET_SEARCH_PREPARATION_STATUSES[0],
        unavailable_reason=None,
        request=request,
        eligibility=eligibility,
        world_selection=selection,
        world_states=world_states,
        root_information_set=root_information_set,
        root_legal_cards=root_information_set.legal_cards,
    )


def _expected_unavailable_reason(
    preparation: InformationSetSearchPreparationV1,
) -> str | None:
    eligibility = preparation.eligibility
    request = preparation.request
    if not eligibility.eligible:
        return eligibility.unavailable_reason
    if request.information_view.game_type not in GAME_TYPES:
        return "unsupported_game_type"
    if not _fixed_policies_are_role_supported(request):
        return "unsupported_fixed_policy"
    if not _information_model_is_available(request):
        return "information_set_model_unavailable"
    selection = preparation.world_selection
    if selection is not None and not selection.available:
        return "incompatible_world_space"
    return None


def _validate_retained_request(request: InformationSetSearchRequestV1) -> None:
    budget = request.requested_budget
    rebuilt_budget = InformationSetSearchBudgetV1(
        information_set_search_budget_version=(budget.information_set_search_budget_version),
        max_remaining_tricks=budget.max_remaining_tricks,
        max_depth_plies=budget.max_depth_plies,
        max_state_nodes=budget.max_state_nodes,
        max_information_sets=budget.max_information_sets,
        max_selected_worlds=budget.max_selected_worlds,
        max_sampled_worlds=budget.max_sampled_worlds,
        minimum_comparable_worlds=budget.minimum_comparable_worlds,
        wall_clock_timeout_ms=budget.wall_clock_timeout_ms,
    )
    rebuilt_fixed_policies = tuple(
        InformationSetFixedPlayerPolicyV1(
            player=item.player,
            lead_policy=item.lead_policy,
            response_policy=item.response_policy,
            tie_policy=item.tie_policy,
        )
        for item in request.policy_settings.fixed_player_policies
    )
    rebuilt_settings = InformationSetSearchPolicySettingsV1(
        information_set_search_policy_settings_version=(
            request.policy_settings.information_set_search_policy_settings_version
        ),
        controlled_player=request.policy_settings.controlled_player,
        control_scope=request.policy_settings.control_scope,
        fixed_player_policies=rebuilt_fixed_policies,
    )
    rebuilt_request = InformationSetSearchRequestV1(
        information_set_search_request_version=(request.information_set_search_request_version),
        search_method=request.search_method,
        information_view=request.information_view,
        requested_budget=rebuilt_budget,
        world_selection_seed=request.world_selection_seed,
        policy_settings=rebuilt_settings,
    )
    if rebuilt_request != request:
        raise ValueError("A retained Preparation changed its canonical Request.")


def _validate_retained_world_state(
    *,
    world_state: InformationSetSearchWorldStateV1,
    exact_state: ExactSearchState,
    preparation: InformationSetSearchPreparationV1,
) -> InformationSetSearchObservationV1:
    request = preparation.request
    view = request.information_view
    eligibility = preparation.eligibility
    if type(world_state) is not InformationSetSearchWorldStateV1:
        raise ValueError("A retained World State has an invalid type.")
    if (
        isinstance(world_state.information_set_search_world_state_version, bool)
        or not isinstance(
            world_state.information_set_search_world_state_version,
            int,
        )
        or world_state.information_set_search_world_state_version
        != INFORMATION_SET_SEARCH_WORLD_STATE_VERSION
    ):
        raise ValueError("A retained World State has an invalid version.")
    if world_state.exact_state is not exact_state:
        raise ValueError("Retained Exact States and World States changed order.")
    if (
        world_state.source != view.source
        or world_state.information_cutoff != view.information_cutoff
        or world_state.root_perspective_player != "me"
        or world_state.root_visible_out_of_play_cards != view.known_skat_cards
        or world_state.public_completed_tricks != view.completed_tricks
    ):
        raise ValueError("A retained World State changed root public facts.")
    expected_public_hands = tuple(
        sorted(
            view.public_hand_constraints,
            key=lambda item: PLAYER_ORDER.index(item.player),
        )
    )
    if world_state.public_hand_constraints != expected_public_hands:
        raise ValueError("A retained World State changed public hands.")

    state = world_state.exact_state
    if type(state) is not ExactSearchState:
        raise ValueError("A retained World State has an invalid Exact State.")
    exact_current_trick = tuple(
        SearchPublicPlay(player=play.player, card=play.card) for play in state.current_trick
    )
    if exact_current_trick != view.current_trick:
        raise ValueError("A retained Exact State changed the root current Trick.")
    if (
        state.declaration != view.declaration
        or state.declarer_player != view.declarer_player
        or state.next_player != view.next_player
        or state.hand_for("me") != view.local_remaining_hand
        or state.declarer_trick_points != view.declarer_points
        or state.defender_trick_points != view.defender_points
        or state.declarer_completed_tricks != view.declarer_trick_count
        or state.defender_completed_tricks != view.defender_trick_count
        or state.remaining_tricks != eligibility.remaining_tricks
    ):
        raise ValueError("A retained Exact State changed root Search facts.")
    if tuple((item.player, item.card_count) for item in view.remaining_hand_sizes) != tuple(
        (player, len(state.hand_for(player))) for player in PLAYER_ORDER
    ):
        raise ValueError("A retained Exact State changed root hand sizes.")
    _validate_public_history(
        completed_tricks=world_state.public_completed_tricks,
        exact_state=state,
    )
    validated_public_hands = _copy_and_validate_public_hands(
        constraints=world_state.public_hand_constraints,
        exact_state=state,
    )
    if validated_public_hands != world_state.public_hand_constraints:
        raise ValueError("A retained World State changed canonical public hands.")
    expected_voids = _derive_public_void_constraints(
        completed_tricks=world_state.public_completed_tricks,
        current_trick=view.current_trick,
        game_type=view.game_type,
    )
    if world_state.public_void_constraints != expected_voids:
        raise ValueError("A retained World State changed public void evidence.")
    _validate_hidden_constraints(
        information_view=view,
        exact_state=state,
        public_hands=validated_public_hands,
        public_voids=expected_voids,
    )
    if not set(world_state.root_visible_out_of_play_cards).issubset(state.out_of_play_cards):
        raise ValueError("Root-visible out-of-play Cards changed exact ownership.")
    if (
        state.declarer_player == "me"
        and not state.declaration.hand_game
        and world_state.root_visible_out_of_play_cards != state.out_of_play_cards
    ):
        raise ValueError("Declarer-visible out-of-play Cards changed exact ownership.")
    return build_information_set_search_observation_v1(world_state)


def validate_information_set_search_preparation_v1(
    preparation: InformationSetSearchPreparationV1,
) -> None:
    """Reconciles one retained Preparation without rebuilding selected Worlds."""
    if type(preparation) is not InformationSetSearchPreparationV1:
        raise ValueError("preparation must be an InformationSetSearchPreparationV1.")
    try:
        if preparation.information_set_search_preparation_version != (
            INFORMATION_SET_SEARCH_PREPARATION_VERSION
        ) or isinstance(preparation.information_set_search_preparation_version, bool):
            raise ValueError("Unsupported information-set Search Preparation version.")
        if preparation.status not in INFORMATION_SET_SEARCH_PREPARATION_STATUSES:
            raise ValueError("A retained Preparation has an invalid status.")
        if type(preparation.request) is not InformationSetSearchRequestV1:
            raise ValueError("A retained Preparation has an invalid Request.")
        _validate_retained_request(preparation.request)
        expected_eligibility = assess_search_eligibility(
            preparation.request.information_view,
            min(
                INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS,
                preparation.request.requested_budget.max_remaining_tricks,
            ),
        )
        if preparation.eligibility != expected_eligibility:
            raise ValueError("A retained Preparation changed Search eligibility.")

        selection = preparation.world_selection
        if selection is not None:
            if type(selection) is not CompatibleSearchWorldSelection:
                raise ValueError("A retained Preparation has an invalid World selection.")
            selection.__post_init__()

        expected_reason = _expected_unavailable_reason(preparation)
        if preparation.status == "unavailable":
            if preparation.unavailable_reason not in (INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS):
                raise ValueError("An unavailable Preparation has a noncanonical reason.")
            if selection is not None and selection.available:
                raise ValueError("An unavailable Preparation retained an available selection.")
            if preparation.unavailable_reason == "incompatible_world_space":
                if selection is None:
                    raise ValueError(
                        "Incompatible-world unavailability requires its zero selection."
                    )
            elif selection is not None:
                raise ValueError("Pre-selection unavailability cannot retain a World selection.")
            if (
                preparation.world_states
                or preparation.root_information_set is not None
                or preparation.root_legal_cards
            ):
                raise ValueError("An unavailable Preparation retained executable values.")
            return

        if preparation.unavailable_reason is not None or expected_reason is not None:
            raise ValueError("An available Preparation retained unavailable facts.")
        if selection is None or not selection.available:
            raise ValueError("An available Preparation requires an available selection.")
        if not preparation.eligibility.eligible:
            raise ValueError("An available Preparation requires eligible Search state.")
        if (
            not 1
            <= preparation.eligibility.remaining_tricks
            <= (INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS)
        ):
            raise ValueError("An available Preparation exceeds exact Trick eligibility.")
        if selection.selected_world_count != len(
            preparation.world_states
        ) or selection.selected_world_count != len(selection.exact_states):
            raise ValueError("Selected World counts do not reconcile.")
        budget = preparation.request.requested_budget
        if (
            selection.selected_world_count > budget.max_selected_worlds
            or selection.sampled_world_count > budget.max_sampled_worlds
        ):
            raise ValueError("Selected World counts exceed the retained Request budget.")
        if (
            selection.selection_method == "uniform_iid_sampling"
            and selection.sampled_world_count != budget.max_sampled_worlds
        ):
            raise ValueError("Sampled draw multiplicity changed after Preparation.")

        observations = tuple(
            _validate_retained_world_state(
                world_state=world_state,
                exact_state=exact_state,
                preparation=preparation,
            )
            for world_state, exact_state in zip(
                preparation.world_states,
                selection.exact_states,
                strict=True,
            )
        )
        if not observations or any(item != observations[0] for item in observations[1:]):
            raise ValueError("Selected Worlds do not share one root Information Set.")
        root_information_set = preparation.root_information_set
        if (
            type(root_information_set) is not InformationSetSearchObservationV1
            or isinstance(
                root_information_set.information_set_search_observation_version,
                bool,
            )
            or not isinstance(
                root_information_set.information_set_search_observation_version,
                int,
            )
            or root_information_set.information_set_search_observation_version
            != INFORMATION_SET_SEARCH_OBSERVATION_VERSION
            or root_information_set != observations[0]
            or root_information_set.actor_player != "me"
        ):
            raise ValueError("The retained root Information Set changed.")
        if (
            preparation.root_legal_cards != observations[0].legal_cards
            or preparation.root_legal_cards != selection.legal_root_cards
        ):
            raise ValueError("The retained root legal Cards changed.")
        if not _fixed_policies_are_role_supported(preparation.request):
            raise ValueError("A retained fixed Policy is invalid for its role.")
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Information-set Search Preparation is internally inconsistent."
        ) from error
