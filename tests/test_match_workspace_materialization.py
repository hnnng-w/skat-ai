import json
import tomllib
from dataclasses import fields
from pathlib import Path

import pytest
from test_match_workspace_contracts import (
    _annotated_observed_game,
    _complete_observed_game,
    _definition,
)

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.api.v1.session as session_api
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.match_training_source_materialization import (
    MatchTrainingSourceCollectionV1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_materialization import (
    MATCH_COMMENTARY_MATERIALIZATION_POLICY,
    MATCH_LIST_MATERIALIZATION_POLICY,
    MATCH_LIST_MATERIALIZATION_UNAVAILABLE_REASONS,
    MATCH_WORKSPACE_MATERIALIZATION_STATUSES,
    MATCH_WORKSPACE_MATERIALIZATION_VERSION,
    MatchWorkspaceMaterializationV1,
    build_match_workspace_materialization_v1,
)
from skat_ai.match_workspace_operations import (
    mark_match_workspace_passed_deal_v1,
    set_match_workspace_observed_game_v1,
)
from skat_ai.match_workspace_persistence import _build_match_workspace_file_bytes_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _all_passed_workspace():
    workspace = create_match_workspace_v1(_definition())
    for position in range(1, 37):
        workspace = mark_match_workspace_passed_deal_v1(
            workspace,
            match_position=position,
            game_timecode=None,
            expected_revision=workspace.revision,
        ).workspace
    return workspace


def _mixed_complete_workspace():
    workspace = create_match_workspace_v1(_definition())
    for position in range(1, 37):
        if position == 3:
            workspace = set_match_workspace_observed_game_v1(
                workspace,
                _complete_observed_game(
                    workspace.match_definition,
                    match_position=3,
                ),
                expected_revision=workspace.revision,
            ).workspace
        else:
            workspace = mark_match_workspace_passed_deal_v1(
                workspace,
                match_position=position,
                game_timecode=None,
                expected_revision=workspace.revision,
            ).workspace
    return workspace


def test_versions_statuses_reasons_policies_and_fields_are_exact() -> None:
    assert MATCH_WORKSPACE_MATERIALIZATION_VERSION == 1
    assert MATCH_WORKSPACE_MATERIALIZATION_STATUSES == (
        "empty",
        "partial",
        "complete",
    )
    assert MATCH_LIST_MATERIALIZATION_UNAVAILABLE_REASONS == (
        "workspace_not_structurally_complete",
        "observed_game_not_historical_materializable",
    )
    assert MATCH_LIST_MATERIALIZATION_POLICY == ("existing_fixed_three_player_36_position_contract")
    assert MATCH_COMMENTARY_MATERIALIZATION_POLICY == (
        "remain_workspace_sidecar_without_analysis_influence"
    )
    assert tuple(field.name for field in fields(MatchWorkspaceMaterializationV1)) == (
        "match_workspace_materialization_version",
        "status",
        "match_id",
        "workspace_revision",
        "match_played_at",
        "player_statistics_preparation",
        "slot_materializations",
        "prepared_decision_count",
        "skipped_decision_count",
        "historical_game_count",
        "training_record_count",
        "passed_deal_count",
        "commentary_count",
        "response_link_count",
        "training_source_collection",
        "historical_list_materialization",
    )


def test_empty_workspace_summary_is_reconciled_and_list_unavailable() -> None:
    result = build_match_workspace_materialization_v1(create_match_workspace_v1(_definition()))
    assert result.status == "empty"
    assert len(result.slot_materializations) == 36
    assert result.prepared_decision_count == 0
    assert result.historical_game_count == 0
    assert result.training_record_count == 0
    assert result.passed_deal_count == 0
    assert result.historical_list_materialization.status == "unavailable"
    assert result.historical_list_materialization.unavailable_reason == (
        "workspace_not_structurally_complete"
    )
    assert result.historical_list_materialization.unavailable_positions == tuple(range(1, 37))


def test_all_passed_workspace_materializes_existing_list_and_unresolved_lot() -> None:
    workspace = _all_passed_workspace()
    result = build_match_workspace_materialization_v1(workspace)
    list_result = result.historical_list_materialization
    assert result.status == "complete"
    assert result.passed_deal_count == 36
    assert result.historical_game_count == 0
    assert result.training_record_count == 0
    assert result.training_source_collection.available_record_count == 0
    assert result.training_source_collection.unavailable_positions == tuple(range(1, 37))
    assert list_result.status == "available"
    assert list_result.historical_list is not None
    assert list_result.historical_list.list_id == f"{result.match_id}-list"
    assert tuple(entry.entry_id for entry in list_result.historical_list.entries) == tuple(
        f"{result.match_id}-entry-{position:02d}" for position in range(1, 37)
    )
    assert all(entry.entry_kind == "passed_deal" for entry in list_result.historical_list.entries)
    assert list_result.aggregation is not None
    assert list_result.aggregation.passed_deal_count == 36
    assert list_result.aggregation.ranking_status == "lot_required"
    assert len(list_result.aggregation.progression) == 36


def test_external_lot_reuses_existing_exact_behavior() -> None:
    workspace = _all_passed_workspace()
    unresolved = build_match_workspace_materialization_v1(workspace)
    tied_ids = unresolved.historical_list_materialization.aggregation.tied_player_ids
    result = build_match_workspace_materialization_v1(
        workspace,
        lot_order=tuple(reversed(tied_ids)),
    )
    aggregation = result.historical_list_materialization.aggregation
    assert aggregation is not None
    assert aggregation.ranking_status == "final"
    assert aggregation.applied_lot_order == tuple(reversed(tied_ids))
    assert aggregation.lot_required_player_ids == ()


def test_mixed_complete_workspace_collects_historical_and_training_in_order() -> None:
    workspace = _mixed_complete_workspace()
    result = build_match_workspace_materialization_v1(workspace)
    assert result.status == "complete"
    assert result.prepared_decision_count == 30
    assert result.skipped_decision_count == 0
    assert result.historical_game_count == 1
    assert result.training_record_count == 1
    assert result.passed_deal_count == 35
    assert tuple(record.record_id for record in result.training_source_collection.records) == (
        f"{result.match_id}-record-03",
    )
    list_result = result.historical_list_materialization
    assert list_result.historical_list is not None
    assert list_result.historical_list.entries[2].entry_kind == "played_game"
    assert list_result.aggregation is not None
    assert list_result.aggregation.played_game_count == 1
    assert list_result.aggregation.passed_deal_count == 35
    assert result.to_dict() == build_match_workspace_materialization_v1(workspace).to_dict()


def test_materialization_does_not_change_workspace_or_persistence_bytes() -> None:
    workspace = _mixed_complete_workspace()
    source_document = build_match_workspace_persistence_document_v1(workspace)
    source_bytes = _build_match_workspace_file_bytes_v1(source_document)
    source_workspace = workspace.to_dict()
    build_match_workspace_materialization_v1(workspace)
    assert workspace.to_dict() == source_workspace
    assert build_match_workspace_persistence_document_v1(workspace) == source_document
    assert _build_match_workspace_file_bytes_v1(source_document) == source_bytes


def test_commentary_and_response_links_remain_counted_workspace_sidecars() -> None:
    workspace = create_match_workspace_v1(_definition())
    workspace = set_match_workspace_observed_game_v1(
        workspace,
        _annotated_observed_game(workspace.match_definition),
        expected_revision=workspace.revision,
    ).workspace
    result = build_match_workspace_materialization_v1(workspace)
    serialized = result.to_dict()
    assert result.commentary_count == 1
    assert result.response_link_count == 1
    assert serialized["slot_materializations"][2]["commentary_count"] == 1
    assert serialized["slot_materializations"][2]["response_link_count"] == 1
    text = json.dumps(serialized)
    assert "Observed opening explanation." not in text
    assert "comment-1" not in text
    assert "response-1" not in text


def test_workspace_prepares_statistics_once(monkeypatch) -> None:
    import skat_ai.match_player_statistics_preparation as preparation_module

    original = preparation_module.build_match_player_statistics_context_v1
    calls = []

    def counted(*args, **kwargs):
        calls.append(kwargs["player_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(
        preparation_module,
        "build_match_player_statistics_context_v1",
        counted,
    )
    build_match_workspace_materialization_v1(_mixed_complete_workspace())
    assert calls == ["player-a", "player-b", "player-c"]


def test_workspace_validates_each_trace_and_derives_list_facts_once(
    monkeypatch,
) -> None:
    import skat_ai.fixed_three_player_historical_list as list_module
    import skat_ai.observed_game_contracts as observed_module

    original_trace = observed_module.validate_observed_game_trace_v1
    original_facts = list_module.build_fixed_three_player_historical_list_entry_facts
    workspace = _mixed_complete_workspace()
    trace_calls = 0
    fact_calls = 0

    def counted_trace(*args, **kwargs):
        nonlocal trace_calls
        trace_calls += 1
        return original_trace(*args, **kwargs)

    def counted_facts(historical_list):
        nonlocal fact_calls
        fact_calls += 1
        return original_facts(historical_list)

    monkeypatch.setattr(observed_module, "validate_observed_game_trace_v1", counted_trace)
    monkeypatch.setattr(
        list_module,
        "build_fixed_three_player_historical_list_entry_facts",
        counted_facts,
    )
    result = build_match_workspace_materialization_v1(workspace)
    assert result.status == "complete"
    assert trace_calls == 1
    assert fact_calls == 1


def test_materialization_executes_no_workflow_policy_io_or_background_work(
    monkeypatch,
) -> None:
    import socket
    import threading

    import skat_ai.application.execution as application_execution
    import skat_ai.effective_opponent_policy as effective_policy
    import skat_ai.match_workspace_persistence as persistence
    import skat_ai.training_dataset as training_dataset

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Forbidden execution boundary was crossed.")

    monkeypatch.setattr(
        application_execution,
        "execute_application_invocation",
        forbidden,
    )
    monkeypatch.setattr(
        effective_policy,
        "build_effective_opponent_policy_settings",
        forbidden,
    )
    monkeypatch.setattr(training_dataset, "build_training_dataset_summary", forbidden)
    monkeypatch.setattr(persistence, "load_match_workspace_file_v1", forbidden)
    monkeypatch.setattr(persistence, "save_match_workspace_file_v1", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(threading.Thread, "start", forbidden)
    result = build_match_workspace_materialization_v1(_mixed_complete_workspace())
    assert result.status == "complete"


def test_structurally_complete_workspace_with_incomplete_game_blocks_list() -> None:
    workspace = _all_passed_workspace()
    incomplete = _definition()
    game = _complete_observed_game(incomplete, match_position=3)
    from skat_ai.observed_game_contracts import build_observed_game_record_v1

    partial = build_observed_game_record_v1(
        workspace.match_definition,
        game_id="partial-game",
        match_position=3,
        game_timecode=None,
        seat_order_player_ids=tuple(player.player_id for player in game.players),
        perspective_initial_hand=game.perspective_initial_hand,
        declarer_player_id=game.declarer_player_id,
        declaration=game.declaration,
        original_skat=game.original_skat,
        discarded_cards=game.discarded_cards,
        plays=game.plays[:3],
        commentaries=(),
        response_links=(),
    )
    workspace = set_match_workspace_observed_game_v1(
        workspace,
        partial,
        expected_revision=workspace.revision,
    ).workspace
    result = build_match_workspace_materialization_v1(workspace)
    assert result.status == "partial"
    assert result.historical_list_materialization.unavailable_reason == (
        "observed_game_not_historical_materializable"
    )
    assert result.historical_list_materialization.unavailable_positions == (3,)


def test_public_package_schema_and_scenario_boundaries_remain_unchanged() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    authoritative_schemas = tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))
    packaged_schemas = tuple(
        (PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob("*.schema.json")
    )
    assert pyproject["project"]["version"] == "0.16.0"
    assert skat_ai.__version__ == "0.16.0"
    assert len(authoritative_schemas) == 71
    assert len(packaged_schemas) == 71
    assert len(SCENARIOS) == 98
    assert len(tuple(WorkflowV1)) == 7
    assert not hasattr(api_v1, "MatchWorkspaceMaterializationV1")
    assert not hasattr(session_api, "MatchWorkspaceMaterializationV1")
    json.dumps(
        build_match_workspace_materialization_v1(create_match_workspace_v1(_definition())).to_dict()
    )


def test_training_collection_rejects_noncanonical_record_identity() -> None:
    result = build_match_workspace_materialization_v1(_mixed_complete_workspace())
    source = result.training_source_collection.records[0]
    forged_record = type(source)(
        record_id=f"{result.match_id}-record-extra-03",
        provenance=source.provenance,
        historical_game=source.historical_game,
    )
    with pytest.raises(ValueError, match="exact Match IDs"):
        MatchTrainingSourceCollectionV1(
            match_id=result.match_id,
            available_record_count=1,
            unavailable_record_count=35,
            records=(forged_record,),
            unavailable_positions=tuple(position for position in range(1, 37) if position != 3),
        )
