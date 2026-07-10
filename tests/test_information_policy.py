from skat_ai.information_policy import (
    build_information_policy_summary,
    is_live_information_enforced,
    validate_information_policy_from_input,
    validate_live_completed_trick_metadata,
)


def test_is_live_information_enforced_for_live_decision() -> None:
    assert is_live_information_enforced("live_decision") is True


def test_is_live_information_enforced_for_post_game_review() -> None:
    assert is_live_information_enforced("post_game_review") is False


def test_build_information_policy_summary_for_live_decision() -> None:
    assert build_information_policy_summary(
        analysis_mode="live_decision",
        skat_visibility="unknown",
        game_end_reason="not_ended",
    ) == {
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "live_information_enforced": True,
        "known_post_game_skat_allowed": False,
        "known_skat_cards_allowed": False,
        "ended_game_allowed": False,
        "unverifiable_completed_trick_winner_metadata_allowed": False,
    }


def test_build_information_policy_summary_for_post_game_review() -> None:
    assert build_information_policy_summary(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
        game_end_reason="normal_completion",
    ) == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "normal_completion",
        "live_information_enforced": False,
        "known_post_game_skat_allowed": True,
        "known_skat_cards_allowed": True,
        "ended_game_allowed": True,
        "unverifiable_completed_trick_winner_metadata_allowed": True,
    }


def test_build_information_policy_summary_allows_live_declarer_private_skat() -> None:
    assert build_information_policy_summary(
        analysis_mode="live_decision",
        skat_visibility="known_to_declarer",
        game_end_reason="not_ended",
    ) == {
        "analysis_mode": "live_decision",
        "skat_visibility": "known_to_declarer",
        "game_end_reason": "not_ended",
        "live_information_enforced": True,
        "known_post_game_skat_allowed": False,
        "known_skat_cards_allowed": True,
        "ended_game_allowed": False,
        "unverifiable_completed_trick_winner_metadata_allowed": False,
    }


def test_validate_live_completed_trick_metadata_rejects_side_only_winner_role() -> None:
    try:
        validate_live_completed_trick_metadata(
            analysis_mode="live_decision",
            completed_tricks=[
                {
                    "cards": ["SA", "S7", "S8"],
                    "winner_role": "defenders",
                }
            ],
        )
    except ValueError as error:
        assert "winner_role" in str(error)
        assert "players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_live_completed_trick_metadata_allows_post_game_side_only_history() -> None:
    validate_live_completed_trick_metadata(
        analysis_mode="post_game_review",
        completed_tricks=[
            {
                "cards": ["SA", "S7", "S8"],
                "winner_role": "defenders",
            }
        ],
    )


def test_validate_information_policy_rejects_live_unverifiable_winner_role() -> None:
    try:
        validate_information_policy_from_input(
            {
                "analysis_mode": "live_decision",
                "game_type": "grand",
                "player_role": "unknown",
                "declarer_player": "unknown",
                "skat_visibility": "unknown",
                "completed_tricks": [
                    {
                        "cards": ["SA", "S7", "S8"],
                        "players": ["left", "right", "me"],
                        "winner_role": "declarer",
                    }
                ],
            }
        )
    except ValueError as error:
        assert "winner_role cannot be verified" in str(error)
        assert "concrete declarer_player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
