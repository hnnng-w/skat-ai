import copy
import json
import random
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

from skatmind.declarer_card_exposure_continuation import (
    build_declarer_card_exposure_continuation,
    build_game_continuation_summary,
    resolve_declarer_card_exposure_continuation,
)
from skatmind.input_loader import build_local_game_state_from_input
from skatmind.input_validation import validate_actual_card_played, validate_position_input
from skatmind.multi_step_simulation import simulate_multiple_steps
from skatmind.policy_comparison import compare_multi_step_policies
from skatmind.public_hand_constraint import PublicHandConstraint
from skatmind.simulation import (
    generate_sampled_hidden_state,
    simulate_immediate_trick_once_detailed,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = PROJECT_ROOT / "examples" / "declarer_card_exposure_continuation.json"
GAME_CONTINUATION_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "game_continuation.schema.json"
CONTINUATION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "declarer_card_exposure_continuation_output.schema.json"
)
PUBLIC_HAND_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "public_hand_constraint.schema.json"
DEFENDER_CONTINUATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "defender_open_play_continuation.schema.json"
)


def build_continuation() -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "declarer_card_exposure",
        "exposure": {"form": "laid_open"},
        "claimed_play_level": "schneider",
        "defender_responses": [
            {"player": "right", "response": "accept", "form": "explicit"},
            {"player": "left", "response": "continue", "form": "explicit"},
        ],
        "public_declarer_cards": ["SA", "C10", "D7"],
    }


def build_local_declarer_position() -> dict[str, object]:
    return {
        "game_type": "grand",
        "player_role": "declarer",
        "declarer_player": "me",
        "hand": ["SA", "C10", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [{} for _ in range(7)],
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 10,
        "analysis_mode": "live_decision",
        "skat_visibility": "known_to_declarer",
        "game_end_reason": "not_ended",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 1,
        "bid_value": 24,
    }


def load_example() -> dict[str, object]:
    with EXAMPLE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_schema(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_focused_schemas_accept_valid_contract_and_outputs() -> None:
    continuation = build_declarer_card_exposure_continuation(build_continuation())
    context = resolve_declarer_card_exposure_continuation(
        build_local_declarer_position(), continuation
    )
    summary = build_game_continuation_summary(context)
    constraint = {
        "player": "me",
        "source": "declarer_card_exposure_continuation",
        "visibility_scope": "all_players",
        "card_count": 3,
        "cards": ["C10", "SA", "D7"],
    }

    defender_schema = load_schema(DEFENDER_CONTINUATION_SCHEMA_PATH)
    registry = Registry().with_resource(
        defender_schema["$id"],
        Resource.from_contents(defender_schema),
    )
    Draft202012Validator(load_schema(GAME_CONTINUATION_SCHEMA_PATH), registry=registry).validate(
        build_continuation()
    )
    Draft202012Validator(load_schema(CONTINUATION_OUTPUT_SCHEMA_PATH)).validate(summary)
    Draft202012Validator(load_schema(PUBLIC_HAND_SCHEMA_PATH)).validate(constraint)

    summary["settlement_applied"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(load_schema(CONTINUATION_OUTPUT_SCHEMA_PATH)).validate(summary)


def test_resolves_separate_continuation_with_canonical_output() -> None:
    value = build_continuation()
    continuation = build_declarer_card_exposure_continuation(value)
    context = resolve_declarer_card_exposure_continuation(
        build_local_declarer_position(),
        continuation,
    )

    assert context.card_reconciliation == "confirmed"
    assert context.public_hand_constraint == PublicHandConstraint(
        player="me",
        cards=("C10", "SA", "D7"),
    )
    assert build_game_continuation_summary(context) == {
        "schema_version": 1,
        "kind": "declarer_card_exposure",
        "rule_sections": ["4.4.4"],
        "declarer_player": "me",
        "exposure_form": "laid_open",
        "shown_to_player": None,
        "defender_responses": [
            {"player": "left", "response": "continue", "form": "explicit"},
            {"player": "right", "response": "accept", "form": "explicit"},
        ],
        "continuing_defenders": ["left"],
        "accepting_defenders": ["right"],
        "unanimous_acceptance": False,
        "continuation_required": True,
        "public_declarer_cards": ["C10", "SA", "D7"],
        "public_declarer_card_count": 3,
        "card_reconciliation": "confirmed",
        "visibility_scope": "all_players",
        "claimed_play_level": "schneider",
        "claimed_play_level_status": ("continuation_required_no_immediate_settlement_effect"),
        "game_end_applied": False,
        "settlement_applied": False,
    }


def test_both_defenders_can_continue_and_input_is_not_mutated() -> None:
    value = build_continuation()
    value["defender_responses"] = [
        {"player": "left", "response": "continue", "form": "explicit"},
        {
            "player": "right",
            "response": "continue",
            "form": "unambiguous_conduct",
        },
    ]
    original = copy.deepcopy(value)

    continuation = build_declarer_card_exposure_continuation(value)

    assert [response.response for response in continuation.defender_responses] == [
        "continue",
        "continue",
    ]
    assert value == original


@pytest.mark.parametrize(
    "cards",
    [
        ["CA"],
        ["CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10"],
    ],
)
def test_public_hand_accepts_one_or_ten_unique_cards(cards: list[str]) -> None:
    value = build_continuation()
    value["public_declarer_cards"] = cards

    continuation = build_declarer_card_exposure_continuation(value)

    assert continuation.public_declarer_cards == tuple(cards)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda value: value.update(
                defender_responses=[
                    {"player": "left", "response": "accept", "form": "explicit"},
                    {"player": "right", "response": "accept", "form": "explicit"},
                ]
            ),
            "game_shortening.kind='declarer_card_exposure'",
        ),
        (
            lambda value: value.update(defender_responses=value["defender_responses"][:1]),
            "exactly two defender responses",
        ),
        (
            lambda value: value.update(defender_responses=[value["defender_responses"][0]] * 2),
            "each defender exactly once",
        ),
        (
            lambda value: value["defender_responses"][0].update(player=" left"),
            "player must be",
        ),
        (
            lambda value: value["defender_responses"][0].update(response="maybe"),
            "response must be",
        ),
        (
            lambda value: value["defender_responses"][0].update(form="implicit"),
            "form must be",
        ),
        (lambda value: value.update(extra=True), "unsupported keys"),
        (lambda value: value.update(public_declarer_cards=[]), "between 1 and 10"),
        (
            lambda value: value.update(public_declarer_cards=["SA", "SA"]),
            "Duplicate cards",
        ),
        (
            lambda value: value.update(public_declarer_cards=["X1"]),
            "Invalid cards",
        ),
    ],
)
def test_rejects_invalid_contract_values(change, message: str) -> None:
    value = build_continuation()
    change(value)

    with pytest.raises(ValueError, match=message):
        build_declarer_card_exposure_continuation(value)


@pytest.mark.parametrize("shown_to_player", ["left", "right"])
def test_shown_to_defender_requires_a_concrete_defender(
    shown_to_player: str,
) -> None:
    value = build_continuation()
    value["exposure"] = {
        "form": "shown_to_defender",
        "shown_to_player": shown_to_player,
    }
    continuation = build_declarer_card_exposure_continuation(value)

    if shown_to_player == "left":
        context = resolve_declarer_card_exposure_continuation(
            build_local_declarer_position(), continuation
        )
        assert context.continuation.exposure.shown_to_player == "left"
    else:
        context = resolve_declarer_card_exposure_continuation(
            build_local_declarer_position(), continuation
        )
        assert context.continuation.exposure.shown_to_player == "right"


def test_showing_to_me_becomes_public_when_me_is_a_defender() -> None:
    data = load_example()
    data["game_continuation"]["exposure"] = {
        "form": "shown_to_defender",
        "shown_to_player": "me",
    }

    validate_position_input(data)
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    context = resolve_declarer_card_exposure_continuation(data, continuation)

    assert context.continuation.exposure.shown_to_player == "me"
    assert context.public_hand_constraint.visibility_scope == "all_players"


def test_rejects_declarer_response_and_declarer_shown_player() -> None:
    value = build_continuation()
    value["defender_responses"][0]["player"] = "me"
    continuation = build_declarer_card_exposure_continuation(value)
    with pytest.raises(ValueError, match="cannot include the declarer"):
        resolve_declarer_card_exposure_continuation(build_local_declarer_position(), continuation)

    value = build_continuation()
    value["exposure"] = {
        "form": "shown_to_defender",
        "shown_to_player": "me",
    }
    continuation = build_declarer_card_exposure_continuation(value)
    with pytest.raises(ValueError, match="not the declarer"):
        resolve_declarer_card_exposure_continuation(build_local_declarer_position(), continuation)


@pytest.mark.parametrize("field", ["current_trick", "played_cards", "skat"])
def test_rejects_public_card_contradicting_reliable_position_field(field: str) -> None:
    position = build_local_declarer_position()
    position[field] = ["SA"]
    continuation = build_declarer_card_exposure_continuation(build_continuation())

    with pytest.raises(ValueError, match=f"reliable {field} evidence"):
        resolve_declarer_card_exposure_continuation(position, continuation)


def test_rejects_public_card_in_completed_trick_or_local_defender_hand() -> None:
    data = load_example()
    data["game_continuation"]["public_declarer_cards"][0] = "CJ"
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    with pytest.raises(ValueError, match="reliable completed_tricks evidence"):
        resolve_declarer_card_exposure_continuation(data, continuation)

    data = load_example()
    data["game_continuation"]["public_declarer_cards"][0] = "CK"
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    with pytest.raises(ValueError, match="reliable defender_hand evidence"):
        resolve_declarer_card_exposure_continuation(data, continuation)


def test_rejects_public_hand_count_or_exact_local_hand_mismatch() -> None:
    continuation_value = build_continuation()
    continuation_value["public_declarer_cards"] = ["SA", "C10"]
    continuation = build_declarer_card_exposure_continuation(continuation_value)
    with pytest.raises(ValueError, match="expected 3 cards, got 2"):
        resolve_declarer_card_exposure_continuation(build_local_declarer_position(), continuation)

    position = build_local_declarer_position()
    position["hand"] = ["SA", "C10", "D8"]
    continuation = build_declarer_card_exposure_continuation(build_continuation())
    with pytest.raises(ValueError, match="exactly match"):
        resolve_declarer_card_exposure_continuation(position, continuation)


def test_null_allows_only_simple_claim_provenance() -> None:
    position = build_local_declarer_position()
    position.update(game_type="null", matadors=None, bid_value=23)
    continuation = build_declarer_card_exposure_continuation(build_continuation())

    with pytest.raises(ValueError, match="claimed_play_level='simple'"):
        resolve_declarer_card_exposure_continuation(position, continuation)


@pytest.mark.parametrize("level", ["simple", "schneider", "schwarz"])
def test_grand_preserves_claimed_level_only_as_provenance(level: str) -> None:
    value = build_continuation()
    value["claimed_play_level"] = level
    continuation = build_declarer_card_exposure_continuation(value)

    context = resolve_declarer_card_exposure_continuation(
        build_local_declarer_position(), continuation
    )
    summary = build_game_continuation_summary(context)

    assert summary["claimed_play_level"] == level
    assert summary["claimed_play_level_status"] == (
        "continuation_required_no_immediate_settlement_effect"
    )
    assert summary["game_end_applied"] is False
    assert summary["settlement_applied"] is False


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "bid_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_null_variants_allow_simple_provenance(
    hand_game: bool,
    ouvert: bool,
    bid_value: int,
) -> None:
    position = build_local_declarer_position()
    position.update(
        game_type="null",
        hand_game=hand_game,
        ouvert=ouvert,
        matadors=None,
        bid_value=bid_value,
    )
    value = build_continuation()
    value["claimed_play_level"] = "simple"
    continuation = build_declarer_card_exposure_continuation(value)

    context = resolve_declarer_card_exposure_continuation(position, continuation)

    assert context.continuation.claimed_play_level == "simple"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("game_shortening", {"kind": "declarer_concession"}),
        ("game_end_reason", "normal_completion"),
        ("impossible_null_settlement", {}),
        ("list_performance_input", {}),
    ],
)
def test_rejects_ending_and_unrelated_workflow_combinations(field: str, value) -> None:
    position = build_local_declarer_position()
    position[field] = value
    continuation = build_declarer_card_exposure_continuation(build_continuation())

    with pytest.raises(ValueError):
        resolve_declarer_card_exposure_continuation(position, continuation)


def test_rejects_missing_concrete_declarer_declaration_and_completed_play() -> None:
    continuation = build_declarer_card_exposure_continuation(build_continuation())
    position = build_local_declarer_position()
    position["declarer_player"] = "unknown"
    with pytest.raises(ValueError, match="concrete declarer_player"):
        resolve_declarer_card_exposure_continuation(position, continuation)

    position = build_local_declarer_position()
    position.update(
        player_role="defender",
        declarer_player="left",
        hand=["C7", "S7", "H7"],
        matadors=None,
    )
    value = build_continuation()
    value["defender_responses"] = [
        {"player": "me", "response": "continue", "form": "explicit"},
        {"player": "right", "response": "accept", "form": "explicit"},
    ]
    continuation_without_declaration = build_declarer_card_exposure_continuation(value)
    with pytest.raises(ValueError, match="final declaration information"):
        resolve_declarer_card_exposure_continuation(position, continuation_without_declaration)

    position = build_local_declarer_position()
    position["completed_tricks"] = [{} for _ in range(10)]
    with pytest.raises(ValueError, match="all ten tricks"):
        resolve_declarer_card_exposure_continuation(position, continuation)


def test_live_example_validates_and_public_opponent_hand_is_not_verifiable() -> None:
    data = load_example()

    validate_position_input(data)
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    context = resolve_declarer_card_exposure_continuation(data, continuation)

    assert context.card_reconciliation == "not_verifiable"
    assert context.public_hand_constraint.player == "left"


def test_flat_post_game_review_keeps_local_actual_card_rules() -> None:
    data = load_example()
    data["analysis_mode"] = "post_game_review"
    data["actual_card_played"] = "C9"

    validate_position_input(data)

    data["actual_card_played"] = "C10"
    with pytest.raises(ValueError, match="must be contained in hand"):
        validate_actual_card_played(data)


def test_local_declarer_actual_card_and_public_hand_are_the_same_exact_set() -> None:
    position = build_local_declarer_position()
    position["analysis_mode"] = "post_game_review"
    position["actual_card_played"] = "C10"
    continuation = build_declarer_card_exposure_continuation(build_continuation())

    validate_actual_card_played(position)
    context = resolve_declarer_card_exposure_continuation(position, continuation)

    assert position["actual_card_played"] in context.public_hand_constraint.cards


def test_hidden_world_assigns_exact_public_declarer_hand_deterministically() -> None:
    data = load_example()
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    constraint = resolve_declarer_card_exposure_continuation(
        data, continuation
    ).public_hand_constraint

    samples = [
        generate_sampled_hidden_state(
            state,
            left_hand_size=6,
            right_hand_size=5,
            random_generator=random.Random(89),
            public_hand_constraints=(constraint,),
        )
        for _ in range(2)
    ]

    assert samples[0] == samples[1]
    assert set(samples[0].left_hand) == set(constraint.cards)
    assert set(samples[0].right_hand).isdisjoint(constraint.cards)
    assert set(samples[0].hypothetical_skat).isdisjoint(constraint.cards)
    assert len(samples[0].right_hand) == 5
    assert len(samples[0].hypothetical_skat) == 2


def test_immediate_analysis_uses_only_exact_public_declarer_cards() -> None:
    data = load_example()
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    constraint = resolve_declarer_card_exposure_continuation(
        data, continuation
    ).public_hand_constraint

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="C9",
        left_hand_size=6,
        right_hand_size=5,
        random_generator=random.Random(89),
        public_hand_constraints=(constraint,),
    )

    assert result["trick"] == ["C8", "C9", "C10"]


def test_multi_step_removes_played_public_cards_without_reintroducing_them() -> None:
    data = load_example()
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    constraint = resolve_declarer_card_exposure_continuation(
        data, continuation
    ).public_hand_constraint

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=6,
        right_hand_size=5,
        step_count=2,
        random_seed=89,
        public_hand_constraints=(constraint,),
        strict_context=True,
    )

    remaining = result["context"].public_hand_constraints[0].cards
    played_public = set(constraint.cards) - set(remaining)
    assert result["steps_simulated"] == 2
    assert "C10" in played_public
    assert played_public.isdisjoint(remaining)
    assert result["context_summary"]["public_hand_constraints"][0]["cards"] == list(remaining)


def test_policy_comparison_uses_same_public_hand_without_new_policies() -> None:
    data = load_example()
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    continuation = build_declarer_card_exposure_continuation(data["game_continuation"])
    constraint = resolve_declarer_card_exposure_continuation(
        data, continuation
    ).public_hand_constraint

    first = compare_multi_step_policies(
        state=state,
        left_hand_size=6,
        right_hand_size=5,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=89,
        public_hand_constraints=(constraint,),
    )
    second = compare_multi_step_policies(
        state=state,
        left_hand_size=6,
        right_hand_size=5,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=89,
        public_hand_constraints=(constraint,),
    )

    assert first == second
    assert first["policies"] == ["first_legal", "lowest_point"]
    for policy_result in first["policy_results"]:
        assert policy_result["context_summary"]["public_hand_constraints"][0]["player"] == "left"
