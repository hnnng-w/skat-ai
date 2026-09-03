from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import skatmind
import skatmind.api.v1 as public_api
from skatmind.app_web.frontend_profile_codec import (
    build_frontend_profile_bytes_v1,
    build_local_frontend_profile_v1,
    resume_local_frontend_profile_v1,
)
from skatmind.app_web.frontend_profile_contracts import (
    FrontendInterfacePreferencesV1,
)
from skatmind.app_web.localization_contracts import (
    IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES,
)
from skatmind.app_web.profile_player_contracts import (
    PROFILE_DRIVEN_FORM_DEFAULTS_VERSION,
    KnownPlayerPlatformIdV1,
    KnownPlayerV1,
    ManagedItemDisplayLabelV1,
)


def _known_player(player_id: str, display_name: str) -> KnownPlayerV1:
    return KnownPlayerV1(
        player_id=player_id,
        display_name=display_name,
        aliases=("H",),
        platform_player_ids=(KnownPlayerPlatformIdV1(platform="EuroSkat", player_id="external-1"),),
    )


def test_private_version_policy_and_nested_field_order_are_exact() -> None:
    assert PROFILE_DRIVEN_FORM_DEFAULTS_VERSION == 1
    assert type(PROFILE_DRIVEN_FORM_DEFAULTS_VERSION) is int
    assert "PROFILE_DRIVEN_FORM_DEFAULTS_VERSION" not in skatmind.__all__
    assert not hasattr(skatmind, "PROFILE_DRIVEN_FORM_DEFAULTS_VERSION")
    assert "PROFILE_DRIVEN_FORM_DEFAULTS_VERSION" not in public_api.__all__
    assert not hasattr(public_api, "PROFILE_DRIVEN_FORM_DEFAULTS_VERSION")
    assert IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES == (
        "technical_contracts_and_machine_values_remain_english",
        "unified_frontend_visible_content_supports_german_and_english",
        "one_private_local_frontend_profile_per_managed_data_root",
        "saved_language_overrides_browser_language",
        "browser_language_bootstraps_only_without_saved_preference",
        "user_facing_names_replace_required_manual_internal_ids",
        "validation_preserves_safe_values_and_workflow_context",
        "home_separates_record_analyze_learn_and_product_information",
        "language_and_profile_never_change_product_semantics",
        "no_external_translation_profile_sync_or_cloud_service",
    )

    platform_id = KnownPlayerPlatformIdV1("EuroSkat", "external-1")
    player = KnownPlayerV1("frontend-player-" + "a" * 64, "Henning", (), (platform_id,))
    label = ManagedItemDisplayLabelV1(
        "matches",
        "frontend-match-" + "b" * 64,
        "Thursday Match",
        "2026-09-03",
    )
    assert tuple(platform_id.to_dict()) == ("platform", "player_id")
    assert tuple(player.to_dict()) == (
        "player_id",
        "display_name",
        "aliases",
        "platform_player_ids",
    )
    assert tuple(label.to_dict()) == (
        "family",
        "product_id",
        "display_name",
        "played_date",
    )
    with pytest.raises(FrozenInstanceError):
        player.display_name = "Changed"  # type: ignore[misc]


def test_activated_profile_round_trip_and_empty_bytes_are_backward_compatible() -> None:
    old = build_local_frontend_profile_v1(revision=0, language="de")
    old_bytes = build_frontend_profile_bytes_v1(old)
    assert old_bytes == (
        b'{\n  "local_frontend_profile_version": 1,\n'
        b'  "document_kind": "skatmind_frontend_profile",\n'
        b'  "revision": 0,\n  "language": "de",\n'
        b'  "interface_preferences": {\n'
        b'    "advanced_settings_expanded": false\n  },\n'
        b'  "own_player_id": null,\n  "known_players": [],\n'
        b'  "preferred_perspective_player_id": null,\n'
        b'  "preferred_game_platform": null,\n'
        b'  "workflow_preferences": {\n'
        b'    "position_analysis": null,\n'
        b'    "historical_review": null\n  },\n'
        b'  "managed_item_display_labels": [],\n'
        b'  "content_fingerprint": "' + old.content_fingerprint.encode("ascii") + b'"\n}\n'
    )

    player = _known_player("frontend-player-" + "1" * 64, "Henning")
    label = ManagedItemDisplayLabelV1(
        family="sessions",
        product_id="frontend-session-" + "2" * 64,
        display_name="Game against Peter and Anna",
    )
    activated = build_local_frontend_profile_v1(
        revision=4,
        language="en",
        interface_preferences=FrontendInterfacePreferencesV1(advanced_settings_expanded=True),
        own_player_id=player.player_id,
        known_players=(player,),
        preferred_perspective_player_id=player.player_id,
        preferred_game_platform="EuroSkat",
        managed_item_display_labels=(label,),
    )
    assert resume_local_frontend_profile_v1(activated.to_dict()) == activated
    assert tuple(activated.to_dict()) == (
        "local_frontend_profile_version",
        "document_kind",
        "revision",
        "language",
        "interface_preferences",
        "own_player_id",
        "known_players",
        "preferred_perspective_player_id",
        "preferred_game_platform",
        "workflow_preferences",
        "managed_item_display_labels",
        "content_fingerprint",
    )


@pytest.mark.parametrize(
    "value",
    (
        KnownPlayerV1,
        ManagedItemDisplayLabelV1,
    ),
)
def test_profile_contract_classes_are_private(value: object) -> None:
    name = value.__name__
    assert name not in skatmind.__all__
    assert not hasattr(skatmind, name)
    assert name not in public_api.__all__
    assert not hasattr(public_api, name)


def test_known_player_limits_duplicate_normalization_and_reference_integrity() -> None:
    prefix = "frontend-player-"
    peter = KnownPlayerV1(prefix + "1" * 64, "Peter", (), ())
    with pytest.raises(ValueError, match="disambiguated"):
        build_local_frontend_profile_v1(
            known_players=(peter, KnownPlayerV1(prefix + "2" * 64, "peter", (), ()))
        )
    with pytest.raises(ValueError, match="own_player_id"):
        build_local_frontend_profile_v1(own_player_id=prefix + "3" * 64)
    with pytest.raises(ValueError, match="preferred_perspective_player_id"):
        build_local_frontend_profile_v1(
            known_players=(peter,),
            preferred_perspective_player_id=prefix + "3" * 64,
        )
    with pytest.raises(ValueError, match="maximum 512"):
        build_local_frontend_profile_v1(
            known_players=tuple(
                KnownPlayerV1(f"{prefix}{index:064x}", f"Player {index}", (), ())
                for index in range(513)
            )
        )
    with pytest.raises(ValueError, match="control"):
        KnownPlayerV1(prefix + "4" * 64, "Bad\nName", (), ())
    with pytest.raises(ValueError, match="120"):
        KnownPlayerV1(prefix + "4" * 64, "x" * 121, (), ())
    with pytest.raises(ValueError, match="at most 16"):
        KnownPlayerV1(
            prefix + "4" * 64,
            "Anna",
            tuple(f"Alias {index}" for index in range(17)),
            (),
        )
    with pytest.raises(ValueError, match="at most 16"):
        KnownPlayerV1(
            prefix + "4" * 64,
            "Anna",
            (),
            tuple(
                KnownPlayerPlatformIdV1("EuroSkat", f"player-{index}")
                for index in range(17)
            ),
        )
    with pytest.raises(ValueError, match="255"):
        KnownPlayerPlatformIdV1("EuroSkat", "x" * 256)


def test_managed_display_label_rules_are_strict() -> None:
    with pytest.raises(ValueError, match="Matches"):
        ManagedItemDisplayLabelV1("sessions", "session", "Game", "2026-09-03")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        ManagedItemDisplayLabelV1("matches", "match", "Match", "03.09.2026")
    with pytest.raises(ValueError, match="maximum 2,048"):
        build_local_frontend_profile_v1(
            managed_item_display_labels=tuple(
                ManagedItemDisplayLabelV1("sessions", f"session-{index}", f"Game {index}")
                for index in range(2049)
            )
        )
    long_imported_id = "imported-" + "x" * 512
    assert (
        ManagedItemDisplayLabelV1("sessions", long_imported_id, "Imported game").product_id
        == long_imported_id
    )
