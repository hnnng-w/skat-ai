from skat_ai.game_history import (
    build_completed_trick_from_cards,
    build_completed_trick_from_state_and_candidate,
    build_score_summary,
    calculate_completed_trick_points_by_side,
    get_all_played_cards,
    get_completed_trick_cards,
    get_completed_trick_points,
    get_completed_trick_winner_player,
    get_completed_trick_winner_role,
    get_expected_winner_role_for_player,
    get_played_cards_from_completed_tricks,
    get_players_for_trick_leader,
    get_winner_player_from_trick_players,
    get_winner_role_for_trick_winner,
    get_winner_role_for_winner_player,
    validate_completed_trick_player_order,
    validate_completed_trick_rule_winner,
    validate_completed_trick_sequence,
    validate_completed_trick_structure,
    validate_completed_trick_winner_consistency,
)
from skat_ai.game_state import GameState


def test_get_completed_trick_cards() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "declarer",
    }

    assert get_completed_trick_cards(completed_trick) == ["CA", "C10", "CK"]


def test_get_completed_trick_winner_role() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "declarer",
    }

    assert get_completed_trick_winner_role(completed_trick) == "declarer"


def test_get_completed_trick_points() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "declarer",
    }

    assert get_completed_trick_points(completed_trick) == 25


def test_calculate_completed_trick_points_by_side() -> None:
    completed_tricks = [
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
        },
        {
            "cards": ["SA", "S10", "SK"],
            "winner_role": "defenders",
        },
    ]

    points = calculate_completed_trick_points_by_side(completed_tricks)

    assert points["declarer_points"] == 25
    assert points["defender_points"] == 25


def test_build_score_summary() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=[],
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ],
        declarer_points=10,
        defender_points=5,
    )

    summary = build_score_summary(state)

    assert summary["explicit_declarer_points"] == 10
    assert summary["explicit_defender_points"] == 5
    assert summary["completed_trick_declarer_points"] == 25
    assert summary["completed_trick_defender_points"] == 0
    assert summary["total_declarer_points"] == 35
    assert summary["total_defender_points"] == 5


def test_get_played_cards_from_completed_tricks() -> None:
    completed_tricks = [
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
        },
        {
            "cards": ["SA", "S10", "SK"],
            "winner_role": "defenders",
        },
    ]

    played_cards = get_played_cards_from_completed_tricks(completed_tricks)

    assert played_cards == ["CA", "C10", "CK", "SA", "S10", "SK"]


def test_get_all_played_cards_combines_legacy_played_cards_and_completed_tricks() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H7"],
        current_trick=[],
        played_cards=["D7"],
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ],
    )

    played_cards = get_all_played_cards(state)

    assert played_cards == ["D7", "CA", "C10", "CK"]


def test_get_winner_role_for_trick_winner_when_declarer_wins_own_card() -> None:
    winner_role = get_winner_role_for_trick_winner(
        winner_index=1,
        player_index=1,
        player_role="declarer",
    )

    assert winner_role == "declarer"


def test_get_winner_role_for_trick_winner_when_declarer_loses() -> None:
    winner_role = get_winner_role_for_trick_winner(
        winner_index=0,
        player_index=1,
        player_role="declarer",
    )

    assert winner_role == "defenders"


def test_get_winner_role_for_trick_winner_when_defender_wins_own_card() -> None:
    winner_role = get_winner_role_for_trick_winner(
        winner_index=2,
        player_index=2,
        player_role="defender",
    )

    assert winner_role == "defenders"


def test_get_winner_role_for_trick_winner_rejects_unresolved_defender_loss() -> None:
    try:
        get_winner_role_for_trick_winner(
            winner_index=0,
            player_index=2,
            player_role="defender",
        )
    except ValueError as error:
        assert "without concrete winner_player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_winner_role_for_trick_winner_rejects_unknown_player_role() -> None:
    try:
        get_winner_role_for_trick_winner(
            winner_index=0,
            player_index=0,
            player_role="unknown",
        )
    except ValueError as error:
        assert "Unsupported player role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_completed_trick_from_cards_for_declarer_win() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["S7", "SA", "S8"],
        game_type="grand",
        player_index=1,
        player_role="declarer",
        trick_players=["left", "me", "right"],
    )

    assert completed_trick["cards"] == ["S7", "SA", "S8"]
    assert completed_trick["players"] == ["left", "me", "right"]
    assert completed_trick["winner_role"] == "declarer"
    assert completed_trick["winner_player"] == "me"


def test_build_completed_trick_from_cards_for_declarer_loss() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["S7", "S9", "SA"],
        game_type="grand",
        player_index=1,
        player_role="declarer",
        trick_players=["left", "me", "right"],
    )

    assert completed_trick["cards"] == ["S7", "S9", "SA"]
    assert completed_trick["players"] == ["left", "me", "right"]
    assert completed_trick["winner_role"] == "defenders"
    assert completed_trick["winner_player"] == "right"


def test_build_completed_trick_from_cards_requires_three_cards() -> None:
    try:
        build_completed_trick_from_cards(
            cards=["S7", "SA"],
            game_type="grand",
            player_index=1,
            player_role="declarer",
        )
    except ValueError as error:
        assert "exactly 3 cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_completed_trick_from_cards_requires_valid_player_index() -> None:
    try:
        build_completed_trick_from_cards(
            cards=["S7", "SA", "S8"],
            game_type="grand",
            player_index=3,
            player_role="declarer",
        )
    except ValueError as error:
        assert "player_index" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_completed_trick_from_state_and_candidate_second_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=["S7"],
        trick_leader="right",
    )

    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=["S7", "SA", "S8"],
    )

    assert completed_trick["cards"] == ["S7", "SA", "S8"]
    assert completed_trick["players"] == ["right", "me", "left"]
    assert completed_trick["winner_role"] == "declarer"
    assert completed_trick["winner_player"] == "me"


def test_build_completed_trick_from_state_and_candidate_third_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=["S7", "S8"],
        trick_leader="left",
    )

    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=["S7", "S8", "SA"],
    )

    assert completed_trick["cards"] == ["S7", "S8", "SA"]
    assert completed_trick["players"] == ["left", "right", "me"]
    assert completed_trick["winner_role"] == "declarer"
    assert completed_trick["winner_player"] == "me"


def test_get_players_for_trick_leader_me() -> None:
    assert get_players_for_trick_leader("me") == ["me", "left", "right"]


def test_get_players_for_trick_leader_left() -> None:
    assert get_players_for_trick_leader("left") == ["left", "right", "me"]

def test_get_players_for_trick_leader_right() -> None:
    assert get_players_for_trick_leader("right") == ["right", "me", "left"]

def test_get_players_for_trick_leader_rejects_unknown() -> None:
    try:
        get_players_for_trick_leader("unknown")
    except ValueError as error:
        assert "Cannot determine trick players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_winner_player_from_trick_players() -> None:
    winner_player = get_winner_player_from_trick_players(
        winner_index=2,
        trick_players=["left", "me", "right"],
    )

    assert winner_player == "right"


def test_get_winner_player_from_trick_players_rejects_invalid_index() -> None:
    try:
        get_winner_player_from_trick_players(
            winner_index=3,
            trick_players=["left", "me", "right"],
        )
    except ValueError as error:
        assert "winner_index" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_winner_player_from_trick_players_rejects_invalid_player_list_length() -> None:
    try:
        get_winner_player_from_trick_players(
            winner_index=0,
            trick_players=["left", "me"],
        )
    except ValueError as error:
        assert "exactly 3 players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_winner_role_for_winner_player_when_declarer_is_me() -> None:
    assert get_winner_role_for_winner_player("me", "declarer") == "declarer"
    assert get_winner_role_for_winner_player("left", "declarer") == "defenders"
    assert get_winner_role_for_winner_player("right", "declarer") == "defenders"


def test_get_winner_role_for_winner_player_when_declarer_is_left() -> None:
    assert get_winner_role_for_winner_player("left", "defender", "left") == "declarer"
    assert get_winner_role_for_winner_player("me", "defender", "left") == "defenders"
    assert get_winner_role_for_winner_player("right", "defender", "left") == "defenders"


def test_get_winner_role_for_winner_player_when_declarer_is_right() -> None:
    assert get_winner_role_for_winner_player("right", "defender", "right") == "declarer"
    assert get_winner_role_for_winner_player("me", "defender", "right") == "defenders"
    assert get_winner_role_for_winner_player("left", "defender", "right") == "defenders"


def test_get_winner_role_for_winner_player_rejects_unresolved_defender_identity() -> None:
    try:
        get_winner_role_for_winner_player("left", "defender")
    except ValueError as error:
        assert "player_role='defender'" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_completed_trick_from_cards_defender_partner_right_wins() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["S7", "SA", "S8"],
        game_type="grand",
        player_index=2,
        player_role="defender",
        trick_players=["left", "right", "me"],
        declarer_player="left",
    )

    assert completed_trick["winner_player"] == "right"
    assert completed_trick["winner_role"] == "defenders"


def test_build_completed_trick_from_cards_defender_partner_left_wins() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["SA", "S7", "S8"],
        game_type="grand",
        player_index=2,
        player_role="defender",
        trick_players=["left", "right", "me"],
        declarer_player="right",
    )

    assert completed_trick["winner_player"] == "left"
    assert completed_trick["winner_role"] == "defenders"


def test_build_completed_trick_from_cards_declarer_left_wins() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["SA", "S7", "S8"],
        game_type="grand",
        player_index=2,
        player_role="defender",
        trick_players=["left", "right", "me"],
        declarer_player="left",
    )

    assert completed_trick["winner_player"] == "left"
    assert completed_trick["winner_role"] == "declarer"


def test_build_completed_trick_from_cards_local_defender_wins() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["S7", "S8", "SA"],
        game_type="grand",
        player_index=2,
        player_role="defender",
        trick_players=["left", "right", "me"],
        declarer_player="left",
    )

    assert completed_trick["winner_player"] == "me"
    assert completed_trick["winner_role"] == "defenders"


def test_get_completed_trick_winner_player_defaults_to_unknown() -> None:
    completed_trick = {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "declarer",
    }

    assert get_completed_trick_winner_player(completed_trick) == "unknown"


def test_build_completed_trick_from_cards_with_known_players() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["S7", "SA", "S8"],
        game_type="grand",
        player_index=1,
        player_role="declarer",
        trick_players=["left", "me", "right"],
    )

    assert completed_trick["cards"] == ["S7", "SA", "S8"]
    assert completed_trick["players"] == ["left", "me", "right"]
    assert completed_trick["winner_role"] == "declarer"
    assert completed_trick["winner_player"] == "me"


def test_build_completed_trick_from_state_and_candidate_uses_trick_leader() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=["S7", "S8"],
        trick_leader="left",
    )

    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=["S7", "S8", "SA"],
    )

    assert completed_trick["players"] == ["left", "right", "me"]
    assert completed_trick["winner_player"] == "me"
    assert completed_trick["winner_role"] == "declarer"

def test_validate_completed_trick_player_order_accepts_valid_order() -> None:
    validate_completed_trick_player_order(
        {
            "cards": ["S7", "S8", "SA"],
            "players": ["left", "right", "me"],
            "winner_player": "me",
        }
    )


def test_validate_completed_trick_player_order_rejects_invalid_order() -> None:
    try:
        validate_completed_trick_player_order(
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "me", "right"],
                "winner_player": "me",
            }
        )
    except ValueError as error:
        assert "expected player order" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_sequence_accepts_consistent_sequence() -> None:
    validate_completed_trick_sequence(
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_player": "me",
            },
            {
                "cards": ["DK", "DA", "D10"],
                "players": ["me", "left", "right"],
                "winner_player": "left",
            },
            {
                "cards": ["HA", "H10", "HK"],
                "players": ["left", "right", "me"],
                "winner_player": "left",
            },
        ],
        current_trick=["S7"],
        trick_leader="left",
    )


def test_validate_completed_trick_sequence_rejects_wrong_next_leader() -> None:
    try:
        validate_completed_trick_sequence(
            completed_tricks=[
                {
                    "cards": ["CJ", "SJ", "DJ"],
                    "players": ["me", "left", "right"],
                    "winner_player": "me",
                },
                {
                    "cards": ["DA", "D10", "DK"],
                    "players": ["left", "right", "me"],
                    "winner_player": "left",
                },
            ],
            current_trick=[],
            trick_leader="unknown",
        )
    except ValueError as error:
        assert "expected next trick leader me" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_sequence_rejects_current_trick_leader_mismatch() -> None:
    try:
        validate_completed_trick_sequence(
            completed_tricks=[
                {
                    "cards": ["CJ", "SJ", "DJ"],
                    "players": ["me", "left", "right"],
                    "winner_player": "me",
                }
            ],
            current_trick=["S7"],
            trick_leader="left",
        )
    except ValueError as error:
        assert "trick_leader is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_sequence_is_tolerant_without_players() -> None:
    validate_completed_trick_sequence(
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "DJ"],
            }
        ],
        current_trick=["S7"],
        trick_leader="left",
    )

def test_validate_completed_trick_sequence_uses_winner_without_players() -> None:
    try:
        validate_completed_trick_sequence(
            completed_tricks=[
                {
                    "cards": ["CJ", "SJ", "DJ"],
                    "winner_player": "me",
                }
            ],
            current_trick=["S7"],
            trick_leader="left",
        )
    except ValueError as error:
        assert "trick_leader is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_completed_trick_structure_accepts_valid_trick() -> None:
    validate_completed_trick_structure(
        {
            "cards": ["S7", "S8", "SA"],
            "players": ["left", "right", "me"],
            "winner_role": "declarer",
            "winner_player": "me",
        }
    )


def test_validate_completed_trick_structure_rejects_wrong_card_count() -> None:
    try:
        validate_completed_trick_structure(
            {
                "cards": ["S7", "S8"],
                "players": ["left", "right", "me"],
            }
        )
    except ValueError as error:
        assert "completed_trick.cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_structure_rejects_wrong_player_count() -> None:
    try:
        validate_completed_trick_structure(
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right"],
            }
        )
    except ValueError as error:
        assert "completed_trick.players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_structure_rejects_invalid_player() -> None:
    try:
        validate_completed_trick_structure(
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "north"],
            }
        )
    except ValueError as error:
        assert "Invalid completed_trick player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_structure_rejects_invalid_winner_player() -> None:
    try:
        validate_completed_trick_structure(
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "me"],
                "winner_player": "north",
            }
        )
    except ValueError as error:
        assert "Invalid completed_trick winner_player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_structure_rejects_invalid_winner_role() -> None:
    try:
        validate_completed_trick_structure(
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "me"],
                "winner_role": "solo",
            }
        )
    except ValueError as error:
        assert "Invalid completed_trick winner_role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_structure_rejects_winner_player_not_in_players() -> None:
    try:
        validate_completed_trick_structure(
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "me"],
                "winner_player": "north",
            }
        )
    except ValueError as error:
        assert "Invalid completed_trick winner_player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_completed_trick_structure_rejects_duplicate_players() -> None:
    try:
        validate_completed_trick_structure(
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "left", "me"],
            }
        )
    except ValueError as error:
        assert "three unique players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_get_expected_winner_role_for_player_when_me_is_declarer() -> None:
    assert get_expected_winner_role_for_player("me", "declarer") == "declarer"


def test_get_expected_winner_role_for_player_when_left_wins_against_declarer() -> None:
    assert get_expected_winner_role_for_player("left", "declarer") == "defenders"


def test_get_expected_winner_role_for_player_is_tolerant_for_defender_context() -> None:
    assert get_expected_winner_role_for_player("left", "defender") is None


def test_get_expected_winner_role_for_player_uses_concrete_defender_identity() -> None:
    assert get_expected_winner_role_for_player("left", "defender", "right") == "defenders"
    assert get_expected_winner_role_for_player("right", "defender", "right") == "declarer"


def test_validate_completed_trick_winner_consistency_accepts_consistent_role() -> None:
    validate_completed_trick_winner_consistency(
        completed_trick={
            "cards": ["S7", "S8", "SA"],
            "players": ["left", "right", "me"],
            "winner_player": "me",
            "winner_role": "declarer",
        },
        player_role="declarer",
    )


def test_validate_completed_trick_winner_consistency_rejects_inconsistent_role() -> None:
    try:
        validate_completed_trick_winner_consistency(
            completed_trick={
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "me"],
                "winner_player": "me",
                "winner_role": "defenders",
            },
            player_role="declarer",
        )
    except ValueError as error:
        assert "winner_role is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_winner_consistency_rejects_defender_side_conflict() -> None:
    try:
        validate_completed_trick_winner_consistency(
            completed_trick={
                "cards": ["S7", "S8", "SA"],
                "winner_player": "left",
                "winner_role": "declarer",
            },
            player_role="defender",
            declarer_player="right",
        )
    except ValueError as error:
        assert "winner_role is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_winner_consistency_accepts_valid_defender_side() -> None:
    validate_completed_trick_winner_consistency(
        completed_trick={
            "cards": ["S7", "S8", "SA"],
            "winner_player": "left",
            "winner_role": "defenders",
        },
        player_role="defender",
        declarer_player="right",
    )

def test_validate_completed_trick_rule_winner_accepts_correct_winner() -> None:
    validate_completed_trick_rule_winner(
        completed_trick={
            "cards": ["S7", "S8", "SA"],
            "players": ["left", "right", "me"],
            "winner_player": "me",
        },
        game_type="grand",
    )


def test_validate_completed_trick_rule_winner_rejects_wrong_winner() -> None:
    try:
        validate_completed_trick_rule_winner(
            completed_trick={
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "me"],
                "winner_player": "left",
            },
            game_type="grand",
        )
    except ValueError as error:
        assert "winner_player is inconsistent with trick rules" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_trick_rule_winner_accepts_grand_jack_winner() -> None:
    validate_completed_trick_rule_winner(
        completed_trick={
            "cards": ["SA", "CJ", "S10"],
            "players": ["left", "right", "me"],
            "winner_player": "right",
        },
        game_type="grand",
    )


def test_validate_completed_trick_rule_winner_is_tolerant_without_players() -> None:
    validate_completed_trick_rule_winner(
        completed_trick={
            "cards": ["S7", "S8", "SA"],
            "winner_player": "me",
        },
        game_type="grand",
    )


def test_validate_completed_trick_rule_winner_is_tolerant_without_winner_player() -> None:
    validate_completed_trick_rule_winner(
        completed_trick={
            "cards": ["S7", "S8", "SA"],
            "players": ["left", "right", "me"],
        },
        game_type="grand",
    )


def test_validate_completed_trick_sequence_rejects_rule_wrong_winner() -> None:
    try:
        validate_completed_trick_sequence(
            completed_tricks=[
                {
                    "cards": ["S7", "S8", "SA"],
                    "players": ["left", "right", "me"],
                    "winner_player": "left",
                }
            ],
            current_trick=[],
            trick_leader="unknown",
            player_role="unknown",
            game_type="grand",
        )
    except ValueError as error:
        assert "winner_player is inconsistent with trick rules" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
