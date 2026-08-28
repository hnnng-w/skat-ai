import pytest
from test_historical_game import build_historical_input
from test_match_workspace_contracts import _definition
from test_observed_game_contracts import declaration_from_historical

import skatmind.match_capture_application as application_module
import skatmind.match_capture_position_view as position_view_module
from skatmind.game_declaration import GameDeclaration
from skatmind.match_capture_application import (
    append_match_capture_play_v1,
    append_match_capture_plays_v1,
    mark_match_capture_passed_deal_v1,
    set_match_capture_declaration_v1,
    set_match_capture_discarded_cards_v1,
    set_match_capture_game_timecode_v1,
    set_match_capture_original_skat_v1,
    set_match_capture_perspective_initial_hand_v1,
    start_match_capture_game_v1,
)
from skatmind.match_capture_application_contracts import MatchCaptureCardEntryV1
from skatmind.match_capture_game_updates import build_default_match_capture_game_id_v1
from skatmind.match_source_metadata import MediaTimecodeV1
from skatmind.match_workspace_contracts import create_match_workspace_v1


def _entry(card: str, start: int | None = None) -> MatchCaptureCardEntryV1:
    return MatchCaptureCardEntryV1(
        card=card,
        decision_timecode=(
            None if start is None else MediaTimecodeV1(start_offset_ms=start, end_offset_ms=None)
        ),
    )


def _start(workspace, *, position: int = 1, **overrides):
    return start_match_capture_game_v1(
        workspace,
        match_position=position,
        expected_revision=workspace.revision,
        **overrides,
    )


def _declare(workspace, *, position: int = 1, declarer: str = "player-b"):
    return set_match_capture_declaration_v1(
        workspace,
        match_position=position,
        declarer_player_id=declarer,
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        expected_revision=workspace.revision,
    )


def test_default_game_ids_are_exact_zero_padded_and_environment_free() -> None:
    workspace = create_match_workspace_v1(_definition())
    assert (
        build_default_match_capture_game_id_v1(
            workspace,
            match_position=1,
        )
        == "match-160-game-01"
    )
    assert (
        build_default_match_capture_game_id_v1(
            workspace,
            match_position=36,
        )
        == "match-160-game-36"
    )
    assert build_default_match_capture_game_id_v1(
        workspace,
        match_position=1,
    ) == build_default_match_capture_game_id_v1(workspace, match_position=1)


def test_start_game_derives_rotation_perspective_identity_timecode_and_revision() -> None:
    source = create_match_workspace_v1(_definition())
    timecode = MediaTimecodeV1(start_offset_ms=20_000, end_offset_ms=40_000)
    result = _start(source, position=1, game_timecode=timecode)
    game = result.workspace_change.workspace.slots[0].observed_game
    assert result.operation == "start_game"
    assert result.status == "applied"
    assert result.workspace_change.source_revision == 0
    assert result.workspace_change.current_revision == 1
    assert result.workspace_change.workspace.revision == 1
    assert source.revision == 0 and source.slots[0].slot_kind == "empty"
    assert game.game_id == "match-160-game-01"
    assert game.game_timecode == timecode
    assert tuple(player.player_id for player in game.players) == (
        "player-b",
        "player-c",
        "player-a",
    )
    assert game.perspective_player_id == "player-a"
    assert game.perspective_initial_hand is None
    assert game.declarer_player_id is game.declaration is None
    assert game.original_skat is game.discarded_cards is None
    assert game.plays == game.commentaries == game.response_links == ()
    assert result.position_view.workspace_progress.observed_game_count == 1


def test_start_game_supports_explicit_id_passed_replacement_and_idempotence() -> None:
    source = create_match_workspace_v1(_definition())
    passed = mark_match_capture_passed_deal_v1(
        source,
        match_position=36,
        game_timecode=None,
        expected_revision=0,
    ).workspace_change.workspace
    started = _start(passed, position=36, game_id="explicit-game-36")
    assert started.status == "applied"
    assert started.position_view.slot_kind == "observed_game"
    assert started.position_view.game_id == "explicit-game-36"
    repeated = start_match_capture_game_v1(
        started.workspace_change.workspace,
        match_position=36,
        game_id="explicit-game-36",
        game_timecode=None,
        expected_revision=started.workspace_change.current_revision,
    )
    assert repeated.status == "unchanged"
    assert repeated.workspace_change.workspace is started.workspace_change.workspace


def test_equal_capture_inputs_are_deterministic() -> None:
    workspace = create_match_workspace_v1(_definition())
    first = start_match_capture_game_v1(
        workspace,
        match_position=1,
        expected_revision=0,
    )
    second = start_match_capture_game_v1(
        workspace,
        match_position=1,
        expected_revision=0,
    )
    assert first == second
    assert first.to_dict() == second.to_dict()


def test_start_existing_game_never_erases_evidence_and_rejects_identity_or_timecode_drift() -> None:
    started = _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    declared = _declare(started).workspace_change.workspace
    played = append_match_capture_play_v1(
        declared,
        match_position=1,
        entry=_entry("CA"),
        expected_revision=declared.revision,
    ).workspace_change.workspace
    existing = played.slots[0].observed_game
    for values in (
        {"game_id": "different-game"},
        {
            "game_id": existing.game_id,
            "game_timecode": MediaTimecodeV1(
                start_offset_ms=20_000,
                end_offset_ms=30_000,
            ),
        },
    ):
        with pytest.raises(ValueError, match="clear it or use"):
            start_match_capture_game_v1(
                played,
                match_position=1,
                expected_revision=played.revision,
                **values,
            )
    assert played.slots[0].observed_game == existing
    assert len(existing.plays) == 1


def test_revision_conflict_precedes_start_and_update_payload_semantics() -> None:
    workspace = create_match_workspace_v1(_definition())
    start_conflict = start_match_capture_game_v1(
        workspace,
        match_position=1,
        expected_revision=1,
        game_id=" padded ",
        game_timecode="invalid",
    )
    assert start_conflict.status == "revision_conflict"
    assert start_conflict.workspace_change.workspace is workspace
    assert start_conflict.position_view.game_state == "empty"

    started = _start(workspace).workspace_change.workspace
    hand_conflict = set_match_capture_perspective_initial_hand_v1(
        started,
        match_position=1,
        cards=("XX",),
        expected_revision=0,
    )
    append_conflict = append_match_capture_plays_v1(
        started,
        match_position=1,
        entries=("not-an-entry",),
        expected_revision=0,
    )
    assert hand_conflict.status == append_conflict.status == "revision_conflict"
    assert hand_conflict.workspace_change.workspace is started
    assert append_conflict.workspace_change.workspace is started


def test_game_timecode_set_clear_equal_and_nested_timecode_validation() -> None:
    workspace = _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    timecode = MediaTimecodeV1(start_offset_ms=20_000, end_offset_ms=50_000)
    set_result = set_match_capture_game_timecode_v1(
        workspace,
        match_position=1,
        game_timecode=timecode,
        expected_revision=workspace.revision,
    )
    assert set_result.status == "applied"
    retained = set_result.workspace_change.workspace
    equal = set_match_capture_game_timecode_v1(
        retained,
        match_position=1,
        game_timecode=timecode,
        expected_revision=retained.revision,
    )
    assert equal.status == "unchanged"
    cleared = set_match_capture_game_timecode_v1(
        retained,
        match_position=1,
        game_timecode=None,
        expected_revision=retained.revision,
    )
    assert cleared.status == "applied"
    assert cleared.workspace_change.workspace.slots[0].observed_game.game_timecode is None

    declared = _declare(retained).workspace_change.workspace
    played = append_match_capture_play_v1(
        declared,
        match_position=1,
        entry=_entry("CA", 30_000),
        expected_revision=declared.revision,
    ).workspace_change.workspace
    with pytest.raises(ValueError, match="within game_timecode"):
        set_match_capture_game_timecode_v1(
            played,
            match_position=1,
            game_timecode=MediaTimecodeV1(
                start_offset_ms=35_000,
                end_offset_ms=40_000,
            ),
            expected_revision=played.revision,
        )
    assert played.slots[0].observed_game.plays[0].decision_timecode.start_offset_ms == 30_000


def test_game_timecode_update_preserves_workspace_position_ordering() -> None:
    workspace = create_match_workspace_v1(_definition())
    first = _start(
        workspace,
        position=1,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=30_000,
            end_offset_ms=35_000,
        ),
    ).workspace_change.workspace
    second = _start(
        first,
        position=2,
        game_timecode=MediaTimecodeV1(
            start_offset_ms=40_000,
            end_offset_ms=45_000,
        ),
    ).workspace_change.workspace
    with pytest.raises(ValueError, match="non-decreasing"):
        set_match_capture_game_timecode_v1(
            second,
            match_position=2,
            game_timecode=MediaTimecodeV1(
                start_offset_ms=25_000,
                end_offset_ms=45_000,
            ),
            expected_revision=second.revision,
        )
    assert second.slots[1].observed_game.game_timecode.start_offset_ms == 40_000


def test_perspective_hand_set_clear_equal_and_trace_ownership_reconciliation() -> None:
    workspace = _start(
        create_match_workspace_v1(_definition()), position=3
    ).workspace_change.workspace
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
    set_result = set_match_capture_perspective_initial_hand_v1(
        workspace,
        match_position=3,
        cards=hand,
        expected_revision=workspace.revision,
    )
    assert set_result.status == "applied"
    retained = set_result.workspace_change.workspace
    assert retained.slots[2].observed_game.perspective_initial_hand == hand
    assert (
        set_match_capture_perspective_initial_hand_v1(
            retained,
            match_position=3,
            cards=hand,
            expected_revision=retained.revision,
        ).status
        == "unchanged"
    )
    assert (
        set_match_capture_perspective_initial_hand_v1(
            retained,
            match_position=3,
            cards=None,
            expected_revision=retained.revision,
        )
        .workspace_change.workspace.slots[2]
        .observed_game.perspective_initial_hand
        is None
    )
    with pytest.raises(ValueError, match="Card counts"):
        set_match_capture_perspective_initial_hand_v1(
            retained,
            match_position=3,
            cards=("CA",),
            expected_revision=retained.revision,
        )


@pytest.mark.parametrize(
    "declaration",
    (
        GameDeclaration(game_type="clubs", matadors=1, bid_value=18),
        GameDeclaration(game_type="spades", matadors=1, bid_value=18),
        GameDeclaration(game_type="hearts", matadors=1, bid_value=18),
        GameDeclaration(game_type="diamonds", matadors=1, bid_value=18),
        GameDeclaration(game_type="grand", hand_game=True, matadors=1, bid_value=48),
        GameDeclaration(game_type="null", bid_value=23),
        GameDeclaration(game_type="null", hand_game=True, bid_value=35),
        GameDeclaration(game_type="null", ouvert=True, bid_value=35),
        GameDeclaration(game_type="null", hand_game=True, ouvert=True, bid_value=59),
    ),
)
def test_declaration_updates_retain_all_existing_variants_and_equal_is_unchanged(
    declaration: GameDeclaration,
) -> None:
    workspace = _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    result = set_match_capture_declaration_v1(
        workspace,
        match_position=1,
        declarer_player_id="player-b",
        declaration=declaration,
        expected_revision=workspace.revision,
    )
    assert result.status == "applied"
    game = result.workspace_change.workspace.slots[0].observed_game
    assert game.declarer_player_id == "player-b"
    assert game.declaration == declaration
    assert (
        set_match_capture_declaration_v1(
            result.workspace_change.workspace,
            match_position=1,
            declarer_player_id="player-b",
            declaration=declaration,
            expected_revision=result.workspace_change.current_revision,
        ).status
        == "unchanged"
    )


def test_declaration_clear_requires_pair_and_cannot_remove_play_requirements() -> None:
    workspace = _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    for declarer, declaration in (
        ("player-b", None),
        (None, GameDeclaration(game_type="grand", bid_value=24)),
    ):
        with pytest.raises(ValueError, match="both null or both present"):
            set_match_capture_declaration_v1(
                workspace,
                match_position=1,
                declarer_player_id=declarer,
                declaration=declaration,
                expected_revision=workspace.revision,
            )
    declared = _declare(workspace).workspace_change.workspace
    cleared = set_match_capture_declaration_v1(
        declared,
        match_position=1,
        declarer_player_id=None,
        declaration=None,
        expected_revision=declared.revision,
    )
    assert cleared.position_view.game_state == "setup"
    played = append_match_capture_play_v1(
        declared,
        match_position=1,
        entry=_entry("CA"),
        expected_revision=declared.revision,
    ).workspace_change.workspace
    with pytest.raises(ValueError, match="Observed Plays require"):
        set_match_capture_declaration_v1(
            played,
            match_position=1,
            declarer_player_id=None,
            declaration=None,
            expected_revision=played.revision,
        )


def test_original_skat_and_discard_updates_preserve_unknown_empty_and_exact_states() -> None:
    workspace = _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    declared = _declare(workspace).workspace_change.workspace
    skat = set_match_capture_original_skat_v1(
        declared,
        match_position=1,
        cards=("D8", "H8"),
        expected_revision=declared.revision,
    )
    assert skat.workspace_change.workspace.slots[0].observed_game.original_skat == (
        "H8",
        "D8",
    )
    assert (
        set_match_capture_original_skat_v1(
            skat.workspace_change.workspace,
            match_position=1,
            cards=("H8", "D8"),
            expected_revision=skat.workspace_change.current_revision,
        ).status
        == "unchanged"
    )
    assert (
        set_match_capture_original_skat_v1(
            skat.workspace_change.workspace,
            match_position=1,
            cards=None,
            expected_revision=skat.workspace_change.current_revision,
        )
        .workspace_change.workspace.slots[0]
        .observed_game.original_skat
        is None
    )

    discards = set_match_capture_discarded_cards_v1(
        declared,
        match_position=1,
        cards=("H9", "D9"),
        expected_revision=declared.revision,
    )
    assert discards.workspace_change.workspace.slots[0].observed_game.discarded_cards == (
        "H9",
        "D9",
    )
    assert (
        set_match_capture_discarded_cards_v1(
            discards.workspace_change.workspace,
            match_position=1,
            cards=None,
            expected_revision=discards.workspace_change.current_revision,
        )
        .workspace_change.workspace.slots[0]
        .observed_game.discarded_cards
        is None
    )

    hand_declaration = set_match_capture_declaration_v1(
        workspace,
        match_position=1,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", hand_game=True, bid_value=48),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    empty_discards = set_match_capture_discarded_cards_v1(
        hand_declaration,
        match_position=1,
        cards=(),
        expected_revision=hand_declaration.revision,
    )
    assert empty_discards.workspace_change.workspace.slots[0].observed_game.discarded_cards == ()
    with pytest.raises(ValueError, match="Hand games"):
        set_match_capture_discarded_cards_v1(
            hand_declaration,
            match_position=1,
            cards=("H9", "D9"),
            expected_revision=hand_declaration.revision,
        )


def test_setup_evidence_updates_reconcile_with_existing_plays() -> None:
    workspace = _declare(
        _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    ).workspace_change.workspace
    played = append_match_capture_plays_v1(
        workspace,
        match_position=1,
        entries=(_entry("CA"), _entry("S7")),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    with pytest.raises(ValueError, match="belongs to the perspective initial hand"):
        set_match_capture_perspective_initial_hand_v1(
            played,
            match_position=1,
            cards=("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10"),
            expected_revision=played.revision,
        )
    with pytest.raises(ValueError, match="only by the Declarer"):
        set_match_capture_original_skat_v1(
            played,
            match_position=1,
            cards=("S7", "D7"),
            expected_revision=played.revision,
        )
    with pytest.raises(ValueError, match="cannot appear in Plays"):
        set_match_capture_discarded_cards_v1(
            played,
            match_position=1,
            cards=("CA", "D7"),
            expected_revision=played.revision,
        )
    assert len(played.slots[0].observed_game.plays) == 2


def test_complete_trace_setup_updates_accept_only_reconciled_retained_evidence() -> None:
    data = build_historical_input(game_type="grand", hand_game=False)
    workspace = _start(
        create_match_workspace_v1(_definition()),
        position=3,
    ).workspace_change.workspace
    workspace = set_match_capture_declaration_v1(
        workspace,
        match_position=3,
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    entries = tuple(_entry(play["card"]) for trick in data["tricks"] for play in trick["plays"])
    workspace = append_match_capture_plays_v1(
        workspace,
        match_position=3,
        entries=entries,
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    workspace = set_match_capture_original_skat_v1(
        workspace,
        match_position=3,
        cards=tuple(data["skat"]),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    workspace = set_match_capture_discarded_cards_v1(
        workspace,
        match_position=3,
        cards=tuple(data["discarded_cards"]),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    perspective_hand = next(
        tuple(player["initial_hand"])
        for player in data["players"]
        if player["player_id"] == "player-a"
    )
    reconciled = set_match_capture_perspective_initial_hand_v1(
        workspace,
        match_position=3,
        cards=perspective_hand,
        expected_revision=workspace.revision,
    )
    assert reconciled.status == "applied"
    with pytest.raises(ValueError):
        set_match_capture_discarded_cards_v1(
            reconciled.workspace_change.workspace,
            match_position=3,
            cards=("CA", "D7"),
            expected_revision=reconciled.workspace_change.current_revision,
        )


def test_append_single_and_batch_derive_players_indexes_timecodes_and_one_revision() -> None:
    workspace = _declare(
        _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    ).workspace_change.workspace
    single = append_match_capture_play_v1(
        workspace,
        match_position=1,
        entry=_entry("CA", 20_000),
        expected_revision=workspace.revision,
    )
    assert single.operation == "append_plays"
    assert single.workspace_change.current_revision == workspace.revision + 1
    first = single.workspace_change.workspace.slots[0].observed_game.plays[0]
    assert (first.decision_index, first.player_id, first.card) == (1, "player-b", "CA")
    assert first.decision_timecode.start_offset_ms == 20_000

    source = single.workspace_change.workspace
    batch = append_match_capture_plays_v1(
        source,
        match_position=1,
        entries=(_entry("S7", 20_000), _entry("C7", 21_000), _entry("D7", 22_000)),
        expected_revision=source.revision,
    )
    assert batch.workspace_change.current_revision == source.revision + 1
    plays = batch.workspace_change.workspace.slots[0].observed_game.plays
    assert tuple((play.decision_index, play.player_id, play.card) for play in plays) == (
        (1, "player-b", "CA"),
        (2, "player-c", "S7"),
        (3, "player-a", "C7"),
        (4, "player-b", "D7"),
    )
    assert batch.position_view.next_player_id == "player-c"


def test_append_batch_rejection_is_atomic_for_duplicate_time_and_exact_illegal_play() -> None:
    workspace = _declare(
        _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    ).workspace_change.workspace
    source_dict = workspace.to_dict()
    for entries, message in (
        ((_entry("CA"), _entry("CA")), "more than once"),
        ((_entry("CA", 30_000), _entry("S7", 20_000)), "non-decreasing"),
        ((), "non-empty"),
    ):
        with pytest.raises(ValueError, match=message):
            append_match_capture_plays_v1(
                workspace,
                match_position=1,
                entries=entries,
                expected_revision=workspace.revision,
            )
        assert workspace.to_dict() == source_dict

    position_three = _start(
        create_match_workspace_v1(_definition()),
        position=3,
    ).workspace_change.workspace
    declared = set_match_capture_declaration_v1(
        position_three,
        match_position=3,
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", bid_value=24),
        expected_revision=position_three.revision,
    ).workspace_change.workspace
    known = set_match_capture_perspective_initial_hand_v1(
        declared,
        match_position=3,
        cards=("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10"),
        expected_revision=declared.revision,
    ).workspace_change.workspace
    with pytest.raises(ValueError, match="does not own"):
        append_match_capture_play_v1(
            known,
            match_position=3,
            entry=_entry("H7"),
            expected_revision=known.revision,
        )
    assert known.slots[2].observed_game.plays == ()


def test_one_atomic_batch_can_complete_the_full_trace_without_hidden_completion() -> None:
    data = build_historical_input(game_type="grand", hand_game=False)
    workspace = _start(
        create_match_workspace_v1(_definition()),
        position=3,
    ).workspace_change.workspace
    declared = set_match_capture_declaration_v1(
        workspace,
        match_position=3,
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        expected_revision=workspace.revision,
    ).workspace_change.workspace
    entries = tuple(_entry(play["card"]) for trick in data["tricks"] for play in trick["plays"])
    result = append_match_capture_plays_v1(
        declared,
        match_position=3,
        entries=entries,
        expected_revision=declared.revision,
    )
    game = result.workspace_change.workspace.slots[2].observed_game
    assert result.status == "applied"
    assert result.workspace_change.current_revision == declared.revision + 1
    assert len(game.plays) == 30
    assert result.position_view.game_state == "play_complete"
    assert game.original_skat is None
    assert game.discarded_cards is None
    assert result.position_view.evidence_summary.complete_play_trace
    with pytest.raises(ValueError, match="at most 30"):
        append_match_capture_play_v1(
            result.workspace_change.workspace,
            match_position=3,
            entry=_entry("D7"),
            expected_revision=result.workspace_change.current_revision,
        )


def test_play_batch_uses_one_update_pass_workspace_change_view_and_progress(
    monkeypatch,
) -> None:
    workspace = _declare(
        _start(create_match_workspace_v1(_definition())).workspace_change.workspace
    ).workspace_change.workspace
    calls = {"append": 0, "workspace": 0, "view": 0, "progress": 0}
    original_append = application_module.append_match_capture_game_plays_v1
    original_workspace = application_module.set_match_workspace_observed_game_v1
    original_view = application_module.build_match_capture_position_view_v1
    original_progress = position_view_module._build_validated_match_workspace_progress_v1

    def counted_append(*args, **kwargs):
        calls["append"] += 1
        return original_append(*args, **kwargs)

    def counted_workspace(*args, **kwargs):
        calls["workspace"] += 1
        return original_workspace(*args, **kwargs)

    def counted_view(*args, **kwargs):
        calls["view"] += 1
        return original_view(*args, **kwargs)

    def counted_progress(*args, **kwargs):
        calls["progress"] += 1
        return original_progress(*args, **kwargs)

    monkeypatch.setattr(
        application_module,
        "append_match_capture_game_plays_v1",
        counted_append,
    )
    monkeypatch.setattr(
        application_module,
        "set_match_workspace_observed_game_v1",
        counted_workspace,
    )
    monkeypatch.setattr(
        application_module,
        "build_match_capture_position_view_v1",
        counted_view,
    )
    monkeypatch.setattr(
        position_view_module,
        "_build_validated_match_workspace_progress_v1",
        counted_progress,
    )
    result = application_module.append_match_capture_plays_v1(
        workspace,
        match_position=1,
        entries=(_entry("CA"), _entry("S7")),
        expected_revision=workspace.revision,
    )
    assert result.status == "applied"
    assert calls == {"append": 1, "workspace": 1, "view": 1, "progress": 1}
