import copy
import json
import random
from pathlib import Path

import pytest

from main import build_analysis_result, print_analysis_result
from skatmind.deck import get_full_deck
from skatmind.game_declaration import build_game_declaration_from_input
from skatmind.input_loader import build_local_game_state_from_input
from skatmind.input_validation import validate_position_input
from skatmind.multi_step_simulation import simulate_multiple_steps
from skatmind.ouvert_simulation import (
    build_declared_ouvert_public_hand_constraint,
    resolve_effective_public_hand_constraints,
    validate_declared_ouvert_public_cards,
)
from skatmind.policy_comparison import compare_multi_step_policies
from skatmind.public_hand_constraint import PublicHandConstraint
from skatmind.simulation import (
    estimate_immediate_trick_values_for_legal_cards,
    generate_sampled_hidden_state,
)


def build_ouvert_position(declarer_player: str = "left") -> dict[str, object]:
    deck = get_full_deck()
    player_role = "declarer" if declarer_player == "me" else "defender"
    data: dict[str, object] = {
        "game_type": "grand",
        "player_role": player_role,
        "declarer_player": declarer_player,
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": deck[:10],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 5,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "hand_game": True,
        "ouvert": True,
        "schneider_announced": True,
        "schwarz_announced": True,
        "matadors": 1,
        "bid_value": 18,
    }
    if declarer_player != "me":
        data["public_declarer_cards"] = deck[10:20]
    return data


def test_local_ouvert_declarer_derives_and_reconciles_public_hand() -> None:
    data = build_ouvert_position("me")
    validate_position_input(data)

    constraint = build_declared_ouvert_public_hand_constraint(data)

    assert constraint is not None
    assert constraint.player == "me"
    assert constraint.cards == tuple(get_full_deck()[:10])
    assert constraint.source == "declared_ouvert"

    supplied = copy.deepcopy(data)
    supplied["public_declarer_cards"] = list(reversed(data["hand"]))
    validate_position_input(supplied)
    assert build_declared_ouvert_public_hand_constraint(supplied) == constraint

    supplied["public_declarer_cards"] = [*data["hand"][:-1], "D7"]
    with pytest.raises(ValueError, match="exactly match hand"):
        validate_position_input(supplied)


@pytest.mark.parametrize("declarer_player", ["left", "right"])
def test_opponent_ouvert_declarer_requires_complete_exact_hand(
    declarer_player: str,
) -> None:
    data = build_ouvert_position(declarer_player)
    validate_position_input(data)

    constraint = build_declared_ouvert_public_hand_constraint(data)

    assert constraint is not None
    assert constraint.player == declarer_player
    assert constraint.cards == tuple(get_full_deck()[10:20])

    del data["public_declarer_cards"]
    with pytest.raises(ValueError, match="requires public_declarer_cards"):
        validate_position_input(data)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"ouvert": False}, "allowed only when ouvert=true"),
        (
            {"player_role": "unknown", "declarer_player": "unknown"},
            "requires declarer_player",
        ),
        ({"public_declarer_cards": ["invalid"]}, "Invalid cards"),
        (
            {"public_declarer_cards": ["SK"] * 10},
            "Duplicate cards",
        ),
        ({"left_hand_size": 9}, "left_hand_size is 9"),
        ({"played_cards": ["SK"]}, "played_cards"),
        ({"skat": ["SK"]}, "skat"),
    ],
)
def test_flat_ouvert_validation_rejects_invalid_or_contradictory_public_cards(
    change: dict[str, object],
    message: str,
) -> None:
    data = build_ouvert_position("left")
    data.update(change)

    with pytest.raises(ValueError, match=message):
        validate_position_input(data)


def test_flat_ouvert_validation_rejects_current_completed_and_local_card_conflicts() -> None:
    current = build_ouvert_position("left")
    current["current_trick"] = ["SK"]
    current["trick_leader"] = "right"
    with pytest.raises(ValueError, match="current_trick"):
        validate_position_input(current)

    completed = build_ouvert_position("left")
    completed["completed_tricks"] = [{"cards": ["SK", "H7", "D7"]}]
    with pytest.raises(ValueError, match="completed_tricks"):
        validate_declared_ouvert_public_cards(completed)

    local = build_ouvert_position("left")
    local["hand"] = ["SK", *local["hand"][1:]]
    with pytest.raises(ValueError, match="hand"):
        validate_declared_ouvert_public_cards(local)


def test_constraint_resolution_prefers_declared_ouvert_and_rejects_conflicts() -> None:
    cards = ("SA", "S10")
    declared = PublicHandConstraint(
        player="left",
        cards=cards,
        source="declared_ouvert",
    )
    continuation = PublicHandConstraint(
        player="left",
        cards=tuple(reversed(cards)),
        source="declarer_card_exposure_continuation",
    )
    defender = PublicHandConstraint(
        player="right",
        cards=("HA", "H10"),
        source="defender_open_play_continuation",
    )

    assert resolve_effective_public_hand_constraints(
        (continuation, defender, declared)
    ) == (declared, defender)

    with pytest.raises(ValueError, match="Contradictory"):
        resolve_effective_public_hand_constraints(
            (
                declared,
                PublicHandConstraint(
                    player="left",
                    cards=("SA", "S9"),
                    source="declarer_card_exposure_continuation",
                ),
            )
        )
    with pytest.raises(ValueError, match="both left and right"):
        resolve_effective_public_hand_constraints(
            (
                declared,
                PublicHandConstraint(
                    player="right",
                    cards=("SA", "H10"),
                    source="defender_open_play_continuation",
                ),
            )
        )


def test_declared_ouvert_deduplicates_declarer_continuation_and_keeps_provenance(
    tmp_path: Path,
) -> None:
    source = Path("examples/declarer_card_exposure_continuation.json")
    data = json.loads(source.read_text(encoding="utf-8"))
    data.update(
        {
            "hand_game": True,
            "ouvert": True,
            "schneider_announced": True,
            "schwarz_announced": True,
            "public_declarer_cards": data["game_continuation"][
                "public_declarer_cards"
            ],
        }
    )
    path = tmp_path / "ouvert-declarer-continuation.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(str(path), sample_count_override=1)

    assert result["information_policy_summary"]["public_hand_constraints"] == [
        {
            "player": "left",
            "source": "declared_ouvert",
            "visibility_scope": "all_players",
            "card_count": 6,
            "cards": ["C10", "SK", "SJ", "S7", "HK", "DK"],
        }
    ]
    assert result["game_continuation_summary"]["kind"] == "declarer_card_exposure"

    data["public_declarer_cards"] = [
        *data["public_declarer_cards"][:-1],
        "D8",
    ]
    with pytest.raises(ValueError, match="Contradictory"):
        validate_position_input(data)


def test_declared_ouvert_coexists_with_public_defender_continuation(
    tmp_path: Path,
) -> None:
    source = Path("examples/defender_open_play_continuation.json")
    data = json.loads(source.read_text(encoding="utf-8"))
    data.update(
        {
            "ouvert": True,
            "schneider_announced": True,
            "schwarz_announced": True,
        }
    )
    path = tmp_path / "ouvert-defender-continuation.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(str(path), sample_count_override=1)
    public = result["information_policy_summary"]["public_hand_constraints"]

    assert [constraint["player"] for constraint in public] == ["me", "left"]
    assert [constraint["source"] for constraint in public] == [
        "declared_ouvert",
        "defender_open_play_continuation",
    ]
    assert set(public[0]["cards"]).isdisjoint(public[1]["cards"])
    assert result["game_continuation_summary"]["kind"] == "defender_open_play"


def test_hidden_sampling_fixes_opponent_declarer_and_keeps_remainder_uncertain() -> None:
    data = build_ouvert_position("left")
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    constraint = build_declared_ouvert_public_hand_constraint(data)
    assert constraint is not None

    first = generate_sampled_hidden_state(
        state,
        left_hand_size=10,
        right_hand_size=10,
        random_generator=random.Random(42),
        public_hand_constraints=(constraint,),
    )
    second = generate_sampled_hidden_state(
        state,
        left_hand_size=10,
        right_hand_size=10,
        random_generator=random.Random(42),
        public_hand_constraints=(constraint,),
    )
    other_seed = generate_sampled_hidden_state(
        state,
        left_hand_size=10,
        right_hand_size=10,
        random_generator=random.Random(43),
        public_hand_constraints=(constraint,),
    )

    assert first == second
    assert first.left_hand == list(constraint.cards)
    assert len(first.left_hand) == 10
    assert len(first.right_hand) == 10
    assert len(first.hypothetical_skat) == 2
    assert set(first.right_hand).isdisjoint(constraint.cards)
    assert set(first.hypothetical_skat).isdisjoint(constraint.cards)
    assert (first.right_hand, first.hypothetical_skat) != (
        other_seed.right_hand,
        other_seed.hypothetical_skat,
    )


def test_local_declarer_constraint_preserves_hidden_defenders_and_skat() -> None:
    data = build_ouvert_position("me")
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    constraint = build_declared_ouvert_public_hand_constraint(data)
    assert constraint is not None

    sample = generate_sampled_hidden_state(
        state,
        left_hand_size=10,
        right_hand_size=10,
        random_generator=random.Random(42),
        public_hand_constraints=(constraint,),
    )

    assert set(constraint.cards) == set(state.hand)
    assert len(sample.left_hand) == len(sample.right_hand) == 10
    assert len(sample.hypothetical_skat) == 2
    assert set(sample.left_hand).isdisjoint(state.hand)
    assert set(sample.right_hand).isdisjoint(state.hand)


def test_immediate_ouvert_candidates_use_the_same_seeded_world_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = build_ouvert_position("left")
    state = build_local_game_state_from_input(data)
    constraint = build_declared_ouvert_public_hand_constraint(data)
    observed_seeds: list[int | None] = []

    def capture_value(*args, random_seed=None, **kwargs):
        observed_seeds.append(random_seed)
        return {
            "win_rate": 0.5,
            "average_trick_points": 0.0,
            "average_points_won": 0.0,
            "average_points_lost": 0.0,
        }

    monkeypatch.setattr("skatmind.simulation.estimate_immediate_trick_value", capture_value)
    values = estimate_immediate_trick_values_for_legal_cards(
        state,
        left_hand_size=10,
        right_hand_size=10,
        sample_count=1,
        random_seed=42,
        public_hand_constraints=(constraint,),
    )

    assert set(values) == set(state.hand)
    assert observed_seeds == [42] * len(state.hand)


def test_multi_step_and_policy_comparison_shrink_the_same_declared_hand() -> None:
    data = build_ouvert_position("left")
    state = build_local_game_state_from_input(data)
    constraint = build_declared_ouvert_public_hand_constraint(data)
    assert constraint is not None

    result = simulate_multiple_steps(
        state,
        left_hand_size=10,
        right_hand_size=10,
        step_count=1,
        random_seed=42,
        public_hand_constraints=(constraint,),
        strict_context=True,
    )
    remaining = result["context"].public_hand_constraints[0]
    assert remaining.source == "declared_ouvert"
    assert len(remaining.cards) == 9
    assert set(remaining.cards) < set(constraint.cards)

    first = compare_multi_step_policies(
        state,
        left_hand_size=10,
        right_hand_size=10,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=42,
        public_hand_constraints=(constraint,),
    )
    second = compare_multi_step_policies(
        state,
        left_hand_size=10,
        right_hand_size=10,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=42,
        public_hand_constraints=(constraint,),
    )
    assert first == second
    assert first["policies"] == ["first_legal", "lowest_point"]
    assert all(
        row["context_summary"]["public_hand_constraints"][0]["source"]
        == "declared_ouvert"
        for row in first["policy_results"]
    )


def test_flat_analysis_and_post_game_review_emit_only_authorized_public_hand(
    tmp_path: Path,
) -> None:
    data = build_ouvert_position("left")
    data["analysis_mode"] = "post_game_review"
    data["actual_card_played"] = data["hand"][0]
    path = tmp_path / "ouvert-review.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(str(path), sample_count_override=1)
    public = result["information_policy_summary"]["public_hand_constraints"]

    assert result["post_game_review_summary"]["is_available"] is True
    assert public == [
        {
            "player": "left",
            "source": "declared_ouvert",
            "visibility_scope": "all_players",
            "card_count": 10,
            "cards": get_full_deck()[10:20],
        }
    ]
    assert result["position"]["hand"] == data["hand"]
    assert "right_hand" not in result["position"]
    assert result["final_settlement_summary"]["is_complete"] is False


def test_cli_reports_declared_ouvert_simulation_context(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_ouvert_position("left")
    path = tmp_path / "ouvert-cli.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = build_analysis_result(str(path), sample_count_override=1)

    print_analysis_result(result)

    output = capsys.readouterr().out
    assert "Declared Ouvert: yes" in output
    assert "Public declarer: left" in output
    assert "Public declarer cards: 10" in output
    assert "Ouvert-aware simulation: applied" in output
    assert "Recommended card:" in output


def test_public_opponent_ouvert_cards_support_visible_matador_inference() -> None:
    data = build_ouvert_position("left")
    del data["matadors"]

    declaration = build_game_declaration_from_input(data)

    assert declaration.matadors == 1


@pytest.mark.parametrize(
    ("game_type", "hand_game"),
    [("clubs", True), ("grand", True), ("null", False), ("null", True)],
)
def test_all_supported_ouvert_declarations_build_public_constraints(
    game_type: str,
    hand_game: bool,
) -> None:
    data = build_ouvert_position("me")
    data["game_type"] = game_type
    data["hand_game"] = hand_game
    if game_type == "null":
        data["schneider_announced"] = False
        data["schwarz_announced"] = False
        data.pop("matadors")

    validate_position_input(data)

    assert build_declared_ouvert_public_hand_constraint(data) is not None
