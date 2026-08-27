import random

import pytest

import skat_ai.multi_step_simulation as multi_step_module
import skat_ai.opponent_lead as opponent_lead_module
from skat_ai.card_tracking import get_unseen_cards
from skat_ai.coherent_hidden_world import CoherentHiddenWorld
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.opponent_sequence import get_unsupported_turn_phase_reason
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.side_ownership import get_player_side


def _world(
    state: GameState,
    left_hand: tuple[str, ...],
    right_hand: tuple[str, ...],
) -> CoherentHiddenWorld:
    assigned = {*left_hand, *right_hand}
    hypothetical_skat = tuple(
        card for card in get_unseen_cards(state) if card not in assigned
    )
    return CoherentHiddenWorld(left_hand, right_hand, hypothetical_skat)


@pytest.mark.parametrize(
    (
        "trick_leader",
        "current_trick",
        "left_hand",
        "right_hand",
        "expected_players",
        "expected_plays",
    ),
    [
        (
            "me",
            ["SA"],
            ("S7",),
            ("S8",),
            ["me", "left", "right"],
            (("left", "S7"), ("right", "S8")),
        ),
        (
            "me",
            ["SA", "S7"],
            (),
            ("S8",),
            ["me", "left", "right"],
            (("right", "S8"),),
        ),
        (
            "right",
            ["S7", "SA"],
            ("S8",),
            (),
            ["right", "me", "left"],
            (("left", "S8"),),
        ),
    ],
)
def test_former_gap_completes_exact_trick_without_replaying_local_card(
    trick_leader: str,
    current_trick: list[str],
    left_hand: tuple[str, ...],
    right_hand: tuple[str, ...],
    expected_players: list[str],
    expected_plays: tuple[tuple[str, str], ...],
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=[],
        current_trick=current_trick,
        trick_leader=trick_leader,
        next_player=expected_plays[0][0],
    )
    root = _world(state, left_hand, right_hand)

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=len(left_hand),
        right_hand_size=len(right_hand),
        step_count=1,
        random_seed=7,
        initial_hidden_world=root,
        strict_context=True,
    )

    completed = result["final_state"].completed_tricks[-1]
    assert completed == {
        "cards": [*current_trick, *[card for _, card in expected_plays]],
        "players": expected_players,
        "winner_role": "declarer",
        "winner_player": "me",
    }
    assert result["steps_simulated"] == 0
    assert result["stop_reason"] == "Player has no cards left."
    assert result["steps"] == []
    assert result["final_state"].hand == []
    assert result["final_state"].current_trick == []
    assert result["final_state"].trick_leader == "me"
    assert result["context"].simulated_opponent_card_ownership == list(
        expected_plays
    )
    assert result["context"].root_hidden_world is root
    assert root.ownership_transitions == ()
    assert state.current_trick == current_trick
    assert result["stop_reason"] != get_unsupported_turn_phase_reason()


@pytest.mark.parametrize(
    "declaration",
    [
        GameDeclaration("clubs", matadors=1),
        GameDeclaration("grand", matadors=1),
        GameDeclaration("null"),
        GameDeclaration("null", hand_game=True),
        GameDeclaration("null", ouvert=True),
        GameDeclaration("null", hand_game=True, ouvert=True),
    ],
    ids=[
        "suit",
        "grand",
        "null",
        "null-hand",
        "null-ouvert",
        "null-hand-ouvert",
    ],
)
@pytest.mark.parametrize(
    ("player_role", "declarer_player"),
    [("declarer", "me"), ("defender", "left")],
)
def test_terminal_completion_preserves_contract_and_perspective_side_mapping(
    declaration: GameDeclaration,
    player_role: str,
    declarer_player: str,
) -> None:
    state = GameState(
        game_type=declaration.game_type,
        player_role=player_role,
        declarer_player=declarer_player,
        hand=[],
        current_trick=["SA"],
        trick_leader="me",
        next_player="left",
    )
    root = _world(state, ("S7",), ("S8",))

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        game_declaration=declaration,
        initial_hidden_world=root,
    )

    completed = result["final_state"].completed_tricks[-1]
    winner_side = get_player_side(completed["winner_player"], declarer_player)
    assert completed["winner_role"] == winner_side
    assert completed["cards"] == ["SA", "S7", "S8"]
    assert result["steps_simulated"] == 0
    assert result["stop_reason"] == "Player has no cards left."


def test_left_winner_uses_existing_left_led_preparation_before_step_zero() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["C7"],
        current_trick=["S7"],
        trick_leader="me",
        next_player="left",
    )
    root = _world(
        state,
        ("SA", "H7"),
        ("S8", "D7"),
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=11,
        initial_hidden_world=root,
    )

    step = result["steps"][0]
    assert step["step_index"] == 0
    assert step["prepared_state"].hand == ["C7"]
    assert step["prepared_state"].completed_tricks[-1]["winner_player"] == "left"
    assert step["prepared_state"].current_trick == ["H7", "D7"]
    assert step["prepared_state"].next_player == "me"
    assert step["opponent_lead_result"]["leader"] == "left"
    assert result["context"].simulated_opponent_card_ownership == [
        ("left", "SA"),
        ("right", "S8"),
        ("left", "H7"),
        ("right", "D7"),
    ]


@pytest.mark.parametrize(
    "card_selection_policy",
    [
        "first_legal",
        "lowest_point",
        "highest_point",
        "highest_expected_value",
    ],
)
def test_completion_preserves_each_legacy_local_policy_boundary(
    card_selection_policy: str,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["D7"],
        current_trick=["CA"],
        trick_leader="me",
        next_player="left",
    )
    root = _world(
        state,
        ("C7", "H7"),
        ("C8", "S7"),
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=19,
        card_selection_policy=card_selection_policy,
        expected_value_sample_count=2,
        initial_hidden_world=root,
    )

    assert result["steps_simulated"] == 1
    assert result["steps"][0]["step_index"] == 0
    assert result["steps"][0]["candidate_card"] == "D7"
    assert result["steps"][0]["prepared_state"].hand == ["D7"]
    assert result["steps"][0]["prepared_state"].completed_tricks[-1]["cards"] == [
        "CA",
        "C7",
        "C8",
    ]


def test_completion_and_continuation_update_public_constraints_and_voids_once() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["S7"],
        trick_leader="me",
        next_player="left",
    )
    public_constraints = (
        PublicHandConstraint(player="left", cards=("S8", "C7")),
        PublicHandConstraint(player="right", cards=("H7", "D7")),
    )
    root = _world(
        state,
        public_constraints[0].cards,
        public_constraints[1].cards,
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=13,
        public_hand_constraints=public_constraints,
        initial_hidden_world=root,
        strict_context=True,
    )

    step = result["steps"][0]
    assert step["prepared_state"].completed_tricks[-1]["cards"] == [
        "S7",
        "S8",
        "H7",
    ]
    assert step["prepared_state"].current_trick == ["C7", "D7"]
    assert [constraint.cards for constraint in result["context"].public_hand_constraints] == [
        (),
        (),
    ]
    assert step["hidden_card_inference_summary"]["confirmed_voids"] == [
        {
            "player": "right",
            "forbidden_effective_categories": ["clubs", "spades"],
        }
    ]
    assert step["hidden_card_inference_summary"][
        "confirmed_void_evidence_count"
    ] == 2
    assert result["context_summary"]["simulated_opponent_card_count"] == 4
    assert result["context_summary"]["duplicate_simulated_opponent_cards"] == []


def test_completion_passes_exact_partner_currently_winning_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["D7"],
        current_trick=["S7"],
        trick_leader="me",
        next_player="left",
    )
    root = _world(state, ("SA", "H7"), ("S10", "S8"))
    observed_partner_contexts = []
    real_chooser = opponent_lead_module.choose_opponent_response_card_by_policy

    def observed_chooser(**kwargs):
        observed_partner_contexts.append(
            (
                kwargs["partner_currently_winning"],
                kwargs["partner_index"],
            )
        )
        return real_chooser(**kwargs)

    monkeypatch.setattr(
        opponent_lead_module,
        "choose_opponent_response_card_by_policy",
        observed_chooser,
    )

    completion = opponent_lead_module.simulate_opponents_to_complete_current_trick_once(
        state=state,
        completion_players=("left", "right"),
        left_hand_size=2,
        right_hand_size=2,
        random_generator=random.Random(23),
        opponent_response_policy_by_player={
            "left": "basic_defender_response",
            "right": "basic_defender_response",
        },
        coherent_hidden_world=root,
    )

    assert observed_partner_contexts == [(False, 0), (True, 1)]
    assert completion["completed_trick"]["cards"] == ["S7", "SA", "S10"]


def test_terminal_completion_rebuilds_and_validates_new_void_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=[],
        current_trick=["S7"],
        trick_leader="me",
        next_player="left",
    )
    root = _world(state, ("H7",), ("D7",))
    inferred_states = []
    real_builder = multi_step_module.build_hidden_card_inference_model

    def observed_builder(state, *args, **kwargs):
        model = real_builder(state, *args, **kwargs)
        inferred_states.append((state, model))
        return model

    monkeypatch.setattr(
        multi_step_module,
        "build_hidden_card_inference_model",
        observed_builder,
    )
    result = simulate_multiple_steps(
        state=state,
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        initial_hidden_world=root,
        strict_context=True,
    )

    terminal_state, terminal_model = inferred_states[-1]
    assert terminal_state == result["final_state"]
    assert terminal_model is not None
    assert [
        (item.player, item.effective_category)
        for item in terminal_model.constraints.confirmed_void_evidence
    ] == [("left", "spades"), ("right", "spades")]


def test_policy_comparison_has_no_recommendation_without_new_local_decision() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=[],
        current_trick=["SA"],
        trick_leader="me",
        next_player="left",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        policies=["first_legal", "highest_point"],
        random_seed=17,
    )

    assert all(row["steps_simulated"] == 0 for row in result["policy_results"])
    assert all(
        row["stop_reason"] == "Player has no cards left."
        for row in result["policy_results"]
    )
    assert result["recommended_policy"] is None
