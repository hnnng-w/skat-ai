from skat_ai.game_state import GameState
from skat_ai.simulation_context import (
    SimulationContext,
    add_simulated_opponent_card,
    add_simulated_opponent_cards,
    add_simulation_event,
    apply_context_to_state_for_sampling,
    build_context_summary,
    get_context_cards_safe_to_add_to_played_cards,
    get_duplicate_simulated_opponent_cards,
    get_unique_simulated_opponent_cards,
    validate_no_duplicate_simulated_opponent_cards,
)
from skat_ai.strategic_metadata import StrategicMetadata


def test_simulation_context_defaults_to_empty_lists() -> None:
    context = SimulationContext()

    assert context.simulated_opponent_cards == []
    assert context.events == []


def test_add_simulated_opponent_card_returns_updated_context() -> None:
    context = SimulationContext()

    updated_context = add_simulated_opponent_card(
        context=context,
        card="S7",
    )

    assert updated_context.simulated_opponent_cards == ["S7"]


def test_add_simulated_opponent_card_does_not_mutate_original_context() -> None:
    context = SimulationContext()

    updated_context = add_simulated_opponent_card(
        context=context,
        card="S7",
    )

    assert context.simulated_opponent_cards == []
    assert updated_context.simulated_opponent_cards == ["S7"]


def test_add_simulated_opponent_cards_adds_multiple_cards() -> None:
    context = SimulationContext()

    updated_context = add_simulated_opponent_cards(
        context=context,
        cards=["S7", "S8"],
    )

    assert updated_context.simulated_opponent_cards == ["S7", "S8"]


def test_add_simulation_event_returns_updated_context() -> None:
    context = SimulationContext()
    event = {
        "type": "test_event",
        "card": "S7",
    }

    updated_context = add_simulation_event(
        context=context,
        event=event,
    )

    assert updated_context.events == [
        {
            "type": "test_event",
            "card": "S7",
        }
    ]


def test_add_simulation_event_does_not_mutate_original_context() -> None:
    context = SimulationContext()
    event = {
        "type": "test_event",
        "card": "S7",
    }

    updated_context = add_simulation_event(
        context=context,
        event=event,
    )

    assert context.events == []
    assert updated_context.events == [
        {
            "type": "test_event",
            "card": "S7",
        }
    ]


def test_get_unique_simulated_opponent_cards_preserves_order() -> None:
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8", "S7", "H10"],
    )

    unique_cards = get_unique_simulated_opponent_cards(context)

    assert unique_cards == ["S7", "S8", "H10"]


def test_get_duplicate_simulated_opponent_cards() -> None:
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8", "S7", "H10", "S8"],
    )

    duplicates = get_duplicate_simulated_opponent_cards(context)

    assert duplicates == ["S7", "S8"]


def test_build_context_summary() -> None:
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8", "S7"],
        events=[
            {"type": "first"},
            {"type": "second"},
        ],
    )

    summary = build_context_summary(context)

    assert summary == {
        "simulated_opponent_card_count": 3,
        "unique_simulated_opponent_card_count": 2,
        "duplicate_simulated_opponent_cards": ["S7"],
        "event_count": 2,
        "strategic_metadata": {
            "analysis_mode": "live_decision",
            "skat_visibility": "unknown",
            "game_end_reason": "not_ended",
        },
    }


def test_apply_context_to_state_for_sampling_adds_simulated_cards_to_played_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        played_cards=[],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8"],
    )

    updated_state = apply_context_to_state_for_sampling(
        state=state,
        context=context,
    )

    assert updated_state.played_cards == ["S7", "S8"]


def test_apply_context_to_state_for_sampling_does_not_duplicate_played_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        played_cards=["S7"],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8"],
    )

    updated_state = apply_context_to_state_for_sampling(
        state=state,
        context=context,
    )

    assert updated_state.played_cards == ["S7", "S8"]


def test_apply_context_to_state_for_sampling_does_not_add_cards_from_hand() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S7"],
        current_trick=[],
        played_cards=[],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8"],
    )

    updated_state = apply_context_to_state_for_sampling(
        state=state,
        context=context,
    )

    assert updated_state.played_cards == ["S8"]


def test_apply_context_to_state_for_sampling_does_not_add_cards_from_current_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        played_cards=[],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8"],
    )

    updated_state = apply_context_to_state_for_sampling(
        state=state,
        context=context,
    )

    assert updated_state.played_cards == ["S8"]


def test_apply_context_to_state_for_sampling_does_not_mutate_original_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        played_cards=[],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7"],
    )

    updated_state = apply_context_to_state_for_sampling(
        state=state,
        context=context,
    )

    assert state.played_cards == []
    assert updated_state.played_cards == ["S7"]


def test_apply_context_to_state_for_sampling_preserves_declarer_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="right",
        hand=["SA"],
        current_trick=[],
        played_cards=[],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7"],
    )

    updated_state = apply_context_to_state_for_sampling(
        state=state,
        context=context,
    )

    assert updated_state.declarer_player == "right"

def test_validate_no_duplicate_simulated_opponent_cards_accepts_unique_cards() -> None:
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8", "H10"],
    )

    validate_no_duplicate_simulated_opponent_cards(context)


def test_validate_no_duplicate_simulated_opponent_cards_rejects_duplicates() -> None:
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8", "S7"],
    )

    try:
        validate_no_duplicate_simulated_opponent_cards(context)
    except ValueError as error:
        assert "Duplicate simulated opponent cards detected" in str(error)
        assert "S7" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_get_context_cards_safe_to_add_to_played_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        played_cards=["C7"],
        skat=["D7"],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7", "S8", "C7", "D7", "H10"],
    )

    safe_cards = get_context_cards_safe_to_add_to_played_cards(
        state=state,
        context=context,
    )

    assert safe_cards == ["S8", "H10"]


def test_apply_context_to_state_for_sampling_rejects_duplicate_known_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        played_cards=["SA"],
    )
    context = SimulationContext(
        simulated_opponent_cards=["S7"],
    )

    try:
        apply_context_to_state_for_sampling(
            state=state,
            context=context,
        )
    except ValueError as error:
        assert "Duplicate known cards detected" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_simulation_context_uses_default_strategic_metadata() -> None:
    context = SimulationContext()

    assert context.strategic_metadata.analysis_mode == "live_decision"
    assert context.strategic_metadata.skat_visibility == "unknown"
    assert context.strategic_metadata.game_end_reason == "not_ended"


def test_simulation_context_preserves_strategic_metadata_when_adding_card() -> None:
    metadata = StrategicMetadata(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
        game_end_reason="normal_completion",
    )
    context = SimulationContext(strategic_metadata=metadata)

    updated_context = add_simulated_opponent_card(
        context=context,
        card="S7",
    )

    assert updated_context.strategic_metadata == metadata


def test_simulation_context_preserves_strategic_metadata_when_adding_event() -> None:
    metadata = StrategicMetadata(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
        game_end_reason="normal_completion",
    )
    context = SimulationContext(strategic_metadata=metadata)

    updated_context = add_simulation_event(
        context=context,
        event={"type": "test"},
    )

    assert updated_context.strategic_metadata == metadata


def test_build_context_summary_includes_strategic_metadata() -> None:
    metadata = StrategicMetadata(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
        game_end_reason="normal_completion",
    )
    context = SimulationContext(strategic_metadata=metadata)

    summary = build_context_summary(context)

    assert summary["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "normal_completion",
    }
