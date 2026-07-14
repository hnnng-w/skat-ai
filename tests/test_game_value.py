import pytest

from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_value import (
    build_game_value_summary,
    calculate_game_value,
    calculate_suit_or_grand_game_level,
    get_matador_multiplier,
    get_modifier_multiplier,
    get_null_game_value,
    is_null_game,
)


def test_is_null_game() -> None:
    assert is_null_game(GameDeclaration(game_type="null")) is True
    assert is_null_game(GameDeclaration(game_type="grand")) is False


def test_get_null_game_value() -> None:
    assert get_null_game_value(GameDeclaration(game_type="null")) == 23
    assert get_null_game_value(GameDeclaration(game_type="null", hand_game=True)) == 35
    assert get_null_game_value(GameDeclaration(game_type="null", ouvert=True)) == 46
    assert (
        get_null_game_value(
            GameDeclaration(game_type="null", hand_game=True, ouvert=True)
        )
        == 59
    )


def test_get_null_game_value_rejects_non_null_game() -> None:
    try:
        get_null_game_value(GameDeclaration(game_type="grand"))
    except ValueError as error:
        assert "Only null games use null game values" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_matador_multiplier_returns_none_when_unknown() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        matadors=None,
    )

    assert get_matador_multiplier(declaration) is None


def test_get_matador_multiplier_from_matadors() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        matadors=2,
    )

    assert get_matador_multiplier(declaration) == 3


def test_get_modifier_multiplier_defaults_to_zero() -> None:
    declaration = GameDeclaration(
        game_type="grand",
    )

    assert get_modifier_multiplier(declaration) == 0


def test_get_modifier_multiplier_counts_modifiers() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        hand_game=True,
        schneider_announced=True,
        schwarz_announced=True,
        ouvert=True,
    )

    assert get_modifier_multiplier(declaration) == 4


def test_calculate_suit_or_grand_game_level() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        matadors=2,
        hand_game=True,
        schneider_announced=True,
    )

    assert calculate_suit_or_grand_game_level(declaration) == 5


def test_calculate_suit_or_grand_game_level_rejects_null() -> None:
    try:
        calculate_suit_or_grand_game_level(GameDeclaration(game_type="null"))
    except ValueError as error:
        assert "Null games do not use" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_calculate_game_value_for_grand() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        matadors=2,
    )

    assert calculate_game_value(declaration) == 72


def test_calculate_game_value_for_suit_game() -> None:
    declaration = GameDeclaration(
        game_type="hearts",
        matadors=1,
        hand_game=True,
    )

    assert calculate_game_value(declaration) == 30


@pytest.mark.parametrize(
    ("game_type", "expected_base_value"),
    [
        ("clubs", 12),
        ("spades", 11),
        ("hearts", 10),
        ("diamonds", 9),
        ("grand", 24),
    ],
)
def test_suit_and_grand_game_values_use_base_value_multipliers(
    game_type: str,
    expected_base_value: int,
) -> None:
    declaration = GameDeclaration(
        game_type=game_type,
        matadors=1,
    )

    summary = build_game_value_summary(declaration)

    assert calculate_game_value(declaration) == expected_base_value * 2
    assert summary["base_value"] == expected_base_value
    assert summary["game_level"] == 2
    assert summary["game_value"] == expected_base_value * 2


@pytest.mark.parametrize(
    ("declaration_values", "expected_modifier_multiplier"),
    [
        ({"hand_game": True}, 1),
        ({"schneider_announced": True}, 2),
        ({"schwarz_announced": True}, 3),
        ({"ouvert": True}, 4),
    ],
)
def test_canonical_declarations_produce_cumulative_levels(
    declaration_values: dict[str, bool],
    expected_modifier_multiplier: int,
) -> None:
    declaration = GameDeclaration(
        game_type="grand",
        matadors=1,
        **declaration_values,
    )

    assert get_modifier_multiplier(declaration) == expected_modifier_multiplier
    assert calculate_suit_or_grand_game_level(declaration) == (
        2 + expected_modifier_multiplier
    )


def test_calculate_game_value_for_null() -> None:
    declaration = GameDeclaration(
        game_type="null",
        hand_game=True,
        ouvert=True,
    )

    assert calculate_game_value(declaration) == 59


def test_build_game_value_summary_for_grand() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        matadors=2,
        hand_game=True,
        schneider_announced=False,
        schwarz_announced=False,
        ouvert=False,
    )

    summary = build_game_value_summary(declaration)

    assert summary == {
        "game_type": "grand",
        "is_null_game": False,
        "base_value": 24,
        "game_level": 4,
        "game_value": 96,
        "details": {
            "matadors": 2,
            "matador_multiplier": 3,
            "hand_game": True,
            "schneider_announced": False,
            "schwarz_announced": False,
            "ouvert": False,
            "modifier_multiplier": 1,
            "is_complete": True,
        },
    }


def test_build_game_value_summary_for_null() -> None:
    declaration = GameDeclaration(
        game_type="null",
        hand_game=True,
        ouvert=True,
    )

    summary = build_game_value_summary(declaration)

    assert summary == {
        "game_type": "null",
        "is_null_game": True,
        "base_value": None,
        "game_level": None,
        "game_value": 59,
        "details": {
            "hand_game": True,
            "ouvert": True,
        },
    }

def test_calculate_suit_or_grand_game_level_rejects_unknown_matadors() -> None:
    try:
        calculate_suit_or_grand_game_level(
            GameDeclaration(game_type="grand", matadors=None)
        )
    except ValueError as error:
        assert "without matadors" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
