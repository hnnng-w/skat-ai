from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from skatmind.deck import get_full_deck
from skatmind.game_declaration import GameDeclaration
from skatmind.rules import get_legal_cards, get_trick_points, get_trick_winner
from skatmind.side_ownership import get_player_side
from skatmind.turn_phase import CONCRETE_PLAYERS, derive_next_player

_FULL_DECK = tuple(get_full_deck())
_FULL_DECK_SET = set(_FULL_DECK)
_CARD_ORDER = {card: index for index, card in enumerate(_FULL_DECK)}


@dataclass(frozen=True)
class ExactSearchPlay:
    """One exact current-trick play attributed to a concrete player."""

    player: str
    card: str


@dataclass(frozen=True, init=False)
class ExactSearchState:
    """Immutable perspective-neutral state for one exact complete world."""

    declaration: GameDeclaration
    declarer_player: str
    hands: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]
    current_trick: tuple[ExactSearchPlay, ...]
    next_player: str
    declarer_trick_points: int
    defender_trick_points: int
    declarer_completed_tricks: int
    defender_completed_tricks: int
    out_of_play_cards: tuple[str, str]

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("Use build_exact_search_state() to construct an exact search state.")

    @classmethod
    def _from_validated(
        cls,
        *,
        declaration: GameDeclaration,
        declarer_player: str,
        hands: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]],
        current_trick: tuple[ExactSearchPlay, ...],
        next_player: str,
        declarer_trick_points: int,
        defender_trick_points: int,
        declarer_completed_tricks: int,
        defender_completed_tricks: int,
        out_of_play_cards: tuple[str, str],
    ) -> "ExactSearchState":
        state = object.__new__(cls)
        object.__setattr__(state, "declaration", declaration)
        object.__setattr__(state, "declarer_player", declarer_player)
        object.__setattr__(state, "hands", hands)
        object.__setattr__(state, "current_trick", current_trick)
        object.__setattr__(state, "next_player", next_player)
        object.__setattr__(state, "declarer_trick_points", declarer_trick_points)
        object.__setattr__(state, "defender_trick_points", defender_trick_points)
        object.__setattr__(state, "declarer_completed_tricks", declarer_completed_tricks)
        object.__setattr__(state, "defender_completed_tricks", defender_completed_tricks)
        object.__setattr__(state, "out_of_play_cards", out_of_play_cards)
        return state

    def hand_for(self, player: str) -> tuple[str, ...]:
        """Returns the exact remaining hand for one concrete player."""
        if player not in CONCRETE_PLAYERS:
            raise ValueError(f"Invalid exact search player: {player}")
        return self.hands[CONCRETE_PLAYERS.index(player)]

    @property
    def remaining_plies(self) -> int:
        """Returns the number of cards still held in all hands."""
        return sum(len(hand) for hand in self.hands)

    @property
    def remaining_tricks(self) -> int:
        """Returns unresolved complete tricks, including the current partial trick."""
        return (self.remaining_plies + len(self.current_trick)) // 3

    @property
    def is_terminal(self) -> bool:
        """Returns whether normal play has completed all ten tricks."""
        return self.remaining_plies == 0 and not self.current_trick


@dataclass(frozen=True)
class ExactSearchCompletedTrick:
    """Neutral resolution facts for one newly completed trick."""

    plays: tuple[ExactSearchPlay, ...]
    winner_player: str
    winner_side: str
    trick_points: int


@dataclass(frozen=True)
class ExactSearchTransition:
    """One immutable exact card transition."""

    actor: str
    card: str
    next_state: ExactSearchState
    completed_trick: ExactSearchCompletedTrick | None


@dataclass(frozen=True)
class ExactSearchTerminalFacts:
    """Perspective-neutral card-point and trick facts after normal completion."""

    declarer_final_points: int
    defender_final_points: int
    declarer_trick_count: int
    defender_trick_count: int
    out_of_play_points: int


def _canonicalize_cards(cards: Iterable[str], context: str) -> tuple[str, ...]:
    if isinstance(cards, str):
        raise ValueError(f"{context} must be a card collection.")
    try:
        copied = tuple(cards)
    except TypeError as error:
        raise ValueError(f"{context} must be a card collection.") from error
    invalid = [card for card in copied if not isinstance(card, str) or card not in _FULL_DECK_SET]
    if invalid:
        raise ValueError(f"Invalid cards in {context}: {invalid}")
    return tuple(sorted(copied, key=_CARD_ORDER.__getitem__))


def _normalize_hands(
    remaining_hands: Mapping[str, Iterable[str]] | Iterable[tuple[str, Iterable[str]]],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    try:
        items = list(
            remaining_hands.items()
            if isinstance(remaining_hands, Mapping)
            else remaining_hands
        )
    except TypeError as error:
        raise ValueError("remaining_hands must provide all three concrete players.") from error

    hands_by_player: dict[str, tuple[str, ...]] = {}
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("remaining_hands entries must be player-card pairs.")
        player, cards = item
        if not isinstance(player, str) or player not in CONCRETE_PLAYERS:
            raise ValueError(f"Unknown exact search hand player: {player}")
        if player in hands_by_player:
            raise ValueError(f"Duplicate exact search hand player: {player}")
        hands_by_player[player] = _canonicalize_cards(cards, f"remaining hand for {player}")

    missing_players = [player for player in CONCRETE_PLAYERS if player not in hands_by_player]
    if missing_players:
        raise ValueError(f"Missing exact search hands for players: {missing_players}")
    return tuple(hands_by_player[player] for player in CONCRETE_PLAYERS)  # type: ignore[return-value]


def _normalize_current_trick(
    current_trick: Iterable[ExactSearchPlay | tuple[str, str]],
) -> tuple[ExactSearchPlay, ...]:
    if isinstance(current_trick, str):
        raise ValueError("current_trick must be an attributed play collection.")
    try:
        copied = tuple(current_trick)
    except TypeError as error:
        raise ValueError("current_trick must be an attributed play collection.") from error
    if len(copied) > 2:
        raise ValueError("current_trick cannot contain more than two cards.")

    normalized = []
    for item in copied:
        if isinstance(item, ExactSearchPlay):
            play = ExactSearchPlay(player=item.player, card=item.card)
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            play = ExactSearchPlay(player=item[0], card=item[1])
        else:
            raise ValueError("current_trick entries must contain one player and one card.")
        if play.player not in CONCRETE_PLAYERS:
            raise ValueError(f"Unknown current-trick player: {play.player}")
        if not isinstance(play.card, str) or play.card not in _FULL_DECK_SET:
            raise ValueError(f"Invalid current-trick card: {play.card}")
        normalized.append(play)
    return tuple(normalized)


def _copy_declaration(declaration: GameDeclaration) -> GameDeclaration:
    if not isinstance(declaration, GameDeclaration):
        raise ValueError("declaration must be a valid GameDeclaration.")
    return GameDeclaration(
        game_type=declaration.game_type,
        hand_game=declaration.hand_game,
        ouvert=declaration.ouvert,
        schneider_announced=declaration.schneider_announced,
        schwarz_announced=declaration.schwarz_announced,
        matadors=declaration.matadors,
        bid_value=declaration.bid_value,
    )


def _validate_non_negative_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")


def build_exact_search_state(
    *,
    declaration: GameDeclaration,
    declarer_player: str,
    remaining_hands: Mapping[str, Iterable[str]] | Iterable[tuple[str, Iterable[str]]],
    current_trick: Iterable[ExactSearchPlay | tuple[str, str]],
    next_player: str,
    declarer_trick_points: int,
    defender_trick_points: int,
    declarer_completed_tricks: int,
    defender_completed_tricks: int,
    out_of_play_cards: Iterable[str],
) -> ExactSearchState:
    """Strictly validates and builds one immutable exact complete-world state."""
    normalized_declaration = _copy_declaration(declaration)
    if declarer_player not in CONCRETE_PLAYERS:
        raise ValueError("Exact search requires a concrete declarer_player.")
    if next_player not in CONCRETE_PLAYERS:
        raise ValueError("Exact search requires a concrete next_player.")

    hands = _normalize_hands(remaining_hands)
    plays = _normalize_current_trick(current_trick)
    normalized_out_of_play = _canonicalize_cards(out_of_play_cards, "out_of_play_cards")
    if len(normalized_out_of_play) != 2:
        raise ValueError("out_of_play_cards must contain exactly two cards.")

    for field_name, value in (
        ("declarer_trick_points", declarer_trick_points),
        ("defender_trick_points", defender_trick_points),
        ("declarer_completed_tricks", declarer_completed_tricks),
        ("defender_completed_tricks", defender_completed_tricks),
    ):
        _validate_non_negative_integer(value, field_name)

    if len({play.player for play in plays}) != len(plays):
        raise ValueError("current_trick cannot contain duplicate players.")
    if plays:
        leader = plays[0].player
        expected_players = tuple(derive_next_player(leader, index) for index in range(len(plays)))
        if tuple(play.player for play in plays) != expected_players:
            raise ValueError("current_trick player order is inconsistent with fixed seat order.")
        expected_next_player = derive_next_player(leader, len(plays))
        if next_player != expected_next_player:
            raise ValueError(
                "next_player is inconsistent with current_trick: "
                f"expected {expected_next_player}, got {next_player}."
            )

    explicit_cards = [
        *(card for hand in hands for card in hand),
        *(play.card for play in plays),
        *normalized_out_of_play,
    ]
    duplicates = sorted(
        {card for card in explicit_cards if explicit_cards.count(card) > 1},
        key=_CARD_ORDER.__getitem__,
    )
    if duplicates:
        raise ValueError(f"Duplicate explicit exact search cards: {duplicates}")

    unresolved_card_count = sum(len(hand) for hand in hands) + len(plays)
    if unresolved_card_count % 3 != 0:
        raise ValueError("Unresolved exact search cards must form complete tricks.")
    remaining_tricks = unresolved_card_count // 3
    if remaining_tricks > 10:
        raise ValueError("Exact search state cannot exceed ten remaining tricks.")

    current_players = {play.player for play in plays}
    for player, hand in zip(CONCRETE_PLAYERS, hands, strict=True):
        expected_size = remaining_tricks - (1 if player in current_players else 0)
        if len(hand) != expected_size:
            raise ValueError(
                "Exact search hand-size progression is inconsistent: "
                f"expected {expected_size} cards for {player}, got {len(hand)}."
            )

    completed_cards = tuple(card for card in _FULL_DECK if card not in explicit_cards)
    completed_trick_count = declarer_completed_tricks + defender_completed_tricks
    if len(completed_cards) != 3 * completed_trick_count:
        raise ValueError(
            "Completed card count must equal three times the completed-trick count."
        )
    if completed_trick_count + remaining_tricks != 10:
        raise ValueError("Completed and remaining trick counts must total ten.")
    completed_card_points = get_trick_points(list(completed_cards))
    if completed_card_points != declarer_trick_points + defender_trick_points:
        raise ValueError(
            "Completed card points must equal declarer_trick_points plus "
            "defender_trick_points."
        )
    for side, trick_points, trick_count in (
        ("Declarer", declarer_trick_points, declarer_completed_tricks),
        ("Defender", defender_trick_points, defender_completed_tricks),
    ):
        if trick_count == 0 and trick_points != 0:
            raise ValueError(f"{side} cannot have trick points without a completed trick.")

    prior_cards: list[str] = []
    for play in plays:
        hand_before_play = [*hands[CONCRETE_PLAYERS.index(play.player)], play.card]
        legal_cards = get_legal_cards(
            hand_before_play,
            prior_cards,
            normalized_declaration.game_type,
        )
        if play.card not in legal_cards:
            raise ValueError(
                f"current_trick card {play.card} was not a legal play for {play.player}."
            )
        prior_cards.append(play.card)

    return ExactSearchState._from_validated(
        declaration=normalized_declaration,
        declarer_player=declarer_player,
        hands=hands,
        current_trick=plays,
        next_player=next_player,
        declarer_trick_points=declarer_trick_points,
        defender_trick_points=defender_trick_points,
        declarer_completed_tricks=declarer_completed_tricks,
        defender_completed_tricks=defender_completed_tricks,
        out_of_play_cards=(normalized_out_of_play[0], normalized_out_of_play[1]),
    )


def get_exact_search_legal_cards(state: ExactSearchState) -> tuple[str, ...]:
    """Returns the next player's legal cards in canonical deck order."""
    if state.is_terminal:
        return ()
    legal_cards = get_legal_cards(
        list(state.hand_for(state.next_player)),
        [play.card for play in state.current_trick],
        state.declaration.game_type,
    )
    return tuple(sorted(legal_cards, key=_CARD_ORDER.__getitem__))


def apply_exact_search_card(state: ExactSearchState, card: str) -> ExactSearchTransition:
    """Applies one legal card without mutating the exact parent state."""
    if state.is_terminal:
        raise ValueError("Cannot apply a card to a terminal exact search state.")
    if not isinstance(card, str) or card not in _FULL_DECK_SET:
        raise ValueError(f"Invalid exact search card: {card}")

    actor = state.next_player
    hand = state.hand_for(actor)
    if card not in hand:
        raise ValueError(f"Player {actor} does not own exact search card {card}.")
    if card not in get_exact_search_legal_cards(state):
        raise ValueError(f"Card {card} is not legal for exact search player {actor}.")

    actor_index = CONCRETE_PLAYERS.index(actor)
    next_hands = list(state.hands)
    next_hands[actor_index] = tuple(held_card for held_card in hand if held_card != card)
    next_trick = (*state.current_trick, ExactSearchPlay(actor, card))
    completed_trick = None
    next_player = derive_next_player(actor, 1)
    declarer_points = state.declarer_trick_points
    defender_points = state.defender_trick_points
    declarer_tricks = state.declarer_completed_tricks
    defender_tricks = state.defender_completed_tricks

    if len(next_trick) == 3:
        trick_cards = [play.card for play in next_trick]
        winner_index = get_trick_winner(trick_cards, state.declaration.game_type)
        winner_player = next_trick[winner_index].player
        winner_side = get_player_side(winner_player, state.declarer_player)
        if winner_side is None:
            raise ValueError("Exact search trick winner side could not be resolved.")
        trick_points = get_trick_points(trick_cards)
        completed_trick = ExactSearchCompletedTrick(
            plays=next_trick,
            winner_player=winner_player,
            winner_side=winner_side,
            trick_points=trick_points,
        )
        if winner_side == "declarer":
            declarer_points += trick_points
            declarer_tricks += 1
        else:
            defender_points += trick_points
            defender_tricks += 1
        next_trick = ()
        next_player = winner_player

    next_state = ExactSearchState._from_validated(
        declaration=state.declaration,
        declarer_player=state.declarer_player,
        hands=tuple(next_hands),  # type: ignore[arg-type]
        current_trick=next_trick,
        next_player=next_player,
        declarer_trick_points=declarer_points,
        defender_trick_points=defender_points,
        declarer_completed_tricks=declarer_tricks,
        defender_completed_tricks=defender_tricks,
        out_of_play_cards=state.out_of_play_cards,
    )
    return ExactSearchTransition(
        actor=actor,
        card=card,
        next_state=next_state,
        completed_trick=completed_trick,
    )


def get_exact_search_terminal_facts(state: ExactSearchState) -> ExactSearchTerminalFacts:
    """Returns neutral normal-completion facts without settlement interpretation."""
    if not state.is_terminal:
        raise ValueError("Exact search terminal facts require a normal terminal state.")
    out_of_play_points = get_trick_points(list(state.out_of_play_cards))
    facts = ExactSearchTerminalFacts(
        declarer_final_points=state.declarer_trick_points + out_of_play_points,
        defender_final_points=state.defender_trick_points,
        declarer_trick_count=state.declarer_completed_tricks,
        defender_trick_count=state.defender_completed_tricks,
        out_of_play_points=out_of_play_points,
    )
    if facts.declarer_final_points + facts.defender_final_points != 120:
        raise ValueError("Terminal exact search card points must total 120.")
    if facts.declarer_trick_count + facts.defender_trick_count != 10:
        raise ValueError("Terminal exact search completed tricks must total ten.")
    return facts
