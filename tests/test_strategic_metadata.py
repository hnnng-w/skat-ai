from skat_ai.strategic_metadata import (
    StrategicMetadata,
    build_default_strategic_metadata,
    build_strategic_metadata_from_dict,
    validate_analysis_mode,
    validate_analysis_mode_skat_visibility_combination,
    validate_game_end_reason,
    validate_skat_visibility,
    validate_strategic_metadata,
)


def test_build_default_strategic_metadata() -> None:
    metadata = build_default_strategic_metadata()

    assert metadata == StrategicMetadata(
        analysis_mode="live_decision",
        skat_visibility="unknown",
        game_end_reason="not_ended",
    )


def test_build_strategic_metadata_from_dict() -> None:
    metadata = build_strategic_metadata_from_dict(
        {
            "analysis_mode": "post_game_review",
            "skat_visibility": "known_post_game",
            "game_end_reason": "normal_completion",
        }
    )

    assert metadata.analysis_mode == "post_game_review"
    assert metadata.skat_visibility == "known_post_game"
    assert metadata.game_end_reason == "normal_completion"


def test_build_strategic_metadata_from_partial_dict() -> None:
    metadata = build_strategic_metadata_from_dict(
        {
            "analysis_mode": "post_game_review",
        }
    )

    assert metadata.analysis_mode == "post_game_review"
    assert metadata.skat_visibility == "unknown"
    assert metadata.game_end_reason == "not_ended"


def test_validate_analysis_mode_accepts_valid_value() -> None:
    validate_analysis_mode("live_decision")


def test_validate_analysis_mode_rejects_invalid_value() -> None:
    try:
        validate_analysis_mode("future_mode")
    except ValueError as error:
        assert "Invalid analysis mode" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_skat_visibility_accepts_valid_value() -> None:
    validate_skat_visibility("known_post_game")


def test_validate_skat_visibility_rejects_invalid_value() -> None:
    try:
        validate_skat_visibility("visible_to_everyone")
    except ValueError as error:
        assert "Invalid skat visibility" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_end_reason_accepts_valid_value() -> None:
    validate_game_end_reason("defenders_conceded_remaining_tricks")


def test_validate_game_end_reason_rejects_invalid_value() -> None:
    try:
        validate_game_end_reason("rage_quit")
    except ValueError as error:
        assert "Invalid game end reason" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_strategic_metadata_accepts_valid_metadata() -> None:
    metadata = StrategicMetadata(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
        game_end_reason="normal_completion",
    )

    validate_strategic_metadata(metadata)


def test_validate_strategic_metadata_rejects_invalid_metadata() -> None:
    metadata = StrategicMetadata(
        analysis_mode="invalid",
        skat_visibility="unknown",
        game_end_reason="not_ended",
    )

    try:
        validate_strategic_metadata(metadata)
    except ValueError as error:
        assert "Invalid analysis mode" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_strategic_metadata_rejects_live_known_post_game_skat() -> None:
    metadata = StrategicMetadata(
        analysis_mode="live_decision",
        skat_visibility="known_post_game",
        game_end_reason="not_ended",
    )

    try:
        validate_strategic_metadata(metadata)
    except ValueError as error:
        assert "known_post_game" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_analysis_mode_skat_visibility_accepts_live_unknown() -> None:
    validate_analysis_mode_skat_visibility_combination(
        analysis_mode="live_decision",
        skat_visibility="unknown",
    )


def test_validate_analysis_mode_skat_visibility_accepts_post_game_known() -> None:
    validate_analysis_mode_skat_visibility_combination(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
    )


def test_validate_analysis_mode_skat_visibility_rejects_live_known_post_game() -> None:
    try:
        validate_analysis_mode_skat_visibility_combination(
            analysis_mode="live_decision",
            skat_visibility="known_post_game",
        )
    except ValueError as error:
        assert "known_post_game" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")