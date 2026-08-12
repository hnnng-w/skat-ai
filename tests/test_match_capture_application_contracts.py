import json
from dataclasses import FrozenInstanceError, fields, replace

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

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_capture_application import (
    append_match_capture_plays_v1,
    mark_match_capture_passed_deal_v1,
    set_match_capture_declaration_v1,
    start_match_capture_game_v1,
)
from skat_ai.match_capture_application_contracts import (
    MATCH_CAPTURE_ANNOTATION_ID_POLICY,
    MATCH_CAPTURE_APPLICATION_OPERATIONS,
    MATCH_CAPTURE_APPLICATION_POLICY,
    MATCH_CAPTURE_APPLICATION_RESULT_VERSION,
    MATCH_CAPTURE_APPLICATION_STATUSES,
    MATCH_CAPTURE_APPLICATION_VERSION,
    MATCH_CAPTURE_CARD_SELECTION_POLICY,
    MATCH_CAPTURE_CARD_SELECTION_SCOPES,
    MATCH_CAPTURE_GAME_ID_POLICY,
    MATCH_CAPTURE_GAME_STATES,
    MATCH_CAPTURE_INFORMATION_POLICY,
    MATCH_CAPTURE_POSITION_VIEW_VERSION,
    MATCH_CAPTURE_RECORD_PLAY_BLOCKERS,
    MATCH_CAPTURE_TRUNCATION_POLICY,
    MatchCaptureApplicationResultV1,
    MatchCaptureCardEntryV1,
    MatchCapturePositionViewV1,
)
from skat_ai.match_capture_position_view import build_match_capture_position_view_v1
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.match_workspace_contracts import create_match_workspace_v1


def _entry(card: str, start: int | None = None) -> MatchCaptureCardEntryV1:
    return MatchCaptureCardEntryV1(
        card=card,
        decision_timecode=(
            None if start is None else MediaTimecodeV1(start_offset_ms=start, end_offset_ms=None)
        ),
    )


def _started_workspace(*, position: int = 1):
    workspace = create_match_workspace_v1(_definition())
    return start_match_capture_game_v1(
        workspace,
        match_position=position,
        expected_revision=workspace.revision,
    ).workspace_change.workspace


def _ready_workspace(*, position: int = 1, declarer: str = "player-b"):
    workspace = _started_workspace(position=position)
    return set_match_capture_declaration_v1(
        workspace,
        match_position=position,
        declarer_player_id=declarer,
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        expected_revision=workspace.revision,
    ).workspace_change.workspace


def test_versions_tuples_policies_and_contract_fields_are_exact() -> None:
    assert (
        MATCH_CAPTURE_APPLICATION_VERSION,
        MATCH_CAPTURE_POSITION_VIEW_VERSION,
        MATCH_CAPTURE_APPLICATION_RESULT_VERSION,
    ) == (1, 1, 1)
    assert MATCH_CAPTURE_APPLICATION_OPERATIONS == (
        "start_game",
        "set_game_timecode",
        "set_perspective_hand",
        "set_declaration",
        "set_original_skat",
        "set_discarded_cards",
        "append_plays",
        "truncate_plays",
        "set_commentary",
        "remove_commentary",
        "set_response_link",
        "remove_response_link",
        "mark_passed_deal",
        "clear_position",
    )
    assert MATCH_CAPTURE_APPLICATION_STATUSES == (
        "applied",
        "unchanged",
        "revision_conflict",
    )
    assert MATCH_CAPTURE_GAME_STATES == (
        "empty",
        "setup",
        "ready_for_play",
        "play_in_progress",
        "play_complete",
        "passed_deal",
    )
    assert MATCH_CAPTURE_CARD_SELECTION_SCOPES == (
        "unavailable",
        "exact_legal_cards",
        "bounded_observation_candidates",
    )
    assert MATCH_CAPTURE_RECORD_PLAY_BLOCKERS == (
        "empty_slot",
        "passed_deal",
        "missing_declaration",
        "complete_play_trace",
    )
    assert MATCH_CAPTURE_APPLICATION_POLICY == ("transport_free_workspace_observed_game_updates")
    assert MATCH_CAPTURE_GAME_ID_POLICY == "match_id_plus_zero_padded_position"
    assert MATCH_CAPTURE_ANNOTATION_ID_POLICY == ("match_id_position_workspace_revision")
    assert MATCH_CAPTURE_CARD_SELECTION_POLICY == (
        "exclude_only_observed_or_proven_unavailable_cards"
    )
    assert MATCH_CAPTURE_TRUNCATION_POLICY == "remove_suffix_and_invalid_annotations"
    assert MATCH_CAPTURE_INFORMATION_POLICY == "no_hidden_completion"
    assert [field.name for field in fields(MatchCaptureCardEntryV1)] == [
        "card",
        "decision_timecode",
    ]
    assert [field.name for field in fields(MatchCapturePositionViewV1)] == [
        "match_capture_position_view_version",
        "match_id",
        "workspace_revision",
        "match_position",
        "round_number",
        "slot_kind",
        "game_state",
        "dealer_player_id",
        "forehand_player_id",
        "middlehand_player_id",
        "rearhand_player_id",
        "perspective_player_id",
        "game_id",
        "declarer_player_id",
        "play_count",
        "completed_trick_count",
        "current_trick_play_count",
        "current_trick_player_ids",
        "current_trick_cards",
        "next_player_id",
        "player_play_counts",
        "played_cards",
        "card_selection_scope",
        "selectable_cards",
        "can_record_play",
        "record_play_blockers",
        "can_truncate_plays",
        "evidence_summary",
        "workspace_progress",
    ]
    assert [field.name for field in fields(MatchCaptureApplicationResultV1)] == [
        "match_capture_application_result_version",
        "operation",
        "status",
        "workspace_change",
        "position_view",
        "removed_commentary_ids",
        "removed_response_link_ids",
        "affected_commentary_id",
        "affected_response_link_id",
    ]


def test_card_entry_is_frozen_slotted_keyword_only_validated_and_defensive() -> None:
    timecode = MediaTimecodeV1(start_offset_ms=12_345, end_offset_ms=12_500)
    entry = MatchCaptureCardEntryV1(card="CA", decision_timecode=timecode)
    assert entry.decision_timecode == timecode
    assert entry.decision_timecode is not timecode
    assert entry.to_dict() == {
        "card": "CA",
        "decision_timecode": timecode.to_dict(),
    }
    first = entry.to_dict()
    first["decision_timecode"]["start_offset_ms"] = 0
    assert entry.to_dict()["decision_timecode"]["start_offset_ms"] == 12_345
    assert not hasattr(entry, "__dict__")
    with pytest.raises(FrozenInstanceError):
        entry.card = "C10"
    with pytest.raises(TypeError):
        MatchCaptureCardEntryV1("CA", None)
    for card in ("", "XX", None):
        with pytest.raises(ValueError, match="valid Skat Card"):
            MatchCaptureCardEntryV1(card=card, decision_timecode=None)
    with pytest.raises(ValueError, match="MediaTimecodeV1"):
        MatchCaptureCardEntryV1(card="CA", decision_timecode="00:01")


def test_position_view_and_result_are_immutable_builder_values_with_fresh_json() -> None:
    workspace = create_match_workspace_v1(_definition())
    result = start_match_capture_game_v1(
        workspace,
        match_position=1,
        expected_revision=0,
    )
    view = result.position_view
    assert not hasattr(view, "__dict__")
    assert not hasattr(result, "__dict__")
    with pytest.raises(TypeError, match="focused builder"):
        MatchCapturePositionViewV1()
    with pytest.raises(FrozenInstanceError):
        view.game_state = "empty"
    with pytest.raises(FrozenInstanceError):
        result.status = "unchanged"
    first = result.to_dict()
    first["position_view"]["record_play_blockers"].append("hidden_hand")
    first["workspace_change"]["workspace"]["slots"][0]["slot_kind"] = "empty"
    assert result.to_dict()["position_view"]["record_play_blockers"] == ["missing_declaration"]
    assert (
        result.to_dict()["workspace_change"]["workspace"]["slots"][0]["slot_kind"]
        == "observed_game"
    )
    json.dumps(result.to_dict())
    with pytest.raises(ValueError, match="status must equal"):
        replace(result, status="unchanged")

    passed = mark_match_capture_passed_deal_v1(
        workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    )
    with pytest.raises(ValueError, match="exactly describe"):
        replace(result, position_view=passed.position_view)


def test_position_view_builder_contract_rejects_forged_impossible_state_combinations() -> None:
    empty = build_match_capture_position_view_v1(
        create_match_workspace_v1(_definition()),
        match_position=1,
    )
    empty_values = {
        field.name: getattr(empty, field.name)
        for field in fields(MatchCapturePositionViewV1)
        if field.name != "match_capture_position_view_version"
    }
    with pytest.raises(ValueError, match="Non-Game Views cannot contain Play"):
        MatchCapturePositionViewV1._from_validated(
            **{
                **empty_values,
                "play_count": 3,
                "completed_trick_count": 1,
                "player_play_counts": (
                    ("player-b", 1),
                    ("player-c", 1),
                    ("player-a", 1),
                ),
                "played_cards": ("CA", "S7", "H7"),
                "can_truncate_plays": True,
            }
        )

    partial = append_match_capture_plays_v1(
        _ready_workspace(),
        match_position=1,
        entries=(_entry("CA"),),
        expected_revision=2,
    ).position_view
    partial_values = {
        field.name: getattr(partial, field.name)
        for field in fields(MatchCapturePositionViewV1)
        if field.name != "match_capture_position_view_version"
    }
    with pytest.raises(ValueError, match="setup Game cannot contain Plays"):
        MatchCapturePositionViewV1._from_validated(
            **{
                **partial_values,
                "game_state": "setup",
                "declarer_player_id": None,
                "next_player_id": None,
                "card_selection_scope": "unavailable",
                "selectable_cards": (),
                "can_record_play": False,
                "record_play_blockers": ("missing_declaration",),
            }
        )


def test_empty_passed_setup_and_ready_views_have_exact_states_blockers_and_progress() -> None:
    workspace = create_match_workspace_v1(_definition())
    empty = build_match_capture_position_view_v1(workspace, match_position=1)
    assert (
        empty.slot_kind,
        empty.game_state,
        empty.next_player_id,
        empty.card_selection_scope,
        empty.selectable_cards,
        empty.record_play_blockers,
        empty.can_record_play,
        empty.can_truncate_plays,
        empty.evidence_summary,
    ) == (
        "empty",
        "empty",
        None,
        "unavailable",
        (),
        ("empty_slot",),
        False,
        False,
        None,
    )
    assert empty.workspace_progress.status == "empty"

    passed_result = mark_match_capture_passed_deal_v1(
        workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    )
    passed = passed_result.position_view
    assert passed.game_state == passed.slot_kind == "passed_deal"
    assert passed.record_play_blockers == ("passed_deal",)
    assert passed.game_id is passed.evidence_summary is None
    assert passed.workspace_progress.passed_deal_count == 1

    setup_workspace = _started_workspace()
    setup = build_match_capture_position_view_v1(setup_workspace, match_position=1)
    assert setup.game_state == "setup"
    assert setup.record_play_blockers == ("missing_declaration",)
    assert setup.game_id == "match-160-game-01"
    assert setup.evidence_summary.play_count == 0
    assert setup.workspace_progress.observed_game_count == 1

    ready_workspace = set_match_capture_declaration_v1(
        setup_workspace,
        match_position=1,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        expected_revision=setup_workspace.revision,
    ).workspace_change.workspace
    ready = build_match_capture_position_view_v1(ready_workspace, match_position=1)
    assert ready.game_state == "ready_for_play"
    assert ready.next_player_id == "player-b"
    assert ready.record_play_blockers == ()
    assert ready.can_record_play
    assert ready.card_selection_scope == "bounded_observation_candidates"


def test_position_view_rotation_current_trick_counts_and_winner_led_next_player() -> None:
    workspace = _ready_workspace()
    result = append_match_capture_plays_v1(
        workspace,
        match_position=1,
        entries=(_entry("CA"), _entry("S7")),
        expected_revision=workspace.revision,
    )
    view = result.position_view
    assert (
        view.dealer_player_id,
        view.forehand_player_id,
        view.middlehand_player_id,
        view.rearhand_player_id,
    ) == ("player-a", "player-b", "player-c", "player-a")
    assert view.game_state == "play_in_progress"
    assert view.current_trick_player_ids == ("player-b", "player-c")
    assert view.current_trick_cards == ("CA", "S7")
    assert view.next_player_id == "player-a"
    assert view.player_play_counts == (
        ("player-b", 1),
        ("player-c", 1),
        ("player-a", 0),
    )
    assert view.played_cards == ("CA", "S7")
    assert view.can_truncate_plays

    completed = append_match_capture_plays_v1(
        result.workspace_change.workspace,
        match_position=1,
        entries=(_entry("C7"),),
        expected_revision=result.workspace_change.current_revision,
    ).position_view
    assert completed.completed_trick_count == 1
    assert completed.current_trick_play_count == 0
    assert completed.current_trick_cards == ()
    assert completed.next_player_id == "player-b"


def test_29_and_30_play_views_distinguish_in_progress_from_complete() -> None:
    definition = _definition()
    data = build_historical_input(game_type="grand", hand_game=False)
    partial_game = _observed_game(
        definition,
        match_position=3,
        game_id="partial-29",
        perspective_initial_hand=None,
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=None,
        discarded_cards=None,
        plays=observed_plays_from_historical(data, count=29),
    )
    partial_workspace = _set_game(create_match_workspace_v1(definition), partial_game)
    partial = build_match_capture_position_view_v1(
        partial_workspace,
        match_position=3,
    )
    assert partial.game_state == "play_in_progress"
    assert partial.play_count == 29
    assert partial.current_trick_play_count == 2
    assert partial.can_record_play
    assert partial.next_player_id is not None

    complete_workspace = _set_game(
        create_match_workspace_v1(definition),
        _complete_observed_game(definition, match_position=3),
    )
    complete = build_match_capture_position_view_v1(
        complete_workspace,
        match_position=3,
    )
    assert complete.game_state == "play_complete"
    assert complete.play_count == 30
    assert complete.completed_trick_count == 10
    assert complete.next_player_id is None
    assert complete.record_play_blockers == ("complete_play_trace",)
    assert complete.card_selection_scope == "unavailable"
    assert complete.selectable_cards == ()
    assert complete.evidence_summary.complete_play_trace


@pytest.mark.parametrize(
    ("declarer_player_id", "declaration", "original_skat", "discarded_cards"),
    (
        (
            "player-b",
            GameDeclaration(game_type="grand", bid_value=24),
            None,
            None,
        ),
        (
            "player-a",
            GameDeclaration(game_type="grand", hand_game=True, bid_value=48),
            None,
            (),
        ),
        (
            "player-a",
            GameDeclaration(game_type="grand", bid_value=24),
            ("H8", "D8"),
            ("H7", "D7"),
        ),
    ),
)
def test_exact_selection_supports_defender_hand_and_non_hand_perspective(
    declarer_player_id: str,
    declaration: GameDeclaration,
    original_skat: tuple[str, ...] | None,
    discarded_cards: tuple[str, ...] | None,
) -> None:
    definition = _definition()
    initial_hand = (
        "C7",
        "SA",
        "S10",
        "SK",
        "SQ",
        "SJ",
        "S9",
        "S8",
        "H7",
        "D7",
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"exact-{declarer_player_id}-{declaration.hand_game}",
        perspective_initial_hand=initial_hand,
        declarer_player_id=declarer_player_id,
        declaration=declaration,
        original_skat=original_skat,
        discarded_cards=discarded_cards,
        plays=(),
    )
    view = build_match_capture_position_view_v1(
        _set_game(create_match_workspace_v1(definition), game),
        match_position=3,
    )
    assert view.next_player_id == "player-a"
    assert view.card_selection_scope == "exact_legal_cards"
    expected = set(initial_hand)
    if original_skat is not None:
        expected.update(original_skat)
    if discarded_cards is not None:
        expected.difference_update(discarded_cards)
    assert view.selectable_cards == tuple(card for card in get_full_deck() if card in expected)


def test_exact_selection_applies_bedienpflicht_only_to_known_current_hand() -> None:
    definition = _definition()
    game = _observed_game(
        definition,
        match_position=1,
        game_id="exact-follow",
        perspective_initial_hand=(
            "C7",
            "SA",
            "S10",
            "SK",
            "SQ",
            "SJ",
            "S9",
            "S8",
            "H7",
            "D7",
        ),
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        plays=(),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    result = append_match_capture_plays_v1(
        workspace,
        match_position=1,
        entries=(_entry("CA"), _entry("H8")),
        expected_revision=workspace.revision,
    )
    assert result.position_view.next_player_id == "player-a"
    assert result.position_view.card_selection_scope == "exact_legal_cards"
    assert result.position_view.selectable_cards == ("C7",)


def test_exact_selection_removes_perspective_cards_already_played() -> None:
    definition = _definition()
    hand = (
        "CA",
        "C10",
        "CK",
        "CQ",
        "CJ",
        "C9",
        "C8",
        "C7",
        "SA",
        "S10",
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id="exact-after-trick",
        perspective_initial_hand=hand,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    view = append_match_capture_plays_v1(
        workspace,
        match_position=3,
        entries=(_entry("CA"), _entry("S7"), _entry("H7")),
        expected_revision=workspace.revision,
    ).position_view
    assert view.next_player_id == "player-a"
    assert view.card_selection_scope == "exact_legal_cards"
    assert "CA" not in view.selectable_cards
    assert view.selectable_cards == tuple(card for card in get_full_deck() if card in hand[1:])


def test_bounded_candidates_exclude_only_proven_unavailable_cards_without_bedienpflicht() -> None:
    definition = _definition()
    perspective_hand = (
        "C7",
        "SA",
        "S10",
        "SK",
        "SQ",
        "SJ",
        "S9",
        "S8",
        "H7",
        "D7",
    )
    game = _observed_game(
        definition,
        match_position=1,
        game_id="bounded-evidence",
        perspective_initial_hand=perspective_hand,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        original_skat=("H8", "D8"),
        discarded_cards=("H9", "D9"),
        plays=(),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    initial = build_match_capture_position_view_v1(workspace, match_position=1)
    assert initial.next_player_id == "player-b"
    assert initial.card_selection_scope == "bounded_observation_candidates"
    assert "H8" in initial.selectable_cards
    for unavailable in (*perspective_hand, "H9", "D9"):
        assert unavailable not in initial.selectable_cards

    after_lead = append_match_capture_plays_v1(
        workspace,
        match_position=1,
        entries=(_entry("CA"),),
        expected_revision=workspace.revision,
    ).position_view
    assert after_lead.next_player_id == "player-c"
    assert after_lead.card_selection_scope == "bounded_observation_candidates"
    assert "CA" not in after_lead.selectable_cards
    assert "C10" in after_lead.selectable_cards
    assert "H10" in after_lead.selectable_cards
    assert "H8" not in after_lead.selectable_cards
    assert "D8" not in after_lead.selectable_cards
    assert after_lead.selectable_cards == tuple(
        card for card in get_full_deck() if card in set(after_lead.selectable_cards)
    )


def test_hand_original_skat_is_proven_unavailable_to_every_player() -> None:
    definition = _definition()
    game = _observed_game(
        definition,
        match_position=1,
        game_id="bounded-hand-skat",
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", hand_game=True, bid_value=48),
        original_skat=("H8", "D8"),
        discarded_cards=(),
    )
    view = build_match_capture_position_view_v1(
        _set_game(create_match_workspace_v1(definition), game),
        match_position=1,
    )
    assert view.card_selection_scope == "bounded_observation_candidates"
    assert "H8" not in view.selectable_cards
    assert "D8" not in view.selectable_cards
    assert {
        "opponent_hands",
        "hidden_ownership",
        "bedienpflicht_inferred",
        "skat_inferred",
        "discarded_cards_inferred",
        "analysis_result",
    }.isdisjoint(view.to_dict())
