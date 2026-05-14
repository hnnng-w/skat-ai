from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerProfile:
    """
    Describes long-term player tendencies.

    This is currently a placeholder for future opponent modeling.
    The simulation engine does not use these values yet.
    """
    solo_rate: float | None = None
    solo_win_rate: float | None = None
    hand_game_rate: float | None = None
    suit_game_rate: float | None = None
    grand_rate: float | None = None
    null_game_rate: float | None = None
    defender_win_rate: float | None = None


def build_default_player_profile() -> PlayerProfile:
    """
    Builds a neutral player profile.

    The default profile intentionally contains no assumptions.
    """
    return PlayerProfile()


def build_player_profile_from_dict(
    data: dict[str, float | None],
) -> PlayerProfile:
    """
    Builds a PlayerProfile from a dictionary.
    """
    return PlayerProfile(
        solo_rate=data.get("solo_rate"),
        solo_win_rate=data.get("solo_win_rate"),
        hand_game_rate=data.get("hand_game_rate"),
        suit_game_rate=data.get("suit_game_rate"),
        grand_rate=data.get("grand_rate"),
        null_game_rate=data.get("null_game_rate"),
        defender_win_rate=data.get("defender_win_rate"),
    )