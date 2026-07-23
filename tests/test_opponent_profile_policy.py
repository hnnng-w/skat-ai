from skat_ai.opponent_profile_policy import (
    apply_profile_based_policy_preset,
    apply_profile_based_side_policy_preset,
    choose_actionable_profile_policy_preset,
    choose_combined_profile_policy_preset,
    choose_opponent_policy_preset_for_profile,
    get_profile_data_confidence,
    is_aggressive_profile,
    is_cautious_defender_profile,
)
from skat_ai.player_profile import PlayerProfile


def test_get_profile_data_confidence_unknown() -> None:
    profile = PlayerProfile()

    assert get_profile_data_confidence(profile) == "unknown"


def test_get_profile_data_confidence_low() -> None:
    profile = PlayerProfile(games_played=50)

    assert get_profile_data_confidence(profile) == "low"


def test_get_profile_data_confidence_medium() -> None:
    profile = PlayerProfile(games_played=250)

    assert get_profile_data_confidence(profile) == "medium"


def test_get_profile_data_confidence_high() -> None:
    profile = PlayerProfile(games_played=1000)

    assert get_profile_data_confidence(profile) == "high"


def test_is_aggressive_profile_by_solo_rate() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.36,
    )

    assert is_aggressive_profile(profile) is True


def test_is_aggressive_profile_by_grand_rate() -> None:
    profile = PlayerProfile(
        games_played=1000,
        grand_rate=0.25,
    )

    assert is_aggressive_profile(profile) is True


def test_is_aggressive_profile_by_hand_game_rate() -> None:
    profile = PlayerProfile(
        games_played=1000,
        hand_game_rate=0.10,
    )

    assert is_aggressive_profile(profile) is True


def test_is_aggressive_profile_returns_false_for_neutral_profile() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
    )

    assert is_aggressive_profile(profile) is False


def test_is_cautious_defender_profile() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )

    assert is_cautious_defender_profile(profile) is True


def test_is_cautious_defender_profile_requires_confidence() -> None:
    profile = PlayerProfile(
        games_played=50,
        defender_win_rate=0.55,
    )

    assert is_cautious_defender_profile(profile) is False


def test_is_cautious_defender_profile_rejects_aggressive_profile() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.40,
        defender_win_rate=0.55,
    )

    assert is_cautious_defender_profile(profile) is False


def test_choose_opponent_policy_preset_for_unknown_profile() -> None:
    profile = PlayerProfile()

    assert choose_opponent_policy_preset_for_profile(profile) == "simple_lowest"


def test_choose_opponent_policy_preset_for_low_confidence_profile() -> None:
    profile = PlayerProfile(
        games_played=20,
        defender_win_rate=0.60,
    )

    assert choose_opponent_policy_preset_for_profile(profile) == "simple_lowest"


def test_choose_opponent_policy_preset_for_low_confidence_aggressive_profile() -> None:
    profile = PlayerProfile(
        games_played=20,
        solo_rate=0.40,
        grand_rate=0.30,
    )

    assert choose_opponent_policy_preset_for_profile(profile) == "simple_lowest"


def test_choose_opponent_policy_preset_for_aggressive_profile() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.38,
        grand_rate=0.27,
    )

    assert choose_opponent_policy_preset_for_profile(profile) == "aggressive_points"


def test_choose_opponent_policy_preset_for_cautious_defender_profile() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )

    assert choose_opponent_policy_preset_for_profile(profile) == "cautious_defender"


def test_choose_opponent_policy_preset_for_neutral_profile() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.50,
    )

    assert choose_opponent_policy_preset_for_profile(profile) == "simple_lowest"


def test_unknown_profile_has_no_actionable_preset() -> None:
    profile = PlayerProfile()

    assert choose_actionable_profile_policy_preset(profile) is None


def test_low_confidence_aggressive_profile_has_no_actionable_preset() -> None:
    profile = PlayerProfile(
        games_played=20,
        solo_rate=0.40,
        grand_rate=0.30,
    )

    assert choose_actionable_profile_policy_preset(profile) is None


def test_grand_signal_uses_declarer_confidence_in_legacy_helpers() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.05,
        grand_rate=0.30,
    )

    assert get_profile_data_confidence(profile) == "high"
    assert is_aggressive_profile(profile) is True
    assert choose_opponent_policy_preset_for_profile(profile) == "simple_lowest"
    assert choose_actionable_profile_policy_preset(profile) is None


def test_defender_signal_uses_defender_confidence_in_legacy_helpers() -> None:
    profile = PlayerProfile(
        games_played=1000,
        defender_rate=0.05,
        defender_win_rate=0.60,
    )

    assert get_profile_data_confidence(profile) == "high"
    assert is_cautious_defender_profile(profile) is False
    assert choose_opponent_policy_preset_for_profile(profile) == "simple_lowest"
    assert choose_actionable_profile_policy_preset(profile) is None


def test_low_confidence_cautious_profile_has_no_actionable_preset() -> None:
    profile = PlayerProfile(
        games_played=20,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.60,
    )

    assert choose_actionable_profile_policy_preset(profile) is None


def test_medium_confidence_aggressive_profile_is_actionable() -> None:
    profile = PlayerProfile(
        games_played=250,
        solo_rate=0.38,
        grand_rate=0.27,
    )

    assert choose_actionable_profile_policy_preset(profile) == "aggressive_points"


def test_high_confidence_cautious_profile_is_actionable() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )

    assert choose_actionable_profile_policy_preset(profile) == "cautious_defender"


def test_neutral_medium_high_profile_has_no_actionable_preset() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.50,
    )

    assert choose_actionable_profile_policy_preset(profile) is None


def test_choose_combined_profile_policy_preset_prefers_aggressive() -> None:
    left_profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.38,
    )
    right_profile = PlayerProfile(
        games_played=1000,
        defender_win_rate=0.55,
    )

    preset = choose_combined_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    assert preset == "aggressive_points"


def test_choose_combined_profile_policy_preset_prefers_higher_confidence_signal() -> None:
    left_profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )
    right_profile = PlayerProfile(
        games_played=250,
        solo_rate=0.38,
        grand_rate=0.27,
    )

    preset = choose_combined_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    assert preset == "cautious_defender"


def test_choose_combined_profile_policy_preset_prefers_higher_aggressive_confidence() -> None:
    left_profile = PlayerProfile(
        games_played=250,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )
    right_profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.38,
        grand_rate=0.27,
    )

    preset = choose_combined_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    assert preset == "aggressive_points"


def test_choose_combined_profile_policy_preset_uses_cautious_defender() -> None:
    left_profile = PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )
    right_profile = PlayerProfile()

    preset = choose_combined_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    assert preset == "cautious_defender"


def test_choose_combined_profile_policy_preset_falls_back_to_simple_lowest() -> None:
    left_profile = PlayerProfile()
    right_profile = PlayerProfile()

    preset = choose_combined_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    assert preset == "simple_lowest"


def test_apply_profile_based_policy_preset_returns_copy_when_disabled() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_profile_based_policy_preset(
        opponent_policy_settings=settings,
        left_profile=PlayerProfile(games_played=1000, solo_rate=0.38),
        right_profile=PlayerProfile(),
        use_profile_presets=False,
    )

    assert updated_settings == settings
    assert updated_settings is not settings


def test_apply_profile_based_policy_preset_preserves_non_actionable_profiles() -> None:
    settings = {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }

    updated_settings = apply_profile_based_policy_preset(
        opponent_policy_settings=settings,
        left_profile=PlayerProfile(games_played=20, solo_rate=0.40),
        right_profile=PlayerProfile(
            games_played=1000,
            solo_rate=0.25,
            grand_rate=0.15,
            hand_game_rate=0.03,
            defender_win_rate=0.50,
        ),
        use_profile_presets=True,
    )

    assert updated_settings == settings
    assert updated_settings is not settings


def test_apply_profile_based_policy_preset_applies_aggressive_profile() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_profile_based_policy_preset(
        opponent_policy_settings=settings,
        left_profile=PlayerProfile(games_played=1000, solo_rate=0.38),
        right_profile=PlayerProfile(),
        use_profile_presets=True,
    )

    assert updated_settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }


def test_apply_profile_based_policy_preset_applies_actionable_profile() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_profile_based_policy_preset(
        opponent_policy_settings=settings,
        left_profile=PlayerProfile(),
        right_profile=PlayerProfile(games_played=250, solo_rate=0.38),
        use_profile_presets=True,
    )

    assert updated_settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }


def test_apply_profile_based_policy_preset_applies_cautious_defender_profile() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_profile_based_policy_preset(
        opponent_policy_settings=settings,
        left_profile=PlayerProfile(
            games_played=1000,
            solo_rate=0.25,
            grand_rate=0.15,
            hand_game_rate=0.03,
            defender_win_rate=0.55,
        ),
        right_profile=PlayerProfile(),
        use_profile_presets=True,
    )

    assert updated_settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def test_apply_profile_based_side_policy_preset_returns_copy_when_disabled() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_profile_based_side_policy_preset(
        opponent_policy_settings=settings,
        profile=PlayerProfile(games_played=1000, solo_rate=0.38),
        use_profile_presets=False,
    )

    assert updated_settings == settings
    assert updated_settings is not settings


def test_apply_profile_based_side_policy_preset_keeps_unknown_profile() -> None:
    settings = {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }

    updated_settings = apply_profile_based_side_policy_preset(
        opponent_policy_settings=settings,
        profile=PlayerProfile(),
        use_profile_presets=True,
    )

    assert updated_settings == settings
    assert updated_settings is not settings


def test_apply_profile_based_side_policy_preset_keeps_low_confidence_profile() -> None:
    settings = {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }

    updated_settings = apply_profile_based_side_policy_preset(
        opponent_policy_settings=settings,
        profile=PlayerProfile(games_played=20, solo_rate=0.40, grand_rate=0.30),
        use_profile_presets=True,
    )

    assert updated_settings == settings
    assert updated_settings is not settings


def test_apply_profile_based_side_policy_preset_keeps_neutral_profile() -> None:
    settings = {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }

    updated_settings = apply_profile_based_side_policy_preset(
        opponent_policy_settings=settings,
        profile=PlayerProfile(
            games_played=1000,
            solo_rate=0.25,
            grand_rate=0.15,
            hand_game_rate=0.03,
            defender_win_rate=0.50,
        ),
        use_profile_presets=True,
    )

    assert updated_settings == settings
    assert updated_settings is not settings


def test_apply_profile_based_side_policy_preset_applies_aggressive_profile() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_profile_based_side_policy_preset(
        opponent_policy_settings=settings,
        profile=PlayerProfile(games_played=1000, solo_rate=0.38),
        use_profile_presets=True,
    )

    assert updated_settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }


def test_apply_profile_based_side_policy_preset_applies_cautious_profile() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_profile_based_side_policy_preset(
        opponent_policy_settings=settings,
        profile=PlayerProfile(
            games_played=1000,
            solo_rate=0.25,
            grand_rate=0.15,
            hand_game_rate=0.03,
            defender_win_rate=0.55,
        ),
        use_profile_presets=True,
    )

    assert updated_settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
