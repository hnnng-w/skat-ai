import copy
import json
import random
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

from main import build_analysis_result
from skat_ai.defender_open_play_continuation import (
    build_defender_open_play_continuation,
    build_defender_open_play_continuation_summary,
    resolve_defender_open_play_continuation,
)
from skat_ai.game_continuation import (
    build_game_continuation,
    get_game_continuation_from_input,
    resolve_game_continuation,
)
from skat_ai.input_loader import build_local_game_state_from_input
from skat_ai.input_validation import validate_actual_card_played, validate_position_input
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.simulation import (
    generate_sampled_hidden_state,
    simulate_immediate_trick_once_detailed,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = PROJECT_ROOT / "examples" / "defender_open_play_continuation.json"
INPUT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "defender_open_play_continuation.schema.json"
UNION_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "game_continuation.schema.json"
OUTPUT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "defender_open_play_continuation_output.schema.json"
PUBLIC_HAND_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "public_hand_constraint.schema.json"


def load_example() -> dict[str, object]:
    with EXAMPLE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_schema(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_continuation(
    *,
    exposing_defender: str = "left",
    cards: list[str] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "defender_open_play",
        "exposing_defender": exposing_defender,
        "declarer_response": "request_continued_play",
        "public_exposing_defender_cards": (cards if cards is not None else ["C7", "H8", "D9"]),
    }


def build_position(
    *,
    declarer_player: str = "me",
    exposing_defender: str = "left",
) -> dict[str, object]:
    if exposing_defender == "me":
        declarer_player = "left"
        hand = ["C7", "H8", "D9"]
    else:
        hand = ["DQ", "D8", "D7"]
    return {
        "game_type": "grand",
        "player_role": "declarer" if declarer_player == "me" else "defender",
        "declarer_player": declarer_player,
        "trick_leader": "me",
        "next_player": "me",
        "hand": hand,
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [{} for _ in range(7)],
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 10,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 1,
        "bid_value": 24,
    }


def test_version_one_union_dispatches_both_continuation_kinds() -> None:
    defender = build_game_continuation(build_continuation())
    declarer = build_game_continuation(
        {
            "schema_version": 1,
            "kind": "declarer_card_exposure",
            "exposure": {"form": "laid_open"},
            "claimed_play_level": "simple",
            "defender_responses": [
                {"player": "left", "response": "continue", "form": "explicit"},
                {"player": "right", "response": "accept", "form": "explicit"},
            ],
            "public_declarer_cards": ["CA"],
        }
    )

    assert defender.kind == "defender_open_play"
    assert declarer.kind == "declarer_card_exposure"
    assert get_game_continuation_from_input({"game_continuation": build_continuation()}) == defender
    assert get_game_continuation_from_input({}) is None
    with pytest.raises(ValueError, match="Unsupported game_continuation.kind"):
        build_game_continuation({"schema_version": 1, "kind": "other"})


def test_strict_builder_and_focused_schemas() -> None:
    value = build_continuation()
    continuation = build_defender_open_play_continuation(value)
    context = resolve_defender_open_play_continuation(build_position(), continuation)
    summary = build_defender_open_play_continuation_summary(context)
    input_schema = load_schema(INPUT_SCHEMA_PATH)
    registry = Registry().with_resource(
        input_schema["$id"],
        Resource.from_contents(input_schema),
    )

    Draft202012Validator(input_schema).validate(value)
    Draft202012Validator(load_schema(UNION_SCHEMA_PATH), registry=registry).validate(value)
    Draft202012Validator(load_schema(OUTPUT_SCHEMA_PATH)).validate(summary)
    Draft202012Validator(load_schema(PUBLIC_HAND_SCHEMA_PATH)).validate(
        {
            "player": "left",
            "source": "defender_open_play_continuation",
            "visibility_scope": "all_players",
            "card_count": 3,
            "cards": ["C7", "H8", "D9"],
        }
    )

    for field in value:
        invalid = copy.deepcopy(value)
        del invalid[field]
        with pytest.raises(ValueError, match="missing required keys"):
            build_defender_open_play_continuation(invalid)
    invalid = copy.deepcopy(value)
    invalid["extra"] = True
    with pytest.raises(ValueError, match="unsupported keys"):
        build_defender_open_play_continuation(invalid)
    for version in (0, 2, True):
        invalid = copy.deepcopy(value)
        invalid["schema_version"] = version
        with pytest.raises(ValueError, match="exactly 1"):
            build_defender_open_play_continuation(invalid)
    with pytest.raises(ValidationError):
        invalid = copy.deepcopy(value)
        invalid["declarer_response"] = "accept_adjudication"
        Draft202012Validator(input_schema).validate(invalid)
    assert 'version = "0.8.0"' in (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("declarer", "exposing", "non_exposing"),
    [
        ("left", "me", "right"),
        ("me", "left", "right"),
        ("me", "right", "left"),
    ],
)
def test_requires_concrete_defending_party_and_derives_other_defender(
    declarer: str,
    exposing: str,
    non_exposing: str,
) -> None:
    position = build_position(declarer_player=declarer, exposing_defender=exposing)
    continuation = build_defender_open_play_continuation(
        build_continuation(exposing_defender=exposing)
    )

    context = resolve_defender_open_play_continuation(position, continuation)

    assert context.declarer_player == declarer
    assert context.exposing_defender == exposing
    assert context.non_exposing_defender == non_exposing


@pytest.mark.parametrize("exposing", ["unknown", " left", "", None])
def test_rejects_non_concrete_or_padded_exposing_defender(exposing: object) -> None:
    value = build_continuation()
    value["exposing_defender"] = exposing
    with pytest.raises(ValueError, match="exposing_defender must be"):
        build_defender_open_play_continuation(value)


def test_rejects_missing_or_equal_declarer() -> None:
    continuation = build_defender_open_play_continuation(build_continuation())
    position = build_position()
    position["declarer_player"] = "unknown"
    with pytest.raises(ValueError, match="concrete declarer_player"):
        resolve_defender_open_play_continuation(position, continuation)
    position["declarer_player"] = "left"
    with pytest.raises(ValueError, match="defending party"):
        resolve_defender_open_play_continuation(position, continuation)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ("accept_adjudication", "game_shortening.kind='defender_open_play'"),
        ("continue", "request_continued_play"),
        (None, "request_continued_play"),
    ],
)
def test_only_continued_play_response_is_accepted(response: object, message: str) -> None:
    value = build_continuation()
    value["declarer_response"] = response
    with pytest.raises(ValueError, match=message):
        build_defender_open_play_continuation(value)


@pytest.mark.parametrize(
    "cards",
    [
        ["CA"],
        ["CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10"],
    ],
)
def test_builder_accepts_one_or_ten_valid_unique_cards(cards: list[str]) -> None:
    continuation = build_defender_open_play_continuation(build_continuation(cards=cards))
    assert continuation.public_exposing_defender_cards == tuple(cards)


@pytest.mark.parametrize(
    ("cards", "message"),
    [
        ([], "between 1 and 10"),
        (["CA"] * 11, "between 1 and 10"),
        (["XX"], "Invalid cards"),
        ([1], "Invalid cards"),
        (["CA", "CA"], "Duplicate cards"),
    ],
)
def test_builder_rejects_invalid_card_lists(cards: list[object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_defender_open_play_continuation(build_continuation(cards=cards))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_trick", ["C7"]),
        ("played_cards", ["C7"]),
        ("skat", ["C7"]),
        ("completed_tricks", [{"cards": ["C7"]}] + [{} for _ in range(6)]),
        ("hand", ["C7", "D8", "D7"]),
    ],
)
def test_rejects_cards_contradicting_reliable_position_evidence(
    field: str,
    value: list[object],
) -> None:
    position = build_position()
    position[field] = value
    if field == "current_trick":
        position["next_player"] = "left"
    continuation = build_defender_open_play_continuation(build_continuation())
    with pytest.raises(ValueError, match="contradicts reliable"):
        resolve_defender_open_play_continuation(position, continuation)


def test_local_exposing_hand_is_confirmed_and_must_match_exactly() -> None:
    position = build_position(exposing_defender="me")
    continuation = build_defender_open_play_continuation(build_continuation(exposing_defender="me"))

    context = resolve_defender_open_play_continuation(position, continuation)

    assert context.card_reconciliation == "confirmed"
    assert context.public_hand_constraint == PublicHandConstraint(
        player="me",
        cards=("C7", "H8", "D9"),
        source="defender_open_play_continuation",
    )
    position["hand"] = ["C7", "H8", "D8"]
    with pytest.raises(ValueError, match="exactly match the reliable local hand"):
        resolve_defender_open_play_continuation(position, continuation)


def test_opponent_hand_is_authoritative_but_not_independently_verifiable() -> None:
    context = resolve_defender_open_play_continuation(
        build_position(),
        build_defender_open_play_continuation(build_continuation()),
    )

    assert context.card_reconciliation == "not_verifiable"
    assert context.public_hand_constraint.cards == ("C7", "H8", "D9")


def test_rejects_reliable_hand_size_mismatch_and_accepts_current_trick_contribution() -> None:
    position = build_position()
    position["left_hand_size"] = 2
    continuation = build_defender_open_play_continuation(build_continuation())
    with pytest.raises(ValueError, match="contradicts play history"):
        resolve_defender_open_play_continuation(position, continuation)

    position = build_position()
    position.update(
        trick_leader="me",
        next_player="right",
        current_trick=["DQ", "C7"],
        hand=["D8", "D7"],
        left_hand_size=2,
        right_hand_size=3,
    )
    continuation = build_defender_open_play_continuation(build_continuation(cards=["H8", "D9"]))
    context = resolve_defender_open_play_continuation(position, continuation)
    assert context.public_hand_constraint.cards == ("H8", "D9")


def test_rejects_invalid_turn_phase_and_completed_game() -> None:
    continuation = build_defender_open_play_continuation(build_continuation())
    position = build_position()
    position["next_player"] = "right"
    with pytest.raises(ValueError, match="turn phase is inconsistent"):
        resolve_defender_open_play_continuation(position, continuation)
    position = build_position()
    position["completed_tricks"] = [{} for _ in range(10)]
    with pytest.raises(ValueError, match="all ten tricks"):
        resolve_defender_open_play_continuation(position, continuation)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("analysis_mode", "historical_game", "flat live_decision"),
        ("game_shortening", {}, "cannot be combined"),
        ("game_end_reason", "normal_completion", "ongoing game"),
        ("impossible_null_settlement", {}, "impossible_null_settlement"),
        ("list_performance_input", {}, "list-performance"),
    ],
)
def test_rejects_unrelated_or_completed_workflows(
    field: str,
    value: object,
    message: str,
) -> None:
    position = build_position()
    position[field] = value
    continuation = build_defender_open_play_continuation(build_continuation())
    with pytest.raises(ValueError, match=message):
        resolve_defender_open_play_continuation(position, continuation)


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert"),
    [
        ("clubs", False, False),
        ("grand", False, False),
        ("null", False, False),
        ("null", True, False),
        ("null", False, True),
        ("null", True, True),
    ],
)
def test_preserves_supported_original_declarations(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
) -> None:
    position = build_position()
    position.update(game_type=game_type, hand_game=hand_game, ouvert=ouvert)
    if game_type == "null":
        position["bid_value"] = 23
        position.pop("matadors")
    context = resolve_defender_open_play_continuation(
        position,
        build_defender_open_play_continuation(build_continuation()),
    )
    summary = build_defender_open_play_continuation_summary(context)
    assert "claimed_play_level" not in summary
    assert "mandatory_play_level" not in summary


def test_summary_records_returned_public_hand_and_no_adjudication() -> None:
    context = resolve_game_continuation(
        build_position(),
        build_game_continuation(build_continuation(cards=["D9", "C7", "H8"])),
    )
    summary = build_defender_open_play_continuation_summary(context)

    assert summary == {
        "schema_version": 1,
        "kind": "defender_open_play",
        "rule_sections": ["4.4.5", "4.1.6"],
        "declarer_player": "me",
        "exposing_defender": "left",
        "non_exposing_defender": "right",
        "declarer_response": "request_continued_play",
        "cards_returned_to_hand": True,
        "hand_physically_open": False,
        "visibility_scope": "all_players",
        "public_exposing_defender_cards": ["C7", "H8", "D9"],
        "public_exposing_defender_card_count": 3,
        "card_reconciliation": "not_verifiable",
        "rest_trick_claim": "all_remaining_tricks",
        "rest_trick_claim_status": "not_adjudicated_due_to_continued_play",
        "continued_play_effect": "open_play_consequence_disregarded",
        "continuation_required": True,
        "exact_proof_applied": False,
        "game_end_applied": False,
        "settlement_applied": False,
    }
    for field in (
        "proof",
        "counterexample",
        "successful_line",
        "rest_trick_assignment",
        "winner",
        "settlement_basis",
        "final_settlement",
    ):
        assert field not in summary


def test_exact_rest_trick_solver_is_not_called(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("exact rest-trick solver was called")

    monkeypatch.setattr(
        "skat_ai.defender_open_play.prove_defender_rest_tricks",
        fail_if_called,
    )
    result = build_analysis_result(str(EXAMPLE_PATH), sample_count_override=5)
    assert result["game_continuation_summary"]["exact_proof_applied"] is False


def test_hidden_world_fixes_exact_exposing_hand_and_keeps_other_cards_unknown() -> None:
    data = load_example()
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    continuation = build_defender_open_play_continuation(data["game_continuation"])
    constraint = resolve_defender_open_play_continuation(data, continuation).public_hand_constraint

    first = generate_sampled_hidden_state(
        state,
        left_hand_size=3,
        right_hand_size=3,
        random_generator=random.Random(91),
        public_hand_constraints=(constraint,),
    )
    second = generate_sampled_hidden_state(
        state,
        left_hand_size=3,
        right_hand_size=3,
        random_generator=random.Random(91),
        public_hand_constraints=(constraint,),
    )

    assert first == second
    assert set(first.left_hand) == set(constraint.cards)
    assert len(first.left_hand) == 3
    assert set(first.right_hand).isdisjoint(constraint.cards)
    assert set(first.hypothetical_skat).isdisjoint(constraint.cards)
    assert len(first.right_hand) == 3
    assert len(first.hypothetical_skat) == 2


def test_immediate_multi_step_and_policy_comparison_share_known_hand() -> None:
    data = load_example()
    validate_position_input(data)
    state = build_local_game_state_from_input(data)
    continuation = build_defender_open_play_continuation(data["game_continuation"])
    constraint = resolve_defender_open_play_continuation(data, continuation).public_hand_constraint

    immediate = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="D7",
        left_hand_size=3,
        right_hand_size=3,
        random_generator=random.Random(91),
        public_hand_constraints=(constraint,),
    )
    assert immediate["trick"][1] in constraint.cards

    multi_step = simulate_multiple_steps(
        state=state,
        left_hand_size=3,
        right_hand_size=3,
        step_count=2,
        random_seed=91,
        public_hand_constraints=(constraint,),
        strict_context=True,
    )
    remaining = multi_step["context"].public_hand_constraints[0].cards
    played_known = set(constraint.cards) - set(remaining)
    assert played_known
    assert played_known.isdisjoint(remaining)
    assert multi_step["context_summary"]["public_hand_constraints"][0]["source"] == (
        "defender_open_play_continuation"
    )

    first = compare_multi_step_policies(
        state=state,
        left_hand_size=3,
        right_hand_size=3,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=91,
        public_hand_constraints=(constraint,),
    )
    second = compare_multi_step_policies(
        state=state,
        left_hand_size=3,
        right_hand_size=3,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=91,
        public_hand_constraints=(constraint,),
    )
    assert first == second
    assert first["policies"] == ["first_legal", "lowest_point"]
    for policy_result in first["policy_results"]:
        public = policy_result["context_summary"]["public_hand_constraints"][0]
        assert public["player"] == "left"
        assert public["source"] == "defender_open_play_continuation"


def test_flat_post_game_review_uses_known_state_without_ending_game(
    tmp_path: Path,
) -> None:
    data = load_example()
    data["analysis_mode"] = "post_game_review"
    data["actual_card_played"] = "D7"
    validate_position_input(data)
    validate_actual_card_played(data)
    input_path = tmp_path / "review.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(str(input_path), sample_count_override=5)

    assert result["post_game_review_summary"] is not None
    assert result["adjusted_game_result_summary"]["is_complete"] is False
    assert result["adjusted_game_result_summary"]["winner"] == "undecided"
    assert result["final_settlement_summary"]["is_complete"] is False
    assert result["final_settlement_summary"]["settlement_score"] is None
    assert "game_shortening_summary" not in result


def test_local_exposing_defender_review_card_must_belong_to_public_hand() -> None:
    position = build_position(exposing_defender="me")
    position["analysis_mode"] = "post_game_review"
    position["actual_card_played"] = "C7"
    validate_actual_card_played(position)
    context = resolve_defender_open_play_continuation(
        position,
        build_defender_open_play_continuation(build_continuation(exposing_defender="me")),
    )
    assert position["actual_card_played"] in context.public_hand_constraint.cards

    position["actual_card_played"] = "CA"
    with pytest.raises(ValueError, match="must be contained in hand"):
        validate_actual_card_played(position)
