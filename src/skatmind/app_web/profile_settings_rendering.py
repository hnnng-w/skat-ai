from __future__ import annotations

from html import escape

from .frontend_identifier_generation import build_known_player_handle_v1
from .frontend_profile_contracts import LocalFrontendProfileV1
from .frontend_profile_operations import (
    FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE,
    FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE,
    FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE,
)
from .profile_driven_creation import FRIENDLY_GAME_PLATFORMS
from .translation_catalog import translate_frontend_message_v1


def _t(locale: str, key: str, **values: object) -> str:
    return escape(translate_frontend_message_v1(locale, key, **values))


def _generation(value: int) -> str:
    return f'<input type="hidden" name="profile_generation" value="{value}">'


def _player_options(
    profile: LocalFrontendProfileV1 | None,
    *,
    selected_id: str | None,
    locale: str,
) -> str:
    options = [f'<option value="">{_t(locale, "settings.players.none")}</option>']
    if profile is not None:
        options.extend(
            f'<option value="{build_known_player_handle_v1(player.player_id)}"'
            f"{' selected' if player.player_id == selected_id else ''}>"
            f"{escape(player.display_name)}</option>"
            for player in profile.known_players
        )
    return "".join(options)


def _platform_fields(
    profile: LocalFrontendProfileV1 | None,
    *,
    locale: str,
) -> str:
    preferred = None if profile is None else profile.preferred_game_platform
    product_values = {value for _choice, value in FRIENDLY_GAME_PLATFORMS}
    selected_choice = next(
        (choice for choice, value in FRIENDLY_GAME_PLATFORMS if value == preferred),
        "custom" if preferred is not None else "",
    )
    custom_value = preferred if preferred is not None and preferred not in product_values else ""
    options = [
        f'<option value=""{" selected" if not selected_choice else ""}>'
        f"{_t(locale, 'settings.platform.none')}</option>"
    ]
    options.extend(
        f'<option value="{choice}"'
        f"{' selected' if choice == selected_choice else ''}>"
        f"{_t(locale, f'creation.platform.{choice}')}</option>"
        for choice, _value in FRIENDLY_GAME_PLATFORMS
    )
    options.append(
        f'<option value="custom"{" selected" if selected_choice == "custom" else ""}>'
        f"{_t(locale, 'creation.platform.custom')}</option>"
    )
    return (
        f"<label>{_t(locale, 'settings.preferences.platform')}"
        f'<select name="platform_choice">{"".join(options)}</select></label>'
        f'<label class="custom-platform-field">{_t(locale, "settings.preferences.custom_platform")}'
        f'<input name="custom_platform" maxlength="120" '
        f'value="{escape(custom_value, quote=True)}"></label>'
    )


def _preferences(
    profile: LocalFrontendProfileV1 | None,
    *,
    generation: int,
    locale: str,
) -> str:
    own_player_id = None if profile is None else profile.own_player_id
    perspective_id = None if profile is None else profile.preferred_perspective_player_id
    advanced = (
        False if profile is None else profile.interface_preferences.advanced_settings_expanded
    )
    return (
        '<section class="settings-panel" aria-labelledby="creation-defaults-heading">'
        f'<h3 id="creation-defaults-heading">'
        f"{_t(locale, 'settings.preferences.heading')}</h3>"
        f"<p>{_t(locale, 'settings.preferences.help')}</p>"
        f'<form method="post" action="{FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE}">'
        + _generation(generation)
        + f"<label>{_t(locale, 'settings.preferences.own_player')}"
        f'<select name="own_player_handle">'
        f"{_player_options(profile, selected_id=own_player_id, locale=locale)}"
        "</select></label>"
        f"<label>{_t(locale, 'settings.preferences.perspective')}"
        '<select name="preferred_perspective_player_handle">'
        f"{_player_options(profile, selected_id=perspective_id, locale=locale)}"
        "</select></label>"
        + _platform_fields(profile, locale=locale)
        + f"<fieldset><legend>{_t(locale, 'settings.preferences.advanced')}</legend>"
        f'<label><input type="radio" name="advanced_settings_expanded" value="false"'
        f"{' checked' if not advanced else ''}> "
        f"{_t(locale, 'common.answer.no')}</label>"
        f'<label><input type="radio" name="advanced_settings_expanded" value="true"'
        f"{' checked' if advanced else ''}> "
        f"{_t(locale, 'common.answer.yes')}</label></fieldset>"
        f'<button type="submit">{_t(locale, "settings.preferences.save")}</button>'
        "</form></section>"
    )


def _player_data(player) -> tuple[str, str]:
    aliases = "\n".join(player.aliases)
    platform_ids = "\n".join(
        f"{value.platform} = {value.player_id}" for value in player.platform_player_ids
    )
    return aliases, platform_ids


def _player_card(
    player,
    *,
    profile: LocalFrontendProfileV1,
    generation: int,
    locale: str,
) -> str:
    handle = build_known_player_handle_v1(player.player_id)
    aliases, platform_ids = _player_data(player)
    referenced = player.player_id in {
        profile.own_player_id,
        profile.preferred_perspective_player_id,
    }
    confirmation = (
        f'<label><input type="checkbox" name="confirm_referenced" value="on" required> '
        f"{_t(locale, 'settings.players.confirm_referenced')}</label>"
        if referenced
        else ""
    )
    return (
        '<article class="known-player-card">'
        f"<h4>{escape(player.display_name)}</h4>"
        "<details><summary>"
        f"{_t(locale, 'settings.players.edit')}</summary>"
        f'<form method="post" action="{FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE}">'
        + _generation(generation)
        + f'<input type="hidden" name="player_handle" value="{handle}">'
        + _player_editor_fields(
            display_name=player.display_name,
            aliases=aliases,
            platform_ids=platform_ids,
            locale=locale,
        )
        + f'<button type="submit">{_t(locale, "settings.players.save")}</button>'
        "</form></details>"
        f'<form class="remove-player-form" method="post" '
        f'action="{FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE}">'
        + _generation(generation)
        + f'<input type="hidden" name="player_handle" value="{handle}">'
        + confirmation
        + f'<button type="submit">{_t(locale, "settings.players.remove")}</button>'
        "</form></article>"
    )


def _player_editor_fields(
    *,
    display_name: str,
    aliases: str,
    platform_ids: str,
    locale: str,
) -> str:
    return (
        f"<label>{_t(locale, 'settings.players.display_name')}"
        f'<input name="display_name" maxlength="120" required '
        f'value="{escape(display_name, quote=True)}"></label>'
        f"<label>{_t(locale, 'settings.players.aliases')}"
        f'<textarea name="aliases" rows="3">{escape(aliases)}</textarea></label>'
        f"<p>{_t(locale, 'settings.players.aliases_help')}</p>"
        f"<label>{_t(locale, 'settings.players.platform_ids')}"
        f'<textarea name="platform_player_ids" rows="3">'
        f"{escape(platform_ids)}</textarea></label>"
        f"<p>{_t(locale, 'settings.players.platform_ids_help')}</p>"
    )


def _players(
    profile: LocalFrontendProfileV1 | None,
    *,
    generation: int,
    locale: str,
) -> str:
    cards = (
        ""
        if profile is None
        else "".join(
            _player_card(
                player,
                profile=profile,
                generation=generation,
                locale=locale,
            )
            for player in profile.known_players
        )
    )
    empty_players = f"<p>{_t(locale, 'settings.players.empty')}</p>"
    return (
        '<section class="settings-panel" aria-labelledby="known-players-heading">'
        f'<h3 id="known-players-heading">{_t(locale, "settings.players.heading")}</h3>'
        f"<p>{_t(locale, 'settings.players.help')}</p>"
        f'<div class="known-player-grid">{cards or empty_players}</div>'
        '<details class="add-player"><summary>'
        f"{_t(locale, 'settings.players.add')}</summary>"
        f'<form method="post" action="{FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE}">'
        + _generation(generation)
        + _player_editor_fields(
            display_name="",
            aliases="",
            platform_ids="",
            locale=locale,
        )
        + f'<button type="submit">{_t(locale, "settings.players.add_action")}</button>'
        "</form></details></section>"
    )


def _recommended_reset(*, generation: int, locale: str) -> str:
    return (
        '<section class="settings-panel" aria-labelledby="recommended-reset-heading">'
        f'<h3 id="recommended-reset-heading">'
        f"{_t(locale, 'settings.recommended_reset.heading')}</h3>"
        f"<p>{_t(locale, 'settings.recommended_reset.help')}</p>"
        f'<form method="post" action="{FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE}">'
        + _generation(generation)
        + '<label><input type="checkbox" name="confirm_recommended_reset" '
        'value="on" required> '
        f"{_t(locale, 'settings.recommended_reset.confirm')}</label>"
        f'<button type="submit">{_t(locale, "settings.recommended_reset.action")}</button>'
        "</form></section>"
    )


def render_local_settings_v1(
    *,
    profile: LocalFrontendProfileV1 | None,
    profile_generation: int,
    profile_valid: bool,
    locale: str,
) -> str:
    if type(profile_generation) is not int or profile_generation < 0:
        raise ValueError("profile_generation must be a non-negative integer.")
    if type(profile_valid) is not bool:
        raise ValueError("profile_valid must be a boolean.")
    if not profile_valid:
        return f"<p>{_t(locale, 'settings.invalid_reset_only')}</p>"
    return (
        '<div class="local-settings">'
        + _preferences(
            profile,
            generation=profile_generation,
            locale=locale,
        )
        + _players(
            profile,
            generation=profile_generation,
            locale=locale,
        )
        + _recommended_reset(generation=profile_generation, locale=locale)
        + "</div>"
    )
