from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skatmind.bounded_search_information import (
    SEARCH_INFORMATION_CUTOFF,
    SEARCH_INFORMATION_SOURCES,
    SearchCompletedTrick,
    SearchInformationView,
    SearchPublicPlay,
    SearchRemainingHandSize,
)
from skatmind.deck import get_full_deck
from skatmind.exact_search_state import (
    ExactSearchState,
    apply_exact_search_card,
    get_exact_search_legal_cards,
)
from skatmind.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
)
from skatmind.hidden_card_inference import (
    EFFECTIVE_CATEGORY_ORDER,
    PLAYER_ORDER,
    get_public_effective_category,
)
from skatmind.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_OBSERVATION_VERSION,
    INFORMATION_SET_SEARCH_WORLD_STATE_VERSION,
)
from skatmind.public_hand_constraint import (
    DECLARED_OUVERT_SOURCE,
    DECLARER_EXPOSURE_CONTINUATION_SOURCE,
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PUBLIC_HAND_VISIBILITY_SCOPE,
    PublicHandConstraint,
    build_serializable_public_hand_constraints,
    canonicalize_cards,
    remove_public_hand_cards,
)
from skatmind.rules import get_trick_points, get_trick_winner
from skatmind.side_ownership import get_player_side
from skatmind.turn_phase import CONCRETE_PLAYERS, derive_next_player

_FULL_DECK = tuple(get_full_deck())
_FULL_DECK_SET = set(_FULL_DECK)


def _validate_cards(cards: tuple[str, ...], context: str) -> None:
    if not isinstance(cards, tuple):
        raise TypeError(f"{context} must be a tuple.")
    if any(not isinstance(card, str) or card not in _FULL_DECK_SET for card in cards):
        raise ValueError(f"{context} contains an invalid Card.")
    if len(cards) != len(set(cards)):
        raise ValueError(f"{context} contains duplicate Cards.")
    if cards != canonicalize_cards(cards):
        raise ValueError(f"{context} must use canonical Card order.")


def _serialize_play(play: SearchPublicPlay) -> dict[str, str]:
    return {"player": play.player, "card": play.card}


def _serialize_completed_trick(trick: SearchCompletedTrick) -> dict[str, Any]:
    return {
        "plays": [_serialize_play(play) for play in trick.plays],
        "winner_player": trick.winner_player,
        "winner_side": trick.winner_side,
        "trick_points": trick.trick_points,
    }


def _serialize_exact_state(state: ExactSearchState) -> dict[str, Any]:
    return {
        "declaration": build_serializable_game_declaration(state.declaration),
        "declarer_player": state.declarer_player,
        "hands": {
            player: list(state.hand_for(player)) for player in CONCRETE_PLAYERS
        },
        "current_trick": [
            {"player": play.player, "card": play.card}
            for play in state.current_trick
        ],
        "next_player": state.next_player,
        "declarer_trick_points": state.declarer_trick_points,
        "defender_trick_points": state.defender_trick_points,
        "declarer_completed_tricks": state.declarer_completed_tricks,
        "defender_completed_tricks": state.defender_completed_tricks,
        "out_of_play_cards": list(state.out_of_play_cards),
    }


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetPublicVoidConstraintV1:
    player: str
    forbidden_effective_categories: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.player not in CONCRETE_PLAYERS:
            raise ValueError(f"Invalid public void-constraint Player: {self.player}")
        if not isinstance(self.forbidden_effective_categories, tuple):
            raise TypeError("forbidden_effective_categories must be a tuple.")
        categories = self.forbidden_effective_categories
        if any(category not in EFFECTIVE_CATEGORY_ORDER for category in categories):
            raise ValueError("A public void constraint contains an invalid category.")
        canonical = tuple(
            category for category in EFFECTIVE_CATEGORY_ORDER if category in categories
        )
        if len(categories) != len(set(categories)) or categories != canonical:
            raise ValueError("Public void categories must be unique and canonical.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "player": self.player,
            "forbidden_effective_categories": list(
                self.forbidden_effective_categories
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class InformationSetSearchWorldStateV1:
    information_set_search_world_state_version: int
    source: str
    information_cutoff: str
    root_perspective_player: str
    root_visible_out_of_play_cards: tuple[str, ...]
    exact_state: ExactSearchState = field(repr=False)
    public_completed_tricks: tuple[SearchCompletedTrick, ...]
    public_hand_constraints: tuple[PublicHandConstraint, ...]
    public_void_constraints: tuple[InformationSetPublicVoidConstraintV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "InformationSetSearchWorldStateV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> InformationSetSearchWorldStateV1:
        result = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(result, field_name, field_value)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_set_search_world_state_version": (
                self.information_set_search_world_state_version
            ),
            "source": self.source,
            "information_cutoff": self.information_cutoff,
            "root_perspective_player": self.root_perspective_player,
            "root_visible_out_of_play_cards": list(
                self.root_visible_out_of_play_cards
            ),
            "exact_state": _serialize_exact_state(self.exact_state),
            "public_completed_tricks": [
                _serialize_completed_trick(trick)
                for trick in self.public_completed_tricks
            ],
            "public_hand_constraints": build_serializable_public_hand_constraints(
                self.public_hand_constraints
            ),
            "public_void_constraints": [
                item.to_dict() for item in self.public_void_constraints
            ],
        }


def _copy_completed_tricks(
    completed_tricks: tuple[SearchCompletedTrick, ...],
) -> tuple[SearchCompletedTrick, ...]:
    if not isinstance(completed_tricks, tuple):
        raise TypeError("completed_tricks must be a tuple.")
    if any(not isinstance(trick, SearchCompletedTrick) for trick in completed_tricks):
        raise ValueError("Public history must contain SearchCompletedTrick values.")
    if any(not isinstance(trick.plays, tuple) for trick in completed_tricks):
        raise TypeError("Every public completed Trick must contain a Play tuple.")
    return tuple(
        SearchCompletedTrick(
            plays=tuple(
                SearchPublicPlay(player=play.player, card=play.card)
                for play in trick.plays
            ),
            winner_player=trick.winner_player,
            winner_side=trick.winner_side,
            trick_points=trick.trick_points,
        )
        for trick in completed_tricks
    )


def _validate_public_history(
    *,
    completed_tricks: tuple[SearchCompletedTrick, ...],
    exact_state: ExactSearchState,
) -> None:
    required_leader: str | None = None
    public_cards: list[str] = []
    declarer_points = 0
    defender_points = 0
    declarer_tricks = 0
    defender_tricks = 0
    for index, trick in enumerate(completed_tricks, start=1):
        if not isinstance(trick, SearchCompletedTrick):
            raise ValueError("Public history must contain SearchCompletedTrick values.")
        if not isinstance(trick.plays, tuple) or len(trick.plays) != 3:
            raise ValueError(f"Public completed Trick {index} must contain three Plays.")
        players = tuple(play.player for play in trick.plays)
        cards = tuple(play.card for play in trick.plays)
        if any(player not in CONCRETE_PLAYERS for player in players):
            raise ValueError(f"Public completed Trick {index} has an invalid Player.")
        if players != tuple(derive_next_player(players[0], offset) for offset in range(3)):
            raise ValueError(f"Public completed Trick {index} has invalid Player order.")
        if required_leader is not None and players[0] != required_leader:
            raise ValueError(f"Public completed Trick {index} has the wrong leader.")
        if any(card not in _FULL_DECK_SET for card in cards):
            raise ValueError(f"Public completed Trick {index} contains an invalid Card.")
        winner = players[get_trick_winner(list(cards), exact_state.declaration.game_type)]
        winner_side = get_player_side(winner, exact_state.declarer_player)
        points = get_trick_points(list(cards))
        if (
            trick.winner_player != winner
            or trick.winner_side != winner_side
            or trick.trick_points != points
        ):
            raise ValueError(f"Public completed Trick {index} has contradictory facts.")
        required_leader = winner
        public_cards.extend(cards)
        if winner_side == "declarer":
            declarer_points += points
            declarer_tricks += 1
        else:
            defender_points += points
            defender_tricks += 1

    if len(public_cards) != len(set(public_cards)):
        raise ValueError("Public completed Trick history contains duplicate Cards.")
    exact_current = tuple(
        SearchPublicPlay(player=play.player, card=play.card)
        for play in exact_state.current_trick
    )
    if exact_current:
        if required_leader is not None and exact_current[0].player != required_leader:
            raise ValueError("The current Trick contradicts the public winner history.")
    elif required_leader is not None and not exact_state.is_terminal:
        if exact_state.next_player != required_leader:
            raise ValueError("The next Player contradicts the public winner history.")

    explicit_cards = {
        *(card for hand in exact_state.hands for card in hand),
        *(play.card for play in exact_state.current_trick),
        *exact_state.out_of_play_cards,
    }
    implicit_completed = set(_FULL_DECK).difference(explicit_cards)
    if set(public_cards) != implicit_completed:
        raise ValueError("Exact and public completed Card histories disagree.")
    if (
        declarer_points != exact_state.declarer_trick_points
        or defender_points != exact_state.defender_trick_points
        or declarer_tricks != exact_state.declarer_completed_tricks
        or defender_tricks != exact_state.defender_completed_tricks
    ):
        raise ValueError("Exact and public completed Trick totals disagree.")


def _derive_public_void_constraints(
    *,
    completed_tricks: tuple[SearchCompletedTrick, ...],
    current_trick: tuple[SearchPublicPlay, ...],
    game_type: str,
) -> tuple[InformationSetPublicVoidConstraintV1, ...]:
    forbidden: dict[str, set[str]] = {player: set() for player in CONCRETE_PLAYERS}
    trick_sequences = (
        *(trick.plays for trick in completed_tricks),
        current_trick,
    )
    for plays in trick_sequences:
        if not plays:
            continue
        led_category = get_public_effective_category(plays[0].card, game_type)
        for play_index, play in enumerate(plays):
            played_category = get_public_effective_category(play.card, game_type)
            if played_category in forbidden[play.player]:
                raise ValueError(
                    f"Public history assigns {played_category} to {play.player} after "
                    "confirming that Player void."
                )
            if play_index > 0 and played_category != led_category:
                forbidden[play.player].add(led_category)
    return tuple(
        InformationSetPublicVoidConstraintV1(
            player=player,
            forbidden_effective_categories=tuple(
                category
                for category in EFFECTIVE_CATEGORY_ORDER
                if category in forbidden[player]
            ),
        )
        for player in PLAYER_ORDER
    )


def _copy_and_validate_public_hands(
    *,
    constraints: tuple[PublicHandConstraint, ...],
    exact_state: ExactSearchState,
) -> tuple[PublicHandConstraint, ...]:
    if not isinstance(constraints, tuple):
        raise TypeError("public_hand_constraints must be a tuple.")
    copied: list[PublicHandConstraint] = []
    players: set[str] = set()
    for constraint in constraints:
        if not isinstance(constraint, PublicHandConstraint):
            raise ValueError("An invalid public hand constraint was supplied.")
        if constraint.player not in CONCRETE_PLAYERS or constraint.player in players:
            raise ValueError("Public hands must cover each constrained Player at most once.")
        players.add(constraint.player)
        if constraint.visibility_scope != PUBLIC_HAND_VISIBILITY_SCOPE:
            raise ValueError("Information-set Search public hands must be visible to all.")
        cards = tuple(constraint.cards)
        _validate_cards(cards, f"public {constraint.player} hand")
        if cards != exact_state.hand_for(constraint.player):
            raise ValueError(f"Public {constraint.player} hand contradicts exact ownership.")
        if constraint.source == DECLARED_OUVERT_SOURCE:
            if (
                not exact_state.declaration.ouvert
                or constraint.player != exact_state.declarer_player
            ):
                raise ValueError("Declared-Ouvert public hand authorization is invalid.")
        elif constraint.source == DECLARER_EXPOSURE_CONTINUATION_SOURCE:
            if constraint.player != exact_state.declarer_player:
                raise ValueError("Declarer exposure must expose the Declarer hand.")
        elif constraint.source == DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE:
            if constraint.player == exact_state.declarer_player:
                raise ValueError("Defender open play cannot expose the Declarer hand.")
        else:
            raise ValueError("Unsupported information-set Search public-hand source.")
        copied.append(
            PublicHandConstraint(
                player=constraint.player,
                cards=canonicalize_cards(cards),
                visibility_scope=constraint.visibility_scope,
                source=constraint.source,
            )
        )
    return tuple(sorted(copied, key=lambda item: PLAYER_ORDER.index(item.player)))


def _validate_hidden_constraints(
    *,
    information_view: SearchInformationView,
    exact_state: ExactSearchState,
    public_hands: tuple[PublicHandConstraint, ...],
    public_voids: tuple[InformationSetPublicVoidConstraintV1, ...],
) -> None:
    hidden = information_view.hidden_card_constraints
    if not isinstance(hidden, tuple):
        raise TypeError("hidden_card_constraints must be a tuple.")
    if tuple(item.player for item in hidden) != PLAYER_ORDER:
        raise ValueError("Hidden constraints must cover me, left, and right canonically.")
    public_by_player = {item.player: item for item in public_hands}
    void_by_player = {item.player: item for item in public_voids}
    for item in hidden:
        if item.forbidden_effective_categories != (
            void_by_player[item.player].forbidden_effective_categories
        ):
            raise ValueError("Retained hidden constraints contain non-public void facts.")
        exact_cards = tuple(item.exact_cards)
        _validate_cards(exact_cards, f"exact {item.player} constraints")
        if item.player == "me":
            if exact_cards != exact_state.hand_for("me"):
                raise ValueError("Local exact constraints contradict the exact hand.")
        elif item.player in public_by_player:
            if exact_cards != exact_state.hand_for(item.player):
                raise ValueError("Public exact constraints contradict the exact hand.")
        elif exact_cards:
            raise ValueError("Private opponent ownership cannot enter public constraints.")
        for card in exact_state.hand_for(item.player):
            category = get_public_effective_category(
                card,
                exact_state.declaration.game_type,
            )
            if category in item.forbidden_effective_categories:
                raise ValueError("Exact ownership contradicts a public void constraint.")


def build_information_set_search_world_state_v1(
    *,
    information_view: SearchInformationView,
    exact_state: ExactSearchState,
) -> InformationSetSearchWorldStateV1:
    if not isinstance(information_view, SearchInformationView):
        raise ValueError("information_view must be a SearchInformationView.")
    if not isinstance(exact_state, ExactSearchState):
        raise ValueError("exact_state must be an ExactSearchState.")
    if information_view.source not in SEARCH_INFORMATION_SOURCES:
        raise ValueError("Unsupported information-set Search source.")
    if information_view.information_cutoff != SEARCH_INFORMATION_CUTOFF:
        raise ValueError("Unsupported information-set Search cutoff.")
    if information_view.perspective_player != "me":
        raise ValueError("Information-set Search root perspective must be me.")
    if (
        information_view.declaration != exact_state.declaration
        or information_view.game_type != exact_state.declaration.game_type
    ):
        raise ValueError("Exact state and root Declaration disagree.")
    if information_view.declarer_player != exact_state.declarer_player:
        raise ValueError("Exact state and root Declarer disagree.")
    if information_view.local_side != get_player_side("me", exact_state.declarer_player):
        raise ValueError("Root side ownership contradicts the exact Declarer.")

    exact_current = tuple(
        SearchPublicPlay(player=play.player, card=play.card)
        for play in exact_state.current_trick
    )
    if information_view.current_trick != exact_current:
        raise ValueError("Exact state and root current Trick disagree.")
    if information_view.next_player != exact_state.next_player:
        raise ValueError("Exact state and root next Player disagree.")
    if (
        information_view.declarer_points != exact_state.declarer_trick_points
        or information_view.defender_points != exact_state.defender_trick_points
        or information_view.declarer_trick_count
        != exact_state.declarer_completed_tricks
        or information_view.defender_trick_count
        != exact_state.defender_completed_tricks
    ):
        raise ValueError("Exact state and root score or Trick counts disagree.")

    if information_view.local_remaining_hand != exact_state.hand_for("me"):
        raise ValueError("Exact state and root local hand disagree.")
    _validate_cards(information_view.local_remaining_hand, "local remaining hand")
    if tuple(item.player for item in information_view.remaining_hand_sizes) != PLAYER_ORDER:
        raise ValueError("Remaining hand sizes must cover all Players canonically.")
    for item in information_view.remaining_hand_sizes:
        if (
            isinstance(item.card_count, bool)
            or not isinstance(item.card_count, int)
            or item.card_count < 0
            or item.card_count != len(exact_state.hand_for(item.player))
        ):
            raise ValueError("Root and exact remaining hand sizes disagree.")

    completed_tricks = _copy_completed_tricks(information_view.completed_tricks)
    _validate_public_history(
        completed_tricks=completed_tricks,
        exact_state=exact_state,
    )
    public_hands = _copy_and_validate_public_hands(
        constraints=information_view.public_hand_constraints,
        exact_state=exact_state,
    )
    public_voids = _derive_public_void_constraints(
        completed_tricks=completed_tricks,
        current_trick=exact_current,
        game_type=exact_state.declaration.game_type,
    )
    _validate_hidden_constraints(
        information_view=information_view,
        exact_state=exact_state,
        public_hands=public_hands,
        public_voids=public_voids,
    )

    visible_out_of_play = tuple(information_view.known_skat_cards)
    _validate_cards(visible_out_of_play, "root-visible out-of-play Cards")
    if not set(visible_out_of_play).issubset(exact_state.out_of_play_cards):
        raise ValueError("Root-visible out-of-play Cards contradict the exact world.")
    root_is_declarer = exact_state.declarer_player == "me"
    if exact_state.declaration.hand_game:
        expected_visible: tuple[str, ...] = ()
    elif root_is_declarer:
        expected_visible = exact_state.out_of_play_cards
    else:
        expected_visible = ()
    if visible_out_of_play != expected_visible:
        raise ValueError("Root-visible out-of-play Cards violate actor visibility.")

    return InformationSetSearchWorldStateV1._from_validated(
        information_set_search_world_state_version=(
            INFORMATION_SET_SEARCH_WORLD_STATE_VERSION
        ),
        source=information_view.source,
        information_cutoff=information_view.information_cutoff,
        root_perspective_player="me",
        root_visible_out_of_play_cards=visible_out_of_play,
        exact_state=exact_state,
        public_completed_tricks=completed_tricks,
        public_hand_constraints=public_hands,
        public_void_constraints=public_voids,
    )


def apply_information_set_search_card_v1(
    world_state: InformationSetSearchWorldStateV1,
    card: str,
) -> InformationSetSearchWorldStateV1:
    if not isinstance(world_state, InformationSetSearchWorldStateV1):
        raise ValueError("world_state must be an InformationSetSearchWorldStateV1.")
    parent_trick = world_state.exact_state.current_trick
    transition = apply_exact_search_card(world_state.exact_state, card)

    public_hands = remove_public_hand_cards(
        world_state.public_hand_constraints,
        (transition.card,),
    )
    for constraint in public_hands:
        if constraint.cards != transition.next_state.hand_for(constraint.player):
            raise ValueError("A public hand transition contradicts exact ownership.")

    forbidden = {
        item.player: set(item.forbidden_effective_categories)
        for item in world_state.public_void_constraints
    }
    if parent_trick:
        led_category = get_public_effective_category(
            parent_trick[0].card,
            world_state.exact_state.declaration.game_type,
        )
        played_category = get_public_effective_category(
            transition.card,
            world_state.exact_state.declaration.game_type,
        )
        if played_category != led_category:
            forbidden[transition.actor].add(led_category)
    public_voids = tuple(
        InformationSetPublicVoidConstraintV1(
            player=player,
            forbidden_effective_categories=tuple(
                category
                for category in EFFECTIVE_CATEGORY_ORDER
                if category in forbidden[player]
            ),
        )
        for player in PLAYER_ORDER
    )

    completed_tricks = world_state.public_completed_tricks
    if transition.completed_trick is not None:
        exact_trick = transition.completed_trick
        completed_tricks = (
            *completed_tricks,
            SearchCompletedTrick(
                plays=tuple(
                    SearchPublicPlay(player=play.player, card=play.card)
                    for play in exact_trick.plays
                ),
                winner_player=exact_trick.winner_player,
                winner_side=exact_trick.winner_side,
                trick_points=exact_trick.trick_points,
            ),
        )

    return InformationSetSearchWorldStateV1._from_validated(
        information_set_search_world_state_version=(
            INFORMATION_SET_SEARCH_WORLD_STATE_VERSION
        ),
        source=world_state.source,
        information_cutoff=world_state.information_cutoff,
        root_perspective_player=world_state.root_perspective_player,
        root_visible_out_of_play_cards=world_state.root_visible_out_of_play_cards,
        exact_state=transition.next_state,
        public_completed_tricks=completed_tricks,
        public_hand_constraints=public_hands,
        public_void_constraints=public_voids,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class InformationSetSearchObservationV1:
    information_set_search_observation_version: int
    actor_player: str
    actor_side: str
    declarer_player: str
    declaration: GameDeclaration
    game_type: str
    own_remaining_hand: tuple[str, ...]
    current_trick: tuple[SearchPublicPlay, ...]
    public_completed_tricks: tuple[SearchCompletedTrick, ...]
    next_player: str
    declarer_points: int
    defender_points: int
    declarer_trick_count: int
    defender_trick_count: int
    remaining_hand_sizes: tuple[SearchRemainingHandSize, ...]
    visible_out_of_play_cards: tuple[str, ...]
    public_hand_constraints: tuple[PublicHandConstraint, ...]
    public_void_constraints: tuple[InformationSetPublicVoidConstraintV1, ...]
    legal_cards: tuple[str, ...]
    information_cutoff: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "InformationSetSearchObservationV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> InformationSetSearchObservationV1:
        result = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(result, field_name, field_value)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_set_search_observation_version": (
                self.information_set_search_observation_version
            ),
            "actor_player": self.actor_player,
            "actor_side": self.actor_side,
            "declarer_player": self.declarer_player,
            "declaration": build_serializable_game_declaration(self.declaration),
            "game_type": self.game_type,
            "own_remaining_hand": list(self.own_remaining_hand),
            "current_trick": [_serialize_play(play) for play in self.current_trick],
            "public_completed_tricks": [
                _serialize_completed_trick(trick)
                for trick in self.public_completed_tricks
            ],
            "next_player": self.next_player,
            "declarer_points": self.declarer_points,
            "defender_points": self.defender_points,
            "declarer_trick_count": self.declarer_trick_count,
            "defender_trick_count": self.defender_trick_count,
            "remaining_hand_sizes": [
                {"player": item.player, "card_count": item.card_count}
                for item in self.remaining_hand_sizes
            ],
            "visible_out_of_play_cards": list(self.visible_out_of_play_cards),
            "public_hand_constraints": build_serializable_public_hand_constraints(
                self.public_hand_constraints
            ),
            "public_void_constraints": [
                item.to_dict() for item in self.public_void_constraints
            ],
            "legal_cards": list(self.legal_cards),
            "information_cutoff": self.information_cutoff,
        }


def build_information_set_search_observation_v1(
    world_state: InformationSetSearchWorldStateV1,
) -> InformationSetSearchObservationV1:
    if not isinstance(world_state, InformationSetSearchWorldStateV1):
        raise ValueError("world_state must be an InformationSetSearchWorldStateV1.")
    state = world_state.exact_state
    actor = state.next_player
    actor_side = get_player_side(actor, state.declarer_player)
    if actor_side is None:
        raise ValueError("Actor side cannot be resolved without a concrete Declarer.")
    if actor == state.declarer_player and not state.declaration.hand_game:
        visible_out_of_play = state.out_of_play_cards
    else:
        visible_out_of_play = ()
    if actor == world_state.root_perspective_player and (
        visible_out_of_play != world_state.root_visible_out_of_play_cards
    ):
        raise ValueError("Root actor out-of-play visibility changed across the world.")

    current_trick = tuple(
        SearchPublicPlay(player=play.player, card=play.card)
        for play in state.current_trick
    )
    remaining_sizes = tuple(
        SearchRemainingHandSize(player, len(state.hand_for(player)))
        for player in PLAYER_ORDER
    )
    return InformationSetSearchObservationV1._from_validated(
        information_set_search_observation_version=(
            INFORMATION_SET_SEARCH_OBSERVATION_VERSION
        ),
        actor_player=actor,
        actor_side=actor_side,
        declarer_player=state.declarer_player,
        declaration=state.declaration,
        game_type=state.declaration.game_type,
        own_remaining_hand=state.hand_for(actor),
        current_trick=current_trick,
        public_completed_tricks=world_state.public_completed_tricks,
        next_player=state.next_player,
        declarer_points=state.declarer_trick_points,
        defender_points=state.defender_trick_points,
        declarer_trick_count=state.declarer_completed_tricks,
        defender_trick_count=state.defender_completed_tricks,
        remaining_hand_sizes=remaining_sizes,
        visible_out_of_play_cards=visible_out_of_play,
        public_hand_constraints=world_state.public_hand_constraints,
        public_void_constraints=world_state.public_void_constraints,
        legal_cards=get_exact_search_legal_cards(state),
        information_cutoff=world_state.information_cutoff,
    )
