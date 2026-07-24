import copy
import json
from pathlib import Path

import pytest

from skat_ai.declarer_card_exposure import (
    DeclarerExposedCardEvidence,
    adjudicate_accepted_declarer_card_exposure,
    build_declarer_card_exposure,
    build_declarer_exposed_card_evidence,
    reconcile_exposed_cards,
    validate_declarer_card_exposure_context,
    validate_exposure_parties,
)
from skat_ai.declarer_concession import DeclarerCardCountEvidence
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_result import build_game_result_summary_from_points
from skat_ai.game_shortening import get_game_shortening_from_input
from skat_ai.game_value import build_game_value_summary
from skat_ai.input_validation import validate_position_input
from skat_ai.overbid import build_overbid_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_exposure_data(
    *,
    form: str = "laid_open",
    exposed_cards: list[object] | None = None,
    shown_to_player: str | None = None,
    claimed_play_level: str = "simple",
    response_players: tuple[str, str] = ("left", "right"),
    response_forms: tuple[str, str] = ("explicit", "unambiguous_conduct"),
) -> dict[str, object]:
    exposure: dict[str, object] = {
        "form": form,
        "exposed_cards": exposed_cards if exposed_cards is not None else ["C7"],
    }
    if shown_to_player is not None:
        exposure["shown_to_player"] = shown_to_player
    return {
        "schema_version": 1,
        "kind": "declarer_card_exposure",
        "exposure": exposure,
        "claimed_play_level": claimed_play_level,
        "defender_responses": [
            {
                "player": player,
                "response": "accept",
                "form": response_form,
            }
            for player, response_form in zip(
                response_players, response_forms, strict=True
            )
        ],
    }


def load_example_input() -> dict[str, object]:
    with (PROJECT_ROOT / "examples" / "declarer_card_exposure.json").open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)


def adjudicate_declaration(
    declaration: GameDeclaration,
    *,
    claimed_play_level: str = "simple",
    declarer_points: int = 0,
    defender_points: int = 0,
    winner_roles: tuple[str, ...] = (),
):
    exposure = build_declarer_card_exposure(
        build_exposure_data(claimed_play_level=claimed_play_level)
    )
    result = build_game_result_summary_from_points(declarer_points, defender_points)
    value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(value, declaration.bid_value)
    tricks = [
        {"cards": ["D7", "D8", "D9"], "winner_role": winner_role}
        for winner_role in winner_roles
    ]
    adjudication = adjudicate_accepted_declarer_card_exposure(
        exposure,
        result,
        value,
        overbid,
        tricks,
    )
    settlement = build_final_settlement_summary(
        value,
        adjudication.game_result_summary,
        overbid,
        tricks,
    )
    return adjudication, settlement


@pytest.mark.parametrize("claimed_level", ["simple", "schneider", "schwarz"])
def test_runtime_union_accepts_all_suit_grand_claim_levels(claimed_level: str) -> None:
    data = build_exposure_data(claimed_play_level=claimed_level)

    exposure = get_game_shortening_from_input({"game_shortening": data})

    assert exposure == build_declarer_card_exposure(data)
    assert exposure.claimed_play_level == claimed_level


@pytest.mark.parametrize(
    ("form", "shown_to_player"),
    [
        ("laid_open", None),
        ("shown_to_defender", "me"),
        ("shown_to_defender", "left"),
        ("shown_to_defender", "right"),
    ],
)
def test_exposure_forms_and_concrete_shown_players(
    form: str,
    shown_to_player: str | None,
) -> None:
    exposure = build_declarer_card_exposure(
        build_exposure_data(form=form, shown_to_player=shown_to_player)
    )

    assert exposure.exposure.form == form
    assert exposure.exposure.shown_to_player == shown_to_player


def test_exposure_form_requires_and_forbids_shown_player() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        build_declarer_card_exposure(build_exposure_data(form="shown_to_defender"))

    with pytest.raises(ValueError, match="unsupported keys"):
        build_declarer_card_exposure(
            build_exposure_data(form="laid_open", shown_to_player="left")
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("kind", "defender_concession"),
        ("claimed_play_level", "ouvert"),
    ],
)
def test_builder_rejects_invalid_top_level_values(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_exposure_data()
    data[field_name] = invalid_value

    with pytest.raises(ValueError, match=field_name):
        build_declarer_card_exposure(data)


@pytest.mark.parametrize("missing_field", list(build_exposure_data()))
def test_builder_rejects_missing_top_level_fields(missing_field: str) -> None:
    data = build_exposure_data()
    data.pop(missing_field)

    with pytest.raises(ValueError, match="missing required keys"):
        build_declarer_card_exposure(data)


def test_builder_rejects_unknown_top_level_and_nested_properties() -> None:
    data = build_exposure_data()
    data["continued_play"] = False
    with pytest.raises(ValueError, match="unsupported keys"):
        build_declarer_card_exposure(data)

    data = build_exposure_data()
    exposure = data["exposure"]
    assert isinstance(exposure, dict)
    exposure["deliberate"] = True
    with pytest.raises(ValueError, match="unsupported keys"):
        build_declarer_card_exposure(data)


@pytest.mark.parametrize(
    "cards",
    [
        [],
        ["C7"] * 11,
        ["C7", "C7"],
        ["X7"],
        [True],
        [None],
        [7],
        [["C7"]],
    ],
)
def test_builder_rejects_invalid_exposed_card_lists(cards: list[object]) -> None:
    with pytest.raises(ValueError, match="exposed_cards|Invalid|Duplicate"):
        build_declarer_card_exposure(build_exposure_data(exposed_cards=cards))


@pytest.mark.parametrize(
    "cards",
    [
        ["C7"],
        ["CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10"],
    ],
)
def test_builder_accepts_one_or_ten_unique_cards(cards: list[str]) -> None:
    exposure = build_declarer_card_exposure(build_exposure_data(exposed_cards=cards))

    assert list(exposure.exposure.exposed_cards) == cards


@pytest.mark.parametrize("acceptance_form", ["explicit", "unambiguous_conduct"])
def test_builder_accepts_both_external_acceptance_forms(
    acceptance_form: str,
) -> None:
    exposure = build_declarer_card_exposure(
        build_exposure_data(response_forms=(acceptance_form, acceptance_form))
    )

    assert {response.form for response in exposure.defender_responses} == {
        acceptance_form
    }


def test_builder_requires_two_unique_accepting_concrete_players() -> None:
    data = build_exposure_data()
    responses = data["defender_responses"]
    assert isinstance(responses, list)
    responses.pop()
    with pytest.raises(ValueError, match="exactly two"):
        build_declarer_card_exposure(data)

    with pytest.raises(ValueError, match="each defender exactly once"):
        build_declarer_card_exposure(
            build_exposure_data(response_players=("left", "left"))
        )

    with pytest.raises(ValueError, match="player"):
        build_declarer_card_exposure(
            build_exposure_data(response_players=("left", "unknown"))
        )


def test_non_acceptance_uses_deterministic_continuation_message() -> None:
    data = build_exposure_data()
    responses = data["defender_responses"]
    assert isinstance(responses, list) and isinstance(responses[1], dict)
    responses[1]["response"] = "continue_play"

    with pytest.raises(ValueError, match="continuation.*not supported by Issue #88"):
        build_declarer_card_exposure(data)


@pytest.mark.parametrize(
    ("declarer", "responders", "shown"),
    [
        ("me", ("left", "right"), "left"),
        ("left", ("me", "right"), "me"),
        ("right", ("me", "left"), "left"),
    ],
)
def test_party_validation_accepts_exact_defender_sets(
    declarer: str,
    responders: tuple[str, str],
    shown: str,
) -> None:
    exposure = build_declarer_card_exposure(
        build_exposure_data(
            form="shown_to_defender",
            shown_to_player=shown,
            response_players=responders,
        )
    )

    validate_exposure_parties(exposure, declarer)


def test_party_validation_rejects_declarer_as_responder_or_shown_player() -> None:
    exposure = build_declarer_card_exposure(
        build_exposure_data(response_players=("me", "left"))
    )
    with pytest.raises(ValueError, match="cannot include the declarer"):
        validate_exposure_parties(exposure, "me")

    shown = build_declarer_card_exposure(
        build_exposure_data(
            form="shown_to_defender",
            shown_to_player="me",
        )
    )
    with pytest.raises(ValueError, match="not the declarer"):
        validate_exposure_parties(shown, "me")


def test_reconciliation_confirms_exact_hand_and_canonicalizes_only_output() -> None:
    exposure = build_declarer_card_exposure(
        build_exposure_data(exposed_cards=["SJ", "C7", "CA"])
    )
    evidence = DeclarerExposedCardEvidence(
        declarer_player="me",
        exact_declarer_cards=("CA", "SJ", "C7"),
        declarer_card_count=DeclarerCardCountEvidence(3, "declarer_hand"),
        unavailable_cards=(),
    )
    assert list(exposure.exposure.exposed_cards) == ["SJ", "C7", "CA"]
    assert reconcile_exposed_cards(exposure, evidence) == "confirmed"

    value = build_game_value_summary(GameDeclaration("grand", matadors=2))
    adjudication = adjudicate_accepted_declarer_card_exposure(
        exposure,
        build_game_result_summary_from_points(0, 0),
        value,
        build_overbid_summary(value, None),
        [],
        evidence,
    )
    assert adjudication.game_shortening_summary["exposed_cards"] == [
        "CA",
        "C7",
        "SJ",
    ]


def test_reconciliation_rejects_count_exact_set_and_ownership_contradictions() -> None:
    exposure = build_declarer_card_exposure(
        build_exposure_data(exposed_cards=["C7", "C8"])
    )
    with pytest.raises(ValueError, match="expected 3 cards"):
        reconcile_exposed_cards(
            exposure,
            DeclarerExposedCardEvidence(
                "left", None, DeclarerCardCountEvidence(3, "left_hand_size"), ()
            ),
        )
    with pytest.raises(ValueError, match="exactly match"):
        reconcile_exposed_cards(
            exposure,
            DeclarerExposedCardEvidence(
                "me",
                ("C7", "C9"),
                DeclarerCardCountEvidence(2, "declarer_hand"),
                (),
            ),
        )
    for source in ("completed_tricks", "current_trick", "skat", "defender_hand"):
        with pytest.raises(ValueError, match=source):
            reconcile_exposed_cards(
                exposure,
                DeclarerExposedCardEvidence(
                    "left",
                    None,
                    DeclarerCardCountEvidence(2, "left_hand_size"),
                    (("C7", source),),
                ),
            )


def test_insufficient_exact_evidence_is_not_verifiable_without_inference() -> None:
    exposure = build_declarer_card_exposure(build_exposure_data())
    evidence = DeclarerExposedCardEvidence(
        "left",
        None,
        DeclarerCardCountEvidence(1, "left_hand_size"),
        (),
    )

    assert reconcile_exposed_cards(exposure, evidence) == "not_verifiable"
    assert reconcile_exposed_cards(exposure, None) == "not_verifiable"


def test_example_has_confirmed_complete_reconciliation() -> None:
    data = load_example_input()
    validate_position_input(data)
    exposure = build_declarer_card_exposure(data["game_shortening"])

    assert reconcile_exposed_cards(
        exposure,
        build_declarer_exposed_card_evidence(data),
    ) == "confirmed"


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("analysis_mode", "live_decision", "post_game_review"),
        ("game_end_reason", "normal_completion", "active legacy"),
        ("game_end_reason", "declarer_claimed_remaining_tricks", "active legacy"),
    ],
)
def test_context_rejects_wrong_workflow_or_active_legacy_end(
    field_name: str,
    value: str,
    message: str,
) -> None:
    data = load_example_input()
    data[field_name] = value

    with pytest.raises(ValueError, match=message):
        validate_declarer_card_exposure_context(
            data,
            build_declarer_card_exposure(data["game_shortening"]),
        )


def test_context_rejects_impossible_null_list_completion_and_missing_value() -> None:
    data = load_example_input()
    exposure = build_declarer_card_exposure(data["game_shortening"])

    impossible = copy.deepcopy(data)
    impossible["impossible_null_settlement"] = {}
    with pytest.raises(ValueError, match="impossible_null_settlement"):
        validate_declarer_card_exposure_context(impossible, exposure)

    list_input = copy.deepcopy(data)
    list_input["list_analysis_results"] = []
    with pytest.raises(ValueError, match="list-performance"):
        validate_declarer_card_exposure_context(list_input, exposure)

    completed = copy.deepcopy(data)
    completed["completed_tricks"] = [{}] * 10
    with pytest.raises(ValueError, match="all ten tricks"):
        validate_declarer_card_exposure_context(completed, exposure)

    missing_value = copy.deepcopy(data)
    missing_value["game_declaration"] = {}
    missing_value["player_role"] = "defender"
    missing_value["declarer_player"] = "left"
    missing_value["hand"] = ["H7"]
    shortening = missing_value["game_shortening"]
    assert isinstance(shortening, dict)
    shortening["defender_responses"] = [
        {"player": "me", "response": "accept", "form": "explicit"},
        {"player": "right", "response": "accept", "form": "explicit"},
    ]
    shortening["exposure"] = {
        "form": "laid_open",
        "exposed_cards": ["CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SJ"],
    }
    with pytest.raises(ValueError, match="calculate the game value"):
        validate_declarer_card_exposure_context(
            missing_value,
            build_declarer_card_exposure(shortening),
        )


@pytest.mark.parametrize(
    ("claimed_level", "expected_value", "schneider", "schwarz"),
    [
        ("simple", 72, False, False),
        ("schneider", 96, True, False),
        ("schwarz", 120, True, True),
    ],
)
def test_undecided_grand_applies_claim_without_achieved_labels(
    claimed_level: str,
    expected_value: int,
    schneider: bool,
    schwarz: bool,
) -> None:
    adjudication, settlement = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        claimed_play_level=claimed_level,
        declarer_points=20,
        defender_points=30,
    )
    result = adjudication.game_result_summary
    basis = settlement["settlement_basis"]

    assert result["winner"] == "declarer"
    assert result["status"] == "final_adjudicated"
    assert result["declarer_points"] == 20
    assert result["defender_points"] == 30
    assert result["points_remaining"] == 70
    assert result["remaining_points_recipient"] is None
    assert result["remaining_points_assigned"] == 0
    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_score"] == expected_value
    assert basis["accepted_claimed_schneider_applied"] is schneider
    assert basis["accepted_claimed_schwarz_applied"] is schwarz
    assert basis["achieved_schneider_applied"] is False
    assert basis["achieved_schwarz_applied"] is False


@pytest.mark.parametrize(
    ("declaration", "expected_value", "mandatory_schneider", "mandatory_schwarz"),
    [
        (GameDeclaration("clubs", matadors=1, hand_game=True), 36, False, False),
        (
            GameDeclaration(
                "clubs", matadors=1, hand_game=True, schneider_announced=True
            ),
            60,
            True,
            False,
        ),
        (
            GameDeclaration(
                "clubs",
                matadors=1,
                hand_game=True,
                schneider_announced=True,
                schwarz_announced=True,
            ),
            84,
            True,
            True,
        ),
        (
            GameDeclaration(
                "clubs",
                matadors=1,
                hand_game=True,
                schneider_announced=True,
                schwarz_announced=True,
                ouvert=True,
            ),
            96,
            True,
            True,
        ),
    ],
)
def test_simple_claim_preserves_hand_and_declared_mandatory_levels(
    declaration: GameDeclaration,
    expected_value: int,
    mandatory_schneider: bool,
    mandatory_schwarz: bool,
) -> None:
    _, settlement = adjudicate_declaration(declaration)
    basis = settlement["settlement_basis"]

    assert settlement["effective_game_value"] == expected_value
    assert basis["declared_mandatory_schneider_applied"] is mandatory_schneider
    assert basis["declared_mandatory_schwarz_applied"] is mandatory_schwarz
    assert basis["accepted_claimed_schneider_applied"] is False


def test_failed_declared_levels_preserve_preexisting_loss() -> None:
    schneider, schneider_settlement = adjudicate_declaration(
        GameDeclaration(
            "clubs", matadors=1, hand_game=True, schneider_announced=True
        ),
        claimed_play_level="schwarz",
        declarer_points=61,
        defender_points=31,
    )
    schwarz, schwarz_settlement = adjudicate_declaration(
        GameDeclaration(
            "clubs",
            matadors=1,
            hand_game=True,
            schneider_announced=True,
            schwarz_announced=True,
        ),
        claimed_play_level="schwarz",
        winner_roles=("defenders",),
    )

    for adjudication, settlement in (
        (schneider, schneider_settlement),
        (schwarz, schwarz_settlement),
    ):
        assert adjudication.game_result_summary["winner"] == "defenders"
        assert adjudication.game_shortening_summary["winner_basis"] == (
            "preexisting_game_decision"
        )
        assert settlement["settlement_score"] < 0
        assert settlement["settlement_basis"][
            "accepted_claimed_schwarz_applied"
        ] is False


@pytest.mark.parametrize(
    ("bid", "claim", "winner", "expected_value", "covered"),
    [
        (49, "simple", "defenders", 72, False),
        (49, "schneider", "declarer", 72, True),
        (73, "schneider", "defenders", 96, False),
        (73, "schwarz", "declarer", 96, True),
    ],
)
def test_supported_overbid_level_must_be_covered_by_claim(
    bid: int,
    claim: str,
    winner: str,
    expected_value: int,
    covered: bool,
) -> None:
    adjudication, settlement = adjudicate_declaration(
        GameDeclaration("grand", matadors=1, bid_value=bid),
        claimed_play_level=claim,
    )

    assert adjudication.game_result_summary["winner"] == winner
    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_basis"]["overbid_requirement_covered"] is covered
    assert settlement["settlement_basis"][
        "overbid_required_value_applied"
    ] is True
    assert settlement["settlement_basis"]["achieved_schneider_applied"] is False


def test_declared_mandatory_level_can_cover_supported_overbid_requirement() -> None:
    adjudication, settlement = adjudicate_declaration(
        GameDeclaration(
            "grand",
            matadors=1,
            hand_game=True,
            schneider_announced=True,
            bid_value=97,
        ),
        claimed_play_level="simple",
    )

    assert adjudication.game_result_summary["winner"] == "declarer"
    assert settlement["effective_game_value"] == 120
    assert settlement["settlement_basis"]["overbid_requirement_covered"] is True
    assert settlement["settlement_basis"][
        "declared_mandatory_schneider_applied"
    ] is True


def test_unsupported_overbid_depth_is_rejected() -> None:
    value = build_game_value_summary(GameDeclaration("grand", matadors=1))
    overbid = build_overbid_summary(value, 121)

    with pytest.raises(ValueError, match="beyond Schwarz"):
        adjudicate_accepted_declarer_card_exposure(
            build_declarer_card_exposure(build_exposure_data()),
            build_game_result_summary_from_points(0, 0),
            value,
            overbid,
            [],
        )


def test_preexisting_wins_and_losses_are_preserved_without_claim_upgrade() -> None:
    declarer_win, win_settlement = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        claimed_play_level="schwarz",
        declarer_points=61,
    )
    defender_win, loss_settlement = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        claimed_play_level="schwarz",
        defender_points=60,
    )

    assert declarer_win.game_result_summary["winner"] == "declarer"
    assert defender_win.game_result_summary["winner"] == "defenders"
    assert declarer_win.game_result_summary["status"] == "final_decided"
    assert win_settlement["effective_game_value"] == 72
    assert loss_settlement["settlement_score"] == -144
    assert win_settlement["settlement_basis"][
        "accepted_claimed_schwarz_applied"
    ] is False
    assert loss_settlement["settlement_basis"]["winner_basis"] == (
        "preexisting_game_decision"
    )


def test_preexisting_secured_schneider_is_achieved_not_claimed() -> None:
    _, settlement = adjudicate_declaration(
        GameDeclaration("grand", matadors=2),
        claimed_play_level="schwarz",
        declarer_points=90,
    )
    basis = settlement["settlement_basis"]

    assert settlement["effective_game_value"] == 96
    assert basis["achieved_schneider_applied"] is True
    assert basis["accepted_claimed_schneider_applied"] is False
    assert basis["accepted_claimed_schwarz_applied"] is False


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_null_variants_win_without_prior_declarer_trick(
    hand_game: bool,
    ouvert: bool,
    expected_value: int,
) -> None:
    adjudication, settlement = adjudicate_declaration(
        GameDeclaration("null", hand_game=hand_game, ouvert=ouvert),
        defender_points=60,
    )

    assert adjudication.game_result_summary["winner"] == "declarer"
    assert settlement["effective_game_value"] == expected_value
    assert settlement["settlement_score"] == expected_value
    assert settlement["settlement_basis"]["achieved_schneider_applied"] is False


def test_null_prior_declarer_trick_preserves_loss_and_points_do_not_decide() -> None:
    adjudication, settlement = adjudicate_declaration(
        GameDeclaration("null"),
        declarer_points=90,
        winner_roles=("declarer",),
    )

    assert adjudication.game_result_summary["winner"] == "defenders"
    assert settlement["settlement_score"] == -46
    assert adjudication.game_result_summary["remaining_points_assigned"] == 0


@pytest.mark.parametrize("claimed_level", ["schneider", "schwarz"])
def test_null_rejects_higher_claim_levels(claimed_level: str) -> None:
    value = build_game_value_summary(GameDeclaration("null"))

    with pytest.raises(ValueError, match="requires claimed_play_level='simple'"):
        adjudicate_accepted_declarer_card_exposure(
            build_declarer_card_exposure(
                build_exposure_data(claimed_play_level=claimed_level)
            ),
            build_game_result_summary_from_points(0, 0),
            value,
            build_overbid_summary(value, None),
            [],
        )


def test_response_order_does_not_change_deterministic_output_or_inputs() -> None:
    first = build_declarer_card_exposure(build_exposure_data())
    second = build_declarer_card_exposure(
        build_exposure_data(
            response_players=("right", "left"),
            response_forms=("unambiguous_conduct", "explicit"),
        )
    )
    result = build_game_result_summary_from_points(0, 0)
    original = copy.deepcopy(result)
    value = build_game_value_summary(GameDeclaration("grand", matadors=2))
    overbid = build_overbid_summary(value, None)

    first_output = adjudicate_accepted_declarer_card_exposure(
        first, result, value, overbid, []
    )
    second_output = adjudicate_accepted_declarer_card_exposure(
        second, result, value, overbid, []
    )

    assert result == original
    assert first_output == second_output
    assert first_output.game_shortening_summary["accepting_defenders"] == [
        "left",
        "right",
    ]


def test_package_version_remains_0_8_0() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'version = "0.8.0"' in pyproject
