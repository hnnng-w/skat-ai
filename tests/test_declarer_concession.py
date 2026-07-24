import copy
import json
from pathlib import Path

import pytest

from skat_ai.declarer_concession import (
    DeclarerCardCountEvidence,
    adjudicate_declarer_concession,
    build_declarer_concession,
    validate_declarer_concession_context,
)
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_result import build_game_result_summary_from_points
from skat_ai.game_value import build_game_value_summary
from skat_ai.input_loader import get_input_workflow
from skat_ai.input_validation import validate_position_input
from skat_ai.overbid import build_overbid_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_concession_data(
    hand_cards_remaining: int = 9,
    consent_status: str = "not_required",
    consenting_defender_count: int = 0,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "declarer_concession",
        "declarer_hand_cards_remaining": hand_cards_remaining,
        "defender_consent": {
            "status": consent_status,
            "consenting_defender_count": consenting_defender_count,
        },
    }


def load_example_input() -> dict[str, object]:
    path = PROJECT_ROOT / "examples" / "declarer_concession.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def adjudicate_declaration(
    declaration: GameDeclaration,
    *,
    declarer_points: int = 0,
    defender_points: int = 0,
):
    concession = build_declarer_concession(build_concession_data())
    game_result_summary = build_game_result_summary_from_points(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )
    game_value_summary = build_game_value_summary(declaration)
    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=declaration.bid_value,
    )
    adjudication = adjudicate_declarer_concession(
        game_shortening=concession,
        game_result_summary=game_result_summary,
        game_value_summary=game_value_summary,
        overbid_summary=overbid_summary,
        evidence=DeclarerCardCountEvidence(9, "declarer_hand"),
    )
    settlement = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=adjudication.game_result_summary,
        overbid_summary=overbid_summary,
    )
    return adjudication, settlement, game_value_summary


@pytest.mark.parametrize("hand_cards_remaining", [9, 10])
def test_concession_at_least_nine_cards_requires_no_consent(
    hand_cards_remaining: int,
) -> None:
    concession = build_declarer_concession(
        build_concession_data(hand_cards_remaining=hand_cards_remaining)
    )

    assert concession.declarer_hand_cards_remaining == hand_cards_remaining
    assert concession.defender_consent.status == "not_required"
    assert concession.defender_consent.consenting_defender_count == 0


@pytest.mark.parametrize(
    ("hand_cards_remaining", "consenting_defender_count"),
    [(8, 1), (1, 2)],
)
def test_later_concession_accepts_one_or_two_defenders(
    hand_cards_remaining: int,
    consenting_defender_count: int,
) -> None:
    concession = build_declarer_concession(
        build_concession_data(
            hand_cards_remaining=hand_cards_remaining,
            consent_status="granted",
            consenting_defender_count=consenting_defender_count,
        )
    )

    assert concession.defender_consent.consenting_defender_count == (
        consenting_defender_count
    )


@pytest.mark.parametrize("invalid_count", [0, 11, -1, True, False, 1.5, "9"])
def test_concession_rejects_invalid_hand_card_count(invalid_count: object) -> None:
    data = build_concession_data()
    data["declarer_hand_cards_remaining"] = invalid_count

    with pytest.raises(ValueError, match="declarer_hand_cards_remaining"):
        build_declarer_concession(data)


def test_concession_rejects_missing_hand_card_count() -> None:
    data = build_concession_data()
    data.pop("declarer_hand_cards_remaining")

    with pytest.raises(ValueError, match="missing required keys"):
        build_declarer_concession(data)


@pytest.mark.parametrize(
    ("hand_count", "status", "defender_count"),
    [
        (10, "granted", 1),
        (9, "not_required", 1),
        (8, "not_required", 0),
        (8, "granted", 0),
        (8, "granted", 3),
        (8, "required", 1),
    ],
)
def test_concession_rejects_invalid_consent_combinations(
    hand_count: int,
    status: str,
    defender_count: int,
) -> None:
    with pytest.raises(ValueError, match="defender_consent|consenting defenders"):
        build_declarer_concession(
            build_concession_data(
                hand_cards_remaining=hand_count,
                consent_status=status,
                consenting_defender_count=defender_count,
            )
        )


@pytest.mark.parametrize("invalid_count", [True, False, 1.5, "1"])
def test_concession_rejects_non_integer_consent_count(invalid_count: object) -> None:
    data = build_concession_data()
    consent = data["defender_consent"]
    assert isinstance(consent, dict)
    consent["consenting_defender_count"] = invalid_count

    with pytest.raises(ValueError, match="consenting_defender_count"):
        build_declarer_concession(data)


def test_concession_rejects_unknown_properties_and_versions() -> None:
    unknown_property = build_concession_data()
    unknown_property["open_cards"] = True
    with pytest.raises(ValueError, match="unsupported keys"):
        build_declarer_concession(unknown_property)

    wrong_version = build_concession_data()
    wrong_version["schema_version"] = 2
    with pytest.raises(ValueError, match="schema_version"):
        build_declarer_concession(wrong_version)

    wrong_kind = build_concession_data()
    wrong_kind["kind"] = "defender_concession"
    with pytest.raises(ValueError, match="kind"):
        build_declarer_concession(wrong_kind)


def test_position_validation_confirms_and_rejects_reliable_hand_count() -> None:
    data = load_example_input()
    validate_position_input(copy.deepcopy(data))

    game_shortening = data["game_shortening"]
    assert isinstance(game_shortening, dict)
    game_shortening["declarer_hand_cards_remaining"] = 10

    with pytest.raises(ValueError, match="contradicts reliable declarer_hand"):
        validate_position_input(data)


def test_position_validation_rejects_hand_size_that_contradicts_play_history() -> None:
    data = load_example_input()
    data["hand"] = [*data["hand"], "HA"]
    game_shortening = data["game_shortening"]
    assert isinstance(game_shortening, dict)
    game_shortening["declarer_hand_cards_remaining"] = 10
    consent = game_shortening["defender_consent"]
    assert isinstance(consent, dict)

    with pytest.raises(ValueError, match="current-hand evidence contradicts play history"):
        validate_position_input(data)


def test_unknown_declarer_count_evidence_is_not_required() -> None:
    adjudication, _, _ = adjudicate_declaration(GameDeclaration("grand", matadors=2))
    concession = build_declarer_concession(build_concession_data())
    repeated = adjudicate_declarer_concession(
        game_shortening=concession,
        game_result_summary=build_game_result_summary_from_points(0, 0),
        game_value_summary=build_game_value_summary(GameDeclaration("grand", matadors=2)),
        overbid_summary=build_overbid_summary(
            build_game_value_summary(GameDeclaration("grand", matadors=2)),
            None,
        ),
    )

    assert adjudication.game_shortening_summary["hand_card_count_reconciliation"] == (
        "confirmed"
    )
    assert repeated.game_shortening_summary["hand_card_count_reconciliation"] == (
        "not_verifiable"
    )


@pytest.mark.parametrize(
    "game_end_reason",
    [
        "normal_completion",
        "declarer_claimed_remaining_tricks",
        "declarer_conceded_remaining_tricks",
        "defenders_conceded_remaining_tricks",
        "impossible_null_declaration",
    ],
)
def test_structured_concession_rejects_active_legacy_game_end_reason(
    game_end_reason: str,
) -> None:
    data = load_example_input()
    data["game_end_reason"] = game_end_reason

    with pytest.raises(ValueError, match="active legacy game_end_reason"):
        validate_declarer_concession_context(
            data,
            build_declarer_concession(data["game_shortening"]),
        )


def test_structured_concession_rejects_completed_play_and_list_workflow() -> None:
    data = load_example_input()
    completed = copy.deepcopy(data)
    completed["completed_tricks"] = [{}] * 10
    with pytest.raises(ValueError, match="after all tricks"):
        validate_declarer_concession_context(
            completed,
            build_declarer_concession(completed["game_shortening"]),
        )

    list_input = copy.deepcopy(data)
    list_input["list_performance_input"] = {}
    with pytest.raises(ValueError, match="list-performance"):
        validate_declarer_concession_context(
            list_input,
            build_declarer_concession(list_input["game_shortening"]),
        )


def test_structured_concession_rejects_missing_value_and_unsupported_null_overbid() -> None:
    data = load_example_input()
    data["player_role"] = "unknown"
    data["declarer_player"] = "unknown"
    data["game_declaration"] = {}
    with pytest.raises(ValueError, match="calculate the game value"):
        validate_declarer_concession_context(
            data,
            build_declarer_concession(data["game_shortening"]),
        )

    null_data = load_example_input()
    null_data["game_type"] = "null"
    null_data["game_declaration"] = {"bid_value": 24}
    with pytest.raises(ValueError, match="overbid-required game value"):
        validate_declarer_concession_context(
            null_data,
            build_declarer_concession(null_data["game_shortening"]),
        )


@pytest.mark.parametrize(
    "wrapper_key",
    ["historical_game_input", "training_dataset_input", "opponent_statistics_input"],
)
def test_non_position_workflows_reject_game_shortening(wrapper_key: str) -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        get_input_workflow(
            {
                wrapper_key: {},
                "game_shortening": build_concession_data(),
            }
        )


def test_adjudication_preserves_observed_and_unplayed_points_without_mutation() -> None:
    declaration = GameDeclaration("grand", matadors=2, bid_value=72)
    game_result = build_game_result_summary_from_points(10, 20)
    original = copy.deepcopy(game_result)
    game_value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(game_value, declaration.bid_value)
    concession = build_declarer_concession(build_concession_data())

    first = adjudicate_declarer_concession(
        concession,
        game_result,
        game_value,
        overbid,
        DeclarerCardCountEvidence(9, "declarer_hand"),
    )
    second = adjudicate_declarer_concession(
        concession,
        game_result,
        game_value,
        overbid,
        DeclarerCardCountEvidence(9, "declarer_hand"),
    )
    adjusted = first.game_result_summary

    assert game_result == original
    assert first == second
    assert adjusted["declarer_points"] == 10
    assert adjusted["defender_points"] == 20
    assert adjusted["points_remaining"] == 90
    assert adjusted["is_complete"] is True
    assert adjusted["winner"] == "defenders"
    assert adjusted["status"] == "final_adjudicated"
    assert adjusted["remaining_points_recipient"] is None
    assert adjusted["remaining_points_assigned"] == 0
    assert adjusted["effective_schneider_status"] == "not_applicable"
    assert adjusted["effective_schwarz_status"] == "not_applicable"


@pytest.mark.parametrize(
    ("declaration", "expected_value"),
    [
        (GameDeclaration("spades", matadors=2), 33),
        (GameDeclaration("grand", matadors=2), 72),
        (GameDeclaration("grand", hand_game=True, matadors=2), 96),
        (
            GameDeclaration(
                "clubs",
                hand_game=True,
                schneider_announced=True,
                matadors=1,
            ),
            48,
        ),
        (
            GameDeclaration(
                "clubs",
                hand_game=True,
                schneider_announced=True,
                schwarz_announced=True,
                matadors=1,
            ),
            60,
        ),
        (
            GameDeclaration(
                "clubs",
                hand_game=True,
                schneider_announced=True,
                schwarz_announced=True,
                ouvert=True,
                matadors=1,
            ),
            72,
        ),
    ],
)
def test_suit_and_grand_concession_retains_declared_levels_without_achieved_levels(
    declaration: GameDeclaration,
    expected_value: int,
) -> None:
    adjudication, settlement, game_value = adjudicate_declaration(declaration)

    assert game_value["game_value"] == expected_value
    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_score"] == -2 * expected_value
    assert settlement["winner"] == "defenders"
    assert settlement["declarer_won_by_card_points"] is None
    assert settlement["settlement_basis"]["achieved_schneider_applied"] is False
    assert settlement["settlement_basis"]["achieved_schwarz_applied"] is False
    assert adjudication.game_result_summary["points_remaining"] == 120


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_null_concessions_are_doubled_fixed_value_losses(
    hand_game: bool,
    ouvert: bool,
    expected_value: int,
) -> None:
    _, settlement, _ = adjudicate_declaration(
        GameDeclaration("null", hand_game=hand_game, ouvert=ouvert)
    )

    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_score"] == -2 * expected_value
    assert settlement["is_loss"] is True


def test_concession_overbid_uses_required_value_without_claiming_achieved_levels() -> None:
    _, settlement, game_value = adjudicate_declaration(
        GameDeclaration("grand", matadors=1, bid_value=73)
    )

    assert game_value["game_value"] == 48
    assert settlement["overbid_required_game_value"] == 96
    assert settlement["effective_game_value"] == 96
    assert settlement["settlement_score"] == -192
    assert settlement["settlement_basis"] == {
        "game_end_kind": "declarer_concession",
        "outcome_source": "adjudicated",
        "forced_winner": "defenders",
        "achieved_schneider_applied": False,
        "achieved_schwarz_applied": False,
        "overbid_required_value_applied": True,
    }


def test_observed_low_points_do_not_add_schneider_or_schwarz() -> None:
    _, settlement, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        declarer_points=0,
        defender_points=30,
    )

    assert settlement["game_value"] == 72
    assert settlement["effective_game_value"] == 72
    assert settlement["settlement_score"] == -144
