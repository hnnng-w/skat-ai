from dataclasses import fields

import pytest
from test_historical_game import build_historical_input
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

from skatmind.errors import SkatMindInvariantError
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_serializable_historical_record,
)
from skatmind.match_historical_materialization import (
    MATCH_HISTORICAL_GAME_MATERIALIZATION_VERSION,
    MATCH_HISTORICAL_MATERIALIZATION_POLICY,
    MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS,
    MATCH_MATERIALIZATION_ARTIFACT_STATUSES,
    MATCH_MATERIALIZED_PLAYED_AT_POLICY,
    MatchHistoricalGameMaterializationV1,
    materialize_match_observed_game_historical_v1,
)
from skatmind.match_training_source_materialization import (
    MATCH_TRAINING_SOURCE_COLLECTION_VERSION,
    MATCH_TRAINING_SOURCE_POLICY,
    materialize_match_training_source_record_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1


def test_versions_reasons_policies_and_fields_are_exact() -> None:
    assert MATCH_HISTORICAL_GAME_MATERIALIZATION_VERSION == 1
    assert MATCH_TRAINING_SOURCE_COLLECTION_VERSION == 1
    assert MATCH_MATERIALIZATION_ARTIFACT_STATUSES == ("available", "unavailable")
    assert MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS == (
        "slot_empty",
        "passed_deal",
        "declaration_unavailable",
        "incomplete_play_trace",
        "original_skat_unavailable",
        "discarded_cards_unavailable",
    )
    assert MATCH_HISTORICAL_MATERIALIZATION_POLICY == (
        "existing_normal_completion_contract_with_complete_initial_deal"
    )
    assert MATCH_MATERIALIZED_PLAYED_AT_POLICY == (
        "retain_match_played_at_without_media_offset_derivation"
    )
    assert MATCH_TRAINING_SOURCE_POLICY == (
        "existing_unpartitioned_record_from_materialized_historical_game"
    )
    assert tuple(field.name for field in fields(MatchHistoricalGameMaterializationV1)) == (
        "match_historical_game_materialization_version",
        "status",
        "match_id",
        "match_position",
        "game_id",
        "unavailable_reason",
        "historical_game",
    )


def test_empty_passed_and_incomplete_evidence_return_exact_reasons() -> None:
    definition = _definition()
    empty = create_match_workspace_v1(definition)
    assert (
        materialize_match_observed_game_historical_v1(
            empty,
            match_position=1,
        ).unavailable_reason
        == "slot_empty"
    )
    passed = mark_match_workspace_passed_deal_v1(
        empty,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    assert (
        materialize_match_observed_game_historical_v1(
            passed,
            match_position=1,
        ).unavailable_reason
        == "passed_deal"
    )
    no_declaration = _set_game(
        empty,
        _observed_game(definition, match_position=1),
    )
    assert (
        materialize_match_observed_game_historical_v1(
            no_declaration,
            match_position=1,
        ).unavailable_reason
        == "declaration_unavailable"
    )


def test_unknown_bid_is_declaration_unavailable_for_strict_historical() -> None:
    definition = _definition()
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
        plays=observed_plays_from_historical(data),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=3,
    )
    assert result.status == "unavailable"
    assert result.unavailable_reason == "declaration_unavailable"


@pytest.mark.parametrize(
    ("include_skat", "include_discards", "reason"),
    (
        (False, True, "original_skat_unavailable"),
        (True, False, "discarded_cards_unavailable"),
    ),
)
def test_complete_trace_missing_deal_evidence_is_normally_unavailable(
    include_skat: bool,
    include_discards: bool,
    reason: str,
) -> None:
    definition = _definition()
    game = _complete_observed_game(definition, match_position=3)
    rebuilt = _observed_game(
        definition,
        match_position=3,
        game_id=game.game_id,
        perspective_initial_hand=game.perspective_initial_hand,
        declarer_player_id=game.declarer_player_id,
        declaration=game.declaration,
        original_skat=game.original_skat if include_skat else None,
        discarded_cards=game.discarded_cards if include_discards else None,
        plays=game.plays,
    )
    workspace = _set_game(create_match_workspace_v1(definition), rebuilt)
    assert (
        materialize_match_observed_game_historical_v1(
            workspace,
            match_position=3,
        ).unavailable_reason
        == reason
    )


def test_historical_reason_precedence_prefers_trace_before_missing_deal() -> None:
    definition = _definition()
    source = _complete_observed_game(definition, match_position=3)
    game = _observed_game(
        definition,
        match_position=3,
        game_id=source.game_id,
        perspective_initial_hand=source.perspective_initial_hand,
        declarer_player_id=source.declarer_player_id,
        declaration=source.declaration,
        original_skat=None,
        discarded_cards=None,
        plays=source.plays[:3],
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=3,
    )
    assert result.unavailable_reason == "incomplete_play_trace"


@pytest.mark.parametrize(
    ("game_type", "hand_game", "bid_value"),
    (
        ("clubs", False, 18),
        ("grand", True, 24),
        ("null", False, 23),
        ("null", True, 35),
    ),
)
def test_strict_historical_materialization_reuses_canonical_contract(
    game_type: str,
    hand_game: bool,
    bid_value: int,
) -> None:
    definition = _definition(played_at="2026-08-09T18:00:00Z")
    data = build_historical_input(
        game_type=game_type,
        hand_game=hand_game,
        bid_value=bid_value,
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"strict-{game_type}-{hand_game}",
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=3,
    )
    record = result.historical_game
    assert result.status == "available"
    assert result.unavailable_reason is None
    assert record is not None
    assert record.game_id == game.game_id
    assert record.played_at == definition.played_at
    assert len(record.players) == 3
    assert all(len(player.initial_hand) == 10 for player in record.players)
    assert record.skat == game.original_skat
    assert record.discarded_cards == game.discarded_cards
    assert record.game_end_reason == "normal_completion"
    assert record.game_end is None
    assert record.game_events == ()
    assert len(record.tricks) == 10
    serialized = build_serializable_historical_record(record)
    assert build_historical_game_record(serialized) == record
    summary = build_historical_game_summary(record)
    assert summary["status"] == "complete"
    assert summary["final_settlement_summary"]["is_complete"] is True
    assert "commentaries" not in serialized
    assert "response_links" not in serialized


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "bid_value"),
    (
        (False, False, 23),
        (True, False, 35),
        (False, True, 46),
        (True, True, 59),
    ),
)
def test_all_four_null_variants_materialize(
    hand_game: bool,
    ouvert: bool,
    bid_value: int,
) -> None:
    definition = _definition()
    data = build_historical_input(
        game_type="null",
        hand_game=hand_game,
        bid_value=bid_value,
    )
    declaration = type(declaration_from_historical(data))(
        game_type="null",
        hand_game=hand_game,
        ouvert=ouvert,
        bid_value=bid_value,
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"null-{hand_game}-{ouvert}",
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration,
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    record = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=3,
    ).historical_game
    assert record is not None
    assert record.declaration.game_type == "null"
    assert record.declaration.hand_game is hand_game
    assert record.declaration.ouvert is ouvert
    assert record.declaration.bid_value == bid_value
    assert record.declaration.matadors is None


def test_non_hand_declarer_original_hand_is_reconstructed_exactly() -> None:
    definition = _definition()
    data = build_historical_input(game_type="grand", hand_game=False)
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
    record = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=3,
    ).historical_game
    assert record is not None
    hands = {player.player_id: player.initial_hand for player in record.players}
    assert hands == {
        player["player_id"]: tuple(player["initial_hand"]) for player in data["players"]
    }


def test_conflicting_retained_matadors_are_not_silently_replaced() -> None:
    definition = _definition()
    data = build_historical_input(game_type="grand")
    declaration = type(declaration_from_historical(data))(
        game_type="grand",
        matadors=2,
        bid_value=18,
    )
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration,
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    with pytest.raises(SkatMindInvariantError, match="Complete exact Match evidence"):
        materialize_match_observed_game_historical_v1(
            workspace,
            match_position=3,
        )


def test_training_source_record_uses_match_source_and_has_no_partition() -> None:
    definition = _definition()
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition, match_position=3),
    )
    historical = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=3,
    )
    result = materialize_match_training_source_record_v1(
        historical,
        source_title=definition.source.source_title,
    )
    assert result.status == "available"
    assert result.record_id == f"{definition.match_id}-record-03"
    assert result.record is not None
    assert result.record.provenance.source_type == "manual_entry"
    assert result.record.provenance.source_name == definition.source.source_title
    assert result.record.provenance.source_record_id == historical.game_id
    assert result.record.provenance.collected_at is None
    assert result.record.provenance.notes is None
    assert not hasattr(result.record, "partition")
    assert not hasattr(result.record, "samples")
