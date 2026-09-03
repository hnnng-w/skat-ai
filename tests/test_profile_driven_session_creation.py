from __future__ import annotations

import pytest

from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.profile_driven_creation import (
    prepare_profile_driven_session_creation_v1,
)
from skatmind.app_web.profile_player_contracts import KnownPlayerV1


def _entropy_source():
    values = iter((b"p" * 32, b"q" * 32, b"r" * 32, b"s" * 32))
    return lambda _size: next(values)


def test_session_form_maps_names_mode_seats_perspective_and_profile_label() -> None:
    known = KnownPlayerV1("frontend-player-" + "a" * 64, "Anna", (), ())
    profile = build_local_frontend_profile_v1(
        known_players=(known,),
        preferred_perspective_player_id=known.player_id,
    )
    prepared = prepare_profile_driven_session_creation_v1(
        {
            "game_name": "Thursday game",
            "capture_mode": "live",
            "player_1_handle": build_known_player_handle_v1(known.player_id),
            "player_1_name": "",
            "player_2_handle": "",
            "player_2_name": "Peter",
            "player_3_handle": "",
            "player_3_name": "Mira",
            "perspective_seat": "forehand",
            "save_players": "on",
            "save_preferences": "on",
        },
        profile=profile,
        expected_profile_generation=7,
        existing_session_ids=(),
        entropy_source=_entropy_source(),
    )
    assert prepared.session_id.startswith("frontend-session-")
    assert tuple(player.seat for player in prepared.players) == (
        "forehand",
        "middlehand",
        "rearhand",
    )
    assert tuple(player.player_label for player in prepared.players) == (
        "Anna",
        "Peter",
        "Mira",
    )
    assert prepared.capture_mode == "live"
    assert prepared.local_player_id == known.player_id
    assert prepared.expected_profile_generation == 7
    assert tuple(player.display_name for player in prepared.profile_document.known_players) == (
        "Anna",
        "Peter",
        "Mira",
    )
    assert prepared.profile_document.preferred_perspective_player_id == known.player_id
    assert prepared.profile_document.managed_item_display_labels[-1].display_name == (
        "Thursday game"
    )


def test_session_one_off_players_are_not_saved_and_retrospective_can_have_no_perspective() -> None:
    prepared = prepare_profile_driven_session_creation_v1(
        {
            "game_name": "Review game",
            "capture_mode": "retrospective",
            "player_1_handle": "",
            "player_1_name": "A",
            "player_2_handle": "",
            "player_2_name": "B",
            "player_3_handle": "",
            "player_3_name": "C",
            "perspective_seat": "",
            "save_players": "",
            "save_preferences": "",
        },
        profile=None,
        expected_profile_generation=0,
        existing_session_ids=(),
        entropy_source=_entropy_source(),
    )
    assert prepared.local_player_id is None
    assert prepared.profile_document.known_players == ()
    assert len(prepared.profile_document.managed_item_display_labels) == 1


def test_session_validation_precedes_entropy_and_rejects_duplicate_seats() -> None:
    calls = 0

    def entropy(_size: int) -> bytes:
        nonlocal calls
        calls += 1
        return b"x" * 32

    values = {
        "game_name": "Game",
        "capture_mode": "live",
        "player_1_handle": "",
        "player_1_name": "Peter",
        "player_2_handle": "",
        "player_2_name": "peter",
        "player_3_handle": "",
        "player_3_name": "Anna",
        "perspective_seat": "",
        "save_players": "on",
        "save_preferences": "",
    }
    with pytest.raises(ValueError, match="duplicate new Player"):
        prepare_profile_driven_session_creation_v1(
            values,
            profile=None,
            expected_profile_generation=0,
            existing_session_ids=(),
            entropy_source=entropy,
        )
    assert calls == 0
    values["player_2_name"] = "Mira"
    with pytest.raises(ValueError, match="During-play"):
        prepare_profile_driven_session_creation_v1(
            values,
            profile=None,
            expected_profile_generation=0,
            existing_session_ids=(),
            entropy_source=entropy,
        )
    assert calls == 0


def test_session_rejects_mixed_saved_and_new_duplicate_names_before_entropy() -> None:
    known = KnownPlayerV1("frontend-player-" + "a" * 64, "Anna", (), ())
    profile = build_local_frontend_profile_v1(known_players=(known,))

    def entropy(_size: int) -> bytes:
        raise AssertionError("Duplicate Player names must be rejected before entropy.")

    with pytest.raises(ValueError, match="saved/new duplicates"):
        prepare_profile_driven_session_creation_v1(
            {
                "game_name": "Game",
                "capture_mode": "retrospective",
                "player_1_handle": build_known_player_handle_v1(known.player_id),
                "player_1_name": "",
                "player_2_handle": "",
                "player_2_name": "anna",
                "player_3_handle": "",
                "player_3_name": "Mira",
                "perspective_seat": "",
                "save_players": "false",
                "save_preferences": "false",
            },
            profile=profile,
            expected_profile_generation=0,
            existing_session_ids=(),
            entropy_source=entropy,
        )


def test_retrospective_saved_empty_perspective_clears_the_preference() -> None:
    known = KnownPlayerV1("frontend-player-" + "a" * 64, "Anna", (), ())
    profile = build_local_frontend_profile_v1(
        known_players=(known,),
        preferred_perspective_player_id=known.player_id,
    )
    prepared = prepare_profile_driven_session_creation_v1(
        {
            "game_name": "Review game",
            "capture_mode": "retrospective",
            "player_1_handle": build_known_player_handle_v1(known.player_id),
            "player_1_name": "",
            "player_2_handle": "",
            "player_2_name": "Peter",
            "player_3_handle": "",
            "player_3_name": "Mira",
            "perspective_seat": "",
            "save_players": "true",
            "save_preferences": "true",
        },
        profile=profile,
        expected_profile_generation=0,
        existing_session_ids=(),
        entropy_source=_entropy_source(),
    )
    assert prepared.local_player_id is None
    assert prepared.profile_document is not None
    assert prepared.profile_document.preferred_perspective_player_id is None
