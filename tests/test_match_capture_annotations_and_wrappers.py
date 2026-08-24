import ast
import builtins
import json
import socket
import tomllib
import urllib.request
from pathlib import Path

import pytest
from test_match_workspace_contracts import _definition

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.api.v1.session as session_api
import skat_ai.api.v1.session.files as session_files_api
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.cli.root_parser import build_argument_parser
from skat_ai.cli.session_parser import build_session_argument_parser
from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_capture_application import (
    append_match_capture_plays_v1,
    clear_match_capture_position_v1,
    mark_match_capture_passed_deal_v1,
    remove_match_capture_commentary_v1,
    remove_match_capture_response_link_v1,
    set_match_capture_commentary_v1,
    set_match_capture_declaration_v1,
    set_match_capture_game_timecode_v1,
    set_match_capture_response_link_v1,
    start_match_capture_game_v1,
    truncate_match_capture_plays_v1,
    undo_match_capture_last_play_v1,
)
from skat_ai.match_capture_application_contracts import MatchCaptureCardEntryV1
from skat_ai.match_capture_game_updates import (
    build_default_match_capture_commentary_id_v1,
    build_default_match_capture_response_link_id_v1,
)
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _entry(card: str) -> MatchCaptureCardEntryV1:
    return MatchCaptureCardEntryV1(card=card, decision_timecode=None)


def _played_workspace(*, count: int = 6):
    workspace = create_match_workspace_v1(_definition())
    workspace = start_match_capture_game_v1(
        workspace,
        match_position=1,
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    workspace = set_match_capture_declaration_v1(
        workspace,
        match_position=1,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    cards = ("CA", "S7", "C7", "D7", "H7", "D8")[:count]
    if cards:
        workspace = append_match_capture_plays_v1(
            workspace,
            match_position=1,
            entries=tuple(_entry(card) for card in cards),
            expected_revision=workspace.revision,
        ).workspace_change.workspace
    return workspace


def _set_commentary(
    workspace,
    *,
    decision: int,
    commentary_id: str | None = None,
    text: str = "Observed explanation.",
    commentator_player_id: str | None = "player-a",
    commentator_name: str | None = None,
):
    return set_match_capture_commentary_v1(
        workspace,
        match_position=1,
        decision_index=decision,
        commentator_player_id=commentator_player_id,
        commentator_name=commentator_name,
        text=text,
        commentary_timecode=None,
        expected_revision=workspace.revision,
        commentary_id=commentary_id,
    )


def test_generated_annotation_ids_use_game_identity_and_next_workspace_revision() -> None:
    workspace = _played_workspace(count=2)
    expected_commentary_id = f"match-160-game-01-commentary-r{workspace.revision + 1}"
    assert (
        build_default_match_capture_commentary_id_v1(
            workspace,
            match_position=1,
        )
        == expected_commentary_id
    )
    commentary = _set_commentary(workspace, decision=1)
    assert commentary.affected_commentary_id == expected_commentary_id
    assert (
        commentary.workspace_change.workspace.slots[0].observed_game.commentaries[0].commentary_id
        == expected_commentary_id
    )

    retained = commentary.workspace_change.workspace
    expected_link_id = f"match-160-game-01-response-r{retained.revision + 1}"
    assert (
        build_default_match_capture_response_link_id_v1(
            retained,
            match_position=1,
        )
        == expected_link_id
    )
    link = set_match_capture_response_link_v1(
        retained,
        match_position=1,
        commentary_id=expected_commentary_id,
        response_decision_index=2,
        expected_revision=retained.revision,
    )
    assert link.affected_response_link_id == expected_link_id
    assert (
        link.workspace_change.workspace.slots[0].observed_game.response_links[0].link_id
        == expected_link_id
    )


def test_generated_annotation_id_collisions_are_rejected_deterministically() -> None:
    workspace = _played_workspace(count=3)
    future_commentary_id = f"match-160-game-01-commentary-r{workspace.revision + 2}"
    retained = _set_commentary(
        workspace,
        decision=1,
        commentary_id=future_commentary_id,
    ).workspace_change.workspace
    with pytest.raises(ValueError, match="generated Commentary ID collides"):
        _set_commentary(retained, decision=2)

    commentary_id = retained.slots[0].observed_game.commentaries[0].commentary_id
    future_link_id = f"match-160-game-01-response-r{retained.revision + 2}"
    retained = set_match_capture_response_link_v1(
        retained,
        match_position=1,
        commentary_id=commentary_id,
        response_decision_index=2,
        expected_revision=retained.revision,
        link_id=future_link_id,
    ).workspace_change.workspace
    with pytest.raises(ValueError, match="generated Response Link ID collides"):
        set_match_capture_response_link_v1(
            retained,
            match_position=1,
            commentary_id=commentary_id,
            response_decision_index=3,
            expected_revision=retained.revision,
        )


def test_commentary_add_replace_equal_and_subject_derivation_preserve_free_text() -> None:
    workspace = _played_workspace(count=3)
    added = _set_commentary(
        workspace,
        decision=2,
        commentary_id="explicit-commentary",
        text="First line\nSecond line",
        commentator_player_id=None,
        commentator_name="Video analyst",
    )
    assert added.status == "applied"
    item = added.workspace_change.workspace.slots[0].observed_game.commentaries[0]
    assert item.subject_player_id == "player-c"
    assert item.commentator_name == "Video analyst"
    assert item.text == "First line\nSecond line"
    assert {
        "taxonomy",
        "sentiment",
        "tactical_category",
        "error_type",
        "optimality",
        "ai_label",
    }.isdisjoint(item.to_dict())

    replaced = _set_commentary(
        added.workspace_change.workspace,
        decision=3,
        commentary_id="explicit-commentary",
        text="Replacement text.",
        commentator_player_id="player-b",
    )
    replacement = replaced.workspace_change.workspace.slots[0].observed_game.commentaries[0]
    assert replacement.decision_index == 3
    assert replacement.subject_player_id == "player-a"
    assert replacement.commentator_player_id == "player-b"
    equal = _set_commentary(
        replaced.workspace_change.workspace,
        decision=3,
        commentary_id="explicit-commentary",
        text="Replacement text.",
        commentator_player_id="player-b",
    )
    assert equal.status == "unchanged"
    assert equal.affected_commentary_id == "explicit-commentary"


def test_commentary_timecode_and_later_game_timecode_updates_reconcile() -> None:
    workspace = create_match_workspace_v1(_definition())
    workspace = start_match_capture_game_v1(
        workspace,
        match_position=1,
        expected_revision=0,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=20_000,
            end_offset_ms=50_000,
        ),
    ).workspace_change.workspace
    workspace = set_match_capture_declaration_v1(
        workspace,
        match_position=1,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    workspace = append_match_capture_plays_v1(
        workspace,
        match_position=1,
        entries=(_entry("CA"), _entry("S7")),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    commentary = set_match_capture_commentary_v1(
        workspace,
        match_position=1,
        decision_index=1,
        commentator_player_id="player-a",
        commentator_name=None,
        text="Timed observation.",
        commentary_timecode=MediaTimecodeV1(
            start_offset_ms=30_000,
            end_offset_ms=None,
        ),
        expected_revision=workspace.revision,
        commentary_id="timed-commentary",
    )
    retained = commentary.workspace_change.workspace
    with pytest.raises(ValueError, match="within game_timecode"):
        set_match_capture_game_timecode_v1(
            retained,
            match_position=1,
            game_timecode=MediaTimecodeV1(
                start_offset_ms=35_000,
                end_offset_ms=45_000,
            ),
            expected_revision=retained.revision,
        )
    with pytest.raises(ValueError, match="within game_timecode"):
        set_match_capture_commentary_v1(
            retained,
            match_position=1,
            decision_index=2,
            commentator_player_id="player-a",
            commentator_name=None,
            text="Outside bounds.",
            commentary_timecode=MediaTimecodeV1(
                start_offset_ms=60_000,
                end_offset_ms=None,
            ),
            expected_revision=retained.revision,
            commentary_id="outside-commentary",
        )


def test_commentary_replacement_preserves_valid_links_and_removes_newly_invalid_links() -> None:
    workspace = _played_workspace(count=4)
    commentary = _set_commentary(
        workspace,
        decision=1,
        commentary_id="commentary-1",
    ).workspace_change.workspace
    link_two = set_match_capture_response_link_v1(
        commentary,
        match_position=1,
        commentary_id="commentary-1",
        response_decision_index=2,
        expected_revision=commentary.revision,
        link_id="link-2",
    ).workspace_change.workspace
    link_four = set_match_capture_response_link_v1(
        link_two,
        match_position=1,
        commentary_id="commentary-1",
        response_decision_index=4,
        expected_revision=link_two.revision,
        link_id="link-4",
    ).workspace_change.workspace

    replaced = _set_commentary(
        link_four,
        decision=3,
        commentary_id="commentary-1",
        text="Later subject.",
    )
    assert replaced.removed_response_link_ids == ("link-2",)
    game = replaced.workspace_change.workspace.slots[0].observed_game
    assert tuple(link.link_id for link in game.response_links) == ("link-4",)


def test_remove_commentary_cascades_links_and_unknown_id_is_unchanged() -> None:
    workspace = _played_workspace(count=3)
    workspace = _set_commentary(
        workspace,
        decision=1,
        commentary_id="commentary-1",
    ).workspace_change.workspace
    workspace = set_match_capture_response_link_v1(
        workspace,
        match_position=1,
        commentary_id="commentary-1",
        response_decision_index=2,
        expected_revision=workspace.revision,
        link_id="link-1",
    ).workspace_change.workspace
    removed = remove_match_capture_commentary_v1(
        workspace,
        match_position=1,
        commentary_id="commentary-1",
        expected_revision=workspace.revision,
    )
    assert removed.status == "applied"
    assert removed.removed_commentary_ids == ("commentary-1",)
    assert removed.removed_response_link_ids == ("link-1",)
    game = removed.workspace_change.workspace.slots[0].observed_game
    assert game.commentaries == game.response_links == ()
    unknown = remove_match_capture_commentary_v1(
        removed.workspace_change.workspace,
        match_position=1,
        commentary_id="unknown-commentary",
        expected_revision=removed.workspace_change.current_revision,
    )
    assert unknown.status == "unchanged"
    assert unknown.removed_commentary_ids == unknown.removed_response_link_ids == ()


def test_response_link_add_replace_equal_duplicate_direction_and_remove() -> None:
    workspace = _played_workspace(count=4)
    workspace = _set_commentary(
        workspace,
        decision=1,
        commentary_id="commentary-1",
    ).workspace_change.workspace
    added = set_match_capture_response_link_v1(
        workspace,
        match_position=1,
        commentary_id="commentary-1",
        response_decision_index=2,
        expected_revision=workspace.revision,
        link_id="link-1",
    )
    assert added.status == "applied"
    assert added.affected_response_link_id == "link-1"
    replaced = set_match_capture_response_link_v1(
        added.workspace_change.workspace,
        match_position=1,
        commentary_id="commentary-1",
        response_decision_index=4,
        expected_revision=added.workspace_change.current_revision,
        link_id="link-1",
    )
    assert (
        replaced.workspace_change.workspace.slots[0]
        .observed_game.response_links[0]
        .response_decision_index
        == 4
    )
    equal = set_match_capture_response_link_v1(
        replaced.workspace_change.workspace,
        match_position=1,
        commentary_id="commentary-1",
        response_decision_index=4,
        expected_revision=replaced.workspace_change.current_revision,
        link_id="link-1",
    )
    assert equal.status == "unchanged"

    for commentary_id, response_index, message in (
        ("missing", 2, "retained commentary"),
        ("commentary-1", 1, "later observed decision"),
    ):
        with pytest.raises(ValueError, match=message):
            set_match_capture_response_link_v1(
                replaced.workspace_change.workspace,
                match_position=1,
                commentary_id=commentary_id,
                response_decision_index=response_index,
                expected_revision=replaced.workspace_change.current_revision,
                link_id="invalid-link",
            )
    with pytest.raises(ValueError, match="Duplicate commentary"):
        set_match_capture_response_link_v1(
            replaced.workspace_change.workspace,
            match_position=1,
            commentary_id="commentary-1",
            response_decision_index=4,
            expected_revision=replaced.workspace_change.current_revision,
            link_id="duplicate-pair",
        )

    removed = remove_match_capture_response_link_v1(
        replaced.workspace_change.workspace,
        match_position=1,
        link_id="link-1",
        expected_revision=replaced.workspace_change.current_revision,
    )
    assert removed.removed_response_link_ids == ("link-1",)
    assert removed.workspace_change.workspace.slots[0].observed_game.response_links == ()
    unknown = remove_match_capture_response_link_v1(
        removed.workspace_change.workspace,
        match_position=1,
        link_id="missing-link",
        expected_revision=removed.workspace_change.current_revision,
    )
    assert unknown.status == "unchanged"
    assert unknown.removed_response_link_ids == ()
    assert {
        "causality",
        "correctness",
        "tactical_category",
        "optimality",
    }.isdisjoint(added.to_dict())


def test_truncation_removes_invalid_suffix_annotations_and_retains_valid_ones() -> None:
    workspace = _played_workspace(count=6)
    workspace = _set_commentary(
        workspace,
        decision=1,
        commentary_id="commentary-1",
    ).workspace_change.workspace
    workspace = _set_commentary(
        workspace,
        decision=5,
        commentary_id="commentary-5",
    ).workspace_change.workspace
    for link_id, commentary_id, response in (
        ("link-valid", "commentary-1", 2),
        ("link-response-removed", "commentary-1", 6),
        ("link-commentary-removed", "commentary-5", 6),
    ):
        workspace = set_match_capture_response_link_v1(
            workspace,
            match_position=1,
            commentary_id=commentary_id,
            response_decision_index=response,
            expected_revision=workspace.revision,
            link_id=link_id,
        ).workspace_change.workspace
    source_revision = workspace.revision
    truncated = truncate_match_capture_plays_v1(
        workspace,
        match_position=1,
        target_play_count=4,
        expected_revision=workspace.revision,
    )
    assert truncated.status == "applied"
    assert truncated.workspace_change.current_revision == source_revision + 1
    assert truncated.removed_commentary_ids == ("commentary-5",)
    assert truncated.removed_response_link_ids == (
        "link-response-removed",
        "link-commentary-removed",
    )
    game = truncated.workspace_change.workspace.slots[0].observed_game
    assert len(game.plays) == 4
    assert tuple(item.commentary_id for item in game.commentaries) == ("commentary-1",)
    assert tuple(item.link_id for item in game.response_links) == ("link-valid",)
    assert truncated.position_view.play_count == 4
    assert truncated.position_view.current_trick_cards == ("D7",)
    assert truncated.position_view.next_player_id == "player-c"
    assert truncated.position_view.evidence_summary.commentary_count == 1


def test_truncate_equal_invalid_zero_and_undo_recompute_without_persistent_log() -> None:
    workspace = _played_workspace(count=3)
    equal = truncate_match_capture_plays_v1(
        workspace,
        match_position=1,
        target_play_count=3,
        expected_revision=workspace.revision,
    )
    assert equal.status == "unchanged"
    assert equal.workspace_change.workspace is workspace
    for target in (-1, 4, True, 1.0):
        with pytest.raises(ValueError, match="target_play_count"):
            truncate_match_capture_plays_v1(
                workspace,
                match_position=1,
                target_play_count=target,
                expected_revision=workspace.revision,
            )
    undone = undo_match_capture_last_play_v1(
        workspace,
        match_position=1,
        expected_revision=workspace.revision,
    )
    assert undone.position_view.play_count == 2
    assert undone.position_view.current_trick_cards == ("CA", "S7")
    assert "undo_log" not in undone.to_dict()

    no_plays = _played_workspace(count=0)
    no_op = undo_match_capture_last_play_v1(
        no_plays,
        match_position=1,
        expected_revision=no_plays.revision,
    )
    assert no_op.status == "unchanged"
    assert no_op.position_view.can_truncate_plays is False


def test_truncate_one_complete_trick_and_to_zero() -> None:
    workspace = _played_workspace(count=6)
    one_trick = truncate_match_capture_plays_v1(
        workspace,
        match_position=1,
        target_play_count=3,
        expected_revision=workspace.revision,
    )
    assert one_trick.position_view.play_count == 3
    assert one_trick.position_view.completed_trick_count == 1
    assert one_trick.position_view.current_trick_cards == ()
    assert one_trick.position_view.next_player_id == "player-b"
    zero = truncate_match_capture_plays_v1(
        workspace,
        match_position=1,
        target_play_count=0,
        expected_revision=workspace.revision,
    )
    assert zero.position_view.game_state == "ready_for_play"
    assert zero.position_view.play_count == 0
    assert zero.position_view.played_cards == ()
    assert zero.position_view.next_player_id == "player-b"
    assert zero.position_view.evidence_summary.play_count == 0


def test_passed_deal_and_clear_wrappers_reconcile_view_progress_and_conflicts() -> None:
    source = create_match_workspace_v1(_definition())
    passed = mark_match_capture_passed_deal_v1(
        source,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    )
    assert passed.operation == "mark_passed_deal"
    assert passed.status == "applied"
    assert passed.position_view.game_state == "passed_deal"
    assert passed.position_view.game_id is None
    assert passed.position_view.workspace_progress.passed_deal_count == 1
    assert passed.workspace_change.workspace.slots[0].observed_game is None

    conflict = clear_match_capture_position_v1(
        passed.workspace_change.workspace,
        match_position=1,
        expected_revision=0,
    )
    assert conflict.status == "revision_conflict"
    assert conflict.workspace_change.workspace is passed.workspace_change.workspace
    assert conflict.position_view.game_state == "passed_deal"
    cleared = clear_match_capture_position_v1(
        passed.workspace_change.workspace,
        match_position=1,
        expected_revision=passed.workspace_change.current_revision,
    )
    assert cleared.status == "applied"
    assert cleared.position_view.game_state == "empty"
    assert cleared.position_view.workspace_progress.status == "empty"
    assert (
        clear_match_capture_position_v1(
            cleared.workspace_change.workspace,
            match_position=1,
            expected_revision=cleared.workspace_change.current_revision,
        ).status
        == "unchanged"
    )

    game_workspace = _played_workspace(count=1)
    replaced = mark_match_capture_passed_deal_v1(
        game_workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=game_workspace.revision,
    )
    assert replaced.position_view.game_state == "passed_deal"
    assert replaced.workspace_change.previous_slot.observed_game is not None

    observed = _played_workspace(count=1)
    cleared_observed = clear_match_capture_position_v1(
        observed,
        match_position=1,
        expected_revision=observed.revision,
    )
    assert cleared_observed.status == "applied"
    assert cleared_observed.workspace_change.previous_slot.observed_game is not None
    assert cleared_observed.position_view.game_state == "empty"


def test_capture_services_execute_no_file_network_application_or_hidden_workflow(
    monkeypatch,
) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("Forbidden transport or workflow executed.")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(urllib.request, "urlopen", fail)
    monkeypatch.setattr(
        "skat_ai.application.execution.execute_application_invocation",
        fail,
    )
    result = start_match_capture_game_v1(
        create_match_workspace_v1(_definition()),
        match_position=1,
        expected_revision=0,
    )
    assert result.status == "applied"


def test_capture_import_architecture_has_no_transport_persistence_or_analysis_dependencies() -> (
    None
):
    module_paths = tuple(
        PROJECT_ROOT / "src" / "skat_ai" / filename
        for filename in (
            "match_capture_application_contracts.py",
            "match_capture_position_view.py",
            "match_capture_game_updates.py",
            "match_capture_application.py",
        )
    )
    forbidden_prefixes = (
        "skat_ai.cli",
        "skat_ai.api",
        "skat_ai.application",
        "skat_ai.match_workspace_persistence",
        "skat_ai.session",
        "skat_ai.historical",
        "skat_ai.search",
        "skat_ai.bounded_search",
        "skat_ai.replay_coaching",
        "skat_ai.training_dataset",
    )
    for module_path in module_paths:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.append(node.module)
        assert not any(
            name == prefix or name.startswith(f"{prefix}.")
            for name in imported
            for prefix in forbidden_prefixes
        ), (module_path, imported)
    for cli_path in (PROJECT_ROOT / "src" / "skat_ai" / "cli").glob("*.py"):
        if cli_path.name in {"capture.py", "capture_parser.py"}:
            continue
        source = cli_path.read_text(encoding="utf-8")
        assert "match_capture_application" not in source


def test_public_cli_package_schema_output_and_persistence_boundaries_are_unchanged() -> None:
    internal_names = {
        "MatchCaptureCardEntryV1",
        "MatchCapturePositionViewV1",
        "MatchCaptureApplicationResultV1",
        "start_match_capture_game_v1",
        "append_match_capture_play_v1",
    }
    for namespace in (
        skat_ai,
        api_v1,
        session_api,
        session_files_api,
    ):
        assert internal_names.isdisjoint(getattr(namespace, "__all__", ()))
        assert all(not hasattr(namespace, name) for name in internal_names)
    root_help = build_argument_parser().format_help()
    session_help = build_session_argument_parser().format_help()
    assert "match-capture" not in root_help
    assert "match-capture" not in session_help
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 71
    assert (
        len(tuple((PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob("*.schema.json")))
        == 71
    )
    assert len(SCENARIOS) == 98
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        assert tomllib.load(file)["project"]["version"] == "0.16.0"

    document = build_match_workspace_persistence_document_v1(
        create_match_workspace_v1(_definition())
    ).to_dict()
    assert tuple(document) == (
        "match_workspace_persistence_version",
        "document_kind",
        "workspace_fingerprint",
        "content_fingerprint",
        "workspace",
    )
    serialized = json.dumps(document, ensure_ascii=True, indent=2) + "\n"
    assert "position_view" not in serialized
    assert "match_capture_application_result_version" not in serialized
