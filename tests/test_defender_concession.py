import copy
import json
from pathlib import Path

import pytest

from skat_ai.defender_concession import (
    adjudicate_defender_concession,
    build_defender_concession,
    validate_defender_concession_context,
)
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_result import build_game_result_summary_from_points
from skat_ai.game_value import build_game_value_summary
from skat_ai.input_loader import (
    get_declarer_concession_from_input,
    get_game_shortening_from_input,
)
from skat_ai.input_validation import validate_position_input
from skat_ai.overbid import build_overbid_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_concession_data(
    conceding_player: str = "left",
    concession_form: str = "explicit_verbal",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "defender_concession",
        "conceding_player": conceding_player,
        "concession_form": concession_form,
    }


def load_example_input() -> dict[str, object]:
    path = PROJECT_ROOT / "examples" / "defender_concession.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_tricks(*winner_roles: str) -> list[dict[str, object]]:
    return [
        {"cards": ["C7", "C8", "C9"], "winner_role": winner_role}
        for winner_role in winner_roles
    ]


def adjudicate_declaration(
    declaration: GameDeclaration,
    *,
    declarer_points: int = 0,
    defender_points: int = 0,
    winner_roles: tuple[str, ...] = (),
):
    game_result = build_game_result_summary_from_points(
        declarer_points,
        defender_points,
    )
    game_value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(game_value, declaration.bid_value)
    adjudication = adjudicate_defender_concession(
        build_defender_concession(build_concession_data()),
        game_result,
        game_value,
        overbid,
        build_tricks(*winner_roles),
    )
    settlement = build_final_settlement_summary(
        game_value,
        adjudication.game_result_summary,
        overbid,
        build_tricks(*winner_roles),
    )
    return adjudication, settlement, game_value


@pytest.mark.parametrize("conceding_player", ["me", "left", "right"])
@pytest.mark.parametrize(
    "concession_form",
    ["explicit_verbal", "adjudicated_unambiguous_conduct"],
)
def test_build_defender_concession_accepts_players_and_forms(
    conceding_player: str,
    concession_form: str,
) -> None:
    concession = build_defender_concession(
        build_concession_data(conceding_player, concession_form)
    )

    assert concession.conceding_player == conceding_player
    assert concession.concession_form == concession_form


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("kind", "declarer_concession"),
        ("conceding_player", "unknown"),
        ("conceding_player", " left"),
        ("conceding_player", "left "),
        ("concession_form", "ambiguous_conduct"),
        ("concession_form", " explicit_verbal"),
    ],
)
def test_build_defender_concession_rejects_invalid_fields(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_concession_data()
    data[field_name] = invalid_value

    with pytest.raises(ValueError, match=field_name):
        build_defender_concession(data)


@pytest.mark.parametrize("missing_field", list(build_concession_data()))
def test_build_defender_concession_rejects_missing_fields(missing_field: str) -> None:
    data = build_concession_data()
    data.pop(missing_field)

    with pytest.raises(ValueError, match="missing required keys"):
        build_defender_concession(data)


def test_build_defender_concession_rejects_unknown_property() -> None:
    data = build_concession_data()
    data["partner_consent"] = False

    with pytest.raises(ValueError, match="unsupported keys"):
        build_defender_concession(data)


def test_runtime_game_shortening_union_dispatches_without_reinterpreting_kind() -> None:
    data = {"game_shortening": build_concession_data()}

    assert get_game_shortening_from_input(data) == build_defender_concession(
        data["game_shortening"]
    )
    assert get_declarer_concession_from_input(data) is None


@pytest.mark.parametrize(
    ("declarer_player", "conceding_player"),
    [("left", "me"), ("me", "left"), ("me", "right")],
)
def test_position_validation_accepts_each_concrete_defender(
    declarer_player: str,
    conceding_player: str,
) -> None:
    data = load_example_input()
    data["declarer_player"] = declarer_player
    data["player_role"] = "defender" if declarer_player != "me" else "declarer"
    if declarer_player != "me":
        data["completed_tricks"] = []
    shortening = data["game_shortening"]
    assert isinstance(shortening, dict)
    shortening["conceding_player"] = conceding_player

    validate_position_input(data)


def test_position_validation_rejects_declarer_as_conceding_player() -> None:
    data = load_example_input()
    shortening = data["game_shortening"]
    assert isinstance(shortening, dict)
    shortening["conceding_player"] = "me"

    with pytest.raises(ValueError, match="defending party"):
        validate_position_input(data)


def test_context_rejects_unknown_declarer_and_live_analysis() -> None:
    data = load_example_input()
    concession = build_defender_concession(data["game_shortening"])
    data["declarer_player"] = "unknown"
    with pytest.raises(ValueError, match="concrete declarer_player"):
        validate_defender_concession_context(data, concession)

    data = load_example_input()
    data["analysis_mode"] = "live_decision"
    with pytest.raises(ValueError, match="post_game_review"):
        validate_defender_concession_context(data, concession)


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
def test_context_rejects_active_legacy_game_end_reason(game_end_reason: str) -> None:
    data = load_example_input()
    data["game_end_reason"] = game_end_reason

    with pytest.raises(ValueError, match="active legacy game_end_reason"):
        validate_defender_concession_context(
            data,
            build_defender_concession(data["game_shortening"]),
        )


def test_context_rejects_impossible_null_list_and_completed_play() -> None:
    data = load_example_input()
    concession = build_defender_concession(data["game_shortening"])

    impossible = copy.deepcopy(data)
    impossible["impossible_null_settlement"] = {}
    with pytest.raises(ValueError, match="impossible_null_settlement"):
        validate_defender_concession_context(impossible, concession)

    list_input = copy.deepcopy(data)
    list_input["list_game_contributions"] = []
    with pytest.raises(ValueError, match="list-performance"):
        validate_defender_concession_context(list_input, concession)

    completed = copy.deepcopy(data)
    completed["completed_tricks"] = [{}] * 10
    with pytest.raises(ValueError, match="all ten tricks"):
        validate_defender_concession_context(completed, concession)


def test_context_rejects_missing_value_and_unsupported_overbid_depth() -> None:
    data = load_example_input()
    data["game_declaration"] = {}
    data["player_role"] = "defender"
    data["declarer_player"] = "right"
    data["hand"] = ["H7"]
    with pytest.raises(ValueError, match="calculate the game value"):
        validate_defender_concession_context(
            data,
            build_defender_concession(data["game_shortening"]),
        )

    data = load_example_input()
    data["game_declaration"] = {"matadors": 1, "bid_value": 121}
    with pytest.raises(ValueError, match="beyond Schwarz"):
        validate_defender_concession_context(
            data,
            build_defender_concession(data["game_shortening"]),
        )


def test_undecided_concession_preserves_points_and_binds_both_defenders() -> None:
    game_result = build_game_result_summary_from_points(20, 30)
    original = copy.deepcopy(game_result)
    declaration = GameDeclaration("grand", matadors=2, bid_value=72)
    game_value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(game_value, declaration.bid_value)
    adjudication = adjudicate_defender_concession(
        build_defender_concession(build_concession_data()),
        game_result,
        game_value,
        overbid,
        [],
    )
    adjusted = adjudication.game_result_summary
    summary = adjudication.game_shortening_summary

    assert game_result == original
    assert adjusted["declarer_points"] == 20
    assert adjusted["defender_points"] == 30
    assert adjusted["points_remaining"] == 70
    assert adjusted["winner"] == "declarer"
    assert adjusted["status"] == "final_adjudicated"
    assert adjusted["remaining_points_recipient"] is None
    assert adjusted["remaining_points_assigned"] == 0
    assert summary["liable_party"] == "defenders"
    assert summary["joint_liability"] is True
    assert "partner_consent" not in summary
    assert summary["rule_sections"] == ["4.4.3", "4.1.4"]


@pytest.mark.parametrize(
    ("declaration", "expected_value"),
    [
        (GameDeclaration("spades", matadors=2), 33),
        (GameDeclaration("grand", matadors=2), 72),
        (GameDeclaration("grand", hand_game=True, matadors=2), 96),
    ],
)
def test_undecided_suit_and_grand_use_declared_value_without_optional_levels(
    declaration: GameDeclaration,
    expected_value: int,
) -> None:
    adjudication, settlement, game_value = adjudicate_declaration(declaration)

    assert game_value["game_value"] == expected_value
    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_score"] == expected_value
    assert settlement["winner"] == "declarer"
    assert settlement["settlement_basis"]["achieved_schneider_applied"] is False
    assert settlement["settlement_basis"]["achieved_schwarz_applied"] is False
    assert adjudication.game_result_summary["points_remaining"] == 120


@pytest.mark.parametrize(
    "declaration",
    [
        GameDeclaration(
            "clubs", hand_game=True, schneider_announced=True, matadors=1
        ),
        GameDeclaration(
            "clubs",
            hand_game=True,
            schneider_announced=True,
            schwarz_announced=True,
            matadors=1,
        ),
        GameDeclaration(
            "clubs",
            hand_game=True,
            schneider_announced=True,
            schwarz_announced=True,
            ouvert=True,
            matadors=1,
        ),
    ],
)
def test_still_possible_declared_level_is_mandatory_awarded(
    declaration: GameDeclaration,
) -> None:
    adjudication, settlement, _ = adjudicate_declaration(declaration)
    summary = adjudication.game_shortening_summary
    basis = settlement["settlement_basis"]

    assert summary["decision_state_before_concession"] == "undecided"
    assert summary["rule_sections"] == ["4.4.3", "4.1.4", "4.1.5"]
    assert basis["mandatory_level_awarded"] is True
    assert basis["mandatory_level_source"] == "declared_announcement"
    assert basis["achieved_schneider_applied"] is False
    assert basis["achieved_schwarz_applied"] is False


def test_failed_schneider_announcement_preserves_declarer_loss() -> None:
    adjudication, settlement, _ = adjudicate_declaration(
        GameDeclaration(
            "clubs", hand_game=True, schneider_announced=True, matadors=1
        ),
        declarer_points=61,
        defender_points=31,
    )

    assert adjudication.game_result_summary["winner"] == "defenders"
    assert adjudication.game_shortening_summary[
        "decision_state_before_concession"
    ] == "defenders_already_won"
    assert settlement["settlement_score"] < 0
    assert settlement["settlement_basis"]["mandatory_level_awarded"] is False


@pytest.mark.parametrize("ouvert", [False, True])
def test_failed_schwarz_or_ouvert_preserves_declarer_loss(ouvert: bool) -> None:
    adjudication, settlement, _ = adjudicate_declaration(
        GameDeclaration(
            "clubs",
            hand_game=True,
            schneider_announced=True,
            schwarz_announced=True,
            ouvert=ouvert,
            matadors=1,
        ),
        winner_roles=("defenders",),
    )

    assert adjudication.game_result_summary["winner"] == "defenders"
    assert settlement["settlement_score"] < 0


def test_supported_overbid_requirements_are_awarded_only_while_possible() -> None:
    schneider, schneider_settlement, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=1, bid_value=49)
    )
    schwarz, schwarz_settlement, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=1, bid_value=73)
    )

    assert schneider_settlement["effective_game_value"] == 72
    assert schwarz_settlement["effective_game_value"] == 96
    assert schneider_settlement["settlement_basis"]["mandatory_level_source"] == (
        "overbid_requirement"
    )
    assert schwarz_settlement["settlement_basis"]["mandatory_level_awarded"] is True
    assert schneider.game_result_summary["achieved_schneider_applied"] is False
    assert schwarz.game_result_summary["achieved_schwarz_applied"] is False

    failed_schneider, _, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=1, bid_value=49),
        declarer_points=61,
        defender_points=31,
    )
    failed_schwarz, _, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=1, bid_value=73),
        winner_roles=("defenders",),
    )
    assert failed_schneider.game_result_summary["winner"] == "defenders"
    assert failed_schwarz.game_result_summary["winner"] == "defenders"


def test_declared_and_overbid_mandatory_sources_remain_distinct() -> None:
    _, settlement, _ = adjudicate_declaration(
        GameDeclaration(
            "grand",
            hand_game=True,
            schneider_announced=True,
            matadors=1,
            bid_value=97,
        )
    )

    assert settlement["effective_game_value"] == 120
    assert settlement["settlement_basis"]["mandatory_level_source"] == (
        "declared_announcement_and_overbid_requirement"
    )
    assert settlement["settlement_basis"]["mandatory_level_awarded"] is True
    assert settlement["settlement_basis"]["achieved_schneider_applied"] is False


def test_preexisting_suit_or_grand_decisions_are_preserved() -> None:
    declarer_win, win_settlement, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        declarer_points=61,
    )
    defender_win, loss_settlement, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        defender_points=60,
    )

    assert declarer_win.game_result_summary["winner"] == "declarer"
    assert defender_win.game_result_summary["winner"] == "defenders"
    assert declarer_win.game_result_summary["status"] == "final_decided"
    assert defender_win.game_shortening_summary["winner_basis"] == (
        "preexisting_game_decision"
    )
    assert win_settlement["settlement_score"] == 72
    assert loss_settlement["settlement_score"] == -144
    assert loss_settlement["settlement_basis"]["outcome_source"] == (
        "preexisting_game_decision"
    )


def test_secured_schneider_uses_observed_points_only() -> None:
    adjudication, settlement, _ = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        declarer_points=90,
    )

    assert adjudication.game_result_summary["effective_schneider_status"] == (
        "declarer_made_schneider"
    )
    assert settlement["effective_game_value"] == 96
    assert settlement["settlement_basis"]["achieved_schneider_applied"] is True
    assert settlement["settlement_basis"]["achieved_schwarz_applied"] is False


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_null_variants_use_trick_ownership_not_points(
    hand_game: bool,
    ouvert: bool,
    expected_value: int,
) -> None:
    win, win_settlement, _ = adjudicate_declaration(
        GameDeclaration("null", hand_game=hand_game, ouvert=ouvert),
        defender_points=60,
    )
    loss, loss_settlement, _ = adjudicate_declaration(
        GameDeclaration("null", hand_game=hand_game, ouvert=ouvert),
        declarer_points=61,
        winner_roles=("declarer",),
    )

    assert win.game_result_summary["winner"] == "declarer"
    assert win_settlement["settlement_score"] == expected_value
    assert loss.game_result_summary["winner"] == "defenders"
    assert loss_settlement["settlement_score"] == -2 * expected_value
    assert loss.game_result_summary["remaining_points_assigned"] == 0
