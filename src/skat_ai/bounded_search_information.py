from copy import deepcopy
from dataclasses import dataclass

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_history import get_players_for_trick_leader
from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    HiddenCardInferenceConstraints,
    PlayerHiddenCardConstraints,
    build_hidden_card_inference_constraints,
)
from skat_ai.historical_snapshot_adapter import HistoricalSnapshotPosition
from skat_ai.information_view import is_skat_visible_to_local_player
from skat_ai.known_cards import validate_no_duplicate_known_cards
from skat_ai.public_hand_constraint import (
    DECLARED_OUVERT_SOURCE,
    DECLARER_EXPOSURE_CONTINUATION_SOURCE,
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PublicHandConstraint,
    canonicalize_cards,
)
from skat_ai.rules import GAME_TYPES, get_legal_cards, get_trick_points, get_trick_winner
from skat_ai.side_ownership import get_player_side, normalize_declarer_player
from skat_ai.turn_phase import (
    CONCRETE_PLAYERS,
    UNKNOWN_PLAYER,
    derive_next_player,
    normalize_turn_phase_for_position,
)

LIVE_LOCAL_VIEW_SOURCE = "live_local_view"
HISTORICAL_DECISION_SNAPSHOT_SOURCE = "historical_decision_snapshot"
SEARCH_INFORMATION_CUTOFF = "current_decision"
SEARCH_INFORMATION_SOURCES = (
    LIVE_LOCAL_VIEW_SOURCE,
    HISTORICAL_DECISION_SNAPSHOT_SOURCE,
)

SEARCH_UNAVAILABLE_REASONS = (
    "unsupported_game_type",
    "unsupported_turn_phase",
    "unsupported_perspective",
    "local_player_not_to_act",
    "missing_concrete_declarer",
    "remaining_trick_limit_exceeded",
    "compatible_world_limit_exceeded",
    "incompatible_world_space",
    "missing_terminal_utility_inputs",
    "game_already_complete",
    "no_legal_cards",
)


@dataclass(frozen=True)
class SearchPublicPlay:
    """One public card with its concrete decision-relative owner."""

    player: str
    card: str


@dataclass(frozen=True)
class SearchCompletedTrick:
    """One canonical completed public trick at the search boundary."""

    plays: tuple[SearchPublicPlay, ...]
    winner_player: str
    winner_side: str
    trick_points: int


@dataclass(frozen=True)
class SearchRemainingHandSize:
    """One concrete player's public remaining-card count."""

    player: str
    card_count: int


@dataclass(frozen=True)
class SearchInformationView:
    """Immutable information legitimately visible at one local decision."""

    source: str
    perspective_player: str
    declarer_player: str
    local_side: str | None
    declaration: GameDeclaration
    game_type: str
    local_remaining_hand: tuple[str, ...]
    current_trick: tuple[SearchPublicPlay, ...]
    completed_tricks: tuple[SearchCompletedTrick, ...]
    next_player: str
    declarer_points: int
    defender_points: int
    declarer_trick_count: int
    defender_trick_count: int
    remaining_hand_sizes: tuple[SearchRemainingHandSize, ...]
    known_skat_cards: tuple[str, ...]
    public_hand_constraints: tuple[PublicHandConstraint, ...]
    hidden_card_constraints: tuple[PlayerHiddenCardConstraints, ...]
    information_cutoff: str = SEARCH_INFORMATION_CUTOFF

    def __post_init__(self) -> None:
        tuple_fields = (
            "local_remaining_hand",
            "current_trick",
            "completed_tricks",
            "remaining_hand_sizes",
            "known_skat_cards",
            "public_hand_constraints",
            "hidden_card_constraints",
        )
        for field_name in tuple_fields:
            if not isinstance(getattr(self, field_name), tuple):
                raise TypeError(f"{field_name} must be a tuple.")

    def remaining_hand_size(self, player: str) -> int:
        """Returns one concrete player's remaining-card count."""
        for item in self.remaining_hand_sizes:
            if item.player == player:
                return item.card_count
        raise ValueError(f"No remaining hand size exists for player {player!r}.")


@dataclass(frozen=True)
class SearchEligibility:
    """Supported-domain assessment for one bounded search request."""

    eligible: bool
    unavailable_reason: str | None
    remaining_plies: int
    remaining_tricks: int
    configured_remaining_trick_limit: int


def _copy_declaration(declaration: GameDeclaration) -> GameDeclaration:
    return GameDeclaration(
        game_type=declaration.game_type,
        hand_game=declaration.hand_game,
        ouvert=declaration.ouvert,
        schneider_announced=declaration.schneider_announced,
        schwarz_announced=declaration.schwarz_announced,
        matadors=declaration.matadors,
        bid_value=declaration.bid_value,
    )


def _validate_cards(cards: tuple[str, ...], context: str) -> None:
    full_deck = set(get_full_deck())
    invalid = sorted(set(cards) - full_deck)
    if invalid:
        raise ValueError(f"Invalid cards in {context}: {invalid}")
    if len(cards) != len(set(cards)):
        raise ValueError(f"Duplicate cards in {context}.")


def _normalize_completed_tricks_for_game(
    completed_tricks: list[dict],
    game_type: str,
    declarer_player: str,
) -> tuple[SearchCompletedTrick, ...]:
    if len(completed_tricks) > 10:
        raise ValueError("Bounded search supports at most ten completed tricks.")
    normalized = []
    required_leader = None
    for trick_index, trick in enumerate(completed_tricks, start=1):
        if not isinstance(trick, dict):
            raise ValueError(f"completed_tricks[{trick_index - 1}] must be an object.")
        cards = trick.get("cards")
        players = trick.get("players")
        if not isinstance(cards, list) or len(cards) != 3:
            raise ValueError(f"Completed trick {trick_index} must contain three cards.")
        _validate_cards(tuple(cards), f"completed trick {trick_index}")
        if not isinstance(players, list) or len(players) != 3:
            raise ValueError(
                f"Completed trick {trick_index} must contain three concrete players."
            )
        if any(player not in CONCRETE_PLAYERS for player in players):
            raise ValueError(f"Completed trick {trick_index} has an invalid player.")
        if players != get_players_for_trick_leader(players[0]):
            raise ValueError(f"Completed trick {trick_index} player order is invalid.")
        if required_leader is not None and players[0] != required_leader:
            raise ValueError(
                f"Completed trick {trick_index} must be led by {required_leader}."
            )

        winner_player = players[get_trick_winner(cards, game_type)]
        supplied_winner = trick.get("winner_player")
        if supplied_winner not in (None, winner_player):
            raise ValueError(
                f"Completed trick {trick_index} winner_player is inconsistent."
            )
        winner_side = (
            get_player_side(winner_player, declarer_player)
            if declarer_player in CONCRETE_PLAYERS
            else trick.get("winner_role")
        )
        if winner_side not in {"declarer", "defenders"}:
            raise ValueError(
                f"Completed trick {trick_index} requires a concrete winner side."
            )
        supplied_side = trick.get("winner_role")
        if supplied_side not in (None, winner_side):
            raise ValueError(f"Completed trick {trick_index} winner_role is inconsistent.")
        normalized.append(
            SearchCompletedTrick(
                plays=tuple(
                    SearchPublicPlay(player=player, card=card)
                    for player, card in zip(players, cards, strict=True)
                ),
                winner_player=winner_player,
                winner_side=winner_side,
                trick_points=get_trick_points(cards),
            )
        )
        required_leader = winner_player
    return tuple(normalized)


def _canonical_public_hand_constraints(
    constraints: tuple[PublicHandConstraint, ...],
    declaration: GameDeclaration,
    declarer_player: str,
) -> tuple[PublicHandConstraint, ...]:
    player_order = {player: index for index, player in enumerate(CONCRETE_PLAYERS)}
    copied = []
    for constraint in constraints:
        if constraint.player not in CONCRETE_PLAYERS:
            raise ValueError(
                f"Invalid public hand constraint player: {constraint.player}"
            )
        if constraint.visibility_scope != "all_players":
            raise ValueError("Search public hand constraints must be visible to all players.")
        if declarer_player not in CONCRETE_PLAYERS:
            raise ValueError(
                "Public hand constraints require a concrete declarer."
            )
        if constraint.source == DECLARED_OUVERT_SOURCE:
            if not declaration.ouvert or constraint.player != declarer_player:
                raise ValueError(
                    "A declared-Ouvert constraint requires the declarer's Ouvert hand."
                )
        elif constraint.source == DECLARER_EXPOSURE_CONTINUATION_SOURCE:
            if constraint.player != declarer_player:
                raise ValueError(
                    "Declarer-exposure continuation must expose the declarer hand."
                )
        elif constraint.source == DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE:
            if constraint.player == declarer_player:
                raise ValueError(
                    "Defender-open-play continuation must expose a defender hand."
                )
        else:
            raise ValueError(
                f"Unsupported search public hand source: {constraint.source}"
            )
        cards = tuple(constraint.cards)
        _validate_cards(cards, f"public {constraint.player} hand")
        if len(cards) > 10:
            raise ValueError("A public remaining hand cannot exceed ten cards.")
        copied.append(
            PublicHandConstraint(
                player=constraint.player,
                cards=canonicalize_cards(cards),
                visibility_scope=constraint.visibility_scope,
                source=constraint.source,
            )
        )
    return tuple(sorted(copied, key=lambda item: player_order[item.player]))


def _copy_hidden_constraints(
    constraints: HiddenCardInferenceConstraints,
) -> tuple[PlayerHiddenCardConstraints, ...]:
    player_order = {player: index for index, player in enumerate(CONCRETE_PLAYERS)}
    return tuple(
        sorted(
            (
                PlayerHiddenCardConstraints(
                    player=item.player,
                    forbidden_effective_categories=tuple(
                        item.forbidden_effective_categories
                    ),
                    exact_cards=canonicalize_cards(tuple(item.exact_cards)),
                )
                for item in constraints.player_constraints
            ),
            key=lambda item: player_order[item.player],
        )
    )


def _build_search_information_view(
    *,
    source: str,
    state: GameState,
    declaration: GameDeclaration,
    left_hand_size: int,
    right_hand_size: int,
    known_skat_cards: tuple[str, ...] = (),
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    current_declarer_points: int | None = None,
    current_defender_points: int | None = None,
    perspective_player: str = "me",
) -> SearchInformationView:
    """Builds one shared, immutable, decision-time-safe search view."""
    if source not in SEARCH_INFORMATION_SOURCES:
        raise ValueError(f"Invalid bounded-search information source: {source}")
    if perspective_player not in CONCRETE_PLAYERS:
        raise ValueError(f"Invalid bounded-search perspective: {perspective_player}")
    if declaration.game_type != state.game_type or state.game_type not in GAME_TYPES:
        raise ValueError("Search declaration and state game types must match.")
    if state.played_cards:
        raise ValueError(
            "Bounded search requires attributed completed trick history instead of "
            "legacy played_cards."
        )
    for field_name, value in (
        ("left_hand_size", left_hand_size),
        ("right_hand_size", right_hand_size),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer.")
        if value > 10:
            raise ValueError(f"{field_name} cannot exceed ten cards.")

    declarer_player = normalize_declarer_player(
        state.player_role,
        state.declarer_player,
    )
    copied_completed = deepcopy(state.completed_tricks)
    normalized_completed = _normalize_completed_tricks_for_game(
        copied_completed,
        state.game_type,
        declarer_player,
    )
    completed_for_state = [
        {
            "cards": [play.card for play in trick.plays],
            "players": [play.player for play in trick.plays],
            "winner_player": trick.winner_player,
            "winner_role": trick.winner_side,
        }
        for trick in normalized_completed
    ]
    copied_current_trick = list(state.current_trick)
    phase = normalize_turn_phase_for_position(
        state.trick_leader,
        state.next_player,
        copied_current_trick,
        completed_for_state,
    )
    current_plays = tuple(
        SearchPublicPlay(
            player=derive_next_player(phase.trick_leader, index),
            card=card,
        )
        for index, card in enumerate(copied_current_trick)
    )
    hand_cards = tuple(state.hand)
    skat_cards = tuple(known_skat_cards)
    current_cards = tuple(copied_current_trick)
    if declaration.hand_game and skat_cards:
        raise ValueError("A Hand game search view cannot contain known Skat cards.")
    _validate_cards(hand_cards, "local remaining hand")
    _validate_cards(skat_cards, "known Skat")
    _validate_cards(current_cards, "current trick")
    if len(hand_cards) > 10:
        raise ValueError("The local remaining hand cannot exceed ten cards.")
    if len(skat_cards) > 2:
        raise ValueError("Known Skat cards cannot exceed two cards.")
    canonical_hand = canonicalize_cards(hand_cards)
    canonical_skat = canonicalize_cards(skat_cards)
    canonical_public_hands = _canonical_public_hand_constraints(
        tuple(public_hand_constraints),
        declaration,
        declarer_player,
    )
    safe_state = GameState(
        game_type=state.game_type,
        player_role=state.player_role,
        hand=list(canonical_hand),
        current_trick=[play.card for play in current_plays],
        played_cards=[],
        skat=list(canonical_skat),
        player_position=state.player_position,
        declarer_player=declarer_player,
        trick_leader=phase.trick_leader,
        completed_tricks=completed_for_state,
        declarer_points=state.declarer_points,
        defender_points=state.defender_points,
        next_player=phase.next_player,
    )
    validate_no_duplicate_known_cards(safe_state)
    derived_hidden_constraints = build_hidden_card_inference_constraints(
        safe_state,
        canonical_public_hands,
    )
    if derived_hidden_constraints.game_type != state.game_type:
        raise ValueError("Hidden-card constraints use a different game type.")

    remaining_sizes = {
        "me": len(canonical_hand),
        "left": left_hand_size,
        "right": right_hand_size,
    }
    before_current_trick_sizes = {
        player: remaining_sizes[player]
        + int(any(play.player == player for play in current_plays))
        for player in CONCRETE_PLAYERS
    }
    if len(set(before_current_trick_sizes.values())) != 1:
        raise ValueError(
            "Remaining hand sizes are inconsistent with the normalized current trick."
        )
    for constraint in canonical_public_hands:
        if len(constraint.cards) != remaining_sizes[constraint.player]:
            raise ValueError(
                f"Public {constraint.player} hand size does not match its remaining "
                "hand size."
            )

    completed_declarer_points = sum(
        trick.trick_points
        for trick in normalized_completed
        if trick.winner_side == "declarer"
    )
    completed_defender_points = sum(
        trick.trick_points
        for trick in normalized_completed
        if trick.winner_side == "defenders"
    )
    declarer_points = (
        state.declarer_points + completed_declarer_points
        if current_declarer_points is None
        else current_declarer_points
    )
    defender_points = (
        state.defender_points + completed_defender_points
        if current_defender_points is None
        else current_defender_points
    )
    for field_name, value in (
        ("current_declarer_points", declarer_points),
        ("current_defender_points", defender_points),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer.")
    if declarer_points + defender_points > 120:
        raise ValueError("Current declarer and defender points exceed 120.")

    return SearchInformationView(
        source=source,
        perspective_player=perspective_player,
        declarer_player=declarer_player,
        local_side=(
            get_player_side(perspective_player, declarer_player)
            if declarer_player in CONCRETE_PLAYERS
            else None
        ),
        declaration=_copy_declaration(declaration),
        game_type=state.game_type,
        local_remaining_hand=canonical_hand,
        current_trick=current_plays,
        completed_tricks=normalized_completed,
        next_player=phase.next_player,
        declarer_points=declarer_points,
        defender_points=defender_points,
        declarer_trick_count=sum(
            trick.winner_side == "declarer" for trick in normalized_completed
        ),
        defender_trick_count=sum(
            trick.winner_side == "defenders" for trick in normalized_completed
        ),
        remaining_hand_sizes=(
            SearchRemainingHandSize("me", len(canonical_hand)),
            SearchRemainingHandSize("left", left_hand_size),
            SearchRemainingHandSize("right", right_hand_size),
        ),
        known_skat_cards=canonical_skat,
        public_hand_constraints=canonical_public_hands,
        hidden_card_constraints=_copy_hidden_constraints(
            derived_hidden_constraints
        ),
    )


def build_live_search_information_view(
    *,
    state: GameState,
    declaration: GameDeclaration,
    left_hand_size: int,
    right_hand_size: int,
    skat_visibility: str = "unknown",
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> SearchInformationView:
    """Builds a live local view after enforcing local Skat visibility."""
    if skat_visibility == "known_post_game":
        raise ValueError("A live bounded-search view cannot use post-game Skat cards.")
    if declaration.hand_game and skat_visibility == "known_to_declarer" and state.skat:
        raise ValueError("A live Hand game cannot expose Skat cards to the declarer.")
    known_skat_cards = (
        tuple(state.skat)
        if is_skat_visible_to_local_player(
            state.player_role,
            state.declarer_player,
            skat_visibility,
        )
        else ()
    )
    return _build_search_information_view(
        source=LIVE_LOCAL_VIEW_SOURCE,
        state=state,
        declaration=declaration,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        known_skat_cards=known_skat_cards,
        public_hand_constraints=public_hand_constraints,
    )


def build_historical_search_information_view(
    position: HistoricalSnapshotPosition,
) -> SearchInformationView:
    """Builds a search view only from an already reconstructed safe snapshot."""
    return _build_search_information_view(
        source=HISTORICAL_DECISION_SNAPSHOT_SOURCE,
        state=position.state,
        declaration=position.game_declaration,
        left_hand_size=position.left_hand_size,
        right_hand_size=position.right_hand_size,
        known_skat_cards=tuple(position.state.skat),
        public_hand_constraints=position.public_hand_constraints,
        current_declarer_points=position.state.declarer_points,
        current_defender_points=position.state.defender_points,
    )


def get_remaining_search_card_count(view: SearchInformationView) -> int:
    """Counts unresolved play cards, including a current partial trick."""
    return sum(item.card_count for item in view.remaining_hand_sizes) + len(
        view.current_trick
    )


def get_remaining_search_trick_count(view: SearchInformationView) -> int:
    """Counts unresolved tricks from all unresolved play cards."""
    unresolved_cards = get_remaining_search_card_count(view)
    return (unresolved_cards + 2) // 3


def has_terminal_utility_inputs(view: SearchInformationView) -> bool:
    """Returns whether existing settlement inputs can be resolved at a leaf."""
    if view.declaration.bid_value is None:
        return False
    return view.game_type == "null" or view.declaration.matadors is not None


def assess_search_eligibility(
    view: SearchInformationView,
    configured_remaining_trick_limit: int,
) -> SearchEligibility:
    """Assesses the first bounded local-player search domain without worlds."""
    if (
        isinstance(configured_remaining_trick_limit, bool)
        or not isinstance(configured_remaining_trick_limit, int)
        or configured_remaining_trick_limit <= 0
    ):
        raise ValueError("configured_remaining_trick_limit must be positive.")
    remaining_plies = get_remaining_search_card_count(view)
    remaining_tricks = get_remaining_search_trick_count(view)

    reason = None
    if view.perspective_player != "me":
        reason = "unsupported_perspective"
    elif view.declarer_player not in CONCRETE_PLAYERS or view.local_side is None:
        reason = "missing_concrete_declarer"
    elif remaining_plies == 0:
        reason = "game_already_complete"
    elif view.next_player == UNKNOWN_PLAYER:
        reason = "unsupported_turn_phase"
    elif view.next_player != "me":
        reason = "local_player_not_to_act"
    elif not get_legal_cards(
        list(view.local_remaining_hand),
        [play.card for play in view.current_trick],
        view.game_type,
    ):
        reason = "no_legal_cards"
    elif not has_terminal_utility_inputs(view):
        reason = "missing_terminal_utility_inputs"
    elif remaining_tricks > configured_remaining_trick_limit:
        reason = "remaining_trick_limit_exceeded"

    return SearchEligibility(
        eligible=reason is None,
        unavailable_reason=reason,
        remaining_plies=remaining_plies,
        remaining_tricks=remaining_tricks,
        configured_remaining_trick_limit=configured_remaining_trick_limit,
    )
