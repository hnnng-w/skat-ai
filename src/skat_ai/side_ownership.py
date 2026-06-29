VALID_CONCRETE_PLAYERS = ["me", "left", "right"]
VALID_DECLARER_PLAYERS = [*VALID_CONCRETE_PLAYERS, "unknown"]
VALID_PLAYER_ROLES = ["declarer", "defender", "unknown"]
VALID_PLAYER_SIDES = ["declarer", "defenders"]


def validate_declarer_player_value(declarer_player: str) -> None:
    """Validates a declarer_player value."""
    if declarer_player not in VALID_DECLARER_PLAYERS:
        raise ValueError(f"Invalid declarer_player: {declarer_player}")


def normalize_declarer_player(
    player_role: str,
    declarer_player: str | None,
) -> str:
    """Returns the normalized concrete declarer player for a local role."""
    if player_role not in VALID_PLAYER_ROLES:
        raise ValueError(f"Invalid player role: {player_role}")

    if declarer_player is not None:
        validate_declarer_player_value(declarer_player)

    if player_role == "declarer":
        if declarer_player is None:
            return "me"

        if declarer_player == "me":
            return "me"

        raise ValueError("player_role='declarer' requires declarer_player to be 'me'.")

    if player_role == "defender":
        if declarer_player in ["left", "right"]:
            return declarer_player

        raise ValueError(
            "player_role='defender' requires declarer_player to be 'left' or 'right'."
        )

    if declarer_player in [None, "unknown"]:
        return "unknown"

    raise ValueError(
        "player_role='unknown' requires declarer_player to be missing or 'unknown'."
    )


def get_player_side(
    player: str,
    declarer_player: str,
) -> str | None:
    """Returns a concrete player's side, or None when declarer identity is unresolved."""
    if player not in VALID_CONCRETE_PLAYERS:
        raise ValueError(f"Invalid player: {player}")

    validate_declarer_player_value(declarer_player)

    if declarer_player == "unknown":
        return None

    if player == declarer_player:
        return "declarer"

    return "defenders"


def get_winner_role(
    winner_player: str,
    declarer_player: str,
) -> str | None:
    """Returns the side that won a trick, or None when ownership is unresolved."""
    return get_player_side(
        player=winner_player,
        declarer_player=declarer_player,
    )


def get_defender_partner(
    declarer_player: str,
) -> str | None:
    """Returns the local defender partner for the fixed three-player table."""
    validate_declarer_player_value(declarer_player)

    if declarer_player == "left":
        return "right"

    if declarer_player == "right":
        return "left"

    return None


def did_local_side_win(
    winner_player: str,
    player_role: str,
    declarer_player: str,
) -> bool | None:
    """Returns whether the local side won, or None when ownership is unresolved."""
    winner_role = get_winner_role(
        winner_player=winner_player,
        declarer_player=declarer_player,
    )

    return did_local_side_win_for_winner_role(
        winner_role=winner_role,
        player_role=player_role,
    )


def did_local_side_win_for_winner_role(
    winner_role: str | None,
    player_role: str,
) -> bool | None:
    """Returns whether the local side won from an already-resolved winner side."""
    if player_role not in VALID_PLAYER_ROLES:
        raise ValueError(f"Invalid player role: {player_role}")

    if winner_role is not None and winner_role not in VALID_PLAYER_SIDES:
        raise ValueError(f"Invalid winner role: {winner_role}")

    if winner_role is None:
        return None

    if player_role == "declarer":
        return winner_role == "declarer"

    if player_role == "defender":
        return winner_role == "defenders"

    return None
