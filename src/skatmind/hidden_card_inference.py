from __future__ import annotations

import random
from dataclasses import dataclass
from functools import cache
from typing import Any

from skatmind.card_tracking import get_unseen_cards
from skatmind.deck import get_full_deck
from skatmind.game_history import get_players_for_trick_leader
from skatmind.game_state import GameState
from skatmind.public_hand_constraint import PublicHandConstraint, canonicalize_cards
from skatmind.rules import get_effective_suit

HIDDEN_CARD_INFERENCE_SCHEMA_VERSION = 1
HIDDEN_CARD_INFERENCE_MODE = "exact_evidence_constrained"
COMPATIBLE_WORLD_MODEL = "uniform_labeled_assignments"
CONFIDENCE_BASIS = "compatible_world_ownership_concentration"
HIGH_CONFIDENCE_MIN_PROBABILITY = 0.85
MEDIUM_CONFIDENCE_MIN_PROBABILITY = 0.65

OWNER_ORDER = ("left", "right", "skat")
PLAYER_ORDER = ("me", "left", "right")
EFFECTIVE_CATEGORY_ORDER = ("clubs", "spades", "hearts", "diamonds", "trump")
_EFFECTIVE_CATEGORY_NAMES = {
    "C": "clubs",
    "S": "spades",
    "H": "hearts",
    "D": "diamonds",
    "TRUMP": "trump",
}
_FULL_DECK = tuple(get_full_deck())
_FULL_DECK_SET = set(_FULL_DECK)
_CARD_ORDER = {card: index for index, card in enumerate(_FULL_DECK)}


@dataclass(frozen=True)
class HiddenCardEvidence:
    """One immutable, public, decision-time structural evidence item."""

    evidence_type: str
    player: str
    effective_category: str | None
    cards: tuple[str, ...]
    confidence: str
    source_trick_number: int | None
    source_play_index: int | None
    source: str


@dataclass(frozen=True)
class PlayerHiddenCardConstraints:
    """Exact cards and effective categories forbidden for one player."""

    player: str
    forbidden_effective_categories: tuple[str, ...]
    exact_cards: tuple[str, ...]


@dataclass(frozen=True)
class HiddenCardInferenceConstraints:
    """The complete public hard-constraint view for one decision."""

    game_type: str
    player_constraints: tuple[PlayerHiddenCardConstraints, ...]
    exact_public_hands: tuple[PublicHandConstraint, ...]
    evidence: tuple[HiddenCardEvidence, ...]
    provenance_status: str

    @property
    def confirmed_void_evidence(self) -> tuple[HiddenCardEvidence, ...]:
        return tuple(
            item
            for item in self.evidence
            if item.evidence_type == "failed_to_follow"
        )

    def for_player(self, player: str) -> PlayerHiddenCardConstraints:
        for constraint in self.player_constraints:
            if constraint.player == player:
                return constraint
        raise ValueError(f"No hidden-card constraints exist for player {player!r}.")


@dataclass(frozen=True)
class CompatibleAssignmentProblem:
    """One bounded labeled-card assignment problem."""

    cards: tuple[str, ...]
    left_slots: int
    right_slots: int
    skat_slots: int
    allowed_locations_by_card: tuple[tuple[str, tuple[str, ...]], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.cards, tuple):
            raise TypeError("cards must be a tuple.")
        if not isinstance(self.allowed_locations_by_card, tuple):
            raise TypeError("allowed_locations_by_card must be a tuple.")
        for item in self.allowed_locations_by_card:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[1], tuple)
            ):
                raise TypeError(
                    "allowed_locations_by_card entries must contain a card and owner tuple."
                )

    def allowed_locations(self) -> dict[str, tuple[str, ...]]:
        return dict(self.allowed_locations_by_card)


@dataclass(frozen=True)
class HiddenCardOwnershipMarginal:
    """Exact assignment-count numerators for one unresolved card."""

    card: str
    owner_assignment_counts: tuple[tuple[str, int], ...]
    compatible_world_count: int


@dataclass(frozen=True)
class CompatibleHiddenWorld:
    """One private compatible assignment selected uniformly."""

    left_hand: tuple[str, ...]
    right_hand: tuple[str, ...]
    hypothetical_skat: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("left_hand", "right_hand", "hypothetical_skat"):
            if not isinstance(getattr(self, field_name), tuple):
                raise TypeError(f"{field_name} must be a tuple.")


@dataclass(frozen=True)
class HiddenCardInferenceModel:
    """Exact count, marginals, and hard constraints for one public decision."""

    constraints: HiddenCardInferenceConstraints
    assignment_problem: CompatibleAssignmentProblem
    compatible_world_count: int
    ownership_marginals: tuple[HiddenCardOwnershipMarginal, ...]


@dataclass(frozen=True)
class _AttributedPublicPlay:
    player: str
    card: str
    trick_number: int
    play_index: int
    source: str


def get_public_effective_category(card: str, game_type: str) -> str:
    """Returns the stable public name for the existing effective-suit result."""
    return _EFFECTIVE_CATEGORY_NAMES[get_effective_suit(card, game_type)]


def _canonical_cards(cards: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return canonicalize_cards(tuple(cards))


def _derive_attributed_public_plays(
    state: GameState,
) -> tuple[tuple[_AttributedPublicPlay, ...], str]:
    plays: list[_AttributedPublicPlay] = []
    missing_provenance = bool(state.played_cards)
    attributed_source_found = False

    for trick_index, trick in enumerate(state.completed_tricks, start=1):
        cards = trick.get("cards")
        players = trick.get("players")
        if players is None:
            missing_provenance = True
            continue
        if not isinstance(cards, list) or len(cards) != 3:
            raise ValueError(
                f"Completed trick {trick_index} must contain exactly three cards."
            )
        if not isinstance(players, list) or len(players) != 3:
            raise ValueError(
                f"Completed trick {trick_index} must contain exactly three players."
            )
        expected_players = get_players_for_trick_leader(players[0])
        if players != expected_players:
            raise ValueError(
                f"Completed trick {trick_index} player order is invalid: {players}."
            )
        attributed_source_found = True
        plays.extend(
            _AttributedPublicPlay(
                player=player,
                card=card,
                trick_number=trick_index,
                play_index=play_index,
                source="completed_tricks",
            )
            for play_index, (player, card) in enumerate(
                zip(players, cards, strict=True), start=1
            )
        )

    if state.current_trick:
        if state.trick_leader == "unknown":
            missing_provenance = True
        else:
            current_players = get_players_for_trick_leader(state.trick_leader)
            attributed_source_found = True
            trick_number = len(state.completed_tricks) + 1
            plays.extend(
                _AttributedPublicPlay(
                    player=current_players[play_index - 1],
                    card=card,
                    trick_number=trick_number,
                    play_index=play_index,
                    source="current_trick",
                )
                for play_index, card in enumerate(state.current_trick, start=1)
            )

    if attributed_source_found and missing_provenance:
        status = "partially_available_missing_play_provenance"
    elif attributed_source_found:
        status = "available"
    elif missing_provenance:
        status = "not_available_missing_play_provenance"
    else:
        status = "no_public_play_history"
    return tuple(plays), status


def derive_failed_to_follow_evidence(
    state: GameState,
) -> tuple[HiddenCardEvidence, ...]:
    """Derives earliest confirmed void evidence from attributed public plays."""
    attributed_plays, _ = _derive_attributed_public_plays(state)
    plays_by_trick: dict[int, list[_AttributedPublicPlay]] = {}
    for play in attributed_plays:
        plays_by_trick.setdefault(play.trick_number, []).append(play)

    evidence_by_player_category: dict[tuple[str, str], HiddenCardEvidence] = {}
    for trick_number in sorted(plays_by_trick):
        trick_plays = plays_by_trick[trick_number]
        if len(trick_plays) < 2:
            continue
        led_category = get_public_effective_category(
            trick_plays[0].card,
            state.game_type,
        )
        for play in trick_plays[1:]:
            played_category = get_public_effective_category(play.card, state.game_type)
            if played_category == led_category:
                continue
            key = (play.player, led_category)
            evidence_by_player_category.setdefault(
                key,
                HiddenCardEvidence(
                    evidence_type="failed_to_follow",
                    player=play.player,
                    effective_category=led_category,
                    cards=(play.card,),
                    confidence="confirmed",
                    source_trick_number=play.trick_number,
                    source_play_index=play.play_index,
                    source=play.source,
                ),
            )

    player_order = {player: index for index, player in enumerate(PLAYER_ORDER)}
    category_order = {
        category: index for index, category in enumerate(EFFECTIVE_CATEGORY_ORDER)
    }
    return tuple(
        sorted(
            evidence_by_player_category.values(),
            key=lambda item: (
                item.source_trick_number or 0,
                item.source_play_index or 0,
                player_order[item.player],
                category_order[item.effective_category or "clubs"],
            ),
        )
    )


def _build_exact_structural_evidence(
    state: GameState,
    public_hand_constraints: tuple[PublicHandConstraint, ...],
    attributed_plays: tuple[_AttributedPublicPlay, ...],
) -> tuple[HiddenCardEvidence, ...]:
    evidence = [
        HiddenCardEvidence(
            evidence_type="local_exact_hand",
            player="me",
            effective_category=None,
            cards=_canonical_cards(state.hand),
            confidence="confirmed",
            source_trick_number=None,
            source_play_index=None,
            source="local_hand",
        )
    ]
    for constraint in sorted(
        public_hand_constraints,
        key=lambda item: PLAYER_ORDER.index(item.player),
    ):
        evidence.append(
            HiddenCardEvidence(
                evidence_type="exact_public_hand",
                player=constraint.player,
                effective_category=None,
                cards=_canonical_cards(constraint.cards),
                confidence="confirmed",
                source_trick_number=None,
                source_play_index=None,
                source=constraint.source,
            )
        )
    if state.skat:
        evidence.append(
            HiddenCardEvidence(
                evidence_type="known_skat",
                player="skat",
                effective_category=None,
                cards=_canonical_cards(state.skat),
                confidence="confirmed",
                source_trick_number=None,
                source_play_index=None,
                source="known_skat",
            )
        )
    evidence.extend(
        HiddenCardEvidence(
            evidence_type="public_played_card_owner",
            player=play.player,
            effective_category=get_public_effective_category(play.card, state.game_type),
            cards=(play.card,),
            confidence="confirmed",
            source_trick_number=play.trick_number,
            source_play_index=play.play_index,
            source=play.source,
        )
        for play in attributed_plays
    )
    return tuple(evidence)


def _validate_void_constraints(
    state: GameState,
    player_constraints: tuple[PlayerHiddenCardConstraints, ...],
    public_hand_constraints: tuple[PublicHandConstraint, ...],
    attributed_plays: tuple[_AttributedPublicPlay, ...],
    void_evidence: tuple[HiddenCardEvidence, ...],
) -> None:
    exact_hands = {"me": tuple(state.hand)}
    exact_sources = {"me": "local_hand"}
    for constraint in public_hand_constraints:
        if constraint.player in exact_hands and set(exact_hands[constraint.player]) != set(
            constraint.cards
        ):
            raise ValueError(
                f"Card ownership contradiction for {constraint.player}: exact hands disagree."
            )
        exact_hands[constraint.player] = constraint.cards
        exact_sources[constraint.player] = constraint.source

    for constraint in player_constraints:
        for card in exact_hands.get(constraint.player, ()):
            category = get_public_effective_category(card, state.game_type)
            if category in constraint.forbidden_effective_categories:
                raise ValueError(
                    f"Hidden-card inference contradiction for {constraint.player}: "
                    f"confirmed void in {category}, but {exact_sources[constraint.player]} "
                    f"fixes card {card} to that player."
                )

    earliest_void = {
        (item.player, item.effective_category): (
            item.source_trick_number or 0,
            item.source_play_index or 0,
            item.source,
        )
        for item in void_evidence
    }
    for play in attributed_plays:
        category = get_public_effective_category(play.card, state.game_type)
        source = earliest_void.get((play.player, category))
        if source is None:
            continue
        evidence_position = source[:2]
        play_position = (play.trick_number, play.play_index)
        if play_position <= evidence_position:
            continue
        raise ValueError(
            f"Hidden-card inference contradiction for {play.player}: confirmed void in "
            f"{category} from {source[2]}, but later public ownership assigns card "
            f"{play.card} at trick {play.trick_number}, play {play.play_index}."
        )


def build_hidden_card_inference_constraints(
    state: GameState,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> HiddenCardInferenceConstraints:
    """Builds and validates one deterministic public constraint set."""
    attributed_plays, provenance_status = _derive_attributed_public_plays(state)
    void_evidence = derive_failed_to_follow_evidence(state)
    forbidden_by_player: dict[str, set[str]] = {
        player: set() for player in PLAYER_ORDER
    }
    for item in void_evidence:
        if item.effective_category is not None:
            forbidden_by_player[item.player].add(item.effective_category)

    public_by_player: dict[str, PublicHandConstraint] = {}
    public_cards: set[str] = set()
    known_state_cards = set(state.hand + state.current_trick + state.played_cards + state.skat)
    known_state_cards.update(
        play.card for play in attributed_plays if play.source == "completed_tricks"
    )
    for constraint in public_hand_constraints:
        if constraint.player not in PLAYER_ORDER:
            raise ValueError(
                f"Unsupported public hand constraint player: {constraint.player}."
            )
        if constraint.player in public_by_player:
            raise ValueError(
                f"Duplicate public hand constraint for {constraint.player}."
            )
        duplicate_public_cards = public_cards.intersection(constraint.cards)
        if duplicate_public_cards:
            raise ValueError(
                "Public hand constraints fix cards to multiple players: "
                f"{sorted(duplicate_public_cards)}"
            )
        public_by_player[constraint.player] = constraint
        public_cards.update(constraint.cards)
        if constraint.player != "me":
            unavailable = sorted(set(constraint.cards).intersection(known_state_cards))
            if unavailable:
                raise ValueError(
                    f"Public {constraint.player} hand conflicts with known ownership: "
                    f"{unavailable}"
                )

    local_public = public_by_player.get("me")
    if local_public is not None and set(local_public.cards) != set(state.hand):
        raise ValueError("The local public hand constraint must exactly match state.hand.")

    category_order = {
        category: index for index, category in enumerate(EFFECTIVE_CATEGORY_ORDER)
    }
    player_constraints = tuple(
        PlayerHiddenCardConstraints(
            player=player,
            forbidden_effective_categories=tuple(
                sorted(forbidden_by_player[player], key=category_order.__getitem__)
            ),
            exact_cards=(
                _canonical_cards(state.hand)
                if player == "me"
                else _canonical_cards(public_by_player[player].cards)
                if player in public_by_player
                else ()
            ),
        )
        for player in PLAYER_ORDER
    )
    _validate_void_constraints(
        state,
        player_constraints,
        public_hand_constraints,
        attributed_plays,
        void_evidence,
    )
    evidence = (
        *_build_exact_structural_evidence(
            state,
            public_hand_constraints,
            attributed_plays,
        ),
        *void_evidence,
    )
    return HiddenCardInferenceConstraints(
        game_type=state.game_type,
        player_constraints=player_constraints,
        exact_public_hands=tuple(public_hand_constraints),
        evidence=evidence,
        provenance_status=provenance_status,
    )


def build_compatible_assignment_problem(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    constraints: HiddenCardInferenceConstraints,
) -> CompatibleAssignmentProblem:
    """Builds exact allowed ownership locations for every unresolved card."""
    if left_hand_size < 0 or right_hand_size < 0:
        raise ValueError("Opponent hand sizes must not be negative.")
    cards = tuple(get_unseen_cards(state))
    skat_slots = len(cards) - left_hand_size - right_hand_size
    if skat_slots < 0:
        raise ValueError(
            "Requested opponent hand sizes exceed the unresolved card count."
        )

    exact_by_player = {
        item.player: set(item.exact_cards)
        for item in constraints.player_constraints
        if item.player in {"left", "right"} and item.exact_cards
    }
    for player, expected_size in (
        ("left", left_hand_size),
        ("right", right_hand_size),
    ):
        exact_cards = exact_by_player.get(player)
        if exact_cards is None:
            continue
        if len(exact_cards) != expected_size:
            raise ValueError(
                f"The exact public {player} hand has {len(exact_cards)} cards, "
                f"but the required hand size is {expected_size}."
            )
        unavailable = sorted(exact_cards.difference(cards))
        if unavailable:
            raise ValueError(
                f"Exact public {player} cards are unavailable for assignment: {unavailable}"
            )

    forbidden = {
        player: set(constraints.for_player(player).forbidden_effective_categories)
        for player in ("left", "right")
    }
    exact_owner_by_card = {
        card: player
        for player, exact_cards in exact_by_player.items()
        for card in exact_cards
    }
    allowed_by_card: list[tuple[str, tuple[str, ...]]] = []
    for card in cards:
        allowed: list[str] = []
        for owner in OWNER_ORDER:
            exact_owner = exact_owner_by_card.get(card)
            if exact_owner is not None and owner != exact_owner:
                continue
            if owner == "skat":
                allowed.append(owner)
                continue
            owner_exact = exact_by_player.get(owner)
            if owner_exact is not None and card not in owner_exact:
                continue
            other_owner = "right" if owner == "left" else "left"
            if card in exact_by_player.get(other_owner, set()):
                continue
            category = get_public_effective_category(card, state.game_type)
            if category in forbidden[owner]:
                continue
            allowed.append(owner)
        allowed_by_card.append((card, tuple(allowed)))

    return CompatibleAssignmentProblem(
        cards=cards,
        left_slots=left_hand_size,
        right_slots=right_hand_size,
        skat_slots=skat_slots,
        allowed_locations_by_card=tuple(allowed_by_card),
    )


def _validate_assignment_inputs(
    cards: tuple[str, ...],
    left_slots: int,
    right_slots: int,
    allowed_locations_by_card: dict[str, tuple[str, ...]],
) -> None:
    for field_name, value in (
        ("left_slots", left_slots),
        ("right_slots", right_slots),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer.")
    if left_slots + right_slots > len(cards):
        raise ValueError("Assignment slot counts exceed the card count.")
    invalid_cards = [
        card for card in cards if not isinstance(card, str) or card not in _FULL_DECK_SET
    ]
    if invalid_cards:
        raise ValueError(f"Invalid compatible assignment cards: {invalid_cards}")
    if len(cards) != len(set(cards)):
        raise ValueError("Compatible assignment cards must be unique.")
    if set(cards) != set(allowed_locations_by_card):
        raise ValueError("Allowed locations must be provided for every assignment card.")
    for card in cards:
        allowed = allowed_locations_by_card[card]
        if len(allowed) != len(set(allowed)) or any(
            owner not in OWNER_ORDER for owner in allowed
        ):
            raise ValueError(f"Invalid allowed ownership locations for card {card}.")


def _validate_assignment_problem(
    problem: CompatibleAssignmentProblem,
) -> dict[str, tuple[str, ...]]:
    if not isinstance(problem, CompatibleAssignmentProblem):
        raise ValueError("problem must be a CompatibleAssignmentProblem.")
    if (
        isinstance(problem.skat_slots, bool)
        or not isinstance(problem.skat_slots, int)
        or problem.skat_slots < 0
    ):
        raise ValueError("skat_slots must be a non-negative integer.")
    location_cards = tuple(card for card, _ in problem.allowed_locations_by_card)
    if len(location_cards) != len(set(location_cards)):
        raise ValueError("Allowed ownership locations contain duplicate cards.")
    allowed_by_card = problem.allowed_locations()
    _validate_assignment_inputs(
        problem.cards,
        problem.left_slots,
        problem.right_slots,
        allowed_by_card,
    )
    if problem.cards != tuple(sorted(problem.cards, key=_CARD_ORDER.__getitem__)):
        raise ValueError("Compatible assignment cards must use canonical deck order.")
    if (
        problem.left_slots + problem.right_slots + problem.skat_slots
        != len(problem.cards)
    ):
        raise ValueError("Compatible assignment slots must equal the assignment-card count.")
    return allowed_by_card


def _build_completion_counter(
    cards: tuple[str, ...],
    allowed_locations_by_card: dict[str, tuple[str, ...]],
):
    @cache
    def count_from(index: int, left_remaining: int, right_remaining: int) -> int:
        remaining_cards = len(cards) - index
        if left_remaining < 0 or right_remaining < 0:
            return 0
        if left_remaining + right_remaining > remaining_cards:
            return 0
        if index == len(cards):
            return int(left_remaining == 0 and right_remaining == 0)

        total = 0
        for owner in allowed_locations_by_card[cards[index]]:
            if owner == "left":
                total += count_from(index + 1, left_remaining - 1, right_remaining)
            elif owner == "right":
                total += count_from(index + 1, left_remaining, right_remaining - 1)
            else:
                total += count_from(index + 1, left_remaining, right_remaining)
        return total

    return count_from


def count_compatible_assignments(
    cards: tuple[str, ...],
    left_slots: int,
    right_slots: int,
    allowed_locations_by_card: dict[str, tuple[str, ...]],
) -> int:
    """Counts exact compatible labeled assignments with bounded dynamic programming."""
    _validate_assignment_inputs(
        cards,
        left_slots,
        right_slots,
        allowed_locations_by_card,
    )
    counter = _build_completion_counter(cards, allowed_locations_by_card)
    return counter(0, left_slots, right_slots)


def count_compatible_hidden_worlds(problem: CompatibleAssignmentProblem) -> int:
    """Counts exact worlds for one immutable assignment problem."""
    allowed_by_card = _validate_assignment_problem(problem)
    counter = _build_completion_counter(problem.cards, allowed_by_card)
    return counter(0, problem.left_slots, problem.right_slots)


def validate_compatible_hidden_world(
    problem: CompatibleAssignmentProblem,
    world: CompatibleHiddenWorld,
) -> None:
    """Validates one complete assignment against exact slots and allowed owners."""
    allowed_by_card = _validate_assignment_problem(problem)
    if not isinstance(world, CompatibleHiddenWorld):
        raise ValueError("world must be a CompatibleHiddenWorld.")

    locations = (
        ("left", world.left_hand, problem.left_slots),
        ("right", world.right_hand, problem.right_slots),
        ("skat", world.hypothetical_skat, problem.skat_slots),
    )
    all_cards: list[str] = []
    for owner, cards, expected_size in locations:
        if len(cards) != expected_size:
            raise ValueError(
                f"Compatible world {owner} size is {len(cards)}, expected {expected_size}."
            )
        for card in cards:
            if not isinstance(card, str) or card not in _FULL_DECK_SET:
                raise ValueError(f"Compatible world contains invalid card {card!r}.")
            if card not in allowed_by_card:
                raise ValueError(f"Compatible world contains foreign card {card}.")
            if owner not in allowed_by_card[card]:
                raise ValueError(f"Card {card} is not allowed to be owned by {owner}.")
        if cards != tuple(sorted(cards, key=_CARD_ORDER.__getitem__)):
            raise ValueError(f"Compatible world {owner} cards must use canonical deck order.")
        all_cards.extend(cards)

    if len(all_cards) != len(set(all_cards)):
        raise ValueError("Compatible world assigns at least one card more than once.")
    if set(all_cards) != set(problem.cards):
        missing = tuple(card for card in problem.cards if card not in all_cards)
        foreign = tuple(card for card in all_cards if card not in allowed_by_card)
        raise ValueError(
            "Compatible world must cover every assignment card exactly once: "
            f"missing={missing}, foreign={foreign}."
        )


def enumerate_compatible_hidden_worlds(
    problem: CompatibleAssignmentProblem,
    max_worlds: int,
) -> tuple[CompatibleHiddenWorld, ...]:
    """Enumerates every compatible world canonically when the exact space fits."""
    if isinstance(max_worlds, bool) or not isinstance(max_worlds, int) or max_worlds <= 0:
        raise ValueError("max_worlds must be a positive integer.")
    allowed_by_card = _validate_assignment_problem(problem)
    counter = _build_completion_counter(problem.cards, allowed_by_card)
    total = counter(0, problem.left_slots, problem.right_slots)
    if total > max_worlds:
        raise ValueError(
            f"Compatible world count {total} exceeds max_worlds {max_worlds}; "
            "enumeration is not truncated."
        )
    if total == 0:
        return ()

    hands: dict[str, list[str]] = {owner: [] for owner in OWNER_ORDER}
    worlds: list[CompatibleHiddenWorld] = []

    def enumerate_from(index: int, left_remaining: int, right_remaining: int) -> None:
        if index == len(problem.cards):
            world = CompatibleHiddenWorld(
                left_hand=tuple(hands["left"]),
                right_hand=tuple(hands["right"]),
                hypothetical_skat=tuple(hands["skat"]),
            )
            validate_compatible_hidden_world(problem, world)
            worlds.append(world)
            return

        card = problem.cards[index]
        allowed = allowed_by_card[card]
        for owner in OWNER_ORDER:
            if owner not in allowed:
                continue
            next_left = left_remaining - int(owner == "left")
            next_right = right_remaining - int(owner == "right")
            if counter(index + 1, next_left, next_right) == 0:
                continue
            hands[owner].append(card)
            enumerate_from(index + 1, next_left, next_right)
            hands[owner].pop()

    enumerate_from(0, problem.left_slots, problem.right_slots)
    if len(worlds) != total:
        raise ValueError("Canonical enumeration did not reconcile with the exact world count.")
    return tuple(worlds)


def calculate_hidden_card_ownership_marginals(
    problem: CompatibleAssignmentProblem,
    compatible_world_count: int | None = None,
) -> tuple[HiddenCardOwnershipMarginal, ...]:
    """Calculates exact per-card ownership counts under the uniform model."""
    allowed_by_card = _validate_assignment_problem(problem)
    total = (
        count_compatible_hidden_worlds(problem)
        if compatible_world_count is None
        else compatible_world_count
    )
    if total <= 0:
        raise ValueError("Cannot calculate ownership marginals without a compatible world.")

    marginals = []
    for card in problem.cards:
        counts = []
        original_allowed = allowed_by_card[card]
        for owner in OWNER_ORDER:
            if owner not in original_allowed:
                owner_count = 0
            else:
                forced_allowed = dict(allowed_by_card)
                forced_allowed[card] = (owner,)
                owner_count = count_compatible_assignments(
                    problem.cards,
                    problem.left_slots,
                    problem.right_slots,
                    forced_allowed,
                )
            counts.append((owner, owner_count))
        if sum(count for _, count in counts) != total:
            raise ValueError(f"Ownership marginal counts do not reconcile for card {card}.")
        marginals.append(
            HiddenCardOwnershipMarginal(
                card=card,
                owner_assignment_counts=tuple(counts),
                compatible_world_count=total,
            )
        )
    return tuple(marginals)


def classify_hidden_card_confidence(
    maximum_probability: float,
    compatible_owner_count: int,
) -> str:
    """Classifies compatible-world concentration without adding constraints."""
    if compatible_owner_count == 1:
        return "confirmed"
    if maximum_probability >= HIGH_CONFIDENCE_MIN_PROBABILITY:
        return "high"
    if maximum_probability >= MEDIUM_CONFIDENCE_MIN_PROBABILITY:
        return "medium"
    return "low"


def sample_compatible_hidden_world(
    problem: CompatibleAssignmentProblem,
    random_generator: random.Random,
) -> CompatibleHiddenWorld:
    """Samples one world uniformly using exact DP completion counts."""
    allowed_by_card = _validate_assignment_problem(problem)
    counter = _build_completion_counter(problem.cards, allowed_by_card)
    total = counter(0, problem.left_slots, problem.right_slots)
    if total == 0:
        raise ValueError("Hidden-card inference has no compatible assignment to sample.")

    return _sample_compatible_hidden_world_with_counter(
        problem,
        random_generator,
        allowed_by_card,
        counter,
    )


def _sample_compatible_hidden_world_with_counter(
    problem: CompatibleAssignmentProblem,
    random_generator: random.Random,
    allowed_by_card: dict[str, tuple[str, ...]],
    counter,
) -> CompatibleHiddenWorld:
    """Draws one world using a caller-validated reusable completion counter."""

    hands: dict[str, list[str]] = {owner: [] for owner in OWNER_ORDER}
    left_remaining = problem.left_slots
    right_remaining = problem.right_slots
    for index, card in enumerate(problem.cards):
        choices: list[tuple[str, int]] = []
        for owner in allowed_by_card[card]:
            next_left = left_remaining - int(owner == "left")
            next_right = right_remaining - int(owner == "right")
            completion_count = counter(index + 1, next_left, next_right)
            if completion_count > 0:
                choices.append((owner, completion_count))
        choice_total = sum(count for _, count in choices)
        if choice_total == 0:
            raise ValueError(
                f"Hidden-card inference reached an impossible assignment at card {card}."
            )
        draw = random_generator.randrange(choice_total)
        selected_owner = choices[-1][0]
        cumulative = 0
        for owner, completion_count in choices:
            cumulative += completion_count
            if draw < cumulative:
                selected_owner = owner
                break
        hands[selected_owner].append(card)
        left_remaining -= int(selected_owner == "left")
        right_remaining -= int(selected_owner == "right")

    if left_remaining != 0 or right_remaining != 0:
        raise ValueError("Sampled compatible world does not fill exact opponent hand sizes.")
    world = CompatibleHiddenWorld(
        left_hand=tuple(hands["left"]),
        right_hand=tuple(hands["right"]),
        hypothetical_skat=tuple(hands["skat"]),
    )
    validate_compatible_hidden_world(problem, world)
    return world


def sample_compatible_hidden_worlds(
    problem: CompatibleAssignmentProblem,
    sample_count: int,
    random_generator: random.Random,
) -> tuple[CompatibleHiddenWorld, ...]:
    """Draws IID compatible worlds with replacement while preserving draw order."""
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count <= 0
    ):
        raise ValueError("sample_count must be a positive integer.")
    if not isinstance(random_generator, random.Random):
        raise ValueError("random_generator must be a random.Random instance.")
    allowed_by_card = _validate_assignment_problem(problem)
    counter = _build_completion_counter(problem.cards, allowed_by_card)
    total = counter(0, problem.left_slots, problem.right_slots)
    if total == 0:
        raise ValueError("Hidden-card inference has no compatible assignment to sample.")
    return tuple(
        _sample_compatible_hidden_world_with_counter(
            problem,
            random_generator,
            allowed_by_card,
            counter,
        )
        for _ in range(sample_count)
    )


def build_hidden_card_inference_model(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> HiddenCardInferenceModel | None:
    """Builds the exact model when confirmed void evidence is available."""
    constraints = build_hidden_card_inference_constraints(
        state,
        public_hand_constraints,
    )
    if not constraints.confirmed_void_evidence:
        return None
    problem = build_compatible_assignment_problem(
        state,
        left_hand_size,
        right_hand_size,
        constraints,
    )
    compatible_world_count = count_compatible_hidden_worlds(problem)
    if compatible_world_count == 0:
        voids = ", ".join(
            f"{item.player}:{item.effective_category}"
            for item in constraints.confirmed_void_evidence
        )
        raise ValueError(
            "Hidden-card inference constraints leave no compatible assignment "
            f"for confirmed voids [{voids}]."
        )
    marginals = calculate_hidden_card_ownership_marginals(
        problem,
        compatible_world_count,
    )
    return HiddenCardInferenceModel(
        constraints=constraints,
        assignment_problem=problem,
        compatible_world_count=compatible_world_count,
        ownership_marginals=marginals,
    )


def _serialize_evidence(item: HiddenCardEvidence) -> dict[str, Any]:
    return {
        "evidence_type": item.evidence_type,
        "player": item.player,
        "effective_category": item.effective_category,
        "cards": list(item.cards),
        "confidence": item.confidence,
        "source_trick_number": item.source_trick_number,
        "source_play_index": item.source_play_index,
        "source": item.source,
    }


def _serialize_marginal(item: HiddenCardOwnershipMarginal) -> dict[str, Any]:
    counts = dict(item.owner_assignment_counts)
    probabilities = {
        owner: counts[owner] / item.compatible_world_count for owner in OWNER_ORDER
    }
    possible_owners = [owner for owner in OWNER_ORDER if counts[owner] > 0]
    most_likely_owner = max(OWNER_ORDER, key=lambda owner: probabilities[owner])
    maximum_probability = probabilities[most_likely_owner]
    confidence = classify_hidden_card_confidence(
        maximum_probability,
        len(possible_owners),
    )
    return {
        "card": item.card,
        "possible_owners": possible_owners,
        "ownership_probability": probabilities,
        "most_likely_owner": most_likely_owner,
        "confidence": confidence,
        "exact_owner_confirmed": confidence == "confirmed",
    }


def build_hidden_card_inference_summary(
    model: HiddenCardInferenceModel | None,
) -> dict[str, Any] | None:
    """Builds the version-1 privacy-safe public summary."""
    if model is None:
        return None
    constraints = model.constraints
    exact_public_players = {
        constraint.player for constraint in constraints.exact_public_hands
    }
    ownership_estimates = [
        _serialize_marginal(item)
        for item in model.ownership_marginals
        if not any(
            item.card in constraint.cards
            for constraint in constraints.exact_public_hands
        )
    ]
    confirmed_voids = [
        {
            "player": player,
            "forbidden_effective_categories": list(
                constraints.for_player(player).forbidden_effective_categories
            ),
        }
        for player in PLAYER_ORDER
        if constraints.for_player(player).forbidden_effective_categories
    ]
    return {
        "schema_version": HIDDEN_CARD_INFERENCE_SCHEMA_VERSION,
        "information_cutoff": "current_decision",
        "mode": HIDDEN_CARD_INFERENCE_MODE,
        "compatible_world_model": COMPATIBLE_WORLD_MODEL,
        "compatible_world_count": model.compatible_world_count,
        "constraints_applied": True,
        "provenance_status": constraints.provenance_status,
        "confirmed_void_evidence_count": len(
            constraints.confirmed_void_evidence
        ),
        "exact_public_hand_count": len(exact_public_players),
        "hypothetical_skat_size": model.assignment_problem.skat_slots,
        "confidence_basis": CONFIDENCE_BASIS,
        "confidence_is_calibrated": False,
        "confidence_thresholds": {
            "high_min_probability": HIGH_CONFIDENCE_MIN_PROBABILITY,
            "medium_min_probability": MEDIUM_CONFIDENCE_MIN_PROBABILITY,
        },
        "evidence": [_serialize_evidence(item) for item in constraints.evidence],
        "confirmed_voids": confirmed_voids,
        "ownership_estimates": ownership_estimates,
        "behavioral_inference_applied": False,
        "future_information_used": False,
        "actual_hidden_hands_emitted": False,
        "privacy_flags": {
            "sampled_hands_emitted": False,
            "sampled_hypothetical_skat_emitted": False,
            "coherent_root_ownership_emitted": False,
            "actual_historical_hidden_hands_emitted": False,
            "dynamic_programming_tables_emitted": False,
        },
    }
