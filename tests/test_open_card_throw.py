import json
from pathlib import Path

import pytest

from main import build_analysis_result
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_history import calculate_completed_trick_points_by_side
from skat_ai.game_result import build_game_result_summary_from_points
from skat_ai.game_shortening import build_game_shortening
from skat_ai.game_value import build_game_value_summary
from skat_ai.input_validation import validate_position_input
from skat_ai.open_card_throw import (
    OpenCardThrow,
    adjudicate_open_card_throw,
    resolve_open_card_throw_context,
)
from skat_ai.overbid import build_overbid_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = PROJECT_ROOT / "examples" / "open_card_throw.json"


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def adjudicate(data: dict):
    validate_position_input(data)
    event = build_game_shortening(data["game_shortening"])
    assert isinstance(event, OpenCardThrow)
    context = resolve_open_card_throw_context(data, event)
    declaration = build_game_declaration_from_input(data)
    game_value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(game_value, declaration.bid_value)
    completed_points = calculate_completed_trick_points_by_side(data["completed_tricks"])
    result = build_game_result_summary_from_points(
        data.get("declarer_points", 0) + completed_points["declarer_points"],
        data.get("defender_points", 0) + completed_points["defender_points"],
    )
    outcome = adjudicate_open_card_throw(
        event,
        context,
        result,
        game_value,
        overbid,
        data["completed_tricks"],
    )
    settlement = build_final_settlement_summary(
        game_value,
        outcome.game_result_summary,
        overbid,
        data["completed_tricks"],
    )
    return event, context, outcome, settlement


def build_null_position(*, throwing_player: str, hand_game: bool, ouvert: bool) -> dict:
    local_hand = ["CJ", "SJ", "HJ", "DJ", "CA", "C10", "CK", "CQ", "C9", "C8"]
    left_hand = ["SA", "S10", "SK", "SQ", "S9", "S8", "S7", "HA", "H10", "HK"]
    thrown_cards = local_hand if throwing_player == "me" else left_hand
    return {
        "game_type": "null",
        "player_role": "declarer",
        "player_position": "forehand",
        "declarer_player": "me",
        "trick_leader": "unknown",
        "hand": local_hand,
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "game_declaration": {"hand_game": hand_game, "ouvert": ouvert},
        "game_shortening": {
            "schema_version": 1,
            "kind": "open_card_throw",
            "throwing_player": throwing_player,
            "thrown_cards": thrown_cards,
            "statement_classification": "none",
        },
    }


def test_union_builds_strict_version_one_open_card_throw() -> None:
    event = build_game_shortening(load_example()["game_shortening"])

    assert isinstance(event, OpenCardThrow)
    assert event.schema_version == 1
    assert event.kind == "open_card_throw"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "exactly 1"),
        ("throwing_player", " left", "must be 'me', 'left', or 'right'"),
        ("statement_classification", "free text", "must be 'none'"),
        ("thrown_cards", [], "between 1 and 10"),
        ("thrown_cards", ["C10", "C10"], "Duplicate cards"),
        ("thrown_cards", ["XX"], "Invalid cards"),
    ],
)
def test_structural_invalid_values_are_rejected(field, value, message) -> None:
    value_object = load_example()["game_shortening"]
    value_object[field] = value

    with pytest.raises(ValueError, match=message):
        build_game_shortening(value_object)


def test_unknown_fields_and_specific_trick_assertions_are_rejected() -> None:
    value = load_example()["game_shortening"]
    value["speech"] = "out of Schneider"
    with pytest.raises(ValueError, match="unsupported keys"):
        build_game_shortening(value)

    value = load_example()["game_shortening"]
    value["specific_future_trick_assertion"] = {"trick_count": 1}
    with pytest.raises(ValueError, match="separate classified trick-claim workflow"):
        build_game_shortening(value)


def test_defender_throw_assigns_all_unresolved_tricks_and_points_with_joint_liability() -> None:
    _, context, outcome, settlement = adjudicate(load_example())
    result = outcome.game_result_summary
    summary = outcome.game_shortening_summary

    assert context.throwing_party == "defenders"
    assert context.opposing_party == "declarer"
    assert context.joint_liability is True
    assert context.card_reconciliation == "not_verifiable"
    assert summary["thrown_cards"] == ["C10", "S10"]
    assert summary["decision_state_before_shortening"] == "undecided"
    assert result["rest_trick_assignment"] == {
        "source": "open_card_throw",
        "recipient": "declarer",
        "remaining_trick_count": 2,
        "assigned_card_count": 6,
        "assigned_card_points": 63,
    }
    assert result["observed_trick_counts"] == {"declarer": 8, "defenders": 0}
    assert result["final_trick_counts"] == {"declarer": 10, "defenders": 0}
    assert result["final_points"] == {"declarer": 120, "defenders": 0}
    assert result["winner"] == "declarer"
    assert result["open_throw_schneider_applied"] is True
    assert result["open_throw_schwarz_applied"] is True
    assert result["achieved_schneider_applied"] is False
    assert result["achieved_schwarz_applied"] is False
    assert settlement["effective_game_value"] == 168
    assert settlement["settlement_score"] == 168


@pytest.mark.parametrize(
    ("declarer_player", "player_role", "throwing_player", "party", "joint_liability"),
    [
        ("me", "declarer", "me", "declarer", False),
        ("left", "defender", "left", "declarer", False),
        ("left", "defender", "me", "defenders", True),
        ("me", "declarer", "left", "defenders", True),
        ("left", "defender", "right", "defenders", True),
    ],
)
def test_throwing_player_party_derivation_is_deterministic(
    declarer_player,
    player_role,
    throwing_player,
    party,
    joint_liability,
) -> None:
    data = build_null_position(
        throwing_player=throwing_player,
        hand_game=False,
        ouvert=False,
    )
    data["declarer_player"] = declarer_player
    data["player_role"] = player_role

    _, context, _, _ = adjudicate(data)

    assert context.throwing_party == party
    assert context.opposing_party != party
    assert context.joint_liability is joint_liability


def test_declarer_throw_keeps_only_observed_state_and_loses_unresolved_game() -> None:
    data = load_example()
    data["game_shortening"].update(
        {
            "throwing_player": "me",
            "thrown_cards": data["hand"],
            "statement_classification": "generic_concession",
        }
    )

    _, context, outcome, settlement = adjudicate(data)

    assert context.card_reconciliation == "confirmed"
    assert context.joint_liability is False
    assert outcome.game_result_summary["rest_tricks_recipient"] == "defenders"
    assert outcome.game_result_summary["final_points"] == {
        "declarer": 57,
        "defenders": 63,
    }
    assert outcome.game_result_summary["winner"] == "defenders"
    assert settlement["settlement_score"] == -240


@pytest.mark.parametrize("statement", ["none", "generic_concession", "attempted_level_limitation"])
def test_statement_classification_has_no_scoring_effect(statement: str) -> None:
    data = load_example()
    data["game_shortening"]["statement_classification"] = statement

    _, _, outcome, settlement = adjudicate(data)

    assert outcome.game_result_summary["winner"] == "declarer"
    assert outcome.game_result_summary["open_throw_schwarz_applied"] is True
    assert settlement["settlement_score"] == 168


@pytest.mark.parametrize(
    ("current_trick", "next_player", "thrown_cards", "left_size"),
    [
        (["DK"], "left", ["C10", "S10", "D9"], 3),
        (["DK", "D9"], "right", ["C10", "S10"], 2),
    ],
)
def test_incomplete_current_trick_is_assigned_exactly_once(
    current_trick,
    next_player,
    thrown_cards,
    left_size,
) -> None:
    data = load_example()
    data["completed_tricks"] = data["completed_tricks"][:-1]
    data["current_trick"] = current_trick
    data["next_player"] = next_player
    data["left_hand_size"] = left_size
    data["right_hand_size"] = 3
    data["game_shortening"]["thrown_cards"] = thrown_cards

    _, _, outcome, _ = adjudicate(data)
    assignment = outcome.game_result_summary["rest_trick_assignment"]

    assert assignment["remaining_trick_count"] == 3
    assert assignment["assigned_card_count"] == 9
    assert sum(outcome.game_result_summary["final_trick_counts"].values()) == 10
    assert sum(outcome.game_result_summary["final_points"].values()) == 120


def test_one_remaining_thrown_card_is_supported() -> None:
    data = load_example()
    data["completed_tricks"].append(
        {
            "cards": ["H10", "C10", "CK"],
            "players": ["me", "left", "right"],
            "winner_role": "declarer",
            "winner_player": "me",
        }
    )
    data["hand"] = ["HK"]
    data["left_hand_size"] = 1
    data["right_hand_size"] = 1
    data["game_shortening"]["thrown_cards"] = ["S10"]

    _, context, outcome, _ = adjudicate(data)

    assert context.remaining_trick_count == 1
    assert outcome.game_shortening_summary["thrown_card_count"] == 1


def test_reliable_card_and_hand_size_contradictions_are_rejected() -> None:
    data = load_example()
    data["game_shortening"]["thrown_cards"] = ["DA", "S10"]
    with pytest.raises(ValueError, match="skat evidence"):
        validate_position_input(data)

    data = load_example()
    data["left_hand_size"] = 1
    with pytest.raises(ValueError, match="contradicts play history"):
        validate_position_input(data)


def test_preexisting_declarer_and_defender_decisions_are_preserved() -> None:
    declarer_data = load_example()
    declarer_data["declarer_points"] = 4
    declarer_data["game_shortening"].update(
        {"throwing_player": "me", "thrown_cards": declarer_data["hand"]}
    )
    _, _, declarer_outcome, _ = adjudicate(declarer_data)
    assert declarer_outcome.game_result_summary["decision_state_before_game_end"] == (
        "declarer_already_won"
    )
    assert declarer_outcome.game_result_summary["winner"] == "declarer"

    defender_data = load_example()
    defender_data["defender_points"] = 60
    _, _, defender_outcome, _ = adjudicate(defender_data)
    assert defender_outcome.game_result_summary["decision_state_before_game_end"] == (
        "defenders_already_won"
    )
    assert defender_outcome.game_result_summary["winner"] == "defenders"


def test_schneider_threshold_uses_final_rule_assigned_points() -> None:
    data = load_example()
    data["defender_points"] = 30
    _, _, at_threshold, _ = adjudicate(data)
    assert at_threshold.game_result_summary["open_throw_schneider_applied"] is True

    data = load_example()
    data["defender_points"] = 31
    _, _, above_threshold, _ = adjudicate(data)
    assert above_threshold.game_result_summary["open_throw_schneider_applied"] is False


def test_top_jack_ownership_excludes_declarer_throw_schwarz() -> None:
    data = load_example()
    data["game_shortening"].update(
        {"throwing_player": "me", "thrown_cards": data["hand"]}
    )
    _, _, outcome, _ = adjudicate(data)

    assessment = outcome.game_result_summary["theoretical_schwarz_assessment"]
    assert assessment["status"] == "excluded"
    assert assessment["exclusion_basis"] == "losing_party_owned_top_jack"
    assert outcome.game_result_summary["open_throw_schwarz_applied"] is False


def test_still_possible_declared_schwarz_is_covered_by_rule_state() -> None:
    data = load_example()
    data["game_declaration"].update(
        {"hand_game": True, "schneider_announced": True, "schwarz_announced": True}
    )

    _, _, outcome, settlement = adjudicate(data)

    assert outcome.game_result_summary["mandatory_play_level"] == "schwarz"
    assert outcome.game_result_summary["mandatory_level_covered"] is True
    assert outcome.game_result_summary["declared_mandatory_schwarz_applied"] is True
    assert outcome.game_result_summary["winner"] == "declarer"
    assert settlement["settlement_score"] == 240


@pytest.mark.parametrize(
    ("bid_value", "required_level", "expected_value"),
    [(121, "schneider", 144), (145, "schwarz", 168)],
)
def test_supported_overbid_level_is_covered_by_open_throw_rule_state(
    bid_value,
    required_level,
    expected_value,
) -> None:
    data = load_example()
    data["game_declaration"]["bid_value"] = bid_value

    _, _, outcome, settlement = adjudicate(data)

    assert outcome.game_result_summary["overbid_required_level"] == required_level
    assert outcome.game_result_summary["overbid_requirement_covered"] is True
    assert outcome.game_result_summary["winner"] == "declarer"
    assert settlement["effective_game_value"] == expected_value


def test_theoretically_excluded_required_schwarz_preserves_overbid_loss() -> None:
    data = build_null_position(
        throwing_player="left",
        hand_game=False,
        ouvert=False,
    )
    data.update(
        {
            "game_type": "grand",
            "hand": ["CA", "C10", "CK", "CQ", "C9", "C8", "C7", "HA", "H10", "HK"],
            "game_declaration": {"matadors": 1, "bid_value": 73},
        }
    )
    data["game_shortening"]["thrown_cards"] = [
        "CJ",
        "SA",
        "S10",
        "SK",
        "SQ",
        "S9",
        "S8",
        "S7",
        "HQ",
        "H9",
    ]

    _, _, outcome, settlement = adjudicate(data)

    assert outcome.game_result_summary["overbid_required_level"] == "schwarz"
    assert outcome.game_result_summary["theoretical_schwarz_status"] == "excluded"
    assert outcome.game_result_summary["winner_basis"] == (
        "theoretically_excluded_required_schwarz"
    )
    assert outcome.game_result_summary["winner"] == "defenders"
    assert settlement["effective_game_value"] == 96
    assert settlement["settlement_score"] == -192


def test_suit_game_uses_existing_declaration_and_settlement_rules() -> None:
    data = build_null_position(
        throwing_player="left",
        hand_game=False,
        ouvert=False,
    )
    data.update(
        {
            "game_type": "clubs",
            "hand": ["CA", "C10", "CK", "CQ", "C9", "C8", "C7", "HA", "H10", "HK"],
            "game_declaration": {"matadors": 1, "bid_value": 18},
        }
    )
    data["game_shortening"]["thrown_cards"] = [
        "CJ",
        "SA",
        "S10",
        "SK",
        "SQ",
        "S9",
        "S8",
        "S7",
        "HQ",
        "H9",
    ]

    _, _, outcome, settlement = adjudicate(data)

    assert outcome.game_result_summary["winner"] == "declarer"
    assert outcome.game_result_summary["open_throw_schneider_applied"] is True
    assert outcome.game_result_summary["open_throw_schwarz_applied"] is False
    assert settlement["game_value"] == 24
    assert settlement["effective_game_value"] == 36


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
@pytest.mark.parametrize(
    ("throwing_player", "expected_winner"),
    [("me", "declarer"), ("left", "defenders")],
)
def test_all_null_variants_use_rule_assigned_tricks_and_fixed_values(
    hand_game,
    ouvert,
    expected_value,
    throwing_player,
    expected_winner,
) -> None:
    data = build_null_position(
        throwing_player=throwing_player,
        hand_game=hand_game,
        ouvert=ouvert,
    )

    _, _, outcome, settlement = adjudicate(data)

    assert outcome.game_result_summary["winner"] == expected_winner
    assert outcome.game_result_summary["effective_schneider_status"] == "not_applicable"
    assert outcome.game_result_summary["effective_schwarz_status"] == "not_applicable"
    assert outcome.game_result_summary["normally_played_declarer_trick_count"] == 0
    assert outcome.game_result_summary["rule_assigned_declarer_trick_count"] == (
        0 if throwing_player == "me" else 10
    )
    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_score"] == (
        expected_value if expected_winner == "declarer" else -2 * expected_value
    )


def test_cli_result_is_private_and_does_not_run_exact_rest_trick_solver(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("exact rest-trick solver must not run")

    monkeypatch.setattr(
        "skat_ai.defender_open_play.prove_defender_rest_tricks",
        fail_if_called,
    )
    result = build_analysis_result(str(EXAMPLE_PATH))

    assert result["position"]["hand"] == []
    assert result["game_shortening_summary"]["thrown_cards"] == ["C10", "S10"]
    serialized = json.dumps(result)
    assert "remaining_hands" not in serialized
    assert "exact_proof" not in serialized
    assert "simulation" not in result["game_shortening_summary"]
