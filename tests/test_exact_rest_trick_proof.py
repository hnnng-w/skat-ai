import pytest

from skat_ai.exact_rest_trick_proof import (
    ExactRemainingPlayState,
    build_exact_remaining_play_state,
    prove_defender_rest_tricks,
)


def build_one_trick_state(
    *,
    me: tuple[str, ...],
    left: tuple[str, ...],
    right: tuple[str, ...],
    leader: str = "left",
):
    return build_exact_remaining_play_state(
        game_type="grand",
        remaining_hands={"me": me, "left": left, "right": right},
        current_trick_cards=[],
        trick_leader=leader,
        next_player=leader,
    )


def test_exact_proof_accepts_forced_defender_trick() -> None:
    proof = prove_defender_rest_tricks(
        build_one_trick_state(me=("C7",), left=("CJ",), right=("C8",)),
        exposing_defender="left",
        declarer_player="me",
    )

    assert proof.status == "valid"
    assert proof.proof_complete is True
    assert proof.counterexample_found is False
    assert proof.evaluated_state_count == proof.memoized_state_count


def test_exact_proof_finds_declarer_counterexample() -> None:
    proof = prove_defender_rest_tricks(
        build_one_trick_state(me=("CA",), left=("C7",), right=("C8",)),
        exposing_defender="left",
        declarer_player="me",
    )

    assert proof.status == "invalid"
    assert proof.counterexample_found is True
    assert proof.line[-1].trick_winner == "me"


def test_exact_proof_is_deterministic_and_supports_state_dependent_play() -> None:
    state = build_exact_remaining_play_state(
        game_type="grand",
        remaining_hands={
            "me": ("CK", "S9"),
            "left": ("D7", "D8"),
            "right": ("D9", "H8"),
        },
        current_trick_cards=[],
        trick_leader="left",
        next_player="left",
    )

    first = prove_defender_rest_tricks(state, "me", "left")
    second = prove_defender_rest_tricks(state, "me", "left")

    assert first == second
    assert first.status == "valid"
    assert first.remaining_trick_count == 2


def test_current_trick_declarer_win_invalidates_claim() -> None:
    state = build_exact_remaining_play_state(
        game_type="grand",
        remaining_hands={"me": (), "left": (), "right": ("D7",)},
        current_trick_cards=["CA", "C7"],
        trick_leader="me",
        next_player="right",
    )

    proof = prove_defender_rest_tricks(state, "left", "me")

    assert proof.status == "invalid"
    assert proof.line[-1].trick_winner == "me"


def test_exposing_defender_uses_existential_legal_choice() -> None:
    state = build_exact_remaining_play_state(
        game_type="grand",
        remaining_hands={
            "me": ("CA", "C10"),
            "left": ("C7", "S7"),
            "right": ("SA", "S10"),
        },
        current_trick_cards=[],
        trick_leader="left",
        next_player="left",
    )

    proof = prove_defender_rest_tricks(state, "left", "me")

    assert proof.status == "valid"
    assert proof.line[0].card == "S7"


def test_non_exposing_defender_uses_universal_legal_choice() -> None:
    state = ExactRemainingPlayState(
        game_type="grand",
        hands=(("CA", "C10"), ("C7",), ("SA", "S7")),
        current_trick=(("left", "S10"),),
        next_player="right",
    )

    proof = prove_defender_rest_tricks(state, "left", "me")

    assert proof.status == "invalid"
    assert proof.line[0].player == "right"
    assert proof.line[0].card == "S7"


def test_exact_proof_retains_five_remaining_trick_bound() -> None:
    cards = (
        "CA",
        "C10",
        "CK",
        "CQ",
        "CJ",
        "C9",
        "C8",
        "C7",
        "SA",
        "S10",
        "SK",
        "SQ",
        "SJ",
        "S9",
        "S8",
        "S7",
        "HA",
        "H10",
    )
    state = build_exact_remaining_play_state(
        game_type="grand",
        remaining_hands={
            "me": cards[:6],
            "left": cards[6:12],
            "right": cards[12:],
        },
        current_trick_cards=[],
        trick_leader="left",
        next_player="left",
    )

    with pytest.raises(ValueError, match="at most five"):
        prove_defender_rest_tricks(state, "left", "me")
