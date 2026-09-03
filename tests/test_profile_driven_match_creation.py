from __future__ import annotations

import pytest

from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.profile_driven_creation import (
    prepare_profile_driven_match_creation_v1,
)
from skatmind.app_web.profile_player_contracts import (
    KnownPlayerPlatformIdV1,
    KnownPlayerV1,
)


def _values(**overrides: str) -> dict[str, str]:
    values = {
        "match_title": "Thursday Match",
        "played_date": "2026-09-03",
        "platform_choice": "euroskat",
        "custom_platform": "",
        "player_1_handle": "",
        "player_1_name": "Anna",
        "player_2_handle": "",
        "player_2_name": "Peter",
        "player_3_handle": "",
        "player_3_name": "Mira",
        "perspective_seat": "middlehand",
        "source_url": "",
        "external_match_id": "",
        "player_1_platform_id": "",
        "player_2_platform_id": "",
        "player_3_platform_id": "",
        "source_kind": "",
        "source_title": "",
        "source_channel_name": "",
        "played_at": "",
        "match_timecode_start": "",
        "match_timecode_end": "",
        "save_players": "on",
        "save_preferences": "on",
    }
    values.update(overrides)
    return values


def _entropy_source():
    values = iter((b"a" * 32, b"b" * 32, b"c" * 32, b"d" * 32))
    return lambda _size: next(values)


def test_match_form_maps_friendly_values_without_inventing_an_instant() -> None:
    prepared = prepare_profile_driven_match_creation_v1(
        _values(),
        profile=None,
        expected_profile_generation=0,
        existing_match_ids=(),
        entropy_source=_entropy_source(),
    )
    values = dict(prepared.product_values)
    assert values["match_id"].startswith("frontend-match-")
    assert values["title"] == "Thursday Match"
    assert values["game_platform"] == "EuroSkat"
    assert values["played_at"] == ""
    assert values["source_kind"] == "manual_observation"
    assert values["source_url"] == ""
    assert values["source_title"] == "Thursday Match"
    assert values["perspective_player_id"] == values["player_2_id"]
    label = prepared.profile_document.managed_item_display_labels[-1]
    assert label.display_name == "Thursday Match"
    assert label.played_date == "2026-09-03"
    assert prepared.profile_document.preferred_game_platform == "EuroSkat"


@pytest.mark.parametrize(
    ("url", "kind"),
    (
        ("https://youtube.com/watch?v=x", "youtube_video"),
        ("https://www.youtube.com/watch?v=x", "youtube_video"),
        ("https://m.youtube.com/watch?v=x", "youtube_video"),
        ("https://youtu.be/x", "youtube_video"),
        ("https://videos.example/match", "other_video"),
    ),
)
def test_match_source_url_derivation_is_exact(url: str, kind: str) -> None:
    prepared = prepare_profile_driven_match_creation_v1(
        _values(source_url=url),
        profile=None,
        expected_profile_generation=0,
        existing_match_ids=(),
        entropy_source=_entropy_source(),
    )
    assert prepared.product_values["source_kind"] == kind
    assert prepared.product_values["source_url"] == url
    assert prepared.product_values["source_title"] == "Thursday Match"


@pytest.mark.parametrize(
    "url",
    (
        "https://youtube.com.evil.example/watch?v=x",
        "ftp://youtube.com/x",
        "https://user:password@youtube.com/x",
    ),
)
def test_match_source_rejects_lookalikes_schemes_and_credentials(url: str) -> None:
    if "evil" in url:
        prepared = prepare_profile_driven_match_creation_v1(
            _values(source_url=url),
            profile=None,
            expected_profile_generation=0,
            existing_match_ids=(),
            entropy_source=_entropy_source(),
        )
        assert prepared.product_values["source_kind"] == "other_video"
        return
    with pytest.raises(ValueError):
        prepare_profile_driven_match_creation_v1(
            _values(source_url=url),
            profile=None,
            expected_profile_generation=0,
            existing_match_ids=(),
            entropy_source=_entropy_source(),
        )


def test_match_advanced_timestamp_and_date_must_reconcile() -> None:
    prepared = prepare_profile_driven_match_creation_v1(
        _values(played_at="2026-09-03T19:30:00+02:00"),
        profile=None,
        expected_profile_generation=0,
        existing_match_ids=(),
        entropy_source=_entropy_source(),
    )
    assert prepared.product_values["played_at"] == "2026-09-03T19:30:00+02:00"
    with pytest.raises(ValueError, match="same calendar date"):
        prepare_profile_driven_match_creation_v1(
            _values(played_at="2026-09-04T00:30:00+02:00"),
            profile=None,
            expected_profile_generation=0,
            existing_match_ids=(),
            entropy_source=_entropy_source(),
        )


def test_match_custom_platform_and_advanced_source_values_remain_product_values() -> None:
    prepared = prepare_profile_driven_match_creation_v1(
        _values(
            platform_choice="custom",
            custom_platform="Local club",
            source_url="https://videos.example/match",
            source_kind="other_video",
            source_title="Camera 2",
            source_channel_name="Club archive",
            match_timecode_start="01:02",
            match_timecode_end="02:03",
            player_1_platform_id="anna-1",
        ),
        profile=None,
        expected_profile_generation=0,
        existing_match_ids=(),
        entropy_source=_entropy_source(),
    )
    values = prepared.product_values
    assert values["game_platform"] == "Local club"
    assert values["source_title"] == "Camera 2"
    assert values["source_channel_name"] == "Club archive"
    assert values["player_1_platform_id"] == "anna-1"


def test_match_builtin_platform_ignores_stale_custom_platform_text() -> None:
    prepared = prepare_profile_driven_match_creation_v1(
        _values(platform_choice="euroskat", custom_platform="Previous custom value"),
        profile=None,
        expected_profile_generation=0,
        existing_match_ids=(),
        entropy_source=_entropy_source(),
    )
    assert prepared.product_values["game_platform"] == "EuroSkat"


def test_match_does_not_invisibly_copy_saved_platform_player_ids() -> None:
    known = KnownPlayerV1(
        "frontend-player-" + "a" * 64,
        "Anna",
        (),
        (KnownPlayerPlatformIdV1("EuroSkat", "saved-account"),),
    )
    profile = build_local_frontend_profile_v1(known_players=(known,))
    prepared = prepare_profile_driven_match_creation_v1(
        _values(
            player_1_handle=build_known_player_handle_v1(known.player_id),
            player_1_name="",
        ),
        profile=profile,
        expected_profile_generation=0,
        existing_match_ids=(),
        entropy_source=_entropy_source(),
    )
    assert prepared.product_values["player_1_platform_id"] == ""
