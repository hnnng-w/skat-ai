import pytest

from skat_ai.input_validation import (
    validate_boolean,
    validate_cards,
    validate_completed_tricks,
    validate_current_trick,
    validate_game_type,
    validate_next_player,
    validate_no_duplicate_cards,
    validate_non_negative_integer,
    validate_optional_analysis_metadata,
    validate_optional_game_declaration,
    validate_optional_opponent_policies,
    validate_optional_player_profile,
    validate_optional_profile_preset_settings,
    validate_optional_random_seed,
    validate_player_position,
    validate_player_role,
    validate_position_input,
    validate_positive_integer,
    validate_required_keys,
    validate_trick_leader,
    validate_trick_leader_matches_current_trick,
)


def build_valid_input() -> dict[str, object]:
    return {
        "game_type": "spades",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "right",
        "hand": ["C7", "SA", "S7"],
        "current_trick": ["CA"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
    }


def build_six_point_completed_trick() -> dict[str, object]:
    return {
        "cards": ["CJ", "SJ", "DJ"],
        "winner_role": "declarer",
    }


@pytest.mark.parametrize(
    ("field_name", "valid_value"),
    [
        ("left_hand_size", 1),
        ("right_hand_size", 1),
        ("sample_count", 1),
        ("random_seed", -42),
        ("declarer_points", 120),
        ("defender_points", 120),
    ],
)
def test_validate_position_input_accepts_strict_integer_fields(
    field_name: str,
    valid_value: object,
) -> None:
    data = build_valid_input()
    data[field_name] = valid_value

    validate_position_input(data)


@pytest.mark.parametrize(
    "field_name",
    [
        "left_hand_size",
        "right_hand_size",
        "sample_count",
        "random_seed",
        "declarer_points",
        "defender_points",
    ],
)
@pytest.mark.parametrize("invalid_value", [True, False, 1.5, "1"])
def test_validate_position_input_rejects_non_strict_integer_fields(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_valid_input()
    data[field_name] = invalid_value

    with pytest.raises(ValueError, match=field_name):
        validate_position_input(data)


@pytest.mark.parametrize(
    "field_name",
    [
        "left_hand_size",
        "right_hand_size",
        "sample_count",
        "declarer_points",
        "defender_points",
    ],
)
def test_validate_position_input_rejects_null_for_non_nullable_integer_fields(
    field_name: str,
) -> None:
    data = build_valid_input()
    data[field_name] = None

    with pytest.raises(ValueError, match=field_name):
        validate_position_input(data)


def test_validate_position_input_accepts_null_random_seed() -> None:
    data = build_valid_input()
    data["random_seed"] = None

    validate_position_input(data)


@pytest.mark.parametrize("field_name", ["random_seed", "declarer_points", "defender_points"])
def test_validate_position_input_accepts_omitted_optional_numeric_fields(
    field_name: str,
) -> None:
    data = build_valid_input()
    data.pop(field_name)

    validate_position_input(data)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("left_hand_size", 0),
        ("right_hand_size", 0),
        ("sample_count", 0),
        ("declarer_points", -1),
        ("defender_points", -1),
    ],
)
def test_validate_position_input_preserves_lower_integer_boundaries(
    field_name: str,
    invalid_value: object,
) -> None:
    data = build_valid_input()
    data[field_name] = invalid_value

    with pytest.raises(ValueError, match=field_name):
        validate_position_input(data)


def test_validate_position_input_accepts_negative_random_seed() -> None:
    data = build_valid_input()
    data["random_seed"] = -1

    validate_position_input(data)


@pytest.mark.parametrize(
    ("declarer_points", "defender_points"),
    [
        (59, 60),
        (70, 50),
    ],
)
def test_validate_position_input_accepts_explicit_known_point_totals_at_or_below_120(
    declarer_points: int,
    defender_points: int,
) -> None:
    data = build_valid_input()
    data["declarer_points"] = declarer_points
    data["defender_points"] = defender_points

    validate_position_input(data)


def test_validate_position_input_rejects_explicit_known_point_total_above_120() -> None:
    data = build_valid_input()
    data["declarer_points"] = 70
    data["defender_points"] = 51

    with pytest.raises(ValueError, match="Known card points cannot exceed 120"):
        validate_position_input(data)


@pytest.mark.parametrize("field_name", ["declarer_points", "defender_points"])
def test_validate_position_input_accepts_one_omitted_side_point_field(
    field_name: str,
) -> None:
    data = build_valid_input()
    data["declarer_points"] = 30
    data["defender_points"] = 40
    data.pop(field_name)

    validate_position_input(data)


def test_validate_position_input_counts_completed_trick_points_once() -> None:
    data = build_valid_input()
    data["completed_tricks"] = [build_six_point_completed_trick()]
    data["declarer_points"] = 114
    data["defender_points"] = 0

    validate_position_input(data)


def test_validate_position_input_rejects_explicit_plus_completed_points_above_120() -> None:
    data = build_valid_input()
    data["completed_tricks"] = [build_six_point_completed_trick()]
    data["declarer_points"] = 115
    data["defender_points"] = 0

    with pytest.raises(ValueError, match="Known card points cannot exceed 120"):
        validate_position_input(data)


def test_validate_position_input_rejects_boolean_points_before_aggregate_total() -> None:
    data = build_valid_input()
    data["completed_tricks"] = [build_six_point_completed_trick()]
    data["declarer_points"] = True
    data["defender_points"] = 120

    with pytest.raises(ValueError) as error:
        validate_position_input(data)

    error_message = str(error.value)
    assert "declarer_points must be a non-negative integer" in error_message
    assert "Known card points" not in error_message


def test_validate_position_input_normalizes_declarer_missing_to_me() -> None:
    data = build_valid_input()

    validate_position_input(data)

    assert data["declarer_player"] == "me"


def test_validate_position_input_accepts_local_declarer_identity() -> None:
    data = build_valid_input()
    data["declarer_player"] = "me"

    validate_position_input(data)

    assert data["declarer_player"] == "me"


@pytest.mark.parametrize("declarer_player", ["unknown", "left", "right"])
def test_validate_position_input_rejects_invalid_local_declarer_identity(
    declarer_player: str,
) -> None:
    data = build_valid_input()
    data["declarer_player"] = declarer_player

    with pytest.raises(ValueError, match="player_role='declarer'"):
        validate_position_input(data)


@pytest.mark.parametrize("declarer_player", ["left", "right"])
def test_validate_position_input_accepts_local_defender_identity(
    declarer_player: str,
) -> None:
    data = build_valid_input()
    data["player_role"] = "defender"
    data["declarer_player"] = declarer_player

    validate_position_input(data)

    assert data["declarer_player"] == declarer_player


@pytest.mark.parametrize("declarer_player", [None, "unknown", "me"])
def test_validate_position_input_rejects_invalid_local_defender_identity(
    declarer_player: str | None,
) -> None:
    data = build_valid_input()
    data["player_role"] = "defender"
    if declarer_player is None:
        data.pop("declarer_player", None)
    else:
        data["declarer_player"] = declarer_player

    with pytest.raises(ValueError, match="player_role='defender'"):
        validate_position_input(data)


def test_validate_position_input_normalizes_unknown_role_missing_to_unknown() -> None:
    data = build_valid_input()
    data["player_role"] = "unknown"

    validate_position_input(data)

    assert data["declarer_player"] == "unknown"


def test_validate_position_input_accepts_unknown_role_unknown_declarer() -> None:
    data = build_valid_input()
    data["player_role"] = "unknown"
    data["declarer_player"] = "unknown"

    validate_position_input(data)

    assert data["declarer_player"] == "unknown"


@pytest.mark.parametrize("declarer_player", ["me", "left", "right"])
def test_validate_position_input_rejects_unknown_role_concrete_declarer(
    declarer_player: str,
) -> None:
    data = build_valid_input()
    data["player_role"] = "unknown"
    data["declarer_player"] = declarer_player

    with pytest.raises(ValueError, match="player_role='unknown'"):
        validate_position_input(data)


def test_validate_required_keys_accepts_complete_input() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA"],
        "current_trick": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
    }

    validate_required_keys(data)


def test_validate_required_keys_rejects_missing_keys() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
    }

    try:
        validate_required_keys(data)
    except ValueError as error:
        assert "Missing required input keys" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_type_accepts_valid_game_type() -> None:
    validate_game_type("grand")


def test_validate_game_type_rejects_invalid_game_type() -> None:
    try:
        validate_game_type("invalid_game")
    except ValueError as error:
        assert "Invalid game type" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_player_role_accepts_valid_player_role() -> None:
    validate_player_role("declarer")


def test_validate_player_role_rejects_invalid_player_role() -> None:
    try:
        validate_player_role("attacker")
    except ValueError as error:
        assert "Invalid player role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_cards_accepts_valid_cards() -> None:
    validate_cards(["SA", "S10", "D7"], "hand")


def test_validate_cards_rejects_invalid_cards() -> None:
    try:
        validate_cards(["SA", "S1O"], "hand")
    except ValueError as error:
        assert "Invalid cards in hand" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_no_duplicate_cards_accepts_unique_cards() -> None:
    data = {
        "hand": ["SA", "S10"],
        "current_trick": ["H7"],
        "played_cards": ["D7"],
        "skat": ["C7", "C8"],
    }

    validate_no_duplicate_cards(data)


def test_validate_no_duplicate_cards_rejects_duplicates() -> None:
    data = {
        "hand": ["SA", "S10"],
        "current_trick": ["SA"],
        "played_cards": [],
        "skat": [],
    }

    try:
        validate_no_duplicate_cards(data)
    except ValueError as error:
        assert "Duplicate known cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_current_trick_accepts_up_to_two_cards() -> None:
    validate_current_trick([])
    validate_current_trick(["SA"])
    validate_current_trick(["SA", "S10"])


def test_validate_current_trick_rejects_three_cards() -> None:
    try:
        validate_current_trick(["SA", "S10", "S9"])
    except ValueError as error:
        assert "at most 2 cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_positive_integer_accepts_positive_integer() -> None:
    validate_positive_integer(100, "sample_count")


def test_validate_positive_integer_rejects_zero() -> None:
    try:
        validate_positive_integer(0, "sample_count")
    except ValueError as error:
        assert "positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


@pytest.mark.parametrize("value", [True, False])
def test_validate_positive_integer_rejects_boolean(value: bool) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        validate_positive_integer(value, "sample_count")


def test_validate_optional_random_seed_accepts_integer_or_none() -> None:
    validate_optional_random_seed(42)
    validate_optional_random_seed(None)


def test_validate_optional_random_seed_rejects_string() -> None:
    try:
        validate_optional_random_seed("42")
    except ValueError as error:
        assert "random_seed" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


@pytest.mark.parametrize("value", [True, False])
def test_validate_optional_random_seed_rejects_boolean(value: bool) -> None:
    with pytest.raises(ValueError, match="random_seed"):
        validate_optional_random_seed(value)


def test_validate_boolean_accepts_bool() -> None:
    validate_boolean(True, "use_basic_opponent_strategy")
    validate_boolean(False, "use_basic_opponent_strategy")


def test_validate_boolean_rejects_non_bool() -> None:
    try:
        validate_boolean("true", "use_basic_opponent_strategy")
    except ValueError as error:
        assert "boolean" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_valid_input() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    validate_position_input(data)


def test_validate_position_input_rejects_invalid_input() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA", "S1O"],
        "current_trick": [],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Invalid cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_player_position_accepts_valid_player_position() -> None:
    validate_player_position("forehand")
    validate_player_position("middlehand")
    validate_player_position("rearhand")
    validate_player_position("unknown")


def test_validate_player_position_rejects_invalid_player_position() -> None:
    try:
        validate_player_position("button")
    except ValueError as error:
        assert "Invalid player position" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_trick_leader_accepts_valid_trick_leader() -> None:
    validate_trick_leader("me")
    validate_trick_leader("left")
    validate_trick_leader("right")
    validate_trick_leader("unknown")


def test_validate_trick_leader_rejects_invalid_trick_leader() -> None:
    try:
        validate_trick_leader("opponent")
    except ValueError as error:
        assert "Invalid trick leader" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_trick_leader_matches_empty_current_trick() -> None:
    validate_trick_leader_matches_current_trick("me", [])
    validate_trick_leader_matches_current_trick("left", [])
    validate_trick_leader_matches_current_trick("right", [])
    validate_trick_leader_matches_current_trick("unknown", [])


def test_validate_trick_leader_rejects_concrete_phase_contradiction() -> None:
    try:
        validate_trick_leader_matches_current_trick(
            trick_leader="left",
            current_trick=["S7"],
            next_player="me",
        )
    except ValueError as error:
        assert "turn phase is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


@pytest.mark.parametrize(
    ("trick_leader", "current_trick", "next_player"),
    [
        ("me", [], "me"),
        ("me", ["CA"], "left"),
        ("me", ["CA", "C10"], "right"),
        ("left", [], "left"),
        ("left", ["CA"], "right"),
        ("left", ["CA", "C10"], "me"),
        ("right", [], "right"),
        ("right", ["CA"], "me"),
        ("right", ["CA", "C10"], "left"),
    ],
)
def test_validate_position_input_accepts_canonical_turn_phases(
    trick_leader: str,
    current_trick: list[str],
    next_player: str,
) -> None:
    data = build_valid_input()
    data["trick_leader"] = trick_leader
    data["current_trick"] = current_trick
    data["next_player"] = next_player

    validate_position_input(data)


def test_validate_position_input_accepts_empty_left_lead() -> None:
    data = build_valid_input()
    data["trick_leader"] = "left"
    data["current_trick"] = []
    data["next_player"] = "left"

    validate_position_input(data)


def test_validate_position_input_accepts_empty_right_lead() -> None:
    data = build_valid_input()
    data["trick_leader"] = "right"
    data["current_trick"] = []
    data["next_player"] = "right"

    validate_position_input(data)


def test_validate_position_input_derives_unknown_next_from_concrete_leader() -> None:
    data = build_valid_input()
    data["trick_leader"] = "right"
    data["current_trick"] = ["CA"]
    data["next_player"] = "unknown"

    validate_position_input(data)


def test_validate_position_input_derives_missing_next_from_concrete_leader() -> None:
    data = build_valid_input()
    data["trick_leader"] = "left"
    data["current_trick"] = ["CA", "C10"]
    data.pop("next_player")

    validate_position_input(data)


def test_validate_position_input_derives_unknown_leader_from_concrete_next() -> None:
    data = build_valid_input()
    data["trick_leader"] = "unknown"
    data["current_trick"] = ["CA"]
    data["next_player"] = "me"

    validate_position_input(data)


def test_validate_position_input_derives_missing_leader_from_concrete_next() -> None:
    data = build_valid_input()
    data.pop("trick_leader")
    data["current_trick"] = ["CA", "C10"]
    data["next_player"] = "right"

    validate_position_input(data)


def test_validate_position_input_rejects_explicit_phase_contradiction() -> None:
    data = build_valid_input()
    data["trick_leader"] = "left"
    data["current_trick"] = ["CA"]
    data["next_player"] = "me"

    with pytest.raises(ValueError, match="turn phase is inconsistent"):
        validate_position_input(data)


def test_validate_position_input_rejects_non_empty_unresolved_phase() -> None:
    data = build_valid_input()
    data["trick_leader"] = "unknown"
    data["current_trick"] = ["CA"]
    data["next_player"] = "unknown"

    with pytest.raises(ValueError, match="Cannot determine turn phase"):
        validate_position_input(data)


def test_validate_position_input_accepts_position_fields() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["D7"],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    validate_position_input(data)


def test_validate_position_input_rejects_invalid_position_fields() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "button",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["D7"],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Invalid player position" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_tricks_accepts_valid_completed_trick() -> None:
    validate_completed_tricks(
        [
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ]
    )


def test_validate_completed_tricks_rejects_invalid_card() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C1O", "CK"],
                    "winner_role": "declarer",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid cards in completed_tricks" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_tricks_rejects_invalid_winner_role() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C10", "CK"],
                    "winner_role": "unknown",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid completed trick winner role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_next_player_accepts_valid_next_player() -> None:
    validate_next_player("me")
    validate_next_player("left")
    validate_next_player("right")
    validate_next_player("unknown")


def test_validate_next_player_rejects_invalid_next_player() -> None:
    try:
        validate_next_player("dealer")
    except ValueError as error:
        assert "Invalid next player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_non_negative_integer_accepts_zero_and_positive_integer() -> None:
    validate_non_negative_integer(0, "declarer_points")
    validate_non_negative_integer(10, "declarer_points")


def test_validate_non_negative_integer_rejects_negative_integer() -> None:
    try:
        validate_non_negative_integer(-1, "declarer_points")
    except ValueError as error:
        assert "non-negative integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


@pytest.mark.parametrize("value", [True, False])
def test_validate_non_negative_integer_rejects_boolean(value: bool) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        validate_non_negative_integer(value, "declarer_points")


def test_validate_completed_tricks_accepts_players_and_winner_player() -> None:
    validate_completed_tricks(
        [
            {
                "cards": ["CA", "C10", "CK"],
                "players": ["left", "me", "right"],
                "winner_role": "defenders",
                "winner_player": "left",
            }
        ]
    )


def test_validate_completed_tricks_rejects_invalid_players() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C10", "CK"],
                    "players": ["left", "me", "dealer"],
                    "winner_role": "defenders",
                    "winner_player": "left",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid completed trick players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_tricks_rejects_invalid_winner_player() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C10", "CK"],
                    "players": ["left", "me", "right"],
                    "winner_role": "defenders",
                    "winner_player": "dealer",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid completed trick winner player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_player_profile_accepts_valid_profile() -> None:
    validate_optional_player_profile(
        {
            "games_played": 1240,
            "solo_rate": 0.31,
            "solo_win_rate": 0.66,
        },
        "left_player_profile",
    )


def test_validate_optional_player_profile_rejects_negative_games_played() -> None:
    try:
        validate_optional_player_profile(
            {
                "games_played": -1,
            },
            "left_player_profile",
        )
    except ValueError as error:
        assert "games_played" in str(error)
        assert "non-negative integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


@pytest.mark.parametrize(
    "field_name",
    [
        "games_played",
        "solo_games_played",
        "defender_games_played",
    ],
)
def test_validate_optional_player_profile_rejects_boolean_integer_fields(
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        validate_optional_player_profile(
            {
                field_name: True,
            },
            "left_player_profile",
        )


def test_validate_optional_player_profile_rejects_invalid_rate() -> None:
    try:
        validate_optional_player_profile(
            {
                "solo_rate": 1.5,
            },
            "left_player_profile",
        )
    except ValueError as error:
        assert "solo_rate" in str(error)
        assert "between 0 and 1" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


@pytest.mark.parametrize(
    "field_name",
    [
        "solo_rate",
        "solo_win_rate",
        "hand_game_rate",
        "suit_game_rate",
        "grand_rate",
        "null_game_rate",
        "defender_win_rate",
    ],
)
def test_validate_optional_player_profile_rejects_boolean_rate_fields(
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        validate_optional_player_profile(
            {
                field_name: False,
            },
            "left_player_profile",
        )


def test_validate_optional_player_profile_accepts_zero_and_rate_boundaries() -> None:
    validate_optional_player_profile(
        {
            "games_played": 0,
            "solo_games_played": 0,
            "defender_games_played": 0,
            "solo_rate": 0,
            "solo_win_rate": 1,
            "hand_game_rate": 0.0,
            "suit_game_rate": 1.0,
            "grand_rate": 0,
            "null_game_rate": 1,
            "defender_win_rate": 0.5,
        },
        "left_player_profile",
    )


def test_validate_optional_analysis_metadata_accepts_valid_metadata() -> None:
    validate_optional_analysis_metadata(
        {
            "analysis_mode": "post_game_review",
            "skat_visibility": "known_post_game",
            "game_end_reason": "normal_completion",
            "left_player_profile": {
                "games_played": 1240,
                "solo_rate": 0.31,
            },
        }
    )


def test_validate_optional_analysis_metadata_accepts_valid_left_and_right_profiles() -> None:
    validate_optional_analysis_metadata(
        {
            "left_player_profile": {
                "games_played": 1240,
                "solo_games_played": 380,
                "defender_games_played": 860,
                "solo_rate": 0.31,
                "solo_win_rate": 0.66,
                "hand_game_rate": 0.08,
                "suit_game_rate": 0.46,
                "grand_rate": 0.22,
                "null_game_rate": 0.04,
                "defender_win_rate": 0.54,
            },
            "right_player_profile": {
                "games_played": 520,
                "solo_games_played": 160,
                "defender_games_played": 360,
                "solo_rate": 0.28,
                "solo_win_rate": 0.59,
                "hand_game_rate": 0.05,
                "suit_game_rate": 0.51,
                "grand_rate": 0.18,
                "null_game_rate": 0.06,
                "defender_win_rate": 0.49,
            },
        }
    )


def test_validate_optional_analysis_metadata_rejects_invalid_analysis_mode() -> None:
    try:
        validate_optional_analysis_metadata(
            {
                "analysis_mode": "future_mode",
            }
        )
    except ValueError as error:
        assert "Invalid analysis mode" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_opponent_policies_accepts_valid_policies() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "basic_trick_play",
        }
    )


def test_validate_optional_opponent_policies_rejects_invalid_policy() -> None:
    try:
        validate_optional_opponent_policies(
            {
                "opponent_lead_policy": "reckless",
            }
        )
    except ValueError as error:
        assert "Invalid opponent card policy" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_opponent_policies_accepts_basic_defender_response() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_response_policy": "basic_defender_response",
        }
    )

def test_validate_optional_opponent_policies_accepts_basic_defender_lead() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_lead_policy": "basic_defender_lead",
        }
    )

def test_validate_optional_opponent_policies_accepts_preset() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_policy_preset": "cautious_defender",
        }
    )


def test_validate_optional_opponent_policies_rejects_invalid_preset() -> None:
    try:
        validate_optional_opponent_policies(
            {
                "opponent_policy_preset": "reckless",
            }
        )
    except ValueError as error:
        assert "Invalid opponent policy preset" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_profile_preset_settings_accepts_boolean() -> None:
    validate_optional_profile_preset_settings(
        {
            "use_profile_presets": True,
        }
    )


def test_validate_optional_profile_preset_settings_rejects_non_boolean() -> None:
    try:
        validate_optional_profile_preset_settings(
            {
                "use_profile_presets": "yes",
            }
        )
    except ValueError as error:
        assert "use_profile_presets" in str(error)
        assert "boolean" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_game_declaration_accepts_valid_declaration() -> None:
    validate_optional_game_declaration(
        {
            "game_type": "grand",
            "hand_game": True,
            "schneider_announced": True,
            "matadors": 2,
        }
    )


def test_validate_optional_game_declaration_accepts_valid_nested_declaration() -> None:
    validate_optional_game_declaration(
        {
            "game_type": "grand",
            "game_declaration": {
                "hand_game": True,
                "ouvert": False,
                "schneider_announced": True,
                "schwarz_announced": False,
                "matadors": 2,
                "bid_value": 48,
                "comment": "accepted metadata",
            },
        }
    )


def test_validate_optional_game_declaration_accepts_nested_numeric_nulls() -> None:
    validate_optional_game_declaration(
        {
            "game_type": "grand",
            "game_declaration": {
                "matadors": None,
                "bid_value": None,
            },
        }
    )


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "expected_error"),
    [
        ("hand_game", "true", "must be a boolean"),
        ("ouvert", None, "must be a boolean"),
        ("schneider_announced", 1, "must be a boolean"),
        ("schwarz_announced", 0, "must be a boolean"),
        ("matadors", True, "matadors"),
        ("matadors", -1, "matadors"),
        ("matadors", 1.5, "matadors"),
        ("bid_value", True, "bid_value"),
        ("bid_value", 0, "bid_value"),
        ("bid_value", -1, "bid_value"),
        ("bid_value", 1.5, "bid_value"),
    ],
)
def test_validate_optional_game_declaration_rejects_invalid_top_level_and_nested_values(
    field_name: str,
    invalid_value: object,
    expected_error: str,
) -> None:
    for data in [
        {
            "game_type": "grand",
            field_name: invalid_value,
        },
        {
            "game_type": "grand",
            "game_declaration": {
                field_name: invalid_value,
            },
        },
    ]:
        with pytest.raises(ValueError, match=expected_error):
            validate_optional_game_declaration(data)


@pytest.mark.parametrize("game_declaration", [True, 1, "declaration", []])
def test_validate_optional_game_declaration_rejects_non_object_game_declaration(
    game_declaration: object,
) -> None:
    with pytest.raises(ValueError, match="game_declaration must be an object"):
        validate_optional_game_declaration(
            {
                "game_type": "grand",
                "game_declaration": game_declaration,
            }
        )


def test_validate_optional_game_declaration_rejects_invalid_null_declaration() -> None:
    try:
        validate_optional_game_declaration(
            {
                "game_type": "null",
                "schneider_announced": True,
            }
        )
    except ValueError as error:
        assert "Null games cannot have schneider announced" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_rejects_inconsistent_completed_trick_sequence() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["S7"],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_role": "declarer",
                "winner_player": "me",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "trick_leader is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_rejects_inconsistent_winner_role() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_role": "defenders",
                "winner_player": "me",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "winner_role is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_rejects_defender_winner_role_conflict() -> None:
    data = build_valid_input()
    data["player_role"] = "defender"
    data["declarer_player"] = "right"
    data["trick_leader"] = "left"
    data["next_player"] = "right"
    data["completed_tricks"] = [
        {
            "cards": ["CJ", "SJ", "DJ"],
            "winner_role": "declarer",
            "winner_player": "left",
        }
    ]

    with pytest.raises(ValueError, match="winner_role is inconsistent"):
        validate_position_input(data)


def test_validate_position_input_accepts_valid_defender_historical_winner_role() -> None:
    data = build_valid_input()
    data["player_role"] = "defender"
    data["declarer_player"] = "right"
    data["trick_leader"] = "left"
    data["next_player"] = "right"
    data["completed_tricks"] = [
        {
            "cards": ["CJ", "SJ", "DJ"],
            "winner_role": "defenders",
            "winner_player": "left",
        }
    ]

    validate_position_input(data)


def test_validate_position_input_does_not_infer_declarer_identity_from_history() -> None:
    data = build_valid_input()
    data["player_role"] = "unknown"
    data["trick_leader"] = "unknown"
    data["current_trick"] = []
    data["next_player"] = "unknown"
    data["completed_tricks"] = [
        {
            "cards": ["CJ", "SJ", "DJ"],
            "players": ["left", "right", "me"],
            "winner_role": "declarer",
            "winner_player": "left",
        }
    ]

    validate_position_input(data)

    assert data["declarer_player"] == "unknown"


def test_validate_position_input_rejects_rule_wrong_completed_trick_winner() -> None:
    data = {
        "game_type": "grand",
        "player_role": "unknown",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["S10", "S9", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "me"],
                "winner_role": "declarer",
                "winner_player": "left",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "winner_player is inconsistent with trick rules" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_rejects_rule_wrong_role_only_completed_trick() -> None:
    data = build_valid_input()
    data["game_type"] = "grand"
    data["player_role"] = "declarer"
    data["declarer_player"] = "me"
    data["trick_leader"] = "left"
    data["next_player"] = "left"
    data["current_trick"] = []
    data["hand"] = ["C7", "C8", "C9"]
    data["completed_tricks"] = [
        {
            "cards": ["SA", "S7", "S8"],
            "players": ["left", "right", "me"],
            "winner_role": "declarer",
        }
    ]

    with pytest.raises(ValueError, match=r"completed_tricks\[0\]\.winner_role"):
        validate_position_input(data)


def test_validate_position_input_accepts_rule_correct_role_only_completed_trick() -> None:
    data = build_valid_input()
    data["game_type"] = "grand"
    data["player_role"] = "declarer"
    data["declarer_player"] = "me"
    data["trick_leader"] = "left"
    data["next_player"] = "left"
    data["current_trick"] = []
    data["hand"] = ["C7", "C8", "C9"]
    data["completed_tricks"] = [
        {
            "cards": ["SA", "S7", "S8"],
            "players": ["left", "right", "me"],
            "winner_role": "defenders",
        }
    ]

    validate_position_input(data)


def test_validate_position_input_rejects_defender_rule_wrong_role_only_trick() -> None:
    data = build_valid_input()
    data["game_type"] = "grand"
    data["player_role"] = "defender"
    data["declarer_player"] = "right"
    data["trick_leader"] = "left"
    data["next_player"] = "left"
    data["current_trick"] = []
    data["hand"] = ["C7", "C8", "C9"]
    data["completed_tricks"] = [
        {
            "cards": ["SA", "S7", "S8"],
            "players": ["left", "right", "me"],
            "winner_role": "declarer",
        }
    ]

    with pytest.raises(ValueError, match="expected defenders, got declarer"):
        validate_position_input(data)


def test_validate_position_input_rejects_null_rule_wrong_role_only_trick() -> None:
    data = build_valid_input()
    data["game_type"] = "null"
    data["player_role"] = "declarer"
    data["declarer_player"] = "me"
    data["trick_leader"] = "me"
    data["next_player"] = "me"
    data["current_trick"] = []
    data["hand"] = ["C7", "C8", "C9"]
    data["completed_tricks"] = [
        {
            "cards": ["C10", "CJ", "CA"],
            "players": ["left", "right", "me"],
            "winner_role": "defenders",
        }
    ]

    with pytest.raises(ValueError, match="expected declarer, got defenders"):
        validate_position_input(data)


def test_validate_position_input_accepts_legacy_side_only_post_game_history() -> None:
    data = build_valid_input()
    data["game_type"] = "grand"
    data["player_role"] = "declarer"
    data["declarer_player"] = "me"
    data["trick_leader"] = "unknown"
    data["next_player"] = "unknown"
    data["current_trick"] = []
    data["hand"] = ["C7", "C8", "C9"]
    data["completed_tricks"] = [
        {
            "cards": ["SA", "S7", "S8"],
            "winner_role": "declarer",
        }
    ]

    validate_position_input(data)


def test_validate_position_input_keeps_unknown_declarer_role_only_tolerance() -> None:
    data = build_valid_input()
    data["game_type"] = "grand"
    data["player_role"] = "unknown"
    data["declarer_player"] = "unknown"
    data["trick_leader"] = "unknown"
    data["next_player"] = "unknown"
    data["current_trick"] = []
    data["hand"] = ["C7", "C8", "C9"]
    data["completed_tricks"] = [
        {
            "cards": ["SA", "S7", "S8"],
            "players": ["left", "right", "me"],
            "winner_role": "declarer",
        }
    ]

    validate_position_input(data)


def build_completed_trick_won_by_me() -> dict[str, object]:
    return {
        "cards": ["CJ", "SJ", "DJ"],
        "players": ["me", "left", "right"],
        "winner_role": "declarer",
        "winner_player": "me",
    }


def test_validate_position_input_derives_empty_trick_leader_from_last_winner() -> None:
    data = build_valid_input()
    data["trick_leader"] = "unknown"
    data["current_trick"] = []
    data["next_player"] = "unknown"
    data["completed_tricks"] = [build_completed_trick_won_by_me()]

    validate_position_input(data)


def test_validate_position_input_keeps_last_winner_for_one_card_partial() -> None:
    data = build_valid_input()
    data["trick_leader"] = "unknown"
    data["current_trick"] = ["CA"]
    data["next_player"] = "unknown"
    data["completed_tricks"] = [build_completed_trick_won_by_me()]

    validate_position_input(data)


def test_validate_position_input_keeps_last_winner_for_two_card_partial() -> None:
    data = build_valid_input()
    data["trick_leader"] = "unknown"
    data["current_trick"] = ["CA", "C10"]
    data["next_player"] = "unknown"
    data["completed_tricks"] = [build_completed_trick_won_by_me()]

    validate_position_input(data)


def test_validate_position_input_rejects_last_winner_leader_conflict() -> None:
    data = build_valid_input()
    data["trick_leader"] = "left"
    data["current_trick"] = []
    data["next_player"] = "left"
    data["completed_tricks"] = [build_completed_trick_won_by_me()]

    with pytest.raises(ValueError, match="completed_tricks"):
        validate_position_input(data)


def test_validate_position_input_does_not_derive_from_side_only_winner_role() -> None:
    data = build_valid_input()
    data["trick_leader"] = "unknown"
    data["current_trick"] = ["CA"]
    data["next_player"] = "unknown"
    data["completed_tricks"] = [
        {
            "cards": ["CJ", "SJ", "DJ"],
            "winner_role": "declarer",
        }
    ]

    with pytest.raises(ValueError, match="Cannot determine turn phase"):
        validate_position_input(data)

def test_validate_position_input_rejects_zero_bid_value() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "bid_value": 0,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "bid_value must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_rejects_non_integer_bid_value() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "bid_value": "72",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "bid_value must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_accepts_known_performance_rating_system() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "performance_rating_system": "isko_list",
    }

    validate_position_input(data)

def test_validate_position_input_rejects_unknown_performance_rating_system() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "performance_rating_system": "unknown_system",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Unknown performance rating system" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_list_performance_input() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_performance_input"] = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
    }

    validate_position_input(data)


def test_validate_position_input_accepts_negative_list_player_game_points() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_performance_input"] = {
        "player_game_points": -80,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
    }

    validate_position_input(data)


def test_validate_position_input_rejects_list_performance_without_rating_system() -> None:
    data = build_valid_input()
    data["list_performance_input"] = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
    }

    with pytest.raises(
        ValueError,
        match="list_performance_input requires performance_rating_system",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_list_performance_for_placeholder() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "placeholder"
    data["list_performance_input"] = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
    }

    with pytest.raises(
        ValueError,
        match="list_performance_input requires performance_rating_system",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_missing_list_performance_fields() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_performance_input"] = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
    }

    with pytest.raises(
        ValueError,
        match="list_performance_input is missing required keys",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_non_integer_list_performance_values() -> None:
    cases = [
        ("player_game_points", "120"),
        ("own_games_won", 1.5),
        ("own_games_lost", True),
        ("other_players_lost_games", False),
    ]

    for field_name, value in cases:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_performance_input"] = {
            "player_game_points": 120,
            "own_games_won": 3,
            "own_games_lost": 1,
            "other_players_lost_games": 2,
        }
        data["list_performance_input"][field_name] = value

        with pytest.raises(
            ValueError,
            match=f"list_performance_input.{field_name} must be an integer",
        ):
            validate_position_input(data)


def test_validate_position_input_rejects_negative_list_game_counters() -> None:
    for field_name in [
        "own_games_won",
        "own_games_lost",
        "other_players_lost_games",
    ]:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_performance_input"] = {
            "player_game_points": 120,
            "own_games_won": 3,
            "own_games_lost": 1,
            "other_players_lost_games": 2,
        }
        data["list_performance_input"][field_name] = -1

        with pytest.raises(
            ValueError,
            match=f"list_performance_input.{field_name} must be non-negative",
        ):
            validate_position_input(data)


def test_validate_position_input_accepts_list_game_contributions() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_game_contributions"] = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
        },
        {
            "player_role": "defender",
            "game_outcome": "declarer_loss",
            "settlement_score": -144,
        },
    ]

    validate_position_input(data)


def test_validate_position_input_accepts_empty_list_game_contributions() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_game_contributions"] = []

    validate_position_input(data)


def test_validate_position_input_rejects_both_list_performance_input_modes() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_performance_input"] = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
    }
    data["list_game_contributions"] = []

    with pytest.raises(ValueError, match="alternative input modes"):
        validate_position_input(data)


def test_validate_position_input_rejects_list_game_contributions_without_rating_system() -> None:
    data = build_valid_input()
    data["list_game_contributions"] = []

    with pytest.raises(
        ValueError,
        match="list_game_contributions requires performance_rating_system",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_list_game_contributions_for_placeholder() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "placeholder"
    data["list_game_contributions"] = []

    with pytest.raises(
        ValueError,
        match="list_game_contributions requires performance_rating_system",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_non_array_list_game_contributions() -> None:
    for list_game_contributions in [None, {}, "games", True]:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_game_contributions"] = list_game_contributions

        with pytest.raises(
            ValueError,
            match="list_game_contributions must be an array",
        ):
            validate_position_input(data)


def test_validate_position_input_rejects_non_object_list_game_contribution() -> None:
    for contribution in [None, "game", 1, True]:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_game_contributions"] = [contribution]

        with pytest.raises(ValueError, match="must be an object"):
            validate_position_input(data)


def test_validate_position_input_rejects_missing_list_game_contribution_fields() -> None:
    for field_name in ["player_role", "game_outcome", "settlement_score"]:
        contribution = {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
        }
        del contribution[field_name]

        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_game_contributions"] = [contribution]

        with pytest.raises(ValueError, match="missing required keys"):
            validate_position_input(data)


def test_validate_position_input_rejects_additional_list_game_contribution_fields() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_game_contributions"] = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
            "table_size": 3,
        }
    ]

    with pytest.raises(ValueError, match="unsupported keys"):
        validate_position_input(data)


def test_validate_position_input_rejects_invalid_list_game_contribution_role() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_game_contributions"] = [
        {
            "player_role": "unknown",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
        }
    ]

    with pytest.raises(ValueError, match="Unsupported .*player_role"):
        validate_position_input(data)


def test_validate_position_input_rejects_invalid_list_game_contribution_outcome() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_game_contributions"] = [
        {
            "player_role": "declarer",
            "game_outcome": "unknown",
            "settlement_score": 96,
        }
    ]

    with pytest.raises(ValueError, match="Unsupported .*game_outcome"):
        validate_position_input(data)


def test_validate_position_input_rejects_non_integer_list_game_contribution_scores() -> None:
    for settlement_score in [None, "96", 96.0, True, False]:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_game_contributions"] = [
            {
                "player_role": "declarer",
                "game_outcome": "declarer_win",
                "settlement_score": settlement_score,
            }
        ]

        with pytest.raises(ValueError, match="settlement_score must be an integer"):
            validate_position_input(data)


def test_validate_position_input_rejects_list_game_contribution_score_signs() -> None:
    cases = [
        {
            "game_outcome": "declarer_win",
            "settlement_score": 0,
            "expected_error": "positive settlement_score",
        },
        {
            "game_outcome": "declarer_win",
            "settlement_score": -96,
            "expected_error": "positive settlement_score",
        },
        {
            "game_outcome": "declarer_loss",
            "settlement_score": 0,
            "expected_error": "negative settlement_score",
        },
        {
            "game_outcome": "declarer_loss",
            "settlement_score": 96,
            "expected_error": "negative settlement_score",
        },
    ]

    for case in cases:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_game_contributions"] = [
            {
                "player_role": "declarer",
                "game_outcome": case["game_outcome"],
                "settlement_score": case["settlement_score"],
            }
        ]

        with pytest.raises(ValueError, match=case["expected_error"]):
            validate_position_input(data)


def build_valid_list_analysis_result(
    player_role="declarer",
    is_complete=True,
    is_loss=False,
    settlement_score=96,
) -> dict[str, object]:
    return {
        "position": {
            "player_role": player_role,
        },
        "final_settlement_summary": {
            "is_complete": is_complete,
            "is_loss": is_loss,
            "settlement_score": settlement_score,
        },
    }


def build_valid_list_game_contribution(
    player_role="declarer",
    game_outcome="declarer_win",
    settlement_score=96,
) -> dict[str, object]:
    return {
        "player_role": player_role,
        "game_outcome": game_outcome,
        "settlement_score": settlement_score,
    }


def build_list_mode_data(
    mode: str,
    entries: list[dict[str, object]],
) -> dict[str, object]:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data[mode] = entries

    return data


def build_list_mode_entry(
    mode: str,
    player_role="declarer",
    game_outcome="declarer_win",
    settlement_score=96,
) -> dict[str, object]:
    if mode == "list_game_contributions":
        return build_valid_list_game_contribution(
            player_role=player_role,
            game_outcome=game_outcome,
            settlement_score=settlement_score,
        )

    return build_valid_list_analysis_result(
        player_role=player_role,
        is_loss=game_outcome == "declarer_loss",
        settlement_score=settlement_score,
    )


def add_list_performance_mode(data: dict[str, object], mode: str) -> None:
    if mode == "list_performance_input":
        data[mode] = {
            "player_game_points": 120,
            "own_games_won": 3,
            "own_games_lost": 1,
            "other_players_lost_games": 2,
        }
        return

    if mode == "list_game_contributions":
        data[mode] = [
            {
                "player_role": "declarer",
                "game_outcome": "declarer_win",
                "settlement_score": 96,
            }
        ]
        return

    data[mode] = [build_valid_list_analysis_result()]


def test_validate_position_input_accepts_list_analysis_results() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(
            player_role="declarer",
            is_loss=False,
            settlement_score=96,
        ),
        build_valid_list_analysis_result(
            player_role="defender",
            is_loss=True,
            settlement_score=-144,
        ),
    ]

    validate_position_input(data)


def test_validate_position_input_accepts_list_analysis_result_supersets() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        {
            "input_file": "generated.json",
            "position": {
                "player_role": "declarer",
                "game_type": "grand",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
                "winner": "declarer",
            },
            "recommendation": {
                "card": "SA",
            },
        }
    ]

    validate_position_input(data)


def test_validate_position_input_accepts_empty_list_analysis_results() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = []

    validate_position_input(data)


def test_validate_position_input_accepts_incomplete_list_analysis_result() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        {
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": False,
            },
        }
    ]

    validate_position_input(data)


def test_validate_position_input_accepts_unknown_role_list_analysis_result() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(player_role="unknown")
    ]

    validate_position_input(data)


def test_validate_position_input_rejects_non_array_list_analysis_results() -> None:
    for list_analysis_results in [None, {}, "results", True]:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_analysis_results"] = list_analysis_results

        with pytest.raises(ValueError, match="list_analysis_results must be an array"):
            validate_position_input(data)


def test_validate_position_input_rejects_non_object_list_analysis_result() -> None:
    for analysis_result in [None, [], "result", True, 1]:
        data = build_valid_input()
        data["performance_rating_system"] = "isko_list"
        data["list_analysis_results"] = [analysis_result]

        with pytest.raises(
            ValueError,
            match=r"list_analysis_results\[0\]: analysis_result must be an object",
        ):
            validate_position_input(data)


@pytest.mark.parametrize(
    "analysis_result",
    [
        {},
        {"position": None},
        {"position": []},
        {"position": "position"},
    ],
)
def test_validate_position_input_rejects_invalid_list_analysis_result_position(
    analysis_result,
) -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [analysis_result]

    with pytest.raises(ValueError, match="analysis_result.position must be an object"):
        validate_position_input(data)


def test_validate_position_input_rejects_missing_list_analysis_result_role() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    analysis_result = build_valid_list_analysis_result()
    del analysis_result["position"]["player_role"]
    data["list_analysis_results"] = [analysis_result]

    with pytest.raises(ValueError, match="position.player_role is required"):
        validate_position_input(data)


def test_validate_position_input_rejects_invalid_list_analysis_result_role() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(player_role="attacker")
    ]

    with pytest.raises(ValueError, match="Unsupported analysis_result.position.player_role"):
        validate_position_input(data)


@pytest.mark.parametrize(
    "final_settlement_summary",
    [None, [], "summary"],
)
def test_validate_position_input_rejects_invalid_list_analysis_result_settlement(
    final_settlement_summary,
) -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    analysis_result = build_valid_list_analysis_result()
    analysis_result["final_settlement_summary"] = final_settlement_summary
    data["list_analysis_results"] = [analysis_result]

    with pytest.raises(
        ValueError,
        match="analysis_result.final_settlement_summary must be an object",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_missing_list_analysis_result_settlement() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    analysis_result = build_valid_list_analysis_result()
    del analysis_result["final_settlement_summary"]
    data["list_analysis_results"] = [analysis_result]

    with pytest.raises(
        ValueError,
        match="analysis_result.final_settlement_summary must be an object",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_missing_list_analysis_result_is_complete() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    analysis_result = build_valid_list_analysis_result()
    del analysis_result["final_settlement_summary"]["is_complete"]
    data["list_analysis_results"] = [analysis_result]

    with pytest.raises(ValueError, match="is_complete is required"):
        validate_position_input(data)


@pytest.mark.parametrize("is_complete", [None, "true", 1, 0])
def test_validate_position_input_rejects_invalid_list_analysis_result_is_complete(
    is_complete,
) -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(is_complete=is_complete)
    ]

    with pytest.raises(ValueError, match="is_complete must be a boolean"):
        validate_position_input(data)


def test_validate_position_input_rejects_completed_list_analysis_result_missing_is_loss() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    analysis_result = build_valid_list_analysis_result()
    del analysis_result["final_settlement_summary"]["is_loss"]
    data["list_analysis_results"] = [analysis_result]

    with pytest.raises(ValueError, match="is_loss is required"):
        validate_position_input(data)


@pytest.mark.parametrize("is_loss", [None, "false", 1, 0])
def test_validate_position_input_rejects_completed_list_analysis_result_invalid_is_loss(
    is_loss,
) -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(is_loss=is_loss)
    ]

    with pytest.raises(ValueError, match="is_loss must be a boolean"):
        validate_position_input(data)


def test_validate_position_input_rejects_completed_list_analysis_result_missing_score() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    analysis_result = build_valid_list_analysis_result()
    del analysis_result["final_settlement_summary"]["settlement_score"]
    data["list_analysis_results"] = [analysis_result]

    with pytest.raises(ValueError, match="settlement_score is required"):
        validate_position_input(data)


@pytest.mark.parametrize("settlement_score", [None, "96", 96.0, True, False])
def test_validate_position_input_rejects_completed_list_analysis_result_invalid_score(
    settlement_score,
) -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(settlement_score=settlement_score)
    ]

    with pytest.raises(ValueError, match="settlement_score must be an integer"):
        validate_position_input(data)


@pytest.mark.parametrize(
    ("is_loss", "settlement_score", "expected_error"),
    [
        (False, 0, "positive settlement_score"),
        (False, -96, "positive settlement_score"),
        (True, 0, "negative settlement_score"),
        (True, 96, "negative settlement_score"),
    ],
)
def test_validate_position_input_rejects_list_analysis_result_score_signs(
    is_loss,
    settlement_score,
    expected_error,
) -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(
            is_loss=is_loss,
            settlement_score=settlement_score,
        )
    ]

    with pytest.raises(ValueError, match=expected_error):
        validate_position_input(data)


def test_validate_position_input_adds_index_to_list_analysis_result_errors() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    malformed_result = build_valid_list_analysis_result()
    del malformed_result["final_settlement_summary"]["settlement_score"]
    data["list_analysis_results"] = [
        build_valid_list_analysis_result(),
        malformed_result,
    ]

    with pytest.raises(
        ValueError,
        match=r"list_analysis_results\[1\]: .*settlement_score is required",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_list_analysis_results_without_rating_system() -> None:
    data = build_valid_input()
    data["list_analysis_results"] = []

    with pytest.raises(
        ValueError,
        match="list_analysis_results requires performance_rating_system",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_list_analysis_results_for_placeholder() -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "placeholder"
    data["list_analysis_results"] = []

    with pytest.raises(
        ValueError,
        match="list_analysis_results requires performance_rating_system",
    ):
        validate_position_input(data)


@pytest.mark.parametrize(
    "modes",
    [
        ("list_performance_input", "list_game_contributions"),
        ("list_performance_input", "list_analysis_results"),
        ("list_game_contributions", "list_analysis_results"),
        (
            "list_performance_input",
            "list_game_contributions",
            "list_analysis_results",
        ),
    ],
)
def test_validate_position_input_rejects_multiple_list_performance_input_modes(
    modes,
) -> None:
    data = build_valid_input()
    data["performance_rating_system"] = "isko_list"
    for mode in modes:
        add_list_performance_mode(data, mode)

    with pytest.raises(ValueError, match="alternative input modes"):
        validate_position_input(data)


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
@pytest.mark.parametrize("field_name", ["rated_player_id", "game_id"])
@pytest.mark.parametrize(
    "invalid_value",
    ["", "   ", " player-1", "player-1 ", True, 123, 1.5, [], {}, None],
)
def test_validate_position_input_rejects_invalid_list_entry_identifier_values(
    mode: str,
    field_name: str,
    invalid_value: object,
) -> None:
    entry = build_list_mode_entry(mode)
    entry[field_name] = invalid_value
    data = build_list_mode_data(mode, [entry])

    with pytest.raises(ValueError) as error:
        validate_position_input(data)

    error_message = str(error.value)
    assert mode in error_message
    assert "[0]" in error_message
    assert field_name in error_message


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_accepts_same_rated_player_id_for_list_modes(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(
        mode,
        player_role="defender",
        game_outcome="declarer_loss",
        settlement_score=-144,
    )
    first_entry["rated_player_id"] = "player-1"
    second_entry["rated_player_id"] = "player-1"

    validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_accepts_single_rated_player_id_for_list_modes(
    mode: str,
) -> None:
    entry = build_list_mode_entry(mode)
    entry["rated_player_id"] = "player-1"

    validate_position_input(build_list_mode_data(mode, [entry]))


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_rejects_conflicting_rated_player_ids(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(mode)
    first_entry["rated_player_id"] = "player-a"
    second_entry["rated_player_id"] = "Player-A"

    with pytest.raises(ValueError) as error:
        validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))

    error_message = str(error.value)
    assert f"{mode}.rated_player_id values conflict" in error_message
    assert "index 0" in error_message
    assert "index 1" in error_message
    assert "player-a" in error_message
    assert "Player-A" in error_message


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_rejects_partial_rated_player_id_presence(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(mode)
    first_entry["rated_player_id"] = "player-1"

    with pytest.raises(ValueError) as error:
        validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))

    error_message = str(error.value)
    assert f"{mode}.rated_player_id" in error_message
    assert "supplied indexes: [0]" in error_message
    assert "missing indexes: [1]" in error_message


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_accepts_unique_game_ids_for_list_modes(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(mode)
    first_entry["game_id"] = "game-1"
    second_entry["game_id"] = "game-2"

    validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_accepts_partial_unique_game_ids(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(mode)
    first_entry["game_id"] = "game-1"

    validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_rejects_duplicate_game_ids(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(mode)
    first_entry["game_id"] = "game-1"
    second_entry["game_id"] = "game-1"

    with pytest.raises(ValueError) as error:
        validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))

    error_message = str(error.value)
    assert f"Duplicate {mode}.game_id 'game-1'" in error_message
    assert "indexes 0 and 1" in error_message


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_rejects_duplicate_game_ids_for_different_content(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(
        mode,
        player_role="declarer",
        game_outcome="declarer_win",
        settlement_score=96,
    )
    second_entry = build_list_mode_entry(
        mode,
        player_role="defender",
        game_outcome="declarer_loss",
        settlement_score=-144,
    )
    first_entry["game_id"] = "game-1"
    second_entry["game_id"] = "game-1"

    with pytest.raises(ValueError, match="Duplicate .*game_id 'game-1'"):
        validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_accepts_identical_content_with_different_game_ids(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(mode)
    first_entry["game_id"] = "game-1"
    second_entry["game_id"] = "game-2"

    validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))


@pytest.mark.parametrize(
    "mode",
    ["list_game_contributions", "list_analysis_results"],
)
def test_validate_position_input_treats_case_different_game_ids_as_distinct(
    mode: str,
) -> None:
    first_entry = build_list_mode_entry(mode)
    second_entry = build_list_mode_entry(mode)
    first_entry["game_id"] = "game-1"
    second_entry["game_id"] = "GAME-1"

    validate_position_input(build_list_mode_data(mode, [first_entry, second_entry]))


def test_validate_position_input_reports_rated_player_conflict_before_duplicate_game_id() -> None:
    first_entry = build_valid_list_game_contribution()
    second_entry = build_valid_list_game_contribution()
    first_entry["rated_player_id"] = "player-1"
    second_entry["rated_player_id"] = "player-2"
    first_entry["game_id"] = "game-1"
    second_entry["game_id"] = "game-1"
    data = build_list_mode_data(
        "list_game_contributions",
        [first_entry, second_entry],
    )

    with pytest.raises(ValueError) as error:
        validate_position_input(data)

    error_message = str(error.value)
    assert "rated_player_id values conflict" in error_message
    assert "Duplicate" not in error_message


def test_validate_position_input_rejects_live_known_post_game_skat() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "known_post_game",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "known_post_game" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

   
def test_validate_position_input_rejects_live_decision_with_known_skat_cards() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": ["C7", "D8"],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Known skat cards" in str(error)
        assert "live_decision" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_live_known_to_declarer_skat_for_defender() -> None:
    data = {
        "game_type": "grand",
        "player_role": "defender",
        "declarer_player": "left",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "D8"],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "known_to_declarer",
    }

    validate_position_input(data)


def test_validate_position_input_rejects_unknown_visibility_with_skat_cards() -> None:
    data = build_valid_input()
    data["analysis_mode"] = "post_game_review"
    data["skat_visibility"] = "unknown"
    data["skat"] = ["H8", "D8"]

    with pytest.raises(ValueError, match="skat_visibility='unknown'"):
        validate_position_input(data)


def test_validate_position_input_rejects_one_known_to_declarer_skat_card() -> None:
    data = build_valid_input()
    data["analysis_mode"] = "post_game_review"
    data["skat_visibility"] = "known_to_declarer"
    data["skat"] = ["H8"]

    with pytest.raises(ValueError, match="zero or two"):
        validate_position_input(data)

def test_validate_position_input_accepts_post_game_review_with_known_skat_cards() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": ["C7", "D8"],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
    }

    validate_position_input(data)


def test_position_input_rejects_live_winner_player_without_players() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "winner_player": "me",
                "winner_role": "declarer",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "winner_player" in str(error)
        assert "players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
    

def test_position_input_accepts_live_trick_with_players_and_winner() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_player": "me",
                "winner_role": "declarer",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
    }

    validate_position_input(data)


def test_validate_position_input_rejects_live_normal_completion() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 70,
        "defender_points": 50,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "normal_completion",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "game_end_reason" in str(error)
        assert "not_ended" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_rejects_live_complete_points() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 70,
        "defender_points": 50,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "live_decision" in str(error)
        assert "120" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_post_game_complete_points() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 70,
        "defender_points": 50,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "game_end_reason": "normal_completion",
    }

    validate_position_input(data)

def test_validate_optional_opponent_policies_accepts_left_right_values() -> None:
    validate_optional_opponent_policies(
        {
            "left_opponent_lead_policy": "highest_point",
            "left_opponent_response_policy": "basic_trick_play",
            "right_opponent_lead_policy": "lowest_point",
            "right_opponent_response_policy": "highest_point",
        }
    )

def test_validate_optional_opponent_policies_rejects_invalid_left_lead() -> None:
    try:
        validate_optional_opponent_policies(
            {
                "left_opponent_lead_policy": "invalid_policy",
            }
        )
    except ValueError as error:
        assert "opponent card policy" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_legal_actual_card_in_post_game_review() -> None:
    data = build_valid_input()
    data["actual_card_played"] = "C7"

    validate_position_input(data)


def test_validate_position_input_rejects_invalid_actual_card() -> None:
    data = build_valid_input()
    data["actual_card_played"] = "XX"

    with pytest.raises(ValueError, match="Invalid cards in actual_card_played"):
        validate_position_input(data)


def test_validate_position_input_rejects_actual_card_in_live_decision() -> None:
    data = build_valid_input()
    data["analysis_mode"] = "live_decision"
    data["skat_visibility"] = "unknown"
    data["actual_card_played"] = "C7"

    with pytest.raises(
        ValueError,
        match="actual_card_played requires analysis_mode to be post_game_review",
    ):
        validate_position_input(data)


def test_validate_position_input_rejects_actual_card_not_in_hand() -> None:
    data = build_valid_input()
    data["actual_card_played"] = "D7"

    with pytest.raises(ValueError, match="actual_card_played must be contained in hand"):
        validate_position_input(data)


def test_validate_position_input_rejects_illegal_actual_card() -> None:
    data = build_valid_input()
    data["actual_card_played"] = "SA"

    with pytest.raises(
        ValueError,
        match="actual_card_played must be legal in the current position",
    ):
        validate_position_input(data)
