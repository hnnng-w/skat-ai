import random
from dataclasses import dataclass, field

from skat_ai.bounded_search_information import SearchInformationView
from skat_ai.bounded_search_result import RequestedSearchBudget
from skat_ai.coherent_hidden_world import derive_simulation_child_seed
from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import (
    ExactSearchState,
    build_exact_search_state,
    get_exact_search_legal_cards,
)
from skat_ai.hidden_card_inference import (
    EFFECTIVE_CATEGORY_ORDER,
    OWNER_ORDER,
    CompatibleAssignmentProblem,
    CompatibleHiddenWorld,
    count_compatible_hidden_worlds,
    enumerate_compatible_hidden_worlds,
    get_public_effective_category,
    sample_compatible_hidden_worlds,
    validate_compatible_hidden_world,
)

COMPATIBLE_SEARCH_WORLD_SELECTION_VERSION = 1
COMPATIBLE_SEARCH_WORLD_SELECTION_STREAM = (
    "bounded_search_compatible_world_selection_v1"
)
COMPATIBLE_SEARCH_WORLD_SELECTION_METHODS = (
    "exact_enumeration",
    "uniform_iid_sampling",
)

_FULL_DECK = tuple(get_full_deck())
_FULL_DECK_SET = set(_FULL_DECK)


@dataclass(frozen=True, init=False)
class CompatibleSearchWorldSpace:
    """Private compatible assignments derived from one safe search view."""

    _information_view: SearchInformationView = field(repr=False)
    _assignment_problem: CompatibleAssignmentProblem = field(repr=False)
    compatible_world_count: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "Use build_compatible_search_world_space() to construct a search world space."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        information_view: SearchInformationView,
        assignment_problem: CompatibleAssignmentProblem,
        compatible_world_count: int,
    ) -> "CompatibleSearchWorldSpace":
        world_space = object.__new__(cls)
        object.__setattr__(world_space, "_information_view", information_view)
        object.__setattr__(world_space, "_assignment_problem", assignment_problem)
        object.__setattr__(
            world_space,
            "compatible_world_count",
            compatible_world_count,
        )
        return world_space


@dataclass(frozen=True)
class CompatibleSearchWorldSelection:
    """One frozen private world sequence for future common-world evaluation."""

    selection_version: int
    available: bool
    unavailable_reason: str | None
    selection_method: str | None
    world_coverage: str
    compatible_world_count: int
    selected_world_count: int
    sampled_world_count: int
    unique_sampled_world_count: int
    legal_root_cards: tuple[str, ...]
    exact_states: tuple[ExactSearchState, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            isinstance(self.selection_version, bool)
            or not isinstance(self.selection_version, int)
            or self.selection_version != COMPATIBLE_SEARCH_WORLD_SELECTION_VERSION
        ):
            raise ValueError("Unsupported compatible Search-world selection version.")
        if not isinstance(self.available, bool):
            raise ValueError("available must be a boolean.")
        if not isinstance(self.legal_root_cards, tuple):
            raise TypeError("legal_root_cards must be a tuple.")
        if not isinstance(self.exact_states, tuple):
            raise TypeError("exact_states must be a tuple.")
        if any(not isinstance(state, ExactSearchState) for state in self.exact_states):
            raise ValueError("exact_states must contain only ExactSearchState values.")
        if (
            any(
                not isinstance(card, str) or card not in _FULL_DECK_SET
                for card in self.legal_root_cards
            )
            or len(self.legal_root_cards) != len(set(self.legal_root_cards))
            or self.legal_root_cards
            != tuple(card for card in _FULL_DECK if card in self.legal_root_cards)
        ):
            raise ValueError("legal_root_cards must be unique and in canonical deck order.")
        for field_name in (
            "compatible_world_count",
            "selected_world_count",
            "sampled_world_count",
            "unique_sampled_world_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.selected_world_count != len(self.exact_states):
            raise ValueError("selected_world_count must match the exact-state sequence.")

        if not self.available:
            if self.unavailable_reason != "incompatible_world_space":
                raise ValueError("An unavailable selection requires incompatible_world_space.")
            if self.compatible_world_count != 0:
                raise ValueError("An incompatible world space must have zero worlds.")
            if self.selection_method is not None or self.world_coverage != "none":
                raise ValueError("An unavailable selection has no method or coverage.")
            if any(
                (
                    self.selected_world_count,
                    self.sampled_world_count,
                    self.unique_sampled_world_count,
                )
            ):
                raise ValueError("An unavailable selection cannot contain selected worlds.")
            if self.legal_root_cards:
                raise ValueError("An unavailable selection cannot contain legal root cards.")
            return

        if self.unavailable_reason is not None:
            raise ValueError("An available selection cannot have an unavailable reason.")
        if self.selection_method not in COMPATIBLE_SEARCH_WORLD_SELECTION_METHODS:
            raise ValueError(f"Invalid compatible-world selection method: {self.selection_method}")
        if self.compatible_world_count <= 0 or self.selected_world_count <= 0:
            raise ValueError("An available selection requires compatible selected worlds.")
        if any(
            get_exact_search_legal_cards(state) != self.legal_root_cards
            for state in self.exact_states
        ):
            raise ValueError("Every selected exact state must share legal_root_cards.")
        if self.selection_method == "exact_enumeration":
            if self.world_coverage != "all_compatible_worlds":
                raise ValueError("Exact enumeration requires all-compatible-world coverage.")
            if self.selected_world_count != self.compatible_world_count:
                raise ValueError("Exact enumeration must select every compatible world.")
            if self.sampled_world_count or self.unique_sampled_world_count:
                raise ValueError("Exact enumeration cannot report sampled worlds.")
            if len(set(self.exact_states)) != self.selected_world_count:
                raise ValueError("Exact enumeration cannot contain duplicate exact states.")
        else:
            if self.world_coverage != "sampled_compatible_worlds":
                raise ValueError("IID sampling requires sampled-compatible-world coverage.")
            if self.selected_world_count != self.sampled_world_count:
                raise ValueError("Every sampled draw must remain in the selected sequence.")
            if not 0 < self.unique_sampled_world_count <= self.sampled_world_count:
                raise ValueError("Sampled selection requires a valid unique-world count.")
            if self.unique_sampled_world_count != len(set(self.exact_states)):
                raise ValueError("unique_sampled_world_count must match distinct exact states.")
            if self.unique_sampled_world_count > self.compatible_world_count:
                raise ValueError(
                    "Unique sampled worlds cannot exceed the compatible world count."
                )


def _validated_exact_constraints(
    information_view: SearchInformationView,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    constraints_by_player = {}
    for constraint in information_view.hidden_card_constraints:
        if constraint.player not in {"me", "left", "right"}:
            raise ValueError(f"Invalid hidden-card constraint player: {constraint.player}")
        if constraint.player in constraints_by_player:
            raise ValueError(
                f"Duplicate hidden-card constraints for {constraint.player}."
            )
        if not isinstance(constraint.exact_cards, tuple):
            raise TypeError(f"Exact {constraint.player} cards must be a tuple.")
        invalid_cards = [
            card
            for card in constraint.exact_cards
            if not isinstance(card, str) or card not in _FULL_DECK_SET
        ]
        if invalid_cards:
            raise ValueError(
                f"Invalid exact cards for {constraint.player}: {invalid_cards}"
            )
        if len(constraint.exact_cards) != len(set(constraint.exact_cards)):
            raise ValueError(f"Exact {constraint.player} cards contain duplicates.")
        constraints_by_player[constraint.player] = constraint
    if set(constraints_by_player) != {"me", "left", "right"}:
        raise ValueError("Search hidden-card constraints must cover me, left, and right.")

    exact_by_player = {
        player: set(constraints_by_player[player].exact_cards)
        for player in ("me", "left", "right")
    }
    if exact_by_player["me"] != set(information_view.local_remaining_hand):
        raise ValueError("Local exact hidden-card constraints must match the local hand.")
    forbidden_by_player = {
        player: set(constraints_by_player[player].forbidden_effective_categories)
        for player in ("left", "right")
    }
    for player, categories in forbidden_by_player.items():
        invalid = categories.difference(EFFECTIVE_CATEGORY_ORDER)
        if invalid:
            raise ValueError(
                f"Invalid forbidden effective categories for {player}: {sorted(invalid)}"
            )
    return exact_by_player, forbidden_by_player


def _validate_public_exact_hands(
    information_view: SearchInformationView,
    exact_by_player: dict[str, set[str]],
) -> None:
    public_by_player = {}
    public_cards: set[str] = set()
    for constraint in information_view.public_hand_constraints:
        if constraint.player not in exact_by_player:
            raise ValueError(f"Invalid public hand player: {constraint.player}")
        if constraint.player in public_by_player:
            raise ValueError(f"Duplicate public hand constraint for {constraint.player}.")
        invalid_cards = [
            card
            for card in constraint.cards
            if not isinstance(card, str) or card not in _FULL_DECK_SET
        ]
        if invalid_cards:
            raise ValueError(
                f"Invalid public {constraint.player} hand cards: {invalid_cards}"
            )
        cards = set(constraint.cards)
        if len(cards) != len(constraint.cards):
            raise ValueError(f"Public {constraint.player} hand contains duplicate cards.")
        overlap = public_cards.intersection(cards)
        if overlap:
            raise ValueError(
                f"Public hands contain conflicting exact ownership: {sorted(overlap)}"
            )
        public_by_player[constraint.player] = cards
        public_cards.update(cards)
        if cards != exact_by_player[constraint.player]:
            raise ValueError(
                f"Public {constraint.player} hand disagrees with hidden-card constraints."
            )
    for player in ("left", "right"):
        if exact_by_player[player] and player not in public_by_player:
            raise ValueError(
                f"Exact {player} ownership requires an authorized public hand constraint."
            )


def build_compatible_search_world_space(
    information_view: SearchInformationView,
) -> CompatibleSearchWorldSpace:
    """Builds the canonical exact compatible-world space from one search view."""
    if not isinstance(information_view, SearchInformationView):
        raise ValueError("information_view must be a SearchInformationView.")

    size_players = tuple(item.player for item in information_view.remaining_hand_sizes)
    if len(size_players) != len(set(size_players)) or set(size_players) != {
        "me",
        "left",
        "right",
    }:
        raise ValueError("Search remaining hand sizes must cover me, left, and right once.")
    for item in information_view.remaining_hand_sizes:
        if (
            isinstance(item.card_count, bool)
            or not isinstance(item.card_count, int)
            or item.card_count < 0
        ):
            raise ValueError(
                f"Remaining hand size for {item.player} must be a non-negative integer."
            )
    if information_view.remaining_hand_size("me") != len(
        information_view.local_remaining_hand
    ):
        raise ValueError("The local remaining hand size must match the local hand.")

    completed_cards = tuple(
        play.card
        for trick in information_view.completed_tricks
        for play in trick.plays
    )
    current_cards = tuple(play.card for play in information_view.current_trick)
    known_cards = (
        *information_view.local_remaining_hand,
        *completed_cards,
        *current_cards,
        *information_view.known_skat_cards,
    )
    invalid_cards = [card for card in known_cards if card not in _FULL_DECK_SET]
    if invalid_cards:
        raise ValueError(f"Invalid cards in Search information view: {invalid_cards}")
    if len(known_cards) != len(set(known_cards)):
        raise ValueError("Search information view contains duplicate known cards.")
    if len(information_view.known_skat_cards) > 2:
        raise ValueError("Known out-of-play cards cannot exceed two cards.")

    exact_by_player, forbidden_by_player = _validated_exact_constraints(
        information_view
    )
    _validate_public_exact_hands(information_view, exact_by_player)
    assignment_cards = tuple(card for card in _FULL_DECK if card not in known_cards)
    assignment_card_set = set(assignment_cards)

    for player in ("left", "right"):
        exact_cards = exact_by_player[player]
        expected_size = information_view.remaining_hand_size(player)
        if exact_cards and len(exact_cards) != expected_size:
            raise ValueError(
                f"The exact public {player} hand has {len(exact_cards)} cards, "
                f"but the required hand size is {expected_size}."
            )
        unavailable = exact_cards.difference(assignment_card_set)
        if unavailable:
            raise ValueError(
                f"Exact public {player} cards are unavailable for assignment: "
                f"{sorted(unavailable)}"
            )
    overlap = exact_by_player["left"].intersection(exact_by_player["right"])
    if overlap:
        raise ValueError(f"Conflicting exact opponent ownership: {sorted(overlap)}")

    left_slots = information_view.remaining_hand_size("left")
    right_slots = information_view.remaining_hand_size("right")
    skat_slots = 2 - len(information_view.known_skat_cards)
    if len(assignment_cards) != left_slots + right_slots + skat_slots:
        raise ValueError(
            "Search assignment cards do not reconcile with left, right, and Skat slots."
        )

    exact_owner_by_card = {
        card: player
        for player in ("left", "right")
        for card in exact_by_player[player]
    }
    allowed_by_card = []
    for card in assignment_cards:
        allowed = []
        for owner in OWNER_ORDER:
            exact_owner = exact_owner_by_card.get(card)
            if exact_owner is not None and owner != exact_owner:
                continue
            if owner == "skat":
                allowed.append(owner)
                continue
            owner_exact = exact_by_player[owner]
            if owner_exact and card not in owner_exact:
                continue
            if get_public_effective_category(
                card,
                information_view.game_type,
            ) in forbidden_by_player[owner]:
                continue
            allowed.append(owner)
        allowed_by_card.append((card, tuple(allowed)))

    problem = CompatibleAssignmentProblem(
        cards=assignment_cards,
        left_slots=left_slots,
        right_slots=right_slots,
        skat_slots=skat_slots,
        allowed_locations_by_card=tuple(allowed_by_card),
    )
    compatible_world_count = count_compatible_hidden_worlds(problem)
    return CompatibleSearchWorldSpace._from_validated(
        information_view=information_view,
        assignment_problem=problem,
        compatible_world_count=compatible_world_count,
    )


def build_exact_search_state_from_compatible_world(
    *,
    world_space: CompatibleSearchWorldSpace,
    world: CompatibleHiddenWorld,
) -> ExactSearchState:
    """Strictly materializes one private exact state from one compatible world."""
    if not isinstance(world_space, CompatibleSearchWorldSpace):
        raise ValueError("world_space must be a CompatibleSearchWorldSpace.")
    validate_compatible_hidden_world(world_space._assignment_problem, world)
    view = world_space._information_view
    out_of_play_cards = (*view.known_skat_cards, *world.hypothetical_skat)
    if len(out_of_play_cards) != 2:
        raise ValueError("A compatible Search world must produce two out-of-play cards.")
    return build_exact_search_state(
        declaration=view.declaration,
        declarer_player=view.declarer_player,
        remaining_hands={
            "me": view.local_remaining_hand,
            "left": world.left_hand,
            "right": world.right_hand,
        },
        current_trick=tuple(
            (play.player, play.card) for play in view.current_trick
        ),
        next_player=view.next_player,
        declarer_trick_points=view.declarer_points,
        defender_trick_points=view.defender_points,
        declarer_completed_tricks=view.declarer_trick_count,
        defender_completed_tricks=view.defender_trick_count,
        out_of_play_cards=out_of_play_cards,
    )


def _common_legal_root_cards(
    exact_states: tuple[ExactSearchState, ...],
) -> tuple[str, ...]:
    if not exact_states:
        return ()
    expected = get_exact_search_legal_cards(exact_states[0])
    for state in exact_states[1:]:
        if get_exact_search_legal_cards(state) != expected:
            raise ValueError(
                "Compatible Search worlds do not share one legal root-card tuple."
            )
    return expected


def select_compatible_search_worlds(
    *,
    world_space: CompatibleSearchWorldSpace,
    requested_budget: RequestedSearchBudget,
    random_seed: int,
) -> CompatibleSearchWorldSelection:
    """Freezes one exhaustive or deterministic IID compatible-world sequence."""
    if not isinstance(world_space, CompatibleSearchWorldSpace):
        raise ValueError("world_space must be a CompatibleSearchWorldSpace.")
    if not isinstance(requested_budget, RequestedSearchBudget):
        raise ValueError("requested_budget must be a RequestedSearchBudget.")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int):
        raise ValueError("random_seed must be an integer and must not be a boolean.")

    count = world_space.compatible_world_count
    if count == 0:
        return CompatibleSearchWorldSelection(
            selection_version=COMPATIBLE_SEARCH_WORLD_SELECTION_VERSION,
            available=False,
            unavailable_reason="incompatible_world_space",
            selection_method=None,
            world_coverage="none",
            compatible_world_count=0,
            selected_world_count=0,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            legal_root_cards=(),
            exact_states=(),
        )

    if count <= requested_budget.max_selected_worlds:
        worlds = enumerate_compatible_hidden_worlds(
            world_space._assignment_problem,
            requested_budget.max_selected_worlds,
        )
        method = "exact_enumeration"
        coverage = "all_compatible_worlds"
        sampled_count = 0
    else:
        child_seed = derive_simulation_child_seed(
            random_seed,
            COMPATIBLE_SEARCH_WORLD_SELECTION_STREAM,
        )
        if child_seed is None:
            raise ValueError("Compatible Search-world child seed could not be derived.")
        worlds = sample_compatible_hidden_worlds(
            world_space._assignment_problem,
            requested_budget.max_sampled_worlds,
            random.Random(child_seed),
        )
        method = "uniform_iid_sampling"
        coverage = "sampled_compatible_worlds"
        sampled_count = len(worlds)

    exact_states = tuple(
        build_exact_search_state_from_compatible_world(
            world_space=world_space,
            world=world,
        )
        for world in worlds
    )
    return CompatibleSearchWorldSelection(
        selection_version=COMPATIBLE_SEARCH_WORLD_SELECTION_VERSION,
        available=True,
        unavailable_reason=None,
        selection_method=method,
        world_coverage=coverage,
        compatible_world_count=count,
        selected_world_count=len(exact_states),
        sampled_world_count=sampled_count,
        unique_sampled_world_count=(
            len(set(exact_states)) if sampled_count else 0
        ),
        legal_root_cards=_common_legal_root_cards(exact_states),
        exact_states=exact_states,
    )
