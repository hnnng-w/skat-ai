from dataclasses import FrozenInstanceError, fields

import pytest
from test_historical_game import build_historical_input, rebuild_historical_suffix
from test_match_player_statistics_context import (
    _actionable_snapshot,
    _capture_with_snapshots,
)
from test_match_workspace_contracts import (
    _complete_observed_game,
    _definition,
    _observed_game,
    _set_game,
)
from test_observed_game_contracts import (
    declaration_from_historical,
    observed_plays_from_historical,
)

from skat_ai.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot,
)
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.match_decision_review_preparation import (
    MATCH_DECISION_REVIEW_INFORMATION_POLICY,
    MATCH_DECISION_REVIEW_PREPARATION_STATUSES,
    MATCH_DECISION_REVIEW_PREPARATION_VERSION,
    MATCH_DECISION_REVIEW_SKIP_REASONS,
    MATCH_PROFILE_BINDING_POLICY,
    MatchDecisionOpponentProfileBindingV1,
    MatchDecisionReviewPreparationV1,
    MatchSkippedDecisionV1,
    build_match_decision_review_preparation_v1,
)
from skat_ai.match_historical_materialization import (
    materialize_match_observed_game_historical_v1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_operations import set_match_workspace_observed_game_v1
from skat_ai.rules import get_legal_cards


def _workspace_with_partial_game(*, perspective_player_id="player-a"):
    definition = _capture_with_snapshots()
    assert definition.perspective_player_id == perspective_player_id
    data = build_historical_input(game_type="grand")
    perspective_hand = next(
        player["initial_hand"]
        for player in data["players"]
        if player["player_id"] == perspective_player_id
    )
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=perspective_hand,
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data, count=6),
    )
    return _set_game(create_match_workspace_v1(definition), game), data


def test_versions_statuses_reasons_policies_and_fields_are_exact() -> None:
    assert MATCH_DECISION_REVIEW_PREPARATION_VERSION == 1
    assert MATCH_DECISION_REVIEW_PREPARATION_STATUSES == (
        "available",
        "partial",
        "unavailable",
    )
    assert MATCH_DECISION_REVIEW_SKIP_REASONS == (
        "acting_hand_unavailable",
        "required_public_hand_unavailable",
    )
    assert MATCH_DECISION_REVIEW_INFORMATION_POLICY == (
        "reconstruct_decision_time_own_hand_without_future_opponent_information"
    )
    assert MATCH_PROFILE_BINDING_POLICY == (
        "prepare_eligible_relative_opponents_without_policy_application"
    )
    assert tuple(field.name for field in fields(MatchSkippedDecisionV1)) == (
        "decision_index",
        "acting_player_id",
        "reason",
    )
    assert tuple(field.name for field in fields(MatchDecisionOpponentProfileBindingV1)) == (
        "decision_index",
        "acting_player_id",
        "left_opponent_player_id",
        "right_opponent_player_id",
        "left_temporal_status",
        "right_temporal_status",
        "left_profile_available",
        "right_profile_available",
        "left_actionable_policy_preset",
        "right_actionable_policy_preset",
    )
    assert tuple(field.name for field in fields(MatchDecisionReviewPreparationV1)) == (
        "match_decision_review_preparation_version",
        "status",
        "match_id",
        "game_id",
        "match_position",
        "source_played_at",
        "source_play_count",
        "prepared_decision_count",
        "skipped_decision_count",
        "snapshots",
        "skipped_decisions",
        "profile_bindings",
    )


def test_partial_trace_prepares_only_exact_perspective_decisions() -> None:
    workspace, data = _workspace_with_partial_game()
    result = build_match_decision_review_preparation_v1(
        workspace,
        match_position=3,
    )
    expected_indexes = tuple(
        play.decision_index
        for play in workspace.slots[2].observed_game.plays
        if play.player_id == "player-a"
    )
    assert result.status == "partial"
    assert tuple(snapshot.decision_index for snapshot in result.snapshots) == (expected_indexes)
    assert result.prepared_decision_count == len(expected_indexes)
    assert result.skipped_decision_count == 6 - len(expected_indexes)
    assert {item.reason for item in result.skipped_decisions} == {"acting_hand_unavailable"}
    first = result.snapshots[0]
    assert first.source_played_at == workspace.match_definition.played_at
    assert first.visible_state.own_hand == tuple(data["players"][0]["initial_hand"])
    assert first.visible_state.legal_cards == tuple(
        get_legal_cards(list(first.visible_state.own_hand), [], "grand")
    )
    assert first.visible_state.current_trick == ()
    assert first.visible_state.completed_tricks == ()
    assert first.visible_state.declarer_trick_points == 0
    assert first.visible_state.defender_trick_points == 0
    assert first.actual_card_played in first.visible_state.own_hand
    assert first.actual_card_played not in first.visible_state.current_trick
    assert result.prepared_decision_count + result.skipped_decision_count == 6


def test_partial_hand_declarer_prepares_exact_perspective_decision() -> None:
    definition = _definition(perspective_player_id="player-b")
    data = build_historical_input(
        game_type="grand",
        hand_game=True,
        declarer_player_id="player-b",
    )
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][1]["initial_hand"],
        declarer_player_id="player-b",
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=(),
        plays=observed_plays_from_historical(data, count=2),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    assert result.status == "partial"
    assert tuple(snapshot.decision_index for snapshot in result.snapshots) == (2,)
    assert result.snapshots[0].visible_state.own_hand == tuple(data["players"][1]["initial_hand"])


def test_partial_non_hand_declarer_prepares_exact_transformed_hand() -> None:
    definition = _definition(perspective_player_id="player-a")
    data = build_historical_input(
        game_type="grand",
        declarer_player_id="player-a",
    )
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id="player-a",
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data, count=1),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    expected_hand = tuple(
        card
        for card in (
            *data["players"][0]["initial_hand"],
            *data["skat"],
        )
        if card not in data["discarded_cards"]
    )
    assert result.status == "available"
    assert set(result.snapshots[0].visible_state.own_hand) == set(expected_hand)


@pytest.mark.parametrize("game_type", ("clubs", "grand", "null"))
def test_complete_trace_prepares_all_decisions_equal_to_existing_snapshots(
    game_type: str,
) -> None:
    definition = _capture_with_snapshots()
    data = build_historical_input(game_type=game_type)
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    historical = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=3,
    ).historical_game
    assert historical is not None
    expected = build_historical_decision_snapshots(build_historical_game_summary(historical))
    assert result.status == "available"
    assert result.prepared_decision_count == 30
    assert result.skipped_decision_count == 0
    assert [
        build_serializable_historical_decision_snapshot(snapshot) for snapshot in result.snapshots
    ] == [
        build_serializable_historical_decision_snapshot(snapshot) for snapshot in expected.snapshots
    ]
    with pytest.raises(FrozenInstanceError):
        result.status = "partial"


def test_complete_trace_visible_states_do_not_expose_opponent_cards_or_results() -> None:
    definition = _capture_with_snapshots()
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition, match_position=3),
    )
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    serialized = result.to_dict()
    first = serialized["snapshots"][0]
    assert set(first["relative_player_map"]) == {"me", "left", "right"}
    assert len(first["visible_state"]["opponent_hand_sizes"]) == 2
    assert not {
        "winner",
        "result",
        "settlement",
        "final_settlement_summary",
        "commentaries",
        "response_links",
    }.intersection(first["visible_state"])
    own_cards = set(first["visible_state"]["own_hand"])
    assert all(
        "cards" not in opponent for opponent in first["visible_state"]["opponent_hand_sizes"]
    )
    assert first["actual_card_played"] in own_cards


def test_skat_visibility_is_limited_to_non_hand_declarer() -> None:
    definition = _capture_with_snapshots()
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition, match_position=3),
    )
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    game = workspace.slots[2].observed_game
    assert game is not None
    for snapshot in result.snapshots:
        state = snapshot.visible_state
        if snapshot.acting_player_id == game.declarer_player_id:
            assert state.skat_visibility == "known_to_declarer"
            assert state.known_skat_cards == game.discarded_cards
        else:
            assert state.skat_visibility == "unknown"
            assert state.known_skat_cards == ()


def test_ouvert_requires_and_shrinks_exact_public_declarer_hand() -> None:
    definition = _capture_with_snapshots()
    data = build_historical_input(game_type="null", hand_game=True)
    declaration = declaration_from_historical(data)
    declaration = type(declaration)(
        game_type="null",
        hand_game=True,
        ouvert=True,
        bid_value=59,
    )
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration,
        original_skat=data["skat"],
        discarded_cards=(),
        plays=observed_plays_from_historical(data),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    exposure_sizes = [
        len(snapshot.visible_state.public_exposed_cards[0].cards) for snapshot in result.snapshots
    ]
    assert exposure_sizes[0] == 10
    assert exposure_sizes[-1] == 0
    assert exposure_sizes == sorted(exposure_sizes, reverse=True)


def test_partial_ouvert_skips_known_actor_when_public_hand_is_unavailable() -> None:
    definition = _capture_with_snapshots()
    data = build_historical_input(game_type="null", hand_game=True)
    declaration = type(declaration_from_historical(data))(
        game_type="null",
        hand_game=True,
        ouvert=True,
        bid_value=59,
    )
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration,
        original_skat=data["skat"],
        discarded_cards=(),
        plays=observed_plays_from_historical(data, count=1),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    assert result.status == "unavailable"
    assert result.skipped_decisions[0].reason == "required_public_hand_unavailable"


@pytest.mark.parametrize(
    ("include_skat", "include_discards"),
    ((False, True), (True, False)),
)
def test_partial_non_hand_perspective_declarer_requires_exact_transformation(
    include_skat: bool,
    include_discards: bool,
) -> None:
    definition = _capture_with_snapshots()
    data = build_historical_input(game_type="grand", declarer_player_id="player-a")
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id="player-a",
        declaration=declaration_from_historical(data),
        original_skat=data["skat"] if include_skat else None,
        discarded_cards=data["discarded_cards"] if include_discards else None,
        plays=observed_plays_from_historical(data, count=1),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    assert result.status == "unavailable"
    assert result.skipped_decisions[0].reason == "acting_hand_unavailable"


def test_profile_bindings_are_relative_eligible_and_exclude_actor() -> None:
    definition = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
            _actionable_snapshot("player-c", "snapshot-c"),
        )
    )
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition, match_position=3),
    )
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    assert len(result.profile_bindings) == 30
    for snapshot, binding in zip(result.snapshots, result.profile_bindings, strict=True):
        assert binding.acting_player_id == snapshot.relative_player_map["me"]
        assert binding.left_opponent_player_id == snapshot.relative_player_map["left"]
        assert binding.right_opponent_player_id == snapshot.relative_player_map["right"]
        assert binding.acting_player_id not in {
            binding.left_opponent_player_id,
            binding.right_opponent_player_id,
        }
        assert binding.left_profile_available is True
        assert binding.right_profile_available is True
        assert binding.left_actionable_policy_preset == "aggressive_points"
        assert binding.right_actionable_policy_preset == "aggressive_points"


def test_profile_bindings_retain_ineligible_contexts_without_profiles() -> None:
    definition = _capture_with_snapshots(
        played_at=None,
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
        ),
    )
    source_game = _complete_observed_game(
        _capture_with_snapshots(),
        match_position=3,
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=source_game.game_id,
        perspective_initial_hand=source_game.perspective_initial_hand,
        declarer_player_id=source_game.declarer_player_id,
        declaration=source_game.declaration,
        original_skat=source_game.original_skat,
        discarded_cards=source_game.discarded_cards,
        plays=source_game.plays,
    )
    workspace = set_match_workspace_observed_game_v1(
        create_match_workspace_v1(definition),
        game,
        expected_revision=0,
    ).workspace
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    bindings = result.profile_bindings
    assert any(binding.left_temporal_status == "match_time_unavailable" for binding in bindings)
    assert all(
        not binding.left_profile_available
        for binding in bindings
        if binding.left_temporal_status == "match_time_unavailable"
    )
    assert all(
        binding.left_actionable_policy_preset is None
        for binding in bindings
        if binding.left_temporal_status == "match_time_unavailable"
    )


def test_future_opponent_play_order_does_not_change_earlier_visible_state() -> None:
    definition = _capture_with_snapshots()
    first_data = build_historical_input(game_type="grand")
    second_data = rebuild_historical_suffix(first_data, completed_prefix_tricks=2)
    first_game = _observed_game(
        definition,
        match_position=3,
        game_id="first-suffix",
        perspective_initial_hand=first_data["players"][0]["initial_hand"],
        declarer_player_id=first_data["declarer_player_id"],
        declaration=declaration_from_historical(first_data),
        original_skat=first_data["skat"],
        discarded_cards=first_data["discarded_cards"],
        plays=observed_plays_from_historical(first_data),
    )
    second_game = _observed_game(
        definition,
        match_position=3,
        game_id="second-suffix",
        perspective_initial_hand=second_data["players"][0]["initial_hand"],
        declarer_player_id=second_data["declarer_player_id"],
        declaration=declaration_from_historical(second_data),
        original_skat=second_data["skat"],
        discarded_cards=second_data["discarded_cards"],
        plays=observed_plays_from_historical(second_data),
    )
    first = build_match_decision_review_preparation_v1(
        _set_game(create_match_workspace_v1(definition), first_game),
        match_position=3,
    )
    second = build_match_decision_review_preparation_v1(
        _set_game(create_match_workspace_v1(definition), second_game),
        match_position=3,
    )
    for first_snapshot, second_snapshot in zip(
        first.snapshots[:6], second.snapshots[:6], strict=True
    ):
        assert first_snapshot.visible_state == second_snapshot.visible_state
        assert first_snapshot.actual_card_played == second_snapshot.actual_card_played


def test_empty_observed_trace_is_unavailable_without_skips() -> None:
    definition = _capture_with_snapshots()
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _observed_game(definition, match_position=3),
    )
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    assert result.status == "unavailable"
    assert result.source_play_count == 0
    assert result.snapshots == ()
    assert result.skipped_decisions == ()


def test_unknown_bid_does_not_block_own_hand_decision_preparation() -> None:
    definition = _capture_with_snapshots()
    data = build_historical_input(game_type="grand")
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=type(declaration_from_historical(data))(
            game_type="grand",
            bid_value=None,
        ),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data, count=1),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    assert result.status == "available"
    assert result.snapshots[0].visible_state.declaration.bid_value is None


def test_unknown_discards_do_not_invent_non_hand_declarer_matadors() -> None:
    definition = _capture_with_snapshots()
    source = _complete_observed_game(definition, match_position=3)
    game = _observed_game(
        definition,
        match_position=3,
        game_id=source.game_id,
        perspective_initial_hand=source.perspective_initial_hand,
        declarer_player_id=source.declarer_player_id,
        declaration=source.declaration,
        original_skat=source.original_skat,
        discarded_cards=None,
        plays=source.plays,
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = build_match_decision_review_preparation_v1(workspace, match_position=3)
    declarer_snapshots = tuple(
        snapshot
        for snapshot in result.snapshots
        if snapshot.acting_player_id == source.declarer_player_id
    )
    assert declarer_snapshots
    assert all(
        snapshot.visible_state.declaration.matadors is None for snapshot in declarer_snapshots
    )
