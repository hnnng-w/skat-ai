import copy
from dataclasses import replace

import pytest
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_defender_open_play_continuation import (
    build_event_record as build_defender_open_play_continuation,
)
from test_historical_game import build_historical_input
from test_session_decision_checkpoint import _checkpoint, _ready_live_state
from test_session_historical_export import _early_promoted_normal_session
from test_session_position_export import (
    _live_ouvert_defender_state,
    _options,
    _set_opponent_ouvert_hand,
)
from test_session_transitions import (
    _apply,
    _complete_retrospective_session,
    _players,
)

import skat_ai.session_history as history_module
from skat_ai.deck import get_full_deck
from skat_ai.errors import SkatAIInvariantError
from skat_ai.game_declaration import GameDeclaration
from skat_ai.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionDiscardCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionGameMetadataCommandV1,
    SetSessionPublicHandCommandV1,
)
from skat_ai.session_decision_checkpoint import build_session_decision_checkpoint_v1
from skat_ai.session_historical_export import export_session_historical_game_request_v1
from skat_ai.session_history import (
    build_session_state_from_accepted_prefix_v1,
    classify_session_decision_checkpoint_v1,
    correct_session_command_v1,
    rewind_session_state_v1,
)
from skat_ai.session_history_contracts import SessionCommandCorrectionV1
from skat_ai.session_position_export import export_session_position_analysis_request_v1
from skat_ai.session_transitions import (
    create_session_state_v1,
    replay_session_state_v1,
)


def _record_revision(state, kind: str, occurrence: int = 1) -> int:
    records = [record for record in state.command_log if record.command.kind == kind]
    return records[occurrence - 1].revision


def _correction(state, target_revision: int, replacement_command):
    return correct_session_command_v1(
        state,
        SessionCommandCorrectionV1(
            expected_revision=state.revision,
            target_revision=target_revision,
            replacement_command=replacement_command,
        ),
    )


def _promoted_private_suffix_state(*, second_opponent_card: bool = False):
    state = create_session_state_v1(
        session_id="session-promotion-correction",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    state = _apply(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        ),
    )
    state = _apply(
        state,
        PromoteSessionToRetrospectiveCommandV1(expected_revision=1),
    )
    state = _apply(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=2,
            destination="player_hand",
            player_id="player-b",
            card="D7",
        ),
    )
    if second_opponent_card:
        state = _apply(
            state,
            RecordSessionDealtCardCommandV1(
                expected_revision=3,
                destination="player_hand",
                player_id="player-b",
                card="D8",
            ),
        )
    return state


def _public_hand_with_plays_state():
    state = _set_opponent_ouvert_hand(_live_ouvert_defender_state())
    state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    return _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-b",
            card="SK",
        ),
    )


def test_undo_every_target_returns_exact_prefix_suffix_and_valid_state() -> None:
    state = create_session_state_v1(
        session_id="session-undo-targets",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    state = _apply(
        state,
        SetSessionGameMetadataCommandV1(expected_revision=0, game_id="undo-game"),
    )
    for card in ("CA", "D7", "H8"):
        state = _apply(
            state,
            RecordSessionDealtCardCommandV1(
                expected_revision=state.revision,
                destination="player_hand",
                player_id="player-a",
                card=card,
            ),
        )
    source_dict = state.to_dict()

    for target_revision in range(state.revision + 1):
        result = rewind_session_state_v1(
            state,
            expected_revision=state.revision,
            target_revision=target_revision,
        )
        expected_status = "unchanged" if target_revision == state.revision else "applied"
        assert result.status == expected_status
        assert result.state.command_log == state.command_log[:target_revision]
        assert result.removed_records == (
            () if expected_status == "unchanged" else state.command_log[target_revision:]
        )
        assert result.current_revision == target_revision
        assert replay_session_state_v1(result.state) is not None
    assert state.to_dict() == source_dict


def test_undo_unchanged_rejected_and_conflict_preserve_exact_source() -> None:
    state = create_session_state_v1(
        session_id="session-undo-normal-results",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    unchanged = rewind_session_state_v1(state, expected_revision=0, target_revision=0)
    rejected = rewind_session_state_v1(state, expected_revision=0, target_revision=1)
    stale = rewind_session_state_v1(state, expected_revision=1, target_revision=1)
    future = rewind_session_state_v1(state, expected_revision=2, target_revision=0)

    assert unchanged.status == "unchanged" and unchanged.state is state
    assert rejected.status == "rejected" and rejected.state is state
    assert rejected.diagnostics[0].path == "/target_revision"
    assert stale.status == future.status == "revision_conflict"
    assert stale.state is future.state is state
    assert stale.target_revision == 1
    assert stale.diagnostics[0].path == "/expected_revision"


@pytest.mark.parametrize("value", (-1, True, 1.0, "0"))
def test_undo_rejects_invalid_scalar_targets_before_operation(value: object) -> None:
    state = create_session_state_v1(
        session_id="session-undo-invalid",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    with pytest.raises(ValueError, match="target_revision"):
        rewind_session_state_v1(state, expected_revision=1, target_revision=value)


def test_prefix_builder_reconstructs_without_normal_command_application(monkeypatch) -> None:
    source = _complete_retrospective_session(build_historical_input())

    def forbidden_apply(*_args, **_kwargs):
        raise AssertionError("Prefix reconstruction called normal State application.")

    import skat_ai.session_transitions as transitions

    monkeypatch.setattr(transitions, "apply_session_command_v1", forbidden_apply)
    replay_session_state_v1(source)
    prefix = build_session_state_from_accepted_prefix_v1(
        source,
        target_revision=source.revision - 1,
    )
    assert prefix.phase == "play"
    assert prefix.command_log == source.command_log[:-1]
    assert replay_session_state_v1(prefix) is not None


def test_undo_rederives_every_phase_and_removes_derived_facts() -> None:
    data = build_historical_input()
    source = _complete_retrospective_session(data)
    end_result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=source.revision - 1,
    )
    assert end_result.state.phase == "play"
    assert replay_session_state_v1(end_result.state).game_end_reason is None
    assert end_result.state.validation.historical_export.status == "unavailable"

    first_discard_revision = _record_revision(source, "record_discard", 1)
    discard_result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=first_discard_revision,
    )
    discard_projection = replay_session_state_v1(discard_result.state)
    assert discard_result.state.phase == "skat_and_discard"
    assert len(discard_projection.discarded_cards) == 1
    assert discard_projection.plays == ()

    declarer_revision = _record_revision(source, "set_declarer")
    declaration_result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=declarer_revision,
    )
    declaration_projection = replay_session_state_v1(declaration_result.state)
    assert declaration_result.state.phase == "declaration"
    assert declaration_projection.declaration is None
    assert declaration_projection.declarer_player_id == data["declarer_player_id"]

    last_deal_revision = _record_revision(source, "record_dealt_card", 32)
    deal_result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=last_deal_revision - 1,
    )
    assert deal_result.state.phase == "deal"

    setup_result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=1,
    )
    setup_projection = replay_session_state_v1(setup_result.state)
    assert setup_result.state.phase == "setup"
    assert setup_projection.game_id == data["game_id"]
    assert setup_projection.initial_known_hands == ()

    empty_result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=0,
    )
    assert replay_session_state_v1(empty_result.state).game_id is None


def test_undo_removes_continuation_public_hand_plays_and_tricks() -> None:
    data = build_defender_open_play_continuation(after_play_count=12)
    source = _complete_retrospective_session(data)
    event_revision = _record_revision(source, "set_game_event")
    event_result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=event_revision - 1,
    )
    event_projection = replay_session_state_v1(event_result.state)
    assert event_projection.continuation_event is None
    assert event_projection.exact_public_hands == ()
    assert event_projection.played_card_count == 12
    assert len(event_projection.completed_tricks) == 4

    public_source = _public_hand_with_plays_state()
    public_revision = _record_revision(public_source, "set_public_hand")
    public_result = rewind_session_state_v1(
        public_source,
        expected_revision=public_source.revision,
        target_revision=public_revision - 1,
    )
    public_projection = replay_session_state_v1(public_result.state)
    assert public_projection.exact_public_hands == ()
    assert public_projection.plays == ()


def test_undoing_promotion_returns_to_live_without_changing_initial_identity() -> None:
    source = _early_promoted_normal_session(build_historical_input())
    promotion_revision = _record_revision(source, "promote_to_retrospective")
    result = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=promotion_revision - 1,
    )
    projection = replay_session_state_v1(result.state)
    assert result.state.initial_capture_mode == "live"
    assert result.state.capture_mode == projection.capture_mode == "live"
    assert result.state.local_player_id == source.local_player_id
    assert result.state.players == source.players
    assert all(
        player_id == source.local_player_id
        for player_id, _ in projection.initial_known_hands
    )
    assert result.state.validation.historical_export.status == "unavailable"


def test_correction_all_five_statuses_preserve_source_and_exact_reports() -> None:
    source = create_session_state_v1(
        session_id="session-correction-statuses",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    source = _apply(
        source,
        SetSessionGameMetadataCommandV1(expected_revision=0, game_id="original"),
    )
    source_dict = source.to_dict()
    applied = _correction(
        source,
        1,
        SetSessionGameMetadataCommandV1(expected_revision=0, game_id="replacement"),
    )
    unchanged = _correction(source, 1, source.command_log[0].command)
    rejected = _correction(
        source,
        1,
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="player-b",
            card="CA",
        ),
    )
    partial_source = _promoted_private_suffix_state()
    partial = _correction(
        partial_source,
        2,
        SetSessionGameMetadataCommandV1(
            expected_revision=1,
            game_id="without-promotion",
        ),
    )
    conflict = correct_session_command_v1(
        source,
        SessionCommandCorrectionV1(
            expected_revision=2,
            target_revision=1,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=0,
                game_id="future",
            ),
        ),
    )

    assert applied.status == "applied"
    assert applied.state.revision == source.revision
    assert applied.original_record == source.command_log[0]
    assert applied.state.command_log[0].command == applied.replacement_command
    assert unchanged.status == "unchanged" and unchanged.state is source
    assert rejected.status == "rejected" and rejected.state is source
    assert rejected.failed_original_revision == 1
    assert partial.status == "partial"
    assert partial.replayed_suffix_records == ()
    assert partial.discarded_suffix_records == partial_source.command_log[2:]
    assert partial.failed_original_revision == 3
    assert conflict.status == "revision_conflict" and conflict.state is source
    assert conflict.original_record is None
    assert source.to_dict() == source_dict
    assert replay_session_state_v1(partial.state) is not None


def test_complete_correction_replays_exact_suffix_order_and_payload() -> None:
    source = _complete_retrospective_session(build_historical_input())
    replacement = SetSessionGameMetadataCommandV1(
        expected_revision=0,
        game_id="corrected-game-id",
    )
    result = _correction(source, 1, replacement)
    assert result.status == "applied"
    assert result.current_revision == source.revision
    assert result.state.command_log[0].command == replacement
    assert result.replayed_suffix_records == source.command_log[1:]
    assert result.state.command_log[1:] == source.command_log[1:]
    assert result.discarded_suffix_records == ()
    assert result.failed_original_revision is None
    assert result.state.phase == "ended"
    assert result.state.validation.historical_export.status == "available"
    assert replay_session_state_v1(result.state) is not None


def test_partial_correction_stops_before_first_rejected_suffix(monkeypatch) -> None:
    source = _promoted_private_suffix_state(second_opponent_card=True)
    applied_kinds = []
    original_apply = history_module.apply_session_command_to_projection_v1

    def counted_apply(projection, command):
        applied_kinds.append(command.kind)
        return original_apply(projection, command)

    monkeypatch.setattr(
        history_module,
        "apply_session_command_to_projection_v1",
        counted_apply,
    )
    result = _correction(
        source,
        2,
        SetSessionGameMetadataCommandV1(
            expected_revision=1,
            game_id="without-promotion",
        ),
    )
    assert result.status == "partial"
    assert result.current_revision == 2
    assert result.discarded_suffix_records == source.command_log[2:]
    assert result.failed_original_revision == 3
    assert result.diagnostics[0].code == "information_policy_violation"
    assert applied_kinds == [
        "record_dealt_card",
        "set_game_metadata",
        "record_dealt_card",
    ]
    assert "D8" not in str(result.state.to_dict())


def test_correction_supports_every_current_target_command_kind() -> None:
    normal = _complete_retrospective_session(build_historical_input())
    results = {}

    results["set_game_metadata"] = _correction(
        normal,
        _record_revision(normal, "set_game_metadata"),
        SetSessionGameMetadataCommandV1(expected_revision=0, game_id="corrected"),
    )

    first_deal = _record_revision(normal, "record_dealt_card")
    results["record_dealt_card"] = _correction(
        normal,
        first_deal,
        RecordSessionDealtCardCommandV1(
            expected_revision=first_deal - 1,
            destination="player_hand",
            player_id="player-a",
            card="D7",
        ),
    )

    declarer_revision = _record_revision(normal, "set_declarer")
    results["set_declarer"] = _correction(
        normal,
        declarer_revision,
        SetSessionDeclarerCommandV1(
            expected_revision=declarer_revision - 1,
            declarer_player_id="player-a",
        ),
    )

    declaration_revision = _record_revision(normal, "set_declaration")
    original_declaration = normal.command_log[declaration_revision - 1].command.declaration
    results["set_declaration"] = _correction(
        normal,
        declaration_revision,
        SetSessionDeclarationCommandV1(
            expected_revision=declaration_revision - 1,
            declaration=replace(original_declaration, bid_value=48),
        ),
    )

    first_discard = _record_revision(normal, "record_discard")
    second_discard = normal.command_log[first_discard].command.card
    results["record_discard"] = _correction(
        normal,
        first_discard,
        RecordSessionDiscardCommandV1(
            expected_revision=first_discard - 1,
            card=second_discard,
        ),
    )

    first_play = _record_revision(normal, "record_play")
    results["record_play"] = _correction(
        normal,
        first_play,
        RecordSessionPlayCommandV1(
            expected_revision=first_play - 1,
            player_id="player-a",
            card="C10",
        ),
    )

    event_source = _complete_retrospective_session(
        build_defender_open_play_continuation(after_play_count=12)
    )
    event_revision = _record_revision(event_source, "set_game_event")
    event = event_source.command_log[event_revision - 1].command.to_dict()["event"]
    event["exposed_cards"].reverse()
    results["set_game_event"] = _correction(
        event_source,
        event_revision,
        SetSessionGameEventCommandV1(
            expected_revision=event_revision - 1,
            event=event,
        ),
    )

    end_source = _complete_retrospective_session(
        build_concession_prefix(completed_trick_count=4, current_trick_card_count=2)
    )
    end_revision = _record_revision(end_source, "set_game_end")
    replacement_end = build_defender_concession_prefix(
        completed_trick_count=4,
        current_trick_card_count=2,
    )
    results["set_game_end"] = _correction(
        end_source,
        end_revision,
        SetSessionGameEndCommandV1(
            expected_revision=end_revision - 1,
            game_end_reason="defender_concession",
            game_end=replacement_end["game_end"],
        ),
    )

    promotion_source = _promoted_private_suffix_state()
    promotion_revision = _record_revision(
        promotion_source,
        "promote_to_retrospective",
    )
    results["promote_to_retrospective"] = _correction(
        promotion_source,
        promotion_revision,
        SetSessionGameMetadataCommandV1(
            expected_revision=promotion_revision - 1,
            game_id="without-promotion",
        ),
    )

    public_source = _public_hand_with_plays_state()
    public_revision = _record_revision(public_source, "set_public_hand")
    results["set_public_hand"] = _correction(
        public_source,
        public_revision,
        SetSessionPublicHandCommandV1(
            expected_revision=public_revision - 1,
            source="declared_ouvert",
            player_id="player-b",
            cards=get_full_deck()[11:21],
        ),
    )

    assert set(results) == {
        "set_game_metadata",
        "record_dealt_card",
        "set_declarer",
        "set_declaration",
        "record_discard",
        "record_play",
        "set_game_event",
        "set_game_end",
        "promote_to_retrospective",
        "set_public_hand",
    }
    assert all(result.status in {"applied", "partial", "rejected"} for result in results.values())
    assert results["set_game_metadata"].status == "applied"
    assert results["set_declaration"].status == "applied"
    assert results["set_game_event"].status == "applied"
    assert results["set_game_end"].status == "applied"
    assert results["promote_to_retrospective"].status == "partial"
    assert results["set_public_hand"].status == "partial"
    assert all(replay_session_state_v1(result.state) is not None for result in results.values())


def test_live_correction_preserves_private_information_boundaries() -> None:
    live = create_session_state_v1(
        session_id="session-live-correction",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    live = _apply(
        live,
        SetSessionGameMetadataCommandV1(expected_revision=0, game_id="live"),
    )
    opponent_hand = _correction(
        live,
        1,
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="player-b",
            card="CA",
        ),
    )
    opponent_skat = _correction(
        live,
        1,
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="skat",
            player_id=None,
            card="CA",
        ),
    )
    assert opponent_hand.status == opponent_skat.status == "rejected"
    assert opponent_hand.diagnostics[0].code == "information_policy_violation"
    assert opponent_skat.diagnostics[0].code == "information_policy_violation"
    assert replay_session_state_v1(live).initial_known_hands == ()

    promotion_source = _promoted_private_suffix_state()
    removed_promotion = _correction(
        promotion_source,
        2,
        SetSessionGameMetadataCommandV1(
            expected_revision=1,
            game_id="still-live",
        ),
    )
    projection = replay_session_state_v1(removed_promotion.state)
    assert removed_promotion.status == "partial"
    assert projection.capture_mode == "live"
    assert projection.initial_hand_for("player-b") is None


def test_checkpoint_lineage_current_ancestor_future_and_diverged() -> None:
    checkpoint_state, _, checkpoint = _checkpoint()
    current = classify_session_decision_checkpoint_v1(checkpoint_state, checkpoint)
    played = _apply(
        checkpoint_state,
        RecordSessionPlayCommandV1(
            expected_revision=checkpoint_state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    ancestor = classify_session_decision_checkpoint_v1(played, checkpoint)
    rewound_current = rewind_session_state_v1(
        played,
        expected_revision=played.revision,
        target_revision=checkpoint.source_revision,
    ).state
    current_after_undo = classify_session_decision_checkpoint_v1(
        rewound_current,
        checkpoint,
    )
    future_state = rewind_session_state_v1(
        played,
        expected_revision=played.revision,
        target_revision=checkpoint.source_revision - 1,
    ).state
    future = classify_session_decision_checkpoint_v1(future_state, checkpoint)

    declaration_revision = _record_revision(checkpoint_state, "set_declaration")
    diverged_state = _correction(
        checkpoint_state,
        declaration_revision,
        SetSessionDeclarationCommandV1(
            expected_revision=declaration_revision - 1,
            declaration=GameDeclaration(
                game_type="grand",
                hand_game=True,
                bid_value=48,
            ),
        ),
    ).state
    diverged = classify_session_decision_checkpoint_v1(diverged_state, checkpoint)

    assert current.relationship == "current"
    assert ancestor.relationship == "ancestor"
    assert current_after_undo.relationship == "current"
    assert future.relationship == "future"
    assert diverged.relationship == "diverged"


def test_checkpoint_lineage_correction_boundaries_and_equal_effective_request() -> None:
    checkpoint_state, _, checkpoint = _checkpoint()
    later_state = _apply(
        checkpoint_state,
        RecordSessionPlayCommandV1(
            expected_revision=checkpoint_state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    later_correction = _correction(
        later_state,
        later_state.revision,
        RecordSessionPlayCommandV1(
            expected_revision=later_state.revision - 1,
            player_id="player-a",
            card="C10",
        ),
    )
    assert later_correction.status == "applied"
    assert classify_session_decision_checkpoint_v1(
        later_correction.state,
        checkpoint,
    ).relationship == "ancestor"

    first_deal_revision = _record_revision(checkpoint_state, "record_dealt_card")
    earlier_correction = _correction(
        checkpoint_state,
        first_deal_revision,
        RecordSessionDealtCardCommandV1(
            expected_revision=first_deal_revision - 1,
            destination="player_hand",
            player_id="player-a",
            card="SK",
        ),
    )
    assert earlier_correction.status == "applied"
    assert classify_session_decision_checkpoint_v1(
        earlier_correction.state,
        checkpoint,
    ).relationship == "diverged"

    metadata_state = _apply(
        _ready_live_state(),
        SetSessionGameMetadataCommandV1(
            expected_revision=_ready_live_state().revision,
            game_id="metadata-before-checkpoint",
        ),
    )
    metadata_export = export_session_position_analysis_request_v1(
        metadata_state,
        _options(),
    )
    metadata_checkpoint = build_session_decision_checkpoint_v1(
        state=metadata_state,
        position_export=metadata_export,
    )
    metadata_correction = _correction(
        metadata_state,
        metadata_state.revision,
        SetSessionGameMetadataCommandV1(
            expected_revision=metadata_state.revision - 1,
            game_id="different-metadata",
        ),
    )
    assert metadata_correction.status == "applied"
    assert classify_session_decision_checkpoint_v1(
        metadata_correction.state,
        metadata_checkpoint,
    ).relationship == "current"


def test_checkpoint_lineage_rejects_wrong_session_and_forged_checkpoint() -> None:
    state, _, checkpoint = _checkpoint()
    other = replace(state, session_id="other-session")
    with pytest.raises(ValueError, match="Session ID"):
        classify_session_decision_checkpoint_v1(other, checkpoint)

    forged = copy.copy(checkpoint)
    object.__setattr__(forged, "source_capture_mode", "unknown")
    with pytest.raises(SkatAIInvariantError, match="Checkpoint"):
        classify_session_decision_checkpoint_v1(state, forged)


def test_history_edits_never_mutate_checkpoint_or_attach_results() -> None:
    state, _, checkpoint = _checkpoint()
    before = checkpoint.to_dict()
    played = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    rewind_session_state_v1(
        played,
        expected_revision=played.revision,
        target_revision=state.revision - 1,
    )
    _correction(
        played,
        played.revision,
        RecordSessionPlayCommandV1(
            expected_revision=played.revision - 1,
            player_id="player-a",
            card="C10",
        ),
    )
    mutable = checkpoint.to_dict()
    mutable["request"]["document"]["hand"].clear()
    assert checkpoint.to_dict() == before
    assert "actual_card" not in checkpoint.to_dict()
    assert "result" not in checkpoint.to_dict()


def test_position_and_historical_exports_use_only_edited_active_log() -> None:
    checkpoint_state, _, _ = _checkpoint()
    played = _apply(
        checkpoint_state,
        RecordSessionPlayCommandV1(
            expected_revision=checkpoint_state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    rewound = rewind_session_state_v1(
        played,
        expected_revision=played.revision,
        target_revision=checkpoint_state.revision,
    )
    position = export_session_position_analysis_request_v1(rewound.state, _options())
    assert position.status == "available"
    assert position.request.to_dict()["document"]["hand"] == list(
        replay_session_state_v1(rewound.state).remaining_hand_for("player-a")
    )
    assert "CA" in position.request.to_dict()["document"]["hand"]

    historical_source = _complete_retrospective_session(build_historical_input())
    corrected = _correction(
        historical_source,
        1,
        SetSessionGameMetadataCommandV1(
            expected_revision=0,
            game_id="historical-corrected",
        ),
    )
    historical = export_session_historical_game_request_v1(corrected.state)
    assert historical.status == "available"
    assert historical.request.to_dict()["document"]["historical_game_input"][
        "game_id"
    ] == "historical-corrected"

    before_end = rewind_session_state_v1(
        historical_source,
        expected_revision=historical_source.revision,
        target_revision=historical_source.revision - 1,
    )
    unavailable = export_session_historical_game_request_v1(before_end.state)
    assert unavailable.status == "unavailable"
    assert unavailable.request is None


def test_repeated_history_operations_are_deterministic() -> None:
    source = _complete_retrospective_session(build_historical_input())
    first_undo = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=source.revision - 2,
    )
    second_undo = rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=source.revision - 2,
    )
    correction = SessionCommandCorrectionV1(
        expected_revision=source.revision,
        target_revision=1,
        replacement_command=SetSessionGameMetadataCommandV1(
            expected_revision=0,
            game_id="deterministic-correction",
        ),
    )
    first_correction = correct_session_command_v1(source, correction)
    second_correction = correct_session_command_v1(source, correction)
    state, _, checkpoint = _checkpoint()
    first_lineage = classify_session_decision_checkpoint_v1(state, checkpoint)
    second_lineage = classify_session_decision_checkpoint_v1(state, checkpoint)

    assert first_undo == second_undo
    assert first_undo.to_dict() == second_undo.to_dict()
    assert first_correction == second_correction
    assert first_correction.to_dict() == second_correction.to_dict()
    assert first_lineage == second_lineage
    assert first_lineage.to_dict() == second_lineage.to_dict()


def test_undo_and_correction_execution_counts_are_structurally_bounded(monkeypatch) -> None:
    source = _promoted_private_suffix_state(second_opponent_card=True)
    replay_count = 0
    prefix_count = 0
    original_replay = history_module.replay_session_state_v1
    original_prefix = history_module._reconstruct_session_prefix_v1

    def counted_replay(value):
        nonlocal replay_count
        replay_count += 1
        return original_replay(value)

    def counted_prefix(value, *, target_revision):
        nonlocal prefix_count
        prefix_count += 1
        return original_prefix(value, target_revision=target_revision)

    monkeypatch.setattr(history_module, "replay_session_state_v1", counted_replay)
    monkeypatch.setattr(
        history_module,
        "_reconstruct_session_prefix_v1",
        counted_prefix,
    )
    undo = history_module.rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=1,
    )
    assert undo.status == "applied"
    assert (replay_count, prefix_count) == (1, 1)

    replay_count = prefix_count = 0
    correction = history_module.correct_session_command_v1(
        source,
        SessionCommandCorrectionV1(
            expected_revision=source.revision,
            target_revision=2,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=1,
                game_id="bounded",
            ),
        ),
    )
    assert correction.status == "partial"
    assert (replay_count, prefix_count) == (1, 1)


def test_noop_correction_skips_prefix_and_suffix_application(monkeypatch) -> None:
    source = _promoted_private_suffix_state()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("No-op correction evaluated a prefix or suffix.")

    monkeypatch.setattr(history_module, "_reconstruct_session_prefix_v1", forbidden)
    monkeypatch.setattr(
        history_module,
        "apply_session_command_to_projection_v1",
        forbidden,
    )
    result = history_module.correct_session_command_v1(
        source,
        SessionCommandCorrectionV1(
            expected_revision=source.revision,
            target_revision=2,
            replacement_command=source.command_log[1].command,
        ),
    )
    assert result.status == "unchanged"


def test_lineage_uses_one_source_replay_prefix_and_expected_request(monkeypatch) -> None:
    state, _, checkpoint = _checkpoint()
    later = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    counts = {"replay": 0, "prefix": 0, "request": 0}
    original_replay = history_module.replay_session_state_v1
    original_prefix = history_module._reconstruct_session_prefix_v1
    original_request = (
        history_module._export_replayed_session_position_analysis_request_v1
    )

    def counted_replay(value):
        counts["replay"] += 1
        return original_replay(value)

    def counted_prefix(value, *, target_revision):
        counts["prefix"] += 1
        return original_prefix(value, target_revision=target_revision)

    def counted_request(**values):
        counts["request"] += 1
        return original_request(**values)

    monkeypatch.setattr(history_module, "replay_session_state_v1", counted_replay)
    monkeypatch.setattr(
        history_module,
        "_reconstruct_session_prefix_v1",
        counted_prefix,
    )
    monkeypatch.setattr(
        history_module,
        "_export_replayed_session_position_analysis_request_v1",
        counted_request,
    )
    result = history_module.classify_session_decision_checkpoint_v1(
        later,
        checkpoint,
    )
    assert result.relationship == "ancestor"
    assert counts == {"replay": 1, "prefix": 1, "request": 1}


def test_history_operations_do_not_automatically_execute_exports(monkeypatch) -> None:
    source = _promoted_private_suffix_state()

    def forbidden_export(*_args, **_kwargs):
        raise AssertionError("History edit executed an export automatically.")

    monkeypatch.setattr(
        history_module,
        "_export_replayed_session_position_analysis_request_v1",
        forbidden_export,
    )
    assert rewind_session_state_v1(
        source,
        expected_revision=source.revision,
        target_revision=1,
    ).status == "applied"
    assert _correction(
        source,
        2,
        SetSessionGameMetadataCommandV1(
            expected_revision=1,
            game_id="no-export",
        ),
    ).status == "partial"


def test_history_functions_validate_exact_types_and_forged_source_first() -> None:
    state = create_session_state_v1(
        session_id="session-history-types",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    with pytest.raises(ValueError, match="SessionStateV1"):
        rewind_session_state_v1(object(), expected_revision=0, target_revision=0)
    with pytest.raises(ValueError, match="SessionCommandCorrectionV1"):
        correct_session_command_v1(state, object())
    with pytest.raises(ValueError, match="SessionDecisionCheckpointV1"):
        classify_session_decision_checkpoint_v1(state, object())

    forged = copy.copy(state)
    object.__setattr__(forged, "revision", 1)
    with pytest.raises(SkatAIInvariantError, match="revision"):
        rewind_session_state_v1(forged, expected_revision=2, target_revision=2)
