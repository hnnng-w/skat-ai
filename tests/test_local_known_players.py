from __future__ import annotations

from pathlib import Path

import pytest

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.frontend_profile_operations import (
    FrontendProfilePersistenceConflictError,
    reset_frontend_recommended_defaults_v1,
    set_frontend_language_v1,
)
from skatmind.app_web.frontend_profile_persistence import save_frontend_profile_file_v1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.profile_player_contracts import (
    KnownPlayerPlatformIdV1,
    ManagedItemDisplayLabelV1,
)
from skatmind.app_web.profile_player_operations import (
    add_known_player_v1,
    remove_known_player_v1,
    replace_known_player_v1,
    resolve_known_player_handle_v1,
    set_frontend_creation_preferences_v1,
    set_managed_item_display_label_v1,
)


def _context(tmp_path: Path) -> AppWebContextV1:
    return AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))


def test_add_edit_and_resolve_known_player_without_product_mutation(tmp_path: Path) -> None:
    context = _context(tmp_path)
    result = add_known_player_v1(
        context,
        display_name="Henning",
        aliases=("H",),
        platform_player_ids=(KnownPlayerPlatformIdV1("EuroSkat", "henning-1"),),
        expected_generation=0,
        entropy_source=lambda _size: b"p" * 32,
    )
    assert result.status == "saved"
    assert result.player.display_name == "Henning"
    assert context.frontend_profile.generation == 1
    assert not tuple(context.managed_home.category("sessions").path.iterdir())
    assert not tuple(context.managed_home.category("matches").path.iterdir())
    assert not tuple(context.managed_home.category("corpora").path.iterdir())

    handle = build_known_player_handle_v1(result.player.player_id)
    assert (
        resolve_known_player_handle_v1(
            context.frontend_profile.document,
            handle,
        )
        == result.player
    )
    edited = replace_known_player_v1(
        context,
        player_handle=handle,
        display_name="Henning (Berlin)",
        aliases=("H", "Hen"),
        platform_player_ids=(),
        expected_generation=1,
    )
    assert edited.status == "saved"
    assert edited.player.player_id == result.player.player_id
    assert edited.player.display_name == "Henning (Berlin)"
    assert (
        replace_known_player_v1(
            context,
            player_handle=handle,
            display_name="Henning (Berlin)",
            aliases=("H", "Hen"),
            platform_player_ids=(),
            expected_generation=2,
        ).status
        == "unchanged"
    )
    assert context.frontend_profile.generation == 2


def test_preferences_language_and_recommended_reset_preserve_profile_data(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    added = add_known_player_v1(
        context,
        display_name="Henning",
        aliases=(),
        platform_player_ids=(),
        expected_generation=0,
        entropy_source=lambda _size: b"q" * 32,
    )
    player_id = added.player.player_id
    assert (
        set_frontend_creation_preferences_v1(
            context,
            own_player_id=player_id,
            preferred_perspective_player_id=player_id,
            preferred_game_platform="EuroSkat",
            advanced_settings_expanded=True,
            expected_generation=1,
        )
        == "saved"
    )
    assert (
        set_managed_item_display_label_v1(
            context,
            label=ManagedItemDisplayLabelV1(
                "sessions", "frontend-session-" + "a" * 64, "Friendly game"
            ),
            expected_generation=2,
        )
        == "saved"
    )
    assert (
        set_frontend_language_v1(
            context,
            language="de",
            expected_generation=3,
        )
        == "saved"
    )
    document = context.frontend_profile.document
    assert document is not None
    assert document.language == "de"
    assert document.known_players == (added.player,)
    assert document.own_player_id == player_id
    assert document.preferred_perspective_player_id == player_id
    assert document.preferred_game_platform == "EuroSkat"
    assert len(document.managed_item_display_labels) == 1

    assert (
        reset_frontend_recommended_defaults_v1(
            context,
            expected_generation=4,
        )
        == "saved"
    )
    reset = context.frontend_profile.document
    assert reset is not None
    assert reset.language == "de"
    assert reset.known_players == (added.player,)
    assert reset.own_player_id == player_id
    assert reset.managed_item_display_labels == document.managed_item_display_labels
    assert reset.preferred_perspective_player_id is None
    assert reset.preferred_game_platform is None
    assert reset.interface_preferences.advanced_settings_expanded is False


def test_referenced_player_removal_requires_confirmation_and_clears_references(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    added = add_known_player_v1(
        context,
        display_name="Henning",
        aliases=(),
        platform_player_ids=(),
        expected_generation=0,
        entropy_source=lambda _size: b"r" * 32,
    )
    player_id = added.player.player_id
    set_frontend_creation_preferences_v1(
        context,
        own_player_id=player_id,
        preferred_perspective_player_id=player_id,
        preferred_game_platform=None,
        advanced_settings_expanded=False,
        expected_generation=1,
    )
    handle = build_known_player_handle_v1(player_id)
    with pytest.raises(ValueError, match="confirmation"):
        remove_known_player_v1(
            context,
            player_handle=handle,
            confirm_referenced=False,
            expected_generation=2,
        )
    assert (
        remove_known_player_v1(
            context,
            player_handle=handle,
            confirm_referenced=True,
            expected_generation=2,
        )
        == "saved"
    )
    document = context.frontend_profile.document
    assert document is not None
    assert document.known_players == ()
    assert document.own_player_id is None
    assert document.preferred_perspective_player_id is None


def test_duplicate_name_stale_handle_and_cas_conflict_fail_safely(tmp_path: Path) -> None:
    context = _context(tmp_path)
    added = add_known_player_v1(
        context,
        display_name="Peter",
        aliases=(),
        platform_player_ids=(),
        expected_generation=0,
        entropy_source=lambda _size: b"s" * 32,
    )

    def unexpected_entropy(_size: int) -> bytes:
        raise AssertionError("Duplicate names must be rejected before entropy.")

    with pytest.raises(ValueError, match="disambiguated"):
        add_known_player_v1(
            context,
            display_name="peter",
            aliases=(),
            platform_player_ids=(),
            expected_generation=1,
            entropy_source=unexpected_entropy,
        )
    with pytest.raises(ValueError, match="Unknown or stale"):
        resolve_known_player_handle_v1(
            context.frontend_profile.document,
            "0" * 64,
        )

    current = context.frontend_profile.document
    assert current is not None
    external = build_local_frontend_profile_v1(
        revision=current.revision + 1,
        language="en",
        known_players=current.known_players,
    )
    assert (
        save_frontend_profile_file_v1(
            context.managed_home.root,
            external,
            expected_fingerprint=current.content_fingerprint,
        ).status
        == "saved"
    )
    with pytest.raises(FrontendProfilePersistenceConflictError):
        replace_known_player_v1(
            context,
            player_handle=build_known_player_handle_v1(added.player.player_id),
            display_name="Peter (Berlin)",
            aliases=(),
            platform_player_ids=(),
            expected_generation=1,
        )
    assert context.frontend_profile.document == current
