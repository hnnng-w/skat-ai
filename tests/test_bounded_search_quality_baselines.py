from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations

import pytest

from skatmind.bounded_search_information import (
    SearchCompletedTrick,
    SearchInformationView,
    SearchPublicPlay,
    build_live_search_information_view,
)
from skatmind.bounded_search_result import RequestedSearchBudget
from skatmind.compatible_world_minimax import solve_compatible_world_minimax
from skatmind.deck import get_full_deck
from skatmind.exact_search_state import (
    ExactSearchState,
    apply_exact_search_card,
    build_exact_search_state,
    get_exact_search_legal_cards,
)
from skatmind.exact_terminal_utility import build_exact_terminal_utility
from skatmind.game_declaration import GameDeclaration
from skatmind.game_state import GameState
from skatmind.hidden_card_inference import (
    EFFECTIVE_CATEGORY_ORDER,
    get_public_effective_category,
)
from skatmind.recommender import recommend_card_by_expected_value
from skatmind.rules import get_effective_suit, get_trick_points, get_trick_winner
from skatmind.terminal_utility import TerminalUtility, compare_terminal_utilities


@dataclass(frozen=True)
class QualityFixture:
    game_type: str
    local_hand: tuple[str, ...]
    hidden_cards: tuple[str, ...]
    declarer_points: int
    immediate_seed: int
    tactical_reason: str
    current_trick: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class AggregateRow:
    card: str
    success_count: int
    success_rate: float
    mean_score: float
    mean_margin: float | None


def _declaration(game_type: str) -> GameDeclaration:
    return GameDeclaration(
        game_type,
        matadors=None if game_type == "null" else 1,
        bid_value=23 if game_type == "null" else 18,
    )


def _completed_cards(fixture: QualityFixture) -> tuple[str, ...]:
    unresolved = {
        *fixture.local_hand,
        *fixture.hidden_cards,
        *(card for _, card in fixture.current_trick),
    }
    return tuple(card for card in get_full_deck() if card not in unresolved)


def _completed_tricks(fixture: QualityFixture) -> tuple[SearchCompletedTrick, ...]:
    cards = _completed_cards(fixture)
    cards_by_category = {
        category: [
            card
            for card in cards
            if get_public_effective_category(card, fixture.game_type) == category
        ]
        for category in EFFECTIVE_CATEGORY_ORDER
    }
    card_groups = []
    for category_cards in cards_by_category.values():
        assert len(category_cards) % 3 == 0
        card_groups.extend(
            tuple(category_cards[index : index + 3])
            for index in range(0, len(category_cards), 3)
        )
    card_groups = tuple(card_groups)
    point_values = tuple(get_trick_points(group) for group in card_groups)
    required_final_winner = fixture.current_trick[0][0] if fixture.current_trick else "me"
    defender_winner = required_final_winner if required_final_winner != "me" else "left"
    winner_mask = next(
        mask
        for mask in range(1 << len(card_groups))
        if sum(
            points for index, points in enumerate(point_values) if mask & (1 << index)
        )
        == fixture.declarer_points
        and (
            ("me" if mask & (1 << (len(card_groups) - 1)) else defender_winner)
            == required_final_winner
        )
    )
    players = ("me", "left", "right")
    leader = "left"
    tricks = []
    for index, group in enumerate(card_groups):
        winner_player = "me" if winner_mask & (1 << index) else defender_winner
        leader_index = players.index(leader)
        play_order = players[leader_index:] + players[:leader_index]
        ordered_cards = next(
            ordered
            for ordered in permutations(group)
            if play_order[get_trick_winner(list(ordered), fixture.game_type)]
            == winner_player
            and (
                play_order[0] == "me"
                or get_effective_suit(
                    ordered[play_order.index("me")], fixture.game_type
                )
                == get_effective_suit(ordered[0], fixture.game_type)
                or not any(
                    get_effective_suit(card, fixture.game_type)
                    == get_effective_suit(ordered[0], fixture.game_type)
                    for card in fixture.local_hand
                )
            )
        )
        tricks.append(
            SearchCompletedTrick(
                plays=tuple(
                    SearchPublicPlay(player, card)
                    for player, card in zip(play_order, ordered_cards, strict=True)
                ),
                winner_player=winner_player,
                winner_side="declarer" if winner_player == "me" else "defenders",
                trick_points=point_values[index],
            )
        )
        leader = winner_player
    assert leader == required_final_winner
    return tuple(tricks)


def _information_view(fixture: QualityFixture) -> SearchInformationView:
    completed_cards = _completed_cards(fixture)
    completed_points = get_trick_points(completed_cards)
    remaining_tricks = len(fixture.local_hand)
    completed_tricks = _completed_tricks(fixture)
    current_trick = [card for _, card in fixture.current_trick]
    state = GameState(
        game_type=fixture.game_type,
        player_role="declarer",
        declarer_player="me",
        hand=list(fixture.local_hand),
        current_trick=current_trick,
        played_cards=[],
        completed_tricks=[
            {
                "cards": [play.card for play in trick.plays],
                "players": [play.player for play in trick.plays],
                "winner_player": trick.winner_player,
                "winner_role": trick.winner_side,
            }
            for trick in completed_tricks
        ],
        declarer_points=0,
        defender_points=0,
        trick_leader=fixture.current_trick[0][0] if fixture.current_trick else "me",
        next_player="me",
    )
    view = build_live_search_information_view(
        state=state,
        declaration=_declaration(fixture.game_type),
        left_hand_size=remaining_tricks
        - int("left" in {actor for actor, _ in fixture.current_trick}),
        right_hand_size=remaining_tricks
        - int("right" in {actor for actor, _ in fixture.current_trick}),
    )
    assert view.declarer_points == fixture.declarer_points
    assert view.defender_points == completed_points - fixture.declarer_points
    assert all(
        not constraint.forbidden_effective_categories
        for constraint in view.hidden_card_constraints
    )
    return view


def _immediate_state(fixture: QualityFixture) -> GameState:
    completed_cards = list(_completed_cards(fixture))
    return GameState(
        game_type=fixture.game_type,
        player_role="declarer",
        declarer_player="me",
        hand=list(fixture.local_hand),
        current_trick=[card for _, card in fixture.current_trick],
        played_cards=completed_cards,
        declarer_points=fixture.declarer_points,
        defender_points=get_trick_points(completed_cards) - fixture.declarer_points,
        trick_leader=fixture.current_trick[0][0] if fixture.current_trick else "me",
        next_player="me",
    )


def _budget(world_count: int) -> RequestedSearchBudget:
    max_remaining_tricks = 3
    return RequestedSearchBudget(
        max_remaining_tricks=max_remaining_tricks,
        max_depth_plies=3 * max_remaining_tricks,
        max_nodes=1_000_000,
        max_selected_worlds=world_count,
        max_sampled_worlds=world_count,
        minimum_comparable_worlds=1,
        wall_clock_timeout_ms=None,
    )


def _independent_exact_worlds(fixture: QualityFixture) -> tuple[ExactSearchState, ...]:
    completed_points = get_trick_points(_completed_cards(fixture))
    remaining_tricks = len(fixture.local_hand)
    completed_tricks = _completed_tricks(fixture)
    completed_trick_count = len(completed_tricks)
    declarer_tricks = sum(
        trick.winner_side == "declarer" for trick in completed_tricks
    )
    current_players = {player for player, _ in fixture.current_trick}
    left_size = remaining_tricks - int("left" in current_players)
    right_size = remaining_tricks - int("right" in current_players)
    constraints = {
        constraint.player: set(constraint.forbidden_effective_categories)
        for constraint in _information_view(fixture).hidden_card_constraints
    }
    worlds = []
    for left_hand in combinations(fixture.hidden_cards, left_size):
        if any(
            get_public_effective_category(card, fixture.game_type)
            in constraints["left"]
            for card in left_hand
        ):
            continue
        after_left = tuple(card for card in fixture.hidden_cards if card not in left_hand)
        for right_hand in combinations(after_left, right_size):
            if any(
                get_public_effective_category(card, fixture.game_type)
                in constraints["right"]
                for card in right_hand
            ):
                continue
            skat = tuple(card for card in after_left if card not in right_hand)
            worlds.append(
                build_exact_search_state(
                    declaration=_declaration(fixture.game_type),
                    declarer_player="me",
                    remaining_hands={
                        "me": fixture.local_hand,
                        "left": left_hand,
                        "right": right_hand,
                    },
                    current_trick=fixture.current_trick,
                    next_player="me",
                    declarer_trick_points=fixture.declarer_points,
                    defender_trick_points=completed_points - fixture.declarer_points,
                    declarer_completed_tricks=declarer_tricks,
                    defender_completed_tricks=completed_trick_count - declarer_tricks,
                    out_of_play_cards=skat,
                )
            )
    assert worlds
    assert len(set(worlds)) == len(worlds)
    return tuple(worlds)


def _oracle_value(state: ExactSearchState) -> TerminalUtility:
    if state.is_terminal:
        return build_exact_terminal_utility(state=state, local_side="declarer")

    maximizing = state.next_player == state.declarer_player
    best = None
    for card in get_exact_search_legal_cards(state):
        utility = _oracle_value(apply_exact_search_card(state, card).next_state)
        if best is None:
            best = utility
            continue
        comparison = compare_terminal_utilities(utility, best)
        if (maximizing and comparison > 0) or (not maximizing and comparison < 0):
            best = utility
    assert best is not None
    return best


def _independent_aggregate(fixture: QualityFixture) -> tuple[AggregateRow, ...]:
    worlds = _independent_exact_worlds(fixture)
    cards = get_exact_search_legal_cards(worlds[0])
    totals = {
        card: {"success": 0, "score": 0, "margin": 0}
        for card in cards
    }
    for world in worlds:
        assert get_exact_search_legal_cards(world) == cards
        for card in cards:
            utility = _oracle_value(apply_exact_search_card(world, card).next_state)
            totals[card]["success"] += int(utility.local_contract_success)
            totals[card]["score"] += utility.local_side_game_score
            if utility.local_side_card_point_margin is not None:
                totals[card]["margin"] += utility.local_side_card_point_margin

    card_order = {card: index for index, card in enumerate(get_full_deck())}
    rows = tuple(
        AggregateRow(
            card=card,
            success_count=values["success"],
            success_rate=values["success"] / len(worlds),
            mean_score=values["score"] / len(worlds),
            mean_margin=(
                None
                if fixture.game_type == "null"
                else values["margin"] / len(worlds)
            ),
        )
        for card, values in totals.items()
    )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                -row.success_rate,
                -row.mean_score,
                -(row.mean_margin or 0.0),
                card_order[row.card],
            ),
        )
    )


STRICT_IMPROVEMENT_FIXTURES = (
    # Immediate cashes DJ, but ducking with D8 preserves the trump winner for the
    # final trick and more often reaches the Suit contract's card-point threshold.
    QualityFixture(
        game_type="clubs",
        local_hand=("DJ", "D8"),
        hidden_cards=("D10", "HK", "CK", "DA", "D7", "SQ"),
        declarer_points=38,
        immediate_seed=21,
        tactical_reason="duck-to-preserve-final-trump-control",
    ),
    # Immediate preserves the ten by leading H7, but Search identifies H10 as
    # the only lead with any compatible-world path to a Grand success.
    QualityFixture(
        game_type="grand",
        local_hand=("H10", "H7"),
        hidden_cards=("HJ", "C10", "HA", "D8", "S10", "H9"),
        declarer_points=24,
        immediate_seed=23,
        tactical_reason="cash-ten-before-opponents-gain-control",
    ),
    # Immediate sheds H7 on the current Null trick. Search instead sheds CK,
    # retaining the low heart that cannot win against the compatible hidden ace.
    QualityFixture(
        game_type="null",
        local_hand=("H7", "CK"),
        hidden_cards=("HA", "C10", "SA", "S10"),
        declarer_points=0,
        immediate_seed=8,
        tactical_reason="discard-club-king-to-retain-low-heart",
        current_trick=(("left", "D10"), ("right", "DQ")),
    ),
)


CONVERGENCE_FIXTURES = (
    QualityFixture(
        game_type="clubs",
        local_hand=("C8", "C7", "HQ"),
        hidden_cards=("D7", "S8", "DQ", "DK", "D8", "SK", "S10", "S7"),
        declarer_points=45,
        immediate_seed=0,
        tactical_reason="suit-three-trick-convergence",
    ),
    QualityFixture(
        game_type="grand",
        local_hand=("HQ", "HA", "CQ"),
        hidden_cards=("D7", "H10", "DJ", "SQ", "D8", "D10", "D9", "HK"),
        declarer_points=49,
        immediate_seed=0,
        tactical_reason="grand-three-trick-convergence",
    ),
    QualityFixture(
        game_type="null",
        local_hand=("HK", "C7", "H7"),
        hidden_cards=("D7", "HA", "S9", "H8", "C10", "SQ", "H10"),
        declarer_points=0,
        immediate_seed=0,
        tactical_reason="null-three-trick-convergence",
        current_trick=(("right", "DQ"),),
    ),
)

CONVERGENCE_SAMPLE_COUNTS = (32, 64, 128)
CONVERGENCE_SEEDS = (11, 29, 47, 71, 101)


@pytest.mark.parametrize(
    "fixture",
    STRICT_IMPROVEMENT_FIXTURES,
    ids=lambda fixture: f"{fixture.game_type}-{fixture.tactical_reason}",
)
def test_search_strictly_improves_on_immediate_with_independent_reference(
    fixture: QualityFixture,
) -> None:
    expected = _independent_aggregate(fixture)
    exact_world_count = len(_independent_exact_worlds(fixture))
    result = solve_compatible_world_minimax(
        information_view=_information_view(fixture),
        requested_budget=_budget(exact_world_count),
        random_seed=115,
    )
    current_players = {player for player, _ in fixture.current_trick}
    remaining_tricks = len(fixture.local_hand)
    immediate_card, _, _ = recommend_card_by_expected_value(
        state=_immediate_state(fixture),
        left_hand_size=remaining_tricks - int("left" in current_players),
        right_hand_size=remaining_tricks - int("right" in current_players),
        sample_count=256,
        random_seed=fixture.immediate_seed,
    )

    assert result.status == "complete"
    assert result.world_coverage == "all_compatible_worlds"
    assert result.compatible_world_count == exact_world_count
    assert result.recommended_card == expected[0].card
    assert result.recommended_card != immediate_card

    actual_by_card = {candidate.card: candidate for candidate in result.candidate_results}
    for row in expected:
        actual = actual_by_card[row.card]
        assert actual.local_contract_success_count == row.success_count
        assert actual.local_contract_success_rate == row.success_rate
        assert actual.mean_local_side_game_score == row.mean_score
        assert actual.mean_local_side_card_point_margin == row.mean_margin

    expected_by_card = {row.card: row for row in expected}
    assert expected_by_card[result.recommended_card].success_rate > expected_by_card[
        immediate_card
    ].success_rate


def test_iid_sampled_search_converges_toward_independent_exhaustive_aggregates() -> None:
    exact_by_fixture = {}
    exact_world_counts = {}
    for fixture in CONVERGENCE_FIXTURES:
        expected = _independent_aggregate(fixture)
        exact_world_count = len(_independent_exact_worlds(fixture))
        assert exact_world_count > max(CONVERGENCE_SAMPLE_COUNTS)

        exact_result = solve_compatible_world_minimax(
            information_view=_information_view(fixture),
            requested_budget=_budget(exact_world_count),
            random_seed=115,
        )
        assert exact_result.status == "complete"
        assert exact_result.world_coverage == "all_compatible_worlds"
        assert exact_result.recommended_card == expected[0].card
        for actual, row in zip(exact_result.candidate_results, expected, strict=True):
            assert actual.card == row.card
            assert actual.local_contract_success_count == row.success_count
            assert actual.local_contract_success_rate == row.success_rate
            assert actual.mean_local_side_game_score == row.mean_score
            assert actual.mean_local_side_card_point_margin == row.mean_margin
        exact_by_fixture[fixture] = expected
        exact_world_counts[fixture] = exact_world_count

    errors_by_sample_count = {count: [] for count in CONVERGENCE_SAMPLE_COUNTS}
    top1_by_sample_count = {
        count: {"agreements": 0, "comparisons": 0}
        for count in CONVERGENCE_SAMPLE_COUNTS
    }
    duplicate_draw_observed = {count: False for count in CONVERGENCE_SAMPLE_COUNTS}

    for sample_count in CONVERGENCE_SAMPLE_COUNTS:
        for fixture, expected in exact_by_fixture.items():
            expected_by_card = {row.card: row for row in expected}
            exact_success_gap = expected[0].success_rate - expected[1].success_rate
            for seed in CONVERGENCE_SEEDS:
                sampled = solve_compatible_world_minimax(
                    information_view=_information_view(fixture),
                    requested_budget=_budget(sample_count),
                    random_seed=seed,
                )
                consumed = sampled.consumed_budget
                assert sampled.status == "complete"
                assert sampled.world_coverage == "sampled_compatible_worlds"
                assert sampled.compatible_world_count == exact_world_counts[fixture]
                assert consumed.selected_world_count == sample_count
                assert consumed.sampled_world_count == sample_count
                assert consumed.completed_world_count == sample_count
                assert consumed.unique_sampled_world_count <= sample_count
                duplicate_draw_observed[sample_count] |= (
                    consumed.unique_sampled_world_count < sample_count
                )

                for candidate in sampled.candidate_results:
                    assert candidate.completed_world_count == sample_count
                    errors_by_sample_count[sample_count].append(
                        abs(
                            candidate.local_contract_success_rate
                            - expected_by_card[candidate.card].success_rate
                        )
                    )

                if exact_success_gap >= 0.10:
                    counts = top1_by_sample_count[sample_count]
                    counts["comparisons"] += 1
                    counts["agreements"] += int(
                        sampled.recommended_card == expected[0].card
                    )

    mean_absolute_errors = {
        count: sum(errors) / len(errors)
        for count, errors in errors_by_sample_count.items()
    }
    assert mean_absolute_errors[128] <= 0.05
    for sample_count, counts in top1_by_sample_count.items():
        assert counts["comparisons"] > 0
        assert counts["agreements"] / counts["comparisons"] >= 0.90
        assert duplicate_draw_observed[sample_count], (
            f"IID draws at {sample_count=} must retain at least one duplicate."
        )
