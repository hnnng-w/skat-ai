from skat_ai.game_declaration import (
    GameDeclaration,
    build_game_declaration_from_input,
    build_serializable_game_declaration,
    get_base_game_value,
    validate_declaration_game_type,
    validate_game_declaration,
    validate_matadors,
)


def test_validate_declaration_game_type_accepts_valid_game_type() -> None:
    validate_declaration_game_type("grand")


def test_validate_declaration_game_type_rejects_invalid_game_type() -> None:
    try:
        validate_declaration_game_type("poker")
    except ValueError as error:
        assert "Invalid declaration game type" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_matadors_accepts_none() -> None:
    validate_matadors(None)


def test_validate_matadors_accepts_non_negative_integer() -> None:
    validate_matadors(3)


def test_validate_matadors_rejects_negative_integer() -> None:
    try:
        validate_matadors(-1)
    except ValueError as error:
        assert "matadors" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_declaration_accepts_grand() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        hand_game=True,
        matadors=2,
    )

    validate_game_declaration(declaration)


def test_validate_game_declaration_rejects_null_with_schneider_announced() -> None:
    declaration = GameDeclaration(
        game_type="null",
        schneider_announced=True,
    )

    try:
        validate_game_declaration(declaration)
    except ValueError as error:
        assert "Null games cannot have schneider announced" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_declaration_rejects_null_with_schwarz_announced() -> None:
    declaration = GameDeclaration(
        game_type="null",
        schwarz_announced=True,
    )

    try:
        validate_game_declaration(declaration)
    except ValueError as error:
        assert "Null games cannot have schwarz announced" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_declaration_rejects_null_with_matadors() -> None:
    declaration = GameDeclaration(
        game_type="null",
        matadors=1,
    )

    try:
        validate_game_declaration(declaration)
    except ValueError as error:
        assert "Null games cannot have matadors" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_game_declaration_from_input_defaults() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
        }
    )

    assert declaration == GameDeclaration(
        game_type="grand",
        hand_game=False,
        ouvert=False,
        schneider_announced=False,
        schwarz_announced=False,
        matadors=None,
    )


def test_build_game_declaration_from_input_reads_fields() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "hand_game": True,
            "ouvert": False,
            "schneider_announced": True,
            "schwarz_announced": False,
            "matadors": 3,
        }
    )

    assert declaration == GameDeclaration(
        game_type="grand",
        hand_game=True,
        ouvert=False,
        schneider_announced=True,
        schwarz_announced=False,
        matadors=3,
    )


def test_build_game_declaration_does_not_infer_matadors_from_defender_hand() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "defender",
            "hand": ["CJ", "SJ", "H7"],
            "skat": [],
            "completed_tricks": [],
        }
    )

    assert declaration.matadors is None


def test_build_game_declaration_does_not_infer_matadors_from_unknown_hand() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "unknown",
            "hand": ["CJ", "SJ", "H7"],
            "skat": [],
            "completed_tricks": [],
        }
    )

    assert declaration.matadors is None


def test_build_game_declaration_infers_matadors_from_local_declarer_hand() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "hand": ["CJ", "SJ", "HJ", "H7"],
            "skat": [],
            "completed_tricks": [],
        }
    )

    assert declaration.matadors == 3


def test_build_game_declaration_keeps_top_level_matadors_for_non_declarers() -> None:
    for player_role in ["defender", "unknown"]:
        declaration = build_game_declaration_from_input(
            {
                "game_type": "grand",
                "player_role": player_role,
                "hand": ["CJ", "SJ", "H7"],
                "skat": [],
                "matadors": 4,
                "completed_tricks": [],
            }
        )

        assert declaration.matadors == 4


def test_build_game_declaration_keeps_nested_matadors_for_defender() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "defender",
            "hand": ["CJ", "SJ", "H7"],
            "skat": [],
            "matadors": 4,
            "game_declaration": {
                "matadors": 1,
            },
            "completed_tricks": [],
        }
    )

    assert declaration.matadors == 1


def test_build_game_declaration_infers_matadors_from_completed_trick_ownership() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "hand": ["CJ"],
            "skat": [],
            "completed_tricks": [
                {
                    "cards": ["SJ", "H7", "HJ"],
                    "players": ["me", "left", "right"],
                }
            ],
        }
    )

    assert declaration.matadors == 2


def test_build_game_declaration_ignores_ambiguous_completed_trick_ownership() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "hand": [],
            "skat": [],
            "completed_tricks": [
                {
                    "cards": ["CJ", "SJ", "HJ"],
                }
            ],
        }
    )

    assert declaration.matadors is None


def test_build_game_declaration_uses_declarer_skat_when_ownership_is_known() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "hand": ["CJ"],
            "skat": ["SJ"],
            "completed_tricks": [
                {
                    "cards": ["C7", "HJ", "D7"],
                    "players": ["me", "left", "right"],
                }
            ],
        }
    )

    assert declaration.matadors == 2


def test_build_game_declaration_does_not_infer_matadors_from_defender_skat() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "defender",
            "hand": [],
            "skat": ["CJ", "SJ"],
            "analysis_mode": "post_game_review",
            "skat_visibility": "known_post_game",
            "completed_tricks": [],
        }
    )

    assert declaration.matadors is None


def test_build_game_declaration_keeps_live_declarer_skat_inference() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "hand": ["CJ"],
            "skat": ["SJ", "HJ"],
            "analysis_mode": "live_decision",
            "skat_visibility": "unknown",
            "completed_tricks": [],
        }
    )

    assert declaration.matadors == 3


def test_build_game_declaration_hand_game_uses_known_local_declarer_context() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "hand_game": True,
            "hand": ["CJ"],
            "skat": ["SJ"],
            "completed_tricks": [
                {
                    "cards": ["C7", "HJ", "D7"],
                    "players": ["me", "left", "right"],
                }
            ],
        }
    )

    assert declaration.hand_game is True
    assert declaration.matadors == 2


def test_build_game_declaration_keeps_explicit_matadors_over_ownership_inference() -> None:
    declaration = build_game_declaration_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "hand": ["CJ"],
            "skat": [],
            "matadors": 4,
            "game_declaration": {
                "matadors": 1,
            },
            "completed_tricks": [
                {
                    "cards": ["SJ", "H7", "HJ"],
                    "players": ["me", "left", "right"],
                }
            ],
        }
    )

    assert declaration.matadors == 1


def test_build_serializable_game_declaration() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        hand_game=True,
        ouvert=False,
        schneider_announced=True,
        schwarz_announced=False,
        matadors=3,
    )

    result = build_serializable_game_declaration(declaration)

    assert result == {
        "game_type": "grand",
        "hand_game": True,
        "ouvert": False,
        "schneider_announced": True,
        "schwarz_announced": False,
        "matadors": 3,
        "bid_value": None,
    }


def test_get_base_game_value() -> None:
    assert get_base_game_value("clubs") == 12
    assert get_base_game_value("spades") == 11
    assert get_base_game_value("hearts") == 10
    assert get_base_game_value("diamonds") == 9
    assert get_base_game_value("grand") == 24


def test_get_base_game_value_rejects_null() -> None:
    try:
        get_base_game_value("null")
    except ValueError as error:
        assert "Null games do not use" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_game_declaration_defaults_bid_value_to_none() -> None:
    declaration = GameDeclaration(game_type="grand")

    assert declaration.bid_value is None

def test_game_declaration_accepts_bid_value() -> None:
    declaration = GameDeclaration(
        game_type="grand",
        bid_value=72,
    )

    assert declaration.bid_value == 72

def test_validate_game_declaration_rejects_non_positive_bid_value() -> None:
    try:
        validate_game_declaration(
            GameDeclaration(
                game_type="grand",
                bid_value=0,
            )
        )
    except ValueError as error:
        assert "bid_value must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
