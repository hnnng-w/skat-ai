import pytest

from skat_ai.game_declaration import GameDeclaration
from skat_ai.impossible_null_settlement import (
    ImpossibleNullSettlementSelection,
    build_impossible_null_settlement_selection_from_input,
    build_impossible_null_settlement_summary,
    build_serializable_impossible_null_settlement_summary,
)


@pytest.mark.parametrize(
    ("game_type", "base_value"),
    [
        ("clubs", 12),
        ("spades", 11),
        ("hearts", 10),
        ("diamonds", 9),
        ("grand", 24),
    ],
)
def test_replacement_summary_uses_official_base_values(
    game_type: str,
    base_value: int,
) -> None:
    summary = build_impossible_null_settlement_summary(
        selection=ImpossibleNullSettlementSelection(game_type, 1),
        original_declaration=GameDeclaration(game_type="null", bid_value=24),
    )

    assert summary.base_value == base_value
    assert summary.minimum_game_value == base_value * 2
    assert summary.required_game_value >= 24


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_hand"),
    [
        (False, False, False),
        (True, False, True),
        (False, True, False),
        (True, True, True),
    ],
)
def test_replacement_inherits_hand_but_not_null_ouvert(
    hand_game: bool,
    ouvert: bool,
    expected_hand: bool,
) -> None:
    summary = build_impossible_null_settlement_summary(
        selection=ImpossibleNullSettlementSelection("clubs", 1),
        original_declaration=GameDeclaration(
            game_type="null",
            hand_game=hand_game,
            ouvert=ouvert,
            bid_value=60,
        ),
    )

    assert summary.hand_game is expected_hand
    assert "ouvert" not in build_serializable_impossible_null_settlement_summary(
        summary
    )


def test_replacement_value_rounds_bid_up() -> None:
    summary = build_impossible_null_settlement_summary(
        selection=ImpossibleNullSettlementSelection("clubs", 1),
        original_declaration=GameDeclaration(game_type="null", bid_value=25),
    )

    assert summary.minimum_game_value == 24
    assert summary.required_game_value == 36


def test_hand_minimum_replacement_value_can_exceed_rounded_bid() -> None:
    summary = build_impossible_null_settlement_summary(
        selection=ImpossibleNullSettlementSelection("clubs", 11),
        original_declaration=GameDeclaration(
            game_type="null",
            hand_game=True,
            bid_value=36,
        ),
    )

    assert summary.minimum_game_value == 156
    assert summary.required_game_value == 156


@pytest.mark.parametrize(
    ("game_type", "matadors"),
    [("clubs", 1), ("clubs", 11), ("grand", 1), ("grand", 4)],
)
def test_replacement_accepts_matador_boundaries(
    game_type: str,
    matadors: int,
) -> None:
    assert ImpossibleNullSettlementSelection(game_type, matadors).matadors == matadors


@pytest.mark.parametrize(
    ("game_type", "matadors"),
    [("null", 1), ("clubs", 0), ("clubs", 12), ("grand", 0), ("grand", 5)],
)
def test_replacement_rejects_invalid_game_type_or_matadors(
    game_type: str,
    matadors: int,
) -> None:
    with pytest.raises(ValueError):
        ImpossibleNullSettlementSelection(game_type, matadors)


def test_replacement_input_requires_complete_strict_object() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        build_impossible_null_settlement_selection_from_input(
            {"impossible_null_settlement": {"replacement_game_type": "clubs"}}
        )

    with pytest.raises(ValueError, match="unsupported keys"):
        build_impossible_null_settlement_selection_from_input(
            {
                "impossible_null_settlement": {
                    "replacement_game_type": "clubs",
                    "matadors": 1,
                    "ouvert": True,
                }
            }
        )
