import copy
import hashlib
import json
from collections import OrderedDict
from dataclasses import replace

import pytest
from test_match_capture_contracts import _capture
from test_match_workspace_contracts import (
    _annotated_observed_game,
    _complete_observed_game,
    _definition,
    _observed_game,
    _set_game,
)

import skatmind.match_workspace_persistence_codec as codec_module
from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.game_declaration import GameDeclaration
from skatmind.match_source_metadata import MatchSourceMetadataV1, MediaTimecodeV1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import (
    mark_match_workspace_passed_deal_v1,
    replace_match_workspace_definition_v1,
    set_match_workspace_observed_game_v1,
)
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_fingerprint_v1,
    build_match_workspace_persistence_document_v1,
    resume_match_workspace_document_v1,
)
from skatmind.observed_game_trace import ObservedPlayV1


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _empty_document():
    return build_match_workspace_persistence_document_v1(
        create_match_workspace_v1(_definition())
    )


def _rich_document():
    definition = _capture()
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(workspace, _complete_observed_game(definition))
    return build_match_workspace_persistence_document_v1(workspace)


def test_workspace_and_content_fingerprints_match_independent_domain_oracles() -> None:
    document = _rich_document()
    expected_workspace = hashlib.sha256(
        b"skatmind\0match_workspace_v1\0"
        + _canonical_bytes(document.workspace.to_dict())
    ).hexdigest()
    content = document.to_dict()
    del content["content_fingerprint"]
    expected_content = hashlib.sha256(
        b"skatmind\0match_workspace_persistence_v1\0"
        + _canonical_bytes(content)
    ).hexdigest()
    assert document.workspace_fingerprint == expected_workspace
    assert document.content_fingerprint == expected_content
    assert build_match_workspace_fingerprint_v1(document.workspace) == expected_workspace
    assert len(expected_workspace) == len(expected_content) == 64


def test_same_revision_different_content_has_distinct_workspace_and_content_identity() -> None:
    source = create_match_workspace_v1(_definition())
    first = mark_match_workspace_passed_deal_v1(
        source,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    second = mark_match_workspace_passed_deal_v1(
        source,
        match_position=2,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    first_document = build_match_workspace_persistence_document_v1(first)
    second_document = build_match_workspace_persistence_document_v1(second)
    assert first.revision == second.revision == 1
    assert first_document.workspace_fingerprint != second_document.workspace_fingerprint
    assert first_document.content_fingerprint != second_document.content_fingerprint


def test_every_retained_content_family_changes_the_workspace_fingerprint() -> None:
    definition = _definition()
    empty = create_match_workspace_v1(definition)
    baseline = build_match_workspace_fingerprint_v1(empty)
    passed = mark_match_workspace_passed_deal_v1(
        empty,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    timed_passed = mark_match_workspace_passed_deal_v1(
        empty,
        match_position=1,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=20_000,
            end_offset_ms=30_000,
        ),
        expected_revision=0,
    ).workspace
    game_workspace = _set_game(
        empty,
        _observed_game(definition, match_position=1),
    )
    annotated = _set_game(
        empty,
        _annotated_observed_game(definition),
    )
    corrected_definition = replace(definition, title="Corrected metadata")
    metadata = replace_match_workspace_definition_v1(
        empty,
        corrected_definition,
        expected_revision=0,
    ).workspace
    fingerprints = {
        baseline,
        build_match_workspace_fingerprint_v1(passed),
        build_match_workspace_fingerprint_v1(timed_passed),
        build_match_workspace_fingerprint_v1(game_workspace),
        build_match_workspace_fingerprint_v1(annotated),
        build_match_workspace_fingerprint_v1(metadata),
    }
    assert len(fingerprints) == 6


def test_play_commentary_and_response_changes_are_fingerprinted_independently() -> None:
    definition = _definition()
    source_game = _annotated_observed_game(definition)
    source = _set_game(create_match_workspace_v1(definition), source_game)
    source_fingerprint = build_match_workspace_fingerprint_v1(source)

    changed_play = ObservedPlayV1(
        decision_index=2,
        player_id="player-b",
        card="S8",
        decision_timecode=None,
    )
    play_game = _observed_game(
        definition,
        match_position=3,
        game_id="annotated-game",
        declarer_player_id="player-a",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        plays=(source_game.plays[0], changed_play),
        commentaries=source_game.commentaries,
        response_links=source_game.response_links,
    )
    changed_commentary = replace(
        source_game.commentaries[0],
        text="Corrected explanation.",
    )
    commentary_game = _observed_game(
        definition,
        match_position=3,
        game_id="annotated-game",
        declarer_player_id="player-a",
        declaration=source_game.declaration,
        plays=source_game.plays,
        commentaries=(changed_commentary,),
        response_links=source_game.response_links,
    )
    changed_link = replace(source_game.response_links[0], link_id="corrected-link")
    link_game = _observed_game(
        definition,
        match_position=3,
        game_id="annotated-game",
        declarer_player_id="player-a",
        declaration=source_game.declaration,
        plays=source_game.plays,
        commentaries=source_game.commentaries,
        response_links=(changed_link,),
    )
    changed = (
        play_game,
        commentary_game,
        link_game,
    )
    fingerprints = {
        build_match_workspace_fingerprint_v1(
            set_match_workspace_observed_game_v1(
                source,
                game,
                expected_revision=source.revision,
            ).workspace
        )
        for game in changed
    }
    assert source_fingerprint not in fingerprints
    assert len(fingerprints) == 3


def test_strict_resume_reconstructs_snapshots_complete_game_and_progress() -> None:
    document = _rich_document()
    resumed = resume_match_workspace_document_v1(document.to_dict())
    assert resumed.document == document
    assert resumed.document.workspace is not document.workspace
    assert resumed.progress.revision == document.workspace.revision
    assert resumed.progress.observed_game_count == 1
    assert resumed.progress.complete_play_trace_count == 1
    snapshot = resumed.document.workspace.match_definition.participants[0].statistics_snapshot
    assert snapshot is not None
    assert snapshot == document.workspace.match_definition.participants[0].statistics_snapshot


def test_strict_resume_reconstructs_partial_annotations_and_passed_deal() -> None:
    definition = _definition()
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _annotated_observed_game(definition),
    )
    workspace = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=4,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=400_000,
            end_offset_ms=410_000,
        ),
        expected_revision=workspace.revision,
    ).workspace
    document = build_match_workspace_persistence_document_v1(workspace)
    resumed = resume_match_workspace_document_v1(document.to_dict())
    assert resumed.document == document
    assert resumed.progress.observed_game_count == 1
    assert resumed.progress.passed_deal_count == 1
    assert resumed.progress.commentary_count == 1
    assert resumed.progress.response_link_count == 1


@pytest.mark.parametrize("source_kind", ("youtube_video", "other_video", "manual_observation"))
def test_strict_resume_reconstructs_every_match_source_kind(source_kind: str) -> None:
    if source_kind == "manual_observation":
        source = MatchSourceMetadataV1(
            source_kind=source_kind,
            source_url=None,
            source_title="Manual observation",
            source_channel_name=None,
            match_timecode=None,
        )
    else:
        source = MatchSourceMetadataV1(
            source_kind=source_kind,
            source_url="https://example.com/match/163",
            source_title="Video observation",
            source_channel_name="Example channel",
            match_timecode=MediaTimecodeV1(
                start_offset_ms=0,
                end_offset_ms=10_000_000,
            ),
        )
    workspace = create_match_workspace_v1(_definition(source=source))
    document = build_match_workspace_persistence_document_v1(workspace)
    assert resume_match_workspace_document_v1(document.to_dict()).document == document


@pytest.mark.parametrize(
    ("game_type", "declaration"),
    (
        ("clubs", GameDeclaration(game_type="clubs", hand_game=True, bid_value=24)),
        ("grand", GameDeclaration(game_type="grand", bid_value=24)),
        ("null", GameDeclaration(game_type="null", ouvert=True, bid_value=46)),
    ),
)
def test_strict_resume_reconstructs_suit_grand_and_null_declarations(
    game_type: str,
    declaration: GameDeclaration,
) -> None:
    definition = _definition()
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"{game_type}-game",
        declarer_player_id="player-a",
        declaration=declaration,
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    document = build_match_workspace_persistence_document_v1(workspace)
    resumed_declaration = (
        resume_match_workspace_document_v1(document.to_dict())
        .document.workspace.slots[2]
        .observed_game.declaration
    )
    assert resumed_declaration == declaration


def test_resume_accepts_alternate_object_order_but_requires_canonical_array_order() -> None:
    document = _rich_document()
    reversed_root = OrderedDict(reversed(tuple(document.to_dict().items())))
    assert resume_match_workspace_document_v1(reversed_root).document == document
    noncanonical = document.to_dict()
    noncanonical["workspace"]["slots"].reverse()
    with pytest.raises(SkatMindValidationError, match="positions"):
        resume_match_workspace_document_v1(noncanonical)


def test_resume_rejects_missing_unknown_and_nested_field_drift() -> None:
    source = _rich_document().to_dict()
    cases = []
    missing_root = copy.deepcopy(source)
    missing_root.pop("document_kind")
    cases.append(missing_root)
    unknown_root = copy.deepcopy(source)
    unknown_root["path"] = "private.json"
    cases.append(unknown_root)
    unknown_workspace = copy.deepcopy(source)
    unknown_workspace["workspace"]["progress"] = {}
    cases.append(unknown_workspace)
    missing_slot = copy.deepcopy(source)
    missing_slot["workspace"]["slots"][0].pop("passed_deal")
    cases.append(missing_slot)
    unknown_game = copy.deepcopy(source)
    unknown_game["workspace"]["slots"][2]["observed_game"]["analysis"] = {}
    cases.append(unknown_game)
    unknown_play = copy.deepcopy(source)
    unknown_play["workspace"]["slots"][2]["observed_game"]["plays"][0][
        "winner"
    ] = True
    cases.append(unknown_play)
    unknown_snapshot = copy.deepcopy(source)
    unknown_snapshot["workspace"]["match_definition"]["participants"][0][
        "statistics_snapshot"
    ]["extra"] = None
    cases.append(unknown_snapshot)
    for value in cases:
        with pytest.raises(SkatMindValidationError):
            resume_match_workspace_document_v1(value)


@pytest.mark.parametrize(
    "tamper",
    (
        "workspace_version",
        "slot_version",
        "passed_version",
        "registry_object",
        "game_linkage",
        "rotation",
        "revision",
        "workspace_fingerprint",
        "content_fingerprint",
    ),
)
def test_resume_rejects_versions_registry_linkage_rotation_and_fingerprint_tampering(
    tamper: str,
) -> None:
    if tamper == "passed_version":
        workspace = mark_match_workspace_passed_deal_v1(
            create_match_workspace_v1(_definition()),
            match_position=1,
            game_timecode=None,
            expected_revision=0,
        ).workspace
        source = build_match_workspace_persistence_document_v1(workspace).to_dict()
    else:
        source = _rich_document().to_dict()
    if tamper == "workspace_version":
        source["workspace"]["match_workspace_contract_version"] = 2
    elif tamper == "slot_version":
        source["workspace"]["slots"][0]["match_workspace_slot_version"] = 2
    elif tamper == "passed_version":
        source["workspace"]["slots"][0]["passed_deal"][
            "match_passed_deal_version"
        ] = 2
    elif tamper == "registry_object":
        source["workspace"]["match_definition"]["tournament_format"][
            "provider"
        ] = "Forged"
    elif tamper == "game_linkage":
        source["workspace"]["slots"][2]["observed_game"]["match_id"] = "wrong"
    elif tamper == "rotation":
        source["workspace"]["slots"][2]["observed_game"]["players"].reverse()
    elif tamper == "revision":
        source["workspace"]["revision"] = True
    elif tamper == "workspace_fingerprint":
        source["workspace_fingerprint"] = "0" * 64
    else:
        source["content_fingerprint"] = "f" * 64
    with pytest.raises(SkatMindValidationError):
        resume_match_workspace_document_v1(source)


def test_resume_rejects_validly_refingerprinted_unreachable_revision() -> None:
    workspace = create_match_workspace_v1(_definition())
    for position in (1, 2):
        workspace = mark_match_workspace_passed_deal_v1(
            workspace,
            match_position=position,
            game_timecode=None,
            expected_revision=workspace.revision,
        ).workspace
    source = build_match_workspace_persistence_document_v1(workspace).to_dict()
    source["workspace"]["revision"] = 1
    source["workspace_fingerprint"] = hashlib.sha256(
        b"skatmind\0match_workspace_v1\0" + _canonical_bytes(source["workspace"])
    ).hexdigest()
    content = copy.deepcopy(source)
    del content["content_fingerprint"]
    source["content_fingerprint"] = hashlib.sha256(
        b"skatmind\0match_workspace_persistence_v1\0" + _canonical_bytes(content)
    ).hexdigest()
    with pytest.raises(SkatMindValidationError, match="occupied"):
        resume_match_workspace_document_v1(source)


@pytest.mark.parametrize("root", (None, [], "workspace"))
def test_resume_requires_mapping_root(root: object) -> None:
    with pytest.raises(SkatMindValidationError, match="JSON object"):
        resume_match_workspace_document_v1(root)


def test_document_build_and_resume_each_use_two_domain_hashes(monkeypatch) -> None:
    workspace = create_match_workspace_v1(_definition())
    count = 0
    original_sha256 = codec_module.hashlib.sha256

    def counted_sha256(value=b""):
        nonlocal count
        count += 1
        return original_sha256(value)

    monkeypatch.setattr(codec_module.hashlib, "sha256", counted_sha256)
    document = codec_module.build_match_workspace_persistence_document_v1(workspace)
    assert count == 2
    count = 0
    resumed = codec_module.resume_match_workspace_document_v1(document.to_dict())
    assert resumed.document == document
    assert count == 2


def test_persistence_build_rejects_forged_internal_workspace_as_invariant() -> None:
    workspace = create_match_workspace_v1(_definition())
    object.__setattr__(workspace, "revision", True)
    with pytest.raises(SkatMindInvariantError, match="inconsistent"):
        build_match_workspace_fingerprint_v1(workspace)
    with pytest.raises(SkatMindInvariantError, match="assembly"):
        build_match_workspace_persistence_document_v1(workspace)


def test_resume_is_deterministic_and_does_not_materialize_downstream_contracts() -> None:
    document = _rich_document()
    first = resume_match_workspace_document_v1(document.to_dict())
    second = resume_match_workspace_document_v1(document.to_dict())
    assert first == second
    serialized = json.dumps(first.to_dict())
    forbidden = {
        "historical_game_input",
        "fixed_three_player_historical_list_input",
        "training_dataset_input",
        "analysis_result",
        "field_provenance",
        "search_worlds",
    }
    assert all(f'"{field}"' not in serialized for field in forbidden)
    assert document.workspace.match_definition.source.source_url in serialized
