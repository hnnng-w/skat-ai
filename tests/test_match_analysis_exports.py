import hashlib
import json

import pytest
from test_match_workspace_contracts import _definition
from test_match_workspace_materialization import (
    _all_passed_workspace,
    _mixed_complete_workspace,
)

from skat_ai.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    build_match_analysis_report_v1,
    prepare_match_materialization_report_v1,
)
from skat_ai.match_analysis_exports import (
    MatchArtifactExportV1,
    build_match_historical_game_collection_export_v1,
    build_match_historical_list_aggregation_export_v1,
    build_match_historical_list_input_export_v1,
    build_match_materialization_summary_export_v1,
    build_match_report_result_export_v1,
    build_match_training_source_collection_export_v1,
    canonical_match_artifact_json_bytes_v1,
)
from skat_ai.match_decision_analysis import execute_match_decision_analysis_v1
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_materialization import (
    build_match_workspace_materialization_v1,
)


def test_materialization_and_collection_exports_have_exact_shapes_and_names() -> None:
    materialization = build_match_workspace_materialization_v1(
        _mixed_complete_workspace()
    )
    summary = build_match_materialization_summary_export_v1(materialization)
    assert summary.filename == f"{materialization.match_id}-materialization.json"
    assert summary.document_to_dict() == materialization.to_dict()

    games = build_match_historical_game_collection_export_v1(materialization)
    games_document = games.document_to_dict()
    assert games.filename == f"{materialization.match_id}-historical-games.json"
    assert games_document["match_artifact_export_version"] == 1
    assert games_document["match_id"] == materialization.match_id
    assert games_document["workspace_revision"] == materialization.workspace_revision
    assert games_document["available_game_count"] == 1
    assert games_document["games"][0]["match_position"] == 3
    assert set(games_document["games"][0]) == {
        "match_position",
        "historical_game_input",
    }
    assert games_document["unavailable_positions"] == [
        position for position in range(1, 37) if position != 3
    ]

    training = build_match_training_source_collection_export_v1(materialization)
    assert training.filename == f"{materialization.match_id}-training-sources.json"
    assert training.document_to_dict() == materialization.training_source_collection.to_dict()


def test_available_list_exports_reuse_existing_serializers() -> None:
    materialization = build_match_workspace_materialization_v1(
        _all_passed_workspace()
    )
    list_input = build_match_historical_list_input_export_v1(materialization)
    assert list_input.filename == (
        f"{materialization.match_id}-historical-list-input.json"
    )
    assert set(list_input.document_to_dict()) == {
        "fixed_three_player_historical_list_input"
    }
    assert list_input.document_to_dict()[
        "fixed_three_player_historical_list_input"
    ]["list_id"] == f"{materialization.match_id}-list"

    aggregation = build_match_historical_list_aggregation_export_v1(
        materialization
    )
    assert aggregation.filename == (
        f"{materialization.match_id}-historical-list-aggregation.json"
    )
    assert aggregation.document_to_dict()["ranking_status"] == "lot_required"
    assert len(aggregation.document_to_dict()["progression"]) == 36


def test_unavailable_list_has_no_export() -> None:
    materialization = prepare_match_materialization_report_v1(
        create_match_workspace_v1(_definition())
    ).materialization
    assert materialization.historical_list_materialization.status == "unavailable"
    with pytest.raises(ValueError, match="unavailable"):
        build_match_historical_list_input_export_v1(materialization)
    with pytest.raises(ValueError, match="unavailable"):
        build_match_historical_list_aggregation_export_v1(materialization)


def test_position_root_result_export_is_exact_and_method_named() -> None:
    workspace = _mixed_complete_workspace()
    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    report = build_match_analysis_report_v1(result)
    exported = build_match_report_result_export_v1(report)
    assert exported.filename == (
        f"{result.match_id}-position-03-decision-01-immediate_expected_value.json"
    )
    assert exported.document_to_dict() == result.result.to_dict()["document"]
    assert "api_contract_version" not in exported.document_to_dict()
    assert "workflow" not in exported.document_to_dict()


def test_canonical_json_bytes_are_utf8_two_space_ascii_lf_and_defensive() -> None:
    document = {"label": "Skat ä", "values": [1, {"ready": True}]}
    expected = (
        json.dumps(document, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")
    assert canonical_match_artifact_json_bytes_v1(document) == expected
    assert b"\r\n" not in expected
    assert expected.endswith(b"\n")
    assert not expected.endswith(b"\n\n")
    assert b"\\u00e4" in expected

    export = MatchArtifactExportV1(
        export_kind="materialization_summary",
        match_id="match-id",
        workspace_revision=2,
        filename="match-id-materialization.json",
        document=document,
    )
    document["values"].clear()
    first = export.document_to_dict()
    first["values"].clear()
    assert export.document_to_dict()["values"] == [1, {"ready": True}]
    assert export.to_bytes() == expected


@pytest.mark.parametrize(
    "filename",
    ("../report.json", "folder/report.json", "folder\\report.json", "report.txt"),
)
def test_artifact_export_rejects_paths_and_non_json_names(filename: str) -> None:
    with pytest.raises(ValueError, match="filename"):
        MatchArtifactExportV1(
            export_kind="materialization_summary",
            match_id="match-id",
            workspace_revision=0,
            filename=filename,
            document={},
        )


@pytest.mark.parametrize(
    "match_id",
    (
        "match/with/slashes",
        "match\\with\\slashes",
        'match\"with\r\ncontrols',
        "match-with-unicode-ä",
        "match-with-percent-%2F",
        "\ud800",
        "m" * 300,
    ),
)
def test_opaque_match_ids_use_bounded_deterministic_ascii_filenames(
    match_id: str,
) -> None:
    materialization = build_match_workspace_materialization_v1(
        create_match_workspace_v1(_definition(match_id=match_id))
    )
    exported = build_match_materialization_summary_export_v1(materialization)
    canonical_id = json.dumps(
        match_id,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("ascii")
    expected_stem = f"match-{hashlib.sha256(canonical_id).hexdigest()}"
    assert exported.filename == f"{expected_stem}-materialization.json"
    assert exported.filename.isascii()
    assert len(exported.filename) < 255
    assert all(character not in exported.filename for character in '/\\\r\n\"%')
