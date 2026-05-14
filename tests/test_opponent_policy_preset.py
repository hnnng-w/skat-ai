from skat_ai.opponent_policy_preset import (
    apply_opponent_policy_preset,
    build_serializable_opponent_policy_presets,
    get_opponent_policy_settings_for_preset,
    validate_opponent_policy_preset,
)


def test_validate_opponent_policy_preset_accepts_valid_preset() -> None:
    validate_opponent_policy_preset("cautious_defender")


def test_validate_opponent_policy_preset_rejects_invalid_preset() -> None:
    try:
        validate_opponent_policy_preset("reckless")
    except ValueError as error:
        assert "Invalid opponent policy preset" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_opponent_policy_settings_for_simple_lowest() -> None:
    settings = get_opponent_policy_settings_for_preset("simple_lowest")

    assert settings == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_get_opponent_policy_settings_for_cautious_defender() -> None:
    settings = get_opponent_policy_settings_for_preset("cautious_defender")

    assert settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def test_get_opponent_policy_settings_for_aggressive_points() -> None:
    settings = get_opponent_policy_settings_for_preset("aggressive_points")

    assert settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }


def test_get_opponent_policy_settings_for_random() -> None:
    settings = get_opponent_policy_settings_for_preset("random")

    assert settings == {
        "opponent_lead_policy": "random_legal",
        "opponent_response_policy": "random_legal",
    }


def test_apply_opponent_policy_preset_returns_copy_without_preset() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "basic_trick_play",
    }

    updated_settings = apply_opponent_policy_preset(
        opponent_policy_settings=settings,
        preset=None,
    )

    assert updated_settings == settings
    assert updated_settings is not settings


def test_apply_opponent_policy_preset_overwrites_settings() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_opponent_policy_preset(
        opponent_policy_settings=settings,
        preset="cautious_defender",
    )

    assert updated_settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def test_build_serializable_opponent_policy_presets() -> None:
    result = build_serializable_opponent_policy_presets()

    assert "valid_presets" in result
    assert "presets" in result
    assert "cautious_defender" in result["valid_presets"]
    assert result["presets"]["cautious_defender"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }