import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest

import skat_ai.information_set_search_policy as policy_module
import skat_ai.information_set_search_preparation as preparation_module
import skat_ai.information_set_search_state as state_module
from skat_ai.bounded_search_information import (
    SearchPublicPlay,
    build_historical_search_information_view,
    build_live_search_information_view,
)
from skat_ai.bounded_search_result import (
    AggregateSearchCandidateResult,
    RequestedSearchBudget,
)
from skat_ai.compatible_search_world import (
    build_compatible_search_world_space,
    select_compatible_search_worlds,
)
from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import (
    apply_exact_search_card,
    build_exact_search_state,
    get_exact_search_legal_cards,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    EFFECTIVE_CATEGORY_ORDER,
    get_public_effective_category,
)
from skat_ai.historical_snapshot_adapter import HistoricalSnapshotPosition
from skat_ai.information_set_search_contracts import (
    BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
    INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
    InformationSetControlledPolicyDecisionV1,
    InformationSetFixedPlayerPolicyV1,
    InformationSetSearchBudgetV1,
    InformationSetSearchConsumedBudgetV1,
    InformationSetSearchPolicySettingsV1,
    InformationSetSearchResultV1,
    build_information_set_search_request_v1,
    build_unavailable_information_set_search_result_v1,
)
from skat_ai.information_set_search_policy import (
    select_information_set_fixed_policy_card_v1,
)
from skat_ai.information_set_search_preparation import (
    InformationSetSearchPreparationV1,
    prepare_information_set_search_v1,
)
from skat_ai.information_set_search_state import (
    InformationSetPublicVoidConstraintV1,
    InformationSetSearchObservationV1,
    InformationSetSearchWorldStateV1,
    apply_information_set_search_card_v1,
    build_information_set_search_observation_v1,
    build_information_set_search_world_state_v1,
)
from skat_ai.opponent_policy import determine_current_trick_winner_index
from skat_ai.public_hand_constraint import (
    DECLARER_EXPOSURE_CONTINUATION_SOURCE,
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PublicHandConstraint,
)
from skat_ai.side_ownership import get_player_side
from skat_ai.terminal_utility import TERMINAL_UTILITY_VERSION
from skat_ai.turn_phase import CONCRETE_PLAYERS, UNKNOWN_PLAYER


def _declaration(*, hand_game: bool = False) -> GameDeclaration:
    return GameDeclaration("grand", hand_game=hand_game, matadors=1, bid_value=24)


def _initial_hands() -> dict[str, tuple[str, ...]]:
    deck = tuple(get_full_deck())
    return {
        player: deck[index * 10 : (index + 1) * 10] for index, player in enumerate(CONCRETE_PLAYERS)
    }


def _view_after_plies(
    played_plies: int,
    *,
    declarer_player: str = "me",
    hand_game: bool = False,
    known_out_of_play: bool | None = None,
    public_players: tuple[str, ...] = (),
):
    deck = tuple(get_full_deck())
    declaration = _declaration(hand_game=hand_game)
    exact_state = build_exact_search_state(
        declaration=declaration,
        declarer_player=declarer_player,
        remaining_hands=_initial_hands(),
        current_trick=(),
        next_player="me",
        declarer_trick_points=0,
        defender_trick_points=0,
        declarer_completed_tricks=0,
        defender_completed_tricks=0,
        out_of_play_cards=deck[-2:],
    )
    completed = []
    for _ in range(played_plies):
        transition = apply_exact_search_card(
            exact_state,
            get_exact_search_legal_cards(exact_state)[0],
        )
        exact_state = transition.next_state
        if transition.completed_trick is not None:
            trick = transition.completed_trick
            completed.append(
                {
                    "cards": [play.card for play in trick.plays],
                    "players": [play.player for play in trick.plays],
                    "winner_player": trick.winner_player,
                    "winner_role": trick.winner_side,
                }
            )

    public_constraints = tuple(
        PublicHandConstraint(
            player=player,
            cards=exact_state.hand_for(player),
            source=(
                DECLARER_EXPOSURE_CONTINUATION_SOURCE
                if player == declarer_player
                else DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE
            ),
        )
        for player in public_players
    )
    if known_out_of_play is None:
        known_out_of_play = declarer_player == "me" and not hand_game
    game_state = GameState(
        game_type="grand",
        player_role="declarer" if declarer_player == "me" else "defender",
        declarer_player=declarer_player,
        hand=list(exact_state.hand_for("me")),
        current_trick=[play.card for play in exact_state.current_trick],
        completed_tricks=completed,
        skat=list(exact_state.out_of_play_cards) if known_out_of_play else [],
        trick_leader=(
            exact_state.current_trick[0].player
            if exact_state.current_trick
            else exact_state.next_player
        ),
        next_player=exact_state.next_player,
    )
    view = build_live_search_information_view(
        state=game_state,
        declaration=declaration,
        left_hand_size=len(exact_state.hand_for("left")),
        right_hand_size=len(exact_state.hand_for("right")),
        skat_visibility="known_to_declarer" if known_out_of_play else "unknown",
        public_hand_constraints=public_constraints,
    )
    return view, exact_state


def _find_view(
    *,
    actor: str,
    remaining_tricks: int = 3,
    current_trick_size: int | None = None,
    declarer_player: str = "me",
    hand_game: bool = False,
    public_players: tuple[str, ...] = (),
    known_out_of_play: bool | None = None,
):
    first_play = 30 - 3 * remaining_tricks
    for played_plies in range(first_play, first_play + 3):
        view, exact_state = _view_after_plies(
            played_plies,
            declarer_player=declarer_player,
            hand_game=hand_game,
            public_players=public_players,
            known_out_of_play=known_out_of_play,
        )
        if exact_state.next_player == actor and (
            current_trick_size is None or len(exact_state.current_trick) == current_trick_size
        ):
            return view, exact_state
    raise AssertionError("The deterministic fixture did not reach the requested actor.")


def _fixed_policy(
    player: str,
    *,
    lead_policy: str = "lowest_point",
    response_policy: str = "basic_trick_play",
) -> InformationSetFixedPlayerPolicyV1:
    return InformationSetFixedPlayerPolicyV1(
        player=player,
        lead_policy=lead_policy,
        response_policy=response_policy,
        tie_policy="first_canonical_preferred_card",
    )


def _settings(
    *,
    left_lead: str = "lowest_point",
    left_response: str = "basic_trick_play",
    right_lead: str = "lowest_point",
    right_response: str = "basic_trick_play",
) -> InformationSetSearchPolicySettingsV1:
    return InformationSetSearchPolicySettingsV1(
        information_set_search_policy_settings_version=1,
        controlled_player="me",
        control_scope="root_perspective_only",
        fixed_player_policies=(
            _fixed_policy(
                "left",
                lead_policy=left_lead,
                response_policy=left_response,
            ),
            _fixed_policy(
                "right",
                lead_policy=right_lead,
                response_policy=right_response,
            ),
        ),
    )


def _budget(
    *,
    max_remaining_tricks: int = 3,
    max_selected_worlds: int = 8,
    max_sampled_worlds: int | None = None,
) -> InformationSetSearchBudgetV1:
    return InformationSetSearchBudgetV1(
        information_set_search_budget_version=1,
        max_remaining_tricks=max_remaining_tricks,
        max_depth_plies=9,
        max_state_nodes=20_000,
        max_information_sets=5_000,
        max_selected_worlds=max_selected_worlds,
        max_sampled_worlds=max_sampled_worlds or max_selected_worlds,
        minimum_comparable_worlds=1,
        wall_clock_timeout_ms=None,
    )


def _request(view, **budget_changes):
    return build_information_set_search_request_v1(
        information_view=view,
        requested_budget=_budget(**budget_changes),
        world_selection_seed=17,
        policy_settings=_settings(),
    )


def _candidate(
    card: str,
    *,
    completed_world_count: int,
    recommended: bool,
    margin: float | None = 2.0,
) -> AggregateSearchCandidateResult:
    return AggregateSearchCandidateResult(
        card=card,
        rank=1,
        is_recommended=recommended,
        completed_world_count=completed_world_count,
        local_contract_success_count=completed_world_count,
        local_contract_success_rate=(1.0 if completed_world_count else None),
        mean_local_side_game_score=(12.0 if completed_world_count else None),
        mean_local_side_card_point_margin=(margin if completed_world_count else None),
    )


def test_world_state_reconciles_exact_public_facts_and_serializes_privately() -> None:
    view, exact_state = _find_view(
        actor="me",
        public_players=("left", "right"),
    )
    world_state = build_information_set_search_world_state_v1(
        information_view=view,
        exact_state=exact_state,
    )

    assert world_state.source == view.source
    assert world_state.information_cutoff == view.information_cutoff
    assert world_state.root_perspective_player == "me"
    assert world_state.root_visible_out_of_play_cards == exact_state.out_of_play_cards
    assert world_state.exact_state is exact_state
    assert world_state.public_completed_tricks == view.completed_tricks
    assert tuple(item.player for item in world_state.public_void_constraints) == (
        "me",
        "left",
        "right",
    )
    assert not hasattr(world_state, "__dict__")
    serialized = world_state.to_dict()
    assert "world_index" not in serialized
    assert "fingerprint" not in serialized
    assert serialized["exact_state"]["hands"]["left"] == list(exact_state.hand_for("left"))
    assert world_state.to_dict() is not serialized
    json.dumps(serialized, allow_nan=False)
    with pytest.raises(FrozenInstanceError):
        world_state.source = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError, match="focused builder"):
        InformationSetSearchWorldStateV1()


@pytest.mark.parametrize(
    "change",
    [
        {"declarer_points": 121},
        {"next_player": "left"},
        {"local_remaining_hand": ()},
        {"known_skat_cards": ()},
    ],
)
def test_world_state_rejects_exact_public_contradictions(change: dict) -> None:
    view, exact_state = _find_view(actor="me")
    with pytest.raises(ValueError):
        build_information_set_search_world_state_v1(
            information_view=replace(view, **change),
            exact_state=exact_state,
        )


def test_world_transition_delegates_once_shrinks_public_hand_and_appends_trick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view, exact_state = _find_view(
        actor="left",
        current_trick_size=1,
        public_players=("me", "left", "right"),
    )
    world_state = build_information_set_search_world_state_v1(
        information_view=view,
        exact_state=exact_state,
    )
    original_serialized = world_state.to_dict()
    original_apply = state_module.apply_exact_search_card
    calls = []

    def counted(state, card):
        calls.append((state, card))
        return original_apply(state, card)

    monkeypatch.setattr(state_module, "apply_exact_search_card", counted)
    card = get_exact_search_legal_cards(exact_state)[0]
    child = apply_information_set_search_card_v1(world_state, card)
    assert len(calls) == 1
    assert world_state.to_dict() == original_serialized
    assert child.exact_state != world_state.exact_state
    parent_public = {item.player: item.cards for item in world_state.public_hand_constraints}
    child_public = {item.player: item.cards for item in child.public_hand_constraints}
    assert child_public["left"] == tuple(held for held in parent_public["left"] if held != card)
    assert len(child.public_completed_tricks) == len(world_state.public_completed_tricks)

    completing_card = get_exact_search_legal_cards(child.exact_state)[0]
    completed = apply_information_set_search_card_v1(child, completing_card)
    assert len(calls) == 2
    assert len(completed.public_completed_tricks) == (len(world_state.public_completed_tricks) + 1)
    exact_completed = original_apply(child.exact_state, completing_card).completed_trick
    assert exact_completed is not None
    retained = completed.public_completed_tricks[-1]
    assert retained.winner_player == exact_completed.winner_player
    assert retained.winner_side == exact_completed.winner_side
    assert retained.trick_points == exact_completed.trick_points
    assert completed.exact_state.current_trick == ()


def test_world_transition_adds_only_public_failure_to_follow_evidence() -> None:
    view, exact_state = _find_view(
        actor="left",
        current_trick_size=1,
        public_players=("left",),
    )
    world_state = build_information_set_search_world_state_v1(
        information_view=view,
        exact_state=exact_state,
    )
    card = get_exact_search_legal_cards(exact_state)[0]
    led_category = get_public_effective_category(
        exact_state.current_trick[0].card,
        exact_state.declaration.game_type,
    )
    played_category = get_public_effective_category(
        card,
        exact_state.declaration.game_type,
    )
    before = next(item for item in world_state.public_void_constraints if item.player == "left")
    child = apply_information_set_search_card_v1(world_state, card)
    after = next(item for item in child.public_void_constraints if item.player == "left")
    expected = set(before.forbidden_effective_categories)
    if played_category != led_category:
        expected.add(led_category)
    assert after.forbidden_effective_categories == tuple(
        category for category in EFFECTIVE_CATEGORY_ORDER if category in expected
    )


def test_world_transition_lead_does_not_add_false_void_evidence() -> None:
    view, exact_state = _view_after_plies(0)
    world_state = build_information_set_search_world_state_v1(
        information_view=view,
        exact_state=exact_state,
    )
    child = apply_information_set_search_card_v1(
        world_state,
        get_exact_search_legal_cards(exact_state)[0],
    )
    assert child.public_void_constraints == world_state.public_void_constraints


def test_actor_observations_include_only_own_private_hand_and_visible_discards() -> None:
    view, exact_state = _find_view(actor="me")
    root = build_information_set_search_world_state_v1(
        information_view=view,
        exact_state=exact_state,
    )
    observation = build_information_set_search_observation_v1(root)
    assert observation.actor_player == observation.next_player == "me"
    assert observation.actor_side == "declarer"
    assert observation.own_remaining_hand == exact_state.hand_for("me")
    assert observation.visible_out_of_play_cards == exact_state.out_of_play_cards
    assert observation.legal_cards == get_exact_search_legal_cards(exact_state)
    assert observation.public_completed_tricks == view.completed_tricks
    assert tuple(item.player for item in observation.remaining_hand_sizes) == (
        "me",
        "left",
        "right",
    )
    serialized = observation.to_dict()
    assert "hands" not in serialized
    assert "exact_state" not in serialized
    assert "world_index" not in serialized
    assert serialized["own_remaining_hand"] == list(exact_state.hand_for("me"))
    json.dumps(serialized, allow_nan=False)
    assert not hasattr(observation, "__dict__")
    with pytest.raises(TypeError, match="focused builder"):
        InformationSetSearchObservationV1()


def test_out_of_play_visibility_is_actor_specific() -> None:
    hand_view, hand_state = _find_view(actor="me", hand_game=True)
    hand_observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=hand_view,
            exact_state=hand_state,
        )
    )
    assert hand_observation.visible_out_of_play_cards == ()

    defender_view, defender_state = _find_view(
        actor="me",
        declarer_player="left",
        known_out_of_play=False,
    )
    defender_observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=defender_view,
            exact_state=defender_state,
        )
    )
    assert defender_observation.actor_side == "defenders"
    assert defender_observation.visible_out_of_play_cards == ()

    declarer_view, declarer_state = _find_view(
        actor="left",
        declarer_player="left",
        known_out_of_play=False,
    )
    declarer_observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=declarer_view,
            exact_state=declarer_state,
        )
    )
    assert declarer_observation.actor_side == "declarer"
    assert declarer_observation.visible_out_of_play_cards == (declarer_state.out_of_play_cards)


def test_hidden_world_ownership_does_not_split_equal_root_information_sets() -> None:
    view, _ = _find_view(actor="me", hand_game=True)
    world_space = build_compatible_search_world_space(view)
    selection = select_compatible_search_worlds(
        world_space=world_space,
        requested_budget=RequestedSearchBudget(
            max_remaining_tricks=3,
            max_depth_plies=9,
            max_nodes=10_000,
            max_selected_worlds=5,
            max_sampled_worlds=5,
            minimum_comparable_worlds=1,
        ),
        random_seed=9,
    )
    assert selection.selected_world_count == 5
    assert len(set(selection.exact_states)) > 1
    observations = tuple(
        build_information_set_search_observation_v1(
            build_information_set_search_world_state_v1(
                information_view=view,
                exact_state=exact_state,
            )
        )
        for exact_state in selection.exact_states
    )
    assert all(observation == observations[0] for observation in observations)
    assert all(observation.visible_out_of_play_cards == () for observation in observations)


def test_hidden_partner_and_skat_ownership_do_not_split_defender_information_sets() -> None:
    view, _ = _find_view(
        actor="me",
        remaining_tricks=2,
        declarer_player="left",
        known_out_of_play=False,
    )
    selection = select_compatible_search_worlds(
        world_space=build_compatible_search_world_space(view),
        requested_budget=RequestedSearchBudget(
            max_remaining_tricks=3,
            max_depth_plies=9,
            max_nodes=10_000,
            max_selected_worlds=5,
            max_sampled_worlds=5,
            minimum_comparable_worlds=1,
        ),
        random_seed=3,
    )
    assert len(set(selection.exact_states)) > 1
    observations = tuple(
        build_information_set_search_observation_v1(
            build_information_set_search_world_state_v1(
                information_view=view,
                exact_state=state,
            )
        )
        for state in selection.exact_states
    )
    assert all(item.actor_side == "defenders" for item in observations)
    assert all(item.visible_out_of_play_cards == () for item in observations)
    assert all(item == observations[0] for item in observations)


def test_visible_discards_and_own_hand_split_information_sets() -> None:
    view, exact_state = _find_view(actor="me", public_players=("left",))
    observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=view,
            exact_state=exact_state,
        )
    )
    values = {field.name: getattr(observation, field.name) for field in fields(observation)}
    different_discards = InformationSetSearchObservationV1._from_validated(
        **(values | {"visible_out_of_play_cards": ("D9", "D8")})
    )
    different_hand = InformationSetSearchObservationV1._from_validated(
        **(values | {"own_remaining_hand": observation.own_remaining_hand[:-1]})
    )
    different_current_trick = InformationSetSearchObservationV1._from_validated(
        **(values | {"current_trick": (SearchPublicPlay(player="left", card="D7"),)})
    )
    different_history = InformationSetSearchObservationV1._from_validated(
        **(values | {"public_completed_tricks": observation.public_completed_tricks[:-1]})
    )
    different_public_hand = InformationSetSearchObservationV1._from_validated(
        **(values | {"public_hand_constraints": ()})
    )
    assert different_discards != observation
    assert different_hand != observation
    assert different_current_trick != observation
    assert different_history != observation
    assert different_public_hand != observation


@pytest.mark.parametrize("actor", ["left", "right"])
def test_world_state_builds_each_fixed_actor_observation(actor: str) -> None:
    view, exact_state = _find_view(actor=actor)
    observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=view,
            exact_state=exact_state,
        )
    )
    assert observation.actor_player == observation.next_player == actor
    assert observation.actor_side == "defenders"
    assert observation.own_remaining_hand == exact_state.hand_for(actor)
    assert observation.visible_out_of_play_cards == ()


def test_public_void_contract_is_strict_canonical_and_deterministic() -> None:
    constraint = InformationSetPublicVoidConstraintV1(
        player="left",
        forbidden_effective_categories=("clubs", "trump"),
    )
    assert constraint.to_dict() == {
        "player": "left",
        "forbidden_effective_categories": ["clubs", "trump"],
    }
    assert not hasattr(constraint, "__dict__")
    for categories in (("trump", "clubs"), ("clubs", "clubs"), ("invalid",)):
        with pytest.raises(ValueError):
            InformationSetPublicVoidConstraintV1(
                player="left",
                forbidden_effective_categories=categories,
            )


def test_fixed_policy_selection_reuses_preference_once_and_public_partner_fact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, source_state = _view_after_plies(23)
    actor = source_state.next_player
    assert actor in {"left", "right"}
    view, exact_state = _view_after_plies(
        23,
        public_players=(actor,),
    )
    observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=view,
            exact_state=exact_state,
        )
    )
    calls = []

    def preferred(**kwargs):
        calls.append(kwargs)
        return list(reversed(observation.legal_cards))

    monkeypatch.setattr(
        policy_module,
        "get_preferred_opponent_cards_by_policy",
        preferred,
    )
    settings_changes = {
        f"{actor}_response": "basic_defender_response",
    }
    selected = select_information_set_fixed_policy_card_v1(
        observation=observation,
        policy_settings=_settings(**settings_changes),
    )
    assert len(calls) == 1
    assert selected == observation.legal_cards[0]
    assert calls[0]["hand"] == list(observation.own_remaining_hand)
    assert calls[0]["current_trick"] == [play.card for play in observation.current_trick]
    winner_index = determine_current_trick_winner_index(
        calls[0]["current_trick"],
        observation.game_type,
    )
    expected_partner_winning = (
        observation.current_trick[winner_index].player != observation.declarer_player
    )
    assert calls[0]["partner_currently_winning"] is expected_partner_winning
    assert calls[0]["partner_index"] == winner_index
    assert "partner_hand" not in calls[0]


def test_rear_hand_defender_response_protects_partner_at_second_trick_index() -> None:
    view, exact_state = _find_view(actor="me")
    base = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=view,
            exact_state=exact_state,
        )
    )
    values = {field.name: getattr(base, field.name) for field in fields(base)}
    observation = InformationSetSearchObservationV1._from_validated(
        **(
            values
            | {
                "actor_player": "right",
                "actor_side": "defenders",
                "own_remaining_hand": ("D10", "DK"),
                "current_trick": (
                    SearchPublicPlay(player="me", card="D7"),
                    SearchPublicPlay(player="left", card="DA"),
                ),
                "next_player": "right",
                "visible_out_of_play_cards": (),
                "legal_cards": ("D10", "DK"),
            }
        )
    )
    selected = select_information_set_fixed_policy_card_v1(
        observation=observation,
        policy_settings=_settings(right_response="basic_defender_response"),
    )
    assert selected == "D10"


def test_fixed_policy_selection_rejects_controlled_and_role_invalid_actors() -> None:
    controlled_view, controlled_state = _find_view(actor="me")
    controlled_observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=controlled_view,
            exact_state=controlled_state,
        )
    )
    with pytest.raises(ValueError, match="controlled"):
        select_information_set_fixed_policy_card_v1(
            observation=controlled_observation,
            policy_settings=_settings(),
        )

    declarer_view, declarer_state = _find_view(
        actor="left",
        declarer_player="left",
        known_out_of_play=False,
    )
    declarer_observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=declarer_view,
            exact_state=declarer_state,
        )
    )
    with pytest.raises(ValueError, match="Defender-only"):
        select_information_set_fixed_policy_card_v1(
            observation=declarer_observation,
            policy_settings=_settings(left_lead="basic_defender_lead"),
        )


def test_preparation_reuses_exact_selection_and_builds_one_equal_root_set() -> None:
    view, exact_state = _find_view(
        actor="me",
        public_players=("left", "right"),
    )
    preparation = prepare_information_set_search_v1(_request(view, max_selected_worlds=1))
    assert preparation.status == "available"
    assert preparation.unavailable_reason is None
    assert preparation.eligibility.eligible is True
    assert preparation.world_selection is not None
    assert preparation.world_selection.selection_method == "exact_enumeration"
    assert preparation.world_selection.selected_world_count == 1
    assert len(preparation.world_states) == 1
    assert preparation.root_information_set is not None
    assert preparation.root_information_set.actor_player == "me"
    assert preparation.root_legal_cards == preparation.world_selection.legal_root_cards
    assert list(preparation.to_dict()) == [field.name for field in fields(preparation)]
    json.dumps(preparation.to_dict(), allow_nan=False)
    assert not hasattr(preparation, "__dict__")
    with pytest.raises(TypeError, match="focused builder"):
        InformationSetSearchPreparationV1()

    historical_state = GameState(
        game_type=view.game_type,
        player_role="declarer",
        declarer_player=view.declarer_player,
        hand=list(view.local_remaining_hand),
        current_trick=[play.card for play in view.current_trick],
        trick_leader=(view.current_trick[0].player if view.current_trick else view.next_player),
        completed_tricks=[
            {
                "cards": [play.card for play in trick.plays],
                "players": [play.player for play in trick.plays],
                "winner_player": trick.winner_player,
                "winner_role": trick.winner_side,
            }
            for trick in view.completed_tricks
        ],
        skat=list(exact_state.out_of_play_cards),
        declarer_points=view.declarer_points,
        defender_points=view.defender_points,
        next_player=view.next_player,
    )
    sizes = {item.player: item.card_count for item in view.remaining_hand_sizes}
    historical_view = build_historical_search_information_view(
        HistoricalSnapshotPosition(
            state=historical_state,
            legal_cards=tuple(get_exact_search_legal_cards(exact_state)),
            left_hand_size=sizes["left"],
            right_hand_size=sizes["right"],
            game_declaration=view.declaration,
            public_hand_constraints=view.public_hand_constraints,
        )
    )
    historical = prepare_information_set_search_v1(_request(historical_view, max_selected_worlds=1))
    assert historical.status == "available"
    assert historical.root_information_set == preparation.root_information_set


@pytest.mark.parametrize("remaining_tricks", [1, 2, 3])
def test_preparation_accepts_one_through_three_unresolved_tricks(
    remaining_tricks: int,
) -> None:
    view, _ = _find_view(actor="me", remaining_tricks=remaining_tricks)
    preparation = prepare_information_set_search_v1(_request(view))
    assert preparation.status == "available"
    assert preparation.eligibility.remaining_tricks == remaining_tricks


def test_sampled_preparation_preserves_order_and_duplicate_draw_weight() -> None:
    view, _ = _find_view(actor="me", remaining_tricks=2)
    duplicate = None
    for seed in range(100):
        request = build_information_set_search_request_v1(
            information_view=view,
            requested_budget=_budget(
                max_selected_worlds=5,
                max_sampled_worlds=5,
            ),
            world_selection_seed=seed,
            policy_settings=_settings(),
        )
        candidate = prepare_information_set_search_v1(request)
        if (
            candidate.status == "available"
            and candidate.world_selection is not None
            and candidate.world_selection.unique_sampled_world_count
            < candidate.world_selection.sampled_world_count
        ):
            duplicate = candidate
            break
    assert duplicate is not None
    assert duplicate.world_selection is not None
    assert duplicate.world_selection.selection_method == "uniform_iid_sampling"
    assert tuple(state.exact_state for state in duplicate.world_states) == (
        duplicate.world_selection.exact_states
    )
    assert len(duplicate.world_states) == 5
    assert len(set(duplicate.world_states)) < len(duplicate.world_states)


def test_preparation_calls_world_build_and_selection_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view, _ = _find_view(actor="me", hand_game=True)
    original_build = preparation_module.build_compatible_search_world_space
    original_select = preparation_module.select_compatible_search_worlds
    calls = {"build": 0, "select": 0, "state": 0, "observation": 0}

    def counted_build(source):
        calls["build"] += 1
        return original_build(source)

    def counted_select(**kwargs):
        calls["select"] += 1
        return original_select(**kwargs)

    original_state = preparation_module.build_information_set_search_world_state_v1
    original_observation = preparation_module.build_information_set_search_observation_v1

    def counted_state(**kwargs):
        calls["state"] += 1
        return original_state(**kwargs)

    def counted_observation(world_state):
        calls["observation"] += 1
        return original_observation(world_state)

    monkeypatch.setattr(
        preparation_module,
        "build_compatible_search_world_space",
        counted_build,
    )
    monkeypatch.setattr(
        preparation_module,
        "select_compatible_search_worlds",
        counted_select,
    )
    monkeypatch.setattr(
        preparation_module,
        "build_information_set_search_world_state_v1",
        counted_state,
    )
    monkeypatch.setattr(
        preparation_module,
        "build_information_set_search_observation_v1",
        counted_observation,
    )
    preparation = prepare_information_set_search_v1(_request(view, max_selected_worlds=4))
    assert preparation.status == "available"
    assert calls == {
        "build": 1,
        "select": 1,
        "state": len(preparation.world_states),
        "observation": len(preparation.world_states),
    }


def test_preparation_reports_bounded_policy_model_and_world_unavailability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    four_trick_view, _ = _find_view(actor="me", remaining_tricks=4)
    four_tricks = prepare_information_set_search_v1(_request(four_trick_view))
    assert four_tricks.status == "unavailable"
    assert four_tricks.unavailable_reason == "remaining_trick_limit_exceeded"

    missing_discards_view, _ = _find_view(
        actor="me",
        known_out_of_play=False,
    )
    missing_discards = prepare_information_set_search_v1(_request(missing_discards_view))
    assert missing_discards.unavailable_reason == "information_set_model_unavailable"

    defender_view, _ = _find_view(
        actor="me",
        declarer_player="left",
        known_out_of_play=False,
    )
    role_invalid_request = build_information_set_search_request_v1(
        information_view=defender_view,
        requested_budget=_budget(),
        world_selection_seed=4,
        policy_settings=_settings(left_lead="basic_defender_lead"),
    )
    role_invalid = prepare_information_set_search_v1(role_invalid_request)
    assert role_invalid.unavailable_reason == "unsupported_fixed_policy"

    impossible_view = replace(
        defender_view,
        hidden_card_constraints=tuple(
            replace(
                item,
                forbidden_effective_categories=EFFECTIVE_CATEGORY_ORDER,
            )
            if item.player == "left"
            else item
            for item in defender_view.hidden_card_constraints
        ),
    )
    incompatible = prepare_information_set_search_v1(_request(impossible_view))
    assert incompatible.unavailable_reason == "incompatible_world_space"
    assert incompatible.world_selection is not None
    assert incompatible.world_selection.available is False
    assert incompatible.world_states == ()

    monkeypatch.setattr(
        preparation_module,
        "build_compatible_search_world_space",
        lambda _view: pytest.fail("ineligible preparation built a world space"),
    )
    assert prepare_information_set_search_v1(_request(four_trick_view)).status == ("unavailable")


def test_observation_field_order_defines_the_information_set_key() -> None:
    view, exact_state = _find_view(actor="me")
    observation = build_information_set_search_observation_v1(
        build_information_set_search_world_state_v1(
            information_view=view,
            exact_state=exact_state,
        )
    )
    assert [field.name for field in fields(observation)] == [
        "information_set_search_observation_version",
        "actor_player",
        "actor_side",
        "declarer_player",
        "declaration",
        "game_type",
        "own_remaining_hand",
        "current_trick",
        "public_completed_tricks",
        "next_player",
        "declarer_points",
        "defender_points",
        "declarer_trick_count",
        "defender_trick_count",
        "remaining_hand_sizes",
        "visible_out_of_play_cards",
        "public_hand_constraints",
        "public_void_constraints",
        "legal_cards",
        "information_cutoff",
    ]
    changed_void = tuple(
        replace(
            item,
            forbidden_effective_categories=("clubs",),
        )
        if item.player == "left" and "clubs" not in item.forbidden_effective_categories
        else item
        for item in observation.public_void_constraints
    )
    if changed_void != observation.public_void_constraints:
        altered = InformationSetSearchObservationV1._from_validated(
            **{
                field.name: (
                    changed_void
                    if field.name == "public_void_constraints"
                    else getattr(observation, field.name)
                )
                for field in fields(observation)
            }
        )
        assert altered != observation
    assert (
        get_player_side(
            observation.actor_player,
            observation.declarer_player,
        )
        == observation.actor_side
    )


def test_complete_partial_timeout_and_unavailable_results_are_strict() -> None:
    view, _ = _find_view(
        actor="me",
        public_players=("left", "right"),
    )
    request = _request(view)
    preparation = prepare_information_set_search_v1(request)
    assert preparation.root_information_set is not None
    information_set = preparation.root_information_set
    selected_card = information_set.legal_cards[0]
    decision = InformationSetControlledPolicyDecisionV1(
        information_set=information_set,
        selected_card=selected_card,
        reached_world_count=1,
        depth_plies=0,
    )
    complete_consumed = InformationSetSearchConsumedBudgetV1(
        depth_reached=1,
        state_nodes_evaluated=4,
        information_sets_evaluated=1,
        controlled_policy_decisions=1,
        fixed_policy_decisions=3,
        selected_world_count=1,
        completed_world_count=1,
        sampled_world_count=0,
        unique_sampled_world_count=0,
        wall_clock_elapsed_ms=2,
    )
    complete = InformationSetSearchResultV1(
        information_set_search_result_version=1,
        analysis_method=INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
        search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        game_type="grand",
        status="complete",
        stop_reason="completed",
        world_coverage="all_compatible_worlds",
        policy_claim="exact_selected_world_policy",
        policy_consistency="controlled_player_information_set_consistent",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=request.requested_budget,
        consumed_budget=complete_consumed,
        compatible_world_count=1,
        candidate_results=(
            _candidate(
                selected_card,
                completed_world_count=1,
                recommended=True,
            ),
        ),
        recommended_card=selected_card,
        controlled_policy=(decision,),
        fixed_policy_settings=request.policy_settings,
    )
    assert complete.recommended_card == selected_card
    assert complete.policy_claim == "exact_selected_world_policy"
    assert list(complete.to_dict()) == [field.name for field in fields(complete)]
    json.dumps(complete.to_dict(), allow_nan=False)

    partial_consumed = InformationSetSearchConsumedBudgetV1(
        depth_reached=1,
        state_nodes_evaluated=request.requested_budget.max_state_nodes,
        information_sets_evaluated=1,
        controlled_policy_decisions=1,
        fixed_policy_decisions=2,
        selected_world_count=2,
        completed_world_count=0,
        sampled_world_count=0,
        unique_sampled_world_count=0,
        wall_clock_elapsed_ms=2,
    )
    partial = InformationSetSearchResultV1(
        information_set_search_result_version=1,
        analysis_method=INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
        search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        game_type="grand",
        status="partial",
        stop_reason="state_node_budget_exhausted",
        world_coverage="all_compatible_worlds",
        policy_claim="common_policy_prefix",
        policy_consistency="controlled_player_information_set_consistent",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=request.requested_budget,
        consumed_budget=partial_consumed,
        compatible_world_count=2,
        candidate_results=(),
        recommended_card=None,
        controlled_policy=(replace(decision, reached_world_count=2),),
        fixed_policy_settings=request.policy_settings,
    )
    assert partial.recommended_card is None
    assert partial.policy_claim == "common_policy_prefix"
    assert partial.candidate_results == ()

    started_unresolved = InformationSetSearchResultV1(
        **{
            field.name: (
                replace(partial.consumed_budget, information_sets_evaluated=2)
                if field.name == "consumed_budget"
                else getattr(partial, field.name)
            )
            for field in fields(partial)
        }
    )
    assert len(started_unresolved.controlled_policy) == 1
    assert started_unresolved.consumed_budget.information_sets_evaluated == 2

    partial_values = {field.name: getattr(partial, field.name) for field in fields(partial)}
    with pytest.raises(ValueError, match="every selected world"):
        InformationSetSearchResultV1(
            **(
                partial_values
                | {
                    "controlled_policy": (
                        replace(
                            partial.controlled_policy[0],
                            reached_world_count=1,
                        ),
                    )
                }
            )
        )

    with pytest.raises(ValueError, match="consumed budget limit"):
        InformationSetSearchResultV1(
            **{
                field.name: (
                    replace(partial.consumed_budget, state_nodes_evaluated=10)
                    if field.name == "consumed_budget"
                    else getattr(partial, field.name)
                )
                for field in fields(partial)
            }
        )

    timeout_budget = replace(request.requested_budget, wall_clock_timeout_ms=5)
    timeout_consumed = InformationSetSearchConsumedBudgetV1(
        depth_reached=1,
        state_nodes_evaluated=4,
        information_sets_evaluated=1,
        controlled_policy_decisions=0,
        fixed_policy_decisions=2,
        selected_world_count=2,
        completed_world_count=0,
        sampled_world_count=2,
        unique_sampled_world_count=2,
        wall_clock_elapsed_ms=5,
    )
    timeout = InformationSetSearchResultV1(
        information_set_search_result_version=1,
        analysis_method=INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
        search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        game_type="grand",
        status="timeout",
        stop_reason="wall_clock_timeout",
        world_coverage="sampled_compatible_worlds",
        policy_claim="none",
        policy_consistency="not_assessed",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=timeout_budget,
        consumed_budget=timeout_consumed,
        compatible_world_count=6,
        candidate_results=(),
        recommended_card=None,
        controlled_policy=(),
        fixed_policy_settings=request.policy_settings,
    )
    assert timeout.policy_claim == "none"
    assert timeout.recommended_card is None

    unavailable = build_unavailable_information_set_search_result_v1(
        request=request,
        unavailable_reason="remaining_trick_limit_exceeded",
    )
    assert unavailable.status == "unavailable"
    assert unavailable.world_coverage == "none"
    assert unavailable.candidate_results == unavailable.controlled_policy == ()
    assert not any(unavailable.consumed_budget.to_dict().values())


def test_result_rejects_strategy_fusion_and_noncomplete_recommendations() -> None:
    view, _ = _find_view(
        actor="me",
        public_players=("left", "right"),
    )
    request = _request(view)
    preparation = prepare_information_set_search_v1(request)
    information_set = preparation.root_information_set
    assert information_set is not None
    assert len(information_set.legal_cards) >= 2
    decisions = tuple(
        InformationSetControlledPolicyDecisionV1(
            information_set=information_set,
            selected_card=card,
            reached_world_count=1,
            depth_plies=0,
        )
        for card in information_set.legal_cards[:2]
    )
    consumed = InformationSetSearchConsumedBudgetV1(
        depth_reached=1,
        state_nodes_evaluated=4,
        information_sets_evaluated=2,
        controlled_policy_decisions=2,
        fixed_policy_decisions=2,
        selected_world_count=1,
        completed_world_count=1,
        sampled_world_count=0,
        unique_sampled_world_count=0,
        wall_clock_elapsed_ms=1,
    )
    common = {
        "information_set_search_result_version": 1,
        "analysis_method": INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
        "search_method": BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        "game_type": "grand",
        "status": "complete",
        "stop_reason": "completed",
        "world_coverage": "all_compatible_worlds",
        "policy_claim": "exact_selected_world_policy",
        "policy_consistency": "controlled_player_information_set_consistent",
        "terminal_utility_version": TERMINAL_UTILITY_VERSION,
        "requested_budget": request.requested_budget,
        "consumed_budget": consumed,
        "compatible_world_count": 1,
        "candidate_results": (
            _candidate(
                information_set.legal_cards[0],
                completed_world_count=1,
                recommended=True,
            ),
        ),
        "recommended_card": information_set.legal_cards[0],
        "controlled_policy": decisions,
        "fixed_policy_settings": request.policy_settings,
    }
    with pytest.raises(ValueError, match="Equal Information Sets"):
        InformationSetSearchResultV1(**common)

    single_consumed = replace(
        consumed,
        information_sets_evaluated=1,
        controlled_policy_decisions=1,
    )
    with pytest.raises(ValueError, match="depth-zero"):
        InformationSetSearchResultV1(
            **(
                common
                | {
                    "consumed_budget": single_consumed,
                    "controlled_policy": (decisions[1],),
                }
            )
        )

    omitted_consumed = replace(
        consumed,
        information_sets_evaluated=2,
    )
    with pytest.raises(ValueError, match="retain every evaluated"):
        InformationSetSearchResultV1(
            **(
                common
                | {
                    "consumed_budget": omitted_consumed,
                    "controlled_policy": (decisions[0],),
                }
            )
        )

    below_requested_minimum = InformationSetSearchResultV1(
        **(
            common
            | {
                "requested_budget": replace(
                    request.requested_budget,
                    minimum_comparable_worlds=2,
                ),
                "consumed_budget": single_consumed,
                "controlled_policy": (decisions[0],),
            }
        )
    )
    assert below_requested_minimum.status == "complete"

    complete_two_worlds = replace(
        single_consumed,
        selected_world_count=2,
        completed_world_count=2,
    )
    with pytest.raises(ValueError, match="every selected world"):
        InformationSetSearchResultV1(
            **(
                common
                | {
                    "consumed_budget": complete_two_worlds,
                    "compatible_world_count": 2,
                    "candidate_results": (
                        _candidate(
                            information_set.legal_cards[0],
                            completed_world_count=2,
                            recommended=True,
                        ),
                    ),
                    "controlled_policy": (decisions[0],),
                }
            )
        )

    observation_values = {
        field.name: getattr(information_set, field.name) for field in fields(information_set)
    }
    changed_declaration = InformationSetSearchObservationV1._from_validated(
        **(observation_values | {"declaration": GameDeclaration("grand", matadors=2, bid_value=24)})
    )
    changed_context_decision = InformationSetControlledPolicyDecisionV1(
        information_set=changed_declaration,
        selected_card=changed_declaration.legal_cards[0],
        reached_world_count=1,
        depth_plies=1,
    )
    with pytest.raises(ValueError, match="one game context"):
        InformationSetSearchResultV1(
            **(
                common
                | {
                    "consumed_budget": replace(
                        consumed,
                        information_sets_evaluated=2,
                    ),
                    "controlled_policy": (decisions[0], changed_context_decision),
                }
            )
        )

    defender_information_set = InformationSetSearchObservationV1._from_validated(
        **(
            observation_values
            | {
                "declarer_player": "left",
                "actor_side": "defenders",
            }
        )
    )
    defender_decision = InformationSetControlledPolicyDecisionV1(
        information_set=defender_information_set,
        selected_card=defender_information_set.legal_cards[0],
        reached_world_count=1,
        depth_plies=0,
    )
    with pytest.raises(ValueError, match="Declarer cannot use"):
        InformationSetSearchResultV1(
            **(
                common
                | {
                    "consumed_budget": single_consumed,
                    "controlled_policy": (defender_decision,),
                    "fixed_policy_settings": _settings(left_lead="basic_defender_lead"),
                }
            )
        )

    with pytest.raises(ValueError):
        InformationSetSearchResultV1(
            **(
                common
                | {
                    "status": "partial",
                    "stop_reason": "depth_budget_exhausted",
                    "policy_claim": "common_policy_prefix",
                    "recommended_card": information_set.legal_cards[0],
                    "controlled_policy": (decisions[0],),
                }
            )
        )


def test_null_result_ranking_has_no_card_point_margin() -> None:
    view, _ = _find_view(actor="me")
    request = _request(view)
    preparation = prepare_information_set_search_v1(request)
    base_information_set = preparation.root_information_set
    assert base_information_set is not None
    observation_values = {
        field.name: getattr(base_information_set, field.name)
        for field in fields(base_information_set)
    }
    information_set = InformationSetSearchObservationV1._from_validated(
        **(
            observation_values
            | {
                "declaration": GameDeclaration("null", bid_value=23),
                "game_type": "null",
            }
        )
    )
    decision = InformationSetControlledPolicyDecisionV1(
        information_set=information_set,
        selected_card=information_set.legal_cards[0],
        reached_world_count=2,
        depth_plies=0,
    )
    consumed = InformationSetSearchConsumedBudgetV1(
        depth_reached=1,
        state_nodes_evaluated=2,
        information_sets_evaluated=1,
        controlled_policy_decisions=1,
        fixed_policy_decisions=1,
        selected_world_count=2,
        completed_world_count=2,
        sampled_world_count=0,
        unique_sampled_world_count=0,
        wall_clock_elapsed_ms=1,
    )
    candidate = _candidate(
        information_set.legal_cards[0],
        completed_world_count=2,
        recommended=True,
        margin=None,
    )
    result = InformationSetSearchResultV1(
        information_set_search_result_version=1,
        analysis_method=INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
        search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
        game_type="null",
        status="complete",
        stop_reason="completed",
        world_coverage="all_compatible_worlds",
        policy_claim="exact_selected_world_policy",
        policy_consistency="controlled_player_information_set_consistent",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=request.requested_budget,
        consumed_budget=consumed,
        compatible_world_count=2,
        candidate_results=(candidate,),
        recommended_card=information_set.legal_cards[0],
        controlled_policy=(decision,),
        fixed_policy_settings=request.policy_settings,
    )
    assert result.candidate_results[0].mean_local_side_card_point_margin is None


def test_unsupported_perspective_is_a_preparation_result_not_request_failure() -> None:
    view, _ = _find_view(actor="me")
    request = _request(
        replace(
            view,
            perspective_player="left",
            local_side=get_player_side("left", view.declarer_player),
            known_skat_cards=(),
        )
    )
    preparation = prepare_information_set_search_v1(request)
    assert preparation.status == "unavailable"
    assert preparation.unavailable_reason == "unsupported_perspective"


def test_malformed_view_is_rejected_before_preparation() -> None:
    view, exact_state = _find_view(actor="me")
    for malformed in (
        replace(view, perspective_player="bogus"),
        replace(view, declarer_player="bogus"),
        replace(view, next_player="bogus"),
    ):
        with pytest.raises(ValueError):
            _request(malformed)

    mutable_public = PublicHandConstraint(
        player="left",
        cards=list(exact_state.hand_for("left")),  # type: ignore[arg-type]
        source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    )
    with pytest.raises(TypeError, match="Public hand Cards"):
        _request(replace(view, public_hand_constraints=(mutable_public,)))

    mutable_hidden = tuple(
        replace(item, exact_cards=list(item.exact_cards))  # type: ignore[arg-type]
        if item.player == "me"
        else item
        for item in view.hidden_card_constraints
    )
    with pytest.raises(TypeError, match="Exact constraint Cards"):
        _request(replace(view, hidden_card_constraints=mutable_hidden))

    private_opponent_constraints = tuple(
        replace(item, exact_cards=exact_state.hand_for("left")) if item.player == "left" else item
        for item in view.hidden_card_constraints
    )
    with pytest.raises(ValueError, match="authorized public hand"):
        _request(replace(view, hidden_card_constraints=private_opponent_constraints))

    defender_view, defender_state = _find_view(
        actor="me",
        declarer_player="left",
        hand_game=True,
    )
    with pytest.raises(ValueError, match="Hand game"):
        _request(
            replace(
                defender_view,
                known_skat_cards=defender_state.out_of_play_cards,
            )
        )


def test_shared_eligibility_reasons_remain_normal_preparation_outcomes() -> None:
    view, _ = _find_view(actor="me")
    unsupported_game = prepare_information_set_search_v1(
        _request(replace(view, game_type="ramsch"))
    )
    assert unsupported_game.unavailable_reason == "unsupported_game_type"
    unsupported_game_result = build_unavailable_information_set_search_result_v1(
        request=unsupported_game.request,
        unavailable_reason="unsupported_game_type",
    )
    assert unsupported_game_result.game_type == "ramsch"
    json.dumps(unsupported_game_result.to_dict(), allow_nan=False)

    local_not_to_act, _ = _find_view(actor="left")
    assert prepare_information_set_search_v1(_request(local_not_to_act)).unavailable_reason == (
        "local_player_not_to_act"
    )

    unsupported_turn = prepare_information_set_search_v1(
        _request(replace(view, next_player=UNKNOWN_PLAYER))
    )
    assert unsupported_turn.unavailable_reason == "unsupported_turn_phase"

    missing_declarer = prepare_information_set_search_v1(
        _request(
            replace(
                view,
                declarer_player=UNKNOWN_PLAYER,
                local_side=None,
                known_skat_cards=(),
            )
        )
    )
    assert missing_declarer.unavailable_reason == "missing_concrete_declarer"

    complete_view, _ = _view_after_plies(30)
    complete = prepare_information_set_search_v1(_request(complete_view))
    assert complete.unavailable_reason == "game_already_complete"

    missing_utility_view = replace(
        view,
        declaration=GameDeclaration("grand", matadors=None, bid_value=24),
    )
    missing_utility = prepare_information_set_search_v1(_request(missing_utility_view))
    assert missing_utility.unavailable_reason == "missing_terminal_utility_inputs"

    no_cards_view = replace(
        view,
        local_remaining_hand=(),
        remaining_hand_sizes=tuple(
            replace(item, card_count=0) if item.player == "me" else item
            for item in view.remaining_hand_sizes
        ),
        hidden_card_constraints=tuple(
            replace(item, exact_cards=()) if item.player == "me" else item
            for item in view.hidden_card_constraints
        ),
    )
    no_cards = prepare_information_set_search_v1(_request(no_cards_view))
    assert no_cards.unavailable_reason == "no_legal_cards"
