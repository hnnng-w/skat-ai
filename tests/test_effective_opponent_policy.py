from skat_ai.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skat_ai.opponent_profile_policy import choose_combined_profile_policy_preset
from skat_ai.player_profile import PlayerProfile


def assert_effective_settings(
    settings: EffectiveOpponentPolicySettings,
    global_lead_policy: str = "lowest_point",
    global_response_policy: str = "lowest_point",
    left_lead_policy: str = "lowest_point",
    left_response_policy: str = "lowest_point",
    right_lead_policy: str = "lowest_point",
    right_response_policy: str = "lowest_point",
    immediate_response_policy_by_player: dict[str, str] | None = None,
) -> None:
    assert settings.global_lead_policy == global_lead_policy
    assert settings.global_response_policy == global_response_policy
    assert settings.left_lead_policy == left_lead_policy
    assert settings.left_response_policy == left_response_policy
    assert settings.right_lead_policy == right_lead_policy
    assert settings.right_response_policy == right_response_policy
    assert settings.immediate_response_policy_by_player == immediate_response_policy_by_player


def build_aggressive_profile(games_played: int = 1000) -> PlayerProfile:
    return PlayerProfile(
        games_played=games_played,
        solo_rate=0.38,
        grand_rate=0.27,
    )


def build_cautious_profile(games_played: int = 1000) -> PlayerProfile:
    return PlayerProfile(
        games_played=games_played,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )


def build_neutral_profile() -> PlayerProfile:
    return PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.50,
    )


def test_effective_policy_defaults_do_not_activate_immediate_policy_mode() -> None:
    settings = build_effective_opponent_policy_settings({})

    assert_effective_settings(settings)


def test_profiles_present_but_disabled_do_not_activate_policies() -> None:
    settings = build_effective_opponent_policy_settings(
        {},
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert_effective_settings(settings)


def test_false_profile_preset_flag_does_not_activate_policies() -> None:
    settings = build_effective_opponent_policy_settings(
        {"use_profile_presets": False},
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert_effective_settings(settings)


def test_input_global_preset_applies_to_global_and_both_sides() -> None:
    settings = build_effective_opponent_policy_settings(
        {"opponent_policy_preset": "cautious_defender"},
    )

    assert_effective_settings(
        settings,
        global_lead_policy="basic_defender_lead",
        global_response_policy="basic_defender_response",
        left_lead_policy="basic_defender_lead",
        left_response_policy="basic_defender_response",
        right_lead_policy="basic_defender_lead",
        right_response_policy="basic_defender_response",
        immediate_response_policy_by_player={
            "left": "basic_defender_response",
            "right": "basic_defender_response",
        },
    )


def test_explicit_input_global_policies_override_input_preset_by_dimension() -> None:
    settings = build_effective_opponent_policy_settings(
        {
            "opponent_policy_preset": "cautious_defender",
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "lowest_point",
        },
    )

    assert_effective_settings(
        settings,
        global_lead_policy="highest_point",
        global_response_policy="lowest_point",
        left_lead_policy="highest_point",
        left_response_policy="lowest_point",
        right_lead_policy="highest_point",
        right_response_policy="lowest_point",
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "lowest_point",
        },
    )


def test_input_profile_derived_policies_affect_their_side() -> None:
    settings = build_effective_opponent_policy_settings(
        {"use_profile_presets": True},
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert_effective_settings(
        settings,
        left_lead_policy="basic_defender_lead",
        left_response_policy="basic_defender_response",
        right_lead_policy="highest_point",
        right_response_policy="highest_point",
        immediate_response_policy_by_player={
            "left": "basic_defender_response",
            "right": "highest_point",
        },
    )


def test_explicit_input_side_values_override_input_profiles_and_global_values() -> None:
    settings = build_effective_opponent_policy_settings(
        {
            "opponent_policy_preset": "aggressive_points",
            "use_profile_presets": True,
            "left_opponent_lead_policy": "lowest_point",
            "left_opponent_response_policy": "lowest_point",
        },
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert_effective_settings(
        settings,
        global_lead_policy="highest_point",
        global_response_policy="highest_point",
        left_lead_policy="lowest_point",
        left_response_policy="lowest_point",
        right_lead_policy="highest_point",
        right_response_policy="highest_point",
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "highest_point",
        },
    )


def test_side_only_input_response_creates_sparse_immediate_map() -> None:
    settings = build_effective_opponent_policy_settings(
        {"left_opponent_response_policy": "highest_point"},
    )

    assert_effective_settings(
        settings,
        left_response_policy="highest_point",
        immediate_response_policy_by_player={"left": "highest_point"},
    )


def test_global_cli_preset_applies_to_both_sides() -> None:
    settings = build_effective_opponent_policy_settings(
        {},
        opponent_policy_preset_override="random",
    )

    assert_effective_settings(
        settings,
        global_lead_policy="random_legal",
        global_response_policy="random_legal",
        left_lead_policy="random_legal",
        left_response_policy="random_legal",
        right_lead_policy="random_legal",
        right_response_policy="random_legal",
        immediate_response_policy_by_player={
            "left": "random_legal",
            "right": "random_legal",
        },
    )


def test_cli_profile_activation_overrides_global_cli_preset_by_side() -> None:
    settings = build_effective_opponent_policy_settings(
        {},
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_neutral_profile(),
        opponent_policy_preset_override="random",
        use_profile_presets_override=True,
    )

    assert_effective_settings(
        settings,
        global_lead_policy="random_legal",
        global_response_policy="random_legal",
        left_lead_policy="basic_defender_lead",
        left_response_policy="basic_defender_response",
        right_lead_policy="random_legal",
        right_response_policy="random_legal",
        immediate_response_policy_by_player={
            "left": "basic_defender_response",
            "right": "random_legal",
        },
    )


def test_explicit_global_cli_policies_apply_to_both_sides_by_dimension() -> None:
    settings = build_effective_opponent_policy_settings(
        {"left_opponent_response_policy": "basic_defender_response"},
        opponent_lead_policy_override="highest_point",
        opponent_response_policy_override="lowest_point",
    )

    assert_effective_settings(
        settings,
        global_lead_policy="highest_point",
        global_response_policy="lowest_point",
        left_lead_policy="highest_point",
        left_response_policy="lowest_point",
        right_lead_policy="highest_point",
        right_response_policy="lowest_point",
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "lowest_point",
        },
    )


def test_explicit_side_cli_values_remain_final() -> None:
    settings = build_effective_opponent_policy_settings(
        {"left_opponent_response_policy": "basic_defender_response"},
        opponent_response_policy_override="highest_point",
        left_opponent_response_policy_override="lowest_point",
        right_opponent_lead_policy_override="basic_defender_lead",
    )

    assert_effective_settings(
        settings,
        global_response_policy="highest_point",
        left_response_policy="lowest_point",
        right_lead_policy="basic_defender_lead",
        right_response_policy="highest_point",
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "highest_point",
        },
    )


def test_side_only_cli_response_creates_sparse_immediate_map() -> None:
    settings = build_effective_opponent_policy_settings(
        {},
        right_opponent_response_policy_override="highest_point",
    )

    assert_effective_settings(
        settings,
        right_response_policy="highest_point",
        immediate_response_policy_by_player={"right": "highest_point"},
    )


def test_global_cli_preset_overrides_explicit_input_side_configuration() -> None:
    settings = build_effective_opponent_policy_settings(
        {
            "left_opponent_lead_policy": "basic_defender_lead",
            "left_opponent_response_policy": "basic_defender_response",
            "right_opponent_response_policy": "lowest_point",
        },
        opponent_policy_preset_override="aggressive_points",
    )

    assert_effective_settings(
        settings,
        global_lead_policy="highest_point",
        global_response_policy="highest_point",
        left_lead_policy="highest_point",
        left_response_policy="highest_point",
        right_lead_policy="highest_point",
        right_response_policy="highest_point",
        immediate_response_policy_by_player={
            "left": "highest_point",
            "right": "highest_point",
        },
    )


def test_cli_activated_profile_loses_to_explicit_global_cli_response() -> None:
    settings = build_effective_opponent_policy_settings(
        {},
        right_player_profile=build_aggressive_profile(),
        use_profile_presets_override=True,
        opponent_response_policy_override="lowest_point",
    )

    assert_effective_settings(
        settings,
        global_response_policy="lowest_point",
        left_response_policy="lowest_point",
        right_lead_policy="highest_point",
        right_response_policy="lowest_point",
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "lowest_point",
        },
    )


def test_explicit_global_cli_response_loses_to_explicit_side_cli_response() -> None:
    settings = build_effective_opponent_policy_settings(
        {},
        opponent_response_policy_override="highest_point",
        left_opponent_response_policy_override="lowest_point",
    )

    assert_effective_settings(
        settings,
        global_response_policy="highest_point",
        left_response_policy="lowest_point",
        right_response_policy="highest_point",
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "highest_point",
        },
    )


def test_lead_and_response_are_overridden_independently() -> None:
    settings = build_effective_opponent_policy_settings(
        {
            "opponent_policy_preset": "cautious_defender",
            "left_opponent_response_policy": "highest_point",
        },
        opponent_lead_policy_override="random_legal",
    )

    assert_effective_settings(
        settings,
        global_lead_policy="random_legal",
        global_response_policy="basic_defender_response",
        left_lead_policy="random_legal",
        left_response_policy="highest_point",
        right_lead_policy="random_legal",
        right_response_policy="basic_defender_response",
        immediate_response_policy_by_player={
            "left": "highest_point",
            "right": "basic_defender_response",
        },
    )


def test_non_applicable_profile_result_does_not_create_immediate_entry() -> None:
    settings = build_effective_opponent_policy_settings(
        {"use_profile_presets": True},
        left_player_profile=build_neutral_profile(),
        right_player_profile=PlayerProfile(),
    )

    assert_effective_settings(settings)


def test_profile_confidence_logic_is_reused_for_side_policies() -> None:
    settings = build_effective_opponent_policy_settings(
        {"use_profile_presets": True},
        left_player_profile=build_aggressive_profile(games_played=20),
        right_player_profile=build_cautious_profile(games_played=500),
    )

    assert choose_combined_profile_policy_preset(
        left_profile=build_aggressive_profile(games_played=250),
        right_profile=build_cautious_profile(games_played=1000),
    ) == "cautious_defender"
    assert_effective_settings(
        settings,
        right_lead_policy="basic_defender_lead",
        right_response_policy="basic_defender_response",
        immediate_response_policy_by_player={"right": "basic_defender_response"},
    )


def test_explicit_lowest_point_response_activates_immediate_policy_mode() -> None:
    settings = build_effective_opponent_policy_settings(
        {"opponent_response_policy": "lowest_point"},
    )

    assert_effective_settings(
        settings,
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "lowest_point",
        },
    )


def test_explicit_simple_lowest_preset_activates_immediate_policy_mode() -> None:
    settings = build_effective_opponent_policy_settings(
        {"opponent_policy_preset": "simple_lowest"},
    )

    assert_effective_settings(
        settings,
        immediate_response_policy_by_player={
            "left": "lowest_point",
            "right": "lowest_point",
        },
    )


def test_raw_key_presence_not_value_difference_determines_immediate_explicitness() -> None:
    implicit_settings = build_effective_opponent_policy_settings({})
    explicit_settings = build_effective_opponent_policy_settings(
        {"left_opponent_response_policy": "lowest_point"},
    )

    assert implicit_settings.immediate_response_policy_by_player is None
    assert explicit_settings.immediate_response_policy_by_player == {
        "left": "lowest_point",
    }
