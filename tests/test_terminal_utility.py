import pytest

from skatmind.terminal_utility import (
    TERMINAL_UTILITY_VERSION,
    build_terminal_utility,
    compare_terminal_utilities,
    terminal_utility_comparison_key,
)


@pytest.mark.parametrize("game_type", ["clubs", "grand", "null"])
@pytest.mark.parametrize(
    ("local_side", "winner", "expected_success", "expected_score"),
    [
        ("declarer", "declarer", True, 48),
        ("declarer", "defenders", False, 48),
        ("defenders", "defenders", True, -48),
        ("defenders", "declarer", False, -48),
    ],
)
def test_terminal_utility_orients_contract_and_settlement_to_local_side(
    game_type: str,
    local_side: str,
    winner: str,
    expected_success: bool,
    expected_score: int,
) -> None:
    utility = build_terminal_utility(
        game_type=game_type,
        local_side=local_side,
        winner=winner,
        declarer_settlement_score=48,
        declarer_points=70,
        defender_points=50,
    )

    assert utility.version == TERMINAL_UTILITY_VERSION
    assert utility.local_contract_success is expected_success
    assert utility.local_side_game_score == expected_score
    assert utility.local_side_card_point_margin == (
        None if game_type == "null" else 20 if local_side == "declarer" else -20
    )


@pytest.mark.parametrize("game_type", ["clubs", "grand"])
def test_suit_and_grand_order_success_then_score_then_card_margin(
    game_type: str,
) -> None:
    success = build_terminal_utility(
        game_type=game_type,
        local_side="declarer",
        winner="declarer",
        declarer_settlement_score=24,
        declarer_points=61,
        defender_points=59,
    )
    failed_with_higher_score = build_terminal_utility(
        game_type=game_type,
        local_side="declarer",
        winner="defenders",
        declarer_settlement_score=96,
        declarer_points=90,
        defender_points=30,
    )
    higher_score = build_terminal_utility(
        game_type=game_type,
        local_side="declarer",
        winner="declarer",
        declarer_settlement_score=48,
        declarer_points=61,
        defender_points=59,
    )
    higher_margin = build_terminal_utility(
        game_type=game_type,
        local_side="declarer",
        winner="declarer",
        declarer_settlement_score=48,
        declarer_points=70,
        defender_points=50,
    )

    assert compare_terminal_utilities(success, failed_with_higher_score) > 0
    assert compare_terminal_utilities(higher_score, success) > 0
    assert compare_terminal_utilities(higher_margin, higher_score) > 0


def test_null_order_has_no_invented_card_point_secondary_objective() -> None:
    low_points = build_terminal_utility(
        game_type="null",
        local_side="defenders",
        winner="defenders",
        declarer_settlement_score=-46,
        declarer_points=2,
        defender_points=118,
    )
    high_points = build_terminal_utility(
        game_type="null",
        local_side="defenders",
        winner="defenders",
        declarer_settlement_score=-46,
        declarer_points=50,
        defender_points=70,
    )
    better_score = build_terminal_utility(
        game_type="null",
        local_side="defenders",
        winner="defenders",
        declarer_settlement_score=-59,
        declarer_points=50,
        defender_points=70,
    )

    assert terminal_utility_comparison_key(low_points) == (True, 46)
    assert compare_terminal_utilities(low_points, high_points) == 0
    assert compare_terminal_utilities(better_score, low_points) > 0


@pytest.mark.parametrize("game_type", ["clubs", "grand"])
def test_defender_suit_and_grand_order_uses_local_orientation(game_type: str) -> None:
    defender_success = build_terminal_utility(
        game_type=game_type,
        local_side="defenders",
        winner="defenders",
        declarer_settlement_score=-48,
        declarer_points=50,
        defender_points=70,
    )
    defender_failure = build_terminal_utility(
        game_type=game_type,
        local_side="defenders",
        winner="declarer",
        declarer_settlement_score=96,
        declarer_points=90,
        defender_points=30,
    )

    assert compare_terminal_utilities(defender_success, defender_failure) > 0


def test_declarer_null_order_uses_contract_then_local_settlement() -> None:
    lower_score = build_terminal_utility(
        game_type="null",
        local_side="declarer",
        winner="declarer",
        declarer_settlement_score=23,
        declarer_points=0,
        defender_points=120,
    )
    higher_score = build_terminal_utility(
        game_type="null",
        local_side="declarer",
        winner="declarer",
        declarer_settlement_score=59,
        declarer_points=0,
        defender_points=120,
    )

    assert compare_terminal_utilities(higher_score, lower_score) > 0


def test_terminal_utility_rejects_null_card_point_margin() -> None:
    utility = build_terminal_utility(
        game_type="null",
        local_side="declarer",
        winner="declarer",
        declarer_settlement_score=23,
        declarer_points=0,
        defender_points=120,
    )

    with pytest.raises(ValueError, match="no card-point margin"):
        type(utility)(
            version=1,
            game_type="null",
            local_contract_success=True,
            local_side_game_score=23,
            local_side_card_point_margin=120,
        )
