import copy
import json
from pathlib import Path

import pytest

from skatmind.defender_open_play import (
    DefenderOpenPlayContext,
    adjudicate_defender_open_play,
    build_defender_open_play,
    validate_defender_open_play_context,
)
from skatmind.exact_rest_trick_proof import build_exact_remaining_play_state
from skatmind.exact_search_state import ExactSearchState
from skatmind.final_settlement import build_final_settlement_summary
from skatmind.game_declaration import GameDeclaration
from skatmind.game_result import build_game_result_summary_from_points
from skatmind.game_value import build_game_value_summary
from skatmind.input_validation import validate_position_input
from skatmind.overbid import build_overbid_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_example() -> dict[str, object]:
    with (PROJECT_ROOT / "examples" / "defender_open_play.json").open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)


def test_example_has_complete_bounded_exact_state() -> None:
    data = load_example()

    validate_position_input(data)
    open_play = build_defender_open_play(data["game_shortening"])
    context = validate_defender_open_play_context(data, open_play)

    assert context.remaining_trick_count == 2
    assert context.assigned_card_count == 6
    assert set(context.inferred_out_of_play_cards) == {"HK", "DK"}
    assert context.non_exposing_defender == "right"
    assert isinstance(context.exact_state, ExactSearchState)


@pytest.mark.parametrize("exposing_defender", ["me", "left", "right"])
def test_builder_accepts_every_concrete_exposing_player(exposing_defender: str) -> None:
    value = copy.deepcopy(load_example()["game_shortening"])
    value["exposing_defender"] = exposing_defender

    assert build_defender_open_play(value).exposing_defender == exposing_defender


@pytest.mark.parametrize(
    ("exposing_defender", "declarer_player"),
    [("me", "left"), ("left", "right"), ("right", "left")],
)
def test_context_accepts_every_concrete_exposing_defender(
    exposing_defender: str,
    declarer_player: str,
) -> None:
    with (PROJECT_ROOT / "examples" / "grand_late_game_history_heavy_live.json").open(
        "r", encoding="utf-8"
    ) as file:
        data = json.load(file)
    data["analysis_mode"] = "post_game_review"
    data["skat_visibility"] = "known_post_game"
    data["current_trick"] = []
    data["hand"] = ["D7"]
    data["left_hand_size"] = 1
    data["right_hand_size"] = 1
    data["next_player"] = "left"
    data["skat"] = ["HK", "DK"]
    data["declarer_player"] = declarer_player
    data["player_role"] = "declarer" if declarer_player == "me" else "defender"
    for trick in data["completed_tricks"]:
        trick["winner_role"] = (
            "declarer" if trick["winner_player"] == declarer_player else "defenders"
        )
    data["game_declaration"] = {"matadors": 1, "bid_value": 24}
    data["game_shortening"] = {
        "schema_version": 1,
        "kind": "defender_open_play",
        "exposing_defender": exposing_defender,
        "remaining_hands": {
            "me": ["D7"],
            "left": ["D8"],
            "right": ["D9"],
        },
        "declarer_response": "accept_adjudication",
    }

    validate_position_input(data)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("schema_version", 2, "schema_version"),
        ("schema_version", True, "schema_version"),
        ("exposing_defender", " left", "exposing_defender"),
        ("declarer_response", "continue", "declarer_response"),
        (
            "declarer_response",
            "request_continued_play",
            "game_continuation.kind='defender_open_play'",
        ),
    ],
)
def test_builder_rejects_unsupported_values(field_name: str, value: object, message: str) -> None:
    event = copy.deepcopy(load_example()["game_shortening"])
    event[field_name] = value

    with pytest.raises(ValueError, match=message):
        build_defender_open_play(event)


def test_builder_rejects_duplicate_cards_across_hands() -> None:
    event = copy.deepcopy(load_example()["game_shortening"])
    event["remaining_hands"]["right"][0] = "CK"

    with pytest.raises(ValueError, match="across"):
        build_defender_open_play(event)


def test_context_rejects_declarer_as_exposing_player() -> None:
    data = load_example()
    data["game_shortening"]["exposing_defender"] = "left"
    open_play = build_defender_open_play(data["game_shortening"])

    with pytest.raises(ValueError, match="defending party"):
        validate_defender_open_play_context(data, open_play)


def test_context_rejects_more_than_five_remaining_tricks() -> None:
    data = load_example()
    data["completed_tricks"] = data["completed_tricks"][:4]
    data["game_declaration"]["matadors"] = 2
    open_play = build_defender_open_play(data["game_shortening"])

    with pytest.raises(ValueError, match="at most five"):
        validate_defender_open_play_context(data, open_play)


def test_context_rejects_local_hand_contradiction() -> None:
    data = load_example()
    data["hand"] = ["CK"]
    open_play = build_defender_open_play(data["game_shortening"])

    with pytest.raises(ValueError, match="hand must exactly match"):
        validate_defender_open_play_context(data, open_play)


@pytest.mark.parametrize(
    ("current_trick", "next_player", "left_hand", "right_hand"),
    [
        ([], "left", ["D8"], ["D9"]),
        (["D8"], "right", [], ["D9"]),
        (["D8", "D9"], "me", [], []),
    ],
)
def test_context_accepts_empty_and_incomplete_current_tricks(
    current_trick: list[str],
    next_player: str,
    left_hand: list[str],
    right_hand: list[str],
) -> None:
    with (PROJECT_ROOT / "examples" / "grand_late_game_history_heavy_live.json").open(
        "r", encoding="utf-8"
    ) as file:
        data = json.load(file)
    data["analysis_mode"] = "post_game_review"
    data["skat_visibility"] = "known_post_game"
    data["current_trick"] = current_trick
    data["next_player"] = next_player
    data["skat"] = ["HK", "DK"]
    data["left_hand_size"] = len(left_hand)
    data["right_hand_size"] = len(right_hand)
    data["game_declaration"] = {"matadors": 2, "bid_value": 48}
    data["game_shortening"] = {
        "schema_version": 1,
        "kind": "defender_open_play",
        "exposing_defender": "me",
        "remaining_hands": {
            "me": ["D7"],
            "left": left_hand,
            "right": right_hand,
        },
        "declarer_response": "accept_adjudication",
    }

    validate_position_input(data)
    context = validate_defender_open_play_context(
        data,
        build_defender_open_play(data["game_shortening"]),
    )

    assert context.remaining_trick_count == 1
    assert context.assigned_card_count == 3
    assert len(context.exact_state.current_trick) == len(current_trick)


def adjudicate_one_trick(
    declaration: GameDeclaration,
    *,
    declarer_card: str,
    exposing_card: str,
    partner_card: str,
    declarer_points: int = 0,
    defender_points: int = 0,
    completed_tricks: list[dict[str, object]] | None = None,
):
    event = build_defender_open_play(
        {
            "schema_version": 1,
            "kind": "defender_open_play",
            "exposing_defender": "left",
            "remaining_hands": {
                "me": [declarer_card],
                "left": [exposing_card],
                "right": [partner_card],
            },
            "declarer_response": "accept_adjudication",
        }
    )
    context = DefenderOpenPlayContext(
        declarer_player="me",
        exposing_defender="left",
        non_exposing_defender="right",
        exact_state=build_exact_remaining_play_state(
            game_type=declaration.game_type,
            remaining_hands=event.get_remaining_hands(),
            current_trick_cards=[],
            trick_leader="left",
            next_player="left",
        ),
        remaining_trick_count=1,
        assigned_card_count=3,
        inferred_out_of_play_cards=(),
    )
    game_result = build_game_result_summary_from_points(
        declarer_points,
        defender_points,
    )
    game_value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(game_value, declaration.bid_value)
    adjudication = adjudicate_defender_open_play(
        event,
        context,
        game_result,
        game_value,
        overbid,
        completed_tricks or [],
    )
    settlement = build_final_settlement_summary(
        game_value,
        adjudication.game_result_summary,
        overbid,
        completed_tricks or [],
    )
    return adjudication, settlement


def test_valid_grand_claim_assigns_points_to_defenders() -> None:
    adjudication, settlement = adjudicate_one_trick(
        GameDeclaration("grand", matadors=1),
        declarer_card="C7",
        exposing_card="CJ",
        partner_card="C8",
        declarer_points=50,
        defender_points=50,
        completed_tricks=[{"cards": ["S7", "S8", "S9"], "winner_role": "declarer"}],
    )

    result = adjudication.game_result_summary
    assert result["rest_trick_proof_status"] == "valid"
    assert result["declarer_points"] == 50
    assert result["defender_points"] == 70
    assert result["winner"] == "defenders"
    assert result["achieved_schneider_applied"] is False
    assert settlement["settlement_score"] == -96


def test_invalid_grand_claim_awards_simple_undecided_game() -> None:
    adjudication, settlement = adjudicate_one_trick(
        GameDeclaration("grand", matadors=1),
        declarer_card="CA",
        exposing_card="C7",
        partner_card="C8",
        declarer_points=50,
        defender_points=50,
    )

    result = adjudication.game_result_summary
    assert adjudication.game_shortening_summary["rule_sections"] == ["4.4.5", "4.1.4"]
    assert result["rest_trick_proof_status"] == "invalid"
    assert result["declarer_points"] == 70
    assert result["defender_points"] == 50
    assert result["winner"] == "declarer"
    assert result["achieved_schneider_applied"] is False
    assert result["achieved_schwarz_applied"] is False
    assert settlement["effective_game_value"] == 48
    assert settlement["settlement_score"] == 48


def test_invalid_announced_schneider_awards_only_the_mandatory_level() -> None:
    adjudication, settlement = adjudicate_one_trick(
        GameDeclaration(
            "grand",
            hand_game=True,
            schneider_announced=True,
            matadors=1,
        ),
        declarer_card="CA",
        exposing_card="C7",
        partner_card="C8",
    )

    result = adjudication.game_result_summary
    assert adjudication.game_shortening_summary["rule_sections"] == [
        "4.4.5",
        "4.1.4",
        "4.1.5",
    ]
    assert result["mandatory_level_awarded"] is True
    assert result["mandatory_play_level"] == "schneider"
    assert result["achieved_schneider_applied"] is False
    assert settlement["effective_game_value"] == 120


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
@pytest.mark.parametrize(
    ("declarer_card", "exposing_card", "partner_card", "proof_status"),
    [("C7", "CA", "C8", "valid"), ("CA", "C7", "C8", "invalid")],
)
def test_null_variants_use_fixed_value_and_preserve_rule_assignment(
    hand_game: bool,
    ouvert: bool,
    expected_value: int,
    declarer_card: str,
    exposing_card: str,
    partner_card: str,
    proof_status: str,
) -> None:
    adjudication, settlement = adjudicate_one_trick(
        GameDeclaration("null", hand_game=hand_game, ouvert=ouvert),
        declarer_card=declarer_card,
        exposing_card=exposing_card,
        partner_card=partner_card,
    )

    result = adjudication.game_result_summary
    assert result["rest_trick_proof_status"] == proof_status
    assert result["winner"] == "declarer"
    assert result["rest_tricks_recipient"] == (
        "defenders" if proof_status == "valid" else "declarer"
    )
    assert settlement["declarer_won_by_card_points"] is None
    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_score"] == expected_value


def test_null_prior_declarer_trick_preserves_loss() -> None:
    completed_tricks = [{"cards": ["S7", "S8", "S9"], "winner_role": "declarer"}]
    adjudication, settlement = adjudicate_one_trick(
        GameDeclaration("null"),
        declarer_card="C7",
        exposing_card="CA",
        partner_card="C8",
        completed_tricks=completed_tricks,
    )

    assert adjudication.game_result_summary["winner"] == "defenders"
    assert adjudication.game_shortening_summary["rule_sections"] == ["4.4.5", "4.1.3"]
    assert settlement["settlement_score"] == -46
