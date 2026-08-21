import json
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest
from test_historical_game import build_historical_input
from test_match_capture_contracts import _capture, _participants
from test_observed_game_contracts import (
    declaration_from_historical,
    observed_plays_from_historical,
)

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.api.v1.session as session_api
import skat_ai.api.v1.session.files as session_files_api
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.cli.root_parser import build_argument_parser
from skat_ai.cli.session_parser import build_session_argument_parser
from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_capture_contracts import MatchCaptureDefinitionV1
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.match_workspace_contracts import (
    MATCH_PASSED_DEAL_VERSION,
    MATCH_WORKSPACE_CONTRACT_VERSION,
    MATCH_WORKSPACE_SLOT_KINDS,
    MATCH_WORKSPACE_SLOT_POLICY,
    MATCH_WORKSPACE_SLOT_VERSION,
    MATCH_WORKSPACE_STATUSES,
    MatchPassedDealV1,
    MatchWorkspacePositionFactV1,
    MatchWorkspaceSlotV1,
    MatchWorkspaceV1,
    create_match_workspace_v1,
    validate_match_workspace_v1,
)
from skat_ai.match_workspace_operations import (
    MATCH_WORKSPACE_CHANGE_OPERATIONS,
    MATCH_WORKSPACE_CHANGE_STATUSES,
    MATCH_WORKSPACE_CHANGE_VERSION,
    MatchWorkspaceChangeResultV1,
    clear_match_workspace_slot_v1,
    mark_match_workspace_passed_deal_v1,
    replace_match_workspace_definition_v1,
    set_match_workspace_observed_game_v1,
)
from skat_ai.match_workspace_progress import (
    MATCH_WORKSPACE_PROGRESS_POLICY,
    MATCH_WORKSPACE_PROGRESS_VERSION,
    MatchWorkspaceProgressV1,
    build_match_workspace_progress_v1,
)
from skat_ai.match_workspace_rotation import (
    MATCH_WORKSPACE_ROTATION_POLICY,
    build_match_workspace_position_fact_v1,
    build_match_workspace_position_facts_v1,
    build_match_workspace_seat_assignment_v1,
)
from skat_ai.observed_game_commentary import (
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
)
from skat_ai.observed_game_contracts import build_observed_game_record_v1
from skat_ai.observed_game_trace import ObservedPlayV1

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _definition(**overrides) -> MatchCaptureDefinitionV1:
    values = {
        "participants": _participants(snapshots=False),
    }
    values.update(overrides)
    return _capture(**values)


def _seat_order(
    definition: MatchCaptureDefinitionV1,
    match_position: int,
) -> tuple[str, str, str]:
    assignment = build_match_workspace_seat_assignment_v1(
        definition,
        match_position,
    )
    return (
        assignment.forehand_player_id,
        assignment.middlehand_player_id,
        assignment.rearhand_player_id,
    )


def _observed_game(
    definition: MatchCaptureDefinitionV1,
    *,
    match_position: int = 1,
    game_id: str | None = None,
    game_timecode: MediaTimecodeV1 | None | object = ...,
    **overrides,
):
    if game_timecode is ...:
        start = 20_000 + (match_position - 1) * 100_000
        game_timecode = MediaTimecodeV1(
            start_offset_ms=start,
            end_offset_ms=start + 80_000,
        )
    values = {
        "game_id": game_id or f"observed-game-{match_position}",
        "match_position": match_position,
        "game_timecode": game_timecode,
        "seat_order_player_ids": _seat_order(definition, match_position),
        "perspective_initial_hand": None,
        "declarer_player_id": None,
        "declaration": None,
        "original_skat": None,
        "discarded_cards": None,
        "plays": (),
        "commentaries": (),
        "response_links": (),
    }
    values.update(overrides)
    return build_observed_game_record_v1(definition, **values)


def _complete_observed_game(
    definition: MatchCaptureDefinitionV1,
    *,
    match_position: int = 3,
    game_id: str = "complete-game",
):
    data = build_historical_input(game_type="grand", hand_game=False)
    perspective_hand = next(
        player["initial_hand"]
        for player in data["players"]
        if player["player_id"] == definition.perspective_player_id
    )
    return _observed_game(
        definition,
        match_position=match_position,
        game_id=game_id,
        perspective_initial_hand=perspective_hand,
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"],
        discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data),
    )


def _annotated_observed_game(definition: MatchCaptureDefinitionV1):
    plays = (
        ObservedPlayV1(
            decision_index=1,
            player_id="player-a",
            card="CA",
            decision_timecode=None,
        ),
        ObservedPlayV1(
            decision_index=2,
            player_id="player-b",
            card="S7",
            decision_timecode=None,
        ),
    )
    commentary = ObservedDecisionCommentaryV1(
        commentary_id="comment-1",
        decision_index=1,
        subject_player_id="player-a",
        commentator_player_id="player-a",
        commentator_name=None,
        text="Observed opening explanation.",
        commentary_timecode=None,
    )
    link = ObservedDecisionResponseLinkV1(
        link_id="response-1",
        commentary_id="comment-1",
        response_decision_index=2,
    )
    return _observed_game(
        definition,
        match_position=3,
        game_id="annotated-game",
        declarer_player_id="player-a",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        plays=plays,
        commentaries=(commentary,),
        response_links=(link,),
    )


def _set_game(workspace: MatchWorkspaceV1, game):
    result = set_match_workspace_observed_game_v1(
        workspace,
        game,
        expected_revision=workspace.revision,
    )
    assert result.status == "applied"
    return result.workspace


def test_versions_policies_tuples_and_contract_fields_are_exact() -> None:
    assert (
        MATCH_WORKSPACE_CONTRACT_VERSION,
        MATCH_WORKSPACE_SLOT_VERSION,
        MATCH_PASSED_DEAL_VERSION,
        MATCH_WORKSPACE_PROGRESS_VERSION,
        MATCH_WORKSPACE_CHANGE_VERSION,
    ) == (1, 1, 1, 1, 1)
    assert MATCH_WORKSPACE_SLOT_KINDS == (
        "empty",
        "observed_game",
        "passed_deal",
    )
    assert MATCH_WORKSPACE_STATUSES == ("empty", "in_progress", "complete")
    assert MATCH_WORKSPACE_CHANGE_OPERATIONS == (
        "replace_definition",
        "set_observed_game",
        "mark_passed_deal",
        "clear_slot",
    )
    assert MATCH_WORKSPACE_CHANGE_STATUSES == (
        "applied",
        "unchanged",
        "revision_conflict",
    )
    assert MATCH_WORKSPACE_SLOT_POLICY == "fixed_authoritative_36_position_array"
    assert MATCH_WORKSPACE_ROTATION_POLICY == "reuse_fixed_three_player_list_rotation"
    assert (
        MATCH_WORKSPACE_PROGRESS_POLICY
        == "derived_from_slot_occupancy_and_observed_evidence"
    )
    assert [item.name for item in fields(MatchPassedDealV1)] == [
        "match_passed_deal_version",
        "game_timecode",
    ]
    assert [item.name for item in fields(MatchWorkspaceSlotV1)] == [
        "match_workspace_slot_version",
        "match_position",
        "slot_kind",
        "observed_game",
        "passed_deal",
    ]
    assert [item.name for item in fields(MatchWorkspaceV1)] == [
        "match_workspace_contract_version",
        "revision",
        "match_definition",
        "slots",
    ]
    assert [item.name for item in fields(MatchWorkspacePositionFactV1)] == [
        "match_position",
        "round_number",
        "slot_kind",
        "dealer_player_id",
        "forehand_player_id",
        "middlehand_player_id",
        "rearhand_player_id",
        "game_id",
        "play_count",
        "complete_play_trace",
    ]
    assert [item.name for item in fields(MatchWorkspaceProgressV1)] == [
        "match_workspace_progress_version",
        "status",
        "revision",
        "total_slot_count",
        "empty_slot_count",
        "observed_game_count",
        "passed_deal_count",
        "occupied_slot_count",
        "complete_play_trace_count",
        "perspective_sample_ready_game_count",
        "all_player_sample_ready_game_count",
        "discard_review_ready_game_count",
        "complete_initial_deal_ready_game_count",
        "commentary_count",
        "response_link_count",
        "next_empty_position",
    ]
    assert [item.name for item in fields(MatchWorkspaceChangeResultV1)] == [
        "match_workspace_change_version",
        "operation",
        "status",
        "match_id",
        "expected_revision",
        "source_revision",
        "current_revision",
        "match_position",
        "previous_slot",
        "workspace",
    ]


def test_creation_has_revision_zero_and_36_defensive_empty_slots() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    assert workspace.revision == 0
    assert len(workspace.slots) == 36
    assert tuple(slot.match_position for slot in workspace.slots) == tuple(range(1, 37))
    assert {slot.slot_kind for slot in workspace.slots} == {"empty"}
    assert all(slot.observed_game is None and slot.passed_deal is None for slot in workspace.slots)
    assert workspace.match_definition == definition
    assert workspace.match_definition is not definition
    assert workspace.match_definition.participants is not definition.participants
    assert "game_id" not in workspace.to_dict()["slots"][0]
    validate_match_workspace_v1(workspace)


def test_workspace_values_are_frozen_slotted_keyword_only_and_freshly_serialized() -> None:
    workspace = create_match_workspace_v1(_definition())
    passed = MatchPassedDealV1(game_timecode=None)
    assert not hasattr(workspace, "__dict__")
    assert not hasattr(workspace.slots[0], "__dict__")
    assert not hasattr(passed, "__dict__")
    first = workspace.to_dict()
    second = workspace.to_dict()
    first["slots"][0]["slot_kind"] = "passed_deal"
    first["match_definition"]["participants"][0]["player_label"] = "Changed"
    assert second == workspace.to_dict()
    json.dumps(second)
    with pytest.raises(FrozenInstanceError):
        workspace.revision = 1
    with pytest.raises(TypeError, match="focused builder"):
        MatchWorkspaceV1()
    with pytest.raises(TypeError, match="focused builder"):
        MatchWorkspaceSlotV1()
    with pytest.raises(TypeError):
        MatchPassedDealV1(1, None)


def test_derived_contracts_reject_impossible_play_and_empty_progress_values() -> None:
    values = {
        "match_position": 1,
        "round_number": 1,
        "slot_kind": "observed_game",
        "dealer_player_id": "player-a",
        "forehand_player_id": "player-b",
        "middlehand_player_id": "player-c",
        "rearhand_player_id": "player-a",
        "game_id": "game-1",
        "play_count": 30,
        "complete_play_trace": True,
    }
    with pytest.raises(ValueError, match="exactly"):
        MatchWorkspacePositionFactV1(
            **{**values, "complete_play_trace": False}
        )
    with pytest.raises(ValueError, match="exceed"):
        MatchWorkspacePositionFactV1(**{**values, "play_count": 31})

    progress = build_match_workspace_progress_v1(
        create_match_workspace_v1(_definition())
    )
    with pytest.raises(ValueError, match="next_empty_position 1"):
        replace(progress, next_empty_position=2)
    definition = _definition()
    complete_progress = build_match_workspace_progress_v1(
        _set_game(
            create_match_workspace_v1(definition),
            _complete_observed_game(definition),
        )
    )
    with pytest.raises(ValueError, match="all_player"):
        replace(complete_progress, all_player_sample_ready_game_count=0)


@pytest.mark.parametrize("position", (1, 2, 3, 4, 36))
def test_rotation_reuses_exact_fixed_place_cycle(position: int) -> None:
    definition = _definition()
    assignment = build_match_workspace_seat_assignment_v1(definition, position)
    expected = {
        1: ("player-a", "player-b", "player-c", "player-a", 1),
        2: ("player-b", "player-c", "player-a", "player-b", 1),
        3: ("player-c", "player-a", "player-b", "player-c", 1),
        4: ("player-a", "player-b", "player-c", "player-a", 2),
        36: ("player-c", "player-a", "player-b", "player-c", 12),
    }[position]
    assert (
        assignment.dealer_player_id,
        assignment.forehand_player_id,
        assignment.middlehand_player_id,
        assignment.rearhand_player_id,
        ((position - 1) // 3) + 1,
    ) == expected


def test_all_position_facts_cover_twelve_rounds_and_dealer_is_rearhand() -> None:
    workspace = create_match_workspace_v1(_definition())
    facts = build_match_workspace_position_facts_v1(workspace)
    assert len(facts) == 36
    assert tuple(fact.round_number for fact in facts) == tuple(
        round_number for round_number in range(1, 13) for _ in range(3)
    )
    assert all(fact.dealer_player_id == fact.rearhand_player_id for fact in facts)
    assert {fact.slot_kind for fact in facts} == {"empty"}
    assert all(fact.game_id is None and fact.play_count == 0 for fact in facts)


def test_workspace_creation_delegates_all_36_positions_to_existing_rotation(
    monkeypatch,
) -> None:
    import skat_ai.match_workspace_rotation as rotation_module

    positions = []
    original = rotation_module.build_fixed_three_player_list_seat_assignment

    def recorded(position, player_id_by_place):
        positions.append(position)
        assert tuple(player_id_by_place) == ("place_1", "place_2", "place_3")
        return original(position, player_id_by_place)

    monkeypatch.setattr(
        rotation_module,
        "build_fixed_three_player_list_seat_assignment",
        recorded,
    )
    create_match_workspace_v1(_definition())
    assert positions == list(range(1, 37))


def test_partial_complete_and_passed_slots_produce_exact_position_facts() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(workspace, _observed_game(definition, match_position=1))
    passed_result = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=2,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=120_000,
            end_offset_ms=180_000,
        ),
        expected_revision=workspace.revision,
    )
    workspace = passed_result.workspace
    workspace = _set_game(workspace, _complete_observed_game(definition))
    facts = build_match_workspace_position_facts_v1(workspace)
    assert (facts[0].slot_kind, facts[0].game_id, facts[0].play_count) == (
        "observed_game",
        "observed-game-1",
        0,
    )
    assert facts[1].slot_kind == "passed_deal" and facts[1].game_id is None
    assert facts[2].complete_play_trace is True and facts[2].play_count == 30
    assert build_match_workspace_position_fact_v1(workspace, 3) == facts[2]


def test_observed_game_set_replace_and_equal_unchanged_revision_behavior() -> None:
    definition = _definition()
    source = create_match_workspace_v1(definition)
    partial = _observed_game(definition, match_position=1)
    first = set_match_workspace_observed_game_v1(
        source,
        partial,
        expected_revision=0,
    )
    assert first.status == "applied"
    assert first.source_revision == 0 and first.current_revision == 1
    assert first.previous_slot == source.slots[0]
    assert source.slots[0].slot_kind == "empty"

    equal = set_match_workspace_observed_game_v1(
        first.workspace,
        partial,
        expected_revision=1,
    )
    assert equal.status == "unchanged"
    assert equal.workspace is first.workspace
    assert equal.current_revision == equal.source_revision == 1

    richer = _observed_game(
        definition,
        match_position=1,
        game_id="replacement-game",
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="clubs", bid_value=18),
    )
    replaced = set_match_workspace_observed_game_v1(
        first.workspace,
        richer,
        expected_revision=1,
    )
    assert replaced.status == "applied"
    assert replaced.workspace.revision == 2
    assert replaced.workspace.slots[0].observed_game.game_id == "replacement-game"


def test_partial_can_be_replaced_by_complete_and_passed_content() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(workspace, _observed_game(definition, match_position=3))
    complete = set_match_workspace_observed_game_v1(
        workspace,
        _complete_observed_game(definition),
        expected_revision=workspace.revision,
    )
    assert complete.status == "applied"
    assert len(complete.workspace.slots[2].observed_game.plays) == 30
    passed = mark_match_workspace_passed_deal_v1(
        complete.workspace,
        match_position=3,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=220_000,
            end_offset_ms=300_000,
        ),
        expected_revision=complete.workspace.revision,
    )
    assert passed.status == "applied"
    assert passed.workspace.slots[2].slot_kind == "passed_deal"
    assert passed.workspace.slots[2].observed_game is None

    observed_again = set_match_workspace_observed_game_v1(
        passed.workspace,
        _observed_game(
            definition,
            match_position=3,
            game_id="after-pass-game",
        ),
        expected_revision=passed.workspace.revision,
    )
    assert observed_again.status == "applied"
    assert observed_again.workspace.slots[2].slot_kind == "observed_game"
    assert observed_again.workspace.slots[2].passed_deal is None


def test_passed_deal_equal_unchanged_and_clear_retains_previous_slot() -> None:
    workspace = create_match_workspace_v1(_definition())
    timecode = MediaTimecodeV1(start_offset_ms=20_000, end_offset_ms=40_000)
    passed = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=1,
        game_timecode=timecode,
        expected_revision=0,
    )
    assert passed.status == "applied"
    assert passed.workspace.slots[0].observed_game is None
    assert "game_id" not in passed.workspace.slots[0].passed_deal.to_dict()
    equal = mark_match_workspace_passed_deal_v1(
        passed.workspace,
        match_position=1,
        game_timecode=timecode,
        expected_revision=1,
    )
    assert equal.status == "unchanged" and equal.workspace is passed.workspace
    cleared = clear_match_workspace_slot_v1(
        passed.workspace,
        match_position=1,
        expected_revision=1,
    )
    assert cleared.status == "applied"
    assert cleared.previous_slot == passed.workspace.slots[0]
    assert cleared.workspace.slots[0].slot_kind == "empty"
    unchanged = clear_match_workspace_slot_v1(
        cleared.workspace,
        match_position=1,
        expected_revision=2,
    )
    assert unchanged.status == "unchanged" and unchanged.workspace is cleared.workspace


def test_revision_conflict_precedes_target_semantics_and_preserves_source() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    forged = _observed_game(definition, match_position=1)
    object.__setattr__(forged, "match_id", "wrong-match")
    result = set_match_workspace_observed_game_v1(
        workspace,
        forged,
        expected_revision=5,
    )
    assert result.status == "revision_conflict"
    assert result.workspace is workspace
    assert result.expected_revision == 5
    assert result.source_revision == result.current_revision == 0
    passed = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=1,
        game_timecode="not-a-timecode",
        expected_revision=5,
    )
    assert passed.status == "revision_conflict" and passed.workspace is workspace


def test_wrong_match_position_rotation_perspective_and_duplicate_game_ids_are_rejected() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    wrong_match = _observed_game(definition, match_position=1)
    object.__setattr__(wrong_match, "match_id", "wrong")
    with pytest.raises(ValueError, match="canonical form"):
        set_match_workspace_observed_game_v1(
            workspace,
            wrong_match,
            expected_revision=0,
        )

    wrong_rotation = _observed_game(definition, match_position=1)
    object.__setattr__(wrong_rotation.players[0], "player_id", "player-a")
    with pytest.raises(ValueError):
        set_match_workspace_observed_game_v1(
            workspace,
            wrong_rotation,
            expected_revision=0,
        )

    wrong_perspective = _observed_game(definition, match_position=1)
    object.__setattr__(wrong_perspective, "perspective_player_id", "player-b")
    with pytest.raises(ValueError, match="canonical form"):
        set_match_workspace_observed_game_v1(
            workspace,
            wrong_perspective,
            expected_revision=0,
        )

    wrong_position = _observed_game(definition, match_position=1)
    object.__setattr__(wrong_position, "match_position", 2)
    with pytest.raises(ValueError):
        set_match_workspace_observed_game_v1(
            workspace,
            wrong_position,
            expected_revision=0,
        )

    first = _set_game(
        workspace,
        _observed_game(definition, match_position=1, game_id="duplicate-game"),
    )
    with pytest.raises(ValueError, match="unique"):
        set_match_workspace_observed_game_v1(
            first,
            _observed_game(definition, match_position=2, game_id="duplicate-game"),
            expected_revision=first.revision,
        )


def test_global_slot_timecodes_allow_missing_equal_and_overlap_but_reject_decrease() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(
        workspace,
        _observed_game(
            definition,
            match_position=1,
            game_timecode=MediaTimecodeV1(
                start_offset_ms=100_000,
                end_offset_ms=300_000,
            ),
        ),
    )
    workspace = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=2,
        game_timecode=None,
        expected_revision=workspace.revision,
    ).workspace
    equal_overlap = _observed_game(
        definition,
        match_position=3,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=100_000,
            end_offset_ms=200_000,
        ),
    )
    workspace = _set_game(workspace, equal_overlap)
    assert workspace.slots[2].observed_game == equal_overlap
    with pytest.raises(ValueError, match="non-decreasing"):
        set_match_workspace_observed_game_v1(
            workspace,
            _observed_game(
                definition,
                match_position=4,
                game_timecode=MediaTimecodeV1(
                    start_offset_ms=90_000,
                    end_offset_ms=110_000,
                ),
            ),
            expected_revision=workspace.revision,
        )


def test_out_of_order_entry_is_allowed_when_final_position_order_is_valid() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(
        workspace,
        _observed_game(definition, match_position=2, game_timecode=None),
    )
    workspace = _set_game(
        workspace,
        _observed_game(
            definition,
            match_position=1,
            game_timecode=MediaTimecodeV1(
                start_offset_ms=20_000,
                end_offset_ms=30_000,
            ),
        ),
    )
    assert workspace.revision == 2


def test_match_definition_replacement_corrects_descriptive_values_and_snapshots() -> None:
    definition = _capture()
    workspace = create_match_workspace_v1(definition)
    corrected_source = replace(
        definition.source,
        source_title="Corrected source title",
        source_channel_name="Corrected Channel",
    )
    corrected_participants = list(definition.participants)
    corrected_participants[0] = replace(
        corrected_participants[0],
        player_label="Corrected Alice",
        platform_player_id="corrected-platform-a",
        statistics_snapshot=None,
    )
    corrected_definition = replace(
        definition,
        title="Corrected Match title",
        game_platform="Corrected EuroSkat label",
        external_match_id="corrected-external-id",
        played_at="2026-08-09T20:00:00+02:00",
        source=corrected_source,
        participants=tuple(corrected_participants),
    )
    result = replace_match_workspace_definition_v1(
        workspace,
        corrected_definition,
        expected_revision=0,
    )
    assert result.status == "applied"
    assert result.workspace.revision == 1
    assert result.workspace.match_definition == corrected_definition
    assert result.workspace.slots == workspace.slots
    equal = replace_match_workspace_definition_v1(
        result.workspace,
        corrected_definition,
        expected_revision=1,
    )
    assert equal.status == "unchanged" and equal.workspace is result.workspace


@pytest.mark.parametrize("change", ("match_id", "participants", "perspective"))
def test_match_definition_replacement_preserves_structural_identity(change: str) -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    if change == "match_id":
        candidate = replace(definition, match_id="different-match")
    elif change == "perspective":
        candidate = replace(definition, perspective_player_id="player-b")
    else:
        participants = list(definition.participants)
        participants[0] = replace(participants[0], player_id="different-player")
        candidate = replace(
            definition,
            participants=tuple(participants),
            perspective_player_id="different-player",
        )
    with pytest.raises(ValueError, match="preserve"):
        replace_match_workspace_definition_v1(
            workspace,
            candidate,
            expected_revision=0,
        )


def test_definition_replacement_revalidates_retained_game_and_passed_timecodes() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(workspace, _observed_game(definition, match_position=1))
    workspace = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=2,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=120_000,
            end_offset_ms=130_000,
        ),
        expected_revision=workspace.revision,
    ).workspace
    narrowed_source = replace(
        definition.source,
        match_timecode=MediaTimecodeV1(
            start_offset_ms=125_000,
            end_offset_ms=7_654_321,
        ),
    )
    with pytest.raises(ValueError, match="within"):
        replace_match_workspace_definition_v1(
            workspace,
            replace(definition, source=narrowed_source),
            expected_revision=workspace.revision,
        )


def test_progress_counts_occupancy_evidence_commentary_and_next_empty() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    initial = build_match_workspace_progress_v1(workspace)
    assert initial.to_dict() == {
        "match_workspace_progress_version": 1,
        "status": "empty",
        "revision": 0,
        "total_slot_count": 36,
        "empty_slot_count": 36,
        "observed_game_count": 0,
        "passed_deal_count": 0,
        "occupied_slot_count": 0,
        "complete_play_trace_count": 0,
        "perspective_sample_ready_game_count": 0,
        "all_player_sample_ready_game_count": 0,
        "discard_review_ready_game_count": 0,
        "complete_initial_deal_ready_game_count": 0,
        "commentary_count": 0,
        "response_link_count": 0,
        "next_empty_position": 1,
    }
    workspace = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    workspace = _set_game(workspace, _annotated_observed_game(definition))
    progress = build_match_workspace_progress_v1(workspace)
    assert progress.status == "in_progress"
    assert progress.revision == 2
    assert (progress.empty_slot_count, progress.observed_game_count) == (34, 1)
    assert progress.passed_deal_count == 1 and progress.occupied_slot_count == 2
    assert progress.commentary_count == progress.response_link_count == 1
    assert progress.complete_play_trace_count == 0
    assert progress.next_empty_position == 2


def test_complete_evidence_sets_every_progress_capability_count() -> None:
    definition = _definition()
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition),
    )
    progress = build_match_workspace_progress_v1(workspace)
    assert (
        progress.complete_play_trace_count,
        progress.perspective_sample_ready_game_count,
        progress.all_player_sample_ready_game_count,
        progress.discard_review_ready_game_count,
        progress.complete_initial_deal_ready_game_count,
    ) == (1, 1, 1, 1, 1)


def test_complete_status_means_only_all_slots_are_classified() -> None:
    workspace = create_match_workspace_v1(_definition())
    for position in range(1, 37):
        workspace = mark_match_workspace_passed_deal_v1(
            workspace,
            match_position=position,
            game_timecode=None,
            expected_revision=workspace.revision,
        ).workspace
    progress = build_match_workspace_progress_v1(workspace)
    assert progress.status == "complete"
    assert progress.passed_deal_count == progress.occupied_slot_count == 36
    assert progress.empty_slot_count == 0 and progress.next_empty_position is None
    assert progress.complete_play_trace_count == 0
    assert progress.complete_initial_deal_ready_game_count == 0


def test_mixed_observed_and_passed_slots_complete_structural_progress() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    for position in range(1, 37):
        if position % 2:
            workspace = _set_game(
                workspace,
                _observed_game(
                    definition,
                    match_position=position,
                    game_timecode=None,
                ),
            )
        else:
            workspace = mark_match_workspace_passed_deal_v1(
                workspace,
                match_position=position,
                game_timecode=None,
                expected_revision=workspace.revision,
            ).workspace
    progress = build_match_workspace_progress_v1(workspace)
    assert progress.status == "complete"
    assert progress.observed_game_count == progress.passed_deal_count == 18
    assert progress.complete_play_trace_count == 0


def test_36_partial_observed_games_complete_occupancy_without_complete_evidence() -> None:
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    for position in range(1, 37):
        workspace = _set_game(
            workspace,
            _observed_game(definition, match_position=position, game_timecode=None),
        )
    progress = build_match_workspace_progress_v1(workspace)
    assert progress.status == "complete"
    assert progress.observed_game_count == 36
    assert progress.complete_play_trace_count == 0


def test_workspace_validator_rejects_forged_slots_positions_and_versions() -> None:
    workspace = create_match_workspace_v1(_definition())
    object.__setattr__(workspace.slots[0], "match_workspace_slot_version", 2)
    with pytest.raises(ValueError, match="slot_version"):
        validate_match_workspace_v1(workspace)

    workspace = create_match_workspace_v1(_definition())
    object.__setattr__(workspace, "revision", True)
    with pytest.raises(ValueError, match="revision"):
        validate_match_workspace_v1(workspace)

    workspace = create_match_workspace_v1(_definition())
    object.__setattr__(workspace, "revision", 1)
    object.__setattr__(workspace.slots[0], "slot_kind", "passed_deal")
    object.__setattr__(
        workspace.slots[0],
        "passed_deal",
        MatchPassedDealV1(game_timecode=None),
    )
    object.__setattr__(workspace.slots[1], "slot_kind", "passed_deal")
    object.__setattr__(
        workspace.slots[1],
        "passed_deal",
        MatchPassedDealV1(game_timecode=None),
    )
    with pytest.raises(ValueError, match="occupied"):
        validate_match_workspace_v1(workspace)


def test_workspace_private_information_is_retained_without_synthetic_hidden_facts() -> None:
    definition = _definition()
    game = _complete_observed_game(definition)
    workspace = _set_game(create_match_workspace_v1(definition), game)
    serialized = json.dumps(workspace.to_dict())
    assert definition.source.source_url in serialized
    assert game.perspective_initial_hand[0] in serialized
    assert game.original_skat[0] in serialized
    assert game.discarded_cards[0] in serialized
    forbidden = {
        "search_worlds",
        "simulation_ownership",
        "analysis_result",
        "field_provenance",
        "synthetic_hidden_cards",
        "historical_game_input",
        "fixed_three_player_historical_list_input",
    }
    assert all(f'"{field}"' not in serialized for field in forbidden)


def test_public_api_cli_schema_output_and_package_boundaries_remain_unchanged() -> None:
    new_names = {
        "MatchWorkspaceV1",
        "create_match_workspace_v1",
        "save_match_workspace_file_v1",
    }
    public_exports = (
        set(skat_ai.__all__)
        | set(api_v1.__all__)
        | set(session_api.__all__)
        | set(session_files_api.__all__)
    )
    assert new_names.isdisjoint(public_exports)
    assert tuple(workflow.value for workflow in WorkflowV1) == (
        "position_analysis",
        "historical_game",
        "training_dataset",
        "training_dataset_preparation",
        "opponent_statistics",
        "fixed_three_player_historical_list",
        "fixed_three_player_historical_list_comparison",
    )
    assert "match-workspace" not in build_argument_parser().format_help()
    assert "match-workspace" not in build_session_argument_parser().format_help()
    assert skat_ai.__version__ == "0.16.0"
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 69
    assert len(
        tuple(
            (PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob(
                "*.schema.json"
            )
        )
    ) == 69
    assert len(SCENARIOS) == 94
    assert all("match_workspace" not in scenario.name for scenario in SCENARIOS)
