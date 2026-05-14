from skat_ai.opponent_profile_policy import (
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