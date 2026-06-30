import pytest

from skat_ai.turn_phase import (
    TurnPhase,
    derive_next_player,
    derive_trick_leader,
    normalize_turn_phase,
    validate_turn_phase,
)

CANONICAL_PHASES = [
    ("me", 0, "me"),
    ("me", 1, "left"),
    ("me", 2, "right"),
    ("left", 0, "left"),
    ("left", 1, "right"),
    ("left", 2, "me"),
    ("right", 0, "right"),
    ("right", 1, "me"),
    ("right", 2, "left"),
]


@pytest.mark.parametrize(
    ("trick_leader", "current_trick_length", "next_player"),
    CANONICAL_PHASES,
)
def test_derive_next_player_covers_canonical_table(
    trick_leader: str,
    current_trick_length: int,
    next_player: str,
) -> None:
    assert derive_next_player(trick_leader, current_trick_length) == next_player


@pytest.mark.parametrize(
    ("trick_leader", "current_trick_length", "next_player"),
    CANONICAL_PHASES,
)
def test_derive_trick_leader_covers_reverse_canonical_table(
    trick_leader: str,
    current_trick_length: int,
    next_player: str,
) -> None:
    assert derive_trick_leader(next_player, current_trick_length) == trick_leader


@pytest.mark.parametrize(
    ("trick_leader", "current_trick_length", "next_player"),
    CANONICAL_PHASES,
)
def test_normalize_turn_phase_accepts_concrete_consistency(
    trick_leader: str,
    current_trick_length: int,
    next_player: str,
) -> None:
    phase = normalize_turn_phase(
        trick_leader=trick_leader,
        next_player=next_player,
        current_trick_length=current_trick_length,
    )

    assert phase == TurnPhase(
        trick_leader=trick_leader,
        next_player=next_player,
    )


def test_normalize_turn_phase_rejects_concrete_contradiction() -> None:
    with pytest.raises(ValueError, match="turn phase is inconsistent"):
        normalize_turn_phase(
            trick_leader="left",
            next_player="me",
            current_trick_length=1,
        )


def test_normalize_turn_phase_derives_unknown_next_from_concrete_leader() -> None:
    phase = normalize_turn_phase(
        trick_leader="right",
        next_player="unknown",
        current_trick_length=1,
    )

    assert phase == TurnPhase(trick_leader="right", next_player="me")


def test_normalize_turn_phase_derives_missing_next_from_concrete_leader() -> None:
    phase = normalize_turn_phase(
        trick_leader="left",
        next_player=None,
        current_trick_length=2,
    )

    assert phase == TurnPhase(trick_leader="left", next_player="me")


def test_normalize_turn_phase_derives_unknown_leader_from_concrete_next() -> None:
    phase = normalize_turn_phase(
        trick_leader="unknown",
        next_player="me",
        current_trick_length=1,
    )

    assert phase == TurnPhase(trick_leader="right", next_player="me")


def test_normalize_turn_phase_derives_missing_leader_from_concrete_next() -> None:
    phase = normalize_turn_phase(
        trick_leader=None,
        next_player="right",
        current_trick_length=2,
    )

    assert phase == TurnPhase(trick_leader="me", next_player="right")


def test_normalize_turn_phase_rejects_unsupported_trick_length() -> None:
    with pytest.raises(ValueError, match="current_trick length"):
        normalize_turn_phase(
            trick_leader="me",
            next_player="me",
            current_trick_length=3,
        )


def test_normalize_turn_phase_rejects_non_empty_unknown_unknown() -> None:
    with pytest.raises(ValueError, match="Cannot determine turn phase"):
        normalize_turn_phase(
            trick_leader="unknown",
            next_player="unknown",
            current_trick_length=1,
        )


def test_normalize_turn_phase_preserves_empty_unknown_unknown() -> None:
    phase = normalize_turn_phase(
        trick_leader="unknown",
        next_player="unknown",
        current_trick_length=0,
    )

    assert phase == TurnPhase(trick_leader="unknown", next_player="unknown")


def test_normalize_turn_phase_uses_required_trick_leader() -> None:
    phase = normalize_turn_phase(
        trick_leader="unknown",
        next_player="unknown",
        current_trick_length=0,
        required_trick_leader="left",
    )

    assert phase == TurnPhase(trick_leader="left", next_player="left")


def test_normalize_turn_phase_rejects_required_leader_conflict() -> None:
    with pytest.raises(ValueError, match="completed_tricks"):
        normalize_turn_phase(
            trick_leader="right",
            next_player="right",
            current_trick_length=0,
            required_trick_leader="left",
        )


def test_validate_turn_phase_accepts_valid_phase() -> None:
    validate_turn_phase(
        trick_leader="left",
        next_player="me",
        current_trick_length=2,
    )
