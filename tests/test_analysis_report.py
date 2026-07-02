from skat_ai.analysis_report import (
    build_card_analysis_report,
    build_strategic_summary,
    calculate_expected_point_swing,
    format_card_analysis_report,
)
from skat_ai.game_state import GameState


def test_calculate_expected_point_swing() -> None:
    value = {
        "win_rate": 0.5,
        "average_trick_points": 12.0,
        "average_points_won": 8.0,
        "average_points_lost": 4.0,
    }

    assert calculate_expected_point_swing(value) == 4.0


def test_build_card_analysis_report_returns_one_row_per_legal_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert len(report) == 3

    cards = [row["card"] for row in report]
    assert set(cards) == {"SA", "S10", "S9"}


def test_build_card_analysis_report_contains_expected_fields() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    expected_keys = {
        "card",
        "win_rate",
        "average_trick_points",
        "average_points_won",
        "average_points_lost",
        "expected_point_swing",
        "is_recommended",
    }

    for row in report:
        assert set(row.keys()) == expected_keys


def test_build_card_analysis_report_is_sorted_by_expected_point_swing() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    swings = [row["expected_point_swing"] for row in report]

    assert swings == sorted(swings, reverse=True)


def test_build_card_analysis_report_sorts_null_by_contract_objective() -> None:
    state = GameState(
        game_type="null",
        player_role="declarer",
        declarer_player="me",
        hand=["CA", "C7"],
        current_trick=["C10", "C9"],
        trick_leader="left",
        next_player="me",
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=0,
        right_hand_size=0,
        sample_count=1,
        random_seed=42,
    )

    assert [row["card"] for row in report] == ["C7", "CA"]
    assert report[0]["is_recommended"] is True
    assert report[0]["expected_point_swing"] == -10.0
    assert report[1]["expected_point_swing"] == 21.0


def test_build_strategic_summary_uses_null_objective_wording() -> None:
    report = [
        {
            "card": "C7",
            "win_rate": 0.0,
            "average_trick_points": 10.0,
            "average_points_won": 0.0,
            "average_points_lost": 10.0,
            "expected_point_swing": -10.0,
            "is_recommended": True,
        },
        {
            "card": "CA",
            "win_rate": 1.0,
            "average_trick_points": 21.0,
            "average_points_won": 21.0,
            "average_points_lost": 0.0,
            "expected_point_swing": 21.0,
            "is_recommended": False,
        },
    ]

    summary = build_strategic_summary(
        report,
        game_type="null",
        player_role="declarer",
    )

    assert "Null contract objective" in summary
    assert "avoid taking any evaluated trick" in summary
    assert "expected point swing" not in summary


def test_format_card_analysis_report_contains_header_and_cards() -> None:
    report = [
        {
            "card": "SA",
            "win_rate": 0.75,
            "average_trick_points": 14.0,
            "average_points_won": 10.0,
            "average_points_lost": 4.0,
            "expected_point_swing": 6.0,
            "is_recommended": True,
        },
        {
            "card": "S9",
            "win_rate": 0.0,
            "average_trick_points": 3.0,
            "average_points_won": 0.0,
            "average_points_lost": 3.0,
            "expected_point_swing": -3.0,
            "is_recommended": False,
        },
    ]

    formatted_report = format_card_analysis_report(report)

    assert "Card analysis report" in formatted_report
    assert "Win rate" in formatted_report
    assert "Swing" in formatted_report
    assert "Recommendation" in formatted_report
    assert "<-- best" in formatted_report
    assert "SA" in formatted_report
    assert "S9" in formatted_report


def test_format_card_analysis_report_handles_empty_report() -> None:
    assert format_card_analysis_report([]) == "No legal cards available."


def test_build_card_analysis_report_marks_exactly_one_recommended_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        player_position="forehand",
        trick_leader="me",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    recommended_rows = [row for row in report if row["is_recommended"]]

    assert len(recommended_rows) == 1


def test_build_card_analysis_report_marks_first_row_as_recommended() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        player_position="forehand",
        trick_leader="me",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert report[0]["is_recommended"] is True


def test_build_card_analysis_report_uses_response_policy_map(monkeypatch) -> None:
    def fake_generate_random_opponent_hands(
        state,
        left_hand_size: int,
        right_hand_size: int,
        random_generator=None,
    ) -> tuple[list[str], list[str]]:
        _ = (state, left_hand_size, right_hand_size, random_generator)
        return ["S8", "S10"], ["S9", "SA"]

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    state = GameState(
        game_type="grand",
        player_role="declarer",
        player_position="forehand",
        trick_leader="me",
        hand=["S7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    report = build_card_analysis_report(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        sample_count=1,
        random_seed=1,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={
            "left": "highest_point",
            "right": "highest_point",
        },
    )

    assert report[0]["card"] == "S7"
    assert report[0]["average_trick_points"] == 21.0


def test_build_strategic_summary_handles_empty_report() -> None:
    summary = build_strategic_summary([])

    assert summary == "Strategic summary: No legal cards are available."


def test_build_strategic_summary_handles_single_legal_card() -> None:
    report = [
        {
            "card": "SA",
            "win_rate": 0.75,
            "average_trick_points": 14.0,
            "average_points_won": 10.0,
            "average_points_lost": 4.0,
            "expected_point_swing": 6.0,
            "is_recommended": True,
        }
    ]

    summary = build_strategic_summary(report)

    assert "SA is the only legal card" in summary
    assert "6.00" in summary
    assert "0.750" in summary


def test_build_strategic_summary_describes_clear_best_card() -> None:
    report = [
        {
            "card": "SA",
            "win_rate": 0.75,
            "average_trick_points": 14.0,
            "average_points_won": 10.0,
            "average_points_lost": 4.0,
            "expected_point_swing": 6.0,
            "is_recommended": True,
        },
        {
            "card": "S9",
            "win_rate": 0.10,
            "average_trick_points": 3.0,
            "average_points_won": 1.0,
            "average_points_lost": 4.0,
            "expected_point_swing": -3.0,
            "is_recommended": False,
        },
    ]

    summary = build_strategic_summary(report)

    assert "SA is recommended" in summary
    assert "ahead of S9" in summary
    assert "9.00 expected points" in summary


def test_build_strategic_summary_describes_close_position() -> None:
    report = [
        {
            "card": "SA",
            "win_rate": 0.55,
            "average_trick_points": 12.0,
            "average_points_won": 7.0,
            "average_points_lost": 3.0,
            "expected_point_swing": 4.0,
            "is_recommended": True,
        },
        {
            "card": "S10",
            "win_rate": 0.50,
            "average_trick_points": 12.0,
            "average_points_won": 6.5,
            "average_points_lost": 3.0,
            "expected_point_swing": 3.5,
            "is_recommended": False,
        },
    ]

    summary = build_strategic_summary(report)

    assert "advantage over S10 is modest" in summary
    assert "position may be close" in summary


def test_build_strategic_summary_describes_least_damaging_option() -> None:
    report = [
        {
            "card": "S9",
            "win_rate": 0.0,
            "average_trick_points": 4.0,
            "average_points_won": 0.0,
            "average_points_lost": 4.0,
            "expected_point_swing": -4.0,
            "is_recommended": True,
        },
        {
            "card": "H10",
            "win_rate": 0.0,
            "average_trick_points": 12.0,
            "average_points_won": 0.0,
            "average_points_lost": 12.0,
            "expected_point_swing": -12.0,
            "is_recommended": False,
        },
    ]

    summary = build_strategic_summary(report)

    assert "least damaging option" in summary
    assert "-4.00" in summary
