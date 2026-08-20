from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.bounded_search_information import (
    SEARCH_INFORMATION_CUTOFF,
    SEARCH_INFORMATION_SOURCES,
    SearchCompletedTrick,
    SearchInformationView,
    SearchPublicPlay,
    SearchRemainingHandSize,
)
from skat_ai.bounded_search_result import (
    WORLD_COVERAGE_VALUES,
    AggregateSearchCandidateResult,
    rank_search_candidate_results,
)
from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
)
from skat_ai.hidden_card_inference import (
    EFFECTIVE_CATEGORY_ORDER,
    PLAYER_ORDER,
    PlayerHiddenCardConstraints,
)
from skat_ai.public_hand_constraint import (
    DECLARED_OUVERT_SOURCE,
    DECLARER_EXPOSURE_CONTINUATION_SOURCE,
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PUBLIC_HAND_VISIBILITY_SCOPE,
    PublicHandConstraint,
    build_serializable_public_hand_constraints,
    canonicalize_cards,
)
from skat_ai.rules import GAME_TYPES
from skat_ai.side_ownership import get_player_side
from skat_ai.terminal_utility import TERMINAL_UTILITY_VERSION
from skat_ai.turn_phase import CONCRETE_PLAYERS, UNKNOWN_PLAYER

INFORMATION_SET_SEARCH_WORLD_STATE_VERSION = 1
INFORMATION_SET_SEARCH_OBSERVATION_VERSION = 1
INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION = 1
INFORMATION_SET_SEARCH_BUDGET_VERSION = 1
INFORMATION_SET_SEARCH_REQUEST_VERSION = 1
INFORMATION_SET_SEARCH_PREPARATION_VERSION = 1
INFORMATION_SET_SEARCH_RESULT_VERSION = 1

BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD = (
    "bounded_information_set_policy_search_v1"
)
INFORMATION_SET_SEARCH_CONTROLLED_PLAYERS = ("me",)
INFORMATION_SET_SEARCH_CONTROL_SCOPES = ("root_perspective_only",)
INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS = 3

INFORMATION_SET_SEARCH_PREPARATION_STATUSES = ("available", "unavailable")
INFORMATION_SET_SEARCH_STATUSES = (
    "complete",
    "partial",
    "timeout",
    "unavailable",
)
INFORMATION_SET_SEARCH_POLICY_CLAIMS = (
    "none",
    "common_policy_prefix",
    "exact_selected_world_policy",
)
INFORMATION_SET_SEARCH_POLICY_CONSISTENCY_VALUES = (
    "not_assessed",
    "controlled_player_information_set_consistent",
)
INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS = (
    "unsupported_game_type",
    "unsupported_turn_phase",
    "unsupported_perspective",
    "local_player_not_to_act",
    "missing_concrete_declarer",
    "remaining_trick_limit_exceeded",
    "incompatible_world_space",
    "missing_terminal_utility_inputs",
    "game_already_complete",
    "no_legal_cards",
    "unsupported_fixed_policy",
    "nondeterministic_fixed_policy",
    "information_set_model_unavailable",
)
INFORMATION_SET_SEARCH_STOP_REASONS = (
    "completed",
    "state_node_budget_exhausted",
    "information_set_budget_exhausted",
    "depth_budget_exhausted",
    "wall_clock_timeout",
    *INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS,
)
INFORMATION_SET_SEARCH_FIXED_POLICY_VALUES = (
    "lowest_point",
    "highest_point",
    "basic_trick_play",
    "basic_defender_response",
    "basic_defender_lead",
)
_DEFENDER_ONLY_POLICY_NAMES = {
    "basic_defender_response",
    "basic_defender_lead",
}

INFORMATION_SET_SEARCH_SOURCE_POLICY = (
    "existing_information_view_and_selected_compatible_worlds"
)
INFORMATION_SET_SEARCH_WORLD_STATE_POLICY = "exact_state_plus_complete_public_history"
INFORMATION_SET_SEARCH_OBSERVATION_POLICY = (
    "actor_own_hand_private_facts_and_public_history_only"
)
INFORMATION_SET_SEARCH_EQUIVALENCE_POLICY = (
    "equal_actor_observations_define_one_information_set"
)
INFORMATION_SET_SEARCH_CONTROLLED_POLICY = (
    "optimize_root_perspective_policy_over_information_sets"
)
INFORMATION_SET_SEARCH_FIXED_PLAYER_POLICY = (
    "non_controlled_players_use_fixed_information_safe_policies"
)
INFORMATION_SET_SEARCH_PARTNER_POLICY = (
    "defender_partner_remains_separate_fixed_policy_actor"
)
INFORMATION_SET_SEARCH_OUT_OF_PLAY_POLICY = (
    "exact_discards_visible_only_to_non_hand_declarer"
)
INFORMATION_SET_SEARCH_PUBLIC_HAND_POLICY = (
    "authorized_public_hands_visible_to_all_and_shrink_with_play"
)
INFORMATION_SET_SEARCH_VOID_POLICY = "confirmed_voids_derive_from_public_play_only"
INFORMATION_SET_SEARCH_WORLD_WEIGHT_POLICY = (
    "selected_world_order_and_sampled_duplicate_weight_are_preserved"
)
INFORMATION_SET_SEARCH_FIXED_POLICY_TIE_POLICY = (
    "first_canonical_preferred_card"
)
INFORMATION_SET_SEARCH_UTILITY_POLICY = "existing_local_side_terminal_utility"
INFORMATION_SET_SEARCH_STRATEGY_FUSION_POLICY = (
    "one_controlled_action_per_equal_information_set"
)
INFORMATION_SET_SEARCH_CLAIM_POLICY = (
    "best_response_to_fixed_policies_not_equilibrium_or_general_optimality"
)
INFORMATION_SET_SEARCH_EXECUTION_POLICY = (
    "contracts_and_preparation_without_policy_search_execution"
)
INFORMATION_SET_SEARCH_PUBLIC_POLICY = (
    "private_internal_without_public_schema_or_routing"
)

INFORMATION_SET_SEARCH_ANALYSIS_METHOD = "information_set_search"
_STRUCTURAL_STOP_REASONS = (
    "state_node_budget_exhausted",
    "information_set_budget_exhausted",
    "depth_budget_exhausted",
)
_FULL_DECK_SET = set(get_full_deck())


def _require_version(value: object, expected: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"Unsupported {field_name}.")


def _require_positive_integer(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a strict positive integer.")


def _require_non_negative_integer(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a strict non-negative integer.")


def _serialize_information_view(view: SearchInformationView) -> dict[str, Any]:
    return {
        "source": view.source,
        "perspective_player": view.perspective_player,
        "declarer_player": view.declarer_player,
        "local_side": view.local_side,
        "declaration": build_serializable_game_declaration(view.declaration),
        "game_type": view.game_type,
        "local_remaining_hand": list(view.local_remaining_hand),
        "current_trick": [
            {"player": play.player, "card": play.card} for play in view.current_trick
        ],
        "completed_tricks": [
            {
                "plays": [
                    {"player": play.player, "card": play.card}
                    for play in trick.plays
                ],
                "winner_player": trick.winner_player,
                "winner_side": trick.winner_side,
                "trick_points": trick.trick_points,
            }
            for trick in view.completed_tricks
        ],
        "next_player": view.next_player,
        "declarer_points": view.declarer_points,
        "defender_points": view.defender_points,
        "declarer_trick_count": view.declarer_trick_count,
        "defender_trick_count": view.defender_trick_count,
        "remaining_hand_sizes": [
            {"player": item.player, "card_count": item.card_count}
            for item in view.remaining_hand_sizes
        ],
        "known_skat_cards": list(view.known_skat_cards),
        "public_hand_constraints": build_serializable_public_hand_constraints(
            view.public_hand_constraints
        ),
        "hidden_card_constraints": [
            {
                "player": item.player,
                "forbidden_effective_categories": list(
                    item.forbidden_effective_categories
                ),
                "exact_cards": list(item.exact_cards),
            }
            for item in view.hidden_card_constraints
        ],
        "information_cutoff": view.information_cutoff,
    }


def _serialize_candidate(candidate: AggregateSearchCandidateResult) -> dict[str, Any]:
    return {
        "card": candidate.card,
        "rank": candidate.rank,
        "is_recommended": candidate.is_recommended,
        "completed_world_count": candidate.completed_world_count,
        "local_contract_success_count": candidate.local_contract_success_count,
        "local_contract_success_rate": candidate.local_contract_success_rate,
        "mean_local_side_game_score": candidate.mean_local_side_game_score,
        "mean_local_side_card_point_margin": (
            candidate.mean_local_side_card_point_margin
        ),
    }


def _validate_information_view_structure(view: SearchInformationView) -> None:
    if view.source not in SEARCH_INFORMATION_SOURCES:
        raise ValueError("Unsupported information-set Search information source.")
    if view.information_cutoff != SEARCH_INFORMATION_CUTOFF:
        raise ValueError("Unsupported information-set Search information cutoff.")
    if view.perspective_player not in CONCRETE_PLAYERS:
        raise ValueError("Search perspective must be one concrete Player.")
    if view.declarer_player not in {*CONCRETE_PLAYERS, UNKNOWN_PLAYER}:
        raise ValueError("Search Declarer must be concrete or unknown.")
    if view.next_player not in {*CONCRETE_PLAYERS, UNKNOWN_PLAYER}:
        raise ValueError("Search next Player must be concrete or unknown.")
    if not isinstance(view.declaration, GameDeclaration):
        raise ValueError("Search information requires a GameDeclaration.")
    if not isinstance(view.game_type, str) or not view.game_type:
        raise ValueError("Search information requires a game type.")
    if view.game_type in GAME_TYPES and view.game_type != view.declaration.game_type:
        raise ValueError("Search information game type and Declaration must agree.")
    expected_side = (
        get_player_side(view.perspective_player, view.declarer_player)
        if view.declarer_player in CONCRETE_PLAYERS
        else None
    )
    if view.local_side != expected_side:
        raise ValueError("Search perspective side contradicts the Declarer.")

    card_tuples = (
        (view.local_remaining_hand, "local_remaining_hand", 10),
        (view.known_skat_cards, "known_skat_cards", 2),
    )
    for cards, field_name, maximum in card_tuples:
        if not isinstance(cards, tuple):
            raise TypeError(f"{field_name} must be a tuple.")
        if any(
            not isinstance(card, str) or card not in _FULL_DECK_SET
            for card in cards
        ):
            raise ValueError(f"{field_name} contains an invalid Card.")
        if len(cards) != len(set(cards)) or len(cards) > maximum:
            raise ValueError(f"{field_name} contains invalid Card cardinality.")
        if cards != canonicalize_cards(cards):
            raise ValueError(f"{field_name} must use canonical Card order.")

    if not isinstance(view.current_trick, tuple) or len(view.current_trick) > 2:
        raise ValueError("current_trick must be a tuple of at most two Plays.")
    if any(not isinstance(play, SearchPublicPlay) for play in view.current_trick):
        raise ValueError("current_trick contains an invalid Play.")
    if any(
        play.player not in CONCRETE_PLAYERS or play.card not in _FULL_DECK_SET
        for play in view.current_trick
    ):
        raise ValueError("current_trick contains invalid Player or Card facts.")
    if len({play.player for play in view.current_trick}) != len(view.current_trick):
        raise ValueError("current_trick contains duplicate Players.")

    if not isinstance(view.completed_tricks, tuple):
        raise TypeError("completed_tricks must be a tuple.")
    for trick in view.completed_tricks:
        if not isinstance(trick, SearchCompletedTrick):
            raise ValueError("completed_tricks contain an invalid Trick.")
        if not isinstance(trick.plays, tuple) or len(trick.plays) != 3:
            raise ValueError("Every completed Trick must contain three Plays.")
        if any(not isinstance(play, SearchPublicPlay) for play in trick.plays):
            raise ValueError("A completed Trick contains an invalid Play.")
        if any(
            play.player not in CONCRETE_PLAYERS or play.card not in _FULL_DECK_SET
            for play in trick.plays
        ):
            raise ValueError("A completed Trick contains invalid Player or Card facts.")
        if trick.winner_player not in CONCRETE_PLAYERS:
            raise ValueError("A completed Trick has an invalid winner Player.")
        if trick.winner_side not in {"declarer", "defenders"}:
            raise ValueError("A completed Trick has an invalid winner side.")
        _require_non_negative_integer(trick.trick_points, "trick_points")

    if any(
        not isinstance(item, SearchRemainingHandSize)
        for item in view.remaining_hand_sizes
    ):
        raise ValueError("remaining_hand_sizes contain an invalid value.")
    if tuple(item.player for item in view.remaining_hand_sizes) != tuple(
        CONCRETE_PLAYERS
    ):
        raise ValueError("remaining_hand_sizes must cover all Players canonically.")
    for item in view.remaining_hand_sizes:
        _require_non_negative_integer(item.card_count, "remaining card_count")
        if item.card_count > 10:
            raise ValueError("A remaining hand cannot exceed ten Cards.")
    if not isinstance(view.public_hand_constraints, tuple) or any(
        not isinstance(item, PublicHandConstraint)
        for item in view.public_hand_constraints
    ):
        raise ValueError("public_hand_constraints contain an invalid value.")
    if not isinstance(view.hidden_card_constraints, tuple) or any(
        not isinstance(item, PlayerHiddenCardConstraints)
        for item in view.hidden_card_constraints
    ):
        raise ValueError("hidden_card_constraints contain an invalid value.")
    for field_name in (
        "declarer_points",
        "defender_points",
        "declarer_trick_count",
        "defender_trick_count",
    ):
        _require_non_negative_integer(getattr(view, field_name), field_name)
    if view.declarer_points + view.defender_points > 120:
        raise ValueError("Search points cannot exceed 120.")
    if view.declarer_trick_count + view.defender_trick_count > 10:
        raise ValueError("Search completed-Trick counts cannot exceed ten.")

    if view.declaration.hand_game and view.known_skat_cards:
        raise ValueError("A Hand game cannot expose out-of-play Cards.")
    if view.declarer_player not in CONCRETE_PLAYERS and view.known_skat_cards:
        raise ValueError("Unknown Declarer ownership cannot expose out-of-play Cards.")
    if (
        view.declarer_player in CONCRETE_PLAYERS
        and view.perspective_player != view.declarer_player
        and view.known_skat_cards
    ):
        raise ValueError("A Defender cannot retain hidden out-of-play Cards.")

    public_by_player: dict[str, PublicHandConstraint] = {}
    for constraint in view.public_hand_constraints:
        if constraint.player not in CONCRETE_PLAYERS:
            raise ValueError("A public hand has an invalid Player.")
        if constraint.player in public_by_player:
            raise ValueError("Public hands cannot repeat one Player.")
        if not isinstance(constraint.cards, tuple):
            raise TypeError("Public hand Cards must be a tuple.")
        if any(card not in _FULL_DECK_SET for card in constraint.cards):
            raise ValueError("A public hand contains an invalid Card.")
        if (
            len(constraint.cards) != len(set(constraint.cards))
            or constraint.cards != canonicalize_cards(constraint.cards)
        ):
            raise ValueError("Public hand Cards must be unique and canonical.")
        if constraint.visibility_scope != PUBLIC_HAND_VISIBILITY_SCOPE:
            raise ValueError("A public hand must be visible to all Players.")
        if constraint.source == DECLARED_OUVERT_SOURCE:
            if (
                not view.declaration.ouvert
                or constraint.player != view.declarer_player
            ):
                raise ValueError("Declared-Ouvert public-hand authorization is invalid.")
        elif constraint.source == DECLARER_EXPOSURE_CONTINUATION_SOURCE:
            if constraint.player != view.declarer_player:
                raise ValueError("Declarer exposure must expose the Declarer hand.")
        elif constraint.source == DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE:
            if constraint.player == view.declarer_player:
                raise ValueError("Defender open play cannot expose the Declarer hand.")
        else:
            raise ValueError("A public hand has an unsupported source.")
        public_by_player[constraint.player] = constraint

    if tuple(item.player for item in view.hidden_card_constraints) != PLAYER_ORDER:
        raise ValueError("Hidden constraints must cover all Players canonically.")
    for constraint in view.hidden_card_constraints:
        if not isinstance(constraint.forbidden_effective_categories, tuple):
            raise TypeError("Forbidden effective categories must be a tuple.")
        categories = constraint.forbidden_effective_categories
        if (
            any(category not in EFFECTIVE_CATEGORY_ORDER for category in categories)
            or len(categories) != len(set(categories))
            or categories
            != tuple(
                category
                for category in EFFECTIVE_CATEGORY_ORDER
                if category in categories
            )
        ):
            raise ValueError("Forbidden effective categories must be unique and canonical.")
        if not isinstance(constraint.exact_cards, tuple):
            raise TypeError("Exact constraint Cards must be a tuple.")
        if any(card not in _FULL_DECK_SET for card in constraint.exact_cards):
            raise ValueError("Exact constraints contain an invalid Card.")
        if (
            len(constraint.exact_cards) != len(set(constraint.exact_cards))
            or constraint.exact_cards != canonicalize_cards(constraint.exact_cards)
        ):
            raise ValueError("Exact constraint Cards must be unique and canonical.")
        if constraint.player == "me":
            if constraint.exact_cards != view.local_remaining_hand:
                raise ValueError("Local exact constraints must match the local hand.")
        elif constraint.exact_cards:
            public = public_by_player.get(constraint.player)
            if public is None or constraint.exact_cards != public.cards:
                raise ValueError(
                    "Exact opponent constraints require an equal authorized public hand."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetFixedPlayerPolicyV1:
    player: str
    lead_policy: str
    response_policy: str
    tie_policy: str

    def __post_init__(self) -> None:
        if self.player not in {"left", "right"}:
            raise ValueError("A fixed information-set Policy must belong to left or right.")
        for field_name in ("lead_policy", "response_policy"):
            value = getattr(self, field_name)
            if value == "random_legal":
                raise ValueError("random_legal is not deterministic and is not supported.")
            if value not in INFORMATION_SET_SEARCH_FIXED_POLICY_VALUES:
                raise ValueError(f"Invalid information-set fixed policy: {value}")
        if self.tie_policy != INFORMATION_SET_SEARCH_FIXED_POLICY_TIE_POLICY:
            raise ValueError("Unsupported information-set fixed-policy tie behavior.")

    def to_dict(self) -> dict[str, str]:
        return {
            "player": self.player,
            "lead_policy": self.lead_policy,
            "response_policy": self.response_policy,
            "tie_policy": self.tie_policy,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchPolicySettingsV1:
    information_set_search_policy_settings_version: int
    controlled_player: str
    control_scope: str
    fixed_player_policies: tuple[InformationSetFixedPlayerPolicyV1, ...]

    def __post_init__(self) -> None:
        _require_version(
            self.information_set_search_policy_settings_version,
            INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
            "information-set Search Policy Settings version",
        )
        if self.controlled_player not in INFORMATION_SET_SEARCH_CONTROLLED_PLAYERS:
            raise ValueError("The controlled information-set Search Player must be me.")
        if self.control_scope not in INFORMATION_SET_SEARCH_CONTROL_SCOPES:
            raise ValueError("Unsupported information-set Search control scope.")
        if not isinstance(self.fixed_player_policies, tuple):
            raise TypeError("fixed_player_policies must be a tuple.")
        if any(
            not isinstance(item, InformationSetFixedPlayerPolicyV1)
            for item in self.fixed_player_policies
        ):
            raise ValueError("fixed_player_policies contain an invalid value.")
        players = tuple(item.player for item in self.fixed_player_policies)
        if len(players) != 2 or set(players) != {"left", "right"}:
            raise ValueError("Fixed Policies must cover left and right exactly once.")
        canonical = tuple(
            sorted(
                self.fixed_player_policies,
                key=lambda item: ("left", "right").index(item.player),
            )
        )
        object.__setattr__(self, "fixed_player_policies", canonical)

    def for_player(self, player: str) -> InformationSetFixedPlayerPolicyV1:
        for policy in self.fixed_player_policies:
            if policy.player == player:
                return policy
        raise ValueError(f"No fixed information-set Policy exists for {player!r}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_set_search_policy_settings_version": (
                self.information_set_search_policy_settings_version
            ),
            "controlled_player": self.controlled_player,
            "control_scope": self.control_scope,
            "fixed_player_policies": [
                item.to_dict() for item in self.fixed_player_policies
            ],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchBudgetV1:
    information_set_search_budget_version: int
    max_remaining_tricks: int
    max_depth_plies: int
    max_state_nodes: int
    max_information_sets: int
    max_selected_worlds: int
    max_sampled_worlds: int
    minimum_comparable_worlds: int
    wall_clock_timeout_ms: int | None

    def __post_init__(self) -> None:
        _require_version(
            self.information_set_search_budget_version,
            INFORMATION_SET_SEARCH_BUDGET_VERSION,
            "information-set Search Budget version",
        )
        for field_name in (
            "max_remaining_tricks",
            "max_depth_plies",
            "max_state_nodes",
            "max_information_sets",
            "max_selected_worlds",
            "max_sampled_worlds",
            "minimum_comparable_worlds",
        ):
            _require_positive_integer(getattr(self, field_name), field_name)
        if self.wall_clock_timeout_ms is not None:
            _require_positive_integer(
                self.wall_clock_timeout_ms,
                "wall_clock_timeout_ms",
            )
        if self.max_remaining_tricks > INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS:
            raise ValueError("Information-set Search supports at most three Tricks.")
        if self.max_sampled_worlds > self.max_selected_worlds:
            raise ValueError("max_sampled_worlds cannot exceed max_selected_worlds.")
        if self.minimum_comparable_worlds > self.max_selected_worlds:
            raise ValueError(
                "minimum_comparable_worlds cannot exceed max_selected_worlds."
            )

    def to_dict(self) -> dict[str, int | None]:
        return {
            "information_set_search_budget_version": (
                self.information_set_search_budget_version
            ),
            "max_remaining_tricks": self.max_remaining_tricks,
            "max_depth_plies": self.max_depth_plies,
            "max_state_nodes": self.max_state_nodes,
            "max_information_sets": self.max_information_sets,
            "max_selected_worlds": self.max_selected_worlds,
            "max_sampled_worlds": self.max_sampled_worlds,
            "minimum_comparable_worlds": self.minimum_comparable_worlds,
            "wall_clock_timeout_ms": self.wall_clock_timeout_ms,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchRequestV1:
    information_set_search_request_version: int
    search_method: str
    information_view: SearchInformationView
    requested_budget: InformationSetSearchBudgetV1
    world_selection_seed: int
    policy_settings: InformationSetSearchPolicySettingsV1

    def __post_init__(self) -> None:
        validate_information_set_search_request_v1(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_set_search_request_version": (
                self.information_set_search_request_version
            ),
            "search_method": self.search_method,
            "information_view": _serialize_information_view(self.information_view),
            "requested_budget": self.requested_budget.to_dict(),
            "world_selection_seed": self.world_selection_seed,
            "policy_settings": self.policy_settings.to_dict(),
        }


def validate_information_set_search_request_v1(
    request: InformationSetSearchRequestV1,
) -> None:
    if not isinstance(request, InformationSetSearchRequestV1):
        raise ValueError("request must be an InformationSetSearchRequestV1.")
    _require_version(
        request.information_set_search_request_version,
        INFORMATION_SET_SEARCH_REQUEST_VERSION,
        "information-set Search Request version",
    )
    if request.search_method != BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD:
        raise ValueError("Unsupported information-set Search method.")
    if not isinstance(request.information_view, SearchInformationView):
        raise ValueError("information_view must be a SearchInformationView.")
    _validate_information_view_structure(request.information_view)
    if not isinstance(request.requested_budget, InformationSetSearchBudgetV1):
        raise ValueError("requested_budget must be an InformationSetSearchBudgetV1.")
    if isinstance(request.world_selection_seed, bool) or not isinstance(
        request.world_selection_seed, int
    ):
        raise ValueError("world_selection_seed must be an integer, not a boolean.")
    if not isinstance(request.policy_settings, InformationSetSearchPolicySettingsV1):
        raise ValueError(
            "policy_settings must be an InformationSetSearchPolicySettingsV1."
        )


def build_information_set_search_request_v1(
    *,
    information_view: SearchInformationView,
    requested_budget: InformationSetSearchBudgetV1,
    world_selection_seed: int,
    policy_settings: InformationSetSearchPolicySettingsV1,
) -> InformationSetSearchRequestV1:
    return InformationSetSearchRequestV1(
        information_set_search_request_version=INFORMATION_SET_SEARCH_REQUEST_VERSION,
        search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        information_view=information_view,
        requested_budget=requested_budget,
        world_selection_seed=world_selection_seed,
        policy_settings=policy_settings,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetControlledPolicyDecisionV1:
    information_set: Any
    selected_card: str
    reached_world_count: int
    depth_plies: int

    def __post_init__(self) -> None:
        from skat_ai.information_set_search_state import (
            InformationSetSearchObservationV1,
        )

        if not isinstance(self.information_set, InformationSetSearchObservationV1):
            raise ValueError(
                "information_set must be an InformationSetSearchObservationV1."
            )
        if self.information_set.actor_player != "me":
            raise ValueError("Controlled Policy Decisions must belong to me.")
        if self.selected_card not in self.information_set.legal_cards:
            raise ValueError("selected_card must be legal in its Information Set.")
        _require_positive_integer(self.reached_world_count, "reached_world_count")
        _require_non_negative_integer(self.depth_plies, "depth_plies")

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_set": self.information_set.to_dict(),
            "selected_card": self.selected_card,
            "reached_world_count": self.reached_world_count,
            "depth_plies": self.depth_plies,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchConsumedBudgetV1:
    depth_reached: int
    state_nodes_evaluated: int
    information_sets_evaluated: int
    controlled_policy_decisions: int
    fixed_policy_decisions: int
    selected_world_count: int
    completed_world_count: int
    sampled_world_count: int
    unique_sampled_world_count: int
    wall_clock_elapsed_ms: int

    def __post_init__(self) -> None:
        for field_name in (
            "depth_reached",
            "state_nodes_evaluated",
            "information_sets_evaluated",
            "controlled_policy_decisions",
            "fixed_policy_decisions",
            "selected_world_count",
            "completed_world_count",
            "sampled_world_count",
            "unique_sampled_world_count",
            "wall_clock_elapsed_ms",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.information_sets_evaluated > self.state_nodes_evaluated:
            raise ValueError("Information-set count cannot exceed evaluated state nodes.")
        if (
            self.controlled_policy_decisions + self.fixed_policy_decisions
            > self.state_nodes_evaluated
        ):
            raise ValueError("Policy Decisions cannot exceed evaluated state nodes.")
        if self.completed_world_count > self.selected_world_count:
            raise ValueError("Completed worlds cannot exceed selected worlds.")
        if self.sampled_world_count not in {0, self.selected_world_count}:
            raise ValueError("Sampling must cover every selected world or none of them.")
        if self.sampled_world_count == 0 and self.unique_sampled_world_count != 0:
            raise ValueError("Non-sampled Search cannot report unique sampled worlds.")
        if self.sampled_world_count > 0 and not (
            0 < self.unique_sampled_world_count <= self.sampled_world_count
        ):
            raise ValueError("Sampled Search requires a valid unique sampled-world count.")

    def to_dict(self) -> dict[str, int]:
        return {
            "depth_reached": self.depth_reached,
            "state_nodes_evaluated": self.state_nodes_evaluated,
            "information_sets_evaluated": self.information_sets_evaluated,
            "controlled_policy_decisions": self.controlled_policy_decisions,
            "fixed_policy_decisions": self.fixed_policy_decisions,
            "selected_world_count": self.selected_world_count,
            "completed_world_count": self.completed_world_count,
            "sampled_world_count": self.sampled_world_count,
            "unique_sampled_world_count": self.unique_sampled_world_count,
            "wall_clock_elapsed_ms": self.wall_clock_elapsed_ms,
        }


def build_zero_information_set_search_consumed_budget_v1(
) -> InformationSetSearchConsumedBudgetV1:
    return InformationSetSearchConsumedBudgetV1(
        depth_reached=0,
        state_nodes_evaluated=0,
        information_sets_evaluated=0,
        controlled_policy_decisions=0,
        fixed_policy_decisions=0,
        selected_world_count=0,
        completed_world_count=0,
        sampled_world_count=0,
        unique_sampled_world_count=0,
        wall_clock_elapsed_ms=0,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchResultV1:
    information_set_search_result_version: int
    analysis_method: str
    search_method: str
    game_type: str
    status: str
    stop_reason: str
    world_coverage: str
    policy_claim: str
    policy_consistency: str
    terminal_utility_version: int
    requested_budget: InformationSetSearchBudgetV1
    consumed_budget: InformationSetSearchConsumedBudgetV1
    compatible_world_count: int | None
    candidate_results: tuple[AggregateSearchCandidateResult, ...]
    recommended_card: str | None
    controlled_policy: tuple[InformationSetControlledPolicyDecisionV1, ...]
    fixed_policy_settings: InformationSetSearchPolicySettingsV1

    def __post_init__(self) -> None:
        self._validate_common()
        self._validate_budget()
        self._validate_coverage()
        self._validate_candidates()
        self._validate_controlled_policy()
        self._validate_status()

    def _validate_common(self) -> None:
        _require_version(
            self.information_set_search_result_version,
            INFORMATION_SET_SEARCH_RESULT_VERSION,
            "information-set Search Result version",
        )
        if self.analysis_method != INFORMATION_SET_SEARCH_ANALYSIS_METHOD:
            raise ValueError("analysis_method must be information_set_search.")
        if self.search_method != BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD:
            raise ValueError("Unsupported information-set Search method.")
        if self.game_type not in GAME_TYPES and not (
            self.status == "unavailable"
            and self.stop_reason == "unsupported_game_type"
            and isinstance(self.game_type, str)
            and self.game_type
        ):
            raise ValueError(f"Invalid information-set Search game type: {self.game_type}")
        if self.status not in INFORMATION_SET_SEARCH_STATUSES:
            raise ValueError(f"Invalid information-set Search status: {self.status}")
        if self.stop_reason not in INFORMATION_SET_SEARCH_STOP_REASONS:
            raise ValueError(f"Invalid information-set Search stop reason: {self.stop_reason}")
        if self.world_coverage not in WORLD_COVERAGE_VALUES:
            raise ValueError(f"Invalid information-set Search coverage: {self.world_coverage}")
        if self.policy_claim not in INFORMATION_SET_SEARCH_POLICY_CLAIMS:
            raise ValueError(f"Invalid information-set Search Policy claim: {self.policy_claim}")
        if self.policy_consistency not in INFORMATION_SET_SEARCH_POLICY_CONSISTENCY_VALUES:
            raise ValueError("Invalid information-set Search Policy consistency value.")
        _require_version(
            self.terminal_utility_version,
            TERMINAL_UTILITY_VERSION,
            "terminal utility version",
        )
        if not isinstance(self.requested_budget, InformationSetSearchBudgetV1):
            raise ValueError("requested_budget must be an InformationSetSearchBudgetV1.")
        if not isinstance(self.consumed_budget, InformationSetSearchConsumedBudgetV1):
            raise ValueError(
                "consumed_budget must be an InformationSetSearchConsumedBudgetV1."
            )
        if self.compatible_world_count is not None:
            _require_non_negative_integer(
                self.compatible_world_count,
                "compatible_world_count",
            )
        if not isinstance(self.candidate_results, tuple):
            raise TypeError("candidate_results must be a tuple.")
        if any(
            not isinstance(item, AggregateSearchCandidateResult)
            for item in self.candidate_results
        ):
            raise ValueError("candidate_results contain an invalid value.")
        if not isinstance(self.controlled_policy, tuple):
            raise TypeError("controlled_policy must be a tuple.")
        if any(
            not isinstance(item, InformationSetControlledPolicyDecisionV1)
            for item in self.controlled_policy
        ):
            raise ValueError("controlled_policy contains an invalid value.")
        if not isinstance(self.fixed_policy_settings, InformationSetSearchPolicySettingsV1):
            raise ValueError("fixed_policy_settings contain an invalid value.")

    def _validate_budget(self) -> None:
        consumed = self.consumed_budget
        requested = self.requested_budget
        if consumed.depth_reached > requested.max_depth_plies:
            raise ValueError("Consumed depth exceeds the requested budget.")
        if consumed.state_nodes_evaluated > requested.max_state_nodes:
            raise ValueError("Consumed state nodes exceed the requested budget.")
        if consumed.information_sets_evaluated > requested.max_information_sets:
            raise ValueError("Consumed Information Sets exceed the requested budget.")
        if consumed.selected_world_count > requested.max_selected_worlds:
            raise ValueError("Selected worlds exceed the requested budget.")
        if consumed.sampled_world_count > requested.max_sampled_worlds:
            raise ValueError("Sampled worlds exceed the requested budget.")

    def _validate_coverage(self) -> None:
        consumed = self.consumed_budget
        if self.world_coverage == "none":
            if any(
                (
                    consumed.selected_world_count,
                    consumed.completed_world_count,
                    consumed.sampled_world_count,
                    consumed.unique_sampled_world_count,
                )
            ):
                raise ValueError("World coverage none cannot retain world counts.")
            return
        if self.world_coverage not in {
            "all_compatible_worlds",
            "sampled_compatible_worlds",
        }:
            raise ValueError("Information-set Search requires Compatible-world coverage.")
        if self.compatible_world_count is None or self.compatible_world_count <= 0:
            raise ValueError("Available coverage requires a positive Compatible-world count.")
        if self.world_coverage == "all_compatible_worlds":
            if consumed.selected_world_count != self.compatible_world_count:
                raise ValueError("All-compatible coverage must select every world.")
            if consumed.sampled_world_count or consumed.unique_sampled_world_count:
                raise ValueError("All-compatible coverage is not sampled coverage.")
        else:
            if consumed.selected_world_count == 0:
                raise ValueError("Sampled coverage requires selected worlds.")
            if consumed.sampled_world_count != consumed.selected_world_count:
                raise ValueError("Every sampled draw must remain selected.")
            if consumed.unique_sampled_world_count > self.compatible_world_count:
                raise ValueError("Unique sampled worlds exceed Compatible Worlds.")

    def _validate_candidates(self) -> None:
        if (
            self.candidate_results
            and self.consumed_budget.completed_world_count
            < self.requested_budget.minimum_comparable_worlds
        ):
            raise ValueError(
                "Candidate Results require the requested minimum comparable worlds."
            )
        cards = tuple(item.card for item in self.candidate_results)
        if len(cards) != len(set(cards)):
            raise ValueError("Candidate Cards must be unique.")
        if self.candidate_results:
            recommend = self.status == "complete"
            expected = rank_search_candidate_results(
                self.candidate_results,
                self.game_type,
                recommend=recommend,
            )
            if expected != self.candidate_results:
                raise ValueError(
                    "Candidate Results do not use existing deterministic ranking."
                )
        for candidate in self.candidate_results:
            if candidate.completed_world_count != self.consumed_budget.completed_world_count:
                raise ValueError("Candidate Results must share the completed-world prefix.")
            if self.game_type == "null":
                if candidate.mean_local_side_card_point_margin is not None:
                    raise ValueError("Null Candidates cannot contain a card-point margin.")
            elif (
                candidate.completed_world_count > 0
                and candidate.mean_local_side_card_point_margin is None
            ):
                raise ValueError("Suit and Grand Candidates require a card-point margin.")
        marked = tuple(item for item in self.candidate_results if item.is_recommended)
        if self.recommended_card is None:
            if marked:
                raise ValueError("No Candidate may be recommended without recommended_card.")
        elif (
            len(marked) != 1
            or marked[0].rank != 1
            or marked[0].card != self.recommended_card
        ):
            raise ValueError("recommended_card must identify the marked rank-1 Candidate.")

    def _validate_controlled_policy(self) -> None:
        selected_by_information_set: dict[Any, str] = {}
        declaration_context: tuple[GameDeclaration, str, str] | None = None
        for decision in self.controlled_policy:
            if decision.information_set in selected_by_information_set:
                if (
                    selected_by_information_set[decision.information_set]
                    != decision.selected_card
                ):
                    raise ValueError(
                        "Equal Information Sets cannot select different Cards."
                    )
                raise ValueError("A controlled Policy cannot repeat an Information Set.")
            selected_by_information_set[decision.information_set] = (
                decision.selected_card
            )
            if decision.depth_plies > self.consumed_budget.depth_reached:
                raise ValueError("Controlled Policy depth exceeds consumed depth.")
            if decision.reached_world_count > self.consumed_budget.selected_world_count:
                raise ValueError("Controlled Policy world count exceeds selected worlds.")
            if decision.information_set.game_type != self.game_type:
                raise ValueError("Controlled Policy game type differs from the Result.")
            decision_context = (
                decision.information_set.declaration,
                decision.information_set.declarer_player,
                decision.information_set.information_cutoff,
            )
            if declaration_context is None:
                declaration_context = decision_context
            elif decision_context != declaration_context:
                raise ValueError(
                    "Controlled Policy Information Sets must share one game context."
                )
        if len(self.controlled_policy) > self.consumed_budget.controlled_policy_decisions:
            raise ValueError("Retained Policy Decisions exceed consumed decisions.")
        if len(selected_by_information_set) > self.consumed_budget.information_sets_evaluated:
            raise ValueError("Retained Information Sets exceed consumed Information Sets.")
        root_decisions = tuple(
            decision for decision in self.controlled_policy if decision.depth_plies == 0
        )
        if len(root_decisions) > 1:
            raise ValueError("A controlled Policy cannot retain multiple root Decisions.")
        if root_decisions and (
            root_decisions[0].reached_world_count
            != self.consumed_budget.selected_world_count
        ):
            raise ValueError(
                "A controlled root Decision must reach every selected world."
            )
        if self.policy_consistency == "controlled_player_information_set_consistent" and (
            len(self.controlled_policy)
            != self.consumed_budget.controlled_policy_decisions
            or len(self.controlled_policy)
            != self.consumed_budget.information_sets_evaluated
        ):
            raise ValueError(
                "A consistent controlled Policy must retain every evaluated Information Set."
            )
        if declaration_context is not None:
            declarer_player = declaration_context[1]
            for setting in self.fixed_policy_settings.fixed_player_policies:
                if setting.player == declarer_player and (
                    setting.lead_policy in _DEFENDER_ONLY_POLICY_NAMES
                    or setting.response_policy in _DEFENDER_ONLY_POLICY_NAMES
                ):
                    raise ValueError(
                        "A Declarer cannot use a Defender-only fixed Policy."
                    )

    def _validate_status(self) -> None:
        consumed = self.consumed_budget
        if self.status == "complete":
            if self.stop_reason != "completed":
                raise ValueError("Complete Search requires stop reason completed.")
            if self.policy_claim != "exact_selected_world_policy":
                raise ValueError("Complete Search requires an exact selected-world Policy.")
            if self.policy_consistency != "controlled_player_information_set_consistent":
                raise ValueError("Complete Search requires controlled Policy consistency.")
            if (
                consumed.selected_world_count == 0
                or consumed.completed_world_count != consumed.selected_world_count
            ):
                raise ValueError("Complete Search must complete every selected world.")
            if not self.candidate_results or self.recommended_card is None:
                raise ValueError("Complete Search requires Candidates and a recommendation.")
            if not self.controlled_policy:
                raise ValueError("Complete Search requires one controlled Policy.")
            root_decisions = tuple(
                decision
                for decision in self.controlled_policy
                if decision.depth_plies == 0
            )
            if (
                len(root_decisions) != 1
                or root_decisions[0].selected_card != self.recommended_card
            ):
                raise ValueError(
                    "The complete recommendation must match one full-coverage "
                    "depth-zero Policy Decision."
                )
            return
        if self.status == "partial":
            if self.stop_reason not in _STRUCTURAL_STOP_REASONS:
                raise ValueError("Partial Search requires structural budget exhaustion.")
            exhausted = {
                "depth_budget_exhausted": (
                    consumed.depth_reached,
                    self.requested_budget.max_depth_plies,
                ),
                "state_node_budget_exhausted": (
                    consumed.state_nodes_evaluated,
                    self.requested_budget.max_state_nodes,
                ),
                "information_set_budget_exhausted": (
                    consumed.information_sets_evaluated,
                    self.requested_budget.max_information_sets,
                ),
            }
            if exhausted[self.stop_reason][0] != exhausted[self.stop_reason][1]:
                raise ValueError(
                    "A structural stop reason must match its consumed budget limit."
                )
            if self.policy_claim != "common_policy_prefix":
                raise ValueError("Partial Search requires a common-Policy-prefix claim.")
            if self.policy_consistency != "controlled_player_information_set_consistent":
                raise ValueError("Partial Search requires controlled Policy consistency.")
            if self.recommended_card is not None:
                raise ValueError("Partial Search cannot recommend a Card in version 1.")
        elif self.status == "timeout":
            if self.stop_reason != "wall_clock_timeout":
                raise ValueError("Timeout Search requires wall_clock_timeout.")
            if self.requested_budget.wall_clock_timeout_ms is None:
                raise ValueError("Timeout Search requires a requested wall-clock cutoff.")
            if self.policy_claim != "none" or self.policy_consistency != "not_assessed":
                raise ValueError("Timeout Search cannot retain a Policy claim.")
            if self.controlled_policy or self.recommended_card is not None:
                raise ValueError("Timeout Search cannot retain a Policy or recommendation.")
        else:
            if self.stop_reason not in INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS:
                raise ValueError("Unavailable Search requires a canonical unavailable reason.")
            if (
                self.world_coverage != "none"
                or self.policy_claim != "none"
                or self.policy_consistency != "not_assessed"
            ):
                raise ValueError("Unavailable Search has no coverage or Policy claim.")
            if self.candidate_results or self.controlled_policy:
                raise ValueError("Unavailable Search cannot retain Candidates or a Policy.")
            if self.recommended_card is not None:
                raise ValueError("Unavailable Search cannot recommend a Card.")
            if any(self.consumed_budget.to_dict().values()):
                raise ValueError("Unavailable Search must consume a zero budget.")
            if (
                self.stop_reason == "incompatible_world_space"
                and self.compatible_world_count != 0
            ):
                raise ValueError("Incompatible world space requires zero Compatible Worlds.")
            return
        if self.world_coverage == "none":
            raise ValueError("Available Search requires Compatible-world coverage.")
        if (
            consumed.selected_world_count == 0
            or consumed.completed_world_count >= consumed.selected_world_count
        ):
            raise ValueError("Incomplete Search requires a strict selected-world prefix.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_set_search_result_version": (
                self.information_set_search_result_version
            ),
            "analysis_method": self.analysis_method,
            "search_method": self.search_method,
            "game_type": self.game_type,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "world_coverage": self.world_coverage,
            "policy_claim": self.policy_claim,
            "policy_consistency": self.policy_consistency,
            "terminal_utility_version": self.terminal_utility_version,
            "requested_budget": self.requested_budget.to_dict(),
            "consumed_budget": self.consumed_budget.to_dict(),
            "compatible_world_count": self.compatible_world_count,
            "candidate_results": [
                _serialize_candidate(candidate) for candidate in self.candidate_results
            ],
            "recommended_card": self.recommended_card,
            "controlled_policy": [item.to_dict() for item in self.controlled_policy],
            "fixed_policy_settings": self.fixed_policy_settings.to_dict(),
        }


def build_unavailable_information_set_search_result_v1(
    *,
    request: InformationSetSearchRequestV1,
    unavailable_reason: str,
    compatible_world_count: int | None = None,
) -> InformationSetSearchResultV1:
    validate_information_set_search_request_v1(request)
    return InformationSetSearchResultV1(
        information_set_search_result_version=INFORMATION_SET_SEARCH_RESULT_VERSION,
        analysis_method=INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
        search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        game_type=request.information_view.game_type,
        status="unavailable",
        stop_reason=unavailable_reason,
        world_coverage="none",
        policy_claim="none",
        policy_consistency="not_assessed",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=request.requested_budget,
        consumed_budget=build_zero_information_set_search_consumed_budget_v1(),
        compatible_world_count=compatible_world_count,
        candidate_results=(),
        recommended_card=None,
        controlled_policy=(),
        fixed_policy_settings=request.policy_settings,
    )
