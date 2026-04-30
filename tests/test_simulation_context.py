from skat_ai.simulation_context import (
    SimulationContext,
    add_simulated_opponent_card,
    add_simulated_opponent_cards,
    add_simulation_event,
    build_context_summary,
    get_duplicate_simulated_opponent_cards,
    get_unique_simulated_opponent_cards,
)


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
    }